#!/usr/bin/env bash
# 一次性清理：剥除净化包内所有主控侧运维痕迹（教训 #N / 主真源 / 论衡开发版）
# 教训 #296：教训对技能用户无意义——行内"教训 #N"必须从净化包剥光
#
# 用法：bash scripts/strip-internal-leakage.sh <净化包目录>

set -euo pipefail

# 默认 = 最新版本目录（独立复查指出：原默认字面量 `latest` 不存在 ⇒ 默认调用必报 not found）
_OCR="${OUTPUTS_ROOT:-$HOME/lunheng-build/lunheng-outputs}/clawhub-release"
_LATEST_V=$(ls -1 "$_OCR" 2>/dev/null | grep -E '^[0-9]+(\.[0-9]+){2}$' | sort -V | tail -1)
PKG_DIR="${1:-${_LATEST_V:+$_OCR/$_LATEST_V}}"
PKG_DIR="${PKG_DIR:-$_OCR/latest}"

if [ ! -d "$PKG_DIR" ]; then
  echo "ERROR: pkg dir not found: $PKG_DIR"
  exit 1
fi

echo "=== Stripping internal leakage: $PKG_DIR ==="

# ---------- 1. Count ----------
COUNT_LESSON=$( { grep -rE "教训 #" "$PKG_DIR" 2>/dev/null || true; } | wc -l)
COUNT_FILE=$( { grep -rE "audit-lessons\.md|lessons\.md" "$PKG_DIR" 2>/dev/null || true; } | wc -l)
COUNT_DEV=$( { grep -rE "论衡开发版|github\.com/zuoyunlai/lunheng" "$PKG_DIR" 2>/dev/null || true; } | wc -l)
COUNT_PATH=$( { grep -rE "/home/zuoyunlai/" "$PKG_DIR" 2>/dev/null || true; } | wc -l)

echo ""
echo "  Pre-cleanup counts:"
echo "    教训 #N 引用:                $COUNT_LESSON"
echo "    audit-lessons/lessons 文件名: $COUNT_FILE"
echo "    论衡开发版/GitHub 真源:      $COUNT_DEV"
echo "    /home/zuoyunlai/ 路径:       $COUNT_PATH"

# ---------- 2. Process all md files ----------
echo ""
echo "Processing .md files..."

mapfile -t MD_FILES < <(find "$PKG_DIR" -type f -name "*.md")

for f in "${MD_FILES[@]}"; do
python3 - "$f" <<'PYEOF'
import re, sys

path = sys.argv[1]
with open(path, encoding='utf-8') as fh:
    content = fh.read()

orig = content

# ===== 阶段 1: 处理整段（行级 / 块级）=====
# 必须先处理整段，否则行内删除可能留下空 bullet

def collapse_cjk_space(line):
    """删除 token 后留下「汉字 + 空格 + 汉字」的空档——中文之间不留空格。

    例外：`§ 二 组 A` 这类「章号 + 序号 + 名称」全库统一写法，
    前一字是 `§` 后的序号时保留空格（不被本条误收）。
    """
    def rep(m):
        if re.search(r'§\s*$', line[:m.start()]):
            return m.group(0)
        return m.group(1) + m.group(2)
    return re.sub(r'([\u4e00-\u9fff])[ \t]+([\u4e00-\u9fff])', rep, line)


lines = content.split('\n')
new_lines = []
in_code = False

# 形态 X1: 整行「- **教训 #N**：说明」—— 去掉前缀，保留说明
# 形态 X2: 整行「## 标题（..., 教训 #N/N/M）」
# 形态 X3: 整行「**教训 #N** 引用：主真源在...」（泛指术语条目）

def process_line(line):
    # 表格行特殊处理
    is_table = line.lstrip().startswith('|') and line.rstrip().endswith('|')
    if is_table:
        # 表格内只删「教训 #N」具体编号，保留其他
        new = re.sub(r'\*\*?教训 #\d+(?:\.\d+)?\*\*?', '', line)
        new = re.sub(r'（\s*）', '', new)
        new = re.sub(r'（([^（）]*?)）', lambda m: '（' + m.group(1).strip(' ，,') + '）' if m.group(1).strip(' ，,') else '', new)
        new = re.sub(r'\| +\|', '|', new)
        return new.rstrip()
    return line

