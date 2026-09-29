#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B7 图注、方向纠偏和主人通知边界回归门。"""
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parent.parent

def read(rel): return (ROOT / rel).read_text(encoding="utf-8")
def test_b7_protocol_defines_caption_direction_and_notification_boundaries():
 t=read("references/_shared/真源/关键协议.md")
 for x in ("B7 质量与人机交互收尾","组装后图注复检","direction_correction","owner_notified","owner_acknowledged"):
  assert x in t
def test_status_has_structured_b7_snapshot():
 t=read("references/templates/status-template.md")
 for x in ("B7 质量与人机交互摘要","g14_caption_recheck","caption_scope","direction_decision","recorded_in_status","owner_acknowledged"):
  assert x in t
def test_final_assembly_caption_recheck_remains_required():
 n=yaml.safe_load(read("references/_shared/真源/phase-order/final_assembly.yaml"))[0]
 assert "g14_caption_recheck" in n["post_assembly_checks"]
 assert n["post_assembly_recheck"] == "required"
 assert "未登记新主张" in n["note"]
def test_phase35_direction_correction_contract_is_preserved():
 n=yaml.safe_load(read("references/_shared/真源/phase-order/phase3_5_insight.yaml"))[0]
 assert set(n["decisions"]) == {"insight","direction_correction","no_insight"}
 assert "correction_scope" in n["decision_contract"]
def test_no_auto_push_or_auto_continue_boundary():
 t=read("references/_shared/真源/关键协议.md")
 assert "不新增 webhook、terminal fallback、自动推送或自动继续" in t
