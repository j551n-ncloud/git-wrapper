# Testing Guide for Advanced Git Features

This document provides comprehensive information about testing the advanced Git features in the Interactive Git Wrapper.

## Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Test Categories](#test-categories)
5. [Test Utilities](#test-utilities)
6. [Writing New Tests](#writing-new-tests)
7. [Continuous Integration](#continuous-integration)
8. [Troubleshooting](#troubleshooting)

## Overview

The testing framework for advanced Git features includes:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test feature interactions and cross-feature functionality
- **End-to-End Tests**: Test complete user workflows
- **Performance Tests**: Test performance with large repositories and datasets
- **Git Command Integration Tests**: Test actual Git command interactions

## Test Structure

```
├── test_*.py                           # Individual test modules
├── test_utilities.py                   # Test utilities and helpers
├── run_all_tests.py                   # Comprehensive test runner
├── TESTING.md                         # This documentation
└── test_data/                         # Test data files (if needed)
```

### Test Modules

| Module | Purpose |
|--------|---------|
| `test_base_setup.py` | Basic setup and import tests |
| `test_feature_initialization.py` | Feature initialization and dependency management |
| `test_menu_integration.py` | Menu integration and navigation |
| `test_stash_manager.py` | Stash management functionality |
| `test_commit_template_engine.py` | Commit template functionality |
| `test_branch_workflow_manager.py` | Branch workflow automation |
| `test_conflict_resolver.py` | Conflict resolution functionality |
| `test_repository_health_dashboard.py` | Repository health analysis |
| `test_smart_backup_system.py` | Backup system functionality |
| `test_integration_feature_interactions.py` | Cross-feature integration tests |
| `test_end_to_end_workflows.py` | Complete user workflow tests |
| `test_git_command_integration.py` | Git command integration tests |
| `test_performance_large_repositories.py` | Performance tests |

## Running Tests

### Prerequisites

1. **Git**: Ensure Git is installed and accessible from command line
2. **Python 3.7+**: Required for running tests
3. **Repository**: Tests should be run from the project root directory

### Quick Start

```bash
# Run all tests
python run_all_tests.py

# Run with verbose output
python run_all_tests.py --verbose

# Run specific test modules
python run_all_tests.py --modules test_stash_manager test_commit_template_engine

# Skip performance tests (faster execution)
python run_all_tests.py --no-performance

# Skip integration tests
python run_all_tests.py --no-integration

# List available test modules
python run_all_tests.py --list-modules
```

### Individual Test Execution

```bash
# Run a single test module
python -m unittest test_stash_manager

# Run a specific test class
python -m unittest test_stash_manager.TestStashManager

# Run a specific test method
python -m unittest test_stash_manager.TestStashManager.test_create_named_stash
```

### Test Runner Options

| Option | Description |
|--------|-------------|
| `--verbose` | Show detailed test output |
| `--no-performance` | Skip performance tests |
| `--no-integration` | Skip integration tests |
| `--modules MODULE [MODULE ...]` | Run only specified modules |
| `--skip-checks` | Skip pre-test environment checks |
| `--list-modules` | List available test modules |

## Test Categories

### Unit Tests

Test individual components in isolation using mocks and stubs.

**Characteristics:**
- Fast execution (< 1 second per test)
- No external dependencies
- Use mocks for Git commands and file operations
- Focus on single functionality

**Example:**
```python
def test_create_named_stash(self):
    """Test creating a named stash"""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(returncode=0)
        result = self.stash_manager.create_named_stash('test-stash', 'Test message')
        self.assertTrue(result)
```

### Integration Tests

Test interactions between different features and components.

**Characteristics:**
- Medium execution time (1-10 seconds per test)
- Test feature interactions
- Use temporary Git repositories
- Verify data sharing between features

**Example:**
```python
def test_stash_and_branch_workflow_integration(self):
    """Test integration between stash management and branch workflows"""
    # Create stash, switch branch, apply stash
    # Verify cross-feature functionality
```

### End-to-End Tests

Test complete user workflows from start to finish.

**Characteristics:**
- Longer execution time (10-30 seconds per test)
- Test complete user scenarios
- Use real Git repositories
- Simulate user interactions

**Example:**
```python
def test_complete_feature_development_workflow(self):
    """Test complete feature development from start to finish"""
    # 1. Check repository health
    # 2. Stash work in progress
    # 3. Start feature branch
    # 4. Apply stashed work
    # 5. Complete feature
    # 6. Commit with template
    # 7. Finish feature branch
```

### Performance Tests

Test performance with large repositories and datasets.

**Characteristics:**
- Long execution time (30+ seconds per test)
- Test with large amounts of data
- Measure execution time and memory usage
- Verify scalability

**Example:**
```python
def test_health_dashboard_performance_large_repo(self):
    """Test health dashboard performance with large repository"""
    self._create_large_repository(num_branches=20, num_commits_per_branch=10)
    result, execution_time = self._measure_execution_time(
        health_dashboard.analyze_branches
    )
    self.assertLess(execution_time, self.MEDIUM_OPERATION_THRESHOLD)
```

## Test Utilities

The `test_utilities.py` module provides helpful utilities for testing:

### MockGitRepository

Create temporary Git repositories for testing:

```python
from test_utilities import MockGitRepository

with MockGitRepository() as repo:
    repo.initialize()
    repo.create_file('test.py', 'print("hello")')
    repo.add_and_commit(['test.py'], 'Add test file')
    repo.create_branch('feature-branch')
```

### TestDataGenerator

Generate test data for various scenarios:

```python
from test_utilities import TestDataGenerator

# Generate Python file content
content = TestDataGenerator.generate_python_file_content(
    function_name='test_func',
    class_name='TestClass'
)

# Generate commit messages
messages = TestDataGenerator.generate_commit_messages(10, 'conventional')

# Create complex repository structure
metadata = TestDataGenerator.create_complex_repository(
    repo, num_branches=5, commits_per_branch=3
)
```

### GitCommandMocker

Mock Git commands for unit testing:

```python
from test_utilities import GitCommandMocker

mocker = GitCommandMocker()
mocker.mock_git_status('M  modified_file.py')
mocker.mock_git_branch_list(['main', 'feature-branch'])

with mocker.patch_subprocess():
    # Run code that calls git commands
    # Mocked responses will be returned
```

### TestEnvironmentManager

Manage test environments and cleanup:

```python
from test_utilities import TestEnvironmentManager

with TestEnvironmentManager() as env:
    temp_dir = env.create_temp_dir()
    mock_repo = env.create_mock_repo(temp_dir)
    # Environment automatically cleaned up on exit
```

## Writing New Tests

### Test Class Structure

```python
import unittest
from unittest.mock import Mock, patch
from test_utilities import MockGitRepository, create_test_git_wrapper

class TestNewFeature(unittest.TestCase):
    """Test new feature functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.git_wrapper = create_test_git_wrapper()
        self.feature_manager = self.git_wrapper.get_feature_manager('new_feature')
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Cleanup code here
        pass
    
    def test_basic_functionality(self):
        """Test basic functionality"""
        # Test implementation
        pass
    
    def test_error_handling(self):
        """Test error handling"""
        # Test error scenarios
        pass
```

### Best Practices

1. **Use Descriptive Names**: Test method names should clearly describe what is being tested
2. **Test One Thing**: Each test should focus on a single aspect of functionality
3. **Use Mocks Appropriately**: Mock external dependencies but not the code under test
4. **Clean Up Resources**: Always clean up temporary files and directories
5. **Test Error Cases**: Include tests for error conditions and edge cases
6. **Use Assertions Effectively**: Use specific assertions that provide clear failure messages

### Test Categories Guidelines

| Test Type | When to Use | Execution Time | Dependencies |
|-----------|-------------|----------------|--------------|
| Unit | Testing individual methods/functions | < 1s | None (mocked) |
| Integration | Testing feature interactions | 1-10s | Temporary repos |
| End-to-End | Testing complete workflows | 10-30s | Real Git repos |
| Performance | Testing scalability | 30s+ | Large datasets |

### Mocking Guidelines

```python
# Mock external commands
with patch('subprocess.run') as mock_run:
    mock_run.return_value = Mock(returncode=0, stdout='success')
    # Test code here

# Mock user input
with patch('builtins.input', side_effect=['user', 'input', 'values']):
    # Test interactive functionality

# Mock file operations
with patch('pathlib.Path.exists', return_value=True):
    # Test file-dependent code
```

## Continuous Integration

### GitHub Actions Configuration

```yaml
name: Test Advanced Git Features

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.7, 3.8, 3.9, '3.10']
    
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        # Install any required dependencies
    
    - name: Run tests
      run: |
        python run_all_tests.py --no-performance
```

### Test Coverage

To measure test coverage:

```bash
# Install coverage tool
pip install coverage

# Run tests with coverage
coverage run run_all_tests.py

# Generate coverage report
coverage report -m

# Generate HTML coverage report
coverage html
```

## Troubleshooting

### Common Issues

#### Git Not Available
```
Error: Git not available or not working properly
```
**Solution**: Ensure Git is installed and accessible from command line.

#### Import Errors
```
ImportError: No module named 'git_wrapper'
```
**Solution**: Run tests from the project root directory.

#### Permission Errors
```
PermissionError: [Errno 13] Permission denied
```
**Solution**: Ensure you have write permissions in the test directory.

#### Timeout Errors
```
subprocess.TimeoutExpired: Command timed out
```
**Solution**: Check if Git operations are hanging. May need to configure Git credentials.

### Debug Mode

Enable debug mode for more detailed output:

```python
# In test setup
self.git_wrapper.config['debug_mode'] = True
```

### Logging

Enable logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Isolation

Ensure tests are properly isolated:

```python
def setUp(self):
    """Set up test fixtures"""
    # Create fresh environment for each test
    self.temp_dir = tempfile.mkdtemp()
    os.chdir(self.temp_dir)

def tearDown(self):
    """Clean up test fixtures"""
    # Always clean up
    os.chdir(self.original_cwd)
    shutil.rmtree(self.temp_dir, ignore_errors=True)
```

## Performance Benchmarks

### Expected Performance Thresholds

| Operation Type | Threshold | Description |
|----------------|-----------|-------------|
| Fast Operations | < 1s | Unit tests, simple operations |
| Medium Operations | < 5s | Integration tests, moderate complexity |
| Slow Operations | < 15s | End-to-end tests, complex workflows |
| Performance Tests | < 60s | Large repository operations |

### Memory Usage Guidelines

- Unit tests: < 50MB memory increase
- Integration tests: < 100MB memory increase
- Performance tests: < 500MB memory increase

## Contributing

When contributing new tests:

1. **Follow Naming Conventions**: Use descriptive test names
2. **Add Documentation**: Document complex test scenarios
3. **Update This Guide**: Update documentation for new test categories
4. **Run Full Test Suite**: Ensure all tests pass before submitting
5. **Consider Performance**: Add performance tests for new features

### Test Review Checklist

- [ ] Tests have descriptive names
- [ ] Tests are properly isolated
- [ ] Mocks are used appropriately
- [ ] Error cases are tested
- [ ] Resources are cleaned up
- [ ] Tests run in reasonable time
- [ ] Documentation is updated

## Resources

- [Python unittest documentation](https://docs.python.org/3/library/unittest.html)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Git documentation](https://git-scm.com/doc)
- [Testing best practices](https://docs.python-guide.org/writing/tests/)