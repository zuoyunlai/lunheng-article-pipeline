# Changelog

---

## [v2.15.10] — 2026-10-05 · 架构评审收口：契约真源化 + T9b 降级 opt-in

> 背景：2026-10-04 架构与扩展性评审。原评审报告的 P0 结论（`ci-test.yml` 不存在、CI 漏跑全量测试）经复核**证伪**——该文件自 v2.5.6 起一直在仓，且被评审时点双 workflow 各跑一遍全量；原报告的 9 项「字节数」实为字符数（系统性计量口径错误）。真正成立且值得修的是派发合同机制三缺口（R2），本版逐项落地，并按主理人指令把 T9b 降级为 opt-in。

### 1. 派发/轮次契约真源化（P1）—— 删除代码侧无源常量

- **问题**：`dispatch-contract.py` 的 `NODE_CONSTANTS` 把 `recheck_max_rounds` 硬编码在代码侧——其中 `t9_review: 0` 在切片中**任何层级都不存在**（纯代码侧发明）；且 `--check` 比较的是「生成结果 vs 生成结果」，常量漂移对门不可见。覆盖集 `NODE_TO_DISPATCH` 靠手工登记，新增派发节点零成本漏登。
- **修复**：
  - 切片真源化：`g14`/`t9` 补 `recheck_max_rounds`；`g14`/`t9`/`t1b` 补 `dispatch:` 载体登记；`t9b`/`methodology_snapshot` 补 `contract_key_carriers:`；`audit_revision`/`t5_style_revision` 补 `rounds_carrier:`。
  - 生成器重写：覆盖集由切片 `dispatch:` 字段**现算**（新增派发节点零手工登记）；轮次合同块入 `pipeline-overview.md` 仲裁段，成为全仓 5 项轮限的唯一机械登记处；owner 节点契约键逐文件验「键在载体」（极性中立：condition / opt_out / opt_in 任一声明键均覆盖）。
  - 测试重写 7 → 15 项，含「切片改值 ⇒ 块跟着变」传播测试与「常量不得还魂」棘轮。
- **纪律**：T5 派发文件明文「本文件不复述轮次数字」⇒ 轮次契约**不写入 T5 dispatch**，另择仲裁段为唯一载体（避免当场违反既有纪律）。
- **验收**：`dispatch-contract --check` 绿（3 派发块 + 1 轮次块 + 2 项 owner 载体检查）。

### 2. T9b 压力测试轮降级为 opt-in（默认不跑）

- **问题**（三条实测证据）：
  ① 扫描 `run/` 下 40+ 项目目录**零产出**（管线明显越过该位置而报告不存在；同类型的 `methodology_snapshot` 却多次实跑产出，差别在产出是否交付必需）；
  ② 产出**无下游消费方**（T8/交付说明/status 皆不读，协议自承不改 T9 评分、不代替 T7、不自行触发修订、默认不入交付说明）；
  ③ 主控亲为 = 重读定稿全文 ≈20k tokens 压在管线最稀缺的 agent 上，方向与「落盘减负」纪律相反。
- **修复**：`default: triggered → opt_in`；`opt_out/on_opt_out` → `condition: owner_stress_test_opt_in` + `on_not_triggered`（未开启 ≠ 漏跑，留痕口径与 opt-out 分离）+ `condition_undecidable`；条件键在 `condition_definitions` 登记 producer + marker（规则 25 同族治理）；同步任务简报 full/lite、09b 角色卡、00-主控-扩展职责、压力测试协议、全景行 22。
- **保留理由**：三类剧本（方法论审查者 / 立场与范围 / 跨语境）有真实学术价值（对应投稿前的 referee method review）⇒ **保留节点**，改为**冲刺投稿时**由主人在 Phase 0 勾选 `owner_stress_test_opt_in: yes` 开启。
- **守卫**：新增 `tests/test_t9b_optin_downgrade.py`（6 项，含 2 项反向注入：改回 `default: triggered` 必红、生产方载体丢键必红），防静默回潮。
- **顺带修正**：任务简报「2 个默认启用项」计数漂移（实为 3 项，T9b 移出可选项组后归真）。

