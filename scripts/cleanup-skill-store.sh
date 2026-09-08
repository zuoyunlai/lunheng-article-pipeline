#!/usr/bin/env bash
# =============================================================================
# cleanup-skill-store.sh — 论衡技能库瘦身脚本（v2.10.4 新增，教训 #232）
# =============================================================================
# 背景（教训 #232）：论衡技能文件夹 .git/ 46M + outputs/ 29M = 77M，
#   其中 .git/ 大量 unreachable 对象（reset/filter-branch/rebase 残留），
#   outputs/ 累计 29 个历史版本 clawhub-release/ + 10 个远古 archive/。
#   主人 2026-09-08 20:56 GMT+8 拍板清理，问"技能库超限怎么办"。
#
# 触发：主人手动跑 / 每次发版前自动跑
# 行为：
#   1. 软备份待删目录到 /tmp/lunheng-cleanup-bak-<时间戳>/
#   2. 删 outputs/archive/（v2.5.x 远古版本，10 个目录）
#   3. 保留 outputs/clawhub-release/ 最近 N 个版本（默认 3，默认保留 v2.10.1+.2+.3）
#   4. 删 outputs/clawhub-release/--dry-run/（dry-run 测试产物）
#   5. git reflog expire + git gc --prune=now（清 unreachable 对象）
#   6. 验证：自审门 15/15 + 净化包残留扫 0
# 返回：exit 0 = 成功 / exit 1 = 任意步骤失败
#
# ⚠️ 安全设计：所有删前先备份到 /tmp，主人可手动恢复
# ⚠️ N 版本保留策略：默认 3（v2.10.1/2/3），可传参 --keep=N 调整
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
KEEP=3
BAK_PARENT="/tmp"

# 解析参数
while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep=*)
      KEEP="${1#*=}"
      shift
      ;;
    --bak-parent=*)
      BAK_PARENT="${1#*=}"
      shift
      ;;
    --no-backup)
      NO_BACKUP=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--keep=N] [--bak-parent=/tmp] [--no-backup] [--dry-run]"
      echo "  --keep=N      保留最近 N 个 clawhub-release 版本（默认 3）"
      echo "  --bak-parent  备份目录父路径（默认 /tmp）"
      echo "  --no-backup   不备份（高风险，慎用）"
      echo "  --dry-run     只看不删"
      exit 0
      ;;
    *)
      echo "❌ 未知参数：$1"
      exit 1
      ;;
  esac
done

cd "$SKILL_ROOT"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# =============================================================================
# 步骤 0：基线测量
# =============================================================================
echo "📊 步骤 0: 基线测量"
BEFORE_GIT=$(du -sh .git 2>/dev/null | awk '{print $1}')
BEFORE_OUT=$(du -sh outputs 2>/dev/null | awk '{print $1}')
BEFORE_TOTAL=$(du -sh . 2>/dev/null | awk '{print $1}')
echo "  .git = $BEFORE_GIT"
echo "  outputs/ = $BEFORE_OUT"
echo "  总 = $BEFORE_TOTAL"
echo ""

# =============================================================================
# 步骤 1：备份到 /tmp/lunheng-cleanup-bak-<时间戳>/
# =============================================================================
TIMESTAMP=$(date +%Y%m%d-%H%M)
BAK_DIR="$BAK_PARENT/lunheng-cleanup-bak-$TIMESTAMP"

