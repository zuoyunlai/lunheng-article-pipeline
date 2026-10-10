#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_run_mode.py — 运行模式（run_mode）特性的机械锁（v2.18.0）。

背景（业主定案 2026-10-10：Phase 0 二选一——全自动流水线（推荐）/ 人在四环）：
  全自动 = Phase 0 一次性预授权，四例行拍板（2.5/3.5/5 + 图位按推荐）自动落**合法枚举值**；
  质量门 / 审计 / 同行评审照跑，异常三选照停。唯一真源 = 运行模式对照表.md。

架构边界（台账 §四-3 铁律）：phase-order 状态机（index.yaml / 装配视图 / 四节点切片）
**零改动**——run_mode 机制全部沉入旁侧真源（对照表）+ 接线面（关键协议 / status-template /
checkpoint 卡 / 两级任务简报）。本文件锁死十件事（防漂移 / 防回潮 / 防 fail-open 扩大化）：
  ① 三值枚举四载体一致（status-template / 简报 full+lite / 对照表）；
  ② 对照表 §3 自动落值 ∈ 对应节点切片 decisions 词表（防自创字面值，v2.12.61）；
  ③ silence_doctrine.forbidden_kinds 未被改动（预授权 ≠ auto_continue 的机械面）；
  ④ 生产方载体（任务简报 full）承载「运行模式」marker（条件键登记已按铁律撤出 index.yaml）；
  ⑤ 运行性质三处披露载体均含「生产·全自动」（T8 机械核对的文本面存在）；
  ⑥ 可发表性 3.4 人类决策判据已扩「预授权」（M-2 闭合）；
  ⑦ counts.yaml version_files == check-version.sh CHECKS 实测条目数；
  ⑧ .pkg-manifest.txt / sync-version.sh 登记运行模式对照表.md（净化包 + 版本头一致性）；
  ⑨ 投稿版禁入清单均已扩「全自动模式披露」（防复制漂移）；
  ⑩ 对照表停点键名与 27 节点矩阵对得上 phase-order 真源（防键名/节点漂移）。
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
TRUTH = ROOT / "references" / "_shared" / "真源"
INDEX = TRUTH / "phase-order" / "index.yaml"
STATUS_TPL = ROOT / "references" / "templates" / "status-template.md"
BRIEF_FULL = ROOT / "references" / "templates" / "任务简报-template.md"
BRIEF_LITE = ROOT / "references" / "templates" / "任务简报-template-lite.md"
CARD = ROOT / "references" / "templates" / "checkpoint-card-template.md"
MODE_TABLE = TRUTH / "运行模式对照表.md"
MANIFEST = ROOT / "scripts" / ".pkg-manifest.txt"
COUNTS = TRUTH / "counts.yaml"

MODE_VALUES = {"生产·人在四环", "生产·全自动", "测试模式"}


def _index():
    return yaml.safe_load(INDEX.read_text(encoding="utf-8"))


def _slice(node_id):
    p = TRUTH / "phase-order" / f"{node_id}.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))[0]


def test_mode_values_consistent_across_carriers():
    """三值枚举在各载体一致（多一个少一个/写法漂移都算红）。"""
    st = STATUS_TPL.read_text(encoding="utf-8")
    full = BRIEF_FULL.read_text(encoding="utf-8")
    lite = BRIEF_LITE.read_text(encoding="utf-8")
    table = MODE_TABLE.read_text(encoding="utf-8")
    for v in MODE_VALUES:
        assert v in st, f"status-template 缺运行模式值 {v}"
        assert v in full, f"任务简报 full 缺 {v}"
        assert v in lite, f"任务简报 lite 缺 {v}"
        assert f"`{v}`" in table, f"对照表 §1 三值表缺 {v}"
    # phase-order 状态机保持零改动（架构边界，防有人把 run_mode 塞回棘轮文件）
    assert "run_mode:" not in _index(), "index.yaml 出现 run_mode 契约键（台账 §四-3 铁律：状态机不受理）"


