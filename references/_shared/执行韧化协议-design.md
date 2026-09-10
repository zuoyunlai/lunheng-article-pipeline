> 版本：v2.12.9（自动同步 2026-09-10）
> 🌐 **语言政策**：产出语言默认中文，Phase 0 可改 English / 中英混 / 其他（写入任务简报「目标语言」字段，全流程以该字段为准）；中文特化（G14 中文 AI 痕迹检测 / GB/T 7714-2015 引用规范）是设计定位，不构成使用者语种限制。










# 执行韧化协议 v2.1.0（论衡激进重构，设计者文档**）

# 执行韧化协议 v2.1.0（论衡激进重构）

> **v2.2.8 Phase D 修订**：本协议从「v2.1.0~v2.2.7 内联到 7 张角色卡」改为「**主流程读本文件** + 7 张角色卡顶部精简索引」。理由：原 7 张角色卡复制完整内容约 1.2K tokens 重复，精简后 token 节省 + 协议版本演进只需改本文件一处。

> 2026-08-14 论衡 v2.1.0 引入 | 教训 #288 | 解决子代理脆弱 + 写手卡死

## 协议三大铁律（每个角色 prompt 头部必读）

### 1. 心跳信号（必须执行）
- **启动 30 秒内**：写自己的心跳文件 `run/<项目>/.tmp/<角色>-heartbeat.md`（状态=🔄 In Progress + 启动时间 + 当前模型）；status.md 由主控独占更新
- **每 5 分钟一次**：在 status.md 阶段行末尾追加心跳时间戳（格式：`[心跳 HH:MM] model=<model-id>`）
- **超时硬卡（分角色分级，教训 #126 + #279）**：
  - **T1-T3 检索员**：10 分钟（分级表准；中文检索单次 7s+，教训 #126）
  - **T6 批判 / T7 审计**：15 / 12 分钟（分级表准；批判+修订任务需更长，教训 #279）
  - **T4 分析 / T5 写手**：12 / 15 分钟（旧「8 分钟保持」已废）
  - 各角色硬卡时间点：提前 2 分钟写 `[警告] 已耗时 X 分钟`；提前 1 分钟必须产出 partial output；到点主控 kill + 标记 Failed
  - **读文件 vs 写文件区分**：写文件（落盘）比读文件耗时更长，硬卡判断时对「写文件任务」放宽 2 分钟

### 2. 分阶段 ack（按任务时长分级）

| 任务预估时长 | ack 节点 |
|------------|----------|
| < 2 分钟 | 启动 ack 即可，无需中间 ack |
| 2-5 分钟 | 启动 + 完成二段 ack |
| 5-15 分钟（写手/审计） | 启动 + 25% + 50% + 75% + 完成 五段 ack |
| > 15 分钟 | **禁止**——必须拆任务 |

每段 ack 在 status.md 阶段行末尾追加： `[ack N% HH:MM] <一句话说进度>`。

**完成 ack 的 token 消耗由主控记录（精确机制）**：
角色完成 ack **不**回传自己的 token（子代理拿不到：sessions_spawn 返回值无 stats 字段，教训 #256）。token 由**主控**在 `sessions_yield` 收到 completion event 时从事件末尾 Stats line 提取 `Token usage` 记入 status.md 4.7 表：
- **输入**：`Token usage` 的 input（精确值，来自 completion 末尾 Stats line）
- **输出**：`Token usage` 的 output（精确值，来自 completion 末尾 Stats line）
- **总计**：`Token usage` 的 total（input + output）
- **v2.12.2 重写根因**（教训 #256）：v2.6.1 起文档误把来源写成「sessions_spawn stats」（沿袭教训 #192 的误记），实测 spawn 返回值无 stats。拿不到精确值 = 平台异常（completion event 缺 Stats line），不填「未配置」/「N/A」。

**示例（写手 4758 字）：**
```
[ack 0% 17:35] 已读简报+大纲+10文献+17数据+3案例
[ack 25% 17:38] 完成开篇+第1节（549字）
[ack 50% 17:42] 完成第2-3节（788+592=1380字）
[ack 75% 17:46] 完成第4-5节（599+594=1193字）
[ack 100% 17:52] 完成第6-7节+参考文献（489+432+清单）
```

