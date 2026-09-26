#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""门 C 版本真源守卫（2026-09-25 全面审计修订 R-05）。

背景（2026-09-25 审计探针实测复现）：
  门 C 自称「每个版本戳必须一致」，但其判据是 `grep -qF "$EXPECTED_VERSION"`。
  `EXPECTED_VERSION` 读自 SKILL.md frontmatter；一旦该键被删 / 改名 / 写成空值，
  期望串就是空串，而 **`grep -qF ""` 恒真**（空模式匹配任意行）—— 于是唯一真源损坏时，
  专门守护该真源的门变成 no-op：审计实测把 `version:` 改名为 `versionX:` 后，
  门仍输出「✓ 门 C: 56 文件版本号 v 一致」并 PASS。

  同族缺陷（子串吞噬）：`grep -qF v2.13.3` 对 `v2.13.30` 同样命中 → 版本戳写多一位不报错。

本文件锁两条判据（全部在临时副本上注入；真源零写入由 tracked_tree 与字数快照护栏保证）：
  ① 删/改名 version 键 ⇒ 门 C 必须 **FAIL** 且点名「门 C」（不允许空转绿灯、也不允许静默跳过）
  ② 版本戳 `v2.13.<N>0`（前缀吞噬形态）⇒ 门 C 必须 **FAIL**（边界匹配生效）
"""
import os
import pathlib
import re
import subprocess

import pytest

from conftest import tracked_tree

REPO = pathlib.Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "self-audit-gate.sh"
SKILL = REPO / "SKILL.md"
README = REPO / "README.md"
FIXTURE_LESSONS = pathlib.Path(__file__).parent / "fixtures" / "lessons-gate.md"

ANSI = re.compile(r"\033\[[0-9;]+m")


def run_gate(root: pathlib.Path) -> tuple[int, str]:
    env = dict(os.environ)
    env.setdefault("LESSONS_SRC", str(FIXTURE_LESSONS))
    r = subprocess.run(
        ["bash", str(root / "scripts" / "self-audit-gate.sh")],
        cwd=root, env=env, capture_output=True, text=True, timeout=300,
    )
    return r.returncode, r.stdout + r.stderr


def gate_line(out: str, name: str) -> str:
    """取出含 `门 <name>` 的输出行（去 ANSI），无命中返回空串。"""
    for line in out.splitlines():
        clean = ANSI.sub("", line)
        if f"门 {name}" in clean:
            return clean.strip()
    return ""


def make_copy(tmp_path: pathlib.Path) -> pathlib.Path:
    dst = tmp_path / "repo"
    tracked_tree(REPO, dst)
    return dst


@pytest.fixture()
def repo_copy(tmp_path: pathlib.Path) -> pathlib.Path:
    return make_copy(tmp_path)


def test_gate_c_baseline_passes(repo_copy: pathlib.Path) -> None:
    """未注入时门 C 必须为 ✓（防止把守卫改成「无条件红」）。"""
    rc, out = run_gate(repo_copy)
    line = gate_line(out, "C:")
    assert line.startswith("✓"), f"基线门 C 应为 ✓：{line}\n{out[-1500:]}"


def test_gate_c_fails_when_version_key_renamed(repo_copy: pathlib.Path) -> None:
    """① 把 SKILL.md 的 `version:` 键改名 ⇒ 门 C 必须 FAIL（原实现会打印「v 一致」并 PASS）。"""
    target = repo_copy / SKILL.relative_to(REPO)
    text = target.read_text(encoding="utf-8")
    mutated = re.sub(r"(?m)^(\s*)version:", r"\1versionX:", text, count=1)
    assert mutated != text, "变异未生效：SKILL.md frontmatter 未找到 version 键"
    target.write_text(mutated, encoding="utf-8")

    rc, out = run_gate(repo_copy)
    line = gate_line(out, "C:")
    assert line.startswith("✗"), (
        "SKILL.md 无 version 时门 C 竟仍为 ✓ —— 空转绿灯回归（grep -qF \"\" 恒真）\n"
        f"门 C 行：{line}\n{out[-2000:]}"
    )
    assert "门 C" in out, "失败信息未点名门 C"
    assert rc != 0, "门 C 失败后自审门退出码应为非 0"


def test_gate_c_fails_on_version_prefix_swallow(repo_copy: pathlib.Path) -> None:
    """② 版本戳写长一位（前缀吞噬形态）⇒ 门 C 必须 FAIL（原实现子串匹配会放过）。"""
    target = repo_copy / README.relative_to(REPO)
    text = target.read_text(encoding="utf-8")
    expect = re.search(r'^\s*version:\s*"?([0-9]+\.[0-9]+\.[0-9]+)"?\s*$',
                       (repo_copy / SKILL.relative_to(REPO)).read_text(encoding="utf-8"), re.M).group(1)
    mutated = text.replace(f"> 版本：v{expect}", f"> 版本：v{expect}0", 1)
    assert mutated != text, f"变异未生效：README 顶部未找到 `> 版本：v{expect}`"
    target.write_text(mutated, encoding="utf-8")

    rc, out = run_gate(repo_copy)
    line = gate_line(out, "C:")
    assert line.startswith("✗"), (
        f"版本戳 v{expect}0 被当作 v{expect} 通过 —— 子串吞噬回归\n门 C 行：{line}\n"
        f"{out[-2000:]}"
    )
    assert rc != 0


def test_gate_c_checks_real_files(repo_copy: pathlib.Path) -> None:
    """反向护栏：门 C 的清单必须真有文件、且不一致时点名具体文件（防门被改成空清单）。"""
    target = repo_copy / README.relative_to(REPO)
    text = target.read_text(encoding="utf-8")
    expect = re.search(r'^\s*version:\s*"?([0-9]+\.[0-9]+\.[0-9]+)"?\s*$',
                       (repo_copy / SKILL.relative_to(REPO)).read_text(encoding="utf-8"), re.M).group(1)
    target.write_text(text.replace(f"> 版本：v{expect}", "> 版本：v0.0.0", 1), encoding="utf-8")

    _, out = run_gate(repo_copy)
    line = gate_line(out, "C:")
    assert line.startswith("✗")
    assert "README.md" in line, f"门 C 未点名不一致的文件：{line}"
