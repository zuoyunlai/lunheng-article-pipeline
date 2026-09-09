# status 模板（精简版）

> **精简版**：只保留骨架，详细说明见 [`status-template.md`](status-template.md)

```markdown
# Status

> **位置**: `run/<项目名>/status.md`
> **使用**: 每个角色更新

## 当前状态

- 🔄 In Progress / ✅ Done / ❌ Failed
- 角色: T1 / T2 / **T3** 案例检索/ T4 分析/ T5 写手/ T6 批判/ T7 审计/ T8 终检主控亲完成
- 启动时间: YYYY-MM-DD HH:MM
- 当前模型: deepseek-v4-pro

## 执行韧化记录

- 启动心跳: ✅
- 中途 ACK: ✅ / N/A
- 超时硬卡（角色分级）: 未触发 / 已 kill

## 修订回环记录

- v1 → v2: [日期 + 修改内容]
- v2 → v3: [日期 + 修改内容]
- 归档中间态到 archive/
```

---

**精简版结束**

> 完整版见 [`status-template.md`](status-template.md)