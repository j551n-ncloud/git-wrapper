#!/usr/bin/env python3
"""
Test Cross-Platform Compatibility - Test cross-platform features

This test module verifies that the cross-platform compatibility improvements
work correctly across different operating systems and handle Unicode properly.
"""

import unittest
import tempfile
import shutil
import os
import platform
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from git_wrapper import InteractiveGitWrapper


class TestCrossPlatformCompatibility(unittest.TestCase):
    """Test cross-platform compatibility features."""
    
    def setUp(self):
        """Set up test environment before each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create a mock git repository
        os.makedirs('.git', exist_ok=True)
        
        # Initialize git wrapper with mocked config file
        with patch.object(Path, 'home', return_value=Path(self.temp_dir)):
            self.wrapper = InteractiveGitWrapper()
            self.wrapper.config_file = Path(self.temp_dir) / 'test_config.json'
        
        # Mock print methods to avoid output during tests
        self.wrapper.print_success = Mock()
        self.wrapper.print_error = Mock()
        self.wrapper.print_info = Mock()
        self.wrapper.print_working = Mock()
    
    def tearDown(self):
        """Clean up after each test."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_platform_detection(self):
        """Test platform detection functionality."""
        platform_info = self.wrapper.platform_info
        
        # Check that basic platform info is detected
        self.assertIn('system', platform_info)
        self.assertIn('is_windows', platform_info)
        self.assertIn('is_macos', platform_info)
        self.assertIn('is_linux', platform_info)
        self.assertIn('is_unix', platform_info)
        
        # Check encoding information
        self.assertIn('filesystem_encoding', platform_info)
        self.assertIn('console_encoding', platform_info)
        
        # Check Unicode support detection
        self.assertIn('unicode_support', platform_info)
        unicode_support = platform_info['unicode_support']
        self.assertIn('filesystem_unicode', unicode_support)
        self.assertIn('console_unicode', unicode_support)
        self.assertIn('environment_unicode', unicode_support)
    
    def test_git_executable_detection(self):
        """Test Git executable detection."""
        git_executable = self.wrapper.platform_info.get('git_executable')
        
        if git_executable:
            # If Git is found, it should be a valid path
            self.assertTrue(os.path.isfile(git_executable))
            self.assertTrue(os.access(git_executable, os.X_OK))
    
    def test_config_file_path_generation(self):
        """Test platform-appropriate config file path generation."""
        config_path = self.wrapper._get_config_file_path()
        
        # Should be a Path object
        self.assertIsInstance(config_path, Path)
        
        # Should be an absolute path
        self.assertTrue(config_path.is_absolute())
        
        # Should end with config.json
        self.assertEqual(config_path.name, 'config.json')
        
        # Should be in appropriate directory for platform
        if platform.system().lower() == 'windows':
            # Should be in AppData or similar
            path_str = str(config_path).lower()
            self.assertTrue(any(x in path_str for x in ['appdata', 'gitwrapper']))
        elif platform.system().lower() == 'darwin':
            # Should be in Library/Application Support
            self.assertIn('Library/Application Support', str(config_path))
        else:
            # Should be in .config
            self.assertIn('.config', str(config_path))
    
    def test_path_normalization(self):
        """Test path normalization for cross-platform compatibility."""
        test_paths = [
            'simple/path',
            './relative/path',
            '../parent/path',
            '~/home/path',
        ]
        
        for test_path in test_paths:
            normalized = self.wrapper.normalize_path(test_path)
            
            # Should be a Path object
            self.assertIsInstance(normalized, Path)
            
            # Should be absolute (after normalization)
            if not test_path.startswith('..'):
                self.assertTrue(normalized.is_absolute())
    
    def test_safe_path_join(self):
        """Test safe path joining with various inputs."""
        test_cases = [
            (['dir1', 'dir2', 'file.txt'], 'dir1/dir2/file.txt'),
            (['dir1', '', 'file.txt'], 'dir1/file.txt'),
            (['dir1', None, 'file.txt'], 'dir1/file.txt'),
            ([], '.'),
        ]
        
        for parts, expected_end in test_cases:
            result = self.wrapper.safe_path_join(*parts)
            
            # Should be a Path object
            self.assertIsInstance(result, Path)
            
            # Should end with expected pattern (accounting for platform differences)
            if expected_end != '.':
                expected_parts = expected_end.split('/')
                result_parts = result.parts
                self.assertTrue(all(part in result_parts for part in expected_parts if part))
    
    def test_unicode_text_encoding(self):
        """Test Unicode text encoding for Git operations."""
        test_strings = [
            'simple ascii text',
            'café résumé naïve',  # Basic Unicode
            '🚀 ✅ 🔄',          # Emoji
            '测试 テスト 한국어',    # CJK characters
            'mixed: café 🚀 测试'  # Mixed Unicode
        ]
        
        for test_string in test_strings:
            # Test safe encoding
            encoded = self.wrapper.safe_encode_for_git(test_string)
            self.assertIsInstance(encoded, str)
            
            # Should be able to encode with system encoding
            try:
                encoded.encode(self.wrapper.system_encoding)
            except UnicodeEncodeError:
                self.fail(f"Failed to encode string: {test_string}")
    
    def test_git_output_decoding(self):
        """Test Git output decoding with various encodings."""
        test_cases = [
            b'simple ascii output',
            'already a string',
            'café résumé'.encode('utf-8'),
            'café résumé'.encode('latin-1'),
        ]
        
        for test_input in test_cases:
            decoded = self.wrapper.safe_decode_git_output(test_input)
            
            # Should always return a string
            self.assertIsInstance(decoded, str)
            
            # Should not be empty (unless input was empty)
            if test_input:
                self.assertTrue(decoded)
    
    def test_platform_specific_config(self):
        """Test platform-specific configuration generation."""
        config = self.wrapper.get_platform_specific_config()
        
        # Should contain basic cross-platform settings
        required_keys = [
            'line_endings', 'case_sensitive', 'max_path_length',
            'shell_command', 'git_executable', 'supports_color',
            'path_separator', 'encoding', 'console_encoding'
        ]
        
        for key in required_keys:
            self.assertIn(key, config, f"Missing required config key: {key}")
        
        # Check platform-specific values
        if platform.system().lower() == 'windows':
            self.assertEqual(config['line_endings'], 'crlf')
            self.assertEqual(config['path_separator'], '\\')
            self.assertFalse(config['case_sensitive'])
        else:
            self.assertEqual(config['line_endings'], 'lf')
            self.assertEqual(config['path_separator'], '/')
            self.assertTrue(config['case_sensitive'])
    
    def test_temp_file_creation(self):
        """Test cross-platform temporary file creation."""
        temp_file = self.wrapper.create_cross_platform_temp_file(
            suffix='.txt',
            prefix='test_'
        )
        
        try:
            # Should be a Path object
            self.assertIsInstance(temp_file, Path)
            
            # Should be an absolute path
            self.assertTrue(temp_file.is_absolute())
            
            # Should have correct suffix and prefix
            self.assertTrue(temp_file.name.startswith('test_'))
            self.assertTrue(temp_file.name.endswith('.txt'))
            
            # File should exist (created by mkstemp)
            self.assertTrue(temp_file.exists())
            
        finally:
            # Clean up
            if temp_file.exists():
                temp_file.unlink()
    
    def test_unicode_path_handling(self):
        """Test handling of paths with Unicode characters."""
        if not self.wrapper.platform_info.get('unicode_support', {}).get('console_unicode', True):
            self.skipTest("System doesn't support Unicode")
        
        unicode_paths = [
            'café/résumé.txt',
            '测试/文件.txt',
            'emoji_🚀_file.txt'
        ]
        
        for unicode_path in unicode_paths:
            try:
                # Test path normalization
                normalized = self.wrapper.normalize_path(unicode_path)
                self.assertIsInstance(normalized, Path)
                
                # Test path formatting for display
                formatted = self.wrapper.format_path_for_display(normalized)
                self.assertIsInstance(formatted, str)
                
            except Exception as e:
                # If Unicode handling fails, it should fail gracefully
                self.assertIsInstance(e, (UnicodeError, OSError))
    
    @patch('subprocess.run')
    def test_git_config_unicode_handling(self, mock_run):
        """Test Git configuration with Unicode values."""
        # Mock successful git config command
        mock_run.return_value = Mock(returncode=0, stdout='café résumé', stderr='')
        
        # Test getting config value
        with patch.object(self.wrapper, 'run_git_command', return_value='café résumé'):
            value = self.wrapper.get_safe_git_config_value('user.name')
            self.assertEqual(value, 'café résumé')
        
        # Test setting config value
        with patch.object(self.wrapper, 'run_git_command', return_value=True):
            success = self.wrapper.set_safe_git_config_value('user.name', 'café résumé')
            self.assertTrue(success)
    
    def test_encoding_fallback_handling(self):
        """Test encoding fallback mechanisms."""
        # Test with problematic byte sequences
        problematic_bytes = [
            b'\xff\xfe',  # BOM that might cause issues
            b'\x80\x81\x82',  # Invalid UTF-8 sequence
            b'caf\xe9',  # Latin-1 encoded 'café'
        ]
        
        for test_bytes in problematic_bytes:
            decoded = self.wrapper.safe_decode_git_output(test_bytes)
            
            # Should always return a string without raising exceptions
            self.assertIsInstance(decoded, str)
            
            # Should not be empty
            self.assertTrue(decoded)
    
    def test_long_path_support_detection(self):
        """Test long path support detection on Windows."""
        if platform.system().lower() != 'windows':
            self.skipTest("Long path test only relevant on Windows")
        
        supports_long_paths = self.wrapper.platform_info.get('supports_long_paths', False)
        
        # Should be a boolean
        self.assertIsInstance(supports_long_paths, bool)
        
        # Test path normalization with long paths
        long_path = 'very_long_directory_name_' * 20 + '/file.txt'
        normalized = self.wrapper.normalize_path(long_path)
        
        # Should handle long paths gracefully
        self.assertIsInstance(normalized, Path)


