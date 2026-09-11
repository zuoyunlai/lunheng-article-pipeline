#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_create_release_e2e.py — 端到端正向回归：tag → create-github-release.sh → 退出 0（教训 #334）

背景（教训 #334，2026-09-11 实测自锁）：
  `scripts/create-github-release.sh` 第 2 步硬性要求本地已有 tag（先 tag、后建 Release），
  第 6.5 步又无条件调用 `release-preflight.sh`；而闸的 ② 把「本地/远端已有该 tag」判为
  **编号占用 → exit 11**。两者语义矛盾 → **正常发版路径必然被自己的闸拦死**，只剩
  `--skip-preflight` 能走通（而该开关文档写着「不得作为常规发版路径」）。
  实测：打完 tag 再跑写路径 → `❌ 目标编号已被占用` → `EXIT=11`，Release 未创建。

  既有 `test_release_preflight.py` 全是闸的**孤立单测**（fake sessions / fake ls-remote），
  没有一条覆盖「真实发版链路能否走通」——**门自身全绿 ≠ 链路可达**。本文件补的就是
  「应当放行」的正向样本：临时仓库里真打 tag → 调 create-github-release.sh（fake gh）→ 断言退出 0。

零网络、零真实 gh：
  - `gh` 用 PATH 前置的桩脚本（记录调用 + 固定回答）；origin 用 github 形态 URL 仅供
    `git remote get-url` 解析 slug，真实网络传输被 `GIT_ALLOW_PROTOCOL=file` 挡下（快速失败）。
  - 前置闸的在飞链 / 远端 tag 用 `LUNHENG_PREFLIGHT_SESSIONS_CMD` / `..._REMOTE_CMD` 注入快照。

断言：
  - 打 tag 后走写路径 ⇒ 退出 0，且闸的 ② 走放松口径（打印 `--allow-existing-tag` 提示）
  - 同一仓库直接跑**严格口径**的闸 ⇒ 仍退出 11（证明「链路通」不是靠闸失效）
  - 不打 tag ⇒ 退出 2（第 2 步的「tag 必须先存在」铁律未被放松）
  - 有同项目在飞链 ⇒ 退出 10（写路径仍被闸守住，退出码透传）
