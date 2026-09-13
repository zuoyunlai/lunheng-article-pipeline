#!/usr/bin/env bash
# =============================================================================
# cleanup-skill-store.sh — 论衡技能库瘦身脚本（v2.10.4 新增，教训 #232）
# =============================================================================
# 背景（教训 #232）：论衡技能文件夹 .git/ 46M + $OUTPUTS_ROOT/ 29M = 77M，
#   其中 .git/ 大量 unreachable 对象（reset/filter-branch/rebase 残留），
#   $OUTPUTS_ROOT/ 累计 29 个历史版本 clawhub-release/ + 10 个远古 archive/。
#   主人 2026-09-08 20:56 GMT+8 拍板清理，问"技能库超限怎么办"。
#
# 触发：主人手动跑 / 每次发版前自动跑
# 行为（v2.12.30 修订，回应第三方审计 P1-2）：
#   1. 软备份待删目录到 /tmp/lunheng-cleanup-bak-<时间戳>/（--no-backup 除外）
#   2. 删 $OUTPUTS_ROOT/archive/（v2.5.x 远古版本，10 个目录）
#   3. 保留 $OUTPUTS_ROOT/clawhub-release/ 最近 N 个版本（默认 3）
#   4. 删 $OUTPUTS_ROOT/clawhub-release/--dry-run/（dry-run 测试产物）
#   5. [默认跳过] .git/ 历史清理 —— 仅 --purge-git-history 时执行（见下）
#   6. 验证：自审门（全门，以脚本实跑为准）+ 净化包重建 + 残留扫 0
# 返回：exit 0 = 成功 / exit 1 = 任意步骤失败 / exit 2 = 用法或参数错误
#
# ⚠️ 安全设计：默认口径下所有删除都先在 /tmp 留备份，主人可手动恢复。
# ⚠️ --purge-git-history 是**不可逆**操作（reflog expire + gc --prune=now 会永久丢弃
#    reset/filter-branch/rebase 留下的可恢复历史）。故：
#      · 默认**不执行**（旧版无条件执行，与「所有删前先备份」的承诺相矛盾 —— 审计 P1-2）；
#      · 执行前强制打 **git bundle 全量备份**（可完整重建仓库），再要求 --purge-git-history；
#      · 与 --no-backup 互斥（既不备份又要销毁历史 = 拒绝执行）。
# ⚠️ N 版本保留策略：默认 3，可传参 --keep=N 调整（须为正整数）
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
KEEP=3
BAK_PARENT="/tmp"
# v2.13.x 整改 A5：$OUTPUTS_ROOT/ 已迁出技能根（→ ~/lunheng-build/lunheng-$OUTPUTS_ROOT/）；保留 env 覆盖
OUTPUTS_ROOT="${OUTPUTS_ROOT:-$HOME/lunheng-build/lunheng-outputs}"

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
    --purge-git-history)
      PURGE_GIT_HISTORY=true
      shift
      ;;
    --bundle-dir=*)
      BUNDLE_DIR="${1#*=}"
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--keep=N] [--bak-parent=/tmp] [--no-backup] [--purge-git-history] [--bundle-dir=DIR] [--dry-run]"
      echo "  --keep=N              保留最近 N 个 clawhub-release 版本（默认 3，须正整数）"
      echo "  --bak-parent          备份目录父路径（默认 /tmp）"
      echo "  --no-backup           不备份待删目录（高风险，慎用）"
      echo "  --purge-git-history   【不可逆】清 .git 历史（reflog expire + gc --prune=now）"
      echo "                        默认关闭；开启前会先打 git bundle 全量备份"
      echo "  --bundle-dir=DIR      上述 bundle 存放目录（默认 <bak-parent>）"
      echo "  --dry-run             只看不删"
      exit 0
      ;;
    *)
      echo "❌ 未知参数：$1"
      exit 1
      ;;
  esac
done

