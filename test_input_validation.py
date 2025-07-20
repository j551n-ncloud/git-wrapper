#!/usr/bin/env python3
"""
Test Input Validation - Tests for the input validation functionality

This module contains tests for the input validation and sanitization functions
to ensure they properly validate and sanitize user inputs.
"""

import unittest
import os
import sys
from pathlib import Path
from features.input_validator import InputValidator, InputValidationError


class TestInputValidation(unittest.TestCase):
    """Test cases for input validation functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.validator = InputValidator()
    
    def test_branch_name_validation(self):
        """Test branch name validation."""
        # Valid branch names
        self.assertTrue(self.validator.validate_branch_name("main"))
        self.assertTrue(self.validator.validate_branch_name("feature/new-feature"))
        self.assertTrue(self.validator.validate_branch_name("release-1.0"))
        self.assertTrue(self.validator.validate_branch_name("hotfix_123"))
        self.assertTrue(self.validator.validate_branch_name("user/john/feature"))
        
        # Invalid branch names
        self.assertFalse(self.validator.validate_branch_name(""))
        self.assertFalse(self.validator.validate_branch_name(" spaces "))
        self.assertFalse(self.validator.validate_branch_name("branch~name"))
        self.assertFalse(self.validator.validate_branch_name("branch^name"))
        self.assertFalse(self.validator.validate_branch_name("branch:name"))
        self.assertFalse(self.validator.validate_branch_name("branch?name"))
        self.assertFalse(self.validator.validate_branch_name("branch*name"))
        self.assertFalse(self.validator.validate_branch_name("branch[name"))
        self.assertFalse(self.validator.validate_branch_name("branch\\name"))
        self.assertFalse(self.validator.validate_branch_name("branch..name"))
        self.assertFalse(self.validator.validate_branch_name("branch@{name"))
        self.assertFalse(self.validator.validate_branch_name("branch//name"))
        self.assertFalse(self.validator.validate_branch_name("branch/.name"))
        self.assertFalse(self.validator.validate_branch_name(".branch"))
        self.assertFalse(self.validator.validate_branch_name("/branch"))
        self.assertFalse(self.validator.validate_branch_name("branch."))
        self.assertFalse(self.validator.validate_branch_name("branch/"))
        self.assertFalse(self.validator.validate_branch_name("HEAD"))
    
    def test_remote_name_validation(self):
        """Test remote name validation."""
        # Valid remote names
        self.assertTrue(self.validator.validate_remote_name("origin"))
        self.assertTrue(self.validator.validate_remote_name("upstream"))
        self.assertTrue(self.validator.validate_remote_name("remote_123"))
        self.assertTrue(self.validator.validate_remote_name("remote-123"))
        
        # Invalid remote names
        self.assertFalse(self.validator.validate_remote_name(""))
        self.assertFalse(self.validator.validate_remote_name(" spaces "))
        self.assertFalse(self.validator.validate_remote_name("remote/name"))
        self.assertFalse(self.validator.validate_remote_name("remote.name"))
        self.assertFalse(self.validator.validate_remote_name("remote:name"))
        self.assertFalse(self.validator.validate_remote_name("remote@name"))
    
    def test_file_path_validation(self):
        """Test file path validation."""
        # Valid file paths
        self.assertTrue(self.validator.validate_file_path("file.txt"))
        self.assertTrue(self.validator.validate_file_path("dir/file.txt"))
        self.assertTrue(self.validator.validate_file_path("dir/subdir/file.txt"))
        
        # Invalid file paths
        self.assertFalse(self.validator.validate_file_path(""))
        self.assertFalse(self.validator.validate_file_path("file?.txt"))
        self.assertFalse(self.validator.validate_file_path("file*.txt"))
        self.assertFalse(self.validator.validate_file_path("file<.txt"))
        self.assertFalse(self.validator.validate_file_path("file>.txt"))
        self.assertFalse(self.validator.validate_file_path("file:.txt"))
        self.assertFalse(self.validator.validate_file_path("file\".txt"))
        self.assertFalse(self.validator.validate_file_path("file|.txt"))
        
        # Path traversal attempts
        self.assertFalse(self.validator.validate_file_path("../file.txt", allow_outside_repo=False))
        self.assertFalse(self.validator.validate_file_path("dir/../../file.txt", allow_outside_repo=False))
        self.assertTrue(self.validator.validate_file_path("../file.txt", allow_outside_repo=True))
    
    def test_url_validation(self):
        """Test URL validation."""
        # Valid URLs
        self.assertTrue(self.validator.validate_url("https://github.com/user/repo.git"))
        self.assertTrue(self.validator.validate_url("http://github.com/user/repo.git"))
        self.assertTrue(self.validator.validate_url("git@github.com:user/repo.git"))
        self.assertTrue(self.validator.validate_url("ssh://git@github.com/user/repo.git"))
        self.assertTrue(self.validator.validate_url("file:///path/to/repo.git"))
        
        # Invalid URLs
        self.assertFalse(self.validator.validate_url(""))
        self.assertFalse(self.validator.validate_url("not a url"))
        self.assertFalse(self.validator.validate_url("github.com/user/repo.git"))
        self.assertFalse(self.validator.validate_url("https:/github.com/user/repo.git"))
    
    def test_email_validation(self):
        """Test email validation."""
        # Valid emails
        self.assertTrue(self.validator.validate_email("user@example.com"))
        self.assertTrue(self.validator.validate_email("user.name@example.com"))
        self.assertTrue(self.validator.validate_email("user+tag@example.com"))
        self.assertTrue(self.validator.validate_email("user123@example.co.uk"))
        
        # Invalid emails
        self.assertFalse(self.validator.validate_email(""))
        self.assertFalse(self.validator.validate_email("not an email"))
        self.assertFalse(self.validator.validate_email("user@"))
        self.assertFalse(self.validator.validate_email("@example.com"))
        self.assertFalse(self.validator.validate_email("user@example"))
    
    def test_commit_hash_validation(self):
        """Test commit hash validation."""
        # Valid commit hashes
        self.assertTrue(self.validator.validate_commit_hash("1234567"))
        self.assertTrue(self.validator.validate_commit_hash("abcdef0123456789"))
        self.assertTrue(self.validator.validate_commit_hash("abcdef0123456789abcdef0123456789abcdef01"))
        
        # Invalid commit hashes
        self.assertFalse(self.validator.validate_commit_hash(""))
        self.assertFalse(self.validator.validate_commit_hash("123456"))  # Too short
        self.assertFalse(self.validator.validate_commit_hash("abcdefg"))  # Contains non-hex character
        self.assertFalse(self.validator.validate_commit_hash("abcdef 123456"))  # Contains space
    
    def test_sanitize_shell_input(self):
        """Test shell input sanitization."""
        # Test basic sanitization - simple strings don't need quotes
        self.assertEqual(self.validator.sanitize_shell_input("simple"), "simple")
        
        # Test sanitization of special characters
        self.assertNotEqual(self.validator.sanitize_shell_input("command; rm -rf /"), "command; rm -rf /")
        self.assertNotEqual(self.validator.sanitize_shell_input("$(rm -rf /)"), "$(rm -rf /)")
        self.assertNotEqual(self.validator.sanitize_shell_input("`rm -rf /`"), "`rm -rf /`")
        
        # Ensure quotes are properly escaped
        self.assertNotEqual(self.validator.sanitize_shell_input("'quote'"), "'quote'")
        self.assertNotEqual(self.validator.sanitize_shell_input('"double"'), '"double"')
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        # Test basic sanitization
        self.assertEqual(self.validator.sanitize_filename("file.txt"), "file.txt")
        
        # Test sanitization of invalid characters
        self.assertEqual(self.validator.sanitize_filename("file?.txt"), "file_.txt")
        self.assertEqual(self.validator.sanitize_filename("file*.txt"), "file_.txt")
        self.assertEqual(self.validator.sanitize_filename("file<.txt"), "file_.txt")
        self.assertEqual(self.validator.sanitize_filename("file>.txt"), "file_.txt")
        self.assertEqual(self.validator.sanitize_filename("file:.txt"), "file_.txt")
        self.assertEqual(self.validator.sanitize_filename("file\".txt"), "file_.txt")
        self.assertEqual(self.validator.sanitize_filename("file|.txt"), "file_.txt")
        
        # Test control characters
        self.assertEqual(self.validator.sanitize_filename("file\x00.txt"), "file.txt")
        self.assertEqual(self.validator.sanitize_filename("file\x1F.txt"), "file.txt")
        
        # Test length limitation
        long_name = "a" * 300
        self.assertEqual(len(self.validator.sanitize_filename(long_name)), 255)
    
    def test_sanitize_path(self):
        """Test path sanitization."""
        # Test basic sanitization
        self.assertEqual(self.validator.sanitize_path("dir/file.txt"), "dir/file.txt")
        
        # Test path normalization
        self.assertEqual(self.validator.sanitize_path("dir/../file.txt"), "file.txt")
        self.assertEqual(self.validator.sanitize_path("dir/./file.txt"), "dir/file.txt")
        
        # Test path traversal prevention
        self.assertEqual(self.validator.sanitize_path("../file.txt", allow_outside_repo=False), "file.txt")
        self.assertEqual(self.validator.sanitize_path("dir/../../file.txt", allow_outside_repo=False), "file.txt")
        
        # Test with allow_outside_repo=True
        if os.name == 'posix':  # Unix-like systems
            self.assertEqual(self.validator.sanitize_path("../file.txt", allow_outside_repo=True), "../file.txt")
        else:  # Windows
            # Windows path normalization may behave differently
            pass
    
    def test_validate_input(self):
        """Test comprehensive input validation."""
        # Test required validation
        self.assertFalse(self.validator.validate_input("", {"required": True}, "field"))
        self.assertTrue(self.validator.validate_input("value", {"required": True}, "field"))
        
        # Test type validation
        self.assertTrue(self.validator.validate_input("string", {"type": str}, "field"))
        self.assertFalse(self.validator.validate_input(123, {"type": str}, "field"))
        
        # Test length validation
        self.assertTrue(self.validator.validate_input("abc", {"min_length": 3}, "field"))
        self.assertFalse(self.validator.validate_input("ab", {"min_length": 3}, "field"))
        self.assertTrue(self.validator.validate_input("abc", {"max_length": 3}, "field"))
        self.assertFalse(self.validator.validate_input("abcd", {"max_length": 3}, "field"))
        
        # Test pattern validation
        self.assertTrue(self.validator.validate_input("abc123", {"pattern": r"^[a-z0-9]+$"}, "field"))
        self.assertFalse(self.validator.validate_input("ABC", {"pattern": r"^[a-z0-9]+$"}, "field"))
        
        # Test enum validation
        self.assertTrue(self.validator.validate_input("apple", {"enum": ["apple", "banana", "cherry"]}, "field"))
        self.assertFalse(self.validator.validate_input("orange", {"enum": ["apple", "banana", "cherry"]}, "field"))
        
        # Test range validation
        self.assertTrue(self.validator.validate_input(5, {"min_value": 1, "max_value": 10}, "field"))
        self.assertFalse(self.validator.validate_input(0, {"min_value": 1}, "field"))
        self.assertFalse(self.validator.validate_input(11, {"max_value": 10}, "field"))
        
        # Test custom validator
        self.assertTrue(self.validator.validate_input("even", {"validator": lambda x: len(x) % 2 == 0}, "field"))
        self.assertFalse(self.validator.validate_input("odd", {"validator": lambda x: len(x) % 2 == 0}, "field"))
        
        # Test specific validators
        self.assertTrue(self.validator.validate_input("main", {"validator_type": "branch_name"}, "field"))
        self.assertFalse(self.validator.validate_input("main*", {"validator_type": "branch_name"}, "field"))


if __name__ == "__main__":
    unittest.main()