#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_e1_3_feedback_fixes.py — E1-3 微型实测反哺修订回归门（v2.13.2 批次）

背景：E1-3 微型实测（run/first-degree-screening-2026，2026-09-25）暴露 6 类缺陷，
反哺建议已落入活文档。本测试机械锁死 6 条建议的**落地痕迹**，防后续编辑漂移回旧约定：

  R1 登记表 per-role 分片 + 追加式写入（治 D-1 并行整文件覆盖）
  R2 ClaimEvidenceLink 强制回写 + T7/T8 否决项（治 D-4 单表闭环未达成）
  R3 重量档拆段增量落盘（D-2）+ 修订轮定点 edit 禁整文件重写（D-3）
  R4 completion event Stats line 缺口处置（子代理 token 连续多轮缺失）
  R5 performance-benchmarks 增补 E1-3 实测行
  R6 报告模板区分 bytes / chars + 字数判定表补组装口径备注

  §反向注入：从 tmp 副本抽掉任一规则标记 ⇒ 校验器必须报红（真源零写入）。
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# 规则标记表：相对路径 -> 必须出现的标记（缺一即该条反哺落地不完整）
RULES = {
    "references/_shared/真源/evidence-object-model.md": (
        "唯一生产者 = 主控（T0）",
        "evidence-register-<角色号>.md",
        "主张关系的强制回写",
        "否决项（T7/T8）",
    ),
    "references/templates/evidence-register-template.md": ("## 分片（v2.13.2", "分片齐全性"),
    "references/templates/claim-evidence-map-template.md": ("回写义务（v2.13.2",),
    "references/agents/01-文献检索-literature-scout.md": ("分片纪律（v2.13.2",),
    "references/agents/03-案例检索-case-scout.md": ("分片纪律（v2.13.2",),
    "references/agents/04-分析-analyst.md": ("回写义务（v2.13.2",),
    "references/agents/07-审计-auditor.md": ("分片齐全性", "ClaimEvidenceLink"),
    "references/agents/08-终检-final-inspector.md": ("分片齐全性", "ClaimEvidenceLink"),
    "references/agents/05-写作-writer.md": ("长文分段与增量落盘", "修订轮的定点编辑纪律"),
    "references/dispatch/T1-文献检索.md": ("本角色分片",),
    "references/dispatch/T3-案例检索.md": ("本角色分片",),
    "references/dispatch/T4-分析.md": ("回写义务（v2.13.2",),
    "references/dispatch/T5-写手.md": ("定点编辑纪律（v2.13.2", "长文分段与增量落盘（v2.13.2"),
    "references/dispatch/T7-审计.md": ("分片齐全性",),
    "references/dispatch/T8-终检.md": ("分片齐全性",),
    "references/_shared/真源/dispatch-header.md": ("Stats line 缺口处置",),
    "references/_shared/真源/performance-benchmarks.md": ("first-degree-screening-2026",),
    "references/_shared/真源/字数判定表.md": ("备注 5（v2.13.2", "备注 6（v2.13.2"),
    "references/templates/交接报告-template.md": ("文件系统字节数",),
    "references/templates/审稿报告-template.md": ("文件系统字节数",),
}


def scan(root=ROOT, overrides=None):
    """返回违规列表；overrides: {相对路径: 文本} 用于注入测试（不落盘）。"""
    overrides = overrides or {}
    bad = []
    for rel, markers in RULES.items():
        p = pathlib.Path(root) / rel
        if rel in overrides:
            text = overrides[rel]
        elif p.is_file():
            text = p.read_text(encoding="utf-8")
        else:
            bad.append(rel + " : 文件不存在")
            continue
        for m in markers:
            if m not in text:
                bad.append(rel + " : 缺标记 " + m)
    return bad


def test_e1_3_feedback_fixes_all_present():
    bad = scan()
    assert not bad, "E1-3 反哺修订落地不完整：%s" % bad


def test_rule_table_covers_all_six_recommendations():
    keys = set(RULES)
    for rel in (
        "references/_shared/真源/evidence-object-model.md",   # R1/R2
        "references/agents/05-写作-writer.md",                 # R3
        "references/_shared/真源/dispatch-header.md",          # R4
        "references/_shared/真源/performance-benchmarks.md",   # R5
        "references/templates/交接报告-template.md",            # R6
    ):
        assert rel in keys, "回归表未覆盖反哺建议目标文件：" + rel


def test_injection_stripping_partition_rule_is_caught():
    """抽掉真源里的分片写入纪律 ⇒ 校验器报红（防规则被静默删回旧约定）。"""
    rel = "references/_shared/真源/evidence-object-model.md"
    text = (ROOT / rel).read_text(encoding="utf-8")
    assert "唯一生产者 = 主控（T0）" in text
    mutated = text.replace("唯一生产者 = 主控（T0）", "唯一生产者 = 主控", 1)
    bad = scan(overrides={rel: mutated})
    assert bad and any("唯一生产者" in b for b in bad), "分片纪律被删未被检出：%s" % bad


def test_injection_stripping_writeback_veto_is_caught():
    """抽掉 T7 卡的 ClaimEvidenceLink 否决项标记 ⇒ 校验器报红。"""
    rel = "references/agents/07-审计-auditor.md"
    text = (ROOT / rel).read_text(encoding="utf-8")
    mutated = text.replace("ClaimEvidenceLink", "核心主张关系", 1)
    bad = scan(overrides={rel: mutated})
    assert bad and any("ClaimEvidenceLink" in b for b in bad), "回写否决项被删未被检出：%s" % bad


def test_truth_source_not_modified_by_scan():
    """护栏：扫描与注入均为只读/内存变异，真源 sha256 前后一致。"""
    import hashlib
    rel = "references/_shared/真源/evidence-object-model.md"
    before = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    scan(overrides={rel: "空文本"})
    after = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    assert before == after, "扫描污染了真源"
