# Changelog

---

## [v2.12.58] — 2026-09-19

- **M 门算法文档围栏错位修复（教训 #426 沉淀）**：`references/_shared/M-Gate-Algorithm.md` 此前有 2 个多余围栏（L1048、L1181）把 `M-Exist-3: 数据信任级别一致性 diff` 与 `M-Integrity-1: T2.5 完整性门` 两个标题裹进代码块，并使 7 行伪代码注释（L1081/1085/1090/1102 + L1148/1160/1170 + L1203 后的）落到块外被渲染为文档 H1。实测：原围栏总数 46（偶）但相位错位 ⇒ 13 个 M 门标题中只有 4 个在块外、9 个被吞；删两个多余围栏后围栏总数 44（偶）且全部 M 门标题归位、伪 H1 消失。可复用结论：**围栏总数偶数只是必要不充分条件**（错位的围栏可以两两配对但配错了位置），要真校验相位必须叠加「M 门标题必须在块外 + 围栏外无紧跟围栏的 # 伪 H1」。
- **同类缺陷扩围抓到第二例（教训 #427）**：把 X.1 的判据从「M-Gate 单文件」扩到「全仓 `.md`」后**立即红** —— `references/pipeline-readme.md` 围栏 **7 个（奇）= 未闭合**，按渲染配对规则其尾部 **57 行**（含 `## status.md 状态机` / `## 模板加载策略` / `## 设计文档加载策略` 等章节）整块被吞进代码块；对比 v2.12.53 该文件为 8 个围栏（偶）⇒ 缺陷由 **v2.12.54 全景收敛的删除残留**引入（删开围栏、留闭围栏），**存活 4 个版本 / 跨 5 次发版**未被任何门拦下（门 X.1 的扫描面当时写死为单文件）。修复：删孤儿闭围栏（7 → 6 个围栏，尾部 57 行归位）。可复用结论：**判据的扫描面 = 该缺陷「类」的宿主集，不是「上次出事的那一个文件」**；修完个案先问「同类问题在别处是否可能」，并把范围先开大跑一遍（红 = 又抓到同类；全绿 = 拿到「该类当前为零」的基线）。
- **README 正文版本 + 排版残留修正（教训 #428）**：主人问「readme 是否需要修正」→ 先跑全量 pytest 取证，发现仓库**实际是红的**：`tests/test_audit_residuals.py::test_readme_prose_version_matches_frontmatter` 报 `README 正文版本 v2.12.57 ≠ frontmatter 2.12.58`（README 正文「当前版本」段是**手写载体**，不在 `sync-version.sh` / `check-version.sh` 受管网内 ⇒ 自审门 C 与 check-version 全绿；但 pytest 里早就有这条断言）⇒ **「门存在」≠「门跑过」**：上一批升版本戳（89 文件）未跑全量测试，本版内记录的「373 passed」在最终态不成立。已修：README 正文段 v2.12.57 → v2.12.58（同批补本版摘要），并顺手收敛 README **43 行** / `glossary-full.md` **13 行**连续空行块（排版残留，渲染为巨空白；全仓仅此两处 ≥4 行）。：`scripts/self-audit-gate.sh` 末尾新增门 X.1 / X.2 / X.3 三道断言 —— X.1 抓 M-Gate 围栏总数为奇数；X.2 抓 13 个 M 门标题（8 Form + 3 Exist + 2 Integrity）被裹进代码围栏；X.3 抓围栏外「紧跟围栏行且首字符为 #」的伪 H1（围栏错位的真实信号）。CHANGELOG-archive.md 走白名单（历史归档允许多 H1）。
- **配套 6 条单测 `tests/test_gate_x_fence_phase.py`**：① 基线正向验证（X.1-X.4 全 ✓ + 退出码 0）；② X.2 变异（M-Gate 追加被围栏裹的 M-Form-99，须 ✗）；③ X.2 变异（把 `pipeline-readme.md` 的章节锚点裹进围栏，须 ✗ —— 验证锚点表第二项真生效）；④ X.1 变异（删一个裸围栏让总数变奇数，须 ✗）；⑤ X.3 变异（追加「紧跟围栏关闭的 # 伪 H1」，须 ✗）；⑥ X.4 变异（新增一个含未闭合围栏的 `.md`，须 ✗）。**变异必须被门真跑到并 FAIL 才算有效**（避免 #175/#421 同型「门只描述不执行 → 静默空转」）；且**变异一律注入临时整仓副本、真源零写入**（旧写法直接写真源再 finally 还原，中途被 kill 即把变异留在真源里 —— 同族教训 #333）；另配两条护栏单测：真源 sha256 前后一致、锚点表登记文件必须存在且覆盖两份立项文档。
- **changelog 分层轮转（同批收尾）**：主文件加 v2.12.58 章节后有 **6 期**（上限 5）⇒ `python3 scripts/changelog-check.py --check` 红；按既定口径把最旧的 **v2.12.53** 逐字迁入 `CHANGELOG-archive.md`（守恒断言：归档内恰一份、主文件为 0、主文件剩 5 期），归档标题边界更新为「v2.12.53 及更早」并补记 v2.12.52（于 v2.12.57 轮转，上一批漏记）；同时把主文件「范围说明」与 README 里的**字面版本边界**（曾写 v2.12.44 / v2.12.41，逐版漂移）改为不写死边界 + 指向归档轮转记录。
- **验收（实测回填 · 最终态，本批重跑）**：自审门 **PASS 30 / FAIL 0**（门 X.1-X.4 全绿 + 既有 26 门无回退）；`python3 -m pytest tests/ -q` → **377 passed**（门 X 单测改造后共 6 条）；`bash -n scripts/self-audit-gate.sh` 通过；`bash scripts/check-version.sh` 通过（v2.12.58）；`python3 scripts/flow-check.py` RC=0；`python3 scripts/link-check.py` RC=0（494 条相对链接全解析）；`python3 scripts/changelog-check.py --check` RC=0（轮转后恢复）。**⚠️ 修正说明**：本版上一批记录的「PASS 29 / 373 passed」在最终态**不成立** —— 升版本戳（89 文件）后 README 正文版本断言红（见教训 #428），本批已修并重跑；围栏修复后 `references/_shared/M-Gate-Algorithm.md` 行数 1250 → 1248，`references/pipeline-readme.md` 围栏 7 → 6。
- **教训库同批同步（#424-#428 五条入库 + 编号修正）**：主真源续录 **#424**（裸 grep/awk 不认围栏，标题编号从错写的 #423 修正）/ **#425**（trigger 脚本 exec 大 JSON 静默不报）/ **#426**（围栏错位 → 偶数必要不充分 → 门 X 三道）/ **#427**（结构类判据限定单文件 ⇒ 同类缺陷漏检）/ **#428**（门存在 ≠ 门跑过）；`references/_shared/lessons-max.snapshot` 423 → **425** → **428**（载明两段更新记录 + 一段 off-by-one 修正记录）；`references/_shared/教训索引.md` 三处副本同批对齐（§一 / §二 / §三 完整教训库）+ 新增 §三点八 批次 G 分类补记 / §三点九 快照 off-by-one 修正补记 / §三点十 批次 H 分类补记；排除表 `LUNHENG_LESSON_EXCLUDE` **未变** —— 五条均属论衡类（F 审计/分析方法 + 工程实践）。

