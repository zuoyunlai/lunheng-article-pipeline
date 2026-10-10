# Changelog

---

## [v2.18.1] — 2026-10-10 · 反哺回灌（冒烟反哺 7 条）

> 背景：v2.18.0 运行模式冒烟的 `audits/反哺报告-v2.md` 提出 7 条建议；主人令「制定修订方案后开始修订」（机制保护 v2.12.40 的人工 approve 已给出）。
> 性质：**纪律与文档回灌**；不改流程节点、不改 G/M 门计数、不新增 flow-check 规则、`metadata.tools` 与 denied 真源零变化。

### 1. 工具可达性（FB-01 / FB-02）

- `dispatch-header.md` 增「**工具可达性前提**」：本 skill 假设 worker 直接可见 read/write/edit/检索类工具；**前提不满足时唯一处置 = `capability_excess` 阻断 + 主控接管 + L1 披露**；**禁止**改用 exec 总线（exec 属工具面超限，不是授权通道）。
- 交接报告 `runtime_tool_surface` 增 `call_channel` 必填（`direct` / `code-mode`）；**主控不采信未标通道的自报**，核验以**产物在盘**为准。

### 2. 派发面（FB-03）

- `skill-entry-appendix.md` §一 spawn 参数表增 `taskName`：平台强制 ASCII（`[a-z][a-z0-9_-]*`），中文/大写/空格一律被拒（实测 `T1-文献检索` 被打回）；建议 `t1-lit-scout` 形态。

### 3. 主控运行纪律（FB-04 / FB-08）

- `主动介入机制.md` 增「判 worker 存活性**以实时 `subagents(action=list)` 为准**，不信宿主内部快照」——实测快照陈旧（报「无活动子代理」而实时 2 个 running）会误触发「换族重派」，白烧一轮且可能覆盖并行主任务。
- `关键协议.md` 增「**判级分歧并列纪律**」（§二·补）：同一缺陷两门判级不同时必须并列记录、**不得择一掩盖**、交付就绪取更严一侧、采纳权在主人。实测两例：论点编号断裂（T7 **P2-1** / T9 **P0-1**）；`[L03]`（T7 判非缺陷 / T9 判 **P0-3**）。

### 4. 人在环与宿主文档（FB-06 / FB-07）

- `checkpoint-card-template.md` 的 ask_user **降级触发收窄为两条**（工具未装配 / standalone 无 binding 且不在结构化 UI）；明确「无 native 控件 ≠ 不支持」「多问多选只降渲染、仍可答」「`no_answer` ≠ 回退（走 `pending_owner_halt`）」。
- `QUICKSTART.md` / `README.md` 增**宿主工具面要求**（含 `sessions_yield` 缺失时的降级写法、`ask_user` 应直连而非经 Code Mode 发起）。

### 5. 机械件

- 新增 `tests/test_feedback_backflow.py`（7 条规则的文本面存在性 + 反向注入）。
- 版本 v2.18.0 → **v2.18.1**（同长度替换，门 Y 棘轮中性）；温层轮转 v2.16.0 入 `CHANGELOG-archive.md`，ceiling 同步实测。

---

## [v2.18.0] — 2026-10-10 · 运行模式统一（全自动 ↔ 人在四环）

> 背景：业主定案（2026-10-10）——Phase 0 二选一显式确认：① 全自动流水线（推荐）② 人在四环；全自动 = 大纲自动通过、初稿后无洞察补充、数据图表按推荐、终稿自动验收。
> 性质：**新增 Phase 0 运行模式预授权机制 + 伴生人环修复（H-1/H-2/H-5/H-6/H-9/M-2）**；不改流程节点数、不改 G/M 门计数、不新增 flow-check 规则、`metadata.tools` 与 denied 真源零变化。

### 1. 核心机制：预授权 ≠ 自动继续（M-1 闭合）

- 复用 status「运行性质」扩三值：`生产·人在四环` / `生产·全自动` / `测试模式`；唯一真源 = 新文件 `_shared/真源/运行模式对照表.md`（27 节点 × 两模式行为矩阵 + 永不自动停点清单 + 运行期模式切换）。
- 全自动下 2.5/3.5/5 仍写**合法枚举 decision**（approved / no_insight / accepted，词表零新增）+ `preauthorization_basis` 留痕；`checkpoint_status` 增 `preauthorized` 枚举（仅本模式合法）；`silence_doctrine.forbidden_kinds` 语义零改动——预授权扩大化 = auto_continue（阻断级，`tests/test_run_mode.py` 锁死）。

