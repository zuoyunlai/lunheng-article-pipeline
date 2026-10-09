#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工具能力边界参考与 SKILL.md frontmatter 的集合一致性。"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
BOUNDARY = ROOT / "references/_shared/真源/工具能力边界.md"


def _denied_truth() -> set:
    """禁用面完整清单真源（v2.13.5 R-22 外移后不再在 frontmatter）。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cap_assert", ROOT / "scripts" / "capability-assert.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return set(m.TRUTH_DENIED)


def _frontmatter_tools():
    text = SKILL.read_text(encoding="utf-8")
    fm = yaml.safe_load(text.split("---", 2)[1])
    tools = fm["metadata"]["tools"]
    allowed = (set(tools.get("base", []))
               | set(tools.get("coordinator_only", []))
               | set(tools.get("research_extra", []))
               | set(tools.get("academic_extra", [])))  # v2.17.0 学术检索层
    denied = _denied_truth()   # R-22：完整清单已外移，frontmatter 不再承载
    return allowed, denied


def _boundary_tools():
    text = BOUNDARY.read_text(encoding="utf-8")
    section = text.split("### ✅ 可以使用的工具", 1)[1].split("### ❌ 不可以使用的工具", 1)[0]
    # 长名在前：负向前瞻会把短名（如 search_semantic）截在长名内部
    return set(re.findall(
        r"(?<![\w-])(?:"
        r"read_semantic_paper|read_arxiv_paper|read_biorxiv_paper|read_medrxiv_paper|read_by_doi|"
        r"search_semantic_bulk|search_semantic_paper_match|search_semantic_snippets|"
        r"search_semantic_authors|search_google_scholar|search_arxiv|search_biorxiv|"
        r"search_medrxiv|search_pubmed|search_semantic|"
        r"get_semantic_recommendations_for_paper|get_semantic_paper_authors|"
        r"get_semantic_paper_batch|get_semantic_paper_detail|get_semantic_citations|"
        r"get_semantic_references|get_semantic_author_batch|get_semantic_author_detail|"
        r"read|write|edit|web_search|web_fetch|tavily_search|tavily_extract|"
        r"sessions_spawn|sessions_yield|sessions_history|sessions_list|subagents|"
        r"progress_card|session_status|ask_user"
        r")(?![\w-])", section))


def test_boundary_reference_matches_frontmatter_allowed_surface():
    allowed, denied = _frontmatter_tools()
    documented = _boundary_tools()
    assert documented == allowed, f"工具能力边界参考与 frontmatter 不一致：documented-only={documented-allowed}, frontmatter-only={allowed-documented}"
    assert not documented & denied, f"能力边界参考误列 denied 工具：{documented & denied}"
    assert "ask_user" in documented
    assert "sessions_list" in documented


def test_boundary_declares_total_allowed_count():
    text = BOUNDARY.read_text(encoding="utf-8")
    import yaml
    fm = yaml.safe_load(SKILL.read_text(encoding="utf-8").split("---", 2)[1])
    tools = fm["metadata"]["tools"]
    n = sum(len(v) for k, v in tools.items()
            if isinstance(v, (list, tuple)) and k not in ("denied", "denied_high_risk"))
    assert f"允许工具共 {n} 项" in text, f"边界文档计数与 frontmatter 实际允许面不符（应 {n}）"
