#!/usr/bin/env python3
"""
Error Handler - Comprehensive Error Handling and Logging

This module provides centralized error handling, logging, and recovery mechanisms
for all advanced Git features. It includes:
- Structured error handling with recovery suggestions
- Configurable logging with multiple levels
- Debug mode with detailed operation tracing
- Error recovery mechanisms
- User-friendly error messages
"""

import logging
import logging.handlers
import traceback
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from functools import wraps
from datetime import datetime, timedelta


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better classification."""
    GIT_COMMAND = "git_command"
    FILE_OPERATION = "file_operation"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    VALIDATION = "validation"
    USER_INPUT = "user_input"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class GitWrapperError(Exception):
    """Base exception class for Git Wrapper errors."""
    
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.UNKNOWN,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 suggestions: List[str] = None, recoverable: bool = True):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.suggestions = suggestions or []
        self.recoverable = recoverable
        self.timestamp = time.time()


class GitCommandError(GitWrapperError):
    """Exception for Git command failures."""
    
    def __init__(self, command: List[str], return_code: int, stderr: str = "",
                 suggestions: List[str] = None):
        message = f"Git command failed: {' '.join(command)}"
        if stderr:
            message += f"\nError: {stderr}"
        
        super().__init__(
            message=message,
            category=ErrorCategory.GIT_COMMAND,
            severity=ErrorSeverity.HIGH,
            suggestions=suggestions or self._generate_git_suggestions(command, return_code, stderr)
        )
        self.command = command
        self.return_code = return_code
        self.stderr = stderr
    
    def _generate_git_suggestions(self, command: List[str], return_code: int, stderr: str) -> List[str]:
        """Generate helpful suggestions based on Git command failure."""
        suggestions = []
        
        if "not a git repository" in stderr.lower():
            suggestions.extend([
                "Initialize a Git repository with 'git init'",
                "Navigate to a directory that contains a Git repository",
                "Clone an existing repository with 'git clone <url>'"
            ])
        elif "permission denied" in stderr.lower():
            suggestions.extend([
                "Check file and directory permissions",
                "Ensure you have write access to the repository",
                "Try running with appropriate permissions"
            ])
        elif "merge conflict" in stderr.lower():
            suggestions.extend([
                "Resolve merge conflicts manually",
                "Use the conflict resolution assistant",
                "Abort the merge with 'git merge --abort'"
            ])
        elif "nothing to commit" in stderr.lower():
            suggestions.extend([
                "Stage changes with 'git add <files>'",
                "Check repository status with 'git status'",
                "Ensure there are changes to commit"
            ])
        elif "remote" in ' '.join(command) and "not found" in stderr.lower():
            suggestions.extend([
                "Check remote configuration with 'git remote -v'",
                "Add the remote with 'git remote add <name> <url>'",
                "Verify the remote URL is correct"
            ])
        
        return suggestions


class FileOperationError(GitWrapperError):
    """Exception for file operation failures."""
    
    def __init__(self, operation: str, file_path: str, original_error: Exception):
        message = f"File operation '{operation}' failed for {file_path}: {str(original_error)}"
        
        super().__init__(
            message=message,
            category=ErrorCategory.FILE_OPERATION,
            severity=ErrorSeverity.MEDIUM,
            suggestions=self._generate_file_suggestions(operation, file_path, original_error)
        )
        self.operation = operation
        self.file_path = file_path
        self.original_error = original_error
    
    def _generate_file_suggestions(self, operation: str, file_path: str, error: Exception) -> List[str]:
        """Generate suggestions for file operation errors."""
        suggestions = []
        
        if "permission" in str(error).lower():
            suggestions.extend([
                f"Check permissions for {file_path}",
                "Ensure you have read/write access to the file",
                "Try running with elevated permissions if necessary"
            ])
        elif "not found" in str(error).lower() or "no such file" in str(error).lower():
            suggestions.extend([
                f"Verify that {file_path} exists",
                "Check the file path for typos",
                "Ensure the parent directory exists"
            ])
        elif "disk" in str(error).lower() or "space" in str(error).lower():
            suggestions.extend([
                "Check available disk space",
                "Clean up temporary files",
                "Try saving to a different location"
            ])
        
        return suggestions


class ErrorHandler:
    """
    Centralized error handling and logging system.
    
    Provides comprehensive error handling, logging, and recovery mechanisms
    for all Git Wrapper features.
    """
    
    def __init__(self, git_wrapper, log_dir: Path = None):
        """
        Initialize the ErrorHandler.
        
        Args:
            git_wrapper: Reference to the main InteractiveGitWrapper instance
            log_dir: Directory for log files (defaults to ~/.gitwrapper/logs)
        """
        self.git_wrapper = git_wrapper
        self.config = git_wrapper.config
        
        # Setup logging directory
        self.log_dir = log_dir or Path.home() / '.gitwrapper' / 'logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logging
        self._setup_logging()
        
        # Error tracking
        self.error_history = []
        self.recovery_attempts = {}
        
        # Load error handling configuration
        self._load_error_config()
    
    def _load_error_config(self) -> None:
        """Load error handling configuration with defaults."""
        default_config = {
            'log_level': 'INFO',
            'max_log_files': 10,
            'max_log_size_mb': 10,
            'enable_debug_mode': False,
            'auto_recovery': True,
            'max_recovery_attempts': 3,
            'show_stack_traces': False,
            'log_git_commands': True,
            'error_reporting': True
        }
        
        if 'error_handling' not in self.config:
            self.config['error_handling'] = default_config
        else:
            # Merge with defaults
            for key, value in default_config.items():
                if key not in self.config['error_handling']:
                    self.config['error_handling'][key] = value
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Setup main logger
        self.logger = logging.getLogger('gitwrapper')
        self.logger.setLevel(getattr(logging, self.config.get('error_handling', {}).get('log_level', 'INFO')))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler for general logs
        log_file = self.log_dir / 'gitwrapper.log'
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.config.get('error_handling', {}).get('max_log_size_mb', 10) * 1024 * 1024,
            backupCount=self.config.get('error_handling', {}).get('max_log_files', 10)
        )
        file_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(file_handler)
        
        # Error file handler for errors and above
        error_log_file = self.log_dir / 'errors.log'
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB for error logs
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(error_handler)
        
        # Debug file handler (only when debug mode is enabled)
        if self.config.get('error_handling', {}).get('enable_debug_mode', False):
            debug_log_file = self.log_dir / 'debug.log'
            debug_handler = logging.handlers.RotatingFileHandler(
                debug_log_file,
                maxBytes=20 * 1024 * 1024,  # 20MB for debug logs
                backupCount=3
            )
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(detailed_formatter)
            self.logger.addHandler(debug_handler)
        
        # Console handler for critical errors (optional)
        if self.config.get('error_handling', {}).get('show_stack_traces', False):
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(logging.ERROR)
            console_handler.setFormatter(simple_formatter)
            self.logger.addHandler(console_handler)
    
    def log_info(self, message: str, feature: str = None, operation: str = None) -> None:
        """Log an info message."""
        extra_info = self._build_log_context(feature, operation)
        self.logger.info(f"{extra_info}{message}")
    
    def log_warning(self, message: str, feature: str = None, operation: str = None) -> None:
        """Log a warning message."""
        extra_info = self._build_log_context(feature, operation)
        self.logger.warning(f"{extra_info}{message}")
    
    def log_error(self, message: str, feature: str = None, operation: str = None, 
                  exception: Exception = None) -> None:
        """Log an error message."""
        extra_info = self._build_log_context(feature, operation)
        
        if exception:
            self.logger.error(f"{extra_info}{message}", exc_info=exception)
        else:
            self.logger.error(f"{extra_info}{message}")
    
    def log_debug(self, message: str, feature: str = None, operation: str = None) -> None:
        """Log a debug message."""
        if self.config.get('error_handling', {}).get('enable_debug_mode', False):
            extra_info = self._build_log_context(feature, operation)
            self.logger.debug(f"{extra_info}{message}")
    
    def _build_log_context(self, feature: str = None, operation: str = None) -> str:
        """Build context information for log messages."""
        context_parts = []
        
        if feature:
            context_parts.append(f"[{feature}]")
        if operation:
            context_parts.append(f"({operation})")
        
        return " ".join(context_parts) + " " if context_parts else ""
    
    def handle_error(self, error: Exception, feature: str = None, operation: str = None,
                    context: Dict[str, Any] = None, auto_recover: bool = None) -> bool:
        """
        Handle an error with logging, user notification, and optional recovery.
        
        Args:
            error: The exception that occurred
            feature: Name of the feature where error occurred
            operation: Name of the operation that failed
            context: Additional context information
            auto_recover: Whether to attempt automatic recovery
            
        Returns:
            True if error was handled/recovered, False otherwise
        """
        # Convert to GitWrapperError if needed
        if not isinstance(error, GitWrapperError):
            error = self._convert_to_wrapper_error(error, feature, operation)
        
        # Log the error
        self.log_error(
            f"Error in {feature or 'unknown'}.{operation or 'unknown'}: {error.message}",
            feature=feature,
            operation=operation,
            exception=error
        )
        
        # Add to error history
        error_record = {
            'timestamp': error.timestamp,
            'feature': feature,
            'operation': operation,
            'category': error.category.value,
            'severity': error.severity.value,
            'message': error.message,
            'recoverable': error.recoverable,
            'context': context or {}
        }
        self.error_history.append(error_record)
        
        # Keep only last 100 errors in memory
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]
        
        # Display user-friendly error message
        self._display_error_to_user(error, feature, operation)
        
        # Attempt recovery if enabled and error is recoverable
        if auto_recover is None:
            auto_recover = self.config.get('error_handling', {}).get('auto_recovery', True)
        
        if auto_recover and error.recoverable:
            return self._attempt_recovery(error, feature, operation, context)
        
        return False
    
    def _convert_to_wrapper_error(self, error: Exception, feature: str = None, 
                                operation: str = None) -> GitWrapperError:
        """Convert a generic exception to a GitWrapperError."""
        error_type = type(error).__name__
        
        # Determine category based on error type and context
        category = ErrorCategory.UNKNOWN
        severity = ErrorSeverity.MEDIUM
        
        if isinstance(error, (FileNotFoundError, PermissionError, OSError)):
            category = ErrorCategory.FILE_OPERATION
        elif isinstance(error, (ConnectionError, TimeoutError)):
            category = ErrorCategory.NETWORK
        elif isinstance(error, (ValueError, TypeError)):
            category = ErrorCategory.VALIDATION
        elif "subprocess" in error_type.lower() or "git" in str(error).lower():
            category = ErrorCategory.GIT_COMMAND
            severity = ErrorSeverity.HIGH
        
        return GitWrapperError(
            message=f"{error_type}: {str(error)}",
            category=category,
            severity=severity,
            suggestions=self._generate_generic_suggestions(error, feature, operation)
        )
    
    def _generate_generic_suggestions(self, error: Exception, feature: str = None,
                                    operation: str = None) -> List[str]:
        """Generate generic suggestions for common errors."""
        suggestions = []
        error_str = str(error).lower()
        
        if "permission" in error_str:
            suggestions.extend([
                "Check file and directory permissions",
                "Ensure you have necessary access rights",
                "Try running with elevated permissions if needed"
            ])
        elif "not found" in error_str or "no such file" in error_str:
            suggestions.extend([
                "Verify the file or directory exists",
                "Check for typos in the path",
                "Ensure all parent directories exist"
            ])
        elif "network" in error_str or "connection" in error_str:
            suggestions.extend([
                "Check your internet connection",
                "Verify remote URLs are correct",
                "Try again after a few moments"
            ])
        elif "timeout" in error_str:
            suggestions.extend([
                "The operation took too long to complete",
                "Check your network connection",
                "Try with a smaller dataset or simpler operation"
            ])
        
        # Add feature-specific suggestions
        if feature:
            suggestions.extend(self._get_feature_specific_suggestions(feature, operation, error))
        
        return suggestions
    
    def _get_feature_specific_suggestions(self, feature: str, operation: str = None,
                                        error: Exception = None) -> List[str]:
        """Get feature-specific error suggestions."""
        suggestions = []
        
        if feature.lower() == 'stashmanager':
            suggestions.extend([
                "Ensure you have uncommitted changes to stash",
                "Check if the stash exists before applying",
                "Verify repository is in a clean state"
            ])
        elif feature.lower() == 'committemplateengine':
            suggestions.extend([
                "Check template syntax and required fields",
                "Ensure staged changes exist before committing",
                "Verify template file permissions"
            ])
        elif feature.lower() == 'branchworkflowmanager':
            suggestions.extend([
                "Ensure you're on the correct base branch",
                "Check for uncommitted changes",
                "Verify remote tracking is set up correctly"
            ])
        elif feature.lower() == 'conflictresolver':
            suggestions.extend([
                "Ensure merge conflicts exist before resolving",
                "Check that all conflicts are properly marked",
                "Verify editor configuration is correct"
            ])
        elif feature.lower() == 'repositoryhealthdashboard':
            suggestions.extend([
                "Ensure repository has sufficient history",
                "Check file system permissions for analysis",
                "Verify Git repository is not corrupted"
            ])
        elif feature.lower() == 'smartbackupsystem':
            suggestions.extend([
                "Check backup remote configuration",
                "Verify network connectivity to backup destinations",
                "Ensure sufficient storage space for backups"
            ])
        
        return suggestions
    
    def _display_error_to_user(self, error: GitWrapperError, feature: str = None,
                              operation: str = None) -> None:
        """Display user-friendly error message."""
        # Use emoji based on configuration
        show_emoji = self.config.get('show_emoji', True)
        
        # Choose emoji based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            emoji = "🚨" if show_emoji else ""
        elif error.severity == ErrorSeverity.HIGH:
            emoji = "❌" if show_emoji else ""
        elif error.severity == ErrorSeverity.MEDIUM:
            emoji = "⚠️" if show_emoji else ""
        else:
            emoji = "ℹ️" if show_emoji else ""
        
        # Display main error message
        if hasattr(self.git_wrapper, 'print_error'):
            self.git_wrapper.print_error(f"{emoji} {error.message}")
        else:
            print(f"{emoji} Error: {error.message}")
        
        # Display suggestions if available
        if error.suggestions:
            suggestion_emoji = "💡" if show_emoji else ""
            print(f"\n{suggestion_emoji} Suggestions:")
            for i, suggestion in enumerate(error.suggestions[:5], 1):  # Limit to 5 suggestions
                print(f"  {i}. {suggestion}")
        
        # Show recovery options if error is recoverable
        if error.recoverable:
            recovery_emoji = "🔧" if show_emoji else ""
            print(f"\n{recovery_emoji} This error may be recoverable. Attempting automatic recovery...")
    
    def _attempt_recovery(self, error: GitWrapperError, feature: str = None,
                         operation: str = None, context: Dict[str, Any] = None) -> bool:
        """
        Attempt to recover from an error.
        
        Args:
            error: The error to recover from
            feature: Feature where error occurred
            operation: Operation that failed
            context: Additional context for recovery
            
        Returns:
            True if recovery was successful, False otherwise
        """
        recovery_key = f"{feature}.{operation}.{error.category.value}"
        
        # Check if we've already attempted recovery for this error type
        if recovery_key in self.recovery_attempts:
            attempts = self.recovery_attempts[recovery_key]
            max_attempts = self.config.get('error_handling', {}).get('max_recovery_attempts', 3)
            
            if attempts >= max_attempts:
                self.log_warning(f"Max recovery attempts ({max_attempts}) reached for {recovery_key}")
                return False
        else:
            self.recovery_attempts[recovery_key] = 0
        
        self.recovery_attempts[recovery_key] += 1
        
        self.log_info(f"Attempting recovery for {recovery_key} (attempt {self.recovery_attempts[recovery_key]})")
        
        # Attempt category-specific recovery
        recovery_success = False
        
        if error.category == ErrorCategory.GIT_COMMAND:
            recovery_success = self._recover_git_command_error(error, context)
        elif error.category == ErrorCategory.FILE_OPERATION:
            recovery_success = self._recover_file_operation_error(error, context)
        elif error.category == ErrorCategory.CONFIGURATION:
            recovery_success = self._recover_configuration_error(error, context)
        elif error.category == ErrorCategory.NETWORK:
            recovery_success = self._recover_network_error(error, context)
        
        if recovery_success:
            self.log_info(f"Recovery successful for {recovery_key}")
            # Reset recovery attempts on success
            self.recovery_attempts[recovery_key] = 0
        else:
            self.log_warning(f"Recovery failed for {recovery_key}")
        
        return recovery_success
    
    def _recover_git_command_error(self, error: GitCommandError, context: Dict[str, Any] = None) -> bool:
        """Attempt to recover from Git command errors."""
        if not isinstance(error, GitCommandError):
            return False
        
        command = error.command
        stderr = error.stderr.lower()
        
        # Recovery strategies for common Git errors
        if "not a git repository" in stderr:
            # Try to initialize repository if in empty directory
            try:
                import subprocess
                subprocess.run(['git', 'init'], check=True, capture_output=True)
                self.log_info("Initialized new Git repository for recovery")
                return True
            except:
                return False
        
        elif "nothing to commit" in stderr and 'commit' in command:
            # Try to stage changes first
            try:
                import subprocess
                subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
                self.log_info("Staged changes for recovery")
                return True
            except:
                return False
        
        elif "merge conflict" in stderr:
            # For merge conflicts, we can't auto-recover, but we can provide guidance
            self.log_info("Merge conflict detected - manual resolution required")
            return False
        
        return False
    
    def _recover_file_operation_error(self, error: FileOperationError, context: Dict[str, Any] = None) -> bool:
        """Attempt to recover from file operation errors."""
        if not isinstance(error, FileOperationError):
            return False
        
        file_path = Path(error.file_path)
        
        # Try to create parent directories if they don't exist
        if "no such file or directory" in str(error.original_error).lower():
            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                self.log_info(f"Created parent directories for {file_path}")
                return True
            except:
                return False
        
        # Try to fix permissions if possible
        elif "permission denied" in str(error.original_error).lower():
            try:
                # Try to make file writable (basic attempt)
                if file_path.exists():
                    import stat
                    current_mode = file_path.stat().st_mode
                    file_path.chmod(current_mode | stat.S_IWUSR)
                    self.log_info(f"Fixed permissions for {file_path}")
                    return True
            except:
                return False
        
        return False
    
    def _recover_configuration_error(self, error: GitWrapperError, context: Dict[str, Any] = None) -> bool:
        """Attempt to recover from configuration errors."""
        # Try to reset to default configuration
        try:
            if hasattr(self.git_wrapper, 'load_config'):
                # Create backup of current config
                config_backup = self.git_wrapper.config.copy()
                
                # Reset to defaults and try to save
                self.git_wrapper.config = self.git_wrapper._get_default_config()
                if hasattr(self.git_wrapper, 'save_config'):
                    self.git_wrapper.save_config()
                
                self.log_info("Reset configuration to defaults for recovery")
                return True
        except:
            return False
        
        return False
    
    def _recover_network_error(self, error: GitWrapperError, context: Dict[str, Any] = None) -> bool:
        """Attempt to recover from network errors."""
        # For network errors, we can try a simple retry after a delay
        try:
            import time
            time.sleep(2)  # Wait 2 seconds before retry
            self.log_info("Waited for network recovery")
            return True  # Return True to indicate retry is possible
        except:
            return False
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and trends."""
        if not self.error_history:
            return {'total_errors': 0}
        
        # Calculate statistics
        total_errors = len(self.error_history)
        
        # Group by category
        category_counts = {}
        severity_counts = {}
        feature_counts = {}
        
        recent_errors = []
        one_hour_ago = time.time() - 3600
        
        for error in self.error_history:
            # Category counts
            category = error['category']
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Severity counts
            severity = error['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Feature counts
            feature = error.get('feature', 'unknown')
            feature_counts[feature] = feature_counts.get(feature, 0) + 1
            
            # Recent errors
            if error['timestamp'] > one_hour_ago:
                recent_errors.append(error)
        
        return {
            'total_errors': total_errors,
            'recent_errors_count': len(recent_errors),
            'category_breakdown': category_counts,
            'severity_breakdown': severity_counts,
            'feature_breakdown': feature_counts,
            'most_common_category': max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else None,
            'most_problematic_feature': max(feature_counts.items(), key=lambda x: x[1])[0] if feature_counts else None
        }
    
    def export_error_report(self, output_file: Path = None) -> Path:
        """
        Export detailed error report to file.
        
        Args:
            output_file: Path to output file (defaults to timestamped file in log directory)
            
        Returns:
            Path to the generated report file
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.log_dir / f"error_report_{timestamp}.json"
        
        report_data = {
            'generated_at': datetime.now().isoformat(),
            'statistics': self.get_error_statistics(),
            'error_history': self.error_history[-50:],  # Last 50 errors
            'recovery_attempts': self.recovery_attempts,
            'configuration': self.config.get('error_handling', {}),
            'log_files': [str(f) for f in self.log_dir.glob('*.log')]
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            self.log_info(f"Error report exported to {output_file}")
            return output_file
        except Exception as e:
            self.log_error(f"Failed to export error report: {str(e)}")
            raise
    
    def clear_error_history(self) -> None:
        """Clear error history and reset recovery attempts."""
        self.error_history.clear()
        self.recovery_attempts.clear()
        self.log_info("Cleared error history and recovery attempts")
    
    def configure_logging(self, log_level: str = None, enable_debug: bool = None,
                         max_log_size_mb: int = None) -> None:
        """
        Update logging configuration.
        
        Args:
            log_level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            enable_debug: Whether to enable debug mode
            max_log_size_mb: Maximum log file size in MB
        """
        config_updated = False
        
        if log_level:
            self.config['error_handling']['log_level'] = log_level.upper()
            config_updated = True
        
        if enable_debug is not None:
            self.config['error_handling']['enable_debug_mode'] = enable_debug
            config_updated = True
        
        if max_log_size_mb:
            self.config['error_handling']['max_log_size_mb'] = max_log_size_mb
            config_updated = True
        
        if config_updated:
            # Reconfigure logging
            self._setup_logging()
            self.log_info("Logging configuration updated")
            
            # Save configuration
            if hasattr(self.git_wrapper, 'save_config'):
                self.git_wrapper.save_config()


def error_handler_decorator(feature: str = None, operation: str = None, 
                          auto_recover: bool = None):
    """
    Decorator for automatic error handling in feature methods.
    
    Args:
        feature: Name of the feature
        operation: Name of the operation
        auto_recover: Whether to attempt automatic recovery
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                # Get error handler from the instance
                error_handler = getattr(self, 'error_handler', None)
                if error_handler and isinstance(error_handler, ErrorHandler):
                    handled = error_handler.handle_error(
                        error=e,
                        feature=feature or getattr(self, 'feature_name', self.__class__.__name__),
                        operation=operation or func.__name__,
                        auto_recover=auto_recover
                    )
                    
                    if not handled:
                        # Re-raise if not handled
                        raise
                else:
                    # Fallback: just re-raise
                    raise
        
        return wrapper
    return decorator


def safe_git_command(error_handler: ErrorHandler, command: List[str], 
                    feature: str = None, operation: str = None,
                    capture_output: bool = False, show_output: bool = True,
                    cwd: Optional[str] = None) -> Union[str, bool]:
    """
    Execute a Git command with comprehensive error handling.
    
    Args:
        error_handler: ErrorHandler instance
        command: Git command as list of strings
        feature: Name of the feature calling this command
        operation: Name of the operation
        capture_output: Whether to capture and return output
        show_output: Whether to show output to user
        cwd: Working directory for command execution
        
    Returns:
        Command output as string if capture_output=True, otherwise boolean success status
    """
    import subprocess
    
    try:
        # Log the command if enabled
        if error_handler.config.get('error_handling', {}).get('log_git_commands', True):
            error_handler.log_debug(f"Executing Git command: {' '.join(command)}", feature, operation)
        
        if capture_output:
            result = subprocess.run(command, capture_output=True, text=True, check=True, cwd=cwd)
            error_handler.log_debug(f"Git command output: {result.stdout[:200]}...", feature, operation)
            return result.stdout.strip()
        else:
            if show_output:
                subprocess.run(command, check=True, cwd=cwd)
            else:
                subprocess.run(command, capture_output=True, check=True, cwd=cwd)
            error_handler.log_debug("Git command completed successfully", feature, operation)
            return True
            
    except subprocess.CalledProcessError as e:
        # Create specific Git command error
        git_error = GitCommandError(
            command=command,
            return_code=e.returncode,
            stderr=e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
        )
        
        # Handle the error
        handled = error_handler.handle_error(
            error=git_error,
            feature=feature,
            operation=operation,
            context={'command': command, 'cwd': cwd}
        )
        
        if handled:
            # Retry the command once after recovery
            try:
                if capture_output:
                    result = subprocess.run(command, capture_output=True, text=True, check=True, cwd=cwd)
                    return result.stdout.strip()
                else:
                    if show_output:
                        subprocess.run(command, check=True, cwd=cwd)
                    else:
                        subprocess.run(command, capture_output=True, check=True, cwd=cwd)
                    return True
            except subprocess.CalledProcessError:
                # Recovery didn't work, return failure
                pass
        
        return False if not capture_output else ""
    
    except Exception as e:
        # Handle other exceptions
        error_handler.handle_error(
            error=e,
            feature=feature,
            operation=operation,
            context={'command': command, 'cwd': cwd}
        )
        return False if not capture_output else ""