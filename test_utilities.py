#!/usr/bin/env python3
"""
Test utilities and helper functions for advanced Git features testing
"""

import os
import tempfile
import shutil
import subprocess
import json
import time
import random
import string
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import Mock, MagicMock, patch
from contextlib import contextmanager


class MockGitRepository:
    """Mock Git repository for isolated testing"""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize mock git repository.
        
        Args:
            temp_dir: Optional temporary directory path
        """
        self.temp_dir = temp_dir or tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        self.git_dir = Path(self.temp_dir) / '.git'
        self.initialized = False
        
    def __enter__(self):
        """Context manager entry"""
        os.chdir(self.temp_dir)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        os.chdir(self.original_cwd)
        if hasattr(self, 'cleanup_on_exit') and self.cleanup_on_exit:
            self.cleanup()
    
    def initialize(self, with_initial_commit: bool = True) -> 'MockGitRepository':
        """
        Initialize the git repository.
        
        Args:
            with_initial_commit: Whether to create an initial commit
            
        Returns:
            Self for method chaining
        """
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True)
        
        if with_initial_commit:
            self.create_file('README.md', '# Test Repository\nInitial content\n')
            self.add_and_commit(['README.md'], 'Initial commit')
        
        self.initialized = True
        return self
    
    def create_file(self, filename: str, content: str) -> Path:
        """
        Create a file with specified content.
        
        Args:
            filename: Name of the file to create
            content: Content to write to the file
            
        Returns:
            Path to the created file
        """
        file_path = Path(self.temp_dir) / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        return file_path
    
    def create_large_file(self, filename: str, size_mb: float) -> Path:
        """
        Create a large file for testing.
        
        Args:
            filename: Name of the file to create
            size_mb: Size of the file in megabytes
            
        Returns:
            Path to the created file
        """
        file_path = Path(self.temp_dir) / filename
        size_bytes = int(size_mb * 1024 * 1024)
        
        with open(file_path, 'w') as f:
            # Write in chunks to avoid memory issues
            chunk_size = 1024
            content_chunk = 'x' * chunk_size
            chunks_needed = size_bytes // chunk_size
            
            for _ in range(chunks_needed):
                f.write(content_chunk)
            
            # Write remaining bytes
            remaining = size_bytes % chunk_size
            if remaining:
                f.write('x' * remaining)
        
        return file_path
    
    def add_and_commit(self, files: List[str], message: str) -> str:
        """
        Add files and create a commit.
        
        Args:
            files: List of file paths to add
            message: Commit message
            
        Returns:
            Commit hash
        """
        for file in files:
            subprocess.run(['git', 'add', file], check=True)
        
        result = subprocess.run(['git', 'commit', '-m', message], 
                              check=True, capture_output=True, text=True)
        
        # Get commit hash
        commit_hash = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                                   capture_output=True, text=True).stdout.strip()
        return commit_hash
    
    def create_branch(self, branch_name: str, checkout: bool = True) -> 'MockGitRepository':
        """
        Create a new branch.
        
        Args:
            branch_name: Name of the branch to create
            checkout: Whether to checkout the new branch
            
        Returns:
            Self for method chaining
        """
        if checkout:
            subprocess.run(['git', 'checkout', '-b', branch_name], check=True, capture_output=True)
        else:
            subprocess.run(['git', 'branch', branch_name], check=True, capture_output=True)
        
        return self
    
    def checkout_branch(self, branch_name: str) -> 'MockGitRepository':
        """
        Checkout an existing branch.
        
        Args:
            branch_name: Name of the branch to checkout
            
        Returns:
            Self for method chaining
        """
        subprocess.run(['git', 'checkout', branch_name], check=True, capture_output=True)
        return self
    
    def create_merge_conflict(self, filename: str, branch1_content: str, 
                            branch2_content: str, base_branch: str = 'main') -> Tuple[str, str]:
        """
        Create a merge conflict scenario.
        
        Args:
            filename: File to create conflict in
            branch1_content: Content for first branch
            branch2_content: Content for second branch
            base_branch: Base branch name
            
        Returns:
            Tuple of (branch1_name, branch2_name)
        """
        branch1_name = f'conflict-branch-1-{random.randint(1000, 9999)}'
        branch2_name = f'conflict-branch-2-{random.randint(1000, 9999)}'
        
        # Create first branch with content
        self.create_branch(branch1_name)
        self.create_file(filename, branch1_content)
        self.add_and_commit([filename], f'Add {filename} on {branch1_name}')
        
        # Go back to base branch
        self.checkout_branch(base_branch)
        
        # Create second branch with conflicting content
        self.create_branch(branch2_name)
        self.create_file(filename, branch2_content)
        self.add_and_commit([filename], f'Add {filename} on {branch2_name}')
        
        return branch1_name, branch2_name
    
    def create_stash(self, message: str = None) -> str:
        """
        Create a git stash.
        
        Args:
            message: Optional stash message
            
        Returns:
            Stash ID
        """
        # Create some changes
        test_file = f'stash_test_{random.randint(1000, 9999)}.py'
        self.create_file(test_file, f'# Stash test content\nprint("stash test")\n')
        
        # Create stash
        cmd = ['git', 'stash', 'push']
        if message:
            cmd.extend(['-m', message])
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Get stash ID
        result = subprocess.run(['git', 'stash', 'list'], capture_output=True, text=True)
        if result.stdout:
            # Extract stash ID from first line
            first_line = result.stdout.split('\n')[0]
            stash_id = first_line.split(':')[0]
            return stash_id
        
        return 'stash@{0}'
    
    def get_current_branch(self) -> str:
        """Get the current branch name."""
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True)
        return result.stdout.strip()
    
    def get_all_branches(self) -> List[str]:
        """Get list of all branches."""
        result = subprocess.run(['git', 'branch'], capture_output=True, text=True)
        branches = []
        for line in result.stdout.split('\n'):
            if line.strip():
                branch = line.strip().replace('* ', '')
                branches.append(branch)
        return branches
    
    def get_commit_count(self) -> int:
        """Get total number of commits."""
        result = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], 
                              capture_output=True, text=True)
        return int(result.stdout.strip()) if result.stdout.strip() else 0
    
    def cleanup(self):
        """Clean up the temporary directory."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestDataGenerator:
    """Generate test data for various repository states"""
    
    @staticmethod
    def generate_random_string(length: int = 10) -> str:
        """Generate a random string of specified length."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def generate_python_file_content(function_name: str = None, class_name: str = None) -> str:
        """
        Generate Python file content for testing.
        
        Args:
            function_name: Optional function name to include
            class_name: Optional class name to include
            
        Returns:
            Python file content as string
        """
        content = f'#!/usr/bin/env python3\n"""Generated test file"""\n\n'
        
        if function_name:
            content += f'''def {function_name}():
    """Generated function for testing"""
    return "{TestDataGenerator.generate_random_string()}"

'''
        
        if class_name:
            content += f'''class {class_name}:
    """Generated class for testing"""
    
    def __init__(self):
        self.data = "{TestDataGenerator.generate_random_string()}"
    
    def get_data(self):
        return self.data

'''
        
        content += f'# Generated at {time.time()}\n'
        return content
    
    @staticmethod
    def generate_commit_messages(count: int, template_type: str = 'conventional') -> List[str]:
        """
        Generate commit messages for testing.
        
        Args:
            count: Number of commit messages to generate
            template_type: Type of commit message template
            
        Returns:
            List of commit messages
        """
        messages = []
        
        if template_type == 'conventional':
            types = ['feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore']
            scopes = ['core', 'ui', 'api', 'auth', 'db', 'config']
            
            for i in range(count):
                commit_type = random.choice(types)
                scope = random.choice(scopes)
                description = f'add {TestDataGenerator.generate_random_string(8).lower()} functionality'
                message = f'{commit_type}({scope}): {description}'
                messages.append(message)
        else:
            # Simple messages
            for i in range(count):
                action = random.choice(['Add', 'Update', 'Fix', 'Remove', 'Improve'])
                subject = TestDataGenerator.generate_random_string(10).lower()
                message = f'{action} {subject}'
                messages.append(message)
        
        return messages
    
    @staticmethod
    def create_complex_repository(repo: MockGitRepository, 
                                num_branches: int = 10,
                                commits_per_branch: int = 5,
                                files_per_commit: int = 3) -> Dict[str, Any]:
        """
        Create a complex repository structure for testing.
        
        Args:
            repo: MockGitRepository instance
            num_branches: Number of branches to create
            commits_per_branch: Number of commits per branch
            files_per_commit: Number of files per commit
            
        Returns:
            Dictionary with repository metadata
        """
        metadata = {
            'branches': [],
            'commits': [],
            'files': [],
            'total_commits': 0
        }
        
        commit_messages = TestDataGenerator.generate_commit_messages(
            num_branches * commits_per_branch
        )
        
        for branch_idx in range(num_branches):
            branch_name = f'feature/branch-{branch_idx:03d}'
            repo.create_branch(branch_name)
            metadata['branches'].append(branch_name)
            
            for commit_idx in range(commits_per_branch):
                files_in_commit = []
                
                for file_idx in range(files_per_commit):
                    filename = f'branch_{branch_idx:03d}_file_{file_idx:03d}.py'
                    content = TestDataGenerator.generate_python_file_content(
                        function_name=f'func_{branch_idx}_{commit_idx}_{file_idx}',
                        class_name=f'Class_{branch_idx}_{commit_idx}_{file_idx}'
                    )
                    repo.create_file(filename, content)
                    files_in_commit.append(filename)
                    metadata['files'].append(filename)
                
                commit_msg = commit_messages[metadata['total_commits']]
                commit_hash = repo.add_and_commit(files_in_commit, commit_msg)
                
                metadata['commits'].append({
                    'hash': commit_hash,
                    'message': commit_msg,
                    'branch': branch_name,
                    'files': files_in_commit
                })
                metadata['total_commits'] += 1
            
            # Go back to main for next branch
            repo.checkout_branch('main')
        
        return metadata


class MockFeatureManager:
    """Mock feature manager for testing"""
    
    def __init__(self, feature_name: str, git_wrapper=None):
        """
        Initialize mock feature manager.
        
        Args:
            feature_name: Name of the feature
            git_wrapper: Optional git wrapper instance
        """
        self.feature_name = feature_name
        self.git_wrapper = git_wrapper or Mock()
        self.config = {}
        self.call_log = []
        
    def interactive_menu(self):
        """Mock interactive menu method"""
        self.call_log.append('interactive_menu')
        return True
    
    def get_config(self) -> Dict[str, Any]:
        """Get mock configuration"""
        return self.config
    
    def set_config(self, config: Dict[str, Any]):
        """Set mock configuration"""
        self.config = config
    
    def log_call(self, method_name: str, *args, **kwargs):
        """Log method calls for testing"""
        self.call_log.append({
            'method': method_name,
            'args': args,
            'kwargs': kwargs,
            'timestamp': time.time()
        })


class GitCommandMocker:
    """Mock Git commands for testing"""
    
    def __init__(self):
        """Initialize Git command mocker"""
        self.command_responses = {}
        self.command_calls = []
        
    def mock_command(self, command: List[str], returncode: int = 0, 
                    stdout: str = '', stderr: str = '') -> 'GitCommandMocker':
        """
        Mock a specific git command.
        
        Args:
            command: Git command as list of strings
            returncode: Return code to simulate
            stdout: Standard output to return
            stderr: Standard error to return
            
        Returns:
            Self for method chaining
        """
        command_key = ' '.join(command)
        self.command_responses[command_key] = {
            'returncode': returncode,
            'stdout': stdout,
            'stderr': stderr
        }
        return self
    
    def mock_git_status(self, status_output: str) -> 'GitCommandMocker':
        """Mock git status command"""
        return self.mock_command(['git', 'status', '--porcelain'], stdout=status_output)
    
    def mock_git_branch_list(self, branches: List[str]) -> 'GitCommandMocker':
        """Mock git branch listing"""
        branch_output = '\n'.join(f'  {branch}' for branch in branches)
        return self.mock_command(['git', 'branch'], stdout=branch_output)
    
    def mock_git_stash_list(self, stashes: List[Dict[str, str]]) -> 'GitCommandMocker':
        """Mock git stash list"""
        stash_lines = []
        for i, stash in enumerate(stashes):
            line = f"stash@{{{i}}}: {stash.get('message', 'WIP on main')}"
            stash_lines.append(line)
        
        stash_output = '\n'.join(stash_lines)
        return self.mock_command(['git', 'stash', 'list'], stdout=stash_output)
    
    def mock_git_log(self, commits: List[Dict[str, str]]) -> 'GitCommandMocker':
        """Mock git log output"""
        log_lines = []
        for commit in commits:
            log_lines.append(f"commit {commit.get('hash', 'abc123')}")
            log_lines.append(f"Author: {commit.get('author', 'Test User <test@example.com>')}")
            log_lines.append(f"Date: {commit.get('date', 'Mon Jan 1 12:00:00 2024 +0000')}")
            log_lines.append("")
            log_lines.append(f"    {commit.get('message', 'Test commit')}")
            log_lines.append("")
        
        log_output = '\n'.join(log_lines)
        return self.mock_command(['git', 'log'], stdout=log_output)
    
    @contextmanager
    def patch_subprocess(self):
        """Context manager to patch subprocess.run with mocked responses"""
        original_run = subprocess.run
        
        def mock_run(*args, **kwargs):
            command = args[0] if args else []
            command_key = ' '.join(command) if isinstance(command, list) else str(command)
            
            # Log the command call
            self.command_calls.append({
                'command': command,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
            
            # Check if we have a mock response
            if command_key in self.command_responses:
                response = self.command_responses[command_key]
                mock_result = Mock()
                mock_result.returncode = response['returncode']
                mock_result.stdout = response['stdout']
                mock_result.stderr = response['stderr']
                return mock_result
            
            # Fall back to original implementation
            return original_run(*args, **kwargs)
        
        with patch('subprocess.run', side_effect=mock_run):
            yield self
    
    def get_command_calls(self) -> List[Dict[str, Any]]:
        """Get list of all command calls made during testing"""
        return self.command_calls
    
    def reset(self):
        """Reset all mocked commands and call logs"""
        self.command_responses.clear()
        self.command_calls.clear()


class TestEnvironmentManager:
    """Manage test environments and cleanup"""
    
    def __init__(self):
        """Initialize test environment manager"""
        self.temp_dirs = []
        self.mock_repos = []
        self.patches = []
        
    def create_temp_dir(self) -> str:
        """Create a temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def create_mock_repo(self, temp_dir: str = None) -> MockGitRepository:
        """Create a mock git repository"""
        if not temp_dir:
            temp_dir = self.create_temp_dir()
        
        mock_repo = MockGitRepository(temp_dir)
        self.mock_repos.append(mock_repo)
        return mock_repo
    
    def add_patch(self, patch_obj):
        """Add a patch object to be cleaned up"""
        self.patches.append(patch_obj)
        return patch_obj
    
    def cleanup_all(self):
        """Clean up all test resources"""
        # Stop all patches
        for patch_obj in self.patches:
            if hasattr(patch_obj, 'stop'):
                try:
                    patch_obj.stop()
                except Exception:
                    pass
        
        # Clean up mock repositories
        for mock_repo in self.mock_repos:
            try:
                mock_repo.cleanup()
            except Exception:
                pass
        
        # Clean up temporary directories
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
        
        # Reset lists
        self.temp_dirs.clear()
        self.mock_repos.clear()
        self.patches.clear()
    
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup_all()


