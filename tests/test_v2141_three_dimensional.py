#!/usr/bin/env python3
"""v2.14.1 三维优化修订的结构回归门（R-52/R-53/R-56/R-57）。"""
from pathlib import Path

ROOT = Path(__file__).parent.parent
DISPATCH = ROOT / "references" / "dispatch"


def test_all_dispatch_cards_inline_workspace_boundary():
    """R-53：11 张派发卡都必须带同一段 workspace 边界，避免重复读 28KB 协议。"""
    cards = sorted(DISPATCH.glob("*.md"))
    assert len(cards) == 11
    marker = "## 📁 workspace 路径边界（本卡内联，R-53）"
    missing = [p.name for p in cards if marker not in p.read_text(encoding="utf-8")]
    assert not missing, f"dispatch 卡缺 workspace 内联段：{missing}"


def test_dispatch_workspace_boundary_has_required_invariants():
    marker = "## 📁 workspace 路径边界（本卡内联，R-53）"
    required = ("读", "写", "cwd", "..", "run/…/run/…")
    for p in DISPATCH.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        block = text[text.index(marker):]
        for token in required:
            assert token in block, f"{p.name} workspace 内联段缺少 {token!r}"


def test_status_template_has_runtime_gate_trigger_accounting():
    """R-52：触发计数必须成为运行期模板字段，而不是只有方案散文。"""
    text = (ROOT / "references/templates/status-template.md").read_text(encoding="utf-8")
    for token in ("三.六、审计门触发计数", "本轮触发次数", "累计触发次数", "反向注入测试", "裁撤审查"):
        assert token in text


def test_g14_voice_preservation_is_structured():
    """R-56：声音保留反查必须有结构化输出字段。"""
    gate = (ROOT / "references/gates/14-中文AI痕迹-gate.md").read_text(encoding="utf-8")
    report = (ROOT / "references/templates/G14检测报告-template.md").read_text(encoding="utf-8")
    for token in ("声音保留反查", "voice_preservation", "neutralization_signals", "owner_insight_preserved"):
        assert token in gate or token in report


def test_lite_audit_has_sensitivity_matrix():
    """R-57：轻量档裁剪必须按敏感度和具体豁免记账。"""
    text = (ROOT / "references/_shared/真源/audit-checklist-quickref.md").read_text(encoding="utf-8")
    for token in ("轻量档字数敏感度矩阵", "高", "中", "低", "skipped_or_core"):
        assert token in text


def test_chapter_minor_is_consistent_in_truth_and_derived_view():
    """R-55：章节级 minor 口径在交付文档与流程唯一派生视图同时在位。"""
    deliverables = (ROOT / "references/deliverables.md").read_text(encoding="utf-8")
    overview = (ROOT / "references/_shared/真源/pipeline-overview.md").read_text(encoding="utf-8")
    for text in (deliverables, overview):
        assert "章节级 minor" in text
        assert "跨章引用/结论不变" in text
        assert "≤5%" in text
