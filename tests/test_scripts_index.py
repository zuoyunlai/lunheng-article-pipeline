#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_scripts_index.py — scripts/ 索引双向一致锁（v2.12.56 候选新增）

背景（外部审计发现，2026-09-18 核对成立）：
  `scripts/` 是构建期 / 发版期工具链，此前**全仓没有任何索引**（26 个 .sh/.py/.yaml 无一登记）。
  使用者只能逐个打开文件读头部注释才知道「这个脚本干什么、怎么调、挂在哪」——
  同型于教训索引腐烂：**没有真源指针，人就只能靠记忆**。

口径（一条款一真源）：
  - 脚本用途 / 用法 / 触发时机的**真源 = 各脚本头部注释**；`scripts/README.md` 只是**派生视图**，
    由 `scripts/gen-scripts-index.py` 机械生成，**不得手改**。
  - 索引放在 `scripts/` 而非 `references/`：`references/` 是运行时正文层（进发布包），
    而构建脚本把 `scripts/` 整目录排除、且要求产物内 `scripts/` 命中数为 0 ——
    索引若住进 `references/`，它在发布包里必然被剥成残缺文本。

本测试锁死**双向**一致（两个方向各自可红）：
  - 新增脚本未进索引   ⇒ 红（`test_drift_detected_when_new_script_appears`）
  - 索引残留已删脚本   ⇒ 红（`test_drift_detected_when_script_deleted`）
  - 脚本头改了未刷新   ⇒ 红（`test_index_matches_generator`）
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
GEN_SCRIPT = SCRIPTS / "gen-scripts-index.py"
INDEX = SCRIPTS / "README.md"
LINK_CHECK = SCRIPTS / "link-check.py"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gen = _load(GEN_SCRIPT, "gen_scripts_index")


def _rows(text):
    """索引表格数据行 → [(脚本名, 用途, 用法, 触发, make 入口)]"""
    out = []
    for line in text.splitlines():
        m = re.match(r'^\|\s*\[`([^`]+)`\]\([^)]+\)\s*\|(.+)\|\s*$', line)
        if m:
            cells = [c.strip() for c in m.group(2).split("|")]
            out.append((m.group(1), *cells))
    return out


