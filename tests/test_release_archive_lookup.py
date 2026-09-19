#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_release_archive_lookup.py — 补发旧版 Release 必须能读 CHANGELOG 归档（v2.12.62）

背景（本批实测暴露）：changelog 分层（主文件只留最近 5 期，历史迁 CHANGELOG-archive.md）后，
`create-github-release.sh` 的章节提取**只读主文件** —— 于是「补发旧版 Release」**永远失败**：
报「CHANGELOG.md 中无 [vX] 章节」，而章节其实就在归档里。工具被自己的分层规则改坏。

锁死两件事：
  ① 源码不变量：提取段必须同时查 `CHANGELOG.md` 与 `CHANGELOG-archive.md`（防回归）
  ② 功能实证：对**已归档**版本跑 `--dry-run` 必须成功取到正文（tag 不存在则跳过 —— 版本库
     浅克隆场景）
"""
import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "create-github-release.sh"
ARCHIVE = ROOT / "CHANGELOG-archive.md"


def test_extraction_searches_archive():
    """源码不变量：提取段必须同时含主文件与归档两个候选（只查主文件 = 旧缺陷复发）"""
    src = SCRIPT.read_text(encoding="utf-8")
    assert 'root / "CHANGELOG.md", root / "CHANGELOG-archive.md"' in src, \
        "create-github-release.sh 的章节提取未同时查归档 —— 补发旧版 Release 会再次失败"
    assert "CHANGELOG-archive.md 中均无" in src, "缺「两处均无」的报错文案（错误信息须指认两个搜索面）"


def _archived_release_tag():
    """归档里存在、且本地有 tag 的最靠近版本"""
    if not ARCHIVE.is_file():
        return None
    heads = re.findall(r"^## \[(v[0-9.]+)\]", ARCHIVE.read_text(encoding="utf-8"), re.M)
    for tag in heads:
        r = subprocess.run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
                           cwd=str(ROOT), capture_output=True, text=True)
        if r.returncode == 0:
            return tag
    return None


def test_dry_run_works_for_archived_version():
    """功能实证：对已归档版本跑 --dry-run 必须成功（正文取自归档，而非报「无章节」）"""
    tag = _archived_release_tag()
    if tag is None:
        pytest.skip("本地无归档版本的 tag（浅克隆 / 无 tag 环境）")
    r = subprocess.run(["bash", str(SCRIPT), tag, "--dry-run"],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    out = (r.stdout or "") + (r.stderr or "")
    assert r.returncode == 0, f"{tag}（已归档）dry-run 失败：rc={r.returncode}\n{out[-1200:]}"
    assert "中无 [" not in out, f"{tag} 章节未被归档检索命中：\n{out[-800:]}"
    assert "gh release" in out, f"dry-run 未产出将执行的命令：\n{out[-800:]}"
