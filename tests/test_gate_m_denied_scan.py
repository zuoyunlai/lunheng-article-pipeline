#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""门 M：denied 授权语句扫描的「覆盖面 + 词边界」回归（v2.13.6 修订）

本轮修订的两个发现（均为实测）：
  ① **覆盖假象**：R-22 把 denied 清单外移到 `references/permissions.md` 后，SKILL.md 已无
     `denied:` 行 ⇒ 门 M 的旧提取恒空 ⇒ 只剩回退值 "exec process" 两项被扫，
     **104 项禁用面实际未被覆盖**。
  ② **裸词误报**：旧判据是子串匹配（形如 `主控.{0,40}`?ls`?`）⇒ 命中 `toolsAllow` /
     `tools.subagents` 里的 `ls`；清单一旦扩到 104 项，干净树会被误判为红。

本文件锁死的样本（教训 #334：门类改动必须配「应当放行」的正向样本）：
  ① 覆盖：门 M 的 PASS 行必须报出**完整禁用面项数**（≥100，而不是 2）；
  ② 负向：副本注入「词内含 ls」的上下文（`主控可用 toolsAllow …`）⇒ 门 M 不得误报；
  ③ 正向：副本注入短名工具授权语句（`主控可用 `ls` 读取目录`）⇒ 门 M 必须 ✗ 且点名 ls；
  ④ fail-closed：副本破坏禁用面真源块标题 ⇒ 门 M 必须 ✗（不得静默回退旧两项清单）。

约束：变异注入一律在 `tracked_tree` 临时副本内进行，真源零写入（教训 #333）。
"""
import os
import re
import subprocess
from pathlib import Path

from conftest import tracked_tree

REPO = Path(__file__).resolve().parents[1]
GATE_REL = Path("scripts") / "self-audit-gate.sh"
TRUTH_REL = Path("references") / "permissions.md"
INJECT_REL = Path("references") / "_shared" / "真源" / "glossary-core.md"

ANSI = re.compile(r"\033\[[0-9;]+m")
FIXTURE_LESSONS = Path(__file__).parent / "fixtures" / "lessons-gate.md"


def make_copy(tmp_path: Path) -> Path:
    """整仓副本（tracked-only）—— 变异只注入副本。"""
    dst = tmp_path / "repo"
    tracked_tree(REPO, dst)
    return dst


def run_gate(root: Path):
    env = dict(os.environ)
    env.setdefault("LESSONS_SRC", str(FIXTURE_LESSONS))
    r = subprocess.run(
        ["bash", str(root / GATE_REL)],
        cwd=root, env=env, capture_output=True, text=True, timeout=300,
    )
    return r.returncode, ANSI.sub("", r.stdout + r.stderr)


def gate_m_result(out: str):
    """返回 (ok|None, 门 M 结论行)。门 M.3/M.4 的行不含 `门 M:`，不会误命中。"""
    for line in out.splitlines():
        if "门 M:" in line:
            return ("✓" in line), line.strip()
    return None, ""


def test_gate_m_reports_full_denied_coverage():
    """覆盖：门 M PASS 行必须报出完整禁用面项数（>=100），不得再退化成两项。"""
    rc, out = run_gate(REPO)
    ok, line = gate_m_result(out)
    assert ok is True, f"门 M 应为 ✓（实际：{line or '门 M 行缺失'}）\n{out[-1500:]}"
    m = re.search(r"×\s*(\d+)\s*项禁用面", line)
    assert m, f"门 M PASS 行缺少项数：{line}"
    assert int(m.group(1)) >= 100, f"门 M 覆盖面退化（报 {m.group(1)} 项，应 >=100）：{line}"
    assert rc == 0, f"自审门退出码 {rc} != 0\n{out[-1200:]}"


def test_gate_m_no_false_positive_on_word_internal_hit(tmp_path):
    """负向：上下文命中但工具名只出现在词内部（toolsAllow / tools.subagents）⇒ 不得误报。"""
    root = make_copy(tmp_path)
    target = root / INJECT_REL
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\n\n主控可用 toolsAllow 与 tools.subagents 列出词内样本。\n",
        encoding="utf-8",
    )
    _, out = run_gate(root)
    ok, line = gate_m_result(out)
    assert ok is True, f"词内命中不得误报（门 M 报红）：{line}\n{out[-1200:]}"


def test_gate_m_detects_short_name_authorization(tmp_path):
    """正向：注入短名工具授权语句 ⇒ 门 M 必须 ✗ 并点名该工具。"""
    root = make_copy(tmp_path)
    target = root / INJECT_REL
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\n\n主控可用 `ls` 读取目录（变异样本）。\n",
        encoding="utf-8",
    )
    rc, out = run_gate(root)
    ok, line = gate_m_result(out)
    assert ok is False, f"注入授权语句后门 M 应为 ✗：{line}\n{out[-1200:]}"
    assert "ls" in line, f"门 M 报红但未点名工具：{line}"
    assert rc != 0, "门 M 判红时自审门退出码应非 0"


def test_gate_m_fails_closed_when_truth_block_missing(tmp_path):
    """fail-closed：真源块标题被破坏 ⇒ 门 M 必须 ✗，不得回退旧两项清单静默通过。"""
    root = make_copy(tmp_path)
    truth = root / TRUTH_REL
    text = truth.read_text(encoding="utf-8")
    marker = "禁用面（denied）唯一真源"
    assert marker in text, "禁用面真源块标题缺失，样本前提不成立"
    truth.write_text(text.replace(marker, "禁用面（denied）真源块已被变异移除", 1), encoding="utf-8")
    rc, out = run_gate(root)
    ok, line = gate_m_result(out)
    assert ok is False, f"真源不可读时门 M 应 fail-closed 判红：{line}\n{out[-1200:]}"
    assert rc != 0
