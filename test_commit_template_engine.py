#!/usr/bin/env python3
"""
Unit tests for CommitTemplateEngine

Tests template data structures, storage, validation, and management functionality.
"""

import unittest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the class to test
from features.commit_template_engine import CommitTemplateEngine


class TestCommitTemplateEngine(unittest.TestCase):
    """Test cases for CommitTemplateEngine template data management."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock git wrapper
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {
            'advanced_features': {
                'committemplate': {
                    'default_template': 'conventional',
                    'auto_suggest': True,
                    'validate_conventional': True,
                    'show_template_preview': True,
                    'max_subject_length': 50,
                    'max_body_line_length': 72
                }
            }
        }
        self.mock_git_wrapper.save_config = Mock()
        self.mock_git_wrapper.print_success = Mock()
        self.mock_git_wrapper.print_error = Mock()
        self.mock_git_wrapper.print_info = Mock()
        self.mock_git_wrapper.print_working = Mock()
        
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.temp_templates_file = Path(self.temp_dir) / 'test_templates.json'
        
        # Create CommitTemplateEngine instance
        with patch('features.commit_template_engine.Path.home') as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            self.engine = CommitTemplateEngine(self.mock_git_wrapper)
            self.engine.templates_file = self.temp_templates_file
    
    def tearDown(self):
        """Clean up after each test method."""
        # Remove temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_default_config(self):
        """Test default configuration values."""
        default_config = self.engine._get_default_config()
        
        expected_keys = [
            'default_template', 'auto_suggest', 'validate_conventional',
            'show_template_preview', 'max_subject_length', 'max_body_line_length'
        ]
        
        for key in expected_keys:
            self.assertIn(key, default_config)
        
        self.assertEqual(default_config['default_template'], 'conventional')
        self.assertTrue(default_config['auto_suggest'])
        self.assertTrue(default_config['validate_conventional'])
        self.assertEqual(default_config['max_subject_length'], 50)
        self.assertEqual(default_config['max_body_line_length'], 72)
    
    def test_load_default_templates(self):
        """Test loading of default templates."""
        default_templates = self.engine._load_default_templates()
        
        # Check that all expected template types are present
        expected_types = ['feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore', 'perf', 'ci', 'build', 'revert']
        
        for template_type in expected_types:
            self.assertIn(template_type, default_templates)
        
        # Check structure of a specific template
        feat_template = default_templates['feat']
        required_fields = ['name', 'pattern', 'fields', 'required', 'conventional', 'description', 'examples']
        
        for field in required_fields:
            self.assertIn(field, feat_template)
        
        self.assertEqual(feat_template['name'], 'Feature')
        self.assertTrue(feat_template['conventional'])
        self.assertIn('description', feat_template['required'])
        self.assertIn('scope', feat_template['fields'])
    
    def test_ensure_templates_file_creation(self):
        """Test that templates file is created with default content."""
        # Remove the file if it exists
        if self.temp_templates_file.exists():
            self.temp_templates_file.unlink()
        
        # Create new engine instance to trigger file creation
        with patch('features.commit_template_engine.Path.home') as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            engine = CommitTemplateEngine(self.mock_git_wrapper)
            engine.templates_file = self.temp_templates_file
            engine._ensure_templates_file()  # Explicitly call to ensure file creation
        
        # Check that file was created
        self.assertTrue(self.temp_templates_file.exists())
        
        # Check file content
        with open(self.temp_templates_file, 'r') as f:
            data = json.load(f)
        
        self.assertIn('templates', data)
        self.assertIn('custom_templates', data)
        self.assertIn('created_at', data)
        self.assertIn('version', data)
        
        # Check that default templates are included
        self.assertIn('feat', data['templates'])
        self.assertIn('fix', data['templates'])
    
    def test_load_templates(self):
        """Test loading templates from file."""
        # Create test data
        test_data = {
            'templates': {'test_template': {'name': 'Test'}},
            'custom_templates': {'custom_test': {'name': 'Custom Test'}},
            'version': '1.0'
        }
        
        with open(self.temp_templates_file, 'w') as f:
            json.dump(test_data, f)
        
        loaded_data = self.engine._load_templates()
        
        self.assertEqual(loaded_data['templates']['test_template']['name'], 'Test')
        self.assertEqual(loaded_data['custom_templates']['custom_test']['name'], 'Custom Test')
        self.assertEqual(loaded_data['version'], '1.0')
    
    def test_save_templates(self):
        """Test saving templates to file."""
        test_data = {
            'templates': {'test_template': {'name': 'Test'}},
            'custom_templates': {},
            'version': '1.0'
        }
        
        result = self.engine._save_templates(test_data)
        self.assertTrue(result)
        
        # Verify file was saved
        self.assertTrue(self.temp_templates_file.exists())
        
        # Verify content
        with open(self.temp_templates_file, 'r') as f:
            saved_data = json.load(f)
        
        self.assertEqual(saved_data['templates']['test_template']['name'], 'Test')
        self.assertIn('updated_at', saved_data)
    
    def test_get_all_templates(self):
        """Test getting all templates (default + custom)."""
        # Create test data with both default and custom templates
        test_data = {
            'templates': {'default_template': {'name': 'Default'}},
            'custom_templates': {'custom_template': {'name': 'Custom'}},
            'version': '1.0'
        }
        
        with open(self.temp_templates_file, 'w') as f:
            json.dump(test_data, f)
        
        all_templates = self.engine.get_all_templates()
        
        self.assertIn('default_template', all_templates)
        self.assertIn('custom_template', all_templates)
        self.assertEqual(all_templates['default_template']['name'], 'Default')
        self.assertEqual(all_templates['custom_template']['name'], 'Custom')
    
    def test_get_template(self):
        """Test getting a specific template by key."""
        # Create test data
        test_data = {
            'templates': {'test_template': {'name': 'Test Template', 'pattern': 'test: {description}'}},
            'custom_templates': {},
            'version': '1.0'
        }
        
        with open(self.temp_templates_file, 'w') as f:
            json.dump(test_data, f)
        
        template = self.engine.get_template('test_template')
        self.assertIsNotNone(template)
        self.assertEqual(template['name'], 'Test Template')
        self.assertEqual(template['pattern'], 'test: {description}')
        
        # Test non-existent template
        non_existent = self.engine.get_template('non_existent')
        self.assertIsNone(non_existent)
    
    def test_validate_template_structure(self):
        """Test template structure validation."""
        # Valid template
        valid_template = {
            'name': 'Test Template',
            'pattern': 'test: {description}',
            'fields': ['description'],
            'required': ['description']
        }
        
        errors = self.engine.validate_template_structure(valid_template)
        self.assertEqual(len(errors), 0)
        
        # Invalid template - missing required fields
        invalid_template = {
            'name': 'Test Template'
            # Missing pattern, fields, required
        }
        
        errors = self.engine.validate_template_structure(invalid_template)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('Missing required field' in error for error in errors))
        
        # Invalid template - required field not in pattern
        invalid_pattern_template = {
            'name': 'Test Template',
            'pattern': 'test: {other_field}',
            'fields': ['description', 'other_field'],
            'required': ['description']  # description not in pattern
        }
        
        errors = self.engine.validate_template_structure(invalid_pattern_template)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('not found in pattern' in error for error in errors))
    
    def test_validate_conventional_commit(self):
        """Test conventional commit message validation."""
        # Valid conventional commit
        valid_message = "feat(auth): add OAuth2 login support"
        result = self.engine.validate_conventional_commit(valid_message)
        
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(result['parsed']['type'], 'feat')
        self.assertEqual(result['parsed']['scope'], 'auth')
        self.assertEqual(result['parsed']['description'], 'add OAuth2 login support')
        
        # Invalid conventional commit
        invalid_message = "added new feature"
        result = self.engine.validate_conventional_commit(invalid_message)
        
        self.assertFalse(result['valid'])
        self.assertGreater(len(result['errors']), 0)
        
        # Empty message
        empty_result = self.engine.validate_conventional_commit("")
        self.assertFalse(empty_result['valid'])
        self.assertIn("cannot be empty", empty_result['errors'][0])
        
        # Test warnings for long subject
        long_message = "feat: " + "a" * 60  # Exceeds default 50 char limit
        result = self.engine.validate_conventional_commit(long_message)
        
        self.assertTrue(result['valid'])  # Still valid format
        self.assertGreater(len(result['warnings']), 0)
        self.assertTrue(any('characters' in warning for warning in result['warnings']))
    
    def test_create_custom_template(self):
        """Test creating custom templates."""
        custom_template = {
            'name': 'Custom Feature',
            'pattern': 'custom: {description}\n\n{body}',
            'fields': ['description', 'body'],
            'required': ['description'],
            'conventional': False,
            'description': 'A custom template for testing'
        }
        
        result = self.engine.create_custom_template('custom_feat', custom_template)
        self.assertTrue(result)
        
        # Verify template was saved
        all_templates = self.engine.get_all_templates()
        self.assertIn('custom_feat', all_templates)
        
        saved_template = all_templates['custom_feat']
        self.assertEqual(saved_template['name'], 'Custom Feature')
        self.assertTrue(saved_template['custom'])
        self.assertIn('created_at', saved_template)
        
        # Test invalid template
        invalid_template = {
            'name': 'Invalid Template'
            # Missing required fields
        }
        
        result = self.engine.create_custom_template('invalid', invalid_template)
        self.assertFalse(result)
    
    def test_update_template(self):
        """Test updating existing templates."""
        # First create a custom template
        custom_template = {
            'name': 'Original Name',
            'pattern': 'test: {description}',
            'fields': ['description'],
            'required': ['description']
        }
        
        self.engine.create_custom_template('test_template', custom_template)
        
        # Update the template
        updated_template = {
            'name': 'Updated Name',
            'pattern': 'updated: {description}\n\n{body}',
            'fields': ['description', 'body'],
            'required': ['description']
        }
        
        result = self.engine.update_template('test_template', updated_template)
        self.assertTrue(result)
        
        # Verify update
        template = self.engine.get_template('test_template')
        self.assertEqual(template['name'], 'Updated Name')
        self.assertIn('updated_at', template)
        
        # Test updating non-existent template
        result = self.engine.update_template('non_existent', updated_template)
        self.assertFalse(result)
    
    def test_delete_template(self):
        """Test deleting custom templates."""
        # Create a custom template
        custom_template = {
            'name': 'To Delete',
            'pattern': 'delete: {description}',
            'fields': ['description'],
            'required': ['description']
        }
        
        self.engine.create_custom_template('to_delete', custom_template)
        
        # Verify it exists
        self.assertIsNotNone(self.engine.get_template('to_delete'))
        
        # Delete it
        result = self.engine.delete_template('to_delete')
        self.assertTrue(result)
        
        # Verify it's gone
        self.assertIsNone(self.engine.get_template('to_delete'))
        
        # Test deleting default template (should fail)
        result = self.engine.delete_template('feat')
        self.assertFalse(result)
        
        # Test deleting non-existent template
        result = self.engine.delete_template('non_existent')
        self.assertFalse(result)
    
    def test_reset_to_defaults(self):
        """Test resetting templates to defaults."""
        # Create some custom templates
        custom_template = {
            'name': 'Custom',
            'pattern': 'custom: {description}',
            'fields': ['description'],
            'required': ['description']
        }
        
        self.engine.create_custom_template('custom1', custom_template)
        self.engine.create_custom_template('custom2', custom_template)
        
        # Verify custom templates exist
        all_templates = self.engine.get_all_templates()
        self.assertIn('custom1', all_templates)
        self.assertIn('custom2', all_templates)
        
        # Reset to defaults
        result = self.engine.reset_to_defaults()
        self.assertTrue(result)
        
        # Verify custom templates are gone
        all_templates = self.engine.get_all_templates()
        self.assertNotIn('custom1', all_templates)
        self.assertNotIn('custom2', all_templates)
        
        # Verify default templates still exist
        self.assertIn('feat', all_templates)
        self.assertIn('fix', all_templates)



class TestCommitTemplateEngineApplication(unittest.TestCase):
    """Test cases for CommitTemplateEngine template selection and application."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock git wrapper
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {
            'advanced_features': {
                'committemplate': {
                    'default_template': 'conventional',
                    'auto_suggest': True,
                    'validate_conventional': True,
                    'show_template_preview': True,
                    'max_subject_length': 50,
                    'max_body_line_length': 72
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
        self.mock_git_wrapper.confirm = Mock()
        self.mock_git_wrapper.clear_screen = Mock()
        
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.temp_templates_file = Path(self.temp_dir) / 'test_templates.json'
        
        # Create CommitTemplateEngine instance
        with patch('features.commit_template_engine.Path.home') as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            self.engine = CommitTemplateEngine(self.mock_git_wrapper)
            self.engine.templates_file = self.temp_templates_file
    
    def tearDown(self):
        """Clean up after each test method."""
        # Remove temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_apply_template(self):
        """Test template application with context values."""
        template = {
            'name': 'Feature Template',
            'pattern': 'feat({scope}): {description}\n\n{body}\n\n{footer}',
            'fields': ['scope', 'description', 'body', 'footer'],
            'required': ['description']
        }
        
        context = {
            'scope': 'auth',
            'description': 'add OAuth2 support',
            'body': 'Implement OAuth2 authentication flow',
            'footer': 'Closes #123'
        }
        
        result = self.engine.apply_template(template, context)
        
        expected = 'feat(auth): add OAuth2 support\n\nImplement OAuth2 authentication flow\n\nCloses #123'
        self.assertEqual(result, expected)
    
    def test_apply_template_with_empty_optional_fields(self):
        """Test template application with empty optional fields."""
        template = {
            'name': 'Simple Template',
            'pattern': 'feat({scope}): {description}\n\n{body}',
            'fields': ['scope', 'description', 'body'],
            'required': ['description']
        }
        
        context = {
            'scope': 'api',
            'description': 'add new endpoint',
            'body': ''  # Empty optional field
        }
        
        result = self.engine.apply_template(template, context)
        
        # Should clean up empty lines
        expected = 'feat(api): add new endpoint'
        self.assertEqual(result, expected)
    
    def test_apply_template_minimal(self):
        """Test template application with minimal required fields."""
        template = {
            'name': 'Minimal Template',
            'pattern': '{type}: {description}',
            'fields': ['type', 'description'],
            'required': ['type', 'description']
        }
        
        context = {
            'type': 'fix',
            'description': 'resolve memory leak'
        }
        
        result = self.engine.apply_template(template, context)
        
        expected = 'fix: resolve memory leak'
        self.assertEqual(result, expected)
    
    @patch('tempfile.NamedTemporaryFile')
    @patch('os.unlink')
    def test_create_commit_with_message(self, mock_unlink, mock_tempfile):
        """Test creating a commit with a message."""
        # Mock temporary file
        mock_file = Mock()
        mock_file.name = '/tmp/test_commit_msg.txt'
        mock_tempfile.return_value.__enter__.return_value = mock_file
        
        # Mock git command success
        self.engine.run_git_command = Mock(return_value=True)
        
        commit_message = "feat: add new feature"
        result = self.engine.create_commit_with_message(commit_message)
        
        self.assertTrue(result)
        
        # Verify git commit command was called
        self.engine.run_git_command.assert_called_once_with(
            ['git', 'commit', '-F', '/tmp/test_commit_msg.txt'],
            show_output=False
        )
        
        # Verify temporary file was written and cleaned up
        mock_file.write.assert_called_once_with(commit_message)
        mock_unlink.assert_called_once_with('/tmp/test_commit_msg.txt')
    
    @patch('tempfile.NamedTemporaryFile')
    def test_create_commit_with_message_failure(self, mock_tempfile):
        """Test commit creation failure handling."""
        # Mock temporary file
        mock_file = Mock()
        mock_file.name = '/tmp/test_commit_msg.txt'
        mock_tempfile.return_value.__enter__.return_value = mock_file
        
        # Mock git command failure
        self.engine.run_git_command = Mock(return_value=False)
        
        commit_message = "feat: add new feature"
        result = self.engine.create_commit_with_message(commit_message)
        
        self.assertFalse(result)
    
    def test_show_commit_preview_valid_conventional(self):
        """Test commit preview with valid conventional commit."""
        commit_message = "feat(auth): add OAuth2 support"
        self.engine.show_commit_preview(commit_message)
        
        # Check that print_success was called for valid format
        self.mock_git_wrapper.print_success.assert_called_with("✓ Valid conventional commit format")
    
    def test_show_commit_preview_invalid_conventional(self):
        """Test commit preview with invalid conventional commit."""
        commit_message = "added new feature"  # Invalid format
        self.engine.show_commit_preview(commit_message)
        
        # Check that print_error was called for invalid format
        self.mock_git_wrapper.print_error.assert_called_with("✗ Invalid conventional commit format")
    
    def test_show_commit_preview_with_warnings(self):
        """Test commit preview with warnings."""
        with patch('builtins.print') as mock_print:
            # Long subject line to trigger warning
            long_message = "feat: " + "a" * 60
            self.engine.show_commit_preview(long_message)
            
            # Should show warnings section
            printed_calls = [str(call) for call in mock_print.call_args_list]
            warning_found = any("Warnings:" in call for call in printed_calls)
            self.assertTrue(warning_found)
    
    def test_template_field_extraction(self):
        """Test extraction of fields from template patterns."""
        import re
        
        pattern = "feat({scope}): {description}\n\n{body}\n\nCloses #{issue}"
        field_matches = re.findall(r'\{([^}]+)\}', pattern)
        fields = list(set(field_matches))
        
        expected_fields = ['scope', 'description', 'body', 'issue']
        self.assertEqual(sorted(fields), sorted(expected_fields))
    
    def test_template_validation_with_missing_required_field(self):
        """Test template validation when required field is missing from pattern."""
        template = {
            'name': 'Invalid Template',
            'pattern': 'feat: {description}',  # Missing {scope}
            'fields': ['scope', 'description'],
            'required': ['scope', 'description']  # scope is required but not in pattern
        }
        
        errors = self.engine.validate_template_structure(template)
        
        # Should have error about missing required field in pattern
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('not found in pattern' in error for error in errors))
    
    def test_conventional_commit_parsing(self):
        """Test parsing of conventional commit components."""
        message = "feat(auth): add OAuth2 login support"
        result = self.engine.validate_conventional_commit(message)
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['parsed']['type'], 'feat')
        self.assertEqual(result['parsed']['scope'], 'auth')
        self.assertEqual(result['parsed']['description'], 'add OAuth2 login support')
    
    def test_conventional_commit_without_scope(self):
        """Test parsing conventional commit without scope."""
        message = "fix: resolve memory leak"
        result = self.engine.validate_conventional_commit(message)
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['parsed']['type'], 'fix')
        self.assertNotIn('scope', result['parsed'])
        self.assertEqual(result['parsed']['description'], 'resolve memory leak')
    
    def test_conventional_commit_with_body_and_footer(self):
        """Test validation of multi-line conventional commit."""
        message = """feat(api): add user authentication

Implement JWT-based authentication system
with refresh token support.

BREAKING CHANGE: API endpoints now require authentication
Closes #123"""
        
        result = self.engine.validate_conventional_commit(message)
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['parsed']['type'], 'feat')
        self.assertEqual(result['parsed']['scope'], 'api')
        self.assertEqual(result['parsed']['description'], 'add user authentication')
    
    def test_template_cleanup_empty_lines(self):
        """Test that template application cleans up empty lines properly."""
        template = {
            'name': 'Test Template',
            'pattern': 'feat: {description}\n\n{body}\n\n{footer}',
            'fields': ['description', 'body', 'footer'],
            'required': ['description']
        }
        
        # Context with empty optional fields
        context = {
            'description': 'add feature',
            'body': '',
            'footer': ''
        }
        
        result = self.engine.apply_template(template, context)
        
        # Should not have trailing empty lines
        self.assertEqual(result, 'feat: add feature')
        self.assertFalse(result.endswith('\n\n'))


