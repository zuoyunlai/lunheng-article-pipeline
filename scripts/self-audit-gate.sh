#!/usr/bin/env bash
# =============================================================================
# self-audit-gate.sh — 论衡自审门自动化执行脚本（v2.5.6 新增，教训 #175；v2.5.9 加门 H，教训 #180）
# =============================================================================
# 背景（教训 #175）：v2.5.5 发布前自审门 22 门**没真跑**（仅文档描述），导致
#   P0-1 #2 8 分钟硬卡散落 / P0-1 #3 T7 派发话术硬编码 / P0-2 M 门「机械化」名不副实 等
#   问题逃逸到发布版。v2.5.6 修订：把核心门从「文档」变「可执行脚本」。
#
# ⚠️ 门编号声明（v2.5.11 补，回应第三方全量审计 P0）：
#   本脚本的 8 门（A/B/C/D/E/F/G/H）是**当前生效的自审门权威**。
#   历史文档 references/_shared/版本升级自审门-v2.3.0.md 含 25 项历史门（A-W），
#   其中门 D/G/H 与本脚本同名不同义（本脚本门 D=8 分钟硬卡 / 门 G=双端 md5 / 门 H=教训差集），
#   以本脚本为准。详见该文档头部「现状权威声明」。
#
# 触发：commit 前由 sync-version.sh 末尾自动调用；或主控 LLM 主动跑
# 返回：exit 0 = 全过 / exit 1 = 有门失败 + 错误清单
# 依赖：bash + grep + md5sum（论衡 zero exec 哲学下所有工具都在白名单内）
# =============================================================================

# 不 set -e，因为 grep 无匹配时 exit 1 会让脚本意外退出

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

FAILED=()
PASSED=()
SKIPPED=()

# v2.13.x 审计修订（R-20）：门自身健康对账。
#   背景：门 S/T/U 曾因「条件注册且无 else」而**整门静默消失**（PASS 从 36 静默降到 31，
#   报告上看不出任何异常）；门 C 曾因 `grep -qF ""` 恒真而**空转绿灯**。两者同源——
#   **门的自身健康无人检查**。现口径：每个声明的门必须落在 PASS / FAIL / SKIP 三态之一，
#   SKIP 需带原因并计入配额（有 SKIP 即 warn：覆盖缩小 ≠ 全绿）。
SEEN_GATE_IDS=""

# 从消息前缀提取门标识（`门 X.4: ...` → `X`；子门归入父门）
_gate_id_of() {
  printf '%s' "$1" | grep -oE '门 [A-Za-z0-9]+' | head -1 | awk '{print $2}'
}

_record_gate_id() {
  local _id
  _id="$(_gate_id_of "$1")"
  [ -z "$_id" ] && return 0
  case " $SEEN_GATE_IDS " in
    *" $_id "*) ;;
    *) SEEN_GATE_IDS="${SEEN_GATE_IDS} ${_id}" ;;
  esac
}

pass() { PASSED+=("$1"); _record_gate_id "$1"; echo -e "${GREEN}✓${NC} $1"; }
fail() { FAILED+=("$1: $2"); _record_gate_id "$1"; echo -e "${RED}✗${NC} $1: $2"; }
# SKIP = 环境不满足致本门本轮不可执行（**不是** PASS，也**不是**静默消失）
skip() { SKIPPED+=("$1: $2"); _record_gate_id "$1"; echo -e "${YELLOW}⊘${NC} $1: SKIP — $2"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }

# 声明的门清单（顶层门：M.3/M.4 归 M，X.1-X.4 归 X）——门 0 以此对账，缺一即红
DECLARED_GATES=(A B C D E F G H I J K L M N O P Q R S T U V W X Y Z AA AB AC)

cd "$SKILL_ROOT" || exit

# =============================================================================
# 门 A：角色卡完整性（v2.7.0 实测 11 文件 = 10 角色：主控 2 文件 + T1-T9 九卡。
# 概念口径「11 张角色卡」= T0 主控 + T1-T7 + T8 终检 + T9 同行评审 + T9b 压力测试；物理 12 文件因主控拆 coordinator + 扩展职责两张）
# 2026-09-25 审计修订（R-24-2）：原判据**只查缺席不查多出** —— 目录里多出一个未被登记的角色卡
#   （如 `0A-临时卡.md`）本门照过，而门 C 的 VERSION_FILES 与 sync/check-version 清单都是白名单，
#   同样不报 ⇒ 「新增角色卡」这一动作当时无任何机械门覆盖。现补**反向差集**。
# =========================================================================
EXPECTED_AGENTS=("00-主控-coordinator.md" "00-主控-扩展职责.md" "01-文献检索-literature-scout.md" "02-数据检索-data-scout.md" "03-案例检索-case-scout.md" "04-分析-analyst.md" "05-写作-writer.md" "06-批判-critical-companion.md" "07-审计-auditor.md" "08-终检-final-inspector.md" "09-审稿-peer-reviewer.md" "09b-压力测试-owner.md")
ACTUAL_AGENTS=""
# v2.13.4：glob 改为 `0*-*.md` —— 原 glob（`0[0-9]-*`）会把 sync-version.sh 留在同目录的
# gitignore 备份 `.bak.<ts>` 当「多出未登记角色卡」判红（实测 2026-09-26 发版时踩到）。
# ⚠️ 不要收紧成 `0[0-9]-*.md`：那样 `0A-临时卡.md` 这类**真正的未登记角色卡**会被一起放走
#   （本仓反向注入测试 test_gate_a_still_catches_unregistered_role_card 实测抓到）。
# 现口径：形如 `0X-*.md` 的一律纳入反向差集；备份名不以 .md 结尾，天然排除。
for f in references/agents/0*-*.md; do
  [ -e "$f" ] || continue
  ACTUAL_AGENTS="${ACTUAL_AGENTS}$(basename "$f")"$'\n'
done
MISSING=()
for exp in "${EXPECTED_AGENTS[@]}"; do
  if ! echo "$ACTUAL_AGENTS" | grep -qF "$exp"; then
    MISSING+=("$exp")
  fi
done
EXTRA=()
while IFS= read -r act; do
  [ -z "$act" ] && continue
  found=0
  for exp in "${EXPECTED_AGENTS[@]}"; do
    if [ "$exp" = "$act" ]; then found=1; break; fi
  done
  [ "$found" -eq 0 ] && EXTRA+=("$act")
