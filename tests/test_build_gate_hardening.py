#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_build_gate_hardening.py — 构建链「全包白名单准入 + 正向门补强」测试

背景（2026-09-19 第四批审计，C-1 推广 / C-4 / C-5 / C-6 / C-7）：
  四类缺陷的共同形态是 **fail-open** —— 门在「该炸的时候不炸」，而不是炸错：

  · C-1 推广（P0 同源）：净化包的排除清单是**黑名单式**（不在 `--exclude` 里就默认入包）。
    `_shared/` 已改白名单（v2.12.63），但 `agents/ templates/ gates/ checkers/ dispatch/`
    与 `references/` 顶层仍是黑名单 ⇒ 新增一个维护者内档 = 默认出厂。
  · C-4（P2）：被排除文档的引用（死链）由 purify() 逐条硬编码 sed 中和 ⇒ 新增一个被排除
    文件就漏一次，规则与排除清单两处必然漂移。
  · C-5（P2）：正向完整性门**只覆盖 `*.md`** ⇒ 非 md 文本资产（yaml/json/txt/toml）被整篇
    删空也无人报错（负向扫描只报「违规命中数 ≠ 0」）。
  · C-6（P2）：正向门按**字符保留率**判，分母异常小或为零时比率可恒过
    （0→0、10→10 都算 100%）⇒ 门退化为恒真。
  · C-7（P2）：`allow_empty=yes` 是「真源零命中仍放行」的唯一逃生口，理由字段可空 ⇒
    这条路退化成「标注一下即可关掉真源侧守卫」。

