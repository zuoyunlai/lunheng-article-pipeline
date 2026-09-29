#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""markdown-structure-lint.py 的反向注入与现状守卫。

锁定两类硬错误（字面 \\n、未闭合围栏）+ 两类 strict 错误
（重复章号、孤立标题）；仓库现状必须通过默认扫描。
"""
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("mlint", ROOT / "scripts" / "markdown-structure-lint.py")
_mod = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mod)


def test_catches_literal_backslash_n_outside_fence():
    text = "正常一行" + chr(10) + "下一行含字面 \\n 终止符" + chr(10)
    errs = _mod.lint_text(text, "<text>")
    assert any("literal" in e for e in errs), errs


def test_literal_backslash_n_inside_fence_is_exempt():
    text = "```" + chr(10) + "内含字面 \\n 终止符" + chr(10) + "```" + chr(10)
    errs = _mod.lint_text(text, "<text>")
    assert not any("literal" in e for e in errs), errs


def test_catches_unclosed_code_fence():
    text = "前文" + chr(10) + "```" + chr(10) + "未闭合围栏" + chr(10)
    errs = _mod.lint_text(text, "<text>")
    assert any("unclosed" in e for e in errs), errs


def test_clean_file_passes():
    text = "# 标题" + chr(10) + chr(10) + "段落一。" + chr(10) + chr(10) + "## 子节" + chr(10) + chr(10) + "段落二。" + chr(10)
    errs = _mod.lint_text(text, "<text>")
    assert errs == [], errs


def test_strict_catches_duplicate_section_number():
    text = "# 一" + chr(10) + "## 一、内容" + chr(10) + "段落" + chr(10) + "## 一、其它" + chr(10) + "段落" + chr(10)
    errs = _mod.lint_text(text, "<text>", strict=True)
    assert any("duplicate" in e for e in errs), errs


def test_strict_catches_isolated_heading():
    text = "# 一" + chr(10) + "## 二、孤立" + chr(10) + "## 三、另一节" + chr(10) + "段落" + chr(10)
    errs = _mod.lint_text(text, "<text>", strict=True)
    assert any("isolated" in e for e in errs), errs


def test_non_strict_does_not_flag_strict_violations():
    text = "# 一" + chr(10) + "## 二、孤立" + chr(10) + "## 三、另一节" + chr(10) + "段落" + chr(10)
    errs = _mod.lint_text(text, "<text>", strict=False)
    assert errs == [], errs


def test_real_repo_passes_default_scan():
    """默认扫描（不含 strict）必须在现状仓库退出 0。"""
    errs = _mod.scan(ROOT, ("reports/", "archive/", "教训索引.md", "CHANGELOG"), strict=False)
    assert errs == [], errs[:5]

