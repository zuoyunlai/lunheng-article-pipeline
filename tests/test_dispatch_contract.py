#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dispatch-contract.py —— 派发话术合同块的现状守卫与反向注入。

背景（2026-09-29 审计修订 P0-1 / P1-4 同源）：G14 复检轮次与 T9 默认触发
此前与 phase-order 真源靠「人记住 N 处同步」，漂移即这两类问题。本测试锁死：
  ① 现状：两个合同块与 phase-order 节点切片一致（块漂移 = 本测试红）；
  ② 反向：块被手改 / 被删除时必须判失败（防门空转，教训 #320 同口径）。
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


def _check_all():
    errors = []
    for nid, name in _mod.NODE_TO_DISPATCH.items():
        errors.extend(_mod.check_one(nid, name))
    return errors


def test_baseline_contracts_match_source():
    """现状守卫：仓库内两个合同块必须与 phase-order 真源一致。"""
    errors = _check_all()
    assert errors == [], errors


def test_generated_block_carries_contract_fields():
    block = _mod.generate_block("g14_style_gate")
    for key in ("node: g14_style_gate", "default: required", "recheck_max_rounds: 2"):
        assert key in block, key
    t9 = _mod.generate_block("t9_review")
    assert "opt_out_key: owner_peer_review_opt_out" in t9
    assert "recheck_max_rounds: 0" in t9


def test_tampered_block_is_caught(tmp_path, monkeypatch):
    """反向注入：手改块内字段 ⇒ check 必须报漂移。"""
    tmp = tmp_path / "dispatch"
    shutil.copytree(_mod.DISPATCH, tmp)
    monkeypatch.setattr(_mod, "DISPATCH", tmp)
    name = "G14-中文AI痕迹检测器.md"
    p = tmp / name
    p.write_text(p.read_text(encoding="utf-8").replace("recheck_max_rounds: 2", "recheck_max_rounds: 3"),
                 encoding="utf-8")
    errors = _mod.check_one("g14_style_gate", name)
    assert errors and "contract drift" in errors[0], errors


def test_missing_block_is_caught(tmp_path, monkeypatch):
    """反向注入：整块被删 ⇒ check 必须报缺失（不得静默通过）。"""
    tmp = tmp_path / "dispatch"
    shutil.copytree(_mod.DISPATCH, tmp)
    monkeypatch.setattr(_mod, "DISPATCH", tmp)
    name = "T9-同行评审.md"
    p = tmp / name
    p.write_text(p.read_text(encoding="utf-8").replace(_mod.BEGIN, "").replace(_mod.END, ""),
                 encoding="utf-8")
    errors = _mod.check_one("t9_review", name)
    assert errors and "missing generated contract block" in errors[0], errors


def test_injection_is_idempotent(tmp_path, monkeypatch):
    """再次生成不得产生第二块（幂等：替换而非追加）。"""
    tmp = tmp_path / "dispatch"
    shutil.copytree(_mod.DISPATCH, tmp)
    monkeypatch.setattr(_mod, "DISPATCH", tmp)
    for nid, name in _mod.NODE_TO_DISPATCH.items():
        p = tmp / name
        text = p.read_text(encoding="utf-8")
        new, changed = _mod.inject_block(text, _mod.generate_block(nid))
        assert not changed, name
        assert new.count(_mod.BEGIN) == 1, name


def test_cli_check_mode_is_green():
    r = subprocess.run([sys.executable, str(SCRIPT), "--check"], cwd=ROOT,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
