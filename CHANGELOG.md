# Changelog

---

## [v2.15.4] — 2026-09-30

> **主题：全量审计修订 —— 3 项 P0 阻断缺陷 + 12 项 P1 门假绿 + 10 项 P2 口径漂移**

- **P0-1 发布链失败不可见修复**（`scripts/publish-clawhub.sh`）：dry-run 去掉 `|| true`（失败即 `exit 6`）；displayName 不符由 warn 改硬失败（`exit 7`）；净化包新增内容核验（版本戳 + `.pkg-manifest.txt` 路径解析到源树）；正式发布前串行调用 `release-preflight.sh`。
- **P0-2 T7.5 时序倒置修复**（`M-Gate-核心.md`）：步骤 4（读 `final/交付说明.md`）整体移出至 T8 —— 该文件在 T7.5（phase_seq 15）时尚未生成，旧版导致首轮必然落「路径或参数错误」第 4 档。新增「合法输入集合」声明，伪代码第 0 步改判 `audits/` 审计报告。
- **P0-3 字数合同门恒等比较修复**（`scripts/contract-check.py`）：`tier_declarations()` 改捕获正则实际区间（原存入 `TIER_LABELS` 常量，与自身比较恒等通过）；补 3 条反向注入回归。
- **P1 门假绿与越权修复**：M 门判定改 `glob(M-Gate-Report-*.json)` + 四档 `判定档位`（废止 `exit_code`）；引用闭环改 `(作者, 年份)` 双键对账 + 编号首现序严格一致；CI 分类器要求 `status=completed AND conclusion=success`（`[{}]`/skipped 不再记 green）；M 门 6 处零断言用例补真断言；项目锁改 `O_EXCL` 原子创建 + `owner_token` 防 PID 复用（并补空文件窗口竞态守卫）；`audited_artifact` 语义区分 T7/G14（草稿）与 T9/T8（终稿）。
- **P1 口径与脚本加固**：发布前置闸扩为「五查一停」（新增教训快照在位，判据 = 仓库内 hermetic 快照 `教训索引.md`）；`cleanup-skill-store.sh` 增 `.git/objects` 物理备份（覆盖 reflog-only 对象）；`incremental_m_gate.py` 落缓存文件清单；`capability-assert.py` 明确最小权限真源 = frontmatter；T1 派发话术澄清工具自适应真源；`t7_audit` 前置接受 `skip_in_lite_tier`。
- **P2 口径漂移收敛**：`dispatch-header.md` 只读档心跳由主控代写 + `degraded_toolset_silent_continue`/`degraded_workforce_takeover` 语义消歧；`SKILL.md` 轻量档 G18 措辞对齐真源、frontmatter `fmt`→`audit` 档位名；`Makefile`/`quality.yml` 同步五查措辞与 action 版本钉（`action-shellcheck@v2.0.6`）；`T1b` 补 `phase_window` 双窗口字段（`Phase 1.5` 初筛复核 / `Phase 4.3` 修订回查，同一角色卡两处引用 → 显式消歧；**不新增独立角色**，T1b 复用 T1 角色卡，九角色架构不变）。
- **验证收口追加**：修复验证过程暴露的 7 处连带缺陷（JS 层 `\n` 转义破坏 Python 字面量 ×3、项目锁空文件窗口竞态、`M-Form-2` 必需节口径、合同门误报、`#*` 引号、反向注入用例 5 位数字失效）；33 项回归 3 连跑稳定通过；自审门 38 PASS / 0 FAIL。

---

## [v2.15.3] — 2026-09-29

- **高频数字机械门加固**：`scripts/contract-check.py` 升级为多文档多值集合比对，新增字数分档簇（轻量/中段/重量）与版本文件数（`scripts/check-version.sh` 真源）的实测钩子；`conceptual roles` 与 `physical role-card files` 拆为两个独立语义簇，避免把概念口径与物理文件数误判为冲突。
- **语言政策真源化与反向校验**：`scripts/inject-lang-policy.py` 加 `--normalize` 写入选项，`--check` 升级为同时检测「缺失」与「旧变体/不一致」，旧文本出现即红。
- **Markdown 结构门上线**：`scripts/markdown-structure-lint.py` 默认拦截字面量 `\n` 与未闭合代码围栏；`--strict` 额外拦截重复章号与孤立标题，作为新文档核验工具。
- **计数真源扩展**：`references/_shared/真源/counts.yaml` 新增 `version_files` 与 `word_tiers` 两组字段；`tests/test_contract_check.py` / `tests/test_markdown_structure_lint.py` 注册对应回归。
- **派发话术合同门**：新增 `scripts/dispatch-contract.py`，从 `phase-order/` 节点切片生成 G14 / T9 派发话术顶部合同块，`--check` 把「复检轮次 / 默认触发」口径漂移升级为构建期阻断；配套反向注入回归 `tests/test_dispatch_contract.py`。
- **模板能力矩阵真源**：新增 `references/_shared/真源/template-contracts.yaml` 驱动 lite/full 模板必填字段校验（维护者侧资产，已显式排除出净化包，不随包出厂）。
- **净化链一致性**：`counts.yaml` 注释去除随包文件中不得出现的维护者脚本名；随包准入与最终残留扫描双侧闭合。
- **验收**：核心回归 **56+ passed**（含本轮新增门与回归）；`contract-check` / `markdown structure lint` / `inject-lang-policy --check` 全部 PASS。

---

## [v2.15.2] — 2026-09-29

- **发布链修复**：轮转 `CHANGELOG.md` 保持最近 5 期上限，补齐 v2.14.5 归档章节，修复 changelog CI 阻断。
- **v2.15.1 收口延续**：保留审计收口、fail-closed 加固、Phase 0 字段与流程对齐等修订。

---

## [v2.15.1] — 2026-09-29

- **审计修订收口**：统一 G14 首审与风格修订后全文复检 ≤2 轮的口径，修正相关派发话术、闸门、流程索引与测试锚点。
- **Fail-closed 加固**：M 门证据包 `sha256` / `bytes` 占位符不再判通过；投稿版引用闭环检查不再接受空集合。
- **Phase 0 字段与流程对齐**：补齐 lite 任务简报生产字段，统一字数分档、T9 默认触发、G0-G18 审计范围及多格式导出时序。
- **维护性修订**：修复脚本索引漂移、phase-order 装配视图同步、体量棘轮基线与语言政策旧文案残留。

---

## [v2.15.0] — 2026-09-29

- **B1 运行可靠性**：补强 worker 终态、空输出、重要写入 read-back、主控接管和 T9 缺位硬规则。
- **B2 证据链闭环**：补全方法契约、引用—证据卡四向对账与 DOI 分层核验。
- **B3-B5 运行效率与可观测性**：引入 current_draft_sync 指针化同步、机械任务查询化、事件账本、工具路由降级记录和 gate telemetry。
- **B6-B7 诊断与质量收尾**：新增三态 pipeline-doctor、组装后图注复检、独立方向纠偏状态与主人通知三态留痕。
- **边界保持**：全程保持纯 skill、零 exec、声明式、fail-closed 人在环；诊断和机械对账不得替代语义审计或主人 checkpoint。
- **验收**：全量 pytest 652 passed；B1-B7 回归 39 passed；流程一致性 125 passed；自审门 40 PASS / 0 FAIL（门 H 环境性 SKIP）。
