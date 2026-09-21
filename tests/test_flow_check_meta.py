#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_flow_check_meta.py — flow-check 规则集元健康度门（v2.12.67，审计 P1-3）

背景（2026-09-21 第三方全量审计 P1-3）：
  flow-check 规则已 43 条，但「每条规则至少有一条负例（反向注入）」从未被机器校验——
  规则新增速度（v2.12.58-66 新增 9 条）远超负例覆盖速度，部分早期规则（1-11）只有
  正向断言或无专项测试。负例缺失 = 规则退化成永真时无人知晓（v2.12.65 P0-1
  「机械门静默放行」同族：门在跑、判据失效、绿灯照常亮）。

本门锁四件事（借鉴 allow_empty 豁免闭合语义）：
  1. 清单完整性（双向对账）：从 flow-check.py 真源（docstring + 内联注释）抽取全部
     规则号，每条必须在 COVERED / DEBT 之一登记——新增规则不登记即红；删规则不清
     登记即红（陈旧登记）。
  2. 引用真实性：COVERED 引用的测试函数必须真实存在于 tests/（防幻影覆盖——
     引用了改名/删除后的测试名 = 覆盖声明失真）。
  3. 豁免闭合：DEBT 条目必须带 ≥12 字符豁免理由（与 build-clawhub-release.sh 的
     allow_empty 最小长度同语义）。
  4. 软棘轮：COVERED 数量只许涨（防「覆盖悄悄退坡」）。

登记纪律：新增 flow-check 规则时，同批在 COVERED（配负例测试）或 DEBT（带理由）
登记；补上负例后把条目从 DEBT 挪入 COVERED，并随迁移上调 COVERED_MIN。
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
FLOW_CHECK = ROOT / "scripts" / "flow-check.py"

# ===== 登记表（v2.12.67 首登：33 covered / 10 debt，共 43 条） =====

# COVERED：规则号 → 负例测试函数名（须真实存在于 tests/，由本文件核对）
COVERED = {
    "6": "test_flow_check_detects_missing_producer",
    "7": "test_duplicate_key_detection_actually_works",
    "12": "test_flow_check_detects_missing_owner_gate_declaration",
    "13": "test_m2_flow_check_detects_missing_terminal",
    "14": "test_m1_flow_check_detects_missing_fingerprint_pair",
    "15": "test_m8_flow_check_detects_missing_audited_artifact_required",
    "16": "test_m3_m5_dual_source_lock_in_flow_check",
    "17": "test_m4_m6_flow_check_dual_lock",
    "18": "test_m4_m6_flow_check_dual_lock",
    "19": "test_m7_m9_flow_check_dual_lock",
    "20": "test_m10_m11_flow_check_dual_lock",
    "20b": "test_m11_figure_embed_lock_reverse_injection",
    "21": "test_m13_m14_flow_check_dual_lock",
    "22": "test_t3_liveness_gate_reverse_injection",
    "23": "test_flow_check_detects_readonly_tier_write_authority",
    "24": "test_r1_exempt_files_must_not_carry_panorama",
    "25": "test_r4_reverse_injection",
    "26": "test_r6_reverse_injection",
    "27": "test_r2_r3_status_template_locks",
    "28": "test_r5_t8_owner_action_list_four_classes",
    "30": "test_s2_flow_check_detects_owner_ghostwriting_fallback",
    "31": "test_s3_flow_check_detects_missing_rule",
    "32": "test_missing_node_kind_reverse_injection",
    "33": "test_selfinvented_decision_value_reverse_injection",
    "34": "test_b12_status_field_reverse_injection",
    "35": "test_p01_m_gate_criterion_field_reverse_injection",
    "36": "test_p11_lite_tier_template_reverse_injection",
    "37": "test_p12_path_boundary_reverse_injection",
    "38": "test_p14_manifest_missing_file_reverse_injection",
    "39": "test_p23_unregistered_danger_reverse_injection",
    "40": "test_p22_provider_side_flip_reverse_injection",
    "41": "test_m13_stale_embedding_clause_reverse_injection",
    "42": "test_rule42_t6_dispatch_reverse_injection",
}

