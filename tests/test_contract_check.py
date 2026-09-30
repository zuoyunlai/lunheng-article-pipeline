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


def test_word_tier_contract_catches_drift_reverse_injection():
    """P0-3 反向注入（验证收口 2026-09-30 修正：用三引号字符串避开 \n 转义坑）：
    写一个含错误档位的临时文件，验证 contract-check 必红线；
    同时验证存在正确 + 错误两个不同区间时仍能检出。"""
    import contextlib

    base = ROOT / 'references' / '_shared' / '真源'
    wrong_path = base / '_TEST_DRIFT_WRONG.md'
    both_path = base / '_TEST_DRIFT_BOTH.md'

    # 验证收口 2026-09-30：regex \d{4} 只能匹配 4 位数字；9999-10000 中 10000 是 5 位不匹配
    WRONG_TEXT = """# 漂移注入测试

> 轻量档 9000-9500 字（P0-3 反向注入；该文件由测试创建并清理）
"""
    BOTH_TEXT = """# 漂移注入测试（并存）

- 轻量档 2000-3000 字
- 轻量档 9000-9500 字（P0-3 反向注入；该文件由测试创建并清理）
"""
    try:
        # 第一次：单一错误 → 必须检出
        wrong_path.write_text(WRONG_TEXT, encoding='utf-8')
        both_path.write_text(WRONG_TEXT, encoding='utf-8')
        errors = contract.check_counts()
        assert any('word_tier_轻量' in e for e in errors),             f'expected word_tier_轻量 drift error, got: {errors}'

        # 清理：让基线恢复绿
        with contextlib.suppress(FileNotFoundError):
            wrong_path.unlink()
        with contextlib.suppress(FileNotFoundError):
            both_path.unlink()

        # 第二次：并存错误必须能被检出（即修复未退化为"第一个胜出"）
        wrong_path.write_text(BOTH_TEXT, encoding='utf-8')
        errors2 = contract.check_counts()
        assert any('word_tier_轻量' in e for e in errors2),             f'expected drift detection on coexisting correct+wrong, got: {errors2}'
    finally:
        with contextlib.suppress(FileNotFoundError):
            wrong_path.unlink()
        with contextlib.suppress(FileNotFoundError):
            both_path.unlink()


def test_word_tier_contract_passes_after_cleanup():
    """P0-3 修复后：基线文档不带错误档位时 contract.check_counts() 应通过。"""
    # 若上一个测试未清理（例如异常退出），这里再保底清一次
    for p in (ROOT / 'references' / '_shared' / '真源').glob('_TEST_DRIFT_*.md'):
        p.unlink(missing_ok=True)
    errors = contract.check_counts()
    assert not errors, f'baseline drift after P0-3 cleanup: {errors}'


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
