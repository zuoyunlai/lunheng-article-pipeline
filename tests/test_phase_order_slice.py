#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""phase-order 派生切片门（v2.13.5，审计修订 R-21）

背景：`references/_shared/真源/phase-order.yaml` 是流程真源（41,262 字符），主控原先
「进入每个 Phase 前必读完整定义」⇒ 单次运行反复付全量读取成本。R-21 增量 1 的做法是
**不改真源结构**，新增受机械门约束的派生切片（1 索引 + 24 节点），把读法改为
「索引 + 当前节点切片」≈ −70% 读取量。

本测试锁死三件事（缺任一件，切片就会悄悄腐烂）：
  1. **覆盖**：真源每个节点都有切片，且**没有**多余切片；索引路由与真源顺序一致。
  2. **无损**：切片解析后与真源对应节点**深度相等** —— 切片不得漏字段或改写判据。
  3. **漂移可判（反向注入）**：改切片 / 删切片 / 加多余切片 / 真源新增节点，
     `--check` 都必须非 0 退出并点名；真源仓库上 `--check` 必须绿（防假阳性）。
"""
import pathlib
import shutil
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
TRUTH_REL = "references/_shared/真源/phase-order.yaml"
SLICES_REL = "references/_shared/真源/phase-order"
GEN_REL = "scripts/phase-order-slice.py"
TRUTH = ROOT / TRUTH_REL
SLICES = ROOT / SLICES_REL
GEN = ROOT / GEN_REL


def _truth():
    return yaml.safe_load(TRUTH.read_text(encoding="utf-8"))


def _mini_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """把「真源 + 切片 + 生成器」复制成独立小仓，用于端到端跑 --check。"""
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / SLICES_REL).mkdir(parents=True, exist_ok=True)
    shutil.copy2(TRUTH, tmp_path / TRUTH_REL)
    shutil.copy2(GEN, tmp_path / GEN_REL)
    for p in SLICES.iterdir():
        if p.is_file():
            shutil.copy2(p, tmp_path / SLICES_REL / p.name)
    return tmp_path


def _check(root: pathlib.Path):
    r = subprocess.run([sys.executable, str(root / GEN_REL), "--check"],
                       cwd=root, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


# ------------------------------------------------------------------ 正向

def test_slice_set_covers_every_node_and_has_no_extra():
    nodes = _truth()["pipeline"]
    expected = {f"{n['id']}.yaml" for n in nodes} | {"index.yaml"}
    actual = {p.name for p in SLICES.iterdir() if p.is_file()}
    assert actual == expected, (
        f"切片集合与真源不一致 —— 缺：{sorted(expected - actual)}；多：{sorted(actual - expected)}"
    )


def test_slices_are_lossless_vs_truth():
    """切片解析后必须与真源节点**深度相等**（防漏字段/改写判据）。"""
    for n in _truth()["pipeline"]:
        got = yaml.safe_load((SLICES / f"{n['id']}.yaml").read_text(encoding="utf-8"))
        assert got == n, f"切片 {n['id']}.yaml 与真源节点不等（无损性破坏）"


def test_index_routing_matches_truth_order():
    doc = _truth()
    idx = yaml.safe_load((SLICES / "index.yaml").read_text(encoding="utf-8"))
    assert idx["node_count"] == len(doc["pipeline"])
    assert [r["node"] for r in idx["nodes"]] == [n["id"] for n in doc["pipeline"]], (
        "索引路由顺序与真源 pipeline 顺序不一致（主控会按错序推进）"
    )
    # 跨阶段共用契约必须在索引里（否则「只读索引 + 切片」会丢判据）
    for k in ("verdict_scale", "condition_definitions", "terminal_freeze"):
        assert k in idx, f"索引缺跨阶段契约 {k} —— 读法改为「索引 + 切片」后会丢判据"


def test_check_passes_on_truth_repo():
    rc, out = _check(ROOT)
    assert rc == 0, f"真源仓库上 --check 应绿：\n{out}"
    assert "逐字节一致" in out


# ------------------------------------------------------------------ 反向注入

def test_check_detects_mutated_slice(tmp_path):
    root = _mini_repo(tmp_path)
    target = root / SLICES_REL / "t9_review.yaml"
    target.write_text(target.read_text(encoding="utf-8") + "# 手改一行\n", encoding="utf-8")
    rc, out = _check(root)
    assert rc != 0, f"切片被手改，--check 竟仍绿：\n{out}"
    assert "t9_review.yaml" in out, f"未点名漂移文件：{out}"


def test_check_detects_missing_slice(tmp_path):
    root = _mini_repo(tmp_path)
    (root / SLICES_REL / "t7_audit.yaml").unlink()
    rc, out = _check(root)
    assert rc != 0 and "t7_audit.yaml" in out, f"缺切片未判红：\n{out}"
    assert "缺失" in out


def test_check_detects_extra_slice(tmp_path):
    root = _mini_repo(tmp_path)
    (root / SLICES_REL / "zz_ghost.yaml").write_text("id: zz_ghost\n", encoding="utf-8")
    rc, out = _check(root)
    assert rc != 0 and "zz_ghost.yaml" in out, f"多余切片未判红：\n{out}"
    assert "多余" in out


def test_check_detects_new_truth_node_without_slice(tmp_path):
    """真源新增节点但没重生成切片 ⇒ 必须红（治「真源改了、切片没跟」）。"""
    root = _mini_repo(tmp_path)
    truth = yaml.safe_load((root / TRUTH_REL).read_text(encoding="utf-8"))
    truth["pipeline"].append({"id": "zz_new_phase", "phase": "Phase 9", "phase_seq": 99,
                              "kind": "mechanical"})
    (root / TRUTH_REL).write_text(
        yaml.safe_dump(truth, allow_unicode=True, sort_keys=False), encoding="utf-8")
    rc, out = _check(root)
    assert rc != 0, f"真源新增节点未重生成切片，--check 竟绿：\n{out}"
    assert "zz_new_phase" in out, f"未点名缺切片的新节点：{out}"