---

---

## [v2.12.57] — 2026-09-18

- **教训 #421 入库（唯一真源 = 主工作区 `memory/lessons.md`，新编号 #421）**：`scripts/publish-clawhub.sh` 的 `extract_changelog()` 压缩器只认「`> **主题：…**` 主题行 + `### 小节标题`」两种**旧**写法，而 CHANGELOG 写作风格早已迁移为顶层 `- **要点**：详解`（v2.12.54/55/56 三章的 `###` 计数均为 0）⇒ 提取恒空 ⇒ 走 fail-closed 分支 `exit 3`，ClawHub 发布被中止。历史遗留：v2.12.53 仅因该章残留 1 行主题行才「非空」通过 —— 这道门长期近乎空转。可复用结论：**压缩/提取类门必须对真源的实际书写格式有正向样本，否则门会静默空转**（判据是「解析结果」而非「真源内容」，故「解析为空」不能直接推断「真源缺失」）。
  - 报错位置（「CHANGELOG 找不到该版本」）与真实缺陷位置（提取口径认不出格式）**完全不同**：门把「读取侧缺陷」误诊为「写入侧缺陷」。
- **索引与快照同批刷新（三者同批，不提交中间态）**：`references/_shared/教训索引.md` 声明的最大编号 #420 → **#421**（§一 分类行 / §二 定位行 / §三 完整教训库 三处副本同批），`references/_shared/lessons-max.snapshot` **421**（载明 420→421 的更新记录）；排除表 `LUNHENG_LESSON_EXCLUDE` **未变** —— #421 属论衡类，按设计不入排除表（新增宿主/通用类才入表，且不得靠放宽门判据代替）。
- **提取器兜底口径（提交 d51c03c，本版一并记录）**：主口径（主题行 + `###` 小节标题）**保留不变**（旧章行为不变），新增**顶层要点标题**兜底（`- **…**：…` → `- …`）；缩进子项与纯文本条目**不入正文**，平台页面仍是压缩摘要而非全文。e2e 实绩：v2.12.56 提取 6 行 → dry-run `would-publish` → 正式发布已提交。
- **新增正向单测 `tests/test_publish_changelog_extraction.py`（6 条）**：给这道门补「应当放行」的样本（教训 #334 同族）。实现口径 = 从真脚本抽出 `extract_changelog()` **函数真身**执行（不复制一份实现，避免第二真源漂移），在临时 `SKILL_ROOT` 下放构造章节。覆盖 —— ① 新格式章节提取非空且只留顶层要点标题；② 缩进子项 / 纯文本条目不入正文、无残留强调符；③ 旧格式（主题行 + `###`）行为不变；④ 两种写法并存时主口径优先；⑤ 章节确实缺失时仍为空（fail-closed 分支可达、语义未被兜底冲掉）；⑥ **真源防线**：本仓 CHANGELOG 的**当前 SKILL.md 版本**章节必须提取非空（不往仓库根写临时文件，避免弄脏「工作区干净」发版前置闸）。
- **随批并入的其他链已收口内容（如实登记，避免「谁改的」不可考）**：本版提交同时收进本仓三条并行链已收口但未提交的改动 —— ①「P1 软边界收口」内容（`agents/00-主控-扩展职责.md` 的「处置优先级规则（v2.12.57 单一权威口径）」与「两层别混」精确口径、`08-终检-final-inspector.md` 的职责/边界澄清、`任务简报-template.md` 的「换档重派」措辞、`执行韧化协议-design.md` 的适用边界、`errors.md` 零产物处置指针、`_shared/external-services.md` 与 `permissions.md` 的消歧义）；② `设计文档-架构.md` 补 `scripts/README.md` 索引视图指针（索引本体已于 `9f6f095` 提交）；③ 开发者侧探针 `scripts/runtime-capability-probe.py` 入库（纯标准库、不需新增依赖；`scripts/` 不入净化包）。
- **门 Q 与 build 的「可见面」口径对齐（主人 2026-09-19 裁定：`reports/` / `memory/` 属工程过程产物、不进版本库）**：二者已由 `.gitignore` 拦，但 `build-clawhub-release.sh` 只排除 `memory`、门 Q 两者都不排除 ⇒ 前者会把未跟踪报告扫进净化包（触发 #333 跟踪性断言），后者会因报告内的扫描器编号**误红**。本版补齐：build 增 `--exclude 'reports'`（含 `cp -a` 回退路径的清理），门 Q 扫描范围增 `reports/*` / `memory/*` —— 与 build 可见面一致，正是该门注释自己声明的口径。
- **验收（实测回填 · 最终态）**：自审门 **PASS 26 / FAIL 0**（门 C 53 文件版本号 v2.12.57 一致 / 门 H 双向差集：引用 164 个编号全有定义、索引 #421 ≥ 快照 #421 / 门 Q 可见面口径补齐后恢复绿 / 门 V SKILL.md 9827 ≤ 10000 字符）；`python3 -m pytest tests/ -q` → **369 passed**（含本批新增 `tests/test_publish_changelog_extraction.py` 6 条）；`scripts/README.md` 随探针入库重生成（28 条，双向漂移锁转绿）；版本戳同步 **89 文件**；`python3 scripts/changelog-check.py --check` **RC=0**。

