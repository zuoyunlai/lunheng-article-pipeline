#!/usr/bin/env bash
# 论衡版本号同步脚本（P1-3 版本号自动化 - 层 2）
#
# ⚠️ 三层联动防漏改（教训 #118.1）：
#   层 1 本脚本（check-version.sh）= 本地只读验证
#   层 2 sync-version.sh = 本地批量同步写入
#   层 3 .github/workflows/version-check.yml = CI 云端自动验证
#   改角色文件名（references/agents/0X-*.md 重命名）时，必须三处同步更新角色文件清单，
#   否则版本号自动化会扫错路径直接报错（v2.3.0 重构时 scripts/ 两层漏改，教训 #118.1）。

#
# 用途：从 SKILL.md frontmatter 读取版本号，批量同步到所有应含版本号的文件
# 调用：./scripts/sync-version.sh [--dry-run]
# 选项：--dry-run  只显示将修改的内容，不实际写入
# 退出码：0 = 同步成功 / 1 = 同步失败

set -e

SKILL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"  # v2.5.6 P0 修复：用于 self-audit-gate.sh 调用

# 自动检测目录结构：工作区（pipeline/）vs skill 副本（references/ + 根 SKILL.md）
if [ -d "$SKILL_ROOT/pipeline" ]; then
  CONTENT_DIR="$SKILL_ROOT/pipeline"
  SKILL_MD="$CONTENT_DIR/SKILL.md"
  ENTRY_DIR="$CONTENT_DIR"
elif [ -d "$SKILL_ROOT/references" ]; then
  CONTENT_DIR="$SKILL_ROOT/references"
  SKILL_MD="$SKILL_ROOT/SKILL.md"
  ENTRY_DIR="$SKILL_ROOT"
else
  echo "❌ 无法识别目录结构（找不到 pipeline/ 或 references/）"
  exit 1
fi
DRY_RUN=false

if [ "$1" == "--dry-run" ]; then
  DRY_RUN=true
  echo "🔍 DRY-RUN 模式：只显示将修改的内容，不实际写入"
  echo ""
fi

# 从 SKILL.md frontmatter 读取版本号（单一真源）
EXPECTED=$(grep -E '^[[:space:]]*version:' "$SKILL_MD" | head -1 | sed -E 's/^[[:space:]]*version:[[:space:]]*//;s/["'"'"']//g;s/[[:space:]]*$//')

if [ -z "$EXPECTED" ]; then
  echo "❌ 无法从 SKILL.md 读取版本号"
  exit 1
fi

echo "📌 目标版本号（来自 SKILL.md frontmatter）：v$EXPECTED"
echo ""

