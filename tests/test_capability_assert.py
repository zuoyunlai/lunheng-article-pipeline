#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_capability_assert.py — 权限口径一致性测试（v2.12.30 新增）

背景（2026-09-12 第三方全量审计 P0-1）：
  SKILL.md frontmatter `denied` 声明禁用 memory_store / memory_forget / sessions_search，
  但 scripts/capability-assert.py 把它们列入 ALLOWED_CAPABILITIES 且判定只查
  FORBIDDEN_CAPABILITIES → 文档声明禁用、脚本实际放行（假绿灯）。

本测试锁死「声明 vs 执行体」：
  - 允许面 ∩ 禁用面 = ∅
  - frontmatter denied 的每一项都必须被断言脚本拒绝
  - 合法能力仍可通过（防修过头）
"""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
CAS_PATH = ROOT / "scripts" / "capability-assert.py"


def _load():
    spec = importlib.util.spec_from_file_location("capability_assert", CAS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CAS = _load()

# P0-1 点名能力：这三项曾同时出现在 denied 与允许白名单
REGRESSION_DENIED = ["memory_store", "memory_forget", "sessions_search"]

# 合法能力抽样（每个角色类型一个）
LEGIT = ["read", "write", "edit", "web_search", "tavily_search", "ask_user",
         "ov_search", "ov_read", "sessions_spawn"]


def test_denied_and_allowed_disjoint():
    """允许面与禁用面必须零交集（denied 永不失效）"""
    overlap = CAS.SKILL_DENIED & CAS.ALLOWED_CAPABILITIES
    assert not overlap, f"denied 能力出现在允许面: {sorted(overlap)}"


def test_allowed_and_forbidden_disjoint():
    """ALLOWED_CAPABILITIES ∩ FORBIDDEN_CAPABILITIES = ∅"""
    overlap = CAS.ALLOWED_CAPABILITIES & CAS.FORBIDDEN_CAPABILITIES
    assert not overlap, f"允许面含禁用能力: {sorted(overlap)}"


def test_frontmatter_denied_all_rejected():
    """frontmatter denied 的每一项都必须被拒绝（逐项回归）"""
    accepted = []
    for cap in sorted(CAS.SKILL_DENIED):
        try:
            CAS.validate_capabilities("T0", ["read", cap])
        except CAS.CapabilityAssertionError:
            continue
        accepted.append(cap)
    assert not accepted, f"以下 denied 能力被放行: {accepted}"


def test_p0_regression_three_capabilities_rejected():
    """P0-1 点名：memory_store / memory_forget / sessions_search 必须被拒"""
    for cap in REGRESSION_DENIED:
        assert cap in CAS.SKILL_DENIED, f"{cap} 不在 frontmatter denied 中（真源被改？）"
        try:
            CAS.validate_capabilities("T5", ["read", cap])
        except CAS.CapabilityAssertionError:
            continue
        raise AssertionError(f"denied 能力 {cap} 被 capability-assert.py 放行")


def test_legit_capabilities_still_pass():
    """合法能力仍可通过（防修过头把正常能力误杀）"""
    for cap in LEGIT:
        CAS.validate_capabilities("T5", ["read", cap])


def test_hard_forbidden_extras():
    """硬禁用面（secrets / gateway / automations）不得出现在允许面"""
    for cap in ("secrets", "gateway", "automations"):
        assert cap in CAS.FORBIDDEN_CAPABILITIES
        assert cap not in CAS.ALLOWED_CAPABILITIES


def test_selfcheck_exit_zero():
    """--selfcheck 真源自检通过"""
    assert CAS.selfcheck() == 0


def test_unknown_capability_rejected():
    """未知能力仍被拒（白名单机制未退化）"""
    try:
        CAS.validate_capabilities("T5", ["read", "definitely_not_a_tool"])
    except CAS.CapabilityAssertionError:
        return
    raise AssertionError("未知能力未被拒绝")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ✓ {name}")
    print("capability-assert 测试全过")
