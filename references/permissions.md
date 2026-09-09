> 版本：v2.11.0（自动同步 2026-09-09）


# 执行能力边界（完整版）

> **用途**：论衡技能的工具边界完整说明，主控 Phase 0 按需加载

---

**论衡技能的工具边界（v2.6.5 分层最小权限，回应 ClawHub A.I.G T05 + SkillSpector 6 findings）**：

**主控 documented（`metadata.tools.declared`）— 13 项**：
- read / write / edit（项目文件 I/O）
- sessions_spawn / sessions_yield / sessions_history（子代理编排）+ subagents（v2.7.8 起替代 sessions_list：宿主强制 self-spawn 列表，仅看本技能 spawn 的子代理，不枚举宿主可见会话）
- web_search / web_fetch / tavily_search / tavily_extract（检索，T1-T3 子代理共享；v2.7.7 声明补全 web_fetch——中文数据源第一梯队 OpenAlex/Crossref 拉 JSON 用，与 allow_research 一致）
- session_status / progress_card（可观测性）

**子代理 5 档分级白名单（v2.6.5 新增；v2.7.12 起定位为「各角色最小工具集声明」，`metadata.subagent_tiers`）**：
| 档位 | 适用角色 | 工具集（最小权限声明） | 凭什么调网络/记忆 |
|---|---|---|---|
| `allow_research` | T1/T2/T3 文献/数据/案例检索 | read + write + edit + web_* + tavily_* | 检索是本职 |
| `allow_analysis` | T4 分析 | read + write + edit | 不出网，仅本地读产物 |
| `allow_writing` | T5 写手 | read + write + edit | 纯本地写盘，不出网 |
| `allow_audit` | T6/T7 批判/审计 | **read**（只读） | 只读审阅，不干预产物；报告经交接回传、主控代写盘（v2.7.2） |
| `allow_review` | T9 同行评审 / G14 风格闸 | **read**（只读） | 只读评分，不干预产物；报告经交接回传、主控代写盘（v2.7.2） |
| （空） | T8 终检 | [] | T8 由主控亲完成，不 spawn 子代理 |

> ⚠️ **执行层真源（v2.7.12）**：OpenClaw 2026.9.x 的 `sessions_spawn` **无 toolsAllow 参数**（官方参数清单 + 本机工具 schema 双证），上表是**声明/部署建议**，不是可传参数。子代理实际工具面 = 平台**硬性剥除**（`gateway`/`agents_list`/`session_status`/`cron`/`message`/`sessions_send`/`conversations_*`；叶子另剥 `subagents`/`sessions_*`）− 主控有效工具策略快照 + 宿主 config `tools.subagents.tools.allow/deny`（全局，无法按 spawn 逐档）。档位间差异在工具层不可逐子表达时，以 prompt 约束 + 只读路径约束兜底。`session_status`/`progress_card` 是**主控侧**可观测性工具，不给子代理。

**Opt-in（默认禁止，Phase 0 主人明确同意才解锁，`metadata.tools.opt_in`）**：
- `image_generate` — 封面生成专用，**默认关闭**，主控在 Phase 0 问「是否需要生成封面」答「是」才开
- `memory_get` / `memory_search` / `memory_recall` — **默认关闭**（v2.7.9 集中授权制）：**默认工作流不读任何 Agent 工作区记忆文件**，写作偏好一律由主人 Phase 0 写入任务简报「写作偏好」字段；仅当主人在 Phase 0 显式勾选「启用记忆辅助」并点名允许读取的文件/用途时才解锁，且须记入 status.md「Phase 0 同意记录」；T6/T7 调 `memory_recall` 需宿主在 config 层为其子代理临时放行（v2.7.12：OpenClaw 2026.9.x spawn 无 per-run 工具参数；不放行则主控代查回传）
- 解锁方式：主控在 status.md「Phase 0 同意记录」段填写 `opt_in: [image_generate: yes, memory: yes]`，凭此记录而非凭 prompt 调阅

