# Changelog

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

- **① P1-1 只读档超长报告分片预申报协议（flow-check 规则 42）**：审计指出「completion 回传 ≤4096 字符、超限**静默截断不报错**」与「T6/T7/T9/G14 报告要求逐项完整」叠加 ⇒ 超长报告回传可能不完整且无截断信号；既有 display-cap 三角（磁盘优先 / `sessions_history` 捞取 / 标记）是**事后**兜底，缺**事前**设计。新增协议（真源 = [`_shared/执行韧化协议-exec.md`](references/_shared/执行韧化协议-exec.md) §6 分片预申报）：**触发线 3500 字符**（4096 减摘要与结构开销的保守线；数值唯一真源在协议本体，规则只锁存在性——防双判据漂移）——前置自查超线 ⇒ final message **首块先交分片清单**（`【报告分片 N/M】` + 每片首行/末行指纹），随后连续输出 M 片（按报告自然结构切：T6 按 C1-C7 / T7 按 G 门 / T9 按 6 维度 / G14 按 8 类，**禁跨段拦腰切**）；主控按清单逐片核对，缺片/指纹不符 ⇒ 走既有 display-cap 捞取（不重跑）；与 display-cap 三角**叠加不互替**（事前 + 事后双层）。接线：T6/T7/T9/G14 四 dispatch + 06/07/09 三角色卡 + G14 checker 话术对齐；**规则 42** 锁协议与四载体的「报告分片 N/M」「分片清单」双 token 存在性（#427「协议从载体静默消失」同族防线）。
- **② P1-2 性能基准四维登记表（`_shared/performance-benchmarks.md` 新建）**：审计指出此前只有耗时一维（9500 字 ~2h 单点），token/成本/引用数三维缺失、重量档无实测。新建唯一登记表：字段 = 字数 / 档位 / 耗时 / token in-out / 成本 / 引用数 / 修订轮数 / 子代理数（口径逐列声明：token 以 completion event Stats line 为**权威值**，禁用会话文本行展示值——教训 #256 口径）；**外推守则（诚实边界）**：重量档（≥8000 字）尚无实测 ⇒ README/QUICKSTART 耗时数字保持「估计值」措辞（不写「经验证」）、不足 3 行不同档位实测**禁止**外推结论；旧单点数据（2026-09-16《个体化命题》）迁入并如实标注三维缺失。README/QUICKSTART 改「估计值」措辞 + 指针到本表；登记进版本戳三载体（sync / check-version / 门 C）+ `_shared` 准入清单（31→32）+ pkg-manifest（84→85）+ asset-index。
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

## [v2.12.66] — 2026-09-20

- **发版流程缺口修补（升版后正文版本加本地机械门）+ M-13 清单跨载体漂移收口**，主人 2026-09-20 指令「修补发版流程缺口：升版后 README 正文版本漂移目前只能被 CI 抓到，本地 pre-push 无法拦」。本批两条工作提交：`79afe51`（升版后正文版本一致性硬门 + 8 条回归测试）、`7a512a1`（M-13 清单跨载体漂移收口 + flow-check 规则 41 + 4 条回归测试）。

