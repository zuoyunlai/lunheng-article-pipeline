#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""markdown-structure-lint.py — 确定性 Markdown 结构门。

检查字面量 \\n与未闭合围栏；--strict 额外检查重复章号与孤立标题。
维护者工具；默认扫描当前仓库的受管 Markdown。
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")

# 默认排除面（**唯一真源**：脚本 main() 与 tests/test_markdown_structure_lint.py 共用本常量，
# 避免「脚本一份、测试硬编码一份」的两套判据漂移——本仓反复出现的反模式）。
#   - `CHANGELOG` 子串命中 CHANGELOG.md / CHANGELOG-archive.md（子串匹配**大小写敏感**）
#   - `changelog-cold` 命中冷归档（小写文件名，**不被 `CHANGELOG` 命中**——v2.15.10 补记；
#     该文件与上面两个同属 changelog 历史层，历史原文不得为过 lint 而改写）
DEFAULT_EXCLUDES = ("reports/", "archive/", "教训索引.md", "CHANGELOG", "changelog-cold")
NUMBERED = re.compile(r"^(?:第\s*)?([一二三四五六七八九十百千万0-9]+)[、.．)]\s*(.*)$")

def lint_text(text: str, rel: str = "<text>", strict: bool = False) -> list[str]:
    errors=[]; lines=text.splitlines(); in_fence=False; prev_heading=False; seen={}
    for no,line in enumerate(lines,1):
        if re.match(r"^\s*(`{3,}|~{3,})", line):
            in_fence=not in_fence; continue
        if not in_fence and r"\n" in line:
            errors.append(f"{rel}:{no}: literal \\n")
        if in_fence: continue
        m=HEADING.match(line)
        if m:
            body=m.group(2)
            n=NUMBERED.match(body)
            if strict and n:
                key=(len(m.group(1)), n.group(1))
                if key in seen:
                    errors.append(f"{rel}:{no}: duplicate section number {n.group(1)} (first line {seen[key]})")
                seen[key]=no
            if strict and prev_heading:
                errors.append(f"{rel}:{no}: isolated heading after heading at line {no-1}")
            prev_heading=True
        elif line.strip():
            prev_heading=False
    if in_fence: errors.append(f"{rel}: unclosed code fence")
    return errors

def scan(root: Path, excludes: tuple[str,...]=(), strict: bool = False) -> list[str]:
    out=[]
    for p in sorted(root.rglob("*.md")):
        rel=p.relative_to(root).as_posix()
        if ".git/" in rel or any(x in rel for x in excludes): continue
        out.extend(lint_text(p.read_text(encoding="utf-8"), rel, strict=strict))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=Path(__file__).resolve().parents[1])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--strict", action="store_true", help="额外检查重复章号与孤立标题；仅用于单文件/新文档核验")
    args=ap.parse_args(); root=Path(args.root)
    # ⚠️ v2.15.10 补 `changelog-cold`：排除元组是**大小写敏感**的子串匹配，而冷归档文件
    #   名为小写 `changelog-cold-v2.0-v2.12.md`，此前从未被 `CHANGELOG` 命中 ⇒ 该文件一直
    #   在扫描面内（潜伏缺陷：前几版冷归档恰好无违规内容而未暴露）。它与 CHANGELOG.md /
    #   CHANGELOG-archive.md 同属 changelog 历史层，理应同侧排除——**历史原文不得为过 lint 而改写**。
    errors=scan(root, DEFAULT_EXCLUDES, strict=args.strict)
    if errors:
        print("\n".join(errors)); return 1
    print("markdown structure lint: PASS"); return 0
if __name__ == "__main__": raise SystemExit(main())
