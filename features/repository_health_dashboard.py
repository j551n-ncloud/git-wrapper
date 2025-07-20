#!/usr/bin/env python3
"""
Repository Health Dashboard

This module provides comprehensive repository health analysis including:
- Branch analysis (unmerged, stale, ahead/behind status)
- Repository statistics (size, commits, contributors)
- Large file detection
- Cleanup recommendations
- Health reporting
"""

import subprocess
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from .base_manager import BaseFeatureManager


class RepositoryHealthDashboard(BaseFeatureManager):
    """
    Repository Health Dashboard for analyzing and monitoring Git repository health.
    
    Features:
    - Branch analysis with stale branch detection
    - Repository statistics and metrics
    - Large file identification
    - Cleanup recommendations
    - Health report generation
    """
    
    def __init__(self, git_wrapper):
        """Initialize the Repository Health Dashboard."""
        super().__init__(git_wrapper)
        self.health_cache = {}
        self.cache_timeout = 300  # 5 minutes
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for repository health dashboard."""
        return {
            'stale_branch_days': 30,
            'large_file_threshold_mb': 10,
            'auto_refresh': True,
            'show_remote_branches': True,
            'max_branches_display': 50,
            'health_score_weights': {
                'stale_branches': 0.3,
                'large_files': 0.2,
                'unmerged_branches': 0.3,
                'repository_size': 0.2
            }
        }
    
    def interactive_menu(self) -> None:
        """Display the interactive repository health dashboard menu."""
        if not self.is_git_repo():
            self.print_error("Not in a Git repository!")
            return
        
        while True:
            self.show_feature_header("Repository Health Dashboard")
            
            print(f"{self.format_with_emoji('Dashboard Options:', '📊')}")
            print(f"1. {self.format_with_emoji('Branch Analysis', '🌿')}")
            print(f"2. {self.format_with_emoji('Repository Statistics', '📈')}")
            print(f"3. {self.format_with_emoji('Large Files Analysis', '📁')}")
            print(f"4. {self.format_with_emoji('Cleanup Recommendations', '🧹')}")
            print(f"5. {self.format_with_emoji('Full Health Report', '📋')}")
            print(f"6. {self.format_with_emoji('Export Health Report', '📤')}")
            print(f"7. {self.format_with_emoji('Configure Dashboard', '⚙️')}")
            print(f"8. {self.format_with_emoji('Refresh Analysis', '🔄')}")
            print(f"9. {self.format_with_emoji('Back to Main Menu', '🏠')}")
            
            choice = self.get_input("\nSelect option (1-9): ").strip()
            
            if choice == '1':
                self._show_branch_analysis()
            elif choice == '2':
                self._show_repository_statistics()
            elif choice == '3':
                self._show_large_files_analysis()
            elif choice == '4':
                self._show_cleanup_recommendations()
            elif choice == '5':
                self._show_full_health_report()
            elif choice == '6':
                self._export_health_report()
            elif choice == '7':
                self._configure_dashboard()
            elif choice == '8':
                self._refresh_analysis()
            elif choice == '9':
                break
            else:
                self.print_error("Invalid option. Please try again.")
            
            if choice != '9':
                input("\nPress Enter to continue...")
    
    def analyze_branches(self) -> Dict[str, Any]:
        """
        Analyze all branches for health metrics.
        
        Returns:
            Dictionary containing branch analysis results
        """
        self.print_working("Analyzing branches...")
        
        try:
            # Get all branches
            local_branches = self._get_local_branches()
            remote_branches = self._get_remote_branches() if self.get_feature_config('show_remote_branches') else []
            
            # Analyze each branch
            branch_analysis = {
                'local_branches': {},
                'remote_branches': {},
                'stale_branches': [],
                'unmerged_branches': [],
                'ahead_behind_status': {},
                'summary': {
                    'total_local': len(local_branches),
                    'total_remote': len(remote_branches),
                    'stale_count': 0,
                    'unmerged_count': 0
                }
            }
            
            current_branch = self.get_current_branch()
            stale_days = self.get_feature_config('stale_branch_days')
            
            # Analyze local branches
            for branch in local_branches:
                branch_info = self._analyze_single_branch(branch, is_remote=False)
                branch_analysis['local_branches'][branch] = branch_info
                
                # Check if stale
                if self._is_branch_stale(branch, stale_days):
                    branch_analysis['stale_branches'].append({
                        'name': branch,
                        'type': 'local',
                        'last_commit_date': branch_info.get('last_commit_date'),
                        'days_old': branch_info.get('days_old', 0)
                    })
                    branch_analysis['summary']['stale_count'] += 1
                
                # Check if unmerged (not current branch)
                if branch != current_branch and not self._is_branch_merged(branch):
                    branch_analysis['unmerged_branches'].append({
                        'name': branch,
                        'type': 'local',
                        'ahead': branch_info.get('ahead', 0),
                        'behind': branch_info.get('behind', 0)
                    })
                    branch_analysis['summary']['unmerged_count'] += 1
                
                # Get ahead/behind status
                ahead_behind = self._get_ahead_behind_status(branch)
                if ahead_behind:
                    branch_analysis['ahead_behind_status'][branch] = ahead_behind
            
            # Analyze remote branches if enabled
            if self.get_feature_config('show_remote_branches'):
                for branch in remote_branches[:self.get_feature_config('max_branches_display')]:
                    branch_info = self._analyze_single_branch(branch, is_remote=True)
                    branch_analysis['remote_branches'][branch] = branch_info
            
            return branch_analysis
            
        except Exception as e:
            self.print_error(f"Error analyzing branches: {str(e)}")
            return {}
    
    def _get_local_branches(self) -> List[str]:
        """Get list of local branches."""
        try:
            result = self.run_git_command(['git', 'branch', '--format=%(refname:short)'], capture_output=True)
            if result:
                return [branch.strip() for branch in result.split('\n') if branch.strip()]
            return []
        except Exception:
            return []
    
    def _get_remote_branches(self) -> List[str]:
        """Get list of remote branches."""
        try:
            result = self.run_git_command(['git', 'branch', '-r', '--format=%(refname:short)'], capture_output=True)
            if result:
                branches = []
                for branch in result.split('\n'):
                    branch = branch.strip()
                    if branch and not branch.endswith('/HEAD'):
                        branches.append(branch)
                return branches
            return []
        except Exception:
            return []
    
    def _analyze_single_branch(self, branch_name: str, is_remote: bool = False) -> Dict[str, Any]:
        """
        Analyze a single branch for health metrics.
        
        Args:
            branch_name: Name of the branch to analyze
            is_remote: Whether this is a remote branch
            
        Returns:
            Dictionary containing branch analysis data
        """
        try:
            branch_info = {
                'name': branch_name,
                'is_remote': is_remote,
                'exists': True,
                'last_commit_date': None,
                'last_commit_hash': None,
                'last_commit_message': None,
                'author': None,
                'days_old': 0,
                'ahead': 0,
                'behind': 0
            }
            
            # Get last commit information
            commit_info = self._get_branch_last_commit(branch_name)
            if commit_info:
                branch_info.update(commit_info)
                
                # Calculate days old
                if branch_info['last_commit_date']:
                    try:
                        commit_date = datetime.fromisoformat(branch_info['last_commit_date'].replace('Z', '+00:00'))
                        days_old = (datetime.now(commit_date.tzinfo) - commit_date).days
                        branch_info['days_old'] = days_old
                    except Exception:
                        pass
            
            # Get ahead/behind status for local branches
            if not is_remote:
                ahead_behind = self._get_ahead_behind_status(branch_name)
                if ahead_behind:
                    branch_info['ahead'] = ahead_behind.get('ahead', 0)
                    branch_info['behind'] = ahead_behind.get('behind', 0)
            
            return branch_info
            
        except Exception as e:
            self.print_error(f"Error analyzing branch {branch_name}: {str(e)}")
            return {'name': branch_name, 'exists': False, 'error': str(e)}
    
    def _get_branch_last_commit(self, branch_name: str) -> Optional[Dict[str, str]]:
        """
        Get the last commit information for a branch.
        
        Args:
            branch_name: Name of the branch
            
        Returns:
            Dictionary with commit information or None
        """
        try:
            # Get commit hash, date, message, and author
            cmd = [
                'git', 'log', '-1', '--format=%H|%aI|%s|%an', branch_name
            ]
            result = self.run_git_command(cmd, capture_output=True)
            
            if result:
                parts = result.split('|', 3)
                if len(parts) >= 4:
                    return {
                        'last_commit_hash': parts[0],
                        'last_commit_date': parts[1],
                        'last_commit_message': parts[2],
                        'author': parts[3]
                    }
            
            return None
            
        except Exception:
            return None
    
    def _get_ahead_behind_status(self, branch_name: str) -> Optional[Dict[str, int]]:
        """
        Get ahead/behind status of a branch compared to its upstream.
        
        Args:
            branch_name: Name of the branch
            
        Returns:
            Dictionary with ahead/behind counts or None
        """
        try:
            # First, try to get the upstream branch
            upstream_cmd = ['git', 'rev-parse', '--abbrev-ref', f'{branch_name}@{{upstream}}']
            upstream_result = self.run_git_command(upstream_cmd, capture_output=True)
            
            if not upstream_result:
                # No upstream, try comparing with origin/main or origin/master
                remotes = self.get_remotes()
                if 'origin' in remotes:
                    for main_branch in ['main', 'master']:
                        upstream_result = f'origin/{main_branch}'
                        # Check if this remote branch exists
                        check_cmd = ['git', 'rev-parse', '--verify', upstream_result]
                        if self.run_git_command(check_cmd, capture_output=True):
                            break
                    else:
                        return None
                else:
                    return None
            
            # Get ahead/behind counts
            cmd = ['git', 'rev-list', '--left-right', '--count', f'{branch_name}...{upstream_result}']
            result = self.run_git_command(cmd, capture_output=True)
            
            if result:
                parts = result.split()
                if len(parts) >= 2:
                    return {
                        'ahead': int(parts[0]),
                        'behind': int(parts[1]),
                        'upstream': upstream_result
                    }
            
            return None
            
        except Exception:
            return None
    
    def _is_branch_stale(self, branch_name: str, stale_days: int) -> bool:
        """
        Check if a branch is considered stale.
        
        Args:
            branch_name: Name of the branch
            stale_days: Number of days to consider a branch stale
            
        Returns:
            True if branch is stale, False otherwise
        """
        try:
            commit_info = self._get_branch_last_commit(branch_name)
            if not commit_info or not commit_info.get('last_commit_date'):
                return False
            
            commit_date = datetime.fromisoformat(commit_info['last_commit_date'].replace('Z', '+00:00'))
            days_old = (datetime.now(commit_date.tzinfo) - commit_date).days
            
            return days_old > stale_days
            
        except Exception:
            return False
    
    def _is_branch_merged(self, branch_name: str) -> bool:
        """
        Check if a branch has been merged into the main branch.
        
        Args:
            branch_name: Name of the branch
            
        Returns:
            True if branch is merged, False otherwise
        """
        try:
            # Try to find the main branch
            main_branches = ['main', 'master', 'develop']
            main_branch = None
            
            for branch in main_branches:
                if self.run_git_command(['git', 'rev-parse', '--verify', branch], capture_output=True):
                    main_branch = branch
                    break
            
            if not main_branch:
                return False
            
            # Check if branch is merged into main
            cmd = ['git', 'merge-base', '--is-ancestor', branch_name, main_branch]
            result = self.run_git_command(cmd, capture_output=True)
            
            # If the command succeeds, the branch is an ancestor (merged)
            return result is not False
            
        except Exception:
            return False
    
    def _show_branch_analysis(self) -> None:
        """Display detailed branch analysis."""
        self.show_feature_header("Branch Analysis")
        
        analysis = self.analyze_branches()
        if not analysis:
            self.print_error("Failed to analyze branches")
            return
        
        summary = analysis.get('summary', {})
        
        # Show summary
        print(f"{self.format_with_emoji('Branch Summary:', '📊')}")
        print(f"   Local Branches: {summary.get('total_local', 0)}")
        if self.get_feature_config('show_remote_branches'):
            print(f"   Remote Branches: {summary.get('total_remote', 0)}")
        print(f"   Stale Branches: {summary.get('stale_count', 0)}")
        print(f"   Unmerged Branches: {summary.get('unmerged_count', 0)}")
        print()
        
        # Show stale branches
        if analysis.get('stale_branches'):
            print(f"{self.format_with_emoji('Stale Branches:', '🕰️')}")
            for branch in analysis['stale_branches'][:10]:  # Show top 10
                days_old = branch.get('days_old', 0)
                print(f"   • {branch['name']} ({branch['type']}) - {days_old} days old")
            
            if len(analysis['stale_branches']) > 10:
                print(f"   ... and {len(analysis['stale_branches']) - 10} more")
            print()
        
        # Show unmerged branches
        if analysis.get('unmerged_branches'):
            print(f"{self.format_with_emoji('Unmerged Branches:', '🔀')}")
            for branch in analysis['unmerged_branches'][:10]:  # Show top 10
                ahead = branch.get('ahead', 0)
                behind = branch.get('behind', 0)
                status = f"↑{ahead} ↓{behind}" if ahead or behind else "even"
                print(f"   • {branch['name']} ({branch['type']}) - {status}")
            
            if len(analysis['unmerged_branches']) > 10:
                print(f"   ... and {len(analysis['unmerged_branches']) - 10} more")
            print()
        
        # Show ahead/behind status for current branches
        if analysis.get('ahead_behind_status'):
            print(f"{self.format_with_emoji('Branch Status (vs upstream):', '📈')}")
            for branch, status in list(analysis['ahead_behind_status'].items())[:10]:
                ahead = status.get('ahead', 0)
                behind = status.get('behind', 0)
                upstream = status.get('upstream', 'unknown')
                
                if ahead or behind:
                    status_str = f"↑{ahead} ↓{behind}"
                    print(f"   • {branch} vs {upstream}: {status_str}")
            print()
    
    def get_repository_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive repository statistics.
        
        Returns:
            Dictionary containing repository statistics
        """
        self.print_working("Gathering repository statistics...")
        
        try:
            stats = {
                'repository_size': self._get_repository_size(),
                'commit_count': self._get_commit_count(),
                'contributor_count': self._get_contributor_count(),
                'contributors': self._get_top_contributors(),
                'file_count': self._get_file_count(),
                'line_count': self._get_line_count(),
                'languages': self._get_language_stats(),
                'age_days': self._get_repository_age(),
                'last_commit_date': self._get_last_commit_date(),
                'tags_count': self._get_tags_count(),
                'remotes_count': len(self.get_remotes())
            }
            
            return stats
            
        except Exception as e:
            self.print_error(f"Error gathering repository statistics: {str(e)}")
            return {}
    
    def _get_repository_size(self) -> Dict[str, float]:
        """Get repository size information."""
        try:
            git_root = self.get_git_root()
            if not git_root:
                return {'total_mb': 0, 'git_db_mb': 0, 'working_tree_mb': 0}
            
            # Get .git directory size
            git_dir = git_root / '.git'
            git_size = self._get_directory_size(git_dir) if git_dir.exists() else 0
            
            # Get working tree size (excluding .git)
            working_size = 0
            for item in git_root.iterdir():
                if item.name != '.git':
                    if item.is_file():
                        working_size += item.stat().st_size
                    elif item.is_dir():
                        working_size += self._get_directory_size(item)
            
            total_size = git_size + working_size
            
            return {
                'total_mb': round(total_size / (1024 * 1024), 2),
                'git_db_mb': round(git_size / (1024 * 1024), 2),
                'working_tree_mb': round(working_size / (1024 * 1024), 2)
            }
            
        except Exception:
            return {'total_mb': 0, 'git_db_mb': 0, 'working_tree_mb': 0}
    
    def _get_directory_size(self, directory: Path) -> int:
        """Get total size of a directory recursively."""
        total_size = 0
        try:
            for item in directory.rglob('*'):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            pass
        return total_size
    
    def _get_commit_count(self) -> int:
        """Get total number of commits."""
        try:
            result = self.run_git_command(['git', 'rev-list', '--all', '--count'], capture_output=True)
            return int(result) if result.isdigit() else 0
        except Exception:
            return 0
    
    def _get_contributor_count(self) -> int:
        """Get number of unique contributors."""
        try:
            result = self.run_git_command(['git', 'shortlog', '-sn', '--all'], capture_output=True)
            if result:
                return len(result.strip().split('\n'))
            return 0
        except Exception:
            return 0
    
    def _get_top_contributors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top contributors by commit count."""
        try:
            result = self.run_git_command(['git', 'shortlog', '-sn', '--all'], capture_output=True)
            if not result:
                return []
            
            contributors = []
            for line in result.strip().split('\n')[:limit]:
                parts = line.strip().split('\t', 1)
                if len(parts) == 2:
                    count = int(parts[0])
                    name = parts[1]
                    contributors.append({
                        'name': name,
                        'commits': count
                    })
            
            return contributors
            
        except Exception:
            return []
    
    def _get_file_count(self) -> Dict[str, int]:
        """Get file count statistics."""
        try:
            # Get tracked files
            tracked_result = self.run_git_command(['git', 'ls-files'], capture_output=True)
            tracked_count = len(tracked_result.split('\n')) if tracked_result else 0
            
            # Get total files in working directory
            git_root = self.get_git_root()
            total_count = 0
            if git_root:
                for item in git_root.rglob('*'):
                    if item.is_file() and '.git' not in str(item):
                        total_count += 1
            
            return {
                'tracked': tracked_count,
                'total': total_count,
                'untracked': max(0, total_count - tracked_count)
            }
            
        except Exception:
            return {'tracked': 0, 'total': 0, 'untracked': 0}
    
    def _get_line_count(self) -> Dict[str, int]:
        """Get line count statistics for tracked files."""
        try:
            git_root = self.get_git_root()
            if not git_root:
                return {'total_lines': 0, 'code_lines': 0, 'blank_lines': 0, 'comment_lines': 0}
            
            total_lines = 0
            code_lines = 0
            blank_lines = 0
            comment_lines = 0
            
            # Get list of tracked files
            tracked_files = self.run_git_command(['git', 'ls-files'], capture_output=True)
            if not tracked_files:
                return {'total_lines': 0, 'code_lines': 0, 'blank_lines': 0, 'comment_lines': 0}
            
            for file_path in tracked_files.split('\n')[:100]:  # Limit to first 100 files for performance
                if not file_path.strip():
                    continue
                
                full_path = git_root / file_path.strip()
                if full_path.exists() and full_path.is_file():
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                total_lines += 1
                                line_stripped = line.strip()
                                if not line_stripped:
                                    blank_lines += 1
                                elif line_stripped.startswith(('#', '//', '/*', '*', '--', '%')):
                                    comment_lines += 1
                                else:
                                    code_lines += 1
                    except (OSError, UnicodeDecodeError):
                        continue
            
            return {
                'total_lines': total_lines,
                'code_lines': code_lines,
                'blank_lines': blank_lines,
                'comment_lines': comment_lines
            }
            
        except Exception:
            return {'total_lines': 0, 'code_lines': 0, 'blank_lines': 0, 'comment_lines': 0}
    
    def _get_language_stats(self) -> Dict[str, int]:
        """Get programming language statistics."""
        try:
            git_root = self.get_git_root()
            if not git_root:
                return {}
            
            language_counts = {}
            
            # Get list of tracked files
            tracked_files = self.run_git_command(['git', 'ls-files'], capture_output=True)
            if not tracked_files:
                return {}
            
            for file_path in tracked_files.split('\n'):
                if not file_path.strip():
                    continue
                
                # Get file extension
                extension = Path(file_path.strip()).suffix.lower()
                if extension:
                    # Map extensions to languages
                    language = self._extension_to_language(extension)
                    if language:
                        language_counts[language] = language_counts.get(language, 0) + 1
            
            return dict(sorted(language_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            
        except Exception:
            return {}
    
    def _extension_to_language(self, extension: str) -> Optional[str]:
        """Map file extension to programming language."""
        extension_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.go': 'Go',
            '.rs': 'Rust',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.less': 'LESS',
            '.json': 'JSON',
            '.xml': 'XML',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.md': 'Markdown',
            '.sh': 'Shell',
            '.bash': 'Bash',
            '.zsh': 'Zsh',
            '.sql': 'SQL',
            '.r': 'R',
            '.m': 'Objective-C',
            '.pl': 'Perl',
            '.lua': 'Lua',
            '.vim': 'Vim Script'
        }
        return extension_map.get(extension)
    
    def _get_repository_age(self) -> int:
        """Get repository age in days."""
        try:
            # Get first commit date
            result = self.run_git_command(['git', 'log', '--reverse', '--format=%aI', '-1'], capture_output=True)
            if result:
                first_commit_date = datetime.fromisoformat(result.replace('Z', '+00:00'))
                age = (datetime.now(first_commit_date.tzinfo) - first_commit_date).days
                return age
            return 0
        except Exception:
            return 0
    
    def _get_last_commit_date(self) -> Optional[str]:
        """Get the date of the last commit."""
        try:
            result = self.run_git_command(['git', 'log', '-1', '--format=%aI'], capture_output=True)
            return result if result else None
        except Exception:
            return None
    
    def _get_tags_count(self) -> int:
        """Get number of tags."""
        try:
            result = self.run_git_command(['git', 'tag'], capture_output=True)
            if result:
                return len([tag for tag in result.split('\n') if tag.strip()])
            return 0
        except Exception:
            return 0
    
    def find_large_files(self, threshold_mb: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Find large files in the repository.
        
        Args:
            threshold_mb: Size threshold in MB (uses config default if None)
            
        Returns:
            List of large files with their information
        """
        if threshold_mb is None:
            threshold_mb = self.get_feature_config('large_file_threshold_mb')
        
        self.print_working(f"Scanning for files larger than {threshold_mb} MB...")
        
        try:
            large_files = []
            git_root = self.get_git_root()
            if not git_root:
                return []
            
            # Get tracked files to check
            tracked_files = self.run_git_command(['git', 'ls-files'], capture_output=True)
            if not tracked_files:
                return []
            
            threshold_bytes = threshold_mb * 1024 * 1024
            
            for file_path in tracked_files.split('\n'):
                if not file_path.strip():
                    continue
                
                full_path = git_root / file_path.strip()
                if full_path.exists() and full_path.is_file():
                    try:
                        file_size = full_path.stat().st_size
                        if file_size > threshold_bytes:
                            # Get file info from git
                            file_info = self._get_file_git_info(file_path.strip())
                            
                            large_files.append({
                                'path': file_path.strip(),
                                'size_mb': round(file_size / (1024 * 1024), 2),
                                'size_bytes': file_size,
                                'last_modified': file_info.get('last_modified'),
                                'last_author': file_info.get('last_author'),
                                'commit_count': file_info.get('commit_count', 0)
                            })
                    except OSError:
                        continue
            
            # Sort by size (largest first)
            large_files.sort(key=lambda x: x['size_bytes'], reverse=True)
            return large_files
            
        except Exception as e:
            self.print_error(f"Error finding large files: {str(e)}")
            return []
    
    def _get_file_git_info(self, file_path: str) -> Dict[str, Any]:
        """Get git information for a specific file."""
        try:
            # Get last commit info for the file
            result = self.run_git_command([
                'git', 'log', '-1', '--format=%aI|%an', '--', file_path
            ], capture_output=True)
            
            info = {}
            if result:
                parts = result.split('|', 1)
                if len(parts) >= 2:
                    info['last_modified'] = parts[0]
                    info['last_author'] = parts[1]
            
            # Get commit count for the file
            commit_count_result = self.run_git_command([
                'git', 'rev-list', '--count', 'HEAD', '--', file_path
            ], capture_output=True)
            
            if commit_count_result and commit_count_result.isdigit():
                info['commit_count'] = int(commit_count_result)
            
            return info
            
        except Exception:
            return {}
    
    def calculate_health_score(self) -> Dict[str, Any]:
        """
        Calculate overall repository health score.
        
        Returns:
            Dictionary containing health score and breakdown
        """
        try:
            weights = self.get_feature_config('health_score_weights')
            
            # Get analysis data
            branch_analysis = self.analyze_branches()
            stats = self.get_repository_stats()
            large_files = self.find_large_files()
            
            # Calculate individual scores (0-100)
            scores = {
                'stale_branches': self._score_stale_branches(branch_analysis),
                'large_files': self._score_large_files(large_files),
                'unmerged_branches': self._score_unmerged_branches(branch_analysis),
                'repository_size': self._score_repository_size(stats)
            }
            
            # Calculate weighted overall score
            overall_score = sum(
                scores[metric] * weights.get(metric, 0.25)
                for metric in scores
            )
            
            return {
                'overall_score': round(overall_score, 1),
                'individual_scores': scores,
                'weights': weights,
                'grade': self._score_to_grade(overall_score),
                'recommendations': self._get_score_recommendations(scores)
            }
            
        except Exception as e:
            self.print_error(f"Error calculating health score: {str(e)}")
            return {
                'overall_score': 0, 
                'grade': 'F', 
                'individual_scores': {},
                'weights': {},
                'recommendations': []
            }
    
    def _score_stale_branches(self, branch_analysis: Dict) -> float:
        """Score based on stale branches (fewer is better)."""
        total_branches = branch_analysis.get('summary', {}).get('total_local', 1)
        stale_count = branch_analysis.get('summary', {}).get('stale_count', 0)
        
        if total_branches == 0:
            return 100.0
        
        stale_ratio = stale_count / total_branches
        return max(0, 100 - (stale_ratio * 100))
    
    def _score_large_files(self, large_files: List) -> float:
        """Score based on large files (fewer and smaller is better)."""
        if not large_files:
            return 100.0
        
        # Penalize based on number and size of large files
        file_count_penalty = min(len(large_files) * 10, 50)
        size_penalty = min(sum(f['size_mb'] for f in large_files[:5]) / 10, 50)
        
        return max(0, 100 - file_count_penalty - size_penalty)
    
    def _score_unmerged_branches(self, branch_analysis: Dict) -> float:
        """Score based on unmerged branches (fewer is better)."""
        total_branches = branch_analysis.get('summary', {}).get('total_local', 1)
        unmerged_count = branch_analysis.get('summary', {}).get('unmerged_count', 0)
        
        if total_branches <= 1:  # Only main branch
            return 100.0
        
        unmerged_ratio = unmerged_count / (total_branches - 1)  # Exclude main branch
        return max(0, 100 - (unmerged_ratio * 80))  # Less penalty than stale branches
    
    def _score_repository_size(self, stats: Dict) -> float:
        """Score based on repository size (smaller is generally better)."""
        size_mb = stats.get('repository_size', {}).get('total_mb', 0)
        
        if size_mb < 10:
            return 100.0
        elif size_mb < 50:
            return 90.0
        elif size_mb < 100:
            return 80.0
        elif size_mb < 500:
            return 70.0
        elif size_mb < 1000:
            return 60.0
        else:
            return max(0, 60 - ((size_mb - 1000) / 100))
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def _get_score_recommendations(self, scores: Dict) -> List[str]:
        """Get recommendations based on individual scores."""
        recommendations = []
        
        if scores.get('stale_branches', 100) < 70:
            recommendations.append("Consider cleaning up stale branches that haven't been updated recently")
        
        if scores.get('large_files', 100) < 70:
            recommendations.append("Review large files and consider using Git LFS for binary assets")
        
        if scores.get('unmerged_branches', 100) < 70:
            recommendations.append("Merge or delete feature branches that are no longer needed")
        
        if scores.get('repository_size', 100) < 70:
            recommendations.append("Repository is getting large - consider cleaning up history or splitting into smaller repos")
        
        return recommendations
    
    def _show_repository_statistics(self) -> None:
        """Display comprehensive repository statistics."""
        self.show_feature_header("Repository Statistics")
        
        stats = self.get_repository_stats()
        if not stats:
            self.print_error("Failed to gather repository statistics")
            return
        
        # Repository size
        size_info = stats.get('repository_size', {})
        print(f"{self.format_with_emoji('Repository Size:', '💾')}")
        print(f"   Total: {size_info.get('total_mb', 0)} MB")
        print(f"   Git Database: {size_info.get('git_db_mb', 0)} MB")
        print(f"   Working Tree: {size_info.get('working_tree_mb', 0)} MB")
        print()
        
        # Commit and contributor info
        print(f"{self.format_with_emoji('Activity Statistics:', '📈')}")
        print(f"   Total Commits: {stats.get('commit_count', 0):,}")
        print(f"   Contributors: {stats.get('contributor_count', 0)}")
        print(f"   Repository Age: {stats.get('age_days', 0)} days")
        print(f"   Tags: {stats.get('tags_count', 0)}")
        print(f"   Remotes: {stats.get('remotes_count', 0)}")
        print()
        
        # File statistics
        file_info = stats.get('file_count', {})
        print(f"{self.format_with_emoji('File Statistics:', '📁')}")
        print(f"   Tracked Files: {file_info.get('tracked', 0):,}")
        print(f"   Total Files: {file_info.get('total', 0):,}")
        print(f"   Untracked Files: {file_info.get('untracked', 0):,}")
        print()
        
        # Line count
        line_info = stats.get('line_count', {})
        if line_info.get('total_lines', 0) > 0:
            print(f"{self.format_with_emoji('Code Statistics:', '📝')}")
            print(f"   Total Lines: {line_info.get('total_lines', 0):,}")
            print(f"   Code Lines: {line_info.get('code_lines', 0):,}")
            print(f"   Blank Lines: {line_info.get('blank_lines', 0):,}")
            print(f"   Comment Lines: {line_info.get('comment_lines', 0):,}")
            print()
        
        # Top contributors
        contributors = stats.get('contributors', [])
        if contributors:
            print("👥 Top Contributors:")
            for i, contributor in enumerate(contributors[:5], 1):
                print(f"   {i}. {contributor['name']} ({contributor['commits']} commits)")
            print()
        
        # Programming languages
        languages = stats.get('languages', {})
        if languages:
            print("💻 Programming Languages:")
            for lang, count in list(languages.items())[:5]:
                print(f"   • {lang}: {count} files")
            print()
    
    def _show_large_files_analysis(self) -> None:
        """Display large files analysis."""
        self.show_feature_header("Large Files Analysis")
        
        threshold_mb = self.get_feature_config('large_file_threshold_mb')
        large_files = self.find_large_files(threshold_mb)
        
        if not large_files:
            self.print_success(f"No files larger than {threshold_mb} MB found!")
            return
        
        print(f"{self.format_with_emoji('Files larger than', '📁')} {threshold_mb} MB:")
        print()
        
        total_size = 0
        for i, file_info in enumerate(large_files[:20], 1):  # Show top 20
            size_mb = file_info['size_mb']
            path = file_info['path']
            last_author = file_info.get('last_author', 'Unknown')
            commit_count = file_info.get('commit_count', 0)
            
            total_size += size_mb
            
            print(f"{i:2d}. {path}")
            print(f"    Size: {size_mb} MB")
            print(f"    Last modified by: {last_author}")
            print(f"    Commits: {commit_count}")
            print()
        
        if len(large_files) > 20:
            remaining_size = sum(f['size_mb'] for f in large_files[20:])
            print(f"... and {len(large_files) - 20} more files ({remaining_size:.1f} MB)")
            total_size += remaining_size
        
        print(f"{self.format_with_emoji('Summary:', '📊')}")
        print(f"   Total large files: {len(large_files)}")
        print(f"   Combined size: {total_size:.1f} MB")
        
        if total_size > 100:
            print()
            self.print_info(f"{self.format_with_emoji('Consider using Git LFS for large binary files', '💡')}")
            print("   Git LFS helps manage large files without bloating your repository")
    
    def generate_cleanup_recommendations(self) -> List[Dict[str, Any]]:
        """
        Generate cleanup recommendations based on repository analysis.
        
        Returns:
            List of cleanup recommendations with details
        """
        self.print_working("Generating cleanup recommendations...")
        
        try:
            recommendations = []
            
            # Get analysis data
            branch_analysis = self.analyze_branches()
            stats = self.get_repository_stats()
            large_files = self.find_large_files()
            
            # Stale branches recommendations
            stale_branches = branch_analysis.get('stale_branches', [])
            if stale_branches:
                stale_count = len(stale_branches)
                stale_names = [b['name'] for b in stale_branches[:5]]  # Show first 5
                
                recommendations.append({
                    'type': 'stale_branches',
                    'priority': 'medium',
                    'title': f'Clean up {stale_count} stale branch{"es" if stale_count > 1 else ""}',
                    'description': f'Found {stale_count} branches that haven\'t been updated in over {self.get_feature_config("stale_branch_days")} days',
                    'items': stale_names,
                    'action': 'delete_branches',
                    'impact': 'Reduces repository clutter and improves branch management',
                    'commands': [f'git branch -d {branch}' for branch in stale_names[:3]]
                })
            
            # Unmerged branches recommendations
            unmerged_branches = branch_analysis.get('unmerged_branches', [])
            if unmerged_branches:
                unmerged_count = len(unmerged_branches)
                unmerged_names = [b['name'] for b in unmerged_branches[:5]]
                
                recommendations.append({
                    'type': 'unmerged_branches',
                    'priority': 'high',
                    'title': f'Review {unmerged_count} unmerged branch{"es" if unmerged_count > 1 else ""}',
                    'description': f'Found {unmerged_count} branches with unmerged changes',
                    'items': unmerged_names,
                    'action': 'merge_or_delete',
                    'impact': 'Prevents loss of work and maintains clean repository state',
                    'commands': [f'git merge {branch}' for branch in unmerged_names[:3]]
                })
            
            # Large files recommendations
            if large_files:
                large_count = len(large_files)
                large_names = [f['path'] for f in large_files[:5]]
                total_size = sum(f['size_mb'] for f in large_files)
                
                priority = 'high' if total_size > 100 else 'medium'
                recommendations.append({
                    'type': 'large_files',
                    'priority': priority,
                    'title': f'Optimize {large_count} large file{"s" if large_count > 1 else ""} ({total_size:.1f} MB)',
                    'description': f'Found {large_count} files larger than {self.get_feature_config("large_file_threshold_mb")} MB',
                    'items': large_names,
                    'action': 'use_git_lfs',
                    'impact': 'Reduces repository size and improves clone/fetch performance',
                    'commands': [
                        'git lfs track "*.bin"',
                        'git lfs track "*.zip"',
                        'git add .gitattributes'
                    ]
                })
            
            # Repository size recommendations
            repo_size = stats.get('repository_size', {}).get('total_mb', 0)
            if repo_size > 500:
                priority = 'high' if repo_size > 1000 else 'medium'
                recommendations.append({
                    'type': 'repository_size',
                    'priority': priority,
                    'title': f'Repository is large ({repo_size:.1f} MB)',
                    'description': 'Large repository size may impact performance',
                    'items': [
                        'Consider using Git LFS for large files',
                        'Review and clean up old branches',
                        'Consider repository splitting if appropriate'
                    ],
                    'action': 'optimize_size',
                    'impact': 'Improves clone, fetch, and push performance',
                    'commands': [
                        'git gc --aggressive',
                        'git prune',
                        'git remote prune origin'
                    ]
                })
            
            # Git database size recommendations
            git_db_size = stats.get('repository_size', {}).get('git_db_mb', 0)
            if git_db_size > 100:
                recommendations.append({
                    'type': 'git_database',
                    'priority': 'low',
                    'title': f'Git database is large ({git_db_size:.1f} MB)',
                    'description': 'Git database size can be optimized',
                    'items': [
                        'Run garbage collection',
                        'Prune unreachable objects',
                        'Clean up reflog entries'
                    ],
                    'action': 'optimize_git_db',
                    'impact': 'Reduces .git directory size and improves performance',
                    'commands': [
                        'git gc --aggressive --prune=now',
                        'git reflog expire --expire=30.days.ago --all',
                        'git prune'
                    ]
                })
            
            # Sort by priority
            priority_order = {'high': 0, 'medium': 1, 'low': 2}
            recommendations.sort(key=lambda x: priority_order.get(x['priority'], 3))
            
            return recommendations
            
        except Exception as e:
            self.print_error(f"Error generating cleanup recommendations: {str(e)}")
            return []
    
    def export_health_report(self, format: str = 'json', file_path: Optional[str] = None) -> Optional[str]:
        """
        Export comprehensive health report.
        
        Args:
            format: Export format ('json' or 'text')
            file_path: Optional file path to save report
            
        Returns:
            Report content as string or None if error
        """
        try:
            self.print_working(f"Generating {format.upper()} health report...")
            
            # Gather all data
            branch_analysis = self.analyze_branches()
            stats = self.get_repository_stats()
            large_files = self.find_large_files()
            health_score = self.calculate_health_score()
            recommendations = self.generate_cleanup_recommendations()
            
            # Create report data
            report_data = {
                'generated_at': datetime.now().isoformat(),
                'repository_path': str(self.get_git_root()) if self.get_git_root() else 'unknown',
                'health_score': health_score,
                'branch_analysis': branch_analysis,
                'repository_statistics': stats,
                'large_files': large_files[:20],  # Limit to top 20
                'cleanup_recommendations': recommendations
            }
            
            if format.lower() == 'json':
                report_content = self._export_json_report(report_data)
            elif format.lower() == 'text':
                report_content = self._export_text_report(report_data)
            else:
                self.print_error(f"Unsupported format: {format}")
                return None
            
            # Save to file if path provided
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(report_content)
                    self.print_success(f"Report saved to {file_path}")
                except IOError as e:
                    self.print_error(f"Error saving report: {str(e)}")
                    return None
            
            return report_content
            
        except Exception as e:
            self.print_error(f"Error exporting health report: {str(e)}")
            return None
    
    def _export_json_report(self, report_data: Dict[str, Any]) -> str:
        """Export report in JSON format."""
        return json.dumps(report_data, indent=2, ensure_ascii=False, default=str)
    
    def _export_text_report(self, report_data: Dict[str, Any]) -> str:
        """Export report in human-readable text format."""
        lines = []
        
        # Header
        lines.append("=" * 60)
        lines.append("REPOSITORY HEALTH REPORT")
        lines.append("=" * 60)
        lines.append(f"Generated: {report_data['generated_at']}")
        lines.append(f"Repository: {report_data['repository_path']}")
        lines.append("")
        
        # Health Score
        health_score = report_data.get('health_score', {})
        lines.append("OVERALL HEALTH SCORE")
        lines.append("-" * 20)
        lines.append(f"Score: {health_score.get('overall_score', 0)}/100 (Grade: {health_score.get('grade', 'F')})")
        lines.append("")
        
        individual_scores = health_score.get('individual_scores', {})
        if individual_scores:
            lines.append("Individual Scores:")
            for metric, score in individual_scores.items():
                metric_name = metric.replace('_', ' ').title()
                lines.append(f"  • {metric_name}: {score:.1f}/100")
            lines.append("")
        
        # Repository Statistics
        stats = report_data.get('repository_statistics', {})
        if stats:
            lines.append("REPOSITORY STATISTICS")
            lines.append("-" * 21)
            
            # Size info
            size_info = stats.get('repository_size', {})
            lines.append(f"Repository Size: {size_info.get('total_mb', 0)} MB")
            lines.append(f"  • Git Database: {size_info.get('git_db_mb', 0)} MB")
            lines.append(f"  • Working Tree: {size_info.get('working_tree_mb', 0)} MB")
            lines.append("")
            
            # Activity info
            lines.append(f"Total Commits: {stats.get('commit_count', 0):,}")
            lines.append(f"Contributors: {stats.get('contributor_count', 0)}")
            lines.append(f"Repository Age: {stats.get('age_days', 0)} days")
            lines.append(f"Tags: {stats.get('tags_count', 0)}")
            lines.append("")
            
            # File info
            file_info = stats.get('file_count', {})
            lines.append(f"Files: {file_info.get('tracked', 0):,} tracked, {file_info.get('untracked', 0):,} untracked")
            lines.append("")
        
        # Branch Analysis
        branch_analysis = report_data.get('branch_analysis', {})
        if branch_analysis:
            lines.append("BRANCH ANALYSIS")
            lines.append("-" * 15)
            
            summary = branch_analysis.get('summary', {})
            lines.append(f"Local Branches: {summary.get('total_local', 0)}")
            lines.append(f"Remote Branches: {summary.get('total_remote', 0)}")
            lines.append(f"Stale Branches: {summary.get('stale_count', 0)}")
            lines.append(f"Unmerged Branches: {summary.get('unmerged_count', 0)}")
            lines.append("")
        
        # Large Files
        large_files = report_data.get('large_files', [])
        if large_files:
            lines.append("LARGE FILES")
            lines.append("-" * 11)
            for i, file_info in enumerate(large_files[:10], 1):
                lines.append(f"{i:2d}. {file_info['path']} ({file_info['size_mb']} MB)")
            
            if len(large_files) > 10:
                lines.append(f"... and {len(large_files) - 10} more files")
            lines.append("")
        
        # Cleanup Recommendations
        recommendations = report_data.get('cleanup_recommendations', [])
        if recommendations:
            lines.append("CLEANUP RECOMMENDATIONS")
            lines.append("-" * 23)
            
            for i, rec in enumerate(recommendations, 1):
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec['priority'], "⚪")
                lines.append(f"{i}. {priority_icon} {rec['title']}")
                lines.append(f"   {rec['description']}")
                lines.append(f"   Impact: {rec['impact']}")
                
                if rec.get('commands'):
                    lines.append("   Suggested commands:")
                    for cmd in rec['commands'][:3]:
                        lines.append(f"     $ {cmd}")
                lines.append("")
        
        lines.append("=" * 60)
        lines.append("End of Report")
        lines.append("=" * 60)
        
        return '\n'.join(lines)
    
    def _show_cleanup_recommendations(self) -> None:
        """Display cleanup recommendations with interactive options."""
        self.show_feature_header("Cleanup Recommendations")
        
        recommendations = self.generate_cleanup_recommendations()
        
        if not recommendations:
            self.print_success("🎉 No cleanup recommendations - your repository looks healthy!")
            return
        
        print(f"Found {len(recommendations)} cleanup recommendations:\n")
        
        for i, rec in enumerate(recommendations, 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec['priority'], "⚪")
            formatted_priority = self.format_with_emoji(rec['title'], priority_icon)
            print(f"{i}. {formatted_priority} ({rec['priority'].upper()} priority)")
            print(f"   {self.format_with_emoji(rec['description'], '📝')}")
            print(f"   {self.format_with_emoji('Impact:', '💡')} {rec['impact']}")
            
            if rec.get('items'):
                print(f"   {self.format_with_emoji('Items:', '📋')}")
                for item in rec['items'][:3]:
                    print(f"      • {item}")
                if len(rec['items']) > 3:
                    print(f"      ... and {len(rec['items']) - 3} more")
            
            if rec.get('commands'):
                print(f"   {self.format_with_emoji('Suggested commands:', '🔧')}")
                for cmd in rec['commands'][:3]:
                    print(f"      $ {cmd}")
            
            print()
        
        # Interactive cleanup options
        if self.confirm("Would you like to see detailed cleanup actions?"):
            self._show_interactive_cleanup(recommendations)
    
    def _show_interactive_cleanup(self, recommendations: List[Dict[str, Any]]) -> None:
        """Show interactive cleanup options."""
        while True:
            self.clear_screen()
            self.show_feature_header("Interactive Cleanup")
            
            print("Select a cleanup action:")
            for i, rec in enumerate(recommendations, 1):
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec['priority'], "⚪")
                print(f"{i}. {priority_icon} {rec['title']}")
            
            print(f"{len(recommendations) + 1}. {self.format_with_emoji('Back to Dashboard', '🏠')}")
            
            choice = self.get_input(f"\nSelect option (1-{len(recommendations) + 1}): ").strip()
            
            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(recommendations):
                    self._show_cleanup_details(recommendations[choice_num - 1])
                elif choice_num == len(recommendations) + 1:
                    break
                else:
                    self.print_error("Invalid option. Please try again.")
            else:
                self.print_error("Invalid option. Please try again.")
            
            if choice != str(len(recommendations) + 1):
                input("\nPress Enter to continue...")
    
    def _show_cleanup_details(self, recommendation: Dict[str, Any]) -> None:
        """Show detailed information about a cleanup recommendation."""
        self.clear_screen()
        print("=" * 50)
        print(f"{self.format_with_emoji(recommendation['title'], '🧹')}")
        print("=" * 50)
        
        print(f"{self.format_with_emoji('Description:', '📝')} {recommendation['description']}")
        print(f"{self.format_with_emoji('Impact:', '💡')} {recommendation['impact']}")
        print(f"{self.format_with_emoji('Priority:', '⚠️')} {recommendation['priority'].upper()}")
        print()
        
        if recommendation.get('items'):
            print(f"{self.format_with_emoji('Affected Items:', '📋')}")
            for item in recommendation['items']:
                print(f"   • {item}")
            print()
        
        if recommendation.get('commands'):
            print(f"{self.format_with_emoji('Suggested Commands:', '🔧')}")
            for cmd in recommendation['commands']:
                print(f"   $ {cmd}")
            print()
        
        print(f"{self.format_with_emoji('Note: Please review these suggestions carefully before executing.', '⚠️')}")
        print("   Always backup your repository before making significant changes.")
    
    def show_health_dashboard(self) -> None:
        """
        Display comprehensive interactive health dashboard.
        
        This is the main dashboard interface that shows all health metrics
        and provides interactive navigation through health issues.
        """
        if not self.is_git_repo():
            self.print_error("Not in a Git repository!")
            return
        
        while True:
            try:
                self._display_dashboard()
                
                print(f"\n{self.format_with_emoji('Dashboard Actions:', '🎯')}")
                print(f"1. {self.format_with_emoji('Refresh Dashboard', '🔄')}")
                print(f"2. {self.format_with_emoji('View Branch Details', '🌿')}")
                print(f"3. {self.format_with_emoji('View Large Files Details', '📁')}")
                print(f"4. {self.format_with_emoji('View Cleanup Recommendations', '🧹')}")
                print(f"5. {self.format_with_emoji('Export Health Report', '📤')}")
                print(f"6. {self.format_with_emoji('Configure Dashboard', '⚙️')}")
                print(f"7. {self.format_with_emoji('Back to Main Menu', '🏠')}")
                
                choice = self.get_input("\nSelect action (1-7): ").strip()
                
                if choice == '1':
                    self._refresh_dashboard()
                elif choice == '2':
                    self._show_branch_details()
                elif choice == '3':
                    self._show_large_files_details()
                elif choice == '4':
                    self._show_cleanup_recommendations()
                elif choice == '5':
                    self._export_health_report()
                elif choice == '6':
                    self._configure_dashboard()
                elif choice == '7':
                    break
                else:
                    self.print_error("Invalid option. Please try again.")
                
                if choice != '7':
                    input("\nPress Enter to continue...")
                    
            except KeyboardInterrupt:
                print("\n\nDashboard interrupted by user.")
                break
            except Exception as e:
                self.print_error(f"Dashboard error: {str(e)}")
                input("\nPress Enter to continue...")
    
    def _display_dashboard(self) -> None:
        """Display the main dashboard with all health metrics."""
        self.show_feature_header("Repository Health Dashboard")
        
        # Get all analysis data
        self.print_working("Loading dashboard data...")
        
        try:
            branch_analysis = self.analyze_branches()
            stats = self.get_repository_stats()
            large_files = self.find_large_files()
            health_score = self.calculate_health_score()
            recommendations = self.generate_cleanup_recommendations()
            
            # Display health score prominently
            self._display_health_score(health_score)
            
            # Display key metrics in columns
            self._display_key_metrics(branch_analysis, stats, large_files)
            
            # Display quick recommendations
            self._display_quick_recommendations(recommendations)
            
        except Exception as e:
            self.print_error(f"Error loading dashboard: {str(e)}")
    
    def _display_health_score(self, health_score: Dict[str, Any]) -> None:
        """Display the overall health score prominently."""
        score = health_score.get('overall_score', 0)
        grade = health_score.get('grade', 'F')
        
        # Color-coded score display
        if score >= 90:
            score_color = "🟢"  # Green
        elif score >= 70:
            score_color = "🟡"  # Yellow
        else:
            score_color = "🔴"  # Red
        
        print("=" * 60)
        print(f"🏥 OVERALL HEALTH SCORE: {score_color} {score}/100 (Grade: {grade})")
        print("=" * 60)
        
        # Show individual scores
        individual_scores = health_score.get('individual_scores', {})
        if individual_scores:
            print(f"\n{self.format_with_emoji('Individual Metrics:', '📊')}")
            for metric, metric_score in individual_scores.items():
                metric_name = metric.replace('_', ' ').title()
                bar = self._create_score_bar(metric_score)
                print(f"   {metric_name:20} {bar} {metric_score:.1f}/100")
        
        print()
    
    def _create_score_bar(self, score: float, width: int = 20) -> str:
        """Create a visual score bar."""
        filled = int((score / 100) * width)
        empty = width - filled
        
        if score >= 80:
            bar_char = "█"
            color = "🟢"
        elif score >= 60:
            bar_char = "█"
            color = "🟡"
        else:
            bar_char = "█"
            color = "🔴"
        
        return f"[{'█' * filled}{'░' * empty}]"
    
    def _display_key_metrics(self, branch_analysis: Dict, stats: Dict, large_files: List) -> None:
        """Display key metrics in a structured format."""
        print(f"{self.format_with_emoji('KEY METRICS', '📈')}")
        print("-" * 40)
        
        # Repository info
        repo_size = stats.get('repository_size', {}).get('total_mb', 0)
        commit_count = stats.get('commit_count', 0)
        contributor_count = stats.get('contributor_count', 0)
        age_days = stats.get('age_days', 0)
        
        print(f"{self.format_with_emoji('Repository Size:', '📦')}     {repo_size:.1f} MB")
        print(f"📝 Total Commits:       {commit_count:,}")
        print(f"👥 Contributors:        {contributor_count}")
        print(f"📅 Repository Age:      {age_days} days")
        
        # Branch info
        summary = branch_analysis.get('summary', {})
        local_branches = summary.get('total_local', 0)
        stale_branches = summary.get('stale_count', 0)
        unmerged_branches = summary.get('unmerged_count', 0)
        
        print(f"🌿 Local Branches:      {local_branches}")
        print(f"🕰️  Stale Branches:      {stale_branches}")
        print(f"🔀 Unmerged Branches:   {unmerged_branches}")
        
        # File info
        large_files_count = len(large_files)
        large_files_size = sum(f['size_mb'] for f in large_files)
        
        print(f"📁 Large Files:         {large_files_count} ({large_files_size:.1f} MB)")
        
        print()
    
    def _display_quick_recommendations(self, recommendations: List[Dict]) -> None:
        """Display top recommendations quickly."""
        if not recommendations:
            print("🎉 No recommendations - your repository looks healthy!")
            return
        
        print("🧹 TOP RECOMMENDATIONS")
        print("-" * 40)
        
        # Show top 3 recommendations
        for i, rec in enumerate(recommendations[:3], 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec['priority'], "⚪")
            print(f"{i}. {priority_icon} {rec['title']}")
        
        if len(recommendations) > 3:
            print(f"   ... and {len(recommendations) - 3} more recommendations")
        
        print()
    
    def _refresh_dashboard(self) -> None:
        """Refresh dashboard data."""
        self.print_working("Refreshing dashboard data...")
        self.health_cache.clear()
        self.print_success("Dashboard refreshed!")
    
    def _show_branch_details(self) -> None:
        """Show detailed branch analysis."""
        self.show_feature_header("Branch Details")
        
        branch_analysis = self.analyze_branches()
        if not branch_analysis:
            self.print_error("Failed to analyze branches")
            return
        
        # Show detailed branch information
        summary = branch_analysis.get('summary', {})
        
        print("🌿 BRANCH SUMMARY")
        print("-" * 30)
        print(f"Local Branches:    {summary.get('total_local', 0)}")
        print(f"Remote Branches:   {summary.get('total_remote', 0)}")
        print(f"Stale Branches:    {summary.get('stale_count', 0)}")
        print(f"Unmerged Branches: {summary.get('unmerged_count', 0)}")
        print()
        
        # Show stale branches
        stale_branches = branch_analysis.get('stale_branches', [])
        if stale_branches:
            print("🕰️  STALE BRANCHES")
            print("-" * 20)
            for branch in stale_branches[:10]:
                days_old = branch.get('days_old', 0)
                print(f"   • {branch['name']} ({days_old} days old)")
            
            if len(stale_branches) > 10:
                print(f"   ... and {len(stale_branches) - 10} more")
            print()
        
        # Show unmerged branches
        unmerged_branches = branch_analysis.get('unmerged_branches', [])
        if unmerged_branches:
            print("🔀 UNMERGED BRANCHES")
            print("-" * 20)
            for branch in unmerged_branches[:10]:
                ahead = branch.get('ahead', 0)
                behind = branch.get('behind', 0)
                status = f"↑{ahead} ↓{behind}" if ahead or behind else "even"
                print(f"   • {branch['name']} ({status})")
            
            if len(unmerged_branches) > 10:
                print(f"   ... and {len(unmerged_branches) - 10} more")
            print()
        
        # Interactive branch actions
        if stale_branches or unmerged_branches:
            print("🎯 BRANCH ACTIONS")
            print("-" * 15)
            print("1. 🗑️  Show commands to delete stale branches")
            print("2. 🔀 Show commands to merge unmerged branches")
            print("3. 🏠 Back to Dashboard")
            
            choice = self.get_input("\nSelect action (1-3): ").strip()
            
            if choice == '1' and stale_branches:
                self._show_stale_branch_commands(stale_branches)
            elif choice == '2' and unmerged_branches:
                self._show_unmerged_branch_commands(unmerged_branches)
    
    def _show_stale_branch_commands(self, stale_branches: List[Dict]) -> None:
        """Show commands to clean up stale branches."""
        print("\n🗑️  STALE BRANCH CLEANUP COMMANDS")
        print("-" * 35)
        print("⚠️  Review these branches before deleting!")
        print()
        
        for branch in stale_branches[:10]:
            print(f"# Delete {branch['name']} (last updated {branch.get('days_old', 0)} days ago)")
            print(f"git branch -d {branch['name']}")
            print()
        
        print("💡 Use 'git branch -D' to force delete if needed")
        print("💡 Always backup important branches before deleting")
    
    def _show_unmerged_branch_commands(self, unmerged_branches: List[Dict]) -> None:
        """Show commands to handle unmerged branches."""
        print("\n🔀 UNMERGED BRANCH COMMANDS")
        print("-" * 25)
        print("⚠️  Review changes before merging!")
        print()
        
        for branch in unmerged_branches[:10]:
            ahead = branch.get('ahead', 0)
            behind = branch.get('behind', 0)
            
            print(f"# Merge {branch['name']} (↑{ahead} ↓{behind})")
            if behind > 0:
                print(f"git checkout {branch['name']}")
                print("git pull origin main  # Update with latest changes")
                print("git checkout main")
            print(f"git merge {branch['name']}")
            print()
        
        print("💡 Consider using 'git rebase' for cleaner history")
        print("💡 Test thoroughly before merging to main branch")
    
    def _show_large_files_details(self) -> None:
        """Show detailed large files analysis."""
        self.show_feature_header("Large Files Details")
        
        threshold_mb = self.get_feature_config('large_file_threshold_mb')
        large_files = self.find_large_files(threshold_mb)
        
        if not large_files:
            self.print_success(f"🎉 No files larger than {threshold_mb} MB found!")
            return
        
        print(f"📁 FILES LARGER THAN {threshold_mb} MB")
        print("-" * 40)
        
        total_size = 0
        for i, file_info in enumerate(large_files[:20], 1):
            size_mb = file_info['size_mb']
            path = file_info['path']
            last_author = file_info.get('last_author', 'Unknown')
            commit_count = file_info.get('commit_count', 0)
            
            total_size += size_mb
            
            print(f"{i:2d}. {path}")
            print(f"    📏 Size: {size_mb} MB")
            print(f"    👤 Last modified by: {last_author}")
            print(f"    📝 Commits: {commit_count}")
            print()
        
        if len(large_files) > 20:
            remaining_size = sum(f['size_mb'] for f in large_files[20:])
            print(f"... and {len(large_files) - 20} more files ({remaining_size:.1f} MB)")
            total_size += remaining_size
        
        print(f"📊 SUMMARY")
        print("-" * 10)
        print(f"Total large files: {len(large_files)}")
        print(f"Combined size: {total_size:.1f} MB")
        
        if total_size > 50:
            print()
            print("💡 RECOMMENDATIONS")
            print("-" * 15)
            print("• Consider using Git LFS for large binary files")
            print("• Git LFS helps manage large files without bloating your repository")
            print("• Commands to set up Git LFS:")
            print("  git lfs install")
            print("  git lfs track '*.bin'")
            print("  git lfs track '*.zip'")
            print("  git add .gitattributes")
    
    def _show_full_health_report(self) -> None:
        """Display the comprehensive health dashboard."""
        self.show_health_dashboard()
    
    def _export_health_report(self) -> None:
        """Interactive health report export."""
        self.show_feature_header("Export Health Report")
        
        print("📤 Export Options:")
        print("1. 📄 JSON Format")
        print("2. 📝 Text Format")
        print("3. 🏠 Back to Dashboard")
        
        choice = self.get_input("\nSelect format (1-3): ").strip()
        
        if choice == '1':
            format_type = 'json'
            extension = '.json'
        elif choice == '2':
            format_type = 'text'
            extension = '.txt'
        elif choice == '3':
            return
        else:
            self.print_error("Invalid option.")
            return
        
        # Get file path
        git_root = self.get_git_root()
        default_name = f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"
        default_path = str(git_root / default_name) if git_root else default_name
        
        file_path = self.get_input(f"Save as [{default_path}]: ").strip()
        if not file_path:
            file_path = default_path
        
        # Export report
        report_content = self.export_health_report(format_type, file_path)
        
        if report_content:
            print()
            if self.confirm("Would you like to preview the report?"):
                print("\n" + "=" * 50)
                print("REPORT PREVIEW")
                print("=" * 50)
                
                # Show first 30 lines for preview
                lines = report_content.split('\n')
                for line in lines[:30]:
                    print(line)
                
                if len(lines) > 30:
                    print(f"\n... and {len(lines) - 30} more lines")
                    print(f"Full report saved to: {file_path}")
        else:
            self.print_error("Failed to export health report")
    
    def _configure_dashboard(self) -> None:
        """Configure dashboard settings."""
        self.show_feature_header("Dashboard Configuration")
        
        print("⚙️  Current Configuration:")
        config = self.get_feature_config()
        print(f"   Stale Branch Days: {config.get('stale_branch_days', 30)}")
        print(f"   Large File Threshold: {config.get('large_file_threshold_mb', 10)} MB")
        print(f"   Show Remote Branches: {config.get('show_remote_branches', True)}")
        print(f"   Max Branches Display: {config.get('max_branches_display', 50)}")
        print()
        
        if self.confirm("Do you want to modify the configuration?"):
            # Stale branch days
            stale_days = self.get_input(
                f"Stale branch threshold (days) [{config.get('stale_branch_days', 30)}]: "
            ).strip()
            if stale_days.isdigit():
                self.set_feature_config('stale_branch_days', int(stale_days))
            
            # Large file threshold
            large_file_mb = self.get_input(
                f"Large file threshold (MB) [{config.get('large_file_threshold_mb', 10)}]: "
            ).strip()
            if large_file_mb.replace('.', '').isdigit():
                self.set_feature_config('large_file_threshold_mb', float(large_file_mb))
            
            # Show remote branches
            show_remote = self.confirm(
                "Show remote branches in analysis?", 
                config.get('show_remote_branches', True)
            )
            self.set_feature_config('show_remote_branches', show_remote)
            
            # Max branches display
            max_display = self.get_input(
                f"Maximum branches to display [{config.get('max_branches_display', 50)}]: "
            ).strip()
            if max_display.isdigit():
                self.set_feature_config('max_branches_display', int(max_display))
            
            self.print_success("Configuration updated successfully!")
    
    def _refresh_analysis(self) -> None:
        """Refresh the analysis cache."""
        self.print_working("Refreshing analysis cache...")
        self.health_cache.clear()
        self.print_success("Analysis cache refreshed!")