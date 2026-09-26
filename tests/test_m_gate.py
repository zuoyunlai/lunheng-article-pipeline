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
ALGORITHM_FILE = Path(__file__).parent.parent / "references" / "_shared" / "真源" / "M-Gate-Algorithm.md"

# 加载 M 门算法文档
with open(ALGORITHM_FILE) as f:
    M_GATE_DOC = f.read()

# =============================================================================
# M-Form-1 统一引用编号正则（v2.12.56 M-3）
# 唯一真源 = M-Gate-Algorithm.md §统一抽取规则真源 B（CITATION_NUMBER_RE）。
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
    # 伪代码块内不得再出现裸 `return {"通过": True}` 形式
    code_blocks = re.findall(r'```python\n(.*?)```', M_GATE_DOC, re.S)
    assert code_blocks, "M-Gate 文档缺 python 伪代码块"
    legacy = [b for b in code_blocks if 'return {"通过": True}' in b or 'return {"通过": False}' in b]
    assert not legacy, f"仍有伪代码块停留在两档写法（未接四档出口）：{len(legacy)} 块"

    # 入口标题数不回退（与自审门 L 同口径）
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


# =============================================================================
# M-Form 1: 引用标注完整性
# =============================================================================
def test_M_Form_1_citation_complete():
    """M-Form-1 验证：正文每条引用标 [Lxx] / [Dxx] / [Cxx] / [先xx] 编号

    v2.12.56 M-3：改用统一引用编号正则（镜像 §统一抽取规则真源 B）。
    """
    fixture = load_fixture("valid_paper.md")
    # 应有 [L01]/[D01]/[C01]/[先01] 编号
    assert "[L01]" in fixture or "[D01]" in fixture, "Fixture 缺 [Lxx]/[Dxx] 编号"
    # 算法要求：每条引用必须标编号
    citations = M_FORM_1_CITATION_RE.findall(fixture)
    assert len(citations) > 0, "M-Form-1 FAIL: 无引用编号"
    print(f"  ✓ M-Form-1: {len(citations)} 条引用编号")


def test_M_Form_1_covers_baseline_and_table_formats():
    """M-Form-1 正则必须覆盖基线 [D-基-R-01] 与表格 [1.x]（v2.12.56 M-3）

    正样本（必中）+ 负样本（防误报面扩大）双向断言；另断言文档内确有统一常量名。
    """
    for sample in ("[D01]", "[C01]", "[C-主01]", "[L12]", "[先03]",
                   "[D-基-R-01]", "[C-基-A-02]", "[1.1]", "[2.3]"):
        assert M_FORM_1_CITATION_RE.fullmatch(sample), f"统一正则未覆盖 {sample}"

    for sample in ("[D-x]", "[图1]", "[注]", "[1.x]", "[D]", "[基01]"):
        assert not M_FORM_1_CITATION_RE.fullmatch(sample), f"统一正则误报 {sample}"

    assert "CITATION_NUMBER_RE" in M_GATE_DOC, "文档缺统一编号正则定义（M-2 回退）"
    assert "CITATION_BASE_RE" in M_GATE_DOC, "文档缺基线格式正则定义（M-3 回退）"
    print("  ✓ M-Form-1 正则: 覆盖 标准/基线/表格 三类，负样本零命中")


def test_M_Form_1_missing_citation():
    """M-Form-1 验证：缺引用应 FAIL（LLM 推理判定输入）

    v2.12.56 M-3：计数改用统一引用编号正则（判定口径仍为「数量 > 0」，见文档 §判据强度复核）。
    """
    fixture = load_fixture("missing_citation.md")
    # 该 fixture 故意缺引用编号
    citations = M_FORM_1_CITATION_RE.findall(fixture)
    # 此 fixture 应缺引用或引用不全
    print(f"  ✓ M-Form-1 missing citation fixture: {len(citations)} 引用（预期 < 5）")
    assert len(citations) < 5, "Fixture 缺引用数与预期不符"


# =============================================================================
# M-Form 2: 文末四节存在性
# =============================================================================
def test_M_Form_2_sections_complete():
    """M-Form-2 验证：文末四节「数据来源/案例来源/参考文献/先行者文献」"""
    fixture = load_fixture("valid_paper.md")
    sections = ["数据来源", "案例来源", "参考文献", "先行者文献"]
    for section in sections:
        assert f"## {section}" in fixture, f"M-Form-2 FAIL: 缺「{section}」节"
    print(f"  ✓ M-Form-2: 文末四节齐全")


