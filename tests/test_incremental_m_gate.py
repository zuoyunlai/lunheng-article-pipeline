#!/usr/bin/env python3
"""
增量 M 门验证器单元测试
版本: v2.9.0
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys
import json

# 添加脚本目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from incremental_m_gate import ChangeDetector, IncrementalMGateValidator


class TestChangeDetector(unittest.TestCase):
    """变更检测器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cache_file = self.temp_dir / ".test_cache.json"
        self.detector = ChangeDetector(self.cache_file)
    
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir)
    
    def test_compute_hash(self):
        """测试哈希计算"""
        test_file = self.temp_dir / "test.txt"
        test_file.write_text("hello world", encoding='utf-8')
        
        hash1 = self.detector.compute_hash(test_file)
        self.assertIsNotNone(hash1)
        self.assertEqual(len(hash1), 64)  # SHA256 = 64 hex chars
        
        # 相同内容应该产生相同哈希
        hash2 = self.detector.compute_hash(test_file)
        self.assertEqual(hash1, hash2)
    
    def test_has_changed_new_file(self):
        """测试新文件检测"""
        test_file = self.temp_dir / "new.txt"
        test_file.write_text("new content", encoding='utf-8')
        
        # 新文件应该被检测为变更
        self.assertTrue(self.detector.has_changed(test_file))
        
        # 第二次检查应该不再变更
        self.assertFalse(self.detector.has_changed(test_file))
    
    def test_has_changed_modified_file(self):
        """测试修改文件检测"""
        test_file = self.temp_dir / "modified.txt"
        test_file.write_text("original", encoding='utf-8')
        
        # 首次检测
        self.detector.has_changed(test_file)
        
        # 修改文件
        test_file.write_text("modified", encoding='utf-8')
        
        # 应该检测到变更
        self.assertTrue(self.detector.has_changed(test_file))
    
    def test_has_changed_deleted_file(self):
        """测试删除文件检测"""
        test_file = self.temp_dir / "deleted.txt"
        test_file.write_text("to be deleted", encoding='utf-8')
        
        # 首次检测
        self.detector.has_changed(test_file)
        self.detector._save_cache()
        
        # 删除文件
        test_file.unlink()
        
        # 应该检测到变更
        self.assertTrue(self.detector.has_changed(test_file))
    
    def test_get_changed_files(self):
        """测试批量变更检测"""
        file1 = self.temp_dir / "file1.txt"
        file2 = self.temp_dir / "file2.txt"
        file3 = self.temp_dir / "file3.txt"
        
        file1.write_text("content1", encoding='utf-8')
        file2.write_text("content2", encoding='utf-8')
        file3.write_text("content3", encoding='utf-8')
        
        files = [file1, file2, file3]
        
        # 首次检测，全部变更
        changed = self.detector.get_changed_files(files)
        self.assertEqual(len(changed), 3)
        
        # 修改一个文件
        file2.write_text("modified content2", encoding='utf-8')
        
        # 再次检测，只有一个变更
        changed = self.detector.get_changed_files(files)
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0], file2)
    
    def test_cache_persistence(self):
        """测试缓存持久化"""
        test_file = self.temp_dir / "persist.txt"
        test_file.write_text("content", encoding='utf-8')
        
        # 首次检测并保存
        self.detector.has_changed(test_file)
        self.detector._save_cache()
        
        # 创建新检测器，应该能加载缓存
        detector2 = ChangeDetector(self.cache_file)
        
        # 未修改文件不应该被检测为变更
        self.assertFalse(detector2.has_changed(test_file))


