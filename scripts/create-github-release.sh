#!/usr/bin/env bash
# =============================================================================
# create-github-release.sh — 从 CHANGELOG.md 建 / 同步 GitHub Release（一条命令）
# =============================================================================
# 背景（教训 #254 同型）：changelog 是「易腐历史」——发布动作在 GitHub Releases 做，
#   仓库内没有单一真源，于是出现「有 tag 无 Release」的静默缺口（v2.3.11 / v2.11.0 /
#   v2.11.1 均曾漏建，2026-09-10 v2.12.8 又漏一次，靠人肉眼发现）。
#   缺口的本质不是「忘了点按钮」，而是**建 Release 没有可执行的单一入口**：
#   正文要手工从 CHANGELOG 粘、标题要手工拼、顺序靠人记。
#
# 本脚本把「建 Release」变成一条命令，并把三条铁律机械化：
#   ① 正文单一真源 = CHANGELOG.md 对应章节（逐字提取，非人工粘贴，不产生第二份真相）
#   ② 标题单一格式 = 「论衡 <tag> — <摘要>」，摘要取自 tag 所指提交的 subject（约定
#      `release: <tag> — <摘要>`，取破折号之后部分）；若 tag 已被发版后的 changelog/index
#      补提交前移（v2.12.16 实际发生，摘要丢失需手工 gh release edit），回退取 tag 可达
#      历史中最近一条同 tag 的发版 subject；仍无命中才退化为「论衡 <tag>」并在日志提示
#   ③ 已存在则 edit 同步（修复正文/标题漂移），不新建、不覆盖历史
#
# 用法：
#   bash scripts/create-github-release.sh [<tag>] [--dry-run|--check] [--no-dispatch]
#                                       [--skip-preflight]
#
#   <tag>            默认 = SKILL.md frontmatter 的当前版本（v<version>）
#   --dry-run        只打印将执行的动作 + 正文预览，不做任何写操作（本地零副作用）
#   --check          只比对「CHANGELOG 章节 vs 线上 Release 正文」，不写
#   --no-dispatch    建/改后不触发 changelog-check.yml 的在线校验
#   --skip-preflight 跳过 release-preflight.sh 前置闸（**仅限**已确认无并发链的补救场景，
#                    如线上正文漂移修复；会打印醒目警告，且不进 --dry-run/--check）
#
# 写操作（建 / 改 Release）前强制跑 scripts/release-preflight.sh（教训 #332「两查一停」）：
#   在飞链 / 编号占用 / 工作区干净任一不过 → 本脚本拒绝执行，退出码透传（10/11/12）。
#   本链自身的会话 key 用环境变量 LUNHENG_PREFLIGHT_SELF_SESSION 传入，否则闸会把
#   本链也算作在飞链而拒绝（失败关闭，不替人猜哪条是自己）。
#
# 退出码：0 = 完成/一致 / 1 = 漂移或缺 Release（--check）/ 2 = 环境或用法不满足
#         / 10 = 前置闸：在飞链未收口 / 11 = 前置闸：编号已占用 / 12 = 前置闸：工作区不净
# 依赖：bash + git + python3 + gh（gh 需已登录，见 `gh auth status`）
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

WORKFLOW_FILE="changelog-check.yml"

DRY_RUN=false
CHECK_ONLY=false
DISPATCH=true
PREFLIGHT=true
TAG=""

usage() {
  # 打印第 3 行起、到 header 注释块末尾（首个非 # 行前）——不硬编码行号，header 增删不漂移
  awk 'NR < 3 { next } /^#/ { sub(/^# /, ""); sub(/^#/, ""); print; next } { exit }' "$0"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)    DRY_RUN=true ;;
    --check)      CHECK_ONLY=true ;;
    --no-dispatch) DISPATCH=false ;;
    --skip-preflight) PREFLIGHT=false ;;
    -h|--help)    usage; exit 0 ;;
    -*)           echo "❌ 未知参数：$1（试 --help）" >&2; exit 2 ;;
    *)            if [ -n "$TAG" ]; then
                    echo "❌ 只接受一个 <tag> 位置参数（已有：$TAG）" >&2; exit 2
                  fi
                  TAG="$1" ;;
  esac
  shift
