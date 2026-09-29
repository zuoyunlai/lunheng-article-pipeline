#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B3 上下文减负回归门：草稿指针、增量读取和证据保真。"""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_current_draft_sync_declares_pointer_contract():
    node = yaml.safe_load(read("references/_shared/真源/phase-order/current_draft_sync.yaml"))[0]
    contract = node["draft_ref_contract"]
    assert contract["path"] == "drafts/current_draft.md"
    assert {"draft_id", "draft_version", "sha256", "section_manifest", "changed_sections"} <= set(contract["required"])
    assert contract["hash_mismatch"] == "stop_and_request_resync"
    assert "final_assembly" in contract["full_read_exceptions"]


def test_context_metrics_cannot_equate_compression_with_success():
    node = yaml.safe_load(read("references/_shared/真源/phase-order/current_draft_sync.yaml"))[0]
    metrics = set(node["context_metrics"]["required"])
    assert {"raw_input_bytes", "structured_output_bytes", "context_reduction_ratio", "critical_evidence_preserved", "locator_preserved", "false_negative_count"} <= metrics
    assert node["context_metrics"]["compression_is_not_evidence"] is True


def test_protocol_preserves_identifiers_and_incremental_read_boundary():
    text = read("references/_shared/真源/关键协议.md")
    for token in ("draft_id", "draft_version", "section_manifest", "changed_sections", "hash_status", "critical_evidence_preserved", "locator_preserved", "false_negative_count"):
        assert token in text
    for token in ("[Lxx]", "[Dxx]", "[Cxx]", "[图N]", "压缩率高而证据或定位丢失"):
        assert token in text


def test_status_template_exposes_draft_pointer_and_context_metrics():
    text = read("references/templates/status-template.md")
    for token in ("draft_ref（B3）", "section_manifest", "hash_status", "resync", "上下文指标（B3）", "false_negative_count"):
        assert token in text


def test_dispatch_workers_use_pointerized_reading():
    for rel in ("references/dispatch/T6-批判.md", "references/dispatch/T7-审计.md", "references/dispatch/T8-终检.md"):
        text = read(rel)
        assert "draft_id" in text and "draft_version" in text and "sha256" in text
        assert "B3" in text
    assert "仅读取与本任务相关的章节" in read("references/dispatch/T6-批判.md")
    assert "跨章一致性审计才读取全文" in read("references/dispatch/T7-审计.md")
    assert "B3 全文例外" in read("references/dispatch/T8-终检.md")
