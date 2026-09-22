# Changelog

---

## [v2.12.73] — 2026-09-22

- **安全边界修订**：修订 T5 字数估算失败恢复流程，删除 `exec` + Python、`cp` 和 shell 命令路径，改为仅使用已授权的 `read` / `write` / `edit` 工具。
- **越权防护**：明确恢复流程不得要求、暗示或调用 `exec`、`process`、`code_execution` 等执行类工具；无法可靠统计字数时必须暂停并请主人在本机自行统计，不得用估算冒充实测。
- **同步修订**：更新 T5 派发卡、写作角色卡与执行韧化协议，统一采用 `read → write → edit → read` 的版本修订 SOP。
- **验收基线**：自审门 **37 PASS / 0 FAIL**；正文版本一致性门 **2 passed**；`git diff --check` 通过。

## [v2.12.72] — 2026-09-22

- **批次 2-E：主控上下文预算管理**：在 `pre_spawn_enforcement` 接入声明式上下文预算门，按字数档位预估主控累计 token；阶段边界复核余量，低于阈值给出落盘减负建议，超过预算给出 `overspend_alert`。预算模型以 `performance-benchmarks.md` §五为校准真源，缺失值保持 `unavailable`，不臆测。
- **批次 3-D：端到端活体冒烟协议**：新增 L1 机制冒烟 / L2 轻量档全流程冒烟规范、`smoke_run_id` 等 status 留痕、性能表登记和发布前 SOP；明确冒烟不进 CI，主人 checkpoint 仍 fail-closed，未实际运行不得冒充活体通过。
- **批次 4-B：flow-schema 产品化试点**：新增通用声明式 `scripts/flow-schema.py` 引擎、论衡演示 schema 与负例注入 cookbook；支持载体存在性、token 存在/禁用断言、重复键 fail-closed。完整论衡规则仍由 `flow-check.py` 负责，演示 schema 不替代旗舰校验。
- **批次 5-G：可观测性最小层**：status 模板新增 `status_json` 机器可解析快照，结构化记录 spawn 落地、截断、G14、M 门、token、修订轮和冒烟状态；性能登记表增加聚合指针，未知值保留 `null` / `unavailable`。
- **批次 5-F：英文场景最小试点**：任务简报与交接报告增加字段标签英文对照，明确“仅参考、判据真源仍为中文”；完整英文角色卡/模板及英文 AI 痕迹检测暂缓，等待真实需求证据，避免与治理瘦身冲突。
- **机械接线**：新增 flow-check 规则 46–49，覆盖上下文预算、活体冒烟、status_json 与英文参考层；新增规则均配正向/反向测试并登记进规则覆盖台账；脚本索引扩至 30 条。
- **范围边界**：本批新增运行协议与开发者侧工具，但**未执行真实 L1/L2 活体冒烟**；首次冒烟仍需维护者/主人在场并按协议回填登记表。
- **验收基线**：最终全量测试、构建净化链、flow-check、flow-schema、链接门、自审门和版本门全部通过后发布。

---

## [v2.12.71] — 2026-09-22

- **重量档实测数据回填（优化方案 C，P1）**：主人 2026-09-22 在另一对话跑完首个重量档实战项目《谁有权认定你自愿？——同意门槛的“认证政治”》（`consent-certification-politics-2026`，正文 12721 字），按 `performance-benchmarks.md` §一字段口径回填真实数据。

- **① 性能基准表新增重量档实测行**：字数 12721（T8 `body_char_count`）/ 耗时约 2h40m（任务简报 11:06 → Phase 5 验收 13:46）/ token 286k in + 5.5k out（主控精确）/ 成本 ≥$0.31（主控）/ 引用 31 条 / 修订轮 2 / 子代理 15 个心跳留痕。重量档首次有实测记录。

- **② 外推守则据实修订**：重量档由“尚无实测”改为“已有 1 例实测”，但尚不足 3 行不同档位实测，README/QUICKSTART 的耗时数字继续保持“估计”措辞；同步更新两处预计时间说明。

- **③ 数据缺口如实登记**：子代理 completion event Stats line 未沿回传路径带回主控，因此 token/成本仅主控侧精确；`status.md` 阶段表时间戳与产物 mtime 也存在不一致，耗时采用可复算的任务简报创建时间至 Phase 5 验收时间。

