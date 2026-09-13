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
    """P0-2 回归：t6_g14.output 必须同时保留 T6 与 G14 两个产物路径"""
    out = _node("t6_g14")["output"]
    assert isinstance(out, dict), f"t6_g14.output 应为角色→路径映射，实为 {type(out)}"
    assert set(out) == {"T6", "G14"}, f"t6_g14.output 键异常: {sorted(out)}"
    assert out["G14"].startswith("audits/"), f"G14 报告路径丢失: {out['G14']}"


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
    orphan = []
    for n in P:
        for key in ("input", "inputs"):
            for t in FC._paths(n.get(key)):
                if t not in produced:
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
    p = pathlib.Path("references/_shared/phase-order.yaml")
    src = p.read_text(encoding="utf-8")
    # 移除 final_assembly 节点的 output 声明 → 制造 final/定稿.md 无生产者
    bad = src.replace("    output: final/定稿.md\n", "")
    assert bad != src, "反向注入点未命中（final_assembly.output 写法已变）"
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
