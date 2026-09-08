#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
path_validator.py — 路径注入防护工具（P0-2 修订 2026-09-08）

用途：
- 验证用户输入路径是否在允许的基础目录内
- 防止路径遍历攻击（如 ../../etc/passwd）
- 供主控 Phase 0 和检索员使用

设计原则：
- 路径必须规范化后仍在 base_dir 内
- 拒绝符号链接（除非显式允许）
- 拒绝特殊字符（如 null byte）
"""

import os
from pathlib import Path
from typing import Optional


class PathValidationError(Exception):
    """路径验证失败异常"""
    pass


def validate_path(
    user_path: str,
    base_dir: str,
    allow_symlinks: bool = False,
    create_missing: bool = False
) -> Path:
    """
    验证路径在允许范围内
    
    Args:
        user_path: 用户提供的路径（相对或绝对）
        base_dir: 允许的基础目录
        allow_symlinks: 是否允许符号链接
        create_missing: 如果父目录不存在是否创建
    
    Returns:
        规范化后的绝对路径（Path 对象）
    
    Raises:
        PathValidationError: 路径验证失败
    
    Example:
        >>> validate_path("run/project1/draft.md", "/home/user/.openclaw/workspace/skills/lunheng")
        PosixPath('/home/user/.openclaw/workspace/skills/lunheng/run/project1/draft.md')
        
        >>> validate_path("../../etc/passwd", "/home/user/.openclaw/workspace/skills/lunheng")
        PathValidationError: 路径遍历到基础目录外
    """
    # 1. 输入验证
    if not user_path or not isinstance(user_path, str):
        raise PathValidationError("路径不能为空")
    
    if '\x00' in user_path:
        raise PathValidationError("路径包含非法字符（null byte）")
    
    if not base_dir or not isinstance(base_dir, str):
        raise PathValidationError("基础目录不能为空")
    
    # 2. 规范化路径
    try:
        base = Path(base_dir).resolve(strict=True)
    except (OSError, RuntimeError) as e:
        raise PathValidationError(f"基础目录无效: {e}")
    
    # 用户路径可以不存在（待创建），但需要规范化
    try:
        # 先拼接，再规范化
        candidate = (base / user_path).resolve()
    except (OSError, RuntimeError) as e:
        raise PathValidationError(f"路径无效: {e}")
    
    # 3. 检查是否在基础目录内
    try:
        candidate.relative_to(base)
    except ValueError:
        raise PathValidationError(
            f"路径遍历到基础目录外: {candidate} 不在 {base} 内"
        )
    
    # 4. 符号链接检查
    if not allow_symlinks and candidate.is_symlink():
        raise PathValidationError(f"不允许符号链接: {candidate}")
    
    # 5. 父目录处理
    if create_missing and not candidate.parent.exists():
        try:
            candidate.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise PathValidationError(f"无法创建父目录: {e}")
    
    return candidate


def validate_workspace_path(user_path: str, workspace_root: str) -> Path:
    """
    论衡专用：验证路径在 workspace 或其子目录 run/ 内
    
    Args:
        user_path: 用户提供的路径
        workspace_root: workspace 根目录
    
    Returns:
        规范化后的绝对路径
    
    Raises:
        PathValidationError: 路径验证失败
    """
    validated = validate_path(user_path, workspace_root, create_missing=False)
    
    # 论衡特定规则：只允许写入 run/<项目名>/ 或读取 references/
    rel = validated.relative_to(Path(workspace_root).resolve())
    parts = rel.parts
    
    if len(parts) == 0:
        raise PathValidationError("不允许直接操作 workspace 根目录")
    
    first_dir = parts[0]
    allowed_dirs = {'run', 'references', 'outputs', 'tests', 'scripts'}
    
    if first_dir not in allowed_dirs:
        raise PathValidationError(
            f"路径必须在允许的目录内: {allowed_dirs}，当前: {first_dir}"
        )
    
    return validated


if __name__ == "__main__":
    # 自测
    import sys
    
    print("=== 路径验证工具自测 ===")
    
    # 测试用例
    test_base = "/tmp/test_workspace"
    os.makedirs(test_base, exist_ok=True)
    
    test_cases = [
        ("run/project1/draft.md", True, "正常相对路径"),
        ("../../../etc/passwd", False, "路径遍历攻击"),
        ("/etc/passwd", False, "绝对路径逃逸"),
        ("run/../run/project1/draft.md", True, "规范化后合法"),
        ("run\x00/project1/draft.md", False, "null byte 注入"),
    ]
    
    passed = 0
    failed = 0
    
    for user_path, should_pass, description in test_cases:
        try:
            result = validate_path(user_path, test_base)
            if should_pass:
                print(f"✓ {description}: {user_path} -> {result}")
                passed += 1
            else:
                print(f"✗ {description}: 应该失败但通过了: {user_path}")
                failed += 1
        except PathValidationError as e:
            if not should_pass:
                print(f"✓ {description}: 正确拒绝: {e}")
                passed += 1
            else:
                print(f"✗ {description}: 不应失败: {e}")
                failed += 1
    
    print(f"\n通过: {passed}, 失败: {failed}")
    sys.exit(0 if failed == 0 else 1)
