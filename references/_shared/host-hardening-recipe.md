> 版本：v2.12.27（自动同步 2026-09-11，纳入 v2.12.27 批）

> 🌐 **语言政策**：产出语言默认中文；本文为宿主侧配置建议（可选），不随语言切换而变。

# 可选宿主加固配方（机械级权限边界）

> **性质：可选、非前提。** 论衡仍是**纯 skill** —— **任意 OpenClaw 配置开箱可用**，不要求、也不附带任何宿主配置，**不读取、不修改**宿主配置，也不对宿主的权限设定作任何前提假设。
> **本文给的是「想更进一步」的宿主**：把论衡的**声明式**五档白名单，升级为**平台机械强制**的权限边界。**不做这些配置，论衡照常运行**（只是档位靠 agent 侧自律 + 自检可观测）。
> ⚠️ **配置风险自负**：配错可能导致子代理**拿不到所需工具**或**无法 spawn**；本文只给建议，**论衡不校验、不代改、不报错**。改前请先 `openclaw doctor`，改后用 `openclaw sandbox explain` 与 `/tools` 核对。

## 一、为什么需要这份配方（问题陈述）

论衡的五档白名单（research / analysis / writing / audit / review）是**声明/部署建议**——因为 `sessions_spawn` **没有** `toolsAllow` 参数（子代理实际工具面由平台剥除 + 主控策略快照 + 宿主配置共同决定）。因此**默认情况下档位靠提示词自律**。

OpenClaw 提供了**三条机械路径**可把档位真正锁死。

## 二、配方 1：叶子纪律 → 机械强制（`maxSpawnDepth`）

论衡要求 T1-T9/G14 **不得再 spawn**（叶子 worker）。平台按**深度**剥除编排工具：

| 位置 | 拿到的编排工具 |
|---|---|
| Orchestrator（低于 `maxSpawnDepth`） | `sessions_spawn` / `subagents` / `sessions_list` / `sessions_history` |
| **Leaf（到达 `maxSpawnDepth`）** | **没有递归编排工具**（机械剥除） |

```json5
{
  agents: {
    defaults: {
      subagents: {
        maxSpawnDepth: 1,        // 论衡的主控在 depth 0；子代理 depth 1 → 机械成叶子
        maxChildrenPerAgent: 5,  // 每会话最多 5 个活动子代理（论衡并行最多 3）
        maxConcurrent: 8,        // 全局并发上限
      },
    },
  },
}
```

> **效果**：主控（depth 0）能 spawn；所有 T 角色（depth 1）**机械拿不到** `sessions_spawn` / `subagents` / `sessions_*`。论衡的「叶子纪律」从提示词升级为平台强制。
> **代价**：宿主若还想让其它 skill 做**多层嵌套**委派，会被这条限制（可改为按 agent 分别配置）。

## 三、配方 2 + 3：五档 → 按 agent 分档 + 按档 spawn

平台支持**按 agent 定义工具策略**，并允许 `sessions_spawn` 用 `agentId` **spawn 到指定 agent**（需 `subagents.allowAgents` 放行）。

```json5
{
  agents: {
    entries: {
      // 论衡主控（现有 agent 即可）——需放行可 spawn 的目标
      "main": {
        subagents: { allowAgents: ["lh-research", "lh-analysis", "lh-writing", "lh-audit", "lh-review"] },
      },
      "lh-research": { tools: { allow: ["read", "write", "edit", "web_search", "web_fetch", "tavily_search", "tavily_extract"] } },
      "lh-analysis": { tools: { allow: ["read", "write", "edit"] } },
      "lh-writing":  { tools: { allow: ["read", "write", "edit"] } },
      "lh-audit":    { tools: { allow: ["read"] } },   // T6/T7 只读
      "lh-review":   { tools: { allow: ["read"] } },   // T9/G14 只读
    },
  },
  tools: { deny: ["exec", "process", "browser", "terminal", "secrets", "gateway", "automations", "apply_patch"] },
}
```

**主控侧配合**：spawn 时按档传 `agentId`：

| 档位 | 角色 | `agentId` |
|---|---|---|
| research | T1 / T2 / T3 | `lh-research` |
| analysis | T4 | `lh-analysis` |
| writing | T5 | `lh-writing` |
| audit | T6 / T7 | `lh-audit` |
| review | T9 / G14 | `lh-review` |
| — | T8 终检 | **不 spawn**（主控亲完成） |

> **效果**：档位差异从「提示词声明」变成**平台工具策略**——`lh-audit` 的只读、`lh-research` 的检索权限都由宿主配置强制。
> **代价**：需要多维护 5 个 agent entry（各自的 workspace 引导文件、模型等）。若只想要叶子纪律，**配方 1 就够了**。

