#!/usr/bin/env python3
"""
Unit Tests for Error Handling and Logging

This module contains comprehensive tests for the error handling system
including error classification, recovery mechanisms, and logging functionality.
"""

import unittest
import tempfile
import shutil
import json
import time
import subprocess
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the modules to test
from features.error_handler import (
    ErrorHandler, GitWrapperError, GitCommandError, FileOperationError,
    ErrorSeverity, ErrorCategory, error_handler_decorator, safe_git_command
)
from features.base_manager import BaseFeatureManager
from features.input_validator import InputValidator, InputValidationError
from features.timeout_handler import TimeoutHandler, TimeoutError, timeout_context


class MockGitWrapper:
    """Mock GitWrapper for testing."""
    
    def __init__(self):
        self.config = {
            'show_emoji': True,
            'error_handling': {
                'log_level': 'INFO',
                'max_log_files': 5,
                'max_log_size_mb': 5,
                'enable_debug_mode': True,
                'auto_recovery': True,
                'max_recovery_attempts': 3,
                'show_stack_traces': False,
                'log_git_commands': True,
                'error_reporting': True
            }
        }
        self.messages = []
        self.input_validator = InputValidator()
        self.timeout_handler = TimeoutHandler()
    
    def print_error(self, message):
        self.messages.append(('error', message))
    
    def print_success(self, message):
        self.messages.append(('success', message))
    
    def print_info(self, message):
        self.messages.append(('info', message))
    
    def save_config(self):
        pass


class TestErrorClasses(unittest.TestCase):
    """Test error class functionality."""
    
    def test_git_wrapper_error_creation(self):
        """Test GitWrapperError creation and properties."""
        error = GitWrapperError(
            message="Test error",
            category=ErrorCategory.GIT_COMMAND,
            severity=ErrorSeverity.HIGH,
            suggestions=["Try this", "Or this"],
            recoverable=True
        )
        
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.category, ErrorCategory.GIT_COMMAND)
        self.assertEqual(error.severity, ErrorSeverity.HIGH)
        self.assertEqual(error.suggestions, ["Try this", "Or this"])
        self.assertTrue(error.recoverable)
        self.assertIsInstance(error.timestamp, float)
    
    def test_git_command_error_creation(self):
        """Test GitCommandError creation and suggestion generation."""
        error = GitCommandError(
            command=['git', 'status'],
            return_code=128,
            stderr="not a git repository"
        )
        
        self.assertIn("git status", error.message)
        self.assertEqual(error.return_code, 128)
        self.assertEqual(error.stderr, "not a git repository")
        self.assertEqual(error.category, ErrorCategory.GIT_COMMAND)
        self.assertEqual(error.severity, ErrorSeverity.HIGH)
        
        # Check that suggestions are generated
        self.assertGreater(len(error.suggestions), 0)
        self.assertTrue(any("git init" in suggestion for suggestion in error.suggestions))
    
    def test_file_operation_error_creation(self):
        """Test FileOperationError creation."""
        original_error = FileNotFoundError("File not found")
        error = FileOperationError(
            operation="read",
            file_path="/path/to/file.txt",
            original_error=original_error
        )
        
        self.assertIn("read", error.message)
        self.assertIn("/path/to/file.txt", error.message)
        self.assertEqual(error.operation, "read")
        self.assertEqual(error.file_path, "/path/to/file.txt")
        self.assertEqual(error.original_error, original_error)
        self.assertEqual(error.category, ErrorCategory.FILE_OPERATION)


