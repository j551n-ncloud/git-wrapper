#!/usr/bin/env python3
"""
Timeout Handler - Manage timeouts for long-running operations

This module provides utilities for handling timeouts in long-running operations,
particularly Git commands that might hang or take too long to complete.
"""

import signal
import time
import threading
import subprocess
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class TimeoutError(Exception):
    """Exception raised when an operation times out."""
    
    def __init__(self, message: str, command: List[str] = None, timeout: int = None):
        super().__init__(message)
        self.message = message
        self.command = command
        self.timeout = timeout


class TimeoutHandler:
    """
    Utility for handling timeouts in long-running operations.
    
    Provides mechanisms to execute operations with timeouts and
    handle timeout situations gracefully.
    """
    
    def __init__(self, error_handler=None):
        """
        Initialize the TimeoutHandler.
        
        Args:
            error_handler: Optional error handler for logging timeout errors
        """
        self.error_handler = error_handler
        self.default_timeout = 60  # Default timeout in seconds
    
    def run_with_timeout(self, func: Callable, args: List = None, kwargs: Dict = None, 
                        timeout: int = None) -> Any:
        """
        Run a function with a timeout.
        
        Args:
            func: Function to run
            args: Arguments to pass to the function
            kwargs: Keyword arguments to pass to the function
            timeout: Timeout in seconds (None for no timeout)
            
        Returns:
            Result of the function
            
        Raises:
            TimeoutError: If the function times out
        """
        if timeout is None:
            timeout = self.default_timeout
        
        args = args or []
        kwargs = kwargs or {}
        
        result = [None]
        error = [None]
        completed = [False]
        
        def target():
            try:
                result[0] = func(*args, **kwargs)
                completed[0] = True
            except Exception as e:
                error[0] = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            # Operation timed out
            error_message = f"Operation timed out after {timeout} seconds"
            
            if self.error_handler:
                self.error_handler.log_error(
                    error_message,
                    feature="timeout_handler",
                    operation="run_with_timeout"
                )
            
            raise TimeoutError(error_message, timeout=timeout)
        
        if error[0]:
            # Re-raise any exception that occurred in the thread
            raise error[0]
        
        return result[0]
    
    def run_subprocess_with_timeout(self, cmd: List[str], timeout: int = None, 
                                  capture_output: bool = False, **kwargs) -> subprocess.CompletedProcess:
        """
        Run a subprocess command with a timeout.
        
        Args:
            cmd: Command to run as a list of strings
            timeout: Timeout in seconds (None for no timeout)
            capture_output: Whether to capture stdout and stderr
            **kwargs: Additional arguments to pass to subprocess.run
            
        Returns:
            CompletedProcess instance
            
        Raises:
            TimeoutError: If the command times out
            subprocess.SubprocessError: For other subprocess errors
        """
        if timeout is None:
            timeout = self.default_timeout
        
        try:
            # Use subprocess.run with built-in timeout
            return subprocess.run(
                cmd,
                timeout=timeout,
                capture_output=capture_output,
                text=True,
                **kwargs
            )
        except subprocess.TimeoutExpired as e:
            # Command timed out
            error_message = f"Command timed out after {timeout} seconds: {' '.join(cmd)}"
            
            # Generate specific troubleshooting suggestions based on the command
            suggestions = self._generate_timeout_suggestions(cmd, timeout)
            
            if self.error_handler:
                self.error_handler.log_error(
                    error_message,
                    feature="timeout_handler",
                    operation="run_subprocess_with_timeout"
                )
                
                # Log suggestions for troubleshooting
                for suggestion in suggestions:
                    self.error_handler.log_info(
                        f"Suggestion: {suggestion}",
                        feature="timeout_handler",
                        operation="timeout_suggestions"
                    )
            
            # Try to kill the process if it's still running
            try:
                # This is a best effort to clean up, but the process might already be gone
                # due to how subprocess.run handles timeouts internally
                if hasattr(e, 'args') and len(e.args) > 1:
                    # Try to terminate the process if we have access to it
                    pass
            except:
                pass
            
            # Create enhanced timeout error with suggestions
            timeout_error = TimeoutError(error_message, command=cmd, timeout=timeout)
            timeout_error.suggestions = suggestions
            raise timeout_error
    
    def set_default_timeout(self, timeout: int) -> None:
        """
        Set the default timeout for operations.
        
        Args:
            timeout: Default timeout in seconds
        """
        self.default_timeout = timeout
    
    def get_recommended_timeout(self, operation_type: str, repo_size: int = None) -> int:
        """
        Get a recommended timeout based on operation type and repository size.
        
        Args:
            operation_type: Type of operation (e.g., 'clone', 'push', 'pull')
            repo_size: Repository size in MB (if known)
            
        Returns:
            Recommended timeout in seconds
        """
        # Base timeouts for different operation types
        base_timeouts = {
            'status': 10,
            'log': 15,
            'branch': 10,
            'checkout': 30,
            'commit': 20,
            'add': 30,
            'clone': 300,  # 5 minutes
            'push': 180,   # 3 minutes
            'pull': 180,   # 3 minutes
            'fetch': 120,  # 2 minutes
            'merge': 60,
            'rebase': 120,
            'gc': 300,     # 5 minutes
            'fsck': 300,   # 5 minutes
            'default': 60  # 1 minute
        }
        
        # Get base timeout for the operation type
        timeout = base_timeouts.get(operation_type, base_timeouts['default'])
        
        # Adjust based on repository size if provided
        if repo_size:
            # For large repositories (>1GB), increase timeout
            if repo_size > 1000:  # >1GB
                timeout *= 3
            # For medium repositories (100MB-1GB), slightly increase timeout
            elif repo_size > 100:
                timeout *= 2
        
        return timeout
    
    def _generate_timeout_suggestions(self, cmd: List[str], timeout: int) -> List[str]:
        """
        Generate specific troubleshooting suggestions for timeout errors.
        
        Args:
            cmd: The command that timed out
            timeout: The timeout value that was used
            
        Returns:
            List of troubleshooting suggestions
        """
        suggestions = []
        
        if not cmd:
            return suggestions
        
        command_name = cmd[0] if cmd else ""
        operation = cmd[1] if len(cmd) > 1 else ""
        
        # General suggestions
        suggestions.append(f"The operation timed out after {timeout} seconds")
        suggestions.append("Check your network connection if this is a network operation")
        
        # Git-specific suggestions
        if "git" in command_name.lower():
            if operation in ['clone', 'fetch', 'pull', 'push']:
                suggestions.extend([
                    "Network operations can be slow with large repositories",
                    "Try using --depth 1 for shallow clones to reduce download size",
                    "Check if the remote repository is accessible",
                    "Consider using a different network connection or VPN"
                ])
            elif operation in ['gc', 'fsck', 'repack']:
                suggestions.extend([
                    "Repository maintenance operations can take time with large repositories",
                    "Consider running these operations during off-peak hours",
                    "Check available disk space - low space can slow operations"
                ])
            elif operation in ['merge', 'rebase']:
                suggestions.extend([
                    "Complex merges with many conflicts can take time",
                    "Consider breaking large merges into smaller chunks",
                    "Check if there are uncommitted changes that need to be stashed"
                ])
            elif operation == 'log':
                suggestions.extend([
                    "Large repository history can slow log operations",
                    "Try limiting the log with --max-count or date ranges",
                    "Use --oneline for faster log display"
                ])
            else:
                suggestions.extend([
                    "Try running the Git command directly to see if it completes",
                    "Check if the repository is corrupted with 'git fsck'",
                    "Ensure you have sufficient permissions for the operation"
                ])
        
        # System-level suggestions
        suggestions.extend([
            "Check system resources (CPU, memory, disk space)",
            "Close other resource-intensive applications",
            "Try increasing the timeout if this operation normally takes longer"
        ])
        
        # Repository-specific suggestions
        if len(cmd) > 2:
            # Look for repository paths or URLs in the command
            for arg in cmd[2:]:
                if '://' in arg or arg.startswith('/') or '\\' in arg:
                    suggestions.extend([
                        "Verify the repository path or URL is correct and accessible",
                        "Check file system permissions for local repositories"
                    ])
                    break
        
        return suggestions


