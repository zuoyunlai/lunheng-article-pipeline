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

第二类检查（v2.12.31 新增）：**入口文档裸文件引用**。ClawHub 扫描（SkillSpector）
      曾对 SKILL.md 报 **AE1 HIGH**「Referenced artifact was not completely inspected」，
      命中的是「主控必读文档清单」表内的**裸文件名**（`pipeline-readme.md`）——
      外部读取者/扫描器无法判定它相对哪个目录，因而无法定位该产物（与「悬挂指针」同族）。
      本类只查 SKILL.md（外部读取者实际读的入口文件），不查 references/ ——
      后者含 200+ 处**运行时项目树路径**（`status.md` / `final/定稿.md` 等），非仓库文件。
      解析基准 = **入口文档自身所在目录**（严格：不试 `references/` 等子目录，
      否则 AE1 那类「裸名但碰巧能找回」的写法永远不报）。
      链接文本不查——整个 markdown 链接（`[文本](url)`，含文本带后缀词的写法）先剔除，
      路径真伪由第一类（相对链接）负责，不重复判定。
      豁免：占位符（`<` `>` `{` `}` `*` `$`）、官方文档前缀（`docs/`）、`~` 路径，
            含空格 token，以及下方显式允许清单（运行时文件 / 有意提及不存在者）。

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


# -----------------------------------------------------------------------------
# 第二类：入口文档裸文件引用（v2.12.31 新增，回应 ClawHub SkillSpector AE1 HIGH）
#   解析基准 = **入口文档自身所在目录**（严格）；链接文本不查（第一类负责路径真伪）。
#   豁免：占位符、`docs/` 官方文档前缀、`~` 路径、含空格 token，以及 BARE_ALLOW。
#   BARE_ALLOW 是**显式债务/合理例外清单**：新增项必须在此注明理由（失败时提示）。
# -----------------------------------------------------------------------------
BARE_EXT_RE = re.compile(r'\.(md|yaml|yml|json)$')
BARE_ENTRY = "SKILL.md"
LINK_TEXT_RE = re.compile(r'\[[^\]\n]*\]\([^)\n]*\)')
BARE_ALLOW = {
    "status.md",       # 运行时文件（run/<项目名>/status.md），非仓库文件
    "01-任务简报.md",   # 运行时文件（run/<项目名>/01-任务简报.md），非仓库文件
    "设计文档.md",      # SKILL.md 明示「发布版无 设计文档.md」——有意提及不存在的文件
}


def check_bare_entry_refs(entry=BARE_ENTRY):
    """入口文档反引号内**独立文件提及**的可解析性 → (不可解析列表, 检查条数)"""
    p = pathlib.Path(entry)
    if not p.is_file():
        return [], 0
    body, in_fence = [], False
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            body.append(line)
    base = p.parent
    bad, checked = [], 0
    for tok in re.findall(r'`([^`\n]+)`', LINK_TEXT_RE.sub(" ", "\n".join(body))):
        t = tok.strip()
        if not BARE_EXT_RE.search(t):
            continue
        if any(c in t for c in '<>{}*$') or " " in t:
            continue
        if t.startswith(("docs/", "http", "~")):
            continue
        if t in BARE_ALLOW:
            continue
        checked += 1
        if not (base / t).exists():
            bad.append((str(p), t))
    return bad, checked


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 2
    targets = args or DEFAULT_TARGETS
    broken, checked = check(targets)
    bare_bad, bare_checked = check_bare_entry_refs()
    if broken or bare_bad:
        if broken:
            print(f"❌ 相对链接断链 {len(broken)} 处（共检查 {checked} 条）：", file=sys.stderr)
            for f, url in broken:
                print(f"   {f} → {url}", file=sys.stderr)
            print("   修法：修正路径；产物在 .gitignore 目录（如 outputs/）或已不存在的文档，"
                  "应降级为**无链接的陈述**（见 CHANGELOG 既有先例）。", file=sys.stderr)
        if bare_bad:
            print(f"❌ 入口文档裸文件引用不可解析 {len(bare_bad)} 处"
                  f"（共检查 {bare_checked} 条）：", file=sys.stderr)
            for f, tok in bare_bad:
                print(f"   {f} → {tok}", file=sys.stderr)
            print("   修法：补全为仓库根相对路径（`references/...`）；确属运行时文件或有意提及"
                  "不存在的文件，加入本脚本 BARE_ALLOW 并注明理由。", file=sys.stderr)
        return 1
    print(f"✅ 相对链接全部可解析（共 {checked} 条，覆盖 {len(list(iter_files(targets)))} 个 md）"
          f"；入口文档裸引用全部可解析（共 {bare_checked} 条）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
