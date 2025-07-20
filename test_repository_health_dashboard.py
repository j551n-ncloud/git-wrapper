#!/usr/bin/env python3
"""
Unit tests for Repository Health Dashboard

Tests the branch analysis functionality including:
- Branch detection and analysis
- Stale branch identification
- Ahead/behind status calculation
- Branch merge status detection
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Add the features directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'features'))

from features.repository_health_dashboard import RepositoryHealthDashboard


class TestRepositoryHealthDashboard(unittest.TestCase):
    """Test cases for Repository Health Dashboard branch analysis functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_git_wrapper = Mock()
        self.mock_git_wrapper.config = {
            'advanced_features': {
                'repositoryhealth': {
                    'stale_branch_days': 30,
                    'large_file_threshold_mb': 10,
                    'show_remote_branches': True,
                    'max_branches_display': 50
                }
            }
        }
        self.mock_git_wrapper.print_success = Mock()
        self.mock_git_wrapper.print_error = Mock()
        self.mock_git_wrapper.print_info = Mock()
        self.mock_git_wrapper.print_working = Mock()
        self.mock_git_wrapper.save_config = Mock()
        
        self.dashboard = RepositoryHealthDashboard(self.mock_git_wrapper)
    
    def test_init(self):
        """Test dashboard initialization."""
        self.assertEqual(self.dashboard.git_wrapper, self.mock_git_wrapper)
        self.assertEqual(self.dashboard.feature_name, 'repositoryhealth')
        self.assertIsInstance(self.dashboard.health_cache, dict)
        self.assertEqual(self.dashboard.cache_timeout, 300)
    
    def test_get_default_config(self):
        """Test default configuration values."""
        config = self.dashboard._get_default_config()
        
        self.assertEqual(config['stale_branch_days'], 30)
        self.assertEqual(config['large_file_threshold_mb'], 10)
        self.assertTrue(config['auto_refresh'])
        self.assertTrue(config['show_remote_branches'])
        self.assertEqual(config['max_branches_display'], 50)
        self.assertIn('health_score_weights', config)
    
    @patch('subprocess.run')
    def test_get_local_branches(self, mock_run):
        """Test getting local branches."""
        # Mock successful git branch command
        mock_result = Mock()
        mock_result.stdout = "main\nfeature/test\ndevelop\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        with patch.object(self.dashboard, 'run_git_command') as mock_git_cmd:
            mock_git_cmd.return_value = "main\nfeature/test\ndevelop"
            
            branches = self.dashboard._get_local_branches()
            
            self.assertEqual(len(branches), 3)
            self.assertIn('main', branches)
            self.assertIn('feature/test', branches)
            self.assertIn('develop', branches)
            mock_git_cmd.assert_called_once_with(['git', 'branch', '--format=%(refname:short)'], capture_output=True)
    
    @patch('subprocess.run')
    def test_get_remote_branches(self, mock_run):
        """Test getting remote branches."""
        with patch.object(self.dashboard, 'run_git_command') as mock_git_cmd:
            mock_git_cmd.return_value = "origin/main\norigin/feature/test\norigin/HEAD"
            
            branches = self.dashboard._get_remote_branches()
            
            # Should exclude HEAD references
            self.assertEqual(len(branches), 2)
            self.assertIn('origin/main', branches)
            self.assertIn('origin/feature/test', branches)
            self.assertNotIn('origin/HEAD', branches)
    
    def test_get_branch_last_commit(self):
        """Test getting last commit information for a branch."""
        commit_hash = "abc123def456"
        commit_date = "2024-01-15T10:30:00Z"
        commit_message = "Add new feature"
        commit_author = "Test User"
        
        with patch.object(self.dashboard, 'run_git_command') as mock_git_cmd:
            mock_git_cmd.return_value = f"{commit_hash}|{commit_date}|{commit_message}|{commit_author}"
            
            result = self.dashboard._get_branch_last_commit('feature/test')
            
            self.assertIsNotNone(result)
            self.assertEqual(result['last_commit_hash'], commit_hash)
            self.assertEqual(result['last_commit_date'], commit_date)
            self.assertEqual(result['last_commit_message'], commit_message)
            self.assertEqual(result['author'], commit_author)
    
    def test_get_branch_last_commit_no_result(self):
        """Test getting last commit when no result is returned."""
        with patch.object(self.dashboard, 'run_git_command') as mock_git_cmd:
            mock_git_cmd.return_value = ""
            
            result = self.dashboard._get_branch_last_commit('nonexistent')
            
            self.assertIsNone(result)
    
    def test_get_ahead_behind_status(self):
        """Test getting ahead/behind status for a branch."""
        with patch.object(self.dashboard, 'run_git_command') as mock_git_cmd:
            # Mock upstream branch detection
            mock_git_cmd.side_effect = [
                "origin/main",  # upstream branch
                "5\t3"  # ahead/behind counts
            ]
            
            result = self.dashboard._get_ahead_behind_status('feature/test')
            
            self.assertIsNotNone(result)
            self.assertEqual(result['ahead'], 5)
            self.assertEqual(result['behind'], 3)
            self.assertEqual(result['upstream'], "origin/main")
    
    def test_get_ahead_behind_status_no_upstream(self):
        """Test ahead/behind status when no upstream is configured."""
        with patch.object(self.dashboard, 'run_git_command') as mock_git_cmd:
            with patch.object(self.dashboard, 'get_remotes') as mock_remotes:
                # No upstream, but has origin remote
                mock_git_cmd.side_effect = [
                    "",  # no upstream
                    "origin/main",  # verify origin/main exists
                    "2\t1"  # ahead/behind counts
                ]
                mock_remotes.return_value = ['origin']
                
                result = self.dashboard._get_ahead_behind_status('feature/test')
                
                self.assertIsNotNone(result)
                self.assertEqual(result['ahead'], 2)
                self.assertEqual(result['behind'], 1)
    
    def test_is_branch_stale(self):
        """Test stale branch detection."""
        # Create a date 45 days ago
        old_date = datetime.now() - timedelta(days=45)
        old_date_iso = old_date.isoformat() + "Z"
        
        with patch.object(self.dashboard, '_get_branch_last_commit') as mock_commit:
            mock_commit.return_value = {
                'last_commit_date': old_date_iso
            }
            
            # Branch is stale (45 days > 30 days threshold)
            self.assertTrue(self.dashboard._is_branch_stale('old-branch', 30))
            
            # Branch is not stale with higher threshold
            self.assertFalse(self.dashboard._is_branch_stale('old-branch', 60))
    
    def test_is_branch_stale_recent(self):
        """Test stale branch detection with recent branch."""
        # Create a date 10 days ago
        recent_date = datetime.now() - timedelta(days=10)
        recent_date_iso = recent_date.isoformat() + "Z"
        
        with patch.object(self.dashboard, '_get_branch_last_commit') as mock_commit:
            mock_commit.return_value = {
                'last_commit_date': recent_date_iso
            }
            
            # Branch is not stale (10 days < 30 days threshold)
            self.assertFalse(self.dashboard._is_branch_stale('recent-branch', 30))
    
    def test_is_branch_merged(self):
        """Test branch merge status detection."""
        with patch.object(self.dashboard, 'run_git_command') as mock_git_cmd:
            # Mock main branch exists and branch is merged
            mock_git_cmd.side_effect = [
                "main",  # main branch exists
                True  # merge-base command succeeds (branch is ancestor)
            ]
            
            self.assertTrue(self.dashboard._is_branch_merged('feature/merged'))
    
    def test_is_branch_not_merged(self):
        """Test detection of unmerged branch."""
        with patch.object(self.dashboard, 'run_git_command') as mock_git_cmd:
            # Mock main branch exists but branch is not merged
            mock_git_cmd.side_effect = [
                "main",  # main branch exists
                False  # merge-base command fails (branch is not ancestor)
            ]
            
            self.assertFalse(self.dashboard._is_branch_merged('feature/unmerged'))
    
    def test_analyze_single_branch(self):
        """Test analyzing a single branch."""
        branch_name = "feature/test"
        commit_date = "2024-01-15T10:30:00Z"
        
        with patch.object(self.dashboard, '_get_branch_last_commit') as mock_commit:
            with patch.object(self.dashboard, '_get_ahead_behind_status') as mock_ahead_behind:
                mock_commit.return_value = {
                    'last_commit_hash': 'abc123',
                    'last_commit_date': commit_date,
                    'last_commit_message': 'Test commit',
                    'author': 'Test User'
                }
                mock_ahead_behind.return_value = {
                    'ahead': 2,
                    'behind': 1,
                    'upstream': 'origin/main'
                }
                
                result = self.dashboard._analyze_single_branch(branch_name)
                
                self.assertEqual(result['name'], branch_name)
                self.assertFalse(result['is_remote'])
                self.assertTrue(result['exists'])
                self.assertEqual(result['last_commit_hash'], 'abc123')
                self.assertEqual(result['last_commit_date'], commit_date)
                self.assertEqual(result['ahead'], 2)
                self.assertEqual(result['behind'], 1)
                self.assertGreater(result['days_old'], 0)  # Should calculate days
    
    def test_analyze_single_remote_branch(self):
        """Test analyzing a remote branch."""
        branch_name = "origin/feature/test"
        
        with patch.object(self.dashboard, '_get_branch_last_commit') as mock_commit:
            mock_commit.return_value = {
                'last_commit_hash': 'def456',
                'last_commit_date': '2024-01-20T15:45:00Z',
                'last_commit_message': 'Remote commit',
                'author': 'Remote User'
            }
            
            result = self.dashboard._analyze_single_branch(branch_name, is_remote=True)
            
            self.assertEqual(result['name'], branch_name)
            self.assertTrue(result['is_remote'])
            self.assertTrue(result['exists'])
            self.assertEqual(result['last_commit_hash'], 'def456')
            # Remote branches don't get ahead/behind analysis
            self.assertEqual(result['ahead'], 0)
            self.assertEqual(result['behind'], 0)
    
    def test_analyze_branches_integration(self):
        """Test the complete branch analysis integration."""
        with patch.object(self.dashboard, '_get_local_branches') as mock_local:
            with patch.object(self.dashboard, '_get_remote_branches') as mock_remote:
                with patch.object(self.dashboard, 'get_current_branch') as mock_current:
                    with patch.object(self.dashboard, '_analyze_single_branch') as mock_analyze:
                        with patch.object(self.dashboard, '_is_branch_stale') as mock_stale:
                            with patch.object(self.dashboard, '_is_branch_merged') as mock_merged:
                                # Setup mocks
                                mock_local.return_value = ['main', 'feature/test', 'old-branch']
                                mock_remote.return_value = ['origin/main', 'origin/develop']
                                mock_current.return_value = 'main'
                                
                                # Mock branch analysis results
                                def analyze_side_effect(branch, is_remote=False):
                                    return {
                                        'name': branch,
                                        'is_remote': is_remote,
                                        'exists': True,
                                        'last_commit_date': '2024-01-15T10:30:00Z',
                                        'days_old': 35 if branch == 'old-branch' else 5,
                                        'ahead': 2 if branch == 'feature/test' else 0,
                                        'behind': 1 if branch == 'feature/test' else 0
                                    }
                                
                                mock_analyze.side_effect = analyze_side_effect
                                mock_stale.side_effect = lambda branch, days: branch == 'old-branch'
                                mock_merged.side_effect = lambda branch: branch != 'feature/test'
                                
                                result = self.dashboard.analyze_branches()
                                
                                # Verify results
                                self.assertIn('local_branches', result)
                                self.assertIn('remote_branches', result)
                                self.assertIn('stale_branches', result)
                                self.assertIn('unmerged_branches', result)
                                self.assertIn('summary', result)
                                
                                # Check summary
                                summary = result['summary']
                                self.assertEqual(summary['total_local'], 3)
                                self.assertEqual(summary['total_remote'], 2)
                                self.assertEqual(summary['stale_count'], 1)
                                self.assertEqual(summary['unmerged_count'], 1)
                                
                                # Check stale branches
                                stale_branches = result['stale_branches']
                                self.assertEqual(len(stale_branches), 1)
                                self.assertEqual(stale_branches[0]['name'], 'old-branch')
                                
                                # Check unmerged branches
                                unmerged_branches = result['unmerged_branches']
                                self.assertEqual(len(unmerged_branches), 1)
                                self.assertEqual(unmerged_branches[0]['name'], 'feature/test')


    def test_get_repository_stats(self):
        """Test getting repository statistics."""
        with patch.object(self.dashboard, '_get_repository_size') as mock_size:
            with patch.object(self.dashboard, '_get_commit_count') as mock_commits:
                with patch.object(self.dashboard, '_get_contributor_count') as mock_contributors:
                    with patch.object(self.dashboard, '_get_top_contributors') as mock_top_contributors:
                        with patch.object(self.dashboard, '_get_file_count') as mock_files:
                            with patch.object(self.dashboard, '_get_line_count') as mock_lines:
                                with patch.object(self.dashboard, '_get_language_stats') as mock_languages:
                                    with patch.object(self.dashboard, '_get_repository_age') as mock_age:
                                        with patch.object(self.dashboard, '_get_last_commit_date') as mock_last_commit:
                                            with patch.object(self.dashboard, '_get_tags_count') as mock_tags:
                                                with patch.object(self.dashboard, 'get_remotes') as mock_remotes:
                                                    # Setup mocks
                                                    mock_size.return_value = {'total_mb': 50.5, 'git_db_mb': 20.2, 'working_tree_mb': 30.3}
                                                    mock_commits.return_value = 150
                                                    mock_contributors.return_value = 5
                                                    mock_top_contributors.return_value = [{'name': 'User1', 'commits': 50}]
                                                    mock_files.return_value = {'tracked': 100, 'total': 120, 'untracked': 20}
                                                    mock_lines.return_value = {'total_lines': 5000, 'code_lines': 3000, 'blank_lines': 1000, 'comment_lines': 1000}
                                                    mock_languages.return_value = {'Python': 50, 'JavaScript': 30}
                                                    mock_age.return_value = 365
                                                    mock_last_commit.return_value = '2024-01-15T10:30:00Z'
                                                    mock_tags.return_value = 10
                                                    mock_remotes.return_value = ['origin', 'upstream']
                                                    
                                                    stats = self.dashboard.get_repository_stats()
                                                    
                                                    # Verify all statistics are included
                                                    self.assertIn('repository_size', stats)
                                                    self.assertIn('commit_count', stats)
                                                    self.assertIn('contributor_count', stats)
                                                    self.assertIn('contributors', stats)
                                                    self.assertIn('file_count', stats)
                                                    self.assertIn('line_count', stats)
                                                    self.assertIn('languages', stats)
                                                    self.assertIn('age_days', stats)
                                                    self.assertIn('last_commit_date', stats)
                                                    self.assertIn('tags_count', stats)
                                                    self.assertIn('remotes_count', stats)
                                                    
                                                    # Verify values
                                                    self.assertEqual(stats['commit_count'], 150)
                                                    self.assertEqual(stats['contributor_count'], 5)
                                                    self.assertEqual(stats['age_days'], 365)
                                                    self.assertEqual(stats['tags_count'], 10)
                                                    self.assertEqual(stats['remotes_count'], 2)
    
    def test_get_commit_count(self):
        """Test getting commit count."""
        with patch.object(self.dashboard, 'run_git_command') as mock_git_cmd:
            mock_git_cmd.return_value = "150"
            
            count = self.dashboard._get_commit_count()
            
            self.assertEqual(count, 150)
            mock_git_cmd.assert_called_once_with(['git', 'rev-list', '--all', '--count'], capture_output=True)
    
    def test_get_contributor_count(self):
        """Test getting contributor count."""
        with patch.object(self.dashboard, 'run_git_command') as mock_git_cmd:
            mock_git_cmd.return_value = "    50\tJohn Doe\n    30\tJane Smith\n    20\tBob Wilson"
            
            count = self.dashboard._get_contributor_count()
            
            self.assertEqual(count, 3)
    
    def test_get_top_contributors(self):
        """Test getting top contributors."""
        with patch.object(self.dashboard, 'run_git_command') as mock_git_cmd:
            mock_git_cmd.return_value = "    50\tJohn Doe\n    30\tJane Smith\n    20\tBob Wilson"
            
            contributors = self.dashboard._get_top_contributors(limit=2)
            
            self.assertEqual(len(contributors), 2)
            self.assertEqual(contributors[0]['name'], 'John Doe')
            self.assertEqual(contributors[0]['commits'], 50)
            self.assertEqual(contributors[1]['name'], 'Jane Smith')
            self.assertEqual(contributors[1]['commits'], 30)
    
    def test_get_file_count(self):
        """Test getting file count statistics."""
        with patch.object(self.dashboard, 'run_git_command') as mock_git_cmd:
            with patch.object(self.dashboard, 'get_git_root') as mock_root:
                # Mock tracked files
                mock_git_cmd.return_value = "file1.py\nfile2.js\nfile3.md"
                
                # Mock git root and file system
                mock_root_path = Mock()
                
                # Create mock file objects
                file1 = Mock()
                file1.is_file.return_value = True
                file2 = Mock()
                file2.is_file.return_value = True
                file3 = Mock()
                file3.is_file.return_value = True
                untracked = Mock()
                untracked.is_file.return_value = True
                
                mock_root_path.rglob.return_value = [file1, file2, file3, untracked]
                mock_root.return_value = mock_root_path
                
                result = self.dashboard._get_file_count()
                
                self.assertEqual(result['tracked'], 3)
                self.assertEqual(result['total'], 4)
                self.assertEqual(result['untracked'], 1)
    
    def test_extension_to_language(self):
        """Test file extension to language mapping."""
        self.assertEqual(self.dashboard._extension_to_language('.py'), 'Python')
        self.assertEqual(self.dashboard._extension_to_language('.js'), 'JavaScript')
        self.assertEqual(self.dashboard._extension_to_language('.java'), 'Java')
        self.assertEqual(self.dashboard._extension_to_language('.unknown'), None)
    
    def test_get_language_stats(self):
        """Test getting programming language statistics."""
        with patch.object(self.dashboard, 'run_git_command') as mock_git_cmd:
            with patch.object(self.dashboard, 'get_git_root') as mock_root:
                mock_git_cmd.return_value = "file1.py\nfile2.py\nfile3.js\nREADME.md"
                mock_root.return_value = Mock()  # Just need it to exist
                
                result = self.dashboard._get_language_stats()
                
                self.assertEqual(result.get('Python'), 2)
                self.assertEqual(result.get('JavaScript'), 1)
                self.assertEqual(result.get('Markdown'), 1)
    
    def test_get_repository_age(self):
        """Test getting repository age."""
        # Mock first commit date (30 days ago)
        past_date = datetime.now() - timedelta(days=30)
        past_date_iso = past_date.isoformat() + "Z"
        
        with patch.object(self.dashboard, 'run_git_command') as mock_git_cmd:
            mock_git_cmd.return_value = past_date_iso
            
            age = self.dashboard._get_repository_age()
            
            # Should be approximately 30 days (allow some variance for test execution time)
            self.assertGreaterEqual(age, 29)
            self.assertLessEqual(age, 31)
    
    def test_find_large_files_basic(self):
        """Test basic large files functionality."""
        # Test with empty result
        with patch.object(self.dashboard, 'run_git_command') as mock_git_cmd:
            mock_git_cmd.return_value = ""
            large_files = self.dashboard.find_large_files(threshold_mb=10)
            self.assertEqual(len(large_files), 0)
        
        # Test with no git root
        with patch.object(self.dashboard, 'get_git_root') as mock_root:
            mock_root.return_value = None
            large_files = self.dashboard.find_large_files(threshold_mb=10)
            self.assertEqual(len(large_files), 0)
    
    def test_calculate_health_score(self):
        """Test calculating repository health score."""
        with patch.object(self.dashboard, 'analyze_branches') as mock_branches:
            with patch.object(self.dashboard, 'get_repository_stats') as mock_stats:
                with patch.object(self.dashboard, 'find_large_files') as mock_large_files:
                    with patch.object(self.dashboard, 'get_feature_config') as mock_config:
                        # Mock configuration
                        mock_config.return_value = {
                            'stale_branches': 0.3,
                            'large_files': 0.2,
                            'unmerged_branches': 0.3,
                            'repository_size': 0.2
                        }
                        
                        # Mock data for scoring
                        mock_branches.return_value = {
                            'summary': {
                                'total_local': 10,
                                'stale_count': 2,
                                'unmerged_count': 3
                            }
                        }
                        mock_stats.return_value = {
                            'repository_size': {'total_mb': 25.0}
                        }
                        mock_large_files.return_value = [
                            {'size_mb': 15.0},
                            {'size_mb': 12.0}
                        ]
                        
                        health_score = self.dashboard.calculate_health_score()
                        
                        self.assertIn('overall_score', health_score)
                        self.assertIn('individual_scores', health_score)
                        self.assertIn('grade', health_score)
                        self.assertIn('recommendations', health_score)
                        
                        # Score should be between 0 and 100
                        self.assertGreaterEqual(health_score['overall_score'], 0)
                        self.assertLessEqual(health_score['overall_score'], 100)
                        
                        # Should have individual scores for each metric
                        individual = health_score['individual_scores']
                        self.assertIn('stale_branches', individual)
                        self.assertIn('large_files', individual)
                        self.assertIn('unmerged_branches', individual)
                        self.assertIn('repository_size', individual)
    
    def test_score_to_grade(self):
        """Test converting numeric score to letter grade."""
        self.assertEqual(self.dashboard._score_to_grade(95), 'A')
        self.assertEqual(self.dashboard._score_to_grade(85), 'B')
        self.assertEqual(self.dashboard._score_to_grade(75), 'C')
        self.assertEqual(self.dashboard._score_to_grade(65), 'D')
        self.assertEqual(self.dashboard._score_to_grade(55), 'F')
    
    def test_score_stale_branches(self):
        """Test scoring based on stale branches."""
        # No stale branches - perfect score
        analysis = {'summary': {'total_local': 10, 'stale_count': 0}}
        score = self.dashboard._score_stale_branches(analysis)
        self.assertEqual(score, 100.0)
        
        # Half branches are stale - 50% score
        analysis = {'summary': {'total_local': 10, 'stale_count': 5}}
        score = self.dashboard._score_stale_branches(analysis)
        self.assertEqual(score, 50.0)
        
        # All branches are stale - 0% score
        analysis = {'summary': {'total_local': 10, 'stale_count': 10}}
        score = self.dashboard._score_stale_branches(analysis)
        self.assertEqual(score, 0.0)
    
    def test_score_large_files(self):
        """Test scoring based on large files."""
        # No large files - perfect score
        score = self.dashboard._score_large_files([])
        self.assertEqual(score, 100.0)
        
        # Some large files - reduced score
        large_files = [
            {'size_mb': 20.0},
            {'size_mb': 15.0},
            {'size_mb': 10.0}
        ]
        score = self.dashboard._score_large_files(large_files)
        self.assertLess(score, 100.0)
        self.assertGreaterEqual(score, 0.0)


    def test_generate_cleanup_recommendations(self):
        """Test generating cleanup recommendations."""
        with patch.object(self.dashboard, 'analyze_branches') as mock_branches:
            with patch.object(self.dashboard, 'get_repository_stats') as mock_stats:
                with patch.object(self.dashboard, 'find_large_files') as mock_large_files:
                    # Mock data that should generate recommendations
                    mock_branches.return_value = {
                        'stale_branches': [
                            {'name': 'old-feature', 'days_old': 45},
                            {'name': 'abandoned-branch', 'days_old': 60}
                        ],
                        'unmerged_branches': [
                            {'name': 'feature/new', 'ahead': 5, 'behind': 0}
                        ]
                    }
                    mock_stats.return_value = {
                        'repository_size': {'total_mb': 600.0, 'git_db_mb': 150.0}
                    }
                    mock_large_files.return_value = [
                        {'path': 'large_file.bin', 'size_mb': 25.0},
                        {'path': 'huge_file.zip', 'size_mb': 50.0}
                    ]
                    
                    recommendations = self.dashboard.generate_cleanup_recommendations()
                    
                    # Should generate multiple recommendations
                    self.assertGreater(len(recommendations), 0)
                    
                    # Check recommendation structure
                    for rec in recommendations:
                        self.assertIn('type', rec)
                        self.assertIn('priority', rec)
                        self.assertIn('title', rec)
                        self.assertIn('description', rec)
                        self.assertIn('impact', rec)
                        self.assertIn(rec['priority'], ['high', 'medium', 'low'])
                    
                    # Should be sorted by priority (high first)
                    priorities = [rec['priority'] for rec in recommendations]
                    priority_values = {'high': 0, 'medium': 1, 'low': 2}
                    priority_nums = [priority_values[p] for p in priorities]
                    self.assertEqual(priority_nums, sorted(priority_nums))
    
    def test_generate_cleanup_recommendations_empty(self):
        """Test cleanup recommendations with healthy repository."""
        with patch.object(self.dashboard, 'analyze_branches') as mock_branches:
            with patch.object(self.dashboard, 'get_repository_stats') as mock_stats:
                with patch.object(self.dashboard, 'find_large_files') as mock_large_files:
                    # Mock healthy repository data
                    mock_branches.return_value = {
                        'stale_branches': [],
                        'unmerged_branches': []
                    }
                    mock_stats.return_value = {
                        'repository_size': {'total_mb': 25.0, 'git_db_mb': 10.0}
                    }
                    mock_large_files.return_value = []
                    
                    recommendations = self.dashboard.generate_cleanup_recommendations()
                    
                    # Should generate no recommendations for healthy repo
                    self.assertEqual(len(recommendations), 0)
    
    def test_export_json_report(self):
        """Test exporting health report in JSON format."""
        test_data = {
            'generated_at': '2024-01-15T10:30:00',
            'repository_path': '/test/repo',
            'health_score': {'overall_score': 85.5, 'grade': 'B'},
            'branch_analysis': {'summary': {'total_local': 5}},
            'repository_statistics': {'commit_count': 100},
            'large_files': [],
            'cleanup_recommendations': []
        }
        
        json_report = self.dashboard._export_json_report(test_data)
        
        # Should be valid JSON
        import json
        parsed_data = json.loads(json_report)
        
        # Should contain all expected fields
        self.assertEqual(parsed_data['generated_at'], '2024-01-15T10:30:00')
        self.assertEqual(parsed_data['health_score']['overall_score'], 85.5)
        self.assertEqual(parsed_data['repository_statistics']['commit_count'], 100)
    
    def test_export_text_report(self):
        """Test exporting health report in text format."""
        test_data = {
            'generated_at': '2024-01-15T10:30:00',
            'repository_path': '/test/repo',
            'health_score': {
                'overall_score': 85.5,
                'grade': 'B',
                'individual_scores': {
                    'stale_branches': 90.0,
                    'large_files': 80.0
                }
            },
            'repository_statistics': {
                'commit_count': 100,
                'contributor_count': 5,
                'repository_size': {'total_mb': 50.0, 'git_db_mb': 20.0, 'working_tree_mb': 30.0}
            },
            'branch_analysis': {
                'summary': {'total_local': 5, 'total_remote': 3, 'stale_count': 1, 'unmerged_count': 2}
            },
            'large_files': [
                {'path': 'large_file.bin', 'size_mb': 25.0}
            ],
            'cleanup_recommendations': [
                {
                    'title': 'Clean up stale branches',
                    'description': 'Found old branches',
                    'priority': 'medium',
                    'impact': 'Improves organization',
                    'commands': ['git branch -d old-branch']
                }
            ]
        }
        
        text_report = self.dashboard._export_text_report(test_data)
        
        # Should contain expected sections
        self.assertIn('REPOSITORY HEALTH REPORT', text_report)
        self.assertIn('OVERALL HEALTH SCORE', text_report)
        self.assertIn('Score: 85.5/100 (Grade: B)', text_report)
        self.assertIn('REPOSITORY STATISTICS', text_report)
        self.assertIn('Repository Size: 50.0 MB', text_report)
        self.assertIn('Total Commits: 100', text_report)
        self.assertIn('BRANCH ANALYSIS', text_report)
        self.assertIn('Local Branches: 5', text_report)
        self.assertIn('LARGE FILES', text_report)
        self.assertIn('large_file.bin (25.0 MB)', text_report)
        self.assertIn('CLEANUP RECOMMENDATIONS', text_report)
        self.assertIn('Clean up stale branches', text_report)
    
    def test_export_health_report_json(self):
        """Test full health report export in JSON format."""
        with patch.object(self.dashboard, 'analyze_branches') as mock_branches:
            with patch.object(self.dashboard, 'get_repository_stats') as mock_stats:
                with patch.object(self.dashboard, 'find_large_files') as mock_large_files:
                    with patch.object(self.dashboard, 'calculate_health_score') as mock_health:
                        with patch.object(self.dashboard, 'generate_cleanup_recommendations') as mock_recommendations:
                            with patch.object(self.dashboard, 'get_git_root') as mock_root:
                                # Setup mocks
                                mock_branches.return_value = {'summary': {'total_local': 5}}
                                mock_stats.return_value = {'commit_count': 100}
                                mock_large_files.return_value = []
                                mock_health.return_value = {'overall_score': 85.0, 'grade': 'B'}
                                mock_recommendations.return_value = []
                                mock_root.return_value = Path('/test/repo')
                                
                                # Export without saving to file
                                report_content = self.dashboard.export_health_report('json')
                                
                                self.assertIsNotNone(report_content)
                                
                                # Should be valid JSON
                                import json
                                parsed_data = json.loads(report_content)
                                
                                # Should contain expected sections
                                self.assertIn('generated_at', parsed_data)
                                self.assertIn('repository_path', parsed_data)
                                self.assertIn('health_score', parsed_data)
                                self.assertIn('branch_analysis', parsed_data)
                                self.assertIn('repository_statistics', parsed_data)
    
    def test_export_health_report_text(self):
        """Test full health report export in text format."""
        with patch.object(self.dashboard, 'analyze_branches') as mock_branches:
            with patch.object(self.dashboard, 'get_repository_stats') as mock_stats:
                with patch.object(self.dashboard, 'find_large_files') as mock_large_files:
                    with patch.object(self.dashboard, 'calculate_health_score') as mock_health:
                        with patch.object(self.dashboard, 'generate_cleanup_recommendations') as mock_recommendations:
                            with patch.object(self.dashboard, 'get_git_root') as mock_root:
                                # Setup mocks
                                mock_branches.return_value = {'summary': {'total_local': 5}}
                                mock_stats.return_value = {'commit_count': 100}
                                mock_large_files.return_value = []
                                mock_health.return_value = {'overall_score': 85.0, 'grade': 'B'}
                                mock_recommendations.return_value = []
                                mock_root.return_value = Path('/test/repo')
                                
                                # Export without saving to file
                                report_content = self.dashboard.export_health_report('text')
                                
                                self.assertIsNotNone(report_content)
                                self.assertIn('REPOSITORY HEALTH REPORT', report_content)
                                self.assertIn('Score: 85.0/100', report_content)
    
    def test_export_health_report_invalid_format(self):
        """Test health report export with invalid format."""
        report_content = self.dashboard.export_health_report('invalid_format')
        self.assertIsNone(report_content)
    
    def test_export_health_report_with_file(self):
        """Test health report export with file saving."""
        import tempfile
        import os
        
        with patch.object(self.dashboard, 'analyze_branches') as mock_branches:
            with patch.object(self.dashboard, 'get_repository_stats') as mock_stats:
                with patch.object(self.dashboard, 'find_large_files') as mock_large_files:
                    with patch.object(self.dashboard, 'calculate_health_score') as mock_health:
                        with patch.object(self.dashboard, 'generate_cleanup_recommendations') as mock_recommendations:
                            with patch.object(self.dashboard, 'get_git_root') as mock_root:
                                # Setup mocks
                                mock_branches.return_value = {'summary': {'total_local': 5}}
                                mock_stats.return_value = {'commit_count': 100}
                                mock_large_files.return_value = []
                                mock_health.return_value = {'overall_score': 85.0, 'grade': 'B'}
                                mock_recommendations.return_value = []
                                mock_root.return_value = Path('/test/repo')
                                
                                # Create temporary file
                                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
                                    temp_path = temp_file.name
                                
                                try:
                                    # Export with file saving
                                    report_content = self.dashboard.export_health_report('json', temp_path)
                                    
                                    self.assertIsNotNone(report_content)
                                    
                                    # Check file was created and contains content
                                    self.assertTrue(os.path.exists(temp_path))
                                    
                                    with open(temp_path, 'r') as f:
                                        file_content = f.read()
                                    
                                    self.assertEqual(file_content, report_content)
                                    
                                finally:
                                    # Clean up
                                    if os.path.exists(temp_path):
                                        os.unlink(temp_path)

    def test_create_score_bar(self):
        """Test creating visual score bars."""
        # High score (green)
        bar = self.dashboard._create_score_bar(90.0, width=10)
        self.assertIn('[', bar)
        self.assertIn(']', bar)
        self.assertIn('█', bar)
        
        # Medium score (yellow)
        bar = self.dashboard._create_score_bar(70.0, width=10)
        self.assertIn('[', bar)
        self.assertIn(']', bar)
        
        # Low score (red)
        bar = self.dashboard._create_score_bar(40.0, width=10)
        self.assertIn('[', bar)
        self.assertIn(']', bar)
        
        # Zero score
        bar = self.dashboard._create_score_bar(0.0, width=10)
        self.assertIn('[░░░░░░░░░░]', bar)
    
    def test_display_health_score(self):
        """Test displaying health score."""
        health_score = {
            'overall_score': 85.5,
            'grade': 'B',
            'individual_scores': {
                'stale_branches': 90.0,
                'large_files': 80.0,
                'unmerged_branches': 85.0,
                'repository_size': 87.0
            }
        }
        
        # Should not raise any exceptions
        try:
            self.dashboard._display_health_score(health_score)
        except Exception as e:
            self.fail(f"_display_health_score raised an exception: {e}")
    
    def test_display_key_metrics(self):
        """Test displaying key metrics."""
        branch_analysis = {
            'summary': {
                'total_local': 5,
                'stale_count': 2,
                'unmerged_count': 1
            }
        }
        
        stats = {
            'repository_size': {'total_mb': 50.5},
            'commit_count': 150,
            'contributor_count': 5,
            'age_days': 365
        }
        
        large_files = [
            {'size_mb': 15.0},
            {'size_mb': 10.0}
        ]
        
        # Should not raise any exceptions
        try:
            self.dashboard._display_key_metrics(branch_analysis, stats, large_files)
        except Exception as e:
            self.fail(f"_display_key_metrics raised an exception: {e}")
    
    def test_display_quick_recommendations(self):
        """Test displaying quick recommendations."""
        # Test with recommendations
        recommendations = [
            {
                'title': 'Clean up stale branches',
                'priority': 'high'
            },
            {
                'title': 'Review large files',
                'priority': 'medium'
            },
            {
                'title': 'Optimize repository size',
                'priority': 'low'
            },
            {
                'title': 'Additional recommendation',
                'priority': 'medium'
            }
        ]
        
        # Should not raise any exceptions
        try:
            self.dashboard._display_quick_recommendations(recommendations)
        except Exception as e:
            self.fail(f"_display_quick_recommendations raised an exception: {e}")
        
        # Test with no recommendations
        try:
            self.dashboard._display_quick_recommendations([])
        except Exception as e:
            self.fail(f"_display_quick_recommendations with empty list raised an exception: {e}")
    
    def test_refresh_dashboard(self):
        """Test refreshing dashboard data."""
        # Add some data to cache
        self.dashboard.health_cache['test'] = 'data'
        
        # Refresh should clear cache
        self.dashboard._refresh_dashboard()
        
        # Cache should be empty
        self.assertEqual(len(self.dashboard.health_cache), 0)
    
    def test_show_stale_branch_commands(self):
        """Test showing stale branch cleanup commands."""
        stale_branches = [
            {'name': 'old-feature', 'days_old': 45},
            {'name': 'abandoned-branch', 'days_old': 60},
            {'name': 'test-branch', 'days_old': 30}
        ]
        
        # Should not raise any exceptions
        try:
            self.dashboard._show_stale_branch_commands(stale_branches)
        except Exception as e:
            self.fail(f"_show_stale_branch_commands raised an exception: {e}")
    
    def test_show_unmerged_branch_commands(self):
        """Test showing unmerged branch commands."""
        unmerged_branches = [
            {'name': 'feature/new', 'ahead': 5, 'behind': 0},
            {'name': 'feature/update', 'ahead': 2, 'behind': 3},
            {'name': 'hotfix/bug', 'ahead': 1, 'behind': 0}
        ]
        
        # Should not raise any exceptions
        try:
            self.dashboard._show_unmerged_branch_commands(unmerged_branches)
        except Exception as e:
            self.fail(f"_show_unmerged_branch_commands raised an exception: {e}")
    
    def test_show_branch_details(self):
        """Test showing detailed branch analysis."""
        with patch.object(self.dashboard, 'analyze_branches') as mock_analyze:
            mock_analyze.return_value = {
                'summary': {
                    'total_local': 5,
                    'total_remote': 3,
                    'stale_count': 2,
                    'unmerged_count': 1
                },
                'stale_branches': [
                    {'name': 'old-feature', 'days_old': 45}
                ],
                'unmerged_branches': [
                    {'name': 'feature/new', 'ahead': 5, 'behind': 0}
                ]
            }
            
            # Should not raise any exceptions
            try:
                self.dashboard._show_branch_details()
            except Exception as e:
                self.fail(f"_show_branch_details raised an exception: {e}")
    
    def test_show_large_files_details(self):
        """Test showing detailed large files analysis."""
        with patch.object(self.dashboard, 'find_large_files') as mock_find:
            mock_find.return_value = [
                {
                    'path': 'large_file.bin',
                    'size_mb': 25.0,
                    'last_author': 'Test User',
                    'commit_count': 5
                },
                {
                    'path': 'huge_file.zip',
                    'size_mb': 50.0,
                    'last_author': 'Another User',
                    'commit_count': 3
                }
            ]
            
            # Should not raise any exceptions
            try:
                self.dashboard._show_large_files_details()
            except Exception as e:
                self.fail(f"_show_large_files_details raised an exception: {e}")
    
    def test_show_large_files_details_empty(self):
        """Test showing large files details when no large files exist."""
        with patch.object(self.dashboard, 'find_large_files') as mock_find:
            mock_find.return_value = []
            
            # Should not raise any exceptions
            try:
                self.dashboard._show_large_files_details()
            except Exception as e:
                self.fail(f"_show_large_files_details with empty list raised an exception: {e}")
    
    def test_display_dashboard_integration(self):
        """Test the main dashboard display integration."""
        with patch.object(self.dashboard, 'analyze_branches') as mock_branches:
            with patch.object(self.dashboard, 'get_repository_stats') as mock_stats:
                with patch.object(self.dashboard, 'find_large_files') as mock_large_files:
                    with patch.object(self.dashboard, 'calculate_health_score') as mock_health:
                        with patch.object(self.dashboard, 'generate_cleanup_recommendations') as mock_recommendations:
                            # Setup comprehensive mock data
                            mock_branches.return_value = {
                                'summary': {
                                    'total_local': 8,
                                    'total_remote': 5,
                                    'stale_count': 3,
                                    'unmerged_count': 2
                                },
                                'stale_branches': [
                                    {'name': 'old-feature', 'days_old': 45}
                                ],
                                'unmerged_branches': [
                                    {'name': 'feature/new', 'ahead': 5, 'behind': 0}
                                ]
                            }
                            
                            mock_stats.return_value = {
                                'repository_size': {'total_mb': 75.5},
                                'commit_count': 250,
                                'contributor_count': 8,
                                'age_days': 180
                            }
                            
                            mock_large_files.return_value = [
                                {'size_mb': 20.0},
                                {'size_mb': 15.0}
                            ]
                            
                            mock_health.return_value = {
                                'overall_score': 78.5,
                                'grade': 'C',
                                'individual_scores': {
                                    'stale_branches': 70.0,
                                    'large_files': 85.0,
                                    'unmerged_branches': 80.0,
                                    'repository_size': 75.0
                                }
                            }
                            
                            mock_recommendations.return_value = [
                                {
                                    'title': 'Clean up stale branches',
                                    'priority': 'high'
                                },
                                {
                                    'title': 'Review large files',
                                    'priority': 'medium'
                                }
                            ]
                            
                            # Should not raise any exceptions
                            try:
                                self.dashboard._display_dashboard()
                            except Exception as e:
                                self.fail(f"_display_dashboard raised an exception: {e}")
                            
                            # Verify all methods were called
                            mock_branches.assert_called_once()
                            mock_stats.assert_called_once()
                            mock_large_files.assert_called_once()
                            mock_health.assert_called_once()
                            mock_recommendations.assert_called_once()


if __name__ == '__main__':
    unittest.main()