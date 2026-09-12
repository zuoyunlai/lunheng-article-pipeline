#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_gate_h_reverse_diff.py — 门 H「反向差集」解析口径回归门（v2.12.33 候选新增）

背景（2026-09-12 实测，教训 #352 的换形复发）：
  门 H 的反向差集（`scripts/self-audit-gate.sh`）原本用
  `grep -E '^#{2,4} (教训 )?#[0-9]+.*论衡'` 解析主真源最大编号 —— **要求教训标题行内含
  「论衡」二字**。于是主真源 `memory/lessons.md` 中
  `## #352 半成品版本戳：只改受管文件不写 CHANGELOG/README 正文 = 带红门`
  这类**标题不含「论衡」的论衡类教训对反向差集完全不可见**：真源已到 #352、索引仍声明 #351
  时，门 H 照样 PASS（漏报）；直到 #353 标题恰好带「论衡」才暴露落后。
  这正是门 H 当初为 #317/#318/#319（「真源已有新教训、索引未跟」）修的同一类问题的复发 ——
  编号解析修了，却把「标题必须含论衡」当成了隐含前提。

现口径：按「标题形如 `## #N ` 的编号」取最大编号，再用排除表 `LUNHENG_LESSON_EXCLUDE`
  （默认 `340 341`，宿主/通用类，索引设计上不入本索引）剔除非论衡编号；未列入者一律按论衡类
  计入 —— 宁可多报（红）不可漏报。

本文件锁死的样本（教训 #334：门类改动必须配「应当放行」的正向样本）：
  ① 正向：真源新增「标题不含论衡字样」的编号 → 索引落后必须红（旧口径会漏报）
  ② 负向：索引与真源一致 → 不得误报（全门 25 PASS / 0 FAIL）
  ③ 负向：索引**合法领先**真源 → 不得误报
  ④ 排除表：宿主/通用类编号（#340/#341 同型）不计入最大编号，未列入者照常计入
  ⑤ 元测试：排除表默认值不得被静默清空
"""
import os
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).parent.parent
GATE = ROOT / "scripts" / "self-audit-gate.sh"
INDEX = ROOT / "references" / "_shared" / "教训索引.md"

HOME = pathlib.Path.home()
REAL_SRC = pathlib.Path(os.environ.get(
    "LESSONS_SRC", HOME / ".openclaw" / "workspace" / "memory" / "lessons.md"))

REVERSE_DIFF = "门 H: 教训索引最大编号"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _idx_decl():
    """索引声明的「当前最大编号 #N」"""
    m = re.search(r"当前最大编号 \*\*#(\d+)\*\*", INDEX.read_text(encoding="utf-8"))
    assert m, "教训索引缺「当前最大编号 **#N**」声明"
    return int(m.group(1))


def _run_gate(lessons_src, extra_env=None):
    """返回 (CompletedProcess, 已剥 ANSI 的 stdout)"""
    env = os.environ.copy()
    env["LESSONS_SRC"] = str(lessons_src)
    if extra_env:
        env.update(extra_env)
    r = subprocess.run(["bash", str(GATE)], capture_output=True, text=True,
                       cwd=str(ROOT), env=env)
    return r, ANSI.sub("", r.stdout)


def _reverse_diff_lines(out):
    return [l for l in out.splitlines() if REVERSE_DIFF in l]


def _src_numbers(text):
    return [int(n) for n in re.findall(r"^#{2,4} (?:教训 )?#(\d+)", text, re.M)]


requires_real_src = pytest.mark.skipif(
    not REAL_SRC.is_file(), reason=f"主真源不可达：{REAL_SRC}（门 H 为软门，跳过）")


def _real_src_copy(tmp_path):
    return tmp_path / "lessons.md"


# ---------------- ① 正向：标题不含「论衡」的新编号必须红 ----------------

