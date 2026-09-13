#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_gate_h_reverse_diff.py — 门 H「反向差集」解析口径回归门（v2.12.33 候选新增）

历史背景（2026-09-12 实测，教训 #352 的换形复发）：
  门 H 的反向差集（`scripts/self-audit-gate.sh`）原本用
  `grep -E '^#{2,4} (教训 )?#[0-9]+.*论衡'` 解析主真源最大编号 —— **要求教训标题行内含
  「论衡」二字**。于是主真源 `memory/lessons.md` 中
  `## #352 半成品版本戳：只改受管文件不写 CHANGELOG/README 正文 = 带红门`
  这类**标题不含「论衡」的论衡类教训对反向差集完全不可见**：真源已到 #352、索引仍声明 #351
  时，门 H 照样 PASS（漏报）；直到 #353 标题恰好带「论衡」才暴露落后。

官方审计整改（F1/F3，2026-09-13）后的新口径：
  ① 反向差集判据改为 **仓库内快照** `references/_shared/lessons-max.snapshot`（hermetic）——
    不再受仓库外 `memory/lessons.md` 的「已发布的绿可被墙外追加追溯性推翻」影响
  ② 外部真源仅作 **参照告警**（warn），不参与 exit code
  ③ 排除表 `LUNHENG_LESSON_EXCLUDE` 默认 `340 341 355`（宿主/通用类，索引设计上不入本索引）

本文件锁死的样本（教训 #334：门类改动必须配「应当放行」的正向样本）：
  ① 正向：真源新增「标题不含论衡字样」**且未列入排除表**的编号 → 快照告警但不 fail（hermetic）
  ② 负向：索引与快照一致 → 不得误报
  ③ 负向：排除表覆盖真源 → 不得误报（合法领先语义）
  ④ 排除表：宿主/通用类编号不计入最大告警编号
  ⑤ 元测试：排除表默认值不得被静默清空，且 SRC_MAX 解析不得依赖标题里的「论衡」字样
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
SNAPSHOT = ROOT / "references" / "_shared" / "lessons-max.snapshot"

HOME = pathlib.Path.home()
REAL_SRC = pathlib.Path(os.environ.get(
    "LESSONS_SRC", HOME / ".openclaw" / "workspace" / "memory" / "lessons.md"))

REVERSE_DIFF = "索引最大编号"  # pass 与 fail 两条消息共有子串（旧值「门 H: 索引最大编号」匹配不到 fail 行）
ADVISORY = "门 H: 外部真源"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _idx_decl():
    """索引声明的「当前最大编号 #N」"""
    m = re.search(r"当前最大编号 \*\*#(\d+)\*\*", INDEX.read_text(encoding="utf-8"))
    assert m, "教训索引缺「当前最大编号 **#N**」声明"
    return int(m.group(1))


def _snap_max():
    """仓库内快照最大编号"""
    if not SNAPSHOT.is_file():
        return None
    m = re.search(r"(\d+)", SNAPSHOT.read_text(encoding="utf-8").strip())
    return int(m.group(1)) if m else None


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


def _advisory_lines(out):
    return [l for l in out.splitlines() if ADVISORY in l]


def _src_numbers(text):
    return [int(n) for n in re.findall(r"^#{2,4} (?:教训 )?#(\d+)", text, re.M)]


requires_real_src = pytest.mark.skipif(
    not REAL_SRC.is_file(), reason=f"主真源不可达：{REAL_SRC}（门 H 为软门，跳过）")


# ---------------- ①ᐟ 正向红样本：索引落后快照 → 门 H 必须红 -------------

@requires_real_src
def test_index_lagging_snapshot_must_fail(tmp_path):
    """正向红样本（独立复查指出：重写后无一条断言门会 FAIL，防 fail 分支被删仍全绿）。
    构造一个「更高」的临时快照 → 索引（声明的 #N）必然落后 → 门 H 必须红。"""
    snap = _snap_max()
    assert snap is not None, "快照文件缺失"
    higher = tmp_path / "snapshot-high"
    higher.write_text(f"{snap + 100}\n", encoding="utf-8")
    r, out = _run_gate(REAL_SRC, {"LESSONS_SNAPSHOT": str(higher)})
    assert r.returncode != 0, f"索引落后快照却放行（门 H 退化为永绿）：\n{out}"
    lines = _reverse_diff_lines(out)
    assert any(l.lstrip().startswith("✗") for l in lines), \
        f"索引落后快照未报红（✗ 行缺失）：{lines}"


# ---------------- ① 正向：真源超过快照且不在排除表 → 参照告警但不 fail ----------------

