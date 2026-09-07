> 版本：v2.7.5（自动同步 2026-09-07）

> **所有 dispatch 头部公共内容**（v2.7.5 拆分，子代理启动时按需读本文件 + 角色卡即可，避免一次加载全部派发话术）。

> **零 exec 哲学护栏**：论衡 agent 全部禁 `exec` / `process` / `browser` / `apply_patch` / `cron` / `video_generate` / `music_generate` / `tts` / `memory_store` / `skill_workshop` / `memory_forget` / `sessions_search` / `sessions_send`（永久拒绝，Phase 0 同意不能豁免）。

> **子代理工具白名单（5 档角色最小工具集声明，v2.7.12 修正；v2.7.13 软化为建议）**：OpenClaw 2026.9.x 的 `sessions_spawn` **无 toolsAllow 参数**——子代理实际工具 = 主控有效工具策略快照 − 平台硬性剥除（gateway/agents_list/session_status/cron/message/sessions_send/conversations_*；叶子另剥 sessions 系列）。**建议宿主**用 config `tools.subagents.tools.allow/deny` 收紧（至少 deny exec/process/browser/apply_patch）以获得机械保证；未收紧时零 exec 为纪律层软保障（本文件 + 角色卡零授权约束），非机械强制。档位差异在工具层不可逐子表达时，以 prompt + 只读路径约束兜底。
> - `allow_research`（T1/T2/T3）: `["read","write","edit","web_search","web_fetch","tavily_search","tavily_extract"]`
> - `allow_analysis`（T4）: `["read","write","edit"]`
> - `allow_writing`（T5）: `["read","write","edit"]`
> - `allow_audit`（T6/T7）: `["read"]` — **只读**，不写/不改/不出网/不调记忆/不调图像/不 spawn 子会话
> - `allow_review`（T9/G14）: `["read"]` — **只读**

> **降级自报（v2.7.3 ECS 实战）**：遇 provider 401 / 配额耗尽，在 final message 返回 `{"status": "degraded", "reason": "<错误摘要>"}` 后立即结束，**禁止 0 tokens 静默退出**（主控凭此触发 fallback 标注）。

> **token 统计（v2.6.1 精确机制）**：子代理 stats 由 sessions_spawn 返回值提供（精确值），取代 v2.5.18 三级降级。