done <<EOF
$ACTUAL_AGENTS
EOF
if [ ${#MISSING[@]} -eq 0 ] && [ ${#EXTRA[@]} -eq 0 ]; then
  pass "门 A: 角色卡完整性（12 文件 / 11 角色，无未登记多出）"
elif [ ${#MISSING[@]} -gt 0 ]; then
  fail "门 A: 角色卡完整性" "缺失: ${MISSING[*]}"
else
  fail "门 A: 角色卡完整性" "多出未登记角色卡: ${EXTRA[*]}（新增角色卡须同步本清单 + 门 C 的 VERSION_FILES + sync/check-version 清单）"
fi

# =============================================================================
# 门 B：10 角色编号在 3 处文档全覆盖（README / SKILL / pipeline-readme）
# =============================================================================
# v2.12.40 修复（教训 #150 同族·假绿灯，2026-09-14 实测）：旧写法 `grep -c "$r" f || echo 0`
#   在**零命中**时 grep -c 仍打印 "0" 且退出码 1 ⇒ 命令替换产出 "0\n0" ⇒
#   `[ "0\n0" -lt 2 ]` 报「需要整数表达式」并以状态 2 退出（= false）⇒ 该角色**不进入缺失清单**。
#   后果：三处文档**内容全缺**时门 B 反而 PASS（门 B 假绿灯；同族于门 S/门 T 假绿灯与 #150）。
#   现口径：`grep -c -- ... || true` 只取标准输出，再用 case 强制「非负整数」，
#   零命中/非数值一律归一为 0（按「缺内容」处理，而不是当作通过）。
count_role_hits() {
  local n
  n="$(grep -c -- "$1" "$2" 2>/dev/null || true)"
  case "$n" in
    ''|*[!0-9]*) n=0 ;;
  esac
  printf '%s' "$n"
}

ROLE_NUMS=("T1" "T2" "T3" "T4" "T5" "T6" "T7" "T8" "T9")
ROLE_MISSING=""
for r in "${ROLE_NUMS[@]}"; do
  IN_README=$(count_role_hits "$r" README.md)
  IN_SKILL=$(count_role_hits "$r" SKILL.md)
  IN_PIPE=$(count_role_hits "$r" references/pipeline-readme.md)
  if [ "$IN_README" -lt 2 ] || [ "$IN_SKILL" -lt 2 ] || [ "$IN_PIPE" -lt 3 ]; then
    ROLE_MISSING="$ROLE_MISSING $r(README=$IN_README SKILL=$IN_SKILL pipe=$IN_PIPE)"
  fi
done
if [ -z "$ROLE_MISSING" ]; then
  pass "门 B: 11 角色编号 README/SKILL/pipeline 三处覆盖"
else
  fail "门 B: 角色编号覆盖不全" "$ROLE_MISSING"
fi

# =============================================================================
# 门 C：版本号一致性（36 文件清单 = SKILL.md + 8 角色卡 + 闸门 + 检测器 + 共享协议 + 模板 + README + QUICKSTART）
# =============================================================================
EXPECTED_VERSION=$(grep -m1 -E '^[[:space:]]*version:' SKILL.md | sed -E 's/^[[:space:]]*version:[[:space:]]*//;s/["'"'"']//g;s/[[:space:]]*$//')
# v2.13.x 审计修订（R-05）：**空转守卫**。原实现下，一旦 SKILL.md frontmatter 的 `version:` 键被删/改名
#   （或被写成无值），EXPECTED_VERSION 为空串，而下方判据用的是 `grep -qF "$EXPECTED_VERSION"` ——
#   `grep -qF ""` **恒真**（空模式匹配任意行）⇒ 本门输出「✓ 门 C: 56 文件版本号 v 一致」并 PASS。
#   即：唯一真源损坏时，专门守护该真源的门变成 no-op（2026-09-25 审计探针实测复现）。
#   现口径：读不到版本号 = **本门不可判定** ⇒ fail（不是 pass，也不是静默跳过）。
if [ -z "$EXPECTED_VERSION" ]; then
  fail "门 C: 版本号一致性" "SKILL.md frontmatter 无 version（读版本为空 ⇒ 本门不可判定，不允许空转绿灯）；修法：恢复 metadata.openclaw.version，或修正缩进读法"
fi
VERSION_FILES=(
  "SKILL.md" "README.md" "QUICKSTART.md"
  "references/_shared/真源/glossary-full.md" "references/pipeline-readme.md"
  "references/deliverables.md" "references/case-studies.md"
  "references/operations.md" "references/errors.md"
  "references/agents/00-主控-coordinator.md"
  "references/agents/00-主控-扩展职责.md"
  "references/agents/01-文献检索-literature-scout.md"
  "references/agents/02-数据检索-data-scout.md"
  "references/agents/03-案例检索-case-scout.md"
  "references/agents/04-分析-analyst.md"
  "references/agents/05-写作-writer.md"
  "references/agents/06-批判-critical-companion.md"
  "references/agents/07-审计-auditor.md"
  "references/agents/08-终检-final-inspector.md"
  "references/agents/09-审稿-peer-reviewer.md"
  "references/agents/09b-压力测试-owner.md"
  "references/_shared/真源/M-Gate-Algorithm.md"
  "references/_shared/真源/M-Gate-核心.md"
  "references/_shared/真源/M-Gate-背景.md"
  "references/_shared/真源/M-Gate-Algorithm-appendix.md"
  "references/_shared/真源/audit-checklist-quickref.md"
  "references/_shared/真源/failure-modes.md"
  "references/_shared/真源/degraded-scenarios.md"
  "references/_shared/真源/字数判定表.md"
  "references/_shared/真源/期刊数据库.md"
  "references/_shared/真源/期刊匹配算法.md"
  "references/_shared/真源/中文数据源集成.md"
  "references/_shared/真源/format-export.md"
  "references/_shared/真源/执行韧化协议-exec.md"
  "references/_shared/真源/执行韧化协议-design.md"
  "references/gates/14-中文AI痕迹-gate.md"
  "references/checkers/中文AI痕迹-checker.md"
  "references/templates/任务简报-template.md"
  "references/templates/审稿报告-template.md"
  "references/templates/G14检测报告-template.md"
  "references/templates/status-template.md"
  "references/templates/投稿就绪检查表-template.md"
  "references/templates/修订说明-template-full.md"
  "references/templates/案例卡-template.md"
  "references/templates/数据卡-template.md"
  "references/templates/文献卡-template.md"
  "references/templates/先行者清单-template.md"
  "references/templates/交接报告-template.md"
  "references/templates/图表-SVG-template.md"
  "references/_shared/真源/工具能力边界.md"
  "references/_shared/真源/关键协议.md"
  "references/_shared/治理/教训索引.md"
  "references/_shared/真源/模型候选池.md"
  # v2.12.14 SKILL.md 瘦身外移文件（批次 4.6/4B）
  "references/_shared/真源/pipeline-overview.md"
  "references/_shared/真源/asset-index.md"
  "references/_shared/真源/external-services.md"
  # v2.12.59：补上审计发现的悬空指针目标文件（原被 2 处活文档引用却从未存在）
  "references/_shared/真源/host-verify-recipe.md"
  "references/_shared/治理/反哺报告处理.md"
  # v2.12.67：性能基准表（审计 P1-2）——版本戳第三处载体登记（sync / check-version 已先行登记）
  "references/_shared/真源/performance-benchmarks.md"
)
VERSION_MISSING=""
for f in "${VERSION_FILES[@]}"; do
  if [ ! -f "$f" ]; then
    VERSION_MISSING="$VERSION_MISSING [missing:$f]"
    continue
  fi
  # 边界匹配（R-05-2）：原 `grep -qF v2.13.3` 是**子串**匹配，版本戳 `v2.13.30` / `v2.13.31` 会被当作
  # `v2.13.3` 通过（前缀吞噬）。改为要求版本串后紧跟非数字字符或行尾。
  if ! head -10 "$f" | grep -qE "v?${EXPECTED_VERSION}([^0-9]|$)"; then
    VERSION_MISSING="$VERSION_MISSING [$f]"
  fi
done
if [ -n "$EXPECTED_VERSION" ] && [ -z "$VERSION_MISSING" ]; then
  pass "门 C: ${#VERSION_FILES[@]} 文件版本号 v$EXPECTED_VERSION 一致"
elif [ -z "$EXPECTED_VERSION" ]; then
  : # 上方空转守卫已 fail，此处不重复计数
else
  fail "门 C: 版本号不一致" "期望 v$EXPECTED_VERSION, 不一致:$VERSION_MISSING"
fi

# =============================================================================
# 门 AB：正文版本一致性（R-60）
# 判据唯一真源 = tests/test_audit_residuals.py；本门只触发，不复制正则。
# 缺少 python3/pytest 或任一测试失败均 fail-closed，不得静默跳过。
# =============================================================================
if command -v python3 >/dev/null 2>&1; then
  if python3 -m pytest -q \
    tests/test_audit_residuals.py::test_readme_prose_version_matches_frontmatter \
    tests/test_audit_residuals.py::test_skill_body_version_header_matches_frontmatter \
    >/tmp/lunheng-gate-ab.out 2>&1; then
    pass "门 AB: 正文版本一致性（README/SKILL.md == frontmatter）"
  else
    fail "门 AB: 正文版本一致性" "升版后正文版本一致性门失败：$(tail -3 /tmp/lunheng-gate-ab.out | tr '\\n' '|')"
  fi
else
  fail "门 AB: 正文版本一致性" "缺少 python3，正文版本一致性门不可判定"
fi

# =============================================================================
# 门 D：禁止「8 分钟硬卡」散落（v2.5.5 P0-1 #2 教训，v2.5.6 修正）
# =============================================================================
# 搜索所有 .md 文件「8 分钟硬卡」/「超时会被主控 kill」等过时表述
# 例外：主控卡 §二十二「硬卡阈值表 v2.5.5 P0 硬性化，原 8 分钟改为角色分级阈值」（已升级）
# 例外：changelog 历史段（v2.1.0/v2.1.1/v2.2.x 的版本演进日志，讲历史事件）
# 检测规则：跳过包含「v2.5.5 P0 硬性化」或「历史段」的行
STALE_8MIN=""
for f in SKILL.md references/pipeline-readme.md references/agents/00-主控-coordinator.md references/agents/00-主控-扩展职责.md; do
  # 只检活文档段（跳过前 60 行 changelog 历史）
  # 跳过已升级表述：「v2.5.5 P0 硬性化」/「v2.3.13 能力抽象」/「改为角色分级」/「硬卡放宽」/「实战教训」/「changelog」
  # 允许表内阈值（如 G14 8 分钟 = 实际硬卡阈值）
  # 允许目录锚点（带 [] 的 markdown 链接文本）
  # 允许「硬卡阈值表」表格行（G14 = 8 分钟 是合法阈值）
  # 允许「实战教训」/「实战中 T3 连续」段
  # 允许「实战背景」/「任一行停留超硬卡阈值」已修订表述
  # 允许「模型 fallback v2.5.6 P1-3 修订，去硬编码」段（含「claude-opus-5 静默无响应」反例）
  HITS=$(awk 'NR > 60' "$f" 2>/dev/null | grep -E '8 分钟|超时' | grep -v '\[.*\](#' | grep -v "已废弃" | grep -v "v2.5.5 P0 硬性化" | grep -v "v2.3.13 能力抽象" | grep -v "改为角色分级" | grep -v "硬卡放宽" | grep -v "实战教训" | grep -v "实战中 T3 连续" | grep -v "changelog" | grep -v "硬卡阈值表" | grep -v "P0 硬性化" | grep -v "| 角色" | grep -v "| G14 检测" | grep -v "T 派发后 8 分钟内未出产物" | grep -v "任一行停留超硬卡阈值" | grep -v "实战背景" | grep -v "v2.5.6 P1-3 修订" | grep -v "重跑论衡首单测试" | grep -v "超 8 分终" | grep -v "超 8 分静" | grep -v "超时 ≠ 零产物")
  if [ -n "$HITS" ]; then
    STALE_8MIN="$STALE_8MIN [$f]"
  fi
done
if [ -z "$STALE_8MIN" ]; then
  pass "门 D: 超时硬卡阈值表述一致性（v2.5.5 分级化，v2.7.2 文案对齐）"
else
  fail "门 D: 8 分钟硬卡散落" "需诚实化文档:$STALE_8MIN"
fi

# =============================================================================
# 门 E：禁止硬编码模型 ID（v2.5.5 P1-3 教训，v2.5.6 修正）
# =============================================================================
# SKILL.md 候选池硬编码 5 个 DSH 模型 ID（deepseek-v4-flash/glm-4-flash/qwen3-coder/minimax-m3/claude-opus-5）
# v2.5.6 修订：改为「能力档 = 描述性」，不绑定具体模型 ID
HARDCODED_MODELS=""
# 检查 SKILL.md 候选池表格行（跳过 changelog 与「v2.5.6 修订前」诚实化上下文）
if awk 'NR > 60' SKILL.md 2>/dev/null | grep -E 'deepseek-v4-flash.*glm-4-flash.*qwen3-coder' | grep -v "v2.5.6 修订前" | head -1 | grep -q .; then
  HARDCODED_MODELS="[SKILL.md]"
fi
# 检查 references/agents/ + _shared/ 候选池表格行
for f in references/agents/*.md references/_shared/真源/*.md references/_shared/治理/*.md; do
  HITS=$(awk 'NR > 60' "$f" 2>/dev/null | grep -E 'deepseek-v4-flash.*glm-4-flash.*qwen3-coder|minimax-M3.*deepseek-v4-pro.*claude-opus-5' | grep -v "v2.5.6 修订前" | grep -v "changelog" | grep -v "v2.3.13" | head -1)
  if [ -n "$HITS" ]; then
    HARDCODED_MODELS="$HARDCODED_MODELS [$f]"
  fi
done
if [ -z "$HARDCODED_MODELS" ]; then
  pass "门 E: 硬编码模型 ID 检查（v2.5.6 P1-3 修正）"
else
  fail "门 E: 硬编码模型 ID" "$HARDCODED_MODELS"
fi

# =============================================================================
# 门 F：M 门「机械化」诚实化（v2.5.5 P0-2 教训，v2.5.6 修正）
# =============================================================================
# M-Gate-核心.md 头部必明示「LLM 推理判定，非机器强制」
M_GATE_MISSING=""
if ! grep -qE 'M 门.*LLM 推理|LLM 推理判定.*M 门' references/_shared/真源/M-Gate-核心.md 2>/dev/null; then
  M_GATE_MISSING="[M-Gate-核心.md 缺诚实声明]"
fi
if [ -z "$M_GATE_MISSING" ]; then
  pass "门 F: M 门「机械化」诚实声明（v2.5.6 P0-2 修正）"
else
  fail "门 F: M 门缺诚实声明" "$M_GATE_MISSING"
fi

# =============================================================================
# 门 H：教训编号引用 vs 登记表差集（v2.15.9 重写 —— hermetic 单点真源，无 SKIP）
# -----------------------------------------------------------------------------
# 历史：v2.5.9 原始实现依赖仓库外主真源 memory/lessons.md 做正向差集 ⇒ 长期 SKIP
#   （2026-10-03 全量审计 P1：29 门中唯一常态化覆盖缺口）。
#   主真源 2026-09-26 / 09-28 两次被整文件覆写（教训 #474/#461），#180-#472 原文
#   不可恢复，「从未定义」与「已知销毁」在外部真源上已不可区分。
#   v2.15.9 正解（登记表 = references/_shared/治理/lessons-registry.md §一a 区间）：
#     · 判据① 仓库引用全查 —— 每个「教训 #N」引用按登记表三态判定：
#       永久空档（§二）⇒ FAIL；可引用区间（§一a）⇒ PASS；其余 ⇒ FAIL（缺登记）；
#     · 判据④ 登记表自洽 —— 三区间键可解析 + alive 上界 == 快照值（防 off-by-one）；
#     · SKIP 路径移除；CI / 本地同口径；LESSONS_SRC 降格为**可选参照告警**
#       （外部真源最大未排除编号 > 快照 ⇒ warn，不参与 exit code）。
#   登记表更新纪律（同批五件套）见该文件 §五；禁止凭印象编造已蒸发区间的标题。
# =============================================================================
LESSONS_SRC="${LESSONS_SRC:-}"
LUNHENG_LESSON_EXCLUDE="${LUNHENG_LESSON_EXCLUDE:-340 341 355 374 375 376 380 382 383 385 392 393 394 395 396 397 398 402 403 404 405 410 411 412 413 414}"
# v2.12.62（审计 P2-7）：**编号只在快照写一次**。索引三处旧副本已于本版改为派生指针；
#   本门保留「索引**不得**出现硬编码最大编号」判据（下方双判据块）。LUNHENG_LESSON_INDEX 供测试注入副本。
LESSON_INDEX_FILE="${LUNHENG_LESSON_INDEX:-references/_shared/治理/教训索引.md}"
IDX_HARDCODED_COUNT=$(grep -cE '最大编号 \*\*#[0-9]+\*\*' "$LESSON_INDEX_FILE" 2>/dev/null | tr -d '[:space:]')
IDX_HARDCODED_COUNT=${IDX_HARDCODED_COUNT:-0}
SNAPSHOT_FILE="${LESSONS_SNAPSHOT:-references/_shared/治理/lessons-max.snapshot}"
SNAP_MAX=$(grep -oE '[0-9]+' "$SNAPSHOT_FILE" 2>/dev/null | head -1)
REGISTRY_FILE="${LUNHENG_LESSON_REGISTRY:-references/_shared/治理/lessons-registry.md}"

# ---- 判据① + ④：引用全查（登记表区间判定）+ 登记表自洽（python 单源解析）----
# 解析与判定都在 python 里完成（bash 字符串手术是 sed -i 教训 #265 的重灾区）。
# 采集面与 v2.5.9 起一致：references/ scripts/ SKILL.md README.md QUICKSTART.md 的
# 「教训 #N」引用 + 教训索引表格裸「| #N |」列（教训 #249），排除 .bak。
if command -v python3 >/dev/null 2>&1; then
  GATE_H_OUT="$(python3 - "$REGISTRY_FILE" "$LESSON_INDEX_FILE" "$SNAP_MAX" "$LESSONS_SRC" "$LUNHENG_LESSON_EXCLUDE" <<'PYEOF'
import re, subprocess, sys

registry_path, index_path, snap_max, lessons_src, exclude_raw = sys.argv[1:6]
exclude = {int(x) for x in exclude_raw.split()}

# --- 登记表解析（判据④）---
try:
    reg = open(registry_path, encoding="utf-8").read()
except OSError:
    print("REFS_FAIL\t登记表缺失: " + registry_path); sys.exit(0)

def parse_ranges(key):
    m = re.search(rf"^\s*{key}:\s*\[(.*)\]\s*$", reg, re.M)
    if not m:
        return None
    ranges = []
    for tok in m.group(1).split(","):
        tok = tok.strip().strip('"').strip("'")
        if not tok:
            continue
        if "-" in tok:
            a, b = tok.split("-", 1)
            ranges.append((int(a), int(b)))
        else:
            ranges.append((int(tok), int(tok)))
    return ranges or None

evap = parse_ranges("evaporated_ok")
alive = parse_ranges("alive")
gaps = parse_ranges("permanent_gaps")
if evap is None or alive is None or gaps is None:
    print("REFS_FAIL\t登记表不可解析（§一a 区间键 evaporated_ok/alive/permanent_gaps 缺一或为空）: " + registry_path); sys.exit(0)

ok_set = set()
for a, b in evap + alive:
    ok_set.update(range(a, b + 1))
gap_set = set()
for a, b in gaps:
    gap_set.update(range(a, b + 1))
alive_max = max(b for _, b in alive)

# --- 引用采集（与旧门同口径）---
refs_raw = subprocess.run(
    ["grep", "-rhoE", r"教训 #[0-9]+",
     "--include=*.md", "--include=*.sh", "--include=*.py", "--exclude=*.bak*",
     "references/", "scripts/", "SKILL.md", "README.md", "QUICKSTART.md"],
    capture_output=True, text=True).stdout
refs = {int(n) for n in re.findall(r"[0-9]+", refs_raw)}
try:
    idx_raw = open(index_path, encoding="utf-8").read()
    refs |= {int(n) for n in re.findall(r"^\| #(\d+) ", idx_raw, re.M)}
except OSError:
    pass

# --- 判据基自洽：alive 上界 == 快照值（两处数字同批改，教训 #352）---
if snap_max and int(alive_max) != int(snap_max):
    print(f"REFS_FAIL\t登记表 alive 上界 #{alive_max} != 快照 #{snap_max}（同批五件套，登记表 §五-2）")
    sys.exit(0)

# --- 判据①：三态判定（N >= 115 才检；#1-#114 已归档）---
missing, gap_hits = [], []
for n in sorted(refs):
    if n < 115:
        continue
    if n in gap_set:
        gap_hits.append(n)
    elif n not in ok_set:
        missing.append(n)

checked = sum(1 for n in refs if n >= 115)
if gap_hits or missing:
    parts = []
    if gap_hits:
        parts.append("永久空档被引用: " + " ".join(f"#{n}" for n in gap_hits))
    if missing:
        parts.append("缺登记: " + " ".join(f"#{n}" for n in missing))
    print("REFS_FAIL\t" + "; ".join(parts))
else:
    print(f"REFS_OK\t{checked} 个编号全过；登记表三区间可解析，alive #{alive_max} = 快照 #{snap_max}")

# --- 参照告警（可选，不参与 exit code）：外部真源最大未排除编号 > 快照 ---
if lessons_src:
    try:
        src_text = open(lessons_src, encoding="utf-8").read()
        src_nums = [int(n) for n in re.findall(r"^#{2,4} (?:教训 )?#(\d+)", src_text, re.M)]
        src_max = max((n for n in src_nums if n not in exclude), default=0)
        if snap_max and src_max > int(snap_max):
            print(f"ADVISORY\t#{src_max}")
    except OSError:
        pass
PYEOF
)"
  GATE_H_REFS_VERDICT="$(printf '%s\n' "$GATE_H_OUT" | grep -E '^REFS_' | head -1 | cut -f1)"
  GATE_H_REFS_DETAIL="$(printf '%s\n' "$GATE_H_OUT" | grep -E '^REFS_' | head -1 | cut -f2-)"
  GATE_H_ADVISORY="$(printf '%s\n' "$GATE_H_OUT" | grep -E '^ADVISORY' | head -1 | cut -f2-)"

  case "$GATE_H_REFS_VERDICT" in
    REFS_OK)     pass "门 H: 教训编号引用全部在登记表有定义（$GATE_H_REFS_DETAIL）" ;;
    REFS_FAIL)   fail "门 H: 教训引用与登记表不一致" "$GATE_H_REFS_DETAIL —— 补登记（references/_shared/治理/lessons-registry.md §一a）或修正引用；永久空档不回收" ;;
    *)            fail "门 H: 引用全查未执行（python 判定器无输出）" "本门不可判定（不允许静默跳过）；检查 python3 与登记表" ;;
  esac

  if [ -n "$GATE_H_ADVISORY" ]; then
    warn "门 H: 外部真源 $GATE_H_ADVISORY > 快照 #$SNAP_MAX —— 若属论衡类，请同步 快照 + 登记表 + 索引 + 排除表（同批五件套）"
  fi
else
  fail "门 H: 引用全查未执行（缺 python3）" "本门不可判定（不允许静默跳过；v2.15.9 起门 H 无 SKIP 路径）"
fi

# -----------------------------------------------------------------------------
# 反向差集（官方审计 F1/F3 整改）：判据 = **仓库内快照**（hermetic），不受外部漂移影响
#   原判据依赖仓库外 memory/lessons.md → 「已发布的绿」可被墙外追加追溯性推翻
#   （实测：宿主类教训 #355 续录后 HEAD 由绿转红）。现口径：
#     ① 索引声明编号 ≥ 仓库快照编号 → PASS
#     ② 外部真源可达且更大 → 上方仅 warn（不参与 exit code）
#   宿主/通用类教训请加入 LUNHENG_LESSON_EXCLUDE（#340/#341/#355），勿放宽本门。
#   📌 快照更新纪律（2026-09-13 官方复查补）：快照值 = 最近一次核对主真源时论衡类最大编号；
#   更新时机 = 主真源新增论衡类教训 / 索引声明变化 / 新增宿主类（后者走排除表不推高快照）。
#   三者同批改（本值 + 索引声明 + 排除表，教训 #352）；快照只升不降。完整条文见 snapshot 文件头。
#   提醒器 = 本门参照告警「外部真源 #N > 快照 #M」——它响就是快照该更新了。
# -----------------------------------------------------------------------------
# 双判据（v2.12.62 改，审计 P2-7「5 处联动 → 压到 2 处」）：
#   ① 单点真源在位：快照必须可解析 —— 编号唯一载体消失了就没有任何真源；
#   ② 派生面无副本：索引不得出现硬编码最大编号 —— 出现即 FAIL（防 5 处联动回归）。
#   （旧判据「索引声明 ≥ 快照」比的是两处**人工维护**的数字，正是 off-by-one 的来源；
#     现判据把这个类别**从结构上移除**：没有第二处数字，就没有第二处可漂移。）
if [ -n "$SNAP_MAX" ]; then
  pass "门 H: 快照单一真源可解析（lessons-max.snapshot = #$SNAP_MAX）"
else
  fail "门 H: 教训快照不可解析" "$SNAPSHOT_FILE 无数字头 —— 编号唯一真源缺失（门 H 失去判据基）"
fi
if [ "$IDX_HARDCODED_COUNT" -eq 0 ]; then
  pass "门 H: 教训索引无硬编码最大编号（编号已压到 2 处：快照 + 派生）"
else
  fail "门 H: 教训索引又出现硬编码最大编号（$IDX_HARDCODED_COUNT 处）" \
       "$LESSON_INDEX_FILE —— 编号只在 lessons-max.snapshot 写一次；索引三处旧副本已于 v2.12.62 改为指针，请勿回退（审计 P2-7）"
fi

# =============================================================================
# 门 I：dispatch 派发话术 vs 角色卡「产出结构级」差集（v2.5.16 新增，教训 #183 延伸）
# -----------------------------------------------------------------------------
# 背景：v2.5.6 把 pipeline-readme 派发话术拆成 dispatch/ 10 文件时，**没做
#   「派发话术 vs 角色卡」差集校验**，导致过时内容被原样搬进 dispatch，成「冻结旧版」：
#   - v2.5.14 修图表链路（T4 建议图表 / T5 图位标注 / T7 图位核验）
#   - v2.5.15 修 T6 C1-C7 七维只写五维 + T1/T2/T3/T9 必填字段漏
#   根因同一：拆分动作做完，「把新结构登记进 dispatch」的动作忘了。
# 方法：grep 每个角色卡的「产出结构级」关键词（产出文件/必填字段/维度编号），
#   检查对应 dispatch 是否含。角色卡有、dispatch 无 = fail。
#   只检「产出结构级」（改变产物结构的东西），不检铁律细节——
#   dispatch 是「最小派发话术」，铁律细节靠子代理「先读角色卡」补，但产出结构不能省。
# =============================================================================
DISPATCH_CHECK_FAIL=""
# 格式：角色卡路径|dispatch路径|逗号分隔的产出结构级关键词
DISPATCH_CHECKS=(
  "references/agents/01-文献检索-literature-scout.md|references/dispatch/T1-文献检索.md|先行者清单,信任级别,可信度等级"
  "references/agents/02-数据检索-data-scout.md|references/dispatch/T2-数据检索.md|信任级别,时效评级"
  "references/agents/03-案例检索-case-scout.md|references/dispatch/T3-案例检索.md|信任级别,多方说法"
  "references/agents/04-分析-analyst.md|references/dispatch/T4-分析.md|建议图表,原创性"
  "references/agents/05-写作-writer.md|references/dispatch/T5-写手.md|图位"
  "references/agents/06-批判-critical-companion.md|references/dispatch/T6-批判.md|C6,C7"
  "references/agents/07-审计-auditor.md|references/dispatch/T7-审计.md|图位,反哺报告"
  "references/agents/09-审稿-peer-reviewer.md|references/dispatch/T9-同行评审.md|扩写清单,建议元数据"

  # v2.5.18 token 消耗三级降级（宿主无关设计，所有角色 dispatch 都要含）
  "references/agents/01-文献检索-literature-scout.md|references/dispatch/T1-文献检索.md|token 消耗,三级降级"
  "references/agents/02-数据检索-data-scout.md|references/dispatch/T2-数据检索.md|token 消耗,三级降级"
  "references/agents/03-案例检索-case-scout.md|references/dispatch/T3-案例检索.md|token 消耗,三级降级"
  "references/agents/04-分析-analyst.md|references/dispatch/T4-分析.md|token 消耗,三级降级"
  "references/agents/05-写作-writer.md|references/dispatch/T5-写手.md|token 消耗,三级降级"
  "references/agents/06-批判-critical-companion.md|references/dispatch/T6-批判.md|token 消耗,三级降级"
  "references/agents/07-审计-auditor.md|references/dispatch/T7-审计.md|token 消耗,三级降级"
  "references/agents/09-审稿-peer-reviewer.md|references/dispatch/T9-同行评审.md|token 消耗,三级降级"
)
for entry in "${DISPATCH_CHECKS[@]}"; do
  IFS='|' read -r card disp kws <<< "$entry"
  card_full="$SKILL_ROOT/$card"
  disp_full="$SKILL_ROOT/$disp"
  [ ! -f "$card_full" ] && continue
  if [ ! -f "$disp_full" ]; then
    DISPATCH_CHECK_FAIL="$DISPATCH_CHECK_FAIL [缺dispatch文件:$disp]"
    continue
  fi
  card_text=$(cat "$card_full" 2>/dev/null)
  disp_text=$(cat "$disp_full" 2>/dev/null)
  IFS=',' read -ra kwarr <<< "$kws"
  missing_kws=""
  for kw in "${kwarr[@]}"; do
    # 角色卡含该关键词，但 dispatch 不含 → 漏项
    if echo "$card_text" | grep -qF "$kw"; then
      if ! echo "$disp_text" | grep -qF "$kw"; then
        missing_kws="$missing_kws $kw"
      fi
    fi
  done
  if [ -n "$missing_kws" ]; then
    DISPATCH_CHECK_FAIL="$DISPATCH_CHECK_FAIL [$disp 缺:$missing_kws]"
  fi
done
if [ -z "$DISPATCH_CHECK_FAIL" ]; then
  pass "门 I: dispatch 派发话术 vs 角色卡「产出结构级」关键词无差集（8 角色）"
else
  fail "门 I: dispatch 漏产出结构级关键词" "$DISPATCH_CHECK_FAIL"
fi

# =============================================================================
# 门 J：M 门 + T6 + T7 核验范围 = 全部产出物类型（v2.5.17 新增，教训 #184 + #183）
# -----------------------------------------------------------------------------
# 背景：v2.5.13 实战复盘“93% 补集错误”根因——论衡核验范围默认只覆盖 .md 正文，
#   SVG / 图件 / 未来新增的产出物类型均被排除在 M 门 + T6 + T7 外。
#   这正是「检查滞后」根因：流水线产出物演进（v2.0.5 仅 .md → v2.2.8 加 .svg
#   → v2.5.13 加图件 PDF/PNG），核验规则没同步跟进。
# 方法：grep M-Gate 算法文档 + T6/T7 dispatch 中是否含「final/图件」「SVG」
#   等产出物扩展点；未含 = fail。
# 与门 I 区别：门 I 是「dispatch 写了什么」差集，门 J 是「核验范围覆盖什么」检查。
# =============================================================================
VERIFY_SCOPE_FAIL=""
# 核验范围文件清单：M 门 + T6/T7 dispatch
VERIFY_SCOPE_FILES=(
  "references/_shared/真源/M-Gate-核心.md:M-Gate算法"
  "references/dispatch/T6-批判.md:T6"
  "references/dispatch/T7-审计.md:T7"
)
# 必须含产出物范围扩展关键词（v2.5.17 新增）
REQUIRED_SCOPE_KEYWORDS="(SVG|图件|内嵌)"
for entry in "${VERIFY_SCOPE_FILES[@]}"; do
  IFS=':' read -r path label <<< "$entry"
  full="$SKILL_ROOT/$path"
  [ ! -f "$full" ] && continue
  if ! grep -qE "$REQUIRED_SCOPE_KEYWORDS" "$full" 2>/dev/null; then
    VERIFY_SCOPE_FAIL="$VERIFY_SCOPE_FAIL [$label 未提及 SVG/图件核验范围]"
  fi
done
if [ -z "$VERIFY_SCOPE_FAIL" ]; then
  pass "门 J: M 门 + T6 + T7 核验范围含 SVG/图件扩展（v2.5.17 + 教训 #184）"
else
  fail "门 J: 核验范围未覆盖 SVG/图件产出物" "$VERIFY_SCOPE_FAIL"
fi

# =============================================================================
# 门 K：dispatch 引用教训编号 vs 对应角色卡（v2.5.22 新增，2026-08-26）
# -----------------------------------------------------------------------------
# 背景（门 I 盲区）：门 I 只查「dispatch 漏了角色卡有的关键词」（漏项），不查
#   「dispatch 引用了角色卡已删铁律的教训编号」（多余引用）。结构性漂移的两个方向：
#   - 角色卡改了/删了铁律 A → dispatch 还引用 A 的教训编号 = 冻结旧版
#   - v2.5.21 实战正是「角色卡有 16 项、dispatch 只抄了 9 项」漏项；本门补另一向。
# 方法：提取每个 dispatch 引用的「教训 #N」编号，检查是否在「对应角色卡」或
#   「该 dispatch 自身正文」中出现（dispatch 自己也会新增教训）。
#   dispatch 引用、但角色卡和 dispatch 正文都没有 = 疑似孤儿引用 = fail。
# 说明：软边界——教训编号可能在「全局文档」（glossary/pipeline-readme/M 门）
#   而非单角色卡出现，故额外并入全局引用集做白名单，避免误报。
# =============================================================================
GATE_K_FAIL=""
# 先建「全局教训引用集」：所有非 dispatch 文件引用的教训编号（白名单）
GLOBAL_LESSON_REFS=$(grep -rhoE '教训 #[0-9]+' \
    --include="*.md" --include="*.sh" \
    --exclude="*.bak*" \
    references/agents/ references/_shared/ references/gates/ \
    references/_shared/真源/glossary-full.md references/_shared/真源/glossary-core.md references/pipeline-readme.md references/operations.md \
    references/design*.md references/设计文档*.md \
    SKILL.md README.md QUICKSTART.md 2>/dev/null \
  | grep -oE '[0-9]+' | sort -un | tr '\n' ' ')

for disp in "$SKILL_ROOT"/references/dispatch/*.md; do
  [ -f "$disp" ] || continue
  disp_name=$(basename "$disp")
  # 跳过无对应角色卡的特殊文件（G14 对应 gate，T8 对应主控卡）
  # 全部 10 个 dispatch 都有权威源注解（v2.5.22 已加），按注解取权威源
  auth_src=$(grep -m1 '权威源：' "$disp" 2>/dev/null | sed -E 's/.*权威源：([^（(]+).*/\1/' | xargs)
  # dispatch 引用的教训编号
  disp_refs=$(grep -oE '教训 #[0-9]+' "$disp" 2>/dev/null | grep -oE '[0-9]+' | sort -un)
  [ -z "$disp_refs" ] && continue
  # 权威源（角色卡）的教训编号
  if [ -n "$auth_src" ] && [ -f "$SKILL_ROOT/$auth_src" ]; then
    card_refs=$(grep -oE '教训 #[0-9]+' "$SKILL_ROOT/$auth_src" 2>/dev/null | grep -oE '[0-9]+' | sort -un | tr '\n' ' ')
  else
    card_refs=""
  fi
  orphan=""
  for n in $disp_refs; do
    # 在权威源 OR 全局白名单 中 → 合法
    if echo "$card_refs" | grep -qw "$n"; then
      continue
    fi
    if echo "$GLOBAL_LESSON_REFS" | grep -qw "$n"; then
      continue
    fi
    orphan="$orphan #$n"
  done
  if [ -n "$orphan" ]; then
    GATE_K_FAIL="$GATE_K_FAIL [$disp_name 孤儿教训引用:$orphan]"
  fi
done

if [ -z "$GATE_K_FAIL" ]; then
  pass "门 K: dispatch 教训引用均可在权威源或全局文档溯源（10 文件）"
else
  fail "门 K: dispatch 引用孤儿教训编号（角色卡已删/全局无）" "$GATE_K_FAIL"
fi

# =============================================================================
# 门 L：M 门算法引用完整性 + JSON 产出可执行性（v2.5.22 新增，2026-08-26）
# -----------------------------------------------------------------------------
# 背景（v2.5.22 主人核查发现）：
#   M 门是论衡三大防线之首，13 项规则（M-Form×8 / M-Exist×3 / M-Integrity×2）
#   描述在 references/_shared/真源/M-Gate-核心.md。但门 F 只检查"LLM 推理诚实
#   声明"，不检查算法自身一致性也不检查应用文档是否同步。教训 #187 同型。
#
#   更严重：M-Gate-Report JSON 产出 = LLM 主动 write，零触发器保证——实战中
#   「T8 跑完 M 门」等于「主控自陈跑过」（教训 #150/#177 同型）。
#
# 查两项：
#   1. 跨文档 M 门项数一致性：deliverables.md / 主控扩责 等应用文档描述的
#      「M-Form N 项」必须与算法文档实际定义数匹配。偏差 = fail。
#   2. 算法文档引用的产出物路径（final/M-Gate-Report-v2.2.12.json）必须
#      在附录的 schema 中定义，附录文件本身必须存在。
# 说明：JSON 实战产出检查（检测 run/*/final/M-Gate-Report-v2.2.12.json）
#   是 optional——只在主流程项目存在时检查（CI 环境无项目 → warn 不 fail）。
# =============================================================================
GATE_L_FAIL=""

# --- L.1：算法文档实际定义的 M-Form/M-Exist/M-Integrity 项数 ---
M_FORM_DEFINED=$(grep -cE '^### M-Form-[0-9]+:' references/_shared/真源/M-Gate-核心.md 2>/dev/null)
M_EXIST_DEFINED=$(grep -cE '^### M-Exist-[0-9]+:' references/_shared/真源/M-Gate-核心.md 2>/dev/null)
M_INTEGRITY_DEFINED=$(grep -cE '^### M-Integrity-[0-9]+:' references/_shared/真源/M-Gate-核心.md 2>/dev/null)

# --- L.2：跨文档项数描述一致性（deliverables.md / 主控扩责 / status-template）---
# 期望表述：「M-Form N 项」「M-Exist N 项」中 N 与算法文档匹配。
# 仅检测明确「总项数 = N」的表述（如「M-Form 共 6 项」「（6 项）」），不含
# 「v2.2.0 5 项 + 新增 = 8」这类合法的「原版 N 项 + 新增」拆分表述。
# v2.12.13（方案 1.5）：补 `references/_shared/真源/audit-checklist-quickref.md`——该文件是**最高风险单点**
#   （G8 双重编号 + M-Form 项数 6 vs 8），却不在门 L 描述一致性扫描面内；
#   且下方 `[ -f ] || continue` 会对缺失文件**静默跳过**（门 R 已加存在性反向校验）。
for doc in references/deliverables.md references/agents/00-主控-扩展职责.md references/templates/status-template.md references/_shared/真源/audit-checklist-quickref.md; do
  [ -f "$SKILL_ROOT/$doc" ] || continue
  doc_name=$(basename "$doc")
  for wrong_count in 5 6 7; do
    if [ "$wrong_count" -lt "$M_FORM_DEFINED" ] 2>/dev/null; then
      # 只匹配**同一行内含 M-Form** 的「共 N 项」「总 N 项」「（N 项）」表述
      # （v2.12.13 修：原第三条 alternative `（N 项）` 无上下文锚，会把同文件里无关的
      #   `M-Integrity 阶段闸门（2 项）` 误判为 M-Form 漂移——门自身缺陷，1.5 扩大扫描面后暴露）
      if grep -E 'M-Form' "$SKILL_ROOT/$doc" 2>/dev/null | grep -qE "共 ${wrong_count} 项|总 ${wrong_count} 项|（${wrong_count} 项）"; then
        GATE_L_FAIL="$GATE_L_FAIL [$doc_name 含过时 M-Form 总项数表述（应 ${M_FORM_DEFINED} 项，非 ${wrong_count} 项）]"
      fi
    fi
  done
  wrong_count=2
  if [ "$wrong_count" -lt "$M_EXIST_DEFINED" ] 2>/dev/null; then
    if grep -E 'M-Exist' "$SKILL_ROOT/$doc" 2>/dev/null | grep -qE "共 ${wrong_count} 项|总 ${wrong_count} 项|（${wrong_count} 项）"; then
      GATE_L_FAIL="$GATE_L_FAIL [$doc_name 含过时 M-Exist 总项数表述（应 ${M_EXIST_DEFINED} 项，非 ${wrong_count} 项）]"
    fi
  fi
done

# --- L.3：附录 schema 文件存在（JSON 输出格式定义） ---
if [ ! -f "references/_shared/真源/M-Gate-Algorithm-appendix.md" ]; then
  GATE_L_FAIL="$GATE_L_FAIL [缺 M-Gate-Algorithm-appendix.md（JSON schema 必要）]"
fi

# --- L.4：实战 JSON 产出（optional，主流程有 run/* 项目时检查） ---
PROJECTS_WITH_REPORT=0
PROJECTS_TOTAL=0
for proj in "$SKILL_ROOT"/run/*/; do
  [ -d "$proj" ] || continue
  PROJECTS_TOTAL=$((PROJECTS_TOTAL+1))
  report_file="$proj/final/M-Gate-Report-v2.2.12.json"
  if [ -f "$report_file" ]; then
    PROJECTS_WITH_REPORT=$((PROJECTS_WITH_REPORT+1))
    # 检查 JSON 含 13 项 M 门字段（粗略检查：用 jq 或 grep）
    if ! grep -qE 'M-Form-[1-8]|M-Exist-[1-3]|M-Integrity-[1-2]' "$report_file"; then
      GATE_L_FAIL="$GATE_L_FAIL [$(basename $proj) M-Gate-Report JSON 缺全部 13 项字段]"
    fi
  fi
done

# 报告实战覆盖率（warn 级别，不阻塞 commit）
if [ "$PROJECTS_TOTAL" -gt 0 ] && [ "$PROJECTS_WITH_REPORT" -lt "$PROJECTS_TOTAL" ]; then
  warn "门 L: $PROJECTS_TOTAL 个实战项目中 $PROJECTS_WITH_REPORT 个产出 M-Gate-Report JSON（缺 $((PROJECTS_TOTAL-PROJECTS_WITH_REPORT)) 个，主控 T8 未主动 write）"
fi

if [ -z "$GATE_L_FAIL" ]; then
  pass "门 L: M 门算法引用完整（${M_FORM_DEFINED} Form + ${M_EXIST_DEFINED} Exist + ${M_INTEGRITY_DEFINED} Integrity = $((M_FORM_DEFINED+M_EXIST_DEFINED+M_INTEGRITY_DEFINED)) 项，附录 JSON schema 存在）"
else
  fail "门 L: M 门算法引用或 JSON schema 不一致" "$GATE_L_FAIL"
fi

# =============================================================================
# 共享：M 门族扫描文件集（一次 find，M.2/M.3/M.4 复用；v2.7.5 批3 优化）
# 注：CHANGELOG.md / CHANGELOG-archive.md 除外——它们是历史记录，逐字保留历次 Release 正文（含已修复问题的原文与
#   审计结论引文），按「当前状态一致性」口径扫描必然产生永久误报；门 M/M.3/M.4 查的是
#   现行技能内容，不是历史轨迹。（v2.12.47：主文件拆为 5 期 + 归档，两份同属历史资产，须同排除）
MD_SCAN_FILES=$(find "$SKILL_ROOT" -name '*.md' \
    -not -path '*/outputs/*' -not -path '*/.git/*' \
    -not -path '*/references/_shared/archive/*' -not -path '*/references/design/*' \
    -not -name '版本升级自审门*.md' -not -name 'self-audit-gate*' \
    -not -name '*.bak*' \
    -not -path '*/reports/*' -not -path '*/memory/*' -not -path '*/.audit/*' \
    -not -name 'CHANGELOG.md' -not -name 'CHANGELOG-archive.md' -not -name 'changelog-cold-*.md' 2>/dev/null)
MD_SCAN_COUNT=$(echo "$MD_SCAN_FILES" | grep -c . || true)

# 门 M：发布包 exec/process 授权语句一致性（v2.6.8 新增，回应 ClawHub T05 三连击）
# =============================================================================
# 背景：v2.6.6 修协议、v2.6.7 修兜底列表，但模板里仍残留「主控可 exec」授权表述
# （图表-SVG-template 6.1 节）——同类问题三次「修 A 漏 B」。本门机械化扫全部发布范围
# md，任何「主控/子代理可用 denied 工具」的授权语句 = 红。
# 语义：只扫发布包会携带的文件（排除 archive/design/outputs/.git）；
# 含明确拒绝语境（禁止/不得/never/denied…）的行不算授权。
GATE_M_FAIL=""

# --- M.1：禁用面清单真源（v2.13.6 修订：读唯一真源 + fail-closed） ---
#   发现①（覆盖假象，本轮修订）：R-22 把 denied 清单外移到权限文档后，SKILL.md 已无 `denied:` 行
#     ⇒ 旧提取恒空 ⇒ 只剩回退值 `exec process` 两项被扫 —— 104 项禁用面**实际未被覆盖**。
#   发现②（裸词误报，本轮修订）：旧判据是**子串**匹配（形如 `主控.{0,40}\`?ls\`?`）⇒ 命中
#     `toolsAllow` / `tools.subagents` 里的 `ls`；清单一旦扩到 104 项，干净树必被误判为红。
#   现口径：
#     ① 清单 = permissions.md「禁用面唯一真源」块（经 capability-assert 的**唯一加载器**读取）；
#        读不到（缺块 / 围栏异常 / python3 不可用）⇒ 判红，**不回退**旧两项清单。
#     ② 工具名按**显式 ASCII 词边界** `[^A-Za-z0-9_]` 匹配 —— 排除词内命中（`toolsAllow`），
#        且不像 `` 在 CJK 相邻处漏报（实测 `允许exec执行`：`` 0 命中 / 显式词类 1 命中）。
#     ③ 单遍扫描（每个 md 文件 1 次 grep），命中行再归属到具体工具名 —— 104 项也保持秒级。
DENIED_TOOLS=""
if [ -f "$SKILL_ROOT/scripts/capability-assert.py" ] && command -v python3 >/dev/null 2>&1; then
  DENIED_TOOLS="$(python3 "$SKILL_ROOT/scripts/capability-assert.py" --list-denied 2>/dev/null | grep . | sort -u)"
fi
DENIED_TOOL_COUNT=$(printf '%s
' "$DENIED_TOOLS" | grep -c . || true)

if [ -z "$DENIED_TOOLS" ]; then
  GATE_M_FAIL="$GATE_M_FAIL [禁用面真源不可读：capability-assert 的 TRUTH_DENIED 为空（permissions.md 真源块缺失 / 围栏异常 / python3 不可用）—— fail-closed，不回退旧两项清单]"
else
  # --- M.2：单遍扫描授权语句（显式 ASCII 词边界；排除拒绝语境） ---
  M_LB='[^A-Za-z0-9_]'
  M_LBL='[^A-Za-z0-9_-]'   # 左边界额外排除连字符：文件名片段（如 xxx-exec.md）不算工具引用
  M_ALT="$(printf '%s
' "$DENIED_TOOLS" | paste -sd'|' -)"
  M_ATOM="(^|${M_LBL})(${M_ALT})(${M_LB}|\$)"
  # 引用形态（v2.13.6 修订）：只在「工具引用」上判定授权语句 —— 排除两类词法误报（实测）：
  #   ① 散文名词：主控并行 spawn T1 + T2 + T3 三个独立 sessions（sessions 是名词，不是工具）
  #   ② 路径片段：_shared/真源/执行韧化协议-exec.md（exec 在文件名里）
  # 形态 = ① 代码跨度恰为工具名 / ② 与动作·授权动词相邻（前 6 字符）/ ③ 工具名后接核验动作
  M_REF="(\`(${M_ALT})\`|(用|使用|调用|可用|允许|直接|执行|授权|走).{0,6}(${M_LBL}|^)(${M_ALT})(${M_LB}|\$)|(${M_LBL}|^)(${M_ALT})(${M_LB}|\$).{0,6}(验证|核验|扫描|检查|列举|调用|执行|使用))"
  while IFS= read -r md_file; do
    [ -n "$md_file" ] || continue
    hits=$(grep -nE "主控.{0,40}${M_ATOM}|${M_ATOM}.{0,12}兜底|同意后的.{0,12}${M_ATOM}|子代理.{0,20}(使用|调用|可用).{0,8}${M_ATOM}" "$md_file" 2>/dev/null       | grep -vE '禁止|不得|不能|永不|绝不|不调用|不使用|不执行|不碰|不自动|never|must not|deny|denied|永久拒绝|零 exec|zero-exec|不包含|无法|拒绝' \
      | grep -E "$M_REF")
    if [ -n "$hits" ]; then
      M_TOOLS="$(printf '%s
' "$hits" | grep -oE "$M_ATOM" | tr -cd 'A-Za-z0-9_
' | sed '/^$/d' | sort -u | tr '
' ',' | sed 's/,$//')"
      GATE_M_FAIL="$GATE_M_FAIL [${md_file#$SKILL_ROOT/} 含 denied 工具授权残留（${M_TOOLS}）: $(printf '%s
' "$hits" | head -1 | cut -c1-80)]"
    fi
  done < <(printf '%s
' "$MD_SCAN_FILES")
fi
if [ -z "$GATE_M_FAIL" ]; then
  pass "门 M: denied 工具授权语句一致性（扫描 ${MD_SCAN_COUNT} 处文件 × ${DENIED_TOOL_COUNT} 项禁用面，零授权残留）"
else
  fail "门 M: 发现 denied 工具授权语句（禁用面真源 vs 正文矛盾 / 真源缺失）" "$GATE_M_FAIL"
fi

# --- M.3：跨项目状态写入强制语句（v2.6.9 新增，回应 T02 + Missing User Warnings）---
# 任何「主控/agent 必须自动写回跨项目共享文件（lessons.md / 案例库 / skill 自身文件）」的强制语句 = 红；
# 允许「项目内 audit-lessons.md 草稿 + 待主人 review / 人工 merge」表述。
M_CROSS_HITS=""
while IFS= read -r md_file; do
  hits=$(grep -nE '(必须|自动).{0,20}(写回|追加到|merge 到|同步到).{0,20}(lessons\.md|case-studies|案例库)|(教训反向回写)' "$md_file" 2>/dev/null \
    | grep -vE '不自动|不得自动|禁止自动|不执行|待主人|人工 merge|review 后|audit-lessons|草稿|run/<')
  if [ -n "$hits" ]; then
    M_CROSS_HITS="$M_CROSS_HITS [${md_file#$SKILL_ROOT/}: $(echo "$hits" | head -1 | cut -c1-70)]"
  fi
done < <(echo "$MD_SCAN_FILES")
if [ -z "$M_CROSS_HITS" ]; then
  pass "门 M.3: 跨项目状态写入零强制语句（教训只进项目内草稿，共享文件需主人人工 merge）"
else
  fail "门 M.3: 发现跨项目状态强制写入语句（与 SKILL.md 写入边界矛盾）" "$M_CROSS_HITS"
fi

# --- M.4：models list 残留（v2.6.9 新增，回应 Intent-Code Divergence）---
# 「扫本机可用模型（models list）」类表述 = 与零 exec 冲突；只允许否定语境（不得假设可调用）。
M_ML_HITS=""
while IFS= read -r md_file; do
  hits=$(grep -n 'models list' "$md_file" 2>/dev/null | grep -vE '不得假设|不是 agent|指控|改走')
  if [ -n "$hits" ]; then
    M_ML_HITS="$M_ML_HITS [${md_file#$SKILL_ROOT/}: $(echo "$hits" | head -1 | cut -c1-70)]"
  fi
done < <(echo "$MD_SCAN_FILES")
if [ -z "$M_ML_HITS" ]; then
  pass "门 M.4: models list 零授权残留（模型自检统一 session_status 只读口径）"
else
  fail "门 M.4: 发现 models list 授权表述（与零 exec 冲突）" "$M_ML_HITS"
fi

# =============================================================================
# 门 N：依赖版本锁定（v2.8.0 新增，P0-1 修订 2026-09-08）
# =============================================================================
# 检查 requirements.txt 和 tests/requirements-test.txt 是否锁定版本
REQ_FILES=("requirements.txt" "tests/requirements-test.txt")
REQ_MISSING=""
for req_file in "${REQ_FILES[@]}"; do
  if [ ! -f "$req_file" ]; then
    REQ_MISSING="$REQ_MISSING [missing:$req_file]"
    continue
  fi
  # 检查是否有未锁定版本的行（包含包名但没有 ==）
  unpinned=$(grep -vE '^#|^$' "$req_file" | grep -vE '==.*')
  if [ -n "$unpinned" ]; then
    REQ_MISSING="$REQ_MISSING [$req_file: $(echo "$unpinned" | head -1)]"
  fi
done
if [ -z "$REQ_MISSING" ]; then
  pass "门 N: 依赖版本锁定（requirements.txt + tests/requirements-test.txt）"
else
  fail "门 N: 依赖版本未锁定" "$REQ_MISSING"
fi

# =============================================================================
# 门 O：Markdown 表格分隔行有效性（v2.12.4 新增，教训 #299）
# =============================================================================
# GFM 要求表格第二行只含 -、:、| 与空白；`| | |` 这类无短横线的分隔行
# 会让整张表**不渲染成表格**（用户侧可见的排版崩坏）。
# 此处全库扫描：表头行后的第一行若只由 | 与空白构成，即判定无效。
TABLE_BAD=$(python3 - "$PWD" <<'PYEOF'
import pathlib, re, sys
root = pathlib.Path(sys.argv[1])
bad = []
for p in sorted(root.rglob('*.md')):
    s = str(p.relative_to(root))
    if s.startswith(('outputs/', '.git/')) or '/.git/' in s:
        continue
    lines = p.read_text(encoding='utf-8').split('\n')
    incode = False
    for i, l in enumerate(lines):
        if l.lstrip().startswith('```'):
            incode = not incode
            continue
        if incode or i == 0:
            continue
        prev, cur = lines[i - 1].strip(), l.strip()
        if not (prev.startswith('|') and prev.endswith('|')):
            continue
        if cur.startswith('|') and cur.endswith('|') and not set(cur) - set('| \t'):
            bad.append(f'{s}:{i + 1}')
print(' '.join(bad[:5]) + (f' …(+{len(bad) - 5})' if len(bad) > 5 else ''))
PYEOF
)
if [ -z "$TABLE_BAD" ]; then
  pass "门 O: Markdown 表格分隔行有效性（表头后无「| | |」型无效行）"
else
  fail "门 O: 发现无效表格分隔行（表格不会渲染）" "$TABLE_BAD"
fi

# =============================================================================
# 门 P：净化脚本「代码保真」回归测试（v2.12.10 新增，教训 #300）
# =============================================================================
# 教训 #300：strip-anchor-residue.py 的空括号规则用 `[（(]` 同时匹配半角，
#   导致代码块内**所有无参函数调用的括号被吃掉**（`resolve()` → `resolve`），
#   代码语义静默损坏，无任何扫描器报警。v2.12.4 / v2.12.5 净化包 6 文件 13 处中招，
#   并被 ClawHub 安全审计 v2.12.5 列为 Finding #1（Medium, 99%）。
# 本门不扫产出（防误报），而是把探针文本喂给真净化链，断言不变量：
#   1. 代码块内函数调用括号必须存活
#   2. 锚点残留下的空全角括号必须仍被清除
PROBE_DIR=$(mktemp -d)
mkdir -p "$PROBE_DIR/probe"
PROBE_N=999
{
  printf '%s\n' '```python'
  printf '%s\n' 'base = Path(base_dir).resolve()'
  printf '%s\n' 'candidate = (base / target_path).resolve()'
  printf '%s\n' 'claims = [c.strip() for c in claim_pattern]'
  printf '%s\n' 'hit = any(v >= 3 for v in pattern_a_count.values())'
  printf '%s\n' 'wait_start = time.now()'
  printf '%s\n' '```'
  printf '%s\n' "主控记录 cases 需求，写入 status.md（教训 #${PROBE_N}）"
} > "$PROBE_DIR/probe/probe.md"
python3 "$SKILL_ROOT/scripts/strip-anchor-residue.py" "$PROBE_DIR/probe" >/dev/null 2>&1
python3 "$SKILL_ROOT/scripts/strip-shell-commands.py" "$PROBE_DIR/probe/probe.md" >/dev/null 2>&1
PROBE_OUT=$(cat "$PROBE_DIR/probe/probe.md" 2>/dev/null)

# v2.12.40 新增探针（分隔符夹持引用）：`（…），教训 #N；…` 必须被剥除且正文仍可读。
#   背景：2026-09-14 实测 `build-clawhub-release.sh 2.12.39` 首次 EXIT=1，真因是净化包内
#   `references/templates/任务简报-template.md` 的 `，教训 #277；口径真源 = …` 未被剥除
#   （长期缺口，v2.12.38 包内同样残留）。本探针把该形态钉进门 P，禁止回退。
#   注：单独目录 + 只跑剥离脚本——不得与上面 probe.md 的链混跑，否则
#   `（教训 #N）` 会被提前改写成 `（见相关算法）`，「空括号残留清除」覆盖失效（教训 #300 回归面）。
mkdir -p "$PROBE_DIR/leak"
printf '%s\n' '（含 AI 使用声明/致谢），教训 #'"${PROBE_N}"'；口径真源 = 字数判定表.md' \
  > "$PROBE_DIR/leak/leak-delim.md"
printf '%s\n' '- [ ] checkbox 不得被剥离' >> "$PROBE_DIR/leak/leak-delim.md"
CHECKBOX_BEFORE=$(grep -cE '^[[:space:]]*[-*][[:space:]]*\[[ xX]?\]' "$PROBE_DIR/leak/leak-delim.md" || true)
bash "$SKILL_ROOT/scripts/strip-internal-leakage.sh" "$PROBE_DIR/leak" >/dev/null 2>&1 || true
LEAK_OUT=$(cat "$PROBE_DIR/leak/leak-delim.md" 2>/dev/null)
CHECKBOX_AFTER=$(printf '%s\n' "$LEAK_OUT" | grep -cE '^[[:space:]]*[-*][[:space:]]*\[[ xX]?\]' || true)

rm -rf "$PROBE_DIR"
GATE_P_FAIL=""
for probe_tok in '.resolve()' 'c.strip()' 'values()' 'time.now()'; do
  case "$PROBE_OUT" in
    *"$probe_tok"*) ;;
    *) GATE_P_FAIL="$GATE_P_FAIL [代码括号被吃:$probe_tok]" ;;
  esac
done
case "$PROBE_OUT" in
  *"status.md（）"*) GATE_P_FAIL="$GATE_P_FAIL [锚点残留空括号未清]" ;;
esac
if [ "$CHECKBOX_AFTER" -lt "$CHECKBOX_BEFORE" ]; then
  GATE_P_FAIL="$GATE_P_FAIL [checkbox 行被剥离:$CHECKBOX_BEFORE->$CHECKBOX_AFTER]"
fi
case "$LEAK_OUT" in
  *"教训 #"*) GATE_P_FAIL="$GATE_P_FAIL [分隔符夹持引用未剥除]" ;;
esac
case "$LEAK_OUT" in
  *"口径真源"*) ;;
  *) GATE_P_FAIL="$GATE_P_FAIL [分隔符剥除误伤正文]" ;;
esac
if [ -z "$GATE_P_FAIL" ]; then
  pass "门 P: 净化链代码保真（括号存活 + 残留清除 + 分隔符夹持剥除）"
else
  fail "门 P: 净化链损伤代码或残留未清" "$GATE_P_FAIL"
fi

# =============================================================================
# 门 G：净化包与真源的一致性（版本号硬校验 + 指纹 informational）
# =============================================================================
# v2.12.12 修正（门设计缺陷）：旧版把「真源 md5 == 包 md5」当硬校验，但净化链本就对包做
#   sed 替换（剥离开发者叙事），只要包已生成就必然不一致 → 门 G 永远无法 PASS，
#   CHANGELOG 里于是并存「18 PASS（含未生成包时的门 G）」与「17 PASS + 门 G ⚠」两种口径
#   （2026-09-10 核对：属门设计缺陷，非记录错误）。
#   现改为：硬校验 = ①包内版本号 == 真源版本号；②包内无开发者脚本；
#   md5 差异降为 informational 提示，不参与 PASS/FAIL 计数。
# 警告：论衡 zero exec 哲学——md5 仅作可选校验，不阻塞 commit
# v2.13.x 整改（独立复查阻断项）：outputs/ 已迁出技能根（A5）——路径须与 build/publish/cleanup 同源；
#   旧写法 $SKILL_ROOT/outputs/... 在迁移后恒不命中 ⇒ 门 G 退化成「恒报未生成」的假绿灯，
#   发布前包一致性硬校验（版本号/无脚本）永久哑火。
# OUTPUTS_ROOT 语义（全仓统一，2026-09-14 修正）=「输出**总根**」（不含 /clawhub-release 段），
#   故包路径恒为 <总根>/clawhub-release/<版本>——与 build/publish/strip/cleanup 同源；
#   兼容注意：旧 build/publish 曾把它当「发布根」（默认值含 /clawhub-release），
#   调用方显式设 OUTPUTS_ROOT 时门 G 会查不到包而假绿灯。回归门：tests/test_outputs_root_semantics.py
OUTPUTS_ROOT="${OUTPUTS_ROOT:-$HOME/lunheng-build/lunheng-outputs}"
PURIFY_DIR="$OUTPUTS_ROOT/clawhub-release/$EXPECTED_VERSION"
if [ -d "$PURIFY_DIR" ]; then
  GATE_G_FAIL=""
  # 硬校验 1：包内版本号 == 真源版本号（防「包是真源旧版」静默发布）
  if [ -f "$PURIFY_DIR/SKILL.md" ]; then
    PUR_VER=$(grep -m1 -E '^[[:space:]]*version:' "$PURIFY_DIR/SKILL.md" | sed -E 's/^[[:space:]]*version:[[:space:]]*//;s/["'"'"']//g;s/[[:space:]]*$//')
    [ "$PUR_VER" != "$EXPECTED_VERSION" ] && GATE_G_FAIL="$GATE_G_FAIL [包内版本 $PUR_VER ≠ 真源 $EXPECTED_VERSION]"
  else
    GATE_G_FAIL="$GATE_G_FAIL [包内缺 SKILL.md]"
  fi
  # 硬校验 2：包内不得出现开发者脚本（.sh 或 scripts/ 路径）
  if find "$PURIFY_DIR" \( -name '*.sh' -o -path '*/scripts/*' \) -print -quit 2>/dev/null | grep -q .; then
    GATE_G_FAIL="$GATE_G_FAIL [包内含开发者脚本]"
  fi
  # 硬校验 3：包内文件集必须与构建白名单精确相等。
  PKG_MANIFEST="$SKILL_ROOT/scripts/.pkg-manifest.txt"
  if [ ! -f "$PKG_MANIFEST" ]; then
    GATE_G_FAIL="$GATE_G_FAIL [缺少随包清单 scripts/.pkg-manifest.txt]"
  else
    PKG_ACTUAL=$(cd "$PURIFY_DIR" && find . -type f | sed 's|^./||' | LC_ALL=C sort)
    PKG_EXPECT=$(LC_ALL=C sort "$PKG_MANIFEST")
    if [ "$PKG_ACTUAL" != "$PKG_EXPECT" ]; then
      GATE_G_FAIL="$GATE_G_FAIL [包内文件集与 scripts/.pkg-manifest.txt 不一致]"
    fi
  fi
  # informational：关键文件 md5 差异（净化链替换导致，属预期，不计 PASS/FAIL）
  KEY_FILES=("SKILL.md" "QUICKSTART.md" "references/_shared/真源/glossary-full.md")
  MD5_MISMATCH=""
  for kf in "${KEY_FILES[@]}"; do
    [ ! -f "$kf" ] && continue
    [ ! -f "$PURIFY_DIR/$kf" ] && continue
    SRC_MD5=$(md5sum "$kf" 2>/dev/null | awk '{print $1}')
    PUR_MD5=$(md5sum "$PURIFY_DIR/$kf" 2>/dev/null | awk '{print $1}')
    [ "$SRC_MD5" != "$PUR_MD5" ] && MD5_MISMATCH="$MD5_MISMATCH [$kf]"
  done
  if [ -z "$GATE_G_FAIL" ]; then
    pass "门 G: 净化包与真源一致（版本号 $EXPECTED_VERSION + 无开发者脚本）"
    [ -n "$MD5_MISMATCH" ] && echo -e "  ${YELLOW}ℹ${NC} 门 G 指纹差异（informational，净化链替换所致，不计入 PASS/FAIL）：$MD5_MISMATCH"
  else
    fail "门 G: 净化包与真源不一致" "$GATE_G_FAIL"
  fi
else
  pass "门 G: 净化包未生成（commit 阶段正常态，发布时 build-clawhub-release.sh 后自动生成）"
fi

# =============================================================================
# 门 Q：净化可见面「审计归因语」回归门（v2.12.12 新增）
# =============================================================================
# 背景：leak-audit §四.1 建议「把门禁升级为语义扫描」，但 v2.12.11 只修了审计点名的 1 处，
#   并只做了词表中性化（'A.I.G 扫描器'→'A.I.G 审计'）—— 结果包内仍存「回应 <平台> <扫描器>
#   <finding 编号>」类维护者叙事（实测 14 文件 50+ 行，changelog 只披露 2 个文件）。
#   根因：检查点在**包侧**（构建后才报），而写法漂移源在**真源侧**（改 A 漏 A，同教训 #192/#300）。
# 本门把检查点前移到真源：对「将来会进包的可见面」直接 fail-loud，构建前就能拦住。
# 范围 = 与 build-clawhub-release.sh 的可见面一致（排除不外发文件）。
GATE_Q_FAIL=""
Q_FILES=()
while IFS= read -r -d '' f; do
  case "${f#"$SKILL_ROOT"/}" in
    references/_shared/治理/教训索引.md|references/设计文档*.md|references/design/*|references/_shared/archive/*|.safe-pattern-manifest.json) continue ;;
    reports/*|memory/*) continue ;;   # v2.12.57：主人 2026-09-19 裁定「工程过程产物不进版本库」（.gitignore 已拦）⇒ 同 build 可见面，不纳入本门扫描
  esac
  Q_FILES+=("$f")
done < <(find "$SKILL_ROOT" \( -name '*.md' -o -name '*.json' -o -name '*.yaml' -o -name '*.yml' -o -name '*.txt' -o -name '*.toml' \) -not -path '*/.git/*' -not -path '*/outputs/*' \
  -not -path '*/references/_shared/archive/*' -not -path '*/references/design/*' \
  -not -path '*/reports/*' -not -path '*/memory/*' \
  -not -name 'CHANGELOG.md' -not -name 'CHANGELOG-archive.md' -not -name 'changelog-cold-*.md' -not -name 'README.md' -print0)
Q_PATTERNS=(
  'ClawHub A\.I\.G'
  'A\.I\.G'
  'SkillSpector|ClawScan'
  'SQP-[0-9]|SDI-[0-9]'
  'Intent-Code Divergence|Description-Behavior Mismatch|Context-Inappropriate Capability|External Transmission'
  'scanner'
  '扫描器'
  'Remediation'
  'T0[0-9]'
  '92% finding|#89% finding'
  '平台审核'
)
if [ ${#Q_FILES[@]} -gt 0 ]; then
  for pat in "${Q_PATTERNS[@]}"; do
    hits=$(grep -lE "$pat" "${Q_FILES[@]}" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$hits" -gt 0 ]; then
      GATE_Q_FAIL="$GATE_Q_FAIL [$pat → $hits 文件]"
    fi
  done
fi
if [ -z "$GATE_Q_FAIL" ]; then
  pass "门 Q: 净化可见面无审计归因语（${#Q_FILES[@]} 文本文件，11 类 token）"
else
  fail "门 Q: 净化可见面残留审计归因语" "$GATE_Q_FAIL"
fi

# =============================================================================
# 门 R：门有效性自证（v2.12.13 新增，方案 1.8 / 教训 #320）
# -----------------------------------------------------------------------------
# 背景：本次审计抓到的两个最严重缺陷（Archive SOP 漏入 / 67 页脚逸出）都不是
#   「门没写」，而是「门写了但空转」——规则目标文本已不存在，grep 永不命中，
#   于是门永远 PASS。**静默空转比没门更危险**（有门 = 假安全感）。
# 查三项：
#   R.1 门 L 描述一致性扫描的文档列表**逐个存在**（原 `[ -f ] || continue` 对
#       缺失文件静默跳过 → 文档改名即门失效）；
#   R.2 关键门正则**有效性自证**：对每条 fail-loud 正则构造「必中样本」，
#       grep 必须命中样本（证明正则未写坏 / 未被转义破坏）；
#   R.3 构建脚本规则清单**格式与基数**自证（4 字段、条数 > 0）。
# =============================================================================
GATE_R_FAIL=""
R_RULE_TOTAL=0
R_FINAL_TOTAL=0

# --- R.1：门 L 文档列表存在性 ---
GATE_L_DOCS=(
  references/deliverables.md
  references/agents/00-主控-扩展职责.md
  references/templates/status-template.md
  references/_shared/真源/audit-checklist-quickref.md
)
for d in "${GATE_L_DOCS[@]}"; do
  [ -f "$SKILL_ROOT/$d" ] || GATE_R_FAIL="$GATE_R_FAIL [门 L 扫描文档缺失：$d（原逻辑会静默跳过）]"
done

# --- R.2：关键门正则有效性自证（名称~正则~必中样本）---
GATE_R_PROBES=(
  '零exec口径~零 exec~零 exec'
  '教训引用~教训 #[0-9]+~教训 #320'
  'M-Form 定义行~^### M-Form-[0-9]+:~### M-Form-1:'
  '审计归因语~SkillSpector|ClawScan~SkillSpector'
  '教训索引行~^\| #[0-9]+ ~| #320 |'
  '剥离目标·净化包~净化包~净化包'
)
for probe in "${GATE_R_PROBES[@]}"; do
  IFS='~' read -r pname ppat psample <<<"$probe"
  if ! printf '%s\n' "$psample" | grep -qE "$ppat" 2>/dev/null; then
    GATE_R_FAIL="$GATE_R_FAIL [正则已失效：$pname（必中样本未命中，正则=$ppat）]"
  fi
done

# --- R.3：构建脚本规则清单格式与基数自证 ---
BUILD_SH="$SKILL_ROOT/scripts/build-clawhub-release.sh"
if [ -f "$BUILD_SH" ]; then
  R_RULE_TOTAL=$(sed -n '/^RULE_CHECKS=(/,/^)/p' "$BUILD_SH" | grep -cE "^[[:space:]]*'[^']+\|[^|]+\|(critical|warn)\|(yes|no)'")
  R_FINAL_TOTAL=$(sed -n '/^FINAL_PATTERNS=(/,/^)/p' "$BUILD_SH" | grep -cE "^[[:space:]]*'")
  if [ "$R_RULE_TOTAL" -eq 0 ]; then
    GATE_R_FAIL="$GATE_R_FAIL [构建脚本 RULE_CHECKS 为空或格式不符（规则清单已失效）]"
  fi
  if [ "$R_FINAL_TOTAL" -eq 0 ]; then
    GATE_R_FAIL="$GATE_R_FAIL [构建脚本 FINAL_PATTERNS 为空（残留扫描门已失效）]"
  fi
  if [ "$R_RULE_TOTAL" -lt 44 ]; then
    GATE_R_FAIL="$GATE_R_FAIL [构建脚本 RULE_CHECKS 数量 $R_RULE_TOTAL < 基线 44（规则被删除或失效）]"
  fi
else
  GATE_R_FAIL="$GATE_R_FAIL [构建脚本缺失：scripts/build-clawhub-release.sh]"
fi

if [ -z "$GATE_R_FAIL" ]; then
  pass "门 R: 门有效性自证通过（门 L 文档 ${#GATE_L_DOCS[@]} 个齐备 / 正则探针 ${#GATE_R_PROBES[@]} 条命中 / 构建规则 $R_RULE_TOTAL 条格式合法）"
else
  fail "门 R: 存在空转风险的门或规则" "$GATE_R_FAIL"
fi

# =============================================================================
# 门 S：流程图可达性与入参链（v2.12.28 新增 —— 防孤立节点 / 断链 / 缺 next / 缺 input）
#   background：2026-09-12 实测发现 phase4_4_figures 无上游指向（配图被跳），
#   且 6 个执行类节点缺 input 声明 → 衔接无机械校验。本门防复发。
# =============================================================================
if command -v python3 >/dev/null 2>&1 && [ -f references/_shared/真源/phase-order.yaml ]; then
  FLOW_ERR="$(python3 scripts/flow-check.py 2>&1)"
  if [ -z "$FLOW_ERR" ]; then
    NODES=$(grep -c '^  - id:' references/_shared/真源/phase-order.yaml)
    pass "门 S: 流程图可达性与入参链（$NODES 节点全可达 + 无缺 next/input）"
  else
    fail "门 S: 流程图断链/孤立节点" "$FLOW_ERR"
  fi
else
  # v2.13.x 审计修订（R-06）：原实现**无 else** —— 缺 python3 或真源被改名时，本门整行不输出、
  #   门数默默从 36 降到 35，报告上看不出任何异常（2026-09-25 审计实测复现）。
  #   「检查器缺失 / 真源被改名」恰恰是最该报警的场景，不得以静默消失呈现。
  _GATE_S_WHY=""
  command -v python3 >/dev/null 2>&1 || _GATE_S_WHY="缺 python3；"
  [ -f references/_shared/真源/phase-order.yaml ] || _GATE_S_WHY="${_GATE_S_WHY}缺 references/_shared/真源/phase-order.yaml；"
  fail "门 S: 未执行（流程图可达性与入参链）" "${_GATE_S_WHY}⇒ 本门不可判定（不允许静默跳过）；修法：装 python3 / 恢复真源文件"
fi

# =============================================================================
# 门 T：权限口径一致性（v2.12.30 新增 —— 防「文档声明禁用、脚本实际放行」）
#   v2.13.5（R-22）：禁面清单真源外移至权限文档块；本门改读该真源（经 capability-assert 的唯一加载器）。
#   background：2026-09-12 第三方审计 P0-1 —— SKILL.md frontmatter denied 列了
#   memory_store / memory_forget / sessions_search，但 capability-assert.py 把它们
#   放进允许白名单（判定只查 FORBIDDEN_CAPABILITIES）→ 断言脚本错误放行，与声明冲突。
#   本门把「权限声明 vs 机器执行体」做成机械校验：denied 的每一项都必须被断言脚本拒绝。
# =============================================================================
if [ -f scripts/capability-assert.py ] && command -v python3 >/dev/null 2>&1; then
  GATE_T_FAIL=""
  # v2.13.5（R-22）：真源外移后不再从 frontmatter 读清单 —— 直接复用 capability-assert 的真源加载器
  #   （单一解析入口：口径守卫只此一份，门 T 与之永不漂移）
  DENIED_CAPS="$(python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('cap_assert', 'scripts/capability-assert.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(' '.join(sorted(m.TRUTH_DENIED)))
" 2>/dev/null)"
  if [ -z "$DENIED_CAPS" ]; then
    fail "门 T: 权限口径一致性" "未能从权限文档真源块读出 denied 清单（R-22：真源 = permissions.md 的禁用面块）"
  else
    if ! python3 scripts/capability-assert.py --selfcheck >/dev/null 2>&1; then
      GATE_T_FAIL="$GATE_T_FAIL [selfcheck 失败：denied ∩ allowed ≠ ∅]"
    fi
    for cap in $DENIED_CAPS; do
      if python3 scripts/capability-assert.py T0 read "$cap" >/dev/null 2>&1; then
        GATE_T_FAIL="$GATE_T_FAIL [$cap]"
      fi
    done
    if [ -z "$GATE_T_FAIL" ]; then
      pass "门 T: 权限口径一致性（denied $(echo $DENIED_CAPS | wc -w) 项全部被 capability-assert.py 拒绝）"
    else
      fail "门 T: denied 能力被能力断言脚本放行" "$GATE_T_FAIL"
    fi
  fi
else
  # v2.13.x 审计修订（R-06）：同门 S —— 原实现无 else，门 T 在缺 python3/缺断言脚本时静默消失。
  _GATE_T_WHY=""
  [ -f scripts/capability-assert.py ] || _GATE_T_WHY="缺 scripts/capability-assert.py；"
  command -v python3 >/dev/null 2>&1 || _GATE_T_WHY="${_GATE_T_WHY}缺 python3；"
  fail "门 T: 未执行（权限口径一致性）" "${_GATE_T_WHY}⇒ 本门不可判定（不允许静默跳过）"
fi

# =============================================================================
# 门 U：相对链接可解析性（v2.12.30 新增，回应第三方审计 P2）
#   background：CHANGELOG 曾积累 10 处**结构性断链**（../outputs/* 指向 .gitignore 的
#   产物目录 / docs/* 指向不存在的目录 / 裸相对名指向不存在文件）——对任何克隆者都不可达，
#   且此前无任何机械门能发现（只有人工点开才暴露）。本门把它变成机械校验。
#   注：脚本自身忽略代码围栏/行内代码中的链接（示例文本非真链接）。
#   v2.12.59 扩面（回应 2026-09-19 全面审计 P1-1/P1-2）：原判据面 = ① markdown 链接
#   + ② SKILL.md 裸文件名，合起来**仍不覆盖**活文档的**反引号内联路径引用**——实测
#   `_shared/真源/host-verify-recipe.md` 被 2 处活文档（均在净化包可见面）引用却从未存在过，
#   而本门报「全部可解析」。⇒ 判据面改为**缺陷类的宿主集**（教训 #427）：三类并列，
#   第三类扫 references/**（含 templates/）的反引号内联引用，解析顺序 = 同级→仓根→同名。
#   反向注入单测见 tests/test_link_check.py（注入悬空 token 必须报错 + 真源零写入护栏）。
# =============================================================================
if [ -f scripts/link-check.py ] && command -v python3 >/dev/null 2>&1; then
  if GATE_U_OUT="$(python3 scripts/link-check.py 2>&1)"; then
    pass "门 U: 相对链接可解析性（${GATE_U_OUT#✅ }）"
  else
    GATE_U_BAD="$(printf '%s' "$GATE_U_OUT" | grep -E '→' | head -5 | tr '\n' ' ')"
    fail "门 U: 相对链接断链" "$GATE_U_BAD"
  fi
else
  # v2.13.x 审计修订（R-06）：同门 S/T —— 原实现无 else，门 U 静默消失。
  _GATE_U_WHY=""
  [ -f scripts/link-check.py ] || _GATE_U_WHY="缺 scripts/link-check.py；"
  command -v python3 >/dev/null 2>&1 || _GATE_U_WHY="${_GATE_U_WHY}缺 python3；"
  fail "门 U: 未执行（相对链接可解析性）" "${_GATE_U_WHY}⇒ 本门不可判定（不允许静默跳过）"
fi

# =============================================================================
# 门 V：SKILL.md 体量棘轮（v2.12.30 新增，回应第三方审计 P2）
#   background：SKILL.md 曾达 12,440 字符，入口膨胀会挤占模型预算、稀释触发判据。
#   10,000 字符是论衡自身的可读性/上下文预算棘轮，不是本 direct-maintenance
#   技能的通用官方硬上限；官方 10,000 字符限制仅适用于 autonomous proposal，
#   通用 maxSkillBytes 与运行模式另有口径，详见 references/_shared/真源/skill-entry-appendix.md。
#   本门为**棘轮**：只许变小——超过项目记录上限即失败；瘦身成功后必须同步下调本上限。
#   说明：内容受「机械门锚定」保护者（tests/test_rules_consistency.py 以 SKILL.md 为
#   T9 6 维度 / 4 档 + G14 8 类的漂移锚点）与合规清单（外发同意）**不得为凑数而删**。
# =============================================================================
# v2.15.9（审计 P2「frontmatter 预算事前拦截」）：frontmatter 单独预算门。
#   缺口来源：门 V 锁的是 SKILL.md 全文字符数，而 v2.15.7 踩的坑是 frontmatter
#   单独撑到 9487 字符（R-22 常驻预算 <9000）—— 全文门当时并未报警（正文够短），
#   直到事后 CI 才红。本门补上「frontmatter 自己的预算」。
#   语义：frontmatter = 首个 --- 与其配对 --- 之间的内容（不含两行分隔符）；
#   预算 9000 字符（R-22 常驻预算；frontmatter 每次加载都进模型上下文，比正文更贵）。
FM_CHARS_CEIL=9000
if [ -f SKILL.md ] && command -v python3 >/dev/null 2>&1; then
  FM_CHARS=$(python3 -c "
import io, re
t = io.open('SKILL.md', encoding='utf-8').read()
m = re.match(r'^---\n(.*?)\n---', t, re.S)
print(len(m.group(1)) if m else -1)
")
  if [ "${FM_CHARS:-0}" -lt 0 ]; then
    fail "门 V: SKILL.md frontmatter 不可解析" "首部无配对的 --- 分隔符（frontmatter 预算不可判定）"
  elif [ "$FM_CHARS" -le "$FM_CHARS_CEIL" ]; then
    FM_NOTE="frontmatter ${FM_CHARS} ≤ ${FM_CHARS_CEIL}"
  else
    fail "门 V: SKILL.md frontmatter 预算超限" "${FM_CHARS} > ${FM_CHARS_CEIL}（R-22）—— 长清单/模型枚举请回真源文件，frontmatter 只留指针"
  fi
fi
SKILL_CHARS_CEIL=10000
if [ -f SKILL.md ]; then
  SKILL_CHARS=$(wc -m < SKILL.md | tr -d '[:space:]')
  if [ "$SKILL_CHARS" -le "$SKILL_CHARS_CEIL" ]; then
    pass "门 V: SKILL.md 体量棘轮（${SKILL_CHARS} <= ${SKILL_CHARS_CEIL} 字符；${FM_NOTE:-frontmatter 未检}；只许降）"
  else
    fail "门 V: SKILL.md 体量回涨" "${SKILL_CHARS} > ${SKILL_CHARS_CEIL} 项目棘轮上限—— 请外移长内容而非放宽本上限"
  fi
fi

# =============================================================================
# 门 Y：必读文件体量软棘轮 + SKILL.md 余量告警（v2.12.62 新增，回应审计 P1-3）
#   背景（2026-09-19 全面审计 P1-3）：门 V 只锁 SKILL.md 那 ~9.8K 字符 —— 占仓库 1.72M 字符
#   的 0.57%。仓库里**唯一**有硬棘轮的，恰恰是余量最紧的那一个：三个「每次必读」的大文件
#   合计 ~213KB 无任何约束。审计建议「不要动门 V 的 10000 上限（那是官方约束），而是加
#   第二层棘轮」——给这三个文件设**软阈值**。
#   语义：**⚠️ 提示级，不计入 exit code**（warn 不改 FAILED）。目的是逼「加内容前先分层/
#   外移」，而不是把大文件变成第二个 SKILL.md。上限 = 最近一次分层后的**实测值，只许降**：
#   瘦身成功后必须同步下调本表（记录在案，防回涨）。
#   另加 SKILL.md「余量告警」：余量 < 阈值即告警 —— 余量枯竭会诱发论衡自认的头号死敌
#   「改 A 漏 B」（边删边加），必须在余量耗尽前被看见，而不是等撞到门 V 硬墙才发现。
#   测试覆盖：tests/test_bulk_ratchet.py（正向无告警 / 覆盖阈值必告警 / 清单完整性 / 缺失文件）。
# =============================================================================
# ⚠️ 2026-10-01 缩容备案（扩展职责卡重构 · 历史叙事外移）：00-主控-扩展职责.md 78031→69808（−8223 B）；
#   教训 #N 由来/版本考古/实战事故叙事外移至 CHANGELOG [Unreleased]，节编号与顺序不变（外部 §N 指针依赖）。
#   同步修复：§九 G14 孤头、§二十二断裂列表、T7.5 元说明计数、exit 0 旧口径。按「只许降」下调上限。
# ⚠️ 2026-10-02 基线重定（v2.15.7 扩容备案 · CI 债务修复）：00-主控-扩展职责.md 69808→74923
#   （§十六点五 派发硬验证 + weight 阈值表，v2.15.7 功能性新增）；phase-order.yaml 63928→66412 /
#   index.yaml 24767→25084（新增 post_phase1_dispatch_verify 节点；装配视图系生成物，无分层可选）。
#   按 v2.15 B1-B7 先例以实测重定，后续仍**只许降**；不得借此掩盖无关内容膨胀。明细见 CHANGELOG [v2.15.7]。
# ⚠️ 2026-10-05 扩容备案（架构评审 v3 R2 契约真源化）：phase-order.yaml 66574→68238（+1664 B）。
#   原因 = 7 个节点切片新增协议契约字段（g14/t9/t1b 的 dispatch: 载体登记、recheck_max_rounds
#   真源化、t9b/methodology 的 opt_out_carriers、audit/t5 的 rounds_carrier）——派发合同块生成器
#   由代码侧常量改为切片现算的配套真源登记，属协议契约内容（非注释膨胀）。
#   按 v2.15 B1-B7 先例以实测重定，后续仍**只许降**。
# ⚠️ 2026-10-05 第二轮扩容备案（T9b 降级 opt-in + R2 契约真源化累积）：
#   00-主控-扩展职责.md 70189→70277（+88，T9b 极性说明行）
#   phase-order.yaml 68238→69293（+1055，本轮 T9b 切片的 opt-in 契约字段 + 昨轮 R2 派发/轮次字段累积）
#   phase-order/index.yaml 25084→25358（+274，condition_definitions 键改名 owner_stress_test_opt_out→owner_stress_test_opt_in + 备案注）
#   均为**协议契约内容**（非注释膨胀），已同批写入 references/_shared/治理/ratchet-ledger.md（台账 §四-1「上涨 = 记账」）。
#   ⚠️ 登记遗漏修正：2026-10-05 上午 R2 契约真源化那轮把 phase-order.yaml 66574→68238 时**未同批写台账**，
#      违反台账 §四-1（重定不得为隐式豁免），本轮一并补登（直接更新原 open 债务行的 to 值，不新开行）。
#   按 v2.15 B1-B7 先例以实测重定，后续仍**只许降**。
# ⚠️ 2026-10-05 发版重定（v2.15.9 → v2.15.10）：四个必读文件各 +1 B。
#   原因 = **版本戳机械变长**（2.15.9 → 2.15.10，每处版本头 +1 字符），
#   属 sync-version.sh 的协议必做动作，**非内容膨胀**（台账 §二 structural_exempt 记为
#   version_stamp_lengthening 类；**2026-10-06 方案 A 定案**：该类按发版频率豁免，
#   不计入 §四-3 三次上调铁律、不计入 §一 settle_to 比对，见 ratchet-ledger.md §二
#   （原「只允许发生一次」与该类冲突的设计待办已销）。
#   数值：00-主控 70277→70278 / M-Gate 77526→77527 / phase-order.yaml 69293→69294 / index.yaml 25358→25359
#   三条 open 债务的 to 值同步累加（未销账不新开行）；M-Gate-核心.md 那条为**纯版本戳机械变长**，
#   2026-10-06 起按 §二 豁免口径**移出** §一 债务、记为豁免实例（不新开债务行）。
# ⚠️ 2026-10-08 审计修订（批次 1「契约自洽」R-4/R-5/R-6 + 批次 2「假绿灯面」R-1/B1）：
#   phase-order.yaml 70860→75003（+4143 B）/ index.yaml 25359→26813（+1454 B）。
#   原因 = **功能性判据新增，非注释膨胀**：
#     · 批次 1 R-5：`pre_spawn_enforcement.precondition` 增「模型路由 phase0_route 段且 selected_by=owner，
#       缺记录判 path_or_param_error」判据（取消 route_tier「无记录走默认」fail-open 尾巴）。
#     · 批次 1 R-6：`terminal_freeze.doctrine` 重开链改**依赖序** current_draft_sync→g14→final_assembly
#       (含 g14_caption_recheck)→t9_review→t8（原序与 `t9_review.input = final/定稿.md`（seq 22 > 21）矛盾，
#       会让盲审读旧版定稿）。
#     · 批次 2 R-1（B1）：Phase 1.5 拆两个求值点，新增节点 `phase1_5b_post_t2_5_review`（seq 6），
#       节点数 26→27（装配视图为生成物，随切片同步变长）。
#   ⚠️ **铁律预警已触发**：两文件各自在 2026-10-08 一天内被上调（原 70860/25359 → 71724/25909 → 75003/26813），
#   按 §四-3「同一 path 第 3 次上调须走分层/外移」的口径，按 v2.15.13 批次既有先例累加到原 open 行（未销账不新开行）。
#   当日下半段**主动回落（见下）**，铁律额度已释放。
# ⚠️ 2026-10-08 N-2「真分层·结构约束外移」（当日主动回落，铁律额度已释放）：
#   index.yaml 26813→22939（−3874 B）、phase-order.yaml 75003→71091（−3912 B）。
#   动因 = **真冗余**：index.yaml 第 16-48 行「结构约束 ①-⑬」共 4481 B，是对 flow-check.py **已实现**规则的
#   散文复述（12 个约束关键词中 11 个两处重复）。这些是**真源编写 / 构建期校验**规则，而 flow-check.py
#   随 `scripts/` 整目录排除、**不随包分发** —— 留在随包的 index.yaml 等于让包内用户读到「无法执行的
#   校验规则」。故全文迁至 flow-check.py docstring 之后，index.yaml 只留指针。
#   迁移安全性已验：迁移块对 `_rule_labels()` 两个正则（`^ {1,2}(\d{1,2}[a-z]?)\s` 与
#   `^ *# (\d{1,2}[a-z]?)\s`）**均抽不出任何规则号**，规则号集合保持 50 不变（现**贴** RULE_COUNT_MAX=50）。
#   回落同时触发台账 §四-2 销账：`index.yaml` 两条 debt 均达成 settle_to（22939 ≤ 25359 / ≤ 24767）⇒ 已销；
#   `phase-order.yaml` 71091 仍高于其 settle_to（70860 / 63928）⇒ 保持 open。
#   注：实际值 index 22947 / phase-order 71099（比 22939/71091 多 8 B）—— 因随包指针必须去掉
#   `scripts/` 字面量（构建链 FINAL_PATTERNS 将 `scripts/` 列为包内残留，带则构建失败），替代措辞略长；
#   **非内容膨胀**，不上调任何 debt。
#   （v2.15.14 发版微调 2 项：版本串 2.15.13→2.16.0 变短 1 字符 ⇒ 00-主控 / M-Gate-核心
#   各缩 1 B。棘轮语义「上限 == 实测」要求同步下调，否则 test_bulk_ratchet 红。）
BULK_RATCHET_CEIL_DEFAULT="references/agents/00-主控-扩展职责.md|70277,references/_shared/真源/M-Gate-核心.md|78089,references/_shared/真源/phase-order.yaml|71099,references/_shared/真源/phase-order/index.yaml|22947"
# v2.15 B1-B7 扩容备案：新增运行可靠性、证据链、上下文指针、机械对账、遥测、pipeline-doctor 与质量/HMI 真源字段；
# phase-order.yaml/index.yaml 的基线按本轮真实落盘体量重定，后续仍只许降，不得借此掩盖无关内容膨胀。
#   v2.13.5 R-21 增量 2 基线说明（**不是放宽既有上限**，而是规范形态变更后的重新定基）：
#     · 增量 2 把装配从「YAML 重打」改为「原文逐字拼接」—— 重打会丢行尾注释与作者引号，
#       实测会静默废掉文本型机械门（D-3 注释 4 处断言 + 5 条按文本注入的反向测试）。
#     · 故 phase-order.yaml 回涨到 61,626 B（= 历史真源 61,559 B + 装配头 2 行）；这不是新增内容，
#       而是把上游本就存在的文本还原回来。index.yaml 24,267 B 则承载契约段原文（含 144 行注释）。
#     · 家族合计 85,893 B > 倒置前 61,559 B：真源被拆成「索引 + 装配」两份共存；代价换来的收益是
#       运行期读取量 —— 旧协议每进一个 Phase 重读全量（≈61.6 KB × 24），新协议 index 读一次 + 逐节点切片。
# ⚠️ v2.13.6 缩容备案（R-38 指针收口 · 主动下调，非扩容）：00-主控-扩展职责.md 77380→77353（−27 B）；phase-order.yaml 61603→61520（−83 B）；index.yaml 24261→24212（−49 B）。
#   本轮新增「等待期体验与运行期留痕」运行纪律（规则 50 载体），同时把 §二十一 的「无应答兜底」长句
#   与概览行压缩为指针/短句（真源 = phase-order.yaml owner_timeout_policy，本卡不重列）。净值为**减少**，
#   故按「只许降」同步下调上限；后续若再增内容请先分层/外移，不要放宽本值。
# ⚠️ v2.12.72 扩容备案（批次 2-E 主控上下文预算门 · 审计 P2-6 要求的「扩容说明」）：两个大文件微增，
#   原因 = 新增「主控上下文预算与落盘减负」真源段与运行协议（防教训 #268）：00-主控 74063→75473（+1410）/ phase-order 55967→57344（+1377）。
#   属协议真源内容（非注释膨胀），已在 phase-order.yaml 挂 `pre_spawn_enforcement.context_budget_gate` 子门，并加 flow-check 规则 46 反向注入。
#   v2.12.72 补充：去除随包 YAML 内部教训编号后的诚实边界表述增加 27 B（57344→57371），非规则膨胀。
#   下次分层/瘦身时按实下调本节所有上限（只许降）。
# ⚠️ v2.12.70 扩容备案（A-治理瘦身分层 · 审计 P2-6 要求的「扩容说明」）：三个大文件微增，
#   原因 = `_shared/` 分层为 真源/ + 治理/ 后，大文件内引用的 `_shared/xxx.md` 前缀统一变为
#   `_shared/真源/xxx.md` / `_shared/治理/xxx.md`（每次引用 +3 字节），属**路径前缀机械变长**，
#   非内容膨胀：00-主控 73538→74028（+490）/ M-Gate 84250→84274（+24）/ phase-order 55272→55328（+56）。
#   分层完成后若后续做归档外移/内容瘦身，按实下调本节所有上限（只许降）。
# ⚠️ v2.12.70 修订回环规则增补备案：00-主控与 phase-order 增加版本号、T6/G14/P2 边界真源映射；上限同步至本次增补后的实测值，非为掩盖无关内容膨胀。
# ⚠️ v2.12.65 扩容备案（审计 P2-6 要求的「扩容说明」）：phase-order.yaml 54651 → 55272（+621 B），
#   原因 = 新增顶层 `silence_doctrine` 单一真源（跨状态机「静默 ≠ 有效决策」不变式 + 挂起类处置枚举），
#   配套 flow-check 规则 40 双向投影校验。该段是**真源内容**（非注释膨胀），同时已把头部 ⑬ 的 S-3
#   冗余复述压缩为指针（净增已扣减）。下次分层时按实下调本节所有上限。
BULK_RATCHET_CEIL="${LUNHENG_BULK_RATCHET:-$BULK_RATCHET_CEIL_DEFAULT}"
SKILL_MARGIN_WARN="${LUNHENG_SKILL_MARGIN_WARN:-300}"
BULK_RATCHET_OK=1
while IFS='|' read -r _bf _bceil; do
  [ -z "${_bf:-}" ] && continue
  if [ ! -f "$_bf" ]; then
    warn "门 Y: 体量棘轮目标文件缺失（$_bf）—— 本门清单须与实际文件同步（缺失即清单失效）"
    BULK_RATCHET_OK=0
    continue
  fi
  _bnow=$(wc -c < "$_bf" | tr -d '[:space:]')
  if [ "$_bnow" -le "$_bceil" ]; then
    pass "门 Y: 体量棘轮 $(basename "$_bf") ${_bnow} ≤ ${_bceil} B（只许降）"
  else
    warn "门 Y: $(basename "$_bf") 体量 ${_bnow} B > 上限 ${_bceil} B —— 请分层/外移内容，**不要**放宽本上限"
    BULK_RATCHET_OK=0
  fi
done <<EOF
$(echo "$BULK_RATCHET_CEIL" | tr ',' '\n')
EOF
# ---- 棘轮重定台账（v2.15.9 增补，审计 P1「合法上涨通道」修复）----
# 语义：上涨本身不是错误，但必须是**有账的债务** —— 每次重定须登记回落目标 + 截止版本。
# 判据（软门，与门 Y 同语义，不进 exit code）：
#   ① 未过期债务计数（status=open 且当前 minor >= due minor）→ 逐条点名；
#   ② 台账不可解析 / 声明文件缺失 → 告警；
#   ③ 零未结 → pass。
# 真源 = references/_shared/治理/ratchet-ledger.md（维护者侧，随包排除）。
RATCHET_LEDGER="${LUNHENG_RATCHET_LEDGER:-references/_shared/治理/ratchet-ledger.md}"
if [ -f "$RATCHET_LEDGER" ] && command -v python3 >/dev/null 2>&1; then
  _CUR_VER="$(grep -m1 -E '^[[:space:]]*version:' SKILL.md | sed -E 's/^[[:space:]]*version:[[:space:]]*//;s/["'"'"']//g;s/[[:space:]]*$//')"
  _LEDGER_OUT="$(python3 - "$RATCHET_LEDGER" "$_CUR_VER" "$BULK_RATCHET_CEIL" <<'PYEOF'
import re, sys
ledger_path, cur_ver, ceil_raw = sys.argv[1:4]
try:
    text = open(ledger_path, encoding="utf-8").read()
except OSError:
    print("LEDGER_UNREADABLE"); raise SystemExit(0)

def vkey(v):
    parts = re.findall(r"\d+", str(v))
    return tuple(int(x) for x in parts[:3]) if parts else (0,)

lines = text.splitlines()
items, cur = [], None
for ln in lines:
    m = re.match(r"^\s*-\s*path:\s*(.+?)\s*$", ln)
    if m:
        if cur: items.append(cur)
        cur = {"path": m.group(1).strip().strip('"').strip("'"), "status": "?", "due": "0"}
        continue
    if cur is None:
        continue
    ms = re.search(r"^\s*status:\s*[\"']?(\w+)", ln)
    md = re.search(r"^\s*due_version:\s*[\"']?([0-9.]+)", ln)
    if ms: cur["status"] = ms.group(1)
    if md: cur["due"] = md.group(1)
    # 顶层新块（非 debt 项）终止收集
    if re.match(r"^structural_exempt:", ln): break
if cur: items.append(cur)
if not items: print("LEDGER_UNPARSABLE"); raise SystemExit(0)
open_items, expired = [], []
for it in items:
    if it["status"] != "open": continue
    open_items.append((it["path"], it["due"]))
    if cur_ver and vkey(cur_ver) >= vkey(it["due"]):
        expired.append(f"{it['path'].rsplit('/',1)[-1]} (due {it['due']})")


if expired:
    print("LEDGER_EXPIRED\t" + " / ".join(expired))
elif open_items:
    print(f"LEDGER_OPEN\t{len(open_items)} 条未结（最近截止 {max(d for _, d in open_items)}）")
else:
    print("LEDGER_CLEAN\t0")
PYEOF
)"
  _LEDGER_VERDICT="$(printf '%s\n' "$_LEDGER_OUT" | head -1 | cut -f1)"
  _LEDGER_DETAIL="$(printf '%s\n' "$_LEDGER_OUT" | head -1 | cut -f2-)"
  # 结论并入下方「清单全部在位」行（门 Z 项数棘轮：只许降，不新增结论行）
  case "$_LEDGER_VERDICT" in
    LEDGER_CLEAN)   _RATCHET_LEDGER_NOTE="棘轮无未结债务" ;;
    LEDGER_OPEN)    _RATCHET_LEDGER_NOTE="台账 $_LEDGER_DETAIL" ;;
    LEDGER_EXPIRED) _RATCHET_LEDGER_NOTE="⚠ 债务已过期未回落：$_LEDGER_DETAIL"
                    warn "门 Y: 棘轮债务已过期未回落：$_LEDGER_DETAIL —— 请分层/外移后下调上限并销账，**不得**再次重定（台账 §四-3）" ;;
    *)              _RATCHET_LEDGER_NOTE="⚠ 台账不可解析或缺失"
                    warn "门 Y: 棘轮台账不可解析或缺失（$RATCHET_LEDGER）—— 重定上涨将失去账本约束" ;;
  esac