# Utility functions for common test scenarios

def create_test_git_wrapper(temp_dir: str = None) -> 'InteractiveGitWrapper':
    """
    Create a git wrapper instance for testing.
    
    Args:
        temp_dir: Optional temporary directory
        
    Returns:
        Configured InteractiveGitWrapper instance
    """
    from git_wrapper import InteractiveGitWrapper
    
    if not temp_dir:
        temp_dir = tempfile.mkdtemp()
    
    wrapper = InteractiveGitWrapper()
    wrapper.config_file = Path(temp_dir) / 'test_config.json'
    
    # Mock print methods to reduce test output
    wrapper.print_info = Mock()
    wrapper.print_success = Mock()
    wrapper.print_error = Mock()
    wrapper.print_working = Mock()
    
    return wrapper


def assert_git_command_called(mock_subprocess, expected_command: List[str]):
    """
    Assert that a specific git command was called.
    
    Args:
        mock_subprocess: Mocked subprocess object
        expected_command: Expected command as list of strings
    """
    calls = mock_subprocess.call_args_list
    command_strings = []
    
    for call in calls:
        args, kwargs = call
        if args and isinstance(args[0], list):
            command_strings.append(' '.join(args[0]))
    
    expected_command_str = ' '.join(expected_command)
    assert any(expected_command_str in cmd for cmd in command_strings), \
        f"Expected command '{expected_command_str}' not found in calls: {command_strings}"