### 3. 散文 seq 漂移修正

- `dispatch/T1b-定向回查.md:16-17` 两处 `seq 3` / `seq 14` → **4 / 15**（与 `phase_seq` 真源对账；v2.15.7 插入 `post_phase1_dispatch_verify` 后整体位移，此处未同步）。
- `agents/08-终检-final-inspector.md:180` `seq 17→18` → **19→20**（同一批次位移）。

### 4. CI 口径注释 + Python 支持面声明

- `quality.yml:53,60` 注释「4 路分片」→ **slow/fast 双 job**（对齐 `8ca7973` 方案 A 现状），并新增 `test_ci_config::test_j` 注释锚点防复发（原 `test_d` 只断言结构、不断言注释 ⇒ 漂移无门拦截）。
- README 开发环境段补 **Python 3.12** 支持面声明（CI 钉 3.12；`target-version = py312`；3.11/3.13 不在支持面）。

### 5. 门 Y 体量棘轮重定 + 台账补登

- 三个必读文件按协议契约字段重定基线：`00-主控-扩展职责.md` 70189→70277、`phase-order.yaml` 68238→69293、`phase-order/index.yaml` 25084→25358，同批写入棘轮台账。
- **补登**：本日第 1 项那轮把 `phase-order.yaml` 66574→68238 时**漏记账**（违反台账 §四-1「上涨 = 记账」——重定不得退化为注释豁免），本版一并补登，并在门内注释写明是哪一轮、为何漏。
- 未结债务 3 条（回落目标与截止版本见 `references/_shared/治理/ratchet-ledger.md`，截止 2.18.0）。

### 6. 冷归档扫描豁免补登（v2.15.9 同族遗漏）

- `tests/test_scan_stale_language.py` 的 `EXCLUDE_NAMES` 补 `CHANGELOG-archive.md` / `changelog-cold-v2.0-v2.12.md`（历史沿革文件的旧口径是史实，不得被漂移扫描要求改写；与 `test_count_drift.py` 的白名单对齐）。

### 验收

- 自审门 **PASS 42 / FAIL 0**（0 SKIP）
- 全量 pytest **707 passed / 1 skipped**（515.21s）
- CI 4/4 success：论衡算法测试 CI（含 slow/fast 全量 + 自审门 + 官方校验）10m27s、Code Quality 11m8s、版本号一致性、changelog 完整性
- `contract-check` / `markdown-structure-lint` / `dispatch-contract --check` / `flow-check` 全绿
- 门 AA：装配视图与 26 节点切片逐字节一致

## [v2.15.9] — 2026-10-03 · 全量审计七项修订

> 背景：2026-10-03 全量审计（评分 8.6/10）提出 7 项问题与优化空间，本版逐项落地。
> 方法论：每项先**实测核实**再动手（教训 #480「先对齐再归因」）——其中 3 项审计预设被实测推翻。

### 1. 门 H 闭合（P1）—— 消除 29 门中唯一常态化 SKIP

- **问题**：门 H 正向差集长期 SKIP（判据依赖仓库外 memory/lessons.md，该真源 2026-09-26 / 09-28 两次被整文件覆写，原文丢失不可恢复）。
- **修复**：新建 references/_shared/治理/lessons-registry.md 承载「论衡侧合法引用编号全集」，**三态区间**（可引用 / 永久空档 / 从未登记）；门 H 由「外查真源」改为「内查登记表」，**SKIP 路径移除**；CI / 本地同口径、无外发依赖。
- **快照**：492 → 495（#493 CLI 挂死看 CPU=0 + #494 pkill -f 自噬 + #495 sandbox read 截断）。
- **验收**：自审门 42 PASS / 0 FAIL / **0 SKIP**。

### 2. 棘轮重定台账（P1）—— 把「合法上涨通道」变成有账债务