class TestErrorHandler(unittest.TestCase):
    """Test ErrorHandler functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_git_wrapper = MockGitWrapper()
        self.error_handler = ErrorHandler(self.mock_git_wrapper, log_dir=self.temp_dir / 'logs')
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization."""
        self.assertIsInstance(self.error_handler.logger, logging.Logger)
        self.assertTrue(self.error_handler.log_dir.exists())
        self.assertEqual(len(self.error_handler.error_history), 0)
        self.assertEqual(len(self.error_handler.recovery_attempts), 0)
    
    def test_logging_methods(self):
        """Test logging methods."""
        # Test info logging
        self.error_handler.log_info("Test info message", feature="test", operation="test_op")
        
        # Test warning logging
        self.error_handler.log_warning("Test warning message", feature="test", operation="test_op")
        
        # Test error logging
        test_exception = Exception("Test exception")
        self.error_handler.log_error("Test error message", feature="test", operation="test_op", exception=test_exception)
        
        # Test debug logging
        self.error_handler.log_debug("Test debug message", feature="test", operation="test_op")
        
        # Check that log files were created
        log_files = list(self.error_handler.log_dir.glob('*.log'))
        self.assertGreater(len(log_files), 0)
    
    def test_error_handling(self):
        """Test error handling workflow."""
        test_error = GitWrapperError(
            message="Test error for handling",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            suggestions=["Fix this", "Try that"],
            recoverable=True
        )
        
        # Handle the error
        result = self.error_handler.handle_error(
            error=test_error,
            feature="test_feature",
            operation="test_operation",
            context={'test': 'context'}
        )
        
        # Check that error was recorded
        self.assertEqual(len(self.error_handler.error_history), 1)
        error_record = self.error_handler.error_history[0]
        
        self.assertEqual(error_record['feature'], 'test_feature')
        self.assertEqual(error_record['operation'], 'test_operation')
        self.assertEqual(error_record['category'], 'validation')
        self.assertEqual(error_record['severity'], 'medium')
        self.assertTrue(error_record['recoverable'])
        
        # Check that user was notified
        self.assertGreater(len(self.mock_git_wrapper.messages), 0)
        error_messages = [msg for msg_type, msg in self.mock_git_wrapper.messages if msg_type == 'error']
        self.assertGreater(len(error_messages), 0)
    
    def test_error_conversion(self):
        """Test conversion of generic exceptions to GitWrapperError."""
        generic_error = ValueError("Invalid value")
        
        converted_error = self.error_handler._convert_to_wrapper_error(
            generic_error, 
            feature="test_feature", 
            operation="test_op"
        )
        
        self.assertIsInstance(converted_error, GitWrapperError)
        self.assertIn("ValueError", converted_error.message)
        self.assertEqual(converted_error.category, ErrorCategory.VALIDATION)
    
    def test_recovery_attempts_tracking(self):
        """Test recovery attempts tracking."""
        test_error = GitWrapperError(
            message="Recoverable error",
            category=ErrorCategory.FILE_OPERATION,
            recoverable=True
        )
        
        # First attempt
        self.error_handler._attempt_recovery(test_error, "test_feature", "test_op")
        recovery_key = "test_feature.test_op.file_operation"
        self.assertEqual(self.error_handler.recovery_attempts[recovery_key], 1)
        
        # Second attempt
        self.error_handler._attempt_recovery(test_error, "test_feature", "test_op")
        self.assertEqual(self.error_handler.recovery_attempts[recovery_key], 2)
        
        # Third attempt
        self.error_handler._attempt_recovery(test_error, "test_feature", "test_op")
        self.assertEqual(self.error_handler.recovery_attempts[recovery_key], 3)
        
        # Fourth attempt should be blocked
        result = self.error_handler._attempt_recovery(test_error, "test_feature", "test_op")
        self.assertFalse(result)
        self.assertEqual(self.error_handler.recovery_attempts[recovery_key], 3)
    
    def test_error_statistics(self):
        """Test error statistics generation."""
        # Add some test errors
        errors = [
            GitWrapperError("Error 1", ErrorCategory.GIT_COMMAND, ErrorSeverity.HIGH),
            GitWrapperError("Error 2", ErrorCategory.FILE_OPERATION, ErrorSeverity.MEDIUM),
            GitWrapperError("Error 3", ErrorCategory.GIT_COMMAND, ErrorSeverity.LOW),
        ]
        
        for error in errors:
            self.error_handler.handle_error(error, "test_feature", "test_op")
        
        stats = self.error_handler.get_error_statistics()
        
        self.assertEqual(stats['total_errors'], 3)
        self.assertEqual(stats['category_breakdown']['git_command'], 2)
        self.assertEqual(stats['category_breakdown']['file_operation'], 1)
        self.assertEqual(stats['severity_breakdown']['high'], 1)
        self.assertEqual(stats['severity_breakdown']['medium'], 1)
        self.assertEqual(stats['severity_breakdown']['low'], 1)
    
    def test_error_report_export(self):
        """Test error report export functionality."""
        # Add a test error
        test_error = GitWrapperError("Test error for export")
        self.error_handler.handle_error(test_error, "test_feature", "test_op")
        
        # Export report
        report_file = self.error_handler.export_error_report()
        
        self.assertTrue(report_file.exists())
        
        # Verify report content
        with open(report_file, 'r') as f:
            report_data = json.load(f)
        
        self.assertIn('generated_at', report_data)
        self.assertIn('statistics', report_data)
        self.assertIn('error_history', report_data)
        self.assertEqual(len(report_data['error_history']), 1)
    
    def test_logging_configuration(self):
        """Test logging configuration updates."""
        # Update configuration
        self.error_handler.configure_logging(
            log_level='DEBUG',
            enable_debug=True,
            max_log_size_mb=20
        )
        
        # Check configuration was updated
        self.assertEqual(self.error_handler.config['error_handling']['log_level'], 'DEBUG')
        self.assertTrue(self.error_handler.config['error_handling']['enable_debug_mode'])
        self.assertEqual(self.error_handler.config['error_handling']['max_log_size_mb'], 20)