done

cd "$SKILL_ROOT"

# ---- 1. 解析 tag（默认 = SKILL.md 当前版本，版本号单一真源）----
if [ -z "$TAG" ]; then
  VERSION="$(grep -m1 -E '^[[:space:]]*version:' SKILL.md | sed 's/^[[:space:]]*version:[[:space:]]*//; s/["'"'"']//g')"
  [ -n "$VERSION" ] || { echo "❌ 无法从 SKILL.md frontmatter 读取版本号" >&2; exit 2; }
  TAG="v$VERSION"
fi

if ! printf '%s' "$TAG" | grep -qE '^v[0-9]+(\.[0-9]+)*$'; then
  echo "❌ tag 形如 vX.Y.Z：$TAG" >&2
  exit 2
fi

echo "📌 目标 tag：$TAG"

# ---- 2. tag 必须已存在（先打 tag 再建 Release；本脚本不替人打 tag）----
if ! git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  echo "❌ 本地无 tag $TAG —— 先打 tag 再建 Release：git tag -a $TAG -m 'release: $TAG — <摘要>'" >&2
  exit 2
fi

if ! git ls-remote --exit-code --tags origin "refs/tags/$TAG" >/dev/null 2>&1; then
  echo "⚠️  origin 上未见 tag $TAG（尚未 push？）——gh release create --verify-tag 会失败" >&2
fi

# ---- 3. 标题：commit subject 约定 `release: <tag> — <摘要>` ----
# 摘要在 tag 可达历史里就近取：发版后追加的 changelog/index 补提交会把 tag 前移，
# 直接读 tag 提交的 subject 会静默退化成「论衡 <tag>」。v2.12.16 实际发生过——tag 从
# `release: v2.12.16 — 归档保留策略去删除指令（…）` 移到 `changelog: 补 v2.12.16 章节`，
# 摘要丢失，需手工 `gh release edit` 才恢复。故约定不匹配时回退扫描 tag 可达 log。
RELEASE_RE="^release:[[:space:]]*${TAG}[[:space:]]*—[[:space:]]*(.+)$"
SUBJECT="$(git log -1 --format=%s "$TAG" 2>/dev/null || true)"
SUMMARY=""
SOURCE=""
if printf '%s' "$SUBJECT" | grep -qE "$RELEASE_RE"; then
  SUMMARY="$(printf '%s' "$SUBJECT" | sed -E "s/^release:[[:space:]]*${TAG}[[:space:]]*—[[:space:]]*//")"
  SOURCE="$TAG 的 commit subject（release: <tag> — <摘要>）"
else
  # 回退：取 tag 可达历史中最近一条同 tag 的发版 subject（不跨 tag，避免错摘上一版摘要）。
  # 不用 `| head -1`：pipefail 下 grep 先退会被 SIGPIPE 打断、管道整体非零，回退静默失效。
  MATCHES="$(git log --format=%s "$TAG" 2>/dev/null | grep -E "$RELEASE_RE" || true)"
  if [ -n "$MATCHES" ]; then
    FIRST_MATCH="${MATCHES%%$'\n'*}"
    SUMMARY="$(printf '%s' "$FIRST_MATCH" | sed -E "s/^release:[[:space:]]*${TAG}[[:space:]]*—[[:space:]]*//")"
    SOURCE="回退命中：$TAG 可达历史中最近一条 release 提交（$FIRST_MATCH）"
  fi
fi

TITLE=""
if [ -n "$SUMMARY" ]; then
  TITLE="论衡 $TAG — $SUMMARY"
  echo "📝 标题来源：$SOURCE"
else
  TITLE="论衡 $TAG"
  if printf '%s' "$SUBJECT" | grep -qE "^release:[[:space:]]*${TAG}[[:space:]]*$"; then
    echo "⚠️  commit subject 无「— <摘要>」部分且 $TAG 可达历史无更近的 release 提交，标题退化为「论衡 $TAG」"
  else
    echo "⚠️  $TAG 的 commit subject 未用发版约定：$SUBJECT"
    echo "    → 且 $TAG 可达历史中无 ^release: $TAG — <摘要> 形式的提交，标题退化为「论衡 $TAG」"
    echo "    （建议发版提交写成：release: $TAG — <摘要>）"
  fi
