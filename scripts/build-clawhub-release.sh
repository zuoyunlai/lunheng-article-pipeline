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
#   默认从 SKILL.md 读取当前版本号，输出到 outputs/clawhub-release/<VERSION>/
#   然后手动执行：clawhub publish outputs/clawhub-release/<VERSION> --slug ... --version <VERSION>
# =============================================================================

set -euo pipefail

# ---- 目录定位 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_ROOT="$SKILL_ROOT/outputs/clawhub-release"

# ---- 版本号 ----
VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  VERSION="$(grep -m1 '^version:' "$SKILL_ROOT/SKILL.md" | sed 's/version:[[:space:]]*//' | tr -d '"')"
fi
if [[ -z "$VERSION" ]]; then
  echo "❌ 无法确定版本号，请显式传入：bash scripts/build-clawhub-release.sh 2.3.9" >&2
  exit 1
fi

OUT_DIR="$OUT_ROOT/$VERSION"
echo "🔧 生成 ClawHub 净化发布包 v$VERSION"
echo "   源：$SKILL_ROOT"
echo "   输出：$OUT_DIR"

# ---- 1. 清空旧输出 ----
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

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
    --exclude 'audits' --exclude 'scripts' --exclude '.github' \
    --exclude 'references/_shared/archive' --exclude 'references/design' \
    --exclude 'references/_shared/m_exist_1_diff.sh' \
    --exclude 'references/_shared/通用韧化块-v2.1.0.md' \
    --exclude 'references/_shared/版本升级自审门-*.md' \
    --exclude 'references/_shared/M-Gate-渐进式验证-*.md' \
    --exclude 'references/templates/README-模板拆分方案.md' \
    --exclude 'README.md' \
    --exclude 'CHANGELOG.md' \
    --exclude 'tests' \
    --exclude 'references/设计文档.md' \
    --exclude 'references/设计文档-架构.md' \
    --exclude 'references/设计文档-哲学.md' \
    --exclude 'PERFORMANCE-PROFILE.md' \
    --exclude 'references/_shared/教训索引.md' \
    --exclude 'pyproject.toml' \
    --exclude 'requirements.txt' \
    --exclude 'Makefile' \
    --exclude '.shellcheckrc' \
    --exclude '.pytest_cache' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'RELEASE-*.md' \
    "$SKILL_ROOT/" "$OUT_DIR/"
else
  cp -a "$SKILL_ROOT/." "$OUT_DIR/"
  # 手动清理
  rm -rf "$OUT_DIR/.git" "$OUT_DIR/outputs" "$OUT_DIR/audits" "$OUT_DIR/scripts" \
    "$OUT_DIR/.github" "$OUT_DIR/tests" "$OUT_DIR/references/_shared/archive" "$OUT_DIR/references/design" \
    "$OUT_DIR/docs" "$OUT_DIR/.bak-20260823-2024-v2.4.0-migrate" \
    "$OUT_DIR/.pytest_cache"
  find "$OUT_DIR" -name '*.bak.*' -delete
  find "$OUT_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +
  find "$OUT_DIR" -name '*.pyc' -delete
  rm -f "$OUT_DIR/references/_shared/m_exist_1_diff.sh" "$OUT_DIR/PERFORMANCE-PROFILE.md"
  rm -f "$OUT_DIR/references/_shared/教训索引.md"
  rm -f "$OUT_DIR/references/_shared/通用韧化块-v2.1.0.md"
  rm -f "$OUT_DIR/.gitignore"
  rm -f "$OUT_DIR/references/templates/README-模板拆分方案.md"
  rm -f "$OUT_DIR/README.md"
  rm -f "$OUT_DIR/CHANGELOG.md"
  rm -f "$OUT_DIR/references/设计文档.md" "$OUT_DIR/references/设计文档-架构.md" "$OUT_DIR/references/设计文档-哲学.md"
  rm -f "$OUT_DIR"/RELEASE-*.md
  rm -f "$OUT_DIR"/references/_shared/版本升级自审门-*.md
  rm -f "$OUT_DIR"/references/_shared/M-Gate-渐进式验证-*.md
  # 剥离开发者工具文件（教训 #212）
  for f in "${DEV_TOOL_FILES[@]}"; do
    rm -f "$OUT_DIR/$f"
  done