class TestPlatformSpecificFeatures(unittest.TestCase):
    """Test platform-specific features."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        with patch.object(Path, 'home', return_value=Path(self.temp_dir)):
            self.wrapper = InteractiveGitWrapper()
            self.wrapper.config_file = Path(self.temp_dir) / 'test_config.json'
    
    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_windows_specific_features(self):
        """Test Windows-specific features."""
        if platform.system().lower() != 'windows':
            self.skipTest("Windows-specific test")
        
        config = self.wrapper.get_platform_specific_config()
        
        # Check Windows-specific configuration
        self.assertIn('wsl_available', config)
        self.assertIn('git_bash_available', config)
        self.assertIn('powershell_available', config)
        
        # Check executable extensions
        self.assertIn('executable_extensions', config)
        self.assertIn('.exe', config['executable_extensions'])
    
    def test_macos_specific_features(self):
        """Test macOS-specific features."""
        if platform.system().lower() != 'darwin':
            self.skipTest("macOS-specific test")
        
        config = self.wrapper.get_platform_specific_config()
        
        # Check macOS-specific configuration
        self.assertIn('homebrew_available', config)
        self.assertIn('xcode_available', config)
        self.assertIn('terminal_app', config)
        
        # Check package manager detection
        self.assertIn('package_manager', config)
    
    def test_linux_specific_features(self):
        """Test Linux-specific features."""
        if platform.system().lower() != 'linux':
            self.skipTest("Linux-specific test")
        
        config = self.wrapper.get_platform_specific_config()
        
        # Check Linux-specific configuration
        self.assertIn('distribution', config)
        self.assertIn('package_manager', config)
        
        # Should support color
        self.assertTrue(config['supports_color'])


if __name__ == '__main__':
    unittest.main()