def test_table_auto_decisions_stay_in_node_enum():
    """对照表 §3 的自动落值必须 ∈ 对应节点切片 decisions 词表（禁自创字面值）。"""
    table = MODE_TABLE.read_text(encoding="utf-8")
    # §3 表格行形态：| `phase2_5_outline` | `approved` | ...
    rows = re.findall(r"^\| `([a-z0-9_]+)` \| `([a-z_]+)` \|", table, re.M)
    got = dict(rows)
    assert got.get("phase2_5_outline") == "approved", f"2.5 自动落值漂移: {got}"
    assert got.get("phase3_5_insight") == "no_insight", f"3.5 自动落值漂移: {got}"
    assert got.get("phase5_acceptance") == "accepted", f"5 自动落值漂移: {got}"
    for node_id, decision in got.items():
        node = _slice(node_id)
        assert decision in node["decisions"], (
            f"{node_id}: 对照表自动落值 {decision!r} 不在 decisions={node['decisions']}"
            "（自创字面值，违 v2.12.61）"
        )
    # 切片本体不得出现 run_mode_auto（架构边界）
    for node_id in got:
        assert "run_mode_auto" not in (TRUTH / "phase-order" / f"{node_id}.yaml").read_text(encoding="utf-8"), (
            f"{node_id}: 切片出现 run_mode_auto（应沉对照表，台账铁律）"
        )


def test_silence_doctrine_forbidden_kinds_untouched():
    """silence_doctrine.forbidden_kinds 未变——预授权扩展绝不允许写成自动继续。"""
    sd = _index()["silence_doctrine"]
    assert sd["invariant"] == "silence_is_not_valid_decision"
    assert set(sd["forbidden_kinds"]) == {"auto_continue", "silent_proceed", "degrade_and_continue"}
    assert set(sd["halt_kinds"]) == {"pending_owner_halt"}
    assert "run_mode" not in (sd.get("applies_to") or [])


def test_producer_carries_run_mode_marker():
    """生产方载体（简报 full）承载「运行模式」字段与结构化 run_mode 块。"""
    full = BRIEF_FULL.read_text(encoding="utf-8")
    assert "运行模式" in full, "简报 full 缺「运行模式」字段"
    assert "run_mode:" in full, "简报 full 缺结构化 run_mode 记录块"
    assert "preauthorized_nodes" in full, "简报 full 缺 preauthorized_nodes 留痕字段"
    # 不答 ≠ 全自动（fail-closed 口径必须随字段出现）
    assert "不答" in full and ("pending_owner_halt" in full or "不推进" in full)


def test_three_carrier_disclosure_texts_present():
    """T8 dispatch / deliverables / status-template 三处披露文本均含「生产·全自动」。"""
    t8 = (ROOT / "references" / "dispatch" / "T8-终检.md").read_text(encoding="utf-8")
    dl = (ROOT / "references" / "deliverables.md").read_text(encoding="utf-8")
    st = STATUS_TPL.read_text(encoding="utf-8")
    for name, text in (("T8-终检", t8), ("deliverables", dl), ("status-template", st)):
        assert "生产·全自动" in text, f"{name} 缺三处披露口径（生产·全自动）"
    # T8 另核对四项（预授权 basis / decision 落值 / preauthorized 留痕 / AI 声明）
    assert "预授权 basis" in t8, "T8 缺生产·全自动四项核对第①项"
    # status-template 呈现枚举含 preauthorized（仅本模式合法）
    assert "preauthorized" in st, "status-template 缺 checkpoint_status=preauthorized 枚举"


