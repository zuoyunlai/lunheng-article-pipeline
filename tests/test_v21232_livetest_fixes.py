#!/usr/bin/env python3
"""test_v21232_livetest_fixes.py — v2.12.32 无人值守实测修订回归门

背景（2026-09-12，`run/2026-09-12-算法审美趋同/实测报告.md` §六）：
  v2.12.32 实测跑通全流程，但暴露 2 P0 + 3 P1 + 2 P2。本测试把每条修复钉死。

  P0-1  denied 声明「自锁陷阱」—— 工具面超限被当阻断项 ⇒ T2/T3 首轮零产物、流水线自锁
        修法：判据拆分（工具面超限=警告 / 实际调用=阻断）+ degraded 语义 + 主控裁决旁路
  P0-2  字数约束自相矛盾 —— 分章硬指标之和 5,500 与总量上限 6,000 同时写死 ⇒ 永不关闭的 P0
        修法：Phase 0 预算机械自查（上限与分章硬指标只允许给定其一）
  P1-1  G14 复检次数无收敛判据 → 修法：4 条收敛规则
  P1-2  G14 判定口径分叉（同一稿 Warning vs Pass）→ 修法：Phase 0 固定口径 + 报告头标 g14_scope
  P1-3  M-Form-7 白名单缺「致谢」，而可发表性 F 选项强制要求致谢 ⇒ 字面必判违规
  P2-1  机械搬运无低成本路径 → 修法：sync 与组装合并
  P2-2  T5 成本中心易超时 → 修法：禁止全文重读卡片（按需 offset/limit）+ 硬卡 900s 照抄

设计原则：只断言「修复后的口径」，不断言实现细节；每条都能被变异击杀。
"""

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DH = ROOT / "references/_shared/dispatch-header.md"
PERM = ROOT / "references/permissions.md"
COORD = ROOT / "references/agents/00-主控-扩展职责.md"
STATUS_TPL = ROOT / "references/templates/status-template.md"
BRIEF_TPL = ROOT / "references/templates/任务简报-template.md"
WC_TABLE = ROOT / "references/_shared/字数判定表.md"
G14 = ROOT / "references/gates/14-中文AI痕迹-gate.md"
PHASE_ORDER = ROOT / "references/_shared/phase-order.yaml"
DELIVERABLES = ROOT / "references/deliverables.md"
MGATE = ROOT / "references/_shared/M-Gate-Algorithm.md"
T5 = ROOT / "references/dispatch/T5-写手.md"
HARDENING = ROOT / "references/_shared/host-hardening-recipe.md"


def read(p):
    assert p.exists(), f"缺少文件：{p}"
    return p.read_text(encoding="utf-8")


# =============================================================================
# P0-1 自锁陷阱：工具面 ≠ 调用
# =============================================================================
def test_p0_1_tool_surface_vs_call_split():
    """两级判据必须同时存在：工具面超限=警告级（不中止）、实际调用=阻断级"""
    dh = read(DH)
    assert "工具面超限" in dh, "dispatch-header 缺「工具面超限」判据"
    assert "警告级" in dh and "不中止" in dh, "工具面超限必须降为警告级且明确不中止"
    assert "实际调用越权工具 = 阻断级" in dh or "实际调用" in dh and "阻断级" in dh, \
        "缺「实际调用=阻断级」判据"
    assert "针对「调用」，不针对「工具面」" in dh, "必须写明阻断只针对调用"


def test_p0_1_old_selflock_wording_is_gone():
    """旧口径「工具面超限 ⇒ 立即停止」不得残留（它就是自锁根因）"""
    dh = read(DH)
    for bad in [
        "若出现**本档白名单之外**的工具（尤其",
        "⇒ **立即停止：不读、不写、不 spawn**",
        "由主控裁决。\n> - 若与本档白名单一致",
    ]:
        assert bad not in dh, f"旧自锁口径未清除：{bad!r}"


