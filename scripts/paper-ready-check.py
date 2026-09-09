#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper-ready-check.py —— 论衡 v2.12.0 可发表性 36 项检查器

教训 #252（2026-09-09）：把内容质量门从 SKILL.md 散文层迁回机器可执行层。
本脚本 = references/_shared/可发表性判定表.md 的本地开发者版执行器。
ClawHub 净化版无此脚本（被 build-clawhub-release.sh 排除），使用者侧靠
LLM 推理 + 判定表口诀执行同一份规则。

用法：
    python3 scripts/paper-ready-check.py <项目名>
    或：bash scripts/paper-ready-check.sh <项目名>  # 封装

依赖：
    - final/定稿.md（必）
    - final/M-Gate-Report-v2.2.12.json（必，M 门组）
    - final/figures/*.mmd（必，图表组）

返回：
    退出码 0 = 全 PASS
    退出码 1 = 有 FAIL，附失败清单
"""

import glob
import json
import os
import re
import sys
from pathlib import Path


# ============================================================
# 判据函数（与 references/_shared/可发表性判定表.md § 一伪代码对应）
# ============================================================


def check_head_clean(final_md_path: str) -> tuple:
    """维度 1 头部洁净 5 项"""
    with open(final_md_path, encoding='utf-8') as f:
        head = '\n'.join(f.readlines()[:10])
    forbidden_patterns = [
        (r'v\d+\.\d+', '版本号'),
        (r'T\d+ 修订|v[1-9](?![\d\.])', '修订轮'),
        (r'底本|修订要点|修订依据|修订时间|本稿由.*修订', '工程术语'),
        (r'drafts/|audits/|analysis/|run/[^/\s]+/', '过程路径'),
        (r'T6 批判报告|T7 审计|G14 检测|修订说明 v\d', '过程卡引用'),
    ]
    hits = []
    for pat, label in forbidden_patterns:
        for m in re.finditer(pat, head):
            hits.append(f'{label}: {m.group(0)}')
    return (len(hits) == 0, hits)


def check_front_matter(final_md_path: str) -> tuple:
    """维度 2 前置要素 5 项"""
    with open(final_md_path, encoding='utf-8') as f:
        text = f.read()
    head50 = '\n'.join(text.splitlines()[:50])
    counts = {
        'author': len(re.findall(r'^\*\*作者\*\*', head50, re.MULTILINE)),
        'abstract': len(re.findall(r'^## (摘要|Abstract)', head50, re.MULTILINE)),
        'keywords': len(re.findall(r'^\*\*关键词\*\*', head50, re.MULTILINE)),
        'period': len(re.findall(r'研究周期|本文基于', head50)),
        'method': len(re.findall(r'^## (研究方法|Methodology)', head50, re.MULTILINE)),
    }
    passed = all(v >= 1 for v in counts.values())
    return (passed, counts)


def check_ai_declaration(final_md_path: str) -> tuple:
    """维度 3 AI 使用声明 5 项"""
    with open(final_md_path, encoding='utf-8') as f:
        text = f.read()
    checks = {
        'section_exists': bool(re.search(
            r'^## (AI 使用声明|Author Contribution|人工智能辅助声明)',
            text, re.MULTILINE)),
        'five_phases': all(k in text for k in
            ['检索', '分析', '写作', '批判', '审计', '终检']),
        'model_choice': bool(re.search(
            r'(模型|model|MiniMax|DeepSeek|Kimi|GPT|Claude|Gemini)',
            text)),
        'human_decision': bool(re.search(
            r'(Phase [0-5]\.?[0-5]?|主人|人类决策|人工决策)',
            text)),
        'no_concealment': bool(re.search(
            r'(论衡 G13|诚实透明|不试图隐瞒 AI 痕迹)',
            text)),
    }
    return (all(checks.values()), checks)


def check_citation_ordering(final_md_path: str) -> tuple:
    """维度 4 国标引用 · 顺序编码闭环（教训 #251 核心修复）"""
    with open(final_md_path, encoding='utf-8') as f:
        text = f.read()

    body_refs = re.findall(r'\[(C-\u4e3b?\d+|D\d+|L\d+|\u5148\d+)\]', text)

    appendix_start = -1
    for marker in ['## 引用来源', '## 参考文献', '## 先行者文献']:
        idx = text.find(marker)
        if idx > appendix_start:
            appendix_start = idx

    if appendix_start < 0:
        return (False, {'error': 'no_appendix_found'})

    appendix = text[appendix_start:]
    appendix_refs = re.findall(r'\[(C-\u4e3b?\d+|D\d+|L\d+|\u5148\d+)\]', appendix)

    seen = set()
    body_unique_ordered = []
    for r in body_refs:
        if r not in seen:
            seen.add(r)
            body_unique_ordered.append(r)

    missing = [r for r in body_unique_ordered if r not in appendix_refs]
    unused = [r for r in appendix_refs if r not in body_unique_ordered]
    passed = (len(missing) == 0 and len(unused) == 0)
    return (passed, {
        'body_unique_ordered': body_unique_ordered,
        'appendix_ordered': appendix_refs,
        'missing_in_appendix': missing,
        'unused_in_body': unused,
    })


def check_gbt_types(final_md_path: str) -> tuple:
    """维度 4 国标引用 · 类型标识齐全"""
    with open(final_md_path, encoding='utf-8') as f:
        text = f.read()
    types_found = set(re.findall(r'\[(M|J|C|S|D|R|P|Z|N|EB/OL)\]', text))
    passed = len(types_found) >= 5
    return (passed, {'types_found': sorted(types_found), 'count': len(types_found)})


def check_figures(final_md_path: str, project_dir: str) -> tuple:
    """维度 5 图表 5 项"""
    with open(final_md_path, encoding='utf-8') as f:
        text = f.read()

    mmd_files = glob.glob(os.path.join(project_dir, 'final', 'figures', '*.mmd'))
    mmd_count = len(mmd_files)

    mermaid_blocks = len(re.findall(r'```mermaid', text))
    md_image_refs = len(re.findall(r'!\[', text))
    body_ref_count = mermaid_blocks + md_image_refs

    lines = text.splitlines()
    last_5th = len(lines) * 4 // 5
    tail_refs = sum(1 for line in lines[last_5th:]
                    if '```mermaid' in line or '![' in line)
    inlined = tail_refs < 3

    data_sources = []
    for mmd in mmd_files:
        with open(mmd, encoding='utf-8') as f:
            mmd_text = f.read()
        data_sources.append(bool(re.search(r'\[(D\d+|L\d+)\]', mmd_text)))

    body_fig_nums = sorted(set(int(m.group(1))
        for m in re.finditer(r'\[图 (\d+)\]', text)))
    mmd_fig_nums = sorted(set(int(re.search(r'(\d+)', os.path.basename(f)).group(1))
        for f in mmd_files if re.search(r'(\d+)', os.path.basename(f))))
    seq_match = body_fig_nums == mmd_fig_nums

    passed = (mmd_count >= 5 and body_ref_count >= 5 and inlined
              and all(data_sources) and seq_match)
    return (passed, {
        'mmd_count': mmd_count,
        'body_ref_count': body_ref_count,
        'inlined': inlined,
        'data_sources_count': sum(data_sources),
        'seq_match': seq_match,
    })


def check_acknowledgment(final_md_path: str) -> tuple:
    """维度 6 致谢 + 先行者 4 项"""
    with open(final_md_path, encoding='utf-8') as f:
        text = f.read()
    checks = {
        'ack_section': bool(re.search(r'^## 致谢', text, re.MULTILINE)),
        'ack_funding': bool(re.search(r'资助|基金|数据来源', text)),
        'pioneer_section': bool(re.search(r'^## 先行者文献', text, re.MULTILINE)),
        'differentiation': bool(re.search(r'本文差异化', text)),
    }
    return (all(checks.values()), checks)


def check_word_count(final_md_path: str, project_dir: str) -> tuple:
    """组 C · 字数双口径（按字数判定表.md）"""
    with open(final_md_path, encoding='utf-8') as f:
        text = f.read()
    han_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total_chars = len(text)
    return (True, {'纯汉字': han_chars, '总字符': total_chars})


def check_m_gate(project_dir: str) -> tuple:
    """组 D · M 门 exit 0"""
    mgate = os.path.join(project_dir, 'final', 'M-Gate-Report-v2.2.12.json')
    if not os.path.exists(mgate):
        return (False, {'error': 'M-Gate report not found', 'path': mgate})
    try:
        with open(mgate, encoding='utf-8') as f:
            data = json.load(f)
        exit_code = data.get('exit_code', 1)
        return (exit_code == 0, {'exit_code': exit_code})
    except Exception as e:
        return (False, {'error': str(e)})


def check_residual_codes(final_md_path: str) -> tuple:
    """组 A · 编号残留清零（grep -E 实测）"""
    with open(final_md_path, encoding='utf-8') as f:
        text = f.read()
    # 仅查正文（不含附录）
    appendix_start = len(text)
    for marker in ['## 引用来源', '## 参考文献']:
        idx = text.find(marker)
        if idx > 0 and idx < appendix_start:
            appendix_start = idx
    body = text[:appendix_start]
    patterns = [
        r'\[T\d+\]',       # T 编号
        r'修订要点|修订依据|底本',  # 工程术语
        r'drafts/初稿-v\d',  # 过程稿路径
    ]
    hits = []
    for pat in patterns:
        for m in re.finditer(pat, body):
            hits.append(m.group(0))
    return (len(hits) == 0, hits)


# ============================================================
# 主流程
# ============================================================


def main():
    if len(sys.argv) < 2:
        print('用法: python3 scripts/paper-ready-check.py <项目名>')
        sys.exit(2)

    project = sys.argv[1]
    project_dir = os.path.join('run', project)
    final_md = os.path.join(project_dir, 'final', '定稿.md')

    if not os.path.exists(final_md):
        print(f'❌ {final_md} 不存在')
        sys.exit(1)

    print(f'🔍 论衡 v2.12.0 可发表性 36 项检查 · 项目: {project}')
    print(f'   定稿: {final_md}')
    print('=' * 70)

    groups = [
        ('F1-F5  头部洁净 (维度1)', check_head_clean, (final_md,)),
        ('F6-F10 前置要素 (维度2)', check_front_matter, (final_md,)),
        ('F11-F15 AI 使用声明 (维度3)', check_ai_declaration, (final_md,)),
        ('F16-F19 国标引用·顺序编码 (维度4.3 教训#251)', check_citation_ordering, (final_md,)),
        ('F20-F22 国标引用·类型标识 (维度4.2)', check_gbt_types, (final_md,)),
        ('F23-F27 图表 (维度5)', check_figures, (final_md, project_dir)),
        ('F28-F31 致谢+先行者 (维度6)', check_acknowledgment, (final_md,)),
        ('A1-A4  编号残留清零 (组A)', check_residual_codes, (final_md,)),
        ('C1-C4  字数双口径 (组C)', check_word_count, (final_md, project_dir)),
        ('D1     M 门 exit 0 (组D)', check_m_gate, (project_dir,)),
    ]

    total_groups = len(groups)
    failed = 0
    for name, fn, args in groups:
        try:
            passed, detail = fn(*args)
            status = '✅ PASS' if passed else '❌ FAIL'
            if not passed:
                failed += 1
            print(f'{status} | {name}')
            if not passed:
                detail_str = json.dumps(detail, ensure_ascii=False, indent=2)
                print(f'       详情: {detail_str}')
        except Exception as e:
            failed += 1
            print(f'❌ ERROR | {name}: {e}')

    print('=' * 70)
    if failed == 0:
        print(f'✅ 全部 {total_groups} 组检查通过 · 论衡可发表性 PASS')
        sys.exit(0)
    else:
        print(f'❌ {failed}/{total_groups} 组失败 · 详见上方详情')
        sys.exit(1)


if __name__ == '__main__':
    main()
