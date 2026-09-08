#!/usr/bin/env python3
"""
增量 M 门验证器
版本: v2.10.0
用途: 只验证变更部分 + 跨阶段依赖，复用未变更部分的缓存结果
v2.10.0 增强: 章节级变更检测（从文件级升级到章节级，识别「改了哪一章」）
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from fnmatch import fnmatch
from datetime import datetime
import yaml


class ChangeDetector:
    """检测文件级变更（v2.9.0 保留，作为 fallback）"""

    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, str]:
        """加载上次验证的文件哈希缓存"""
        if self.cache_file.exists():
            return json.loads(self.cache_file.read_text(encoding='utf-8'))
        return {}

    def _save_cache(self):
        """保存文件哈希缓存"""
        self.cache_file.write_text(
            json.dumps(self.cache, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

    def compute_hash(self, file_path: Path) -> str:
        """计算文件 SHA256 哈希"""
        return hashlib.sha256(file_path.read_bytes()).hexdigest()

    def has_changed(self, file_path: Path) -> bool:
        """检查文件是否变更"""
        if not file_path.exists():
            # 文件被删除也算变更
            old_hash = self.cache.get(str(file_path))
            if old_hash:
                del self.cache[str(file_path)]
                return True
            return False

        current_hash = self.compute_hash(file_path)
        old_hash = self.cache.get(str(file_path))

        if old_hash != current_hash:
            self.cache[str(file_path)] = current_hash
            return True
        return False

    def get_changed_files(self, file_list: List[Path]) -> List[Path]:
        """批量检测变更文件"""
        changed = []
        for file_path in file_list:
            if self.has_changed(file_path):
                changed.append(file_path)
        self._save_cache()
        return changed


class SectionChangeDetector:
    """章节级变更检测器（v2.10.0 新增）

    把 Markdown 文件按 `## ` 二级标题拆分为章节，
    对每个章节计算 SHA256，识别「改了哪一章」而非「改了哪个文件」。
    """

    SECTION_MARKER = '## '

    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Dict[str, str]]:
        """加载章节哈希缓存 {文件路径: {章节标题: SHA256}}"""
        if self.cache_file.exists():
            return json.loads(self.cache_file.read_text(encoding='utf-8'))
        return {}

    def _save_cache(self):
        self.cache_file.write_text(
            json.dumps(self.cache, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

    def split_sections(self, file_path: Path) -> List[Tuple[str, str]]:
        """拆分 Markdown 文件为章节列表 [(标题, 内容), ...]

        章节边界 = `## ` 开头的行。首个 `## ` 之前的正文归入「（前言）」。
        """
        if not file_path.exists():
            return []

        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        sections = []
        current_title = '（前言）'
        current_lines = []

        for line in lines:
            if line.startswith(self.SECTION_MARKER):
                # 遇到新章节，保存当前章节
                if current_lines:
                    sections.append((current_title, '\n'.join(current_lines)))
                current_title = line[len(self.SECTION_MARKER):].strip()
                current_lines = [line]
            else:
                current_lines.append(line)

        # 保存最后一个章节
        if current_lines:
            sections.append((current_title, '\n'.join(current_lines)))

        return sections

    def get_changed_sections(self, file_path: Path) -> List[str]:
        """识别变更的章节标题列表（含新增/删除/修改）

        返回格式：
        - 修改章节：标题名
        - 新增章节：`[新增] 标题名`
        - 删除章节：`[删除] 标题名`
        """
        sections = self.split_sections(file_path)
        current_hashes = {
            title: hashlib.sha256(content.encode('utf-8')).hexdigest()
            for title, content in sections
        }

        old_hashes = self.cache.get(str(file_path), {})

        changed = []
        # 检测修改 + 新增章节
        for title, h in current_hashes.items():
            if title not in old_hashes:
                changed.append(f'[新增] {title}')
            elif old_hashes[title] != h:
                changed.append(title)

        # 检测删除章节
        deleted = set(old_hashes.keys()) - set(current_hashes.keys())
        for title in sorted(deleted):
            changed.append(f'[删除] {title}')

        # 更新缓存
        self.cache[str(file_path)] = current_hashes
        self._save_cache()

        return changed


class IncrementalMGateValidator:
    """增量 M 门验证器"""

    def __init__(self, project_dir: Path, enable_section_level: bool = True):
        self.project_dir = project_dir
        self.detector = ChangeDetector(project_dir / '.m_gate_cache.json')
        self.section_detector = SectionChangeDetector(
            project_dir / '.m_gate_section_cache.json'
        )
        self.enable_section_level = enable_section_level
        self.dependencies = self._load_dependencies()
        self.last_results = self._load_last_results()

    def _load_dependencies(self) -> Dict:
        """加载 M 门依赖关系"""
        dep_file = Path(__file__).parent / 'm_gate_dependencies.yaml'
        if not dep_file.exists():
            raise FileNotFoundError(f'依赖配置文件不存在: {dep_file}')
        return yaml.safe_load(dep_file.read_text(encoding='utf-8'))

    def _load_last_results(self) -> Dict:
        """加载上次验证结果"""
        result_file = self.project_dir / '.m_gate_results.json'
        if result_file.exists():
            return json.loads(result_file.read_text(encoding='utf-8'))
        return {}

    def _save_results(self, results: Dict):
        """保存验证结果"""
        result_file = self.project_dir / '.m_gate_results.json'
        result_file.write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

    def get_changed_sections_for_files(
        self, changed_files: List[Path]
    ) -> Dict[str, List[str]]:
        """获取变更文件的章节级变更 {文件路径: [章节标题]}

        仅对含 `## ` 章节的 Markdown 文件生效；
        无章节的文件返回空列表（回退到文件级）。
        """
        section_changes = {}
        for f in changed_files:
            try:
                rel_path = str(f.relative_to(self.project_dir))
            except ValueError:
                rel_path = str(f)

            sections = self.section_detector.get_changed_sections(f)
            if sections:
                section_changes[rel_path] = sections

        return section_changes

    def validate_incremental(self, phase: str) -> Dict:
        """
        增量验证

        Args:
            phase: 当前阶段 (phase_1.5, phase_2.5, phase_4)

        Returns:
            验证结果 {gate_id: result, ...}
        """
        # 1. 检测变更文件（文件级）
        all_files = list(self.project_dir.rglob('*.md'))
        # 过滤掉缓存文件和临时文件
        all_files = [f for f in all_files if not any(
            part.startswith('.') for part in f.parts
        )]

        changed_files = self.detector.get_changed_files(all_files)

        if not changed_files:
            print('✓ 无文件变更，跳过 M 门验证')
            return self.last_results

        print(f'检测到 {len(changed_files)} 个文件变更:')
        for f in changed_files:
            try:
                rel_path = f.relative_to(self.project_dir)
                print(f'  - {rel_path}')
            except ValueError:
                print(f'  - {f}')

        # 2. 章节级变更检测（v2.10.0 增强）
        section_changes = {}
        if self.enable_section_level:
            section_changes = self.get_changed_sections_for_files(changed_files)
            if section_changes:
                print(f'\n章节级变更检测（v2.10.0）:')
                for rel_path, sections in section_changes.items():
                    print(f'  {rel_path}:')
                    for s in sections:
                        print(f'    - {s}')

        # 3. 确定需要重新验证的 M 门（文件级）
        gates_to_validate = self._get_affected_gates(changed_files)

        if not gates_to_validate:
            print('✓ 变更未影响任何 M 门，复用上次结果')
            return self.last_results

        print(f'\n需要重新验证 {len(gates_to_validate)} 个 M 门:')
        for gate_id in sorted(gates_to_validate):
            gate_name = self.dependencies[gate_id]['name']
            print(f'  - {gate_id}: {gate_name}')

        # 4. 执行增量验证
        results = self.last_results.copy()
        for gate_id in sorted(gates_to_validate):
            gate_name = self.dependencies[gate_id]['name']
            print(f'验证 {gate_id} ({gate_name})...', end=' ')
            result = self._validate_single_gate(gate_id, section_changes)
            results[gate_id] = result
            print('✓' if result['passed'] else '✗')

        # 5. 保存结果
        self._save_results(results)
        self.last_results = results  # v2.10.0 修复：同步内存态，避免下次「无变更」返回旧结果

        # 6. 汇总
        total = len(self.dependencies)
        validated = len(gates_to_validate)
        skipped = total - validated
        passed = sum(1 for r in results.values() if r.get('passed', False))

        print(f'\n增量验证完成:')
        print(f'  - 总计: {total} 项')
        print(f'  - 本次验证: {validated} 项')
        print(f'  - 复用缓存: {skipped} 项')
        print(f'  - 通过: {passed}/{total}')

        return results

    def _get_affected_gates(self, changed_files: List[Path]) -> Set[str]:
        """确定受变更影响的 M 门（文件级）"""
        affected = set()

        for gate_id, gate_info in self.dependencies.items():
            for dep_pattern in gate_info['depends_on']:
                # 检查变更文件是否匹配依赖模式
                if self._matches_pattern(changed_files, dep_pattern):
                    affected.add(gate_id)
                    break

        return affected

    def _matches_pattern(self, files: List[Path], pattern: str) -> bool:
        """检查文件列表是否匹配模式"""
        for file_path in files:
            try:
                rel_path = str(file_path.relative_to(self.project_dir))
                if fnmatch(rel_path, pattern):
                    return True
            except ValueError:
                # 文件不在项目目录内，跳过
                continue
        return False

    def _validate_single_gate(
        self, gate_id: str, section_changes: Optional[Dict] = None
    ) -> Dict:
        """
        验证单个 M 门

        Args:
            gate_id: M 门 ID
            section_changes: 章节级变更信息 {文件路径: [章节标题]}

        Returns:
            {'passed': bool, 'message': str, 'timestamp': str}
        """
        # 这里是占位实现，实际需要集成现有的 M 门验证逻辑
        # TODO: 集成 references/_shared/M-Gate-Algorithm.md 中的验证函数
        # v2.10.0: 章节级变更信息作为验证提示传给 LLM

        message = f'{gate_id} 验证通过（占位实现）'
        if section_changes:
            # 附带章节级变更信息，供 LLM 聚焦验证范围
            changed_summary = '; '.join(
                f'{f}: {", ".join(sections)}'
                for f, sections in section_changes.items()
            )
            message = (
                f'{gate_id} 验证通过（占位实现）'
                f' | 章节变更: {changed_summary}'
            )

        return {
            'passed': True,  # 占位
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'gate_name': self.dependencies[gate_id]['name']
        }

    def clear_cache(self):
        """清除缓存，强制下次全量验证"""
        cache_file = self.project_dir / '.m_gate_cache.json'
        result_file = self.project_dir / '.m_gate_results.json'
        section_cache_file = self.project_dir / '.m_gate_section_cache.json'

        for f in (cache_file, result_file, section_cache_file):
            if f.exists():
                f.unlink()
                print(f'✓ 已清除 {f.name}')


def main():
    """命令行入口"""
    import sys

    if len(sys.argv) < 2:
        print(
            '用法: python incremental_m_gate.py <项目目录> '
            '[--phase phase_name] [--clear-cache] [--no-section-level]'
        )
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    if not project_dir.exists():
        print(f'错误: 项目目录不存在: {project_dir}')
        sys.exit(1)

    enable_section = '--no-section-level' not in sys.argv
    validator = IncrementalMGateValidator(project_dir, enable_section)

    # 检查是否清除缓存
    if '--clear-cache' in sys.argv:
        validator.clear_cache()
        return

    # 获取阶段参数
    phase = 'phase_4'  # 默认阶段
    if '--phase' in sys.argv:
        phase_idx = sys.argv.index('--phase')
        if phase_idx + 1 < len(sys.argv):
            phase = sys.argv[phase_idx + 1]

    # 执行增量验证
    results = validator.validate_incremental(phase)

    # 检查是否有失败项
    failed = [k for k, v in results.items() if not v.get('passed', False)]
    if failed:
        print(f'\n❌ 验证失败，{len(failed)} 项未通过:')
        for gate_id in failed:
            print(f'  - {gate_id}: {results[gate_id]["message"]}')
        sys.exit(1)
    else:
        print('\n✓ 所有 M 门验证通过')


if __name__ == '__main__':
    main()
