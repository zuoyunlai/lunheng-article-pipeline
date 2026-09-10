> 版本：v2.12.10（自动同步 2026-09-10）
> 🌐 **语言政策**：产出语言默认中文，Phase 0 可改 English / 中英混 / 其他（写入任务简报「目标语言」字段，全流程以该字段为准）；中文特化（G14 中文 AI 痕迹检测 / GB/T 7714-2015 引用规范）是设计定位，不构成使用者语种限制。































































# 多格式导出（可选，默认 md）

> **原则**：主人不选就不加载导出逻辑，尽可能节省 token。
> **默认**：Phase 5 终稿输出 Markdown（当前行为，零额外 token）。
> **触发**：主人在 Phase 0 定题时或 Phase 5 终稿时选 `--format md/latex/docx/pdf`。
>
> ⚠️ **诚实声明（回应第三方审计）**：**md 是完整支持的**；latex/docx/pdf 三格式是**实验性功能**——命令模板引用的 4 个依赖文件（参考文献.bib / academic-paper 模板 / academic-paper-template.docx / chinese-gb7714-2015-numeric.csl）**论衡当前不自动产出**，需主人自备（见下方「前置条件清单」），且 **pandoc/rsvg-convert 由主人手动跑**（零 exec）。选 latex/docx/pdf 前请确认已满足前置条件，否则会卡壳。**.bib 自动生成机制计划 v2.6.0 落地**。

## 〇、前置条件清单（latex/docx/pdf 必读）

主人选 latex/docx/pdf 前，需自备以下依赖（论衡不自动产出）：

| 依赖 | 用途 | 论衡现状 | 主人自备方式 |
|------|------|---------|------------|
| `final/证据包/参考文献.bib` | pandoc 引文数据（BibTeX 格式） | ❌ 不产出（论衡产出 GB/T 7714 文本，无 .bib 转换机制） | 主人从 T1 文献卡手动转 BibTeX，或等 v2.6.0 |
| `academic-paper`（LaTeX 模板） | `--format latex` 排版 | ❌ 仓库无此文件 | 主人提供 .tex 模板 |
| `academic-paper-template.docx` | `--format docx` 排版 | ❌ 仓库无此文件 | 主人提供 reference-doc |
| `chinese-gb7714-2015-numeric.csl` | 中文 GB/T 7714 引用样式 | ❌ 仓库无此文件 | 主人从 Zotero CSL 仓库下载 |

## 一、format 参数

| 参数 | 输出格式 | 适用场景 | 主人操作 |
|------|---------|---------|---------|
| `--format md`（默认） | Markdown | 公众号 / 知乎 / 商业评论 / 通用 | 无需操作 |
| `--format latex` | LaTeX 学术模板 | 学术论文投稿（LaTeX 排版） | 主人选 + 自备模板/bib/csl + pandoc + LaTeX 引擎 |
| `--format docx` | Word 学术模板 | 学术论文投稿（Word 排版） | 主人选 + 自备 reference-doc/bib/csl + pandoc |
| `--format pdf` | Markdown → PDF（含 SVG 图表嵌入） | 终稿存档 / 打印 | 主人选 + 自备模板/bib/csl + pandoc + rsvg-convert + LaTeX 引擎 |

## 二、导出命令（pandoc 模板）

### `--format md`（默认）
无需额外命令，直接输出 `final/定稿.md`（当前行为）。

### `--format latex`
```bash
pandoc final/定稿.md -o final/定稿.tex \
  --template=academic-paper \
  --bibliography=final/证据包/参考文献.bib \
  --csl=chinese-gb7714-2015-numeric
```

### `--format docx`
```bash
pandoc final/定稿.md -o final/定稿.docx \
  --reference-doc=academic-paper-template.docx \
  --bibliography=final/证据包/参考文献.bib \
  --csl=chinese-gb7714-2015-numeric
```

### `--format pdf`
```bash
# 注意：pdf 导出需先做 SVG 图表嵌入（见下方 § 三），否则图表丢失/变占位框
pandoc final/定稿.md -o final/定稿.pdf \
  --pdf-engine=xelatex \
  --template=academic-paper \
  --bibliography=final/证据包/参考文献.bib \
  --csl=chinese-gb7714-2015-numeric
```

## 三、SVG 图表嵌入（PDF 关键）

`--format pdf` 必须先处理 SVG 图表嵌入，否则图表丢失或变占位框：

```bash
# 1. SVG 转 PDF（每张）
for svg in final/图件/*.svg; do
  rsvg-convert -f pdf "$svg" -o "${svg%.svg}.pdf"
done

# 2. Markdown 引用替换（[图N：标题] → ![图N：标题](图N_标题.pdf)）
# ⚠️ v2.5.16 修正：以下 sed 会**原地修改** final/定稿.md，是临时中间态。
# 跑完 pandoc 后**必须恢复**定稿.md（或先 cp 备份再跑），否则图位标注被替换后
# 定稿.md 被污染（图片 markdown 混入正文，M-Gate 图位检查会误判）。
cp final/定稿.md final/定稿.md.bak-pdf
sed -i 's|\[\(图[0-9]\)：\(.*\)\]|\![\1：\2](final/图件/\1_\2.pdf)|g' final/定稿.md

# 3. 跑 pandoc PDF
pandoc final/定稿.md -o final/定稿.pdf --pdf-engine=xelatex ...

# 4. 恢复定稿.md（关键！）
mv final/定稿.md.bak-pdf final/定稿.md
```

