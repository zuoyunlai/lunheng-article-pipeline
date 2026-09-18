#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen-scripts-index.py — 从各脚本头部注释生成 scripts/README.md 索引（纯派生视图）

为什么要有它：
  `scripts/` 是构建期 / 发版期工具链，此前**全仓没有任何索引**：想知道某个脚本是干什么的、
  怎么调、挂在哪个 make 目标上，只能逐个打开文件读头部注释（本目录 26 个文件，含 .sh/.py/.yaml）。
  本脚本把「脚本头部注释 + Makefile 入口」机械提取成一张表，写入 `scripts/README.md`。

铁律（一条款一真源）：
  1. **脚本用途 / 用法的真源 = 脚本头部注释**；`scripts/README.md` 只是派生视图，不承载新口径。
     口径要改就改脚本头，然后重跑本脚本（`make scripts-index`）。
  2. 索引**不搬运内部教训锚点**（`教训 #N` 与括号内的裸 `#N`）——门 H 会扫 `scripts/` 目录做
     教训编号差集，锚点跟着索引走会把「派生视图」变成第二份编号真源。
  3. 索引**不含时间戳 / 版本号 / 笔数以外的环境信息**：同一份 `scripts/` + `Makefile` 恒产出
     同一份文本，否则「漂移即红」的锁会退化成噪声（比较型断言必须有确定性）。
  4. 条目集合 = `scripts/` 下**除索引自身以外**的全部普通文件（跳过隐藏文件与 `__pycache__`）；
     `tests/test_scripts_index.py` 锁死双向一致：新增脚本未进索引 = 红，索引残留已删脚本 = 红。

用法：
  python3 scripts/gen-scripts-index.py
  python3 scripts/gen-scripts-index.py --check     # 只校验，漂移即 exit 1（供门 / CI 用）
  python3 scripts/gen-scripts-index.py --stdout    # 打印到 stdout，不写盘
  python3 scripts/gen-scripts-index.py --root DIR  # 指定仓库根（测试用；默认 = 本脚本的上上级）
