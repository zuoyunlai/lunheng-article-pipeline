# Changelog

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

## [v2.15.12] — 2026-10-06 · 全量审计报告核实修订（14/16 项落地 + 棘轮台账方案 A 定案）

> 背景：`reports/2026-10-06-全量审计报告-v2.15.11.md`（§一–§八 缺陷清单 + §九 修订后复审）提出 16 项真问题 + 7 项延伸观察；本版逐项**实测核实**后落地 14 项，另 2 项经实测推翻 / 回退（见 §5）。
> 性质：**计数真源扩展 + 机械门补齐 + 棘轮台账治理定案 + 文档口径收口**；不改流程节点、不改门判据。

### 1. 计数真源扩展（P-3 / P-4）

- `counts.yaml` 新增 `t8_formal_compliance: 17`（组 A-E）/ `t8_publishability: 31`（组 F 6 维度拆分）—— 48 项「17+31」分层首次进机械真源；`t8_items == 17 + 31` 由 `test_counts_internal_consistency` 硬校验。
- `counts.yaml` 新增 `t9_methodology_dimensions: 4` + `t9_consumes_g18: true` —— 显式声明 T9 D2 方法论评分是 G18 12 项清单的**聚合（消费关系）**，而非第 7 个独立维度。

### 2. 机械门补齐（P-2 / P-7 / L-2）

`tests/test_count_drift.py` 新增 5 类门 + 4 组反向注入：

- **P-2** `t9_default` 反向注入：`test_t9_default_matches_phase_order`（与 `t9_review.yaml` 对账）+ `test_no_t9_default_prose_drift_in_repo`（扫「按模式开关 / 公众号默认关 / T9 默认关」矛盾型散句）。**首跑命中 2 处同义表述后收窄规则**（「默认开启（可 opt-out）」与真源同义，不算漂移）。
- **P-7** `phase-order/` **目录实物数**核对（27 yaml − index = 26）—— 「加了 yaml 却没登记 index.yaml」这类静默漂移从此硬失败。
- **L-2** `test_phase_order_index_seq_is_contiguous`：`index.yaml` seq 条数 == `pipeline_nodes` 且必须连续 0..N-1。

### 3. 文档口径收口（P-5 / P-6 / L-3 / L-4 / L-5 / R-3）

- **P-5**：`字数判定表.md` §二 表后新增「生效条件（与 §七 对齐）」—— P1/P0 两档的「触发修订」**仅在有外部硬要求时成立**，与 §七「无外部要求不触发」互为条件分支。
- **P-6**：`SKILL.md:112` 角色速查补 **T0 主控**（原先 T0 从角色生态图里缺失）。
- **L-3**：`08-终检-final-inspector.md` 新增「M 门不重复项清单」—— 讲清「M 门 13 项」vs「T8 兜底 11 项」**不矛盾、不是漏检**（M-Integrity-1/2 锁定在 T2.5/T7.5 不回退）。
- **L-4**：README 能力边界段「按 runtime 探针实测泄漏面全量补声明」→「按 **2026-09-20** runtime 探针**一次性实测** … **快照、非持续监控**」。
- **L-5**：SKILL.md frontmatter description「标准架构 = 多 Agent 九角色」→「九角色流水线（角色卡 11 张，含 T0 主控 + T9b 压力测试；T9b 默认不跑）」。
- **R-3**：README Phase 0「4 选 1」明细改指针（唯一真源 = `关键协议.md`）。

### 4. 棘轮台账方案 A 定案（P-1 / L-1 / R-1，同源三面）

`ratchet-ledger.md` §二 原先自承「『只允许发生一次』与『每版必发号』直接冲突，待台主人裁决」的设计债，本版按**主人裁决方案 A** 收口：

- `version_stamp_lengthening`（发版机械 +1 B/文件）**按发版频率豁免**：不计入 §四-3 三次上调铁律、不计入 §一 `settle_to` 比对、不写 debt 行。
- `M-Gate-核心.md` 原第 4 条债务为**纯版本戳 +1 B、零内容变更**（`settle_to` 物理上永不可达），**移出** §一 债务、记为 §二 豁免实例 → **未结债务 4 → 3 条**。
- **未采用报告建议的「4 条减为 1 条」**：另 3 条 `reason` 混有真实内容增长（v2.15.7 新增节点 / 契约真源化 / T9b 极性改写），一并销账会掩盖真实债务。
- 同步：`self-audit-gate.sh` 门 Y 注释改「已定案 / 已移出」（保留历史沿革句）；`可发表性判定表.md`「同步 6 处外部引用」→ **7 处**（补 `counts.yaml`）；`counts.yaml` T8 组名注按真源更正为 A–E 全称（§九 §9.3 三轮脱同步一并清）。