本模块锁三件事：**源侧不变量**（清单/理由表双向闭合）、**门真的存在**（防被静默移除）、
**门真的拦得住**（故障注入实测，而非只读源码断言）。
"""
import os
import pathlib
import re
import shutil
import subprocess

import pytest

from conftest import tracked_tree

ROOT = pathlib.Path(__file__).parent.parent
BUILD = ROOT / "scripts" / "build-clawhub-release.sh"
MANIFEST = ROOT / "scripts" / ".pkg-manifest.txt"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
}


def _src():
    return BUILD.read_text(encoding="utf-8")


def _manifest_entries():
    return [l for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]


def _copy_repo(tmp_path):
    """复制仓库到临时目录并建立 git（构建的非 git 门是 fail-closed，必须有 .git）。"""
    dst = tmp_path / "copy"
    tracked_tree(ROOT, dst)
    env = {**os.environ, **GIT_ENV}
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base"]):
        subprocess.run(cmd, cwd=str(dst), env=env, capture_output=True, text=True)
    return dst


def _build(repo, out_root, version="9.9.9", extra_env=None):
    return subprocess.run(
        ["bash", str(repo / "scripts" / "build-clawhub-release.sh"), version],
        capture_output=True, text=True, cwd=str(repo),
        env={**os.environ, "OUTPUTS_ROOT": str(out_root), **(extra_env or {})})


# ---------------- 源侧不变量：随包清单（全包白名单准入）----------------

def test_pkg_manifest_exists_sorted_and_unrotten():
    """清单必须存在、非空、ASCII-优先排序、无重复，且每条都能在真源找到（防清单腐烂）。"""
    assert MANIFEST.is_file(), \
        "scripts/.pkg-manifest.txt 缺失 —— 全包白名单准入门无真源可比（C-1 推广的根）"
    entries = _manifest_entries()
    assert entries, "随包清单为空 = 准入门空转，按失败处理"
    assert entries == sorted(entries), \
        f"清单未按 LC_ALL=C sort 排序（diff 不可审）：{[a for a, b in zip(entries, sorted(entries)) if a != b][:5]}"
    assert len(entries) == len(set(entries)), "清单存在重复条目"
    # 反向：清单里的文件必须真实存在于真源（否则构建时「清单已登记但包内缺失」恒炸）
    missing = [e for e in entries if not (ROOT / e).is_file()]
    assert not missing, f"清单登记了真源不存在的文件（清单腐烂）：{missing}"
    # 清单是维护者资产，不得随包分发 —— 由脚本内的显式断言锁（此处锁断言存在）
    assert "scripts/.pkg-manifest.txt" in _src()


def test_manifest_gate_has_all_fail_closed_branches():
    """准入门必须包含全部 fail-closed 分支：缺失 / 空清单 / 清单自身入包 / 双向差异。"""
    src = _src()
    assert "PKG_MANIFEST=" in src
    assert "随包清单缺失" in src, "缺「清单缺失」分支 → 删掉清单即可关掉整门"
    assert "随包清单为空" in src, "缺「空清单」分支 → 置空清单即可放行一切"
    assert "清单是维护者资产，不得随包分发" in src, "缺「清单自身入包」断言"
    assert "包内有但清单未登记" in src and "清单已登记但包内缺失" in src, \
        "缺双向差异打印（只查一个方向会漏掉「误删」或「默认入包」）"
    # 门必须在复制步骤之后（否则无包可比）
    assert src.index("PKG_MANIFEST=") > src.index("---- 2a.")


# ---------------- 源侧不变量：豁免理由表（C-7）----------------

def test_exemption_reasons_are_closed_and_substantive():
    """`allow_empty=yes` 条目 ↔ 理由表必须**双向闭合**，且理由有实质长度。

    这条正是「空理由即豁免」缺的那道门：只校验格式/基数时，标一个 yes 就能关掉真源侧守卫。
    """
    src = _src()
    block = src.split("RULE_EMPTY_REASONS=(")[1].split("\n)")[0]
    reasons = dict(re.findall(r"'([^'|]+)\|([^']+)'", block))
    checks = re.findall(r"\n  '([^'|]+)\|([^'|]*)\|(warn|critical)\|(yes|no)'", src)
    assert checks, "未解析到 RULE_CHECKS 条目（规则自检表被改格式？）"
    yes_names = {n for n, _, _, a in checks if a == "yes"}

    min_chars = int(re.search(r"RULE_REASON_MIN_CHARS=(\d+)", src).group(1))
    missing = sorted(yes_names - set(reasons))
    orphans = sorted(set(reasons) - yes_names)
    short = sorted(n for n in reasons if len(reasons[n]) < min_chars)
    assert not missing, f"allow_empty=yes 却无登记理由（= 静默关闭守卫）：{missing}"
    assert not orphans, f"理由表孤儿（对应条目已删除/改 no ⇒ 理由表腐烂）：{orphans}"
    assert not short, f"豁免理由过短（< {min_chars}）：{short}"
    # 理由本身不得是占位词
    for name, reason in reasons.items():
        assert "待补" not in reason and "TODO" not in reason.upper(), f"'{name}' 理由是占位词"


# ---------------- 门存在性（防被静默移除）----------------

def test_deadlink_gate_is_programmatic_and_declared_once():
    """C-4：死链中和必须由「排除清单推导」而非逐条硬编码 sed。"""
    src = _src()
    assert "PKG_EXCLUDED_DOC_PATHS=(" in src, "被排除文档清单缺失 —— 死链门无真源"
    excl = re.findall(r"PKG_EXCLUDED_DOC_PATHS=\((.*?)\n\)", src, re.S)[0]
    assert len(re.findall(r"'", excl)) >= 2 * 10, "被排除文档清单条目过少（疑似被清空）"
    assert "中和包内死链" in src, "缺死链中和门"
    assert "raise SystemExit(1)" in src.split("PKG_EXCLUDED_DOC_PATHS=(")[1][:6000], \
        "死链门缺 fail-closed 退出"
    # 旧实现（逐条硬编码路径的 sed）不得仍是活代码
    assert not re.search(r"^\s*sed .*README-模板拆分方案", src, re.M), \
        "仍有逐条硬编码的死链中和 sed（C-4 的成因：新增被排除文件就漏一次）"


def test_nonmd_positive_gate_present():
    """C-5：非 md 文本资产必须有同款正向校验（存在性 + 非空 + 保留率）。"""
    src = _src()
    assert "非 md 正向完整性未通过" in src
    assert "PKG_SNAPSHOT_NONMD" in src
    assert re.search(r"exts = \{'\.yaml', '\.yml', '\.json', '\.txt', '\.toml'\}", src), \
        "非 md 扫描扩展面缺失或与 §扫描面 SCAN_INCLUDES 口径不一致"
    assert "'被清空（0 字符）'" in src or "被清空（0 字符）" in src


def test_baseline_floor_gate_present():
    """C-6：比率分母必须有下限守卫（否则保留率恒过）。"""
    src = _src()
    assert "PKG_MIN_BASELINE_CHARS" in src
    assert "基线下限守卫未通过" in src
    assert "比率分母为零" in src
    # 下限守卫必须在快照生成之后、正向门之前（否则无从判定）
    snap_at = src.index('pkg-integrity.py" snapshot')
    floor_at = src.index("基线下限守卫未通过")
    nonmd_at = src.index("非 md 正向完整性未通过")
    assert snap_at < floor_at, "基线下限守卫跑在快照生成之前 —— 无基线可判，门形同虚设"
    assert floor_at < nonmd_at, "基线下限守卫应在非 md 正向门之前（先证分母有判别力）"


# ---------------- 故障注入：门真的拦得住 ----------------

@pytest.fixture(scope="module")
def built_pkg(tmp_path_factory):
    """真实构建一次（本模块内复用），返回 (rc, blob, pkg_path)。"""
    out_root = tmp_path_factory.mktemp("out")
    r = _build(ROOT, out_root, version="2.12.63")
    return r, out_root / "clawhub-release" / "2.12.63"


def test_real_build_matches_manifest_exactly(built_pkg):
    """全包白名单准入：真实构建后，包内文件集必须与清单**精确相等**。"""
    r, pkg = built_pkg
    assert r.returncode == 0, f"构建失败：\n{(r.stderr + r.stdout)[-2000:]}"
    actual = sorted(str(p.relative_to(pkg)) for p in pkg.rglob("*") if p.is_file())
    assert actual == sorted(_manifest_entries()), (
        "包内文件集与 scripts/.pkg-manifest.txt 不一致："
        f"多={sorted(set(actual) - set(_manifest_entries()))[:5]} "
        f"少={sorted(set(_manifest_entries()) - set(actual))[:5]}"
    )
    # 清单自身不得随包出厂（维护者资产）
    assert not (pkg / "scripts" / ".pkg-manifest.txt").exists(), "随包清单被分发进包"
    assert not (pkg / "scripts").exists(), "scripts/ 未被剥离出包"


def test_real_build_has_no_deadlink_to_excluded_docs(built_pkg):
    """C-4 产物侧反向断言：包内任何 .md 都不得再引用被排除的仓库文档。"""
    r, pkg = built_pkg
    assert r.returncode == 0
    dead = []
    for p in pkg.rglob("*.md"):
        t = p.read_text(encoding="utf-8", errors="replace")
        for victim in ("README-模板拆分方案.md", "设计文档-架构.md", "设计文档-哲学.md"):
            if victim in t:
                dead.append(f"{p.relative_to(pkg)} → {victim}")
    assert not dead, f"包内仍有指向被排除文档的死链：{dead}"


def test_build_fails_when_baseline_floor_raised(tmp_path):
    """C-6 故障注入：把下限抬到高于任何真实文件 ⇒ 必须 fail（证明下限真的在判）。

    注入的是**环境变量**（脚本公开的阈值），不是改源码 —— 门被静默移除时本用例会挂在
    「未命中基线下限守卫」而不是 null 变量上。
    """
    out_root = tmp_path / "out"
    r = _build(ROOT, out_root, version="9.9.9", extra_env={"PKG_MIN_BASELINE_CHARS": "100000"})
    blob = r.stderr + r.stdout
    assert r.returncode != 0, "基线下限被抬高到不可能满足，构建仍成功 —— 下限守卫失效"
    assert "基线下限守卫未通过" in blob, f"未命中基线下限守卫：\n{blob[-1500:]}"


def test_build_blocks_tracked_unregistered_file_at_package_scope(tmp_path):
    """C-1 推广故障注入：**已跟踪**但未登记的文件落在 `_shared/` 之外 ⇒ 必须拦住。

    这正是 v2.12.42 内档泄漏的成因（新文件默认入包）。放在 `references/agents/`
    才能证明准入门的作用面已从 `_shared/` 扩到**全包**（`_shared/` 门会先炸，故不能用它）。
    """
    dst = _copy_repo(tmp_path)
    intruder = dst / "references" / "agents" / "zz-未登记-全包门.md"
    intruder.write_text("# 全包范围未登记新文件\n\n> 版本：v9.9.9\n\n维护者内档测试。\n",
                        encoding="utf-8")
    env = {**os.environ, **GIT_ENV}
    subprocess.run(["git", "add", "references/agents/zz-未登记-全包门.md"],
                   cwd=str(dst), env=env, capture_output=True, text=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"],
                   cwd=str(dst), env=env, capture_output=True, text=True)

    r = _build(dst, tmp_path / "out")
    blob = r.stderr + r.stdout
    assert r.returncode != 0, "已跟踪但未登记的文件入包竟构建成功 —— 全包准入门失效"
    assert "随包清单不一致" in blob, f"未命中全包准入门（可能别的门先炸）：\n{blob[-1500:]}"
    assert "zz-未登记-全包门.md" in blob, "准入门未点名未登记文件"


def test_build_fails_on_nonmd_asset_collapse(tmp_path):
    """C-5 故障注入：非 md 资产在快照后被塌陷 ⇒ 非 md 正向门必须拦住。

    注入内容**保留 `pipeline:` 锚点**，好让 4b' 的必需锚点门不先炸 —— 从而证明
    「非 md 正向门」是独立在判，而不是搭 4b' 的便车（首版注入即因此被锚点门误认）。
    """
    dst = _copy_repo(tmp_path)
    script = dst / "scripts" / "build-clawhub-release.sh"
    src = script.read_text(encoding="utf-8")
    anchor = "# ---- 3. 文档净化（sed 替换"
    assert anchor in src, "注入锚点缺失（构建脚本结构变了，请同步本用例）"
    inject = (
        '_C5T="$OUT_DIR/references/_shared/真源/phase-order.yaml"\n'
        '[[ -f "$_C5T" ]] && printf "pipeline: ok\\n" > "$_C5T"\n\n'
    )
    script.write_text(src.replace(anchor, inject + anchor, 1), encoding="utf-8")

    r = _build(dst, tmp_path / "out")
    blob = r.stderr + r.stdout
    assert r.returncode != 0, "非 md 资产被塌陷竟构建成功 —— 非 md 正向门失效"
    assert "非 md 正向完整性未通过" in blob, f"未命中非 md 正向门：\n{blob[-2000:]}"
    assert "phase-order.yaml" in blob and "字符保留率" in blob, "非 md 门未点名塌陷文件/保留率"


# ---------------- v2.12.64：工具残留排除（CI 实测回归，2026-09-19）----------------
# 背景：CI 的 Code Quality 以 `pytest --cov=scripts` 跑全量 ⇒ coverage 并行模式在**仓库根**
#   落 `.coverage.<host>.<pid>.<随机>` ⇒ rsync 全量复制把它们带进包 ⇒ §2b″ 全包清单门拦下，
#   Code Quality 变红。**门拦得没错**（那确实是包内不该有的文件），但根因是排除清单漏了这一类。
#   本地不跑 `--cov` ⇒ 从未复现 ⇒「本地绿 / CI 红」（#430 同族）。本组用例把两类都锁死。

_TOOL_RESIDUE_AT_ROOT = (
    ".coverage",                          # 非并行模式的单一数据文件
    ".coverage.runnervmlun5p.pid86983.XlcXavZx",  # 并行模式：CI 实测的形态
    ".DS_Store",
    "scratch.swp",
)

def test_tool_residue_is_excluded_in_both_copy_branches():
    """源侧不变量：排除清单是**黑名单**（新类型默认入包）⇒ rsync 与 cp 两侧必须对称。

    单侧补漏 = 另一条分支仍会把残留打进包（rsync 缺失时才走 cp，属罕见路径 ⇒ 更难发现）。
    """
    src = _src()
    for token in (".coverage", "htmlcov", ".DS_Store", "*.swp"):
        assert f"--exclude '{token}'" in src, f"rsync 侧缺 {token} 排除（{token} 会随包出厂）"
    assert '.coverage.*' in src, "rsync 侧缺 .coverage.* 排除（并行模式主形态）"
    cp_branch = src.split("cp -a \"$SKILL_ROOT/.\"")[1]
    for token in (".coverage", "htmlcov", ".DS_Store", "swp"):
        assert token in cp_branch, f"cp 分支缺 {token} 清理（两侧不对称）"


def test_build_survives_and_drops_tool_residue(tmp_path):
    """故障注入：仓库根铺满工具残留 ⇒ 构建**必须成功**且包内**不得**含这些文件。

    这条正是 CI 回归的复现：修复前 ② 因 §2b″ 清单门而红；修复后应绿，且残留确实被剥离。
    """
    dst = _copy_repo(tmp_path)
    for name in _TOOL_RESIDUE_AT_ROOT:
        (dst / name).write_text("residue\n", encoding="utf-8")
    (dst / "htmlcov").mkdir()
    (dst / "htmlcov" / "index.html").write_text("<html>cov</html>\n", encoding="utf-8")

    out_root = tmp_path / "out"
    r = _build(dst, out_root)
    blob = r.stderr + r.stdout
    assert r.returncode == 0, (
        f"仓库根有工具残留时构建失败 —— 排除清单漏了该类型（CI 回归）：\n{blob[-2000:]}")
    pkg = out_root / "clawhub-release" / "9.9.9"
    leaked = sorted(str(p.relative_to(pkg)) for p in pkg.rglob("*")
                    if p.is_file() and (p.name.startswith(".coverage")
                                        or p.name in (".DS_Store", "scratch.swp")
                                        or p.suffix == ".swp"))
    assert not leaked, f"工具残留随包出厂：{leaked}"
    assert not (pkg / "htmlcov").exists(), "htmlcov/ 随包出厂"
