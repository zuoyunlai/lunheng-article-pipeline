#!/usr/bin/env python3
"""flow-schema.py — 声明式「跨载体一致性」校验器（可复用治理引擎，批次 4-B）

用途：
  把「真源 vs 派生视图」一致性与「协议不得从载体静默消失」两类治理判据，从特定技能抽成
  **可移植**的声明式校验器：一份 YAML schema 声明「哪些载体文件必须存在、哪些关键 token
  必须/不得出现在哪些载体里」，本脚本逐条校验并输出问题列表。论衡自身继续用 flow-check.py
  做完整校验（旗舰用例）；本脚本是抽离出的**通用引擎 + 演示实例**（flow-schema.lunheng.yaml），
  证明「规则引擎」与「具体规则」可解耦、可被其他多 Agent 技能复用，不必每次重写 flow-check。

设计（fail-closed，与 flow-check 同源）：
  - 重复键 YAML 硬失败（后键静默覆盖前键 = 真源失真）。
  - 断言不满足 = 报错并 exit 2；无报错 = exit 0（与 flow-check 一致）。
  - 只做「存在性」机械校验，不复制判据全文，防双判据漂移。

schema 格式（YAML）：
  version: 1
  carriers:                      # 载体别名 → 相对路径（相对本脚本上上级 = 仓库根）
    status: references/templates/status-template.md
    registry: references/_shared/真源/performance-benchmarks.md
  assertions:
    - id: smoke-protocol-in-carriers    # kebab-case，用于报告定位
      kind: files_exist                 # files_exist | tokens_exist | tokens_absent
      carriers: [status, registry]      # 引用上面的别名
      tokens: [smoke_run_id]            # 仅 tokens_exist / tokens_absent 需要

用法：
  python3 scripts/flow-schema.py [--schema scripts/flow-schema.lunheng.yaml]
退出码：0 = 通过 / 2 = 有断言失败 / 1 = schema 解析失败
"""
import argparse
import pathlib
import sys

import yaml


class UniqueKeyLoader(yaml.SafeLoader):
    """重复键 → 硬失败（后键静默覆盖前键 = 真源失真）。"""


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

KINDS = ('files_exist', 'tokens_exist', 'tokens_absent')



def _load_schema(schema_path):
    raw = schema_path.read_text(encoding='utf-8')
    try:
        return yaml.load(raw, Loader=UniqueKeyLoader)
    except yaml.YAMLError as e:
        print(f'ERR:schema 解析失败（含重复键） {e}')
        return None
    except Exception as e:  # noqa: BLE001
        print(f'ERR:schema 解析失败 {e}')
        return None


def _carrier_paths(root, carriers, names, errs):
    """别名 → 绝对路径；未定义别名 = fail-closed。"""
    out = {}
    for name in names:
        if name not in carriers:
            errs.append(f'carrier 别名未定义: {name}')
            continue
        out[name] = root / carriers[name]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--schema', default='scripts/flow-schema.lunheng.yaml')
    ap.add_argument('--root', default=None,
                    help='仓库根（默认 = 本脚本上上级）；schema 与载体路径相对它解析')
    args = ap.parse_args(argv)

    root = (pathlib.Path(args.root).resolve() if args.root
            else pathlib.Path(__file__).resolve().parent.parent)
    schema_path = pathlib.Path(args.schema)
    if not schema_path.is_absolute():
        schema_path = root / schema_path
    if not schema_path.is_file():
        print(f'ERR:schema 文件不存在 {schema_path}')
        return 1
    sc = _load_schema(schema_path)
    if sc is None:
        return 1
    if not isinstance(sc, dict):
        print('ERR:schema 顶层不是映射')
        return 1

    carriers = sc.get('carriers') or {}
    assertions = sc.get('assertions') or []
    if not isinstance(carriers, dict) or not isinstance(assertions, list):
        print('ERR:schema 缺 carriers（映射）或 assertions（列表）')
        return 1

    errs = []
    for a in assertions:
        if not isinstance(a, dict):
            errs.append(f'断言非映射: {a!r}')
            continue
        aid = a.get('id') or '(无 id)'
        kind = a.get('kind')
        names = a.get('carriers') or []
        if kind not in KINDS:
            errs.append(f'[{aid}] 未知 kind: {kind}')
            continue
        paths = _carrier_paths(root, carriers, names, errs)
        if kind == 'files_exist':
            for name, p in paths.items():
                if not p.is_file():
                    errs.append(f'[{aid}] 载体不存在: {carriers[name]}')
            continue
        tokens = a.get('tokens') or []
        if not tokens:
            errs.append(f'[{aid}] kind={kind} 但 tokens 为空')
            continue
        for name, p in paths.items():
            if not p.is_file():
                errs.append(f'[{aid}] 载体不存在: {carriers[name]}')
                continue
            text = p.read_text(encoding='utf-8', errors='replace')
            for tok in tokens:
                hit = tok in text
                if kind == 'tokens_exist' and not hit:
                    errs.append(f'[{aid}] {carriers[name]} 缺「{tok}」')
                if kind == 'tokens_absent' and hit:
                    errs.append(f'[{aid}] {carriers[name]} 仍含禁用 token「{tok}」')

    print(';'.join(errs))
    return 0 if not errs else 2


if __name__ == '__main__':
    sys.exit(main())