### 3. LLM 可用性初判
- **每个角色启动时**依赖宿主 agent 的 `model.fallbacks` 配置链（**宿主维护项，论衡不绑定模型 ID；以下为本机开发示例，实际以宿主 OpenClaw 配置为准）：
  - primary: `deepseek/deepseek-v4-pro`（本机开发示例）
  - fallback 1: `minimax-portal/MiniMax-M3`（本机开发示例，曾验证 fallback 成功 T4 实战）
  - fallback 2: `deepseek/deepseek-v4-flash`（本机开发示例，便宜快）
  - fallback 3: `coding-plan/glm-5.3`（本机开发示例，跨供应商最终兜底）
- **预检方法**：每个角色 session 第一次 LLM 调用前，先发一个 1-token ping（"ok"），若 30 秒内无响应则降级到下一档
- **降级日志**：在 status.md 阶段行末尾写 `[降级 HH:MM] primary→fallback1, 原因=ping超时`

### 3.5 配额耗尽识别 + 授权兜底（教训 #184，实战）
> **背景**：v2.5.13 实战中 SVG→PNG 子代理派发时 DeepSeek-v4-flash 返回 `billing error`。当时主控直接用 exec 亲完成（主人现场知情的一次性授权）。v2.6.6 起该兜底固化为 **Phase 0 显式 opt-in 项**，默认关闭。
> **边界原则**：本技能文档中任何让宿主 agent 调用工具的指令都算技能自身能力，受 `metadata.tools` 声明约束。技能文本**不包含**任何「主控例外」豁免——永久拒绝（exec/process 等）对主控、子代理、fallback 路径、错误恢复流程一律生效。子代理卡死时主控的合法兜底只有：暂停询问主人 / 换 provider 重试 / 用白名单工具接力。

**识别（LLM 推理判定，不靠硬阈值）**：
- **关键信号**（任一命中即视为配额类失败）：
  - 子代理回复中包含：`billing error` / `quota exceeded` / `insufficient balance` / `429`（响应头带 `rate limit`）/ `payment required` / `usage limit` / `over quota`
  - **LLM 推理判定**：主控读到这些信号时，**推理为**「这是账号级配额问题，不是网络/超时类临时问题」，与 ping 超时区别开
- **判定时机**：**不限定硬性秒数** —— 主控根据当前任务进展感判断（如果子代理刚启动就连续报错→几乎肯定是配额；跑了 10 分钟才出问题→可能是临时网络）。LLM 推理 vs 硬代码 `if elapsed > 300:`，区别就在这里。
- **本节不是硬代码**：v2.5.18 第一版写了「5 秒内」「5 分钟内」硬阈值，v2.5.20 改成软推理——论衡靠 LLM 推理，阈值由主控 LLM 看到上下文后自主判断

**处理（默认暂停等主人）**：
1. **status.md 状态标注**（建议做法，**不强制**）：写一行记录配额告警
2. **不再自动切 fallback**（**硬建议**）：配额耗尽是账号级问题，切单个 fallback 不解——下一档同样会撞同个账户的余额。**LLM 推理例外**：主控推理判断「切换到不同 provider 可能解」时，仅换 provider 不换同 provider 的档位
3. **暂停流水线，向主人呈报**（fail-closed，**默认必停**）：主控在对话里告知「本轮 LLM 配额可能耗尽」+ 3 选项，**等主人拍板后才继续**：
   - □ 主人切其他 provider（如 OpenAI / Google）重试子代理
   - □ 主控用白名单工具（read/write/edit）接力完成该子代理任务（零 exec 路径，任何宿主环境均合规）
   - □ 等下个计费周期（保留 partial 产物，安全终止）
   - **禁止**：主控自行调用 exec/process/browser 等永久拒绝工具——该约束无例外，Phase 0 一般性同意不覆盖工具/权限变更
4. **Phase 0 opt-in 预授权（可选，默认关闭）**：若主人在 Phase 0 任务简报「授权记录」段明确勾选「配额耗尽时授权 X（换 provider / 白名单接力）」，配额事件发生时主控按预授权选项直接执行并事后通报，无需再次等待。**未勾选 = 无预授权 = 必须暂停等主人**。
5. **记录与追溯**：配额事件 + 主人选择 + 执行动作写入 status.md「配额事件」段，供 T7 审计追溯

## 改造要点（角色卡层面）

