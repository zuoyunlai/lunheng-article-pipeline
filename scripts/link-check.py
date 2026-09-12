#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""link-check.py — 相对链接可解析性检查（v2.12.30 新增，回应第三方审计 P2）

背景：CHANGELOG 曾积累 10 处**结构性断链**（`../outputs/*` 指向 .gitignore 的产物目录、
`docs/*` 指向不存在的目录、裸相对名指向不存在的文件）。这类断链对任何克隆者都不可达，
且**没有机械门**会发现它们 —— 只有人工点开才会暴露。

判定：只查**相对链接**（`http(s)://` 不查，避免联网）。
      `#锚点` 单独考虑：跳过（锚点校验属另一维度，且易误报）。
      解析基准 = 含链接文件所在目录。
      忽略**代码围栏**与**行内代码**中的链接（它们是示例文本，不是真链接 ——
      本脚本首跑即在 CHANGELOG 的历史修订说明上踩到这个误报）。

用法：
  python3 scripts/link-check.py [文件或目录 ...]        # 默认：README/QUICKSTART/CHANGELOG/references
  python3 scripts/link-check.py --list                  # 只列不断言（自查用）
退出码：0 = 无断链 / 1 = 存在断链 / 2 = 用法错误
"""
import pathlib
import re
import sys

DEFAULT_TARGETS = ["README.md", "QUICKSTART.md", "CHANGELOG.md", "SKILL.md", "references"]
FENCE_RE = re.compile(r'^\s*(```|~~~)')
INLINE_CODE_RE = re.compile(r'`[^`\n]*`')
LINK_RE = re.compile(r'\[[^\]\n]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')


def strip_code(text: str) -> str:
    """去掉代码围栏内容与行内代码，避免把示例链接当真链接"""
    out, in_fence = [], False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else INLINE_CODE_RE.sub("", line))
    return "\n".join(out)


def iter_files(targets):
    for t in targets:
        p = pathlib.Path(t)
        if p.is_file() and p.suffix == ".md":
            yield p
        elif p.is_dir():
            yield from sorted(x for x in p.rglob("*.md") if x.is_file())


def check(targets):
    broken, checked = [], 0
    for f in iter_files(targets):
        text = strip_code(f.read_text(encoding="utf-8", errors="replace"))
        for m in LINK_RE.finditer(text):
            url = m.group(1)
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', url):   # http(s)/mailto 等
                continue
            if url.startswith("#"):
                continue
            target = (f.parent / url.split("#")[0]).resolve()
            checked += 1
            if not target.exists():
                broken.append((str(f), url))
    return broken, checked


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 2
    targets = args or DEFAULT_TARGETS
    broken, checked = check(targets)
    if broken:
        print(f"❌ 相对链接断链 {len(broken)} 处（共检查 {checked} 条）：", file=sys.stderr)
        for f, url in broken:
            print(f"   {f} → {url}", file=sys.stderr)
        print("   修法：修正路径；产物在 .gitignore 目录（如 outputs/）或已不存在的文档，"
              "应降级为**无链接的陈述**（见 CHANGELOG 既有先例）。", file=sys.stderr)
        return 1
    print(f"✅ 相对链接全部可解析（共 {checked} 条，覆盖 {len(list(iter_files(targets)))} 个 md）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