- **① 缺失门本体（v2.12.65 实测复盘）**：`sync-version.sh` 同步 91 个文件、自审门 **PASS 36 / FAIL 0**、打印「版本同步完成」—— 但 `README.md` 正文「当前版本」块仍停在 **v2.12.64**。该判据**按设计不在** `check-version.sh` 覆盖面内（后者只校文件头版本戳 / 安装 pin / 9 角色旧命名）⇒ **本地全绿**；推送后 `论衡算法测试 CI（全量）` 与 `Code Quality` 同时红，同一根因 = `tests/test_audit_residuals.py::test_readme_prose_version_matches_frontmatter`（`AssertionError: README 正文版本 v2.12.64 ≠ frontmatter 2.12.65`）。与教训 #428 属**同一缺陷的第二次复现** ⇒ 证明该教训此前**只靠纪律、无机械门**；与 #430 同族（本地门全绿 ≠ CI 全绿）。
- **② 修法（`79afe51`）：把判据挂到「引入缺陷的那个流程末端」** —— `sync-version.sh` 在非 DRY-RUN 分支、自审门**之后**、`.bak` 清理**之前**触发两条版本真源断言：`::test_readme_prose_version_matches_frontmatter`（README 正文「当前版本」）与 `::test_skill_body_version_header_matches_frontmatter`（SKILL.md 正文版本头）。失败即 `exit 1` ⇒ 既有「**同步成功才清 .bak**」语义自动覆盖本门（失败 = 视同**未同步**，备份保留供回滚）；退出信息点名**文件 + 断言 + 判据真源节点 + 改法**。
- **③ 口径（一条款一真源，刻意不做第二份判据）**：判据**唯一真源 = 上述两条断言**，本门**只负责触发**、不复制正则 ⇒ **不扩** `check-version.sh` 的判据面（扩 = 两套判据必然漂移，正是本仓 P1-1 / P1-2 刚拆掉的那类）。用**显式节点 id** 而非 `-k "version"`：`-k` 是子串过滤器，测试改名/新增会静默改变覆盖范围；显式 id 由 pytest 以「未收集到」直接报红（fail-closed）。工具链缺失（无 `python3` / 无 `pytest`）同样非零退出并明示「**环境错误，非版本不一致**」，不允许静默降级。
- **④ M-13 跨载体漂移收口（`7a512a1`）**：T8 dispatch 与 08-终检 是**同一份**「主人自行操作建议清单」的两个载体，两处内容已漂移且**无任何门**校验。漂移 ①：v2.12.60 把第 2 类由「图件落地与嵌入」瘦回「SVG → PNG 转换」（图位嵌入改由 `final_assembly` 在流水线内完成）时**只改 T8、08 漏改** ⇒ 按 08 字面执行 = 让主人重做流水线已完成的嵌入。漂移 ②：T8 内联「可直接复制的命令模板」与它自己声明的真源 `_shared/format-export.md` §二 **不符**（缺 `.tex` 行、`--reference-doc` 指向 `templates/word-reference.docx` 旧文件、pdf 行缺 `--template / --bibliography / --csl`）⇒ 主人照抄即得**错误产物**。修法：08 对齐 T8 口径 + T8 命令模板回真源 §二（两处逐字节一致），并新增 **flow-check 规则 41**（两载体四类动作齐备 + 两处 pandoc 围栏块彼此相等且与 §二同源 + 禁已作废写法）。
- **⑤ 回归测试（两层，全部整仓副本注入、真源 sha256 前后一致）**：`tests/test_version_prose_gate.py` **8 条** —— 接线（节点清单**从脚本抽取**不复制 + 位置断言「自审门之后 / `.bak` 之前」 + 缺 pytest fail-closed）/ 判据有效（README 正文与 SKILL.md 正文头各一条反向注入必红）/ 端到端（跑**副本的** `sync-version.sh`：注入错版 ⇒ 非零退出 + 点名 + **`.bak` 保留**；一致副本 ⇒ 退出 0 防假阳性；副本自审门换恒过桩，确保红/绿只可能来自本门）。规则 41 **4 条**（跨载体一致性正向 + 08 第 2 类回潮注入 + T8 命令块 `reference-doc` 漂移注入）。
- **⑥ 文档同步**：`references/设计文档-架构.md`「修订后必跑硬门三件套」段声明 `sync-version.sh` 末尾现**内建两道门**，并说明「本门为何住在这里而非 `check-version.sh`」；同段把长期失真的「**69 个**应含版本号的文件」改为**不写死数字的派生口径**（实测已漂到 91）—— 硬编码副本必然腐烂，同型于 v2.12.62「编号去副本」。
- **⑦ 并发链实测记录（诚实边界，教训 #423 再现）**：本批工作期间，同一仓库工作树上**另有并行会话链在飞**（同项目 `spawnedCwd`）：该链先提交 ①②，再提交 ③；本链在升号阶段已写下的**版本戳 / README 正文 / CHANGELOG 章节**被该链回收工作树时清除。收口后本链**重做记账 + 先跑发版前置闸（在飞链 = 0，已确认对方 `done`）** 才发版 —— 即既有纪律在真实并发下**正常工作**，也再次证实「先 bump 后检查」的顺序风险（#423）。
- **⑧ 验收（实测回填 · 最终态）**：对**故意错版**的 README 正文跑 `bash scripts/sync-version.sh` → **RC=1**，输出点名 `README 正文版本 v2.12.64 ≠ frontmatter 2.12.65` + 断言行 + 判据真源节点，且 `references/_shared/phase-order.yaml.bak.*` **未被清理**；真源仓 `README.md` / `SKILL.md` / `scripts/sync-version.sh` sha256 前后不变。自审门 **PASS 36 / FAIL 0**；`bash scripts/check-version.sh` 通过（v2.12.66）；`python3 scripts/flow-check.py` **RC=0**（含新规则 41）；`python3 scripts/changelog-check.py --check` RC=0；`python3 -m pytest tests/ -q` → **463 passed**（含本批新增 12 条）。
- **⑨ changelog 分层轮转（同批收尾）**：主文件加本节后有 **6 期**（上限 5）⇒ 把最旧的 **v2.12.61** 逐字迁入 `CHANGELOG-archive.md` 尾部（与上一轮 v2.12.60 的落位一致），归档标题边界更新为「v2.12.61 及更早」。
- **本批范围**：一条本地机械门 + 一组 M-13 跨载体收口（含一条 flow-check 规则）+ 12 条回归测试 + 两处文档同步 + 记账。**无新增运行能力、无破坏性行为变更**（不改任何论衡运行时口径）。