- **问题**：门 Y「只许降」存在合法上涨通道 —— v2.15.8 以「按实测重定」把扩展职责卡 69808→74923 B，规则文本说「后续只许降」，但重定动作本身无机制约束。
- **修复**：新建 references/_shared/治理/ratchet-ledger.md（回落目标 + 截止版本 + 状态）；门 Y 增补「债务不得过期」判据，结论并入既有行（守门 Z 项数上限）；三次上调须改走分层。
- **验收**：棘轮测试 6/6。

### 3. 仓库瘦身（P2）—— 实测修正审计预设

- **实测**：memory/ 12K + reports/ 356K **已被 .gitignore 排除**（不进 git、不进净化包）⇒ 审计原文「混入技能仓库」**不成立**；已备份至 workspace 并移出仓库根。
- **真缺口**：CHANGELOG-archive.md 502KB / 382 章为全仓最大被跟踪文件，且主文件有 5 期门而**归档无上限**。
- **修复**：changelog-check.py 新增 CHANGELOG_ARCHIVE_CEIL 体量棘轮（实测水位，只许降），超限告警引导冷归档外移。

### 4. 主控文档拆分（P2）—— 外移 §二十二 主动介入机制

- **实测**：主控文档 74923 B 中**零重复长段落**、22 处真源指针 ⇒ 无冗余可压；最大两章（§十二 失败处置状态机 9424B / §十五点五 能力断言 8104B）**属安全红线**，按文档自订纪律不得外移。
- **修复**（主人定案方案 A）：外移 §二十二 主动介入机制（含 F4 轮次约束，非红线）至 references/_shared/真源/主动介入机制.md，原位留索引指针；主控文档 **74923 → 70189 B（−4734 B）**。
- **台账销账**：主控卡债务 open → settled，未结 3 → 2 条 —— **台账机制的首个真实销账**。
- 连带面（教训 #491 四张清单）：SHARED_ADMITTED（LC_ALL=C 重排 69 项）/ .pkg-manifest.txt / 净化包重建 / 4 处外部引用改指。

### 5. 测试提速（P3）—— 520s → 98s

- **实测**：全量 690 项约 520s，其中约 470s = 12 个测试文件对 self-audit-gate.sh 的 49 次 subprocess 调用。
- **修复**：pyproject.toml 注册 slow 标记；12 个跑门脚本的测试文件加模块级 pytestmark；Makefile 新增 test-fast 目标。
- **验收**：快速回路 586 passed / 103 deselected，**98.35s（提速 5.3×）**；CI 仍跑全量。

### 6. 门家族合并（P2）—— 实测无需动作

- **实测**：门 Z 按**父门归并**计数（门 X.4 → 归入 X），X.1-X.4 / M 家族各只算 1 项。
- **结论**：合并子门**不降低门 Z 项数**，仅形式变化 + 增加改动风险；现状 40 ≤ 40 未越限 ⇒ 记录判定依据，不做动作。

### 7. frontmatter 预算事前拦截（P3）—— 补门 V 缺口

- **问题**：门 V 锁 SKILL.md **全文**（10000），而 v2.15.7 踩的坑是 **frontmatter 单独**撑到 9487（R-22 常驻预算 <9000）—— 全文门当时未报警，事后 CI 才红。
- **修复**：门 V 增补 frontmatter 单独预算判据（9000 字符），结论并入既有体量棘轮行。

### 验收

- 自审门 **42 PASS / 0 FAIL / 0 SKIP**（门 Z = 40）
- 全量 pytest **692 passed / 1 skipped**（487s，完整跑完）
- 快速回路 **586 passed**（98s）
- 构建门 **36/36**；棘轮测试 **6/6**；frontmatter 测试 **3/3**；归档棘轮 **3/3**

---

## [v2.15.8] — 2026-10-02 · 发版债务清零（v2.15.7 遗留 15 项 CI 失败全修）

