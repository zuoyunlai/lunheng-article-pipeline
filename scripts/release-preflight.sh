#!/usr/bin/env bash
# =============================================================================
# release-preflight.sh — 发版前置闸「两查一停」（教训 #332）
# =============================================================================
# 背景（教训 #332，2026-09-11 实测错乱）：多条会话链并行修订同一仓库时，发版动作
#   （升版号 / tag / push / GitHub Release / 净化包）被当成「本链的下一步」，没检查
#   全局状态 → 版本谱系被劈成两半：远端 master=eb7dc46(v2.12.18)、本地 HEAD=958278e
#   (v2.12.20)，v2.12.19 / v2.12.20 的 tag 本地远端都没有，净化包只到 2.12.18。
#   根因：版本号 / tag / 远端 master / 净化包目录都是**单点共享资源**，却按单链上下文推断。
#
# 两查一停（任一不过 → 退出码非 0，绝不静默通过）：
#   ① 在飞链：同项目（spawnedCwd 在本仓内，或 label / cwd 命中项目关键词）status=running
#      的会话与子会话 → 有则拒绝发版，打印清单 + 「如何等」
#   ② 编号占用：目标 tag 在本地（git tag -l）与远端（git ls-remote --tags）双向查
#      → 任一已占用即拒绝，要求换号
#   ③ 工作区干净：git status --porcelain 非空即拒绝（未跟踪文件也算，见 --allow-untracked）
#
# 本脚本**只读**：不 push、不打 tag、不建 GitHub Release、不改任何 ref，可反复安全运行。
# 它是「拒绝器」不是「执行器」——通过后由维护者按 SOP 手工发版。
#
# 用法：
#   bash scripts/release-preflight.sh [<tag>] [选项]
#
#   <tag>                目标版本号（默认 = SKILL.md frontmatter 版本 → v<version>）
#   --self-session <key> 本发版链自身的会话 key（不计入在飞链；环境变量
#                        LUNHENG_PREFLIGHT_SELF_SESSION 同义）。**建议必给**：不给时
#                        本链自身会被计入在飞链 → 拒绝（失败关闭，不替人猜哪条是自己）
#   --exclude <key>      显式忽略某条在飞链（可重复）；忽略项会打印在报告里，不静默
#   --allow-untracked    未跟踪文件不计入「工作区不净」（默认计入 = 严格口径）
#   --sessions-file <f>  从文件读在飞链清单 JSON（离线 / 测试用 = fake 在飞链清单）
#   --sessions-cmd <c>   覆盖在飞链采集命令（默认 openclaw sessions list --json ...）
#   --remote-file <f>    从文件读 ls-remote 输出（离线 / 测试用 = fake ls-remote）
#   --remote-cmd <c>     覆盖远端查询命令（默认 git ls-remote --heads --tags origin）
#   -h | --help
#
# 退出码：0=通过 / 10=在飞链未收口 / 11=目标编号已占用 / 12=工作区不净 / 2=用法或环境错误
# 依赖：bash + git + python3（JSON 解析）
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

EXIT_PASS=0
EXIT_INFLIGHT=10
EXIT_TAG_TAKEN=11
EXIT_DIRTY=12
EXIT_USAGE=2

INFLIGHT_STATUSES="${LUNHENG_PREFLIGHT_INFLIGHT_STATUS:-running}"
PROJECT_KEYWORDS="${LUNHENG_PREFLIGHT_KEYWORDS:-论衡 lunheng}"
SELF_SESSION="${LUNHENG_PREFLIGHT_SELF_SESSION:-}"
SESSIONS_CMD="${LUNHENG_PREFLIGHT_SESSIONS_CMD:-openclaw sessions list --json --all-agents --limit all}"
REMOTE_CMD="${LUNHENG_PREFLIGHT_REMOTE_CMD:-git ls-remote --heads --tags origin}"

SESSIONS_FILE=""
REMOTE_FILE=""
ALLOW_UNTRACKED=false
TAG=""
EXCLUDES=()

