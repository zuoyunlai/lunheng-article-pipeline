#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_changelog_fill_idempotent.py — changelog-check.py --fill 幂等性回归测试（v2.12.19，教训 #330）

背景（v2.12.17 实测）：
  `--fill` 每次运行都给每个版本章节多加一条 `---` 分隔行——
  142 章节的提交态 184 行 `---` → run1 326 → run2 468（每次净增「章节数」行）。
  根因：`split_changelog()` 切出的章节文本**天然包含其末尾的分隔行**，
  `cmd_fill()` 又追加一条 → 每次累积。伪 diff 掩盖真实变更，`--fill` 无法安全重跑。

本测试零网络依赖（不调 gh / 不碰 GitHub），只验证纯函数：
  - strip_section_separator()：尾部 `---`/空行是否被剥离干净
  - render_changelog()：render(render(x)) == render(x)，且每章节恰好一条分隔行
"""
import importlib.util
import inspect
import re
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_ROOT / "scripts" / "changelog-check.py"

spec = importlib.util.spec_from_file_location("changelog_check", SCRIPT)
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)


def count_separators(text):
    """按 grep -c '^---$' 口径计数（分隔行之间有空行，不能用相邻行判断）。"""
    return sum(1 for line in text.splitlines() if line == "---")


# --------------------------------------------------------------------------
# 1. strip_section_separator：尾部归一化
# --------------------------------------------------------------------------

def test_strip_trailing_separator():
    assert cc.strip_section_separator("## [v1.0.0] — 2026-01-01\n\n正文\n\n---\n") == \
        "## [v1.0.0] — 2026-01-01\n\n正文"


def test_strip_accumulated_separators():
    """累积多条的尾部 `---` 必须一次剥净（否则幂等只能靠多跑几次达成）。"""
    assert cc.strip_section_separator("正文\n\n---\n\n---\n\n---\n\n") == "正文"


def test_strip_keeps_inbody_rule():
    """章节正文中间的 `---` 是正文内容（横向分隔线），不得误删。"""
    section = "## [v1.0.0]\n\n第一节\n\n---\n\n第二节\n\n---\n"
    assert cc.strip_section_separator(section) == \
        "## [v1.0.0]\n\n第一节\n\n---\n\n第二节"


# --------------------------------------------------------------------------
# 2. render_changelog：幂等 + 结构恒定
# --------------------------------------------------------------------------

def test_render_is_idempotent_on_real_changelog():
    """真实 CHANGELOG.md：渲染两次必须逐字相同（--fill 重跑零 diff 的纯函数等价形式）。"""
    text = (SKILL_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    header, sections = cc.split_changelog(text)
    known = dict(sections)
    once = cc.render_changelog(header, known)
    header2, sections2 = cc.split_changelog(once)
    twice = cc.render_changelog(header2, dict(sections2))
    assert once == twice


def test_render_normalizes_accumulated_damage():
    """模拟旧 bug 的产物（每章节多挂一条 `---`）：一次渲染即收敛，且幂等。"""
    text = (SKILL_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    header, sections = cc.split_changelog(text)
    damaged = {v: s.rstrip("\n") + "\n\n---\n" for v, s in sections}
    fixed_once = cc.render_changelog(header, damaged)
    header2, sections2 = cc.split_changelog(fixed_once)
    assert fixed_once == cc.render_changelog(header2, dict(sections2))
    # 收敛后：每章节恰好一条尾部结构分隔行（不能靠「多跑几次」才收敛）
    assert count_separators(fixed_once) == count_separators(
        cc.render_changelog(header, dict(sections)))


def test_render_separator_count_stable():
    """渲染结果里「后随 `## [` 的结构分隔行」数 == 章节数（头部 1 条 + 章节间 N-1 条 + 末尾 1 条）。"""
    text = (SKILL_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    header, sections = cc.split_changelog(text)
    rendered = cc.render_changelog(header, dict(sections))
    lines = rendered.splitlines()
    structural = 0
    for i, line in enumerate(lines):
        if line != "---":
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        # 结构分隔行 = 其后（跳过空行）紧跟章节标题；末尾一条其后无内容
        if (j < len(lines) and lines[j].startswith("## [")) or j == len(lines):
            structural += 1
    assert structural == len(sections) + 1


def test_split_detects_all_sections():
    """口径不变：`^## [v...]` 章节识别（含围栏内同形行不受影响的正则边界）。"""
    text = (SKILL_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    _, sections = cc.split_changelog(text)
    assert len(cc.HEADING_RE.findall(text)) == len(sections)
    assert all(v.startswith("v") for v, _ in sections)


# --------------------------------------------------------------------------
# 3. v2.12.67 README「当前版本」块容量门（审计 P2-4）
# --------------------------------------------------------------------------

def _readme_prose_line(text):
    return re.search(r"^\*\*v[0-9.]+\*\*（[^）]*当前版本[^\n]*$", text, re.M)


def test_readme_prose_capacity_positive():
    """真实 README：当前版本行存在且 ≤ 上限（正向门，堆叠式写法已改写为摘要）。"""
    text = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
    assert cc.readme_prose_gate(text) is None


def test_readme_prose_capacity_oversize_detected():
    """反向：当前版本行膨胀超上限（堆叠式 changelog 复述回潮）⇒ 必须报上限。"""
    text = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
    line = _readme_prose_line(text).group(0)
    bad = text.replace(line, line + "（" + "历史版本全文复述。" * 40 + "）", 1)
    err = cc.readme_prose_gate(bad)
    assert err and "上限" in err, f"超限未检出：{err}"


def test_readme_prose_capacity_missing_line_detected():
    """反向：当前版本行被删 ⇒ 必须报缺行（与版本一致性断言互补的判据面）。"""
    text = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
    line = _readme_prose_line(text).group(0)
    err = cc.readme_prose_gate(text.replace(line + "\n", "", 1))
    assert err and "缺" in err, f"缺行未检出：{err}"


def test_readme_prose_capacity_gate_is_wired():
    """接线：cmd_check 必须调用 readme_prose_gate（防门空转——函数在、没人调，教训 #421 同族）。"""
    assert "readme_prose_gate" in inspect.getsource(cc.cmd_check)
