#!/usr/bin/env python3
"""
Base Manager Class for Advanced Git Features

This module provides the base functionality that all feature managers inherit from.
It includes common Git operations, configuration management, and user interface helpers.

The BaseFeatureManager is an abstract base class that defines the interface and common
functionality for all feature managers. Each feature manager should inherit from this
class and implement the required abstract methods.

Example:
    ```python
    from features.base_manager import BaseFeatureManager
    
    class MyFeatureManager(BaseFeatureManager):
        def __init__(self, git_wrapper):
            super().__init__(git_wrapper)
            # Feature-specific initialization
            
        def _get_default_config(self) -> Dict[str, Any]:
            return {
                'my_setting': True,
                'another_setting': 'default_value'
            }
            
        def interactive_menu(self) -> None:
            self.show_feature_header("My Feature")
            # Menu implementation
    ```

Attributes:
    git_wrapper: Reference to the main InteractiveGitWrapper instance
    feature_name: Name of the feature (derived from class name)
    config: Reference to the global configuration
    error_handler: Error handling utility
    debug_logger: Debug logging utility
"""

import subprocess
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from abc import ABC, abstractmethod
from features.error_handler import ErrorHandler, error_handler_decorator, safe_git_command
from features.debug_logger import DebugLogger, debug_trace
from features.input_validator import InputValidator, validate_input
from features.timeout_handler import TimeoutHandler, with_timeout, timeout_context
from features.safe_file_operations import SafeFileOperations
from features.git_command_executor import GitCommandExecutor, GitCommandConfig


