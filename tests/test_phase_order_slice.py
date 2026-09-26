#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""phase-order 真源 / 装配视图门（v2.13.5，审计修订 R-21 增量 2）

布局（倒置后）：
  真源 = references/_shared/真源/phase-order/ 目录
    · index.yaml —— 跨阶段契约（**原文**，含注释与引号）+ 节点路由（顺序唯一真源）
    · <node>.yaml —— 24 个节点定义（**原文**，逐字保存）
  装配视图 = references/_shared/真源/phase-order.yaml（**生成物**；文本逐字拼接，非 YAML 重打）

本测试锁死六件事：
  1. **闭合**：路由覆盖全部切片、无孤儿、id 不重复。
  2. **等价**：装配视图 pipeline 逐节点等于切片数据且顺序 = 路由顺序。
  3. **文本保真**：行尾注释与作者引号必须在装配视图里原样存活（重打会静默废掉文本型机械门）。
  4. **逐字节**：真源仓库上 --check 必绿（防假阳性）。
  5. **漂移可判（反向注入）**：手改装配视图 / 改切片未重生成 / 删切片 / 孤儿切片 /
     路由指向不存在节点 / 契约段键集漂移 —— 六类都必须判红并点名。
  6. **作者权**：真源目录内不得出现装配视图的身份标记（生成物不得回流成真源）。
