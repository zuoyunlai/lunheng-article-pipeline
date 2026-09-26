# Changelog

---

## [v2.13.6] — 2026-09-26

- **深挖审计修订（R-26～R-42）**：收口发布包平台审计叙事泄漏、manifest 豁免内容漂移、checkbox 剥离损伤、unreachable 计数、项目锁释放假成功、增量 M 门缓存继承、paper-ready-check 附录/字数/CWD 判据，以及 phase-order 真源指针族。
- **门与净化链加固**：门 Q 扩展文本扫描面，门 G 增加随包清单对账，门 P 增加 checkbox 保真不变量，门 R 增加 RULE_CHECKS 基线，净化链保留 Markdown checkbox。
- **工具与文档收口**：统一 24 节点 seq 0–23 与 `phase-order/` 真源指针；补充 `.safe-pattern-manifest.json` 内容绑定；`project_lock.py release --force` 仅作显式夺锁。
- **验收**：针对性回归 **142 passed**；自审门 **39 PASS / 0 FAIL**；隔离发布包 v2.13.6 构建成功（115 文件）。

## [v2.13.5] — 2026-09-26

- **否认面真源外移（R-22）**：104 项 `denied` 完整清单从 SKILL.md frontmatter 迁入 `references/permissions.md` 的「禁用面唯一真源」块，frontmatter 只留 `denied_count: 104` + 8 项高危具名；门 T 与 `capability-assert.py` 统一从真源块读（缺块 / 计数漂移 / 高危越界一律 fail-closed）。SKILL.md 常驻预算 9,690 → **7,887 字符**（余量 2,113），门 T 覆盖 104 项逐项拒绝（原 41 项）。
- **相位序真源切片（R-21）**：相位序真源反转为逐节点切片 + 字节级漂移门，组装以文本忠实为判据（流程真源结构变更，单独立项完成）。
- **发版链残余收口（R-24.4）**：`cleanup-skill-store.sh` 三处 `grep -c … || echo 0`（零命中会输出 `0\n0`，同族教训 #150）改为 `|| true`；`find "$OUTPUTS_ROOT/…"` 补引号；确认未知参数 usage + exit 2。
- **验收**：自审门 **39 PASS / 0 FAIL**；全量 pytest **590/590**；构建链 23/23。

## [v2.13.4] — 2026-09-26

- **全面审计修订**：收口 G14 9 类与复检口径、门 C 空转/版本边界、门 S/T/U 静默跳过、门 X.4 围栏状态机、门 Z 失败计数、发版半成品清理与 preflight fail-closed；补齐 T1b 版本清单、tracked-only 测试沙箱、M fixture fail-loud、工具/计数文档漂移。
- **工具面与 CI 对齐**：工具能力边界与 frontmatter 集合对齐（补 `ask_user` / `sessions_list`，并新增集合一致性测试锁死漂移）；`path-canonical` 由「无任何门/CI 调用的孤儿脚本」纳入 `make test` 与 CI；CI 触发面与步骤对齐（`references/**` / `SKILL.md`、quality 增 changelog 检查、changelog workflow 监听 `references/**`）；新增 `.gitattributes` 统一换行，治跨挂载 CRLF/exec 位幻影。
- **计数单一真源**：新增 `references/_shared/真源/counts.yaml` 与计数漂移机械门 `tests/test_count_drift.py` —— 把「人记住 N 个地方」升级为「机器同源」，白名单 = CHANGELOG / archive / reports / 教训索引，并豁免「版本历史」小节（旧数字是史实）。
- **门清单自证（新增门 0）**：声明的 25 个顶层门必须各有 PASS / FAIL / SKIP 结论，缺一即红并点名；新增 SKIP 三态与配额告警（SKIP 从「静默消失」变成「可观测的覆盖缩小」）。此门回应实测事故：门 S/T/U 曾因条件注册而整门静默消失，报告上看不出异常。
- **验收**：全量 pytest 567/567、自审门 37 PASS/0 FAIL、版本一致性 89/89、path-canonical 12/12、发版链专项（构建/净化/清单）42/42；反向注入覆盖门 0（门 V 静默消失必红）与计数漂移 8 例。
- **验收基线**：全量 pytest 535/535、自审门 36/36、flow-check RC=0、版本一致性通过。


## [v2.13.3] — 2026-09-25

- **人在环交互体验**：Checkpoint Card 改为“决策摘要优先、详情后置”，降低主人在等待节点的认知负担。
- **等待与恢复协议**：新增首次呈现、一次轻提醒、挂起和主人返回后的恢复对账规则；不自动继续、不默认接受主人未作出的决定。
- **运行期可审计留痕**：status 模板新增 `checkpoint_id`、呈现时间、状态、提醒、挂起及主人决策归一化字段。
- **机械门**：将 HITL 呈现留痕检查接入 flow-check 规则 40，并补充反向注入测试，防止协议静默消失。
- **验收**：全量 pytest 535/535、自审门 36/36、flow-check RC=0、版本一致性通过。


## [v2.13.2] — 2026-09-25

- **外部审计修订**：完成 P1-B/P1-C/P2-A/P2-B，补充 runtime 工具面可观测字段、平台可见面/实际调用面/宿主 deny 三层边界、`Acknowledged Limitations` 统一入口，以及 Linux/WSL 支持环境与性能基线协议。
- **门 H hermetic 修订**：自审门默认不再受外部 workspace `lessons.md` 漂移影响，保留显式外部真源的正向差集与参照告警能力。
- **E1-3 反哺**：补齐证据对象、登记模板、主张—证据映射及相关流水线接线，并记录最新微型实测基线。
- **验收**：专项回归 38/38、发布净化链 42/42、自审门 36/36、全量 pytest 533/533、版本一致性 88/88、相对链接 554 条全部通过。
