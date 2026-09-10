> 版本：v2.12.5（自动同步 2026-09-10）

























































# 项目状态机 — run/<项目名>/status.md

> **读取指引**：主控/子代理运行期**只读「一~四」节（~3K）** 维护状态；「方法论足迹」「执行韧化记录」「维护说明」「重写说明」是扩展段（~7K），按需查阅——无需要时不必全量读。
>
> **重写**（教训 #166，主控实测反馈）：原 markdown 表格 7 列 + 主控 edit 频繁失败（空格漂移 / old_string 不匹配 / 重复行 bug）。**改为「4 段结构化纯文本」+ key:value 字段**，主控用 `**当前**: X` → `**当前**: Y` 替换策略，零空格漂移、零编辑摩擦。
>
> 主控维护，每个角色交接时更新对应行。状态：Inbox → Assigned → In Progress → Review → Done | Failed | Skipped。对 T3 和 Phase 1.5 不得只写通用 `Skipped`，必须使用下方规定的结果/触发状态。
> 失败必须留原因；任一行停留 >8 分钟无进展 → 主控介入（按主控卡 §二十二 硬卡阈值表）。
> **T3 案例检索任何量级必 spawn**（教训 #267）——含 0 条场景走空卡协议；T2 不再兼带案例，状态独立行。

## 一、项目元数据（key:value 替换，主控用 `**当前**: X` 策略）

**项目名**: <项目名>
**模式**: 学术论文 / 商业评论 / 行业分析 / 公众号深度长文
**当前阶段**: Phase 0 / Phase 1 / Phase 1.5 / Phase 2 / Phase 2.5 / Phase 3 / Phase 3.5 / Phase 3.6 / Phase 4 / Phase 4.2 / Phase 4.5 / Phase 5
**当前活动**: <一句话描述>
**最后更新**: YYYY-MM-DD HH:MM
**软保障**: mechanical / prompt-level（Phase 0 确认：mechanical = 主控无特权工具；prompt-level = 宿主未机械 deny、主人已确认软保障运行）
**M 门**: v2.2.12 / v2.5.x
**数据信任档**: 全外发 / 混合 / 全人工（教训 #259，拓展，Phase 0 拍板）
  - 全外发：默认 web_search + tavily_search 检索，主人不投喂一手数据
  - 混合：部分一手（主人投喂 / 限定检索） + 部分 LLM 检索
  - 全人工：所有数据均为主人一手，LLM 不检索
**G14 状态**: enabled / disabled_by_owner（Phase 0 决定后全项目不变）
**当前稿件**: draft_id=<唯一标识> / draft_version=v1 / 来源=T5
**审计修订轮**: 0 / 上限=2
**T8 技术终检**: ⬜ 未完成 / ✅ 完成
**Phase 5 主人验收**: ⬜ 未决策 / ✅ accepted / 🔁 revision_requested / ↩ restart_phase / ⏸ deferred

## ▲ 降级运行记录（fallback 每次一行，主人扫一眼可见）

- （无降级时保持此空行；有降级必须写：`▲ DEGRADED RUN：<角色> 由主控顶替（<原因：401/超时/配额>）HH:MM → 产物头部已标注`）

## 人在环决策记录（四节点，缺一不可）

- **Phase 0 定题**: decision=<start|补充信息|暂停|拒绝> / owner_confirmed_at=<时间> / evidence=01-任务简报.md
- **Phase 2.5 大纲**: decision=<approved|revision_requested> / owner_confirmed_at=<时间> / evidence=analysis/分析大纲.md
- **Phase 3.5 洞察**: decision=<insight|no_insight> / owner_confirmed_at=<时间> / evidence=drafts/初稿-v1.md
- **Phase 5 验收**: decision=<accepted|revision_requested|restart_phase|deferred> / owner_confirmed_at=<时间> / evidence=final/定稿.md

> 仅有材料、主控代判、子代理声称已确认，均不构成决策；`no_insight` 是明确决策，不是跳过。

## 二、角色状态（key:value 替换，每角色一行）

> **维护规则**：主控用 `**T<n> 角色**: ⬜ Inbox` → `**T<n> 角色**: ✅ Done (时间)` 替换。**禁止** 用表格行替换，零空格漂移风险。

