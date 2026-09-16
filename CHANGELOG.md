# Changelog

> ⚠️ **范围说明（v2.12.47 起）**：本文件只保留**最近 5 期**；**v2.12.41 及更早**的全部章节逐字迁入 [`CHANGELOG-archive.md`](CHANGELOG-archive.md)。部分历史条目链接指向 `docs/` 或 `../outputs/` 中的**当时产物**（发布说明 / 审计报告 / 设计方案），这些文件**已随清理移除或归档**，链接可能失效——**属史料，不影响当前使用**。当前版本行为以 [`SKILL.md`](SKILL.md) 与 `references/` 为准。

论衡（`lunheng-article-pipeline`）版本变更记录。**本文件 + [`CHANGELOG-archive.md`](CHANGELOG-archive.md) 共同构成仓库内 changelog 的单一真源**（`scripts/changelog-check.py` 同时读取两份，「每个版本 tag 都有章节」的校验不受拆分影响）；GitHub [Releases](https://github.com/zuoyunlai/lunheng-article-pipeline/releases) 是同一内容的发布视图。

- **排序**：版本倒序（最新在前）。查找某一版本：`grep -n '^## \[v2.12' CHANGELOG.md CHANGELOG-archive.md`
- **章节标题**：`## [<tag>] — <发布日期>`；正文＝该版本 Release 正文逐字保留（早期 Release 由 GitHub 自动生成，正文天然偏薄，`python3 scripts/changelog-check.py --report` 可列出）。
- **发版流程**：建 GitHub Release 后执行 `python3 scripts/changelog-check.py --fill` 回填本节；也可直接手写章节。`--check` 校验「每个版本 tag 都有章节 + 围栏闭合 + 当前版本已记录」，`--online` 追加校验「每个版本 tag 都有 GitHub Release」。
- **发版前置闸（教训 #332 / #334）**：任何对外发版动作（push / tag / GitHub Release / 净化包）前先跑 `bash scripts/release-preflight.sh <tag>`——两查一停：**在飞链**（同项目 `status=running` 会话）/ **编号占用**（本地 tag + `git ls-remote --tags` 双向）/ **工作区干净**（`git status --porcelain`），任一不过即非 0 退出（10/11/12）；通过时打印「远端 master / 本地 HEAD / tag 区间 / 在飞链=0」四行现状。`scripts/create-github-release.sh` 的写路径已强制调用本闸（并自动带 `--allow-existing-tag`：② 口径 = 「编号是否被本链之外的人占用」，避免「先 tag、后补发 Release」被自己的闸自锁），`--dry-run` / `--check` 不进闸。闸只读：不自行 push / 打 tag / 建 Release。
- **非版本 tag**（`full-repo-consistency-audit-2026-09-06`、`before-batch1-optimization`）不进入本表。

---

## [v2.12.46] — 2026-09-15

> **主题：架构定案 —— 多 Agent 九角色为唯一标准架构；Phase 编号真源化；角色产物写入边界；人在环机械门。**
> **性质：架构语义收敛 + 真源字段化 + 机械门补齐。无新增能力、无破坏性行为变更。**

### 一、★ 多 Agent 为唯一标准架构（删除「单主控」并列模式）

> **背景**：v2.12.13 起为回应宿主权限不确定性引入「默认单主控」兼容策略；此前又以 `single_controller_fallback` 实现，导致**默认路径可绕过整条质量链直达 Phase 5**（全量复审 P0）。业主定案：论衡的九角色就是多 Agent 架构，**不存在与之并列的第二种架构**。

- 删除 `executor_by_mode` / `single_controller` / `mode_is_multi_agent` / 全局模式旁路与 `record_single_controller_mode` 出口
- 新增顶层 `architecture`：`standard: multi_agent_role_pipeline`、`worker_roles: [T1..T7, T9, G14]`、`worker_failure_policy: owner_takeover_with_disclosure`、`fallback_is_not_equivalent: true`
- worker 节点统一声明 `role` / `write_authority: executor` / `verification_authority: 主控` / `on_worker_failure`（接管者 = 主控，`retry_limit: 1`）
- **worker 不可用/失败 = 单节点故障**：只接管失败节点 + `status.md` 记「worker 接管记录」+ 交付说明披露 L1 独立性风险；**不改架构、不跳质量门**
- 宿主不存在「架构上不兼容多 Agent」；实际发生的是策略拒绝 / 超时 / 失败 / 无产物 / 配额不可用

### 二、★ Phase 编号真源化

- 23 个节点逐一新增第一类字段 `phase`（文档层标签）+ `phase_seq`（流水线序号）
- 新增顶层 `phase_order` 编号表（唯一真源；主控呈现 Phase 标签不得自创）
- `flow-check.py` 新增**规则 11**：phase/phase_seq 完整性 + 唯一性 + 与 `phase_order` 两处一致 + 沿 next/after_trigger/on_fail **序号不得回退**（`after_each` 为重跑动作，不计）
- `status.md` 模板「当前阶段」枚举、`pipeline-overview.md` 标签同步对齐编号真源

### 三、角色产物写入边界

- **角色写自己的产物**：T1/T2/T3 检索卡、T4 大纲、**T5 初稿与修订稿（T5 = 正式写手，落盘职责保留）**、T6/T7/G14/T9 各自报告
- **主控独占**：`status.md` / `drafts/current_draft.md` / `final/定稿.md` / `final/交付说明.md` / `final/M-Gate-Report-*.json`
- `dispatch-header.md` 新增「产物写入边界」条；`任务简报` 模板新增「运行架构（固定）+ worker 接管披露」段（与 status / 交付说明**三处一致**）

### 四、人在环机械门

- 新增 `test_all_paths_pass_through_human_checkpoints`：枚举 Phase 0 → Phase 5 验收的**所有**路径，断言每条都经过 4 个 owner checkpoint；每个 checkpoint 必须有 `decisions` 枚举
- Phase 0 外发同意门（fail-closed）与心跳写盘同意门保持不变

### 五、验收

- `pytest` **285 passed**；自审门 **26 PASS / 0 FAIL**
- `flow-check` / `link-check` / `check-version` / `shellcheck` / `py_compile` / `diff-check` 全绿
- `SKILL.md` 体量 9954 ≤ 10000 字符

---

## [v2.12.45] — 2026-09-15

> **主题：ClawHub 审计复核整改 — 一致性 pass（消 T09 + SDI-4 0.96 两条 [unexpected]）+ 技能侧 SDI/SDI-2/SQP-2 配套修复。**
> **性质：一致性修复 + manifest 披露扩展。无行为破坏性变更。**

### 一、★ 一致性 pass —— 消 AIG T09 + SkillSpector SDI-4 0.96 两条 [unexpected]

> **背景**：v2.12.44 修了 fail-closed 措辞但只动了 3 份文件。**00-主控-扩展职责.md / SKILL.md / QUICKSTART.md 仍写"默认多 Agent / 任意配置开箱可用"** —— 文档互相矛盾，扫描器正确地标了两条 [unexpected]：
> - AIG **T09** "Role-Based Least-Privilege Restrictions Are Not Mechanically Enforced" at `references/permissions.md:59-84` + 跨文件引用
> - SkillSpector **SDI-4 0.96 HIGH** at `references/permissions.md:108-119` "the default-mode and fail-closed language is inconsistent across SKILL.md, QUICKSTART.md, permissions.md, and controller guidance"

> **修复**：选定 **权威口径**（一处定义，逐文件对齐）：
> > 「**默认 = 单主控**（主控亲为、不 spawn）。**多 Agent 须两条件齐**：(1) 宿主按 host-hardening-recipe 配方 0/1 落地（`tools.subagents.tools.deny` + `maxSpawnDepth: 1`），(2) 主人在 Phase 0 显式确认。任一缺失 ⇒ 单主控模式。**『任意配置开箱可用』= 启动不被拒，不等于『默认多 Agent』**。」

> 落 8 处：`SKILL.md`（描述 + 定位 + 权限边界）/ `QUICKSTART.md`（宿主配置 + 权限边界）/ `references/agents/00-主控-扩展职责.md`（三·L94-95、四·Phase 0 gate + 471 默认说明 + T9 advisory-only）/ `references/permissions.md`（73、75、105 用户警示、110-116 默认表）/ `references/templates/status-template.md`（25 默认说明）/ `references/_shared/host-hardening-recipe.md`（7、11）

### 二、★ Manifest（description）扩展 —— 消 SDI-1 0.84 / 0.87 / 0.89 / 0.91 / 0.93

`SKILL.md` frontmatter `description` 扩展为显式声明：本技能默认 = 单主控；多 Agent 须两条件齐；routine 写盘（`status.md` / `audits/` / `final/` / `drafts/<role>-status.json` / `analysis/`）已声明；心跳为 opt-in「Operational Telemetry」。

### 三、修复 SDI-1 / SDI-2 / SQP-2 多项

| Finding | 文件 / 行 | 修复 |
|---|---|---|
| **SDI-1 0.93** 心跳 vs metadata 同意语义矛盾 | `references/_shared/执行韧化协议-exec.md:11-13` | 重写：默认**不**写盘；写盘需 Phase 0 显式同意；manifest「Operational Telemetry」已声明 |
| **SDI-1 0.93** 同上 | `references/_shared/dispatch-header.md:29` | 同上 |
| **SDI-1 0.87** routine 写盘未声明 | `references/agents/00-主控-扩展职责.md:65-70` | description 已显式声明 |
| **SDI-1 0.89** Phase 1 retrieval 缺同意门 | `references/agents/00-主控-扩展职责.md:100-103` | 加 Phase 0 硬关卡（spawn 前显式核对同意记录；未勾选 ⇒ 主控亲为单主控） |
| **SDI-1 0.93** manifest vs orchestrator 控制面 | `references/agents/00-主控-扩展职责.md:381-395` | description 已显式声明 sessions_history / subagents / sessions_list / sessions_yield 等编排面 |
| **SDI-1 0.91** project-end snapshot 自动写盘 | `references/templates/status-template.md:133` | 改为 Phase 0 opt-in：未勾选不写；勾选才写 |
| **SDI-1 0.93** session_status / token-cost 默认收集 | `references/templates/status-template.md:204` | 改为 Phase 0 opt-in：未勾选仅在交付说明写"token 总计 ≈ Σ（精度 0）" |
| **SDI-1 0.84** T9 journal 匹配被描述为自动 | `references/agents/00-主控-扩展职责.md:198-200` | 改为 advisory-only：T9 仅产出候选，主人 Phase 5 须显式确认才进交付说明；manifest「Journal / Venue Matching」已声明 |
| **SDI-2 0.83** heartbeat 缺平台层 opt-in | `references/_shared/执行韧化协议-exec.md:11-13` | 同 SDI-1 0.93：opt-in |
| **SDI-2 0.78** run-control lifecycle 未声明 | `references/_shared/执行韧化协议-exec.md:44-46` | description 已显式声明 |
| **SDI-4 0.76** telemetry 矛盾 | `references/templates/status-template.md:202-203` | 由 SDI-1 0.93 token-cost opt-in 一并解决 |
| **SDI-4 0.92** controller 不读 host config vs 自我审计 | `references/agents/00-主控-扩展职责.md:94-95` | 「不读 host config」+「自我审计可见工具面」二者并不矛盾（前者指配置读取、后者指运行期观测），已在一致性 pass 中明确 |
| **SQP-2 0.75** permissions.md 缺用户警示 | `references/permissions.md:105` | 加用户警示 block：列出所有写盘路径 + Phase 0 同意门 + 默认单主控 |
| **Context-Inappropriate Capability 0.83** | 多处 | manifest 已声明为 opt-in operational telemetry；heartbeat 改为 Phase 0 opt-in |
| **Context-Inappropriate Capability 0.78** | 多处 | 同上 + description 已声明编排面 |
| **Description-Behavior Mismatch 0.93/0.87/0.89/0.93/0.8** | 多处 | description 扩展后与各 dispatch / controller 章节对齐 |
| **Description-Behavior Mismatch 0.91** status-template 自动建 audits/ 副本 | `status-template.md:133` | 改 opt-in |
| **Description-Behavior Mismatch 0.93** token-cost 收集 | `status-template.md:204` | 改 opt-in |
| **Missing User Warnings 0.75** | `permissions.md:105` | 已加 |

### 四、判为不修（附判据）

- **AE4 ×2**（`deliverables.md:1` / `status-template.md:1`）：官方判定 expected，控制字符扫描无 bidi / 零宽混淆；启发式误报，不修
- **E1 ×2**（OpenAlex / Crossref）：官方判定 expected（默认关闭 opt-in、只发检索词）

### 五、宿主加固（v2.12.44 落地的延续；本版未改）

- `tools.subagents.tools.deny` = 44 项
- `agents.defaults.subagents.maxSpawnDepth = 1`
- 回滚：`openclaw config unset tools.subagents.tools.deny` + `openclaw config unset agents.defaults.subagents.maxSpawnDepth`

### 六、★ 自查纪律（来自 lessons #375 + #376）

本批**先**下载 v2.12.44 官方扫描报告包（`clawhub scan download ... -o scan.zip`）、抽出 7 关键字段（verdict / confidence / findings / issueCount / score / severity / recommendation）后才动手；不下报告包 = 不算完成。修一致性而非加新措辞。

### 验收

- pytest · 自审门 · shellcheck · link-check · flow-check · check-version 全绿（见下）｜ SKILL.md **9,906 / 10,000** 棘轮内

---

## [v2.12.44] — 2026-09-15

> **主题：ClawHub 安全审计复核整改 —— 未加固主机改 fail-closed（默认单主控）、心跳写盘同意语去自相矛盾、期刊/渠道建议写入 manifest；配套宿主加固落地（子代理工具硬拒 + spawn 深度上限）。**
> **性质：安全整改（含一处默认行为收紧）+ 措辞一致性修复。无破坏性接口变更。**

### 一、★ 未加固主机改 fail-closed（消唯一 unexpected 项）

- **默认翻转**：宿主未配 `tools.subagents.tools.deny` / `maxSpawnDepth` 时，**多 Agent 不再是默认** —— Phase 0 须由主人**显式确认**「同意仅在软约束下跑多 Agent」；**未确认 ⇒ 直接单主控模式（不 spawn）**；敏感题材**无需确认即强制单主控**。`加固状态` 记 `未加固（已降级）`
- **判据分层**：宿主是否已加固由**主人核验并书面确认**；子代理侧**唯一可观测判据 = 启动自检回执**（非主控推断）
- **保留的部分**：「任意配置开箱可用」保留（**不拒绝启动**）；「未加固即拒跑（A 档）」仍否决（v2.12.32 实测曾致并行层自锁零产物）。**B 档本义即「默认降级单主控」——本次是把实现对齐该本义**
- 落 4 处：`SKILL.md` / `permissions.md`（§边界速查 + §未加固默认口径 + §为何不采纳补记）/ `host-hardening-recipe.md`

### 二、心跳写盘同意语义去矛盾（消两条高置信 finding）

- **删「运行本 skill 即表示主人已明示接受」**类**隐含同意**表述（`external-services.md` / `执行韧化协议-exec.md`）
- 改为**显式同意门**：心跳写盘唯一依据 = 主人对 Phase 0「将创建的文件清单」的**显式确认**，且清单**逐项**含 `.tmp/<角色>-heartbeat.md`；**主控自动列清单 / 主人沉默 / 「本来就要写盘」的推断，都不构成同意**；缺确认 ⇒ **不写 `.tmp/`、不开工**（fail-closed）
- `QUICKSTART.md`「运行即会写盘」→「**须先经 Phase 0 显式同意**，未确认前不写任何文件」

### 三、期刊/发布渠道建议写入 manifest（消 Description-Behavior Mismatch）

- `SKILL.md` frontmatter `description` 增列「**含同行评审与期刊/发布渠道匹配建议（advisory）**」—— 使 manifest 与 T9 实际行为一致
- T9 角色卡新增「**能力声明**」段：渠道建议属**声明范围内的 advisory 能力**、**不阻塞交付**、采纳权在主人

### 四、宿主加固落地（本批配套，非技能文件）

- `tools.subagents.tools.deny` = **44 项**（执行类 / 凭据 / 消息 / 记忆写入 / 设备 / 递归编排全拒；`deny wins` 覆盖继承策略）
- `agents.defaults.subagents.maxSpawnDepth = 1`（子代理成叶子，不能再派生孙代）
- 两者均 **hot reload**，无需重启网关

### 五、复核结论（判为不修，附判据）

- **AE4 ×2（`deliverables.md:1` / `status-template.md:1`）**：官方 ClawScan 判定 **expected** —— 与「中文正文 + 英文标识符 / 路径」混排一致，且**控制字符扫描未发现 bidi 覆盖或零宽混淆**；判为启发式误报，**不修**
- **E1 ×2（OpenAlex / Crossref）**：官方判定 **expected**（默认关闭的 opt-in、无需 Key、只发检索词）；保持现状，仅保留授权点同意约束
- Static analysis **clean** / VirusTotal **0/65**

### 验收

- pytest · 自审门 · shellcheck · link-check · flow-check 全绿（见下）｜ SKILL.md 棘轮内

---

## [v2.12.43] — 2026-09-15

> **主题：实战复盘 9 项（采 8）+ 外部安全审计 8 条（采 6）综合修订 —— 投稿域/工程域硬分离（消双漏检同型根因）、display-cap 截断应对、编排面口径收紧、产品中性披露、会话可见性收口。**
> **性质：机制修订（含两处口径收紧）+ 附带修复 2 项既有红门。无破坏性行为变更。**

### 一、P0（实战根因，必修 3 项）

- **投稿域 vs 工程域硬分离**（消实战 #P1-3 + #P1-4 同型双漏检）：新增两域定义 + **「投稿版禁入清单」**（头部工程元数据段 / `## 投稿就绪附录` 段 / 图表清单 / 主控签字 / 引用规范）；`final_assembly` 节点钉死「**只产投稿版**」；T8 终检 A1 判据扩为「含投稿域 vs 工程域归属正确」。落 5 处：`deliverables.md` / `agents/08-终检` / `可发表性判定表` A1 / `phase-order.yaml` / `dispatch/T8-终检`
- **display-cap 截断应对自动化**（消 5 次实测截断的主控手工捞取）：识别三信号（回传中途中止 / 缺 Stats line / 缺「已写盘 + 产物路径」声明）→ **磁盘产物优先** → 缺则按该角色会话拉 `sessions_history` 整合（**不轮询**）→ 标 `[主控 fallback 产物]` + `status.md` 记 `display_cap_truncated`。落 3 处：`dispatch-header` / `agents/00-主控` / `permissions` §边界速查
- **工具面实际阻断加固**：`capability_excess` 处置升级为**四步具名硬动作**（① 不采纳产物 ② 该档停用 ③ `status.md` 记 ④ 具名报告）；`加固状态` 判据钉死 = **子代理启动自检回执**（非主控推断）

### 二、应修（实战 3 项）

- **T5 反方段融入铁律**：T4 大纲「反方论证规划」必须为每段标**落位**（目标节 + 段位序号）；T5 按落位融入各节，**不得独立成章**（独立成章须大纲明文允许 + 主控拍板）；T5 自检加「反方段落位与大纲一致」
- **跨卡多口径标注**：T2 关键量化数据必填三字段「**主口径 / 扩展口径 / 来源差异说明**」；T3 优先引用主口径或并列双口径 + 边界声明；T7 新增「**跨卡数值一致性核验**」专项并在报告加「跨卡数值对账」小节
- **`audit_revision` 触发配结构化修订任务书**：4 关键字段（问题描述 / 修复位置 / 修复建议 / 优先级）缺一即不合格 → 主控**退回 T7 补全**（不得代填，防越权改写审计结论）

### 三、选修（实战 2 项）

- **测试模式三处披露校验**：T8 机械核对任务简报 / `status.md`「项目元数据」/ 交付说明三处一致，缺一 = **P1** 并重跑终检
- **字数判定表阈值示例**：新增备注 4 —— 以「上限 10,500」为例给出四档具体区间（≤ 达标 / 5% 内呈现信息 / 5-10% P1 / >10% P0）
- （实战 #9「删探测机制评估」= **观察项**，需 5 个项目样本后复核，本轮不改动）

### 四、★ 口径收紧（外部安全审计采 6 条）

- **产品中性披露**：投稿版披露文本**默认不出现任何产品 / 流水线 / 厂商名称**；**指名所用流水线 = 显式 opt-in**（Phase 0 询问，**默认否**，决定记任务简报）；**匿名 / 双盲评审默认省略产品识别语**；主人可替换 / 删除该段措辞而**不判门失败**（T8 只核「披露是否如实 + 是否符合期刊/机构政策」）；删除写手卡内「为避免扫描误报而中性化」这类**规避检测动机**的元注释
- **「零 exec」精确口径**：明确只指**执行类**工具（`exec`/`process`/`code_execution`）；`denied` 另含的 `browser`/`terminal`/`computer`/`nodes` 等**非执行类**工具由该清单另行覆盖；**显式申明主控另持编排与状态面**（`coordinator_only` 8 项 = 派发 / 收报告 / 记账的**设计内必需**能力，非特权扩张）
- **会话可见性收口**：会话类工具**仅限本项目本轮 spawn 的角色会话**（项目名 + 角色名匹配）；**禁**枚举 / 读取 / 取消无关会话，命中即不操作、不记录、不转述；`subagents(action=list)` 仅「完成事件疑似丢失」时**一次性**使用（非轮询）；`cancel` 非常规手段
- **授权点同意约束前置**：`SKILL.md` frontmatter `research_extra` 行注释 + 权限文档 opt-in 段**内嵌** Phase 0 同意约束（学术元数据 OpenAlex / Crossref = opt-in、默认关闭）

### 五、附带修复（既有红门 2 项，非本批引入）

- **`deliverables.md` M-Form-7 白名单回补「致谢」**：白名单声明与表格停在 **5** 节，与 v2.12.32「补入致谢」注释及可发表性 F 选项**自相矛盾**（`test_p1_3_whitelist_has_thanks` 长期红）→ 声明改 **6** 节 + 表格补第 6 行
- **`references/_shared/论衡仓库内教训.md` 补语言政策声明**（v2.12.42 新增该文件时漏注入 → 净化包构建门「语言政策声明缺失」长期红）→ 跑 `inject-lang-policy.py` 补齐

### 验收

- pytest **275 passed / 0 failed** ｜ 自审门 **26 PASS / 0 FAIL** ｜ SKILL.md **9,992 / 10,000** 字符（棘轮内）

---

## [v2.12.42] — 2026-09-15

> **主题：扫描收尾九项 —— 删记忆残留 / G14 清扫 + 机械门 / ★全删探测（业主裁决）/ ★B 档设计取舍明示（选项 A）。**
> **性质：安全整改 + 机制精简（探测整套删除）+ 新增机械门。**

### 一、P0×3

- **checkpoint-card 删「主控读记忆 / 记忆读取」**：v2.12.35 已删记忆支持，模板是过时残留（2026-09-15 扫描 AIG T05 实证）；改为「读当前项目材料」+ 可选服务两项
- **G14 stale 语言清扫累计 15 处**：v2.12.41 漏 5 处（asset-index / glossary×2 / 投稿就绪 / quickref / README×2 / SKILL 措辞 / permissions）—— 手工 grep 模式太窄
- **★ 新机械门** `tests/test_scan_stale_language.py`（3 项）：G14 stale 语言 / 探测 stale 语言 / 记忆能力复活 —— **首跑即抓 5 处漏网**，实证「清扫必须配机械门」

### 二、★ 全删探测（业主裁决 2026-09-15：
「全删探测」）

删掉整套「Phase 0 逐模型 1-token ping + 余额预检 + 派发前预算闸门」（回应扫描：模型清单枚举与主动探测超出写作流水线必要范围）：

- **改为静态映射**（读一次 `session_status` 配置清单，非探测、不查余额）+ **运行时首败降级**（`degraded` 自报 → 候选池下一档；配额耗尽 → 等主人拍板；同项目已确认失败 → 直接降档）
- **sessionKey / sessionId 一律不记录**（角色名即关联，聚合成本不需要会话标识）
- 教训 #236 残余风险（配置存在 ≠ 可用）由运行时降级承担 —— 撞墙成本从「Phase 0 多次探测」降为「一次失败调用 + 自动降档」
- 涉及 15 文件（status-template §4.6 重写 / 模型候选池 §二§三重写 / 4 张角色卡 / readme / coordinator / 关键协议 / deliverables / archive-sop / dispatch-header / design §3）

### 三、★ 选项 A（业主裁决）：T05 设计取舍明示

- **措辞降对比度**：「工具面超限 → 继续开工」→「工具面超限 → **呈主人裁决** + 敏感题材自动降单主控」（agents/00 + permissions）
- **README 新增「权限设计取舍」明示段**：B 档定位 + 铁律「工具面超限 ≠ 调用许可」+ v2.12.32 实测否决史 + 「**这是有意的设计取舍，不是未修复的缺陷**」

### 四、P1×4（消扫描 Intent-Code Divergence）

- **心跳↔Phase 0 同意绑定**（dispatch-header + 执行韧化协议-exec 各 1 句，消「写盘先于同意」读法，96-98%×3 条）
- **重试矩阵分层澄清**（任务级降级策略 vs 平台层恢复，消 89%）
- **能力自检消歧义**（自省自身会话可见工具面 ≠ 读宿主配置，消 93%）
- **代笔窄例外封闭清单**（P1-D/AI 披露/元叙事/≤5% → T8 亲修，逐条登记，消 87%）

### 五、扫描预期（下版核对）

| 项 | v2.12.41 实况 | v2.12.42 预期 |
|---|---|---|
| AIG checkpoint 记忆残留 | T05 Warning | **消失**（已删） |
| AIG 遥测采集 | T05 Warning（认可⑤但要求少采） | **转 expected/消失**（采集面本身收缩） |
| AIG T05 最小权限 | **Error/High** | 降档（README 明示设计取舍） |
| SS G14 矛盾（3 条） | 97/95/95% | **归零**（15 处全清 + 机械门钉死） |
| SS 探测/心跳矛盾 | 96-98% | 消（同意绑定 + 探测删除） |

### 验收

- pytest **275 passed**（含新增 3 项机械门）｜ 自审门 **26 PASS / 0 FAIL**
- flow ✓ / link ✓（406 条）｜ check-version v2.12.42 ｜ `SKILL.md` **9,969 / 10,000**

---

