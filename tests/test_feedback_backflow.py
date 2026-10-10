#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_feedback_backflow.py — 反哺回灌（v2.18.1）7 条规则的机械锁。

来源：v2.18.0 运行模式冒烟的 `audits/反哺报告-v2.md` §七；主人令「制定修订方案后开始修订」。
本文件锁死七条规则的**文本面存在性**，防后续版本静默回退：
  R-01 工具可达性前提 + 前提不满足唯一处置（dispatch-header）
  R-02 工具选用记录必写调用通道（交接报告模板）
  R-03 taskName ASCII 强制（skill-entry-appendix）
  R-04 判 worker 存活性以实时 subagents list 为准（主动介入机制）
  R-05 判级分歧并列纪律（关键协议）
  R-06 ask_user 降级触发收窄 + no_answer 不等于回退（checkpoint-card-template）
  R-07 宿主工具面要求（QUICKSTART / README）
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
REF = ROOT / "references"


def _t(p):
    return (REF / p).read_text(encoding="utf-8")


def test_r01_reachability_premise_in_dispatch_header():
    t = _t("_shared/真源/dispatch-header.md")
    assert "工具可达性前提" in t, "R-01：dispatch-header 缺工具可达性前提"
    assert "唯一处置" in t, "R-01：缺「前提不满足时唯一处置」"
    assert "capability_excess" in t and "停写" in t, "R-01：缺阻断动作"
    assert "不是授权通道" in t, "R-01：缺「exec 不得作为通道」禁令"


def test_r02_call_channel_required_in_handoff_template():
    t = (ROOT / "references" / "templates" / "交接报告-template.md").read_text(encoding="utf-8")
    assert "call_channel" in t, "R-02：交接报告缺 call_channel 字段"
    assert "code-mode" in t and "direct" in t, "R-02：缺通道枚举"


def test_r03_taskname_ascii_in_spawn_params():
    t = _t("_shared/真源/skill-entry-appendix.md")
    assert "taskName" in t, "R-03：spawn 参数表缺 taskName"
    assert "[a-z][a-z0-9_-]*" in t, "R-03：缺 ASCII 字符集"


def test_r04_live_subagent_list_over_snapshot():
    t = _t("_shared/真源/主动介入机制.md")
    assert "实时" in t and "subagents(action=list)" in t, "R-04：缺「以实时列表为准」"
    assert "快照" in t and "不作判定依据" in t, "R-04：缺快照不可采信口径"


def test_r05_severity_divergence_discipline():
    t = _t("_shared/真源/关键协议.md")
    assert "判级分歧并列纪律" in t, "R-05：关键协议缺判级分歧条款"
    assert "不得择一掩盖" in t, "R-05：缺「不得择一掩盖」"
    assert "更严" in t, "R-05：缺「就绪判定取更严一侧」"


def test_r06_ask_user_degradation_narrowed():
    t = (ROOT / "references" / "templates" / "checkpoint-card-template.md").read_text(encoding="utf-8")
    assert "收窄为三条" in t, "R-06：ask_user 降级未标注收窄"
    assert "no_answer" in t and "不是回退" in t, "R-06：缺「no_answer 不等于回退」"
    assert "不等于" in t, "R-06：缺「无 native 控件不等于不支持」"


def test_r07_host_tool_surface_requirement_documented():
    q = (ROOT / "QUICKSTART.md").read_text(encoding="utf-8")
    assert "宿主工具面要求" in q, "R-07：QUICKSTART 缺宿主工具面要求"
    assert "sessions_yield" in q, "R-07：缺 sessions_yield 降级说明"
    r = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "工具可达性前提" in r, "R-07：README 缺工具可达性前提"


def test_version_and_changelog_reflect_v2181():
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "version: 2.18.1" in skill, "版本未升到 2.18.1"
    cl = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [v2.18.1]" in cl, "CHANGELOG 缺 v2.18.1 章节"