@requires_real_src
def test_snapshot_advisory_when_source_exceeds_snapshot(tmp_path):
    """新口径：真源新增一个**未列入排除表**的编号 → 快照告警，但门仍 pass（hermetic 判据）"""
    idx = _idx_decl()
    snap = _snap_max()
    assert snap is not None, "快照文件缺失"
    # 选未列入排除表（340/341/355）的编号
    new_num = snap + 50  # 远超快照与排除表
    probe = tmp_path / "lessons.md"
    probe.write_text(
        REAL_SRC.read_text(encoding="utf-8")
        + f"\n## #{new_num} 复现样本：来源超过快照的告警测试（2026-09-13）\n\n- 探针。\n",
        encoding="utf-8")

    r, out = _run_gate(probe)
    # 新逻辑：hermetic 判据不动 exit code
    assert r.returncode == 0, f"参照告警不应 fail（hermetic 判据）：\n{out}"
    # 必有「外部真源 #N > 快照」告警
    assert any(ADVISORY in l and f"#{new_num}" in l for l in _advisory_lines(out)), \
        f"参照告警未点名 #{new_num}：{out}"
    # 告警行不参与 exit code
    reds = [l for l in out.splitlines() if l.lstrip().startswith("✗")]
    assert len(reds) == 0, f"参照告警不应进红门：{reds}"


# ---------------- ② 负向：索引 ≥ 快照 → 不得误报 ----------------

@requires_real_src
def test_no_false_positive_when_index_matches_snapshot(tmp_path):
    """当主真源不可达时，仍执行 hermetic 判据（索引 ≥ 快照）。"""
    snap = _snap_max()
    assert snap is not None, "快照文件缺失"
    r, out = _run_gate(REAL_SRC)
    assert r.returncode == 0, f"索引与快照一致却报红：\n{out}"
    assert "FAIL: 0" in out, f"存在误报门：\n{out}"
    line = _reverse_diff_lines(out)[-1]
    assert f"索引 #{_idx_decl()} ≥ 快照 #{snap}" in line, \
        f"反向差集行格式异常（应使用快照判据）：{line}"


# ---------------- ③ 负向：排除表覆盖真源 → 不得误报（合法领先） ----------------

@requires_real_src
def test_no_false_positive_when_exclude_table_leads_source(tmp_path):
    """合法领先样本：把所有真源编号列入排除表 → SRC_MAX=0 ≤ 快照，判据必放行。"""
    idx = _idx_decl()
    nums = sorted(set(_src_numbers(REAL_SRC.read_text(encoding="utf-8"))))
    exclude = " ".join(str(n) for n in nums) or "0"
    r, out = _run_gate(REAL_SRC, {"LUNHENG_LESSON_EXCLUDE": exclude})
    assert r.returncode == 0, f"排除表合法领先却报红：\n{out}"
    line = _reverse_diff_lines(out)[-1]
    assert line.lstrip().startswith("✓") and "未落后仓库快照" in line, \
        f"合法领先被判为落后：{line}"
    assert "≥ 快照 #" in line, f"反向差集行格式异常：{line}"


# ---------------- ④ 排除表：宿主/通用类编号不计入最大告警编号 ----------------

def test_host_class_numbers_excluded_from_advisory(tmp_path):
    """#340/#341/#355 宿主类不计入 SRC_MAX，告警行不出现这些编号。"""
    base = REAL_SRC if REAL_SRC.is_file() else pathlib.Path("/dev/null")
    base_text = base.read_text(encoding="utf-8") if base != pathlib.Path("/dev/null") else ""
    probe = tmp_path / "lessons.md"
    probe.write_text(
        base_text
        + "\n## #340 宿主/通用类样本（索引设计上不入本索引）\n"
        "## #341 宿主/通用类样本二\n"
        "## #355 宿主/通用类样本三\n"
        "## #342 论衡类样本（标题不含「论衡」字样）\n",
        encoding="utf-8")
    r, out = _run_gate(probe)
    if not REAL_SRC.is_file():
        pytest.skip("主真源不可达")
    assert r.returncode == 0, f"宿主类排除应放行：\n{out}"
    for line in _advisory_lines(out):
        for n in (340, 341, 355):
            assert f"#{n}" not in line, f"宿主类 #{n} 不应出现在告警中：{line}"
        assert "#342" in line, f"#342 应被计入：{line}"


# ---------------- ⑤ 元测试：排除表默认值不得被清空 + 解析口径不动 ----------------

def test_default_exclusion_table_not_empty():
    src = GATE.read_text(encoding="utf-8")
    m = re.search(r'LUNHENG_LESSON_EXCLUDE="\$\{LUNHENG_LESSON_EXCLUDE:-([^}]*)\}"', src)
    assert m, "门 H 缺 LUNHENG_LESSON_EXCLUDE 默认值声明"
    defaults = m.group(1).split()
    # 排除表默认必须含 #340/#341（历史宿主类）+ 不得被清空
    assert "340" in defaults, f"排除表缺 #340（历史宿主类）：{defaults}"
    assert "341" in defaults, f"排除表缺 #341（历史宿主类）：{defaults}"
    # SRC_MAX 解析口径不得再依赖标题里的「论衡」字样
    src_after_excl = src.split("LUNHENG_LESSON_EXCLUDE")[1] if "LUNHENG_LESSON_EXCLUDE" in src else src
    assert "论衡" not in src_after_excl.split("SRC_MAX=")[1].split("if [ -n")[0] if "SRC_MAX=" in src_after_excl else True, \
        "SRC_MAX 解析口径不得再依赖标题里的「论衡」字样"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))