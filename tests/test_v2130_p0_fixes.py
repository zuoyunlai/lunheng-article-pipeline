#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_v2130_p0_fixes.py — v2.13.0 P0 三项修订回归门（ECS 实战反馈闭环）

背景（2026-09-24 ECS 实战项目 lunheng-un-veto-russia-ukraine-2026 反馈；主人拍板三项合并 v2.13.0）：
  P0-1 T5 修订轮新增引用标「待人工核验」而 T1 已结束 ⇒ 系统性核验缺口
       → 新增 Phase 4.3 `t1b_targeted_review`（T1b 定向回查，≤2 轮，耗尽主人三选一）
  P0-2 G14 旧轻量复检只扫修订片段，实测「路径」残留 11 处
       → 复检严格度档：全文词表计数，回环 ≤2 轮（`style_recheck_rounds_max: 2`）
  P0-3 [D21-D28] 合并引用（8 条数据点共用一个出处）
       → 引用编号独立性 + 出处可验证性（DOI/URL/出版信息）铁律入三张角色卡

本文件锁死三项修订的机械锚点（防回退）；口径真源 = phase-order.yaml + 各角色卡/gate 文件。
"""
import importlib.util  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).parent.parent


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


flow_check = _load(ROOT / "scripts" / "flow-check.py", "flow_check_2130")  # 复用真源解析器，防第二套 YAML 读法

import yaml  # noqa: E402

YAML_REL = "references/_shared/真源/phase-order.yaml"
D = yaml.safe_load((ROOT / YAML_REL).read_text(encoding="utf-8"))
PIPE = {n["id"]: n for n in D["pipeline"]}


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _node(nid: str) -> dict:
    assert nid in PIPE, f"{nid} 不在 pipeline（v2.13.0 P0-1 修订被回退？）"
    return PIPE[nid]


# ---------------- P0-1：t1b_targeted_review 节点 ----------------

def test_t1b_node_declared():
    """Phase 4.3 定向回查节点存在且关键字段齐全（kind/condition/上限/出口/产物）。"""
    n = _node("t1b_targeted_review")
    assert n["phase_seq"] == 14, "t1b phase_seq 应为 14（audit_revision 之后、t7_5_integrity 之前）"
    assert n["kind"] == "conditional_agent"
    assert n["condition"] == "t5_t7_report_unverified_references"
    assert n["on_not_triggered"] == "record_not_triggered_in_status"
    assert n["max_rounds"] == 2, "t1b 回查上限必须 ≤2 轮"
    assert n["next"] == "t7_5_integrity"
    assert n["output"] == "literature/回查报告-v{N}.md"
    assert n.get("input"), "t1b 必须声明 input（执行类节点门）"


def test_t1b_exhausted_outlet_three_choice():
    """轮次耗尽出口 = 主人三选一，无默认、fail-closed（写法同 audit_revision M-6）。"""
    outlet = _node("t1b_targeted_review")["rounds_exhausted_outlet"]
    ids = {c["id"] for c in outlet["owner_decision"]}
    assert ids == {"accept_with_limitations", "manual_verify", "remove_references"}
    assert outlet["no_default_option"] is True
    assert outlet["halt_pending_owner"] is True


def test_t1b_condition_registered_with_producer():
    """触发条件键在 condition_definitions 登记生产方，且 marker 真存在于写手卡（R-4 同型断链治理）。"""
    cdef = D["condition_definitions"]["t5_t7_report_unverified_references"]
    assert cdef["producer"] == "references/agents/05-写作-writer.md"
    assert cdef["producer_marker"] == "待人工核验"
    assert "待人工核验" in _read(cdef["producer"]), "写手卡缺「待人工核验」标记生产面"


def test_t1b_role_reuse_t1_card_and_dispatch():
    """T1b 复用 T1 角色卡（九角色架构不变）+ 派发话术文件存在且入打包清单。"""
    assert _node("t1b_targeted_review")["role"] == "T1"
    t1b_dispatch = ROOT / "references/dispatch/T1b-定向回查.md"
    assert t1b_dispatch.exists(), "dispatch/T1b-定向回查.md 缺失"
    manifest = _read("scripts/.pkg-manifest.txt")
    assert "references/dispatch/T1b-定向回查.md" in manifest, "T1b 派发话术未入打包清单"


def test_canary_has_t1b_row():
    """全景唯一派生视图承载 t1b 行 + 节点计数 24。"""
    t = _read("references/_shared/真源/pipeline-overview.md")
    assert "t1b_targeted_review" in t, "全景缺 t1b 行（R-1 漂移）"
    assert "共 24 节点" in t


def test_mirrors_no_stale_node_count():
    """镜像文档不得残留「23 节点」旧计数（R-1 指针 + 计数同步）。"""
    for rel in D["panorama_sources"]["mirrors"]:
        assert "23 节点" not in _read(rel), f"{rel} 残留旧节点计数"


def test_brief_template_supports_lxx_review():
    """任务简报待复核段支持 [Lxx] 文献级标记（Phase 1.5 触发面扩展）。"""
    t = _read("references/templates/任务简报-template.md")
    assert "待复核关键 Dxx / Lxx" in t
    assert "[Lxx] 文献描述" in t


def test_phase15_trigger_includes_lxx():
    """phase1_5 trigger_conditions 含 brief_marked_Lxx_for_review。"""
    trig = _node("phase1_5_targeted_review")["trigger_conditions"]
    assert "brief_marked_Lxx_for_review" in trig


# ---------------- P0-2：G14 复检严格度档 ----------------

def test_g14_style_recheck_rounds_max_in_yaml():
    """t5_style_revision.style_recheck_rounds_max = 2（复检回环上限入真源）。"""
    assert _node("t5_style_revision")["style_recheck_rounds_max"] == 2


def test_g14_gate_strict_recheck_mode():
    """gate §四 复检严格度档：全文扫描 + 词表计数 + 收敛判据 + 轮次上限 + 三选一。"""
    t = _read("references/gates/14-中文AI痕迹-gate.md")
    for token in ("复检严格度档", "扫描对象 = 修订后全文", "全文词表计数",
                  "收敛判据", "回环上限 ≤ 2 轮", "主人三选一"):
        assert token in t, f"gate 文件缺「{token}」（P0-2 复检严格度被回退？）"


def test_g14_recheck_drift_anchors():
    """复检口径漂移锚：关键派生文档统一为「全文复检 ≤2 轮」表述（防单点改、多点漏）。"""
    anchors = {
        "references/dispatch/G14-中文AI痕迹检测器.md": "复检 ≤2 轮",
        "references/templates/G14检测报告-template.md": "复检 ≤2 轮",
        "references/templates/status-template.md": "复检 ≤2 轮",
        "references/checkers/中文AI痕迹-checker.md": "复检 ≤2 轮",
        "references/agents/00-主控-扩展职责.md": "复检 ≤2 轮",
        "references/_shared/真源/glossary-core.md": "复检 ≤2 轮",
        "references/_shared/真源/关键协议.md": "复检 ≤2 轮",
        "references/_shared/真源/audit-checklist-quickref.md": "复检 ≤2 轮",
        "references/_shared/真源/asset-index.md": "复检 ≤2 轮",
    }
    for rel, token in anchors.items():
        assert token in _read(rel), f"{rel} 缺「{token}」（G14 复检口径漂移）"


# ---------------- P0-3：引用编号独立性 + 出处可验证性 ----------------

def test_writer_card_citation_discipline():
    """写手卡：修订轮新增引用核验纪律（待人工核验标记 + 禁区间/合并引用）。"""
    t = _read("references/agents/05-写作-writer.md")
    for token in ("修订轮新增引用核验纪律", "待人工核验", "禁止区间引用", "禁止合并引用"):
        assert token in t, f"写手卡缺「{token}」（P0-3 引用纪律被回退？）"


def test_t2_card_source_verifiability():
    """T2 卡 + 派发话术：出处可验证性（DOI 优先）+ 禁止合并出处。"""
    t = _read("references/agents/02-数据检索-data-scout.md")
    for token in ("出处可验证性", "DOI", "禁止合并出处"):
        assert token in t, f"T2 卡缺「{token}」"
    d = _read("references/dispatch/T2-数据检索.md")
    assert "出处独立可验证" in d and "DOI" in d, "T2 派发话术缺出处独立可验证条目"


def test_t7_card_reference_independence_check():
    """T7 卡：引用编号独立性核验（区间/合并引用 → P0）+ 待人工核验 grep 入报告。"""
    t = _read("references/agents/07-审计-auditor.md")
    for token in ("引用编号独立性核验", "区间引用", "合并引用", "t1b_targeted_review"):
        assert token in t, f"T7 卡缺「{token}」"


# ---------------- 附带修复：flow-check PATH_RE 版本占位 ----------------

def test_flow_check_path_re_handles_version_increment_placeholders():
    """PATH_RE 必须捕获 {N+1} 占位路径（规则 6/9 对修订产出节点的覆盖缺口，v2.13.0 修复）。"""
    hits = flow_check.PATH_RE.findall("drafts/初稿-v{N+1}.md + drafts/修订说明-v{N+1}.md")
    assert set(hits) == {"drafts/初稿-v{N+1}.md", "drafts/修订说明-v{N+1}.md"}
