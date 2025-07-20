#!/usr/bin/env python3
"""
Unit tests for interactive configuration menu functionality.

Tests the interactive configuration menus including:
- Basic configuration menu
- Advanced features configuration
- Feature-specific configuration menus
- Import/export functionality
- Reset configuration options
"""

import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the main class
from git_wrapper import InteractiveGitWrapper


class TestInteractiveConfiguration(unittest.TestCase):
    """Test cases for interactive configuration menu functionality."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / 'test_config.json'
        
        # Mock the config file path
        with patch.object(Path, 'home', return_value=Path(self.temp_dir)):
            self.wrapper = InteractiveGitWrapper()
            self.wrapper.config_file = self.config_file
    
    def tearDown(self):
        """Clean up after each test."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_feature_config_options(self):
        """Test generation of feature configuration options."""
        feature_config = {
            'auto_name_stashes': True,
            'max_stashes': 50,
            'default_template': 'conventional',
            'backup_remotes': ['origin', 'backup']
        }
        
        options = self.wrapper._get_feature_config_options('stash_management', feature_config)
        
        # Check that appropriate options are generated
        self.assertIn('Disable Auto Name Stashes', options)
        self.assertIn('Set Max Stashes', options)
        self.assertIn('Change Default Template', options)
        self.assertIn('Modify Backup Remotes', options)
    
    @patch('builtins.input', side_effect=['75'])
    def test_get_numeric_input_valid(self, mock_input):
        """Test numeric input with valid value."""
        result = self.wrapper._get_numeric_input('max_stashes', 50, 'stash_management')
        self.assertEqual(result, 75)
    
    @patch('builtins.input', side_effect=['invalid'])
    def test_get_numeric_input_invalid(self, mock_input):
        """Test numeric input with invalid value."""
        result = self.wrapper._get_numeric_input('max_stashes', 50, 'stash_management')
        self.assertIsNone(result)
    
    @patch('builtins.input', side_effect=['-5'])
    def test_get_numeric_input_out_of_range(self, mock_input):
        """Test numeric input with out-of-range value."""
        result = self.wrapper._get_numeric_input('max_stashes', 50, 'stash_management')
        self.assertIsNone(result)
    
    @patch('builtins.input', side_effect=['new_item'])
    def test_handle_list_config_add_item(self, mock_input):
        """Test adding item to list configuration."""
        current_list = ['existing_item']
        
        with patch.object(self.wrapper, 'clear_screen'):
            with patch.object(self.wrapper, 'get_choice', side_effect=['Add Item', 'Done']):
                self.wrapper._handle_list_config('backup_system', 'backup_remotes', current_list, 'Backup Remotes')
        
        self.assertIn('new_item', current_list)
        self.assertEqual(len(current_list), 2)
    
    def test_handle_list_config_remove_item(self):
        """Test removing item from list configuration."""
        current_list = ['item1', 'item2']
        
        with patch.object(self.wrapper, 'clear_screen'):
            with patch.object(self.wrapper, 'get_choice', side_effect=['Remove Item', 'item1', 'Done']):
                self.wrapper._handle_list_config('backup_system', 'backup_remotes', current_list, 'Backup Remotes')
        
        self.assertNotIn('item1', current_list)
        self.assertEqual(len(current_list), 1)
    
    def test_handle_list_config_clear_all(self):
        """Test clearing all items from list configuration."""
        current_list = ['item1', 'item2', 'item3']
        
        with patch.object(self.wrapper, 'clear_screen'):
            with patch.object(self.wrapper, 'get_choice', side_effect=['Clear All', 'Done']):
                with patch.object(self.wrapper, 'confirm', return_value=True):
                    self.wrapper._handle_list_config('backup_system', 'backup_remotes', current_list, 'Backup Remotes')
        
        self.assertEqual(len(current_list), 0)
    
    def test_handle_feature_config_choice_boolean(self):
        """Test handling boolean configuration choice."""
        feature_config = {'auto_name_stashes': True}
        
        with patch.object(self.wrapper, 'set_feature_config', return_value=True) as mock_set:
            self.wrapper._handle_feature_config_choice('stash_management', 'Disable Auto Name Stashes', feature_config)
            mock_set.assert_called_once_with('stash_management', 'auto_name_stashes', False)
    
    @patch('builtins.input', side_effect=['100'])
    def test_handle_feature_config_choice_numeric(self, mock_input):
        """Test handling numeric configuration choice."""
        feature_config = {'max_stashes': 50}
        
        with patch.object(self.wrapper, 'set_feature_config', return_value=True) as mock_set:
            self.wrapper._handle_feature_config_choice('stash_management', 'Set Max Stashes', feature_config)
            mock_set.assert_called_once_with('stash_management', 'max_stashes', 100)
    
    @patch('builtins.input', side_effect=['new_template'])
    def test_handle_feature_config_choice_string(self, mock_input):
        """Test handling string configuration choice."""
        feature_config = {'default_template': 'conventional'}
        
        with patch.object(self.wrapper, 'set_feature_config', return_value=True) as mock_set:
            self.wrapper._handle_feature_config_choice('commit_templates', 'Change Default Template', feature_config)
            mock_set.assert_called_once_with('commit_templates', 'default_template', 'new_template')
    
    def test_handle_feature_config_choice_list(self):
        """Test handling list configuration choice."""
        feature_config = {'backup_remotes': ['origin']}
        
        with patch.object(self.wrapper, '_handle_list_config') as mock_handle_list:
            self.wrapper._handle_feature_config_choice('backup_system', 'Modify Backup Remotes', feature_config)
            mock_handle_list.assert_called_once()
    
    @patch('builtins.input')
    def test_interactive_all_features_overview(self, mock_input):
        """Test the all features overview display."""
        with patch.object(self.wrapper, 'clear_screen'):
            self.wrapper.interactive_all_features_overview()
        
        # Should not raise any exceptions
        self.assertTrue(True)
    
    def test_feature_config_validation_integration(self):
        """Test integration of feature configuration with validation."""
        # Test setting valid configuration
        success = self.wrapper.set_feature_config('stash_management', 'max_stashes', 75)
        self.assertTrue(success)
        
        # Verify the value was set
        value = self.wrapper.get_feature_config('stash_management', 'max_stashes')
        self.assertEqual(value, 75)
        
        # Test setting invalid configuration
        success = self.wrapper.set_feature_config('stash_management', 'max_stashes', -1)
        self.assertFalse(success)
        
        # Verify the value wasn't changed
        value = self.wrapper.get_feature_config('stash_management', 'max_stashes')
        self.assertEqual(value, 75)  # Should still be the previous valid value
    
    def test_feature_config_options_generation(self):
        """Test that feature configuration options are generated correctly for all feature types."""
        test_configs = {
            'stash_management': {
                'auto_name_stashes': True,
                'max_stashes': 50,
                'show_preview_lines': 10
            },
            'commit_templates': {
                'auto_suggest': False,
                'default_template': 'conventional',
                'template_categories': ['feat', 'fix']
            },
            'backup_system': {
                'compress_backups': True,
                'retention_days': 90,
                'backup_remotes': ['origin', 'backup']
            }
        }
        
        for feature_name, config in test_configs.items():
            options = self.wrapper._get_feature_config_options(feature_name, config)
            
            # Should have options for each configuration item
            self.assertEqual(len(options), len(config))
            
            # Check that boolean options have Enable/Disable
            for key, value in config.items():
                if isinstance(value, bool):
                    action = "Disable" if value else "Enable"
                    expected_option = f"{action} {key.replace('_', ' ').title()}"
                    self.assertIn(expected_option, options)
    
    def test_nested_config_menu_navigation(self):
        """Test that nested configuration menu structure works correctly."""
        # This is more of a structural test to ensure methods exist and are callable
        
        # Test that all menu methods exist
        self.assertTrue(hasattr(self.wrapper, 'interactive_config_menu'))
        self.assertTrue(hasattr(self.wrapper, 'interactive_basic_config_menu'))
        self.assertTrue(hasattr(self.wrapper, 'interactive_advanced_features_menu'))
        self.assertTrue(hasattr(self.wrapper, 'interactive_feature_config_menu'))
        self.assertTrue(hasattr(self.wrapper, 'interactive_import_export_menu'))
        self.assertTrue(hasattr(self.wrapper, 'interactive_reset_config_menu'))
        
        # Test that helper methods exist
        self.assertTrue(hasattr(self.wrapper, '_get_feature_config_options'))
        self.assertTrue(hasattr(self.wrapper, '_handle_feature_config_choice'))
        self.assertTrue(hasattr(self.wrapper, '_get_numeric_input'))
        self.assertTrue(hasattr(self.wrapper, '_handle_list_config'))
    
    def test_configuration_persistence_across_menu_operations(self):
        """Test that configuration changes persist across menu operations."""
        # Set initial configuration
        self.wrapper.set_feature_config('stash_management', 'max_stashes', 100)
        
        # Simulate saving and reloading
        self.wrapper.save_config()
        
        # Create new wrapper instance to test persistence
        with patch.object(Path, 'home', return_value=Path(self.temp_dir)):
            new_wrapper = InteractiveGitWrapper()
            new_wrapper.config_file = self.config_file
            new_wrapper.load_config()
        
        # Check that configuration persisted
        value = new_wrapper.get_feature_config('stash_management', 'max_stashes')
        self.assertEqual(value, 100)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)