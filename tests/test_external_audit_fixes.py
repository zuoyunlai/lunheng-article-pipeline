#!/usr/bin/env python3
"""test_external_audit_fixes.py — 第三方「论衡 vs 官方文档」三维审计修复回归门

背景（2026-09-12，三维只读审计）：
  审计发现三类系统性问题，本测试把修复钉死，防复发：

  P0-1  denied 漏 4 个高危工具（message / gateway / secrets / code_execution）
  P0-2  「19 项特权工具禁用」被写成既成事实 —— 而官方 SKILL.md frontmatter
        **无任何工具策略键**，沙箱默认 off、未设 tools.* 时平台默认即全权访问
        （docs/gateway/sandboxing.md、docs/gateway/permission-modes.md）。
        修法：措辞改为**声明式** + 指向 host-hardening-recipe.md。
  P0-3  「记忆辅助无 LLM vendor 外发」不成立 —— memory.search.provider 未显式设置时
        默认走 OpenAI embeddings（docs/concepts/active-memory.md）。
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

# 第三方审计点名的 P0 遗漏工具（必须进 denied）
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

@pytest.mark.parametrize("cap", AUDIT_P0_TOOLS + AUDIT_P1_TOOLS)
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
    """正文声明的「27 项」必须等于 frontmatter 实际条数（防数字漂移）"""
    assert len(_denied()) == 27, f"denied 实际 {len(_denied())} 项，与正文声明的 27 项不符"


def test_declarative_stance_declared():
    """必须显式声明「声明式、非平台强制」——这是 P0-2 的根因修复"""
    skill = SKILL.read_text(encoding="utf-8")
    assert "声明式" in skill, "SKILL.md 未声明 denied 为「声明式」"
    perms = PERMISSIONS.read_text(encoding="utf-8")
    assert "声明式" in perms, "permissions.md 未声明 denied 为「声明式」"


def test_no_frontmatter_enforcement_claim():
    """不得暗示 frontmatter 本身可强制工具面"""
    skill = SKILL.read_text(encoding="utf-8")
    assert "无工具策略键" in skill or "无任何工具策略键" in skill, (
        "SKILL.md 未说明官方 frontmatter 无工具策略键（P0-2 根因）")


# ---------------- P0-3：记忆辅助外发口径 ----------------

def test_memory_egress_claim_corrected():
    """「无 LLM vendor 外发」是错的 —— memory.search.provider 未设时默认 OpenAI embeddings"""
    for f in (README, QUICKSTART, EXT_SERVICES):
        text = f.read_text(encoding="utf-8")
        assert "无 LLM vendor 外发" not in text, (
            f"{f.name} 仍在声称记忆检索「无 LLM vendor 外发」（官方默认走 OpenAI embeddings）")
    # 修正后的口径必须点明 embeddings 默认外发
    assert "embeddings" in EXT_SERVICES.read_text(encoding="utf-8"), (
        "external-services.md 未点明 memories 检索默认走 embeddings")


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
    """taskName 约束须含 {0,63} 上限与 last/all 保留字"""
    ext = (ROOT / "references" / "agents" / "00-主控-扩展职责.md").read_text(encoding="utf-8")
    assert "{0,63}" in ext, "taskName 约束缺 {0,63} 长度上限"
    assert "保留字" in ext and "last" in ext and "all" in ext, (
        "taskName 约束缺 last/all 保留字说明")
