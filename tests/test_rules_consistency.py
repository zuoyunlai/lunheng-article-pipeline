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

import yaml

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
WORDCOUNT_TABLE = ROOT / "references" / "_shared" / "真源" / "字数判定表.md"
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
    quickref = _read(ROOT / "references" / "_shared" / "真源" / "audit-checklist-quickref.md")
    t7 = _read(ROOT / "references" / "dispatch" / "T7-审计.md")

    missing_quickref = [t for t in G15_G16_TERMS if t not in quickref]
    missing_t7 = [t for t in G15_G16_TERMS if t not in t7]

    assert not missing_quickref, f"audit-checklist-quickref.md 缺 G15/G16: {missing_quickref}"
    assert not missing_t7, f"T7 dispatch 缺 G15/G16: {missing_t7}"
    print("  ✓ G15/G16: 真源 + T7 dispatch 两处齐全（写作质量门不漂移）")


G17_TERM = "G17 数据指纹"


def test_G17_data_fingerprint_consistency():
    """G17 数据指纹比对在真源 + T7 dispatch 两处齐全（防漂移）"""
    quickref = _read(ROOT / "references" / "_shared" / "真源" / "audit-checklist-quickref.md")
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
# 2026-10-08 审计批次 1「契约自洽」（R-4 / R-5 / R-6 / R-7）回归门
# =============================================================================
# 背景：这四项都是**主控会照抄的契约**，而契约自身出过矛盾或算术错误：
#   R-4 route_tier.md 曾写「至少 2 族可满足 T6/T7/T9 三节点两两互异」——算术错误（需 3 族）；
#   R-5 route_tier.md 曾有「无记录 = 走默认链」fail-open 尾巴，与全局 silence_doctrine 冲突；
#   R-6 index.yaml terminal_freeze 重开链把 t9_review 排在 final_assembly 之前，与
#       `t9_review.input = final/定稿.md`（seq 21 > 20）矛盾；
#   R-7 可发表性判定表.md 的伪代码比判据列宽松（`>= 5` vs `= 拍板 N`；顺序判据未实现）。
#   四项均已修，以下用例防回潮。
ROUTE_TIER = ROOT / "references" / "_shared" / "真源" / "route_tier.md"
PORDER = ROOT / "references" / "_shared" / "真源" / "phase-order"
PUB_TABLE = ROOT / "references" / "_shared" / "真源" / "可发表性判定表.md"


def _active_rules(text: str) -> str:
    """只返回**生效规则**文本：剔除代码注释行与「原口径/旧口径/已废」引述行。

    为什么需要（2026-10-08 首轮红）：修订说明必然会引用旧条款原文
    （如「原口径「无记录 = 走默认链」」），naive 子串断言会把「已修净的历史引述」
    误判为「未修净的活规则」—— 本轮 3 条新门就是这么假红的。

    判别式：负面断言只扫本函数返回值；若将来真回归，则旧条款必然以**活规则**形式
    重新出现（不在注释行、也不在「原口径」引述里），仍会被捕获。
    """
    kept = []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("#"):
            continue
        if any(mark in s for mark in ("原口径", "旧口径", "已废", "原为")):
            continue
        kept.append(ln)
    return "\n".join(kept)


def test_R4_route_tier_family_count_has_two_separate_criteria():
    """R-4：族数判据须拆成「写手vs审计 ≥2」与「T6/T7/T9 两两互异 ≥3」两档，且旧的错误算术口径已消失"""
    text = _read(ROUTE_TIER)

    assert "writer_audit_distinct_families ≥ 2" in text, "缺「写手 vs 审计异族 ≥2 族」判据"
    assert "audit_full_independence_families ≥ 3" in text, "缺「T6/T7/T9 两两互异 ≥3 族」判据"
    # 旧的错误表述必须已删除（否则主控会读成 2 族即可满足三节点互异）
    assert "至少 2 个互异 provider 族**可用（满足 T6/T7/T9 三节点两两互异" not in text, \
        "R-4 未修净：仍存在「2 族满足三节点两两互异」的算术错误表述"
    # N=2 时必须判 degraded，不得判 pass
    assert "N=2 时 `audit_full_independence` 必判 `degraded`" in text, \
        "缺 N=2 ⇒ degraded 的显式判档纪律"
    print("  ✓ R-4: route_tier 族数判据已拆两档（≥2 / ≥3），旧算术错误已清")


