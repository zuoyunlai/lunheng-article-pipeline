# Changelog

> ⚠️ **范围说明（v2.12.47 起）**：本文件只保留**最近 5 期**；**v2.12.44 及更早**的全部章节逐字迁入 [`CHANGELOG-archive.md`](CHANGELOG-archive.md)。部分历史条目链接指向 `docs/` 或 `../outputs/` 中的**当时产物**（发布说明 / 审计报告 / 设计方案），这些文件**已随清理移除或归档**，链接可能失效——**属史料，不影响当前使用**。当前版本行为以 [`SKILL.md`](SKILL.md) 与 `references/` 为准。

论衡（`lunheng-article-pipeline`）版本变更记录。**本文件 + [`CHANGELOG-archive.md`](CHANGELOG-archive.md) 共同构成仓库内 changelog 的单一真源**（`scripts/changelog-check.py` 同时读取两份，「每个版本 tag 都有章节」的校验不受拆分影响）；GitHub [Releases](https://github.com/zuoyunlai/lunheng-article-pipeline/releases) 是同一内容的发布视图。

- **排序**：版本倒序（最新在前）。查找某一版本：`grep -n '^## \[v2.12' CHANGELOG.md CHANGELOG-archive.md`
- **章节标题**：`## [<tag>] — <发布日期>`；正文＝该版本 Release 正文逐字保留（早期 Release 由 GitHub 自动生成，正文天然偏薄，`python3 scripts/changelog-check.py --report` 可列出）。
- **发版流程**：建 GitHub Release 后执行 `python3 scripts/changelog-check.py --fill` 回填本节；也可直接手写章节。`--check` 校验「每个版本 tag 都有章节 + 围栏闭合 + 当前版本已记录」，`--online` 追加校验「每个版本 tag 都有 GitHub Release」。
- **发版前置闸（教训 #332 / #334）**：任何对外发版动作（push / tag / GitHub Release / 净化包）前先跑 `bash scripts/release-preflight.sh <tag>`——两查一停：**在飞链**（同项目 `status=running` 会话）/ **编号占用**（本地 tag + `git ls-remote --tags` 双向）/ **工作区干净**（`git status --porcelain`），任一不过即非 0 退出（10/11/12）；通过时打印「远端 master / 本地 HEAD / tag 区间 / 在飞链=0」四行现状。`scripts/create-github-release.sh` 的写路径已强制调用本闸（并自动带 `--allow-existing-tag`：② 口径 = 「编号是否被本链之外的人占用」，避免「先 tag、后补发 Release」被自己的闸自锁），`--dry-run` / `--check` 不进闸。闸只读：不自行 push / 打 tag / 建 Release。
- **非版本 tag**（`full-repo-consistency-audit-2026-09-06`、`before-batch1-optimization`）不进入本表。

---

## [v2.12.52] — 2026-09-17

> **主题：能力移除登记收口 —— 封面（`image_generate`）与格式转换彻底退出流水线，全仓去「宿主加固」语言。**
> **性质：文档口径收口 + 能力移除登记 + 平台责任边界中立化。无新增能力、无破坏性行为变更、无安全语义变化。**

### 一、封面与格式转换退出流水线（接续 v2.12.49「`image_generate` 入 denied」，本轮清文档侧残留）

- **外发服务类别 4 → 3 类**：删「③ 封面（opt-in）」行；同意轴 A「外发数据形态」**3 → 2 项**（检索关键词 / 大模型推理全文）
- `references/_shared/关键协议.md`：4 选 1 选项 ①/③ 去「图像 prompt」；同意门逐类表删「封面（`image_generate`）」行；**新增「v2.12.52 能力移除登记（非口径削弱）」**段 —— 明示条目消失源自能力删除（该外发路径客观不存在），且「未恢复调用能力前，任何后续版本不得重新出现封面同意项」
- 统一表述为「**封面与格式转换不在流水线内**」→ T8 终检后写入「主人自行操作建议清单」（命令模板 + 执行者 = 主人 host shell）：`operations.md` / `图表-SVG-template.md` / `glossary-full.md` / `phase-1-details.md` / `pipeline-overview.md` / `external-services.md` / `dispatch-header.md` / `任务简报-template.md` / `checkpoint-card-template.md` / `投稿就绪检查表-template.md` / `SKILL.md` / `QUICKSTART.md`
- 删除残留授权面：`README.md` 外发服务表行、`pipeline-readme.md` 逐类表行、`_shared/工具能力边界.md`「可视化：image_generate」行、`glossary-full.md` 服务清单第 4 条与备选方案「封面生成」三条
- `图表-SVG-template.md`：数据图表 vs 封面视觉对比表收敛为单列（数据图表）；转换表删「主控调 `image_generate` 转 PNG」行与 Phase 0「PNG 转换需求」触发门
- `任务简报-template.md`：`consent` 结构体删「图像 prompt」/「封面」两键（轴 A 2 项 / 轴 B 3 类）

### 二、去「宿主加固」语言（平台责任边界中立化）

- 全仓措辞：「宿主未加固 / 加固缺口 / 加固配方 / 加固状态」→ 平台中立表述（「平台给的工具面比本档声明宽」「平台工具策略由平台与宿主负责」），涉及 `SKILL.md` / `permissions.md` / `dispatch-header.md` / `agents/00-主控-扩展职责.md` / `external-services.md` / `关键协议.md` / `glossary-full.md` / `README.md` / `QUICKSTART.md` / `status-template.md`
- `references/permissions.md`：四层表 ②/③ 行「**可选**（见 `host-hardening-recipe.md`）」→「**平台职责**（论衡不配置、不校验）」；「加固状态判据与默认口径」→「工具面判据与默认口径」；「为何不采纳 A 档（宿主未加固即拒跑）」→「为何不采纳『平台未收紧即拒跑』」
- `status-template.md`：删「不记录『加固状态』」记录位表述 → 只留「不记录宿主配置明细、不记 deny 原文」
- `README.md`「权限设计取舍（对审计方/扫描器明示）」段重写：子代理角色白名单改述为**声明式调用边界**（描述本 skill 自身不越权；加载器不执行），删除指向 `host-hardening-recipe.md` 的部署建议
- `图表-SVG-template.md` 等处的「真实隔离由宿主 config 机械层生效」句保留原文（属能力边界说明，非加固承诺）
- **保留**：`references/_shared/host-hardening-recipe.md` 本体仍在仓库（维护者附录，`sync-version.sh` / `check-version.sh` 版本戳依赖），只是不再充当运行时文档的授权来源

### 三、附带一致性（审计 P1/P2 文档卫生）

- 删「single-controller 不 spawn」残留（`asset-index.md` / `字数判定表.md` / `agents/03-案例检索` / `设计文档-架构.md` / `任务简报-template.md`）—— 与 v2.12.46「多 Agent 九角色为唯一标准架构」对齐
- `字数判定表.md`：`<2000 字` 行「流水线偏重，建议简化（主控+写手两角色直写更快）」→「**论衡不适用**（流水线偏重；主控+写手直写、不 spawn 多角色）」
- `deliverables.md`：教训 #270 行去第三方署名
- `scripts/self-audit-gate.sh`：注释「md5 仅作可选加固」→「md5 仅作可选校验」

### 四、验收（实测回填）

- `python3 -m pytest tests/ -q` → **331 passed**（0 failed）
- `bash scripts/self-audit-gate.sh` → **26 PASS / 0 FAIL**
- `python3 scripts/flow-check.py` → **RC=0**
- `python3 scripts/changelog-check.py --check` → **RC=0**
- `bash scripts/check-version.sh` → **通过**（版本号 v2.12.52）

> ⚠️ **未做项（待主人批）**：本批次**仅本地提交** —— 未 push / 未打 tag / 未建 GitHub Release / 未构建净化包。发版前须先跑 `bash scripts/release-preflight.sh v2.12.52`；本轮已随提交把最旧章节 v2.12.47 迁入归档（主文件保持 5 期）。

---

## [v2.12.51] — 2026-09-17

> **主题：批次 B 一致性收口 —— 只读档写盘主体唯一化（D-3）+ 测试反向注入不再写真源（D-4）。**
> **性质：真源口径统一 + 测试污染面消除。无新增能力、无破坏性变更、无安全语义变化。**

### 一、D-3：只读档「报告写盘主体」唯一化（统一为「主控代写盘」）

- **背景**：v2.12.50 一致性审计检出两套口径并存 —— 10 处角色卡 / dispatch 写「我无 `write` 工具，报告随交接回传、由主控 `write` 落盘」，而 `permissions.md:61`「两径定义」+ `phase-order.yaml` 四节点 `write_authority: executor` + `dispatch/T9-同行评审.md:40` 写「报告由 T9 写盘」。
- **裁定**：统一为「**主控代写盘**」。三条理由：① 只读档确无 `write` 工具 = 更强的权限姿态；② 与 10 处角色卡 / dispatch 口径一致；③ 与 `verification_authority: 主控` 自洽（核验者不落盘则无从核验）。
- `references/_shared/phase-order.yaml`：`t6_critique` / `t7_audit` / `g14_style_gate` / `t9_review` 四节点 `write_authority: executor` → **`owner`**（行尾注明 D-3）；T1/T2/T3/T4/T5 等自有产物节点保持 `executor` 不动。
- `references/permissions.md`：删「只读档落盘例外（v2.12.32/33 两径定义）」，改为统一口径段（工具面 = `read`；报告正文随交接回传、主控 `write` 落盘；不得直写；上游产物一律只读）；五档表 `allow_audit` / `allow_review` 两行「工具集」列去掉「+ 自有报告可写」，第三列改为「不修改上游产物；报告由主控落盘」。
- `references/dispatch/T9-同行评审.md`：「报告由 T9 写盘；主控收到后 `read` 核验并 `write` 落盘二次核验」→「报告正文随交接回传；主控收到后 `write` 落盘并 `read` 核验（**读盘确认铁律**）」；**T9 独立性硬定义（禁主控代笔、主控只做派发 / 收报告 / 落盘拼装）表述不变**。

### 二、D-4：测试反向注入不再写真源（副本注入 + 硬断言）

- **背景**：`tests/test_flow_check.py` ≥11 处反向注入直接 `write_text` **真源**（`phase-order.yaml` / `字数判定表.md` / `可发表性判定表.md` / `08-终检-final-inspector.md`），仅靠 `try/finally` 恢复 —— kill / 超时 / 并行即**永久污染真源**。
- 新增 helper：`_sandbox()`（`copytree` 整仓 → `tmp_path/repo`，忽略 `.git` / `__pycache__` / `.pytest_cache` / `*.pyc`）+ `_flow_check_in()`（`subprocess.run([sys.executable, <副本>/scripts/flow-check.py], cwd=副本根)` —— 因 `main()` 读**相对路径** `references/_shared/phase-order.yaml`，cwd 必须 = 副本根）+ `_inject_and_expect()`（三断言：真源 sha256 前后不变 / 副本 RC≠0 / 报错指向预期节点或路径）。
- 11 处反向注入全部改为副本注入；`tests/test_flow_check.py` 独立跑模式（`__main__`）支持 `tmp_path` 参数（临时目录注入）。

### 三、新增机械门「只读档写权」（flow-check）+ 双向回归

- `scripts/flow-check.py` 新增「只读档写权」检查：`role ∈ {T6, T7, T9, G14}` 且 `kind ∈ {agent, conditional_agent, advisory_agent}` 的节点，`write_authority` 必须为 `owner`，否则输出含该节点 id 的错误。（编号取 **23**：13–22 已被 v2.12.49 M/T 系列占用；清单见脚本头部 docstring）
- `tests/test_flow_check.py`：`test_every_worker_node_declares_role_writability_and_takeover` 改为按档位区分（只读档 → `owner`；自有产物 → `executor`）；新增正向 `test_readonly_tier_reports_are_owner_written` + 反向注入 `test_flow_check_detects_readonly_tier_write_authority`（`t6_critique` 改回 `executor` ⇒ 必须红，教训 #399「机械门必须能红」）。

### 四、验收（实测回填）

> 本批次编辑与验收在**同一次会话补齐**：先由无 exec 的会话完成编辑（留下版本号半 bump 状态），再由具备 shell 的会话执行 `scripts/sync-version.sh`（90 文件）并回填下列实测值。

- `python3 -m pytest tests/ -q` → **331 passed**（0 failed；含新增副本注入 helper 与规则 23 双向回归）
- `bash scripts/self-audit-gate.sh` → **26 PASS / 0 FAIL**
- `python3 scripts/flow-check.py` → **RC=0**
- `python3 scripts/changelog-check.py --check` → **RC=0**（唯一输出为「CHANGELOG 有章节但本地无 tag: v2.12.51」提示，属未发版前的预期态，tag 随发版生成）
- `bash scripts/check-version.sh` → **通过**（README install pin / 9 角色编号 / 版本号三者一致，v2.12.51）

> ⚠️ **过程留痕（教训 #399 同族）**：本批首轮实测为 **4 failed + 自审门门 C FAIL**，根因非逻辑缺陷，而是「版本号只 bump 了 `SKILL.md`、未跑 `sync-version.sh`」⇒ 51 个文件仍带 v2.12.50 戳 ⇒ 门 C 红，并连带污染 `tests/test_gate_h_reverse_diff.py` 的 4 条断言（该测试解析自审门输出，遇门 C 失败即误判）。**改版本号必须原子完成「bump + sync + 门 C 绿」**，不能拆到两个会话。

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
