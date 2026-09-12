#!/usr/bin/env python3
"""论衡流程图检查（v2.12.28 新增；v2.12.30 扩）

检查项：
  1 引用有效性（next / after_trigger / after_each 指向已知节点或 rerun_* 动作）
  2 可达性（无孤立节点）
  3 除终态外须有 next
  4 入参类节点须声明 input（agent / owner_agent / parallel_agents / conditional_agent /
    advisory_agent / bounded_loop / conditional_review_window）
  5 执行类节点须声明 output（同上，去掉 conditional_review_window）
  6 入参链闭合：被 ≥2 个节点声明为 input 的受管路径，须有节点以 output 生产
  7 YAML 重复键**硬失败**（后键静默覆盖前键 = 真源失真）

用法：python3 scripts/flow-check.py  → 无输出=通过；有输出=问题列表（分号分隔）。"""
import pathlib, re, sys, yaml

# 执行类节点：产出受管产物，必须 input + output
EXEC_KINDS = (
    'agent', 'owner_agent', 'parallel_agents', 'conditional_agent',
    'advisory_agent', 'bounded_loop',
)
# 入参类节点：只需 input
INPUT_KINDS = EXEC_KINDS + ('conditional_review_window',)

# 路径 token：必须含目录分隔符，扩展名 ∈ md/svg/json/yaml（保守匹配，宁少勿误报）
PATH_RE = re.compile(r'[A-Za-z0-9_\-\u4e00-\u9fff]+/[A-Za-z0-9_\-\u4e00-\u9fff/{}.]+\.(?:md|svg|json|yaml)')


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
    return {_norm(m) for m in PATH_RE.findall(str(decl))}


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

    for n in P:                                    # 4 入参类节点须声明 input
        if n.get('kind') in INPUT_KINDS and not n.get('input'):
            errs.append(f"{n['id']} 缺 input")

    for n in P:                                    # 5 执行类节点须声明 output
        if n.get('kind') in EXEC_KINDS and not n.get('output'):
            errs.append(f"{n['id']} 缺 output")

    consumers, produced = {}, set()                # 6 入参链闭合
    for n in P:
        produced |= _paths(n.get('output'))
        produced |= _paths(n.get('output_if_triggered'))
        for t in _paths(n.get('input')):
            consumers.setdefault(t, []).append(n['id'])
        for t in _paths(n.get('inputs')):
            consumers.setdefault(t, []).append(n['id'])
    for t, who in sorted(consumers.items()):
        if len(who) >= 2 and t not in produced:
            errs.append(f'{t} 被 {len(who)} 节点消费但无生产者({",".join(who)})')

    print(';'.join(errs))
    return 0 if not errs else 2


if __name__ == '__main__':
    sys.exit(main())
