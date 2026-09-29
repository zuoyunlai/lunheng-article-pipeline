# Changelog

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

---

## [v2.14.3] — 2026-09-27

- **入口职责去重**：README 收敛为面向人的定位、能力与安装概览；执行步骤与运行纪律统一指向 QUICKSTART、SKILL.md 及真源文档，减少三入口重复加载。
- **模板骨架瘦身**：checkpoint-card、status、任务简报模板移除可外移的说明注释、历史背景与重复判据，保留运行期填写骨架和机械校验锚点；维护说明下沉至仓库维护资料，并确保该资料不进入净化发布包。
- **发布链守卫**：净化构建脚本将维护资料明确列入排除清单，避免内部维护口径随包外发。
- **验收**：全量 pytest **608 passed / 1 skipped**；自审门 **39 PASS / 0 FAIL**（门 H 因外部 lessons 真源不可达 SKIP）；链接与流程检查通过。

---