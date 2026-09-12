> 版本：v2.12.33（自动同步 2026-09-12）

> 🌐 **语言政策**：产出语言默认中文，Phase 0 可改 English / 中英混 / 其他（写入任务简报「目标语言」字段，全流程以该字段为准）；中文特化（G14 中文 AI 痕迹检测 / GB/T 7714-2015 引用规范）是设计定位，不构成使用者语种限制。

# M 门算法规约（论衡当前主流程完整版）

> ⚠️ **先读这一句**：**本规约不是机器执行** —— 13 项 M 门是「**主控 LLM 推理模拟执行**」（零 shell、零 exec）。文内出现的历史叫法「M **机械化**硬门」是**旧名（已弃用）**、与实现不符；完整信任模型与各类错判率见下方「## ⚠️ 诚实声明：M 门 = LLM 推理判定，非机器强制」。**读到「机械化」三字时，以本节为准。**

> **渐进式执行模式（已合并入本文档）**：把 13 项 M 门从「T8 一次性全跑」改为「5 阶段分批执行 + T8 兜底」，P0 错误提前暴露（Phase 1.5 而非 T8），节省 30-50% 工作量。详见本文档 M-Form / M-Exist / M-Integrity 各阶段描述。
>
> **v2.2.8 Phase D-1 重大变更**：本规约从「**4 个增量版本并存**」合并为「**1 个完整版**」（本文件约 12K tokens，主流程只读这一份）。
>
> 完整版包含 v2.2.0 基础 + v2.2.1 扩展（M-Form-6 + M-Exist-3 + M-Integrity-1/2）+ v2.2.1.2 算法升级（M-Form-3 + M-Exist-1 + M-Form-6 + M-Exist-3 双格式）+ v2.2.4 内联引用 + 补检索回填 + 修订轮流程约束。**3 个历史版本已由维护者归档，不随发布包分发（仅做版本演进参考，不需主流程读取）**。
>
> **执行前置**：「同时读取 4 个版本」改为「**读取本完整版**」。节省 ~10K tokens 主流程加载。
>
> **章节级增量验证**：文件级变更检测升级为**章节级**——把 Markdown 按 `## ` 二级标题拆章节，识别「改了哪一章」而非「改了哪个文件」。修订轮（v2→v3）只改一章时，主控只需对该章节重跑引用类 M 门（M-Form-1/M-Exist-1/M-Form-6），未变更章节复用上轮结果。**定位**：章节级聚焦是**主控 LLM 的推理思路**（M 门本就是 LLM 推理，见下方诚实声明）——修订轮时先定位「哪些章节变了」，再只对这些章节重跑引用类 M 门，未变章节复用上轮结果，不必全文重跑。本地开发辅助脚本 `scripts/incremental_m_gate.py`（新增 `SectionChangeDetector`，用法 `python scripts/incremental_m_gate.py <项目目录> [--no-section-level]`）给主人手工复核变更范围用，**净化包剥离 scripts/，不依赖此脚本运行**。

---

## ⚠️ 诚实声明：M 门 = LLM 推理判定，非机器强制（教训 #177）

**重要**：本文档名称「M 机械化硬门」与实际实现存在**重要差别**——本节是信任模型的关键。

### 1. 实际执行机制

M 门 13 项伪代码是「**主控 LLM 推理模拟执行**」，不是真 shell 命令：

```
❌ 不是：主控跑 `grep -E "..." file.md | comm -23/-13` 等真 shell 命令
✅ 是：主控 LLM read 文件 → 推理模拟算法 → 输出 JSON 报告「✅ 通过」/「❌ 失败」
```

### 2. 信任模型（诚实的边界）

| 维度 | 信任度 | 说明 |
|------|--------|------|
| **M-Form（形式合规）** | **80-90%** | LLM 推理判定格式（编号/标签/章节结构），错判可能性低 |
| **M-Exist（存在性）** | **70-85%** | LLM 推理判定文件存在 + 编号对应，错判可能性中（特别是大文档） |
| **M-Integrity（阶段闸门）** | **85-95%** | LLM 推理判定主控 checkpoint，错判可能性低 |
| **sha256 完整性（M-Exist-2 修订）** | **默认不验** | 主人可选手工 `sha256sum` 后填回，论衡 LLM 不实际计算（zero exec 哲学） |

### 3. 已知漏洞（实战暴露）

- **LLM 自评自过** = 同一模型既写又审，**有偏的 LLM 可能给自己放行**。缓解：v2.3.11 引入「主控强制 wait 30s + 双重 ls」验证产物（#2 写盘后自检）。
- **大文档错判** = M-Exist-1 算法对大文档（20+ 文献卡）错判可能性上升。缓解：实战已分批跑。
- **跳过主人意图** = LLM 推理可能跳过主人未明示但需验证的细节（如「截至 YYYY 年」时效标注）。缓解：M-Gate-Report v2.2.12 JSON 主人可人工抽检。

### 4. 主人操作建议

- **关键项目**（投稿顶会 / 商业发布 / 学术出版）：M-Gate 报告 → **主人人工抽检** `final/M-Gate-Report-v2.2.12.json`
- **实战项目**（主人日常使用）：M-Gate 80-95% 信任度 = **足够**；不必每次都人工抽检
- **验证 vs 信任平衡**：LLM 推理 vs 主人人工 = 5-15 分钟 vs 1-2 小时，**实战不要过度依赖自动化**

### 5. 「机械化硬门」四字的修订

- **原表述**：「M 机械化硬门 = 论衡质量的兜底」
- **修订**（诚实化）：**「M 门 = LLM 结构化判定，非机器强制」**——「机械化」是设计意图（结构化/可复用），不是实际机制（真 shell 调用）

### 6. 替代方案

