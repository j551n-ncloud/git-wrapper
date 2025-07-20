#!/usr/bin/env python3
"""
Unit Tests for Smart Backup System

This module contains comprehensive tests for the SmartBackupSystem class,
covering backup configuration, remote management, backup operations,
and error handling scenarios.
"""

import unittest
import tempfile
import shutil
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the class to test
from features.smart_backup_system import SmartBackupSystem


class TestSmartBackupSystem(unittest.TestCase):
    """Test cases for SmartBackupSystem class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create temporary directory for test repository
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        
        # Create mock git wrapper
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {
            'advanced_features': {
                'smartbackup': {
                    'backup_remotes': [],
                    'auto_backup_branches': ['main', 'develop'],
                    'retention_days': 90,
                    'max_backup_versions': 50,
                    'backup_timeout_minutes': 30,
                    'verify_backups': True
                }
            }
        }
        self.mock_git_wrapper.save_config = Mock()
        self.mock_git_wrapper.print_success = Mock()
        self.mock_git_wrapper.print_error = Mock()
        self.mock_git_wrapper.print_info = Mock()
        self.mock_git_wrapper.print_working = Mock()
        self.mock_git_wrapper.get_input = Mock()
        self.mock_git_wrapper.get_choice = Mock()
        self.mock_git_wrapper.get_multiple_choice = Mock()
        self.mock_git_wrapper.confirm = Mock()
        self.mock_git_wrapper.clear_screen = Mock()
        
        # Create SmartBackupSystem instance
        self.backup_system = SmartBackupSystem(self.mock_git_wrapper)
        
        # Mock file paths to use test directory
        self.backup_system.backup_log_file = self.test_path / 'backup.log'
        self.backup_system.backup_config_file = self.test_path / 'backup_config.json'
    
    def tearDown(self):
        """Clean up test environment after each test."""
        # Remove temporary directory
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_init_default_config(self):
        """Test initialization with default configuration."""
        default_config = self.backup_system._get_default_config()
        
        expected_keys = [
            'backup_remotes', 'auto_backup_branches', 'retention_days',
            'max_backup_versions', 'backup_on_push', 'backup_on_merge',
            'backup_schedule_enabled', 'backup_schedule_hours',
            'backup_timeout_minutes', 'verify_backups', 'compress_backups'
        ]
        
        for key in expected_keys:
            self.assertIn(key, default_config)
        
        self.assertEqual(default_config['auto_backup_branches'], ['main', 'master', 'develop'])
        self.assertEqual(default_config['retention_days'], 90)
        self.assertEqual(default_config['max_backup_versions'], 50)
        self.assertTrue(default_config['verify_backups'])
    
    def test_load_backup_config(self):
        """Test loading backup configuration from file."""
        # Create test config file
        test_config = {
            'remotes': {
                'backup1': {
                    'url': 'https://github.com/user/backup1.git',
                    'enabled': True
                }
            },
            'schedules': {},
            'last_backup': {},
            'backup_history': []
        }
        
        with open(self.backup_system.backup_config_file, 'w') as f:
            json.dump(test_config, f)
        
        loaded_config = self.backup_system._load_backup_config()
        
        self.assertEqual(loaded_config['remotes']['backup1']['url'], 
                        'https://github.com/user/backup1.git')
        self.assertTrue(loaded_config['remotes']['backup1']['enabled'])
    
    def test_save_backup_config(self):
        """Test saving backup configuration to file."""
        test_config = {
            'remotes': {
                'test_remote': {
                    'url': 'git@github.com:user/repo.git',
                    'enabled': True,
                    'auth_method': 'ssh-key'
                }
            }
        }
        
        self.backup_system.backup_config = test_config
        result = self.backup_system._save_backup_config()
        
        self.assertTrue(result)
        self.assertTrue(self.backup_system.backup_config_file.exists())
        
        # Verify saved content
        with open(self.backup_system.backup_config_file, 'r') as f:
            saved_config = json.load(f)
        
        self.assertEqual(saved_config['remotes']['test_remote']['url'],
                        'git@github.com:user/repo.git')
    
    def test_validate_git_url(self):
        """Test Git URL validation."""
        valid_urls = [
            'https://github.com/user/repo.git',
            'http://gitlab.com/user/repo.git',
            'git@github.com:user/repo.git',
            'ssh://git@server.com/repo.git',
            'file:///path/to/repo.git',
            '/local/path/to/repo'
        ]
        
        invalid_urls = [
            '',
            'not-a-url',
            'ftp://server.com/repo',
            None
        ]
        
        for url in valid_urls:
            self.assertTrue(self.backup_system._validate_git_url(url), 
                          f"URL should be valid: {url}")
        
        for url in invalid_urls:
            self.assertFalse(self.backup_system._validate_git_url(url), 
                           f"URL should be invalid: {url}")
    
    @patch('subprocess.run')
    def test_test_specific_remote_success(self, mock_subprocess):
        """Test successful remote connection testing."""
        # Setup mock remote
        self.backup_system.backup_config = {
            'remotes': {
                'test_remote': {
                    'url': 'https://github.com/user/repo.git',
                    'enabled': True
                }
            }
        }
        
        # Mock successful git ls-remote
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "ref: refs/heads/main\n"
        
        with patch.object(self.backup_system, 'run_git_command', return_value="success"):
            result = self.backup_system._test_specific_remote('test_remote')
        
        self.assertTrue(result)
        self.assertEqual(
            self.backup_system.backup_config['remotes']['test_remote']['connection_status'],
            'success'
        )
    
    @patch('subprocess.run')
    def test_test_specific_remote_failure(self, mock_subprocess):
        """Test failed remote connection testing."""
        # Setup mock remote
        self.backup_system.backup_config = {
            'remotes': {
                'test_remote': {
                    'url': 'https://invalid-url.git',
                    'enabled': True
                }
            }
        }
        
        with patch.object(self.backup_system, 'run_git_command', return_value=False):
            result = self.backup_system._test_specific_remote('test_remote')
        
        self.assertFalse(result)
        self.assertEqual(
            self.backup_system.backup_config['remotes']['test_remote']['connection_status'],
            'failed'
        )
    
    def test_generate_backup_id(self):
        """Test backup ID generation."""
        backup_id = self.backup_system._generate_backup_id()
        
        self.assertIsInstance(backup_id, str)
        self.assertTrue(backup_id.startswith('backup_'))
        self.assertEqual(len(backup_id), 22)  # backup_ + YYYYMMDD_HHMMSS
    
    @patch('time.time')
    def test_branch_exists(self, mock_time):
        """Test branch existence checking."""
        mock_time.return_value = 1234567890
        
        with patch.object(self.backup_system, 'get_branches', return_value=['main', 'develop', 'feature']):
            self.assertTrue(self.backup_system._branch_exists('main'))
            self.assertTrue(self.backup_system._branch_exists('develop'))
            self.assertFalse(self.backup_system._branch_exists('nonexistent'))
    
    @patch('builtins.open', create=True)
    def test_log_backup_operation(self, mock_open):
        """Test backup operation logging."""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        backup_entry = {
            'id': 'backup_20240101_120000',
            'timestamp': 1234567890,
            'branches': ['main'],
            'remotes': ['backup1'],
            'status': 'completed',
            'duration': 30.5,
            'errors': []
        }
        
        self.backup_system._log_backup_operation(backup_entry)
        
        mock_open.assert_called_once_with(self.backup_system.backup_log_file, 'a', encoding='utf-8')
        mock_file.write.assert_called_once()
        
        # Verify log entry format
        written_data = mock_file.write.call_args[0][0]
        log_entry = json.loads(written_data.strip())
        
        self.assertEqual(log_entry['id'], 'backup_20240101_120000')
        self.assertEqual(log_entry['status'], 'completed')
        self.assertEqual(log_entry['branches'], ['main'])
    
    def test_backup_branch_to_remote_no_url(self):
        """Test backup failure when remote has no URL."""
        remote_config = {'enabled': True}  # Missing URL
        
        result = self.backup_system._backup_branch_to_remote('main', 'test_remote', remote_config)
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_error.assert_called_with(
            "No URL configured for remote 'test_remote'"
        )
    
    def test_backup_branch_to_remote_branch_not_exists(self):
        """Test backup failure when branch doesn't exist."""
        remote_config = {
            'url': 'https://github.com/user/repo.git',
            'enabled': True
        }
        
        with patch.object(self.backup_system, '_branch_exists', return_value=False):
            result = self.backup_system._backup_branch_to_remote('nonexistent', 'test_remote', remote_config)
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_error.assert_called_with(
            "Branch 'nonexistent' does not exist locally"
        )
    
    @patch('time.time')
    def test_backup_branch_to_remote_success(self, mock_time):
        """Test successful branch backup to remote."""
        mock_time.return_value = 1234567890
        
        remote_config = {
            'url': 'https://github.com/user/repo.git',
            'enabled': True
        }
        
        with patch.object(self.backup_system, '_branch_exists', return_value=True), \
             patch.object(self.backup_system, 'run_git_command', side_effect=[True, True, True]):
            
            result = self.backup_system._backup_branch_to_remote('main', 'test_remote', remote_config)
        
        self.assertTrue(result)
        self.assertEqual(remote_config['last_backup'], 1234567890)
    
    def test_create_backup_already_in_progress(self):
        """Test backup creation when another backup is in progress."""
        self.backup_system.backup_in_progress = True
        
        result = self.backup_system.create_backup(['main'], ['remote1'])
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_error.assert_called_with(
            "Another backup is already in progress"
        )
    
    @patch('time.time')
    def test_create_backup_success(self, mock_time):
        """Test successful backup creation."""
        mock_time.return_value = 1234567890
        
        # Setup backup config
        self.backup_system.backup_config = {
            'remotes': {
                'remote1': {
                    'url': 'https://github.com/user/repo.git',
                    'enabled': True
                }
            },
            'backup_history': []
        }
        
        with patch.object(self.backup_system, '_backup_branch_to_remote', return_value=True), \
             patch.object(self.backup_system, '_save_backup_config', return_value=True), \
             patch.object(self.backup_system, '_log_backup_operation'):
            
            result = self.backup_system.create_backup(['main'], ['remote1'], 'test_backup')
        
        self.assertTrue(result)
        self.assertFalse(self.backup_system.backup_in_progress)
        
        # Verify backup history was updated
        self.assertEqual(len(self.backup_system.backup_config['backup_history']), 1)
        backup_entry = self.backup_system.backup_config['backup_history'][0]
        self.assertEqual(backup_entry['id'], 'test_backup')
        self.assertEqual(backup_entry['status'], 'completed')
    
    @patch('time.time')
    def test_create_backup_partial_failure(self, mock_time):
        """Test backup creation with partial failures."""
        mock_time.return_value = 1234567890
        
        # Setup backup config with multiple remotes
        self.backup_system.backup_config = {
            'remotes': {
                'remote1': {'url': 'https://github.com/user/repo1.git', 'enabled': True},
                'remote2': {'url': 'https://github.com/user/repo2.git', 'enabled': True}
            },
            'backup_history': []
        }
        
        # Mock one success, one failure
        def mock_backup_branch(branch, remote, config):
            return remote == 'remote1'  # Only remote1 succeeds
        
        with patch.object(self.backup_system, '_backup_branch_to_remote', side_effect=mock_backup_branch), \
             patch.object(self.backup_system, '_save_backup_config', return_value=True), \
             patch.object(self.backup_system, '_log_backup_operation'):
            
            result = self.backup_system.create_backup(['main'], ['remote1', 'remote2'], 'test_backup')
        
        self.assertFalse(result)  # Overall failure due to partial failure
        
        # Verify backup entry shows failed status
        backup_entry = self.backup_system.backup_config['backup_history'][0]
        self.assertEqual(backup_entry['status'], 'failed')
        self.assertTrue(len(backup_entry['errors']) > 0)


