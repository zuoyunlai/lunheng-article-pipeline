> 版本：v2.13.0（自动同步 2026-09-24）
> 🌐 **语言政策**：产出语言由 Phase 0「目标语言」字段**显式选择**（中文 / English / 中英混 / 其他，**不设默认**），全流程以该字段为准；中文特化（G14 中文 AI 痕迹检测 / GB/T 7714-2015 引用规范）为**可选能力**，不构成使用者语种限制。

# 主张—证据初始映射表

> E1-0 模板 v2.13.0-E1-0（2026-09-24）
> 对象、字段和枚举唯一真源：[`../_shared/真源/evidence-object-model.md`](../_shared/真源/evidence-object-model.md)
> 责任边界：T4 负责初始映射；最终关系核验由 T7/T8 按既有审计职责完成。

## 项目元数据

- 项目：
- 映射阶段：T4
- 当前稿件版本：
- 映射时间：
- 证据登记表：`run/<项目名>/research/evidence-register.md`

## 使用规则

1. 每个核心正文主张使用唯一 `claim_id`，格式如 `C-001`。
2. `evidence_id` 必须先在证据登记表中存在；不可用正文引用临时代替证据对象。
3. `directly_supports` 不是自动放行标记，仍须符合 G15 的措辞—证据双轴。
4. `indirectly_supports` 必须填写限定语或降级措辞。
5. `contextualizes` 只能用于背景、概念或文献对话，不得写成直接证明。
6. `qualifies` 与 `contradicts` 不得静默删除；需在讨论或局限性中处理。
7. `insufficient` 不得支撑正文主张；空证据或未核验关系不得进入定稿候选。
8. `abstract_only` 不得写成全文研究显示；`metadata_only` 只能证明身份/元数据。

## 映射表

| Claim ID | 分析主张（原句或准确摘要） | Evidence ID | Source ref | 初判关系 | 证据类型 | 证据访问状态 | G15 causal_force | G15 evidence_force | 建议措辞/限定语 | 缺口 | T4 状态 |
|---|---|---|---|---|---|---|---:|---:|---|---|---|
| C-001 | （示例）算法治理与个体选择空间相关 | E-001 | [L01] | indirectly_supports | abstract | abstract_only | 2 | 2 | 「与……相关」 | 缺直接原文 | needs_review |
| C-002 | （示例）平台依赖度逐年上升 | E-002 | [D01] | directly_supports | results | available | 3 | 4 | 直接引用数据 | 需核对时间范围 | needs_review |
| C-003 | （示例）存在反向案例 | E-C01 | [C01] | contradicts | body | available | 1 | 3 | 交 T6/T7 处理 | 反方未回应 | needs_review |

## 未绑定主张

| Claim ID | 主张 | 是否核心主张 | 缺口 | 处置建议 |
|---|---|---|---|---|
| C-004 | （示例）尚无证据支撑的推断 | 是 | 无证据 | 建议降级措辞或补检索 |

## 映射完成前自查

- [ ] 每个核心主张均有唯一 Claim ID
- [ ] 每个 Evidence ID 均存在于证据登记表
- [ ] 每个 Source ref 均能回指文献/数据/案例卡
- [ ] `relevance_score` 未被当作证据强度
- [ ] `abstract_only` / `metadata_only` 限制已保留
- [ ] 间接证据已填写限定语或降级措辞
- [ ] 反向证据已登记且未静默删除
- [ ] 未绑定核心主张已列入上表
- [ ] T4 只做初判，未冒充 T7/T8 最终审计
