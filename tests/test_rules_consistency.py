#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_rules_consistency.py — 论衡 T9 评分规则 + G14 检测规则一致性测试（v2.5.12 新增）

背景（第三方全量审计 P1-3）：
  论衡的 M 门已有 15 项格式测试（test_m_gate.py），但 T9 同行评审（6 维度评分）
  与 G14 中文 AI 痕迹闸（9 类检测）这两个「规则型算法」零测试覆盖。
  T9/G14 与 M 门一样是 LLM 推理判定，无法测「行为正确性」，但可以测
  「规则定义一致性」——即维度数、阈值档位在多文件间不漂移（防「改 A 漏 B」）。

测试范围：
  - T9 6 维度（原创性/方法论/证据强度/论证结构/写作质量/引文规范）三处一致
  - T9 阈值 4 档（accept 26-30 / minor 21-25 / major 16-20 / reject <16）一致
  - G14 9 类检测维度（学术模板语…防御性写作）三处一致
  - G14 阈值 3 档（0-2 Pass / 3-4 Warning / 5+ Fail）一致

设计原则（对齐 test_m_gate.py 教训 #177）：
  - 只验证「规则文档结构一致性」，不依赖真实 LLM 调用
  - 断言目标 = 「多文件维度/阈值不漂移」，非「LLM 行为正确」
