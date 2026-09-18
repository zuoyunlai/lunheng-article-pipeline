# Changelog

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

## [v2.12.53] — 2026-09-18

- **能力边界收口**：移除 `host-hardening-recipe.md` 维护者附录；运行文档与测试锚点统一回到 skill 自身声明与权限真源，不把宿主侧配置作为本 skill 前提。
- **批次 C1（P0）**：删除 single-controller / 紧急模式绕过 Phase 2.5 / 第 3 轮自动降级 / G14 超时自动选择 A 等 fail-open 残留，统一改为显式主人裁决与 `pending_owner` 挂起。
- **批次 C2（P1）**：清除 image_generate 授权残留、200 字/exit 0 旧判据、G14/T6 相位与图位数量分叉、轻量档与硬卡区间漂移；补齐 G14 checker 单类严重度档和 T5 六条铁律口径。
- **批次 C3（P2）**：统一 G 清单 17 项、denied 41 项、24 中文期刊、角色/信任级别/心跳命名/ACK 分档/人环四节点等计数与文档引用，修复失效路径及重复表述。
- **批次 D**：教训索引、`lessons-max.snapshot` 与 `LUNHENG_LESSON_EXCLUDE` 同批刷新；论衡类最大编号由 #373 更新为 **#409**。


---

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
