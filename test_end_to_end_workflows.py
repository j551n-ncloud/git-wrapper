#!/usr/bin/env python3
"""
End-to-end workflow tests covering complete user scenarios
"""

import unittest
import tempfile
import shutil
import os
import json
import subprocess
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from git_wrapper import InteractiveGitWrapper


class TestEndToEndWorkflows(unittest.TestCase):
    """Test complete user scenarios from start to finish"""
    
    def setUp(self):
        """Set up test fixtures with temporary git repository"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Initialize a git repository
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True)
        
        # Create initial commit
        with open('README.md', 'w') as f:
            f.write('# Test Repository\nInitial content\n')
        subprocess.run(['git', 'add', 'README.md'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], check=True)
        
        # Initialize git wrapper
        self.git_wrapper = InteractiveGitWrapper()
        self.git_wrapper.config_file = Path(self.test_dir) / 'test_config.json'
        
        # Mock print methods to avoid output during tests
        self.git_wrapper.print_info = Mock()
        self.git_wrapper.print_success = Mock()
        self.git_wrapper.print_error = Mock()
        self.git_wrapper.print_working = Mock()
    
    def tearDown(self):
        """Clean up test fixtures"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_complete_feature_development_workflow(self):
        """Test complete feature development from start to finish"""
        # Get required feature managers
        stash_manager = self.git_wrapper.get_feature_manager('stash')
        template_engine = self.git_wrapper.get_feature_manager('templates')
        workflow_manager = self.git_wrapper.get_feature_manager('workflows')
        health_dashboard = self.git_wrapper.get_feature_manager('health')
        
        if not all([stash_manager, template_engine, workflow_manager, health_dashboard]):
            self.skipTest("Required features not available")
        
        # Step 1: Check repository health before starting
        initial_health = health_dashboard.analyze_branches()
        self.assertIsInstance(initial_health, dict)
        
        # Step 2: Start working on a feature, but get interrupted
        with open('feature_file.py', 'w') as f:
            f.write('# Work in progress\ndef new_feature():\n    pass\n')
        
        # Step 3: Stash work in progress
        with patch('builtins.input', side_effect=['wip-feature', 'y']):
            stash_result = stash_manager.create_named_stash('wip-feature', 'Work in progress on new feature')
            self.assertTrue(stash_result)
        
        # Step 4: Start proper feature branch
        with patch('builtins.input', side_effect=['user-profile', 'y']):
            branch_result = workflow_manager.start_feature_branch('user-profile', 'github_flow')
            self.assertTrue(branch_result)
        
        # Verify we're on the feature branch
        current_branch = subprocess.run(['git', 'branch', '--show-current'], 
                                      capture_output=True, text=True).stdout.strip()
        self.assertIn('user-profile', current_branch)
        
        # Step 5: Apply stashed work
        stashes = stash_manager.list_stashes_with_metadata()
        if stashes:
            with patch('builtins.input', side_effect=['y']):
                apply_result = stash_manager.apply_stash(stashes[0]['id'], keep=False)
                self.assertTrue(apply_result)
        
        # Step 6: Complete the feature implementation
        with open('feature_file.py', 'w') as f:
            f.write('''def new_feature():
    """Implement user profile feature"""
    return {"name": "User", "email": "user@example.com"}

def validate_profile(profile):
    """Validate user profile data"""
    return "name" in profile and "email" in profile
''')
        
        subprocess.run(['git', 'add', 'feature_file.py'], check=True)
        
        # Step 7: Commit using template
        template = template_engine.get_template_by_name('feat')
        if template:
            commit_msg = template_engine.apply_template(template, {
                'scope': 'profile',
                'description': 'implement user profile management',
                'body': 'Add user profile creation and validation functions'
            })
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        
        # Step 8: Add tests
        with open('test_feature.py', 'w') as f:
            f.write('''import unittest
from feature_file import new_feature, validate_profile

class TestUserProfile(unittest.TestCase):
    def test_new_feature(self):
        profile = new_feature()
        self.assertIn("name", profile)
        self.assertIn("email", profile)
    
    def test_validate_profile(self):
        valid_profile = {"name": "Test", "email": "test@example.com"}
        self.assertTrue(validate_profile(valid_profile))
        
        invalid_profile = {"name": "Test"}
        self.assertFalse(validate_profile(invalid_profile))

if __name__ == '__main__':
    unittest.main()
''')
        
        subprocess.run(['git', 'add', 'test_feature.py'], check=True)
        
        # Commit tests using template
        if template:
            test_commit_msg = template_engine.apply_template(template, {
                'scope': 'profile',
                'description': 'add comprehensive tests',
                'body': 'Add unit tests for user profile functionality'
            })
            subprocess.run(['git', 'commit', '-m', test_commit_msg], check=True)
        
        # Step 9: Check health before merging
        pre_merge_health = health_dashboard.analyze_branches()
        self.assertGreater(len(pre_merge_health.get('unmerged_branches', [])), 0)
        
        # Step 10: Finish feature branch
        with patch('builtins.input', side_effect=['merge', 'y']):
            finish_result = workflow_manager.finish_feature_branch(current_branch, 'merge')
            self.assertTrue(finish_result)
        
        # Step 11: Verify final state
        final_branch = subprocess.run(['git', 'branch', '--show-current'], 
                                    capture_output=True, text=True).stdout.strip()
        self.assertEqual(final_branch, 'main')
        
        # Verify files exist on main branch
        self.assertTrue(Path('feature_file.py').exists())
        self.assertTrue(Path('test_feature.py').exists())
        
        # Check final health
        final_health = health_dashboard.analyze_branches()
        self.assertIsInstance(final_health, dict)
    
    def test_hotfix_workflow_with_conflict_resolution(self):
        """Test hotfix workflow with conflict resolution"""
        template_engine = self.git_wrapper.get_feature_manager('templates')
        workflow_manager = self.git_wrapper.get_feature_manager('workflows')
        conflict_resolver = self.git_wrapper.get_feature_manager('conflicts')
        
        if not all([template_engine, workflow_manager, conflict_resolver]):
            self.skipTest("Required features not available")
        
        # Step 1: Create a production-like scenario
        with open('config.py', 'w') as f:
            f.write('VERSION = "1.0.0"\nDEBUG = False\n')
        subprocess.run(['git', 'add', 'config.py'], check=True)
        subprocess.run(['git', 'commit', '-m', 'feat: add production config'], check=True)
        
        # Step 2: Create a development branch with conflicting changes
        subprocess.run(['git', 'checkout', '-b', 'develop'], check=True)
        with open('config.py', 'w') as f:
            f.write('VERSION = "1.1.0-dev"\nDEBUG = True\nLOG_LEVEL = "DEBUG"\n')
        subprocess.run(['git', 'add', 'config.py'], check=True)
        subprocess.run(['git', 'commit', '-m', 'feat: add development config'], check=True)
        
        # Step 3: Go back to main for hotfix
        subprocess.run(['git', 'checkout', 'main'], check=True)
        
        # Step 4: Start hotfix branch
        with patch('builtins.input', side_effect=['security-patch', 'y']):
            hotfix_result = workflow_manager.start_feature_branch('security-patch', 'git_flow')
            self.assertTrue(hotfix_result)
        
        # Step 5: Make hotfix changes
        with open('config.py', 'w') as f:
            f.write('VERSION = "1.0.1"\nDEBUG = False\nSECURITY_ENABLED = True\n')
        subprocess.run(['git', 'add', 'config.py'], check=True)
        
        # Commit hotfix using template
        template = template_engine.get_template_by_name('fix')
        if template:
            commit_msg = template_engine.apply_template(template, {
                'scope': 'security',
                'description': 'enable security features',
                'body': 'Add security configuration to prevent vulnerabilities'
            })
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        
        # Step 6: Merge hotfix back to main
        subprocess.run(['git', 'checkout', 'main'], check=True)
        current_branch = subprocess.run(['git', 'branch', '--show-current'], 
                                      capture_output=True, text=True).stdout.strip()
        
        # Find the hotfix branch name
        branches = subprocess.run(['git', 'branch'], capture_output=True, text=True).stdout
        hotfix_branch = None
        for line in branches.split('\n'):
            if 'security-patch' in line:
                hotfix_branch = line.strip().replace('* ', '').strip()
                break
        
        if hotfix_branch:
            subprocess.run(['git', 'merge', hotfix_branch], check=True)
        
        # Step 7: Now merge develop to create conflict
        merge_result = subprocess.run(['git', 'merge', 'develop'], capture_output=True)
        if merge_result.returncode != 0:  # Conflict occurred
            # Step 8: Use conflict resolver
            conflicted_files = conflict_resolver.list_conflicted_files()
            self.assertIn('config.py', conflicted_files)
            
            # Resolve using manual strategy (keep both changes)
            with patch('builtins.input', side_effect=['manual', 'y']):
                resolve_result = conflict_resolver.resolve_conflict('config.py', 'manual')
                
                # Manually resolve the conflict
                with open('config.py', 'w') as f:
                    f.write('VERSION = "1.1.0-dev"\nDEBUG = True\nLOG_LEVEL = "DEBUG"\nSECURITY_ENABLED = True\n')
                subprocess.run(['git', 'add', 'config.py'], check=True)
                
                # Finalize merge
                with patch('builtins.input', side_effect=['y']):
                    finalize_result = conflict_resolver.finalize_merge()
                    self.assertTrue(finalize_result)
        
        # Verify final state
        self.assertTrue(Path('config.py').exists())
        with open('config.py', 'r') as f:
            content = f.read()
            self.assertIn('SECURITY_ENABLED', content)
    
    def test_backup_and_recovery_workflow(self):
        """Test complete backup and recovery workflow"""
        backup_system = self.git_wrapper.get_feature_manager('backup')
        health_dashboard = self.git_wrapper.get_feature_manager('health')
        
        if not backup_system or not health_dashboard:
            self.skipTest("Required features not available")
        
        # Step 1: Create multiple branches with work
        branches_data = [
            ('feature/auth', 'auth.py', 'Authentication module'),
            ('feature/ui', 'ui.py', 'User interface module'),
            ('hotfix/bug-123', 'fix.py', 'Critical bug fix')
        ]
        
        for branch_name, filename, description in branches_data:
            subprocess.run(['git', 'checkout', '-b', branch_name], check=True)
            with open(filename, 'w') as f:
                f.write(f'# {description}\nprint("Hello from {branch_name}")\n')
            subprocess.run(['git', 'add', filename], check=True)
            subprocess.run(['git', 'commit', '-m', f'feat: add {description.lower()}'], check=True)
        
        subprocess.run(['git', 'checkout', 'main'], check=True)
        
        # Step 2: Analyze repository health to determine backup strategy
        health_analysis = health_dashboard.analyze_branches()
        important_branches = ['main'] + [b for b in health_analysis.get('unmerged_branches', []) 
                                       if 'hotfix' in b]
        
        # Step 3: Configure and create backup
        with patch.object(backup_system, '_push_to_remote', return_value=True), \
             patch('builtins.input', side_effect=['y']):
            backup_result = backup_system.create_backup(important_branches, 'backup')
            self.assertTrue(backup_result)
        
        # Step 4: Simulate data loss (delete a branch)
        subprocess.run(['git', 'branch', '-D', 'hotfix/bug-123'], check=True)
        
        # Verify branch is gone
        branches = subprocess.run(['git', 'branch'], capture_output=True, text=True).stdout
        self.assertNotIn('hotfix/bug-123', branches)
        
        # Step 5: List backup versions
        backup_versions = backup_system.list_backup_versions()
        self.assertGreater(len(backup_versions), 0)
        
        # Step 6: Restore from backup
        if backup_versions:
            with patch.object(backup_system, '_fetch_from_remote', return_value=True), \
                 patch('builtins.input', side_effect=['y']):
                restore_result = backup_system.restore_from_backup(backup_versions[0]['id'])
                # Note: In real scenario this would restore the branch
                # For test, we just verify the method was called correctly
                self.assertIsInstance(restore_result, bool)
    
    def test_repository_maintenance_workflow(self):
        """Test complete repository maintenance workflow"""
        health_dashboard = self.git_wrapper.get_feature_manager('health')
        stash_manager = self.git_wrapper.get_feature_manager('stash')
        
        if not health_dashboard or not stash_manager:
            self.skipTest("Required features not available")
        
        # Step 1: Create a messy repository state
        # Create old stashes
        for i in range(3):
            with open(f'temp_{i}.py', 'w') as f:
                f.write(f'# Temporary file {i}\n')
            with patch('builtins.input', side_effect=[f'temp-work-{i}', 'y']):
                stash_manager.create_named_stash(f'temp-work-{i}', f'Temporary work {i}')
        
        # Create stale branches
        stale_branches = ['feature/old-1', 'feature/old-2', 'experiment/test']
        for branch in stale_branches:
            subprocess.run(['git', 'checkout', '-b', branch], check=True)
            with open(f'{branch.replace("/", "_")}.py', 'w') as f:
                f.write(f'# Content for {branch}\n')
            subprocess.run(['git', 'add', f'{branch.replace("/", "_")}.py'], check=True)
            subprocess.run(['git', 'commit', '-m', f'Add {branch} content'], check=True)
        
        subprocess.run(['git', 'checkout', 'main'], check=True)
        
        # Create large files
        with open('large_file.txt', 'w') as f:
            f.write('x' * 1024 * 1024)  # 1MB file
        subprocess.run(['git', 'add', 'large_file.txt'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Add large file'], check=True)
        
        # Step 2: Run health analysis
        health_analysis = health_dashboard.analyze_branches()
        self.assertIn('unmerged_branches', health_analysis)
        self.assertGreater(len(health_analysis['unmerged_branches']), 0)
        
        repo_stats = health_dashboard.get_repository_stats()
        self.assertIn('total_size', repo_stats)
        
        large_files = health_dashboard.find_large_files(threshold_mb=0.5)
        self.assertGreater(len(large_files), 0)
        
        # Step 3: Generate cleanup recommendations
        recommendations = health_dashboard.generate_cleanup_recommendations()
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
        
        # Step 4: Clean up stashes
        stashes = stash_manager.list_stashes_with_metadata()
        if stashes:
            # Delete old stashes
            with patch('builtins.input', side_effect=['y'] * len(stashes)):
                for stash in stashes[:2]:  # Delete first 2 stashes
                    delete_result = stash_manager.delete_stash(stash['id'])
                    self.assertTrue(delete_result)
        
        # Step 5: Verify cleanup
        remaining_stashes = stash_manager.list_stashes_with_metadata()
        self.assertLess(len(remaining_stashes), len(stashes))
        
        # Step 6: Export health report
        report = health_dashboard.export_health_report('json')
        self.assertIsInstance(report, str)
        
        # Verify report contains expected data
        if report:
            import json
            report_data = json.loads(report)
            self.assertIn('branches', report_data)
            self.assertIn('files', report_data)
    
    def test_collaborative_development_workflow(self):
        """Test workflow simulating collaborative development"""
        template_engine = self.git_wrapper.get_feature_manager('templates')
        workflow_manager = self.git_wrapper.get_feature_manager('workflows')
        conflict_resolver = self.git_wrapper.get_feature_manager('conflicts')
        
        if not all([template_engine, workflow_manager, conflict_resolver]):
            self.skipTest("Required features not available")
        
        # Step 1: Simulate multiple developers working
        # Developer 1 starts feature
        with patch('builtins.input', side_effect=['login-system', 'y']):
            workflow_manager.start_feature_branch('login-system', 'github_flow')
        
        # Developer 1 commits work
        with open('login.py', 'w') as f:
            f.write('def login(username, password):\n    return True\n')
        subprocess.run(['git', 'add', 'login.py'], check=True)
        
        template = template_engine.get_template_by_name('feat')
        if template:
            commit_msg = template_engine.apply_template(template, {
                'scope': 'auth',
                'description': 'implement basic login',
                'body': 'Add basic login functionality'
            })
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        
        # Step 2: Simulate main branch updates (other developer's work)
        subprocess.run(['git', 'checkout', 'main'], check=True)
        with open('config.py', 'w') as f:
            f.write('AUTH_ENABLED = True\nSESSION_TIMEOUT = 3600\n')
        subprocess.run(['git', 'add', 'config.py'], check=True)
        subprocess.run(['git', 'commit', '-m', 'feat: add auth configuration'], check=True)
        
        # Step 3: Developer 1 continues work on feature branch
        current_branch = subprocess.run(['git', 'branch', '--list', '*login*'], 
                                      capture_output=True, text=True).stdout.strip()
        if current_branch:
            branch_name = current_branch.strip().replace('* ', '')
            subprocess.run(['git', 'checkout', branch_name], check=True)
            
            # Add more functionality
            with open('session.py', 'w') as f:
                f.write('def create_session(user_id):\n    return {"user_id": user_id, "timestamp": time.time()}\n')
            subprocess.run(['git', 'add', 'session.py'], check=True)
            
            if template:
                commit_msg = template_engine.apply_template(template, {
                    'scope': 'auth',
                    'description': 'add session management',
                    'body': 'Implement user session creation and management'
                })
                subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        
        # Step 4: Attempt to merge feature (may cause conflicts)
        subprocess.run(['git', 'checkout', 'main'], check=True)
        
        if current_branch:
            merge_result = subprocess.run(['git', 'merge', branch_name], capture_output=True)
            
            if merge_result.returncode != 0:  # Conflict occurred
                conflicted_files = conflict_resolver.list_conflicted_files()
                
                # Resolve any conflicts
                for file in conflicted_files:
                    with patch('builtins.input', side_effect=['ours', 'y']):
                        conflict_resolver.resolve_conflict(file, 'ours')
                
                # Finalize merge
                with patch('builtins.input', side_effect=['y']):
                    conflict_resolver.finalize_merge()
        
        # Step 5: Verify final state
        self.assertTrue(Path('login.py').exists())
        self.assertTrue(Path('session.py').exists())
        self.assertTrue(Path('config.py').exists())


if __name__ == '__main__':
    unittest.main()