如主人需要真正机器强制校验，可选：
- **OpenClaw runtime 加 M-Gate 工具**（类似 OpenAlex 路径 B：MCP server）
- **主人手工跑 `bash scripts/m-gate-check.sh`**（从 M-Gate 伪代码派生 bash 脚本，但**不在论衡 agent 工具白名单内；发布版亦不含 `scripts/` 目录**）

---

## 📖 核心概念（优先阅读）

**执行 M 门前，请先阅读**：[`glossary-full.md`](glossary-full.md)（完整真源 ~21KB；子代理精简核心见 [`glossary-core.md`](glossary-core.md) ~2.5K）

词汇表第二章详细定义了 M 门的性质、覆盖范围、单一真源原则。本文档是算法实现细节，不重复概念定义。

---

## 执行模型

**M 门的执行方式**：
1. 主控用 `read` 工具读取本算法文档
2. 主控用 `read` 工具读取 `final/定稿.md` + `final/证据包/` 所有文件  
3. 主控按下面的**伪代码推理判定**，产出 `M-Gate-Report-v2.2.12.json`
4. **判定通过**才能返回，否则触发修订或补检索

**本文档中的代码示例**：
- **Python 风格** → 伪代码，描述算法逻辑（主控 LLM 推理执行）
- **Bash 风格** → 验证示例，供人类主人在 host shell 手动执行（非 agent 执行）

**工具能力边界**：详见 [glossary-full.md 第五章](glossary-full.md) + [工具能力边界.md](工具能力边界.md)

---

## 背景

论衡 agent 的工具白名单（`metadata.tools`）不含 `exec`，M 门由 LLM 推理执行，不引入新代码风险。

**设计哲学**：算法规约 100% 由论衡主控可读懂的伪代码构成，零 shell 依赖。

**借鉴出处**：vincentjiang06 paper-writer objective/verify gate 硬约束理念 + ARS M1-M7 失败模式组织。

**扩展**（教训 #271）：数据信任级别 + 阶段闸门 — vincentjiang06 paper-writer Trust Boundary + ARS Stage 2.5/4.5 论衡化。

**v2.2.1.2 升级**（教训 #272，+ #291 + #292 + #293）：4 个算法 bug 实战修正 + 数据卡双格式支持。

**升级**（AI安全隐患实战 + 深度长文定位）：内联引用模式分支 + 补检索回填校验 + 修订轮流程约束。

---

## 📦 分片加载策略（🟠 分片必读）

| 分片 | 内容 | 加载 |
|---|---|---|
| **必读**（本文件）| 执行模型 / M-Form 8 项 / M-Exist 3 项 / M-Integrity 2 项（规则 + 伪代码）| 🟠 跑 M 门前 + T8 终检前**必读** |
| **按需**（附录）| 输出格式（M-Gate-Report JSON schema）/ 论衡哲学化 / 教训沉淀 / 历史版本归档 | 🟡 按需 → [`M-Gate-Algorithm-appendix.md`](M-Gate-Algorithm-appendix.md) |

**理由**：主流程真正需要的是「13 项规则 + 触发条件 + 伪代码」；输出格式与版本沿革属按需。附录自 v2.5.4 起已独立成文件，本文件**不再要求通读全文**——主控按上表只读必读分片即可，读到 🟠 标记时按指定分片读，不为凑「完整性」把附录一并读入。


## 执行前置

**主控 T8 终检前必须**：

1. ✅ **分片读取本规约**（🟠 **分片必读**：用 `read` 工具读 `M-Gate-Algorithm.md` 的**执行模型 + M-Form 8 项 + M-Exist 3 项 + M-Integrity 2 项**规则与伪代码段；**附录段按需** → [`M-Gate-Algorithm-appendix.md`](M-Gate-Algorithm-appendix.md)，**不再需要读 4 个历史版本**）
2. ✅ **读取 final/定稿.md + final/证据包/所有文件**（用 `read` 工具）
3. ✅ **依次执行 M-Form 8 项 + M-Exist 3 项 + M-Integrity 2 项**（按本规约伪代码推理，含升级算法）
4. ✅ **产出 M-Gate-Report-v2.2.12.json**（用 `write` 工具写入）
5. ✅ **判定通过才允许 T8 返回**（注：本门为 **LLM 结构化判定**，非进程级返回码 —— 见顶部诚实声明），否则触发 T5 修订或主控补检索

**Phase 0 同意关卡**：本算法不调用任何外部服务（纯 LLM 推理 + 项目内文件 I/O），**不新增网络级外发**，因此不产生「额外」的网络级同意需求；但流水线整体仍受 Phase 0 同意关卡约束（文件清单 + 外部服务 4 选 1 已由主人在 Phase 0 确认），本算法在其授权范围内运行，不构成免同意通道。实战验证如需在宿主侧跑 dry-run 对比，由主人手工执行并明示同意（教训 #266，金标准）。

---

## M-Form 形式合规门（8 项）

### M-Form-1: 引用标注完整性

**伪代码**（主控 LLM 推理执行）：
```python
# 读取定稿全文 + final/图件/ 内 SVG
draft_text = read("final/定稿.md")
svg_texts = []
for svg_file in glob("final/图件/*.svg"):
    # 提取 SVG 文本节点：<text>…</text> / <desc>…</desc> / <title>…</title>
    svg_texts.append(read(svg_file))

# 提取所有引用标注（md 正文 + SVG 内嵌文本 视为事实层）
all_text = draft_text + "\n".join(svg_texts)
import re
references = re.findall(r'\[(?:D|C|C-主|L|先)\d+\]', all_text)
references_unique = sorted(set(references))

# 判定
if len(references_unique) > 0:
    return {"通过": True, "引用数": len(references_unique), "SVG 文本节点纳入": len(svg_texts)}
else:
    return {"通过": False, "失败原因": "正文 + SVG 内嵌文本均无任何引用标注"}
```

