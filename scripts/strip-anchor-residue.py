#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""净化包「编号锚点」残留清理（教训 #296 扩展：裸 #N 变体）

背景：strip-internal-leakage.sh 删掉「教训 #N」字面后，留下三类残留：
  1. 破损括号锚点：`（，+ #118）`、`（ + #173）`、`（M-Form-6，双格式升级 #292+#293）`
  2. 整行/表格锚点：`相关教训：#96（…）`、教训编号索引表、`- **教训编号**：#284（…）`
  3. 代码块内标签：`log("[#274] spawn …")`

铁律：只清「教训编号锚点」，不碰技能自身的内部编号与视觉元素：
  角色卡 #10 / 写手铁律 #16 / T8 必查项 #15-19 / G8 #1 / 回应实测 #7 /
  审查建议 #5 / 可发表性 #1-4 / ClawHub #89% finding / SVG 色值 `#2A2826`

用法：python3 scripts/strip-anchor-residue.py <净化包目录>
"""
import re
import sys
import pathlib

# ---- 保护 1：SVG/HTML 十六进制色值（属性形 + 裸色值）----
HEX_LONG = re.compile(r'#[0-9a-fA-F]{6}(?![0-9a-fA-F])|#[0-9a-fA-F]{8}(?![0-9a-fA-F])')
HEX_SHORT_COLOR = re.compile(r'#(?=[0-9a-fA-F]{3}(?![0-9a-fA-F]))(?=[0-9a-fA-F]*[a-fA-F])[0-9a-fA-F]{3}')

# ---- 保护 2：合法内部编号的左邻词 ----
LEGIT_WORD = (
    r'(?:实测|建议|审查|铁律|必查项|检查项|清单|角色卡|可发表性|图表|反馈|选项|条目|'
    r'G\d+|M-Form-\d|M-Exist-\d|M-Integrity-\d|Phase|Step|阶段)'
)
LEGIT_LEFT = re.compile(LEGIT_WORD + r'\s*$')
# 合法编号链：`角色卡 #10/#13-#16`、`T8 必查项 #15-19`、`可发表性 #1-4 + 图表 #5`
LEGIT_CHAIN = re.compile(
    LEGIT_WORD + r'(\s*#\d+(?:\.\d+)?(?:\s*[/&,、~+\-–—]\s*#\d+(?:\.\d+)?)*)'
)
PERCENT = re.compile(r'#\d+(?:\.\d+)?%')

# ---- 锚点 token ----
ANCHOR = re.compile(r'(?:教训\s*)?#\d+(?:\.\d+)?')
CONNECTOR_CHARS = '，,、+＋-—~～/·'

# ---- 括号内只剩锚点 / 占位符 → 整括号删除 ----
PAREN_ONLY_ANCHOR = re.compile(
    r'[（(]\s*(?:教训\s*)?(?:#\d+(?:\.\d+)?\s*(?:[，,、+＋/~～\-]\s*)?)+\s*[）)]'
)
PAREN_PLACEHOLDER = re.compile(r'[（(]\s*见相关算法\s*[）)]')
PAREN_LEAD_CONNECTOR = re.compile(r'[（(]\s*[，,、+＋]{1,3}\s*')

# ---- 行级处理 ----
LINE_REWRITE = [
    (re.compile(r'^相关教训[:：].*$'), '相关教训：[引用相关条目]'),
]
LINE_DROP = [
    re.compile(r'^[-*]\s*\*\*教训编号\*\*[:：]'),
]

# ---- 代码块内标签 ----
CODE_TAG_WITH_TEXT = re.compile(r'\[#\d+(?:\.\d+)?\s+([^\]]+)\]')
CODE_TAG_BARE = re.compile(r'\[#\d+(?:\.\d+)?\]')
CODE_LABEL = re.compile(r'(?<=[\[\(])#\d+(?:\.\d+)?\s+')

TIDY = [
    (re.compile(r'[（(]\s*[，,、+＋\s]*[）)]'), ''),
    (re.compile(r'[（(]\s*[）)]'), ''),
    (re.compile(r'[，,、+＋\s]+[）)]'), '）'),
    (re.compile(r'[（(][，,、+＋\s]+'), '（'),
    (re.compile(r'[，,]\s*。'), '。'),
    (re.compile(r'。\s*。+'), '。'),
    (re.compile(r'[ \t]{2,}'), ' '),
    (re.compile(r'\*\*\s*\*\*'), ''),
]

# ---- 无条件标点修补（旧轮次剥离留下的空括号 / 悬空冒号）----
# 注意：跳过正则字符组 `[^（）]`（M-Gate-Algorithm 的内联引用匹配式依赖它）
JUNK_TIDY = [
    (re.compile(r'(?<!\^)[（(][ \t]*[）)](?!\])'), ''),
    (re.compile(r'[（(][：:]+'), '（'),
    (re.compile(r'[：:]+[）)]'), '）'),
]


def strip_line(line: str) -> str:
    masks = []

    def _mask(m):
        masks.append(m.group(0))
        return f'\x00{len(masks) - 1}\x00'

    protected = line
    for pat in (HEX_LONG, HEX_SHORT_COLOR, PERCENT, LEGIT_CHAIN):
        protected = pat.sub(_mask, protected)

    before = protected
    protected = PAREN_ONLY_ANCHOR.sub('', protected)
    protected = PAREN_PLACEHOLDER.sub('', protected)
    protected = PAREN_LEAD_CONNECTOR.sub('（', protected)
    protected = CODE_TAG_WITH_TEXT.sub(r'[\1]', protected)
    protected = CODE_TAG_BARE.sub('[防御]', protected)
    protected = CODE_LABEL.sub('', protected)

    out, idx, touched = [], 0, protected != before
    while True:
        m = ANCHOR.search(protected, idx)
        if not m:
            out.append(protected[idx:])
            break
        if LEGIT_LEFT.search(protected[:m.start()]):
            out.append(protected[idx:m.end()])
            idx = m.end()
            continue
        start, end = m.start(), m.end()
        while start > 0 and protected[start - 1] in CONNECTOR_CHARS:
            start -= 1
        while end < len(protected) and protected[end] in CONNECTOR_CHARS:
            end += 1
        out.append(protected[idx:start])
        idx = end
        touched = True
    protected = ''.join(out)

    if touched:
        for pat, repl in TIDY:
            protected = pat.sub(repl, protected)
        # 锚点删除后留下的「汉字 + 空格 + 汉字」空档 → 收口（教训 #298）
        # 例外：`§ 二 组 A` 这类章号 + 序号 + 名称写法保留空格。
        def _cjk(m):
            if re.search(r'§\s*$', protected[:m.start()]):
                return m.group(0)
            return m.group(1) + m.group(2)
        protected = re.sub(r'([\u4e00-\u9fff])[ \t]+([\u4e00-\u9fff])', _cjk, protected)

    for pat, repl in JUNK_TIDY:
        protected = pat.sub(repl, protected)

    return re.sub(r'\x00(\d+)\x00', lambda m: masks[int(m.group(1))], protected)


# ---- 结构性处理（跨行）----
GLOSSARY_LESSON_SECTION = re.compile(r'^##\s*六、教训沉淀体系\s*$')
DEV_TOOL_SECTION = re.compile(r'^##\s*本地开发者工具')
LESSON_TABLE_HEADER = re.compile(r'^\|\s*教训\s*\|')
LESSON_TABLE_ROW = re.compile(
    r'^\|\s*#\d+(?:\s*[~\-/、+～—–]\s*#?\d+)*\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$'
)
LESSON_TABLE_TITLE = re.compile(r'^按教训编号')

GLOSSARY_REPLACEMENT = """## 六、经验沉淀体系

