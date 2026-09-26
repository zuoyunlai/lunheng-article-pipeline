#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""计数漂移机械门（2026-09-25 审计修订 R-19）。

背景：整族计数散落全仓（「G14 9 类」、「13 类常见错误」、「24 中文 + 12 英文」、
「dispatch 11 文件」……），此前靠**人记住 N 个地方**同步 —— 2026-09-25 审计实测已出现
整族漂移：同为错误类数出现 12 与 13 两种写法；期刊总数出现 37 与 36 两种写法。

口径：把「人工同源」升级为「机器同源」。唯一计数真源 =
`references/_shared/真源/counts.yaml`；任何与它冲突的数字即 FAIL。

白名单（不扫）：CHANGELOG*（历史沿革必须保留旧数字）、references/_shared/archive/（归档）、
reports/（工程过程产物）。
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
COUNTS_REL = "references/_shared/真源/counts.yaml"
# 历史沿革类文件必须豁免（旧数字是史实，不得被机械门要求改写）：
#   CHANGELOG* / archive/ / reports/（工程过程产物）/ 教训索引（历史教训台账）
WHITELIST_MARKERS = ("CHANGELOG", "/archive/", "reports/", "教训索引.md")


def load_counts(root: pathlib.Path = ROOT) -> dict:
    return yaml.safe_load((root / COUNTS_REL).read_text(encoding="utf-8"))


def md_files(root: pathlib.Path):
    for p in sorted(root.rglob("*.md")):
        rel = p.relative_to(root).as_posix()
        if any(m in rel for m in WHITELIST_MARKERS):
            continue
        if ".git" in p.parts or "node_modules" in p.parts:
            continue
        yield rel, p


def check_line(line: str, counts: dict):
    """单行计数一致性检查 → 冲突说明列表（空 = 一致）。"""
    msgs = []

    def neq(found, expected, what):
        if str(found) != str(expected):
            msgs.append(f"{what}: 文中 {found} ≠ counts.yaml {expected}")

    for m in re.finditer(r"(\d+)\s*类常见错误", line):
        neq(m.group(1), counts["errors"], "错误类数")

    for m in re.finditer(r"(\d+)\s*中文\s*\+\s*(\d+)\s*英文", line):
        neq(m.group(1), counts["journals"]["zh"], "期刊中文数")
        neq(m.group(2), counts["journals"]["en"], "期刊英文数")
        total = re.search(r"=\s*(\d+)\s*个", line)
        if total:
            neq(total.group(1), counts["journals"]["total"], "期刊总数")

    # 只在「G14」邻近窗口内取类数（早期实现扫全行所有「N 类」，把同行的
    # 「2 类问题」之类无关数字也算进来 ⇒ 大量误报）
    for m in re.finditer(r"G14[^\n]{0,40}?(\d+)\s*类", line):
        neq(m.group(1), counts["g14_classes"], "G14 类数")
    for m in re.finditer(r"(\d+)\s*类判定", line):
        neq(m.group(1), counts["g14_classes"], "G14 类判定数")

    if "dispatch" in line.lower():
        for m in re.finditer(r"(\d+)\s*(?:个)?文件", line):
            neq(m.group(1), counts["dispatch_files"], "dispatch 文件数")

    for m in re.finditer(r"(\d+)\s*Form\s*\+\s*(\d+)\s*Exist\s*\+\s*(\d+)\s*Integrity", line):
        neq(m.group(1), counts["m_gate_items"]["form"], "M-Form 项数")
        neq(m.group(2), counts["m_gate_items"]["exist"], "M-Exist 项数")
        neq(m.group(3), counts["m_gate_items"]["integrity"], "M-Integrity 项数")

    if "T9" in line:
        for m in re.finditer(r"(?<![A-Za-z0-9])(\d+)\s*维度", line):
            neq(m.group(1), counts["t9_dimensions"], "T9 维度数")

    if "T8" in line:
        for m in re.finditer(r"(\d+)\s*项（(\d+)\s*维度）", line):
            neq(m.group(1), counts["t8_items"], "T8 项数")
            neq(m.group(2), counts["t8_publishable_dimensions"], "T8 维度数")

    return msgs


# 版本历史类小节标题（进入后不再扫计数：小节里的旧数字是史实。
#   实测例：G14 类数 8 → 9 的演进记录住在 gates/14-中文AI痕迹-gate.md §七 版本历史）
HISTORY_HEADING = re.compile(r"^#{1,6}\s*.*(版本历史|变更历史|历史沿革|修订历史)")


def collect_drift(root: pathlib.Path = ROOT):
    counts = load_counts(root)
    drift = []
    for rel, path in md_files(root):
        in_history = False
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("#"):
                in_history = bool(HISTORY_HEADING.match(line))
                continue
            if in_history:
                continue
            for msg in check_line(line, counts):
                drift.append(f"{rel}:{i} → {msg}")
    return drift


# ---------------------------------------------------------------- 正向

