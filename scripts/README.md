<!-- 自动生成，请勿手改：本文件由 scripts/gen-scripts-index.py 从各脚本头部注释 + Makefile 派生。
     脚本用途的真源 = 各脚本头部注释；刷新 = make scripts-index；漂移锁 = tests/test_scripts_index.py -->

# scripts/ 脚本索引（自动生成）

> 🔁 **派生视图**：本表由 `gen-scripts-index.py` 机械提取，**不承载新口径**。列源：**用途** = 脚本头部首个内容行；**用法** = 头部 `用法：` / `调用：` 行；**触发时机** = 头部 `触发：` 行；**make 入口** = `Makefile` recipe 中调用该脚本的目标。单元格里的「—」= 该脚本**未声明**该项（不是「不存在用法」；补口径请改脚本头，勿改本文件）。改了脚本头请跑 `make scripts-index` 刷新本文件；`tests/test_scripts_index.py` 会因本文件与 `scripts/` 不一致而报红（缺条目 / 残留已删条目 / 条目内容漂移）。
> 📦 **本文件不进发布包**：`scripts/` 整目录由构建脚本排除，使用者侧不出现开发者工具链。

共 **28** 个条目（`scripts/` 下除本索引自身以外的全部文件）。

| 脚本 | 用途 | 用法 | 触发时机（头部声明） | make 入口 |
|---|---|---|---|---|
| [`build-clawhub-release.sh`](build-clawhub-release.sh) | build-clawhub-release.sh — 从「完整特性真源」生成「ClawHub 净化发布包」 | bash scripts/build-clawhub-release.sh [VERSION] | — | `make build-release` |
| [`capability-assert.py`](capability-assert.py) | capability-assert.py — 论衡能力断言脚本 | python3 scripts/capability-assert.py <role> <capability1> <capability2> ... | — | — |
| [`changelog-check.py`](changelog-check.py) | 论衡 changelog 一致性检查 / 回填（P2「changelog 完整化 CI 校验」） | python3 scripts/changelog-check.py [--check\|--online\|--fill\|--report] | — | `make changelog-check` |
| [`check-version.sh`](check-version.sh) | 论衡版本号一致性检查脚本（P1-3 版本号自动化 - 层 1） | ./scripts/check-version.sh | — | — |
| [`cleanup-skill-store.sh`](cleanup-skill-store.sh) | cleanup-skill-store.sh — 论衡技能库瘦身脚本 | — | 主人手动跑 / 每次发版前自动跑 | — |
| [`create-github-release.sh`](create-github-release.sh) | create-github-release.sh — 从 CHANGELOG.md 建 / 同步 GitHub Release（一条命令） | bash scripts/create-github-release.sh [<tag>] [--dry-run\|--check] [--no-dispatch] | — | — |
| [`flow-check.py`](flow-check.py) | 论衡流程图检查 | python3 scripts/flow-check.py → 无输出=通过；有输出=问题列表（分号分隔）。 | — | — |
| [`gen-scripts-index.py`](gen-scripts-index.py) | gen-scripts-index.py — 从各脚本头部注释生成 scripts/README.md 索引（纯派生视图） | python3 scripts/gen-scripts-index.py | — | `make scripts-index` |
| [`incremental_m_gate.py`](incremental_m_gate.py) | 增量 M 门验证器 | — | — | — |
| [`inject-lang-policy.py`](inject-lang-policy.py) | inject-lang-policy.py — 批量注入「语言政策」声明行（幂等） | python3 scripts/inject-lang-policy.py # 注入（幂等） | — | — |
| [`link-check.py`](link-check.py) | link-check.py — 相对链接可解析性检查 | python3 scripts/link-check.py [文件或目录 ...] # 默认：README/QUICKSTART/CHANGELOG/references | — | — |
| [`m_gate_dependencies.yaml`](m_gate_dependencies.yaml) | M 门依赖关系配置 | — | — | — |
| [`normalize-version-header.py`](normalize-version-header.py) | normalize-version-header.py — 文件头版本戳归一化（sync-version.sh 的幂等写入口） | python3 scripts/normalize-version-header.py --root <skill_root> \ | — | — |
| [`paper-ready-check.py`](paper-ready-check.py) | paper-ready-check.py —— 论衡 v2.12.0 可发表性 48 项检查器 | python3 scripts/paper-ready-check.py <项目名> | — | — |
| [`paper-ready-check.sh`](paper-ready-check.sh) | paper-ready-check.sh —— 论衡 v2.12.0 可发表性 48 项本地自动检查封装 | — | — | — |
| [`path-canonical.py`](path-canonical.py) | path-canonical.py — 论衡路径规范化校验器 | python3 scripts/path-canonical.py <base_dir> <target_path> | — | — |
| [`pkg-integrity.py`](pkg-integrity.py) | pkg-integrity.py — 净化包**正向**完整性校验 | python3 scripts/pkg-integrity.py snapshot <pkg_dir> <snapshot.json> | — | — |
| [`project_lock.py`](project_lock.py) | 论衡项目锁管理器 | — | — | — |
| [`publish-clawhub.sh`](publish-clawhub.sh) | publish-clawhub.sh — 论衡 ClawHub 一键发布封装 | bash scripts/publish-clawhub.sh [VERSION] [--yes] | — | — |
| [`release-preflight.sh`](release-preflight.sh) | release-preflight.sh — 发版前置闸「两查一停」 | bash scripts/release-preflight.sh [<tag>] [选项] | — | `make preflight` |
| [`runtime-capability-probe.py`](runtime-capability-probe.py) | runtime-capability-probe.py — 论衡能力边界「声明 vs 实际」runtime 探针工具 | — | — | — |
| [`self-audit-gate.sh`](self-audit-gate.sh) | self-audit-gate.sh — 论衡自审门自动化执行脚本 | — | commit 前由 sync-version.sh 末尾自动调用；或主控 LLM 主动跑 | `make audit` |
| [`strip-anchor-residue.py`](strip-anchor-residue.py) | 净化包「编号锚点」残留清理 | python3 scripts/strip-anchor-residue.py <净化包目录> | — | — |
| [`strip-internal-leakage.sh`](strip-internal-leakage.sh) | 一次性清理：剥除净化包内所有主控侧运维痕迹 | bash scripts/strip-internal-leakage.sh <净化包目录> | — | — |
| [`strip-shell-commands.py`](strip-shell-commands.py) | 论衡 ClawHub 净化包 —— shell 命令剥离脚本 | — | — | — |
| [`sync-version.sh`](sync-version.sh) | 论衡版本号同步脚本（P1-3 版本号自动化 - 层 2） | ./scripts/sync-version.sh [--dry-run] | — | `make sync-version` |
| [`test-capability-assert.sh`](test-capability-assert.sh) | test-capability-assert.sh — capability-assert.py 测试套件（v2.9.1） | — | — | `make test` |
| [`test-path-canonical.sh`](test-path-canonical.sh) | test-path-canonical.sh — path-canonical.py 测试套件（v2.9.1） | — | — | — |
