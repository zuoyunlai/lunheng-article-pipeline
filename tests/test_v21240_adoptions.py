#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_v21240_adoptions.py — 四条「反向输入」采纳的机械门（2026-09-14，v2.12.40 候选）

背景：v2.12.40 采纳四条来自外部同族实现的可借鉴做法——
  ① 双字段 + 证伪证据（报告固定字段）
  ② 判定结果四档（替代「退出码」语义；路径/参数错误单独成档）
  ③ 「报告后激活」重跑时序
  ④ 机制保护人工化（机制面改动一律人工 approve，禁止自动合并）

这四条全是**判定口径**类改动，没有机械门就会静默漂移（教训 #36「改 A 漏 B」）。

设计原则：
  - 只验证「口径定义的结构一致性 + 分档语义」，不依赖真实 LLM 调用（对齐教训 #177）。
  - **正向/必中样本（教训 #334）**：门类判定口径改动必须配「应当放行」样本——
    不只断言文档里有这句话，还要构造「产物不存在」样本并断言它落在
    `path_or_param_error` 档、且该档**不触发内容修订轮**（= 应当放行，不白烧一轮）。
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).parent.parent
PHASE_ORDER = ROOT / "references" / "_shared" / "phase-order.yaml"
MGATE = ROOT / "references" / "_shared" / "M-Gate-Algorithm.md"
MGATE_APPENDIX = ROOT / "references" / "_shared" / "M-Gate-Algorithm-appendix.md"
PROTOCOL = ROOT / "references" / "_shared" / "关键协议.md"
PATH_SPEC = ROOT / "references" / "_shared" / "路径校验规范.md"
QUICKREF = ROOT / "references" / "_shared" / "audit-checklist-quickref.md"
COORDINATOR = ROOT / "references" / "agents" / "00-主控-扩展职责.md"
AUDITOR = ROOT / "references" / "agents" / "07-审计-auditor.md"
FINAL_INSPECTOR = ROOT / "references" / "agents" / "08-终检-final-inspector.md"

TIER_LABELS = {"pass": "通过", "fail": "不通过",
               "undecidable": "无法判定", "path_or_param_error": "路径或参数错误"}

# 依赖他角色报告落盘的节点（「报告后激活」适用面）
REPORT_DEPENDENT_CONDITIONAL = (
    "phase1_5_targeted_review", "t5_feedback_revision", "audit_revision",
)


def _read(p):
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _pipeline():
    return yaml.safe_load(PHASE_ORDER.read_text(encoding="utf-8"))


def _node(pid):
    return [n for n in _pipeline()["pipeline"] if n["id"] == pid][0]


# =============================================================================
# ① + ② 判定口径真源：四档定义（phase-order.yaml 为节点级真源）
# =============================================================================
def test_verdict_scale_has_exactly_four_tiers():
    """四档判定：恰好 4 档、标签与 id 一一对应（不得自创第五档）；名称→定义两层结构（P0-1 接线）"""
    vs = _pipeline()["verdict_scale"]
    assert "four_tier" in vs, "verdict_scale 缺 four_tier 名称定义（P0-1 接线回退为一层结构）"
    tiers = vs["four_tier"]["tiers"]
    assert len(tiers) == 4, f"档位数应为 4，实为 {len(tiers)}"
    got = {t["id"]: t["label"] for t in tiers}
    assert got == TIER_LABELS, f"档位 id/label 漂移: {got}"


def test_verdict_scale_flags_match_doctrine():
    """分档的处置语义：只有「不通过」触发修订；路径/参数错误是「非内容缺陷」；默认处置禁 fail-open"""
    four = _pipeline()["verdict_scale"]["four_tier"]
    by_id = {t["id"]: t for t in four["tiers"]}
    assert by_id["pass"]["blocks_pipeline"] is False
    assert by_id["fail"]["triggers_revision"] is True
    for tid in ("undecidable", "path_or_param_error"):
        assert by_id[tid]["triggers_revision"] is False, f"{tid} 不得触发内容修订轮"
        assert by_id[tid]["blocks_pipeline"] is True, f"{tid} 必须阻断（fail-closed）"
    assert by_id["path_or_param_error"]["not_content_defect"] is True
    dh = four.get("default_handling", {})
    assert set(dh) == {"pass", "fail", "undecidable", "path_or_param_error"}, \
        f"default_handling 四档必须全覆盖: {sorted(dh)}"
    assert dh.get("pass") == "continue_to_next"
    for tid in ("fail", "undecidable", "path_or_param_error"):
        assert dh.get(tid) != "continue_to_next", f"{tid} 默认处置 fail-open 放行"


def _classify(signals, tiers):
    """文档口径的可执行镜像：现象信号 → 档位（判定权仍属 LLM，此处只锁分档语义）"""
    if not signals.get("target_exists", True):
        return "path_or_param_error"
    if not signals.get("readable", True):
        return "undecidable"
    if signals.get("content_defects"):
        return "fail"
    return "pass"


def test_positive_sample_path_error_does_not_trigger_revision():
    """正向/必中样本（教训 #334）：产物不存在 = 路径或参数错误档，**应当放行**修订轮"""
    by_id = {t["id"]: t for t in _pipeline()["verdict_scale"]["four_tier"]["tiers"]}

    # 样本 1：定稿不存在 → 路径或参数错误（不是「不通过」）
    tier = _classify({"target_exists": False}, by_id)
    assert tier == "path_or_param_error", f"产物不存在被误分为 {tier}"
    assert by_id[tier]["triggers_revision"] is False, "路径错误不得触发内容修订轮"

    # 样本 2：读不出来 → 无法判定（不得升格为通过）
    assert _classify({"readable": False}, by_id) == "undecidable"

    # 样本 3：真有内容缺陷 → 不通过（该拦的必须拦住，防分档把真缺陷也放行）
    assert _classify({"content_defects": ["P1"]}, by_id) == "fail"

    # 样本 4：无缺陷 → 通过
    assert _classify({}, by_id) == "pass"


