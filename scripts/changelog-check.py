#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""论衡 changelog 一致性检查 / 回填（P2「changelog 完整化 CI 校验」）

背景：changelog 是「易腐历史」——发布动作在 GitHub Releases 做，仓库内没有单一真源，
       于是出现「有 tag 无 Release」（v2.11.0 / v2.11.1）与「README 表格停在旧版本」两类缺口，
       而两类缺口都**不会报错**，只是查不到（同型：教训 #254 索引腐烂）。

本脚本是 changelog 完整性的单一真源，四种模式：

  --check    离线校验（默认）：每个版本 tag 在 CHANGELOG.md 有对应章节；当前版本已记录
  --online   追加在线校验：每个版本 tag 在 GitHub 有对应 Release（需 gh CLI 已登录）
  --fill     从 GitHub Releases 回填 CHANGELOG.md 缺失章节（逐字保留 Release 正文；幂等，可安全重跑）
  --report   列出 Release 正文过短的章节（篇幅不均匀，供人工判断是否重写）

调用：python3 scripts/changelog-check.py [--check|--online|--fill|--report]
退出码：0 = 通过 / 1 = 存在缺口 / 2 = 环境不满足
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = SKILL_ROOT / "CHANGELOG.md"
SKILL_MD = SKILL_ROOT / "SKILL.md"

# 章节标题用方括号包裹版本号：Release 正文里也有「## v2.2.6 核心改进」这类同形行，
# 不加边界会让解析把正文小标题误当章节（回填/校验口径都会错位）。
VERSION_TAG_RE = re.compile(r"^v\d+(?:\.\d+)*$")
HEADING_RE = re.compile(r"^## \[(v\d+(?:\.\d+)*)\]", re.M)


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=SKILL_ROOT, **kw)


