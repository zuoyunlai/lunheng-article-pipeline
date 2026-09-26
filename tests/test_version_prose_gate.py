#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_version_prose_gate.py — 升版后「正文版本」一致性门回归测试（v2.12.66）

背景（2026-09-20 实测，v2.12.65 升版流程）：
  `sync-version.sh` 同步 91 个文件、自审门 36 门全绿、打印「版本同步完成」—— 但 README
  正文「当前版本」块仍停在 v2.12.64。该判据按设计**不在** `check-version.sh` 覆盖面内
  （后者只校文件头版本戳 / 安装 pin / 角色命名），于是「本地全绿 + CI 红」：推送后
  `论衡算法测试 CI（全量）` 与 `Code Quality` 同时红，同一根因 =
  `tests/test_audit_residuals.py::test_readme_prose_version_matches_frontmatter`。
  与教训 #428 属**同一缺陷的第二次复现** ⇒ 该教训此前只靠纪律、无机械门（#430 同族）。

本测试锁死三层（缺任一层都可能只是「门存在 ≠ 门跑过」）：
  1. **接线**：`sync-version.sh` 必须调用这两条版本真源断言，且位置在「自审门之后、
     .bak 清理之前」（失败 ⇒ exit 1 ⇒ 既有「同步成功才清 .bak」语义自动覆盖本门）。
     清单不在此复制 —— 从脚本正文抽取，避免两处清单漂移（本仓老坑）。
  2. **判据有效（反向注入）**：对**整仓副本**注入「正文版本落后 frontmatter」，门必须红；
     真源 sha256 前后一致（硬断言）。注入点 = README 正文「当前版本」块 / SKILL.md 正文版本头。
  3. **端到端**：跑**副本的** `sync-version.sh` —— 注入错版 ⇒ 非零退出 + 点名文件与断言 +
     `.bak` 保留（= 视同未同步）；副本一致 ⇒ 退出 0（防假阳性）。
     副本的自审门替换为恒过桩，确保红/绿只可能来自本门（否则「因别的门红」会假绿本断言）。