---

## [v2.12.65] — 2026-09-20

- **审计第六批整改 — 三条独立审计链交叉收口（P0×1 + P1×6 + P2×3）**，主人 2026-09-20 指令「发版」。本批五条提交：`342a7f3`（P0-1/P1-1/P1-2 交叉收口）、`eeb5e29`（P1-3 快照抬号）、`a4a9c62`（P1-4/P1-5）、`aa0c8bf`（P2-3）、`caad3f0`（P2-2）。
- **审计主体与交叉验证**：对 v2.12.64 开展独立全量审计，合并**主审计 / 子代理只读审计 / 另一台 ECS 审计**三链结果。主链与子代理链在 P0-1（T2.5 判据字段无生产方）与 P1-1（轻量档口径不一致）上**逐条吻合**；ECS 链基于**发布净化包（84 文件）**而非 git 真源（170 文件），行数统计多处失真，**三条 P0 经核实全属设计取舍误判**，仅三条 P2 属实并纳入清单。

- **① P0-1 · T2.5 完整性门判据输入补生产方（致命：机械门可静默放行）**：`M-Integrity-1` 要求读任务简报「研究问题」段各子问题的「**需找数据点 ≥N**」累加为需求量，但**任务简报模板从不提供该字段** ⇒ 需求量恒 0 ⇒ `data_count >= 0` **恒真** ⇒ 「通过才派 T4」的阻断语义对数据量维度**失效**（退化为只查数据卡文件存在）。四点修复：① `任务简报-template.md` 补 `需找数据点 ≥N` 必填行；② `phase-order.yaml` 的 `m_gate_criterion_fields` 登记 producer + producer_marker；③ `M-Gate-Algorithm.md` 伪代码把 `outline_count == None/0` 显式改为 `verdict_undecidable`（禁 `>=0` 放行）；④ `flow-check` 新增**规则 35**：每个 `requires` 字段必须有生产方登记（复用 R-4 marker 断言写法）。
- **② P1-1 · 轻量档跳过集合三处口径不一致**：模板声称轻量档跳过 **T6/T7/T9**，而真源（`字数判定表` / `phase-order.yaml`）**仅要求跳 T6** —— T7/T9 正常执行、G14 走 selfcheck ⇒ 按模板字面执行会**少做两项质量门**。收口为 `phase-order.yaml` 唯一真源，模板改「T6 必跳 / T4 可省」；新增**规则 36** 防回潮 + 反向注入测试。
- **③ P1-2 · 路径边界口径四处不一致（旧单域残留）**：v2.12.64 已在 `permissions.md` 定案「两域」口径（skill 资产域只读 / 项目数据域读写，违规以**写**为准），但 `SKILL.md`、`关键协议.md`、`dispatch-header.md` 三处**仍保留旧单域口径** —— 按旧口径字面遵守会导致**流水线不可执行**（把设计意图内的 `read` 也判越界）。三处指针化到 `permissions.md` 真源；新增**规则 37** 防回潮 + 反向注入测试。
- **④ P1-3 · 门 H 快照抬号**：`lessons-max.snapshot` 430 → **437**。`#431`–`#437` 七条经逐条裁定**全部属论衡类**（论衡流程 / 构建 / 发版），排除表未变，门 H 告警清零。
- **⑤ P1-4 · 安全扫描误报面收敛**：通用扫描器（`skill-auditor-plus/security_audit.py`）**无豁免机制**，误报只能每轮人工排查。新增 `.safe-pattern-manifest.json` 登记 4 类**已逐条核实**的误报（`regex-engine-call` 正则引擎调用 / `defensive-test-sample` 防御性测试样本 / `guarded-cleanup` 受护栏保护的清理 / `internal-variable-exec` 内部字面量动态执行），每条带 file + reason + lines + note；`flow-check` 新增**规则 38** 校验清单完整性（JSON 可解析 / 四字段齐备 / file 真实存在 / **行号端点不越界**）—— 防「登记一行就走、文件改名或行号漂移后成假账」。
- **⑥ P1-5 · 审计类子代理回传可回收性**：审计/长报告类子代理只走 completion 回传会 `result_truncated` **且不报错**；若 `cleanup=delete` 则正文**不可回收**（本轮实测 P1-2～P1-6 正文永久丢失，事后靠重跑补）。`dispatch-header.md` 的回传硬上限约定补三条回收纪律：`cleanup=keep` / **先落盘再回报路径+摘要** / 见到截断先回收全文再判断补跑。
- **⑦ P2-1 · sessionKey 口径合并**：`status-template.md` 头部第 7 行**同时存在两代口径**（「截断前 8 字符」v2.12.41 与「一律不记录」v2.12.42），而正文 §4.7 明确「不记录」—— 头部告警块未随 v2.12.42 收紧回改，新读者无法判断到底截断还是不记录。收口为「**一律不记录**，截断规则仅兜底」。
- **⑧ P2-3 · 维护者脚本危险操作统一审计点**：`rm -rf` / `bash -c` 分散在多个维护者脚本、**无统一审计点**，新增一处危险操作时无人察觉。收敛为单点：`.safe-pattern-manifest.json` 新增 `maintainer_danger_ops`（`patterns` 为扫描口径**唯一真源** + 6 文件逐项登记 ops/guard）；`flow-check` 新增**规则 39** 做**双向对账** —— 漏登记（新脚本加 `rm -rf` 未登记）与陈旧登记（构造已移除未销账）**都报红**；扫描口径刻意与通用扫描器一致（同样跳过 `#` / `-` / `**` / 围栏 / 三引号行），两端不漏不重。登记 6 文件：`build-clawhub-release.sh`（输出路径逃逸防护，校验位于 `rm -rf` **之前**）、`cleanup-skill-store.sh`、`release-preflight.sh`（`rm -rf` 只作用于 `mktemp`；`bash -c` 变量源为脚本内固定字面量）、`self-audit-gate.sh`、`strip-shell-commands.py`（危险模式**定义**非执行路径）、`test-path-canonical.sh`。
- **⑨ P2-2 · 跨状态机「静默 ≠ 有效决策」不变式机械化**：审计原判「四个状态机分散、无聚合视图」经核实**不成立**（`verdict_scale` / `owner_timeout_policy` / `provider_silence_escalation` / `terminal_freeze` 本就相邻排在同一文件 `phase-order.yaml`，96 行连续块且头部注释已做交叉索引）—— 新建独立文档会制造第二份副本，**违反一条款一真源**（正是 P1-1 / P1-2 刚拆掉的那类漂移）。但核实出**真缺口**：`owner_timeout_policy`（主人无应答）与 `provider_silence_escalation`（同 provider 连续静默）共享同一不变式（静默/无应答 ≠ 有效决策 ⇒ 挂起等主人 + 无默认继续），而该「同侧」关系**只写在注释散文里**，任一侧被改成自动继续另一侧不会报红。故新增顶层 `silence_doctrine` 单一真源（`invariant` / `halt_kinds` 挂起类处置唯一枚举 / `forbidden_kinds` fail-open 枚举 / `applies_to` 覆盖面）+ `flow-check` **规则 40** 做双侧投影 + 双向对账（两侧挂起态必须相等）。**独有闭合面**：规则 12 只查 `default_fallback ∈ fallback_kinds`，故**新增一个 fail-open 处置**时规则 12/31 都不拦 —— 只有规则 40 能拦，已配专门注入测试证明其为唯一拦截者。

