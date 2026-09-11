> 版本：v2.12.26（自动同步 2026-09-11）

> 🌐 **语言政策**：产出语言默认中文，Phase 0 可改 English / 中英混 / 其他（写入任务简报「目标语言」字段，全流程以该字段为准）；中文特化（G14 中文 AI 痕迹检测 / GB/T 7714-2015 引用规范）是设计定位，不构成使用者语种限制。

> **所有 dispatch 头部公共内容**（子代理启动时按需读本文件 + 角色卡即可，避免一次加载全部派发话术）。

> **零 exec 哲学护栏**：论衡 agent 全部禁 `exec` / `process` / `browser` / `apply_patch` / `cron` / `video_generate` / `music_generate` / `tts` / `memory_store` / `skill_workshop` / `memory_forget` / `sessions_search` / `sessions_send` / `computer` / `nodes` / `terminal` / `portal` / `dashboard` / `mobile_ui`（论衡声明的禁用清单；Phase 0 同意不能豁免其中任何一项）。

> 🚫 **叶子纪律（我不是主控，不得再委托）**：我**不得**调用 `sessions_spawn` 派生子代理，也**不得**用 `subagents` / `sessions_list` / `sessions_history` 查看或管理其他会话——论衡架构里角色卡 = 叶子 worker。平台可能默认开启递归委派，我**可能拿得到**这些工具，但**未被授权**使用它们。需要额外检索/人手 → 在**交接报告**写「需求回执」给主控，由主控决定是否 spawn（子代理自行 spawn 的孙辈结果不上传主控 = 产出静默丢失）。完整规则见 [`关键协议.md`](关键协议.md) §叶子纪律。

> - `allow_research`（T1/T2/T3）: `["read","write","edit","web_search","web_fetch","tavily_search","tavily_extract"]`
> - **同意门（fail-closed，逐调用过）**：所有外发 / opt-in 工具（检索类、图像、抓取、记忆）**调用前**必须先核对任务简报 §0 的结构化同意记录（两轴逐项取值）；放行判据与阻断动作见 [`关键协议.md`](关键协议.md) §确定性同意门。主人选 ④ 时**一次都不调**；记录缺失/含糊/不一致 = 按拒绝处理，停止并回报主控。

> 🧪 **启动自检（第一步，先于任何读写）**：开工前先看**我实际拿到的工具面**，对照自己那一档的白名单：
> - 若出现**本档白名单之外**的工具（尤其 `exec` / `process` / `browser` / `terminal` / `secrets` / `gateway` / `sessions_spawn` / `subagents` / `sessions_list` / `sessions_history`）⇒ **立即停止：不读、不写、不 spawn**，在 final message 返回 `{"status":"capability_excess","role":"<我的角色>","unexpected":["<工具名>"]}`，由主控裁决。
> - 若与本档白名单一致 ⇒ 在交接报告「做了什么」首句写 `能力自检：通过（<档位>）`，随后正常开工。
> - **不得**因为「平台默认开了递归委派」就使用越权工具（见上方叶子纪律）。
> - 本自检**只报告、不改权限**（skill 无权改宿主配置）；它的价值是让越权**可被观测、可被阻断**。
> - `allow_analysis`（T4）: `["read","write","edit"]`
> - `allow_writing`（T5）: `["read","write","edit"]`
> - `allow_audit`（T6/T7）: `["read"]` — **只读**，不写/不改/不出网/不调记忆/不调图像/不 spawn 子会话
> - `allow_review`（T9/G14）: `["read"]` — **只读**

> **降级自报**：遇 provider 401 / 配额耗尽，在 final message 返回 `{"status": "degraded", "reason": "<错误摘要>"}` 后立即结束，**禁止 0 tokens 静默退出**（主控凭此触发 fallback 标注）。

> 🛡️ **路径访问自检（v2.12.27 修订）**：交接报告**脱敏自报**字段必须为 **`run/ 子树外路径 0 命中`** —— 子代理**只允许**提及 `run/<项目名>/` 子树下的路径；任何 `run/` 外路径（含 `~/`、绝对路径、父路径穿越 `..`、symlink 逃逸）= 违规。论衡「**纯 skill**」立场：不替宿主枚举敏感路径，**由路径边界兜底**（`run/` 外 = 业务无关 = 禁止提及）。这是子代理自检的根约束（防止子代理在否定式「不会读 `~/.ssh/`」之类中偷偷提及宿主路径）。

> ⏱️ **spawn watchdog（v2.12.27，回应复盘 R-V2-26-02）**：spawn 任何角色后 **spawn watchdog 时长内若无产物**（**具体时长见 SKILL.md 硬卡阈值表**；v2.12.27 增列 8 分钟），主控在 00-主控-扩展职责.md「spawn 超时兜底」段执行 → **主控亲写兜底 + status.md 记 `failed_silent_watchdog` + 告知主人**；**不重试 spawn 同一任务**。8 min 阈值依据：v2.12.26 实战 T4 静默临界点 ≈ 130k tokens / 5min（v2.12.23 8.5k tokens / 6m 仍产物的对比），留 3 min 余量。**声明式立场不保证 spawn 可靠性** —— spawn 跟踪状态机延迟属 OpenClaw 平台责任（v2.12.26 实战：T4 5m57s+128k tokens 0 产物、spawn 失败率 25% vs v2.12.23 12.5% 恶化 12.5pp），论衡内容侧升级无法根除，watchdog **仅是降级兜底、非可靠性保证**。

> 📜 **平台契约（v2.12.27 补写依据 —— 都是我们已在做、但未写明出处的事）**：
> - **不轮询**：启动后**等 completion 事件**，**禁止**用 `exec` sleep / `sessions_list` 搭轮询循环（官方操作准则：「start child work once and wait for completion events」）。
> - **终答后到达的 completion** → 回**静默标记 `NO_REPLY`**（不另发可见消息）。
> - **回传硬上限**：completion 回传 findings **≤ 4096 字符** / 单条结果 **≤ 512** / 路由通知 **≤ 1024**（平台硬上限，**超限即被截断且不报错**）→ **大报告一律写盘**，回传只带**摘要 + 产物路径 + 「已写盘」声明**。
> - **announce 逐层传递**：每层只见**直接子代**的 announce（论衡仅 1 层，不受影响）。

> **错误码语义分层（教训 #285）**：子代理报错时区分「资源/认证层错误」vs「产物缺失」，避免主控误判兜底：
> - `HTTP 401/403/429` / `quota exceeded` / 欠费 = **资源/认证层错误**，产物**可能已完整写盘**——若已写盘，返回 degraded 时**附带产物路径**，主控先 `read` 验证再决定是否兜底
> - `tool_error` / `protocol` = 工具调用错误，产物可能部分
> - `status=incomplete` = 显式未完成

> **token 统计**：子代理 token 由**完成事件（completion event）末尾的 Stats line** 提供——精确值，固定含 `Token usage`（input/output/total）+ `Runtime` + `Estimated cost` + `sessionKey`/`sessionId`，主控 `sessions_yield` 收到 completion event 时提取记入 status.md 4.7 表，取代 v2.5.18 三级降级。**Stats line 缺失 = 平台异常**：标「Stats line 缺失」告警，禁止估算/静默跳过。**sessions_spawn 返回值无 stats 字段**（教训 #256）。