# Context manager for timeout operations
class timeout_context:
    """
    Context manager for executing code with a timeout.
    
    Example:
        ```python
        try:
            with timeout_context(5):  # 5 second timeout
                # Code that might hang
                result = long_running_operation()
        except TimeoutError:
            print("Operation timed out")
        ```
    """
    
    def __init__(self, seconds: Union[int, float], error_message: str = "Operation timed out"):
        self.seconds = int(seconds)  # Convert to integer for signal.alarm
        self.error_message = error_message
        self.timer = None
    
    def _timeout_handler(self, signum, frame):
        raise TimeoutError(self.error_message, timeout=self.seconds)
    
    def __enter__(self):
        if self.seconds > 0:
            # Set the timeout handler
            signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(self.seconds)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cancel the timeout
        signal.alarm(0)
        # Don't suppress exceptions
        return False


# Decorator for adding timeouts to functions
def with_timeout(timeout: int = None, operation_type: str = None):
    """
    Decorator for adding timeout to functions.
    
    Args:
        timeout: Timeout in seconds (None to use default)
        operation_type: Type of operation for dynamic timeout calculation
        
    Example:
        ```python
        @with_timeout(30)  # 30 second timeout
        def fetch_remote_data(self, remote):
            # Long-running operation
            pass
            
        @with_timeout(operation_type='clone')  # Dynamic timeout based on operation type
        def clone_repository(self, url, path):
            # Long-running clone operation
            pass
        ```
    """
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get or create timeout handler
            timeout_handler = getattr(self, 'timeout_handler', None)
            if not timeout_handler:
                error_handler = getattr(self, 'error_handler', None)
                timeout_handler = TimeoutHandler(error_handler)
            
            # Determine actual timeout to use
            actual_timeout = timeout
            if actual_timeout is None and operation_type:
                # Get repository size if available
                repo_size = None
                if hasattr(self, 'get_repository_size'):
                    try:
                        repo_size = self.get_repository_size()
                    except:
                        pass
                
                actual_timeout = timeout_handler.get_recommended_timeout(operation_type, repo_size)
            elif actual_timeout is None:
                actual_timeout = timeout_handler.default_timeout
            
            # Run the function with timeout
            try:
                return timeout_handler.run_with_timeout(func, [self] + list(args), kwargs, actual_timeout)
            except TimeoutError as e:
                # Get print_error method if available
                print_error = getattr(self, 'print_error', None)
                if print_error and callable(print_error):
                    print_error(f"Operation timed out after {actual_timeout} seconds")
                
                # Re-raise the exception
                raise
        
        return wrapper
    
    return decorator