### 5. 经实测推翻 / 回退的 2 项（不进版）

- **R-2（🌐 语言政策块）不成立**：实测全块签名命中 **107 个文件**，由 `scripts/inject-lang-policy.py` **机械注入**、被**构建门 4d + `test_contract_check.py` 强制**。按建议改指针会**直接打破构建门**并让 v2.12.9 修掉的 SkillSpector finding 复发 → **驳回**（报告原估「8 处」已由 §九 自更正为 107）。
- **R-4（硬卡阈值表外移）实测不可行**：移出后 **门 B 立即红**（`角色编号覆盖不全: T2 SKILL=1 …`）—— 该表是 `SKILL.md` 里 T1-T9 编号的主要覆盖源 → **已回退**，表原样保留。

### 6. 验证

- 自审门 `self-audit-gate.sh`：**PASS 42 / FAIL 0**（门 B 角色覆盖 / 门 V `8902 ≤ 10000` 且 frontmatter `1602 ≤ 9000` / 门 Y「台账 3 条未结」/ 门 Z `40 ≤ 40` 全绿）。
- `check-version.sh`：**98/98 文件版本一致**；门 AA 装配视图与 27 真源文件逐字节一致（26 节点切片）。
- 字节账：`2.15.11 → 2.15.12` 同长度 ⇒ 四个必读文件体量**零变化**，门 Y 上限无需重定。

---

## [v2.15.11] — 2026-10-05 · 文档专项审计修订（22 项全修）

> 背景：2026-10-04 文档专项审计（`outputs/2026-10-04-lunheng-doc-audit-report.md`，文档面 7.3/10）提出 7 项 P1 + 9 项 P2 + 6 项 P3 与机械加固建议；本版逐项落地。
> 方法论：每项先**实测核实**再动手（教训 #480「先对齐再归因」，本轮再次奏效——P2-1 的 README 部分与 P3-4 的 gates/14 部分经 grep **证伪**，见 §4 勘误）。
> 性质：**纯文档层修订 + 计数/版本机械件**；不改流程逻辑、不改门判据。

### 1. P1 口径修复（7 项）

- **心跳 opt-in 三处漂移**（真源 = `external-services.md`「默认不写，Phase 0 勾选 Operational Telemetry 才启用」；入口层原先写成无条件副作用，按字面执行会在未勾选时写 `.tmp/`，直接违反 fail-closed 同意门）：`SKILL.md` 写入警告段、`QUICKSTART.md` 副作用清单、`permissions.md` 完整写入清单第 ③ 类，三处同批补 opt-in 限定。
- **触发边界自相矛盾**：`SKILL.md` 触发段「<3000 字短文不适用」与紧邻的「2000-3000 可走轻量档」互斥 —— 改为 **<2000**（对齐 `字数判定表.md` §五）；`pipeline-readme.md` 定位段「任务形态判据 ≥3000 / 3000 字以下不适用」同批 → **≥2000 / 2000 字以下**。
- **G14 权限档归属冲突**：`SKILL.md` frontmatter `audit` 档注释含 G14，与 `permissions.md` 五档表（`allow_review` = T9/G14）及 `dispatch-header.md` 矛盾 —— 注释改为「T6 批判 + T7 审计映射至此，G14 归 review 档」。
- **节点数 25 → 26 全批同步**：v2.15.7 新增 `post_phase1_dispatch_verify` 后，**11 处**副本漏改 —— README / QUICKSTART / 设计文档-架构 / 设计文档-哲学 / pipeline-readme / glossary-full / dispatch-header 指针块（7）+ skill-entry-appendix「25 节点切片」+ pipeline-overview R-21 段「25 个节点切片」+ 模板填写说明「25 节点，seq 0–24」+ checkpoint-card 映射标题；另删 README 演进表内的历史数字「24 节点全表」（避免新扫描面误报）。
- **T9 默认开关三口径并存**：真源 `t9_review.yaml` = `default: triggered`（无条件默认开 + 显式 opt-out），而 SKILL / QUICKSTART TL;DR / 字数判定表 §五 / asset-index / 设计文档-架构 / glossary-core / 09 角色卡 / pipeline-readme 派发索引仍写「按模式：行业分析学术默认开、公众号默认关」或「可选」—— 全部统一为「默认触发；主人显式 opt-out 才关闭；轻量档不因档位静默跳过」。
- **pipeline-readme 外发表缺 2 类**：Phase 0 披露面只列 4 行，缺 **学术元数据（OpenAlex/Crossref，opt-in）** 与 **抓取层（Firecrawl，opt-in）** —— 补齐两行（与真源 3 类 + 轴 A 对齐）。
- **QUICKSTART 技巧 4 残留旧语义**：「主控不再死磕 → 直接走 Acknowledged Limitations」隐含自动降级，与同文件后文及真源「暂停等主人裁决」冲突 —— 改为「暂停呈主人裁决（出口真源 = `phase-order.yaml` `rounds_exhausted_outlet`）」。

