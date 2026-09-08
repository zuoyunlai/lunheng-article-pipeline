# 论衡 v2.9.1 发布说明

**发布日期**：2026-09-08

## 概述

v2.9.1 响应腾讯 AIG 安全审计建议，实施三项纵深防御改进，强化论衡流水线的安全性和可靠性。

## 新增功能

### 1. 宿主工具 denylist 预检（AUDIT-1）

**位置**：Phase 0（任务简报确认后、首次 spawn 前）

**功能**：
- 读取 `tools.subagents.tools.deny` 配置
- 列表为空 → 告警 + 人在环确认（纵深防御可选，不强制阻断）
- 设计原则：告警而非阻断，不替代平台配置

**参考文档**：`references/agents/00-主控-扩展职责.md` § 十五点五

---

### 2. Canonical 路径校验（AUDIT-2）

**适用角色**：所有角色（T1-T9）

**功能**：
- 所有文件写入前强制校验路径
- 拒绝：绝对路径 / 路径遍历（`..`）/ 符号链接逃逸
- 校验失败 → 记录错误 + 人在环介入

**工具**：
- `scripts/path-canonical.py`：路径校验脚本
- `scripts/test-path-canonical.sh`：测试套件（12/12 通过）

**调用示例**：
```bash
canonical=$(python3 scripts/path-canonical.py "run/<项目>" "<目标路径>")
if [[ $? -eq 0 ]]; then
    echo "内容" > "$canonical"
else
    echo "Error: Path validation failed" >&2
    exit 1
fi
```

**参考文档**：`references/_shared/路径校验规范.md`

---

### 3. Spawn 前能力断言（AUDIT-3）

**适用角色**：主控（T0）

**功能**：
- 每次 spawn 子代理前断言所需能力
- 白名单：read/write/edit + 搜索 + memory/ov + sessions + ask_user + 图像
- 明确禁止：exec/process/terminal/secrets/browser/portal/nodes/gateway/automations
- 校验失败 → 人在环介入

**工具**：
- `scripts/capability-assert.py`：能力断言脚本
- `scripts/test-capability-assert.sh`：测试套件（16/16 通过）

**调用示例**：
```bash
python3 scripts/capability-assert.py T1 read web_search tavily_search
# 输出: ✅ Role T1: All capabilities valid (3 total)
```

**参考文档**：`scripts/capability-assert.py` 顶部文档注释

---

## Bug 修复

### 修复 build-clawhub-release.sh pipefail 陷阱（教训 #213）

**根因**：`set -o pipefail` + `grep` 无命中返回 1 → 脚本提前退出

**修复**：`hits=$({ grep ... || true; } | wc -l)` 保护所有残留扫描 pattern

**验证**：v2.9.1 净化包生成正常，exit 0，0 残留

---

## 技术指标

- **净化包大小**：816K / 72 文件（+4626 bytes vs v2.9.0）
- **测试覆盖**：
  - 路径校验：12/12 通过
  - 能力断言：16/16 通过
  - 净化脚本：0 残留

---

## 教训记录

**#210 - 安全审计响应：纵深防御 + 人在环介入**

关键原则：
- 告警而非阻断：论衡有执行韧化协议，宿主 denylist 是纵深防御
- 不替代平台：论衡不能代替 OpenClaw 配置 allowlist
- 人在环介入：所有安全校验失败 → 记录 + 告知 + 等待决策

---

## Git 提交

- `df3261b` fix: 修复 build-clawhub-release.sh pipefail 陷阱 + 剥离开发者文件
- `0f0fce9` feat(v2.9.1): 实施腾讯 AIG 安全审计三项改进

---

## 升级指南

### 从 v2.9.0 升级

1. **更新技能包**：
   ```bash
   clawhub publish outputs/clawhub-release/2.9.1 \
     --slug lunheng-article-pipeline \
     --version 2.9.1 \
     --name "论衡 — 严肃长文流水线"
   ```

2. **（可选）配置宿主 denylist**：
   编辑 `~/.openclaw/openclaw.json`：
   ```json
   {
     "tools": {
       "subagents": {
         "tools": {
           "deny": ["exec", "process", "terminal", "secrets"]
         }
       }
     }
   }
   ```

3. **验证安全改进**：
   - Phase 0 应显示 denylist 预检结果
   - 子代理写文件前自动调用路径校验
   - 主控 spawn 前自动执行能力断言

---

## 下一版本预告（v2.10.0）

计划优化项：
- P1-3 外置详细说明（22% tokens 优化）
- 增量 M 门增强：章节级变更检测
- T4→T5 准并行优化

---

## 审计溯源

- **审计报告**：腾讯 AIG v2.9.0 安全审计（2026-09-08）
- **响应报告**：`outputs/论衡v2.9.0-腾讯AIG安全审计响应.md`（待创建）
- **采纳矩阵**：Remediation #2/#5/#6 采纳，#1/#3/#4/#7 不采纳（原因见响应报告）

---

## 联系方式

- **项目仓库**：https://github.com/zuoyunlai/lunheng-article-pipeline
- **ClawHub**：https://clawhub.org/skills/lunheng-article-pipeline
- **主人**：左运来（东莞老左设计研发工作室）
