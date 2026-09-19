> 版本：v2.12.61（自动同步 2026-09-19）

> 🌐 **语言政策**：产出语言由 Phase 0「目标语言」字段**显式选择**（中文 / English / 中英混 / 其他，**不设默认**），全流程以该字段为准；中文特化（G14 中文 AI 痕迹检测 / GB/T 7714-2015 引用规范）为**可选能力**，不构成使用者语种限制。

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

| 落点 | 字段 | 说明 |
|---|---|---|
| `final/定稿.sha256` | 两列输出本体 | 指纹真源，见 §二 |
| `final/交付说明.md` 头部 | `deliverables_fingerprint`（path / bytes / sha256） | 主人验收时比对用 |
| 四份只读档报告头部 | `audited_artifact.{path, bytes, sha256}` | T7 / G14 / T9 / T8 各一份，值必须两两相等（M-8） |
| 归档清单 | 校验和登记行 | 见 [`project-archive-sop.md`](project-archive-sop.md) §二 |

`bytes` = 主控 `read` 后填入的字节数；`sha256` = 本文件 §二 命令输出值。二者必须来自**同一次** `read` 与同一次补算——对象名与指纹同源是 M-1 的核心要求。

## 五、与既有文档的关系（一条款一真源）

| 需要什么 | 去哪读 |
|---|---|
| M-1 / M-8 / M-13 断言全文 | [`../agents/08-终检-final-inspector.md`](../agents/08-终检-final-inspector.md) |
| 归档范围 / 目标路径 / 移动命令 | [`project-archive-sop.md`](project-archive-sop.md) |
| 格式转换（docx / pdf / latex）命令 | [`format-export.md`](format-export.md) |
| 图件 SVG → PNG 转换命令 | [`../templates/图表-SVG-template.md`](../templates/图表-SVG-template.md) |
| 交付说明 / 报告头部的字段清单 | [`../templates/交接报告-template.md`](../templates/交接报告-template.md) |

---

> **维护提示**：本文件是「主人操作类」模板的**汇聚点**。新增任何「终检后由主人手动执行」的动作时，命令写进本文件或对应专文后在 [`asset-index.md`](asset-index.md) 登记，**不要**在角色卡里重列命令（防口径漂移）。
