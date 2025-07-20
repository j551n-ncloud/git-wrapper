#!/usr/bin/env python3
"""
Unit tests for extended configuration management functionality.

Tests the comprehensive configuration system including:
- Configuration loading and saving
- Feature-specific configuration validation
- Configuration migration
- Import/export functionality
- Default configuration management
"""

import unittest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the main class
from git_wrapper import InteractiveGitWrapper


class TestConfigurationManagement(unittest.TestCase):
    """Test cases for configuration management functionality."""
    
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
    
    def test_default_config_structure(self):
        """Test that default configuration has proper structure."""
        default_config = self.wrapper._get_default_config()
        
        # Test basic structure
        self.assertIn('name', default_config)
        self.assertIn('email', default_config)
        self.assertIn('advanced_features', default_config)
        self.assertIn('config_version', default_config)
        
        # Test advanced features structure
        advanced_features = default_config['advanced_features']
        expected_features = [
            'stash_management', 'commit_templates', 'branch_workflows',
            'conflict_resolution', 'health_dashboard', 'backup_system'
        ]
        
        for feature in expected_features:
            self.assertIn(feature, advanced_features)
            self.assertIsInstance(advanced_features[feature], dict)
    
    def test_config_validation(self):
        """Test configuration validation functionality."""
        # Test valid values
        self.assertTrue(self.wrapper._validate_feature_config_value(
            'stash_management', 'max_stashes', 50))
        self.assertTrue(self.wrapper._validate_feature_config_value(
            'commit_templates', 'auto_suggest', True))
        self.assertTrue(self.wrapper._validate_feature_config_value(
            'branch_workflows', 'default_workflow', 'github_flow'))
        
        # Test invalid values
        self.assertFalse(self.wrapper._validate_feature_config_value(
            'stash_management', 'max_stashes', 0))  # Too low
        self.assertFalse(self.wrapper._validate_feature_config_value(
            'stash_management', 'max_stashes', 300))  # Too high
        self.assertFalse(self.wrapper._validate_feature_config_value(
            'branch_workflows', 'default_workflow', 'invalid_workflow'))
    
    def test_nested_config_access(self):
        """Test nested configuration value access."""
        # Set a nested value
        self.wrapper._set_nested_config_value(
            'advanced_features.stash_management.max_stashes', 75)
        
        # Get the nested value
        value = self.wrapper._get_nested_config_value(
            'advanced_features.stash_management.max_stashes')
        
        self.assertEqual(value, 75)
        
        # Test non-existent path
        value = self.wrapper._get_nested_config_value(
            'advanced_features.nonexistent.setting')
        self.assertIsNone(value)
    
    def test_feature_config_management(self):
        """Test feature-specific configuration management."""
        # Test getting feature config
        stash_config = self.wrapper.get_feature_config('stash_management')
        self.assertIsInstance(stash_config, dict)
        self.assertIn('max_stashes', stash_config)
        
        # Test getting specific key
        max_stashes = self.wrapper.get_feature_config('stash_management', 'max_stashes')
        self.assertIsInstance(max_stashes, int)
        
        # Test setting feature config
        success = self.wrapper.set_feature_config('stash_management', 'max_stashes', 100)
        self.assertTrue(success)
        
        # Verify the value was set
        new_value = self.wrapper.get_feature_config('stash_management', 'max_stashes')
        self.assertEqual(new_value, 100)
        
        # Test setting invalid value
        success = self.wrapper.set_feature_config('stash_management', 'max_stashes', -1)
        self.assertFalse(success)
    
    def test_deep_merge_config(self):
        """Test deep merging of configuration dictionaries."""
        base_config = {
            'level1': {
                'level2': {
                    'existing_key': 'old_value',
                    'keep_key': 'keep_value'
                }
            }
        }
        
        loaded_config = {
            'level1': {
                'level2': {
                    'existing_key': 'new_value',
                    'new_key': 'new_value'
                }
            }
        }
        
        self.wrapper._deep_merge_config(base_config, loaded_config)
        
        # Check that existing key was updated
        self.assertEqual(base_config['level1']['level2']['existing_key'], 'new_value')
        # Check that new key was added
        self.assertEqual(base_config['level1']['level2']['new_key'], 'new_value')
        # Check that existing key was preserved
        self.assertEqual(base_config['level1']['level2']['keep_key'], 'keep_value')
    
    def test_config_migration(self):
        """Test configuration migration from older versions."""
        # Create old version config
        old_config = {
            'name': 'Test User',
            'email': 'test@example.com',
            'config_version': '1.0',
            'advanced_features': {
                'stash_management': {
                    'max_stashes': 25  # Old value
                }
            }
        }
        
        # Save old config
        with open(self.config_file, 'w') as f:
            json.dump(old_config, f)
        
        # Load config (should trigger migration)
        self.wrapper.load_config()
        
        # Check that migration occurred
        self.assertEqual(self.wrapper.config['config_version'], '2.0')
        self.assertEqual(self.wrapper.config['name'], 'Test User')
        self.assertEqual(self.wrapper.config['email'], 'test@example.com')
        
        # Check that old settings were preserved
        self.assertEqual(
            self.wrapper.config['advanced_features']['stash_management']['max_stashes'], 25)
        
        # Check that new settings were added
        self.assertIn('show_preview_lines', 
                     self.wrapper.config['advanced_features']['stash_management'])
    
    @patch('builtins.input', return_value='y')
    def test_config_export_import(self, mock_input):
        """Test configuration export and import functionality."""
        # Modify some configuration
        self.wrapper.set_feature_config('stash_management', 'max_stashes', 75)
        self.wrapper.config['name'] = 'Export Test User'
        
        # Export configuration
        export_path = Path(self.temp_dir) / 'exported_config.json'
        success = self.wrapper.export_config(str(export_path))
        self.assertTrue(success)
        self.assertTrue(export_path.exists())
        
        # Reset configuration
        self.wrapper.config = self.wrapper._get_default_config()
        
        # Import configuration
        success = self.wrapper.import_config(str(export_path))
        self.assertTrue(success)
        
        # Verify imported values
        self.assertEqual(self.wrapper.config['name'], 'Export Test User')
        self.assertEqual(
            self.wrapper.get_feature_config('stash_management', 'max_stashes'), 75)
    
    @patch('builtins.input', return_value='y')
    def test_reset_config_to_defaults(self, mock_input):
        """Test resetting configuration to defaults."""
        # Modify configuration
        self.wrapper.set_feature_config('stash_management', 'max_stashes', 150)
        self.wrapper.config['name'] = 'Modified User'
        
        # Reset specific feature
        success = self.wrapper.reset_config_to_defaults('stash_management')
        self.assertTrue(success)
        
        # Check that feature was reset
        default_max = self.wrapper._get_default_config()['advanced_features']['stash_management']['max_stashes']
        current_max = self.wrapper.get_feature_config('stash_management', 'max_stashes')
        self.assertEqual(current_max, default_max)
        
        # Check that other config wasn't affected
        self.assertEqual(self.wrapper.config['name'], 'Modified User')
        
        # Reset all configuration
        success = self.wrapper.reset_config_to_defaults()
        self.assertTrue(success)
        
        # Check that everything was reset
        default_name = self.wrapper._get_default_config()['name']
        self.assertEqual(self.wrapper.config['name'], default_name)
    
    def test_config_validation_on_load(self):
        """Test that configuration is validated when loaded."""
        # Create config with invalid values
        invalid_config = {
            'name': 'Test User',
            'advanced_features': {
                'stash_management': {
                    'max_stashes': -5,  # Invalid: too low
                    'show_preview_lines': 1000  # Invalid: too high
                }
            }
        }
        
        # Save invalid config
        with open(self.config_file, 'w') as f:
            json.dump(invalid_config, f)
        
        # Load config (should fix invalid values)
        self.wrapper.load_config()
        
        # Check that invalid values were corrected
        max_stashes = self.wrapper.get_feature_config('stash_management', 'max_stashes')
        preview_lines = self.wrapper.get_feature_config('stash_management', 'show_preview_lines')
        
        self.assertGreaterEqual(max_stashes, 1)
        self.assertLessEqual(preview_lines, 50)
    
    def test_config_backup_on_save(self):
        """Test that configuration backup is created when saving."""
        # Create initial config
        self.wrapper.config['name'] = 'Initial User'
        self.wrapper.save_config()
        
        # Modify and save again
        self.wrapper.config['name'] = 'Modified User'
        self.wrapper.save_config()
        
        # Check that backup was created
        backup_file = self.config_file.with_suffix('.json.backup')
        self.assertTrue(backup_file.exists())
        
        # Check backup content
        with open(backup_file, 'r') as f:
            backup_config = json.load(f)
        
        self.assertEqual(backup_config['name'], 'Initial User')
    
    def test_invalid_config_file_handling(self):
        """Test handling of invalid configuration files."""
        # Create invalid JSON file
        with open(self.config_file, 'w') as f:
            f.write('invalid json content {')
        
        # Should load defaults without crashing
        self.wrapper.load_config()
        
        # Should have default configuration
        default_config = self.wrapper._get_default_config()
        self.assertEqual(self.wrapper.config['name'], default_config['name'])
        self.assertEqual(self.wrapper.config['config_version'], default_config['config_version'])


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)