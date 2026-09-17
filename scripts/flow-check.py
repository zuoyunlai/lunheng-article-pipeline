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

用法：python3 scripts/flow-check.py  → 无输出=通过；有输出=问题列表（分号分隔）。"""
import pathlib, re, sys, yaml
from collections import deque

# 执行类节点：产出受管产物，必须 input + output
EXEC_KINDS = (
    'agent', 'owner_agent', 'parallel_agents', 'conditional_agent',
    'advisory_agent', 'bounded_loop',
)
# 入参类节点：只需 input
INPUT_KINDS = EXEC_KINDS + ('conditional_review_window',)

# 路径 token：必须含目录分隔符，扩展名 ∈ md/svg/json/yaml（保守匹配，宁少勿误报）
PATH_RE = re.compile(r'[A-Za-z0-9_\-\u4e00-\u9fff]+/[A-Za-z0-9_\-\u4e00-\u9fff/{}.*]+\.(?:md|svg|json|yaml)')
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
    p = pathlib.Path('references/_shared/phase-order.yaml')
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
        for k in ('next', 'after_trigger', 'on_fail'):
            v = n.get(k)
            if isinstance(v, str) and v in byid:
                out.append(v)
        for v in (n.get('after_each') or []):
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
        ('references/_shared/M-Gate-Algorithm.md',
         '## 🎯 计数类档位真源 + P2 量化锚点'),
        ('references/_shared/字数判定表.md',
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
    fabiao = pathlib.Path(__file__).resolve().parent.parent / 'references/_shared/可发表性判定表.md'
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
    kp_text = (_R / 'references/_shared/关键协议.md').read_text(encoding='utf-8')
    if '四·补' not in kp_text or '派发禁止摘要' not in kp_text:
        errs.append('关键协议 缺 §四·补 只读档报告落盘前置 + 派发禁止摘要（T-1）')
    jj_text = (_R / 'references/templates/交接报告-template.md').read_text(encoding='utf-8')
    if 'upstream_read' not in jj_text or 'dispatched_ids' not in jj_text:
        errs.append('交接报告模板 缺 upstream_read/dispatched_ids 差集断言字段（T-1）')
    cand_text = (_R / 'references/_shared/模型候选池.md').read_text(encoding='utf-8')
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
    wc_text = (_R / 'references/_shared/字数判定表.md').read_text(encoding='utf-8')
    if '修订净增上限' not in wc_text or 'net_delta_cjk' not in wc_text:
        errs.append('字数判定表 缺 §八 修订净增上限 + net_delta_cjk（T-5）')
    n_ms = byid.get('methodology_snapshot')
    if n_ms is not None and (n_ms.get('default') != 'triggered' or not n_ms.get('opt_out')):
        errs.append('methodology_snapshot 未改为「默认 triggered + opt_out」（T-6）')
    if '引用体例单一化' not in deliv_text:
        errs.append('deliverables.md 缺 T-8 引用体例单一化段')
    m_exist_text = (_R / 'references/_shared/M-Gate-Algorithm.md').read_text(encoding='utf-8')
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

    print(';'.join(errs))
    return 0 if not errs else 2


if __name__ == '__main__':
    sys.exit(main())
