#!/usr/bin/env python3
"""capability-assert.py — 论衡能力断言脚本（响应腾讯 A.I.G 审计 Remediation #6）

用途：
- 在 spawn 子代理前，断言所需能力可用
- 拒绝高风险能力
- 为角色分配最小必要能力集

调用：
    python3 scripts/capability-assert.py <role> <capability1> <capability2> ...

返回：
    - exit 0：所有能力均合法
    - exit 1 + stderr：发现禁用能力或无效能力

示例：
    $ python3 scripts/capability-assert.py T1 read web_search tavily_search
    ✅ Role T1: All capabilities valid (3 total)

    $ python3 scripts/capability-assert.py T5 read write exec
    Error: Forbidden capability ['exec'] requested by role T5

    $ python3 scripts/capability-assert.py T5 read sessions_yield
    Error: Forbidden capability ['sessions_yield'] requested by worker role T5 (coordinator_only 仅限主控角色 ['T0', 'T8'])

设计（教训 #210，审计响应）：
- **单一真源**：允许面/禁用面**直接读 SKILL.md frontmatter**（metadata.tools.{base,coordinator_only,
  research_extra,opt_in} 为允许，metadata.tools.denied 为禁用）；
  硬编码列表一旦与 frontmatter 漂移，就会出现「文档声明禁用、脚本实际放行」的假绿灯
  （2026-09-12 第三方审计 P0-1：denied 里的 memory_store / memory_forget / sessions_search
   曾被本脚本列入允许白名单）。本脚本现**不再维护第二份权限清单**。
- **denied 优先**：任何同时出现在允许面与 denied 的能力，一律判定为禁用（denied 永不失效）。
- **角色最小权限**：每个角色只声明实际需要的能力。
- **角色分区（v2.12.74 F2，CARD-P1 问题 2）**：`coordinator_only` 仅对主控角色 T0/T8 放行；
   worker 角色（T1-T7/T9/G14）请求任一项即拒绝——旧实现取全部允许档并集，导致
   `T5 sessions_yield` 也 exit 0（声明、脚本、runtime 三处口径互相矛盾）。
- **spawn 前校验**：主控在 spawn 前断言，失败 → 人在环介入。
- 校验方式：`python3 scripts/capability-assert.py --selfcheck` 自检真源可读 + 声面真交集 + 逐项拒斥行为断言
  （v2.12.50 重写为**能判红**的四路断言；原「denied ∩ 减法后允许面」恒空，属空转门，教训 #399；
  v2.12.74 增第⑥路角色分区断言：coordinator_only 逐项对 worker 真拒绝 + 对主控真接受）。
"""

import sys
import pathlib
import yaml

SKILL_MD = pathlib.Path(__file__).resolve().parent.parent / 'SKILL.md'

# 论衡角色定义
ROLES = {
    "T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9",
    "G14"
}

# v2.12.74：不再维护宿主工具的第二份允许清单。
# 过去这里硬编码 OpenViking 只读扩展；R2 已将其纳入 frontmatter denied，
# 且任何宿主扩展都必须以 SKILL.md 为唯一真源，否则会出现「声明禁用、脚本放行」漂移。
# 保留空集合只是为了兼容测试与派生集表达；它不是额外授权面。
HOST_READONLY_EXTRAS = set()

# 绝对禁用（不在 SKILL.md frontmatter 五档内，但属宿主特权面，永久拒绝）
HARD_FORBIDDEN = {"secrets", "gateway", "automations"}


def load_permission_surface(skill_md: pathlib.Path = SKILL_MD):
    """从 SKILL.md frontmatter 读取权限真源 → (denied, declared_allowed, coordinator_only)

    frontmatter 结构（metadata.tools）：base / coordinator_only / research_extra / opt_in / denied
    """
    text = skill_md.read_text(encoding='utf-8')
    parts = text.split('---', 2)
    if len(parts) < 3:
        raise RuntimeError(f'{skill_md} 缺 frontmatter（无法读取权限真源）')
    fm = yaml.safe_load(parts[1]) or {}
    tools = ((fm.get('metadata') or {}).get('tools') or {})
    denied = {str(x) for x in (tools.get('denied') or [])}
    coordinator_only = {str(x) for x in (tools.get('coordinator_only') or [])}
    declared = set()
    for key, val in tools.items():
        if key == 'denied':
            continue
        if isinstance(val, (list, tuple)):
            declared.update(str(x) for x in val)
    return denied, declared, coordinator_only


SKILL_DENIED, SKILL_DECLARED, COORDINATOR_ONLY = load_permission_surface()