if __name__ == '__main__':
    unittest.main()

class TestCommitTemplateEngineValidationAndManagement(unittest.TestCase):
    """Test cases for CommitTemplateEngine validation and management functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock git wrapper
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {
            'advanced_features': {
                'committemplate': {
                    'default_template': 'conventional',
                    'auto_suggest': True,
                    'validate_conventional': True,
                    'show_template_preview': True,
                    'max_subject_length': 50,
                    'max_body_line_length': 72
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
        self.mock_git_wrapper.confirm = Mock()
        self.mock_git_wrapper.clear_screen = Mock()
        
        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.temp_templates_file = Path(self.temp_dir) / 'test_templates.json'
        
        # Create CommitTemplateEngine instance
        with patch('features.commit_template_engine.Path.home') as mock_home:
            mock_home.return_value = Path(self.temp_dir)
            self.engine = CommitTemplateEngine(self.mock_git_wrapper)
            self.engine.templates_file = self.temp_templates_file
    
    def tearDown(self):
        """Clean up after each test method."""
        # Remove temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_conventional_commit_validation_all_types(self):
        """Test validation of all conventional commit types."""
        valid_types = ['feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore', 'perf', 'ci', 'build', 'revert']
        
        for commit_type in valid_types:
            with self.subTest(commit_type=commit_type):
                message = f"{commit_type}: add new functionality"
                result = self.engine.validate_conventional_commit(message)
                
                self.assertTrue(result['valid'], f"Type '{commit_type}' should be valid")
                self.assertEqual(result['parsed']['type'], commit_type)
                self.assertEqual(result['parsed']['description'], 'add new functionality')
    
    def test_conventional_commit_validation_with_scope(self):
        """Test validation of conventional commits with scope."""
        test_cases = [
            ("feat(api): add endpoint", "feat", "api", "add endpoint"),
            ("fix(ui): resolve button styling", "fix", "ui", "resolve button styling"),
            ("docs(readme): update installation", "docs", "readme", "update installation"),
        ]
        
        for message, expected_type, expected_scope, expected_desc in test_cases:
            with self.subTest(message=message):
                result = self.engine.validate_conventional_commit(message)
                
                self.assertTrue(result['valid'])
                self.assertEqual(result['parsed']['type'], expected_type)
                self.assertEqual(result['parsed']['scope'], expected_scope)
                self.assertEqual(result['parsed']['description'], expected_desc)
    
    def test_conventional_commit_validation_invalid_formats(self):
        """Test validation of invalid conventional commit formats."""
        invalid_messages = [
            "added new feature",  # No type
            "feature: add something",  # Invalid type
            "feat add something",  # Missing colon
            "feat:",  # Missing description
            "feat: ",  # Empty description
            "FEAT: add something",  # Wrong case
        ]
        
        for message in invalid_messages:
            with self.subTest(message=message):
                result = self.engine.validate_conventional_commit(message)
                self.assertFalse(result['valid'], f"Message '{message}' should be invalid")
                self.assertGreater(len(result['errors']), 0)
    
    def test_conventional_commit_validation_warnings(self):
        """Test validation warnings for conventional commits."""
        # Test long subject line
        long_message = "feat: " + "a" * 60  # Exceeds default 50 char limit
        result = self.engine.validate_conventional_commit(long_message)
        
        self.assertTrue(result['valid'])  # Still valid format
        self.assertGreater(len(result['warnings']), 0)
        self.assertTrue(any('characters' in warning for warning in result['warnings']))
        
        # Test uppercase description
        uppercase_message = "feat: Add new feature"  # Should start with lowercase
        result = self.engine.validate_conventional_commit(uppercase_message)
        
        self.assertTrue(result['valid'])
        self.assertTrue(any('lowercase' in warning for warning in result['warnings']))
        
        # Test description ending with period
        period_message = "feat: add new feature."
        result = self.engine.validate_conventional_commit(period_message)
        
        self.assertTrue(result['valid'])
        self.assertTrue(any('period' in warning for warning in result['warnings']))
    
    def test_conventional_commit_validation_body_line_length(self):
        """Test validation of body line lengths."""
        # Create message with long body lines
        long_line = "a" * 80  # Exceeds default 72 char limit
        message = f"feat: add feature\n\n{long_line}\n\nAnother line"
        
        result = self.engine.validate_conventional_commit(message)
        
        self.assertTrue(result['valid'])
        self.assertGreater(len(result['warnings']), 0)
        self.assertTrue(any('Line' in warning and 'characters' in warning for warning in result['warnings']))
    
    def test_template_crud_operations_comprehensive(self):
        """Test comprehensive CRUD operations for templates."""
        # Create
        template = {
            'name': 'Test Template',
            'pattern': 'test({scope}): {description}\n\n{body}',
            'fields': ['scope', 'description', 'body'],
            'required': ['description'],
            'conventional': False,
            'description': 'A test template'
        }
        
        # Test Create
        result = self.engine.create_custom_template('test_crud', template)
        self.assertTrue(result)
        
        # Verify creation
        created_template = self.engine.get_template('test_crud')
        self.assertIsNotNone(created_template)
        self.assertEqual(created_template['name'], 'Test Template')
        self.assertTrue(created_template['custom'])
        self.assertIn('created_at', created_template)
        
        # Test Read (already tested above)
        
        # Test Update
        updated_template = template.copy()
        updated_template['name'] = 'Updated Test Template'
        updated_template['description'] = 'An updated test template'
        
        result = self.engine.update_template('test_crud', updated_template)
        self.assertTrue(result)
        
        # Verify update
        updated = self.engine.get_template('test_crud')
        self.assertEqual(updated['name'], 'Updated Test Template')
        self.assertEqual(updated['description'], 'An updated test template')
        self.assertIn('updated_at', updated)
        
        # Test Delete
        result = self.engine.delete_template('test_crud')
        self.assertTrue(result)
        
        # Verify deletion
        deleted = self.engine.get_template('test_crud')
        self.assertIsNone(deleted)
    
    def test_template_validation_comprehensive(self):
        """Test comprehensive template structure validation."""
        # Test valid template
        valid_template = {
            'name': 'Valid Template',
            'pattern': 'valid({scope}): {description}\n\n{body}\n\n{footer}',
            'fields': ['scope', 'description', 'body', 'footer'],
            'required': ['description'],
            'conventional': True,
            'description': 'A valid template'
        }
        
        errors = self.engine.validate_template_structure(valid_template)
        self.assertEqual(len(errors), 0)
        
        # Test missing required fields
        invalid_templates = [
            # Missing name
            {
                'pattern': 'test: {description}',
                'fields': ['description'],
                'required': ['description']
            },
            # Missing pattern
            {
                'name': 'Test',
                'fields': ['description'],
                'required': ['description']
            },
            # Missing fields
            {
                'name': 'Test',
                'pattern': 'test: {description}',
                'required': ['description']
            },
            # Missing required
            {
                'name': 'Test',
                'pattern': 'test: {description}',
                'fields': ['description']
            }
        ]
        
        for i, invalid_template in enumerate(invalid_templates):
            with self.subTest(template_index=i):
                errors = self.engine.validate_template_structure(invalid_template)
                self.assertGreater(len(errors), 0)
        
        # Test required field not in pattern
        invalid_pattern_template = {
            'name': 'Invalid Pattern',
            'pattern': 'test: {description}',  # Missing {scope}
            'fields': ['scope', 'description'],
            'required': ['scope', 'description']  # scope required but not in pattern
        }
        
        errors = self.engine.validate_template_structure(invalid_pattern_template)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('not found in pattern' in error for error in errors))
        
        # Test invalid field types
        invalid_types_template = {
            'name': 'Invalid Types',
            'pattern': 'test: {description}',
            'fields': 'description',  # Should be list
            'required': 'description'  # Should be list
        }
        
        errors = self.engine.validate_template_structure(invalid_types_template)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('must be a list' in error for error in errors))
    
    def test_template_override_default(self):
        """Test overriding default templates with custom versions."""
        # Try to update a default template (should create custom override)
        updated_feat_template = {
            'name': 'Custom Feature Template',
            'pattern': 'feat({scope}): {description}\n\nCustom body: {body}',
            'fields': ['scope', 'description', 'body'],
            'required': ['description'],
            'conventional': True,
            'description': 'Custom version of feat template'
        }
        
        result = self.engine.update_template('feat', updated_feat_template)
        self.assertTrue(result)
        
        # Verify that a custom override was created
        templates_data = self.engine._load_templates()
        self.assertIn('feat', templates_data['custom_templates'])
        
        custom_feat = templates_data['custom_templates']['feat']
        self.assertEqual(custom_feat['name'], 'Custom Feature Template')
        self.assertTrue(custom_feat['custom'])
        self.assertTrue(custom_feat['overrides_default'])
        
        # Verify that get_template returns the custom version
        feat_template = self.engine.get_template('feat')
        self.assertEqual(feat_template['name'], 'Custom Feature Template')
    
    def test_template_management_error_handling(self):
        """Test error handling in template management operations."""
        # Test creating template with invalid structure
        invalid_template = {
            'name': 'Invalid'
            # Missing required fields
        }
        
        result = self.engine.create_custom_template('invalid', invalid_template)
        self.assertFalse(result)
        
        # Test updating non-existent template
        valid_template = {
            'name': 'Valid',
            'pattern': 'test: {description}',
            'fields': ['description'],
            'required': ['description']
        }
        
        result = self.engine.update_template('non_existent', valid_template)
        self.assertFalse(result)
        
        # Test deleting non-existent template
        result = self.engine.delete_template('non_existent')
        self.assertFalse(result)
        
        # Test deleting default template (should fail)
        result = self.engine.delete_template('feat')
        self.assertFalse(result)
    
    def test_reset_to_defaults_comprehensive(self):
        """Test comprehensive reset to defaults functionality."""
        # Create several custom templates
        custom_templates = {
            'custom1': {
                'name': 'Custom 1',
                'pattern': 'custom1: {description}',
                'fields': ['description'],
                'required': ['description']
            },
            'custom2': {
                'name': 'Custom 2',
                'pattern': 'custom2: {description}',
                'fields': ['description'],
                'required': ['description']
            }
        }
        
        for key, template in custom_templates.items():
            self.engine.create_custom_template(key, template)
        
        # Override a default template
        self.engine.update_template('feat', {
            'name': 'Overridden Feat',
            'pattern': 'feat: {description}',
            'fields': ['description'],
            'required': ['description']
        })
        
        # Verify custom templates and overrides exist
        all_templates = self.engine.get_all_templates()
        self.assertIn('custom1', all_templates)
        self.assertIn('custom2', all_templates)
        
        feat_template = self.engine.get_template('feat')
        self.assertEqual(feat_template['name'], 'Overridden Feat')
        
        # Reset to defaults
        result = self.engine.reset_to_defaults()
        self.assertTrue(result)
        
        # Verify custom templates are gone
        all_templates = self.engine.get_all_templates()
        self.assertNotIn('custom1', all_templates)
        self.assertNotIn('custom2', all_templates)
        
        # Verify default templates are restored
        feat_template = self.engine.get_template('feat')
        self.assertEqual(feat_template['name'], 'Feature')  # Original default name
        
        # Verify only default templates remain
        templates_data = self.engine._load_templates()
        self.assertEqual(len(templates_data['custom_templates']), 0)
        self.assertGreater(len(templates_data['templates']), 0)
    
    def test_template_field_extraction_edge_cases(self):
        """Test field extraction from template patterns with edge cases."""
        test_cases = [
            # Normal case
            ("feat({scope}): {description}", ['scope', 'description']),
            # Duplicate fields
            ("feat({scope}): {description} in {scope}", ['scope', 'description']),
            # No fields
            ("feat: static message", []),
            # Complex pattern
            ("feat({scope}): {description}\n\n{body}\n\nCloses #{issue}", ['scope', 'description', 'body', 'issue']),
            # Nested braces (regex will match both, but this is edge case behavior)
            ("feat: {description} with {nested{field}}", ['description', 'nested{field']),
        ]
        
        for pattern, expected_fields in test_cases:
            with self.subTest(pattern=pattern):
                import re
                field_matches = re.findall(r'\{([^}]+)\}', pattern)
                fields = list(set(field_matches))
                
                self.assertEqual(sorted(fields), sorted(expected_fields))
    
    def test_conventional_commit_edge_cases(self):
        """Test conventional commit validation edge cases."""
        edge_cases = [
            # Empty message
            ("", False, ["cannot be empty"]),
            # Only whitespace - this will fail conventional format validation, not empty check
            ("   ", False, ["does not follow conventional commit format"]),
            # Valid minimal
            ("feat: x", True, []),
            # Multiple colons
            ("feat: add: new feature", True, []),
            # Special characters in scope
            ("feat(api-v2): add endpoint", True, []),
            ("feat(api_v2): add endpoint", True, []),
            # Unicode characters
            ("feat: add café feature", True, []),
        ]
        
        for message, should_be_valid, expected_error_keywords in edge_cases:
            with self.subTest(message=repr(message)):
                result = self.engine.validate_conventional_commit(message)
                
                self.assertEqual(result['valid'], should_be_valid)
                
                if not should_be_valid:
                    for keyword in expected_error_keywords:
                        self.assertTrue(
                            any(keyword in error for error in result['errors']),
                            f"Expected error containing '{keyword}' not found in {result['errors']}"
                        )


if __name__ == '__main__':
    unittest.main()