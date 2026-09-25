# 论衡 Code Wiki — 代码级深度篇

> **定位**：本文档是 [CODE_WIKI.md](CODE_WIKI.md) 的代码级深度补充，所有细节均基于实际读取的源码/真源文档，不凭惯例臆写。
> **版本**：v2.13.3（2026-09-25）

---

## 目录

1. [phase-order.yaml 真源结构详解](#一phase-orderyaml-真源结构详解)
2. [flow-check.py 42 条规则逐条说明](#二flow-checkpy-42-条规则逐条说明)
3. [paper-ready-check.py 可发表性 48 项检查器](#三paper-ready-checkpy-可发表性-48-项检查器)
4. [G14 中文 AI 痕迹闸 9 类检测维度](#四g14-中文-ai-痕迹闸-9-类检测维度)
5. [T7 审计员执行细节](#五t7-审计员执行细节)
6. [T5 写手执行细节](#六t5-写手执行细节)
7. [M 门算法信任模型与判定协议](#七m-门算法信任模型与判定协议)
8. [E1 证据对象模型](#八e1-证据对象模型)
9. [主控执行韧化协议](#九主控执行韧化协议)
10. [24 节点流水线全景表](#十24-节点流水线全景表)

---

## 一、phase-order.yaml 真源结构详解

文件路径：`references/_shared/真源/phase-order.yaml`

### 1.1 顶层结构

```yaml
version: 2.13.3                    # 版本号（随 SKILL.md 同步）
verdict_scale:                     # 判定结果四档定义（规则 10 校验）
  four_tier:
    tiers: [pass, fail, undecidable, path_or_param_error]  # 必须恰好 4 档
    default_handling:              # 四档全覆盖，禁 fail-open
      pass: continue_to_next
      fail: halt_then_revision_outlet
      undecidable: halt_pending_evidence_or_owner_ruling
      path_or_param_error: halt_fix_inputs_then_rerun_same_node
silence_doctrine:                  # 跨状态机共享不变式（规则 40）
  invariant: silence_is_not_valid_decision
  halt_kinds: [pending_owner_halt]
  forbidden_kinds: [auto_continue, silent_proceed, degrade_and_continue]
owner_timeout_policy:              # 人在环无应答处置唯一真源（规则 12）
  no_answer_minutes: 60
  fallback_kinds: {pending_owner_halt: ...}
  default_fallback: pending_owner_halt
provider_silence_escalation:       # 同 provider 连续静默升级（规则 31）
  threshold: 3
  scope: same_provider
  no_default_option: true
  halt_pending_owner: true
  owner_choices: [switch_provider_family, switch_capability_tier, accept_same_source_with_disclosure]
terminal_freeze: ...               # 终态冻结真源（规则 13）
panorama_sources:                  # 全景唯一派生视图（规则 24）
  canary: references/_shared/真源/pipeline-overview.md
  mirrors: [SKILL.md, README.md, ...]
pipeline: [...]                    # 节点列表（24 节点）
```

### 1.2 节点字段约束（由 flow-check.py 机械校验）

| 字段 | 约束 | 对应规则 |
|------|------|----------|
| `id` | 全局唯一，被 `next`/`after_trigger`/`on_fail` 引用时必须存在 | 规则 1 |
| `kind` | 必填，∈ {owner_checkpoint, mode_declaration, parallel_agents, conditional_review_window, mechanical_checkpoint, agent, conditional_agent, bounded_loop, owner_agent, advisory_agent} | 规则 32 |
| `phase` + `phase_seq` | 必填；seq 全局唯一且与顶层 `phase_order` 一致；沿前向边不得回退 | 规则 11 |
| `input` | 入参类节点（INPUT_KINDS）必填 | 规则 4 |
| `output` | 执行类节点（EXEC_KINDS）必填 | 规则 5 |
| `condition` | 若声明则必须有 `on_not_triggered`/`degrade`/`decisions` 其一 | 规则 8 |
| `verdict_scale` | 引用的档位名必须在顶层有同名定义 | 规则 10 |
| `write_authority` | T6/T7/T9/G14 只读档角色必须为 `owner` | 规则 23 |
| `blocking`/`owner_visible`/`decisions`/`timeout_fallback` | owner_checkpoint 节点必填 | 规则 12 |
| `independence` | blind_review 节点不得声明 `on_worker_failure.executor: 主控` | 规则 30 |

### 1.3 入参链闭合（规则 6）

- 每个被消费的受管路径都必须有节点以 `output` 生产
- 取消了「≥2 消费者」前提——单消费者路径同样逃检
- 目录型产出（如 `final/图件/`）覆盖其下通配消费（前缀匹配）

---

## 二、flow-check.py 42 条规则逐条说明

文件路径：`scripts/flow-check.py`

核心机制：
- `UniqueKeyLoader`：YAML 重复键硬失败（后键静默覆盖前键 = 真源失真）
- `_paths(decl)`：从声明中抽出归一路径集合
- `_norm(tok)`：版本占位归一（`初稿-v{N}.md` → `初稿-v#.md`）

| 规则号 | 名称 | 校验内容 |
|--------|------|----------|
| 1 | 引用有效性 | `next`/`after_trigger`/`on_fail`/`on_not_triggered` 指向已知节点或 `rerun_*`/`record_*` 动作 |
| 2 | 可达性 | 无孤立节点；`on_fail` 出口边计入可达性 |
| 3 | next 必填 | 除终态 `phase5_acceptance` 外须有 `next` |
| 4 | input 必填 | 入参类节点须声明 `input` |
| 5 | output 必填 | 执行类节点须声明 `output` |
| 6 | 入参链闭合 | 每个被消费的受管路径都必须有生产者 |
| 7 | YAML 重复键 | 重复键硬失败（UniqueKeyLoader） |
| 8 | 条件未触发处置 | 有 `condition` 的节点须声明 `on_not_triggered`/`degrade`/`decisions` |
| 9 | current_draft_sync 必经 | 初稿生产者到 `t7_audit` 的路径必须经过 `current_draft_sync` |
| 10 | verdict_scale 接线 | 节点引用的档位名必须在顶层有同名定义，且 4 档 + default_handling 全覆盖 |
| 11 | Phase 编号 | 每节点须声明 `phase`+`phase_seq`；seq 全局唯一；沿前向边不得回退 |
| 12 | 人环闸门声明 | `owner_checkpoints` 与 kind=owner_checkpoint 节点集双向一致；须 blocking+owner_visible+decisions+timeout_fallback |
| 13 | 终态冻结 | `phase5_acceptance` 须声明 terminal；accepted 后修改须重跑 G14 |
| 14 | 交付物指纹 | `fingerprint: required` 节点须有 output；final_assembly 与 t8_technical_final 须同步声明 |
| 15 | 审计对象一致 | t7_5_integrity/t8_technical_final/t9_review 须声明 audited_artifact_required |
| 16 | 计数档位 + P2 锚点 | M-Gate-Algorithm.md 与 字数判定表.md 须同时声明 v2.12.49 新段 |
| 17 | 轮次耗尽出口 | audit_revision 须声明 rounds_exhausted_outlet（三选一 + no_default + halt_pending_owner） |
| 18 | G14 严重度 | 14-中文AI痕迹-gate.md 须含 severe_single_class + max(类数档, 单类严重度档) |
| 19 | 48 必查严重度列 | 可发表性判定表 §二 A-E 每行须含严重度字段（≥17 处） |
| 20 | 图件路径与决策 | phase4_4_figures.output = `final/图件/*.svg`；status + checkpoint-card 须含 figures/figure_decision |
| 20b | 图件嵌入锁 | deliverables.md + 08-终检 + T8 dispatch 须含嵌入式图位规范 + 嵌入计数 |
| 21 | 主人操作清单 + 字数口径 | T8 dispatch 须含「主人自行操作建议清单」；任务简报须含 body_limit |
| 22 | T 系列锁 | 关键协议/交接报告/模型候选池/审稿报告模板/字数判定表等须含对应字段 |
| 23 | 只读档写权 | T6/T7/T9/G14 节点 write_authority 必须为 owner |
| 24 | 全景一致性 | 全景收敛为唯一派生视图（pipeline-overview.md），其余文档只留指针 |
| 25 | 条件字段生产方 | condition_definitions 每条须登记 producer + producer_marker |
| 26 | 条件不可判定处置 | 有 condition/opt_out 的节点须声明 condition_undecidable ∈ {report_to_owner, halt_pending_owner} |
| 27 | status 记账 | status-template 须含 R-2 节点 id 合法性 + R-3 Done 记账一致性 |
| 28 | T8 建议清单四类 | T8 dispatch + 08-终检 须含文档格式转换/SVG/PNG/封面视觉/SHA256 |
| 29 | 进度卡映射 + 失效指针 | checkpoint-card 须含 13 步↔23 节点映射；QUICKSTART 须含 pipeline-overview 指针 |
| 30 | 盲审禁主控代笔 | blind_review 节点不得声明通用 fallback；须 independence_failure_policy（executor_takeover: forbidden + retry_limit 正整数） |
| 31 | 同 provider 静默升级 | provider_silence_escalation 须 threshold=3 + scope=same_provider + 三选一 + 挂起 |
| 32 | kind 必填 | kind 是分派键，缺失使节点对检查隐身 |
| 33 | 人环决策词表同源 | status-template decision 字面值 ⊆ 对应节点 decisions；checkpoint-card 须带枚举真源指针 |
| 34 | spawn 落地验证三点接线 | 执行韧化协议 + 主控卡指针 + status-template spawn_landing 留痕 |
| 35 | M 门判据字段生产方 | m_gate_criterion_fields 每条须登记 producer + producer_marker |
| 36 | 轻量档跳过集合 | skip_in_lite_tier 节点集须 == {t6_critique} |
| 37 | 路径边界两域口径 | SKILL.md/关键协议/dispatch-header 不得含旧单域措辞 |
| 38 | 安全误报白名单 | .safe-pattern-manifest.json 须可解析，每条豁免须 file/reason/lines/note |
| 39 | 维护者危险操作统一审计点 | — |
| 40 | 静默≠有效决策双侧对账 | owner_timeout_policy 与 provider_silence_escalation 挂起态必须相等 |
| 41 | M-13 清单跨载体一致性 | T8 dispatch 与 08-终检 的主人操作建议清单四类动作名齐备且命令模板相等 |
| 42 | 只读档报告分片预申报 | 执行韧化协议 + T6/T7/T9/G14 dispatch 须含「分片清单」与「报告分片 N/M」口径 |

---

## 三、paper-ready-check.py 可发表性 48 项检查器

文件路径：`scripts/paper-ready-check.py`

### 3.1 设计背景（教训 #252）

把内容质量门从 SKILL.md 散文层迁回机器可执行层。本脚本是 `references/_shared/真源/可发表性判定表.md` 的本地开发者版执行器。ClawHub 净化版无此脚本，使用者侧靠 LLM 推理 + 判定表口诀执行同一份规则。

### 3.2 10 组检查函数

| 组 | 检查项 | 函数 | 判定逻辑 |
|----|--------|------|----------|
| 维度1 头部洁净 | F1-F5 | `check_head_clean(final_md)` | 头部 10 行禁含版本号/修订轮/工程术语/过程路径/过程卡引用 |
| 维度2 前置要素 | F6-F10 | `check_front_matter(final_md)` | 须含作者/摘要/关键词/研究周期/研究方法 |
| 维度3 AI 使用声明 | F11-F15 | `check_ai_declaration(final_md)` | 须含 AI 使用声明段 + 五阶段(检索/分析/写作/批判/审计/终检) + 模型选择 + 人类决策 + 不隐瞒声明 |
| 维度4.3 国标引用·顺序编码 | F16-F19 | `check_citation_ordering(final_md)` | 正文 [Lxx]/[Dxx]/[Cxx]/[先xx] 与附录引用集合须完全一致（无遗漏、无未用） |
| 维度4.2 国标引用·类型标识 | F20-F22 | `check_gbt_types(final_md)` | 须含 ≥5 种 GB/T 7714 文献类型标识（M/J/C/S/D/R/P/Z/N/EB/OL） |
| 维度5 图表 | F23-F27 | `check_figures(final_md, project_dir)` | mmd 文件 ≥5 + 正文引用 ≥5 + 非尾部集中 + 数据来源标注 + 图号序列一致 |
| 维度6 致谢+先行者 | F28-F31 | `check_acknowledgment(final_md)` | 须含致谢段(资助/基金/数据来源) + 先行者文献段 + 本文差异化声明 |
| 组A 编号残留清零 | A1-A4 | `check_residual_codes(final_md)` | 正文禁含 T 编号/工程术语/过程稿路径/断言编号/角色名/流程术语/流程配额/自评结论/虚假致谢/内部卡编号 |
| 组C 正文字数 | C1-C4 | `check_word_count(final_md, project_dir)` | 纯中文字符数（截去文末附录），仅统计不判定 |
| 组D M 门 | D1 | `check_m_gate(project_dir)` | final/M-Gate-Report-v2.2.12.json 的 exit_code == 0 |

### 3.3 关键实现细节

- **字数口径**：`re.findall(r'[\u4e00-\u9fff]', body)` — 纯中文字符，截去 `## 参考文献|数据来源|案例来源|先行者文献|AI 使用声明|致谢` 之后的附录
- **引用顺序编码**：正文引用去重保序后，与附录引用集合做双向差集（missing_in_appendix + unused_in_body 均须为空）
- **残留清零**：在正文（不含附录）中 grep 10 类工程残留模式
- **图件序列**：正文 `[图 N]` 编号集合须与 `final/figures/*.mmd` 文件名编号集合完全相等
- **退出码**：0 = 全 PASS / 1 = 有 FAIL / 2 = 参数错误

---

## 四、G14 中文 AI 痕迹闸 9 类检测维度

文件路径：`references/gates/14-中文AI痕迹-gate.md`

### 4.1 检测维度

| 类别 | 检测点 | 阈值 |
|------|--------|------|
| **G14-A 学术模板语** | 「综上所述/笔者认为/本文认为/值得关注的是/不容忽视/在新时代背景下/具有重要的理论与现实意义」 | 任一模板 ≥3 次 |
| **G14-B 句式同质化** | 连续 3 段同句式起头（「首先...其次...最后」「不仅...而且」） | 同模板 ≥2 次连续段 |
| **G14-C 学术套话高频** | 「赋能/抓手/底层逻辑/范式/迭代/路径」每段 ≥1 次 | 全文 ≥5 处 |
| **G14-D 破折号滥用** | 全文 >8 处，或每段 ≥2 处且 ≥5 段，或破折号总字数占比 >3% | 全文 ≥5 段 |
| **G14-E 三项排比** | 全文 ≥3 处「A/B/C」式排比 | 全文 ≥3 处 |
| **G14-F 人称错位** | 学术论文滥用第一人称「我」 | 「我」字频 >1% |
| **G14-G 个人辨识度缺失** | 本文与 10 篇同主题论文风格相似度 >80% | LLM 自评判定 |
| **G14-H 党报话语堆砌** | 「重要讲话精神/重要指示/根本遵循」过多 | 全文 ≥3 处 |
| **G14-I 防御性写作** | 理由前置/元话语/自我辩护/过度免责 | 任一模式 ≥3 处 |

### 4.2 双轨判定（v2.12.49 M-4）

**取 `max(类数档判定, 单类严重度档判定)`，二者取严**：

| 类数档 | 单类严重度档 | 判定 |
|--------|-------------|------|
| 0-2 类 | 任一类 < 3x 阈值 | ✅ Pass |
| 3-4 类 | 任一类 ≥ 3x 阈值 | ⚠️ Warning（不自动修订，主控呈报 3 选 1） |
| 5+ 类 | 任一类 ≥ 5x 阈值 | ❌ Fail（触发 t5_style_revision） |

**反面实例**：超阈 11.5 倍但类数 0 → 旧口径判 Pass；新口径 = max(Pass, Fail) = Fail。

### 4.3 报告头必填字段

```yaml
g14_report_header:
  hit_class_count: <N>
  hit_class_names: [G14-A, ...]
  severe_single_class:
    - {name: G14-D, measured: <N>, threshold: <M>, ratio: <R>}
  final_verdict: <pass|warning|fail>
  max_band_basis: <class_count|single_severity>
```

### 4.4 触发位置与次数

- 位置：`t7_5_integrity → g14_style_gate → phase4_4_figures`（Phase 4.4 前置，定稿前最后一道闸）
- 首审全流程只一次；`t5_style_revision` 风格修订后全文复检 ≤2 轮
- 适用性由 Phase 0「目标语言」客观决定：含中文必跑，纯外语记 n/a

---

## 五、T7 审计员执行细节

文件路径：`references/agents/07-审计-auditor.md`

### 5.1 核心定位

「唯一专门挑错的角色。写手看不到自己的盲区，我的存在就是防止质量漂移。」

### 5.2 严重级分类

| 级别 | 含义 | 处置 |
|------|------|------|
| **P0 致命** | 编造引用/数据、论点无据、论证链断裂、抄袭、跑题 | 必须改，否则不能用 |
| **P1 严重** | P1-A/B/C 结构性（论证补强/结构缺失/反方观点缺失）→ T5 重启独立写手；P1-D 事实错误（引用格式/数据溯源/漏引/拼写）→ T8 亲修 | 应当改 |
| **P2 建议** | 措辞、篇幅、可读性 | 可优化 |

### 5.3 审计必查项（G0-G17，共 20 项）

- **G1 引用核验**：两档标注——存在性核验（标题/作者/年份）≠ 数字级核验（具体数值）；新增文献 A 级 100% 抽验
- **G8 字数核验**：单一口径（纯中文字符数，仅正文不含附录），仅报档位（达上限/超5-10%/超>10%），不得报精确数
- **G14 核验**：已移交 T8（G14 在 T7 之后），T7 只保留边界声明
- **引用编号独立性**：禁区间引用（[Dxx]-[Dyy]）和合并引用，命中 = P0
- **跨卡数值一致性**：数据卡与案例卡同指标数值 diff，未并列声明主/扩展口径 = P1
- **E1 证据链抽验**（项目启用时）：分片齐全性 + 主张关系回写，两项须显式成节

### 5.4 硬卡与产出

- 硬卡阈值：**12 分钟**，超时 → 主控 kill + 接受 partial
- 产出两份：`audits/审计报告-vN.md` + `audits/反哺报告-vN.md`（缺一不可）
- 报告头显式写 `修订回环 = N/2`
- 反哺报告分级：P0（产品机制 bug，建议高优 merge）/ P1（体验质量，中优）/ P2（优化，低优）

### 5.5 工具档

- allow_audit = **read（只读）**
- 报告全文随交接回传，由主控 write 落盘
- 报告前置自查超 3500 字符 → 分片预申报协议

---

## 六、T5 写手执行细节

文件路径：`references/agents/05-写作-writer.md`

### 6.1 核心原则

「严格按分析大纲写，只用检索卡里的真实材料，绝不自由发挥编造。」

### 6.2 素材按需加载硬步骤

1. 读 `analysis/分析大纲.md`「论点-论据映射表」段
2. 列出本稿引用的所有 [Lxx]/[Dxx]/[Cxx] 编号
3. 只 read 相关 evidence 段（不读全文）
4. 证据超 100 条 → Phase 2.5 拍板「按主题分组读」
5. 实测节省：8 万字素材 → 只读 1.5 万字，节省 80% token

### 6.3 反方论证四要素模板

每个反方回应段必含：
1. **反方观点**（最强反方版本，来自大纲）
2. **数据反驳**（引 [Dxx]/[Lxx] 回应）
3. **边界声明**（本方论据适用边界）
4. **自评局限**（本方论证的已知弱点）

### 6.4 字数口径与权威核验分离

- 字数 = 纯中文字符数（仅正文，不含文末附录）
- T5 自报只给「估算值 + 口径 + 误差标注」
- **权威核验唯一出口** = 主人 host shell 跑 `grep -oP '\p{Han}' file.md | wc -l`，或 T8 终检 read 逐字计数
- 禁止 `grep -o '[一-龥]'`（字节范围 bug，实测 20 倍失真）
- T8 实测覆盖自报，不得采信 T5/T7 自报

### 6.5 长文分段与增量落盘（v2.13.2）

- 单轮安全量级 ≈ 8k 汉字 / 900s
- 重量档（≥10000 字）默认拆段：先 write 骨架，再按节 edit 追加
- 拆段须预申报分片清单

### 6.6 修订轮定点编辑纪律

- 默认流程：主控 cp 出基线 → T5 只做 edit 定点替换
- 禁止 write 重写正文、整文件覆盖、借修订之名重排压缩
- 修订说明逐条记 oldText → newText + 汉字增减
- 自报与实测背离 ⇒ 整轮作废

---

## 七、M 门算法信任模型与判定协议

文件路径：`references/_shared/真源/M-Gate-Algorithm.md`

### 7.1 诚实声明：M 门 = LLM 推理判定，非机器强制

M 门 13 项伪代码是「**主控 LLM 推理模拟执行**」，不是真 shell 命令：
- ❌ 不是：主控跑 `grep -E "..." file.md` 等真 shell
- ✅ 是：主控 LLM read 文件 → 推理模拟算法 → 输出 JSON 报告

### 7.2 信任模型

| 维度 | 信任度 | 说明 |
|------|--------|------|
| M-Form（形式合规） | 80-90% | LLM 推理判定格式，错判可能性低 |
| M-Exist（存在性） | 70-85% | LLM 推理判定文件存在 + 编号对应 |
| M-Integrity（阶段闸门） | 85-95% | LLM 推理判定主控 checkpoint |
| sha256 / bytes | 默认不验 | 主人侧量值，未回填 ⇒ pending_owner_verification |

### 7.3 判定结果四档（替代退出码）

| 档位 | 含义 | 阻断 | 触发修订 | 处置 |
|------|------|------|----------|------|
| 通过 | 全部检查项为真 | 否 | 否 | 放行 |
| 不通过 | 内容/证据缺陷（P0/P1/P2） | 是 | 是 | 触发修订或补检索 |
| 无法判定 | 输入不可读/证据不足 | 是 | 否 | 补证据或人在环裁决后重跑 |
| 路径或参数错误 | 产物不存在/路径越界/参数非法 | 是 | 否 | 修路径/参数后重跑同一判定 |

### 7.4 可复核判定协议（四固定字段）

每个 M 门条目必备：

| 字段 | 含义 |
|------|------|
| `判定输入` | 实际读了哪个版本：{文件路径, 版本标识, 首行原文, 末行原文, 字节数} |
| `原文值` | 判定的输入事实（计数/编号集合/标题清单），逐字照抄 |
| `裁定值` | LLM 推理结论值 |
| `证伪依据` | 不一致时必填：命中位置枚举 + 真阳性模式扫描 + 规范冲突说明 |

**通过档证据最低要求**：扫描对象指纹 + 命中清单（不得只给计数）+ 零命中自证（扫描范围 + 匹配规则）。

### 7.5 渐进式执行（5 阶段分批）

- Phase 1.5（T1/T2/T3 后）：M-Integrity-1 + M-Form-6
- Phase 2.5（T4 后）：M-Form-3
- Phase 3.5（T5 v1 后）：M-Form-1/2/4/5
- Phase 3.6（T6 后）：M-Form-7
- T7.5（T7 后）：M-Exist-1/2/3 + M-Integrity-2
- Phase 5（T8）：T8 兜底集

---

## 八、E1 证据对象模型

文件路径：`references/_shared/真源/evidence-object-model.md`

### 8.1 设计目的

增加可追踪中间层，使核心正文主张能够回溯：

```
正文主张 C-xxx → ClaimEvidenceLink → E-xxx 证据 → L/D/C 来源记录
```

E1 不是新质量门，不替代 G2/G15/G17。

### 8.2 三类对象

#### PaperRecord（论文记录）

必填字段：`record_type`(=paper) / `paper_id` / `title` / `authors` / `year` / `source_records` / `retrieval_status`(candidate/verified/rejected)

边界：`full_text: unavailable` 必须保留；PaperRecord 不能单独支撑实质理论判断。

#### SnippetRecord（原文片段记录）

必填字段：`record_type`(fulltext_snippet/case_evidence) / `evidence_id`(E-xxx) / `source_ref` / `text` / `snippet_kind` / `support_type` / `retrieved_at` / `verification_status`

`snippet_kind` 枚举：title | abstract | body | methods | results | discussion | conclusion | metadata_only

`access_basis` 枚举：open_access | abstract_only | owner_supplied | secondary_source

#### ClaimEvidenceLink（主张-证据链）

（从 glossary-core.md 可见，E1 启用时建立主张—证据链）

### 8.3 支持类型语义

- `directly_supports`：须符合 G15
- `indirectly_supports`：必须降级措辞或加限定
- `contextualizes`：只能作背景
- `qualifies` / `contradicts`：不得静默删除
- `insufficient`：不得支撑正文
- `abstract_only` / `metadata_only`：不得写成全文实证

---

## 九、主控执行韧化协议

文件路径：`references/agents/00-主控-coordinator.md` + `references/_shared/真源/执行韧化协议-exec.md`

### 9.1 四层防御

1. **启动心跳**：子代理启动后发心跳
2. **分阶段 ACK**：4 段 0%/33%/66%/100%
3. **LLM 可用性初判**：Phase 0 静态映射模型能力档
4. **角色分级硬卡**：T1-T3 10min / T4 12min / T5 15min / T6 15min / T7 12min / G14 8min

### 9.2 模型能力抽象

- **能力档**：检索=便宜快 / 分析写作=强推理 / 批判审计=顶配 / 主控=稳定路由
- **Phase 0 静态映射**：读 session_status 只读元数据，每个能力档选第一个可用模型
- **运行时降级**：首次失败 → degraded 自报 → 优先换 provider 族；顶配档连续 2 次失败 ⇒ 断路器

### 9.3 盲审禁代笔（S-2）

`independence: blind_review` 节点（当前 = t9_review）失败时：
- 唯一合法恢复 = 重试 spawn 独立子代理
- 重试仍失败 ⇒ 记为缺失 + 告知主人（不得记 Done/accepted）
- 禁声明 `on_worker_failure: {executor: 主控}`

### 9.4 同 provider 连续静默升级（S-3）

同一 provider 连续 ≥3 次静默（无产物 + 无交接回执，心跳仍在 = 未静默）⇒ 强制主人三选一：
1. 换 provider 族
2. 换能力档
3. 接受同源并披露

无默认，静默 ≠ 有效决策。

### 9.5 主控兜底唤醒（P-2）

spawn 任意 worker 后，安排一次「定时自唤醒」兜底，触发时间 = 硬卡阈值 + 缓冲。到点后主动 read 磁盘核对产物。零 exec / 零轮询。

### 9.6 写盘确认铁律

收到完成报告后，用 read 检查：存在 + 非空 + 首尾哨兵 + 当前稿件版本 + 交接报告关键字段。不得把回执本身当作写盘证据。3 步任一不通过 → 不接管、不进入下一阶段。

---

## 十、24 节点流水线全景表

文件路径：`references/_shared/真源/pipeline-overview.md`（唯一派生视图）

| seq | 节点 id | Phase | 执行者 | 产物 / 出口 |
|-----|---------|-------|--------|-------------|
| 0 | phase0_definition | Phase 0 | 主人 × 主控 | 01-任务简报.md + status.md |
| 1 | pre_spawn_enforcement | Phase 0 后置 | 主控 | status.md（顶配档探活门） |
| 2 | retrieval | Phase 1 | T1∥T2∥T3 | 文献卡 + 数据卡 + 案例卡 |
| 3 | phase1_5_targeted_review | Phase 1.5 | 主控 spawn T1b | 回查报告（条件触发） |
| 4 | t2_5_integrity | T2.5 | 主控 checkpoint | 数据卡完整性门 |
| 5 | t4_analysis | Phase 2 | T4 | 分析大纲 + T5-写作上下文 |
| 6 | phase2_5_outline | Phase 2.5 | 主人 × 主控 | 大纲确认 + 图位拍板 |
| 7 | t5_draft_v1 | Phase 3 | T5 | drafts/初稿-v1.md |
| 8 | phase3_5_insight | Phase 3.5 | 主人 × 主控 | insight / no_insight |
| 9 | current_draft_sync | Phase 3.6 前置 | 主控 | drafts/current_draft.md |
| 10 | t6_critique | Phase 3.6 | T6（轻量档必跳） | 批判报告 |
| 11 | t5_feedback_revision | Phase 3.7 | T5（条件触发） | 修订稿 + 修订说明 |
| 12 | t7_audit | Phase 4 | T7 | 审计报告（G0-G17） |
| 13 | audit_revision | Phase 4.2 | T5（有界回环） | 修订稿，max_rounds=2 |
| 14 | t1b_targeted_review | Phase 4.3 | T1b（条件触发） | 定向回查报告 |
| 15 | t7_5_integrity | T7.5 | 主控 checkpoint | M-Gate-Report JSON |
| 16 | g14_style_gate | Phase 4.4 前置 | G14 | G14 检测报告（含中文必跑） |
| 17 | t5_style_revision | Phase 4.4 前置 | T5 | 仅风格层修订（G14 Fail 出口） |
| 18 | phase4_4_figures | Phase 4.4 | 主控 | final/图件/*.svg（零外发） |
| 19 | final_assembly | Phase 4.4 后置 | 主控 | final/定稿.md（只产投稿版） |
| 20 | t9_review | Phase 4.5 | T9（盲审） | 审稿报告（6 维度评分） |
| 21 | t8_technical_final | Phase 5 | 主控（T8 亲为） | 交付说明.md |
| 22 | methodology_snapshot | Phase 5 后置 | 主控 | methodology-footprint（默认触发） |
| 23 | phase5_acceptance | Phase 5 验收 | 主人 × 主控 | accepted / revision_requested / restart_phase / deferred |

### 修订回环仲裁

| 轮次 | 内容 | 计数 |
|------|------|------|
| 0 轮 | T5 初稿 v1 | — |
| 不计轮 | v1→v2 主人洞察修订 | ❌ 不计入 ≤2 轮 |
| 轮 1 | v2→v3 批判修订（T6→T5） | ✅ 计入 |
| 轮 2 | v3→v4 审计修订（T7，内部 ≤2 轮） | ✅ 计入 |
| minor | T8 inline 亲修（≤5% 字） | 独立登记 |
| 超限 | Acknowledged Limitations（主人拍板） | 例外通道 |

---

> **文档说明**：本文档所有细节均来自实际读取的源码/真源文档。流程顺序与阻断关系的唯一真源为 `references/_shared/真源/phase-order.yaml`；M 门算法真源为 `references/_shared/真源/M-Gate-Algorithm.md`；G14 判定真源为 `references/gates/14-中文AI痕迹-gate.md`。
