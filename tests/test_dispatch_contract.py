#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_dispatch_contract.py — 派发/轮次契约三族判据的真源化守卫与反向注入（2026-10-05 v3 重写）。

背景（架构评审 v3 R2 收口；前身 = 2026-09-29 第二批机械门）：
  旧生成器把 recheck_max_rounds 硬编码在 NODE_CONSTANTS（t9 的 0 在切片中任何层级
  都不存在 = 纯代码侧发明），--check 比较「生成结果 vs 生成结果」⇒ 常量漂移对门不可见。
  现口径：全部契约面从切片现算，覆盖集 = 切片 `dispatch:` 字段（零手工登记）。

本文件锁死三族判据 + 两条棘轮：
  ① 现状：dispatch 合同块 / 轮次块（pipeline-overview 仲裁段）/ owner 载体检查全绿；
  ② 反向：块被手改 / 被删 / 载体丢键 / 切片轮限改值 ⇒ 必红（教训 #320/#399 口径）；
  ③ 棘轮：NODE_CONSTANTS / NODE_TO_DISPATCH 常量不得还魂（防代码侧真源回潮）。
"""
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "dispatch-contract.py"

_spec = importlib.util.spec_from_file_location("dispatch_contract", SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def _all_errors():
    errors = []
    for nid, rel in _mod.covered_nodes():
        errors.extend(_mod.check_one(nid, rel))
    errors.extend(_mod.check_rounds())
    errors.extend(_mod.check_owner_carriers())
    return errors


def _tmp_root_with_dispatch(tmp_path):
    tmp_root = tmp_path / "root"
    (tmp_root / "references").mkdir(parents=True)
    shutil.copytree(ROOT / "references" / "dispatch", tmp_root / "references" / "dispatch")
    return tmp_root


# ---------------- ① 现状守卫 ----------------

def test_baseline_all_three_families_match_source():
    """三族判据全绿（dispatch 块 + 轮次块 + owner 载体）与切片真源一致。"""
    assert _all_errors() == []


def test_covered_nodes_derived_from_slice_dispatch_field():
    """覆盖集 = 切片 dispatch: 字段现算（新增派发节点零手工登记，v3 S2-3）。"""
    nodes = {nid for nid, _ in _mod.covered_nodes()}
    assert {"g14_style_gate", "t9_review", "t1b_targeted_review"} <= nodes
    for nid, rel in _mod.covered_nodes():
        assert _mod._load_node(nid).get("dispatch") == rel, f"{nid} 覆盖登记与切片 dispatch 字段不一致"


def test_generated_blocks_carry_slice_fields():
    """块字段直读切片：g14=2 / t9=0 / t1b max_rounds=2（无代码侧常量）。"""
    g14 = _mod.generate_block("g14_style_gate")
    assert "node: g14_style_gate" in g14
    assert "default: required" in g14
    assert "recheck_max_rounds: 2" in g14
    t9 = _mod.generate_block("t9_review")
    assert "recheck_max_rounds: 0" in t9
    assert "opt_out_key: owner_peer_review_opt_out" in t9
    t1b = _mod.generate_block("t1b_targeted_review")
    assert "max_rounds: 2" in t1b
    assert "condition: t5_t7_report_unverified_references" in t1b


def test_rounds_block_locks_all_slice_round_fields():
    """轮次块 = 全仓轮限唯一机械登记：切片每个轮限字段都必须出现在块内（v3 S2-c）。"""
    block = _mod.generate_rounds_block()
    decls = {(nid, key, val) for _, nid, key, val in _mod.rounds_declarations()}
    # 基线锁（v3 实测 5 项；增删轮限字段 = 有意识地同步更新本基线）
    assert {("audit_revision", "max_rounds", 2),
            ("t1b_targeted_review", "max_rounds", 2),
            ("g14_style_gate", "recheck_max_rounds", 2),
            ("t5_style_revision", "style_recheck_rounds_max", 2),
            ("t9_review", "recheck_max_rounds", 0)} <= decls
    for nid, key, val in decls:
        assert f"{nid}.{key}: {val}" in block, f"轮次块缺 {nid}.{key}"


def test_owner_carrier_baseline_green():
    """owner 节点（t9b / methodology，无 dispatch 文件）的 opt-out 键在登记载体中全部在位。"""
    assert _mod.check_owner_carriers() == []


# ---------------- ② 反向注入（漂移必红） ----------------

def test_tampered_dispatch_block_is_caught(tmp_path, monkeypatch):
    """手改块内字段（2→3）⇒ check 必须报漂移。"""
    tmp_root = _tmp_root_with_dispatch(tmp_path)
    monkeypatch.setattr(_mod, "ROOT", tmp_root)
    rel = "references/dispatch/G14-中文AI痕迹检测器.md"
    p = tmp_root / rel
    p.write_text(p.read_text(encoding="utf-8").replace(
        "recheck_max_rounds: 2", "recheck_max_rounds: 3"), encoding="utf-8")
    errors = _mod.check_one("g14_style_gate", rel)
    assert errors and "contract drift" in errors[0], errors


def test_missing_dispatch_block_is_caught(tmp_path, monkeypatch):
    """整块被删 ⇒ check 必须报缺失（不得静默通过）。"""
    tmp_root = _tmp_root_with_dispatch(tmp_path)
    monkeypatch.setattr(_mod, "ROOT", tmp_root)
    rel = "references/dispatch/T9-同行评审.md"
    p = tmp_root / rel
    p.write_text(p.read_text(encoding="utf-8").replace(
        _mod.BEGIN, "").replace(_mod.END, ""), encoding="utf-8")
    errors = _mod.check_one("t9_review", rel)
    assert errors and "missing generated contract block" in errors[0], errors


def test_tampered_rounds_block_is_caught(tmp_path, monkeypatch):
    """轮次块被手改（2→9）⇒ check_rounds 必须报漂移。"""
    ov = tmp_path / "pipeline-overview.md"
    text = _mod.OVERVIEW.read_text(encoding="utf-8")
    ov.write_text(text.replace(
        "audit_revision.max_rounds: 2", "audit_revision.max_rounds: 9"), encoding="utf-8")
    monkeypatch.setattr(_mod, "OVERVIEW", ov)
    errors = _mod.check_rounds()
    assert errors and "pipeline-overview.md" in errors[0], errors


def test_missing_rounds_block_is_caught(tmp_path, monkeypatch):
    """轮次块被删 ⇒ check_rounds 必须报缺失。"""
    ov = tmp_path / "pipeline-overview.md"
    text = _mod.OVERVIEW.read_text(encoding="utf-8")
    ov.write_text(text.replace(_mod.ROUNDS_BEGIN, "").replace(_mod.ROUNDS_END, ""),
                  encoding="utf-8")
    monkeypatch.setattr(_mod, "OVERVIEW", ov)
    errors = _mod.check_rounds()
    assert errors and "missing rounds contract block" in errors[0], errors


def test_owner_carrier_missing_key_is_caught(tmp_path):
    """owner 节点 opt-out 载体丢键 ⇒ 红（owner 契约断链，v3 S2-b）。"""
    carrier = tmp_path / "references" / "templates" / "任务简报-template.md"
    carrier.parent.mkdir(parents=True)
    carrier.write_text("# 模板（测试副本，无 opt-out 键）", encoding="utf-8")
    errors = _mod.check_owner_carriers(root=tmp_path)
    assert any("owner_stress_test_opt_out" in e or "methodology_snapshot_opt_out" in e
               for e in errors), errors


def test_slice_round_change_propagates(tmp_path, monkeypatch):
    """切片轮限改值 ⇒ 块跟着变（防代码侧常量覆盖真源 = v3 R2② 核心回归）。"""
    dst = tmp_path / "phase-order"
    shutil.copytree(_mod.PHASE_ORDER, dst)
    p = dst / "g14_style_gate.yaml"
    text = p.read_text(encoding="utf-8")
    assert "recheck_max_rounds: 2" in text
    p.write_text(text.replace("recheck_max_rounds: 2", "recheck_max_rounds: 5"),
                 encoding="utf-8")
    monkeypatch.setattr(_mod, "PHASE_ORDER", dst)
    assert "recheck_max_rounds: 5" in _mod.generate_block("g14_style_gate")
    block = _mod.generate_rounds_block()
    assert "g14_style_gate.recheck_max_rounds: 5" in block
    assert "g14_style_gate.recheck_max_rounds: 2" not in block


# ---------------- ③ 幂等 + 棘轮 + CLI ----------------

def test_injection_is_idempotent(tmp_path, monkeypatch):
    """再次生成不得产生第二块（幂等：替换而非追加）。"""
    tmp_root = _tmp_root_with_dispatch(tmp_path)
    monkeypatch.setattr(_mod, "ROOT", tmp_root)
    for nid, rel in _mod.covered_nodes():
        p = tmp_root / rel
        text = p.read_text(encoding="utf-8")
        new, changed = _mod.inject_block(text, _mod.generate_block(nid))
        assert not changed, rel
        assert new.count(_mod.BEGIN) == 1, rel


def test_no_code_side_constants_left():
    """棘轮：代码侧真源常量不得还魂（v3 R2② 根因 = NODE_CONSTANTS 无源硬编码）。"""
    assert not hasattr(_mod, "NODE_CONSTANTS"), "代码侧常量还魂 = 真源倒置回潮"
    assert not hasattr(_mod, "NODE_TO_DISPATCH"), "覆盖集必须由切片 dispatch: 字段现算"


def test_cli_check_mode_is_green():
    r = subprocess.run([sys.executable, str(SCRIPT), "--check"], cwd=ROOT,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
