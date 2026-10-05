#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_t9b_optin_downgrade.py — T9b「默认触发 → opt-in」降级的机械锁（2026-10-05）。

背景（架构评审 v3 R2 附带裁决，主人指令「T9b 降级为 opt-in」）：
  T9b 节点经实测判定为低价值：① 扫描 `run/` 40+ 项目目录**零产出**（管线明显越过
  该位置而报告不存在）；② 产出无下游消费方（T8 / 交付说明 / status 皆不读，协议自承
  「不改变 T9 评分、不代替 T7、不自行触发修订、默认不入交付说明」）；③ 主控亲为 =
  重读定稿全文 ≈20k tokens 压在管线里最稀缺的 agent 上（方向与「落盘减负」纪律相反）。
  保留节点（三剧本有真实学术价值，对应投稿前 referee method review），但改为
  **默认不跑，冲刺投稿时由主人 Phase 0 勾选 `owner_stress_test_opt_in` 开启**。

本文件锁死四件事（防静默回潮到默认触发）：
  ① 切片极性 = opt-in（`default: opt_in` + condition 键 + 未触发留痕 + 无 opt_out）；
  ② 条件键在 index.yaml `condition_definitions` 登记（producer + marker 同族治理）；
  ③ 生产方载体（任务简报 lite / full）承载该键；
  ④ 反向注入（教训 #334）：把 default 改回 triggered ⇒ 判据必红。
"""
import copy
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SLICE = ROOT / "references" / "_shared" / "真源" / "phase-order" / "t9b_stress_test.yaml"
INDEX = ROOT / "references" / "_shared" / "真源" / "phase-order" / "index.yaml"
LITE = ROOT / "references" / "templates" / "任务简报-template-lite.md"
FULL = ROOT / "references" / "templates" / "任务简报-template.md"
COND_KEY = "owner_stress_test_opt_in"


def _slice_node():
    spec = yaml.safe_load(SLICE.read_text(encoding="utf-8"))
    assert isinstance(spec, list) and len(spec) == 1, "t9b 切片结构异常"
    return spec[0]


def _condition_defs():
    return yaml.safe_load(INDEX.read_text(encoding="utf-8")).get("condition_definitions") or {}


def _polarity_errors(node, condition_defs, lite_text, full_text):
    """T9b opt-in 极性判据（纯函数，便于反向注入）。"""
    errs = []
    if node.get("default") != "opt_in":
        errs.append(f"t9b default={node.get('default')!r}，应为 opt_in（默认不跑）")
    if node.get("opt_out"):
        errs.append("t9b 不应再声明 opt_out（opt-in 极性下 opt-out 无意义）")
    cond = node.get("condition")
    if not cond:
        errs.append("t9b 必须声明 condition（opt-in 触发键）")
    elif cond not in condition_defs:
        errs.append(f"t9b.condition={cond} 未在 condition_definitions 登记（规则 25 同族）")
    if not node.get("on_not_triggered"):
        errs.append("t9b 缺 on_not_triggered（未开启 ≠ 漏跑）")
    if not node.get("condition_undecidable"):
        errs.append("t9b 缺 condition_undecidable（规则 26）")
    if not node.get("contract_key_carriers"):
        errs.append("t9b 缺 contract_key_carriers（owner 节点契约键须有机械锚点载体）")
    if cond and cond not in lite_text:
        errs.append(f"契约键「{cond}」不在生产方 lite 简报")
    if cond and cond not in full_text:
        errs.append(f"契约键「{cond}」不在 full 简报")
    return errs


# ---------------- ①②③ 现状守卫 ----------------

def test_t9b_polarity_is_opt_in():
    """① 切片极性 = opt-in：default: opt_in + condition 键 + 未触发留痕 + 无 opt_out。"""
    errs = _polarity_errors(_slice_node(), _condition_defs(),
                            LITE.read_text(encoding="utf-8"),
                            FULL.read_text(encoding="utf-8"))
    assert errs == [], errs


def test_t9b_condition_registered_with_producer():
    """② 条件键在 condition_definitions 登记，producer_marker 真在生产方（规则 25 同族）。"""
    cdef = _condition_defs()[COND_KEY]
    assert cdef["requires"] == [COND_KEY]
    assert cdef["producer"] == "references/templates/任务简报-template-lite.md"
    assert cdef["producer_marker"] in (ROOT / cdef["producer"]).read_text(encoding="utf-8")


def test_t9b_opt_out_key_is_gone():
    """旧的 owner_stress_test_opt_out 键须全仓消失（防两套极性并存）。"""
    stale = "owner_stress_test_opt_out"
    for rel in ("references/_shared/真源/phase-order/index.yaml",
                "references/templates/任务简报-template.md",
                "references/templates/任务简报-template-lite.md",
                "references/agents/00-主控-扩展职责.md",
                "references/agents/09b-压力测试-owner.md",
                "references/_shared/真源/pressure-test-protocol.md"):
        assert stale not in (ROOT / rel).read_text(encoding="utf-8"), f"{rel} 残留旧 opt-out 键"


def test_t9b_brief_presents_as_optional():
    """③ 简报把 T9b 呈现为「默认关闭的可选项」，不再混在「默认启用项」里。"""
    full = FULL.read_text(encoding="utf-8")
    lite = LITE.read_text(encoding="utf-8")
    assert "默认关闭" in full and COND_KEY in full
    assert "默认不跑" in lite
    # 「默认启用项」组内不得再有 T9b（该组应恰为 T9 + 方法论留档两项）
    grp = full.split("▲ 默认启用项")[1].split("目标篇幅")[0]
    assert "压力测试" not in grp, "T9b 仍混在「默认启用项」组（应移入可选项组）"


# ---------------- ④ 反向注入（判据必须会红） ----------------

def test_detector_catches_revert_to_default_triggered():
    """把 default 改回 triggered ⇒ 判据必红（防静默回潮，教训 #334）。"""
    node = copy.deepcopy(_slice_node())
    node["default"] = "triggered"
    node.pop("condition", None)
    errs = _polarity_errors(node, _condition_defs(), "", "")
    assert any("应为 opt_in" in e for e in errs), errs
    assert any("必须声明 condition" in e for e in errs), errs


def test_detector_catches_missing_carrier_anchor():
    """生产方载体丢键 ⇒ 判据必红（契约断链）。"""
    node = _slice_node()
    errs = _polarity_errors(node, _condition_defs(), "压力测试轮：默认触发", "")
    assert any("不在生产方 lite 简报" in e for e in errs), errs
    assert any("不在 full 简报" in e for e in errs), errs
