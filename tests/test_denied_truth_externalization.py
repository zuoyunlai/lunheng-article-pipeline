#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R-22：禁用面（denied）声明外移后的真源一致性门（v2.13.5，审计 D3 定案）

口径：
  · 完整清单唯一真源 = references/permissions.md 的「禁用面（denied）唯一真源」块
  · SKILL.md frontmatter 只留 denied_count + denied_high_risk（高危摘录）

硬约束是「**声明完整性与机械校验力不降**」，故本文件锁死：
  1. 真源块可解析、项数 = 104、无重复；
  2. frontmatter 计数 == 真源项数；高危摘录非空、⊆ 真源、且高危类别具名；
  3. frontmatter **不得**重新承载整表（防外移被回滚成双份真源 + 重新吃掉常驻预算）；
  4. 真源缺失 / 围栏未闭合 / 清单为空 ⇒ 加载器必须**抛错**（fail-closed，禁止回落旧快照）；
  5. frontmatter 计数漂移、高危摘录含真源外工具 ⇒ 表面加载器必须抛错。
"""
import importlib.util
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
PERMISSIONS = ROOT / "references" / "permissions.md"
HEADING = "# 🔒 禁用面（denied）唯一真源"
FENCE = chr(96) * 3
HIGH_RISK_MUST = ("exec", "process", "code_execution", "browser",
                  "terminal", "apply_patch", "computer", "secrets")


def _cas():
    spec = importlib.util.spec_from_file_location(
        "cap_assert_r22", ROOT / "scripts" / "capability-assert.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _tools():
    fm = yaml.safe_load(SKILL.read_text(encoding="utf-8").split("---", 2)[1])
    return ((fm.get("metadata") or {}).get("tools") or {})


def test_truth_block_parses_with_104_unique_items():
    truth = _cas().load_denied_truth()
    assert len(truth) == 104, "禁用面真源项数应为 104"
    assert len(set(truth)) == 104, "禁用面真源存在重复项"
    assert "exec" in truth and "firecrawl__firecrawl_search_feedback" in truth


def test_frontmatter_count_matches_truth():
    assert _tools().get("denied_count") == len(_cas().load_denied_truth()) == 104


def test_frontmatter_high_risk_subset_and_named():
    high = {str(x) for x in (_tools().get("denied_high_risk") or [])}
    truth = set(_cas().load_denied_truth())
    assert high, "高危摘录不得为空"
    assert high <= truth, f"高危摘录含真源外工具：{sorted(high - truth)}"
    for t in HIGH_RISK_MUST:
        assert t in high, f"高危摘录缺 {t}（R-22 要求高危类别具名）"


def test_frontmatter_does_not_carry_full_list_again():
    """防回退：把整表塞回 frontmatter = 双份真源 + 重新吃掉常驻预算。"""
    assert "denied" not in _tools(), "frontmatter 又出现 denied 全表键（R-22 外移被回滚？）"
    assert len(SKILL.read_text(encoding="utf-8")) < 9000, "SKILL.md 回涨（R-22 腾出的预算被吃掉）"


# ---------------- fail-closed 反向注入 ----------------

def _write_perms(tmp_path, text):
    p = tmp_path / "permissions.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_loader_fails_closed_when_block_missing(tmp_path):
    p = _write_perms(tmp_path, "# 无真源块的权限文档；正文若干。")
    with pytest.raises(RuntimeError):
        _cas().load_denied_truth(p)


def test_loader_fails_closed_when_fence_not_yaml(tmp_path):
    broken = PERMISSIONS.read_text(encoding="utf-8").replace(FENCE + "yaml", FENCE + "text", 1)
    p = _write_perms(tmp_path, broken)
    with pytest.raises(RuntimeError):
        _cas().load_denied_truth(p)


def test_loader_fails_closed_when_list_empty(tmp_path):
    body = HEADING + chr(10) + chr(10) + FENCE + "yaml" + chr(10) + "denied: []" + chr(10) + FENCE + chr(10)
    p = _write_perms(tmp_path, body)
    with pytest.raises(RuntimeError):
        _cas().load_denied_truth(p)


def test_surface_loader_rejects_count_drift(tmp_path):
    m = _cas()
    skill = tmp_path / "SKILL.md"
    skill.write_text(SKILL.read_text(encoding="utf-8").replace("denied_count: 104", "denied_count: 103", 1),
                     encoding="utf-8")
    with pytest.raises(RuntimeError):
        m.load_permission_surface(skill_md=skill, permissions_md=PERMISSIONS)


def test_surface_loader_rejects_high_risk_outside_truth(tmp_path):
    m = _cas()
    skill = tmp_path / "SKILL.md"
    skill.write_text(SKILL.read_text(encoding="utf-8").replace('"secrets"]', '"secrets", "zz_not_in_truth"]', 1),
                     encoding="utf-8")
    with pytest.raises(RuntimeError):
        m.load_permission_surface(skill_md=skill, permissions_md=PERMISSIONS)
