#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_strip_internal_leakage_delimiters.py — 净化剥离「分隔符变体」回归门（v2.12.40 候选新增）

背景（2026-09-14 发版实测，v2.12.39）：
  `bash scripts/build-clawhub-release.sh 2.12.39` 首次返回 EXIT=1，但终末输出只剩
  「🧹 清理内部痕迹（教训 #296）...」一行 —— 因为 build 脚本把剥离步骤的 stdout 吞进 /dev/null。
  单跑 `scripts/strip-internal-leakage.sh` 才看到真因：净化包内
  `references/templates/任务简报-template.md` 残留
      ...（含 AI 使用声明/致谢），教训 #277；口径真源 = ...
  —— `，教训 #N；`（全角逗号 + 教训 #N + 全角分号）这种**分隔符夹持**写法不在任何正则的
  前瞻类内（旧类只有 `，。、！？）]` 与行尾），残留门 fail-closed 阻断整次构建。
  已核实 v2.12.38 净化包内同样残留（长期缺口，非该版引入）。

本文件锁死的样本（教训 #334：门类改动必须配「注入即必被剥离」的正向样本）：
  ① 正向：v2.12.38 净化包内真实泄漏行（必中样本）→ 必被剥除且句子仍可读
  ② 正向：`，教训 #N；` / `；教训 #N` / `、教训 #N` / `：教训 #N` / 半角等价 → 全数剥除
  ③ 反例：SVG 色值 / 合法内部编号（角色卡 #10 等）不得被误伤
  ④ 负向：非 .md 文件内残留仍必须 fail-closed（剥除能力增强不得削弱残留门）
  ⑤ 幂等：二次运行不得再改动文件（无震荡）
  ⑥ 元测试：build 脚本不得静默吞掉子步骤输出（可见性修复不得回退）
  ⑦ 元测试：自审门门 P 探针必须含「分隔符夹持」样本（门与剥离规则同源演进）
  ⑧ 静默失败：默认根探测不得在打出任何字之前把脚本拖死（失败原因必须可见）
