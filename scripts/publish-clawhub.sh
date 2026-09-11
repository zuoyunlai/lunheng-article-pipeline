#!/usr/bin/env bash
# =============================================================================
# publish-clawhub.sh — 论衡 ClawHub 一键发布封装（教训 #200 防线）
# =============================================================================
# 背景（教训 #200，2026-09-07）：
#   clawhub publish 的 H1/displayName **不读 SKILL.md frontmatter 的 displayName**，
#   而是 `options.name ?? titleCase(basename(folder))`（源码 publish.js:26 实锤）。
#   净化包目录名 = 版本号 → 漏传 --name = H1 显示版本号（v2.7.4 修过 frontmatter 仍复发）。
#   本脚本固定 --name，并在 dry-run 阶段断言 displayName 不是「纯版本号」，杜绝再犯。
#
# 用法：
#   bash scripts/publish-clawhub.sh [VERSION] [--yes]
#     VERSION  缺省从 SKILL.md frontmatter 读取
#     --yes    跳过最终确认，直接正式发布（CI/无人值守用）
#   流程：build 净化包（若缺失）→ dry-run 校验 displayName → 确认 → 正式发布
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_ROOT="$SKILL_ROOT/outputs/clawhub-release"
SLUG="lunheng-article-pipeline"
DISPLAY_NAME="论衡 — 严肃长文流水线"

VERSION="${1:-}"
shift || true
CONFIRM="yes"
if [[ "${1:-}" == "--yes" ]]; then
  CONFIRM="no"
fi

if [[ -z "$VERSION" ]]; then
  VERSION="$(grep -m1 -E '^[[:space:]]*version:' "$SKILL_ROOT/SKILL.md" | sed 's/^[[:space:]]*version:[[:space:]]*//' | tr -d '"')"
fi
[[ -z "$VERSION" ]] && { echo "❌ 无法确定版本号（传参或 SKILL.md frontmatter）" >&2; exit 1; }

OUT_DIR="$(cd "$OUT_ROOT/$VERSION" && pwd)"  # 转绝对路径（clawhub publish 不接受相对路径）

# ---- 1. 净化包存在性（缺则现场构建） ----
if [[ ! -f "$OUT_DIR/SKILL.md" ]]; then
  echo "🔧 净化包缺失，先构建 $OUT_DIR ..."
  bash "$SCRIPT_DIR/build-clawhub-release.sh" "$VERSION"
fi

# ---- 2. dry-run 校验 displayName ----
echo "🔍 dry-run 校验 displayName ..."
DRY="$(clawhub publish "$OUT_DIR" --slug "$SLUG" --version "$VERSION" --name "$DISPLAY_NAME" --dry-run --json 2>&1 || true)"
echo "$DRY" | tail -14

# displayName 若等于纯版本号（如 "2.7.9"）→ 失败退出（教训 #200 防线）
if echo "$DRY" | grep -qE '"displayName"[[:space:]]*:[[:space:]]*"v?[0-9]+\.[0-9]+\.[0-9]+"'; then
  echo "❌ displayName 仍是版本号（漏 --name？），发布中止——见教训 #200" >&2
  exit 1
fi
if echo "$DRY" | grep -q '"displayName"[[:space:]]*:[[:space:]]*"论衡'; then
  echo "✅ displayName = $DISPLAY_NAME"
else
  echo "⚠️ dry-run 未识别出预期 displayName，继续前请人工核对上方 JSON" >&2
fi

# ---- 3. 确认 + 正式发布 ----
if [[ "$CONFIRM" == "yes" ]]; then
  echo ""
  read -r -p "确认发布 $SLUG@$VERSION（displayName=$DISPLAY_NAME）？[y/N] " ans
  [[ "$ans" == "y" || "$ans" == "Y" ]] || { echo "已取消"; exit 0; }
fi

echo "🚀 正式发布 $SLUG@$VERSION ..."
clawhub publish "$OUT_DIR" --slug "$SLUG" --version "$VERSION" --name "$DISPLAY_NAME"
echo ""
echo "✅ 已提交。审核页：https://clawhub.ai/$SLUG?version=$VERSION （服务端异步扫描，H1 应显示「$DISPLAY_NAME」）"
echo "   安全审计页：https://clawhub.ai/zuoyunlai/skills/lunheng-article-pipeline/security-audit"
