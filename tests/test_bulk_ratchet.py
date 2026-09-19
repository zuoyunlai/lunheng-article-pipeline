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
  ③ 清单完整性：门 Y 清单必须含全部三个「每次必读」大文件
  ④ 缺失文件：清单指向不存在的文件时必须告警（防清单失效后静默通过）
"""
import os
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).parent.parent
GATE = ROOT / "scripts" / "self-audit-gate.sh"

BULK_FILES = (
    "references/agents/00-主控-扩展职责.md",
    "references/_shared/M-Gate-Algorithm.md",
    "references/_shared/phase-order.yaml",
)
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _run_gate(extra_env=None):
    env = os.environ.copy()
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


def test_gate_y_overrun_warns_but_does_not_fail():
    """② 红样本：阈值压到 1 ⇒ 必告警，但软门语义要求 RC 仍为 0（不许变成第二个硬门）"""
    tiny = ",".join(f"{p}|1" for p in BULK_FILES)
    r, out = _run_gate({"LUNHENG_BULK_RATCHET": tiny})
    lines = _y_lines(out)
    warns = [l for l in lines if l.lstrip().startswith("⚠") and "上限" in l]
    assert len(warns) == len(BULK_FILES), f"回涨未逐文件告警：{lines}"
    assert r.returncode == 0, f"软门不得改 exit code（否则等于第二个硬门）：\n{out}"
    assert "FAIL: 0" in out, f"软门不得进 FAIL 列表：\n{out}"


def test_gate_y_missing_target_warns():
    """④ 清单指向不存在的文件 ⇒ 必须告警（防清单失效后静默通过）"""
    r, out = _run_gate({"LUNHENG_BULK_RATCHET": "references/__不存在__.md|1"})
    lines = _y_lines(out)
    assert any("目标文件缺失" in l for l in lines), f"缺失文件未告警：{lines}"
    assert r.returncode == 0, "缺失告警仍属软门语义"


def test_gate_y_covers_all_mandatory_files():
    """③ 清单完整性：三个「每次必读」大文件必须都在（漏一个 = 该文件重新失去约束）"""
    ceils = _default_ceils()
    assert set(ceils) == set(BULK_FILES), f"门 Y 清单与必读大文件集不一致：{set(ceils)}"


def test_gate_y_ceilings_match_actual_sizes():
    """棘轮语义：上限必须 = 最近一次分层后的实测值（只许降）——写小了会误报，写大了棘轮失效"""
    ceils = _default_ceils()
    for path, ceil in ceils.items():
        actual = (ROOT / path).stat().st_size
        assert actual == ceil, (
            f"{path} 实测 {actual} B ≠ 门 Y 上限 {ceil} B —— "
            f"缩容后请同步下调本表；扩容说明未走分层（审计 P2-6）")