fi
echo "📌 标题：$TITLE"

# ---- 4. 正文：从 CHANGELOG.md 逐字提取（单一真源）----
NOTES_FILE="$(mktemp -t "lunheng-release-$TAG.XXXXXX.md")"
cleanup() { rm -f "$NOTES_FILE"; }
trap cleanup EXIT

if ! python3 - "$SKILL_ROOT" "$TAG" "$NOTES_FILE" <<'PYEOF'
import re, sys
from pathlib import Path

root, tag, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
text = (root / "CHANGELOG.md").read_text(encoding="utf-8")

HEAD_RE = re.compile(r"^## \[(v\d+(?:\.\d+)*)\]", re.M)
BOLD_RE = re.compile(r"^\*\*.+\*\*$")
matches = list(HEAD_RE.finditer(text))
section = None
for i, m in enumerate(matches):
    if m.group(1) == tag:
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section = text[m.start():end]
        break
if section is None:
    print(f"❌ CHANGELOG.md 中无 [{tag}] 章节——先补章节（python3 scripts/changelog-check.py --fill 或手写）",
          file=sys.stderr)
    sys.exit(2)

lines = section.split("\n")[1:]                      # 去掉 `## [tag] — <date>` 标题行
while lines and not lines[0].strip():
    lines.pop(0)
# changelog-check.py --fill 会在正文前补一行 `**<Release 名称>**`；导出时剥掉，保证往返稳定
if lines and BOLD_RE.match(lines[0].strip()) and (tag in lines[0] or "论衡" in lines[0]):
    lines = lines[1:]
body = re.sub(r"\n-{3,}\s*$", "", "\n".join(lines)).rstrip()

# 围栏闭合性：奇数个 ``` 会让其后全部版本渲染成代码块；此态下导出正文会连带崩坏，宁可不发
if sum(1 for l in body.splitlines() if l.strip().startswith("```")) % 2:
    print(f"❌ [{tag}] 章节代码围栏未闭合——先跑 python3 scripts/changelog-check.py --check 修复",
          file=sys.stderr)
    sys.exit(2)

if not body.strip():
    print(f"❌ [{tag}] 章节正文为空", file=sys.stderr)
    sys.exit(2)

out.write_text(body + "\n", encoding="utf-8")
print(f"📄 正文：{out}（{len(body)} 字符 / {len(body.splitlines())} 行）")
PYEOF
then
  exit 2
fi

# ---- 5. --dry-run：只报计划，不写远端 ----
if [ "$DRY_RUN" = true ]; then
  echo ""
  echo "--- 正文预览（前 12 行）---"
  head -n 12 "$NOTES_FILE"
  echo "--- 预览结束（全文 $NOTES_FILE，命令结束即删）---"
  echo ""
  echo "--- 将执行（dry-run，未执行）---"
  echo "gh release create $TAG --verify-tag --title \"$TITLE\" --notes-file <CHANGELOG 章节正文>"
  echo "  ↑ 若 $TAG 已有 Release，则改为："
  echo "gh release edit $TAG --title \"$TITLE\" --notes-file <CHANGELOG 章节正文>"
  [ "$DISPATCH" = true ] && echo "gh workflow run $WORKFLOW_FILE -F online=true   # 建后立即在线校验"
  echo ""
  echo "✅ dry-run 完成（零远端写入）"
  exit 0
fi

command -v gh >/dev/null 2>&1 || { echo "❌ 未找到 gh CLI（需已登录：gh auth status）" >&2; exit 2; }

RELEASE_EXISTS=false
if gh release view "$TAG" >/dev/null 2>&1; then
  RELEASE_EXISTS=true
fi

