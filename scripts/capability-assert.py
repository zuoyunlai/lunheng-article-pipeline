#!/usr/bin/env python3
"""
capability-assert.py — 论衡能力断言脚本（v2.9.1，响应腾讯 A.I.G 审计 Remediation #6）

用途：
- 在 spawn 子代理前，断言所需能力可用
- 拒绝高风险能力（exec/process/terminal/secrets）
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
    Error: Forbidden capability 'exec' requested by role T5

设计（教训 #210，审计响应）：
- **白名单机制**：只允许论衡定义的安全能力集
- **角色最小权限**：每个角色只声明实际需要的能力
- **spawn 前校验**：主控在 spawn 前断言，失败 → 人在环介入
"""

import sys
from typing import List, Set

# 论衡角色定义（v2.9.1）
ROLES = {
    "T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9",
    "G14"
}

# 论衡允许的能力白名单（基于 SKILL.md frontmatter metadata.tools）
ALLOWED_CAPABILITIES = {
    # 文件操作
    "read", "write", "edit",
    
    # 搜索与网络
    "web_search", "web_fetch", "tavily_search", "tavily_extract",
    
    # OpenViking 记忆与上下文
    "memory_search", "memory_get", "memory_recall", "memory_store", "memory_forget",
    "ov_search", "ov_read", "ov_multi_read", "ov_list",
    "ov_archive_search", "ov_archive_expand",
    "openviking_tool_result_list", "openviking_tool_result_read", "openviking_tool_result_search",
    
    # 会话管理
    "sessions_spawn", "sessions_list", "sessions_history", "sessions_search",
    "session_status", "progress_card",
    
    # 用户交互
    "ask_user",
    
    # 图像处理
    "view_image", "image_generate",
}

# 明确禁止的高风险能力
FORBIDDEN_CAPABILITIES = {
    "exec", "process", "terminal", "secrets",
    "browser", "portal", "nodes",
    "gateway", "automations",
}


class CapabilityAssertionError(Exception):
    """能力断言失败异常"""
    pass


def validate_capabilities(role: str, capabilities: List[str]) -> None:
    """
    校验角色请求的能力集合。
    
    Args:
        role: 角色标识（如 T1, T5）
        capabilities: 请求的能力列表
    
    Raises:
        CapabilityAssertionError: 能力校验失败
    """
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


def main():
    if len(sys.argv) < 3:
        print("Usage: capability-assert.py <role> <capability1> [capability2 ...]", file=sys.stderr)
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