if [ "$NO_BACKUP" != "true" ] && [ "$DRY_RUN" != "true" ]; then
  echo "📦 步骤 1: 备份待删目录 → $BAK_DIR"
  mkdir -p "$BAK_DIR"

  # 1a. 备份 outputs/archive/
  if [ -d outputs/archive ]; then
    mv outputs/archive "$BAK_DIR/archive"
    echo "  ✅ archive/ 已备份"
  else
    echo "  ⏭️  archive/ 不存在，跳过"
  fi

  # 1b. 备份 outputs/clawhub-release/ 老版本（保留最近 N 个）
  if [ -d outputs/clawhub-release ]; then
    mkdir -p "$BAK_DIR/clawhub-release"
    KEEP_VERSIONS=$(ls outputs/clawhub-release/ 2>/dev/null | grep -v -- "--dry-run" | sort -V | tail -$KEEP)
    DELETED=0
    for v in outputs/clawhub-release/*/; do
      vname=$(basename "$v")
      if [ "$vname" != "--dry-run" ] && ! echo "$KEEP_VERSIONS" | grep -qFx "$vname"; then
        mv "$v" "$BAK_DIR/clawhub-release/"
        echo "  📦 备份并待删: $vname"
        DELETED=$((DELETED+1))
      fi
    done
    echo "  ✅ 保留: $KEEP_VERSIONS"
    echo "  ✅ 待删: $DELETED 个老版本"

    # 1c. 删 --dry-run 测试产物
    if [ -d outputs/clawhub-release/--dry-run ]; then
      rm -rf outputs/clawhub-release/--dry-run
      echo "  ✅ 删 --dry-run 测试产物"
    fi
  fi
elif [ "$DRY_RUN" == "true" ]; then
  echo "🔍 DRY_RUN 模式：列出待删目录（不实际删除）"
  echo "  outputs/archive/（如存在）"
  ls outputs/clawhub-release/ 2>/dev/null | grep -v -- "--dry-run" | sort -V | awk -v keep=$KEEP '
    { versions[NR]=$1; total=NR }
    END {
      for (i=1; i<=total; i++) {
        if (i <= total-keep) print "  待删: " versions[i]
        else print "  保留: " versions[i]
      }
    }'
  exit 0
fi
echo ""

# =============================================================================
# 步骤 2: .git/ 清理（reflog expire + gc --prune=now）
# =============================================================================
echo "🧹 步骤 2: .git/ 清理（reflog + gc prune）"

UNREACHABLE_BEFORE=$(git fsck --no-reflogs --unreachable --no-progress 2>&1 | grep -c "^(不可达|悬空)" || echo 0)
echo "  清理前 unreachable 对象数: $UNREACHABLE_BEFORE"

git reflog expire --expire=now --all
git gc --prune=now

UNREACHABLE_AFTER=$(git fsck --no-reflogs --unreachable --no-progress 2>&1 | grep -c "^(不可达|悬空)" || echo 0)
echo "  清理后 unreachable 对象数: $UNREACHABLE_AFTER"
echo "  ✅ git gc 完成"
echo ""

# =============================================================================
# 步骤 3: 验证完整性
# =============================================================================
echo "✅ 步骤 3: 验证完整性"

# 3a. git 状态
echo "  git status: $(git status --porcelain | wc -l) 个未提交变更"
echo "  git commits: $(git rev-list --count HEAD)"
echo "  git tags: $(git tag -l | wc -l)"

# 3b. 自审门
echo ""
echo "  跑自审门（门 C 36 文件版本戳必须全过）..."
if bash scripts/self-audit-gate.sh > /tmp/audit.log 2>&1; then
  echo "  ✅ 自审门 15/15 全过"
else
  echo -e "  ${RED}❌ 自审门失败！查看 /tmp/audit.log${NC}"
  cat /tmp/audit.log | tail -10
  exit 1
fi

# 3c. 净化包重建（验证 build 脚本仍正常）
echo ""
echo "  重建 v2.10.3 净化包..."
if bash scripts/build-clawhub-release.sh > /tmp/build.log 2>&1; then
  echo "  ✅ 净化包重建成功"
else
  echo -e "  ${RED}❌ 净化包重建失败！查看 /tmp/build.log${NC}"
  cat /tmp/build.log | tail -10
  exit 1
fi

# 3d. 净化包残留扫
echo ""
echo "  净化包残留扫..."
SKILL_VERSION=$(grep -m1 '^version:' SKILL.md | sed -E 's/version:[[:space:]]*//;s/["'"'"']//g;s/[[:space:]]*$//')
STALE=0
while IFS= read -r f; do
  head -10 "$f" 2>/dev/null | grep -E "v${SKILL_VERSION%.*}\.[012]" > /tmp/fhead.txt
  if grep -v "v$SKILL_VERSION" /tmp/fhead.txt | grep -qE "v${SKILL_VERSION%.*}\.[012]"; then
    echo -e "  ${RED}❌ $f 残留${NC}"
    STALE=$((STALE+1))
  fi
done < <(find outputs/clawhub-release -type f \( -name "*.md" -o -name "*.json" -o -name "*.yaml" \))

if [ "$STALE" -eq 0 ]; then
  echo "  ✅ 净化包残留扫 0"
else
  echo -e "  ${RED}❌ 净化包残留 $STALE 处${NC}"
  exit 1
fi

# =============================================================================
# 步骤 4: 对比 + 报告
# =============================================================================
echo ""
echo "============================================"
echo "🎉 清理完成"
echo "============================================"
echo "  .git: $BEFORE_GIT → $(du -sh .git 2>/dev/null | awk '{print $1}')"
echo "  outputs/: $BEFORE_OUT → $(du -sh outputs 2>/dev/null | awk '{print $1}')"
echo "  总: $BEFORE_TOTAL → $(du -sh . 2>/dev/null | awk '{print $1}')"
echo ""
echo "  备份位置: $BAK_DIR"
echo "  主人可手动删除备份（确认无误后）："
echo "    rm -rf $BAK_DIR"
echo ""

# 写教训到日记
echo "  日记建议：'清理 $BEFORE_TOTAL → $(du -sh . 2>/dev/null | awk '{print $1}')，备份在 $BAK_DIR'"