#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_frontmatter_budget.py — SKILL.md frontmatter 预算事前拦截回归门（v2.15.9，审计 P2）

背景（2026-10-03 全量审计「frontmatter 预算」项）：
  门 V 锁的是 SKILL.md **全文**字符数，而 v2.15.7 踩的坑是 **frontmatter 单独**
  撑到 9487 字符（R-22 常驻预算 <9000）—— 当时全文门并未报警（正文够短），
  直到事后 CI 才红。缺口 = 没有人管 frontmatter 自己的预算。

修复：门 V 增补 frontmatter 单独预算判据（9000 字符），结论并入既有体量棘轮行
  （守门 Z 项数上限，不新增结论行）。

本文件锁死三件事：
  ① 正向：干净树 → 门 V 行同时报告体量 + frontmatter 两项数值；RC=0
  ② 红样本：注入超预算 frontmatter（> 9000）→ 门 V 必红并点名 R-22
  ③ 解析守卫：frontmatter 分隔符缺失 → 判「不可判定」而非静默通过
"""
import os
import pathlib
import re
import subprocess

from conftest import tracked_tree

import pytest

ROOT = pathlib.Path(__file__).parent.parent
GATE = ROOT / "scripts" / "self-audit-gate.sh"
LESSONS_FIXTURE = ROOT / "tests" / "fixtures" / "lessons-gate.md"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _run(root, env_extra=None):
    env = dict(os.environ)
    env.setdefault("LESSONS_SRC", str(LESSONS_FIXTURE))
    if env_extra:
        env.update(env_extra)
    r = subprocess.run(["bash", str(root / "scripts" / "self-audit-gate.sh")],
                       capture_output=True, text=True, cwd=str(root), timeout=300, env=env)
    return r.returncode, ANSI.sub("", r.stdout + r.stderr)


def _v_lines(out):
    return [l for l in out.splitlines() if "门 V:" in l]


def test_clean_tree_reports_both_budgets():
    """① 正向：门 V 行须同时含体量数值与 frontmatter 数值。"""
    rc, out = _run(ROOT)
    lines = _v_lines(out)
    joined = " ".join(lines)
    assert "frontmatter" in joined, f"门 V 未报告 frontmatter 预算：{lines}"
    assert re.search(r"frontmatter \d+ ≤ \d+", joined), f"frontmatter 数值格式不符：{lines}"
    assert "体量棘轮" in joined, f"体量棘轮结论行丢失：{lines}"
    assert rc == 0, f"干净树不得红：\n{out[-600:]}"


def test_over_budget_frontmatter_fails(tmp_path):
    """② 红样本：frontmatter 超 9000 字符 ⇒ 门 V 红并点名 R-22。"""
    dst = tmp_path / "repo"
    tracked_tree(ROOT, dst)
    skill = dst / "SKILL.md"
    t = skill.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", t, re.S)
    assert m, "样本 SKILL.md 无 frontmatter"
    # 在 frontmatter 内注入超预算内容
    blob = "\n# " + ("填充" * 4000)
    mutated = "---\n" + m.group(1) + blob + "\n---" + t[m.end():]
    skill.write_text(mutated, encoding="utf-8")

    rc, out = _run(dst)
    lines = _v_lines(out)
    assert any(l.lstrip().startswith("✗") and "frontmatter" in l for l in lines), \
        f"超预算 frontmatter 未报红：{lines}"
    assert any("R-22" in l for l in lines), f"未点名 R-22：{lines}"
    assert rc != 0, "门 V 红时自审门退出码应非 0"


def test_missing_delimiter_is_not_silent(tmp_path):
    """③ 解析守卫：frontmatter 分隔符缺失 ⇒ 判「不可判定」而非静默通过。"""
    dst = tmp_path / "repo"
    tracked_tree(ROOT, dst)
    skill = dst / "SKILL.md"
    t = skill.read_text(encoding="utf-8")
    skill.write_text(t.replace("---\n", "\n", 1), encoding="utf-8")
    rc, out = _run(dst)
    lines = _v_lines(out)
    assert any("不可解析" in l for l in lines), f"分隔符缺失未判不可判定：{lines}"
    assert rc != 0, "不可判定应红（不允许静默通过）"