class TestSmartBackupSystemConfiguration(unittest.TestCase):
    """Test cases for SmartBackupSystem configuration management."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {'advanced_features': {}}
        self.mock_git_wrapper.save_config = Mock()
        
        self.backup_system = SmartBackupSystem(self.mock_git_wrapper)
    
    def test_get_feature_config(self):
        """Test getting feature configuration."""
        # Test getting entire config
        config = self.backup_system.get_feature_config()
        self.assertIsInstance(config, dict)
        
        # Test getting specific key
        retention_days = self.backup_system.get_feature_config('retention_days')
        self.assertEqual(retention_days, 90)
        
        # Test getting non-existent key
        non_existent = self.backup_system.get_feature_config('non_existent_key')
        self.assertIsNone(non_existent)
    
    def test_set_feature_config(self):
        """Test setting feature configuration."""
        self.backup_system.set_feature_config('test_key', 'test_value')
        
        # Verify config was updated
        config = self.backup_system.get_feature_config()
        self.assertEqual(config['test_key'], 'test_value')
        
        # Verify save_config was called
        self.mock_git_wrapper.save_config.assert_called_once()
    
    def test_update_feature_config(self):
        """Test updating multiple configuration values."""
        update_dict = {
            'retention_days': 120,
            'max_backup_versions': 100,
            'new_setting': True
        }
        
        self.backup_system.update_feature_config(update_dict)
        
        # Verify all values were updated
        config = self.backup_system.get_feature_config()
        self.assertEqual(config['retention_days'], 120)
        self.assertEqual(config['max_backup_versions'], 100)
        self.assertTrue(config['new_setting'])


class TestSmartBackupSystemIntegration(unittest.TestCase):
    """Integration tests for SmartBackupSystem."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)
        
        # Create mock git wrapper with more realistic behavior
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {
            'advanced_features': {
                'smartbackup': {
                    'auto_backup_branches': ['main'],
                    'retention_days': 30
                }
            }
        }
        
        self.backup_system = SmartBackupSystem(self.mock_git_wrapper)
        self.backup_system.backup_config_file = self.test_path / 'backup_config.json'
    
    def tearDown(self):
        """Clean up integration test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_full_backup_workflow(self):
        """Test complete backup workflow from configuration to execution."""
        # Step 1: Configure remote
        remote_config = {
            'url': 'https://github.com/user/backup.git',
            'enabled': True,
            'auth_method': 'none',
            'auth_config': {},
            'created_at': time.time()
        }
        
        self.backup_system.backup_config = {
            'remotes': {'backup_remote': remote_config},
            'backup_history': []
        }
        
        # Step 2: Test remote connection
        with patch.object(self.backup_system, 'run_git_command', return_value="success"):
            connection_result = self.backup_system._test_specific_remote('backup_remote')
            self.assertTrue(connection_result)
        
        # Step 3: Create backup
        with patch.object(self.backup_system, '_branch_exists', return_value=True), \
             patch.object(self.backup_system, 'run_git_command', return_value=True), \
             patch.object(self.backup_system, '_save_backup_config', return_value=True), \
             patch.object(self.backup_system, '_log_backup_operation'):
            
            backup_result = self.backup_system.create_backup(['main'], ['backup_remote'])
            self.assertTrue(backup_result)
        
        # Step 4: Verify backup history
        history = self.backup_system.backup_config.get('backup_history', [])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['status'], 'completed')


class TestSmartBackupSystemScheduling(unittest.TestCase):
    """Test cases for SmartBackupSystem scheduling functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {
            'advanced_features': {
                'smartbackup': {
                    'backup_schedule_enabled': False,
                    'backup_schedule_hours': 24,
                    'backup_on_push': False,
                    'backup_on_merge': False,
                    'auto_backup_branches': ['main']
                }
            }
        }
        self.mock_git_wrapper.save_config = Mock()
        self.mock_git_wrapper.print_success = Mock()
        self.mock_git_wrapper.print_error = Mock()
        self.mock_git_wrapper.print_info = Mock()
        self.mock_git_wrapper.print_working = Mock()
        
        self.backup_system = SmartBackupSystem(self.mock_git_wrapper)
        self.backup_system.backup_config = {
            'remotes': {
                'backup1': {'url': 'https://github.com/user/backup.git', 'enabled': True}
            },
            'last_backup': {}
        }
    
    def test_should_run_scheduled_backup_no_previous(self):
        """Test scheduled backup should run when no previous backup exists."""
        result = self.backup_system._should_run_scheduled_backup()
        self.assertTrue(result)
    
    @patch('time.time')
    def test_should_run_scheduled_backup_time_elapsed(self, mock_time):
        """Test scheduled backup should run when enough time has elapsed."""
        # Set current time
        current_time = 1000000
        mock_time.return_value = current_time
        
        # Set last backup to 25 hours ago (schedule is 24 hours)
        last_backup_time = current_time - (25 * 3600)
        self.backup_system.backup_config['last_backup'] = {
            'timestamp': last_backup_time
        }
        
        result = self.backup_system._should_run_scheduled_backup()
        self.assertTrue(result)
    
    @patch('time.time')
    def test_should_run_scheduled_backup_time_not_elapsed(self, mock_time):
        """Test scheduled backup should not run when not enough time has elapsed."""
        # Set current time
        current_time = 1000000
        mock_time.return_value = current_time
        
        # Set last backup to 12 hours ago (schedule is 24 hours)
        last_backup_time = current_time - (12 * 3600)
        self.backup_system.backup_config['last_backup'] = {
            'timestamp': last_backup_time
        }
        
        result = self.backup_system._should_run_scheduled_backup()
        self.assertFalse(result)
    
    def test_get_enabled_remotes(self):
        """Test getting enabled remotes."""
        self.backup_system.backup_config = {
            'remotes': {
                'remote1': {'enabled': True},
                'remote2': {'enabled': False},
                'remote3': {'enabled': True},
                'remote4': {}  # Default should be enabled
            }
        }
        
        enabled_remotes = self.backup_system._get_enabled_remotes()
        
        # remote4 should be included as default is enabled
        expected = ['remote1', 'remote3', 'remote4']
        self.assertEqual(sorted(enabled_remotes), sorted(expected))
    
    def test_trigger_event_backup_push_disabled(self):
        """Test event backup doesn't trigger when push events are disabled."""
        result = self.backup_system.trigger_event_backup('push')
        self.assertFalse(result)
    
    def test_trigger_event_backup_merge_disabled(self):
        """Test event backup doesn't trigger when merge events are disabled."""
        result = self.backup_system.trigger_event_backup('merge')
        self.assertFalse(result)
    
    def test_trigger_event_backup_in_progress(self):
        """Test event backup doesn't trigger when another backup is in progress."""
        # Enable push backups
        self.backup_system.set_feature_config('backup_on_push', True)
        
        # Set backup in progress
        self.backup_system.backup_in_progress = True
        
        result = self.backup_system.trigger_event_backup('push')
        self.assertFalse(result)
        
        # Verify info message was printed
        self.mock_git_wrapper.print_info.assert_called_with(
            "Skipping push backup - another backup in progress"
        )
    
    def test_trigger_event_backup_success(self):
        """Test successful event backup trigger."""
        # Enable push backups
        self.backup_system.set_feature_config('backup_on_push', True)
        
        with patch.object(self.backup_system, 'get_current_branch', return_value='main'), \
             patch.object(self.backup_system, 'create_backup', return_value=True):
            
            result = self.backup_system.trigger_event_backup('push')
            self.assertTrue(result)
    
    def test_trigger_event_backup_no_current_branch(self):
        """Test event backup fails when no current branch."""
        # Enable push backups
        self.backup_system.set_feature_config('backup_on_push', True)
        
        with patch.object(self.backup_system, 'get_current_branch', return_value=None):
            result = self.backup_system.trigger_event_backup('push')
            self.assertFalse(result)
    
    def test_trigger_event_backup_no_remotes(self):
        """Test event backup fails when no enabled remotes."""
        # Enable push backups
        self.backup_system.set_feature_config('backup_on_push', True)
        
        # Disable all remotes
        self.backup_system.backup_config = {'remotes': {}}
        
        with patch.object(self.backup_system, 'get_current_branch', return_value='main'):
            result = self.backup_system.trigger_event_backup('push')
            self.assertFalse(result)


