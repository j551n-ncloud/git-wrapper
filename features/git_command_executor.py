#!/usr/bin/env python3
"""
Git Command Executor - Enhanced Git command execution with security and reliability

This module provides enhanced Git command execution with:
- Proper shell escaping for all arguments
- Command execution timeouts to prevent hanging
- Retry mechanisms for transient failures
- Detailed error handling with context
- Security validation for Git commands
"""

import subprocess
import shlex
import time
import os
import signal
from pathlib import Path
from typing import List, Dict, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum


class GitCommandResult:
    """Result of a Git command execution."""
    
    def __init__(self, success: bool, stdout: str = "", stderr: str = "", 
                 return_code: int = 0, execution_time: float = 0.0):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code
        self.execution_time = execution_time


class RetryStrategy(Enum):
    """Retry strategies for failed commands."""
    NONE = "none"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    CUSTOM = "custom"


@dataclass
class GitCommandConfig:
    """Configuration for Git command execution."""
    timeout: Optional[int] = None
    retry_count: int = 1
    retry_strategy: RetryStrategy = RetryStrategy.LINEAR
    retry_delay: float = 1.0
    max_retry_delay: float = 10.0
    capture_output: bool = True
    show_output: bool = False
    working_directory: Optional[Union[str, Path]] = None
    environment: Optional[Dict[str, str]] = None
    shell_escape: bool = True
    validate_command: bool = True


