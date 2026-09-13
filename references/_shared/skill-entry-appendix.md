# SKILL.md 外移附录（入口文档瘦身用）

> **用途**：承载从 `SKILL.md` 外移的**长表格与平台参数**，使入口文档回到官方 10,000 字符上限内。
> **来源**：官方技能审计（2026-09-13）A1 —— `SKILL.md` 11,335 字符 > 官方 Workshop 上限 10,000 字符。
> **约束**：本文件内容与 `SKILL.md` 为**派生关系**；冲突时以本文件为准（`SKILL.md` 只留指针）。

---

## 一、spawn 参数约定（主控 spawn 子代理时必用）

> 平台参数，**非 frontmatter 键**——官方 skill frontmatter 无该键且拒顶层未知键。

| 参数 | 取值 | 说明 |
|---|---|---|
| `expectsCompletionMessage` | `true` | 需完成事件回传 |
| `context` | `"isolated"` | 叶子 worker（不带父上下文）|
| `cleanup` | `"keep"` | 保留子会话供调试（平台默认即 keep）|
| `cwd` | **绝对路径** `<workspace>/run/<项目名>/` | **必须绝对路径**，禁相对拼接（教训 #255）|
| `runTimeoutSeconds` | **按角色**（见 `SKILL.md` 硬卡阈值表）| 平台**机械**超时，与硬卡阈值同源 |
| `visible` | T5 / T7 → `true`；其余 → 默认（hidden）| 关键路径 dashboard 可见；并行检索员不刷屏 |

---

## 二、主控必读文档清单（🔴 必读全文 / 🟠 分片必读）

> **完整分层清单真源 = [`00-主控-扩展职责.md`](../agents/00-主控-扩展职责.md)「主控必读文档清单」段**。本表只留 🔴 / 🟠，🟡 按需分片项见真源。
> **表内路径均以仓库根为基准。**

| 层 | 文档 | 标记 |
|----|------|------|
| 0 | `references/agents/00-主控-coordinator.md`（核心职责全貌）| 🔴 |
| 1 | `SKILL.md`（入口）| 🔴 |
| 1 | `references/pipeline-readme.md`（入口）| 🔴 |
| 1 | `references/_shared/glossary-full.md`（入口）| 🔴 |
| 2 | `references/_shared/phase-order.yaml`（流程顺序与阻断关系**唯一真源**，冲突以 yaml 为准）| 🔴 |
| 2 | `references/_shared/M-Gate-Algorithm.md`（M-Form/M-Exist/M-Integrity 伪代码段**逐段必读**；「分片」只为省 token，**不表示跳读**）| 🟠 |

---

## 三、License

**MIT License** — Copyright (c) 2026 左运来 (zuoyunlai)。完整文本见 [`LICENSE`](../../LICENSE)；允许商业使用、修改、分发，需保留版权声明。受 MIT License 约束。

---

## 四、Phase 0 必走步骤 完整条文

1. 读 `references/pipeline-readme.md`（启动清单 / 模型配置 / 派发话术索引）+ [`glossary-full.md`](glossary-full.md)（核心概念单一真源；发布版无 `设计文档.md`）
2. **语言与受众确认**：先向主人确认目标语言（中文 / English / 中英混 / 其他，写入任务简报）；非中文使用者须在此步声明
3. **spawn 前必读对应派发话术**（`references/dispatch/` 10 个文件，spawn 哪角色读哪文件，勿凭记忆复制，教训 #268）。**含「能力自检」**：主控核验自身工具面是否超限；子代理 spawn 后首步自检回报 —— **工具面超限 = 警告级**（记录 + 披露 + 照样开工，**≠ 调用许可**）；**实际调用越权工具 = 阻断级**（停止 + 回报 `capability_excess`）。见 [`permissions.md`](../permissions.md)「能力自检」
4. **审计前必读 G 体系**：`references/agents/07-审计-auditor.md`（G0-G14 必查项 + M 门算法）
5. **文件修改安全流程**：**禁止 `sed -i`**（静默清空，教训 #265）——用 `edit` 精确 oldText 匹配；改前 `read` 后另存备份（`write` 到 `drafts/archive/`，语义等价 `cp`），改后验证
6. **硬卡阈值表**（左＝硬卡墙钟；右＝平台机械超时 `runTimeoutSeconds`，**同源不另立数**）：T1-T3 10 分钟/**600s** · T4 12 分钟/**720s** · T5 15 分钟/**900s** · T6 12-15 分钟/**900s** · T7 12-15 分钟/**720s** · T9/**600s** · G14 8 分钟/**480s** · **spawn watchdog 8 分钟**（spawn 后无产物兜底）

---

## 五、单源指针表低频行（SKILL.md 入口只留高频）

| 需要什么 | 去哪读 |
|---|---|
| 安全须知 / 外部服务声明 / 隐私与外发 | [`external-services.md`](external-services.md) |
| 字数分层 / 字数判定（单一口径：仅正文） | [`字数判定表.md`](字数判定表.md) |
| M 门算法（🟠 分片：伪代码必读 / 附录按需）| [`M-Gate-Algorithm.md`](M-Gate-Algorithm.md) + [附录](M-Gate-Algorithm-appendix.md) |
| 交付边界 / F1-F9 失败模式 / 阶段闸门 | [`deliverables.md`](../deliverables.md) |
| 模型 5 档候选池 + 运行手册 | [`model-assignment.md`](../model-assignment.md) / [`pipeline-readme.md`](../pipeline-readme.md) |