"""
import pathlib
import shutil
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
TRUTH_REL = "references/_shared/真源/phase-order"
ASM_REL = "references/_shared/真源/phase-order.yaml"
GEN_REL = "scripts/phase-order-slice.py"
TDIR = ROOT / TRUTH_REL
ASM = ROOT / ASM_REL
GEN = ROOT / GEN_REL
BODY_MARK = "# ── 节点 YAML 正文（装配时逐字拼入；本行以上为切片头）──"
ASM_IDENTITY = "⚠️ 装配视图（生成物）"


def _idx():
    return yaml.safe_load((TDIR / "index.yaml").read_text(encoding="utf-8"))


def _asm():
    return yaml.safe_load(ASM.read_text(encoding="utf-8"))


def _slice(nid):
    """切片正文 → 单元素节点序列的第 1 项（正文按单元素序列保存，便于逐字拼接）。"""
    txt = (TDIR / (nid + ".yaml")).read_text(encoding="utf-8")
    assert BODY_MARK in txt, nid + ".yaml 缺正文标记行（切片结构被破坏）"
    seq = yaml.safe_load(txt.split(BODY_MARK, 1)[1].lstrip())
    assert isinstance(seq, list) and len(seq) == 1, nid + ".yaml 正文不是单元素序列"
    return seq[0]


def _mini_repo(tmp_path):
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / TRUTH_REL).mkdir(parents=True, exist_ok=True)
    shutil.copy2(GEN, tmp_path / GEN_REL)
    shutil.copy2(ASM, tmp_path / ASM_REL)
    for p in TDIR.iterdir():
        if p.is_file():
            shutil.copy2(p, tmp_path / TRUTH_REL / p.name)
    return tmp_path


def _check(root):
    r = subprocess.run([sys.executable, str(root / GEN_REL), "--check"],
                       cwd=root, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


# ------------------------------------------------ 正向（闭合 + 等价 + 保真）

def test_routing_covers_all_slices_with_no_orphans():
    routed = [r["node"] for r in _idx()["nodes"]]
    assert len(routed) == len(set(routed)), "路由中节点 id 重复"
    on_disk = {p.stem for p in TDIR.glob("*.yaml") if p.name != "index.yaml"}
    assert set(routed) == on_disk, (
        "路由与切片不闭合 —— 缺文件：" + str(sorted(set(routed) - on_disk)) +
        "；孤儿：" + str(sorted(on_disk - set(routed))))


def test_assembly_pipeline_equals_slices_in_routing_order():
    routed = [r["node"] for r in _idx()["nodes"]]
    pipe = _asm()["pipeline"]
    assert [n["id"] for n in pipe] == routed, "装配视图 pipeline 顺序 ≠ 路由顺序（顺序真源被绕过）"
    for n in pipe:
        assert n == _slice(n["id"]), "装配视图的 " + n["id"] + " 与切片数据不等（视图失真）"


def test_assembly_phase_order_is_seq_sorted_and_covers_pipeline():
    po = _asm()["phase_order"]
    seqs = [e["seq"] for e in po]
    assert all(s is not None for s in seqs), "phase_order 存在缺 seq 的项"
    assert seqs == sorted(seqs), "phase_order 未按 seq 升序（历史口径）"
    assert {e["node"] for e in po} == {n["id"] for n in _asm()["pipeline"]}


def test_assembly_preserves_trailing_comments_and_quotes():
    """文本保真：重打（yaml.dump）会丢掉行尾注释与作者引号，进而废掉文本型机械门的检出。"""
    asm_text = ASM.read_text(encoding="utf-8")
    d3 = "# v2.12.51 D-3：只读档报告由主控 write 落盘，本节点不授写权"
    assert asm_text.count(d3) == 4, "四个只读档节点的 D-3 行尾注释不齐（实为 " + str(asm_text.count(d3)) + " 处）"
    assert 'producer_marker: "需找数据点"' in asm_text, "作者引号在装配视图里丢失（文本保真被破坏）"


def test_check_passes_on_truth_repo():
    rc, out = _check(ROOT)
    assert rc == 0, "真源仓库上 --check 应绿：" + out
    assert "逐字节一致" in out


def test_truth_dir_has_no_assembly_identity_marker():
    """作者权护栏：真源目录内不得出现装配视图的身份标记（生成物不得回流成真源）。"""
    bad = [p.name for p in TDIR.glob("*.yaml")
           if ASM_IDENTITY in p.read_text(encoding="utf-8")]
    assert not bad, "真源目录内出现装配视图身份标记（作者权混淆）：" + str(bad)


# ------------------------------------------------ 反向注入

def test_check_detects_hand_edited_assembly(tmp_path):
    root = _mini_repo(tmp_path)
    p = root / ASM_REL
    p.write_text(p.read_text(encoding="utf-8") + "# 手改一行" + chr(10), encoding="utf-8")
    rc, out = _check(root)
    assert rc != 0, "装配视图被手改，--check 竟仍绿：" + out
    assert "装配视图" in out, "未点名装配视图漂移：" + out


def test_check_detects_edited_slice_without_regen(tmp_path):
    root = _mini_repo(tmp_path)
    p = root / TRUTH_REL / "t9_review.yaml"
    p.write_text(p.read_text(encoding="utf-8") + "# 手改探针" + chr(10), encoding="utf-8")
    rc, out = _check(root)
    assert rc != 0, "改了切片未重生成装配视图，--check 竟仍绿：" + out


def test_check_detects_missing_slice(tmp_path):
    root = _mini_repo(tmp_path)
    (root / TRUTH_REL / "t7_audit.yaml").unlink()
    rc, out = _check(root)
    assert rc != 0 and "t7_audit" in out, "缺切片未判红：" + out


def test_check_detects_orphan_slice(tmp_path):
    root = _mini_repo(tmp_path)
    (root / TRUTH_REL / "zz_ghost.yaml").write_text("# 孤儿切片" + chr(10), encoding="utf-8")
    rc, out = _check(root)
    assert rc != 0 and "zz_ghost" in out, "孤儿切片未判红：" + out
    assert "孤儿" in out


def test_check_detects_routing_to_nonexistent_node(tmp_path):
    root = _mini_repo(tmp_path)
    ip = root / TRUTH_REL / "index.yaml"
    txt = ip.read_text(encoding="utf-8")
    add = "  - {seq: 99, phase: Phase 9, node: zz_new_phase}" + chr(10)
    injected = txt.replace("  - seq:", add + "  - seq:", 1)
    assert injected != txt, "注入点未命中（nodes 路由表格式变化）"
    ip.write_text(injected, encoding="utf-8")
    rc, out = _check(root)
    assert rc != 0 and "zz_new_phase" in out, "路由指向不存在的节点未判红：" + out


def test_check_detects_contract_key_drift(tmp_path):
    root = _mini_repo(tmp_path)
    ip = root / TRUTH_REL / "index.yaml"
    txt = ip.read_text(encoding="utf-8")
    injected = txt.replace("version:", "unregistered_contract: 1" + chr(10) + "version:", 1)
    assert injected != txt, "注入点未命中（契约段起始格式变化）"
    ip.write_text(injected, encoding="utf-8")
    rc, out = _check(root)
    assert rc != 0 and "unregistered_contract" in out, "契约段键集漂移未判红：" + out