class TestSmartBackupSystemProgressTracking(unittest.TestCase):
    """Test cases for backup progress tracking and status reporting."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {'advanced_features': {}}
        self.mock_git_wrapper.print_working = Mock()
        
        self.backup_system = SmartBackupSystem(self.mock_git_wrapper)
    
    @patch('time.time')
    def test_backup_progress_tracking(self, mock_time):
        """Test backup progress tracking during multi-branch, multi-remote backup."""
        mock_time.return_value = 1234567890
        
        # Setup multiple branches and remotes
        branches = ['main', 'develop', 'feature']
        remotes = ['remote1', 'remote2']
        
        self.backup_system.backup_config = {
            'remotes': {
                'remote1': {'url': 'https://github.com/user/repo1.git', 'enabled': True},
                'remote2': {'url': 'https://github.com/user/repo2.git', 'enabled': True}
            },
            'backup_history': []
        }
        
        # Track print_working calls to verify progress reporting
        progress_calls = []
        
        def track_progress(message):
            progress_calls.append(message)
        
        self.mock_git_wrapper.print_working.side_effect = track_progress
        
        with patch.object(self.backup_system, '_backup_branch_to_remote', return_value=True), \
             patch.object(self.backup_system, '_save_backup_config', return_value=True), \
             patch.object(self.backup_system, '_log_backup_operation'):
            
            result = self.backup_system.create_backup(branches, remotes, 'test_backup')
        
        self.assertTrue(result)
        
        # Verify progress was reported for each operation
        # Should have: starting message + (3 branches × 2 remotes) progress messages
        self.assertGreaterEqual(len(progress_calls), 6)
        
        # Check that progress percentages are included
        progress_messages = [call for call in progress_calls if '%)' in call]
        self.assertGreater(len(progress_messages), 0)
    
    def test_backup_status_reporting(self):
        """Test backup status reporting in backup history."""
        # Setup backup history with various statuses
        self.backup_system.backup_config = {
            'backup_history': [
                {
                    'id': 'backup_1',
                    'timestamp': 1234567890,
                    'status': 'completed',
                    'branches': ['main'],
                    'remotes': ['remote1'],
                    'duration': 30.5,
                    'errors': []
                },
                {
                    'id': 'backup_2',
                    'timestamp': 1234567800,
                    'status': 'failed',
                    'branches': ['main', 'develop'],
                    'remotes': ['remote1', 'remote2'],
                    'duration': 45.2,
                    'errors': ['Failed to backup develop to remote2']
                }
            ]
        }
        
        # Test that backup history contains expected information
        history = self.backup_system.backup_config['backup_history']
        
        completed_backup = history[0]
        self.assertEqual(completed_backup['status'], 'completed')
        self.assertEqual(len(completed_backup['errors']), 0)
        
        failed_backup = history[1]
        self.assertEqual(failed_backup['status'], 'failed')
        self.assertGreater(len(failed_backup['errors']), 0)


if __name__ == '__main__':
    unittest.main()


class TestSmartBackupSystemRestoration(unittest.TestCase):
    """Test cases for SmartBackupSystem restoration functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {'advanced_features': {}}
        self.mock_git_wrapper.print_success = Mock()
        self.mock_git_wrapper.print_error = Mock()
        self.mock_git_wrapper.print_info = Mock()
        self.mock_git_wrapper.print_working = Mock()
        self.mock_git_wrapper.get_choice = Mock()
        self.mock_git_wrapper.get_multiple_choice = Mock()
        self.mock_git_wrapper.confirm = Mock()
        
        self.backup_system = SmartBackupSystem(self.mock_git_wrapper)
        
        # Setup test backup history
        self.backup_system.backup_config = {
            'remotes': {
                'backup_remote': {
                    'url': 'https://github.com/user/backup.git',
                    'enabled': True
                }
            },
            'backup_history': [
                {
                    'id': 'backup_20240101_120000',
                    'timestamp': 1704110400,  # 2024-01-01 12:00:00
                    'status': 'completed',
                    'branches': ['main', 'develop'],
                    'remotes': ['backup_remote'],
                    'duration': 30.5,
                    'errors': [],
                    'results': {
                        'backup_remote': {
                            'main': True,
                            'develop': True
                        }
                    }
                },
                {
                    'id': 'backup_20240102_120000',
                    'timestamp': 1704196800,  # 2024-01-02 12:00:00
                    'status': 'failed',
                    'branches': ['main', 'feature'],
                    'remotes': ['backup_remote'],
                    'duration': 15.2,
                    'errors': ['Failed to backup feature to backup_remote'],
                    'results': {
                        'backup_remote': {
                            'main': True,
                            'feature': False
                        }
                    }
                }
            ]
        }
    
    def test_list_backup_versions(self):
        """Test listing available backup versions."""
        with patch('builtins.input'):  # Mock input to avoid blocking
            versions = self.backup_system.list_backup_versions()
        
        self.assertEqual(len(versions), 2)
        
        # Check that versions are sorted by timestamp (newest first)
        self.assertEqual(versions[0]['id'], 'backup_20240102_120000')
        self.assertEqual(versions[1]['id'], 'backup_20240101_120000')
        
        # Check version information
        first_version = versions[0]
        self.assertEqual(first_version['status'], 'failed')
        self.assertEqual(first_version['branches'], ['main', 'feature'])
        self.assertEqual(first_version['remotes'], ['backup_remote'])
    
    def test_list_backup_versions_empty(self):
        """Test listing backup versions when none exist."""
        self.backup_system.backup_config = {'backup_history': []}
        
        with patch('builtins.input'):
            versions = self.backup_system.list_backup_versions()
        
        self.assertEqual(len(versions), 0)
    
    def test_get_branch_commit(self):
        """Test getting branch commit hash."""
        with patch.object(self.backup_system, 'run_git_command', return_value='abc123def456'):
            commit = self.backup_system._get_branch_commit('main')
            self.assertEqual(commit, 'abc123def456')
    
    def test_get_branch_commit_failure(self):
        """Test getting branch commit when command fails."""
        with patch.object(self.backup_system, 'run_git_command', return_value=False):
            commit = self.backup_system._get_branch_commit('main')
            self.assertIsNone(commit)
    
    def test_get_backup_commits(self):
        """Test getting backup commits from remotes."""
        # Mock ls-remote output
        ls_remote_output = "abc123def456\trefs/heads/main\n"
        
        with patch.object(self.backup_system, 'run_git_command', return_value=ls_remote_output):
            commits = self.backup_system._get_backup_commits('main', ['backup_remote'])
        
        self.assertEqual(commits['backup_remote'], 'abc123def456')
    
    def test_get_backup_commits_no_remote_config(self):
        """Test getting backup commits when remote config is missing."""
        commits = self.backup_system._get_backup_commits('main', ['nonexistent_remote'])
        self.assertIsNone(commits['nonexistent_remote'])
    
    def test_get_commit_difference(self):
        """Test getting commit difference between local and backup."""
        with patch.object(self.backup_system, 'run_git_command', side_effect=['3', '1']):
            ahead, behind = self.backup_system._get_commit_difference('main', 'abc123')
            
            self.assertEqual(ahead, 3)
            self.assertEqual(behind, 1)
    
    def test_get_commit_difference_failure(self):
        """Test getting commit difference when commands fail."""
        with patch.object(self.backup_system, 'run_git_command', return_value=False):
            ahead, behind = self.backup_system._get_commit_difference('main', 'abc123')
            
            self.assertIsNone(ahead)
            self.assertIsNone(behind)
    
    def test_has_local_changes_true(self):
        """Test detecting local changes when they exist."""
        # Mock git diff commands to indicate changes
        with patch.object(self.backup_system, 'run_git_command', return_value=False):
            has_changes = self.backup_system._has_local_changes()
            self.assertTrue(has_changes)
    
    def test_has_local_changes_false(self):
        """Test detecting local changes when none exist."""
        # Mock git diff commands to indicate no changes
        with patch.object(self.backup_system, 'run_git_command', return_value=True):
            has_changes = self.backup_system._has_local_changes()
            self.assertFalse(has_changes)
    
    def test_stash_local_changes_success(self):
        """Test successfully stashing local changes."""
        with patch.object(self.backup_system, 'run_git_command', return_value=True):
            result = self.backup_system._stash_local_changes()
            self.assertTrue(result)
    
    def test_stash_local_changes_failure(self):
        """Test failing to stash local changes."""
        with patch.object(self.backup_system, 'run_git_command', return_value=False):
            result = self.backup_system._stash_local_changes()
            self.assertFalse(result)
    
    def test_restore_from_backup_remote_not_found(self):
        """Test restoration failure when remote is not found."""
        result = self.backup_system.restore_from_backup('test_backup', 'main', 'nonexistent_remote')
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_error.assert_called_with(
            "Remote 'nonexistent_remote' not found in configuration"
        )
    
    def test_restore_from_backup_no_url(self):
        """Test restoration failure when remote has no URL."""
        # Add remote without URL
        self.backup_system.backup_config['remotes']['no_url_remote'] = {'enabled': True}
        
        result = self.backup_system.restore_from_backup('test_backup', 'main', 'no_url_remote')
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_error.assert_called_with(
            "No URL configured for remote 'no_url_remote'"
        )
    
    @patch('time.time')
    def test_restore_from_backup_success_existing_branch(self, mock_time):
        """Test successful restoration of existing branch."""
        mock_time.return_value = 1234567890
        
        # Mock all required methods
        with patch.object(self.backup_system, '_has_local_changes', return_value=False), \
             patch.object(self.backup_system, '_branch_exists', return_value=True), \
             patch.object(self.backup_system, 'run_git_command', return_value=True):
            
            result = self.backup_system.restore_from_backup('test_backup', 'main', 'backup_remote')
        
        self.assertTrue(result)
    
    @patch('time.time')
    def test_restore_from_backup_success_new_branch(self, mock_time):
        """Test successful restoration creating new branch."""
        mock_time.return_value = 1234567890
        
        # Mock all required methods
        with patch.object(self.backup_system, '_has_local_changes', return_value=False), \
             patch.object(self.backup_system, '_branch_exists', return_value=False), \
             patch.object(self.backup_system, 'run_git_command', return_value=True):
            
            result = self.backup_system.restore_from_backup('test_backup', 'new_branch', 'backup_remote')
        
        self.assertTrue(result)
    
    @patch('time.time')
    def test_restore_from_backup_with_local_changes(self, mock_time):
        """Test restoration with local changes requiring stash."""
        mock_time.return_value = 1234567890
        
        # Mock user confirms stashing
        self.mock_git_wrapper.confirm.side_effect = [True, True]  # Continue with restoration, stash changes
        
        with patch.object(self.backup_system, '_has_local_changes', return_value=True), \
             patch.object(self.backup_system, '_stash_local_changes', return_value=True), \
             patch.object(self.backup_system, '_branch_exists', return_value=True), \
             patch.object(self.backup_system, 'run_git_command', return_value=True):
            
            result = self.backup_system.restore_from_backup('test_backup', 'main', 'backup_remote')
        
        self.assertTrue(result)
    
    @patch('time.time')
    def test_restore_from_backup_user_cancels_with_changes(self, mock_time):
        """Test restoration cancelled by user when local changes exist."""
        mock_time.return_value = 1234567890
        
        # Mock user cancels restoration
        self.mock_git_wrapper.confirm.return_value = False
        
        with patch.object(self.backup_system, '_has_local_changes', return_value=True):
            result = self.backup_system.restore_from_backup('test_backup', 'main', 'backup_remote')
        
        self.assertFalse(result)
    
    def test_restore_from_backup_fetch_failure(self):
        """Test restoration failure when fetch fails."""
        with patch.object(self.backup_system, '_has_local_changes', return_value=False), \
             patch.object(self.backup_system, 'run_git_command', side_effect=[True, False, True]):
            # First call (add remote) succeeds, second call (fetch) fails, third call (remove remote) succeeds
            
            result = self.backup_system.restore_from_backup('test_backup', 'main', 'backup_remote')
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_error.assert_called_with(
            "Failed to fetch branch 'main' from remote"
        )