# 主控角色（v2.12.74 F2，CARD-P1 问题 2）：coordinator_only 仅对 T0（主控）与
#   T8（主控亲完成的终检节点）放行；T1-T7/T9/G14 = worker 一律拒绝。
#   角色编号是本脚本层概念（与 ROLES 同源），frontmatter 无载体，故在此定义。
COORDINATOR_ROLES = {"T0", "T8"}

# 禁用面 = frontmatter denied ∪ 永久硬禁用
FORBIDDEN_CAPABILITIES = SKILL_DENIED | HARD_FORBIDDEN

# 允许面 = frontmatter 允许档 ∪ 只读宿主扩展，**再减去禁用面**（denied 优先，永不失效）
ALLOWED_CAPABILITIES = (SKILL_DECLARED | HOST_READONLY_EXTRAS) - FORBIDDEN_CAPABILITIES


class CapabilityAssertionError(Exception):
    """能力断言失败异常"""
    pass


def validate_capabilities(role, capabilities):
    """校验角色请求的能力集合。"""
    if not role:
        raise CapabilityAssertionError("Role cannot be empty")

    if role not in ROLES:
        raise CapabilityAssertionError(f"Unknown role: {role}")

    if not capabilities:
        raise CapabilityAssertionError(f"Role {role} must declare at least one capability")

    requested = set(capabilities)

    # 检查禁用能力
    forbidden = requested & FORBIDDEN_CAPABILITIES
    if forbidden:
        raise CapabilityAssertionError(
            f"Forbidden capability {sorted(forbidden)} requested by role {role}"
        )

    # 角色分区（v2.12.74 F2）：coordinator_only 仅限主控角色，worker 请求即拒绝
    if role not in COORDINATOR_ROLES:
        coord_leak = requested & COORDINATOR_ONLY
        if coord_leak:
            raise CapabilityAssertionError(
                f"Forbidden capability {sorted(coord_leak)} requested by worker role {role} "
                f"(coordinator_only 仅限主控角色 {sorted(COORDINATOR_ROLES)})"
            )

    # 检查未知能力
    unknown = requested - ALLOWED_CAPABILITIES
    if unknown:
        raise CapabilityAssertionError(
            f"Unknown capability {sorted(unknown)} requested by role {role}. "
            f"Allowed: {sorted(ALLOWED_CAPABILITIES)}"
        )


