# 论衡（lunheng-article-pipeline）Code Wiki

> **版本**：v2.13.3（2026-09-25）
> **项目定位**：中文学术 / 深度长文多 Agent 流水线
> **核心命题**：「独立角色 + 结构化自评门 > 自我复核」
> **许可证**：MIT License — Copyright (c) 2026 左运来 (zuoyunlai)

---

## 目录

1. [项目概述](#一项目概述)
2. [整体架构](#二整体架构)
3. [目录结构与模块职责](#三目录结构与模块职责)
4. [核心流水线与阶段真源](#四核心流水线与阶段真源)
5. [十角色体系](#五十角色体系)
6. [三层防御体系（M 门 / F 模式 / G 清单）](#六三层防御体系m-门--f-模式--g-清单)
7. [工程侧工具链（scripts/）](#七工程侧工具链scripts)
8. [关键类与函数说明](#八关键类与函数说明)
9. [依赖关系](#九依赖关系)
10. [测试体系（tests/）](#十测试体系tests)
11. [CI/CD 流水线](#十一cicd-流水线)
12. [项目运行方式](#十二项目运行方式)
13. [设计原则与关键取舍](#十三设计原则与关键取舍)

---

## 一、项目概述

论衡是一套**纯 Skill**（不附带宿主配置项）的多 Agent 深度长文生产流水线，定位为中文学术论文 / 商业评论 / 行业分析 / 公众号深度长文的通用写作框架。

### 1.1 核心特性

- **九角色多 Agent 编排**：主控用 OpenClaw `sessions_spawn` 派发三方真并行子代理（T1∥T2∥T3 互不干涉）
- **三角验证证据底座**：文献卡 [Lxx] + 数据卡 [Dxx] + 案例卡 [Cxx]
- **三层防御体系**：M 门（形式合规）+ F 模式（失败模式）+ G 清单（质量审计）
- **人在环四节点**：Phase 0 定题 / Phase 2.5 大纲 / Phase 3.5 洞察 / Phase 5 终稿验收
- **G14 中文 AI 痕迹闸**：定稿前最后一道闸，9 类检测维度，LLM 推理判定（零 exec）
- **T9 同行评审**：6 维度评分 + 期刊匹配
- **零 exec 哲学**：所有子代理不调用 `exec` / `process` / `code_execution` 等执行类工具

### 1.2 项目双视图

| 视图 | 范围 | 受众 |
|------|------|------|
| **开发者视图**（GitHub 仓库） | 完整特性：`scripts/` + `tests/` + `Makefile` + `.github/` + 根级配置 | 维护者 |
| **使用者视图**（ClawHub 净化包） | 仅 `SKILL.md` + `LICENSE` + `references/` + `QUICKSTART.md` | 终端使用者 |

净化包由 `scripts/build-clawhub-release.sh` 生成，剥离所有开发者工具链（`scripts/` 整目录、`tests/`、`.github/`、根级配置均不进包）。

---

## 二、整体架构

### 2.1 分层架构

论衡采用三层分层架构，遵循「一条款一真源」原则：

```
┌─────────────────────────────────────────────────────────┐
│  使用者可读层（SKILL.md / QUICKSTART.md / README.md）    │
│  · 只引用不重列运行时真源；重列即构建期红（flow-check 24）│
├─────────────────────────────────────────────────────────┤
│  运行时正文层（references/）                             │
│  · 同一口径只有一个真源文件，其余为派生视图并标注真源指针  │
├─────────────────────────────────────────────────────────┤
│  工程层（scripts/ / tests/ / 根级配置）                  │
│  · 不承载运行时口径，只承载机械校验                      │
│  · 变更不改变流水线语义，对使用者不可见（不进净化包）    │
└─────────────────────────────────────────────────────────┘
```

### 2.2 流水线全景

```
主控（Coordinator）—— 定题/拆解/派发/T8 终检亲完成/状态机
  │
  ├─ T1 文献检索员（Literature Scout）── 文献卡 [Lxx]      ┐
  ├─ T2 数据检索员（Data Scout）──────── 数据卡 [Dxx]      │ 三方真并行
  ├─ T3 案例检索员（Case Scout）────── 案例卡 [Cxx]      ┘ 互不干涉
  │
  ├─ T4 分析员（Analyst）────────── 分析大纲（论证主线 + 反方论证 + 建议图表）
  ├─ T5 写手（Writer）────────────── 初稿（AI 去味 10 项）
  ├─ T6 批判伙伴（Critical Companion）── 批判报告（C1-C7 反方攻击 v2）
  ├─ T7 审计员（Auditor）────────── 审计报告（G0-G17 = 20 项）
  └─ T9 同行评审（Peer Reviewer）── 审稿报告（6 维度评分 + 期刊匹配）
              ↓
         T8 终检 = 主控亲完成（独立角色卡，不 spawn）
```

### 2.3 状态机

每个任务状态：`Inbox → Assigned → In Progress → Review → Done | Failed`

- **主控独占写** `status.md`；角色不直接写，经心跳文件 `run/<项目名>/.tmp/<两位角色号>-<角色名>-heartbeat.md` 发信号
- 失败要留原因；任一行停留超硬卡阈值无进展 → 主控介入

---

## 三、目录结构与模块职责

### 3.1 根目录

| 文件 / 目录 | 面向 | 职责 |
|-------------|------|------|
| `SKILL.md` | 使用者 + 宿主 | **入口契约**：触发场景、能力边界与权限声明、Phase 0 启动清单、单源指针与派发索引 |
| `QUICKSTART.md` | 使用者 | 安装 / 宿主适配要点 / 5 分钟上手 / 不适用场景 / FAQ |
| `README.md` | 外部读者 | 对外介绍与导读：核心特点、外发类别导读、实战案例、版本演进 |
| `pyproject.toml` | 开发者 | black / isort / pylint / pytest / coverage 配置 |
| `requirements.txt` | 开发者 | 核心依赖（tiktoken / pyyaml / pytest / pytest-cov） |
| `Makefile` | 开发者 | 开发者工具入口（install / test / lint / format / audit / preflight 等） |
| `CHANGELOG.md` | 开发者 | 版本演进记录（最近 5 期，更早迁入 `CHANGELOG-archive.md`） |
| `LICENSE` | 全部 | MIT 许可证 |

### 3.2 references/（运行时正文层）

| 子目录 | 职责 | 关键文件 |
|--------|------|----------|
| `agents/` | 10 张角色卡定义 | `00-主控-coordinator.md`、`01-文献检索` ~ `09-审稿-peer-reviewer.md` |
| `dispatch/` | 各阶段派发话术（spawn 前主控按需读） | T1-T9 + G14 + T1b 共 11 文件 |
| `gates/` | 闸门定义 | `14-中文AI痕迹-gate.md` |
| `checkers/` | 检查器 | `中文AI痕迹-checker.md` |
| `templates/` | 产物模板（精简版 `-lite` + 完整版） | 任务简报 / status / 交接报告 / 卡片 / checkpoint-card 等 |
| `_shared/真源/` | **共享真源层**：口径、算法、协议、索引 | `phase-order.yaml`、`asset-index.md`、`pipeline-overview.md`、`M-Gate-Algorithm.md` 等 |
| `_shared/治理/` | 维护者内档（不进净化包） | 教训索引、项目归档 SOP、反哺报告处理 |

### 3.3 scripts/（工程层工具链）

30 个脚本文件，详见 [第七节](#七工程侧工具链scripts)。

### 3.4 tests/（测试层）

36 个测试文件 + fixtures，详见 [第十节](#十测试体系tests)。

### 3.5 .github/workflows/（CI 层）

4 个工作流，详见 [第十一节](#十一cicd-流水线)。

---

## 四、核心流水线与阶段真源

### 4.1 唯一真源：phase-order.yaml

`references/_shared/真源/phase-order.yaml` 是**流程顺序与阻断关系的唯一真源**。主控进入每个 Phase 前必读其完整定义；`SKILL.md` 与 `pipeline-overview.md` 均为派生视图，冲突时以 yaml 为准。

yaml 顶层结构：
- `version`：版本号（随 SKILL.md 同步）
- `verdict_scale`：判定结果四档定义（pass / fail / undecidable / path_or_param_error）+ default_handling
- `silence_doctrine`：跨状态机共享不变式（静默 ≠ 有效决策）
- `owner_timeout_policy`：人在环节点无应答处置（唯一真源）
- `pipeline`：节点列表（含 `id` / `kind` / `phase` / `phase_seq` / `input` / `output` / `next` / `on_fail` 等）

### 4.2 阶段划分（Phase 0-5）

| Phase | 名称 | 负责角色 | 关键产物 | 人在环 |
|-------|------|----------|----------|--------|
| **0** | 定题 | 主控 × 人类 | `01-任务简报.md`、`status.md` | ✅ 4 选 1 同意关卡 |
| **1** | 并行检索 | T1∥T2∥T3 | 文献卡 / 数据卡 / 案例卡 | - |
| **2** | 分析 | T4 | `analysis/分析大纲.md` | - |
| **2.5** | 大纲确认 | - | - | ✅ 主人过目大纲 |
| **3** | 写作 | T5 | `drafts/初稿-v1.md` | - |
| **3.5** | 洞察补充 | - | - | ✅ 主人补充或「无补充」 |
| **3.6** | 批判 | T6 | `analysis/批判报告-vN.md` | - |
| **4** | 审计 | T7 | `audits/审计报告-vN.md` | - |
| **4.4 前置** | G14 痕迹闸 | G14 | `audits/G14-检测报告-vN.md` | - |
| **4.5** | 同行评审 | T9 | `audits/审稿报告-vN.md` | - |
| **5** | 终检 | T8（主控亲完成） | `final/定稿.md` + 证据包 | ✅ 主人验收决策 |

### 4.3 关键协议

完整 5 协议见 `references/_shared/真源/关键协议.md`：
- **Phase 0 同意关卡**：外发数据须先经主人拍板（4 选 1）
- **0 条空卡**：cases=0 时产空卡（显式声明，不静默跳过）
- **并行独立运行**：T1/T2/T3 互不干涉
- **修订回环**：常规修订 ≤2 轮硬约束，例外通道须主人拍板
- **完成验证铁律**：无明确决策 = 未通过

---

## 五、十角色体系

### 5.1 角色定义

| 编号 | 角色 | 职责 | 启动时机 | 工具档 |
|------|------|------|----------|--------|
| **T0** | 主控 Coordinator | 定题、拆解、派发、状态机、T8 终检亲完成 | 始终在线 | base + coordinator_only + research_extra |
| **T1** | 文献检索员 Literature Scout | 已发布学术文献/政策文件/统计年鉴检索 | Phase 1 | research |
| **T2** | 数据检索员 Data Scout | 已发布统计数据/行业报告/新闻数据检索 | Phase 1 | research |
| **T3** | 案例检索员 Case Scout | 企业行为/事件/司法案件检索；cases=0 产空卡 | Phase 1 | research |
| **T4** | 分析员 Analyst | 论点拆解 + 论证结构设计 + 大纲编写 | Phase 2 | analysis |
| **T5** | 写手 Writer | 正文撰写 + 修订执行 | Phase 3 | writing |
| **T6** | 批判伙伴 Critical Companion | 从反方攻击论证（C1-C7） | Phase 3.6 | audit |
| **T7** | 审计员 Auditor | 质量审计（G0-G17，共 20 项）+ 修订任务书 | Phase 4 | audit |
| **T8** | 终检 Final Inspector | 48 必查项 + 小幅修补（**主控亲完成，不 spawn**） | Phase 5 | （空） |
| **T9** | 同行评审 Peer Reviewer | 6 维度评分 + 期刊匹配 | Phase 4.5 | review |

### 5.2 子代理工具档分级（metadata.subagent_tiers）

| 档位 | 适用角色 | 工具集（声明） |
|------|----------|----------------|
| `research` | T1/T2/T3 | read + write + edit + web_search + web_fetch + tavily_search + tavily_extract |
| `analysis` | T4 | read + write + edit |
| `writing` | T5 | read + write + edit |
| `audit` | T6/T7 | **read（只读）** — 报告随交接回传，由主控 write 落盘 |
| `review` | T9/G14 | **read（只读）** |

> ⚠️ **声明式边界**：档位是论衡自身的调用边界声明，OpenClaw 加载器不据此限制工具；实际工具面由平台决定。`denied` 清单 104 项（真源 = `SKILL.md` frontmatter `metadata.tools.denied`）。

### 5.3 硬卡阈值

| 角色 | 硬卡墙钟 | 平台超时 runTimeoutSeconds |
|------|----------|----------------------------|
| T1/T2/T3 | 10 分钟 | 600s |
| T4 | 12 分钟 | 720s |
| T5 | 15 分钟 | 900s |
| T6 | 15 分钟 | 900s |
| T7 | 12 分钟 | 720s |
| T9 | - | 600s |
| G14 | 8 分钟 | 480s |
| spawn watchdog | 8 分钟 | - |

---

## 六、三层防御体系（M 门 / F 模式 / G 清单）

### 6.1 M 门（形式合规）

LLM 结构化自评（**零 exec**；规则硬性、非机器强制），共 13 项：

| 类别 | 项 | 名称 |
|------|-----|------|
| **M-Form**（8 项） | M-Form-1 | 引用完整性 |
| | M-Form-2 | 结构完整性 |
| | M-Form-3 | 无临时编号 |
| | M-Form-4 | 无角色元信息 |
| | M-Form-5 | 无过程性语言 |
| | M-Form-6 | 信任度标注 |
| | M-Form-7 | 章节白名单 |
| | M-Form-8 | 三角验证覆盖 |
| **M-Exist**（3 项） | M-Exist-1 | 引用证据存在性 |
| | M-Exist-2 | 证据完整性 |
| | M-Exist-3 | 信任度一致性 |
| **M-Integrity**（2 项） | M-Integrity-1 | T2 数据源 5 要素 |
| | M-Integrity-2 | T7 审计报告完整性 |

- **渐进式执行**：分批触发，P0 错误提前暴露
- **算法真源**：`references/_shared/真源/M-Gate-Algorithm.md`（伪代码段必读）
- **依赖配置**：`scripts/m_gate_dependencies.yaml`（每项 M 门的依赖文件与 scope）

### 6.2 F 模式（失败模式）

面向用户的叙事，F1-F9 失败模式清单（幻觉 / 格式 / 数据信任 / 论证强度等）。真源 = `references/_shared/真源/failure-modes.md`。

### 6.3 G 清单（质量审计）

面向审计员，G0-G17 共 20 项（含 G0.5 / G2.5）。真源 = `references/agents/07-审计-auditor.md` + 速查 `audit-checklist-quickref.md`。

### 6.4 G14 中文 AI 痕迹闸

- **位置**：Phase 4.4 前置（`g14_style_gate`）——定稿前最后一道闸
- **频次**：全流程只审一次；风格修订后全文复检 ≤2 轮
- **适用性**：由 Phase 0「目标语言」客观决定（含中文必跑，纯外语记 n/a）
- **判定**：9 类检测维度，LLM 推理判定（零 exec）
  - 0-2 类 Pass / 3-4 类 Warning（呈报 3 选 1）/ 5+ 类 Fail → T5 最后一次风格层修订
- **真源**：`references/gates/14-中文AI痕迹-gate.md` + `references/checkers/中文AI痕迹-checker.md`

---

## 七、工程侧工具链（scripts/）

共 30 个脚本文件，索引视图 = `scripts/README.md`（由 `gen-scripts-index.py` 自动生成）。以下按职责分组：

### 7.1 版本管理与一致性

| 脚本 | 职责 | 关键函数/逻辑 |
|------|------|---------------|
| `sync-version.sh` | 从 SKILL.md frontmatter 读版本号，批量同步到全部受管文件顶部（层 2 写入）；末尾自动调用 self-audit-gate.sh + 正文版本一致性门 | 三层联动：check-version（只读）/ sync-version（写入）/ CI 验证 |
| `check-version.sh` | 只读验证所有应含版本号文件的版本戳一致性（层 1） | - |
| `normalize-version-header.py` | 文件头版本戳归一化（sync-version.sh 的幂等写入口） | - |
| `changelog-check.py` | changelog 一致性检查/回填；4 种模式：--check / --online / --fill / --report | `current_version()`、`version_tags()` |
| `gen-scripts-index.py` | 从各脚本头部注释生成 scripts/README.md 索引（纯派生视图） | - |

### 7.2 流程与质量校验

| 脚本 | 职责 | 关键函数/逻辑 |
|------|------|---------------|
| `flow-check.py` | **流程图检查**：phase-order.yaml 的引用有效性、可达性、入参链闭合、YAML 重复键、Phase 编号、人环闸门声明等 42 条规则 | `UniqueKeyLoader`、`_paths()`、`_norm()`、`main()` |
| `flow-schema.py` | 声明式「跨载体一致性」校验器（可复用治理引擎）；校验载体文件存在性 + token 必须/不得出现 | `UniqueKeyLoader`、`_load_schema()`、`_carrier_paths()`、`main()` |
| `flow-schema.lunheng.yaml` | 论衡「跨载体一致性」规则的声明式演示实例 | - |
| `link-check.py` | 相对链接可解析性检查（3 类：markdown 链接 / 入口文档裸文件引用 / 活文档反引号内联引用） | - |
| `self-audit-gate.sh` | 自审门（8 门 A-H）：角色卡完整性、编号覆盖、流程图可达性、权限口径一致性等 | `pass()` / `fail()` / `count_role_hits()` |
| `paper-ready-check.py` | 可发表性 48 项检查器（6 维度：头部洁净 / 前置要素 / AI 使用声明 / 结构 / 图表 / 引文） | `check_head_clean()`、`check_front_matter()`、`check_ai_declaration()` 等 |
| `paper-ready-check.sh` | paper-ready-check.py 的本地封装 | - |
| `incremental_m_gate.py` | 增量 M 门验证器：定位变更范围 + 判定受影响的 M 门（**不产出验证结论**，fail-closed） | `ChangeDetector`、`SectionChangeDetector`、`compute_hash()` |
| `m_gate_dependencies.yaml` | M 门依赖关系配置（每项 M 门的 depends_on 文件 + scope） | - |

### 7.3 能力与权限

| 脚本 | 职责 | 关键函数/逻辑 |
|------|------|---------------|
| `capability-assert.py` | 能力断言脚本：spawn 前断言所需能力可用，拒绝高风险能力；单一真源读 SKILL.md frontmatter | 角色分区校验、denied 优先、`--selfcheck` 自检 |
| `runtime-capability-probe.py` | 能力边界「声明 vs 实际」runtime 探针工具 | - |
| `inject-lang-policy.py` | 批量注入「语言政策」声明行（幂等） | - |

### 7.4 发布与构建

| 脚本 | 职责 | 关键函数/逻辑 |
|------|------|---------------|
| `build-clawhub-release.sh` | 从「完整特性真源」生成「ClawHub 净化发布包」（双视图分离） | 版本号格式校验（防 rm -rf 注入）、`--exclude` 剥离开发者工具 |
| `publish-clawhub.sh` | ClawHub 一键发布封装 | - |
| `create-github-release.sh` | 从 CHANGELOG.md 建/同步 GitHub Release（写路径强制调 preflight） | `--allow-existing-tag`、`--skip-preflight` |
| `release-preflight.sh` | 发版前置闸「四查一停」：在飞链 / 编号占用 / 工作区干净 / CI 不红 | 只读拒绝器，退出码 10/11/12/13 分别对应四查失败 |
| `pkg-integrity.py` | 净化包**正向**完整性校验：净化前快照，净化后比对（防过度剥离） | `snapshot` / `verify` 双模式、字符保留率、必需结构锚点 |

### 7.5 净化与清理

| 脚本 | 职责 |
|------|------|
| `strip-internal-leakage.sh` | 剥除净化包内所有主控侧运维痕迹 |
| `strip-anchor-residue.py` | 净化包「编号锚点」残留清理 |
| `strip-shell-commands.py` | 净化包 shell 命令剥离 |
| `cleanup-skill-store.sh` | 技能库瘦身脚本 |

### 7.6 路径与锁

| 脚本 | 职责 |
|------|------|
| `path-canonical.py` | 路径规范化校验器 |
| `project_lock.py` | 项目锁管理器（防并发运行多项目时的文件冲突） |

### 7.7 测试辅助

| 脚本 | 职责 |
|------|------|
| `test-capability-assert.sh` | capability-assert.py 测试套件 |
| `test-path-canonical.sh` | path-canonical.py 测试套件 |

---

## 八、关键类与函数说明

### 8.1 flow-check.py（流程图检查器）

核心类与函数：

| 名称 | 类型 | 说明 |
|------|------|------|
| `UniqueKeyLoader` | 类（继承 `yaml.SafeLoader`） | YAML 重复键硬失败（后键静默覆盖前键 = 真源失真） |
| `_no_dup_keys(loader, node, deep)` | 函数 | 构造映射时检测重复键，命中则抛 `ConstructorError` |
| `_norm(tok)` | 函数 | 版本占位归一：`初稿-v{N}.md` / `初稿-vN.md` / `初稿-v1.md` → `初稿-v#.md` |
| `_paths(decl)` | 函数 | 从声明（字符串/列表/映射）中抽出归一路径集合 |
| `main()` | 函数 | 主入口：加载 phase-order.yaml，执行 42 条规则校验 |

关键常量：
- `EXEC_KINDS`：执行类节点 kind（agent / owner_agent / parallel_agents / conditional_agent / advisory_agent / bounded_loop）
- `INPUT_KINDS`：入参类节点 kind（EXEC_KINDS + conditional_review_window）
- `PATH_RE` / `DIR_RE`：路径 token 正则

### 8.2 flow-schema.py（声明式校验引擎）

| 名称 | 类型 | 说明 |
|------|------|------|
| `UniqueKeyLoader` | 类 | 同 flow-check，YAML 重复键硬失败 |
| `_load_schema(schema_path)` | 函数 | 加载并解析 schema YAML |
| `_carrier_paths(root, carriers, names, errs)` | 函数 | 别名 → 绝对路径映射；未定义别名 = fail-closed |
| `main(argv)` | 函数 | 主入口：支持 `--schema` / `--root` 参数 |

断言类型（`KINDS`）：`files_exist` / `tokens_exist` / `tokens_absent`

### 8.3 incremental_m_gate.py（增量 M 门）

| 名称 | 类型 | 说明 |
|------|------|------|
| `ChangeDetector` | 类 | 文件级变更检测（fallback）；`compute_hash()` SHA256、`has_changed()` |
| `SectionChangeDetector` | 类 | 章节级变更检测（v2.10.0 增强） |

设计要点：**fail-closed** —— 未做机械验证的 M 门一律报 `passed=False` / `status=unverified`，退出码非 0。

### 8.4 capability-assert.py（能力断言）

设计要点：
- **单一真源**：允许面/禁用面直接读 SKILL.md frontmatter，不维护第二份权限清单
- **denied 优先**：同时出现在允许面与 denied 的能力，一律判定为禁用
- **角色分区**：`coordinator_only` 仅对主控角色 T0/T8 放行；worker 请求任一项即拒绝

### 8.5 pkg-integrity.py（净化包正向校验）

| 模式 | 说明 |
|------|------|
| `snapshot <pkg_dir> <snapshot.json>` | 净化前快照 |
| `verify <pkg_dir> <snapshot.json>` | 净化后比对 |

verify 判定（任一不过即 exit 1）：快照非空 / 文件仍存在 / md 非退化（≥200 字符 + 标题）/ 字符保留率 ≥ 35% / 必需结构锚点 / frontmatter 可解析

### 8.6 changelog-check.py（changelog 校验）

| 名称 | 说明 |
|------|------|
| `current_version()` | 从 SKILL.md frontmatter 读取当前版本号（单一真源） |
| `version_tags()` | 本地版本 tag（排除工作 tag） |
| `--check` | 离线校验：每个 tag 有对应章节 + 当前版本已记录 |
| `--online` | 追加在线校验：每个 tag 有 GitHub Release |
| `--fill` | 从 GitHub Releases 回填缺失章节（幂等） |
| `--report` | 列出 Release 正文过短的章节 |

### 8.7 project_lock.py（项目锁）

| 名称 | 类型 | 说明 |
|------|------|------|
| `ProjectLock` | 类 | 项目锁管理器；`acquire()` / `release()` 防并发文件冲突 |

---

## 九、依赖关系

### 9.1 Python 依赖（requirements.txt）

| 包 | 版本 | 用途 |
|----|------|------|
| `tiktoken` | 0.5.2 | Token 计数（SKILL.md token 统计） |
| `pyyaml` | 6.0.1 | YAML 解析（phase-order.yaml 等配置读取） |
| `pytest` | 7.4.4 | 测试框架 |
| `pytest-cov` | 4.1.0 | 覆盖率报告 |

### 9.2 测试依赖（tests/requirements-test.txt）

测试专用依赖（具体见该文件）。

### 9.3 系统依赖

- **bash**（脚本执行）
- **grep** / **md5sum**（self-audit-gate.sh）
- **shellcheck**（lint，`make lint`；需 `sudo apt install shellcheck`）
- **git**（版本管理、发版前置闸）
- **gh CLI**（changelog-check --online、create-github-release.sh，需登录）
- **openclaw**（官方 quick_validate.py 校验，`npm i -g openclaw`）

### 9.4 开发工具配置（pyproject.toml）

| 工具 | 配置 |
|------|------|
| **black** | line-length=88，target=py312 |
| **isort** | profile=black，multi_line_output=3 |
| **pylint** | max-line-length=88，禁用 C0111/C0103/R0913/R0914 |
| **pytest** | testpaths=tests，addopts="-v --tb=short --strict-markers" |
| **coverage** | source=scripts,tests |

### 9.5 外部服务（运行时，Phase 0 须主人同意）

| 服务 | 类别 | 默认状态 |
|------|------|----------|
| `web_search` | OpenClaw 内置 web provider | 默认启用 |
| `tavily_search` / `tavily_extract` | Tavily AI | 默认启用 |
| `web_fetch` | OpenClaw 内置 | 默认启用 |
| OpenAlex / Crossref（学术元数据） | 只读公开 API | **opt-in，默认关闭** |
| 数据图表 SVG | 本地内置（主控 write 手写） | 零外发 |
| 大模型推理 | 当前模型 provider | 默认启用 |

---

## 十、测试体系（tests/）

### 10.1 测试组织

36 个测试文件，按职责可分为：

| 类别 | 测试文件 |
|------|----------|
| **流程与真源一致性** | `test_flow_check.py`、`test_flow_check_meta.py`、`test_flow_schema.py`、`test_m_gate.py`、`test_incremental_m_gate.py` |
| **文档质量与口径** | `test_doc_quality.py`、`test_rules_consistency.py`、`test_audit_residuals.py`、`test_scan_stale_language.py`、`test_version_prose_gate.py` |
| **版本与 changelog** | `test_sync_version_header_idempotent.py`、`test_changelog_fill_idempotent.py`、`test_publish_changelog_extraction.py`、`test_release_archive_lookup.py` |
| **发布与构建** | `test_release_preflight.py`、`test_create_release_e2e.py`、`test_release_script_guards.py`、`test_build_gate_hardening.py`、`test_pkg_integrity.py`、`test_outputs_root_semantics.py` |
| **能力与权限** | `test_capability_assert.py`、`test_gate_x_fence_phase.py` |
| **净化链** | `test_strip_internal_leakage_delimiters.py`、`test_link_check.py`、`test_scripts_index.py` |
| **证据对象** | `test_e1_evidence_objects.py`、`test_e1_3_feedback_fixes.py` |
| **版本回归** | `test_v21232_livetest_fixes.py`、`test_v21233_audit_fixes.py`、`test_v21240_adoptions.py`、`test_v2130_p0_fixes.py` |
| **其他** | `test_project_lock.py`、`test_status_telemetry.py`、`test_gate_h_reverse_diff.py`、`test_bulk_ratchet.py`、`test_external_audit_fixes.py`、`test_ci_config.py` |

### 10.2 测试 fixtures

`tests/fixtures/` 下提供论文样例：
- `valid_paper.md` / `valid_paper_with_year.md` —— 合规论文样例
- `missing_citation.md` —— 缺引用样例
- `inline_paper.md` —— 内联引用样例
- `lessons-gate.md` —— 教训索引样例

### 10.3 运行测试

```bash
make test          # 运行全量测试 + capability-assert 测试
# 或
pytest -v --tb=short --cov=scripts --cov-report=term-missing
```

---

## 十一、CI/CD 流水线

### 11.1 工作流清单

| 工作流 | 触发条件 | 职责 |
|--------|----------|------|
| `quality.yml` | push / PR（main/master/develop） | ShellCheck + pytest + self-audit-gate + check-version + Python 语法 |
| `ci-test.yml` | PR（特定路径）/ push master | M 门测试 + T9/G14 规则一致性 + 权限/流程图测试 + 全量测试 + 版本同步 + 自审门 + 官方 quick_validate.py |
| `version-check.yml` | push / PR（SKILL.md + references/**） | 版本号一致性检查（调 check-version.sh） |
| `changelog-check.yml` | push / PR（CHANGELOG*）/ 每周一 09:00 | changelog 离线校验 + 在线覆盖校验 + 篇幅报告 |

### 11.2 quality.yml 核心步骤

1. **ShellCheck** —— `scripts/*.sh`，severity=warning
2. **pytest** —— 仓库根运行，`--cov=scripts`
3. **self-audit-gate.sh** —— 自审门
4. **check-version.sh** —— 版本一致性
5. **py_compile** —— Python 语法检查

### 11.3 ci-test.yml 核心步骤

1. M 门 13 项算法格式测试（`test_m_gate.py`）
2. T9 + G14 规则一致性测试（`test_rules_consistency.py`）
3. 权限口径 + 流程图真源测试（`test_capability_assert.py` + `test_flow_check.py`）
4. **全量测试**（`tests/` 全量，权威判据）
5. 版本号同步检查
6. 自审门验证
7. 官方 SKILL.md 校验（`quick_validate.py`）

---

## 十二、项目运行方式

### 12.1 安装（使用者）

```bash
# 方式一：ClawHub 安装（推荐）
openclaw skills install @zuoyunlai/lunheng-article-pipeline@2.13.3

# 方式二：本地安装
openclaw skills add /path/to/lunheng-article-pipeline
```

装好后，在任意有 `sessions_spawn` + 检索工具的 agent 里 `@lunheng-article-pipeline` 显式触发。

### 12.2 快速开始

1. **写任务简报**（2 分钟）：新建 `<项目名>/01-任务简报.md`，含研究问题/类型/篇幅/引用格式 + Phase 0 同意关卡
2. **主控自动派发**：T1∥T2∥T3 并行检索 → T4 分析 → T5 写作 → T6 批判 → T7 审计 → T9 审稿 → T8 主控亲终检
3. **主人在 4 个节点介入**：Phase 0（定题）/ 2.5（大纲）/ 3.5（洞察）/ 5（终稿验收）

### 12.3 预计时间

| 档位 | 字数 | 预计时间 |
|------|------|----------|
| 轻量档 | 2000-3000 字 | 30-60 分钟 |
| 中段档 | 3000-5000 字 | 1-2 小时 |
| 重量档 | ≥5000 字 | 2-4 小时 |

### 12.4 开发者命令（Makefile）

| 命令 | 职责 |
|------|------|
| `make install` | 安装开发依赖 |
| `make test` | 运行测试套件 + capability-assert 测试 |
| `make lint` | ShellCheck（severity=warning）+ Python 语法检查 |
| `make format` | black + isort 格式化 |
| `make audit` | 运行自审门 |
| `make changelog-check` | changelog 完整性校验 |
| `make scripts-index` | 刷新 scripts/README.md 索引 |
| `make preflight` | 发版前置闸（四查一停） |
| `make sync-version` | 同步版本号 |
| `make build-release` | 构建 ClawHub 发布包 |
| `make release` | 完整发布流程（preflight + sync-version + all + build-release） |
| `make all` | lint + test + audit + changelog-check |
| `make clean` | 清理临时文件 |

### 12.5 版本升级流程（维护者 SOP）

1. 改 `SKILL.md` frontmatter 的 `version:` 字段
2. 跑 `./scripts/sync-version.sh`（自动同步 + 自审门 + 正文版本一致性门）
3. 跑 `./scripts/check-version.sh`（只读验证）
4. 跑 `./scripts/self-audit-gate.sh`（全门自审）
5. 内容质量 SOP 修订后额外跑 `./scripts/paper-ready-check.sh <项目名>`
6. 跑 `make preflight`（发版前置闸四查一停）
7. `git commit` + `git tag` + `git push`

---

## 十三、设计原则与关键取舍

### 13.1 一条款一真源

- 同一口径只有一个真源文件，其余为派生视图并显式标注真源指针
- 使用者可读层**只引用不重列**运行时真源；重列即构建期红（flow-check 规则 24）
- 工程层不承载运行时口径，只承载机械校验

### 13.2 零 exec 哲学

- 所有子代理不调用 `exec` / `process` / `code_execution` 等执行类工具
- M 门通过「LLM 兜底执行伪代码」实现结构化核验，不引入 Python 脚本
- 数据图表由主控 `write` 手写 SVG，零外发

### 13.3 fail-closed 设计

- Phase 0 未同意 = 不得进 Phase 1
- 人在环节点无应答 = 挂起等主人，**不静默推进**（静默 ≠ 有效决策）
- 未做机械验证的 M 门 = 未验证（≠ 通过）
- YAML 重复键 = 硬失败
- 净化包只有负向检查不够，必须有正向校验（pkg-integrity.py）

### 13.4 双视图分离

- 开发者视图（完整特性）vs 使用者视图（净化包）
- 开发者工具链不进净化包，避免 ClawHub scanner 误判
- 净化包内容由 `_shared/` 白名单准入门控制

### 13.5 版本一致性三层联动

- 层 1：`check-version.sh`（只读验证）
- 层 2：`sync-version.sh`（批量写入 + 末尾自动跑自审门 + 正文版本一致性门）
- 层 3：`.github/workflows/version-check.yml`（CI 云端验证）

### 13.6 权限边界取舍

- 论衡是**纯 skill**，不附带宿主配置项
- 子代理工具面由 OpenClaw 平台负责；论衡的运行时处置 = 记录 + 披露 + 主人裁决
- 铁律：**工具面超限 ≠ 调用许可**
- 论衡不判断宿主配置状态，也不要求宿主做任何额外设置

---

> **文档生成说明**：本文档基于仓库 v2.13.3 版本分析生成。流程顺序与阻断关系的唯一真源为 `references/_shared/真源/phase-order.yaml`；角色定义真源为 `references/agents/`；M 门算法真源为 `references/_shared/真源/M-Gate-Algorithm.md`。本文档为派生视图，冲突时以真源为准。
