# Changelog

---

## [v2.13.1] — 2026-09-24

- **E1 证据对象与主张—证据链基础层**：新增供应商无关的 `PaperRecord`、`SnippetRecord`、`ClaimEvidenceLink` 对象模型真源。
- **证据登记与主张映射模板**：新增项目级 `research/evidence-register.md` 登记模板和 `analysis/主张—证据映射.md` 模板，保留 `[Lxx]` / `[Dxx]` / `[Cxx]` 交付编号体系。
- **流水线最小接线**：T1/T3/T4/T7/T8 增加 E1 可选接线；复用 G15 主张强度双轴，不新增 G18、不新增外发类别、不接入 AI4Scholar API。
- **机械验收**：新增 E1 一致性/反向注入测试；全量 pytest **524 passed**；链接门、版本头门和构建净化链通过。
- **兼容与边界**：旧项目无 E1 登记表时保持兼容；`full_text: unavailable`、`abstract_only` 和反向证据披露边界明确。

## [v2.13.0] — 2026-09-24

- **背景**：ECS 实战项目《否决权阴影下的制度对冲》（`lunheng-un-veto-russia-ukraine-2026`，12031 字重量档）暴露 8 项问题；主人拍板 P0 三项合并本版一次发版。
- **P0-1 · Phase 4.3 T1b 定向回查节点（新节点，流水线 23→24 节点）**：T5 修订轮新增引用标「待人工核验」而 T1 已结束的系统性缺口 → 新增 `t1b_targeted_review`（`audit_revision` 后、`t7_5_integrity` 前），复用 T1 角色卡与 research 档（九角色架构不变）；≤2 轮，耗尽走主人三选一（接受 + Acknowledged Limitations / 主人自行核验 / 删除未核验引用）；新增 `dispatch/T1b-定向回查.md` 派发话术；Phase 1.5 触发面同步扩展文献级 [Lxx] 待复核。
- **P0-2 · G14 风格复检严格度档（全文词表计数，≤2 轮）**：旧轻量复检只扫修订片段，实战「路径」残留 11 处 → `rerun_g14_style_recheck` 升级为全文 9 类词表逐类计数（禁只扫修订片段）；收敛判据 = 命中类数下降且无单类 ≥3x 阈值；`t5_style_revision.style_recheck_rounds_max: 2` 入真源；耗尽走主人三选一；v2.12.67「修订后不再复检、风险静默披露」口径作废；复检口径全仓 17 处同步（gate/dispatch/checker/报告模板/status 模板/主控卡/glossary/关键协议/quickref/asset-index/phase-3-details/全景）。
- **P0-3 · 引用编号独立性 + 出处可验证性铁律**：实战 T9 P0 发现 [D21-D28] 合并引用 → 写手卡新增「修订轮新增引用核验纪律」（未经核验必标「待人工核验」触发 T1b；禁区间引用 [L21]-[L26] 连写、禁合并引用/内部材料指路）；T2 卡 + 派发话术新增「出处可验证性」（学术来源 DOI 优先，非学术三件套；一个 [Dxx] 一条出处）；T7 卡新增「引用编号独立性核验」（区间/合并引用 → P0 必改）。
- **附带修复 · flow-check 两处机械缺口**：① PATH_RE 支持 `{N+1}` 版本占位（规则 6/9 此前对修订产出节点全程失效——产出路径从未被捕获）；② 规则 9 BFS 边序修正（`after_each` 先于 `next` 入队；原顺序提前命中 t7_audit 而 break，永远看不到同节点 after_each 里的 current_draft_sync）。均为本次新增 t1b 节点时被门暴露的既有缺陷。
- **全景与计数同步**：流水线 23→24 节点（canary 增 t1b 行 + seq 14-23 重排）；8 个镜像文档节点计数同步；checkpoint-card 步骤 9 映射补 t1b；门 Y 体量棘轮按实测重锚（00-主控 77630 / phase-order 61552）。
- **验收基线**：全仓版本统一 v2.13.0；新增 `tests/test_v2130_p0_fixes.py` 15 项回归锚（节点声明/三选一出口/生产方登记/漂移锚/G14 严格度/引用纪律/PATH_RE）；flow-check RC=0。

## [v2.12.74] — 2026-09-23

- **权限边界收敛**：补齐 runtime 实测漏出工具的 denied 声明至 104 项；移除 capability-assert 的宿主扩展硬编码，改以 SKILL.md frontmatter 为唯一权限真源。
- **角色分区校验**：coordinator_only 工具仅对 T0/T8 放行，worker 请求即拒绝，并新增双向 selfcheck 与回归测试。
- **流程与 CI 一致性**：修复 `t8_technical_final` 重复 `input/inputs` 字段、CI PR paths 的重组前旧路径，并新增 workflow 路径存在性测试。
- **版本与入口瘦身**：统一 v2.12.74 版本戳，压缩 SKILL.md 至官方 10000 字符上限以内；更新体量棘轮和旧权限语义测试。
- **验收基线**：权限 selfcheck、版本门、流程门与全量 pytest（494 项）通过；L1/L2 活体冒烟均已完成（结论 `pass_with_limits`：证据为离线预置/示例、引用真实性未联网核验，SHA256 已由宿主侧补算）；未 tag、未 push。

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