## 三·补 配方 4：保住引用标识符（上下文压缩）

论衡的引用体系是**不透明标识符**（`[Lxx]` / `[Dxx]` / `[Cxx]` / `[图N]`），而 M 门 / G 项靠读文本对账。平台自动压缩**默认保全**它们，但可被关闭：

- ❌ **不要**把压缩的 `identifierPolicy` 设为 `"off"`。
- ⚠️ 若使用**自定义压缩 provider**，必须在其汇总实现中保全上述标识符 —— 平台不会替你检查。
- （可选）开启活跃 transcript 字节守卫与压缩前记忆冲刷，降低长跑上下文压力。

> 论衡已把一切关键状态**落盘**（`status.md` / `run/<项目名>/`）—— **磁盘产物不受压缩影响**，这是主要防线；本条是补充。

## 三·补 配方 5：会话权限模式与文件系统边界

平台提供**会话权限模式**（`read-only` / `guarded` / `workspace` / `full`）与 **`sessionRoot` 文件系统边界**（机械强制）：

| 论衡档位 | 建议权限模式 | 效果 |
|---|---|---|
| audit / review（T6 / T7 / T9 / G14） | `read-only` | **机械只读**：变更类工具被平台**省略**，exec 被拒 |
| analysis / writing（T4 / T5） | `guarded` 或 `workspace` | 限 `sessionRoot` 内读写 |
| research（T1 / T2 / T3） | `guarded` + 放行检索工具 | 同上 + 网络工具 |

配合 `sessionRoot`（或显式 cwd）指向 `run/<项目名>/`，可获得**平台级路径 containment**（含 symlink 逃逸拦截）—— 比第①层的"提示词拒绝绝对路径/父穿越"更强。

> ⚠️ 权限模式与会话绑定，**不是每次 spawn 都能逐档指定**；以官方文档与实际会话结构为准。`full` 需 `operator.admin`。
## 三·补 配方 6：让子代理活动对主人可见（渠道 progress 草稿）

论衡一次长跑会 spawn 多个角色（T1∥T2∥T3 → T4 → T5 → …）。默认情况下**主人只看到主控的阶段级进度**（`progress_card` 侧栏 + `status.md`），而**子代理的活动写在磁盘心跳里，主人看不到**。

平台提供**渠道级进度草稿**：`channels.<channel>.streaming.mode: "progress"` —— 一条消息**原地编辑**、实时更新，且**原生把子代理 spawn / 活动事件变成一行**（每个 worker 复用一行；「给 worker 发消息」单独成条，因为**发消息 ≠ worker 已启动**）。

```json5
{
  channels: {
    telegram: { streaming: { mode: "progress" } },   // Telegram 默认即 progress
    discord:  { streaming: { mode: "progress" } },   // Discord 需显式开（默认 off）
  },
}
```

- **收益**：主人能实时看到「T1 搜索中 / T5 写作中」等 worker 级活动，**论衡零改动**。
- 相关旋钮：`progress.toolProgress`（默认 `false`，开了才有滚动工具日志）/ `progress.maxLines`（默认 `8`）/ `progress.commentary`（注释泳道，默认 `false`）。
- ⚠️ **开启后注意去重**：渠道已有实时草稿时，`progress_card` **只作侧栏总览**，不要在正文重复贴进度（见 `templates/checkpoint-card-template.md`「progress_card 联动规范」）。
- 官方依据：`docs/concepts/progress-drafts.md`。

## 四、验证与诊断

```bash
openclaw doctor                 # 先查配置合法性
openclaw sandbox explain        # 看某会话实际生效的 sandbox / 工具 allow-deny 来源
# 会话内： /tools              # 确认当前会话实际可用工具面
```

论衡侧的对应自检（**不需要宿主配置也能跑**）：`references/permissions.md`「能力自检」+ `references/_shared/dispatch-header.md`「启动自检」——子代理首步核验自身工具面，越权即回报 `capability_excess`。

## 五、边界声明（重要）

- 本文**不是**论衡的运行前提；**不做任何配置，论衡照常工作**。
- 论衡**不读取、不修改、不校验**宿主配置；本文只是「给人看的建议」。
- 论衡**不能**代替宿主做权限裁决；宿主配置错误导致的行为（工具缺失 / spawn 被拒 / 越权），属**宿主侧责任**。
- 本配方随 OpenClaw 版本而变（键名/默认值可能调整）——**以官方文档为准**：`docs/tools/subagents.md`、`docs/gateway/config-tools.md`、`docs/gateway/sandbox-vs-tool-policy-vs-elevated.md`。
