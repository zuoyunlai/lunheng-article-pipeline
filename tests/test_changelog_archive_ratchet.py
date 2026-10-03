#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_changelog_archive_ratchet.py — 归档体量棘轮回归门（v2.15.9，审计 P2 仓库瘦身）

背景（2026-10-03 全量审计「仓库瘦身」项，实测修正）：
  审计原文预设「memory/ + reports/ 混入技能仓库、CHANGELOG-archive 拖累体积」三项。
  实测结果：
    · memory/ / reports/ 已被 .gitignore 排除（不进 git、不进净化包）⇒ 该两项**不成立**；
    · CHANGELOG-archive.md 502KB / 382 章是**全仓最大被跟踪文件**，且主文件有 5 期门
      而归档**无任何上限** ⇒ 「轮转」长期看只是把体积从主文件挪到归档，仍无界。

本文件锁死修复后的机制：
  ① 常量在位：CHANGELOG_ARCHIVE_CEIL 声明存在且为正整数；
  ② 实测对齐：上限 == 当前归档实测体量（棘轮语义：写大了失效、写小了误报）；
  ③ 超限告警：把上限压低到 1 ⇒ 必须输出「归档已接近无界」告警（软门，不阻断校验）；
  ④ 软门语义：超限时 changelog-check 退出码仍为 0（不把告警升级成硬失败）。
"""
import importlib.util
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent.parent
CHECK = ROOT / "scripts" / "changelog-check.py"
ARCHIVE = ROOT / "CHANGELOG-archive.md"


def _load_module():
    spec = importlib.util.spec_from_file_location("clcheck", CHECK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ceiling_constant_declared():
    """① 常量在位且为正整数（防机制被静默移除）。"""
    mod = _load_module()
    assert hasattr(mod, "CHANGELOG_ARCHIVE_CEIL"), "changelog-check 缺 CHANGELOG_ARCHIVE_CEIL 声明"
    assert isinstance(mod.CHANGELOG_ARCHIVE_CEIL, int) and mod.CHANGELOG_ARCHIVE_CEIL > 0


def test_ceiling_matches_actual_size():
    """② 棘轮语义：上限 == 当前实测体量（缩容后须同步下调；扩容须走冷归档）。"""
    mod = _load_module()
    assert ARCHIVE.is_file(), f"归档文件缺失：{ARCHIVE}"
    actual = ARCHIVE.stat().st_size
    assert actual <= mod.CHANGELOG_ARCHIVE_CEIL, (
        f"归档实测 {actual} B > 上限 {mod.CHANGELOG_ARCHIVE_CEIL} B —— "
        f"请把最旧若干章冷归档到 docs/history/，而非放宽本值"
    )
    assert actual == mod.CHANGELOG_ARCHIVE_CEIL, (
        f"归档实测 {actual} B != 上限 {mod.CHANGELOG_ARCHIVE_CEIL} B —— "
        f"缩容后请同步下调上限（棘轮只许降）"
    )


def test_overrun_warns_but_does_not_fail(tmp_path):
    """③④ 超限 ⇒ 告警输出，但退出码仍 0（软门语义）。

    注：探针必须放在 scripts/ 下 —— changelog-check.py 用 __file__ 的 parent.parent
    解析 SKILL_ROOT，放 tmp 会让它找不到 SKILL.md/CHANGELOG（首版即踩此坑）。
    """
    probe = ROOT / "scripts" / "_probe_cc_ratchet.py"
    src = CHECK.read_text(encoding="utf-8")
    probe.write_text(re.sub(r"CHANGELOG_ARCHIVE_CEIL = \d+", "CHANGELOG_ARCHIVE_CEIL = 1", src),
                     encoding="utf-8")
    try:
        r = subprocess.run([sys.executable, str(probe), "--check"],
                           capture_output=True, text=True, cwd=str(ROOT))
    finally:
        probe.unlink(missing_ok=True)
    out = r.stdout + r.stderr
    assert "归档已接近无界" in out, f"超限未告警：\n{out[-800:]}"
    assert r.returncode == 0, f"归档告警属软门，不得改退出码：{r.returncode}\n{out[-400:]}"

