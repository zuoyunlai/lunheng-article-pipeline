<!-- 自动生成，请勿手改：本文件由 scripts/gen-scripts-index.py 从各脚本头部注释 + Makefile 派生。
     脚本用途的真源 = 各脚本头部注释；刷新 = make scripts-index；漂移锁 = tests/test_scripts_index.py -->

# scripts/ 脚本索引（自动生成）

> 🔁 **派生视图**：本表由 `gen-scripts-index.py` 机械提取，**不承载新口径**。列源：**用途** = 脚本头部首个内容行；**用法** = 头部 `用法：` / `调用：` 行；**触发时机** = 头部 `触发：` 行；**make 入口** = `Makefile` recipe 中调用该脚本的目标。单元格里的「—」= 该脚本**未声明**该项（不是「不存在用法」；补口径请改脚本头，勿改本文件）。改了脚本头请跑 `make scripts-index` 刷新本文件；`tests/test_scripts_index.py` 会因本文件与 `scripts/` 不一致而报红（缺条目 / 残留已删条目 / 条目内容漂移）。
> 📦 **本文件不进发布包**：`scripts/` 整目录由构建脚本排除，使用者侧不出现开发者工具链。

共 **35** 个条目（`scripts/` 下除本索引自身以外的全部文件）。

| 脚本 | 用途 | 用法 | 触发时机（头部声明） | make 入口 |
|---|---|---|---|---|
| [`build-clawhub-release.sh`](build-clawhub-release.sh) | build-clawhub-release.sh — 从「完整特性真源」生成「ClawHub 净化发布包」 | bash scripts/build-clawhub-release.sh [VERSION] | — | `make build-release` |
| [`capability-assert.py`](capability-assert.py) | capability-assert.py — 论衡能力断言脚本 | python3 scripts/capability-assert.py <role> <capability1> <capability2> ... | — | — |
| [`changelog-check.py`](changelog-check.py) | 论衡 changelog 一致性检查 / 回填（P2「changelog 完整化 CI 校验」） | python3 scripts/changelog-check.py [--check\|--online\|--fill\|--report] | — | `make changelog-check` |
| [`check-version.sh`](check-version.sh) | 论衡版本号一致性检查脚本（P1-3 版本号自动化 - 层 1） | ./scripts/check-version.sh | — | — |
| [`cleanup-skill-store.sh`](cleanup-skill-store.sh) | cleanup-skill-store.sh — 论衡技能库瘦身脚本 | — | 主人手动跑 / 每次发版前自动跑 | — |
| [`contract-check.py`](contract-check.py) | Build-time contracts for high-drift declarations. | — | — | `make contract-check` |
| [`create-github-release.sh`](create-github-release.sh) | create-github-release.sh — 从 CHANGELOG.md 建 / 同步 GitHub Release（一条命令） | bash scripts/create-github-release.sh [<tag>] [--dry-run\|--check] [--no-dispatch] | — | — |
| [`dispatch-contract.py`](dispatch-contract.py) | dispatch-contract.py — 论衡派发话术合同块生成与校验（v2.15.x 第二批机械门）。 | python3 scripts/dispatch-contract.py # 生成并写盘 | — | `make dispatch-contract`、`make dispatch-contract-check` |
| [`flow-check.py`](flow-check.py) | 论衡流程图检查 | python3 scripts/flow-check.py → 无输出=通过；有输出=问题列表（分号分隔）。 | — | — |
| [`flow-schema.lunheng.yaml`](flow-schema.lunheng.yaml) | flow-schema.lunheng.yaml — 论衡「跨载体一致性」规则的声明式演示实例（批次 4-B） | — | — | — |
| [`flow-schema.py`](flow-schema.py) | flow-schema.py — 声明式「跨载体一致性」校验器（可复用治理引擎，批次 4-B） | python3 scripts/flow-schema.py [--schema scripts/flow-schema.lunheng.yaml] | — | — |
| [`gen-scripts-index.py`](gen-scripts-index.py) | gen-scripts-index.py — 从各脚本头部注释生成 scripts/README.md 索引（纯派生视图） | python3 scripts/gen-scripts-index.py | — | `make scripts-index` |
| [`incremental_m_gate.py`](incremental_m_gate.py) | 增量 M 门验证器 | — | — | — |
| [`inject-lang-policy.py`](inject-lang-policy.py) | inject-lang-policy.py — 批量注入「语言政策」声明行（幂等） | python3 scripts/inject-lang-policy.py # 注入（幂等） | — | — |
| [`link-check.py`](link-check.py) | link-check.py — 相对链接可解析性检查 | python3 scripts/link-check.py [文件或目录 ...] # 默认：README/QUICKSTART/CHANGELOG/references | — | — |
| [`m_gate_dependencies.yaml`](m_gate_dependencies.yaml) | M 门依赖关系配置 | — | — | — |
| [`markdown-structure-lint.py`](markdown-structure-lint.py) | markdown-structure-lint.py — 确定性 Markdown 结构门。 | — | — | `make markdown-structure-lint` |
| [`normalize-version-header.py`](normalize-version-header.py) | normalize-version-header.py — 文件头版本戳归一化（sync-version.sh 的幂等写入口） | python3 scripts/normalize-version-header.py --root <skill_root> \ | — | — |
| [`paper-ready-check.py`](paper-ready-check.py) | paper-ready-check.py —— 可发表性判定表 48 项的机械分组检查。 | — | — | — |
| [`paper-ready-check.sh`](paper-ready-check.sh) | paper-ready-check.sh —— 论衡 v2.12.0 可发表性机械实现 34 项本地自动检查（判定表总计 48 项，未实现项不计入）封装 | — | — | — |
| [`path-canonical.py`](path-canonical.py) | path-canonical.py — 论衡路径规范化校验器 | python3 scripts/path-canonical.py <base_dir> <target_path> | — | — |
| [`phase-order-slice.py`](phase-order-slice.py) | phase-order-slice.py — 论衡流程真源「文本保真装配器」 | python3 scripts/phase-order-slice.py # 生成/刷新装配视图 | — | — |
| [`pkg-integrity.py`](pkg-integrity.py) | pkg-integrity.py — 净化包**正向**完整性校验 | python3 scripts/pkg-integrity.py snapshot <pkg_dir> <snapshot.json> | — | — |
| [`project_lock.py`](project_lock.py) | 论衡项目锁管理器 | — | — | — |
| [`publish-clawhub.sh`](publish-clawhub.sh) | publish-clawhub.sh — 论衡 ClawHub 一键发布封装 | bash scripts/publish-clawhub.sh [VERSION] [--yes] | — | — |
| [`rebuild.sh`](rebuild.sh) | 论衡 phase-order.yaml 一键重建 | — | — | — |
| [`release-preflight.sh`](release-preflight.sh) | release-preflight.sh — 发版前置闸「五查一停」 | bash scripts/release-preflight.sh [<tag>] [选项] | — | `make preflight` |
| [`runtime-capability-probe.py`](runtime-capability-probe.py) | runtime-capability-probe.py — 论衡能力边界「声明 vs 实际」runtime 探针工具 | — | — | — |
| [`self-audit-gate.sh`](self-audit-gate.sh) | self-audit-gate.sh — 论衡自审门自动化执行脚本 | — | commit 前由 sync-version.sh 末尾自动调用；或主控 LLM 主动跑 | `make audit` |
| [`strip-anchor-residue.py`](strip-anchor-residue.py) | 净化包「编号锚点」残留清理 | python3 scripts/strip-anchor-residue.py <净化包目录> | — | — |
| [`strip-internal-leakage.sh`](strip-internal-leakage.sh) | 一次性清理：剥除净化包内所有主控侧运维痕迹 | bash scripts/strip-internal-leakage.sh <净化包目录> | — | — |
| [`strip-shell-commands.py`](strip-shell-commands.py) | 论衡 ClawHub 净化包 —— shell 命令剥离脚本 | — | — | — |
| [`sync-version.sh`](sync-version.sh) | 论衡版本号同步脚本（P1-3 版本号自动化 - 层 2） | ./scripts/sync-version.sh [--dry-run] | — | `make sync-version` |
| [`test-capability-assert.sh`](test-capability-assert.sh) | test-capability-assert.sh — capability-assert.py 测试套件（v2.9.1） | — | — | `make test` |
| [`test-path-canonical.sh`](test-path-canonical.sh) | test-path-canonical.sh — path-canonical.py 测试套件（v2.9.1） | — | — | `make path-canonical`、`make test` |

