# Changelog

> ⚠️ **范围说明（v2.12.47 起）**：本文件只保留**最近 5 期**；**v2.12.41 及更早**的全部章节逐字迁入 [`CHANGELOG-archive.md`](CHANGELOG-archive.md)。部分历史条目链接指向 `docs/` 或 `../outputs/` 中的**当时产物**（发布说明 / 审计报告 / 设计方案），这些文件**已随清理移除或归档**，链接可能失效——**属史料，不影响当前使用**。当前版本行为以 [`SKILL.md`](SKILL.md) 与 `references/` 为准。

论衡（`lunheng-article-pipeline`）版本变更记录。**本文件 + [`CHANGELOG-archive.md`](CHANGELOG-archive.md) 共同构成仓库内 changelog 的单一真源**（`scripts/changelog-check.py` 同时读取两份，「每个版本 tag 都有章节」的校验不受拆分影响）；GitHub [Releases](https://github.com/zuoyunlai/lunheng-article-pipeline/releases) 是同一内容的发布视图。

- **排序**：版本倒序（最新在前）。查找某一版本：`grep -n '^## \[v2.12' CHANGELOG.md CHANGELOG-archive.md`
- **章节标题**：`## [<tag>] — <发布日期>`；正文＝该版本 Release 正文逐字保留（早期 Release 由 GitHub 自动生成，正文天然偏薄，`python3 scripts/changelog-check.py --report` 可列出）。
- **发版流程**：建 GitHub Release 后执行 `python3 scripts/changelog-check.py --fill` 回填本节；也可直接手写章节。`--check` 校验「每个版本 tag 都有章节 + 围栏闭合 + 当前版本已记录」，`--online` 追加校验「每个版本 tag 都有 GitHub Release」。
- **发版前置闸（教训 #332 / #334）**：任何对外发版动作（push / tag / GitHub Release / 净化包）前先跑 `bash scripts/release-preflight.sh <tag>`——两查一停：**在飞链**（同项目 `status=running` 会话）/ **编号占用**（本地 tag + `git ls-remote --tags` 双向）/ **工作区干净**（`git status --porcelain`），任一不过即非 0 退出（10/11/12）；通过时打印「远端 master / 本地 HEAD / tag 区间 / 在飞链=0」四行现状。`scripts/create-github-release.sh` 的写路径已强制调用本闸（并自动带 `--allow-existing-tag`：② 口径 = 「编号是否被本链之外的人占用」，避免「先 tag、后补发 Release」被自己的闸自锁），`--dry-run` / `--check` 不进闸。闸只读：不自行 push / 打 tag / 建 Release。
- **非版本 tag**（`full-repo-consistency-audit-2026-09-06`、`before-batch1-optimization`）不进入本表。

---

## [v2.12.48] — 2026-09-16

> **主题：纯 skill 定位收口——明确 OpenClaw 多 Agent 为平台能力，宿主配置不再是论衡运行前提。**
> **性质：C1 口径修订 + 权限边界收敛 + 状态模板与回归测试同步。**

### 一、纯 skill 与平台责任边界

- 明确论衡不要求、不读取、不修改宿主配置；OpenClaw 原生提供多 Agent、会话与工具策略能力
- 宿主 deny、sandbox、spawn 深度等机械限制降为维护者可选附录，不再作为启动、质量或交付条件
- worker 失败仍按单节点故障由主控接管并披露，不把宿主工具面差异写成论衡失败

### 二、C1 口径一致性修订

- 启动自检只核对本角色声明与当前会话可见工具面，不产生“未加固”项目状态
- 工具面出现未声明工具 = 观测提示；实际调用未声明工具才阻断并转主控接管
- 同步 SKILL.md、permissions、dispatch-header、主控职责、pipeline-readme、status-template、交接模板与宿主附录

### 三、验收

- pytest **285 passed**
- 自审门 **26 PASS / 0 FAIL**
- SKILL.md **9958 ≤ 10000** 字符
- 版本号同步覆盖 90 项文件

---

## [v2.12.47] — 2026-09-16

> **主题：v2.12.46 扫描整改落地 + 仓库冗余清理；changelog 分层（主文件 5 期 + 归档）。**
> **性质：一致性整改 + 仓库可维护性清理 + 文档结构分层。无新增能力、无破坏性行为变更。**

### 一、v2.12.46 ClawHub 扫描整改（8 文件）

- **协调器工具面对齐**：`00-主控-coordinator.md` 能力白名单与 `SKILL.md` frontmatter 16 项逐项对齐（删 `ov_*` / `openviking_tool_result_*` 共 9 项过声明）
- **脱敏升为条件强制**：`phase-3-details.md` 内幕 / 未公开案例 / 内部资料 / 个人隐私 4 类触发即强制（脱敏方式四选一，脱敏前不得写 `drafts/`）
- **数据流声明强化**：`01-文献检索` / `03-案例检索` 角色卡明列 OpenAlex / Crossref「仅发送检索关键词 + 排序/过滤参数；不发送稿件正文 / 各类卡 / 主人洞察；不携带身份 / 凭据」
- **术语消歧**：`dispatch-header.md` 区分模型 fallback（兑底换档）与主控 fallback（worker 节点接管）；T9 禁用主控 fallback
- **会话管理原语作用域**：`00-主控` 卡补「硬限定主控自己 spawn 的子代理树」
- **引用政策**：T1 派发「默认 GB/T」改为「不静默 fallback」，绑定回任务简报
- **T9 触发**：`phase-order.yaml` 注释与 `condition_definitions` 对齐（体裁不再机械门控，仅靠 consent）
- **T9 交接报告**：移除「主控 fallback 亲出」（T9 违反独立性硬定义，失败走 `degraded_executor: T9` 披露，不补做）

### 二、仓库冗余清理

- 删除 `references/_shared/m_exist_1_diff.sh`：零 exec 立场下主控永久不可达（唯一使用方式是宿主 shell 手跑，与「纯 skill」定位冲突）；同步清理 `build-clawhub-release.sh` 中配套的 `exclude` / `rm` 失效引用
- `references/_shared/lessons-max.snapshot` 加入发布包排除清单（rsync + 非 rsync 两分支）—— 按该文件头注自述「不随包交付」修正长期矛盾；该文件是门 H 反向差集的 **hermetic 判据基准**，**必须留在仓库**
- 删除仓库外过期产物与工作区缓存（`clawhub-scan…-2.12.37.zip` / `__pycache__` / `.pytest_cache`）

### 三、changelog 分层（主文件 5 期 + 归档）

- `CHANGELOG.md` 只保留**最近 5 期**（本版起）；v2.12.41 及更早逐字迁入新增的 `CHANGELOG-archive.md`
- 拆分**逐字无损**（170 章节全覆盖，逐章内容比对零差异）
- `scripts/changelog-check.py` 改为读两份：`--check` 校验面跨两份（「每个版本 tag 都有章节」纪律不变）；`--fill` 不再把归档版本灌回主文件；围栏闭合检查与 `--report` 同步覆盖两份
- **新增主文件容量门**：主文件保有章节数 > 5 即红（防「加新版忘轮转」）
- 同步面：`self-audit-gate.sh` 历史资产排除名单补归档（防空历史「教训 #N」触发门 M/M.3/M.4 永久误报）；`build-clawhub-release.sh` 归档纳入 `exclude` / `rm` / `FORBIDDEN_IN_PACKAGE`；`changelog-check.yml` 触发路径补归档；`README.md` 口径同步

### 四、验收

- `pytest` **285 passed**；自审门 **26 PASS / 0 FAIL**；`changelog-check --check` 通过；`flow-check` / `link-check`（425 链 / 89 md） / `check-version` 全绿
- `SKILL.md` 体量 **9954 ≤ 10000** 字符（棘轮守约）

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

