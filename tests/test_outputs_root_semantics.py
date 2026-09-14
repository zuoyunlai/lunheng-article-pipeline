#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_outputs_root_semantics.py — OUTPUTS_ROOT 语义同源回归门（2026-09-14）

背景（2026-09-14 隔离构建实测发现）：
  同族脚本对环境变量 `OUTPUTS_ROOT` 的语义**不一致** ——
    build-clawhub-release.sh 第 28 行 / publish-clawhub.sh 第 32 行
      → 当「**发布根**」：默认值 = `$HOME/lunheng-build/lunheng-outputs/clawhub-release`
    strip-internal-leakage.sh / self-audit-gate.sh 门 G / cleanup-skill-store.sh
      → 当「**输出总根**」：再拼 `/clawhub-release`
  默认（未设该变量）时三者路径恰好一致；但调用方**显式设置**时（如隔离构建
  `OUTPUTS_ROOT=/tmp/x`）：
    build 写 `/tmp/x/<ver>`，而门 G 查 `/tmp/x/clawhub-release/<ver>`
    ⇒ 门 G 退化为「包未生成」的**假绿灯**（发布前包一致性硬校验永久哑火），
      剥离脚本探测到不存在的默认根（2026-09-14 已另行修掉其「零输出静默 exit 1」）。

本文件锁死（统一口径 = 「输出总根」，与 gate/strip/cleanup 多数派一致）：
  ① 显式 `OUTPUTS_ROOT=<tmp>`：build 产物目录 == gate G 查找目录 == strip 默认目录（**三者同源**）
  ② **不设** `OUTPUTS_ROOT`：三处仍解析到 `~/lunheng-build/lunheng-outputs/clawhub-release/...`
     （默认行为完全不变，默认路径不改）
  ③ 反向：`OUT_ROOT=` 默认值不得再自带 `/clawhub-release`（防语义回退到「发布根」）
  ④ 功能：真跑隔离 build（LUNHENG_ALLOW_NO_GIT=1），断言产物**只**落在总根下

同源手法：断言直接从**脚本真实文本**里抽出赋值行求值（不复写表达式），
  故脚本一日改回旧语义，本门即刻变红（而不是「测试自己算对」）。