# ---- 6. --check：比对线上正文 vs CHANGELOG 章节 ----
if [ "$CHECK_ONLY" = true ]; then
  if [ "$RELEASE_EXISTS" != true ]; then
    echo "❌ $TAG 无 GitHub Release（changelog 缺页）"
    exit 1
  fi
  LIVE_FILE="$(mktemp -t "lunheng-live-$TAG.XXXXXX.md")"
  gh release view "$TAG" --json body --jq .body > "$LIVE_FILE"
  if python3 - "$NOTES_FILE" "$LIVE_FILE" "$TAG" <<'PYEOF'
import re, sys, difflib
from pathlib import Path

def norm(p):
    s = Path(p).read_text(encoding="utf-8")
    return re.sub(r"\n-{3,}\s*$", "", s.strip()).strip()

a, b, tag = norm(sys.argv[1]), norm(sys.argv[2]), sys.argv[3]
if a == b:
    print(f"✅ {tag} 线上 Release 正文 = CHANGELOG 章节正文（逐字一致）")
    sys.exit(0)
print(f"⚠️  {tag} 正文漂移（左=CHANGELOG / 右=线上 Release）：")
for line in list(difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm=""))[:40]:
    print("   " + line)
print(f"   修复：bash scripts/create-github-release.sh {tag}")
sys.exit(1)
PYEOF
  then
    rm -f "$LIVE_FILE"
    exit 0
  else
    rm -f "$LIVE_FILE"
    exit 1
  fi
fi

# ---- 6.5 发版前置闸（教训 #332）：写远端前先「两查一停」----
# 在飞链 / 编号占用 / 工作区干净任一不过就拒绝——Release 是收口动作，不是推进动作。
# --dry-run / --check 是只读路径，不进闸（它们的语义就是不写远端）；写路径默认必过闸。
if [ "$DRY_RUN" = true ] || [ "$CHECK_ONLY" = true ]; then
  echo "⏭️  前置闸跳过（$([ "$DRY_RUN" = true ] && echo --dry-run || echo --check) 为只读路径，零远端写入）"
  echo ""
elif [ "$PREFLIGHT" = true ]; then
  PREFLIGHT_SH="$SCRIPT_DIR/release-preflight.sh"
  if [ ! -f "$PREFLIGHT_SH" ]; then
    echo "❌ 缺前置闸脚本：$PREFLIGHT_SH（发版拒绝执行；补回后可重跑）" >&2
    exit 2
  fi
  echo "🚦 发版前置闸（release-preflight.sh，教训 #332）..."
  echo ""
  if bash "$PREFLIGHT_SH" "$TAG"; then
    echo ""
  else
    rc=$?
    echo "" >&2
    echo "❌ 前置闸未通过（退出码 $rc）→ 本脚本不建 / 不改 Release" >&2
    echo "   10=在飞链未收口 / 11=编号已占用 / 12=工作区不净（详见上方报告）" >&2
    exit "$rc"
  fi
  echo ""
else
  echo "⚠️  --skip-preflight：已跳过发版前置闸（在飞链 / 编号占用 / 工作区干净均未核验）" >&2
  echo "   仅限已确认无并发链的补救场景使用，不得作为常规发版路径" >&2
  echo ""
fi

# ---- 7. 建 / 同步 Release ----
if [ "$RELEASE_EXISTS" = true ]; then
  echo "♻️  已存在 Release $TAG → edit 同步正文（修复漂移；不新建、不覆盖历史）"
  gh release edit "$TAG" --title "$TITLE" --notes-file "$NOTES_FILE"
  echo "✅ Release $TAG 正文已同步"
else
  gh release create "$TAG" --verify-tag --title "$TITLE" --notes-file "$NOTES_FILE"
  echo "✅ Release $TAG 已创建"
fi

# ---- 8. 建后立即触发在线覆盖校验（不等下一次 cron）----
if [ "$DISPATCH" = true ]; then
  if gh workflow run "$WORKFLOW_FILE" -F online=true >/dev/null 2>&1; then
    echo "🔎 已触发 $WORKFLOW_FILE（online=true）——在线覆盖校验立即开跑"
  else
    echo "⚠️  触发 $WORKFLOW_FILE 失败（不阻塞）：可手动 gh workflow run $WORKFLOW_FILE -F online=true"
  fi
fi

# ---- 9. 本地在线校验（同一口径的即时回执）----
python3 scripts/changelog-check.py --online
