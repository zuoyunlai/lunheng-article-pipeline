#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""phase-order-slice.py — 论衡流程真源「文本保真装配器」（v2.13.5，审计修订 R-21 增量 2）

真源（两部分共同构成，人工编辑这两处）：
  · references/_shared/真源/phase-order/index.yaml    —— 跨阶段契约（原文）+ 节点路由（顺序唯一真源）
  · references/_shared/真源/phase-order/<node>.yaml   —— 24 个节点定义（原文）
装配视图（**生成物，禁止手改**）：
  · references/_shared/真源/phase-order.yaml          —— 供 flow-check / 门 S / 既有引用按原路径读取

**为什么是「文本拼接」而不是 YAML 重打**：
  重打（yaml.dump）会丢掉两样东西 —— **行尾注释**与**作者引号**。实测代价：
    · `tests/test_flow_check.py::test_readonly_tier_reports_are_owner_written` 直接断言真源里
      「# v2.12.51 D-3：…」恰好 4 处；
    · 另有 5 条反向注入测试按「带行尾注释/带引号」的文本模式定位注入点 —— 重打后它们
      会**静默失配**（注入点未命中），等于用格式漂移把机械门的检出能力废掉。
  故真源两处都**逐字保存原文本**，装配只做「缩进 2 空格 + 按路由顺序拼接」，绝不重新序列化。

不变量（--check / 自审门 AA 逐条校验）：
  ① 路由与切片双向闭合（无缺文件、无孤儿切片、id 不重复）；
  ② 路由 seq/phase 与切片正文一致（防两处漂移）；
  ③ 契约段键集必须恰好 = 注册表（新增键未登记即报错，不静默漏配）；
  ④ 装配视图与「真源拼接结果」逐字节一致（手改生成物即红）。

用法：
  python3 scripts/phase-order-slice.py            # 生成/刷新装配视图
  python3 scripts/phase-order-slice.py --check    # 只校验（CI / 自审门 AA）
