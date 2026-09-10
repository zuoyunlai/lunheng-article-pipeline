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
    (r'rm -rf', '删除目录'),
    (r'\brm\b', '删除'),
]


def is_shell_codeblock_lang(lang: str) -> bool:
    return lang.strip().lower() in ('bash', 'sh', 'shell', 'zsh', 'fish')


def looks_like_shell(content: str) -> bool:
    """判定反引号内容是否为 shell 命令（v2.6.0 重写，教训 #192）

    旧版把 '<' / '>' 出现即判为 shell，导致 `run/<项目>/x.md`、
    `<br>`、`[ack 0%] <一句话进度>` 等纯文本被误吞成裸「（检查）」。
    新规则：只有出现 shell 动词 / 管道 / 重定向串 / /tmp/ 路径才算命令。
    """
    if re.search(
        r'\b(grep|awk|sed|comm|sort|uniq|diff|stat|find|xargs|chmod|'
        r'sha256sum|md5sum|head|tail|pandoc|rsvg-convert|cat|ls|cp|mv|rm|wc)\b',
        content,
    ):
        return True
    if '|' in content:
        return True
    if '2>&1' in content or '/tmp/' in content:
        return True
    return False


def block_is_user_facing(block_lines: list) -> bool:
    """shell 代码块里若含用户安装/触发命令（非 host 验证命令），保留（教训 #192）"""
    joined = '\n'.join(block_lines)
    return 'openclaw skills install' in joined or 'clawhub skills install' in joined


def strip_shell(s: str) -> str:
    # ---- -1. v2.12.0: 论衡开发者门表文件内的 python 代码块也要剥（教训 #252）
    # 这些文件的代码块仅供本地开发者 python3 执行；净化版使用者侧无脚本，靠 LLM 推理 + 口诀
    # 实现：检测 "def check_" + "检查器" 标识，若匹配，把 python 围栏块替换为口诀+表格引导
    s = re.sub(
        r'```python\n(?:def check_\w+\(.*?\n)+.*?\n```',
        '**【本地质量检查工具见 `paper-ready-check`（发布版已剥离）】** —— LLM 推理口诀 + 三列表已在上方。',
        s,
        flags=re.DOTALL,
    )

    # ---- 0. 删除「跨平台等价命令」类表格（人类验证命令参考，agent 用不上）----
    s = re.sub(
        r'\*\*跨平台等价命令\*\*.*?(?=\n\n\*\*|\n###|\Z)',
        '',
        s,
        flags=re.DOTALL
    )

    # ---- 0b. 开发者工具引用行删除（scripts/ .github/ .sh .yml）—— 已移到行循环内「正文行处理」处，
    #          避免误伤代码块内的 scripts/ 参数行（教训 #256 同型：v2.12.1 曾误删
    #          「路径校验规范」subprocess.run 的 ["python3","scripts/path-canonical.py",...] 参数行）----

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
                    # （用户安装命令除外——那是使用说明，不是 host 验证命令）
                    i += 1
                    block = []
                    while i < len(lines):
                        end_bt = _backtick_count(lines[i])
                        if end_bt == bt_count:
                            break
                        block.append(lines[i])
                        i += 1
                    if block_is_user_facing(block):
                        out.append(line)  # 保留开始围栏
                        out.extend(block)
                        out.append(lines[i] if i < len(lines) else '')
                        i += 1
                        codeblock_stack.pop()
                        continue
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
                        block = []
                        while i < len(lines):
                            end_bt = _backtick_count(lines[i])
                            if end_bt == bt_count:
                                break
                            block.append(lines[i])
                            i += 1
                        if block_is_user_facing(block):
                            out.append(line)
                            out.extend(block)
                            out.append(lines[i] if i < len(lines) else '')
                            i += 1
                            codeblock_stack.pop()
                            continue
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
        # 0b. 删除开发者工具引用行（scripts/ .github/ .sh .yml）——仅正文，不碰代码块（教训 #256 同型）
        if re.search(r'(scripts/|\.github/)', line) or re.search(r'\.(sh|yml)\s*(#.*)?$', line):
            i += 1
            continue
        line = process_inline(line)
        out.append(line)
        i += 1

    return '\n'.join(out)


