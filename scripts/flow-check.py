#!/usr/bin/env python3
"""论衡流程图检查（v2.12.28 新增；v2.12.30 扩；v2.12.37 扩；v2.12.40 扩；v2.12.49 扩；v2.12.51 扩）

检查项：
  1 引用有效性（next / after_trigger / after_each / **on_fail** 指向已知节点或 rerun_* 动作）
  2 可达性（无孤立节点；**v2.12.40：出口边 on_fail 计入可达性**）
  3 除终态外须有 next
  4 入参类节点须声明 input（agent / owner_agent / parallel_agents / conditional_agent /
    advisory_agent / bounded_loop / conditional_review_window）
  5 执行类节点须声明 output（同上，去掉 conditional_review_window）
  6 入参链闭合：**每个被消费的受管路径**都必须有节点以 output 生产
    （v2.12.37 取消原「≥2 消费者」前提 —— 单消费者路径同样逃检）
  7 YAML 重复键**硬失败**（后键静默覆盖前键 = 真源失真）
  8 条件节点须声明未触发处置（on_not_triggered / degrade / decisions）
  9 初稿生产者到 t7_audit 的路径必须经过 current_draft_sync
 10 **verdict_scale 接线**（v2.12.40 修 P0-1）：节点引用的档位名必须在顶层有同名定义，
    且定义含恰好 4 档 + `default_handling` 四档全覆盖 —— 防「声明四档却无处置」的 fail-open。
 11 **Phase 编号**（v2.12.46）：每个节点须声明 `phase` + `phase_seq`；seq 全局唯一且与顶层
    `phase_order` 一致；沿 next/after_trigger/on_fail 边**序号不得回退**（after_each 为重跑动作，不计）。
 12 **人环闸门声明**（v2.12.49，修 P2-1 / P2-2）：顶层 `owner_checkpoints` 与 `kind: owner_checkpoint`
    节点集必须**双向一致**；每个此类节点须声明 `blocking: true` + `owner_visible: true` + 非空 `decisions`
    + `timeout_fallback`，且该取值须在顶层 `owner_timeout_policy.fallback_kinds` 中有定义。
    防两类缺口：①「人环闸门只写在散文、真源不承载」；②「无应答静默自动推进」（fail-open）。
 13–22 **v2.12.49 M / T 系列规则**（逐条标题见脚本内联注释）：终态冻结 / 交付物指纹 /
    审计对象一致 / 计数类档位 + P2 量化锚点 / 轮次耗尽出口三选一 / G14 严重度 /
    status 对账 + 48 必查严重度列 / 图件路径 + 图位决策 / 主人操作清单 + 字数口径 / T 系列全项。
 23 **只读档写权**（v2.12.51 D-3）：`pipeline` 中 `role ∈ {T6, T7, T9, G14}` 且 `kind` 属
    agent 类（`agent` / `conditional_agent` / `advisory_agent`）的节点，`write_authority`
    必须为 `owner` —— 只读档工具面仅 `read`，报告正文随交接回传（final message）、
    由主控 `write` 落盘，本节点不授写权（v2.12.32/v2.12.33「两径定义」= 已废止口径）。
 24 **全景一致性**（v2.12.54 R-1）：全景**收敛为唯一一份派生视图**（`panorama_sources.canary`），
    须完整承载全部节点 id 且首现顺序 = `phase_seq`；`mirrors` 列出的文档**必须已删除全景段**
    （不含 `section_marker`）且**含指针串** —— 防「11 份文档各写一套全景、无一与真源一致」复发。
 30 **盲审禁主控代笔**（v2.12.55 S-2）：`independence: blind_review` 的节点**不得**声明通用 fallback
    （`on_worker_failure.executor: 主控`），必须声明 `independence_failure_policy`
    （`executor_takeover: forbidden` + `on_exhausted: record_missing_and_notify_owner` + 正整数 `retry_limit`）
    —— 主控已读遍全部内部材料，代笔即独立性归零且事后不可修复。
 31 **同 provider 连续静默升级**（v2.12.55 S-3）：顶层 `provider_silence_escalation` 必须存在且为
    「≥3 次 / `scope: same_provider` / 三选一无默认 / `halt_pending_owner: true`」，且主控角色卡
    必须承载同一协议（真源 ↔ 角色卡双向接线）—— 防「静默继续」与「只写在散文」。
 40 **跨状态机「静默 ≠ 有效决策」与 HITL 留痕一致性**（v2.12.65 / v2.13.2）：顶层 `silence_doctrine` 是
    「静默/无应答 ≠ 有效决策 ⇒ 挂起等主人 + 无默认继续」的**单一真源**，并锁定呈现后的可恢复留痕协议
    （`halt_kinds` 挂起类处置唯一枚举 / `forbidden_kinds` fail-open 枚举 / `applies_to` 覆盖面）。
    本规则做**双侧投影 + 双向对账**：`owner_timeout_policy` 的无应答处置必须全落 `halt_kinds`
    且 `default_fallback ∈ halt_kinds`、各 `owner_checkpoint.timeout_fallback ∈ halt_kinds`；
    `provider_silence_escalation` 必须 `halt_pending_owner: true` + `no_default_option: true`
    且 `owner_choices` 无默认项；两侧挂起态**必须相等**（一侧挂起/一侧自动继续 = 不同侧，报红）。
    防「改 A 漏 B」：侧语义只在散文声明时，只改一侧不会报红。
 41 **M-13 清单跨载体一致性**（v2.12.66）：T8 dispatch 与 08-终检 是**同一份**「主人自行操作建议
    清单」的两个载体。两处四类动作名必须齐备；两处「可直接复制的命令模板」必须**彼此相等**且与
    声明真源 `_shared/真源/format-export.md` §二 同源（含 `.tex` 行 + `--reference-doc=academic-paper-template.docx`
    + `--bibliography` / `--csl`）；禁 v2.12.60 已作废写法回潮（`templates/word-reference.docx` /
    「再嵌入定稿」—— 图位嵌入由 `final_assembly` 在流水线内完成，主人只做 SVG→PNG）。
    防「同一份清单两处承载、改 A 漏 B」（与 P1-1 轻量档口径 / P1-2 路径边界同族）。
 42 **只读档报告分片预申报接线（v2.12.67，审计 P1-1）**：`执行韧化协议-exec.md`（真源）与 T6/T7/T9/G14
    四个 dispatch 载体必须同时含「分片清单」与「报告分片 N/M」口径——超长报告回传协议不得从任何
    载体静默消失（#427 同族）；触发线 3500 的数值真源在协议本体，本规则只锁存在性（防双判据漂移）。
用法：python3 scripts/flow-check.py  → 无输出=通过；有输出=问题列表（分号分隔）。"""
import json, pathlib, re, sys, yaml
from collections import deque

# 执行类节点：产出受管产物，必须 input + output
EXEC_KINDS = (
    'agent', 'owner_agent', 'parallel_agents', 'conditional_agent',
    'advisory_agent', 'bounded_loop',
)
# 入参类节点：只需 input
INPUT_KINDS = EXEC_KINDS + ('conditional_review_window',)

# 路径 token：必须含目录分隔符，扩展名 ∈ md/svg/json/yaml（保守匹配，宁少勿误报）
PATH_RE = re.compile(r'[A-Za-z0-9_\-\u4e00-\u9fff]+/[A-Za-z0-9_\-\u4e00-\u9fff/{}.+*]+\.(?:md|svg|json|yaml)')
# 目录型产物（如 final/图件/）：用于「目录产出覆盖其下通配消费」的前缀匹配（v2.12.41）
DIR_RE = re.compile(r'\b(?:final|drafts|audits|analysis|literature|data|cases|run)/[A-Za-z0-9_\-\u4e00-\u9fff/]*/')


class UniqueKeyLoader(yaml.SafeLoader):
    """重复键 → 失效（ConstructorError），不静默取后键。"""


def _no_dup_keys(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None, None,
                f'duplicate key {key!r} at line {key_node.start_mark.line + 1}',
                key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup_keys)


def _norm(tok):
    """版本占位归一：初稿-v{N}.md / 初稿-vN.md / 初稿-v1.md → 初稿-v#.md"""
    return re.sub(r'-v(?:[0-9N]+|\{N(?:\+[0-9]+)?\})', '-v#', tok)


def _paths(decl):
    """从声明（字符串 / 列表 / 映射）中抽出归一路径集合"""
    if decl is None:
        return set()
    if isinstance(decl, dict):
        return set().union(*[_paths(v) for v in decl.values()]) if decl else set()
    if isinstance(decl, (list, tuple)):
        return set().union(*[_paths(v) for v in decl]) if decl else set()
    out = {_norm(m) for m in PATH_RE.findall(str(decl))}
    out |= {m for m in DIR_RE.findall(str(decl))}
    return out


