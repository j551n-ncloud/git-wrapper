#!/usr/bin/env python3
"""
Integration tests for Git command interactions
"""

import unittest
import tempfile
import shutil
import os
import subprocess
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from git_wrapper import InteractiveGitWrapper


class TestGitCommandIntegration(unittest.TestCase):
    """Test integration with actual Git commands"""
    
    def setUp(self):
        """Set up test fixtures with real git repository"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Initialize a git repository
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True)
        
        # Create initial commit
        with open('README.md', 'w') as f:
            f.write('# Test Repository\n')
        subprocess.run(['git', 'add', 'README.md'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], check=True)
        
        # Initialize git wrapper
        self.git_wrapper = InteractiveGitWrapper()
        self.git_wrapper.config_file = Path(self.test_dir) / 'test_config.json'
        
        # Mock print methods to reduce test output
        self.git_wrapper.print_info = Mock()
        self.git_wrapper.print_success = Mock()
        self.git_wrapper.print_error = Mock()
        self.git_wrapper.print_working = Mock()
    
    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_stash_manager_git_integration(self):
        """Test stash manager integration with actual git stash commands"""
        stash_manager = self.git_wrapper.get_feature_manager('stash')
        if not stash_manager:
            self.skipTest("Stash manager not available")
        
        # Create some changes to stash
        with open('test_file.py', 'w') as f:
            f.write('print("Hello, World!")\n')
        
        # Test stash creation
        with patch('builtins.input', side_effect=['test-stash', 'y']):
            result = stash_manager.create_named_stash('test-stash', 'Test stash message')
            self.assertTrue(result)
        
        # Verify stash was created using git command
        git_stash_list = subprocess.run(['git', 'stash', 'list'], capture_output=True, text=True)
        self.assertEqual(git_stash_list.returncode, 0)
        self.assertIn('test-stash', git_stash_list.stdout)
        
        # Test stash listing matches git output
        stashes = stash_manager.list_stashes_with_metadata()
        self.assertEqual(len(stashes), 1)
        self.assertEqual(stashes[0]['name'], 'test-stash')
        
        # Test stash preview
        preview = stash_manager.preview_stash(stashes[0]['id'])
        self.assertIsInstance(preview, str)
        self.assertIn('test_file.py', preview)
        
        # Test stash application
        with patch('builtins.input', side_effect=['y']):
            result = stash_manager.apply_stash(stashes[0]['id'], keep=True)
            self.assertTrue(result)
        
        # Verify file was restored
        self.assertTrue(Path('test_file.py').exists())
        
        # Test stash deletion
        with patch('builtins.input', side_effect=['y']):
            result = stash_manager.delete_stash(stashes[0]['id'])
            self.assertTrue(result)
        
        # Verify stash was deleted using git command
        git_stash_list = subprocess.run(['git', 'stash', 'list'], capture_output=True, text=True)
        self.assertEqual(git_stash_list.returncode, 0)
        self.assertEqual(git_stash_list.stdout.strip(), '')
    
    def test_branch_workflow_git_integration(self):
        """Test branch workflow integration with actual git branch commands"""
        workflow_manager = self.git_wrapper.get_feature_manager('workflows')
        if not workflow_manager:
            self.skipTest("Workflow manager not available")
        
        # Test feature branch creation
        with patch('builtins.input', side_effect=['test-feature', 'y']):
            result = workflow_manager.start_feature_branch('test-feature', 'github_flow')
            self.assertTrue(result)
        
        # Verify branch was created using git command
        git_branch_list = subprocess.run(['git', 'branch'], capture_output=True, text=True)
        self.assertEqual(git_branch_list.returncode, 0)
        self.assertIn('test-feature', git_branch_list.stdout)
        
        # Verify we're on the new branch
        current_branch = subprocess.run(['git', 'branch', '--show-current'], 
                                      capture_output=True, text=True).stdout.strip()
        self.assertIn('test-feature', current_branch)
        
        # Make some changes on the feature branch
        with open('feature.py', 'w') as f:
            f.write('def new_feature():\n    return "feature"\n')
        subprocess.run(['git', 'add', 'feature.py'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Add new feature'], check=True)
        
        # Test branch finishing
        with patch('builtins.input', side_effect=['merge', 'y']):
            result = workflow_manager.finish_feature_branch(current_branch, 'merge')
            self.assertTrue(result)
        
        # Verify we're back on main branch
        final_branch = subprocess.run(['git', 'branch', '--show-current'], 
                                    capture_output=True, text=True).stdout.strip()
        self.assertEqual(final_branch, 'main')
        
        # Verify feature was merged
        self.assertTrue(Path('feature.py').exists())
    
    def test_conflict_resolver_git_integration(self):
        """Test conflict resolver integration with actual git merge conflicts"""
        conflict_resolver = self.git_wrapper.get_feature_manager('conflicts')
        if not conflict_resolver:
            self.skipTest("Conflict resolver not available")
        
        # Create a branch with conflicting changes
        subprocess.run(['git', 'checkout', '-b', 'conflict-branch'], check=True)
        
        with open('conflict_file.txt', 'w') as f:
            f.write('Branch version\n')
        subprocess.run(['git', 'add', 'conflict_file.txt'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Add conflict file on branch'], check=True)
        
        # Switch back to main and create conflicting change
        subprocess.run(['git', 'checkout', 'main'], check=True)
        with open('conflict_file.txt', 'w') as f:
            f.write('Main version\n')
        subprocess.run(['git', 'add', 'conflict_file.txt'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Add conflict file on main'], check=True)
        
        # Attempt merge to create conflict
        merge_result = subprocess.run(['git', 'merge', 'conflict-branch'], capture_output=True)
        self.assertNotEqual(merge_result.returncode, 0)  # Should fail due to conflict
        
        # Test conflict detection
        conflicted_files = conflict_resolver.list_conflicted_files()
        self.assertIn('conflict_file.txt', conflicted_files)
        
        # Test conflict preview
        preview = conflict_resolver.show_conflict_preview('conflict_file.txt')
        self.assertIsInstance(preview, str)
        self.assertIn('<<<<<<< HEAD', preview)
        self.assertIn('>>>>>>>', preview)
        
        # Test conflict resolution using "ours" strategy
        with patch('builtins.input', side_effect=['y']):
            result = conflict_resolver.resolve_conflict('conflict_file.txt', 'ours')
            self.assertTrue(result)
        
        # Verify conflict was resolved
        with open('conflict_file.txt', 'r') as f:
            content = f.read()
            self.assertEqual(content.strip(), 'Main version')
        
        # Test merge finalization
        with patch('builtins.input', side_effect=['y']):
            result = conflict_resolver.finalize_merge()
            self.assertTrue(result)
        
        # Verify merge was completed
        git_status = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        self.assertEqual(git_status.stdout.strip(), '')  # Should be clean
    
    def test_commit_template_git_integration(self):
        """Test commit template integration with actual git commits"""
        template_engine = self.git_wrapper.get_feature_manager('templates')
        if not template_engine:
            self.skipTest("Template engine not available")
        
        # Create some changes to commit
        with open('new_feature.py', 'w') as f:
            f.write('def awesome_feature():\n    return "awesome"\n')
        subprocess.run(['git', 'add', 'new_feature.py'], check=True)
        
        # Test template application
        template = template_engine.get_template_by_name('feat')
        if template:
            commit_msg = template_engine.apply_template(template, {
                'scope': 'core',
                'description': 'add awesome feature',
                'body': 'Implements the most awesome feature ever'
            })
            
            # Commit using the template
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
            
            # Verify commit was created with correct message
            git_log = subprocess.run(['git', 'log', '-1', '--pretty=format:%s'], 
                                   capture_output=True, text=True)
            self.assertEqual(git_log.returncode, 0)
            self.assertIn('feat(core): add awesome feature', git_log.stdout)
            
            # Verify full commit message
            git_log_full = subprocess.run(['git', 'log', '-1', '--pretty=format:%B'], 
                                        capture_output=True, text=True)
            self.assertIn('Implements the most awesome feature ever', git_log_full.stdout)
    
    def test_health_dashboard_git_integration(self):
        """Test health dashboard integration with actual git repository analysis"""
        health_dashboard = self.git_wrapper.get_feature_manager('health')
        if not health_dashboard:
            self.skipTest("Health dashboard not available")
        
        # Create multiple branches for analysis
        branches = ['feature/test1', 'feature/test2', 'hotfix/urgent']
        for branch in branches:
            subprocess.run(['git', 'checkout', '-b', branch], check=True)
            with open(f'{branch.replace("/", "_")}.txt', 'w') as f:
                f.write(f'Content for {branch}\n')
            subprocess.run(['git', 'add', f'{branch.replace("/", "_")}.txt'], check=True)
            subprocess.run(['git', 'commit', '-m', f'Add {branch} content'], check=True)
        
        subprocess.run(['git', 'checkout', 'main'], check=True)
        
        # Test branch analysis
        branch_analysis = health_dashboard.analyze_branches()
        self.assertIsInstance(branch_analysis, dict)
        self.assertIn('unmerged_branches', branch_analysis)
        
        # Verify analysis matches actual git state
        git_branches = subprocess.run(['git', 'branch'], capture_output=True, text=True)
        git_branch_list = [line.strip().replace('* ', '') for line in git_branches.stdout.split('\n') 
                          if line.strip() and line.strip() != 'main']
        
        for branch in branches:
            self.assertIn(branch, branch_analysis['unmerged_branches'])
        
        # Test repository stats
        repo_stats = health_dashboard.get_repository_stats()
        self.assertIsInstance(repo_stats, dict)
        self.assertIn('total_commits', repo_stats)
        self.assertGreater(repo_stats['total_commits'], 0)
        
        # Create a large file for testing
        with open('large_file.txt', 'w') as f:
            f.write('x' * 1024 * 1024)  # 1MB file
        subprocess.run(['git', 'add', 'large_file.txt'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Add large file'], check=True)
        
        # Test large file detection
        large_files = health_dashboard.find_large_files(threshold_mb=0.5)
        self.assertIsInstance(large_files, list)
        self.assertGreater(len(large_files), 0)
        
        # Verify large file was detected
        large_file_names = [f['name'] for f in large_files]
        self.assertIn('large_file.txt', large_file_names)
    
    def test_backup_system_git_integration(self):
        """Test backup system integration with actual git remote operations"""
        backup_system = self.git_wrapper.get_feature_manager('backup')
        if not backup_system:
            self.skipTest("Backup system not available")
        
        # Create multiple branches for backup testing
        branches = ['main', 'feature/backup-test']
        subprocess.run(['git', 'checkout', '-b', 'feature/backup-test'], check=True)
        with open('backup_test.py', 'w') as f:
            f.write('def backup_test():\n    return "tested"\n')
        subprocess.run(['git', 'add', 'backup_test.py'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Add backup test'], check=True)
        subprocess.run(['git', 'checkout', 'main'], check=True)
        
        # Mock remote operations since we don't have actual remotes in test
        with patch.object(backup_system, '_push_to_remote', return_value=True) as mock_push, \
             patch.object(backup_system, '_verify_remote_exists', return_value=True), \
             patch('builtins.input', side_effect=['y']):
            
            # Test backup creation
            result = backup_system.create_backup(branches, 'test-remote')
            self.assertTrue(result)
            
            # Verify push was called for each branch
            self.assertEqual(mock_push.call_count, len(branches))
        
        # Test backup version listing
        backup_versions = backup_system.list_backup_versions()
        self.assertIsInstance(backup_versions, list)
        
        # Test backup restoration (mocked)
        with patch.object(backup_system, '_fetch_from_remote', return_value=True), \
             patch('builtins.input', side_effect=['y']):
            
            if backup_versions:
                result = backup_system.restore_from_backup(backup_versions[0]['id'])
                self.assertIsInstance(result, bool)
    
    def test_git_command_error_handling(self):
        """Test error handling for git command failures"""
        # Test with non-git directory
        non_git_dir = tempfile.mkdtemp()
        original_dir = os.getcwd()
        
        try:
            os.chdir(non_git_dir)
            
            # Create new wrapper in non-git directory
            non_git_wrapper = InteractiveGitWrapper()
            non_git_wrapper.print_info = Mock()
            non_git_wrapper.print_error = Mock()
            
            # Test that git operations fail gracefully
            self.assertFalse(non_git_wrapper.is_git_repo())
            
            # Test feature operations in non-git directory
            stash_manager = non_git_wrapper.get_feature_manager('stash')
            if stash_manager:
                with patch('builtins.input', side_effect=['test-stash', 'y']):
                    result = stash_manager.create_named_stash('test-stash', 'Test message')
                    self.assertFalse(result)  # Should fail in non-git directory
            
        finally:
            os.chdir(original_dir)
            shutil.rmtree(non_git_dir, ignore_errors=True)
    
    def test_git_command_timeout_handling(self):
        """Test handling of long-running git commands"""
        health_dashboard = self.git_wrapper.get_feature_manager('health')
        if not health_dashboard:
            self.skipTest("Health dashboard not available")
        
        # Mock a slow git command
        original_run = subprocess.run
        
        def slow_git_command(*args, **kwargs):
            if 'git' in str(args[0]):
                import time
                time.sleep(0.1)  # Simulate slow command
            return original_run(*args, **kwargs)
        
        with patch('subprocess.run', side_effect=slow_git_command):
            # Test that operations complete despite slow git commands
            result = health_dashboard.get_repository_stats()
            self.assertIsInstance(result, dict)
    
    def test_git_command_output_parsing(self):
        """Test parsing of git command outputs"""
        health_dashboard = self.git_wrapper.get_feature_manager('health')
        if not health_dashboard:
            self.skipTest("Health dashboard not available")
        
        # Create branches with specific patterns for testing parsing
        test_branches = [
            'feature/user-auth-123',
            'bugfix/critical-fix',
            'experiment/new-algorithm'
        ]
        
        for branch in test_branches:
            subprocess.run(['git', 'checkout', '-b', branch], check=True)
            with open(f'{branch.replace("/", "_").replace("-", "_")}.py', 'w') as f:
                f.write(f'# {branch}\nprint("branch content")\n')
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run(['git', 'commit', '-m', f'Work on {branch}'], check=True)
        
        subprocess.run(['git', 'checkout', 'main'], check=True)
        
        # Test branch analysis parsing
        branch_analysis = health_dashboard.analyze_branches()
        
        # Verify all test branches are detected
        for branch in test_branches:
            self.assertIn(branch, branch_analysis['unmerged_branches'])
        
        # Test that branch analysis includes ahead/behind information
        for branch_info in branch_analysis['branch_details']:
            self.assertIn('name', branch_info)
            self.assertIn('ahead', branch_info)
            self.assertIn('behind', branch_info)
    
    def test_git_hooks_integration(self):
        """Test integration with git hooks"""
        # Create a simple pre-commit hook
        hooks_dir = Path('.git/hooks')
        hooks_dir.mkdir(exist_ok=True)
        
        pre_commit_hook = hooks_dir / 'pre-commit'
        with open(pre_commit_hook, 'w') as f:
            f.write('#!/bin/sh\necho "Pre-commit hook executed"\nexit 0\n')
        pre_commit_hook.chmod(0o755)
        
        # Test that commits work with hooks
        with open('hook_test.py', 'w') as f:
            f.write('print("hook test")\n')
        subprocess.run(['git', 'add', 'hook_test.py'], check=True)
        
        # Commit should succeed and trigger hook
        result = subprocess.run(['git', 'commit', '-m', 'Test hook integration'], 
                              capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn('Pre-commit hook executed', result.stdout)


if __name__ == '__main__':
    unittest.main()