# 定义需要同步版本号的文件列表
# 格式：文件路径|插入位置（header=文件顶部，replace=全文替换旧版本号）
# 路径规则：内容文件（glossary/agents 等）相对 CONTENT_DIR；入口文件（README/QUICKSTART）用 @ 前缀，相对 ENTRY_DIR
SYNCS=(
  # 核心文档（顶部插入版本号）
  "_shared/glossary-full.md|header"
  "_shared/glossary-core.md|header"
  "pipeline-readme.md|header"
  "设计文档.md|header"
  "设计文档-架构.md|header"
  "设计文档-哲学.md|header"
  "deliverables.md|header"
  "case-studies.md|header"
  "operations.md|header"
  "errors.md|header"

  # 共享协议（顶部插入版本号）
  "_shared/M-Gate-Algorithm.md|header"
  "_shared/M-Gate-Algorithm-appendix.md|header"
  "_shared/audit-checklist-quickref.md|header"

  # 10 个角色卡（顶部插入版本号）
  "agents/00-主控-coordinator.md|header"
  "agents/01-文献检索-literature-scout.md|header"
  "agents/02-数据检索-data-scout.md|header"
  "agents/03-案例检索-case-scout.md|header"
  "agents/04-分析-analyst.md|header"
  "agents/05-写作-writer.md|header"
  "agents/06-批判-critical-companion.md|header"
  "agents/07-审计-auditor.md|header"
  "agents/08-终检-final-inspector.md|header"
  "agents/09-审稿-peer-reviewer.md|header"

  # 主控扩展职责（v2.5.0 主控卡拆分后新增）
  "agents/00-主控-扩展职责.md|header"

  # 派发话术（v2.5.6 拆分新增，教训 #183 补入三层清单）
  "dispatch/T1-文献检索.md|header"
  "dispatch/T2-数据检索.md|header"
  "dispatch/T3-案例检索.md|header"
  "dispatch/T4-分析.md|header"
  "dispatch/T5-写手.md|header"
  "dispatch/T6-批判.md|header"
  "dispatch/T7-审计.md|header"
  "dispatch/T8-终检.md|header"
  "dispatch/T9-同行评审.md|header"
  "dispatch/G14-中文AI痕迹检测器.md|header"

  # 闸门 + 检测器（v2.4.0 G14 新增）
  "gates/14-中文AI痕迹-gate.md|header"
  "checkers/中文AI痕迹-checker.md|header"

  # 扩展 _shared 协议（实战反馈 + v2.5.0/v2.5.1 新增）
  "_shared/执行韧化协议-exec.md|header"
  "_shared/执行韧化协议-design.md|header"
  "_shared/failure-modes.md|header"
  "_shared/字数判定表.md|header"
  "_shared/degraded-scenarios.md|header"
  "_shared/期刊数据库.md|header"
  "_shared/期刊匹配算法.md|header"
  "_shared/中文数据源集成.md|header"
  "_shared/format-export.md|header"

  # _shared 协议（v2.5.6 第三方独立审查建议 #5，教训 #175 防漏改）
  "_shared/工具能力边界.md|header"
  "_shared/关键协议.md|header"
  "_shared/教训索引.md|header"
  "_shared/模型候选池.md|header"
  "_shared/可发表性判定表.md|header"
  # v2.12.1 版本一致性盲区修复：project-archive-sop（v2.7.16 引入）+ 路径校验规范（v2.9.1 引入）补入清单
  "_shared/project-archive-sop.md|header"
  "_shared/路径校验规范.md|header"
  # v2.12.14 SKILL.md 瘦身外移文件（批次 4.6/4B）
  "_shared/pipeline-overview.md|header"
  "_shared/asset-index.md|header"
  "_shared/external-services.md|header"

  # 模板（v2.4.6 + v2.5.0 + v2.5.1 + v2.6.4 补全，教训 #175 防漏改）
  "templates/任务简报-template.md|header"
  "templates/审稿报告-template.md|header"
  "templates/G14检测报告-template.md|header"
  "templates/status-template.md|header"
  "templates/投稿就绪检查表-template.md|header"
  "templates/修订说明-template-full.md|header"
  "templates/案例卡-template.md|header"
  "templates/数据卡-template.md|header"
  "templates/文献卡-template.md|header"
  "templates/先行者清单-template.md|header"
  "templates/交接报告-template.md|header"
  "templates/图表-SVG-template.md|header"

  # 顶层文档（入口，v2.3.6 起纳入；@ = 相对 ENTRY_DIR）
  "@README.md|header"
  "@QUICKSTART.md|header"

  # v2.10.0 SKILL.md 外置文件（v2.10.0 P1-3 拆分新增，教训 #198 补入防漏改）
  "model-assignment.md|header"
  "permissions.md|header"
  "_shared/phase-1-details.md|header"
  "_shared/phase-2-details.md|header"
  "_shared/phase-3-details.md|header"
  "_shared/dispatch-header.md|header"

  # v2.12.12 版本一致性盲区修复：phase-order.yaml（阶段真源，头部自述「版本随 SKILL.md 同步」
  #   但既不在本清单、也不是 markdown 块引用格式，故长期停在旧版本戳 —— 净化包内随包分发的
  #   版本与 SKILL.md 不一致）。用 yarnversion 模式改专用 `version: X.Y.Z` 行。
  "_shared/phase-order.yaml|yamlversion"
)

# v2.12.20（教训 #331）：header 模式改为「排队 + 末尾一次性归一化」，写入路径统一由
#   scripts/normalize-version-header.py 承担（幂等）。
HEADER_FILES=()
UPDATED=0
SKIPPED=0

