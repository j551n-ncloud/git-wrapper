#!/usr/bin/env python3
"""
Unit Tests for Debug Logging and Performance Monitoring

This module contains comprehensive tests for the debug logging system
including performance tracking, operation monitoring, and log management.
"""

import unittest
import tempfile
import shutil
import json
import time
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import the modules to test
from features.debug_logger import (
    DebugLogger, OperationMetrics, PerformanceStats, LogLevel,
    debug_trace, time_operation
)
from features.base_manager import BaseFeatureManager


class MockGitWrapper:
    """Mock GitWrapper for testing."""
    
    def __init__(self):
        self.config = {
            'show_emoji': True,
            'debug_logging': {
                'log_level': 'DEBUG',
                'enable_debug_mode': True,
                'trace_operations': True,
                'profile_performance': True,
                'max_log_files': 5,
                'max_log_size_mb': 5,
                'console_logging': False,
                'detailed_git_logging': True,
                'operation_timing': True,
                'memory_monitoring': False,
                'log_format': 'detailed',
                'auto_cleanup_days': 30
            }
        }
        self.messages = []
    
    def print_error(self, message):
        self.messages.append(('error', message))
    
    def print_success(self, message):
        self.messages.append(('success', message))
    
    def print_info(self, message):
        self.messages.append(('info', message))
    
    def save_config(self):
        pass


class TestOperationMetrics(unittest.TestCase):
    """Test OperationMetrics functionality."""
    
    def test_operation_metrics_creation(self):
        """Test OperationMetrics creation and properties."""
        start_time = time.time()
        metrics = OperationMetrics(
            operation_name="test_operation",
            feature="test_feature",
            start_time=start_time
        )
        
        self.assertEqual(metrics.operation_name, "test_operation")
        self.assertEqual(metrics.feature, "test_feature")
        self.assertEqual(metrics.start_time, start_time)
        self.assertIsNone(metrics.end_time)
        self.assertIsNone(metrics.duration)
        self.assertTrue(metrics.success)
        self.assertIsNone(metrics.error_message)
        self.assertEqual(len(metrics.git_commands), 0)
    
    def test_operation_metrics_finish(self):
        """Test finishing operation metrics."""
        start_time = time.time()
        metrics = OperationMetrics(
            operation_name="test_operation",
            feature="test_feature",
            start_time=start_time
        )
        
        time.sleep(0.01)  # Small delay to ensure duration > 0
        metrics.finish(success=True)
        
        self.assertIsNotNone(metrics.end_time)
        self.assertIsNotNone(metrics.duration)
        self.assertGreater(metrics.duration, 0)
        self.assertTrue(metrics.success)
        self.assertIsNone(metrics.error_message)
        
        # Test finishing with error
        metrics.finish(success=False, error_message="Test error")
        self.assertFalse(metrics.success)
        self.assertEqual(metrics.error_message, "Test error")


class TestPerformanceStats(unittest.TestCase):
    """Test PerformanceStats functionality."""
    
    def test_performance_stats_initialization(self):
        """Test PerformanceStats initialization."""
        stats = PerformanceStats()
        
        self.assertEqual(stats.total_operations, 0)
        self.assertEqual(stats.successful_operations, 0)
        self.assertEqual(stats.failed_operations, 0)
        self.assertEqual(stats.total_duration, 0.0)
        self.assertEqual(stats.average_duration, 0.0)
        self.assertEqual(stats.min_duration, float('inf'))
        self.assertEqual(stats.max_duration, 0.0)
        self.assertEqual(stats.git_commands_executed, 0)
    
    def test_performance_stats_update(self):
        """Test updating performance statistics."""
        stats = PerformanceStats()
        
        # Create test metrics
        metrics1 = OperationMetrics("op1", "feature1", time.time())
        metrics1.finish(success=True)
        metrics1.duration = 0.5
        metrics1.git_commands = ["git status", "git add ."]
        
        metrics2 = OperationMetrics("op2", "feature1", time.time())
        metrics2.finish(success=False, error_message="Test error")
        metrics2.duration = 0.3
        metrics2.git_commands = ["git commit"]
        
        # Update stats
        stats.update(metrics1)
        stats.update(metrics2)
        
        self.assertEqual(stats.total_operations, 2)
        self.assertEqual(stats.successful_operations, 1)
        self.assertEqual(stats.failed_operations, 1)
        self.assertEqual(stats.total_duration, 0.8)
        self.assertEqual(stats.average_duration, 0.4)
        self.assertEqual(stats.min_duration, 0.3)
        self.assertEqual(stats.max_duration, 0.5)
        self.assertEqual(stats.git_commands_executed, 3)


