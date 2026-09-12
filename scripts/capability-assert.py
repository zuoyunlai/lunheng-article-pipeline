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

设计（教训 #210，审计响应）：
- **单一真源**：允许面/禁用面**直接读 SKILL.md frontmatter**（metadata.tools.{base,coordinator_only,
  research_extra,opt_in} 为允许，metadata.tools.denied 为禁用）；
  硬编码列表一旦与 frontmatter 漂移，就会出现「文档声明禁用、脚本实际放行」的假绿灯
  （2026-09-12 第三方审计 P0-1：denied 里的 memory_store / memory_forget / sessions_search
   曾被本脚本列入允许白名单）。本脚本现**不再维护第二份权限清单**。
- **denied 优先**：任何同时出现在允许面与 denied 的能力，一律判定为禁用（denied 永不失效）。
- **角色最小权限**：每个角色只声明实际需要的能力。
- **spawn 前校验**：主控在 spawn 前断言，失败 → 人在环介入。
- 校验方式：`python3 scripts/capability-assert.py --selfcheck` 自检真源可读 + 无交集。
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

# 论衡 agent 侧可用的**只读宿主工具**（OpenViking 检索家族 / 只读会话与交互工具）：
# 不属于 SKILL.md 五档工具声明，但检索、审计与人在环节点合法使用。
HOST_READONLY_EXTRAS = {
    "ov_search", "ov_read", "ov_multi_read", "ov_list",
    "ov_archive_search", "ov_archive_expand",
    "openviking_tool_result_list", "openviking_tool_result_read",
    "openviking_tool_result_search",
    "sessions_list", "ask_user", "view_image",
}

# 绝对禁用（不在 SKILL.md frontmatter 五档内，但属宿主特权面，永久拒绝）
HARD_FORBIDDEN = {"secrets", "gateway", "automations"}


def load_permission_surface(skill_md: pathlib.Path = SKILL_MD):
    """从 SKILL.md frontmatter 读取权限真源 → (denied, declared_allowed)

    frontmatter 结构（metadata.tools）：base / coordinator_only / research_extra / opt_in / denied
    """
    text = skill_md.read_text(encoding='utf-8')
    parts = text.split('---', 2)
    if len(parts) < 3:
        raise RuntimeError(f'{skill_md} 缺 frontmatter（无法读取权限真源）')
    fm = yaml.safe_load(parts[1]) or {}
    tools = ((fm.get('metadata') or {}).get('tools') or {})
    denied = {str(x) for x in (tools.get('denied') or [])}
    declared = set()
    for key, val in tools.items():
        if key == 'denied':
            continue
        if isinstance(val, (list, tuple)):
            declared.update(str(x) for x in val)
    return denied, declared


SKILL_DENIED, SKILL_DECLARED = load_permission_surface()

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

    # 检查未知能力
    unknown = requested - ALLOWED_CAPABILITIES
    if unknown:
        raise CapabilityAssertionError(
            f"Unknown capability {sorted(unknown)} requested by role {role}. "
            f"Allowed: {sorted(ALLOWED_CAPABILITIES)}"
        )


def selfcheck() -> int:
    """真源自检：denied 与允许面必须无交集，且 denied 全部被判定为禁用。"""
    overlap = SKILL_DENIED & ALLOWED_CAPABILITIES
    if overlap:
        print(f'❌ 权限口径冲突：denied 能力出现在允许面 {sorted(overlap)}', file=sys.stderr)
        return 1
    for cap in sorted(FORBIDDEN_CAPABILITIES):
        if cap in ALLOWED_CAPABILITIES:
            print(f'❌ 禁用能力 {cap} 同时出现在允许面', file=sys.stderr)
            return 1
    print(f'✅ 权限口径一致：denied {len(FORBIDDEN_CAPABILITIES)} 项 / allowed {len(ALLOWED_CAPABILITIES)} 项，零交集')
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
