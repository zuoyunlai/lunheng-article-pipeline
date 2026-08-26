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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"  # v2.5.6 P0 修复：用于 self-audit-gate.sh 调用

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

# 清理上一批 .bak 备份（v2.5.11 补，回应第三方全量审计 P1-1）
# 每次 sync 前清掉旧备份，避免 .bak 无限堆积污染 grep 自查（教训 #118 系列重演）
# 保留「当轮 cp 备份」的回滚能力（git 已提供版本控制，cp 备份是额外保险）
if [ "$DRY_RUN" != true ]; then
  BAK_COUNT=$(find "$SKILL_ROOT" -name '*.bak.*' -not -path '*/.git/*' 2>/dev/null | wc -l | tr -d ' ')
  if [ "$BAK_COUNT" -gt 0 ]; then
    find "$SKILL_ROOT" -name '*.bak.*' -not -path '*/.git/*' -delete 2>/dev/null || true
    echo "🧹 清理旧 .bak 备份（$BAK_COUNT 个）"
    echo ""
  fi
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
  "case-studies.md|header"
  "operations.md|header"
  "errors.md|header"

  # 共享协议（顶部插入版本号）
  "_shared/M-Gate-Algorithm.md|header"
  "_shared/M-Gate-Algorithm-appendix.md|header"
  "_shared/audit-checklist-quickref.md|header"

  # 9 个角色卡（顶部插入版本号）
  "agents/00-主控-coordinator.md|header"
  "agents/01-文献检索-literature-scout.md|header"
  "agents/02-数据检索-data-scout.md|header"
  "agents/03-案例检索-case-scout.md|header"
  "agents/04-分析-analyst.md|header"
  "agents/05-写作-writer.md|header"
  "agents/06-批判-critical-companion.md|header"
  "agents/07-审计-auditor.md|header"
  "agents/09-审稿-peer-reviewer.md|header"

  # 主控扩展职责（v2.5.0 主控卡拆分后新增）
  "agents/00-主控-扩展职责.md|header"

  # 派发话术（v2.5.6 拆分新增，教训 #183 补入三层清单）
  "dispatch/T1-文献检索.md|header"
  "dispatch/T2-数据检索.md|header"
  "dispatch/T3-案例检索.md|header"
  "dispatch/T4-分析.md|header"
  "dispatch/T5-写手.md|header"
  "dispatch/T6-批判.md|header"
  "dispatch/T7-审计.md|header"
  "dispatch/T8-终检.md|header"
  "dispatch/T9-同行评审.md|header"
  "dispatch/G14-中文AI痕迹检测器.md|header"

  # 闸门 + 检测器（v2.4.0 G14 新增）
  "gates/14-中文AI痕迹-gate.md|header"
  "checkers/中文AI痕迹-checker.md|header"

  # 扩展 _shared 协议（实战反馈 + v2.5.0/v2.5.1 新增）
  "_shared/执行韧化协议-v2.1.0.md|header"
  "_shared/failure-modes.md|header"
  "_shared/字数判定表.md|header"
  "_shared/degraded-scenarios.md|header"
  "_shared/期刊数据库.md|header"
  "_shared/期刊匹配算法.md|header"
  "_shared/中文数据源集成.md|header"
  "_shared/format-export.md|header"

  # 模板（v2.4.6 + v2.5.0 + v2.5.1 新增）
  "templates/任务简报-template.md|header"
  "templates/审稿报告-template.md|header"
  "templates/G14检测报告-template.md|header"
  "templates/status-template.md|header"
  "templates/投稿就绪检查表-template.md|header"
  "templates/修订说明-template-full.md|header"

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
  # v2.5.6 P0 修复：直接 find 所有 .md 文件 trim（避免 SYNCS 路径拼接复杂逻辑）
  # 用 find 拿到所有 .md 文件的绝对路径（排除 .git/outputs/archive）
  python3 - <<'TRIMEOF'
import os
def trim(path, keep=1):
    """保留最前 keep 个版本行（版本行从上往下「新→旧」，最前=最新）"""
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')
    version_idx = [i for i, line in enumerate(lines) if line.startswith('> 版本：')]
    if len(version_idx) <= keep:
        return 0
    keep_set = set(version_idx[:keep])
    remove_set = set(version_idx[keep:])
    out = [line for i, line in enumerate(lines) if i not in remove_set]
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    return len(remove_set)

trimmed = 0
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ('.git', 'outputs', 'archive')]
    for name in files:
        if not name.endswith('.md'):
            continue
        path = os.path.join(root, name)
        n = trim(path, 1)
        if n > 0:
            print(f"  -{n} 行  {path}")
            trimmed += n
print(f"✅ 清理 {trimmed} 行旧版本记录（每文件保留最近 1 个 = 收敛单行）")
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
  echo ""
  # 第三方独立审查建议 #2（v2.5.6 P0 必修，教训 #175）：自动跑自审门，不依赖主控「记得」跑
  if [ -f "$SCRIPT_DIR/self-audit-gate.sh" ]; then
    echo "🛡️  启动自动自审门（v2.5.6 新增）..."
    echo ""
    if bash "$SCRIPT_DIR/self-audit-gate.sh"; then
      echo ""
      echo "✅ 自审门通过，版本同步完成"
    else
      echo ""
      echo "❌ 自审门失败，请修复后重新跑 sync-version.sh"
      exit 1
    fi
  else
    echo "⚠️  self-audit-gate.sh 不存在，跳过自动自审门"
  fi
fi