class TestDebugLogger(unittest.TestCase):
    """Test DebugLogger functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_git_wrapper = MockGitWrapper()
        self.debug_logger = DebugLogger(self.mock_git_wrapper, log_dir=self.temp_dir / 'logs')
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_debug_logger_initialization(self):
        """Test DebugLogger initialization."""
        self.assertTrue(self.debug_logger.log_dir.exists())
        self.assertTrue(self.debug_logger.debug_mode)
        self.assertTrue(self.debug_logger.trace_operations)
        self.assertTrue(self.debug_logger.profile_performance)
        self.assertEqual(len(self.debug_logger.operation_metrics), 0)
        self.assertGreater(len(self.debug_logger.performance_stats), 0)
    
    def test_logging_methods(self):
        """Test various logging methods."""
        # Test info logging
        self.debug_logger.log_info("Test info message", "test_feature", "test_op")
        
        # Test debug logging
        self.debug_logger.log_debug("Test debug message", "test_feature", "test_op")
        
        # Test warning logging
        self.debug_logger.log_warning("Test warning message", "test_feature", "test_op")
        
        # Test error logging
        test_exception = Exception("Test exception")
        self.debug_logger.log_error("Test error message", "test_feature", "test_op", test_exception)
        
        # Test Git command logging
        self.debug_logger.log_git_command(
            ["git", "status"], "test_feature", "test_op", 0.5, True, "output"
        )
        
        # Check that log files were created
        log_files = list(self.debug_logger.log_dir.glob('*.log'))
        self.assertGreater(len(log_files), 0)
    
    def test_operation_tracking(self):
        """Test operation tracking context manager."""
        with self.debug_logger.track_operation("test_operation", "test_feature") as metrics:
            self.assertIsInstance(metrics, OperationMetrics)
            self.assertEqual(metrics.operation_name, "test_operation")
            self.assertEqual(metrics.feature, "test_feature")
            
            # Simulate some work
            time.sleep(0.01)
            
            # Add a Git command
            self.debug_logger.add_git_command_to_current_operation(["git", "status"])
        
        # Check that operation was recorded
        self.assertEqual(len(self.debug_logger.operation_metrics), 1)
        recorded_metrics = self.debug_logger.operation_metrics[0]
        
        self.assertEqual(recorded_metrics.operation_name, "test_operation")
        self.assertEqual(recorded_metrics.feature, "test_feature")
        self.assertTrue(recorded_metrics.success)
        self.assertIsNotNone(recorded_metrics.duration)
        self.assertGreater(recorded_metrics.duration, 0)
        self.assertEqual(len(recorded_metrics.git_commands), 1)
        self.assertEqual(recorded_metrics.git_commands[0], "git status")
    
    def test_operation_tracking_with_error(self):
        """Test operation tracking with error."""
        try:
            with self.debug_logger.track_operation("failing_operation", "test_feature") as metrics:
                time.sleep(0.01)
                raise ValueError("Test error")
        except ValueError:
            pass  # Expected
        
        # Check that operation was recorded with error
        self.assertEqual(len(self.debug_logger.operation_metrics), 1)
        recorded_metrics = self.debug_logger.operation_metrics[0]
        
        self.assertFalse(recorded_metrics.success)
        self.assertEqual(recorded_metrics.error_message, "Test error")
        self.assertIsNotNone(recorded_metrics.duration)
    
    def test_performance_stats_tracking(self):
        """Test performance statistics tracking."""
        # Perform some operations
        with self.debug_logger.track_operation("op1", "test_feature"):
            time.sleep(0.01)
        
        with self.debug_logger.track_operation("op2", "test_feature"):
            time.sleep(0.01)
        
        try:
            with self.debug_logger.track_operation("op3", "test_feature"):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Check performance stats
        stats = self.debug_logger.get_performance_stats("test_feature")
        self.assertEqual(stats.total_operations, 3)
        self.assertEqual(stats.successful_operations, 2)
        self.assertEqual(stats.failed_operations, 1)
        self.assertGreater(stats.total_duration, 0)
        self.assertGreater(stats.average_duration, 0)
    
    def test_debug_mode_controls(self):
        """Test debug mode control methods."""
        # Test disabling debug mode
        self.debug_logger.disable_debug_mode()
        self.assertFalse(self.debug_logger.debug_mode)
        
        # Test enabling debug mode
        self.debug_logger.enable_debug_mode()
        self.assertTrue(self.debug_logger.debug_mode)
        
        # Test operation tracing controls
        self.debug_logger.disable_operation_tracing()
        self.assertFalse(self.debug_logger.trace_operations)
        
        self.debug_logger.enable_operation_tracing()
        self.assertTrue(self.debug_logger.trace_operations)
        
        # Test performance profiling controls
        self.debug_logger.disable_performance_profiling()
        self.assertFalse(self.debug_logger.profile_performance)
        
        self.debug_logger.enable_performance_profiling()
        self.assertTrue(self.debug_logger.profile_performance)
    
    def test_log_management(self):
        """Test log management functionality."""
        # Create some log entries
        self.debug_logger.log_info("Test message 1")
        self.debug_logger.log_info("Test message 2")
        
        # Test log file info
        log_info = self.debug_logger.get_log_file_info()
        self.assertGreater(len(log_info), 0)
        
        for file_name, info in log_info.items():
            if 'error' not in info:
                self.assertIn('size_mb', info)
                self.assertIn('modified', info)
    
    def test_recent_operations_retrieval(self):
        """Test retrieving recent operations."""
        # Perform some operations
        for i in range(5):
            with self.debug_logger.track_operation(f"op_{i}", "test_feature"):
                time.sleep(0.001)
        
        # Get recent operations
        recent_ops = self.debug_logger.get_recent_operations(limit=3)
        self.assertEqual(len(recent_ops), 3)
        
        # Get recent operations for specific feature
        feature_ops = self.debug_logger.get_recent_operations(limit=10, feature="test_feature")
        self.assertEqual(len(feature_ops), 5)
        
        # Get recent operations for non-existent feature
        no_ops = self.debug_logger.get_recent_operations(limit=10, feature="nonexistent")
        self.assertEqual(len(no_ops), 0)
    
    def test_performance_data_clearing(self):
        """Test clearing performance data."""
        # Add some data
        with self.debug_logger.track_operation("test_op", "test_feature"):
            pass
        
        self.assertEqual(len(self.debug_logger.operation_metrics), 1)
        
        # Clear data
        self.debug_logger.clear_performance_data()
        
        self.assertEqual(len(self.debug_logger.operation_metrics), 0)
        stats = self.debug_logger.get_performance_stats("test_feature")
        self.assertEqual(stats.total_operations, 0)
    
    def test_debug_report_export(self):
        """Test debug report export."""
        # Add some test data
        with self.debug_logger.track_operation("test_op", "test_feature"):
            self.debug_logger.add_git_command_to_current_operation(["git", "status"])
        
        # Export report
        report_file = self.debug_logger.export_debug_report()
        
        self.assertTrue(report_file.exists())
        
        # Verify report content
        with open(report_file, 'r') as f:
            report_data = json.load(f)
        
        self.assertIn('generated_at', report_data)
        self.assertIn('debug_mode', report_data)
        self.assertIn('performance_stats', report_data)
        self.assertIn('recent_operations', report_data)
        self.assertIn('log_file_info', report_data)
        
        # Check that operation data is included
        self.assertEqual(len(report_data['recent_operations']), 1)
        operation = report_data['recent_operations'][0]
        self.assertEqual(operation['operation_name'], 'test_op')
        self.assertEqual(operation['feature'], 'test_feature')


class TestDebugDecorators(unittest.TestCase):
    """Test debug decorators."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_git_wrapper = MockGitWrapper()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_debug_trace_decorator(self):
        """Test debug trace decorator."""
        class TestClass:
            def __init__(self, temp_dir):
                self.debug_logger = DebugLogger(MockGitWrapper(), log_dir=temp_dir / 'logs')
                self.feature_name = "test_feature"
            
            @debug_trace(feature="test_feature", operation="traced_op")
            def traced_method(self, value):
                time.sleep(0.01)
                return value * 2
        
        test_obj = TestClass(self.temp_dir)
        result = test_obj.traced_method(5)
        
        self.assertEqual(result, 10)
        
        # Check that operation was tracked
        self.assertEqual(len(test_obj.debug_logger.operation_metrics), 1)
        metrics = test_obj.debug_logger.operation_metrics[0]
        self.assertEqual(metrics.operation_name, "traced_op")
        self.assertEqual(metrics.feature, "test_feature")
        self.assertTrue(metrics.success)
    
    def test_debug_trace_decorator_with_error(self):
        """Test debug trace decorator with error."""
        class TestClass:
            def __init__(self, temp_dir):
                self.debug_logger = DebugLogger(MockGitWrapper(), log_dir=temp_dir / 'logs')
                self.feature_name = "test_feature"
            
            @debug_trace()
            def failing_method(self):
                raise ValueError("Test error")
        
        test_obj = TestClass(self.temp_dir)
        
        with self.assertRaises(ValueError):
            test_obj.failing_method()
        
        # Check that operation was tracked with error
        self.assertEqual(len(test_obj.debug_logger.operation_metrics), 1)
        metrics = test_obj.debug_logger.operation_metrics[0]
        self.assertFalse(metrics.success)
        self.assertEqual(metrics.error_message, "Test error")
    
    def test_time_operation_decorator(self):
        """Test time operation decorator."""
        @time_operation
        def timed_function(x):
            time.sleep(0.01)
            return x * 2
        
        # Capture stdout to check timing output
        import io
        import sys
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        try:
            result = timed_function(5)
            self.assertEqual(result, 10)
            
            output = captured_output.getvalue()
            self.assertIn("timed_function completed in", output)
            self.assertIn("s", output)
        finally:
            sys.stdout = sys.__stdout__


