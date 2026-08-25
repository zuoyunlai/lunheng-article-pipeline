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
    # 嵌套代码块深度跟踪（v2.5.2 修复：支持 ````` 外层 + ``` 内层嵌套）
    codeblock_stack = []  # [(lang, backtick_count), ...]

    def _backtick_count(line: str) -> int:
        """返回行首反引号数量，若非围栏行返回 0"""
        stripped = line.strip()
        m = re.match(r'(`{3,})', stripped)
        return len(m.group(1)) if m else 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        bt_count = _backtick_count(line)

        # ---- 代码块围栏检测（支持嵌套）----
        if bt_count > 0:
            if not codeblock_stack:
                # 进入最外层代码块
                lang = stripped[bt_count:].strip()
                codeblock_stack.append((lang, bt_count))
                if is_shell_codeblock_lang(lang):
                    # shell 代码块：跳过内容直到匹配的结束围栏
                    i += 1
                    while i < len(lines):
                        end_bt = _backtick_count(lines[i])
                        if end_bt == bt_count:
                            break
                        i += 1
                    # 跳过结束围栏
                    i += 1
                    codeblock_stack.pop()
                    continue
                else:
                    # 非 shell 代码块：保留围栏
                    out.append(line)
                    i += 1
                    continue
            else:
                # 嵌套代码块：内层围栏
                inner_lang = stripped[bt_count:].strip()
                if bt_count < codeblock_stack[-1][1]:
                    # 更少的反引号 = 进入内层代码块
                    codeblock_stack.append((inner_lang, bt_count))
                    if is_shell_codeblock_lang(inner_lang):
                        # 内层 shell 代码块：跳过
                        i += 1
                        while i < len(lines):
                            end_bt = _backtick_count(lines[i])
                            if end_bt == bt_count:
                                break
                            i += 1
                        i += 1  # 跳过结束围栏
                        codeblock_stack.pop()
                        continue
                    else:
                        out.append(line)
                        i += 1
                        continue
                elif bt_count == codeblock_stack[-1][1]:
                    # 同层围栏 = 结束当前代码块
                    codeblock_stack.pop()
                    out.append(line)
                    i += 1
                    # 如果栈非空，继续在外层代码块内
                    continue
                else:
                    # 更多反引号 = 仍然是内容
                    out.append(line)
                    i += 1
                    continue

        # ---- 代码块内（非 shell）----
        if codeblock_stack:
            lang = codeblock_stack[-1][0]
            if lang == '' or lang == 'markdown':
                # 无语言标记或 markdown 代码块：内部仍做 shell 替换
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

    # 4. ~/.openclaw 主机路径 → 泛化（v2.5.2 新增，scanner 命中点）
    line = re.sub(r'~/\.openclaw[^\s`>}\])]*', '`<OpenClaw数据目录>`', line)
    line = re.sub(r'`<OpenClaw数据目录>`/[^\s`]*', '`<OpenClaw数据目录>`', line)

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
