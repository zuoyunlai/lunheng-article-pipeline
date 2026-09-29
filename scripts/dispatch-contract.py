#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dispatch-contract.py — 论衡派发话术合同块生成与校验（v2.15.x 第二批机械门）。

背景（2026-09-29 审计修订 P0-1/P1-4 同源）：
  G14 复检轮次、T9 默认触发、owner_peer_review_opt_out 等派发话术关键口径
  此前与 phase-order 真源靠**人记住 N 处同步**——P0-1（复检口径矛盾）与 P1-4
  （T9 默认触发）正是漂移结果。本工具从 references/_shared/真源/phase-order/<node>.yaml
  提取节点契约字段，写入 dispatch/*.md 顶部 `<!-- generated: dispatch-contract -->` 块；
  --check 模式在构建期阻断漂移，把上述两类问题升级为「构建期红」。

设计（最小化、零误伤）：
  - 块只插在版本头 + 语言政策**之后**、正文之前（不动既有结构）
  - 块内只放构建期可机读的锚点（node / phase / default / recheck_max / opt_out_key / on_opt_out）
  - 块由 BEGIN/END 注释包夹；已存在则替换，绝不重复
  - --check 跑无写盘副作用；漂移即 exit 1

用法：
  python3 scripts/dispatch-contract.py              # 生成并写盘
  python3 scripts/dispatch-contract.py --check      # 只校验，漂移即 exit 1
  python3 scripts/dispatch-contract.py --stdout      # 打印合同块（供调试 / 测试）

覆盖节点（node_id → dispatch 文件名）：
  g14_style_gate  → references/dispatch/G14-中文AI痕迹检测器.md
  t9_review       → references/dispatch/T9-同行评审.md
"""
import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "references" / "dispatch"
PHASE_ORDER = ROOT / "references" / "_shared" / "真源" / "phase-order"

NODE_TO_DISPATCH = {
    "g14_style_gate": "G14-中文AI痕迹检测器.md",
    "t9_review": "T9-同行评审.md",
}

BEGIN = "<!-- generated: dispatch-contract (do not edit by hand) -->"
END = "<!-- /generated -->"

# 节点特定常量（与 phase-order 真源注释保持一致；改这里 = 改 phase-order 注释，反向亦同）
NODE_CONSTANTS = {
    "g14_style_gate": {"recheck_max_rounds": 2},
    "t9_review": {"recheck_max_rounds": 0},
}


def _load_node(node_id: str) -> dict:
    src = PHASE_ORDER / f"{node_id}.yaml"
    if not src.is_file():
        raise SystemExit(f"phase-order slice missing: {src.relative_to(ROOT)}")
    spec = yaml.safe_load(src.read_text(encoding="utf-8"))
    if not isinstance(spec, list) or not spec:
        raise SystemExit(f"unexpected yaml shape (expected list with one node): {src.relative_to(ROOT)}")
    return spec[0]


def generate_block(node_id: str) -> str:
    """从 phase-order/<node>.yaml 提取契约字段，生成合同块。"""
    node = _load_node(node_id)
    fields = {
        "node": node.get("id"),
        "phase": node.get("phase"),
        "default": node.get("default") or ("required" if not node.get("opt_out") else "opt_in"),
        "opt_out_key": node.get("opt_out") or "n/a",
        "on_opt_out": node.get("on_opt_out") or "n/a",
        "condition": node.get("condition") or "n/a",
    }
    constants = NODE_CONSTANTS.get(node_id, {})
    if "recheck_max_rounds" in constants:
        fields["recheck_max_rounds"] = constants["recheck_max_rounds"]

    lines = [BEGIN]
    for k, v in fields.items():
        lines.append(f"{k}: {v}")
    lines.append(END)
    return "\n".join(lines) + "\n"


def _insertion_point(lines: list[str]) -> int:
    """找到版本头 + 语言政策之后、正文之前的插入位置。

    跳过所有 `>` 开头行（版本头 / 语言政策 / 权威源等），直到首个
    非 `>` 非空行。安全默认值 = 0（文件首行之前）。
    """
    for i, line in enumerate(lines):
        if line.startswith(">") or line.strip() == "":
            continue
        return i
    return 0


def inject_block(doc_text: str, block: str) -> tuple[str, bool]:
    """把合同块插入 dispatch 文档；若已存在则替换。返回 (新文本, 是否变更)。"""
    if BEGIN in doc_text and END in doc_text:
        # 替换已有块
        pre, _, rest = doc_text.partition(BEGIN)
        _, _, post = rest.partition(END)
        return pre + block.rstrip("\n") + post, False
    # 插入到版本头 + 语言政策之后
    lines = doc_text.splitlines(keepends=False)
    insert_at = _insertion_point(lines)
    lines.insert(insert_at, "")
    lines.insert(insert_at + 1, block.rstrip("\n"))
    return "\n".join(lines) + "\n", True


def check_one(node_id: str, dispatch_name: str) -> list[str]:
    errors = []
    p = DISPATCH / dispatch_name
    if not p.is_file():
        return [f"{dispatch_name}: missing dispatch file"]
    text = p.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        return [f"{dispatch_name}: missing generated contract block (rerun make dispatch-contract)"]
    pre, _, rest = text.partition(BEGIN)
    existing, _, post = rest.partition(END)
    # 只比较块体：BEGIN / END 两行本身是常量，不参与字段级对账
    # （原实现在这里把 BEGIN 行也算进 expected，导致生成后 --check 恒红）
    expected_lines = [l for l in generate_block(node_id).rstrip("\n").splitlines()
                      if l not in (BEGIN, END)]
    actual_lines = [l for l in existing.strip().splitlines() if l.strip()]
    if actual_lines != expected_lines:
        for i, (e, a) in enumerate(zip(expected_lines, actual_lines)):
            if e != a:
                errors.append(f"{dispatch_name}: contract drift at line {i+1}: expected={e!r} actual={a!r}")
                break
        else:
            if len(expected_lines) != len(actual_lines):
                errors.append(
                    f"{dispatch_name}: contract block line count differs: "
                    f"expected={len(expected_lines)} actual={len(actual_lines)}"
                )
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验，漂移即 exit 1（供门使用）")
    ap.add_argument("--stdout", action="store_true", help="打印合同块到 stdout，不写盘")
    args = ap.parse_args()

    if args.stdout:
        for nid, _ in NODE_TO_DISPATCH.items():
            print(f"--- {nid} ---")
            print(generate_block(nid))
        return 0

    if args.check:
        errors = []
        for nid, name in NODE_TO_DISPATCH.items():
            errors.extend(check_one(nid, name))
        if errors:
            print("\n".join(errors))
            return 1
        print(f"dispatch-contract: PASS（{len(NODE_TO_DISPATCH)} 个合同块与 phase-order 真源一致）")
        return 0

    # 默认：生成并写盘
    updated = 0
    for nid, name in NODE_TO_DISPATCH.items():
        p = DISPATCH / name
        text = p.read_text(encoding="utf-8")
        new, changed = inject_block(text, generate_block(nid))
        if changed:
            p.write_text(new, encoding="utf-8")
            print(f"✅ inserted: {name}")
            updated += 1
        else:
            print(f"⏭️  replaced: {name}")
            updated += 1
            p.write_text(new, encoding="utf-8")
    print(f"dispatch-contract: 已更新 {updated} / {len(NODE_TO_DISPATCH)} 个 dispatch 文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