- **⑩ 验收（实测回填 · 最终态）**：自审门 **PASS 36 / FAIL 0**；`python3 -m pytest tests/ -q` → **452 passed**；`python3 scripts/flow-check.py` **RC=0**；`bash scripts/check-version.sh` 通过；`release-preflight.sh` **四查全过**（在飞链 0 / 编号未占用 / 工作区干净 / CI 不红）。新增机械门六条（35–40）**每条均配反向注入测试**（真源 sha256 前后不变 + 副本变异 + 断言报红）。
- **⑪ 门 Y 棘轮备案**：`phase-order.yaml` 54651 → **55272** B（+621）。按 `test_bulk_ratchet` 的「扩容说明」要求在 `self-audit-gate.sh` 内备案 —— 该段是**真源内容**（`silence_doctrine` 挂起类处置唯一枚举）非注释膨胀，且已把头部 ⑬ 对 S-3 的冗余复述压缩为指针（净增已扣减）。
- **⑫ changelog 分层轮转（同批收尾）**：主文件加本节后有 **6 期**（上限 5）⇒ 按既定口径把最旧的 **v2.12.60** 逐字迁入 `CHANGELOG-archive.md`，归档标题边界更新为「v2.12.60 及更早」。

---

## [v2.12.64] — 2026-09-19

