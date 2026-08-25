#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
论衡 ClawHub 净化包 —— shell 命令剥离脚本
用途：把「人类 host shell 验证示例」里的 shell 命令替换为自然语言，
      删除 bash/sh 代码块，保留 python 伪代码（算法判定的精确描述）。

原则（主人 2026-08-24 拍板）：
  - 净化包（ClawHub 上传用）完全移除所有 shell 命令和 .sh 文件
  - 不影响论衡技能功能：检测逻辑/三角验证/角色卡职责保留
  - bash/sh = 人类验证命令（agent 零 exec 用不上）→ 删除
  - python 伪代码 = M 门算法判定逻辑的精确描述 → 保留（agent 靠 LLM 推理模拟）
"""
import re
import sys

# 裸 shell 动词 → 自然语言（长词优先，避免子串误伤）
VERB_PATTERNS = [
    (r'sha256sum', '校验哈希'),
    (r'md5sum', '校验 MD5'),
    (r'wc -l', '统计行数'),
    (r'comm -23', '求差集'),
    (r'comm -13', '求差集'),
    (r'sort -u', '去重'),
    (r'grep -oE', '匹配'),
    (r'grep -oP', '匹配'),
    (r'grep -cE', '计数'),
    (r'grep -c', '计数'),
    (r'grep -o', '匹配'),
    (r'\bgrep\b', '检查'),
    (r'\bawk\b', '提取'),
    (r'\bcomm\b', '对比'),
    (r'\bsed\b', '替换'),
    (r'\bcat\b', '查看'),
    (r'\bls\b', '列出'),
    (r'\bdiff\b', '对比'),
    (r'\bcp\b', '复制'),
    (r'\bmv\b', '移动'),
]


def is_shell_codeblock_lang(lang: str) -> bool:
    return lang.strip().lower() in ('bash', 'sh', 'shell', 'zsh', 'fish')


def strip_shell(s: str) -> str:
    # ---- 0. 删除「跨平台等价命令」类表格（人类验证命令参考，agent 用不上）----
    s = re.sub(
        r'\*\*跨平台等价命令\*\*.*?(?=\n\n\*\*|\n###|\Z)',
        '',
        s,
        flags=re.DOTALL
    )

    # ---- 0b. 删除目录树里 scripts/ .github/ .sh .yml 行（开发者维护工具，净化包已剥离）----
    s = re.sub(r'[^\n]*(scripts/|\.github/)[^\n]*\n', '', s)
    s = re.sub(r'[^\n]*\.(sh|yml)\s*(#.*)?\n', '', s)

    lines = s.split('\n')
    out = []
    i = 0
    in_codeblock = False
    codeblock_lang = ''
    codeblock_start = -1

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # ---- 代码块围栏检测 ----
        if stripped.startswith('```'):
            if not in_codeblock:
                # 进入代码块
                in_codeblock = True
                codeblock_lang = stripped[3:].strip()
                codeblock_start = i
                if is_shell_codeblock_lang(codeblock_lang):
                    # shell 代码块：跳过直到结束围栏（不输出）
                    i += 1
                    while i < len(lines) and not lines[i].strip().startswith('```'):
                        i += 1
                    # 跳过结束围栏
                    i += 1
                    in_codeblock = False
                    codeblock_lang = ''
                    continue
                else:
                    # 非 shell 代码块（python/json/无标记）：保留围栏
                    out.append(line)
                    i += 1
                    continue
            else:
                # 代码块结束围栏
                in_codeblock = False
                codeblock_lang = ''
                out.append(line)
                i += 1
                continue

        # ---- 代码块内（非 shell）----
        if in_codeblock:
            # 无语言标记的代码块（混合伪代码）内部也做 shell 替换；python/json 原样保留
            if codeblock_lang == '':
                out.append(process_inline(line))
            else:
                out.append(line)
            i += 1
            continue

        # ---- 正文行处理 ----
        line = process_inline(line)
        out.append(line)
        i += 1

    return '\n'.join(out)


def process_inline(line: str) -> str:
    """处理正文行内的 shell 命令（反引号内 + 裸动词）"""

    # 1. 反引号内的 shell 命令 → 自然语言
    def replace_backtick(m):
        content = m.group(1)
        is_shell = (
            '|' in content or '>' in content or '<' in content
            or '/tmp/' in content
            or re.search(r'\b(grep|awk|sed|comm|cp|sha256sum|md5sum|wc|sort|uniq|diff|ls|cat|mv|chmod|rm)\b', content)
        )
        if not is_shell:
            return m.group(0)  # 非 shell 命令，保留
        # 提取检测对象（编号模式或文件路径）
        num = re.search(r'\[(?:D|C|C-主|L|先)\d+\]', content)
        if num:
            return f'（检查 {num.group(0)}）'
        fpath = re.search(r'(?:drafts/|final/|literature/|data/|cases/|analysis/|audits/|run/)[^\s`|>]*\.md', content)
        if fpath:
            return f'（检查 {fpath.group(0)}）'
        return '（检查）'

    line = re.sub(r'`([^`]*)`', replace_backtick, line)

    # 2. 裸 shell 动词 → 自然语言
    for pat, repl in VERB_PATTERNS:
        line = re.sub(pat, repl, line)

    # 2b. .sh 文件引用 → 泛化（scanner 命中点）
    line = re.sub(r'`[^`]*\.sh`', '`shell 脚本`', line)
    line = re.sub(r'(?<!`)\bm_exist_1_diff\.sh\b(?!`)', 'shell 脚本', line)
    line = re.sub(r'\b(sync-version|check-version|build-clawhub-release)\.sh\b', '版本维护脚本', line)
    line = re.sub(r'（shell 版）|（shell 脚本）', '（脚本版）', line)

    # 2c. sha256 占位符 → 泛化
    line = line.replace('[SHA256-PENDING:HOST-VERIFY]', '[哈希校验待主人回填]')
    line = line.replace('sha256 指纹', '哈希指纹')

    # 3. 清理「零 exec 声明」里的具体命令列举 → 「shell 命令」
    line = re.sub(r'（`[^`]*`(?:/`[^`]*`)*\s*等）', '（shell 命令）', line)
    line = re.sub(r'\(`[^`]*`(?:/`[^`]*`)*\s*等\)', '（shell 命令）', line)

    return line


if __name__ == '__main__':
    for path in sys.argv[1:]:
        with open(path, encoding='utf-8') as f:
            orig = f.read()
        cleaned = strip_shell(orig)
        if cleaned == orig:
            print(f'SKIP: {path}')
            continue
        with open(path, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        dl = orig.count('\n') - cleaned.count('\n')
        print(f'OK: {path} (-{dl} 行)')
