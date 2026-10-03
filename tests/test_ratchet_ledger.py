#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_ratchet_ledger.py — 门 Y「棘轮重定台账」回归门（v2.15.9 新增，审计 P1）

背景（2026-10-03 全量审计 P1）：
  门 Y 的「只许降」棘轮存在**合法上涨通道** —— v2.15.8 按「实测重定」把
  00-主控-扩展职责.md 69808→74923 B、phase-order.yaml 63928→66574 B。
  规则文本说「后续仍只许降」，但**重定动作本身不受机制约束**：注释里写一句
  「功能性新增」即可永久合法（B1-B7 / v2.12.65 / v2.12.70 / v2.12.72 /
  v2.13.5 / v2.13.6 / v2.15.7 已连续使用该通道）。

修复：把「重定」从豁免变成**债务** —— 每次上涨须登记回落目标 + 截止版本，
  门 Y 校验债务未过期（真源 = references/_shared/治理/ratchet-ledger.md）。

本文件锁死四件事：
  ① 正向：干净树 → 台账结论行出现「台账」字样，且条目数与台账文件一致
  ② 零未结：台账只含 settled ⇒ 结论含「棘轮无未结债务」
  ③ 过期红样本：注入一条 due_version 低于当前版本的 open 债务 ⇒ 告警点名（软门不红）
  ④ 缺台账：台账文件不存在 ⇒ 告警「未执行」（防账本消失后静默通过）
"""
import os
import pathlib
import re
import shutil
import subprocess

import pytest

from conftest import tracked_tree

ROOT = pathlib.Path(__file__).parent.parent
GATE = ROOT / "scripts" / "self-audit-gate.sh"
LEDGER = ROOT / "references" / "_shared" / "治理" / "ratchet-ledger.md"
LESSONS_FIXTURE = ROOT / "tests" / "fixtures" / "lessons-gate.md"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _run_gate(root=None, extra_env=None):
    root = root or ROOT
    env = os.environ.copy()
    env.setdefault("LESSONS_SRC", str(LESSONS_FIXTURE))
    if extra_env:
        env.update(extra_env)
    r = subprocess.run(["bash", str(root / "scripts" / "self-audit-gate.sh")],
                       capture_output=True, text=True, cwd=str(root), env=env, timeout=300)
    return r, ANSI.sub("", r.stdout)


def _y_lines(out):
    return [l for l in out.splitlines() if "门 Y" in l]


def _ledger_note(out):
    """门 Y「清单全部在位」行里的台账附注"""
    for l in _y_lines(out):
        if "清单全部在位" in l or "棘轮无未结债务" in l:
            return l
    return ""


def test_ledger_exists_and_parses():
    """台账必须在位且能被门内解析器读出条目（防账本腐烂成空指针）。"""
    assert LEDGER.is_file(), f"棘轮台账缺失：{LEDGER}"
    text = LEDGER.read_text(encoding="utf-8")
    assert "debt:" in text and "structural_exempt:" in text, "台账 §一/§二 键缺失"
    items = re.findall(r"^\s*-\s*path:", text, re.M)
    assert items, "台账 debt 无条目（重定上涨将无账可查）"


def test_clean_tree_reports_open_debt_count():
    """① 正向：干净树 → 台账结论出现且与条目数一致；软门不红。"""
    r, out = _run_gate()
    note = _ledger_note(out)
    assert "台账" in note or "无未结债务" in note, f"门 Y 未输出台账结论：{_y_lines(out)}"
    if (ROOT / LEDGER.relative_to(ROOT)).is_file():
        text = LEDGER.read_text(encoding="utf-8")
        expected = len(re.findall(r"^\s*-\s*path:", text, re.M))
        if "未结" in note:
            m = re.search(r"(\d+)\s*条未结", note)
            assert m and int(m.group(1)) == expected, \
                f"台账条目数 {expected} 与门内报告不一致：{note}"
    assert r.returncode == 0, f"软门不得改 exit code：\n{out[-800:]}"


def test_all_settled_reports_clean(tmp_path):
    """② 零未结：台账只含 settled ⇒ 结论含「棘轮无未结债务」。"""
    dst = tmp_path / "repo"
    tracked_tree(ROOT, dst)
    ledger = dst / "references" / "_shared" / "治理" / "ratchet-ledger.md"
    text = ledger.read_text(encoding="utf-8")
    ledger.write_text(re.sub(r'status: "open"', 'status: "settled"', text), encoding="utf-8")
    r, out = _run_gate(dst)
    assert "棘轮无未结债务" in out, f"全 settled 未报无未结：{_y_lines(out)}"


def test_expired_debt_warns(tmp_path):
    """③ 过期红样本：due_version 低于当前版本 ⇒ 告警点名（软门，RC 仍 0）。"""
    dst = tmp_path / "repo"
    tracked_tree(ROOT, dst)
    ledger = dst / "references" / "_shared" / "治理" / "ratchet-ledger.md"
    text = ledger.read_text(encoding="utf-8")
    # 把第一条 open 债务的截止版本压到 1.0.0（必然已过期）
    ledger.write_text(re.sub(r'due_version: "2\.18\.0"', 'due_version: "1.0.0"', text, count=1),
                      encoding="utf-8")
    r, out = _run_gate(dst)
    warns = [l for l in _y_lines(out) if "过期" in l]
    assert warns, f"过期债务未告警：{_y_lines(out)}"
    assert r.returncode == 0, "过期告警属软门语义，不得改 exit code"


def test_missing_ledger_warns(tmp_path):
    """④ 缺台账 ⇒ 告警「未执行」（防账本消失后静默通过）。"""
    dst = tmp_path / "repo"
    tracked_tree(ROOT, dst)
    ledger = dst / "references" / "_shared" / "治理" / "ratchet-ledger.md"
    ledger.unlink()
    r, out = _run_gate(dst)
    lines = _y_lines(out)
    assert any("台账" in l for l in lines), f"缺台账未告警：{lines}"
    assert r.returncode == 0, "缺台账告警属软门语义"


def test_gate_y_still_within_gate_z_ceiling():
    """门 Z 棘轮：门 Y 结论行数不得回涨（本次增补须并入既有行，不新增结论行）。"""
    r, out = _run_gate()
    m = re.search(r"门 Z: 自审门项数\s*(\d+)", out)
    assert m, f"未找到门 Z 行：\n{out[-600:]}"
    assert int(m.group(1)) <= 40, f"门 Z 项数 {m.group(1)} 超软上限 40（加门须先合并旧门）"
