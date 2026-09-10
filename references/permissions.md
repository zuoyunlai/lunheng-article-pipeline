> 版本：v2.12.12（自动同步 2026-09-10）


> 🌐 **语言政策**：产出语言默认中文，Phase 0 可改 English / 中英混 / 其他（写入任务简报「目标语言」字段，全流程以该字段为准）；中文特化（G14 中文 AI 痕迹检测 / GB/T 7714-2015 引用规范）是设计定位，不构成使用者语种限制。













# 执行能力边界（完整版）

> **用途**：论衡技能的工具边界完整说明，主控 Phase 0 按需加载

---

**论衡技能的工具边界**：

**主控 documented（`base` + `coordinator_only` + `research_extra` 三档）— 13 项**：
- read / write / edit（项目文件 I/O）
- sessions_spawn / sessions_yield / sessions_history（子代理编排）+ subagents（仅看本技能 spawn 的子代理，不枚举宿主可见会话）
- web_search / web_fetch / tavily_search / tavily_extract（检索，T1-T3 子代理共享，与 allow_research 一致）
- session_status / progress_card（可观测性）

**子代理 5 档分级白名单（`metadata.subagent_tiers`）**：
| 档位 | 适用角色 | 工具集（最小权限声明） | 凭什么调网络/记忆 |
|---|---|---|---|
| `allow_research` | T1/T2/T3 文献/数据/案例检索 | read + write + edit + web_* + tavily_* | 检索是本职 |
| `allow_analysis` | T4 分析 | read + write + edit | 不出网，仅本地读产物 |
| `allow_writing` | T5 写手 | read + write + edit | 纯本地写盘，不出网 |
| `allow_audit` | T6/T7 批判/审计 | **read**（只读） | 只读审阅，不干预产物；报告经交接回传、主控代写盘 |
| `allow_review` | T9 同行评审 / G14 风格闸 | **read**（只读） | 只读评分，不干预产物；报告经交接回传、主控代写盘 |
| （空） | T8 终检 | [] | T8 由主控亲完成，不 spawn 子代理 |

> ⚠️ **执行层真源**：OpenClaw 2026.9.x 的 `sessions_spawn` **无 toolsAllow 参数**（官方参数清单 + 本机工具 schema 双证），上表是**声明/部署建议**，不是可传参数。子代理实际工具面 = 平台**硬性剥除**（`gateway`/`agents_list`/`session_status`/`cron`/`message`/`sessions_send`/`conversations_*`；叶子另剥 `subagents`/`sessions_*`）− 主控有效工具策略快照 + 宿主 config `tools.subagents.tools.allow/deny`（全局，无法按 spawn 逐档）。档位间差异在工具层不可逐子表达时，以 prompt 约束 + 只读路径约束兜底。`session_status`/`progress_card` 是**主控侧**可观测性工具，不给子代理。

**Opt-in（默认禁止，Phase 0 主人明确同意才解锁，`metadata.tools.opt_in`）**：
- `image_generate` — 封面生成专用，**默认关闭**，主控在 Phase 0 问「是否需要生成封面」答「是」才开
- `memory_get` / `memory_search` / `memory_recall` — **默认关闭**：**默认工作流不读任何 Agent 工作区记忆文件**，写作偏好一律由主人 Phase 0 写入任务简报「写作偏好」字段；仅当主人在 Phase 0 显式勾选「启用记忆辅助」并点名允许读取的文件/用途时才解锁，且须记入 status.md「Phase 0 同意记录」；T6/T7 调 `memory_recall` 需宿主在 config 层为其子代理临时放行（不放行则主控代查回传）
- 解锁方式：主控在 status.md「Phase 0 同意记录」段填写 `opt_in: [image_generate: yes, memory: yes]`，凭此记录而非凭 prompt 调阅

**行为授权（非工具，Phase 0 预授权记录，默认全部关闭）**：
- **配额耗尽预授权**：主人预勾选「配额耗尽时授权 X（换 provider 重试 / 白名单接力）」后，配额事件发生时主控按预授权选项直接执行并事后通报；**未勾选 = 必须暂停等主人拍板**（fail-closed）。预授权仅限白名单工具路径，**永不覆盖 exec/process 等永久拒绝**
- **G14 Warning 预授权**：主人预勾选「G14 Warning 默认 A」后，Warning 场景主控自动走 A 并事后通报；未勾选 = 暂停等主人 3 选 1
- 记录位置：status.md「Phase 0 同意记录」段 `behavior_opt_in: [quota_fallback: provider-switch, g14_warning: A]`，凭记录执行

