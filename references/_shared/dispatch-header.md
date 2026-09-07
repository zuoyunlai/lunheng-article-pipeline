> 版本：v2.7.5（自动同步 2026-09-07）

> **所有 dispatch 头部公共内容**（v2.7.5 拆分，子代理启动时按需读本文件 + 角色卡即可，避免一次加载全部派发话术）。

> **零 exec 哲学护栏**：论衡 agent 全部禁 `exec` / `process` / `browser` / `apply_patch` / `cron` / `video_generate` / `music_generate` / `tts` / `memory_store` / `skill_workshop` / `memory_forget` / `sessions_search` / `sessions_send`（永久拒绝，Phase 0 同意不能豁免）。

> **子代理工具白名单（5 档，主控 spawn 必传 toolsAllow）**：
> - `allow_research`（T1/T2/T3）: `["read","write","edit","web_search","web_fetch","tavily_search","tavily_extract","session_status","progress_card"]`
> - `allow_analysis`（T4）: `["read","write","edit","session_status","progress_card"]`
> - `allow_writing`（T5）: `["read","write","edit","session_status","progress_card"]`
> - `allow_audit`（T6/T7）: `["read","session_status","progress_card"]` — **只读**，不写/不改/不出网/不调记忆/不调图像/不 spawn 子会话
> - `allow_review`（T9/G14）: `["read","session_status","progress_card"]` — **只读**

> **降级自报（v2.7.3 ECS 实战）**：遇 provider 401 / 配额耗尽，在 final message 返回 `{"status": "degraded", "reason": "<错误摘要>"}` 后立即结束，**禁止 0 tokens 静默退出**（主控凭此触发 fallback 标注）。

> **token 统计（v2.6.1 精确机制）**：子代理 stats 由 sessions_spawn 返回值提供（精确值），取代 v2.5.18 三级降级。
