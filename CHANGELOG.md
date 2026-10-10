# Changelog

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

## [v2.16.0] — 2026-10-08 · 全量审计修订（里程碑：新增交付级闸门）

> 背景：对 v2.15.13 做只读全量审计（26 节点真源 + 四个人环节点 + 修订回环 + 上下文契约 + 测试面 + 历史实跑交叉核验），综合评分 **7.1/10**；产出 **12 项修订清单（P0×4 / P1×4 / P2×4）**、4 个施工批次、4 个待主人拍板项。主人拍板 **A1**（投稿就绪升独立闸门）/ **B1**（Phase 1.5 拆两求值点）/ **C1**（状态真源收敛）。
> 性质：**新增 1 交付级闸门 + 1 节点 + 2 组判据单源**；节点数 26→27；不新增 G/M 门计数；不新增 flow-check 规则（规则数保持 49/50）。
> 审计与施工报告：`reports/2026-10-08-审计修订计划-v2.15.13.md`（含逐项证据、负例与踩坑复盘）。

### 1. 终态假绿灯面（P0，新增交付级闸门）

- **R-2（C1）** `status.md` §一 头部摘要**降为派生视图**（以详情段为准，禁独立编辑本节「追平」）；新增 `acceptance_reconciliation` + 四项前置对账（决策齐 / 报告齐 / 状态自洽 / 产物在盘），判据落 `可发表性判定表.md` §六·6.1。依据：2026-10-06 实跑中头部写「已通过 Phase 5 验收」而同文件 `Phase 3.5 = 未决策`、`T7.5 = ⬜ Inbox`、`status_json` 停在项目早期。
- **R-3（A1，里程碑）** 新增 `delivery_readiness: [submission_ready, accepted_with_open_items]`（**必填二态，禁留空**）；`submission_ready` 四项必要条件见 §六·6.2（含「末轮 P0/P1 修订须经独立审计员复核」）；Phase 5 卡点明 **`accepted` ≠ `submission_ready`**。依据：同次实跑 T9 盲审 22/30（minor revision）、引文体例 D 项 ⚠️、末轮修订未经独立审计员复核，仍可「按现状接受」。

### 2. 流程时序与契约自洽

- **R-1（B1）** Phase 1.5 拆两个求值点：原单节点（seq 4）同时承载「简报标记」与「T2.5 红数据未回溯」，却**早于** `t2_5_integrity`(seq 5) ⇒ 红数据项首次到达**恒为假**且被 `on_not_triggered` 静默吞掉（与「闸门真没跑」不可分）。新增 `phase1_5b_post_t2_5_review`(seq 6) 承接红数据求值；旧节点只认简报标记。条件键拆为 `phase1_5_brief_flag_trigger` / `phase1_5b_red_data_trigger`。**节点数 26→27**。
- **R-4** `route_tier.md` 族数算术错误：原文「至少 2 族可满足 T6/T7/T9 三节点两两互异」——**三节点两两互异需 3 族**。拆为 `writer_audit_distinct_families ≥ 2` 与 `audit_full_independence_families ≥ 3` 两判据，N=2 时后者必判 `degraded`。
- **R-5** 取消 `phase0_route`「无记录 = 走默认链」fail-open 尾巴（与 `silence_doctrine` 正面冲突）；`pre_spawn_enforcement.precondition` 增判据，缺记录判 `path_or_param_error`。
- **R-6** `terminal_freeze` 重开链改**依赖序**：原序 `g14→t9_review→final_assembly` 与 `t9_review.input = final/定稿.md`（seq 22 > 21）矛盾，按原序执行等于让盲审读**旧版定稿**。
- **R-7** `可发表性判定表.md` 伪代码对齐判据列：`check_charts` 由 `>= 5` 改 `== 拍板 N`（原伪代码比判据宽松）；`check_citation_ordering` 补 `order_mismatch`——**「顺序编码闭环」判据此前从未被伪代码实现**。
- **R-9** `owner_checkpoint.blocks`（局部阻塞）纳入 flow-check **规则 12**（不开新规则，总数保持 49/50）。
- **R-11** Checkpoint 卡两层呈现：首屏 ⛔ 待决策（≤1 核心 + 2 取舍）/ 次屏 ✅ 已落定（不阻塞但**仍须留痕**）。依据：Phase 0 一屏 6 项、主人只答 1-2 项、其余静默与「已答」不可分。