**关键扩展（教训 #184 实战）**：SVG 内的 `<text>` / `<desc>` / `<title>` / `<tspan>` 节点现视为事实层（M-Gate 核验覆盖），与正文 .md 同等待遇。这是为了防止「正文中正、SVG 中错」的双线不一致（SVG 残留 3 处」）。

**人类验证示例**（可选，主人手动复核用）：
```bash
# 在 host shell 执行
grep -oE '\[(D|C|L|先)\d+\]' final/定稿.md | sort -u | wc -l
for f in final/图件/*.svg; do grep -oE '\[(D|C|L|先)\d+\]' "$f" | sort -u; done | sort -u | wc -l
```

### M-Form-2: 文末四节存在性

**伪代码**（主控 LLM 推理执行）：
```python
# 读取定稿全文
draft_text = read("final/定稿.md")

# 检查四节
required_sections = [
    "## 数据来源",
    "## 案例来源", 
    "## 参考文献",
    "## 先行者文献"
]

missing = [s for s in required_sections if s not in draft_text]

if len(missing) == 0:
    return {"通过": True}
else:
    return {"通过": False, "缺失章节": missing}
```

### M-Form-3: 临时编号残留（教训 #272）

**v2.2.0 算法**（**有 bug**）：简单 grep 段落中 [L/D/Cxx] → 误判合规内联引用为「残留」。

**v2.2.1.2 新算法**：

**伪代码**（主控 LLM 推理执行）：
```python
# 读取定稿
draft_text = read("final/定稿.md")

# 辅助函数：提取正文部分（排除文末四节）
def extract_body(text):
    endnote_markers = ["## 数据来源", "## 案例来源", "## 参考文献", "## 先行者文献", "## 附"]
    for marker in endnote_markers:
        if marker in text:
            text = text.split(marker)[0]
    return text

# 辅助函数：提取文末部分
def extract_endnote(text):
    endnote_markers = ["## 数据来源", "## 案例来源", "## 参考文献", "## 先行者文献", "## 附"]
    parts = []
    for marker in endnote_markers:
        if marker in text:
            parts.append(text.split(marker)[1] if len(text.split(marker)) > 1 else "")
    return "\n".join(parts)

# 提取正文和文末的引用编号
import re
body_text = extract_body(draft_text)
endnote_text = extract_endnote(draft_text)

intext = sorted(set(re.findall(r'\[(L|D|C)\d+\]', body_text)))
endnote = sorted(set(re.findall(r'\[(L|D|C)\d+\]', endnote_text)))

# 计算真正残留（正文有但文末无）
orphan = sorted(set(intext) - set(endnote))

if len(orphan) == 0:
    return {"通过": True}
else:
    return {"通过": False, "残留编号": orphan}
```

**人类验证示例**（可选）：
```bash
# 提取正文编号（文末四节之前）
awk '/^## 数据来源|^## 案例来源|^## 参考文献|^## 先行者/{exit} {print}' final/定稿.md | \
  grep -oE '\[(L|D|C)\d+\]' | sort -u > /tmp/intext.txt

# 提取文末编号
awk '/^## 数据来源|^## 案例来源|^## 参考文献|^## 先行者/{flag=1} flag' final/定稿.md | \
  grep -oE '\[(L|D|C)\d+\]' | sort -u > /tmp/endnote.txt

# 计算差集
comm -23 /tmp/intext.txt /tmp/endnote.txt  # 正文有但文末无
```

**实战验证**：
- 实战 5（教师场域孤岛）：v2.2.0 算法 38 条命中（误判）→ v2.2.1.2 算法 0 命中（合规内联引用）✅
- 实战 4（品牌一致性）：v2.2.0 算法 14 条命中（误判）→ v2.2.1.2 算法 0 命中 ✅

### M-Form-4: 角色元数据泄露

**伪代码**（主控 LLM 推理执行）：
```python
# 读取定稿
draft_text = read("final/定稿.md")

# 元数据泄露检查词
metadata_leaks = [
    "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8",
    "交接报告", "七段", "论衡主控", "子代理", "反哺报告", "角色卡"
]

found = [word for word in metadata_leaks if word in draft_text]

if len(found) == 0:
    return {"通过": True}
else:
    return {"通过": False, "泄露词": found, "优先级": "P0"}
```

**注意**：M-Form-4 是 P0 优先级，角色元数据泄露 = 读者看到论衡内部代码 = 失去学术严肃性。

### M-Form-5: 过程语言残留

**伪代码**（主控 LLM 推理执行）：
```python
# 读取定稿
draft_text = read("final/定稿.md")

import re

# 过程语言检查
process_patterns = [
    r'v[0-9] 稿',
    r'初稿',
    r'草稿',
    r'修订说明',
    r'上一版',
    r'下一版'
]

found = []
for pattern in process_patterns:
    matches = re.findall(pattern, draft_text)
    if matches:
        found.extend(matches)

# 特殊检查："据行业经验估算" 必须有 [行业估算] 标记
estimate_uses = re.findall(r'据行业经验估算', draft_text)
for use in estimate_uses:
    # 检查上下文是否有 [行业估算] 标记
    context = get_paragraph_containing(draft_text, use)
    if "[行业估算" not in context:
        found.append("据行业经验估算（未标记）")

if len(found) == 0:
    return {"通过": True}
else:
    return {"通过": False, "残留词": found}
```

**注意**："据行业经验估算" 是 v2.1.1 引入的「合法估算标记」。段落开头标 `[行业估算，非数据卡]` → G6 论据类型自标（合法）；无标记直接用 → P1 残留。

> 📌 **数据卡路径口径（v2.12.28）**：M 门与 G 项一律读**源文件 `data/数据卡.md`**；`final/证据包/` 中是**交付副本，不得作判定依据**（副本可能滞后于源）。

