#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B6 pipeline-doctor 结构化诊断协议回归门。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def test_protocol_defines_doctor_three_state_schema():
    text = read("references/_shared/真源/关键协议.md")
    for token in ("B6 pipeline-doctor 诊断协议", "verdict: blocked | proceed_with_limits | proceed", "blocking_findings:", "warnings:", "evidence:", "required_action:"):
        assert token in text

def test_protocol_keeps_doctor_non_executing_boundary():
    text = read("references/_shared/真源/关键协议.md")
    for token in ("不是 exec", "自动继续机制", "不得替代 M/G 门", "pending_owner_halt"):
        assert token in text

def test_protocol_lists_minimum_diagnostic_checks():
    text = read("references/_shared/真源/关键协议.md")
    for token in ("输入是否齐全", "worker 是否有有效产物", "产物是否 read-back 验证", "T9 是否完成", "主人决策是否明确", "版本/清单是否一致"):
        assert token in text

def test_status_template_exposes_doctor_snapshot():
    text = read("references/templates/status-template.md")
    for token in ("pipeline-doctor 诊断快照", "doctor:", "proceed_with_limits", "blocking_findings", "required_action"):
        assert token in text

def test_t7_t8_dispatches_preserve_doctor_boundary():
    for rel in ("references/dispatch/T7-审计.md", "references/dispatch/T8-终检.md"):
        text = read(rel)
        assert "B6 pipeline-doctor" in text
        assert "blocking_findings" in text
        assert "proceed_with_limits" in text
        assert "不等于质量通过" in text or "不得替代" in text