"""
import re
import sys
from pathlib import Path

# 路径配置
ROOT = Path(__file__).parent.parent
SKILL = ROOT / "SKILL.md"
T9_CARD = ROOT / "references" / "agents" / "09-审稿-peer-reviewer.md"
T9_TEMPLATE = ROOT / "references" / "templates" / "审稿报告-template.md"
G14_GATE = ROOT / "references" / "gates" / "14-中文AI痕迹-gate.md"
G14_CHECKER = ROOT / "references" / "checkers" / "中文AI痕迹-checker.md"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


# =============================================================================
# T9 同行评审：6 维度一致性
# =============================================================================
T9_DIMENSIONS = ["原创性", "方法论", "证据强度", "论证结构", "写作质量", "引文规范"]


def test_T9_6_dimensions_consistency():
    """T9 的 6 个评分维度在角色卡 + 审稿报告模板 + SKILL.md 三处齐全（防漂移）"""
    card = _read(T9_CARD)
    template = _read(T9_TEMPLATE)
    skill = _read(SKILL)

    missing_card = [d for d in T9_DIMENSIONS if d not in card]
    missing_tpl = [d for d in T9_DIMENSIONS if d not in template]
    missing_skill = [d for d in T9_DIMENSIONS if d not in skill]

    assert not missing_card, f"T9 角色卡缺维度: {missing_card}"
    assert not missing_tpl, f"审稿报告模板缺维度: {missing_tpl}"
    assert not missing_skill, f"SKILL.md 缺维度: {missing_skill}"
    print(f"  ✓ T9-6维度: 角色卡/模板/SKILL.md 三处齐全")


# =============================================================================
# T9 同行评审：阈值 4 档一致性
# =============================================================================
T9_TIERS = [
    ("accept", "26-30"),
    ("minor", "21-25"),
    ("major", "16-20"),
    ("reject", "<16"),
]


def test_T9_4_tiers_consistency():
    """T9 阈值 4 档（accept 26-30 / minor 21-25 / major 16-20 / reject <16）一致"""
    card = _read(T9_CARD)
    skill = _read(SKILL)

    for tier, score in T9_TIERS:
        # 角色卡必须含分数区间（L189-192 段）
        assert score in card, f"T9 角色卡缺阈值 {tier}({score})"
        # SKILL.md 必须含分数区间（角色卡总评段同步）
        assert score in skill, f"SKILL.md 缺阈值 {tier}({score})"
    print(f"  ✓ T9-4档阈值: accept/minor/major/reject 分数区间一致")


# =============================================================================
# G14 中文 AI 痕迹闸：9 类检测维度一致性
# =============================================================================
G14_CATEGORIES = [
    "学术模板语", "句式同质化", "学术套话高频", "破折号滥用",
    "三项排比", "人称错位", "个人辨识度缺失", "党报话语堆砌",
    "防御性写作",
]


def test_G14_9_categories_consistency():
    """G14 的 9 类检测维度在 gate 文档 + 检测器 + SKILL.md 三处齐全（防漂移）"""
    gate = _read(G14_GATE)
    checker = _read(G14_CHECKER)
    skill = _read(SKILL)

    missing_gate = [c for c in G14_CATEGORIES if c not in gate]
    missing_checker = [c for c in G14_CATEGORIES if c not in checker]

    # 真源（gate + 检测器）必须 9 类齐全
    assert not missing_gate, f"G14 gate 文档缺维度: {missing_gate}"
    assert not missing_checker, f"G14 检测器缺维度: {missing_checker}"
    # SKILL.md（入口，受 10,000 字符棘轮约束）按单一真源纪律只留指针、不重列（v2.12.41 改）
    assert "9 类判定" in skill, "SKILL.md 缺 G14「9 类判定」指针"
    assert "gates/14-中文AI痕迹-gate.md" in skill, "SKILL.md 缺 G14 真源指针"
    print(f"  ✓ G14-9类: gate/检测器真源齐全；SKILL.md 留指针（不重列，防漂移+保字符预算）")


# =============================================================================
# G14 中文 AI 痕迹闸：阈值 3 档一致性
# =============================================================================
G14_TIERS = [
    ("0-2", "Pass"),
    ("3-4", "Warning"),
    ("5+", "Fail"),
]


def test_G14_3_tiers_consistency():
    """G14 阈值 3 档（0-2 Pass / 3-4 Warning / 5+ Fail）一致"""
    gate = _read(G14_GATE)
    checker = _read(G14_CHECKER)

    # gate 文档：字符串阈值「0-2 / 3-4 / 5+」+ 三档判定
    for hit, verdict in G14_TIERS:
        assert hit in gate, f"G14 gate 文档缺阈值 {hit}"
        assert verdict in gate, f"G14 gate 文档缺判定 {verdict}"

    # 检测器：代码形式阈值（<= 2 命中 = 0-2 档 / <= 4 命中 = 3-4 档 / else = 5+ 档）+ 三档判定
    for verdict in ("Pass", "Warning", "Fail"):
        assert verdict in checker, f"G14 检测器缺判定 {verdict}"
    assert "<= 2" in checker, "G14 检测器缺 0-2 阈值（代码形式 <= 2）"
    assert "<= 4" in checker, "G14 检测器缺 3-4 阈值（代码形式 <= 4）"
    print(f"  ✓ G14-3档阈值: gate 字符串(0-2/3-4/5+) + 检测器代码(<=2/<=4) 一致")


# =============================================================================
# 字数判定表：单一口径 + 三级阈值一致性（v2.5.13 新增；口径统一为「仅正文」）
# =============================================================================
WORDCOUNT_TABLE = ROOT / "references" / "_shared" / "字数判定表.md"
WORDCOUNT_REF_FILES = [
    ROOT / "references" / "agents" / "07-审计-auditor.md",
    ROOT / "references" / "templates" / "任务简报-template.md",
    SKILL,
]


def test_wordcount_single_caliber():
    """字数判定表：单一口径（仅正文，不含文末附录）已定案；旧双口径写法须清除"""
    table = _read(WORDCOUNT_TABLE)
    # 唯一口径 = 正文字数（仅正文，不含文末附录）
    assert "仅正文" in table, "字数判定表缺「仅正文」口径定义"
    assert "不含文末附录" in table, "字数判定表缺「不含文末附录」口径定义"
    # 不得再出现已废除的旧口径
    assert "双口径" not in table, "字数判定表仍残留已废除的「双口径」"
    assert "含文末四节" not in table, "字数判定表仍残留「含文末四节」旧口径"
    print("  ✓ 字数单一口径: 仅正文 / 不含文末附录（旧双口径已清除）")


def test_wordcount_3_tiers_consistency():
    """字数判定三级阈值（v2.12.41：≤5% 呈现 / 5-10% P1 / >10% P0）在真源 + 引用文件间一致"""
    table = _read(WORDCOUNT_TABLE)
    # 真源必须含新的三档（粒度放宽：判定精度不得细于测量精度）
    assert "≤5%" in table and "呈现信息" in table, "字数判定表缺 ≤5% 呈现信息档"
    assert "5-10%" in table and "P1" in table, "字数判定表缺 5-10% P1 档"
    assert ">10%" in table and "P0" in table, "字数判定表缺 >10% P0 档"
    # 旧粒度必须清除（防回退）
    assert "≤1%" not in table and "1-5%" not in table, "字数判定表仍残留旧粒度（≤1% / 1-5%）"

    # 审计员卡（权威核验点）必须与新真源一致
    auditor = _read(ROOT / "references" / "agents" / "07-审计-auditor.md")
    assert "≤5%" in auditor and "5-10%" in auditor and ">10%" in auditor, \
        "07-审计-auditor.md 缺新三档阈值"

    # 任务简报（用户可见入口）：v2.12.41 起不再复述三档，改为「外部硬要求 ±5% / 无外部要求只呈现」
    brief = _read(ROOT / "references" / "templates" / "任务简报-template.md")
    assert "±5%" in brief and "无外部要求" in brief, \
        "任务简报-template.md 缺字数口径（±5% 粒度 / 无外部要求默认）"

    # 分章硬指标必须已废除（v2.12.41 的核心决定，防回退）
    assert "每章最小字数硬指标" not in brief, "任务简报仍残留「每章最小字数硬指标」"
    print(f"  ✓ 字数三档阈值: ≤5% 呈现 / 5-10% P1 / >10% P0（真源+审计员+任务简报一致；旧粒度已清除）")


def test_wordcount_no_byte_bug():
    """字数判定表：禁止 [一-龥] 字节 bug 命令（教训 #128 核心）"""
    table = _read(WORDCOUNT_TABLE)
    # 真源必须含禁止标注
    assert "一-龥" in table, "字数判定表缺 [一-龥] 字节 bug 禁止标注"
    # 审计员卡也必须含禁止标注（它是字数核验执行点）
    auditor = _read(ROOT / "references" / "agents" / "07-审计-auditor.md")
    assert "一-龥" in auditor, "07-审计-auditor.md 缺 [一-龥] 字节 bug 禁止标注"
    print(f"  ✓ 字数口径: 禁止 [一-龥] 字节 bug 命令（教训 #128）")


