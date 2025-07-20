#!/usr/bin/env python3
"""
Unit tests for BranchWorkflowManager

Tests workflow configuration system, feature branch lifecycle,
merge strategies, and rollback functionality.
"""

import unittest
import tempfile
import shutil
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the classes to test
from features.branch_workflow_manager import BranchWorkflowManager


class TestBranchWorkflowManager(unittest.TestCase):
    """Test cases for BranchWorkflowManager."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test repository
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
        # Initialize git repository
        subprocess.run(['git', 'init'], cwd=self.test_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.test_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.test_dir, capture_output=True)
        
        # Create initial commit
        test_file = Path(self.test_dir) / 'README.md'
        test_file.write_text('# Test Repository')
        subprocess.run(['git', 'add', 'README.md'], cwd=self.test_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=self.test_dir, capture_output=True)
        
        # Change to test directory
        import os
        os.chdir(self.test_dir)
        
        # Create mock git wrapper
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {
            'default_remote': 'origin',
            'advanced_features': {
                'branch_workflows': {
                    'default_workflow': 'github_flow',
                    'auto_track_remotes': True,
                    'base_branch': 'main',
                    'auto_cleanup': True,
                    'merge_strategy': 'merge',
                    'push_after_finish': True,
                    'delete_after_merge': True
                }
            }
        }
        self.mock_git_wrapper.save_config = Mock()
        self.mock_git_wrapper.print_success = Mock()
        self.mock_git_wrapper.print_error = Mock()
        self.mock_git_wrapper.print_info = Mock()
        self.mock_git_wrapper.print_working = Mock()
        
        # Create BranchWorkflowManager instance
        self.workflow_manager = BranchWorkflowManager(self.mock_git_wrapper)
    
    def tearDown(self):
        """Clean up test environment."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_init(self):
        """Test BranchWorkflowManager initialization."""
        self.assertIsInstance(self.workflow_manager, BranchWorkflowManager)
        self.assertEqual(self.workflow_manager.git_wrapper, self.mock_git_wrapper)
        self.assertTrue(self.workflow_manager.workflow_config_file.exists() or 
                       self.workflow_manager.workflow_config_file.name == 'gitwrapper_workflows.json')
    
    def test_get_default_config(self):
        """Test default configuration values."""
        default_config = self.workflow_manager._get_default_config()
        
        expected_keys = [
            'default_workflow', 'auto_track_remotes', 'base_branch',
            'auto_cleanup', 'merge_strategy', 'push_after_finish', 'delete_after_merge'
        ]
        
        for key in expected_keys:
            self.assertIn(key, default_config)
        
        self.assertEqual(default_config['default_workflow'], 'github_flow')
        self.assertEqual(default_config['base_branch'], 'main')
        self.assertEqual(default_config['merge_strategy'], 'merge')
    
    def test_get_default_workflow_configs(self):
        """Test default workflow configurations."""
        configs = self.workflow_manager._get_default_workflow_configs()
        
        expected_workflows = ['git_flow', 'github_flow', 'gitlab_flow', 'custom']
        for workflow in expected_workflows:
            self.assertIn(workflow, configs)
        
        # Test Git Flow configuration
        git_flow = configs['git_flow']
        self.assertEqual(git_flow['name'], 'Git Flow')
        self.assertIn('feature', git_flow['branch_prefixes'])
        self.assertEqual(git_flow['branch_prefixes']['feature'], 'feature/')
        self.assertEqual(git_flow['base_branches']['feature'], 'develop')
        
        # Test GitHub Flow configuration
        github_flow = configs['github_flow']
        self.assertEqual(github_flow['name'], 'GitHub Flow')
        self.assertEqual(github_flow['base_branches']['feature'], 'main')
        self.assertEqual(github_flow['merge_strategy'], 'squash')
        self.assertTrue(github_flow['require_pull_request'])
    
    def test_load_workflow_configs(self):
        """Test loading workflow configurations."""
        # Test with no custom config file
        configs = self.workflow_manager._load_workflow_configs()
        self.assertIn('git_flow', configs)
        self.assertIn('github_flow', configs)
        
        # Test with custom config file
        custom_config = {
            'github_flow': {
                'merge_strategy': 'rebase'
            },
            'custom_workflow': {
                'name': 'My Custom Workflow',
                'base_branches': {'feature': 'develop'}
            }
        }
        
        config_file = Path(self.test_dir) / '.git' / 'gitwrapper_workflows.json'
        config_file.parent.mkdir(exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(custom_config, f)
        
        # Reload configurations
        self.workflow_manager.workflow_config_file = config_file
        configs = self.workflow_manager._load_workflow_configs()
        
        # Check that custom config was merged
        self.assertEqual(configs['github_flow']['merge_strategy'], 'rebase')
        self.assertIn('custom_workflow', configs)
    
    def test_detect_branch_type(self):
        """Test branch type detection."""
        # Test feature branch detection
        self.assertEqual(self.workflow_manager._detect_branch_type('feature/user-auth'), 'feature')
        self.assertEqual(self.workflow_manager._detect_branch_type('hotfix/critical-bug'), 'hotfix')
        
        # Test base branch detection
        self.assertEqual(self.workflow_manager._detect_branch_type('main'), 'base')
        self.assertEqual(self.workflow_manager._detect_branch_type('develop'), 'base')
        
        # Test default detection
        self.assertEqual(self.workflow_manager._detect_branch_type('my-branch'), 'feature')
        self.assertIsNone(self.workflow_manager._detect_branch_type(''))
    
    def test_branch_exists(self):
        """Test branch existence checking."""
        # Test existing branch (main should exist from setup)
        self.assertTrue(self.workflow_manager._branch_exists('main'))
        
        # Test non-existing branch
        self.assertFalse(self.workflow_manager._branch_exists('non-existent-branch'))
    
    def test_log_operation(self):
        """Test operation logging."""
        operation_details = {
            'feature_name': 'test-feature',
            'branch_type': 'feature',
            'workflow': 'github_flow'
        }
        
        operation_id = self.workflow_manager._log_operation('start_feature', operation_details)
        
        self.assertIsInstance(operation_id, str)
        self.assertTrue(len(operation_id) > 0)
        
        # Check that operation was added to log
        self.assertEqual(len(self.workflow_manager.operation_log), 1)
        operation = self.workflow_manager.operation_log[0]
        self.assertEqual(operation['id'], operation_id)
        self.assertEqual(operation['type'], 'start_feature')
        self.assertEqual(operation['details'], operation_details)
        self.assertEqual(operation['status'], 'in_progress')
    
    def test_update_operation_status(self):
        """Test operation status updates."""
        # Create an operation
        operation_id = self.workflow_manager._log_operation('start_feature', {'test': 'data'})
        
        # Update status
        result = {'branch_name': 'feature/test'}
        self.workflow_manager._update_operation_status(operation_id, 'completed', result)
        
        # Check update
        operation = self.workflow_manager.operation_log[0]
        self.assertEqual(operation['status'], 'completed')
        self.assertEqual(operation['result'], result)
    
    @patch('subprocess.run')
    def test_start_feature_branch_success(self, mock_subprocess):
        """Test successful feature branch creation."""
        # Mock successful git commands
        mock_subprocess.return_value = Mock(returncode=0, stdout='', stderr='')
        
        # Mock git wrapper methods
        self.workflow_manager.run_git_command = Mock(return_value=True)
        self.workflow_manager.get_remotes = Mock(return_value=['origin'])
        
        success, operation_id = self.workflow_manager.start_feature_branch('test-feature', 'feature', 'github_flow')
        
        self.assertTrue(success)
        self.assertIsNotNone(operation_id)
        
        # Check that operation was logged
        self.assertEqual(len(self.workflow_manager.operation_log), 1)
        operation = self.workflow_manager.operation_log[0]
        self.assertEqual(operation['status'], 'completed')
    
    def test_start_feature_branch_invalid_name(self):
        """Test feature branch creation with invalid name."""
        success, operation_id = self.workflow_manager.start_feature_branch('invalid..name', 'feature')
        
        self.assertFalse(success)
        self.assertIsNotNone(operation_id)
        
        # Check that operation was logged as failed
        operation = self.workflow_manager.operation_log[0]
        self.assertEqual(operation['status'], 'failed')
    
    def test_start_feature_branch_existing_branch(self):
        """Test feature branch creation when branch already exists."""
        # Mock branch existence check
        self.workflow_manager._branch_exists = Mock(side_effect=lambda name: name == 'feature/existing')
        
        success, operation_id = self.workflow_manager.start_feature_branch('existing', 'feature')
        
        self.assertFalse(success)
        self.assertIsNotNone(operation_id)
        
        # Check error was logged
        operation = self.workflow_manager.operation_log[0]
        self.assertEqual(operation['status'], 'failed')
        self.assertIn('already exists', operation['result']['error'])
    
    @patch('subprocess.run')
    def test_finish_feature_branch_success(self, mock_subprocess):
        """Test successful feature branch finishing."""
        # Mock successful git commands
        mock_subprocess.return_value = Mock(returncode=0, stdout='', stderr='')
        
        # Mock git wrapper methods
        self.workflow_manager.run_git_command = Mock(return_value=True)
        self.workflow_manager.get_current_branch = Mock(return_value='feature/test')
        self.workflow_manager.get_remotes = Mock(return_value=['origin'])
        
        success, operation_id = self.workflow_manager.finish_feature_branch('feature/test', 'merge')
        
        self.assertTrue(success)
        self.assertIsNotNone(operation_id)
        
        # Check that operation was logged
        operation = self.workflow_manager.operation_log[-1]  # Get last operation
        self.assertEqual(operation['status'], 'completed')
    
    def test_finish_feature_branch_uncommitted_changes(self):
        """Test feature branch finishing with uncommitted changes."""
        # Mock uncommitted changes
        self.workflow_manager.run_git_command = Mock(side_effect=lambda cmd, **kwargs: 
            'modified file.txt' if 'status' in cmd else True)
        self.workflow_manager.get_current_branch = Mock(return_value='feature/test')
        
        success, operation_id = self.workflow_manager.finish_feature_branch('feature/test', 'merge')
        
        self.assertFalse(success)
        self.assertIsNotNone(operation_id)
        
        # Check error was logged
        operation = self.workflow_manager.operation_log[-1]
        self.assertEqual(operation['status'], 'failed')
        self.assertIn('Uncommitted changes', operation['result']['error'])
    
    def test_rollback_start_feature(self):
        """Test rollback of start_feature operation."""
        # Create a start_feature operation
        operation_id = self.workflow_manager._log_operation('start_feature', {
            'feature_name': 'test-feature',
            'branch_name': 'feature/test-feature'
        })
        self.workflow_manager._update_operation_status(operation_id, 'completed', {
            'branch_name': 'feature/test-feature',
            'base_branch': 'main'
        })
        
        # Mock methods
        self.workflow_manager._branch_exists = Mock(return_value=True)
        self.workflow_manager.get_current_branch = Mock(return_value='main')
        self.workflow_manager.run_git_command = Mock(return_value=True)
        self.workflow_manager.get_remotes = Mock(return_value=['origin'])
        
        success = self.workflow_manager.rollback_workflow(operation_id)
        
        self.assertTrue(success)
        
        # Check that operation status was updated
        operation = next(op for op in self.workflow_manager.operation_log if op['id'] == operation_id)
        self.assertEqual(operation['status'], 'rolled_back')
    
    def test_rollback_nonexistent_operation(self):
        """Test rollback of non-existent operation."""
        success = self.workflow_manager.rollback_workflow('non-existent-id')
        self.assertFalse(success)
    
    def test_save_and_load_workflow_configs(self):
        """Test saving and loading workflow configurations."""
        # Modify a workflow config
        self.workflow_manager.workflow_configs['github_flow']['merge_strategy'] = 'rebase'
        
        # Save configurations
        success = self.workflow_manager._save_workflow_configs()
        self.assertTrue(success)
        
        # Create new instance to test loading
        new_manager = BranchWorkflowManager(self.mock_git_wrapper)
        new_manager.workflow_config_file = self.workflow_manager.workflow_config_file
        configs = new_manager._load_workflow_configs()
        
        # Check that custom config was loaded
        self.assertEqual(configs['github_flow']['merge_strategy'], 'rebase')
    
    def test_operation_log_persistence(self):
        """Test operation log saving and loading."""
        # Add some operations
        op1_id = self.workflow_manager._log_operation('start_feature', {'test': 'data1'})
        op2_id = self.workflow_manager._log_operation('finish_feature', {'test': 'data2'})
        
        # Save log
        success = self.workflow_manager._save_operation_log()
        self.assertTrue(success)
        
        # Create new instance to test loading
        new_manager = BranchWorkflowManager(self.mock_git_wrapper)
        new_manager.operation_log_file = self.workflow_manager.operation_log_file
        loaded_log = new_manager._load_operation_log()
        
        # Check that operations were loaded
        self.assertEqual(len(loaded_log), 2)
        self.assertEqual(loaded_log[0]['id'], op1_id)
        self.assertEqual(loaded_log[1]['id'], op2_id)
    
    def test_feature_config_integration(self):
        """Test integration with feature configuration system."""
        # Test getting feature config
        default_workflow = self.workflow_manager.get_feature_config('default_workflow')
        self.assertEqual(default_workflow, 'github_flow')
        
        # Test setting feature config
        self.workflow_manager.set_feature_config('default_workflow', 'git_flow')
        updated_workflow = self.workflow_manager.get_feature_config('default_workflow')
        self.assertEqual(updated_workflow, 'git_flow')
        
        # Verify save_config was called
        self.mock_git_wrapper.save_config.assert_called()


class TestBranchWorkflowManagerIntegration(unittest.TestCase):
    """Integration tests for BranchWorkflowManager with real Git operations."""
    
    def setUp(self):
        """Set up test environment with real Git repository."""
        # Create temporary directory for test repository
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        
        # Initialize git repository
        subprocess.run(['git', 'init'], cwd=self.test_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.test_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.test_dir, capture_output=True)
        
        # Create initial commit
        test_file = Path(self.test_dir) / 'README.md'
        test_file.write_text('# Test Repository')
        subprocess.run(['git', 'add', 'README.md'], cwd=self.test_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=self.test_dir, capture_output=True)
        
        # Rename master to main if needed
        subprocess.run(['git', 'branch', '-M', 'main'], cwd=self.test_dir, capture_output=True)
        
        # Change to test directory
        import os
        os.chdir(self.test_dir)
        
        # Create mock git wrapper with minimal functionality
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {
            'default_remote': 'origin',
            'advanced_features': {
                'branch_workflows': {
                    'default_workflow': 'github_flow',
                    'auto_track_remotes': False,  # Disable for testing
                    'base_branch': 'main',
                    'auto_cleanup': False,  # Disable for testing
                    'merge_strategy': 'merge',
                    'push_after_finish': False,  # Disable for testing
                    'delete_after_merge': False  # Disable for testing
                }
            }
        }
        self.mock_git_wrapper.save_config = Mock()
        self.mock_git_wrapper.print_success = Mock()
        self.mock_git_wrapper.print_error = Mock()
        self.mock_git_wrapper.print_info = Mock()
        self.mock_git_wrapper.print_working = Mock()
        
        # Create BranchWorkflowManager instance
        self.workflow_manager = BranchWorkflowManager(self.mock_git_wrapper)
    
    def tearDown(self):
        """Clean up test environment."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_real_git_start_feature_branch(self):
        """Test starting a feature branch with real Git commands."""
        success, operation_id = self.workflow_manager.start_feature_branch('test-feature', 'feature', 'github_flow')
        
        self.assertTrue(success)
        self.assertIsNotNone(operation_id)
        
        # Check that branch was actually created
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True, cwd=self.test_dir)
        self.assertEqual(result.stdout.strip(), 'feature/test-feature')
        
        # Check operation log
        operation = self.workflow_manager.operation_log[-1]
        self.assertEqual(operation['status'], 'completed')
        self.assertEqual(operation['result']['branch_name'], 'feature/test-feature')
    
    def test_real_git_finish_feature_branch(self):
        """Test finishing a feature branch with real Git commands."""
        # First create a feature branch
        success, start_op_id = self.workflow_manager.start_feature_branch('test-feature', 'feature', 'github_flow')
        self.assertTrue(success)
        
        # Make a commit on the feature branch
        test_file = Path(self.test_dir) / 'feature.txt'
        test_file.write_text('Feature implementation')
        subprocess.run(['git', 'add', 'feature.txt'], cwd=self.test_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Add feature implementation'], cwd=self.test_dir, capture_output=True)
        
        # Finish the feature branch
        success, finish_op_id = self.workflow_manager.finish_feature_branch('feature/test-feature', 'merge')
        
        self.assertTrue(success)
        self.assertIsNotNone(finish_op_id)
        
        # Check that we're back on main branch
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True, cwd=self.test_dir)
        self.assertEqual(result.stdout.strip(), 'main')
        
        # Check that feature was merged (feature.txt should exist)
        self.assertTrue((Path(self.test_dir) / 'feature.txt').exists())
        
        # Check operation log
        operation = self.workflow_manager.operation_log[-1]
        self.assertEqual(operation['status'], 'completed')


if __name__ == '__main__':
    unittest.main()