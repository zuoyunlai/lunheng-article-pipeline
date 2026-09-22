#!/usr/bin/env python3
"""flow-schema 通用引擎回归：正向实例 + 负例注入 + 重复键 fail-closed。"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "scripts" / "flow-schema.py"


def _load():
    spec = importlib.util.spec_from_file_location("flow_schema", ENGINE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_lunheng_schema_passes_current_tree(capsys):
    mod = _load()
    assert mod.main(["--root", str(ROOT), "--schema", "scripts/flow-schema.lunheng.yaml"]) == 0
    assert capsys.readouterr().out == "\n"


def test_missing_token_is_reported_fail_closed(tmp_path, capsys):
    mod = _load()
    (tmp_path / "carrier.md").write_text("保留内容", encoding="utf-8")
    (tmp_path / "schema.yaml").write_text(
        "version: 1\ncarriers:\n  one: carrier.md\nassertions:\n"
        "  - id: required-token\n    kind: tokens_exist\n    carriers: [one]\n    tokens: [缺失协议]\n",
        encoding="utf-8",
    )
    assert mod.main(["--root", str(tmp_path), "--schema", "schema.yaml"]) == 2
    assert "required-token" in capsys.readouterr().out


def test_duplicate_schema_key_fails_closed(tmp_path, capsys):
    mod = _load()
    (tmp_path / "schema.yaml").write_text(
        "version: 1\ncarriers: {}\ncarriers: {}\nassertions: []\n", encoding="utf-8"
    )
    assert mod.main(["--root", str(tmp_path), "--schema", "schema.yaml"]) == 1
    assert "duplicate key" in capsys.readouterr().out
