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

v2.12.62 改判据（审计 P2-7：教训编号「5 处联动副本」必然 off-by-one）：
  原判据「索引声明 #N ≥ 快照 #M」比的是**两处人工维护的数字** —— 实测已出过一次
  off-by-one（v2.12.58：快照 425→426 修正）。现把该类别**从结构上移除**：
  ① 编号只在 `lessons-max.snapshot` 写一次（唯一数值真源，hermetic）；
  ② 索引三处旧副本改为派生指针，门 H **反向校验「索引不得出现硬编码最大编号」**；
  ③ 快照必须可解析（单点真源在位）——否则门 H 失去判据基。
  于是「同批改」从 5 处压到 2 处（快照值 + 排除表），且第 2 处副本由机器拒绝。

官方审计整改（F1/F3，2026-09-13）后的口径（v2.12.62 起在下列基础上收敛）：
  ① 反向差集判据改为 **仓库内快照** `references/_shared/治理/lessons-max.snapshot`（hermetic）——
    不再受仓库外 `memory/lessons.md` 的「已发布的绿可被墙外追加追溯性推翻」影响
  ② 外部真源仅作 **参照告警**（warn），不参与 exit code
  ③ 排除表 `LUNHENG_LESSON_EXCLUDE` 默认 `340 341 355 374 375 376 380 382 383 385 392 393 394 395 396 397 398 402 403 404 405 410 411 412 413 414 380 382 383 385 392 393 394 395 396 397 398 402 403 404 405 410 411 412 413 414`（宿主/工作区/通用类，索引设计上不入本索引）

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
INDEX = ROOT / "references" / "_shared" / "治理" / "教训索引.md"
SNAPSHOT = ROOT / "references" / "_shared" / "治理" / "lessons-max.snapshot"

HOME = pathlib.Path.home()
# Hermetic 默认：测试不能依赖开发者 workspace 的外部 memory/lessons.md。
# 需要验证外部真源告警时，显式传入 LESSONS_SRC；默认夹具覆盖仓库快照的 115-437 编号。
FIXTURE_SRC = pathlib.Path(__file__).parent / "fixtures" / "lessons-gate.md"
REAL_SRC = pathlib.Path(os.environ.get("LESSONS_SRC", FIXTURE_SRC))

REVERSE_DIFF_MARKS = (              # 门 H 反向判据的全部行（pass + fail）
    "快照单一真源可解析",            # 判据① pass
    "教训快照不可解析",              # 判据① fail
    "教训索引无硬编码最大编号",      # 判据② pass
    "又出现硬编码最大编号",          # 判据② fail
)
ADVISORY = "门 H: 外部真源"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _idx_hardcoded_count():
    """索引内**硬编码最大编号**的处数（v2.12.62 起必须为 0）"""
    return len(re.findall(r"最大编号 \*\*#\d+\*\*", INDEX.read_text(encoding="utf-8")))


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
    return [l for l in out.splitlines() if any(m in l for m in REVERSE_DIFF_MARKS)]


def _advisory_lines(out):
    return [l for l in out.splitlines() if ADVISORY in l]


def _src_numbers(text):
    return [int(n) for n in re.findall(r"^#{2,4} (?:教训 )?#(\d+)", text, re.M)]


requires_real_src = pytest.mark.skipif(
    not REAL_SRC.is_file(), reason=f"主真源不可达：{REAL_SRC}（门 H 为软门，跳过）")


# ---------------- ①ᐟ 红样本（v2.12.62 两条）：判据失效必须红 -------------

def test_hardcoded_index_number_must_fail(tmp_path):
    """红样本①：索引里塞回硬编码最大编号 ⇒ 门 H 必须红并点名。

    这是本版的核心防御——「压到 2 处」不是删副本了事，而是**机器拒绝第 2 处副本**。
    """
    probe = tmp_path / "index.md"
    probe.write_text(INDEX.read_text(encoding="utf-8")
                     + "\n> 当前最大编号 **#999**（回归样本）\n", encoding="utf-8")
    r, out = _run_gate(REAL_SRC, {"LUNHENG_LESSON_INDEX": str(probe)})
    assert r.returncode != 0, f"索引硬编码编号却放行（判据②退化为永真）：\n{out}"
    lines = _reverse_diff_lines(out)
    assert any(l.lstrip().startswith("✗") and "硬编码最大编号" in l for l in lines), \
        f"硬编码编号未报红：{lines}"


def test_missing_snapshot_must_fail(tmp_path):
    """红样本②：快照不可解析 ⇒ 门 H 必须红（唯一数值真源缺失 = 判据基缺失）。"""
    gone = tmp_path / "snapshot-empty"
    gone.write_text("（无数字头）\n", encoding="utf-8")
    r, out = _run_gate(REAL_SRC, {"LESSONS_SNAPSHOT": str(gone)})
    assert r.returncode != 0, f"快照不可解析却放行（判据①退化为永真）：\n{out}"
    lines = _reverse_diff_lines(out)
    assert any(l.lstrip().startswith("✗") and "快照不可解析" in l for l in lines), \
        f"快照缺失未报红：{lines}"


# ---------------- ① 正向：真源超过快照且不在排除表 → 参照告警但不 fail ----------------

