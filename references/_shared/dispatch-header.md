> 版本：v2.12.5（自动同步 2026-09-10）










> **所有 dispatch 头部公共内容**（子代理启动时按需读本文件 + 角色卡即可，避免一次加载全部派发话术）。

> **零 exec 哲学护栏**：论衡 agent 全部禁 `exec` / `process` / `browser` / `apply_patch` / `cron` / `video_generate` / `music_generate` / `tts` / `memory_store` / `skill_workshop` / `memory_forget` / `sessions_search` / `sessions_send`（永久拒绝，Phase 0 同意不能豁免）。

> - `allow_research`（T1/T2/T3）: `["read","write","edit","web_search","web_fetch","tavily_search","tavily_extract"]`
> - `allow_analysis`（T4）: `["read","write","edit"]`
> - `allow_writing`（T5）: `["read","write","edit"]`
> - `allow_audit`（T6/T7）: `["read"]` — **只读**，不写/不改/不出网/不调记忆/不调图像/不 spawn 子会话
> - `allow_review`（T9/G14）: `["read"]` — **只读**

> **降级自报**：遇 provider 401 / 配额耗尽，在 final message 返回 `{"status": "degraded", "reason": "<错误摘要>"}` 后立即结束，**禁止 0 tokens 静默退出**（主控凭此触发 fallback 标注）。

> **错误码语义分层（教训 #285）**：子代理报错时区分「资源/认证层错误」vs「产物缺失」，避免主控误判兜底：
> - `HTTP 401/403/429` / `quota exceeded` / 欠费 = **资源/认证层错误**，产物**可能已完整写盘**——若已写盘，返回 degraded 时**附带产物路径**，主控先 `read` 验证再决定是否兜底
> - `tool_error` / `protocol` = 工具调用错误，产物可能部分
> - `status=incomplete` = 显式未完成

> **token 统计**：子代理 token 由**完成事件**的 `Stats:` 行提供（精确值，主控 `sessions_yield` 时提取），取代 v2.5.18 三级降级。**sessions_spawn 返回值无 stats 字段**（教训 #256）。
