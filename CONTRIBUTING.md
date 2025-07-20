# Contributing to Interactive Git Wrapper

Thank you for your interest in contributing to the Interactive Git Wrapper! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Adding New Features](#adding-new-features)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We aim to foster an inclusive and welcoming community.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/git-wrapper.git`
3. Set up the development environment
4. Create a new branch for your feature: `git checkout -b feature/your-feature-name`

## Development Environment

### Requirements

- Python 3.6 or higher
- Git

### Setup

1. Create a virtual environment: `python -m venv venv`
2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
3. Install development dependencies: `pip install -r requirements-dev.txt`

## Project Structure

```
git-wrapper/
├── features/                  # Feature modules
│   ├── __init__.py
│   ├── base_manager.py        # Base class for all features
│   ├── stash_manager.py       # Stash management feature
│   ├── commit_template_engine.py  # Commit templates feature
│   ├── branch_workflow_manager.py # Branch workflows feature
│   ├── conflict_resolver.py   # Conflict resolution feature
│   ├── repository_health_dashboard.py  # Repository health feature
│   ├── smart_backup_system.py # Smart backup feature
│   ├── help_system.py         # Help system feature
│   ├── error_handler.py       # Error handling utilities
│   └── debug_logger.py        # Debug logging utilities
├── git_wrapper.py             # Main wrapper class
├── run_all_tests.py           # Test runner
├── test_*.py                  # Test files
├── user_guide.md              # User documentation
├── git_guide.md               # Git reference guide
└── CONTRIBUTING.md            # This file
```

## Coding Standards

We follow PEP 8 style guidelines for Python code. Additionally:

1. Use type hints for function parameters and return values
2. Write comprehensive docstrings in Google style format
3. Keep functions focused on a single responsibility
4. Use meaningful variable and function names
5. Add comments for complex logic
6. Handle errors gracefully

### Docstring Format

```python
def function_name(param1: type, param2: type) -> return_type:
    """
    Brief description of the function.
    
    Detailed description of what the function does, when to use it,
    and any important considerations.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: When and why this exception is raised
        
    Example:
        ```python
        result = function_name("value", 42)
        ```
    """
```

## Adding New Features

To add a new feature to the Interactive Git Wrapper:

1. Create a new feature manager class that inherits from `BaseFeatureManager`
2. Implement the required abstract methods:
   - `_get_default_config()`
   - `interactive_menu()`
3. Add comprehensive docstrings
4. Add the feature to the feature definitions in `git_wrapper.py`
5. Write tests for the feature
6. Update documentation

### Feature Manager Template

```python
from typing import Dict, Any
from features.base_manager import BaseFeatureManager

class MyFeatureManager(BaseFeatureManager):
    """
    My Feature Manager - Brief description
    
    Detailed description of what this feature does and why it's useful.
    """
    
    def __init__(self, git_wrapper):
        """Initialize the MyFeatureManager."""
        super().__init__(git_wrapper)
        # Feature-specific initialization
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for this feature."""
        return {
            'setting_name': default_value,
            'another_setting': another_default_value
        }
        
    def interactive_menu(self) -> None:
        """Display the interactive menu for this feature."""
        self.show_feature_header("My Feature")
        
        # Menu implementation
        
    def show_context_help(self) -> None:
        """Show context-sensitive help for this feature."""
        self.clear_screen()
        print("❓ My Feature Help\n" + "=" * 30)
        # Help content
        
    # Feature-specific methods
```

## Testing

We use Python's built-in `unittest` framework for testing. All features should have comprehensive tests.

### Running Tests

- Run all tests: `python run_all_tests.py`
- Run specific test: `python test_feature_name.py`

### Writing Tests

1. Create a test file named `test_feature_name.py`
2. Use the `unittest` framework
3. Test both normal operation and error cases
4. Mock Git commands where appropriate

Example test:

```python
import unittest
from unittest.mock import patch, MagicMock
from features.my_feature import MyFeatureManager

class TestMyFeature(unittest.TestCase):
    def setUp(self):
        self.git_wrapper = MagicMock()
        self.feature = MyFeatureManager(self.git_wrapper)
        
    def test_some_functionality(self):
        # Test implementation
        result = self.feature.some_method()
        self.assertEqual(result, expected_value)
        
    @patch('subprocess.run')
    def test_git_command(self, mock_run):
        # Mock Git command execution
        mock_run.return_value.stdout = "mocked output"
        mock_run.return_value.returncode = 0
        
        result = self.feature.method_that_calls_git()
        self.assertEqual(result, expected_value)
```

## Documentation

Good documentation is essential. When contributing:

1. Update docstrings for any modified code
2. Update user_guide.md for user-facing changes
3. Update API documentation for developer-facing changes
4. Add examples where appropriate

## Pull Request Process

1. Ensure your code follows the coding standards
2. Run all tests to ensure they pass
3. Update documentation as needed
4. Submit a pull request with a clear description of the changes
5. Reference any related issues

Your pull request will be reviewed, and feedback may be provided. Once approved, it will be merged into the main branch.

Thank you for contributing to the Interactive Git Wrapper!