> 📌 **发版背景（如实记录）**：本版在**三条并行链同仓改动**的窗口内收口 —— ① 首轮发版前置闸 `EXIT=10`（在飞链 + 工作区 91 条不净），按「两查一停」**停在本地**；② 三条链全部收口（在飞链=0）后，经主人裁定把「P1 软边界收口」等**已收口但未提交**的内容一并收进本版（见上条登记）；③ 未跟踪的 `reports/` / `memory/` 按主人 2026-09-19 裁定走 `.gitignore`（不进版本库），本版仅把 build 与门 Q 的可见面口径对齐。本轮同时把最旧章节 v2.12.52 迁入 `CHANGELOG-archive.md`（主文件保持 5 期）。

---

---

## [v2.12.56] — 2026-09-18

- **批次 C · Layer 4 运行时收尾协议（P-1~P-5）**：把「子代理完成后主控不自动推进」的**无人值守环**（2026-09-18 实测：约 17 分钟零完成事件，只能事后读盘重建状态）从「靠运气」改为**可核查协议**：
  - **P-1 收尾协议（硬约束）**：`_shared/dispatch-header.md` 新增 §收尾协议 —— worker 写完交接报告后**以正常最终消息结束回合**（该消息即 completion event）；**主动作废**自行 `sessions_yield` 的写法（worker 自 `sessions_yield` = 挂起 run 而非完成它 ⇒ 主控收不到完成事件）；交接摘要**不得**塞进 `acknowledgment` 字段（该字段不从子代理回合发出，实际不送达 ⇒ 完成事件 + 摘要双丢）。9 张角色卡 + 两份交接报告模板同步接线，禁用原语清单统一为 `sessions_yield` / `agents_wait` / `next_check` / `subagents` / `sessions_list` / `sessions_history`。
  - **P-2 主控兜底唤醒**：`00-主控-扩展职责.md` 新增第 6 条（与既有第 1 条「spawn 后不轮询」**并存不冲突**）—— spawn 后**必须**安排一次定时自唤醒（= 该角色硬卡阈值 + 缓冲），到点**主动 `read` 核对磁盘产物**，**推进判据以磁盘产物为准**、completion event 仅作**加速信号**；宿主无可用定时面 ⇒ 退化为「下次进入本会话即复核」+ `status.md` 记 `watchdog_unavailable`（不得静默）。⚠️ 方案原文示例的 `automations` **在 `denied` 内**，本协议**不授权调用**（本版不改 `denied` / `coordinator_only`）。
  - **P-3 能力自检真收口**：把「写 `能力自检：通过`」升级为**必须逐项列出本会话实际可见的工具清单**（禁止只写「通过」），档位不符 ⇒ 当场回报主控、不继续跑（实测事故：派发前未核实实际工具面 ⇒ 子代理无 `exec`/`grep`，无法自验）。
  - **P-4/P-5 版本链完整性**：交接报告模板正文须随最终消息结束回合；`dispatch/T5-写手.md` + `dispatch/T7-审计.md` 新增 —— 每个 `drafts/初稿-vN.md` 须配同版本号 `交接报告-T5-vN.md`，或 `修订说明-vN.md` 记录完整版本链（版本号 + 日期 + 产物路径）；缺任一版本且无记录链 ⇒ 该版本**不可核验**（T7 判 **P1**；`status.md` 回环记录**不替代**版本链）。实测反例：仅产 `v{1,3,4}`，v2/v5 缺失。
