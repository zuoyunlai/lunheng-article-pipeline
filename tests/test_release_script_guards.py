#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_release_script_guards.py — 发布链护栏测试（v2.12.30 新增）

背景（2026-09-12 第三方全量审计，第二批 P1）：
  - P1-4：build-clawhub-release.sh / publish-clawhub.sh 的 VERSION 直接进
          `$OUT_ROOT/$VERSION` 并紧接 `rm -rf` —— 参数即删除目标（目录逃逸）。
          对照：release-preflight.sh / create-github-release.sh 早已有 tag 格式校验。
  - P1-3：build 脚本的「未跟踪文件」反向断言在非 git 环境**静默跳过** = 放弃唯一
          能发现「未跟踪残留入包」的机械门（教训 #333）。
  - P1-2：cleanup-skill-store.sh 无条件 `git reflog expire --expire=now --all` +
          `git gc --prune=now`（不可逆），与脚本头部「所有删前先备份」承诺矛盾。
"""
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).parent.parent
BUILD = ROOT / "scripts" / "build-clawhub-release.sh"
PUBLISH = ROOT / "scripts" / "publish-clawhub.sh"
CLEANUP = ROOT / "scripts" / "cleanup-skill-store.sh"


def _run(script, *args):
    return subprocess.run(["bash", str(script), *args],
                          capture_output=True, text=True, cwd=str(ROOT))


# ---------------- P1-4：版本参数校验（参数即 rm -rf 目标）----------------

def test_build_rejects_path_traversal_version():
    r = _run(BUILD, "../../PWNED")
    assert r.returncode == 2, f"应拒绝路径穿越版本号，实际 rc={r.returncode}"
    assert "版本号" in (r.stderr + r.stdout)
    # 反向断言：不得创建任何越界目录
    assert not (ROOT.parent.parent / "PWNED").exists()
    assert not (ROOT / "outputs" / "PWNED").exists()


def test_build_rejects_non_semver_version():
    # 注：空串是**文档化回退**（读 SKILL.md frontmatter），非非法输入，故不在此列；
    #    空白串用于覆盖「非空但格式非法」的同类场景。
    for bad in ("abc", "1.2", "1.2.3.4", " ", "v1.2.3", "1.2.3/../../x"):
        r = _run(BUILD, bad)
        assert r.returncode == 2, f"'{bad}' 应被拒绝，实际 rc={r.returncode}"


def test_build_has_path_containment_guard():
    """正则之外的二层防线：解析后绝对路径必须落在输出根之内"""
    src = BUILD.read_text(encoding="utf-8")
    assert "输出目录逃逸出输出根" in src
    assert "OUT_ROOT_ABS" in src and "OUT_DIR_ABS" in src
    # 容器检查必须出现在 rm -rf 之前
    assert src.index("输出目录逃逸出输出根") < src.index('rm -rf "$OUT_DIR"')


def test_publish_validates_version_before_use():
    src = PUBLISH.read_text(encoding="utf-8")
    assert "版本号格式非法" in src, "publish-clawhub.sh 也必须校验 VERSION"
    # 校验必须在使用该值（cd 到输出目录 / 调 build）之前
    assert src.index("版本号格式非法") < src.index('cd "$OUT_ROOT/$VERSION"')


# ---------------- P1-3：非 git 环境不得静默跳过 ----------------

def test_build_fails_closed_without_git():
    src = BUILD.read_text(encoding="utf-8")
    assert "LUNHENG_ALLOW_NO_GIT" in src, "必须提供显式豁免开关"
    assert "该检查是发现「未跟踪残留入包」的唯一机械门，不允许静默跳过" in src
    # 原实现是「if git ... then <整段> fi」（无 else）→ 非 git 静默通过；现在必须有 else 分支终止
    assert re.search(r'if ! git -C "\$SKILL_ROOT" rev-parse', src), \
        "应以否定形式显式处理「非 git」分支"


def test_build_nongit_guard_is_functional(tmp_path):
    """功能验证：在无 .git 的副本上构建必须失败（而非静默产出包）"""
    import shutil
    dst = tmp_path / "copy"
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "outputs", "__pycache__"))
    r = subprocess.run(["bash", str(dst / "scripts" / "build-clawhub-release.sh"), "9.9.9"],
                       capture_output=True, text=True, cwd=str(dst))
    assert r.returncode != 0
    assert "非 git 环境" in (r.stderr + r.stdout)
    # 豁免开关存在时可继续（此处只验证开关被识别，不跑完整构建）
    src = (dst / "scripts" / "build-clawhub-release.sh").read_text(encoding="utf-8")
    assert "LUNHENG_ALLOW_NO_GIT=1 显式豁免" in src


# ---------------- P1-2：cleanup 脚本不可逆操作改 opt-in ----------------

def test_cleanup_rejects_bad_keep():
    r = _run(CLEANUP, "--keep=abc")
    assert r.returncode == 2
    assert "--keep 必须为正整数" in (r.stderr + r.stdout)


def test_cleanup_rejects_purge_with_no_backup():
    """既不备份、又要销毁历史 = 放弃全部退路 → 拒绝"""
    r = _run(CLEANUP, "--purge-git-history", "--no-backup")
    assert r.returncode == 2
    assert "互斥" in (r.stderr + r.stdout)


def test_cleanup_default_does_not_purge_git_history():
    src = CLEANUP.read_text(encoding="utf-8")
    purge_at = src.index('if [ "$PURGE_GIT_HISTORY" != "true" ]; then')
    reflog_at = src.rindex("git reflog expire")  # 头部注释也含该字样，取实际命令那次
    assert purge_at < reflog_at, "reflog expire 必须落在 PURGE 分支内"
    # 且必须先打 bundle 备份、再销毁历史
    assert src.index("git bundle verify") < reflog_at
    assert "默认口径：不动可恢复历史" in src


def test_cleanup_bundle_backup_precedes_destruction():
    src = CLEANUP.read_text(encoding="utf-8")
    assert "git bundle create" in src
    assert src.index("git bundle create") < src.rindex("git reflog expire")
    assert "拒绝继续销毁历史" in src