def _repo_rows():
    return _rows(INDEX.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# 1. 索引 ↔ 生成器：内容必须逐字一致（脚本头改了没刷新 ⇒ 红）
# --------------------------------------------------------------------------

def test_index_exists():
    assert INDEX.is_file(), f"缺索引文件 {INDEX}（跑 make scripts-index 生成）"


def test_index_matches_generator():
    expected = gen.build_index(SCRIPTS, ROOT / "Makefile")
    actual = INDEX.read_text(encoding="utf-8")
    assert actual == expected, (
        "scripts/README.md 与生成器输出漂移（手改过？还是改了脚本头没刷新？）——"
        "跑 `make scripts-index` 重新生成，勿手改本文件")


def test_generator_check_mode_is_green():
    """CLI --check 是门/CI 的入口，必须与模块口径同源且当前为绿。"""
    r = subprocess.run([sys.executable, str(GEN_SCRIPT), "--check"],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, f"--check 未过：\n{r.stdout}\n{r.stderr}"


# --------------------------------------------------------------------------
# 2. 双向集合一致（缺条目 / 残留条目各自可红）
# --------------------------------------------------------------------------

def test_index_lists_every_script_on_disk():
    """方向一：scripts/ 每个文件都在索引里（新增脚本未登记 ⇒ 红）"""
    on_disk = set(gen.indexed_files(SCRIPTS))
    listed = {row[0] for row in _repo_rows()}
    missing = sorted(on_disk - listed)
    assert not missing, f"以下脚本未进索引（跑 make scripts-index 刷新）：{missing}"


def test_index_has_no_stale_entries():
    """方向二：索引里不能有 scripts/ 已不存在的文件（残留登记 ⇒ 红）"""
    on_disk = set(gen.indexed_files(SCRIPTS))
    listed = {row[0] for row in _repo_rows()}
    stale = sorted(listed - on_disk)
    assert not stale, f"索引含已删除脚本（跑 make scripts-index 刷新）：{stale}"


def test_index_entries_link_to_existing_files():
    for name, *_ in _repo_rows():
        assert (SCRIPTS / name).is_file(), f"索引条目指向不存在的脚本：{name}"


# --------------------------------------------------------------------------
# 3. 反向注入（tmp 副本上变异 ⇒ 必须红；镜像 test_flow_check 的副本变异风格）
# --------------------------------------------------------------------------

def _fake_tree(tmp_path, names=("alpha.sh", "beta.py")):
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    for n in names:
        (root / "scripts" / n).write_text(
            f"#!/usr/bin/env bash\n# {n} — 示例脚本\n# 用法：bash scripts/{n}\n", encoding="utf-8")
    (root / "Makefile").write_text("demo:\n\tbash scripts/alpha.sh\n", encoding="utf-8")
    return root


def _run_cli(root, *extra):
    return subprocess.run([sys.executable, str(GEN_SCRIPT), "--root", str(root), *extra],
                          capture_output=True, text=True)


def test_drift_detected_when_new_script_appears(tmp_path):
    root = _fake_tree(tmp_path)
    assert _run_cli(root).returncode == 0, "生成副本索引失败"
    assert _run_cli(root, "--check").returncode == 0, "干净副本应通过"
    (root / "scripts" / "gamma.sh").write_text("#!/usr/bin/env bash\n# gamma.sh — 新脚本\n",
                                               encoding="utf-8")
    r = _run_cli(root, "--check")
    assert r.returncode == 1, "新增脚本未进索引却通过了 --check"
    assert "gamma.sh" in r.stderr, r.stderr


def test_drift_detected_when_script_deleted(tmp_path):
    root = _fake_tree(tmp_path)
    assert _run_cli(root).returncode == 0
    (root / "scripts" / "alpha.sh").unlink()
    r = _run_cli(root, "--check")
    assert r.returncode == 1, "索引残留已删除脚本却通过了 --check"
    assert "alpha.sh" in r.stderr, r.stderr


def test_drift_after_header_edit_is_detected(tmp_path):
    """改了脚本头（口径变更）但没刷新索引 ⇒ 内容漂移，必须红"""
    root = _fake_tree(tmp_path)
    assert _run_cli(root).returncode == 0
    p = root / "scripts" / "beta.py"
    p.write_text("# beta.py — 改过用途的脚本\n# 用法：python3 scripts/beta.py\n", encoding="utf-8")
    r = _run_cli(root, "--check")
    assert r.returncode == 1, "脚本头已改但索引未刷新却通过了 --check"
    assert "漂移" in r.stderr, r.stderr


def test_drift_helper_agrees_with_cli(tmp_path):
    """--check 与本测试用的 find_drift 必须同源（防「测试测的 helper 已死」）"""
    root = _fake_tree(tmp_path)
    scripts_dir, index_path = root / "scripts", root / "scripts" / "README.md"
    assert gen.find_drift(scripts_dir, index_path) != []      # 索引尚未生成
    assert _run_cli(root).returncode == 0
    assert gen.find_drift(scripts_dir, index_path) == []
    (root / "scripts" / "delta.yaml").write_text("# delta.yaml — 新配置\n", encoding="utf-8")
    assert gen.find_drift(scripts_dir, index_path) == ["新增脚本未进索引：delta.yaml"]


# --------------------------------------------------------------------------
# 4. 条目质量与「不搬运内部锚点」
# --------------------------------------------------------------------------

def test_every_entry_has_a_derived_purpose():
    """用途列必须来自脚本头首个内容行 —— 没有头部注释的脚本应先进「补头部」再进索引"""
    rows = _repo_rows()
    assert len(rows) == len(gen.indexed_files(SCRIPTS)), "索引行数与 scripts/ 文件数不符"
    empty = [r[0] for r in rows if not r[1] or r[1] == gen.NO_PURPOSE]
    assert not empty, f"索引条目缺用途（脚本头缺注释）：{empty}"


def test_index_carries_no_internal_lesson_anchors():
    """索引是派生视图，不得搬运 `教训 #N` / 表格裸 `#N` —— 门 H 会扫 scripts/ 做编号差集"""
    text = INDEX.read_text(encoding="utf-8")
    bad = re.findall(r'教训\s*#\d+', text) + re.findall(r'^\|\s*#\d+\s*\|', text, re.M)
    assert not bad, f"索引残留内部教训锚点：{bad}"


def test_scrub_strips_lesson_anchors_and_audit_parens():
    """单元级：清洗规则覆盖「教训 #N」「括号内审计溯源」「版本沿革括号」"""
    assert "教训" not in gen.scrub("capability-assert.py — 能力断言（教训 #210，回应审计）")
    assert gen.scrub("link-check.py — 相对链接检查（v2.12.30 新增，回应第三方审计 P2）") \
        == "link-check.py — 相对链接检查"
    assert gen.scrub("论衡流程图检查（v2.12.28 新增；v2.12.51 扩）") == "论衡流程图检查"
    # 括号配对不被误裁（列名/尾括号保持平衡）
    assert gen.scrub("changelog 检查（P2「完整化」）") == "changelog 检查（P2「完整化」）"


def test_make_target_column_is_derived_from_makefile():
    """make 入口列必须能在 Makefile recipe 里找到对应调用（防手写第二份真源）"""
    make = (ROOT / "Makefile").read_text(encoding="utf-8")
    targets = gen.make_targets(ROOT / "Makefile")
    assert targets.get("self-audit-gate.sh") == ["audit"], targets
    hits = [r for r in _repo_rows() if r[4] != "—"]
    assert hits, "make 入口列全空 —— 反查逻辑已失效"
    for name, *_rest in hits:
        for t in targets[name]:
            assert re.search(rf'^{re.escape(t)}:', make, re.M), f"Makefile 无目标 {t}"


# --------------------------------------------------------------------------
# 5. 新文件必须无失效链接（link-check 口径；scripts/ 不在其默认扫描面内，故显式纳入）
# --------------------------------------------------------------------------

def test_index_relative_links_resolve():
    link_check = _load(LINK_CHECK, "link_check_for_scripts_index")
    broken, checked = link_check.check([str(INDEX)])
    assert not broken, f"索引存在断链：{broken}"
    assert checked >= len(_repo_rows()), f"检查条数 {checked} 少于索引条目数（假绿灯？）"