- **批次 C · Layer 5 删除清理（D-1~D-3）**：
  - **D-1 多格式导出彻底移出 Phase 0（主人裁定 2026-09-18）**：删 Phase 5 的 A–F「多格式导出选择卡」（7 文件），改为**并入 M-13「主人自行操作建议清单」第 1 项**（执行者 = 主人 host shell，**agent 不执行**任何转换命令）；`SKILL.md` / `关键协议.md` / `external-services.md` / `设计文档-哲学.md` / `checkpoint-card-template.md` / `任务简报-template.md` / `00-主控-扩展职责.md` 六处「3 项 + 多格式 6 选项」口径统一收敛为「**2 项**（期刊匹配 / 中文数据源）」。
  - **D-2 配图表述核实**：全清单仅 2 处涉及配图，均为合规表述（`image_generate` 已于 v2.12.52 移除 ⇒ 论衡不调用），**未为改而改**。
  - **D-3 建议清单命令同源**：T8 命令模板改为与 `_shared/format-export.md` §〇/§二 **同源**，并显式标注 latex/docx/pdf 所需模板 / `.bib` / `.csl` **需主人自备**（否则会卡壳）；封面类**无统一可复制命令**故模板只覆盖第 1/2/4 类。
- **M-Gate 规范补全（M-1~M-7）**：
  - **M-2 抽取规则唯一真源**：`M-Gate-Algorithm.md` 新增 §统一抽取规则真源（**A 文末节集合**：REQUIRED 4 / OPTIONAL 3 / ALL 7 / NONSTANDARD；**B 引用编号正则**：标准 / 基线 / 表格三类），消除**三组**同源不一致（M-Form-2↔M-Form-7、M-Form-1↔M-Exist-3，外加 A.2 未列的 M-Form-3↔M-Form-7 marker 清单）；各门改为引用真源 + 派生展开视图（注明「非第二真源」）。
  - **M-1 悬空指针**：§6 删「主人手工跑 `bash scripts/m-gate-check.sh`」实指写法（全仓无该文件），改为显式标注「未实现 / 未随仓保留」，**不凭空造脚本**。
  - **M-3 弱门评估留痕**：M-Exist-3 等弱判据显式标注「属实弱门，**评估结论：弱，但有意保留**」+ 三条理由（强判据在中英混排/内联引用下必误报；正确性已由 M-Exist-1/M-Form-8/M-Form-3 承担；P0 阻断类塞易误报判据 = 用误报换假阴性）。
  - **M-4 判据收窄**：① 「正文泄露术语」由裸 substring 改为词边界 + 结构位置约束（旧写法使正文合法的「T1 加权成像」「七段式论证」在 **P0** 误报，一次误报 = 白烧一轮修订）；② 证据-信任级别由「计数相等」改为**逐条/逐行配对**（`len(条目) == len(信任级别)` 不等价于每条都有信任级别）。
  - **M-5 判定出口唯一真源**：13 项 M 门伪代码统一经 §统一抽取规则真源 C 的 `verdict_pass` / `verdict_fail` / `verdict_undecidable` / `verdict_path_error` 返回，`档位` 取值与附录 schema `判定记录_双字段` **逐字一致**。
  - **M-6 依赖面补全**：`scripts/m_gate_dependencies.yaml` 补 M-Form-1 / M-Exist-3 的 `final/图件/*.svg` 依赖（对齐自审门 J）、M-Form-8 的 `01-任务简报.md` 依赖（伪代码从简报提取 `[论点N]`），并注明**本文件只影响「变更定位范围」、不产出 M 门结论**。
  - **M-7 未定义 helper**：新增 §未定义 helper 清单与替代口径（`extract_intext_v2` / `extract_endnote_v2` → 按真源 A + B 切分提取）。