### 2. 作用域边界（全自动只免例行拍板，不免出事判断）

- 自动取值：2.5 → approved + 采用 T4 建议（figures 可为 0，reason 必填）；3.5 → no_insight；5 → accepted（acceptance_reconciliation 照跑 + delivery_readiness 机械判定二态，不得虚报）。
- 永不自动（两模式一致）：provider 静默三选 / 修订与回查耗尽三选 / write_failed / 对账失败 / 同意门 / capability_excess / 全部质量门 / pipeline-doctor blocked / 改方向插话。
- **外发同意与运行模式正交**（关键协议确定性规则第 4 条）：选全自动 ≠ 同意外发。运行期切换：暂停→确认→改简报+留痕；已消费节点不追溯重开；测试模式禁中途互切。

### 3. 伴生人环修复

- **H-1**：目标语言「不设默认」与 R-11 次屏举例互斥 → 拍板 2-B：随核心决策单行确认（「产出语言：X（按你的请求；要改请直说）」），无请求语言可循时必须单独问；语言政策注入头/注入器零改动。
- **H-2**：R-11 增两类例外——fail-closed 同意类不进次屏（外发四选一与可选服务保持首屏取舍）；目标语言随核心决策确认。
- **H-5**：Phase 5 卡两屏化（首屏 = 核心四选 + 对账四项 + 就绪二态；次屏 = 可发表性 6 选项 + M-13 四类 + 附录勾选）。
- **H-6**：ask_user 适用面扩 Phase 0（三枚举组：进线态 / 外发四选一 / 可选服务多选）。
- **H-9**：QUICKSTART 宿主适配补 ask_user 可选回退 + viz 工件降级路径。
- **M-2**：可发表性 3.4 人类决策判据扩「Phase 0 预授权说明」；§6.1 增预授权缺失兜底（判未决策 → halt，不得自动接受）；T8 三处披露核对扩全自动 + 四项新增核对；投稿版禁入清单 4 处扩「全自动模式披露」。

### 4. 机械件同步

- phase-order 状态机零改动（台账 §四-3 铁律：装配视图/索引上调额度已用尽，新增真源一律沉旁侧文件）——运行模式唯一真源 = 新文件 `_shared/真源/运行模式对照表.md`（27 节点 × 两模式行为矩阵 + 永不自动停点 + 模式切换），接线面 = 关键协议（Phase 0 必确认 + 确定性规则第 4 条 + 非节点输入表）+ status-template（运行性质三值 + preauthorized 枚举）+ checkpoint 卡（短路协议第 0 步 + R-11 两类例外）+ 两级任务简报模板；`counts.yaml` version_files 99→100，对照表新入版本矩阵（check-version.sh / sync-version.sh / .pkg-manifest.txt）；温层轮转 v2.15.13 入 CHANGELOG-archive.md，棘轮同步实测。
- 版本 v2.17.1 → **v2.18.0**（`counts.yaml` version_files 99→100；运行模式对照表.md 新入版本矩阵：check-version.sh / sync-version.sh / .pkg-manifest.txt）；温层轮转 v2.15.13 入 CHANGELOG-archive.md，棘轮同步实测（发版轮转致水位上移 ⇒ 同步实测，非内容膨胀；同 v2.15.14 先例）。
- 新增 `tests/test_run_mode.py`（10 断言：三值四载体一致 / 对照表落值 ∈ 节点枚举 + 状态机零改动锁 / forbidden_kinds 锁 / 生产方载体 / 三处披露 + preauthorized 枚举 / 3.4 预授权 + §6.1 兕底 / version_files / manifest+sync / 禁入清单 + AI 声明区分 / 停点键名 + 27 节点矩阵 + 短路协议）。

---

## [v2.17.1] — 2026-10-10 · 运行期可视化交付契约（零新权限）

> 背景：主人问「论衡能否在 OpenClaw 可视化面板显示运行报告与校验结果」。审计结论：**面板渲染属宿主侧能力**；论衡声明面内 `show_widget` / `dashboard` / `portal` / `canvas` **均在 denied 唯一真源内**（v2.11.x 回应 ClawHub 扫描器「Context-Inappropriate Capability」所加），本版**不移出、不宽限**。
> 性质：**纯文档 + 工件契约**；不新增工具档、不改 `metadata.tools`、不改 denied 真源与 `denied_count`、不新增 G/M 门、不新增流水线节点。

### 1. 新增「运行期可视化交付契约」

