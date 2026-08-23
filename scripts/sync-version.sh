#!/usr/bin/env bash
# 论衡版本号同步脚本（P1-3 版本号自动化 - 层 2）
#
# ⚠️ 三层联动防漏改（教训 #118.1）：
#   层 1 本脚本（check-version.sh）= 本地只读验证
#   层 2 sync-version.sh = 本地批量同步写入
#   层 3 .github/workflows/version-check.yml = CI 云端自动验证
#   改角色文件名（references/agents/0X-*.md 重命名）时，必须三处同步更新角色文件清单，
#   否则版本号自动化会扫错路径直接报错（v2.3.0 重构时 scripts/ 两层漏改，教训 #118.1）。

#
# 用途：从 SKILL.md frontmatter 读取版本号，批量同步到所有应含版本号的文件
# 调用：./scripts/sync-version.sh [--dry-run]
# 选项：--dry-run  只显示将修改的内容，不实际写入
# 退出码：0 = 同步成功 / 1 = 同步失败

set -e

SKILL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 自动检测目录结构：工作区（pipeline/）vs skill 副本（references/ + 根 SKILL.md）
if [ -d "$SKILL_ROOT/pipeline" ]; then
  CONTENT_DIR="$SKILL_ROOT/pipeline"
  SKILL_MD="$CONTENT_DIR/SKILL.md"
  ENTRY_DIR="$CONTENT_DIR"
elif [ -d "$SKILL_ROOT/references" ]; then
  CONTENT_DIR="$SKILL_ROOT/references"
  SKILL_MD="$SKILL_ROOT/SKILL.md"
  ENTRY_DIR="$SKILL_ROOT"
else
  echo "❌ 无法识别目录结构（找不到 pipeline/ 或 references/）"
  exit 1
fi
DRY_RUN=false

if [ "$1" == "--dry-run" ]; then
  DRY_RUN=true
  echo "🔍 DRY-RUN 模式：只显示将修改的内容，不实际写入"
  echo ""
fi

# 从 SKILL.md frontmatter 读取版本号（单一真源）
EXPECTED=$(grep -E '^version:' "$SKILL_MD" | head -1 | sed -E 's/version:[[:space:]]*//;s/["'"'"']//g;s/[[:space:]]*$//')

if [ -z "$EXPECTED" ]; then
  echo "❌ 无法从 SKILL.md 读取版本号"
  exit 1
fi

echo "📌 目标版本号（来自 SKILL.md frontmatter）：v$EXPECTED"
echo ""

# 定义需要同步版本号的文件列表
# 格式：文件路径|插入位置（header=文件顶部，replace=全文替换旧版本号）
# 路径规则：内容文件（glossary/agents 等）相对 CONTENT_DIR；入口文件（README/QUICKSTART）用 @ 前缀，相对 ENTRY_DIR
SYNCS=(
  # 核心文档（顶部插入版本号）
  "glossary.md|header"
  "pipeline-readme.md|header"
  "设计文档.md|header"
  "设计文档-架构.md|header"
  "设计文档-哲学.md|header"
  "deliverables.md|header"

  # 共享协议（顶部插入版本号）
  "_shared/M-Gate-Algorithm.md|header"
  "_shared/audit-checklist-quickref.md|header"

  # 8 个角色卡（顶部插入版本号）
  "agents/00-主控-coordinator.md|header"
  "agents/01-文献检索-literature-scout.md|header"
  "agents/02-数据检索-data-scout.md|header"
  "agents/03-案例检索-case-scout.md|header"
  "agents/04-分析-analyst.md|header"
  "agents/05-写作-writer.md|header"
  "agents/06-批判-critical-companion.md|header"
  "agents/07-审计-auditor.md|header"

  # 顶层文档（入口，v2.3.6 起纳入；@ = 相对 ENTRY_DIR）
  "@README.md|header"
  "@QUICKSTART.md|header"
)

UPDATED=0
SKIPPED=0

echo "=== 版本号同步 ==="
for sync in "${SYNCS[@]}"; do
  IFS='|' read -r file mode <<< "$sync"
  # 入口文件（@ 前缀）相对 ENTRY_DIR，内容文件相对 CONTENT_DIR
  if [[ "$file" == @* ]]; then
    file="${file#@}"
    full_path="$ENTRY_DIR/$file"
  else
    full_path="$CONTENT_DIR/$file"
  fi

  if [ ! -f "$full_path" ]; then
    echo "⚠️  跳过：$file（文件不存在）"
    SKIPPED=$((SKIPPED+1))
    continue
  fi

  # 检查是否已包含当前版本号
  if head -1 "$full_path" | grep -qE "v$EXPECTED"; then
    echo "⏭️  跳过：$file（已包含 v$EXPECTED）"
    SKIPPED=$((SKIPPED+1))
    continue
  fi

  if [ "$mode" == "header" ]; then
    # 在文件顶部插入版本号
    if [ "$DRY_RUN" == true ]; then
      echo "📝 将修改：$file（顶部插入 v$EXPECTED）"
    else
      # 备份原文件
      cp "$full_path" "$full_path.bak.$(date +%Y%m%d-%H%M%S)"

      # 检测文件是否为 YAML frontmatter（第 1 行是 `---`）
      # 若是，则在 frontmatter 关闭 `---` 之后插入（不破坏 frontmatter 结构）
      # 若否，则在第 1 行前插入（原行为）
      if head -1 "$full_path" | grep -qE "^---$"; then
        # 找第 2 个 `---`（frontmatter 关闭），在它后面插入
        # 使用 awk 找到第 2 个 `---` 的行号（从 1 开始）
        CLOSE_LINE=$(awk 'BEGIN{n=0} /^---$/{n++; if(n==2){print NR; exit}}' "$full_path")
        if [ -n "$CLOSE_LINE" ]; then
          # 在关闭 `---` 之后插入（行号 +1）
          sed -i "${CLOSE_LINE}a\\
