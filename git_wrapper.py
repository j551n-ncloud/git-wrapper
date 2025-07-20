#!/usr/bin/env python3
"""
Interactive Git Wrapper - A user-friendly interface for Git operations
Usage: gw [command] or just gw for interactive mode
"""

import subprocess
import sys
import os
import json
import time
import platform
import locale
from pathlib import Path, PurePath
from typing import Dict, Any, List, Optional, Union, Tuple

# Import feature managers (lazy loading to avoid circular imports)
from features.base_manager import BaseFeatureManager
from features.input_validator import InputValidator
from features.timeout_handler import TimeoutHandler, timeout_context
from features.safe_file_operations import SafeFileOperations
from features.git_command_executor import GitCommandExecutor, GitCommandConfig, RetryStrategy

class InteractiveGitWrapper:
    def __init__(self):
        # Initialize platform-specific settings
        self.platform_info = self._detect_platform()
        
        # Set up configuration file path with platform-specific handling
        self.config_file = self._get_config_file_path()
        
        # Initialize encoding settings for Unicode support
        self._setup_encoding()
        
        self.load_config()
        self.check_git_available()
        
        # Initialize input validator and timeout handler
        self.input_validator = InputValidator()
        self.timeout_handler = TimeoutHandler()
        self.safe_file_ops = SafeFileOperations()
        
        # Initialize Git command executor
        self.git_executor = GitCommandExecutor(
            error_handler=None,  # Will be set later when error handler is available
            timeout_handler=self.timeout_handler,
            input_validator=self.input_validator
        )
        
        # Initialize feature managers (lazy loading)
        self._feature_managers = {}
        self._features_initialized = False
    
    def load_config(self):
        """Load user configuration with comprehensive feature support"""
        # Initialize default configuration with all features
        self.config = self._get_default_config()
        
        if self.config_file.exists():
            try:
                # Use safe file operations for loading configuration
                loaded_config = self.safe_file_ops.safe_read_json(self.config_file)
                
                if loaded_config is not None:
                    # Perform deep merge of configuration
                    self._deep_merge_config(self.config, loaded_config)
                    
                    # Perform configuration migration if needed
                    self._migrate_config()
                else:
                    self.print_error("Error loading configuration: Invalid or corrupted file")
                    self.print_info("Using default configuration")
                    
            except Exception as e:
                self.print_error(f"Error loading configuration: {str(e)}")
                self.print_info("Using default configuration")
        
        # Validate configuration after loading
        self._validate_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get comprehensive default configuration for all features"""
        return {
            'name': '', 
            'email': '', 
            'default_branch': 'main',
            'auto_push': True, 
            'show_emoji': True, 
            'default_remote': 'origin',
            'config_version': '2.0',  # Track config version for migrations
            'advanced_features': {
                'stash_management': {
                    'auto_name_stashes': True,
                    'max_stashes': 50,
                    'show_preview_lines': 10,
                    'confirm_deletions': True,
                    'auto_cleanup_old': False,
                    'cleanup_days': 30
                },
                'commit_templates': {
                    'default_template': 'conventional',
                    'auto_suggest': True,
                    'validate_conventional': True,
                    'custom_templates_enabled': True,
                    'template_categories': ['feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore'],
                    'require_scope': False,
                    'require_body': False
                },
                'branch_workflows': {
                    'default_workflow': 'github_flow',
                    'auto_track_remotes': True,
                    'base_branch': 'main',
                    'feature_prefix': 'feature/',
                    'hotfix_prefix': 'hotfix/',
                    'release_prefix': 'release/',
                    'auto_cleanup_merged': True,
                    'confirm_branch_deletion': True
                },
                'conflict_resolution': {
                    'preferred_editor': 'code',
                    'auto_stage_resolved': True,
                    'show_conflict_markers': True,
                    'backup_before_resolve': True,
                    'preferred_merge_tool': 'vimdiff',
                    'auto_continue_merge': False
                },
                'health_dashboard': {
                    'stale_branch_days': 30,
                    'large_file_threshold_mb': 10,
                    'auto_refresh': True,
                    'show_contributor_stats': True,
                    'check_remote_branches': True,
                    'warn_large_repo_size_gb': 1.0,
                    'max_branches_to_analyze': 100
                },
                'backup_system': {
                    'backup_remotes': ['backup', 'mirror'],
                    'auto_backup_branches': ['main', 'develop'],
                    'retention_days': 90,
                    'backup_frequency': 'daily',
                    'compress_backups': True,
                    'verify_backup_integrity': True,
                    'notification_on_failure': True,
                    'max_backup_size_gb': 5.0
                }
            },
            'platform': self.get_platform_specific_config() if hasattr(self, 'platform_info') else {}
        }
    
    def _deep_merge_config(self, base_config: Dict, loaded_config: Dict) -> None:
        """
        Perform deep merge of configuration dictionaries.
        
        Args:
            base_config: Base configuration to merge into
            loaded_config: Loaded configuration to merge from
        """
        for key, value in loaded_config.items():
            if key in base_config and isinstance(base_config[key], dict) and isinstance(value, dict):
                self._deep_merge_config(base_config[key], value)
            else:
                base_config[key] = value
    
    def _migrate_config(self) -> None:
        """Migrate configuration from older versions if needed"""
        current_version = self.config.get('config_version', '1.0')
        
        if current_version == '1.0':
            self.print_info("Migrating configuration to version 2.0...")
            
            # Migrate old advanced_features structure if it exists
            if 'advanced_features' in self.config:
                old_features = self.config['advanced_features']
                new_features = self._get_default_config()['advanced_features']
                
                # Merge old settings with new defaults
                for feature_name, feature_config in old_features.items():
                    if feature_name in new_features:
                        new_features[feature_name].update(feature_config)
                
                self.config['advanced_features'] = new_features
            
            # Update version
            self.config['config_version'] = '2.0'
            self.save_config()
            self.print_success("Configuration migration completed!")
    
    def _validate_config(self) -> None:
        """Validate configuration values and fix invalid ones"""
        validation_rules = {
            'advanced_features.stash_management.max_stashes': (1, 200),
            'advanced_features.stash_management.show_preview_lines': (1, 50),
            'advanced_features.stash_management.cleanup_days': (1, 365),
            'advanced_features.commit_templates.template_categories': (list, None),
            'advanced_features.branch_workflows.base_branch': (str, None),
            'advanced_features.conflict_resolution.preferred_editor': (str, None),
            'advanced_features.health_dashboard.stale_branch_days': (1, 365),
            'advanced_features.health_dashboard.large_file_threshold_mb': (0.1, 1000),
            'advanced_features.health_dashboard.warn_large_repo_size_gb': (0.1, 100),
            'advanced_features.health_dashboard.max_branches_to_analyze': (10, 1000),
            'advanced_features.backup_system.retention_days': (1, 3650),
            'advanced_features.backup_system.max_backup_size_gb': (0.1, 100),
        }
        
        for config_path, (min_val, max_val) in validation_rules.items():
            try:
                value = self._get_nested_config_value(config_path)
                if value is not None:
                    if isinstance(min_val, type):
                        # Type validation
                        if not isinstance(value, min_val):
                            self._set_nested_config_value(config_path, self._get_default_for_path(config_path))
                    elif isinstance(min_val, (int, float)) and isinstance(value, (int, float)):
                        # Range validation
                        if value < min_val or (max_val and value > max_val):
                            self._set_nested_config_value(config_path, min_val)
            except Exception:
                # Reset to default if validation fails
                self._set_nested_config_value(config_path, self._get_default_for_path(config_path))
    
    def _get_nested_config_value(self, config_path: str) -> Any:
        """Get a nested configuration value using dot notation"""
        keys = config_path.split('.')
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def _set_nested_config_value(self, config_path: str, value: Any) -> None:
        """Set a nested configuration value using dot notation"""
        keys = config_path.split('.')
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value
    
    def _get_default_for_path(self, config_path: str) -> Any:
        """Get default value for a configuration path"""
        default_config = self._get_default_config()
        keys = config_path.split('.')
        value = default_config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def save_config(self):
        """Save user configuration with atomic operations, validation and backup"""
        try:
            # Validate config before saving
            self._validate_config()
            
            # Use safe file operations for atomic write with backup
            success = self.safe_file_ops.atomic_write_json(
                self.config_file, 
                self.config, 
                indent=2, 
                backup=True
            )
            
            if not success:
                self.print_error("Failed to save configuration")
                return
            
            # Verify the saved configuration
            if not self._verify_saved_config():
                self.print_error("Configuration verification failed after save")
            
            # Clean up old backup files (keep last 3)
            self.safe_file_ops.cleanup_old_backups(self.config_file, max_backups=3)
                
        except Exception as e:
            self.print_error(f"Unexpected error saving configuration: {str(e)}")
    
    def _verify_saved_config(self) -> bool:
        """
        Verify that the saved configuration is valid and can be loaded.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Use safe file operations to read and verify
            loaded_config = self.safe_file_ops.safe_read_json(self.config_file)
            
            if loaded_config is None:
                raise ValueError("Could not load saved configuration")
            
            # Basic validation - ensure it's a dictionary
            if not isinstance(loaded_config, dict):
                raise ValueError("Configuration is not a valid dictionary")
            
            # Check for required keys
            required_keys = ['name', 'email', 'default_branch']
            for key in required_keys:
                if key not in loaded_config:
                    self.print_error(f"Warning: Missing required configuration key: {key}")
            
            return True
            
        except Exception as e:
            self.print_error(f"Configuration verification failed: {str(e)}")
            return False
    
    def export_config(self, export_path: Optional[str] = None) -> bool:
        """
        Export configuration to a file.
        
        Args:
            export_path: Path to export to, defaults to gitwrapper_config_export.json
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not export_path:
                export_path = "gitwrapper_config_export.json"
            
            export_file = Path(export_path)
            
            with open(export_file, 'w') as f:
                json.dump(self.config, f, indent=2, sort_keys=True)
            
            self.print_success(f"Configuration exported to: {export_file.absolute()}")
            return True
            
        except Exception as e:
            self.print_error(f"Failed to export configuration: {str(e)}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """
        Import configuration from a file.
        
        Args:
            import_path: Path to import from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import_file = Path(import_path)
            
            if not import_file.exists():
                self.print_error(f"Import file not found: {import_path}")
                return False
            
            with open(import_file, 'r') as f:
                imported_config = json.load(f)
            
            # Validate imported config structure
            if not isinstance(imported_config, dict):
                self.print_error("Invalid configuration format")
                return False
            
            # Merge with current config
            self._deep_merge_config(self.config, imported_config)
            
            # Validate and save
            self._validate_config()
            self.save_config()
            
            self.print_success(f"Configuration imported from: {import_file.absolute()}")
            return True
            
        except json.JSONDecodeError as e:
            self.print_error(f"Invalid JSON in import file: {str(e)}")
            return False
        except Exception as e:
            self.print_error(f"Failed to import configuration: {str(e)}")
            return False
    
    def reset_config_to_defaults(self, feature: Optional[str] = None) -> bool:
        """
        Reset configuration to defaults.
        
        Args:
            feature: Specific feature to reset, or None for all
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if feature:
                # Reset specific feature
                default_config = self._get_default_config()
                if feature in default_config.get('advanced_features', {}):
                    self.config['advanced_features'][feature] = default_config['advanced_features'][feature]
                    self.print_success(f"Reset {feature} configuration to defaults")
                else:
                    self.print_error(f"Unknown feature: {feature}")
                    return False
            else:
                # Reset all configuration
                if self.confirm("Reset ALL configuration to defaults? This cannot be undone.", False):
                    self.config = self._get_default_config()
                    self.print_success("All configuration reset to defaults")
                else:
                    return False
            
            self.save_config()
            return True
            
        except Exception as e:
            self.print_error(f"Failed to reset configuration: {str(e)}")
            return False
    
    def print_success(self, message):
        emoji = "✅ " if self.config['show_emoji'] else ""
        print(f"{emoji}{message}")
    
    def print_error(self, message):
        emoji = "❌ " if self.config['show_emoji'] else ""
        print(f"{emoji}{message}")
    
    def print_info(self, message):
        emoji = "ℹ️  " if self.config['show_emoji'] else ""
        print(f"{emoji}{message}")
    
    def print_working(self, message):
        emoji = "🔄 " if self.config['show_emoji'] else ""
        print(f"{emoji}{message}")
    
    def check_git_available(self):
        """Check if git is available"""
        try:
            subprocess.run(['git', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.print_error("Git is not installed or not available in PATH")
            sys.exit(1)
    
    def is_git_repo(self):
        """Check if current directory is a git repository"""
        try:
            subprocess.run(['git', 'rev-parse', '--git-dir'], 
                         capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def run_git_command(self, cmd, capture_output=False, show_output=True, 
                     timeout=None, operation_type=None, retry_count=1):
        """
        Run a git command with enhanced error handling, timeouts, and retries
        
        Args:
            cmd: Git command as list of strings
            capture_output: Whether to capture and return command output
            show_output: Whether to show command output to user
            timeout: Timeout in seconds (None for default)
            operation_type: Type of operation for dynamic timeout calculation
            retry_count: Number of times to retry on failure
            
        Returns:
            If capture_output is True, returns command output as string.
            Otherwise, returns boolean indicating success (True) or failure (False).
        """
        # Enhanced input validation
        if not cmd or not isinstance(cmd, list):
            self.print_error("Invalid command format - must be a list of strings")
            return False if not capture_output else ""
        
        # Validate that first argument is git
        if not cmd[0] or 'git' not in cmd[0].lower():
            self.print_error("Command must be a Git command")
            return False if not capture_output else ""
        
        # Determine timeout to use
        if timeout is None and operation_type:
            timeout = self.timeout_handler.get_recommended_timeout(operation_type)
        elif timeout is None:
            # Try to determine operation type from command
            if len(cmd) > 1:
                operation_type = cmd[1]
                timeout = self.timeout_handler.get_recommended_timeout(operation_type)
            else:
                timeout = self.timeout_handler.default_timeout
        
        # Configure Git command execution
        config = GitCommandConfig(
            timeout=timeout,
            retry_count=retry_count,
            retry_strategy=RetryStrategy.EXPONENTIAL,
            retry_delay=1.0,
            max_retry_delay=10.0,
            capture_output=capture_output,
            show_output=show_output and not capture_output,
            shell_escape=True,
            validate_command=True
        )
        
        # Execute the command using the enhanced executor
        result = self.git_executor.execute(cmd, config)
        
        # Handle the result
        if result.success:
            return result.stdout.strip() if capture_output else True
        else:
            # Handle failure with detailed error reporting
            self._handle_git_command_failure_enhanced(cmd, result, timeout)
            return "" if capture_output else False
    

    
    def _handle_git_command_failure_enhanced(self, cmd: List[str], result, timeout: int) -> None:
        """
        Handle Git command failure with enhanced error reporting.
        
        Args:
            cmd: The command that failed
            result: GitCommandResult with failure details
            timeout: The timeout that was used
        """
        self.print_error(f"Git command failed: {' '.join(str(c) for c in cmd)}")
        
        # Show specific error details
        if result.stderr:
            print(f"Git error: {result.stderr}")
        
        if result.return_code != 0:
            print(f"Git exited with code: {result.return_code}")
        
        if "timed out" in result.stderr.lower():
            print(f"Command timed out after {timeout} seconds")
        
        # Show execution time if significant
        if result.execution_time > 1.0:
            print(f"Execution time: {result.execution_time:.2f} seconds")
        
        # Generate and show troubleshooting suggestions
        suggestions = self._generate_enhanced_git_suggestions(cmd, result)
        if suggestions:
            emoji = "💡" if self.config.get('show_emoji', True) else ""
            print(f"\n{emoji} Troubleshooting suggestions:")
            for i, suggestion in enumerate(suggestions[:5], 1):  # Limit to 5 suggestions
                print(f"  {i}. {suggestion}")
    
    def _generate_enhanced_git_suggestions(self, cmd: List[str], result) -> List[str]:
        """
        Generate enhanced troubleshooting suggestions for Git command failures.
        
        Args:
            cmd: The command that failed
            result: GitCommandResult with failure details
            
        Returns:
            List of troubleshooting suggestions
        """
        suggestions = []
        error_str = result.stderr.lower() if result.stderr else ""
        
        # Timeout-specific suggestions
        if "timed out" in error_str or result.execution_time > 30:
            suggestions.extend([
                f"Command took {result.execution_time:.1f} seconds - consider increasing timeout",
                "Check your network connection for remote operations",
                "Large repositories may require more time for operations"
            ])
        
        # Network-related suggestions
        if any(pattern in error_str for pattern in ['connection', 'network', 'resolve', 'timeout']):
            suggestions.extend([
                "Check your internet connection",
                "Verify the remote repository URL is correct",
                "Try using a different network or VPN",
                "Check if firewall is blocking Git operations"
            ])
        
        # Permission-related suggestions
        if 'permission' in error_str or 'denied' in error_str:
            suggestions.extend([
                "Check file and directory permissions",
                "Ensure you have write access to the repository",
                "Verify SSH key configuration for remote repositories",
                "Check if files are locked by another process"
            ])
        
        # Repository-specific suggestions
        if 'not a git repository' in error_str:
            suggestions.extend([
                "Initialize a Git repository with 'git init'",
                "Navigate to a directory that contains a Git repository",
                "Check if the .git directory exists and is not corrupted"
            ])
        
        # Operation-specific suggestions
        if len(cmd) > 1:
            operation = cmd[1]
            if operation == 'push':
                suggestions.extend([
                    "Ensure you have push permissions to the remote repository",
                    "Check if the remote branch exists or needs to be created",
                    "Try 'git pull' first to sync with remote changes",
                    "Verify your authentication credentials"
                ])
            elif operation == 'pull':
                suggestions.extend([
                    "Check if there are uncommitted changes that need to be stashed",
                    "Verify the remote repository is accessible",
                    "Try 'git fetch' to test remote connectivity",
                    "Check for merge conflicts that need resolution"
                ])
            elif operation == 'clone':
                suggestions.extend([
                    "Verify the repository URL is correct and accessible",
                    "Check if you have access permissions to the repository",
                    "Ensure you have sufficient disk space",
                    "Try cloning with --depth 1 for large repositories"
                ])
            elif operation in ['merge', 'rebase']:
                suggestions.extend([
                    "Check for merge conflicts that need manual resolution",
                    "Ensure working directory is clean before merge/rebase",
                    "Consider using conflict resolution tools",
                    "Try aborting and retrying the operation"
                ])
        
        # Return code specific suggestions
        if result.return_code == 128:
            suggestions.append("Return code 128 often indicates a Git usage error - check command syntax")
        elif result.return_code == 1:
            suggestions.append("Return code 1 may indicate conflicts or differences found")
        
        return suggestions
    
    def _handle_git_command_failure(self, cmd: List[str], error: Exception, 
                                  suggestions: List[str], timeout: int) -> None:
        """
        Handle Git command failure with detailed error reporting (legacy method).
        
        Args:
            cmd: The command that failed
            error: The exception that occurred
            suggestions: List of troubleshooting suggestions
            timeout: The timeout that was used
        """
        self.print_error(f"Git command failed: {' '.join(str(c) for c in cmd)}")
        
        # Show specific error details
        if hasattr(error, 'stderr') and error.stderr:
            print(f"Git error: {error.stderr}")
        elif hasattr(error, 'returncode'):
            print(f"Git exited with code: {error.returncode}")
        elif "timed out" in str(error).lower():
            print(f"Command timed out after {timeout} seconds")
        else:
            print(f"Error: {str(error)}")
        
        # Show troubleshooting suggestions
        if suggestions:
            emoji = "💡" if self.config.get('show_emoji', True) else ""
            print(f"\n{emoji} Troubleshooting suggestions:")
            for i, suggestion in enumerate(suggestions[:5], 1):  # Limit to 5 suggestions
                print(f"  {i}. {suggestion}")
        else:
            # Generate generic suggestions based on error type
            generic_suggestions = self._generate_generic_git_suggestions(cmd, error)
            if generic_suggestions:
                emoji = "💡" if self.config.get('show_emoji', True) else ""
                print(f"\n{emoji} Suggestions:")
                for i, suggestion in enumerate(generic_suggestions[:3], 1):
                    print(f"  {i}. {suggestion}")
    
    def _generate_generic_git_suggestions(self, cmd: List[str], error: Exception) -> List[str]:
        """
        Generate generic troubleshooting suggestions for Git command failures.
        
        Args:
            cmd: The command that failed
            error: The exception that occurred
            
        Returns:
            List of generic suggestions
        """
        suggestions = []
        error_str = str(error).lower()
        
        if 'not a git repository' in error_str:
            suggestions.extend([
                "Initialize a Git repository with 'git init'",
                "Navigate to a directory that contains a Git repository",
                "Check if you're in the correct directory"
            ])
        elif 'permission denied' in error_str:
            suggestions.extend([
                "Check file and directory permissions",
                "Ensure you have write access to the repository",
                "Try running with appropriate permissions"
            ])
        elif 'network' in error_str or 'connection' in error_str:
            suggestions.extend([
                "Check your internet connection",
                "Verify the remote URL is correct",
                "Try again after a few moments"
            ])
        elif len(cmd) > 1:
            operation = cmd[1]
            if operation == 'push':
                suggestions.extend([
                    "Ensure you have push permissions to the remote repository",
                    "Check if the remote branch exists",
                    "Try 'git pull' first to sync with remote changes"
                ])
            elif operation == 'pull':
                suggestions.extend([
                    "Check if there are uncommitted changes that need to be stashed",
                    "Verify the remote repository is accessible",
                    "Try 'git fetch' to see if you can connect to the remote"
                ])
            elif operation == 'clone':
                suggestions.extend([
                    "Verify the repository URL is correct",
                    "Check if you have access to the repository",
                    "Ensure you have sufficient disk space"
                ])
        
        return suggestions
    
    def get_input(self, prompt, default=None, validation_rules=None, max_attempts=3):
        """
        Get user input with optional default and validation
        
        Args:
            prompt: Prompt to display to the user
            default: Default value if user enters nothing
            validation_rules: Dictionary of validation rules to apply
            max_attempts: Maximum number of input attempts before giving up
            
        Returns:
            Validated user input, or None if max attempts exceeded
        """
        attempts = 0
        
        while attempts < max_attempts:
            try:
                if default:
                    user_input = input(f"{prompt} [{default}]: ").strip()
                    user_input = user_input if user_input else default
                else:
                    user_input = input(f"{prompt}: ").strip()
                
                # Basic security check - prevent null bytes and dangerous characters
                if '\x00' in user_input:
                    self.print_error("Input contains null bytes and is not allowed")
                    attempts += 1
                    continue
                
                # If no validation rules, return the input (after basic security check)
                if not validation_rules:
                    return user_input
                
                # Validate the input
                if self.input_validator.validate_input(user_input, validation_rules, prompt):
                    return user_input
                
                # If validation failed, show error and try again
                attempts += 1
                remaining_attempts = max_attempts - attempts
                
                if remaining_attempts > 0:
                    self.print_error(f"Invalid input. {remaining_attempts} attempts remaining.")
                    
                    # Show validation requirements if available
                    if validation_rules.get('pattern_error'):
                        print(f"Hint: {validation_rules['pattern_error']}")
                    elif validation_rules.get('validator_type'):
                        self._show_validation_hint(validation_rules['validator_type'])
                    else:
                        self._show_generic_validation_hint(validation_rules)
                else:
                    self.print_error("Maximum input attempts exceeded.")
                    return None
                    
            except KeyboardInterrupt:
                print("\nInput cancelled by user.")
                return None
            except EOFError:
                print("\nEnd of input reached.")
                return None
            except Exception as e:
                self.print_error(f"Error reading input: {str(e)}")
                attempts += 1
                if attempts >= max_attempts:
                    return None
        
        return None
    
    def _show_validation_hint(self, validator_type: str) -> None:
        """
        Show validation hints based on validator type.
        
        Args:
            validator_type: Type of validator that failed
        """
        hints = {
            'branch_name': "Branch names cannot contain spaces or special characters like: ~ ^ : ? * [ \\ .. @{ // /. .lock",
            'remote_name': "Remote names must contain only alphanumeric characters, hyphens, and underscores",
            'file_path': "File paths cannot contain dangerous characters like: < > : \" | ? *",
            'url': "URLs must start with http://, https://, git://, ssh://, file:// or be in SSH format (user@host:path)",
            'email': "Email addresses must be in the format: user@domain.com",
            'commit_hash': "Commit hashes must be 7-40 hexadecimal characters",
            'tag_name': "Tag names must start with alphanumeric characters and can contain: _ - . /",
            'semver': "Semantic versions must be in format: v1.2.3 or 1.2.3 (with optional pre-release/build metadata)"
        }
        
        hint = hints.get(validator_type, "Please check the input format")
        print(f"Hint: {hint}")
    
    def _show_generic_validation_hint(self, validation_rules: Dict[str, Any]) -> None:
        """
        Show generic validation hints based on validation rules.
        
        Args:
            validation_rules: Dictionary of validation rules
        """
        hints = []
        
        if validation_rules.get('required'):
            hints.append("This field is required")
        
        if validation_rules.get('min_length'):
            hints.append(f"Minimum length: {validation_rules['min_length']} characters")
        
        if validation_rules.get('max_length'):
            hints.append(f"Maximum length: {validation_rules['max_length']} characters")
        
        if validation_rules.get('min_value'):
            hints.append(f"Minimum value: {validation_rules['min_value']}")
        
        if validation_rules.get('max_value'):
            hints.append(f"Maximum value: {validation_rules['max_value']}")
        
        if validation_rules.get('enum'):
            hints.append(f"Allowed values: {', '.join(str(v) for v in validation_rules['enum'])}")
        
        if validation_rules.get('type'):
            hints.append(f"Expected type: {validation_rules['type'].__name__}")
        
        if hints:
            print(f"Requirements: {'; '.join(hints)}")
        elif validation_rules.get('validator_type') == 'branch_name':
            print("Hint: Branch names cannot contain spaces or special characters like: ~ ^ : ? * [ \\ .. @{")
        elif validation_rules.get('validator_type') == 'remote_name':
            print("Hint: Remote names must contain only alphanumeric characters, hyphens, and underscores.")
    
    def get_choice(self, prompt, choices, default=None):
        """Get user choice from a list"""
        print(f"\n{prompt}")
        for i, choice in enumerate(choices, 1):
            marker = " (default)" if default and choice == default else ""
            print(f"  {i}. {choice}{marker}")
        
        while True:
            try:
                choice_input = input("\nEnter choice number: ").strip()
                if not choice_input and default:
                    return default
                choice_num = int(choice_input)
                if 1 <= choice_num <= len(choices):
                    return choices[choice_num - 1]
                print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
    
    def get_multiple_choice(self, prompt, choices):
        """Get multiple choices from a list"""
        print(f"\n{prompt}")
        print("(Enter comma-separated numbers, e.g., 1,3,4)")
        for i, choice in enumerate(choices, 1):
            print(f"  {i}. {choice}")
        
        while True:
            try:
                choice_input = input("\nEnter choice numbers: ").strip()
                if not choice_input:
                    return []
                
                choice_nums = [int(x.strip()) for x in choice_input.split(',')]
                selected = []
                for num in choice_nums:
                    if 1 <= num <= len(choices):
                        selected.append(choices[num - 1])
                    else:
                        print(f"Invalid choice: {num}")
                        return []
                return selected
            except ValueError:
                print("Please enter valid numbers separated by commas.")
    
    def confirm(self, message, default=True):
        """Ask for confirmation"""
        suffix = "[Y/n]" if default else "[y/N]"
        response = input(f"{message} {suffix}: ").strip().lower()
        return response in ['y', 'yes'] if response else default
    
    def get_remotes(self):
        """Get list of remote repositories"""
        remotes_output = self.run_git_command(['git', 'remote'], capture_output=True)
        return remotes_output.split('\n') if remotes_output else []
    
    def show_main_menu(self):
        """Display the main interactive menu"""
        while True:
            self.clear_screen()
            repo_status = "🟢 Git Repository" if self.is_git_repo() else "🔴 Not a Git Repository"
            current_dir = os.path.basename(os.getcwd())
            
            print("=" * 50)
            print("🚀 Interactive Git Wrapper")
            print("=" * 50)
            print(f"📁 Directory: {current_dir}")
            print(f"📊 Status: {repo_status}")
            print("=" * 50)
            
            if self.is_git_repo():
                try:
                    branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
                    print(f"🌿 Current Branch: {branch}")
                    
                    status = self.run_git_command(['git', 'status', '--porcelain'], capture_output=True)
                    if status:
                        print(f"📝 Uncommitted Changes: {len(status.splitlines())} files")
                    else:
                        print("📝 Working Directory: Clean")
                    print("-" * 50)
                except:
                    pass
            
            # Menu options
            options = []
            if self.is_git_repo():
                options.extend([
                    "📊 Show Status", "💾 Quick Commit", "🔄 Sync (Pull & Push)",
                    "📤 Push Operations", "🌿 Branch Operations", "📋 View Changes", 
                    "📜 View History", "🔗 Remote Management"
                ])
                
                # Add advanced features if available
                if self.has_advanced_features():
                    options.extend([
                        "🗂️  Stash Management", "📝 Commit Templates", "🔀 Branch Workflows",
                        "⚔️  Conflict Resolution", "🏥 Repository Health", "💾 Smart Backup"
                    ])
            else:
                options.extend(["🎯 Initialize Repository", "📥 Clone Repository"])
            
            options.extend(["⚙️ Configuration", "❓ Help", "🚪 Exit"])
            
            for i, option in enumerate(options, 1):
                print(f"  {i}. {option}")
            
            try:
                choice = int(input(f"\nEnter your choice (1-{len(options)}): "))
                if 1 <= choice <= len(options):
                    self.handle_menu_choice(options[choice-1])
                else:
                    self.print_error("Invalid choice!")
                    time.sleep(1)
            except ValueError:
                self.print_error("Please enter a valid number!")
                time.sleep(1)
            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
    
    def handle_menu_choice(self, choice):
        """Handle menu selection"""
        handlers = {
            "Show Status": self.interactive_status,
            "Quick Commit": self.interactive_commit,
            "Sync": self.interactive_sync,
            "Push Operations": self.interactive_push_menu,
            "Branch Operations": self.interactive_branch_menu,
            "View Changes": self.interactive_diff,
            "View History": self.interactive_log,
            "Remote Management": self.interactive_remote_menu,
            "Stash Management": lambda: self._handle_feature_menu('stash'),
            "Commit Templates": lambda: self._handle_feature_menu('templates'),
            "Branch Workflows": lambda: self._handle_feature_menu('workflows'),
            "Conflict Resolution": lambda: self._handle_feature_menu('conflicts'),
            "Repository Health": lambda: self._handle_feature_menu('health'),
            "Smart Backup": lambda: self._handle_feature_menu('backup'),
            "Initialize Repository": self.interactive_init,
            "Clone Repository": self.interactive_clone,
            "Configuration": self.interactive_config_menu,
            "Help": self.show_help,
            "Exit": lambda: (print("\nGoodbye! 👋"), sys.exit(0))
        }
        
        for key, handler in handlers.items():
            if key in choice:
                handler()
                break
    
    def interactive_status(self):
        """Interactive status display"""
        self.clear_screen()
        print("📊 Repository Status\n" + "=" * 30)
        
        branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        if branch:
            print(f"🌿 Current branch: {branch}")
        
        print("\n📝 Working Directory Status:")
        self.run_git_command(['git', 'status'])
        
        print(f"\n📜 Recent commits:")
        self.run_git_command(['git', 'log', '--oneline', '-5'])
        
        input("\nPress Enter to continue...")
    
    def interactive_commit(self):
        """Interactive commit process"""
        self.clear_screen()
        print("💾 Quick Commit\n" + "=" * 20)
        
        # Check status with timeout
        status = self.run_git_command(['git', 'status', '--porcelain'], 
                                    capture_output=True, 
                                    timeout=10, 
                                    operation_type='status')
        if not status:
            self.print_info("No changes to commit!")
            input("Press Enter to continue...")
            return
        
        print("Files to be added:")
        print(status)
        
        if not self.confirm("\nAdd all changes?", True):
            return
        
        # Define validation rules for commit messages
        message_validation_rules = {
            'required': True,
            'min_length': 3,
            'max_length': 500
        }
        
        message = self.get_input("\nEnter commit message", validation_rules=message_validation_rules)
        if not message:
            return
        
        self.print_working("Adding all changes...")
        if not self.run_git_command(['git', 'add', '.'], 
                                  show_output=False, 
                                  timeout=30, 
                                  operation_type='add',
                                  retry_count=2):
            input("Press Enter to continue...")
            return
        
        # Sanitize the commit message to prevent command injection
        sanitized_message = self.input_validator.sanitize_shell_input(message)
        
        self.print_working(f"Committing with message: '{message}'")
        if self.run_git_command(['git', 'commit', '-m', sanitized_message], 
                              timeout=30, 
                              operation_type='commit',
                              retry_count=2):
            self.print_success("Commit successful!")
            
            if self.config['auto_push'] and self.confirm("Push to remote(s)?", True):
                self.interactive_push_menu()
        
        input("Press Enter to continue...")
    
    def interactive_push_menu(self):
        """Interactive push operations menu"""
        self.clear_screen()
        print("📤 Push Operations\n" + "=" * 20)
        
        remotes = self.get_remotes()
        if not remotes:
            self.print_error("No remotes configured!")
            input("Press Enter to continue...")
            return
        
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        print(f"Current branch: {current_branch or 'unknown'}")
        print(f"Available remotes: {', '.join(remotes)}")
        print("-" * 30)
        
        options = [
            "Push to single remote",
            "Push to multiple remotes",
            "Push to all remotes",
            "Back to main menu"
        ]
        
        choice = self.get_choice("Push Options:", options)
        
        if "single remote" in choice:
            self.interactive_push_single()
        elif "multiple remotes" in choice:
            self.interactive_push_multiple()
        elif "all remotes" in choice:
            self.interactive_push_all()
        elif "Back to main menu" in choice:
            return
    
    def interactive_push_single(self):
        """Push to a single selected remote"""
        remotes = self.get_remotes()
        if not remotes:
            return
        
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        branch = self.get_input("Branch to push", current_branch or self.config['default_branch'])
        
        default_remote = self.config.get('default_remote', 'origin')
        if default_remote not in remotes:
            default_remote = remotes[0]
        
        remote = self.get_choice("Select remote to push to:", remotes, default_remote)
        
        self.print_working(f"Pushing {branch} to {remote}...")
        if self.run_git_command(['git', 'push', remote, branch]):
            self.print_success(f"Successfully pushed to {remote}/{branch}!")
        
        input("Press Enter to continue...")
    
    def interactive_push_multiple(self):
        """Push to multiple selected remotes"""
        remotes = self.get_remotes()
        if not remotes:
            return
        
        if len(remotes) == 1:
            self.print_info("Only one remote available. Use single remote push instead.")
            input("Press Enter to continue...")
            return
        
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        branch = self.get_input("Branch to push", current_branch or self.config['default_branch'])
        
        selected_remotes = self.get_multiple_choice("Select remotes to push to:", remotes)
        
        if not selected_remotes:
            self.print_info("No remotes selected.")
            input("Press Enter to continue...")
            return
        
        self.print_info(f"Pushing {branch} to: {', '.join(selected_remotes)}")
        
        success_count = 0
        failed_remotes = []
        
        for remote in selected_remotes:
            self.print_working(f"Pushing to {remote}...")
            if self.run_git_command(['git', 'push', remote, branch], show_output=False):
                self.print_success(f"✓ Pushed to {remote}")
                success_count += 1
            else:
                self.print_error(f"✗ Failed to push to {remote}")
                failed_remotes.append(remote)
        
        print(f"\nSummary: {success_count}/{len(selected_remotes)} remotes successful")
        if failed_remotes:
            print(f"Failed remotes: {', '.join(failed_remotes)}")
        
        input("Press Enter to continue...")
    
    def interactive_push_all(self):
        """Push to all configured remotes"""
        remotes = self.get_remotes()
        if not remotes:
            return
        
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        branch = self.get_input("Branch to push", current_branch or self.config['default_branch'])
        
        if not self.confirm(f"Push {branch} to ALL {len(remotes)} remotes?", False):
            return
        
        self.print_info(f"Pushing {branch} to all remotes: {', '.join(remotes)}")
        
        success_count = 0
        failed_remotes = []
        
        for remote in remotes:
            self.print_working(f"Pushing to {remote}...")
            if self.run_git_command(['git', 'push', remote, branch], show_output=False):
                self.print_success(f"✓ Pushed to {remote}")
                success_count += 1
            else:
                self.print_error(f"✗ Failed to push to {remote}")
                failed_remotes.append(remote)
        
        print(f"\nSummary: {success_count}/{len(remotes)} remotes successful")
        if failed_remotes:
            print(f"Failed remotes: {', '.join(failed_remotes)}")
        
        input("Press Enter to continue...")
    
    def interactive_sync(self):
        """Interactive sync process"""
        self.clear_screen()
        print("🔄 Sync Repository\n" + "=" * 20)
        
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        branch = self.get_input("Branch to sync", current_branch or self.config['default_branch'])
        
        # Select remote for sync
        remotes = self.get_remotes()
        if not remotes:
            self.print_error("No remotes configured!")
            input("Press Enter to continue...")
            return
        
        default_remote = self.config.get('default_remote', 'origin')
        if default_remote not in remotes:
            default_remote = remotes[0]
        
        remote = self.get_choice("Select remote for sync:", remotes, default_remote)
        
        self.print_working(f"Syncing with {remote}/{branch}")
        
        # Pull and Push
        self.print_working("Pulling latest changes...")
        if not self.run_git_command(['git', 'pull', remote, branch]):
            input("Press Enter to continue...")
            return
        
        self.print_working("Pushing local commits...")
        if self.run_git_command(['git', 'push', remote, branch]):
            self.print_success("Sync completed successfully!")
        
        input("Press Enter to continue...")
    
    def interactive_remote_menu(self):
        """Interactive remote management menu"""
        while True:
            self.clear_screen()
            print("🔗 Remote Management\n" + "=" * 25)
            
            remotes = self.get_remotes()
            if remotes:
                print("Current remotes:")
                for remote in remotes:
                    url = self.run_git_command(['git', 'remote', 'get-url', remote], capture_output=True)
                    default_marker = f" (default)" if remote == self.config.get('default_remote') else ""
                    print(f"  {remote}: {url}{default_marker}")
                print()
            else:
                print("No remotes configured\n")
            
            options = [
                "Add remote", "Remove remote", "List remotes", 
                "Change remote URL", "Set default remote", "Back to main menu"
            ]
            
            choice = self.get_choice("Remote Operations:", options)
            
            if "Add remote" in choice:
                self.interactive_add_remote()
            elif "Remove remote" in choice:
                self.interactive_remove_remote()
            elif "List remotes" in choice:
                self.interactive_list_remotes()
            elif "Change remote URL" in choice:
                self.interactive_change_remote_url()
            elif "Set default remote" in choice:
                self.interactive_set_default_remote()
            elif "Back to main menu" in choice:
                break
    
    def interactive_set_default_remote(self):
        """Set default remote for operations"""
        remotes = self.get_remotes()
        if not remotes:
            self.print_info("No remotes configured")
            input("Press Enter to continue...")
            return
        
        current_default = self.config.get('default_remote', 'origin')
        remote = self.get_choice("Select default remote:", remotes, current_default)
        
        self.config['default_remote'] = remote
        self.save_config()
        self.print_success(f"Default remote set to: {remote}")
        
        input("Press Enter to continue...")
    
    def interactive_add_remote(self):
        """Add a new remote"""
        name = self.get_input("Remote name", "origin")
        if not name:
            return
    
        url = self.get_input("Remote URL")
        if not url:
            return
    
        self.print_working(f"Adding remote '{name}'...")
        if not self.run_git_command(['git', 'remote', 'add', name, url]):
            input("Press Enter to continue...")
            return
    
        self.print_success(f"Remote '{name}' added successfully!")
    
        # If this is the first remote, make it default
        remotes = self.get_remotes()
        if len(remotes) == 1:
            self.config['default_remote'] = name
            self.save_config()
            self.print_info(f"Set as default remote: {name}")
    
        # Ask if user wants to set upstream tracking for all branches
        if self.confirm(f"Set upstream tracking for all branches to '{name}'?", False):
            self.print_working("Setting upstream tracking for all branches...")
            if self.run_git_command(['git', 'push', '--set-upstream', name, '--all']):
                self.print_success("Upstream tracking set for all branches!")
            else:
                self.print_error("Failed to set upstream tracking")
    
        input("Press Enter to continue...")
    
    def interactive_remove_remote(self):
        """Remove an existing remote"""
        remotes = self.get_remotes()
        if not remotes:
            self.print_info("No remotes to remove")
            input("Press Enter to continue...")
            return
        
        remote = self.get_choice("Select remote to remove:", remotes)
        
        if self.confirm(f"Are you sure you want to remove remote '{remote}'?", False):
            if self.run_git_command(['git', 'remote', 'remove', remote]):
                self.print_success(f"Remote '{remote}' removed successfully!")
                
                # Update default remote if removed
                if self.config.get('default_remote') == remote:
                    remaining_remotes = self.get_remotes()
                    if remaining_remotes:
                        self.config['default_remote'] = remaining_remotes[0]
                        self.save_config()
                        self.print_info(f"Default remote changed to: {remaining_remotes[0]}")
                    else:
                        self.config['default_remote'] = 'origin'
                        self.save_config()
        
        input("Press Enter to continue...")
    
    def interactive_list_remotes(self):
        """List all remotes with details"""
        self.clear_screen()
        print("🔗 All Remotes\n" + "=" * 15)
        self.run_git_command(['git', 'remote', '-v'])
        input("\nPress Enter to continue...")
    
    def interactive_change_remote_url(self):
        """Change URL of existing remote"""
        remotes = self.get_remotes()
        if not remotes:
            self.print_info("No remotes configured")
            input("Press Enter to continue...")
            return
        
        remote = self.get_choice("Select remote to modify:", remotes)
        current_url = self.run_git_command(['git', 'remote', 'get-url', remote], capture_output=True)
        
        print(f"Current URL: {current_url}")
        new_url = self.get_input("New URL")
        if not new_url:
            return
        
        if self.run_git_command(['git', 'remote', 'set-url', remote, new_url]):
            self.print_success(f"URL for '{remote}' updated successfully!")
        
        input("Press Enter to continue...")
    
    def interactive_branch_menu(self):
        """Interactive branch operations menu"""
        while True:
            self.clear_screen()
            print("🌿 Branch Operations\n" + "=" * 25)
            
            current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
            if current_branch:
                print(f"Current branch: {current_branch}\n")
            
            options = [
                "Create new branch", "Switch to existing branch", "List all branches",
                "Delete branch", "Back to main menu"
            ]
            
            choice = self.get_choice("Branch Operations:", options)
            
            handlers = {
                "Create new branch": self.interactive_create_branch,
                "Switch to existing branch": self.interactive_switch_branch,
                "List all branches": self.interactive_list_branches,
                "Delete branch": self.interactive_delete_branch,
                "Back to main menu": lambda: None
            }
            
            for key, handler in handlers.items():
                if key in choice:
                    result = handler()
                    if key == "Back to main menu":
                        return
                    break
    
    def interactive_create_branch(self):
        """Interactive branch creation"""
        # Define validation rules for branch names
        branch_validation_rules = {
            'required': True,
            'validator_type': 'branch_name',
            'min_length': 1,
            'max_length': 100,
            'pattern_error': "Branch names cannot contain spaces or special characters like: ~ ^ : ? * [ \\ .. @{"
        }
        
        branch_name = self.get_input("Enter new branch name", validation_rules=branch_validation_rules)
        if not branch_name:
            return
        
        self.print_working(f"Creating new branch: {branch_name}")
        if self.run_git_command(['git', 'checkout', '-b', branch_name], timeout=30, operation_type='branch'):
            self.print_success(f"Created and switched to branch: {branch_name}")
        
        input("Press Enter to continue...")
    
    def interactive_switch_branch(self):
        """Interactive branch switching"""
        branches_output = self.run_git_command(['git', 'branch'], capture_output=True)
        if not branches_output:
            return
        
        branches = [b.strip().replace('* ', '') for b in branches_output.split('\n') if b.strip()]
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        
        if len(branches) > 1:
            branches = [b for b in branches if b != current_branch]
        
        if not branches:
            self.print_info("No other branches available")
            input("Press Enter to continue...")
            return
        
        branch = self.get_choice("Select branch to switch to:", branches)
        
        self.print_working(f"Switching to branch: {branch}")
        if self.run_git_command(['git', 'checkout', branch]):
            self.print_success(f"Switched to branch: {branch}")
        
        input("Press Enter to continue...")
    
    def interactive_list_branches(self):
        """Interactive branch listing"""
        self.clear_screen()
        print("🌿 All Branches\n" + "=" * 15)
        self.run_git_command(['git', 'branch', '-a'])
        input("\nPress Enter to continue...")
    
    def interactive_delete_branch(self):
        """Interactive branch deletion"""
        branches_output = self.run_git_command(['git', 'branch'], capture_output=True)
        if not branches_output:
            return
        
        branches = [b.strip().replace('* ', '') for b in branches_output.split('\n') if b.strip()]
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        
        if len(branches) > 1:
            branches = [b for b in branches if b != current_branch]
        
        if not branches:
            self.print_info("No branches available to delete")
            input("Press Enter to continue...")
            return
        
        branch = self.get_choice("Select branch to delete:", branches)
        
        if self.confirm(f"Are you sure you want to delete branch '{branch}'?", False):
            if self.run_git_command(['git', 'branch', '-d', branch]):
                self.print_success(f"Deleted branch: {branch}")
        
        input("Press Enter to continue...")
    
    def interactive_diff(self):
        """Interactive diff viewing"""
        self.clear_screen()
        
        diff_type = self.get_choice("What changes to view?", 
                                  ["Unstaged changes", "Staged changes"])
        
        if "Staged" in diff_type:
            print("📋 Staged changes:")
            self.run_git_command(['git', 'diff', '--cached'])
        else:
            print("📋 Unstaged changes:")
            self.run_git_command(['git', 'diff'])
        
        input("\nPress Enter to continue...")
    
    def interactive_log(self):
        """Interactive log viewing"""
        self.clear_screen()
        
        try:
            count = int(self.get_input("Number of commits to show", "10"))
        except ValueError:
            count = 10
        
        print(f"📜 Last {count} commits:")
        self.run_git_command(['git', 'log', '--oneline', f'-{count}'])
        
        input("\nPress Enter to continue...")
    
    def interactive_init(self):
        """Interactive repository initialization"""
        self.clear_screen()
        print("🎯 Initialize Repository\n" + "=" * 25)
        
        if self.confirm("Initialize git repository in current directory?", True):
            self.print_working("Initializing repository...")
            if not self.run_git_command(['git', 'init']):
                input("Press Enter to continue...")
                return
            
            if self.config['name'] and self.config['email']:
                self.run_git_command(['git', 'config', 'user.name', self.config['name']], show_output=False)
                self.run_git_command(['git', 'config', 'user.email', self.config['email']], show_output=False)
                self.print_info("Applied your saved configuration")
            
            if self.confirm("Add remote origin?", False):
                remote_url = self.get_input("Remote URL")
                if remote_url:
                    if self.run_git_command(['git', 'remote', 'add', 'origin', remote_url]):
                        self.print_success("Remote origin added")
                        self.config['default_remote'] = 'origin'
                        self.save_config()
            
            self.print_success("Repository initialized successfully!")
        
        input("Press Enter to continue...")
    
    def interactive_clone(self):
        """Interactive repository cloning"""
        self.clear_screen()
        print("📥 Clone Repository\n" + "=" * 20)
        
        # Define validation rules for repository URL
        url_validation_rules = {
            'required': True,
            'validator_type': 'url',
            'pattern_error': "Please enter a valid Git repository URL (e.g., https://github.com/user/repo.git or git@github.com:user/repo.git)"
        }
        
        url = self.get_input("Repository URL", validation_rules=url_validation_rules)
        if not url:
            return
        
        # Define validation rules for directory name
        dir_validation_rules = {
            'required': False,
            'pattern': r'^[a-zA-Z0-9][a-zA-Z0-9_\-\.]*$',
            'pattern_error': "Directory name should contain only alphanumeric characters, underscores, hyphens, and dots"
        }
        
        directory = self.get_input("Directory name (optional)", validation_rules=dir_validation_rules)
        
        # Sanitize inputs
        sanitized_url = self.input_validator.sanitize_url(url)
        
        cmd = ['git', 'clone', sanitized_url]
        if directory:
            sanitized_directory = self.input_validator.sanitize_filename(directory)
            cmd.append(sanitized_directory)
        
        self.print_working(f"Cloning repository: {url}")
        self.print_info("This may take a while for large repositories...")
        
        # Use longer timeout for clone operations with retry
        if self.run_git_command(cmd, timeout=300, operation_type='clone', retry_count=2):
            self.print_success("Repository cloned successfully!")
            
            if directory and self.confirm("Change to cloned directory?", True):
                try:
                    # Sanitize directory path before changing to it
                    safe_directory = self.input_validator.sanitize_path(directory)
                    os.chdir(safe_directory)
                    self.print_success(f"Changed to directory: {safe_directory}")
                except FileNotFoundError:
                    self.print_error("Could not change directory")
                except PermissionError:
                    self.print_error("Permission denied when trying to access directory")
        
        input("Press Enter to continue...")
    
    def interactive_config_menu(self):
        """Interactive configuration menu with advanced features support"""
        while True:
            self.clear_screen()
            print("⚙️ Configuration\n" + "=" * 20)
            print(f"Name: {self.config['name'] or 'Not set'}")
            print(f"Email: {self.config['email'] or 'Not set'}")
            print(f"Default Branch: {self.config['default_branch']}")
            print(f"Default Remote: {self.config['default_remote']}")
            print(f"Auto Push: {self.config['auto_push']}")
            print(f"Show Emoji: {self.config['show_emoji']}")
            print(f"Config Version: {self.config.get('config_version', '1.0')}")
            print("-" * 50)
            
            options = [
                "Basic Settings", "Advanced Feature Settings", "Import/Export Config",
                "Reset Configuration", "Back to main menu"
            ]
            
            choice = self.get_choice("Configuration Categories:", options)
            
            config_handlers = {
                "Basic Settings": self.interactive_basic_config_menu,
                "Advanced Feature Settings": self.interactive_advanced_features_menu,
                "Import/Export Config": self.interactive_import_export_menu,
                "Reset Configuration": self.interactive_reset_config_menu,
                "Back to main menu": lambda: None
            }
            
            for key, handler in config_handlers.items():
                if key in choice:
                    result = handler()
                    if key == "Back to main menu":
                        return
                    break
    
    def interactive_basic_config_menu(self):
        """Interactive basic configuration menu"""
        while True:
            self.clear_screen()
            print("⚙️ Basic Configuration\n" + "=" * 30)
            print(f"Name: {self.config['name'] or 'Not set'}")
            print(f"Email: {self.config['email'] or 'Not set'}")
            print(f"Default Branch: {self.config['default_branch']}")
            print(f"Default Remote: {self.config['default_remote']}")
            print(f"Auto Push: {self.config['auto_push']}")
            print(f"Show Emoji: {self.config['show_emoji']}")
            print("-" * 50)
            
            options = [
                "Set Name", "Set Email", "Set Default Branch", "Set Default Remote",
                "Toggle Auto Push", "Toggle Emoji", "Back to configuration menu"
            ]
            
            choice = self.get_choice("Basic Configuration Options:", options)
            
            config_handlers = {
                "Set Name": lambda: self.update_config('name', self.get_input("Enter your name", self.config['name'])),
                "Set Email": lambda: self.update_config('email', self.get_input("Enter your email", self.config['email'])),
                "Set Default Branch": lambda: self.update_config('default_branch', self.get_input("Enter default branch", self.config['default_branch'])),
                "Set Default Remote": self.interactive_set_default_remote_config,
                "Toggle Auto Push": lambda: self.toggle_config('auto_push'),
                "Toggle Emoji": lambda: self.toggle_config('show_emoji'),
                "Back to configuration menu": lambda: None
            }
            
            for key, handler in config_handlers.items():
                if key in choice:
                    result = handler()
                    if key == "Back to configuration menu":
                        return
                    break
            
            if "Back to configuration menu" not in choice:
                time.sleep(1)
    
    def interactive_advanced_features_menu(self):
        """Interactive advanced features configuration menu"""
        while True:
            self.clear_screen()
            print("🚀 Advanced Features Configuration\n" + "=" * 40)
            
            # Show current feature status
            features = self.config.get('advanced_features', {})
            for feature_name, feature_config in features.items():
                status = "✅ Configured" if feature_config else "⚠️  Default"
                print(f"{feature_name.replace('_', ' ').title()}: {status}")
            
            print("-" * 50)
            
            options = [
                "🗂️  Stash Management", "📝 Commit Templates", "🔀 Branch Workflows",
                "⚔️  Conflict Resolution", "🏥 Repository Health", "💾 Smart Backup",
                "🔧 All Features Overview", "Back to configuration menu"
            ]
            
            choice = self.get_choice("Select Feature to Configure:", options)
            
            feature_handlers = {
                "Stash Management": lambda: self.interactive_feature_config_menu('stash_management'),
                "Commit Templates": lambda: self.interactive_feature_config_menu('commit_templates'),
                "Branch Workflows": lambda: self.interactive_feature_config_menu('branch_workflows'),
                "Conflict Resolution": lambda: self.interactive_feature_config_menu('conflict_resolution'),
                "Repository Health": lambda: self.interactive_feature_config_menu('health_dashboard'),
                "Smart Backup": lambda: self.interactive_feature_config_menu('backup_system'),
                "All Features Overview": self.interactive_all_features_overview,
                "Back to configuration menu": lambda: None
            }
            
            for key, handler in feature_handlers.items():
                if key in choice:
                    result = handler()
                    if key == "Back to configuration menu":
                        return
                    break
    
    def interactive_feature_config_menu(self, feature_name: str):
        """
        Interactive configuration menu for a specific feature.
        
        Args:
            feature_name: Name of the feature to configure
        """
        feature_display_name = feature_name.replace('_', ' ').title()
        
        while True:
            self.clear_screen()
            print(f"⚙️ {feature_display_name} Configuration\n" + "=" * 50)
            
            # Get current feature configuration
            feature_config = self.get_feature_config(feature_name)
            
            # Display current settings
            for key, value in feature_config.items():
                display_key = key.replace('_', ' ').title()
                if isinstance(value, bool):
                    display_value = "✅ Enabled" if value else "❌ Disabled"
                elif isinstance(value, list):
                    display_value = f"[{', '.join(map(str, value))}]"
                else:
                    display_value = str(value)
                print(f"{display_key}: {display_value}")
            
            print("-" * 50)
            
            # Generate options based on feature configuration
            options = self._get_feature_config_options(feature_name, feature_config)
            options.extend(["Reset to Defaults", "Back to features menu"])
            
            choice = self.get_choice(f"{feature_display_name} Options:", options)
            
            if "Reset to Defaults" in choice:
                if self.confirm(f"Reset {feature_display_name} to default settings?", False):
                    self.reset_config_to_defaults(feature_name)
                    time.sleep(1)
            elif "Back to features menu" in choice:
                return
            else:
                self._handle_feature_config_choice(feature_name, choice, feature_config)
                time.sleep(1)
    
    def _get_feature_config_options(self, feature_name: str, feature_config: Dict) -> List[str]:
        """
        Get configuration options for a specific feature.
        
        Args:
            feature_name: Name of the feature
            feature_config: Current feature configuration
            
        Returns:
            List of configuration option strings
        """
        options = []
        
        for key, value in feature_config.items():
            display_key = key.replace('_', ' ').title()
            
            if isinstance(value, bool):
                action = "Disable" if value else "Enable"
                options.append(f"{action} {display_key}")
            elif isinstance(value, (int, float)):
                options.append(f"Set {display_key}")
            elif isinstance(value, str):
                options.append(f"Change {display_key}")
            elif isinstance(value, list):
                options.append(f"Modify {display_key}")
        
        return options
    
    def _handle_feature_config_choice(self, feature_name: str, choice: str, feature_config: Dict):
        """
        Handle a feature configuration choice.
        
        Args:
            feature_name: Name of the feature
            choice: User's choice
            feature_config: Current feature configuration
        """
        # Extract the key from the choice
        for key, value in feature_config.items():
            display_key = key.replace('_', ' ').title()
            
            if display_key in choice:
                if isinstance(value, bool):
                    # Toggle boolean value
                    new_value = not value
                    self.set_feature_config(feature_name, key, new_value)
                    status = "enabled" if new_value else "disabled"
                    self.print_success(f"{display_key} {status}!")
                    
                elif isinstance(value, (int, float)):
                    # Get numeric input
                    new_value = self._get_numeric_input(key, value, feature_name)
                    if new_value is not None:
                        self.set_feature_config(feature_name, key, new_value)
                        self.print_success(f"{display_key} set to {new_value}!")
                    
                elif isinstance(value, str):
                    # Get string input
                    new_value = self.get_input(f"Enter new {display_key.lower()}", value)
                    if new_value:
                        self.set_feature_config(feature_name, key, new_value)
                        self.print_success(f"{display_key} updated!")
                    
                elif isinstance(value, list):
                    # Handle list input
                    self._handle_list_config(feature_name, key, value, display_key)
                
                break
    
    def _get_numeric_input(self, key: str, current_value: float, feature_name: str) -> Optional[float]:
        """
        Get numeric input with validation.
        
        Args:
            key: Configuration key
            current_value: Current value
            feature_name: Name of the feature
            
        Returns:
            New numeric value or None if invalid
        """
        try:
            input_str = self.get_input(f"Enter new value for {key.replace('_', ' ')}", str(current_value))
            if not input_str:
                return None
            
            # Try to parse as int first, then float
            try:
                new_value = int(input_str)
            except ValueError:
                new_value = float(input_str)
            
            # Validate the value
            if self._validate_feature_config_value(feature_name, key, new_value):
                return new_value
            else:
                self.print_error("Invalid value! Please check the allowed range.")
                return None
                
        except ValueError:
            self.print_error("Please enter a valid number!")
            return None
    
    def _handle_list_config(self, feature_name: str, key: str, current_list: List, display_key: str):
        """
        Handle list configuration editing.
        
        Args:
            feature_name: Name of the feature
            key: Configuration key
            current_list: Current list value
            display_key: Display name for the key
        """
        while True:
            self.clear_screen()
            print(f"📝 Edit {display_key}\n" + "=" * 30)
            
            if current_list:
                print("Current items:")
                for i, item in enumerate(current_list, 1):
                    print(f"  {i}. {item}")
            else:
                print("No items configured")
            
            print("-" * 30)
            
            options = ["Add Item", "Remove Item", "Clear All", "Done"]
            choice = self.get_choice("List Options:", options)
            
            if "Add Item" in choice:
                new_item = self.get_input("Enter new item")
                if new_item and new_item not in current_list:
                    current_list.append(new_item)
                    self.set_feature_config(feature_name, key, current_list)
                    self.print_success(f"Added '{new_item}'!")
                    time.sleep(1)
                elif new_item in current_list:
                    self.print_error("Item already exists!")
                    time.sleep(1)
                    
            elif "Remove Item" in choice and current_list:
                item_to_remove = self.get_choice("Select item to remove:", current_list)
                current_list.remove(item_to_remove)
                self.set_feature_config(feature_name, key, current_list)
                self.print_success(f"Removed '{item_to_remove}'!")
                time.sleep(1)
                
            elif "Clear All" in choice:
                if self.confirm("Clear all items?", False):
                    current_list.clear()
                    self.set_feature_config(feature_name, key, current_list)
                    self.print_success("All items cleared!")
                    time.sleep(1)
                    
            elif "Done" in choice:
                break
    
    def interactive_all_features_overview(self):
        """Show overview of all feature configurations"""
        self.clear_screen()
        print("🔧 All Features Configuration Overview\n" + "=" * 50)
        
        features = self.config.get('advanced_features', {})
        
        for feature_name, feature_config in features.items():
            print(f"\n📋 {feature_name.replace('_', ' ').title()}:")
            print("-" * 30)
            
            for key, value in feature_config.items():
                display_key = key.replace('_', ' ').title()
                if isinstance(value, bool):
                    display_value = "✅ Yes" if value else "❌ No"
                elif isinstance(value, list):
                    display_value = f"[{len(value)} items]"
                else:
                    display_value = str(value)
                print(f"  {display_key}: {display_value}")
        
        input("\nPress Enter to continue...")
    
    def interactive_import_export_menu(self):
        """Interactive import/export configuration menu"""
        while True:
            self.clear_screen()
            print("📁 Import/Export Configuration\n" + "=" * 40)
            
            options = [
                "Export Configuration", "Import Configuration", 
                "Show Current Config Path", "Back to configuration menu"
            ]
            
            choice = self.get_choice("Import/Export Options:", options)
            
            if "Export Configuration" in choice:
                export_path = self.get_input("Export path (leave empty for default)", "")
                if self.export_config(export_path if export_path else None):
                    time.sleep(2)
                    
            elif "Import Configuration" in choice:
                import_path = self.get_input("Import path")
                if import_path:
                    if self.import_config(import_path):
                        time.sleep(2)
                        
            elif "Show Current Config Path" in choice:
                self.print_info(f"Current config file: {self.config_file.absolute()}")
                time.sleep(2)
                
            elif "Back to configuration menu" in choice:
                return
    
    def interactive_reset_config_menu(self):
        """Interactive reset configuration menu"""
        while True:
            self.clear_screen()
            print("🔄 Reset Configuration\n" + "=" * 30)
            
            options = [
                "Reset Specific Feature", "Reset All Advanced Features", 
                "Reset Everything", "Back to configuration menu"
            ]
            
            choice = self.get_choice("Reset Options:", options)
            
            if "Reset Specific Feature" in choice:
                features = list(self.config.get('advanced_features', {}).keys())
                if features:
                    feature = self.get_choice("Select feature to reset:", features)
                    if self.reset_config_to_defaults(feature):
                        time.sleep(2)
                else:
                    self.print_info("No features configured")
                    time.sleep(2)
                    
            elif "Reset All Advanced Features" in choice:
                if self.confirm("Reset ALL advanced feature settings?", False):
                    default_features = self._get_default_config()['advanced_features']
                    self.config['advanced_features'] = default_features
                    self.save_config()
                    self.print_success("All advanced features reset to defaults!")
                    time.sleep(2)
                    
            elif "Reset Everything" in choice:
                if self.reset_config_to_defaults():
                    time.sleep(2)
                    
            elif "Back to configuration menu" in choice:
                return
    
    def interactive_set_default_remote_config(self):
        """Set default remote from config menu"""
        if not self.is_git_repo():
            self.print_error("Not in a git repository")
            return
        
        remotes = self.get_remotes()
        if not remotes:
            self.print_info("No remotes configured in current repository")
            return
        
        current_default = self.config.get('default_remote', 'origin')
        remote = self.get_choice("Select default remote:", remotes, current_default)
        
        self.config['default_remote'] = remote
        self.save_config()
        self.print_success(f"Default remote set to: {remote}")
    
    def update_config(self, key, value):
        """Update configuration value"""
        if value:
            self.config[key] = value
            self.save_config()
            self.print_success(f"{key.replace('_', ' ').title()} updated!")
    
    def toggle_config(self, key):
        """Toggle boolean configuration value"""
        self.config[key] = not self.config[key]
        self.save_config()
        status = 'enabled' if self.config[key] else 'disabled'
        self.print_success(f"{key.replace('_', ' ').title()} {status}!")
    
    def get_feature_config(self, feature_name: str, key: str = None) -> Any:
        """
        Get feature-specific configuration.
        
        Args:
            feature_name: Name of the feature
            key: Specific configuration key, or None for entire feature config
            
        Returns:
            Configuration value or entire feature config
        """
        feature_config = self.config.get('advanced_features', {}).get(feature_name, {})
        return feature_config.get(key) if key else feature_config
    
    def set_feature_config(self, feature_name: str, key: str, value: Any) -> bool:
        """
        Set feature-specific configuration.
        
        Args:
            feature_name: Name of the feature
            key: Configuration key to set
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if 'advanced_features' not in self.config:
                self.config['advanced_features'] = {}
            if feature_name not in self.config['advanced_features']:
                self.config['advanced_features'][feature_name] = {}
            
            # Validate the value before setting
            if self._validate_feature_config_value(feature_name, key, value):
                self.config['advanced_features'][feature_name][key] = value
                self.save_config()
                return True
            else:
                self.print_error(f"Invalid value for {feature_name}.{key}: {value}")
                return False
                
        except Exception as e:
            self.print_error(f"Failed to set configuration: {str(e)}")
            return False
    
    def _validate_feature_config_value(self, feature_name: str, key: str, value: Any) -> bool:
        """
        Validate a feature configuration value.
        
        Args:
            feature_name: Name of the feature
            key: Configuration key
            value: Value to validate
            
        Returns:
            True if valid, False otherwise
        """
        validation_map = {
            'stash_management': {
                'max_stashes': lambda v: isinstance(v, int) and 1 <= v <= 200,
                'show_preview_lines': lambda v: isinstance(v, int) and 1 <= v <= 50,
                'cleanup_days': lambda v: isinstance(v, int) and 1 <= v <= 365,
                'auto_name_stashes': lambda v: isinstance(v, bool),
                'confirm_deletions': lambda v: isinstance(v, bool),
                'auto_cleanup_old': lambda v: isinstance(v, bool)
            },
            'commit_templates': {
                'default_template': lambda v: isinstance(v, str) and len(v) > 0,
                'auto_suggest': lambda v: isinstance(v, bool),
                'validate_conventional': lambda v: isinstance(v, bool),
                'custom_templates_enabled': lambda v: isinstance(v, bool),
                'template_categories': lambda v: isinstance(v, list) and all(isinstance(x, str) for x in v),
                'require_scope': lambda v: isinstance(v, bool),
                'require_body': lambda v: isinstance(v, bool)
            },
            'branch_workflows': {
                'default_workflow': lambda v: v in ['git_flow', 'github_flow', 'gitlab_flow', 'custom'],
                'auto_track_remotes': lambda v: isinstance(v, bool),
                'base_branch': lambda v: isinstance(v, str) and len(v) > 0,
                'feature_prefix': lambda v: isinstance(v, str),
                'hotfix_prefix': lambda v: isinstance(v, str),
                'release_prefix': lambda v: isinstance(v, str),
                'auto_cleanup_merged': lambda v: isinstance(v, bool),
                'confirm_branch_deletion': lambda v: isinstance(v, bool)
            },
            'conflict_resolution': {
                'preferred_editor': lambda v: isinstance(v, str) and len(v) > 0,
                'auto_stage_resolved': lambda v: isinstance(v, bool),
                'show_conflict_markers': lambda v: isinstance(v, bool),
                'backup_before_resolve': lambda v: isinstance(v, bool),
                'preferred_merge_tool': lambda v: isinstance(v, str) and len(v) > 0,
                'auto_continue_merge': lambda v: isinstance(v, bool)
            },
            'health_dashboard': {
                'stale_branch_days': lambda v: isinstance(v, int) and 1 <= v <= 365,
                'large_file_threshold_mb': lambda v: isinstance(v, (int, float)) and 0.1 <= v <= 1000,
                'auto_refresh': lambda v: isinstance(v, bool),
                'show_contributor_stats': lambda v: isinstance(v, bool),
                'check_remote_branches': lambda v: isinstance(v, bool),
                'warn_large_repo_size_gb': lambda v: isinstance(v, (int, float)) and 0.1 <= v <= 100,
                'max_branches_to_analyze': lambda v: isinstance(v, int) and 10 <= v <= 1000
            },
            'backup_system': {
                'backup_remotes': lambda v: isinstance(v, list) and all(isinstance(x, str) for x in v),
                'auto_backup_branches': lambda v: isinstance(v, list) and all(isinstance(x, str) for x in v),
                'retention_days': lambda v: isinstance(v, int) and 1 <= v <= 3650,
                'backup_frequency': lambda v: v in ['manual', 'daily', 'weekly', 'monthly'],
                'compress_backups': lambda v: isinstance(v, bool),
                'verify_backup_integrity': lambda v: isinstance(v, bool),
                'notification_on_failure': lambda v: isinstance(v, bool),
                'max_backup_size_gb': lambda v: isinstance(v, (int, float)) and 0.1 <= v <= 100
            }
        }
        
        if feature_name in validation_map and key in validation_map[feature_name]:
            try:
                return validation_map[feature_name][key](value)
            except Exception:
                return False
        
        # If no specific validation rule, allow any value
        return True
    
    def show_help(self):
        """Show comprehensive help information with feature-specific documentation"""
        # Use the dedicated help system if available
        help_system = self.get_feature_manager('help')
        if help_system:
            help_system.show_help()
            return
            
        # Fallback to basic help if help system is not available
        self.clear_screen()
        print("❓ Git Wrapper Help\n" + "=" * 25)
        
        # Show main help menu
        help_options = [
            "📖 General Overview",
            "⚡ Quick Commands",
            "🗂️  Stash Management Help",
            "📝 Commit Templates Help", 
            "🔀 Branch Workflows Help",
            "⚔️  Conflict Resolution Help",
            "🏥 Repository Health Help",
            "💾 Smart Backup Help",
            "🔧 Configuration Help",
            "💡 Tips & Best Practices",
            "🚪 Back to Main Menu"
        ]
        
        while True:
            print("\nSelect help topic:")
            for i, option in enumerate(help_options, 1):
                print(f"  {i}. {option}")
            
            try:
                choice = int(input(f"\nEnter choice (1-{len(help_options)}): "))
                if 1 <= choice <= len(help_options):
                    selected_option = help_options[choice-1]
                    
                    if "General Overview" in selected_option:
                        self._show_general_help()
                    elif "Quick Commands" in selected_option:
                        self._show_quick_commands_help()
                    elif "Stash Management" in selected_option:
                        self._show_stash_help()
                    elif "Commit Templates" in selected_option:
                        self._show_templates_help()
                    elif "Branch Workflows" in selected_option:
                        self._show_workflows_help()
                    elif "Conflict Resolution" in selected_option:
                        self._show_conflicts_help()
                    elif "Repository Health" in selected_option:
                        self._show_health_help()
                    elif "Smart Backup" in selected_option:
                        self._show_backup_help()
                    elif "Configuration" in selected_option:
                        self._show_config_help()
                    elif "Tips & Best Practices" in selected_option:
                        self._show_tips_help()
                    elif "Back to Main Menu" in selected_option:
                        return
                    
                    self.clear_screen()
                    print("❓ Git Wrapper Help\n" + "=" * 25)
                else:
                    print("Invalid choice!")
            except ValueError:
                print("Please enter a valid number!")
            except KeyboardInterrupt:
                return
    
    def _show_general_help(self):
        """Show general overview help"""
        self.clear_screen()
        print("📖 General Overview\n" + "=" * 20)
        print("""
🚀 Interactive Git Wrapper - Advanced Git Management Tool

This tool provides an intuitive interface for Git operations with advanced
features for professional development workflows.

🎯 Core Features:
• Interactive menus for all Git operations
• Multi-remote push support (single/multiple/all)
• Advanced stash management with named stashes
• Commit message templates with validation
• Automated branch workflow management
• Interactive conflict resolution assistant
• Repository health monitoring and cleanup
• Smart backup system with multiple destinations

📊 Repository Status:
The tool automatically detects Git repositories and shows:
• Current branch and status
• Uncommitted changes count
• Available remotes and their status

🔄 Workflow Integration:
• Supports Git Flow, GitHub Flow, and GitLab Flow
• Conventional commit message formatting
• Automated branch lifecycle management
• Conflict detection and resolution assistance

🛡️ Safety Features:
• Confirmation prompts for destructive operations
• Automatic backups before major operations
• Rollback capabilities for failed workflows
• Input validation and error handling

Created by Johannes Nguyen
Enhanced with advanced Git workflow features
        """)
        input("\nPress Enter to continue...")
    
    def _show_quick_commands_help(self):
        """Show quick commands help"""
        self.clear_screen()
        print("⚡ Quick Commands\n" + "=" * 18)
        print("""
🚀 Command Line Usage:
Run 'gw' followed by a command for quick access:

📊 Basic Operations:
• gw status     - Show detailed repository status
• gw commit     - Quick commit with interactive message
• gw sync       - Pull latest changes and push current branch
• gw push       - Open push operations menu
• gw config     - Open configuration management

🗂️  Advanced Features (requires Git repository):
• gw stash      - Open stash management interface
• gw templates  - Access commit template system
• gw workflows  - Manage branch workflows
• gw conflicts  - Resolve merge conflicts interactively
• gw health     - View repository health dashboard
• gw backup     - Access smart backup system

💡 Interactive Mode:
• gw            - Launch full interactive menu system

🔧 Configuration:
• All commands respect your configuration settings
• Use 'gw config' to customize behavior
• Settings are saved automatically

⌨️  Keyboard Shortcuts:
• Ctrl+C        - Exit current operation
• Enter         - Accept default values (shown in [brackets])
• Tab           - Auto-complete where available

🎯 Examples:
gw status       # Quick status check
gw commit       # Interactive commit process
gw sync         # Pull and push in one command
gw             # Full interactive experience
        """)
        input("\nPress Enter to continue...")
    
    def _show_stash_help(self):
        """Show stash management help"""
        self.clear_screen()
        print("🗂️  Stash Management Help\n" + "=" * 25)
        print("""
🎯 Purpose:
Advanced stash management with named stashes, search capabilities,
and enhanced organization for temporary changes.

✨ Key Features:
• Named stashes with custom descriptions
• Search stashes by name or content
• Preview stash contents before applying
• Organized stash listing with timestamps
• Batch stash operations

📋 Main Operations:

1️⃣  Create Named Stash:
   • Save current changes with a custom name
   • Add optional description for context
   • Automatically includes untracked files option

2️⃣  List & Browse Stashes:
   • View all stashes with names and timestamps
   • See stash content preview
   • Navigate through stash history

3️⃣  Search Stashes:
   • Find stashes by custom name
   • Search within stash content
   • Filter by date or file patterns

4️⃣  Apply/Pop Stashes:
   • Apply stash while keeping it in stash list
   • Pop stash (apply and remove from list)
   • Handle conflicts during application

5️⃣  Stash Management:
   • Delete individual stashes with confirmation
   • Clean up old stashes automatically
   • Export/import stash metadata

🔧 Configuration Options:
• auto_name_stashes: Automatically suggest names
• max_stashes: Maximum number of stashes to keep
• show_preview_lines: Lines to show in preview
• confirm_deletions: Require confirmation for deletions

💡 Best Practices:
• Use descriptive names for stashes
• Regular cleanup of old stashes
• Preview before applying to avoid conflicts
• Use search to quickly find specific changes

🗃️  Storage:
Stash metadata is stored in .git/gitwrapper_stashes.json
        """)
        input("\nPress Enter to continue...")
    
    def _show_templates_help(self):
        """Show commit templates help"""
        self.clear_screen()
        print("📝 Commit Templates Help\n" + "=" * 24)
        print("""
🎯 Purpose:
Standardize commit messages using predefined templates with
support for Conventional Commits and custom formats.

✨ Key Features:
• Pre-built templates for common commit types
• Conventional Commits format support
• Custom template creation and management
• Template validation and suggestions
• Interactive template application

📋 Built-in Templates:

🚀 feat: New features
   Format: feat(scope): description
   Example: feat(auth): add user login system

🐛 fix: Bug fixes
   Format: fix(scope): description
   Example: fix(api): handle null response errors

📚 docs: Documentation changes
   Format: docs(scope): description
   Example: docs(readme): update installation guide

🎨 style: Code style changes
   Format: style(scope): description
   Example: style(components): fix indentation

♻️  refactor: Code refactoring
   Format: refactor(scope): description
   Example: refactor(utils): extract common functions

✅ test: Test additions/changes
   Format: test(scope): description
   Example: test(auth): add login validation tests

🔧 chore: Maintenance tasks
   Format: chore(scope): description
   Example: chore(deps): update dependencies

🔧 Template Management:

1️⃣  Select Template:
   • Browse available templates by category
   • Preview template structure
   • See example usage

2️⃣  Apply Template:
   • Fill in template placeholders
   • Validate conventional commit format
   • Preview final commit message

3️⃣  Custom Templates:
   • Create your own templates
   • Define required/optional fields
   • Set validation rules

4️⃣  Template Validation:
   • Conventional Commits syntax checking
   • Required field validation
   • Format consistency checks

🔧 Configuration Options:
• default_template: Default template to suggest
• auto_suggest: Automatically suggest templates
• validate_conventional: Enable format validation
• require_scope: Make scope field mandatory
• require_body: Require commit body text

💡 Best Practices:
• Use consistent commit types across team
• Include scope for better organization
• Write clear, descriptive commit messages
• Follow conventional commit format for automation

🗃️  Storage:
Templates are stored in ~/.gitwrapper_templates.json
        """)
        input("\nPress Enter to continue...")
    
    def _show_workflows_help(self):
        """Show branch workflows help"""
        self.clear_screen()
        print("🔀 Branch Workflows Help\n" + "=" * 24)
        print("""
🎯 Purpose:
Automate branch management following established Git workflows
like Git Flow, GitHub Flow, and GitLab Flow.

✨ Key Features:
• Multiple workflow type support
• Automated branch naming conventions
• Merge strategy management
• Remote tracking setup
• Workflow rollback capabilities

📋 Supported Workflows:

🌊 Git Flow:
   • feature/ branches for new features
   • hotfix/ branches for urgent fixes
   • release/ branches for version releases
   • Automatic base branch detection (develop/main)

🐙 GitHub Flow:
   • Feature branches from main
   • Pull request integration ready
   • Simple merge back to main

🦊 GitLab Flow:
   • Environment-based branching
   • Feature branches with environment promotion
   • Release branch management

🔧 Workflow Operations:

1️⃣  Start Feature Branch:
   • Automatically create from base branch
   • Apply naming conventions
   • Set up remote tracking
   • Initialize branch metadata

2️⃣  Work on Feature:
   • Regular commit and push operations
   • Conflict detection and resolution
   • Progress tracking

3️⃣  Finish Feature:
   • Choose merge strategy (merge/rebase/squash)
   • Automatic conflict resolution
   • Clean up local and remote branches
   • Update base branch

4️⃣  Hotfix Management:
   • Emergency fix workflows
   • Automatic versioning
   • Multi-branch deployment

🔧 Merge Strategies:

🔀 Merge Commit:
   • Preserves branch history
   • Clear feature boundaries
   • Good for collaborative features

📏 Rebase:
   • Linear history
   • Clean commit timeline
   • Good for small features

🗜️  Squash Merge:
   • Single commit per feature
   • Clean main branch history
   • Good for atomic features

🔧 Configuration Options:
• default_workflow: Preferred workflow type
• auto_track_remotes: Automatic remote setup
• base_branch: Default base branch (main/develop)
• feature_prefix: Branch naming prefix
• auto_cleanup_merged: Clean up after merge

💡 Best Practices:
• Choose workflow that fits team size
• Use descriptive branch names
• Regular integration with base branch
• Test before finishing features

🗃️  Storage:
Workflow config stored in .git/gitwrapper_workflows.json
        """)
        input("\nPress Enter to continue...")
    
    def _show_conflicts_help(self):
        """Show conflict resolution help"""
        self.clear_screen()
        print("⚔️  Conflict Resolution Help\n" + "=" * 27)
        print("""
🎯 Purpose:
Interactive assistance for resolving merge conflicts with
visual tools and automated resolution strategies.

✨ Key Features:
• Visual conflict highlighting
• Multiple resolution strategies
• Editor integration
• Conflict preview and comparison
• Automated resolution for simple conflicts

📋 Conflict Resolution Process:

1️⃣  Conflict Detection:
   • Automatic detection during merge operations
   • List all conflicted files
   • Show conflict summary and statistics

2️⃣  Conflict Analysis:
   • Preview conflicted sections
   • Show both versions side-by-side
   • Highlight conflict markers (<<<, ===, >>>)

3️⃣  Resolution Strategies:

   🏠 Accept Ours:
   • Keep local version (current branch)
   • Discard incoming changes
   • Good for protecting local work

   🌐 Accept Theirs:
   • Keep remote version (merging branch)
   • Discard local changes
   • Good for accepting upstream changes

   ✏️  Manual Edit:
   • Open file in configured editor
   • Manually resolve conflicts
   • Full control over final result

   🤖 Auto-resolve:
   • Automatic resolution for simple conflicts
   • Non-overlapping changes
   • Safe merge of compatible changes

4️⃣  Conflict Finalization:
   • Stage resolved files
   • Complete merge commit
   • Verify resolution success

🔧 Editor Integration:
• Supports popular editors (VS Code, Vim, Emacs)
• Syntax highlighting for conflict markers
• Side-by-side diff view
• Jump to next/previous conflict

🔧 Advanced Features:

🔍 Conflict Preview:
   • Show conflicts without applying changes
   • Compare different resolution strategies
   • Preview final result

🔄 Merge Tools:
   • Integration with external merge tools
   • Visual diff and merge interfaces
   • Three-way merge support

📊 Conflict Statistics:
   • Number of conflicted files
   • Types of conflicts (content, rename, delete)
   • Resolution progress tracking

🔧 Configuration Options:
• preferred_editor: Default editor for manual resolution
• auto_stage_resolved: Automatically stage resolved files
• show_conflict_markers: Highlight conflict markers
• backup_before_resolve: Create backup before resolution

💡 Best Practices:
• Understand both versions before resolving
• Test resolved code before committing
• Use meaningful commit messages for merges
• Regular integration to minimize conflicts

⚠️  Safety Features:
• Automatic backups before resolution
• Rollback capability for failed merges
• Confirmation prompts for destructive actions
        """)
        input("\nPress Enter to continue...")
    
    def _show_health_help(self):
        """Show repository health help"""
        self.clear_screen()
        print("🏥 Repository Health Help\n" + "=" * 26)
        print("""
🎯 Purpose:
Monitor repository health, identify issues, and provide
cleanup recommendations for optimal Git repository maintenance.

✨ Key Features:
• Branch analysis and cleanup recommendations
• Large file detection and management
• Repository statistics and metrics
• Stale branch identification
• Automated health scoring

📋 Health Dashboard Sections:

1️⃣  Branch Analysis:
   📊 Active Branches:
   • List all local and remote branches
   • Show ahead/behind status vs main branch
   • Identify merge status and relationships

   🗑️  Stale Branches:
   • Find branches older than threshold (default: 30 days)
   • Show last commit date and author
   • Recommend branches for cleanup

   🔀 Unmerged Branches:
   • Identify branches not merged to main
   • Show unique commits per branch
   • Highlight potential work in progress

2️⃣  Repository Statistics:
   📈 Size Metrics:
   • Total repository size
   • Object count and pack statistics
   • Growth trends over time

   👥 Contributor Analysis:
   • Active contributors and commit counts
   • Contribution patterns and frequency
   • Team collaboration metrics

   📅 Activity Metrics:
   • Commit frequency over time
   • Peak activity periods
   • Development velocity trends

3️⃣  File Analysis:
   📦 Large Files:
   • Files exceeding size threshold (default: 10MB)
   • Binary file detection and analysis
   • Storage optimization recommendations

   🗂️  File Type Distribution:
   • Code vs documentation vs assets
   • Language distribution statistics
   • File organization insights

4️⃣  Health Scoring:
   🎯 Overall Score:
   • Composite health score (0-100)
   • Weighted scoring across categories
   • Trend analysis over time

   ⚠️  Issue Categories:
   • Critical: Immediate attention required
   • Warning: Should be addressed soon
   • Info: Optimization opportunities

📋 Cleanup Recommendations:

🧹 Automated Cleanup:
• Delete merged branches
• Remove stale remote tracking branches
• Clean up unreferenced objects
• Optimize repository packing

🔍 Manual Review:
• Large files that could be moved to LFS
• Branches that might need merging
• Contributors who might need access review
• Configuration optimizations

🔧 Configuration Options:
• stale_branch_days: Days before branch considered stale
• large_file_threshold_mb: Size threshold for large files
• auto_refresh: Automatically refresh dashboard
• show_contributor_stats: Include contributor analysis
• max_branches_to_analyze: Limit for performance

📊 Export Options:
• JSON format for automation
• Text report for documentation
• CSV format for spreadsheet analysis
• Integration with external tools

💡 Best Practices:
• Regular health checks (weekly/monthly)
• Address critical issues promptly
• Use cleanup recommendations as guidelines
• Monitor trends over time

🔄 Automation:
• Schedule regular health checks
• Set up alerts for critical issues
• Integrate with CI/CD pipelines
• Export metrics for monitoring systems
        """)
        input("\nPress Enter to continue...")
    
    def _show_backup_help(self):
        """Show smart backup help"""
        self.clear_screen()
        print("💾 Smart Backup Help\n" + "=" * 20)
        print("""
🎯 Purpose:
Automated backup system for protecting important branches
with multiple destinations and intelligent scheduling.

✨ Key Features:
• Multiple backup destinations
• Scheduled and event-based backups
• Backup verification and integrity checks
• Restoration with conflict detection
• Retention policy management

📋 Backup System Components:

1️⃣  Backup Configuration:
   🎯 Backup Remotes:
   • Configure multiple backup destinations
   • Support for different remote types (Git, cloud)
   • Automatic remote verification and testing

   📅 Backup Schedules:
   • Time-based: Daily, weekly, monthly
   • Event-based: Before major operations
   • Manual: On-demand backup creation

   🎛️  Backup Policies:
   • Which branches to backup automatically
   • Retention periods for old backups
   • Compression and optimization settings

2️⃣  Backup Operations:
   💾 Create Backup:
   • Single branch or multiple branches
   • Full repository or incremental
   • Metadata and configuration backup

   📋 List Backups:
   • View all available backup versions
   • Show backup dates and contents
   • Compare backup versions

   🔄 Restore Backup:
   • Restore specific branches or entire repository
   • Conflict detection with current state
   • Selective restoration options

3️⃣  Backup Types:

   🔄 Incremental Backups:
   • Only backup changes since last backup
   • Faster backup process
   • Efficient storage usage

   📦 Full Backups:
   • Complete repository backup
   • Independent restore capability
   • Higher storage requirements

   🎯 Selective Backups:
   • Backup specific branches only
   • Custom file inclusion/exclusion
   • Metadata-only backups

4️⃣  Backup Destinations:

   🌐 Remote Git Repositories:
   • GitHub, GitLab, Bitbucket
   • Self-hosted Git servers
   • Multiple remote redundancy

   ☁️  Cloud Storage:
   • Integration with cloud providers
   • Encrypted backup storage
   • Cross-region redundancy

   💽 Local Storage:
   • External drives and NAS
   • Network attached storage
   • Local backup verification

🔧 Advanced Features:

🔐 Security:
• Backup encryption options
• Secure credential management
• Access control and permissions

📊 Monitoring:
• Backup success/failure notifications
• Storage usage monitoring
• Backup performance metrics

🔄 Automation:
• Pre-commit backup hooks
• CI/CD integration
• Automated testing of backups

🔧 Configuration Options:
• backup_remotes: List of backup destinations
• auto_backup_branches: Branches to backup automatically
• retention_days: How long to keep backups
• backup_frequency: How often to backup
• compress_backups: Enable backup compression
• verify_backup_integrity: Verify backup after creation

💡 Best Practices:
• Multiple backup destinations for redundancy
• Regular backup verification and testing
• Appropriate retention policies
• Monitor backup storage usage
• Test restoration procedures regularly

⚠️  Important Notes:
• Backups include commit history and metadata
• Large repositories may take time to backup
• Network connectivity required for remote backups
• Verify backup integrity regularly

🗃️  Storage:
Backup logs stored in ~/.gitwrapper_backups.log
        """)
        input("\nPress Enter to continue...")
    
    def _show_config_help(self):
        """Show configuration help"""
        self.clear_screen()
        print("🔧 Configuration Help\n" + "=" * 21)
        print("""
🎯 Purpose:
Comprehensive configuration management for all Git Wrapper
features with validation, import/export, and reset capabilities.

✨ Key Features:
• Feature-specific configuration sections
• Configuration validation and migration
• Import/export configuration profiles
• Reset to defaults with granular control
• Interactive configuration menus

📋 Configuration Categories:

1️⃣  Basic Settings:
   👤 User Information:
   • name: Your name for commits
   • email: Your email for commits
   • default_branch: Preferred default branch name

   🎨 Interface Settings:
   • show_emoji: Enable/disable emoji in output
   • auto_push: Automatically push after commits
   • default_remote: Preferred remote for operations

2️⃣  Advanced Feature Settings:

   🗂️  Stash Management:
   • auto_name_stashes: Suggest names automatically
   • max_stashes: Maximum stashes to keep
   • show_preview_lines: Lines in stash preview
   • confirm_deletions: Require deletion confirmation

   📝 Commit Templates:
   • default_template: Default template type
   • auto_suggest: Automatically suggest templates
   • validate_conventional: Enable format validation
   • require_scope: Make scope field mandatory

   🔀 Branch Workflows:
   • default_workflow: Preferred workflow type
   • auto_track_remotes: Automatic remote tracking
   • base_branch: Default base branch
   • auto_cleanup_merged: Clean up after merge

   ⚔️  Conflict Resolution:
   • preferred_editor: Default editor for conflicts
   • auto_stage_resolved: Auto-stage resolved files
   • show_conflict_markers: Highlight markers
   • backup_before_resolve: Create safety backups

   🏥 Repository Health:
   • stale_branch_days: Days before branch is stale
   • large_file_threshold_mb: Large file size limit
   • auto_refresh: Auto-refresh dashboard
   • max_branches_to_analyze: Analysis limit

   💾 Smart Backup:
   • backup_remotes: List of backup destinations
   • auto_backup_branches: Branches to backup
   • retention_days: Backup retention period
   • backup_frequency: How often to backup

🔧 Configuration Management:

📝 Interactive Configuration:
• Feature-by-feature configuration menus
• Input validation and help text
• Preview changes before saving
• Undo/redo configuration changes

📤 Export Configuration:
• Export to JSON file for sharing
• Create configuration templates
• Backup current configuration
• Share team configuration standards

📥 Import Configuration:
• Import from JSON file
• Merge with existing configuration
• Validate imported settings
• Apply team configuration standards

🔄 Reset Configuration:
• Reset all settings to defaults
• Reset specific feature settings
• Selective configuration reset
• Confirmation prompts for safety

🔧 Configuration Files:

🏠 User Configuration:
Location: ~/.gitwrapper_config.json
• Global settings for all repositories
• User preferences and defaults
• Feature enable/disable settings

🗂️  Repository-Specific:
Location: .git/gitwrapper_*.json
• Repository-specific overrides
• Local workflow configurations
• Project-specific settings

📋 Configuration Validation:

✅ Automatic Validation:
• Type checking for all values
• Range validation for numeric settings
• Path validation for file/directory settings
• Format validation for structured data

🔧 Migration Support:
• Automatic migration between versions
• Backward compatibility maintenance
• Configuration upgrade notifications
• Safe migration with backups

💡 Best Practices:
• Regular configuration backups
• Team configuration standardization
• Feature-specific customization
• Performance-conscious settings

🔧 Troubleshooting:
• Configuration validation errors
• Reset to defaults if corrupted
• Import/export for configuration transfer
• Debug mode for detailed logging

🗃️  Storage:
Main config: ~/.gitwrapper_config.json
Backups: ~/.gitwrapper_config.json.backup
        """)
        input("\nPress Enter to continue...")
    
    def _show_tips_help(self):
        """Show tips and best practices"""
        self.clear_screen()
        print("💡 Tips & Best Practices\n" + "=" * 26)
        print("""
🎯 General Usage Tips:

⌨️  Navigation:
• Use Ctrl+C to exit any operation safely
• Default values are shown in [brackets] - just press Enter
• Numbers in menus correspond to options
• Most operations have confirmation prompts

🔄 Workflow Efficiency:
• Use quick commands (gw status, gw commit) for speed
• Set up default remote to avoid repeated selections
• Enable auto_push for streamlined commits
• Use named stashes for better organization

📋 Feature-Specific Best Practices:

🗂️  Stash Management:
• Use descriptive names for stashes
• Regular cleanup prevents clutter
• Preview stashes before applying
• Search functionality saves time with many stashes

📝 Commit Templates:
• Adopt Conventional Commits for consistency
• Use scopes to organize changes by component
• Create custom templates for team standards
• Enable validation to catch format errors

🔀 Branch Workflows:
• Choose workflow that matches team size
• Use feature branches for all new work
• Regular integration prevents large conflicts
• Clean up merged branches promptly

⚔️  Conflict Resolution:
• Understand both sides before resolving
• Use preview to see conflict context
• Test resolved code before committing
• Keep merge commits descriptive

🏥 Repository Health:
• Run health checks regularly (weekly/monthly)
• Address critical issues promptly
• Use cleanup recommendations as guidelines
• Monitor repository growth trends

💾 Smart Backup:
• Set up multiple backup destinations
• Test restoration procedures regularly
• Use appropriate retention policies
• Monitor backup success/failure

🔧 Performance Tips:

⚡ Speed Optimization:
• Use quick commands for common operations
• Enable lazy loading for large repositories
• Set reasonable limits for analysis operations
• Use incremental backups for large repos

💾 Storage Management:
• Regular cleanup of stale branches
• Monitor large files and consider Git LFS
• Use repository health dashboard insights
• Optimize Git configuration for your workflow

🛡️ Safety Practices:

🔒 Data Protection:
• Always backup before major operations
• Use confirmation prompts for destructive actions
• Test in feature branches before main
• Keep multiple backup destinations

🔍 Quality Assurance:
• Use commit templates for consistency
• Regular conflict resolution practice
• Monitor repository health metrics
• Validate configuration changes

👥 Team Collaboration:

🤝 Team Standards:
• Share configuration profiles
• Establish commit message standards
• Use consistent branch naming
• Regular repository health reviews

📚 Documentation:
• Document custom workflows
• Share best practices with team
• Keep configuration changes documented
• Regular training on advanced features

🔧 Troubleshooting:

🐛 Common Issues:
• Configuration corruption: Reset to defaults
• Feature not working: Check initialization
• Performance issues: Adjust limits in config
• Backup failures: Verify remote connectivity

🔍 Debug Mode:
• Enable debug mode for detailed logging
• Check feature status in configuration menu
• Verify Git repository status
• Review error messages carefully

📞 Getting Help:
• Use context-sensitive help in feature menus
• Check configuration validation messages
• Review operation logs for errors
• Reset problematic features to defaults

🚀 Advanced Usage:

🔧 Customization:
• Create custom commit templates
• Configure workflow-specific settings
• Set up automated backup schedules
• Customize health check thresholds

🔗 Integration:
• Use with existing Git workflows
• Integrate with CI/CD pipelines
• Export metrics for monitoring
• Share configurations across team

Remember: This tool is designed to enhance your Git workflow,
not replace Git knowledge. Understanding Git fundamentals
will help you use these features more effectively!
        """)
        input("\nPress Enter to continue...")
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _initialize_features(self):
        """Initialize all feature managers (lazy loading)"""
        if self._features_initialized:
            return
        
        # Feature definitions with dependencies
        feature_definitions = [
            {
                'name': 'stash',
                'module': 'features.stash_manager',
                'class': 'StashManager',
                'description': 'Stash Management',
                'dependencies': []
            },
            {
                'name': 'templates',
                'module': 'features.commit_template_engine',
                'class': 'CommitTemplateEngine',
                'description': 'Commit Templates',
                'dependencies': []
            },
            {
                'name': 'workflows',
                'module': 'features.branch_workflow_manager',
                'class': 'BranchWorkflowManager',
                'description': 'Branch Workflows',
                'dependencies': []
            },
            {
                'name': 'conflicts',
                'module': 'features.conflict_resolver',
                'class': 'ConflictResolver',
                'description': 'Conflict Resolution',
                'dependencies': []
            },
            {
                'name': 'health',
                'module': 'features.repository_health_dashboard',
                'class': 'RepositoryHealthDashboard',
                'description': 'Repository Health',
                'dependencies': []
            },
            {
                'name': 'backup',
                'module': 'features.smart_backup_system',
                'class': 'SmartBackupSystem',
                'description': 'Smart Backup',
                'dependencies': []
            },
            {
                'name': 'help',
                'module': 'features.help_system',
                'class': 'HelpSystem',
                'description': 'Help System',
                'dependencies': []
            }
        ]
        
        self._feature_managers = {}
        failed_features = []
        
        for feature_def in feature_definitions:
            try:
                # Check dependencies first
                missing_deps = [dep for dep in feature_def['dependencies'] 
                              if dep not in self._feature_managers]
                
                if missing_deps:
                    failed_features.append({
                        'name': feature_def['name'],
                        'description': feature_def['description'],
                        'error': f"Missing dependencies: {', '.join(missing_deps)}"
                    })
                    continue
                
                # Import and initialize the feature
                module = __import__(feature_def['module'], fromlist=[feature_def['class']])
                feature_class = getattr(module, feature_def['class'])
                
                # Initialize with error handling
                feature_instance = feature_class(self)
                
                # Verify the feature has required methods
                if not hasattr(feature_instance, 'interactive_menu'):
                    raise AttributeError(f"Feature {feature_def['class']} missing interactive_menu method")
                
                self._feature_managers[feature_def['name']] = feature_instance
                
            except ImportError as e:
                failed_features.append({
                    'name': feature_def['name'],
                    'description': feature_def['description'],
                    'error': f"Import error: {str(e)}"
                })
            except Exception as e:
                failed_features.append({
                    'name': feature_def['name'],
                    'description': feature_def['description'],
                    'error': f"Initialization error: {str(e)}"
                })
        
        # Log initialization results
        if self._feature_managers:
            available_features = [f['description'] for name, f in 
                                [(name, next(f for f in feature_definitions if f['name'] == name)) 
                                 for name in self._feature_managers.keys()]]
            self.print_info(f"Advanced features available: {', '.join(available_features)}")
        
        if failed_features:
            failed_names = [f['description'] for f in failed_features]
            self.print_info(f"Features not available: {', '.join(failed_names)}")
            
            # In debug mode, show detailed errors
            if self.config.get('debug_mode', False):
                for failed in failed_features:
                    print(f"  {failed['description']}: {failed['error']}")
        
        self._features_initialized = True
    
    def get_feature_manager(self, feature_name: str):
        """
        Get a feature manager by name.
        
        Args:
            feature_name: Name of the feature ('stash', 'templates', 'workflows', etc.)
            
        Returns:
            Feature manager instance or None if not available
        """
        self._initialize_features()
        return self._feature_managers.get(feature_name)
    
    def has_advanced_features(self) -> bool:
        """Check if advanced features are available."""
        self._initialize_features()
        return len(self._feature_managers) > 0
    
    def get_feature_status(self) -> dict:
        """
        Get detailed status of all features.
        
        Returns:
            Dictionary with feature status information
        """
        self._initialize_features()
        
        status = {
            'available_features': list(self._feature_managers.keys()),
            'total_available': len(self._feature_managers),
            'features_initialized': self._features_initialized
        }
        
        # Test each feature's health
        feature_health = {}
        for name, manager in self._feature_managers.items():
            try:
                # Basic health check - ensure interactive_menu method exists and is callable
                if hasattr(manager, 'interactive_menu') and callable(manager.interactive_menu):
                    # Try to access the method to see if it raises an error
                    try:
                        # Just check if we can access it, don't call it
                        _ = manager.interactive_menu
                        feature_health[name] = 'healthy'
                    except Exception as e:
                        feature_health[name] = f'error: {str(e)}'
                else:
                    feature_health[name] = 'missing_interface'
            except Exception as e:
                feature_health[name] = f'error: {str(e)}'
        
        status['feature_health'] = feature_health
        return status
    
    def _handle_feature_menu(self, feature_name: str):
        """
        Handle advanced feature menu selection.
        
        Args:
            feature_name: Name of the feature to access
        """
        if not self.is_git_repo():
            self.print_error("Advanced features require a Git repository!")
            input("Press Enter to continue...")
            return
        
        feature_manager = self.get_feature_manager(feature_name)
        if feature_manager:
            try:
                feature_manager.interactive_menu()
            except Exception as e:
                self.print_error(f"Error in {feature_name} feature: {str(e)}")
                input("Press Enter to continue...")
        else:
            self.print_error(f"Feature '{feature_name}' is not available!")
            input("Press Enter to continue...")
    
    def _detect_platform(self) -> Dict[str, Any]:
        """
        Detect platform-specific information for cross-platform compatibility.
        
        Returns:
            Dictionary with platform information
        """
        system = platform.system().lower()
        
        platform_info = {
            'system': system,
            'is_windows': system == 'windows',
            'is_macos': system == 'darwin',
            'is_linux': system == 'linux',
            'is_unix': system in ['linux', 'darwin', 'freebsd', 'openbsd', 'netbsd'],
            'architecture': platform.machine(),
            'python_version': platform.python_version(),
            'path_separator': os.sep,
            'path_list_separator': os.pathsep,
            'line_ending': '\r\n' if system == 'windows' else '\n',
            'home_dir': Path.home(),
            'temp_dir': self._get_temp_directory(),
            'supports_long_paths': self._check_long_path_support(),
            'filesystem_encoding': sys.getfilesystemencoding(),
            'console_encoding': self._get_console_encoding(),
        }
        
        # Detect Git executable location with enhanced Windows support
        platform_info['git_executable'] = self._find_git_executable()
        
        # Detect shell information with enhanced detection
        if system == 'windows':
            platform_info.update(self._detect_windows_shell())
        else:
            platform_info.update(self._detect_unix_shell())
        
        # Detect Unicode support capabilities (will be updated after encoding setup)
        platform_info['unicode_support'] = {
            'filesystem_unicode': True,
            'console_unicode': False,
            'environment_unicode': True
        }
        
        return platform_info
    
    def _get_temp_directory(self) -> Path:
        """
        Get platform-appropriate temporary directory.
        
        Returns:
            Path to temporary directory
        """
        if platform.system().lower() == 'windows':
            # Windows: Try TEMP, TMP, then fallback
            temp_dir = os.environ.get('TEMP') or os.environ.get('TMP') or r'C:\Windows\Temp'
        else:
            # Unix-like: Try TMPDIR, then fallback
            temp_dir = os.environ.get('TMPDIR') or '/tmp'
        
        return Path(temp_dir)
    
    def _check_long_path_support(self) -> bool:
        """
        Check if the system supports long paths (>260 characters on Windows).
        
        Returns:
            True if long paths are supported
        """
        if platform.system().lower() != 'windows':
            return True  # Unix-like systems generally support long paths
        
        try:
            # Try to create a long path to test support
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                              r'SYSTEM\CurrentControlSet\Control\FileSystem') as key:
                value, _ = winreg.QueryValueEx(key, 'LongPathsEnabled')
                return bool(value)
        except (ImportError, OSError, FileNotFoundError):
            return False
    
    def _get_console_encoding(self) -> str:
        """
        Get the console encoding for the current platform.
        
        Returns:
            Console encoding name
        """
        if platform.system().lower() == 'windows':
            try:
                # Try to get Windows console code page
                import subprocess
                result = subprocess.run(['chcp'], capture_output=True, text=True, shell=True)
                if result.returncode == 0 and result.stdout:
                    # Extract code page number from output like "Active code page: 65001"
                    import re
                    match = re.search(r'(\d+)', result.stdout)
                    if match:
                        cp = int(match.group(1))
                        if cp == 65001:
                            return 'utf-8'
                        elif cp == 1252:
                            return 'cp1252'
                        else:
                            return f'cp{cp}'
            except Exception:
                pass
            return 'cp1252'  # Default Windows encoding
        else:
            return locale.getpreferredencoding() or 'utf-8'
    
    def _detect_windows_shell(self) -> Dict[str, str]:
        """
        Detect Windows shell information.
        
        Returns:
            Dictionary with shell information
        """
        shell_info = {}
        
        # Detect primary shell
        comspec = os.environ.get('COMSPEC', 'cmd.exe')
        shell_info['shell'] = comspec
        
        if 'powershell' in comspec.lower() or 'pwsh' in comspec.lower():
            shell_info['shell_type'] = 'powershell'
        elif 'cmd' in comspec.lower():
            shell_info['shell_type'] = 'cmd'
        else:
            shell_info['shell_type'] = 'unknown'
        
        # Check for Windows Subsystem for Linux (WSL)
        if 'microsoft' in platform.uname().release.lower():
            shell_info['wsl_available'] = True
            shell_info['wsl_version'] = self._detect_wsl_version()
        else:
            shell_info['wsl_available'] = False
        
        # Check for Git Bash
        git_bash_paths = [
            r'C:\Program Files\Git\bin\bash.exe',
            r'C:\Program Files (x86)\Git\bin\bash.exe',
            os.path.expanduser(r'~\AppData\Local\Programs\Git\bin\bash.exe')
        ]
        
        for bash_path in git_bash_paths:
            if os.path.isfile(bash_path):
                shell_info['git_bash_available'] = True
                shell_info['git_bash_path'] = bash_path
                break
        else:
            shell_info['git_bash_available'] = False
        
        return shell_info
    
    def _detect_unix_shell(self) -> Dict[str, str]:
        """
        Detect Unix shell information.
        
        Returns:
            Dictionary with shell information
        """
        shell_info = {}
        
        shell_path = os.environ.get('SHELL', '/bin/sh')
        shell_info['shell'] = shell_path
        
        # Determine shell type from path
        shell_name = os.path.basename(shell_path).lower()
        if 'bash' in shell_name:
            shell_info['shell_type'] = 'bash'
        elif 'zsh' in shell_name:
            shell_info['shell_type'] = 'zsh'
        elif 'fish' in shell_name:
            shell_info['shell_type'] = 'fish'
        elif 'csh' in shell_name or 'tcsh' in shell_name:
            shell_info['shell_type'] = 'csh'
        else:
            shell_info['shell_type'] = 'sh'
        
        return shell_info
    
    def _detect_wsl_version(self) -> str:
        """
        Detect WSL version if running under WSL.
        
        Returns:
            WSL version string
        """
        try:
            with open('/proc/version', 'r') as f:
                version_info = f.read().lower()
                if 'microsoft' in version_info:
                    if 'wsl2' in version_info:
                        return '2'
                    else:
                        return '1'
        except Exception:
            pass
        return 'unknown'
    
    def _check_unicode_support(self, console_encoding: str = 'utf-8') -> Dict[str, bool]:
        """
        Check Unicode support capabilities of the system.
        
        Args:
            console_encoding: Console encoding to test with
        
        Returns:
            Dictionary with Unicode support information
        """
        unicode_info = {
            'filesystem_unicode': True,  # Assume modern filesystems support Unicode
            'console_unicode': False,
            'environment_unicode': True
        }
        
        # Test console Unicode support
        try:
            # Try to encode/decode a Unicode string
            test_string = "café 🚀 测试"
            encoded = test_string.encode(console_encoding)
            decoded = encoded.decode(console_encoding)
            unicode_info['console_unicode'] = (test_string == decoded)
        except (UnicodeEncodeError, UnicodeDecodeError):
            unicode_info['console_unicode'] = False
        
        # Test environment variable Unicode support
        try:
            test_env_var = 'GITWRAPPER_UNICODE_TEST'
            test_value = "café_测试"
            os.environ[test_env_var] = test_value
            retrieved = os.environ.get(test_env_var, '')
            unicode_info['environment_unicode'] = (test_value == retrieved)
            # Clean up
            if test_env_var in os.environ:
                del os.environ[test_env_var]
        except Exception:
            unicode_info['environment_unicode'] = False
        
        return unicode_info
    
    def _find_git_executable(self) -> Optional[str]:
        """
        Find the Git executable on the system with enhanced Windows support.
        
        Returns:
            Path to Git executable, or None if not found
        """
        # Common Git executable names
        git_names = ['git']
        if platform.system().lower() == 'windows':
            git_names.extend(['git.exe', 'git.cmd', 'git.bat'])
        
        # Check PATH first
        for git_name in git_names:
            try:
                if platform.system().lower() == 'windows':
                    # Use 'where' command on Windows
                    result = subprocess.run(
                        ['where', git_name],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        shell=True
                    )
                else:
                    # Use 'which' command on Unix-like systems
                    result = subprocess.run(
                        ['which', git_name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                
                if result.returncode == 0 and result.stdout.strip():
                    git_path = result.stdout.strip().split('\n')[0]
                    # Verify the executable exists and is executable
                    if os.path.isfile(git_path) and os.access(git_path, os.X_OK):
                        return git_path
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        
        # Check common installation paths
        common_paths = []
        if platform.system().lower() == 'windows':
            # Windows-specific paths with more comprehensive search
            program_files = [
                os.environ.get('ProgramFiles', r'C:\Program Files'),
                os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
                r'C:\Program Files',
                r'C:\Program Files (x86)'
            ]
            
            for pf in program_files:
                common_paths.extend([
                    os.path.join(pf, 'Git', 'bin', 'git.exe'),
                    os.path.join(pf, 'Git', 'cmd', 'git.exe'),
                    os.path.join(pf, 'Git', 'mingw64', 'bin', 'git.exe'),
                    os.path.join(pf, 'Git', 'mingw32', 'bin', 'git.exe')
                ])
            
            # Additional Windows paths
            common_paths.extend([
                r'C:\Git\bin\git.exe',
                r'C:\msysgit\bin\git.exe',
                os.path.expanduser(r'~\AppData\Local\Programs\Git\bin\git.exe'),
                os.path.expanduser(r'~\AppData\Local\Programs\Git\cmd\git.exe'),
                os.path.expanduser(r'~\scoop\apps\git\current\bin\git.exe'),
                os.path.expanduser(r'~\scoop\shims\git.exe')
            ])
        else:
            # Unix-like paths
            common_paths.extend([
                '/usr/bin/git',
                '/usr/local/bin/git',
                '/bin/git',
                '/opt/local/bin/git',  # MacPorts
                '/sw/bin/git',         # Fink
            ])
            
            # macOS-specific paths
            if platform.system().lower() == 'darwin':
                common_paths.extend([
                    '/opt/homebrew/bin/git',        # Homebrew on Apple Silicon
                    '/usr/local/homebrew/bin/git',  # Homebrew on Intel
                    '/Applications/Xcode.app/Contents/Developer/usr/bin/git'  # Xcode
                ])
        
        # Test each path
        for path in common_paths:
            try:
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    return path
            except OSError:
                continue
        
        return None
    
    def _get_config_file_path(self) -> Path:
        """
        Get platform-appropriate configuration file path with enhanced cross-platform support.
        
        Returns:
            Path to configuration file
        """
        if platform.system().lower() == 'windows':
            # Windows: Use proper Windows directories
            # Priority: APPDATA > LOCALAPPDATA > USERPROFILE
            config_base = None
            
            # Try APPDATA first (roaming profile)
            if 'APPDATA' in os.environ:
                config_base = Path(os.environ['APPDATA'])
            # Fall back to LOCALAPPDATA (local profile)
            elif 'LOCALAPPDATA' in os.environ:
                config_base = Path(os.environ['LOCALAPPDATA'])
            # Final fallback to user profile
            else:
                config_base = Path(os.path.expanduser('~'))
            
            config_dir = config_base / 'GitWrapper'
            return config_dir / 'config.json'
            
        elif platform.system().lower() == 'darwin':
            # macOS: Use proper macOS directories
            # Follow macOS conventions: ~/Library/Application Support/
            config_dir = Path.home() / 'Library' / 'Application Support' / 'GitWrapper'
            return config_dir / 'config.json'
            
        else:
            # Linux and other Unix-like: Use XDG Base Directory Specification
            xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
            if xdg_config_home:
                config_dir = Path(xdg_config_home) / 'gitwrapper'
            else:
                config_dir = Path.home() / '.config' / 'gitwrapper'
            
            return config_dir / 'config.json'
    
    def _setup_encoding(self) -> None:
        """
        Set up proper encoding for Unicode support across platforms with enhanced handling.
        """
        # Get system encoding with fallbacks
        try:
            self.system_encoding = locale.getpreferredencoding()
            if not self.system_encoding or self.system_encoding.lower() == 'ascii':
                self.system_encoding = 'utf-8'
        except Exception:
            self.system_encoding = 'utf-8'
        
        # Store original stdout/stderr for potential restoration
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        
        # Set up console encoding based on platform
        if platform.system().lower() == 'windows':
            self._setup_windows_encoding()
        else:
            self._setup_unix_encoding()
        
        # Ensure environment variables are properly encoded
        self._fix_environment_encoding()
        
        # Test Unicode support
        self._test_unicode_output()
    
    def _setup_windows_encoding(self) -> None:
        """
        Set up Windows-specific encoding handling.
        """
        try:
            # Try to set console to UTF-8 on Windows 10 version 1903+
            import codecs
            
            # Check Windows version for UTF-8 support
            windows_version = platform.version()
            supports_utf8_console = self._check_windows_utf8_support()
            
            if supports_utf8_console:
                try:
                    # Set console code page to UTF-8
                    subprocess.run(['chcp', '65001'], 
                                 capture_output=True, 
                                 check=False, 
                                 shell=True,
                                 timeout=5)
                    
                    # Wrap stdout/stderr with UTF-8 codec
                    if hasattr(sys.stdout, 'detach'):
                        sys.stdout = codecs.getwriter('utf-8')(
                            sys.stdout.detach(), errors='replace'
                        )
                        sys.stderr = codecs.getwriter('utf-8')(
                            sys.stderr.detach(), errors='replace'
                        )
                    
                    self.console_encoding = 'utf-8'
                    
                except Exception:
                    # Fall back to system encoding
                    self.console_encoding = self.system_encoding
            else:
                # Use Windows default encoding
                self.console_encoding = 'cp1252'
                
        except Exception:
            # Ultimate fallback
            self.console_encoding = self.system_encoding
    
    def _setup_unix_encoding(self) -> None:
        """
        Set up Unix-like system encoding handling.
        """
        try:
            # Check if we're in a UTF-8 locale
            current_locale = locale.getlocale()
            if current_locale[1] and 'utf' in current_locale[1].lower():
                self.console_encoding = 'utf-8'
            else:
                # Try to set UTF-8 locale
                try:
                    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
                    self.console_encoding = 'utf-8'
                except locale.Error:
                    try:
                        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
                        self.console_encoding = 'utf-8'
                    except locale.Error:
                        self.console_encoding = self.system_encoding
        except Exception:
            self.console_encoding = 'utf-8'  # Default assumption for Unix
    
    def _check_windows_utf8_support(self) -> bool:
        """
        Check if Windows supports UTF-8 console output.
        
        Returns:
            True if UTF-8 console is supported
        """
        try:
            # Windows 10 version 1903 (build 18362) and later support UTF-8
            import sys
            if sys.version_info >= (3, 6):
                # Check Windows version
                version_info = platform.version().split('.')
                if len(version_info) >= 3:
                    build = int(version_info[2])
                    return build >= 18362
        except Exception:
            pass
        
        return False
    
    def _test_unicode_output(self) -> None:
        """
        Test Unicode output capabilities and store results.
        """
        self.unicode_test_results = {
            'basic_unicode': False,
            'emoji_support': False,
            'cjk_support': False
        }
        
        test_strings = [
            ('basic_unicode', 'café résumé naïve'),
            ('emoji_support', '🚀 ✅ 🔄'),
            ('cjk_support', '测试 テスト 한국어')
        ]
        
        for test_name, test_string in test_strings:
            try:
                # Try to encode and decode the string
                encoded = test_string.encode(self.console_encoding, errors='replace')
                decoded = encoded.decode(self.console_encoding, errors='replace')
                
                # Check if the round-trip was successful
                self.unicode_test_results[test_name] = (test_string == decoded)
                
            except Exception:
                self.unicode_test_results[test_name] = False
        
        # Update platform info with Unicode support results
        if hasattr(self, 'platform_info'):
            self.platform_info['unicode_support'] = self._check_unicode_support(self.console_encoding)
    
    def _fix_environment_encoding(self) -> None:
        """
        Fix environment variable encoding issues on different platforms with enhanced handling.
        """
        # Environment variables that commonly have encoding issues
        critical_env_vars = [
            'PATH', 'HOME', 'USER', 'USERNAME', 'USERPROFILE',
            'APPDATA', 'LOCALAPPDATA', 'TEMP', 'TMP',
            'SHELL', 'EDITOR', 'PAGER'
        ]
        
        # Git-specific environment variables
        git_env_vars = [
            'GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL',
            'GIT_COMMITTER_NAME', 'GIT_COMMITTER_EMAIL',
            'GIT_EDITOR', 'GIT_PAGER', 'GIT_SSH_COMMAND'
        ]
        
        all_env_vars = critical_env_vars + git_env_vars
        
        for var in all_env_vars:
            if var in os.environ:
                try:
                    value = os.environ[var]
                    
                    # Handle different value types
                    if isinstance(value, bytes):
                        # Decode bytes to string
                        fixed_value = value.decode(self.system_encoding, errors='replace')
                        os.environ[var] = fixed_value
                        
                    elif isinstance(value, str):
                        # Validate string encoding
                        try:
                            # Test if the string can be encoded/decoded properly
                            test_encoded = value.encode(self.system_encoding, errors='strict')
                            test_decoded = test_encoded.decode(self.system_encoding, errors='strict')
                            
                            if test_decoded != value:
                                # Re-encode with error handling
                                fixed_value = value.encode(self.system_encoding, errors='replace').decode(self.system_encoding)
                                os.environ[var] = fixed_value
                                
                        except UnicodeEncodeError:
                            # Handle encoding errors by replacing problematic characters
                            fixed_value = value.encode(self.system_encoding, errors='replace').decode(self.system_encoding)
                            os.environ[var] = fixed_value
                            
                        except UnicodeDecodeError:
                            # This shouldn't happen with strings, but handle it anyway
                            fixed_value = str(value).encode(self.system_encoding, errors='replace').decode(self.system_encoding)
                            os.environ[var] = fixed_value
                            
                except Exception as e:
                    # Log the error if we have an error handler, but don't fail
                    if hasattr(self, 'error_handler') and self.error_handler:
                        self.error_handler.log_warning(f"Could not fix encoding for environment variable {var}: {str(e)}")
        
        # Set default encoding-related environment variables if not present
        if platform.system().lower() != 'windows':
            # Set LANG and LC_ALL for Unix-like systems if not set
            if 'LANG' not in os.environ:
                os.environ['LANG'] = 'en_US.UTF-8'
            
            if 'LC_ALL' not in os.environ:
                # Only set LC_ALL if LANG doesn't contain UTF-8
                lang_value = os.environ.get('LANG', '')
                if 'utf' not in lang_value.lower():
                    os.environ['LC_ALL'] = 'en_US.UTF-8'
    
    def normalize_path(self, path: Union[str, Path]) -> Path:
        """
        Normalize a path for cross-platform compatibility with enhanced handling.
        
        Args:
            path: Path to normalize
            
        Returns:
            Normalized Path object
        """
        if isinstance(path, str):
            # Handle encoding issues in path strings
            try:
                # Ensure the path string is properly encoded
                path = path.encode(self.system_encoding, errors='replace').decode(self.system_encoding)
            except Exception:
                pass
            path = Path(path)
        
        # Resolve path and handle platform-specific issues
        try:
            # Use expanduser to handle ~ in paths
            if str(path).startswith('~'):
                path = path.expanduser()
            
            # Resolve the path
            normalized = path.resolve()
            
            # Platform-specific path handling
            if platform.system().lower() == 'windows':
                normalized = self._normalize_windows_path(normalized)
            else:
                normalized = self._normalize_unix_path(normalized)
            
            return normalized
            
        except Exception as e:
            # If resolution fails, try basic normalization
            try:
                if str(path).startswith('~'):
                    path = path.expanduser()
                return path.absolute()
            except Exception:
                # Ultimate fallback: return the original path
                return path
    
    def _normalize_windows_path(self, path: Path) -> Path:
        """
        Normalize Windows-specific path issues.
        
        Args:
            path: Path to normalize
            
        Returns:
            Normalized Windows path
        """
        path_str = str(path)
        
        # Handle long path names on Windows
        if len(path_str) > 260 and not path_str.startswith('\\\\?\\'):
            # Check if long paths are supported
            if self.platform_info.get('supports_long_paths', False):
                # Add long path prefix for Windows
                path_str = '\\\\?\\' + path_str
                return Path(path_str)
        
        # Handle UNC paths
        if path_str.startswith('\\\\'):
            # This is already a UNC path, leave it as-is
            return path
        
        # Handle drive letters and case sensitivity
        if len(path_str) >= 2 and path_str[1] == ':':
            # Normalize drive letter to uppercase
            path_str = path_str[0].upper() + path_str[1:]
            return Path(path_str)
        
        return path
    
    def _normalize_unix_path(self, path: Path) -> Path:
        """
        Normalize Unix-specific path issues.
        
        Args:
            path: Path to normalize
            
        Returns:
            Normalized Unix path
        """
        path_str = str(path)
        
        # Handle symbolic links
        try:
            if path.is_symlink():
                # Optionally resolve symlinks (can be configured)
                if self.config.get('resolve_symlinks', True):
                    return path.resolve()
        except Exception:
            pass
        
        # Handle hidden files and directories (starting with .)
        # No special handling needed, just return as-is
        
        return path
    
    def safe_path_join(self, *parts) -> Path:
        """
        Safely join path parts with enhanced cross-platform compatibility.
        
        Args:
            *parts: Path parts to join
            
        Returns:
            Joined Path object
        """
        if not parts:
            return Path('.')
        
        # Convert all parts to strings and handle encoding
        safe_parts = []
        for part in parts:
            if part is None:
                continue
                
            if isinstance(part, bytes):
                # Decode bytes to string
                try:
                    part_str = part.decode(self.system_encoding, errors='replace')
                except Exception:
                    part_str = str(part, errors='replace')
            elif isinstance(part, Path):
                part_str = str(part)
            else:
                part_str = str(part)
            
            # Handle encoding issues in the string
            try:
                # Test if the string can be encoded properly
                part_str.encode(self.system_encoding, errors='strict')
            except UnicodeEncodeError:
                # Fix encoding issues
                part_str = part_str.encode(self.system_encoding, errors='replace').decode(self.system_encoding)
            
            # Skip empty parts
            if part_str.strip():
                safe_parts.append(part_str)
        
        if not safe_parts:
            return Path('.')
        
        # Join and normalize
        try:
            joined = Path(*safe_parts)
            return self.normalize_path(joined)
        except Exception:
            # Fallback: join manually
            result = safe_parts[0]
            for part in safe_parts[1:]:
                result = os.path.join(result, part)
            return self.normalize_path(Path(result))
    
    def get_platform_specific_config(self) -> Dict[str, Any]:
        """
        Get platform-specific configuration defaults with enhanced cross-platform support.
        
        Returns:
            Dictionary with platform-specific settings
        """
        config = {
            'encoding': self.system_encoding,
            'console_encoding': getattr(self, 'console_encoding', self.system_encoding),
            'unicode_support': getattr(self, 'unicode_test_results', {}),
            'filesystem_encoding': self.platform_info.get('filesystem_encoding', 'utf-8')
        }
        
        if self.platform_info.get('is_windows', False):
            config.update(self._get_windows_config())
        elif self.platform_info.get('is_macos', False):
            config.update(self._get_macos_config())
        elif self.platform_info.get('is_linux', False):
            config.update(self._get_linux_config())
        else:
            config.update(self._get_unix_config())
        
        return config
    
    def _get_windows_config(self) -> Dict[str, Any]:
        """
        Get Windows-specific configuration.
        
        Returns:
            Dictionary with Windows-specific settings
        """
        config = {
            'line_endings': 'crlf',
            'case_sensitive': False,
            'max_path_length': 32767 if self.platform_info.get('supports_long_paths', False) else 260,
            'shell_command': self.platform_info.get('shell', 'cmd.exe'),
            'shell_type': self.platform_info.get('shell_type', 'cmd'),
            'git_executable': self.platform_info.get('git_executable', 'git.exe'),
            'supports_color': self._check_windows_color_support(),
            'path_separator': '\\',
            'path_list_separator': ';',
            'executable_extensions': ['.exe', '.cmd', '.bat', '.com'],
            'temp_dir': str(self.platform_info.get('temp_dir', r'C:\Windows\Temp')),
        }
        
        # Detect preferred editor
        editors_to_try = [
            ('code', 'Visual Studio Code'),
            ('notepad++', 'Notepad++'),
            ('sublime_text', 'Sublime Text'),
            ('atom', 'Atom'),
            ('vim', 'Vim'),
            ('notepad', 'Notepad')
        ]
        
        config['preferred_editor'] = self._find_preferred_editor(editors_to_try, 'notepad')
        
        # Windows-specific features
        config.update({
            'wsl_available': self.platform_info.get('wsl_available', False),
            'wsl_version': self.platform_info.get('wsl_version', 'unknown'),
            'git_bash_available': self.platform_info.get('git_bash_available', False),
            'git_bash_path': self.platform_info.get('git_bash_path', ''),
            'powershell_available': self._check_powershell_available(),
            'windows_terminal_available': self._check_windows_terminal_available()
        })
        
        return config
    
    def _get_macos_config(self) -> Dict[str, Any]:
        """
        Get macOS-specific configuration.
        
        Returns:
            Dictionary with macOS-specific settings
        """
        config = {
            'line_endings': 'lf',
            'case_sensitive': True,  # HFS+ can be case-insensitive, but APFS is case-sensitive by default
            'max_path_length': 1024,  # macOS path limit
            'shell_command': self.platform_info.get('shell', '/bin/zsh'),  # Default shell on macOS Catalina+
            'shell_type': self.platform_info.get('shell_type', 'zsh'),
            'git_executable': self.platform_info.get('git_executable', '/usr/bin/git'),
            'supports_color': True,
            'path_separator': '/',
            'path_list_separator': ':',
            'executable_extensions': [],  # Unix doesn't use extensions for executables
            'temp_dir': '/tmp',
            'terminal_app': 'Terminal.app',
            'package_manager': self._detect_macos_package_manager()
        }
        
        # Detect preferred editor
        editors_to_try = [
            ('code', 'Visual Studio Code'),
            ('subl', 'Sublime Text'),
            ('atom', 'Atom'),
            ('vim', 'Vim'),
            ('nano', 'Nano'),
            ('emacs', 'Emacs')
        ]
        
        config['preferred_editor'] = self._find_preferred_editor(editors_to_try, 'nano')
        
        # macOS-specific features
        config.update({
            'homebrew_available': self._check_homebrew_available(),
            'xcode_available': self._check_xcode_available(),
            'iterm_available': self._check_iterm_available()
        })
        
        return config
    
    def _get_linux_config(self) -> Dict[str, Any]:
        """
        Get Linux-specific configuration.
        
        Returns:
            Dictionary with Linux-specific settings
        """
        config = {
            'line_endings': 'lf',
            'case_sensitive': True,
            'max_path_length': 4096,
            'shell_command': self.platform_info.get('shell', '/bin/bash'),
            'shell_type': self.platform_info.get('shell_type', 'bash'),
            'git_executable': self.platform_info.get('git_executable', '/usr/bin/git'),
            'supports_color': True,
            'path_separator': '/',
            'path_list_separator': ':',
            'executable_extensions': [],
            'temp_dir': '/tmp',
            'package_manager': self._detect_package_manager(),
            'distribution': self._detect_linux_distribution()
        }
        
        # Detect preferred editor
        editors_to_try = [
            ('code', 'Visual Studio Code'),
            ('subl', 'Sublime Text'),
            ('atom', 'Atom'),
            ('vim', 'Vim'),
            ('nano', 'Nano'),
            ('emacs', 'Emacs'),
            ('gedit', 'Gedit')
        ]
        
        config['preferred_editor'] = self._find_preferred_editor(
            editors_to_try, 
            os.environ.get('EDITOR', 'nano')
        )
        
        return config
    
    def _get_unix_config(self) -> Dict[str, Any]:
        """
        Get generic Unix configuration for other Unix-like systems.
        
        Returns:
            Dictionary with Unix-specific settings
        """
        return {
            'line_endings': 'lf',
            'case_sensitive': True,
            'max_path_length': 4096,
            'shell_command': self.platform_info.get('shell', '/bin/sh'),
            'shell_type': self.platform_info.get('shell_type', 'sh'),
            'git_executable': self.platform_info.get('git_executable', '/usr/bin/git'),
            'supports_color': True,
            'path_separator': '/',
            'path_list_separator': ':',
            'executable_extensions': [],
            'temp_dir': '/tmp',
            'preferred_editor': os.environ.get('EDITOR', 'vi')
        }
    
    def _check_windows_color_support(self) -> bool:
        """
        Check if Windows console supports color output.
        
        Returns:
            True if color is supported
        """
        try:
            # Windows 10 and later support ANSI color codes
            version_info = platform.version().split('.')
            if len(version_info) >= 1:
                major_version = int(version_info[0])
                return major_version >= 10
        except Exception:
            pass
        return False
    
    def _find_preferred_editor(self, editors_to_try: List[Tuple[str, str]], fallback: str) -> str:
        """
        Find the preferred editor from a list of candidates.
        
        Args:
            editors_to_try: List of (command, name) tuples to try
            fallback: Fallback editor if none found
            
        Returns:
            Editor command
        """
        # Check environment variable first
        env_editor = os.environ.get('EDITOR')
        if env_editor:
            return env_editor
        
        # Try each editor in order
        for cmd, name in editors_to_try:
            if self._command_exists(cmd):
                return cmd
        
        return fallback
    
    def _command_exists(self, command: str) -> bool:
        """
        Check if a command exists in PATH.
        
        Args:
            command: Command to check
            
        Returns:
            True if command exists
        """
        try:
            if platform.system().lower() == 'windows':
                result = subprocess.run(
                    ['where', command],
                    capture_output=True,
                    timeout=5,
                    shell=True
                )
            else:
                result = subprocess.run(
                    ['which', command],
                    capture_output=True,
                    timeout=5
                )
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_powershell_available(self) -> bool:
        """
        Check if PowerShell is available on Windows.
        
        Returns:
            True if PowerShell is available
        """
        return self._command_exists('powershell') or self._command_exists('pwsh')
    
    def _check_windows_terminal_available(self) -> bool:
        """
        Check if Windows Terminal is available.
        
        Returns:
            True if Windows Terminal is available
        """
        return self._command_exists('wt')
    
    def _detect_macos_package_manager(self) -> Optional[str]:
        """
        Detect package manager on macOS.
        
        Returns:
            Package manager name or None
        """
        managers = [
            ('brew', '/opt/homebrew/bin/brew'),  # Apple Silicon
            ('brew', '/usr/local/bin/brew'),     # Intel
            ('port', '/opt/local/bin/port'),     # MacPorts
            ('fink', '/sw/bin/fink')             # Fink
        ]
        
        for name, path in managers:
            if os.path.isfile(path):
                return name
        
        return None
    
    def _check_homebrew_available(self) -> bool:
        """
        Check if Homebrew is available on macOS.
        
        Returns:
            True if Homebrew is available
        """
        return self._command_exists('brew')
    
    def _check_xcode_available(self) -> bool:
        """
        Check if Xcode command line tools are available.
        
        Returns:
            True if Xcode tools are available
        """
        return os.path.isdir('/Applications/Xcode.app') or self._command_exists('xcode-select')
    
    def _check_iterm_available(self) -> bool:
        """
        Check if iTerm2 is available on macOS.
        
        Returns:
            True if iTerm2 is available
        """
        return os.path.isdir('/Applications/iTerm.app')
    
    def _detect_package_manager(self) -> Optional[str]:
        """
        Detect the package manager on Linux systems.
        
        Returns:
            Package manager name, or None if not detected
        """
        package_managers = [
            ('apt', '/usr/bin/apt'),
            ('apt-get', '/usr/bin/apt-get'),
            ('yum', '/usr/bin/yum'),
            ('dnf', '/usr/bin/dnf'),
            ('pacman', '/usr/bin/pacman'),
            ('zypper', '/usr/bin/zypper'),
            ('emerge', '/usr/bin/emerge'),
            ('apk', '/sbin/apk'),
            ('snap', '/usr/bin/snap'),
            ('flatpak', '/usr/bin/flatpak')
        ]
        
        for name, path in package_managers:
            if os.path.isfile(path):
                return name
        
        return None
    
    def _detect_linux_distribution(self) -> Optional[str]:
        """
        Detect Linux distribution.
        
        Returns:
            Distribution name or None
        """
        try:
            # Try reading /etc/os-release
            if os.path.isfile('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if line.startswith('ID='):
                            return line.split('=')[1].strip().strip('"')
            
            # Try reading /etc/lsb-release
            if os.path.isfile('/etc/lsb-release'):
                with open('/etc/lsb-release', 'r') as f:
                    for line in f:
                        if line.startswith('DISTRIB_ID='):
                            return line.split('=')[1].strip().strip('"')
            
            # Try other distribution-specific files
            dist_files = [
                ('/etc/redhat-release', 'redhat'),
                ('/etc/debian_version', 'debian'),
                ('/etc/arch-release', 'arch'),
                ('/etc/gentoo-release', 'gentoo'),
                ('/etc/SuSE-release', 'suse')
            ]
            
            for file_path, dist_name in dist_files:
                if os.path.isfile(file_path):
                    return dist_name
                    
        except Exception:
            pass
        
        return None

    def safe_encode_for_git(self, text: str) -> str:
        """
        Safely encode text for Git operations with cross-platform compatibility.
        
        Args:
            text: Text to encode
            
        Returns:
            Safely encoded text
        """
        if not isinstance(text, str):
            text = str(text)
        
        try:
            # Test if the text can be encoded with the system encoding
            text.encode(self.system_encoding, errors='strict')
            return text
        except UnicodeEncodeError:
            # Handle encoding issues by replacing problematic characters
            return text.encode(self.system_encoding, errors='replace').decode(self.system_encoding)
    
    def safe_decode_git_output(self, output: Union[str, bytes]) -> str:
        """
        Safely decode Git command output with cross-platform compatibility.
        
        Args:
            output: Git command output to decode
            
        Returns:
            Safely decoded string
        """
        if isinstance(output, str):
            return output
        
        if isinstance(output, bytes):
            # Try different encodings in order of preference
            encodings_to_try = [
                'utf-8',
                self.system_encoding,
                self.console_encoding,
                'latin-1',  # Fallback that can decode any byte sequence
            ]
            
            for encoding in encodings_to_try:
                try:
                    return output.decode(encoding)
                except (UnicodeDecodeError, LookupError):
                    continue
            
            # Ultimate fallback: decode with errors='replace'
            return output.decode('utf-8', errors='replace')
        
        return str(output)
    
    def format_path_for_display(self, path: Union[str, Path]) -> str:
        """
        Format a path for display with proper Unicode handling.
        
        Args:
            path: Path to format
            
        Returns:
            Formatted path string
        """
        path_str = str(path)
        
        # Handle Unicode characters in paths
        if not self.unicode_test_results.get('basic_unicode', True):
            # If Unicode is not supported, replace problematic characters
            try:
                path_str.encode(self.console_encoding, errors='strict')
            except UnicodeEncodeError:
                path_str = path_str.encode(self.console_encoding, errors='replace').decode(self.console_encoding)
        
        return path_str
    
    def create_cross_platform_temp_file(self, suffix: str = '', prefix: str = 'gitwrapper_') -> Path:
        """
        Create a temporary file with cross-platform compatibility.
        
        Args:
            suffix: File suffix
            prefix: File prefix
            
        Returns:
            Path to temporary file
        """
        import tempfile
        
        # Ensure prefix and suffix are safe for the filesystem
        safe_prefix = self.safe_encode_for_git(prefix)
        safe_suffix = self.safe_encode_for_git(suffix)
        
        # Create temporary file
        temp_fd, temp_path = tempfile.mkstemp(
            suffix=safe_suffix,
            prefix=safe_prefix,
            dir=str(self.platform_info.get('temp_dir', tempfile.gettempdir()))
        )
        
        # Close the file descriptor (we just need the path)
        os.close(temp_fd)
        
        return Path(temp_path)
    
    def get_safe_git_config_value(self, key: str, default: str = '') -> str:
        """
        Get a Git configuration value with safe Unicode handling.
        
        Args:
            key: Git config key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        try:
            result = self.run_git_command(['git', 'config', '--get', key], capture_output=True)
            if result:
                return self.safe_decode_git_output(result)
        except Exception:
            pass
        
        return default
    
    def set_safe_git_config_value(self, key: str, value: str) -> bool:
        """
        Set a Git configuration value with safe Unicode handling.
        
        Args:
            key: Git config key
            value: Value to set
            
        Returns:
            True if successful
        """
        try:
            safe_value = self.safe_encode_for_git(value)
            return self.run_git_command(['git', 'config', key, safe_value])
        except Exception:
            return False

def main():
    """Main entry point"""
    git = InteractiveGitWrapper()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        handlers = {
            'status': git.interactive_status,
            'commit': git.interactive_commit,
            'sync': git.interactive_sync,
            'push': git.interactive_push_menu,
            'config': git.interactive_config_menu,
            'help': git.show_help
        }
        
        if command in handlers:
            handlers[command]()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: status, commit, sync, push, config")
            print("Or run 'gw' without arguments for interactive mode")
    else:
        try:
            git.show_main_menu()
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")

if __name__ == '__main__':
    main()