for line in lines:
    line_orig = line
    if line.strip().startswith('```'):
        # 代码块标记本身保留，但块内的"教训 #N"仍要清理
        in_code = not in_code
        new_lines.append(line)
        continue
    if in_code:
        # 代码块内也要清理"教训 #N"等内部泄漏引用
        # （dispatch 派发文件 / M 门伪代码块的整体正文都在围栏内，教训 #298）
        line = re.sub(r'教训 #\d+(?:\.\d+)?', '', line)
        line = re.sub(r'教训 #N', '', line)
        line = re.sub(r'\[[^\]]*?\d{4}-\d{2}-\d{2}[^\]]*?\]', '', line)
        line = re.sub(r'audit-lessons\.md|lessons\.md', '实战经验记录.md', line)
        line = re.sub(r'论衡开发版|github\.com/zuoyunlai/lunheng', '', line)
        # 与正文同源的收口规则（空格残迹 / 内部产物名）
        line = re.sub(r'（[ \t]+(?=\S)', '（', line)
        line = re.sub(r'[ \t]+）', '）', line)
        line = line.replace('教训索引', '编号索引')
        if line != line_orig:
            line = collapse_cjk_space(line)
        new_lines.append(line)
        continue

    stripped = line.strip()

    # ----- 整行删除形态 -----

    # 形态 X3-a: 整行 bullet `**教训 #N** 引用：主真源在 ...` （泛指术语条目）
    if re.match(r'^\s*[-*]\s*\*\*?教训 #N\*\*?\s*引用', line):
        # 整行删除
        continue

    # 形态 X3-b: 整行 bullet「**教训 #N+1 编号不可回收**」
    if re.match(r'^\s*[-*]\s*\*\*?教训 #\w+\+\w+\s*\d*\**?', line):
        continue

    # 形态 X3-c: 整行 bullet `- **教训 #N**：说明` 但内容无意义的，可以保留说明
    # 这里保留说明，仅清理前缀
    m = re.match(r'^(\s*[-*]\s*)\*\*?教训 #\d+(?:\.\d+)?\*\*?[:：]?\s*(.*)$', line)
    if m:
        prefix, rest = m.group(1), m.group(2)
        line = f"{prefix}{rest}"
        new_lines.append(line)
        continue

    # ----- 行内处理形态 -----
    line = process_line(line)

    # 形态 1: 标题中的 `（..., 教训 #N/#M/#K, ..., 教训 #N）` 清理
    line = re.sub(r'[，,、]\s*教训 #\d+(?:\.\d+)?(?:[/&+，,、 ]\s*#\d+(?:\.\d+)?)*\s*(?=[）)]|\)|$)', '', line)

    # 形态 2: `（**教训 #N**）` 全角括号 + 加粗
    line = re.sub(r'（\s*\*\*?教训 #\d+(?:\.\d+)?\*\*?\s*）', '（见相关算法）', line)
    line = re.sub(r'（\s*教训 #\d+(?:\.\d+)?\s*）', '（见相关算法）', line)

    # 形态 3a: `**教训 #N：详细说明**` 加粗完整段（行内有 ** 配对）
    line = re.sub(r'\*\*教训 #\d+(?:\.\d+)?[：:][^*\n]{0,800}?\*\*', '', line)
    # 形态 3d: `**教训 #N**：详细说明` 加粗起+不配对（教训后紧贴 **）
    line = re.sub(r'\*\*教训 #\d+(?:\.\d+)?\*\*[：:][^*\n]{0,800}?(?=\n|。|$)', '', line)
    # 形态 3e: `**教训 #N**：（仅剩空加粗或简单字符）` 短残留
    line = re.sub(r'\*\*教训 #\d+(?:\.\d+)?\*\*', '', line)
    # 形态 3b: `教训 #N：详细说明` 无 ** 结尾（删到句号 / 行末 / **）
    line = re.sub(r'(?<![a-zA-Z0-9_])教训 #\d+(?:\.\d+)?[：:][^*\n]{0,800}?(?=\n|。|$)', '', line)
    # 形态 3c: `, 教训 #N）` 后跟右括号
    line = re.sub(r'[，,；;]\s*教训 #\d+(?:\.\d+)?\s*(?=[）)\]]|$)', '', line)
    # 形态 3f: `教训 #N**）` 编号后紧跟加粗结束 + 括号
    line = re.sub(r'教训 #\d+(?:\.\d+)?\*\*\s*[）)]', '）', line)
    line = re.sub(r'教训 #\d+(?:\.\d+)?\*\*', '', line)

    # 形态 4: `教训 #N——说明` 破折号延续
    line = re.sub(r'教训 #\d+(?:\.\d+)?——[^，,。.;;；\n）)』」』\]】]*', '', line)
    line = re.sub(r'教训 #\d+(?:\.\d+)?——\s*[^，。.;;；\n]*?(?=[，。.;;；\n）)』」』\]】]|$)', '', line)

    # 形态 5: `教训 #N「name」` 命名引用
    line = re.sub(r'教训 #\d+(?:\.\d+)?「[^」]*」', '', line)

    # 形态 6: 方括号内日期 + 教训 `[..., 2026-08-13 教训 #34]`
    # 形态 6a: 整段删除（无其他内容）
    line = re.sub(r'\[[^\]]*?教训 #\d+(?:\.\d+)?[^\]]*?\]', '', line)
    # 形态 6b: 段中 `[前缀 教训 #N 后缀]` 保留前缀
    line = re.sub(r'\[([^\]]*?)教训 #\d+(?:\.\d+)?([^\]]*?)\]',
                  lambda m: ('[' + (m.group(1) + m.group(2)).strip(' ·，, ') + ']')
                            if (m.group(1).strip(' ·，, ') or m.group(2).strip(' ·，, '))
                            else '', line)
    # 形态 6c: 方括号清理后只剩日期/编号元数据（如 `[xxx · 2026-08-13 ]`），整段删除
    line = re.sub(r'\[[^\]]*?\d{4}-\d{2}-\d{2}[^\]]*?\]', '', line)
    # v2.12.23（教训 #335 同族）：YAML 值位置的空数组 `key: []` 是**有效结构**（空集合），
    #   不是「清理残迹」——本规则会把它删成 `key:`（null）。实测受害者：
    #   `metadata.openclaw.requires.bins: []` → `bins:`。故对「纯 `key: []` 行」豁免。
    #   注：单跑本脚本用「文件」当参数是空转（它只接目录），排查时必须让它在目录上跑，
    #   否则会得出「本脚本无问题」的错误结论（本次就为此绕了一圈）。
    if not re.match(r'^\s*[A-Za-z_.-]+:\s*\[\s*\]\s*$', line):
        line = re.sub(r'\[\s*[·・，,]?\s*\]', '', line)

    # 形态 7: 裸 #N 编号（教训引用上下文中）
    line = re.sub(r'漏检 #\d+(?:\.\d+)?', '漏检若干教训', line)
    line = re.sub(r'#\d+(?:\.\d+)?（只扫', '（只扫', line)

    # 形态 8: `教训 #N+M` 占位符
    line = re.sub(r'教训 #\w+\+\s*\w+', '新增条目', line)
    line = re.sub(r'教训 #\d+(?:\.\d+)?\s*\+\s*\d+', '新增条目', line)

    # 形态 9: 行内 `教训 #N/N/M/N` 多编号
    line = re.sub(r'教训 #\d+(?:\.\d+)?(?:[/&+]\s*#\d+(?:\.\d+)?)+', '', line)

    # 形态 10: 「v2.5.5 教训 #170 ...」版本号后的引用
    line = re.sub(r'(v\d+\.\d+\.?\d*)\s+教训 #\d+(?:\.\d+)?', r'\1', line)

    # 形态 11: 「是教训 #127「...」的...」型（行中）
    line = re.sub(r'是\s*教训 #\d+(?:\.\d+)?「[^」]*」\s*的', '的', line)
    line = re.sub(r'是\s*教训 #\d+(?:\.\d+)?', '', line)

    # 形态 12: 「教训 #N」泛指术语（用于「教训 #N 字面」「教训 #N 引用」等）
    # 用户铁律：教训对技能用户无意义，必须彻底剥除
    line = re.sub(r'[「『"\']([^」』"\']*?)教训 #N([^」』"\']*?)[」』"\']',
                  lambda m: '「' + (m.group(1) + m.group(2)).strip(' ，,') + '」'
                            if (m.group(1).strip(' ，,') or m.group(2).strip(' ，,'))
                            else '', line)
    line = re.sub(r'教训 #N\s*字面', '条目', line)
    line = re.sub(r'教训 #N\s*引用', '条目引用', line)
    line = re.sub(r'教训 #N', '', line)  # 兜底：所有残留

    # ===== 阶段 3: 残留孤立清理 =====
    # 残留 `..., 教训 #N`（行中无具体语境）
    line = re.sub(r'[，,；;]\s*教训 #\d+(?:\.\d+)?(?=[，。、.！!？?\s\n）)]|$)', '', line)
    line = re.sub(r'教训 #\d+(?:\.\d+)?(?=[，。、.！!？?\s\n）)]|$)', '', line)
    # 残留 `教训 #N` 泛指（孤悬）
    line = re.sub(r'\s+教训 #\d+(?:\.\d+)?\s+', ' ', line)
    line = re.sub(r'教训 #\d+(?:\.\d+)?\s+', '', line)

    # ===== 阶段 4: 文件名引用清理 =====
    line = line.replace('audit-lessons.md', '实战经验记录.md')
    line = line.replace('lessons.md', '实战经验记录.md')

    # ===== 阶段 5: 论衡开发版 / GitHub 真源清理 =====
    line = re.sub(r'；跨项目教训沉淀仅存在于论衡开发版（含跨项目 lessons 同步机制），见 GitHub 仓库：https://github\.com/zuoyunlai/lunheng-article-pipeline', '', line)
    line = re.sub(r'论衡开发版（含跨项目 lessons 同步机制）', '', line)
    line = re.sub(r'> - 论衡完整设计（含自我维护机制）见 GitHub 仓库：https://github\.com/zuoyunlai/lunheng-article-pipeline\n?', '', line)

    # ===== 阶段 6: 主真源路径清理 =====
    line = re.sub(r'/home/zuoyunlai/\.openclaw/workspace/[^\s`）)]*', '<用户工作区>', line)
    line = re.sub(r'/home/zuoyunlai/[^\s`）)]*', '<用户路径>', line)

    # ===== 阶段 7: 清理空标点 / 多余空格 =====
    line = re.sub(r'[，,；;]+\s*[）)]', '）', line)
    line = re.sub(r'[，,；;]+\s*。', '。', line)
    line = re.sub(r'^[ \t]*[。，,；;]+\s*$', '', line)
    line = re.sub(r'\[\s+]', '[]', line)  # 空方括号里的多余空格
    # v2.12.23（教训 #335 同族）：YAML 值位置的空数组 `key: []` 是**有效结构**（含义＝空集合），
    #   不是「清理残迹」——旧规则一律删除，把 `metadata.openclaw.requires.bins: []` 变成
    #   `bins:`（null）。故对「纯 `key: []` 行」豁免。
    if not re.match(r'^\s*[A-Za-z_.-]+:\s*\[\s*\]\s*$', line):
        line = re.sub(r'\[\s*\]', '', line)   # 完全空的方括号
    line = re.sub(r'。。+', '。', line)   # 双重句号
    # v2.12.23（教训 #335）：只塌缩**句中**的连续空格，保留行首缩进。
    #   旧实现 `re.sub(r'  +', ' ', line)` 不区分行首缩进与句中空格，把 frontmatter 的
    #   2/4/6 层缩进一律压成 1 个空格 → YAML 层级被摧毁（metadata.openclaw 变 null，
    #   version/requires/tools 全被拉成 metadata 的直接子项）。
    #   代码围栏内的内容被掩码保护所以幸免——差异只在「在不在围栏里」。
    line = re.sub(r'(?<=\S)  +', ' ', line)

    # ===== 阶段 7b: 剥离副作用收口（教训 #298）=====
    # 7b-1 加粗标记后被剥出空格：`> ** 根因**：` → `> **根因**：`
    #      仅限「开标记」（前面是空白/行首/括号）——`>` 不入类，否则会误吞
    #      闭标记后的正常空格（`<reject>** |` → `<reject>**|`）
    line = re.sub(r'(^|[\s（(【「『])\*\*[ \t]+(?=\S)', r'\1**', line)
    # 7b-2 括号内被剥出孤立空格：`（ 实战）` → `（实战）`、`（opt_in ）` → `（opt_in）`
    line = re.sub(r'（[ \t]+(?=\S)', '（', line)
    line = re.sub(r'[ \t]+）', '）', line)
    # 7b-3 内部产物名 → 使用者视图用词
    line = line.replace('教训索引', '编号索引')
    # 7b-4 本次确实改动过本行 → 收口汉字间空格（教训 #298）
    if line != line_orig:
        line = collapse_cjk_space(line)

    new_lines.append(line)

