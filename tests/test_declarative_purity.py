#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_declarative_purity.py — 「交付物纯度」反向不变式（v2.14.1，审计 R-43 / R-48）

背景（实测取证，2026-09-27）：
  净化包的「交付物纯度」此前只靠人 grep + 构建脚本 FINAL_PATTERNS 白名单。
  后者是黑名单式的——每新增一类维护者话术都要记得加 token，于是 2.14.0 包内
  实测残留：flow-check 27 处 / 构建期红 12 处 / pytest 3 处 / self-audit 1 处。
  用户读到的是「flow-check 规则 24 会拦你」这种自己无法观察、无法运行的机制 ——
  等于交付物用维护者的方言写成。

本文件把纯度从「靠人 grep」升级为「机器门」，锁死三层：
  ① 兜底不可被删除：FINAL_PATTERNS 必须含 4 类维护者 QA 话术 token（棘轮下限）；
  ② 中性化不可静默失效：strip-internal-leakage.sh 必须同时有 md 通道与
     非 md 通道（2.14.0 实测 14 处 flow-check / 4 处构建期红全在 .yaml，
     只做 md 通道会漏）；
  ③ 净化产物必须干净：若当前版本已有构建产物，逐 token 断言 0 命中。

另含反向对照（教训 #334：门类改动必须配「应当检出」的正向样本）：
  test_detector_detects_injected_dialect 在临时副本注入一行维护者话术，
  断言判据确实会红——防「门写了却恒绿」的空转。
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
BUILD_SH = REPO / "scripts" / "build-clawhub-release.sh"
STRIP_SH = REPO / "scripts" / "strip-internal-leakage.sh"
SKILL_MD = REPO / "SKILL.md"
PKG_ROOT = pathlib.Path.home() / "lunheng-build" / "lunheng-outputs" / "clawhub-release"

Q = chr(39)
NL = chr(10)

# 交付物内必须为 0 的维护者 QA 话术（与 build-clawhub-release.sh 的 v2.14.1 组同源）
MAINTAINER_TOKENS = ["flow-check", "构建期红", "self-audit", "pytest"]

# 使用者侧可读的核心机制名——不得入 FINAL_PATTERNS（审计 R-43 逐条核对结论）。
# 门 M 等由交付物正文（M-Gate-Algorithm.md）自解释，是面向使用者的机制，非维护者方言。
USER_FACING_ALLOWED = ["门 M", "门 C", "门 S", "门 T", "门 U", "门 V"]
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".txt", ".toml"}


def _array_body(name, text):
    marker = name + "=("
    assert marker in text, name + " 未在构建脚本中找到"
    body = text.split(marker, 1)[1]
    return body.split(NL + ")", 1)[0]


def _final_patterns():
    body = _array_body("FINAL_PATTERNS", BUILD_SH.read_text(encoding="utf-8"))
    out = []
    for line in body.splitlines():
        s = line.strip()
        if not s.startswith(Q):
            continue
        end = s.find(Q, 1)
        if end > 0:
            out.append(s[1:end])
    return out


def _rule_checks():
    body = _array_body("RULE_CHECKS", BUILD_SH.read_text(encoding="utf-8"))
    rows = []
    for line in body.splitlines():
        s = line.strip()
        if not s.startswith(Q):
            continue
        parts = s.strip(Q).split("|")
        if len(parts) == 4 and parts[2] in ("critical", "warn") and parts[3] in ("yes", "no"):
            rows.append(tuple(parts))
    return rows


def _scan(root):
    hits = []
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.suffix not in TEXT_SUFFIXES:
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for tok in MAINTAINER_TOKENS:
            if tok in text:
                hits.append(f.name + "::" + tok)
    return hits


# ---------------------------------------------------------------------------
# ① 兜底不可被删除（棘轮下限）
# ---------------------------------------------------------------------------

def test_final_patterns_cover_maintainer_dialect():
    pats = _final_patterns()
    for tok in MAINTAINER_TOKENS:
        assert tok in pats, (
            "FINAL_PATTERNS 缺少维护者话术 token " + tok + " —— 2.14.0 实测该话术曾逸出出厂；"
            "删除本 token 等于把 fail-loud 兜底改回黑名单式人肉 grep（审计 R-43/R-48）"
        )
    assert len(pats) >= 36, "FINAL_PATTERNS 条目数 " + str(len(pats)) + " < 2.14.0 基线 36（规则被删）"