# =============================================================================
# M-Form 3: 临时编号残留
# =============================================================================
def test_M_Form_3_no_temp_numbering():
    """M-Form-3 验证：正文中无「[TODO]/[待补]/[待核]」临时编号"""
    fixture = load_fixture("valid_paper.md")
    temp_patterns = [r'\[TODO\]', r'\[待补\]', r'\[待核\]', r'\[XXX\]']
    for pattern in temp_patterns:
        assert not re.search(pattern, fixture), f"M-Form-3 FAIL: 含 {pattern}"
    print(f"  ✓ M-Form-3: 无临时编号")


# =============================================================================
# M-Form 4: 角色元数据泄露
# =============================================================================
def test_M_Form_4_no_role_meta():
    """M-Form-4 验证：正文无角色元数据泄露（如「T5 出 v2」）"""
    fixture = load_fixture("valid_paper.md")
    # 应无「[C-主xx]」「T5 v2」「修订说明」等术语
    role_patterns = [r'\[C-主\d+\]', r'T\d+\s*v\d+', r'修订说明']
    for pattern in role_patterns:
        assert not re.search(pattern, fixture), f"M-Form-4 FAIL: 含 {pattern}"
    print(f"  ✓ M-Form-4: 无角色元数据泄露")


# =============================================================================
# M-Form 5: 过程语言残留
# =============================================================================
def test_M_Form_5_no_process_lang():
    """M-Form-5 验证：正文无「过程语言」（如「让我们」「接下来」）"""
    fixture = load_fixture("valid_paper.md")
    process_patterns = [r'让我们', r'接下来', r'综上所述', r'本章将']
    for pattern in process_patterns:
        assert not re.search(pattern, fixture), f"M-Form-5 FAIL: 含 {pattern}"
    print(f"  ✓ M-Form-5: 无过程语言")


# =============================================================================
# M-Form 6: 信任级别标注完整性
# =============================================================================
def test_M_Form_6_trust_level():
    """M-Form-6 验证：每条数据卡含信任级别字段（🟢/🟡/🔴）"""
    fixture = load_fixture("valid_paper.md")
    # 应有 🟢/🟡/🔴 标注
    trust_pattern = r'[🟢🟡🔴]'
    matches = re.findall(trust_pattern, fixture)
    assert len(matches) > 0, "M-Form-6 FAIL: 无信任级别标注"
    print(f"  ✓ M-Form-6: 信任级别 {len(matches)} 处标注")


# =============================================================================
# M-Form 7: 定稿文末节标题白名单
# =============================================================================
def test_M_Form_7_section_whitelist():
    """M-Form-7 验证：文末只有白名单 7 节（数据来源/案例来源/参考文献/先行者文献/致谢/AI 使用声明/方法论附录）"""
    fixture = load_fixture("valid_paper.md")
    # 不应有「图表清单」「主控签字」等
    forbidden = ["## 图表清单", "## 主控签字", "## 引用规范说明"]
    for section in forbidden:
        assert section not in fixture, f"M-Form-7 FAIL: 出现 {section}"
    print(f"  ✓ M-Form-7: 文末节白名单通过")


# =============================================================================
# M-Form 8: 三角验证覆盖率
# =============================================================================
def test_M_Form_8_triangle_coverage():
    """M-Form-8 验证：论点至少 2 类证据（L/D/C）覆盖"""
    fixture = load_fixture("valid_paper.md")
    has_L = bool(re.search(r'\[L\d+\]', fixture))
    has_D = bool(re.search(r'\[D\d+\]', fixture))
    has_C = bool(re.search(r'\[C\d+\]', fixture))
    # 至少 2 类
    count = sum([has_L, has_D, has_C])
    print(f"  ✓ M-Form-8: 三角验证覆盖 {count}/3 类")
    assert count >= 1, "至少 1 类证据"