### 3. 构建门与棘轮

- **门 Y 升为硬门（本日实测发现的治理缺陷）**：此前 `BULK_RATCHET_OK=0` **不写 `FAILED[]`**，超限只 `warn` ⇒ 「只许降」棘轮形同建议（当日两次超限 +273 B / +94 B，gate 均 `exit 0`）。补聚合 `fail`；逃生口沿用 `LUNHENG_BULK_RATCHET`。
- 新增切片同步登记 **两份清单**：`scripts/.pkg-manifest.txt` 与 `build-clawhub-release.sh` 的 `SHARED_ADMITTED`（后者须保持 `LC_ALL=C` 排序）。**门 G 只验不建**：修完后须在默认 `OUTPUTS_ROOT` 重建才能转绿。
- 棘轮台账按 v2.15.13 既有先例**累加至原 open 行**（未销账不新开行），并在 §五 标注 **`phase-order.yaml` / `index.yaml` 上调额度已用尽**（§四-3 铁律）⇒ 后续内容须沉旁侧真源。
- 升版 `2.15.13 → 2.16.0`：版本串由 7 字符缩为 6 字符（`2.15.13` 5 位数字 / `2.16.0` 4 位），四个必读文件**各减 1 B**，方向与「只许降」一致，`ceils` 无需上调。

### 4. 验证与已知边界

- 自审门 **42 PASS / 0 FAIL**（`exit 0`）；全量 pytest **618 passed / 1 skipped / 0 failed**（新增 2 条测试前；其所在文件单独验证 19/19）。
- **负例注入 12/12 捕获**：R-1~R-4、R-5、R-6、R-7、R-9、R-11 边界、门 Y 硬门、`hash_mismatch` 降级、「不得判通过」边界被抹。
- 已知边界：① 门 G 依赖默认 `OUTPUTS_ROOT` 的既有包，改动后需重建；② `index.yaml` 余量 0 B，内容新增前须先做分层提案；③ flow-check 规则 49/50，仅余 1 条额度；④ `hash_mismatch` 分支在真实项目中的执行仍待主人回填一次 `sha256sum`。

---

## [v2.15.13] — 2026-10-07 · 实测反哺修订（16 项 merge，含模型路由三档真源）

> 背景：`run/2026-10-06-ai风格剥削与美学权利` 全量档实跑的反哺报告（`audits/反哺报告-v2.md`，T7 未产后主控 Phase 5 补写，经两轮复核修正）提出 14 项 FB + FB-02a + R-04；主人 2026-10-07 21:03 指令「开始修订，全部修订」，并拍板「模型路由三档由 Phase 0 主人选择」。
> 方法论：逐项先实测核实再动手；修订过程自身两度回改（v2.1 字数口径 / v2.2 T5b+探活叙事），教训 #523 沉淀「否定型修订先穷尽权威留痕与全部工件口径」。
> 性质：**新建 1 真源 + 14 文件条款落地 + 4 checkpoint 局部阻塞 + 机械件同步**；不改节点数、不改 G/M 门计数、不改门判据总数。

### 1. 模型路由三档（R-04 + FB-10 + FB-11，新建真源）

- **新建 `references/_shared/真源/route_tier.md`**（单一真源）：T1 继承主对话 / T2 同平台换能力 / T3 跨平台换族；Phase 0 三档探活（T3 需 ≥2 互异族）+ **主人选择提示**（默认链 T1→T2→T3，T7/T9 固定 T3）+ fallback 升级链（**配额类 429/402 不计 retry_limit**；升档留痕 `route_degraded` 三处）；链外中途换族须回主人确认（实测 17:38 T7 换族未确认的缺口）。
- `模型候选池.md` §二·补·2 接线（不重列）；§三 增「配额类失败不计同质 retry」。
- `t9_review.yaml` `independence_failure_policy` 增 `quota_class_retry: not_homogeneous` + `cross_family_retry: first_class_action` + 缺失呈现三要素（status_record 注释）。
- `dispatch-header.md` 增 route_tier 字段块；`SKILL.md` Phase 0 增第 7 步指针；`permissions.md` 配额预授权交叉引用。

