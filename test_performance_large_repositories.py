#!/usr/bin/env python3
"""
Performance tests for large repositories and datasets
"""

import unittest
import tempfile
import shutil
import os
import subprocess
import time
import threading
from unittest.mock import Mock, patch
from pathlib import Path
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from git_wrapper import InteractiveGitWrapper


class TestPerformanceLargeRepositories(unittest.TestCase):
    """Test performance with large repositories and datasets"""
    
    def setUp(self):
        """Set up test fixtures with large repository simulation"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Initialize a git repository
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True)
        
        # Initialize git wrapper
        self.git_wrapper = InteractiveGitWrapper()
        self.git_wrapper.config_file = Path(self.test_dir) / 'test_config.json'
        
        # Mock print methods to avoid output during tests
        self.git_wrapper.print_info = Mock()
        self.git_wrapper.print_success = Mock()
        self.git_wrapper.print_error = Mock()
        self.git_wrapper.print_working = Mock()
        
        # Performance thresholds (in seconds)
        self.FAST_OPERATION_THRESHOLD = 1.0
        self.MEDIUM_OPERATION_THRESHOLD = 5.0
        self.SLOW_OPERATION_THRESHOLD = 15.0
    
    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _create_large_repository(self, num_branches=50, num_commits_per_branch=20, num_files_per_commit=5):
        """Create a large repository for performance testing"""
        print(f"Creating large repository: {num_branches} branches, {num_commits_per_branch} commits each, {num_files_per_commit} files per commit")
        
        # Create initial commit
        with open('README.md', 'w') as f:
            f.write('# Large Test Repository\n')
        subprocess.run(['git', 'add', 'README.md'], check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], check=True, capture_output=True)
        
        # Create multiple branches with commits
        for branch_idx in range(num_branches):
            branch_name = f'feature/branch-{branch_idx:03d}'
            subprocess.run(['git', 'checkout', '-b', branch_name], check=True, capture_output=True)
            
            for commit_idx in range(num_commits_per_branch):
                # Create multiple files per commit
                for file_idx in range(num_files_per_commit):
                    filename = f'branch_{branch_idx:03d}_commit_{commit_idx:03d}_file_{file_idx:03d}.py'
                    with open(filename, 'w') as f:
                        f.write(f'''# File {filename}
# Branch: {branch_name}
# Commit: {commit_idx}

def function_{branch_idx}_{commit_idx}_{file_idx}():
    """Generated function for performance testing"""
    return "{branch_name}_{commit_idx}_{file_idx}"

class Class_{branch_idx}_{commit_idx}_{file_idx}:
    """Generated class for performance testing"""
    
    def __init__(self):
        self.branch = "{branch_name}"
        self.commit = {commit_idx}
        self.file = {file_idx}
    
    def get_info(self):
        return f"{{self.branch}}_{{self.commit}}_{{self.file}}"
''')
                
                # Add and commit files
                subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
                commit_msg = f'feat(branch-{branch_idx:03d}): add commit {commit_idx:03d} with {num_files_per_commit} files'
                subprocess.run(['git', 'commit', '-m', commit_msg], check=True, capture_output=True)
            
            # Go back to main for next branch
            subprocess.run(['git', 'checkout', 'main'], check=True, capture_output=True)
        
        print(f"Large repository created with {num_branches * num_commits_per_branch} total commits")
    
    def _measure_execution_time(self, func, *args, **kwargs):
        """Measure execution time of a function"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    
    def test_health_dashboard_performance_large_repo(self):
        """Test health dashboard performance with large repository"""
        health_dashboard = self.git_wrapper.get_feature_manager('health')
        if not health_dashboard:
            self.skipTest("Health dashboard not available")
        
        # Create moderately large repository
        self._create_large_repository(num_branches=20, num_commits_per_branch=10, num_files_per_commit=3)
        
        # Test branch analysis performance
        result, execution_time = self._measure_execution_time(health_dashboard.analyze_branches)
        self.assertLess(execution_time, self.MEDIUM_OPERATION_THRESHOLD, 
                       f"Branch analysis took {execution_time:.2f}s, expected < {self.MEDIUM_OPERATION_THRESHOLD}s")
        self.assertIsInstance(result, dict)
        self.assertIn('unmerged_branches', result)
        
        # Test repository stats performance
        result, execution_time = self._measure_execution_time(health_dashboard.get_repository_stats)
        self.assertLess(execution_time, self.MEDIUM_OPERATION_THRESHOLD,
                       f"Repository stats took {execution_time:.2f}s, expected < {self.MEDIUM_OPERATION_THRESHOLD}s")
        self.assertIsInstance(result, dict)
        
        # Test large file detection performance
        result, execution_time = self._measure_execution_time(health_dashboard.find_large_files, 0.001)  # Very small threshold
        self.assertLess(execution_time, self.MEDIUM_OPERATION_THRESHOLD,
                       f"Large file detection took {execution_time:.2f}s, expected < {self.MEDIUM_OPERATION_THRESHOLD}s")
        self.assertIsInstance(result, list)
    
    def test_stash_manager_performance_many_stashes(self):
        """Test stash manager performance with many stashes"""
        stash_manager = self.git_wrapper.get_feature_manager('stash')
        if not stash_manager:
            self.skipTest("Stash manager not available")
        
        # Create initial commit
        with open('test_file.py', 'w') as f:
            f.write('print("initial")\n')
        subprocess.run(['git', 'add', 'test_file.py'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], check=True)
        
        # Create many stashes
        num_stashes = 30
        print(f"Creating {num_stashes} stashes for performance testing")
        
        stash_creation_times = []
        for i in range(num_stashes):
            # Modify file
            with open('test_file.py', 'w') as f:
                f.write(f'print("stash {i}")\n# Stash content {i}\n')
            
            # Create stash and measure time
            with patch('builtins.input', side_effect=[f'stash-{i:03d}', 'y']):
                result, execution_time = self._measure_execution_time(
                    stash_manager.create_named_stash, f'stash-{i:03d}', f'Test stash {i}'
                )
                stash_creation_times.append(execution_time)
                self.assertTrue(result)
        
        # Test that stash creation time doesn't degrade significantly
        avg_early_time = sum(stash_creation_times[:5]) / 5
        avg_late_time = sum(stash_creation_times[-5:]) / 5
        degradation_ratio = avg_late_time / avg_early_time if avg_early_time > 0 else 1
        
        self.assertLess(degradation_ratio, 3.0, 
                       f"Stash creation time degraded by {degradation_ratio:.2f}x, expected < 3x")
        
        # Test listing performance
        result, execution_time = self._measure_execution_time(stash_manager.list_stashes_with_metadata)
        self.assertLess(execution_time, self.FAST_OPERATION_THRESHOLD,
                       f"Stash listing took {execution_time:.2f}s, expected < {self.FAST_OPERATION_THRESHOLD}s")
        self.assertEqual(len(result), num_stashes)
        
        # Test search performance
        result, execution_time = self._measure_execution_time(stash_manager.search_stashes, 'stash-01')
        self.assertLess(execution_time, self.FAST_OPERATION_THRESHOLD,
                       f"Stash search took {execution_time:.2f}s, expected < {self.FAST_OPERATION_THRESHOLD}s")
        self.assertGreater(len(result), 0)
    
    def test_branch_workflow_performance_many_branches(self):
        """Test branch workflow performance with many branches"""
        workflow_manager = self.git_wrapper.get_feature_manager('workflows')
        if not workflow_manager:
            self.skipTest("Workflow manager not available")
        
        # Create repository with many branches
        self._create_large_repository(num_branches=30, num_commits_per_branch=5, num_files_per_commit=2)
        
        # Test workflow status performance
        result, execution_time = self._measure_execution_time(workflow_manager.get_workflow_status)
        self.assertLess(execution_time, self.MEDIUM_OPERATION_THRESHOLD,
                       f"Workflow status took {execution_time:.2f}s, expected < {self.MEDIUM_OPERATION_THRESHOLD}s")
        self.assertIsInstance(result, dict)
        
        # Test branch creation performance
        branch_creation_times = []
        for i in range(5):  # Create 5 new branches
            branch_name = f'perf-test-{i}'
            with patch('builtins.input', side_effect=[branch_name, 'y']):
                result, execution_time = self._measure_execution_time(
                    workflow_manager.start_feature_branch, branch_name, 'github_flow'
                )
                branch_creation_times.append(execution_time)
                self.assertTrue(result)
        
        # Verify branch creation time is consistent
        max_creation_time = max(branch_creation_times)
        self.assertLess(max_creation_time, self.FAST_OPERATION_THRESHOLD,
                       f"Branch creation took {max_creation_time:.2f}s, expected < {self.FAST_OPERATION_THRESHOLD}s")
    
    def test_commit_template_performance_many_templates(self):
        """Test commit template performance with many custom templates"""
        template_engine = self.git_wrapper.get_feature_manager('templates')
        if not template_engine:
            self.skipTest("Template engine not available")
        
        # Create many custom templates
        num_templates = 50
        print(f"Creating {num_templates} custom templates for performance testing")
        
        template_creation_times = []
        for i in range(num_templates):
            template_name = f'custom-template-{i:03d}'
            template_pattern = f'custom({i}): {{description}}\n\n{{body}}\n\nTemplate-{i}: {{footer}}'
            
            result, execution_time = self._measure_execution_time(
                template_engine.create_custom_template, template_name, template_pattern
            )
            template_creation_times.append(execution_time)
            self.assertTrue(result)
        
        # Test template listing performance
        result, execution_time = self._measure_execution_time(template_engine.list_templates)
        self.assertLess(execution_time, self.FAST_OPERATION_THRESHOLD,
                       f"Template listing took {execution_time:.2f}s, expected < {self.FAST_OPERATION_THRESHOLD}s")
        self.assertGreaterEqual(len(result), num_templates)
        
        # Test template selection performance
        result, execution_time = self._measure_execution_time(template_engine.get_template_by_name, 'custom-template-025')
        self.assertLess(execution_time, self.FAST_OPERATION_THRESHOLD,
                       f"Template selection took {execution_time:.2f}s, expected < {self.FAST_OPERATION_THRESHOLD}s")
        self.assertIsNotNone(result)
        
        # Test template application performance
        if result:
            context = {'description': 'test', 'body': 'test body', 'footer': 'test footer'}
            applied_result, execution_time = self._measure_execution_time(
                template_engine.apply_template, result, context
            )
            self.assertLess(execution_time, self.FAST_OPERATION_THRESHOLD,
                           f"Template application took {execution_time:.2f}s, expected < {self.FAST_OPERATION_THRESHOLD}s")
            self.assertIsInstance(applied_result, str)
    
    def test_backup_system_performance_large_data(self):
        """Test backup system performance with large amounts of data"""
        backup_system = self.git_wrapper.get_feature_manager('backup')
        if not backup_system:
            self.skipTest("Backup system not available")
        
        # Create repository with substantial data
        self._create_large_repository(num_branches=15, num_commits_per_branch=8, num_files_per_commit=4)
        
        # Get list of branches to backup
        branches_result = subprocess.run(['git', 'branch', '-a'], capture_output=True, text=True)
        all_branches = [line.strip().replace('* ', '') for line in branches_result.stdout.split('\n') 
                       if line.strip() and not line.startswith('*') and 'remotes/' not in line]
        
        # Test backup configuration performance
        result, execution_time = self._measure_execution_time(backup_system.list_backup_versions)
        self.assertLess(execution_time, self.FAST_OPERATION_THRESHOLD,
                       f"Backup version listing took {execution_time:.2f}s, expected < {self.FAST_OPERATION_THRESHOLD}s")
        
        # Test backup creation performance (mocked to avoid actual network operations)
        with patch.object(backup_system, '_push_to_remote', return_value=True), \
             patch('builtins.input', side_effect=['y']):
            
            # Test backing up multiple branches
            branches_to_backup = all_branches[:10]  # Backup first 10 branches
            result, execution_time = self._measure_execution_time(
                backup_system.create_backup, branches_to_backup, 'test-remote'
            )
            self.assertLess(execution_time, self.MEDIUM_OPERATION_THRESHOLD,
                           f"Backup creation took {execution_time:.2f}s, expected < {self.MEDIUM_OPERATION_THRESHOLD}s")
            self.assertTrue(result)
    
    def test_concurrent_feature_operations(self):
        """Test performance of concurrent feature operations"""
        # Get available features
        features = {
            'stash': self.git_wrapper.get_feature_manager('stash'),
            'health': self.git_wrapper.get_feature_manager('health'),
            'templates': self.git_wrapper.get_feature_manager('templates')
        }
        
        available_features = {k: v for k, v in features.items() if v is not None}
        
        if len(available_features) < 2:
            self.skipTest("Need at least 2 features for concurrent testing")
        
        # Create test data
        self._create_large_repository(num_branches=10, num_commits_per_branch=5, num_files_per_commit=2)
        
        # Create some stashes if stash manager is available
        if 'stash' in available_features:
            with open('concurrent_test.py', 'w') as f:
                f.write('print("concurrent test")\n')
            
            with patch('builtins.input', side_effect=['concurrent-stash', 'y']):
                available_features['stash'].create_named_stash('concurrent-stash', 'Concurrent test stash')
        
        # Define concurrent operations
        def run_health_analysis():
            if 'health' in available_features:
                return available_features['health'].analyze_branches()
            return {}
        
        def run_stash_listing():
            if 'stash' in available_features:
                return available_features['stash'].list_stashes_with_metadata()
            return []
        
        def run_template_listing():
            if 'templates' in available_features:
                return available_features['templates'].list_templates()
            return []
        
        # Run operations concurrently
        operations = [run_health_analysis, run_stash_listing, run_template_listing]
        available_operations = [op for op in operations if op.__name__.split('_')[1] in available_features]
        
        if len(available_operations) < 2:
            self.skipTest("Need at least 2 available operations for concurrent testing")
        
        results = []
        threads = []
        start_time = time.time()
        
        def run_operation(operation):
            try:
                result = operation()
                results.append((operation.__name__, result, True))
            except Exception as e:
                results.append((operation.__name__, str(e), False))
        
        # Start concurrent operations
        for operation in available_operations[:3]:  # Run up to 3 concurrent operations
            thread = threading.Thread(target=run_operation, args=(operation,))
            threads.append(thread)
            thread.start()
        
        # Wait for all operations to complete
        for thread in threads:
            thread.join(timeout=self.SLOW_OPERATION_THRESHOLD)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Verify all operations completed successfully
        self.assertEqual(len(results), len(available_operations[:3]))
        for op_name, result, success in results:
            self.assertTrue(success, f"Operation {op_name} failed: {result}")
        
        # Verify reasonable performance
        self.assertLess(total_time, self.SLOW_OPERATION_THRESHOLD,
                       f"Concurrent operations took {total_time:.2f}s, expected < {self.SLOW_OPERATION_THRESHOLD}s")
    
    def test_memory_usage_large_operations(self):
        """Test memory usage during large operations"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large repository
        self._create_large_repository(num_branches=25, num_commits_per_branch=10, num_files_per_commit=3)
        
        # Run memory-intensive operations
        health_dashboard = self.git_wrapper.get_feature_manager('health')
        if health_dashboard:
            # Analyze branches
            health_dashboard.analyze_branches()
            
            # Get repository stats
            health_dashboard.get_repository_stats()
            
            # Find large files
            health_dashboard.find_large_files(0.001)  # Very small threshold
        
        # Check memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for test operations)
        self.assertLess(memory_increase, 100, 
                       f"Memory usage increased by {memory_increase:.2f}MB, expected < 100MB")
        
        print(f"Memory usage: {initial_memory:.2f}MB -> {final_memory:.2f}MB (increase: {memory_increase:.2f}MB)")
    
    def test_feature_initialization_performance(self):
        """Test performance of feature initialization"""
        # Create a new git wrapper to test initialization
        new_wrapper = InteractiveGitWrapper()
        new_wrapper.config_file = Path(self.test_dir) / 'test_config_2.json'
        new_wrapper.print_info = Mock()
        new_wrapper.print_success = Mock()
        new_wrapper.print_error = Mock()
        
        # Test lazy loading performance
        result, execution_time = self._measure_execution_time(new_wrapper.has_advanced_features)
        self.assertLess(execution_time, self.FAST_OPERATION_THRESHOLD,
                       f"Feature initialization took {execution_time:.2f}s, expected < {self.FAST_OPERATION_THRESHOLD}s")
        
        # Test subsequent calls are fast (cached)
        result, execution_time = self._measure_execution_time(new_wrapper.has_advanced_features)
        self.assertLess(execution_time, 0.1,  # Should be very fast for cached result
                       f"Cached feature check took {execution_time:.2f}s, expected < 0.1s")
        
        # Test individual feature manager access
        feature_names = ['stash', 'templates', 'workflows', 'conflicts', 'health', 'backup']
        for feature_name in feature_names:
            result, execution_time = self._measure_execution_time(
                new_wrapper.get_feature_manager, feature_name
            )
            self.assertLess(execution_time, 0.1,
                           f"Feature manager access for {feature_name} took {execution_time:.2f}s, expected < 0.1s")


if __name__ == '__main__':
    # Run with verbose output to see performance metrics
    unittest.main(verbosity=2)