evidence-pack-copy-note

### M-Form-6: 信任级别标注完整性（教训 #292 + #293）

**v2.2.1 算法**：仅支持标准 [Dxx] 格式。

**v2.2.1.2 新算法**（双格式支持）：

**伪代码**（主控 LLM 推理执行）：
```python
# 读取数据卡
data_card_text = read("data/数据卡.md")

import re

# 标准格式检查（[Dxx] 编号；兼容随包模板三种写法：`**[D01]` / `### [D01]` / 行首 `[D01]`）
d_entries_std = re.findall(r'^\s*(?:\*\*|#{2,4}\s*)?\[D\d+\]', data_card_text, re.MULTILINE)
# 信任级别：容忍加粗与 emoji 修饰（模板有 `信任级别：` 与 `**信任级别**: 🟢 已发布` 两种写法）
trust_std = re.findall(r'信任级别[^\n]{0,16}?(已发布|主人投喂|二手转引)', data_card_text)

# 表格 fallback 检查（1.x 表格格式）
d_entries_table = re.findall(r'^\| \d+\.\d+ \|', data_card_text, re.MULTILINE)
trust_table = re.findall(r'\|\s*(已发布|主人投喂|二手转引)\s*\|', data_card_text)

# 判定
std_pass = (len(d_entries_std) == len(trust_std))
table_pass = (len(d_entries_table) == len(trust_table))

if std_pass and table_pass:
    return {
        "通过": True,
        "标准格式": {"条目": len(d_entries_std), "信任级别": len(trust_std)},
        "表格格式": {"条目": len(d_entries_table), "信任级别": len(trust_table)}
    }
else:
    return {"通过": False, "详情": {"标准格式通过": std_pass, "表格格式通过": table_pass}}
```

**人类验证示例**（可选）：
```bash
# 标准格式
grep -cE '^\*\*\[D[0-9]+\]' data/数据卡.md  # 条目数
grep -c '信任级别：' data/数据卡.md  # 信任级别标注数

# 表格格式
grep -cE '^\| [0-9]+\.[0-9]+ \|' data/数据卡.md  # 表格行数
grep -cE '\|\s*(已发布|主人投喂|二手转引)\s*\|' data/数据卡.md  # 信任级别字段数
```

**实战验证**：
- 实战 5（教师场域孤岛）：标准格式 47 条 D + 0 信任级别 → 失败
- 实战 4（品牌一致性）：表格格式 35 行 + 0 信任级别 → v2.2.1.2 能识别为表格格式

### M-Form-7: 定稿文末节标题白名单纯净（教训 #139）

**背景**：v2.3.1 首次实战（ai-productivity-scene-dependence）定稿文末混入「图表清单」「引用规范（四节闭环）」「主控签字（T8 终检）」三段操作员报告内容，而「终检必查项①」只在文档层声明、未机械执行——T8 签字时自己签「✅ 交付边界纯净」但文末明明混着禁止项。**教训 #139：规范从文档层到执行层断链，签字走形式。**

**伪代码**（主控 LLM 推理执行）：
```python
# 读取定稿全文
draft_text = read("final/定稿.md")

import re

# 白名单 7 节（deliverables.md「定稿文末白名单」）
whitelist = ["参考文献", "数据来源", "案例来源", "先行者文献", "致谢", "AI 使用声明", "方法论附录"]  # v2.7.3 +方法论附录（可选，主人 Phase 5 勾选）；v2.12.32 +致谢（可发表性 F 选项启用时必含，否则与 F 判定表强制要求冲突）

def is_whitelisted(title):
    # 前缀匹配：容忍「数据来源（可信度标注）」这类带括号的变体
    return any(title == w or title.startswith(w) for w in whitelist)

# 提取所有二级标题（含行号）
lines = draft_text.split('\n')
sections = [(i, m.group(1)) for i, l in enumerate(lines)
            if (m := re.match(r'^##\s+(.+)$', l))]

# 找文末节起点（第一个白名单标题）
start_idx = next((idx for idx, (i, t) in enumerate(sections) if is_whitelisted(t)), None)

if start_idx is None:
    return {"通过": False, "优先级": "P0", "失败原因": "文末无任何白名单节（参考文献/数据来源/案例来源/先行者文献/致谢/AI 使用声明）"}

# 起点之后的所有 ## 标题必须在白名单内
violations = [t for (i, t) in sections[start_idx:] if not is_whitelisted(t)]

if len(violations) == 0:
    return {"通过": True}
else:
    return {"通过": False, "优先级": "P0", "违规节标题": violations,
            "失败原因": "文末混入操作员报告节（图表清单/主控签字/引用规范等），需移入 final/交付说明.md 或删除"}
```

**人类验证示例**（可选）：
```bash
# 从第一个白名单标题起，打印其后所有 ## 标题——白名单外任何输出 = 违规
awk '/^## (参考文献|数据来源|案例来源|先行者文献|致谢|AI 使用声明)/{flag=1} flag && /^## /{print}' final/定稿.md
```

**判定铁律**：M-Form-7 是 **P0 优先级**。文末混入操作员报告节 = 读者看到论衡内部代码 = 失去「论文是给读者的，报告是给主人的」边界。**T8 在 M-Form-7 exit 0 之前，禁止在签字块写「交付边界纯净」四个字**（教训 #139）。

> **v2.12.32 修正（回应实测 P1）**：旧白名单**缺「致谢」**，而可发表性 F 选项（默认启用）**强制要求** `## 致谢` ⇒ **致谢启用时必判 M-Form-7 违规**（两套判据互斥）。现已补入（亦同步至 `deliverables.md` 白名单表 + 下行 bash 例 + 失败原因文案）。

### M-Form-8: 三角验证覆盖率检查