else
  _RATCHET_LEDGER_NOTE="⚠ 台账检查未执行"
  warn "门 Y: 棘轮台账检查未执行（缺 $RATCHET_LEDGER 或 python3）—— 重定上涨将失去账本约束"
fi

if [ "$BULK_RATCHET_OK" = "1" ]; then
  pass "门 Y: 必读文件体量棘轮清单全部在位且未回涨（${_RATCHET_LEDGER_NOTE:-台账未检}）"
else
  # 2026-10-08 修（N-1）：此前本分支**什么都不发** —— 超限只在循环里 `warn`，而 `warn` 既不进
  #   FAILED[] 也不调 `_record_gate_id`，于是「只许降」棘轮形同建议：2026-10-08 当日实测两次
  #   （超限 +273 B、超限 +94 B）gate 均为 PASS 42 / FAIL 0 且 `exit 0`。
  #   即「不会失败的门等于没有门」。现补一条聚合 fail：`_record_gate_id` 对 Y 幂等（case 去重），
  #   不影响门 0 的 29 门对账；本行位于门 0 之前，顺序正确。
  fail "门 Y: 体量棘轮超限（只许降不可绕）" \
       "见上方 ⚠ 逐文件超限行；修法 = 分层/外移到旁侧真源，**不得**放宽上限（已论证的例外走 LUNHENG_BULK_RATCHET 环境变量）"
