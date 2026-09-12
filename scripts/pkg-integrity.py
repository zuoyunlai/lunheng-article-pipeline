#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pkg-integrity.py — 净化包**正向**完整性校验（v2.12.30 新增，回应第三方审计 P1-1）

背景（fail-open）：
  整条净化链原本**只有负向检查** —— 「违规模式命中数 = 0」即通过。剥离规则一旦过度匹配
  （把正文/结构误删），残留扫描同样全绿 ⇒ 「净化成功、内容损坏」无法被发现。
  本脚本提供互补的**正向**校验：净化前快照，净化后比对，回答「有没有多删」。

用法：
  python3 scripts/pkg-integrity.py snapshot <pkg_dir> <snapshot.json>
  python3 scripts/pkg-integrity.py verify   <pkg_dir> <snapshot.json>

verify 的判定（任一不过即 exit 1）：
  1. 快照非空（防「空快照 = 全部通过」的空转门）
  2. 快照内每个文件仍存在
  3. 每个 md 文件非退化（≥ MIN_CHARS 字符，且仍含标题）
  4. 字符保留率 ≥ MIN_RETENTION（防整段塌陷）
  5. 必需结构锚点仍在（REQUIRED_ANCHORS，防关键段落被剥走）
  6. SKILL.md frontmatter 仍可解析且含 metadata.openclaw.version（防 frontmatter 被毁）
"""
import json
import pathlib
import re
import sys

MIN_CHARS = 200           # 单个 md 退化下限
DEFAULT_RETENTION = 0.35  # 字符保留率下限（净化会刻意删内容，不能定 1.0）
#   实测依据（v2.12.30 首跑，80 个 md）：最低 49%（可发表性判定表，含大量被剥 shell 段）
#   / 次低 77% / 80% → 取 35% 留足余量，只捕获「整段塌陷」级别的误删。

# 必需结构锚点：(包内相对路径, 必须出现的字面) —— 这些段落被剥走即代表「误删」
REQUIRED_ANCHORS = [
    ("SKILL.md", "name: lunheng-article-pipeline"),
    ("SKILL.md", "metadata:"),
    ("QUICKSTART.md", "lunheng-article-pipeline"),
    ("references/_shared/phase-order.yaml", "pipeline:"),
    ("references/_shared/字数判定表.md", "2000-3000"),
    ("references/gates/14-中文AI痕迹-gate.md", "G14"),
    ("references/agents/05-写作-writer.md", "T5"),
    ("references/agents/00-主控-coordinator.md", "T0"),
    ("references/templates/任务简报-template.md", "任务简报"),
    ("references/_shared/M-Gate-Algorithm.md", "M 门"),
]

HEADING_RE = re.compile(r'^#{1,6}\s+\S', re.MULTILINE)


def _md_files(root: pathlib.Path):
    return sorted(p for p in root.rglob("*.md") if p.is_file())


def snapshot(pkg_dir: str, out_path: str) -> int:
    root = pathlib.Path(pkg_dir)
    if not root.is_dir():
        print(f"ERR: 目录不存在 {root}", file=sys.stderr)
        return 1
    data = {"files": {}}
    for f in _md_files(root):
        text = f.read_text(encoding="utf-8", errors="replace")
        data["files"][str(f.relative_to(root))] = {
            "chars": len(text),
            "headings": len(HEADING_RE.findall(text)),
        }
    data["md_count"] = len(data["files"])
    pathlib.Path(out_path).write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  📸 基线快照：{data['md_count']} 个 md → {out_path}")
    return 0


def _check_frontmatter(root: pathlib.Path, errs: list):
    skill = root / "SKILL.md"
    if not skill.is_file():
        errs.append("SKILL.md 缺失")
        return
    text = skill.read_text(encoding="utf-8")
    if not text.startswith("---"):
        errs.append("SKILL.md 不以 frontmatter 开头（结构被毁）")
        return
    parts = text.split("---", 2)
    if len(parts) < 3 or not parts[1].strip():
        errs.append("SKILL.md frontmatter 为空或被截断")
        return
    try:
        import yaml
        fm = yaml.safe_load(parts[1]) or {}
    except Exception as e:  # noqa: BLE001
        errs.append(f"SKILL.md frontmatter 不可解析：{e}")
        return
    version = ((fm.get("metadata") or {}).get("openclaw") or {}).get("version")
    if not version:
        errs.append("SKILL.md frontmatter 缺 metadata.openclaw.version（层级被压平？教训 #335）")


def verify(pkg_dir: str, snap_path: str) -> int:
    root = pathlib.Path(pkg_dir)
    try:
        data = json.loads(pathlib.Path(snap_path).read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"❌ 快照不可读：{e}", file=sys.stderr)
        return 1

    before = data.get("files") or {}
    if not before:
        print("❌ 快照为空 —— 校验门空转（无基线可比），按失败处理", file=sys.stderr)
        return 1

    retention_floor = float(
        __import__("os").environ.get("PKG_MIN_RETENTION", DEFAULT_RETENTION))
    errs, ratios = [], []

    for rel, meta in sorted(before.items()):
        f = root / rel
        if not f.is_file():
            errs.append(f"{rel} 在净化后**消失**")
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        chars = len(text)
        if chars < MIN_CHARS:
            errs.append(f"{rel} 退化为 {chars} 字符（< {MIN_CHARS}）")
        # 标题检查必须与**基线**比：片段类文件（如 dispatch-header.md）本来就没有标题，
        # 一律要求「≥1 个标题」会误报（本门首跑即在此误报，已改基线相对判定）。
        if (meta.get("headings") or 0) > 0 and not HEADING_RE.search(text):
            errs.append(f"{rel} 基线有 {meta['headings']} 个标题，净化后已全部消失"
                        f"（结构被剥空）")
        b = meta.get("chars") or 0
        if b > 0:
            r = chars / b
            ratios.append((r, rel))
            if r < retention_floor:
                errs.append(
                    f"{rel} 字符保留率 {r:.0%} < {retention_floor:.0%}"
                    f"（{b} → {chars}）")

    for rel, marker in REQUIRED_ANCHORS:
        f = root / rel
        if not f.is_file():
            errs.append(f"必需锚点文件缺失：{rel}")
            continue
        if marker not in f.read_text(encoding="utf-8", errors="replace"):
            errs.append(f"必需锚点丢失：{rel} 中已无 {marker!r}")

    _check_frontmatter(root, errs)

    ratios.sort()
    if ratios:
        print(f"  最低字符保留率：{', '.join(f'{r:.0%}·{n}' for r, n in ratios[:3])}")

    if errs:
        print(f"❌ 正向完整性校验未通过（{len(errs)} 项）：", file=sys.stderr)
        for e in errs:
            print(f"   - {e}", file=sys.stderr)
        return 1
    print(f"  ✅ 正向完整性通过（{len(before)} 个 md 全部存活，锚点齐全，frontmatter 可解析）")
    return 0


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in ("snapshot", "verify"):
        print(__doc__, file=sys.stderr)
        return 2
    return snapshot(sys.argv[2], sys.argv[3]) if sys.argv[1] == "snapshot" \
        else verify(sys.argv[2], sys.argv[3])


if __name__ == "__main__":
    sys.exit(main())