**行为授权（非工具，Phase 0 预授权记录，默认全部关闭，v2.6.6 新增回应 T05/G14 审计）**：
- **配额耗尽预授权**：主人预勾选「配额耗尽时授权 X（换 provider 重试 / 白名单接力）」后，配额事件发生时主控按预授权选项直接执行并事后通报；**未勾选 = 必须暂停等主人拍板**（fail-closed）。预授权仅限白名单工具路径，**永不覆盖 exec/process 等永久拒绝**
- **G14 Warning 预授权**：主人预勾选「G14 Warning 默认 A」后，Warning 场景主控自动走 A 并事后通报；未勾选 = 暂停等主人 3 选 1
- 记录位置：status.md「Phase 0 同意记录」段 `behavior_opt_in: [quota_fallback: provider-switch, g14_warning: A]`，凭记录执行

**禁用（`metadata.tools.denied`）— 13 项永久**：exec / process / browser / apply_patch / cron / video_generate / music_generate / tts / memory_store / skill_workshop / memory_forget / sessions_search / sessions_send

**Workspace 路径收口（v2.6.5 新增，回应 SkillSpector 「非声明主机访问」）**：
- 主控 + 所有子代理的 `read/write/edit` 仅允许 `run/<项目名>/` 子树
- **拒绝**：绝对路径（如 `/etc/passwd`<!-- safe-pattern: doc-example, 路径在「拒绝」清单里非真实访问 -->、`~/.ssh/`<!-- safe-pattern: doc-example, 同上 -->）、父路径穿越（`..`）、symlink 逃逸、主控工作区根目录外的访问
- cwd_default 仅是路径提示，**不是沙箱保证**——主控在 spawn 时必须显式传 `cwd: run/<项目名>/` 且每次子代理任务首句必读 `references/_shared/关键协议.md` §workspace 边界
- 实操：主控 spawn 时 `cwd: run/<项目名>/`；子代理拒绝改 cwd；产出写盘必须落在 `run/<项目名>/<子目录>/` 内

