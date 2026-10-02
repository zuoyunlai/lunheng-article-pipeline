> 版本：v2.15.7（自动同步 2026-10-02）

> 🌐 **语言政策**：产出语言由 Phase 0「目标语言」字段**显式选择**（中文 / English / 中英混 / 其他，**不设默认**），全流程以该字段为准；中文特化按**目标语言客观适用**——含中文时 **G14 中文 AI 痕迹闸必跑**（v2.12.40 起不再是可选项），纯外语时记 `n/a`（客观不适用，非「关闭」）；GB/T 7714-2015 引用规范为可选能力。二者均不构成使用者语种限制。

# 主人 host shell 补算与登记模板（交付物指纹）

> **用途**：`M-1` 交付物指纹绑定 / `M-13` 第 4 类「SHA256 校验和登记」的**唯一命令模板真源**。
> **边界（先读）**：论衡零 exec —— 本文件所有命令**由主人本人在 host shell 执行**，agent 在任何阶段都不执行。这与 `M-13` 硬约束同口径，不是建议而是红线。
> **历史沿革**：原「agent 自动写 `final/定稿.sha256`」路径自 v2.12.54 起**作废**（实测该产物曾因重定向写串而完全不可校验），校验和一律改为主人手动补算 + 回填登记。

## 一、为什么由主人执行

`final/定稿.sha256` 的作用是**证明下游四份只读档报告审的是同一份稿**（T7 审计 / G14 风格闸 / T9 同行评审 / T8 终检，见 M-8 集合相等断言）。若该指纹由 agent 自产自写，则「被审计对象」与「审计者声明」同源，锚点失去独立性。因此指纹的计算与落盘**必须落在流水线之外**。

## 二、补算命令（cwd = `run/<项目名>/`）

```bash
sha256sum final/定稿.md final/图件/*.svg > final/定稿.sha256
```

- 项目无图件（Phase 2.5 拍板 0 张）时改用单目标：
  ```bash
  sha256sum final/定稿.md > final/定稿.sha256
  ```
- `final/图件/*.svg` 用 shell 通配展开，**不含目录内非 SVG 文件**；若目录存在 PNG 等转换产物，逐个显式列出，不要用 `*` 兜底。
- 输出为标准两列格式（`<hash>  <path>`）。**禁止**只写路径、或把中间临时文件路径写进第一列——那会让整份指纹文件失去校验能力。

## 三、自验（补算后立即跑）

```bash
sha256sum -c final/定稿.sha256
```

逐行输出 `OK` 才算落盘正确。任一行 `FAILED` = 文件在补算后被改动（或路径写错）⇒ 重新补算，并把改动原因记入 `status.md`。

## 四、回填登记位置（四处，缺一即不合格）

> **P1-5 修复（2026-09-30）**：旧版要求 T7/G14/T9/T8 四份报告 `audited_artifact` 的
> sha256 **两两相等**——但 T7/G14 审的是 `drafts/current_draft.md`（phase_seq 12 / 16），
> T9/T8 审的是 `final/定稿.md`（phase_seq 20 / 22）。final_assembly 一旦做标题整理 /
> 图件嵌入 / 段落合并，二者 sha256 必然不等。**新版改判版本链链接**：T7/G14 与 T9/T8
> 的 audited_artifact 指向不同文件，但都登记到同一份「链式指纹」主链上；归档清单按
> 主链顺序比对即可（drafts/current_draft.md.sha256 → final/定稿.sha256）。

| 落点 | 字段 | 说明 |
|---|---|---|
| `final/定稿.sha256` | 两列输出本体 | 指纹真源，见 §二 |
| `final/交付说明.md` 头部 | `deliverables_fingerprint`（path / bytes / sha256） | 主人验收时比对用 |
| T7 / G14 报告头部 | `audited_artifact.{path, bytes, sha256}` | **path = `drafts/current_draft.md`**（phase_seq 12 / 16，定稿前） |
| **T9 / T8 报告头部** | `audited_artifact.{path, bytes, sha256}` | **path = `final/定稿.md`**（phase_seq 20 / 22，定稿后） |
| 链式指纹主链 | `artifact_chain: [drafts/current_draft.md, final/定稿.md]` | 顺序：草稿 → 终稿；二者 sha256 不要求相等，但都须登记 |
| 归档清单 | 校验和登记行（按 artifact_chain 顺序） | 见 [`project-archive-sop.md`](../治理/project-archive-sop.md) §二 |

**比较规则**：
- T7 vs G14：审同一份草稿 ⇒ sha256 必须相等（同一输入）；
- T9 vs T8：审同一份终稿 ⇒ sha256 必须相等（同一输入）；
- T7/G14 vs T9/T8：审不同文件 ⇒ sha256 **不要求相等**，但要求二者对应的真源
  （drafts/current_draft.md → final/定稿.md）能被 final_assembly 节点的输出链
  关系反查（详见 phase-order/phase-order.yaml 的 assembly 节点）。