def test_counts_file_parses():
    c = load_counts()
    for key in ("g14_classes", "errors", "journals", "dispatch_files", "t8_items",
                "t9_dimensions", "m_gate_items", "role_cards", "role_card_files"):
        assert key in c, f"counts.yaml 缺键：{key}"
    assert c["m_gate_items"]["total"] == (
        c["m_gate_items"]["form"] + c["m_gate_items"]["exist"] + c["m_gate_items"]["integrity"]
    ), "M 门总数 ≠ 分组之和（自发自证基线破坏）"
    assert c["journals"]["total"] == c["journals"]["zh"] + c["journals"]["en"], "期刊总数 ≠ 中文 + 英文"


def test_counts_match_repo_reality():
    """真源数字必须与仓库实物一致（防「真源自己写错」）。"""
    c = load_counts()
    assert len(list((ROOT / "references" / "dispatch").glob("*.md"))) == c["dispatch_files"]
    assert len(list((ROOT / "references" / "agents").glob("*.md"))) == c["role_card_files"]


def test_no_count_drift_in_repo():
    drift = collect_drift()
    assert not drift, "计数与 counts.yaml 不一致（改数只改 counts.yaml，再同步下列位置）：\n" + "\n".join(drift)


# ---------------------------------------------------------------- 反向注入

def _mini_tree(tmp: pathlib.Path, body: str, name: str = "doc.md"):
    (tmp / "references" / "_shared" / "真源").mkdir(parents=True, exist_ok=True)
    (tmp / COUNTS_REL).write_text((ROOT / COUNTS_REL).read_text(encoding="utf-8"), encoding="utf-8")
    (tmp / name).write_text(body, encoding="utf-8")
    return tmp


def test_checker_catches_wrong_error_count(tmp_path):
    root = _mini_tree(tmp_path, "错误信息友好化（12 类常见错误）。\n")
    drift = collect_drift(root)
    assert drift and "错误类数" in drift[0], f"漏报错误类数漂移：{drift}"


def test_checker_catches_wrong_journal_total(tmp_path):
    root = _mini_tree(tmp_path, "期刊数量：24 中文 + 12 英文 = 37 个\n")
    drift = collect_drift(root)
    assert drift and "期刊总数" in " ".join(drift), f"漏报期刊总数漂移：{drift}"


def test_checker_catches_wrong_g14_class_count(tmp_path):
    root = _mini_tree(tmp_path, "G14 中文 AI 痕迹闸：8 类判定\n")
    drift = collect_drift(root)
    assert drift and "G14" in " ".join(drift), f"漏报 G14 类数漂移：{drift}"


def test_checker_catches_wrong_m_gate_items(tmp_path):
    root = _mini_tree(tmp_path, "M 门 = 6 Form + 4 Exist + 2 Integrity = 12 项\n")
    drift = collect_drift(root)
    assert len(drift) >= 2, f"漏报 M 门项数漂移：{drift}"


def test_checker_catches_wrong_dispatch_count(tmp_path):
    root = _mini_tree(tmp_path, "dispatch 派发话术共 10 个文件。\n")
    drift = collect_drift(root)
    assert drift and "dispatch" in " ".join(drift), f"漏报 dispatch 文件数漂移：{drift}"


def test_whitelist_exempts_changelog_and_archive(tmp_path):
    """历史沿革与归档必须豁免（旧数字是史实，不得被机械门要求改写）。"""
    (tmp_path / "references" / "_shared" / "archive").mkdir(parents=True)
    (tmp_path / "references" / "_shared" / "真源").mkdir(parents=True)
    (tmp_path / COUNTS_REL).write_text((ROOT / COUNTS_REL).read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text("历史：错误类数 12 类常见错误\n", encoding="utf-8")
    (tmp_path / "references" / "_shared" / "archive" / "old.md").write_text(
        "旧版：24 中文 + 12 英文 = 37 个\n", encoding="utf-8")
    assert collect_drift(tmp_path) == []


def test_history_section_is_exempt(tmp_path):
    """版本历史小节里的旧数字是史实（如 G14 类数 8 → 9），不得被要求改写。"""
    body = "# 门\n## 七、版本历史\n\n- v2.4.0：8 类检测维度\n- v2.4.0：G14 8 类\n"
    root = _mini_tree(tmp_path, body)
    assert collect_drift(root) == []


def test_drift_after_history_section_is_still_caught(tmp_path):
    """反向：历史小节**之后**回到正文，计数漂移必须继续被抓。"""
    body = "# 门\n## 七、版本历史\n- v2.4.0：8 类\n\n## 八、现行口径\n- G14 8 类判定\n"
    root = _mini_tree(tmp_path, body)
    drift = collect_drift(root)
    assert drift and "八、现行口径" not in " ".join(drift), f"历史小节豁免越界：{drift}"
    assert any(":6" in d or ":7" in d for d in drift), f"未抓到历史小节后的漂移：{drift}"


def test_correct_line_passes(tmp_path):
    root = _mini_tree(tmp_path, "错误信息友好化（13 类常见错误）。\n期刊：24 中文 + 12 英文 = 36 个\n")
    assert collect_drift(root) == []