退出码：0 = 已生成或已一致 / 1 = --check 发现漂移 / 2 = 用法错误
"""

import argparse
import re
import sys
from pathlib import Path

INDEX_BASENAME = "README.md"
SEPARATOR_RE = re.compile(r'^[=\-]{3,}$')
LESSON_ANCHOR_RE = re.compile(r'教训\s*#\d+(?:\.\d+)*')
# 括号内含内部溯源标记（教训 / 审计 / 回应 / 裸 #N）的整段删除：索引只要「这个脚本干什么」
AUDIT_PAREN_RE = re.compile(r'（[^（）]*(?:教训|审计|Remediation|回应|#\d)[^（）]*）')
# 纯版本沿革括号（`（v2.12.30 新增；v2.12.40 扩）`）—— 属脚本头部纪实，不是用途
VERSION_HISTORY_PAREN_RE = re.compile(r'（v?\d[\d.]*[^（）]*?(?:新增|扩|修订|改|更新|补)[^（）]*?）')
BARE_ANCHOR_RE = re.compile(r'#\d+')
USAGE_RE = re.compile(r'^(用法|调用|使用|命令)\s*[：:]')
# 「执行时机」：脚本头部用 `触发：` 声明何时该跑（无用法行的脚本靠它进索引）
TRIGGER_RE = re.compile(r'^(触发|何时|执行时[机刻]|入口)\s*[：:]')
NO_PURPOSE = "（头部无用途注释）"
NO_USAGE = "—"
MAX_CELL = 120


# --------------------------------------------------------------------------
# 头部注释提取（.py 取模块 docstring，其余取文件头连续注释块）
# --------------------------------------------------------------------------

def _strip_comment(line):
    s = line.strip()
    if s.startswith("#"):
        s = s[1:]
    return s.strip()


def _comment_block(text):
    """文件头连续注释块（跳过 shebang；遇到第一个非注释行即停）。"""
    out, started = [], False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#!"):
            continue
        if s == "":
            if started:
                out.append("")
            continue
        if s.startswith("#"):
            started = True
            out.append(_strip_comment(line))
            continue
        break
    return out


def header_lines(path):
    """脚本头部注释行（保留空行，用于「用法」续行判定）"""
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".py":
        m = re.search(r'"""(.*?)"""', text, re.S)
        if m:
            return m.group(1).splitlines()
    return _comment_block(text)


# --------------------------------------------------------------------------
# 派生字段
# --------------------------------------------------------------------------

def scrub(text):
    """剥掉内部溯源痕迹（教训锚点 / 括号内审计溯源 / 版本沿革），返回单元格文本"""
    s = AUDIT_PAREN_RE.sub("", text)
    s = VERSION_HISTORY_PAREN_RE.sub("", s)
    s = LESSON_ANCHOR_RE.sub("", s)
    s = BARE_ANCHOR_RE.sub("", s)
    s = re.sub(r'\s{2,}', " ", s)
    # 只裁尾部空白与标点：括号成对，不裁（裁了会留下不配对的「（」）
    return s.strip(" \t，,、；;：:—－-")


def _cell(text):
    """markdown 表格单元格：竖线转义 + 长度封顶（完整口径在脚本头部）"""
    s = text.replace("|", "\\|").replace("\n", " ").strip()
    if len(s) > MAX_CELL:
        s = s[:MAX_CELL].rstrip() + "…"
    return s


def _content_lines(lines):
    return [ln.strip() for ln in lines
            if ln.strip() and not SEPARATOR_RE.match(ln.strip())]


def derive_purpose(lines):
    content = _content_lines(lines)
    if not content:
        return NO_PURPOSE
    return scrub(content[0]) or NO_PURPOSE


def _derived_line(lines, pattern):
    """取 `pattern` 开头的声明行；本行为空则取其后的首个内容行（例：`用法：` 后换行再给命令）"""
    clean = [ln.strip() for ln in lines]
    for i, line in enumerate(clean):
        m = pattern.match(line)
        if not m:
            continue
        tail = line[m.end():].strip()
        if not tail:
            for nxt in clean[i + 1:]:
                if nxt and not SEPARATOR_RE.match(nxt):
                    tail = nxt
                    break
        if tail:
            return scrub(tail) or None
    return None


def derive_usage(lines):
    return _derived_line(lines, USAGE_RE) or NO_USAGE


def derive_trigger(lines):
    return _derived_line(lines, TRIGGER_RE) or NO_USAGE


def make_targets(makefile):
    """{脚本文件名: [make 目标…]} —— 从 Makefile recipe 里的 `scripts/<name>` 反查"""
    mapping = {}
    if not makefile.is_file():
        return mapping
    current, buf = None, []

    def flush():
        if not current or not buf:
            return
        for m in re.finditer(r'scripts/([A-Za-z0-9_.\-]+)', "\n".join(buf)):
            mapping.setdefault(m.group(1), set()).add(current)

    for line in makefile.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r'^([A-Za-z0-9_.\-]+)\s*:(?!=)', line)
        if m:
            flush()
            current, buf = m.group(1), []
        elif line.startswith("\t") and current:
            buf.append(line)
    flush()
    return {k: sorted(v) for k, v in mapping.items()}


# --------------------------------------------------------------------------
# 条目集合 + 索引文本
# --------------------------------------------------------------------------

def indexed_files(scripts_dir):
    """应进索引的文件名（排序稳定）；索引自身与隐藏文件不入"""
    return sorted(p.name for p in Path(scripts_dir).iterdir()
                  if p.is_file() and not p.name.startswith(".") and p.name != INDEX_BASENAME)


def parse_indexed_names(text):
    """从索引文本反解「已登记脚本名」——行首链接 `[`name`](name)`"""
    return sorted({m.group(1) for m in re.finditer(r'^\|\s*\[`([^`]+)`\]', text, re.M)})


def build_index(scripts_dir, makefile):
    scripts_dir = Path(scripts_dir)
    targets = make_targets(Path(makefile))
    rows = []
    for name in indexed_files(scripts_dir):
        lines = header_lines(scripts_dir / name)
        mk = "、".join("`make %s`" % t for t in targets.get(name, [])) or "—"
        rows.append((name, derive_purpose(lines), derive_usage(lines),
                     derive_trigger(lines), mk))

    out = [
        "<!-- 自动生成，请勿手改：本文件由 scripts/gen-scripts-index.py 从各脚本头部注释 + Makefile 派生。",
        "     脚本用途的真源 = 各脚本头部注释；刷新 = make scripts-index；漂移锁 = tests/test_scripts_index.py -->",
        "",
        "# scripts/ 脚本索引（自动生成）",
        "",
        "> 🔁 **派生视图**：本表由 `gen-scripts-index.py` 机械提取，**不承载新口径**。列源：**用途** = 脚本头部首个"
        "内容行；**用法** = 头部 `用法：` / `调用：` 行；**触发时机** = 头部 `触发：` 行；"
        "**make 入口** = `Makefile` recipe 中调用该脚本的目标。单元格里的「—」= 该脚本**未声明**该项"
        "（不是「不存在用法」；补口径请改脚本头，勿改本文件）。"
        "改了脚本头请跑 `make scripts-index` 刷新本文件；"
        "`tests/test_scripts_index.py` 会因本文件与 `scripts/` 不一致而报红（缺条目 / 残留已删条目 / 条目内容漂移）。",
        "> 📦 **本文件不进发布包**：`scripts/` 整目录由构建脚本排除，使用者侧不出现开发者工具链。",
        "",
        "共 **%d** 个条目（`scripts/` 下除本索引自身以外的全部文件）。" % len(rows),
        "",
        "| 脚本 | 用途 | 用法 | 触发时机（头部声明） | make 入口 |",
        "|---|---|---|---|---|",
    ]
    for name, purpose, usage, trigger, mk in rows:
        out.append("| [`%s`](%s) | %s | %s | %s | %s |"
                   % (name, name, _cell(purpose), _cell(usage), _cell(trigger), _cell(mk)))
    out.append("")
    return "\n".join(out)


def find_drift(scripts_dir, index_path):
    """返回漂移描述列表（空 = 双向一致）；--check 与本文件测试共用同一判据"""
    scripts_dir, index_path = Path(scripts_dir), Path(index_path)
    drift = []
    if not index_path.is_file():
        return ["索引文件不存在：%s（跑 make scripts-index 生成）" % index_path]
    on_disk = set(indexed_files(scripts_dir))
    listed = set(parse_indexed_names(index_path.read_text(encoding="utf-8", errors="replace")))
    for name in sorted(on_disk - listed):
        drift.append("新增脚本未进索引：%s" % name)
    for name in sorted(listed - on_disk):
        drift.append("索引含已删除脚本：%s" % name)
    return drift


# --------------------------------------------------------------------------

def main(argv):
    ap = argparse.ArgumentParser(add_help=True, description="生成 scripts/README.md 脚本索引")
    ap.add_argument("--root", default=None, help="仓库根（默认 = 本脚本的上级的上级）")
    ap.add_argument("--check", action="store_true", help="只校验，漂移即 exit 1")
    ap.add_argument("--stdout", action="store_true", help="打印到 stdout，不写盘")
    args = ap.parse_args(argv[1:])

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    scripts_dir = root / "scripts"
    index_path = scripts_dir / INDEX_BASENAME
    if not scripts_dir.is_dir():
        print("❌ scripts/ 目录不存在：%s" % scripts_dir, file=sys.stderr)
        return 2

    text = build_index(scripts_dir, root / "Makefile")
    drift = find_drift(scripts_dir, index_path)
    # 索引不存在时 current=None ⇒ stale_text=True（漏了这一步会把「不存在」当成「已最新」而静默不写）
    current = index_path.read_text(encoding="utf-8") if index_path.is_file() else None
    stale_text = current != text

    if args.check:
        if drift or stale_text:
            for d in drift:
                print("❌ %s" % d, file=sys.stderr)
            if stale_text:
                print("❌ 索引内容与脚本头部 / Makefile 漂移（跑 make scripts-index 刷新）",
                      file=sys.stderr)
            return 1
        print("✅ 脚本索引与 scripts/ 双向一致（%d 条）" % len(indexed_files(scripts_dir)))
        return 0

    if args.stdout:
        sys.stdout.write(text)
        return 0

    if not stale_text:
        print("✅ 脚本索引已是最新（%d 条）" % len(indexed_files(scripts_dir)))
        return 0
    index_path.write_text(text, encoding="utf-8")
    print("✅ 已生成 %s（%d 条）" % (index_path, len(indexed_files(scripts_dir))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
