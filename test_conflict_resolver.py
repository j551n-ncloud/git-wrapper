#!/usr/bin/env python3
"""
Unit Tests for ConflictResolver

Tests for conflict detection, listing, preview, resolution strategies,
editor integration, and merge finalization functionality.
"""

import unittest
import tempfile
import shutil
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import subprocess

# Import the classes to test
from features.conflict_resolver import ConflictResolver


class TestConflictResolver(unittest.TestCase):
    """Test cases for ConflictResolver functionality."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create mock git wrapper
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {
            'show_emoji': True,
            'advanced_features': {
                'conflictresolver': {
                    'preferred_editor': 'code',
                    'auto_stage_resolved': True,
                    'show_line_numbers': True,
                    'highlight_conflicts': True,
                    'backup_before_resolve': True
                }
            }
        }
        
        # Mock the UI methods
        self.mock_git_wrapper.print_success = Mock()
        self.mock_git_wrapper.print_error = Mock()
        self.mock_git_wrapper.print_info = Mock()
        self.mock_git_wrapper.print_working = Mock()
        self.mock_git_wrapper.get_input = Mock()
        self.mock_git_wrapper.get_choice = Mock()
        self.mock_git_wrapper.confirm = Mock()
        self.mock_git_wrapper.clear_screen = Mock()
        self.mock_git_wrapper.save_config = Mock()
        
        # Create ConflictResolver instance
        self.resolver = ConflictResolver(self.mock_git_wrapper)
        
        # Create .git directory structure
        os.makedirs('.git', exist_ok=True)
    
    def tearDown(self):
        """Clean up after each test."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def create_conflicted_file(self, filename: str, content: str = None) -> str:
        """
        Create a file with conflict markers for testing.
        
        Args:
            filename: Name of the file to create
            content: Custom content, or None for default conflict content
            
        Returns:
            Path to the created file
        """
        if content is None:
            content = """line 1
line 2
<<<<<<< HEAD
our change
our second line
=======
their change
their second line
>>>>>>> branch-name
line 5
line 6"""
        
        file_path = Path(filename)
        file_path.write_text(content, encoding='utf-8')
        return str(file_path)
    
    def create_merge_head(self):
        """Create MERGE_HEAD file to simulate merge state."""
        merge_head_path = Path('.git/MERGE_HEAD')
        merge_head_path.write_text('abc123def456\n')
    
    # Tests for conflict detection and listing (Task 5.1)
    
    @patch('subprocess.run')
    def test_list_conflicted_files_with_conflicts(self, mock_run):
        """Test listing files with merge conflicts."""
        # Mock git status output with conflicted files
        mock_result = Mock()
        mock_result.stdout = """UU file1.txt
AA file2.py
M  file3.js
UD file4.md
AU file5.css"""
        mock_run.return_value = mock_result
        
        conflicted_files = self.resolver.list_conflicted_files()
        
        expected_files = ['file1.txt', 'file2.py', 'file4.md', 'file5.css']
        self.assertEqual(sorted(conflicted_files), sorted(expected_files))
        mock_run.assert_called_once_with(['git', 'status', '--porcelain'], 
                                       capture_output=True, text=True, check=True, cwd=None)
    
    @patch('subprocess.run')
    def test_list_conflicted_files_no_conflicts(self, mock_run):
        """Test listing files when no conflicts exist."""
        mock_result = Mock()
        mock_result.stdout = """M  file1.txt
A  file2.py
D  file3.js"""
        mock_run.return_value = mock_result
        
        conflicted_files = self.resolver.list_conflicted_files()
        
        self.assertEqual(conflicted_files, [])
    
    @patch('subprocess.run')
    def test_list_conflicted_files_empty_status(self, mock_run):
        """Test listing files when git status is empty."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result
        
        conflicted_files = self.resolver.list_conflicted_files()
        
        self.assertEqual(conflicted_files, [])
    
    @patch('subprocess.run')
    def test_list_conflicted_files_git_error(self, mock_run):
        """Test handling git command errors when listing conflicts."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git status')
        
        conflicted_files = self.resolver.list_conflicted_files()
        
        self.assertEqual(conflicted_files, [])
        self.mock_git_wrapper.print_error.assert_called()
    
    def test_show_conflict_preview_with_conflicts(self):
        """Test showing conflict preview with visual highlighting."""
        filename = self.create_conflicted_file('test.txt')
        
        preview = self.resolver.show_conflict_preview(filename)
        
        # Check that preview contains conflict markers and formatting
        self.assertIn('OURS (Current:', preview)
        self.assertIn('SEPARATOR', preview)
        self.assertIn('THEIRS (Incoming:', preview)
        self.assertIn('our change', preview)
        self.assertIn('their change', preview)
        
        # Check emoji usage
        if self.mock_git_wrapper.config.get('show_emoji', True):
            self.assertIn('🔴', preview)
            self.assertIn('🟡', preview)
            self.assertIn('🔵', preview)
    
    def test_show_conflict_preview_with_line_numbers(self):
        """Test conflict preview with line numbers enabled."""
        filename = self.create_conflicted_file('test.txt')
        
        preview = self.resolver.show_conflict_preview(filename)
        
        # Check that line numbers are included
        self.assertRegex(preview, r'\s*\d+:')
    
    def test_show_conflict_preview_no_conflicts(self):
        """Test conflict preview for file without conflicts."""
        filename = 'test.txt'
        Path(filename).write_text('line 1\nline 2\nline 3\n')
        
        preview = self.resolver.show_conflict_preview(filename)
        
        self.assertIn('No conflict markers found', preview)
    
    def test_show_conflict_preview_file_not_found(self):
        """Test conflict preview for non-existent file."""
        preview = self.resolver.show_conflict_preview('nonexistent.txt')
        
        self.assertIn('File not found', preview)
    
    def test_show_conflict_preview_file_read_error(self):
        """Test conflict preview with file read error."""
        # Create a file and then make it unreadable
        filename = 'test.txt'
        Path(filename).write_text('test content')
        
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            preview = self.resolver.show_conflict_preview(filename)
        
        self.assertIn('Error reading file', preview)
    
    def test_has_conflict_markers_true(self):
        """Test detection of conflict markers in content."""
        content = """line 1
<<<<<<< HEAD
our change
=======
their change
>>>>>>> branch
line 2"""
        
        has_conflicts = self.resolver._has_conflict_markers(content)
        
        self.assertTrue(has_conflicts)
    
    def test_has_conflict_markers_false(self):
        """Test detection when no conflict markers present."""
        content = """line 1
line 2
line 3"""
        
        has_conflicts = self.resolver._has_conflict_markers(content)
        
        self.assertFalse(has_conflicts)
    
    def test_has_conflict_markers_partial(self):
        """Test detection with incomplete conflict markers."""
        content = """line 1
<<<<<<< HEAD
our change
line 2"""
        
        has_conflicts = self.resolver._has_conflict_markers(content)
        
        self.assertFalse(has_conflicts)
    
    @patch('subprocess.run')
    def test_interactive_conflict_resolution_no_conflicts(self, mock_run):
        """Test interactive resolution when no conflicts exist."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result
        
        result = self.resolver.interactive_conflict_resolution()
        
        self.assertTrue(result)
        self.mock_git_wrapper.print_info.assert_called_with("No conflicts to resolve")
    
    def test_conflict_status_display_with_conflicts(self):
        """Test conflict status display formatting."""
        conflicted_files = ['file1.txt', 'file2.py', 'file3.js']
        
        self.resolver._show_conflict_status(conflicted_files)
        
        self.mock_git_wrapper.print_error.assert_called_with("Found 3 conflicted files:")
    
    def test_conflict_status_display_no_conflicts(self):
        """Test conflict status display when no conflicts."""
        conflicted_files = []
        
        self.resolver._show_conflict_status(conflicted_files)
        
        self.mock_git_wrapper.print_success.assert_called_with("No conflicts detected")
    
    @patch('subprocess.run')
    def test_check_for_conflicts_found(self, mock_run):
        """Test conflict checking when conflicts are found."""
        mock_result = Mock()
        mock_result.stdout = "UU file1.txt\nAA file2.py"
        mock_run.return_value = mock_result
        
        with patch('builtins.input'):
            self.resolver._check_for_conflicts()
        
        self.mock_git_wrapper.print_working.assert_called_with("Checking for conflicts...")
        self.mock_git_wrapper.print_error.assert_called_with("Found 2 conflicted files:")
    
    @patch('subprocess.run')
    def test_check_for_conflicts_none_found(self, mock_run):
        """Test conflict checking when no conflicts found."""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result
        
        with patch('builtins.input'):
            self.resolver._check_for_conflicts()
        
        self.mock_git_wrapper.print_working.assert_called_with("Checking for conflicts...")
        self.mock_git_wrapper.print_success.assert_called_with("No conflicts found")
    
    def test_list_conflicts_detailed_with_conflicts(self):
        """Test detailed conflict listing with file information."""
        filename = self.create_conflicted_file('test.txt')
        
        with patch.object(self.resolver, 'list_conflicted_files', return_value=[filename]):
            with patch('builtins.input'):
                with patch.object(self.resolver, 'clear_screen'):
                    self.resolver._list_conflicts_detailed()
        
        # Verify that file details were processed
        self.assertTrue(Path(filename).exists())
    
    def test_list_conflicts_detailed_no_conflicts(self):
        """Test detailed conflict listing when no conflicts exist."""
        with patch.object(self.resolver, 'list_conflicted_files', return_value=[]):
            with patch('builtins.input'):
                self.resolver._list_conflicts_detailed()
        
        self.mock_git_wrapper.print_success.assert_called_with("No conflicts found")
    
    def test_create_backup_success(self):
        """Test successful backup creation."""
        filename = 'test.txt'
        Path(filename).write_text('test content')
        
        result = self.resolver._create_backup(filename)
        
        self.assertTrue(result)
        self.assertTrue(Path(f'{filename}.conflict_backup').exists())
    
    def test_create_backup_failure(self):
        """Test backup creation failure."""
        result = self.resolver._create_backup('nonexistent.txt')
        
        self.assertFalse(result)
    
    def test_get_configured_editor_from_config(self):
        """Test getting editor from feature configuration."""
        editor = self.resolver._get_configured_editor()
        
        self.assertEqual(editor, 'code')
    
    @patch.dict(os.environ, {'VISUAL': 'vim'})
    def test_get_configured_editor_from_env(self):
        """Test getting editor from environment variable."""
        # Clear feature config
        self.resolver.config['advanced_features']['conflictresolver']['preferred_editor'] = None
        
        with patch.object(self.resolver, 'run_git_command', return_value=''):
            editor = self.resolver._get_configured_editor()
        
        self.assertEqual(editor, 'vim')
    
    @patch('platform.system')
    def test_get_configured_editor_default_macos(self, mock_system):
        """Test default editor selection on macOS."""
        mock_system.return_value = 'Darwin'
        
        # Clear all editor configs
        self.resolver.config['advanced_features']['conflictresolver']['preferred_editor'] = None
        
        with patch.object(self.resolver, 'run_git_command', return_value=''):
            with patch.dict(os.environ, {}, clear=True):
                editor = self.resolver._get_configured_editor()
        
        self.assertEqual(editor, 'open -t')
    
    @patch('platform.system')
    def test_get_configured_editor_default_linux(self, mock_system):
        """Test default editor selection on Linux."""
        mock_system.return_value = 'Linux'
        
        # Clear all editor configs
        self.resolver.config['advanced_features']['conflictresolver']['preferred_editor'] = None
        
        with patch.object(self.resolver, 'run_git_command', return_value=''):
            with patch.dict(os.environ, {}, clear=True):
                editor = self.resolver._get_configured_editor()
        
        self.assertEqual(editor, 'nano')
    
    def test_get_editor_command_vscode(self):
        """Test editor command generation for VS Code."""
        command = self.resolver._get_editor_command('test.txt')
        
        self.assertEqual(command, 'code --wait "test.txt"')
    
    def test_get_editor_command_sublime(self):
        """Test editor command generation for Sublime Text."""
        self.resolver.editor = 'subl'
        
        command = self.resolver._get_editor_command('test.txt')
        
        self.assertEqual(command, 'subl --wait "test.txt"')
    
    def test_get_editor_command_generic(self):
        """Test editor command generation for generic editor."""
        self.resolver.editor = 'vim'
        
        command = self.resolver._get_editor_command('test.txt')
        
        self.assertEqual(command, 'vim "test.txt"')
    
    # Additional tests for conflict preview and visualization (Task 5.2)
    
    def test_show_conflict_preview_enhanced_formatting(self):
        """Test enhanced conflict preview with header and footer."""
        filename = self.create_conflicted_file('test.txt')
        
        preview = self.resolver.show_conflict_preview(filename)
        
        # Check for enhanced formatting elements
        self.assertIn('File: test.txt', preview)
        self.assertIn('─' * 50, preview)  # Header separator
        self.assertIn('Found 1 conflict(s)', preview)  # Footer summary
        self.assertIn('OURS (Current:', preview)
        self.assertIn('THEIRS (Incoming:', preview)
    
    def test_show_conflict_preview_multiple_conflicts(self):
        """Test conflict preview with multiple conflict sections."""
        content = """line 1