- **验收（实测回填 · 最终态）**：自审门 **PASS 37 / FAIL 0**；`python3 -m pytest tests/ -q` → **480 passed**；`python3 scripts/flow-check.py` RC=0；`bash scripts/check-version.sh` 通过；`python3 scripts/link-check.py` 全绿。

- **本批范围**：1 行重量档实测数据 + README/QUICKSTART 口径更新 + 记账。**无新增运行能力、无判据变更**（纯数据/文档层）。

---

## [v2.12.70] — 2026-09-21

- **治理瘦身（方案 A，P0 战略）**，主人 2026-09-21 指令「批次1 A 治理瘦身」——对 2026-09-21 优化方案「A. 治理复杂度瘦身」落地。方案 A 三步：① `_shared/` 分层 ② 治理叙事归档外移 ③ 规则软上限。本批完成 ① 分层 + ③ 规则软上限；② 归档核验后**无 30 天未引用对象**（治理/ 5 文件全有活跃引用，仓库历史仅 12 天），如实记录不做硬造归档。

- **① `_shared/` 物理分层（真源/ 30 文件 + 治理/ 5 文件）**：方案 A 核心——`_shared/` 588K 里「治理叙事」（教训索引/审计链/变更考古/反哺报告）与「判据真源」（phase-order.yaml / M-Gate-Algorithm / 字数判定表 / 路径校验规范）长期混在同一目录，新人/新子代理分不清「哪些是必读真源、哪些是历史复盘」。本批拆为两个子目录：**真源/**（30 文件，判据真源，每次必读）+ **治理/**（5 文件，治理叙事，按需查证）。纯目录重组，不改判据内容。

- **①-补 · 全仓引用修正（分层机械后果，本批最大工作量）**：35 文件下移一层后，全仓 74 文件 421 处 `_shared/<文件名>` 引用 + 真源/治理内部 32 处交叉引用 + 51 处 markdown 相对链接断链全部修正；`scripts/.pkg-manifest.txt` 32 条路径重排（LC_ALL=C 字节序）；`build-clawhub-release.sh` SHARED_ADMITTED 白名单带子目录前缀 + find 递归（-mindepth 1 -maxdepth 2）；`self-audit-gate.sh` 候选池 glob + 门 Y 上限；12 个测试文件 Path 分片写法；门 Y 体量棘轮上限按实上调（00-主控 73538→74028 / M-Gate 84250→84274 / phase-order 55272→55328，均为路径前缀机械变长，非内容膨胀）。

- **③ 规则软上限（治「规则的规则」内卷）**：`tests/test_flow_check_meta.py` 新增 `RULE_COUNT_MAX=50`（当前 46 条，只许降）+ `test_rule_count_soft_ceiling`；`self-audit-gate.sh` 新增**门 Z**（自审门项数软上限 `GATE_COUNT_CEIL=40`，warn 级软门，不计 exit code）。逼「加规则前先合并/退役旧规则」。

- **验收（实测回填 · 最终态）**：自审门 **PASS 37 / FAIL 0**（门 Z 使 PASS 36→37）；`python3 -m pytest tests/ -q` → **480 passed**（+1 条软上限测试）；`python3 scripts/flow-check.py` **RC=0**；`bash scripts/check-version.sh` 通过（v2.12.70）；`python3 scripts/link-check.py` 全绿（518 链接 + 281 内联）；`python3 scripts/changelog-check.py --check` RC=0。

- **本批范围**：目录重组（35 文件）+ 全仓引用修正 + 2 处软上限机械门 + 1 条测试 + 记账。**无新增运行能力、无判据内容变更**（纯工程/治理层）。**未 tag、未 push**（发布动作等主人点头）。

---

## [v2.12.69] — 2026-09-21

- **写作质量守门批次 1（借 DSH writing-guard，续批次 0）**，主人 2026-09-21 指令「继续批次1修订」——对 2026-09-21 优化方案「H 类：写作质量守门」剩余三个借鉴点（H4/H5/H6）落地。批次 0 已完成 H1/H2/H3（三个 P1），本批落地 H5/H6（P2/P3）+ H4 交叉引用标注，**H 类 6 点全部闭环**。借鉴对象 `github.com/xmutfyh/dsh-plugin-writing-guard`，仍**只借鉴方法论、不引入其 exec 实现**（论衡零 exec 路线不变）。

- **① H5 · G17「数据指纹比对」（借 EVIDENCE 层「Scholarship Lock」）**：对正文所有硬数据点（数字 / 单位 / p 值 / DOI / 统计量）做**修订前后精确比对**——修订 / 润色后数据指纹必须与修订前一致，**不可静默改写**。与 G2 数据溯源互补（G2 看「数字有无来源」真实性，G17 看「数字在修订中变没变」完整性）。静默改写（改了但修订说明未披露）→ P1；豁免窄口 = 修订说明记载「数据修正依据」+ T7 核验回查依据真实。触发时机 = T7 审计（修订回环每轮核对 vN → vN+1）。

- **② H6 · T9「期刊约定校验」（借 JOURNAL 层 scope/style/convention）**：T9 期刊匹配从「纯 LLM 判断」升级为「期刊约定词表 + 确定性核对」——① scope 学科范围 / ② style 引文风格（GB/T 7714-2015 / APA / MLA / Chicago 对齐）/ ③ convention 格式约定（栏目 / 字数上限 / 结构）。任一类不满足 → 匹配度降档并标注缺口；目标期刊无已知约定 → 标注「需主人补充期刊约定」。落点 = T9 同行评审 + 09-审稿角色卡。

- **③ H4「润色膨胀指数」——已被既有约束覆盖，不另立第二判据**：writing-guard 2.0「Style-only revisions same length or shorter」（≤1.05）的诉求，已被字数判定表 §八「修订净增上限 ≤2%」（v2.12.49 T-5）**等价且更严格**覆盖（2% < 5%）。本批在 §八 补「writing-guard 对照」交叉引用标注，明确「润色类修订同长度或更短」已由净增上限机械约束，**不新增第二判据**（一条款一真源，防两套口径漂移）。

- **④ G 门计数收口（G0-G16 → G0-G17，19 → 20 项）**：G17 入 T7 审计后，G 门总数 19 → 20 项（含 G0.5/G2.5 子项）。audit-checklist-quickref（真源）+ T7 dispatch + 07-审计 + 06-批判 + 09-审稿 + 08-终检 + 00-主控 + 设计文档 + glossary-full/core + skill-entry-appendix + asset-index + deliverables + SKILL.md 同步计数；**顺带修正批次 0 漏改的 README/QUICKSTART「G0-G14 = 17 项」残留**（README 架构图 + G 清单表 + QUICKSTART G 清单表 3 处）。

- **⑤ 机械闭环**：flow-check **规则 44**（G17 数据指纹跨载体一致性）+ **规则 45**（期刊约定校验跨载体一致性）；`test_rules_consistency.py` 新增 `test_G17_data_fingerprint_consistency` + `test_H6_journal_convention_check_consistency`；`test_flow_check_meta.py` DEBT 登记规则 44/45。

- **验收（实测回填 · 最终态）**：自审门 **PASS 36 / FAIL 0**；`python3 -m pytest tests/ -q` → **479 passed**（新增 2 条）；`python3 scripts/flow-check.py` **RC=0**（含新规则 44/45）；`bash scripts/check-version.sh` 通过（v2.12.69）；`python3 scripts/changelog-check.py --check` RC=0。

- **本批范围**：三个写作质量门（G17 + 期刊约定校验 + 润色膨胀指数标注）+ G 门计数收口 + 2 条 flow-check 规则 + 2 条测试 + 记账。**无新增运行能力、无破坏性行为变更**（全部为判据/词表/计数层）。**未 tag、未 push**（发布动作等主人点头）。

---

## [v2.12.68] — 2026-09-21

- **写作质量三门（借 DSH writing-guard，批次 0）**，主人 2026-09-21 指令「依次开始修订」——对 2026-09-21 优化方案「H 类：写作质量守门」首批落地。A-G 七项优化聚焦「工程/治理/性能」，H 类补的恰是论衡作为写作技能**最该强、当前测试零覆盖**的维度——写作质量与学术规范的机械守门。借鉴对象 `github.com/xmutfyh/dsh-plugin-writing-guard`（五层 guard：STYLE/EVIDENCE/JOURNAL/DELIVERY/DOCUMENT），**只借鉴方法论、不引入其 exec 实现**（论衡零 exec 路线不变，全部 LLM 推理判定 + 判据真源 + 反向注入测试落进既有体系）。

- **① H1 · G14-I「防御性写作」检测维度（8 类 → 9 类）**：借 STYLE 层「argument economy」——检测「写手怕被驳 → 堆防御句」的语义级症状（理由前置「为防止X我们采用Y」/ 元话语「值得注意的是」/ 自我辩护「本文并非要证明」/ 过度免责「本研究存在一定局限性」，任一 ≥3 处命中）。G14 原 8 类全是词袋级（模板语/句式/破折号/排比），**无语义级维度**；G14-I 补此空白。真源 = gates/14 §二 + checkers/中文AI痕迹-checker（8→9 类）；13 处派生载体同步（dispatch/agents/模板/设计文档/status/glossary/asset-index 等）；`test_rules_consistency.py` G14_CATEGORIES 加「防御性写作」、断言「8 类判定」→「9 类判定」。

- **② H2 · G15「主张强度校准」（借 EVIDENCE 层「双轴主张模型」）**：对核心论点谓语动词做**双轴强度标记**（因果力 0-5：一致→相关→预示→贡献→影响→强因果；证据力 1-5：推测→相关→支持→直接→确立），修订/润色后**只能平移或变弱、禁止升档**（如「与…相关」→「导致」、或「可能」→「充分证明」= P1）。堵「润色时 correlated→caused 静默变强」的典型副作用。豁免窄口：修订说明记载新增证据支撑 + T7 核验证据真实 → 允许升档但须披露。落点：T7 审计 G 门（**内容语义审计归 G 门，非 M 门形式合规**——优化方案「M-Claim」命名按架构边界修正为 G15，避开 M 门 `==8/==3/==2` 机械静态锁）。

- **③ H3 · G16「上下文泄漏反向反查」（借 DELIVERY 层「Context-to-Artifact Leakage」）**：反向反查四类「写作过程上下文」漏进成品——被否决方案 / 修订过程残留 / 来源 metadata 泄漏 / 防御性 hedge 泄漏，任一命中 = P1。G13 只声明 AI 身份、无反向反查机制，G16 补此空白。触发时机 = T7 审计 + T8 终检（两处覆盖，防 CAL 前漏后漏）。与 G14 风格净化、M-Form-4/5 元数据/过程语言互补。

- **④ G 门计数收口（G0-G14 → G0-G16，17 → 19 项）**：G15/G16 入 T7 审计后，G 门总数 17 → 19 项（含 G0.5/G2.5 子项）。`audit-checklist-quickref.md`（真源）+ T7 dispatch + 07-审计 + 06-批判 + 09-审稿 + 08-终检 + 00-主控 + 设计文档 + glossary-full/core + asset-index + pipeline-overview + skill-entry-appendix + SKILL.md 共 14 文件同步计数（含「G0-G13；G14 已迁出」→「G0-G13 + G15-G16；G14 已迁出」）。

- **⑤ 机械闭环**：flow-check **规则 43**（G15/G16 跨载体一致性，真源 + T7 dispatch 双 token 存在性）；`test_rules_consistency.py` 新增 `test_G15_G16_writing_quality_gates_consistency`（真源 + T7 dispatch 两处齐全，防漂移）。

- **验收（实测回填 · 最终态）**：自审门 PASS 36 / FAIL 0；`python3 -m pytest tests/ -q` → **477 passed**（新增 1 条 G15/G16）；`python3 scripts/flow-check.py` RC=0（含新规则 43）；`python3 scripts/check-version.sh` 通过（v2.12.68）；`python3 scripts/changelog-check.py --check` RC=0。

- **本批范围**：三个写作质量门（G14-I + G15 + G16）+ G 门计数收口 + flow-check 规则 43 + 1 条测试 + 记账。**无新增运行能力、无破坏性行为变更**（全部为判据/词表/计数层）。**未 tag、未 push**（发布动作等主人点头）。

---
