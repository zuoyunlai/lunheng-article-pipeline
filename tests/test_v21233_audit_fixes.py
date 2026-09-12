#!/usr/bin/env python3
"""test_v21233_audit_fixes.py — v2.12.33 ClawHub 审计页复核修复回归门

背景（2026-09-12，ClawHub security-audit 页 v2.12.32：Outcome = Review，
Tencent AIG 1 条 + NVIDIA SkillSpector 15 条 + static-analysis clean）：

  F1  AIG T05（Warning·Least-privilege）—— 扫描器逐字引用 v2.12.32 新写的
      「工具面超限 → 继续」两级判据，判定「特权工具在多 Agent 常态运行中仍可用」。
      处置（主人裁决 = A 档「保持行为，只消歧义」）：重排为「阻断级在前 +
      铁律「超限 ≠ 调用许可」+ 主控裁决只放行继续、不放行越权调用」
      **行为一字不改**。
  F2  SkillSpector Intent-Code Divergence（Medium 98%）—— T7.5 散文写「不得依赖
      final/M-Gate-Report-v2.2.12.json」，5 行后伪代码却 check 该文件（T8 产物，
      此时不存在）⇒ 依赖倒置。今日 P1-6 只改散文、漏改伪代码（半修）。
  F3  SKILL.md:88 旧口径「发现越权即阻断该角色」残留（与 permissions.md 两级判据分叉）。
  F4  AIG AE1（HIGH，本次唯一 HIGH）—— 必读清单把三个路径用 ` + ` 拼在一格，
      扫描器逐个解析失败 ⇒ 拆成独立行（每格一个仓库根相对路径）。
  F5  SkillSpector Intent-Code Divergence（Medium 96%）—— 「只读」后开例外，读作矛盾
      ⇒ 改为「两径定义」（上游只读 / 自有报告可写），保留既有行为。
  F6  只读档落盘口径须三处（permissions / dispatch-header / 角色卡）一致，防漂移。

设计原则：每条断言「修复后的口径」，可被变异击杀；不断言实现细节。
"""

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
DH = ROOT / "references/_shared/dispatch-header.md"
PERM = ROOT / "references/permissions.md"
MGATE = ROOT / "references/_shared/M-Gate-Algorithm.md"
HARDENING = ROOT / "references/_shared/host-hardening-recipe.md"
COORD = ROOT / "references/agents/00-主控-扩展职责.md"


def read(p):
    assert p.exists(), f"缺少文件：{p}"
    return p.read_text(encoding="utf-8")


# =============================================================================
# F1 AIG T05（A 档：保持行为，只消歧义）
# =============================================================================
def test_f1_iron_rule_surface_is_not_a_licence():
    """铁律必须写在启动自检里：工具面超限 ≠ 获得任何调用许可"""
    dh = read(DH)
    assert "工具面超限 ≠ 获得任何调用许可" in dh, "缺铁律「超限 ≠ 调用许可」"
    assert "不授权我调用" in dh, "须点明超限不构成任何工具的调用授权"


def test_f1_blocking_rule_is_stated_first():
    """阻断级（实际调用）须排在工具面超限之前 —— 消歧义的核心动作"""
    dh = read(DH)
    i_call = dh.index("① 实际调用越权工具 = 阻断级")
    i_surface = dh.index("② 工具面超限 = 警告级")
    assert i_call < i_surface, "阻断级必须先于工具面超限陈述"


def test_f1_coordinator_override_does_not_license_calls():
    """主控裁决只放行「继续干活」，不放行任何越权调用"""
    dh = read(DH)
    assert "只放行「继续干活」，不放行任何越权工具调用" in dh, \
        "须写清裁决旁路的边界（不放行越权调用）"


def test_f1_surface_excess_points_to_hardening():
    """工具面超限须指明根治手段 = 宿主加固（而非让 worker 停工）"""
    dh = read(DH)
    assert "根治手段是宿主加固" in dh, "缺「根治手段是宿主加固」"
    assert "host-hardening-recipe.md" in dh, "须指向加固配方"


def test_f1_behavior_unchanged_continue_still_allowed():
    """A 档行为不变：超限仍记录 + 披露 + 照样开工（不退回自锁）"""
    dh = read(DH)
    assert "记录 + 披露" in dh and "照样开工" in dh
    assert "不中止" in dh, "不得退回「超限即中止」"
    assert "degraded" in dh and "降级可用" in dh


# =============================================================================
# F2 T7.5 伪代码 vs 散文（依赖倒置）
# =============================================================================
def test_f2_pseudocode_does_not_read_t8_artifact():
    """伪代码不得再 check T8 产出的 M-Gate 报告文件"""
    m = read(MGATE)
    bad = re.findall(r"check_m_gate_all_pass\(\s*['\"]final/M-Gate-Report", m)
    assert not bad, f"伪代码仍在 check T8 产物（依赖倒置未修）：{bad}"