<<<<<<< HEAD
our change 1
=======
their change 1
>>>>>>> branch1
line 3
<<<<<<< HEAD
our change 2
=======
their change 2
>>>>>>> branch2
line 5"""
        
        filename = self.create_conflicted_file('multi_conflict.txt', content)
        preview = self.resolver.show_conflict_preview(filename)
        
        # Should detect both conflicts
        self.assertIn('Found 2 conflict(s)', preview)
        self.assertIn('our change 1', preview)
        self.assertIn('their change 1', preview)
        self.assertIn('our change 2', preview)
        self.assertIn('their change 2', preview)
    
    def test_show_conflict_preview_no_emoji(self):
        """Test conflict preview without emoji when disabled."""
        self.mock_git_wrapper.config['show_emoji'] = False
        filename = self.create_conflicted_file('test.txt')
        
        preview = self.resolver.show_conflict_preview(filename)
        
        # Should use text markers instead of emoji
        self.assertIn('<<<', preview)
        self.assertIn('===', preview)
        self.assertIn('>>>', preview)
        self.assertNotIn('🔴', preview)
        self.assertNotIn('🟡', preview)
        self.assertNotIn('🔵', preview)
    
    def test_show_conflict_side_by_side_basic(self):
        """Test side-by-side conflict display."""
        filename = self.create_conflicted_file('test.txt')
        
        side_by_side = self.resolver.show_conflict_side_by_side(filename)
        
        # Check for side-by-side formatting
        self.assertIn('Side-by-side diff:', side_by_side)
        self.assertIn('OURS (Current)', side_by_side)
        self.assertIn('THEIRS (Incoming)', side_by_side)
        self.assertIn('│', side_by_side)  # Column separator
        self.assertIn('our change', side_by_side)
        self.assertIn('their change', side_by_side)
    
    def test_show_conflict_side_by_side_no_conflicts(self):
        """Test side-by-side display for file without conflicts."""
        filename = 'test.txt'
        Path(filename).write_text('line 1\nline 2\nline 3\n')
        
        side_by_side = self.resolver.show_conflict_side_by_side(filename)
        
        self.assertIn('No conflict markers found', side_by_side)
    
    def test_show_conflict_side_by_side_file_not_found(self):
        """Test side-by-side display for non-existent file."""
        side_by_side = self.resolver.show_conflict_side_by_side('nonexistent.txt')
        
        self.assertIn('File not found', side_by_side)
    
    def test_show_conflict_side_by_side_multiple_conflicts(self):
        """Test side-by-side display with multiple conflicts."""
        content = """line 1