class TestSmartBackupSystemCleanup(unittest.TestCase):
    """Test cases for SmartBackupSystem cleanup functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {
            'advanced_features': {
                'smartbackup': {
                    'retention_days': 30,
                    'max_backup_versions': 10,
                    'verify_backups': True
                }
            }
        }
        self.mock_git_wrapper.save_config = Mock()
        self.mock_git_wrapper.print_success = Mock()
        self.mock_git_wrapper.print_error = Mock()
        self.mock_git_wrapper.print_info = Mock()
        self.mock_git_wrapper.confirm = Mock()
        
        self.backup_system = SmartBackupSystem(self.mock_git_wrapper)
        
        # Setup test backup history with various ages and statuses
        current_time = time.time()
        self.backup_system.backup_config = {
            'backup_history': [
                {
                    'id': 'recent_backup',
                    'timestamp': current_time - (5 * 24 * 3600),  # 5 days old
                    'status': 'completed'
                },
                {
                    'id': 'old_backup_1',
                    'timestamp': current_time - (35 * 24 * 3600),  # 35 days old
                    'status': 'completed'
                },
                {
                    'id': 'old_backup_2',
                    'timestamp': current_time - (40 * 24 * 3600),  # 40 days old
                    'status': 'completed'
                },
                {
                    'id': 'failed_backup',
                    'timestamp': current_time - (10 * 24 * 3600),  # 10 days old
                    'status': 'failed',
                    'errors': ['Test error']
                }
            ]
        }
    
    @patch('time.time')
    def test_get_old_backups(self, mock_time):
        """Test getting old backups based on retention policy."""
        current_time = 1000000
        mock_time.return_value = current_time
        
        # Set backup timestamps
        self.backup_system.backup_config['backup_history'] = [
            {'id': 'recent', 'timestamp': current_time - (20 * 24 * 3600)},  # 20 days old
            {'id': 'old1', 'timestamp': current_time - (35 * 24 * 3600)},    # 35 days old
            {'id': 'old2', 'timestamp': current_time - (45 * 24 * 3600)}     # 45 days old
        ]
        
        old_backups = self.backup_system._get_old_backups(30)  # 30 day retention
        
        self.assertEqual(len(old_backups), 2)
        old_ids = [b['id'] for b in old_backups]
        self.assertIn('old1', old_ids)
        self.assertIn('old2', old_ids)
        self.assertNotIn('recent', old_ids)
    
    def test_get_failed_backups(self):
        """Test getting failed backup entries."""
        failed_backups = self.backup_system._get_failed_backups()
        
        self.assertEqual(len(failed_backups), 1)
        self.assertEqual(failed_backups[0]['id'], 'failed_backup')
        self.assertEqual(failed_backups[0]['status'], 'failed')
    
    def test_delete_backup_entries(self):
        """Test deleting backup entries from history."""
        # Get initial count
        initial_count = len(self.backup_system.backup_config['backup_history'])
        
        # Delete failed backup
        failed_backups = self._get_failed_backups()
        
        with patch.object(self.backup_system, '_save_backup_config', return_value=True):
            deleted_count = self.backup_system._delete_backup_entries(failed_backups)
        
        self.assertEqual(deleted_count, 1)
        self.assertEqual(len(self.backup_system.backup_config['backup_history']), initial_count - 1)
        
        # Verify the failed backup was removed
        remaining_ids = [b['id'] for b in self.backup_system.backup_config['backup_history']]
        self.assertNotIn('failed_backup', remaining_ids)
    
    def test_delete_backup_entries_empty_list(self):
        """Test deleting backup entries with empty list."""
        deleted_count = self.backup_system._delete_backup_entries([])
        self.assertEqual(deleted_count, 0)
    
    @patch('time.time')
    def test_cleanup_old_backups(self, mock_time):
        """Test cleanup of old backups."""
        current_time = 1000000
        mock_time.return_value = current_time
        
        # Set backup timestamps to make some old
        self.backup_system.backup_config['backup_history'] = [
            {'id': 'recent', 'timestamp': current_time - (20 * 24 * 3600)},  # 20 days old
            {'id': 'old1', 'timestamp': current_time - (35 * 24 * 3600)},    # 35 days old
            {'id': 'old2', 'timestamp': current_time - (45 * 24 * 3600)}     # 45 days old
        ]
        
        with patch.object(self.backup_system, '_save_backup_config', return_value=True):
            deleted_count = self.backup_system.cleanup_old_backups(30)
        
        self.assertEqual(deleted_count, 2)  # Should delete 2 old backups
        
        # Verify only recent backup remains
        remaining_ids = [b['id'] for b in self.backup_system.backup_config['backup_history']]
        self.assertEqual(len(remaining_ids), 1)
        self.assertIn('recent', remaining_ids)
    
    def _get_failed_backups(self):
        """Helper method to get failed backups."""
        return [b for b in self.backup_system.backup_config['backup_history'] if b.get('status') == 'failed']


class TestSmartBackupSystemErrorHandling(unittest.TestCase):
    """Test cases for SmartBackupSystem error handling."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {'advanced_features': {}}
        self.mock_git_wrapper.print_error = Mock()
        self.mock_git_wrapper.print_success = Mock()
        
        self.backup_system = SmartBackupSystem(self.mock_git_wrapper)
    
    def test_backup_with_exception(self):
        """Test backup handling when exception occurs."""
        # Mock an exception during backup
        with patch.object(self.backup_system, '_backup_branch_to_remote', side_effect=Exception("Test error")):
            result = self.backup_system.create_backup(['main'], ['remote1'])
        
        self.assertFalse(result)
        self.assertFalse(self.backup_system.backup_in_progress)
    
    def test_backup_branch_to_remote_exception(self):
        """Test branch backup with exception handling."""
        remote_config = {
            'url': 'https://github.com/user/repo.git',
            'enabled': True
        }
        
        with patch.object(self.backup_system, '_branch_exists', side_effect=Exception("Test error")):
            result = self.backup_system._backup_branch_to_remote('main', 'test_remote', remote_config)
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_error.assert_called()
    
    def test_restore_with_exception(self):
        """Test restore handling when exception occurs."""
        self.backup_system.backup_config = {
            'remotes': {
                'test_remote': {
                    'url': 'https://github.com/user/repo.git',
                    'enabled': True
                }
            }
        }
        
        with patch.object(self.backup_system, '_has_local_changes', side_effect=Exception("Test error")):
            result = self.backup_system.restore_from_backup('test_backup', 'main', 'test_remote')
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_error.assert_called()
    
    def test_verify_backup_with_exception(self):
        """Test backup verification with exception handling."""
        test_backup = {
            'id': 'test_backup',
            'branches': ['main'],
            'remotes': ['test_remote']
        }
        
        # Mock exception during verification
        with patch.object(self.backup_system, '_test_specific_remote', side_effect=Exception("Test error")):
            result = self.backup_system._verify_single_backup(test_backup)
        
        self.assertFalse(result['success'])
        self.assertTrue(any('Verification exception' in error for error in result['errors']))
    
    def test_backup_timeout_handling(self):
        """Test backup timeout handling."""
        remote_config = {
            'url': 'https://github.com/user/repo.git',
            'enabled': True
        }
        
        # Mock timeout during push
        def mock_run_command(cmd, **kwargs):
            if 'push' in cmd:
                raise TimeoutError("Backup operation timed out")
            return True
        
        with patch.object(self.backup_system, '_branch_exists', return_value=True), \
             patch.object(self.backup_system, 'run_git_command', side_effect=mock_run_command):
            
            result = self.backup_system._backup_branch_to_remote('main', 'test_remote', remote_config)
        
        self.assertFalse(result)
    
    def test_save_config_failure_handling(self):
        """Test handling of configuration save failures."""
        with patch.object(self.backup_system, '_save_backup_config', return_value=False):
            # This should not raise an exception, just return False
            result = self.backup_system._save_backup_config()
            self.assertFalse(result)
    
    def test_invalid_git_url_handling(self):
        """Test handling of invalid Git URLs."""
        invalid_urls = [
            '',
            'not-a-url',
            'ftp://invalid.com',
            None
        ]
        
        for url in invalid_urls:
            result = self.backup_system._validate_git_url(url)
            self.assertFalse(result, f"URL should be invalid: {url}")
    
    def test_missing_remote_config_handling(self):
        """Test handling of missing remote configuration."""
        # Try to backup to non-existent remote
        result = self.backup_system.create_backup(['main'], ['nonexistent_remote'])
        
        self.assertFalse(result)
    
    def test_network_error_handling(self):
        """Test handling of network errors during remote operations."""
        remote_config = {
            'url': 'https://invalid-domain-that-does-not-exist.com/repo.git',
            'enabled': True
        }
        
        # Mock network error
        with patch.object(self.backup_system, 'run_git_command', return_value=False):
            result = self.backup_system._test_specific_remote('test_remote')
        
        self.assertFalse(result)