每个角色 prompt 头部新增段落：
```markdown
## 执行韧化协议（30 秒心跳 + 分阶段 ack）

1. 启动 30 秒内写自己的心跳文件（`run/<项目>/.tmp/<角色>-heartbeat.md`，状态=🔄 In Progress + 启动时间 + 当前模型）；status.md 由主控独占更新
2. 按任务时长选择 ack 节奏（<2分钟/2-5分钟/5-15分钟）
3. LLM 可用性初判：子代理观察首次 LLM 调用响应；30 秒无首响应则降级 fallback
4. 超时硬卡（角色分级）：按「主控扩展职责 §二十二 硬卡阈值表」执行（T1-T3 10 分钟 / T4 12 / T5 15 / T6 15 / T7 12 / T9 10 / G14 8）；到点主控 kill + 接受 partial
5. **禁止假装在线**：心跳 ack 必须真实反映进度，禁止编造 ack
```

## 改造要点（主控层面）

主控在 spawn 子代理时：
- 每次 spawn 后立即 watch 子代理 status.md 心跳（不再静默等待）
- 30 秒内未心跳 → 主控 console 警告，但**不**自动 kill（给子代理多一次机会）
- 5 分钟无 ack → 主控主动 ping 子代理 session（sessions_history）
- 超角色分级阈值无 ack + 无产出 → 主控 kill + 标记 Failed + 决定是否重试（阈值表见主控扩展职责 §二十二）

### 4. 编排循环防空转（教训 #274）
> **背景**：2026-08-19 ECS 实战，T8→T5 交接点被 duplicate 完成事件打断，导致 T5 的 spawn tool call 丢失，主控却误以为已 spawn，空转 2.5 小时。根因：编排循环对「完成事件恰好投递一次」过度依赖，缺三道防御。

**主控编排循环必须遵守的三防**：适用于 T1→T3 / T3→T4 / T4→T8 / T8→T5 / T5→T4（修订）/ T5→T7 等**所有 T 角色 spawn 交接点**。

#### 4.1 spawn 后验证落地（必做）
每次 `sessions_spawn` 后，**必须**立即调 `subagents(action=list)` 确认 runId 出现在 active runs，再进入 yield。没出现 = spawn 丢失，立即重试（≤2 次）：
```python
# 伪代码（spawn 验证）
run = sessions_spawn(task=...)
if not subagents_has_active(run.runId):
    # spawn 丢失，判定为 duplicate 事件 / 网路问题
    log("[#274 防御] spawn runId={} 未落地，重试".format(run.runId))
    run = sessions_spawn(task=...)  # 重试 1 次
```

#### 4.2 yield watchdog 超时自查（必做）
`sessions_yield` 后超过 N 分钟（推荐 **3 分钟**，可根据 Phase 调整）仍无完成事件 → 主控**不再静默等**，自查 `subagents(action=list)`（宿主强制 self-spawn 列表，超出最小权限，回应 A.I.G T05）：
- 预期角色仍在 active runs + 最近有 status.md 心跳 → 子代理真在跑，继续 yield（但记录已等待 X 分钟，下次超阈值重判定）
- 预期角色不在 active runs（subagent 已结束但没投递完成事件）或重复投递同一子代理的完成事件 ≥2 次 → **duplicate 事件嫌疑**，立即补 spawn：
```python
# 伪代码（yield watchdog）
wait_start = time.now()
while wait_elapsed < WATCHDOG_TIMEOUT:
    yield()  # 等下一次完成事件
    if completion_received:
        # 检查 幂等：status.md 该角色是否已 Done？
        if is_role_done(status_md, role):
            log("[#274 幂等] {} 完成事件已处理过，忽略 duplicate".format(role))
            continue  # 忽略 duplicate，不重复推进
        return  # 推进编排
    if wait_elapsed > WATCHDOG_TIMEOUT:
        # 第一次超过阈值时跑一次自查
        if not subagent_alive_in_active_runs(runId):
            log("[#274 修复] yield 超时 + 子代理不在 active = spawn 丢失，重派")
            respawn()  # 补 spawn
```

#### 4.3 完成事件幂等处理（必做）
收到任何角色完成事件时，**先查 `status.md` 该角色是否已 Done**——已 Done = duplicate 事件，忽略不重复推进：
```python
# 伪代码（完成事件幂等）
def on_completion(role, runId):
    if status_md[role]['state'] == 'Done':
        log("[#274 幂等] {} 已在 Done，忽略 duplicate 完成事件 runId={}".format(role, runId))
        return  # 静默忽略，不推进下一个 T
    # 正常推进
    status_md[role]['state'] = 'Done'
    spawn_next_role()
```

