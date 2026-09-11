#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalize-version-header.py — 文件头版本戳归一化（sync-version.sh 的幂等写入口）

背景（v2.12.20，教训 #331）：
  sync-version.sh 的 header 模式旧实现用
      sed -i "${CLOSE_LINE}a\\ ... \\ ..."
  追加版本戳行。sed 的 `a\\` 把「尾部续行」当成文本的一部分，等于多写一个空行；
  脚本末尾的 trim() 只裁剪多余的 `> 版本：` 行、**不管这些空行**，于是每次 sync 都在
  每个受管文件的版本戳行后多累积 1 个空行（实测 README.md：v2.12.10 = 0 个 →
  v2.12.19 = 9 个；教训索引 47 个）。属「不报错、只是变坏」的静默退化
  （同型：教训 #254 / #307 / #329 / #330）。

本模块把「文件头元数据块」的写入收敛为一次性归一化（幂等）：
  元数据行 = `> 版本：...`（版本戳）+ `> 🌐 **语言政策**...`（语言政策，若有）
  规范形态 = 元数据行之间、以及元数据块与正文之间**恰好 1 个空行**：

      [YAML frontmatter]
      > 版本：vX（自动同步 YYYY-MM-DD）
      <blank>
      [> 🌐 **语言政策**：...]
      <blank>
      正文

  写入前先剥净头部区域内已有的「版本戳行 + 其后的连续空行」再统一补写，故
  normalize(normalize(x)) == normalize(x)：连跑两次零 diff，且历史累积的空行一次收敛。

用法：
  python3 scripts/normalize-version-header.py --root <skill_root> \
      --version 2.12.20 --date 2026-09-11 [--update <abs_path> ...] [--dry-run|--check]

  --update   需要保证版本戳为 --version 的文件（其余含版本戳的文件只归一化、不改版本号）
  --dry-run  只报告不写入
  --check    只校验，存在需要归一化的文件即 exit 1
"""

import argparse
import datetime
import os
import sys

STAMP_PREFIX = "> 版本："
LANG_PREFIX = "> 🌐 **语言政策**"
STAMP_LOOKAHEAD = 6  # 版本戳允许偏离锚点多少行（frontmatter 关闭行之后 + 容错）
# 净化包产物与历史归档不参与归一化（与 sync-version.sh 旧 trim 的排除口径一致）
SKIP_DIRS = {".git", "outputs", "archive", "node_modules", "__pycache__", ".pytest_cache"}


def header_anchor(lines):
    """版本戳锚点：YAML frontmatter 关闭 `---` 之后；否则文件第 0 行。"""
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return i + 1
    return 0


def _stamp_index(lines, anchor):
    """头部区域内已有版本戳的行号（无则 None）。"""
    for i in range(anchor, min(anchor + STAMP_LOOKAHEAD, len(lines))):
        if lines[i].startswith(STAMP_PREFIX):
            return i
    return None


def has_stamp(lines):
    return _stamp_index(lines, header_anchor(lines)) is not None


def normalize_header(lines, stamp_line=None):
    """归一化文件头元数据块，返回 (新行列表, 是否变更)。

    stamp_line=None → 只归一化已存在的版本戳（不新增版本戳、不改版本号）；
    传入字符串 → 保证头部恰好一条该版本戳行（旧版本行一并收敛）。
    """
    anchor = header_anchor(lines)
    idx = _stamp_index(lines, anchor)
    if idx is None and stamp_line is None:
        return lines, False

    start = anchor if idx is None else idx

    # 头部区域 = 从版本戳开始，连续的「版本戳 / 语言政策 / 空行」
    stamps, langs = [], []
    end = start
    while end < len(lines):
        line = lines[end]
        if line.startswith(STAMP_PREFIX):
            stamps.append(line)
        elif line.startswith(LANG_PREFIX):
            langs.append(line)
        elif line.strip() == "":
            pass
        else:
            break
        end += 1

    if not stamps and stamp_line is None:
        return lines, False

    meta = [stamp_line if stamp_line is not None else stamps[0]] + langs
    block = []
    for i, line in enumerate(meta):
        if i:
            block.append("")
        block.append(line)

    new = lines[:start] + block + [""] + lines[end:]
    return new, new != lines


def iter_md_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if not name.endswith(".md") or ".bak." in name:
                continue
            yield os.path.join(dirpath, name)


def run(root, version, date, update_paths, dry_run=False, check=False, backup=True):
    stamp_line = None
    if version:
        stamp_line = f"{STAMP_PREFIX}v{version}（自动同步 {date}）"
    update = {os.path.realpath(p) for p in update_paths}
    stamp_ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    stamped, trimmed, removed, touched = [], [], 0, []
    for path in iter_md_files(root):
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        lines = text.split("\n")
        want = stamp_line if os.path.realpath(path) in update else None
        if want is None and not has_stamp(lines):
            continue
        new_lines, changed = normalize_header(lines, want)
        if not changed:
            continue
        rel = os.path.relpath(path, root)
        touched.append(rel)
        if want is not None and _stamp_index(lines, header_anchor(lines)) is not None:
            stamped.append(rel)
        elif want is not None:
            stamped.append(rel)
        else:
            trimmed.append(rel)
        removed += len(lines) - len(new_lines)
        if check or dry_run:
            continue
        if backup:
            with open(path, "rb") as fh:
                blob = fh.read()
            with open(f"{path}.bak.{stamp_ts}", "wb") as fh:
                fh.write(blob)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(new_lines))

    for rel in stamped:
        print(f"  ✅ 版本戳 v{version}：{rel}")
    for rel in trimmed:
        print(f"  ✂️  空行/旧版本行收敛：{rel}")

    if check:
        if touched:
            print(f"❌ 文件头未归一化 {len(touched)} 个文件（跑 sync-version.sh 修正）")
            return 1
        print("✅ 文件头元数据块全部为规范形态（版本戳 / 语言政策 / 正文各隔 1 空行）")
        return 0
    if dry_run:
        print(f"（DRY-RUN）待归一化 {len(touched)} 个文件，未写入")
        return 0
    print(f"✅ 文件头归一化：{len(touched)} 个文件（版本戳更新 {len(stamped)} / "
          f"收敛 {len(trimmed)}，共 -{removed} 行）")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="文件头版本戳归一化（幂等）")
    ap.add_argument("--root", required=True, help="skill 根目录")
    ap.add_argument("--version", default=None, help="要写入的版本号（不带 v）")
    ap.add_argument("--date", default=datetime.date.today().isoformat(),
                    help="版本戳日期 YYYY-MM-DD（默认今天）")
    ap.add_argument("--update", nargs="*", default=[],
                    help="需要保证版本戳为 --version 的文件（绝对路径）")
    ap.add_argument("--dry-run", action="store_true", help="只报告不写入")
    ap.add_argument("--check", action="store_true", help="只校验，需归一化即 exit 1")
    ap.add_argument("--no-backup", action="store_true", help="不写 .bak 备份")
    args = ap.parse_args(argv)

    if args.version and not args.date:
        print("❌ 指定 --version 时必须给出 --date", file=sys.stderr)
        return 2
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"❌ --root 不是目录：{root}", file=sys.stderr)
        return 2

    return run(root, args.version, args.date, [p for p in args.update if p],
               dry_run=args.dry_run, check=args.check, backup=not args.no_backup)


if __name__ == "__main__":
    sys.exit(main())