@requires_real_src
def test_new_lesson_without_lunheng_in_title_is_flagged(tmp_path):
    idx = _idx_decl()
    new_num = idx + 1
    probe = tmp_path / "lessons.md"
    probe.write_text(
        REAL_SRC.read_text(encoding="utf-8")
        + f"\n## #{new_num} 复现样本：标题刻意不含那两个字（2026-09-12）\n\n- 探针。\n",
        encoding="utf-8")
    assert "论衡" not in f"复现样本：标题刻意不含那两个字", "样本标题必须不含「论衡」"

    r, out = _run_gate(probe)
    lines = _reverse_diff_lines(out)
    assert lines, f"门 H 未输出反向差集行：\n{out}"
    assert r.returncode != 0, f"真源已到 #{new_num}、索引仍声明 #{idx}，门 H 却放行（漏报）：\n{out}"
    assert any(l.lstrip().startswith("✗") and f"#{new_num}" in l for l in lines), \
        f"反向差集未点名 #{new_num}：{lines}"
    # 除该门外不得再红（样本只注入一个变量）
    reds = [l for l in out.splitlines() if l.lstrip().startswith("✗")]
    assert len(reds) == 1, f"样本应只红 1 门，实际 {len(reds)}：{reds}"


# ---------------- ② 负向：索引与真源一致不得误报 ----------------

@requires_real_src
def test_no_false_positive_when_index_matches_source(tmp_path):
    r, out = _run_gate(REAL_SRC)
    assert r.returncode == 0, f"索引与真源一致却报红：\n{out}"
    assert "FAIL: 0" in out, f"存在误报门：\n{out}"
    line = _reverse_diff_lines(out)[-1]
    assert f"索引 #{_idx_decl()} ≥ 真源 #{_idx_decl()}" in line, \
        f"解析出的真源最大编号与索引声明不一致（应与排除表无关）：{line}"


# ---------------- ③ 负向：索引合法领先不得误报 ----------------

@requires_real_src
def test_no_false_positive_when_index_leads_source(tmp_path):
    """合法领先样本：把真源中 >= 索引声明-1 的编号全部列入排除表 ⇒ 解析出的真源最大值 < 索引声明。
    门 H 只检「索引落后」，故必须放行（旧代码同此语义，此处锁死不得回归成双向硬校验）。"""
    idx = _idx_decl()
    nums = sorted(set(_src_numbers(REAL_SRC.read_text(encoding="utf-8"))))
    exclude = " ".join(str(n) for n in nums if n >= idx - 1) or "0"
    r, out = _run_gate(REAL_SRC, {"LUNHENG_LESSON_EXCLUDE": exclude})
    assert r.returncode == 0, f"索引合法领先却报红：\n{out}"
    line = _reverse_diff_lines(out)[-1]
    assert line.lstrip().startswith("✓") and "未落后主真源" in line, \
        f"合法领先被判为落后：{line}"
    assert "≥ 真源 #" in line, f"反向差集行格式异常：{line}"


# ---------------- ④ 排除表：宿主/通用类编号不计入 ----------------

def test_host_class_numbers_excluded_from_max(tmp_path):
    probe = tmp_path / "lessons.md"
    probe.write_text(
        "## #340 宿主/通用类样本（索引设计上不入本索引）\n"
        "## #341 宿主/通用类样本二\n"
        "## #342 论衡类样本（标题不含「论衡」字样）\n",
        encoding="utf-8")
    _r, out = _run_gate(probe)
    line = _reverse_diff_lines(out)[-1]
    assert "真源 #342" in line, f"#340/#341 未被排除或 #342 未被计入：{line}"
    assert "#341" not in line, f"排除表失效：{line}"


# ---------------- ⑤ 元测试：排除表默认值不得被清空 ----------------

def test_default_exclusion_table_not_empty():
    src = GATE.read_text(encoding="utf-8")
    m = re.search(r'LUNHENG_LESSON_EXCLUDE="\$\{LUNHENG_LESSON_EXCLUDE:-([^}]*)\}"', src)
    assert m, "门 H 缺 LUNHENG_LESSON_EXCLUDE 默认值声明"
    assert m.group(1).split() == ["340", "341"], \
        f"排除表默认值被改动（应恰为宿主/通用类 #340/#341，只许按需追加）：{m.group(1)!r}"
    assert "论衡" not in src.split("SRC_MAX=")[1].split("if [ -n")[0], \
        "SRC_MAX 解析口径不得再依赖标题里的「论衡」字样"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