def test_p0_1_degraded_not_abort():
    """自检发现工具面超限且无主控裁决 ⇒ 返回 degraded 并继续执行，不是中止"""
    dh = read(DH)
    assert 'degraded' in dh and 'capability_excess' in dh
    assert "降级可用" in dh and "**不是**中止" in dh, "必须写明 degraded ≠ 中止"


def test_p0_1_coordinator_override_passthrough():
    """主控裁决旁路必须写入文档（实测按此路径成功重派）"""
    dh = read(DH)
    assert "主控裁决旁路" in dh, "dispatch-header 缺主控裁决旁路"
    assert "报告 + 自律继续" in dh, "旁路话术必须可照抄"
    assert "不得" in dh and "中止" in dh


def test_p0_1_tier_deactivation_not_triggered_by_surface_only():
    """「仅工具面超限」不得触发该档停用（否则未加固宿主上多 Agent 不可用）"""
    perm = read(PERM)
    coord = read(COORD)
    assert "仅「工具面超限」不触发该档停用" in perm, "permissions 缺该档停用边界"
    assert "自锁陷阱" in coord, "主控卡需显式记录自锁陷阱与裁决旁路"


def test_p0_1_status_template_two_level():
    """status.md 能力自检表须分两级列（面超限 / 调用越权）"""
    tpl = read(STATUS_TPL)
    assert "工具面超限（警告级" in tpl
    assert "越权调用（阻断级" in tpl
    assert "面超限·继续" in tpl or "⚠️ 面超限" in tpl


# =============================================================================
# P0-2 字数预算机械自查
# =============================================================================
def test_p0_2_budget_identity_exists():
    """字数判定表须含 Phase 0 预算恒等式"""
    t = read(WC_TABLE)
    assert "Phase 0 预算机械自查" in t, "字数判定表缺 §六 预算机械自查"
    assert "Σ(各章最小字数硬指标) + 附录预算 + Σ(刚性段落下限) ≤ 总量上限" in t, \
        "缺预算恒等式"


def test_p0_2_only_one_given():
    """铁律：上限与分章硬指标只允许给定其一（两个都写死=必出矛盾）"""
    t = read(WC_TABLE)
    assert "只允许给定其一" in t
    assert "禁" in t and "超了再说" in t, "必须禁掉「先写着，超了再说」"
    assert "二选一" in t, "不满足须当场请主人二选一"


def test_p0_2_brief_template_requires_selfcheck():
    """任务简报模板必须要求填写 预算自查 行"""
    t = read(BRIEF_TPL)
    assert "预算自查" in t, "任务简报模板缺预算自查字段"
    assert "只允许给定其一" in t


# =============================================================================
# P1-1 G14 复检收敛判据
# =============================================================================
def test_p1_1_g14_convergence_rules():
    """4 条收敛规则：绑定交付版本 / 条件跳过 / 收敛停 / 硬上限"""
    g = read(G14)
    assert "复检收敛判据" in g, "G14 闸缺复检收敛判据"
    assert "判定绑定交付版本" in g, "缺硬原则：判定必须绑定交付版本"
    assert "skipped_no_new_prose" in g, "缺「仅删不新增 → 跳过复检」标记"
    assert "连续两次同判定且无新增命中项" in g, "缺收敛停条件"
    assert re.search(r"G14 重跑次数 ≤ 修订轮数 \+ 1", g), "缺硬上限"


def test_p1_1_phase_order_references_convergence():
    """phase-order.yaml 的 after_each 须指针到收敛判据"""
    p = read(PHASE_ORDER)
    assert "复检收敛" in p or "收敛判据" in p, "phase-order 缺收敛判据指针"
    assert "g14_rerun: skipped_no_new_prose" in p


def test_p1_1_no_polling_style_growth():
    """G14 收敛不得写成「无限重跑」口径"""
    g = read(G14)
    assert "不得无界增长" in g


# =============================================================================
# P1-2 G14 判定口径分叉
# =============================================================================
def test_p1_2_g14_scope_pinned_at_phase0():
    """G14-B 口径须在 Phase 0 固定，报告头标 g14_scope"""
    g = read(G14)
    assert "G14-B 口径固定" in g, "缺 G14-B 口径固定"
    assert "g14_scope: strict|lax" in g or "g14_scope" in g, "缺报告头口径字段"
    assert "严格" in g and "宽松" in g, "必须给出严格/宽松两档定义"
    assert "小节开门段同构" in g, "必须点名争议点（小节开门段同构）"


