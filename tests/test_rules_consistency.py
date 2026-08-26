#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_rules_consistency.py — 论衡 T9 评分规则 + G14 检测规则一致性测试（v2.5.12 新增）

背景（第三方全量审计 P1-3）：
  论衡的 M 门已有 15 项格式测试（test_m_gate.py），但 T9 同行评审（6 维度评分）
  与 G14 中文 AI 痕迹闸（8 类检测）这两个「规则型算法」零测试覆盖。
  T9/G14 与 M 门一样是 LLM 推理判定，无法测「行为正确性」，但可以测
  「规则定义一致性」——即维度数、阈值档位在多文件间不漂移（防「改 A 漏 B」）。

测试范围：
  - T9 6 维度（原创性/方法论/证据强度/论证结构/写作质量/引文规范）三处一致
  - T9 阈值 4 档（accept 26-30 / minor 21-25 / major 16-20 / reject <16）一致
  - G14 8 类检测维度（学术模板语…党报话语堆砌）三处一致
  - G14 阈值 3 档（0-2 Pass / 3-4 Warning / 5+ Fail）一致

设计原则（对齐 test_m_gate.py 教训 #177）：
  - 只验证「规则文档结构一致性」，不依赖真实 LLM 调用
  - 断言目标 = 「多文件维度/阈值不漂移」，非「LLM 行为正确」
"""
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
# G14 中文 AI 痕迹闸：8 类检测维度一致性
# =============================================================================
G14_CATEGORIES = [
    "学术模板语", "句式同质化", "学术套话高频", "破折号滥用",
    "三项排比", "人称错位", "个人辨识度缺失", "党报话语堆砌",
]


def test_G14_8_categories_consistency():
    """G14 的 8 类检测维度在 gate 文档 + 检测器 + SKILL.md 三处齐全（防漂移）"""
    gate = _read(G14_GATE)
    checker = _read(G14_CHECKER)
    skill = _read(SKILL)

    missing_gate = [c for c in G14_CATEGORIES if c not in gate]
    missing_checker = [c for c in G14_CATEGORIES if c not in checker]
    missing_skill = [c for c in G14_CATEGORIES if c not in skill]

    assert not missing_gate, f"G14 gate 文档缺维度: {missing_gate}"
    assert not missing_checker, f"G14 检测器缺维度: {missing_checker}"
    assert not missing_skill, f"SKILL.md 缺维度: {missing_skill}"
    print(f"  ✓ G14-8类: gate/检测器/SKILL.md 三处齐全")


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
# 主入口
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("论衡 T9 + G14 规则一致性测试（v2.5.12 新增）")
    print("=" * 60)
    print()

    tests = [
        test_T9_6_dimensions_consistency,
        test_T9_4_tiers_consistency,
        test_G14_8_categories_consistency,
        test_G14_3_tiers_consistency,
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
