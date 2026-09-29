#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_b2_evidence_chain.py — B2 证据链闭环回归门（M3/M4/M5）

锁死三件落地痕迹，防后续编辑漂移回旧约定：
  M3 方法契约（method_contract 字段集 + 状态枚举 + 空白/unknown 不得判 present）
  M4 四向证据对账（citation_evidence_reconciliation 差集字段 + ClaimEvidenceLink 回写）
  M5 DOI 分层核验（identifier_check 五级字段 + 语义不相关不得 pass）

判据真源 = references/_shared/真源/方法论-审计清单.md；接线面 = T4/T5/T7/T8 角色卡与派发。
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


# 真源 + 接线面（缺任一即该条落地不完整）
TRUTH = "references/_shared/真源/方法论-审计清单.md"
WIRED = {
    "references/agents/04-分析-analyst.md": ("method_contract", "not_applicable_with_reason"),
    "references/agents/05-写作-writer.md": ("method_contract_status", "§4_contract_complete"),
    "references/agents/07-审计-auditor.md": ("citation_evidence_reconciliation", "identifier_check"),
    "references/agents/08-终检-final-inspector.md": ("citation_evidence_reconciliation", "identifier_check"),
    "references/dispatch/T4-分析.md": ("method_contract", "sampling_frame"),
    "references/dispatch/T5-写手.md": ("method_contract", "not_applicable_with_reason"),
    "references/dispatch/T7-审计.md": ("citation_evidence_reconciliation", "identifier_check"),
    "references/dispatch/T8-终检.md": ("citation_evidence_reconciliation", "identifier_check"),
}

M3_FIELDS = (
    "research_question", "design", "sample_or_corpus", "sampling_frame",
    "inclusion_exclusion", "variables_or_categories", "analysis_method",
    "limitations", "ethics_or_data_access", "reproducibility_boundary",
)

M4_KEYS = (
    "body_without_card", "card_without_body", "claim_without_link",
    "link_without_evidence", "unavailable_overclaim",
    "counter_evidence_unhandled", "verdict",
)

M5_KEYS = (
    "syntax", "resolves", "metadata_match", "semantic_match",
    "checked_sources", "verdict",
)


def test_m3_method_contract_fields_in_truth():
    t = _read(TRUTH)
    for f in M3_FIELDS:
        assert f in t, f"真源缺 method_contract 字段：{f}"
    for token in ("not_applicable_with_reason", "unknown", "unverified"):
        assert token in t, f"真源缺状态枚举：{token}"
    assert "空白不等于完成" in t or "不得判为" in t, "真源缺「空白不得判完成」规则"


def test_m4_reconciliation_keys_in_truth():
    t = _read(TRUTH)
    for k in M4_KEYS:
        assert k in t, f"真源缺 citation_evidence_reconciliation 字段：{k}"
    for token in ("正文引用 → 来源卡", "ClaimEvidenceLink → 证据对象"):
        assert token in t, "真源缺四向对账方向声明"


def test_m5_identifier_check_keys_in_truth():
    t = _read(TRUTH)
    for k in M5_KEYS:
        assert k in t, f"真源缺 identifier_check 字段：{k}"
    for token in ("semantic_match", "needs_review", "主题不相关"):
        assert token in t, "真源缺 DOI 语义核验规则"


def test_wired_surfaces_carry_b2_tokens():
    for rel, markers in WIRED.items():
        p = ROOT / rel
        assert p.is_file(), f"B2 接线清单指向不存在文件：{rel}"
        text = _read(rel)
        for m in markers:
            assert m in text, f"{rel} 缺标记：{m}"


def test_no_wired_surface_was_missed():
    # T4/T5/T7/T8 的 4 张角色卡 + 4 张派发都必须接线
    expected = {
        "references/agents/04-分析-analyst.md",
        "references/agents/05-写作-writer.md",
        "references/agents/07-审计-auditor.md",
        "references/agents/08-终检-final-inspector.md",
        "references/dispatch/T4-分析.md",
        "references/dispatch/T5-写手.md",
        "references/dispatch/T7-审计.md",
        "references/dispatch/T8-终检.md",
    }
    assert set(WIRED) == expected, f"接线清单漂移：{set(WIRED) ^ expected}"


def test_injection_removing_semantic_match_is_caught():
    """从真源抽掉 semantic_match ⇒ 校验器报红（防 M5 语义核验被静默删回旧约定）。"""
    import shutil
    import tempfile
    d = pathlib.Path(tempfile.mkdtemp())
    dst = d / "methodology.md"
    src = (ROOT / TRUTH).read_text(encoding="utf-8")
    assert "semantic_match" in src
    dst.write_text(src.replace("semantic_match", "match_placeholder"), encoding="utf-8")
    t = dst.read_text(encoding="utf-8")
    missing = [k for k in M5_KEYS if k not in t]
    assert "semantic_match" in missing, "抽掉 semantic_match 未被检出"
    shutil.rmtree(d)


def test_injection_removing_claim_without_link_is_caught():
    """从真源抽掉 claim_without_link ⇒ 校验器报红（防 M4 回写否决项被删）。"""
    import shutil
    import tempfile
    d = pathlib.Path(tempfile.mkdtemp())
    dst = d / "methodology.md"
    src = (ROOT / TRUTH).read_text(encoding="utf-8")
    assert "claim_without_link" in src
    dst.write_text(src.replace("claim_without_link", "link_placeholder", 1), encoding="utf-8")
    t = dst.read_text(encoding="utf-8")
    missing = [k for k in M4_KEYS if k not in t]
    assert "claim_without_link" in missing, "抽掉 claim_without_link 未被检出"
    shutil.rmtree(d)


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  ✓ {fn.__name__}")
        except Exception:
            failed += 1
            print(f"  ✗ {fn.__name__}")
            traceback.print_exc()
    print(f"{len(fns) - failed} passed, {failed} failed")
    raise SystemExit(1 if failed else 0)