def test_final_patterns_do_not_ban_user_facing_gate_names():
    """门 M / 门 C 等是使用者可读的核心机制名，不得入兜底清单。

    审计方案曾提议加 门 [A-Z]——实测包内命中 41 处，绝大多数是 M-Gate-Algorithm.md
    等交付物正文自解释的合法机制名；一刀切会破坏交付物语义（审计 R-43 逐条核对结论）。
    """
    pats = _final_patterns()
    for bad in ["门 [A-Z]", "门 M", "门 C", "门 S"]:
        assert bad not in pats, (
            "FINAL_PATTERNS 不得含 " + bad + "：" + str(USER_FACING_ALLOWED) +
            " 属使用者侧可读机制名，会误伤交付物正文（审计 R-43 逐条核对结论）"
        )


# ---------------------------------------------------------------------------
# ② 中性化通道不可静默失效
# ---------------------------------------------------------------------------

def test_strip_script_has_maintainer_dialect_neutralization():
    s = STRIP_SH.read_text(encoding="utf-8")
    assert "阶段 6b" in s, "strip 脚本缺少阶段 6b（维护者 QA 话术中性化）"
    for repl in ["维护者机制", "维护者校验", "构建期校验不通过", "自检门", "维护者测试"]:
        assert repl in s, "阶段 6b 缺少替换目标 " + repl
    for tok in ["flow-check", "构建期红", "self-audit", "pytest"]:
        assert (Q + tok + Q) in s, "阶段 6b 未覆盖 " + tok


def test_strip_script_covers_non_md_text_assets():
    """2.14.0 实测：包内 flow-check 14 处 / 构建期红 4 处全部在 .yaml。

    只做 md 通道会让 yaml 里的规则编号话术原样出厂。
    """
    s = STRIP_SH.read_text(encoding="utf-8")
    assert "non-md text assets" in s, "strip 脚本缺少非 md 文本资产通道（yaml/json/txt 会漏）"
    assert ".yaml" in s and ".yml" in s, "非 md 通道未覆盖 .yaml/.yml"


def test_rule_checks_registers_purity_rules():
    rows = _rule_checks()
    names = set(r[0] for r in rows)
    for want in ["flow-check话术", "构建期红话术", "self-audit话术", "pytest话术"]:
        assert want in names, "RULE_CHECKS 缺少 " + want + "（中性化无产物侧回归守卫）"
    for want in ["flow-check话术", "构建期红话术"]:
        row = [r for r in rows if r[0] == want][0]
        assert row[3] == "no", want + " 的 allow_empty 应为 no（防中性命中退化）"
    assert len(rows) >= 40, "RULE_CHECKS 合规条目 " + str(len(rows)) + " < 2.14.1 基线 40"


# ---------------------------------------------------------------------------
# ③ 净化产物必须干净（有产物时才跑）
# ---------------------------------------------------------------------------

def _current_package():
    ver = None
    for line in SKILL_MD.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("version:"):
            ver = stripped.split(":", 1)[1].strip().strip(chr(34))
            break
    if not ver:
        return None
    pkg = PKG_ROOT / ver
    return pkg if pkg.is_dir() else None


def test_shipped_package_is_free_of_maintainer_dialect():
    pkg = _current_package()
    if pkg is None:
        pytest.skip("当前版本无构建产物（先跑 scripts/build-clawhub-release.sh <ver>）")
    offenders = _scan(pkg)
    assert not offenders, (
        "净化包仍含维护者 QA 话术（交付物用维护者方言写成）：" + NL + "  " + (NL + "  ").join(offenders[:20])
    )


# ---------------------------------------------------------------------------
# ④ 反向对照：判据必须会红（教训 #334）
# ---------------------------------------------------------------------------

def test_detector_detects_injected_dialect():
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        (root / "clean.md").write_text("本事实由维护者机制机械校验。", encoding="utf-8")
        assert _scan(root) == [], "干净样本被误判为残留（判据过宽）"
        (root / "leak.md").write_text("缺关键段 = 构建期红：flow-check 规则 99。", encoding="utf-8")
        hits = _scan(root)
        assert "leak.md::flow-check" in hits, "注入 flow-check 未被检出（判据空转）"
        assert "leak.md::构建期红" in hits, "注入构建期红未被检出（判据空转）"


def test_neutralizer_semantics_are_substitutions():
    """中性化必须是语义化替换，不是「删字后留残骸」。"""
    s = STRIP_SH.read_text(encoding="utf-8")
    assert "line = re.sub(" in s, "规则编号中性化正则缺失"
    assert "line.replace(" + Q + "构建期红" + Q + ", " + Q + "构建期校验不通过" + Q + ")" in s
    assert "line.replace(" + Q + "self-audit" + Q + ", " + Q + "自检门" + Q + ")" in s
    assert "line.replace(" + Q + "pytest" + Q + ", " + Q + "维护者测试" + Q + ")" in s