- 论衡侧新增运行期工件 `viz/index.html`：主控用 `write` 产出的自包含单文件视图（阶段树 / 闸门通过情况 / T9 评分 / 修订轮次 / 降级与接管记录 / 字数与图件计数）。
- 硬约束：① 零外链（CSS 与 SVG 全内联）；② 零 exec（纯文本写入）；③ 不引入新外发类别。
- 位置纪律：与 `final/图件/*.svg` 并列但**不进 `final/`** —— 属运行期遥测视图，按 `status.md` 同档管理，不属交付物；Phase 0「将创建文件」清单须先列入。

### 2. 职责分离（本版的核心判据）

- **论衡 = 只写工件**：声明面保持零面板工具（`denied` 优先，`show_widget` 等永不移出）。
- **宿主 = 只渲面板**：把该工件呈现到 OpenClaw 面板是**宿主会话**职责；宿主未提供该能力时工件退化为可直接打开的文件，功能不减。

### 3. 边界与不变量

- 工具面零变化：`metadata.tools` 五档（`base` / `coordinator_only` / `research_extra` / `academic_extra`）、`denied_count`、`denied_high_risk` **逐字节未改**。
- 刷新节奏与「方法论足迹面板」同源：阶段级（**非秒级流式**）；真·流式面板需独立 HTTP + WebSocket 服务，属另一项目职责，不在论衡内。

---

## [v2.17.0] — 2026-10-09 · 素材与论据检索升级（学术检索层接入 + 一致性修复）

> 背景：主人要求审计论衡「素材与论据检索」面的全面性 / 精准性 / 真实性 / 冗余 / token 成本，并据此升级。
> 性质：**检索能力与一致性修复**；新增 1 工具档（`academic_extra`，opt-in）+ 1 模板（检索覆盖矩阵）+ Phase 1 覆盖对账环节；不新增 G/M 门计数；不新增流水线节点。

### 1. P0 一致性缺陷：决策树引用了声明面外的工具名

- 实测：T1/T2/T3 角色卡的「工具选用决策树」引用 `exa_search` / `consensus_search` / `AI4Scholar_search` / `multi_search` / `search_google_scholar` 五个名字，其中**前四个在标准 OpenClaw 环境不存在**，且**全部不在 `research_extra` 白名单**内。
- 危害：宿主若确实装了某工具，worker 按树调用即「调用声明面外工具」→ 按既有纪律属 `capability_excess` **阻断级**——角色卡与白名单自相矛盾。
- 修复：v2.17.0 起决策树只引用 frontmatter 声明面内的真实工具名；决策树真源收敛到角色卡，dispatch 只留纪律（消除 3 份重复树）。

### 2. 新增 `academic_extra` 学术检索层（23 项，opt-in）

- 接入宿主学术插件工具族：结构化检索（`search_semantic` / `search_google_scholar` / `search_arxiv` / `search_pubmed` 等）、元数据核验（`search_semantic_paper_match` / `get_semantic_paper_batch`）、引文图谱（`get_semantic_citations` / `get_semantic_references`）、全文读取（`read_by_doi` / `read_arxiv_paper` 等）。
- 归类：并入 [`external-services.md`] 既有类别 ②「学术检索与元数据」（默认关闭、Phase 0 勾选；**不新增第 4 类**）；外发数据形态不变（仅关键词 / DOI / 标题；全文类工具为读入）。
- 降级：宿主未装插件 ⇒ 全层不可见 ⇒ 决策树自动回落默认层，**零行为变化**。
- 收益：真实性（引文核验由「网页比对」升级为数据库主键比对）、全面性（前向/后向引文滚雪球 + 预印本）、精准性（结构化元数据）、成本（批量接口单次可达数百条）。

### 3. 新增「检索覆盖矩阵」（Phase 0 建表 → Phase 1 对账）

- 针对三检索员「各查各的」导致的子问题集体漏检：Phase 0 拆题时由主控建 3-5 子问题 × L/D/C 需求矩阵（模板 = `templates/检索覆盖矩阵-template.md`）。
- Phase 1 新增「覆盖对账」四步（数量对账 → 缺口分类 → 冲突仲裁 → 冻结）：客观缺口写入局限性，检索缺口触发 T1b 补检索；同指标多来源矛盾强制并列 + 口径归因。
- 三检索员任务首步新增「检索分工」与「检索覆盖清单」留痕，使「全面性」可度量、可审计。

### 4. 冗余与成本治理