**禁用（`metadata.tools.denied`）— 13 项永久**：exec / process / browser / apply_patch / cron / video_generate / music_generate / tts / memory_store / skill_workshop / memory_forget / sessions_search / sessions_send

**Workspace 路径收口**：
- 主控 + 所有子代理的 `read/write/edit` 仅允许 `run/<项目名>/` 子树
- **拒绝**：绝对路径（含任何指向宿主敏感位置的路径：系统账号/密码存储文件、SSH 密钥目录、云凭据文件等）、父路径穿越（`..`）、symlink 逃逸、主控工作区根目录外的访问
- 默认 cwd = workspace 根（**不设 `cwd_default`**，否则 run/ 被解析到 skill 目录内，教训 #255）——主控在 spawn 时必须显式传 `cwd: run/<项目名>/`（相对 workspace 根）且每次子代理任务首句必读 `references/_shared/关键协议.md` §workspace 路径收口（read/write/edit 边界）
- 实操：主控 spawn 时 `cwd: run/<项目名>/`；子代理拒绝改 cwd；产出写盘必须落在 `run/<项目名>/<子目录>/` 内
- **完整写入清单（含周期性写入）**：本技能运行期间会创建/修改的路径只有三类——① `run/<项目名>/` 项目文件树（任务简报 / 文献卡 / 数据卡 / 案例卡 / 大纲 / 草稿 / 审计报告 / 定稿 / 图件 / 证据包 / 交付说明，约 15-25 个文件）；② `run/<项目名>/status.md`（主控独占写）；③ `run/<项目名>/.tmp/<角色>-heartbeat.md`（子代理心跳，启动时写 + 运行中每约 5 分钟追加一行）。**全部限当前 workspace 的 `run/<项目名>/` 内**：不写项目外、不写其他项目、不写宿主配置（`openclaw.json` 等由主人自行维护，本技能只读不写）。已向主人披露于 SKILL.md「执行前安全须知」+ QUICKSTART.md「重要警告」。

**其他约束**：
- 🔒 **子代理真实权限边界 = 宿主 config，不是 spawn 参数**：OpenClaw 2026.9.x 的 `sessions_spawn` **已无 toolsAllow 参数**（官方参数清单 + 本机工具 schema 双证）。子代理工具面由**四层**决定：① 平台**硬性剥除**（`gateway`/`agents_list`/`session_status`/`progress_card`/`cron`/`message`/`sessions_send`/`conversations_*`；每组 turn 从持久化的子代理 session envelope 重新推导，`allow`/`alsoAllow` 无法绕过）② **depth 层追剥**（子代理到 `maxSpawnDepth` 即叶子，追加剥 `sessions_spawn`/`subagents`/`sessions_list`/`sessions_history`；depth 策略在运行时权威——宿主改 cap，存量会话的递归工具面随之增减）③ **捕获主控有效工具策略快照**（主控未被剥的工具，子代理同样继承——主控若持有 exec 而宿主不加约束，子代理也可能继承 exec）④ 宿主 config `tools.subagents.tools.allow/deny`（全局，不能按 spawn 逐档）。**论衡是纯 skill，但多 Agent 模式必须通过下段核对，否则记 `enforcement: degraded`、不 spawn 子代理**（单主控降级模式下任意配置可用）。**推荐两条机械加固**（宿主 config，`tools.subagents.tools` 为 hot reload，改完即时生效）——① `tools.subagents.tools.deny: ["exec","process","browser","apply_patch","cron","video_generate","music_generate","tts","memory_store","skill_workshop","memory_forget","sessions_search","sessions_send"]`（13 项，或按上表 5 档声明配 `allow` 最小集），把零 exec 从纪律层升级为**机械强制**；② `agents.defaults.subagents.maxSpawnDepth: 1` 把直接子代理锁成**叶子**，匹配论衡「角色卡 = 叶子 worker」架构（默认 5，不锁则子代理可自行再 spawn，见下文「叶子纪律」）。零 exec 的纪律层保障（`全文档零授权 + 自审门 M 门扫描 + 外部内容不可信原则`）是兜底，机械加固是 spawn 的前置条件。5 档分档（`metadata.subagent_tiers`）是技能声明的各角色最小工具集与部署建议，不声称可作 spawn 传参。