## 维护者 QA 装置索引（v2.14.1，审计 R-49）

> **分层约定（两层文档）**：本索引是**维护者侧 QA 装置叫法**的唯一落点。交付物
> （`SKILL.md` / `references/` / `templates/` / `dispatch/`）**只写「给使用者看的声明式内容」**；
> 维护者侧的**命令名 / 规则编号 / 门编号 / 测试框架名**一律收敛到本文件（或 `references/_shared/治理/`）。
> 违反此约定 = 交付物用维护者方言写成（审计 R-43：2.14.0 包内实测 `flow-check` 27 处 /
> `构建期红` 12 处 / `pytest` 3 处 / `self-audit` 1 处逸出）。

| 装置 | 维护者侧叫法 | 交付物侧口径 |
|---|---|---|
| 流程校验器 | `scripts/flow-check.py` 规则编号 | 「由维护者机制机械校验」（**不裸露规则编号**） |
| 构建期阻断 | 「构建期红」 | 「构建期校验不通过」 |
| 自审门 | `scripts/self-audit-gate.sh`（门 A-AA） | 「自检门」 |
| 测试框架 | `pytest tests/` | 「维护者侧一致性测试」 |
| 净化链 | `scripts/strip-internal-leakage.sh` / `scripts/build-clawhub-release.sh` | 不存在（纯构建期装置） |

**机械保障（三重，防复发）**：

1. **源头中性化** — `strip-internal-leakage.sh` 阶段 6b（md 通道 + 非 md 文本资产通道）；
2. **产物侧兜底** — `build-clawhub-release.sh` `FINAL_PATTERNS` v2.14.1 组（产物命中即 fail-loud）；
3. **不变式单测** — `tests/test_declarative_purity.py`（含反向对照，防判据空转）。

**新增内容时的落点**：维护者命令 / 门编号 / 指标 → 写在本文件；使用者可读的核心机制名
（`门 M` / `门 C` / `门 S` 等，由交付物正文自解释）→ 留在交付物。