"""
import os
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).parent.parent
STRIP = ROOT / "scripts" / "strip-internal-leakage.sh"
BUILD = ROOT / "scripts" / "build-clawhub-release.sh"
GATE = ROOT / "scripts" / "self-audit-gate.sh"

# v2.12.38 净化包内实测泄漏行（逐字复制，勿改写成「更干净」的样子——
# 它就是这个缺口的必中样本；改写会让本回归门失去与真实事故的对应关系）
HISTORICAL_LINE = (
    "- **目标篇幅**：（字数或页数；**字数 = 纯中文字符数（仅正文，不含文末附录："
    "参考文献/数据来源/案例来源/先行者文献/AI 使用声明/致谢），教训 #277；"
    "口径真源 = [`字数判定表.md`](../_shared/字数判定表.md) §一**）"
)

# 分隔符夹持变体：每条都必须被剥成「无 `教训 #`」且保留 `口径真源` 这句正文
SEPARATOR_VARIANTS = [
    ("全角逗号 + 全角分号", "> 见 `x.md`（含 AI 使用声明/致谢），教训 #277；口径真源 = `y.md`"),
    ("前导全角分号", "> 见 `x.md`；教训 #278，口径真源 = `y.md`"),
    ("顿号", "> 见 `x.md`、教训 #279，口径真源 = `y.md`"),
    ("全角冒号", "> 正文说明：教训 #280，口径真源 = `y.md`"),
    ("半角逗号 + 半角分号", "> 见 `x.md`, 教训 #281; 口径真源 = `y.md`"),
    ("起句（无前导分隔符，后随分号）", "> 教训 #282；口径真源 = `y.md`"),
    ("紧贴汉字 + 全角分号", "> 某段教训 #283；口径真源 = `y.md`"),
]

# 不变量：这些 token 不属于「教训锚点」，任何剥离轮次都不得碰
INVARIANTS = [
    "`#2A2826`",          # SVG 长色值
    "`#abc`",             # SVG 短色值
    "角色卡 #10",          # 合法内部编号
    "T8 必查项 #15-19",    # 合法编号链
]


def _strip(tmp_path, files: dict):
    """把 files 写进临时目录，跑真剥离脚本，返回 (CompletedProcess, {相对路径: 文本})"""
    for name, text in files.items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    r = subprocess.run(["bash", str(STRIP), str(tmp_path)],
                       capture_output=True, text=True, cwd=str(ROOT))
    out = {name: (tmp_path / name).read_text(encoding="utf-8") for name in files}
    return r, out


# ---------------- ① 必中样本：v2.12.38 真实泄漏行 ----------------

def test_historical_leak_line_is_stripped(tmp_path):
    r, out = _strip(tmp_path, {"refs/任务简报-template.md": HISTORICAL_LINE + "\n"})
    text = out["refs/任务简报-template.md"]
    assert r.returncode == 0, f"剥离脚本应成功剥离该行，实际 rc={r.returncode}\n{r.stdout}\n{r.stderr}"
    assert "教训 #" not in text, f"历史泄漏行未被剥除：{text!r}"
    # 行为断言：不只是「字符串消失」，正文必须仍可读
    for token in ("AI 使用声明/致谢", "口径真源", "字数判定表.md"):
        assert token in text, f"剥离误伤正文，丢了 {token}：{text!r}"
    assert "，；" not in text, f"剥离留下残迹标点：{text!r}"


# ---------------- ② 分隔符变体全数剥除 ----------------

@pytest.mark.parametrize("label,line", SEPARATOR_VARIANTS, ids=[v[0] for v in SEPARATOR_VARIANTS])
def test_separator_variants_are_stripped(tmp_path, label, line):
    r, out = _strip(tmp_path, {"v.md": line + "\n"})
    text = out["v.md"]
    assert r.returncode == 0, f"[{label}] 残留门应通过，实际 rc={r.returncode}\n{r.stdout}"
    assert "教训 #" not in text, f"[{label}] 未被剥除：{text!r}"
    assert "口径真源" in text, f"[{label}] 剥离误伤正文：{text!r}"


# ---------------- ③ 反例：不变量不得被误伤 ----------------

def test_invariants_not_harmed(tmp_path):
    body = "\n".join(["正文引用见相关说明。", "", *INVARIANTS, ""])
    r, out = _strip(tmp_path, {"inv.md": body})
    assert r.returncode == 0, f"无锚点文件不应导致失败：rc={r.returncode}\n{r.stdout}"
    text = out["inv.md"]
    for token in INVARIANTS:
        assert token in text, f"不变量被误伤：{token}（{text!r}）"


# ---------------- ④ 负向：残留门仍 fail-closed ----------------
def test_residual_gate_still_fail_closed(tmp_path):
    """剥离能力增强不得削弱残留门：非 .md 文件内的锚点照旧 must-fail"""
    r, out = _strip(tmp_path, {
        "clean.md": "正文无锚点。\n",
        "notes.txt": "残留锚点 教训 #999 不应被静默放过\n",
    })
    assert r.returncode != 0, "残留锚点应使脚本非零退出（fail-closed）"
    assert "WARNING" in r.stdout and "教训 #" in r.stdout, "失败时必须打印残留清单"


# ---------------- ⑤ 幂等 ----------------
def test_strip_is_idempotent(tmp_path):
    r1, out1 = _strip(tmp_path, {"v.md": HISTORICAL_LINE + "\n"})
    assert r1.returncode == 0
    first = out1["v.md"]
    r2 = subprocess.run(["bash", str(STRIP), str(tmp_path)],
                        capture_output=True, text=True, cwd=str(ROOT))
    second = (tmp_path / "v.md").read_text(encoding="utf-8")
    assert r2.returncode == 0, f"二次运行不应失败：{r2.stdout}"
    assert first == second, "剥离不幂等（二次运行仍改动文件）"


# ---------------- ⑥ 元测试：build 脚本不得吞掉子步骤输出 ----------------

def test_build_script_surfaces_substep_output():
    src = BUILD.read_text(encoding="utf-8")
    for name in ("strip-internal-leakage.sh", "strip-anchor-residue.py"):
        assert f'{name}" "$OUT_DIR" >/dev/null' not in src, \
            f"{name} 的调用又回到了静默吞输出（失败将不可见）"
    # 失败分支内必须「先透出输出，后 exit 1」（否则日志拿不到原因）
    for marker in ("❌ 内部痕迹剥离失败", "❌ 编号锚点残留清理失败"):
        at = src.index(marker)
        branch = src[at:]
        branch = branch[:branch.index("exit 1")]
        assert "tail -n 40" in branch, f"{marker} 失败分支未透出子步骤输出：{branch!r}"
        assert "2>&1" in src[:at], f"{marker} 之前未见子步骤输出捕获（2>&1）"


# ---------------- ⑧ 静默失败：默认根探测不得把脚本拖死 ----------------

def test_explicit_dir_ignores_missing_default_root(tmp_path):
    """显式传目录时，无关的默认根探测不得静默拖死脚本（同族：失败必须可见）。

    2026-09-14 实测：`OUTPUTS_ROOT=<不存在的根>` + 显式目录 → 旧实现**无条件**探测默认根，
    配合 `set -euo pipefail` 在打出任何字之前 exit 1（零输出）——build 侧即使已加
    「失败透出子步骤输出」也只能打印一个空块，排障信息仍为 0。
    """
    (tmp_path / "v.md").write_text("正文无锚点。\n", encoding="utf-8")
    env = {**os.environ, "OUTPUTS_ROOT": str(tmp_path / "no-such-root")}
    r = subprocess.run(["bash", str(STRIP), str(tmp_path)], capture_output=True, text=True,
                       cwd=str(ROOT), env=env)
    assert r.returncode == 0, f"应正常完成，实际 rc={r.returncode}（stdout={r.stdout!r}）"
    assert "=== Stripping internal leakage" in r.stdout, "不得零输出静默死"


def test_missing_default_root_without_arg_reports_visibly(tmp_path):
    """无参 + 默认根不存在 → 必须非零退出**且**打印可见错误（不是静默退出）"""
    env = {**os.environ, "OUTPUTS_ROOT": str(tmp_path / "no-such-root")}
    r = subprocess.run(["bash", str(STRIP)], capture_output=True, text=True,
                       cwd=str(ROOT), env=env)
    assert r.returncode != 0
    assert "ERROR: pkg dir not found" in r.stdout, f"失败原因必须可见：{r.stdout!r}"


# ---------------- ⑦ 元测试：自审门门 P 探针与剥离规则同源 ----------------

def test_gate_p_probe_covers_separator_variant():
    src = GATE.read_text(encoding="utf-8")
    probe_at = src.index("门 P")
    assert "，教训 #" in src[probe_at:], "门 P 探针未覆盖「分隔符夹持」样本"
    assert "分隔符夹持引用未剥除" in src[probe_at:], "门 P 探针缺「未剥除」断言"
