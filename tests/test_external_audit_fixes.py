#!/usr/bin/env python3
"""test_external_audit_fixes.py — 第三方「论衡 vs 官方文档」三维审计修复回归门

背景（2026-09-12，三维只读审计）：
  审计发现三类系统性问题，本测试把修复钉死，防复发：

  P0-1  denied 漏 4 个高危工具（message / gateway / secrets / code_execution）
  P0-2  「19 项特权工具禁用」被写成既成事实 —— 而官方 SKILL.md frontmatter
        **无任何工具策略键**，沙箱默认 off、未设 tools.* 时平台默认即全权访问
        （docs/gateway/sandboxing.md、docs/gateway/permission-modes.md）。
        修法：措辞改为**声明式**（声明调用边界，不承诺平台强制）。
  P0-3  记忆读工具「无 LLM vendor 外发」误述 —— memory.search.provider 未显式设置时
        默认走 OpenAI embeddings（docs/concepts/active-memory.md）。
        后续口径重构：该类工具已从论衡工具面整体移除，本项回归门改写为移除门。
  P1-1  spawn `cwd` 口径自相矛盾（absolute vs relative）
  P1-2  yield watchdog 伪代码写成 while 轮询循环（官方禁止为等待而轮询）
  P1-4  denied 漏 sessions / conversations_send / conversations_turn

设计原则：只断言「修复后的口径」，不断言实现细节；每条都能被变异击杀。
"""

import re
import sys
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
README = ROOT / "README.md"
QUICKSTART = ROOT / "QUICKSTART.md"
PERMISSIONS = ROOT / "references" / "permissions.md"
PROTOCOL = ROOT / "references" / "_shared" / "关键协议.md"
EXT_SERVICES = ROOT / "references" / "_shared" / "external-services.md"
DISPATCH_HEADER = ROOT / "references" / "_shared" / "dispatch-header.md"
RESILIENCE = ROOT / "references" / "_shared" / "执行韧化协议-design.md"

# 审计/扫描器先后点名的遗漏工具（必须进 denied；v2.12.39 从 39 扩至 40；v2.12.49 从 40 扩至 41，含 image_generate）
AUDIT_NAMED = ["message", "gateway", "secrets", "code_execution", "sessions",
               "conversations_send", "conversations_turn",
               # v2.12.38：SkillSpector/AIG + 全量审计 P1-1 补列
               "screen", "canvas", "show_widget", "agents_list",
               "get_goal", "create_goal", "update_goal",
               "suggest_task", "dismiss_task", "heartbeat_respond",
               "x_search", "pdf",
               # v2.12.39：SkillSpector「Context-Inappropriate Capability」
               "view_image"]
AUDIT_P0_TOOLS = ["message", "gateway", "secrets", "code_execution"]
# P1 遗漏工具
AUDIT_P1_TOOLS = ["sessions", "conversations_send", "conversations_turn"]


def _fm_tools() -> dict:
    text = SKILL.read_text(encoding="utf-8")
    fm = yaml.safe_load(text.split("---", 2)[1])
    return ((fm.get("metadata") or {}).get("tools") or {})


def _denied() -> set:
    return {str(x) for x in (_fm_tools().get("denied") or [])}


# ---------------- P0-1 / P1-4：denied 遗漏修复 ----------------

@pytest.mark.parametrize("cap", AUDIT_NAMED)
def test_audit_named_tools_are_denied(cap):
    """审计点名的遗漏工具必须出现在 frontmatter denied 中"""
    assert cap in _denied(), (
        f"{cap} 不在 metadata.tools.denied —— 第三方审计 P0/P1 遗漏修复被回退？")


