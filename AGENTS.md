# AGENTS.md — 论文流水线操作手册

## 启动时必读
1. `SOUL.md` — 我的身份与职责
2. `pipeline/README.md` — 流水线运行手册（含复制即用的派发话术）
3. `memory/YYYY-MM-DD.md` — 今日/昨日记录（如有）

## 流水线协议（摘要，详见 pipeline/README.md）

```
Phase 0 定题     → 与主人确认主题/类型/篇幅/引用格式 + 案例检索强度 + 外部服务告知 → 写 run/<项目>/01-任务简报.md
Phase 1 并行检索 → spawn T1 文献检索员 ∥ T2 数据检索员 ∥ T6 案例检索员（可选重量场景）（sessions_yield 等待）
Phase 2 分析     → spawn T3 分析员 → analysis/分析大纲.md
Phase 2.5 大纲确认 → 主人过目 → 三角验证 [L]+[D]+[C] 缺角补检索
Phase 3 写作     → spawn T4 写手 → drafts/初稿-v1.md
Phase 3.5 洞察补充 → 主人深度洞察补充（人在环，v2.1.3）→ 写手 v2 融入
Phase 4 审计     → spawn T5 审计员 → audits/审计报告-vN.md（G0-G10 十项检查）
                 → 打回修订 ≤2 轮；仍不过 → 升级决策
Phase 5/T7 终检  → 通读全文 → final/定稿.md + 证据包/ + 交付说明.md
```

## 关键规则
- **派发话术**：直接从 `pipeline/README.md` 复制，改项目名即可
- **每个项目一个目录**：`run/<项目名>/`，产物路径见任务简报
- **模型分配**：检索子代理用便宜的（deepseek-v4-flash），审计用顶配（minimax-m3 / claude-opus-5）
- **子代理产出必须交交接报告**：五要素缺一不可，静默超 **8 分钟**主动介入（v2.3 从 10 分钟收紧）
- **执行韧化协议**（v2.1.0）：7 角色卡全部注入——30s 心跳 + 分阶段 ack + 模型健康度预检 + 8 分钟硬卡
- **项目进展记入** `memory/YYYY-MM-DD.md` 和 `memory/projects.md`

## 文件修改操作约束（v2.1.4 F5 补完，教训 #48）

论衡工作区所有修改走以下安全流程，**任何时候禁止 `sed -i`**（静默清空文件事故教训）：

1. **改前**：`wc -l <file>` 记录行数 + `cp <file> /tmp/<file>.bak` 备份
2. **改中**：用 `edit` 工具（精确 oldText 匹配），**不用 sed/awk/perl 直接写回原文件**
3. **改后**：`wc -l` 对比 + `diff <file> /tmp/<file>.bak` 验证（不一致立即从 .bak 恢复）
4. **跨文件 sync**：用 `cp` 不带任何转换，直接覆盖（skill 副本同步是 `references/` 路径映射）
5. **验证**：本修改走完后必 `grep` 关键词 + 结构性 grep（如本手册的「## 交接报告」所有角色卡齐整性）

## 记忆文件
- `memory/YYYY-MM-DD.md` — 每日日志（记结论不记过程）
- `memory/projects.md` — 各论文项目状态
- `MEMORY.md` — 长期约定（保持精简）
