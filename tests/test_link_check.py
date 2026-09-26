#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""门 U 第三类：活文档反引号内联 `.md` 引用的可解析性（v2.12.59 新增）。

背景（2026-09-19 全面审计 P1-1 / P1-2）：
  门 U 原判据面 = ① markdown 链接 + ② SKILL.md 裸文件名。两类合起来**仍不覆盖**
  活文档里的**反引号内联路径引用**（例：`_shared/真源/host-verify-recipe.md`）。
  实测后果：`host-verify-recipe.md` 被 2 处活文档引用（均在净化包可见面）却**从未存在过**，
  而门 U 报「全部可解析」——给的是「markdown 链接面全绿」，被读成「引用面全绿」。
  可复用结论（教训 #427）：**判据的扫描面 = 该缺陷「类」的宿主集，不是「上次出事的那一个文件」**。

本测试锁定三件事：
  ① 基线：真源下三类检查全绿、退出码 0；
  ② 变异：注入一条指向不存在文档的反引号引用 ⇒ 必须报错并点名该 token（门真跑到，非空转）；
  ③ 不过度拦截：扩展名枚举写法（`` `.md` ``）与运行时/白名单 token（`status.md` / `交付说明.md`）
     不得报错 —— 防「把门收紧到天天误报 ⇒ 训练读者忽略告警」（教训同族）。

约束（教训 #333 同族）：**变异注入一律在临时整仓副本中进行，真源零写入**；
  护栏单测 test_truth_source_untouched 校验真源 sha256 前后一致。
"""
import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import tracked_tree

REPO = Path(__file__).resolve().parents[1]
LINK_CHECK = REPO / "scripts" / "link-check.py"
# 变异落点：选一个既在扫描面内、又不在净化白名单排除项里的活文档
MUTATION_TARGET = REPO / "references" / "_shared" / "真源" / "关键协议.md"
COPY_IGNORE = shutil.ignore_patterns(
    ".git", "outputs", "reports", "memory", "__pycache__", ".pytest_cache", "*.bak.*",
)
GHOST = "_shared/__ghost_audit_probe__.md"


def run_link_check(root: Path) -> tuple[int, str]:
    r = subprocess.run(
        ["python3", str(root / "scripts" / "link-check.py")],
        cwd=root, capture_output=True, text=True, timeout=180,
    )
    return r.returncode, r.stdout + r.stderr


@pytest.fixture()
def repo_copy(tmp_path: Path) -> Path:
    """整仓临时副本（真源零写入）"""
    dst = tmp_path / "repo"
    tracked_tree(REPO, dst)
    return dst


def test_baseline_link_check_passes() -> None:
    """真源基线：三类检查全绿、退出码 0"""
    rc, out = run_link_check(REPO)
    assert rc == 0, f"基线应为绿：\n{out}"
    assert "活文档内联引用全部可解析" in out, f"第三类检查未参与输出：\n{out}"


def test_injected_dangling_inline_ref_is_caught(repo_copy: Path) -> None:
    """变异：注入指向不存在文档的反引号引用 ⇒ 必须报错并点名 token

    这条是门有效性的核心（同族：教训 #175/#421「门只描述不执行 ⇒ 静默空转」）。
    """
    target = repo_copy / MUTATION_TARGET.relative_to(REPO)
    src = target.read_text(encoding="utf-8")
    assert GHOST not in src, "变异 token 不应预先存在于真源"
    target.write_text(src + f"\n\n> 变异探针：`{GHOST}`\n", encoding="utf-8")

    rc, out = run_link_check(repo_copy)
    assert rc == 1, f"注入悬空内联引用后应报错：\n{out}"
    assert GHOST in out, f"报错未点名该 token：\n{out}"
    assert "活文档反引号内联引用不可解析" in out, f"未落到第三类检查：\n{out}"


def test_extension_enumeration_is_not_flagged(repo_copy: Path) -> None:
    """不过度拦截：扩展名枚举（`.md` 单独成 token，无 stem）不是路径"""
    target = repo_copy / MUTATION_TARGET.relative_to(REPO)
    src = target.read_text(encoding="utf-8")
    target.write_text(src + "\n\n> 变异探针：版本戳载体有 `.sh`/`.md` 两种写法。\n",
                      encoding="utf-8")

    rc, out = run_link_check(repo_copy)
    assert rc == 0, f"扩展名枚举不应被判为断链：\n{out}"


def test_runtime_and_allowlist_tokens_are_not_flagged(repo_copy: Path) -> None:
    """不过度拦截：运行时产物与白名单 token 不得报错（否则门会被训练成噪声）"""
    target = repo_copy / MUTATION_TARGET.relative_to(REPO)
    src = target.read_text(encoding="utf-8")
    target.write_text(
        src + "\n\n> 变异探针：产物在 `status.md`，交付物为 `交付说明.md`，"
              "心跳形如 `01-文献检索-heartbeat.md`。\n",
        encoding="utf-8",
    )

    rc, out = run_link_check(repo_copy)
    assert rc == 0, f"运行时/白名单 token 不应判为断链：\n{out}"


def test_truth_source_untouched() -> None:
    """护栏：本测试不得改动真源（变异只在临时副本）"""
    before = hashlib.sha256(MUTATION_TARGET.read_bytes()).hexdigest()
    assert GHOST not in MUTATION_TARGET.read_text(encoding="utf-8")
    after = hashlib.sha256(MUTATION_TARGET.read_bytes()).hexdigest()
    assert before == after
