#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""门 X：Markdown 围栏相位 + 声明式锚点 + 伪 H1 检测。

背景（教训 #424 / #426 / #427）：
  references/_shared/真源/M-Gate-Algorithm.md 曾因两个多余围栏（L1048 / L1181）导致
  M-Exist-3 / M-Integrity-1 标题被裹进代码块、7 行伪代码注释落到块外被渲染为文档 H1。

    X.1  M-Gate-Algorithm.md 围栏总数偶数
    X.2  声明式锚点表（文件 → 锚点正则）的锚点全部在围栏外
    X.3  围栏外「紧跟关闭符且首字符为 #」的伪 H1 = 0
    X.4  全仓 .md 围栏总数均为偶数（未闭合围栏 = 尾部被吞）

  判据全仓扩围（教训 #427）后立即抓到第二例同类缺陷：references/pipeline-readme.md
  7 个围栏（未闭合）⇒ 尾部 57 行被吞进代码块。

约束（教训 #333 / #427 同族）：**变异注入一律在临时副本中进行，真源零写入**。
  旧写法直接写真源再 finally 还原，中途被 kill / 超时就把变异留在真源里
  （工作区不干净 ⇒ 发版前置闸红）。test_mutations_do_not_touch_truth_source 即该约束的护栏。
"""
import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "self-audit-gate.sh"
MGATE = REPO / "references" / "_shared" / "真源" / "M-Gate-Algorithm.md"
PIPE_README = REPO / "references" / "pipeline-readme.md"

FENCE = re.compile(r"^[ \t]*(```|~~~)")
COPY_IGNORE = shutil.ignore_patterns(
    ".git", "outputs", "reports", "memory", "__pycache__", ".pytest_cache", "*.bak.*",
)


FIXTURE_LESSONS = Path(__file__).parent / "fixtures" / "lessons-gate.md"


def run_gate(root: Path) -> tuple[int, str]:
    """跑 root 下的 self-audit-gate.sh，默认使用 hermetic lessons fixture。"""
    env = dict(os.environ)
    env.setdefault("LESSONS_SRC", str(FIXTURE_LESSONS))
    r = subprocess.run(
        ["bash", str(root / "scripts" / "self-audit-gate.sh")],
        cwd=root, env=env, capture_output=True, text=True, timeout=300,
    )
    return r.returncode, r.stdout + r.stderr


def gate_x_results(out: str) -> dict[str, bool]:
    """返回 { 'X.1': pass_bool, ... } —— True=pass。

    脚本用 echo -e "${GREEN}✓${NC} 门 X.1: ..." 输出带 ANSI 颜色码，
    先 strip ANSI 再按子串匹配 ✓/✗。
    """
    res: dict[str, bool] = {}
    ansi = re.compile(r"\033\[[0-9;]+m")
    for line in out.splitlines():
        line = ansi.sub("", line)
        m = re.search(r"[✓✗]\s*门 X\.(\d+):", line)
        if not m:
            continue
        res[f"X.{m.group(1)}"] = line.lstrip().startswith("✓")
    return res


def make_copy(tmp_path: Path) -> Path:
    """整仓副本（排除 .git / 产物 / 备份）—— 变异只注入副本（教训 #333 口径）。"""
    dst = tmp_path / "repo"
    shutil.copytree(REPO, dst, ignore=COPY_IGNORE)
    return dst


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# 基线：修复后的仓库，门 X 四道断言全过（在真源上只读运行）
# --------------------------------------------------------------------------

def test_gate_x_baseline_passes():
    rc, out = run_gate(REPO)
    results = gate_x_results(out)
    for key in ("X.1", "X.2", "X.3", "X.4"):
        assert key in results, f"门 {key} 输出缺失：{results}\n---\n{out[-1500:]}"
        assert results[key] is True, f"{key} 应为 ✓（实际 ✗）\n{out[-2000:]}"
    assert rc == 0, f"self-audit-gate.sh 退出码 {rc} ≠ 0\n{out[-1500:]}"


# --------------------------------------------------------------------------
# 变异注入（全部在临时副本内，真源零写入）
# --------------------------------------------------------------------------

def test_gate_x2_detects_m_gate_anchor_inside_fence(tmp_path):
    """变异：在副本的 M-Gate-Algorithm.md 末尾追加被围栏裹的 M-Form-99 标题 → X.2 必须 ✗。"""
    if not MGATE.exists():
        pytest.skip("M-Gate-Algorithm.md 不存在")
    root = make_copy(tmp_path)
    target = root / MGATE.relative_to(REPO)
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\n\n## 变异段（测试用）\n\n```\n### M-Form-99: 变异标题（应被门 X.2 抓到）\n伪代码注释\n```\n",
        encoding="utf-8",
    )
    _, out = run_gate(root)
    results = gate_x_results(out)
    assert results.get("X.2") is False, f"变异后 X.2 应为 ✗\n{out[-2000:]}"
    assert results.get("X.4") is True, "本变异围栏成对，X.4 不应受影响"


