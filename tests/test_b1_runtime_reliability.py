#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B1 回归门：worker 终态、T9 缺位和重要写入完整性。"""
import pathlib
import yaml
ROOT=pathlib.Path(__file__).parent.parent

def read(rel): return (ROOT/rel).read_text(encoding="utf-8")
def load(rel): return yaml.safe_load(read(rel))
def test_worker_terminal_states_are_explicit_and_fail_closed():
 a=load("references/_shared/真源/phase-order/index.yaml")["architecture"]
 assert {"worker_not_started","worker_failed","worker_empty_output","worker_timeout","main_controller_takeover","owner_decision_required","not_executed"} <= set(a["worker_terminal_states"])
 r=a["worker_state_rules"]
 assert r["empty_output_is_success"] is False and r["takeover_preserves_original_role_done"] is False and r["takeover_requires_disclosure"] is True and r["t9_takeover"] == "forbidden"
def test_status_template_records_worker_executor_and_artifact_state():
 t=read("references/templates/status-template.md")
 for x in ("worker 终态","worker_empty_output","实际执行者","产物状态","主控接管不得把原角色记为 `Done`"): assert x in t
def test_t9_missing_review_is_not_replaceable_by_owner():
 n=load("references/_shared/真源/phase-order/t9_review.yaml")[0]; p=n["independence_failure_policy"]; r=n["terminal_state_rules"]
 assert p["executor_takeover"] == "forbidden" and p["on_exhausted"] == "record_missing_and_notify_owner" and p["status_record"] == "missing_blind_review"
 assert r["empty_output_is_success"] is False and r["executor_takeover"] == "forbidden" and r["missing_report_blocks_t9_claims"] is True
def test_t8_cannot_claim_complete_verdict_without_t9_status():
 p=load("references/_shared/真源/phase-order/t8_technical_final.yaml")[0]["t9_missing_review_policy"]
 assert p["missing_blind_review_blocks_t9_claims"] is True and p["owner_acceptance_required_for_limited_delivery"] is True and p["complete_final_verdict_forbidden_without_t9_status"] is True
def test_write_verification_is_structured_and_fail_closed():
 s=read("references/templates/status-template.md"); p=read("references/_shared/真源/关键协议.md")
 for x in ("重要写入验证记录","readback=","anchor_preserved=","unrelated_sections_preserved="): assert x in s
 for x in ("重要写入完整性","append:true","read-back","readback=failed","不得推进状态机"): assert x in p