#### 4.4 交接点「三段式 spawn」
关键交接点（T8→T5、T4→T8、T5→T4 修订）**必须**走「spawn → 验证落地 → 确认后 yield」三段，**禁止**「spawn → 直接 yield」：
```
# 错误（之前模式，duplicate 事件可击穿）
sessions_spawn(T5)
sessions_yield()  # ← 被打断则空转

# 正确（#274 修复后）
sessions_spawn(T5)
assert subagents_has_active(runId)  # 验证落地
sessions_yield()  # 确认后才 yield
```

#### 4.6 spawn 后静默探测（ECS 实战：三子代理 401 静默退出主控无感知）

spawn 任何子代理后，主控**不能只等完成事件**：
- spawn 后 ~30s（首个硬卡警告点前）用 `subagents list` / `sessions_history` 看一眼：status=running 但 tokens=0 且 history 停留在初始 prompt → **raise fallback warning**，不静默等硬卡
- 子代理遇 provider 401 / 配额耗尽：**在 final message 返回 `{"status": "degraded", "reason": "<错误摘要>"}`**，禁止 0 tokens 静默退出（各 dispatch 已注入此条）
- 主控 fallback 顶替时：①status.md「降级运行记录」段写独立行 `⚠️ DEGRADED RUN：<角色> 由主控顶替（<原因>）HH:MM`；②亲出产物头部强制标注 `[主控 fallback 产物 / <实际模型> / <日期>]`；③**亲出前必 `read` 对应角色卡 + dispatch 最新版**，按当前版本格式产出（禁止凭 memory 写旧版格式，ECS 实战 T7 口径漂移教训）；④对话中向主人显式报告降级事实

#### 4.7 报告长度上限 + 超限分块协议（回应实测 #4 质量降级）

> **背景（实测 #4）**：T6 v1 首跑 16k 字符超外化阈值被截 → 主控被迫分块拼接（v3 末段 + v4 总结段含主控拼接成分）→ 质量降级。根因 = 报告无长度上限 + fallback 无分级。

**1. 硬上限（单一真源 = phase-order.yaml 各节点 `output_chars_max`）**：

| 产出 | 上限（字符量级，read 估算非 wc） |
|------|------|
| T4 分析大纲 | ≤12000 |
| T6 批判报告 | ≤12000 |
| G14 检测报告 | ≤6000 |
| T7 审计报告 | ≤10000 |
| T9 审稿报告 | ≤15000 |
| T8 终检说明 | ≤10000 |

> 口径：上限是「回传长度」控制，不是「内容深度」限制——超限优先砍展开论述、保结论 + 证据编号；禁止砍维度本身。

**2. 超限分块协议（子代理侧主动，主控侧接收）**：
- 子代理回传前自查：read 估行数/字符量级，超限 → **按报告结构分块回传**（T6 按 C1-C7、T7 按 G 门分组、T9 按 6 维度），每块 ≤ 上限，块间用分隔行 `<!-- chunk N/M -->`
- 单块仍超 → 砍细节保结论（各块结论 + 证据编号必留，展开论述可省）
- 主控侧：逐块接收 → `write` 落盘拼接 → 「读盘确认铁律」核验首尾与块数；块缺失 → 立即要求补块，不静默接受不完整报告
- 禁止「一次性全量发出赌截断」——截断后丢失内容主控无从知晓，是质量黑洞

**3. fallback 质量分级（主控拼接/顶替时的接受标准，回应实测 #4 根因 4.3）**：

| 级 | 定义 | 处置 |
|----|------|------|
| **A 级（可接受）** | 主控仅机械拼接各块（子代理内容完整、仅因分块需拼接），未改实质内容 | 正常继续；产物头部标注 `[多块拼接产物]` 即可 |
| **B 级（警告）** | 主控做了内容补充/裁剪/重组（如砍细节保结论、补缺失块概述） | 产物头部标注 `[主控 fallback 产物]` + **逐段标注哪些段含主控补充**；对话中向主人报告 |
| **C 级（阻断）** | 主控不得不自己写实质段落（子代理核心产出丢失/静默退出） | **触发完整重跑**（同角色同档重 spawn，或降档后重跑）；禁止以主控代写冒充子代理产出 |

