#!/usr/bin/env python3
"""
Input Validator - Comprehensive Input Validation and Sanitization

This module provides centralized input validation and sanitization functions
for all advanced Git features. It includes:
- Input sanitization to prevent command injection
- Validation for branch names, remote names, and file paths
- Pattern matching and format validation
- Secure input handling utilities
"""

import re
import os
import shlex
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Pattern, Callable


class InputValidationError(Exception):
    """Exception raised for input validation errors."""
    
    def __init__(self, message: str, field_name: str = None, validation_type: str = None):
        super().__init__(message)
        self.message = message
        self.field_name = field_name
        self.validation_type = validation_type


class InputValidator:
    """
    Centralized input validation and sanitization system.
    
    Provides comprehensive input validation and sanitization functions
    for all Git Wrapper features to prevent security issues.
    """
    
    # Common regex patterns
    PATTERNS = {
        'alphanumeric': re.compile(r'^[a-zA-Z0-9]+$'),
        'branch_name': re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_\-./]+$'),
        'remote_name': re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_\-]+$'),
        'email': re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'),
        'commit_hash': re.compile(r'^[0-9a-f]{7,40}$'),
        'tag_name': re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_\-./]+$'),
        'semver': re.compile(r'^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'),
        'url': re.compile(r'^(https?|git|ssh|file):\/\/[^\s/$.?#].[^\s]*$|^[^\s@]+@[^\s@]+\.[^\s@]+:.+$|^file:\/\/\/.*$'),
    }
    
    # Characters that should be escaped in shell commands
    SHELL_UNSAFE_CHARS = set('\\\'";$&|<>(){}[]!*?~` \t\n')
    
    # Characters not allowed in file paths (platform independent subset)
    PATH_UNSAFE_CHARS = set('<>:"|?*')
    
    def __init__(self, error_handler=None):
        """
        Initialize the InputValidator.
        
        Args:
            error_handler: Optional error handler for logging validation errors
        """
        self.error_handler = error_handler
    
    def validate_branch_name(self, branch_name: str) -> bool:
        """
        Validate a Git branch name according to Git rules.
        
        Args:
            branch_name: Branch name to validate
            
        Returns:
            True if valid, False otherwise
            
        Rules:
        - Cannot be empty
        - Cannot contain spaces
        - Cannot contain special characters: ~ ^ : ? * [ \ ..
        - Cannot start with a dot or slash
        - Cannot contain consecutive dots
        - Cannot contain @{
        - Cannot end with a slash or dot
        - Cannot be "HEAD"
        """
        if not branch_name or not isinstance(branch_name, str):
            return False
        
        # Check for reserved name
        if branch_name.upper() == "HEAD":
            return False
        
        # Check for invalid patterns
        invalid_patterns = [
            ' ', '~', '^', ':', '?', '*', '[', '\\', '..', '@{', '//', '/.', '.lock'
        ]
        
        for pattern in invalid_patterns:
            if pattern in branch_name:
                return False
        
        # Cannot start with dot or slash
        if branch_name.startswith(('.', '/')):
            return False
        
        # Cannot end with slash or dot
        if branch_name.endswith(('.', '/')):
            return False
        
        return True
    
    def validate_remote_name(self, remote_name: str) -> bool:
        """
        Validate a Git remote name.
        
        Args:
            remote_name: Remote name to validate
            
        Returns:
            True if valid, False otherwise
            
        Rules:
        - Cannot be empty
        - Cannot contain spaces or special characters
        - Must match the remote_name pattern
        """
        if not remote_name or not isinstance(remote_name, str):
            return False
        
        return bool(self.PATTERNS['remote_name'].match(remote_name))
    
    def validate_file_path(self, file_path: str, must_exist: bool = False, 
                          allow_outside_repo: bool = False) -> bool:
        """
        Validate a file path.
        
        Args:
            file_path: File path to validate
            must_exist: Whether the file must exist
            allow_outside_repo: Whether to allow paths outside the repository
            
        Returns:
            True if valid, False otherwise
        """
        if not file_path or not isinstance(file_path, str):
            return False
        
        # Check for unsafe characters
        if any(c in self.PATH_UNSAFE_CHARS for c in file_path):
            return False
        
        # Check for path traversal attempts
        normalized_path = os.path.normpath(file_path)
        if not allow_outside_repo and '..' in normalized_path.split(os.sep):
            return False
        
        # Check if file exists if required
        if must_exist and not os.path.exists(file_path):
            return False
        
        return True
    
    def validate_url(self, url: str) -> bool:
        """
        Validate a URL.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
        
        return bool(self.PATTERNS['url'].match(url))
    
    def validate_email(self, email: str) -> bool:
        """
        Validate an email address.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
        
        return bool(self.PATTERNS['email'].match(email))
    
    def validate_commit_hash(self, commit_hash: str) -> bool:
        """
        Validate a Git commit hash.
        
        Args:
            commit_hash: Commit hash to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not commit_hash or not isinstance(commit_hash, str):
            return False
        
        return bool(self.PATTERNS['commit_hash'].match(commit_hash))
    
    def validate_tag_name(self, tag_name: str) -> bool:
        """
        Validate a Git tag name.
        
        Args:
            tag_name: Tag name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not tag_name or not isinstance(tag_name, str):
            return False
        
        return bool(self.PATTERNS['tag_name'].match(tag_name))
    
    def validate_semver(self, version: str) -> bool:
        """
        Validate a semantic version string.
        
        Args:
            version: Version string to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not version or not isinstance(version, str):
            return False
        
        return bool(self.PATTERNS['semver'].match(version))
    
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
            
        Raises:
            InputValidationError: If validation fails and error_handler is None
        """
        try:
            # Enhanced security check - prevent null bytes and control characters
            if isinstance(input_value, str):
                # Check for null bytes (potential for command injection)
                if '\x00' in input_value:
                    error_msg = f"{field_name} contains null bytes"
                    if self.error_handler:
                        self.error_handler.log_warning(
                            error_msg, 
                            feature="input_validation", 
                            operation="validate_security"
                        )
                    return False
                
                # Check for other dangerous control characters
                dangerous_chars = ['\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08', 
                                 '\x0b', '\x0c', '\x0e', '\x0f', '\x10', '\x11', '\x12', '\x13', 
                                 '\x14', '\x15', '\x16', '\x17', '\x18', '\x19', '\x1a', '\x1b', 
                                 '\x1c', '\x1d', '\x1e', '\x1f', '\x7f']
                if any(char in input_value for char in dangerous_chars):
                    error_msg = f"{field_name} contains dangerous control characters"
                    if self.error_handler:
                        self.error_handler.log_warning(
                            error_msg, 
                            feature="input_validation", 
                            operation="validate_security"
                        )
                    return False
            
            # Required check
            if validation_rules.get('required', False) and not input_value:
                error_msg = f"{field_name} is required"
                if self.error_handler:
                    self.error_handler.log_warning(
                        error_msg, 
                        feature="input_validation", 
                        operation="validate_required"
                    )
                    return False
                else:
                    # Just return False without raising an exception
                    return False
            
            # Skip further validation if value is None or empty and not required
            if input_value is None or (isinstance(input_value, str) and not input_value):
                return True
            
            # Type check
            expected_type = validation_rules.get('type')
            if expected_type and not isinstance(input_value, expected_type):
                error_msg = f"{field_name} must be of type {expected_type.__name__}"
                if self.error_handler:
                    self.error_handler.log_warning(
                        error_msg, 
                        feature="input_validation", 
                        operation="validate_type"
                    )
                    return False
                else:
                    return False
            
            # Length check for strings
            if isinstance(input_value, str):
                min_length = validation_rules.get('min_length')
                max_length = validation_rules.get('max_length')
                
                if min_length is not None and len(input_value) < min_length:
                    error_msg = f"{field_name} must be at least {min_length} characters"
                    if self.error_handler:
                        self.error_handler.log_warning(
                            error_msg, 
                            feature="input_validation", 
                            operation="validate_min_length"
                        )
                    return False
                
                if max_length is not None and len(input_value) > max_length:
                    error_msg = f"{field_name} must be no more than {max_length} characters"
                    if self.error_handler:
                        self.error_handler.log_warning(
                            error_msg, 
                            feature="input_validation", 
                            operation="validate_max_length"
                        )
                    return False
            
            # Pattern check for strings
            pattern = validation_rules.get('pattern')
            if pattern and isinstance(input_value, str):
                if isinstance(pattern, str) and pattern in self.PATTERNS:
                    pattern = self.PATTERNS[pattern]
                
                if isinstance(pattern, re.Pattern) and not pattern.match(input_value):
                    error_msg = validation_rules.get('pattern_error', f"{field_name} does not match required format")
                    if self.error_handler:
                        self.error_handler.log_warning(
                            error_msg, 
                            feature="input_validation", 
                            operation="validate_pattern"
                        )
                    return False
                elif isinstance(pattern, str) and not re.match(pattern, input_value):
                    error_msg = validation_rules.get('pattern_error', f"{field_name} does not match required format")
                    if self.error_handler:
                        self.error_handler.log_warning(
                            error_msg, 
                            feature="input_validation", 
                            operation="validate_pattern"
                        )
                    return False
            
            # Enum check
            enum_values = validation_rules.get('enum')
            if enum_values and input_value not in enum_values:
                error_msg = f"{field_name} must be one of: {', '.join(str(v) for v in enum_values)}"
                if self.error_handler:
                    self.error_handler.log_warning(
                        error_msg, 
                        feature="input_validation", 
                        operation="validate_enum"
                    )
                return False
            
            # Range check for numbers
            if isinstance(input_value, (int, float)):
                min_value = validation_rules.get('min_value')
                max_value = validation_rules.get('max_value')
                
                if min_value is not None and input_value < min_value:
                    error_msg = f"{field_name} must be at least {min_value}"
                    if self.error_handler:
                        self.error_handler.log_warning(
                            error_msg, 
                            feature="input_validation", 
                            operation="validate_min_value"
                        )
                    return False
                
                if max_value is not None and input_value > max_value:
                    error_msg = f"{field_name} must be no more than {max_value}"
                    if self.error_handler:
                        self.error_handler.log_warning(
                            error_msg, 
                            feature="input_validation", 
                            operation="validate_max_value"
                        )
                    return False
            
            # Custom validator
            custom_validator = validation_rules.get('validator')
            if custom_validator and callable(custom_validator):
                if not custom_validator(input_value):
                    error_msg = validation_rules.get('validator_error', f"{field_name} is invalid")
                    if self.error_handler:
                        self.error_handler.log_warning(
                            error_msg, 
                            feature="input_validation", 
                            operation="validate_custom"
                        )
                    return False
            
            # Specific validators
            validator_type = validation_rules.get('validator_type')
            if validator_type:
                if validator_type == 'branch_name' and not self.validate_branch_name(input_value):
                    error_msg = "Invalid branch name. Branch names cannot contain spaces or special characters like: ~ ^ : ? * [ \\ .. @{ // /. .lock"
                    if self.error_handler:
                        self.error_handler.log_warning(
                            error_msg, 
                            feature="input_validation", 
                            operation="validate_branch_name"
                        )
                    return False
                elif validator_type == 'remote_name' and not self.validate_remote_name(input_value):
                    error_msg = "Invalid remote name. Remote names must contain only alphanumeric characters, hyphens, and underscores."
                    if self.error_handler:
                        self.error_handler.log_warning(
                            error_msg, 
                            feature="input_validation", 
                            operation="validate_remote_name"
                        )
                    return False
                elif validator_type == 'file_path' and not self.validate_file_path(
                    input_value, 
                    validation_rules.get('must_exist', False),
                    validation_rules.get('allow_outside_repo', False)
                ):
                    error_msg = "Invalid file path. Path contains invalid characters or is not accessible."
                    if self.error_handler:
                        self.error_handler.log_warning(
                            error_msg, 
                            feature="input_validation", 
                            operation="validate_file_path"
                        )
                    return False
                elif validator_type == 'url' and not self.validate_url(input_value):
                    error_msg = "Invalid URL format."
                    if self.error_handler:
                        self.error_handler.log_warning(
                            error_msg, 
                            feature="input_validation", 
                            operation="validate_url"
                        )
                    return False
                elif validator_type == 'email' and not self.validate_email(input_value):
                    error_msg = "Invalid email address format."
                    if self.error_handler:
                        self.error_handler.log_warning(
                            error_msg, 
                            feature="input_validation", 
                            operation="validate_email"
                        )
                    return False
            
            return True
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.log_error(f"Validation error: {str(e)}")
            
            # Just return False without raising an exception
            return False
    
    def _handle_validation_error(self, message: str, field_name: str, validation_type: str) -> None:
        """
        Handle a validation error.
        
        Args:
            message: Error message
            field_name: Name of the field that failed validation
            validation_type: Type of validation that failed
            
        Raises:
            InputValidationError: If error_handler is None
        """
        if self.error_handler:
            self.error_handler.log_warning(
                message, 
                feature="input_validation", 
                operation=f"validate_{validation_type}"
            )
        else:
            # Just print the error message instead of raising an exception
            print(f"Validation error: {message}")
    
    # Sanitization Methods
    
    def sanitize_shell_input(self, input_str: str) -> str:
        """
        Sanitize input for safe use in shell commands.
        
        Args:
            input_str: Input string to sanitize
            
        Returns:
            Sanitized string safe for shell commands
        """
        if not input_str or not isinstance(input_str, str):
            return ""
        
        # Remove null bytes and dangerous control characters first
        sanitized = input_str.replace('\x00', '')
        
        # Remove other dangerous control characters
        dangerous_chars = ['\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08', 
                         '\x0b', '\x0c', '\x0e', '\x0f', '\x10', '\x11', '\x12', '\x13', 
                         '\x14', '\x15', '\x16', '\x17', '\x18', '\x19', '\x1a', '\x1b', 
                         '\x1c', '\x1d', '\x1e', '\x1f', '\x7f']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Check for command injection patterns
        injection_patterns = [
            ';', '&&', '||', '|', '`', '$(',  # Command separators and substitution
            '$(', '${', '`',  # Command/variable substitution
            '>', '>>', '<',   # Redirection
            '&', '#',         # Background execution and comments
        ]
        
        # If any dangerous patterns are found, use shlex.quote
        if any(pattern in sanitized for pattern in injection_patterns):
            return shlex.quote(sanitized)
        
        # Use shlex.quote for proper shell escaping if needed
        # For testing compatibility, we'll handle the quotes explicitly
        if "'" in sanitized or " " in sanitized or any(c in sanitized for c in self.SHELL_UNSAFE_CHARS):
            return shlex.quote(sanitized)
        return sanitized
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename for safe file system usage.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        if not filename or not isinstance(filename, str):
            return ""
        
        # Remove or replace invalid characters
        sanitized = ''.join(c if c not in self.PATH_UNSAFE_CHARS else '_' for c in filename)
        
        # Remove control characters
        sanitized = ''.join(c for c in sanitized if ord(c) >= 32)
        
        # Limit length
        return sanitized[:255]
    
    def sanitize_path(self, path: str, allow_outside_repo: bool = False) -> str:
        """
        Sanitize a file path.
        
        Args:
            path: File path to sanitize
            allow_outside_repo: Whether to allow paths outside the repository
            
        Returns:
            Sanitized path
        """
        if not path or not isinstance(path, str):
            return ""
        
        # Normalize path
        normalized_path = os.path.normpath(path)
        
        # Prevent path traversal if not allowed
        if not allow_outside_repo:
            parts = normalized_path.split(os.sep)
            filtered_parts = []
            
            for part in parts:
                if part == '..':
                    if filtered_parts:
                        filtered_parts.pop()
                elif part and part != '.':
                    filtered_parts.append(part)
            
            normalized_path = os.sep.join(filtered_parts)
        
        return normalized_path
    
    def sanitize_git_reference(self, ref: str) -> str:
        """
        Sanitize a Git reference (branch, tag, etc.).
        
        Args:
            ref: Git reference to sanitize
            
        Returns:
            Sanitized Git reference
        """
        if not ref or not isinstance(ref, str):
            return ""
        
        # Remove potentially dangerous characters
        sanitized = ''.join(c for c in ref if c.isalnum() or c in '_-./+')
        
        # Ensure it doesn't start with dangerous characters
        while sanitized and sanitized[0] in '.-/':
            sanitized = sanitized[1:]
        
        # Ensure it doesn't end with dangerous characters
        while sanitized and sanitized[-1] in '.-/':
            sanitized = sanitized[:-1]
        
        return sanitized
    
    def sanitize_url(self, url: str) -> str:
        """
        Sanitize a URL.
        
        Args:
            url: URL to sanitize
            
        Returns:
            Sanitized URL
        """
        if not url or not isinstance(url, str):
            return ""
        
        # Basic URL sanitization - remove whitespace and control characters
        sanitized = ''.join(c for c in url if ord(c) >= 32 and not c.isspace())
        
        # Remove null bytes and dangerous characters
        sanitized = sanitized.replace('\x00', '')
        
        # Ensure it starts with a valid protocol
        valid_protocols = ['http://', 'https://', 'git://', 'ssh://', 'file://']
        has_valid_protocol = any(sanitized.startswith(protocol) for protocol in valid_protocols)
        
        # Also check for SSH format (user@host:path)
        is_ssh_format = bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+:.+$', sanitized))
        
        if not has_valid_protocol and not is_ssh_format:
            return ""
        
        return sanitized
    
    def validate_git_url(self, url: str) -> bool:
        """
        Validate a Git repository URL with enhanced security checks.
        
        Args:
            url: Git repository URL to validate
            
        Returns:
            True if valid and safe, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
        
        # Basic URL validation first
        if not self.validate_url(url):
            return False
        
        # Additional Git-specific validation
        # Prevent local file access outside of intended directories
        if url.startswith('file://'):
            # Only allow absolute paths that don't contain path traversal
            path_part = url[7:]  # Remove 'file://'
            if '..' in path_part or not os.path.isabs(path_part):
                return False
        
        # Prevent access to sensitive protocols
        dangerous_protocols = ['ftp://', 'ftps://', 'ldap://', 'ldaps://']
        if any(url.lower().startswith(proto) for proto in dangerous_protocols):
            return False
        
        # Check for suspicious patterns that might indicate injection attempts
        suspicious_patterns = [
            '$(', '`', '${', ';', '&&', '||', '|', '>', '<', '&'
        ]
        if any(pattern in url for pattern in suspicious_patterns):
            return False
        
        return True
    
    def validate_commit_message(self, message: str, max_length: int = 72) -> bool:
        """
        Validate a Git commit message.
        
        Args:
            message: Commit message to validate
            max_length: Maximum length for the first line
            
        Returns:
            True if valid, False otherwise
        """
        if not message or not isinstance(message, str):
            return False
        
        # Check for null bytes and control characters
        if '\x00' in message:
            return False
        
        # Split into lines
        lines = message.split('\n')
        
        # First line (subject) should not be too long
        if len(lines[0]) > max_length:
            return False
        
        # Check for common commit message patterns
        # Should not start with whitespace
        if lines[0].startswith(' ') or lines[0].startswith('\t'):
            return False
        
        # Should not end with a period
        if lines[0].endswith('.'):
            return False
        
        return True
    
    def sanitize_commit_message(self, message: str) -> str:
        """
        Sanitize a commit message.
        
        Args:
            message: Commit message to sanitize
            
        Returns:
            Sanitized commit message
        """
        if not message or not isinstance(message, str):
            return ""
        
        # Remove null bytes and dangerous control characters
        sanitized = message.replace('\x00', '')
        
        # Remove other dangerous control characters but keep newlines and tabs
        dangerous_chars = ['\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08', 
                         '\x0b', '\x0c', '\x0e', '\x0f', '\x10', '\x11', '\x12', '\x13', 
                         '\x14', '\x15', '\x16', '\x17', '\x18', '\x19', '\x1a', '\x1b', 
                         '\x1c', '\x1d', '\x1e', '\x1f', '\x7f']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Normalize line endings
        sanitized = sanitized.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove trailing whitespace from each line
        lines = sanitized.split('\n')
        sanitized_lines = [line.rstrip() for line in lines]
        
        return '\n'.join(sanitized_lines).strip()


# Decorator for input validation
def validate_input(field_name: str, validation_rules: Dict[str, Any], arg_index: int = 0):
    """
    Decorator for validating function input.
    
    Args:
        field_name: Name of the field being validated
        validation_rules: Dictionary of validation rules
        arg_index: Index of the argument to validate
        
    Example:
        ```python
        @validate_input('branch_name', {'required': True, 'validator_type': 'branch_name'})
        def create_branch(self, branch_name: str):
            # Function implementation
        ```
    """
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get the value to validate
            if arg_index < len(args):
                value = args[arg_index]
            elif field_name in kwargs:
                value = kwargs[field_name]
            else:
                # Can't find the argument, just call the function
                return func(self, *args, **kwargs)
            
            # Get or create validator
            validator = getattr(self, 'input_validator', None)
            if not validator:
                error_handler = getattr(self, 'error_handler', None)
                validator = InputValidator(error_handler)
            
            # Validate input
            if not validator.validate_input(value, validation_rules, field_name):
                # Get print_error method if available
                print_error = getattr(self, 'print_error', None)
                if print_error and callable(print_error):
                    print_error(f"Invalid {field_name}")
                return None
            
            # Call the function with validated input
            return func(self, *args, **kwargs)
        
        return wrapper
    
    return decorator