echo "=== 版本号同步 ==="
for sync in "${SYNCS[@]}"; do
  IFS='|' read -r file mode <<< "$sync"
  # 入口文件（@ 前缀）相对 ENTRY_DIR，内容文件相对 CONTENT_DIR
  if [[ "$file" == @* ]]; then
    file="${file#@}"
    full_path="$ENTRY_DIR/$file"
  else
    full_path="$CONTENT_DIR/$file"
  fi

  if [ ! -f "$full_path" ]; then
    echo "⚠️  跳过：$file（文件不存在）"
    SKIPPED=$((SKIPPED+1))
    continue
  fi

  # 检查是否已包含当前版本号（replace / yamlversion 专用）
  # v2.12.20（教训 #331）：header 模式**不能**在此提前 continue——「头部已有本版本号」
  # 恰恰是历史累积空行最严重的文件（每次发版都被跳过归一化），跳过等于永远清不掉。
  # header 模式一律排进 HEADER_FILES，由 normalize-version-header.py 幂等处理。
  if [ "$mode" != "header" ] && head -1 "$full_path" | grep -qE "v$EXPECTED"; then
    echo "⏭️  跳过：$file（已包含 v$EXPECTED）"
    SKIPPED=$((SKIPPED+1))
    continue
  fi
  if [ "$mode" == "header" ]; then
    # v2.12.20（教训 #331）：旧实现用
    #   sed -i "${CLOSE_LINE}a\ ... \ ..."
    # 追加版本戳行——sed 的 `a\` 把尾部续行当成文本内容，等于多写一个空行；末尾的
    # trim() 只裁剪多余的版本行、不管空行 → 每个受管文件每次 sync 净增 1 个空行
    # （实测 README.md：v2.12.10 = 0 个 → v2.12.19 = 9 个；教训索引 47 个）。
    # 现在只排队；写入与归一化由 normalize-version-header.py 一次性完成（幂等）。
    HEADER_FILES+=("$full_path")
    if [ "$DRY_RUN" == true ]; then
      echo "📝 将归一化：$file（版本戳 v$EXPECTED + 文件头元数据块）"
    fi
    UPDATED=$((UPDATED+1))
  elif [ "$mode" == "replace" ]; then
    if [ "$DRY_RUN" == true ]; then
      echo "📝 将修改：$file（全文替换为 v$EXPECTED）"
    else
      # 备份原文件
      cp "$full_path" "$full_path.bak.$(date +%Y%m%d-%H%M%S)"

      # 替换所有 v2.2.x 为当前版本号
      sed -i -E "s/v2\.2\.[0-9]+/v$EXPECTED/g" "$full_path"

      echo "✅ 更新：$file（全文替换为 v$EXPECTED）"
    fi
    UPDATED=$((UPDATED+1))
  elif [ "$mode" == "yamlversion" ]; then
    # v2.12.12：改 YAML 顶层 `version: X.Y.Z` 行（phase-order.yaml 专用；不带 v 前缀）
    if [ "$DRY_RUN" == true ]; then
      echo "📝 将修改：$file（version: 行 → $EXPECTED）"
    else
      cp "$full_path" "$full_path.bak.$(date +%Y%m%d-%H%M%S)"
      sed -i -E "s/^version: [0-9]+\.[0-9]+\.[0-9]+/version: $EXPECTED/" "$full_path"
      echo "✅ 更新：$file（version: → $EXPECTED）"
    fi
    UPDATED=$((UPDATED+1))
  fi
done

# ---- 安装命令 pin 同步（教训 #297）----
# check-version.sh 会校验 QUICKSTART 的 @zuoyunlai/...@x.y.z pin，但上面的循环
# 遇到「头部已有本版本号」就直接 skip，导致 bump 后 pin 停在旧版且永远不被修。
# 故 pin 必须独立同步，不能搭头部的车。
# v2.12.13（方案 1.7）：pin 载体改**多文件列表**——README.md 也是 pin 载体
#   （README.md:193 `@2.12.1` 曾落后 11 版而从未被同步）。
PIN_FILES=("$ENTRY_DIR/QUICKSTART.md" "$ENTRY_DIR/README.md")
for PIN_FILE in "${PIN_FILES[@]}"; do
  [ -f "$PIN_FILE" ] || continue
  PIN_NAME="$(basename "$PIN_FILE")"
  OLD_PIN="$(grep -oE '@zuoyunlai/lunheng-article-pipeline@[0-9]+\.[0-9]+\.[0-9]+' "$PIN_FILE" | head -1 || true)"
  if [ -n "$OLD_PIN" ] && [ "$OLD_PIN" != "@zuoyunlai/lunheng-article-pipeline@$EXPECTED" ]; then
    if [ "$DRY_RUN" == true ]; then
      echo "📝 将修改：$PIN_NAME（安装 pin $OLD_PIN → v$EXPECTED）"
    else
      sed -i -E "s|@zuoyunlai/lunheng-article-pipeline@[0-9]+\.[0-9]+\.[0-9]+|@zuoyunlai/lunheng-article-pipeline@$EXPECTED|g" "$PIN_FILE"
      echo "✅ 更新：$PIN_NAME（安装 pin → v$EXPECTED）"
    fi
    UPDATED=$((UPDATED+1))
  else
    echo "⏭️  跳过：$PIN_NAME（安装 pin 已是 v$EXPECTED）"
  fi
