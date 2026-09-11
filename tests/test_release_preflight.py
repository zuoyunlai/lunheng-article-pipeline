#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_release_preflight.py — 发版前置闸离线回归测试（v2.12.21，教训 #332）

背景（教训 #332，2026-09-11 实测错乱）：
  多条会话链并行修订同一仓库时，发版动作（升版号 / tag / push / GitHub Release /
  净化包）被当成「本链的下一步」，没检查全局状态 → 版本谱系被劈成两半
  （远端 master=v2.12.18 / 本地 HEAD=v2.12.20，中间两版无 tag）。
  `scripts/release-preflight.sh` 是事后加上的「两查一停」拒绝器。

本测试**零网络、零 gh**：远端由 `--remote-file` 注入（= fake ls-remote），
在飞链由 `--sessions-file` 注入（= fake 在飞链清单），每个用例都在 `tmp_path`
里新建一个独立假仓库（真 git，只含 SKILL.md + 本闸脚本）。

核心断言（对应交付要求）：
  - 全干净 ⇒ 通过（rc=0，且打印「远端 master / 本地 HEAD / tag 区间 / 在飞链」四行现状）
  - 有在飞链 ⇒ 拒绝（rc≠0，打印清单 + 如何等）
  - 编号被占（本地 or 远端）⇒ 拒绝（rc≠0，要求换号）
  - 工作区不净 ⇒ 拒绝（rc≠0）
  - 闸「失败关闭」：在飞链清单拿不到 / 解析不了 ⇒ 拒绝，绝不静默放行
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "release-preflight.sh"

VERSION = "2.12.21"
TAG = f"v{VERSION}"

RC_PASS, RC_INFLIGHT, RC_TAG_TAKEN, RC_DIRTY, RC_USAGE = 0, 10, 11, 12, 2


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    )


@pytest.fixture
def repo(tmp_path):
    """独立假仓库：SKILL.md（版本号真源）+ 闸脚本 + 一次提交。"""
    root = (tmp_path / "repo").resolve()
    (root / "scripts").mkdir(parents=True)
    shutil.copy(SCRIPT, root / "scripts" / "release-preflight.sh")
    (root / "SKILL.md").write_text(
        f"---\nversion: {VERSION}\n---\n\n# 假技能（回归测试用）\n", encoding="utf-8"
    )
    subprocess.run(["git", "init", "-q", "-b", "master", str(root)], check=True)
    _git(root, "config", "user.email", "preflight@example.com")
    _git(root, "config", "user.name", "preflight-test")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


def fake_sessions(*items):
    """构造 openclaw sessions list --json 的最小同形清单。"""
    out = []
    for i, item in enumerate(items):
        out.append(
            {
                "key": item.get("key", f"agent:main:fake:{i}"),
                "status": item.get("status", "running"),
                "label": item.get("label", ""),
                "spawnedCwd": item.get("cwd", ""),
                "ageMs": item.get("ageMs", 60000),
            }
        )
    return {"sessions": out}


def ls_remote(pairs):
    """构造 git ls-remote --heads --tags origin 的输出行。"""
    return "".join(f"{sha}\t{ref}\n" for sha, ref in pairs)


def run_gate(repo, tmp_path, sessions=None, remote=None, extra=(), tag=TAG):
    args = ["bash", str(repo / "scripts" / "release-preflight.sh"), tag]
    if sessions is not None:
        f = tmp_path / "sessions.json"
        f.write_text(
            sessions if isinstance(sessions, str) else json.dumps(sessions, ensure_ascii=False),
            encoding="utf-8",
        )
        args += ["--sessions-file", str(f)]
    if remote is not None:
        f = tmp_path / "remote.txt"
        f.write_text(remote, encoding="utf-8")
        args += ["--remote-file", str(f)]
    args += [a for a in extra if a]

    return subprocess.run(args, capture_output=True, text=True, cwd=str(repo))


# ---------------------------------------------------------------------------
# 通过路径
# ---------------------------------------------------------------------------
def test_clean_state_passes_and_prints_lineage(repo, tmp_path):
    """全干净（无在飞链 / 无编号占用 / 工作区干净）⇒ 通过，并打印四行现状。"""
    remote = ls_remote([("a" * 40, "refs/heads/master")])
    r = run_gate(repo, tmp_path, sessions=fake_sessions(), remote=remote)
    assert r.returncode == RC_PASS, r.stdout + r.stderr
    assert "✅ 发版前置闸通过" in r.stdout
    for marker in ("① 远端 master", "② 本地 HEAD", "③ tag 区间", "④ 在飞链"):
        assert marker in r.stdout, f"缺四行现状：{marker}\n{r.stdout}"


