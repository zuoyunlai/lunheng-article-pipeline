#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dispatch-contract.py — 论衡派发/轮次契约块生成与校验（v2.15.x 第二批机械门；2026-10-05 架构评审 v3 R2 真源化重写）。

背景（2026-09-29 审计修订 P0-1/P1-4 同源；2026-10-05 R2 收口）：
  派发话术关键口径（G14 复检轮次、T9 默认触发、T1b 回查上限、owner 节点 opt-out 键）
  与 phase-order 真源同步，此前靠「人记住 N 处」或**代码侧无源常量**——旧 NODE_CONSTANTS
  把 recheck_max_rounds 硬编码在生成器里（t9 的 0 在切片中任何层级都不存在 = 纯代码侧
  发明），而 --check 比较的是「生成结果 vs 生成结果」，常量漂移对门不可见。
  本工具把全部契约面改为**从切片现算**，三族判据：

  ① dispatch 合同块：切片带 `dispatch:` 字段 ⇒ 该节点入覆盖集（新增节点零手工登记）。
     块字段直读切片（default / opt_out / on_opt_out / condition / recheck_max_rounds /
     max_rounds / style_recheck_rounds_max），无任何代码侧常量。
  ② 轮次合同块：pipeline-overview.md「修订回环仲裁规则」段顶部生成块 =
     全仓轮次上限字段的唯一机械登记处（audit_revision / t1b / g14 / t5_style_revision /
     t9_review 的轮限逐条从切片现算）；改切片 ⇒ 重跑生成 ⇒ --check 对账。
     T5 dispatch 明文「不复述轮次数字」——轮次契约的唯一载体就是本块，不入派发文件。
  ③ owner 节点 opt-out 载体检查：t9b / methodology_snapshot 是 owner 节点（不 spawn、
     无 dispatch 文件），其 opt-out 键的实际载体（任务简报模板 / 主控扩展职责卡）由切片
     `opt_out_carriers:` 显式登记，--check 逐文件验「键在载体」。

设计（最小化、零误伤）：
  - dispatch 块只插在版本头 + 语言政策之后、正文之前；已存在则替换，绝不重复
  - 轮次块只插在「## 修订回环仲裁规则」标题之后；已存在则替换
  - --check 跑无写盘副作用；漂移即 exit 1

用法：
  python3 scripts/dispatch-contract.py              # 生成并写盘（dispatch 块 + 轮次块）
  python3 scripts/dispatch-contract.py --check      # 只校验（三族判据），漂移即 exit 1
  python3 scripts/dispatch-contract.py --stdout     # 打印全部块（供调试 / 测试）