- **审计第五批整改 + CI 判据统一 + 发布链工具残留止血**，主人 2026-09-19 指令「版本号 bump 发布」。本批三条提交：`c86bb8f`（第五批整改本体，30 文件 +1318/-60）、`227cf15`（门 Y 棘轮联动）、`d31e23e`（工具残留排除，推送后 CI 实测回归）。

- **① 构建链根因治理（C-1 推广 / C-3 / C-4 / C-5 / C-6 / C-7，`build-clawhub-release.sh` +418 行）**：v2.12.63 只把 `references/_shared/` 改成白名单准入，并**诚实登记**了「`agents/` `templates/` `gates/` `checkers/` `dispatch/` 仍是默认入包」这一同族残余债务。本批把它做完：
  - **C-1 推广（P0 同源）· 新增 §2b″「随包文件清单门」**：包内文件集必须与 `scripts/.pkg-manifest.txt`（**84 条**）**精确集合相等**，不等即 `exit 1`，并用 `comm -13/-23` **双向**打印差异（`+` 未登记入包 / `-` 已登记缺失）。作用面从 `_shared/` 扩到**全包** —— 「新文件默认入包」→「**新文件默认被拦**」的方向反转彻底完成。清单另加**「清单自身不得进包」**显式断言（防清单随包出厂 = 自曝维护面）。
  - **C-4 · 死链中和改程序化**：包内对被排除文档的引用原由 `purify()` **逐条硬编码 sed** 中和 ⇒ 新增一个被排除文件就漏一次（规则与排除清单两处必然漂移）。现改为 `PKG_EXCLUDED_DOC_PATHS`（**14 条为唯一真源**）→ 由 python 从该清单**推导**正则，覆盖「括注内引用 / 反引号 mention / 链接目标」三种形态并跳过代码围栏；随后**同规则 fail-closed 反向断言**，残留即 `exit 1` 并点名文件 + token。（C-4 的实测依据：真实产物 `pipeline-readme.md` 内确有 `见 \`templates/README-模板拆分方案.md\` §四` 这类死链，而旧规则 3h-4 只认「详见 …。」一种字面，故长期漏网。）
  - **C-5 · 非 md 文本资产纳入正向完整性门**：`yaml/yml/json/txt/toml` 纳入快照与校验（存在性 / 非空 / 保留率 ≥35%）。原先正向门**只覆盖 `*.md`** ⇒ 非 md 资产被整篇删空无人报错（负向扫描只报「违规命中数 ≠ 0」）。
  - **C-6 · 基线字符下限守卫**：正向门按**字符保留率**判，分母异常小或为零时比率可恒过（0→0、10→10 都算 100%）⇒ 新增 `PKG_MIN_BASELINE_CHARS`（默认 50），基线 `chars == 0` 或低于下限即 fail，不再去算比率 —— 治「分母退化 ⇒ 门退化为恒真」。
  - **C-3 / C-7 · 规则自检全量覆盖 + 豁免理由双向闭合**：剥离规则自检由部分覆盖扩到 **14 条全量**（44 条规则：生效 27 / `allow_empty` 17）+ §3n 就地 pin 正向不变量块；新增 `RULE_EMPTY_REASONS`（28 条）与最小理由长度 **12 字符**，**双向闭合**校验（每个 `yes` 条目必有理由且长度达标 / 理由表不得有孤儿），根治「`allow_empty=yes` 是唯一逃生口，理由字段可空 ⇒ 标注一下即可关掉真源侧守卫」这条衰减路径。
  - **单测**：新增 `tests/test_build_gate_hardening.py`（**11 条**，全部临时整仓副本注入 / 真源零写入）；`test_release_script_guards.py` +164 行（含 3 条真实构建负向注入）；既有 e2e 增「包 ≡ 清单」「无死链」两断言。四条新门（随包清单门 / 基线下限门 / 非 md 正向门 / 豁免理由门）均经**负向注入**确认必红。