fi

if [ -n "${SKILL_CHARS:-}" ]; then
  SKILL_MARGIN=$((SKILL_CHARS_CEIL - SKILL_CHARS))
  if [ "$SKILL_MARGIN" -lt "$SKILL_MARGIN_WARN" ]; then
    warn "门 Y: SKILL.md 字符余量仅 ${SKILL_MARGIN}（< ${SKILL_MARGIN_WARN}）—— 余量枯竭易诱发「改 A 漏 B」，请先外移长内容而非边删边加"
  else
    pass "门 Y: SKILL.md 字符余量 ${SKILL_MARGIN} ≥ ${SKILL_MARGIN_WARN}"
  fi
fi

# =============================================================================
# 门 W：官方 SKILL.md 校验器（v2.12.37 新增，回应全量审计 P0-1）
#   background：2026-09-13 全量审计发现 —— 项目自审 25 门全绿，但**官方**
#   `skills/skill-creator/scripts/quick_validate.py` 直接拒收（description 含尖括号
#   `<>`）。“自审全绿 + 官方红”属典型的门覆盖缺口：入口文档能否被平台加载，
#   必须由官方校验器说了算，不能被自家门的 PASS 数字掩盖。
#   未找到校验器时：默认仅警告；设 LUNHENG_REQUIRE_QUICK_VALIDATE=1 则硬失败（CI 应用）。
# =============================================================================
QUICK_VALIDATE=""
for _qv in \
  "$HOME/.npm-global/lib/node_modules/openclaw/skills/skill-creator/scripts/quick_validate.py" \
  "$(npm root -g 2>/dev/null)/openclaw/skills/skill-creator/scripts/quick_validate.py" \
  "/usr/lib/node_modules/openclaw/skills/skill-creator/scripts/quick_validate.py"; do
  if [ -n "$_qv" ] && [ -f "$_qv" ]; then QUICK_VALIDATE="$_qv"; break; fi
