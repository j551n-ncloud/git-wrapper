#!/usr/bin/env python3
"""
Unit tests for menu integration and navigation
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from git_wrapper import InteractiveGitWrapper


class TestMenuIntegration(unittest.TestCase):
    """Test menu integration and navigation functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.git_wrapper = InteractiveGitWrapper()
        # Mock the config file to avoid file operations
        self.git_wrapper.config_file = Mock()
        
    @patch('git_wrapper.subprocess.run')
    def test_has_advanced_features_when_available(self, mock_run):
        """Test that has_advanced_features returns True when features are available"""
        # Mock git availability check
        mock_run.return_value = Mock(returncode=0)
        
        # Reset initialization state
        self.git_wrapper._features_initialized = False
        self.git_wrapper._feature_managers = {}
        
        # Mock the feature classes directly in the _initialize_features method
        mock_stash = Mock()
        mock_templates = Mock()
        mock_workflows = Mock()
        mock_conflicts = Mock()
        mock_health = Mock()
        mock_backup = Mock()
        
        # Mock the imports within the _initialize_features method
        def mock_initialize_features():
            self.git_wrapper._feature_managers = {
                'stash': mock_stash,
                'templates': mock_templates,
                'workflows': mock_workflows,
                'conflicts': mock_conflicts,
                'health': mock_health,
                'backup': mock_backup
            }
            self.git_wrapper._features_initialized = True
        
        with patch.object(self.git_wrapper, '_initialize_features', side_effect=mock_initialize_features):
            result = self.git_wrapper.has_advanced_features()
            self.assertTrue(result)
            self.assertTrue(self.git_wrapper._features_initialized)
            self.assertEqual(len(self.git_wrapper._feature_managers), 6)
    
    @patch('git_wrapper.subprocess.run')
    def test_has_advanced_features_when_not_available(self, mock_run):
        """Test that has_advanced_features handles missing features gracefully"""
        # Mock git availability check
        mock_run.return_value = Mock(returncode=0)
        
        # Reset initialization state
        self.git_wrapper._features_initialized = False
        self.git_wrapper._feature_managers = {}
        
        # Mock import error in _initialize_features
        def mock_initialize_features_with_error():
            self.git_wrapper._feature_managers = {}
            self.git_wrapper._features_initialized = True
        
        with patch.object(self.git_wrapper, '_initialize_features', side_effect=mock_initialize_features_with_error):
            result = self.git_wrapper.has_advanced_features()
            self.assertFalse(result)
            self.assertTrue(self.git_wrapper._features_initialized)
            self.assertEqual(len(self.git_wrapper._feature_managers), 0)
    
    def test_get_feature_manager_returns_correct_manager(self):
        """Test that get_feature_manager returns the correct feature manager"""
        # Mock feature managers
        mock_stash = Mock()
        self.git_wrapper._feature_managers = {'stash': mock_stash}
        self.git_wrapper._features_initialized = True
        
        result = self.git_wrapper.get_feature_manager('stash')
        self.assertEqual(result, mock_stash)
    
    def test_get_feature_manager_returns_none_for_unknown_feature(self):
        """Test that get_feature_manager returns None for unknown features"""
        self.git_wrapper._feature_managers = {}
        self.git_wrapper._features_initialized = True
        
        result = self.git_wrapper.get_feature_manager('unknown')
        self.assertIsNone(result)
    
    @patch('git_wrapper.InteractiveGitWrapper.is_git_repo')
    def test_handle_feature_menu_requires_git_repo(self, mock_is_git_repo):
        """Test that feature menus require a git repository"""
        mock_is_git_repo.return_value = False
        
        with patch('builtins.input'), \
             patch('git_wrapper.InteractiveGitWrapper.print_error') as mock_print_error:
            
            self.git_wrapper._handle_feature_menu('stash')
            mock_print_error.assert_called_with("Advanced features require a Git repository!")
    
    @patch('git_wrapper.InteractiveGitWrapper.is_git_repo')
    def test_handle_feature_menu_calls_interactive_menu(self, mock_is_git_repo):
        """Test that feature menu calls the feature's interactive menu"""
        mock_is_git_repo.return_value = True
        
        # Mock feature manager
        mock_feature = Mock()
        self.git_wrapper._feature_managers = {'stash': mock_feature}
        self.git_wrapper._features_initialized = True
        
        self.git_wrapper._handle_feature_menu('stash')
        mock_feature.interactive_menu.assert_called_once()
    
    @patch('git_wrapper.InteractiveGitWrapper.is_git_repo')
    def test_handle_feature_menu_handles_unavailable_feature(self, mock_is_git_repo):
        """Test that feature menu handles unavailable features gracefully"""
        mock_is_git_repo.return_value = True
        
        self.git_wrapper._feature_managers = {}
        self.git_wrapper._features_initialized = True
        
        with patch('builtins.input'), \
             patch('git_wrapper.InteractiveGitWrapper.print_error') as mock_print_error:
            
            self.git_wrapper._handle_feature_menu('nonexistent')
            mock_print_error.assert_called_with("Feature 'nonexistent' is not available!")
    
    @patch('git_wrapper.InteractiveGitWrapper.is_git_repo')
    def test_handle_feature_menu_handles_exceptions(self, mock_is_git_repo):
        """Test that feature menu handles exceptions gracefully"""
        mock_is_git_repo.return_value = True
        
        # Mock feature manager that raises an exception
        mock_feature = Mock()
        mock_feature.interactive_menu.side_effect = Exception("Test error")
        self.git_wrapper._feature_managers = {'stash': mock_feature}
        self.git_wrapper._features_initialized = True
        
        with patch('builtins.input'), \
             patch('git_wrapper.InteractiveGitWrapper.print_error') as mock_print_error:
            
            self.git_wrapper._handle_feature_menu('stash')
            mock_print_error.assert_called_with("Error in stash feature: Test error")
    
    def test_menu_choice_handlers_include_all_features(self):
        """Test that handle_menu_choice includes handlers for all advanced features"""
        # Create a mock choice that would match each feature
        test_cases = [
            ("🗂️  Stash Management", 'stash'),
            ("📝 Commit Templates", 'templates'),
            ("🔀 Branch Workflows", 'workflows'),
            ("⚔️  Conflict Resolution", 'conflicts'),
            ("🏥 Repository Health", 'health'),
            ("💾 Smart Backup", 'backup')
        ]
        
        for choice_text, expected_feature in test_cases:
            with patch.object(self.git_wrapper, '_handle_feature_menu') as mock_handle:
                self.git_wrapper.handle_menu_choice(choice_text)
                mock_handle.assert_called_once_with(expected_feature)
    
    def test_menu_choice_handlers_include_basic_operations(self):
        """Test that handle_menu_choice includes handlers for basic operations"""
        test_cases = [
            ("📊 Show Status", 'interactive_status'),
            ("💾 Quick Commit", 'interactive_commit'),
            ("🔄 Sync (Pull & Push)", 'interactive_sync'),
            ("📤 Push Operations", 'interactive_push_menu'),
            ("🌿 Branch Operations", 'interactive_branch_menu'),
            ("📋 View Changes", 'interactive_diff'),
            ("📜 View History", 'interactive_log'),
            ("🔗 Remote Management", 'interactive_remote_menu'),
            ("🎯 Initialize Repository", 'interactive_init'),
            ("📥 Clone Repository", 'interactive_clone'),
            ("⚙️ Configuration", 'interactive_config_menu'),
            ("❓ Help", 'show_help')
        ]
        
        for choice_text, expected_method in test_cases:
            with patch.object(self.git_wrapper, expected_method) as mock_method:
                self.git_wrapper.handle_menu_choice(choice_text)
                mock_method.assert_called_once()


if __name__ == '__main__':
    unittest.main()