### 2. P2 修复（9 项）

- **两轴不混用（emoji 混用）**：`QUICKSTART.md` Q2 整段轴颠倒（原文「🟢🟡🔴 是信任级别标识」+ 时效评级写成文字「≤2/2-5/>5 年」）→ 重写为「信任=文字（已发布/主人投喂/二手转引）、时效=emoji（🟢 ≤2 年 / 🟡 1-3 年 / 🔴 >3 年）」；`glossary-core.md` 数据信任段原表列的是**来源类型**（一手/二手转引/单边）却挂「数据信任 3 档」标题，且聚合铁律借 🟡 表信任 → 改双轴分列（信任级别 / 来源类型），铁律改「一律按二手来源起步」；`案例卡-template-lite.md` 信任级别字段去 emoji。
- **quickref G14 名实不符**：自称「9 类检测维度」却只列 A-H 共 **8 类**（漏 G14-I 防御性写作），且自称「不重列」却带全部阈值 —— 改为九类名称内联（含 G14-I）+ 阈值/判定档/热力图一律指真源（同时收敛了 8 行阈值的漂移面）。
- **角色计数四套口径**：counts.yaml 已有权威定义（概念 11 / 物理 12），但 `asset-index.md` 同文件先「10 张」后「11 张」、`pipeline-readme.md`「10 张卡」、`设计文档.md`「10 角色卡 + 6 阶段」、`SKILL.md`「10 角色卡 + G14」 —— 统一为「11 概念角色 / 12 物理卡文件（计数真源 = counts.yaml）」或直接去数字化（SKILL 角色速查行改为「T1-T9 + G14」）；`QUICKSTART.md` 角色表补 **T9b 行**（与表题「11 张角色卡」一致，并标注默认不跑）；`设计文档-架构.md` 表补 T9b 口径。
- **性能基准「1 例 vs 2 例」自相矛盾**：§二 实测表有 2 行重量档（09-22 / 09-25），§三/§五 与 README/QUICKSTART 却称「1 例」—— 四处统一为 2 例，并补 09-25 主控侧实测（66k in / 11k out / $0.03）作为预算模型校准依据。
- **幽灵节点 Phase 5.5**：`可发表性判定表.md` 3.4 与 `任务简报-template.md` 要求交付物含「Phase 0/2.5/3.5/5/**5.5** 主人拍板记录」，而全流程人环节点只有 4 个（phase-order 无 5.5 节点；T8.5 是外发许可标记、非 owner checkpoint）—— 两处删「5.5」。
- **D2 映射双计**：`方法论-审计清单.md` 附录 B 中 G18 项 11 同时映射「数据质量」与「可复现性」（一分两算），项 12（理论框架对照）被塞进「可复现性」（语义错位）—— 重排为 研究设计 1+2+3 / 数据质量 3+4 / 分析严密性 5+6+7 / 可复现性 11，项 12 归 D1，并补「参照底本非逐项计分公式 + 项 3 双侧参照 / 8-9-10 门槛项」的防双计口径注。
- **glossary 章节乱序**：§十二「核心原则」（最重要的一节）被追加式编辑挤到「词汇表结束」标记**之后**，§十三 插在 §九/§十 之间 —— 重排为 §一…§十三 顺序，核心原则回到结束标记之前，T9b 段（补 v2.15.10 opt-in 口径）归位为 §十三。
- **字节账不平**：`主动介入机制.md` 外移说明写 69488 B、`CHANGELOG.md` v2.15.9 写 70189 B、棘轮台账 settled 行写 70039 B —— 以 `git show v2.15.9` 实测 **70189 B** 为准统一两处（台账 reason 注明原记系笔误）。
- **B 类扩写通道未入真源**：T9「扩写/改写清单」B 类修订（不占 2 轮预算）只在 09 角色卡定义，而自称轮次真源的 `pipeline-overview.md` 仲裁表没有该通道 —— 补「B 类扩写」独立行并指向决策协议真源。

### 3. P3 + 机械加固

- `关键协议.md` 硬卡段删「原列：T1-T3 10 / …」数字残留（与同段「不在此重列数字」自相矛盾），§二十二 指针改指 `主动介入机制.md`（v2.15.9 外移后未更新）。
- README：删无出处、无更新机制的 Code Quality 87/100 徽章；首屏「5000+ 字强推」改为「≥3000 推荐全量（≥5000 强推）；2000-3000 轻量档」；`asset-index.md` 关键参考去掉已收敛为纯索引页的 `设计文档.md`。
- **版本矩阵盲区补入（教训 #118.1 同型）**：`方法论-审计清单.md`（G18 真源，带内部版本标记却不在两矩阵，下次 bump 将永停旧版）补版本头 + `check-version.sh` CHECKS + `sync-version.sh` SYNCS，`counts.yaml` `version_files` 97→98（`contract-check` 计数对齐）。
- **根因修复：节点数接入计数真源**：`counts.yaml` 新增 `pipeline_nodes: 26`，`test_count_drift.py` 接入三模式扫描（`N 节点全表` / `N 个节点切片` / `N 节点，seq`）+ 反向注入测试 —— 本轮 25→26 漂移的根因就是「节点数不在任何计数真源里，机械门扫不到」，现已闭环。另以注释键登记 `t9_default` / `heartbeat_telemetry` 两个布尔口径（不接数值扫描：布尔句式无稳定数字模式）。
- **CHANGELOG 轮转**：v2.15.6 迁入归档（主文件保持 4 期，待本节落账后为 5 期），`CHANGELOG_ARCHIVE_CEIL` 按实测 245143 → 249426 同步重定（随轮转同步，非内容扩容）。

### 4. 审计报告勘误（两处经 grep 证伪）

- **P2-1 的 README 部分不成立**：审计报告称 README 信任级别表带 🟢🟡🔴 —— 实测 README 现行版本早已是「文字取值 + 两轴不混用」注记，本次无需修订；真实缺陷面为 QUICKSTART Q2 / glossary-core / 案例卡-lite（已修）。
- **P3-4 的 gates/14 部分不成立**：`gates/14-中文AI痕迹-gate.md` 早在 v2.4.0 即在 `check-version.sh` + `sync-version.sh` 两矩阵内；真实盲区仅 `方法论-审计清单.md`（已补入）。

### 验收

- `check-version.sh` **98/98 ✅**（v2.15.11）· `contract-check` PASS · `changelog-check --check` PASS · `flow-check` exit 0 · `markdown-structure-lint` PASS · `dispatch-contract --check` PASS（3 派发块 + 1 轮次块 + 2 owner 载体）
- **全量 pytest 707 passed / 2 skipped（486.84s）**
- 快速回路 `pytest -m "not slow"` **605 passed / 1 skipped**（113.36s；含新增节点数漂移反向注入 1 项）
- 自审门 **42 PASS / 0 FAIL**（门 Z = 40 未越限）；门 Y 四个棘轮文件本轮未改动，无新增债务
- `sync-version.sh` 归一化复核：9/9 通过，无残留 `.bak`
- 门 AA：升版后按生成器重装配，26 节点切片逐字节一致（装配视图为生成物，bump 时只随真源重生成；棘轮字节维持 69294 B）

---

---