**其他约束**：
- 🔒 **子代理真实权限边界 = 宿主 config，不是 spawn 参数（v2.7.12 修正 v2.6.1 旧表述；v2.10.1 重申主人 v2.7.13 拍板）**：OpenClaw 2026.9.x 的 `sessions_spawn` **已无 toolsAllow 参数**（官方参数清单 + 本机工具 schema 双证）。子代理工具面由三层决定：① 平台**硬性剥除**（`gateway`/`agents_list`/`session_status`/`progress_card`/`cron`/`message`/`sessions_send`/`conversations_*`；叶子另剥 `subagents`/`sessions_list`/`sessions_history`/`sessions_spawn`）② **捕获主控有效工具策略快照**（主控未被剥的工具，子代理同样继承——主控若持有 exec 而宿主不加约束，子代理也可能继承 exec，**无法**机械保证零 exec）③ 宿主 config `tools.subagents.tools.allow/deny`（全局，不能按 spawn 逐档）。**论衡是纯 skill（主人 v2.7.13 拍板），任意 OpenClaw 配置开箱可用**——本机宿主 config **不作任何强制收紧要求**：config 只对本机生效，不会随 ClawHub 净化包分发；论衡定位是「说明书」不是「独立 agent」，任意具备 `sessions_spawn` + 检索工具的 OpenClaw agent 加载即可运行。**宿主若需 exec 硬隔离可自行加 `tools.subagents.tools.deny`**（`[exec, process, browser, apply_patch, ...]` 或按 5 档声明配 allow 最小集），但论衡**不做**强制前置要求。零 exec 是纪律层软保障（`全文档零授权 + 自审门 M 门扫描 + 外部内容不可信原则`），非机械强制。5 档分档（`metadata.subagent_tiers`）是技能声明的各角色最小工具集与部署建议，不再声称可作 spawn 传参。**论衡 v2.6.5→v2.6.9 五轮 ClawHub 扫描 CLEAN 是设计表述被认可的实证**：靠的是 SKILL.md 文本层明确表达（禁用 13 项 + fail-closed + 全文档零授权 + 跨文件证据链），扫描器读 SKILL.md 时认可设计表达。**v2.10.1 口径**：本机宿主 config 不作任何强制收紧要求（config 只对本机生效不进净化包）；设计表述上仍坚持「零 exec 纪律层 + 全文档零授权 + fail-closed」，**不**声称机械强制，**不**声称扫描器会自动给 Pass——扫描结果由 ClawHub 扫描器在每次 publish 时判定。
- 🔒 **运行前软保障自检（v2.7.14 新增，v2.10.1 移除三态确认流程——主人 v2.7.13 拍板：不拒绝运行 + 任意配置可用）**：Phase 0 派发第一批子代理前，主控执行一次软保障判定，结果记入 status.md「项目元数据」`**软保障**: mechanical / prompt-level`：
  1. **自查主控工具面**：主控自身不含 `exec/process/browser/apply_patch`（已被宿主策略剥除/deny）→ 子代理继承面必不含这些特权工具（教训 #202：子代理工具面 = 平台硬剥 + 主控策略快照 − 宿主 config deny），机械层成立 → 记 `mechanical`，无需额外确认。
  2. 主控自身持有上述特权工具 → 子代理是否被宿主 `tools.subagents.tools.deny` 机械拦截**无法从技能侧证明**（技能无宿主 config 读取面）→ 记 `prompt-level`（论衡纪律层软保障），**不拒绝运行**——论衡是纯 skill，配置收紧是宿主可选机械加固，不是运行前置条件（主人 v2.7.13 拍板接受软保障）。
  3. 未 deny 或不确定 → 主人确认接受后记 `prompt-level`（软保障运行：零 exec 靠纪律层——全文档零授权 + 角色卡约束 + M 门扫描 + 外部内容不可信原则，非机械强制）；**不拒绝运行**——纯 skill 定位：任意 OpenClaw 配置可用，config 收紧是宿主可选机械加固而非运行前置。
  4. 每次 spawn 前主控复核该标记；`prompt-level` 时任务简报/交接报告附「特权工具可能可及，严守零 exec 纪律」提醒（角色卡已含零授权约束）。
- ℹ️  **M 门算法**：主控 LLM 通过 `read` 读取算法文档后**推理判定**，**不执行实际 shell 命令**——算法文档中的 bash 示例是给人类主人手动复核的参考命令，**不是 agent 执行代码**（回应 SkillSpector 「models list 命令执行」指控，v2.6.5 改走 `session_status` / `read` 元数据自查）
- ℹ️  **零 exec ≠ 零核验（v2.7.9 明示）**：论衡所有「检查/计数/比对/核验」动作都由 agent 用 `read` 读取文件 + LLM 逐项判定完成；文档中出现的命令式短句（检查/计数/求差集/校验哈希等）是**检查规则的速记**，等价动作一律走 read/write/edit 工具，任何角色都不执行也不「模拟」shell 命令——宿主工具策略（config `tools.subagents` / profile / deny）才是真实权限边界
- ℹ️  **建议运行环境**：禁用 exec 的 agent（保持论衡「零 exec」哲学）
- ℹ️  **token 成本统计（v2.6.1 重写，精确机制）**：OpenClaw 9.1 提供 `sessions_spawn` 返回值 stats（含 `tokens.in/out` + `prompt/cache` 字段） + `session_status` 工具。**子代理**：若宿主在 spawn 回执提供精确 stats，主控记录并在交接报告中回传；未提供时记录 `unavailable`。**主控自身**：T8 终检前用 `session_status({sessionKey: "current"})` 拿主会话精确值（含 cost）。**成本统计是可观测性字段，不是交付闸门**：禁止估算
