# Changelog

---

## [v2.13.2] — 2026-09-25

- **外部审计修订**：完成 P1-B/P1-C/P2-A/P2-B，补充 runtime 工具面可观测字段、平台可见面/实际调用面/宿主 deny 三层边界、`Acknowledged Limitations` 统一入口，以及 Linux/WSL 支持环境与性能基线协议。
- **门 H hermetic 修订**：自审门默认不再受外部 workspace `lessons.md` 漂移影响，保留显式外部真源的正向差集与参照告警能力。
- **E1-3 反哺**：补齐证据对象、登记模板、主张—证据映射及相关流水线接线，并记录最新微型实测基线。
- **验收**：专项回归 38/38、发布净化链 42/42、自审门 36/36、全量 pytest 533/533、版本一致性 88/88、相对链接 554 条全部通过。


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