"""
import hashlib
import pathlib
import re
import shutil
import subprocess
import sys

from conftest import tracked_tree

ROOT = pathlib.Path(__file__).resolve().parent.parent
SYNC = ROOT / "scripts" / "sync-version.sh"
SELF_AUDIT = ROOT / "scripts" / "self-audit-gate.sh"
SKILL = ROOT / "SKILL.md"
README = ROOT / "README.md"

# 真源零写入护栏：这些文件在测试前后 sha256 必须一致
TRUTH_FILES = (README, SKILL, SYNC, SELF_AUDIT)

COPY_IGNORE = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc")

# 本门应有的两条判据（正向前提：缺任一条即红，防「门被悄悄收窄」）
REQUIRED_NODES = (
    "tests/test_audit_residuals.py::test_readme_prose_version_matches_frontmatter",
    "tests/test_audit_residuals.py::test_skill_body_version_header_matches_frontmatter",
)

# 端到端失败时脚本必须打印的标记（用于区分「本门拦下」与「因别的门红而红」）
GATE_FAIL_MARK = "升版后正文版本一致性门失败"
GATE_PASS_MARK = "正文版本一致性门通过"


# --------------------------------------------------------------------------
# 工具
# --------------------------------------------------------------------------

def _sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _notes(paths=None):
    return {str(p): _sha256(p) for p in (paths or TRUTH_FILES)}


def gate_nodes():
    """本门实际调用的 pytest 节点（真源 = 脚本正文，测试不复制清单）。"""
    return tuple(re.findall(r'"(tests/test_audit_residuals\.py::[A-Za-z0-9_]+)"',
                            SYNC.read_text(encoding="utf-8")))


def _sandbox(tmp_path):
    """整仓副本（真源字节级只读）。"""
    dst = pathlib.Path(tmp_path) / "repo"
    if dst.exists():
        shutil.rmtree(dst)
    tracked_tree(ROOT, dst)
    return dst


def _run_gate(root):
    """按脚本同口径跑门：绝对节点路径 + `python3 -m pytest -q`（cwd 无关）。"""
    args = [sys.executable, "-m", "pytest", "-q"] + [str(root / n) for n in gate_nodes()]
    proc = subprocess.run(args, cwd=str(root), capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _run_sync(root):
    proc = subprocess.run(["bash", str(root / "scripts" / "sync-version.sh")],
                          cwd=str(root), capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _stub_self_audit(copy_root):
    """隔离被测对象：副本的自审门换恒过桩（只写副本）。"""
    (copy_root / "scripts" / "self-audit-gate.sh").write_text(
        "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")


def _frontmatter_version(root):
    m = re.search(r"^\s{4}version:\s*(\S+)", (root / "SKILL.md").read_text(encoding="utf-8"), re.M)
    assert m, "SKILL.md 缺 frontmatter version"
    return m.group(1)


def _stale(ver):
    """落后一版的错版值（复刻实测形态：frontmatter 2.12.65 / 正文 2.12.64）。"""
    x, y, z = (int(p) for p in ver.split("."))
    if z >= 1:
        return f"{x}.{y}.{z - 1}"
    if y >= 1:
        return f"{x}.{y - 1}.99"
    assert x >= 1, f"无法构造错版值：{ver}"
    return f"{x - 1}.99.99"


def _break_readme_prose(root):
    """注入点 ①：README 正文「当前版本」块退回旧版本号。"""
    p = root / "README.md"
    src = p.read_text(encoding="utf-8")
    bad = re.sub(r"(\*\*v)([0-9]+\.[0-9]+\.[0-9]+)(\*\*（[^）]*当前版本)",
                 lambda m: m.group(1) + _stale(_frontmatter_version(root)) + m.group(3),
                 src, count=1)
    assert bad != src, "反向注入点未命中：README 正文「当前版本」块"
    p.write_text(bad, encoding="utf-8")


def _break_skill_body_header(root):
    """注入点 ②：SKILL.md 正文版本头退回旧版本号（frontmatter 不动）。"""
    p = root / "SKILL.md"
    src = p.read_text(encoding="utf-8")
    bad = re.sub(r"^> 版本：v[0-9]+\.[0-9]+\.[0-9]+",
                 f"> 版本：v{_stale(_frontmatter_version(root))}", src, count=1, flags=re.M)
    assert bad != src, "反向注入点未命中：SKILL.md 正文版本头"
    p.write_text(bad, encoding="utf-8")


# --------------------------------------------------------------------------
# 1. 接线：判据清单 + 位置（自审门之后 / .bak 清理之前）
# --------------------------------------------------------------------------

def test_gate_calls_both_version_truth_assertions():
    nodes = gate_nodes()
    assert set(REQUIRED_NODES) <= set(nodes), \
        f"sync-version.sh 未调用全部版本真源断言（门被收窄）：{nodes}"
    assert len(nodes) == len(set(nodes)) == len(REQUIRED_NODES), f"节点清单异常：{nodes}"


def test_gate_sits_between_self_audit_and_bak_cleanup():
    """失败即 exit 1 ⇒ 必须排在 .bak 清理之前，否则「失败视同未同步」语义失效。"""
    t = SYNC.read_text(encoding="utf-8")
    i_audit = t.index('bash "$SCRIPT_DIR/self-audit-gate.sh"')
    i_gate = t.index("VERSION_TRUTH_TESTS=(")
    i_bak = t.index("BAK_COUNT=$(find")
    assert i_audit < i_gate, "本门排在自审门之前（应在自审门通过后执行）"
    assert i_gate < i_bak, "本门排在 .bak 清理之后 —— 失败将清掉回滚备份"
    # 本门只在非 DRY-RUN 分支生效（DRY-RUN 不写盘，无需校验一致性）
    assert t.index('if [ "$DRY_RUN" == true ]; then') < i_gate, \
        "本门未落在非 DRY-RUN 分支内"


def test_gate_toolchain_missing_is_fail_closed():
    """环境缺 pytest 必须非零退出（不许静默降级为「门跑过」）。"""
    t = SYNC.read_text(encoding="utf-8")
    assert "import pytest" in t, "脚本未做 pytest 可用性探测（缺失时可能静默跳过）"


# --------------------------------------------------------------------------
# 2. 判据有效：整仓副本反向注入（真源零写入）
# --------------------------------------------------------------------------

def test_gate_green_on_truth_repo():
    rc, out = _run_gate(ROOT)
    assert rc == 0, out
    assert "2 passed" in out, f"两条断言未全部执行（可能被改名 / 未收集）：{out}"


def test_gate_detects_stale_readme_prose_version(tmp_path):
    truth = _notes()
    copy_root = _sandbox(tmp_path)
    _break_readme_prose(copy_root)
    rc, out = _run_gate(copy_root)
    assert _notes() == truth, "真源被测试污染（sha256 变了）"
    assert rc != 0, f"反向注入未被检出（RC=0）—— 门退化成永真：{out}"
    assert "test_readme_prose_version_matches_frontmatter" in out, out
    assert "README 正文版本" in out, out


def test_gate_detects_stale_skill_body_version_header(tmp_path):
    truth = _notes()
    copy_root = _sandbox(tmp_path)
    _break_skill_body_header(copy_root)
    rc, out = _run_gate(copy_root)
    assert _notes() == truth, "真源被测试污染（sha256 变了）"
    assert rc != 0, f"反向注入未被检出（RC=0）：{out}"
    assert "test_skill_body_version_header_matches_frontmatter" in out, out
    assert "SKILL.md 正文版本" in out, out


# --------------------------------------------------------------------------
# 3. 端到端：跑脚本本体（副本），验证「拦住 + 点名 + 保留 .bak」与「不误拦」
# --------------------------------------------------------------------------

def test_sync_version_blocks_stale_prose_and_keeps_bak(tmp_path):
    truth = _notes()
    copy_root = _sandbox(tmp_path)
    _stub_self_audit(copy_root)
    _break_readme_prose(copy_root)
    rc, out = _run_sync(copy_root)
    assert _notes() == truth, "真源被测试污染（sha256 变了）"
    assert rc != 0, f"升版后正文错版未被拦（RC=0）—— 缺口仍在：{out}"
    assert GATE_FAIL_MARK in out, f"非零退出但根因不是本门（假阳性断言）：{out}"
    assert "README 正文版本" in out and \
        "test_readme_prose_version_matches_frontmatter" in out, out
    assert list(copy_root.rglob("*.bak.*")), \
        "本门失败却清掉了 .bak —— 「失败视同未同步、备份保留供回滚」语义被破坏"


def test_sync_version_passes_on_consistent_copy(tmp_path):
    truth = _notes()
    copy_root = _sandbox(tmp_path)
    _stub_self_audit(copy_root)
    rc, out = _run_sync(copy_root)
    assert _notes() == truth, "真源被测试污染（sha256 变了）"
    assert rc == 0, f"一致的仓库副本被误拦（假阳性）：{out}"
    assert GATE_PASS_MARK in out, out