- **② 文档一致性 / 权限口径（19 份 `references` + README + `scripts/README`）**：
  - **零 exec 语义收口（S-1/S-4）**：08-终检 / T8-终检 / `M-Gate-Algorithm` / `host-verify-recipe` / `deliverables` / `status-template` 统一口径 —— **sha256 与精确 bytes 属主人侧量值**，agent **不计算、不声称复算**；未回填记 `unavailable` ⇒ `pending_owner_verification`，**明文禁止判通过**。（原口径下「agent 复算 sha256」与零 exec 硬边界自相矛盾。）
  - **路径两域拆分（S-2）**：`permissions.md` 显式拆「skill 资产域（只读）」/「项目数据域（读写）」，判据由「`read` 是否越界」改为「**项目数据域外写入 0 命中**」—— 原判据把 `read` 纳入越界口径，与「读技能资产是设计意图」直接冲突。
  - **字数阈值真源收口（V-7）**：`任务简报-template` 不再复述阈值，改指向字数判定表（原模板写 `≤1% / 1-5% / >5%` 与真源 `5% / 10%` **两套并存** ⇒ 同稿分级互斥、必然冲突）。
  - **图件判据同行互斥修正**：08-终检改「**= Phase 2.5 拍板 N 张**」（与 M-11 严格相等口径一致，废除「≥5」）。
  - `lessons-max.snapshot` **429 → 430**（棘轮跟上主真源续录）。

- **③ CI 判据统一 + 发版闸查 ④**：
  - `tests/requirements-test.txt` 补 **pyyaml**（根因：测试依赖未自声明 ⇒ 子集安装面必断）。
  - `.github/workflows/ci-test.yml`：改**两份 requirements 全装 + 跑全量**（与本地同口径）。
  - `scripts/release-preflight.sh` 新增**查 ④「待发布提交 CI 不红」**（退出码 13；`--allow-red-ci` 为显式逃生口；不可判定时只警告不阻塞）。**背景（教训 #430）**：v2.12.62 发版后发现 `ci-test.yml` **连续 30 次失败、跨 3 天、覆盖 10+ 个版本**，而本地门全绿、发版照走 —— 根因是「同一份代码在另一个 workflow 下是绿的」造成**绿灯幻觉**，红的那条没人点开。本查把「脚下的提交 CI 是否红」搬进发版闸。`Makefile` 由「两查一停」改「**四查一停**」。
  - 新增 `tests/test_ci_config.py`（5 条机械锁）+ `test_release_preflight.py` 补 4 条。