"""
import os
import pathlib
import re
import shutil
import subprocess

ROOT = pathlib.Path(__file__).parent.parent
BUILD = ROOT / "scripts" / "build-clawhub-release.sh"
PUBLISH = ROOT / "scripts" / "publish-clawhub.sh"
STRIP = ROOT / "scripts" / "strip-internal-leakage.sh"
GATE = ROOT / "scripts" / "self-audit-gate.sh"
CLEANUP = ROOT / "scripts" / "cleanup-skill-store.sh"

VER = re.search(r'^\s*version:\s*"?([0-9]+\.[0-9]+\.[0-9]+)"?\s*$',
                (ROOT / "SKILL.md").read_text(encoding="utf-8"), re.M).group(1)
REL = "lunheng-build/lunheng-outputs/clawhub-release"


# ---------------- 同源求值：从脚本源码抽赋值行，交给 bash 求值 ----------------

def _resolve(script: pathlib.Path, names, tail: str, preset: dict = None, env=None):
    """抽出脚本里 `NAME=` 开头的赋值行（脚本真实文本），在给定 env 下求值 `tail`。

    直接消费脚本原文 ⇒ 「同源」：断言的是脚本**现在**怎么解析，而不是测试自己怎么推。
    """
    src = script.read_text(encoding="utf-8")
    lines = []
    for name in names:
        hit = next((ln for ln in src.splitlines() if ln.strip().startswith(f"{name}=")), None)
        assert hit is not None, f"{script.name} 中未找到赋值行 `{name}=`"
        lines.append(hit)
    program = "set -euo pipefail\n"
    for k, v in (preset or {}).items():
        program += f"{k}={v}\n"
    program += "\n".join(lines) + "\n"
    program += f'printf "%s" "{tail}"\n'
    r = subprocess.run(["bash", "-c", program], capture_output=True, text=True,
                       env=env or os.environ)
    assert r.returncode == 0, f"{script.name} 赋值行求值失败：{r.stderr}"
    return r.stdout.strip()


def _env(outputs_root=None, home=None):
    """构造 env：home 给定则同时改写 HOME；outputs_root 为 None 时**删除**该变量（= 未设）"""
    env = {**os.environ}
    if home is not None:
        env["HOME"] = str(home)
    if outputs_root is None:
        env.pop("OUTPUTS_ROOT", None)
    else:
        env["OUTPUTS_ROOT"] = str(outputs_root)
    return env


def _build_dir(env, version):
    return _resolve(BUILD, ["OUT_ROOT"], "$OUT_ROOT/$VERSION", {"VERSION": version}, env)


def _publish_dir(env, version):
    return _resolve(PUBLISH, ["OUT_ROOT"], "$OUT_ROOT/$VERSION", {"VERSION": version}, env)


def _gate_dir(env, version):
    return _resolve(GATE, ["OUTPUTS_ROOT", "PURIFY_DIR"], "$PURIFY_DIR",
                    {"EXPECTED_VERSION": version}, env)


def _strip_dir(env):
    """strip 无参时的默认目录：<总根>/clawhub-release/<最新版本>，无版本目录时退化为 latest"""
    return _resolve(STRIP, ["_OCR"], "$_OCR/latest", {}, env)


def _cleanup_dir(env):
    return _resolve(CLEANUP, ["OUTPUTS_ROOT"], "$OUTPUTS_ROOT", {}, env)


# ---------------- ① 显式 OUTPUTS_ROOT：三者同源 ----------------

def test_explicit_outputs_root_is_single_total_root(tmp_path):
    root = tmp_path / "iso"
    env = _env(outputs_root=root)
    want = f"{root}/clawhub-release/{VER}"

    assert _build_dir(env, VER) == want, "build 未把 OUTPUTS_ROOT 当「输出总根」"
    assert _gate_dir(env, VER) == want, "门 G 查找目录与 build 产物目录不同源"
    assert _publish_dir(env, VER) == want, "publish 待发布目录与 build 产物目录不同源"
    assert _strip_dir(env) == f"{root}/clawhub-release/latest", "strip 默认目录不同源"
    assert _cleanup_dir(env) == str(root), "cleanup 未把 OUTPUTS_ROOT 当输出总根"

    # 点名断言：三者同源（事故的直接成因就是这一条不成立）
    assert _build_dir(env, VER) == _gate_dir(env, VER) == _publish_dir(env, VER) == want


# ---------------- ② 未设 OUTPUTS_ROOT：默认行为完全不变 ----------------

def test_default_path_unchanged_when_unset(tmp_path):
    home = tmp_path / "home"
    env = _env(home=home)  # OUTPUTS_ROOT 不设
    want = f"{home}/{REL}/{VER}"

    assert _build_dir(env, VER) == want
    assert _gate_dir(env, VER) == want
    assert _publish_dir(env, VER) == want
    assert _strip_dir(env) == f"{home}/{REL}/latest"
    assert _cleanup_dir(env) == str(home / "lunheng-build" / "lunheng-outputs")


# ---------------- ③ 反向：默认值不得自带 /clawhub-release ----------------

def test_default_values_do_not_embed_clawhub_release():
    """旧语义的指纹 = 默认值里出现 `lunheng-outputs/clawhub-release`（发布根）。"""
    for script in (BUILD, PUBLISH):
        line = next(ln for ln in script.read_text(encoding="utf-8").splitlines()
                    if ln.strip().startswith("OUT_ROOT="))
        assert "lunheng-outputs/clawhub-release" not in line, \
            f"{script.name} 的 OUTPUTS_ROOT 默认值又变回「发布根」语义：{line.strip()}"


# ---------------- ④ 功能：strip 无参探测落在总根，且失败可见 ----------------

def test_strip_default_probe_uses_total_root(tmp_path):
    pkg = tmp_path / "clawhub-release" / VER
    pkg.mkdir(parents=True)
    (pkg / "v.md").write_text("正文无锚点。\n", encoding="utf-8")

    r = subprocess.run(["bash", str(STRIP)], capture_output=True, text=True, cwd=str(ROOT),
                       env=_env(outputs_root=tmp_path))
    assert r.returncode == 0, f"应命中 {pkg}：rc={r.returncode}\n{r.stdout}\n{r.stderr}"
    assert str(pkg) in r.stdout, f"strip 默认目录不是 <总根>/clawhub-release/<ver>：{r.stdout!r}"


def test_strip_probe_visible_when_root_missing(tmp_path):
    """总根下无包 → 非零退出且打印可见错误（不得零输出静默死；7c31281 修复不许回退）"""
    r = subprocess.run(["bash", str(STRIP)], capture_output=True, text=True, cwd=str(ROOT),
                       env=_env(outputs_root=tmp_path / "nope"))
    assert r.returncode != 0
    assert "pkg dir not found" in r.stdout and "clawhub-release" in r.stdout


# ---------------- ⑤ 功能端到端：真跑隔离 build，产物只落总根 ----------------

def test_build_output_lands_in_total_root(tmp_path):
    dst = tmp_path / "copy"
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(
        ".git", "outputs", "__pycache__", ".pytest_cache"))
    out_root = tmp_path / "iso"

    r = subprocess.run(["bash", str(dst / "scripts" / "build-clawhub-release.sh"), VER],
                       capture_output=True, text=True, cwd=str(dst), timeout=900,
                       env={**os.environ, "OUTPUTS_ROOT": str(out_root),
                            "LUNHENG_ALLOW_NO_GIT": "1"})
    assert r.returncode == 0, f"隔离 build 失败：rc={r.returncode}\n{r.stdout[-3000:]}\n{r.stderr[-2000:]}"

    pkg = out_root / "clawhub-release" / VER
    assert (pkg / "SKILL.md").is_file(), f"产物未落在总根下：{pkg}\n{r.stdout[-1500:]}"
    assert not (out_root / VER).exists(), \
        "build 把产物写到了「发布根」语义路径（<OUTPUTS_ROOT>/<ver>）——语义分歧回归"