- **残余 S-4 指针化收口**：`references/templates/任务简报-template.md` 最后一处轮次口径复述点（原「第 3 轮触发 → Acknowledged Limitations 模式」）改为指向 `_shared/pipeline-overview.md`『修订回环仲裁规则』。
- **教训库同步**：`lessons-max.snapshot` 409 → **420**（主真源续录 #415-#420 六条论衡类教训）；`教训索引.md` 最大编号同步为 #420，并注明**编号撞号未清**（#415×2 / #416×2，撞号不推高本值语义）。
- **验证**：构建期三件套全绿 —— `flow-check.py` rc=0、`self-audit-gate.sh` **PASS 26 / FAIL 0**、`pytest` **348 passed**；`link-check` 相对链接 485 条 + 入口裸引用 2 条全部可解析。

---

---

## [v2.12.55] — 2026-09-18

- **批次 B · Layer 2 真源修复（S-2~S-6）**：
  - **S-2 盲审禁代笔**：`t9_review` **删除**通用 fallback `on_worker_failure.executor: 主控`，改为 `independence_failure_policy`（`retry_spawn_only` / `retry_limit` / `executor_takeover: forbidden` / 重试耗尽 ⇒ `record_missing_and_notify_owner`）；封掉「盲审节点由主控接管」的结构性冲突——主控已读遍全部内部材料，代笔即独立性归零且**事后不可修复**。构建期门 = `flow-check.py` 规则 30。
  - **S-3 同 provider 连续静默升级**：顶层新增 `provider_silence_escalation`（同 provider 连续 **≥3** 次静默 ⇒ **强制暂停 + 呈现主人三选**：换 provider 族 / 换能力档 / 接受同源并披露；**无默认项、必须挂起**），补齐「spawn 前探活门管不到 accepted 之后不产出」的缺口（实测背景：批判审计档 4 连静默无任何升级规则）。构建期门 = `flow-check.py` 规则 31。
  - **S-6 Phase 1.5 触发条件**：删首轮不可达的占位项「T9 证据强度评分低」，改为明示「**上一轮 T9 审稿报告**指出证据强度不足（仅续跑可达）」。
  - **S-4 修订回环口径归一**：轮次口径**唯一真源 = `_shared/pipeline-overview.md`『修订回环仲裁规则』**；全仓副本（README / QUICKSTART / 架构篇 / 哲学篇 / 关键协议 / glossary-core·full / deliverables / errors / dispatch T5·T7 / audit-checklist-quickref / writer·auditor 卡 / 主控扩展职责）改为**指针**，不再复述轮次数字。
  - **S-5 字数上限口径归一**：`字数判定表.md` 不再复述绝对上限，四档一律按任务简报 **`body_limit`（M-14）比例换算**，消除历史上与 `body_limit` 的互斥。
