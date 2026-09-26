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
    allowed = set(tools.get("base", [])) | set(tools.get("coordinator_only", [])) | set(tools.get("research_extra", []))
    denied = _denied_truth()   # R-22：完整清单已外移，frontmatter 不再承载
    return allowed, denied


def _boundary_tools():
    text = BOUNDARY.read_text(encoding="utf-8")
    section = text.split("### ✅ 可以使用的工具", 1)[1].split("### ❌ 不可以使用的工具", 1)[0]
    return set(re.findall(r"(?<![\w-])(?:read|write|edit|web_search|web_fetch|tavily_search|tavily_extract|sessions_spawn|sessions_yield|sessions_history|sessions_list|subagents|progress_card|session_status|ask_user)(?![\w-])", section))


def test_boundary_reference_matches_frontmatter_allowed_surface():
    allowed, denied = _frontmatter_tools()
    documented = _boundary_tools()
    assert documented == allowed, f"工具能力边界参考与 frontmatter 不一致：documented-only={documented-allowed}, frontmatter-only={allowed-documented}"
    assert not documented & denied, f"能力边界参考误列 denied 工具：{documented & denied}"
    assert "ask_user" in documented
    assert "sessions_list" in documented


def test_boundary_declares_total_allowed_count():
    text = BOUNDARY.read_text(encoding="utf-8")
    assert "允许工具共 15 项" in text