# ---- 参数校验（v2.12.30，回应 P1-4 同型：参数即动作目标，必须严格）----
if ! printf '%s' "$KEEP" | grep -qE '^[1-9][0-9]*$'; then
  echo "❌ --keep 必须为正整数，收到：'$KEEP'" >&2
  exit 2
fi
if [ "$PURGE_GIT_HISTORY" = "true" ] && [ "$NO_BACKUP" = "true" ]; then
  echo "❌ --purge-git-history 与 --no-backup 互斥：" >&2
  echo "   既不备份、又要销毁 Git 可恢复历史，等于放弃全部退路，拒绝执行。" >&2
  exit 2
fi

cd "$SKILL_ROOT"

# 颜色
RED='\033[0;31m'
NC='\033[0m'

# =============================================================================
# 步骤 0：基线测量
# =============================================================================
echo "📊 步骤 0: 基线测量"
BEFORE_GIT=$(du -sh .git 2>/dev/null | awk '{print $1}')
BEFORE_OUT=$(du -sh $OUTPUTS_ROOT 2>/dev/null | awk '{print $1}')
BEFORE_TOTAL=$(du -sh . 2>/dev/null | awk '{print $1}')
echo "  .git = $BEFORE_GIT"
echo "  $OUTPUTS_ROOT/ = $BEFORE_OUT"
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

  # 1a. 备份 $OUTPUTS_ROOT/archive/
  if [ -d $OUTPUTS_ROOT/archive ]; then
    mv $OUTPUTS_ROOT/archive "$BAK_DIR/archive"
    echo "  ✅ archive/ 已备份"
  else
    echo "  ⏭️  archive/ 不存在，跳过"
  fi

  # 1b. 备份 $OUTPUTS_ROOT/clawhub-release/ 老版本（保留最近 N 个）
  if [ -d $OUTPUTS_ROOT/clawhub-release ]; then
    mkdir -p "$BAK_DIR/clawhub-release"
    KEEP_VERSIONS=$({
      for entry in $OUTPUTS_ROOT/clawhub-release/*/; do
        [ -d "$entry" ] || continue
        ename=$(basename "$entry")
        [ "$ename" = "--dry-run" ] && continue
        printf '%s\n' "$ename"
      done
    } | sort -V | tail -n "$KEEP")
    DELETED=0
    for v in $OUTPUTS_ROOT/clawhub-release/*/; do
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
    if [ -d $OUTPUTS_ROOT/clawhub-release/--dry-run ]; then
      rm -rf $OUTPUTS_ROOT/clawhub-release/--dry-run
      echo "  ✅ 删 --dry-run 测试产物"
    fi
  fi
elif [ "$DRY_RUN" == "true" ]; then
  echo "🔍 DRY_RUN 模式：列出待删目录（不实际删除）"
  echo "  $OUTPUTS_ROOT/archive/（如存在）"
  {
    for entry in $OUTPUTS_ROOT/clawhub-release/*/; do
      [ -d "$entry" ] || continue
      ename=$(basename "$entry")
      [ "$ename" = "--dry-run" ] && continue
      printf '%s\n' "$ename"
    done
  } | sort -V | awk -v keep="$KEEP" '
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
# 步骤 2: .git/ 历史清理 —— 【默认跳过】破坏性操作，须显式 --purge-git-history
# =============================================================================
# v2.12.30（回应第三方审计 P1-2）：旧版**无条件**执行 `git reflog expire --expire=now --all`
#   + `git gc --prune=now`，会永久丢弃 reset/filter-branch/rebase 残留的可恢复对象，
#   与脚本头部「所有删前先备份到 /tmp，主人可手动恢复」的承诺直接矛盾（.git 没有备份）。
#   现在：默认不动 .git；显式 --purge-git-history 时**先打全量 bundle 备份**再清理。
if [ "$PURGE_GIT_HISTORY" != "true" ]; then
  echo "⏭️  步骤 2: 跳过 .git 历史清理（默认口径：不动可恢复历史）"
  echo "    如需清理 unreachable 对象，显式加 --purge-git-history（会先打 bundle 备份）"
  UNREACHABLE_BEFORE=$(git fsck --no-reflogs --unreachable --no-progress 2>&1 | grep -c "^(不可达|悬空)" || echo 0)
  echo "    （现存 unreachable 对象数：$UNREACHABLE_BEFORE，本次不清理）"
  echo ""
else
  echo "🧹 步骤 2: .git/ 历史清理（reflog expire + gc --prune=now）—— 不可逆操作"
  UNREACHABLE_BEFORE=$(git fsck --no-reflogs --unreachable --no-progress 2>&1 | grep -c "^(不可达|悬空)" || echo 0)
  echo "  清理前 unreachable 对象数: $UNREACHABLE_BEFORE"

  # 强制全量 bundle 备份（可 git clone <bundle> 完整重建仓库）
  BUNDLE_DIR="${BUNDLE_DIR:-$BAK_PARENT}"
  mkdir -p "$BUNDLE_DIR"
  BUNDLE_FILE="$BUNDLE_DIR/lunheng-git-full-$TIMESTAMP.bundle"
  echo "  📦 全量 git bundle 备份 → $BUNDLE_FILE"
  if ! git bundle create "$BUNDLE_FILE" --all >/dev/null 2>&1; then
    echo "❌ git bundle 备份失败，拒绝继续销毁历史" >&2
    exit 1
  fi
  if ! git bundle verify "$BUNDLE_FILE" >/dev/null 2>&1; then
    echo "❌ git bundle 校验失败（备份不可用），拒绝继续销毁历史" >&2
    echo "   备份文件保留在 $BUNDLE_FILE 供排查" >&2
    exit 1
  fi
  echo "  ✅ bundle 校验通过（$(du -sh "$BUNDLE_FILE" | awk '{print $1}')）"

  git reflog expire --expire=now --all
  git gc --prune=now

  UNREACHABLE_AFTER=$(git fsck --no-reflogs --unreachable --no-progress 2>&1 | grep -c "^(不可达|悬空)" || echo 0)
  echo "  清理后 unreachable 对象数: $UNREACHABLE_AFTER"
  echo "  ✅ git gc 完成（回滚方式：git clone $BUNDLE_FILE <新目录>）"
  echo ""
fi

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
  echo "  ✅ 自审门全过（道数以脚本实跑输出为准，勿引用历史数字）"
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
SKILL_VERSION=$(grep -m1 -E '^[[:space:]]*version:' SKILL.md | sed -E 's/^[[:space:]]*version:[[:space:]]*//;s/["'"'"']//g;s/[[:space:]]*$//')
STALE=0
while IFS= read -r f; do
  head -10 "$f" 2>/dev/null | grep -E "v${SKILL_VERSION%.*}\.[012]" > /tmp/fhead.txt
  if grep -v "v$SKILL_VERSION" /tmp/fhead.txt | grep -qE "v${SKILL_VERSION%.*}\.[012]"; then
    echo -e "  ${RED}❌ $f 残留${NC}"
    STALE=$((STALE+1))
  fi
done < <(find $OUTPUTS_ROOT/clawhub-release -type f \( -name "*.md" -o -name "*.json" -o -name "*.yaml" \))

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
echo "  $OUTPUTS_ROOT/: $BEFORE_OUT → $(du -sh $OUTPUTS_ROOT 2>/dev/null | awk '{print $1}')"
echo "  总: $BEFORE_TOTAL → $(du -sh . 2>/dev/null | awk '{print $1}')"
echo ""
echo "  备份位置: $BAK_DIR"
echo "  主人可手动删除备份（确认无误后）："
echo "    rm -rf $BAK_DIR"
echo ""

# 写教训到日记
echo "  日记建议：'清理 $BEFORE_TOTAL → $(du -sh . 2>/dev/null | awk '{print $1}')，备份在 $BAK_DIR'"