content = '\n'.join(new_lines)

# ===== 阶段 8: 全局多行清理（跨行残留）=====
# `（..., 教训 #N\n  ...）` 跨行
content = re.sub(r'（[^\n）]*?教训 #\d+(?:\.\d+)?[^\n）]*?）', lambda m: '（' + re.sub(r'教训 #\d+(?:\.\d+)?', '', m.group(0)[1:-1]).strip() + '）' if re.sub(r'教训 #\d+(?:\.\d+)?', '', m.group(0)[1:-1]).strip() else '', content, flags=re.DOTALL)

# `> ** 根因**：` 整段保留，但里面的 `教训 #N` 字面 + 描述都清掉
# `教训 #N 引用：主真源在 ...` 的整 bullet 已经处理；剩余 `教训 #N` 泛指作为术语已删

# 清理连续的换行
content = re.sub(r'\n\n\n+', '\n\n', content)

if content != orig:
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(content)
    print(f"  EDITED: {path}")
PYEOF
done

echo ""
echo "=== Re-scan residual ==="
RESIDUAL_LESSON=$( { grep -rE "教训 #" "$PKG_DIR" 2>/dev/null || true; } | wc -l)
RESIDUAL_FILE=$( { grep -rE "audit-lessons\.md|lessons\.md" "$PKG_DIR" 2>/dev/null || true; } | wc -l)
RESIDUAL_DEV=$( { grep -rE "论衡开发版|github\.com/zuoyunlai/lunheng" "$PKG_DIR" 2>/dev/null || true; } | wc -l)
RESIDUAL_PATH=$( { grep -rE "/home/zuoyunlai/" "$PKG_DIR" 2>/dev/null || true; } | wc -l)
echo "  Residual 教训 #N:               ${RESIDUAL_LESSON:-0}"
echo "  Residual 文件名 lessons/audit:  ${RESIDUAL_FILE:-0}"
echo "  Residual 论衡开发版/GitHub:     ${RESIDUAL_DEV:-0}"
echo "  Residual /home/zuoyunlai/ 路径:  ${RESIDUAL_PATH:-0}"

TOTAL=$((RESIDUAL_LESSON + RESIDUAL_FILE + RESIDUAL_DEV + RESIDUAL_PATH))

if [ "$TOTAL" -gt 0 ]; then
  echo ""
  echo "WARNING: residual leaks found (showing first 30):"
  grep -rEn "教训 #|audit-lessons\.md|lessons\.md|论衡开发版|github\.com/zuoyunlai/lunheng|/home/zuoyunlai/" "$PKG_DIR" 2>/dev/null | head -30
  exit 1
fi

echo ""
echo "OK: all internal leakage stripped from $PKG_DIR"