"""
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
VERSION = "2.12.22"
TAG = f"v{VERSION}"
GH_STUB = "gh"

RC_INFLIGHT, RC_TAG_TAKEN, RC_USAGE = 10, 11, 2


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )


@pytest.fixture
def e2e(tmp_path):
    """临时仓库：SKILL.md + CHANGELOG 章节 + 三个真脚本 + fake gh + 空在飞链快照。"""
    root = (tmp_path / "repo").resolve()
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for name in ("release-preflight.sh", "create-github-release.sh", "changelog-check.py"):
        shutil.copy(REPO / "scripts" / name, scripts / name)

    (root / "SKILL.md").write_text(
        f"---\nname: lunheng-article-pipeline\nversion: {VERSION}\n---\n\n# 端到端样本\n",
        encoding="utf-8",
    )
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n---\n\n"
        f"## [{TAG}] — 2026-09-11\n\n"
        "> 端到端回归样本：验证「先 tag、后补发 Release」的正路径不再被前置闸自锁。\n\n"
        "### 修复\n\n- 发版前置闸 ② 口径细化为「编号是否被本链之外的人占用」。\n\n---\n",
        encoding="utf-8",
    )

    subprocess.run(["git", "init", "-q", "-b", "master", str(root)], check=True)
    _git(root, "config", "user.email", "e2e@example.com")
    _git(root, "config", "user.name", "e2e-test")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", f"release: {TAG} — 端到端回归样本")
    # origin 只为 slug 解析（changelog-check.py --online 读它），传输被 GIT_ALLOW_PROTOCOL 挡下
    _git(root, "remote", "add", "origin",
         "https://github.com/zuoyunlai/lunheng-article-pipeline.git")
    head = _git(root, "rev-parse", "HEAD").stdout.strip()

    bindir = (tmp_path / "bin").resolve()
    bindir.mkdir()
    log = (tmp_path / "gh.log").resolve()
    stub = bindir / GH_STUB
    stub.write_text(
        "#!/usr/bin/env bash\n"
        "# fake gh：记录调用；release view 未建前报「不存在」；api 回带 tag 的 Release 列表\n"
        'printf \'%s\\n\' "$*" >> "$FAKE_GH_LOG"\n'
        'case "${1:-}" in\n'
        '  api) printf \'[{"tag_name":"%s","name":"论衡 %s","published_at":"2026-09-11T00:00:00Z","body":"样本"}]\''
        ' "$FAKE_GH_TAG" "$FAKE_GH_TAG" ; exit 0 ;;\n'
        '  release) case "${2:-}" in\n'
        '             view) [ -f "$FAKE_GH_RELEASES" ] && exit 0 || exit 1 ;;\n'
        '             create) printf \'created: %s\\n\' "$*" > "$FAKE_GH_RELEASES" ;;\n'
        '             edit) [ -f "$FAKE_GH_RELEASES" ] || printf \'edited: %s\\n\' "$*" > "$FAKE_GH_RELEASES" ;;\n'
        '           esac ;;\n'
        "  *) exit 0 ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # 前置闸：在飞链空快照 + 远端 tag 快照（annotated tag 的 tag 对象 + ^{} 解引用提交）
    sessions = (tmp_path / "sessions.json").resolve()
    sessions.write_text(json.dumps({"sessions": []}), encoding="utf-8")
    tag_obj = head
    remote = (tmp_path / "ls-remote.txt").resolve()
    remote.write_text(
        f"{'a' * 40}\trefs/heads/master\n{tag_obj}\trefs/tags/{TAG}\n{head}\trefs/tags/{TAG}^{{}}\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"
    env["GIT_ALLOW_PROTOCOL"] = "file"          # https 传输立即失败（离线、确定性）
    env["LUNHENG_PREFLIGHT_SESSIONS_CMD"] = f"cat {sessions}"
    env["LUNHENG_PREFLIGHT_REMOTE_CMD"] = f"cat {remote}"
    env["FAKE_GH_LOG"] = str(log)
    env["FAKE_GH_RELEASES"] = str(tmp_path / "gh-releases.log")
    env["FAKE_GH_TAG"] = TAG

    return {
        "root": root, "env": env, "log": log,
        "sessions": sessions, "remote": remote, "head": head,
    }


def _run(e2e, *args):
    return subprocess.run(
        ["bash", str(e2e["root"] / "scripts" / "create-github-release.sh"), *args],
        capture_output=True, text=True, cwd=str(e2e["root"]), env=e2e["env"],
    )


def _run_gate(e2e, *args):
    return subprocess.run(
        ["bash", str(e2e["root"] / "scripts" / "release-preflight.sh"), *args],
        capture_output=True, text=True, cwd=str(e2e["root"]), env=e2e["env"],
    )


# ---------------------------------------------------------------------------
# 正向：正常发版路径必须走得通（教训 #334 的核心断言）
# ---------------------------------------------------------------------------
def test_tag_then_create_release_exits_zero(e2e):
    """先打 tag、后补发 Release 的正路径 ⇒ 退出 0，Release 真创建（fake gh 记录到 create）。"""
    _git(e2e["root"], "tag", "-a", TAG, "-m", f"release: {TAG} — 端到端回归样本")
    r = _run(e2e, TAG)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"✅ Release {TAG} 已创建" in r.stdout
    # 闸确实跑了，且以放松口径（教训 #334）判 ②
    assert "--allow-existing-tag" in r.stdout
    assert "本链之外" in r.stdout
    # fake gh 真的收到了 create（不是靠 --skip-preflight 绕过去）
    gh_log = e2e["log"].read_text(encoding="utf-8")
    assert "release create" in gh_log
    assert "release edit" not in gh_log
    assert "--skip-preflight" not in r.stdout


def test_same_repo_strict_gate_still_blocks(e2e):
    """同一仓库：直接跑严格口径的闸仍退出 11 —— 说明链路通是修法生效，不是闸被架空。"""
    _git(e2e["root"], "tag", TAG)
    strict = _run_gate(e2e, TAG)
    assert strict.returncode == RC_TAG_TAKEN, strict.stdout + strict.stderr
    assert "目标编号已被占用" in strict.stdout
    relaxed = _run_gate(e2e, "--allow-existing-tag", TAG)
    assert relaxed.returncode == 0, relaxed.stdout + relaxed.stderr


# ---------------------------------------------------------------------------
# 反向：铁律与守卫仍在（别把「应当拒绝」的路径一起放松掉）
# ---------------------------------------------------------------------------
def test_without_tag_still_refuses(e2e):
    """不打 tag ⇒ 第 2 步照旧拒绝（退出 2），提示先打 tag。"""
    r = _run(e2e, TAG)
    assert r.returncode == RC_USAGE, r.stdout + r.stderr
    assert f"本地无 tag {TAG}" in r.stderr
    assert "先打 tag 再建 Release" in r.stderr


def test_inflight_chain_still_blocks_write_path(e2e):
    """同项目有在飞链 ⇒ 写路径退出 10（透传闸的退出码），Release 未创建。"""
    _git(e2e["root"], "tag", TAG)
    e2e["sessions"].write_text(
        json.dumps({"sessions": [{
            "key": "agent:main:dashboard:inflight",
            "status": "running",
            "label": "并发修订链",
            "spawnedCwd": str(e2e["root"]),
            "ageMs": 60000,
        }]}),
        encoding="utf-8",
    )
    r = _run(e2e, TAG)
    assert r.returncode == RC_INFLIGHT, r.stdout + r.stderr
    assert "前置闸未通过" in r.stderr
    assert not e2e["log"].exists() or "release create" not in e2e["log"].read_text(encoding="utf-8")


def test_dirty_workspace_still_blocks_write_path(e2e):
    """工作区不净 ⇒ 写路径退出 12，Release 未创建。"""
    _git(e2e["root"], "tag", TAG)
    with (e2e["root"] / "CHANGELOG.md").open("a", encoding="utf-8") as fh:
        fh.write("\n改了没提交\n")          # 只动工作区（章节仍在，过不了的是第 3 查）
    r = _run(e2e, TAG)
    assert r.returncode == 12, r.stdout + r.stderr
    assert "工作区不净" in r.stdout


def test_dry_run_skips_gate_and_writes_nothing(e2e):
    """--dry-run 是只读路径：不进闸（无需 tag 之外的任何准备），且不调用 gh。"""
    _git(e2e["root"], "tag", TAG)
    r = _run(e2e, TAG, "--dry-run")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "dry-run 完成（零远端写入）" in r.stdout
    assert not e2e["log"].exists()
