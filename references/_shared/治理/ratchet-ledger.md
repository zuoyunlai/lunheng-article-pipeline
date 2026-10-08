# 体量棘轮台账（v2.15.9 新增 —— 给「只许降」装上可审的账本）

> **版本**：v2.15.9（自动同步 2026-10-03）

> 🌐 **语言政策**：产出语言由 Phase 0「目标语言」字段**显式选择**（中文 / English / 中英混 / 其他，**不设默认**），全流程以该字段为准；中文特化按**目标语言客观适用**——含中文时 **G14 中文 AI 痕迹闸必跑**（v2.12.40 起不再是可选项），纯外语时记 `n/a`（客观不适用，非「关闭」）；GB/T 7714-2015 引用规范为可选能力。二者均不构成使用者语种限制。

## 为什么需要本台账

2026-10-03 全量审计 P1 结论：门 Y 的「只许降」棘轮**存在合法上涨通道**。v2.15.8 以「按实测重定」把扩展职责卡 69808→74923 B、phase-order.yaml 63928→66574 B——规则文本说的是「后续仍只许降」，但**重定动作本身不受任何机制约束**：只要在注释里写一句「功能性新增」，涨上去就永久合法。B1-B7、v2.12.65、v2.12.70、v2.12.72、v2.13.5、v2.13.6、v2.15.7 已连续使用该通道（见门 Y 脚本内注释）。

本台账把「重定」从**豁免**变成**债务**：每次上涨必须登记，且**必须承诺回落目标与期限**；门 Y 机器校验债务未过期。

## §一、债务台账（唯一真源；门 Y 逐条校验）