- **④ 发布链工具残留止血（`d31e23e`，推送后 CI 实测回归）**：`c86bb8f` 推送后 **Code Quality 变红**，报错来自本批新加的 §2b″ 清单门，多出 `+ .coverage.<host>.<pid>.<随机>`。
  - **根因**：Code Quality 以 `pytest --cov=scripts` 跑全量 ⇒ coverage **并行模式**在每个 python 子进程退出时向其 cwd（**仓库根**）写 `.coverage.<host>.<pid>.<随机>` ⇒ 构建的 `rsync -a` 全量复制把它们带进包。排除清单是**黑名单式**，已有 `.pytest_cache` / `__pycache__` / `*.pyc`，**唯独漏了 `.coverage*`**。本地不跑 `--cov` ⇒ 从未复现 ⇒「**本地绿 / CI 红**」（#430 同族）。
  - **关键判断：门没错**。§2b″ 拦的确实是包内不该有的文件（coverage 数据含维护者脚本路径，属**真**泄漏）。第一反应若是「把门放宽」，就等于把刚建立的白名单准入重新变成漏勺。故修的是**排除清单**：rsync 侧与 cp 分支**两侧对称**新增 `.coverage` / `.coverage.*` / `htmlcov` / `.mypy_cache` / `.ruff_cache` / `.DS_Store` / `*.swp` / `*.swo`（`cp` 是 rsync 缺失时的罕见路径 ⇒ 单侧补漏更难在真实使用中暴露）。
  - **新增 2 条回归测试**：`test_tool_residue_is_excluded_in_both_copy_branches`（两侧对称的**源侧不变量**）+ `test_build_survives_and_drops_tool_residue`（**故障注入**：仓库根铺满 `.coverage*` / `.DS_Store` / `*.swp` / `htmlcov` ⇒ 构建必须成功**且**残留不得入包 —— 即该次 CI 回归的复现）。

- **⑤ 门 Y 棘轮联动（`227cf15`）**：`references/agents/00-主控-扩展职责.md` 卡体量下调后，`scripts/self-audit-gate.sh` 的门 Y 上限表同步 **73690 → 73689**。两者**必须同批提交**，否则提交态 `test_bulk_ratchet` 必红（`c86bb8f` 已显式登记该约束）。

- **⑥ 验收（实测回填 · 最终态）**：自审门 **PASS 36 / FAIL 0**；`python3 -m pytest tests/ -q` → **436 passed**；`bash scripts/check-version.sh` 通过（**v2.12.64，87 处版本戳**）；`release-preflight.sh` **四查全过**（在飞链 0 / 编号未占用 / 工作区干净 / CI 不红）；隔离 `OUTPUTS_ROOT` 构建 **RC=0**，包内 **84 文件 ≡ 随包清单**、14 条排除路径**死链 0 命中**。
  - **CI 最终态（`d31e23e`）**：`论衡算法测试 CI（全量）` ✅ success、`Code Quality` ✅ success。**其中「论衡算法测试 CI」此前自 v2.12.62 起长期红着**（`29ac87c` / `a4a9060` 均为 failure）—— 本批 ③ 的 CI 判据统一（补 pyyaml + 跑全量）使其**转绿**，「红着没人看」的绿灯幻觉到此结束。

- **⑦ changelog 分层轮转（同批收尾）**：主文件加本节后有 **6 期**（上限 5）⇒ 按既定口径把最旧的 **v2.12.59** 逐字迁入 `CHANGELOG-archive.md`，归档标题边界更新为「v2.12.59 及更早」。

- **本批范围**：六类构建链缺陷（C-1 推广 / C-3 / C-4 / C-5 / C-6 / C-7）+ 五项文档一致性 + CI 判据统一与发版闸查 ④ + 一次 CI 实测回归止血 + 13 条新单测。**无新增运行能力、无破坏性行为变更。**

---