论衡的判据、角色卡铁律与失败模式清单来自实战复盘沉淀；发布包只保留可直接执行的规则与判据，内部记录不随包分发。
"""


def process_text(text: str) -> str:
    lines = text.split('\n')
    out, in_code, drop_section, lesson_table = [], False, None, False

    for line in lines:
        if line.strip().startswith('```'):
            in_code = not in_code
            out.append(line)
            continue

        if not in_code:
            # 段落级删除/替换
            if GLOSSARY_LESSON_SECTION.match(line):
                out.append(GLOSSARY_REPLACEMENT.rstrip('\n'))
                out.append('')
                drop_section = '## '
                continue
            if DEV_TOOL_SECTION.match(line):
                drop_section = '## '
                continue
            if drop_section and re.match(r'^#{1,2}\s', line):
                drop_section = None
            if drop_section:
                continue

            # 教训编号表：表头/分隔行删除，数据行转 bullet
            if LESSON_TABLE_TITLE.match(line):
                out.append('按出现频次（跨案例）：')
                continue
            if LESSON_TABLE_HEADER.match(line):
                lesson_table = True
                continue
            if lesson_table:
                if re.match(r'^\|[\s\-:|]+\|\s*$', line):
                    continue
                m = LESSON_TABLE_ROW.match(line)
                if m:
                    out.append(f'- {m.group(1)}（{m.group(2)}）')
                    continue
                lesson_table = False
        out.append(line)
    return '\n'.join(out)


def process(path: pathlib.Path) -> int:
    raw = path.read_text(encoding='utf-8')
    text = process_text(raw)
    lines = text.split('\n')
    res, changed = [], 0
    for line in lines:
        if line.strip().startswith('```'):
            res.append(line)
            continue
        if any(p.search(line) for p in LINE_DROP):
            changed += 1
            continue
        rewritten = None
        for pat, repl in LINE_REWRITE:
            if pat.search(line):
                rewritten = pat.sub(repl, line)
                break
        new = strip_line(rewritten if rewritten is not None else line)
        if new != line:
            changed += 1
        res.append(new)
    if changed or text != raw:
        path.write_text('\n'.join(res), encoding='utf-8')
    return changed


if __name__ == '__main__':
    root = pathlib.Path(sys.argv[1])
    total = 0
    for f in sorted(root.rglob('*.md')):
        n = process(f)
        if n:
            print(f'  {f.relative_to(root)}: {n} 行')
            total += n
    print(f'共修改 {total} 行')