def test_publishability_34_covers_preauthorization():
    """可发表性 3.4 人类决策判据已扩预授权说明（M-2 闭合）。"""
    pub = (TRUTH / "可发表性判定表.md").read_text(encoding="utf-8")
    line34 = [l for l in pub.splitlines() if l.startswith("| 3.4 |")]
    assert line34, "可发表性 3.4 行丢失"
    assert "预授权" in line34[0], "3.4 判据未扩「预授权说明」"
    assert "预授权记录缺失" in pub, "§6.1 缺预授权缺失兜底（不得自动接受）"


def test_version_files_count_matches_check_matrix():
    """counts.version_files == check-version.sh CHECKS 矩阵实测条目数（contract-check 同口径）。"""
    counts = yaml.safe_load(COUNTS.read_text(encoding="utf-8"))
    script = (ROOT / "scripts" / "check-version.sh").read_text(encoding="utf-8")
    measured = len(re.findall(r'^\s*"[^"|]+\|v\$EXPECTED\|1"', script, re.M))
    assert measured == counts["version_files"], (
        f"version_files: counts.yaml={counts['version_files']} but check-version.sh has {measured}"
    )
    assert '"_shared/真源/运行模式对照表.md|v$EXPECTED|1"' in script


def test_manifest_registers_mode_table():
    """净化包清单 + 版本头同步面登记运行模式对照表.md。"""
    lines = MANIFEST.read_text(encoding="utf-8").splitlines()
    assert "references/_shared/真源/运行模式对照表.md" in [l.strip() for l in lines]
    sync = (ROOT / "scripts" / "sync-version.sh").read_text(encoding="utf-8")
    assert "_shared/真源/运行模式对照表.md|header" in sync


def test_submission_banned_list_expanded():
    """投稿版禁入清单均已扩「全自动模式披露」（防复制漂移）。"""
    dl = (ROOT / "references" / "deliverables.md").read_text(encoding="utf-8")
    inspector = (ROOT / "references" / "agents" / "08-终检-final-inspector.md").read_text(encoding="utf-8")
    pub = (TRUTH / "可发表性判定表.md").read_text(encoding="utf-8")
    for name, text in (("deliverables", dl), ("08-终检", inspector)):
        for line in text.splitlines():
            if "测试模式披露" in line:
                assert "全自动模式披露" in line, f"{name} 禁入清单行未同步扩全自动: {line[:60]}"
    a1 = [l for l in pub.splitlines() if l.startswith("| A1 |")]
    assert a1 and "全自动模式披露" in a1[0], "可发表性 A1 行未扩全自动模式披露"
    # AI 声明（投稿版正式章节）必须保留预授权说明——禁入清单管头部工程元数据，二者不冲突
    assert "预授权说明" in pub, "AI 声明判据缺预授权说明（诚实披露面）"


def test_mode_table_halt_list_and_node_matrix_match_truth():
    """对照表停点键名与 27 节点矩阵对得上 phase-order 真源（防键名/节点漂移）。"""
    idx_text = INDEX.read_text(encoding="utf-8")
    table = MODE_TABLE.read_text(encoding="utf-8")
    for key in ("provider_silence_escalation", "owner_timeout_policy", "silence_doctrine"):
        assert key in idx_text, f"index.yaml 缺真源键 {key}（前置损坏）"
        assert key in table, f"对照表缺停点键 {key}"
    routing = _index()["nodes"]
    missing = [r["node"] for r in routing if r["node"] not in table]
    assert not missing, f"对照表 27 节点矩阵缺: {missing}"


def test_checkpoint_card_short_circuit_protocol():
    """呈现层短路协议第 0 步在卡（生产·全自动不呈现、备案通知、fail-closed 回退）。"""
    card = CARD.read_text(encoding="utf-8")
    assert "生产·全自动短路" in card, "checkpoint 卡缺短路协议第 0 步"
    assert "备案通知" in card, "短路协议缺备案通知口径"
    assert "按人在四环呈现卡" in card, "短路协议缺 fail-closed 回退"
    assert "不新增 decision 字面值" in card, "Phase 0 选项缺 v2.12.61 纪律注记"
