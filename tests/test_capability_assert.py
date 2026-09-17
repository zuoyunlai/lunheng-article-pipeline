#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_capability_assert.py — 权限口径一致性测试（v2.12.30 新增）

背景（2026-09-12 第三方全量审计 P0-1）：
  SKILL.md frontmatter `denied` 声明禁用 memory_store / memory_forget / sessions_search，
  但 scripts/capability-assert.py 把它们列入 ALLOWED_CAPABILITIES 且判定只查
  FORBIDDEN_CAPABILITIES → 文档声明禁用、脚本实际放行（假绿灯）。

本测试锁死「声明 vs 执行体」：
  - 声面真交集：允许档 ∩ denied = ∅（不减法，可判红）
  - 派生集 == 真源现算期望集（防派生集自身被改坏后断言真空）
  - frontmatter denied 的每一项都必须被断言脚本拒绝
  - 合法能力仍可通过（防修过头）
  - 反向注入：四类破坏都必须让 --selfcheck 变红（v2.12.50，教训 #399）
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


def test_declared_surface_disjoint_from_denied():
    """声面真交集：允许档与 denied 不得同时声明同一能力（**不做减法**）

    v2.12.50：原测试取 `SKILL_DENIED & ALLOWED_CAPABILITIES`，而 ALLOWED 定义时已减去
    FORBIDDEN（⊇ denied）⇒ 交集数学上恒空，属**空转断言**（教训 #399）。
    """
    overlap = CAS.SKILL_DECLARED & CAS.SKILL_DENIED
    assert not overlap, f"同一能力同时出现在允许档与 denied: {sorted(overlap)}"


def test_readonly_extras_disjoint_from_forbidden():
    """只读宿主扩展不得与禁用面冲突（否则会被静默减法吞掉，无从察觉）"""
    forbidden = CAS.SKILL_DENIED | CAS.HARD_FORBIDDEN
    overlap = CAS.HOST_READONLY_EXTRAS & forbidden
    assert not overlap, f"只读宿主扩展与禁用面冲突: {sorted(overlap)}"


def test_derived_sets_match_truth_source():
    """派生集必须等于由真源现算的期望集

    防「派生集自身被改坏」⇒ 所有挂派生集的断言全部真空仍报绿。
    """
    expected_forbidden = CAS.SKILL_DENIED | CAS.HARD_FORBIDDEN
    expected_allowed = (CAS.SKILL_DECLARED | CAS.HOST_READONLY_EXTRAS) - expected_forbidden
    assert CAS.FORBIDDEN_CAPABILITIES == expected_forbidden, "禁用面派生集与真源不一致"
    assert CAS.ALLOWED_CAPABILITIES == expected_allowed, "允许面派生集与真源不一致"


def test_selfcheck_goes_red_on_injection():
    """反向注入（教训 #399「机械门必须能红」）：三类破坏都必须让 selfcheck 变红"""
    keys = ('SKILL_DENIED', 'SKILL_DECLARED', 'HOST_READONLY_EXTRAS',
            'FORBIDDEN_CAPABILITIES', 'ALLOWED_CAPABILITIES', 'validate_capabilities')
    saved = {k: getattr(CAS, k) for k in keys}
    cap = sorted(CAS.SKILL_DENIED)[0]

    def run_injected(fn):
        try:
            fn()
            return CAS.selfcheck()
        finally:
            for k, v in saved.items():
                setattr(CAS, k, v)

    def inj_declared_overlap():
        CAS.SKILL_DECLARED = saved['SKILL_DECLARED'] | {cap}
        CAS.ALLOWED_CAPABILITIES = saved['ALLOWED_CAPABILITIES'] | {cap}
    assert run_injected(inj_declared_overlap) != 0, 'selfcheck 未检出「denied 进允许档」'

    def inj_forbidden_lost():
        CAS.FORBIDDEN_CAPABILITIES = set()
        CAS.ALLOWED_CAPABILITIES = saved['SKILL_DECLARED'] | saved['HOST_READONLY_EXTRAS']
    assert run_injected(inj_forbidden_lost) != 0, 'selfcheck 未检出「禁用面派生集被清空」'

    def inj_denied_empty():
        CAS.SKILL_DENIED = set()
        CAS.FORBIDDEN_CAPABILITIES = set(CAS.HARD_FORBIDDEN)
        CAS.ALLOWED_CAPABILITIES = saved['SKILL_DECLARED'] | saved['HOST_READONLY_EXTRAS']
    assert run_injected(inj_denied_empty) != 0, 'selfcheck 未检出「denied 清单为空」'

    def inj_always_reject():
        def _reject(role, caps):
            raise CAS.CapabilityAssertionError('injected')
        CAS.validate_capabilities = _reject
    assert run_injected(inj_always_reject) != 0, 'selfcheck 未检出「验证器一律拒绝」（反向假绿灯）'

    # 收尾：注入全部回退后基线必须仍绿
    assert CAS.selfcheck() == 0


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