<<<<<<< HEAD
our first change
our second line
=======
their first change
>>>>>>> branch1
line 3
<<<<<<< HEAD
our other change
=======
their other change
their extra line
>>>>>>> branch2
line 5"""
        
        filename = self.create_conflicted_file('multi.txt', content)
        side_by_side = self.resolver.show_conflict_side_by_side(filename)
        
        # Should show both conflicts
        self.assertIn('Conflict #1:', side_by_side)
        self.assertIn('Conflict #2:', side_by_side)
        self.assertIn('our first change', side_by_side)
        self.assertIn('their first change', side_by_side)
        self.assertIn('our other change', side_by_side)
        self.assertIn('their other change', side_by_side)
    
    def test_extract_conflicts_single(self):
        """Test extracting a single conflict from file lines."""
        lines = [
            'line 1',
            '<<<<<<< HEAD',
            'our change',
            '=======',
            'their change',
            '>>>>>>> branch',
            'line 2'
        ]
        
        conflicts = self.resolver._extract_conflicts(lines)
        
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['ours'], ['our change'])
        self.assertEqual(conflicts[0]['theirs'], ['their change'])
    
    def test_extract_conflicts_multiple(self):
        """Test extracting multiple conflicts from file lines."""
        lines = [
            'line 1',
            '<<<<<<< HEAD',
            'our change 1',
            '=======',
            'their change 1',
            '>>>>>>> branch1',
            'line 2',
            '<<<<<<< HEAD',
            'our change 2',
            '=======',
            'their change 2',
            '>>>>>>> branch2',
            'line 3'
        ]
        
        conflicts = self.resolver._extract_conflicts(lines)
        
        self.assertEqual(len(conflicts), 2)
        self.assertEqual(conflicts[0]['ours'], ['our change 1'])
        self.assertEqual(conflicts[0]['theirs'], ['their change 1'])
        self.assertEqual(conflicts[1]['ours'], ['our change 2'])
        self.assertEqual(conflicts[1]['theirs'], ['their change 2'])
    
    def test_extract_conflicts_multiline(self):
        """Test extracting conflicts with multiple lines in each section."""
        lines = [
            'line 1',
            '<<<<<<< HEAD',
            'our line 1',
            'our line 2',
            '=======',
            'their line 1',
            'their line 2',
            'their line 3',
            '>>>>>>> branch',
            'line 2'
        ]
        
        conflicts = self.resolver._extract_conflicts(lines)
        
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['ours'], ['our line 1', 'our line 2'])
        self.assertEqual(conflicts[0]['theirs'], ['their line 1', 'their line 2', 'their line 3'])
    
    def test_extract_conflicts_empty_sections(self):
        """Test extracting conflicts with empty sections."""
        lines = [
            'line 1',
            '<<<<<<< HEAD',
            '=======',
            'their change',
            '>>>>>>> branch',
            'line 2'
        ]
        
        conflicts = self.resolver._extract_conflicts(lines)
        
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['ours'], [])
        self.assertEqual(conflicts[0]['theirs'], ['their change'])
    
    def test_extract_conflicts_no_conflicts(self):
        """Test extracting conflicts from file with no conflicts."""
        lines = ['line 1', 'line 2', 'line 3']
        
        conflicts = self.resolver._extract_conflicts(lines)
        
        self.assertEqual(len(conflicts), 0)
    
    # Tests for conflict resolution strategies (Task 5.3)
    
    @patch('subprocess.run')
    def test_resolve_conflict_ours_strategy(self, mock_run):
        """Test resolving conflict using 'ours' strategy."""
        filename = self.create_conflicted_file('test.txt')
        
        result = self.resolver.resolve_conflict(filename, 'ours')
        
        self.assertTrue(result)
        
        # Check that file contains only 'our' changes
        with open(filename, 'r') as f:
            content = f.read()
        
        self.assertIn('our change', content)
        self.assertNotIn('their change', content)
        self.assertNotIn('<<<<<<<', content)
        self.assertNotIn('=======', content)
        self.assertNotIn('>>>>>>>', content)
    
    @patch('subprocess.run')
    def test_resolve_conflict_theirs_strategy(self, mock_run):
        """Test resolving conflict using 'theirs' strategy."""
        filename = self.create_conflicted_file('test.txt')
        
        result = self.resolver.resolve_conflict(filename, 'theirs')
        
        self.assertTrue(result)
        
        # Check that file contains only 'their' changes
        with open(filename, 'r') as f:
            content = f.read()
        
        self.assertIn('their change', content)
        self.assertNotIn('our change', content)
        self.assertNotIn('<<<<<<<', content)
        self.assertNotIn('=======', content)
        self.assertNotIn('>>>>>>>', content)
    
    def test_resolve_conflict_file_not_found(self):
        """Test resolving conflict for non-existent file."""
        result = self.resolver.resolve_conflict('nonexistent.txt', 'ours')
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_error.assert_called_with("File not found: nonexistent.txt")
    
    def test_resolve_conflict_no_conflicts(self):
        """Test resolving conflict for file without conflicts."""
        filename = 'test.txt'
        Path(filename).write_text('line 1\nline 2\nline 3\n')
        
        result = self.resolver.resolve_conflict(filename, 'ours')
        
        self.assertTrue(result)
        self.mock_git_wrapper.print_info.assert_called_with(f"No conflicts found in {filename}")
    
    @patch('subprocess.run')
    def test_resolve_conflict_auto_strategy_empty_ours(self, mock_run):
        """Test auto-resolution when 'ours' section is empty."""
        content = """line 1