- **T1 文献检索**: ⬜ Inbox → 🔄 In Progress → ✅ Done（YYYY-MM-DD HH:MM, N 文献卡）
- **T2 数据检索**: ⬜ Inbox → 🔄 In Progress → ✅ Done（YYYY-MM-DD HH:MM, N 数据卡 + M 缺口）
- **T2.5 完整性门**: ⬜ Inbox → 🔄 In Progress → ✅ Done（YYYY-MM-DD HH:MM, 主控 checkpoint）
- **T3 案例检索**: ⬜ Inbox → 🔄 In Progress → ✅ Done（YYYY-MM-DD HH:MM, result=required|empty_card|waived, N 案例卡）
- **T4 分析**: ⬜ Inbox → 🔄 In Progress → ✅ Done（YYYY-MM-DD HH:MM, analysis/分析大纲.md）
- **Phase 2.5 大纲确认**: ⬜ Inbox → 🔄 In Progress → ✅ Done（主人确认日期, 拍板图位 N）
- **T5 写作**: ⬜ Inbox → 🔄 In Progress → ✅ Done v1/v2/v3（YYYY-MM-DD HH:MM, 初稿-v3.md, M 字数）
- **Phase 3.5 洞察补充**: ⬜ Inbox → 🔄 In Progress → ✅ Done（主人确认日期, 洞察内容或「无补充」决策）
- **T6 批判伙伴**: ⬜ Inbox → 🔄 In Progress → ✅ Done（YYYY-MM-DD HH:MM, C1-C7 报告）
- **Phase 1.5 定向回查**: ⬜ not_triggered（必须写未触发依据）→ 🔄 triggered → ✅ Done（YYYY-MM-DD HH:MM, T1b 回查报告 + T2.5 重跑）
- **G14 中文 AI 痕迹闸**: ⬜ Inbox → 🔄 In Progress → ✅ Done（YYYY-MM-DD HH:MM, 8 类检测, Pass/Warning/Fail）
- **T7 审计**: ⬜ Inbox → 🔄 In Progress → ✅ Done（YYYY-MM-DD HH:MM, 审计报告-vN.md + 反哺报告-vN.md）
- **修订回环**（≤2 轮）: ⬜ Inbox → 🔄 第 1 轮 → ✅ Done / 🔄 第 2 轮 → ✅ Done / 🔒 Acknowledged Limitations 模式
- **T7.5 完整性门**: ⬜ Inbox → 🔄 In Progress → ✅ Done（YYYY-MM-DD HH:MM, 主控 checkpoint）
- **T8 技术终检**: ⬜ Inbox → 🔄 In Progress → ✅ Done（YYYY-MM-DD HH:MM, final/定稿.md 技术检查）
- **Phase 5 主人验收**: ⬜ 未决策 → 🔄 In Progress → ✅ accepted / 🔁 revision_requested / ↩ restart_phase / ⏸ deferred
- **T9 同行评审**: ⬜ Inbox → 🔄 In Progress → ✅ Done（YYYY-MM-DD HH:MM, 6 维度评分 XX/30 + Top 3 期刊）

## 三、闸门清单（checklist）

- [ ] **M-Integrity-1**（T2.5 数据完整性，T2 → T4 间触发）
- [ ] **M-Integrity-2**（T7.5 审计完整性，T7 → T8 间触发）
- [ ] **M-Form-6**（数据卡信任级别完整性）
- [ ] **M-Form-7**（交付边界纯净，T8 终检必跑，教训 #139）
- [ ] **M-Form-8**（三角验证覆盖率）
- [ ] **M-Exist-1**（数据 URL 真实存在）
- [ ] **M-Exist-2**（证据包完整性校验，教训 #169）
- [ ] **M-Exist-3**（数据信任级别一致性）
- [ ] **G14 中文 AI 痕迹闸**（Phase 4.5 触发）
- [ ] **T2.5 数据完整性门**
- [ ] **T7.5 审计完整性门**

## 三.五、M 门执行记录（教训 #286，主控每 phase 跑完登记）

> **用途**：M 门从「T8 终检一次性跑」升级为「每 phase 强制跑 + 记录」。主控每跑一道 M 门，在此登记结果（时间 + 结论 + 通过/失败）。