def test_unrelated_running_session_does_not_block(repo, tmp_path):
    """别的项目的在飞链（cwd 不在本仓、label 不含项目关键词）不算数。"""
    remote = ls_remote([("a" * 40, "refs/heads/master")])
    r = run_gate(
        repo,
        tmp_path,
        sessions=fake_sessions(
            {"key": "agent:novelist:main", "label": "写小说", "cwd": "/home/someone/novel"}
        ),
        remote=remote,
    )
    assert r.returncode == RC_PASS, r.stdout + r.stderr


def test_self_session_can_be_excluded(repo, tmp_path):
    """本链自身在飞 ⇒ 用 --self-session 排除后可通过（排除项打印在报告里）。"""
    remote = ls_remote([("a" * 40, "refs/heads/master")])
    mine = "agent:main:dashboard:self"
    s = fake_sessions({"key": mine, "label": "发版链自身", "cwd": str(repo)})
    blocked = run_gate(repo, tmp_path, sessions=s, remote=remote)
    assert blocked.returncode == RC_INFLIGHT
    ok = run_gate(repo, tmp_path, sessions=s, remote=remote, extra=("--self-session", mine))
    assert ok.returncode == RC_PASS, ok.stdout + ok.stderr
    assert "本链自身已排除" in ok.stdout


# ---------------------------------------------------------------------------
# 拒绝路径
# ---------------------------------------------------------------------------
def test_inflight_chain_blocks_with_list_and_howto(repo, tmp_path):
    """有同项目在飞链 ⇒ 拒绝，打印清单与「如何等」。"""
    remote = ls_remote([("a" * 40, "refs/heads/master")])
    s = fake_sessions(
        {"key": "agent:main:dashboard:inflight", "label": "并发修订链", "cwd": str(repo)},
        {"key": "agent:main:dashboard:done", "label": "已收口链", "cwd": str(repo), "status": "done"},
    )
    r = run_gate(repo, tmp_path, sessions=s, remote=remote)
    assert r.returncode == RC_INFLIGHT, r.stdout + r.stderr
    assert "agent:main:dashboard:inflight" in r.stdout
    assert "agent:main:dashboard:done" not in r.stdout  # status=done 不计入
    assert "如何等" in r.stdout
    assert "在飞链检查" in r.stdout


def test_tag_taken_locally_blocks(repo, tmp_path):
    """目标编号本地已占用 ⇒ 拒绝换号。"""
    _git(repo, "tag", TAG)
    remote = ls_remote([("a" * 40, "refs/heads/master")])
    r = run_gate(repo, tmp_path, sessions=fake_sessions(), remote=remote)
    assert r.returncode == RC_TAG_TAKEN, r.stdout + r.stderr
    assert "本地已有 tag" in r.stdout and TAG in r.stdout
    assert "换号" in r.stdout


def test_tag_taken_remotely_blocks(repo, tmp_path):
    """目标编号远端已占用（本地无该 tag）⇒ 也拒绝。"""
    remote = ls_remote(
        [("a" * 40, "refs/heads/master"), ("b" * 40, f"refs/tags/{TAG}")]
    )
    r = run_gate(repo, tmp_path, sessions=fake_sessions(), remote=remote)
    assert r.returncode == RC_TAG_TAKEN, r.stdout + r.stderr
    assert "远端已有 tag" in r.stdout


def test_remote_annotated_tag_deref_blocks(repo, tmp_path):
    """带注解 tag 的 `^{}` 解引用行同样算占用（不当成两个不同编号放过）。"""
    remote = ls_remote(
        [
            ("a" * 40, "refs/heads/master"),
            ("b" * 40, f"refs/tags/{TAG}"),
            ("c" * 40, f"refs/tags/{TAG}^{{}}"),
        ]
    )
    r = run_gate(repo, tmp_path, sessions=fake_sessions(), remote=remote)
    assert r.returncode == RC_TAG_TAKEN, r.stdout + r.stderr


def test_dirty_workspace_blocks(repo, tmp_path):
    """工作区不净（未提交改动）⇒ 拒绝。"""
    (repo / "SKILL.md").write_text("---\nversion: 2.12.21\n---\n改了没提交\n", encoding="utf-8")
    remote = ls_remote([("a" * 40, "refs/heads/master")])
    r = run_gate(repo, tmp_path, sessions=fake_sessions(), remote=remote)
    assert r.returncode == RC_DIRTY, r.stdout + r.stderr
    assert "工作区不净" in r.stdout
    assert "M SKILL.md" in r.stdout