<<<<<<< HEAD
=======
their change
>>>>>>> branch
line 3"""
        
        filename = self.create_conflicted_file('test.txt', content)
        result = self.resolver.resolve_conflict(filename, 'auto')
        
        self.assertTrue(result)
        
        # Should use 'theirs' since 'ours' is empty
        with open(filename, 'r') as f:
            resolved_content = f.read()
        
        self.assertIn('their change', resolved_content)
        self.assertNotIn('<<<<<<<', resolved_content)
    
    @patch('subprocess.run')
    def test_resolve_conflict_auto_strategy_identical_sections(self, mock_run):
        """Test auto-resolution when both sections are identical."""
        content = """line 1
<<<<<<< HEAD
same change
=======
same change
>>>>>>> branch
line 3"""
        
        filename = self.create_conflicted_file('test.txt', content)
        result = self.resolver.resolve_conflict(filename, 'auto')
        
        self.assertTrue(result)
        
        # Should resolve to the common content
        with open(filename, 'r') as f:
            resolved_content = f.read()
        
        self.assertIn('same change', resolved_content)
        self.assertNotIn('<<<<<<<', resolved_content)
    
    @patch('subprocess.run')
    def test_resolve_conflict_auto_strategy_import_statements(self, mock_run):
        """Test auto-resolution for import statements."""
        content = """line 1