def measure_test_performance(func, *args, **kwargs) -> Tuple[Any, float]:
    """
    Measure the performance of a test function.
    
    Args:
        func: Function to measure
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Tuple of (result, execution_time_seconds)
    """
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    execution_time = end_time - start_time
    return result, execution_time


@contextmanager
def temporary_git_repo(initialize: bool = True, with_initial_commit: bool = True):
    """
    Context manager for creating temporary git repositories.
    
    Args:
        initialize: Whether to initialize the git repository
        with_initial_commit: Whether to create an initial commit
        
    Yields:
        MockGitRepository instance
    """
    with MockGitRepository() as repo:
        if initialize:
            repo.initialize(with_initial_commit=with_initial_commit)
        yield repo


# Test configuration helpers

def get_test_config() -> Dict[str, Any]:
    """Get a standard test configuration"""
    return {
        'name': 'Test User',
        'email': 'test@example.com',
        'default_branch': 'main',
        'auto_push': False,  # Disable for testing
        'show_emoji': False,  # Reduce output noise
        'debug_mode': True,  # Enable debug mode for testing
        'advanced_features': {
            'stash_management': {
                'auto_name_stashes': True,
                'max_stashes': 10,  # Lower limit for testing
                'confirm_deletions': False  # Skip confirmations in tests
            },
            'commit_templates': {
                'default_template': 'conventional',
                'auto_suggest': False,  # Disable for testing
                'validate_conventional': True
            },
            'branch_workflows': {
                'default_workflow': 'github_flow',
                'auto_track_remotes': False,  # Disable for testing
                'base_branch': 'main'
            },
            'conflict_resolution': {
                'preferred_editor': 'nano',  # Simple editor for testing
                'auto_stage_resolved': True
            },
            'health_dashboard': {
                'stale_branch_days': 7,  # Shorter period for testing
                'large_file_threshold_mb': 1,  # Lower threshold for testing
                'auto_refresh': False
            },
            'backup_system': {
                'backup_remotes': ['test-backup'],
                'auto_backup_branches': ['main'],
                'retention_days': 7  # Shorter retention for testing
            }
        }
    }


def create_test_config_file(temp_dir: str, config: Dict[str, Any] = None) -> Path:
    """
    Create a test configuration file.
    
    Args:
        temp_dir: Temporary directory path
        config: Optional configuration dictionary
        
    Returns:
        Path to the created config file
    """
    if config is None:
        config = get_test_config()
    
    config_file = Path(temp_dir) / 'test_config.json'
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    return config_file