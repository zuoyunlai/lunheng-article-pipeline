#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_publish_changelog_extraction.py — changelog 提取器的正向样本（v2.12.57 新增）

背景（教训 #421，2026-09-18 实测）：
  v2.12.56 发布 ClawHub 时被 fail-closed 拦死 —— `scripts/publish-clawhub.sh` 的
  `extract_changelog()` 压缩器只认「`> **主题：…**` 主题行 + `### 小节标题`」两种
  **旧**写法，而 CHANGELOG 章节的写作风格早已迁移为顶层 `- **要点**：详解`
  （v2.12.54 / v2.12.55 / v2.12.56 三章的 `###` 计数均为 0）⇒ 提取恒空 ⇒ `exit 3`，
  发布中止。历史遗留：v2.12.53 仅因该章残留 1 行主题行才「非空」通过 —— 这道门长期
  近乎空转（页面正文里本版要点一条都没进）。

本文件的作用 = 给这道门补**「应当放行」的正向样本**（教训 #334 同族、教训 #421 的结论）：
  判据是「解析结果」而非「真源内容」，当真源书写格式自由时，「解析为空」既可能是
  「真源缺失」也可能是「提取器认不出格式」—— 只测后者（fail-closed）永远为真，
  真正会静默失效的是前者。故必须证明「当前实际使用的格式真的能被解析出来」。

口径：从真脚本里抽出 `extract_changelog()` 函数真身执行（**不复制一份实现**，
  避免第二真源漂移），在临时 SKILL_ROOT 下放构造章节 —— 测的是脚本行为，不是源码字面。
"""
import os
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).parent.parent
PUBLISH = ROOT / "scripts" / "publish-clawhub.sh"
SKILL_MD = ROOT / "SKILL.md"

# 新格式（当前写作风格）：顶层 `- **要点**：详解` + 缩进子项
SECTION_NEW_FORMAT = """# Changelog

---

## [v9.9.9] — 2026-09-18

- **要点甲**：甲的解释（含 `代码` 与 **加粗**）。
  - 缩进子项一：这条属详解，**不入**平台正文。
  - 缩进子项二：同样不入正文。
- **要点乙**：乙的解释。
- 纯文本条目：同样不入正文。

---

## [v9.9.8] — 2026-09-17

- **上一版要点**：不应被本版提取带出。
"""

# 旧格式（历史章节）：`> **主题：…**` + `### 小节标题`
SECTION_LEGACY_FORMAT = """# Changelog

---

## [v9.9.9] — 2026-09-18

> **主题：旧章主题行**

### 小节一

正文。

### 小节二

正文。

---

## [v9.9.8] — 2026-09-17

> **主题：上一版主题**
"""

SECTION_MISSING_VERSION = """# Changelog

---

## [v9.9.8] — 2026-09-17

- **上一版要点**：本版不存在。
"""


def _extract_function_source() -> str:
    """从 publish-clawhub.sh 抽出 extract_changelog() 函数真身。

    终止判据 = 列 0 的 `}`（函数体内 awk 的 `{` / `}` 一律在缩进行，
    故第一个顶格 `}` 即函数结束）。
    """
    lines, inside = [], False
    for line in PUBLISH.read_text(encoding="utf-8").splitlines():
        if re.match(r"^extract_changelog\(\) \{", line):
            inside = True
        if inside:
            lines.append(line)
            if line == "}":
                break
    assert lines and lines[-1] == "}", "未能从 publish-clawhub.sh 抽出 extract_changelog() 函数体"
    assert "primary=" in "\n".join(lines), "抽出的内容不像 extract_changelog() 函数体"
    return "\n".join(lines) + "\n"


def _run_extract(skill_root: pathlib.Path, changelog_text: str, version: str = "9.9.9") -> str:
    """在给定 SKILL_ROOT（临时目录或本仓）下执行真函数，返回 stdout。"""
    skill_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "CHANGELOG.md").write_text(changelog_text, encoding="utf-8")
    fn = skill_root / "_extracted_fn.sh"
    fn.write_text(_extract_function_source(), encoding="utf-8")
    script = f'set -euo pipefail\nsource "{fn}"\nextract_changelog "{version}"\n'
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                       cwd=str(skill_root),
                       env={**os.environ, "SKILL_ROOT": str(skill_root)})
    assert r.returncode == 0, f"提取器执行失败（rc={r.returncode}）：{r.stderr}"
    return r.stdout


# ---------------- 正向样本：当前实际书写格式必须「放行」 ----------------

def test_new_format_section_extracts_nonempty(tmp_path):
    """顶层要点标题格式（当前写法）→ 提取非空（本用例若红即「门在空转」，教训 #421）"""
    out = _run_extract(tmp_path, SECTION_NEW_FORMAT)
    assert out.strip(), "新格式章节提取为空 —— 提取器认不出真源的实际书写格式（教训 #421 复发）"
    lines = [ln for ln in out.splitlines() if ln.strip()]
    # 压缩语义：兜底口径只取「顶层要点标题」本身，冒号后的详解不进平台正文
    assert lines == ["- 要点甲", "- 要点乙"], f"新格式提取内容不符：{lines}"


