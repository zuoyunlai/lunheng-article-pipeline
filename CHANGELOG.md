# Changelog

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

## [v2.12.67] — 2026-09-21

- **审计第七批整改（P1×3 + P2×5 全量落地）**，主人 2026-09-21 指令「继续修订」——对 2026-09-21 第三方全量审计（对象 v2.12.66，评分 88.5/100；上轮 v2.7.16 = 87/100）问题清单的全量整改。上轮 8 项建议经复核 **8/8 闭环**；本批处理新发现的 P1×3 + P2×5。

- **① P1-1 只读档超长报告分片预申报协议（flow-check 规则 42）**：审计指出「completion 回传 ≤4096 字符、超限**静默截断不报错**」与「T6/T7/T9/G14 报告要求逐项完整」叠加 ⇒ 超长报告回传可能不完整且无截断信号；既有 display-cap 三角（磁盘优先 / `sessions_history` 捞取 / 标记）是**事后**兜底，缺**事前**设计。新增协议（真源 = [`_shared/真源/执行韧化协议-exec.md`](references/_shared/真源/执行韧化协议-exec.md) §6 分片预申报）：**触发线 3500 字符**（4096 减摘要与结构开销的保守线；数值唯一真源在协议本体，规则只锁存在性——防双判据漂移）——前置自查超线 ⇒ final message **首块先交分片清单**（`【报告分片 N/M】` + 每片首行/末行指纹），随后连续输出 M 片（按报告自然结构切：T6 按 C1-C7 / T7 按 G 门 / T9 按 6 维度 / G14 按 8 类，**禁跨段拦腰切**）；主控按清单逐片核对，缺片/指纹不符 ⇒ 走既有 display-cap 捞取（不重跑）；与 display-cap 三角**叠加不互替**（事前 + 事后双层）。接线：T6/T7/T9/G14 四 dispatch + 06/07/09 三角色卡 + G14 checker 话术对齐；**规则 42** 锁协议与四载体的「报告分片 N/M」「分片清单」双 token 存在性（#427「协议从载体静默消失」同族防线）。
- **② P1-2 性能基准四维登记表（`_shared/真源/performance-benchmarks.md` 新建）**：审计指出此前只有耗时一维（9500 字 ~2h 单点），token/成本/引用数三维缺失、重量档无实测。新建唯一登记表：字段 = 字数 / 档位 / 耗时 / token in-out / 成本 / 引用数 / 修订轮数 / 子代理数（口径逐列声明：token 以 completion event Stats line 为**权威值**，禁用会话文本行展示值——教训 #256 口径）；**外推守则（诚实边界）**：重量档（≥8000 字）尚无实测 ⇒ README/QUICKSTART 耗时数字保持「估计值」措辞（不写「经验证」）、不足 3 行不同档位实测**禁止**外推结论；旧单点数据（2026-09-16《个体化命题》）迁入并如实标注三维缺失。README/QUICKSTART 改「估计值」措辞 + 指针到本表；登记进版本戳三载体（sync / check-version / 门 C）+ `_shared` 准入清单（31→32）+ pkg-manifest（84→85）+ asset-index。
- **③ P1-3 flow-check 规则集元健康度门（`tests/test_flow_check_meta.py` 新建，审计「谁测试测试」的机器答案）**：审计指出规则已 43 条但负例覆盖不均、新增速度（v2.12.58-66 新增 9 条）> 负例覆盖速度——负例缺失 = 规则退化成永真时无人知晓（v2.12.65 P0-1「机械门静默放行」同族）。新门四锁：**清单双向对账**（从 flow-check.py 真源 docstring + 内联注释抽取规则号，与 COVERED/DEBT 登记表精确相等——新规则不登记即红、删规则留陈旧登记即红）；**幻影覆盖检测**（COVERED 引用的测试函数必须真实存在——本门首跑即抓到一处笔误引用，当场自证价值）；**豁免闭合**（DEBT 理由 ≥12 字符，allow_empty 同语义）；**覆盖软棘轮**（COVERED ≥ 33 只许涨）+ 抽取器下限护栏（≥40：docstring/注释格式被重构致抽取面缩水时先红，防对账给出误导性报错）。首登 **33 covered / 10 debt**——早期规则 1-5 / 8-11 / 29 的负例缺口从「无声空白」变为「点名登记的债务」。
- **④ P2-4 README「当前版本」块容量门（changelog-check.py 扩）**：审计指出堆叠式 changelog 复述曾把该行写到 >4000 字符（v2.12.66 段即 1200+，且历版累加），可读性崩坏、与 CHANGELOG 职责重叠。新增 `readme_prose_gate()`：行 ≤500 字符（超限即红）+ 缺行即红（与 test_audit_residuals 版本一致性断言互补：那边锁「版本号对」，这边锁「可读性」）；README 当前版本块改写为「摘要 + 指向 CHANGELOG 首节」，v2.12.66 及更早的堆叠段退役（内容仍在 CHANGELOG 对应章节，零信息损失）；配套 4 条测试（正向 / 超限反向 / 缺行反向 / **接线断言**——cmd_check 必须真的调用该函数，防「函数在、没人调」的 #421 式空转）。
- **⑤ P2-5 G14 时点有效性诚实边界**：审计指出「全流程只审一次」（v2.12.40 定案）与「G14 之后 T5 仍可能做最后一次风格层修订」叠加 ⇒ 审后改文的残留风险未披露。gates/14 报告必含字段新增「时点有效性诚实边界」：G14 结论作用于**判定时点的文本**；`t5_style_revision`（Fail 出口 / Warning 主人选 B）之后的文本**不再复检**，属已知残留风险——由 T8 终检披露 + Phase 5 主人验收把关，**不以 G14 结论背书修订后文本**。
- **⑥ P2-1 平台升级冒烟检查（`host-verify-recipe.md` §六新增）**：`SKILL.md` frontmatter `version` 置于 `metadata.openclaw` 下是兼容性 workaround（bundled 校验器拒顶层 `version`，官方文档未记载该子键语义）⇒ OpenClaw 升级可能改变校验/加载行为。新增维护者冒烟三步：quick_validate（路径变了以 `npm root -g` 定位）+ 加载冒烟（版本头/角色卡可读）+ 自审门（含门 T 官方校验段）；发现校验行为变化 ⇒ 按 v2.12.13 方案 3.6 思路重评 frontmatter 结构并记教训。
- **⑦ P2-2 glossary 漂移清理**：§五工具档位列删旧档名 `opt_in`（frontmatter 已无此键——工具级 opt-in 于 v2.12.52 归零，列名漂移 15 版）；§四教训分类「#270-#67」笔误订正为 #276；「教训分类（待实施 P1-2）」标注自 v2.12.59 起 8 版未动 ⇒ 改「示例性归类，非完备索引；完整定位以教训索引为准」——要么实施要么摘标注，不留僵尸标注。
- **⑧ P2-3 心跳归属标识**：三方对账（心跳 / 主控转写 / 磁盘产物）的信任前提 = 心跳文件归属真实。`dispatch-header.md` + `执行韧化协议-exec.md`：心跳文件名的**两位角色号即归属标识**，主控对账时须与该角色**本轮 spawn 记录**匹配——**前缀与角色不符的心跳不采信**（防跨角色/跨项目心跳误配）；零 exec 下不做加密签名（性价比诚实边界，已注明）。
- **⑨ 配套测试 13 条**：规则 42 共 4 条（正向四载体双 token + T6/T9 dispatch 反向注入 + 协议真源本体反向注入）+ 元健康度门 5 条（抽取下限 / 双向对账 / 幻影覆盖 / 豁免闭合 / 软棘轮）+ README 容量门 4 条（正向 / 超限 / 缺行 / 接线）；全部整仓副本注入或纯函数判据、真源 sha256 零写入。
- **验收（实测回填 · 最终态）**：自审门 **PASS 36 / FAIL 0**；`python3 -m pytest tests/ -q` → **476 passed**（新增 13 条）；`python3 scripts/flow-check.py` RC=0（含新规则 42）；`python3 scripts/link-check.py` RC=0；`bash scripts/check-version.sh` 通过（v2.12.67）；`python3 scripts/inject-lang-policy.py --check` 通过；`python3 scripts/changelog-check.py --check` RC=0。
- **changelog 分层轮转（同批收尾）**：主文件加本节后有 **6 期**（上限 5）⇒ 按既定口径把最旧的 **v2.12.62** 逐字迁入 `CHANGELOG-archive.md`，归档标题边界更新为「v2.12.62 及更早」。
- **本批范围**：审计 P1×3 + P2×5 全量落地 + flow-check 规则 42 + 2 个新文件（登记表 / 元健康度门）+ 13 条测试 + 记账。**无新增运行能力、无破坏性行为变更**（全部为协议 / 判据 / 台账层）。**未 tag、未 push**（发布动作等主人点头）。

---