usage() {
  awk 'NR < 3 { next } /^#/ { sub(/^# /, ""); sub(/^#/, ""); print; next } { exit }' "$0"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --self-session)    SELF_SESSION="${2:-}"
                       [ -n "$SELF_SESSION" ] || { echo "❌ --self-session 需带会话 key" >&2; exit "$EXIT_USAGE"; }
                       shift ;;
    --exclude)         [ -n "${2:-}" ] || { echo "❌ --exclude 需带会话 key" >&2; exit "$EXIT_USAGE"; }
                       EXCLUDES+=("$2"); shift ;;
    --allow-untracked) ALLOW_UNTRACKED=true ;;
    --sessions-file)   SESSIONS_FILE="${2:-}"; shift ;;
    --sessions-cmd)    SESSIONS_CMD="${2:-}"; shift ;;
    --remote-file)     REMOTE_FILE="${2:-}"; shift ;;
    --remote-cmd)      REMOTE_CMD="${2:-}"; shift ;;
    -h|--help)         usage; exit "$EXIT_PASS" ;;
    -*)                echo "❌ 未知参数：$1（试 --help）" >&2; exit "$EXIT_USAGE" ;;
    *)                 if [ -n "$TAG" ]; then
                         echo "❌ 只接受一个 <tag> 位置参数（已有：$TAG）" >&2; exit "$EXIT_USAGE"
                       fi
                       TAG="$1" ;;
  esac
  shift
done

cd "$SKILL_ROOT"

TMP_PF="$(mktemp -d -t lunheng-preflight.XXXXXX)"
cleanup() { rm -rf "$TMP_PF"; }
trap cleanup EXIT

# ---- 0. 目标编号（默认 = SKILL.md frontmatter，版本号单一真源）----
if [ -z "$TAG" ]; then
  VERSION="$(grep -m1 -E '^[[:space:]]*version:' SKILL.md | sed 's/^[[:space:]]*version:[[:space:]]*//; s/["'"'"']//g')" || true
  [ -n "$VERSION" ] || { echo "❌ 无法从 SKILL.md frontmatter 读取版本号" >&2; exit "$EXIT_USAGE"; }
  TAG="v$VERSION"
fi

if ! printf '%s' "$TAG" | grep -qE '^v[0-9]+(\.[0-9]+)*$'; then
  echo "❌ tag 形如 vX.Y.Z：$TAG" >&2
  exit "$EXIT_USAGE"
fi

echo "🚦 论衡发版前置闸（release-preflight.sh，教训 #332）"
echo "   目标 tag：$TAG"
echo "   仓库：$SKILL_ROOT"
echo "   本闸只读：不 push / 不打 tag / 不建 Release / 不改 ref"
echo ""

# =============================================================================
# 查 ① 在飞链（同项目 status=running 的会话 / 子会话）
# =============================================================================
if [ -n "$SESSIONS_FILE" ]; then
  [ -f "$SESSIONS_FILE" ] || { echo "❌ --sessions-file 不存在：$SESSIONS_FILE" >&2; exit "$EXIT_USAGE"; }
  cp -- "$SESSIONS_FILE" "$TMP_PF/sessions.json"
else
  if ! bash -c "$SESSIONS_CMD" > "$TMP_PF/sessions.json" 2> "$TMP_PF/sessions.err"; then
    echo "❌ 无法获取在飞链清单（命令失败）：$SESSIONS_CMD" >&2
    sed -n '1,3p' "$TMP_PF/sessions.err" >&2 || true
    echo "   → 拒绝发版（失败关闭）：查不到在飞链就不能声称「没有在飞链」。" >&2
    echo "     修法：确认 openclaw CLI 可用，或用 --sessions-file 提供清单快照。" >&2
    exit "$EXIT_USAGE"
  fi
fi

# 在飞链过滤（JSON → TSV：key / label / cwd / 最近活动分钟）。无法解析 = 拒绝，不当作 0 条放行。
if ! python3 - "$TMP_PF/sessions.json" "$SKILL_ROOT" "$SELF_SESSION" "$INFLIGHT_STATUSES" \
     "$PROJECT_KEYWORDS" ${EXCLUDES[@]+"${EXCLUDES[@]}"} > "$TMP_PF/inflight.tsv" <<'PYEOF'
