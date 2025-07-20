#!/usr/bin/env python3
"""
Debug Logger - Advanced Logging and Debugging Support

This module provides comprehensive logging and debugging capabilities including:
- Configurable logging levels and output formats
- Debug mode with detailed operation tracing
- Performance monitoring and profiling
- Log file management and rotation
- Interactive debugging tools
- Operation timing and metrics
"""

import logging
import logging.handlers
import time
import json
import sys
import traceback
import functools
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from enum import Enum


class LogLevel(Enum):
    """Logging levels with descriptions."""
    DEBUG = ("DEBUG", "Detailed information for debugging")
    INFO = ("INFO", "General information about program execution")
    WARNING = ("WARNING", "Warning messages for potential issues")
    ERROR = ("ERROR", "Error messages for failures")
    CRITICAL = ("CRITICAL", "Critical errors that may cause program termination")


@dataclass
class OperationMetrics:
    """Metrics for a single operation."""
    operation_name: str
    feature: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    memory_usage: Optional[int] = None
    git_commands: List[str] = None
    
    def __post_init__(self):
        if self.git_commands is None:
            self.git_commands = []
    
    def finish(self, success: bool = True, error_message: str = None):
        """Mark operation as finished."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success
        self.error_message = error_message


@dataclass
class PerformanceStats:
    """Performance statistics for operations."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_duration: float = 0.0
    average_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    git_commands_executed: int = 0
    
    def update(self, metrics: OperationMetrics):
        """Update stats with new operation metrics."""
        self.total_operations += 1
        
        if metrics.success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
        
        if metrics.duration:
            self.total_duration += metrics.duration
            self.average_duration = self.total_duration / self.total_operations
            self.min_duration = min(self.min_duration, metrics.duration)
            self.max_duration = max(self.max_duration, metrics.duration)
        
        self.git_commands_executed += len(metrics.git_commands)


