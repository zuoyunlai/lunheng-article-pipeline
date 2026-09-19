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

第三类检查（v2.12.59 新增）：**活文档反引号内联文档引用**（回应 2026-09-19 全面审计 P1-2）。
      前两类各管一半：第一类只认 markdown 链接语法，第二类只认 SKILL.md 的裸文件名。
      而活文档里还有一种写法——**反引号内联路径引用**（例：`_shared/host-verify-recipe.md`），
      它既不是 markdown 链接、又不在入口文档内 ⇒ 两类都不覆盖。
      实测后果：`host-verify-recipe.md` 被 2 处活文档引用却**从未存在过**，且两处均在
      净化包可见面；而本脚本报「全部可解析」——给的是「markdown 链接面全绿」，
      被读者当成「引用面全绿」。门 U 的判据面必须等于**该缺陷类的宿主集**（教训 #427），
      不是「上次出事的那一个位置」。
      扫描面 = `references/**/*.md`（含 templates/）；CHANGELOG*.md 排除（历史归档引用允许失效，
      与第一类既有豁免同构）。
      解析顺序：① 相对引用文件所在目录 → ② 相对仓库根 → ③ 仓库内任意目录的同名文件。
      三级都不命中 ⇒ 报错。豁免 = 占位符 / 空格 / `~` / 宿主文档前缀 `docs/` /
      运行时项目树前缀（见 RUNTIME_PREFIXES）/ 脚本域 `scripts/` /
      显式 INLINE_ALLOW（每条注明理由 —— 该清单是**显式债务**，新增必须写理由）。

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


# -----------------------------------------------------------------------------
# 第三类：活文档反引号内联文档引用（v2.12.59 新增，回应 2026-09-19 全面审计 P1-2）
#   详见文件头「第三类检查」段。核心纪律：门 U 的判据面 = 缺陷类的宿主集（教训 #427）。
# -----------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
INLINE_ROOTS = ["references"]
INLINE_SKIP_NAMES = {"CHANGELOG.md", "CHANGELOG-archive.md"}
# 运行时项目树专用目录：这些前缀下的路径属 run/<项目名>/ 产物，不是仓库文件
RUNTIME_PREFIXES = (
    "audits/", "drafts/", "final/", "analysis/", "data/", "cases/",
    "literature/", "run/", "outputs/", "memory/", ".tmp/",
)
# 宿主/平台域：`docs/...` 与 `scripts/...` 分别是宿主官方文档与开发者侧脚本（不进净化包），
#   均不在「随包分发的文档引用」面内，故整类前缀跳过（与第一类对 docs/ 的豁免一致）。
SKIP_PREFIXES = ("docs/", "scripts/", "http", "~") + RUNTIME_PREFIXES
# 显式债务清单：键 = 文件名（basename），值 = 允许理由。
#   新增项必须在此写明理由；「解析不到就加白名单」是本清单唯一的滥用方式，评审时优先盯这条。
INLINE_ALLOW = {
    "status.md":            "运行时文件 run/<项目名>/status.md",
    "status.redacted.md":   "运行时文件（status.md 脱敏副本）",
    "01-任务简报.md":        "运行时文件 run/<项目名>/01-任务简报.md",
    "current_draft.md":     "运行时文件 run/<项目名>/drafts/current_draft.md",
    "phase-history.md":     "运行时产物 final/phase-history.md",
    "audit-lessons.md":     "运行时产物 run/<项目名>/audit-lessons.md",
    "AGENTS.md":            "宿主工作区种子文件（不在本仓，.gitignore 有意硬拦）",
    "BOOTSTRAP.md":         "宿主工作区种子文件（同上）",
    "IDENTITY.md":          "宿主工作区种子文件（同上）",
    "SOUL.md":              "宿主工作区种子文件（同上）",
    "USER.md":              "宿主工作区种子文件（同上）",
    "设计文档.md":           "明示「发布版无 设计文档.md」——有意提及不存在的文件",
    "06-v2-attack.deepseek-v4-pro.md": "运行时产物 audits/ 下的历史报告文件名（实测 run 证据）",
    "交付说明.md":          "运行时交付物 final/交付说明.md（非仓内文件）",
    "lessons.md":           "宿主主工作区 memory/lessons.md（跨项目教训真源，不在本仓）",
    "01-文献检索-heartbeat.md": "运行时心跳文件名示例 run/<项目>/.tmp/<角色号>-<角色名>-heartbeat.md",
}