```yaml
# 字段：path | 上涨日期 | 旧上限 | 新上限 | 回落目标 | 截止版本 | 状态
# 状态枚举：open（未回落，门 Y 校验截止版本未到）| settled（已回落，须留 settled_at）
# 「回落目标」语义：下次触达该文件时必须 ≤ 本值；不得再次上调（三次上调即须走分层，见 §三）
# 机械变长豁免（2026-10-06 方案 A）：版本戳类 +1 B（§二 version_stamp_lengthening）不计入本比对
debt:
  - path: "references/agents/00-主控-扩展职责.md"
    raised_at: "2026-10-02"
    from: 69808
    to: 70189
    settle_to: 70189
    due_version: "2.18.0"
    status: "settled"
    settled_at: "2026-10-03 (v2.15.9)"
    reason: "v2.15.7 功能性新增 74923；v2.15.9 外移 §二十二 主动介入机制 -> _shared/真源/主动介入机制.md，回落至 70189（-4734 B，与 v2.15.9 tag 实测一致；原记 70039/-4884 系笔误）"
  - path: "references/_shared/真源/phase-order.yaml"
    raised_at: "2026-10-02"
    from: 63928
    to: 70860
    settle_to: 63928
    due_version: "2.18.0"
    status: "open"
    reason: "v2.15.7 新增 post_phase1_dispatch_verify 节点（装配视图为生成物，无分层可选）；2026-10-05 上午 R2 契约真源化 66574→68238（派发/轮次契约字段，**该轮漏登记，本轮补登**）+ 同日 T9b 降级 opt-in 68238→69293（opt-in 契约字段）+ 发版 v2.15.10 版本戳变长 69293→69294；均未销账，故累加至原 open 行而非新开行；2026-10-07 v2.15.13 反哺修订 69294→70860（FB-12 四 checkpoint blocks 局部阻塞 + FB-11 t9 quota_class_retry/cross_family_retry/缺失呈现三要素，装配视图为生成物，无分层可选，累加同一 open 行）"
  - path: "references/_shared/真源/phase-order/index.yaml"
    raised_at: "2026-10-02"
    from: 24767
    to: 25359
    settle_to: 24767
    due_version: "2.18.0"
    status: "open"
    reason: "v2.15.7 同上（契约段随节点新增）；2026-10-05 T9b 降级 opt-in：condition_definitions 键改名 owner_stress_test_opt_out→owner_stress_test_opt_in + 备案注；发版 v2.15.10 版本戳变长 25358→25359"
  - path: "references/agents/00-主控-扩展职责.md"
    raised_at: "2026-10-05"
    from: 70189
    to: 70278
    settle_to: 70189
    due_version: "2.18.0"
    status: "open"
    reason: "T9b 极性说明行改写（默认触发 + opt-out -> 默认不跑 + opt-in，含 status 留痕口径）+ 发版 v2.15.10 版本戳变长 70277→70278"
  - path: "references/_shared/真源/M-Gate-核心.md"
    raised_at: "2026-10-07"
    from: 77527
    to: 78090
    settle_to: 77527
    due_version: "2.18.0"
    status: "open"
    reason: "v2.15.13 反哺 FB-13：可复核判定协议四字段扩为五字段（新增 basis: mechanical|llm 证据类型二分 + 交付说明分组呈现口径，+563 B 纯功能性新增，非膨胀；无分层可选——basis 字段属判定协议本体）"
  - path: "references/_shared/真源/phase-order.yaml"
    raised_at: "2026-10-08"
    from: 70860
    to: 75003
    settle_to: 70860
    due_version: "2.18.0"
    status: "open"
    reason: "审计 R-5（fail-closed 收口）：`pre_spawn_enforcement.precondition` 增「模型路由 `phase0_route` 段且 `selected_by=owner`；缺记录或 selected_by 为空 = 判 path_or_param_error」判据，废除 route_tier.md「无记录 = 走默认链」尾部。**2026-10-08 批次 2 R-1（B1）累加**：Phase 1.5 拆两个求值点，新增节点 `phase1_5b_post_t2_5_review`（seq 6，排在 t2_5_integrity 之后），节点数 26→27 ⇒ 装配视图 71724→75003（+3279 B）。两次上调均为判据本体（非注释），装配视图为生成物、**无分层可选**（分层 = 改真源切片）。**⚠️ 本行已累计 2 次上调（70860→71724→75003），按 §四-3 铁律额度用尽：后续新增内容一律沉入旁侧真源，不得再堆进本文件**。本行 = 该 path 第 2 条 debt（第 3 条按铁律不再受理）"
  - path: "references/_shared/真源/phase-order/index.yaml"
    raised_at: "2026-10-08"
    from: 25359
    to: 26813
    settle_to: 25359
    due_version: "2.18.0"
    status: "open"
    reason: "审计 R-6（重开链依赖序修正）：`terminal_freeze.doctrine` 原序 `g14_style_gate / t9_review / final_assembly / t8_technical_final` 与 `t9_review.input = final/定稿.md`（phase_seq 21 > final_assembly 20）**矛盾** —— 按原序执行等于让盲审读**旧版定稿**，重跑形同虚设。改为依赖序 `current_draft_sync(有改时) → g14_style_gate → phase4_4_figures/final_assembly(含 g14_caption_recheck) → t9_review → t8_technical_final`，并注明 T9 受审对象指纹须与重开后定稿一致。**2026-10-08 批次 2 R-1（B1）累加**：`nodes:` 路由表插入 `phase1_5b_post_t2_5_review`（seq 6）并整体重编号，26→27 ⇒ 25909→26813（+904 B）。无分层可选（顶层 terminal_freeze 为跨阶段共享不变式，不属可外移的节点体）。**⚠️ 本行已累计 2 次上调（25359→25909→26813），§四-3 铁律额度用尽**。本行 = 该 path 第 2 条 debt"
```

## §二、豁免类（结构性变更，走 §二 而非 §一）

**语义**：以下情形**不属于**「内容膨胀」，但仍须登记。**默认只允许发生一次**（第二次同类变更必须改走分层/外移）；**唯一例外 = `version_stamp_lengthening`（发版机械变长）—— 按发版频率豁免，不计入 §四-3 三次上调铁律，也不计入 §一 债务的 settle_to 比对**（2026-10-06 方案 A 定案，解 R-1 自相矛盾）。

