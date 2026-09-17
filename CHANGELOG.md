# Changelog

> ⚠️ **范围说明（v2.12.47 起）**：本文件只保留**最近 5 期**；**v2.12.44 及更早**的全部章节逐字迁入 [`CHANGELOG-archive.md`](CHANGELOG-archive.md)。部分历史条目链接指向 `docs/` 或 `../outputs/` 中的**当时产物**（发布说明 / 审计报告 / 设计方案），这些文件**已随清理移除或归档**，链接可能失效——**属史料，不影响当前使用**。当前版本行为以 [`SKILL.md`](SKILL.md) 与 `references/` 为准。

论衡（`lunheng-article-pipeline`）版本变更记录。**本文件 + [`CHANGELOG-archive.md`](CHANGELOG-archive.md) 共同构成仓库内 changelog 的单一真源**（`scripts/changelog-check.py` 同时读取两份，「每个版本 tag 都有章节」的校验不受拆分影响）；GitHub [Releases](https://github.com/zuoyunlai/lunheng-article-pipeline/releases) 是同一内容的发布视图。

- **排序**：版本倒序（最新在前）。查找某一版本：`grep -n '^## \[v2.12' CHANGELOG.md CHANGELOG-archive.md`
- **章节标题**：`## [<tag>] — <发布日期>`；正文＝该版本 Release 正文逐字保留（早期 Release 由 GitHub 自动生成，正文天然偏薄，`python3 scripts/changelog-check.py --report` 可列出）。
- **发版流程**：建 GitHub Release 后执行 `python3 scripts/changelog-check.py --fill` 回填本节；也可直接手写章节。`--check` 校验「每个版本 tag 都有章节 + 围栏闭合 + 当前版本已记录」，`--online` 追加校验「每个版本 tag 都有 GitHub Release」。
- **发版前置闸（教训 #332 / #334）**：任何对外发版动作（push / tag / GitHub Release / 净化包）前先跑 `bash scripts/release-preflight.sh <tag>`——两查一停：**在飞链**（同项目 `status=running` 会话）/ **编号占用**（本地 tag + `git ls-remote --tags` 双向）/ **工作区干净**（`git status --porcelain`），任一不过即非 0 退出（10/11/12）；通过时打印「远端 master / 本地 HEAD / tag 区间 / 在飞链=0」四行现状。`scripts/create-github-release.sh` 的写路径已强制调用本闸（并自动带 `--allow-existing-tag`：② 口径 = 「编号是否被本链之外的人占用」，避免「先 tag、后补发 Release」被自己的闸自锁），`--dry-run` / `--check` 不进闸。闸只读：不自行 push / 打 tag / 建 Release。
- **非版本 tag**（`full-repo-consistency-audit-2026-09-06`、`before-batch1-optimization`）不进入本表。

---

## [v2.12.50] — 2026-09-17

> **主题：v2.12.49 后续修订——机械门空转止血（D-1/D-2，P0×2）+ 一致性回归收口预告（D-3/D-4，P1×2）。**
> **性质：纯缺陷修复（内部一致性 + 机械门能红）。无新增能力、无破坏性变更、无安全语义变化。**

### 一、机械门空转止血（D-1：能力断言 selfcheck 假绿灯 → 五路可失败断言）

- `scripts/capability-assert.py:127` 原写 `SKILL_DENIED & ALLOWED_CAPABILITIES`，而 `:88` `ALLOWED` 已减去 `FORBIDDEN（⊇ denied）` ⇒ 交集**数学上恒空** ⇒ 自检永不红（教训 #399「机械门必须能红」）。
- 改为五路可失败断言：① 解析守卫（denied/allowed 任一空即报错）② 派生一致性（FORBIDDEN/ALLOWED 必须等于真源现算，防派生集被清空后真空通过）③ 声面真交集（**不做减法**直接取 `SKILL_DECLARED & SKILL_DENIED`，命中即冲突）④ 行为断言（denied 真源每一项都必须被 `validate_capabilities` 拒绝）⑤ 镜像断言（允许面抽一项必须真被接受，防「一律拒绝」反向假绿灯）。
- **界定（不夸大）**：门 T 主体拦截仍有效（`self-audit-gate.sh:984` 逐项 T0 拒斥走 `:110/:117` 正常逻辑）。空转的只是 selfcheck 半句；本修**仅**让 selfcheck 真判红，不动主路径。

### 二、机械门空转止血（D-2：增量 M 门验证假绿灯 → fail-closed）

- `scripts/incremental_m_gate.py:354` 原写 `'passed': True, # 占位`，全文件**唯一** `passed` 赋值 ⇒ `main()` 的 `if failed:`（:407）不可达 ⇒ 任何输入都印「✓ 所有 M 门验证通过」。
- 现改为 fail-closed：`_validate_single_gate` 返回 `passed=False` / `status=unverified`；`main()` 空结果分支也直接 RC=1。M 门真验证见 `references/_shared/M-Gate-Algorithm.md`，由 agent 按流程执行。
- 同步说明：本工具**只做变更定位 + 依赖判定**，不产出「M 门通过」结论（任何 `passed:True` 都属于历史错误，**不得**回滚此约定）。

### 三、回归测试反向注入（锁死能红）

- `tests/test_capability_assert.py` 增至 10 项，含四类反向注入（denied 进允许档 / 禁用面派生集被清空 / denied 清单为空 / 验证器一律拒绝 → **全部必须让 `--selfcheck` 变红**）。
- `tests/test_incremental_m_gate.py` 增至 21 项，新增 `TestFailClosedContract` 三项反向注入（单门验证必须 passed=False / 空项目 CLI 必须 RC=1 / 真实变更 CLI 必须 RC=1）。
- 反向注入测试锁死契约：任何让假绿灯回潮的改动都会在 CI 阶段立刻被抓。

### 四、一致性回归预告（暂不修，攒批）

> 本版**仅**止血 P0（机械门空转）。下列两条 P1 一致性回归**已记录**于 `outputs/论衡-一致性审计-2026-09-17.md`，留待同批或下批处理：

- **D-3**：只读档「写盘责任主体」两套口径并存（主控代写盘 10 处 vs 角色直写 3 处，`permissions.md:61`「两径定义」与 `phase-order.yaml` 的 `t6/t7/g14/t9` 全 `write_authority: executor` 互斥，属 v2.7.x 已修过一次又被 v2.12.32/33 例外重开的回归）。
- **D-4**：`tests/test_flow_check.py` ≥10 处反向注入直接 `write_text` 真源 `references/_shared/phase-order.yaml` + 字数判定表 + 08-终检，仅靠 `try/finally` 恢复 → kill/超时/并行即污染真源。

**建议**：D-3 + D-4 合并走 **v2.12.51**（不攒批拖延：D-3 是真源互斥、D-4 是测试污染真源，两者都属「不该有的松」）。

### 五、验收

- `pytest`：326 → **329 passed**（新增 3 项反向注入：capability ×4 / incremental ×3；0 项失败）
- 自审门：**26 PASS / 0 FAIL**（与上版持平；门 H `#398 > 快照 #373` 为预存在 informational，已界定 #398 = 宿主类）
- `flow-check`：RC=0（与上版持平）
- `SKILL.md` 体量棘轮：仍在 ≤10000 字符内（与上版持平）
- 平台侧扫描 verdict：本版**无改动真源行为**，ClawHub `Moderate` 仍 = `CLEAN`（与上版持平）

## [v2.12.49] — 2026-09-17

> **主题：v2.12.48 后续修订——人环闸门真源化 + 零 exec 边界澄清 + M/T 系列机制修复。**
> **性质：架构行为修复 + 文档一致性治理 + 多处机械可验铁律落地。无新增能力（论衡 agent 零 exec 原则不变）。**

### 一、人环闸门真源化（修 P2-1）

- 4 个 owner_checkpoint（`phase0_definition` / `phase2_5_outline` / `phase3_5_insight` / `phase5_acceptance`）补 `blocking: true` + `owner_visible: true` + `timeout_fallback`；`phase-order.yaml` 头部结构约束补 ⑩
- `scripts/flow-check.py` 新增规则 12：顶层 `owner_checkpoints` 与 `kind: owner_checkpoint` 节点集**双向一致**；每节点须有 blocking/owner_visible/decisions/timeout_fallback
- `tests/test_flow_check.py` 增 3 项正向 + 1 项反向注入（去掉 phase5 的 blocking → 必须报错），防新规则退化成永真

### 二、删除 Phase 5 fail-open 节点（修 P2-2）

- 旧写法「Phase 5：不答 = 接受当前定稿」使 Phase 5 静默 60 分钟即等于主人拍板「接受」；且只活在散文，与「无明确决策 = 未通过」正面张力
- 现四节点一律 fail-closed：无应答 = 写 status `pending_owner` + 告警挂起。静默、主控推断、子代理回执、「产物已存在」均不得记为 accepted
- 旧口径在 `phase-order.yaml` 登记为「已删除的旧语义（防回潮）」，并有测试锁死

### 三、无应答分钟数归一（修 P3-1）

- 唯一真源 = `phase-order.yaml` 的 `owner_timeout_policy.no_answer_minutes: 60`
- `glossary-full.md` / `phase-2-details.md` / `执行韧化协议-design.md` 三处字面重列改为引用（一条款一真源）

### 四、`image_generate` 退出 opt-in 入 denied（M-12 反演）

- 封面与图件去留由主人手动操作，论衡 agent 零 exec 原则不变
- `denied` 从 40 项扩至 41 项（与 `video_generate` / `music_generate` / `tts` 同构）；工具级 opt-in 归零；服务级外发 4→3 类
- 同步 SKILL.md / permissions.md / 00-主控-coordinator.md / 00-主控-扩展职责.md / glossary-full.md / pipeline-readme.md / test_external_audit_fixes.py

### 五、M 系列机制修订（14 项）

> 详见仓库根 `outputs/论衡-修订方案-2026-09-16.md`（方案已审定）；本节仅摘要标题

- **M-1** 交付物指纹绑定（sha256 入 status.md `deliverables_fingerprint`）
- **M-2** 终态后修改必重开流水线（fail-closed）
- **M-3** 计数类断言真源（指向交付物文件，不重报数字）
- **M-4** G14 严重度参与判定（warning 不再静默通过）
- **M-5** P2 量化锚点 + 累积升级（5+ 同色 ⇒ 升档）
- **M-6** 轮次耗尽出口改三选一（不静默接受）
- **M-7** status.md 对账机械门（与 current_draft.md / final/ 双向断言）
- **M-8** 审计对象一致性断言
- **M-9** 48 必查清单加「严重度」列
- **M-10** 图件路径归一 + 局限性入真源
- **M-11** Phase 2.5 图位决策必答 + 机械门；**写 SVG 数据图表 = 论衡职责**（主控 `write` 手写，零 exec/零外发）
- **M-13** T8 后「主人自行操作建议清单」（封面 / SVG→PNG / 格式转换）
- **M-14** 字数口径单一化（真源 = 正文汉字数）

### 六、T 系列治本调整（7 项；T-7 已撤回）

> 架构层面修复，与本批次**同走 v2.12.49**（主人 2026-09-16 23:25 裁定 D-4 = 合并）；详修订方案 §三

- **T-1 派发禁摘要 + 上游落盘前置 + 差集断言**：只读档报告（T6/T7/T9/G14）必须**先落盘且非空**才允许派发下游（spawn 前置断言）；派发话术**逐项完整列**（项 ID + 行号 + 阈值 + 实测值；「等」字句 = 不合格）；交接报告新增 `upstream_read`（`upstream_ids ⊖ dispatched_ids ≠ ∅` ⇒ 派发阶段拦截）
- **T-2 降档换族 + 族级独立性 + 断路器**：降档**优先换 provider 族**；独立性判据改「**模型族不同**」（T6/T7/T9 族两两不同才算独立，否则只能写「信息独立达成 / 模型独立性不成立」）；**断路器**：顶配连续 2 次失败 ⇒ 不得自行全量降档，暂停呈报主人三选一
- **T-3 Phase 0 顶配档探活门**（≤3 次、间隔 ≥10s；失败当场三选一；结果含时间戳入简报 §模型映射；超 1 小时重探）—— 顶配不可用在 **Phase 0 暴露**，**不消耗 worker spawn**（`pre_spawn_enforcement.top_tier_liveness_gate`）
- **T-4 独立性声明族级字段**：审稿报告新增 `executor_model` / `model_family` / `independent_from`（**族级**判定）；同源时**不得**写「独立性达成」；该字段同时约束「是否读过过程材料」（防头部声明与正文自承**自相矛盾**）
- **T-5 修订净增上限**：单轮 **≤ 2%**（按正文汉字）；超限须**等量置换**；修订说明必填 `net_delta_cjk: +<N> (<pct>%)`；Phase 0 目标字数取上限 **92%**（实测反例：v1→v4 **+31.5%**）
- **T-6 `methodology_snapshot` 默认触发**：由 opt-in 改「**默认触发（简版 ≤2 节）+ 主人 opt_out**」（`on_opt_out: record_opt_out_in_status`，opt-out 与 not_triggered 语义分列）
- **T-8 引用体例单一化**：正文引用标记 ↔ 文献表编号**一一映射**，禁「正文 `[Lxx]` + 文献表 `[1]…[N]`」两套并存；M-Exist-1 新增「**引用体例层**」校验
- ~~**T-7 零 exec 边界澄清**~~ ❌ **已撤回**：核对设计真源后确认论衡不操作任何转换，**无需机制修订**（残留为运行侧措辞项，并入批次 1）

### 六·补、机械门与测试

- `scripts/flow-check.py` 新增规则 **13–22**：终态冻结 / 交付物指纹 / 审计对象一致 / 计数档位 / 轮次出口 / G14 严重度 / status 对账 / 图件路径 / 图位决策 / 主人操作清单 + 字数口径 / **T 系列全项**
- `tests/test_flow_check.py` 由 **49 → 60** 项；关键新增均带**反向注入**（去掉真源标记 ⇒ 门必须报错），防新规则退化成永真
- 本轮实测抓出并修复 2 处自身缺陷：① 反向注入仅替 1 处而同名字段在文件中有 2 处 ⇒ 注入被漏检（改全量替换）；② 候选池新措辞命中既有 stale-language 守卫（「派发…余额…预检」同句）⇒ 改写

### 七、零 exec 边界澄清（主人 2026-09-16 23:12 / 23:31 裁定）

- SVG 数据图表**生成** = 论衡职责（主控 `write` 纯文本，零 exec 零外发），不动
- SVG→PNG / 文生图封面 / 文档格式转换（docx/pdf/latex）= 主人 host shell 手动执行，论衡 agent 不操作
- 论衡 agent（含主控）零 shell 权限设计原则不变

### 八、修复 P3-2 误报（不改文件，仅澄清）

- 原判「3 处 `templates/...` 裸引用路径不可达」不成立——本仓库约定：references/ 下反引号裸路径以 **references/ 根**为基准；三条全部可达
- 「6 张图去留」具体决定 ≠ 「图件生成」流水线职责（教训 #389）

### 九、验收

- pytest **324 passed**（test_flow_check 由 49 → 60 项，含反向注入）
- 自审门 **26 PASS / 0 FAIL**
- SKILL.md 体量棘轮 **9855 ≤ 10000** 字符
- `flow-check.py` **RC=0**（规则 22 锁死 M/T 全项真源）
- 版本号同步覆盖 **90+ 项文件**（`sync-version.sh` 自动化）
- 提交链：`02db518 → dca71a7 → ac59099 → 41ff9eb → 2bee239 → 9a977bd → 388f01f → e361029 → 905d2ec → 8022aa4`（领先 origin **10** commits；**未打 tag / 未 push**，待主人批准）

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
