> 版本：v2.8.0（自动同步 2026-09-08）













> **核心精简版**（子代理必读，约 2.5K）。完整设计者文档见 [`glossary-full.md`](glossary-full.md)（含关键协议 / 工具边界 / 版本管理 / 引用形式 / 关键术语）。

## 核心角色（10 张卡，T8 终检主控亲完成不 spawn）

| 编号 | 角色 | 关键职责 |
|---|---|---|
| T0 | 主控（Coordinator） | 任务拆解 / 派发 / 状态机 / T8 终检亲完成 |
| T1 | 文献侦查（Literature Scout） | web_search + tavily_search 检索中英文文献 + 先行者清单 |
| T2 | 数据检索（Data Scout） | 国家统计局 / 世行 / CEIC / 皮书 |
| T3 | 案例检索（Case Scout） | 企业行为 / 事件 / 司法案件 |
| T4 | 分析（Analyst） | 论点-论据映射 + 反方规划 + 三角验证 |
| T5 | 写手（Writer） | 严格按大纲 / 数据卡写，AI 去味 10 项 |
| T6 | 批判伙伴（Critical Companion） | C1-C7 七维反方攻击（Phase 3.6 同批 T6∥G14） |
| T7 | 审计（Auditor） | G0-G14 形式核验 + 修订任务书（Phase 4） |
| T8 | 终检（Final Inspector） | 主控亲完成，不 spawn；14 必查项 + 小幅修补权限 |
| T9 | 同行评审（Peer Reviewer） | 6 维度评分 + 期刊匹配（Phase 4.5，可选） |

## 数据信任 3 档（v2.7.3 ECS 文档化）

| 档 | 判定 | 典型 |
|---|---|---|
| 🟢 | 一手：官方统计 / 同行评议 / 学术专著 / 官方一手发布（即使转载，链接指官方原文） | 统计年鉴、期刊论文 |
| 🟡 | 二手：媒体转引 / 百科 / 行业报告 / **聚合平台汇编**（头条聚合、数据聚合站）| 媒体报道数字、艾瑞报告 |
| 🔴 | 单边：平台单方公告 / 自媒体 / 单一来源 | 厂商自报数据 |

> **聚合类铁律**：头条聚合/数据聚合站 ≠ 一手——除非链接直接指向发布机构原文，否则一律 🟡 起步。

## 关键协议（v2.5.6 起为单权威）

完整 5 协议见 [`关键协议.md`](关键协议.md)。子代理执行时只需知道：

- **Phase 0 同意关卡**：外发数据必须先经主人拍板（4 选 1，全同意 / 脱敏 SVG+本地 / 部分 / 全部拒绝）
- **修订回环 ≤2 轮**：v1 → v2（1 轮）→ v3（2 轮）；超 2 轮走 Acknowledged Limitations
- **Phase 3.6（Phase 4 修订回环内的反方攻击）**：T6 与 G14 同批对 current_draft 出报告，主人 Phase 5 签字是闭环终点
- **零 exec**：所有子代理不允许 `exec` / `process` / `browser` / `apply_patch` 等

## 工具边界（5 档子代理最小工具集声明，v2.7.12 修正）

| 档 | 角色 | 工具集（声明） |
|---|---|---|
| allow_research | T1/T2/T3 | read + write + edit + web_* + tavily_* |
| allow_analysis | T4 | read + write + edit |
| allow_writing | T5 | read + write + edit |
| allow_audit | T6/T7 | **read（只读）** |
| allow_review | T9/G14 | **read（只读）** |

> v2.7.12：以上为声明/部署建议，不是 spawn 传参——OpenClaw 2026.9.x 的 `sessions_spawn` 已无 toolsAllow 参数，子代理实际权限 = 平台硬性剥除（含 session_status，子代理不可持有）+ 主控策略快照 + 宿主 config `tools.subagents`（详见 SKILL.md「执行能力边界」）。

> image_generate / memory_get 系列 / exec 等均在 denied；T8 由主控亲完成不 spawn。

## 编号体系

- **[Lx]** 文献 / **[Dx]** 数据 / **[Cx]** 案例——三角验证基础
- **D-基-xx-xx** 基线数据（资金 R / 阈值 T / 案例 C / 其他 E）必保留完整编号
- **教训 #N** 引用：主真源在 `~/.openclaw/workspace/memory/lessons.md`，≥#115 才校验