- 消除 dispatch 与角色卡之间 3 份重复决策树（真源收敛到角色卡）。
- `SKILL.md` 入口压缩：条目清单类内容回归真源文件（G18 12 项 / T9 维度档位 / 派发计数），全文 9734 → 8977 字符（守住 R-22 预算与 门 V）。
- `read_budget` 新增检索档默认（N=2 / M=4 / K=12）——检索密集而非读密集，原 K=8 会在产卡前耗尽。
- 清理仓库内 200 个 2026-10-08 遗留的 `*.bak.*` 备份（.gitignore 内，污染净化包一致性门 G）。

### 5. 同步面

- frontmatter `metadata.tools.academic_extra`（23 项）+ `subagent_tiers.research` 增挂该档；`工具能力边界.md` 计数 15 → 38；`permissions.md` 五档表、`dispatch-header.md` `allow_research`、同意门判定表、`关键协议.md`、`glossary-full.md`、`pipeline-readme.md` 同步。
- 测试：`test_tool_surface_consistency.py` 计数改为**从 frontmatter 推导**（防再漂移）。
- 新增模板同时登记 `scripts/.pkg-manifest.txt`。

---

## [v2.16.1] — 2026-10-08 · changelog 排水机制修复（纠 2.16.0 误判）

> 背景：2.16.0 发布后核查发现 ClawHub 上该版 changelog 是平台自动生成的假摘要（教训 #354 复发）；顺藤排查 changelog 分层机制时，误判「温层撞 ceiling 与主文件 5 期门互斥」，主人拍板 **A**（修机制）后实测推翻了该误判。
> 性质：**仅机制与门判据修正**；不改流水线节点、不改 G/M 门计数、不改门 Y 棘轮；不新增产品功能。

### 1. 误判纠正：ceiling 语义是「上限 == 实测」，不存在「余量归零 ⇒ 两门互斥」

- 实测 `test_changelog_archive_ratchet` 第 ①② 条均断言 `actual == CHANGELOG_ARCHIVE_CEIL` ⇒ **每次轮转后同步 ceiling 到新实测就是正常流程**（v2.15.12、v2.15.14 皆如此），并非「放宽上限」。
- 故上一轮所称「温层 ceiling 归零 ⇒ 强制轮转必然撑破 ceiling ⇒ 两门互斥」**不成立**；本版据实纠正，避免后人再按错误前提改动机制。
- 另一处误判：`changelog_files()` 本就返回**三份**文件（主 + 温 + 冷），`documented` 早已含冷层 ⇒「下沉会让 tag 失去章节」**不成立**。当时误信第 196 行那句过时文案（只写「主文件 + 归档」，漏冷层），未读实现。

### 2. 实修：排水出口此前指向 gitignored 路径（唯一真缺陷）

- 温层超限告警一直指示「冷归档到 `docs/history/`」，而 `.gitignore` 第 4 行排除 `docs/` ⇒ 照做会让章节**从版本控制消失**。已改指 `CHANGELOG_COLD`（`references/_shared/治理/changelog-cold-v2.0-v2.12.md`）：该文件**在版本控制内**，且**已参与**「每个版本 tag 都有章节」校验集合。
- 冷层新增同款棘轮 `CHANGELOG_COLD_CEIL`（v2.16.1）—— 否则「温层排水」只是把无界问题平移到冷层；冷层撞顶时唯一合规出路为 GitHub Release 视图。

### 3. 实际排水与回归门

- 温层 20 期（v2.12.48 – v2.12.29）下沉冷层：温层 260196 → 170714 B，冷层 271296 → 360777 B；`documented` 章节总数 **221 期不变**（tag 解析不受影响），`changelog-check` EXIT=0。
- 新增 4 条回归门（`tests/test_changelog_archive_ratchet.py`）：① 排水目标是冷层且**在版本控制内**、并断言 `docs/` 确被 .gitignore 排除（前提失效即红）② 冷层必须参与 `changelog_files()` ③ 冷层 ceiling == 实测 ④ 生效代码不得再指示 `docs/history/`（**只扫代码行不扫注释**——修复说明注释会刻意引用旧指引原文，全文扫描会自证失败）。
- 2.16.1 轮转 v2.15.10 入温层，ceiling 同步实测 176488 B。

### 4. 已知遗留（未动）

- ClawHub **2.16.0 的 changelog 仍是假摘要**，同版本号不可重发修正 ⇒ 本版以 `publish-clawhub.sh` 发布，正文取自本章节。教训：`changelogSource` 字段不可信，须实读 changelog 文本。
- `⚠️ CHANGELOG 有章节但无 tag：v2.15.7`（历史遗留）。

---