@requires_real_src
def test_snapshot_advisory_when_source_exceeds_snapshot(tmp_path):
    """新口径：真源新增一个**未列入排除表**的编号 → 快照告警，但门仍 pass（hermetic 判据）"""
    snap = _snap_max()
    assert snap is not None, "快照文件缺失"
    # 选未列入排除表（340/341/355/374/375/376）的编号
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
def test_no_false_positive_on_clean_tree(tmp_path):
    """干净树：单点真源在位 + 索引无副本 ⇒ 两条判据都必须 pass，且编号一致。"""
    snap = _snap_max()
    assert snap is not None, "快照文件缺失"
    assert _idx_hardcoded_count() == 0, \
        f"索引仍有 {_idx_hardcoded_count()} 处硬编码最大编号（v2.12.62 起应为 0）"
    r, out = _run_gate(REAL_SRC)
    assert r.returncode == 0, f"干净树却报红：\n{out}"
    assert "FAIL: 0" in out, f"存在误报门：\n{out}"
    lines = _reverse_diff_lines(out)
    assert any("快照单一真源可解析" in l and f"#{snap}" in l for l in lines), \
        f"判据①未 pass 或未点名快照值：{lines}"
    assert any("无硬编码最大编号" in l for l in lines), f"判据②未 pass：{lines}"


# ---------------- ③ 负向：排除表覆盖真源 → 不得误报（合法领先） ----------------

@requires_real_src
def test_no_false_positive_when_exclude_table_leads_source(tmp_path):
    """合法领先样本：把所有真源编号列入排除表 → SRC_MAX=0 ≤ 快照，判据必放行。"""
    nums = sorted(set(_src_numbers(REAL_SRC.read_text(encoding="utf-8"))))
    exclude = " ".join(str(n) for n in nums) or "0"
    r, out = _run_gate(REAL_SRC, {"LUNHENG_LESSON_EXCLUDE": exclude})
    assert r.returncode == 0, f"排除表合法领先却报红：\n{out}"
    lines = _reverse_diff_lines(out)
    assert all(l.lstrip().startswith("✓") for l in lines), \
        f"合法领先被判为红：{lines}"
    assert any("快照单一真源可解析" in l for l in lines), f"判据①缺失：{lines}"


# ---------------- ④ 排除表：宿主/通用类编号不计入最大告警编号 ----------------

@requires_real_src
def test_host_class_numbers_excluded_from_advisory(tmp_path):
    """#340/#341/#355/#374/#375/#376 宿主/工作区类不计入 SRC_MAX，告警行不出现这些编号。

    2026-09-14 去环境耦合修订：旧实现「主真源全文 + 合成条目」却断言告警行点名 #342 ——
    但告警行**只点 SRC_MAX（最大非排除编号）**，主真源持续增长（实测已到 #365）后该断言
    必然为红，属环境漂移型假红。
    现改为：仍以主真源为基（仓库引用的编号必须都有定义，否则会触发门 H 的另一条检查
    「教训编号引用在主真源缺定义」），但用排除表把 **> 342 的全部编号**排除，使 SRC_MAX
    恒为 #342；快照显式压低到 300，令参照告警必响且**只能**点 #342。
    断言意图（宿主类不进 SRC_MAX）原样保留，判据不再依赖真源当前最大编号。
    """
    base_text = REAL_SRC.read_text(encoding="utf-8")
    probe = tmp_path / "lessons.md"
    probe.write_text(
        base_text
        + "\n## #340 宿主/通用类样本（索引设计上不入本索引）\n"
        "## #341 宿主/通用类样本二\n"
        "## #355 宿主/通用类样本三\n"
        "## #374 工作区审计类样本四\n"
        "## #375 工作区审计类样本五\n"
        "## #376 工作区审计类样本六\n"
        "## #342 论衡类样本（标题不含「论衡」字样）\n",
        encoding="utf-8")
    high = sorted({n for n in _src_numbers(base_text) if n > 342})
    exclude = " ".join(["340", "341", "355", "374", "375", "376"] + [str(n) for n in high])
    low_snap = tmp_path / "snapshot-low"
    low_snap.write_text("300\n", encoding="utf-8")
    r, out = _run_gate(probe, {"LUNHENG_LESSON_EXCLUDE": exclude,
                               "LESSONS_SNAPSHOT": str(low_snap)})
    assert r.returncode == 0, f"宿主类排除应放行：\n{out}"
    advisories = _advisory_lines(out)
    assert advisories, f"SRC_MAX 342 > 快照 300，应产生参照告警：\n{out}"
    for line in advisories:
        for n in (340, 341, 355, 374, 375, 376):
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
    for n in ("355", "374", "375", "376"):
        assert n in defaults, f"排除表缺 #{n}（宿主/工作区类）：{defaults}"
    # SRC_MAX 解析口径不得再依赖标题里的「论衡」字样
    src_after_excl = src.split("LUNHENG_LESSON_EXCLUDE")[1] if "LUNHENG_LESSON_EXCLUDE" in src else src
    assert "论衡" not in src_after_excl.split("SRC_MAX=")[1].split("if [ -n")[0] if "SRC_MAX=" in src_after_excl else True, \
        "SRC_MAX 解析口径不得再依赖标题里的「论衡」字样"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))