class TestSmartBackupSystemIntegrity(unittest.TestCase):
    """Test cases for SmartBackupSystem integrity verification."""
    
    def setUp(self):
        """Set up test environment."""
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {
            'advanced_features': {
                'smartbackup': {'verify_backups': True}
            }
        }
        
        self.backup_system = SmartBackupSystem(self.mock_git_wrapper)
        self.backup_system.backup_config = {
            'remotes': {
                'test_remote': {
                    'url': 'https://github.com/user/repo.git',
                    'enabled': True
                }
            }
        }
    
    def test_verify_single_backup_success(self):
        """Test successful backup verification."""
        test_backup = {
            'id': 'test_backup_123',
            'branches': ['main'],
            'remotes': ['test_remote'],
            'results': {
                'test_remote': {
                    'main': True
                }
            },
            'errors': []
        }
        
        with patch.object(self.backup_system, '_test_specific_remote', return_value=True):
            result = self.backup_system._verify_single_backup(test_backup)
        
        self.assertTrue(result['success'])
        self.assertEqual(len(result['errors']), 0)
    
    def test_verify_single_backup_missing_id(self):
        """Test backup verification with missing ID."""
        test_backup = {
            'branches': ['main'],
            'remotes': ['test_remote']
        }
        
        result = self.backup_system._verify_single_backup(test_backup)
        
        self.assertFalse(result['success'])
        self.assertTrue(any('Missing or invalid backup ID' in error for error in result['errors']))
    
    def test_verify_single_backup_no_branches(self):
        """Test backup verification with no branches."""
        test_backup = {
            'id': 'test_backup',
            'branches': [],
            'remotes': ['test_remote']
        }
        
        result = self.backup_system._verify_single_backup(test_backup)
        
        self.assertFalse(result['success'])
        self.assertTrue(any('No branches in backup' in error for error in result['errors']))
    
    def test_verify_single_backup_no_remotes(self):
        """Test backup verification with no remotes."""
        test_backup = {
            'id': 'test_backup',
            'branches': ['main'],
            'remotes': []
        }
        
        result = self.backup_system._verify_single_backup(test_backup)
        
        self.assertFalse(result['success'])
        self.assertTrue(any('No remotes in backup' in error for error in result['errors']))
    
    def test_verify_single_backup_remote_not_found(self):
        """Test backup verification with missing remote configuration."""
        test_backup = {
            'id': 'test_backup',
            'branches': ['main'],
            'remotes': ['nonexistent_remote']
        }
        
        result = self.backup_system._verify_single_backup(test_backup)
        
        self.assertFalse(result['success'])
        self.assertTrue(any('Remote \'nonexistent_remote\' configuration not found' in error for error in result['errors']))
    
    def test_verify_single_backup_remote_disabled(self):
        """Test backup verification with disabled remote."""
        # Add disabled remote
        self.backup_system.backup_config['remotes']['disabled_remote'] = {
            'url': 'https://github.com/user/repo.git',
            'enabled': False
        }
        
        test_backup = {
            'id': 'test_backup',
            'branches': ['main'],
            'remotes': ['disabled_remote']
        }
        
        result = self.backup_system._verify_single_backup(test_backup)
        
        self.assertTrue(result['success'])  # Should still succeed but with warning
        self.assertTrue(any('Remote \'disabled_remote\' is disabled' in warning for warning in result['warnings']))
    
    def test_verify_single_backup_connection_failed(self):
        """Test backup verification with failed remote connection."""
        test_backup = {
            'id': 'test_backup',
            'branches': ['main'],
            'remotes': ['test_remote']
        }
        
        with patch.object(self.backup_system, '_test_specific_remote', return_value=False):
            result = self.backup_system._verify_single_backup(test_backup)
        
        self.assertFalse(result['success'])
        self.assertTrue(any('Cannot connect to remote \'test_remote\'' in error for error in result['errors']))
    
    def test_verify_single_backup_with_backup_errors(self):
        """Test backup verification with backup errors."""
        test_backup = {
            'id': 'test_backup',
            'branches': ['main'],
            'remotes': ['test_remote'],
            'errors': ['Failed to backup branch X', 'Network timeout']
        }
        
        with patch.object(self.backup_system, '_test_specific_remote', return_value=True):
            result = self.backup_system._verify_single_backup(test_backup)
        
        self.assertTrue(result['success'])  # Should succeed but with warnings
        self.assertEqual(len(result['warnings']), 2)
        self.assertTrue(any('Backup error: Failed to backup branch X' in warning for warning in result['warnings']))
    
    def test_verify_single_backup_with_failed_results(self):
        """Test backup verification with failed backup results."""
        test_backup = {
            'id': 'test_backup',
            'branches': ['main', 'develop'],
            'remotes': ['test_remote'],
            'results': {
                'test_remote': {
                    'main': True,
                    'develop': False  # This branch failed
                }
            }
        }
        
        with patch.object(self.backup_system, '_test_specific_remote', return_value=True):
            result = self.backup_system._verify_single_backup(test_backup)
        
        self.assertTrue(result['success'])  # Should succeed but with warnings
        self.assertTrue(any('Branch \'develop\' failed to backup to \'test_remote\'' in warning for warning in result['warnings']))