- **新增/加强测试**：`tests/test_flow_check.py` 新增 8 个用例（S-2 正向/锚点 + 2 条反向注入；S-3 正向/主控卡双向接线 + 2 条反向注入）。反向注入实测：恢复通用 fallback ⇒ `rc=2` 并点名 `t9_review（blind_review）仍声明 on_worker_failure.executor: 主控`；阈值改 `9` ⇒ `rc=2` 并点名 `provider_silence_escalation.threshold->9`；副本还原 ⇒ `rc=0`，真源 sha256 前后一致。

---

---

## [v2.12.54] — 2026-09-18

- **批次 A · Layer 1 机械校验（R-1~R-6）**：把「派生文档与真源漂移」从「靠人记」改为「构建期红」（均位于构建期 `scripts/flow-check.py`，由维护者 host shell 运行；**论衡运行期仍零 exec**）：
  - **R-1 全景一致性**：全景**收敛为唯一一份派生视图**（`_shared/pipeline-overview.md`，23 节点全表 + 修订回环仲裁表）；其余文档**删除全景段、只留指针**；登记真源 = `phase_order.yaml` `panorama_sources`（canary / mirrors / pointer_exempt）；`pointer_exempt` 文件亦**禁承载全景段**。实测背景：11 份含 Phase 序列的文档**无一与真源一致**（pipeline-overview 缺 4 节点且 T7.5 门位置倒置、README 缺 7、pipeline-readme 缺 4、QUICKSTART 口径错 + 指针失效）。
  - **R-2 节点 id 合法性**：status 模板必含「节点 id 取自 yaml / **禁止自创**」断言（历史事故：自创 `t5_final_v5` 致进度表顺序错乱）。
  - **R-3 Done 记账一致性**：`Not Triggered` / `opt_out` / `pending_owner` / 产物缺失 **一律不得计 Done**；汇总行须与逐节点行一致。
  - **R-4 条件字段生产方**：`condition_definitions` 每条必须登记 `producer` + `producer_marker`，否则构建期红 —— 封掉「条件字段全仓无生产方 ⇒ 节点静默不触发」（实测：T9 依赖 `owner_peer_review_consent` 无生产方 ⇒ **T9 整节点消失**、主控代做其产出并给出编造精度）。
  - **R-5 T8 建议清单四类**：文档格式转换 / SVG→PNG / **封面视觉** / **SHA256 登记** 缺一即 T8 不合格（实测：交付说明只给两类、「封面」0 命中）。
  - **R-6 条件不可判定处置**：声明 `condition` 或 `opt_out` 的节点必须显式声明 `condition_undecidable`，禁止用 `on_not_triggered` 静默吞掉「条件证据读不到」。
