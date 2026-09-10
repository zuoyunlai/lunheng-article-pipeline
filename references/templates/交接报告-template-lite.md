# 交接报告模板（精简版）

> **精简版**：只保留骨架 + 必填字段，详细说明见 [`交接报告-template.md`](交接报告-template.md)

```markdown
# 交接报告

> **位置**: `run/<项目名>/交接报告/<角色>-<阶段>.md`
> **使用**: 每个角色交付时必填

## 1. 做了什么
（一句话）

## 2. 产物在哪
- `path/to/file1`
- `path/to/file2`

## 3. 怎么验证
- 检查项 1
- 检查项 2

## 4. 已知问题
- 问题 A
- 问题 B

## 5. token 消耗（由主控记录）
- 说明：token 消耗由**主控**在 `sessions_yield` 收到本子代理 completion event 时，从事件末尾 Stats line 提取 `Token usage`（input/output/total）记录，**子代理无需也回传不了自己的 token**（sessions_spawn 返回值无 stats 字段，教训 #256）

## 6. 下一步
- 阶段 X 的预期任务

## 6. 状态机更新（status.md 对应行）

- 本文由论衡 AI 写作流水线生成
- 核心论点：主人原创洞察（任务简报第 X 行）
- 检索证据：全部真实（[Lxx]/[Dxx]/[Cxx] 编号可追溯）
```

---

**精简版结束**

> 完整版（含文末四节完整性自检）见 [`交接报告-template.md`](交接报告-template.md)