<<<<<<< HEAD
import os
import sys
=======
import json
import sys
>>>>>>> branch
line 3"""
        
        filename = self.create_conflicted_file('test.py', content)
        result = self.resolver.resolve_conflict(filename, 'auto')
        
        self.assertTrue(result)
        
        # Should merge import statements
        with open(filename, 'r') as f:
            resolved_content = f.read()
        
        self.assertIn('import json', resolved_content)
        self.assertIn('import os', resolved_content)
        self.assertIn('import sys', resolved_content)
        self.assertNotIn('<<<<<<<', resolved_content)
    
    def test_resolve_conflict_auto_strategy_complex_conflict(self):
        """Test auto-resolution failure for complex conflicts."""
        content = """line 1
<<<<<<< HEAD
completely different code
with multiple lines
=======
totally different approach
with different logic
>>>>>>> branch
line 3"""
        
        filename = self.create_conflicted_file('test.txt', content)
        result = self.resolver.resolve_conflict(filename, 'auto')
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_error.assert_called()
    
    def test_resolve_with_strategy_invalid_strategy(self):
        """Test resolve with invalid strategy."""
        content = "test content"
        
        result = self.resolver._resolve_with_strategy(content, 'invalid')
        
        self.assertIsNone(result)
    
    def test_auto_resolve_conflicts_no_conflicts(self):
        """Test auto-resolution with no conflicts."""
        content = "line 1\nline 2\nline 3"
        
        result = self.resolver._auto_resolve_conflicts(content)
        
        self.assertEqual(result, content)
    
    def test_extract_conflicts_with_context(self):
        """Test extracting conflicts with line number context."""
        lines = [
            'line 1',
            '<<<<<<< HEAD',
            'our change',
            '=======',
            'their change',
            '>>>>>>> branch',
            'line 2'
        ]
        
        conflicts = self.resolver._extract_conflicts_with_context(lines)
        
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]['start_line'], 1)
        self.assertEqual(conflicts[0]['end_line'], 5)
        self.assertEqual(conflicts[0]['ours'], ['our change'])
        self.assertEqual(conflicts[0]['theirs'], ['their change'])
    
    def test_resolve_single_conflict_auto_empty_ours(self):
        """Test auto-resolving single conflict with empty 'ours'."""
        conflict = {
            'ours': [],
            'theirs': ['their change']
        }
        
        result = self.resolver._resolve_single_conflict_auto(conflict)
        
        self.assertEqual(result, ['their change'])
    
    def test_resolve_single_conflict_auto_empty_theirs(self):
        """Test auto-resolving single conflict with empty 'theirs'."""
        conflict = {
            'ours': ['our change'],
            'theirs': []
        }
        
        result = self.resolver._resolve_single_conflict_auto(conflict)
        
        self.assertEqual(result, ['our change'])
    
    def test_resolve_single_conflict_auto_identical(self):
        """Test auto-resolving single conflict with identical content."""
        conflict = {
            'ours': ['same line'],
            'theirs': ['same line']
        }
        
        result = self.resolver._resolve_single_conflict_auto(conflict)
        
        self.assertEqual(result, ['same line'])
    
    def test_resolve_single_conflict_auto_subset(self):
        """Test auto-resolving single conflict where one is subset of other."""
        conflict = {
            'ours': ['line 1'],
            'theirs': ['line 1', 'line 2']
        }
        
        result = self.resolver._resolve_single_conflict_auto(conflict)
        
        self.assertEqual(result, ['line 1', 'line 2'])
    
    def test_resolve_single_conflict_auto_whitespace_diff(self):
        """Test auto-resolving single conflict with only whitespace differences."""
        conflict = {
            'ours': ['  line 1  ', '  line 2  '],
            'theirs': ['line 1', 'line 2']
        }
        
        result = self.resolver._resolve_single_conflict_auto(conflict)
        
        # Should prefer the version with more content (including whitespace)
        self.assertIsNotNone(result)
        self.assertTrue(len(result) == 2)
    
    def test_resolve_single_conflict_auto_cannot_resolve(self):
        """Test auto-resolving single conflict that cannot be resolved."""
        conflict = {
            'ours': ['completely different'],
            'theirs': ['totally different']
        }
        
        result = self.resolver._resolve_single_conflict_auto(conflict)
        
        self.assertIsNone(result)
    
    def test_is_subset_lines_true(self):
        """Test line subset detection when true."""
        subset = ['line 1']
        superset = ['line 1', 'line 2']
        
        result = self.resolver._is_subset_lines(subset, superset)
        
        self.assertTrue(result)
    
    def test_is_subset_lines_false(self):
        """Test line subset detection when false."""
        subset = ['line 1', 'line 3']
        superset = ['line 1', 'line 2']
        
        result = self.resolver._is_subset_lines(subset, superset)
        
        self.assertFalse(result)
    
    def test_are_import_statements_python(self):
        """Test import statement detection for Python."""
        lines = ['import os', 'from sys import path']
        
        result = self.resolver._are_import_statements(lines)
        
        self.assertTrue(result)
    
    def test_are_import_statements_javascript(self):
        """Test import statement detection for JavaScript."""
        lines = ['const fs = require("fs")', 'require("path")']
        
        result = self.resolver._are_import_statements(lines)
        
        self.assertTrue(result)
    
    def test_are_import_statements_false(self):
        """Test import statement detection for non-import lines."""
        lines = ['function test()', 'return true']
        
        result = self.resolver._are_import_statements(lines)
        
        self.assertFalse(result)
    
    def test_merge_import_statements(self):
        """Test merging import statements."""
        ours = ['import os', 'import sys']
        theirs = ['import json', 'import sys']
        
        result = self.resolver._merge_import_statements(ours, theirs)
        
        expected = ['import json', 'import os', 'import sys']
        self.assertEqual(sorted(result), sorted(expected))
    
    @patch('subprocess.run')
    def test_resolve_conflict_with_backup(self, mock_run):
        """Test conflict resolution with backup creation."""
        filename = self.create_conflicted_file('test.txt')
        
        # Enable backup
        self.resolver.set_feature_config('backup_before_resolve', True)
        
        result = self.resolver.resolve_conflict(filename, 'ours')
        
        self.assertTrue(result)
        self.assertTrue(Path(f'{filename}.conflict_backup').exists())
    
    @patch('subprocess.run')
    def test_resolve_conflict_without_auto_stage(self, mock_run):
        """Test conflict resolution without auto-staging."""
        filename = self.create_conflicted_file('test.txt')
        
        # Disable auto-staging
        self.resolver.set_feature_config('auto_stage_resolved', False)
        
        result = self.resolver.resolve_conflict(filename, 'ours')
        
        self.assertTrue(result)
        # Should not call git add
        mock_run.assert_not_called()
    
    # Tests for editor integration and merge finalization (Task 5.4)
    
    @patch('subprocess.run')
    def test_open_in_editor_success(self, mock_run):
        """Test successfully opening file in editor."""
        filename = self.create_conflicted_file('test.txt')
        mock_run.return_value.returncode = 0
        self.mock_git_wrapper.confirm.return_value = True
        
        result = self.resolver.open_in_editor(filename)
        
        self.assertTrue(result)
        self.mock_git_wrapper.print_working.assert_called()
        self.mock_git_wrapper.print_success.assert_called()
    
    def test_open_in_editor_file_not_found(self):
        """Test opening non-existent file in editor."""
        result = self.resolver.open_in_editor('nonexistent.txt')
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_error.assert_called_with("File not found: nonexistent.txt")
    
    @patch('subprocess.run')
    def test_open_in_editor_failure(self, mock_run):
        """Test editor opening failure."""
        filename = self.create_conflicted_file('test.txt')
        mock_run.return_value.returncode = 1
        
        result = self.resolver.open_in_editor(filename)
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_error.assert_called_with("Editor exited with error")
    
    @patch('subprocess.run')
    def test_open_in_editor_no_staging(self, mock_run):
        """Test opening file in editor without staging after edit."""
        filename = self.create_conflicted_file('test.txt')
        mock_run.return_value.returncode = 0
        self.mock_git_wrapper.confirm.return_value = False
        
        result = self.resolver.open_in_editor(filename)
        
        self.assertTrue(result)
        # Should not call git add since user declined staging
        git_add_calls = [call for call in mock_run.call_args_list if 'git' in str(call) and 'add' in str(call)]
        self.assertEqual(len(git_add_calls), 0)
    
    @patch('subprocess.run')
    def test_finalize_merge_success(self, mock_run):
        """Test successful merge finalization."""
        # Create MERGE_HEAD to simulate merge state
        self.create_merge_head()
        
        # Mock no conflicted files
        with patch.object(self.resolver, 'list_conflicted_files', return_value=[]):
            # Mock successful git commit
            mock_run.return_value = Mock()
            
            result = self.resolver.finalize_merge()
        
        self.assertTrue(result)
        self.mock_git_wrapper.print_working.assert_called_with("Finalizing merge...")
        self.mock_git_wrapper.print_success.assert_called_with("Merge completed successfully!")
    
    def test_finalize_merge_with_unresolved_conflicts(self):
        """Test merge finalization with unresolved conflicts."""
        # Create MERGE_HEAD to simulate merge state
        self.create_merge_head()
        
        # Mock conflicted files still exist
        with patch.object(self.resolver, 'list_conflicted_files', return_value=['file1.txt', 'file2.py']):
            result = self.resolver.finalize_merge()
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_error.assert_called_with("Cannot finalize merge - unresolved conflicts remain:")
    
    def test_finalize_merge_no_merge_in_progress(self):
        """Test merge finalization when no merge is in progress."""
        # No MERGE_HEAD file exists
        result = self.resolver.finalize_merge()
        
        self.assertTrue(result)
        self.mock_git_wrapper.print_info.assert_called_with("No merge in progress")
    
    @patch('subprocess.run')
    def test_finalize_merge_git_error(self, mock_run):
        """Test merge finalization with git command error."""
        # Create MERGE_HEAD to simulate merge state
        self.create_merge_head()
        
        # Mock no conflicted files
        with patch.object(self.resolver, 'list_conflicted_files', return_value=[]):
            # Mock git commit failure
            mock_run.side_effect = subprocess.CalledProcessError(1, 'git commit')
            
            result = self.resolver.finalize_merge()
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_error.assert_called()
    
    @patch('subprocess.run')
    def test_abort_merge_success(self, mock_run):
        """Test successful merge abort."""
        # Create MERGE_HEAD to simulate merge state
        self.create_merge_head()
        self.mock_git_wrapper.confirm.return_value = True
        
        # Mock successful git merge --abort
        mock_run.return_value = Mock()
        
        result = self.resolver.abort_merge()
        
        self.assertTrue(result)
        self.mock_git_wrapper.print_working.assert_called_with("Aborting merge...")
        self.mock_git_wrapper.print_success.assert_called_with("Merge aborted successfully!")
    
    def test_abort_merge_no_merge_in_progress(self):
        """Test merge abort when no merge is in progress."""
        # No MERGE_HEAD file exists
        result = self.resolver.abort_merge()
        
        self.assertTrue(result)
        self.mock_git_wrapper.print_info.assert_called_with("No merge in progress")
    
    def test_abort_merge_user_declines(self):
        """Test merge abort when user declines confirmation."""
        # Create MERGE_HEAD to simulate merge state
        self.create_merge_head()
        self.mock_git_wrapper.confirm.return_value = False
        
        result = self.resolver.abort_merge()
        
        self.assertFalse(result)
    
    @patch('subprocess.run')
    def test_abort_merge_git_error(self, mock_run):
        """Test merge abort with git command error."""
        # Create MERGE_HEAD to simulate merge state
        self.create_merge_head()
        self.mock_git_wrapper.confirm.return_value = True
        
        # Mock git merge --abort failure
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git merge --abort')
        
        result = self.resolver.abort_merge()
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_error.assert_called()
    
    @patch('subprocess.run')
    def test_interactive_conflict_resolution_complete_workflow(self, mock_run):
        """Test complete interactive conflict resolution workflow."""
        filename = self.create_conflicted_file('test.txt')
        
        # Mock conflicted files list
        with patch.object(self.resolver, 'list_conflicted_files') as mock_list:
            mock_list.side_effect = [[filename], []]  # First call has conflicts, second call has none
            
            # Mock user input for resolution choice
            self.mock_git_wrapper.get_input.return_value = "1"  # Choose 'ours'
            self.mock_git_wrapper.confirm.return_value = True  # Confirm finalize merge
            
            # Mock finalize_merge success
            with patch.object(self.resolver, 'finalize_merge', return_value=True):
                result = self.resolver.interactive_conflict_resolution()
        
        self.assertTrue(result)
    
    @patch('subprocess.run')
    def test_interactive_conflict_resolution_user_aborts(self, mock_run):
        """Test interactive conflict resolution when user aborts."""
        filename = self.create_conflicted_file('test.txt')
        
        # Mock conflicted files list
        with patch.object(self.resolver, 'list_conflicted_files', return_value=[filename]):
            # Mock user input to abort
            self.mock_git_wrapper.get_input.return_value = "6"  # Abort
            
            result = self.resolver.interactive_conflict_resolution()
        
        self.assertFalse(result)
        self.mock_git_wrapper.print_info.assert_called_with("Conflict resolution aborted")
    
    @patch('subprocess.run')
    def test_interactive_conflict_resolution_skip_file(self, mock_run):
        """Test interactive conflict resolution when user skips files."""
        filename = self.create_conflicted_file('test.txt')
        
        # Mock conflicted files list
        with patch.object(self.resolver, 'list_conflicted_files') as mock_list:
            mock_list.side_effect = [[filename], [filename]]  # Conflicts remain after skipping
            
            # Mock user input to skip
            self.mock_git_wrapper.get_input.return_value = "5"  # Skip
            
            result = self.resolver.interactive_conflict_resolution()
        
        self.assertFalse(result)  # Should return False since conflicts remain
    
    def test_get_editor_command_special_cases(self):
        """Test editor command generation for special cases."""
        # Test VS Code
        self.resolver.editor = 'code'
        command = self.resolver._get_editor_command('test.txt')
        self.assertEqual(command, 'code --wait "test.txt"')
        
        # Test Sublime Text
        self.resolver.editor = 'subl'
        command = self.resolver._get_editor_command('test.txt')
        self.assertEqual(command, 'subl --wait "test.txt"')
        
        # Test macOS open command
        self.resolver.editor = 'open -t'
        command = self.resolver._get_editor_command('test.txt')
        self.assertEqual(command, 'open -t "test.txt"')
        
        # Test generic editor
        self.resolver.editor = 'nano'
        command = self.resolver._get_editor_command('test.txt')
        self.assertEqual(command, 'nano "test.txt"')
    
    @patch('subprocess.run')
    def test_resolve_conflict_manual_strategy(self, mock_run):
        """Test resolving conflict using manual strategy (editor)."""
        filename = self.create_conflicted_file('test.txt')
        mock_run.return_value.returncode = 0
        self.mock_git_wrapper.confirm.return_value = True
        
        result = self.resolver.resolve_conflict(filename, 'manual')
        
        self.assertTrue(result)
        # Should have called the editor
        mock_run.assert_called()
    
    def test_complete_conflict_resolution_workflow_integration(self):
        """Test complete workflow integration with all components."""
        # This test verifies that all the components work together
        filename = self.create_conflicted_file('test.txt')
        
        # Test conflict detection
        conflicts = self.resolver.list_conflicted_files()
        self.assertIsInstance(conflicts, list)
        
        # Test conflict preview
        preview = self.resolver.show_conflict_preview(filename)
        self.assertIn('File:', preview)
        
        # Test side-by-side view
        side_by_side = self.resolver.show_conflict_side_by_side(filename)
        self.assertIn('Side-by-side diff:', side_by_side)
        
        # Test conflict resolution
        with patch('subprocess.run'):
            result = self.resolver.resolve_conflict(filename, 'ours')
            self.assertTrue(result)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)