@pytest.mark.parametrize("cap", AUDIT_P0_TOOLS)
def test_denied_tools_rejected_by_assert_script(cap):
    """denied 声明必须与能力断言脚本一致（门 T 的能力级回归）"""
    sys.path.insert(0, str(ROOT / "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cap_assert_audit", ROOT / "scripts" / "capability-assert.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with pytest.raises(mod.CapabilityAssertionError):
        mod.validate_capabilities("T1", ["read", cap])


def test_ask_user_still_allowed():
    """人在环依赖 ask_user —— 不得因收窄 denied 而误伤"""
    sys.path.insert(0, str(ROOT / "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cap_assert_ask", ROOT / "scripts" / "capability-assert.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.validate_capabilities("T1", ["read", "ask_user"])  # 不抛异常即通过


# ---------------- P0-2：声明式口径 ----------------

def test_no_stale_19_count():
    """「19 项」旧计数不得残留（本次扩至 27 项）"""
    for f in (SKILL, README, QUICKSTART, PERMISSIONS, DISPATCH_HEADER):
        text = f.read_text(encoding="utf-8")
        assert "19 项" not in text and "19项" not in text, (
            f"{f.name} 仍残留旧计数「19 项」—— denied 已扩至 27 项")


def test_denied_count_matches_declared_number():
    """正文声明的「41 项」必须等于 frontmatter 实际条数（防数字漂移）"""
    assert len(_denied()) == 41, f"denied 实际 {len(_denied())} 项，与正文声明的 41 项不符"


def test_declarative_stance_declared():
    """必须显式声明「声明式、非平台强制」——这是 P0-2 的根因修复"""
    skill = SKILL.read_text(encoding="utf-8")
    assert "声明式" in skill, "SKILL.md 未声明 denied 为「声明式」"
    perms = PERMISSIONS.read_text(encoding="utf-8")
    assert "声明式" in perms, "permissions.md 未声明 denied 为「声明式」"


def test_no_frontmatter_enforcement_claim():
    """不得暗示 frontmatter 本身可强制工具面（v2.12.37 措辞订正）

    旧断言要求出现「无工具策略键」—— 该表述**不准确**：官方认可 `allowed-tools` 键
    （`skills/skill-creator/scripts/quick_validate.py` 允许键白名单；`docs/tools/skills.md`），
    只是它只接受平铺工具白名单，无法表达按角色/按子代理档位的权限矩阵。
    本测试改锚「自定义声明 + 加载器不执行」这一**正确**口径，并禁止回退到旧说法。
    """
    skill = SKILL.read_text(encoding="utf-8")
    assert "自定义声明" in skill and "加载器不执行" in skill, (
        "SKILL.md 未说明 metadata.tools 为自定义声明且加载器不执行（P0-2 根因）")
    assert "无工具策略键" not in skill, (
        "SKILL.md 仍含「无工具策略键」这一不准确表述（官方存在 allowed-tools 键）")


# ---------------- P0-3：记忆读工具外发口径（已随工具面移除而改写） ----------------

def test_memory_helper_removed_no_false_egress_claim():
    """记忆读工具已从论衡工具面移除 —— 不得再残留外发声明或工具名"""
    for f in (README, QUICKSTART, EXT_SERVICES):
        text = f.read_text(encoding="utf-8")
        assert "无 LLM vendor 外发" not in text, (
            f"{f.name} 仍在声称记忆检索「无 LLM vendor 外发」（官方默认走 OpenAI embeddings）")
        for tool in ("memory_get", "memory_search", "memory_recall"):
            assert tool not in text, (
                f"{f.name} 仍提及已移除的记忆读工具 {tool}")


# ---------------- P1-1：cwd 口径统一 ----------------

def test_cwd_absolute_consistent():
    """spawn 的 cwd 必须统一为绝对路径（不得再有「相对 workspace 根」指令）"""
    skill = SKILL.read_text(encoding="utf-8")
    assert "必须绝对路径" in skill, "SKILL.md 未强调 spawn cwd 必须绝对路径"
    for f in (PERMISSIONS, PROTOCOL, QUICKSTART):
        text = f.read_text(encoding="utf-8")
        assert "cwd: run/<项目名>/（相对 workspace 根）" not in text, (
            f"{f.name} 仍指示 spawn 传相对路径 cwd（与 SKILL.md 矛盾）")
        assert "显式传 `cwd: run/<项目名>/`（相对" not in text, (
            f"{f.name} 仍指示 spawn 传相对路径 cwd")


def test_permissions_distinguishes_two_cwd_meanings():
    """permissions.md 必须区分「spawn 参数 cwd」与「read/write 相对路径边界」"""
    perms = PERMISSIONS.read_text(encoding="utf-8")
    assert "两个 `cwd` 不是一回事" in perms, (
        "permissions.md 未区分 spawn cwd（绝对）与文件工具边界（相对）")


# ---------------- P1-2：watchdog 事件驱动 ----------------

def test_no_yield_polling_loop():
    """yield watchdog 不得写成 while 轮询循环（yield 会结束当前 turn）"""
    text = RESILIENCE.read_text(encoding="utf-8")
    assert "while wait_elapsed < WATCHDOG_TIMEOUT" not in text, (
        "执行韧化协议仍含 while-yield 轮询伪代码（官方禁止为等待而轮询）")
    assert "非循环" in text or "无 while" in text, (
        "执行韧化协议未显式声明 watchdog 为单次事件驱动自查")


# ---------------- P1-2b：taskName 约束补全 ----------------

def test_taskname_constraint_complete():
    """taskName 约束须含 {0,63} 上限与 last/all 保留字。

    v2.12.62 起：该约束随「主控扩展职责 §二十三 二次分层」迁入唯一真源
    `_shared/执行韧化协议-exec.md`（审计 P2-6；原三处承载收敛为一处）。
    本测试相应**加强**为「真源含完整约束 **且** 卡内留有指向真源的指针」——
    比只查一个文件的字面更强：约束既完整、又不得从主控阅读路径上消失。
    """
    ext = (ROOT / "references" / "agents" / "00-主控-扩展职责.md").read_text(encoding="utf-8")
    src = (ROOT / "references" / "_shared" / "执行韧化协议-exec.md").read_text(encoding="utf-8")
    assert "{0,63}" in src, "taskName 约束缺 {0,63} 长度上限（真源）"
    assert "保留字" in src and "last" in src and "all" in src, (
        "taskName 约束缺 last/all 保留字说明（真源）")
    assert "执行韧化协议-exec.md" in ext, (
        "主控扩展职责卡未指向 taskName 约束真源（约束从主控阅读路径上消失）")