def test_new_format_excludes_indented_children(tmp_path):
    """兜底口径只取顶层要点：缩进子项 / 纯文本条目不得入正文（页面仍是压缩摘要）"""
    out = _run_extract(tmp_path, SECTION_NEW_FORMAT)
    for absent in ("缩进子项一", "缩进子项二", "纯文本条目", "上一版要点"):
        assert absent not in out, f"「{absent}」不该进平台正文：\n{out}"
    assert "**" not in out and "`" not in out, f"提取正文残留 markdown 强调符：{out}"


# ---------------- 回归：主口径行为不变 + fail-closed 分支仍然可达 ----------------

def test_legacy_format_section_still_extracts(tmp_path):
    """旧格式章节（历史章节）行为不变：主题行 + `###` 小节标题都保留"""
    out = _run_extract(tmp_path, SECTION_LEGACY_FORMAT)
    assert "旧章主题行" in out, f"主口径（主题行）被破坏：{out}"
    assert "- 小节一" in out and "- 小节二" in out, f"主口径（### 标题）被破坏：{out}"


def test_primary_wins_when_both_styles_present(tmp_path):
    """两种写法并存 → 主口径优先（旧章不因新增兜底而改变行为）"""
    mixed = SECTION_LEGACY_FORMAT.replace(
        "> **主题：旧章主题行**",
        "> **主题：旧章主题行**\n\n- **顶层要点**：混排时应由主口径胜出。")
    out = _run_extract(tmp_path, mixed)
    assert "旧章主题行" in out and "- 小节一" in out
    assert "顶层要点" not in out, f"并列时兜底口径不该覆盖主口径：{out}"


def test_missing_version_still_yields_empty(tmp_path):
    """章节缺失 → 仍为空（fail-closed 分支可达，发布中止语义未被兜底冲掉）"""
    out = _run_extract(tmp_path, SECTION_MISSING_VERSION)
    assert out.strip() == "", f"不存在的版本不该提取出内容：{out}"


# ---------------- 真实真源：随包 CHANGELOG 的当前版本必须可提取 ----------------

def test_repo_current_version_changelog_extracts_nonempty(tmp_path):
    """真源防线：本仓 CHANGELOG 的**当前 SKILL.md 版本**章节必须提取非空。

    这条把「真源写法」与「提取器口径」钉在一起：下次再有谁换了书写风格（或改坏了
    提取器），不必等发版被 fail-closed 拦死才发现（教训 #421 的真正代价 = 三个版本空转）。
    """
    m = re.search(r"^[ \t]*version:[ \t]*([0-9]+\.[0-9]+\.[0-9]+)", SKILL_MD.read_text(encoding="utf-8"), re.M)
    assert m, "SKILL.md 缺 version 字段"
    version = m.group(1)
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [v{version}]" in changelog, \
        f"CHANGELOG.md 缺 v{version} 章节（半成品版本戳，教训 #352）"
    # 隔离：真源文本拷进临时 SKILL_ROOT 再跑（绝不能往仓库根写临时文件 ——
    # 那会让「工作区干净」的发版前置闸（教训 #332）在跑测试后失败）
    out = _run_extract(tmp_path, changelog, version)
    assert out.strip(), f"v{version} 章节提取为空 —— 提取器认不出本仓的实际书写格式（教训 #421）"
    assert len(out.splitlines()) <= 40, "提取正文超过 40 行压缩上限"
