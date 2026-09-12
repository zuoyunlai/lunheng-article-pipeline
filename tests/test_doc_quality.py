#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_doc_quality.py — 文档质量门测试（v2.12.30 新增，回应第三方审计 P2）

背景（2026-09-12 第三方全量审计，第三批 P2 文档质量）：
  - P2-1：CHANGELOG 10 处结构性断链（../outputs/* 指向 .gitignore 目录、docs/* 不存在、
          裸相对名不存在）——无机械门，只有人工点开才暴露。
  - P2-2：SKILL.md 12,440 字符，超官方 skill-workshop 提案上限（10,000）
          （docs/tools/skill-workshop.md）24%。
  - P2-3：跨文件重复规则。**关键更正**：其中一部分是**有意的漂移锚点** ——
          tests/test_rules_consistency.py 刻意以 SKILL.md 作为 T9 6 维度/4 档 + G14 8 类
          的第三处锚点（防「改 A 漏 B」）。故「重复」不等于缺陷，不得一概删除。

本测试锁死：断链为 0 / SKILL.md 体量不回涨 / 新门位置正确（计分在全部门之后）。
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent.parent
SKILL = ROOT / "SKILL.md"
CHANGELOG = ROOT / "CHANGELOG.md"
GATE = ROOT / "scripts" / "self-audit-gate.sh"
LINK_CHECK = ROOT / "scripts" / "link-check.py"

SKILL_CHARS_CEIL = 11370


# ---------------- P2-1：相对链接可解析 ----------------

def test_no_broken_relative_links():
    r = subprocess.run([sys.executable, str(LINK_CHECK)], capture_output=True, text=True,
                       cwd=str(ROOT))
    assert r.returncode == 0, f"存在断链：\n{r.stdout}\n{r.stderr}"


def test_changelog_has_no_structural_dead_links():
    """反向断言：指向 .gitignore 产物目录 / 不存在目录的链接必须为 0"""
    text = CHANGELOG.read_text(encoding="utf-8")
    bad = re.findall(r'\]\(\.\./outputs/[^)]*\)', text)
    assert not bad, f"CHANGELOG 仍有 ../outputs/ 断链（outputs/ 在 .gitignore）：{bad}"
    bad_docs = re.findall(r'\]\(docs/[^)]*\)', text)
    assert not bad_docs, f"CHANGELOG 仍有 docs/ 断链（仓库无该目录）：{bad_docs}"


# ---------------- P2-2：SKILL.md 体量棘轮 ----------------

def test_skill_md_size_ratchet():
    chars = len(SKILL.read_text(encoding="utf-8"))
    assert chars <= SKILL_CHARS_CEIL, (
        f"SKILL.md {chars} 字符 > 棘轮上限 {SKILL_CHARS_CEIL}"
        f"（官方上限 10000）—— 请外移长内容，勿放宽上限")


def test_skill_md_ratchet_ceiling_matches_gate():
    """门里的上限必须与本测试一致（双份数字必然漂移 —— 教训 #343 同型）"""
    src = GATE.read_text(encoding="utf-8")
    m = re.search(r'SKILL_CHARS_CEIL=(\d+)', src)
    assert m, "自审门缺 SKILL_CHARS_CEIL"
    assert int(m.group(1)) == SKILL_CHARS_CEIL, \
        f"门上限 {m.group(1)} ≠ 测试上限 {SKILL_CHARS_CEIL}"


def test_skill_md_still_has_anchored_enumerations():
    """体量瘦身不得破坏「漂移锚点」内容（否则 test_rules_consistency 会红）"""
    text = SKILL.read_text(encoding="utf-8")
    for token in ("学术模板语", "党报话语堆砌", "引文规范", "26-30", "<16"):
        assert token in text, f"SKILL.md 瘦身误删锚点内容：{token}"


# ---------------- 门位置（教训 #342：计分必须在全部门之后）----------------

def test_new_gates_run_before_scoring():
    src = GATE.read_text(encoding="utf-8")
    scoring_at = src.index("TOTAL_PASS=${#PASSED[@]}")
    gate_u_at = src.index("门 U: 相对链接可解析性")
    gate_v_at = src.index("门 V: SKILL.md 体量棘轮")
    assert gate_u_at < scoring_at, "门 U 必须在计分之前"
    assert gate_v_at < scoring_at, "门 V 必须在计分之前"


def test_link_check_ignores_code_spans():
    """回归：CHANGELOG 历史修订说明里的 `](project-archive-sop.md)` 是行内代码，不得误报"""
    sys.path.insert(0, str(ROOT / "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("link_check", LINK_CHECK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "](x.md)" not in mod.strip_code("说明：`](x.md)` 应修正")
    assert "](x.md)" in mod.strip_code("真链接 [t](x.md)")


# ---------------- v2.12.31：入口文档裸文件引用（ClawHub SkillSpector AE1 HIGH）----------------

def _load_link_check():
    import importlib.util
    spec = importlib.util.spec_from_file_location("link_check_bare", LINK_CHECK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bare_entry_refs_of_skill_md_all_resolve():
    """真实入口文档：独立文件提及必须全部能按仓库根解析（AE1 防复发）"""
    bad, checked = _load_link_check().check_bare_entry_refs(str(SKILL))
    assert not bad, f"SKILL.md 仍有不可解析的裸文件引用：{bad}"
    assert checked > 0, "裸引用检查未生效（检查条数为 0 = 假绿灯）"


def test_bare_ref_check_catches_dangling(tmp_path):
    """反向：裸文件名（本仓 references/ 下确实不存在）必须被拦"""
    (tmp_path / "references").mkdir()
    (tmp_path / "references" / "ok.md").write_text("x", encoding="utf-8")
    entry = tmp_path / "SKILL.md"
    entry.write_text("真源 = `references/ok.md`；错源 = `missing-doc.md`。", encoding="utf-8")
    bad, _ = _load_link_check().check_bare_entry_refs(str(entry))
    assert [t for _, t in bad] == ["missing-doc.md"], f"漏报裸名：{bad}"


def test_bare_ref_check_does_not_resolve_via_subdirs(tmp_path):
    """口径锁死：**不试** references/ 等子目录 —— 否则 AE1 那类「裸名但能找回」永不报"""
    (tmp_path / "references").mkdir()
    (tmp_path / "references" / "only-in-refs.md").write_text("x", encoding="utf-8")
    entry = tmp_path / "SKILL.md"
    entry.write_text("见 `only-in-refs.md`。", encoding="utf-8")
    bad, _ = _load_link_check().check_bare_entry_refs(str(entry))
    assert [t for _, t in bad] == ["only-in-refs.md"]


def test_bare_ref_check_excludes_link_text_and_exemptions(tmp_path):
    """链接文本（含带后缀词写法）/ 占位符 / docs 前缀 / 运行时清单项均不报"""
    entry = tmp_path / "SKILL.md"
    entry.write_text(
        "[`external-services.md` 逐类表](references/_shared/external-services.md) "
        "`docs/tools/subagents.md` `.tmp/<角色>-heartbeat.md` `status.md` `01-任务简报.md`\n",
        encoding="utf-8")
    bad, checked = _load_link_check().check_bare_entry_refs(str(entry))
    assert not bad, f"误报：{bad}"
    assert checked == 0, f"豁免项被计入检查：{checked}"


def test_gate_u_message_reports_bare_refs():
    """门 U 输出必须能反映第二类结果（否则门过了但检查没跑 = 假绿灯）"""
    r = subprocess.run([sys.executable, str(LINK_CHECK)], capture_output=True, text=True,
                       cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    assert "裸引用" in r.stdout, f"门 U 输出未含裸引用结论：{r.stdout}"