import json
import sys

path, root, self_key, statuses, keywords = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
excludes = {a for a in sys.argv[6:] if a}

try:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
except Exception as exc:                                  # JSON 坏 / 空文件
    print(f"__UNPARSABLE__: {exc}", file=sys.stderr)
    sys.exit(3)

sessions = data.get("sessions") if isinstance(data, dict) else data
if not isinstance(sessions, list):                        # 形如 {"ok": false, ...}
    print("__UNPARSABLE__: 无 sessions 列表（命令可能返回了错误对象）", file=sys.stderr)
    sys.exit(3)

want = {s.strip().lower() for s in statuses.split() if s.strip()}
kws = [k for k in keywords.split() if k]
root = root.rstrip("/")

rows = []
for sess in sessions:
    if not isinstance(sess, dict):
        continue
    key = sess.get("key") or sess.get("sessionKey") or ""
    if not key or key == self_key or key in excludes:
        continue
    if (sess.get("status") or "").lower() not in want:
        continue
    cwd = sess.get("spawnedCwd") or sess.get("cwd") or ""
    label = sess.get("label") or sess.get("displayName") or ""
    related = bool(cwd) and (cwd == root or cwd.startswith(root + "/"))
    if not related:
        related = any(k in label or k in key or k in cwd for k in kws)
    if not related:
        continue
    age = sess.get("ageMs")
    mins = int(age // 60000) if isinstance(age, (int, float)) else -1
    rows.append((key, label or "-", cwd or "-", mins))

for key, label, cwd, mins in rows:
    print(f"{key}\t{label}\t{cwd}\t{mins}")

sys.exit(0)
PYEOF
then
  echo "❌ 在飞链清单无法解析 → 拒绝发版（失败关闭，不按 0 条放行）" >&2
  exit "$EXIT_USAGE"
fi

INFLIGHT_COUNT="$(wc -l < "$TMP_PF/inflight.tsv" | tr -d ' ')"
echo "[1/3] 在飞链检查（同项目 status=${INFLIGHT_STATUSES}）"
if [ "$INFLIGHT_COUNT" -eq 0 ]; then
  echo "      ✅ 0 条"
  [ -n "$SELF_SESSION" ] && echo "      （本链自身已排除：$SELF_SESSION）"
  [ "${#EXCLUDES[@]}" -gt 0 ] && echo "      （显式忽略：${EXCLUDES[*]}）"
else
  echo "      ❌ $INFLIGHT_COUNT 条在飞链 —— 拒绝发版"
  while IFS=$'\t' read -r s_key s_label s_cwd s_mins; do
    if [ "$s_mins" -lt 0 ]; then
      echo "         - $s_key   [$s_label]   cwd=$s_cwd"
    else
      echo "         - $s_key   [$s_label]   cwd=$s_cwd   最近活动 ${s_mins}m 前"
    fi
  done < "$TMP_PF/inflight.tsv"
  echo "      ⏳ 如何等：这些链 status=done 后再重跑本闸（发版是收口动作，不是推进动作）"
  echo "         · 上面若含本链自身 → 用 --self-session <本链 key> 重跑（key 从 sessions_list 取）"
  echo "         · 确认是快照滞后的幽灵 running（教训 #308：摘要/快照会过期）→ 先用"
  echo "           openclaw sessions list 复核，再 --exclude <key>（会打印在报告里，不静默）"
fi
echo ""

FAIL_INFLIGHT=1
[ "$INFLIGHT_COUNT" -eq 0 ] && FAIL_INFLIGHT=0

# =============================================================================
# 查 ② 编号占用（本地 tag + 远端 tag 双向查）
# =============================================================================
if [ -n "$REMOTE_FILE" ]; then
  [ -f "$REMOTE_FILE" ] || { echo "❌ --remote-file 不存在：$REMOTE_FILE" >&2; exit "$EXIT_USAGE"; }
  REMOTE_OUT="$(< "$REMOTE_FILE")"
else
  if ! REMOTE_OUT="$(bash -c "$REMOTE_CMD" 2> "$TMP_PF/remote.err")"; then
    echo "❌ 无法查询远端 tag（离线或 origin 不可达）：$REMOTE_CMD" >&2
    sed -n '1,3p' "$TMP_PF/remote.err" >&2 || true
    echo "   → 拒绝发版（失败关闭）：编号占用无法核验。" >&2
    echo "     修法：联网 / 先确认 origin 可达，或用 --remote-file 提供 ls-remote 快照。" >&2
    exit "$EXIT_USAGE"
  fi
fi

printf '%s\n' "$REMOTE_OUT" \
  | awk '$2 ~ /^refs\/tags\// { n=$2; sub(/^refs\/tags\//, "", n); sub(/\^\{\}$/, "", n); if (n != "") print n }' \
  | sort -u > "$TMP_PF/remote_tags.txt"
git tag -l | sort > "$TMP_PF/local_tags.txt"

LOCAL_HIT="$(grep -Fx -- "$TAG" "$TMP_PF/local_tags.txt" || true)"
REMOTE_HIT="$(grep -Fx -- "$TAG" "$TMP_PF/remote_tags.txt" || true)"

echo "[2/3] 编号占用检查（目标 $TAG）"
if [ -z "$LOCAL_HIT" ] && [ -z "$REMOTE_HIT" ]; then
  echo "      ✅ 本地未占用 / 远端未占用"
else
  echo "      ❌ 目标编号已被占用 —— 拒绝发版，请换号（教训 #332：单点共享资源不可覆盖）"
  [ -n "$LOCAL_HIT" ] && echo "         · 本地已有 tag：$LOCAL_HIT"
  [ -n "$REMOTE_HIT" ] && echo "         · 远端已有 tag：$REMOTE_HIT"
  echo "         · 换号后重跑本闸；不要复用已占用编号（tag/Release 先后关系会与内容错位）"
fi
echo ""

FAIL_TAG=1
{ [ -z "$LOCAL_HIT" ] && [ -z "$REMOTE_HIT" ]; } && FAIL_TAG=0

# =============================================================================
# 查 ③ 工作区干净
# =============================================================================
PORCELAIN="$(git status --porcelain)"
STATUS_SCOPE="含未跟踪文件"
if [ "$ALLOW_UNTRACKED" = true ]; then
  PORCELAIN="$(printf '%s\n' "$PORCELAIN" | grep -v '^?? ' || true)"
  STATUS_SCOPE="忽略未跟踪文件（--allow-untracked）"
fi
DIRTY_COUNT="$(printf '%s\n' "$PORCELAIN" | grep -c . || true)"

echo "[3/3] 工作区干净检查（$STATUS_SCOPE）"
if [ "$DIRTY_COUNT" -eq 0 ]; then
  echo "      ✅ git status --porcelain 为空"
else
  echo "      ❌ 工作区不净（$DIRTY_COUNT 条）—— 拒绝发版：未收口的改动会被带进版本谱系"
  printf '%s\n' "$PORCELAIN" | grep -m 20 . | sed 's/^/         /'
  [ "$DIRTY_COUNT" -gt 20 ] && echo "         …（共 $DIRTY_COUNT 条，仅列前 20）"
  echo "      ⏳ 如何修：等改动链收口并提交，或先 stash / 清理；确认未跟踪文件与本仓发布物"
  echo "         无关时才用 --allow-untracked（默认严格：未跟踪文件同样计入）"
fi
echo ""

FAIL_DIRTY=1
[ "$DIRTY_COUNT" -eq 0 ] && FAIL_DIRTY=0

# =============================================================================
# 判定：任一不过即拒绝（优先级：在飞链 > 编号 > 工作区）
# =============================================================================
if [ "$FAIL_INFLIGHT" -ne 0 ] || [ "$FAIL_TAG" -ne 0 ] || [ "$FAIL_DIRTY" -ne 0 ]; then
  echo "⛔ 发版前置闸未通过（在飞链=$FAIL_INFLIGHT / 编号占用=$FAIL_TAG / 工作区不净=$FAIL_DIRTY，1=未过）"
  echo "   不进入 tag / push / GitHub Release / 净化包 任何一步。"
  [ "$FAIL_INFLIGHT" -ne 0 ] && exit "$EXIT_INFLIGHT"
  [ "$FAIL_TAG" -ne 0 ] && exit "$EXIT_TAG_TAKEN"
  exit "$EXIT_DIRTY"
fi

# ---- 通过：打印四行现状（远端 master / 本地 HEAD / tag 区间 / 在飞链）----
HEAD_SHA="$(git rev-parse --short HEAD)"
HEAD_TAG="$(git describe --tags --abbrev=0 HEAD 2>/dev/null || true)"

REMOTE_MASTER_SHA="$(printf '%s\n' "$REMOTE_OUT" | awk '$2 == "refs/heads/master" { print $1; exit }')"
REMOTE_BRANCH="master"
if [ -z "$REMOTE_MASTER_SHA" ]; then
  REMOTE_MASTER_SHA="$(printf '%s\n' "$REMOTE_OUT" | awk '$2 == "refs/heads/main" { print $1; exit }')"
  REMOTE_BRANCH="main"
fi

if [ -n "$REMOTE_MASTER_SHA" ]; then
  R_SHORT="$(git rev-parse --short "$REMOTE_MASTER_SHA" 2>/dev/null || printf '%s' "$REMOTE_MASTER_SHA" | cut -c1-7)"
  R_TAG="$(git describe --tags --abbrev=0 "$REMOTE_MASTER_SHA" 2>/dev/null || echo '（本地无此对象）')"
  COUNTS="$(git rev-list --left-right --count "HEAD...$REMOTE_MASTER_SHA" 2>/dev/null || echo '? ?')"
  AHEAD="$(printf '%s' "$COUNTS" | awk '{print $1}')"
  BEHIND="$(printf '%s' "$COUNTS" | awk '{print $2}')"
  REMOTE_MASTER_LINE="origin/$REMOTE_BRANCH = $R_SHORT（最近 tag $R_TAG）"
  HEAD_REL_LINE="，领先远端 ${AHEAD} 提交 / 落后 ${BEHIND} 提交"
else
  REMOTE_MASTER_LINE="远端未见 master/main（ls-remote 无输出？）"
  HEAD_REL_LINE=""
fi

comm -23 "$TMP_PF/local_tags.txt" "$TMP_PF/remote_tags.txt" > "$TMP_PF/local_only.txt" || true
comm -13 "$TMP_PF/local_tags.txt" "$TMP_PF/remote_tags.txt" > "$TMP_PF/remote_only.txt" || true
L_ONLY_N="$(grep -c . "$TMP_PF/local_only.txt" || true)"
R_ONLY_N="$(grep -c . "$TMP_PF/remote_only.txt" || true)"
L_ONLY_PREVIEW="$(grep -m 5 . "$TMP_PF/local_only.txt" | tr '\n' ' ' | sed 's/ $//' || true)"

echo "✅ 发版前置闸通过 —— 三查均过，可进入 tag / push / GitHub Release / 净化包"
echo "   ① 远端 master : $REMOTE_MASTER_LINE"
echo "   ② 本地 HEAD   : $HEAD_SHA（最近 tag $HEAD_TAG）$HEAD_REL_LINE"
echo "   ③ tag 区间    : 本地最近 $HEAD_TAG / 远端最近 ${R_TAG:-（无）}；本地独有 $L_ONLY_N 个（未推）${L_ONLY_PREVIEW:+［$L_ONLY_PREVIEW］} / 远端独有 $R_ONLY_N 个（未取）"
echo "   ④ 在飞链      : 0 条（同项目 status=${INFLIGHT_STATUSES} 会话）"
echo "   目标编号 $TAG：本地未占用 / 远端未占用；工作区干净"
exit "$EXIT_PASS"
