"""门 X：M 门围栏相位 + 围栏错位伪 H1 检测。

背景（教训 #424 沉淀到 v2.12.58）：
  references/_shared/M-Gate-Algorithm.md 曾因 L1048 / L1181 两个多余围栏
  导致 M-Exist-3 / M-Integrity-1 标题被裹进代码块、7 行伪代码注释落到块外
  被渲染为文档 H1。本测试用变异注入验证两道断言：

    X.1  M-Gate-Algorithm.md 围栏总数偶数
    X.2  13 个 M 门标题（8 Form + 3 Exist + 2 Integrity）全部在围栏外
    X.3  围栏外「紧跟关闭符且首字符为 #」的伪 H1 = 0
"""
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GATE = REPO / "scripts" / "self-audit-gate.sh"
MGATE = REPO / "references" / "_shared" / "M-Gate-Algorithm.md"

FENCE = re.compile(r"^[ \t]*(```|~~~)")
MGATE_HEAD = re.compile(r"^#{2,4}\s+M-(Form|Exist|Integrity)-(\d+):")


def run_gate() -> tuple[int, str]:
    """跑 self-audit-gate.sh，截取门 X.* 输出。"""
    r = subprocess.run(
        ["bash", str(GATE)], cwd=REPO, capture_output=True, text=True, timeout=180,
    )
    return r.returncode, r.stdout + r.stderr


def _parse_x_lines(out: str) -> dict[str, bool]:
    """返回 { 'X.1': pass_bool, 'X.2': ..., 'X.3': ... } —— True=pass。

    脚本用 echo -e "${GREEN}✓${NC} 门 X.1: ..." 输出带 ANSI 颜色码，
    先 strip ANSI 再按子串匹配 ✓/✗。
    """
    res = {}
    ansi = re.compile(r"\033\[[0-9;]+m")
    for line in out.splitlines():
        line = ansi.sub("", line)
        m = re.search(r"[✓✗]\s*门 X\.(\d+):", line)
        if not m:
            continue
        idx = f"X.{m.group(1)}"
        res[idx] = line.lstrip().startswith("✓")
    return res


def test_gate_x_baseline_passes():
    """基线：修复后的仓库，门 X 三道断言全过。"""
    rc, out = run_gate()
    results = _parse_x_lines(out)
    assert "X.1" in results and "X.2" in results and "X.3" in results, (
        f"门 X 输出缺失：{results}\n---\n{out[-1500:]}"
    )
    assert rc == 0, f"self-audit-gate.sh 退出码 {rc} ≠ 0\n{out[-1500:]}"
    assert results["X.1"] is True, "X.1（M-Gate 围栏偶数）应为 ✓"
    assert results["X.2"] is True, "X.2（13 个 M 门标题块外）应为 ✓"
    assert results["X.3"] is True, "X.3（无围栏错位伪 H1）应为 ✓"


def test_gate_x2_detects_m_gate_inside_fence():
    """变异：在 M-Gate-Algorithm.md 末尾追加一个被围栏裹的 M-Form-1 标题，门 X.2 必须 FAIL。"""
    if not MGATE.exists():
        pytest.skip("M-Gate-Algorithm.md 不存在")  # type: ignore[name-defined]
    original = MGATE.read_text(encoding="utf-8")
    sentinel = (
        "\n\n## 变异段（测试用）\n\n"
        "```\n"
        "### M-Form-99: 变异标题（应被门 X.2 抓到）\n"
        "伪代码注释\n"
        "```\n"
    )
    try:
        MGATE.write_text(original + sentinel, encoding="utf-8")
        rc, out = run_gate()
        results = _parse_x_lines(out)
        assert "X.2" in results, "门 X.2 输出缺失"
        assert results["X.2"] is False, (
            f"变异后门 X.2 应为 ✗（抓到块内 M-Form-99），实际为 ✓\n{out[-2000:]}"
        )
        assert rc != 0, "self-audit-gate.sh 应以非 0 退出"
    finally:
        MGATE.write_text(original, encoding="utf-8")


def test_gate_x1_detects_odd_fence_count():
    """变异：删一个围栏使总数变奇数，门 X.1 必须 FAIL。"""
    if not MGATE.exists():
        pytest.skip("M-Gate-Algorithm.md 不存在")  # type: ignore[name-defined]
    original = MGATE.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=False)
    # 找第一个裸围栏（不带语言标签）并删除
    fence_idxs = [i for i, l in enumerate(lines) if FENCE.match(l) and l.strip() in ("```", "~~~")]
    if len(fence_idxs) < 2:
        pytest.skip("无足够裸围栏可变异")  # type: ignore[name-defined]
    del lines[fence_idxs[0]]
    try:
        MGATE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        rc, out = run_gate()
        results = _parse_x_lines(out)
        assert "X.1" in results, "门 X.1 输出缺失"
        assert results["X.1"] is False, (
            f"变异后门 X.1 应为 ✗（围栏总数奇数），实际为 ✓\n{out[-2000:]}"
        )
    finally:
        MGATE.write_text(original, encoding="utf-8")


def test_gate_x3_detects_fence_leaked_pseudo_h1():
    """变异：在 M-Gate-Algorithm.md 末尾追加「紧跟围栏关闭的 # 伪 H1」，
    门 X.3 必须 FAIL。"""
    if not MGATE.exists():
        pytest.skip("M-Gate-Algorithm.md 不存在")  # type: ignore[name-defined]
    original = MGATE.read_text(encoding="utf-8")
    sentinel = (
        "\n\n## 变异段 X.3（测试用）\n\n"
        "```\n"
        "伪代码块\n"
        "```\n"
        "# 伪 H1（围栏错位产物，应被门 X.3 抓到）\n"
    )
    try:
        MGATE.write_text(original + sentinel, encoding="utf-8")
        rc, out = run_gate()
        results = _parse_x_lines(out)
        assert "X.3" in results, "门 X.3 输出缺失"
        assert results["X.3"] is False, (
            f"变异后门 X.3 应为 ✗（抓到伪 H1），实际为 ✓\n{out[-2000:]}"
        )
    finally:
        MGATE.write_text(original, encoding="utf-8")