### 2. 读密集与修订安全（FB-01 + FB-02 + FB-14）

- `dispatch-header.md` 增 **read_budget 必填字段**（默认 1/4/8/3500）；`主动介入机制.md` 硬卡表增**读密集 ×1.5** 注 + **超硬卡处置判据**（磁盘有产物接受 partial / 零回传换族重派，取代临场判断）。
- T5 派发 + 写手卡：**cp 基线升为强制**（禁 write 整稿）+ `read_basis=<fresh|stale_suspected>` + **结构探针**（edit occurrence 自证唯一）+ 断言式批量替换路径；`关键协议.md` 重要写入完整性同步（含**主控兑底版本链** drafts/版本链.md）。

### 3. 审计判据补齐（FB-05 + FB-06 + FB-07 + FB-02a）

- G16 增第 5 类「任务书指令残留」机械判据（`须[^，。；]{0,12}：` 等，命中即 P1；whitelist：直接引语/法条原文/G14 结构必写段）——实测 13 处三层防御全漏。
- G4-3 扩为**三格式图位门**：数量 ≥ 拍板 + **编号单调递增**（防 1→2→4→3）+ **交叉引用一致**（防错号）；T4 派发/角色卡增「按插入位置出现顺序编号」铁律；T7 派发/角色卡增 b/c 必查；T8 增组装后复查 + G16⑤ 终检。
- G14 复检严格度档增第 3 条：指令残留模式并入复检词表（含 whitelist 与「禁笼统报 0」——实测自报全部清除与实测 4 处不符）。

### 4. 口径与流程（FB-03 + FB-04 + FB-08 + FB-09 + FB-12 + FB-13）

- `permissions.md` 新增**执行器降级路径**节（留痕三要求 + 独立性边界：降级不得生成审计结论；主控亲为审计须异族）。
- 字数判定表 §七 增**下限型要求行**（body_floor；自设带宽 = floor+20% 非契约）+ **口径强制标注纪律**（禁跨口径比较——实测草稿 12,978 vs 定稿 14,138 双口径未声明制造虚高读数）。
- 可发表性 4.1 并入**同体系门 + 三轨→单轨交付层映射**（T8 交付前置，映射表附交付说明）——不动 48 项计数。
- **反哺报告后移 Phase 5**：T7 不再产（只产审计报告）；主控基于全流程留痕撰写；`反哺报告处理.md` 改写第 1 步；T7 卡/派发同步（交付单报告）。
- 四个 owner_checkpoint 切片增 `blocks: [节点列表]` 局部阻塞字段（Phase 2.5 等待期允许 t1b 并行等，实测自行并行的规则化）。
- M 门可复核判定协议增第 5 字段 **`basis: mechanical|llm`**（交付说明按 basis 分组呈现）。

### 5. 机械件同步

- 版本 v2.15.12 → **v2.15.13**（98+1 文件，route_tier.md 新入版本矩阵：check-version.sh / sync-version.sh / .pkg-manifest.txt 三清单同步）；`counts.yaml` version_files 98→99。
- 门 Y 上限重定：M-Gate-核心 77527→78090、phase-order.yaml 69294→70860；棘轮台账登记 1 条新 debt（M-Gate basis 字段）+ phase-order 累加原 open 行；未结债务 3→4 条。
- phase-order.yaml 重装配（blocks 字段入装配视图）；README 版本散文刷新。

### 6. 验证

- `sync-version.sh`：门 AB/AC/AA 全过（v2.15.13）。
- 其余构建门（self-audit / contract / count-drift / flow-check）见提交前 `make all`。