class DebugLogger:
    """
    Advanced logging and debugging system.
    
    Provides comprehensive logging, debugging, and performance monitoring
    capabilities for all Git Wrapper features.
    """
    
    def __init__(self, git_wrapper, log_dir: Path = None):
        """
        Initialize the DebugLogger.
        
        Args:
            git_wrapper: Reference to the main InteractiveGitWrapper instance
            log_dir: Directory for log files (defaults to ~/.gitwrapper/logs)
        """
        self.git_wrapper = git_wrapper
        self.config = git_wrapper.config
        
        # Setup logging directory
        self.log_dir = log_dir or Path.home() / '.gitwrapper' / 'logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logging configuration
        self._load_logging_config()
        self._setup_loggers()
        
        # Performance tracking
        self.operation_metrics: List[OperationMetrics] = []
        self.performance_stats: Dict[str, PerformanceStats] = {}
        self.active_operations: Dict[str, OperationMetrics] = {}
        
        # Debug mode state
        self.debug_mode = self.config.get('debug_logging', {}).get('enable_debug_mode', False)
        self.trace_operations = self.config.get('debug_logging', {}).get('trace_operations', False)
        self.profile_performance = self.config.get('debug_logging', {}).get('profile_performance', False)
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Initialize performance stats for known features
        self._init_performance_stats()
    
    def _load_logging_config(self) -> None:
        """Load logging configuration with defaults."""
        default_config = {
            'log_level': 'INFO',
            'enable_debug_mode': False,
            'trace_operations': False,
            'profile_performance': False,
            'max_log_files': 10,
            'max_log_size_mb': 10,
            'console_logging': False,
            'detailed_git_logging': True,
            'operation_timing': True,
            'memory_monitoring': False,
            'log_format': 'detailed',  # 'simple', 'detailed', 'json'
            'auto_cleanup_days': 30
        }
        
        if 'debug_logging' not in self.config:
            self.config['debug_logging'] = default_config
        else:
            # Merge with defaults
            for key, value in default_config.items():
                if key not in self.config['debug_logging']:
                    self.config['debug_logging'][key] = value
    
    def _setup_loggers(self) -> None:
        """Setup logging configuration with multiple loggers."""
        log_config = self.config.get('debug_logging', {})
        
        # Create formatters
        formatters = self._create_formatters()
        
        # Setup main application logger
        self.app_logger = self._setup_logger(
            'gitwrapper.app',
            self.log_dir / 'application.log',
            formatters['detailed'],
            log_config.get('log_level', 'INFO')
        )
        
        # Setup debug logger (only active in debug mode)
        if log_config.get('enable_debug_mode', False):
            self.debug_logger = self._setup_logger(
                'gitwrapper.debug',
                self.log_dir / 'debug.log',
                formatters['detailed'],
                'DEBUG'
            )
        else:
            self.debug_logger = None
        
        # Setup performance logger
        if log_config.get('profile_performance', False):
            self.perf_logger = self._setup_logger(
                'gitwrapper.performance',
                self.log_dir / 'performance.log',
                formatters['json'] if log_config.get('log_format') == 'json' else formatters['simple'],
                'INFO'
            )
        else:
            self.perf_logger = None
        
        # Setup Git command logger
        if log_config.get('detailed_git_logging', True):
            self.git_logger = self._setup_logger(
                'gitwrapper.git',
                self.log_dir / 'git_commands.log',
                formatters['simple'],
                'DEBUG' if log_config.get('enable_debug_mode') else 'INFO'
            )
        else:
            self.git_logger = None
        
        # Setup console logger if enabled
        if log_config.get('console_logging', False):
            self.console_logger = self._setup_console_logger(formatters['simple'])
        else:
            self.console_logger = None
    
    def _create_formatters(self) -> Dict[str, logging.Formatter]:
        """Create different log formatters."""
        formatters = {}
        
        # Simple formatter
        formatters['simple'] = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Detailed formatter
        formatters['detailed'] = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # JSON formatter (custom)
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno
                }
                if record.exc_info:
                    log_entry['exception'] = self.formatException(record.exc_info)
                return json.dumps(log_entry)
        
        formatters['json'] = JsonFormatter()
        
        return formatters
    
    def _setup_logger(self, name: str, log_file: Path, formatter: logging.Formatter, 
                     level: str) -> logging.Logger:
        """Setup a specific logger with file handler."""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create rotating file handler
        max_size = self.config.get('debug_logging', {}).get('max_log_size_mb', 10) * 1024 * 1024
        backup_count = self.config.get('debug_logging', {}).get('max_log_files', 10)
        
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _setup_console_logger(self, formatter: logging.Formatter) -> logging.Logger:
        """Setup console logger."""
        logger = logging.getLogger('gitwrapper.console')
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _init_performance_stats(self) -> None:
        """Initialize performance statistics for known features."""
        features = [
            'stashmanager', 'committemplateengine', 'branchworkflowmanager',
            'conflictresolver', 'repositoryhealthdashboard', 'smartbackupsystem'
        ]
        
        for feature in features:
            self.performance_stats[feature] = PerformanceStats()
    
    # Logging Methods
    
    def log_info(self, message: str, feature: str = None, operation: str = None, 
                extra_data: Dict[str, Any] = None) -> None:
        """Log an info message."""
        formatted_message = self._format_log_message(message, feature, operation, extra_data)
        self.app_logger.info(formatted_message)
        
        if self.console_logger:
            self.console_logger.info(formatted_message)
    
    def log_debug(self, message: str, feature: str = None, operation: str = None,
                 extra_data: Dict[str, Any] = None) -> None:
        """Log a debug message."""
        if not self.debug_mode:
            return
        
        formatted_message = self._format_log_message(message, feature, operation, extra_data)
        
        if self.debug_logger:
            self.debug_logger.debug(formatted_message)
    
    def log_warning(self, message: str, feature: str = None, operation: str = None,
                   extra_data: Dict[str, Any] = None) -> None:
        """Log a warning message."""
        formatted_message = self._format_log_message(message, feature, operation, extra_data)
        self.app_logger.warning(formatted_message)
        
        if self.console_logger:
            self.console_logger.warning(formatted_message)
    
    def log_error(self, message: str, feature: str = None, operation: str = None,
                 exception: Exception = None, extra_data: Dict[str, Any] = None) -> None:
        """Log an error message."""
        formatted_message = self._format_log_message(message, feature, operation, extra_data)
        
        if exception:
            self.app_logger.error(formatted_message, exc_info=exception)
        else:
            self.app_logger.error(formatted_message)
        
        if self.console_logger:
            self.console_logger.error(formatted_message)
    
    def log_git_command(self, command: List[str], feature: str = None, operation: str = None,
                       duration: float = None, success: bool = True, output: str = None) -> None:
        """Log a Git command execution."""
        if not self.git_logger:
            return
        
        command_str = ' '.join(command)
        context = f"[{feature}:{operation}]" if feature and operation else ""
        
        if duration is not None:
            status = "SUCCESS" if success else "FAILED"
            message = f"{context} {status} ({duration:.3f}s): {command_str}"
        else:
            message = f"{context} EXEC: {command_str}"
        
        if output and self.debug_mode:
            message += f" -> {output[:200]}{'...' if len(output) > 200 else ''}"
        
        self.git_logger.info(message)
    
    def log_performance(self, metrics: OperationMetrics) -> None:
        """Log performance metrics."""
        if not self.perf_logger:
            return
        
        if self.config.get('debug_logging', {}).get('log_format') == 'json':
            self.perf_logger.info(json.dumps(asdict(metrics)))
        else:
            message = (f"PERF [{metrics.feature}:{metrics.operation_name}] "
                      f"Duration: {metrics.duration:.3f}s, "
                      f"Success: {metrics.success}, "
                      f"Git Commands: {len(metrics.git_commands)}")
            self.perf_logger.info(message)
    
    def _format_log_message(self, message: str, feature: str = None, operation: str = None,
                           extra_data: Dict[str, Any] = None) -> str:
        """Format a log message with context."""
        context_parts = []
        
        if feature:
            context_parts.append(f"[{feature}]")
        if operation:
            context_parts.append(f"({operation})")
        
        context = " ".join(context_parts)
        formatted_message = f"{context} {message}" if context else message
        
        if extra_data and self.debug_mode:
            formatted_message += f" | Data: {json.dumps(extra_data, default=str)}"
        
        return formatted_message
    
    # Operation Tracking and Performance Monitoring
    
    @contextmanager
    def track_operation(self, operation_name: str, feature: str):
        """Context manager for tracking operation performance."""
        operation_id = f"{feature}:{operation_name}:{time.time()}"
        
        metrics = OperationMetrics(
            operation_name=operation_name,
            feature=feature,
            start_time=time.time()
        )
        
        with self._lock:
            self.active_operations[operation_id] = metrics
        
        self.log_debug(f"Starting operation: {operation_name}", feature, operation_name)
        
        try:
            yield metrics
            metrics.finish(success=True)
            self.log_debug(f"Operation completed successfully: {operation_name} ({metrics.duration:.3f}s)", 
                          feature, operation_name)
        except Exception as e:
            metrics.finish(success=False, error_message=str(e))
            self.log_error(f"Operation failed: {operation_name} ({metrics.duration:.3f}s): {str(e)}", 
                          feature, operation_name, exception=e)
            raise
        finally:
            with self._lock:
                if operation_id in self.active_operations:
                    del self.active_operations[operation_id]
                
                self.operation_metrics.append(metrics)
                
                # Update performance stats
                if feature not in self.performance_stats:
                    self.performance_stats[feature] = PerformanceStats()
                self.performance_stats[feature].update(metrics)
                
                # Log performance if enabled
                if self.profile_performance:
                    self.log_performance(metrics)
    
    def add_git_command_to_current_operation(self, command: List[str]) -> None:
        """Add a Git command to the currently active operation."""
        if not self.active_operations:
            return
        
        command_str = ' '.join(command)
        
        with self._lock:
            for metrics in self.active_operations.values():
                metrics.git_commands.append(command_str)
    
    def get_performance_stats(self, feature: str = None) -> Union[PerformanceStats, Dict[str, PerformanceStats]]:
        """Get performance statistics."""
        with self._lock:
            if feature:
                return self.performance_stats.get(feature, PerformanceStats())
            else:
                return self.performance_stats.copy()
    
    def get_recent_operations(self, limit: int = 50, feature: str = None) -> List[OperationMetrics]:
        """Get recent operation metrics."""
        with self._lock:
            operations = self.operation_metrics[-limit:] if limit else self.operation_metrics
            
            if feature:
                operations = [op for op in operations if op.feature == feature]
            
            return operations.copy()
    
    def clear_performance_data(self) -> None:
        """Clear all performance data."""
        with self._lock:
            self.operation_metrics.clear()
            for stats in self.performance_stats.values():
                stats.__init__()  # Reset to default values
    
    # Debug Mode Controls
    
    def enable_debug_mode(self) -> None:
        """Enable debug mode."""
        self.debug_mode = True
        self.config['debug_logging']['enable_debug_mode'] = True
        
        # Setup debug logger if not already done
        if not self.debug_logger:
            formatters = self._create_formatters()
            self.debug_logger = self._setup_logger(
                'gitwrapper.debug',
                self.log_dir / 'debug.log',
                formatters['detailed'],
                'DEBUG'
            )
        
        self.log_info("Debug mode enabled")
    
    def disable_debug_mode(self) -> None:
        """Disable debug mode."""
        self.debug_mode = False
        self.config['debug_logging']['enable_debug_mode'] = False
        self.log_info("Debug mode disabled")
    
    def enable_operation_tracing(self) -> None:
        """Enable detailed operation tracing."""
        self.trace_operations = True
        self.config['debug_logging']['trace_operations'] = True
        self.log_info("Operation tracing enabled")
    
    def disable_operation_tracing(self) -> None:
        """Disable operation tracing."""
        self.trace_operations = False
        self.config['debug_logging']['trace_operations'] = False
        self.log_info("Operation tracing disabled")
    
    def enable_performance_profiling(self) -> None:
        """Enable performance profiling."""
        self.profile_performance = True
        self.config['debug_logging']['profile_performance'] = True
        
        # Setup performance logger if not already done
        if not self.perf_logger:
            formatters = self._create_formatters()
            log_config = self.config.get('debug_logging', {})
            self.perf_logger = self._setup_logger(
                'gitwrapper.performance',
                self.log_dir / 'performance.log',
                formatters['json'] if log_config.get('log_format') == 'json' else formatters['simple'],
                'INFO'
            )
        
        self.log_info("Performance profiling enabled")
    
    def disable_performance_profiling(self) -> None:
        """Disable performance profiling."""
        self.profile_performance = False
        self.config['debug_logging']['profile_performance'] = False
        self.log_info("Performance profiling disabled")
    
    # Log Management
    
    def rotate_logs(self) -> None:
        """Manually rotate all log files."""
        for logger_name in ['gitwrapper.app', 'gitwrapper.debug', 'gitwrapper.performance', 'gitwrapper.git']:
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers:
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    handler.doRollover()
        
        self.log_info("Log files rotated")
    
    def cleanup_old_logs(self, days: int = None) -> int:
        """Clean up old log files."""
        if days is None:
            days = self.config.get('debug_logging', {}).get('auto_cleanup_days', 30)
        
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        cleaned_count = 0
        
        for log_file in self.log_dir.glob('*.log*'):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    cleaned_count += 1
            except OSError:
                pass  # Skip files we can't access
        
        self.log_info(f"Cleaned up {cleaned_count} old log files (older than {days} days)")
        return cleaned_count
    
    def get_log_file_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about log files."""
        log_info = {}
        
        for log_file in self.log_dir.glob('*.log*'):
            try:
                stat = log_file.stat()
                log_info[log_file.name] = {
                    'size_mb': stat.st_size / (1024 * 1024),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'lines': self._count_lines(log_file) if log_file.suffix == '.log' else None
                }
            except OSError:
                log_info[log_file.name] = {'error': 'Cannot access file'}
        
        return log_info
    
    def _count_lines(self, file_path: Path) -> int:
        """Count lines in a text file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except:
            return 0
    
    # Export and Reporting
    
    def export_debug_report(self, output_file: Path = None, include_logs: bool = False) -> Path:
        """
        Export comprehensive debug report.
        
        Args:
            output_file: Path to output file (defaults to timestamped file)
            include_logs: Whether to include recent log entries
            
        Returns:
            Path to the generated report file
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.log_dir / f"debug_report_{timestamp}.json"
        
        report_data = {
            'generated_at': datetime.now().isoformat(),
            'debug_mode': self.debug_mode,
            'trace_operations': self.trace_operations,
            'profile_performance': self.profile_performance,
            'configuration': self.config.get('debug_logging', {}),
            'performance_stats': {
                feature: asdict(stats) for feature, stats in self.performance_stats.items()
            },
            'recent_operations': [
                asdict(op) for op in self.get_recent_operations(limit=100)
            ],
            'log_file_info': self.get_log_file_info(),
            'active_operations': len(self.active_operations)
        }
        
        if include_logs:
            report_data['recent_logs'] = self._get_recent_log_entries(limit=500)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.log_info(f"Debug report exported to {output_file}")
            return output_file
        except Exception as e:
            self.log_error(f"Failed to export debug report: {str(e)}")
            raise
    
    def _get_recent_log_entries(self, limit: int = 500) -> List[str]:
        """Get recent log entries from the main log file."""
        main_log = self.log_dir / 'application.log'
        if not main_log.exists():
            return []
        
        try:
            with open(main_log, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                return [line.strip() for line in lines[-limit:]]
        except:
            return []


def debug_trace(feature: str = None, operation: str = None):
    """
    Decorator for automatic operation tracing and performance monitoring.
    
    Args:
        feature: Name of the feature
        operation: Name of the operation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get debug logger from the instance
            debug_logger = getattr(self, 'debug_logger', None)
            if not debug_logger or not isinstance(debug_logger, DebugLogger):
                # Fallback: just execute the function
                return func(self, *args, **kwargs)
            
            feature_name = feature or getattr(self, 'feature_name', self.__class__.__name__)
            operation_name = operation or func.__name__
            
            with debug_logger.track_operation(operation_name, feature_name) as metrics:
                result = func(self, *args, **kwargs)
                return result
        
        return wrapper
    return decorator


def time_operation(func: Callable) -> Callable:
    """Simple decorator to time function execution."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            print(f"⏱️  {func.__name__} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            print(f"⏱️  {func.__name__} failed after {duration:.3f}s: {str(e)}")
            raise
    
    return wrapper