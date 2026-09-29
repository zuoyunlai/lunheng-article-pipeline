#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B4 机械任务查询化回归门。"""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def test_truth_defines_reconciliation_schema_and_fail_closed_rules():
    text = read("references/_shared/真源/audit-checklist-quickref.md")
    for token in ("mechanical_reconciliation", "citation_reconciliation", "data_reconciliation", "gate_coverage", "version_reconciliation", "false_green_risk"):
        assert token in text
    for token in ("不能只回传一个总数", "机械对账完成后", "不等于整项质量通过"):
        assert token in text

def test_status_has_runtime_reconciliation_snapshot():
    text = read("references/templates/status-template.md")
    for token in ("三.六、机械对账快照", "mechanical_reconciliation", "body_without_card", "unresolved", "generated_views_stale"):
        assert token in text

def test_t7_and_t8_dispatch_require_mechanical_first():
    for rel in ("references/dispatch/T7-审计.md", "references/dispatch/T8-终检.md"):
        text = read(rel)
        assert "B4 机械对账优先" in text
        assert "mechanical_reconciliation" in text
        assert "机械 `pass` 不等于整项质量通过" in text

def test_protocol_preserves_semantic_boundary():
    text = read("references/_shared/真源/关键协议.md")
    assert "mechanical_reconciliation" in text
    assert "机械 `pass` 不得替代" in text

def test_reconciliation_verdict_enum_is_explicit():
    text = read("references/templates/status-template.md")
    for verdict in ("pass | fail | path_or_param_error | not_enabled", "false_green_risk"):
        assert verdict in text

def test_gate_count_truth_is_available_for_mechanical_reconciliation():
    data = yaml.safe_load(read("references/_shared/真源/counts.yaml"))
    assert data["g_checklist_items"] >= 19
    assert data["m_gate_items"]["total"] == 13