class TestErrorDecorator(unittest.TestCase):
    """Test error handling decorator."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_git_wrapper = MockGitWrapper()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_decorator_success(self):
        """Test decorator with successful operation."""
        class TestClass:
            def __init__(self, temp_dir):
                self.error_handler = ErrorHandler(MockGitWrapper(), log_dir=temp_dir / 'logs')
            
            @error_handler_decorator(feature="test", operation="success_op")
            def successful_method(self, value):
                return value * 2
        
        test_obj = TestClass(self.temp_dir)
        result = test_obj.successful_method(5)
        self.assertEqual(result, 10)
    
    def test_decorator_with_error(self):
        """Test decorator with error handling."""
        class TestClass:
            def __init__(self, temp_dir):
                self.error_handler = ErrorHandler(MockGitWrapper(), log_dir=temp_dir / 'logs')
            
            @error_handler_decorator(feature="test", operation="error_op")
            def failing_method(self):
                raise ValueError("Test error")
        
        test_obj = TestClass(self.temp_dir)
        
        # The decorator should handle the error
        with self.assertRaises(ValueError):
            test_obj.failing_method()
        
        # Check that error was logged
        self.assertGreater(len(test_obj.error_handler.error_history), 0)


class TestSafeGitCommand(unittest.TestCase):
    """Test safe Git command execution."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_git_wrapper = MockGitWrapper()
        self.error_handler = ErrorHandler(self.mock_git_wrapper, log_dir=self.temp_dir / 'logs')
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('subprocess.run')
    def test_successful_git_command(self, mock_run):
        """Test successful Git command execution."""
        # Mock successful command
        mock_result = Mock()
        mock_result.stdout = "test output"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = safe_git_command(
            error_handler=self.error_handler,
            command=['git', 'status'],
            feature='test',
            operation='status',
            capture_output=True
        )
        
        self.assertEqual(result, "test output")
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_failing_git_command(self, mock_run):
        """Test failing Git command execution."""
        # Mock failing command
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=128,
            cmd=['git', 'status'],
            stderr="not a git repository"
        )
        
        result = safe_git_command(
            error_handler=self.error_handler,
            command=['git', 'status'],
            feature='test',
            operation='status',
            capture_output=True
        )
        
        self.assertEqual(result, "")  # Should return empty string on failure
        
        # Check that error was handled
        self.assertGreater(len(self.error_handler.error_history), 0)
        error_record = self.error_handler.error_history[0]
        self.assertEqual(error_record['category'], 'git_command')