def process_inline(line: str) -> str:
    """处理正文行内的 shell 命令（反引号内 + 裸动词）"""
    orig_line = line

    # 1. 反引号内的 shell 命令 → 自然语言
    def replace_backtick(m):
        content = m.group(1)
        if not looks_like_shell(content):
            return m.group(0)  # 非 shell 命令，保留
        # 提取检测对象（编号模式或文件路径）
        num = re.search(r'\[(?:D|C|C-主|L|先)\d+\]', content)
        if num:
            return f'（检查 {num.group(0)}）'
        fpath = re.search(r'(?:drafts/|final/|literature/|data/|cases/|analysis/|audits/|run/)[^\s`|><]*\.md', content)
        if fpath:
            return f'（检查 {fpath.group(0)}）'
        # 兜底（v2.6.0，教训 #192）：动词换成自然语言、保留宾语，
        # 不再吞成裸「（检查）」（2.5.22-2.5.24 三版 101 处句子残缺的根因）
        replaced = content
        for pat, repl in VERB_PATTERNS:
            replaced = re.sub(pat, repl, replaced)
        return f'`{replaced}`'

    line = re.sub(r'`([^`]*)`', replace_backtick, line)

    # 2. 裸 shell 动词 → 自然语言
    for pat, repl in VERB_PATTERNS:
        line = re.sub(pat, repl, line)

    # 2b. .sh 文件引用 → 泛化（scanner 命中点）
    line = re.sub(r'`[^`]*\.sh`', '`shell 脚本`', line)
    line = re.sub(r'(?<!`)\bm_exist_1_diff\.sh\b(?!`)', 'shell 脚本', line)
    line = re.sub(r'\b(sync-version|check-version|build-clawhub-release)\.sh\b', '版本维护脚本', line)
    line = re.sub(r'（shell 版）|（shell 脚本）', '（脚本版）', line)

    # 2b+. 论衡开发者脚本引用脱钩（v2.12.0，教训 #252）
    line = re.sub(r'`?paper-ready-check\.(sh|py)`?', '论衡开发者脚本', line)

    # 2c. sha256 占位符 → 泛化
    line = line.replace('[SHA256-PENDING:HOST-VERIFY]', '[哈希校验待主人回填]')
    line = line.replace('sha256 指纹', '哈希指纹')

    # 3. 清理「零 exec 声明」里的具体命令列举 → 「shell 命令」
    line = re.sub(r'（`[^`]*`(?:/`[^`]*`)*\s*等）', '（shell 命令）', line)
    line = re.sub(r'\(`[^`]*`(?:/`[^`]*`)*\s*等\)', '（shell 命令）', line)

    # 4. ~/.openclaw 主机路径 → 泛化（v2.5.2 新增，scanner 命中点）
    line = re.sub(r'~/\.openclaw[^\s`>}\])]*', '`<OpenClaw数据目录>`', line)
    line = re.sub(r'`<OpenClaw数据目录>`/[^\s`]*', '`<OpenClaw数据目录>`', line)

    # 5. 替换残迹收口：动词替换后，原 ASCII 空格会夹在中文之间
    #    （`双向 diff` → `双向 对比`、`写完 grep` → `写完 检查`）——
    #    中文之间不留空格，仅在本行确实被改动时塌缩，避免误伤未改动行；
    #    例外：`§ 二 组 A` 这类章号 + 序号 + 名称写法保留空格。
    if line != orig_line:
        def _cjk(m):
            if re.search(r'§\s*$', line[:m.start()]):
                return m.group(0)
            return m.group(1) + m.group(2)
        line = re.sub(r'([\u4e00-\u9fff])[ \t]+([\u4e00-\u9fff])', _cjk, line)

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
