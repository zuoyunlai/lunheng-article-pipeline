#!/usr/bin/env python3
"""第二批真源/语义簇合同门的正向与反向回归。"""
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

contract = load("contract_check", ROOT / "scripts" / "contract-check.py")
lang = load("inject_lang_policy", ROOT / "scripts" / "inject-lang-policy.py")


def test_contract_baseline_is_green():
    assert contract.main() == 0


def test_word_tier_source_has_one_value_per_label():
    tiers, heavy = contract.tier_declarations()
    assert tiers["轻量"] and {item[1] for item in tiers["轻量"]} == {(2000, 3000)}
    assert tiers["中段"] and {item[1] for item in tiers["中段"]} == {(3000, 5000)}
    assert heavy and {item[1] for item in heavy} == {5000}


def test_language_policy_is_single_canonical_line():
    assert lang.LINE.startswith("> 🌐 **语言政策**")
    assert "目标语言客观适用" in lang.LINE
    assert "默认不设" not in lang.LINE
    assert "不设默认" in lang.LINE


def test_language_inject_is_idempotent_and_normalizable():
    source = "# 标题\n\n正文\n"
    first, changed = lang.inject(source)
    assert changed and lang.MARKER in first
    second, changed_again = lang.inject(first)
    assert second == first and not changed_again
    old = first.replace(lang.LINE, "> 🌐 **语言政策**：旧变体")
    normalized = "\n".join(lang.LINE if lang.MARKER in line else line for line in old.split("\n"))
    assert lang.LINE in normalized and "旧变体" not in normalized


def test_contract_excludes_history_and_backups():
    paths = [rel for _, rel in contract.managed_markdown()]
    assert not any(".bak." in rel or "reports/" in rel or "archive/" in rel for rel in paths)