def current_version():
    """从 SKILL.md frontmatter 读取当前版本号（单一真源）。"""
    for line in SKILL_MD.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("version:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    print("❌ 无法从 SKILL.md frontmatter 读取版本号", file=sys.stderr)
    sys.exit(2)


def version_tags():
    """本地版本 tag（排除 before-batch1-optimization 这类工作 tag）。"""
    out = run(["git", "tag"]).stdout.split()
    return sorted({t for t in out if VERSION_TAG_RE.match(t)}, key=version_key)


def version_key(tag):
    parts = [int(x) for x in tag.lstrip("v").split(".")]
    return tuple(parts + [0] * (4 - len(parts)))


def changelog_versions():
    if not CHANGELOG.exists():
        return set()
    return set(HEADING_RE.findall(CHANGELOG.read_text(encoding="utf-8")))


def repo_slug():
    url = run(["git", "remote", "get-url", "origin"]).stdout.strip()
    m = re.search(r"github\.com[:/](?P<slug>[^/]+/[^/\s]+?)(?:\.git)?$", url)
    if not m:
        print(f"❌ 无法从 origin 解析 GitHub 仓库：{url}", file=sys.stderr)
        sys.exit(2)
    return m.group("slug")


def fetch_releases():
    """一次分页拉取全部 Release（避免逐 tag 打 API）。"""
    r = run(["gh", "api", f"/repos/{repo_slug()}/releases", "--paginate"])
    if r.returncode != 0:
        print(f"❌ gh api 拉取 Release 失败：{r.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return json.loads(r.stdout or "[]")


def section_for(release):
    """把一个 Release 转成 CHANGELOG 章节。

    返回 (章节文本, 是否自动闭合围栏)。个别 Release 正文的收尾围栏少写一个反引号
    （如 v2.10.3 用 `` 结尾），在本文件里会让其后**全部版本**渲染成代码块——
    与「表格分隔行失效」同型的不可见排版崩坏，因此在章节内补齐闭合围栏。
    """
    tag = release["tag_name"]
    date = (release.get("published_at") or "")[:10]
    name = (release.get("name") or "").strip()
    body = (release.get("body") or "").strip()

    lines = [f"## [{tag}] — {date}", ""]
    # Release 名称多数重复正文首行标题，仅在「名称 != tag」且正文未自带同名标题时补一行
    if name and name != tag and not body.startswith(f"## {tag}"):
        lines += [f"**{name}**", ""]
    body_lines = body.splitlines()
    # 剥掉正文自带的首行同名 H2（避免与章节标题重复），其余逐字保留
    if body_lines and body_lines[0].startswith(f"## {tag}"):
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        body_lines.pop(0)
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)

    auto_closed = False
    fence_count = sum(1 for l in body_lines if l.strip().startswith("```"))
    if fence_count % 2:
        body_lines += ["", "```"]
        auto_closed = True

    lines += body_lines
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n", auto_closed


def split_changelog(text):
    """切成 (头部块, [(version, 章节文本)])，章节按文件出现顺序。"""
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return text, []
    header = text[: matches[0].start()]
    sections = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((m.group(1), text[m.start():end]))
    return header, sections


def cmd_check(online):
    expected = current_version()
    tags = version_tags()
    documented = changelog_versions()

    if not CHANGELOG.exists():
        print("❌ 仓库内无 CHANGELOG.md（changelog 无单一真源）")
        return 1

    missing = [t for t in tags if t not in documented]
    print(f"📌 当前版本（SKILL.md）：v{expected}")
    print(f"📌 本地版本 tag：{len(tags)} 个；CHANGELOG 章节：{len(documented)} 个")
    print("")

    fail = 0
    if f"v{expected}" not in documented:
        print(f"❌ 当前版本 v{expected} 在 CHANGELOG.md 中无章节（发版漏记）")
        fail = 1
    if missing:
        print(f"❌ {len(missing)} 个版本 tag 在 CHANGELOG.md 中无章节：")
        for t in missing:
            print(f"   - {t}")
        print("   修复：python3 scripts/changelog-check.py --fill（从 GitHub Releases 回填）")
        fail = 1
    # 章节不得出现本地无 tag 的「幽灵版本」（拼写错误/手写臆造）
    ghost = sorted(documented - set(tags), key=version_key)
    if ghost:
        print(f"⚠️  CHANGELOG 有章节但本地无对应 tag（核对是否拼写错误）：{', '.join(ghost)}")

    # 围栏闭合性：某章节里 ``` 为奇数会让其后**全部版本**渲染成代码块（不可见排版崩坏）
    _, sections = split_changelog(CHANGELOG.read_text(encoding="utf-8"))
    unbalanced = [
        v for v, body in sections
        if sum(1 for l in body.splitlines() if l.strip().startswith("```")) % 2
    ]
    if unbalanced:
        print(f"❌ {len(unbalanced)} 个章节代码围栏未闭合（其后版本会渲染成代码块）：")
        for v in sorted(unbalanced, key=version_key):
            print(f"   - {v}")
        fail = 1

    if online:
        releases = fetch_releases()
        released = {r["tag_name"] for r in releases}
        no_release = [t for t in tags if t not in released]
        print("")
        print(f"🌐 GitHub Release：{len(released)} 个")
        if no_release:
            print(f"❌ {len(no_release)} 个版本 tag 在 GitHub 无 Release（changelog 会缺页）：")
            for t in no_release:
                print(f"   - {t}")
            fail = 1
        else:
            print("✅ 每个版本 tag 都有对应 GitHub Release")

    print("")
    print("✅ changelog 一致性检查通过" if not fail else "❌ changelog 一致性检查失败")
    return fail


def strip_section_separator(section):
    """剥掉章节尾部的 `---` 分隔行及其周围空行（--fill 幂等的关键）。

    `split_changelog()` 按 `^## [` 切章节，章节文本**天然包含紧跟其后的分隔行**
    （它落在本条章节与下一条 `## [` 之间）。若把它原样写回、又在后面补一条 `---`，
    则每次 --fill 都为每个章节累积一条分隔行——v2.12.17 实测：142 章节的提交态
    184 行 `---` → 跑一次 326 → 再跑 468（每次净增「章节数」行），既掩盖真实变更，
    也让 --fill 无法安全重跑（教训 #330）。故写回前先归一化尾部，分隔行由 cmd_fill 统一补。

    注意：`---` 之间有空行，故**不能**用相邻行重复判断，只能按行尾逐个剥离。
    """
    lines = section.splitlines()
    while lines and lines[-1].strip() in ("", "---"):
        lines.pop()
    return "\n".join(lines)


def render_changelog(header, sections):
    """把 (头部块, {版本: 章节文本}) 渲染成 CHANGELOG 全文（纯函数，便于回归测试）。

    幂等约束：输出里每个版本章节恰好带一条 `---` 分隔行——章节自带的尾部 `---`
    先由 strip_section_separator 剥掉，再由本函数统一补写，故 render(render(x)) == render(x)。
    """
    ordered = sorted(sections, key=version_key, reverse=True)
    out = [header.rstrip("\n"), ""]
    for v in ordered:
        out += [strip_section_separator(sections[v]), "", "---", ""]
    return "\n".join(out).rstrip("\n") + "\n"


def cmd_fill():
    releases = fetch_releases()
    released = {r["tag_name"]: r for r in releases}

    text = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else ""
    header, sections = split_changelog(text)
    known = {v: s for v, s in sections}
    added = []
    closed = []
    for tag, rel in released.items():
        if tag not in known and VERSION_TAG_RE.match(tag):
            text_new, auto_closed = section_for(rel)
            known[tag] = text_new
            added.append(tag)
            if auto_closed:
                closed.append(tag)

    # 非版本 tag 的 Release（如 full-repo-consistency-audit-…）不进 CHANGELOG
    CHANGELOG.write_text(render_changelog(header, known), encoding="utf-8")

    if added:
        print(f"✅ 回填 {len(added)} 个章节：{', '.join(sorted(added, key=version_key))}")
    else:
        print("✅ 无缺失章节（CHANGELOG.md 已与 GitHub Releases 一致）")
    if closed:
        print(f"⚠️  {len(closed)} 个章节的 Release 正文围栏未闭合，已在本文件补齐闭合围栏："
              f"{', '.join(sorted(closed, key=version_key))}")
    print(f"   共 {len(known)} 个版本章节 → {CHANGELOG.relative_to(SKILL_ROOT)}")
    return 0


def cmd_report():
    text = CHANGELOG.read_text(encoding="utf-8")
    _, sections = split_changelog(text)
    thin = []
    for v, body in sections:
        # 去掉标题行后的正文字符数
        payload = "\n".join(body.splitlines()[1:]).strip()
        thin.append((len(payload), v))
    thin.sort()
    print(f"📊 CHANGELOG 章节篇幅：{len(thin)} 个")
    print(f"   最短：{thin[0][0]} 字符（{thin[0][1]}）／最长：{thin[-1][0]} 字符（{thin[-1][1]}）")
    print("")
    print("正文 <300 字符的章节（GitHub 自动生成正文，内容偏薄）：")
    for n, v in thin:
        if n < 300:
            print(f"   - {v}: {n} 字符")
    return 0


def main():
    ap = argparse.ArgumentParser(description="论衡 changelog 一致性检查 / 回填")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="离线校验（默认）")
    g.add_argument("--online", action="store_true", help="离线校验 + GitHub Release 覆盖校验")
    g.add_argument("--fill", action="store_true", help="从 GitHub Releases 回填缺失章节")
    g.add_argument("--report", action="store_true", help="列出篇幅过短的章节")
    args = ap.parse_args()

    if args.fill:
        return cmd_fill()
    if args.report:
        return cmd_report()
    return cmd_check(online=args.online)


if __name__ == "__main__":
    sys.exit(main())
