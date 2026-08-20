#!/usr/bin/env bash
# 论衡版本号同步脚本（P1-3 版本号自动化 - 层 2）
#
# 用途：从 SKILL.md frontmatter 读取版本号，批量同步到所有应含版本号的文件
# 调用：./scripts/sync-version.sh [--dry-run]
# 选项：--dry-run  只显示将修改的内容，不实际写入
# 退出码：0 = 同步成功 / 1 = 同步失败

set -e

SKILL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_MD="$SKILL_ROOT/SKILL.md"
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
SYNCS=(
  # 核心文档（顶部插入版本号）
  "references/glossary.md|header"
  "references/pipeline-readme.md|header"
  "references/设计文档.md|header"

  # 共享协议（顶部插入版本号）
  "references/_shared/M-Gate-Algorithm.md|header"

  # 8 个角色卡（顶部插入版本号）
  "references/agents/00-主控-coordinator.md|header"
  "references/agents/01-文献检索-literature-scout.md|header"
  "references/agents/02-数据检索-data-scout.md|header"
  "references/agents/03-分析-analyst.md|header"
  "references/agents/04-写作-writer.md|header"
  "references/agents/05-审计-auditor.md|header"
  "references/agents/06-案例检索-case-scout.md|header"
  "references/agents/08-批判-critical-companion.md|header"
)

UPDATED=0
SKIPPED=0

echo "=== 版本号同步 ==="
for sync in "${SYNCS[@]}"; do
  IFS='|' read -r file mode <<< "$sync"
  full_path="$SKILL_ROOT/$file"

  if [ ! -f "$full_path" ]; then
    echo "⚠️  跳过：$file（文件不存在）"
    SKIPPED=$((SKIPPED+1))
    continue
  fi

  # 检查是否已包含当前版本号
  if grep -qE "v$EXPECTED" "$full_path"; then
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

      # 在文件顶部插入版本号注释
      sed -i "1i\\
> 版本：v$EXPECTED（自动同步 $(date +%Y-%m-%d)）\\
" "$full_path"

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
