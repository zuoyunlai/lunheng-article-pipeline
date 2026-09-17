#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_flow_check.py — 流程图真源结构测试（v2.12.30 新增）

背景（2026-09-12 第三方全量审计 P0-2 / P0-3）：
  - P0-2：phase-order.yaml 的 t6_g14 有**两个 output 键**，YAML 后键静默覆盖前键 →
          G14 报告路径被丢弃，纯字符串解析的 flow-check 仍 PASS。
  - P0-3：drafts/current_draft.md 被 T6/T7/T9 消费，但**全仓无节点声明生产它**，
          且审计修订回环不重写它 → 主控漏做即「集体无输入」。

本测试锁死：真源可解析（无重复键）/ 多产物映射完整 / 被多方消费的产物有生产者 / 全门绿。
"""
import importlib.util
import pathlib

import yaml

ROOT = pathlib.Path(__file__).parent.parent
YAML_PATH = ROOT / "references" / "_shared" / "phase-order.yaml"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FC = _load(ROOT / "scripts" / "flow-check.py", "flow_check")


def _pipeline():
    return yaml.load(YAML_PATH.read_text(encoding="utf-8"),
                     Loader=FC.UniqueKeyLoader)


def _node(pid):
    return [n for n in _pipeline()["pipeline"] if n["id"] == pid][0]


def test_condition_names_have_canonical_definitions():
    """审计 P1：每个 condition 必须在 phase-order 顶层 condition_definitions 中有定义。"""
    data = _pipeline()
    defs = data.get("condition_definitions") or {}
    assert defs, "phase-order.yaml 缺 condition_definitions"
    missing = [n["id"] for n in data["pipeline"]
               if n.get("condition") and n.get("condition") not in defs]
    assert not missing, f"节点引用未定义 condition: {missing}"


def test_all_paths_pass_through_human_checkpoints():
    """人在环：Phase 0 → Phase 5 验收的每条路径都必须经过四个主人决策节点。"""
    data = _pipeline()
    by = {n["id"]: n for n in data["pipeline"]}
    owners = set(data.get("owner_checkpoints") or [])
    assert owners == {"phase0_definition", "phase2_5_outline", "phase3_5_insight", "phase5_acceptance"}, \
        f"人在环节点集被改动: {sorted(owners)}"
    succ = {}
    for n in data["pipeline"]:
        out = []
        for k in ("next", "after_trigger", "on_fail"):
            v = n.get(k)
            if isinstance(v, str) and v in by:
                out.append(v)
        succ[n["id"]] = out
    paths = []
    def walk(x, path, seen):
        if x in seen:
            return
        path = path + [x]
        seen = seen | {x}
        if x == "phase5_acceptance":
            paths.append(path)
            return
        for y in succ[x]:
            walk(y, path, seen)
    walk("phase0_definition", [], set())
    assert paths, "不可达 Phase 5 验收"
    bad = [p for p in paths if not owners.issubset(p)]
    assert not bad, "存在绕过人在环节点的路径: " + " -> ".join(bad[0])
    for n in data["pipeline"]:
        if n.get("kind") == "owner_checkpoint":
            assert n.get("decisions"), f"{n['id']} 缺 decisions 枚举（不得空手推进）"


def test_phase_numbering_is_explicit_and_monotonic():
    """v2.12.46：Phase 编号为第一类真源字段 —— 每节点声明 phase/phase_seq，唯一且沿前向边不回退。"""
    data = _pipeline()
    P = data["pipeline"]
    order = data.get("phase_order") or []
    assert order, "phase-order.yaml 缺顶层 phase_order 编号表"
    seq = {}
    for n in P:
        assert n.get("phase"), f"{n['id']} 缺 phase"
        assert isinstance(n.get("phase_seq"), int), f"{n['id']} 缺 phase_seq"
        seq[n["id"]] = n["phase_seq"]
    assert len(set(seq.values())) == len(seq), "phase_seq 必须唯一"
    assert {e["node"] for e in order} == set(seq), "phase_order 与 pipeline 节点集不一致"
    for e in order:
        assert e["seq"] == seq[e["node"]], f"phase_order[{e['node']}] seq 与节点声明不一致"
        assert e["phase"] == _node(e["node"])["phase"], f"phase_order[{e['node']}] 标签与节点声明不一致"
    for n in P:
        for k in ("next", "after_trigger", "on_fail"):
            v = n.get(k)
            if isinstance(v, str) and v in seq:
                assert seq[v] >= seq[n["id"]], f"{n['id']}.{k}->{v} 序号回退"


def test_architecture_is_multi_agent_role_pipeline():
    """v2.12.46 定案：论衡只有一个标准架构 = 多 Agent 九角色流水线，不设总开关。"""
    arch = _pipeline().get("architecture") or {}
    assert arch.get("standard") == "multi_agent_role_pipeline"
    assert arch.get("worker_failure_policy") == "owner_takeover_with_disclosure"
    assert arch.get("fallback_is_not_equivalent") is True
    assert set(arch.get("worker_roles") or []) == {
        "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T9", "G14"}
    raw = YAML_PATH.read_text(encoding="utf-8")
    assert "executor_by_mode" not in raw, "旧 executor_by_mode 并列模式语义复活"
    assert "single_controller" not in raw, "旧 single_controller 并列模式语义复活"


def test_every_worker_node_declares_role_writability_and_takeover():
    """worker 节点必须声明角色、写入权、核验权与失败接管策略（节点级接管，非整轮降级）。"""
    missing = []
    for n in _pipeline()["pipeline"]:
        if n.get("kind") in {"agent", "parallel_agents", "conditional_agent", "advisory_agent"}:
            if not n.get("role") or n.get("write_authority") != "executor":
                missing.append(f"{n['id']}.role/write_authority")
            if n.get("verification_authority") != "主控":
                missing.append(f"{n['id']}.verification_authority")
            takeover = n.get("on_worker_failure") or {}
            if takeover.get("executor") != "主控" or takeover.get("disclosure") != "degraded_executor":
                missing.append(f"{n['id']}.on_worker_failure")
    assert not missing, f"worker 节点声明缺失: {missing}"


def test_role_artifacts_are_executor_written_and_owner_artifacts_are_owner_written():
    """角色产物由角色写（T5 就是写手）；权威汇总产物只由主控节点生产。"""
    byid = {n["id"]: n for n in _pipeline()["pipeline"]}
    for pid in ("current_draft_sync", "final_assembly", "pre_spawn_enforcement"):
        n = byid[pid]
        assert n.get("write_authority") == "owner", f"{pid} 应为 owner 写入权"
    assert byid["t8_technical_final"].get("kind") == "owner_agent"
    # T5 = 正式写手：初稿/修订稿必须由 T5 角色直接落盘
    for pid in ("t5_draft_v1", "t5_feedback_revision", "t5_style_revision"):
        assert byid[pid].get("role") == "T5" and byid[pid].get("write_authority") == "executor", \
            f"{pid} 未保留 T5 写手落盘职责"
    producers = [n["id"] for n in _pipeline()["pipeline"]
                 if "final/定稿.md" in FC._paths(n.get("output"))]
    assert producers == ["final_assembly"], f"final/定稿.md 生产者异常: {producers}"


def test_all_paths_reach_quality_gates_before_acceptance():
    """P0：任意模式路径都必须经过 T7、T7.5、T8 和 Phase 5，禁止 fallback 直达终态。"""
    data = _pipeline(); by = {n["id"]: n for n in data["pipeline"]}
    required = {"t7_audit", "t7_5_integrity", "t8_technical_final", "phase5_acceptance"}
    successors = {}
    for n in data["pipeline"]:
        out = []
        for key in ("next", "after_trigger", "on_fail", "on_not_triggered"):
            v = n.get(key)
            if isinstance(v, str) and v in by: out.append(v)
        successors[n["id"]] = out
    terminals = []
    def walk(node, seen, path):
        if node in seen: return
        seen = seen | {node}; path = path + [node]
        if node == "phase5_acceptance": terminals.append(path); return
        for nxt in successors[node]: walk(nxt, seen, path)
    walk("phase0_definition", set(), [])
    assert terminals, "从 Phase 0 不可达 Phase 5"
    bad = [p for p in terminals if not required.issubset(p)]
    assert not bad, "存在绕过质量门的路径: " + " -> ".join(bad[0])


def test_methodology_snapshot_is_explicit_opt_in():
    """审计 P0-2：快照只能由独立 opt-in 节点生成。"""
    n = _node("methodology_snapshot")
    assert n.get("condition") == "methodology_snapshot_opt_in"
    assert n.get("on_not_triggered") == "record_not_triggered_in_status"
    assert n.get("output") == "run/<项目名>/audits/methodology-footprint-{项目名}.md"


def test_phase_order_has_no_duplicate_keys():
    """真源不得有重复键（重复键 = 后键静默覆盖，真源失真）"""
    _pipeline()  # 解析失败即抛 ConstructorError


def test_duplicate_key_detection_actually_works():
    """反向断言：重复键必须被检出（防加载器退化成静默覆盖）"""
    bad = "pipeline:\n  - id: a\n    output: x\n    output: y\n"
    try:
        yaml.load(bad, Loader=FC.UniqueKeyLoader)
    except yaml.YAMLError:
        return
    raise AssertionError("重复键未被检出 —— 加载器退化")


def test_t6_g14_output_keeps_both_products():
    """P0-2 回归（v2.12.40 A1 迁移后）：T6 / G14 产物路径分由 t6_critique / g14_style_gate 声明"""
    ids = {n["id"] for n in _pipeline()["pipeline"]}
    assert "t6_g14" not in ids, "旧合并节点 t6_g14 复活（A1 已拆为 t6_critique + g14_style_gate）"
    t6 = str(_node("t6_critique").get("output", ""))
    assert t6.startswith("analysis/"), f"T6 批判报告路径丢失: {t6}"
    g14 = str(_node("g14_style_gate").get("output", ""))
    assert g14.startswith("audits/"), f"G14 检测报告路径丢失: {g14}"


def test_current_draft_has_producer():
    """P0-3 回归：drafts/current_draft.md 必须有节点声明生产"""
    produced = set()
    for n in _pipeline()["pipeline"]:
        produced |= FC._paths(n.get("output"))
    assert "drafts/current_draft.md" in produced, \
        "drafts/current_draft.md 无生产者（消费者会读到不存在/过期文件）"


def test_current_draft_refreshed_in_revision_loop():
    """P0-3 回归：审计修订回环每轮必须重写 current_draft.md"""
    after = _node("audit_revision").get("after_each") or []
    assert "current_draft_sync" in after, \
        f"audit_revision.after_each 缺 current_draft_sync: {after}"


def test_execution_nodes_declare_input_and_output():
    """执行类节点必须同时声明 input 与 output（防「有消费无生产」）"""
    missing = []
    for n in _pipeline()["pipeline"]:
        if n.get("kind") in FC.EXEC_KINDS:
            for key in ("input", "output"):
                if not n.get(key):
                    missing.append(f"{n['id']}.{key}")
    assert not missing, f"执行类节点缺声明: {missing}"


def test_flow_check_passes_end_to_end():
    """flow-check.py 端到端 exit 0（当前真源无断链/孤立/缺声明/无生产者）"""
    import os
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        assert FC.main() == 0
    finally:
        os.chdir(cwd)


def test_all_managed_inputs_have_producers():
    """v2.12.37 审计 P0-3/P1-1/P1-2：**每个被消费的受管路径**都必须有生产者。

    旧口径要求「被 ≥2 节点消费」才检查 → 单消费者路径全部逃检
    （实测漏掉 analysis/T5-写作上下文.md 与 final/定稿.md）。
    """
    P = _pipeline()["pipeline"]
    produced = set()
    for n in P:
        produced |= FC._paths(n.get("output"))
        produced |= FC._paths(n.get("output_if_triggered"))
    # 目录型产物覆盖其下通配消费（v2.12.41：与 scripts/flow-check.py 规则6 对齐 —— DIR_RE + 前缀匹配）
    dirs = sorted({t for t in produced if t.endswith('/')})
    orphan = []
    for n in P:
        for key in ("input", "inputs"):
            for t in FC._paths(n.get(key)):
                if t in produced:
                    continue
                if any(t.startswith(d) for d in dirs):
                    continue
                orphan.append(f"{n['id']}.{key}:{t}")
    assert not orphan, f"有消费者无生产者的受管路径: {sorted(set(orphan))}"


def test_conditional_nodes_declare_disposition():
    """v2.12.37 审计 P1-3：条件节点必须给出未触发处置，否则「未触发」与「漏跑」不可分。"""
    missing = []
    for n in _pipeline()["pipeline"]:
        if n.get("condition") and not (
                n.get("on_not_triggered") or n.get("degrade") or n.get("decisions")):
            missing.append(n["id"])
    assert not missing, f"条件节点缺未触发处置: {missing}"


def test_draft_producers_refresh_current_draft_before_t7():
    """v2.12.37 审计 P0-2：产出初稿的节点到 t7_audit 的路径必须经过 current_draft_sync。

    回归对象：t5_feedback_revision（Phase 3.7）曾直连 t7_audit，
    导致 T6/G14 触发的修订自动逃过 T7 审计。
    """
    after = _node("t5_feedback_revision").get("after_each") or []
    assert "current_draft_sync" in after, \
        f"t5_feedback_revision.after_each 缺 current_draft_sync: {after}"


def test_final_manuscript_has_producer():
    """v2.12.37 审计 P0-3：final/定稿.md 必须有节点声明生产（否则续跑核对永远漏掉它）。"""
    produced = set()
    for n in _pipeline()["pipeline"]:
        produced |= FC._paths(n.get("output"))
    assert "final/定稿.md" in produced, "final/定稿.md 无生产者"


def test_t8_declares_review_report_input():
    """v2.12.37 审计 P1-2：T8 需读 T9 报告做建议分流，必须声明该输入。"""
    n = _node("t8_technical_final")
    decl = " ".join(str(n.get(k) or "") for k in ("input", "inputs"))
    assert "审稿报告" in decl, f"t8_technical_final 未声明审稿报告输入: {decl}"


def test_flow_check_detects_missing_producer():
    """反向注入：无生产者的单消费者路径必须被检出（防新规则退化成永真）。"""
    import tempfile
    import os
    p = YAML_PATH  # 绝对路径（v2.12.39 修：原相对路径依赖 CWD，属顺序依赖的脆弱测试）
    src = p.read_text(encoding="utf-8")
    # 移除 final_assembly 节点的 output 声明 → 制造 final/定稿.md 无生产者
    marker = "  - id: final_assembly"
    start = src.index(marker)
    end = src.find("\n  - id:", start + len(marker))
    block = src[start:] if end < 0 else src[start:end]
    assert "    output: final/定稿.md\n" in block, "反向注入点未命中（final_assembly.output 写法已变）"
    bad_block = block.replace("    output: final/定稿.md\n", "", 1)
    bad = src[:start] + bad_block + src[start + len(block):]
    backup = src
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        p.write_text(bad, encoding="utf-8")
        out = []
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = FC.main()
        out = buf.getvalue()
        assert rc != 0, "反向注入未被检出 —— 入参链闭合规则退化"
        assert "final/定稿.md" in out, f"报错未指向 final/定稿.md: {out}"
    finally:
        p.write_text(backup, encoding="utf-8")
        os.chdir(cwd)


def test_owner_checkpoints_declare_gate_semantics():
    """v2.12.49（修 P2-1）：人环闸门的阻断语义必须落在真源字段上，而不只活在散文。"""
    data = _pipeline()
    otp = data.get("owner_timeout_policy") or {}
    fb_kinds = otp.get("fallback_kinds") or {}
    assert fb_kinds, "缺 owner_timeout_policy.fallback_kinds"
    assert otp.get("default_fallback") in fb_kinds, "default_fallback 未在 fallback_kinds 定义"
    ck = [n for n in data["pipeline"] if n.get("kind") == "owner_checkpoint"]
    assert {n["id"] for n in ck} == set(data.get("owner_checkpoints") or []), \
        "顶层 owner_checkpoints 与 kind: owner_checkpoint 节点集不一致"
    for n in ck:
        assert n.get("blocking") is True, f"{n['id']} 未声明 blocking: true（人环闸门可被静默绕过）"
        assert n.get("owner_visible") is True, f"{n['id']} 未声明 owner_visible: true"
        assert n.get("decisions"), f"{n['id']} 缺 decisions 枚举"
        assert n.get("timeout_fallback") in fb_kinds, \
            f"{n['id']}.timeout_fallback 未在 fallback_kinds 中定义: {n.get('timeout_fallback')}"


def test_owner_timeout_policy_is_single_source():
    """v2.12.49（修 P3-1）：无应答分钟数只在 phase-order.yaml 定义，docs 层不得重列。"""
    data = _pipeline()
    assert isinstance(data["owner_timeout_policy"]["no_answer_minutes"], int)
    assert data["owner_timeout_policy"]["no_answer_minutes"] > 0
    for rel in ("references/_shared/glossary-full.md",
                "references/_shared/phase-2-details.md",
                "references/_shared/执行韧化协议-design.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "60 分钟" not in text, f"{rel} 重列了无应答分钟数（违一条款一真源）"


def test_phase5_silence_is_not_acceptance():
    """v2.12.49（修 P2-2）：已删除「Phase 5 不答 = 接受当前定稿」——不得回潮。

    允许出现的唯一情形：出现在「已删除 / 旧写法」语境里（防回潮登记）。
    任何一行把它当仍生效的口径陈述，即判失败。
    """
    raw = YAML_PATH.read_text(encoding="utf-8")
    n = _node("phase5_acceptance")
    assert n.get("timeout_fallback") == "pending_owner_halt", \
        "Phase 5 又变成 fail-open（静默自动接受）"
    DELETED_MARKERS = ("已删除", "旧写法", "旧口径", "防回潮", "已收紧")
    for rel in ("references/_shared/glossary-full.md",
                "references/agents/00-主控-扩展职责.md"):
        for i, line in enumerate((ROOT / rel).read_text(encoding="utf-8").splitlines(), 1):
            if "不答 = 接受当前定稿" in line:
                assert any(m in line for m in DELETED_MARKERS), \
                    f"{rel}:{i} 把旧 fail-open 口径当仍生效口径陈述"
    assert "已删除的旧语义" in raw, "真源未登记被删除的 fail-open 口径（防回潮缺口）"


def test_flow_check_detects_missing_owner_gate_declaration():
    """反向注入：owner_checkpoint 缺 blocking: true 必须被规则 12 检出（防新规则退化成永真）。"""
    import contextlib
    import io
    import os
    src = YAML_PATH.read_text(encoding="utf-8")
    marker = "  - id: phase5_acceptance"
    start = src.index(marker)
    block = src[start:]
    lines = block.splitlines(keepends=True)
    kept = [ln for ln in lines if not ln.lstrip().startswith("blocking: true")]
    assert len(kept) == len(lines) - 1, "反向注入点未命中（phase5_acceptance 的 blocking 写法已变）"
    bad = src[:start] + "".join(kept)
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        YAML_PATH.write_text(bad, encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = FC.main()
        out = buf.getvalue()
        assert rc != 0, "反向注入未被检出 —— 人环闸门规则退化"
        assert "phase5_acceptance" in out, f"报错未指向 phase5_acceptance: {out}"
    finally:
        YAML_PATH.write_text(src, encoding="utf-8")
        os.chdir(cwd)


# ===== v2.12.49 M-1 交付物指纹 =====

def test_m1_fingerprint_required_nodes_declared():
    """M-1：final_assembly / t9_review / t8_technical_final 三节点必须声明 fingerprint: required。"""
    data = _pipeline()
    fp_required = {n["id"] for n in data["pipeline"] if n.get("fingerprint") == "required"}
    assert {"final_assembly", "t9_review", "t8_technical_final"} <= fp_required, \
        f"fingerprint: required 节点集不足: {fp_required}"


def test_m1_audited_artifact_field_required_in_templates():
    """M-1：交接报告 + 审稿报告模板头部必填 audited_artifact 三元组。"""
    for rel in ("references/templates/交接报告-template.md",
                "references/templates/审稿报告-template.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "audited_artifact" in text, f"{rel} 缺 audited_artifact 字段"
        assert all(k in text for k in ("path", "bytes", "sha256")), \
            f"{rel} audited_artifact 三元组（path/bytes/sha256）不全"


def test_m1_flow_check_detects_missing_fingerprint_pair():
    """反向注入：final_assembly 声明 fingerprint 但 t8 未同步 ⇒ 规则 13 检出。"""
    import contextlib, io, os
    src = YAML_PATH.read_text(encoding="utf-8")
    marker = "  - id: t8_technical_final"
    start = src.index(marker)
    # 取该节点块（约 12 行）
    lines = src[start:].splitlines(keepends=True)
    end = next((i for i, ln in enumerate(lines)
                if i > 3 and (ln.startswith("  - id:") or ln.startswith("- id:"))), len(lines))
    block = lines[:end]
    kept = [ln for ln in block if not ln.lstrip().startswith("fingerprint:")]
    bad = src[:start] + "".join(kept) + src[start + sum(len(x) for x in lines[:end]):]
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        YAML_PATH.write_text(bad, encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = FC.main()
        out = buf.getvalue()
        assert rc != 0, "反向注入未被检出 —— M-1 指纹同步规则退化"
        assert "t8_technical_final" in out, f"报错未指向 t8_technical_final: {out}"
    finally:
        YAML_PATH.write_text(src, encoding="utf-8")
        os.chdir(cwd)


# ===== v2.12.49 M-2 终态冻结 =====

def test_m2_terminal_freeze_top_level_declared():
    """M-2：顶层 terminal_freeze 块必须存在且包含 protected_paths / freeze_state / reopen_required_gates。"""
    tf = _pipeline().get("terminal_freeze") or {}
    assert tf, "phase-order.yaml 缺顶层 terminal_freeze 段（M-2 必填）"
    assert tf.get("freeze_state") == "accepted"
    assert "final/" in tf.get("protected_paths", [])
    assert "drafts/current_draft.md" in tf.get("protected_paths", [])
    assert "g14_style_gate" in tf.get("reopen_required_gates", [])
    assert tf.get("rerun_after_post_acceptance") is True


def test_m2_phase5_acceptance_declares_terminal():
    """M-2：phase5_acceptance 节点必须声明 terminal: accepted（终态真源）。"""
    assert _node("phase5_acceptance").get("terminal") == "accepted", \
        "phase5_acceptance 未声明 terminal: accepted（M-2 终态真源缺失）"


def test_m2_g14_style_gate_has_rerun_after_post_acceptance():
    """M-2：g14_style_gate 必须声明 rerun_after_post_acceptance: true（终态后修改必重跑）。"""
    g14 = _node("g14_style_gate")
    assert g14.get("rerun_after_post_acceptance") is True, \
        "g14_style_gate 未声明 rerun_after_post_acceptance: true（M-2：跨终态修改 G14 必重跑）"


def test_m2_flow_check_detects_missing_terminal():
    """反向注入：phase5_acceptance 缺 terminal ⇒ 规则 13 检出。"""
    import contextlib, io, os
    src = YAML_PATH.read_text(encoding="utf-8")
    marker = "  - id: phase5_acceptance"
    start = src.index(marker)
    lines = src[start:].splitlines(keepends=True)
    end = next((i for i, ln in enumerate(lines)
                if i > 3 and (ln.startswith("  - id:") or ln.startswith("- id:"))), len(lines))
    block = lines[:end]
    kept = [ln for ln in block if not ln.lstrip().startswith("terminal:")]
    bad = src[:start] + "".join(kept) + src[start + sum(len(x) for x in lines[:end]):]
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        YAML_PATH.write_text(bad, encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = FC.main()
        out = buf.getvalue()
        assert rc != 0, "反向注入未被检出 —— M-2 终态规则退化"
        assert "terminal" in out, f"报错未指向 terminal: {out}"
    finally:
        YAML_PATH.write_text(src, encoding="utf-8")
        os.chdir(cwd)


# ===== v2.12.49 M-8 审计对象一致 =====

def test_m8_audited_artifact_required_on_critical_nodes():
    """M-8：t7_5_integrity / t8_technical_final / t9_review 必须声明 audited_artifact_required: true。"""
    required = {"t7_5_integrity", "t8_technical_final", "t9_review"}
    missing = sorted(nid for nid in required if not _node(nid).get("audited_artifact_required"))
    assert not missing, f"以下节点缺 audited_artifact_required: true（M-8）：{missing}"


def test_m8_flow_check_detects_missing_audited_artifact_required():
    """反向注入：t7_5_integrity 缺 audited_artifact_required ⇒ 规则 15 检出。"""
    import contextlib, io, os
    src = YAML_PATH.read_text(encoding="utf-8")
    marker = "  - id: t7_5_integrity"
    start = src.index(marker)
    lines = src[start:].splitlines(keepends=True)
    end = next((i for i, ln in enumerate(lines)
                if i > 3 and (ln.startswith("  - id:") or ln.startswith("- id:"))), len(lines))
    block = lines[:end]
    kept = [ln for ln in block if not ln.lstrip().startswith("audited_artifact_required:")]
    bad = src[:start] + "".join(kept) + src[start + sum(len(x) for x in lines[:end]):]
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        YAML_PATH.write_text(bad, encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = FC.main()
        out = buf.getvalue()
        assert rc != 0, "反向注入未被检出 —— M-8 审计一致规则退化"
        assert "audited_artifact_required" in out, f"报错未指向 audited_artifact_required: {out}"
    finally:
        YAML_PATH.write_text(src, encoding="utf-8")
        os.chdir(cwd)


# ===== v2.12.49 M-3 / M-5 计数档位真源 + P2 量化锚点 =====

def test_m3_counting_uses_band_not_exact():
    """M-3：07-审计 G8 必须报「档位」不得报「精确数」；字数判定表 5% 粒度与档位表达一致。"""
    auditor = (ROOT / "references/agents/07-审计-auditor.md").read_text(encoding="utf-8")
    assert "T7 仅报档位" in auditor or "T7 **仅报档位**" in auditor, \
        "07-审计 G8 未声明 T7 仅报档位（M-3）"
    assert "T8 终检或主人在 host shell" in auditor, \
        "07-审计 G8 未声明精确值唯一出口（M-3）"


def test_m5_p2_quantitative_anchors_declared():
    """M-5：字数判定表 §二 + M-Gate-Algorithm §🎯 必须同时声明 P2 量化锚点（3 倍 / 1.5 倍 / 累积升级）。"""
    wz = (ROOT / "references/_shared/字数判定表.md").read_text(encoding="utf-8")
    mgate = (ROOT / "references/_shared/M-Gate-Algorithm.md").read_text(encoding="utf-8")
    assert "实测 > 3 倍" in wz and "1.5 倍" in wz, "字数判定表 §二 缺 M-5 P2 量化锚点"
    assert "P2 ≥ 3 项" in mgate and "形态类瑕疵" in mgate, "M-Gate §🎯 缺 M-5 P2 量化锚点"


def test_m3_m5_dual_source_lock_in_flow_check():
    """M-3/M-5：flow-check 规则 16 必须同时锁两个文件存在新段（防单边丢掉）。"""
    import contextlib, io, os
    # 反向注入：把字数判定表里“实测 > 3 倍”彻底删掉，看 flow-check 是否报缺
    wz_path = ROOT / "references/_shared/字数判定表.md"
    src = wz_path.read_text(encoding="utf-8")
    # 注入点：删掉该行包括分隔符（** 与 **）与上下文空格
    import re as _re
    bad = _re.sub(r"\|\s*\*\*实测 > 3 倍\*\*\s*\|", "| ~~删~~~~ |", src, count=1)
    if bad == src:
        bad = _re.sub(r"\*\*实测 > 3 倍\*\*", "~~删~~~~", src, count=1)
    assert bad != src, "反向注入点未命中"
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        wz_path.write_text(bad, encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = FC.main()
        out = buf.getvalue()
        assert rc != 0, "反向注入未被检出 —— M-3/M-5 双真源锁死规则退化"
        assert "字数判定表" in out, f"报错未指向双真源: {out}"
    finally:
        wz_path.write_text(src, encoding="utf-8")
        os.chdir(cwd)


# ===== v2.12.49 M-4 G14 严重度 + M-6 轮次出口三选一 =====

def test_m4_g14_severity_band_declared():
    """M-4：G14 §三判定规则必须声明 max(类数档, 单类严重度档) + severe_single_class 报告字段。"""
    g14 = (ROOT / "references/gates/14-中文AI痕迹-gate.md").read_text(encoding="utf-8")
    assert "max(类数档判定, 单类严重度档判定)" in g14, \
        "G14 §三 未声明 max(类数档, 单类严重度档) 双轨判定（M-4）"
    assert "severe_single_class" in g14, \
        "G14 §三 缺 severe_single_class 报告头字段（M-4）"
    # 阈值表
    assert "5 倍" in g14 and "3 倍" in g14, "G14 §三 缺 3x/5x 阈值档（M-4）"


def test_m6_audit_revision_three_choice_outlet_declared():
    """M-6：audit_revision 节点 rounds_exhausted_outlet 必须声明 A/B/C 三选项 + no_default_option + halt_pending_owner。"""
    ar = _node("audit_revision")
    outlet = ar.get("rounds_exhausted_outlet")
    assert outlet, "audit_revision 缺 rounds_exhausted_outlet（M-6）"
    assert outlet.get("no_default_option") is True, "no_default_option ≠ true（M-6）"
    assert outlet.get("halt_pending_owner") is True, "halt_pending_owner ≠ true（M-6）"
    labels = [d.get("id") for d in (outlet.get("owner_decision") or [])]
    for must in ("accept_with_limitations", "extend_one_round", "manual_polish"):
        assert must in labels, f"owner_decision 缺「{must}」选项（M-6 三选一）"


def test_m4_m6_flow_check_dual_lock():
    """M-4/M-6：flow-check 规则 17/18 必须锁 audit_revision 三选一 + G14 severe_single_class。

    反向注入：去掉 owner_decision 三个选项之一（manual_polish）。YAML 仍合法但
    rules 17 应检出三选一缺失。两个有效信号：(a) main() 返回码 != 0；(b) 输出含 manual_polish。
    其中 (a) 为必要条件。
    """
    import contextlib, io, os
    src = YAML_PATH.read_text(encoding="utf-8")
    # 删除 manual_polish 选项整段（4 行：id/label/requires + 后行）
    import re as _re
    bad = _re.sub(
        r"\n        - id: manual_polish\n          label:.*?\n          requires:.*?\n",
        "\n        # manual_polish 被反向注入删去\n",
        src, count=1, flags=_re.DOTALL,
    )
    assert bad != src, "反向注入点未命中（manual_polish 选项格式已变）"
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        YAML_PATH.write_text(bad, encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = FC.main()
        out = buf.getvalue()
        assert rc != 0, "反向注入未被检出 —— M-6 轮次出口锁退化"
        # 输出任一信号即可：manual_polish / owner_decision / rounds_exhausted_outlet
        assert any(s in out for s in ("manual_polish", "owner_decision", "rounds_exhausted_outlet")), \
            f"报错未指向 M-6 owner_decision 任意关键字符串: {out}"
    finally:
        YAML_PATH.write_text(src, encoding="utf-8")
        os.chdir(cwd)


# ===== v2.12.49 M-7 status 对账 + M-9 48 必查严重度列 =====

def test_m9_48_items_have_severity_column():
    """M-9：可发表性判定表 §二 A-E 5 组每行必含严重度列（P0/P1/P2/advisory）。"""
    text = (ROOT / "references/_shared/可发表性判定表.md").read_text(encoding="utf-8")
    sec2 = text[text.index("## 二、"):text.index("\n## 三、")]
    # §二 A-E 必含 17 处严重度标记（4+5+4+2+2 = 17 行）
    sev_count = sum(sec2.count(f"**{sev}**") for sev in ("P0", "P1", "P2", "advisory"))
    assert sev_count >= 17, f"§二 A-E 严重度标记仅 {sev_count} 处 < 17（M-9）"
    # M-9 总注必填：存在 §二段头
    assert "M-9" in sec2 and "严重度" in sec2, "§二 缺 M-9 总注说明"


def test_m7_status_template_has_node_binding():
    """M-7：status-template §四产物路径必含节点 ID 标注（[节点: <id>]）与双向断言总注。"""
    text = (ROOT / "references/templates/status-template.md").read_text(encoding="utf-8")
    assert "M-7 状态对账机械真源" in text, "status-template 缺 M-7 总注"
    assert "[节点:" in text, "status-template §四产物路径缺节点 ID 标注"
    # final/定稿.sha256 是 M-1 配套字段
    assert "final/定稿.sha256" in text, "status-template §四 缺 final/定稿.sha256（M-1 配套）"


def test_m7_m9_flow_check_dual_lock():
    """M-7/M-9：flow-check 规则 19 须锁 §二 A-E 严重度 + status-template 节点标注。"""
    import contextlib, io, os
    src = (ROOT / "references/_shared/可发表性判定表.md").read_text(encoding="utf-8")
    # 反向注入：去掉 A3 行的 **P1**（让总标记数 -1）
    import re as _re
    bad = _re.sub(r"(\| A3 \| .+? \| A \| )\*\*P1\*\*", r"\1~~", src, count=1)
    assert bad != src, "反向注入点未命中（A3 P1 标记格式已变）"
    wz_path = ROOT / "references/_shared/可发表性判定表.md"
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        wz_path.write_text(bad, encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = FC.main()
        out = buf.getvalue()
        assert rc != 0, "反向注入未被检出 —— M-9 严重度列锁退化"
        assert "严重度" in out and "17" in out, f"报错未指向严重度阈值: {out}"
    finally:
        wz_path.write_text(src, encoding="utf-8")
        os.chdir(cwd)


# ===== v2.12.49 M-10 图件路径归一 + M-11 图位决策必答 =====

def test_m10_figure_path_normalized():
    """M-10：phase4_4_figures.output 必须归一为 'final/图件/*.svg'（唯一真源）。"""
    pf4 = _node("phase4_4_figures")
    assert pf4.get("output") == "final/图件/*.svg", \
        f"phase4_4_figures.output ≠ 'final/图件/*.svg'（M-10 路径未归一）: {pf4.get('output')}"


def test_m10_limitations_artifact_in_truth_source():
    """M-10：t8_technical_final 必须声明 acknowledged_limitations_mode 产出 final/局限性.md。"""
    t8 = _node("t8_technical_final")
    oc = t8.get("output_conditional") or {}
    assert oc.get("acknowledged_limitations_mode") == "final/局限性.md", \
        f"t8_technical_final.output_conditional.acknowledged_limitations_mode 未声明 final/局限性.md（M-10）: {oc}"


def test_m11_owner_figure_decision_in_status_template():
    """M-11：status-template §三 人在环决策段必含 figures + figure_decision 字段。"""
    text = (ROOT / "references/templates/status-template.md").read_text(encoding="utf-8")
    assert "figures=" in text and "figure_decision=" in text, \
        "status-template §三 人在环决策段缺 figures + figure_decision（M-11）"


def test_m11_t4_does_not_decide_zero():
    """M-11：04-分析 T4 仅出建议不出一决定（'拍板 0 张'需主人 Phase 2.5 显式拍板）。"""
    text = (ROOT / "references/agents/04-分析-analyst.md").read_text(encoding="utf-8")
    assert "T4 **仅出建议**" in text or "T4 不出一决定" in text, \
        "04-分析-analyst 缺 M-11 T4 仅出建议声明"


def test_m11_checkpoint_card_has_figure_decision():
    """M-11：checkpoint-card-template 必含「图位决策必答」段。"""
    text = (ROOT / "references/templates/checkpoint-card-template.md").read_text(encoding="utf-8")
    assert "图位决策必答" in text, "checkpoint-card-template 缺 M-11 图位决策必答总注"


def test_m10_m11_flow_check_dual_lock():
    """M-10/M-11：flow-check 规则 20 须锁 phase4_4_figures.output 归一 + checkpoint-card 总注 + 04-分析声明。"""
    import contextlib, io, os
    src = YAML_PATH.read_text(encoding="utf-8")
    # 反向注入：改 phase4_4_figures.output
    bad = src.replace("output: final/图件/*.svg", "output: final/figures/", 1)
    assert bad != src, "反向注入点未命中（phase4_4_figures.output 格式已变）"
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        YAML_PATH.write_text(bad, encoding="utf-8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = FC.main()
        out = buf.getvalue()
        assert rc != 0, "反向注入未被检出 —— M-10 路径锁退化"
        assert "M-10" in out or "final/图件" in out, f"报错未指向 M-10 路径: {out}"
    finally:
        YAML_PATH.write_text(src, encoding="utf-8")
        os.chdir(cwd)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ✓ {name}")
    print("flow-check 测试全过")