| Phase | M 门 | 执行时间 | 结论 | 状态 |
|-------|------|---------|------|------|
| T2.5 完整性门 | M-Integrity-1 + M-Form-6 + M-Exist-3 | YYYY-MM-DD HH:MM | 通过/失败 + 一句话 | ✅/❌ |
| T7.5 完整性门 | M-Integrity-2 + M-Form-8 + M-Exist-2 | YYYY-MM-DD HH:MM | 通过/失败 + 一句话 | ✅/❌ |
| v1→v2 修订后 | 章节级 M 门| YYYY-MM-DD HH:MM | 变更点 N 处 | ✅/❌ |
| T8 终检 | M-Form 8 + M-Exist 3 = 11 项 | YYYY-MM-DD HH:MM | exit 0 / exit 1 | ✅/❌ |

## 四、产物路径（key:value 替换）

- **drafts/初稿**: drafts/初稿-v{N}.md
- **analysis/分析大纲**: analysis/分析大纲.md
- **analysis/批判报告**: analysis/批判报告-v{N}.md
- **audits/审计报告**: audits/审计报告-v{N}.md
- **audits/反哺报告**: audits/反哺报告-v{N}.md
- **audits/审稿报告**: audits/审稿报告-v{N}.md
- **audits/G14 检测报告**: audits/G14-检测报告-v{N}.md
- **literature/回查报告**: literature/回查报告-v{N}.md
- **final/定稿**: final/定稿.md
- **final/交付说明**: final/交付说明.md
- **final/M-Gate 报告**: final/M-Gate-Report-v2.2.12.json

---

## 📊 方法论足迹

> **借鉴 deep-research-pro 的方法论透明**（论衡化，非竞品简单复制）
> **作用**：让主人/读者实时看到「**为什么是这个进度、证据强度是多少、下一步预测什么**」
> **维护方**：主控自动更新（每个 Phase / 闸门 / 子代理完成时刷新）
> **归档**：项目结束时同步归档到 `run/<项目名>/audits/methodology-footprint-{项目名}.md`

### 4.1 当前阶段（实时）

| 字段 | 当前值 | 更新时机 |
|------|--------|---------|
| **Phase** | Phase X.X（阶段名）| T0 启动阶段时 |
| **核心活动** | 当前在做 XX | 子代理 ACK 时 |
| **已进入时间** | N 分钟 | 阶段启动时 |
| **预计剩余** | N-N 分钟 | 子代理 ACK 时 |

### 4.2 证据强度（实时，三角验证可视化）

| 维度 | 当前 | 目标 | 状态 | 备注 |
|------|------|------|------|------|
| **文献覆盖** | N 篇（核心 X / 次要 Y） | ≥X 篇核心 | ✅/⚠️/❌ | T1 完成后刷新 |
| **数据来源** | N 个（来源 1 + 来源 2 + ...）| ≥X 个独立 | ✅/⚠️/❌ | T2 完成后刷新 |
| **案例支撑** | N 个（事件/主体 X） | ≥X 个 | ✅/⚠️/❌ | T3 完成后刷新 |
| **三角验证** | N 论点 X 三档齐 | ≥X% 三档齐 | ✅/⚠️/❌ | T4 完成后刷新 |
| **基线编号**| N 条 [D-基-xx-xx] | ≥X 条 | ✅/⚠️/❌ | T2 完成后刷新 |
| **G14 AI 痕迹**| Pass / Warning / Fail | Pass | ✅/⚠️/❌ | G14 闸门后刷新 |

### 4.3 已触发闸门（实时清单）

参见顶部「## 三、闸门清单」checklist。

### 4.4 下一步预测（实时，LLM 推理预测）

```
当前阶段完成后，下一阶段预计：
- 触发 T6 批判伙伴（预计 5 分钟内）
- T5 进入 Phase 3 写作（预计 40 分钟内进入 Phase 4.5）
- G14 闸门预计 2 分钟内触发

▲ 预测仅供主人参考，不作为承诺
```

### 4.5 不确定性（实时，主人看到的所有风险点）

- ▲ **T1 覆盖**：某主题文献可能偏窄（仅 X 篇核心），下一步计划补检
- ▲ **T2 数据**：「某数据」最新数据待 G11 时效校验
- ▲ **T3 案例**：某事件案例可能涉及未公开信息，需谨慎引用
- ▲ **G14 痕迹**：8 类检测维度若有命中，按闸门规则触发修订
- ▲ **依赖外部**：论衡核心是 LLM 推理 + 文件读写 + Web 检索，若工具不可用自动降级

### 4.6 LLM 可用性（实时）