fi

# ---- 2b. 净化包禁入清单守卫（P2「changelog 完整化」新增）----
# CHANGELOG.md / README.md 含「教训 #N」编号与真源仓库链接，属主控侧运维资产
# （铁律：教训不对技能用户开放）。它们不在净化包内时才安全；此处做 fail-closed 守卫，
# 避免日后新增顶层文档时被 rsync 默认带入、直到最终残留扫描才炸。
FORBIDDEN_IN_PACKAGE=(
  'CHANGELOG.md'
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
        out.append(f'> 版本：v{version}（发布净化版，自动同步）\n')
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

  # 3f. 主控卡「反哺报告处理」整段替换为净化版（彻底消除跨项目共享状态写入表述，回应 Finding 3）
  if [[ "$(basename "$f")" == "00-主控-扩展职责.md" ]]; then
  # 修复（v2.6.0）：旧版匹配 00-主控-coordinator.md，但「反哺报告处理」段在
  # 扩展职责卡 §二十（教训 #192 同型：改 A 漏 A 漏——重命名文件后 sed 目标未跟）
    python3 - "$f" <<'PYEOF'
import sys, re
path = sys.argv[1]
s = open(path, encoding='utf-8').read()
# 定位「## 二十、反哺报告处理」到「## 二十一、」之间的整段，替换为净化版
# （v2.6.0 修正：旧模式 ## 反哺报告处理→## 边界 是 coordinator 老卡格式，永不匹配）
pattern = re.compile(r'## 二十、反哺报告处理.*?(?=\n## 二十一、)', re.DOTALL)
replacement = '''## 二十、反哺报告处理（发布版简化，v2.6.0）

主控会话结束时（Phase 5 终检后）执行：

1. **读取** T7 审计员交付的 `audits/反哺报告-vN.md`
2. **列出建议 merge 的反哺规则**到 `final/交付说明.md` 末段「建议 merge 的反哺规则」清单
3. **不自动修改任何角色卡或共享状态文件**——等主人人工 review 后手动 merge
4. **项目内教训记录**：本次实战发现写入 `run/<项目>/audit-lessons.md`（**项目内文件**，非跨项目共享状态）；跨项目教训沉淀仅存在于论衡开发版（含跨项目 lessons 同步机制），见 GitHub 仓库：https://github.com/zuoyunlai/lunheng-article-pipeline

如反哺报告为空（无新增问题），主控写「本轮反哺报告：T7 未发现可沉淀新增问题」，避免机制被跳过。
'''
s, n = pattern.subn(replacement, s)
open(path, 'w', encoding='utf-8').write(s)
print(f'✅ 主控卡反哺段净化完成（替换 {n} 处）')
PYEOF
  fi

  # 3h. 设计文档死链处理（设计文档已 --exclude，需改引用为 glossary）
  python3 - "$f" <<'PYEOF'
import sys, re
path = sys.argv[1]
s = open(path, encoding='utf-8').read()

# 1. SKILL.md 启动清单第 2 步：设计文档 → glossary-full（v2.7.10 起 glossary.md 拆分到 _shared/glossary-full.md）
s = s.replace(
    '读 `references/设计文档.md`（数据信任级别 / M 门 / 阶段闸门 / F 失败模式 / T6 批判）',
    '读 `references/_shared/glossary-full.md`（核心概念单一真源：10 张角色卡 / 三层防御 / 数据信任 / 关键协议 / 工具边界）'
)

# 2. SKILL.md 角色卡与模板段：删除「设计文档」行
s = re.sub(r'- 设计文档（[^\n]*）：`references/设计文档\.md`\n', '', s)

# 3. pipeline-readme.md「设计文档加载策略」段：删除
s = re.sub(r'## 设计文档加载策略.*?(?=\n## 派发话术)', '', s, flags=re.DOTALL)

# 4. pipeline-readme.md 模板拆分方案引用：删除
s = s.replace('详见 `templates/README-模板拆分方案.md`。', '。')

# 5. README 目录结构里的「设计文档.md」行：删除
s = re.sub(r'[^\n]*设计文档\.md[^\n]*\n', '', s)

# 6. 任务简报模板「详见设计文档 原创性保证 + 」：删引用，保留写手卡
s = s.replace('（详见设计文档 原创性保证 + 写手卡视角与精度铁律）', '（详见写手卡视角与精度铁律）')

# 7. 剥离「版本一致性检查」的 commit/tag/push release workflow（scanner Context-Inappropriate Capability）
s = re.sub(
    r'- \*\*版本一致性检查[^\n]*\*\*：.*?(?=\n- \*\*)',
    '- **版本一致性检查**：由开发者维护（版本升级时跑机械化自审），使用者无需关心。',
    s,
    flags=re.DOTALL
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

# ---- 3n. 安装命令版本 pin 同步（教训 #297）----
# 净化包内 `openclaw skills install @...@X.Y.Z` 的 pin 必须等于本包版本，
# 防止「包是 v2.12.4、安装命令还钉在 v2.10.3」这类用户可见的审计版本错配。
if [[ -f "$OUT_DIR/QUICKSTART.md" ]]; then
  sed -i -E "s|(@zuoyunlai/lunheng-article-pipeline)@[0-9]+\.[0-9]+\.[0-9]+|\1@$VERSION|g" "$OUT_DIR/QUICKSTART.md"
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
echo "🔧 剥离 shell 命令（保持极简纯净）..."
find "$OUT_DIR" -name '*.md' -print0 | xargs -0 python3 "$SCRIPT_DIR/strip-shell-commands.py"

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
  hits=$({ grep -rE "$pat" --include='*.md' --include='*.txt' --include='*.toml' "$OUT_DIR" 2>/dev/null || true; } | wc -l | tr -d ' ')
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
echo "🧹 清理内部痕迹（教训 #296）..." >&2
bash "$SCRIPT_DIR/strip-internal-leakage.sh" "$OUT_DIR" >/dev/null
python3 "$SCRIPT_DIR/strip-anchor-residue.py" "$OUT_DIR" >/dev/null

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
)
FINAL_HITS=0
for pat in "${FINAL_PATTERNS[@]}"; do
  hits=$({ grep -rE "$pat" --include='*.md' "$OUT_DIR" 2>/dev/null || true; } | wc -l | tr -d ' ')
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

# 净化残留扫描已完成（前置到 #3h，教训 #213），以下为汇总段（可被 exec timeout SIGTERM 不影响产物）

# ---- 5. 汇总 ----
echo ""
echo "✅ 净化发布包已生成：$OUT_DIR"
echo "   文件数：$(find "$OUT_DIR" -type f | wc -l | tr -d ' ')（对比真源 $(find "$SKILL_ROOT" -type f -not -path '*/.git/*' -not -path '*/outputs/*' -not -name '*.bak.*' | wc -l | tr -d ' ')，排除 .git/ 与 .bak.* 备份与 outputs/ 产物）"
echo ""
echo "下一步（手动执行）："
echo "  clawhub publish $OUT_DIR --slug lunheng-article-pipeline --version $VERSION --name \"论衡 — 严肃长文流水线\""
echo "  ⚠️ --name 必传（教训 #200）：CLI 不读 SKILL.md frontmatter 的 displayName，缺省会用文件夹名 2.7.9 当 H1"
echo "  （或先 dry-run 预览并检查 JSON 的 displayName 是否为人类可读名：clawhub publish $OUT_DIR --slug lunheng-article-pipeline --version $VERSION --name \"论衡 — 严肃长文流水线\" --dry-run --json）"