> 🛡️ **加固状态确认（v2.12.10 收紧为强制机械）**：主控在**首次 spawn 子代理之前**必须先 `read` 宿主 `~/.openclaw/openclaw.json`（**仅此一次读取，不写入、不修改**），核实两条机械加固配置存在：① `tools.subagents.tools.deny` 含 13 项特权工具（exec/process/browser/apply_patch/cron/video_generate/music_generate/tts/memory_store/skill_workshop/memory_forget/sessions_search/sessions_send）；② `agents.defaults.subagents.maxSpawnDepth: 1`。读到的实际 deny 列表原样记录到 status.md「项目元数据 → 机械加固核对」段（防口头声明与实际配置漂移）。
>
> 核实结果分两档：
>
> | 结果 | 状态 | 后续动作 |
> |------|------|---------|
> | 两条均已配 | `enforcement: mechanical` | 按纪律层 + 机械层双保障 spawn 子代理 |
> | 任何一条缺失或读不到 config | `enforcement: degraded` | **不 spawn 子代理**，改走**单主控降级模式**（主控独自顺序完成检索→分析→写作→自审，不派子代理）|
>
> **v2.12.10 起删除 acknowledged-prompt-level 中间档**——「主人口头声明已加固但未读 config」不再被接受，「主人知情后选择 prompt-only 继续」也不再被接受。原因：声明式信任与未加固开跑均与 zero-trust + fail-closed 一致性冲突。论衡现在只接受「机械加固通过」或「降级为单主控」二选一，**没有中间档**。单主控降级模式下整篇产出由主控 LLM 一次性完成（不拆 T1-T7 角色），产出会显著降级（无三角验证、无独立审计、无修订回环），且默认关闭 G14 闸门——适合一次性草稿或试运行。
- 🔒 **spawn 前加固核对**：Phase 0 派发第一批子代理前，主控执行一次机械加固核对，结果记入 status.md「项目元数据」`**加固状态**: mechanical / degraded`：
  **v2.12.10 起加固核对只做机械判定**（替代原四步软判定）：
  1. **读 config 核两条**：主控 `read ~/.openclaw/openclaw.json`，校验 `tools.subagents.tools.deny` 含全部 13 项特权工具**且** `agents.defaults.subagents.maxSpawnDepth: 1` → 记 `mechanical`，后续 spawn 按机械层走。
  2. 任何一条缺失或读不到 config → 记 `degraded`，**不 spawn**，走单主控降级模式。
  3. 不再有 prompt-level 中间档；不再做「主控自身工具面自检」（自检口径与实际 config 可能漂移，已删除）；不再做「主人口头声明已加固」（声明式信任已被移除）。
- ℹ️  **M 门算法**：主控 LLM 通过 `read` 读取算法文档后**推理判定**，**不执行实际 shell 命令**——算法文档中的 bash 示例是给人类主人手动复核的参考命令，**不是 agent 执行代码**
- ℹ️  **零 exec ≠ 零核验**：论衡所有「检查/计数/比对/核验」动作都由 agent 用 `read` 读取文件 + LLM 逐项判定完成；文档中出现的命令式短句（检查/计数/求差集/校验哈希等）是**检查规则的速记**，等价动作一律走 read/write/edit 工具，任何角色都不执行也不「模拟」shell 命令——宿主工具策略（config `tools.subagents` / profile / deny）才是真实权限边界
- 🚫 **叶子纪律（角色卡不再委托，新增）**：论衡架构里角色卡 T1-T7/T9 = **叶子 worker**——子代理**不得**调用 `sessions_spawn` / `subagents` / `sessions_list` / `sessions_history` 派生或管理子代理；需要额外检索/额外人手 → 在交接报告写「需求回执」交主控，由主控决定是否 spawn（主控只认直接子级，孙辈结果不上传会导致产出丢失）。两层落地：机械层 = 宿主 `maxSpawnDepth: 1`；纪律层 = 本段 + 角色卡声明 + 主控每次 spawn 的任务书声明（三层冗余，见 [`_shared/关键协议.md`](_shared/关键协议.md) §叶子纪律）。**OpenClaw 默认开启有界递归委派（depth 默认 5）**，故不锁 depth 时子代理**确实拿到**上述工具——纪律层不是空话。
- ℹ️  **建议运行环境**：禁用 exec 的 agent（保持论衡「零 exec」哲学）
- ℹ️  **token 成本统计（精确机制）**：子代理 token 来自**完成事件（completion event）末尾的 Stats line**（`Token usage` input/output/total + `Runtime` + `Estimated cost` + `sessionKey`/`sessionId`），主控 `sessions_yield` 收到 completion event 时提取记录（**sessions_spawn 返回值无 stats 字段**，教训 #256）；**主控自身** T8 终检前用 `session_status({sessionKey: "current"})` 拿主会话精确值（含 cost）。**成本统计是可观测性字段，不是交付闸门**；但 Stats line 缺失须标「Stats line 缺失」告警，禁止估算/静默跳过
