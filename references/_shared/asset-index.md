> 版本：v2.12.24（自动同步 2026-09-11）

> 🌐 **语言政策**：产出语言默认中文，Phase 0 可改 English / 中英混 / 其他（写入任务简报「目标语言」字段，全流程以该字段为准）；中文特化（G14 中文 AI 痕迹检测 / GB/T 7714-2015 引用规范）是设计定位，不构成使用者语种限制。

# 资产与文档索引（角色卡 / 模板 / 项目目录 / 核心文档）

> **本文件是 SKILL.md「项目目录结构 + 角色卡与模板」「核心文档索引」两段的外移正文**（按需加载：主控需要定位资产或查「某文档在哪个时机读」时才读）。

## 项目目录结构 + 角色卡与模板

**项目目录**（`run/<项目名>/`）：

```
├── 01-任务简报.md       # Phase 0
├── status.md            # 状态机（Inbox→Assigned→In Progress→Review→Done|Failed）
├── literature/文献卡.md # T1: [L01]...
├── data/数据卡.md       # T2: [D01]... 含来源机构+年份+URL+时效🟢🟡🔴
├── cases/案例卡.md      # T3: [C01]... 多方说法+≥2 来源
├── analysis/分析大纲.md # T4: 论点-论据映射 + 反方规划
├── analysis/批判报告-vN.md # T6: C1-C7 七维批判
├── drafts/初稿-vN.md + 修订说明-vN.md # T5 + 修订稿
├── audits/审计报告-vN.md# T7: P0/P1/P2
├── final/定稿.md + final/图件/ + final/证据包/ + final/交付说明.md # Phase 5
```

**角色卡**（10 张，主控 + 9 子代理）：`references/agents/`（T8 终检有独立角色卡 `08-终检-final-inspector.md`，由主控亲完成不 spawn）
**角色速查**（10 张角色卡，`references/agents/`；T8 由主控亲完成不 spawn）：

| 角色 | 职责 | 产出 |
|---|---|---|
| **T1** 文献检索 | 并行检索已发布文献 | `literature/文献卡.md` |
| **T2** 数据检索 | 并行检索数据（含时效 🟢🟡🔴） | `data/数据卡.md` |
| **T3** 案例检索 | 并行检索案例（任何量级必 spawn，0 条出空卡） | `cases/案例卡.md` |
| **T4** 分析 | 论点-论据映射 + 反方规划 + 三角验证 | `analysis/分析大纲.md` |
| **T5** 写作 | 初稿 + 修订（引用标 [Lxx]、数字标 [Dxx]、案例标 [Cxx]） | `drafts/初稿-vN.md` |
| **T6** 批判 | C1-C7 七维批判（攻击 v2 不是 v1） | `analysis/批判报告-vN.md` |
| **T7** 审计 | G0-G14 独立审计（只审不改） | `audits/审计报告-vN.md` |
| **T8** 终检 | 可发表性 48 项终检（主控亲完成，不 spawn） | `final/定稿.md` + 交付说明 |
| **T9** 同行评审 | 6 维度评分（行业/学术默认开启，公众号可选） | `audits/审稿报告-vN.md` |

**流水线运行手册**（8 角色完整派发话术 + M 门 + F 模式 + AI 使用披露，T8 不 spawn）：`references/pipeline-readme.md`

**模板**（7 类，含 lite + full）：`references/templates/`（任务简报 / status状态机 / 交接报告 / 文献卡 / 数据卡 / 案例卡 / 先行者清单 + 审稿报告 / 修订说明 / 投稿就绪检查表 / checkpoint-card）


**关键参考**：

- 字数判定表（T7+T8 共用单一真源）：[`字数判定表.md`](字数判定表.md)
- 退化场景规范（跳过 Phase 3.5）：[`degraded-scenarios.md`](degraded-scenarios.md)
- 期刊数据库 + 匹配算法：[`期刊数据库.md`](期刊数据库.md) + [`期刊匹配算法.md`](期刊匹配算法.md)
- 中文数据源集成（OpenAlex/Crossref 默认推荐无需 Key）：[`中文数据源集成.md`](中文数据源集成.md)
- 多格式导出（可选 `--format md/latex/docx/pdf`）：[`format-export.md`](format-export.md)
- 设计文档 / 实战案例库：[`references/设计文档.md`](../设计文档.md) / [`references/case-studies.md`](../case-studies.md)
- 方法论实时可见面板（6 字段：当前阶段/证据强度/已触发闸门/下一步预测/不确定性/模型健康度）：[`status-template.md`](../templates/status-template.md)「方法论足迹」段

**T9 同行评审**（行业/学术默认开启，公众号默认关闭）：6 维度 1-5 分（原创性 / 方法论 / 证据强度 / 论证结构 / 写作质量 / 引文规范），26-30 accept / 21-25 minor / 16-20 major / <16 reject。详见 [`references/agents/09-审稿-peer-reviewer.md`](../agents/09-审稿-peer-reviewer.md) + [`references/templates/审稿报告-template.md`](../templates/审稿报告-template.md)。

**G14 中文 AI 痕迹深度检测闸**：8 类检测维度（学术模板语 / 句式同质化 / 学术套话高频 / 破折号滥用 / 三项排比 / 人称错位 / 个人辨识度缺失 / 党报话语堆砌），**LLM 推理判定**（零 exec 依赖）。0-2 类 Pass / 3-4 类 Warning（主控呈报 3 选 1，不自动修订）/ 5+ 类 Fail 触发 T5 修订 2 轮。详见 [`references/gates/14-中文AI痕迹-gate.md`](../gates/14-中文AI痕迹-gate.md)。**主人在 Phase 0 可显式关闭 G14**。

## 核心文档索引（按需加载）

主控按需加载时查此表，不凭记忆找文件：

| 用途 | 文档 | 加载时机 |
|------|------|---------|
| 核心概念单一真源（10 角色 + 三层防御 + 数据信任 3 档 + 工具边界）| [`glossary-full.md`](glossary-full.md)；子代理必读精简版 [`glossary-core.md`](glossary-core.md) | 🟡 按需 |
| 快速开始（5 分钟上手）| [`QUICKSTART.md`](../../QUICKSTART.md) | 新用户首读 |
| 模型 5 档候选池 + 映射规则 | [`model-assignment.md`](../model-assignment.md) | Phase 0 模型自检 |
| 交付边界 + F1-F9 失败模式 + M 门 + 阶段闸门 | [`deliverables.md`](../deliverables.md) | Phase 0 读 / Phase 4-5 复核 |
| F 体系详解 | [`failure-modes.md`](failure-modes.md) | Phase 0 / 4 |
| 错误友好化（12 类常见错误）| [`errors.md`](../errors.md) | 出错时查 |
| 配图 + 写手禁做 + 成本模型 | [`operations.md`](../operations.md) | Phase 4.4 |
| 证据检索边界（能/不能主动采集，判断口诀「这是已发布证据吗」）| [`phase-1-details.md`](phase-1-details.md)「检索边界」| Phase 1 |
| G0-G14 审计详解 | [`audit-checklist-quickref.md`](audit-checklist-quickref.md) | Phase 4 |
| M 门算法完整规约 | [`M-Gate-Algorithm.md`](M-Gate-Algorithm.md)（🟠 分片必读：伪代码段必读 / 附录按需 → [`M-Gate-Algorithm-appendix.md`](M-Gate-Algorithm-appendix.md)）| 跑 M 门前 + T8 终检前 |
| 实战案例库（商业热点 / 品牌一致性 / 原创性悖论）| [`case-studies.md`](../case-studies.md) | 参考 |

---
