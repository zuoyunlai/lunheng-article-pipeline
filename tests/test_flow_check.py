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


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ✓ {name}")
    print("flow-check 测试全过")
