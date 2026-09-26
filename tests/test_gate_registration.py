#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""门 S/T/U 条件注册 + 门 Z 项数口径（2026-09-25 全面审计修订 R-06 / R-08）。

背景（2026-09-25 审计实测复现）：
  ① 门 S / T / U 的整个门体包在 `if [ -f ... ] && command -v python3 ...; then` 里，
     **没有 else 分支**。于是「缺 python3」或「真源/检查器被改名」这类最该报警的场景，
     表现为该门**整行不输出**：PASS 从 36 静默降到 35/31，报告上看不出任何异常。
     （审计探针：PATH 去掉 python3 → 门 S/T/U 三行彻底消失、PASS 36→31；
      `mv phase-order.yaml` → 门 S 行消失。）
  ② 门 Z（自审门项数软上限）原写 `_GATE_AX_COUNT=${#PASSED[@]}` —— 有门失败时 FAILED
     不进分母 ⇒ 失败越多、项数越小，「只许降」的软上限在失败时反而变松。

本文件把两条都锁成功能判据（注入一律在临时副本；真源零写入）。
"""
import os
import pathlib
import re
import subprocess

import pytest

from conftest import tracked_tree

REPO = pathlib.Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "self-audit-gate.sh"
FIXTURE_LESSONS = pathlib.Path(__file__).parent / "fixtures" / "lessons-gate.md"

ANSI = re.compile(r"\033\[[0-9;]+m")

GUARDED = {
    "S": "references/_shared/真源/phase-order.yaml",
    "T": "scripts/capability-assert.py",
    "U": "scripts/link-check.py",
}


def run_gate(root: pathlib.Path) -> tuple[int, str]:
    env = dict(os.environ)
    env.setdefault("LESSONS_SRC", str(FIXTURE_LESSONS))
    r = subprocess.run(
        ["bash", str(root / "scripts" / "self-audit-gate.sh")],
        cwd=root, env=env, capture_output=True, text=True, timeout=300,
    )
    return r.returncode, r.stdout + r.stderr


def gate_line(out: str, name: str) -> str:
    for line in out.splitlines():
        clean = ANSI.sub("", line)
        if f"门 {name}" in clean:
            return clean.strip()
    return ""


def make_copy(tmp_path: pathlib.Path) -> pathlib.Path:
    dst = tmp_path / "repo"
    tracked_tree(REPO, dst)
    return dst


def parsed_pass_fail(out: str) -> tuple[int, int]:
    m = re.search(r"PASS:\s*(\d+)\s+FAIL:\s*(\d+)", ANSI.sub("", out))
    assert m, f"未解析到 PASS/FAIL 汇总行：\n{out[-800:]}"
    return int(m.group(1)), int(m.group(2))


def gate_z_count(out: str) -> int:
    for line in ANSI.sub("", out).splitlines():
        m = re.search(r"门 Z:.*?项数\s*(\d+)", line)
        if m:
            return int(m.group(1))
    raise AssertionError(f"未找到门 Z 行：\n{out[-1500:]}")


@pytest.fixture()
def repo_copy(tmp_path: pathlib.Path) -> pathlib.Path:
    return make_copy(tmp_path)


# ---------------------------------------------------------------- 门 S/T/U

@pytest.mark.parametrize("gate,relpath", sorted(GUARDED.items()))
def test_guarded_gate_fails_loud_when_target_missing(repo_copy: pathlib.Path, gate: str, relpath: str) -> None:
    """真源/检查器被改名或缺失 ⇒ 该门必须 FAIL 并点名，不得静默消失。"""
    target = repo_copy / relpath
    assert target.exists(), f"前提失败：{relpath} 不存在"
    target.rename(target.with_suffix(target.suffix + ".MUTATED"))

    rc, out = run_gate(repo_copy)
    line = gate_line(out, f"{gate}:")
    assert line, (
        f"门 {gate} 整行消失 —— 条件注册的静默跳过回归（缺 {relpath} 时必须 FAIL）\n"
        f"{out[-2000:]}"
    )
    assert line.startswith("✗"), f"缺 {relpath} 时门 {gate} 应为 ✗，实得：{line}"
    assert "未执行" in line or "不可判定" in line, f"失败信息未说明「未执行/不可判定」：{line}"
    assert rc != 0, "被守卫门失败后自审门退出码应为非 0"


def test_all_guarded_gates_present_at_baseline(repo_copy: pathlib.Path) -> None:
    """基线（依赖齐备）下 S/T/U 三门都必须出现且为 ✓ —— 防止守卫改成「无条件红」。"""
    rc, out = run_gate(repo_copy)
    for gate in GUARDED:
        line = gate_line(out, f"{gate}:")
        assert line, f"基线下门 {gate} 未输出"
        assert line.startswith("✓"), f"基线下门 {gate} 应为 ✓：{line}"
    assert rc == 0, f"基线下自审门应通过：\n{out[-1500:]}"


def test_gate_count_reconciles_with_summary(repo_copy: pathlib.Path) -> None:
    """门数对账：门 Z 的项数必须等于汇总 PASS+FAIL（防某门失败后总数悄悄变小）。"""
    _, out = run_gate(repo_copy)
    passed, failed = parsed_pass_fail(out)
    # 门 Z 自身不计入 A-X 分母，但会计入最终 PASS 汇总，因此总汇总比门 Z 项数多 1。
    assert gate_z_count(out) == passed + failed - 1, (
        f"门 Z 项数 {gate_z_count(out)} ≠ A-X 门数 {passed} + {failed} - 1\n{out[-1200:]}"
    )


# ------------------------------------------------------------------ 门 Z

def test_gate_z_count_does_not_shrink_on_failure(tmp_path: pathlib.Path) -> None:
    """注入一个失败门 ⇒ 门 Z 项数**不得下降**（原实现 FAILED 不入分母 ⇒ 失败时变松）。"""
    base_root = make_copy(tmp_path / "base")
    _, base_out = run_gate(base_root)
    base_count = gate_z_count(base_out)

    broken = make_copy(tmp_path / "broken")
    (broken / "references" / "agents" / "09-审稿-peer-reviewer.md").rename(
        broken / "references" / "agents" / "09-审稿-peer-reviewer.md.MUTATED"
    )
    _, out = run_gate(broken)
    passed, failed = parsed_pass_fail(out)
    assert failed >= 1, f"注入未产生失败门（用例失效）：\n{out[-1200:]}"
    assert gate_z_count(out) >= base_count, (
        f"有门失败后门 Z 项数从 {base_count} 降到 {gate_z_count(out)} —— "
        f"软上限在失败时变松（FAILED 未计入分母）\n{out[-1200:]}"
    )
    # 门 Z 自身不计入 A-X 分母，但会计入最终 PASS/FAIL 汇总。
    assert gate_z_count(out) == passed + failed - 1


def test_gate_z_source_uses_pass_plus_fail() -> None:
    """源侧不变量：门 Z 口径必须显式含 FAILED（防回退到只数 PASSED）。"""
    src = GATE.read_text(encoding="utf-8")
    m = re.search(r"_GATE_AX_COUNT=([^\n]+)", src)
    assert m, "未找到门 Z 项数赋值"
    expr = m.group(1)
    assert "#PASSED[@]" in expr and "#FAILED[@]" in expr, (
        f"门 Z 项数口径缺少 PASSED/FAILED 之一：{expr}"
    )
