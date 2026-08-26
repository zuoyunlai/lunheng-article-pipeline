> 版本：v2.5.9（自动同步 2026-08-26）




# 论衡（lunheng-article-pipeline）— 中文学术 / 深度长文多 Agent 流水线

> **中文学术/深度长文专用**。多 Agent 编排 + 三角验证（文献/数据/案例）+ M 门形式合规 + 实战反馈驱动升级。5000+ 字强推。

**v2.5.4**（2026-08-25，当前版本）— [ClawHub 已上架](https://clawhub.ai/zuoyunlai/skills/lunheng-article-pipeline) / [MIT License](LICENSE) / 真源 [226 文件 / 34,370 行]。H1 标题修复 + security-audit Clean + vetter 净化包 0 findings。

论衡把一篇深度长文 / 论文的生产拆成 **9 张角色卡 + 6 个阶段**，由主控用 OpenClaw `sessions_spawn` 编排三方真并行子代理（T1∥T2∥T3 互不干涉），产出有**证据底座、反方论证、独立审计、人工核验节点**的交付物。T8 终检由主控亲完成，**T9 同行评审 v2.4.0 新增**（6 维度评分 + 期刊匹配）。定位：学术论文 / 商业评论 / 行业分析 / 公众号深度长文通用（v2.4.4 澄清中文特化为设计定位，非 locale 缺陷）。经验证：~9500 字深度文全流程约 2 小时。

---

## 🌟 快速开始（5 分钟）

**第一次使用？** 读 [`QUICKSTART.md`](QUICKSTART.md)：

1. **写任务简报**（2 分钟）：新建 `<项目名>/01-任务简报.md`，含研究问题/类型/篇幅/引用格式 + Phase 0 同意关卡
2. **主控自动派发**：T1∥T2∥T3 并行检索 → T4 分析 → T5 写作 → T6 批判 → T7 审计 → T9 审稿 → T8 主控亲终检
3. **主人在 4 个节点介入**：Phase 0（定题）/ 2.5（大纲）/ 3.5（洞察）/ 5（终稿）——Phase 3.6（T6 批判）+ Phase 4.5（T9 审稿）是内部流水线动作

**预计项目时间**：轻量档（≤4000 字）30-60 分钟 / 中段档 1-2 小时 / 重量档（≥5000 字）2-4 小时。

---

## ⚠️ 外发项与能力边界声明

**流水线默认会调用以下外部服务**（使用前需主人同意——Phase 0 同意关卡，4 选 1）：

| 操作 | 第三方服务商 | 发送内容 |
|------|------------|---------|
| `web_search` | OpenClaw 内置 web provider | 检索关键词 |
| `tavily_search` / `tavily_extract` | **Tavily AI** | 研究主题/URL |
| `image_generate`（封面，可选默认关闭） | **OpenAI gpt-image-2**（默认）→ Google gemini / minimax-image / SVG 本地 | 主题 + 品牌 prompt |
| **数据图表 SVG** | **本地内置**（主控 `write` 手写 SVG，零外发） | — |
| 大模型推理 | 当前模型 provider | 文献/数据/案例/草稿/大纲全文 |
| `memory_get` / `memory_search` | 仅本地 OpenViking（**不外发**） | 检索关键词 |

**主控 agent 能力边界**（**不**会做的事）：
- ❌ 不调用 `exec` / `process` 工具（15 项白名单 + 11 项 denied）
- ❌ 不读取运行时内部路径（`~/.openclaw/agents/<agent>/sessions/*.trajectory.jsonl` 等）
- ❌ 不直接计算 sha256（需要时由主人在 host shell 手动跑后回填）
- ❌ 不主动采集一手数据（实验/调查/访谈）—— 主人投喂后使用

**Phase 0 强同意关卡**：所有外发项在流水线启动前需主人明示同意（4 选 1：全部同意 / 脱敏+SVG+本地 Ollama / 部分同意 / 全部拒绝）。**未同意前不可跳到 Phase 1**。

完整说明 + 错误信息友好化（12 类常见错误）：详见 [`SKILL.md`](SKILL.md) + [`references/errors.md`](references/errors.md)。

---

## 核心特点

### 三不原则（质量底线）
- **不编造** — 引用带 URL/DOI + 数据带来源年份 + 审计分级抽验
- **不堆砌** — 强相关性铁律（每条材料必答「它支撑哪个论点」+ 反向淘汰自查）
- **不重复** — 先行者检索 + 差异点声明 + 原创性审计

### 九角色流水线

```
主控（Coordinator）—— 定题/拆解/派发/T8 终检亲完成/状态机
  │
  ├─ T1 文献检索员（Literature Scout）── 文献卡 [Lxx]      ┐
  ├─ T2 数据检索员（Data Scout）──────── 数据卡 [Dxx]      │ 三方真并行
  ├─ T3 案例检索员（Case Scout）────── 案例卡 [Cxx]      ┘ 互不干涉
  │
  ├─ T4 分析员（Analyst）────────── 分析大纲（论证主线 + 反方论证 + 建议图表）
  ├─ T5 写手（Writer）────────────── 初稿（AI 去味 10 项）
  ├─ T6 批判伙伴（Critical Companion）── 批判报告（C1-C7 反方攻击 v2）
  ├─ T7 审计员（Auditor）────────── 审计报告（G0-G14 = 15 项）
  └─ T9 同行评审（Peer Reviewer，v2.4.0 新增）── 审稿报告（6 维度评分 + 期刊匹配，**v2.4.6 按模式默认开启**）
              ↓
         T8 终检 = 主控亲完成（无独立角色卡）
```

**T9 同行评审**（v2.4.0 新增，v2.2.x ARS Stage 4.5 论衡化）：论文投稿前的「预演审稿人」，6 维度（原创性/方法论/证据强度/论证结构/写作质量/引文规范，总分 30）→ accept / minor / major / reject 建议。**v2.5.0 期刊匹配助手**：基于 T9 评分 + 主题关键词，从 25 中文 CSSCI/北大核心 + 12 英文 SSCI 数据库输出 Top 3 + 综合匹配度（主题契合 50% + 风格匹配 30% + T9 评分 20%）。**行业分析/学术论文默认开启**，公众号默认关闭（主人可选）。详见 [`09-审稿-peer-reviewer.md`](references/agents/09-审稿-peer-reviewer.md)。

**G14 中文 AI 痕迹深度检测闸**（v2.4.0 新增）：Phase 4.5 与 T6 并行。8 类检测维度（学术模板语/句式同质化/学术套话高频/破折号滥用/三项排比/人称错位/个人辨识度缺失/党报话语堆砌），LLM 推理判定（**零 exec**）。0-2 类 Pass / 3-4 类 Warning 触发修订 1 轮 / 5+ 类 Fail 触发 2 轮。详见 [`14-中文AI痕迹-gate.md`](references/gates/14-中文AI痕迹-gate.md)。

### 三角验证（证据底座）

| 卡片 | 给的是 | 适用论点 |
|------|--------|---------|
| 文献卡 [Lxx] | 理论 / 学术依据 | 「这事有没有人研究过」 |
| 数据卡 [Dxx] | 量级 / 趋势 | 「这事多大、占比多少」 |
| 案例卡 [Cxx] | 事件结构（who/when/what/各方说法） | 「这事具体怎么发生的」 |

**数据信任级别**（v2.2.1 核心机制）：
- 🟢 **已发布公开数据**（最高信任）— 官方统计年鉴 / 学术论文 / 行业协会公开报告
- 🟡 **主人投喂数据**（中信任）— 一手调研 / 访谈记录 / 田野调查
- 🔴 **二手转引**（低信任，严格限制）— 必须回溯一次文献 + 顶部标注

### 人在环四节点
- **Phase 0 定题** · **Phase 2.5 大纲** · **Phase 3.5 洞察补充** · **Phase 5 终稿**

### 三层防御体系

| 层 | 性质 | 用途 |
| --- | --- | --- |
| **M 门**（形式合规）| 机械化、LLM 推理判定（**零 exec**）| 引用/数据/案例的形式完整性（M-Form 8 项 + M-Exist 3 项 + M-Integrity 2 项 = 13 项）|
| **F 模式**（失败模式）| 面向用户的叙事 | F1-F9 失败模式清单（幻觉/格式/数据信任/论证强度）|
| **G 清单**（质量审计）| 面向审计员 | G0-G14 共 15 项（v2.4.0 加 G14 中文 AI 痕迹）|

**修订回环 ≤2 轮硬约束**（v2.2.0）：第 3 轮触发 → Acknowledged Limitations 模式（未关闭 P0/P1 搬入 `final/局限性.md`，论文正常交付不假装完美）。

完整定义：详见 [`references/glossary.md`](references/glossary.md)。

---

## 流水线全景

```
Phase 0  定题       →  01-任务简报.md + status.md
Phase 1  T1∥T2∥T3 三方真并行检索（文献/数据/案例）
Phase 2  T4 分析   →  analysis/分析大纲.md（三角验证 + 原创性声明）
Phase 2.5 主人在环：确认大纲 + 拍板图表
Phase 3  T5 写作   →  drafts/初稿-v{N}.md
Phase 3.5 主人在环：v1 洞察补充 → v2
Phase 3.6 T6 批判  →  analysis/批判报告（攻击 v2，C1-C7 反方论证）
Phase 4  T7 审计   →  audits/审计报告（G0-G14）
Phase 4.2 修订回环   写手修订稿 ≤2 轮（v2.2.0 硬约束）
Phase 4.5 配图 + T9 审稿 + G14 检测（与 T6 并行）
Phase 5  T8 主控亲终检 → final/定稿.md + 证据包/ + 交付说明.md
```

---

## 怎么用

**方式一（推荐）**：ClawHub 安装
```bash
openclaw skills install @zuoyunlai/lunheng-article-pipeline
# 或本地：openclaw skills add /path/to/lunheng-article-pipeline
```

**方式二：参考方法论**——九角色 + 三角验证 + 独立审计 + 三不原则可移植到任意支持子代理编排的框架。

**模型更换**：能力分层（检索/分析写作/审计/主控）+ 候选池集中管理，任何 OpenAI 兼容模型可替换。详见 [`SKILL.md 模型分档`](SKILL.md)。

---

## 实战验证案例

完整案例库见 [`references/case-studies.md`](references/case-studies.md)（5 个案例）：原创性悖论 ~9500 字（A-）/ AI 安全对齐阿克琉斯之踵 ~7200 字（A-）/ AI 安全隐患 ~5700 字 / 商业热点 7650 字 / 品牌一致性 ~7900 字。

---

## 论衡哲学

> **「独立角色 + 机械化门 > 自我复核」** —— 论衡的核心命题。

主控自我复核是 LLM 的舒适区陷阱。M 门通过「LLM 兜底执行伪代码」把「自我审视」变成「结构化核验」（**零 exec 依赖**，不引入 Python 脚本，不扩大 exec 白名单）；F 失败模式（借鉴 ARS Lu et al. *Nature* 2026）把质量维度变成「AI 失败模式清单」威慑设计；**T6 批判伙伴**从反方独立攻击论证（v2 含主人洞察）。

**版本升级自审门 + 自动化**：
- **v2.2.6**：7 门机械化自审，防「改 A 漏 B」与「头痛医头」
- **v2.3.12**：能力抽象为「能力档 + 候选池」（不再硬编码模型名）
- **v2.3.13**：skill 化部署（任意有 `sessions_spawn` 的 agent 加载即可跑）
- **v2.5.4**：sync-version.sh 与 check-version.sh 双向同步 36 项（教训 #118.1 升级）

---

## 版本演进（重大里程碑）

| 版本 | 时间 | 阶段 | 核心改进 |
|------|------|------|---------|
| v2.0.5 | 2026-08-12 | 初始发布 | 7 角色基础流水线 |
| v2.1.0 | 2026-08-14 | 激进重构 | 7 角色心跳 + 8 分硬卡 + G8/G9 审计补盲区 |
| v2.1.8 | 2026-08-15 | 并行架构 | T1∥T2∥T6 三检索员独立并行 + 0 条空卡协议 |
| v2.2.0 | 2026-08-15 | 机械化门 | M 门 11 项 + F1-F7 失败模式 + 修订 ≤2 轮 |
| v2.2.13 | 2026-08-19 | 模板拆分 | SKILL.md 精简 23 行 + QUICKSTART + errors 友好化 |
| v2.2.18 | 2026-08-20 | scanner 闭环 | ClawHub 16 findings 全清零 + 64/64 vendors clean |
| v2.3.0 | 2026-08-21 | 角色重构 | 9 角色编号统一 + Phase 3.6 批判节点 |
| v2.3.13 | 2026-08-23 | skill 化 | 纯 skill 部署 + 模型收敛（能力档唯一真源）|
| v2.4.0 | 2026-08-23 | 功能增强 | G14 中文 AI 痕迹闸 + T9 同行评审 + 方法论足迹面板（借鉴 deep-research-pro 论衡化）|
| v2.4.3 | 2026-08-24 | 净化包极简 | 12 findings → 0（strip-shell + 嵌套代码块） |
| v2.5.0 | 2026-08-24 | 可选项 | 期刊匹配（25 中文 + 12 英文）+ 中文数据源 3 梯队 + 多格式导出 |
| v2.5.1 | 2026-08-24 | 数据源 | OpenAlex/Crossref 第一梯队默认推荐（无需 Key） |
| **v2.5.4** | **2026-08-25** | **当前** | **H1 标题修复（publish --name）+ security-audit Clean + vetter 净化包 0 findings + 中文 AI 痕迹闸坦诚披露 + 36 项 sync/check 双向同步（教训 #118.1 升级）** |

完整 changelog 见 [Releases](https://github.com/zuoyunlai/lunheng-article-pipeline/releases)。教训沉淀 144+ 条见 [memory/lessons.md](https://github.com/zuoyunlai/openclaw-workspace)。

---

## 许可

[MIT License](LICENSE) — Copyright (c) 2026 左运来 (zuoyunlai)。允许商业使用、修改、再分发，需保留版权声明。