def selfcheck() -> int:
    """真源自检：权限口径必须「能被判红」（v2.12.50 重写，教训 #399「机械门必须能红」）。

    原实现（v2.12.30 → v2.12.49）取 `SKILL_DENIED & ALLOWED_CAPABILITIES`，而
    `ALLOWED_CAPABILITIES` 已在 :88 减去 `FORBIDDEN_CAPABILITIES`（⊇ SKILL_DENIED）
    ⇒ 交集**数学上恒空**，下游那条 `cap in ALLOWED_CAPABILITIES` 亦恒假
    ⇒ 自检**永不失败**（空转门；同族 门 B/门 S/门 T 历史假绿灯、教训 #150）。

    现改为五路可失败断言（均以**声面真源**为基准，不挂派生集）：
      ① 解析守卫：denied / 允许面任一为空 → 报错（防 frontmatter 解析失败后真空通过）
      ② 派生一致性：模块级 FORBIDDEN/ALLOWED 必须等于由真源现算的期望集
         （v2.12.50 二修：反向注入证明——禁用面被清空时，挂派生集的断言会全部真空仍报绿）
      ③ 声面真交集：允许档与 denied **不做减法**直接取交 → 命中即冲突
      ④ 行为断言：禁用面真源每一项都必须被 validate_capabilities 真拒绝
      ⑤ 镜像断言：允许面抽一项必须被真接受（防「一律拒绝」的反向假绿灯）
      ⑥ 角色分区（v2.12.74 F2）：coordinator_only 每一项对 worker 角色 T5 必须真拒绝、
        对主控角色 T0/T8 必须真接受（双向镜像，防分区失效或修过头）
    """
    errors = []

    # 真源现算（不依赖模块级派生集）
    expected_forbidden = SKILL_DENIED | HARD_FORBIDDEN
    expected_allowed = (SKILL_DECLARED | HOST_READONLY_EXTRAS) - expected_forbidden

    # ① 解析守卫
    if not SKILL_DENIED:
        errors.append('denied 清单为空 —— frontmatter 解析失败或真源缺失')
    if not (SKILL_DECLARED or HOST_READONLY_EXTRAS):
        errors.append('允许面为空 —— frontmatter 解析失败或真源缺失')
    if not COORDINATOR_ONLY:
        errors.append('coordinator_only 清单为空 —— frontmatter 解析失败或真源缺失')

    # ② 派生一致性
    if FORBIDDEN_CAPABILITIES != expected_forbidden:
        errors.append(
            f'禁用面派生不一致：实得 {len(FORBIDDEN_CAPABILITIES)} 项 ≠ 真源现算 {len(expected_forbidden)} 项'
            f'（差集 {sorted(expected_forbidden ^ FORBIDDEN_CAPABILITIES)}）'
        )
    if ALLOWED_CAPABILITIES != expected_allowed:
        errors.append(
            f'允许面派生不一致：实得 {len(ALLOWED_CAPABILITIES)} 项 ≠ 真源现算 {len(expected_allowed)} 项'
            f'（差集 {sorted(expected_allowed ^ ALLOWED_CAPABILITIES)}）'
        )

    # ③ 声面真交集（不减法）
    declared_overlap = SKILL_DECLARED & SKILL_DENIED
    if declared_overlap:
        errors.append(f'允许档与 denied 同时声明：{sorted(declared_overlap)}')
    extras_overlap = HOST_READONLY_EXTRAS & expected_forbidden
    if extras_overlap:
        errors.append(f'只读宿主扩展与禁用面冲突：{sorted(extras_overlap)}')

    # ④ 行为断言：禁用面真源必须逐项被拒
    for cap in sorted(expected_forbidden):
        try:
            validate_capabilities('T0', [cap])
        except CapabilityAssertionError:
            continue
        except Exception as e:  # 异常类型漂移也算失败
            errors.append(f'禁用能力 {cap} 断言抛错类型异常：{type(e).__name__}: {e}')
            continue
        errors.append(f'禁用能力 {cap} 被 validate_capabilities 放行')

    # ⑤ 镜像断言：允许面必须真被接受
    sample = sorted(expected_allowed)
    if not sample:
        errors.append('允许面为空 —— 无法做接受性断言（反向假绿灯风险）')
    else:
        try:
            validate_capabilities('T0', [sample[0]])
        except Exception as e:
            errors.append(f'允许能力 {sample[0]} 被误拒：{e}')

    # ⑥ 角色分区行为断言（v2.12.74 F2，CARD-P1 问题 2 验收判据）：
    #    worker 侧 T5 + sessions_yield 必须 exit 1；主控侧 T0/T8 必须真接受（镜像）
    for cap in sorted(COORDINATOR_ONLY):
        try:
            validate_capabilities('T5', ['read', cap])
        except CapabilityAssertionError:
            pass
        except Exception as e:  # 异常类型漂移也算失败
            errors.append(f'coordinator_only 能力 {cap} worker 断言抛错类型异常：{type(e).__name__}: {e}')
        else:
            errors.append(f'coordinator_only 能力 {cap} 被 worker 角色 T5 放行（角色分区失效）')
        for cr in sorted(COORDINATOR_ROLES):
            try:
                validate_capabilities(cr, ['read', cap])
            except Exception as e:
                errors.append(f'coordinator_only 能力 {cap} 被主控角色 {cr} 误拒：{e}')

    if errors:
        for e in errors:
            print(f'❌ 权限口径冲突：{e}', file=sys.stderr)
        return 1

    print(
        f'✅ 权限口径一致：denied {len(expected_forbidden)} 项逐项被拒 / '
        f'allowed {len(expected_allowed)} 项接受性抽查通过（派生一致 + 声面交集 0）/ '
        f'coordinator_only {len(COORDINATOR_ONLY)} 项角色分区双向断言通过（worker 拒绝 + 主控接受）'
    )
    return 0


def main():
    if len(sys.argv) == 2 and sys.argv[1] == '--selfcheck':
        sys.exit(selfcheck())

    if len(sys.argv) < 3:
        print("Usage: capability-assert.py <role> <capability1> [capability2 ...]", file=sys.stderr)
        print("       capability-assert.py --selfcheck", file=sys.stderr)
        print(f"Allowed capabilities: {sorted(ALLOWED_CAPABILITIES)}", file=sys.stderr)
        sys.exit(1)

    role = sys.argv[1]
    capabilities = sys.argv[2:]

    try:
        validate_capabilities(role, capabilities)
        print(f"✅ Role {role}: All capabilities valid ({len(capabilities)} total)")
        sys.exit(0)
    except CapabilityAssertionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