> **v2.3.12 P0-3 模型自检**：Phase 0 启动时主控扫本机可用模型，每个能力档从候选池按优先级选第一个可用模型，写入下方「本轮可用模型」表。**候选池见 `_shared/模型候选池.md`**（单一真源）。

| 能力档 | 角色 | 候选池（描述性，见模型候选池.md） | **本轮实际** | 真实可用性 | 余额 |
|--------|------|-------------------------------|-------------|-----------|------|
| 检索 | T1 / T2 / T3 | 小参数模型 + 高 token/秒 | `<实际>` | ✅实测 / ⚠️未验证 / ❌欠费失效 | ✅/⚠️/❌ |
| 分析写作 | T4 / T5 | 中大参数推理模型 | `<实际>` | ✅实测 / ⚠️未验证 / ❌欠费失效 | ✅/⚠️/❌ |
| 批判审计 | T6 / T7 / G14 | 顶级推理模型 | `<实际>` | ✅实测 / ⚠️未验证 / ❌欠费失效 | ✅/⚠️/❌ |
| 主控 | T0 | 中参数稳定模型 | `<实际>` | ✅实测 / ⚠️未验证 / ❌欠费失效 | ✅/⚠️/❌ |
| 终检 | T8 | 主控亲完成（不 spawn 子代理）| 主控亲完成 | - | - |

**真实可用性（教训 #236）**：Phase 0 模型自检升级为「**静态存在性 + 动态可用性**」双检查——静态读白名单确认模型 ID 存在，动态对每个候选模型做 1-token ping 记录真实返回码。「**配置存在 ≠ 可用**」：v2.10.3 首测顶配档 kkaiapi/claude-opus-5 配置在列但实际 403 认证失败，4 次 spawn 撞墙才暴露。顶配档全不可用 → 主控**显式告知主人**禁止静默降级。

**降级提示**：若顶配档（批判审计）候选池全不可用 → 主控**必须显式告知主人**「本机无顶配审计模型，审计/批判深度将降级，是否继续」——禁止静默降级。

### 4.7 token 消耗记录（精确机制）

> **用途**：T8 终检时汇总「token 总成本」呈现给主人（deliverables.md 成本指标字段的落地）。
> **重写根因**（教训 #256）：OpenClaw 的子代理 token 真实来源是**完成事件**的 `Stats:` 行（`tokens N (in N / out N) • prompt/cache N`），**不是 sessions_spawn 返回值**（其无 stats 字段）。教训 #192 早前把来源误记为「sessions_spawn 返回值 stats」。
>
> **精确机制**（取代三级降级）：
> - **子代理**：主控 `sessions_yield` 收到每个子代理 completion event 时，从 `Stats:` 行提取 in/out + prompt/cache 记入下表——**主控独占记录**，子代理无法也无需回传自己的 token
> - **主控自身**：T8 终检前用 `session_status({sessionKey: "current"})` 拿主会话精确值（含 cost）
> - **拿不到精确值 = 平台异常**（completion event 缺 Stats 行），不是填「未配置」

**主控收到每个子代理 completion 时填**（数据源 = completion event Stats 行）：

| 角色 | token 消耗（in / out） | 模型 | 记录人 |
|------|------------------------|------|--------|
| T1 文献 | `<tokens.in> / <tokens.out>` | `<model>` | 主控（completion Stats） |
| T2 数据 | `<tokens.in> / <tokens.out>` | `<model>` | 主控（completion Stats） |
| T3 案例 | `<tokens.in> / <tokens.out>` | `<model>` | 主控（completion Stats） |
| T4 分析 | `<tokens.in> / <tokens.out>` | `<model>` | 主控（completion Stats） |
| T5 写手 | `<tokens.in> / <tokens.out>` | `<model>` | 主控（completion Stats） |
| T6 批判 | `<tokens.in> / <tokens.out>` | `<model>` | 主控（completion Stats） |
| T7 审计 | `<tokens.in> / <tokens.out>` | `<model>` | 主控（completion Stats） |
| T9 评审 | `<tokens.in> / <tokens.out>` | `<model>` | 主控（completion Stats） |
| G14 检测 | `<tokens.in> / <tokens.out>` | `<model>` | 主控（completion Stats） |
| **主控自身** | `<session_status 查 main>` | `<model>` | T8 汇总 |
| **总计** | `<Σ>` | — | T8 汇总 |

