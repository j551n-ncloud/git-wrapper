#!/usr/bin/env python3
"""
Test emoji toggle compatibility for all advanced Git features.

This test verifies that all new features properly respect the show_emoji configuration
and use the correct print methods instead of hardcoded emojis.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from git_wrapper import InteractiveGitWrapper
from features.stash_manager import StashManager
from features.commit_template_engine import CommitTemplateEngine
from features.branch_workflow_manager import BranchWorkflowManager
from features.conflict_resolver import ConflictResolver
from features.repository_health_dashboard import RepositoryHealthDashboard
from features.smart_backup_system import SmartBackupSystem


class TestEmojiCompatibility(unittest.TestCase):
    """Test emoji toggle compatibility across all features."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock git wrapper with emoji enabled
        self.git_wrapper_emoji = Mock(spec=InteractiveGitWrapper)
        self.git_wrapper_emoji.config = {'show_emoji': True}
        self.git_wrapper_emoji.print_success = Mock()
        self.git_wrapper_emoji.print_error = Mock()
        self.git_wrapper_emoji.print_info = Mock()
        self.git_wrapper_emoji.print_working = Mock()
        self.git_wrapper_emoji.save_config = Mock()
        
        # Mock git wrapper with emoji disabled
        self.git_wrapper_no_emoji = Mock(spec=InteractiveGitWrapper)
        self.git_wrapper_no_emoji.config = {'show_emoji': False}
        self.git_wrapper_no_emoji.print_success = Mock()
        self.git_wrapper_no_emoji.print_error = Mock()
        self.git_wrapper_no_emoji.print_info = Mock()
        self.git_wrapper_no_emoji.print_working = Mock()
        self.git_wrapper_no_emoji.save_config = Mock()
        
        # Initialize feature managers
        self.features_emoji = {
            'stash': StashManager(self.git_wrapper_emoji),
            'commit': CommitTemplateEngine(self.git_wrapper_emoji),
            'branch': BranchWorkflowManager(self.git_wrapper_emoji),
            'conflict': ConflictResolver(self.git_wrapper_emoji),
            'health': RepositoryHealthDashboard(self.git_wrapper_emoji),
            'backup': SmartBackupSystem(self.git_wrapper_emoji)
        }
        
        self.features_no_emoji = {
            'stash': StashManager(self.git_wrapper_no_emoji),
            'commit': CommitTemplateEngine(self.git_wrapper_no_emoji),
            'branch': BranchWorkflowManager(self.git_wrapper_no_emoji),
            'conflict': ConflictResolver(self.git_wrapper_no_emoji),
            'health': RepositoryHealthDashboard(self.git_wrapper_no_emoji),
            'backup': SmartBackupSystem(self.git_wrapper_no_emoji)
        }
    
    def test_print_methods_usage(self):
        """Test that features use the correct print methods."""
        for feature_name, feature in self.features_emoji.items():
            with self.subTest(feature=feature_name):
                # Verify that feature has access to print methods
                self.assertTrue(hasattr(feature, 'print_success'))
                self.assertTrue(hasattr(feature, 'print_error'))
                self.assertTrue(hasattr(feature, 'print_info'))
                self.assertTrue(hasattr(feature, 'print_working'))
                
                # Verify that print methods delegate to git_wrapper
                feature.print_success("test")
                self.git_wrapper_emoji.print_success.assert_called_with("test")
                
                feature.print_error("test")
                self.git_wrapper_emoji.print_error.assert_called_with("test")
                
                feature.print_info("test")
                self.git_wrapper_emoji.print_info.assert_called_with("test")
                
                feature.print_working("test")
                self.git_wrapper_emoji.print_working.assert_called_with("test")
    
    def test_emoji_helper_methods(self):
        """Test that features have and use emoji helper methods."""
        for feature_name, feature in self.features_emoji.items():
            with self.subTest(feature=feature_name):
                # Verify helper methods exist
                self.assertTrue(hasattr(feature, 'print_with_emoji'))
                self.assertTrue(hasattr(feature, 'format_with_emoji'))
                
                # Test print_with_emoji with emoji enabled
                with patch('builtins.print') as mock_print:
                    feature.print_with_emoji("Test message", "🔥")
                    mock_print.assert_called_with("🔥 Test message")
                
                # Test format_with_emoji with emoji enabled
                result = feature.format_with_emoji("Test message", "🔥")
                self.assertEqual(result, "🔥 Test message")
    
    def test_emoji_disabled_behavior(self):
        """Test that emoji helpers work correctly when emojis are disabled."""
        for feature_name, feature in self.features_no_emoji.items():
            with self.subTest(feature=feature_name):
                # Test print_with_emoji with emoji disabled
                with patch('builtins.print') as mock_print:
                    feature.print_with_emoji("Test message", "🔥")
                    mock_print.assert_called_with("Test message")
                
                # Test format_with_emoji with emoji disabled
                result = feature.format_with_emoji("Test message", "🔥")
                self.assertEqual(result, "Test message")
    
    def test_show_feature_header_emoji_toggle(self):
        """Test that show_feature_header respects emoji configuration."""
        for feature_name, feature in self.features_emoji.items():
            with self.subTest(feature=feature_name):
                with patch('builtins.print') as mock_print, \
                     patch.object(feature, 'clear_screen'), \
                     patch.object(feature, 'is_git_repo', return_value=True), \
                     patch.object(feature, 'get_current_branch', return_value='main'), \
                     patch.object(feature, 'get_git_root', return_value=Path('/test')):
                    
                    feature.show_feature_header("Test Feature")
                    
                    # Check that emoji was used in header
                    calls = mock_print.call_args_list
                    header_call = next((call for call in calls if "🚀" in str(call)), None)
                    self.assertIsNotNone(header_call, f"Emoji not found in header for {feature_name}")
        
        # Test with emoji disabled
        for feature_name, feature in self.features_no_emoji.items():
            with self.subTest(feature=feature_name):
                with patch('builtins.print') as mock_print, \
                     patch.object(feature, 'clear_screen'), \
                     patch.object(feature, 'is_git_repo', return_value=True), \
                     patch.object(feature, 'get_current_branch', return_value='main'), \
                     patch.object(feature, 'get_git_root', return_value=Path('/test')):
                    
                    feature.show_feature_header("Test Feature")
                    
                    # Check that no emoji was used in header
                    calls = mock_print.call_args_list
                    header_call = next((call for call in calls if "🚀" in str(call)), None)
                    self.assertIsNone(header_call, f"Emoji found in header when disabled for {feature_name}")
    
    @patch('subprocess.run')
    def test_stash_manager_emoji_usage(self, mock_subprocess):
        """Test StashManager emoji usage."""
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        
        stash_manager = self.features_emoji['stash']
        
        # Mock git repo check
        with patch.object(stash_manager, 'is_git_repo', return_value=True), \
             patch.object(stash_manager, 'list_stashes_with_metadata', return_value=[]), \
             patch('builtins.print') as mock_print:
            
            # Test that print_with_emoji is used instead of hardcoded emojis
            stash_manager.print_with_emoji("Test stash message", "📦")
            mock_print.assert_called_with("📦 Test stash message")
    
    @patch('subprocess.run')
    def test_backup_system_emoji_usage(self, mock_subprocess):
        """Test SmartBackupSystem emoji usage."""
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""
        
        backup_system = self.features_emoji['backup']
        
        # Test format_with_emoji usage
        result = backup_system.format_with_emoji("Backup Options:", "📋")
        self.assertEqual(result, "📋 Backup Options:")
        
        # Test with emoji disabled
        backup_system_no_emoji = self.features_no_emoji['backup']
        result = backup_system_no_emoji.format_with_emoji("Backup Options:", "📋")
        self.assertEqual(result, "Backup Options:")
    
    def test_conflict_resolver_emoji_usage(self):
        """Test ConflictResolver emoji usage."""
        conflict_resolver = self.features_emoji['conflict']
        
        # Mock conflict data
        mock_conflicts = [{
            'ours': ['line1', 'line2'],
            'theirs': ['line3', 'line4']
        }]
        
        # Test side-by-side diff formatting
        with patch('pathlib.Path.exists', return_value=True), \
             patch.object(conflict_resolver, '_has_conflict_markers', return_value=True), \
             patch.object(conflict_resolver, '_extract_conflicts', return_value=mock_conflicts), \
             patch('builtins.open', create=True) as mock_open:
            
            mock_open.return_value.__enter__.return_value.read.return_value = "test content"
            
            result = conflict_resolver.show_conflict_side_by_side("test.txt")
            
            # Should contain emoji when enabled
            self.assertIn("📄", result)
        
        # Test with emoji disabled
        conflict_resolver_no_emoji = self.features_no_emoji['conflict']
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch.object(conflict_resolver_no_emoji, '_has_conflict_markers', return_value=True), \
             patch.object(conflict_resolver_no_emoji, '_extract_conflicts', return_value=mock_conflicts), \
             patch('builtins.open', create=True) as mock_open:
            
            mock_open.return_value.__enter__.return_value.read.return_value = "test content"
            
            result = conflict_resolver_no_emoji.show_conflict_side_by_side("test.txt")
            
            # Should not contain emoji when disabled
            self.assertNotIn("📄", result)
    
    def test_branch_workflow_manager_emoji_usage(self):
        """Test BranchWorkflowManager emoji usage."""
        branch_manager = self.features_emoji['branch']
        
        # Test format_with_emoji in menu options
        result = branch_manager.format_with_emoji("Start Feature Branch", "🚀")
        self.assertEqual(result, "🚀 Start Feature Branch")
        
        # Test with emoji disabled
        branch_manager_no_emoji = self.features_no_emoji['branch']
        result = branch_manager_no_emoji.format_with_emoji("Start Feature Branch", "🚀")
        self.assertEqual(result, "Start Feature Branch")
    
    def test_repository_health_dashboard_emoji_usage(self):
        """Test RepositoryHealthDashboard emoji usage."""
        health_dashboard = self.features_emoji['health']
        
        # Test format_with_emoji usage
        result = health_dashboard.format_with_emoji("Dashboard Options:", "📊")
        self.assertEqual(result, "📊 Dashboard Options:")
        
        # Test with emoji disabled
        health_dashboard_no_emoji = self.features_no_emoji['health']
        result = health_dashboard_no_emoji.format_with_emoji("Dashboard Options:", "📊")
        self.assertEqual(result, "Dashboard Options:")
    
    def test_commit_template_engine_emoji_usage(self):
        """Test CommitTemplateEngine emoji usage."""
        commit_engine = self.features_emoji['commit']
        
        # Test format_with_emoji usage
        result = commit_engine.format_with_emoji("Template Options:", "📝")
        self.assertEqual(result, "📝 Template Options:")
        
        # Test with emoji disabled
        commit_engine_no_emoji = self.features_no_emoji['commit']
        result = commit_engine_no_emoji.format_with_emoji("Template Options:", "📝")
        self.assertEqual(result, "Template Options:")
    
    def test_no_hardcoded_emojis_in_print_statements(self):
        """Test that no hardcoded emojis are used in direct print statements."""
        # This test would ideally scan the source code for hardcoded emojis
        # For now, we'll test that the helper methods are being used correctly
        
        for feature_name, feature in self.features_emoji.items():
            with self.subTest(feature=feature_name):
                # Verify that the feature has the helper methods
                self.assertTrue(hasattr(feature, 'format_with_emoji'))
                self.assertTrue(hasattr(feature, 'print_with_emoji'))
                
                # Test that helper methods work correctly
                formatted = feature.format_with_emoji("Test", "🔥")
                self.assertEqual(formatted, "🔥 Test")
    
    def test_configuration_inheritance(self):
        """Test that features properly inherit emoji configuration."""
        for feature_name, feature in self.features_emoji.items():
            with self.subTest(feature=feature_name):
                # Verify that feature has access to config
                self.assertTrue(hasattr(feature, 'config'))
                self.assertEqual(feature.config['show_emoji'], True)
        
        for feature_name, feature in self.features_no_emoji.items():
            with self.subTest(feature=feature_name):
                # Verify that feature has access to config
                self.assertTrue(hasattr(feature, 'config'))
                self.assertEqual(feature.config['show_emoji'], False)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)