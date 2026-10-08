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
        f"请把最旧若干章下沉到冷归档 references/_shared/治理/changelog-cold-v2.0-v2.12.md，"
        f"而非放宽本值（v2.16.1 修：原指引指向 docs/history/，该路径被 .gitignore 排除）"
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
    # v2.16.1：文案由「归档已接近无界」细化为「温层已接近无界」——温层/冷层从此各有独立棘轮，
    # 必须能区分是哪一层撞顶（软门语义不变：仍只 warn，退出码仍 0）。
    assert "温层已接近无界" in out, f"超限未告警（温层）：\n{out[-800:]}"
    assert r.returncode == 0, f"归档告警属软门，不得改退出码：{r.returncode}\n{out[-400:]}"



# ===== v2.16.1：温层排水机制回归门（审计 §九 结构性冲突修复）=====
# 修复前：温层 ceiling 归零时，告警指引让人「冷归档到 docs/history/」，而 docs/ 被 .gitignore
#        第 4 行排除 ⇒ 照做章节从版本控制消失；且「下沉会让 tag 失去章节」是误判
#        （changelog_files() 本就含冷层）。以下四条把修复锁住，防回潮。

COLD = ROOT / "references" / "_shared" / "治理" / "changelog-cold-v2.0-v2.12.md"


def test_drain_target_is_cold_layer_not_gitignored_docs():
    """① 冷层在版本控制内，且不属 .gitignore 排除路径（v2.16.1 修复的核心）。"""
    assert COLD.is_file(), f"冷归档文件缺失：{COLD}"
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(COLD.relative_to(ROOT))],
                             cwd=str(ROOT), capture_output=True, text=True)
    assert tracked.returncode == 0, f"冷归档未被 git 跟踪：{tracked.stderr.strip()}"
    ignored = subprocess.run(["git", "check-ignore", "-q", "docs/history/x.md"],
                             cwd=str(ROOT), capture_output=True, text=True)
    assert ignored.returncode == 0, (
        "前提失效：docs/ 已不再被 .gitignore 排除 —— 若确已排除，则更**不得**把它当排水目标")


def test_cold_layer_is_read_by_checker():
    """② 冷层必须参与「每个版本 tag 都有章节」的校验集合 —— 否则下沉会让 tag 失去章节。"""
    mod = _load_module()
    files = {p.name for p in mod.changelog_files()}
    assert COLD.name in files, f"changelog_files() 未含冷层：{files}（下沉会致 tag 失去章节）"
    assert ARCHIVE.name in files and "CHANGELOG.md" in files, f"校验文件集异常：{files}"


def test_cold_layer_has_its_own_ratchet():
    """③ 冷层亦有棘轮（否则「温层排水」只是把无界问题平移到冷层）。"""
    mod = _load_module()
    assert hasattr(mod, "CHANGELOG_COLD_CEIL"), "changelog-check 缺 CHANGELOG_COLD_CEIL 声明"
    assert isinstance(mod.CHANGELOG_COLD_CEIL, int) and mod.CHANGELOG_COLD_CEIL > 0
    actual = COLD.stat().st_size
    assert actual == mod.CHANGELOG_COLD_CEIL, (
        f"冷层实测 {actual} B != 上限 {mod.CHANGELOG_COLD_CEIL} B —— 请同步实测（棘轮只许降）")


def test_warm_overrun_guidance_points_at_cold_not_docs():
    """④ 温层超限告警文案必须指向冷层，且不得再出现被忽略的 docs/ 排水指引。"""
    src = CHECK.read_text(encoding="utf-8")
    assert "温层已接近无界" in src, "未找到温层超限告警文案"
    # 排水指引必须点名冷层（可执行的、已被校验读取的出口）
    assert f"下沉到冷归档 {{CHANGELOG_COLD.name}}" in src, \
        "温层超限告警未指向冷层文件（排水出口缺失 = 撞顶时无人知道往哪挪）"
    # 旧的错误指引（会让章节从版本控制消失）必须已从**生效代码**中消失。
    # ⚠️ 只扫代码行、不扫注释：修复说明的注释里会**刻意引用**旧指引原文（「下方告警一直让人
    # 「冷归档到 docs/history/」」），全文扫描会自证失败（2026-10-08 首跑即踩）。
    _code = "\n".join(ln for ln in src.splitlines() if not ln.lstrip().startswith("#"))
    assert "冷归档到 docs/history/" not in _code, \
        "超限告警仍指示「冷归档到 docs/history/」——该路径被 .gitignore 排除，照做会丢章节"