**背景**：v2.3.7 论文三实战 §四 P4 一直缺 [Lxx]（L=0 D=22 C=3），直到 T7 fallback 审计才发现（v3→v4 加了 [L06] [L12]）。**毛在才不出现**——主控「三角验证把关」职责未机制化，写手 v1 落地前没自动跑 [Lxx]+[Dxx]+[Cxx] 三维 grep。

**三角验证原理**（论衡核心机制）：任何论点必须能映射到文献卡[Lxx]+数据卡[Dxx]+案例卡[Cxx]（涉企业行为/事件者必须配案例卡，至少两项齐全）。检索不到就标缺口，严禁编造。主角控「三角验证把关」职责（2026-08-13 原创性保证增）原本是主控手动检查，v2.3.7 P1-4 升级为**写手 v1 落地前的 M 门规则化必查**。

**伪代码**（主控 LLM 推理执行，写手 **v1 落盘后、T7 前**跑）：
```python
import re

# 读取任务简报 + 初稿
brief = read("01-任务简报.md")
draft_text = read("drafts/初稿-v1.md")

# 提取任务简报 §四「核心论点」清单（如 [论点N] 格式）
# 如任务简报未明确标论点，以 §三 研究问题作为论点提取依据
claim_pattern = re.findall(r'\[论点\d+\]|第[一二三四五六七八九十]+章', brief)
claims = [c.strip() for c in claim_pattern]

# 从初稿提取所有引用编号（4 类）
l_refs = re.findall(r'\[L\d+\]', draft_text)
d_refs = re.findall(r'\[(?:D-?基?-?\w*-?\d+)\]', draft_text)
c_refs = re.findall(r'\[C\d+\]', draft_text)

# 对每个论点检查三角验证：拆初稿为按论点的段落（按章节切分）
sections = re.split(r'^## ', draft_text, flags=re.MULTILINE)

violations = []
for claim in claims:
    # 找包含该论点的章节
    section_for_claim = next((s for s in sections if claim in s), "")
    # 检查三角验证覆盖率
    has_l = bool(re.search(r'\[L\d+\]', section_for_claim))
    has_d = bool(re.search(r'\[(?:D-?基?-?\w*-?\d+)\]', section_for_claim))
    has_c = bool(re.search(r'\[C\d+\]', section_for_claim))
    # 三角验证：至少 2 项齐全（不必须 3 项）
    coverage = sum([has_l, has_d, has_c])
    if coverage < 2:
        violations.append({
            "claim": claim,
            "section": section_for_claim[:50],
            "has_L": has_l,
            "has_D": has_d,
            "has_C": has_c,
            "coverage": f"{coverage}/3"
        })

if len(violations) == 0:
    return {"通过": True, "论点数": len(claims)}
else:
    return {"通过": False, "优先级": "P0",
            "未复核论点数": len(violations),
            "违规详情": violations,
            "失败原因": "写手 v1 未补齐三角验证覆盖（<2 类引用），需补检索或降级为「观点」"}
```

**触发时机**：
1. **写手 v1 落地后**（v1 写手产物已落盘）→ T4 分析员或主控跑 M-Form-8 预检 → 不通过 → 打回 v2 重写（计入修订轮）
2. **T7 审计员**跑最终审计时也跑 M-Form-8 → 不通过 → 打回（计入修订轮）

**实战背景**：§四 P4 [论点4] 一直缺 [Lxx]（L=0 D=22 C=3）直到 T7 fallback 审计才发现 → v3→v4 加了 [L06] [L12] 修补 → 浪费 1 轮修订。v2.3.7 升级后 M-Form-8 在 v1 落地时拦截，不再依赖 T7 兜底。

**人类验证示例**（可选）：
```bash
# 提取每个章节的引用类型分布
awk '/^## /{section=$0; next} /\[L[0-9]+\]/{l++} /\[D[0-9]+\]/{d++} /\[C[0-9]+\]/{c++} END{print section, "L="l, "D="d, "C="c}' drafts/初稿-v1.md
```

---

## M-Exist 存在性合规门（3 项）

### M-Exist-1: 文末四节双向 diff

**v2.2.0 算法**（**有 bug**）：awk 严格匹配 4 个标准文末节 → 对「## 附」段误判。

**v2.2.1.2 升级算法**（教训 #291）+ **v2.2.4 内联引用 + 补检索回填分支**：

```
算法步骤：
1. 判断引用格式：读 01-任务简报.md「引用格式」字段
   - 「内联（机构，年份）」或「公众号/商业评论/行业分析」 → 走内联模式分支
   - 「[Lxx]/[Dxx] 编号」或「期刊/学术」 → 走标准 diff

2A. 标准模式：
   ① 提取正文 [Dxx]/[Cxx]/[Lxx]/[先xx]（不在文末任意节内）→ set_intext
   ② 提取文末任意节（标准 ## 数据来源 + ## 案例来源 + ## 参考文献 + ## 先行者文献 + 非标准 ## 附 等 + 文末最后 1/3 段 fallback）的所有引用编号 → set_endnote
   ③ 计算双向 diff：comm -23 set_intext set_endnote = 漏引；comm -13 set_intext set_endnote = 孤儿
   ④ 判定：漏引空 + 孤儿空 → 通过

2B. 内联模式：
   ① 提取正文内联引用（机构，年份）：grep -oE '（[^（）]*[0-9]{4}[^（）]*）' | sort -u
   ② 5 项依赖编号的检查必须改为「可回溯性」检查：
      - M-Exist-1：每条内联引用能否在文末四节+证据包找到对应条目
      - G2 数据溯源：每个正文数字能否在数据卡/文献卡找到来源（防无主数据）
      - M-Exist-3：引用机构的信任级别在数据卡/案例卡有标注
      - G4-2 四节 diff：正文引用的机构/数据/案例在文末四节有对应
   ③ 判定：全部内联引用可回溯 + 所有数字有源 + 信任级别齐全 → 通过；任一不可回溯 → P1

伪代码（标准模式）：
intext = extract_intext_v2(draft_text)
endnote = extract_endnote_v2(draft_text, standard=True, non_standard=True, last_third=True)
leaked = sorted(set(intext) - set(endnote))
orphan = sorted(set(endnote) - set(intext))
return (len(leaked) == 0 and len(orphan) == 0, leaked, orphan)
```