# =============================================================================
# G14 轻量档 selfcheck 阈值一致性（v2.12.30 新增，回应审计 P0-4）
# =============================================================================
def test_G14_selfcheck_threshold_consistency():
    """轻量档 selfcheck 阈值在 gate 文档内必须唯一且与字数判定表一致（防「同文件两口径」）"""
    gate = _read(G14_GATE)
    table = _read(WORDCOUNT_TABLE)

    assert "2000-3000" in table, "字数判定表缺轻量档 2000-3000 字口径"
    assert "2000-3000" in gate, "G14 gate 缺轻量档 2000-3000 字口径"

    # 反向断言：gate 内任何把 selfcheck/轻量档绑到 ≤2000 的表述都是矛盾口径
    bad = re.findall(r"(?:selfcheck|轻量档)[^）)\\n]{0,30}?≤\s*2000", gate)
    assert not bad, f"G14 gate 存在 ≤2000 字矛盾口径: {bad}"
    print("  ✓ G14 轻量档阈值: gate 与字数判定表一致（2000-3000 字，无 ≤2000 矛盾口径）")


# =============================================================================
# G15/G16 写作质量门一致性（v2.12.68 新增，借 writing-guard）
# =============================================================================
G15_G16_TERMS = ("G15 主张强度", "G16 上下文泄漏")


def test_G15_G16_writing_quality_gates_consistency():
    """G15 主张强度 + G16 上下文泄漏在真源 + T7 dispatch 两处齐全（防漂移）"""
    quickref = _read(ROOT / "references" / "_shared" / "audit-checklist-quickref.md")
    t7 = _read(ROOT / "references" / "dispatch" / "T7-审计.md")

    missing_quickref = [t for t in G15_G16_TERMS if t not in quickref]
    missing_t7 = [t for t in G15_G16_TERMS if t not in t7]

    assert not missing_quickref, f"audit-checklist-quickref.md 缺 G15/G16: {missing_quickref}"
    assert not missing_t7, f"T7 dispatch 缺 G15/G16: {missing_t7}"
    print("  ✓ G15/G16: 真源 + T7 dispatch 两处齐全（写作质量门不漂移）")


G17_TERM = "G17 数据指纹"


def test_G17_data_fingerprint_consistency():
    """G17 数据指纹比对在真源 + T7 dispatch 两处齐全（防漂移）"""
    quickref = _read(ROOT / "references" / "_shared" / "audit-checklist-quickref.md")
    t7 = _read(ROOT / "references" / "dispatch" / "T7-审计.md")

    assert G17_TERM in quickref, "audit-checklist-quickref.md 缺 G17 数据指纹"
    assert G17_TERM in t7, "T7 dispatch 缺 G17 数据指纹"
    print("  ✓ G17: 真源 + T7 dispatch 两处齐全（数据指纹门不漂移）")


H6_TERM = "期刊约定校验"


def test_H6_journal_convention_check_consistency():
    """H6 期刊约定校验在 T9 dispatch + 09-审稿角色卡两处齐全（防漂移）"""
    t9 = _read(ROOT / "references" / "dispatch" / "T9-同行评审.md")
    card = _read(ROOT / "references" / "agents" / "09-审稿-peer-reviewer.md")

    assert H6_TERM in t9, "T9 dispatch 缺期刊约定校验"
    assert H6_TERM in card, "09-审稿角色卡缺期刊约定校验"
    print("  ✓ H6: T9 dispatch + 09-审稿角色卡两处齐全（期刊约定校验不漂移）")


# =============================================================================
# 主入口（v2.12.42 删）
# =============================================================================
# 历史：本文件原含 __main__ 块，CI workflow（.github/workflows/ci-test.yml）以
#   `python tests/test_rules_consistency.py` 形式直接跑，触发 __main__。
#   v2.12.40 把函数 `test_wordcount_dual_caliber` 重命名为 `test_wordcount_single_caliber`，
#   忘了同步本列表，CI 因此 NameError 失败（pytest 不会执行 __main__，所以本机漏检）。
#   删 __main__ 后 CI 必须走 `pytest tests/...` —— 与项目其他测试统一入口、避免再漂。
if __name__ == "__main__":
    raise SystemExit(
        "本文件请通过 pytest 跑（CI 一致）：pytest tests/test_rules_consistency.py"
    )
    print(f"PASS: {passed}/{len(tests)}  FAIL: {failed}/{len(tests)}")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
    sys.exit(0)
