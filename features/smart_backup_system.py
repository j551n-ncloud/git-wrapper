#!/usr/bin/env python3
"""
Smart Backup System for Advanced Git Features

This module provides intelligent backup functionality for Git repositories,
including automated backups, multiple remote destinations, scheduling,
and backup restoration capabilities.
"""

import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse

from .base_manager import BaseFeatureManager


class SmartBackupSystem(BaseFeatureManager):
    """
    Smart Backup System for Git repositories.
    
    Features:
    - Multiple backup remote destinations
    - Manual and scheduled backups
    - Backup restoration with conflict detection
    - Backup version management
    - Cleanup and retention policies
    - Progress tracking and error handling
    """
    
    def __init__(self, git_wrapper):
        """Initialize the Smart Backup System."""
        super().__init__(git_wrapper)
        
        # Initialize backup-specific paths
        self.backup_log_file = Path.home() / '.gitwrapper_backups.log'
        self.backup_config_file = self._get_backup_config_path()
        
        # Load backup configuration
        self.backup_config = self._load_backup_config()
        
        # Initialize backup state
        self.backup_in_progress = False
        self.backup_thread = None
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for backup system."""
        return {
            'backup_remotes': [],
            'auto_backup_branches': ['main', 'master', 'develop'],
            'retention_days': 90,
            'max_backup_versions': 50,
            'backup_on_push': False,
            'backup_on_merge': False,
            'backup_schedule_enabled': False,
            'backup_schedule_hours': 24,
            'backup_timeout_minutes': 30,
            'verify_backups': True,
            'compress_backups': False
        }
    
    def _get_backup_config_path(self) -> Path:
        """Get the path for backup configuration file."""
        git_root = self.get_git_root()
        if git_root:
            return git_root / '.git' / 'gitwrapper_backup_config.json'
        return Path.cwd() / '.git' / 'gitwrapper_backup_config.json'
    
    def _load_backup_config(self) -> Dict[str, Any]:
        """Load backup configuration from file."""
        default_config = {
            'remotes': {},
            'schedules': {},
            'last_backup': {},
            'backup_history': []
        }
        
        return self.load_json_file(self.backup_config_file, default_config)
    
    def _save_backup_config(self) -> bool:
        """Save backup configuration to file."""
        return self.save_json_file(self.backup_config_file, self.backup_config)
    
    def interactive_menu(self) -> None:
        """Display the interactive backup system menu."""
        while True:
            self.show_feature_header("Smart Backup System")
            
            if not self.is_git_repo():
                self.print_error("This feature requires a Git repository!")
                input("\nPress Enter to return to main menu...")
                return
            
            # Show backup status
            self._show_backup_status()
            
            print(f"\n{self.format_with_emoji('Backup Options:', '📋')}")
            print(f"1. {self.format_with_emoji('Configure Backup Remotes', '🔧')}")
            print(f"2. {self.format_with_emoji('Create Manual Backup', '💾')}")
            print(f"3. {self.format_with_emoji('Schedule Automatic Backups', '📅')}")
            print(f"4. {self.format_with_emoji('Restore from Backup', '🔄')}")
            print(f"5. {self.format_with_emoji('View Backup History', '📊')}")
            print(f"6. {self.format_with_emoji('Cleanup Old Backups', '🧹')}")
            print(f"7. {self.format_with_emoji('Backup Settings', '⚙️')}")
            print(f"8. {self.format_with_emoji('Verify Backup Integrity', '🔍')}")
            print("0. ← Back to Main Menu")
            
            choice = self.get_input("\nSelect an option", "0")
            
            if choice == "1":
                self.configure_backup_remotes()
            elif choice == "2":
                self.create_manual_backup()
            elif choice == "3":
                self.configure_backup_schedule()
            elif choice == "4":
                self.restore_from_backup_menu()
            elif choice == "5":
                self.show_backup_history()
            elif choice == "6":
                self.cleanup_old_backups_menu()
            elif choice == "7":
                self.configure_backup_settings()
            elif choice == "8":
                self.verify_backup_integrity()
            elif choice == "0":
                break
            else:
                self.print_error("Invalid option. Please try again.")
                input("\nPress Enter to continue...")
    
    def _show_backup_status(self) -> None:
        """Show current backup status."""
        print(f"\n{self.format_with_emoji('Backup Status:', '📊')}")
        
        # Show configured remotes
        remotes = list(self.backup_config.get('remotes', {}).keys())
        if remotes:
            print(f"{self.format_with_emoji('Configured Remotes:', '🔗')} {', '.join(remotes)}")
        else:
            print(self.format_with_emoji("No backup remotes configured", "⚠️"))
        
        # Show last backup info
        last_backup = self.backup_config.get('last_backup', {})
        if last_backup:
            last_time = last_backup.get('timestamp')
            if last_time:
                formatted_time = self.format_timestamp(last_time)
                print(f"{self.format_with_emoji('Last Backup:', '⏰')} {formatted_time}")
                
                branches = last_backup.get('branches', [])
                if branches:
                    print(f"{self.format_with_emoji('Backed up Branches:', '🌿')} {', '.join(branches)}")
        else:
            print(self.format_with_emoji("No backups created yet", "📝"))
        
        # Show backup in progress status
        if self.backup_in_progress:
            print(self.format_with_emoji("Backup currently in progress...", "🔄"))
    
    def configure_backup_remotes(self) -> None:
        """Configure backup remote destinations."""
        self.show_feature_header("Configure Backup Remotes")
        
        while True:
            # Show current remotes
            remotes = self.backup_config.get('remotes', {})
            
            print(f"\n{self.format_with_emoji('Current Backup Remotes:', '🔗')}")
            if remotes:
                for name, config in remotes.items():
                    active_emoji = "✅" if config.get('enabled', True) else "❌"
                    status = self.format_with_emoji("Active", active_emoji) if config.get('enabled', True) else self.format_with_emoji("Disabled", active_emoji)
                    print(f"  • {name}: {config.get('url', 'N/A')} ({status})")
            else:
                print("  No backup remotes configured")
            
            print(f"\n{self.format_with_emoji('Remote Management:', '📋')}")
            print(f"1. {self.format_with_emoji('Add New Remote', '➕')}")
            print(f"2. {self.format_with_emoji('Edit Remote', '✏️')}")
            print(f"3. {self.format_with_emoji('Remove Remote', '🗑️')}")
            print(f"4. {self.format_with_emoji('Test Remote Connection', '🔍')}")
            print(f"5. {self.format_with_emoji('Enable/Disable Remote', '🔄')}")
            print("0. ← Back")
            
            choice = self.get_input("\nSelect an option", "0")
            
            if choice == "1":
                self._add_backup_remote()
            elif choice == "2":
                self._edit_backup_remote()
            elif choice == "3":
                self._remove_backup_remote()
            elif choice == "4":
                self._test_remote_connection()
            elif choice == "5":
                self._toggle_remote_status()
            elif choice == "0":
                break
            else:
                self.print_error("Invalid option. Please try again.")
                input("\nPress Enter to continue...")
    
    def _add_backup_remote(self) -> None:
        """Add a new backup remote."""
        print(f"\n{self.format_with_emoji('Add New Backup Remote', '➕')}")
        
        name = self.get_input("Remote name").strip()
        if not name:
            self.print_error("Remote name cannot be empty")
            return
        
        if name in self.backup_config.get('remotes', {}):
            self.print_error(f"Remote '{name}' already exists")
            return
        
        url = self.get_input("Remote URL (git clone URL)").strip()
        if not url:
            self.print_error("Remote URL cannot be empty")
            return
        
        # Validate URL format
        if not self._validate_git_url(url):
            self.print_error("Invalid Git URL format")
            return
        
        # Optional authentication
        auth_method = self.get_choice(
            "Authentication method",
            ["none", "ssh-key", "token"],
            "none"
        )
        
        auth_config = {}
        if auth_method == "ssh-key":
            key_path = self.get_input("SSH key path (optional)")
            if key_path:
                auth_config['ssh_key'] = key_path
        elif auth_method == "token":
            token = self.get_input("Access token (will be stored securely)")
            if token:
                auth_config['token'] = token
        
        # Create remote configuration
        remote_config = {
            'url': url,
            'enabled': True,
            'auth_method': auth_method,
            'auth_config': auth_config,
            'created_at': time.time(),
            'last_tested': None,
            'last_backup': None
        }
        
        # Save configuration
        if 'remotes' not in self.backup_config:
            self.backup_config['remotes'] = {}
        
        self.backup_config['remotes'][name] = remote_config
        
        if self._save_backup_config():
            self.print_success(f"Backup remote '{name}' added successfully")
            
            # Test connection
            if self.confirm("Test connection to new remote?", True):
                self._test_specific_remote(name)
        else:
            self.print_error("Failed to save backup configuration")
        
        input("\nPress Enter to continue...")
    
    def _validate_git_url(self, url: str) -> bool:
        """Validate Git URL format."""
        if not url:
            return False
        
        # Check for common Git URL patterns
        git_patterns = [
            url.startswith('https://'),
            url.startswith('http://'),
            url.startswith('git@'),
            url.startswith('ssh://'),
            url.startswith('file://'),
            url.startswith('/')  # Local path
        ]
        
        return any(git_patterns)
    
    def _edit_backup_remote(self) -> None:
        """Edit an existing backup remote."""
        remotes = self.backup_config.get('remotes', {})
        if not remotes:
            self.print_error("No backup remotes configured")
            input("\nPress Enter to continue...")
            return
        
        print(f"\n{self.format_with_emoji('Edit Backup Remote', '✏️')}")
        
        remote_names = list(remotes.keys())
        selected = self.get_choice("Select remote to edit", remote_names)
        
        if not selected:
            return
        
        remote_config = remotes[selected]
        
        print(f"\nEditing remote: {selected}")
        print(f"Current URL: {remote_config.get('url', 'N/A')}")
        
        # Edit URL
        new_url = self.get_input("New URL (press Enter to keep current)", remote_config.get('url', ''))
        if new_url and new_url != remote_config.get('url'):
            if self._validate_git_url(new_url):
                remote_config['url'] = new_url
                self.print_success("URL updated")
            else:
                self.print_error("Invalid URL format")
                return
        
        # Edit authentication
        current_auth = remote_config.get('auth_method', 'none')
        new_auth = self.get_choice(
            f"Authentication method (current: {current_auth})",
            ["none", "ssh-key", "token"],
            current_auth
        )
        
        if new_auth != current_auth:
            remote_config['auth_method'] = new_auth
            remote_config['auth_config'] = {}
            
            if new_auth == "ssh-key":
                key_path = self.get_input("SSH key path (optional)")
                if key_path:
                    remote_config['auth_config']['ssh_key'] = key_path
            elif new_auth == "token":
                token = self.get_input("Access token")
                if token:
                    remote_config['auth_config']['token'] = token
        
        # Save changes
        if self._save_backup_config():
            self.print_success(f"Remote '{selected}' updated successfully")
        else:
            self.print_error("Failed to save changes")
        
        input("\nPress Enter to continue...")
    
    def _remove_backup_remote(self) -> None:
        """Remove a backup remote."""
        remotes = self.backup_config.get('remotes', {})
        if not remotes:
            self.print_error("No backup remotes configured")
            input("\nPress Enter to continue...")
            return
        
        print(f"\n{self.format_with_emoji('Remove Backup Remote', '🗑️')}")
        
        remote_names = list(remotes.keys())
        selected = self.get_choice("Select remote to remove", remote_names)
        
        if not selected:
            return
        
        if self.confirm(f"Remove backup remote '{selected}'?", False):
            del self.backup_config['remotes'][selected]
            
            if self._save_backup_config():
                self.print_success(f"Remote '{selected}' removed successfully")
            else:
                self.print_error("Failed to save changes")
        
        input("\nPress Enter to continue...")
    
    def _test_remote_connection(self) -> None:
        """Test connection to backup remotes."""
        remotes = self.backup_config.get('remotes', {})
        if not remotes:
            self.print_error("No backup remotes configured")
            input("\nPress Enter to continue...")
            return
        
        print(f"\n{self.format_with_emoji('Test Remote Connection', '🔍')}")
        
        remote_names = ["all"] + list(remotes.keys())
        selected = self.get_choice("Select remote to test", remote_names)
        
        if not selected:
            return
        
        if selected == "all":
            for name in remotes.keys():
                self._test_specific_remote(name)
        else:
            self._test_specific_remote(selected)
        
        input("\nPress Enter to continue...")
    
    def _test_specific_remote(self, remote_name: str) -> bool:
        """Test connection to a specific remote."""
        remotes = self.backup_config.get('remotes', {})
        if remote_name not in remotes:
            self.print_error(f"Remote '{remote_name}' not found")
            return False
        
        remote_config = remotes[remote_name]
        url = remote_config.get('url')
        
        self.print_working(f"Testing connection to '{remote_name}'...")
        
        try:
            # Test with git ls-remote
            cmd = ['git', 'ls-remote', '--heads', url]
            result = self.run_git_command(cmd, capture_output=True, show_output=False)
            
            if result:
                self.print_success(f"{self.format_with_emoji('Connection to', '✅')} '{remote_name}' successful")
                remote_config['last_tested'] = time.time()
                remote_config['connection_status'] = 'success'
                self._save_backup_config()
                return True
            else:
                self.print_error(f"{self.format_with_emoji('Connection to', '❌')} '{remote_name}' failed")
                remote_config['connection_status'] = 'failed'
                remote_config['last_tested'] = time.time()
                self._save_backup_config()
                return False
                
        except Exception as e:
            self.print_error(f"{self.format_with_emoji('Error testing', '❌')} '{remote_name}': {str(e)}")
            remote_config['connection_status'] = 'error'
            remote_config['last_tested'] = time.time()
            self._save_backup_config()
            return False
    
    def _toggle_remote_status(self) -> None:
        """Enable or disable a backup remote."""
        remotes = self.backup_config.get('remotes', {})
        if not remotes:
            self.print_error("No backup remotes configured")
            input("\nPress Enter to continue...")
            return
        
        print(f"\n{self.format_with_emoji('Enable/Disable Remote', '🔄')}")
        
        remote_names = list(remotes.keys())
        selected = self.get_choice("Select remote", remote_names)
        
        if not selected:
            return
        
        remote_config = remotes[selected]
        current_status = remote_config.get('enabled', True)
        new_status = not current_status
        
        action = "enable" if new_status else "disable"
        if self.confirm(f"{action.capitalize()} remote '{selected}'?", True):
            remote_config['enabled'] = new_status
            
            if self._save_backup_config():
                status_text = "enabled" if new_status else "disabled"
                self.print_success(f"Remote '{selected}' {status_text}")
            else:
                self.print_error("Failed to save changes")
        
        input("\nPress Enter to continue...")
    
    def create_manual_backup(self) -> None:
        """Create a manual backup."""
        self.show_feature_header("Create Manual Backup")
        
        # Check if backup remotes are configured
        remotes = self.backup_config.get('remotes', {})
        enabled_remotes = {name: config for name, config in remotes.items() 
                          if config.get('enabled', True)}
        
        if not enabled_remotes:
            self.print_error("No enabled backup remotes configured")
            self.print_info("Please configure backup remotes first")
            input("\nPress Enter to continue...")
            return
        
        # Select branches to backup
        all_branches = self.get_branches()
        if not all_branches:
            self.print_error("No branches found in repository")
            input("\nPress Enter to continue...")
            return
        
        print(f"\n{self.format_with_emoji('Select Branches to Backup:', '🌿')}")
        auto_backup_branches = self.get_feature_config('auto_backup_branches')
        
        # Pre-select auto backup branches
        default_branches = [b for b in all_branches if b in auto_backup_branches]
        
        if self.confirm("Backup all branches?", False):
            selected_branches = all_branches
        else:
            selected_branches = self.get_multiple_choice(
                "Select branches to backup", 
                all_branches
            )
        
        if not selected_branches:
            self.print_error("No branches selected")
            input("\nPress Enter to continue...")
            return
        
        # Select backup remotes
        remote_names = list(enabled_remotes.keys())
        if len(remote_names) == 1:
            selected_remotes = remote_names
        else:
            if self.confirm("Backup to all remotes?", True):
                selected_remotes = remote_names
            else:
                selected_remotes = self.get_multiple_choice(
                    "Select backup remotes",
                    remote_names
                )
        
        if not selected_remotes:
            self.print_error("No remotes selected")
            input("\nPress Enter to continue...")
            return
        
        # Create backup
        backup_id = self._generate_backup_id()
        success = self.create_backup(selected_branches, selected_remotes, backup_id)
        
        if success:
            self.print_success("Manual backup completed successfully")
        else:
            self.print_error("Backup failed or completed with errors")
        
        input("\nPress Enter to continue...")
    
    def create_backup(self, branches: List[str], remotes: List[str], 
                     backup_id: str = None) -> bool:
        """
        Create a backup of specified branches to specified remotes.
        
        Args:
            branches: List of branch names to backup
            remotes: List of remote names to backup to
            backup_id: Optional backup identifier
            
        Returns:
            True if backup was successful, False otherwise
        """
        if self.backup_in_progress:
            self.print_error("Another backup is already in progress")
            return False
        
        self.backup_in_progress = True
        
        try:
            if not backup_id:
                backup_id = self._generate_backup_id()
            
            self.print_working(f"Starting backup {backup_id}...")
            
            backup_start_time = time.time()
            backup_results = {}
            overall_success = True
            
            # Create backup entry
            backup_entry = {
                'id': backup_id,
                'timestamp': backup_start_time,
                'branches': branches,
                'remotes': remotes,
                'status': 'in_progress',
                'results': {},
                'errors': []
            }
            
            # Add to backup history
            if 'backup_history' not in self.backup_config:
                self.backup_config['backup_history'] = []
            
            self.backup_config['backup_history'].append(backup_entry)
            self._save_backup_config()
            
            # Backup each branch to each remote
            total_operations = len(branches) * len(remotes)
            completed_operations = 0
            
            for remote_name in remotes:
                remote_config = self.backup_config['remotes'].get(remote_name)
                if not remote_config or not remote_config.get('enabled', True):
                    self.print_error(f"Remote '{remote_name}' is not available")
                    overall_success = False
                    continue
                
                backup_results[remote_name] = {}
                
                for branch in branches:
                    completed_operations += 1
                    progress = (completed_operations / total_operations) * 100
                    
                    self.print_working(
                        f"Backing up {branch} to {remote_name} "
                        f"({completed_operations}/{total_operations} - {progress:.1f}%)"
                    )
                    
                    success = self._backup_branch_to_remote(branch, remote_name, remote_config)
                    backup_results[remote_name][branch] = success
                    
                    if not success:
                        overall_success = False
                        error_msg = f"Failed to backup {branch} to {remote_name}"
                        backup_entry['errors'].append(error_msg)
            
            # Update backup entry
            backup_entry['status'] = 'completed' if overall_success else 'failed'
            backup_entry['results'] = backup_results
            backup_entry['duration'] = time.time() - backup_start_time
            
            # Update last backup info
            if overall_success:
                self.backup_config['last_backup'] = {
                    'id': backup_id,
                    'timestamp': backup_start_time,
                    'branches': branches,
                    'remotes': remotes
                }
            
            self._save_backup_config()
            self._log_backup_operation(backup_entry)
            
            if overall_success:
                self.print_success(f"Backup {backup_id} completed successfully")
            else:
                self.print_error(f"Backup {backup_id} completed with errors")
            
            return overall_success
            
        except Exception as e:
            self.print_error(f"Backup failed with exception: {str(e)}")
            return False
        finally:
            self.backup_in_progress = False
    
    def _generate_backup_id(self) -> str:
        """Generate a unique backup ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"backup_{timestamp}"
    
    def _backup_branch_to_remote(self, branch: str, remote_name: str, 
                                remote_config: Dict[str, Any]) -> bool:
        """
        Backup a specific branch to a specific remote.
        
        Args:
            branch: Branch name to backup
            remote_name: Remote name
            remote_config: Remote configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            remote_url = remote_config.get('url')
            if not remote_url:
                self.print_error(f"No URL configured for remote '{remote_name}'")
                return False
            
            # Check if branch exists locally
            if not self._branch_exists(branch):
                self.print_error(f"Branch '{branch}' does not exist locally")
                return False
            
            # Add remote temporarily if not already added
            temp_remote_name = f"backup_{remote_name}_{int(time.time())}"
            
            # Add temporary remote
            add_remote_cmd = ['git', 'remote', 'add', temp_remote_name, remote_url]
            if not self.run_git_command(add_remote_cmd, show_output=False):
                self.print_error(f"Failed to add temporary remote for {remote_name}")
                return False
            
            try:
                # Push branch to remote
                push_cmd = ['git', 'push', temp_remote_name, f"{branch}:{branch}"]
                
                # Add timeout
                timeout_minutes = self.get_feature_config('backup_timeout_minutes')
                if timeout_minutes:
                    import signal
                    
                    def timeout_handler(signum, frame):
                        raise TimeoutError("Backup operation timed out")
                    
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(timeout_minutes * 60)
                
                try:
                    success = self.run_git_command(push_cmd, show_output=False)
                    if timeout_minutes:
                        signal.alarm(0)  # Cancel timeout
                    
                    if success:
                        # Update remote's last backup time
                        remote_config['last_backup'] = time.time()
                        return True
                    else:
                        return False
                        
                except TimeoutError:
                    self.print_error(f"Backup of {branch} to {remote_name} timed out")
                    return False
                
            finally:
                # Remove temporary remote
                remove_remote_cmd = ['git', 'remote', 'remove', temp_remote_name]
                self.run_git_command(remove_remote_cmd, show_output=False)
            
        except Exception as e:
            self.print_error(f"Error backing up {branch} to {remote_name}: {str(e)}")
            return False
    
    def _branch_exists(self, branch: str) -> bool:
        """Check if a branch exists locally."""
        branches = self.get_branches()
        return branch in branches
    
    def _log_backup_operation(self, backup_entry: Dict[str, Any]) -> None:
        """Log backup operation to backup log file."""
        try:
            log_entry = {
                'timestamp': backup_entry['timestamp'],
                'id': backup_entry['id'],
                'status': backup_entry['status'],
                'branches': backup_entry['branches'],
                'remotes': backup_entry['remotes'],
                'duration': backup_entry.get('duration', 0),
                'errors': backup_entry.get('errors', [])
            }
            
            # Append to log file
            with open(self.backup_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            self.print_error(f"Failed to log backup operation: {str(e)}")
    
    def configure_backup_schedule(self) -> None:
        """Configure automatic backup scheduling."""
        self.show_feature_header("Configure Backup Schedule")
        
        while True:
            # Show current schedule status
            schedule_enabled = self.get_feature_config('backup_schedule_enabled')
            schedule_hours = self.get_feature_config('backup_schedule_hours')
            backup_on_push = self.get_feature_config('backup_on_push')
            backup_on_merge = self.get_feature_config('backup_on_merge')
            
            print(f"\n{self.format_with_emoji('Current Schedule Settings:', '📅')}")
            print(f"• Scheduled backups: {'Enabled' if schedule_enabled else 'Disabled'}")
            if schedule_enabled:
                print(f"• Backup interval: Every {schedule_hours} hours")
            print(f"• Backup on push: {'Yes' if backup_on_push else 'No'}")
            print(f"• Backup on merge: {'Yes' if backup_on_merge else 'No'}")
            
            print(f"\n{self.format_with_emoji('Schedule Options:', '📋')}")
            print(f"1. {self.format_with_emoji('Enable/Disable Scheduled Backups', '🔄')}")
            print(f"2. {self.format_with_emoji('Set Backup Interval', '⏰')}")
            print("3. 📤 Configure Backup on Push")
            print("4. 🔀 Configure Backup on Merge")
            print("5. ▶️  Start Backup Scheduler")
            print("6. ⏹️  Stop Backup Scheduler")
            print("7. 📊 View Schedule Status")
            print("0. ← Back")
            
            choice = self.get_input("\nSelect an option", "0")
            
            if choice == "1":
                self._toggle_scheduled_backups()
            elif choice == "2":
                self._configure_backup_interval()
            elif choice == "3":
                self._configure_backup_on_push()
            elif choice == "4":
                self._configure_backup_on_merge()
            elif choice == "5":
                self._start_backup_scheduler()
            elif choice == "6":
                self._stop_backup_scheduler()
            elif choice == "7":
                self._show_schedule_status()
            elif choice == "0":
                break
            else:
                self.print_error("Invalid option. Please try again.")
                input("\nPress Enter to continue...")
    
    def _toggle_scheduled_backups(self) -> None:
        """Toggle scheduled backup functionality."""
        current_enabled = self.get_feature_config('backup_schedule_enabled')
        new_enabled = not current_enabled
        
        self.set_feature_config('backup_schedule_enabled', new_enabled)
        
        status = "enabled" if new_enabled else "disabled"
        self.print_success(f"Scheduled backups {status}")
        
        if new_enabled:
            self.print_info("Use 'Start Backup Scheduler' to begin automatic backups")
        else:
            self.print_info("Automatic backups will stop at next check")
        
        input("\nPress Enter to continue...")
    
    def _configure_backup_interval(self) -> None:
        """Configure backup interval in hours."""
        current_hours = self.get_feature_config('backup_schedule_hours')
        print(f"\nCurrent backup interval: {current_hours} hours")
        
        new_hours = self.get_input("New backup interval (hours)", str(current_hours))
        
        try:
            hours = int(new_hours)
            if hours > 0:
                self.set_feature_config('backup_schedule_hours', hours)
                self.print_success(f"Backup interval set to {hours} hours")
            else:
                self.print_error("Interval must be positive")
        except ValueError:
            self.print_error("Invalid number format")
        
        input("\nPress Enter to continue...")
    
    def _configure_backup_on_push(self) -> None:
        """Configure backup on push events."""
        current_enabled = self.get_feature_config('backup_on_push')
        new_enabled = not current_enabled
        
        self.set_feature_config('backup_on_push', new_enabled)
        
        status = "enabled" if new_enabled else "disabled"
        self.print_success(f"Backup on push {status}")
        
        if new_enabled:
            self.print_info("Backups will be triggered after successful pushes")
        
        input("\nPress Enter to continue...")
    
    def _configure_backup_on_merge(self) -> None:
        """Configure backup on merge events."""
        current_enabled = self.get_feature_config('backup_on_merge')
        new_enabled = not current_enabled
        
        self.set_feature_config('backup_on_merge', new_enabled)
        
        status = "enabled" if new_enabled else "disabled"
        self.print_success(f"Backup on merge {status}")
        
        if new_enabled:
            self.print_info("Backups will be triggered after successful merges")
        
        input("\nPress Enter to continue...")
    
    def _start_backup_scheduler(self) -> None:
        """Start the backup scheduler."""
        if not self.get_feature_config('backup_schedule_enabled'):
            self.print_error("Scheduled backups are disabled")
            self.print_info("Enable scheduled backups first")
            input("\nPress Enter to continue...")
            return
        
        if self.backup_thread and self.backup_thread.is_alive():
            self.print_error("Backup scheduler is already running")
            input("\nPress Enter to continue...")
            return
        
        # Check if remotes are configured
        remotes = self.backup_config.get('remotes', {})
        enabled_remotes = {name: config for name, config in remotes.items() 
                          if config.get('enabled', True)}
        
        if not enabled_remotes:
            self.print_error("No backup remotes configured")
            self.print_info("Configure backup remotes first")
            input("\nPress Enter to continue...")
            return
        
        # Start scheduler thread
        self.backup_thread = threading.Thread(target=self._backup_scheduler_loop, daemon=True)
        self.backup_thread.start()
        
        self.print_success("Backup scheduler started")
        self.print_info("Scheduler is running in the background")
        
        input("\nPress Enter to continue...")
    
    def _stop_backup_scheduler(self) -> None:
        """Stop the backup scheduler."""
        if not self.backup_thread or not self.backup_thread.is_alive():
            self.print_error("Backup scheduler is not running")
            input("\nPress Enter to continue...")
            return
        
        # Set flag to stop scheduler
        self.set_feature_config('backup_schedule_enabled', False)
        
        self.print_success("Backup scheduler will stop at next check")
        self.print_info("Current backup operations will complete normally")
        
        input("\nPress Enter to continue...")
    
    def _show_schedule_status(self) -> None:
        """Show current scheduler status."""
        print("\n📊 Backup Scheduler Status:")
        
        schedule_enabled = self.get_feature_config('backup_schedule_enabled')
        print(f"• Scheduled backups: {'Enabled' if schedule_enabled else 'Disabled'}")
        
        if self.backup_thread and self.backup_thread.is_alive():
            print("• Scheduler thread: Running")
        else:
            print("• Scheduler thread: Stopped")
        
        if schedule_enabled:
            schedule_hours = self.get_feature_config('backup_schedule_hours')
            print(f"• Backup interval: Every {schedule_hours} hours")
            
            # Show next scheduled backup time
            last_backup = self.backup_config.get('last_backup', {})
            if last_backup and 'timestamp' in last_backup:
                next_backup_time = last_backup['timestamp'] + (schedule_hours * 3600)
                next_backup_dt = datetime.fromtimestamp(next_backup_time)
                print(f"• Next backup: {next_backup_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show event-based backup settings
        backup_on_push = self.get_feature_config('backup_on_push')
        backup_on_merge = self.get_feature_config('backup_on_merge')
        print(f"• Backup on push: {'Yes' if backup_on_push else 'No'}")
        print(f"• Backup on merge: {'Yes' if backup_on_merge else 'No'}")
        
        input("\nPress Enter to continue...")
    
    def _backup_scheduler_loop(self) -> None:
        """Main loop for the backup scheduler."""
        self.print_info("Backup scheduler started")
        
        while self.get_feature_config('backup_schedule_enabled'):
            try:
                schedule_hours = self.get_feature_config('backup_schedule_hours')
                
                # Check if it's time for a scheduled backup
                if self._should_run_scheduled_backup():
                    self.print_working("Running scheduled backup...")
                    
                    # Get auto-backup branches and enabled remotes
                    branches = self.get_feature_config('auto_backup_branches')
                    remotes = self._get_enabled_remotes()
                    
                    if branches and remotes:
                        backup_id = f"scheduled_{self._generate_backup_id()}"
                        success = self.create_backup(branches, remotes, backup_id)
                        
                        if success:
                            self.print_success("Scheduled backup completed")
                        else:
                            self.print_error("Scheduled backup failed")
                    else:
                        self.print_error("No branches or remotes configured for auto-backup")
                
                # Sleep for 1 hour before next check
                time.sleep(3600)
                
            except Exception as e:
                self.print_error(f"Scheduler error: {str(e)}")
                time.sleep(3600)  # Continue after error
        
        self.print_info("Backup scheduler stopped")
    
    def _should_run_scheduled_backup(self) -> bool:
        """Check if a scheduled backup should run."""
        last_backup = self.backup_config.get('last_backup', {})
        if not last_backup or 'timestamp' not in last_backup:
            return True  # No previous backup, run now
        
        schedule_hours = self.get_feature_config('backup_schedule_hours')
        time_since_last = time.time() - last_backup['timestamp']
        hours_since_last = time_since_last / 3600
        
        return hours_since_last >= schedule_hours
    
    def _get_enabled_remotes(self) -> List[str]:
        """Get list of enabled remote names."""
        remotes = self.backup_config.get('remotes', {})
        return [name for name, config in remotes.items() if config.get('enabled', True)]
    
    def trigger_event_backup(self, event_type: str) -> bool:
        """
        Trigger an event-based backup.
        
        Args:
            event_type: Type of event ('push', 'merge', etc.)
            
        Returns:
            True if backup was triggered and successful
        """
        if event_type == 'push' and not self.get_feature_config('backup_on_push'):
            return False
        
        if event_type == 'merge' and not self.get_feature_config('backup_on_merge'):
            return False
        
        # Don't trigger if another backup is in progress
        if self.backup_in_progress:
            self.print_info(f"Skipping {event_type} backup - another backup in progress")
            return False
        
        # Get current branch for event-based backup
        current_branch = self.get_current_branch()
        if not current_branch:
            return False
        
        # Get enabled remotes
        remotes = self._get_enabled_remotes()
        if not remotes:
            return False
        
        self.print_working(f"Triggering backup due to {event_type} event...")
        
        backup_id = f"{event_type}_{self._generate_backup_id()}"
        return self.create_backup([current_branch], remotes, backup_id)
    
    def restore_from_backup_menu(self) -> None:
        """Show backup restoration menu."""
        self.show_feature_header("Restore from Backup")
        
        while True:
            print("\n🔄 Backup Restoration Options:")
            print("1. 📋 List Available Backup Versions")
            print("2. 🔍 Compare Backup with Current State")
            print("3. ⬇️  Restore Branch from Backup")
            print("4. 📊 Show Backup Details")
            print("5. 🔄 Restore Multiple Branches")
            print("0. ← Back")
            
            choice = self.get_input("\nSelect an option", "0")
            
            if choice == "1":
                self.list_backup_versions()
            elif choice == "2":
                self.compare_backup_with_current()
            elif choice == "3":
                self.restore_single_branch()
            elif choice == "4":
                self.show_backup_details()
            elif choice == "5":
                self.restore_multiple_branches()
            elif choice == "0":
                break
            else:
                self.print_error("Invalid option. Please try again.")
                input("\nPress Enter to continue...")
    
    def list_backup_versions(self) -> List[Dict[str, Any]]:
        """
        List available backup versions.
        
        Returns:
            List of backup version information
        """
        self.show_feature_header("Available Backup Versions")
        
        backup_history = self.backup_config.get('backup_history', [])
        
        if not backup_history:
            self.print_info("No backup versions available")
            input("\nPress Enter to continue...")
            return []
        
        # Sort by timestamp (newest first)
        sorted_backups = sorted(backup_history, key=lambda x: x.get('timestamp', 0), reverse=True)
        
        print("\n📋 Available Backup Versions:")
        
        backup_versions = []
        for i, backup in enumerate(sorted_backups):
            timestamp = backup.get('timestamp', 0)
            formatted_time = self.format_timestamp(timestamp)
            
            backup_id = backup.get('id', 'Unknown')
            status = backup.get('status', 'Unknown')
            branches = backup.get('branches', [])
            remotes = backup.get('remotes', [])
            
            status_icon = "✅" if status == 'completed' else "❌" if status == 'failed' else "🔄"
            
            version_info = {
                'index': i + 1,
                'id': backup_id,
                'timestamp': timestamp,
                'formatted_time': formatted_time,
                'status': status,
                'branches': branches,
                'remotes': remotes,
                'backup_data': backup
            }
            
            backup_versions.append(version_info)
            
            print(f"\n{i+1}. {status_icon} {backup_id}")
            print(f"   📅 Created: {formatted_time}")
            print(f"   🌿 Branches: {', '.join(branches)}")
            print(f"   🔗 Remotes: {', '.join(remotes)}")
            
            if status == 'failed':
                errors = backup.get('errors', [])
                if errors:
                    print(f"   ⚠️  Errors: {len(errors)} issues")
        
        input("\nPress Enter to continue...")
        return backup_versions
    
    def compare_backup_with_current(self) -> None:
        """Compare a backup version with current repository state."""
        self.show_feature_header("Compare Backup with Current State")
        
        backup_versions = self.list_backup_versions()
        if not backup_versions:
            return
        
        # Select backup version
        version_choices = [f"{v['index']}. {v['id']}" for v in backup_versions]
        selected = self.get_choice("Select backup version to compare", version_choices)
        
        if not selected:
            return
        
        # Extract version index
        version_index = int(selected.split('.')[0]) - 1
        selected_backup = backup_versions[version_index]
        
        print(f"\n🔍 Comparing backup '{selected_backup['id']}' with current state...")
        
        # Compare each branch
        for branch in selected_backup['branches']:
            print(f"\n🌿 Branch: {branch}")
            
            # Check if branch exists locally
            if not self._branch_exists(branch):
                print(f"   ❌ Branch '{branch}' does not exist locally")
                continue
            
            # Get current branch commit
            current_commit = self._get_branch_commit(branch)
            if not current_commit:
                print(f"   ⚠️  Could not get current commit for '{branch}'")
                continue
            
            print(f"   📍 Current commit: {current_commit[:8]}")
            
            # Try to get backup commit from remotes
            backup_commits = self._get_backup_commits(branch, selected_backup['remotes'])
            
            if backup_commits:
                for remote, commit in backup_commits.items():
                    if commit:
                        print(f"   💾 Backup commit ({remote}): {commit[:8]}")
                        
                        if commit == current_commit:
                            print(f"   ✅ Branch '{branch}' is up to date with backup")
                        else:
                            print(f"   🔄 Branch '{branch}' differs from backup")
                            
                            # Show commit difference
                            ahead, behind = self._get_commit_difference(branch, commit)
                            if ahead is not None and behind is not None:
                                print(f"   📊 Local is {ahead} commits ahead, {behind} commits behind backup")
                    else:
                        print(f"   ⚠️  Could not access backup commit from {remote}")
            else:
                print(f"   ❌ Could not access backup commits for '{branch}'")
        
        input("\nPress Enter to continue...")
    
    def restore_single_branch(self) -> None:
        """Restore a single branch from backup."""
        self.show_feature_header("Restore Branch from Backup")
        
        backup_versions = self.list_backup_versions()
        if not backup_versions:
            return
        
        # Select backup version
        version_choices = [f"{v['index']}. {v['id']}" for v in backup_versions]
        selected = self.get_choice("Select backup version", version_choices)
        
        if not selected:
            return
        
        version_index = int(selected.split('.')[0]) - 1
        selected_backup = backup_versions[version_index]
        
        # Select branch to restore
        available_branches = selected_backup['branches']
        if len(available_branches) == 1:
            branch_to_restore = available_branches[0]
        else:
            branch_to_restore = self.get_choice("Select branch to restore", available_branches)
        
        if not branch_to_restore:
            return
        
        # Select remote to restore from
        available_remotes = selected_backup['remotes']
        if len(available_remotes) == 1:
            restore_remote = available_remotes[0]
        else:
            restore_remote = self.get_choice("Select remote to restore from", available_remotes)
        
        if not restore_remote:
            return
        
        # Perform restoration
        success = self.restore_from_backup(
            backup_id=selected_backup['id'],
            branch=branch_to_restore,
            remote=restore_remote
        )
        
        if success:
            self.print_success(f"Branch '{branch_to_restore}' restored successfully")
        else:
            self.print_error(f"Failed to restore branch '{branch_to_restore}'")
        
        input("\nPress Enter to continue...")
    
    def restore_multiple_branches(self) -> None:
        """Restore multiple branches from backup."""
        self.show_feature_header("Restore Multiple Branches")
        
        backup_versions = self.list_backup_versions()
        if not backup_versions:
            return
        
        # Select backup version
        version_choices = [f"{v['index']}. {v['id']}" for v in backup_versions]
        selected = self.get_choice("Select backup version", version_choices)
        
        if not selected:
            return
        
        version_index = int(selected.split('.')[0]) - 1
        selected_backup = backup_versions[version_index]
        
        # Select branches to restore
        available_branches = selected_backup['branches']
        branches_to_restore = self.get_multiple_choice("Select branches to restore", available_branches)
        
        if not branches_to_restore:
            return
        
        # Select remote to restore from
        available_remotes = selected_backup['remotes']
        if len(available_remotes) == 1:
            restore_remote = available_remotes[0]
        else:
            restore_remote = self.get_choice("Select remote to restore from", available_remotes)
        
        if not restore_remote:
            return
        
        # Confirm restoration
        if not self.confirm(f"Restore {len(branches_to_restore)} branches from backup '{selected_backup['id']}'?", False):
            return
        
        # Perform restoration for each branch
        successful_restorations = 0
        failed_restorations = 0
        
        for branch in branches_to_restore:
            self.print_working(f"Restoring branch '{branch}'...")
            
            success = self.restore_from_backup(
                backup_id=selected_backup['id'],
                branch=branch,
                remote=restore_remote
            )
            
            if success:
                successful_restorations += 1
                self.print_success(f"✅ Branch '{branch}' restored")
            else:
                failed_restorations += 1
                self.print_error(f"❌ Failed to restore branch '{branch}'")
        
        # Summary
        print(f"\n📊 Restoration Summary:")
        print(f"✅ Successful: {successful_restorations}")
        print(f"❌ Failed: {failed_restorations}")
        
        input("\nPress Enter to continue...")
    
    def restore_from_backup(self, backup_id: str, branch: str, remote: str) -> bool:
        """
        Restore a specific branch from a backup.
        
        Args:
            backup_id: Backup identifier
            branch: Branch name to restore
            remote: Remote name to restore from
            
        Returns:
            True if restoration was successful, False otherwise
        """
        try:
            # Get remote configuration
            remotes = self.backup_config.get('remotes', {})
            if remote not in remotes:
                self.print_error(f"Remote '{remote}' not found in configuration")
                return False
            
            remote_config = remotes[remote]
            remote_url = remote_config.get('url')
            
            if not remote_url:
                self.print_error(f"No URL configured for remote '{remote}'")
                return False
            
            # Check for conflicts with local changes
            if self._has_local_changes():
                if not self.confirm("You have local changes. Continue with restoration?", False):
                    return False
                
                # Offer to stash changes
                if self.confirm("Stash local changes before restoration?", True):
                    if not self._stash_local_changes():
                        self.print_error("Failed to stash local changes")
                        return False
            
            # Add temporary remote
            temp_remote_name = f"restore_{remote}_{int(time.time())}"
            
            add_remote_cmd = ['git', 'remote', 'add', temp_remote_name, remote_url]
            if not self.run_git_command(add_remote_cmd, show_output=False):
                self.print_error(f"Failed to add temporary remote")
                return False
            
            try:
                # Fetch from remote
                fetch_cmd = ['git', 'fetch', temp_remote_name, branch]
                if not self.run_git_command(fetch_cmd, show_output=False):
                    self.print_error(f"Failed to fetch branch '{branch}' from remote")
                    return False
                
                # Check if local branch exists
                local_branch_exists = self._branch_exists(branch)
                
                if local_branch_exists:
                    # Checkout the branch
                    checkout_cmd = ['git', 'checkout', branch]
                    if not self.run_git_command(checkout_cmd, show_output=False):
                        self.print_error(f"Failed to checkout branch '{branch}'")
                        return False
                    
                    # Reset to backup version
                    reset_cmd = ['git', 'reset', '--hard', f"{temp_remote_name}/{branch}"]
                    if not self.run_git_command(reset_cmd, show_output=False):
                        self.print_error(f"Failed to reset branch '{branch}' to backup version")
                        return False
                else:
                    # Create new branch from backup
                    checkout_cmd = ['git', 'checkout', '-b', branch, f"{temp_remote_name}/{branch}"]
                    if not self.run_git_command(checkout_cmd, show_output=False):
                        self.print_error(f"Failed to create branch '{branch}' from backup")
                        return False
                
                return True
                
            finally:
                # Remove temporary remote
                remove_remote_cmd = ['git', 'remote', 'remove', temp_remote_name]
                self.run_git_command(remove_remote_cmd, show_output=False)
            
        except Exception as e:
            self.print_error(f"Error during restoration: {str(e)}")
            return False
    
    def show_backup_details(self) -> None:
        """Show detailed information about a specific backup."""
        self.show_feature_header("Backup Details")
        
        backup_versions = self.list_backup_versions()
        if not backup_versions:
            return
        
        # Select backup version
        version_choices = [f"{v['index']}. {v['id']}" for v in backup_versions]
        selected = self.get_choice("Select backup to view details", version_choices)
        
        if not selected:
            return
        
        version_index = int(selected.split('.')[0]) - 1
        selected_backup = backup_versions[version_index]
        backup_data = selected_backup['backup_data']
        
        print(f"\n📊 Backup Details: {selected_backup['id']}")
        print("=" * 50)
        
        print(f"📅 Created: {selected_backup['formatted_time']}")
        print(f"⏱️  Duration: {backup_data.get('duration', 0):.1f} seconds")
        print(f"📊 Status: {selected_backup['status']}")
        
        print(f"\n🌿 Branches ({len(selected_backup['branches'])}):")
        for branch in selected_backup['branches']:
            print(f"  • {branch}")
        
        print(f"\n🔗 Remotes ({len(selected_backup['remotes'])}):")
        for remote in selected_backup['remotes']:
            print(f"  • {remote}")
        
        # Show results if available
        results = backup_data.get('results', {})
        if results:
            print(f"\n📋 Backup Results:")
            for remote, branch_results in results.items():
                print(f"  🔗 {remote}:")
                for branch, success in branch_results.items():
                    status_icon = "✅" if success else "❌"
                    print(f"    {status_icon} {branch}")
        
        # Show errors if any
        errors = backup_data.get('errors', [])
        if errors:
            print(f"\n⚠️  Errors ({len(errors)}):")
            for error in errors:
                print(f"  • {error}")
        
        input("\nPress Enter to continue...")
    
    def _get_branch_commit(self, branch: str) -> Optional[str]:
        """Get the current commit hash for a branch."""
        try:
            cmd = ['git', 'rev-parse', f"{branch}"]
            result = self.run_git_command(cmd, capture_output=True, show_output=False)
            return result.strip() if result else None
        except:
            return None
    
    def _get_backup_commits(self, branch: str, remotes: List[str]) -> Dict[str, Optional[str]]:
        """Get backup commit hashes for a branch from multiple remotes."""
        backup_commits = {}
        
        for remote_name in remotes:
            remote_config = self.backup_config.get('remotes', {}).get(remote_name)
            if not remote_config:
                backup_commits[remote_name] = None
                continue
            
            remote_url = remote_config.get('url')
            if not remote_url:
                backup_commits[remote_name] = None
                continue
            
            try:
                # Use git ls-remote to get remote branch commit
                cmd = ['git', 'ls-remote', remote_url, f"refs/heads/{branch}"]
                result = self.run_git_command(cmd, capture_output=True, show_output=False)
                
                if result:
                    # Parse commit hash from ls-remote output
                    lines = result.strip().split('\n')
                    for line in lines:
                        if f"refs/heads/{branch}" in line:
                            commit_hash = line.split('\t')[0]
                            backup_commits[remote_name] = commit_hash
                            break
                    else:
                        backup_commits[remote_name] = None
                else:
                    backup_commits[remote_name] = None
                    
            except:
                backup_commits[remote_name] = None
        
        return backup_commits
    
    def _get_commit_difference(self, branch: str, backup_commit: str) -> Tuple[Optional[int], Optional[int]]:
        """Get the number of commits ahead/behind between local branch and backup."""
        try:
            # Get commits ahead (local commits not in backup)
            ahead_cmd = ['git', 'rev-list', '--count', f"{backup_commit}..{branch}"]
            ahead_result = self.run_git_command(ahead_cmd, capture_output=True, show_output=False)
            ahead = int(ahead_result.strip()) if ahead_result else None
            
            # Get commits behind (backup commits not in local)
            behind_cmd = ['git', 'rev-list', '--count', f"{branch}..{backup_commit}"]
            behind_result = self.run_git_command(behind_cmd, capture_output=True, show_output=False)
            behind = int(behind_result.strip()) if behind_result else None
            
            return ahead, behind
            
        except:
            return None, None
    
    def _has_local_changes(self) -> bool:
        """Check if there are uncommitted local changes."""
        try:
            # Check for staged changes
            staged_cmd = ['git', 'diff', '--cached', '--quiet']
            staged_result = self.run_git_command(staged_cmd, capture_output=True, show_output=False)
            
            # Check for unstaged changes
            unstaged_cmd = ['git', 'diff', '--quiet']
            unstaged_result = self.run_git_command(unstaged_cmd, capture_output=True, show_output=False)
            
            # If either command fails, there are changes
            return not (staged_result and unstaged_result)
            
        except:
            return True  # Assume changes if we can't check
    
    def _stash_local_changes(self) -> bool:
        """Stash local changes."""
        try:
            stash_cmd = ['git', 'stash', 'push', '-m', 'Backup restoration stash']
            return self.run_git_command(stash_cmd, show_output=False)
        except:
            return False
    
    def show_backup_history(self) -> None:
        """Show backup history."""
        self.show_feature_header("Backup History")
        
        backup_history = self.backup_config.get('backup_history', [])
        
        if not backup_history:
            self.print_info("No backup history available")
            input("\nPress Enter to continue...")
            return
        
        print("\n📊 Recent Backups:")
        
        # Sort by timestamp (newest first)
        sorted_history = sorted(backup_history, key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # Show last 10 backups
        for i, backup in enumerate(sorted_history[:10]):
            timestamp = backup.get('timestamp', 0)
            formatted_time = self.format_timestamp(timestamp)
            
            backup_id = backup.get('id', 'Unknown')
            status = backup.get('status', 'Unknown')
            branches = backup.get('branches', [])
            remotes = backup.get('remotes', [])
            duration = backup.get('duration', 0)
            
            status_icon = "✅" if status == 'completed' else "❌" if status == 'failed' else "🔄"
            
            print(f"\n{i+1}. {status_icon} {backup_id}")
            print(f"   📅 Time: {formatted_time}")
            print(f"   🌿 Branches: {', '.join(branches)}")
            print(f"   🔗 Remotes: {', '.join(remotes)}")
            print(f"   ⏱️  Duration: {duration:.1f}s")
            
            errors = backup.get('errors', [])
            if errors:
                print(f"   ⚠️  Errors: {len(errors)}")
        
        if len(sorted_history) > 10:
            print(f"\n... and {len(sorted_history) - 10} more backups")
        
        input("\nPress Enter to continue...")
    
    def cleanup_old_backups_menu(self) -> None:
        """Show backup cleanup menu."""
        self.show_feature_header("Cleanup Old Backups")
        
        while True:
            # Show cleanup statistics
            self._show_cleanup_statistics()
            
            print("\n🧹 Cleanup Options:")
            print("1. 🗓️  Clean by Retention Policy")
            print("2. ❌ Clean Failed Backups")
            print("3. 📊 Clean by Version Limit")
            print("4. 🔍 Preview Cleanup Actions")
            print("5. ⚙️  Configure Cleanup Settings")
            print("6. 🧹 Run Full Cleanup")
            print("0. ← Back")
            
            choice = self.get_input("\nSelect an option", "0")
            
            if choice == "1":
                self.cleanup_by_retention_policy()
            elif choice == "2":
                self.cleanup_failed_backups()
            elif choice == "3":
                self.cleanup_by_version_limit()
            elif choice == "4":
                self.preview_cleanup_actions()
            elif choice == "5":
                self.configure_cleanup_settings()
            elif choice == "6":
                self.run_full_cleanup()
            elif choice == "0":
                break
            else:
                self.print_error("Invalid option. Please try again.")
                input("\nPress Enter to continue...")
    
    def _show_cleanup_statistics(self) -> None:
        """Show current backup cleanup statistics."""
        backup_history = self.backup_config.get('backup_history', [])
        
        if not backup_history:
            print("\n📊 No backups to analyze")
            return
        
        total_backups = len(backup_history)
        completed_backups = len([b for b in backup_history if b.get('status') == 'completed'])
        failed_backups = len([b for b in backup_history if b.get('status') == 'failed'])
        
        # Calculate age statistics
        current_time = time.time()
        retention_days = self.get_feature_config('retention_days')
        old_backups = []
        
        for backup in backup_history:
            backup_time = backup.get('timestamp', 0)
            age_days = (current_time - backup_time) / (24 * 3600)
            if age_days > retention_days:
                old_backups.append(backup)
        
        print(f"\n📊 Backup Statistics:")
        print(f"• Total backups: {total_backups}")
        print(f"• Completed: {completed_backups}")
        print(f"• Failed: {failed_backups}")
        print(f"• Older than {retention_days} days: {len(old_backups)}")
        
        # Show version limit status
        max_versions = self.get_feature_config('max_backup_versions')
        if total_backups > max_versions:
            excess_versions = total_backups - max_versions
            print(f"• Excess versions: {excess_versions} (limit: {max_versions})")
    
    def cleanup_by_retention_policy(self) -> None:
        """Clean up backups based on retention policy."""
        self.show_feature_header("Cleanup by Retention Policy")
        
        retention_days = self.get_feature_config('retention_days')
        old_backups = self._get_old_backups(retention_days)
        
        if not old_backups:
            self.print_info(f"No backups older than {retention_days} days found")
            input("\nPress Enter to continue...")
            return
        
        print(f"\n🗓️  Found {len(old_backups)} backups older than {retention_days} days:")
        
        for backup in old_backups:
            timestamp = backup.get('timestamp', 0)
            formatted_time = self.format_timestamp(timestamp)
            age_days = (time.time() - timestamp) / (24 * 3600)
            
            print(f"• {backup.get('id', 'Unknown')} - {formatted_time} ({age_days:.1f} days old)")
        
        if self.confirm(f"Delete {len(old_backups)} old backups?", False):
            deleted_count = self.cleanup_old_backups(retention_days)
            self.print_success(f"Deleted {deleted_count} old backups")
        
        input("\nPress Enter to continue...")
    
    def cleanup_failed_backups(self) -> None:
        """Clean up failed backup entries."""
        self.show_feature_header("Cleanup Failed Backups")
        
        failed_backups = self._get_failed_backups()
        
        if not failed_backups:
            self.print_info("No failed backups found")
            input("\nPress Enter to continue...")
            return
        
        print(f"\n❌ Found {len(failed_backups)} failed backups:")
        
        for backup in failed_backups:
            timestamp = backup.get('timestamp', 0)
            formatted_time = self.format_timestamp(timestamp)
            errors = backup.get('errors', [])
            
            print(f"• {backup.get('id', 'Unknown')} - {formatted_time}")
            if errors:
                print(f"  Errors: {len(errors)}")
        
        if self.confirm(f"Delete {len(failed_backups)} failed backup entries?", False):
            deleted_count = self._delete_backup_entries(failed_backups)
            self.print_success(f"Deleted {deleted_count} failed backup entries")
        
        input("\nPress Enter to continue...")
    
    def cleanup_by_version_limit(self) -> None:
        """Clean up backups exceeding version limit."""
        self.show_feature_header("Cleanup by Version Limit")
        
        max_versions = self.get_feature_config('max_backup_versions')
        backup_history = self.backup_config.get('backup_history', [])
        
        if len(backup_history) <= max_versions:
            self.print_info(f"Backup count ({len(backup_history)}) is within limit ({max_versions})")
            input("\nPress Enter to continue...")
            return
        
        # Sort by timestamp (newest first) and keep only the newest max_versions
        sorted_backups = sorted(backup_history, key=lambda x: x.get('timestamp', 0), reverse=True)
        excess_backups = sorted_backups[max_versions:]
        
        print(f"\n📊 Found {len(excess_backups)} backups exceeding version limit ({max_versions}):")
        
        for backup in excess_backups:
            timestamp = backup.get('timestamp', 0)
            formatted_time = self.format_timestamp(timestamp)
            
            print(f"• {backup.get('id', 'Unknown')} - {formatted_time}")
        
        if self.confirm(f"Delete {len(excess_backups)} excess backup entries?", False):
            deleted_count = self._delete_backup_entries(excess_backups)
            self.print_success(f"Deleted {deleted_count} excess backup entries")
        
        input("\nPress Enter to continue...")
    
    def preview_cleanup_actions(self) -> None:
        """Preview what cleanup actions would be performed."""
        self.show_feature_header("Preview Cleanup Actions")
        
        retention_days = self.get_feature_config('retention_days')
        max_versions = self.get_feature_config('max_backup_versions')
        
        old_backups = self._get_old_backups(retention_days)
        failed_backups = self._get_failed_backups()
        
        backup_history = self.backup_config.get('backup_history', [])
        sorted_backups = sorted(backup_history, key=lambda x: x.get('timestamp', 0), reverse=True)
        excess_backups = sorted_backups[max_versions:] if len(sorted_backups) > max_versions else []
        
        print("\n🔍 Cleanup Preview:")
        
        if old_backups:
            print(f"\n🗓️  Retention Policy Cleanup ({retention_days} days):")
            for backup in old_backups:
                timestamp = backup.get('timestamp', 0)
                age_days = (time.time() - timestamp) / (24 * 3600)
                print(f"  • {backup.get('id', 'Unknown')} ({age_days:.1f} days old)")
        else:
            print(f"\n🗓️  No backups older than {retention_days} days")
        
        if failed_backups:
            print(f"\n❌ Failed Backup Cleanup:")
            for backup in failed_backups:
                print(f"  • {backup.get('id', 'Unknown')} (failed)")
        else:
            print(f"\n❌ No failed backups to clean")
        
        if excess_backups:
            print(f"\n📊 Version Limit Cleanup (keeping {max_versions}):")
            for backup in excess_backups:
                print(f"  • {backup.get('id', 'Unknown')} (excess)")
        else:
            print(f"\n📊 Backup count within version limit ({max_versions})")
        
        # Calculate total actions
        total_actions = len(set(
            [b.get('id') for b in old_backups] +
            [b.get('id') for b in failed_backups] +
            [b.get('id') for b in excess_backups]
        ))
        
        print(f"\n📋 Total backup entries to be cleaned: {total_actions}")
        
        input("\nPress Enter to continue...")
    
    def configure_cleanup_settings(self) -> None:
        """Configure cleanup settings."""
        self.show_feature_header("Configure Cleanup Settings")
        
        while True:
            retention_days = self.get_feature_config('retention_days')
            max_versions = self.get_feature_config('max_backup_versions')
            
            print(f"\n⚙️  Current Cleanup Settings:")
            print(f"• Retention period: {retention_days} days")
            print(f"• Max backup versions: {max_versions}")
            
            print(f"\n📋 Configuration Options:")
            print("1. 🗓️  Set Retention Period")
            print("2. 📊 Set Max Backup Versions")
            print("3. 🔄 Reset to Defaults")
            print("0. ← Back")
            
            choice = self.get_input("\nSelect an option", "0")
            
            if choice == "1":
                self._configure_retention_period()
            elif choice == "2":
                self._configure_max_versions()
            elif choice == "3":
                self._reset_cleanup_settings()
            elif choice == "0":
                break
            else:
                self.print_error("Invalid option. Please try again.")
                input("\nPress Enter to continue...")
    
    def run_full_cleanup(self) -> None:
        """Run full cleanup with all policies."""
        self.show_feature_header("Full Backup Cleanup")
        
        if not self.confirm("Run full cleanup with all policies?", False):
            return
        
        total_deleted = 0
        
        # Cleanup by retention policy
        retention_days = self.get_feature_config('retention_days')
        deleted_old = self.cleanup_old_backups(retention_days)
        total_deleted += deleted_old
        
        if deleted_old > 0:
            self.print_success(f"Deleted {deleted_old} old backups")
        
        # Cleanup failed backups
        failed_backups = self._get_failed_backups()
        if failed_backups:
            deleted_failed = self._delete_backup_entries(failed_backups)
            total_deleted += deleted_failed
            self.print_success(f"Deleted {deleted_failed} failed backup entries")
        
        # Cleanup by version limit
        max_versions = self.get_feature_config('max_backup_versions')
        backup_history = self.backup_config.get('backup_history', [])
        
        if len(backup_history) > max_versions:
            sorted_backups = sorted(backup_history, key=lambda x: x.get('timestamp', 0), reverse=True)
            excess_backups = sorted_backups[max_versions:]
            deleted_excess = self._delete_backup_entries(excess_backups)
            total_deleted += deleted_excess
            self.print_success(f"Deleted {deleted_excess} excess backup entries")
        
        if total_deleted > 0:
            self.print_success(f"Full cleanup completed - deleted {total_deleted} backup entries")
        else:
            self.print_info("No cleanup actions needed")
        
        input("\nPress Enter to continue...")
    
    def cleanup_old_backups(self, retention_days: int) -> int:
        """
        Clean up backups older than retention period.
        
        Args:
            retention_days: Number of days to retain backups
            
        Returns:
            Number of backups deleted
        """
        old_backups = self._get_old_backups(retention_days)
        return self._delete_backup_entries(old_backups)
    
    def _get_old_backups(self, retention_days: int) -> List[Dict[str, Any]]:
        """Get backups older than retention period."""
        backup_history = self.backup_config.get('backup_history', [])
        current_time = time.time()
        retention_seconds = retention_days * 24 * 3600
        
        old_backups = []
        for backup in backup_history:
            backup_time = backup.get('timestamp', 0)
            if (current_time - backup_time) > retention_seconds:
                old_backups.append(backup)
        
        return old_backups
    
    def _get_failed_backups(self) -> List[Dict[str, Any]]:
        """Get failed backup entries."""
        backup_history = self.backup_config.get('backup_history', [])
        return [backup for backup in backup_history if backup.get('status') == 'failed']
    
    def _delete_backup_entries(self, backups_to_delete: List[Dict[str, Any]]) -> int:
        """
        Delete backup entries from history.
        
        Args:
            backups_to_delete: List of backup entries to delete
            
        Returns:
            Number of entries actually deleted
        """
        if not backups_to_delete:
            return 0
        
        backup_history = self.backup_config.get('backup_history', [])
        backup_ids_to_delete = {backup.get('id') for backup in backups_to_delete}
        
        # Filter out backups to delete
        original_count = len(backup_history)
        self.backup_config['backup_history'] = [
            backup for backup in backup_history 
            if backup.get('id') not in backup_ids_to_delete
        ]
        
        deleted_count = original_count - len(self.backup_config['backup_history'])
        
        # Save updated configuration
        if deleted_count > 0:
            self._save_backup_config()
        
        return deleted_count
    
    def _reset_cleanup_settings(self) -> None:
        """Reset cleanup settings to defaults."""
        default_config = self._get_default_config()
        
        self.set_feature_config('retention_days', default_config['retention_days'])
        self.set_feature_config('max_backup_versions', default_config['max_backup_versions'])
        
        self.print_success("Cleanup settings reset to defaults")
        input("\nPress Enter to continue...")
    
    def verify_backup_integrity(self) -> None:
        """Verify backup integrity."""
        self.show_feature_header("Verify Backup Integrity")
        
        if not self.get_feature_config('verify_backups'):
            self.print_info("Backup verification is disabled")
            if self.confirm("Enable backup verification?", True):
                self.set_feature_config('verify_backups', True)
                self.print_success("Backup verification enabled")
            else:
                input("\nPress Enter to continue...")
                return
        
        backup_history = self.backup_config.get('backup_history', [])
        completed_backups = [b for b in backup_history if b.get('status') == 'completed']
        
        if not completed_backups:
            self.print_info("No completed backups to verify")
            input("\nPress Enter to continue...")
            return
        
        print(f"\n🔍 Verifying {len(completed_backups)} completed backups...")
        
        verification_results = []
        
        for i, backup in enumerate(completed_backups):
            backup_id = backup.get('id', 'Unknown')
            self.print_working(f"Verifying backup {i+1}/{len(completed_backups)}: {backup_id}")
            
            result = self._verify_single_backup(backup)
            verification_results.append({
                'backup_id': backup_id,
                'result': result,
                'backup': backup
            })
        
        # Show verification results
        print(f"\n📊 Verification Results:")
        
        successful_verifications = 0
        failed_verifications = 0
        
        for result in verification_results:
            backup_id = result['backup_id']
            success = result['result']['success']
            
            if success:
                successful_verifications += 1
                print(f"✅ {backup_id}: Verified")
            else:
                failed_verifications += 1
                print(f"❌ {backup_id}: Failed")
                
                errors = result['result'].get('errors', [])
                for error in errors:
                    print(f"   • {error}")
        
        print(f"\n📋 Summary:")
        print(f"✅ Successful: {successful_verifications}")
        print(f"❌ Failed: {failed_verifications}")
        
        if failed_verifications > 0:
            if self.confirm("Remove failed backup entries from history?", False):
                failed_backups = [r['backup'] for r in verification_results if not r['result']['success']]
                deleted_count = self._delete_backup_entries(failed_backups)
                self.print_success(f"Removed {deleted_count} failed backup entries")
        
        input("\nPress Enter to continue...")
    
    def _verify_single_backup(self, backup: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify a single backup's integrity.
        
        Args:
            backup: Backup entry to verify
            
        Returns:
            Verification result dictionary
        """
        result = {
            'success': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            backup_id = backup.get('id', 'Unknown')
            branches = backup.get('branches', [])
            remotes = backup.get('remotes', [])
            
            # Verify backup has required fields
            if not backup_id or backup_id == 'Unknown':
                result['errors'].append("Missing or invalid backup ID")
                result['success'] = False
            
            if not branches:
                result['errors'].append("No branches in backup")
                result['success'] = False
            
            if not remotes:
                result['errors'].append("No remotes in backup")
                result['success'] = False
            
            # Verify remote accessibility
            for remote_name in remotes:
                remote_config = self.backup_config.get('remotes', {}).get(remote_name)
                
                if not remote_config:
                    result['errors'].append(f"Remote '{remote_name}' configuration not found")
                    result['success'] = False
                    continue
                
                if not remote_config.get('enabled', True):
                    result['warnings'].append(f"Remote '{remote_name}' is disabled")
                    continue
                
                # Test remote connectivity
                if not self._test_specific_remote(remote_name):
                    result['errors'].append(f"Cannot connect to remote '{remote_name}'")
                    result['success'] = False
            
            # Verify backup results if available
            backup_results = backup.get('results', {})
            if backup_results:
                for remote_name, branch_results in backup_results.items():
                    for branch, success in branch_results.items():
                        if not success:
                            result['warnings'].append(f"Branch '{branch}' failed to backup to '{remote_name}'")
            
            # Check for errors in backup
            backup_errors = backup.get('errors', [])
            if backup_errors:
                result['warnings'].extend([f"Backup error: {error}" for error in backup_errors])
            
        except Exception as e:
            result['errors'].append(f"Verification exception: {str(e)}")
            result['success'] = False
        
        return result
    
    def configure_backup_settings(self) -> None:
        """Configure backup system settings."""
        self.show_feature_header("Backup Settings")
        
        while True:
            current_config = self.get_feature_config()
            
            print("\n⚙️  Current Settings:")
            print(f"• Auto-backup branches: {', '.join(current_config.get('auto_backup_branches', []))}")
            print(f"• Retention days: {current_config.get('retention_days', 90)}")
            print(f"• Max backup versions: {current_config.get('max_backup_versions', 50)}")
            print(f"• Backup timeout: {current_config.get('backup_timeout_minutes', 30)} minutes")
            print(f"• Verify backups: {'Yes' if current_config.get('verify_backups', True) else 'No'}")
            
            print("\n📋 Settings Options:")
            print("1. 🌿 Configure Auto-backup Branches")
            print("2. 📅 Set Retention Period")
            print("3. 📊 Set Max Backup Versions")
            print("4. ⏱️  Set Backup Timeout")
            print("5. ✅ Toggle Backup Verification")
            print("0. ← Back")
            
            choice = self.get_input("\nSelect an option", "0")
            
            if choice == "1":
                self._configure_auto_backup_branches()
            elif choice == "2":
                self._configure_retention_period()
            elif choice == "3":
                self._configure_max_versions()
            elif choice == "4":
                self._configure_backup_timeout()
            elif choice == "5":
                self._toggle_backup_verification()
            elif choice == "0":
                break
            else:
                self.print_error("Invalid option. Please try again.")
                input("\nPress Enter to continue...")
    
    def _configure_auto_backup_branches(self) -> None:
        """Configure branches for automatic backup."""
        print("\n🌿 Configure Auto-backup Branches")
        
        all_branches = self.get_branches()
        if not all_branches:
            self.print_error("No branches found in repository")
            return
        
        current_branches = self.get_feature_config('auto_backup_branches')
        
        print(f"Current auto-backup branches: {', '.join(current_branches)}")
        
        new_branches = self.get_multiple_choice(
            "Select branches for automatic backup",
            all_branches
        )
        
        if new_branches:
            self.set_feature_config('auto_backup_branches', new_branches)
            self.print_success("Auto-backup branches updated")
        
        input("\nPress Enter to continue...")
    
    def _configure_retention_period(self) -> None:
        """Configure backup retention period."""
        print("\n📅 Configure Retention Period")
        
        current_days = self.get_feature_config('retention_days')
        print(f"Current retention period: {current_days} days")
        
        new_days = self.get_input(f"New retention period in days", str(current_days))
        
        try:
            days = int(new_days)
            if days > 0:
                self.set_feature_config('retention_days', days)
                self.print_success(f"Retention period set to {days} days")
            else:
                self.print_error("Retention period must be positive")
        except ValueError:
            self.print_error("Invalid number format")
        
        input("\nPress Enter to continue...")
    
    def _configure_max_versions(self) -> None:
        """Configure maximum backup versions."""
        print("\n📊 Configure Max Backup Versions")
        
        current_max = self.get_feature_config('max_backup_versions')
        print(f"Current max versions: {current_max}")
        
        new_max = self.get_input(f"New max backup versions", str(current_max))
        
        try:
            max_versions = int(new_max)
            if max_versions > 0:
                self.set_feature_config('max_backup_versions', max_versions)
                self.print_success(f"Max backup versions set to {max_versions}")
            else:
                self.print_error("Max versions must be positive")
        except ValueError:
            self.print_error("Invalid number format")
        
        input("\nPress Enter to continue...")
    
    def _configure_backup_timeout(self) -> None:
        """Configure backup operation timeout."""
        print("\n⏱️  Configure Backup Timeout")
        
        current_timeout = self.get_feature_config('backup_timeout_minutes')
        print(f"Current timeout: {current_timeout} minutes")
        
        new_timeout = self.get_input(f"New timeout in minutes", str(current_timeout))
        
        try:
            timeout = int(new_timeout)
            if timeout > 0:
                self.set_feature_config('backup_timeout_minutes', timeout)
                self.print_success(f"Backup timeout set to {timeout} minutes")
            else:
                self.print_error("Timeout must be positive")
        except ValueError:
            self.print_error("Invalid number format")
        
        input("\nPress Enter to continue...")
    
    def _toggle_backup_verification(self) -> None:
        """Toggle backup verification setting."""
        current_verify = self.get_feature_config('verify_backups')
        new_verify = not current_verify
        
        self.set_feature_config('verify_backups', new_verify)
        
        status = "enabled" if new_verify else "disabled"
        self.print_success(f"Backup verification {status}")
        
        input("\nPress Enter to continue...")
    
    def verify_backup_integrity(self) -> None:
        """Verify backup integrity."""
        self.show_feature_header("Verify Backup Integrity")
        
        print("🚧 Backup verification feature coming soon!")
        print("This will allow you to:")
        print("• Verify backup completeness")
        print("• Check backup data integrity")
        print("• Validate backup accessibility")
        print("• Generate integrity reports")
        
        input("\nPress Enter to continue...")