done

if [ -z "$QUICK_VALIDATE" ]; then
  if [ "${LUNHENG_REQUIRE_QUICK_VALIDATE:-0}" = "1" ]; then
    fail "门 W: 官方 quick_validate.py 未找到" "LUNHENG_REQUIRE_QUICK_VALIDATE=1 但校验器缺失"
  else
    skip "门 W: 官方 quick_validate.py 不可达" "本轮未执行（CI 请设 LUNHENG_REQUIRE_QUICK_VALIDATE=1；本门覆盖缩小，非全绿）"
  fi
elif GATE_W_OUT="$(python3 "$QUICK_VALIDATE" . 2>&1)"; then
  pass "门 W: 官方 SKILL.md 校验器通过（quick_validate.py）"
else
  fail "门 W: 官方 SKILL.md 校验失败" "$(printf '%s' "$GATE_W_OUT" | head -3 | tr '\n' ' ')"
fi

# =============================================================================
# 门 X：Markdown 围栏相位 + 声明式锚点 + 伪 H1（v2.12.58 新增，教训 #424/#426）
#   历史教训：references/_shared/真源/M-Gate-核心.md 曾有 2 个 M 门标题
#   (M-Exist-3 / M-Integrity-1) 被裹进代码围栏，7 行伪代码注释落到块外被
#   渲染为文档 H1；根因是围栏配对错位。
#   判据扩围（教训 #427）：原 X.1/X.2 只锚 M-Gate 单文件 ⇒ 同类缺陷在其余文档
#   长期漏检；改为「全仓 X.4 + 声明式锚点表 X.2」后立即抓到第二例同类缺陷
#   （references/pipeline-readme.md 7 个围栏 = 未闭合 ⇒ 尾部 57 行被吞）。
#     X.1  M-Gate-核心.md 围栏总数为偶数（错位会变奇数）
#     X.2  **声明式锚点表**：每项「文件 → 锚点正则」的锚点必须全部在围栏外
#          （新增锚点 = 加一行；锚点改名须同批改本表）
#     X.3  全仓：围栏外「紧跟围栏且首字符为 #」的伪 H1 = 0
#     X.4  全仓 .md 围栏总数均为偶数（未闭合围栏 = 尾部整块被吞）
# =============================================================================
MGATE=references/_shared/真源/M-Gate-核心.md
if [ -f "$MGATE" ]; then
  # X.1：围栏总数偶数
  FENCE_COUNT=$(grep -cE '^[[:space:]]*(`{3,}|~{3,})' "$MGATE" 2>/dev/null || echo 0)
  if [ $((FENCE_COUNT % 2)) -eq 0 ]; then
    pass "门 X.1: M-Gate-核心.md 围栏总数偶数（$FENCE_COUNT 个）"
  else
    fail "门 X.1: M-Gate-核心.md 围栏总数为奇数" "$FENCE_COUNT 个，疑似配对错位"
  fi

