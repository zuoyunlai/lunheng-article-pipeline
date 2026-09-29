#!/usr/bin/env python3
"""paper-ready-check fail-closed regression matrix."""
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("paper_ready", ROOT / "scripts" / "paper-ready-check.py")
_mod = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mod)


def _load(name):
    p = ROOT / "tests" / "fixtures" / name
    return p.read_text(encoding="utf-8") if p.exists() else ""


def test_missing_and_empty_final_fail_closed(tmp_path):
    missing = tmp_path / "missing.md"
    assert _mod._missing_or_empty(missing)
    empty = tmp_path / "empty.md"; empty.write_text("", encoding="utf-8")
    assert _mod._missing_or_empty(empty)


def test_empty_final_cannot_pass_any_content_check(tmp_path):
    p = tmp_path / "empty.md"; p.write_text("", encoding="utf-8")
    for fn, args in ((_mod.check_front_matter, (str(p),)),
                     (_mod.check_front_matter, (str(p),)),
                     (_mod.check_ai_declaration, (str(p),)),
                     (_mod.check_citation_ordering, (str(p),)),
                     (_mod.check_gbt_types, (str(p),)),
                     (_mod.check_acknowledgment, (str(p),)),
                     (_mod.check_word_count, (str(p), str(tmp_path))),
                     (_mod.check_residual_codes, (str(p),))):
        ok, _ = fn(*args)
        assert not ok, fn.__name__


def test_missing_m_gate_fails_closed(tmp_path):
    ok, detail = _mod.check_m_gate(str(tmp_path))
    assert not ok and detail["error"] == "missing_or_empty_m_gate_report"


def test_empty_m_gate_fails_closed(tmp_path):
    (tmp_path / "final").mkdir(); p = tmp_path / "final" / "M-Gate-Report-v2.2.12.json"
    p.write_text("", encoding="utf-8")
    ok, detail = _mod.check_m_gate(str(tmp_path))
    assert not ok and detail["error"] == "missing_or_empty_m_gate_report"


def test_placeholder_m_gate_fails_closed(tmp_path):
    (tmp_path / "final").mkdir(); p = tmp_path / "final" / "M-Gate-Report-v2.2.12.json"
    p.write_text('{"exit_code":"pending"}', encoding="utf-8")
    ok, detail = _mod.check_m_gate(str(tmp_path))
    assert not ok and detail["placeholder"] is True


def test_no_citations_fails_closed():
    p = ROOT / "tests" / "fixtures" / "missing_citation.md"
    ok, detail = _mod.check_citation_ordering(str(p))
    assert not ok and detail["error"] == "no_citations_in_body"


def test_author_year_citation_passes(tmp_path):
    p = tmp_path / "author_year_paper.md"
    p.write_text(
        "# 标题\n\n正文引用（机构, 2024）。\n\n## 参考文献\n\n- （机构, 2024）\n",
        encoding="utf-8",
    )
    ok, _ = _mod.check_citation_ordering(str(p))
    assert ok