"""
import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PHASE_ORDER = ROOT / "references" / "_shared" / "真源" / "phase-order"
OVERVIEW = ROOT / "references" / "_shared" / "真源" / "pipeline-overview.md"

BEGIN = "<!-- generated: dispatch-contract (do not edit by hand) -->"
END = "<!-- /generated -->"
ROUNDS_BEGIN = "<!-- generated: rounds-contract (do not edit by hand) -->"
ROUNDS_END = "<!-- /generated -->"
ROUNDS_HEADING = "## 修订回环仲裁规则"

# 轮次上限字段族（切片现算的唯一来源；本模块零常量）
ROUND_KEYS = ("recheck_max_rounds", "max_rounds", "style_recheck_rounds_max")


def _slices():
    for p in sorted(PHASE_ORDER.glob("*.yaml")):
        if p.name == "index.yaml":
            continue
        yield p


def _load_slice(path):
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(spec, list) or not spec:
        raise SystemExit(f"unexpected yaml shape (expected list with one node): {path}")
    return spec[0]


def _load_node(node_id):
    src = PHASE_ORDER / f"{node_id}.yaml"
    if not src.is_file():
        raise SystemExit(f"phase-order slice missing: {src}")
    return _load_slice(src)


def covered_nodes():
    """覆盖集 = 切片带 `dispatch:` 字段的节点 → [(node_id, dispatch_rel)]。零手工登记。"""
    out = []
    for p in _slices():
        node = _load_slice(p)
        d = node.get("dispatch")
        if d:
            out.append((node["id"], d))
    return out


def rounds_declarations():
    """全仓轮次上限字段 → [(phase_seq, node_id, key, value)]，从切片现算。"""
    out = []
    for p in _slices():
        node = _load_slice(p)
        for key in ROUND_KEYS:
            if key in node:
                out.append((node.get("phase_seq") or 0, node["id"], key, node[key]))
    out.sort(key=lambda r: (r[0], r[1]))
    return out


def owner_carrier_specs():
    """owner 节点 opt-out 载体登记 → [(node_id, opt_out_key, [carrier_rel])]。"""
    out = []
    for p in _slices():
        node = _load_slice(p)
        if node.get("opt_out_carriers"):
            out.append((node["id"], node.get("opt_out"), list(node["opt_out_carriers"])))
    return out


def generate_block(node_id):
    """从 phase-order/<node>.yaml 提取契约字段，生成 dispatch 合同块（无代码侧常量）。"""
    node = _load_node(node_id)
    fields = {
        "node": node.get("id"),
        "phase": node.get("phase"),
        "default": node.get("default") or ("required" if not node.get("opt_out") else "opt_in"),
        "opt_out_key": node.get("opt_out") or "n/a",
        "on_opt_out": node.get("on_opt_out") or "n/a",
        "condition": node.get("condition") or "n/a",
    }
    for key in ROUND_KEYS:
        if key in node:
            fields[key] = node[key]
    lines = [BEGIN] + [f"{k}: {v}" for k, v in fields.items()] + [END]
    return "\n".join(lines) + "\n"


def generate_rounds_block():
    """全仓轮限字段 → 轮次合同块（pipeline-overview.md 仲裁段）。"""
    lines = [ROUNDS_BEGIN]
    for _, nid, key, value in rounds_declarations():
        lines.append(f"{nid}.{key}: {value}")
    lines.append(ROUNDS_END)
    return "\n".join(lines) + "\n"


def _insertion_point(lines):
    """dispatch 文档：跳过所有 `>` 开头行（版本头 / 语言政策 / 权威源），取首个正文行前。"""
    for i, line in enumerate(lines):
        if line.startswith(">") or line.strip() == "":
            continue
        return i
    return 0


def inject_block(doc_text, block):
    """把合同块插入 dispatch 文档；若已存在则替换。返回 (新文本, 是否变更)。"""
    if BEGIN in doc_text and END in doc_text:
        pre, _, rest = doc_text.partition(BEGIN)
        _, _, post = rest.partition(END)
        return pre + block.rstrip("\n") + post, False
    lines = doc_text.splitlines(keepends=False)
    insert_at = _insertion_point(lines)
    lines.insert(insert_at, "")
    lines.insert(insert_at + 1, block.rstrip("\n"))
    return "\n".join(lines) + "\n", True


def inject_rounds_block(doc_text, block):
    """把轮次块插入 pipeline-overview.md 仲裁段标题之后；已存在则替换。"""
    if ROUNDS_BEGIN in doc_text and ROUNDS_END in doc_text:
        pre, _, rest = doc_text.partition(ROUNDS_BEGIN)
        _, _, post = rest.partition(ROUNDS_END)
        return pre + block.rstrip("\n") + post, False
    lines = doc_text.splitlines(keepends=False)
    h = next((i for i, ln in enumerate(lines) if ln.strip() == ROUNDS_HEADING), None)
    if h is None:
        raise SystemExit(f"pipeline-overview.md 缺「{ROUNDS_HEADING}」标题（轮次块插入点丢失）")
    # 标题后统一整形为：heading / 空 / 块 / 空 / 原内容
    if h + 1 < len(lines) and lines[h + 1].strip() == "":
        del lines[h + 1]
    lines[h + 1:h + 1] = ["", block.rstrip("\n"), ""]
    return "\n".join(lines) + "\n", True


def _compare_block(expected_text, existing, label, begin, end):
    """块体逐行对账（BEGIN/END 常量行不参与），返回错误列表。"""
    expected_lines = [l for l in expected_text.rstrip("\n").splitlines() if l not in (begin, end)]
    actual_lines = [l for l in existing.strip().splitlines() if l.strip()]
    if actual_lines != expected_lines:
        for i, (e, a) in enumerate(zip(expected_lines, actual_lines)):
            if e != a:
                return [f"{label}: contract drift at line {i+1}: expected={e!r} actual={a!r}"]
        return [f"{label}: contract block line count differs: "
                f"expected={len(expected_lines)} actual={len(actual_lines)}"]
    return []


def check_one(node_id, dispatch_rel):
    errors = []
    p = ROOT / dispatch_rel
    if not p.is_file():
        return [f"{dispatch_rel}: missing dispatch file"]
    text = p.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        return [f"{dispatch_rel}: missing generated contract block (rerun make dispatch-contract)"]
    _, _, rest = text.partition(BEGIN)
    existing, _, _ = rest.partition(END)
    return _compare_block(generate_block(node_id), existing, dispatch_rel, BEGIN, END)


def check_rounds():
    if not OVERVIEW.is_file():
        return ["pipeline-overview.md: missing file"]
    text = OVERVIEW.read_text(encoding="utf-8")
    if ROUNDS_BEGIN not in text or ROUNDS_END not in text:
        return ["pipeline-overview.md: missing rounds contract block (rerun make dispatch-contract)"]
    _, _, rest = text.partition(ROUNDS_BEGIN)
    existing, _, _ = rest.partition(ROUNDS_END)
    return _compare_block(generate_rounds_block(), existing, "pipeline-overview.md",
                          ROUNDS_BEGIN, ROUNDS_END)


def check_owner_carriers(root=None):
    """owner 节点 opt-out 键必须真实存在于切片登记的每个载体文件（防契约断链）。"""
    base = root if root is not None else ROOT
    errors = []
    for nid, key, rels in owner_carrier_specs():
        if not key:
            errors.append(f"{nid}: opt_out_carriers 声明但切片缺 opt_out 字段（结构矛盾）")
            continue
        for rel in rels:
            c = base / rel
            if not c.is_file():
                errors.append(f"{nid}: opt-out 载体缺失 {rel}")
                continue
            if key not in c.read_text(encoding="utf-8"):
                errors.append(f"{nid}: opt-out 键「{key}」不在载体 {rel}（owner 契约断链）")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验，漂移即 exit 1（供门使用）")
    ap.add_argument("--stdout", action="store_true", help="打印合同块到 stdout，不写盘")
    args = ap.parse_args()

    nodes = covered_nodes()
    n_carriers = sum(len(rels) for _, _, rels in owner_carrier_specs())

    if args.stdout:
        for nid, rel in nodes:
            print(f"--- {nid} → {rel} ---")
            print(generate_block(nid))
        print("--- rounds → pipeline-overview.md ---")
        print(generate_rounds_block())
        return 0

    if args.check:
        errors = []
        for nid, rel in nodes:
            errors.extend(check_one(nid, rel))
        errors.extend(check_rounds())
        errors.extend(check_owner_carriers())
        if errors:
            print("\n".join(errors))
            return 1
        print(f"dispatch-contract: PASS（{len(nodes)} 个派发合同块 + 1 个轮次块 + "
              f"{n_carriers} 项 owner 载体检查，全部与切片真源一致）")
        return 0

    # 默认：生成并写盘
    updated = 0
    for nid, rel in nodes:
        p = ROOT / rel
        new, _ = inject_block(p.read_text(encoding="utf-8"), generate_block(nid))
        p.write_text(new, encoding="utf-8")
        updated += 1
    ov_new, _ = inject_rounds_block(OVERVIEW.read_text(encoding="utf-8"), generate_rounds_block())
    OVERVIEW.write_text(ov_new, encoding="utf-8")
    print(f"dispatch-contract: 已更新 {updated} 个 dispatch 合同块 + 1 个轮次合同块"
          f"（pipeline-overview.md）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
