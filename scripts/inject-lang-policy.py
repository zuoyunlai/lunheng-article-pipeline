#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inject-lang-policy.py — 批量注入「语言政策」声明行（幂等）

背景（v2.12.9，回应 ClawHub SkillSpector「Natural-Language Policy Violations」类发现）：
  扫描器逐文件判定「中文-only 且未声明 opt-in / 未说明区域限定」。
  SKILL.md 已有「语言边界」表，但净化包 78 个 md 里其余文件没有声明，
  导致同一类 finding 被重复报出十余次。本脚本为每个交付文件补一行标准声明。

用法：
  python3 scripts/inject-lang-policy.py            # 注入（幂等）
  python3 scripts/inject-lang-policy.py --dry-run  # 只报告不写入
  python3 scripts/inject-lang-policy.py --check    # 只校验，缺失即 exit 1（供门使用）

插入位置优先级：
  1) 顶部 `> 版本：...` 行之后（sync-version.sh 生成的行）
  2) YAML frontmatter 关闭 `---` 之后
  3) 文件第 1 行之前
"""

import argparse
import os
import sys

MARKER = "🌐 **语言政策**"
LINE = (
    "> 🌐 **语言政策**：产出语言默认中文，Phase 0 可改 English / 中英混 / 其他"
    "（写入任务简报「目标语言」字段，全流程以该字段为准）；"
    "中文特化（G14 中文 AI 痕迹检测 / GB/T 7714-2015 引用规范）是设计定位，"
    "不构成使用者语种限制。"
)

# 交付文件根（相对 skill 根）
ROOTS = ["REFERENCES", "QUICKSTART.md", "README.md"]

# 不随净化包分发 / 已有独立语言声明 → 不注入
EXCLUDE_REL = {
    "SKILL.md",
    "CHANGELOG.md",
    "references/设计文档.md",
    "references/设计文档-架构.md",
    "references/设计文档-哲学.md",
    "references/_shared/教训索引.md",
    "references/templates/README-模板拆分方案.md",
}


def targets(skill_root):
    out = []
    for root in ROOTS:
        if root.upper() == "REFERENCES":
            base = os.path.join(skill_root, "references")
            if not os.path.isdir(base):
                continue
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [d for d in dirnames if d not in (".git", "outputs", "archive")]
                for name in filenames:
                    if not name.endswith(".md") or ".bak." in name:
                        continue
                    full = os.path.join(dirpath, name)
                    rel = os.path.relpath(full, skill_root)
                    if rel in EXCLUDE_REL:
                        continue
                    out.append((full, rel))
        else:
            full = os.path.join(skill_root, root)
            if os.path.isfile(full) and root not in EXCLUDE_REL:
                out.append((full, root))
    return sorted(out, key=lambda x: x[1])


def inject(text):
    """返回 (新文本, 是否变更)"""
    if MARKER in text:
        return text, False

    lines = text.split("\n")

    # 1) 顶部版本行之后（版本行通常在文件最前几行）
    for i, line in enumerate(lines[:5]):
        if line.startswith("> 版本："):
            lines.insert(i + 1, LINE)
            return "\n".join(lines), True

    # 2) YAML frontmatter 关闭之后
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                lines.insert(i + 1, LINE)
                return "\n".join(lines), True

    # 3) 文件最前
    lines.insert(0, LINE)
    return "\n".join(lines), True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只报告不写入")
    ap.add_argument("--check", action="store_true", help="只校验，缺失即 exit 1")
    args = ap.parse_args()

    skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = targets(skill_root)

    changed, missing = [], []
    for full, rel in files:
        with open(full, encoding="utf-8") as f:
            text = f.read()
        if MARKER in text:
            continue
        missing.append(rel)
        if args.check:
            continue
        changed.append(rel)
        if args.dry_run:
            continue
        new_text, _ = inject(text)
        with open(full, "w", encoding="utf-8") as f:
            f.write(new_text)

    if args.check:
        if missing:
            print(f"❌ 语言政策声明缺失 {len(missing)} 个文件：")
            for rel in missing:
                print(f"  - {rel}")
            return 1
        print(f"✅ 语言政策声明完整（{len(files)} 个交付文件）")
        return 0

    verb = "将修改" if args.dry_run else "已注入"
    print(f"{verb} {len(changed)} / 扫描 {len(files)} 个交付文件")
    for rel in changed:
        print(f"  - {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