class TestBaseManagerErrorIntegration(unittest.TestCase):
    """Test error handling integration in BaseFeatureManager."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_git_wrapper = MockGitWrapper()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_base_manager_error_handler_initialization(self):
        """Test that BaseFeatureManager initializes error handler."""
        class TestManager(BaseFeatureManager):
            def _get_default_config(self):
                return {}
            
            def interactive_menu(self):
                pass
        
        manager = TestManager(self.mock_git_wrapper)
        self.assertIsInstance(manager.error_handler, ErrorHandler)
    
    def test_safe_operation_method(self):
        """Test safe operation execution."""
        class TestManager(BaseFeatureManager):
            def _get_default_config(self):
                return {}
            
            def interactive_menu(self):
                pass
        
        manager = TestManager(self.mock_git_wrapper)
        
        # Test successful operation
        def successful_op(x, y):
            return x + y
        
        result = manager.safe_operation("add", successful_op, 2, 3)
        self.assertEqual(result, 5)
        
        # Test failing operation
        def failing_op():
            raise ValueError("Test error")
        
        result = manager.safe_operation("fail", failing_op)
        self.assertIsNone(result)
        
        # Check that error was logged
        self.assertGreater(len(manager.error_handler.error_history), 0)
    
    def test_input_validation(self):
        """Test input validation functionality."""
        class TestManager(BaseFeatureManager):
            def _get_default_config(self):
                return {}
            
            def interactive_menu(self):
                pass
        
        manager = TestManager(self.mock_git_wrapper)
        
        # Test valid input
        validation_rules = {
            'required': True,
            'type': str,
            'min_length': 3,
            'max_length': 10
        }
        
        self.assertTrue(manager.validate_input("test", validation_rules, "test_field"))
        
        # Test invalid input - too short
        self.assertFalse(manager.validate_input("ab", validation_rules, "test_field"))
        
        # Test invalid input - wrong type
        self.assertFalse(manager.validate_input(123, validation_rules, "test_field"))
        
        # Test invalid input - empty required field
        self.assertFalse(manager.validate_input("", validation_rules, "test_field"))


class TestRecoveryMechanisms(unittest.TestCase):
    """Test error recovery mechanisms."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_git_wrapper = MockGitWrapper()
        self.error_handler = ErrorHandler(self.mock_git_wrapper, log_dir=self.temp_dir / 'logs')
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('subprocess.run')
    def test_git_init_recovery(self, mock_run):
        """Test recovery by initializing Git repository."""
        # First call fails with "not a git repository"
        # Second call succeeds (git init)
        mock_run.side_effect = [
            Mock(),  # Successful git init
        ]
        
        error = GitCommandError(
            command=['git', 'status'],
            return_code=128,
            stderr="not a git repository"
        )
        
        result = self.error_handler._recover_git_command_error(error)
        self.assertTrue(result)
        mock_run.assert_called_with(['git', 'init'], check=True, capture_output=True)
    
    def test_file_operation_recovery(self):
        """Test file operation error recovery."""
        # Create a test scenario where parent directory doesn't exist
        test_file = self.temp_dir / 'nonexistent' / 'test.txt'
        
        error = FileOperationError(
            operation="write",
            file_path=str(test_file),
            original_error=FileNotFoundError("No such file or directory")
        )
        
        result = self.error_handler._recover_file_operation_error(error)
        self.assertTrue(result)
        
        # Check that parent directory was created
        self.assertTrue(test_file.parent.exists())


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)

