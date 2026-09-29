#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B5 运行期状态、路由与 gate telemetry 回归门。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_protocol_defines_event_ledger_and_allowed_events():
    text = read("references/_shared/真源/关键协议.md")
    for token in ("B5 状态事件、路由与 gate telemetry", "control/events/", "event_id:", "worker_dispatched", "write_verified", "delivery_blocked"):
        assert token in text
    assert "不得用事件账本伪造完成" in text


def test_protocol_defines_actual_route_vs_requested_route():
    text = read("references/_shared/真源/关键协议.md")
    for token in ("requested:", "actually_used:", "unavailable:", "fallback_chain:", "degradation_level:"):
        assert token in text
    assert "requested` 不等于 `actually_used`" in text


def test_protocol_defines_gate_telemetry_boundary():
    text = read("references/_shared/真源/关键协议.md")
    for token in ("gate_telemetry:", "current_run:", "cumulative:", "反向注入、构建测试和文档演练不计入"):
        assert token in text
    assert "不得自动删除 gate" in text


def test_status_template_has_runtime_observability_snapshot():
    text = read("references/templates/status-template.md")
    for token in ("三.六、事件、路由与 gate telemetry", "runtime_observability", "event_log", "actually_used", "gate_telemetry"):
        assert token in text


def test_retrieval_dispatches_record_route_truthfully():
    for rel in ("references/dispatch/T1-文献检索.md", "references/dispatch/T2-数据检索.md", "references/dispatch/T3-案例检索.md"):
        text = read(rel)
        for token in ("requested", "actually_used", "unavailable", "fallback_chain", "degradation_level"):
            assert token in text, f"{rel} 缺路由字段 {token}"
        assert "不得把请求工具写成实际使用工具" in text


def test_audit_and_final_dispatches_check_observability():
    for rel in ("references/dispatch/T7-审计.md", "references/dispatch/T8-终检.md"):
        text = read(rel)
        assert "B5" in text
        assert "gate_telemetry" in text or "runtime_observability" in text