> 背景：v2.15.7 两笔提交（`3138ff2` / `4acd8f9`）遗留 **15 项 pytest 失败**（v2.15.6 基线 27/27 全绿），推送后 CI 必红。
> 归属判定：`/tmp` 建 v2.15.6 与 HEAD 双基线 worktree 复跑同一批测试，区分「既有失败」与「新增失败」——本轮修复**零新增**（双基线 11F 完全一致）。

### P0 净化包构建门 6F（根因：v2.15.7 两个新文件未登记入包）

- `scripts/build-clawhub-release.sh` `SHARED_ADMITTED` 补 `真源/model_fallback_takeover_protocol.md` + `真源/phase-order/post_phase1_dispatch_verify.yaml`（按 LC_ALL=C 排序位插入）。
- `scripts/.pkg-manifest.txt` 全包白名单同批补两条。**两处漏任一 ⇒ 构建失败**（该门设计意图：新文件默认入包 = 泄漏风险）。
- 连带清理：`references/` 树下 **55 个** `.bak.20261002-122541`（外部审计者遗留；`.gitignore` 挡得住 git、挡不住构建门源树扫描）移出仓库。

### P1 门 H / 门 Y 棘轮 4F（根因：#490 引用未同步快照 + 上限表未随扩容重定）

- `references/_shared/治理/lessons-max.snapshot` **437 → 490**：#438–#489 为宿主/工作区类（不推高本值），#490（skill 行为判据不得写入宿主配置）属论衡类，随 `4acd8f9` 引用入库；同批补 `tests/fixtures/lessons-gate.md` 的 #490 定义（hermetic fixture 缺项 ⇒ 门 H 硬红）。
- `BULK_RATCHET_CEIL_DEFAULT` 基线重定（v2.15 B1-B7 先例，以实测为准、后续**只许降**）：扩展职责卡 69808→74923、phase-order.yaml 63928→66574、index.yaml 24767→25084；装配视图重生成后再校准一次（+162 B）。

### P1 SKILL.md 预算回涨 1F（根因：v2.15.7 把模型清单内联进 frontmatter）

- 违反 R-22「frontmatter 常驻预算 <9000 字符」：实测 **9487**（内联 7 项已实测模型 + 4 项候选模型清单）。
- 修复：清单整体收回其**既有唯一真源** `references/_shared/真源/模型候选池.md` §二·三（新增「compatible_models 实测清单与候选池」两表），frontmatter 只留指针注释 + `delivery` / `coordinator_spawn_hard_gate` / `coordinator_fallback_protocol_ref`。**9487 → 8641 字符**。
- 附带修正架构一致性：候选池.md §五 章程本就写明「SKILL.md 引用本文件，不重复定义」，v2.15.7 内联写法同时违反该章程与预算门。

### P1 新节点连带面 4F（根因：`post_phase1_dispatch_verify` 插入 seq 3 后位移未同步）

- 该 `mechanical_checkpoint` 补 `rerun_after_report: true`（v2.12.40「报告后激活」纪律，参照 `t7_5_integrity` 先例）⇒ 重生成装配视图。
- canary 校准（`tests/test_v2130_p0_fixes.py`）：t1b `phase_seq` 断言 14→**15**、全景节点计数 25→**26**（与 pipeline-overview.md 头部 v2.15.7 更新记录一致）。

### 验收

- **pytest 681 项 / 57 文件全绿**（分块：块1 159✓+1s · 块2 254✓ · 块3 286✓+1s；零失败）。
- `check-version.sh` 96/96 · `contract-check` PASS · `changelog-check` PASS · 门 AA 逐字节一致 · 自审门 37 PASS / 0 FAIL。

### 同族教训

- **#491**：v2.15.7 两笔提交各留 15 项 CI 失败却已发版/tag —— 「提交后不跑全量回归」与「升版只改 SKILL.md 不跑三层联动」同源于**流程断裂**。新增受管/随包文件时，登记清单不止版本矩阵（check/sync + counts），还包括**净化包双白名单**（SHARED_ADMITTED + `.pkg-manifest`）与**教训快照/fixture**。
- **#492**：外部工具留下的 `.bak` 备份能同时躲过 `git status`（`.gitignore` 命中）与人工抽查（文件名不显眼），却在**构建门源树扫描**整片爆红 —— 清理纪律须覆盖「被 `.gitignore` 掩盖的中间产物」，不能只看 git 视角。

