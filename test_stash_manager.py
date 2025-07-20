#!/usr/bin/env python3
"""
Unit Tests for StashManager

Tests for the StashManager class focusing on metadata persistence,
stash creation, listing, and core functionality.
"""

import unittest
import tempfile
import shutil
import json
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add the features directory to the path
import sys
sys.path.insert(0, 'features')

# Import the modules directly
from features.stash_manager import StashManager


class TestStashManager(unittest.TestCase):
    """Test cases for StashManager class."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create a mock git wrapper
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {
            'show_emoji': True,
            'advanced_features': {
                'stash_management': {
                    'auto_name_stashes': True,
                    'max_stashes': 50,
                    'show_preview_lines': 10,
                    'confirm_deletions': True
                }
            }
        }
        
        # Mock the print methods
        self.mock_git_wrapper.print_success = Mock()
        self.mock_git_wrapper.print_error = Mock()
        self.mock_git_wrapper.print_info = Mock()
        self.mock_git_wrapper.print_working = Mock()
        self.mock_git_wrapper.save_config = Mock()
        
        # Create a mock .git directory
        self.git_dir = Path(self.test_dir) / '.git'
        self.git_dir.mkdir()
        
        # Initialize StashManager
        self.stash_manager = StashManager(self.mock_git_wrapper)
    
    def tearDown(self):
        """Clean up after each test."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    def test_init(self):
        """Test StashManager initialization."""
        self.assertIsNotNone(self.stash_manager)
        self.assertEqual(self.stash_manager.git_wrapper, self.mock_git_wrapper)
        self.assertTrue(self.stash_manager.stash_metadata_file.exists())
    
    def test_get_default_config(self):
        """Test default configuration values."""
        config = self.stash_manager._get_default_config()
        
        expected_keys = ['auto_name_stashes', 'max_stashes', 'show_preview_lines', 'confirm_deletions']
        for key in expected_keys:
            self.assertIn(key, config)
        
        self.assertTrue(config['auto_name_stashes'])
        self.assertEqual(config['max_stashes'], 50)
        self.assertEqual(config['show_preview_lines'], 10)
        self.assertTrue(config['confirm_deletions'])
    
    def test_metadata_file_path(self):
        """Test metadata file path generation."""
        with patch.object(self.stash_manager, 'get_git_root', return_value=Path(self.test_dir)):
            path = self.stash_manager._get_stash_metadata_path()
            expected_path = Path(self.test_dir) / '.git' / 'gitwrapper_stashes.json'
            self.assertEqual(path, expected_path)
    
    def test_metadata_file_creation(self):
        """Test that metadata file is created on initialization."""
        self.assertTrue(self.stash_manager.stash_metadata_file.exists())
        
        # Check that it contains empty dict
        with open(self.stash_manager.stash_metadata_file, 'r') as f:
            data = json.load(f)
            self.assertEqual(data, {})
    
    def test_load_metadata_empty(self):
        """Test loading metadata from empty file."""
        metadata = self.stash_manager._load_metadata()
        self.assertEqual(metadata, {})
    
    def test_save_and_load_metadata(self):
        """Test saving and loading metadata."""
        test_metadata = {
            'stash@{0}': {
                'name': 'test_stash',
                'description': 'Test description',
                'created_at': 1234567890,
                'branch': 'main'
            }
        }
        
        # Save metadata
        result = self.stash_manager._save_metadata(test_metadata)
        self.assertTrue(result)
        
        # Load metadata
        loaded_metadata = self.stash_manager._load_metadata()
        self.assertEqual(loaded_metadata, test_metadata)
    
    def test_generate_stash_name(self):
        """Test stash name generation."""
        with patch.object(self.stash_manager, 'get_current_branch', return_value='feature-branch'):
            # Test with message
            name = self.stash_manager._generate_stash_name("Fix bug in authentication")
            self.assertIn('feature-branch', name)
            self.assertIn('fix', name.lower())
            self.assertIn('bug', name.lower())
            
            # Test without message
            name = self.stash_manager._generate_stash_name()
            self.assertIn('feature-branch', name)
            self.assertIn('stash', name)
    
    def test_update_stash_metadata(self):
        """Test updating metadata for a specific stash."""
        stash_id = 'stash@{0}'
        name = 'test_stash'
        description = 'Test description'
        
        with patch.object(self.stash_manager, 'get_current_branch', return_value='main'):
            result = self.stash_manager._update_stash_metadata(stash_id, name, description)
            self.assertTrue(result)
            
            # Verify metadata was saved
            metadata = self.stash_manager._load_metadata()
            self.assertIn(stash_id, metadata)
            self.assertEqual(metadata[stash_id]['name'], name)
            self.assertEqual(metadata[stash_id]['description'], description)
            self.assertEqual(metadata[stash_id]['branch'], 'main')
            self.assertIsInstance(metadata[stash_id]['created_at'], float)
    
    @patch('subprocess.run')
    def test_get_git_stashes(self, mock_run):
        """Test getting Git stashes from git stash list."""
        # Mock git stash list output
        mock_result = Mock()
        mock_result.stdout = "stash@{0}: WIP on main: Fix authentication bug\nstash@{1}: On feature: Add new feature"
        mock_run.return_value = mock_result
        
        with patch.object(self.stash_manager, 'run_git_command', return_value=mock_result.stdout):
            stashes = self.stash_manager._get_git_stashes()
            
            self.assertEqual(len(stashes), 2)
            
            # Check first stash
            self.assertEqual(stashes[0]['id'], 'stash@{0}')
            self.assertEqual(stashes[0]['info'], 'WIP on main')
            self.assertEqual(stashes[0]['message'], 'Fix authentication bug')
            
            # Check second stash
            self.assertEqual(stashes[1]['id'], 'stash@{1}')
            self.assertEqual(stashes[1]['info'], 'On feature')
            self.assertEqual(stashes[1]['message'], 'Add new feature')
    
    def test_get_git_stashes_empty(self):
        """Test getting Git stashes when none exist."""
        with patch.object(self.stash_manager, 'run_git_command', return_value=""):
            stashes = self.stash_manager._get_git_stashes()
            self.assertEqual(stashes, [])
    
    def test_cleanup_stale_metadata(self):
        """Test cleanup of metadata for non-existent stashes."""
        # Add some metadata
        test_metadata = {
            'stash@{0}': {'name': 'existing_stash'},
            'stash@{1}': {'name': 'stale_stash'},
            'stash@{2}': {'name': 'another_stale_stash'}
        }
        self.stash_manager._save_metadata(test_metadata)
        
        # Mock current stashes (only one exists)
        mock_stashes = [{'id': 'stash@{0}', 'info': 'WIP', 'message': 'test'}]
        
        with patch.object(self.stash_manager, '_get_git_stashes', return_value=mock_stashes):
            self.stash_manager._cleanup_stale_metadata()
            
            # Check that stale metadata was removed
            metadata = self.stash_manager._load_metadata()
            self.assertIn('stash@{0}', metadata)
            self.assertNotIn('stash@{1}', metadata)
            self.assertNotIn('stash@{2}', metadata)
    
    def test_create_named_stash_success(self):
        """Test successful creation of a named stash."""
        name = 'test_stash'
        message = 'Test message'
        description = 'Test description'
        
        # Mock successful git stash command
        with patch.object(self.stash_manager, 'run_git_command', return_value=True):
            # Mock getting the new stash
            mock_stashes = [{'id': 'stash@{0}', 'info': 'WIP', 'message': message}]
            with patch.object(self.stash_manager, '_get_git_stashes', return_value=mock_stashes):
                result = self.stash_manager.create_named_stash(name, message, description)
                
                self.assertTrue(result)
                
                # Verify metadata was created
                metadata = self.stash_manager._load_metadata()
                self.assertIn('stash@{0}', metadata)
                self.assertEqual(metadata['stash@{0}']['name'], name)
                self.assertEqual(metadata['stash@{0}']['description'], description)
    
    def test_create_named_stash_failure(self):
        """Test failed creation of a named stash."""
        name = 'test_stash'
        message = 'Test message'
        
        # Mock failed git stash command
        with patch.object(self.stash_manager, 'run_git_command', return_value=False):
            result = self.stash_manager.create_named_stash(name, message)
            self.assertFalse(result)
    
    def test_list_stashes_with_metadata(self):
        """Test listing stashes with metadata."""
        # Set up test data
        mock_git_stashes = [
            {'id': 'stash@{0}', 'info': 'WIP on main', 'message': 'Fix bug', 'full_line': 'stash@{0}: WIP on main: Fix bug'},
            {'id': 'stash@{1}', 'info': 'On feature', 'message': 'Add feature', 'full_line': 'stash@{1}: On feature: Add feature'}
        ]
        
        test_metadata = {
            'stash@{0}': {
                'name': 'bug_fix_stash',
                'description': 'Fixes authentication bug',
                'created_at': 1234567890,
                'branch': 'main'
            }
        }
        
        self.stash_manager._save_metadata(test_metadata)
        
        with patch.object(self.stash_manager, '_get_git_stashes', return_value=mock_git_stashes):
            stashes = self.stash_manager.list_stashes_with_metadata()
            
            self.assertEqual(len(stashes), 2)
            
            # Check first stash (has metadata)
            self.assertEqual(stashes[0]['id'], 'stash@{0}')
            self.assertEqual(stashes[0]['name'], 'bug_fix_stash')
            self.assertEqual(stashes[0]['description'], 'Fixes authentication bug')
            self.assertEqual(stashes[0]['branch'], 'main')
            
            # Check second stash (no metadata)
            self.assertEqual(stashes[1]['id'], 'stash@{1}')
            self.assertEqual(stashes[1]['name'], 'Unnamed')
            self.assertEqual(stashes[1]['description'], '')
            self.assertEqual(stashes[1]['branch'], 'unknown')
    
    def test_apply_stash_success(self):
        """Test successful stash application."""
        stash_id = 'stash@{0}'
        
        with patch.object(self.stash_manager, 'run_git_command', return_value=True):
            # Test apply (keep stash)
            result = self.stash_manager.apply_stash(stash_id, keep=True)
            self.assertTrue(result)
            
            # Test pop (remove stash)
            # First add some metadata
            test_metadata = {stash_id: {'name': 'test_stash'}}
            self.stash_manager._save_metadata(test_metadata)
            
            result = self.stash_manager.apply_stash(stash_id, keep=False)
            self.assertTrue(result)
            
            # Verify metadata was removed
            metadata = self.stash_manager._load_metadata()
            self.assertNotIn(stash_id, metadata)
    
    def test_apply_stash_failure(self):
        """Test failed stash application."""
        stash_id = 'stash@{0}'
        
        with patch.object(self.stash_manager, 'run_git_command', return_value=False):
            result = self.stash_manager.apply_stash(stash_id)
            self.assertFalse(result)
    
    def test_delete_stash_success(self):
        """Test successful stash deletion."""
        stash_id = 'stash@{0}'
        
        # Add metadata
        test_metadata = {stash_id: {'name': 'test_stash'}}
        self.stash_manager._save_metadata(test_metadata)
        
        with patch.object(self.stash_manager, 'run_git_command', return_value=True):
            result = self.stash_manager.delete_stash(stash_id)
            self.assertTrue(result)
            
            # Verify metadata was removed
            metadata = self.stash_manager._load_metadata()
            self.assertNotIn(stash_id, metadata)
    
    def test_delete_stash_failure(self):
        """Test failed stash deletion."""
        stash_id = 'stash@{0}'
        
        with patch.object(self.stash_manager, 'run_git_command', return_value=False):
            result = self.stash_manager.delete_stash(stash_id)
            self.assertFalse(result)
    
    def test_search_stashes(self):
        """Test stash search functionality."""
        # Set up test data
        mock_git_stashes = [
            {'id': 'stash@{0}', 'info': 'WIP on main', 'message': 'Fix authentication bug', 'full_line': 'test'},
            {'id': 'stash@{1}', 'info': 'On feature', 'message': 'Add user profile', 'full_line': 'test'}
        ]
        
        test_metadata = {
            'stash@{0}': {
                'name': 'auth_fix',
                'description': 'Fixes login issues',
                'branch': 'main'
            },
            'stash@{1}': {
                'name': 'profile_feature',
                'description': 'User profile implementation',
                'branch': 'feature'
            }
        }
        
        self.stash_manager._save_metadata(test_metadata)
        
        with patch.object(self.stash_manager, '_get_git_stashes', return_value=mock_git_stashes):
            # Search by name
            results = self.stash_manager.search_stashes('auth')
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['id'], 'stash@{0}')
            
            # Search by description
            results = self.stash_manager.search_stashes('login')
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['id'], 'stash@{0}')
            
            # Search by branch
            results = self.stash_manager.search_stashes('feature')
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['id'], 'stash@{1}')
            
            # Search with no results
            results = self.stash_manager.search_stashes('nonexistent')
            self.assertEqual(len(results), 0)
    
    def test_preview_stash(self):
        """Test stash preview functionality."""
        stash_id = 'stash@{0}'
        mock_content = "diff --git a/file.txt b/file.txt\n+added line"
        
        with patch.object(self.stash_manager, 'run_git_command', return_value=mock_content):
            with patch.object(self.stash_manager, 'clear_screen'):
                with patch('builtins.input'):  # Mock input for "Press Enter"
                    content = self.stash_manager.preview_stash(stash_id)
                    self.assertEqual(content, mock_content)


    def test_create_named_stash_interactive_workflow(self):
        """Test the interactive stash creation workflow."""
        # Mock user inputs and git commands
        with patch.object(self.stash_manager, 'run_git_command') as mock_git:
            with patch.object(self.stash_manager, 'get_input') as mock_input:
                with patch.object(self.stash_manager, 'clear_screen'):
                    with patch('builtins.input'):  # Mock final input
                        with patch.object(self.stash_manager, 'create_named_stash', return_value=True) as mock_create:
                            # Mock git status showing changes
                            mock_git.return_value = "M file1.txt\nA file2.txt"  # git status --porcelain
                            
                            # Mock user inputs
                            mock_input.side_effect = [
                                "Fix authentication bug",  # message
                                "auth_fix_stash",  # name
                                "Fixes login issues"  # description
                            ]
                            
                            self.stash_manager.create_named_stash_interactive()
                            
                            # Verify create_named_stash was called with correct parameters
                            mock_create.assert_called_once_with('auth_fix_stash', 'Fix authentication bug', 'Fixes login issues')
    
    def test_list_stashes_with_metadata_display(self):
        """Test the display of stashes with metadata."""
        # Set up test data
        mock_git_stashes = [
            {'id': 'stash@{0}', 'info': 'WIP on main', 'message': 'Fix bug', 'full_line': 'stash@{0}: WIP on main: Fix bug'},
            {'id': 'stash@{1}', 'info': 'On feature', 'message': 'Add feature', 'full_line': 'stash@{1}: On feature: Add feature'}
        ]
        
        test_metadata = {
            'stash@{0}': {
                'name': 'bug_fix_stash',
                'description': 'Fixes authentication bug',
                'created_at': 1234567890,
                'branch': 'main'
            },
            'stash@{1}': {
                'name': 'feature_stash',
                'description': 'New user feature',
                'created_at': 1234567900,
                'branch': 'feature'
            }
        }
        
        self.stash_manager._save_metadata(test_metadata)
        
        with patch.object(self.stash_manager, '_get_git_stashes', return_value=mock_git_stashes):
            with patch.object(self.stash_manager, 'clear_screen'):
                with patch('builtins.input'):  # Mock input for "Press Enter"
                    self.stash_manager.show_all_stashes()
                    
                    # Verify the method completes without error
                    # (actual display testing would require capturing stdout)
    
    def test_named_stash_creation_with_auto_naming(self):
        """Test named stash creation with automatic naming."""
        with patch.object(self.stash_manager, 'get_current_branch', return_value='feature-auth'):
            # Test auto-naming with message
            name = self.stash_manager._generate_stash_name("Fix authentication bug")
            self.assertIn('feature-auth', name)
            self.assertIn('fix', name.lower())
            self.assertIn('authentication', name.lower())
            
            # Test auto-naming without message
            name = self.stash_manager._generate_stash_name()
            self.assertIn('feature-auth', name)
            self.assertIn('stash', name)
            
            # Verify timestamp is included
            import time
            current_time = time.strftime("%Y%m%d")
            self.assertIn(current_time, name)
    
    def test_stash_listing_with_empty_repository(self):
        """Test stash listing when no stashes exist."""
        with patch.object(self.stash_manager, '_get_git_stashes', return_value=[]):
            stashes = self.stash_manager.list_stashes_with_metadata()
            self.assertEqual(len(stashes), 0)
    
    def test_stash_metadata_persistence_across_operations(self):
        """Test that metadata persists across multiple operations."""
        # Create first stash
        stash_id_1 = 'stash@{0}'
        name_1 = 'first_stash'
        desc_1 = 'First test stash'
        
        with patch.object(self.stash_manager, 'get_current_branch', return_value='main'):
            result = self.stash_manager._update_stash_metadata(stash_id_1, name_1, desc_1)
            self.assertTrue(result)
        
        # Create second stash
        stash_id_2 = 'stash@{1}'
        name_2 = 'second_stash'
        desc_2 = 'Second test stash'
        
        with patch.object(self.stash_manager, 'get_current_branch', return_value='feature'):
            result = self.stash_manager._update_stash_metadata(stash_id_2, name_2, desc_2)
            self.assertTrue(result)
        
        # Verify both stashes exist in metadata
        metadata = self.stash_manager._load_metadata()
        self.assertIn(stash_id_1, metadata)
        self.assertIn(stash_id_2, metadata)
        self.assertEqual(metadata[stash_id_1]['name'], name_1)
        self.assertEqual(metadata[stash_id_2]['name'], name_2)
        self.assertEqual(metadata[stash_id_1]['branch'], 'main')
        self.assertEqual(metadata[stash_id_2]['branch'], 'feature')

    def test_preview_stash_with_limited_lines(self):
        """Test stash preview with line limit configuration."""
        stash_id = 'stash@{0}'
        long_content = '\n'.join([f"line {i}" for i in range(20)])
        
        # Set preview line limit
        self.stash_manager.set_feature_config('show_preview_lines', 5)
        
        with patch.object(self.stash_manager, 'run_git_command', return_value=long_content):
            with patch.object(self.stash_manager, 'clear_screen'):
                with patch('builtins.input'):  # Mock input for "Press Enter"
                    content = self.stash_manager.preview_stash(stash_id)
                    self.assertEqual(content, long_content)
    
    def test_preview_stash_empty_content(self):
        """Test stash preview with empty content."""
        stash_id = 'stash@{0}'
        
        with patch.object(self.stash_manager, 'run_git_command', return_value=""):
            with patch.object(self.stash_manager, 'clear_screen'):
                with patch('builtins.input'):  # Mock input for "Press Enter"
                    content = self.stash_manager.preview_stash(stash_id)
                    self.assertEqual(content, "")
    
    def test_search_stashes_by_content(self):
        """Test searching stashes by content."""
        # Set up test data
        mock_git_stashes = [
            {'id': 'stash@{0}', 'info': 'WIP on main', 'message': 'Fix bug', 'full_line': 'test'},
            {'id': 'stash@{1}', 'info': 'On feature', 'message': 'Add feature', 'full_line': 'test'}
        ]
        
        test_metadata = {
            'stash@{0}': {'name': 'bug_fix', 'description': '', 'branch': 'main'},
            'stash@{1}': {'name': 'feature_add', 'description': '', 'branch': 'feature'}
        }
        
        self.stash_manager._save_metadata(test_metadata)
        
        # Mock stash content search
        def mock_git_command(cmd, capture_output=False):
            if 'show' in cmd and '-p' in cmd:
                if 'stash@{0}' in cmd:
                    return "authentication code changes"
                elif 'stash@{1}' in cmd:
                    return "user profile implementation"
            return ""
        
        with patch.object(self.stash_manager, '_get_git_stashes', return_value=mock_git_stashes):
            with patch.object(self.stash_manager, 'run_git_command', side_effect=mock_git_command):
                # Search by content
                results = self.stash_manager.search_stashes('authentication')
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0]['id'], 'stash@{0}')
                
                results = self.stash_manager.search_stashes('profile')
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0]['id'], 'stash@{1}')
    
    def test_search_stashes_case_insensitive(self):
        """Test that stash search is case insensitive."""
        mock_git_stashes = [
            {'id': 'stash@{0}', 'info': 'WIP on main', 'message': 'Fix Authentication Bug', 'full_line': 'test'}
        ]
        
        test_metadata = {
            'stash@{0}': {'name': 'Auth_Fix', 'description': 'Login Issues', 'branch': 'main'}
        }
        
        self.stash_manager._save_metadata(test_metadata)
        
        with patch.object(self.stash_manager, '_get_git_stashes', return_value=mock_git_stashes):
            # Test case insensitive search
            results = self.stash_manager.search_stashes('auth')
            self.assertEqual(len(results), 1)
            
            results = self.stash_manager.search_stashes('AUTH')
            self.assertEqual(len(results), 1)
            
            results = self.stash_manager.search_stashes('login')
            self.assertEqual(len(results), 1)
            
            results = self.stash_manager.search_stashes('LOGIN')
            self.assertEqual(len(results), 1)
    
    def test_interactive_preview_selection(self):
        """Test interactive stash preview selection."""
        mock_stashes = [
            {'id': 'stash@{0}', 'name': 'test_stash_1'},
            {'id': 'stash@{1}', 'name': 'test_stash_2'}
        ]
        
        with patch.object(self.stash_manager, 'list_stashes_with_metadata', return_value=mock_stashes):
            with patch.object(self.stash_manager, 'get_choice', return_value='test_stash_1 (stash@{0})'):
                with patch.object(self.stash_manager, 'preview_stash') as mock_preview:
                    self.stash_manager.preview_stash_interactive()
                    mock_preview.assert_called_once_with('stash@{0}')
    
    def test_interactive_search_workflow(self):
        """Test the interactive search workflow."""
        mock_results = [
            {'id': 'stash@{0}', 'name': 'found_stash', 'description': 'test', 'branch': 'main', 'created_at': 1234567890}
        ]
        
        with patch.object(self.stash_manager, 'get_input', return_value='test_query'):
            with patch.object(self.stash_manager, 'search_stashes', return_value=mock_results):
                with patch.object(self.stash_manager, 'clear_screen'):
                    with patch('builtins.input'):  # Mock input for "Press Enter"
                        self.stash_manager.search_stashes_interactive()
                        # Test completes without error
    
    def test_search_stashes_no_results(self):
        """Test search with no matching results."""
        mock_git_stashes = [
            {'id': 'stash@{0}', 'info': 'WIP on main', 'message': 'Fix bug', 'full_line': 'test'}
        ]
        
        with patch.object(self.stash_manager, '_get_git_stashes', return_value=mock_git_stashes):
            results = self.stash_manager.search_stashes('nonexistent_term')
            self.assertEqual(len(results), 0)
    
    def test_preview_stash_error_handling(self):
        """Test preview stash with error handling."""
        stash_id = 'stash@{0}'
        
        with patch.object(self.stash_manager, 'run_git_command', side_effect=Exception("Git error")):
            with patch.object(self.stash_manager, 'clear_screen'):
                with patch('builtins.input'):  # Mock input for "Press Enter"
                    content = self.stash_manager.preview_stash(stash_id)
                    self.assertEqual(content, "")


    def test_interactive_apply_stash_workflow(self):
        """Test the interactive stash application workflow."""
        mock_stashes = [
            {'id': 'stash@{0}', 'name': 'test_stash_1'},
            {'id': 'stash@{1}', 'name': 'test_stash_2'}
        ]
        
        with patch.object(self.stash_manager, 'list_stashes_with_metadata', return_value=mock_stashes):
            with patch.object(self.stash_manager, 'get_choice') as mock_choice:
                with patch.object(self.stash_manager, 'apply_stash', return_value=True) as mock_apply:
                    with patch('builtins.input'):  # Mock final input
                        # Mock user selections
                        mock_choice.side_effect = [
                            'test_stash_1 (stash@{0})',  # Select stash
                            'Apply (keep stash)'  # Select apply method
                        ]
                        
                        self.stash_manager.apply_stash_interactive()
                        
                        # Verify apply_stash was called with correct parameters
                        mock_apply.assert_called_once_with('stash@{0}', True)
    
    def test_interactive_apply_stash_pop_workflow(self):
        """Test the interactive stash pop workflow."""
        mock_stashes = [
            {'id': 'stash@{0}', 'name': 'test_stash_1'}
        ]
        
        with patch.object(self.stash_manager, 'list_stashes_with_metadata', return_value=mock_stashes):
            with patch.object(self.stash_manager, 'get_choice') as mock_choice:
                with patch.object(self.stash_manager, 'apply_stash', return_value=True) as mock_apply:
                    with patch('builtins.input'):  # Mock final input
                        # Mock user selections
                        mock_choice.side_effect = [
                            'test_stash_1 (stash@{0})',  # Select stash
                            'Pop (apply and delete)'  # Select pop method
                        ]
                        
                        self.stash_manager.apply_stash_interactive()
                        
                        # Verify apply_stash was called with correct parameters (keep=False for pop)
                        mock_apply.assert_called_once_with('stash@{0}', False)
    
    def test_interactive_delete_stash_workflow(self):
        """Test the interactive stash deletion workflow."""
        mock_stashes = [
            {'id': 'stash@{0}', 'name': 'test_stash_1'}
        ]
        
        with patch.object(self.stash_manager, 'list_stashes_with_metadata', return_value=mock_stashes):
            with patch.object(self.stash_manager, 'get_choice', return_value='test_stash_1 (stash@{0})'):
                with patch.object(self.stash_manager, 'confirm', return_value=True):
                    with patch.object(self.stash_manager, 'delete_stash', return_value=True) as mock_delete:
                        with patch('builtins.input'):  # Mock final input
                            self.stash_manager.delete_stash_interactive()
                            
                            # Verify delete_stash was called
                            mock_delete.assert_called_once_with('stash@{0}')
    
    def test_interactive_delete_stash_cancelled(self):
        """Test the interactive stash deletion when user cancels."""
        mock_stashes = [
            {'id': 'stash@{0}', 'name': 'test_stash_1'}
        ]
        
        with patch.object(self.stash_manager, 'list_stashes_with_metadata', return_value=mock_stashes):
            with patch.object(self.stash_manager, 'get_choice', return_value='test_stash_1 (stash@{0})'):
                with patch.object(self.stash_manager, 'confirm', return_value=False):
                    with patch.object(self.stash_manager, 'delete_stash') as mock_delete:
                        self.stash_manager.delete_stash_interactive()
                        
                        # Verify delete_stash was NOT called
                        mock_delete.assert_not_called()
    
    def test_interactive_menu_workflow(self):
        """Test the main interactive menu workflow."""
        with patch.object(self.stash_manager, 'show_feature_header'):
            with patch.object(self.stash_manager, 'is_git_repo', return_value=True):
                with patch.object(self.stash_manager, '_cleanup_stale_metadata'):
                    with patch.object(self.stash_manager, 'list_stashes_with_metadata', return_value=[]):
                        with patch.object(self.stash_manager, 'get_choice', return_value='Back to main menu'):
                            # This should exit the loop
                            self.stash_manager.interactive_menu()
    
    def test_apply_stash_with_metadata_cleanup(self):
        """Test that metadata is properly cleaned up when popping stashes."""
        stash_id = 'stash@{0}'
        
        # Add metadata
        test_metadata = {stash_id: {'name': 'test_stash', 'description': 'test'}}
        self.stash_manager._save_metadata(test_metadata)
        
        with patch.object(self.stash_manager, 'run_git_command', return_value=True):
            # Test pop (should remove metadata)
            result = self.stash_manager.apply_stash(stash_id, keep=False)
            self.assertTrue(result)
            
            # Verify metadata was removed
            metadata = self.stash_manager._load_metadata()
            self.assertNotIn(stash_id, metadata)
    
    def test_delete_stash_with_confirmation_disabled(self):
        """Test stash deletion with confirmation disabled."""
        stash_id = 'stash@{0}'
        
        # Disable confirmation
        self.stash_manager.set_feature_config('confirm_deletions', False)
        
        mock_stashes = [
            {'id': stash_id, 'name': 'test_stash_1'}
        ]
        
        with patch.object(self.stash_manager, 'list_stashes_with_metadata', return_value=mock_stashes):
            with patch.object(self.stash_manager, 'get_choice', return_value='test_stash_1 (stash@{0})'):
                with patch.object(self.stash_manager, 'delete_stash', return_value=True) as mock_delete:
                    with patch('builtins.input'):  # Mock final input
                        self.stash_manager.delete_stash_interactive()
                        
                        # Verify delete_stash was called without confirmation
                        mock_delete.assert_called_once_with(stash_id)
    
    def test_stash_operations_error_handling(self):
        """Test error handling in stash operations."""
        stash_id = 'stash@{0}'
        
        # Test apply stash error
        with patch.object(self.stash_manager, 'run_git_command', side_effect=Exception("Git error")):
            result = self.stash_manager.apply_stash(stash_id)
            self.assertFalse(result)
        
        # Test delete stash error
        with patch.object(self.stash_manager, 'run_git_command', side_effect=Exception("Git error")):
            result = self.stash_manager.delete_stash(stash_id)
            self.assertFalse(result)
    
    def test_interactive_operations_with_no_stashes(self):
        """Test interactive operations when no stashes exist."""
        with patch.object(self.stash_manager, 'list_stashes_with_metadata', return_value=[]):
            with patch('builtins.input'):  # Mock input for "Press Enter"
                # These should handle empty stash list gracefully
                self.stash_manager.preview_stash_interactive()
                self.stash_manager.apply_stash_interactive()
                self.stash_manager.delete_stash_interactive()


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)