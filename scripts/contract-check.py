#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build-time contracts for high-drift declarations."""
from pathlib import Path
import re, sys, yaml
ROOT=Path(__file__).resolve().parents[1]
COUNTS=ROOT/'references/_shared/真源/counts.yaml'

def files(rel): return sorted((ROOT/rel).glob('*.md'))
def numbers(text, patterns):
    out=[]
    for p in patterns: out += [int(x) for x in re.findall(p,text)]
    return out

def check_counts():
    c=yaml.safe_load(COUNTS.read_text(encoding='utf-8')); errors=[]
    # distinct semantic clusters: conceptual roles and physical cards are intentionally separate
    clusters={
      'conceptual_roles': (c['role_cards'], [r'(?:概念角色|角色数|角色卡数)[^\n]{0,20}?(\d+)']),
      'physical_role_files': (c['role_card_files'], [r'(?:物理角色卡文件数|角色卡文件数)[^\n]{0,20}?(\d+)']),
      'dispatch_files': (c['dispatch_files'], [r'dispatch[^\n]{0,30}?(\d+)\s*(?:个)?文件']),
      'g14_recheck_max': (2, [r'复检[^\n]{0,20}?≤\s*(\d+)\s*轮']),
    }
    for name,(expected,pats) in clusters.items():
      vals=[]
      for p in ROOT.rglob('*.md'):
        rel=p.relative_to(ROOT).as_posix()
        if any(x in rel for x in ('reports/','archive/','CHANGELOG','教训索引')): continue
        vals += numbers(p.read_text(encoding='utf-8'),pats)
      if vals and set(vals)!={expected}: errors.append(f'{name}: expected {expected}, found {sorted(set(vals))}')
    return errors

def check_version_manifest():
    errors=[]
    sync=(ROOT/'scripts/sync-version.sh').read_text(encoding='utf-8')
    check=(ROOT/'scripts/check-version.sh').read_text(encoding='utf-8')
    # Both lists are operational views of the same version-bearing set; drift here
    # was the root of the historical "file count" false confidence.
    # Prefer the explicit check matrix, then require all listed files to exist.
    expected=set(re.findall(r'^\s*"(@?[^"|]+)\|v\$EXPECTED\|1"', check, re.M))
    sync_paths=set(re.findall(r'^\s*"(@?[^"|]+)\|(?:header|body_header|replace)"', sync, re.M))
    sync_paths.discard('')
    # SKILL.md is the version source itself: sync writes its body header, while
    # check-version validates it separately outside CHECKS.
    sync_paths.discard('@SKILL.md')
    if expected != sync_paths:
        errors.append(f'version manifest drift: sync={len(sync_paths)} check={len(expected)} symmetric_difference={sorted(sync_paths ^ expected)[:8]}')
    for raw in sorted(expected):
        rel=raw.lstrip('@')
        if not (ROOT/rel if raw.startswith('@') else ROOT/'references'/rel).is_file():
            errors.append(f'version manifest missing file: {raw}')
    return errors

def check_templates_and_policy():
    errors=[]
    lite=(ROOT/'references/templates/任务简报-template-lite.md').read_text(encoding='utf-8')
    full=(ROOT/'references/templates/任务简报-template.md').read_text(encoding='utf-8')
    for token in ('目标语言','figure_decision','同行评审','方法论留档','压力测试轮'):
        if token not in lite: errors.append(f'lite template missing required field: {token}')
    for token in ('目标语言','figure_decision','owner_peer_review_opt_out'):
        if token not in full: errors.append(f'full template missing required field: {token}')
    status=(ROOT/'references/templates/status-template.md').read_text(encoding='utf-8')
    for token in ('gate_telemetry','current_run','cumulative','last_result','零触发'):
        if token not in status: errors.append(f'status telemetry contract missing: {token}')
    # The generator is the sole language-policy text source; every managed file must carry its marker.
    import importlib.util
    spec=importlib.util.spec_from_file_location('lang', ROOT/'scripts/inject-lang-policy.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    for path,_ in mod.targets(str(ROOT)):
        if mod.MARKER not in Path(path).read_text(encoding='utf-8'):
            errors.append(f'language policy missing: {Path(path).relative_to(ROOT)}')
    return errors

def check_dispatch():
    errors=[]
    specs={'G14-中文AI痕迹检测器.md':('g14_style_gate','2'),'T9-同行评审.md':('t9_review',None)}
    for name,(node,rounds) in specs.items():
      p=ROOT/'references/dispatch'/name; t=p.read_text(encoding='utf-8')
      if node not in t: errors.append(f'{name}: missing generated node contract {node}')
      if rounds and '复检 ≤2 轮' not in t: errors.append(f'{name}: missing recheck contract')
      if name.startswith('T9') and '默认触发' not in t: errors.append(f'{name}: missing default trigger contract')
    return errors

def main():
    errors=check_counts()+check_version_manifest()+check_dispatch()+check_templates_and_policy()
    if errors: print('\n'.join(errors)); return 1
    print('contract-check: PASS'); return 0
if __name__=='__main__': raise SystemExit(main())
