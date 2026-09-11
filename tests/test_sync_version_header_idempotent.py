#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_sync_version_header_idempotent.py — 文件头版本戳归一化回归测试（v2.12.20，教训 #331）

背景（实测）：
  `sync-version.sh` 的 header 模式用
      sed -i "${CLOSE_LINE}a\\ … \\ …"
  追加版本戳行，sed 的 `a\\` 会把**尾部续行**当成插入文本的一部分（等于多写一个空行）；
  末尾的 trim() 只裁多余的 `> 版本：` 行、不管空行 → 每次 sync 在每个受管文件的版本戳行后
  净增 1 个空行：README.md 逐版回读 0 → 9（v2.12.10 → v2.12.19），教训索引累计 47 行。

本测试零网络依赖，只验证纯函数 `normalize_header()`（可 import 的单一写入口）：
  - 幂等：normalize(normalize(x)) == normalize(x)
  - 一次收敛：历史累积的空行 / 旧版本行**一轮**归一化即到位（不能靠多跑几次）
  - 边界：正文中的多空行不被误伤；无版本戳的文件不动；frontmatter 文件锚点正确
  - 仓内不变量：受管文件「版本戳行后恰好 1 个空行」，且 CLI --check 对当前仓库退出 0
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_ROOT / "scripts" / "normalize-version-header.py"

spec = importlib.util.spec_from_file_location("normalize_version_header", SCRIPT)
nvh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nvh)

STAMP = "> 版本：v2.12.20（自动同步 2026-09-11）"
LANG = ("> 🌐 **语言政策**：产出语言默认中文，Phase 0 可改 English / 中英混 / 其他"
        "（写入任务简报「目标语言」字段，全流程以该字段为准）；"
        "中文特化（G14 中文 AI 痕迹检测 / GB/T 7714-2015 引用规范）是设计定位，"
        "不构成使用者语种限制。")

SKIP_DIRS = {".git", "outputs", "archive", "__pycache__", ".pytest_cache"}


def blanks_after_stamp(lines):
    """版本戳行之后、下一条非空行之前的空行数（缺陷的直读指标）。"""
    for i, line in enumerate(lines):
        if line.startswith("> 版本："):
            n = 0
            for nxt in lines[i + 1:]:
                if nxt.strip() == "":
                    n += 1
                else:
                    return n
            return n
    raise AssertionError("no version stamp")


def repo_md_files():
    """仓内真实 md 语料（排除产物/归档/备份）。"""
    out = []
    for path in sorted(SKILL_ROOT.rglob("*.md")):
        rel = path.relative_to(SKILL_ROOT)
        if any(part in SKIP_DIRS for part in rel.parts) or ".bak." in path.name:
            continue
        out.append(path)
    return out


# --------------------------------------------------------------------------
# 1. 幂等：normalize(normalize(x)) == normalize(x)
# --------------------------------------------------------------------------

def test_normalize_is_idempotent_over_repo_corpus():
    """真实仓内语料：每个文件归一化两次必须逐字相同（= 连跑两次零 diff 的纯函数等价形式）。"""
    checked = 0
    for path in repo_md_files():
        lines = path.read_text(encoding="utf-8").split("\n")
        once, _ = nvh.normalize_header(lines, STAMP)
        twice, changed = nvh.normalize_header(once, STAMP)
        assert twice == once, f"{path} 第二轮仍在变（不幂等）"
        assert changed is False, f"{path} 第二轮仍报告变更"
        checked += 1
    assert checked > 50, f"语料过少（{checked}），测试未真正覆盖仓库"


def test_stamp_write_is_idempotent_on_damaged_header():
    """模拟旧 bug 产物（版本戳后 9 空行 + 语言政策后再 12 空行）：一轮收敛且幂等。"""
    damaged = [STAMP, *[""] * 9, LANG, *[""] * 12, "# 标题", "", "正文"]
    once, changed = nvh.normalize_header(damaged, STAMP)
    assert changed is True
    assert once[:3] == [STAMP, "", LANG], once[:3]
    assert blanks_after_stamp(once) == 1
    twice, changed2 = nvh.normalize_header(once, STAMP)
    assert twice == once and changed2 is False


def test_version_bump_replaces_stack_and_collapses_blanks():
    """版本升位：旧版本行 + 累积空行一次性收敛为单行新版本戳。"""
    damaged = ["> 版本：v2.12.19（自动同步 2026-09-10）", "", "",
               "> 版本：v2.12.18（自动同步 2026-09-09）", "", "", "# 标题"]
    once, _ = nvh.normalize_header(damaged, STAMP)
    assert once[0] == STAMP
    assert sum(1 for line in once if line.startswith("> 版本：")) == 1
    assert blanks_after_stamp(once) == 1


# --------------------------------------------------------------------------
# 2. 边界：不误伤正文 / 不误碰非受管文件
# --------------------------------------------------------------------------

def test_body_blank_runs_are_preserved():
    """正文内部的多空行是内容（如分隔层级），只归一化头部元数据块。"""
    lines = [STAMP, "", "", "# 标题", "", "", "第一段", "", "", "", "第二段"]
    out, _ = nvh.normalize_header(lines, STAMP)
    assert out == [STAMP, "", "# 标题", "", "", "第一段", "", "", "", "第二段"]


def test_file_without_stamp_is_untouched():
    lines = ["# 纯正文", "", "", "保留"]
    out, changed = nvh.normalize_header(lines)
    assert out == lines and changed is False


def test_frontmatter_stamp_goes_after_closing_marker():
    lines = ["---", "name: x", "version: 1.0.0", "---", "", "# 正文"]
    out, _ = nvh.normalize_header(lines, STAMP)
    assert out == ["---", "name: x", "version: 1.0.0", "---", STAMP, "", "# 正文"]


def test_normalize_without_version_only_collapses():
    """未列入 --update 的文件：只收敛，不改版本号、不新增版本戳。"""
    lines = ["> 版本：v2.12.19（自动同步 2026-09-10）", "", "", "", "# 正文"]
    out, _ = nvh.normalize_header(lines)
    assert out == ["> 版本：v2.12.19（自动同步 2026-09-10）", "", "# 正文"]


# --------------------------------------------------------------------------
# 3. 仓内不变量（缺陷的回归护栏）
# --------------------------------------------------------------------------

def test_repo_stamped_files_have_exactly_one_blank_after_stamp():
    """受管文件版本戳行后**恰好 1 个空行**——旧实现每发一版 +1，本条即该缺陷的护栏。"""
    checked = 0
    for path in repo_md_files():
        lines = path.read_text(encoding="utf-8").split("\n")
        if not nvh.has_stamp(lines):
            continue
        checked += 1
        assert blanks_after_stamp(lines) == 1, \
            f"{path} 版本戳后空行数 = {blanks_after_stamp(lines)}（应为 1）"
    assert checked >= 70, f"带版本戳的文件过少（{checked}）"


def test_cli_check_passes_on_repo():
    """CLI --check 对当前仓库退出 0 = 整棵树已是规范形态（可直接接门/CI）。"""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(SKILL_ROOT), "--check"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