---

## [v2.15.7] — 2026-10-02 · 派发硬验证 + fallback 接管协议 + 零宿主要求

### 新能力（`3138ff2`）

- **派发硬验证闸门**：新增 Phase 1 后置节点 `post_phase1_dispatch_verify`（切片 + 装配视图 + 门 AA 接线），spawn 返回值 `runId` / `childSessionKey` / `resolvedModel` 三字段硬校验，防「主控口头已派发、实际静默失败」；新增 `scripts/rebuild.sh` 一键重建装配视图（scripts 索引 34→35）。
- **模型 fallback 接管协议真源**：新增 `references/_shared/真源/model_fallback_takeover_protocol.md`（触发三条件 / 接管五步 / status §八声明段）；`SKILL.md` frontmatter 新增 `coordinator_fallback_protocol_ref` 指向。
- **frontmatter 声明面扩展**：`delivery`（channel_relay 默认 + session_local 兑底，纯声明性建议）；`compatible_models`（7 个已实测模型）+ `compatible_models_candidates`（4 个未实测候选，晋升须一次实跑验证）；`coordinator_spawn_hard_gate: true`。
- **weight 阈值自包含（`4acd8f9`）**：撤回宿主配置耦合——`recommended_session_for_weight` 自造键从 openclaw.json 移除，阈值表改 skill 自包含，「零宿主配置」是架构红线（教训 #490；同族 #484）。

### 审计收尾（外部全量审计报告 2026-10-02）

- **95 个受管文件版本戳同步** v2.15.6→v2.15.7（外部审计复刻 `normalize-version-header.py` 幂等语义写入，diff 仅版本戳行）；README 正文「当前版本」块与安装 pin 同步。
- **版本矩阵盲区修复（审计 D3，教训 #118.1 第三次表现）**：`model_fallback_takeover_protocol.md` 此前是全仓唯一带版本戳但不在两矩阵的受管文件，下次 bump 版本戳将永停 v2.15.7 → 补入 `check-version.sh` CHECKS 与 `sync-version.sh` SYNCS，`counts.yaml` `version_files` 95→96。
- **CHANGELOG 补节 + 轮转（审计 D4）**：补本节；v2.15.2 轮转入归档（保主文件 5 期上限）。
- **审计核实项**：phase-order 装配视图与真源一致（45251 字符，生成器零 diff）；报告所称 16 个 scripts 仅 mode 变化已消失；README/SKILL 版本真源两门人工核验通过。

### 验收

- `check-version.sh` 96/96 ✅ · `contract-check` PASS · `changelog-check` PASS · `phase-order-slice.py --check` 零 diff · pytest 版本真源两门通过。

---

## [v2.15.6] — 2026-10-01 · 真源/模板/运行手册重构（第三、四、五批）

### 变更（第三批：棘轮锁定文件 + README）

| 文件 | 字节 | 教训#N |
|---|---|---|
| `references/_shared/真源/M-Gate-核心.md` | 78423→77526 | 19→0 |
| `README.md` | 18228→18014 | 9→0 |

外移内容：`v2.12.40 新增` / `v2.12.41 实测补强` / `v2.12.56 修正` / `v2.12.49` 等版本考古与
`教训 #N` 括注统一入本段；正文只留现行规则 + 真源指针。

**体量棘轮同步**：M-Gate-核心.md 是门 Y 棘轮锁定文件（`test_bulk_ratchet` 要求实测字节 == 上限，
精确相等）→ `BULK_RATCHET_CEIL_DEFAULT` 由 78423 下调至 77526（「只许降」惯例）。