**T8 终检汇总规则**：Phase 5 终检时主控把上表 Σ + session_status 主会话值 Σ 填入 `final/交付说明.md`「成本指标」字段，并在对话中向主人呈现：
```
## 本轮 token 成本（精确）
- 总计：<Σ> tokens（in <N> / out <M>）
- 子代理 Σ：<Σ_sub> tokens（含 prompt/cache）
- 主控自身：<session_status 主会话值> tokens + $<cost> cost
- 主要消耗：T5 写手 <N> / T7 审计 <N> / T9 评审 <N>
- 数据源：子代理完成事件 Stats 行 + session_status 工具（OpenClaw 9.1+）
```

---

## 五、执行韧化记录（主控/角色更新）

### 5.1 心跳记录

- 每个角色启动 30 秒内 + 每 5 分钟一次追加：`[心跳 HH:MM] role=<角色> model=<model-id>`

### 5.2 分阶段 ack（5-15 分钟任务必走 5 段）

- `[ack 0% HH:MM] <一句话进度>`
- `[ack 25% HH:MM] <进度>`
- `[ack 50% HH:MM] <进度>`
- `[ack 75% HH:MM] <进度>`
- `[ack 100% HH:MM] 完成`

### 5.3 模型降级记录

- `[降级 HH:MM] primary→fallback<N>, 原因=<ping超时/超时/其他>`

### 5.4 主控介入记录（如有）

- `[介入 HH:MM] session-kill/换模型/接受 partial, 说明=`

### 5.5 硬卡超时记录

- `[硬卡 HH:MM:SS] 超 <角色> 阈值 Xmin, kill + 接受 partial`（主控不允许「再等一下」）

### 5.6 失败记录（如有）

- `[失败 HH:MM] 角色=<角色>, 原因=<超时/上下文爆/其他>, 重派=N次`

### 5.7 修订回环记录

- 第 1 轮：P0 x / P1 x → 写手修订 → 审计复核：通过/未通过
- 第 2 轮：P0 x / P1 x → 写手修订 → 审计复核：通过/未通过（仍不过 → 升级主控）
- **G14 触发记录**：
  - 第 1 轮 G14 = Warning（3-4 类）→ 写手修订 1 轮
  - 第 2 轮 G14 = Fail（5+ 类）→ 写手修订 2 轮；第 2 轮仍命中 → 报告主人

### 5.8 项目历史记录归档

> **安全边界**：本节为"过期项目整理"的过程记录，**不涉及文件删除**。论衡工作流本身不执行任何 cleanup，所有"归档"动作由主人在论衡工作流外手动完成；本节仅记录"哪些项目已结题、已结题项目的素材是否被未来项目引用"。

- `[archive HH:MM] 项目 <名> 标记结题，结题产物路径 = <路径>，后续复用需主人在新项目任务简报中显式指定`
- `[reuse HH:MM] 项目 <新名> 引用 <旧名> 的 <素材类型>（已由主人在任务简报勾选授权）`

---

## 维护说明

- **方法论足迹**每阶段自动更新，无需主人手动维护
- **归档**：项目结束时由主控 T8 终检自动归档到 `run/<项目名>/audits/methodology-footprint-{项目名}.md`
- **借鉴 deep-research-pro 的方法论透明**（论衡化）——论衡不是简单复制竞品，而是把方法论足迹当成论衡哲学的一部分：诚实透明 + 主人随时看清进度 + 借鉴但不依赖
- **可选关闭**：主人在 Phase 0 可显式关闭方法论足迹（不强制启用）

---

## 重写说明（教训 #166）

**为什么重写**：
- 原 markdown 表格（7 列） + 主控 edit 频繁失败（空格漂移 / old_string 不匹配 / 重复行 bug）
- 实战口腔 AI + 论艺术中的丑两次项目，主控都遇到 status.md 维护成本过高

**怎么改**：
- 角色状态从「表格行替换」改为「key:value 文本替换」 → `**T5 写作**: ⬜ Inbox` → `**T5 写作**: ✅ Done` （一行一替换，零空格漂移）
- 闸门清单从「表格 checkbox」保留 checkbox 格式（仅打钩不修改内容）
- 产物路径从「表格行」改为「key:value」（路径在项目内不变）
- 方法论足迹从「表格」保留表格（实时数据有数字变化，主控用 row replace）

**向后兼容**：实战项目按新模板启动，旧 status.md 可手工迁移（把表格行拆为 key:value 文本）。