def test_gate_x2_detects_pipeline_readme_anchor_inside_fence(tmp_path):
    """变异：把副本 pipeline-readme.md 的章节锚点裹进围栏 → X.2 必须 ✗（锚点表第二项生效）。"""
    if not PIPE_README.exists():
        pytest.skip("pipeline-readme.md 不存在")
    root = make_copy(tmp_path)
    target = root / PIPE_README.relative_to(REPO)
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\n```\n## 模板加载策略（变异副本，应被门 X.2 抓到）\n```\n",
        encoding="utf-8",
    )
    _, out = run_gate(root)
    results = gate_x_results(out)
    assert results.get("X.2") is False, f"变异后 X.2 应为 ✗（锚点表第二项未生效？）\n{out[-2000:]}"
    assert results.get("X.4") is True, "本变异围栏成对，X.4 不应受影响"


def test_gate_x1_detects_odd_fence_count(tmp_path):
    """变异：删一个裸围栏使 M-Gate 围栏总数变奇数 → X.1 必须 ✗。"""
    if not MGATE.exists():
        pytest.skip("M-Gate-Algorithm.md 不存在")
    root = make_copy(tmp_path)
    target = root / MGATE.relative_to(REPO)
    lines = target.read_text(encoding="utf-8").splitlines()
    fence_idxs = [i for i, l in enumerate(lines) if FENCE.match(l) and l.strip() in ("```", "~~~")]
    if len(fence_idxs) < 2:
        pytest.skip("无足够裸围栏可变异")
    del lines[fence_idxs[0]]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _, out = run_gate(root)
    results = gate_x_results(out)
    assert results.get("X.1") is False, f"变异后 X.1 应为 ✗（围栏奇数）\n{out[-2000:]}"


def test_gate_x3_detects_fence_leaked_pseudo_h1(tmp_path):
    """变异：追加「紧跟围栏关闭的 # 伪 H1」→ X.3 必须 ✗。"""
    if not MGATE.exists():
        pytest.skip("M-Gate-Algorithm.md 不存在")
    root = make_copy(tmp_path)
    target = root / MGATE.relative_to(REPO)
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\n\n## 变异段 X.3（测试用）\n\n```\n伪代码块\n```\n# 伪 H1（围栏错位产物，应被门 X.3 抓到）\n",
        encoding="utf-8",
    )
    _, out = run_gate(root)
    results = gate_x_results(out)
    assert results.get("X.3") is False, f"变异后 X.3 应为 ✗\n{out[-2000:]}"


def test_gate_x4_detects_unclosed_fence_repo_wide(tmp_path):
    """变异：在副本里新增一个含**未闭合围栏**的 .md（全仓扫描面）→ X.4 必须 ✗。

    这正是 references/pipeline-readme.md 的真实缺陷形态（教训 #427）：
    围栏总数为奇数 ⇒ 文件尾部的正文与标题整块被吞进代码块。
    """
    root = make_copy(tmp_path)
    (root / "_mutant_unclosed.md").write_text(
        "# 变异文件（测试用）\n\n```\n未闭合围栏之后的正文会被吞进代码块\n", encoding="utf-8"
    )
    _, out = run_gate(root)
    results = gate_x_results(out)
    assert results.get("X.4") is False, f"变异后 X.4 应为 ✗（未闭合围栏未被抓到）\n{out[-2000:]}"


# --------------------------------------------------------------------------
# 护栏：变异不写真源 + 锚点表不得被掏空
# --------------------------------------------------------------------------

def test_mutations_do_not_touch_truth_source(tmp_path):
    """本文件的变异注入只作用于副本：跑一次完整变异后，真源字节不变。"""
    watched = [p for p in (MGATE, PIPE_README) if p.exists()]
    before = {p: sha256(p) for p in watched}
    test_gate_x4_detects_unclosed_fence_repo_wide(tmp_path)
    test_gate_x2_detects_m_gate_anchor_inside_fence(tmp_path / "b")
    after = {p: sha256(p) for p in watched}
    assert before == after, f"真源被变异测试改写：{ {str(k): (v, after[k]) for k, v in before.items() if v != after[k]} }"


def test_anchor_table_registers_known_docs():
    """锚点表不得被掏空/写错：登记的每个文件必须存在，且至少覆盖门 X 立项时的两份文档。

    分隔符必须是 `@@`：锚点正则内含 `|` 交替，若用 `|` 分隔会被 `${x%%|*}` 截断成
    失效正则 ⇒ 本门变空转绿灯（v2.12.58 实测踩到，由 X.2 变异单测抓出）。
    """
    src = GATE.read_text(encoding="utf-8")
    m = re.search(r"ANCHOR_TABLE=\((.*?)\n\)", src, re.S)
    assert m, "自审门缺 ANCHOR_TABLE 声明"
    entries = re.findall(r'^\s*"([^"]+)"\s*$', m.group(1), re.M)
    assert entries, "ANCHOR_TABLE 为空"
    files = []
    for entry in entries:
        parts = entry.split("@@")
        assert len(parts) == 3, f"锚点表条目必须为「文件@@正则@@说明」三段：{entry[:60]}"
        f, pattern, label = parts
        assert pattern and label, f"锚点表条目缺正则或说明：{entry[:60]}"
        assert (REPO / f).exists(), f"锚点表登记了不存在的文件：{f}"
        files.append(f)
    assert "references/_shared/真源/M-Gate-Algorithm.md" in files
    assert "references/pipeline-readme.md" in files