def test_R5_route_record_missing_is_fail_closed():
    """R-5：`phase0_route` 缺记录必须 fail-closed（三处一致：route_tier / 切片 / SKILL.md）"""
    text = _read(ROUTE_TIER)
    slice_text = _read(PORDER / "pre_spawn_enforcement.yaml")
    skill = _read(ROOT / "SKILL.md")

    # 旧的 fail-open 尾巴必须已从**生效规则层**消失（历史引述允许保留）
    assert "无记录 = 按 [1] 默认链执行" not in _active_rules(text), \
        "R-5 未修净：生效规则层仍存在「无记录 = 走默认链」的 fail-open 尾巴"
    # 新口径
    assert "视同未过 Phase 0 后置" in text, "route_tier 缺「视同未过 Phase 0 后置」判据"
    assert "selected_by: owner" in text, "route_tier 缺 `selected_by: owner` 显式落痕要求"
    # 切片判据
    assert "phase0_route" in slice_text, "pre_spawn_enforcement 切片缺 phase0_route 前置判据"
    assert "selected_by=owner" in slice_text, "pre_spawn_enforcement 切片缺 selected_by=owner 判据"
    assert "path_or_param_error" in slice_text, "pre_spawn_enforcement 切片缺四档判据归属"
    # 入口文档口径：**只断言真源指针存在**，不要求 SKILL.md 重复 fail-closed 明文。
    # 原因：SKILL.md 有比门 V(10000) 更紧的 9000 字符硬预算
    # （tests/test_denied_truth_externalization.py::test_frontmatter_does_not_carry_full_list_again），
    # 2026-10-08 首次尝试写入该指针时实测 8995→9031 破线，已按「一条款一真源」惯例回改为纯指针。
    # fail-closed 判据本体由 route_tier.md 与 pre_spawn_enforcement 切片两处机械锁定（上方已断言）。
    assert "三档路由探活" in skill and "route_tier.md" in skill, \
        "SKILL.md Phase 0 段缺 route_tier 真源指针"
    print("  ✓ R-5: 路由缺记录已 fail-closed（route_tier / 切片 / SKILL.md 三处一致）")


def test_R6_terminal_freeze_reopen_order_respects_t9_input():
    """R-6：重开链必须先 final_assembly 再 t9_review（与 t9_review.input = final/定稿.md 一致）"""
    t9 = yaml.safe_load(_read(PORDER / "t9_review.yaml"))[0]
    asm = yaml.safe_load(_read(PORDER / "final_assembly.yaml"))[0]

    # 依赖事实：T9 读的是组装产物，且位序在组装之后
    assert "final/定稿.md" in str(t9.get("input", "")), "t9_review.input 不含 final/定稿.md（依赖前提已变）"
    assert t9["phase_seq"] > asm["phase_seq"], \
        f"t9_review(seq={t9['phase_seq']}) 必须晚于 final_assembly(seq={asm['phase_seq']})"

    # 契约文本：doctrine 中 final_assembly 必须先于 t9_review 出现
    # （**只扫 doctrine 字段**：reopen_required_gates 列表里也含这两个 id，
    #   用全文 find 会被列表抢到先手而假红 —— 本轮首轮红就是这个）
    data = yaml.safe_load(_read(PORDER / "index.yaml"))
    doctrine = (data.get("terminal_freeze") or {}).get("doctrine") or ""
    assert doctrine, "index.yaml 缺 terminal_freeze.doctrine"
    i_asm = doctrine.find("final_assembly")
    i_t9 = doctrine.find("t9_review")
    assert i_asm != -1 and i_t9 != -1, "terminal_freeze.doctrine 缺 final_assembly / t9_review 重开项"
    assert i_asm < i_t9, (
        "R-6 未修净：terminal_freeze 重开链把 t9_review 排在 final_assembly 之前 —— "
        "按该序执行等于让盲审读旧版定稿"
    )
    print("  ✓ R-6: terminal_freeze 重开链与 t9_review 输入依赖一致（组装 → 盲审）")


def test_R7_publishability_pseudocode_not_looser_than_criteria():
    """R-7：伪代码不得比判据列宽松（图位数严格 = N；引用顺序判据必须真实现）"""
    text = _read(PUB_TABLE)
    active = _active_rules(text)

    # 维度 5：判据列是「= 拍板 N」，伪代码必须同样严格
    assert "svg_count == n_decided" in text, "R-7 未修净：check_charts 仍非「= 拍板 N」严格相等"
    assert "svg_count >= 5" not in active, "R-7 未修净：生效代码仍用旧的 `>= 5` 宽松口径"
    assert "n_decided: int" in text, "check_charts 缺 n_decided 入参（无法取 Phase 2.5 拍板值）"
    # 维度 4.3：顺序判据必须被伪代码真正实现
    assert "order_mismatch" in text, "R-7 未修净：引用顺序判据（order_mismatch）未实现"
    assert "and not order_mismatch" in text, "R-7 未修净：passed 未纳入 order_mismatch"
    print("  ✓ R-7: 可发表性判定表伪代码与判据列一致（= N 严格 / 顺序闭环已实现）")