class TestInputValidationIntegration(unittest.TestCase):
    """Test input validation integration with error handling."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_git_wrapper = MockGitWrapper()
        self.error_handler = ErrorHandler(self.mock_git_wrapper, log_dir=self.temp_dir / 'logs')
        self.input_validator = InputValidator(self.error_handler)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_input_validation_with_error_handling(self):
        """Test input validation with error handling integration."""
        # Test valid input
        validation_rules = {
            'required': True,
            'validator_type': 'branch_name'
        }
        
        # Valid branch name
        self.assertTrue(self.input_validator.validate_input("feature-branch", validation_rules, "branch_name"))
        
        # Invalid branch name
        self.assertFalse(self.input_validator.validate_input("feature branch", validation_rules, "branch_name"))
        
        # Check that error was logged
        self.assertGreater(len(self.error_handler.error_history), 0)
        error_record = self.error_handler.error_history[0]
        self.assertEqual(error_record['category'], 'validation')
    
    def test_sanitization_with_error_handling(self):
        """Test input sanitization with error handling."""
        # Test shell input sanitization
        dangerous_input = "echo 'hello'; rm -rf /"
        sanitized = self.input_validator.sanitize_shell_input(dangerous_input)
        
        # Ensure sanitized input is safe
        self.assertNotEqual(sanitized, dangerous_input)
        self.assertNotIn(";", sanitized)
        
        # Test path sanitization
        path_traversal = "../../../etc/passwd"
        sanitized_path = self.input_validator.sanitize_path(path_traversal, allow_outside_repo=False)
        
        # Ensure path traversal is prevented
        self.assertNotEqual(sanitized_path, path_traversal)
        self.assertNotIn("..", sanitized_path)


class TestTimeoutHandlingIntegration(unittest.TestCase):
    """Test timeout handling integration with error handling."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_git_wrapper = MockGitWrapper()
        self.error_handler = ErrorHandler(self.mock_git_wrapper, log_dir=self.temp_dir / 'logs')
        self.timeout_handler = TimeoutHandler(self.error_handler)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_timeout_with_error_handling(self):
        """Test timeout handling with error handling integration."""
        # Test function that times out
        def slow_function():
            time.sleep(0.5)
            return "success"
        
        # Should raise TimeoutError
        with self.assertRaises(TimeoutError):
            self.timeout_handler.run_with_timeout(slow_function, timeout=0.1)
        
        # Check that error was logged
        self.assertGreater(len(self.error_handler.error_history), 0)
        error_record = self.error_handler.error_history[0]
        self.assertEqual(error_record['category'], 'unknown')  # TimeoutError is converted to GitWrapperError
    
    @patch('subprocess.run')
    def test_subprocess_timeout_with_error_handling(self, mock_run):
        """Test subprocess timeout with error handling."""
        # Mock subprocess.run to raise TimeoutExpired
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=['git', 'clone'], timeout=0.1)
        
        # Should raise TimeoutError
        with self.assertRaises(TimeoutError):
            self.timeout_handler.run_subprocess_with_timeout(
                cmd=['git', 'clone', 'https://example.com/repo.git'],
                timeout=0.1
            )
        
        # Check that error was logged
        self.assertGreater(len(self.error_handler.error_history), 0)
    
    def test_recommended_timeout_calculation(self):
        """Test recommended timeout calculation."""
        # Test different operation types
        clone_timeout = self.timeout_handler.get_recommended_timeout('clone')
        self.assertEqual(clone_timeout, 300)  # 5 minutes
        
        status_timeout = self.timeout_handler.get_recommended_timeout('status')
        self.assertEqual(status_timeout, 10)  # 10 seconds
        
        # Test with repository size
        large_repo_timeout = self.timeout_handler.get_recommended_timeout('clone', repo_size=2000)
        self.assertEqual(large_repo_timeout, 900)  # 15 minutes (3x default)


class TestBaseManagerWithValidationAndTimeout(unittest.TestCase):
    """Test BaseFeatureManager with input validation and timeout handling."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_git_wrapper = MockGitWrapper()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_base_manager_initialization(self):
        """Test that BaseFeatureManager initializes input validator and timeout handler."""
        class TestManager(BaseFeatureManager):
            def _get_default_config(self):
                return {}
            
            def interactive_menu(self):
                pass
        
        manager = TestManager(self.mock_git_wrapper)
        self.assertIsInstance(manager.input_validator, InputValidator)
        self.assertIsInstance(manager.timeout_handler, TimeoutHandler)
    
    @patch('subprocess.run')
    def test_run_git_command_with_timeout(self, mock_run):
        """Test run_git_command with timeout handling."""
        class TestManager(BaseFeatureManager):
            def _get_default_config(self):
                return {}
            
            def interactive_menu(self):
                pass
        
        manager = TestManager(self.mock_git_wrapper)
        
        # Mock successful command
        mock_result = Mock()
        mock_result.stdout = "test output"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Test with timeout
        result = manager.run_git_command(
            ['git', 'status'],
            capture_output=True,
            timeout=10,
            operation_type='status'
        )
        
        self.assertEqual(result, "test output")
        mock_run.assert_called_once()
        
        # Test with timeout error
        mock_run.reset_mock()
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=['git', 'status'], timeout=10)
        
        result = manager.run_git_command(
            ['git', 'status'],
            capture_output=True,
            timeout=10,
            operation_type='status'
        )
        
        self.assertEqual(result, "")  # Should return empty string on failure
    
    def test_input_validation_methods(self):
        """Test input validation methods."""
        class TestManager(BaseFeatureManager):
            def _get_default_config(self):
                return {}
            
            def interactive_menu(self):
                pass
        
        manager = TestManager(self.mock_git_wrapper)
        
        # Test branch name validation
        self.assertTrue(manager.validate_branch_name("feature-branch"))
        self.assertFalse(manager.validate_branch_name("feature branch"))
        
        # Test filename sanitization
        self.assertEqual(manager.sanitize_filename("file.txt"), "file.txt")
        self.assertEqual(manager.sanitize_filename("file?.txt"), "file_.txt")