> **零外发原则**：SVG 转 PDF 用 rsvg-convert（本地工具，零外发），pandoc 本地跑。
> **⚠️ sed 破坏性警示**：SVG 嵌入的 sed 是**原地破坏**定稿.md 的临时操作，
> 必须 cp 备份 + 跑完恢复，否则交付的定稿.md 已被污染。

## 四、Phase 0 + Phase 5 选择流程

### Phase 0（定题，预选）
主控询问主人「本次任务是否需要多格式导出？」（预选，不阻塞）：
```
□ 是（请选格式：md / latex / docx / pdf / 全产 / 跳过）
□ 否（默认 md）→ 不加载导出逻辑，节省 token
```

### Phase 5（终稿，正式拍板，教训 #172）
**主控 T8 终检时必在对话里向主人主动呈现 6 选项**（不依赖 Phase 0 预选，主人不答 = 默认 md）：
```
- □ A. md（默认，零额外 token）— 公众号/知乎/小红书
- □ B. latex（学术论文投稿）— 需主人自备模板 + 手工跑 pandoc
- □ C. docx（学术论文投稿）— 需主人自备 reference-doc + 手工跑 pandoc
- □ D. pdf（终稿存档/打印）— 需主人自备模板 + 手工跑 pandoc + rsvg-convert
- □ E. 多格式全产（md + latex + docx + pdf 一起）
- □ F. 跳过（只要 md）
```
如主人选 B/C/D → T8 给出命令模板（§二），主人自备前置条件（§〇）后**手工跑 pandoc**；论衡 agent 不执行 shell。
如主人选 A/F → 仅输出 final/定稿.md。

## 四·四、表格样式约定（ECS 实战：16 格矩阵 docx 样式不可控）

- 正文表格统一 **pipe 表格**（`| |`），禁止 HTML 表格 / 嵌套表格（pandoc docx 兼容性）
- 单元格内禁用换行符（docx 转换即碎）；多值单元格用「；」分隔
- ≥8 列宽表（对比矩阵）→ T4 大纲阶段就拆为多子表（每表 ≤6 列），pandoc 参考模板 `academic-paper-template.docx` 预置 Table Grid 样式接管
- 表注写表下方普通段落（「表 N 注：」起头），不写在表格末行单元格内

## 四·五、导出前元数据清洗（ECS 实战：docx 残留 emoji 信任块）

**latex/docx/pdf 导出前必做**（md 默认格式跳过；清洗对象 = 定稿 export 副本，不动 run/ 原件）：
1. **信任级别 emoji 清洗**：🟢/🟡/🔴/⚠️ 删除或改正文括注——🟡 → `（数据为二手转引，须回溯原始来源）`；⚠️ → `（单方口径数据）`；🟢 直接删标记
2. **元信息自检块剥离**：字数自检表 / SHA256 校验行 / AI 痕迹 grep 计数表 / 心跳时间戳——这些是过程产物，不进交付稿
3. **清洗后核对**：清洗副本再过一遍 M-Form-7 白名单（操作员报告残留 = P0）；字数按清洗后版本重报（清洗删字后不得超过预算下限）

## 四·六、PDF 渲染验证（回应实测 #9：⚠️ 在 Noto Serif CJK 渲染成 △）

**触发**：主人选 `--format pdf` 并手工跑完 pandoc 后（零 exec，主人执行）。**目的**：抓字体 fallback 乱码（emoji 渲染成 △/豆腐块）与首页文本缺失。

```bash
# 1. 渲染抽页（前 5 页转 PNG，主人目视 or 主控 view_image 自查）
pdftoppm -r 100 -f 1 -l 5 final/定稿.pdf /tmp/lunheng-preview
# 2. 首页文本抽验（确认无乱码、章节标题完整）
pdftotext -f 1 -l 1 final/定稿.pdf - | head -40
```

**验证要点**：
- ⚠️ 等 emoji 若仍渲染成 △/□ → 交付文档内警示符号必须用 ▲（U+25B2 纯几何）或【警告】文本，不得用 ⚠️（来源侧已由 T5/主控模板约束；导出侧 §四·五 清洗兜底）
- 抽验结果主人确认后回填「渲染验证：✅」到交付说明；异常 → 定位是字体栈（模板 font-family 缺 emoji 字体）还是内容含 emoji（改 ▲/【警告】）

## 五、与字数判定表 / 投稿就绪检查表的关系

- 字数判定表：无论 format，所有格式都要过字数核验
- 投稿就绪检查表：Word/PDF 转换检查项在 v2.5.0 启用 `--format docx/pdf` 时激活

## 六、限制

- **零 exec**：pandoc / rsvg-convert 由主人在 host shell 手动跑；论衡 agent 不执行 shell 命令
- **模板依赖**：latex/docx/pdf 需主人自备模板（academic-paper.tex / academic-paper-template.docx）+ .bib + CSL（见 §〇 前置条件清单）
- **中文支持**：用 xelatex 引擎 + csl=chinese-gb7714-2015-numeric 处理中文引用
- **.bib 生成机制缺失**：论衡当前不产出 BibTeX，latex/docx/pdf 的 `--bibliography` 依赖主人手动转换；计划 v2.6.0 补 T1「文献卡 → .bib」自动生成
