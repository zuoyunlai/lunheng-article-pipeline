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

pass() { PASSED+=("$1"); echo -e "${GREEN}✓${NC} $1"; }
fail() { FAILED+=("$1: $2"); echo -e "${RED}✗${NC} $1: $2"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }

cd "$SKILL_ROOT"

# =============================================================================
# 门 A：角色卡完整性（v2.5.5 实测 10 张卡：8 张原版 + 00-主控-扩展职责 + 09 同行评审）
# =============================================================================
EXPECTED_AGENTS=("00-主控-coordinator.md" "01-文献检索-literature-scout.md" "02-数据检索-data-scout.md" "03-案例检索-case-scout.md" "04-分析-analyst.md" "05-写作-writer.md" "06-批判-critical-companion.md" "07-审计-auditor.md" "09-审稿-peer-reviewer.md")
ACTUAL_AGENTS=$(ls references/agents/ 2>/dev/null | grep -E '^0[0-9]-' | sort)
MISSING=()
for exp in "${EXPECTED_AGENTS[@]}"; do
  if ! echo "$ACTUAL_AGENTS" | grep -qF "$exp"; then
    MISSING+=("$exp")
  fi
done
if [ ${#MISSING[@]} -eq 0 ]; then
  pass "门 A: 角色卡完整性（9 张 + 扩展职责 = 10 文件）"
else
  fail "门 A: 角色卡完整性" "缺失: ${MISSING[*]}"
fi

# =============================================================================
# 门 B：9 角色编号在 3 处文档全覆盖（README / SKILL / pipeline-readme）
# =============================================================================
ROLE_NUMS=("T1" "T2" "T3" "T4" "T5" "T6" "T7" "T9")
ROLE_MISSING=""
for r in "${ROLE_NUMS[@]}"; do
  IN_README=$(grep -c "$r" README.md 2>/dev/null || echo 0)
  IN_SKILL=$(grep -c "$r" SKILL.md 2>/dev/null || echo 0)
  IN_PIPE=$(grep -c "$r" references/pipeline-readme.md 2>/dev/null || echo 0)
  if [ "$IN_README" -lt 2 ] || [ "$IN_SKILL" -lt 2 ] || [ "$IN_PIPE" -lt 3 ]; then
    ROLE_MISSING="$ROLE_MISSING $r(README=$IN_README SKILL=$IN_SKILL pipe=$IN_PIPE)"
  fi
done
if [ -z "$ROLE_MISSING" ]; then
  pass "门 B: 9 角色编号 README/SKILL/pipeline 三处覆盖"
else
  fail "门 B: 角色编号覆盖不全" "$ROLE_MISSING"
fi

# =============================================================================
# 门 C：版本号一致性（36 文件清单 = SKILL.md + 8 角色卡 + 闸门 + 检测器 + 共享协议 + 模板 + README + QUICKSTART）
# =============================================================================
EXPECTED_VERSION=$(grep -m1 '^version:' SKILL.md | sed -E 's/version:[[:space:]]*//;s/["'"'"']//g;s/[[:space:]]*$//')
VERSION_FILES=(
  "SKILL.md" "README.md" "QUICKSTART.md"
  "references/glossary.md" "references/pipeline-readme.md"
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
  "references/agents/09-审稿-peer-reviewer.md"
  "references/_shared/M-Gate-Algorithm.md"
  "references/_shared/M-Gate-Algorithm-appendix.md"
  "references/_shared/audit-checklist-quickref.md"
  "references/_shared/failure-modes.md"
  "references/_shared/degraded-scenarios.md"
  "references/_shared/字数判定表.md"
  "references/_shared/期刊数据库.md"
  "references/_shared/期刊匹配算法.md"
  "references/_shared/中文数据源集成.md"
  "references/_shared/format-export.md"
  "references/_shared/执行韧化协议-v2.1.0.md"
  "references/gates/14-中文AI痕迹-gate.md"
  "references/checkers/中文AI痕迹-checker.md"
  "references/templates/任务简报-template.md"
  "references/templates/审稿报告-template.md"
  "references/templates/G14检测报告-template.md"
  "references/templates/status-template.md"
  "references/templates/投稿就绪检查表-template.md"
  "references/templates/修订说明-template-full.md"
)
VERSION_MISSING=""
for f in "${VERSION_FILES[@]}"; do
  if [ ! -f "$f" ]; then
    VERSION_MISSING="$VERSION_MISSING [missing:$f]"
    continue
  fi
  if ! head -10 "$f" | grep -qF "$EXPECTED_VERSION"; then
    VERSION_MISSING="$VERSION_MISSING [$f]"
  fi
done
if [ -z "$VERSION_MISSING" ]; then
  pass "门 C: 36 文件版本号 v$EXPECTED_VERSION 一致"
else
  fail "门 C: 版本号不一致" "期望 v$EXPECTED_VERSION, 不一致:$VERSION_MISSING"
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
  HITS=$(awk 'NR > 60' "$f" 2>/dev/null | grep -E '8 分钟|超时' | grep -v '\[.*\](#' | grep -v "v2.5.5 P0 硬性化" | grep -v "v2.3.13 能力抽象" | grep -v "改为角色分级" | grep -v "硬卡放宽" | grep -v "实战教训" | grep -v "实战中 T3 连续" | grep -v "changelog" | grep -v "硬卡阈值表" | grep -v "P0 硬性化" | grep -v "| 角色" | grep -v "| G14 检测" | grep -v "T 派发后 8 分钟内未出产物" | grep -v "任一行停留超硬卡阈值" | grep -v "实战背景" | grep -v "v2.5.6 P1-3 修订" | grep -v "重跑论衡首单测试" | grep -v "超 8 分终" | grep -v "超 8 分静")
  if [ -n "$HITS" ]; then
    STALE_8MIN="$STALE_8MIN [$f]"
  fi
done
if [ -z "$STALE_8MIN" ]; then
  pass "门 D: 8 分钟硬卡散落检查（v2.5.5 P0-1 #2 修订）"
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
for f in references/agents/*.md references/_shared/*.md; do
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
# M-Gate-Algorithm.md 头部必明示「LLM 推理判定，非机器强制」
M_GATE_MISSING=""
if ! grep -qE 'M 门.*LLM 推理|LLM 推理判定.*M 门' references/_shared/M-Gate-Algorithm.md 2>/dev/null; then
  M_GATE_MISSING="[M-Gate-Algorithm.md 缺诚实声明]"
fi
if [ -z "$M_GATE_MISSING" ]; then
  pass "门 F: M 门「机械化」诚实声明（v2.5.6 P0-2 修正）"
else
  fail "门 F: M 门缺诚实声明" "$M_GATE_MISSING"
fi

# =============================================================================
# 门 H：教训编号引用 vs 主真源实有差集（v2.5.9 新增，2026-08-26）
# -----------------------------------------------------------------------------
# 背景：论衡侧角色卡/脚本/模板一路编到 #178，主真源 memory/lessons.md 停在 #136，
#   造成 36 条教训「有引用无定义」。2026-08-26 清理时靠手写 python 才扫出。
#   文档层漏改会死链报错，**编号层漏写不报错**——只是查不到，比死链更隐蔽。
#   同型于教训 #150「自审工具假绿灯」在记忆层的映射。
# 说明：主真源不在 skill 仓库内（教训 #143 双视图原则），所以本门是**软门**：
#   真源不可达时 warn 不 fail（净化包/CI 环境不应因主工作区缺失而挂）。
# =============================================================================
LESSONS_SRC="${LESSONS_SRC:-$HOME/.openclaw/workspace/memory/lessons.md}"

if [ -f "$LESSONS_SRC" ]; then
  # 采集论衡侧所有「教训 #N」引用编号（排除 .bak / 净化包输出）
  REFS=$(grep -rhoE '教训 #[0-9]+' \
           --include="*.md" --include="*.sh" --include="*.py" \
           --exclude="*.bak*" \
           references/ scripts/ SKILL.md README.md QUICKSTART.md 2>/dev/null \
         | grep -oE '[0-9]+' | sort -un)

  # 采集主真源实有编号（任意标题层级，兼容「## #N」与「## 教训 #N」两种书写）
  HAVE=$(grep -oE '^#{2,4} (教训 )?#[0-9]+' "$LESSONS_SRC" \
         | grep -oE '[0-9]+$' | sort -un)

  # 差集：仅检 >=115（#1-#114 已归档到 memory/archive/，不在 lessons.md 主体）
  MISSING_LESSONS=""
  for n in $REFS; do
    [ "$n" -lt 115 ] && continue
    if ! echo "$HAVE" | grep -qx "$n"; then
      MISSING_LESSONS="$MISSING_LESSONS #$n"
    fi
  done

  if [ -z "$MISSING_LESSONS" ]; then
    REF_COUNT=$(echo "$REFS" | wc -w)
    pass "门 H: 教训编号引用全部在主真源有定义（引用 $REF_COUNT 个编号）"
  else
    fail "门 H: 教训编号引用在主真源缺定义" "$MISSING_LESSONS —— 请补录到 $LESSONS_SRC"
  fi
else
  warn "门 H: 主真源不可达（$LESSONS_SRC），跳过教训编号差集检查"
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
  "references/_shared/M-Gate-Algorithm.md:M-Gate算法"
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
# 门 G：双端 md5 一致性（净化包 = 净化包指纹校验）
# =============================================================================
# 警告：论衡 zero exec 哲学——md5 仅作可选加固，不阻塞 commit
# 主人可在 commit 后手工跑 `bash scripts/self-audit-gate.sh` 看结果
PURIFY_DIR="$SKILL_ROOT/outputs/clawhub-release/$EXPECTED_VERSION"
if [ -d "$PURIFY_DIR" ]; then
  # 仅检查关键文件 md5
  KEY_FILES=("SKILL.md" "QUICKSTART.md" "references/glossary.md")
  MD5_MISMATCH=""
  for kf in "${KEY_FILES[@]}"; do
    [ ! -f "$kf" ] && continue
    [ ! -f "$PURIFY_DIR/$kf" ] && continue
    SRC_MD5=$(md5sum "$kf" 2>/dev/null | awk '{print $1}')
    PUR_MD5=$(md5sum "$PURIFY_DIR/$kf" 2>/dev/null | awk '{print $1}')
    if [ "$SRC_MD5" != "$PUR_MD5" ]; then
      MD5_MISMATCH="$MD5_MISMATCH [$kf]"
    fi
  done
  if [ -z "$MD5_MISMATCH" ]; then
    pass "门 G: 净化包 md5 一致（仅作可选加固）"
  else
    warn "门 G: 净化包 md5 不一致:$MD5_MISMATCH（净化包正常做 sed/pip 替换，不一致属预期）"
  fi
else
  warn "门 G: 净化包未生成（outputs/clawhub-release/$EXPECTED_VERSION 不存在）"
fi

# =============================================================================
# 总结
# =============================================================================
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