class TestIncrementalMGateValidator(unittest.TestCase):
    """增量M门验证器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # 创建模拟项目结构
        (self.temp_dir / "literature").mkdir()
        (self.temp_dir / "data").mkdir()
        (self.temp_dir / "drafts").mkdir()
        
        # 创建测试文件
        (self.temp_dir / "literature/L01.md").write_text("文献1", encoding='utf-8')
        (self.temp_dir / "data/D01.md").write_text("数据1", encoding='utf-8')
        (self.temp_dir / "drafts/初稿-v1.md").write_text("草稿1", encoding='utf-8')
        
        # 创建依赖配置（简化版）
        dep_config = {
            'M-Form-1': {
                'name': '引用完整性',
                'depends_on': ['drafts/*.md', 'literature/*.md'],
                'scope': 'citations'
            },
            'M-Integrity-1': {
                'name': 'T2数据源5要素',
                'depends_on': ['data/*.md'],
                'scope': 'data'
            }
        }
        
        # 保存到scripts目录（相对于项目根）
        scripts_dir = self.temp_dir / "scripts"
        scripts_dir.mkdir()
        dep_file = scripts_dir / "m_gate_dependencies.yaml"
        
        import yaml
        dep_file.write_text(yaml.dump(dep_config, allow_unicode=True), encoding='utf-8')
        
        # 临时修改PATH以便找到依赖文件
        self.original_file = Path(__file__)
        self.validator = IncrementalMGateValidator(self.temp_dir)
    
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir)
    
    def test_no_changes(self):
        """测试无变更场景"""
        # 首次验证
        results1 = self.validator.validate_incremental('phase_4')
        
        # 无变更再次验证
        results2 = self.validator.validate_incremental('phase_4')
        
        # 应该返回相同结果
        self.assertEqual(results1, results2)
    
    def test_draft_change_affects_form_gates(self):
        """测试草稿变更影响格式类M门"""
        # 首次验证
        self.validator.validate_incremental('phase_4')
        
        # 修改草稿
        draft_file = self.temp_dir / "drafts/初稿-v1.md"
        draft_file.write_text("修改后的草稿", encoding='utf-8')
        
        # 获取受影响的M门
        changed_files = [draft_file]
        affected = self.validator._get_affected_gates(changed_files)
        
        # 应该影响M-Form-1（依赖drafts/*.md）
        self.assertIn('M-Form-1', affected)
        
        # 不应该影响M-Integrity-1（只依赖data/*.md）
        self.assertNotIn('M-Integrity-1', affected)
    
    def test_data_change_affects_integrity_gates(self):
        """测试数据卡变更影响完整性类M门"""
        # 首次验证
        self.validator.validate_incremental('phase_4')
        
        # 修改数据卡
        data_file = self.temp_dir / "data/D01.md"
        data_file.write_text("修改后的数据", encoding='utf-8')
        
        # 获取受影响的M门
        changed_files = [data_file]
        affected = self.validator._get_affected_gates(changed_files)
        
        # 应该影响M-Integrity-1（依赖data/*.md）
        self.assertIn('M-Integrity-1', affected)
        
        # 不应该影响M-Form-1（不依赖data/*.md）
        self.assertNotIn('M-Form-1', affected)
    
    def test_cache_clear(self):
        """测试缓存清除"""
        # 首次验证
        self.validator.validate_incremental('phase_4')
        
        # 确认缓存文件存在
        cache_file = self.temp_dir / ".m_gate_cache.json"
        result_file = self.temp_dir / ".m_gate_results.json"
        self.assertTrue(cache_file.exists())
        self.assertTrue(result_file.exists())
        
        # 清除缓存
        self.validator.clear_cache()
        
        # 确认缓存文件已删除
        self.assertFalse(cache_file.exists())
        self.assertFalse(result_file.exists())
    
    def test_results_persistence(self):
        """测试验证结果持久化"""
        # 首次验证
        results1 = self.validator.validate_incremental('phase_4')
        
        # 创建新验证器
        validator2 = IncrementalMGateValidator(self.temp_dir)
        
        # 无变更验证，应该复用结果
        results2 = validator2.validate_incremental('phase_4')
        
        # 结果应该一致
        self.assertEqual(results1, results2)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestChangeDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestIncrementalMGateValidator))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