def test_R2_R3_acceptance_criteria_wired_end_to_end():
    """R-2(C1) / R-3(A1)：验收对账与交付就绪二态必须在「节点 → 判据单源 → status 模板 → Phase 5 卡」四处接线一致。

    防的是「只改了节点字段、判据详情没落」或「只写了判据、卡上不呈现」两类半落地。
    """
    import yaml

    node = yaml.safe_load(_read(PORDER / "phase5_acceptance.yaml"))[0]
    node_raw = _read(PORDER / "phase5_acceptance.yaml")   # 注释不进 YAML 解析结果，指针须查原文
    crit = _read(PUB_TABLE)
    st = _read(ROOT / "references" / "templates" / "status-template.md")
    card = _read(ROOT / "references" / "templates" / "checkpoint-card-template.md")

    # ① 节点侧只放字段 + 枚举 + 指针（棘轮额度用尽，判据正文不得堆进契约文件）
    assert node.get("acceptance_reconciliation") == "required", "phase5_acceptance 缺 acceptance_reconciliation"
    dr = node.get("delivery_readiness")
    assert dr == ["submission_ready", "accepted_with_open_items"], \
        f"delivery_readiness 枚举不符：{dr}"
    # ⚠️ 指针注释写在行尾 ⇒ **必须查原文**（YAML 解析会丢弃注释，早期版本查 dict 因此恒假红）
    assert "§六" in node_raw, "节点未指向判据单源 §六（可发表性判定表）"

    # ② 判据单源确有 §六 且含四项对账 + 二态
    assert "## 六、验收对账与交付就绪" in crit, "可发表性判定表缺 §六（判据单源）"
    for need in ("验收前置对账", "delivery_readiness", "submission_ready",
                 "accepted_with_open_items", "未闭合项"):
        assert need in crit, f"§六 缺「{need}」"

    # ③ status.md 模板：C1 派生视图锁 + 两个新字段
    assert "派生视图" in st, "status-template 缺 R-2(C1) 派生视图锁"
    assert "验收前置对账" in st, "status-template 缺 验收前置对账 字段"
    assert "delivery_readiness" in st, "status-template 缺 delivery_readiness 字段"

    # ④ Phase 5 卡：必呈现对账结果 + 二态，且必须点明 accepted ≠ submission_ready
    assert "验收前置对账" in card, "Phase 5 卡缺 验收前置对账 必呈现项"
    assert "accepted_with_open_items" in card, "Phase 5 卡缺 交付就绪二态"
    assert "submission_ready" in card, "Phase 5 卡缺 交付就绪二态"
    assert "≠" in card and "submission_ready" in card, \
        "Phase 5 卡未点明「accepted ≠ submission_ready」（主人会误读为已可投稿）"
    print("  ✓ R-2/R-3: 验收对账与交付就绪二态四处接线一致")


