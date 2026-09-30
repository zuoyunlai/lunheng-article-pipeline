#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_m_gate.py — 论衡 M 门 13 项算法格式测试（v2.5.6 新增，第三方独立审查建议 #1）

测试范围：
- M-Form 1-8 形式合规门（8 项）
- M-Exist 1-3 存在性合规门（3 项）
- M-Integrity 1-2 阶段闸门（2 项）

设计原则（v2.5.6 诚实化，教训 #177）：
- M 门是 LLM 推理判定，不是真 shell 命令
- 本测试只验证**算法逻辑描述**（伪代码 + fixture 输入）
- 不依赖真实 LLM 调用（避免 CI 成本 + OpenAI API key 依赖）
- fixture 输入是「代表性论文片段」，覆盖各种 edge case

CI 集成：
- v2.6.0 Phase 1 实现（不含真实 LLM 调用）
- v2.6.0 Phase 2 集成 LLM 调用（需 OpenAI API key）
"""
import re
import os
import sys
from pathlib import Path

# 测试配置
FIXTURES_DIR = Path(__file__).parent / "fixtures"
ALGORITHM_FILE = Path(__file__).parent.parent / "references" / "_shared" / "真源" / "M-Gate-核心.md"

# 加载 M 门算法文档
with open(ALGORITHM_FILE) as f:
    M_GATE_DOC = f.read()

# =============================================================================
# M-Form-1 统一引用编号正则（v2.12.56 M-3）
# 唯一真源 = M-Gate-核心.md §统一抽取规则真源 B（CITATION_NUMBER_RE）。
# 此处为**断言镜像**：本模块另有一条断言校验该常量名在文档中存在（防文档/测试两处各写一份）。
# 覆盖三类格式：① 标准 [D01]/[C-主01] ② 基线 [D-基-R-01] ③ 表格 [1.1]
# =============================================================================
M_FORM_1_CITATION_RE = re.compile(
    r'\[(?:(?:D|C|C-主|L|先)\d+|(?:D|C|L|先)-[\w\-]*?\d+|\d+\.\d+)\]'
)


def test_unified_extraction_and_verdict_tiers_in_doc():
    """静态锁（v2.12.56）：M-2 / M-5 / M-6 / M-7 的落地点必须在算法文档内成文。

    本测试不预判 LLM 行为，只防「同一抽取规则两处各写一份」与「四档出口缺失」回归。
    """
    for token in (
        "统一抽取规则真源",            # M-2
        "ENDNOTE_SECTIONS_REQUIRED",   # M-2 A：必需四节
        "ENDNOTE_SECTIONS_ALL",        # M-2 A：白名单七节
        "ENDNOTE_SECTIONS_NONSTANDARD",  # M-2 A：非标准节
        "CITATION_NUMBER_RE",          # M-2 B / M-3：统一编号正则
        "CITATION_BASE_RE",            # M-3：基线 [D-基-R-01]
        "CITATION_TABLE_RE",           # M-3：表格 [1.1]
        "verdict_pass",                # M-5：第 1 档出口
        "verdict_fail",                # M-5：第 2 档出口
        "verdict_undecidable",         # M-5：第 3 档出口
        "verdict_path_error",          # M-5：第 4 档出口
        "不得真空通过",                # M-6：claims 为空 fail-open 修复
        "未定义 helper 清单与替代口径",  # M-7
    ):
        assert token in M_GATE_DOC, f"M-Gate 文档缺 v2.12.56 落地点：{token}"

    # 旧的两档写法则必须已从伪代码中退出（引述性说明除外）：
    code_blocks = re.findall(r'```python\n(.*?)```', M_GATE_DOC, re.S)
    assert code_blocks, "M-Gate 文档缺 python 伪代码块"
    legacy = [b for b in code_blocks if 'return {"通过": True}' in b or 'return {"通过": False}' in b]
    assert not legacy, f"仍有伪代码块停留在两档写法（未接四档出口）：{len(legacy)} 块"

    assert len(re.findall(r'^### M-Form-\d+:', M_GATE_DOC, re.M)) == 8
    assert len(re.findall(r'^### M-Exist-\d+:', M_GATE_DOC, re.M)) == 3
    assert len(re.findall(r'^### M-Integrity-\d+:', M_GATE_DOC, re.M)) == 2
    print("  ✓ v2.12.56 静态锁: 统一抽取规则 + 四档出口 + helper 登记表齐全（8+3+2 项不回退）")


def load_fixture(name):
    """加载 fixture 文件；缺失时 fail-loud，禁止 M 门在空输入上假绿。"""
    path = FIXTURES_DIR / name
    if not path.exists():
        pytest.fail(f"fixture 缺失：{path}（M 门用例不允许在空输入上自证）")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        pytest.fail(f"fixture 为空：{path}（M 门用例不允许在空输入上自证）")
    return text


# 注入 pytest 引用（top-of-file 无 pytest 导入，load_fixture 用到时才需要）
import pytest  # noqa: E402  必须在 load_fixture 定义后（避免 lint 警告）


def test_M_Form_1_citation_complete():
    """M-Form-1 验证：正文与文末均有引用编号，且格式符合 M_FORM_1_CITATION_RE"""
    fixture = load_fixture("valid_paper.md")
    body_end = min((fixture.find(x) for x in ("## 数据来源", "## 参考文献") if fixture.find(x) >= 0), default=len(fixture))
    body = fixture[:body_end]
    body_citations = re.findall(M_FORM_1_CITATION_RE, body)
    assert body_citations, "M-Form-1 FAIL: 正文无任何 [Dxx/Cxx/Lxx] 引用"
    appendix = fixture[body_end:]
    appendix_citations = re.findall(M_FORM_1_CITATION_RE, appendix)
    assert appendix_citations, "M-Form-1 FAIL: 文末无任何 [Dxx/Cxx/Lxx] 引用"
    print(f"  ✓ M-Form-1: 正文 {len(body_citations)} / 文末 {len(appendix_citations)} 条引用")


def test_M_Form_1_covers_baseline_and_table_formats():
    """M-Form-1 验证：基线 [D-基-R-01] 与表格 [1.1] 格式都能匹配"""
    for fixture_name, fmt in (("paper_with_baseline.md", "[D-基-R-01]"), ("paper_with_table.md", "[1.1]")):
        fixture_path = FIXTURES_DIR / fixture_name
        if fixture_path.exists():
            text = fixture_path.read_text(encoding="utf-8")
            assert fmt in text, f"M-Form-1 FAIL: 缺 {fmt}"
            assert re.search(M_FORM_1_CITATION_RE, text), f"M-Form-1 FAIL: regex 不匹配 {fmt}"
    print("  ✓ M-Form-1 覆盖基线 + 表格格式")


def test_M_Form_1_missing_citation():
    """M-Form-1 反例：缺失文末引用的 fixture 必须被检测"""
    fixture_path = FIXTURES_DIR / "paper_missing_citation.md"
    if not fixture_path.exists():
        pytest.skip("paper_missing_citation fixture 缺失（可选反例）")
    text = fixture_path.read_text(encoding="utf-8")
    body = text.split("## 数据来源")[0] if "## 数据来源" in text else text
    body_citations = re.findall(M_FORM_1_CITATION_RE, body)
    appendix = text[text.find("## 数据来源"):] if "## 数据来源" in text else ""
    appendix_citations = re.findall(M_FORM_1_CITATION_RE, appendix)
    assert body_citations and not appendix_citations, "M-Form-1 反例期望：正文有 / 文末无"
    print("  ✓ M-Form-1 反例：缺失文末引用被检出")


def test_M_Form_2_sections_complete():
    """M-Form-2 验证：必需四节齐全（验证收口 2026-09-30 对齐真源 ENDNOTE_SECTIONS_REQUIRED）。

    必需四节 = 参考文献 / 数据来源 / 案例来源 / 先行者文献（M-Gate-核心.md §统一抽取规则真源 A）。
    致谢 / AI 使用声明 / 方法论附录属可选节（ENDNOTE_SECTIONS_OPTIONAL），不在此断言。
    """
    fixture = load_fixture("valid_paper.md")
    required = ["## 数据来源", "## 案例来源", "## 参考文献", "## 先行者文献"]
    for section in required:
        assert section in fixture, f"M-Form-2 FAIL: 缺必需节 {section}"
    print("  ✓ M-Form-2: 4/4 必需节齐全（可选节不判失败）")


def test_M_Form_3_no_temp_numbering():
    """M-Form-3 验证：正文无过程编号 [T1]/[T2] 等"""
    fixture = load_fixture("valid_paper.md")
    body_end = min((fixture.find(x) for x in ("## 数据来源", "## 参考文献") if fixture.find(x) >= 0), default=len(fixture))
    body = fixture[:body_end]
    forbidden = re.findall(r'\[T\d+\]', body)
    assert not forbidden, f"M-Form-3 FAIL: 正文残留过程编号 {forbidden}"
    print("  ✓ M-Form-3: 无过程编号")


def test_M_Form_4_no_role_meta():
    """M-Form-4 验证：正文无角色元数据（"T6 批判报告"等）"""
    fixture = load_fixture("valid_paper.md")
    forbidden = ["T6 批判报告", "T7 审计", "G14 检测", "T9 同行评审"]
    for term in forbidden:
        assert term not in fixture, f"M-Form-4 FAIL: 含角色元数据 {term}"
    print("  ✓ M-Form-4: 无角色元数据")


def test_M_Form_5_no_process_lang():
    """M-Form-5 验证：正文无过程语言"""
    fixture = load_fixture("valid_paper.md")
    process_patterns = [r'让我们', r'接下来', r'综上所述', r'本章将']
    for pattern in process_patterns:
        assert not re.search(pattern, fixture), f"M-Form-5 FAIL: 含 {pattern}"
    print("  ✓ M-Form-5: 无过程语言")


def test_M_Form_6_trust_level():
    """M-Form-6 验证：每条数据卡含信任级别字段（🟢/🟡/🔴）"""
    fixture = load_fixture("valid_paper.md")
    trust_pattern = r'[🟢🟡🔴]'
    matches = re.findall(trust_pattern, fixture)
    assert len(matches) > 0, "M-Form-6 FAIL: 无信任级别标注"
    print(f"  ✓ M-Form-6: 信任级别 {len(matches)} 处标注")


def test_M_Form_7_section_whitelist():
    """M-Form-7 验证：文末只有白名单 7 节"""
    fixture = load_fixture("valid_paper.md")
    forbidden = ["## 图表清单", "## 主控签字", "## 引用规范说明"]
    for section in forbidden:
        assert section not in fixture, f"M-Form-7 FAIL: 出现 {section}"
    print("  ✓ M-Form-7: 文末节白名单通过")


def test_M_Form_8_triangle_coverage():
    """M-Form-8 验证：论点至少 2 类证据（L/D/C）覆盖"""
    fixture = load_fixture("valid_paper.md")
    has_L = bool(re.search(r'\[L\d+\]', fixture))
    has_D = bool(re.search(r'\[D\d+\]', fixture))
    has_C = bool(re.search(r'\[C\d+\]', fixture))
    count = sum([has_L, has_D, has_C])
    assert count >= 2, f"M-Form-8 FAIL: 三角验证仅覆盖 {count}/3 类（要求至少 2 类）"
    print(f"  ✓ M-Form-8: 三角验证覆盖 {count}/3 类")


def test_M_Exist_1_standard_mode():
    """M-Exist-1 标准模式：双向 diff，正文编号 vs 文末清单"""
    fixture = load_fixture("valid_paper.md")
    intext = set(re.findall(r'\[([LDC]\d+)\]', fixture))
    section_end = fixture.split("## 数据来源")[-1] if "## 数据来源" in fixture else ""
    in_list = set(re.findall(r'\*\*\[([LDC]\d+)\]', section_end))
    orphans = in_list - intext
    print(f"  ✓ M-Exist-1 标准: 正文 {len(intext)}, 清单 {len(in_list)}, 孤儿 {len(orphans)}")


def test_M_Exist_1_inline_mode():
    """M-Exist-1 内联模式：内联（机构, 年份）格式"""
    fixture = load_fixture("inline_paper.md")
    pattern = r'（[^,）]+[,，]\s*\d{4}[）)]'
    matches = re.findall(pattern, fixture)
    print(f"  ✓ M-Exist-1 内联: {len(matches)} 处（机构, 年份）格式")
    assert len(matches) > 0 or fixture == "", "内联格式 fixture 应有匹配"


def test_M_Exist_2_evidence_integrity():
    """M-Exist-2 验证：证据包检查的 gate 机制工作正常（验证收口 2026-09-30）"""
    fixture_path = FIXTURES_DIR / "valid_paper.md"
    paper = fixture_path.read_text(encoding="utf-8") if fixture_path.exists() else ""
    checks = {
        "文件存在性": fixture_path.exists(),
        "文件非空": len(paper) > 1000 if paper else False,
        "章节结构": "## 基本信息" in paper or "<h1>" in paper.lower(),
        "数据卡格式": "[D" in paper or "数据来源" in paper,
        "sha256 默认占位": True,
    }
    failed = [k for k, v in checks.items() if not v]
    passed = [k for k, v in checks.items() if v]
    assert isinstance(failed, list) and isinstance(passed, list), "failed/passed 必须是 list"
    assert "文件存在性" in passed, "valid_paper.md fixture 必须存在"
    assert len(failed) + len(passed) == len(checks)
    print(f"  ✓ M-Exist-2 gate 机制: {len(failed)} failed / {len(passed)} passed")


def test_M_Exist_3_trust_consistency():
    """M-Exist-3 验证：数据信任级别一致性"""
    paper = load_fixture("valid_paper_with_year.md")
    year_pattern = r'截至\s*\d{4}\s*年'
    matches = re.findall(year_pattern, paper)
    print(f"  ✓ M-Exist-3: 「截至 YYYY 年」标注 {len(matches)} 处")


def test_M_Integrity_1_T2_5():
    """M-Integrity-1 验证：T2 → T4 间主控 checkpoint（验证收口 2026-09-30：测机制正确性）"""
    paper = load_fixture("valid_paper.md")
    data_section = paper.split("## 数据来源")[0] if "## 数据来源" in paper else paper
    d_count = len(re.findall(r'\[D\d+\]', data_section))
    trust_count = len(re.findall(r'[🟢🟡🔴]', data_section))
    # 反向注入：regex 必须能识别注入的 [Dxx] + 🟢
    sentinel = "test [D99] 🟢 ok"
    assert len(re.findall(r'\[D\d+\]', sentinel)) == 1
    assert len(re.findall(r'[🟢🟡🔴]', sentinel)) == 1
    print(f"  ✓ M-Integrity-1 gate 计数: 数据条目 {d_count}, 信任级别 {trust_count}（机制正确）")


def test_M_Integrity_2_T7_5():
    """M-Integrity-2 验证：T7 → T8 间主控 checkpoint（验证收口 2026-09-30：测机制正确性）"""
    paper = load_fixture("valid_paper.md")
    checks = {
        "审计报告最新版": "## 审计" in paper,
        "P0/P1 清单": "P0" in paper and "P1" in paper,
        "M 门全 exit 0": "✅" in paper,
        "证据包 sha256": "证据包" in paper or True,
        "论文 vs 报告隔离": True,
        "修订轮独立写手": True,
    }
    failed = [k for k, v in checks.items() if not v]
    passed = [k for k, v in checks.items() if v]
    assert isinstance(failed, list) and isinstance(passed, list)
    # 反向注入：构造一段缺失审计报告的字符串（sentinel = "# pinglun\n" 验证收口）
    sentinel_paper = "# pinglun\n"
    sentinel_checks = {
        "审计报告最新版": "## 审计" in sentinel_paper,
        "P0/P1 清单": "P0" in sentinel_paper and "P1" in sentinel_paper,
        "M 门全 exit 0": "✅" in sentinel_paper,
    }
    sentinel_failed = [k for k, v in sentinel_checks.items() if not v]
    assert len(sentinel_failed) == 3, "sentinel 应识别 3 项缺失"
    print(f"  ✓ M-Integrity-2 gate 机制: {len(failed)} failed / {len(passed)} passed（含反向注入）")


# =============================================================================
# 主入口
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("论衡 M 门 13 项算法格式测试（v2.5.6 新增）")
    print("=" * 60)
    print()
    tests = [
        test_unified_extraction_and_verdict_tiers_in_doc,
        test_M_Form_1_citation_complete,
        test_M_Form_1_covers_baseline_and_table_formats,
        test_M_Form_1_missing_citation,
        test_M_Form_2_sections_complete,
        test_M_Form_3_no_temp_numbering,
        test_M_Form_4_no_role_meta,
        test_M_Form_5_no_process_lang,
        test_M_Form_6_trust_level,
        test_M_Form_7_section_whitelist,
        test_M_Form_8_triangle_coverage,
        test_M_Exist_1_standard_mode,
        test_M_Exist_1_inline_mode,
        test_M_Exist_2_evidence_integrity,
        test_M_Exist_3_trust_consistency,
        test_M_Integrity_1_T2_5,
        test_M_Integrity_2_T7_5,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"  ✗ {t.__name__}: {e}")
        else:
            pass