def test_untracked_blocks_by_default_and_relaxes_with_flag(repo, tmp_path):
    """未跟踪文件默认计入「不净」（严格）；--allow-untracked 才放松。"""
    (repo / "residue.txt").write_text("另一条链的残留\n", encoding="utf-8")
    remote = ls_remote([("a" * 40, "refs/heads/master")])
    strict = run_gate(repo, tmp_path, sessions=fake_sessions(), remote=remote)
    assert strict.returncode == RC_DIRTY, strict.stdout + strict.stderr
    assert "?? residue.txt" in strict.stdout
    relaxed = run_gate(
        repo, tmp_path, sessions=fake_sessions(), remote=remote, extra=("--allow-untracked",)
    )
    assert relaxed.returncode == RC_PASS, relaxed.stdout + relaxed.stderr


def test_unparsable_inflight_list_fails_closed(repo, tmp_path):
    """在飞链清单拿不到 / 结构不对 ⇒ 拒绝（不按 0 条放行 = 不静默通过）。"""
    remote = ls_remote([("a" * 40, "refs/heads/master")])
    for bad in ('{"ok": false, "error": {"message": "no agent"}}', "not-json-at-all"):
        r = run_gate(repo, tmp_path, sessions=bad, remote=remote)
        assert r.returncode == RC_USAGE, r.stdout + r.stderr
        assert r.returncode != RC_PASS
        assert "无法解析" in r.stderr or "无法获取" in r.stderr


def test_blocked_output_never_silent(repo, tmp_path):
    """拒绝时必须有可读原因（不静默非 0 退出）。"""
    remote = ls_remote([("a" * 40, "refs/heads/master")])
    s = fake_sessions({"key": "agent:main:fake:x", "label": "并发链", "cwd": str(repo)})
    r = run_gate(repo, tmp_path, sessions=s, remote=remote)
    assert r.returncode != RC_PASS
    assert "⛔ 发版前置闸未通过" in r.stdout
    assert "不进入 tag / push / GitHub Release / 净化包 任何一步" in r.stdout


def test_gate_is_read_only(repo, tmp_path):
    """闸不得改任何 ref / 不建 tag（只读拒绝器）。"""
    before = _git(repo, "for-each-ref", "--format=%(refname) %(objectname)").stdout
    remote = ls_remote([("a" * 40, "refs/heads/master")])
    run_gate(repo, tmp_path, sessions=fake_sessions(), remote=remote)
    after = _git(repo, "for-each-ref", "--format=%(refname) %(objectname)").stdout
    assert before == after
    assert not _git(repo, "tag", "-l").stdout.strip()


# ---------------------------------------------------------------------------
# 放松模式 --allow-existing-tag（教训 #334）：② 口径 = 「编号是否被本链之外的人占用」
# 背景：create-github-release.sh 第 2 步硬性要求本地已有 tag（先 tag、后建 Release），
#   而它调闸时闸的 ② 又把「已有该 tag」判为占用 → 正常发版路径被自己的闸自锁（实测 EXIT=11）。
#   故闸加 --allow-existing-tag：仅当 tag 属本链历史且远端同号同对象才放行，其余仍拒绝。
# ---------------------------------------------------------------------------
def _commit(repo, filename, content, message):
    (repo / filename).write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def test_allow_existing_tag_same_commit_passes_and_notices(repo, tmp_path):
    """tag 正指向待发布提交（HEAD）⇒ 放松模式放行，且打印醒目提示（默认口径不变）。"""
    _git(repo, "tag", TAG)
    remote = ls_remote([("a" * 40, "refs/heads/master")])
    strict = run_gate(repo, tmp_path, sessions=fake_sessions(), remote=remote)
    assert strict.returncode == RC_TAG_TAKEN, strict.stdout + strict.stderr
    relaxed = run_gate(
        repo, tmp_path, sessions=fake_sessions(), remote=remote,
        extra=("--allow-existing-tag",),
    )
    assert relaxed.returncode == RC_PASS, relaxed.stdout + relaxed.stderr
    assert "--allow-existing-tag 已生效" in relaxed.stdout
    assert "属本链历史" in relaxed.stdout
    assert "已存在（--allow-existing-tag 已证属本链历史" in relaxed.stdout


def test_allow_existing_tag_ancestor_commit_passes(repo, tmp_path):
    """tag 落在 HEAD 的祖先提交上（发版后再补 changelog 提交，v2.12.16 同型）⇒ 仍放行。"""
    tagged = _git(repo, "rev-parse", "HEAD").stdout.strip()
    _git(repo, "tag", TAG)
    head = _commit(repo, "later.txt", "发版后的补提交\n", "changelog: 补章节")
    assert head != tagged
    remote = ls_remote([("a" * 40, "refs/heads/master")])
    r = run_gate(
        repo, tmp_path, sessions=fake_sessions(), remote=remote,
        extra=("--allow-existing-tag",),
    )
    assert r.returncode == RC_PASS, r.stdout + r.stderr


