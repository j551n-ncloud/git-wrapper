#!/usr/bin/env python3
"""
Interactive Git Wrapper - A user-friendly interface for Git operations
Usage: gw [command] or just gw for interactive mode
"""

import subprocess
import sys
import os
import json
import time
from pathlib import Path

class InteractiveGitWrapper:
    def __init__(self):
        self.config_file = Path.home() / '.gitwrapper_config.json'
        self.load_config()
        self.check_git_available()
    
    def load_config(self):
        """Load user configuration"""
        self.config = {
            'name': '', 'email': '', 'default_branch': 'main',
            'auto_push': True, 'show_emoji': True, 'default_remote': 'origin'
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self.config.update(json.load(f))
            except (json.JSONDecodeError, IOError):
                pass
    
    def save_config(self):
        """Save user configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except IOError:
            self.print_error("Could not save configuration")
    
    def print_success(self, message):
        emoji = "✅ " if self.config['show_emoji'] else ""
        print(f"{emoji}{message}")
    
    def print_error(self, message):
        emoji = "❌ " if self.config['show_emoji'] else ""
        print(f"{emoji}{message}")
    
    def print_info(self, message):
        emoji = "ℹ️  " if self.config['show_emoji'] else ""
        print(f"{emoji}{message}")
    
    def print_working(self, message):
        emoji = "🔄 " if self.config['show_emoji'] else ""
        print(f"{emoji}{message}")
    
    def check_git_available(self):
        """Check if git is available"""
        try:
            subprocess.run(['git', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.print_error("Git is not installed or not available in PATH")
            sys.exit(1)
    
    def is_git_repo(self):
        """Check if current directory is a git repository"""
        try:
            subprocess.run(['git', 'rev-parse', '--git-dir'], 
                         capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def run_git_command(self, cmd, capture_output=False, show_output=True):
        """Run a git command and handle errors"""
        try:
            if capture_output:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return result.stdout.strip()
            else:
                if show_output:
                    subprocess.run(cmd, check=True)
                else:
                    subprocess.run(cmd, capture_output=True, check=True)
                return True
        except subprocess.CalledProcessError as e:
            self.print_error(f"Git command failed: {' '.join(cmd)}")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"Details: {e.stderr}")
            return False
    
    def get_input(self, prompt, default=None):
        """Get user input with optional default"""
        if default:
            user_input = input(f"{prompt} [{default}]: ").strip()
            return user_input if user_input else default
        return input(f"{prompt}: ").strip()
    
    def get_choice(self, prompt, choices, default=None):
        """Get user choice from a list"""
        print(f"\n{prompt}")
        for i, choice in enumerate(choices, 1):
            marker = " (default)" if default and choice == default else ""
            print(f"  {i}. {choice}{marker}")
        
        while True:
            try:
                choice_input = input("\nEnter choice number: ").strip()
                if not choice_input and default:
                    return default
                choice_num = int(choice_input)
                if 1 <= choice_num <= len(choices):
                    return choices[choice_num - 1]
                print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
    
    def get_multiple_choice(self, prompt, choices):
        """Get multiple choices from a list"""
        print(f"\n{prompt}")
        print("(Enter comma-separated numbers, e.g., 1,3,4)")
        for i, choice in enumerate(choices, 1):
            print(f"  {i}. {choice}")
        
        while True:
            try:
                choice_input = input("\nEnter choice numbers: ").strip()
                if not choice_input:
                    return []
                
                choice_nums = [int(x.strip()) for x in choice_input.split(',')]
                selected = []
                for num in choice_nums:
                    if 1 <= num <= len(choices):
                        selected.append(choices[num - 1])
                    else:
                        print(f"Invalid choice: {num}")
                        return []
                return selected
            except ValueError:
                print("Please enter valid numbers separated by commas.")
    
    def confirm(self, message, default=True):
        """Ask for confirmation"""
        suffix = "[Y/n]" if default else "[y/N]"
        response = input(f"{message} {suffix}: ").strip().lower()
        return response in ['y', 'yes'] if response else default
    
    def get_remotes(self):
        """Get list of remote repositories"""
        remotes_output = self.run_git_command(['git', 'remote'], capture_output=True)
        return remotes_output.split('\n') if remotes_output else []
    
    def show_main_menu(self):
        """Display the main interactive menu"""
        while True:
            self.clear_screen()
            repo_status = "🟢 Git Repository" if self.is_git_repo() else "🔴 Not a Git Repository"
            current_dir = os.path.basename(os.getcwd())
            
            print("=" * 50)
            print("🚀 Interactive Git Wrapper")
            print("=" * 50)
            print(f"📁 Directory: {current_dir}")
            print(f"📊 Status: {repo_status}")
            print("=" * 50)
            
            if self.is_git_repo():
                try:
                    branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
                    print(f"🌿 Current Branch: {branch}")
                    
                    status = self.run_git_command(['git', 'status', '--porcelain'], capture_output=True)
                    if status:
                        print(f"📝 Uncommitted Changes: {len(status.splitlines())} files")
                    else:
                        print("📝 Working Directory: Clean")
                    print("-" * 50)
                except:
                    pass
            
            # Menu options
            options = []
            if self.is_git_repo():
                options.extend([
                    "📊 Show Status", "💾 Quick Commit", "🔄 Sync (Pull & Push)",
                    "📤 Push Operations", "🌿 Branch Operations", "📋 View Changes", 
                    "📜 View History", "🔗 Remote Management"
                ])
            else:
                options.extend(["🎯 Initialize Repository", "📥 Clone Repository"])
            
            options.extend(["⚙️ Configuration", "❓ Help", "🚪 Exit"])
            
            for i, option in enumerate(options, 1):
                print(f"  {i}. {option}")
            
            try:
                choice = int(input(f"\nEnter your choice (1-{len(options)}): "))
                if 1 <= choice <= len(options):
                    self.handle_menu_choice(options[choice-1])
                else:
                    self.print_error("Invalid choice!")
                    time.sleep(1)
            except ValueError:
                self.print_error("Please enter a valid number!")
                time.sleep(1)
            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
    
    def handle_menu_choice(self, choice):
        """Handle menu selection"""
        handlers = {
            "Show Status": self.interactive_status,
            "Quick Commit": self.interactive_commit,
            "Sync": self.interactive_sync,
            "Push Operations": self.interactive_push_menu,
            "Branch Operations": self.interactive_branch_menu,
            "View Changes": self.interactive_diff,
            "View History": self.interactive_log,
            "Remote Management": self.interactive_remote_menu,
            "Initialize Repository": self.interactive_init,
            "Clone Repository": self.interactive_clone,
            "Configuration": self.interactive_config_menu,
            "Help": self.show_help,
            "Exit": lambda: (print("\nGoodbye! 👋"), sys.exit(0))
        }
        
        for key, handler in handlers.items():
            if key in choice:
                handler()
                break
    
    def interactive_status(self):
        """Interactive status display"""
        self.clear_screen()
        print("📊 Repository Status\n" + "=" * 30)
        
        branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        if branch:
            print(f"🌿 Current branch: {branch}")
        
        print("\n📝 Working Directory Status:")
        self.run_git_command(['git', 'status'])
        
        print(f"\n📜 Recent commits:")
        self.run_git_command(['git', 'log', '--oneline', '-5'])
        
        input("\nPress Enter to continue...")
    
    def interactive_commit(self):
        """Interactive commit process"""
        self.clear_screen()
        print("💾 Quick Commit\n" + "=" * 20)
        
        status = self.run_git_command(['git', 'status', '--porcelain'], capture_output=True)
        if not status:
            self.print_info("No changes to commit!")
            input("Press Enter to continue...")
            return
        
        print("Files to be added:")
        print(status)
        
        if not self.confirm("\nAdd all changes?", True):
            return
        
        message = self.get_input("\nEnter commit message")
        if not message:
            self.print_error("Commit message required!")
            input("Press Enter to continue...")
            return
        
        self.print_working("Adding all changes...")
        if not self.run_git_command(['git', 'add', '.'], show_output=False):
            input("Press Enter to continue...")
            return
        
        self.print_working(f"Committing with message: '{message}'")
        if self.run_git_command(['git', 'commit', '-m', message]):
            self.print_success("Commit successful!")
            
            if self.config['auto_push'] and self.confirm("Push to remote(s)?", True):
                self.interactive_push_menu()
        
        input("Press Enter to continue...")
    
    def interactive_push_menu(self):
        """Interactive push operations menu"""
        self.clear_screen()
        print("📤 Push Operations\n" + "=" * 20)
        
        remotes = self.get_remotes()
        if not remotes:
            self.print_error("No remotes configured!")
            input("Press Enter to continue...")
            return
        
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        print(f"Current branch: {current_branch or 'unknown'}")
        print(f"Available remotes: {', '.join(remotes)}")
        print("-" * 30)
        
        options = [
            "Push to single remote",
            "Push to multiple remotes",
            "Push to all remotes",
            "Back to main menu"
        ]
        
        choice = self.get_choice("Push Options:", options)
        
        if "single remote" in choice:
            self.interactive_push_single()
        elif "multiple remotes" in choice:
            self.interactive_push_multiple()
        elif "all remotes" in choice:
            self.interactive_push_all()
        elif "Back to main menu" in choice:
            return
    
    def interactive_push_single(self):
        """Push to a single selected remote"""
        remotes = self.get_remotes()
        if not remotes:
            return
        
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        branch = self.get_input("Branch to push", current_branch or self.config['default_branch'])
        
        default_remote = self.config.get('default_remote', 'origin')
        if default_remote not in remotes:
            default_remote = remotes[0]
        
        remote = self.get_choice("Select remote to push to:", remotes, default_remote)
        
        self.print_working(f"Pushing {branch} to {remote}...")
        if self.run_git_command(['git', 'push', remote, branch]):
            self.print_success(f"Successfully pushed to {remote}/{branch}!")
        
        input("Press Enter to continue...")
    
    def interactive_push_multiple(self):
        """Push to multiple selected remotes"""
        remotes = self.get_remotes()
        if not remotes:
            return
        
        if len(remotes) == 1:
            self.print_info("Only one remote available. Use single remote push instead.")
            input("Press Enter to continue...")
            return
        
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        branch = self.get_input("Branch to push", current_branch or self.config['default_branch'])
        
        selected_remotes = self.get_multiple_choice("Select remotes to push to:", remotes)
        
        if not selected_remotes:
            self.print_info("No remotes selected.")
            input("Press Enter to continue...")
            return
        
        self.print_info(f"Pushing {branch} to: {', '.join(selected_remotes)}")
        
        success_count = 0
        failed_remotes = []
        
        for remote in selected_remotes:
            self.print_working(f"Pushing to {remote}...")
            if self.run_git_command(['git', 'push', remote, branch], show_output=False):
                self.print_success(f"✓ Pushed to {remote}")
                success_count += 1
            else:
                self.print_error(f"✗ Failed to push to {remote}")
                failed_remotes.append(remote)
        
        print(f"\nSummary: {success_count}/{len(selected_remotes)} remotes successful")
        if failed_remotes:
            print(f"Failed remotes: {', '.join(failed_remotes)}")
        
        input("Press Enter to continue...")
    
    def interactive_push_all(self):
        """Push to all configured remotes"""
        remotes = self.get_remotes()
        if not remotes:
            return
        
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        branch = self.get_input("Branch to push", current_branch or self.config['default_branch'])
        
        if not self.confirm(f"Push {branch} to ALL {len(remotes)} remotes?", False):
            return
        
        self.print_info(f"Pushing {branch} to all remotes: {', '.join(remotes)}")
        
        success_count = 0
        failed_remotes = []
        
        for remote in remotes:
            self.print_working(f"Pushing to {remote}...")
            if self.run_git_command(['git', 'push', remote, branch], show_output=False):
                self.print_success(f"✓ Pushed to {remote}")
                success_count += 1
            else:
                self.print_error(f"✗ Failed to push to {remote}")
                failed_remotes.append(remote)
        
        print(f"\nSummary: {success_count}/{len(remotes)} remotes successful")
        if failed_remotes:
            print(f"Failed remotes: {', '.join(failed_remotes)}")
        
        input("Press Enter to continue...")
    
    def interactive_sync(self):
        """Interactive sync process"""
        self.clear_screen()
        print("🔄 Sync Repository\n" + "=" * 20)
        
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        branch = self.get_input("Branch to sync", current_branch or self.config['default_branch'])
        
        # Select remote for sync
        remotes = self.get_remotes()
        if not remotes:
            self.print_error("No remotes configured!")
            input("Press Enter to continue...")
            return
        
        default_remote = self.config.get('default_remote', 'origin')
        if default_remote not in remotes:
            default_remote = remotes[0]
        
        remote = self.get_choice("Select remote for sync:", remotes, default_remote)
        
        self.print_working(f"Syncing with {remote}/{branch}")
        
        # Pull and Push
        self.print_working("Pulling latest changes...")
        if not self.run_git_command(['git', 'pull', remote, branch]):
            input("Press Enter to continue...")
            return
        
        self.print_working("Pushing local commits...")
        if self.run_git_command(['git', 'push', remote, branch]):
            self.print_success("Sync completed successfully!")
        
        input("Press Enter to continue...")
    
    def interactive_remote_menu(self):
        """Interactive remote management menu"""
        while True:
            self.clear_screen()
            print("🔗 Remote Management\n" + "=" * 25)
            
            remotes = self.get_remotes()
            if remotes:
                print("Current remotes:")
                for remote in remotes:
                    url = self.run_git_command(['git', 'remote', 'get-url', remote], capture_output=True)
                    default_marker = f" (default)" if remote == self.config.get('default_remote') else ""
                    print(f"  {remote}: {url}{default_marker}")
                print()
            else:
                print("No remotes configured\n")
            
            options = [
                "Add remote", "Remove remote", "List remotes", 
                "Change remote URL", "Set default remote", "Back to main menu"
            ]
            
            choice = self.get_choice("Remote Operations:", options)
            
            if "Add remote" in choice:
                self.interactive_add_remote()
            elif "Remove remote" in choice:
                self.interactive_remove_remote()
            elif "List remotes" in choice:
                self.interactive_list_remotes()
            elif "Change remote URL" in choice:
                self.interactive_change_remote_url()
            elif "Set default remote" in choice:
                self.interactive_set_default_remote()
            elif "Back to main menu" in choice:
                break
    
    def interactive_set_default_remote(self):
        """Set default remote for operations"""
        remotes = self.get_remotes()
        if not remotes:
            self.print_info("No remotes configured")
            input("Press Enter to continue...")
            return
        
        current_default = self.config.get('default_remote', 'origin')
        remote = self.get_choice("Select default remote:", remotes, current_default)
        
        self.config['default_remote'] = remote
        self.save_config()
        self.print_success(f"Default remote set to: {remote}")
        
        input("Press Enter to continue...")
    
    def interactive_add_remote(self):
        """Add a new remote"""
        name = self.get_input("Remote name", "origin")
        if not name:
            return
    
        url = self.get_input("Remote URL")
        if not url:
            return
    
        self.print_working(f"Adding remote '{name}'...")
        if not self.run_git_command(['git', 'remote', 'add', name, url]):
            input("Press Enter to continue...")
            return
    
        self.print_success(f"Remote '{name}' added successfully!")
    
        # If this is the first remote, make it default
        remotes = self.get_remotes()
        if len(remotes) == 1:
            self.config['default_remote'] = name
            self.save_config()
            self.print_info(f"Set as default remote: {name}")
    
        # Ask if user wants to set upstream tracking for all branches
        if self.confirm(f"Set upstream tracking for all branches to '{name}'?", False):
            self.print_working("Setting upstream tracking for all branches...")
            if self.run_git_command(['git', 'push', '--set-upstream', name, '--all']):
                self.print_success("Upstream tracking set for all branches!")
            else:
                self.print_error("Failed to set upstream tracking")
    
        input("Press Enter to continue...")
    
    def interactive_remove_remote(self):
        """Remove an existing remote"""
        remotes = self.get_remotes()
        if not remotes:
            self.print_info("No remotes to remove")
            input("Press Enter to continue...")
            return
        
        remote = self.get_choice("Select remote to remove:", remotes)
        
        if self.confirm(f"Are you sure you want to remove remote '{remote}'?", False):
            if self.run_git_command(['git', 'remote', 'remove', remote]):
                self.print_success(f"Remote '{remote}' removed successfully!")
                
                # Update default remote if removed
                if self.config.get('default_remote') == remote:
                    remaining_remotes = self.get_remotes()
                    if remaining_remotes:
                        self.config['default_remote'] = remaining_remotes[0]
                        self.save_config()
                        self.print_info(f"Default remote changed to: {remaining_remotes[0]}")
                    else:
                        self.config['default_remote'] = 'origin'
                        self.save_config()
        
        input("Press Enter to continue...")
    
    def interactive_list_remotes(self):
        """List all remotes with details"""
        self.clear_screen()
        print("🔗 All Remotes\n" + "=" * 15)
        self.run_git_command(['git', 'remote', '-v'])
        input("\nPress Enter to continue...")
    
    def interactive_change_remote_url(self):
        """Change URL of existing remote"""
        remotes = self.get_remotes()
        if not remotes:
            self.print_info("No remotes configured")
            input("Press Enter to continue...")
            return
        
        remote = self.get_choice("Select remote to modify:", remotes)
        current_url = self.run_git_command(['git', 'remote', 'get-url', remote], capture_output=True)
        
        print(f"Current URL: {current_url}")
        new_url = self.get_input("New URL")
        if not new_url:
            return
        
        if self.run_git_command(['git', 'remote', 'set-url', remote, new_url]):
            self.print_success(f"URL for '{remote}' updated successfully!")
        
        input("Press Enter to continue...")
    
    def interactive_branch_menu(self):
        """Interactive branch operations menu"""
        while True:
            self.clear_screen()
            print("🌿 Branch Operations\n" + "=" * 25)
            
            current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
            if current_branch:
                print(f"Current branch: {current_branch}\n")
            
            options = [
                "Create new branch", "Switch to existing branch", "List all branches",
                "Delete branch", "Back to main menu"
            ]
            
            choice = self.get_choice("Branch Operations:", options)
            
            handlers = {
                "Create new branch": self.interactive_create_branch,
                "Switch to existing branch": self.interactive_switch_branch,
                "List all branches": self.interactive_list_branches,
                "Delete branch": self.interactive_delete_branch,
                "Back to main menu": lambda: None
            }
            
            for key, handler in handlers.items():
                if key in choice:
                    result = handler()
                    if key == "Back to main menu":
                        return
                    break
    
    def interactive_create_branch(self):
        """Interactive branch creation"""
        branch_name = self.get_input("Enter new branch name")
        if not branch_name:
            return
        
        self.print_working(f"Creating new branch: {branch_name}")
        if self.run_git_command(['git', 'checkout', '-b', branch_name]):
            self.print_success(f"Created and switched to branch: {branch_name}")
        
        input("Press Enter to continue...")
    
    def interactive_switch_branch(self):
        """Interactive branch switching"""
        branches_output = self.run_git_command(['git', 'branch'], capture_output=True)
        if not branches_output:
            return
        
        branches = [b.strip().replace('* ', '') for b in branches_output.split('\n') if b.strip()]
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        
        if len(branches) > 1:
            branches = [b for b in branches if b != current_branch]
        
        if not branches:
            self.print_info("No other branches available")
            input("Press Enter to continue...")
            return
        
        branch = self.get_choice("Select branch to switch to:", branches)
        
        self.print_working(f"Switching to branch: {branch}")
        if self.run_git_command(['git', 'checkout', branch]):
            self.print_success(f"Switched to branch: {branch}")
        
        input("Press Enter to continue...")
    
    def interactive_list_branches(self):
        """Interactive branch listing"""
        self.clear_screen()
        print("🌿 All Branches\n" + "=" * 15)
        self.run_git_command(['git', 'branch', '-a'])
        input("\nPress Enter to continue...")
    
    def interactive_delete_branch(self):
        """Interactive branch deletion"""
        branches_output = self.run_git_command(['git', 'branch'], capture_output=True)
        if not branches_output:
            return
        
        branches = [b.strip().replace('* ', '') for b in branches_output.split('\n') if b.strip()]
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        
        if len(branches) > 1:
            branches = [b for b in branches if b != current_branch]
        
        if not branches:
            self.print_info("No branches available to delete")
            input("Press Enter to continue...")
            return
        
        branch = self.get_choice("Select branch to delete:", branches)
        
        if self.confirm(f"Are you sure you want to delete branch '{branch}'?", False):
            if self.run_git_command(['git', 'branch', '-d', branch]):
                self.print_success(f"Deleted branch: {branch}")
        
        input("Press Enter to continue...")
    
    def interactive_diff(self):
        """Interactive diff viewing"""
        self.clear_screen()
        
        diff_type = self.get_choice("What changes to view?", 
                                  ["Unstaged changes", "Staged changes"])
        
        if "Staged" in diff_type:
            print("📋 Staged changes:")
            self.run_git_command(['git', 'diff', '--cached'])
        else:
            print("📋 Unstaged changes:")
            self.run_git_command(['git', 'diff'])
        
        input("\nPress Enter to continue...")
    
    def interactive_log(self):
        """Interactive log viewing"""
        self.clear_screen()
        
        try:
            count = int(self.get_input("Number of commits to show", "10"))
        except ValueError:
            count = 10
        
        print(f"📜 Last {count} commits:")
        self.run_git_command(['git', 'log', '--oneline', f'-{count}'])
        
        input("\nPress Enter to continue...")
    
    def interactive_init(self):
        """Interactive repository initialization"""
        self.clear_screen()
        print("🎯 Initialize Repository\n" + "=" * 25)
        
        if self.confirm("Initialize git repository in current directory?", True):
            self.print_working("Initializing repository...")
            if not self.run_git_command(['git', 'init']):
                input("Press Enter to continue...")
                return
            
            if self.config['name'] and self.config['email']:
                self.run_git_command(['git', 'config', 'user.name', self.config['name']], show_output=False)
                self.run_git_command(['git', 'config', 'user.email', self.config['email']], show_output=False)
                self.print_info("Applied your saved configuration")
            
            if self.confirm("Add remote origin?", False):
                remote_url = self.get_input("Remote URL")
                if remote_url:
                    if self.run_git_command(['git', 'remote', 'add', 'origin', remote_url]):
                        self.print_success("Remote origin added")
                        self.config['default_remote'] = 'origin'
                        self.save_config()
            
            self.print_success("Repository initialized successfully!")
        
        input("Press Enter to continue...")
    
    def interactive_clone(self):
        """Interactive repository cloning"""
        self.clear_screen()
        print("📥 Clone Repository\n" + "=" * 20)
        
        url = self.get_input("Repository URL")
        if not url:
            return
        
        directory = self.get_input("Directory name (optional)")
        
        cmd = ['git', 'clone', url]
        if directory:
            cmd.append(directory)
        
        self.print_working(f"Cloning repository: {url}")
        if self.run_git_command(cmd):
            self.print_success("Repository cloned successfully!")
            
            if directory and self.confirm("Change to cloned directory?", True):
                try:
                    os.chdir(directory)
                    self.print_success(f"Changed to directory: {directory}")
                except FileNotFoundError:
                    self.print_error("Could not change directory")
        
        input("Press Enter to continue...")
    
    def interactive_config_menu(self):
        """Interactive configuration menu"""
        while True:
            self.clear_screen()
            print("⚙️ Configuration\n" + "=" * 20)
            print(f"Name: {self.config['name'] or 'Not set'}")
            print(f"Email: {self.config['email'] or 'Not set'}")
            print(f"Default Branch: {self.config['default_branch']}")
            print(f"Default Remote: {self.config['default_remote']}")
            print(f"Auto Push: {self.config['auto_push']}")
            print(f"Show Emoji: {self.config['show_emoji']}")
            print("-" * 30)
            
            options = [
                "Set Name", "Set Email", "Set Default Branch", "Set Default Remote",
                "Toggle Auto Push", "Toggle Emoji", "Back to main menu"
            ]
            
            choice = self.get_choice("Configuration Options:", options)
            
            config_handlers = {
                "Set Name": lambda: self.update_config('name', self.get_input("Enter your name", self.config['name'])),
                "Set Email": lambda: self.update_config('email', self.get_input("Enter your email", self.config['email'])),
                "Set Default Branch": lambda: self.update_config('default_branch', self.get_input("Enter default branch", self.config['default_branch'])),
                "Set Default Remote": self.interactive_set_default_remote_config,
                "Toggle Auto Push": lambda: self.toggle_config('auto_push'),
                "Toggle Emoji": lambda: self.toggle_config('show_emoji'),
                "Back to main menu": lambda: None
            }
            
            for key, handler in config_handlers.items():
                if key in choice:
                    result = handler()
                    if key == "Back to main menu":
                        return
                    break
            
            if "Back to main menu" not in choice:
                time.sleep(1)
    
    def interactive_set_default_remote_config(self):
        """Set default remote from config menu"""
        if not self.is_git_repo():
            self.print_error("Not in a git repository")
            return
        
        remotes = self.get_remotes()
        if not remotes:
            self.print_info("No remotes configured in current repository")
            return
        
        current_default = self.config.get('default_remote', 'origin')
        remote = self.get_choice("Select default remote:", remotes, current_default)
        
        self.config['default_remote'] = remote
        self.save_config()
        self.print_success(f"Default remote set to: {remote}")
    
    def update_config(self, key, value):
        """Update configuration value"""
        if value:
            self.config[key] = value
            self.save_config()
            self.print_success(f"{key.replace('_', ' ').title()} updated!")
    
    def toggle_config(self, key):
        """Toggle boolean configuration value"""
        self.config[key] = not self.config[key]
        self.save_config()
        status = 'enabled' if self.config[key] else 'disabled'
        self.print_success(f"{key.replace('_', ' ').title()} {status}!")
    
    def show_help(self):
        """Show help information"""
        self.clear_screen()
        print("❓ Git Wrapper Help\n" + "=" * 25)
        print("""
🚀 Main Features:
• Interactive menus for all operations
• Multi-remote push support (single/multiple/all)
• Remote management with default remote setting
• Branch operations and configuration management

📤 Push Operations:
• Push to single remote (with remote selection)
• Push to multiple selected remotes
• Push to all configured remotes at once
• Visual feedback for multi-remote operations

⚡ Quick Commands:
• gw status    - Show repository status
• gw commit    - Quick commit with message
• gw sync      - Pull and push changes
• gw config    - Open configuration menu
• gw push      - Open push operations menu

🔗 Remote Management:
• Add/remove remotes
• Set default remote for operations
• Change remote URLs
• Multi-remote push capabilities

💡 Tips:
• Use Ctrl+C to exit at any time
• Default values are shown in [brackets]
• All operations ask for confirmation when destructive
• Multi-remote operations show individual results
• Set a default remote to speed up operations

Created by Johannes Nguyen
Enhanced with multi-remote push support
        """)
        input("\nPress Enter to continue...")
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

def main():
    """Main entry point"""
    git = InteractiveGitWrapper()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        handlers = {
            'status': git.interactive_status,
            'commit': git.interactive_commit,
            'sync': git.interactive_sync,
            'push': git.interactive_push_menu,
            'config': git.interactive_config_menu
        }
        
        if command in handlers:
            handlers[command]()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: status, commit, sync, push, config")
            print("Or run 'gw' without arguments for interactive mode")
    else:
        try:
            git.show_main_menu()
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")

if __name__ == '__main__':
    main()