def test_f2_pseudocode_reads_current_round():
    """伪代码须改为读本轮章节级 M 门记录 + status.md 记录表"""
    m = read(MGATE)
    assert "check_m_gate_all_pass_current_round()" in m, "缺本轮口径的检查函数"
    assert "不得读" in m and "尚未生成" in m, "须写明不得读 T8 产物的理由"


def test_f2_prose_and_pseudocode_agree():
    """同一门（M-Integrity-2）散口径与伪代码口径必须一致"""
    m = read(MGATE)
    assert "不得依赖 `final/M-Gate-Report-v2.2.12.json`" in m, "散文口径丢失（P1-6 回归）"
    # 二者不得互相矛盾：散文说「不得依赖」，伪代码就不能去读
    assert "check_m_gate_all_pass('final/M-Gate-Report-v2.2.12.json')" not in m, \
        "散文与伪代码口径分叉"


# =============================================================================
# F3 SKILL.md 旧口径残留
# =============================================================================
def test_f3_skill_no_stale_abort_role():
    """SKILL.md 不得残留「发现越权即阻断该角色」旧口径"""
    s = read(SKILL)
    assert "发现越权即" not in s, "SKILL.md 残留旧口径「发现越权即阻断该角色」"


def test_f3_skill_states_two_level():
    """SKILL.md 须与 permissions 一致地写两级判据"""
    s = read(SKILL)
    assert "工具面超限 = 警告级" in s
    assert "实际调用越权工具 = 阻断级" in s
    assert "≠ 调用许可" in s, "须点明超限 ≠ 调用许可"


# =============================================================================
# F4 AE1 必读清单路径可解析
# =============================================================================
def test_f4_entry_paths_not_glued():
    """必读清单第 1 层不得把多个路径用 + 拼进同一格"""
    s = read(SKILL)
    assert "`SKILL.md` + `references/pipeline-readme.md`" not in s, \
        "入口路径仍以 + 拼接（扫描器无法逐个解析）"


def test_f4_each_entry_path_own_row():
    """入口三件套须各自独立成行，且为仓库根相对路径"""
    s = read(SKILL)
    for p in ["`SKILL.md`（入口）", "`references/pipeline-readme.md`（入口）",
              "`references/_shared/glossary-full.md`（入口）"]:
        assert p in s, f"入口路径未独立成行：{p}"


def test_f4_relative_basis_still_declared():
    """基准声明仍在（v2.12.31 修的这一点不得回退）"""
    s = read(SKILL)
    assert "表内路径均以仓库根为基准" in s


# =============================================================================
# F5 / F6 只读档两径定义 + 三处一致
# =============================================================================
def test_f5_readonly_is_two_path_definition():
    """只读档须写成「两径定义」而非「先只读、再破例」"""
    p = read(PERM)
    assert "只读档落盘例外" in p, "锚点不得删（v2.12.32 测试钉死）"
    assert "两径定义" in p, "缺「两径定义」框架"
    assert "一次定义两条路径、无追加例外" in p, "须写明无追加例外"
    assert "授权路径之外一律只读" in p


def test_f5_no_contradictory_phrasing():
    """不得留「先说只读、再破例」的自相矛盾措辞"""
    p = read(PERM)
    assert "不是「先说只读、再破例」" in p or "并非「先说只读、再破例」" in p, \
        "须显式否掉矛盾读法"
    # 旧的「主控代写盘」口径已被直写授权取代
    assert "报告经交接回传、主控代写盘" not in p, "permissions 表仍留旧的「主控代写盘」口径"


def test_f6_readonly_tier_consistent_across_docs():
    """只读档口径三处一致（permissions / dispatch-header / 角色卡）"""
    p = read(PERM)
    dh = read(DH)
    audit_card = read(ROOT / "references/agents/07-审计-auditor.md")
    assert "上游只读 + 自有报告可写" in p, "permissions 表未用统一措辞"
    assert "上游只读 + 自有报告可写" in dh, "dispatch-header 档位行未同步"
    # 角色卡仍须保留「无 write 工具」这一诚实边界说明
    assert "无 write 工具" in audit_card or "只读档" in audit_card


def test_f6_hardening_mentions_not_a_licence():
    """加固配方须与铁律一致（防四处漂移）"""
    h = read(HARDENING)
    assert "超限 ≠ 调用许可" in h, "加固配方缺「超限 ≠ 调用许可」"
    assert "两级判据" in h and "警告级" in h and "阻断级" in h


def test_f6_coord_card_mentions_iron_rule():
    """主控卡须同步铁律（防与子代理侧口径分叉）"""
    c = read(COORD)
    assert "工具面超限 ≠ 调用许可" in c
    assert "自锁陷阱" in c, "自锁陷阱记录不得丢"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