"""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
TRUTH_DIR = ROOT / "references" / "_shared" / "真源" / "phase-order"
INDEX = TRUTH_DIR / "index.yaml"
ASSEMBLY = ROOT / "references" / "_shared" / "真源" / "phase-order.yaml"

ASSEMBLY_HEADER = (
    "# ⚠️ 装配视图（生成物）—— 禁止手改；真源 = phase-order/ 目录（index.yaml + 节点切片）\n"
    "# 重新生成 = 维护者侧生成器（phase-order-slice.py）；一致性由门 AA 校验\n"
)

# 契约段（index.yaml 中 nodes: 之前的顶层键）注册表 —— 新增契约键必须在此登记
CONTRACT_KEYS = (
    "version",
    "verdict_scale",
    "silence_doctrine",
    "owner_timeout_policy",
    "provider_silence_escalation",
    "terminal_freeze",
    "architecture",
    "version_numbering",
    "condition_definitions",
    "m_gate_criterion_fields",
    "owner_checkpoints",
    "panorama_sources",
)

SLICE_BODY_MARK = "# ── 节点 YAML 正文（装配时逐字拼入；本行以上为切片头）──"
PO_INJECT_MARK = "# ── phase_order 段由生成器在此注入（顺序真源 = 本文件末尾 nodes: 路由表）──"
PIPE_INJECT_MARK = "# ── pipeline 段由生成器在此注入（节点正文逐字来自各切片）──"


class _IndentDumper(yaml.SafeDumper):
    """块序列相对父键缩进（用于生成 phase_order 段，贴合历史格式）。"""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


class Drift(Exception):
    pass


def _slice_body_text(path):
    """取切片中「节点 YAML 正文」部分（切片头 + 标记行之后）。"""
    txt = path.read_text(encoding="utf-8")
    if SLICE_BODY_MARK not in txt:
        raise Drift(f"{path.name} 缺正文标记行 —— 切片结构被破坏（拒绝猜测正文起点）")
    return txt.split(SLICE_BODY_MARK, 1)[1].lstrip("\n")


def _read_routing(idx_text):
    idx = yaml.safe_load(idx_text)
    if not isinstance(idx, dict):
        raise Drift("index.yaml 顶层不是映射")
    routing = idx.get("nodes")
    if not isinstance(routing, list) or not routing:
        raise Drift("index.yaml 缺 nodes 路由表或为空（顺序真源不可判定）")
    # ③ 契约段键集注册表对账
    got = {k for k in idx if k != "nodes"}
    if got != set(CONTRACT_KEYS):
        raise Drift(
            "契约段键集与注册表不一致（新增/漏登记会静默漏配）："
            f"多={sorted(got - set(CONTRACT_KEYS))} 少={sorted(set(CONTRACT_KEYS) - got)}"
        )
    return routing


def build_assembly(truth_dir=TRUTH_DIR):
    """真源（原文）→ 装配视图文本。纯函数，便于 --check 比对。"""
    index_path = truth_dir / "index.yaml"
    if not index_path.is_file():
        raise Drift("真源缺失：index.yaml 不存在（流程真源第一部分）")
    idx_text = index_path.read_text(encoding="utf-8")
    routing = _read_routing(idx_text)

    # 契约段原文 = 首个数据行 → `nodes:` 行之前（逐字保留注释与引号）
    lines = idx_text.splitlines(keepends=True)
    start = next((i for i, l in enumerate(lines) if not l.lstrip().startswith("#")), None)
    if start is None:
        raise Drift("index.yaml 无数据段（只有注释？）")
    nodes_at = next((i for i, l in enumerate(lines) if i > start and l.rstrip("\n") == "nodes:"), None)
    if nodes_at is None:
        raise Drift("index.yaml 缺顶层 `nodes:` 行（无法切分契约段与路由段）")
    contract_raw = lines[start:nodes_at]
    # 契约段内以标记行占位 phase_order（该段由生成器注入，位置沿用历史文档结构）
    mi = next((i for i, l in enumerate(contract_raw) if l.rstrip("\n") == PO_INJECT_MARK), None)
    if mi is None:
        raise Drift("index.yaml 契约段缺 phase_order 注入标记行（结构漂移）")
    contract_pre = "".join(contract_raw[:mi]).rstrip("\n") + "\n\n"
    after_po = "".join(contract_raw[mi + 1:])
    if PIPE_INJECT_MARK not in after_po:
        raise Drift("index.yaml 契约段缺 pipeline 注入标记行（结构漂移）")
    post_a, post_b = after_po.split(PIPE_INJECT_MARK, 1)
    contract_mid = post_a.strip("\n") + "\n\n" if post_a.strip("\n") else ""
    contract_post = post_b.strip("\n")
    contract_post = ("\n" + contract_post + "\n") if contract_post else ""

    # ① ② 闭合 + 正文一致性；同时收集 pipeline 文本与 phase_order 条目
    seen, pipe_chunks, entries = set(), [], []
    for r in routing:
        if not isinstance(r, dict) or "node" not in r:
            raise Drift(f"路由项缺 node 字段：{r!r}")
        nid = r["node"]
        if nid in seen:
            raise Drift(f"节点 id 在路由中重复：{nid}（后键会静默覆盖前键）")
        seen.add(nid)
        sp = truth_dir / f"{nid}.yaml"
        if not sp.is_file():
            raise Drift(f"路由声明了节点 {nid}，但切片 {nid}.yaml 不存在")
        body = _slice_body_text(sp)
        parsed = yaml.safe_load(body)
        if not isinstance(parsed, list) or len(parsed) != 1 or not isinstance(parsed[0], dict):
            raise Drift(f"切片 {nid}.yaml 正文不是「单元素节点序列」")
        node = parsed[0]
        if node.get("id") != nid:
            raise Drift(f"切片 {nid}.yaml 的 id 字段为 {node.get('id')!r} —— 与文件名/路由不一致")
        for rk, bk in (("seq", "phase_seq"), ("phase", "phase")):
            if rk in r and r[rk] != node.get(bk):
                raise Drift(f"{nid}: 路由 {rk}={r[rk]!r} 与切片正文 {bk}={node.get(bk)!r} 不一致")
        entries.append({"seq": node.get("phase_seq"), "phase": node.get("phase"), "node": nid})
        # 逐行 +2 缩进拼入 pipeline:（不重新序列化 ⇒ 注释与引号原样保留）
        pipe_chunks.append("".join(("  " + ln if ln.strip() else ln)
                                   for ln in body.splitlines(keepends=True)))

    stray = sorted(p.stem for p in truth_dir.glob("*.yaml")
                   if p.name != "index.yaml" and p.stem not in seen)
    if stray:
        raise Drift(f"存在未被路由的孤儿切片（新文件默认入装配 → C-1 同型）：{stray}")

    missing_seq = [e["node"] for e in entries if e["seq"] is None]
    if missing_seq:
        raise Drift(f"节点缺 phase_seq，无法生成顺序表：{missing_seq}")
    entries.sort(key=lambda e: e["seq"])          # 顺序表按 seq 升序（历史口径）
    po_text = yaml.dump({"phase_order": entries}, Dumper=_IndentDumper, allow_unicode=True,
                        sort_keys=False, default_flow_style=False, width=100000)
    return (ASSEMBLY_HEADER + contract_pre + po_text + "\n" + contract_mid
            + "pipeline:\n" + "".join(pipe_chunks) + contract_post)


def main(argv):
    check = "--check" in argv[1:]
    try:
        expected = build_assembly()
    except Drift as e:
        print(f"❌ 流程真源不可装配：{e}", file=sys.stderr)
        return 1
    if check:
        if not ASSEMBLY.is_file():
            print("❌ 装配视图缺失：references/_shared/真源/phase-order.yaml", file=sys.stderr)
            return 1
        if ASSEMBLY.read_text(encoding="utf-8") != expected:
            print("❌ 装配视图与真源逐字节不一致：", file=sys.stderr)
            print("   装配视图被手改，或真源已改而未重新生成", file=sys.stderr)
            print("   修法：跑维护者侧生成器（本仓 scripts/ 下 phase-order-slice.py）后提交", file=sys.stderr)
            return 1
        n = len(yaml.safe_load(INDEX.read_text(encoding="utf-8"))["nodes"])
        print(f"✅ 装配视图与真源逐字节一致（真源 {n + 1} 文件：1 索引 + {n} 节点切片）")
        return 0
    changed = not ASSEMBLY.is_file() or ASSEMBLY.read_text(encoding="utf-8") != expected
    ASSEMBLY.write_text(expected, encoding="utf-8")
    n = len(yaml.safe_load(INDEX.read_text(encoding="utf-8"))["nodes"])
    print(f"✅ 装配完成：phase-order.yaml ← index.yaml + {n} 节点切片"
          f"（{'已更新' if changed else '无变化'}，{len(expected)} 字符）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