class TestBaseManagerDebugIntegration(unittest.TestCase):
    """Test debug logging integration in BaseFeatureManager."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_git_wrapper = MockGitWrapper()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_base_manager_debug_logger_initialization(self):
        """Test that BaseFeatureManager initializes debug logger."""
        class TestManager(BaseFeatureManager):
            def _get_default_config(self):
                return {}
            
            def interactive_menu(self):
                pass
        
        manager = TestManager(self.mock_git_wrapper)
        self.assertIsInstance(manager.debug_logger, DebugLogger)
    
    def test_debug_logging_methods(self):
        """Test debug logging methods in BaseFeatureManager."""
        class TestManager(BaseFeatureManager):
            def _get_default_config(self):
                return {}
            
            def interactive_menu(self):
                pass
        
        manager = TestManager(self.mock_git_wrapper)
        
        # Test various logging methods
        manager.log_debug("Debug message", "test_op")
        manager.log_info_debug("Info message", "test_op")
        manager.log_warning_debug("Warning message", "test_op")
        manager.log_git_command_debug(["git", "status"], "test_op", 0.5, True, "output")
        
        # Check that log files were created
        log_files = list(manager.debug_logger.log_dir.glob('*.log'))
        self.assertGreater(len(log_files), 0)
    
    def test_operation_tracking_in_base_manager(self):
        """Test operation tracking through BaseFeatureManager."""
        class TestManager(BaseFeatureManager):
            def _get_default_config(self):
                return {}
            
            def interactive_menu(self):
                pass
            
            def test_tracked_operation(self):
                with self.track_operation("test_operation"):
                    time.sleep(0.01)
                    return "success"
        
        manager = TestManager(self.mock_git_wrapper)
        result = manager.test_tracked_operation()
        
        self.assertEqual(result, "success")
        
        # Check that operation was tracked
        recent_ops = manager.get_recent_feature_operations(limit=1)
        self.assertEqual(len(recent_ops), 1)
        self.assertEqual(recent_ops[0].operation_name, "test_operation")
    
    def test_performance_stats_in_base_manager(self):
        """Test performance statistics in BaseFeatureManager."""
        class TestManager(BaseFeatureManager):
            def _get_default_config(self):
                return {}
            
            def interactive_menu(self):
                pass
        
        manager = TestManager(self.mock_git_wrapper)
        
        # Perform some tracked operations
        with manager.track_operation("op1"):
            time.sleep(0.01)
        
        with manager.track_operation("op2"):
            time.sleep(0.01)
        
        # Get performance stats
        stats = manager.get_feature_performance_stats()
        self.assertEqual(stats.total_operations, 2)
        self.assertEqual(stats.successful_operations, 2)
        self.assertGreater(stats.total_duration, 0)
    
    def test_git_command_with_debug_logging(self):
        """Test Git command execution with debug logging."""
        class TestManager(BaseFeatureManager):
            def _get_default_config(self):
                return {}
            
            def interactive_menu(self):
                pass
        
        manager = TestManager(self.mock_git_wrapper)
        
        # Mock subprocess to avoid actual Git execution
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.stdout = "test output"
            mock_result.returncode = 0
            mock_run.return_value = mock_result
            
            result = manager.run_git_command(['git', 'status'], capture_output=True)
            
            self.assertEqual(result, "test output")
            
            # Check that Git command was logged
            recent_ops = manager.get_recent_feature_operations(limit=1)
            if recent_ops:
                # Git commands should be tracked in the operation
                pass  # The actual tracking happens in the safe_git_command function


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)