def _repo_basename_index() -> set:
    """仓库内全部文件的 basename 集合（排除 .git / 缓存）"""
    idx = set()
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        s = str(p)
        if "/.git/" in s or "/__pycache__/" in s or "/.pytest_cache/" in s:
            continue
        idx.add(p.name)
    return idx


def check_inline_refs(roots=None) -> tuple[list, int]:
    """活文档反引号内联 `.md` 引用的可解析性 → (不可解析列表, 检查条数)"""
    files = []
    for root in (roots or INLINE_ROOTS):
        p = REPO_ROOT / root
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(x for x in p.rglob("*.md") if x.is_file()))
    names = _repo_basename_index()
    bad, checked = [], 0
    for f in files:
        if f.name in INLINE_SKIP_NAMES:
            continue
        body, in_fence = [], False
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if not in_fence:
                body.append(line)
        # 先剔 markdown 链接整体（路径真伪归第一类，不重复判定），再取反引号
        for tok in re.findall(r'`([^`\n]+)`', LINK_TEXT_RE.sub(" ", "\n".join(body))):
            t = tok.strip()
            if not t.endswith(".md") or " " in t:
                continue
            # 扩展名枚举写法（如 `.sh`/`.md`、`.yaml`）不是路径，无 stem 可解析 ⇒ 跳过
            if t.startswith("."):
                continue
            if any(c in t for c in "<>{}*$") or t.startswith(SKIP_PREFIXES):
                continue
            if pathlib.Path(t).name in INLINE_ALLOW:
                continue
            checked += 1
            if not ((f.parent / t).exists() or (REPO_ROOT / t).exists()
                    or pathlib.Path(t).name in names):
                bad.append((str(f.relative_to(REPO_ROOT)), t))
    return bad, checked


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 2
    targets = args or DEFAULT_TARGETS
    broken, checked = check(targets)
    bare_bad, bare_checked = check_bare_entry_refs()
    inline_bad, inline_checked = check_inline_refs()
    if broken or bare_bad or inline_bad:
        if broken:
            print(f"❌ 相对链接断链 {len(broken)} 处（共检查 {checked} 条）：", file=sys.stderr)
            for f, url in broken:
                print(f"   {f} → {url}", file=sys.stderr)
            print("   修法：修正路径；产物在 .gitignore 目录（如 outputs/）或已不存在的文档，"
                  "应降级为**无链接的陈述**（见 CHANGELOG 既有先例）。", file=sys.stderr)
        if inline_bad:
            print(f"❌ 活文档反引号内联引用不可解析 {len(inline_bad)} 处"
                  f"（共检查 {inline_checked} 条）：", file=sys.stderr)
            for f, tok in inline_bad:
                print(f"   {f} → {tok}", file=sys.stderr)
            print("   修法：改为仓库内真实存在的路径（含目录前缀）；确属运行时产物或有意提及"
                  "不存在的文件，加入本脚本 INLINE_ALLOW 并注明理由。", file=sys.stderr)
        if bare_bad:
            print(f"❌ 入口文档裸文件引用不可解析 {len(bare_bad)} 处"
                  f"（共检查 {bare_checked} 条）：", file=sys.stderr)
            for f, tok in bare_bad:
                print(f"   {f} → {tok}", file=sys.stderr)
            print("   修法：补全为仓库根相对路径（`references/...`）；确属运行时文件或有意提及"
                  "不存在的文件，加入本脚本 BARE_ALLOW 并注明理由。", file=sys.stderr)
        return 1
    print(f"✅ 相对链接全部可解析（共 {checked} 条，覆盖 {len(list(iter_files(targets)))} 个 md）"
          f"；入口文档裸引用全部可解析（共 {bare_checked} 条）"
          f"；活文档内联引用全部可解析（共 {inline_checked} 条）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
