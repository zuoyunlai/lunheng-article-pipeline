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

HISTORY_PARTS = ('reports/', 'archive/', 'CHANGELOG', '教训索引', '.bak.')


def managed_markdown():
    for p in sorted(ROOT.rglob('*.md')):
        rel = p.relative_to(ROOT).as_posix()
        if any(x in rel for x in HISTORY_PARTS):
            continue
        yield p, rel


def lines_with_values(pattern):
    """Return (path, value tuple, line) for one semantic declaration family."""
    hits = []
    rx = re.compile(pattern)
    for p, rel in managed_markdown():
        for line in p.read_text(encoding='utf-8').splitlines():
            match = rx.search(line)
            if match:
                hits.append((rel, tuple(int(x) for x in match.groups()), line.strip()))
    return hits


WORD_RANGE = re.compile(r'(\d{4})\s*[-–—]\s*(\d{4})\s*字')
WORD_HEAVY = re.compile(r'(?:≥|>=)\s*(\d{4})\s*字|(\d{4})\s*\+\s*字')
TIER_LABELS = {'轻量': (2000, 3000), '中段': (3000, 5000)}


def tier_declarations():
    """Classify tier declarations by the label nearest the number.

    Labels may precede or follow the range (e.g. “轻量档（2000-3000 字）” and
    “2000-3000 字轻量”), so a fixed left-to-right window would pair the wrong
    label with the wrong range on packed single lines.
    """
    hits = {name: [] for name in TIER_LABELS}
    heavy = []
    for p, rel in managed_markdown():
        for line in p.read_text(encoding='utf-8').splitlines():
            for match in WORD_RANGE.finditer(line):
                lo = max(0, match.start() - 12)
                hi = min(len(line), match.end() + 12)
                near = line[lo:hi]
                for label in TIER_LABELS:
                    if label in near and not any(l in near for l in TIER_LABELS if l != label):
                        # Capture the range actually written in the doc, not the
                        # constant from TIER_LABELS — prior identity comparison
                        # silently passed every drift (P0-3 audit, 2026-09-30).
                        actual = tuple(int(x) for x in match.groups())
                        hits[label].append((rel, actual, line.strip()))
            for match in WORD_HEAVY.finditer(line):
                near = line[max(0, match.start() - 12):match.end() + 12]
                if '重量' in near:
                    heavy.append((rel, int(match.group(1) or match.group(2)), line.strip()))
    return hits, heavy


def check_counts():
    c = yaml.safe_load(COUNTS.read_text(encoding='utf-8'))
    errors = []

    def compare(name, expected, hits):
        if not hits:
            errors.append(f'{name}: no managed declaration found')
            return
        values = set()
        for _, value, _ in hits:
            if isinstance(value, tuple) and len(value) == 1:
                value = value[0]
            values.add(value)
        if values != {expected}:
            sample = '; '.join(f'{rel}={value}' for rel, value, _ in hits[:8])
            errors.append(f'{name}: expected {expected}, found {sorted(values, key=str)} [{sample}]')

    # Each semantic cluster is intentionally independent: conceptual roles (11)
    # and physical role-card files (12) are not one contradictory count.
    compare('conceptual_roles', c['role_cards'], lines_with_values(
        r'(?:论衡(?:有|共)|核心角色|角色速查|角色卡职责)[^\n]{0,35}?(\d+)\s*张角色卡'))
    # Physical files are measured from the authoritative directory, not prose.
    role_files = len(list((ROOT / 'references/agents').glob('*.md')))
    if role_files != c['role_card_files']:
        errors.append(f"physical_role_files: counts.yaml={c['role_card_files']} but references/agents has {role_files}")
    compare('dispatch_files', c['dispatch_files'], lines_with_values(
        r'dispatch[^\n]{0,30}?(\d+)\s*(?:个)?文件'))
    compare('g14_recheck_max', 2, lines_with_values(
        r'复检[^\n]{0,20}?≤\s*(\d+)\s*轮'))

    # Word tiers: labelled declarations only, so unrelated section-length
    # examples (e.g. “§4 1500-3000 字”) never enter the same value set.
    tier_hits, heavy = tier_declarations()
    for label, expected in TIER_LABELS.items():
        compare(f'word_tier_{label}', expected, tier_hits[label])
    compare('word_tier_重量', c['word_tiers']['heavy_min'], heavy)

    # The version count is a measured property of the version-check source,
    # not a prose number. This catches the P1-8 class without scanning history.
    version_script = (ROOT / 'scripts/check-version.sh').read_text(encoding='utf-8')
    measured = len(re.findall(r'^\s*"[^"|]+\|v\$EXPECTED\|1"', version_script, re.M))
    if measured != c['version_files']:
        errors.append(f"version_files: counts.yaml={c['version_files']} but check-version.sh has {measured} entries")
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
    # yaml-driven template capability matrix（v2.15.x 第二批机械门）。
    # 改本节 = 改 references/_shared/真源/template-contracts.yaml；勿在门内复刻字段清单。
    tcontracts = ROOT / "references/_shared/真源/template-contracts.yaml"
    if not tcontracts.is_file():
        errors.append("template-contracts.yaml missing")
    else:
        import yaml
        contracts = yaml.safe_load(tcontracts.read_text(encoding="utf-8")).get("templates", {})
        for rel, spec in contracts.items():
            text = (ROOT / "references/templates" / rel).read_text(encoding="utf-8")
            for token in spec.get("required_fields", []):
                if token not in text:
                    errors.append(f"{rel}[{spec.get('mode','?')}]: missing required field: {token}")
    status=(ROOT/'references/templates/status-template.md').read_text(encoding='utf-8')
    # status telemetry contract keys are also covered by yaml above; this loop is
    # the historical hardcoded list, kept as a defence-in-depth sanity check that
    # the yaml entry actually exists.
    for token in ('gate_telemetry','current_run','cumulative','last_result','零触发'):
        if token not in status: errors.append(f'status telemetry contract missing: {token}')
    # The generator is the sole language-policy text source; every managed file must carry its marker.
    import importlib.util
    spec_imp=importlib.util.spec_from_file_location('lang', ROOT/'scripts/inject-lang-policy.py')
    mod=importlib.util.module_from_spec(spec_imp); spec_imp.loader.exec_module(mod)
    missing_policy = []
    for path,_ in mod.targets(str(ROOT)):
        if mod.MARKER not in Path(path).read_text(encoding="utf-8"):
            missing_policy.append(str(Path(path).relative_to(ROOT)))
    # Reverse verification: not just MARKER present, but exact LINE match (no stale variants)
    stale_policy = []
    for path,_ in mod.targets(str(ROOT)):
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if mod.MARKER in line and line != mod.LINE:
                stale_policy.append(str(Path(path).relative_to(ROOT)))
                break
    if missing_policy:
        errors.append(f"language policy missing in {len(missing_policy)} files: {missing_policy[:5]}{"..." if len(missing_policy)>5 else ""}")
    if stale_policy:
        errors.append(f"language policy stale variant in {len(stale_policy)} files: {stale_policy[:5]}{"..." if len(stale_policy)>5 else ""}")
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