```yaml
structural_exempt:
  - kind: "path_prefix_lengthening"
    note: "v2.12.70 分层后 _shared/ 前缀 +3 字节/引用 —— 机械变长，非内容膨胀"
  - kind: "assembly_restore"
    note: "v2.13.5 R-21 装配从 YAML 重打改逐字拼接 —— 把上游本就存在的文本还原回来"
  - kind: "version_stamp_lengthening"
    note: "发版时 `sync-version.sh` 把四个必读文件的版本头改号，每处 +1 B —— 机械变长，非内容膨胀。**豁免口径（2026-10-06 方案 A 定案）**：本类**按发版频率豁免**，不计入 §四-3 三次上调铁律、不计入 §一 settle_to 比对；每次发版仍由门 Y 逐字节校验（ceils 随实测同步），但**不再登记为内容债务**。"
  - kind: "version_stamp_lengthening（实例，已自 §一 移出）"
    note: "2026-10-05 v2.15.10：`references/_shared/真源/M-Gate-核心.md` 77526→77527 B，**纯发版版本戳 +1 B、零内容变更** —— 原登记为 §一 debt（settle_to 77526 物理上永不可达），2026-10-06 方案 A 移出为记录。"
```

> **判据**：本表只作**记录**，不参与门 Y 判定；新增豁免类条目需在本文件写清「为什么不是内容膨胀 + 为什么不能分层解决」。

## §三、门 Y 校验规则（v2.15.9 增补）

1. **上限逐字节等于实测**（现行规则，保留）：`ceils[path] == filesize(path)`。
2. **上涨必须有台账行**（新增）：若上限高于该 path 在台账中最近一次记录值 → 必须有对应 `debt` 行，否则门 Y 告警「未登记的重定」。
3. **债务不得过期**（新增）：`status: open` 且当前版本 ≥ `due_version` → 门 Y 硬告警（计入 `BULK_RATCHET_DEBT_EXPIRED`，终局汇总点名）。**豁免**：机械变长（§二 `version_stamp_lengthening`）不登记为 §一 债务，故不受本条与 §四-3 约束。
4. **零债务优先**：`debt` 全为 `settled` 时，门 Y 输出「棘轮无未结债务」。

## §四、更新纪律

1. **上涨 = 记账**：任何上调必须同批写 `debt` 行（含 settle_to + due_version）；不写 = 门 Y 点名。**例外**：§二 `version_stamp_lengthening`（发版机械 +1 B/文件）按频率豁免，只随 `ceils` 同步、不写 debt 行。
2. **回落 = 销账**：把 `status` 改 `settled` 并加 `settled_at`（日期 + commit）；`ceils` 与实测同步下调。
3. **三次上调铁律**：同一 path 历史上第 3 次 `debt` 行 → 必须改走分层/外移，**不再接受重定**（本台账按 `path` 计数）。
4. **due_version 建议**：不超过当前 minor + 2（如当前 2.15.x → 至多 2.18.0）。
5. 本文件随包**排除**（维护者侧，与 `lessons-max.snapshot` / `lessons-registry.md` 同侧）。

## §五、当前状态速览

| 文件 | 当前上限 | 未结债务 | 回落目标 | 截止 |
|---|---|---|---|---|
| 00-主控-扩展职责.md | 70278 | 1 | 70189 | 2.18.0 |
| phase-order.yaml | 75003 | 2 | 70860（另有一条历史 open 行 settle_to 63928） | 2.18.0 |
| phase-order/index.yaml | 26813 | 2 | 25359（另有一条历史 open 行 settle_to 24767） | 2.18.0 |
| M-Gate-核心.md | 78090 | 1 | 77527 | 2.18.0 |

> **合计未结债务**：**6 条**（v2.15.7 批次 1 条；T9b 降级 + 发版重定批次 2 条；v2.15.13 反哺 1 条；2026-10-08 审计批次 1「契约自洽」新增 2 条）。
> **棘轮余量提示（2026-10-08 更新）**：`phase-order.yaml` 与 `phase-order/index.yaml` 的 §四-3 上调额度**已用尽**（各累计 2 次：70860→71724→75003 / 25359→25909→26813，第 3 次按铁律不再受理）。**批次 2 剩余项（R-2 状态真源收敛、R-9 blocks 门）的新增内容一律沉入旁侧载体**（`status-template.md` / `scripts/flow-check.py` / 专项测试），不得再堆进这两个契约文件。
> **机械变长豁免（2026-10-06 方案 A）**：`M-Gate-核心.md` 原第 4 条债务为**纯发版版本戳 +1 B**，已按 §二 `version_stamp_lengthening` 豁免口径移出为记录 → 未结债务 4 → 3 条。
