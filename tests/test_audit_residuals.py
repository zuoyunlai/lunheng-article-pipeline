#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_audit_residuals.py — 第三方审计残余项回归门（v2.12.31 候选新增）

背景（2026-09-12 第三方全量审计）：
  三批修复（v2.12.30）覆盖了 P0×4 / 发布链 P1×4 / 文档质量 P2×3，但**流程审计报告**另有
  P1×6 + P2×9 未纳入那三批。本文件为这些残余项补机械门，防止同类缺陷再次静默复发。

对应关系（审计编号 → 本文件测试）：
  P2-2 行号型引用（修订下必然漂移）      → test_no_line_number_refs
  P2-4 悬挂指针（SKILL.md 已无该章节）    → test_no_dangling_arbitration_pointers
  P1-5 轻量档 T6「必跳/可跳过」互斥       → test_lite_tier_t6_rule_consistent
  P2-8 轻量档边界 ≤3000 vs 2000-3000     → test_lite_tier_boundary_consistent
  P2-3 README 正文「当前版本」错版        → test_readme_prose_version_matches_frontmatter
  P1-5 真源缺口（yaml 未声明 T6 轻量档）  → test_yaml_declares_t6_lite_tier_rule
  P2-1 checkpoint 二选一 vs 三态         → test_checkpoint_card_phase2_5_three_states
  P2-9 无应答策略两套并存未标注           → test_g14_warning_declares_non_owner_checkpoint
  P1-6 T7.5 读 T8 才产出的 JSON（倒置）   → test_t7_5_does_not_depend_on_t8_artifact
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
SKILL = ROOT / "SKILL.md"
README = ROOT / "README.md"
REFS = ROOT / "references"
YAML = REFS / "_shared" / "phase-order.yaml"

# 行号型引用：任何 `<path>.md:<数字>`（修订下必然漂移，2026-09-12 审计 P2-2）
LINE_REF = re.compile(r"[A-Za-z0-9_/\-]+\.md:[0-9]+")


def _md_files():
    return [p for p in REFS.rglob("*.md")]


def test_no_line_number_refs():
    bad = []
    for p in _md_files() + [SKILL]:
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for m in LINE_REF.finditer(line):
                bad.append(f"{p.relative_to(ROOT)}:{i} → {m.group(0)}")
    assert not bad, "存在行号型引用（应改章节名）：\n" + "\n".join(bad[:10])


def test_no_dangling_arbitration_pointers():
    """SKILL.md 无「修订回环仲裁规则」章节（已外移 pipeline-overview.md §同名）"""
    bad = []
    for p in _md_files():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "SKILL.md「修订回环仲裁规则」" in line or "SKILL.md 修订回环仲裁表" in line:
                bad.append(f"{p.relative_to(ROOT)}:{i}")
    assert not bad, "悬挂指针（应指向 pipeline-overview.md）：\n" + "\n".join(bad)
    # 正向前提：外移目标章节确实存在，否则「重定向」本身也是悬空的
    assert "## 修订回环仲裁规则" in (REFS / "_shared" / "pipeline-overview.md").read_text(encoding="utf-8"), \
        "pipeline-overview.md 缺「修订回环仲裁规则」章节 —— 指针目标不存在"


def test_lite_tier_t6_rule_consistent():
    """轻量档 T6 口径唯一：必跳（原「可跳过」四处已收敛）"""
    bad = []
    for p in _md_files():
        t = p.read_text(encoding="utf-8")
        if re.search(r"T6\s*可跳过|可跳过\s*T6", t):
            bad.append(str(p.relative_to(ROOT)))
    assert not bad, f"仍有「T6 可跳过」表述（真源 = 字数判定表「T6 必跳」）：{bad}"


def test_lite_tier_boundary_consistent():
    """轻量档边界唯一：2000-3000 字（≤3000 会把 <2000 的「直写」误并入）"""
    bad = []
    for p in _md_files():
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"轻量档（≤\s*3000", line):
                bad.append(f"{p.relative_to(ROOT)}:{i}")
    assert not bad, "轻量档边界仍写 ≤3000（应 2000-3000）：\n" + "\n".join(bad)


def test_readme_prose_version_matches_frontmatter():
    """README 正文「当前版本」不得落后于 SKILL.md frontmatter（check-version 不校正文）"""
    m = re.search(r"^\s{4}version:\s*(\S+)", SKILL.read_text(encoding="utf-8"), re.M)
    assert m, "SKILL.md 缺 frontmatter version"
    ver = m.group(1)
    prose = re.search(r"\*\*v([0-9]+\.[0-9]+\.[0-9]+)\*\*（[^）]*当前版本", README.read_text(encoding="utf-8"))
    assert prose, "README 缺「当前版本」正文行"
    assert prose.group(1) == ver, f"README 正文版本 v{prose.group(1)} ≠ frontmatter {ver}"


def test_yaml_declares_t6_lite_tier_rule():
    """P1-5 真源缺口：t6_g14 须声明 T6 的轻量档规则（原仅声明 G14 → 各文件三种读法）"""
    t = YAML.read_text(encoding="utf-8")
    assert "t6_degrade: skip_in_lite_tier" in t, "phase-order.yaml 未声明 t6_degrade（轻量档 T6 必跳）"


def test_checkpoint_card_phase2_5_three_states():
    """P2-1：Phase 2.5 决策为三态（真源 yaml decisions），缺 restart_phase 会使决策落不到枚举"""
    t = (REFS / "templates" / "checkpoint-card-template.md").read_text(encoding="utf-8")
    assert "restart_phase" in t, "checkpoint 模板 Phase 2.5 未含 restart_phase（三态）"


def test_g14_warning_declares_non_owner_checkpoint():
    """P2-9：G14 Warning 超时继续属自动化例外，须显式标注非「人在环四节点」（两套策略互不适用）"""
    t = (REFS / "gates" / "14-中文AI痕迹-gate.md").read_text(encoding="utf-8")
    assert "不属「人在环四节点」" in t, "gates/14 未声明 G14 Warning 非人在环四节点（与 pending_owner 挂起口径互不适用）"


def test_t7_5_does_not_depend_on_t8_artifact():
    """P1-6：T7.5 在 T8 之前执行，不得要求读 T8 才产出的 final/M-Gate-Report JSON"""
    t = (REFS / "_shared" / "M-Gate-Algorithm.md").read_text(encoding="utf-8")
    assert "不得依赖 `final/M-Gate-Report-v2.2.12.json`" in t, \
        "M-Gate-Algorithm 的 M-Integrity-2 仍要求读 T8 产物（前后依赖倒置）"
