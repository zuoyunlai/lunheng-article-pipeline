> 版本：v2.7.4（自动同步 2026-09-07）















> 权威源：references/gates/14-中文AI痕迹-gate.md（本文件为派生视图，冲突以角色卡为准；G14 是闸门，无独立角色卡）


> 从 pipeline-readme.md 派发话术段拆出（v2.5.6 token 优化）。主控 spawn G14 中文 AI 痕迹检测器（v2.4.0 新增） 时按需读本文件，避免一次加载全部派发话术。完整角色卡见 references/agents/。

> **v2.6.5 子代理工具白名单（主控 spawn 必传 toolsAllow，5 档分档：allow_review）**：
> ```json
> ["read","session_status","progress_card"]
> ```
> **allow_review 档 = 只读**：不写 / 不改 / 不出网 / 不调记忆 / 不调图像 / 不 spawn 子会话。**禁止**：除上表 3 项（read / session_status / progress_card）外的全部工具（含 sessions_spawn / write / edit / memory_* / image_generate）。
> **降级自报（v2.7.3）**：遇 provider 401 / 配额耗尽，在 final message 返回 `{"status": "degraded", "reason": "<错误摘要>"}` 后立即结束，**禁止 0 tokens 静默退出**（主控凭此触发 fallback 标注，ECS 实战三子代理静默教训）。
> **作用**：论衡「零 exec」哲学护栏 + OpenClaw 9.1 子代理工具继承机制修复。**主控 spawn 任何 T 角色必须传 toolsAllow**，不传 = 子代理继承宿主全部默认工具（含 exec / process / browser） = **违背论衡「零 exec」哲学**。
> **token 统计**：子代理 stats 由 sessions_spawn 返回值提供（v2.6.1 精确机制，取代 v2.5.18 三级降级）。


### G14 中文 AI 痕迹检测器（v2.4.0 新增）

> **何时用**：与 T6 对同一个 `current_draft` 同批调用；主人在 Phase 0 选择 `disabled_by_owner` 则全项目不 spawn。

```
请以「G14 中文 AI 痕迹检测器」身份检测 [drafts/初稿-v{N}.md] 的 AI 生成痕迹。

【检测维度】8 类（参考 references/checkers/中文AI痕迹-checker.md）：
A. 学术模板语（综上所述/本文认为/值得关注的是等，任一 ≥3 次命中）
B. 句式同质化（连续 3 段同句式起头）
C. 学术套话高频（赋能/抓手/底层逻辑等，全文 ≥5 处）
D. 破折号滥用（全文 >8 处 / 段 ≥2 处 ≥5 段 / 占比 >3%）
E. 三项排比（全文 ≥3 处）
F. 人称错位（「我」字频 >1%）
G. 个人辨识度缺失（LLM 自评风格相似度 >80%）
H. 党报话语堆砌（重要讲话精神等，全文 ≥3 处，政治学科特化）

【输出】audits/G14-检测报告-v{N}.md（若本报告为主控 fallback 亲出：头部强制标注 `[主控 fallback 产物 / <实际模型> / <日期>]`，v2.7.3）（报告头必须写 `draft_id` / `draft_version` / `g14_status`；**报告回传机制（v2.7.2，配合只读档白名单）**：报告全文置于交接回传（final message），不自行写盘；主控收到后 `write` 落盘并走「读盘确认铁律」核验。）：
- 8 类逐项判定（命中数 + 阈值 + 原文示例 + 位置）
- 整体判定：0-2 类 Pass / 3-4 类 Warning / 5+ 类 Fail
- 修订建议（按类别给改写示例）

【铁律】LLM 推理判定（零 exec）；中文特化；不做事实核验（那是 T7 的活）；检测结果仅供告警。
【交接报告】做了什么（8 类判定 + verdict）/ 产物路径 / 怎么验证 / 已知问题 / 下一步（Pass 继续 / Warning 触发修订 / Fail 强制修订）/ **token 消耗**（v2.6.1 重写：sessions_spawn 返回值 stats 含精确 tokens.in/out，原样回传即精确值——无需估算/降级）
```