`bytes` = **精确字节数属主人侧量值**（`wc -c` 可得；零 exec 下 agent 不可得）；`sha256` = 本文件 §二 命令输出值。二者均由**主人**在 host shell 补算后回填，未回填记 `unavailable`。

> **零 exec 边界（v2.12.64 定案，回应审计 S-1 / S-4）—— 本条即该口径的唯一真源，角色卡只留短指针**：agent 侧可确知的只有 `path` 与**文本度量**（`read` 可得：行数 / 字符数 / 首末行）。`sha256` / `bytes` 未经主人回填 ⇒ 判定档 = `pending_owner_verification`（**无法判定**）——**明文禁止判「通过」**（空值/占位符即通过 = fail-open），也不判不合格。

## 五、与既有文档的关系（一条款一真源）

| 需要什么 | 去哪读 |
|---|---|
| M-1 / M-8 / M-13 断言全文 | [`../agents/08-终检-final-inspector.md`](../../agents/08-终检-final-inspector.md) |
| 归档范围 / 目标路径 / 移动命令 | [`project-archive-sop.md`](../治理/project-archive-sop.md) |
| 格式转换（docx / pdf / latex）命令 | [`format-export.md`](format-export.md) |
| 图件 SVG → PNG 转换命令 | [`../templates/图表-SVG-template.md`](../../templates/图表-SVG-template.md) |
| 交付说明 / 报告头部的字段清单 | [`../templates/交接报告-template.md`](../../templates/交接报告-template.md) |

---

> **维护提示**：本文件是「主人操作类」模板的**汇聚点**。新增任何「终检后由主人手动执行」的动作时，命令写进本文件或对应专文后在 [`asset-index.md`](asset-index.md) 登记，**不要**在角色卡里重列命令（防口径漂移）。

## 七、数据指纹、引用闭环与字数一键复核（R-66）

> **执行者**：以下命令只由主人在 host shell 执行；论衡 agent 不执行、不模拟结果。用途是把 T7 报告中的硬数据点、正文引用闭环和纯中文字数，转为主人可复核的机械清单。

### 7.1 引用编号闭环

在项目根目录 `run/<项目名>/` 执行：

```bash
grep -oE '\[[DL][0-9]+\]' final/定稿.md | sort -u > /tmp/used.txt
grep -oE '^\[[DL][0-9]+\]' literature/文献卡.md data/数据卡.md | sort -u > /tmp/defined.txt
diff /tmp/used.txt /tmp/defined.txt
```

- `diff` 无输出才表示正文中使用的 `[Lxx]` / `[Dxx]` 编号与卡片定义集合一致；有输出时逐条回查，不得把空输出误报为「来源内容已核验」。
- 若项目没有某类卡片，主人应按实际项目目录调整命令并在复核清单中注明「该类未启用」。

### 7.2 纯中文字数

```bash
grep -oP '\\p{Han}' final/定稿.md | wc -l
```

该数值只统计正文中的纯中文字符；文末附录、参考文献等非正文部分应先按项目约定排除。将结果与任务简报目标区间及 [`字数判定表.md`](字数判定表.md) §二 对照，记录实际值、目标区间和判定，不由 agent 估算。

### 7.3 数据指纹复核清单

T7 应把正文每个 `[Dxx]` 硬数据点列入 `audits/主人复核清单.md`，至少包含：

| 编号 | 正文位置 | 数值 + 单位 | 统计量 / DOI | 来源年份 | 主人核对结果 |
|---|---|---|---|---|---|
| [Dxx] | §X.X / 段落首句 | <原文值> | <p 值 / 效应量 / DOI；无则 n/a> | YYYY | pending_owner_verification |

主人逐条对照一手来源后，将结果改为 `verified` / `mismatch`，并把差异或修正依据记入交付说明。未核验项目保持 `pending_owner_verification`，不得写成通过。

### 7.4 产出要求

T7 交接时同时交付 `audits/主人复核清单.md`；没有硬数据点时也要产出文件并写明 `no_hard_data_points: true`。该清单是主人侧核验台账，不替代 G1/G2/G17 的审计结论。

## 六、平台升级冒烟检查（v2.12.67，审计 P2-1）

> **背景**：`SKILL.md` frontmatter 的 `version` 置于 `metadata.openclaw` 下是**兼容性 workaround**（bundled 校验器拒顶层 `version`，官方文档未记载该子键语义）⇒ OpenClaw 升级可能改变校验/加载行为。**每次升级 OpenClaw 后**，维护者执行：

1. `python3 ~/.npm-global/lib/node_modules/openclaw/skills/skill-creator/scripts/quick_validate.py SKILL.md`（存在则跑；路径变了以 `npm root -g` 定位）——通过/失败都记录；
2. 重载本 skill 后目视确认版本头正常显示、角色卡可读（加载冒烟）；
3. 跑一次 `scripts/self-audit-gate.sh`（含门 T 官方校验段），全绿才算升级兼容。

> 本节属维护者操作（不随包消费面）；发现校验行为变化 ⇒ 按 v2.12.13 方案 3.6 的思路重新评估 frontmatter 结构并记教训。
