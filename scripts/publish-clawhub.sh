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
#   流程：build 净化包（若缺失）→ 提取本版 changelog → dry-run 校验 displayName/changelog → 确认 → 正式发布
#
# 变更（教训 #354，2026-09-12）：
#   clawhub publish 的 `--changelog` **缺省为空**（源码 publish.js: `options.changelog ?? ""`），
#   此时平台改用**自动生成**（字段 `changelogSource: "auto"`），其文本与本版真实内容不一致：
#   v2.12.33 自动文本以「Removed redundant file: skill-card.md」开篇 —— 该文件早在 2.12.31
#   就已移除，且全篇未提本版头号修复（T7.5 伪代码 / AE1 HIGH）。同版本号**不可重发修正**
#   （服务端拒 `already exists`）⇒ **发布时必须显式传 `--changelog`**。
#   ⚠️ CLI **不会**自动读 CHANGELOG.md（已核实 dist/ 全仓无该读取路径），必须由命令行给出。
#   本脚本从 CHANGELOG.md 的该版本章节提取（**单一真源，不新增第二份清单**，教训 #343）：
#   主题行 + 各 `###` 小节标题，压缩为 ≤40 行。
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_ROOT="${OUTPUTS_ROOT:-$HOME/lunheng-build/lunheng-outputs/clawhub-release}"
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

# ---- 版本号格式校验（v2.12.30 新增，回应第三方审计 P1-4）----
# 背景：VERSION 直接拼进 `$OUT_ROOT/$VERSION`（并会传给 build 脚本的 rm -rf 路径）。
#   `..` / 含 `/` 的输入会越出输出根 —— 参数即动作目标，必须在使用前严格校验。
if ! printf '%s' "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$'; then
  echo "❌ 版本号格式非法：'$VERSION'（要求 X.Y.Z，可带 -pre 后缀）" >&2
  exit 2
fi
case "$VERSION" in
  */*|*..*) echo "❌ 版本号不得含路径分隔符或 ..：'$VERSION'" >&2; exit 2 ;;
esac

# ---- 提取本版 changelog 文本（教训 #354）----
# 真源 = CHANGELOG.md 的 `## [vX.Y.Z]` 章节；压缩规则 = 主题行（`> **主题：…**`）+ 各 `###` 小节标题。
extract_changelog() {
  awk -v ver="$1" '
    $0 ~ "^## \\[v" ver "\\]" { insec = 1; next }
    insec && /^## \[/ { exit }
    insec { print }
  ' "$SKILL_ROOT/CHANGELOG.md" \
  | awk '
    /^###[[:space:]]/ {
      line = $0; sub(/^###[[:space:]]+/, "", line); print "- " line; next
    }
    /^>/ {
      line = $0; sub(/^>[[:space:]]*/, "", line)
      if (line ~ /^\*\*主题/) { sub(/^\*\*主题：/, "", line); print line }
      next
    }
  ' \
  | sed -e 's/\*\*//g' -e 's/`//g' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
  | grep -v '^$' || true
}

CHANGELOG_TEXT="$(extract_changelog "$VERSION" | head -n 40)"
if [[ -z "$CHANGELOG_TEXT" ]]; then
  if [[ "${CLAWHUB_ALLOW_EMPTY_CHANGELOG:-}" == "1" ]]; then
    echo "⚠️ CHANGELOG.md 无 v$VERSION 章节，按 CLAWHUB_ALLOW_EMPTY_CHANGELOG=1 放行（平台将自动生成，教训 #354）" >&2
  else
    echo "❌ CHANGELOG.md 中找不到 v$VERSION 章节（提取为空）——发布中止（教训 #354）" >&2
    echo "   版本记录须先补进 CHANGELOG.md；确要无 changelog 发布：CLAWHUB_ALLOW_EMPTY_CHANGELOG=1" >&2
    exit 3
  fi
fi

echo "📝 本版 changelog（取自 CHANGELOG.md，共 $(printf '%s\n' "$CHANGELOG_TEXT" | wc -l) 行）："
printf '%s\n' "$CHANGELOG_TEXT" | sed 's/^/   /'

OUT_DIR="$(cd "$OUT_ROOT/$VERSION" && pwd)"  # 转绝对路径（clawhub publish 不接受相对路径）

# ---- 1. 净化包存在性（缺则现场构建） ----
if [[ ! -f "$OUT_DIR/SKILL.md" ]]; then
  echo "🔧 净化包缺失，先构建 $OUT_DIR ..."
  bash "$SCRIPT_DIR/build-clawhub-release.sh" "$VERSION"
fi

# ---- 2. dry-run 校验 displayName ----
echo "🔍 dry-run 校验 displayName ..."
DRY="$(clawhub publish "$OUT_DIR" --slug "$SLUG" --version "$VERSION" --name "$DISPLAY_NAME" --changelog "$CHANGELOG_TEXT" --dry-run --json 2>&1 || true)"
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

# changelog 传递不能靠 dry-run 断言（教训 #354 复验）：当前 CLI 的 dry-run 分支
# （`dist/cli/commands/publish.js` 的 `if (options.dryRun)` 早退）**不构造请求体**，JSON
# 里无 `changelog` 字段 —— 在此断言“非空”会变成假失败并阻断正确的发布（反例见 #344）。
# 真实传递性已由源码逐行核实：`changelog` 进了 `ApiRoutes.skills` 的 POST body。
# 因此此处只保证“本地已提取到非空文本”（上文 exit 3）+ 人工核对上方回显。
echo "ℹ️ 注：dry-run 不校验 changelog（CLI 早退不构请求体）—— 已由上文非空保证罩住"

# ---- 3. 确认 + 正式发布 ----
if [[ "$CONFIRM" == "yes" ]]; then
  echo ""
  read -r -p "确认发布 $SLUG@$VERSION（displayName=$DISPLAY_NAME）？[y/N] " ans
  [[ "$ans" == "y" || "$ans" == "Y" ]] || { echo "已取消"; exit 0; }
fi

echo "🚀 正式发布 $SLUG@$VERSION ..."
clawhub publish "$OUT_DIR" --slug "$SLUG" --version "$VERSION" --name "$DISPLAY_NAME" --changelog "$CHANGELOG_TEXT"
echo ""
echo "✅ 已提交。审核页：https://clawhub.ai/$SLUG?version=$VERSION （服务端异步扫描，H1 应显示「$DISPLAY_NAME」）"
echo "   安全审计页：https://clawhub.ai/zuoyunlai/skills/lunheng-article-pipeline/security-audit"