else
  skip "门 X.1: 围栏总数偶数" "M-Gate-核心.md 不存在，本轮未执行"
fi

# X.2：声明式语义锚点表（v2.12.58 起；教训 #427）
#   判据：锚点行**落在围栏内** = 该小节渲染后不可见/被吞（围栏错位的最坏后果）。
#   只登记「定义型 / 高可见度」文档的锚点；模板/样例文件里围栏内的标题是**内容**，
#   不得登记（否则每份模板都会误红）。
#   条目格式：<文件>@@<锚点正则（awk ERE）>@@<说明>
#   ⚠️ 分隔符必须是 `@@` —— 锚点正则内含 `|` 交替，用 `|` 分隔会被 `${x%%|*}` 截断
#   （v2.12.58 实测：截断后正则失效 ⇒ 本门变空转绿灯；变异单测把它抓了出来）。
#   配套「正向样本」自检：每个锚点正则必须至少命中 1 行，否则判失效（同族教训 #334/#421）。
ANCHOR_TABLE=(
  "references/_shared/真源/M-Gate-核心.md@@^#{2,4}[[:space:]]+M-(Form|Exist|Integrity)-[0-9]+:@@13 个 M 门标题（8 Form + 3 Exist + 2 Integrity）"
  "references/pipeline-readme.md@@^##[[:space:]]+(全景与阶段顺序|status\.md 状态机|模板加载策略|设计文档加载策略)@@4 个章节锚点"
)
ANCHOR_INSIDE=""
ANCHOR_N=0
for _entry in "${ANCHOR_TABLE[@]}"; do
  _af="${_entry%%@@*}"; _rest="${_entry#*@@}"; _apat="${_rest%%@@*}"
  ANCHOR_N=$((ANCHOR_N + 1))
  if [ ! -f "$_af" ]; then
    ANCHOR_INSIDE="$ANCHOR_INSIDE [missing:$_af]"
    continue
  fi
  if [ -z "$_apat" ] || [ "$_rest" = "$_entry" ]; then
    ANCHOR_INSIDE="$ANCHOR_INSIDE [malformed-entry:$_af（缺 @@ 分隔或锚点正则）]"
    continue
  fi
  # 正向样本：锚点正则必须命中文档（换名/写错即判失效，不让门静默空转）
  _total=$(grep -cE "$_apat" "$_af" 2>/dev/null || true)
  if [ "${_total:-0}" -eq 0 ]; then
    ANCHOR_INSIDE="$ANCHOR_INSIDE [pattern-hits-nothing:$_af（锚点正则已失效）]"
    continue
  fi
  _hit=$(awk -v pat="$_apat" '
    /^[[:space:]]*(`{3,}|~{3,})/{ infence = !infence; next }
    infence && $0 ~ pat { print FILENAME ":" NR ":" $0 }
  ' "$_af")
  if [ -n "$_hit" ]; then
    ANCHOR_INSIDE="$ANCHOR_INSIDE [$(echo "$_hit" | head -3 | tr '\n' '|')]"
  fi
done
if [ -z "$ANCHOR_INSIDE" ]; then
  pass "门 X.2: 声明式锚点表 $ANCHOR_N 项全部在围栏外（M 门 13 标题 + pipeline-readme 4 章节）"
else
  fail "门 X.2: 声明式锚点落在围栏内（渲染后不可见）" "$ANCHOR_INSIDE"
fi

# X.3：围栏外「伪 H1」—— 仅扫「紧跟围栏行且首字符为 # 的标题行」
# 这是围栏错位的真实信号：伪代码注释（含 # 注释）原本应在代码块内，
# 因闭合围栏被错甩到块外，开头就被渲染成 H1。
# 排除 CHANGELOG-archive.md（历史归档，允许多 H1 发布说明）。
FAKE_H1=$(find . -type f -name '*.md' \
  -not -path './outputs/*' -not -path './reports/*' -not -path './memory/*' \
  -not -path './node_modules/*' -not -path './.git/*' \
  -not -name 'CHANGELOG-archive.md' \
  -not -name 'changelog-cold-*.md' \
  -exec awk '
    function is_fence(s){ return s ~ /^[[:space:]]*(`{3,}|~{3,})/ }
    {
      if (is_fence($0)) {
        prev_is_fence = 1
        infence = !infence
        next
      }
      if (infence) { prev_is_fence = 0; next }
      # 围栏外：检查是否「上一行就是围栏」+「本行是 # 伪 H1」
      if (prev_is_fence && $0 ~ /^#[^#]/) {
        print FILENAME ":" NR ":" $0
      }
      prev_is_fence = 0
    }
  ' {} \; 2>/dev/null)
