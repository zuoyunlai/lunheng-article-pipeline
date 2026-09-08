"""
项目锁管理器单元测试
"""

import os
import tempfile
import time
from pathlib import Path
import sys

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from project_lock import ProjectLock, check_concurrent_projects


def test_acquire_release():
    """测试基本的获取和释放锁"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lock = ProjectLock("test-project", tmpdir)
        
        # 获取锁
        success, error = lock.acquire()
        assert success, f"获取锁失败: {error}"
        assert error is None
        
        # 锁文件存在
        lock_file = Path(tmpdir) / "run" / "test-project" / ".lunheng.lock"
        assert lock_file.exists(), "锁文件不存在"
        
        # 锁文件内容正确
        content = lock_file.read_text().strip()
        assert content == str(lock.pid), f"锁文件内容错误: {content} != {lock.pid}"
        
        # 释放锁
        lock.release()
        assert not lock_file.exists(), "锁文件未被删除"


def test_concurrent_acquire():
    """测试并发获取锁"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lock1 = ProjectLock("test-project", tmpdir)
        lock2 = ProjectLock("test-project", tmpdir)
        
        # 第一个锁成功
        success1, error1 = lock1.acquire()
        assert success1, f"第一个锁获取失败: {error1}"
        
        # 第二个锁失败
        success2, error2 = lock2.acquire()
        assert not success2, "第二个锁不应该成功"
        assert error2 is not None
        assert "正在被进程" in error2, f"错误消息格式错误: {error2}"
        
        # 释放第一个锁后，第二个锁成功
        lock1.release()
        success2, error2 = lock2.acquire()
        assert success2, f"释放第一个锁后，第二个锁获取失败: {error2}"
        
        lock2.release()


def test_stale_lock_cleanup():
    """测试陈旧锁文件的清理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lock = ProjectLock("test-project", tmpdir)
        
        # 手动创建一个陈旧的锁文件（使用不存在的 PID）
        lock_file = Path(tmpdir) / "run" / "test-project" / ".lunheng.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 使用一个非常大的 PID，几乎肯定不存在
        fake_pid = 999999
        lock_file.write_text(str(fake_pid))
        
        # 尝试获取锁，应该自动清理陈旧锁
        success, error = lock.acquire()
        assert success, f"清理陈旧锁后获取失败: {error}"
        
        # 锁文件内容应该是当前进程的 PID
        content = lock_file.read_text().strip()
        assert content == str(lock.pid), f"锁文件未更新: {content} != {lock.pid}"
        
        lock.release()


def test_context_manager():
    """测试上下文管理器"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = Path(tmpdir) / "run" / "test-project" / ".lunheng.lock"
        
        # 使用 with 语句
        with ProjectLock("test-project", tmpdir) as lock:
            # 在上下文中，锁文件应该存在
            assert lock_file.exists(), "上下文中锁文件不存在"
        
        # 退出上下文后，锁文件应该被删除
        assert not lock_file.exists(), "退出上下文后锁文件未被删除"


def test_context_manager_failure():
    """测试上下文管理器获取失败的情况"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 先获取锁
        lock1 = ProjectLock("test-project", tmpdir)
        lock1.acquire()
        
        # 尝试用上下文管理器获取同一个锁，应该抛出异常
        try:
            with ProjectLock("test-project", tmpdir):
                assert False, "不应该执行到这里"
        except RuntimeError as e:
            assert "正在被进程" in str(e), f"异常消息格式错误: {e}"
        
        lock1.release()


def test_check_concurrent_projects():
    """测试检查运行中的项目"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建两个项目锁
        lock1 = ProjectLock("project-1", tmpdir)
        lock2 = ProjectLock("project-2", tmpdir)
        
        lock1.acquire()
        lock2.acquire()
        
        # 检查运行中的项目
        running = check_concurrent_projects(tmpdir)
        assert len(running) == 2, f"应该有 2 个运行中的项目，实际: {len(running)}"
        
        project_names = [name for name, pid in running]
        assert "project-1" in project_names
        assert "project-2" in project_names
        
        # 释放一个锁
        lock1.release()
        
        # 再次检查，应该只剩一个
        running = check_concurrent_projects(tmpdir)
        assert len(running) == 1, f"应该有 1 个运行中的项目，实际: {len(running)}"
        assert running[0][0] == "project-2"
        
        lock2.release()
        
        # 全部释放后，应该没有运行中的项目
        running = check_concurrent_projects(tmpdir)
        assert len(running) == 0, f"应该没有运行中的项目，实际: {len(running)}"


def test_different_projects_concurrent():
    """测试不同项目可以并发运行"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lock1 = ProjectLock("project-A", tmpdir)
        lock2 = ProjectLock("project-B", tmpdir)
        
        # 两个不同项目的锁都应该成功
        success1, _ = lock1.acquire()
        success2, _ = lock2.acquire()
        
        assert success1, "项目 A 锁获取失败"
        assert success2, "项目 B 锁获取失败"
        
        # 两个锁文件都存在
        lock_file_a = Path(tmpdir) / "run" / "project-A" / ".lunheng.lock"
        lock_file_b = Path(tmpdir) / "run" / "project-B" / ".lunheng.lock"
        
        assert lock_file_a.exists()
        assert lock_file_b.exists()
        
        lock1.release()
        lock2.release()


def test_corrupted_lock_file():
    """测试损坏的锁文件处理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lock = ProjectLock("test-project", tmpdir)
        
        # 手动创建一个损坏的锁文件（非数字内容）
        lock_file = Path(tmpdir) / "run" / "test-project" / ".lunheng.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text("corrupted-content-not-a-number")
        
        # 尝试获取锁，应该自动清理损坏的锁文件
        success, error = lock.acquire()
        assert success, f"清理损坏锁文件后获取失败: {error}"
        
        # 锁文件内容应该是当前进程的 PID
        content = lock_file.read_text().strip()
        assert content == str(lock.pid), f"锁文件未更新: {content} != {lock.pid}"
        
        lock.release()