**连带面（清叙事触发）**：门 K 报 5 处 dispatch 孤儿教训引用（角色卡/真源侧清零后失去溯源载体）——
`T1-文献检索.md`(#107)、`T2-数据检索.md`(#106)、`T6-批判.md`(#184)、`T7-审计.md`(#184)、
`T8-终检.md`(#251) → 同样外移（规则保留、叙事移除）。

### 变更（第四、五批）

### 变更（第五批：模板与协议）

| 文件 | 字节 | 教训#N |
|---|---|---|
| `references/_shared/真源/关键协议.md` | 35695→35242 | 5→0 |
| `references/templates/任务简报-template.md` | 34953→33745 | 20→0 |
| `references/templates/status-template.md` | 33519→33136 | 7→0 |
| `references/deliverables.md` | 27783→26535 | 15→0 |

合计 **-6292 B**。外移内容：`教训 #N` 括注、`vN.N.N 新增/实测/修正` 版本考古、实战事故叙述（三版字数超限 / 口腔 AI archive 冗余 / ai-race-to-bottom 两次 P1 / ClawHub 遥测扫描 / ai-pilled 边界混淆等）统一入本段；正文只留现行规则 + 真源指针。

### 变更（第四批）

按同一标准重构第一档 4 个高频文档，合计 **-6371 B**：

| 文件 | 字节 | 教训#N |
|---|---|---|
| `references/pipeline-readme.md` | 25088→22400 | 22→0 |
| `references/_shared/真源/可发表性判定表.md` | 28056→26147 | 18→0 |
| `references/_shared/真源/audit-checklist-quickref.md` | 18006→17783 | 9→0 |
| `references/_shared/真源/执行韧化协议-design.md` | 23131→21580 | 11→0 |

外移内容：「教训 #N 由来/成因」标注、`vN.N.N 新增/实测/修订` 版本考古、实战事故叙述（T3 三连超时 / 口腔 AI 评分未呈现 / SVG 嵌入孤儿 / 图表截断降级等）统一入本段；正文只留现行规则 + 真源指针。

### 修正的缺陷

1. **执行韧化协议-design 顶部重复 H1**：连续两个一级标题，后者还带 `文档**` 笔误 → 合并为单一 H1。
2. **§4.5 逻辑倒序**：章节实际顺序为 4.1→4.4→**4.6→4.7→4.5** → 调整至正确位置（不改编号，§4.7 的活指针仅存在于 CHANGELOG 归档，§4.5 无外部引用）。
3. **可发表性判定表「修订追溯」整节**：v2.11.0/v2.11.1/v2.12.0 三条版本沿革 → 外移至本段。
4. **失效计数**：`教训沉淀体系（#1-#144）` 已与实际（#400+）脱节 → 改指教训索引真源。
5. **陈旧模型名硬编码**：能力分层表内的 `deepseek-v4-pro` / `flash` / `gemma4:31b` / `qwen3-coder:30b` → 改为能力档表述（本表本就是讲「不硬编码」的，写死模型名自相矛盾）。

### 连带面（清叙事触发，一并修复）

- **门 K 孤儿教训编号**：`dispatch/T5-写手.md`（#163/#259）、`T6-批判.md`（#281）在角色卡清零后失去溯源载体 → 一并外移。
- **发布链「剥离规则自检」**：判据短语「没有自动沉淀到写手禁做清单」的真源唯一载体是 T7 卡的叙事段 → 迁至其真源 `_shared/治理/反哺报告处理.md`，而非塞回角色卡。

### 锁定面（改动全程未破）

`可发表性判定表` 严重度列 P1+P2+advisory = 17（门 19 M-9 门槛 17，**零余量**）；`audit-checklist-quickref` 的 G15/G16/G17、`复检 ≤2 轮`、6 个 `*_reconciliation` token 与 3 个对账纪律串；`pipeline-readme` 的门 B 角色号 T1–T9、门 Z 的 4 个 `##` 标题与**围栏配平**（教训 #427 曾因未闭合围栏吞掉尾部 57 行）；三个文件的第 1 行版本戳（`sync-version` header 载体）。