class BaseFeatureManager(ABC):
    """
    Base class for all advanced Git feature managers.
    
    This abstract base class provides common functionality for all feature managers,
    ensuring consistent behavior and reducing code duplication. Feature managers
    should inherit from this class and implement the required abstract methods.
    
    Provides common functionality including:
    - Git command execution and repository operations
    - Configuration management and persistence
    - User interface helpers and formatting
    - Error handling and recovery
    - File operations and JSON handling
    - Debug logging and performance tracking
    - Help system integration
    
    The class follows a modular design pattern where each feature manager is
    responsible for a specific set of functionality while sharing common
    infrastructure through this base class.
    """
    
    def __init__(self, git_wrapper):
        """
        Initialize the base feature manager.
        
        This constructor sets up the common infrastructure for all feature managers,
        including configuration, error handling, and logging. It also initializes
        the feature name based on the class name for consistent identification.
        
        Args:
            git_wrapper: Reference to the main InteractiveGitWrapper instance
                         that provides access to core Git functionality
        
        Note:
            Subclasses should call super().__init__(git_wrapper) before
            performing their own initialization.
        """
        self.git_wrapper = git_wrapper
        self.feature_name = self.__class__.__name__.replace('Manager', '').replace('Engine', '').replace('Dashboard', '').replace('System', '').lower()
        self.config = git_wrapper.config
        
        # Initialize error handler
        self.error_handler = ErrorHandler(git_wrapper)
        
        # Initialize debug logger
        self.debug_logger = DebugLogger(git_wrapper)
        
        # Initialize input validator
        self.input_validator = InputValidator(self.error_handler)
        
        # Initialize timeout handler
        self.timeout_handler = TimeoutHandler(self.error_handler)
        
        # Initialize safe file operations
        self.safe_file_ops = SafeFileOperations(self.error_handler)
        
        # Initialize Git command executor
        self.git_executor = GitCommandExecutor(
            error_handler=self.error_handler,
            timeout_handler=self.timeout_handler,
            input_validator=self.input_validator
        )
        
        # Initialize feature-specific configuration
        self._init_feature_config()
    
    def _init_feature_config(self):
        """Initialize feature-specific configuration with defaults."""
        if 'advanced_features' not in self.config:
            self.config['advanced_features'] = {}
        
        if self.feature_name not in self.config['advanced_features']:
            self.config['advanced_features'][self.feature_name] = self._get_default_config()
    
    @abstractmethod
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration for this feature.
        
        This abstract method must be implemented by all feature managers to provide
        default configuration values. These values are used when the feature is
        first initialized or when configuration is reset to defaults.
        
        Returns:
            Dictionary containing default configuration values for this feature
            
        Example:
            ```python
            def _get_default_config(self) -> Dict[str, Any]:
                return {
                    'setting_name': default_value,
                    'another_setting': another_default_value
                }
            ```
        """
        pass
    
    @abstractmethod
    def interactive_menu(self) -> None:
        """
        Display the interactive menu for this feature.
        
        This abstract method must be implemented by all feature managers to provide
        an interactive user interface for the feature. This is the main entry point
        for user interaction with the feature.
        
        The implementation should:
        1. Display a header using show_feature_header()
        2. Present menu options to the user
        3. Handle user input and execute corresponding actions
        4. Provide a way to return to the main menu
        
        Example:
            ```python
            def interactive_menu(self) -> None:
                self.show_feature_header("My Feature")
                
                options = ["Option 1", "Option 2", "Back to Main Menu"]
                
                while True:
                    for i, option in enumerate(options, 1):
                        print(f"{i}. {option}")
                        
                    try:
                        choice = int(input("Enter choice: "))
                        if choice == len(options):  # Back option
                            return
                        elif 1 <= choice < len(options):
                            # Handle the selected option
                            pass
                        else:
                            self.print_error("Invalid choice")
                    except ValueError:
                        self.print_error("Please enter a number")
            ```
        """
        pass
    
    # Git Command Execution Methods
    
    def run_git_command(self, cmd: List[str], capture_output: bool = False, 
                       show_output: bool = True, cwd: Optional[str] = None,
                       timeout: int = None, operation_type: str = None,
                       retry_count: int = 1) -> Union[str, bool]:
        """
        Run a git command with comprehensive error handling and logging.
        
        This method provides a safe way to execute Git commands with proper error
        handling, logging, and performance tracking. It uses the error_handler and
        debug_logger to provide detailed information about command execution.
        
        Args:
            cmd: Git command as list of strings (e.g., ['git', 'status'])
            capture_output: Whether to capture and return command output as string
            show_output: Whether to show command output to user
            cwd: Working directory for command execution (defaults to current directory)
            timeout: Timeout in seconds (None for default timeout)
            operation_type: Type of operation for dynamic timeout calculation
            retry_count: Number of times to retry on failure (default: 1, no retry)
            
        Returns:
            If capture_output is True, returns command output as string.
            Otherwise, returns boolean indicating success (True) or failure (False).
            
        Example:
            ```python
            # Run command and show output
            success = self.run_git_command(['git', 'status'])
            
            # Run command and capture output
            branch = self.run_git_command(['git', 'branch', '--show-current'], 
                                         capture_output=True)
            
            # Run command in specific directory without showing output
            success = self.run_git_command(['git', 'init'], 
                                         show_output=False, 
                                         cwd='/path/to/directory')
                                         
            # Run command with timeout and retry
            success = self.run_git_command(['git', 'pull', 'origin', 'main'],
                                         timeout=120,
                                         retry_count=3)
            ```
        """
        start_time = time.time()
        
        # Sanitize command arguments for security
        sanitized_cmd = [cmd[0]]  # Keep the git command itself
        for arg in cmd[1:]:
            if isinstance(arg, str):
                # Only sanitize string arguments
                sanitized_cmd.append(self.input_validator.sanitize_shell_input(arg))
            else:
                sanitized_cmd.append(arg)
        
        # Log the command execution
        self.log_debug(f"Executing Git command: {' '.join(str(c) for c in sanitized_cmd)}", 
                      "git_command", {"cwd": cwd})
        
        # Determine timeout to use
        if timeout is None and operation_type:
            # Get repository size if available for dynamic timeout calculation
            repo_size = None
            try:
                if hasattr(self, 'get_repository_size'):
                    repo_size = self.get_repository_size()
            except:
                pass
            
            timeout = self.timeout_handler.get_recommended_timeout(operation_type, repo_size)
        
        # Execute with retry logic
        attempt = 0
        last_error = None
        
        while attempt < retry_count:
            try:
                # Run the command with timeout
                result = self.timeout_handler.run_subprocess_with_timeout(
                    cmd=sanitized_cmd,
                    timeout=timeout,
                    capture_output=capture_output,
                    text=True,
                    check=True,
                    cwd=cwd
                )
                
                # Process the result
                if capture_output:
                    output = result.stdout.strip()
                    success = True
                else:
                    output = None
                    success = True
                
                # Log the result
                duration = time.time() - start_time
                self.log_git_command_debug(sanitized_cmd, "git_command", duration, success, output)
                
                if success:
                    self.log_debug(f"Git command completed successfully in {duration:.3f}s", "git_command")
                
                return output if capture_output else True
                
            except subprocess.TimeoutExpired:
                attempt += 1
                last_error = f"Command timed out after {timeout} seconds"
                self.log_error(f"Git command timed out: {' '.join(str(c) for c in sanitized_cmd)}", 
                              "git_command")
                
                if attempt < retry_count:
                    self.log_warning(f"Retrying command (attempt {attempt+1}/{retry_count})...", 
                                   "git_command")
                    time.sleep(1)  # Brief pause before retry
                
            except subprocess.CalledProcessError as e:
                attempt += 1
                last_error = f"Command failed with exit code {e.returncode}: {e.stderr}"
                self.log_error(f"Git command failed: {' '.join(str(c) for c in sanitized_cmd)}", 
                              "git_command")
                
                if attempt < retry_count:
                    self.log_warning(f"Retrying command (attempt {attempt+1}/{retry_count})...", 
                                   "git_command")
                    time.sleep(1)  # Brief pause before retry
                
            except Exception as e:
                attempt += 1
                last_error = str(e)
                self.log_error(f"Error executing Git command: {' '.join(str(c) for c in sanitized_cmd)}: {str(e)}", 
                              "git_command")
                
                if attempt < retry_count:
                    self.log_warning(f"Retrying command (attempt {attempt+1}/{retry_count})...", 
                                   "git_command")
                    time.sleep(1)  # Brief pause before retry
        
        # All attempts failed
        duration = time.time() - start_time
        self.log_debug(f"Git command failed after {duration:.3f}s and {retry_count} attempts: {last_error}", 
                      "git_command")
        
        if show_output:
            self.print_error(f"Git command failed: {last_error}")
        
        return "" if capture_output else False
    
    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository."""
        try:
            subprocess.run(['git', 'rev-parse', '--git-dir'], 
                         capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def get_current_branch(self) -> Optional[str]:
        """Get the current branch name."""
        result = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        return result if result else None
    
    def get_remotes(self) -> List[str]:
        """Get list of configured remotes."""
        remotes_output = self.run_git_command(['git', 'remote'], capture_output=True)
        return remotes_output.split('\n') if remotes_output else []
    
    def get_branches(self, include_remote: bool = False) -> List[str]:
        """
        Get list of branches.
        
        Args:
            include_remote: Whether to include remote branches
            
        Returns:
            List of branch names
        """
        cmd = ['git', 'branch']
        if include_remote:
            cmd.append('-a')
        
        branches_output = self.run_git_command(cmd, capture_output=True)
        if not branches_output:
            return []
        
        branches = []
        for line in branches_output.split('\n'):
            branch = line.strip().replace('* ', '').replace('remotes/', '')
            if branch and not branch.startswith('HEAD ->'):
                branches.append(branch)
        
        return branches
    
    def get_git_root(self) -> Optional[Path]:
        """Get the root directory of the git repository."""
        try:
            result = self.run_git_command(['git', 'rev-parse', '--show-toplevel'], capture_output=True)
            return Path(result) if result else None
        except:
            return None
    
    # Configuration Management Methods
    
    def get_feature_config(self, key: str = None) -> Any:
        """
        Get feature-specific configuration.
        
        Retrieves configuration values specific to this feature from the global
        configuration. If key is None, returns the entire feature configuration.
        
        Args:
            key: Specific configuration key to retrieve, or None for entire config
            
        Returns:
            Configuration value for the specified key, or entire feature config if key is None.
            If the key doesn't exist, returns None.
            
        Example:
            ```python
            # Get entire feature config
            config = self.get_feature_config()
            
            # Get specific setting
            max_items = self.get_feature_config('max_items')
            
            # Use with default value
            show_preview = self.get_feature_config('show_preview') or True
            ```
        """
        feature_config = self.config.get('advanced_features', {}).get(self.feature_name, {})
        return feature_config.get(key) if key else feature_config
    
    def set_feature_config(self, key: str, value: Any) -> None:
        """
        Set feature-specific configuration.
        
        Args:
            key: Configuration key to set
            value: Value to set
        """
        if 'advanced_features' not in self.config:
            self.config['advanced_features'] = {}
        if self.feature_name not in self.config['advanced_features']:
            self.config['advanced_features'][self.feature_name] = {}
        
        self.config['advanced_features'][self.feature_name][key] = value
        self.git_wrapper.save_config()
    
    def update_feature_config(self, config_dict: Dict[str, Any]) -> None:
        """
        Update multiple feature configuration values.
        
        Args:
            config_dict: Dictionary of configuration key-value pairs
        """
        if 'advanced_features' not in self.config:
            self.config['advanced_features'] = {}
        if self.feature_name not in self.config['advanced_features']:
            self.config['advanced_features'][self.feature_name] = {}
        
        self.config['advanced_features'][self.feature_name].update(config_dict)
        self.git_wrapper.save_config()
    
    # File Operations Methods
    
    @error_handler_decorator(operation='load_json_file')
    def load_json_file(self, file_path: Path, default: Any = None) -> Any:
        """
        Load data from a JSON file with error handling.
        
        Args:
            file_path: Path to the JSON file
            default: Default value if file doesn't exist or is invalid
            
        Returns:
            Loaded data or default value
        """
        self.error_handler.log_debug(f"Loading JSON file: {file_path}")
        
        if not file_path.exists():
            self.error_handler.log_debug(f"JSON file does not exist: {file_path}")
            return default if default is not None else {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.error_handler.log_debug(f"Successfully loaded JSON file: {file_path}")
            return data
    
    @error_handler_decorator(operation='save_json_file')
    def save_json_file(self, file_path: Path, data: Any) -> bool:
        """
        Save data to a JSON file with error handling.
        
        Args:
            file_path: Path to save the JSON file
            data: Data to save
            
        Returns:
            True if successful, False otherwise
        """
        self.error_handler.log_debug(f"Saving JSON file: {file_path}")
        
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create atomic write by writing to temporary file first
        temp_file = file_path.with_suffix(file_path.suffix + '.tmp')
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Atomic move
        temp_file.replace(file_path)
        
        self.error_handler.log_debug(f"Successfully saved JSON file: {file_path}")
        return True
    
    @error_handler_decorator(operation='ensure_directory')
    def ensure_directory(self, directory: Path) -> bool:
        """
        Ensure a directory exists with error handling.
        
        Args:
            directory: Directory path to create
            
        Returns:
            True if directory exists or was created successfully
        """
        self.error_handler.log_debug(f"Ensuring directory exists: {directory}")
        
        directory.mkdir(parents=True, exist_ok=True)
        
        self.error_handler.log_debug(f"Directory ensured: {directory}")
        return True
    
    # User Interface Helper Methods
    
    def print_success(self, message: str) -> None:
        """Print a success message with emoji if enabled."""
        self.git_wrapper.print_success(message)
    
    def print_error(self, message: str) -> None:
        """Print an error message with emoji if enabled."""
        self.git_wrapper.print_error(message)
    
    def print_info(self, message: str) -> None:
        """Print an info message with emoji if enabled."""
        self.git_wrapper.print_info(message)
    
    def print_working(self, message: str) -> None:
        """Print a working message with emoji if enabled."""
        self.git_wrapper.print_working(message)
    
    def get_input(self, prompt: str, default: str = None) -> str:
        """Get user input with optional default value."""
        return self.git_wrapper.get_input(prompt, default)
    
    def get_choice(self, prompt: str, choices: List[str], default: str = None) -> str:
        """Get user choice from a list of options."""
        return self.git_wrapper.get_choice(prompt, choices, default)
    
    def get_multiple_choice(self, prompt: str, choices: List[str]) -> List[str]:
        """Get multiple user choices from a list of options."""
        return self.git_wrapper.get_multiple_choice(prompt, choices)
    
    def confirm(self, message: str, default: bool = True) -> bool:
        """Ask for user confirmation."""
        return self.git_wrapper.confirm(message, default)
    
    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        self.git_wrapper.clear_screen()
    
    # Utility Methods
    
    def format_timestamp(self, timestamp: float) -> str:
        """
        Format a timestamp for display.
        
        Args:
            timestamp: Unix timestamp
            
        Returns:
            Formatted timestamp string
        """
        import datetime
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    
    def get_file_size_mb(self, file_path: Path) -> float:
        """
        Get file size in megabytes.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File size in MB
        """
        try:
            return file_path.stat().st_size / (1024 * 1024)
        except OSError:
            return 0.0
    
    def validate_branch_name(self, branch_name: str) -> bool:
        """
        Validate a branch name according to Git rules.
        
        Args:
            branch_name: Branch name to validate
            
        Returns:
            True if valid, False otherwise
        """
        return self.input_validator.validate_branch_name(branch_name)
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename for safe file system usage.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        return self.input_validator.sanitize_filename(filename)
    
    def show_feature_header(self, title: str) -> None:
        """
        Show a formatted header for the feature.
        
        Args:
            title: Title to display
        """
        self.clear_screen()
        print("=" * 50)
        
        # Use emoji only if enabled
        rocket_emoji = "🚀 " if self.config.get('show_emoji', True) else ""
        print(f"{rocket_emoji}{title}")
        print("=" * 50)
        
        if self.is_git_repo():
            current_branch = self.get_current_branch()
            if current_branch:
                branch_emoji = "🌿 " if self.config.get('show_emoji', True) else ""
                print(f"{branch_emoji}Current Branch: {current_branch}")
            
            git_root = self.get_git_root()
            if git_root:
                folder_emoji = "📁 " if self.config.get('show_emoji', True) else ""
                print(f"{folder_emoji}Repository: {git_root.name}")
            
            print("-" * 50)
        else:
            self.print_error("Not in a Git repository!")
            print("-" * 50)
    
    def print_with_emoji(self, message: str, emoji: str = "") -> None:
        """
        Print a message with optional emoji based on configuration.
        
        Args:
            message: Message to print
            emoji: Emoji to use if enabled
        """
        if self.config.get('show_emoji', True) and emoji:
            print(f"{emoji} {message}")
        else:
            print(message)
    
    def format_with_emoji(self, message: str, emoji: str = "") -> str:
        """
        Format a message with optional emoji based on configuration.
        
        Args:
            message: Message to format
            emoji: Emoji to use if enabled
            
        Returns:
            Formatted message string
        """
        if self.config.get('show_emoji', True) and emoji:
            return f"{emoji} {message}"
        else:
            return message
    
    # Error Handling and Logging Methods
    
    def log_operation(self, operation: str, message: str, level: str = 'info') -> None:
        """
        Log an operation with appropriate level.
        
        Args:
            operation: Name of the operation
            message: Log message
            level: Log level (debug, info, warning, error)
        """
        log_method = getattr(self.error_handler, f'log_{level}', self.error_handler.log_info)
        log_method(message, feature=self.feature_name, operation=operation)
    
    def handle_operation_error(self, operation: str, error: Exception, 
                              context: Dict[str, Any] = None, auto_recover: bool = True) -> bool:
        """
        Handle an error that occurred during an operation.
        
        Args:
            operation: Name of the operation that failed
            error: The exception that occurred
            context: Additional context information
            auto_recover: Whether to attempt automatic recovery
            
        Returns:
            True if error was handled/recovered, False otherwise
        """
        return self.error_handler.handle_error(
            error=error,
            feature=self.feature_name,
            operation=operation,
            context=context,
            auto_recover=auto_recover
        )
    
    def safe_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """
        Execute an operation with comprehensive error handling.
        
        Args:
            operation_name: Name of the operation for logging
            operation_func: Function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Result of the operation or None if failed
        """
        try:
            self.log_operation(operation_name, f"Starting operation: {operation_name}")
            result = operation_func(*args, **kwargs)
            self.log_operation(operation_name, f"Operation completed successfully: {operation_name}")
            return result
        except Exception as e:
            self.handle_operation_error(operation_name, e)
            return None
    
    def validate_input(self, input_value: Any, validation_rules: Dict[str, Any], 
                      field_name: str = "input") -> bool:
        """
        Validate user input with comprehensive error reporting.
        
        Args:
            input_value: Value to validate
            validation_rules: Dictionary of validation rules
            field_name: Name of the field being validated
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Use the input validator for validation
            is_valid = self.input_validator.validate_input(input_value, validation_rules, field_name)
            
            # Display error message if validation failed
            if not is_valid:
                self.print_error(f"Invalid {field_name}")
            
            return is_valid
            
        except Exception as e:
            self.handle_operation_error('validate_input', e)
            return False
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for this feature."""
        return self.error_handler.get_error_statistics()
    
    def export_feature_logs(self, output_dir: Path = None) -> Path:
        """
        Export logs specific to this feature.
        
        Args:
            output_dir: Directory to save logs (defaults to error handler log directory)
            
        Returns:
            Path to exported log file
        """
        if output_dir is None:
            output_dir = self.error_handler.log_dir
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_file = output_dir / f"{self.feature_name}_logs_{timestamp}.txt"
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Feature Logs: {self.feature_name}\n")
                f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n\n")
                
                # Write recent errors for this feature
                feature_errors = [
                    error for error in self.error_handler.error_history
                    if error.get('feature') == self.feature_name
                ]
                
                if feature_errors:
                    f.write("Recent Errors:\n")
                    f.write("-" * 20 + "\n")
                    for error in feature_errors[-10:]:  # Last 10 errors
                        f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(error['timestamp']))}\n")
                        f.write(f"Operation: {error.get('operation', 'unknown')}\n")
                        f.write(f"Category: {error['category']}\n")
                        f.write(f"Severity: {error['severity']}\n")
                        f.write(f"Message: {error['message']}\n")
                        f.write("-" * 30 + "\n")
                else:
                    f.write("No errors recorded for this feature.\n")
            
            self.log_operation('export_logs', f"Feature logs exported to {log_file}")
            return log_file
            
        except Exception as e:
            self.handle_operation_error('export_logs', e)
            raise
    
    # Debug Logging Methods
    
    def log_debug(self, message: str, operation: str = None, extra_data: Dict[str, Any] = None) -> None:
        """Log a debug message."""
        self.debug_logger.log_debug(message, self.feature_name, operation, extra_data)
    
    def log_info_debug(self, message: str, operation: str = None, extra_data: Dict[str, Any] = None) -> None:
        """Log an info message through debug logger."""
        self.debug_logger.log_info(message, self.feature_name, operation, extra_data)
    
    def log_warning_debug(self, message: str, operation: str = None, extra_data: Dict[str, Any] = None) -> None:
        """Log a warning message through debug logger."""
        self.debug_logger.log_warning(message, self.feature_name, operation, extra_data)
    
    def log_git_command_debug(self, command: List[str], operation: str = None, 
                             duration: float = None, success: bool = True, output: str = None) -> None:
        """Log a Git command through debug logger."""
        self.debug_logger.log_git_command(command, self.feature_name, operation, duration, success, output)
        
        # Also add to current operation tracking
        self.debug_logger.add_git_command_to_current_operation(command)
    
    def track_operation(self, operation_name: str):
        """Get context manager for tracking operation performance."""
        return self.debug_logger.track_operation(operation_name, self.feature_name)
    
    def get_feature_performance_stats(self):
        """Get performance statistics for this feature."""
        return self.debug_logger.get_performance_stats(self.feature_name)
    
    def get_recent_feature_operations(self, limit: int = 20):
        """Get recent operations for this feature."""
        return self.debug_logger.get_recent_operations(limit, self.feature_name)
    
    def enable_debug_mode(self) -> None:
        """Enable debug mode for this feature."""
        self.debug_logger.enable_debug_mode()
        self.log_info_debug("Debug mode enabled for feature", "debug_control")
    
    def disable_debug_mode(self) -> None:
        """Disable debug mode for this feature."""
        self.debug_logger.disable_debug_mode()
        self.log_info_debug("Debug mode disabled for feature", "debug_control")
    
    def export_debug_report(self, output_file: Path = None) -> Path:
        """Export debug report for this feature."""
        return self.debug_logger.export_debug_report(output_file, include_logs=True)
    
    # Help System Methods
    
    def show_context_help(self) -> None:
        """
        Show context-sensitive help for this feature.
        
        This method provides help information specific to the current feature.
        Feature managers should override this method to provide detailed help
        content tailored to their functionality.
        
        The default implementation shows a basic help screen with the feature name
        and a generic description. Override this method to provide more detailed
        help content.
        
        Example implementation:
            ```python
            def show_context_help(self) -> None:
                self.clear_screen()
                print(f"❓ {self.feature_name.title()} Help\\n" + "=" * 30)
                print('''
Purpose:
[Detailed description of feature purpose]

Key Features:
- [Feature 1]
- [Feature 2]
- [Feature 3]

Main Operations:
[Description of main operations]

Configuration Options:
[Description of configuration options]

Best Practices:
[Best practices for using this feature]
''')
                input("\\nPress Enter to continue...")
            ```
        """
        self.clear_screen()
        print(f"❓ {self.feature_name.title()} Help\n" + "=" * 30)
        print(f"""
🎯 Feature: {self.feature_name.title()}

This feature provides advanced Git functionality.
For detailed help, please refer to the main help system.

💡 Quick Tips:
• Use the interactive menu to explore available options
• Most operations include confirmation prompts
• Use Ctrl+C to exit at any time
• Check configuration settings for customization options

🔧 Configuration:
Feature-specific settings can be found in the configuration menu.
        """)
        input("\nPress Enter to continue...")
    
    def get_help_content(self) -> Dict[str, str]:
        """
        Get help content for this feature.
        
        This method returns a dictionary containing help content for the feature,
        which can be used by the help system to display comprehensive documentation.
        Feature managers should override this method to provide detailed help content.
        
        Returns:
            Dictionary with help sections and content. The dictionary should contain
            at least the following keys:
            - 'overview': Brief description of the feature
            - 'usage': Basic usage instructions
            - 'tips': Tips for effective use
            
        Additional keys can be added for more detailed help sections.
        
        Example:
            ```python
            def get_help_content(self) -> Dict[str, str]:
                return {
                    'overview': "Feature description and purpose",
                    'usage': "Detailed usage instructions",
                    'tips': "Tips and best practices",
                    'examples': "Usage examples",
                    'configuration': "Configuration options",
                    'troubleshooting': "Common issues and solutions"
                }
            ```
        """
        return {
            'overview': f"Advanced {self.feature_name} functionality for Git operations",
            'usage': "Use the interactive menu to access feature options",
            'tips': "Check configuration settings for customization options"
        }