class GitCommandExecutor:
    """
    Enhanced Git command executor with security and reliability features.
    
    Provides secure and reliable execution of Git commands with proper
    shell escaping, timeout handling, and retry mechanisms.
    """
    
    def __init__(self, error_handler=None, timeout_handler=None, input_validator=None):
        """
        Initialize the Git command executor.
        
        Args:
            error_handler: Optional error handler for logging
            timeout_handler: Optional timeout handler for command timeouts
            input_validator: Optional input validator for command validation
        """
        self.error_handler = error_handler
        self.timeout_handler = timeout_handler
        self.input_validator = input_validator
        
        # Default configuration
        self.default_config = GitCommandConfig()
        
        # Command execution statistics
        self.stats = {
            'total_commands': 0,
            'successful_commands': 0,
            'failed_commands': 0,
            'retried_commands': 0,
            'total_execution_time': 0.0
        }
    
    def execute(self, command: List[str], config: Optional[GitCommandConfig] = None) -> GitCommandResult:
        """
        Execute a Git command with enhanced security and reliability.
        
        Args:
            command: Git command as list of strings
            config: Optional configuration for command execution
            
        Returns:
            GitCommandResult with execution details
        """
        if config is None:
            config = self.default_config
        
        start_time = time.time()
        self.stats['total_commands'] += 1
        
        try:
            # Validate the command
            if config.validate_command and not self._validate_git_command(command):
                return GitCommandResult(
                    success=False,
                    stderr="Invalid or potentially dangerous Git command",
                    return_code=-1,
                    execution_time=time.time() - start_time
                )
            
            # Prepare the command with proper escaping
            prepared_command = self._prepare_command(command, config)
            
            # Execute with retry logic
            result = self._execute_with_retry(prepared_command, config)
            
            # Update statistics
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            self.stats['total_execution_time'] += execution_time
            
            if result.success:
                self.stats['successful_commands'] += 1
            else:
                self.stats['failed_commands'] += 1
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.stats['failed_commands'] += 1
            self.stats['total_execution_time'] += execution_time
            
            if self.error_handler:
                self.error_handler.log_error(f"Git command execution error: {str(e)}")
            
            return GitCommandResult(
                success=False,
                stderr=str(e),
                return_code=-1,
                execution_time=execution_time
            )
    
    def _validate_git_command(self, command: List[str]) -> bool:
        """
        Validate that a Git command is safe to execute.
        
        Args:
            command: Git command to validate
            
        Returns:
            True if command is safe, False otherwise
        """
        if not command or not isinstance(command, list):
            return False
        
        # First argument should be git
        if not command[0] or 'git' not in command[0].lower():
            return False
        
        # Check for dangerous options
        dangerous_options = [
            '--exec',
            '--upload-pack',
            '--receive-pack',
            '--ssh-command'  # Can be used to execute arbitrary commands
        ]
        
        for arg in command[1:]:
            if isinstance(arg, str):
                for dangerous in dangerous_options:
                    if arg == dangerous or arg.startswith(dangerous + '='):
                        return False
        
        # Additional validation using input validator if available
        if self.input_validator:
            for arg in command[1:]:
                if isinstance(arg, str):
                    # Check for shell injection patterns
                    if not self._is_safe_argument(arg):
                        return False
        
        return True
    
    def _is_safe_argument(self, arg: str) -> bool:
        """
        Check if an argument is safe from shell injection.
        
        Args:
            arg: Argument to check
            
        Returns:
            True if safe, False otherwise
        """
        # Check for command injection patterns
        dangerous_patterns = [
            ';', '&&', '||', '|', '`', '$(',  # Command separators and substitution
            '$(', '${', '`',  # Command/variable substitution
            '>', '>>', '<',   # Redirection (in most contexts)
            '&', '#',         # Background execution and comments
            '\n', '\r',       # Line breaks
            '\x00'            # Null bytes
        ]
        
        # Allow some patterns in specific contexts (like URLs)
        if '://' in arg:  # Likely a URL
            # URLs can contain some characters that would otherwise be dangerous
            url_safe_patterns = ['&', '#']  # These are safe in URL context
            dangerous_patterns = [p for p in dangerous_patterns if p not in url_safe_patterns]
        
        return not any(pattern in arg for pattern in dangerous_patterns)
    
    def _prepare_command(self, command: List[str], config: GitCommandConfig) -> List[str]:
        """
        Prepare a command for execution with proper escaping.
        
        Args:
            command: Original command
            config: Execution configuration
            
        Returns:
            Prepared command with proper escaping
        """
        if not config.shell_escape:
            return command
        
        prepared = []
        
        for i, arg in enumerate(command):
            if isinstance(arg, str):
                if i == 0:
                    # Don't escape the git command itself
                    prepared.append(arg)
                else:
                    # Escape other arguments for shell safety
                    if self.input_validator:
                        escaped = self.input_validator.sanitize_shell_input(arg)
                    else:
                        escaped = shlex.quote(arg)
                    prepared.append(escaped)
            else:
                prepared.append(str(arg))
        
        return prepared
    
    def _execute_with_retry(self, command: List[str], config: GitCommandConfig) -> GitCommandResult:
        """
        Execute a command with retry logic.
        
        Args:
            command: Command to execute
            config: Execution configuration
            
        Returns:
            GitCommandResult with execution details
        """
        last_result = None
        
        for attempt in range(config.retry_count):
            try:
                result = self._execute_single(command, config)
                
                if result.success:
                    return result
                
                last_result = result
                
                # Check if this is a retryable error
                if attempt < config.retry_count - 1 and self._is_retryable_error(result):
                    self.stats['retried_commands'] += 1
                    
                    # Calculate retry delay
                    delay = self._calculate_retry_delay(attempt, config)
                    
                    if self.error_handler:
                        self.error_handler.log_info(
                            f"Retrying Git command in {delay} seconds (attempt {attempt + 2}/{config.retry_count})"
                        )
                    
                    time.sleep(delay)
                    continue
                else:
                    break
                    
            except Exception as e:
                last_result = GitCommandResult(
                    success=False,
                    stderr=str(e),
                    return_code=-1
                )
                
                if attempt < config.retry_count - 1:
                    delay = self._calculate_retry_delay(attempt, config)
                    time.sleep(delay)
                    continue
                else:
                    break
        
        return last_result or GitCommandResult(success=False, stderr="Unknown error")
    
    def _execute_single(self, command: List[str], config: GitCommandConfig) -> GitCommandResult:
        """
        Execute a single command attempt.
        
        Args:
            command: Command to execute
            config: Execution configuration
            
        Returns:
            GitCommandResult with execution details
        """
        # Prepare subprocess arguments
        subprocess_args = {
            'capture_output': config.capture_output,
            'text': True,
            'check': False  # We'll handle return codes ourselves
        }
        
        # Set working directory if specified
        if config.working_directory:
            subprocess_args['cwd'] = str(config.working_directory)
        
        # Set environment if specified
        if config.environment:
            env = os.environ.copy()
            env.update(config.environment)
            subprocess_args['env'] = env
        
        # Set timeout
        timeout = config.timeout
        if timeout is None and self.timeout_handler:
            # Try to determine operation type from command
            operation_type = command[1] if len(command) > 1 else 'default'
            timeout = self.timeout_handler.get_recommended_timeout(operation_type)
        
        if timeout:
            subprocess_args['timeout'] = timeout
        
        try:
            # Execute the command
            if config.show_output and not config.capture_output:
                # Show output directly to user
                result = subprocess.run(command, **subprocess_args)
                return GitCommandResult(
                    success=result.returncode == 0,
                    stdout="",
                    stderr="",
                    return_code=result.returncode
                )
            else:
                # Capture output
                result = subprocess.run(command, **subprocess_args)
                return GitCommandResult(
                    success=result.returncode == 0,
                    stdout=result.stdout or "",
                    stderr=result.stderr or "",
                    return_code=result.returncode
                )
                
        except subprocess.TimeoutExpired as e:
            return GitCommandResult(
                success=False,
                stderr=f"Command timed out after {timeout} seconds",
                return_code=-1
            )
        except Exception as e:
            return GitCommandResult(
                success=False,
                stderr=str(e),
                return_code=-1
            )
    
    def _is_retryable_error(self, result: GitCommandResult) -> bool:
        """
        Determine if an error is retryable.
        
        Args:
            result: Command result to check
            
        Returns:
            True if the error might be resolved by retrying
        """
        if not result.stderr:
            return False
        
        stderr_lower = result.stderr.lower()
        
        # Network-related errors that might be temporary
        retryable_patterns = [
            'connection refused',
            'connection reset',
            'connection timed out',
            'network is unreachable',
            'temporary failure',
            'service unavailable',
            'could not resolve host',
            'operation timed out',
            'timeout',
            'unable to access',
            'failed to connect'
        ]
        
        return any(pattern in stderr_lower for pattern in retryable_patterns)
    
    def _calculate_retry_delay(self, attempt: int, config: GitCommandConfig) -> float:
        """
        Calculate delay before retry based on strategy.
        
        Args:
            attempt: Current attempt number (0-based)
            config: Execution configuration
            
        Returns:
            Delay in seconds
        """
        if config.retry_strategy == RetryStrategy.NONE:
            return 0.0
        elif config.retry_strategy == RetryStrategy.LINEAR:
            return min(config.retry_delay * (attempt + 1), config.max_retry_delay)
        elif config.retry_strategy == RetryStrategy.EXPONENTIAL:
            return min(config.retry_delay * (2 ** attempt), config.max_retry_delay)
        else:  # CUSTOM or fallback
            return config.retry_delay
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get command execution statistics.
        
        Returns:
            Dictionary with execution statistics
        """
        stats = self.stats.copy()
        
        if stats['total_commands'] > 0:
            stats['success_rate'] = stats['successful_commands'] / stats['total_commands']
            stats['average_execution_time'] = stats['total_execution_time'] / stats['total_commands']
        else:
            stats['success_rate'] = 0.0
            stats['average_execution_time'] = 0.0
        
        return stats
    
    def reset_statistics(self) -> None:
        """Reset command execution statistics."""
        self.stats = {
            'total_commands': 0,
            'successful_commands': 0,
            'failed_commands': 0,
            'retried_commands': 0,
            'total_execution_time': 0.0
        }


# Convenience functions for common Git operations
def execute_git_command(command: List[str], timeout: Optional[int] = None,
                       retry_count: int = 1, capture_output: bool = True,
                       error_handler=None, timeout_handler=None,
                       input_validator=None) -> GitCommandResult:
    """
    Convenience function for executing Git commands.
    
    Args:
        command: Git command as list of strings
        timeout: Command timeout in seconds
        retry_count: Number of retry attempts
        capture_output: Whether to capture command output
        error_handler: Optional error handler
        timeout_handler: Optional timeout handler
        input_validator: Optional input validator
        
    Returns:
        GitCommandResult with execution details
    """
    executor = GitCommandExecutor(error_handler, timeout_handler, input_validator)
    config = GitCommandConfig(
        timeout=timeout,
        retry_count=retry_count,
        capture_output=capture_output
    )
    return executor.execute(command, config)


def safe_git_command(command: List[str], **kwargs) -> str:
    """
    Execute a Git command safely and return stdout.
    
    Args:
        command: Git command as list of strings
        **kwargs: Additional arguments for execute_git_command
        
    Returns:
        Command stdout, or empty string if command failed
    """
    result = execute_git_command(command, **kwargs)
    return result.stdout if result.success else ""