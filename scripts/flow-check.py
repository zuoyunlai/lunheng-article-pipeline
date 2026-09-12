#!/usr/bin/env python3
"""论衡流程图检查（v2.12.28 新增）—— 防孤立节点 / 断链 / 缺 next / 缺 input。
用法：python3 scripts/flow-check.py  → 无输出=通过；有输出=问题列表（分号分隔）。"""
import sys, pathlib, yaml

def main():
    p = pathlib.Path('references/_shared/phase-order.yaml')
    try:
        d = yaml.safe_load(p.read_text(encoding='utf-8'))
        P = d['pipeline']
    except Exception as e:
        print(f'ERR:phase-order.yaml 解析失败 {e}'); return 1
    ids = [n['id'] for n in P]; errs = []
    for n in P:                                    # 1 引用有效性
        for k in ('next', 'after_trigger'):
            v = n.get(k)
            if isinstance(v, str) and v and not v.startswith('rerun_') and v not in ids:
                errs.append(f"{n['id']}.{k}->{v}")
        for v in (n.get('after_each') or []):
            if isinstance(v, str) and v not in ids and not v.startswith('rerun_'):
                errs.append(f"{n['id']}.after_each->{v}")
    reach = set()
    def walk(i):                                   # 2 可达性
        if i in reach or i not in ids: return
        reach.add(i)
        for n in P:
            if n['id'] == i and isinstance(n.get('next'), str) and n['next'] in ids:
                walk(n['next'])
    walk(ids[0])
    un = [x for x in ids if x not in reach]
    if un: errs.append('不可达:' + ','.join(un))
    for n in P:                                    # 3 除终态外须有 next
        if n['id'] != 'phase5_acceptance' and not n.get('next'):
            errs.append(f"{n['id']} 缺 next")
    for n in P:                                    # 4 执行类节点须声明 input
        if n.get('kind') in ('agent','owner_agent','parallel_agents','conditional_agent') and not n.get('input'):
            errs.append(f"{n['id']} 缺 input")
    print(';'.join(errs))
    return 0 if not errs else 2

if __name__ == '__main__':
    sys.exit(main())