# =============================================================================
# ② + ③ 节点级落地：condition / mechanical_checkpoint 必声明口径与时序
# =============================================================================
def test_all_condition_and_mechanical_nodes_declare_verdict_scale():
    """凡有 condition 或 kind=mechanical_checkpoint 的节点必须声明 verdict_scale"""
    missing = []
    for n in _pipeline()["pipeline"]:
        if n.get("condition") or n.get("kind") == "mechanical_checkpoint":
            if n.get("verdict_scale") != "four_tier":
                missing.append(n["id"])
    assert not missing, f"未声明 verdict_scale: {missing}"


def test_report_dependent_nodes_declare_rerun_after_report():
    """「报告后激活」：前提为报告/产物落盘的节点必须 rerun_after_report: true"""
    bad = []
    for n in _pipeline()["pipeline"]:
        depends_on_report = (
            n.get("kind") == "mechanical_checkpoint"
            or n["id"] in REPORT_DEPENDENT_CONDITIONAL
            or n["id"] == "t8_technical_final"
        )
        if depends_on_report and n.get("rerun_after_report") is not True:
            bad.append(n["id"])
    assert not bad, f"未标注 rerun_after_report: {bad}"


def test_yaml_carries_rerun_doctrine_text():
    """时序要求必须在真源里成文（节点标注 + 总述两句都要在）"""
    doc = _pipeline()["verdict_scale"]["report_after_rerun_doctrine"]
    assert "报告落盘后重跑" in doc
    assert "不得直接当作闸门输入" in doc


# =============================================================================
# ① 双字段 + 证伪证据（算法文档 + 报告 schema）
# =============================================================================
def test_m_gate_doc_defines_dual_fields_and_falsification():
    doc = _read(MGATE)
    for field in ("原文值", "裁定值", "证伪依据"):
        assert field in doc, f"M-Gate 文档缺字段 {field}"
    assert "视为伪造报告" in doc, "缺「缺证伪三项 = 视为伪造报告」口径"
    assert "可复核判定协议" in doc
    assert "判定结果分档" in doc
    assert "报告后激活" in doc


def test_m_gate_doc_keeps_zero_exec_and_llm_authorship():
    """判定权仍在 LLM，不得因字段化引入运行时 shell / 脚本执行"""
    doc = _read(MGATE)
    assert "不引入任何运行时 shell 或脚本执行" in doc
    assert re.search(r"M 门.*LLM 推理", doc), "诚实声明（门 F 锚点）被破坏"


def test_appendix_schema_has_dual_field_records_and_no_exit_code():
    doc = _read(MGATE_APPENDIX)
    assert "判定记录_双字段" in doc
    for field in ("原文值", "裁定值", "证伪依据"):
        assert field in doc, f"appendix schema 缺字段 {field}"
    # 只在 **JSON 代码块内** 断言退出码字段已退出（说明句里引用旧写法是合法的）
    blocks = re.findall(r'```json\n(.*?)```', doc, re.S)
    assert blocks, "appendix 缺 JSON schema 代码块"
    schema = "\n".join(blocks)
    assert "退出码" not in schema, "JSON schema 仍在用退出码语义"
    assert "M门全exit0" not in schema, "M-Integrity-2 字段仍写 exit0"
    assert "判定档位" in schema, "JSON schema 缺「判定档位」四档字段"


def test_path_spec_maps_path_errors_to_own_tier():
    doc = _read(PATH_SPEC)
    assert "路径或参数错误" in doc
    assert "不得当作 P1 内容问题" in doc
    assert "路径或参数错误" in doc and "无法判定" in doc


# =============================================================================
# ④ 机制保护：机制面改动一律人工 approve
# =============================================================================
def test_protocol_defines_mechanism_protection():
    doc = _read(PROTOCOL)
    assert "机制保护" in doc
    assert "人工 approve" in doc and "禁止自动合并" in doc
    assert "最严重违规" in doc
    for obj in ("反哺报告", "角色卡", "机制文件"):
        assert obj in doc, f"保护面缺 {obj}"
    # 诚实边界：流程层约束，非工具层拦截 → 人工确认不可省
    assert "不是**工具层拦截" in doc.replace("不是 **工具层拦截", "不是**工具层拦截") or "工具层拦截" in doc
    assert "人工确认这一环不可省" in doc


def test_mechanism_protection_wired_into_cards_and_quickref():
    """改 A 漏 B 防线：口径既在协议真源，也必须在角色卡/速查的引用面出现"""
    coord = _read(COORDINATOR)
    assert "机制保护" in coord and "禁止自动合并" in coord
    assert "判定口径三条" in coord and "四档判定" in coord
    auditor = _read(AUDITOR)
    assert "机制保护" in auditor
    # 旧「exit 0」权威表述必须已退出终检卡（“不再用 exit 0 表述”的说明句允许保留）
    fin = _read(FINAL_INSPECTOR)
    assert "路径或参数错误" in fin and "四档判定" in fin
    assert "M 门 exit ≠ 0" not in fin and "M 门 exit 0" not in fin
    qk = _read(QUICKREF)
    assert "判定结果分档" in qk and "报告后激活" in qk and "可复核判定协议" in qk