done

echo ""
echo "✂️  文件头归一化（版本戳 / 语言政策行，空行收敛为「各行之间恰好 1 空行」）"
if [ "$DRY_RUN" == true ]; then
  echo "（DRY-RUN 模式，未实际修改）"
else
  # v2.12.20（教训 #331）：旧实现（内联 trim() heredoc）只删多余的 `> 版本：` 行、
  # 不管它们之间累积的空行；且 os.walk('.') 依赖调用时的工作目录。现统一交给
  # normalize-version-header.py：以 SKILL_ROOT 为根遍历，写入前先剥净
  # 「版本戳行 + 其后的连续空行」再补写成规范形态 → 连跑两次零 diff。
  NORMALIZE_ARGS=(--root "$SKILL_ROOT" --version "$EXPECTED" --date "$(date +%Y-%m-%d)")
  if [ ${#HEADER_FILES[@]} -gt 0 ]; then
    python3 "$SCRIPT_DIR/normalize-version-header.py" "${NORMALIZE_ARGS[@]}" --update "${HEADER_FILES[@]}"
  else
    python3 "$SCRIPT_DIR/normalize-version-header.py" "${NORMALIZE_ARGS[@]}"
  fi
fi

echo ""
echo "📊 统计："
echo "  ✅ 更新：$UPDATED"
echo "  ⏭️  跳过：$SKIPPED"
echo ""

if [ "$DRY_RUN" == true ]; then
  echo "🔍 DRY-RUN 完成，未实际写入文件"
  echo "   如需实际同步，请执行：./scripts/sync-version.sh"
else
  echo "✅ 版本号同步完成（v$EXPECTED）"
  echo "   建议执行 ./scripts/check-version.sh 验证同步结果"
  echo ""
  # 第三方独立审查建议 #2（v2.5.6 P0 必修，教训 #175）：自动跑自审门，不依赖主控「记得」跑
  if [ -f "$SCRIPT_DIR/self-audit-gate.sh" ]; then
    echo "🛡️  启动自动自审门（v2.5.6 新增）..."
    echo ""
    if bash "$SCRIPT_DIR/self-audit-gate.sh"; then
      echo ""
      echo "✅ 自审门通过，版本同步完成"
    else
      echo ""
      echo "❌ 自审门失败，请修复后重新跑 sync-version.sh"
      exit 1
    fi
  else
    echo "⚠️  self-audit-gate.sh 不存在，跳过自动自审门"
  fi
fi

# 清理 .bak 备份（v2.5.21 自审门审查发现，修复 v2.5.11 设计漏洞）
# v2.5.11 设计漏洞：清理逻辑在脚本开头（sync 跑前清旧）→ 但 sync 本身用 cp 创建 .bak 备份
# → 本轮新 .bak 在 sync 跑完后才生成，永远不会被本次 sync 清掉，每次 sync 累积一份（实测堆积 98 个）
# v2.5.21 修复：清理逻辑移到 sync 末尾（自审门通过后）→ 语义 =「同步成功才清、失败保留」
# → sync 失败 / 自审门失败会 exit 1，.bak 保留供回滚；成功才清掉所有 .bak（含本轮临时备份）
# 设计依据：git 已提供版本控制（真源），cp 备份只是 sync 过程的临时保险，成功即清
if [ "$DRY_RUN" != true ]; then
  BAK_COUNT=$(find "$SKILL_ROOT" -name '*.bak.*' -not -path '*/.git/*' 2>/dev/null | wc -l | tr -d ' ')
  if [ "$BAK_COUNT" -gt 0 ]; then
    find "$SKILL_ROOT" -name '*.bak.*' -not -path '*/.git/*' -delete 2>/dev/null || true
    echo ""
    echo "🧹 清理 .bak 备份（$BAK_COUNT 个，同步成功才清，失败时保留供回滚）"
  fi
fi
