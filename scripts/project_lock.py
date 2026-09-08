#!/usr/bin/env python3
"""
论衡项目锁管理器
防止并发运行多个论衡项目时的文件冲突
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple


class ProjectLock:
    """项目锁管理器"""
    
    def __init__(self, project_name: str, workspace_root: str):
        """
        初始化项目锁
        
        Args:
            project_name: 项目名称
            workspace_root: 工作区根目录
        """
        self.project_name = project_name
        self.workspace_root = Path(workspace_root)
        self.lock_file = self.workspace_root / "run" / project_name / ".lunheng.lock"
        self.pid = os.getpid()
    
    def acquire(self) -> Tuple[bool, Optional[str]]:
        """
        获取项目锁
        
        Returns:
            (成功标志, 错误信息)
        """
        # 确保目录存在
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 检查锁文件是否存在
        if self.lock_file.exists():
            # 读取锁文件内容
            try:
                content = self.lock_file.read_text().strip()
                old_pid = int(content)
                
                # 检查进程是否还在运行
                if self._is_process_running(old_pid):
                    return False, f"项目 {self.project_name} 正在被进程 {old_pid} 使用，请等待其完成或终止该进程"
                else:
                    # 旧进程已结束，清理陈旧锁文件
                    self.lock_file.unlink()
            except (ValueError, IOError) as e:
                # 锁文件损坏，清理并继续
                try:
                    self.lock_file.unlink()
                except:
                    pass
        
        # 创建锁文件
        try:
            self.lock_file.write_text(str(self.pid))
            return True, None
        except IOError as e:
            return False, f"无法创建锁文件: {e}"
    
    def release(self):
        """释放项目锁"""
        try:
            if self.lock_file.exists():
                content = self.lock_file.read_text().strip()
                if content == str(self.pid):
                    self.lock_file.unlink()
        except:
            pass
    
    def _is_process_running(self, pid: int) -> bool:
        """
        检查进程是否在运行
        
        Args:
            pid: 进程ID
            
        Returns:
            进程是否存活
        """
        try:
            # 发送信号0检查进程是否存在（不实际杀死进程）
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
    
    def __enter__(self):
        """上下文管理器入口"""
        success, error = self.acquire()
        if not success:
            raise RuntimeError(error)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.release()


def check_concurrent_projects(workspace_root: str) -> list:
    """
    检查当前有哪些论衡项目正在运行
    
    Args:
        workspace_root: 工作区根目录
        
    Returns:
        正在运行的项目列表 [(项目名, PID), ...]
    """
    workspace = Path(workspace_root)
    run_dir = workspace / "run"
    
    if not run_dir.exists():
        return []
    
    running = []
    for project_dir in run_dir.iterdir():
        if not project_dir.is_dir():
            continue
        
        lock_file = project_dir / ".lunheng.lock"
        if lock_file.exists():
            try:
                pid = int(lock_file.read_text().strip())
                # 检查进程是否还在运行
                try:
                    os.kill(pid, 0)
                    running.append((project_dir.name, pid))
                except (OSError, ProcessLookupError):
                    # 陈旧锁文件，清理
                    lock_file.unlink()
            except:
                pass
    
    return running


if __name__ == "__main__":
    # 命令行工具
    if len(sys.argv) < 3:
        print("用法: python project_lock.py <命令> <项目名> [工作区根目录]")
        print("命令:")
        print("  acquire  - 获取锁")
        print("  release  - 释放锁")
        print("  check    - 检查运行中的项目")
        sys.exit(1)
    
    command = sys.argv[1]
    project_name = sys.argv[2]
    workspace_root = sys.argv[3] if len(sys.argv) > 3 else os.getcwd()
    
    if command == "acquire":
        lock = ProjectLock(project_name, workspace_root)
        success, error = lock.acquire()
        if success:
            print(f"✓ 已获取项目锁: {project_name} (PID {lock.pid})")
            sys.exit(0)
        else:
            print(f"✗ 获取项目锁失败: {error}", file=sys.stderr)
            sys.exit(1)
    
    elif command == "release":
        lock = ProjectLock(project_name, workspace_root)
        lock.release()
        print(f"✓ 已释放项目锁: {project_name}")
        sys.exit(0)
    
    elif command == "check":
        running = check_concurrent_projects(workspace_root)
        if running:
            print("运行中的论衡项目:")
            for name, pid in running:
                print(f"  - {name} (PID {pid})")
        else:
            print("当前无运行中的论衡项目")
        sys.exit(0)
    
    else:
        print(f"未知命令: {command}", file=sys.stderr)
        sys.exit(1)
