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

from incremental_m_gate import (
    ChangeDetector,
    SectionChangeDetector,
    IncrementalMGateValidator,
)


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


class TestSectionChangeDetector(unittest.TestCase):
    """章节级变更检测器测试（v2.10.0 新增）"""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cache_file = self.temp_dir / ".test_section_cache.json"
        self.detector = SectionChangeDetector(self.cache_file)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _make_md(self, name, sections):
        """创建含章节的 Markdown 文件，sections = [(标题, 内容), ...]"""
        f = self.temp_dir / name
        lines = ['# 文档标题', '']
        for title, content in sections:
            lines.append(f'## {title}')
            lines.append(content)
        f.write_text('\n'.join(lines), encoding='utf-8')
        return f

    def test_split_sections(self):
        """测试章节拆分"""
        f = self._make_md('test.md', [
            ('第一章', '内容A'),
            ('第二章', '内容B'),
            ('第三章', '内容C'),
        ])

        sections = self.detector.split_sections(f)
        titles = [t for t, _ in sections]

        self.assertIn('（前言）', titles)
        self.assertIn('第一章', titles)
        self.assertIn('第二章', titles)
        self.assertIn('第三章', titles)

    def test_get_changed_sections_new_file(self):
        """测试新文件：所有章节都标记为新增"""
        f = self._make_md('new.md', [
            ('第一章', '内容A'),
            ('第二章', '内容B'),
        ])

        changed = self.detector.get_changed_sections(f)

        # 新文件所有章节都应标记为 [新增]
        self.assertTrue(any('[新增] 第一章' in c for c in changed))
        self.assertTrue(any('[新增] 第二章' in c for c in changed))

        # 第二次检测：无变更
        changed2 = self.detector.get_changed_sections(f)
        self.assertEqual(changed2, [])

    def test_get_changed_sections_modified(self):
        """测试修改单个章节：只标记该章节"""
        f = self._make_md('modified.md', [
            ('第一章', '内容A'),
            ('第二章', '内容B'),
        ])

        # 首次检测（初始化缓存）
        self.detector.get_changed_sections(f)

        # 只修改第二章
        f.write_text(
            '# 文档标题\n\n## 第一章\n内容A\n## 第二章\n内容B已修改',
            encoding='utf-8'
        )

        changed = self.detector.get_changed_sections(f)

        # 只有第二章被标记（不带 [新增]/[删除] 前缀）
        self.assertIn('第二章', changed)
        self.assertNotIn('第一章', changed)
        self.assertFalse(any('第二章' in c and '[新增]' in c for c in changed))

    def test_get_changed_sections_added(self):
        """测试新增章节：标记为 [新增]"""
        f = self._make_md('added.md', [
            ('第一章', '内容A'),
        ])

        self.detector.get_changed_sections(f)

        # 新增第二章
        f.write_text(
            '# 文档标题\n\n## 第一章\n内容A\n## 第二章\n内容B',
            encoding='utf-8'
        )

        changed = self.detector.get_changed_sections(f)

        self.assertTrue(any('[新增] 第二章' in c for c in changed))
        self.assertNotIn('第一章', changed)

    def test_get_changed_sections_deleted(self):
        """测试删除章节：标记为 [删除]"""
        f = self._make_md('deleted.md', [
            ('第一章', '内容A'),
            ('第二章', '内容B'),
        ])

        self.detector.get_changed_sections(f)

        # 删除第二章
        f.write_text(
            '# 文档标题\n\n## 第一章\n内容A',
            encoding='utf-8'
        )

        changed = self.detector.get_changed_sections(f)

        self.assertTrue(any('[删除] 第二章' in c for c in changed))

    def test_cache_persistence_section(self):
        """测试章节缓存持久化"""
        f = self._make_md('persist.md', [
            ('第一章', '内容A'),
        ])

        self.detector.get_changed_sections(f)

        # 创建新检测器，加载缓存
        detector2 = SectionChangeDetector(self.cache_file)
        changed = detector2.get_changed_sections(f)

        # 未修改，无变更
        self.assertEqual(changed, [])


class TestSectionLevelValidation(unittest.TestCase):
    """章节级增量验证集成测试（v2.10.0 新增）"""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        (self.temp_dir / "drafts").mkdir()

        # 创建含章节的草稿
        draft = self.temp_dir / "drafts/初稿-v1.md"
        draft.write_text(
            '# 初稿\n\n## 引言\n内容1 [L01]\n## 第一章\n内容2 [D01]',
            encoding='utf-8'
        )

        self.validator = IncrementalMGateValidator(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_section_changes_detected(self):
        """测试章节级变更被检测"""
        # 首次验证
        self.validator.validate_incremental('phase_4')

        # 只修改第一章
        draft = self.temp_dir / "drafts/初稿-v1.md"
        draft.write_text(
            '# 初稿\n\n## 引言\n内容1 [L01]\n## 第一章\n修改后的内容2 [D01]',
            encoding='utf-8'
        )

        # 检测变更文件
        changed_files = [draft]
        section_changes = self.validator.get_changed_sections_for_files(
            changed_files
        )

        # 应该检测到章节级变更
        self.assertIn('drafts/初稿-v1.md', section_changes)
        sections = section_changes['drafts/初稿-v1.md']
        self.assertIn('第一章', sections)
        self.assertNotIn('引言', sections)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestChangeDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestIncrementalMGateValidator))
    suite.addTests(loader.loadTestsFromTestCase(TestSectionChangeDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestSectionLevelValidation))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
