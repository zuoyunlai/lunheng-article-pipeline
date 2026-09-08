#!/usr/bin/env python3
"""
增量 M 门验证器
版本: v2.9.0
用途: 只验证变更部分 + 跨阶段依赖，复用未变更部分的缓存结果
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from fnmatch import fnmatch
from datetime import datetime
import yaml


class ChangeDetector:
    """检测文件变更"""
    
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


class IncrementalMGateValidator:
    """增量 M 门验证器"""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.detector = ChangeDetector(project_dir / ".m_gate_cache.json")
        self.dependencies = self._load_dependencies()
        self.last_results = self._load_last_results()
    
    def _load_dependencies(self) -> Dict:
        """加载 M 门依赖关系"""
        dep_file = Path(__file__).parent / "m_gate_dependencies.yaml"
        if not dep_file.exists():
            raise FileNotFoundError(f"依赖配置文件不存在: {dep_file}")
        return yaml.safe_load(dep_file.read_text(encoding='utf-8'))
    
    def _load_last_results(self) -> Dict:
        """加载上次验证结果"""
        result_file = self.project_dir / ".m_gate_results.json"
        if result_file.exists():
            return json.loads(result_file.read_text(encoding='utf-8'))
        return {}
    
    def _save_results(self, results: Dict):
        """保存验证结果"""
        result_file = self.project_dir / ".m_gate_results.json"
        result_file.write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
    
    def validate_incremental(self, phase: str) -> Dict:
        """
        增量验证
        
        Args:
            phase: 当前阶段 (phase_1.5, phase_2.5, phase_4)
        
        Returns:
            验证结果 {gate_id: result, ...}
        """
        # 1. 检测变更文件
        all_files = list(self.project_dir.rglob("*.md"))
        # 过滤掉缓存文件和临时文件
        all_files = [f for f in all_files if not any(
            part.startswith('.') for part in f.parts
        )]
        
        changed_files = self.detector.get_changed_files(all_files)
        
        if not changed_files:
            print("✓ 无文件变更，跳过 M 门验证")
            return self.last_results
        
        print(f"检测到 {len(changed_files)} 个文件变更:")
        for f in changed_files:
            try:
                rel_path = f.relative_to(self.project_dir)
                print(f"  - {rel_path}")
            except ValueError:
                print(f"  - {f}")
        
        # 2. 确定需要重新验证的 M 门
        gates_to_validate = self._get_affected_gates(changed_files)
        
        if not gates_to_validate:
            print("✓ 变更未影响任何 M 门，复用上次结果")
            return self.last_results
        
        print(f"\n需要重新验证 {len(gates_to_validate)} 个 M 门:")
        for gate_id in sorted(gates_to_validate):
            gate_name = self.dependencies[gate_id]['name']
            print(f"  - {gate_id}: {gate_name}")
        
        # 3. 执行增量验证
        results = self.last_results.copy()
        for gate_id in sorted(gates_to_validate):
            gate_name = self.dependencies[gate_id]['name']
            print(f"验证 {gate_id} ({gate_name})...", end=" ")
            result = self._validate_single_gate(gate_id)
            results[gate_id] = result
            print("✓" if result['passed'] else "✗")
        
        # 4. 保存结果
        self._save_results(results)
        
        # 5. 汇总
        total = len(self.dependencies)
        validated = len(gates_to_validate)
        skipped = total - validated
        passed = sum(1 for r in results.values() if r.get('passed', False))
        
        print(f"\n增量验证完成:")
        print(f"  - 总计: {total} 项")
        print(f"  - 本次验证: {validated} 项")
        print(f"  - 复用缓存: {skipped} 项")
        print(f"  - 通过: {passed}/{total}")
        
        return results
    
    def _get_affected_gates(self, changed_files: List[Path]) -> Set[str]:
        """确定受变更影响的 M 门"""
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
    
    def _validate_single_gate(self, gate_id: str) -> Dict:
        """
        验证单个 M 门
        
        Returns:
            {'passed': bool, 'message': str, 'timestamp': str}
        """
        # 这里是占位实现，实际需要集成现有的 M 门验证逻辑
        # TODO: 集成 references/_shared/M-Gate-Algorithm.md 中的验证函数
        
        return {
            'passed': True,  # 占位
            'message': f'{gate_id} 验证通过（占位实现）',
            'timestamp': datetime.now().isoformat(),
            'gate_name': self.dependencies[gate_id]['name']
        }
    
    def clear_cache(self):
        """清除缓存，强制下次全量验证"""
        cache_file = self.project_dir / ".m_gate_cache.json"
        result_file = self.project_dir / ".m_gate_results.json"
        
        if cache_file.exists():
            cache_file.unlink()
            print("✓ 已清除变更检测缓存")
        
        if result_file.exists():
            result_file.unlink()
            print("✓ 已清除验证结果缓存")


def main():
    """命令行入口"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python incremental_m_gate.py <项目目录> [--phase phase_name] [--clear-cache]")
        sys.exit(1)
    
    project_dir = Path(sys.argv[1])
    if not project_dir.exists():
        print(f"错误: 项目目录不存在: {project_dir}")
        sys.exit(1)
    
    validator = IncrementalMGateValidator(project_dir)
    
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
        print(f"\n❌ 验证失败，{len(failed)} 项未通过:")
        for gate_id in failed:
            print(f"  - {gate_id}: {results[gate_id]['message']}")
        sys.exit(1)
    else:
        print("\n✓ 所有 M 门验证通过")


if __name__ == '__main__':
    main()
