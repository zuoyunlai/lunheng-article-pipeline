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
import hashlib
import importlib.util
import pathlib
import re
import shutil
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).parent.parent
YAML_PATH = ROOT / "references" / "_shared" / "phase-order.yaml"

# ===== v2.12.51 D-4：反向注入一律在「整仓副本」上施加，真源只读 =====
# 背景：v2.12.51 前 ≥11 处反向注入直接 write_text 真源（phase-order.yaml / 字数判定表.md /
#   可发表性判定表.md / 08-终检-final-inspector.md），仅靠 try/finally 恢复
#   —— kill / 超时 / 并行即永久污染真源。
# 现口径：copytree 整仓到 tmp_path → 在**副本**上变异 → 跑**副本的** scripts/flow-check.py
#   （cwd 必须 = 副本根：main() 读相对路径 references/_shared/phase-order.yaml）
#   → 断言 RC≠0 + 报错指向预期节点/路径 + **真源 sha256 前后不变**（硬断言）。
COPY_IGNORE = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc")
YAML_REL = "references/_shared/phase-order.yaml"


def _sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _sandbox(tmp_path):
    """整仓副本（真源字节级只读）。"""
    dst = pathlib.Path(tmp_path) / "repo"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(ROOT, dst, ignore=COPY_IGNORE)
    return dst


