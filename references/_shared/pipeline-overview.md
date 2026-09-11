> 版本：v2.12.15（自动同步 2026-09-11）


> 🌐 **语言政策**：产出语言默认中文，Phase 0 可改 English / 中英混 / 其他（写入任务简报「目标语言」字段，全流程以该字段为准）；中文特化（G14 中文 AI 痕迹检测 / GB/T 7714-2015 引用规范）是设计定位，不构成使用者语种限制。

# 流水线全景与修订回环仲裁（派生速查视图）

> **本文件是 SKILL.md「流水线全景」「修订回环仲裁规则」两段的外移正文**（SKILL.md 只留压缩速查 + 指针）。流程顺序与阻断关系的**唯一真源**是 [`phase-order.yaml`](phase-order.yaml)——本文件与 yaml 冲突时**以 yaml 为准**，主控每进入一个 Phase 前必读 yaml 该 Phase 完整定义。

## 流水线全景（Phase 0-5）

> 🔴 **唯一真源声明**：本段是**派生速查视图**，流程顺序与阻断关系的**唯一真源**是 [`references/_shared/phase-order.yaml`](phase-order.yaml)。主控每进入一个 Phase 前**必读 yaml 该 Phase 完整定义**（含 parallel_agents / condition / bounded_loop / output_chars_max），不凭本段文字记忆推进；两处冲突时**以 yaml 为准**。

```
Phase 0 定题        与主人确认主题/篇幅/受众/配图意向 → run/<项目名>/01-任务简报.md + status.md；checkpoint-card 骨架呈现
Phase 1 并行检索    T1 ∥ T2 ∥ T3（三方真并行，sessions_yield 等待；T3 任何量级必 spawn，含 0 条空卡协议）
Phase 1.5 定向回查  条件触发窗口（任务简报标 [Dxx 待复核] / 🔴 二手转引未回溯 / T9 证据强度低）；触发则 spawn T1b → 更新数据卡 → 重跑 T2.5；未触发必须记录 not_triggered + 依据
T2.5 完整性门       主控 checkpoint（T2 → T4 间）：数据卡条数 ≥ 任务简报需求数 + 信任级别完整 → 通过才派 T4；不通过 → T2 重检索或主控补数据
Phase 2 分析        T4 → analysis/分析大纲.md（论点-论据映射 + 反方论证规划 + 三角验证）
Phase 2.5 大纲确认  主人过目大纲 + 拍板 T4 建议图表（图位/类型/数据源）（人在环！改方向成本最低）
Phase 3 写作        T5 → drafts/初稿-v1.md（铁律：引用标[Lxx]、数字标[Dxx]、案例标[Cxx]、AI去味10项）
Phase 3.5 洞察补充  主人过目 v1 → 主控问主人洞要补 → T5 v2 融入（人在环！教训 #263）
Phase 3.6 批判      T6（攻击 v2 不是 v1，轻量档可跳过）∥ G14 中文 AI 痕迹闸同批并行（与 T6 对同一 current_draft 同批 spawn）→ 0-2 类 Pass / 3-4 类 Warning / 5+ 类 Fail
Phase 4 审计        T7 → audits/审计报告-vN.md（G0-G14）
Phase 4.2 修订      审计打回 → 写手交修订说明+修订稿 → 审计复核 ≤2 轮 → 仍不过升级主控
Phase 4.4 配图      数据图表：Phase 2.5 拍板图位 → 写手已标 [图N：标题] → 主控 write 手写 SVG（本地零外发）；封面：Phase 0 勾选「启用封面生成」→ image_generate 外发（默认关闭；vendor 路由为宿主配置行为）
T7.5 完整性门       主控 checkpoint（T7 → T8 间；T9 在门后）：审计报告 + 修订回环记录齐备才放行终检
Phase 4.5 审稿      T9 同行评审（= yaml t9_review 独立节点，在 T7.5 完整性门后、T8 终检前；行业/学术默认开启，公众号可选）→ audits/审稿报告-vN.md（6 维度评分 → accept/minor/major/reject）
Phase 5 终检        主控终检 → final/定稿.md + 图件/ + 证据包/ + 交付说明.md（默认 md 完整支持；latex/docx/pdf 由主人自备模板 + 手动跑 pandoc + rsvg-convert，论衡 agent 不执行，详见 [_shared/format-export.md](format-export.md) §零 exec；项目收尾归档按 [_shared/project-archive-sop.md](project-archive-sop.md)：主控出归档清单，主人手工 mv/cp，agent 不执行）
```

> **Phase 详细操作按需加载**：[`phase-1-details.md`](phase-1-details.md)（检索边界 / 强相关性 / 三角验证 / 数据信任 3 档）、[`phase-2-details.md`](phase-2-details.md)（退化场景）、[`phase-3-details.md`](phase-3-details.md)（写作铁律 10 项 + 洞察补充 + T6/G14 + 修订回环）。

---

## 修订回环仲裁规则

| 轮次 | 内容 | 计数 |
|---|---|---|
| v1 | T5 初稿 | 0 轮 |
| v1 → v2 | 主控洞察轮（Phase 3.5 主人补充 + T6/G14 反馈融入） | 1 轮 |
| v2 → v3 | 批判反馈轮（T7 打回 / G14 Warning+ 修订）或 T8 亲修 | 2 轮 |
| v3 之后 minor cosmetic（≤5% 字 / 引用格式 / 拼写） | T8 inline 亲修（minor 修补通道，独立计数） | minor |
| v3 之后 P0 / 结构性 P1（A/B/C） | spawn T5 v4 独立写手 + 启动 Acknowledged Limitations 模式 | 例外通道（超常规 2 轮，须主人拍板）|

> **对外承诺口径**：论衡对外承诺「**常规批判/审计修订 ≤2 轮**」；minor 修补通道与 P0 例外通道是**显式披露的独立计数**（在交付说明中登记，不混入 2 轮承诺）——不存在静默的无限修订。

T7 / T9 / G14 报告头部显式写 `修订回环 = N/2`；T8 终检按此表仲裁。T9 minor 默认 T8 inline 处置；T9 major / 扩写建议 → 呈主人拍板是否启 v4。

---
