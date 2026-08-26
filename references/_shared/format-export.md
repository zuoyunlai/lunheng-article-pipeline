> 版本：v2.5.19（自动同步 2026-08-26）
















# 多格式导出（v2.5.0 新增，可选，默认 md）

> **原则**：主人不选就不加载导出逻辑，尽可能节省 token。
> **默认**：Phase 5 终稿输出 Markdown（当前行为，零额外 token）。
> **触发**：主人在 Phase 0 定题时或 Phase 5 终稿时选 `--format md/latex/docx/pdf`。
>
> ⚠️ **诚实声明（v2.5.16 修订，回应第三方审计）**：**md 是完整支持的**；latex/docx/pdf 三格式是**实验性功能**——命令模板引用的 4 个依赖文件（参考文献.bib / academic-paper 模板 / academic-paper-template.docx / chinese-gb7714-2015-numeric.csl）**论衡当前不自动产出**，需主人自备（见下方「前置条件清单」），且 **pandoc/rsvg-convert 由主人手动跑**（零 exec）。选 latex/docx/pdf 前请确认已满足前置条件，否则会卡壳。**.bib 自动生成机制计划 v2.6.0 落地**。

## 〇、前置条件清单（latex/docx/pdf 必读，v2.5.16 新增）

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
> **⚠️ sed 破坏性警示（v2.5.16 补）**：SVG 嵌入的 sed 是**原地破坏**定稿.md 的临时操作，
> 必须 cp 备份 + 跑完恢复，否则交付的定稿.md 已被污染。

## 四、Phase 0 + Phase 5 选择流程（v2.5.16 同步 v2.5.5 六选项）

### Phase 0（定题，预选）
主控询问主人「本次任务是否需要多格式导出？」（预选，不阻塞）：
```
□ 是（请选格式：md / latex / docx / pdf / 全产 / 跳过）
□ 否（默认 md）→ 不加载导出逻辑，节省 token
```

### Phase 5（终稿，正式拍板，v2.5.5 教训 #172）
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

## 五、与字数判定表 / 投稿就绪检查表的关系

- 字数判定表（v2.4.6）：无论 format，所有格式都要过字数核验
- 投稿就绪检查表（v2.4.6）：Word/PDF 转换检查项在 v2.5.0 启用 `--format docx/pdf` 时激活

## 六、限制（v2.5.16 诚实化）

- **零 exec**：pandoc / rsvg-convert 由主人在 host shell 手动跑；论衡 agent 不执行 shell 命令
- **模板依赖**：latex/docx/pdf 需主人自备模板（academic-paper.tex / academic-paper-template.docx）+ .bib + CSL（见 §〇 前置条件清单）
- **中文支持**：用 xelatex 引擎 + csl=chinese-gb7714-2015-numeric 处理中文引用
- **.bib 生成机制缺失（v2.5.16 明示）**：论衡当前不产出 BibTeX，latex/docx/pdf 的 `--bibliography` 依赖主人手动转换；计划 v2.6.0 补 T1「文献卡 → .bib」自动生成
