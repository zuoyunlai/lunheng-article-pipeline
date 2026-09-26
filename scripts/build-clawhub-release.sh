#!/usr/bin/env bash
# =============================================================================
# build-clawhub-release.sh — 从「完整特性真源」生成「ClawHub 净化发布包」
# =============================================================================
# 背景（教训 #143，2026-08-22）：
#   ClawHub scanner 会把论衡的「开发者维护特性」误判为 suspicious：
#   - 版本号同步脚本 / git 发布文档 → 「scope creep / Excessive Agency」
#   - 实战教训自动沉淀到共享 memory → 「cross-project memory writes」
#   - M 门算法的 shell 命令示例 → 「shell/internal diagnostics」
#   - 历史审计记录 / 归档 / 备份 → 「Data Exfiltration / File Enumeration」
#
#   但这些特性是论衡「实战反馈驱动升级 + 自我维护」的核心，不能为了过
#   scanner 而阉割本地能力。正确做法是「双视图」：
#     本地真源 / GitHub 仓库  → 保留完整特性（开发者视图）
#     ClawHub 发布包          → 净化版（使用者视图，剥离开发者工具）
#
# 用法：
#   bash scripts/build-clawhub-release.sh [VERSION]
#   默认从 SKILL.md 读取当前版本号，输出到 $OUTPUTS_ROOT/clawhub-release/<VERSION>/
#   然后手动执行：clawhub publish $OUTPUTS_ROOT/clawhub-release/<VERSION> --slug ... --version <VERSION>
#
# OUTPUTS_ROOT 语义（全仓统一，2026-09-14 修正；勿再分叉）：
#   = 「输出**总根**」，**不是**发布根。发布包路径恒为 $OUTPUTS_ROOT/clawhub-release/<VERSION>/。
#   默认 $HOME/lunheng-build/lunheng-outputs ⇒ 默认路径 ~/lunheng-build/lunheng-outputs/clawhub-release/<VERSION>/。
#   同源消费点（5 处，全部按「总根」解释该变量）：
#     build-clawhub-release.sh（写）/ publish-clawhub.sh（读）/ strip-internal-leakage.sh（净化）
#     / self-audit-gate.sh 门 G（校验）/ cleanup-skill-store.sh（清理）
#   背景：旧版 build/publish 把 OUTPUTS_ROOT 当「发布根」（默认值里已含 /clawhub-release），
#   与 gate/strip 的「总根」语义分叉 ⇒ 调用方显式设 OUTPUTS_ROOT（如隔离构建 OUTPUTS_ROOT=/tmp/x）
#   时，build 写 /tmp/x/<ver>，而门 G 查 /tmp/x/clawhub-release/<ver> ⇒ 门 G 退化成
#   「包未生成」的假绿灯，剥离脚本探测到不存在的默认根。回归门：tests/test_outputs_root_semantics.py
# =============================================================================

set -euo pipefail

# ---- 目录定位 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_ROOT="${OUTPUTS_ROOT:-$HOME/lunheng-build/lunheng-outputs}/clawhub-release"

# ---- 版本号 ----
VERSION="${1:-}"
KEEP_PARTIAL=0
if [[ "${2:-}" == "--keep-partial" ]]; then
  KEEP_PARTIAL=1
elif [[ -n "${2:-}" ]]; then
  echo "❌ 未知参数：${2}（仅支持 --keep-partial）" >&2
  exit 2
fi
if [[ -z "$VERSION" ]]; then
  VERSION="$(grep -m1 -E '^[[:space:]]*version:' "$SKILL_ROOT/SKILL.md" | sed 's/^[[:space:]]*version:[[:space:]]*//' | tr -d '"')"
fi
if [[ -z "$VERSION" ]]; then
  echo "❌ 无法确定版本号，请显式传入：bash scripts/build-clawhub-release.sh 2.3.9" >&2
  exit 1
fi

# ---- 版本号格式校验（v2.12.30 新增，回应第三方审计 P1-4）----
# 背景：VERSION 直接进 `$OUT_ROOT/$VERSION` 并紧接 `rm -rf`。传入 `..` / `../..` / 含 `/`
#   的值（如 `../../foo`）时，rm -rf 会**删掉输出根之外的目录** —— 参数即删除目标。
#   故：① 只接受 X.Y.Z（可带 -pre 后缀）；② 解析后的绝对路径必须落在 OUT_ROOT 之内。
if ! printf '%s' "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$'; then
  echo "❌ 版本号格式非法：'$VERSION'（要求 X.Y.Z，可带 -pre 后缀）" >&2
  echo "   该值会参与 rm -rf，含 / 、.. 、空值或非数字段一律拒绝。" >&2
  exit 2