def _flow_check_in(copy_root):
    """在副本根跑**副本的** flow-check（cwd 必须 = 副本根，见 D-4）。"""
    proc = subprocess.run(
        [sys.executable, str(pathlib.Path(copy_root) / "scripts" / "flow-check.py")],
        cwd=str(copy_root), capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _inject_and_expect(rel_path, mutate, expect, tmp_path):
    """副本注入契约：① 真源 sha256 前后不变；② 副本 flow-check RC≠0；③ 报错含 expect。"""
    truth = ROOT / rel_path
    before = _sha256(truth)
    copy_root = _sandbox(tmp_path)
    target = copy_root / rel_path
    src = target.read_text(encoding="utf-8")
    bad = mutate(src)
    assert bad != src, f"反向注入点未命中：{rel_path}"
    target.write_text(bad, encoding="utf-8")
    rc, out = _flow_check_in(copy_root)
    assert _sha256(truth) == before, f"真源被测试污染（sha256 变了）：{rel_path}"
    assert rc != 0, f"反向注入未被检出（RC=0）—— 规则退化成永真：{rel_path}"
    assert expect in out, f"报错未指向「{expect}」：{out}"
    return out


def _node_block(src, marker):
    """取节点 YAML 块：返回 (start, block)，block 从 marker 到下一个 `  - id:` 之前。"""
    start = src.index(marker)
    lines = src[start:].splitlines(keepends=True)
    end = next((i for i, ln in enumerate(lines)
                if i > 3 and (ln.startswith("  - id:") or ln.startswith("- id:"))), len(lines))
    return start, "".join(lines[:end])


def _drop_key(src, marker, key):
    """删掉 marker 节点块内所有以 key 开头的行（反向注入通用手法）。"""
    start, block = _node_block(src, marker)
    lines = block.splitlines(keepends=True)
    kept = [ln for ln in lines if not ln.lstrip().startswith(key)]
    assert len(kept) < len(lines), f"反向注入点未命中（{marker} 块内无 {key}）"
    return src[:start] + "".join(kept) + src[start + len(block):]


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
    """worker 节点必须声明角色、写入权、核验权与失败接管策略（节点级接管，非整轮降级）。

    v2.12.51 D-3：写入权按档位分两类 ——
      · 只读档（T6 / T7 / T9 / G14）= 报告由主控 write 落盘 ⇒ 必须 `owner`
      · 自有产物节点（T4 分析 / T5 写手 / 检索三卡）⇒ 必须 `executor`
    v2.12.55 S-2：`independence: blind_review` 节点例外 —— **不得**走通用 fallback（主控接管），
      改由 `independence_failure_policy` 承接（只重试 spawn → 仍失败记缺失 + 告知主人）。
    """
    READONLY_ROLES = {"T6", "T7", "T9", "G14"}
    missing = []
    for n in _pipeline()["pipeline"]:
        if n.get("kind") in {"agent", "parallel_agents", "conditional_agent", "advisory_agent"}:
            if not n.get("role"):
                missing.append(f"{n['id']}.role")
            expected_wa = "owner" if n.get("role") in READONLY_ROLES else "executor"
            if n.get("write_authority") != expected_wa:
                missing.append(
                    f"{n['id']}.write_authority={n.get('write_authority')}（应为 {expected_wa}）")
            if n.get("verification_authority") != "主控":
                missing.append(f"{n['id']}.verification_authority")
            if n.get("independence") == "blind_review":
                # S-2：盲审节点不得声明通用 fallback（= 主控代笔）
                if (n.get("on_worker_failure") or {}).get("executor") == "主控":
                    missing.append(f"{n['id']}.on_worker_failure（盲审禁主控代笔，S-2）")
                continue
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


def test_methodology_snapshot_default_triggered_with_opt_out():
    """v2.12.49 T-6：快照改「默认触发（简版 ≤2 节）+ 主人 opt_out」—— 不再是纯 opt-in。"""
    n = _node("methodology_snapshot")
    assert n.get("default") == "triggered", "T-6：快照应默认触发"
    assert n.get("opt_out") == "methodology_snapshot_opt_out", "T-6：opt-out 条件键缺失/改名"
    assert n.get("on_opt_out") == "record_opt_out_in_status", "T-6：opt-out 必须留痕"
    assert n.get("output") == "run/<项目名>/audits/methodology-footprint-{项目名}.md"
    assert not n.get("condition"), "T-6 后不得保留 opt-in condition（否则又变回纯 opt-in）"


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


def test_flow_check_detects_missing_producer(tmp_path):
    """反向注入（D-4 副本注入）：无生产者的单消费者路径必须被检出（防新规则退化成永真）。"""
    def mutate(src):
        start, block = _node_block(src, "  - id: final_assembly")
        assert "    output: final/定稿.md\n" in block, \
            "反向注入点未命中（final_assembly.output 写法已变）"
        bad_block = block.replace("    output: final/定稿.md\n", "", 1)
        return src[:start] + bad_block + src[start + len(block):]
    _inject_and_expect(YAML_REL, mutate, "final/定稿.md", tmp_path)


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


def test_flow_check_detects_missing_owner_gate_declaration(tmp_path):
    """反向注入（D-4 副本注入）：owner_checkpoint 缺 blocking: true 必须被规则 12 检出。"""
    def mutate(src):
        return _drop_key(src, "  - id: phase5_acceptance", "blocking: true")
    _inject_and_expect(YAML_REL, mutate, "phase5_acceptance", tmp_path)


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


def test_m1_flow_check_detects_missing_fingerprint_pair(tmp_path):
    """反向注入（D-4 副本注入）：final_assembly 声明 fingerprint 但 t8 未同步 ⇒ 规则 14 检出。"""
    def mutate(src):
        return _drop_key(src, "  - id: t8_technical_final", "fingerprint:")
    _inject_and_expect(YAML_REL, mutate, "t8_technical_final", tmp_path)


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


def test_m2_flow_check_detects_missing_terminal(tmp_path):
    """反向注入（D-4 副本注入）：phase5_acceptance 缺 terminal ⇒ 规则 13 检出。"""
    def mutate(src):
        return _drop_key(src, "  - id: phase5_acceptance", "terminal:")
    _inject_and_expect(YAML_REL, mutate, "terminal", tmp_path)


# ===== v2.12.49 M-8 审计对象一致 =====

def test_m8_audited_artifact_required_on_critical_nodes():
    """M-8：t7_5_integrity / t8_technical_final / t9_review 必须声明 audited_artifact_required: true。"""
    required = {"t7_5_integrity", "t8_technical_final", "t9_review"}
    missing = sorted(nid for nid in required if not _node(nid).get("audited_artifact_required"))
    assert not missing, f"以下节点缺 audited_artifact_required: true（M-8）：{missing}"


def test_m8_flow_check_detects_missing_audited_artifact_required(tmp_path):
    """反向注入（D-4 副本注入）：t7_5_integrity 缺 audited_artifact_required ⇒ 规则 15 检出。"""
    def mutate(src):
        return _drop_key(src, "  - id: t7_5_integrity", "audited_artifact_required:")
    _inject_and_expect(YAML_REL, mutate, "audited_artifact_required", tmp_path)


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


def test_m3_m5_dual_source_lock_in_flow_check(tmp_path):
    """M-3/M-5：flow-check 规则 16 必须同时锁两个文件存在新段（防单边丢掉）。

    D-4：副本注入（原文正向写盘真源 → 改为在整仓副本上变异）；注入点 =
    把字数判定表里“实测 > 3 倍”彻底删掉，看副本 flow-check 是否报缺。
    """
    def mutate(src):
        bad = re.sub(r"\|\s*\*\*实测 > 3 倍\*\*\s*\|", "| ~~删~~~~ |", src, count=1)
        if bad == src:
            bad = re.sub(r"\*\*实测 > 3 倍\*\*", "~~删~~~~", src, count=1)
        return bad
    _inject_and_expect("references/_shared/字数判定表.md", mutate, "字数判定表", tmp_path)


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


def test_m4_m6_flow_check_dual_lock(tmp_path):
    """M-4/M-6：flow-check 规则 17/18 必须锁 audit_revision 三选一 + G14 severe_single_class。

    D-4：副本注入。注入点 = 去掉 owner_decision 三个选项之一（manual_polish）。
    YAML 仍合法，但规则 17 应检出三选一缺失。有效信号 =（a）RC≠0（必要条件）+（b）输出含 manual_polish。
    """
    def mutate(src):
        return re.sub(
            r"\n        - id: manual_polish\n          label:.*?\n          requires:.*?\n",
            "\n        # manual_polish 被反向注入删去\n",
            src, count=1, flags=re.DOTALL,
        )
    out = _inject_and_expect(YAML_REL, mutate, "manual_polish", tmp_path)
    assert any(s in out for s in ("manual_polish", "owner_decision", "rounds_exhausted_outlet")), \
        f"报错未指向 M-6 owner_decision 任意关键字符串: {out}"


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


def test_m7_m9_flow_check_dual_lock(tmp_path):
    """M-7/M-9：flow-check 规则 19 须锁 §二 A-E 严重度 + status-template 节点标注（D-4 副本注入）。"""
    def mutate(src):
        return re.sub(r"(\| A3 \| .+? \| A \| )\*\*P1\*\*", r"\1~~", src, count=1)
    out = _inject_and_expect("references/_shared/可发表性判定表.md", mutate, "严重度", tmp_path)
    assert "17" in out, f"报错未指向严重度阈值 17: {out}"


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


def test_m10_m11_flow_check_dual_lock(tmp_path):
    """M-10/M-11：规则 20 须锁 phase4_4_figures.output 归一 + checkpoint-card 总注 + 04-分析声明（D-4 副本注入）。"""
    def mutate(src):
        return src.replace("output: final/图件/*.svg", "output: final/figures/", 1)
    out = _inject_and_expect(YAML_REL, mutate, "M-10", tmp_path)
    assert "final/图件" in out or "phase4_4_figures" in out, f"报错未指向 M-10 路径: {out}"


# ===== v2.12.49 M-13 主人操作清单 + M-14 字数口径 =====

def test_m13_t8_owner_suggestion_list_declared():
    """M-13：T8 dispatch 必含「主人自行操作建议清单」与 M-13 段锁。"""
    text = (ROOT / "references/dispatch/T8-终检.md").read_text(encoding="utf-8")
    assert "主人自行操作建议清单" in text, "T8 dispatch 缺主人自行操作建议清单（M-13）"
    assert "M-13" in text, "T8 dispatch 缺 M-13 段锁"
    # 三类动作必出现
    for action in ("文档格式转换", "SVG → PNG 转换", "封面视觉"):
        assert action in text, f"T8 dispatch 清单缺「{action}」动作（M-13）"


def test_m14_body_limit_in_task_brief():
    """M-14：任务简报模板「目标篇幅」段必含 body_limit 字段。"""
    text = (ROOT / "references/templates/任务简报-template.md").read_text(encoding="utf-8")
    assert "body_limit" in text, "任务简报模板 缺 body_limit 字段（M-14）"


def test_m14_word_count_unity_in_deliverables():
    """M-14：deliverables.md 必含字数口径单一化段 + body_char_count 字段。"""
    text = (ROOT / "references/deliverables.md").read_text(encoding="utf-8")
    assert "字数口径单一化" in text, "deliverables.md 缺字数口径单一化段（M-14）"
    assert "body_char_count" in text, "deliverables.md 缺 body_char_count 字段（M-14）"


def test_m13_m14_flow_check_dual_lock(tmp_path):
    """M-13/M-14：规则 21 锁 T8 dispatch / 任务简报 / deliverables / 08-终检 四真源（D-4 副本注入）。"""
    def mutate(src):
        # 全量替换：该字段在文件中出现多处，只替 1 处会留同名残留 → 反向注入被漏检（v2.12.49 实测）
        return src.replace("body_char_count", "~~删~~~~")
    out = _inject_and_expect("references/agents/08-终检-final-inspector.md", mutate, "M-14", tmp_path)
    assert "body_char_count" in out or "M-14" in out, f"报错未指向 M-14: {out}"


# ===== v2.12.49 T 系列治本（T-1 / T-2 / T-3 / T-4 / T-5 / T-6 / T-8）=====

def test_t1_upstream_read_contract():
    """T-1：关键协议须含落盘前置 + 派发禁摘要；交接报告须含 upstream_read 差集字段。"""
    kp = (ROOT / "references/_shared/关键协议.md").read_text(encoding="utf-8")
    assert "四·补" in kp and "派发禁止摘要" in kp, "关键协议缺 §四·补（T-1）"
    assert "前置断言" in kp, "关键协议缺 spawn 前置断言（T-1）"
    jj = (ROOT / "references/templates/交接报告-template.md").read_text(encoding="utf-8")
    for k in ("upstream_read", "upstream_ids", "dispatched_ids"):
        assert k in jj, f"交接报告缺 {k}（T-1 差集断言）"


def test_t2_t3_model_family_and_liveness_gate():
    """T-2/T-3：候选池须含换族优先/断路器/族级独立性/探活门；探活门须入真源。"""
    c = (ROOT / "references/_shared/模型候选池.md").read_text(encoding="utf-8")
    assert "优先换 provider 族" in c, "候选池缺换族优先（T-2）"
    assert "断路器" in c, "候选池缺断路器（T-2）"
    assert "模型族" in c and "两两不同" in c, "候选池缺族级独立性判据（T-2）"
    assert "二·补" in c and "探活门" in c, "候选池缺探活门节（T-3）"
    n = _node("pre_spawn_enforcement")
    gate = n.get("top_tier_liveness_gate")
    assert isinstance(gate, dict), "T-3 探活门未入 phase-order 真源"
    assert gate.get("attempts") == 3 and gate.get("min_interval_seconds") == 10
    assert gate.get("staleness_minutes") == 60, "T-3 探活结果 1 小时过期未声明"


def test_t4_peer_review_family_fields():
    """T-4：审稿报告模板须含族级独立性三字段 + 同源措辞铁律 + 过程材料约束。"""
    t = (ROOT / "references/templates/审稿报告-template.md").read_text(encoding="utf-8")
    for k in ("executor_model", "model_family", "independent_from"):
        assert k in t, f"审稿报告缺 {k}（T-4）"
    assert "模型独立性不成立" in t, "T-4 缺同源措辞铁律（不得写「独立性达成」）"
    assert "过程材料约束" in t, "T-4 缺过程材料约束（防自相矛盾）"


def test_t5_net_delta_cap():
    """T-5：字数判定表须含单轮净增 ≤2% + 等量置换；修订说明须含 net_delta_cjk。"""
    w = (ROOT / "references/_shared/字数判定表.md").read_text(encoding="utf-8")
    assert "修订净增上限" in w and "≤ 2%" in w, "字数判定表缺净增上限（T-5）"
    assert "等量置换" in w, "字数判定表缺等量置换要求（T-5）"
    assert "92%" in w, "字数判定表缺 Phase 0 92% 预留（T-5）"
    m = (ROOT / "references/templates/修订说明-template-full.md").read_text(encoding="utf-8")
    assert "net_delta_cjk" in m, "修订说明模板缺 net_delta_cjk（T-5）"


def test_t6_methodology_snapshot_default_triggered():
    """T-6：快照默认触发 + 主人 opt-out（不再是纯 opt-in）。"""
    n = _node("methodology_snapshot")
    assert n.get("default") == "triggered"
    assert n.get("opt_out") == "methodology_snapshot_opt_out"
    assert n.get("on_opt_out") == "record_opt_out_in_status"
    assert not n.get("condition")


def test_t8_citation_style_unified():
    """T-8：deliverables 须声明引用体例单一化；M-Exist-1 须含引用体例层校验。"""
    d = (ROOT / "references/deliverables.md").read_text(encoding="utf-8")
    assert "引用体例单一化" in d, "deliverables 缺 T-8 段"
    assert "两套体例并存" in d, "deliverables 缺「禁止两套体例并存」铁律"
    g = (ROOT / "references/_shared/M-Gate-Algorithm.md").read_text(encoding="utf-8")
    assert "引用体例层" in g, "M-Gate-Exist-1 缺引用体例层校验（T-8）"


def test_t3_liveness_gate_reverse_injection(tmp_path):
    """反向注入（D-4 副本注入）：删掉 phase-order 的 top_tier_liveness_gate ⇒ flow-check 必须报错。"""
    def mutate(src):
        return src.replace("top_tier_liveness_gate:", "~~removed~~:", 1)
    out = _inject_and_expect(YAML_REL, mutate, "top_tier_liveness_gate", tmp_path)
    assert "top_tier_liveness_gate" in out or "T-3" in out, f"报错未指向 T-3: {out}"


# ===== v2.12.51 D-3 只读档写权（正向 + 反向注入）=====

def test_readonly_tier_reports_are_owner_written():
    """D-3 正向：只读档四节点（T6/T7/T9/G14）真源必须写 `write_authority: owner`。

    口径 = 只读档工具面仅 `read`，报告正文随交接回传、由主控 `write` 落盘；
    与 10 处角色卡 / dispatch 的「主控代写盘」一致，且与 `verification_authority: 主控` 自洽。
    """
    byid = {n["id"]: n for n in _pipeline()["pipeline"]}
    for pid, role in (("t6_critique", "T6"), ("t7_audit", "T7"),
                      ("g14_style_gate", "G14"), ("t9_review", "T9")):
        n = byid[pid]
        assert n.get("role") == role, f"{pid}.role 异常: {n.get('role')}"
        assert n.get("write_authority") == "owner", \
            f"{pid} 未写 write_authority: owner（D-3：只读档报告由主控 write 落盘）"
    # 自有产物节点不得被误改（回归护栏）
    for pid in ("t4_analysis", "t5_draft_v1", "t5_feedback_revision", "t5_style_revision"):
        assert byid[pid].get("write_authority") == "executor", f"{pid} 应保留 executor（自有产物）"
    raw = YAML_PATH.read_text(encoding="utf-8")
    assert raw.count("# v2.12.51 D-3：只读档报告由主控 write 落盘，本节点不授写权") == 4, \
        "四个只读档节点的 D-3 行尾注释不齐（应恰好 4 处）"


def test_flow_check_detects_readonly_tier_write_authority(tmp_path):
    """D-3 反向注入（教训 #399「机械门必须能红」）：把 t6_critique 的 owner 改回 executor ⇒
    flow-check 规则 23 必须 RC≠0 且报错指向 t6_critique。

    D-4：在整仓副本上注入，真源 sha256 前后不变。
    """
    owner_line = ("    write_authority: owner   # v2.12.51 D-3："
                  "只读档报告由主控 write 落盘，本节点不授写权")

    def mutate(src):
        start, block = _node_block(src, "  - id: t6_critique")
        bad_block = block.replace(owner_line, "    write_authority: executor", 1)
        return src[:start] + bad_block + src[start + len(block):]
    _inject_and_expect(YAML_REL, mutate, "t6_critique", tmp_path)


# ===== v2.12.54 Batch A：R-2 / R-3 / R-4 / R-5 / R-6 =====

def test_r4_condition_fields_have_declared_producers():
    """R-4：每条 condition_definitions 必登记 producer + producer_marker，且 marker 真的在生产方文件里。"""
    defs = _pipeline().get("condition_definitions") or {}
    assert defs, "phase-order.yaml 缺 condition_definitions"
    for name, d in defs.items():
        assert d.get("producer"), f"{name} 缺 producer（R-4：条件字段无生产方）"
        assert d.get("producer_marker"), f"{name} 缺 producer_marker（R-4）"
        f = ROOT / d["producer"]
        assert f.exists(), f"{name}.producer 文件不存在：{d['producer']}"
        assert d["producer_marker"] in f.read_text(encoding="utf-8"), \
            f"{name}.producer_marker 不在 {d['producer']} 中（R-4）"


def test_r4_reverse_injection(tmp_path):
    """R-4 反向注入：抹掉全部 producer_marker ⇒ flow-check 必须报红。"""
    def mutate(src):
        return src.replace("producer_marker:", "producer_marker_x:")
    _inject_and_expect(YAML_REL, mutate, "R-4", tmp_path)


def test_r6_condition_undecidable_declared():
    """R-6：声明 condition 或 opt_out 的节点必须显式声明 condition_undecidable。"""
    for n in _pipeline()["pipeline"]:
        if n.get("condition") or n.get("opt_out"):
            assert n.get("condition_undecidable") in ("report_to_owner", "halt_pending_owner"), \
                f"{n['id']} 缺/非法 condition_undecidable（R-6）"


def test_r6_reverse_injection(tmp_path):
    """R-6 反向注入：抹掉全部 condition_undecidable ⇒ flow-check 必须报红。"""
    def mutate(src):
        return src.replace("condition_undecidable:", "condition_undecidable_x:")
    _inject_and_expect(YAML_REL, mutate, "R-6", tmp_path)


def test_r2_r3_status_template_locks(tmp_path):
    """R-2/R-3：status 模板必含节点 id 合法性 + Done 记账一致性两把锁。"""
    text = (ROOT / "references/templates/status-template.md").read_text(encoding="utf-8")
    for k in ("R-2 节点 id 合法性", "禁止自创", "R-3 Done 记账一致性", "不得计 Done"):
        assert k in text, f"status-template 缺「{k}」（R-2/R-3）"

    def mutate(src):
        return src.replace("R-2 节点 id 合法性", "~~删~~")
    _inject_and_expect("references/templates/status-template.md", mutate, "R-2", tmp_path)


def test_r5_t8_owner_action_list_four_classes(tmp_path):
    """R-5：T8 建议清单四类（格式转换 / SVG→PNG / 封面视觉 / SHA256）缺一即红。"""
    for rel in ("references/dispatch/T8-终检.md", "references/agents/08-终检-final-inspector.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        for act in ("文档格式转换", "SVG", "PNG", "封面视觉", "SHA256", "T8 不合格"):
            assert act in text, f"{rel} 缺「{act}」（R-5）"

    def mutate(src):
        return src.replace("SHA256", "sha")
    _inject_and_expect("references/dispatch/T8-终检.md", mutate, "R-5", tmp_path)


def test_r1_exempt_files_must_not_carry_panorama(tmp_path):
    """R-1：pointer_exempt 文件也禁止承载全景段标记（否则等于第二份全景）。"""
    def mutate(src):
        return "## 流水线全景\n" + src
    _inject_and_expect("references/templates/status-template.md", mutate, "R-1", tmp_path)


# ===== v2.12.55 Batch B 泳道 1：S-2 盲审禁代笔 + S-3 静默升级 =====

def test_s2_blind_review_forbids_owner_takeover():
    """S-2 正向：`independence: blind_review` 节点禁主控代笔。

    判据（一句话）：盲审节点不得声明通用 fallback（`on_worker_failure.executor: 主控`），
    必须声明 `independence_failure_policy`（forbidden + 记缺失告知主人 + 正整数 retry_limit）。
    """
    found = 0
    for n in _pipeline()["pipeline"]:
        if n.get("independence") != "blind_review":
            continue
        found += 1
        owf = n.get("on_worker_failure") or {}
        assert not (isinstance(owf, dict) and owf.get("executor") == "主控"), \
            f"{n['id']} 仍声明 on_worker_failure.executor: 主控（S-2：盲审不得由主控代笔）"
        p = n.get("independence_failure_policy") or {}
        assert p.get("executor_takeover") == "forbidden", \
            f"{n['id']} 缺 independence_failure_policy.executor_takeover: forbidden（S-2）"
        assert p.get("on_exhausted") == "record_missing_and_notify_owner", \
            f"{n['id']} 缺 on_exhausted: record_missing_and_notify_owner（S-2：不得自行产出结论）"
        assert isinstance(p.get("retry_limit"), int) and p["retry_limit"] >= 1, \
            f"{n['id']}.independence_failure_policy.retry_limit 非正整数（S-2）"
        assert n.get("independence_rules"), f"{n['id']} 缺 independence_rules（S-2）"
    assert found, "全文真源中找不到任何 independence: blind_review 节点（S-2 规则退化成永真）"


def test_s2_blind_review_node_set_anchored():
    """S-2 锚点：blind_review 节点集当前 = {t9_review}（改名/新增必须显式回看本规则与角色卡）。"""
    blind = {n["id"] for n in _pipeline()["pipeline"] if n.get("independence") == "blind_review"}
    assert blind == {"t9_review"}, f"blind_review 节点集变化: {blind}（须同步主控卡与 S-2 门）"


def test_s2_flow_check_detects_owner_ghostwriting_fallback(tmp_path):
    """S-2 反向注入（D-4 副本注入）：把通用 fallback（executor: 主控）写回 t9_review ⇒ 规则 30 必须报红点名。"""
    def mutate(src):
        start, block = _node_block(src, "  - id: t9_review")
        injected = ("    on_worker_failure: {executor: 主控, disclosure: degraded_executor, retry_limit: 1}\n"
                    "    # ↓ v2.12.40 业主定案 A2：T9 独立性**硬定义**")
        bad_block = block.replace("    # ↓ v2.12.40 业主定案 A2：T9 独立性**硬定义**", injected, 1)
        return src[:start] + bad_block + src[start + len(block):]
    out = _inject_and_expect(YAML_REL, mutate, "S-2", tmp_path)
    assert "t9_review" in out, f"报错未点名 t9_review: {out}"


def test_s2_flow_check_detects_takeover_allowed(tmp_path):
    """S-2 反向注入：把 executor_takeover 改成 allowed ⇒ 规则 30 必须报红。"""
    def mutate(src):
        return src.replace("      executor_takeover: forbidden", "      executor_takeover: allowed", 1)
    out = _inject_and_expect(YAML_REL, mutate, "S-2", tmp_path)
    assert "t9_review" in out, f"报错未点名 t9_review: {out}"


def test_s3_provider_silence_escalation_declared():
    """S-3 正向：顶层 provider_silence_escalation = ≥3 次 / same_provider / 三选一无默认 / 挂起。"""
    pse = _pipeline().get("provider_silence_escalation") or {}
    assert pse, "缺顶层 provider_silence_escalation（S-3：静默升级规则无机器可读真源）"
    assert pse.get("threshold") == 3, f"threshold ≠ 3: {pse.get('threshold')}"
    assert pse.get("scope") == "same_provider"
    assert pse.get("no_default_option") is True, "S-3 三选一不得有默认项"
    assert pse.get("halt_pending_owner") is True, "S-3 到阈值必须挂起等主人"
    ids = [c.get("id") for c in (pse.get("owner_choices") or [])]
    for must in ("switch_provider_family", "switch_capability_tier", "accept_same_source_with_disclosure"):
        assert must in ids, f"provider_silence_escalation.owner_choices 缺「{must}」（S-3 三选一）"


def test_s3_controller_card_carries_protocol():
    """S-3 接线：主控角色卡必须承载同一协议（真源 ↔ 角色卡双向；防「只活在 yaml」）。"""
    mc = (ROOT / "references/agents/00-主控-coordinator.md").read_text(encoding="utf-8")
    assert "连续 ≥3 次静默" in mc, "主控卡缺 S-3 静默升级协议"
    assert "禁主控代笔" in mc, "主控卡缺 S-2 盲审禁代笔协议"


def test_s3_flow_check_detects_threshold_drift(tmp_path):
    """S-3 反向注入（D-4 副本注入）：把静默阈值改成 9 ⇒ 规则 31 必须报红点名。"""
    def mutate(src):
        return src.replace("  threshold: 3", "  threshold: 9", 1)
    out = _inject_and_expect(YAML_REL, mutate, "S-3", tmp_path)
    assert "provider_silence_escalation" in out, f"报错未点名 provider_silence_escalation: {out}"


def test_s3_flow_check_detects_missing_rule(tmp_path):
    """S-3 反向注入（D-4 副本注入）：顶层键被改名（= 整块失效）⇒ 规则 31 必须报红。"""
    def mutate(src):
        return src.replace("\nprovider_silence_escalation:", "\nprovider_silence_escalation_x:", 1)
    out = _inject_and_expect(YAML_REL, mutate, "S-3", tmp_path)
    assert "provider_silence_escalation" in out, f"报错未点名 provider_silence_escalation: {out}"


if __name__ == "__main__":
    import inspect
    import tempfile
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            if inspect.signature(fn).parameters:   # 需 tmp_path 的副本注入测试
                with tempfile.TemporaryDirectory() as _td:
                    fn(pathlib.Path(_td))
            else:
                fn()
            print(f"  ✓ {name}")
    print("flow-check 测试全过")


# ===== v2.12.60 M-11 图件「嵌入」锁 + 节点 kind 必填 =====

EMBED_SPEC = "![图N：标题](图件/图N_标题.svg)"


def test_m11_figure_embed_lock_in_three_carriers():
    """M-11 图件嵌入锁（v2.12.60，主人裁定「图件如果存在要机械嵌入」）。

    背景：M-11 原只锁「纯文本占位计数 = 拍板 N」，不锁嵌入 —— 实测 run 的 final/定稿.md
    里 .svg / ![ 引用数 = 0，3 张 SVG 躺在 final/图件/ 里「有图但文里看不到」。
    三处载体必须同时含「嵌入式图位规范」与「嵌入计数」口径，否则口径会静默漂回纯占位版。
    """
    for rel in ("references/deliverables.md",
                "references/agents/08-终检-final-inspector.md",
                "references/dispatch/T8-终检.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert EMBED_SPEC in text, f"{rel} 缺嵌入式图位规范（M-11 图件嵌入锁）"
        assert "嵌入计数" in text, f"{rel} 缺「嵌入计数」口径（M-11 图件嵌入锁）"


def test_m11_figure_embed_lock_reverse_injection(tmp_path):
    """D-4 副本注入：删掉 deliverables 的嵌入式图位规范 ⇒ flow-check 必须红且点名。"""
    def mutate(src):
        assert EMBED_SPEC in src, "反向注入点未命中（嵌入式图位规范写法已变）"
        return src.replace(EMBED_SPEC, "~~已删除~~")

    _inject_and_expect("references/deliverables.md", mutate, "图件嵌入锁", tmp_path)


def test_pipeline_nodes_must_declare_kind():
    """kind 必填（v2.12.60）：kind 是规则 4/5 与 owner_nodes 归属的分派键。

    实测：改 final_assembly 时误删 `kind: mechanical_checkpoint`，全仓 flow-check RC=0 零报错
    ⇒ 「kind 缺失 = 该节点对所有按 kind 分派的检查静默隐身」（与教训 #427 同族）。
    """
    known = {"owner_checkpoint", "mode_declaration", "parallel_agents",
             "conditional_review_window", "mechanical_checkpoint", "agent",
             "conditional_agent", "bounded_loop", "owner_agent", "advisory_agent"}
    for n in _pipeline()["pipeline"]:
        assert n.get("kind"), f"{n.get('id')} 缺 kind（仅对 kind 类检查隐身）"
        assert n["kind"] in known, f"{n.get('id')} kind 非法：{n['kind']}"


def test_missing_node_kind_reverse_injection(tmp_path):
    """D-4 副本注入：删掉某节点的 kind 行 ⇒ flow-check 必须红并点名该节点。"""
    def mutate(src):
        start, block = _node_block(src, "  - id: final_assembly")
        assert "    kind: mechanical_checkpoint\n" in block, \
            "反向注入点未命中（final_assembly.kind 写法已变）"
        bad_block = block.replace("    kind: mechanical_checkpoint\n", "", 1)
        return src[:start] + bad_block + src[start + len(block):]

    _inject_and_expect(YAML_REL, mutate, "缺 kind", tmp_path)


# ===== v2.12.61 人环决策词表三处同源（status ↔ yaml ↔ card 真源指针） =====

_OWNER_DECISION_SOURCES = (
    ("Phase 0 定题", "phase0_definition"),
    ("Phase 2.5 大纲", "phase2_5_outline"),
    ("Phase 3.5 洞察", "phase3_5_insight"),
    ("Phase 5 验收", "phase5_acceptance"),
)


def test_status_decision_literals_subset_of_yaml():
    """status-template 四行 decision=<...> 字面值必须 ⊆ 对应节点 yaml decisions。

    实况（2026-09-19 主人问「checkpoint-card 有没有实质作用」时查出）：Phase 0 行写
    `start|补充信息|暂停|拒绝`，yaml 是 `approved|revision_requested|restart_phase` —— 交集为空；
    `start`/`暂停`/`拒绝` 在全仓真源零命中，主控据此写下的字面值在真源里根本不存在，
    人在环硬门必然判「未记录」。
    """
    status = (ROOT / "references/templates/status-template.md").read_text(encoding="utf-8")
    nodes = {n["id"]: n for n in _pipeline()["pipeline"]}
    for label, nid in _OWNER_DECISION_SOURCES:
        m = re.search(r"^- \*\*" + re.escape(label) + r"\*\*:.*?decision=<([^>]*)>", status, re.M)
        assert m, f"status-template 缺「{label}」decision=<...> 行"
        vals = {v.strip() for v in m.group(1).split("|") if v.strip()}
        declared = set(nodes[nid].get("decisions") or [])
        assert vals <= declared, f"「{label}」{sorted(vals)} ⊄ {nid}.decisions {sorted(declared)}"


def test_card_declares_enum_source_for_all_four_nodes():
    """卡片四段各须带枚举真源指针 —— 「选项固定，不可自由发挥」不能只是自我声明。"""
    card = (ROOT / "references/templates/checkpoint-card-template.md").read_text(encoding="utf-8")
    for label, nid in _OWNER_DECISION_SOURCES:
        assert f"{nid}.decisions" in card, f"checkpoint-card 缺「{label}」枚举真源指针（{nid}.decisions）"
    assert "pre_pipeline_exit" in card, "checkpoint-card 缺 pre_pipeline_exit（Phase 0 未进线出口口径）"


def test_selfinvented_decision_value_reverse_injection(tmp_path):
    """D-4 副本注入：给 Phase 0 行塞一个真源没有的字面值 ⇒ flow-check 必须红且点名。"""
    def mutate(src):
        old = "decision=<approved|revision_requested>"
        assert old in src, "反向注入点未命中（Phase 0 decision 写法已变）"
        return src.replace(old, "decision=<approved|revision_requested|paused>", 1)

    _inject_and_expect("references/templates/status-template.md", mutate, "自创词表", tmp_path)


def test_missing_enum_source_pointer_reverse_injection(tmp_path):
    """D-4 副本注入：删掉卡片 Phase 0 段的真源指针 ⇒ flow-check 必须红且点名。"""
    def mutate(src):
        old = "（**仅进线决策**；枚举真源：`phase-order.yaml` `phase0_definition.decisions`）"
        assert old in src, "反向注入点未命中（card Phase 0 指针写法已变）"
        return src.replace(old, "（**仅进线决策**）：", 1)

    _inject_and_expect("references/templates/checkpoint-card-template.md", mutate, "枚举真源指针", tmp_path)


# ===== v2.12.62 B12：spawn 落地验证「三点接线」+ 诚实边界 =====

def test_b12_spawn_landing_three_point_wiring():
    """B12 可机械部分：真源协议 + 主控卡接线 + status 留痕字段 + 诚实边界声明，四点齐备。

    故障面 = spawn 返回 accepted 但子会话不存在 ⇒ 主控无限等待。**运行期行为不可构建期校验**
    （agent 零 exec），故只锁「协议不许从载体里静默消失」+「留痕字段必须在位」+「必须写明
    构建期无机械兜底」（防后人误以为有门）。
    """
    hp = (ROOT / "references/_shared/执行韧化协议-exec.md").read_text(encoding="utf-8")
    for tok in ("spawn 后", "active runs", "重试 ≤2 次", "机械兜底边界"):
        assert tok in hp, f"执行韧化协议-exec.md 缺「{tok}」（B12）"
    mc = (ROOT / "references/agents/00-主控-coordinator.md").read_text(encoding="utf-8")
    assert "执行韧化协议-exec.md" in mc, "主控卡未指向执行韧化协议真源（B12：协议只活在 _shared）"
    st = (ROOT / "references/templates/status-template.md").read_text(encoding="utf-8")
    assert "spawn_landing" in st, "status-template 缺 spawn_landing 留痕字段（B12）"
    assert "机械兜底边界" in st, "status-template 缺「机械兜底边界」诚实声明（B12）"


def test_b12_status_field_reverse_injection(tmp_path):
    """D-4 副本注入：删掉 status-template 的 spawn_landing 字段 ⇒ flow-check 必须红且点名。"""
    def mutate(src):
        assert "spawn_landing" in src, "反向注入点未命中（spawn_landing 写法已变）"
        return src.replace("spawn_landing", "spawnlanding", 1)

    _inject_and_expect("references/templates/status-template.md", mutate, "spawn_landing", tmp_path)


def test_b12_honest_boundary_reverse_injection(tmp_path):
    """D-4 副本注入：删掉诚实边界声明 ⇒ flow-check 必须红（防「假装有机械门」）。"""
    def mutate(src):
        assert "机械兜底边界" in src, "反向注入点未命中（诚实边界声明写法已变）"
        return src.replace("机械兜底边界", "兜底边界（已删）", 1)

    _inject_and_expect("references/_shared/执行韧化协议-exec.md", mutate, "机械兜底边界", tmp_path)
