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
        获取项目锁（P1-8 修复 2026-09-30）

        旧实现走 exists() -> write_text() 非原子路径，两次并发 acquire() 可双双
        返回 (True, None)（audit P1-8 实测）。现实现：
          1. 用 os.open(O_CREAT | O_EXCL | ...) 原子创建锁文件；
          2. 写入 owner_token = f"{pid}:{uuid4().hex[:8]}"，避免 CLI 退出 → 复用
             PID 时被当成「陈旧锁」清理；
          3. 锁文件已存在时，仅当 lock 文件 owner_token 与本进程不匹配且对应
             PID 不在运行时才清理；任何其他情况下立即失败（不再重试写）。

        Returns:
            (成功标志, 错误信息)
        """
        import uuid
        # 确保目录存在
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        token = f"{self.pid}:{uuid.uuid4().hex[:8]}"
        # 最多重试一次：清理陈旧锁后再 O_EXCL（验证收口 2026-09-30 补 audit §3）
        for attempt in range(2):
            try:
                fd = os.open(str(self.lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                try:
                    os.write(fd, token.encode("utf-8"))
                finally:
                    os.close(fd)
                self._owner_token = token
                return True, None
            except FileExistsError:
                # 锁文件已存在 → 判陈旧 vs 真实冲突
                # 竞态守卫（验证收口 2026-09-30）：O_EXCL 创建与 os.write 之间存在空文件窗口；
                # 空内容可能是并发方「已创建未写完」，不能立即按损坏清理（否则双方各持一把锁）。
                # 先短轮询重读（5×20ms=100ms），等写入方落笔后再解析。
                content = ""
                for _ in range(5):
                    try:
                        content = self.lock_file.read_text(encoding="utf-8").strip()
                    except (OSError, ValueError):
                        content = ""
                    if content:
                        break
                    time.sleep(0.02)
                # 解析 owner_pid（兼容旧版纯 PID 锁：没有冒号）
                owner_pid = None
                if ":" in content:
                    try:
                        owner_pid = int(content.split(":", 1)[0])
                    except ValueError:
                        owner_pid = None
                else:
                    try:
                        owner_pid = int(content)
                    except ValueError:
                        owner_pid = None
                is_stale = (
                    owner_pid is not None
                    and owner_pid != self.pid
                    and not self._is_process_running(owner_pid)
                )
                if attempt == 0 and is_stale:
                    # 第一次：清理陈旧锁后重试
                    try:
                        self.lock_file.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                # 第二次或非陈旧：返回失败
                # 损坏锁（owner_pid=None）按可清理处理（验证收口 2026-09-30）
                if owner_pid is None and attempt == 0:
                    try:
                        self.lock_file.unlink()
                    except FileNotFoundError:
                        pass
                    continue
                owner_str = f"进程 {owner_pid}" if owner_pid is not None else f"raw={content!r}"
                if is_stale:
                    return False, f"陈旧锁清理后仍冲突（{owner_str}）—— 仅放行一次重试"
                return False, f"项目 {self.project_name} 正在被{owner_str}使用，请等待或显式 force 夺锁"
        return False, "acquire() 重试耗尽（不应到达此处）"
    
    def release(self, force: bool = False) -> Tuple[bool, Optional[str]]:
        """释放项目锁；按 token 校验 owner，force 才允许夺锁（P1-8 修复 2026-09-30）。

        owner_token 格式 = f"{pid}:{uuid4().hex[:8]}"，单凭 PID 比对不可靠：
        PID 在进程退出后可被系统复用，导致 "CLI 退出 → 下一进程被当成陈旧锁清理"。
        """
        try:
            if not self.lock_file.exists():
                return False, "锁文件不存在"
            content = self.lock_file.read_text().strip()
            owner_token = getattr(self, "_owner_token", None)
            # 兼容旧格式（纯 PID 文件）以防锁来自更早版本 / 其它写者
            is_legacy = ":" not in content
            if not force:
                if owner_token and content == owner_token:
                    pass  # 严格匹配 owner_token
                elif is_legacy and content == str(self.pid):
                    pass  # 旧版纯 PID 锁：本进程持有则可释放
                else:
                    return False, f"锁不属于本进程（owner_token={content!r}，本进程={owner_token!r}），未释放"
            self.lock_file.unlink()
            return True, None
        except (OSError, ValueError) as e:
            return False, f"释放项目锁失败: {e}"
    
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
                content = lock_file.read_text(encoding="utf-8").strip()
                # 验证收口 2026-09-30：解析新 token 格式 "pid:hex"（兼容旧纯 PID 锁）
                pid_str = content.split(":", 1)[0] if ":" in content else content
                pid = int(pid_str)
                # 检查进程是否还在运行
                try:
                    os.kill(pid, 0)
                    running.append((project_dir.name, pid))
                except (OSError, ProcessLookupError):
                    # 陈旧锁文件，清理
                    lock_file.unlink()
            except (ValueError, OSError):
                # 损坏 / 非数字内容：按可清理处理（验证收口 2026-09-30 兼容旧语义）
                try:
                    lock_file.unlink()
                except (FileNotFoundError, OSError):
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
        force = len(sys.argv) > 3 and sys.argv[3] == "--force"
        if force:
            workspace_root = sys.argv[4] if len(sys.argv) > 4 else os.getcwd()
        lock = ProjectLock(project_name, workspace_root)
        ok, error = lock.release(force=force)
        if ok:
            print(f"✓ 已释放项目锁: {project_name}" + ("（强制）" if force else ""))
            sys.exit(0)
        print(f"✗ 释放项目锁失败: {error}", file=sys.stderr)
        sys.exit(1)
    
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
