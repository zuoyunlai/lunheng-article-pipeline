#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_bulk_ratchet.py — 门 Y「必读文件体量软棘轮 + SKILL.md 余量告警」回归门（v2.12.62）

背景（2026-09-19 全面审计 P1-3）：门 V 只锁 SKILL.md 那 ~9.7K 字符 —— 占仓库 1.72M 字符
的 0.57%。仓库里**唯一**有硬棘轮的，恰恰是余量最紧的那一个；三个「每次必读」的大文件
（扩展职责卡 / M-Gate-Algorithm / phase-order.yaml）合计 ~213KB 无任何约束。
审计建议「不要动门 V 的 10000 上限（那是官方约束），而是加第二层棘轮」。

门 Y 语义：**⚠️ 提示级**，不计入 exit code；上限 = 最近一次分层后的实测值，**只许降**。
本文件锁死四件事：
  ① 正向：干净树跑门 → 三条棘轮 pass、无「体量 ... > 上限」告警、余量 pass、RC=0
  ② 红样本：把阈值压到 1（LUNHENG_BULK_RATCHET 覆盖）→ 必出告警，但 **RC 仍为 0**（软门语义）
  ③ 清单完整性：门 Y 清单必须含全部四个「每次必读」文件（v2.13.5 R-21 起含派生索引）
  ④ 缺失文件：清单指向不存在的文件时必须告警（防清单失效后静默通过）
"""
import os
import pathlib
import re
import subprocess



import pytest

# v2.15.9（审计 P2 测试提速）：本文件跑 self-audit-gate.sh（约 9-10s/次）⇒ 标 slow。
#   本地快速回路：pytest -m "not slow"；CI 全量：pytest。
pytestmark = pytest.mark.slow

ROOT = pathlib.Path(__file__).parent.parent
GATE = ROOT / "scripts" / "self-audit-gate.sh"
LESSONS_FIXTURE = ROOT / "tests" / "fixtures" / "lessons-gate.md"

BULK_FILES = (
    "references/agents/00-主控-扩展职责.md",
    "references/_shared/真源/M-Gate-核心.md",
    "references/_shared/真源/phase-order.yaml",
    # v2.13.5（R-21）：派生索引随读法改造成为「每进一个 Phase 前必读」，纳入棘轮
    "references/_shared/真源/phase-order/index.yaml",
)
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _run_gate(extra_env=None):
    # Hermetic by default: gate H's optional external memory source must not
    # make unrelated gate-Y tests depend on the developer workspace state.
    env = os.environ.copy()
    env.setdefault("LESSONS_SRC", str(LESSONS_FIXTURE))
    if extra_env:
        env.update(extra_env)
    r = subprocess.run(["bash", str(GATE)], capture_output=True, text=True,
                       cwd=str(ROOT), env=env)
    return r, ANSI.sub("", r.stdout)


def _y_lines(out):
    return [l for l in out.splitlines() if "门 Y" in l]


def _default_ceils():
    """门内默认阈值表 → {path: ceil}"""
    src = GATE.read_text(encoding="utf-8")
    m = re.search(r'BULK_RATCHET_CEIL_DEFAULT="([^"]+)"', src)
    assert m, "门 Y 缺 BULK_RATCHET_CEIL_DEFAULT 声明"
    out = {}
    for item in m.group(1).split(","):
        path, ceil = item.split("|")
        out[path] = int(ceil)
    return out


def test_gate_y_clean_tree_passes():
    """① 正向：三条棘轮全 pass + 余量 pass + RC=0（干净树不得有告警）"""
    r, out = _run_gate()
    lines = _y_lines(out)
    assert r.returncode == 0, f"干净树门 Y 应为软门且全过，却报红：\n{out}"
    for path in BULK_FILES:
        assert any(f"体量棘轮 {pathlib.Path(path).name}" in l and l.lstrip().startswith("✓")
                   for l in lines), f"门 Y 缺 {path} 的 pass 行：{lines}"
    assert not [l for l in lines if ">" in l and "上限" in l], \
        f"干净树不应有体量回涨告警：{lines}"
    assert any("SKILL.md 字符余量" in l and l.lstrip().startswith("✓") for l in lines), \
        f"余量应达标（若不足请外移内容，而不是压低阈值）：{lines}"


def test_gate_y_overrun_fails_hard():
    """② 红样本：阈值压到 1 ⇒ 逐文件告警**且**门 Y 升为硬门（RC=1）。

    ⚠️ **契约变更（2026-10-08，审计 N-1，主人批准）**：本用例原名 `..._warns_but_does_not_fail`，
    断言「软门不得改 exit code（否则等于第二个硬门）」。门 Y 已由**软门升为硬门** —— 起因是当日实测：
    超限只走 `warn`，既不进 `FAILED[]` 也不影响退出码，gate 连续两次带棘轮违规 `exit 0`，
    「只许降」棘轮形同建议（不会失败的门等于没有门）。
    **未变更的部分**：逐文件告警必须保留（要能定位到**哪个**文件超了），下两行断言原样保留。
    **变更的部分**：收口档位 warn → fail，故 RC 由 0 变 1。
    """
    tiny = ",".join(f"{p}|1" for p in BULK_FILES)
    r, out = _run_gate({"LUNHENG_BULK_RATCHET": tiny})
    lines = _y_lines(out)
    warns = [l for l in lines if l.lstrip().startswith("⚠") and "上限" in l]
    assert len(warns) == len(BULK_FILES), f"回涨未逐文件告警：{lines}"
    assert r.returncode == 1, f"门 Y 已是硬门，超限必须红（否则退回形同建议的软门）：\n{out}"
    assert "FAIL: 1" in out, f"超限须进 FAIL 列表：\n{out}"


def test_gate_y_missing_target_fails_hard():
    """④ 清单指向不存在的文件 ⇒ 必须告警**且**升为硬门（防清单失效后静默通过）。

    ⚠️ 同上契约变更（2026-10-08 审计 N-1）：原断言 `RC=0`（「缺失告警仍属软门语义」），
    现为 `RC=1`。**「必须告警」这一半保留**——清单失效本就不该静默，升为硬门只会让暴露更早。
    """
    r, out = _run_gate({"LUNHENG_BULK_RATCHET": "references/__不存在__.md|1"})
    lines = _y_lines(out)
    assert any("目标文件缺失" in l for l in lines), f"缺失文件未告警：{lines}"
    assert r.returncode == 1, "门 Y 已是硬门，清单指向缺失文件必须红（防清单失效静默通过）"


def test_gate_y_covers_all_mandatory_files():
    """③ 清单完整性：四个「每次必读」文件必须都在（漏一个 = 该文件重新失去约束）"""
    ceils = _default_ceils()
    assert set(ceils) == set(BULK_FILES), f"门 Y 清单与必读大文件集不一致：{set(ceils)}"


def test_gate_y_ceilings_match_actual_sizes():
    """棘轮语义：上限必须 = 当前修订后的实测值（只许降）——写小了会误报，写大了棘轮失效"""
    ceils = _default_ceils()
    for path, ceil in ceils.items():
        actual = (ROOT / path).stat().st_size
        assert actual == ceil, (
            f"{path} 实测 {actual} B ≠ 门 Y 上限 {ceil} B —— "
            f"缩容后请同步下调本表；扩容说明未走分层（审计 P2-6）")