def main():
    p = pathlib.Path(__file__).resolve().parent.parent / 'references/_shared/真源/phase-order.yaml'
    try:
        d = yaml.load(p.read_text(encoding='utf-8'), Loader=UniqueKeyLoader)
        P = d['pipeline']
    except yaml.YAMLError as e:
        print(f'ERR:phase-order.yaml 解析失败（含重复键） {e}')
        return 1
    except Exception as e:
        print(f'ERR:phase-order.yaml 解析失败 {e}')
        return 1
    ids = [n['id'] for n in P]
    errs = []

    # 条件名称必须在顶层集中定义，避免只靠节点注释解释而产生漂移。
    condition_defs = d.get('condition_definitions') or {}
    for n in P:
        condition = n.get('condition')
        if condition and condition not in condition_defs:
            errs.append(f"{n['id']}.condition->{condition}（顶层无定义）")

    for n in P:                                    # 1 引用有效性（记录动作允许作为条件出口）
        for k in ('next', 'after_trigger', 'on_fail', 'on_not_triggered'):
            v = n.get(k)
            if isinstance(v, str) and v and not v.startswith(('rerun_', 'record_')) and v not in ids:
                errs.append(f"{n['id']}.{k}->{v}")
        for v in (n.get('after_each') or []):
            if isinstance(v, str) and v not in ids and not v.startswith('rerun_'):
                errs.append(f"{n['id']}.after_each->{v}")

    reach = set()
    def walk(i):                                   # 2 可达性（v2.12.40：on_fail 出口边也计入）
        if i in reach or i not in ids: return
        reach.add(i)
        for n in P:
            if n['id'] == i:
                for k in ('next', 'after_trigger', 'on_fail', 'on_not_triggered'):
                    v = n.get(k)
                    if isinstance(v, str) and v in ids:
                        walk(v)
    walk(ids[0])
    un = [x for x in ids if x not in reach]
    if un: errs.append('不可达:' + ','.join(un))

    for n in P:                                    # 3 除终态外须有 next
        if n['id'] != 'phase5_acceptance' and not n.get('next'):
            errs.append(f"{n['id']} 缺 next")

    for n in P:                                    # 4 入参类节点须声明 input
        if n.get('kind') in INPUT_KINDS and not n.get('input'):
            errs.append(f"{n['id']} 缺 input")

    for n in P:                                    # 5 执行类节点须声明 output
        if n.get('kind') in EXEC_KINDS and not n.get('output'):
            errs.append(f"{n['id']} 缺 output")

    consumers, produced = {}, set()                # 6 入参链闭合（v2.12.37：取消「≥2 消费者」前提）
    for n in P:
        produced |= _paths(n.get('output'))
        produced |= _paths(n.get('output_if_triggered'))
        for t in _paths(n.get('input')):
            consumers.setdefault(t, []).append(n['id'])
        for t in _paths(n.get('inputs')):
            consumers.setdefault(t, []).append(n['id'])
    dirs = sorted({t for t in produced if t.endswith('/')})   # v2.12.41：目录型产出覆盖其下通配消费
    for t, who in sorted(consumers.items()):
        if t in produced:
            continue
        if any(t.startswith(d) for d in dirs):
            continue
        errs.append(f'{t} 被 {",".join(who)} 消费但无生产者')

    for n in P:                                    # 8 条件节点须声明未触发处置
        if n.get('condition') and not (
                n.get('on_not_triggered') or n.get('degrade') or n.get('decisions')):
            errs.append(f"{n['id']} 有 condition 但缺 on_not_triggered/degrade/decisions")

    byid = {n['id']: n for n in P}                 # 9 初稿生产者必经 current_draft_sync 才可达 T7

    def _succ(nid):
        n = byid.get(nid)
        if not n:
            return []
        out = []
        # v2.13.0：after_each 边先于 next/after_trigger/on_fail 入队 —— 执行语义上「单次执行后动作」
        # 在阶段转移前发生；此前 next 排前会让 BFS 提前命中 t7_audit 而 break，
        # 永远看不到同一节点 after_each 里的 current_draft_sync（规则 9 对 {N+1} 产出节点全程失效）。
        for v in (n.get('after_each') or []):
            if isinstance(v, str) and v in byid:
                out.append(v)
        for k in ('next', 'after_trigger', 'on_fail'):
            v = n.get(k)
            if isinstance(v, str) and v in byid:
                out.append(v)
        return out

    for n in P:
        if 'drafts/初稿-v#.md' not in _paths(n.get('output')):
            continue
        seen, q, synced, reached_t7 = set(), deque([n['id']]), False, False
        while q:
            cur = q.popleft()
            if cur in seen:
                continue
            seen.add(cur)
            if cur == 'current_draft_sync':
                synced = True
            if cur == 't7_audit':
                reached_t7 = True
                break
            q.extend(_succ(cur))
        if reached_t7 and not synced:
            errs.append(f"{n['id']} 产出初稿但到达 t7_audit 的路径未经过 current_draft_sync")

    vs = d.get('verdict_scale') or {}               # 10 verdict_scale 接线（v2.12.40 修 P0-1）
    for n in P:                                     # 10a 引用未知名称 → 逐个点名
        name = n.get('verdict_scale')
        if name and (not isinstance(name, str) or name not in vs):
            errs.append(f"{n['id']}.verdict_scale->{name}（顶层无同名定义）")
    for name in sorted({n.get('verdict_scale') for n in P if n.get('verdict_scale')}):  # 10b 定义块自检（去重）
        if not isinstance(name, str) or name not in vs:
            continue
        blk = vs[name] or {}
        tiers = [t.get('id') for t in (blk.get('tiers') or []) if isinstance(t, dict)]
        if len(tiers) != 4 or len(set(tiers)) != 4:
            errs.append(f"verdict_scale.{name} 档位数≠4: {tiers}")
        dh = blk.get('default_handling') or {}
        miss = [t for t in tiers if t not in dh]
        if miss:
            errs.append(f"verdict_scale.{name}.default_handling 缺档位: {miss}")

    po = d.get('phase_order') or []                # 11 Phase 编号（v2.12.46）
    seq_map = {}
    for n in P:
        if not n.get('phase') or not isinstance(n.get('phase_seq'), int):
            errs.append(f"{n['id']} 缺 phase/phase_seq")
            continue
        seq_map[n['id']] = n['phase_seq']
    if len(set(seq_map.values())) != len(seq_map):
        errs.append('phase_seq 重复（编号必须唯一）')
    listed = {e.get('node') for e in po if isinstance(e, dict)}
    if listed != set(ids):
        miss = sorted(set(ids) - listed)
        extra = sorted(listed - set(ids))
        errs.append(f"phase_order 与 pipeline 不一致（缺 {miss} / 多 {extra}）")
    for e in po:
        if not isinstance(e, dict):
            continue
        nid = e.get('node')
        if nid in seq_map and (e.get('seq') != seq_map[nid] or e.get('phase') != byid[nid].get('phase')):
            errs.append(f"phase_order[{nid}] 与节点声明不一致")
    for n in P:                                    # 沿前向边序号不得回退（after_each = 重跑动作，不计）
        a = seq_map.get(n['id'])
        for k in ('next', 'after_trigger', 'on_fail'):
            v = n.get(k)
            b = seq_map.get(v)
            if a is not None and b is not None and b < a:
                errs.append(f"{n['id']}(seq {a}).{k}->{v}(seq {b}) 序号回退")

    # 12 人环闸门声明（v2.12.49 修 P2-1/P2-2：阻断语义此前只活在散文，真源不承载）
    otp = d.get('owner_timeout_policy') or {}
    fb_kinds = otp.get('fallback_kinds') or {}
    if not isinstance(otp.get('no_answer_minutes'), int) or otp.get('no_answer_minutes') <= 0:
        errs.append('owner_timeout_policy.no_answer_minutes 缺失或非正整数')
    if otp.get('default_fallback') not in fb_kinds:
        errs.append(f"owner_timeout_policy.default_fallback 未在 fallback_kinds 中定义: {otp.get('default_fallback')}")
    ck_declared = list(d.get('owner_checkpoints') or [])
    ck_kind = [n['id'] for n in P if n.get('kind') == 'owner_checkpoint']
    if set(ck_declared) != set(ck_kind):
        errs.append('owner_checkpoints 与 kind: owner_checkpoint 节点集不一致'
                    f"（缺 {sorted(set(ck_kind) - set(ck_declared))} / 多 {sorted(set(ck_declared) - set(ck_kind))}）")
    for n in P:
        if n.get('kind') != 'owner_checkpoint':
            continue
        if n.get('blocking') is not True:
            errs.append(f"{n['id']}（owner_checkpoint）未声明 blocking: true —— 人环闸门不得可自动绕过")
        if n.get('owner_visible') is not True:
            errs.append(f"{n['id']}（owner_checkpoint）未声明 owner_visible: true")
        if not n.get('decisions'):
            errs.append(f"{n['id']}（owner_checkpoint）缺 decisions 枚举")
        fb = n.get('timeout_fallback')
        if fb not in fb_kinds:
            errs.append(f"{n['id']}.timeout_fallback->{fb}（未在 owner_timeout_policy.fallback_kinds 中定义）")

    # 13 终态冻结真源（v2.12.49 M-2）：phase5_acceptance 须声明 terminal；rerun_after_post_acceptance 拓扑检查
    tf = d.get('terminal_freeze') or {}
    p5a = byid.get('phase5_acceptance')
    if p5a is not None:
        if not p5a.get('terminal'):
            errs.append('phase5_acceptance 未声明 terminal（v2.12.49 M-2：终态真源缺失 → 终态冻结规则不能机械校验）')
        if p5a.get('terminal') == 'accepted':
            g14 = byid.get('g14_style_gate')
            if g14 is not None and not g14.get('rerun_after_post_acceptance'):
                errs.append('g14_style_gate 未声明 rerun_after_post_acceptance: true（M-2：终态后修改必须重跑 G14）')

    # 14 交付物指纹真源（v2.12.49 M-1）：声明 fingerprint: required 的节点必须同步可被消费者读到 audited_artifact
    #    机械门为下游报告必填字段（具体字段约束在 T8 / 交接报告模板层，不在此重复）；本规则保证 YAML 真源**双向一致**。
    fp_required = [n['id'] for n in P if n.get('fingerprint') == 'required']
    if 'final_assembly' in fp_required and 't8_technical_final' not in fp_required:
        errs.append('final_assembly 声明 fingerprint: required，但 t8_technical_final 未同步声明（缺一即下游不可机械断言）')
    for nid in fp_required:
        node = byid[nid]
        if not node.get('output'):
            errs.append(f"{nid} 声明 fingerprint: required 但缺 output（交付物路径缺失 → 无法绑定 sha256 真源）")

    # 15 审计对象一致真源（v2.12.49 M-8）：以下游只读档报告节点须声明 audited_artifact_required
    #    防止「节点靠散文约定做断言」漏检 — 形如 t7_5_integrity / t8_technical_final / t9_review 须显式声明
    #    audited_artifact_required: true；不声明 = 交付物可能被错路由读不到真源。
    required_audit = {'t7_5_integrity', 't8_technical_final', 't9_review'}
    missing = sorted(nid for nid in required_audit if byid.get(nid) and not byid[nid].get('audited_artifact_required'))
    if missing:
        errs.append(f'以下节点必须声明 audited_artifact_required: true（M-8）：{missing}')

    # 16 计数类档位真源 + P2 量化锚点（v2.12.49 M-3 + M-5）：
    #    M-Gate-Algorithm.md 与 字数判定表.md 是计数档位 + P2 量化锚点定义的双真源。
    #    机械门锁死两个文件必须同时声明 v2.12.49 新段（防其中一份走散文被另一个被丢）。
    m3_m5_required = [
        ('references/_shared/真源/M-Gate-Algorithm.md',
         '## 🎯 计数类档位真源 + P2 量化锚点'),
        ('references/_shared/真源/字数判定表.md',
         '实测 > 3 倍'),
    ]
    for rel, marker in m3_m5_required:
        text = (pathlib.Path(__file__).resolve().parent.parent / rel).read_text(encoding='utf-8') if (pathlib.Path(__file__).resolve().parent.parent / rel).exists() else ''
        if marker not in text:
            errs.append(f'{rel} 缺 v2.12.49 M-3/M-5 新段（“{marker[:30]}...”）——计数档位与 P2 量化锚点以两文件同时声明为锁死条件')

    # 17 M-6 轮次耗尽出口三选一真源（v2.12.49）：audit_revision 节点必须声明 rounds_exhausted_outlet
    #    且必须含 A/B/C 三选项 + no_default_option: true（防「默认接受 / 按最保守项继续」的 fail-open）
    ar = byid.get('audit_revision')
    if ar is not None:
        outlet = ar.get('rounds_exhausted_outlet')
        if not outlet:
            errs.append('audit_revision 缺 rounds_exhausted_outlet（M-6：轮次耗尽出口未锁死成机械门）')
        else:
            if outlet.get('no_default_option') is not True:
                errs.append('audit_revision.rounds_exhausted_outlet.no_default_option ≠ true（M-6：不得默认接受）')
            decisions = outlet.get('owner_decision') or []
            labels = [d.get('id') for d in decisions]
            for must in ('accept_with_limitations', 'extend_one_round', 'manual_polish'):
                if must not in labels:
                    errs.append(f'audit_revision.rounds_exhausted_outlet.owner_decision 缺「{must}」选项（M-6 三选一锁）')
            if outlet.get('halt_pending_owner') is not True:
                errs.append('audit_revision.rounds_exhausted_outlet.halt_pending_owner ≠ true（M-6：必须挂起不能自动 GO）')

    # 18 M-4 G14 严重度报告头锁死（v2.12.49）：g14 gate 文件必须声明 severe_single_class 报告头字段
    g14_path = pathlib.Path(__file__).resolve().parent.parent / 'references/gates/14-中文AI痕迹-gate.md'
    g14_text = g14_path.read_text(encoding='utf-8')
    if 'severe_single_class' not in g14_text:
        errs.append('14-中文AI痕迹-gate.md 缺 severe_single_class 报告头字段（M-4 严重度报告真源缺失）')
    if 'max(类数档判定, 单类严重度档判定)' not in g14_text and 'max(类数档, 单类严重度档)' not in g14_text:
        errs.append('14-中文AI痕迹-gate.md 未声明 max(类数档, 单类严重度档) 双轨判定（M-4 机械锁丢失）')

    # 19 M-9 48 必查严重度列 + M-7 status 对账锁死（v2.12.49）：
    #    M-9：可发表性判定表 §二 A-E 各表每行必含「严重度」字段（| P0/P1/P2/advisory **|）
    #    M-7：status-template §四产物路径每条必含节点 ID 标注（[节点: <id>]）
    fabiao = pathlib.Path(__file__).resolve().parent.parent / 'references/_shared/真源/可发表性判定表.md'
    fabiao_text = fabiao.read_text(encoding='utf-8')
    sev_in_section2 = sum(fabiao_text.count(f'**{sev}**') for sev in ('P0', 'P1', 'P2', 'advisory'))
    if sev_in_section2 < 17:   # A-E 17 行 × 严重度列必填（17 项中至少 14 P1 + 2 P2 + 1 P0 + 1 advisory）
        errs.append(f'可发表性判定表 §二 A-E 严重度列仅 {sev_in_section2} 处 < 17 行（v2.12.49 M-9 锁：每行必填严重度）')
    status_path = pathlib.Path(__file__).resolve().parent.parent / 'references/templates/status-template.md'
    status_text = status_path.read_text(encoding='utf-8')
    if 'M-7 状态对账机械真源' not in status_text or '[节点:' not in status_text:
        errs.append('status-template §四 缺 M-7 双向断言真源（产物 ↔ 节点机械门）')
    if 'final/定稿.sha256' not in status_text:
        errs.append('status-template §四 缺 final/定稿.sha256 字段（v2.12.49 M-1 交付物指纹）')

    # 20 M-10/M-11 图件路径与图位决策锁死（v2.12.49）：
    #    M-10：phase4_4_figures.output 须为 final/图件/*.svg（唯一归一路径）
    #    M-11：status-template §三 人在环决策段必含 figures + figure_decision 字段
    #    M-11：checkpoint-card-template.md 必含「图位决策必答」总注与三选项
    #    M-11：04-分析 T4 仅出建议不出一决定（建议 0 需主人拍板）
    pf4 = byid.get('phase4_4_figures')
    if pf4 is not None and pf4.get('output') != 'final/图件/*.svg':
        errs.append(f"phase4_4_figures.output ≠ 'final/图件/*.svg'（M-10 路径未归一）")
    if 'figures=' not in status_text or 'figure_decision=' not in status_text:
        errs.append('status-template §三 人在环决策段缺 figures + figure_decision 字段（M-11）')
    cpk_text = (pathlib.Path(__file__).resolve().parent.parent / 'references/templates/checkpoint-card-template.md').read_text(encoding='utf-8')
    if '图位决策必答' not in cpk_text or 'figure_decision' not in cpk_text:
        errs.append('checkpoint-card-template 缺 M-11 图位决策必答总注（Phase 2.5）')
    t4_text = (pathlib.Path(__file__).resolve().parent.parent / 'references/agents/04-分析-analyst.md').read_text(encoding='utf-8')
    if 'T4 不出一决定' not in t4_text and 'T4 **仅出建议**' not in t4_text:
        errs.append('04-分析-analyst 缺 M-11 T4 不出一决定声明（建议 ≠ 拍板）')

    # 20b M-11 图件**嵌入**锁（v2.12.60，主人 2026-09-19 裁定「图件如果存在要机械嵌入」）
    #    背景：M-11 原只锁「纯文本占位计数 = 拍板 N」，不锁嵌入 —— 实测 run 的定稿里
    #    `.svg`/`![` 引用数 = 0，3 张 SVG 躺在 final/图件/ 里「有图但文里看不到」。
    #    判据 = 三处载体（口径 / T8 卡 / T8 dispatch）必须同时含「嵌入式图位规范」与
    #    「嵌入计数」两件，否则这类口径会静默漂回纯占位版（改 A 漏 B 同型）。
    _root20 = pathlib.Path(__file__).resolve().parent.parent
    for _rel20, _lb20 in (('references/deliverables.md', 'deliverables'),
                          ('references/agents/08-终检-final-inspector.md', '08-终检'),
                          ('references/dispatch/T8-终检.md', 'T8 dispatch')):
        _t20 = (_root20 / _rel20).read_text(encoding='utf-8')
        if '![图N：标题](图件/图N_标题.svg)' not in _t20:
            errs.append(f'{_lb20} 缺嵌入式图位规范（M-11 图件嵌入锁 v2.12.60）')
        if '嵌入计数' not in _t20:
            errs.append(f'{_lb20} 缺「嵌入计数」口径（M-11 图件嵌入锁 v2.12.60）')

    # 21 M-13/M-14 主人操作清单 + 字数口径锁死（v2.12.49）：
    #    M-13：T8 dispatch 必含「主人自行操作建议清单」（三类动作 + 命令来源）
    #    M-14：任务简报模板必含 body_limit 字段（正文汉字数上限整数）；deliverables.md 必含「字数口径单一化」段
    #    M-14：08-终检-final-inspector 必含 M-14 段（body_char_count + body_limit 字段 + 复算断言）
    t8d_text = (pathlib.Path(__file__).resolve().parent.parent / 'references/dispatch/T8-终检.md').read_text(encoding='utf-8')
    if '主人自行操作建议清单' not in t8d_text or 'M-13' not in t8d_text:
        errs.append('T8 dispatch 缺 M-13 主人自行操作建议清单锁')
    jb_text = (pathlib.Path(__file__).resolve().parent.parent / 'references/templates/任务简报-template.md').read_text(encoding='utf-8')
    if 'body_limit' not in jb_text:
        errs.append('任务简报模板 缺 body_limit 字段（M-14 字数口径单一化）')
    deliv_text = (pathlib.Path(__file__).resolve().parent.parent / 'references/deliverables.md').read_text(encoding='utf-8')
    if '字数口径单一化' not in deliv_text or 'body_char_count' not in deliv_text:
        errs.append('deliverables.md 缺 M-14 字数口径单一化 + body_char_count 字段')
    t8r_text = (pathlib.Path(__file__).resolve().parent.parent / 'references/agents/08-终检-final-inspector.md').read_text(encoding='utf-8')
    if 'M-14' not in t8r_text or 'body_char_count' not in t8r_text:
        errs.append('08-终检-final-inspector 缺 M-14 段（body_char_count + body_limit）')

    # 22 T 系列治本锁死（v2.12.49）：
    #    T-1 上游落盘前置 + 派发禁摘要 + 差集断言字段
    #    T-2 换族优先 + 族级独立性 + 断路器；T-3 Phase 0 顶配档探活门
    #    T-4 审稿报告族级字段；T-5 修订净增上限；T-6 快照默认触发；T-8 引用体例单一化
    _R = pathlib.Path(__file__).resolve().parent.parent
    kp_text = (_R / 'references/_shared/真源/关键协议.md').read_text(encoding='utf-8')
    if '四·补' not in kp_text or '派发禁止摘要' not in kp_text:
        errs.append('关键协议 缺 §四·补 只读档报告落盘前置 + 派发禁止摘要（T-1）')
    jj_text = (_R / 'references/templates/交接报告-template.md').read_text(encoding='utf-8')
    if 'upstream_read' not in jj_text or 'dispatched_ids' not in jj_text:
        errs.append('交接报告模板 缺 upstream_read/dispatched_ids 差集断言字段（T-1）')
    cand_text = (_R / 'references/_shared/真源/模型候选池.md').read_text(encoding='utf-8')
    if '优先换 provider 族' not in cand_text or '断路器' not in cand_text:
        errs.append('模型候选池 缺 T-2 换族优先 + 断路器')
    if '二·补' not in cand_text or '探活门' not in cand_text:
        errs.append('模型候选池 缺 §二·补 顶配档探活门（T-3）')
    n_ps = byid.get('pre_spawn_enforcement')
    if n_ps is None or not n_ps.get('top_tier_liveness_gate'):
        errs.append('pre_spawn_enforcement 缺 top_tier_liveness_gate（T-3 探活门未入真源）')
    t9t_text = (_R / 'references/templates/审稿报告-template.md').read_text(encoding='utf-8')
    for _k in ('executor_model', 'model_family', 'independent_from'):
        if _k not in t9t_text:
            errs.append(f'审稿报告模板 缺 {_k}（T-4 族级独立性）')
    wc_text = (_R / 'references/_shared/真源/字数判定表.md').read_text(encoding='utf-8')
    if '修订净增上限' not in wc_text or 'net_delta_cjk' not in wc_text:
        errs.append('字数判定表 缺 §八 修订净增上限 + net_delta_cjk（T-5）')
    n_ms = byid.get('methodology_snapshot')
    if n_ms is not None and (n_ms.get('default') != 'triggered' or not n_ms.get('opt_out')):
        errs.append('methodology_snapshot 未改为「默认 triggered + opt_out」（T-6）')
    if '引用体例单一化' not in deliv_text:
        errs.append('deliverables.md 缺 T-8 引用体例单一化段')
    m_exist_text = (_R / 'references/_shared/真源/M-Gate-Algorithm.md').read_text(encoding='utf-8')
    if '引用体例层' not in m_exist_text:
        errs.append('M-Gate-Algorithm 缺 M-Exist-1 引用体例层校验（T-8）')

    # 23 只读档写权（v2.12.51 D-3）：T6 / T7 / T9 / G14 = 只读档（工具面仅 read），
    #    报告正文随交接回传（final message）、由主控 write 落盘 ⇒ 真源必须写 `write_authority: owner`。
    #    防回潮：v2.12.32/v2.12.33 的「两径定义」（自有报告可直写）曾把四节点改回 executor，
    #    与 10 处角色卡/dispatch 的「主控代写盘」口径互斥（v2.12.50 一致性审计 D-3）。
    READONLY_TIER_ROLES = {'T6', 'T7', 'T9', 'G14'}
    READONLY_TIER_KINDS = ('agent', 'conditional_agent', 'advisory_agent')
    for n in P:
        _role = n.get('role')
        if _role in READONLY_TIER_ROLES and n.get('kind') in READONLY_TIER_KINDS:
            if n.get('write_authority') != 'owner':
                errs.append(f"{n['id']}.write_authority->{n.get('write_authority')}"
                            f"（只读档 {_role} 报告由主控 write 落盘，不得授写权，应为 owner）")

    # 24 全景一致性（v2.12.54 R-1）：全仓只留一份派生全景，其余只留指针
    #    实测背景（2026-09-18）：11 份含 Phase 序列的文档无一与真源一致 —— pipeline-overview 缺 4 节点
    #    且 T7.5 门位置倒置、README 缺 7、pipeline-readme 缺 4、QUICKSTART 口径错 + 指针失效。
    #    全景是主控与主人的默认认知，缺节点 = 该节点在认知层不存在，故必须机械守。
    _root24 = pathlib.Path(__file__).resolve().parent.parent
    ps = d.get('panorama_sources') or {}
    canary_rel = ps.get('canary')
    marker = ps.get('section_marker')
    ptr = ps.get('pointer_target')
    exempt = set(ps.get('pointer_exempt') or [])
    if not canary_rel:
        errs.append('panorama_sources.canary 未声明（R-1：全景唯一派生视图缺失）')
    else:
        _cf = _root24 / canary_rel
        if not _cf.exists():
            errs.append(f'panorama_sources.canary 文件不存在: {canary_rel}')
        else:
            _ct = _cf.read_text(encoding='utf-8')
            if marker and marker not in _ct:
                errs.append(f'{canary_rel} 缺全景段标记“{marker}”（R-1）')
            _seq = {n['id']: n['phase_seq'] for n in P}
            _hits = {i: _ct.find(i) for i in ids}
            _miss = sorted(i for i, p in _hits.items() if p < 0)
            if _miss:
                errs.append(f'全景唯一派生视图 {canary_rel} 缺节点: {",".join(_miss)}（R-1）')
            else:
                _order = [s for _, s in sorted(((p, _seq[i]) for i, p in _hits.items()))]
                if _order != sorted(_order):
                    errs.append(f'全景唯一派生视图 {canary_rel} 节点首现顺序与 phase_seq 不一致（R-1）')
    for rel in (ps.get('mirrors') or []):
        _mf = _root24 / rel
        if not _mf.exists():
            errs.append(f'panorama_sources.mirrors 列出的文件不存在: {rel}')
            continue
        _mt = _mf.read_text(encoding='utf-8')
        if ptr and ptr not in _mt:
            errs.append(f'{rel} 缺全景指针串“{ptr}”（R-1：镜像文档只留指针）')
        if marker and marker in _mt:
            errs.append(f'{rel} 仍含全景段“{marker}”—— 应删除并改指针（R-1）')
    for rel in sorted(exempt):
        _ef = _root24 / rel
        if not _ef.exists():
            errs.append(f'panorama_sources.pointer_exempt 列出的文件不存在: {rel}')
            continue
        # exempt = 不承载全景、但允许出现节点级清单（如 status 阶段枚举 / 人环卡步骤映射）
        #    —— 免「必含指针串」与「id 计数上限」两项，但**仍禁全景段标记**（否则又是一份全景）。
        if marker and marker in _ef.read_text(encoding='utf-8'):
            errs.append(f'{rel} 含全景段“{marker}”（R-1：exempt 文件也不得承载全景段）')
    # 「重列」判据：节点 id 出现数 **> 12**（≥ 全集 23 的过半）才算重列 ——
    #   个别节点 id 的正当交叉引用（如 checkpoint-card 清单 / dispatch 指定节点）不计。
    for rel in (ps.get('mirrors') or []):
        _pf = _root24 / rel
        if not _pf.exists():
            continue
        _hit = [i for i in ids if i in _pf.read_text(encoding='utf-8')]
        if len(_hit) > 12:
            errs.append(f'{rel} 重列 {len(_hit)} 个节点 id（>12）—— 应改为指针（R-1）')

    # 25 条件字段生产方（v2.12.54 R-4）：condition_definitions 每条必须登记 `producer` + `producer_marker`，
    #    且 producer 文件存在、marker 确实出现在该文件中 —— 封掉「条件字段全仓无生产方 ⇒ 节点静默不触发」。
    #    实测背景（2026-09-18）：t9_review 依赖 owner_peer_review_consent，而全仓无任何生产方 ⇒ T9 整节点消失。
    for cname, cdef in (condition_defs or {}).items():
        if not isinstance(cdef, dict):
            errs.append(f'condition_definitions.{cname} 不是映射（R-4）')
            continue
        _p = cdef.get('producer')
        _m = cdef.get('producer_marker')
        if not _p or not _m:
            errs.append(f'condition_definitions.{cname} 缺 producer/producer_marker（R-4 生产方登记）')
            continue
        _pf = _root24 / str(_p)
        if not _pf.exists():
            errs.append(f'condition_definitions.{cname}.producer 文件不存在: {_p}（R-4）')
        elif str(_m) not in _pf.read_text(encoding='utf-8'):
            errs.append(f'condition_definitions.{cname}.producer_marker “{_m}” 不在 {_p}（R-4：字段无生产方）')

    # 26 条件不可判定处置（v2.12.54 R-6）：声明 condition 或 opt_out 的节点必须显式声明 condition_undecidable，
    #    禁止用 on_not_triggered 静默吞掉「条件证据读不到/缺失」——「未触发」与「漏跑」必须可分。
    UNDECIDABLE_OK = {'report_to_owner', 'halt_pending_owner'}
    for n in P:
        if n.get('condition') or n.get('opt_out'):
            if n.get('condition_undecidable') not in UNDECIDABLE_OK:
                errs.append(f"{n['id']} 缺/非法 condition_undecidable"
                            f"（R-6：应为 report_to_owner 或 halt_pending_owner）")

    # 27 status 记账两锁（v2.12.54 R-2 / R-3）：节点 id 合法性（禁自创）+ Done 记账一致性
    #    构建期锁模板承载规则，运行期由主控 read 目视执行（agent 无 exec，实例层不可机械校验）。
    st_text = (_root24 / 'references/templates/status-template.md').read_text(encoding='utf-8')
    if 'R-2 节点 id 合法性' not in st_text or '禁止自创' not in st_text:
        errs.append('status-template 缺 R-2 节点 id 合法性锁（禁自创节点 id）')
    if 'R-3 Done 记账一致性' not in st_text or '不得计 Done' not in st_text:
        errs.append('status-template 缺 R-3 Done 记账一致性锁（缺失/pending_owner/Not Triggered 不得计 Done）')

    # 28 T8 主人自行操作建议清单四类锁（v2.12.54 R-5）：格式转换 / SVG→PNG / 封面视觉 / SHA256
    #    实测事故（2026-09-18）：交付说明只给两类，全场「封面」0 命中 —— 建议清单是主人唯一的后续动作入口。
    for _rel28, _label28 in (('references/dispatch/T8-终检.md', 'T8 dispatch'),
                             ('references/agents/08-终检-final-inspector.md', '08-终检')):
        _t28 = (_root24 / _rel28).read_text(encoding='utf-8')
        for _act in ('文档格式转换', 'SVG', 'PNG', '封面视觉', 'SHA256'):
            if _act not in _t28:
                errs.append(f'{_label28} 缺「{_act}」（R-5：主人建议清单四类）')
        if 'T8 不合格' not in _t28:
            errs.append(f'{_label28} 缺「缺项 ⇒ T8 不合格」硬约束（R-5）')

    # 29 进度卡映射 + 失效指针锁（v2.12.54 T-5 / T-3）
    cpk_text = (_root24 / 'references/templates/checkpoint-card-template.md').read_text(encoding='utf-8')
    if '13 步' not in cpk_text or 'phase-order.yaml' not in cpk_text or 'pipeline-overview.md' not in cpk_text:
        errs.append('checkpoint-card 缺「13 步 ↔ 24 节点」映射说明（T-5）')
    qs_text = (_root24 / 'QUICKSTART.md').read_text(encoding='utf-8')
    if 'pipeline-overview.md' not in qs_text:
        errs.append('QUICKSTART 缺修订回环仲裁表指针（T-3：原指针指向已外移的 SKILL.md 章节）')

    # 30 盲审禁主控代笔（v2.12.55 S-2，修「同一节点两条互斥条款并存」）：
    #    实况（v2.12.54 前）：t9_review **同时**声明通用 fallback（executor: 主控 = 主控接管）与
    #    `independence_rules`「必须 spawn 为独立子代理（禁主控代笔）」—— 盲审在结构上不可能由主控接管
    #    （主控已读遍全部内部材料），实测被读成「主控代写审稿报告并给出编造精度」。
    #    现规则：盲审节点不得声明通用 fallback；失败唯一出口 = independence_failure_policy（只能重试 spawn →
    #    仍失败则记为缺失 + 告知主人，不得产出该节点结论）。
    for n in P:
        if n.get('independence') != 'blind_review':
            continue
        _owf = n.get('on_worker_failure') or {}
        if isinstance(_owf, dict) and _owf.get('executor') == '主控':
            errs.append(f"{n['id']}（blind_review）仍声明 on_worker_failure.executor: 主控"
                        f"（S-2：盲审不得由主控代笔，该通用 fallback 必须删除）")
        _ifp = n.get('independence_failure_policy') or {}
        if not isinstance(_ifp, dict) or _ifp.get('executor_takeover') != 'forbidden':
            errs.append(f"{n['id']}.independence_failure_policy.executor_takeover->{_ifp.get('executor_takeover')}"
                        f"（S-2：盲审必须显式禁止主控代笔，应为 forbidden）")
        if _ifp.get('on_exhausted') != 'record_missing_and_notify_owner':
            errs.append(f"{n['id']}.independence_failure_policy.on_exhausted->{_ifp.get('on_exhausted')}"
                        f"（S-2：重试耗尽必须记为缺失 + 告知主人，不得自行产出结论）")
        _rl = _ifp.get('retry_limit')
        if not isinstance(_rl, int) or _rl < 1:
            errs.append(f"{n['id']}.independence_failure_policy.retry_limit->{_rl}（S-2：必须为正整数 retry_limit）")
        if not n.get('independence_rules'):
            errs.append(f"{n['id']}（blind_review）缺 independence_rules（S-2：独立性硬定义不得只剩名号）")

    # 31 同 provider 连续静默升级（v2.12.55 S-3，修 P1「连续 4 次静默无升级规则」）：
    #    `top_tier_liveness_gate` 只做 spawn **前**探活，管不到 accepted 之后不产出 ——
    #    真源必须承载「同 provider 连续 ≥3 次静默 ⇒ 强制主人三选」，且不得 fail-open（无默认 + 挂起）。
    _pse = d.get('provider_silence_escalation') or {}
    if not isinstance(_pse, dict) or not _pse:
        errs.append('缺顶层 provider_silence_escalation（S-3：静默升级规则无机器可读真源，只能靠散文）')
    else:
        if _pse.get('threshold') != 3:
            errs.append(f"provider_silence_escalation.threshold->{_pse.get('threshold')}"
                        f"（S-3：同 provider 连续静默阈值应为 3）")
        if _pse.get('scope') != 'same_provider':
            errs.append(f"provider_silence_escalation.scope->{_pse.get('scope')}（S-3：应为 same_provider）")
        if _pse.get('no_default_option') is not True:
            errs.append('provider_silence_escalation.no_default_option ≠ true（S-3：三选一不得有默认项）')
        if _pse.get('halt_pending_owner') is not True:
            errs.append('provider_silence_escalation.halt_pending_owner ≠ true（S-3：到阈值必须挂起等主人）')
        _choices = [c.get('id') for c in (_pse.get('owner_choices') or []) if isinstance(c, dict)]
        for _must in ('switch_provider_family', 'switch_capability_tier', 'accept_same_source_with_disclosure'):
            if _must not in _choices:
                errs.append(f'provider_silence_escalation.owner_choices 缺「{_must}」选项（S-3 三选一锁）')
    # 真源 ↔ 主控角色卡双向接线（防「只活在 yaml、主控卡不执行」）
    _mc_text = (_root24 / 'references/agents/00-主控-coordinator.md').read_text(encoding='utf-8')
    if '连续 ≥3 次静默' not in _mc_text:
        errs.append('00-主控-coordinator.md 缺 S-3 静默升级协议（连续 ≥3 次静默 ⇒ 强制主人三选）')
    if '禁主控代笔' not in _mc_text:
        errs.append('00-主控-coordinator.md 缺 S-2 盲审禁代笔协议（independence: blind_review）')

    # 32 节点 kind 必填（v2.12.60）
    #    kind 是规则 4/5（入参 / 产出声明）与 owner_nodes 归属的**分派键**。
    #    实测（v2.12.60 本仓）：改 final_assembly 节点时误删 `kind: mechanical_checkpoint` 行，
    #    本次全仓 flow-check **RC=0 零报错** —— 即「kind 缺失 = 该节点对所有按 kind 分派的检查
    #    静默隐身」（与教训 #427 同族：判据依赖的字段本身没人守）。
    _KNOWN_KINDS = {'owner_checkpoint', 'mode_declaration', 'parallel_agents',
                    'conditional_review_window', 'mechanical_checkpoint', 'agent',
                    'conditional_agent', 'bounded_loop', 'owner_agent', 'advisory_agent'}
    for _n32 in P:
        _k32 = _n32.get('kind')
        if not _k32:
            errs.append(f"节点 {_n32.get('id')} 缺 kind（kind=分派键，缺失使该节点对一切 kind 类检查隐身）")
        elif _k32 not in _KNOWN_KINDS:
            errs.append(f"节点 {_n32.get('id')} kind='{_k32}' 不在已知集合内")

    # 33 人环决策词表三处同源（v2.12.61，修 Phase 0「status 字面值与 yaml decisions 交集为空」）：
    #    实况（主人 2026-09-19 问「checkpoint-card 有没有实质作用」时查出）：status-template 写
    #      `decision=<start|补充信息|暂停|拒绝>`，而 yaml `phase0_definition.decisions` =
    #      [approved, revision_requested, restart_phase] —— **交集为空**；`start`/`暂停`/`拒绝` 在全仓
    #      真源里零命中 ⇒ 主人选「暂停」时主控要写的字面值无对应枚举，人在环硬门必然判「未记录」。
    #    根因：Phase 0 把「是否启动」（流水线**外**前置门）与「进线后决策」混成一张选项表，status 照抄。
    #    锁：① status-template 四行 `decision=<...>` 字面值必须 ⊆ 对应节点 yaml `decisions`；
    #        ② 卡片四段各须带「枚举真源」指针（`<节点 id>.decisions`）—— 卡片自称「固定，不可自由发挥」，
    #           但原先只有 Phase 2.5 段有指针，其余三段无真源可对 ⇒ 「不可自创」只是自我声明。
    _st33 = (_root24 / 'references/templates/status-template.md').read_text(encoding='utf-8')
    _ck33 = (_root24 / 'references/templates/checkpoint-card-template.md').read_text(encoding='utf-8')
    for _lbl33, _nid33 in (('Phase 0 定题', 'phase0_definition'),
                           ('Phase 2.5 大纲', 'phase2_5_outline'),
                           ('Phase 3.5 洞察', 'phase3_5_insight'),
                           ('Phase 5 验收', 'phase5_acceptance')):
        _decl33 = set((byid.get(_nid33) or {}).get('decisions') or [])
        _m33 = re.search(r'^- \*\*' + re.escape(_lbl33) + r'\*\*:.*?decision=<([^>]*)>', _st33, re.M)
        if not _m33:
            errs.append(f'status-template 缺「{_lbl33}」decision=<...> 行（词表无真源可比）')
        else:
            _vals33 = {_v.strip() for _v in _m33.group(1).split('|') if _v.strip()}
            _extra33 = sorted(_vals33 - _decl33)
            if _extra33:
                errs.append(f'status-template「{_lbl33}」decision 字面值 {_extra33} 不在 '
                            f'{_nid33}.decisions {sorted(_decl33)} 内（自创词表，人在环硬门会判未记录）')
        if f'{_nid33}.decisions' not in _ck33:
            errs.append(f'checkpoint-card 缺「{_lbl33}」枚举真源指针（{_nid33}.decisions）')

    # 34 B12 spawn 落地验证「三点接线」（v2.12.62，修审计 B12「仅纪律层，无机械兜底」）：
    #    故障面 = `sessions_spawn` 返回 accepted 但子会话不存在 ⇒ 主控无限等待。
    #    诚实边界：论衡 agent 零 exec，**运行期**行为无法在构建期机械校验 —— 本规则**不假装**能拦
    #    故障本身，只锁「协议不许从载体里静默消失」这一可机械部分（三点接线）：
    #      ① 真源：执行韧化协议-exec.md 含落地验证本体（spawn 后 / active runs / 重试 ≤2 次）
    #         + **诚实边界声明**（显式写「构建期无法机械校验」，防后人误以为有门）
    #      ② 主控卡：必须指向该真源（防「只活在 _shared、主控不执行」）
    #      ③ 运行期留痕：status-template 必须有 `spawn_landing` 记账字段（主人可事后核验，
    #         失败不再无声）—— 这是把「纪律」变成「可核验痕迹」的唯一机械化路径。
    _hp34 = (_root24 / 'references/_shared/真源/执行韧化协议-exec.md').read_text(encoding='utf-8')
    for _tok34 in ('spawn 后', 'active runs', '重试 ≤2 次', '机械兜底边界'):
        if _tok34 not in _hp34:
            errs.append(f'执行韧化协议-exec.md 缺「{_tok34}」（B12：落地验证协议或诚实边界声明缺失）')
    _mc34 = (_root24 / 'references/agents/00-主控-coordinator.md').read_text(encoding='utf-8')
    if '执行韧化协议-exec.md' not in _mc34:
        errs.append('00-主控-coordinator.md 未指向执行韧化协议真源（B12：协议只活在 _shared，主控不执行）')
    _st34 = (_root24 / 'references/templates/status-template.md').read_text(encoding='utf-8')
    if 'spawn_landing' not in _st34:
        errs.append('status-template 缺 spawn_landing 留痕字段（B12：落地验证无运行期痕迹，主人无法核验）')
    if '机械兜底边界' not in _st34:
        errs.append('status-template 缺「机械兜底边界」诚实声明（B12：防把纪律层误读为机械门）')

    # 35 M 门判据字段生产方（v2.12.65 P0-1）：m_gate_criterion_fields 每条必须登记
    #    `producer` + `producer_marker`，且 producer 文件存在、marker 确实出现在该文件中 ——
    #    封掉「M 门判据字段全仓无生产方 ⇒ 数据量维度门静默放行」。
    #    与规则 25（R-4）同族，但 25 只覆盖 condition_definitions，本规则覆盖 M 门算法判据字段。
    for cname, cdef in (d.get('m_gate_criterion_fields') or {}).items():
        if not isinstance(cdef, dict):
            errs.append(f'm_gate_criterion_fields.{cname} 不是映射（P0-1）')
            continue
        _p = cdef.get('producer')
        _m = cdef.get('producer_marker')
        if not _p or not _m:
            errs.append(f'm_gate_criterion_fields.{cname} 缺 producer/producer_marker（P0-1 判据字段生产方登记）')
            continue
        _pf = _root24 / str(_p)
        if not _pf.exists():
            errs.append(f'm_gate_criterion_fields.{cname}.producer 文件不存在: {_p}（P0-1）')
        elif str(_m) not in _pf.read_text(encoding='utf-8'):
            errs.append(f'm_gate_criterion_fields.{cname}.producer_marker “{_m}” 不在 {_p}（P0-1：判据字段无生产方）')

    # 36 轻量档跳过集合单一真源（v2.12.65 P1-1）：phase-order.yaml 中 `degrade: skip_in_lite_tier`
    #    的节点集必须 == {t6_critique}（轻量档唯一必跳角色；G14 走 selfcheck 而非 skip）；
    #    任务简报档位表「轻量」行的**跳过列**不得声称跳过 T7/T9（与真源冲突）。
    lite_skip = [n['id'] for n in P if n.get('degrade') == 'skip_in_lite_tier']
    if set(lite_skip) != {'t6_critique'}:
        errs.append(f'轻量档 skip_in_lite_tier 节点集 = {sorted(lite_skip)}（P1-1：真源应为 {{t6_critique}}）')
    _jb36 = (_root24 / 'references/templates/任务简报-template.md').read_text(encoding='utf-8')
    for _ln36 in _jb36.splitlines():
        if _ln36.startswith('| **轻量**'):
            _cols36 = [c.strip() for c in _ln36.split('|')]
            _skip36 = _cols36[2] if len(_cols36) > 2 else ''
            if 'T7' in _skip36 or 'T9' in _skip36:
                errs.append('任务简报档位表「轻量」跳过列声称跳过 T7/T9（P1-1：与 phase-order.yaml 真源冲突）')
            break

    # 37 路径边界两域口径（v2.12.65 P1-2）：三处旧单域口径必须已收敛为两域 + 指向 permissions.md。
    #    旧口径「read/write/edit 仅限 run/<项目名>/ 子树」与角色卡必读 references/ 互斥 ⇒ 字面遵守则
    #    流水线不可执行。三处载体不得再含旧单域措辞（防 v2.12.64「只修一处、三处回潮」复发）。
    for _f37, _tok37 in (
        ('SKILL.md', '仅限 `run/<项目名>/` 子树'),
        ('references/_shared/真源/关键协议.md', '仅允许 `run/<项目名>/` 子树'),
        ('references/_shared/真源/dispatch-header.md', 'run/ 子树外路径'),
    ):
        _t37 = (_root24 / _f37).read_text(encoding='utf-8')
        if _tok37 in _t37:
            errs.append(f'{_f37} 仍含旧单域路径口径「{_tok37}」（P1-2：应改为两域 + 指向 permissions.md）')

    # 38 安全误报白名单清单完整性（v2.12.65 P1-4）：`.safe-pattern-manifest.json` 必须可解析，
    #    每条豁免必须给出 file/reason/lines/note，且 file 真实存在、行号端点落在该文件行数内。
    #    故障面 = 「登记一行就走」：文件改名 / 行号漂移后，白名单变成**假账**，下一轮安全扫描
    #    仍要重复人工逐条排查（P1-4 诉求：把「已知误报 + 理由」变成可复用判据，而不是一次性说明）。
    _mf38 = _root24 / '.safe-pattern-manifest.json'
    _man38 = None
    if not _mf38.exists():
        errs.append('.safe-pattern-manifest.json 缺失（P1-4：已知误报白名单未登记）')
    else:
        try:
            _man38 = json.loads(_mf38.read_text(encoding='utf-8'))
        except Exception as _e38:
            _man38 = None
            errs.append(f'.safe-pattern-manifest.json 解析失败: {_e38}（P1-4）')
        if isinstance(_man38, dict):
            if not isinstance(_man38.get('version'), int):
                errs.append('.safe-pattern-manifest.json 缺整型 version（P1-4）')
            _ex38 = _man38.get('exemptions')
            if not isinstance(_ex38, list) or not _ex38:
                errs.append('.safe-pattern-manifest.json exemptions 缺失或为空（P1-4）')
            else:
                _seen38 = set()
                for _e38 in _ex38:
                    if not isinstance(_e38, dict):
                        errs.append(f'manifest 豁免项不是映射（P1-4）: {_e38!r}')
                        continue
                    _f38, _r38 = _e38.get('file'), _e38.get('reason')
                    _m38 = _e38.get('match')
                    _l38, _n38 = _e38.get('lines'), _e38.get('note')
                    if not (_f38 and _r38 and _m38 and _l38 and _n38):
                        errs.append(f'manifest 豁免项缺 file/reason/match/lines/note（P1-4）: {_e38!r}')
                        continue
                    if _f38 in _seen38:
                        errs.append(f'manifest 豁免项重复登记同一文件: {_f38}（P1-4）')
                    _seen38.add(_f38)
                    if not re.fullmatch(r'[a-z][a-z0-9-]*', str(_r38)):
                        errs.append(f'manifest 豁免项 reason 非 kebab-case: {_r38}（P1-4）')
                    if not re.fullmatch(r'\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*', str(_l38)):
                        errs.append(f'manifest 豁免项 lines 格式非法: {_l38}（P1-4）')
                    if len(str(_n38)) < 10:
                        errs.append(f'manifest 豁免项 note 过短（未写理由）: {_f38}（P1-4）')
                    _pf38 = _root24 / str(_f38)
                    if not _pf38.exists():
                        errs.append(f'manifest 豁免项文件不存在: {_f38}（P1-4：白名单已成假账）')
                        continue
                    _tot38 = len(_pf38.read_text(encoding='utf-8', errors='ignore').splitlines())
                    _txt38 = _pf38.read_text(encoding='utf-8', errors='ignore')
                    try:
                        if not re.search(str(_m38), _txt38):
                            errs.append(f'manifest 豁免项 match 未命中：{_f38} / {_m38}（P1-4：内容已漂移）')
                    except re.error as _re38:
                        errs.append(f'manifest 豁免项 match 正则非法：{_f38} / {_re38}（P1-4）')
                    for _seg38 in str(_l38).split(','):
                        for _num38 in _seg38.split('-') if isinstance(_seg38, str) else []:
                            if not str(_num38).isdigit():
                                continue
                            if int(_num38) > _tot38:
                                errs.append(f'manifest 豁免项行号越界: {_f38} 第 {_num38} 行 > 实际 {_tot38} 行（P1-4：行号已漂移）')

    # 39 维护者脚本危险操作统一审计点（v2.12.65 P2-3）：scripts/ 下含危险构造的脚本必须与
    #    `.safe-pattern-manifest.json` 的 `maintainer_danger_ops.files` **双向对账** ——
    #    漏登记（新脚本加了 rm -rf 却没登记）与陈旧登记（脚本已移除该构造却没销账）都要报红。
    #    扫描口径与通用扫描器一致（跳过 `#` / `-` / `**` / 围栏 / 三引号行），防止两端漏重不一致。
    #    故障面 = 「危险操作分散在多脚本、无统一审计点」：新增一处 rm -rf / bash -c 时无人察觉。
    if isinstance(_man38, dict):
        _mdo39 = _man38.get('maintainer_danger_ops') or {}
        _pats39 = [str(x) for x in (_mdo39.get('patterns') or [])]
        _decl39 = {str(e.get('file')) for e in (_mdo39.get('files') or []) if isinstance(e, dict)}
        if not _pats39:
            errs.append('maintainer_danger_ops.patterns 缺失或为空（P2-3：统一审计点无判据）')
        if not _decl39:
            errs.append('maintainer_danger_ops.files 缺失或为空（P2-3：危险操作无登记）')
        for _e39 in (_mdo39.get('files') or []):
            if isinstance(_e39, dict) and not _e39.get('guard'):
                errs.append(f"maintainer_danger_ops 登记项缺 guard: {_e39.get('file')}（P2-3：必须写明护栏）")
        _hit39 = set()
        for _sf39 in (sorted((_root24 / 'scripts').glob('*.sh'))
                      + sorted((_root24 / 'scripts').glob('*.py'))):
            for _ln39 in _sf39.read_text(encoding='utf-8', errors='ignore').splitlines():
                _s39 = _ln39.strip()
                if (_s39.startswith('#') or _s39.startswith('-') or _s39.startswith('**')
                        or '"""' in _s39 or "'''" in _s39 or '```' in _s39):
                    continue
                if any(_p39 in _ln39 for _p39 in _pats39):
                    _hit39.add(f'scripts/{_sf39.name}')
                    break
        for _f39 in sorted(_hit39 - _decl39):
            errs.append(f'{_f39} 含维护者危险操作但未登记（P2-3：请补 maintainer_danger_ops.files 并写明护栏）')
        for _f39 in sorted(_decl39 - _hit39):
            errs.append(f'{_f39} 已登记危险操作但实际未命中（P2-3：陈旧登记，请销账或复核扫描口径）')

    # 40 跨状态机「静默 ≠ 有效决策」与 HITL 留痕一致性（v2.12.65 / v2.13.2）：
    #    `owner_timeout_policy`（主人无应答）与 `provider_silence_escalation`（同 provider 连续静默）
    #    共享同一不变式 —— 静默/无应答 ≠ 有效决策 ⇒ 挂起等主人 + 无默认继续。此前该不变式
    #    **只用散文声明**（「与 owner_timeout_policy 同侧」），任一侧改成自动继续另一侧不会报红。
    #    真源 = 顶层 `silence_doctrine`；本规则做双侧投影 + 双向对账（故障面 = 「改 A 漏 B」）。
    _sd40 = d.get('silence_doctrine') or {}
    if not isinstance(_sd40, dict) or not _sd40:
        errs.append('缺顶层 silence_doctrine（P2-2：跨状态机不变式无机器可读真源，只能靠散文）')
    else:
        _halt40 = [str(x) for x in (_sd40.get('halt_kinds') or [])]
        _forb40 = [str(x) for x in (_sd40.get('forbidden_kinds') or [])]
        _app40 = [str(x) for x in (_sd40.get('applies_to') or [])]
        if not _halt40:
            errs.append('silence_doctrine.halt_kinds 缺失或为空（P2-2：挂起类处置无枚举）')
        if not _forb40:
            errs.append('silence_doctrine.forbidden_kinds 缺失或为空（P2-2：fail-open 类无枚举）')
        _both40 = sorted(set(_halt40) & set(_forb40))
        if _both40:
            errs.append(f'silence_doctrine 自洽冲突：{_both40} 同时列为挂起类与 fail-open 类（P2-2）')
        if set(_app40) != {'owner_timeout_policy', 'provider_silence_escalation'}:
            errs.append(f'silence_doctrine.applies_to 未恰好覆盖两侧状态机：{_app40}（P2-2）')

        # 主人侧投影：无应答处置必须全为挂起类（比规则 12 更严：12 只查 ∈ fallback_kinds）
        _otp40 = d.get('owner_timeout_policy') or {}
        _fk40 = _otp40.get('fallback_kinds') or {}
        _bad40 = sorted(set(_fk40) - set(_halt40))
        if _bad40:
            errs.append(f'owner_timeout_policy.fallback_kinds 含非挂起类处置 {_bad40}'
                        f'（P2-2：新增处置必须登记进 silence_doctrine.halt_kinds）')
        _df40 = _otp40.get('default_fallback')
        if _df40 not in _halt40:
            errs.append(f'owner_timeout_policy.default_fallback->{_df40} 非挂起类'
                        f'（P2-2：无应答默认处置必须在 halt_kinds 内）')
        _owner_halt40 = bool(_fk40) and not _bad40 and _df40 in _halt40

        # provider 侧投影：同侧的两个布尔必须为真；三选一不得带默认项
        _pse40 = d.get('provider_silence_escalation') or {}
        _prov_halt40 = (_pse40.get('halt_pending_owner') is True
                        and _pse40.get('no_default_option') is True)
        for _c40 in (_pse40.get('owner_choices') or []):
            if isinstance(_c40, dict) and (_c40.get('default') or _c40.get('is_default')):
                errs.append(f"provider_silence_escalation.owner_choices.{_c40.get('id')} 标了默认项"
                            f"（P2-2/S-3：三选一不得有默认）")

        # 双向对账：两侧必须同侧；一侧挂起、另一侧自动继续 = 状态机不同侧
        if _owner_halt40 != _prov_halt40:
            errs.append(
                '跨状态机不同侧：owner_timeout_policy='
                + ('halt' if _owner_halt40 else 'auto_continue')
                + ' vs provider_silence_escalation='
                + ('halt' if _prov_halt40 else 'auto_continue')
                + '（P2-2：静默/无应答必须同侧 —— 挂起等主人 + 无默认继续）')

        # 节点级：各 owner_checkpoint 的 timeout_fallback 必须落在 halt_kinds
        for _n40 in P:
            if _n40.get('kind') != 'owner_checkpoint':
                continue
            _fb40 = _n40.get('timeout_fallback')
            if _fb40 not in _halt40:
                errs.append(f"{_n40['id']}.timeout_fallback->{_fb40} 非挂起类"
                            f"（P2-2：必须落在 silence_doctrine.halt_kinds 内）")

    # 41 M-13 清单跨载体一致性（v2.12.66）：T8 dispatch 与 08-终检 是**同一份**「主人自行操作
    #    建议清单」的两个载体，此前**无任何门**校验二者一致 ⇒ v2.12.60 把第 2 类由「图件落地与
    #    嵌入」瘦回「SVG → PNG 转换」（嵌入改由 final_assembly 在流水线内完成）时**只改 T8、
    #    08 漏改**；同期 T8 的内联命令模板又与它自己声明的真源 `_shared/真源/format-export.md` §二
    #    不符（缺 `.tex` 行、`--reference-doc` 指向旧文件 `templates/word-reference.docx`、
    #    pdf 缺 `--template/--bibliography/--csl`）—— 主人照拄即得错误产物。
    #    故障面 = 「同一份清单两处承载、改 A 漏 B」（与 P1-1 轻量档口径、P1-2 路径边界同族）。
    _M13_ACTIONS41 = ('文档格式转换', 'SVG → PNG 转换', '封面视觉', 'SHA256 校验和登记')
    _M13_STALE41 = ('templates/word-reference.docx', '再嵌入定稿')
    _M13_CARRIERS41 = (('T8 dispatch', 'references/dispatch/T8-终检.md'),
                       ('08-终检', 'references/agents/08-终检-final-inspector.md'))
    _cmd41 = {}
    for _lbl41, _rel41 in _M13_CARRIERS41:
        _t41 = (_R / _rel41).read_text(encoding='utf-8')
        for _a41 in _M13_ACTIONS41:
            if _a41 not in _t41:
                errs.append(f'{_lbl41} M-13 清单缺动作「{_a41}」（规则 41：两载体四类必须一致）')
        for _s41 in _M13_STALE41:
            if _s41 in _t41:
                errs.append(f'{_lbl41} M-13 含已作废写法「{_s41}」'
                            f'（规则 41：v2.12.60 定案图位嵌入在流水线内，主人只做 SVG→PNG）')
        _blk41 = [b for b in re.findall(r'```[a-zA-Z]*\n(.*?)```', _t41, re.S) if 'pandoc' in b]
        if len(_blk41) != 1:
            errs.append(f'{_lbl41} M-13 命令模板块应恰 1 个，实为 {len(_blk41)} 个（规则 41）')
        else:
            _cmd41[_lbl41] = '\n'.join(l.strip() for l in _blk41[0].splitlines() if l.strip())
    if len(_cmd41) == 2 and len(set(_cmd41.values())) != 1:
        errs.append('M-13 命令模板两载体不一致（规则 41：T8 dispatch 与 08-终检 必须同源，'
                    '真源 = _shared/真源/format-export.md §二）')
    # 命令模板须与声明真源同源：canonical 四要素缺一即红
    for _lbl41, _txt41 in _cmd41.items():
        for _need41 in ('final/定稿.tex', '--reference-doc=academic-paper-template.docx',
                        '--bibliography=final/证据包/参考文献.bib',
                        '--csl=chinese-gb7714-2015-numeric'):
            if _need41 not in _txt41:
                errs.append(f'{_lbl41} M-13 命令模板缺 {_need41}'
                            f'（规则 41：与真源 format-export.md §二 同源）')

    # 42 只读档报告分片预申报接线（v2.12.67，审计 P1-1）：超长报告回传协议不得从载体静默消失。
    #    真源 = 执行韧化协议-exec.md §6 分片预申报；四个只读档 dispatch 是同协议的派发载体，
    #    均须含「分片清单」与「报告分片 N/M」口径。触发线 3500 的数值真源在协议本体（一条款一真源，
    #    本规则只锁存在性，不复制数值 —— 防两套判据漂移）。
    _C42_CARRIERS = (
        ('协议真源', 'references/_shared/真源/执行韧化协议-exec.md'),
        ('T6 dispatch', 'references/dispatch/T6-批判.md'),
        ('T7 dispatch', 'references/dispatch/T7-审计.md'),
        ('T9 dispatch', 'references/dispatch/T9-同行评审.md'),
        ('G14 dispatch', 'references/dispatch/G14-中文AI痕迹检测器.md'),
    )
    for _lbl42, _rel42 in _C42_CARRIERS:
        _t42 = (_R / _rel42).read_text(encoding='utf-8')
        for _need42 in ('报告分片 N/M', '分片清单'):
            if _need42 not in _t42:
                errs.append(f'{_lbl42} 缺「{_need42}」（规则 42：超长报告分片预申报不得从载体静默消失，'
                            f'真源 = _shared/真源/执行韧化协议-exec.md §6）')

    # 43 G15/G16 写作质量门跨载体一致性（v2.12.68，借 writing-guard）：主张强度校准 + 上下文泄漏
    #    两项写作质量门不得从真源（audit-checklist-quickref.md）或 T7 dispatch 载体静默消失。
    #    真源 = _shared/真源/audit-checklist-quickref.md；T7 dispatch 是派发载体（一条款一真源，
    #    本规则只锁存在性，不复制判据全文 —— 防两套判据漂移）。
    _C43_CARRIERS = (
        ('G 门真源', 'references/_shared/真源/audit-checklist-quickref.md'),
        ('T7 dispatch', 'references/dispatch/T7-审计.md'),
    )
    for _lbl43, _rel43 in _C43_CARRIERS:
        _t43 = (_R / _rel43).read_text(encoding='utf-8')
        for _need43 in ('G15 主张强度', 'G16 上下文泄漏'):
            if _need43 not in _t43:
                errs.append(f'{_lbl43} 缺「{_need43}」（规则 43：G15/G16 写作质量门不得从载体静默消失，'
                            f'真源 = _shared/真源/audit-checklist-quickref.md）')

    # 44 G17 数据指纹比对跨载体一致性（v2.12.69，借 writing-guard Scholarship Lock）：
    #    数据完整性门不得从真源（audit-checklist-quickref.md）或 T7 dispatch 载体静默消失。
    #    真源 = _shared/真源/audit-checklist-quickref.md；T7 dispatch 是派发载体（一条款一真源，
    #    本规则只锁存在性，不复制判据全文 —— 防两套判据漂移）。
    _C44_CARRIERS = (
        ('G 门真源', 'references/_shared/真源/audit-checklist-quickref.md'),
        ('T7 dispatch', 'references/dispatch/T7-审计.md'),
    )
    for _lbl44, _rel44 in _C44_CARRIERS:
        _t44 = (_R / _rel44).read_text(encoding='utf-8')
        for _need44 in ('G17 数据指纹',):
            if _need44 not in _t44:
                errs.append(f'{_lbl44} 缺「{_need44}」（规则 44：G17 数据指纹门不得从载体静默消失，'
                            f'真源 = _shared/真源/audit-checklist-quickref.md）')

    # 45 期刊约定校验跨载体一致性（v2.12.69，借 writing-guard JOURNAL 层）：
    #    期刊约定校验不得从 T9 dispatch 或 09-审稿角色卡载体静默消失。
    #    真源 = 09-审稿-peer-reviewer.md（角色卡）；T9 dispatch 是派发载体（一条款一真源，
    #    本规则只锁存在性，不复制判据全文 —— 防两套判据漂移）。
    _C45_CARRIERS = (
        ('T9 dispatch', 'references/dispatch/T9-同行评审.md'),
        ('09-审稿角色卡', 'references/agents/09-审稿-peer-reviewer.md'),
    )
    for _lbl45, _rel45 in _C45_CARRIERS:
        _t45 = (_R / _rel45).read_text(encoding='utf-8')
        for _need45 in ('期刊约定校验',):
            if _need45 not in _t45:
                errs.append(f'{_lbl45} 缺「{_need45}」（规则 45：期刊约定校验不得从载体静默消失，'
                            f'真源 = 09-审稿-peer-reviewer.md）')

    # 46 主控上下文预算门跨载体一致性（v2.12.72 批次 2-E，防教训 #268 复发）
    #    故障面 = 主控窗口被压爆 ⇒ 凭记忆复制 dispatch 话术（#268 同族）。token 统计此前只做事后
    #    记账，不做事前预防。本规则锁「事前预算 + 余量检测 + 落盘减负」协议与留痕字段不得从
    #    真源 / 主控运行协议 / status 模板 / 任务简报任一载体静默消失。
    #    诚实边界（同规则 34）：窗口余量是运行期自观测，构建期无法机械校验 —— 不假装能拦压爆本身。
    _cbg46 = (byid.get('pre_spawn_enforcement') or {}).get('context_budget_gate')
    if not isinstance(_cbg46, dict):
        errs.append('pre_spawn_enforcement 缺 context_budget_gate（规则 46：主控上下文预算门未入真源）')
    else:
        for _k46 in ('estimate_by_tier', 'margin_threshold_pct', 'overspend_alert_pct',
                     'on_low_margin', 'offload_actions', 'recheck', 'record', 'doctrine'):
            if _k46 not in _cbg46:
                errs.append(f'context_budget_gate 缺 {_k46}'
                            f'（规则 46：预算门字段不完整，落盘减负无判据）')
    _C46_CARRIERS = (
        ('status 留痕', 'references/templates/status-template.md', '主控上下文预算与余量检测'),
        ('主控运行协议', 'references/agents/00-主控-扩展职责.md', '主控上下文预算与落盘减负'),
        ('预算模型真源', 'references/_shared/真源/performance-benchmarks.md', '主控上下文预算模型'),
        ('任务简报', 'references/templates/任务简报-template.md', 'token_budget'),
    )
    for _lbl46, _rel46, _need46 in _C46_CARRIERS:
        _p46 = _root24 / _rel46
        _t46 = _p46.read_text(encoding='utf-8') if _p46.exists() else ''
        if _need46 not in _t46:
            errs.append(f'{_lbl46} 缺「{_need46}」（规则 46：主控上下文预算协议不得从载体静默消失，'
                        f'真源 = phase-order.yaml pre_spawn_enforcement.context_budget_gate）')

    # 47 端到端活体冒烟跨载体一致性（v2.12.72 批次 3-D）
    #    故障面 = 「构建期门全绿」被误读为「活体链路不断裂」（审计原话：476 项测试全为文档/脚本
    #    判据一致性，无一条跑过 spawn → 交接 → 审计链 → 修订回环）。本规则锁冒烟协议、留痕字段、
    #    登记表与发布钩子不得从任一载体静默消失。
    #    诚实边界（同规则 34/46）：冒烟是运行期行为且耗真实 token，构建期无法代替，
    #    不得把「协议在位」误读为「冒烟已跑」（未跑则登记 pending_owner_run）。
    _sm47 = (_R / 'references/_shared/真源/执行韧化协议-exec.md').read_text(encoding='utf-8')
    for _need47 in ('端到端活体冒烟协议', 'L1 机制冒烟', 'L2 全流程冒烟', '不进 CI'):
        if _need47 not in _sm47:
            errs.append(f'执行韧化协议-exec.md 缺「{_need47}」（规则 47：活体冒烟协议不得从真源静默消失）')
    _C47_CARRIERS = (
        ('status 留痕', 'references/templates/status-template.md', 'smoke_run_id'),
        ('冒烟登记表', 'references/_shared/真源/performance-benchmarks.md', '端到端活体冒烟登记'),
        ('发布 SOP', 'references/设计文档-架构.md', '发布前活体冒烟'),
    )
    for _lbl47, _rel47, _need47b in _C47_CARRIERS:
        _p47 = _R / _rel47
        _t47 = _p47.read_text(encoding='utf-8') if _p47.exists() else ''
        if _need47b not in _t47:
            errs.append(f'{_lbl47} 缺「{_need47b}」（规则 47：活体冒烟载体不得静默消失，'
                        f'真源 = 执行韧化协议-exec.md「端到端活体冒烟协议」）')
    if 'owner_checkpoint' not in _sm47:
        errs.append('活体冒烟协议未声明 owner_checkpoint 口径（规则 47：L2 不得自动通过主人闸门）')

    # 48 机器可解析状态快照（v2.12.72 批次 5-G）
    #    status-template 的 status_json 快照与 performance-benchmarks 的聚合指针不得静默消失。
    #    诚实边界（同 46/47）：快照由主控运行期写入，构建期只锁结构锚点，不伪造自动采集。
    _st48 = (_R / 'references/templates/status-template.md').read_text(encoding='utf-8')
    for _need48 in ('status_json', '机器可解析快照'):
        if _need48 not in _st48:
            errs.append(f'status-template 缺「{_need48}」（规则 48：status_json 快照不得静默消失）')
    _bench48 = (_R / 'references/_shared/真源/performance-benchmarks.md').read_text(encoding='utf-8')
    if 'status_json' not in _bench48:
        errs.append('performance-benchmarks 缺 status_json 聚合指针（规则 48：G 可观测性反哺链断裂）')

    # 49 英文参考层试点（v2.12.72 批次 5-F）
    #    最小适配层（字段标签英文对照）须在两模板在位，且诚实声明「判据真源仍为中文 + 全量适配暂缓」。
    _C49_CARRIERS = (
        ('任务简报', 'references/templates/任务简报-template.md'),
        ('交接报告', 'references/templates/交接报告-template.md'),
    )
    for _lbl49, _rel49 in _C49_CARRIERS:
        _t49 = (_R / _rel49).read_text(encoding='utf-8')
        for _need49 in ('英文参考层', '判据真源仍为中文'):
            if _need49 not in _t49:
                errs.append(f'{_lbl49} 缺「{_need49}」（规则 49：英文参考层或诚实边界不得静默消失）')
    _arch49 = (_R / 'references/设计文档-架构.md').read_text(encoding='utf-8')
    if '英文 AI 痕迹检测不在本批范围' not in _arch49:
        errs.append('设计文档-架构 缺英文 AI 痕迹检测范围声明（规则 49：F 试点不得被静默扩为全量）')

    # HITL-40 扩展：人在环运行期呈现留痕与等待体验跨载体一致性（并入规则 40）
    #     规则 12/40 只锁「必须阻断」，不能防止主控呈现后没有可恢复提示、提醒上限
    #     或 checkpoint 留痕字段从模板中静默消失。本规则只锁协议与载体存在性；
    #     `checkpoint_presented=true` 的真实运行值仍由主控运行期填写，不能伪造为已发生。
    _HITL50_CARRIERS = (
        ('Checkpoint 卡模板', 'references/templates/checkpoint-card-template.md',
         ('🎯 先看这里（决策摘要）', '回复 A/B/C/D', '等待主人期间的交互协议',
          '轻提醒一次', '恢复文案（固定短版）', 'checkpoint_presented=true')),
        ('完整 status 模板', 'references/templates/status-template.md',
         ('运行期呈现留痕', 'checkpoint_id=', 'checkpoint_status=',
          'reminder_sent=', 'owner_response_received=')),
        ('精简 status 模板', 'references/templates/status-template-lite.md',
         ('人在环呈现留痕', 'checkpoint_id=', 'checkpoint_status=',
          'owner_response_received=')),
        ('主控运行协议', 'references/agents/00-主控-扩展职责.md',
         ('等待期体验与运行期留痕', 'checkpoint_presented=true',
          '最多发一次固定短提醒', 'pending_owner_at')),
    )
    for _lbl50, _rel50, _needs50 in _HITL50_CARRIERS:
        _p50 = _R / _rel50
        _t50 = _p50.read_text(encoding='utf-8') if _p50.exists() else ''
        for _need50 in _needs50:
            if _need50 not in _t50:
                errs.append(f'{_lbl50} 缺「{_need50}」（规则 40：HITL 呈现/恢复协议不得静默消失）')

    print(';'.join(errs))
    return 0 if not errs else 2


if __name__ == '__main__':
    sys.exit(main())