> 版本：v$EXPECTED（自动同步 $(date +%Y-%m-%d)）\\
" "$full_path"
        else
          # 兜底：只找到一个 `---`，按第 1 行前插入
          sed -i "1i\\
> 版本：v$EXPECTED（自动同步 $(date +%Y-%m-%d)）\\
" "$full_path"
        fi
      else
        # 非 frontmatter 文件，按原逻辑在第 1 行前插入
        sed -i "1i\\
> 版本：v$EXPECTED（自动同步 $(date +%Y-%m-%d)）\\
" "$full_path"
      fi

      echo "✅ 更新：$file（顶部插入 v$EXPECTED）"
    fi
    UPDATED=$((UPDATED+1))
  elif [ "$mode" == "replace" ]; then
    # 全文替换旧版本号
    if [ "$DRY_RUN" == true ]; then
      echo "📝 将修改：$file（全文替换为 v$EXPECTED）"
    else
      # 备份原文件
      cp "$full_path" "$full_path.bak.$(date +%Y%m%d-%H%M%S)"

      # 替换所有 v2.2.x 为当前版本号
      sed -i -E "s/v2\.2\.[0-9]+/v$EXPECTED/g" "$full_path"

      echo "✅ 更新：$file（全文替换为 v$EXPECTED）"
    fi
    UPDATED=$((UPDATED+1))
  fi
done

echo ""
echo "✂️  版本栈精简（保留最近 5 个）"
if [ "$DRY_RUN" == true ]; then
  echo "（DRY-RUN 模式，未实际修改）"
else
  # 收集所有需要 trim 的文件路径（SKILL.md + 18 个 SYNCS 文件）
  TRIM_FILES="SKILL.md"
  for s in "${SYNCS[@]}"; do
    IFS='|' read -r f _ <<< "$s"
    if [[ "$f" == @* ]]; then
      TRIM_FILES="$TRIM_FILES ${f#@}"
    else
      TRIM_FILES="$TRIM_FILES $f"
    fi
  done
  TRIM_FILES="$TRIM_ROOT/$CONTENT_DIR/../SKILL.md $TRIM_FILES"
  # 实际文件在 CONTENT_DIR，SKILL.md 在 CONTENT_DIR/SKILL.md
  # 修正：直接在 cwd 下拼接（脚本运行 cwd = SKILL_ROOT）
  TRIM_PATHS=""
  for f in $TRIM_FILES; do
    if [[ "$f" == SKILL.md ]]; then
      TRIM_PATHS="$TRIM_PATHS SKILL.md"
    elif [[ "$f" == @* ]]; then
      TRIM_PATHS="$TRIM_PATHS ${f#@}"
    else
      TRIM_PATHS="$TRIM_PATHS $f"
    fi
  done
  python3 - "$TRIM_PATHS" <<'TRIMEOF'
import sys, os
files = sys.argv[1:]
def trim(path, keep=5):
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')
    version_idx = [i for i, line in enumerate(lines) if line.startswith('> 版本：')]
    if len(version_idx) <= keep:
        return 0
    keep_set = set(version_idx[:keep])
    remove_set = set(version_idx[keep:])
    out = []
    for i, line in enumerate(lines):
        if i in remove_set:
            continue
        if line.strip() == '' and (i-1) in remove_set:
            continue
        out.append(line)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    return len(remove_set)
trimmed = 0
for f in files:
    if os.path.isfile(f):
        n = trim(f, 5)
        if n > 0:
            print(f"  -{n} 行  {f}")
            trimmed += n
print(f"✅ 清理 {trimmed} 行旧版本记录（每文件保留最近 5 个）")
TRIMEOF
fi

echo ""
echo "📊 统计："
echo "  ✅ 更新：$UPDATED"
echo "  ⏭️  跳过：$SKIPPED"
echo ""

if [ "$DRY_RUN" == true ]; then
  echo "🔍 DRY-RUN 完成，未实际写入文件"
  echo "   如需实际同步，请执行：./scripts/sync-version.sh"
else
  echo "✅ 版本号同步完成（v$EXPECTED）"
  echo "   建议执行 ./scripts/check-version.sh 验证同步结果"
fi