def test_R1_phase15_split_into_two_evaluation_points():
    """R-1(B1)：Phase 1.5 的两个求值点必须**时序可达**且触发依据互不重叠。

    回退面：把 `t2_5_red_data_unresolved` 塞回 seq 4 节点，会让红数据项在首次到达时恒为假
    且被 `on_not_triggered` 静默吞掉——而 `pipeline_nodes` 计数**不会**因此变红（节点数没变），
    所以必须由本用例按**语义**守，不能指望计数漂移门兜住。
    """
    import yaml

    early = yaml.safe_load(_read(PORDER / "phase1_5_targeted_review.yaml"))[0]
    late = yaml.safe_load(_read(PORDER / "phase1_5b_post_t2_5_review.yaml"))[0]
    t2_5 = yaml.safe_load(_read(PORDER / "t2_5_integrity.yaml"))[0]
    t4 = yaml.safe_load(_read(PORDER / "t4_analysis.yaml"))[0]

    # ① 触发依据互不重叠：红数据项只在后置求值点
    assert "t2_5_red_data_unresolved" not in early.get("trigger_conditions", []), \
        "R-1 回退：红数据触发项被塞回早期节点（时序上恒为假）"
    assert late.get("trigger_conditions") == ["t2_5_red_data_unresolved"], \
        f"R-1 回退：后置求值点触发项不符：{late.get('trigger_conditions')}"
    assert "brief_marked_Dxx_for_review" in early.get("trigger_conditions", []), \
        "早期节点丢了简报标记触发项"

    # ② 时序可达：完整性门 → 红数据求值点 → T4（三者严格递增）
    assert t2_5["phase_seq"] < late["phase_seq"] < t4["phase_seq"], (
        f"R-1 时序破损：t2_5={t2_5['phase_seq']} / 求值点={late['phase_seq']} / t4={t4['phase_seq']}")
    assert t2_5.get("next") == late["id"], f"t2_5 未指向后置求值点：{t2_5.get('next')}"
    assert late.get("next") == "t4_analysis", f"后置求值点未指向 T4：{late.get('next')}"

    # ③ 报告后激活：只有后置求值点依赖 T2.5 判定落盘
    assert late.get("rerun_after_report") is True, "后置求值点缺 rerun_after_report（须在 T2.5 判定落盘后取数）"
    assert early.get("rerun_after_report") is not True, \
        "R-1 回退：早期节点仍标 rerun_after_report（其触发依据已是 Phase 0 简报，非下游报告）"

    # ④ 两条件均已接线到真源定义
    idx = yaml.safe_load(_read(PORDER / "index.yaml"))
    defs = idx.get("condition_definitions") or {}
    assert early.get("condition") in defs, f"早期节点条件键未定义：{early.get('condition')}"
    assert late.get("condition") in defs, f"后置求值点条件键未定义：{late.get('condition')}"
    print("  ✓ R-1: Phase 1.5 两求值点触发依据互斥 + 时序可达 + 条件接线正确")


def test_hash_mismatch_contract_is_fail_closed_and_cannot_slip():
    """`hash_mismatch` 与 `sha256_status` 必须 fail-closed（零 exec 前提下的幂等锚点）。

    为什么值得单独守：论衡零 exec，sha256 属**主人侧量值**，主控不计算。于是 `draft_ref_contract`
    的 hash_mismatch 分支是一个**从未被真实执行过**的分支——本仓容易犯的错是「声明了就算验证了」。
    本用例把三个不可让步的语义钉住：
      ① hash_mismatch 只能是 `stop_and_request_resync`（不得降级为 continue/proceed/忽略）；
      ② `unavailable` 不得被当作已核验（sha256_status 枚举必须显式包含 unavailable，
         且「unavailable ⇒ 不得判通过」这句话必须与契约同处，否则主控会把它当已验证）；
      ③ `required` 字段集含 sha256（否则幂等探测会静默失效）。
    """
    contract = yaml.safe_load(_read(PORDER / "current_draft_sync.yaml"))[0]["draft_ref_contract"]

    # ① hash_mismatch fail-closed
    assert contract.get("hash_mismatch") == "stop_and_request_resync", (
        f"hash_mismatch 降级：{contract.get('hash_mismatch')}（必须 stop_and_request_resync）")

    # ③ required 字段集含 sha256
    assert "sha256" in contract.get("required", []), "required 缺 sha256（幂等探测会静默失效）"

    # ② sha256_status 必须显式枚举 unavailable；且「unavailable ≠ 已核验」的口径必须在其**正式真源**在场。
    #   ⚠️ 载体纪律（2026-10-08 修正）：该边界**不在** current_draft_sync 切片里（切片只持有契约字段，
    #   且装配视图余量仅 38 B，塞不下判据正文）。其归约口径真源 = `状态归约契约.md`
    #   （关键协议.md「节点重入的幂等探测」指定该文件为归约口径真源）。
    #   早前版本误在切片里断言本判据，红了一次 —— 教训：断言先问「这条判据的正式真源在哪」。
    assert "unavailable" in str(contract.get("sha256_status")), \
        f"sha256_status 未枚举 unavailable：{contract.get('sha256_status')}"
    reduce_doc = _read(ROOT / "references" / "_shared" / "真源" / "状态归约契约.md")
    assert "pending_owner_verification" in reduce_doc and "不得判通过" in reduce_doc, \
        "状态归约契约.md 缺「sha256/指纹未回填 ⇒ pending_owner_verification + 不得判通过」" \
        "—— 该边界一旦消失，主控会把 unavailable 当已核验（假绿灯）"
    print("  ✓ hash_mismatch 契约 fail-closed 且 unavailable 不被当已核验")


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
