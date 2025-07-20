#!/usr/bin/env python3
"""
Integration tests for cross-feature functionality and data sharing
"""

import unittest
import tempfile
import shutil
import os
import json
import subprocess
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from git_wrapper import InteractiveGitWrapper


class TestFeatureInteractions(unittest.TestCase):
    """Test cross-feature functionality and data sharing"""
    
    def setUp(self):
        """Set up test fixtures with temporary git repository"""
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
        
        # Mock print methods to avoid output during tests
        self.git_wrapper.print_info = Mock()
        self.git_wrapper.print_success = Mock()
        self.git_wrapper.print_error = Mock()
        self.git_wrapper.print_working = Mock()
    
    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_stash_and_branch_workflow_integration(self):
        """Test integration between stash management and branch workflows"""
        # Create some changes to stash
        with open('test_file.py', 'w') as f:
            f.write('print("Hello, World!")\n')
        
        # Get feature managers
        stash_manager = self.git_wrapper.get_feature_manager('stash')
        workflow_manager = self.git_wrapper.get_feature_manager('workflows')
        
        if not stash_manager or not workflow_manager:
            self.skipTest("Required features not available")
        
        # Create a named stash
        with patch('builtins.input', side_effect=['test-stash', 'y']):
            result = stash_manager.create_named_stash('test-stash', 'Test changes before branch switch')
            self.assertTrue(result)
        
        # Start a feature branch
        with patch('builtins.input', side_effect=['feature-branch', 'y']):
            result = workflow_manager.start_feature_branch('feature-branch', 'github_flow')
            self.assertTrue(result)
        
        # Verify stash is still available after branch switch
        stashes = stash_manager.list_stashes_with_metadata()
        self.assertEqual(len(stashes), 1)
        self.assertEqual(stashes[0]['name'], 'test-stash')
        
        # Apply stash on new branch
        with patch('builtins.input', side_effect=['y']):
            result = stash_manager.apply_stash(stashes[0]['id'], keep=False)
            self.assertTrue(result)
        
        # Verify file exists on new branch
        self.assertTrue(Path('test_file.py').exists())
    
    def test_commit_template_and_conflict_resolution_integration(self):
        """Test integration between commit templates and conflict resolution"""
        template_engine = self.git_wrapper.get_feature_manager('templates')
        conflict_resolver = self.git_wrapper.get_feature_manager('conflicts')
        
        if not template_engine or not conflict_resolver:
            self.skipTest("Required features not available")
        
        # Create a branch and make conflicting changes
        subprocess.run(['git', 'checkout', '-b', 'conflict-branch'], check=True)
        
        with open('conflict_file.txt', 'w') as f:
            f.write('Branch version\n')
        subprocess.run(['git', 'add', 'conflict_file.txt'], check=True)
        
        # Use template for commit
        template = template_engine.get_template_by_name('feat')
        if template:
            commit_msg = template_engine.apply_template(template, {
                'scope': 'test',
                'description': 'add conflict file',
                'body': 'Adding file that will cause conflict'
            })
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        
        # Switch back to main and create conflicting change
        subprocess.run(['git', 'checkout', 'main'], check=True)
        with open('conflict_file.txt', 'w') as f:
            f.write('Main version\n')
        subprocess.run(['git', 'add', 'conflict_file.txt'], check=True)
        subprocess.run(['git', 'commit', '-m', 'fix: add conflict file on main'], check=True)
        
        # Attempt merge to create conflict
        result = subprocess.run(['git', 'merge', 'conflict-branch'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)  # Should fail due to conflict
        
        # Use conflict resolver
        conflicted_files = conflict_resolver.list_conflicted_files()
        self.assertIn('conflict_file.txt', conflicted_files)
        
        # Resolve conflict using "ours" strategy
        with patch('builtins.input', side_effect=['ours', 'y']):
            result = conflict_resolver.resolve_conflict('conflict_file.txt', 'ours')
            self.assertTrue(result)
        
        # Finalize merge with template
        if template:
            merge_msg = template_engine.apply_template(template, {
                'scope': 'merge',
                'description': 'resolve conflict in conflict_file.txt',
                'body': 'Resolved using ours strategy'
            })
            with patch('builtins.input', side_effect=[merge_msg, 'y']):
                result = conflict_resolver.finalize_merge()
                self.assertTrue(result)
    
    def test_health_dashboard_and_backup_system_integration(self):
        """Test integration between health dashboard and backup system"""
        health_dashboard = self.git_wrapper.get_feature_manager('health')
        backup_system = self.git_wrapper.get_feature_manager('backup')
        
        if not health_dashboard or not backup_system:
            self.skipTest("Required features not available")
        
        # Create multiple branches to analyze
        branches = ['feature/test1', 'feature/test2', 'hotfix/urgent']
        for branch in branches:
            subprocess.run(['git', 'checkout', '-b', branch], check=True)
            with open(f'{branch.replace("/", "_")}.txt', 'w') as f:
                f.write(f'Content for {branch}\n')
            subprocess.run(['git', 'add', f'{branch.replace("/", "_")}.txt'], check=True)
            subprocess.run(['git', 'commit', '-m', f'Add {branch} content'], check=True)
        
        subprocess.run(['git', 'checkout', 'main'], check=True)
        
        # Analyze repository health
        branch_analysis = health_dashboard.analyze_branches()
        self.assertGreater(len(branch_analysis['unmerged_branches']), 0)
        
        # Use health analysis to determine backup strategy
        important_branches = ['main'] + [b for b in branch_analysis['unmerged_branches'] 
                                       if 'hotfix' in b or 'main' in b]
        
        # Configure backup system based on health analysis
        backup_config = {
            'backup_remotes': ['backup'],
            'auto_backup_branches': important_branches,
            'retention_days': 30
        }
        
        # Mock backup operations
        with patch.object(backup_system, '_push_to_remote', return_value=True):
            result = backup_system.create_backup(important_branches, 'backup')
            self.assertTrue(result)
        
        # Verify backup log includes health-based decisions
        backup_versions = backup_system.list_backup_versions()
        self.assertGreater(len(backup_versions), 0)
    
    def test_workflow_and_template_integration(self):
        """Test integration between branch workflows and commit templates"""
        workflow_manager = self.git_wrapper.get_feature_manager('workflows')
        template_engine = self.git_wrapper.get_feature_manager('templates')
        
        if not workflow_manager or not template_engine:
            self.skipTest("Required features not available")
        
        # Configure Git Flow workflow
        workflow_config = {
            'type': 'git_flow',
            'feature_prefix': 'feature/',
            'hotfix_prefix': 'hotfix/',
            'release_prefix': 'release/'
        }
        
        # Start feature branch using workflow
        with patch('builtins.input', side_effect=['user-auth', 'y']):
            result = workflow_manager.start_feature_branch('user-auth', 'git_flow')
            self.assertTrue(result)
        
        # Verify we're on the correct branch
        current_branch = subprocess.run(['git', 'branch', '--show-current'], 
                                      capture_output=True, text=True).stdout.strip()
        self.assertEqual(current_branch, 'feature/user-auth')
        
        # Make changes and commit using template
        with open('auth.py', 'w') as f:
            f.write('def authenticate(user): pass\n')
        subprocess.run(['git', 'add', 'auth.py'], check=True)
        
        # Use feat template for feature work
        template = template_engine.get_template_by_name('feat')
        if template:
            commit_msg = template_engine.apply_template(template, {
                'scope': 'auth',
                'description': 'add user authentication module',
                'body': 'Implements basic authentication functionality'
            })
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        
        # Finish feature branch
        with patch('builtins.input', side_effect=['merge', 'y']):
            result = workflow_manager.finish_feature_branch('feature/user-auth', 'merge')
            self.assertTrue(result)
        
        # Verify we're back on main branch
        current_branch = subprocess.run(['git', 'branch', '--show-current'], 
                                      capture_output=True, text=True).stdout.strip()
        self.assertEqual(current_branch, 'main')
    
    def test_cross_feature_configuration_sharing(self):
        """Test that features properly share configuration data"""
        # Get all feature managers
        features = {
            'stash': self.git_wrapper.get_feature_manager('stash'),
            'templates': self.git_wrapper.get_feature_manager('templates'),
            'workflows': self.git_wrapper.get_feature_manager('workflows'),
            'conflicts': self.git_wrapper.get_feature_manager('conflicts'),
            'health': self.git_wrapper.get_feature_manager('health'),
            'backup': self.git_wrapper.get_feature_manager('backup')
        }
        
        available_features = {k: v for k, v in features.items() if v is not None}
        
        if len(available_features) < 2:
            self.skipTest("Need at least 2 features for configuration sharing test")
        
        # Test that all features have access to the same git_wrapper instance
        for name, feature in available_features.items():
            self.assertIs(feature.git_wrapper, self.git_wrapper)
        
        # Test configuration access
        for name, feature in available_features.items():
            config = feature.get_config()
            self.assertIsInstance(config, dict)
            
            # Verify feature-specific config exists
            if hasattr(feature, '_get_default_config'):
                default_config = feature._get_default_config()
                self.assertIsInstance(default_config, dict)
    
    def test_error_propagation_across_features(self):
        """Test that errors are properly handled across feature boundaries"""
        stash_manager = self.git_wrapper.get_feature_manager('stash')
        workflow_manager = self.git_wrapper.get_feature_manager('workflows')
        
        if not stash_manager or not workflow_manager:
            self.skipTest("Required features not available")
        
        # Create a scenario where one feature operation affects another
        with open('test_file.py', 'w') as f:
            f.write('print("test")\n')
        
        # Try to create stash with invalid name (should handle gracefully)
        with patch('builtins.input', side_effect=['', 'valid-name', 'y']):
            result = stash_manager.create_named_stash('', 'Empty name test')
            # Should either succeed with fallback name or fail gracefully
            self.assertIsInstance(result, bool)
        
        # Try to start branch with invalid name
        with patch('builtins.input', side_effect=['invalid/branch/name', 'valid-branch', 'y']):
            result = workflow_manager.start_feature_branch('invalid/branch/name', 'github_flow')
            # Should either succeed with sanitized name or fail gracefully
            self.assertIsInstance(result, bool)
    
    def test_feature_status_consistency(self):
        """Test that feature status reporting is consistent across features"""
        status = self.git_wrapper.get_feature_status()
        
        self.assertIn('available_features', status)
        self.assertIn('total_available', status)
        self.assertIn('features_initialized', status)
        self.assertIn('feature_health', status)
        
        # Verify status consistency
        self.assertEqual(len(status['available_features']), status['total_available'])
        self.assertTrue(status['features_initialized'])
        
        # Check health status for each available feature
        for feature_name in status['available_features']:
            self.assertIn(feature_name, status['feature_health'])
            health = status['feature_health'][feature_name]
            self.assertIn(health, ['healthy', 'missing_interface', 'error'])


if __name__ == '__main__':
    unittest.main()