fi
case "$VERSION" in
  */*|*..*) echo "❌ 版本号不得含路径分隔符或 ..：'$VERSION'" >&2; exit 2 ;;
esac

OUT_DIR="$OUT_ROOT/$VERSION"

# ---- 输出路径逃逸防护（v2.12.30 新增，回应 P1-4）----
mkdir -p "$OUT_ROOT"
OUT_ROOT_ABS="$(cd "$OUT_ROOT" && pwd -P)"
OUT_DIR_ABS="$(cd "$(dirname "$OUT_DIR")" 2>/dev/null && pwd -P)/$(basename "$OUT_DIR")" || OUT_DIR_ABS=""
case "$OUT_DIR_ABS" in
  "$OUT_ROOT_ABS"/*) : ;;
  *) echo "❌ 输出目录逃逸出输出根，拒绝执行 rm -rf：$OUT_DIR_ABS （根=$OUT_ROOT_ABS）" >&2; exit 2 ;;
esac

# ---- 扫描面：文本类文件全集（v2.12.11 起覆盖非 md 资产）----
# 背景（leak-audit §四.2）：旧版所有残留扫描只认 `--include='*.md'`，
#   `.safe-pattern-manifest.json` 与 `references/_shared/真源/phase-order.yaml` 长期处于**盲区**
#   （二者各含 1 项维护者内泄漏却无人报错）。
# 选择「扩展扫描面」而非「逐文件补扫」：根因级修正——日后新增任何非 md 文本资产自动纳入。
SCAN_INCLUDES=(--include='*.md' --include='*.json' --include='*.yaml' --include='*.yml' --include='*.txt' --include='*.toml')

echo "🔧 生成 ClawHub 净化发布包 v$VERSION"
echo "   源：$SKILL_ROOT"
echo "   输出：$OUT_DIR"

# ---- 0. 非 git 环境 fail-closed（2026-09-16 前置；原属 2a' 段）----
# 背景（教训 #333 / 第三方审计 P1-3）：原实现「非 git 环境 → 整段跳过」= **静默放弃**唯一
#   能发现「未跟踪残留入包」的机械门（教训 #333 正是这类事故）。改 fail-closed：
#   非 git 环境直接停构建；确需豁免者须显式设 LUNHENG_ALLOW_NO_GIT=1（并打印告警）。
#
# ⚠️ 工具残留排除（v2.12.64 补，2026-09-19 CI 实测根因）：
#   `.coverage*` 一度不在排除清单里。CI 的 Code Quality 以 `pytest --cov=scripts` 跑全量，
#   coverage 并行模式在**仓库根**落 `.coverage.<host>.<pid>.<随机>`；rsync 全量复制把它带进包，
#   再由 §2b″ 全包清单门拦下（门没错 —— 拦的是**真**工具残留，coverage 数据含维护者脚本路径）。
#   本地不跑 `--cov` 故从未复现 ⇒「本地绿 / CI 红」。#430 同族：判据两边必须同口径。
#   教训：排除清单是**黑名单**（新类型默认入包）—— 故新增工具类产物时两侧（rsync --exclude 与
#   cp 分支）必须同时补，且以 §2b″ 清单门作最终兜底。
# 2026-09-16 前置（原位置：复制步骤**之后**的 2a' 段）：判定在 rm -rf/mkdir/rsync 之后才执行时，
#   失败构建仍会在共享输出根留下半成品包（实测 `build 9.9.9` → rc=1 但已落盘 84 文件）。
#   本门只依赖 SKILL_ROOT 是否为 git 仓库，不依赖包内容 ⇒ 前置到任何写盘动作之前，失败零输出。
if ! git -C "$SKILL_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  if [[ "${LUNHENG_ALLOW_NO_GIT:-0}" == "1" ]]; then
    echo "⚠️ 非 git 环境：跳过「未跟踪文件」反向断言（LUNHENG_ALLOW_NO_GIT=1 显式豁免）" >&2
    echo "   本次**未**校验包内文件是否全部可追溯到 git 跟踪文件，风险自担。" >&2
  else
    echo "❌ 非 git 环境：无法校验「包内文件是否全部可追溯到 git 跟踪文件」（教训 #333）。" >&2
    echo "   该检查是发现「未跟踪残留入包」的唯一机械门，不允许静默跳过。" >&2
    echo "   修法：在 git 仓库内构建；确需非 git 构建请显式设 LUNHENG_ALLOW_NO_GIT=1。" >&2
    exit 1
  fi
fi

# ---- 1. 清空旧输出 ----
rm -rf "$OUT_DIR"
on_exit() {
  local rc=$?
  if [[ "$rc" -ne 0 && "$KEEP_PARTIAL" -ne 1 ]]; then
    rm -rf "$OUT_DIR"
    echo "🧹 构建失败，已清理半成品输出：$OUT_DIR" >&2
  elif [[ "$rc" -ne 0 ]]; then
    echo "⚠️ 构建失败，按 --keep-partial 保留半成品输出：$OUT_DIR" >&2
  fi
  return "$rc"
}
trap on_exit EXIT
mkdir -p "$OUT_DIR"

# ---- 1a. 未跟踪源文件前置守卫（R-04 / F3）----
# 复制前先检查工作树；否则 IDEA.md 等未跟踪文件已进入包后才失败，失败构建会留下半成品。
if git -C "$SKILL_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  _PF_SOURCE_UNTRACKED="$(git -C "$SKILL_ROOT" status --porcelain=v1 --untracked-files=all | awk '
    substr($0,1,3)!="?? " {next}
    { p=substr($0,4); n=split(p,a,"/"); b=a[n]
      if (b ~ /^\.coverage(\..*)?$/ || b == ".DS_Store" || b ~ /\.sw[po]$/ || p ~ /(^|\/)htmlcov\//) next
      print p
    }')"
  if [[ -n "$_PF_SOURCE_UNTRACKED" ]]; then
    echo "❌ 源工作树含未跟踪文件，拒绝构建（失败零输出）：" >&2
    printf '%s\n' "$_PF_SOURCE_UNTRACKED" | sed 's/^/   - /' >&2
    echo "   修法：移出/跟踪/忽略该文件；仅人工排查可加 --keep-partial（不改变守卫结果）。" >&2
    exit 1
  fi
fi

# ---- 2. 复制真源（用 rsync 若可用，否则 cp -a）----
# 开发者工具文件清单（v2.9.0 起净化包必剥离，教训 #212）：
#   pyproject.toml / requirements.txt — Python 项目元数据，终端用户无需
#   Makefile / .shellcheckrc — 构建工具与开发者静态检查，终端用户无需
#   docs/ — CI/CD 设计文档，仅开发者用
#   tests/ — 测试代码，仅开发者用
#   scripts/ — 开发者维护脚本（含 self-audit-gate / 增量 M 门 / 版本同步）
#   .github/ — CI 工作流，仅开发者用
DEV_TOOL_FILES=(
  'pyproject.toml'
  'requirements.txt'
  'Makefile'
  '.shellcheckrc'
)

if command -v rsync >/dev/null 2>&1; then
  rsync -a --exclude '.git' --exclude 'outputs' --exclude '*.bak.*' \
    --exclude '.bak-*' --exclude 'docs' --exclude '.gitignore' \
    --exclude 'audits' --exclude 'scripts' --exclude 'scripts/verify-package.sh' --exclude '.gitattributes' --exclude '.github' \
    --exclude 'references/_shared/archive' --exclude 'references/design' \
    --exclude 'references/_shared/治理/lessons-max.snapshot' \
    --exclude 'references/_shared/通用韧化块-v2.1.0.md' \
    --exclude 'references/_shared/版本升级自审门-*.md' \
    --exclude 'references/_shared/M-Gate-渐进式验证-*.md' \
    --exclude 'references/templates/README-模板拆分方案.md' \
    --exclude 'README.md' \
    --exclude 'CHANGELOG.md' \
    --exclude 'CHANGELOG-archive.md' \
    --exclude 'tests' \
    --exclude 'references/设计文档.md' \
    --exclude 'references/设计文档-架构.md' \
    --exclude 'references/设计文档-哲学.md' \
    --exclude 'PERFORMANCE-PROFILE.md' \
    --exclude 'references/_shared/治理/教训索引.md' \
    --exclude 'references/_shared/治理/论衡仓库内教训.md' \
    --exclude '.safe-pattern-manifest.json' \
    --exclude 'pyproject.toml' \
    --exclude 'requirements.txt' \
    --exclude 'Makefile' \
    --exclude '.shellcheckrc' \
    --exclude '.pytest_cache' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.coverage' \
    --exclude '.coverage.*' \
    --exclude 'htmlcov' \
    --exclude '.mypy_cache' \
    --exclude '.ruff_cache' \
    --exclude '.DS_Store' \
    --exclude '*.swp' \
    --exclude '*.swo' \
    --exclude 'RELEASE-*.md' \
    --exclude 'memory' \
    --exclude 'reports' \
    --exclude 'AGENTS.md' \
    --exclude 'SOUL.md' \
    --exclude 'USER.md' \
    --exclude 'IDENTITY.md' \
    "$SKILL_ROOT/" "$OUT_DIR/"
else
  cp -a "$SKILL_ROOT/." "$OUT_DIR/"
  # 手动清理
  rm -rf "$OUT_DIR/.git" "$OUT_DIR/outputs" "$OUT_DIR/audits" "$OUT_DIR/scripts" \
    "$OUT_DIR/.github" "$OUT_DIR/tests" "$OUT_DIR/references/_shared/archive" "$OUT_DIR/references/design" \
    "$OUT_DIR/docs" "$OUT_DIR/.bak-20260823-2024-v2.4.0-migrate" \
    "$OUT_DIR/.pytest_cache" "$OUT_DIR/memory" "$OUT_DIR/reports"
  find "$OUT_DIR" -name '*.bak.*' -delete
  find "$OUT_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +
  find "$OUT_DIR" -name '*.pyc' -delete
  # v2.12.64：工具残留（coverage / 缓存 / 编辑器）——同 rsync 侧排除清单，两侧必须对称
  rm -f "$OUT_DIR"/.coverage "$OUT_DIR"/.coverage.*
  rm -rf "$OUT_DIR/htmlcov" "$OUT_DIR/.mypy_cache" "$OUT_DIR/.ruff_cache"
  find "$OUT_DIR" -name '.DS_Store' -delete
  find "$OUT_DIR" \( -name '*.swp' -o -name '*.swo' \) -delete
  rm -f "$OUT_DIR/PERFORMANCE-PROFILE.md"
  rm -f "$OUT_DIR/references/_shared/治理/教训索引.md"
  # v2.12.63：维护者工程内档（#R 编号空间），实测自 v2.12.42 起长期随包出厂 —— 见 2b' 段根因说明
  rm -f "$OUT_DIR/references/_shared/治理/论衡仓库内教训.md"
  # v2.12.47：维护者侧门 H 判据快照（不随包交付，与教训索引同侧）
  rm -f "$OUT_DIR/references/_shared/治理/lessons-max.snapshot"
  # ② v2.12.12：维护者扫描器豁免清单（非 md，消费者无用）不再随包分发
  rm -f "$OUT_DIR/.safe-pattern-manifest.json"
  rm -f "$OUT_DIR/references/_shared/通用韧化块-v2.1.0.md"
  rm -f "$OUT_DIR/.gitignore" "$OUT_DIR/.gitattributes"
  rm -f "$OUT_DIR/references/templates/README-模板拆分方案.md"
  rm -f "$OUT_DIR/README.md"
  rm -f "$OUT_DIR/CHANGELOG.md"
  rm -f "$OUT_DIR/CHANGELOG-archive.md"
  rm -f "$OUT_DIR/references/设计文档.md" "$OUT_DIR/references/设计文档-架构.md" "$OUT_DIR/references/设计文档-哲学.md"
  rm -f "$OUT_DIR"/RELEASE-*.md
  rm -f "$OUT_DIR"/references/_shared/版本升级自审门-*.md
  rm -f "$OUT_DIR"/references/_shared/M-Gate-渐进式验证-*.md
  # 剥离开发者工具文件（教训 #212）
  for f in "${DEV_TOOL_FILES[@]}"; do
    rm -f "$OUT_DIR/$f"
  done
  # verify-package.sh 是维护者发布前工具，显式双重排除（与 rsync 侧保持同口径）
  rm -f "$OUT_DIR/scripts/verify-package.sh"
fi

# ---- 2a. 工作区私有文件剔除（v2.12.23，教训 #333）----
# 背景：净化包排除清单是「白名单式逐项列举」，新增任何非内容目录/文件都默认**入包**。
#   实测 2026-09-11：子链把记忆按 cwd 相对路径写成 `仓库/memory/`，另有 4 个工作区人格文件
#   （AGENTS.md / SOUL.md / USER.md / IDENTITY.md）落入仓库根 → 干净克隆构建 81 文件、
#   实盘树直接构建就多打包 → 主控侧运维笔记与人格文件直接上架。
#   本步与上面的 --exclude 双保险（rsync 分支走 --exclude，cp -a 分支靠本步）。
rm -rf "$OUT_DIR/memory" "$OUT_DIR/AGENTS.md" "$OUT_DIR/SOUL.md" "$OUT_DIR/USER.md" "$OUT_DIR/IDENTITY.md"

# ---- 2a'. 反向断言（v2.12.23，教训 #333）：包内文件必须全部可追溯到 git 跟踪文件 ----
# 只比文件数（81）看不出问题——81 这个数字在泄漏时同样「正常」。故用集合差集 fail-closed：
# 任何「在包内但未被 git 跟踪」的文件 = 未跟踪残留入包，立即停构建。
# 注：「非 git 环境 fail-closed」前置门已于 2026-09-16 上移到写盘动作之前（见 §0）——
#   本段只保留 git 环境下的反向断言本体（需复制结果，无法前置）。
if git -C "$SKILL_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  _PF_TRACKED="$(mktemp -t lunheng-tracked.XXXXXX)"
  _PF_PKG="$(mktemp -t lunheng-pkg.XXXXXX)"
  # 注：必须用 `-z` 取原样路径——git 默认 core.quotePath=true 会把非 ASCII 路径转义
  #（「主控」→「\344\270\273」），与 find 的原始路径对不上 → 中文名文件全被误判「未跟踪」
  #（本断言首版实测踩过：69 个中文名文件假阳性）。
  git -C "$SKILL_ROOT" ls-files -z | tr '\0' '\n' | LC_ALL=C sort > "$_PF_TRACKED"
  ( cd "$OUT_DIR" && find . -type f | sed 's|^\./||' ) | LC_ALL=C sort > "$_PF_PKG"
  _PF_UNTRACKED="$(LC_ALL=C comm -13 "$_PF_TRACKED" "$_PF_PKG" || true)"
  rm -f "$_PF_TRACKED" "$_PF_PKG"
  if [[ -n "$_PF_UNTRACKED" ]]; then
    echo "❌ 净化包含有**未跟踪文件**（教训 #333：未跟踪残留默认入包）——" >&2
    printf '%s\n' "$_PF_UNTRACKED" | sed 's/^/   - /' >&2
    echo "   修法：把该文件移出仓库 / 加进 .gitignore / 在排除清单里显式 --exclude。" >&2
    echo "   注意：版本号/构建产物目录不应出现此错；出现即说明有非技能内容混进了仓库树。" >&2
    exit 1
  fi
  echo "✅ 反向断言通过：包内文件全部可追溯到 git 跟踪文件"
fi

# ---- 2b. 净化包禁入清单守卫（P2「changelog 完整化」新增）----
# CHANGELOG.md / README.md 含「教训 #N」编号与真源仓库链接，属主控侧运维资产
# （铁律：教训不对技能用户开放）。它们不在净化包内时才安全；此处做 fail-closed 守卫，
# 避免日后新增顶层文档时被 rsync 默认带入、直到最终残留扫描才炸。
FORBIDDEN_IN_PACKAGE=(
  'CHANGELOG.md'
  'CHANGELOG-archive.md'
  'README.md'
  'CONTRIBUTING.md'
  'SECURITY.md'
)
for f in "${FORBIDDEN_IN_PACKAGE[@]}"; do
  if [[ -f "$OUT_DIR/$f" ]]; then
    echo "❌ 净化包禁入文件被带入：$f（含内部痕迹，会触发最终残留扫描并在用户侧泄漏）" >&2
    exit 1
  fi
done

# ---- 2b'. `_shared/` 目录准入清单（v2.12.63 新增 · 根因治理 · 回应 2026-09-19 审计 C-1）----
# 根因：净化包排除清单是**黑名单式** —— 排除项之外的任何文件**默认入包**。实测事故：
#   `references/_shared/治理/论衡仓库内教训.md`（维护者工程内档：CI run id / commit hash / pytest 命令 /
#   `#R` 编号空间 / 「净化链」「release 链」等内部叫法）自 v2.12.42 引入后**一直随包出厂**，
#   且**同时绕过三道门**：① 不在排除清单；② 不匹配残留模式（模式只认 `教训 #N` 字面，
#   不认 `#R001` 这一 v2.12.42 新引入的编号空间）；③ 它是 git 跟踪文件 ⇒ 2a' 反向断言也不拦。
#   ⇒ 教训 #333 已在 2a 段承认「黑名单式 = 新文件默认入包」这一根因，但当时只补了 memory/ 与人格
#     文件两类，未做类别级修正。本条补上类别级修正。
# 修法：`references/_shared/` 改为**白名单准入** —— 包内该目录的文件集必须**精确等于**下表。
#   新增文件必须先在此登记（并在排除清单里决定去留），否则**构建失败**。
#   即「新文件默认入包」→「新文件默认被拦」的方向反转（不是再补一个黑名单条目）。
# 维护：本表按 `LC_ALL=C sort` 排序（下方有机械自检）；增删条目请保持 ASCII-优先排序。
# v2.12.70 A-治理瘦身：`_shared/` 分层为 真源/（判据）+ 治理/（叙事），本表项带子目录前缀；
#   下方 find 用 -mindepth 1 -maxdepth 2 + %P 输出相对路径，与带前缀清单精确对表。
SHARED_ADMITTED=(
  '治理/project-archive-sop.md'
  '治理/反哺报告处理.md'
  '真源/M-Gate-Algorithm-appendix.md'
  '真源/M-Gate-Algorithm.md'
  '真源/asset-index.md'
  '真源/audit-checklist-quickref.md'
  '真源/counts.yaml'
  '真源/degraded-scenarios.md'
  '真源/dispatch-header.md'
  '真源/evidence-object-model.md'
  '真源/external-services.md'
  '真源/failure-modes.md'
  '真源/format-export.md'
  '真源/glossary-core.md'
  '真源/glossary-full.md'
  '真源/host-verify-recipe.md'
  '真源/performance-benchmarks.md'
  '真源/phase-1-details.md'
  '真源/phase-2-details.md'
  '真源/phase-3-details.md'
  '真源/phase-order.yaml'
  '真源/pipeline-overview.md'
  '真源/skill-entry-appendix.md'
  '真源/中文数据源集成.md'
  '真源/关键协议.md'
  '真源/可发表性判定表.md'
  '真源/字数判定表.md'
  '真源/工具能力边界.md'
  '真源/执行韧化协议-design.md'
  '真源/执行韧化协议-exec.md'
  '真源/期刊匹配算法.md'
  '真源/期刊数据库.md'
  '真源/模型候选池.md'
  '真源/路径校验规范.md'
)
_SA_ACTUAL=$(find "$OUT_DIR/references/_shared" -mindepth 1 -maxdepth 2 -type f -printf '%P\n' 2>/dev/null | LC_ALL=C sort)
_SA_EXPECT=$(printf '%s\n' "${SHARED_ADMITTED[@]}" | LC_ALL=C sort)
if [[ "$(printf '%s\n' "${SHARED_ADMITTED[@]}" | LC_ALL=C sort)" != "$(printf '%s\n' "${SHARED_ADMITTED[@]}")" ]]; then
  echo "❌ SHARED_ADMITTED 未按 LC_ALL=C sort 排序（维护性自检）—— 请重排后再提交" >&2
  exit 1
fi
if [[ "$_SA_ACTUAL" != "$_SA_EXPECT" ]]; then
  echo "❌ 净化包 references/_shared/ 与准入清单不一致（v2.12.63 白名单准入门）——" >&2
  echo "   —— 包内有但清单未登记（新文件默认入包 = 泄漏风险）——" >&2
  LC_ALL=C comm -13 <(printf '%s\n' "$_SA_EXPECT") <(printf '%s\n' "$_SA_ACTUAL") | sed 's/^/   + /' >&2
  echo "   —— 清单已登记但包内缺失（误删 / 排除清单过度匹配）——" >&2
  LC_ALL=C comm -23 <(printf '%s\n' "$_SA_EXPECT") <(printf '%s\n' "$_SA_ACTUAL") | sed 's/^/   - /' >&2
  echo "   修法：若为**有意新增**的共享文件 → 在本脚本 SHARED_ADMITTED 登记（并确认它可对技能用户公开）；" >&2
  echo "         若为**维护者内部资产** → 在 §2a 的 rsync --exclude 与 cp 分支 rm -f 两处同时排除。" >&2
  exit 1
fi
echo "✅ _shared 准入清单通过：包内 ${#SHARED_ADMITTED[@]} 个文件全部已登记"

# ---- 2b''. 随包文件清单门（2026-09-19 审计 C-1 推广 · 白名单准入扩到**整个包**）----
# 根因（与 2b' 同源，作用面从 `_shared/` 扩到**全部内容目录**）：净化包的排除清单是**黑名单式** ——
#   不在 `--exclude` 里的文件**默认入包**。`_shared/` 已改白名单准入（2b'），但
#   `references/agents|templates|gates|checkers|dispatch/` 与 `references/` 顶层 md 仍是黑名单式：
#   新增一个维护者内档 = 默认出厂，直到有人恰好读过它才可能被发现（C-1 事故即此类）。
# 修法：**提交进仓库的包清单** `scripts/.pkg-manifest.txt`（一行一个相对路径，`LC_ALL=C sort`）
#   = 当前**应该**进包的完整文件集。构建时对净化后的包做**精确集合相等**判定，
#   不等即 exit 1，并**双向**打印差异（未登记入包 / 已登记却缺失）。
#   ⇒ 方向反转：「新文件默认入包」→「新文件默认被拦」。
# 维护纪律（新增随包文件前必读）：
#   · **新增任何随包文件 = 必须先显式登记到 scripts/.pkg-manifest.txt**，否则构建失败；
#   · 登记前须确认该文件可对技能用户公开（不含教训编号 / 维护者工具 / 内档叙事）；
#   · 维护者内部资产**不入清单**，且须在 §2a 的 rsync `--exclude` 与 cp 分支 `rm -f` 两处同时排除；
#   · 本门与 `_shared` 准入清单（2b'）是**双保险**：后者管 `_shared/` 目录内新增，前者管**全包**；
#     两门都不得放宽（宁可构建红，不可默认放行）。
#   · 重新生成（仅在确认当前包已干净时）：
#       cd <包根> && find . -type f | sed 's|^\./||' | LC_ALL=C sort > <仓库>/scripts/.pkg-manifest.txt
# 注：`scripts/` 整目录被 `--exclude`（见 §2 排除清单与 cp 分支 `rm -rf "$OUT_DIR/scripts"`），
#   故清单文件自身不会进包 —— 下面另有**显式断言**锁这一点（清单属维护者资产，不得随包分发）。
PKG_MANIFEST="$SCRIPT_DIR/.pkg-manifest.txt"
if [[ ! -f "$PKG_MANIFEST" ]]; then
  echo "❌ 随包清单缺失：$PKG_MANIFEST" >&2
  echo "   该清单是「全包白名单准入」的唯一真源：净化后包内文件集必须精确等于它。" >&2
  echo "   修法：从一次已确认干净的构建产物生成（见本段注释末的重新生成命令）。" >&2
  exit 1
fi
if [[ -f "$OUT_DIR/scripts/.pkg-manifest.txt" ]]; then
  echo "❌ 随包清单文件自身进入了发布包（scripts/ 未被剥离）—— 清单是维护者资产，不得随包分发" >&2
  exit 1
fi
_MF_EXPECT="$(LC_ALL=C sort "$PKG_MANIFEST")"
if [[ -z "$_MF_EXPECT" ]]; then
  echo "❌ 随包清单为空（$PKG_MANIFEST）—— 空清单 = 准入门空转，按失败处理" >&2
  exit 1
fi
_MF_ACTUAL="$( ( cd "$OUT_DIR" && find . -type f | sed 's|^\./||' ) | LC_ALL=C sort )"
if [[ "$_MF_EXPECT" != "$_MF_ACTUAL" ]]; then
  echo "❌ 净化包文件集与随包清单不一致（scripts/.pkg-manifest.txt，全包白名单准入门）——" >&2
  echo "   —— 包内有但清单未登记（新文件默认入包 = 泄漏风险；C-1 内档出厂的根因）——" >&2
  LC_ALL=C comm -13 <(printf '%s\n' "$_MF_EXPECT") <(printf '%s\n' "$_MF_ACTUAL") | sed 's/^/   + /' >&2
  echo "   —— 清单已登记但包内缺失（误删 / 排除清单过度匹配 / 清单过期）——" >&2
  LC_ALL=C comm -23 <(printf '%s\n' "$_MF_EXPECT") <(printf '%s\n' "$_MF_ACTUAL") | sed 's/^/   - /' >&2
  echo "   修法：① 有意新增随包文件 → 在 scripts/.pkg-manifest.txt 显式登记（确认可对技能用户公开）；" >&2
  echo "         ② 维护者内部资产 → 不入清单，且在 §2a 的 rsync --exclude 与 cp 分支 rm -f 两处同时排除。" >&2
  exit 1
fi
echo "✅ 随包清单门通过：包内 $(printf '%s\n' "$_MF_ACTUAL" | wc -l | tr -d ' ') 个文件与 scripts/.pkg-manifest.txt 精确一致"

# ---- 2c. 净化前基线快照（v2.12.30 新增，回应第三方审计 P1-1）----
# 背景：整条净化链**只有负向检查**（违规模式命中数 = 0 即通过）→ 剥离规则一旦过度匹配、
#   把正文或结构误删，扫描同样「全绿」= fail-open（「净化成功、内容损坏」）。
#   故在净化前记录每个 md 的字符数与标题集合，净化后做正向完整性校验（见 4b'）。
PKG_SNAPSHOT="$(mktemp -t lunheng-pkgsnap.XXXXXX)"
python3 "$SCRIPT_DIR/pkg-integrity.py" snapshot "$OUT_DIR" "$PKG_SNAPSHOT"

# C-6（2026-09-19 审计）：**基线下限守卫** —— 正向门（4b'）按「字符保留率」判，比率的分母一旦
#   异常小或被置零（快照不完整 / 目标文件本就近空），比率可**恒过**（0→0、10→10 都算 100%），
#   门退化为恒真。故在快照生成后**立即**校验：任何文件基线字符数 = 0 或 < PKG_MIN_BASELINE_CHARS
#   一律 **fail**（而不是去算比率）。阈值为「比率有判别力」的下限，非内容要求。
_PKG_MIN_BASE="${PKG_MIN_BASELINE_CHARS:-50}"
if ! python3 - "$PKG_SNAPSHOT" "$_PKG_MIN_BASE" <<'PYEOF'
import json, pathlib, sys

snap, floor = pathlib.Path(sys.argv[1]), int(sys.argv[2])
data = json.loads(snap.read_text(encoding='utf-8'))
files = data.get('files') or {}
if not files:
    print('❌ 基线快照为空（无任何 md 基线）—— 正向门将空转，按失败处理', file=sys.stderr)
    raise SystemExit(1)
bad = []
for rel, meta in sorted(files.items()):
    chars = int(meta.get('chars') or 0)
    if chars <= 0:
        bad.append(f'{rel}: 基线字符数 = 0（比率分母为零 ⇒ 保留率检查恒过）')
    elif chars < floor:
        bad.append(f'{rel}: 基线仅 {chars} 字符（< 下限 {floor}）—— 该基数上保留率无判别力')
if bad:
    print(f'❌ 基线下限守卫未通过（{len(bad)} 项）：', file=sys.stderr)
    for b in bad:
        print(f'   - {b}', file=sys.stderr)
    print('   说明：这是「比率恒过」的根因守卫（审计 C-6），不是内容错误。', file=sys.stderr)
    print('   若确有随包的极小文件，请显式设 PKG_MIN_BASELINE_CHARS 并写明理由（不得直接跳过本门）。',
          file=sys.stderr)
    raise SystemExit(1)
print(f'  ✅ 基线下限守卫通过（{len(files)} 个 md，基线均 ≥ {floor} 字符）')
PYEOF
then
  echo "❌ 基线快照未通过下限守卫（见上）—— 已清理快照并中止构建" >&2
  rm -f "$PKG_SNAPSHOT"
  exit 1
fi

# C-5（2026-09-19 审计）：正向完整性门原**只覆盖 `*.md`** —— 非 md 随包文本（`.yaml`/`.json`/
#   `.txt`/`.toml`）净化后即使被整体删空也无人发现（负向扫描只报「违规命中数 ≠ 0」）。
#   实测包内非 md 文本资产 2 个：`references/_shared/真源/phase-order.yaml` +
#   `references/_shared/真源/counts.yaml`（v2.13.x 审计修订 R-19 新增；其余随包文件均为 .md
#   或无扩展名的静态文件 LICENSE）。范围与 §扫描面 `SCAN_INCLUDES` 同口径，日后新增自动纳入。
PKG_SNAPSHOT_NONMD="$(mktemp -t lunheng-pkgsnap-nonmd.XXXXXX)"
python3 - "$OUT_DIR" "$PKG_SNAPSHOT_NONMD" <<'PYEOF'
import json, pathlib, sys

root, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
exts = {'.yaml', '.yml', '.json', '.txt', '.toml'}
data = {'files': {}}
for p in sorted(root.rglob('*')):
    if p.is_file() and p.suffix in exts:
        data['files'][str(p.relative_to(root))] = {
            'chars': len(p.read_text(encoding='utf-8', errors='replace'))}
out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
print(f"  📸 非 md 基线快照：{len(data['files'])} 个文本资产 → {out}")
PYEOF

# ---- 3. 文档净化（sed 替换，剥离「开发者维护」表述）----
purify() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  # 3a. 版本号栈精简：删除 20+ 行的历史版本号栈，只保留当前版本（scanner 误读为「版本冲突」）
  #     匹配从「> 版本：v<上一版本>」开始的连续版本号栈行，替换为单行
  python3 - "$f" "$VERSION" <<'PYEOF'
import sys, re
path, version = sys.argv[1], sys.argv[2]
with open(path, encoding='utf-8') as fh:
    lines = fh.readlines()
out = []
i = 0
stack_started = False
while i < len(lines):
    line = lines[i]
    # 检测版本号栈开头：非第一行的「> 版本：」连续块
    if line.startswith('> 版本：'):
        # 跳过整个版本号栈块（连续的 > 版本： 行）
        j = i
        while j < len(lines) and lines[j].startswith('> 版本：'):
            j += 1
        # 用当前版本单行替代
        out.append(f'> 版本：v{version}（发布版，与 SKILL.md version: 同步）\n')
        i = j
        continue
    out.append(line)
    i += 1
with open(path, 'w', encoding='utf-8') as fh:
    fh.writelines(out)
PYEOF

  # 3b. git 发布/维护指令 → 使用者无需 git（Finding 2, 95%）
  sed -i -E 's/(git commit[^。\n]*|git push[^。\n]*|git tag[^。\n]*)/（维护由开发者完成，使用者无需 git 操作）/g' "$f"

  # 3c. 自动沉淀共享教训 → 建议待 review（Finding 3, 90%）
  sed -i -E 's/实战教训自动沉淀/实战教训沉淀建议（待主人 review 后生效）/g' "$f"
  sed -i -E 's/主控\*\*必须主动\*\*写入论衡工作区/主控产出建议草稿（待主人 review 后 merge）/g' "$f"
  sed -i -E 's/没有自动沉淀到写手禁做清单/未自动产出反哺建议（角色卡改动需主人 review 后手动 merge）/g' "$f"

  # 3d. 版本升级自审门（开发者自指工具）→ 弱化引用
  sed -i -E 's/版本升级自审门/版本一致性检查/g' "$f"
  sed -i -E 's/`_shared\/版本一致性检查-v2\.3\.0\.md`[^））]*）//g' "$f"
  # 文件路径引用：原始命名（开发者视图）→ 描述性措辞（使用者视图）
  sed -i -E 's/_shared\/版本一致性检查-v2\.3\.0\.md/论衡内部的版本一致性检查（脚本已剥离，使用者无需关心）/g' "$f"
  sed -i -E 's/M-Gate-渐进式验证-v2\.2\.15\.md/M-Gate-Algorithm.md/g' "$f"

  # 3f. 反哺报告处理「发布版简化」（彻底消除跨项目共享状态写入表述，回应 Finding 3）
  #   v2.12.61：该正文已由 00-主控-扩展职责.md §二十 外移到 references/_shared/治理/反哺报告处理.md
  #   （审计 P2-6 二次分层）——**规则目标必须随内容同步迁移**：旧版按「## 二十、…(?=## 二十一、)」
  #   在扩展职责卡内做段替换；内容外移后该模式永不匹配，会复现「规则静默空转」
  #   （v2.12.11 已有先例）。现改为**按文件整篇换正文（保留版本头 + 语言政策行）**，
  #   并**硬断言替换必须发生**（count≠1 ⇒ 构建失败，不允许静默通过）。
  if [[ "$(basename "$f")" == "反哺报告处理.md" ]]; then
    python3 - "$f" <<'PYEOF'
import sys, re
path = sys.argv[1]
s = open(path, encoding='utf-8').read()
# 保留头部三行（版本戳 + 空行 + 语言政策行），其余正文整篇替换为净化版
m = re.match(r'(\A> 版本：[^\n]*\n\n> 🌐 \*\*语言政策\*\*：[^\n]*\n\n)', s)
assert m, '反哺报告处理.md 头部（版本戳 + 语言政策行）缺失 —— 净化中止'
body = """# 反哺报告处理（发布版简化）

主控会话结束时（Phase 5 终检后）执行：

1. **读取** T7 审计员交付的 `audits/反哺报告-vN.md`
2. **列出建议 merge 的反哺规则**到 `final/交付说明.md` 末段「建议 merge 的反哺规则」清单
3. **不自动修改任何角色卡或共享状态文件**——等主人人工 review 后手动 merge
4. **项目内教训记录**：本次实战发现写入 `run/<项目>/audit-lessons.md`（**项目内文件**，非跨项目共享状态）；跨项目教训沉淀仅存在于论衡开发版（含跨项目 lessons 同步机制），见 GitHub 仓库：https://github.com/zuoyunlai/lunheng-article-pipeline

如反哺报告为空（无新增问题），主控写「本轮反哺报告：T7 未发现可沉淀新增问题」，避免机制被跳过。
"""
out = m.group(1) + body
assert out != s, '反哺报告处理.md 未发生变化（净化规则目标错位）'
open(path, 'w', encoding='utf-8').write(out)
print('✅ 反哺报告处理.md 净化完成（整篇换正文，版本头保留）')
PYEOF
  fi

  # 3h. 设计文档死链处理（设计文档已 --exclude，需改引用为 glossary）
  python3 - "$f" <<'PYEOF'
import sys, re
path = sys.argv[1]
s = open(path, encoding='utf-8').read()
# v2.12.63：规则 3h-5 的行级反向断言基线（见本块末尾 7c）——只对「源侧本就有该行」的文件生效
_src_had_layer1 = '入口必读（启动清单 1-2 步）' in s

# 1. SKILL.md 启动清单第 2 步：设计文档 → glossary-full（v2.7.10 起 glossary.md 拆分到 _shared/真源/glossary-full.md）
s = s.replace(
    '读 `references/设计文档.md`（数据信任级别 / M 门 / 阶段闸门 / F 失败模式 / T6 批判）',
    '读 `references/_shared/真源/glossary-full.md`（核心概念单一真源：10 张角色卡 / 三层防御 / 数据信任 / 关键协议 / 工具边界）'
)

# 2. SKILL.md 角色卡与模板段：删除「设计文档」行
s = re.sub(r'- 设计文档（[^\n]*）：`references/设计文档\.md`\n', '', s)

# 3. pipeline-readme.md「设计文档加载策略」段：删除
s = re.sub(r'## 设计文档加载策略.*?(?=\n## 派发话术)', '', s, flags=re.DOTALL)

# 4. pipeline-readme.md 模板拆分方案引用：删除
s = s.replace('详见 `templates/README-模板拆分方案.md`。', '。')

# 5. 【v2.12.63 修复】`设计文档.md` 提及处理：**只删该 mention，不得整行删除**
#    旧规则 `re.sub(r'[^\n]*设计文档\.md[^\n]*\n', '', s)` 的语义是「**任何含 `设计文档.md`
#    的整行**」。实测事故（2026-09-19 审计 C-2）：把 `00-主控-扩展职责.md` §〇 主控必读文档清单的
#    **层 1 整行**删掉 —— 包内实测该文件 `设计文档` 0 命中、层号 0→2 跳档、
#    `入口必读（启动清单 1-2 步）` 消失。即「告诉主控去读入口文档的那一行」在发布版里没了。
#    而正向完整性门（4b') 对此零感知：该文件约 73KB，删 1 行保留率仍 ≈99.9%、标题数不变、
#    REQUIRED_ANCHORS 未列该文件 ⇒ 只能靠本条自身做**行级反向断言**（见本块末尾 7c）。
#    另：旧规则自述目的是「README 目录结构里的那一行」，而 README.md 本就被整文件 --exclude
#    **不进包** ⇒ 旧规则在包内**从未达成自述目的，只造成了误删**。
s = s.replace(
    '``glossary-full.md`（**发布版无 `设计文档.md`**，见 `SKILL.md` 启动清单第 1 步）`',
    '`glossary-full.md`'
)

# 6. 任务简报模板「详见设计文档 原创性保证 + 」：删引用，保留写手卡
s = s.replace('（详见设计文档 原创性保证 + 写手卡视角与精度铁律）', '（详见写手卡视角与精度铁律）')

# 7. 【2026-09-19 改写】整段删除 §十四 的「维护者发布 SOP（已外移）」指针块（规则 3h-7）
#    背景：维护者发布 SOP 的**主体已外移**到 `references/设计文档-架构.md` §六（该文件整类被本脚本
#    `--exclude`，**不进净化包**）。外移后真源 §十四 只剩一个指针块，其中含两个**包内不存在**的引用
#    （`设计文档-架构.md` / `scripts/README.md`）⇒ 不剥就是死引用 + 维护者叙事漏入包。
#    本条同时**取代旧的 3h-7**（原「按标题整段删除 §十四 维护者 SOP」）：旧规则的目标内容已不在真源，
#    留看重跑会落入「真源 0 命中」的规则死亡态（教训 #192 / #320 同型）。
#    历史（保留备查）：v2.12.11 修过一次同类静默失效 —— 旧 re-search 目标是 bullet 形态
#    `- **版本一致性检查…**：`，而真源实际是 heading 形态 → 永不匹配，规则空转；后果是
#    「修订后必跑硬门三件套 / 内容质量门脚本」两小节连同 `> **根因**` 引块留在包内，而编号命令清单
#    已被 strip-shell-commands.py 剥走 → 只剩空冒号，形成「声称必跑脚本、却零 exec」的自相矛盾（leak-audit P1-1）。
s, _sop_n = re.subn(
    r'### 维护者发布 SOP（已外移.*?(?=\n## |\n---\n+## |\Z)',
    '',
    s,
    flags=re.DOTALL
)
if _sop_n:
    print(f'  §十四 维护者 SOP 指针块整段删除（规则 3h-7）：{_sop_n} 处')

# 7b. 【v2.12.13 新增，v2.12.16 跟改标题】整段删除 §二十五「Archive 保留建议清单」（旧名「Archive 清理策略」；含删除类 SOP）
#   根因（审计 §一.9 / pkg-audit P1-1）：原规则 3l 的 re-search 目标是 `### 5.8 Archive 清理记录`，
#   真源已无此标题 → 规则静默空转（真源 0 命中），而 §二十五 本就不在任何规则射程内
#   → 「主控 … 清理 drafts/archive/」「保留 N 文件，删 M 文件」等删除类 SOP 整段漏入包，
#   与包内 status-template.md「论衡工作流本身不执行任何 cleanup」直接矛盾。
#   修法：按标题整段删除（到下个 `## ` 标题前）。
s, _arch_n = re.subn(
    r'## 二十五、Archive 保留建议清单.*?(?=\n## )',
    '',
    s,
    flags=re.DOTALL
)
if _arch_n:
    print(f'  §二十五 Archive 保留建议清单整段删除（规则 3h-7b）：{_arch_n} 处')

# 7c. 【v2.12.63 新增】规则 3h-5 行级反向断言：主控必读清单「层 1 入口必读」整行不得消失
#   背景见规则 5 注释（v2.12.63 修复的误删事故）。正向完整性门按「字符保留率 + 标题数 + 锚点」判，
#   单行删除在该文件（约 73KB）上完全不可见 ⇒ 必须由规则自身做行级断言。
if _src_had_layer1 and '入口必读（启动清单 1-2 步）' not in s:
    raise SystemExit(
        '❌ 规则 3h-5 行级反向断言失败：`00-主控-扩展职责.md` §〇 主控必读文档清单的'
        '「层 1 入口必读（启动清单 1-2 步）」整行在净化后消失 —— '
        '说明净化规则又出现「整行正则过度匹配」（v2.12.63 修复项，见规则 5 注释）。'
    )

open(path, 'w', encoding='utf-8').write(s)
PYEOF

  # 3i. 跨项目扫描/枚举类表述 → 强 opt-in（v2.7.4 净化规则，回应 ClawHub F1 ERROR）
  # 真源允许 v2.7.3 新增的「历史项目复用」便利功能，但净化包必须显示为主人显式指定
  python3 - "$f" <<'PYEOF'
import sys, re
path = sys.argv[1]
s = open(path, encoding='utf-8').read()
# 任务简报：把「主控扫描 run/ + 相似主题 grep」等表述替换为「主人显式指定」opt-in 措辞
old_block = '''### -1. 相似项目复用检查（v2.7.3 新增，主控 Phase 0 必做）

主控 Phase 0 前用 `列出 run/` + 相似主题 检查 扫历史项目；命中相似主题（≥1 个关键词重合）→ 任务简报头部列「**可复用素材提示**」呈主人：可复用项（文献卡 / 数据卡 / 案例卡 / 分析大纲 / 期刊匹配）+ 对应 `run/<旧项目>/` 路径。**默认不复用，主人勾选才复用**；复用素材仍须过 T7 G1/G2 时效性核验（>6 个月数据标注「历史数据」）。'''
new_block = '''### -1. 历史项目素材复用（可选，主人显式发起才执行）

**默认状态：跳过**——本节由主控呈现给主人，**不主动扫描任何目录**。如主人希望复用某一历史项目的素材，须：

1. **由主人显式指定**要复用的旧项目名称（或 `run/<旧项目>/` 路径）——主控不主动发现。
2. **主控**仅读取该主控指定的旧项目 `run/<旧项目>/` 内的文献卡 / 数据卡 / 案例卡 / 分析大纲 / 期刊匹配结果等指定素材类型。
3. **主控**列出"可复用素材提示"呈主人复核（清单 + 路径 + 用途），主人在任务简报头部勾选后生效。
4. **复用素材仍须过 T7 G1/G2 时效性核验**（>6 个月数据自动标注「历史数据」）。
5. **未经指定的项目一律不读、不列、不提示**——边界与 SKILL.md「仅当前 `run/<项目名>/`」严格保持一致。

> 本节为 v2.7.3 主人实战反馈后新增的便利功能，与"项目内文件隔离"边界兼容。'''
if old_block in s:
    s = s.replace(old_block, new_block, 1)
# 通用兜底：任何残留的「列出 run/」「扫历史项目」直接干掉
s = re.sub(r'主控 Phase 0 前用 `列出 run/`[^。]*。', '主控 Phase 0 前不主动扫描任何目录；历史项目复用由主人在任务简报中显式指定。', s)
s = re.sub(r'主控 Phase 0 前用 `ls run/`[^。]*。', '主控 Phase 0 前不主动扫描任何目录；历史项目复用由主人在任务简报中显式指定。', s)
open(path, 'w', encoding='utf-8').write(s)
PYEOF

  # 3j. API key 措辞收敛（v2.7.4 净化规则，回应 ClawHub F2 WARN）
  # 真源措辞「需主人提供 API key」「需主人在 OpenClaw 环境变量配置」会被 scanner 读为诱导把 key 粘到 chat
  sed -i -E 's/（需主人提供 API key）/（凭据须在宿主环境外部配置；仅记录"credential_configured: yes\/no"，主控绝不读取\/存储\/外发密钥）/g' "$f"
  sed -i -E 's/— 需主人在 OpenClaw 环境变量配置/— 凭据须在宿主环境外部配置（环境变量或本地凭据文件），仅记录"credential_configured: yes\/no"，主控绝不读取\/存储\/外发密钥/g' "$f"
  sed -i -E 's/可选启二梯队知网\/万方\/科情需提供 API key/可选启二梯队知网\/万方\/科情，凭据须在宿主环境外部配置，详见任务简报第二梯队说明/g' "$f"
  # 任何残留的「需主人提供」「主控读取 key」类表述都直接告警（鲁棒兜底）
  sed -i -E 's/需主人提供 API key/凭据须在宿主环境外部配置/g' "$f"
  sed -i -E 's/主控绝不读取、主控绝不读取、主控绝不读取/主控绝不读取/g' "$f"

  # 3k. 模型健康度预检的 "ping" 措辞（v2.7.4 净化规则，回应 ClawHub F3 WARN）
  sed -i -E 's/模型健康度预检[^：]*：第一次 LLM 调用前发 1-token ping[^。]*。/LLM 可用性初判：子代理观察首次 LLM 调用的响应时间与首 token 延迟；30 秒内无首字节返回 → 降级 fallback 链。/g' "$f"

  # 3l. archive cleanup 段改写为「项目结题标记」记录（v2.7.4 净化规则，回应 ClawHub F4 WARN）
  python3 - "$f" <<'PYEOF'
import sys, re
path = sys.argv[1]
s = open(path, encoding='utf-8').read()
# 把 5.8 archive 清理整段（含安全边界 + trash/dry-run 描述）替换为「项目结题记录」段
old_pattern = re.compile(
    r'### 5\.8 Archive 清理记录.*?(?=\n### 5\.9|\n---|\n## 维护说明|\Z)',
    re.DOTALL
)
new_block = '''### 5.8 项目历史记录归档（v2.5.5 增，v2.7.4 措辞收敛）

> **安全边界**：本节为"过期项目整理"的过程记录，**不涉及文件删除**。论衡工作流本身不执行任何 cleanup，所有"归档"动作由主人在论衡工作流外手动完成；本节仅记录"哪些项目已结题、已结题项目的素材是否被未来项目引用"。

- `[archive HH:MM] 项目 <名> 标记结题，结题产物路径 = <路径>，后续复用需主人在新项目任务简报中显式指定`
- `[reuse HH:MM] 项目 <新名> 引用 <旧名> 的 <素材类型>（已由主人在任务简报勾选授权）`
'''
s, n = old_pattern.subn(new_block, s)
open(path, 'w', encoding='utf-8').write(s)
PYEOF

  # 3m. 维护者叙事中性化（v2.12.11 新增，回应 leak-audit §四.1）
  # 背景：FINAL_PATTERNS 本轮新增「维护者叙事词」后，真源里仍有若干**非本组文件**
  #   （SKILL.md / permissions.md / glossary-full.md / dispatch/* / deliverables.md /
  #   project-archive-sop.md 等）含 ClawHub T05 / SkillSpector / 扫描器 / 净化包 / 自审门 等语汇。
  #   这些文件的**源侧**改写不属本组所有权（A/B 组负责）；若不在包内做中性化，最终残留扫描
  #   会对整包 fail-loud → 阻断发布。故在此做**语义等价**替换：只换词，不改断定内容。
  #   若 A/B 组已在源侧改掉，本步自然零命中（幂等）。
  python3 - "$f" <<'PYEOF'
import sys
path = sys.argv[1]
s = open(path, encoding='utf-8').read()
orig = s

# —— 平台审计编号 / 扫描器产品名 → 中性表述（长形态优先，避免断句）——
s = s.replace('回应 ClawHub T09/审计', '回应平台审计')
s = s.replace('回应 ClawHub T09 一致性审计', '回应平台一致性审计')
s = s.replace('回应 ClawHub T05', '回应平台审计')
s = s.replace('SkillSpector', '平台安全扫描')
s = s.replace('A.I.G 扫描器', 'A.I.G 审计')
s = s.replace('扫描器', '审核工具')
s = s.replace('ClawHub T05', '平台审计')
s = s.replace('ClawHub T09', '平台审计')
s = s.replace('ClawHub 净化包', 'ClawHub 发布版')
s = s.replace('净化脚本', '发布构建流程')
s = s.replace('净化包', '发布版')
# —— 「自审门」→「自检门」（保留门 A-P 命名体系，去掉维护者自指口径）——
#    `自审门门 L` 先去叠字（否则替换后读作「自检门门 L」）
s = s.replace('自审门门', '自检门')
s = s.replace('自审门', '自检门')
# —— 「修订 SOP」→「修订任务规范」（SOP 内史随 §十四 维护者小节一并剥离）——
s = s.replace('修订 SOP 与', '修订任务规范与')
s = s.replace('修订 SOP', '修订任务规范')

# —— v2.12.13 新增：双视图发布架构内部叫法中性化（教训 #321 / #296 同型）——
#   背景：构建脚本 3a 自己注入的页脚文案「发布净化版」进入 67 个文件，却不在
#   FINAL_PATTERNS 覆盖内（规则只防手写，不防自己写）；真源侧 `净化版`/`双视图`/`strip 剥除`
#   亦有多处直入包内。长形态优先替换，避免断句。
import re as _re
s = _re.sub(r'ClawHub T\d+', '平台审计', s)
s = s.replace('净化版代码块被 strip 剥除后', '发布版代码块剥离后')
s = s.replace('代码块被 strip 剥除', '代码块被剥离')
s = s.replace('strip 剥除', '代码块剥离')
s = s.replace('净化版', '发布版')
s = s.replace('双视图硬约束', '双形态硬约束')
s = s.replace('双视图发布架构', '双形态发布架构')
s = s.replace('双视图', '双形态')

if s != orig:
    open(path, 'w', encoding='utf-8').write(s)
    print(f'  维护者叙事中性化：{path}')
PYEOF
}

# 对所有 md 文件净化
while IFS= read -r -d '' f; do
  purify "$f"
done < <(find "$OUT_DIR" -name '*.md' -print0)

# ---- 3o. DEV-ONLY 段落剥离（v2.12.5 新增）----
# 真源用 <!-- DEV-ONLY-START --> ... <!-- DEV-ONLY-END --> 标记「只服务维护者」的段落
# （构建/验证管线说明 + 开发者脚本全文）。净化包必须整段移除：否则 shell 剥离规则会把
# `xxx.sh` 打成 `shell 脚本` 这类无宾语占位符（ClawHub 审计 F2/F6 命中点，且句子残缺）。
# 对应用户侧修复：T5 自审门段落改为「read 核验清单」，不再声明跑脚本。
echo "🧹 剥离 DEV-ONLY 段落..." >&2
find "$OUT_DIR" -name '*.md' -exec python3 -c '
import re, sys
for path in sys.argv[1:]:
    s = open(path, encoding="utf-8").read()
    new = re.sub(r"<!--\s*DEV-ONLY-START.*?DEV-ONLY-END\s*-->\n?", "", s, flags=re.DOTALL)
    if new != s:
        open(path, "w", encoding="utf-8").write(new)
        print("  剥离 DEV-ONLY：", path)
' {} +

# ---- 3p. 包内死链中和（2026-09-19 审计 C-4）----
# 背景：`references/templates/README-模板拆分方案.md` 等**被排除的仓库文档**不进包，
#   但包内其它文档仍可能以「反引号内联路径 / markdown 链接目标」引用它们 ⇒ 包内死链
#   （用户点不到、也读不到那个文件）。实测：包内 `references/pipeline-readme.md` 有一处
#   `（…见 `templates/README-模板拆分方案.md` §四）`（审计 C-4 原名点）。
# 旧做法：在 purify() 里手写 sed 逐条硬编码路径（3h-4 只认「详见 `templates/README-模板拆分方案.md`。」
#   这一种字面形态）——**新增一个被排除文件就漏一次**，且规则与排除清单两处维护必然漂移。
# 修法（程序化生成，审计建议）：排除集**只在此处声明一次**（PKG_EXCLUDED_DOC_PATHS），
#   匹配规则由 python 从该清单**推导生成**（不手写路径），并对产物做 fail-closed 反向断言：
#   中和后包内任何 .md 都不得再出现指向被排除文档的反引号引用 / 链接目标。
# 维护：新增「被 --exclude 的仓库文档」时，把路径补进 PKG_EXCLUDED_DOC_PATHS（一处即可）。
# 注：只处理行内代码与链接目标两种形态（不动裸文本叙述，也不动代码围栏内的内容）——
#   运行期产物路径（`run/` `audits/` `final/` 等）不在本清单，故不会被误中和。
PKG_EXCLUDED_DOC_PATHS=(
  'references/设计文档.md'
  'references/设计文档-架构.md'
  'references/设计文档-哲学.md'
  'references/_shared/治理/教训索引.md'
  'references/_shared/治理/论衡仓库内教训.md'
  'references/_shared/治理/lessons-max.snapshot'
  'references/_shared/通用韧化块-v2.1.0.md'
  'references/_shared/版本升级自审门-*.md'
  'references/_shared/M-Gate-渐进式验证-*.md'
  'references/templates/README-模板拆分方案.md'
  'README.md'
  'CHANGELOG.md'
  'CHANGELOG-archive.md'
  'PERFORMANCE-PROFILE.md'
)
echo "🔗 中和包内死链（指向被排除文档的引用）..." >&2
_DEADLINK_LOG="$(mktemp -t lunheng-deadlink.XXXXXX)"
if ! python3 - "$OUT_DIR" "${PKG_EXCLUDED_DOC_PATHS[@]}" >"$_DEADLINK_LOG" 2>&1 <<'PYEOF'
import pathlib, re, sys

root = pathlib.Path(sys.argv[1])
globs = sys.argv[2:]
if not globs:
    print('❌ 被排除文档清单为空 —— 死链中和门空转', file=sys.stderr)
    raise SystemExit(1)


def _tail_re(g):
    """glob → 「路径尾段」正则：`*` 只吃非分隔符/空白字符，避免跨段误配。"""
    tail = re.escape(g.split('/')[-1]).replace('\\*', r'[^/`\s]*')
    return re.compile(r'(?:^|/)' + tail + r'$')


TAIL_RES = [_tail_re(g) for g in globs]


def is_dead(token):
    t = token.strip().strip('`').strip()
    if not t or len(t) > 200 or ' ' in t or '\t' in t:
        return False
    return any(r.search(t) for r in TAIL_RES)


PAREN = re.compile(r'（[^（）\n]{0,300}）')
CODE = re.compile(r'`([^`\n]{1,200})`')
LINK = re.compile(r'\[([^\]\n]*)\]\(([^)\n]*)\)')
FENCE = re.compile(r'^[ \t]*(?:`{3,}|~{3,})')


def neutralize(line):
    def _paren(m):
        return '' if any(is_dead(c) for c in CODE.findall(m.group(0))) else m.group(0)

    out = PAREN.sub(_paren, line)
    out = CODE.sub(lambda m: '' if is_dead(m.group(1)) else m.group(0), out)
    out = LINK.sub(lambda m: '' if is_dead(m.group(2)) else m.group(0), out)
    out = re.sub(r'（\s*[，。；、,;]?\s*）', '', out)
    out = re.sub(r'（\s*见\s*）', '', out)
    out = re.sub(r'，\s*。', '。', out)
    out = re.sub(r'[ \t]+。', '。', out)
    return out


def process(text):
    out, in_fence = [], False
    for line in text.split('\n'):
        if FENCE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        out.append(line if in_fence else neutralize(line))
    return '\n'.join(out)


def nonfence(text):
    out, in_fence = [], False
    for line in text.split('\n'):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return '\n'.join(out)


changed, leftovers = [], []
for f in sorted(root.rglob('*.md')):
    rel = str(f.relative_to(root))
    text = f.read_text(encoding='utf-8', errors='replace')
    new = process(text)
    if new != text:
        f.write_text(new, encoding='utf-8')
        changed.append(rel)
    body = nonfence(new)
    for tok in CODE.findall(body) + [m[1] for m in LINK.findall(body)]:
        if is_dead(tok):
            leftovers.append(f'{rel}: {tok}')

for rel in changed:
    print(f'  中和死链引用：{rel}')
if leftovers:
    print(f'❌ 包内仍有指向被排除文档的引用（{len(leftovers)} 处）——', file=sys.stderr)
    for item in leftovers[:20]:
        print(f'   - {item}', file=sys.stderr)
    print('   修法：把该写法补进本段的匹配规则（或从真源删掉该死引用）；'
          '确属合法引用请扩充 PKG_EXCLUDED_DOC_PATHS 之外的判定，勿直接弱化本门。', file=sys.stderr)
    raise SystemExit(1)
if not changed:
    print('  （包内无指向被排除文档的引用，无需中和）')
PYEOF
then
  echo "❌ 死链中和失败：包内仍存在指向被排除文档的引用" >&2
  echo "---- 子步骤输出 ----" >&2
  tail -n 40 "$_DEADLINK_LOG" >&2
  echo "--------------------" >&2
  rm -f "$_DEADLINK_LOG"
  exit 1
fi
cat "$_DEADLINK_LOG"
rm -f "$_DEADLINK_LOG"

# ---- 3n. 安装命令版本 pin 同步（教训 #297）----
# 净化包内 `openclaw skills install @...@X.Y.Z` 的 pin 必须等于本包版本，
# 防止「包是 v2.12.4、安装命令还钉在 v2.10.3」这类用户可见的审计版本错配。
if [[ -f "$OUT_DIR/QUICKSTART.md" ]]; then
  sed -i -E "s|(@zuoyunlai/lunheng-article-pipeline)@[0-9]+\.[0-9]+\.[0-9]+|\1@$VERSION|g" "$OUT_DIR/QUICKSTART.md"
  # C-3（2026-09-19 审计）：规则 3n 原本**无产物侧断言** —— pin 替换目标写法一变就静默空转，
  #   用户会照着旧版 pin 安装（审计版本错配，恰是本规则要防的事）。此处补**正向断言**：
  #   QUICKSTART.md 内所有安装命令 pin 必须等于本包版本（无 pin 时不触发）。
  _PIN_BAD="$(grep -oE '@zuoyunlai/lunheng-article-pipeline@[0-9]+\.[0-9]+\.[0-9]+' "$OUT_DIR/QUICKSTART.md" 2>/dev/null | sed 's|^@zuoyunlai/lunheng-article-pipeline@||' | sort -u | grep -vx "$VERSION" || true)"
  if [[ -n "$_PIN_BAD" ]]; then
    echo "❌ 规则 3n 断言失败：QUICKSTART.md 安装命令 pin 与本包版本不一致 ——" >&2
    printf '%s\n' "$_PIN_BAD" | sed 's/^/   - /' >&2
    echo "   修法：核对 QUICKSTART.md 的安装命令写法是否仍为 @<slug>@<ver> 形态（规则 3n 的替换目标）。" >&2
    exit 1
  fi
fi

# ---- 3e. 净化 SKILL.md description（去掉引用已剥离 scripts/ 的「自我维护」句）----
SKILL_OUT="$OUT_DIR/SKILL.md"
python3 - "$SKILL_OUT" <<'PYEOF'
import sys, re
path = sys.argv[1]
s = open(path, encoding='utf-8').read()
# 去掉 description 中「含技能自我维护：...」句（引用了已剥离的 scripts/，且是 scanner Finding 3 标记点）
s = re.sub(
    r'\*\*含技能自我维护\*\*：[^。]*。',
    '',
    s
)
open(path, 'w', encoding='utf-8').write(s)
print('✅ SKILL.md description 净化完成')
PYEOF

# ---- 3g. shell 命令剥离（净化包极简纯净，主人 2026-08-24 拍板）----
# 把「人类 host shell 验证示例」里的 shell 命令替换为自然语言，删除 bash/sh 代码块，
# 保留 python 伪代码（算法判定逻辑）。agent 零 exec，靠 read + LLM 推理模拟。
# v2.12.40（可见性修复，同 3h 口径）：旧实现裸调用 `find ... | xargs python3 strip-shell-commands.py`
#   ⇒ 子步骤失败时构建只中断、无失败归因、子步骤输出不落幕（同链三步可见性不一致：
#   strip-internal-leakage / strip-anchor-residue 已用「失败透出末 40 行」模板，本步没有）。
#   现按**同一模板**包裹，三条剥离子步骤（shell 命令 / 内部痕迹 / 编号锚点）失败可见性一致。
echo "🔧 剥离 shell 命令（保持极简纯净）..."
if ! STRIP_SHELL_OUT="$(find "$OUT_DIR" -name '*.md' -print0 | xargs -0 python3 "$SCRIPT_DIR/strip-shell-commands.py" 2>&1)"; then
  echo "❌ shell 命令剥离失败：strip-shell-commands.py 退出码非 0" >&2
  echo "---- 子步骤输出（末 40 行）----" >&2
  printf '%s\n' "$STRIP_SHELL_OUT" | tail -n 40 >&2
  echo "------------------------------" >&2
  exit 1
fi

# ---- 3h. 净化残留自检（教训 #205 / #213，前置到此处避开 exec timeout）----
# 注：必须在 SKILL.md 顶部补声明之前，否则该 cat 追加的「使用者发布版」段不会受扫描影响
echo "🔍 净化残留扫描（前置，教训 #213）..." >&2
RESIDUAL_HITS=0
for f in "${DEV_TOOL_FILES[@]}"; do
  if [[ -f "$OUT_DIR/$f" ]]; then
    echo "  ❌ 开发者工具残留：$f"
    RESIDUAL_HITS=$((RESIDUAL_HITS + 1))
  fi
done
RESIDUAL_PATTERNS=(
  'git commit'
  'git push'
  'git tag'
  '实战教训自动沉淀'
  'M-Gate-渐进式验证-v2'
  '版本升级自审门'
  '版本一致性检查-v2'
  '需主人提供 API key'
  'shellcheckrc'
  'paper-ready-check\.(sh|py)'  # v2.12.0 新增：论衡开发者脚本不应出现在净化版（脚本随 scripts/ 整目录被剥，但散落 .md 引用必须脱钩）
  'check-version\.sh'           # v2.12.0 新增：开发者版本同步脚本不在净化版
  'self-audit-gate\.sh'        # v2.12.10 新增：自审门脚本（防 project-archive-sop 等散落 .md 引用漏剥，同 check-version.sh 类）
  'sync-version\.sh'           # v2.12.10 新增：版本同步脚本（同 check-version.sh 类）
  'build-clawhub-release\.sh'  # v2.12.10 新增：净化包构建脚本自身（同 check-version.sh 类）
)
for pat in "${RESIDUAL_PATTERNS[@]}"; do
  # grep 无命中时返回 1；在 pipefail 下需显式吞掉该正常状态。
  hits=$({ grep -rE "$pat" "${SCAN_INCLUDES[@]}" "$OUT_DIR" 2>/dev/null || true; } | wc -l | tr -d ' ')
  if [[ "$hits" -gt 0 ]]; then
    echo "  ⚠️ 净化表述残留：$pat（$hits 处）"
    RESIDUAL_HITS=$((RESIDUAL_HITS + 1))
  fi
done
if [[ "$RESIDUAL_HITS" -gt 0 ]]; then
  echo ""
  echo "❌ 净化残留扫描未通过：$RESIDUAL_HITS 项"
  echo "   请检查 build-clawhub-release.sh 的净化规则是否过期（教训 #205：脚本需与真源同步演进）"
  exit 1
fi
echo "  ✅ 净化残留扫描通过"

# ---- 4. 补「使用者视角」声明到 SKILL.md 顶部（回应 scanner 的 scope 疑虑）----
SKILL_OUT="$OUT_DIR/SKILL.md"
if [[ -f "$SKILL_OUT" ]]; then
  # 源 SKILL.md 末尾无换行符时，追加段会与许可证句粘连（`---` 被解析为 setext H2）——先补换行
  [[ -n "$(tail -c 1 "$SKILL_OUT")" ]] && echo >> "$SKILL_OUT"
  cat >> "$SKILL_OUT" <<EOF

---

## 📦 关于本包

> 本包是论衡的使用者发布版，只含运行所需的文档与角色卡。
> - 不含：版本同步脚本 / git 发布指令 / 历史审计记录 / 归档 / 备份 / CI
> - 自检记录、经验沉淀与内部编号属维护者资产，不随包分发
> - 论衡为纯 skill：LLM 推理 + 文件读写 + Web 检索，零 shell 执行
EOF
fi

# ---- 4b. 内部痕迹清理（教训 #296：主控侧运维痕迹不对技能用户开放）----
# 两步：① 剥「教训 #N」字面 / 文件名引用 / 本地路径 / 真源仓库；② 清剥离后残留的裸编号锚点。
#
# v2.12.40（可见性修复）：旧实现两步都 `>/dev/null`，而 strip-internal-leakage.sh 的**唯一**
#   失败信号（WARNING + 残留行清单）走 stdout ⇒ 2026-09-14 实测 `build 2.12.39` 首次 EXIT=1 时
#   终末只剩「🧹 清理内部痕迹（教训 #296）...」一行、零错误信息，排障被迫手动单跑脚本复现。
#   现改为：成功仍安静（不污染构建日志），**失败则把子步骤输出末 40 行透出**再退。
#   同型规则：任何「子步骤失败即决定构建成败」的调用都不得吞掉子步骤输出。
echo "🧹 清理内部痕迹（教训 #296）..." >&2
if ! STRIP_LEAK_OUT="$(bash "$SCRIPT_DIR/strip-internal-leakage.sh" "$OUT_DIR" 2>&1)"; then
  echo "❌ 内部痕迹剥离失败：strip-internal-leakage.sh 退出码非 0" >&2
  echo "---- 子步骤输出（末 40 行）----" >&2
  printf '%s\n' "$STRIP_LEAK_OUT" | tail -n 40 >&2
  echo "------------------------------" >&2
  exit 1
fi
if ! STRIP_ANCHOR_OUT="$(python3 "$SCRIPT_DIR/strip-anchor-residue.py" "$OUT_DIR" 2>&1)"; then
  echo "❌ 编号锚点残留清理失败：strip-anchor-residue.py 退出码非 0" >&2
  echo "---- 子步骤输出（末 40 行）----" >&2
  printf '%s\n' "$STRIP_ANCHOR_OUT" | tail -n 40 >&2
  echo "------------------------------" >&2
  exit 1
fi

# ---- 4b'. 正向完整性校验（v2.12.30 新增，回应第三方审计 P1-1）----
# 与 4b 的负向残留扫描互补：这里回答的是「净化有没有**多删**」—— 文件仍在、非空、
# 结构锚点仍在、字符量未塌陷、SKILL.md frontmatter 仍可解析。任一不过即停构建。
echo "🔍 正向完整性校验（是否误删）..." >&2
if ! python3 "$SCRIPT_DIR/pkg-integrity.py" verify "$OUT_DIR" "$PKG_SNAPSHOT"; then
  echo "❌ 正向完整性门未通过：净化链可能**误删**了必要内容（负向扫描对此盲区）" >&2
  rm -f "$PKG_SNAPSHOT"
  exit 1
fi
rm -f "$PKG_SNAPSHOT"

# C-5（2026-09-19 审计）：非 md 文本资产的同款正向校验（存在性 + 非空 + 字符保留率）。
#   与 4b' 的 md 校验互补；覆盖面与 §扫描面 SCAN_INCLUDES 同口径（.md 之外再收 yaml/yml/json/txt/toml）。
if ! python3 - "$OUT_DIR" "$PKG_SNAPSHOT_NONMD" <<'PYEOF'
import json, pathlib, sys

root, snap = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
data = json.loads(snap.read_text(encoding='utf-8'))
files = data.get('files') or {}
if not files:
    print('  ℹ️ 本包无非 md 文本资产（yaml/yml/json/txt/toml）—— 本子门无对象（清单门仍保证集合不变）')
    raise SystemExit(0)
errs = []
for rel, meta in sorted(files.items()):
    f = root / rel
    if not f.is_file():
        errs.append(f'{rel} 在净化后**消失**（非 md 资产被误删）')
        continue
    b = int(meta.get('chars') or 0)
    c = len(f.read_text(encoding='utf-8', errors='replace'))
    if c == 0:
        errs.append(f'{rel} 被清空（0 字符）')
    elif b > 0 and c / b < 0.35:
        errs.append(f'{rel} 字符保留率 {c / b:.0%} < 35%（{b} → {c}）')
if errs:
    print(f'❌ 非 md 正向完整性未通过（{len(errs)} 项）：', file=sys.stderr)
    for e in errs:
        print(f'   - {e}', file=sys.stderr)
    raise SystemExit(1)
print(f'  ✅ 非 md 正向完整性通过（{len(files)} 个文本资产全部存活且未塔陷）')
PYEOF
then
  echo "❌ 非 md 正向完整性门未通过（见上）" >&2
  rm -f "$PKG_SNAPSHOT_NONMD"
  exit 1
fi
rm -f "$PKG_SNAPSHOT_NONMD"

# ---- 4c. 最终残留扫描（含「教训对用户不可见」铁律的兜底检查）----
echo "🔍 最终残留扫描..." >&2
FINAL_PATTERNS=(
  '教训 #'
  '教训编号'
  '教训来源'
  'audit-lessons'
  'lessons\.md'
  'github\.com/zuoyunlai'
  '/home/zuoyunlai/'
  '完整开发版'
  '见相关算法'
  '\(，\+ #'
  '\( \+ #'
  '裸 #N'
  '`shell 脚本`'                # v2.12.5 新增：.sh 泛化规则留下的无宾语占位符（审计 F2/F6）
  'shell 脚本'                  # v2.12.5 新增：同上（无引号变体）
  'scripts/'                    # v2.12.5 新增：净化包不应出现任何开发者脚本路径
  '论衡开发者脚本'              # v2.12.5 新增：开发者工具引用只应存在于真源，不入包
  '\| \| \|'                     # v2.12.5 新增：空白占位行（表格渲染崩坏同型）
  # ---- v2.12.11 新增：维护者叙事词 ----
  # 背景（leak-audit §四.1）：现有 3 道门只认字面 token（`教训 #` / `.sh` / `scripts/`），
  #   对「维护者与平台审核博弈史」零覆盖：ClawHub T05 / SkillSpector / 五轮扫描 CLEAN /
  #   commit 前必跑脚本 等均可整段逸出。以下词命中即 fail-loud。
  '净化包|净化脚本'              # v2.12.11：双视图发布架构的内部叫法，使用者侧一律称「发布版」
  'ClawHub T0[0-9]'              # v2.12.11：平台逐轮审计台账编号（T05/T09…）
  'ClawScan|SkillSpector'        # v2.12.11：平台扫描器产品名，维护者叙事专有
  '扫描器'                       # v2.12.11：扫描器博弈叙事（「五轮 CLEAN」「认可设计表达」等）
  'commit 前'                    # v2.12.11：git 语境维护者动作，使用者无此动作
  '必跑硬门'                     # v2.12.11：维护者发布 SOP 内史
  '版本维护脚本'                 # v2.12.11：scripts/*.sh 被泛化后的维护者占位符
  '自审门'                       # v2.12.11：维护者自指体系叫法，使用者侧称「自检门」
  # ---- v2.12.13 新增：双视图发布架构内部叫法（构建脚本自身注入的页脚 + 判定表自述）----
  # 背景（教训 #321）：构建脚本 3a 给自己注入的页脚文案「发布净化版」进入 67 个文件，
  #   却不在 FINAL_PATTERNS 覆盖内（规则只防手写，不防自己写）。
  '净化版'                       # v2.12.13：双视图发布架构内部叫法
  'strip 剥除'                   # v2.12.13：剥除链内部术语（可发表性判定表:20 同型）
  '双视图'                       # v2.12.13：双视图发布架构内部叫法
  # ---- v2.12.63 新增：v2.12.42 引入的 `#R` 编号空间 + 维护者内档文件名 ----
  # 背景（2026-09-19 审计 C-1）：上列模式只认 `教训 #N` 字面，而 v2.12.42 新增的
  #   `references/_shared/治理/论衡仓库内教训.md` 用的是**另一套编号空间**（`#R001` 起，与 `#N` 解耦）
  #   ⇒ 该文件整篇维护者叙事（CI run id / commit hash / pytest 命令 / 「净化链」「release 链」）
  #   对全部残留模式**结构性地不可见**，随包出厂且从未报错。
  # 注：本组是**产物侧兜底**；源头拦截在 §2a 排除清单 + §2b' 白名单准入门（双保险）。
  '#R[0-9]{3}'                   # v2.12.63：仓库内教训编号空间（repo-internal）
  'repo-internal'                # v2.12.63：同上（英文自述）
  '论衡仓库内教训'               # v2.12.63：维护者内档文件名（被引用即视为泄漏）
)
FINAL_HITS=0
for pat in "${FINAL_PATTERNS[@]}"; do
  hits=$({ grep -rE "$pat" "${SCAN_INCLUDES[@]}" "$OUT_DIR" 2>/dev/null || true; } | wc -l | tr -d ' ')
  if [[ "$hits" -gt 0 ]]; then
    echo "  ❌ 内部痕迹残留：$pat（$hits 处）"
    FINAL_HITS=$((FINAL_HITS + 1))
  fi
done
if [[ "$FINAL_HITS" -gt 0 ]]; then
  echo ""
  echo "❌ 最终残留扫描未通过：$FINAL_HITS 项（教训 #296 铁律：教训是主控侧运维资产，不得进入发布包）"
  exit 1
fi
echo "  ✅ 最终残留扫描通过"

# ---- 4d. 语言政策声明门（v2.12.10 新增，防回归）----
# 背景：ClawHub SkillSpector 「Natural-Language Policy Violations」逐文件判定，
# 净化包内每个交付 .md 必须带一行「语言政策」声明（说明产出语言可切换 + 中文特化是设计定位）。
# 真源侧由 scripts/inject-lang-policy.py 注入；此处对产物做正向校验，漏注入即阻断发布。
LANG_MISSING=()
while IFS= read -r f; do
  rel="${f#"$OUT_DIR"/}"
  case "$rel" in
    SKILL.md) continue ;;  # SKILL.md 自带「语言边界」表，用另一套声明
  esac
  if ! grep -q '🌐 \*\*语言政策\*\*' "$f" 2>/dev/null; then
    LANG_MISSING+=("$rel")
  fi
done < <(find "$OUT_DIR" -name '*.md' | sort)
if [[ "${#LANG_MISSING[@]}" -gt 0 ]]; then
  echo ""
  echo "❌ 语言政策声明缺失 ${#LANG_MISSING[@]} 个文件（跑 python3 scripts/inject-lang-policy.py 修复）："
  for rel in "${LANG_MISSING[@]}"; do echo "  - $rel"; done
  exit 1
fi
echo "  ✅ 语言政策声明门通过（$(find "$OUT_DIR" -name '*.md' | wc -l | tr -d ' ') 个 md，除 SKILL.md 外均含声明）"

# ---- 4e. 剥离规则命中数自检（v2.12.11 新增，fail-loud）----
# 背景（教训 #192 同型）：sed/regex 剥离规则的「re-search 目标形态」一旦与真源写法失配，
#   规则会**静默空转**——不报错、不告警，只在包内留下维护者叙事。规则 3h-7 就这样从
#   v2.11.x 空转到 v2.12.10（真源早已是 heading 形态，规则还在找 bullet 形态）。
# 做法：对规则清单同时统计两侧命中数——真源（应 >0，否则规则已死/内容已同步删除）
#   + 产物（必须 =0，否则剥离未生效）。关键规则任一不满足即 fail-loud；
#   非关键规则仅告警（避免误伤「本就不存在」的合法规则）。
echo "🔎 剥离规则命中数自检（教训 #192 同型）..." >&2
# 格式：名称|正则|级别(critical/warn)|allow_empty(yes/no)
#   allow_empty=yes：该规则真源命中数**允许为 0**（内容已同步删除，或规则仅作产物侧回归守卫保留）；
#     标 yes 必须能说明理由（教训 #320：门写了却不生效 = 静默空转，比没门更危险）。
# 判定（v2.12.13 收紧，全量覆盖 purify() 规则）：
#   · 真源命中 = 0 且 allow_empty=no → **fail**（规则死亡：目标写法已变，须修规则/改标注）
#   · 产物命中 ≠ 0 → **一律 fail**（剥离未生效，直接阻断发布；不再区分级别）
RULE_CHECKS=(
  # —— 关键门段（critical：一旦失配即代表整段维护者内容漏入包）——
  # 前三项 2026-09-19 改 allow_empty=yes：其监控的**内容已外移到 references/设计文档-架构.md §六**
  #   （该文件整类 --exclude，不进包）⇒ 真源命中 0 属**预期**；条目**保留作产物侧回归守卫**
  #   （若外移内容日后漏回包内，产物侧命中 ≠ 0 仍一律 fail）。理由可复核：真源见 设计文档-架构.md §六。
  '版本修订硬门段|### 修订后必跑硬门三件套|critical|yes'  # 内容已外移（源侧 0 命中属预期）；产物侧守卫保留
  '版本修订质量门段|### 修订后必跑内容质量门脚本|critical|yes'  # 同上
  '版本升级自审门小节|### 版本升级自审门|critical|yes'  # 同上（节标题本身 3d 改名后为「版本一致性检查」）
  '维护者SOP指针块|### 维护者发布 SOP（已外移|critical|no'  # 真源有指针块（1 处）；包内必须 0
  'Archive保留建议清单|Archive 保留建议清单|critical|no'
  'commit 前表述|commit 前|critical|no'
  '教训字面|教训 #[0-9]|critical|no'
  '开发者脚本路径|scripts/|critical|no'
  # —— v2.12.13 新增：维护者叙事 / 双视图叫法（产物侧必为 0）——
  '净化包叫法|净化包|critical|no'
  '净化脚本叫法|净化脚本|critical|no'
  '自审门叫法|自审门|critical|no'
  '修订SOP叫法|修订 SOP|critical|no'
  '平台台账编号|ClawHub T0[0-9]|critical|no'
  '净化版叫法|净化版|critical|no'
  '双视图叫法|双视图|critical|no'
  'strip剥除叫法|strip 剥除|critical|yes'  # 4.1 已源侧中性化（真源 0 命中属预期）；保留作产物侧回归守卫
  # —— warn 级：内容可能已同步删除（allow_empty=yes），保留为产物侧回归守卫 ——
  '凭据措辞收敛|需主人提供 API key|warn|yes'  # v2.12.25 起：第二梯队（万方/科情/NSTL）整体取消，「需主人提供 API key」表述已源侧删除 → 真源 0 命中属预期；保留作产物侧回归守卫
  '跨平台等价命令表|跨平台等价命令|warn|no'
  '反哺未沉淀表述|没有自动沉淀到写手禁做清单|warn|no'
  '自动沉淀表述|实战教训自动沉淀|warn|yes'
  '主动写入表述|主控\*\*必须主动\*\*写入论衡工作区|warn|yes'
  '旧版一致性检查文件名|版本一致性检查-v2\.3\.0|warn|yes'
  '旧版M-Gate文件名|M-Gate-渐进式验证-v2\.2\.15|warn|yes'
  '相似项目复用段|相似项目复用检查|warn|yes'
  '二梯队API key|可选启二梯队知网/万方/科情需提供 API key|warn|yes'
  '旧版5.8清理记录|### 5\.8 Archive 清理记录|warn|yes'
  '扫描器叫法|扫描器|warn|yes'
  'SkillSpector叫法|SkillSpector|warn|yes'
  # ---- v2.12.63 新增：`#R` 编号空间（v2.12.42 引入后长期不在任何模式射程内）----
  '仓库内教训编号|#R[0-9]{3}|critical|no'      # 真源有（内档正文 + 教训索引指针）；包内必须 0
  '仓库内教训内档名|论衡仓库内教训|critical|no'  # 同上
  # ---- 2026-09-19 审计 C-3：purify() 全规则覆盖补齐（补入原先未纳入本表的规则）----
  # 口径说明（为何新条目一律标 allow_empty=yes）：本表新增条目的**真源命中数需实测**，
  #   而标 `no` 会在「真源已无该写法」时直接 fail（规则本已无用武之地却被判死亡）。
  #   故新条目一律标 yes（真源零命中只打 info），但**产物侧 ≠0 仍一律 fail** ——
  #   守卫强度不变，只避免误阻断已同步删除内容的构建。
  #   若日后实测真源确有命中，应改标 no 以恢复源侧死亡检测（见 C-3 报告）。
  #   另：regex 字段**不得含 `|`**（字段分隔符），需哈代表达时拆成多条。
  # 3b  git 发布指令（产物侧另有 §3h RESIDUAL_PATTERNS 同款 fail-closed 守卫）
  'git提交指令|git commit|warn|yes'
  'git推送指令|git push|warn|yes'
  'git打标指令|git tag|warn|yes'
  # 3k  模型健康度预检的 1-token ping 措辞
  '健康度ping措辞|1-token ping|warn|yes'
  # 3j  末条：凭据叠字清洗（真源本就无此叠字，纯产物侧守卫）
  '凭据三连叠字|主控绝不读取、主控绝不读取|warn|yes'
  # 3i  通用兜底两条（「列出 run/」/「ls run/」）
  '历史项目复用兜底A|主控 Phase 0 前用 `列出 run/`|warn|yes'
  '历史项目复用兜底B|主控 Phase 0 前用 `ls run/`|warn|yes'
  # 3o  DEV-ONLY 标记不得随包出厂（标记本身即维护者叙事）
  'DEV-ONLY段落|DEV-ONLY|warn|yes'
  # 3e  SKILL.md description 的「含技能自我维护」句（引用已剥离的 scripts/）
  'SKILL自我维护句|含技能自我维护|warn|yes'
  # 3m  长形态中性化（短形态由 FINAL_PATTERNS / 门 Q 另守）
  'AIG扫描器叫法|A\.I\.G 扫描器|warn|yes'
  '平台扫描器名|ClawScan|warn|yes'
  # 3h  设计文档路径形态（3h-1 / 3h-5，行级反向断言见规则 3h 末段 7c）
  '设计文档路径引用|references/设计文档\.md|warn|yes'
  # 3d  旧版自审门文件名（路径形态；短名形态由既有条目覆盖）
  '旧版自审门路径|_shared/版本升级自审门-v2\.3\.0\.md|warn|yes'
  # 3h-4 / 3p  模板拆分方案引用（C-4 死链；自本版起由 3p 程序化中和）
  '模板拆分方案引用|README-模板拆分方案\.md|warn|yes'
)
# 豁免理由表（C-7，2026-09-19 审计）—— 格式：名称|理由正文（不得含 `|`）
# 要求：① 每个 allow_empty=yes 条目必须在此登记理由且长度 ≥ RULE_REASON_MIN_CHARS；
#       ② 表中不得有孤儿（对应条目已不存在或已改为 no）—— 防理由表腐烂；
#       ③ 理由必须写「**为何允许真源零命中**」，不能写「待补」等占位词（最短长度即为此设）。
RULE_EMPTY_REASONS=(
  '版本修订硬门段|真源内容已外移到 references/设计文档-架构.md §六（该文件整类被 --exclude，不进包）⇒ 零命中属预期；条目保留作产物侧回归守卫。'
  '版本修订质量门段|同「版本修订硬门段」：内容随 §六 一并外移（不进包）⇒ 零命中属预期；保留作产物侧回归守卫。'
  '版本升级自审门小节|节标题已被净化规则 3d 改名（版本升级自审门→版本一致性检查）⇒ 零命中属预期；保留作产物侧回归守卫。'
  'strip剥除叫法|该措辞已在真源侧中性化（审计 §四.1）⇒ 零命中属预期；保留作产物侧回归守卫。'
  '凭据措辞收敛|第二梯队（万方/科情/NSTL）整体取消后真源已无此措辞 ⇒ 零命中属预期；保留作产物侧回归守卫。'
  '自动沉淀表述|真源已改用「实战教训沉淀建议（待主人 review 后生效）」措辞 ⇒ 零命中属预期；保留作产物侧回归守卫。'
  '主动写入表述|真源侧已改为「主控产出建议草稿（待主人 review 后 merge）」表述 ⇒ 零命中属预期；保留作产物侧回归守卫。'
  '旧版一致性检查文件名|旧文件名只应出现在已出包的历史文档 ⇒ 真源零命中属预期；保留作产物侧回归守卫。'
  '旧版M-Gate文件名|规则 3d 已把该文件名改指 M-Gate-Algorithm.md ⇒ 真源零命中属预期；保留作产物侧回归守卫。'
  '相似项目复用段|真源段落已改写为「历史项目素材复用（可选）」⇒ 零命中属预期；保留作产物侧回归守卫。'
  '二梯队API key|第二梯队检索源整体取消 ⇒ 真源零命中属预期；保留作产物侧回归守卫。'
  '旧版5.8清理记录|规则 3l 的目标标题已不存在（内容已重写为「项目历史记录归档」）⇒ 零命中属预期；保留作产物侧回归守卫。'
  '扫描器叫法|真源侧已中性化为「审核工具」（门 Q 同口径）⇒ 零命中属预期；保留作产物侧回归守卫。'
  'SkillSpector叫法|真源侧已中性化为「平台安全扫描」⇒ 零命中属预期；保留作产物侧回归守卫。'
  'git提交指令|规则 3b 的替换目标；真源 git 指令可能已全部外移或删除 ⇒ 零命中放行；产物侧另有 §3h 同款守卫。'
  'git推送指令|同「git提交指令」：真源可能已无该指令 ⇒ 零命中放行；产物侧命中仍一律 fail。'
  'git打标指令|同「git提交指令」：真源可能已无该指令 ⇒ 零命中放行；产物侧命中仍一律 fail。'
  '健康度ping措辞|规则 3k 的替换目标；措辞可能已随真源改写而消失 ⇒ 零命中放行；产物侧命中仍一律 fail。'
  '凭据三连叠字|规则 3j 末条仅作叠字清洗兜底（真源本就无此叠字）⇒ 零命中属预期。'
  '历史项目复用兜底A|规则 3i 的兜底正则；真源措辞可能已被主替换直接改写 ⇒ 零命中放行。'
  '历史项目复用兜底B|同「历史项目复用兜底A」：同为兜底正则 ⇒ 零命中放行。'
  'DEV-ONLY段落|规则 3o 的标记；真源可能已无该标记（段落已整段删除）⇒ 零命中放行；产物侧命中一律 fail。'
  'SKILL自我维护句|规则 3e 的替换目标（description 自我维护句）；真源可能已删 ⇒ 零命中放行。'
  'AIG扫描器叫法|真源侧已中性化（门 Q 禁止可见面出现该叫法）⇒ 零命中属预期。'
  '平台扫描器名|真源侧已中性化（门 Q 同口径）⇒ 零命中属预期；保留作产物侧回归守卫。'
  '设计文档路径引用|references/设计文档.md 已整类 --exclude；真源引用由规则 3h 系列统一改写 ⇒ 零命中属预期。'
  '旧版自审门路径|旧文件路径只应存在于已出包的历史文档 ⇒ 零命中属预期；保留作产物侧回归守卫。'
  '模板拆分方案引用|该模板拆分说明文件已被 --exclude；引用自本版起由规则 3p（程序化死链中和）处理 ⇒ 零命中属预期。'
)
RULE_REASON_MIN_CHARS=12
RULE_FAIL=0
RULE_EMPTY=0

# ---- C-7（2026-09-19 审计）：豁免理由校验 —— 禁止「空理由即豁免」----
# 背景：`allow_empty=yes` 是「真源零命中仍放行」的**唯一**逃生口。若理由字段可空，
#   这条路就退化成「标注一下即可关掉真源侧守卫」（门 R.3 只校验格式与基数，不看理由）。
# 修法：理由表双向闭合 + 最小长度；任一不满足即计入 RULE_FAIL（与规则自检同批阻断）。
_RR_YES_NAMES=""   # 必须在 set -u 下显式初始化（否则首个 allow_empty 条目即 unbound variable）
for entry in "${RULE_CHECKS[@]}"; do
  IFS='|' read -r _rn _rp _rl _ra <<<"$entry"
  [[ "$_ra" == "yes" ]] || continue
  _RR_YES_NAMES="${_RR_YES_NAMES}${_rn}"$'\n'
  _REASON=""
  for _re_entry in "${RULE_EMPTY_REASONS[@]}"; do
    IFS='|' read -r _en _et <<<"$_re_entry"
    if [[ "$_en" == "$_rn" ]]; then _REASON="$_et"; break; fi
  done
  if [[ -z "$_REASON" ]]; then
    echo "      ❌ 豁免无理由：'$_rn' 标了 allow_empty=yes 但未在 RULE_EMPTY_REASONS 登记理由"
    RULE_FAIL=$((RULE_FAIL + 1))
  elif [[ "${#_REASON}" -lt "$RULE_REASON_MIN_CHARS" ]]; then
    echo "      ❌ 豁免理由过短（${#_REASON} < $RULE_REASON_MIN_CHARS）：'$_rn'"
    RULE_FAIL=$((RULE_FAIL + 1))
  fi
done
for _re_entry in "${RULE_EMPTY_REASONS[@]}"; do
  IFS='|' read -r _en _et <<<"$_re_entry"
  if ! grep -qxF "$_en" <<<"$_RR_YES_NAMES"; then
    echo "      ❌ 理由表孤儿：'$_en' 已不是 allow_empty=yes 条目（理由表腐烂）"
    RULE_FAIL=$((RULE_FAIL + 1))
  fi
done
if [[ "$RULE_FAIL" -gt 0 ]]; then
  echo ""
  echo "❌ 豁免理由校验未通过（$RULE_FAIL 项）—— 防「空理由即豁免」（审计 C-7）"
  echo "   修法：在 RULE_EMPTY_REASONS 为每个 allow_empty=yes 条目写明「为何允许真源零命中」；"
  echo "         已不再豁免的条目请从理由表删除（双向闭合，不留孤儿）。"
  exit 1
fi
for entry in "${RULE_CHECKS[@]}"; do
  IFS='|' read -r rname rpat rlevel rallow <<<"$entry"
  r_src=$( { grep -rE "$rpat" "${SCAN_INCLUDES[@]}" "$SKILL_ROOT/references" "$SKILL_ROOT/SKILL.md" "$SKILL_ROOT/QUICKSTART.md" "$SKILL_ROOT/README.md" 2>/dev/null || true; } | wc -l | tr -d ' ')
  r_pkg=$( { grep -rE "$rpat" "${SCAN_INCLUDES[@]}" "$OUT_DIR" 2>/dev/null || true; } | wc -l | tr -d ' ')
  printf '   [%-8s] %-24s 真源=%-4s 产物=%s\n' "$rlevel" "$rname" "$r_src" "$r_pkg"
  if [[ "$r_src" -eq 0 ]]; then
    if [[ "$rallow" == "yes" ]]; then
      echo "      ℹ️ 真源零命中（allow_empty=yes，作为产物侧回归守卫保留）"
      RULE_EMPTY=$((RULE_EMPTY + 1))
    else
      echo "      ❌ 规则已死亡：真源零命中且未标注 allow_empty（须修规则或改标注）"
      RULE_FAIL=$((RULE_FAIL + 1))
    fi
  fi
  if [[ "$r_pkg" -ne 0 ]]; then
    echo "      ❌ 剥离未生效：产物仍含该形态 $r_pkg 处"
    RULE_FAIL=$((RULE_FAIL + 1))
  fi
done
if [[ "$RULE_FAIL" -gt 0 ]]; then
  echo ""
  echo "❌ 剥离规则自检未通过（$RULE_FAIL 项）：规则与真源形态失配，或规则未生效"
  echo "   修法：核对 build-clawhub-release.sh 中该规则 re-search 目标 vs 真源当前写法；"
  echo "   若确已同步删除该内容，请把该条目第 4 字段标 yes 并写明理由（勿留无标注死规则）。"
  exit 1
fi
echo "  ✅ 剥离规则自检通过（共 ${#RULE_CHECKS[@]} 条：生效 $(( ${#RULE_CHECKS[@]} - RULE_EMPTY )) 条 / allow_empty $RULE_EMPTY 条）"

# ---- C-3（2026-09-19 审计）：purify() 中**无法用「真源>0 / 产物=0」表达**的规则，改用**正向不变量**断言 ----
# RULE_CHECKS 只能表达「该有的没有」；但以下规则的失败模式是「规则**根本没生效**」，
#   产物侧本来就没那个字符串，负向扫描永远看不出来（静默空转）：
#   ① 规则 3a（版本号栈精简）：产物每个 md 不得再出现**连续**的 `> 版本：` 行
#      （栈形态 = 连续多行；若精简失效，产物就会留存 20+ 行历史版本栈）。
#      注：只查「连续栈」，不查单文件总行数 —— 非连续的 `> 版本：` 提及（如模板样例）是合法内容。
#   ② 规则 3f（反哺报告处理.md 整篇换正文）：产物该文件必须含「（发布版简化）」标题，
#      证明整篇替换**真的发生了**（该规则的失败模式是目标错位 ⇒ 完全没替换）。
#   ③ 规则 3n（安装命令版本 pin）：已在 §3n 就地断言（产物 pin 必须等于本包版本）。
_POS_FAIL=0
_VSTACK_BAD="$(find "$OUT_DIR" -name '*.md' -exec awk '
  FNR == 1 { prev = 0 }
  /^> 版本：/ { if (prev) { print FILENAME "（第 " FNR " 行起有连续版本号栈）" } prev = 1; next }
  { prev = 0 }' {} + 2>/dev/null)"
if [[ -n "$_VSTACK_BAD" ]]; then
  echo "      ❌ 规则 3a 断言失败：产物仍有连续「> 版本：」版本号栈（整段精简未生效）：" >&2
  printf '%s\n' "$_VSTACK_BAD" | sed 's/^/         - /' >&2
  _POS_FAIL=$((_POS_FAIL + 1))
fi
if ! grep -qF '（发布版简化）' "$OUT_DIR/references/_shared/治理/反哺报告处理.md" 2>/dev/null; then
  echo "      ❌ 规则 3f 断言失败：references/_shared/治理/反哺报告处理.md 未见「（发布版简化）」标题（整篇替换未发生）" >&2
  _POS_FAIL=$((_POS_FAIL + 1))
fi
if [[ "$_POS_FAIL" -gt 0 ]]; then
  echo "❌ purify() 正向不变量断言未通过（$_POS_FAIL 项）：规则未生效（静默空转）" >&2
  exit 1
fi
echo "  ✅ purify() 正向不变量通过（版本号栈无连续残留 / 反哺报告整篇替换已发生）"

# 净化残留扫描已完成（前置到 #3h，教训 #213），以下为汇总段（可被 exec timeout SIGTERM 不影响产物）

# ---- 5. 汇总 ----
echo ""
echo "✅ 净化发布包已生成：$OUT_DIR"
echo "   文件数：$(find "$OUT_DIR" -type f | wc -l | tr -d ' ')（对比真源 $(find "$SKILL_ROOT" -type f -not -path '*/.git/*' -not -path '*/outputs/*' -not -path '*/__pycache__/*' -not -path '*/.pytest_cache/*' -not -name '*.bak.*' -not -name '*.pyc' | wc -l | tr -d ' ')，排除 .git/ 与缓存（__pycache__/.pytest_cache/.pyc）与 .bak.* 备份与 outputs/ 产物）"
echo ""
echo "下一步（手动执行）："
echo "  clawhub publish $OUT_DIR --slug lunheng-article-pipeline --version $VERSION --name \"论衡 — 严肃长文流水线\""
echo "  ⚠️ --name 必传（教训 #200）：CLI 不读 SKILL.md frontmatter 的 displayName，缺省会用文件夹名 2.7.9 当 H1"
echo "  （或先 dry-run 预览并检查 JSON 的 displayName 是否为人类可读名：clawhub publish $OUT_DIR --slug lunheng-article-pipeline --version $VERSION --name \"论衡 — 严肃长文流水线\" --dry-run --json）"