**补检索回填校验分支**（当流水线发生过补检索时触发）：

```
1. 判断是否发生补检索：检查 run/<项目名>/literature/ 是否有「补检索-*.md」文件

2. 回填校验（教训 P1-2：不可用「L总数==清单条目数」判定）：
   ⚠️ 反例警示—— **不要用** 等式判定「L总数==文末清单条目数」。
   文末参考文献清单可包含**非 L 文献**（法规[S]/报告[R]/标准/数据库[DB/OL]/网站等），
   如 GAO/EU AI Act/中国办法/OECD/Stanford HAI/AIID，等式在实战中「23==23」可能只是巧合（不同来源凑出同样数字）。
   审核工具误读为「L23==ref23 PASS」，**这是反例不是示例**。

   正确判定法：
   ① 提取补检索新增 L 编号（文献卡中「补检索」段标记）
   ② 对**每个**补检索 L，**人工逐条**检查文末参考文献清单是否有对应条目（按作者/标题/期刊匹配）
   ③ 判定：每个补检索 L 都在文末清单有对应条目 → 通过；任一缺 → P1
```

**实战验证**：
- 实战 4（品牌一致性-发布稿）：v2.2.0 算法误判 14 条漏引 → v2.2.1.2 算法 0 漏引 0 孤儿（## 附 段被识别）✅
- 实战 AI安全隐患：v2.2.1.2 标准 diff 在内联引用模式下空转 → v2.2.4 内联模式分支覆盖 24 条引用 ✅

### M-Exist-2: 证据包完整性校验（原「证据包文件完整性 sha256」，教训 #169）

**重写原因**：
- 原「M-Exist-2 证据包文件完整性 sha256」设计是「理想」但**实战中 sha256 字段永远占位**（主人不手动跑 `sha256sum`）
- 论衡「零 exec 哲学」= LLM 不能跑 sha256 实际计算（仅可读文件验证非空）
- 实战中占位符 `[SHA256-PENDING:HOST-VERIFY]` 永远不会被回填 = 字段形同虚设
- v2.5.5 重命名为「证据包完整性校验」，判定项从「sha256 匹配」改为「文件存在性 + 字节数 + 章节结构」（LLM 推理实际能判定）