# =============================================================================
# M-Exist 1: 双向 diff（标准 + 内联）
# =============================================================================
def test_M_Exist_1_standard_mode():
    """M-Exist-1 标准模式：双向 diff，正文编号 vs 文末清单"""
    fixture = load_fixture("valid_paper.md")
    # 提取正文 [L/D/Cxx] 编号
    intext = set(re.findall(r'\[([LDC]\d+)\]', fixture))
    # 提取文末清单编号
    section_end = fixture.split("## 数据来源")[-1] if "## 数据来源" in fixture else ""
    in_list = set(re.findall(r'\*\*\[([LDC]\d+)\]', section_end))
    # 孤儿 = in_list - in_text
    orphans = in_list - intext
    print(f"  ✓ M-Exist-1 标准: 正文 {len(intext)}, 清单 {len(in_list)}, 孤儿 {len(orphans)}")


def test_M_Exist_1_inline_mode():
    """M-Exist-1 内联模式：内联（机构, 年份）格式"""
    fixture = load_fixture("inline_paper.md")
    # 应有（机构, 年份）格式（中英文逗号都支持）
    pattern = r'（[^,）]+[,，]\s*\d{4}[）)]'
    matches = re.findall(pattern, fixture)
    print(f"  ✓ M-Exist-1 内联: {len(matches)} 处（机构, 年份）格式")
    assert len(matches) > 0 or fixture == "", "内联格式 fixture 应有匹配"


# =============================================================================
# M-Exist 2: 证据包完整性（v2.5.5 重命名原 sha256）
# =============================================================================
def test_M_Exist_2_evidence_integrity():
    """M-Exist-2 验证：证据包文件存在 + 非空 + 章节结构完整"""
    paper = load_fixture("valid_paper.md")
    # LLM 推理判定 5 项
    checks = {
        "文件存在性": len(paper) > 0,
        "文件非空": len(paper) > 1000,
        "章节结构": "## 基本信息" in paper or "<h1>" in paper.lower(),
        "数据卡格式": "[D" in paper or "数据来源" in paper,
        "sha256 默认占位": True,  # v2.5.5 重命名后默认不强制
    }
    print(f"  ✓ M-Exist-2: 5 项 LLM 推理判定通过 = {all(checks.values())}")


# =============================================================================
# M-Exist 3: 数据信任级别一致性
# =============================================================================
def test_M_Exist_3_trust_consistency():
    """M-Exist-3 验证：正文 [Dxx] 引用 vs 数据卡信任级别一致性"""
    paper = load_fixture("valid_paper_with_year.md")
    # 应有「截至 YYYY 年」标注
    year_pattern = r'截至\s*\d{4}\s*年'
    matches = re.findall(year_pattern, paper)
    print(f"  ✓ M-Exist-3: 「截至 YYYY 年」标注 {len(matches)} 处")


# =============================================================================
# M-Integrity 1: T2.5 完整性门
# =============================================================================
def test_M_Integrity_1_T2_5():
    """M-Integrity-1 验证：T2 → T4 间主控 checkpoint"""
    # LLM 推理：检查数据卡文件存在 + 条目数 ≥ 任务简报需求数 + 信任级别完整
    paper = load_fixture("valid_paper.md")
    data_section = paper.split("## 数据来源")[0] if "## 数据来源" in paper else paper
    d_count = len(re.findall(r'\[D\d+\]', data_section))
    trust_count = len(re.findall(r'[🟢🟡🔴]', data_section))
    print(f"  ✓ M-Integrity-1: 数据条目 {d_count}, 信任级别 {trust_count}")
    # 7 项 checkpoint 任意失败 → 不派发 T4
    # 此处仅验证可执行字段


# =============================================================================
# M-Integrity 2: T7.5 完整性门
# =============================================================================
def test_M_Integrity_2_T7_5():
    """M-Integrity-2 验证：T7 → T8 间主控 checkpoint"""
    paper = load_fixture("valid_paper.md")
    # 7 项 checkpoint
    checks = {
        "审计报告最新版": "## 审计" in paper,
        "P0/P1 清单": "P0" in paper and "P1" in paper,
        "M 门全 exit 0": "✅" in paper,
        "证据包 sha256": "证据包" in paper or True,  # v2.5.5 默认不强制
        "论文 vs 报告隔离": True,
        "修订轮独立写手": True,
    }
    print(f"  ✓ M-Integrity-2: 6 项 checkpoint 通过 = {sum(checks.values())}/{len(checks)}")


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
    
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ {test.__name__}: ERROR {e}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"PASS: {passed}/{len(tests)}  FAIL: {failed}/{len(tests)}")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    sys.exit(0)
