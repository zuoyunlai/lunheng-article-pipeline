#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_pkg_integrity.py — 净化包正向完整性门测试（v2.12.30 新增）

背景（2026-09-12 第三方全量审计 P1-1）：
  净化链原本**只有负向检查**（违规模式命中数 = 0 即通过）→ 剥离规则过度匹配、把正文
  或结构误删时，残留扫描同样全绿 = fail-open（「净化成功、内容损坏」）。
  本组测试锁死正向门能拦住「多删」，也锁死它不会把合法形态误报（首跑即在
  「本来就无标题的片段文件」上误报，故标题判定必须是**基线相对**的）。
"""
import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "pkg-integrity.py"


def _load():
    spec = importlib.util.spec_from_file_location("pkg_integrity", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PI = _load()


def _mk_pkg(tmp_path, monkeypatch):
    """造一个最小包：带标题的正文 + 无标题片段 + 带 frontmatter 的 SKILL.md"""
    pkg = tmp_path / "pkg"
    (pkg / "references").mkdir(parents=True)
    (pkg / "SKILL.md").write_text(
        "---\nname: x\nmetadata:\n  openclaw:\n    version: 1.2.3\n---\n"
        "# 标题\n\n" + "正文内容。" * 60, encoding="utf-8")
    (pkg / "references" / "doc.md").write_text(
        "# 一\n\n" + "内容。" * 200 + "\n\n## 二\n\n" + "更多。" * 50, encoding="utf-8")
    # 片段文件：真源本来就没有标题（净化链实测存在，如 dispatch-header.md）
    (pkg / "references" / "fragment.md").write_text("没有标题的片段。" * 30, encoding="utf-8")
    monkeypatch.setattr(PI, "REQUIRED_ANCHORS", [
        ("SKILL.md", "version: 1.2.3"),
        ("references/doc.md", "## 二"),
    ])
    return pkg


def _snap(pkg, tmp_path):
    snap = tmp_path / "snap.json"
    assert PI.snapshot(str(pkg), str(snap)) == 0
    return snap


def test_verify_passes_when_intact(tmp_path, monkeypatch, capsys):
    pkg = _mk_pkg(tmp_path, monkeypatch)
    snap = _snap(pkg, tmp_path)
    assert PI.verify(str(pkg), str(snap)) == 0
    assert "正向完整性通过" in capsys.readouterr().out


def test_verify_fails_on_truncation(tmp_path, monkeypatch):
    """内容被误删成近乎空文件 → 必须拦住"""
    pkg = _mk_pkg(tmp_path, monkeypatch)
    snap = _snap(pkg, tmp_path)
    (pkg / "references" / "doc.md").write_text("残。", encoding="utf-8")
    assert PI.verify(str(pkg), str(snap)) == 1


def test_verify_fails_on_content_collapse(tmp_path, monkeypatch, capsys):
    """整段塌陷（保留率过低）→ 必须拦住并报保留率"""
    pkg = _mk_pkg(tmp_path, monkeypatch)
    snap = _snap(pkg, tmp_path)
    orig = (pkg / "references" / "doc.md").read_text(encoding="utf-8")
    (pkg / "references" / "doc.md").write_text(orig[: len(orig) // 10], encoding="utf-8")
    assert PI.verify(str(pkg), str(snap)) == 1
    assert "字符保留率" in capsys.readouterr().err


def test_verify_fails_when_file_disappears(tmp_path, monkeypatch):
    pkg = _mk_pkg(tmp_path, monkeypatch)
    snap = _snap(pkg, tmp_path)
    (pkg / "references" / "doc.md").unlink()
    assert PI.verify(str(pkg), str(snap)) == 1


def test_verify_fails_on_missing_anchor(tmp_path, monkeypatch, capsys):
    """必需结构锚点被剥走（关键段落误删）→ 必须拦住"""
    pkg = _mk_pkg(tmp_path, monkeypatch)
    snap = _snap(pkg, tmp_path)
    text = (pkg / "references" / "doc.md").read_text(encoding="utf-8")
    (pkg / "references" / "doc.md").write_text(text.replace("## 二", "二"), encoding="utf-8")
    assert PI.verify(str(pkg), str(snap)) == 1
    assert "必需锚点丢失" in capsys.readouterr().err


def test_verify_fails_on_empty_snapshot(tmp_path, monkeypatch, capsys):
    """空快照 = 门空转（无基线可比）→ 按失败处理，不得静默通过"""
    pkg = _mk_pkg(tmp_path, monkeypatch)
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps({"files": {}}), encoding="utf-8")
    assert PI.verify(str(pkg), str(snap)) == 1
    assert "空转" in capsys.readouterr().err


def test_verify_accepts_headingless_fragment(tmp_path, monkeypatch):
    """回归：基线本就无标题的片段文件不得被误报（首跑实测误报点）"""
    pkg = _mk_pkg(tmp_path, monkeypatch)
    snap = _snap(pkg, tmp_path)
    data = json.loads(snap.read_text(encoding="utf-8"))
    assert data["files"]["references/fragment.md"]["headings"] == 0
    assert PI.verify(str(pkg), str(snap)) == 0


def test_verify_fails_when_headings_all_stripped(tmp_path, monkeypatch, capsys):
    """基线有标题、净化后标题全没了 → 结构被剥空，必须拦住"""
    pkg = _mk_pkg(tmp_path, monkeypatch)
    # 先让 doc.md 只靠标题存活：正文足够长，避免同时触发退化判定
    body = "正文。" * 200
    (pkg / "references" / "doc.md").write_text("# 一\n\n" + body, encoding="utf-8")
    snap = _snap(pkg, tmp_path)
    (pkg / "references" / "doc.md").write_text(body + body, encoding="utf-8")
    assert PI.verify(str(pkg), str(snap)) == 1
    assert "标题" in capsys.readouterr().err


def test_verify_fails_on_flattened_frontmatter(tmp_path, monkeypatch, capsys):
    """frontmatter 层级被压平（教训 #335 同族）→ 必须拦住"""
    pkg = _mk_pkg(tmp_path, monkeypatch)
    snap = _snap(pkg, tmp_path)
    (pkg / "SKILL.md").write_text(
        "---\nname: x\nmetadata:\n  openclaw: {}\n---\n" + "正文。" * 80, encoding="utf-8")
    assert PI.verify(str(pkg), str(snap)) == 1
    assert "version" in capsys.readouterr().err


def test_cli_usage_error():
    r = subprocess.run([sys.executable, str(SCRIPT), "bogus"], capture_output=True, text=True)
    assert r.returncode == 2