```
算法步骤：
1. 读取 final/证据包/ 目录下所有 .md 文件
2. **LLM 推理判定 5 项**（不是 sha256）：
   - ✅ 文件存在性：所有证据文件存在
   - ✅ 文件非空：字节数 > 1000（小文件例外如 先行者清单 可能 <1000）
   - ✅ 文件时间戳：在实战项目时间窗内（本次项目启动后 ~结束前）
   - ✅ 章节结构：文件含「## 基本信息」「## 条目列表」或类似必备段
   - ✅ 数据卡格式：JSON/YAML 校验或文本格式规范（数据卡含「[Dxx]」编号 + 信任级别字段）
3. **判定**：
   - （a）5 项全过 → **P5 ✅ 通过**
   - （b）部分项过但缺失具体证据 → **P5 ⚠️ 部分通过**（标黄提示主人补）
   - （c）文件缺失或全空 → **P5 ❌ 失败**（主控未生成证据 = 真错误）
4. **人类主人补填 sha256 可选**：
   - 主人如需更严验证，在 host shell 跑 `sha256sum final/证据包/*.md` 后追加到 final/交付说明.md
   - 实战中**几乎没人补**，但保留为「理论严格性」项
5. **本文档中所有 sha256 示例**：是「跨平台命令参考」，**不是 agent 执行的代码**。
```

**跨平台等价命令**（教训 #107）——**仅人类主人使用，不是论衡 agent 调用**：

| 平台 | 命令 |
|------|------|
| **Linux/macOS** | `sha256sum file.md` |
| **Windows PowerShell** | `Get-FileHash -Algorithm SHA256 file.md` |
| **Windows CMD** | `certutil -hashfile file.md SHA256` |
| **Python（任意平台）** | `hashlib.sha256(open(file,'rb').read()).hexdigest()` |

**能力边界澄清**：
- 论衡 agent **不能** 直接计算 sha256（不在工具白名单内）
- 主控 LLM 能用 `read` 读全文做「文件非空/章节结构/数据卡格式」验证（**这是 LLM 推理，不是 sha256**）
- 真正 sha256 由人类主人在 host shell **手动计算后回填**到「证据包指纹」段
- 本算法的「exit code」判定仅指「5 项 LLM 推理判定通过」，不包括 sha256 完整性验证（sha256 是人类补填项）

**实战背景**：原 M-Exist-2 sha256 字段永远占位，浪费交付说明.md 文档版面。重命名为「证据包完整性校验」后，字段实际可用（LLM 能判定）。
```

### M-Exist-3: 数据信任级别一致性 diff

**关键扩展（教训 #184 实战）**：SVG 文本节点（`text`/`desc`/`title`/`tspan`）现视为事实层，内嵌的 `[Dxx]` / `[Cxx]` 信任级别与 md 正文同等 diff。防“正文修了 SVG 没修”双线不一致。

**v2.2.1 算法**：grep -oE '\[D[0-9]+\]' final/定稿.md → **不支持表格行 [1.x] 引用**。

**v2.2.1.2 新算法**（双格式支持）：

```
算法步骤：
1. 正文引用提取：
   - 标准格式 [Dxx]：grep -oE '\[D[0-9]+\]' final/定稿.md → set_intext_d
   - 表格格式 [1.x]：grep -oE '\[1\.[0-9]+|\[2\.[0-9]+' final/定稿.md → set_intext_table
   - **扩展**：SVG 内嵌文本纳入（final/图件/*.svg 的 text/desc/title/tspan 节点）→ set_svg_d

2. 数据卡条目提取：
   - 标准格式 [Dxx]：grep -oE '^\*\*\[D[0-9]+\]' data/数据卡.md → set_card_d
   - 表格格式 [1.x]：grep -oE '^\| ([0-9]+\.[0-9]+) |' data/数据卡.md → set_card_table

3. 信任级别一致性 diff：
   - 标准格式 diff：comm -23/-13 set_intext_d set_card_d
   - 表格格式 diff：comm -23/-13 set_intext_table set_card_table
   - SVG 格式 diff：comm -23/-13 set_svg_d set_card_d

4. 信任级别空标检查：
   - 标准格式：每条 [Dxx] 对应数据卡信任级别非空
   - 表格格式：每行 [1.x] 表格的「信任级别」列非空

5. 判定：所有 diff 空 + 信任级别全填 → 通过；任一非空 → 失败

伪代码：
# 扩展：SVG 内嵌文本节点视为事实层，纳入 [Dxx] / [Cxx] 提取与 diff
draft_text = read("final/定稿.md")
svg_text = extract_text_nodes("final/图件/*.svg")  # text/desc/title/tspan 节点合并
all_text = draft_text + "\n" + svg_text
intext_d = sorted(set(re.findall(r'\[D\d+\]', all_text)))
intext_table = sorted(set(re.findall(r'\[\d+\.\d+\]', draft_text)))  # 表格格式仅在正文，SVG 不支持
card_d = sorted(set(re.findall(r'^\*\*\[D\d+\]', data_card_text, re.MULTILINE)))
card_table = sorted(set(re.findall(r'^\| (\d+\.\d+) \|', data_card_text, re.MULTILINE)))
trust_d = extract_trust_dict_standard(data_card_text)
trust_table = extract_trust_dict_table(data_card_text)
leaked = sorted(set(intext_d) - set(card_d))
orphan = sorted(set(card_d) - set(intext_d))
missing_trust = [d for d in intext_d if d not in trust_d or trust_d[d] == '']
all_pass = (len(leaked) == 0 and len(orphan) == 0 and len(missing_trust) == 0)
return (all_pass, leaked, orphan, missing_trust)
```

---

## M-Integrity 阶段闸门（2 项，含修订轮流程约束）

### M-Integrity-1: T2.5 完整性门（T2 数据检索 → T4 分析前）

> **重要修正**：原版逻辑矛盾 — M-Integrity-1 在 T2→T4 之间，大纲（T4 产物）尚不存在却需查「数据条目数 ≥ 大纲 D 列数」。修正为查任务简报（Phase 0 已产物化）子问题的数据需求数。

```
算法步骤（主控 LLM 兜底执行）：
1. 检查数据卡文件存在：ls data/数据卡.md → 必须存在
2. 提取数据条目数（双格式）：
   标准 [Dxx] 计数：grep -cE '^\*\*\[D[0-9]+\]' data/数据卡.md
   表格 [1.x] 计数：grep -cE '^\| [0-9]+\.[0-9]+ \|' data/数据卡.md
   两者取并集 dedupe
3. **修正**：提取任务简报子问题数据需求数
   从 01-任务简报.md 「研究问题」段读取每个子问题的「需找数据点 ≥N」
   需求总数 = Σ 子问题数据需求数
   （不再 grep analysis/分析大纲.md，因 T4 尚未产出）
4. 数据条目数 >= 任务简报需求总数 → 数据完整 → 通过；否则 → 触发 T2 重检索
5. 信任级别完整性：M-Form-6 **判定通过** → 通过；否则 → 触发 T2 补标注
6. 信任级别一致性：M-Exist-3 **判定通过** → 通过；否则 → 触发 T2 补数据卡
7. **修复（教训 #123）**：sha256 指纹为**可选验证**——主控发占位符 `[SHA256-PENDING:HOST-VERIFY]` 到 `final/交付说明.md`「证据包指纹」段，**不**作为闸门强制项。主人如需真实哈希，由**主人本人**在宿主 shell 手动计算后回填（参考 M-Exist-1 的证据包完整性比对规则）。**该步骤不是 agent 执行的代码，是人类验证示例。**
8. **新增（教训 #106）**：数据卡头部「共 N 条」声明 vs 实际 grep 计数一致性
   头部声明：grep -oE '共 [0-9]+ 条' data/数据卡.md
   实际计数：步骤 2 的双格式并集 dedupe
   不一致 → 标 Failed（防 T2 未自检 + T4 人工 grep 才发现的延后问题）
9. 判定：全部判定通过（项数以伪代码为准） → T2.5 ✅ 派发 T4；任一失败 → T2.5 ❌ 不派发 T4
   **删「主人签字 Phase 1」（教训 #136）**：T2.5 是**机械检查点**（LLM 结构化判定，非机器强制），主人签字只在 Phase 0（4 选 1 同意关卡）/ Phase 2.5（大纲确认）/ Phase 5（终稿）三节点；检索完成→T4 之间**不应**打断主人

伪代码：
data_card = 'data/数据卡.md'
data_count = count_d_entries(data_card)
outline_count = count_data_requirements_in_brief('01-任务简报.md')  # v2.2.17 显式标注：读任务简报，不读分析大纲
data_ok = data_count >= outline_count
trust_form_ok = check_M_Form_6(data_card)
trust_exist_ok = check_M_Exist_3(data_card, 'final/定稿.md')
sha256_pending = emit_placeholder_sha256(data_card)  # v2.2.17：发占位符 [SHA256-PENDING:HOST-VERIFY]，**不**作为闸门强制项
header_consistent = check_header_vs_actual_count(data_card)  # v2.2.10 新增
all_pass = data_ok and trust_form_ok and trust_exist_ok and header_consistent  # v2.3.2 删 owner_signed（主人签字不在 T2.5 闸门，教训 #136）
# 修复 F03 + F05：sha256 不是“必填门”，是“可选验证”（主人手动跑）
return (all_pass, fail_reasons, sha256_pending)
```

**实战反例**（教训 #106）：T2 写数据卡时凭印象在头部写「共 29 条」，实际 grep 只有 26 条，T4 靠人工 grep 才发现。本次新增步骤 9 拦截。
```

### M-Integrity-2: T7.5 完整性门（T8 审计 → T8 终检前）

```
算法步骤（主控 LLM 兜底执行）：
1. 检查审计报告最新版：ls audits/审计报告-vN.md → N 取最大 → 必须存在
2. P0/P1 清单已**显式列出**：读 audits/审计报告-vN.md → **P0/P1 条目数可为 0**（审计零缺陷是正常结果，不是失败）；**但必须显式写「本轮无 P0/P1」**，不得留空或以未列示代替；出现 P0/P1 条目时须逐条列明。
3. M 门（M-Form 8 项 + M-Exist 3 项）**全部判定通过**：读**当前轮已产出**的章节级 M 门记录 + `status.md`「7.三.五 M 门执行记录表」→ 全部 true（**不得依赖 `final/M-Gate-Report-v2.2.12.json`**：该文件由 T8 终检产出，而 T7.5 在 T8 **之前**执行 —— 前后依赖倒置会使门必然判失败或被迫推断，2026-09-12 审计 P1-6）
4. 证据包 sha256 指纹段存在：读 final/交付说明.md「证据包指纹」段 → 必须有 sha256 **占位符** `[SHA256-PENDING:HOST-VERIFY]`（人类可选在 host shell 手动计算后回填真实哈希，占位符即视为通过——agent 不执行 sha256，不把 sha256 作闸门强制项）
5. 信任级别一致性：M-Exist-3 exit 0 → 通过
6. 论文交付物 vs 操作员报告独立隔离：
   - final/定稿.md（论文）不含 audits/ / final/交付说明.md 内容
   - final/交付说明.md / audits/（报告）不混入 final/定稿.md
7. **删「主人签字 Phase 5」（教训 #138）**：T7.5 是**机械检查点**（LLM 结构化判定，非机器强制）（T7 审计 → T8 终检），主人签字在 Phase 5（T8 终检交付后主人验收），**不在** T7.5 闸门里；原「如有修订回环 ≤2 轮降级触发则主人读局限性.md」逻辑，改为 T8 终检交付时一并请主人验收（含局限性声明）
8. **修订轮流程约束**：检查本轮修订是否由独立写手子代理执行
   - 证据：status.md 修订回环记录写明「spawn 独立写手 vN 执行」
   - 若发现主控代执行 → 打回修订轮，强制 spawn 独立写手
   - 例外：主控直接 edit 定点修复（<5 处纯校对类）不视为违反
9. 判定：1-6 + 8 项全通过（步骤 7 为「删主人签字」元说明，非检查项）→ T7.5 ✅ 派发 T8；任一失败 → T7.5 ❌ 不派发 T8

伪代码：
audit_latest = get_latest_audit_report('audits/')
p0_p1_listed = check_p0_p1_listed(audit_latest)
m_gate_ok = check_m_gate_all_pass_current_round()  # 读**本轮已产出**的章节级 M 门记录 + status.md「7.三.五 M 门执行记录表」；**不得读** final/M-Gate-Report-v2.2.12.json（T8 产物，T7.5 时尚未生成 —— 2026-09-12 审计 P1-6）
sha256_ok = check_evidence_sha256_placeholder('final/交付说明.md')  # v2.2.17 改：占位符 [SHA256-PENDING:HOST-VERIFY] 即通过，人类可选回填
trust_ok = check_M_Exist_3(...)
isolation_ok = check_draft_vs_report_isolation('final/定稿.md', 'final/交付说明.md', 'audits/')
revision_independent = check_revision_by_independent_writer('status.md')
all_pass = audit_latest and p0_p1_listed and m_gate_ok and sha256_ok and trust_ok and isolation_ok and revision_independent  # v2.3.3 删 owner_signed（主人签字在 Phase 5，不在 T7.5 闸门，教训 #138）
return (all_pass, fail_reasons)
```

---

## 附录（按需加载，不计入主流程必读）

以下 4 段（输出格式 / 论衡哲学化 / 教训沉淀 / 历史版本）已抽出到独立文档，按需加载：

- **M-Gate-Report v2.2.4 输出格式**（JSON schema）：[`references/_shared/M-Gate-Algorithm-appendix.md §1`](M-Gate-Algorithm-appendix.md)
- **论衡哲学化**（4 版本合并）：[`references/_shared/M-Gate-Algorithm-appendix.md §2`](M-Gate-Algorithm-appendix.md)
- **教训沉淀**：[`references/_shared/M-Gate-Algorithm-appendix.md §3`](M-Gate-Algorithm-appendix.md)
- **历史版本归档**：3 个历史版本（基础版 / 增量版 / 算法升级版）已由维护者归档，不随发布包分发。**主流程只读本完整版**，归档版仅做版本演进参考。

> **拆分理由（历史记录）**：**当时**主文件从 780 行降至 635 行（-19%），超 PERF-SIZE-004 800 行临界 145 行；**此后随修订增长，当前行数以文件实际为准**（不在文中硬编码行数）的缓冲。附录按需加载，主流程只读「13 个 M门规则 + 触发条件 + 伪代码」。