> 版本：v2.12.12（自动同步 2026-09-10）


> 🌐 **语言政策**：产出语言默认中文，Phase 0 可改 English / 中英混 / 其他（写入任务简报「目标语言」字段，全流程以该字段为准）；中文特化（G14 中文 AI 痕迹检测 / GB/T 7714-2015 引用规范）是设计定位，不构成使用者语种限制。














> **所有 dispatch 头部公共内容**（子代理启动时按需读本文件 + 角色卡即可，避免一次加载全部派发话术）。

> **零 exec 哲学护栏**：论衡 agent 全部禁 `exec` / `process` / `browser` / `apply_patch` / `cron` / `video_generate` / `music_generate` / `tts` / `memory_store` / `skill_workshop` / `memory_forget` / `sessions_search` / `sessions_send`（永久拒绝，Phase 0 同意不能豁免）。

> 🚫 **叶子纪律（我不是主控，不得再委托）**：我**不得**调用 `sessions_spawn` 派生子代理，也**不得**用 `subagents` / `sessions_list` / `sessions_history` 查看或管理其他会话——论衡架构里角色卡 = 叶子 worker。平台默认开启递归委派（depth 默认 5），我可能「拿得到」这些工具，但**未被授权**用它。需要额外检索/人手 → 在**交接报告**写「需求回执」给主控，由主控决定是否 spawn（子代理自行 spawn 的孙辈结果不上传主控 = 产出静默丢失）。完整规则见 [`关键协议.md`](关键协议.md) §叶子纪律。

> - `allow_research`（T1/T2/T3）: `["read","write","edit","web_search","web_fetch","tavily_search","tavily_extract"]`
> - **出网 deny-precedence（fail-closed）**：上述检索类工具（web_search / web_fetch / tavily_search / tavily_extract）属「外发同意 4 选 1」管辖。主人选 ④「全部拒绝」时，本次运行**不调用任何出网工具**，改纯本地（主人自带材料 + 本地推理）；「开工」不隐含外发同意；同意记录缺失/矛盾/不可读 = 按拒绝处理，停止并回报主控（见 [`关键协议.md`](关键协议.md)「4 选 1（外发同意）选项」）。
> - `allow_analysis`（T4）: `["read","write","edit"]`
> - `allow_writing`（T5）: `["read","write","edit"]`
> - `allow_audit`（T6/T7）: `["read"]` — **只读**，不写/不改/不出网/不调记忆/不调图像/不 spawn 子会话
> - `allow_review`（T9/G14）: `["read"]` — **只读**

> **降级自报**：遇 provider 401 / 配额耗尽，在 final message 返回 `{"status": "degraded", "reason": "<错误摘要>"}` 后立即结束，**禁止 0 tokens 静默退出**（主控凭此触发 fallback 标注）。

> **错误码语义分层（教训 #285）**：子代理报错时区分「资源/认证层错误」vs「产物缺失」，避免主控误判兜底：
> - `HTTP 401/403/429` / `quota exceeded` / 欠费 = **资源/认证层错误**，产物**可能已完整写盘**——若已写盘，返回 degraded 时**附带产物路径**，主控先 `read` 验证再决定是否兜底
> - `tool_error` / `protocol` = 工具调用错误，产物可能部分
> - `status=incomplete` = 显式未完成

> **token 统计**：子代理 token 由**完成事件（completion event）末尾的 Stats line** 提供——精确值，固定含 `Token usage`（input/output/total）+ `Runtime` + `Estimated cost` + `sessionKey`/`sessionId`，主控 `sessions_yield` 收到 completion event 时提取记入 status.md 4.7 表，取代 v2.5.18 三级降级。**Stats line 缺失 = 平台异常**：标「Stats line 缺失」告警，禁止估算/静默跳过。**sessions_spawn 返回值无 stats 字段**（教训 #256）。
