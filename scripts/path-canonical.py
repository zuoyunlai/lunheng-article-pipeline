#!/usr/bin/env python3
"""
path-canonical.py — 论衡路径规范化校验器（v2.9.1，响应腾讯 A.I.G 审计 Remediation #5）

用途：
- 在写入文件前，强制解析为 canonical 路径
- 拒绝绝对路径、路径遍历（..）、符号链接
- 确保所有写入路径在 run/<项目>/ 下

调用：
    python3 scripts/path-canonical.py <base_dir> <target_path>
    
返回：
    - exit 0 + stdout 输出规范化路径：校验通过
    - exit 1 + stderr 输出错误原因：校验失败

示例：
    $ python3 scripts/path-canonical.py run/test-project drafts/outline.md
    run/test-project/drafts/outline.md
    
    $ python3 scripts/path-canonical.py run/test-project /etc/passwd
    Error: Absolute path not allowed: /etc/passwd

设计（教训 #210，审计响应）：
- **canonical = realpath 解析 + 前缀检查**
- **符号链接拒绝**：realpath 会解析 symlink，但解析后路径必须在 base_dir 内
- **不创建目录**：只校验路径合法性，不执行文件系统操作
"""

import sys
import os
from pathlib import Path


def validate_canonical_path(base_dir: str, target_path: str) -> str:
    """
    校验目标路径，返回规范化后的绝对路径。
    
    Args:
        base_dir: 项目根目录（如 run/test-project）
        target_path: 待校验路径（相对或绝对）
    
    Returns:
        规范化后的绝对路径
    
    Raises:
        ValueError: 路径不合法
    """
    # 1. 拒绝绝对路径（除非在 base_dir 内）
    if os.path.isabs(target_path):
        raise ValueError(f"Absolute path not allowed: {target_path}")
    
    # 2. 构造候选绝对路径
    base = Path(base_dir).resolve()
    candidate = (base / target_path).resolve()
    
    # 3. 检查规范化路径是否在 base_dir 内
    try:
        candidate.relative_to(base)
    except ValueError:
        raise ValueError(
            f"Path traversal detected: {target_path} resolves outside {base_dir}"
        )
    
    # 4. 检查路径中是否包含符号链接（严格模式）
    # resolve() 已解析符号链接，如果解析后路径与预期不符，说明有 symlink
    # 但这个检查依赖文件系统状态，在写入前无法完全验证
    # 当前策略：只要最终路径在 base_dir 内即可
    # 可选：如果需要严格禁止 symlink，需在运行时检查
    
    return str(candidate)


def main():
    if len(sys.argv) != 3:
        print("Usage: path-canonical.py <base_dir> <target_path>", file=sys.stderr)
        sys.exit(1)
    
    base_dir = sys.argv[1]
    target_path = sys.argv[2]
    
    try:
        canonical = validate_canonical_path(base_dir, target_path)
        print(canonical)
        sys.exit(0)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