# =============================================================================
# P1-3 M-Form-7 白名单补「致谢」
# =============================================================================
def test_p1_3_whitelist_has_thanks():
    """M-Form-7 白名单必须含致谢（否则与可发表性 F 选项强制要求冲突）"""
    d = read(DELIVERABLES)
    m = read(MGATE)
    assert "`## 致谢`" in d, "deliverables 白名单缺 `## 致谢`"
    assert "以下 **6** 节" in d, "deliverables 白名单节数未更新为 6"
    assert "致谢" in m, "M-Gate 算法 whitelist 数组缺致谢"
    # bash 复核例的 awk 正则须含致谢（第 412 行附近的 M-Form-7 例）
    assert re.search(r"先行者文献\|致谢\|AI 使用声明", m), "M-Gate bash 复核例缺致谢"


def test_p1_3_whitelist_array_has_thanks_not_five():
    """算法数组须为 7 项且注释说明致谢来源"""
    m = read(MGATE)
    arr = re.search(r"whitelist = \[(.*?)\]", m, re.S)
    assert arr, "未找到 whitelist 数组"
    items = [x.strip().strip('"') for x in arr.group(1).split(",")]
    assert "致谢" in items, "whitelist 数组缺致谢"
    assert len(items) == 7, f"whitelist 应为 7 项，实际 {len(items)}"


# =============================================================================
# P2-1 机械搬运合并
# =============================================================================
def test_p2_1_mechanical_merge_documented():
    """机械复制节点须有合并指引（少一个 spawn = 少一个失败面）"""
    p = read(PHASE_ORDER)
    c = read(COORD)
    assert "机械搬运合并" in p, "phase-order 缺机械搬运合并指引"
    assert "机械搬运合并" in c, "主控卡缺机械搬运合并指引"


# =============================================================================
# P2-2 T5 成本中心 / 硬卡 900s
# =============================================================================
def test_p2_2_t5_timeout_and_read_discipline():
    """T5 硬卡须写 900s 照抄 + 禁止全文重读大卡（按需局部读）"""
    t = read(T5)
    assert "900" in t, "T5 派发话术缺 900s 硬卡"
    assert "与 T6 同值" in t, "须点明 T5 与 T6 硬卡同值（实测误传 720）"
    assert "禁止全文重读" in t, "T5 缺读卡纪律"
    assert "offset" in t and "limit" in t, "须给出按需局部读手段"


# =============================================================================
# 文档澄清（实测 §四/§二④ 附带项）
# =============================================================================
def test_docs_timeout_is_not_zero_artifact():
    """超时 ≠ 零产物：watchdog 判据只能是「产物不存在 + 心跳未续」"""
    dh = read(DH)
    c = read(COORD)
    assert "超时 ≠ 零产物" in dh, "dispatch-header 缺「超时≠零产物」"
    assert "超时 ≠ 零产物" in c, "主控卡缺「超时≠零产物」"


def test_docs_token_two_fields_clarified():
    """Stats line 缺失不判平台异常 + 两个 token 字段不是同一口径"""
    dh = read(DH)
    assert "平台未回传" in dh, "缺 Stats line 缺失的口径下调"
    assert "两个 token 字段不是同一口径" in dh, "缺 token 双口径澄清"
    assert "权威值" in dh


def test_docs_readonly_tier_may_write_own_report():
    """只读档落盘例外（实测验证有效，写入文档）"""
    perm = read(PERM)
    assert "只读档落盘例外" in perm, "permissions 缺只读档落盘例外"
    assert "不修改上游产物" in perm, "须写清「只读」的边界"


def test_docs_hardening_mentions_two_level():
    """加固配方须与两级判据一致（防三处漂移）"""
    h = read(HARDENING)
    assert "两级判据" in h
    assert "警告级" in h and "阻断级" in h


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
