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
            'name': '',
            'email': '',
            'default_branch': 'main',
            'auto_push': True,
            'show_emoji': True
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
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
        """Print success message with emoji if enabled"""
        emoji = "✅ " if self.config['show_emoji'] else ""
        print(f"{emoji}{message}")
    
    def print_error(self, message):
        """Print error message with emoji if enabled"""
        emoji = "❌ " if self.config['show_emoji'] else ""
        print(f"{emoji}{message}")
    
    def print_info(self, message):
        """Print info message with emoji if enabled"""
        emoji = "ℹ️  " if self.config['show_emoji'] else ""
        print(f"{emoji}{message}")
    
    def print_working(self, message):
        """Print working message with emoji if enabled"""
        emoji = "🔄 " if self.config['show_emoji'] else ""
        print(f"{emoji}{message}")
    
    def check_git_available(self):
        """Check if git is available in the system"""
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
    
    def confirm(self, message, default=True):
        """Ask for confirmation"""
        suffix = "[Y/n]" if default else "[y/N]"
        response = input(f"{message} {suffix}: ").strip().lower()
        
        if not response:
            return default
        return response in ['y', 'yes']
    
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
                    
                    # Show quick status
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
                    "📊 Show Status",
                    "💾 Quick Commit",
                    "🔄 Sync (Pull & Push)",
                    "🌿 Branch Operations",
                    "📋 View Changes",
                    "📜 View History"
                ])
            else:
                options.extend([
                    "🎯 Initialize Repository",
                    "📥 Clone Repository"
                ])
            
            options.extend([
                "⚙️ Configuration",
                "❓ Help",
                "🚪 Exit"
            ])
            
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
        if "Show Status" in choice:
            self.interactive_status()
        elif "Quick Commit" in choice:
            self.interactive_commit()
        elif "Sync" in choice:
            self.interactive_sync()
        elif "Branch Operations" in choice:
            self.interactive_branch_menu()
        elif "View Changes" in choice:
            self.interactive_diff()
        elif "View History" in choice:
            self.interactive_log()
        elif "Initialize Repository" in choice:
            self.interactive_init()
        elif "Clone Repository" in choice:
            self.interactive_clone()
        elif "Configuration" in choice:
            self.interactive_config_menu()
        elif "Help" in choice:
            self.show_help()
        elif "Exit" in choice:
            print("\nGoodbye! 👋")
            sys.exit(0)
    
    def interactive_status(self):
        """Interactive status display"""
        self.clear_screen()
        print("📊 Repository Status")
        print("=" * 30)
        
        # Current branch
        branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        if branch:
            print(f"🌿 Current branch: {branch}")
        
        # Status
        print("\n📝 Working Directory Status:")
        self.run_git_command(['git', 'status'])
        
        # Recent commits
        print(f"\n📜 Recent commits:")
        self.run_git_command(['git', 'log', '--oneline', '-5'])
        
        input("\nPress Enter to continue...")
    
    def interactive_commit(self):
        """Interactive commit process"""
        self.clear_screen()
        print("💾 Quick Commit")
        print("=" * 20)
        
        # Show what will be committed
        print("Files to be added:")
        status = self.run_git_command(['git', 'status', '--porcelain'], capture_output=True)
        if not status:
            self.print_info("No changes to commit!")
            input("Press Enter to continue...")
            return
        
        print(status)
        
        if not self.confirm("\nAdd all changes?", True):
            return
        
        # Get commit message
        message = self.get_input("\nEnter commit message")
        if not message:
            self.print_error("Commit message required!")
            input("Press Enter to continue...")
            return
        
        # Commit
        self.print_working("Adding all changes...")
        if not self.run_git_command(['git', 'add', '.'], show_output=False):
            input("Press Enter to continue...")
            return
        
        self.print_working(f"Committing with message: '{message}'")
        if self.run_git_command(['git', 'commit', '-m', message]):
            self.print_success("Commit successful!")
            
            if self.config['auto_push'] and self.confirm("Push to remote?", True):
                self.interactive_push()
        
        input("Press Enter to continue...")
    
    def interactive_sync(self):
        """Interactive sync process"""
        self.clear_screen()
        print("🔄 Sync Repository")
        print("=" * 20)
        
        # Get branch
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        branch = self.get_input("Branch to sync", current_branch or self.config['default_branch'])
        
        self.print_working(f"Syncing with remote branch: {branch}")
        
        # Pull
        self.print_working("Pulling latest changes...")
        if not self.run_git_command(['git', 'pull', 'origin', branch]):
            input("Press Enter to continue...")
            return
        
        # Push
        self.print_working("Pushing local commits...")
        if self.run_git_command(['git', 'push', 'origin', branch]):
            self.print_success("Sync completed successfully!")
        
        input("Press Enter to continue...")
    
    def interactive_push(self):
        """Interactive push"""
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        branch = current_branch or self.config['default_branch']
        
        self.print_working(f"Pushing to origin/{branch}...")
        if self.run_git_command(['git', 'push', 'origin', branch]):
            self.print_success("Push successful!")
    
    def interactive_branch_menu(self):
        """Interactive branch operations menu"""
        while True:
            self.clear_screen()
            print("🌿 Branch Operations")
            print("=" * 25)
            
            # Show current branch
            current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
            if current_branch:
                print(f"Current branch: {current_branch}\n")
            
            options = [
                "Create new branch",
                "Switch to existing branch",
                "List all branches",
                "Delete branch",
                "Back to main menu"
            ]
            
            choice = self.get_choice("Branch Operations:", options)
            
            if "Create new branch" in choice:
                self.interactive_create_branch()
            elif "Switch to existing branch" in choice:
                self.interactive_switch_branch()
            elif "List all branches" in choice:
                self.interactive_list_branches()
            elif "Delete branch" in choice:
                self.interactive_delete_branch()
            elif "Back to main menu" in choice:
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
        # Get available branches
        branches_output = self.run_git_command(['git', 'branch'], capture_output=True)
        if not branches_output:
            return
        
        branches = [b.strip().replace('* ', '') for b in branches_output.split('\n') if b.strip()]
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        
        # Remove current branch from choices
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
        print("🌿 All Branches")
        print("=" * 15)
        self.run_git_command(['git', 'branch', '-a'])
        input("\nPress Enter to continue...")
    
    def interactive_delete_branch(self):
        """Interactive branch deletion"""
        branches_output = self.run_git_command(['git', 'branch'], capture_output=True)
        if not branches_output:
            return
        
        branches = [b.strip().replace('* ', '') for b in branches_output.split('\n') if b.strip()]
        current_branch = self.run_git_command(['git', 'branch', '--show-current'], capture_output=True)
        
        # Remove current branch from choices
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
        print("🎯 Initialize Repository")
        print("=" * 25)
        
        if self.confirm("Initialize git repository in current directory?", True):
            self.print_working("Initializing repository...")
            if not self.run_git_command(['git', 'init']):
                input("Press Enter to continue...")
                return
            
            # Configure git
            if self.config['name'] and self.config['email']:
                self.run_git_command(['git', 'config', 'user.name', self.config['name']], show_output=False)
                self.run_git_command(['git', 'config', 'user.email', self.config['email']], show_output=False)
                self.print_info("Applied your saved configuration")
            
            # Add remote?
            if self.confirm("Add remote origin?", False):
                remote_url = self.get_input("Remote URL")
                if remote_url:
                    if self.run_git_command(['git', 'remote', 'add', 'origin', remote_url]):
                        self.print_success("Remote origin added")
            
            self.print_success("Repository initialized successfully!")
        
        input("Press Enter to continue...")
    
    def interactive_clone(self):
        """Interactive repository cloning"""
        self.clear_screen()
        print("📥 Clone Repository")
        print("=" * 20)
        
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
            print("⚙️ Configuration")
            print("=" * 20)
            print(f"Name: {self.config['name'] or 'Not set'}")
            print(f"Email: {self.config['email'] or 'Not set'}")
            print(f"Default Branch: {self.config['default_branch']}")
            print(f"Auto Push: {self.config['auto_push']}")
            print(f"Show Emoji: {self.config['show_emoji']}")
            print("-" * 30)
            
            options = [
                "Set Name",
                "Set Email", 
                "Set Default Branch",
                "Toggle Auto Push",
                "Toggle Emoji",
                "Back to main menu"
            ]
            
            choice = self.get_choice("Configuration Options:", options)
            
            if "Set Name" in choice:
                name = self.get_input("Enter your name", self.config['name'])
                if name:
                    self.config['name'] = name
                    self.save_config()
                    self.print_success("Name updated!")
            elif "Set Email" in choice:
                email = self.get_input("Enter your email", self.config['email'])
                if email:
                    self.config['email'] = email
                    self.save_config()
                    self.print_success("Email updated!")
            elif "Set Default Branch" in choice:
                branch = self.get_input("Enter default branch", self.config['default_branch'])
                if branch:
                    self.config['default_branch'] = branch
                    self.save_config()
                    self.print_success("Default branch updated!")
            elif "Toggle Auto Push" in choice:
                self.config['auto_push'] = not self.config['auto_push']
                self.save_config()
                self.print_success(f"Auto push {'enabled' if self.config['auto_push'] else 'disabled'}!")
            elif "Toggle Emoji" in choice:
                self.config['show_emoji'] = not self.config['show_emoji']
                self.save_config()
                self.print_success(f"Emoji {'enabled' if self.config['show_emoji'] else 'disabled'}!")
            elif "Back to main menu" in choice:
                break
            
            if "Back to main menu" not in choice:
                time.sleep(1)
    
    def show_help(self):
        """Show help information"""
        self.clear_screen()
        print("❓ Git Wrapper Help")
        print("=" * 25)
        print("""
This interactive Git wrapper simplifies common Git operations:

🚀 Main Features:
• Interactive menus for all operations
• Automatic repository detection
• Smart defaults and confirmation prompts
• Configuration management
• Visual feedback with emojis

🎯 Getting Started:
1. Run 'gw' to start interactive mode
2. Configure your name and email in settings
3. Navigate through menus with number choices

⚡ Quick Commands:
• gw status    - Show repository status
• gw commit    - Quick commit with message
• gw sync      - Pull and push changes
• gw config    - Open configuration menu

💡 Tips:
• Use Ctrl+C to exit at any time
• Default values are shown in [brackets]
• All operations ask for confirmation when destructive
        """)
        input("\nPress Enter to continue...")
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

def main():
    """Main entry point"""
    git = InteractiveGitWrapper()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        # Handle direct commands
        if command == 'status':
            git.interactive_status()
        elif command == 'commit':
            git.interactive_commit()
        elif command == 'sync':
            git.interactive_sync()
        elif command == 'config':
            git.interactive_config_menu()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: status, commit, sync, config")
            print("Or run 'gw' without arguments for interactive mode")
    else:
        # Start interactive mode
        try:
            git.show_main_menu()
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")

if __name__ == '__main__':
    main()
