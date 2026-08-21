#!/usr/bin/env bash
# 论衡版本号一致性检查脚本（P1-3 版本号自动化 - 层 1）
#
# ⚠️ 三层联动防漏改（教训 #118.1）：
#   层 1 本脚本（check-version.sh）= 本地只读验证
#   层 2 sync-version.sh = 本地批量同步写入
#   层 3 .github/workflows/version-check.yml = CI 云端自动验证
#   改角色文件名（references/agents/0X-*.md 重命名）时，必须三处同步更新角色文件清单，
#   否则版本号自动化会扫错路径直接报错（v2.3.0 重构时 scripts/ 两层漏改，教训 #118.1）。

#
# 用途：检查所有应含版本号的文件，文件顶部版本号是否与 SKILL.md frontmatter 一致
# 调用：./scripts/check-version.sh
# 退出码：0 = 全部一致 / 1 = 存在不一致

set -e

SKILL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_MD="$SKILL_ROOT/SKILL.md"

# 从 SKILL.md frontmatter 读取版本号（单一真源）
EXPECTED=$(grep -E '^version:' "$SKILL_MD" | head -1 | sed -E 's/version:[[:space:]]*//;s/["'"'"']//g;s/[[:space:]]*$//')

if [ -z "$EXPECTED" ]; then
  echo "❌ 无法从 SKILL.md 读取版本号"
  exit 1
fi

echo "📌 期望版本号（来自 SKILL.md frontmatter）：v$EXPECTED"
echo ""

# 定义版本号检查矩阵（文件路径 + 匹配模式 + 最少出现次数）
# 格式：文件路径|匹配模式|最少次数
CHECKS=(
  # 核心文档
  "references/glossary.md|v$EXPECTED|1"
  "references/pipeline-readme.md|v$EXPECTED|1"
  "references/设计文档.md|v$EXPECTED|1"

  # 共享协议
  "references/_shared/M-Gate-Algorithm.md|v$EXPECTED|1"

  # 8 个角色卡（顶部必须含版本号）
  "references/agents/00-主控-coordinator.md|v$EXPECTED|1"
  "references/agents/01-文献检索-literature-scout.md|v$EXPECTED|1"
  "references/agents/02-数据检索-data-scout.md|v$EXPECTED|1"
  "references/agents/03-案例检索-case-scout.md|v$EXPECTED|1"
  "references/agents/04-分析-analyst.md|v$EXPECTED|1"
  "references/agents/05-写作-writer.md|v$EXPECTED|1"
  "references/agents/06-批判-critical-companion.md|v$EXPECTED|1"
  "references/agents/07-审计-auditor.md|v$EXPECTED|1"
)

PASS=0
FAIL=0
MISSING=0

echo "=== 版本号一致性检查 ==="
printf "%-50s %-15s %-10s %s\n" "文件" "期望" "实际" "状态"
echo "--------------------------------------------------------------------------------"

for check in "${CHECKS[@]}"; do
  IFS='|' read -r file pattern min_count <<< "$check"
  full_path="$SKILL_ROOT/$file"

  if [ ! -f "$full_path" ]; then
    printf "%-50s %-15s %-10s %s\n" "$file" "v$EXPECTED" "N/A" "⚠️  文件不存在"
    MISSING=$((MISSING+1))
    continue
  fi

  actual_count=$(grep -cE "$pattern" "$full_path" || true)

  if [ "$actual_count" -ge "$min_count" ]; then
    printf "%-50s %-15s %-10s %s\n" "$file" "v$EXPECTED" "$actual_count 处" "✅"
    PASS=$((PASS+1))
  else
    printf "%-50s %-15s %-10s %s\n" "$file" "v$EXPECTED" "$actual_count 处" "❌"
    FAIL=$((FAIL+1))
  fi
done

echo "--------------------------------------------------------------------------------"
echo ""
echo "📊 统计："
echo "  ✅ 通过：$PASS"
echo "  ❌ 失败：$FAIL"
echo "  ⚠️  文件缺失：$MISSING"
echo ""

# 检查文件顶部版本号（前 5 行）
echo "=== 文件顶部版本号检查（前 5 行）==="
HEADER_PASS=0
HEADER_FAIL=0

for check in "${CHECKS[@]}"; do
  IFS='|' read -r file pattern min_count <<< "$check"
  full_path="$SKILL_ROOT/$file"

  if [ ! -f "$full_path" ]; then
    continue
  fi

  header_has_version=$(head -5 "$full_path" | grep -cE "v$EXPECTED" || true)

  if [ "$header_has_version" -ge 1 ]; then
    HEADER_PASS=$((HEADER_PASS+1))
  else
    echo "⚠️  $file 顶部缺少版本号 v$EXPECTED"
    HEADER_FAIL=$((HEADER_FAIL+1))
  fi
done

echo ""
echo "📊 顶部版本号统计："
echo "  ✅ 通过：$HEADER_PASS"
echo "  ⚠️  缺少：$HEADER_FAIL"
echo ""

# 最终判定
if [ "$FAIL" -eq 0 ] && [ "$MISSING" -eq 0 ] && [ "$HEADER_FAIL" -eq 0 ]; then
  echo "✅ 版本号一致性检查通过（v$EXPECTED）"
  exit 0
else
  echo "❌ 版本号一致性检查失败"
  echo "   建议执行 ./scripts/sync-version.sh 自动同步"
  exit 1
fi
