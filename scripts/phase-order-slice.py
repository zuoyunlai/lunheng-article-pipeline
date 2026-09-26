#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""phase-order-slice.py — 论衡阶段真源「按节点切片」生成器（v2.13.5，审计修订 R-21）

背景（2026-09-26 审计 R-21）：
  `references/_shared/真源/phase-order.yaml` 是流程顺序与阻断关系的**唯一真源**（41,262 字符）。
  主控「进入每个 Phase 前必读其完整定义」⇒ 单次运行反复付全量读取成本。实测结构：
    pipeline（24 节点）= 14,213 字符；跨阶段共用块 ≈ 5.7K 字符；索引 1.3K 字符。

口径（本轮为「增量 1」，不改真源结构）：
  · 真源仍是**唯一** `phase-order.yaml`（不拆分、不搬迁 —— flow-check / 门 S / 门 Y / 测试
    与约 52 处代码引用继续按原路径读它，语义零变更）。
  · 新增**派生切片**（禁止手改）：`phase-order/index.yaml` + `phase-order/<node-id>.yaml`。
  · 主控读法改为：索引（含跨阶段共用契约）+ 当前节点切片，不必读全量真源。
  · 漂移由机械门兜底：`--check` 逐字节比对生成结果与磁盘，任何差异/缺失/多余即非 0 退出
    （自审门「门 AA」+ `tests/test_phase_order_slice.py` 反向注入共同锁死）。

用法：
  python3 scripts/phase-order-slice.py            # 生成/刷新切片
  python3 scripts/phase-order-slice.py --check    # 只校验（CI / 自审门用）；漂移 ⇒ exit 1
"""
import hashlib
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
TRUTH = ROOT / "references" / "_shared" / "真源" / "phase-order.yaml"
OUTDIR = ROOT / "references" / "_shared" / "真源" / "phase-order"

HEADER_COMMON = (
    "# ⚠️ 派生视图 —— 禁止手改（改真源后由切片生成器重新生成）\n"
    "# 唯一真源 = ../phase-order.yaml；一致性由生成器 --check 校验\n"
)

# 跨阶段共用契约（进任何节点前读一次；顺序与真源一致）
CROSS_KEYS = (
    "version",
    "architecture",
    "version_numbering",
    "verdict_scale",
    "silence_doctrine",
    "owner_timeout_policy",
    "provider_silence_escalation",
    "terminal_freeze",
    "condition_definitions",
    "m_gate_criterion_fields",
    "owner_checkpoints",
    "panorama_sources",
)


def _dump(obj):
    return yaml.safe_dump(obj, allow_unicode=True, sort_keys=False,
                          default_flow_style=False, width=100000)


def build(truth_path=TRUTH):
    """返回 {相对输出目录的文件名: 内容}。纯函数，便于测试与 --check 比对。"""
    raw = truth_path.read_text(encoding="utf-8")
    doc = yaml.safe_load(raw)
    if not isinstance(doc, dict):
        raise SystemExit("❌ 真源顶层不是映射（dict）—— 拒绝生成（结构漂移）")
    nodes = doc.get("pipeline")
    if not isinstance(nodes, list) or not nodes:
        raise SystemExit("❌ 真源缺 pipeline 列表或为空 —— 拒绝生成（结构漂移）")

    files = {}

    # ---- index.yaml：序 + 跨阶段契约 + 节点路由 ----
    index_parts = {"truth_source": "../phase-order.yaml",
                   "truth_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
                   "node_count": len(nodes)}
    for k in CROSS_KEYS:
        if k in doc:
            index_parts[k] = doc[k]
    routing = []
    for n in nodes:
        if not isinstance(n, dict) or "id" not in n:
            raise SystemExit("❌ pipeline 存在无 id 的节点 —— 拒绝生成（漂移/漏项风险）")
        routing.append({
            "seq": n.get("phase_seq", n.get("seq")),
            "phase": n.get("phase"),
            "node": n["id"],
            "slice": f"{n['id']}.yaml",
            "purpose": str(n.get("purpose") or n.get("note") or "")[:80],
        })
    index_parts["nodes"] = routing

    idx_lines = [HEADER_COMMON,
                 "# 读法：本文件（含跨阶段共用契约）+ 当前节点切片 = 该节点所需的全部判据；\n",
                 "#      不必读全量真源。节点切片见同目录 <node>.yaml。\n"]
    files["index.yaml"] = "".join(idx_lines) + _dump(index_parts)

    # ---- 每节点一个切片 ----
    seen = set()
    for n in nodes:
        nid = n["id"]
        if nid in seen:
            raise SystemExit(f"❌ 节点 id 重复：{nid} —— 拒绝生成（后键会静默覆盖前键）")
        seen.add(nid)
        head = (HEADER_COMMON
                + f"# 本切片 = 节点 {nid}（{n.get('phase', '?')}）的完整定义，读它即可推进该节点。\n")
        files[f"{nid}.yaml"] = head + _dump(n)

    return files


def main(argv):
    check = "--check" in argv[1:]
    files = build()
    if check:
        problems = []
        for name, content in sorted(files.items()):
            p = OUTDIR / name
            if not p.is_file():
                problems.append(f"{name}: 切片缺失（真源有该节点，磁盘无切片）")
            elif p.read_text(encoding="utf-8") != content:
                problems.append(f"{name}: 与真源不一致（切片漂移或真源已改未重生成）")
        if OUTDIR.is_dir():
            for p in sorted(OUTDIR.iterdir()):
                if p.is_file() and p.name not in files:
                    problems.append(f"{p.name}: 多余切片（真源已无此节点）")
        if problems:
            print("❌ phase-order 切片与真源不一致（漂移）：", file=sys.stderr)
            for x in problems:
                print(f"   - {x}", file=sys.stderr)
            print("   修法：python3 scripts/phase-order-slice.py 重新生成后再提交", file=sys.stderr)
            return 1
        print(f"✅ phase-order 切片与真源逐字节一致（{len(files)} 个文件：1 索引 + {len(files) - 1} 节点）")
        return 0

    OUTDIR.mkdir(parents=True, exist_ok=True)
    for p in sorted(OUTDIR.iterdir()):
        if p.is_file() and p.name not in files:
            p.unlink()
            print(f"  🗑️  删除多余切片 {p.name}")
    changed = 0
    for name, content in sorted(files.items()):
        p = OUTDIR / name
        if not p.is_file() or p.read_text(encoding="utf-8") != content:
            p.write_text(content, encoding="utf-8")
            changed += 1
    print(f"✅ 生成完成：{len(files)} 个文件（1 索引 + {len(files) - 1} 节点；本次更新 {changed} 个）")
    total = sum(len(c) for c in files.values())
    print(f"   派生总体量 {total} 字符；单节点切片均值 {total // max(1, len(files) - 1)} 字符")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