if [ -z "$FAKE_H1" ]; then
  pass "门 X.3: 围栏外无紧跟围栏的 # 伪 H1（围栏错位零）"
else
  fail "门 X.3: 围栏外存在紧跟围栏的 # 伪 H1" "$(echo "$FAKE_H1" | head -5 | tr '\n' '|')"
fi

# X.4：全仓「围栏相位」——未闭合围栏 = 文件尾部被整块吞进代码块。
#   实测（教训 #427）：references/pipeline-readme.md 7 个围栏 ⇒ 尾部 57 行被吞，
#   由 v2.12.54 全景收敛的删除残留引入（删了开围栏、留下闭围栏）。
#   ⚠️ v2.13.x 审计修订（R-07）：原判据只算 `n % 2`（总数奇偶）——「两个开围栏 + 零个闭围栏」
#     这类**双开**形态总数仍为偶数，本门照过（2026-09-25 审计构造 zzz-probe.md 实测复现）。
#     而「双开围栏」恰是尾部被吞这一故障的最常见形态。现改为**状态机**：逐行翻转 inside，
#     收尾仍在围栏内即判红（与门 X.2 的 awk 范式同源）。
ODD_FENCES=$(find . -type f -name '*.md' \
  -not -path './outputs/*' -not -path './reports/*' -not -path './memory/*' \
  -not -path './node_modules/*' -not -path './.git/*' \
  -exec awk '
    function is_fence(s){ return s ~ /^[[:space:]]*(`{3,}|~{3,})/ }
    { if (is_fence($0)) { inside = !inside; opened++ } }
    END { if (inside) print FILENAME "(未闭合：末行仍在代码块内，共 " opened " 个围栏行)" }
  ' {} \; 2>/dev/null)
if [ -z "$ODD_FENCES" ]; then
  pass "门 X.4: 全仓 .md 围栏相位收尾闭合（状态机判定，无未闭合围栏）"
else
  fail "门 X.4: 存在未闭合围栏（其尾部内容会被吞进代码块）" "$(echo "$ODD_FENCES" | head -5 | tr '\n' '|')"
fi

# AC：跨文档合同、paper-ready fail-closed 与 Markdown 基础结构（本轮 P0/P1 机械收口）
# 合同门必须执行：其内部负责真源多值簇、lite/full 必填字段、dispatch 关键合同、
# 语言政策受管文件完整性与 status gate telemetry 字段。paper-ready 反例与结构 lint
# 由 pytest/独立脚本验证；缺失脚本或任一检查失败均不得静默跳过。
if command -v python3 >/dev/null 2>&1 && [ -f scripts/contract-check.py ] && [ -f scripts/markdown-structure-lint.py ]; then
  AC_OUT=""
  if ! AC_OUT="$(python3 scripts/contract-check.py 2>&1)"; then
    fail "门 AC: 跨文档合同/语言政策/模板遥测不一致" "$(printf '%s' "$AC_OUT" | tail -10 | tr '\n' '|')"
  elif ! AC_OUT="$(python3 scripts/markdown-structure-lint.py --check 2>&1)"; then
    fail "门 AC: Markdown 基础结构 lint 失败" "$(printf '%s' "$AC_OUT" | tail -10 | tr '\n' '|')"
  elif ! AC_OUT="$(python3 -m pytest -q tests/test_paper_ready_check.py tests/test_scripts_index.py 2>&1)"; then
    fail "门 AC: paper-ready/脚本索引反例回归失败" "$(printf '%s' "$AC_OUT" | tail -12 | tr '\n' '|')"
  else
    pass "门 AC: 跨文档合同 + paper-ready fail-closed + Markdown 基础结构通过"
  fi
else
  fail "门 AC: 新增机械门不可执行" "缺 python3 或 contract-check.py 或 markdown-structure-lint.py（fail-closed）"
fi

# =============================================================================
# 总结（v2.12.30 修：计分必须在**全部门执行之后** —— 原位置在门 S/门 T 之前，
#   导致这两门的失败不进入 TOTAL_FAIL，脚本仍以 exit 0 收尾 = 假绿灯）
# =============================================================================
# 门 Z：自审门项数软上限（v2.12.70 方案 A 第③步「规则软上限」）
#   语义：软门（warn 级，不计 exit code）；项数只许降 —— 加门前先合并/退役旧门，
#   治「规则的规则」内卷。检查的是门 A-X 的项数（不含门 Z 自身）。
# =============================================================================
# 门 AA：流程真源 vs 装配视图一致性（v2.13.5，审计修订 R-21 增量 2）
#   布局（倒置后）：真源 = 真源/phase-order/ 目录（index.yaml 契约 + 路由，25 个节点切片）；
#     真源/phase-order.yaml = **装配视图（生成物）**，保留原路径供 flow-check / 门 S /
#     既有引用继续读取（只倒置作者权，不动消费路径）。
#   为什么必须逐字节校验：**漂移的装配视图比没有视图更危险** —— 主控与 flow-check
#     会照着一份过时判据推进。手改生成物、改切片未重生成、孤儿切片、路由与正文不一致
#     四类都要在提交前当场判红。
#   判据：维护者侧生成器 --check；任何差异 / 缺失 / 多余即红。
# =============================================================================
if [ -f scripts/phase-order-slice.py ] && command -v python3 >/dev/null 2>&1; then
  if GATE_AA_OUT="$(python3 scripts/phase-order-slice.py --check 2>&1)"; then
    pass "门 AA: 流程真源装配视图与切片真源逐字节一致"
  else
    fail "门 AA: 装配视图与流程真源不一致（手改生成物 / 改真源未重生成）" "$(printf '%s' "$GATE_AA_OUT" | tail -3 | tr '\n' '|')"
  fi
else
  if [ ! -f scripts/phase-order-slice.py ]; then
    fail "门 AA: 未执行（切片生成器缺失）" "scripts/phase-order-slice.py 不存在 ⇒ 本门不可判定（不允许静默跳过）"
  else
    fail "门 AA: 未执行（缺 python3）" "本门不可判定（不允许静默跳过）"
  fi
fi

GATE_COUNT_CEIL=40
# v2.13.x 审计修订（R-08）：项数口径改为 **PASS + FAIL**。原写 `${#PASSED[@]}` ⇒ 一旦有门失败，
#   分母反而变小，「只许降」的软上限在失败时变松（失败越多越容易「合规」）。软门语义（warn，
#   不计 exit code）保持不变，只修正计数。
_GATE_AX_COUNT=$(( ${#PASSED[@]} + ${#FAILED[@]} ))
if [ "$_GATE_AX_COUNT" -le "$GATE_COUNT_CEIL" ]; then
  pass "门 Z: 自审门项数 ${_GATE_AX_COUNT}（PASS ${#PASSED[@]} + FAIL ${#FAILED[@]}） ≤ ${GATE_COUNT_CEIL}（软上限，只许降）"
else
  warn "门 Z: 自审门项数 ${_GATE_AX_COUNT} > 软上限 ${GATE_COUNT_CEIL} —— 加门前先合并/退役旧门，不要放宽本上限"
fi

# 门 0：门清单对账（必须在门 Z 发射后执行，才能真实检查 Z）
GATE_NO_VERDICT=""
for _dg in "${DECLARED_GATES[@]}"; do
  case " $SEEN_GATE_IDS " in
    *" $_dg "*) ;;
    *) GATE_NO_VERDICT="${GATE_NO_VERDICT} ${_dg}" ;;
  esac
done
if [ -n "$GATE_NO_VERDICT" ]; then
  fail "门 0: 门清单对账（声明的门必须都有 PASS/FAIL/SKIP 结论）" "无结论:${GATE_NO_VERDICT}（门静默消失 = 门的自身健康无人检查）"
else
  pass "门 0: 门清单对账（${#DECLARED_GATES[@]} 门全部有 PASS/FAIL/SKIP 结论）"
fi
if [ ${#SKIPPED[@]} -gt 0 ]; then
  warn "门 0: SKIP 配额 ${#SKIPPED[@]} —— 覆盖缩小（非全绿）：$(printf '%s | ' "${SKIPPED[@]}")"
fi

TOTAL_PASS=${#PASSED[@]}
TOTAL_FAIL=${#FAILED[@]}

echo ""
echo "========================================="
echo -e "PASS: ${GREEN}${TOTAL_PASS}${NC}  FAIL: ${RED}${TOTAL_FAIL}${NC}"
echo "========================================="

if [ $TOTAL_FAIL -gt 0 ]; then
  echo ""
  echo -e "${RED}失败项：${NC}"
  for f in "${FAILED[@]}"; do
    echo "  - $f"
  done
  echo ""
  echo -e "${RED}❌ 自审门失败，请修复后再 commit${NC}"
  exit 1
else
  echo -e "${GREEN}✅ 自审门全过，可以 commit${NC}"
  exit 0
fi