> 与既有标记的关系：v2.7.3 `[主控 fallback 产物 / <实际模型> / <日期>]` 对应 B 级；v2.7.2 回传截断标记（主控落盘后对照回传原文抽查首尾）是 A/B 级的检测手段，保留。

#### 4.5 诊断边界（回应安全审计 SDI-1/SDI-4 sessions_history 措辞歧义）

> **一句话**：本协议区分两类诊断能力，边界不可混：
> - 🔒 **仅人类主人诊断**：读 OpenClaw runtime 内部会话轨迹文件 / 执行 shell 命令（exec/process）——**agent 零 exec，永不调用**
> - ✅ **主流程诊断**：用白名单工具（subagents / sessions_history / progress_card）看**论衡自己 spawn 的子代理**——**仅限 self-spawn 的子代理，不跨会话抓取**（其发现职责由宿主强制的 subagents 列表承担，不枚举宿主可见会话）

#### 🔒 仅人类主人诊断（agent 零 exec，主流程永不调用）

> **范围调整**：原 § 4.5 中读取 OpenClaw runtime 内部会话轨迹文件的方法，原本在主流程中提及，但该路径属于 OpenClaw runtime 内部诊断，不在论衡主流程职责范围。**以下命令仅供人类主人手动排查论衡编排故障时在 host shell 执行**：
>
> <!-- 人类诊断命令（agent 零 exec，主人手动执行） -->
> - 进入 OpenClaw runtime 内部会话目录
> - 取最近的会话轨迹文件
> - 统计 `sessions_spawn` 调用次数
> - 统计 `sessions_yield` 调用次数
> - 取出现频次前 5 的子代理 session_key

#### ✅ 主流程诊断（白名单工具，仅限 self-spawn 子代理）

**论衡主流程实际能跑的诊断**（用 read 工具推理 / 用 progress_card 打钩，全部是 `metadata.tools` 声明的白名单工具）：
- `subagents(action=list)` —— 看当前 session 有没有真的 spawn 出子代理、runId / sessionKey 在不在 active（宿主强制 self-spawn 列表）
- `sessions_history(sessionKey=...)` —— **仅限查看论衡自己 spawn 的子代理会话产物**（`subagent:xxx` sessionKey，来自 spawn 返回或 subagents 列表），**不跨会话读取、不抓取其他 session 的隐藏状态**
- `progress_card` 打钩「§ 4.1 spawn 验证」「§ 4.2 watchdog 自查」「§ 4.3 幂等检查」

**论衡 agent 不调用的**：exec / process / 读 OpenClaw runtime 内部路径 / sha256 直接计算（这些是**人类主人**的能力，不在 agent 范围内）。

> **边界澄清（回应 scanner SDI-1/SDI-4）**：`sessions_history` 是白名单工具，但论衡**只用它读自己 spawn 的子代理**（`subagent:xxx`），用途是编排监控（看子代理有没有产出、有没有死循环），**不是跨会话读取历史或抓取隐藏状态**。上方「🔒 仅人类主人诊断」段的 `session_key` 字样指主人手动排查时在 host shell 查看轨迹文件，与主流程 `sessions_history` 是两回事，勿混。

## 三检索员并行监控补充（教训 #267 + #289）

> 背景：v2.1.8 主控一次性 spawn T1 + T2 + T3 三个独立 sessions_spawn（同一 function_calls 块内），三方并行。与传统单 spawn 不同，主控需额外监控：

- **三方并行心跳看总和**：T1+T2+T3 三个 sessions 都心跳后才视为「三方并行存活」——任一 30s 未心跳 = 该 T 心跳异常
- **三方独立超时**（教训 #289）：硬卡阈值对每个 T **独立生效**——T1 超时 ≠ T2/T3 也超；主控只 kill 超时的那个，其他不受影响
- **runtime vs 墙钟区分**（教训 #289）：runtime = 模型推理 + 工具调用纯耗时；墙钟 = runtime + OpenClaw 调度 + 子会话启动 + 文件落盘；硬卡阈值**指的是墙钟**（含调度延迟），runtime 通常 1-3 分钟
- **失败隔离**：T1 失败不影响 T2/T3 继续；T3 失败不影响 T1/T2；主控收到失败 ack 后标 `Failed` + T0 合并层标「案例缺角」/「文献缺角」/「数据缺角」对应降级
- **三方同步 ack 节点**：三方共享同一 Phase 1 阶段行的 status.md（避免三份独立 status 难以合并）