def test_allow_existing_tag_foreign_commit_blocks(repo, tmp_path):
    """tag 指向不在本链历史上的提交（另一条链建的号）⇒ 仍拒绝，并给出 --expect-commit 提示。"""
    _git(repo, "checkout", "-q", "-b", "side")
    _commit(repo, "side.txt", "另一条链的提交\n", "side: 别的链")
    _git(repo, "tag", TAG)
    _git(repo, "checkout", "-q", "master")
    remote = ls_remote([("a" * 40, "refs/heads/master")])
    r = run_gate(
        repo, tmp_path, sessions=fake_sessions(), remote=remote,
        extra=("--allow-existing-tag",),
    )
    assert r.returncode == RC_TAG_TAKEN, r.stdout + r.stderr
    assert "不在待发布提交" in r.stdout
    assert "--expect-commit" in r.stdout


def test_allow_existing_tag_expect_commit_override_passes(repo, tmp_path):
    """补发旧版 Release：显式 --expect-commit 指向该版本提交 ⇒ 放行（不再与 HEAD 比对）。"""
    _git(repo, "checkout", "-q", "-b", "side")
    side_sha = _commit(repo, "side.txt", "另一条链的提交\n", "side: 别的链")
    _git(repo, "tag", TAG)
    _git(repo, "checkout", "-q", "master")
    remote = ls_remote([("a" * 40, "refs/heads/master")])
    r = run_gate(
        repo, tmp_path, sessions=fake_sessions(), remote=remote,
        extra=("--allow-existing-tag", "--expect-commit", side_sha),
    )
    assert r.returncode == RC_PASS, r.stdout + r.stderr
    assert "属本链历史" in r.stdout


def test_allow_existing_tag_remote_same_object_passes(repo, tmp_path):
    """远端已有同号且指向同一对象（annotated tag：含 `^{}` 解引用行）⇒ 放行。"""
    _git(repo, "tag", "-a", TAG, "-m", "release: 样本")
    tag_obj = _git(repo, "rev-parse", TAG).stdout.strip()
    commit = _git(repo, "rev-parse", f"{TAG}^{{commit}}").stdout.strip()
    remote = ls_remote(
        [
            ("a" * 40, "refs/heads/master"),
            (tag_obj, f"refs/tags/{TAG}"),
            (commit, f"refs/tags/{TAG}^{{}}"),
        ]
    )
    r = run_gate(
        repo, tmp_path, sessions=fake_sessions(), remote=remote,
        extra=("--allow-existing-tag",),
    )
    assert r.returncode == RC_PASS, r.stdout + r.stderr
    assert "远端同号同对象" in r.stdout


def test_allow_existing_tag_remote_different_object_blocks(repo, tmp_path):
    """远端同号但指向不同对象（号被另一条链占用）⇒ 拒绝。"""
    _git(repo, "tag", TAG)
    remote = ls_remote(
        [("a" * 40, "refs/heads/master"), ("d" * 40, f"refs/tags/{TAG}")]
    )
    r = run_gate(
        repo, tmp_path, sessions=fake_sessions(), remote=remote,
        extra=("--allow-existing-tag",),
    )
    assert r.returncode == RC_TAG_TAKEN, r.stdout + r.stderr
    assert "指向对象与本地不同" in r.stdout


def test_allow_existing_tag_local_absent_remote_present_blocks(repo, tmp_path):
    """本地无 tag、远端有 ⇒ 归属无法核验，放松模式同样拒绝（失败关闭）。"""
    remote = ls_remote(
        [("a" * 40, "refs/heads/master"), ("b" * 40, f"refs/tags/{TAG}")]
    )
    r = run_gate(
        repo, tmp_path, sessions=fake_sessions(), remote=remote,
        extra=("--allow-existing-tag",),
    )
    assert r.returncode == RC_TAG_TAKEN, r.stdout + r.stderr
    assert "归属无法核验" in r.stdout


def test_allow_existing_tag_absent_everywhere_still_passes(repo, tmp_path):
    """放松模式下若号本来就空着（无 tag）⇒ 照常放行（放松只作用于「已存在」这一维）。"""
    remote = ls_remote([("a" * 40, "refs/heads/master")])
    r = run_gate(
        repo, tmp_path, sessions=fake_sessions(), remote=remote,
        extra=("--allow-existing-tag",),
    )
    assert r.returncode == RC_PASS, r.stdout + r.stderr
    assert "本地未占用 / 远端未占用" in r.stdout


def test_remote_unreachable_still_fails_closed(repo, tmp_path):
    """放松模式下远端查不到 ⇒ 仍拒绝（退出 2），不按「未占用」放行。"""
    _git(repo, "tag", TAG)
    r = run_gate(repo, tmp_path, sessions=fake_sessions(), remote=None,
                 extra=("--allow-existing-tag",))
    assert r.returncode == RC_USAGE, r.stdout + r.stderr
    assert "无法查询远端 tag" in r.stderr