- **夹带的最小真源修复（S-1）**：`t9_review` 由 opt-in（`owner_peer_review_consent`，**全仓无生产方**）改为「**默认启用 + 主人 opt-out**」（写法同 `methodology_snapshot`）；`任务简报-template.md` 新增 `owner_peer_review_opt_out` 与 `owner_methodology_snapshot_opt_out` 两个生产方字段（后者原为同型断链）。
- **批次 A · Layer 3 表述收敛（T-1~T-5）**：修订回环口径按主人 2026-09-18 裁定归一（**不计轮** = Phase 3.5 主人洞察轮；**轮 1** = Phase 3.6/3.7 批判修订；**轮 2** = Phase 4.2 审计修订；超限 → Acknowledged Limitations 须主人拍板），失效副本（QUICKSTART / degraded-scenarios 等）改为指向 `_shared/pipeline-overview.md`；修复 QUICKSTART 指向已外移 SKILL.md 章节的失效指针；**Phase 0 不再询问输出格式、不再询问是否配图**（格式转换/封面/SHA256 一律下行到 T8 终检后的「主人自行操作建议清单」）；人环卡新增「13 步 ↔ 23 节点映射说明」；`pipeline-readme` 删残留「4 选 1」孤行并明确「Phase 0 呈现时必须实际列出四个模式」。
- **新增/加强测试**：`tests/test_flow_check.py` 补 R-4 / R-6 / R-2+R-3 / R-5 / R-1(exempt) 正向断言 + 反向注入用例（真源 sha256 前后不变、副本必红）。

---

---

---

> ⚠️ **范围说明（v2.12.47 起）**：本文件只保留**最近 5 期**；**更早**的全部章节逐字迁入（当前边界见归档文件头部的轮转记录，本节不再写字面版本号，防漂移） [`CHANGELOG-archive.md`](CHANGELOG-archive.md)。部分历史条目链接指向 `docs/` 或 `../outputs/` 中的**当时产物**（发布说明 / 审计报告 / 设计方案），这些文件**已随清理移除或归档**，链接可能失效——**属史料，不影响当前使用**。当前版本行为以 [`SKILL.md`](SKILL.md) 与 `references/` 为准。

论衡（`lunheng-article-pipeline`）版本变更记录。**本文件 + [`CHANGELOG-archive.md`](CHANGELOG-archive.md) 共同构成仓库内 changelog 的单一真源**（`scripts/changelog-check.py` 同时读取两份，「每个版本 tag 都有章节」的校验不受拆分影响）；GitHub [Releases](https://github.com/zuoyunlai/lunheng-article-pipeline/releases) 是同一内容的发布视图。

- **排序**：版本倒序（最新在前）。查找某一版本：`grep -n '^## \[v2.12' CHANGELOG.md CHANGELOG-archive.md`
- **章节标题**：`## [<tag>] — <发布日期>`；正文＝该版本 Release 正文逐字保留（早期 Release 由 GitHub 自动生成，正文天然偏薄，`python3 scripts/changelog-check.py --report` 可列出）。
- **发版流程**：建 GitHub Release 后执行 `python3 scripts/changelog-check.py --fill` 回填本节；也可直接手写章节。`--check` 校验「每个版本 tag 都有章节 + 围栏闭合 + 当前版本已记录」，`--online` 追加校验「每个版本 tag 都有 GitHub Release」。
- **发版前置闸（教训 #332 / #334）**：任何对外发版动作（push / tag / GitHub Release / 净化包）前先跑 `bash scripts/release-preflight.sh <tag>`——两查一停：**在飞链**（同项目 `status=running` 会话）/ **编号占用**（本地 tag + `git ls-remote --tags` 双向）/ **工作区干净**（`git status --porcelain`），任一不过即非 0 退出（10/11/12）；通过时打印「远端 master / 本地 HEAD / tag 区间 / 在飞链=0」四行现状。`scripts/create-github-release.sh` 的写路径已强制调用本闸（并自动带 `--allow-existing-tag`：② 口径 = 「编号是否被本链之外的人占用」，避免「先 tag、后补发 Release」被自己的闸自锁），`--dry-run` / `--check` 不进闸。闸只读：不自行 push / 打 tag / 建 Release。
- **非版本 tag**（`full-repo-consistency-audit-2026-09-06`、`before-batch1-optimization`）不进入本表。

---

---
