#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper-ready-check.py —— 可发表性判定表 48 项的机械分组检查。

P2-8 修复（2026-09-30）：实际跑的是 **10 个分组**（F1-F5/F6-F10/F11-F15/F16-F19/F20-F22/
F23-F27/F28-F31/A1-A4/C1-C4/D1），合计 34 项机械检查（判定表 48 项中的 34 项）；
剩余 14 项涉及作者声音、理论贡献、反方质量等语义判断，由 T8 按判定表完成，
不把「未实现」当作通过。
"""
import glob, json, os, re, sys
from pathlib import Path


def _read(path):
    with open(path, encoding="utf-8") as f: return f.read()

def _missing_or_empty(path):
    return not os.path.isfile(path) or os.path.getsize(path) == 0

def check_head_clean(path):
    if _missing_or_empty(path): return False, ['missing_or_empty_final']
    head="\n".join(_read(path).splitlines()[:10]); hits=[]
    for pat,label in [(r'v\d+\.\d+','版本号'),(r'T\d+ 修订|v[1-9](?![\d\.])','修订轮'),(r'底本|修订要点|修订依据|修订时间|本稿由.*修订','工程术语'),(r'drafts/|audits/|analysis/|run/[^/\s]+/','过程路径'),(r'T6 批判报告|T7 审计|G14 检测|修订说明 v\d','过程卡引用')]:
        hits += [f'{label}: {m.group(0)}' for m in re.finditer(pat,head)]
    return not hits,hits

def check_front_matter(path):
    text=_read(path); head="\n".join(text.splitlines()[:50])
    c={'author':len(re.findall(r'^\*\*作者\*\*',head,re.M)),'abstract':len(re.findall(r'^## (摘要|Abstract)',head,re.M)),'keywords':len(re.findall(r'^\*\*关键词\*\*',head,re.M)),'period':len(re.findall(r'研究周期|本文基于',head)),'method':len(re.findall(r'^## (研究方法|Methodology)',head,re.M))}
    return all(c.values()),c

def check_ai_declaration(path):
    text=_read(path); c={'section_exists':bool(re.search(r'^## (AI 使用声明|Author Contribution|人工智能辅助声明)',text,re.M)),'five_phases':all(k in text for k in ['检索','分析','写作','批判','审计','终检']),'model_choice':bool(re.search(r'(模型|model|MiniMax|DeepSeek|Kimi|GPT|Claude|Gemini)',text)),'human_decision':bool(re.search(r'(Phase [0-5]\.?[0-5]?|主人|人类决策|人工决策)',text)),'no_concealment':bool(re.search(r'(论衡 G13|诚实透明|不试图隐瞒 AI 痕迹)',text))}
    return all(c.values()),c

def check_citation_ordering(path):
    # P1-7 修复（2026-09-30）：作者年必须 (作者, 年份) 双键对账 + 编号首现序严格一致
    text = _read(path)
    headers = ('## 引用来源', '## 参考文献', '## 先行者文献')
    body_end = min((text.find(h) for h in headers if text.find(h) >= 0), default=len(text))
    body = text[:body_end]
    body_refs = re.findall(r'\[(C-主?\d+|C\d+|D\d+|L\d+|先\d+)\]', body)
    start = min((text.find(h) for h in headers if text.find(h) >= 0), default=-1)
    if start < 0:
        return False, {'error': 'no_appendix_found'}
    appendix = text[start:]
    app_refs = re.findall(r'\[(C-主?\d+|C\d+|D\d+|L\d+|先\d+)\]', appendix)

    # 提取 (作者, 年份) 双键 — 不再只匹配作者子串
    ay_re = re.compile(r'[（(]([^（）()]{1,80}?)[，,]\s*((?:19|20)\d{2})[）)]')
    def ay_pairs(blob):
        return [(m.group(1).strip(), m.group(2)) for m in ay_re.finditer(blob)]

    inline_body = ay_pairs(body)
    inline_app = ay_pairs(appendix)

    if not body_refs and not inline_body:
        return False, {'error': 'no_citations_in_body', 'internal_refs': 0, 'inline_citations': 0}

    if not body_refs:
        # 作者年模式：(作者, 年份) 双键覆盖 + 顺序严格一致
        body_set = set(inline_body)
        app_set = set(inline_app)
        body_order = list(dict.fromkeys(inline_body))
        app_order = list(dict.fromkeys(inline_app))
        missing = [p for p in body_order if p not in app_set]
        unused = [p for p in app_order if p not in body_set]
        order_match = body_order == app_order
        return (not missing) and (not unused) and bool(inline_app) and order_match, {
            'citation_mode': 'author_year',
            'body_inline_count': len(inline_body),
            'appendix_inline_count': len(inline_app),
            'missing_in_appendix': missing,
            'unused_in_body': unused,
            'order_match': order_match,
        }
    # 编号模式：双方向覆盖 + 首现序严格一致
    body_set = set(body_refs)
    app_set = set(app_refs)
    ordered = list(dict.fromkeys(body_refs))
    app_ordered = list(dict.fromkeys(app_refs))
    missing = [x for x in ordered if x not in app_set]
    unused = [x for x in app_ordered if x not in body_set]
    order_match = ordered == app_ordered
    return (not missing) and (not unused) and order_match, {
        'body_unique_ordered': ordered,
        'appendix_ordered': app_ordered,
        'missing_in_appendix': missing,
        'unused_in_body': unused,
        'order_match': order_match,
    }

def check_gbt_types(path):
    found=set(re.findall(r'\[(M|J|C|S|D|R|P|Z|N|EB/OL)\]',_read(path))); return len(found)>=5,{'types_found':sorted(found),'count':len(found)}

def check_figures(path,project):
    text=_read(path); files=glob.glob(os.path.join(project,'final','figures','*.mmd')); blocks=len(re.findall(r'```mermaid',text)); refs=len(re.findall(r'!\[',text)); lines=text.splitlines(); tail=sum(1 for x in lines[len(lines)*4//5:] if '```mermaid' in x or '![' in x); sources=[]
    for f in files:sources.append(bool(re.search(r'\[(D\d+|L\d+)\]',_read(f))))
    body=sorted(set(int(m.group(1)) for m in re.finditer(r'\[图 (\d+)\]',text))); nums=sorted(set(int(re.search(r'(\d+)',os.path.basename(f)).group(1)) for f in files if re.search(r'(\d+)',os.path.basename(f))))
    d={'mmd_count':len(files),'body_ref_count':blocks+refs,'inlined':tail<3,'data_sources_count':sum(sources),'seq_match':body==nums}; return len(files)>=5 and blocks+refs>=5 and tail<3 and all(sources) and body==nums,d

def check_acknowledgment(path):
    t=_read(path); c={'ack_section':bool(re.search(r'^## 致谢',t,re.M)),'ack_funding':bool(re.search(r'资助|基金|数据来源',t)),'pioneer_section':bool(re.search(r'^## 先行者文献',t,re.M)),'differentiation':bool(re.search(r'本文差异化',t))}; return all(c.values()),c

def check_word_count(path,project):
    t=_read(path); m=re.search(r'^## (参考文献|数据来源|案例来源|先行者文献|AI 使用声明|致谢)',t,re.M); body=t[:m.start()] if m else t; n=len(re.findall(r'[\u4e00-\u9fff]',body)); return n>=2000,{'正文字数(纯汉字)':n,'正文字符':len(body),'分层下限(纯汉字)':2000}

def check_m_gate(project):
    # P1-6 修复（2026-09-30）：glob 文件名 + 四档 + 字段对齐 M-Gate-Algorithm-appendix.md。
    # 旧版硬编码 'M-Gate-Report-v2.2.12.json' + 沿用已废止的 exit_code，
    # 导致 "exit_code=0 且 判定档位=不通过" 被错误放行。
    pattern = os.path.join(project, 'final', 'M-Gate-Report-*.json')
    matches = sorted(glob.glob(pattern))
    if not matches:
        # 保留旧错误名以兼容既有 fail-closed 回归（missing / empty 同族）
        return False, {'error': 'missing_or_empty_m_gate_report', 'pattern': pattern}
    if len(matches) > 1:
        # 同一项目内多份 M 门报告 → 必须删除陈旧份；否则无法判定本次终检读哪份
        return False, {'error': 'multiple_m_gate_reports_must_be_unique', 'matches': matches}
    p = matches[0]
    if _missing_or_empty(p):
        return False, {'error': 'missing_or_empty_m_gate_report', 'path': p}
    try:
        d = json.loads(_read(p))
        if not isinstance(d, dict):
            return False, {'error': 'm_gate_report_not_object', 'path': p}
        verdict = d.get('判定档位')
        if verdict is None:
            # 缺四档字段（含旧版 exit_code 伪报告 / 占位）→ fail-closed，标记 placeholder
            return False, {'error': 'placeholder_or_missing_verdict', 'placeholder': True,
                           'raw_keys': sorted(d.keys()), 'path': p}
        allowed = {'通过', '不通过', '无法判定', '路径或参数错误'}
        if verdict not in allowed:
            return False, {'error': 'unknown_verdict_field', '判定档位': verdict, 'allowed': sorted(allowed)}
        return verdict == '通过', {'判定档位': verdict, 'path': p}
    except Exception as exc:
        return False, {'error': str(exc), 'path': p}

def check_residual_codes(path):
    if _missing_or_empty(path): return False, ['missing_or_empty_final']
    t=_read(path); end=min((t.find(x) for x in ('## 引用来源','## 参考文献') if t.find(x)>0),default=len(t)); body=t[:end]; pats=[r'\[T\d+\]',r'修订要点|修订依据|底本',r'drafts/初稿-v\d',r'(?:\[|（)A[1-9](?:\]|）)',r'T\d+\s*分析员|T6 批判报告|G14 检测',r'降级纪律|降级模式|信任级别|主人投喂',r'≥\s*\d+\s*字',r'\d{1,2}/30|Minor Revision|维度评分',r'感谢\s*[0-9一二三四五六七八九十]+\s*位匿名审稿人',r'\[(?:L|D|B|C)\d+\]']; hits=[m.group(0) for p in pats for m in re.finditer(p,body)]; return not hits,hits

USAGE='用法: python3 scripts/paper-ready-check.py <项目名>'
def main():
    if len(sys.argv)>=2 and sys.argv[1] in ('-h','--help'): print(USAGE); print('机械执行 34 项；其余 14 项由 T8 语义核验。'); return 0
    if len(sys.argv)<2: print(USAGE); return 2
    project=sys.argv[1]; root=Path(__file__).resolve().parent.parent; pd=root/'run'/project; final=pd/'final'/'定稿.md'
    if _missing_or_empty(final): print(f'❌ 缺失或空定稿：{final}'); return 1
    print(f'🔍 论衡可发表性机械实现 34/48 项 · 项目: {project}'); groups=[('F1-F5 头部洁净',check_head_clean,(str(final),)),('F6-F10 前置要素',check_front_matter,(str(final),)),('F11-F15 AI 使用声明',check_ai_declaration,(str(final),)),('F16-F19 引用闭环',check_citation_ordering,(str(final),)),('F20-F22 国标引用',check_gbt_types,(str(final),)),('F23-F27 图表',check_figures,(str(final),str(pd))),('F28-F31 致谢+先行者',check_acknowledgment,(str(final),)),('A1-A4 编号残留',check_residual_codes,(str(final),)),('C1-C4 正文字数',check_word_count,(str(final),str(pd))),('D1 M门',check_m_gate,(str(pd),))]; failed=0
    for name,fn,args in groups:
        try: ok,detail=fn(*args)
        except Exception as e: ok,detail=False,{'error':str(e)}
        print(('✅ PASS' if ok else '❌ FAIL')+' | '+name)
        if not ok: failed+=1; print('       '+json.dumps(detail,ensure_ascii=False))
    print(f'❌ {failed}/{len(groups)} 组失败' if failed else f'✅ 机械 34 项检查通过；语义 14 项仍须 T8')
    return 1 if failed else 0
if __name__=='__main__': raise SystemExit(main())