# DEBT：规则号 → 豁免理由（≥12 字符）。债务规则点名登记既有正向证据 + 补负例方向；
#   本登记是「知道自己没测什么」的台账，不是豁免测试的理由。
DEBT = {
    "1": "指向校验（next/after_trigger/after_each/on_fail）：仅端到端正向门（test_flow_check_passes_end_to_end）+ 规则 2/6 负例间接施压同一解析层；『指向不存在节点 ⇒ 必红』专项负例待补。",
    "2": "可达性（孤立节点）：正向断言在位（test_all_paths_reach_quality_gates_before_acceptance 等）；『注入孤儿节点 ⇒ 必红』负例待补。",
    "3": "除终态外须有 next：无专项测试（正向由规则 2 可达性断言部分施压）；『删 next ⇒ 必红』负例待补。",
    "4": "入参类节点 input 声明：仅正向（test_execution_nodes_declare_input_and_output）；『删 input ⇒ 必红』负例待补。",
    "5": "执行类节点 output 声明：仅正向（test_execution_nodes_declare_input_and_output）；『删 output ⇒ 必红』负例待补。",
    "8": "条件节点未触发处置：仅正向（test_conditional_nodes_declare_disposition）；『删 on_not_triggered/degrade ⇒ 必红』负例待补。",
    "9": "初稿→T7 必经 current_draft_sync：仅正向（test_draft_producers_refresh_current_draft_before_t7）；『改道绕过 ⇒ 必红』负例待补。",
    "10": "verdict_scale 四档接线：正向 4 条（tests/test_v21240_adoptions.py）；flow-check 级『档位漂移 ⇒ 必红』负例待补。",
    "11": "Phase 编号唯一性/不回退：仅正向（test_phase_numbering_is_explicit_and_monotonic）；『seq 冲突/回退注入 ⇒ 必红』负例待补。",
    "29": "进度卡映射 + QUICKSTART 指针锁：无专项测试（仅 flow-check 本体判据）；『摘映射段 ⇒ 必红』负例待补。",
    "43": "G15/G16 写作质量门跨载体一致性：正向已测（test_G15_G16_writing_quality_gates_consistency 双载体齐全）；『删 G15 或 G16 ⇒ 必红』负例注入待补。",
}

# 软棘轮下限：已覆盖（负例在位）规则数只许涨。把规则从 COVERED 挪回 DEBT 而不同步
#   下调本值 = 红（防覆盖悄悄退坡）；确属规则删除时随迁移同批下调并给理由。
COVERED_MIN = 33

# 抽取器下限护栏（区别于棘轮：这是抽取器自身健康度——docstring/注释格式被重构导致
#   抽取面静默缩水时，这里先红，避免完整性对账给出「陈旧登记」的误导性报错）
EXTRACTION_FLOOR = 40


def _rule_labels():
    """从 flow-check.py 真源抽取规则号：docstring 行首（1-2 空格 + 数字）+ 内联注释（# N / # Nb）。"""
    src = FLOW_CHECK.read_text(encoding="utf-8")
    doc = src.split('"""')[1]
    labels = set()
    for m in re.finditer(r"^ {1,2}(\d{1,2}[a-z]?)\s", doc, re.M):
        labels.add(m.group(1))
    for m in re.finditer(r"^ *# (\d{1,2}[a-z]?)\s", src, re.M):
        labels.add(m.group(1))
    return labels


def _num_key(label):
    return (int(re.sub(r"[a-z]", "", label)), label)


def _all_test_function_names():
    names = set()
    for p in (ROOT / "tests").glob("test_*.py"):
        for m in re.finditer(r"^def (test_\w+)\(", p.read_text(encoding="utf-8"), re.M):
            names.add(m.group(1))
    return names


def test_rule_extraction_sanity_floor():
    """抽取器下限护栏：抽取面静默缩水（docstring/注释格式重构）先在这里红。"""
    labels = _rule_labels()
    assert len(labels) >= EXTRACTION_FLOOR, (
        f"仅抽到 {len(labels)} 条规则（v2.12.67 登记时为 43）——若 docstring/注释格式"
        f"被重构，请同步修 _rule_labels() 的抽取正则，否则完整性对账会误报「陈旧登记」")


def test_rule_inventory_fully_registered():
    """双向对账：真源规则号与登记表键集精确相等——新规则不登记即红；删规则留陈旧登记即红。"""
    labels = _rule_labels()
    registered = set(COVERED) | set(DEBT)
    unregistered = sorted(labels - registered, key=_num_key)
    stale = sorted(registered - labels, key=_num_key)
    assert not unregistered, (
        f"flow-check 规则未登记覆盖状态（新增规则必须同批登记 COVERED 或 DEBT）：{unregistered}")
    assert not stale, f"登记表含 flow-check 已不存在的规则（陈旧登记，删之）：{stale}"


def test_covered_rules_cite_real_tests():
    """COVERED 引用的测试函数必须真实存在（防幻影覆盖：引用改名/删除后的测试名）。"""
    real = _all_test_function_names()
    phantom = {r: t for r, t in sorted(COVERED.items(), key=lambda kv: _num_key(kv[0]))
               if t not in real}
    assert not phantom, f"COVERED 引用了不存在的测试函数（幻影覆盖）：{phantom}"


def test_debt_reasons_are_closed():
    """DEBT 豁免理由 ≥12 字符（allow_empty 豁免闭合语义：无理由的债务 = 无限期的债务）。"""
    bad = {r: reason for r, reason in sorted(DEBT.items(), key=lambda kv: _num_key(kv[0]))
           if len(reason) < 12}
    assert not bad, f"DEBT 豁免理由缺失或 <12 字符：{bad}"


def test_covered_count_ratchet():
    """软棘轮：COVERED 数量只许涨（覆盖退坡必须显式下调 COVERED_MIN 并给理由）。"""
    assert len(COVERED) >= COVERED_MIN, (
        f"COVERED 仅 {len(COVERED)} 条 < 棘轮下限 {COVERED_MIN}（覆盖退坡；"
        f"若确属规则删除请同批下调 COVERED_MIN 并在提交说明给理由）")
