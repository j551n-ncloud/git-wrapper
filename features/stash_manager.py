#!/usr/bin/env python3
"""
StashManager - Advanced Git Stash Management

This module provides enhanced stash management capabilities including:
- Named stashes with custom metadata
- Stash preview and search functionality
- Interactive stash management interface
- Persistent metadata storage
"""

import json
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from features.base_manager import BaseFeatureManager


class StashManager(BaseFeatureManager):
    """
    Advanced Git Stash Manager with metadata support.
    
    Provides enhanced stash management including named stashes,
    search capabilities, and persistent metadata storage.
    """
    
    def __init__(self, git_wrapper):
        """
        Initialize the StashManager.
        
        Args:
            git_wrapper: Reference to the main InteractiveGitWrapper instance
        """
        super().__init__(git_wrapper)
        self.stash_metadata_file = self._get_stash_metadata_path()
        self._ensure_metadata_file()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for stash management."""
        return {
            'auto_name_stashes': True,
            'max_stashes': 50,
            'show_preview_lines': 10,
            'confirm_deletions': True
        }
    
    def _get_stash_metadata_path(self) -> Path:
        """
        Get the path to the stash metadata file.
        
        Returns:
            Path to the stash metadata JSON file
        """
        git_root = self.get_git_root()
        if git_root:
            return git_root / '.git' / 'gitwrapper_stashes.json'
        else:
            # Fallback to current directory if not in git repo
            return Path('.git') / 'gitwrapper_stashes.json'
    
    def _ensure_metadata_file(self) -> None:
        """Ensure the metadata file exists and is properly initialized."""
        if not self.stash_metadata_file.exists():
            self._save_metadata({})
    
    def _load_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Load stash metadata from JSON file.
        
        Returns:
            Dictionary containing stash metadata keyed by stash ID
        """
        return self.load_json_file(self.stash_metadata_file, {})
    
    def _save_metadata(self, metadata: Dict[str, Dict[str, Any]]) -> bool:
        """
        Save stash metadata to JSON file.
        
        Args:
            metadata: Dictionary containing stash metadata
            
        Returns:
            True if successful, False otherwise
        """
        return self.save_json_file(self.stash_metadata_file, metadata)
    
    def _get_git_stashes(self) -> List[Dict[str, str]]:
        """
        Get list of Git stashes from git stash list command.
        
        Returns:
            List of dictionaries containing stash information
        """
        try:
            stash_output = self.run_git_command(['git', 'stash', 'list'], capture_output=True)
            if not stash_output:
                return []
            
            stashes = []
            for line in stash_output.split('\n'):
                if line.strip():
                    # Parse stash line: "stash@{0}: WIP on branch: message"
                    parts = line.split(': ', 2)
                    if len(parts) >= 2:
                        stash_id = parts[0].strip()
                        stash_info = parts[1].strip() if len(parts) > 1 else ""
                        stash_message = parts[2].strip() if len(parts) > 2 else ""
                        
                        stashes.append({
                            'id': stash_id,
                            'info': stash_info,
                            'message': stash_message,
                            'full_line': line.strip()
                        })
            
            return stashes
        except Exception as e:
            self.print_error(f"Error getting stash list: {str(e)}")
            return []
    
    def _generate_stash_name(self, message: str = None) -> str:
        """
        Generate a default name for a stash.
        
        Args:
            message: Optional commit message to base name on
            
        Returns:
            Generated stash name
        """
        current_branch = self.get_current_branch()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        if message and len(message) > 0:
            # Use first few words of message
            words = message.split()[:3]
            name_part = '_'.join(words).lower()
            # Sanitize the name
            name_part = self.sanitize_filename(name_part)
            return f"{current_branch}_{name_part}_{timestamp}"
        else:
            return f"{current_branch}_stash_{timestamp}"
    
    def _update_stash_metadata(self, stash_id: str, name: str, description: str = None) -> bool:
        """
        Update metadata for a specific stash.
        
        Args:
            stash_id: Git stash ID (e.g., "stash@{0}")
            name: Custom name for the stash
            description: Optional description
            
        Returns:
            True if successful, False otherwise
        """
        metadata = self._load_metadata()
        
        metadata[stash_id] = {
            'name': name,
            'description': description or "",
            'created_at': time.time(),
            'branch': self.get_current_branch() or "unknown"
        }
        
        return self._save_metadata(metadata)
    
    def _cleanup_stale_metadata(self) -> None:
        """Remove metadata for stashes that no longer exist."""
        metadata = self._load_metadata()
        current_stashes = self._get_git_stashes()
        current_stash_ids = {stash['id'] for stash in current_stashes}
        
        # Remove metadata for stashes that no longer exist
        stale_ids = set(metadata.keys()) - current_stash_ids
        if stale_ids:
            for stale_id in stale_ids:
                del metadata[stale_id]
            self._save_metadata(metadata)
            self.print_info(f"Cleaned up metadata for {len(stale_ids)} stale stashes")
    
    def interactive_menu(self) -> None:
        """Display the interactive stash management menu."""
        while True:
            self.show_feature_header("Stash Management")
            
            if not self.is_git_repo():
                self.print_error("Not in a Git repository!")
                input("Press Enter to continue...")
                return
            
            # Clean up stale metadata
            self._cleanup_stale_metadata()
            
            # Show current stashes
            stashes = self.list_stashes_with_metadata()
            if stashes:
                self.print_with_emoji(f"Current Stashes ({len(stashes)}):", "📦")
                for i, stash in enumerate(stashes[:5], 1):  # Show first 5
                    name = stash.get('name', 'Unnamed')
                    created = self.format_timestamp(stash.get('created_at', 0))
                    print(f"  {i}. {name} ({created})")
                
                if len(stashes) > 5:
                    print(f"  ... and {len(stashes) - 5} more")
                print()
            else:
                self.print_with_emoji("No stashes found\n", "📦")
            
            options = [
                "Create new stash",
                "List all stashes",
                "Preview stash",
                "Apply stash",
                "Delete stash",
                "Search stashes",
                "Back to main menu"
            ]
            
            choice = self.get_choice("Stash Operations:", options)
            
            if "Create new stash" in choice:
                self.create_named_stash_interactive()
            elif "List all stashes" in choice:
                self.show_all_stashes()
            elif "Preview stash" in choice:
                self.preview_stash_interactive()
            elif "Apply stash" in choice:
                self.apply_stash_interactive()
            elif "Delete stash" in choice:
                self.delete_stash_interactive()
            elif "Search stashes" in choice:
                self.search_stashes_interactive()
            elif "Back to main menu" in choice:
                break
    
    def create_named_stash_interactive(self) -> None:
        """Interactive stash creation with custom naming."""
        self.clear_screen()
        self.print_with_emoji("Create New Stash\n" + "=" * 20, "📦")
        
        # Check if there are changes to stash
        status = self.run_git_command(['git', 'status', '--porcelain'], capture_output=True)
        if not status:
            self.print_info("No changes to stash!")
            input("Press Enter to continue...")
            return
        
        print("Changes to be stashed:")
        print(status)
        print()
        
        # Get stash message
        message = self.get_input("Enter stash message (optional)")
        
        # Generate or get custom name
        auto_name = self._generate_stash_name(message)
        if self.get_feature_config('auto_name_stashes'):
            name = self.get_input("Stash name", auto_name)
        else:
            name = self.get_input("Stash name")
        
        if not name:
            name = auto_name
        
        # Get optional description
        description = self.get_input("Description (optional)")
        
        # Create the stash
        if self.create_named_stash(name, message, description):
            self.print_success(f"Stash '{name}' created successfully!")
        
        input("Press Enter to continue...")
    
    def create_named_stash(self, name: str, message: str = None, description: str = None) -> bool:
        """
        Create a new named stash.
        
        Args:
            name: Custom name for the stash
            message: Optional stash message
            description: Optional description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create the stash with message
            stash_message = message or name
            cmd = ['git', 'stash', 'push', '-m', stash_message]
            
            if not self.run_git_command(cmd, show_output=False):
                return False
            
            # Get the new stash ID (should be stash@{0})
            stashes = self._get_git_stashes()
            if stashes:
                new_stash_id = stashes[0]['id']  # Most recent stash
                return self._update_stash_metadata(new_stash_id, name, description)
            
            return True
        except Exception as e:
            self.print_error(f"Error creating stash: {str(e)}")
            return False
    
    def list_stashes_with_metadata(self) -> List[Dict[str, Any]]:
        """
        Get list of all stashes with metadata.
        
        Returns:
            List of dictionaries containing stash information and metadata
        """
        git_stashes = self._get_git_stashes()
        metadata = self._load_metadata()
        
        stashes_with_metadata = []
        for stash in git_stashes:
            stash_id = stash['id']
            stash_meta = metadata.get(stash_id, {})
            
            combined_info = {
                'id': stash_id,
                'git_info': stash['info'],
                'git_message': stash['message'],
                'full_line': stash['full_line'],
                'name': stash_meta.get('name', 'Unnamed'),
                'description': stash_meta.get('description', ''),
                'created_at': stash_meta.get('created_at', 0),
                'branch': stash_meta.get('branch', 'unknown')
            }
            
            stashes_with_metadata.append(combined_info)
        
        return stashes_with_metadata
    
    def show_all_stashes(self) -> None:
        """Display all stashes with detailed information."""
        self.clear_screen()
        self.print_with_emoji("All Stashes\n" + "=" * 15, "📦")
        
        stashes = self.list_stashes_with_metadata()
        if not stashes:
            self.print_info("No stashes found!")
            input("Press Enter to continue...")
            return
        
        for i, stash in enumerate(stashes, 1):
            print(f"{i}. {stash['name']}")
            print(f"   ID: {stash['id']}")
            print(f"   Branch: {stash['branch']}")
            if stash['created_at']:
                print(f"   Created: {self.format_timestamp(stash['created_at'])}")
            if stash['description']:
                print(f"   Description: {stash['description']}")
            print(f"   Git Info: {stash['git_info']}")
            if stash['git_message']:
                print(f"   Message: {stash['git_message']}")
            print()
        
        input("Press Enter to continue...")
    
    def preview_stash_interactive(self) -> None:
        """Interactive stash preview selection."""
        stashes = self.list_stashes_with_metadata()
        if not stashes:
            self.print_info("No stashes to preview!")
            input("Press Enter to continue...")
            return
        
        # Create selection list
        stash_choices = [f"{s['name']} ({s['id']})" for s in stashes]
        choice = self.get_choice("Select stash to preview:", stash_choices)
        
        # Find selected stash
        selected_stash = None
        for stash in stashes:
            if f"{stash['name']} ({stash['id']})" == choice:
                selected_stash = stash
                break
        
        if selected_stash:
            self.preview_stash(selected_stash['id'])
    
    def preview_stash(self, stash_id: str) -> str:
        """
        Preview stash content without applying it.
        
        Args:
            stash_id: Git stash ID to preview
            
        Returns:
            Stash content as string
        """
        try:
            self.clear_screen()
            self.print_with_emoji(f"Stash Preview: {stash_id}\n" + "=" * 30, "📋")
            
            # Show stash diff
            preview_content = self.run_git_command(['git', 'stash', 'show', '-p', stash_id], capture_output=True)
            
            if preview_content:
                # Limit preview lines if configured
                max_lines = self.get_feature_config('show_preview_lines')
                if max_lines and max_lines > 0:
                    lines = preview_content.split('\n')
                    if len(lines) > max_lines:
                        print('\n'.join(lines[:max_lines]))
                        print(f"\n... ({len(lines) - max_lines} more lines)")
                    else:
                        print(preview_content)
                else:
                    print(preview_content)
            else:
                self.print_info("No changes in this stash")
            
            input("\nPress Enter to continue...")
            return preview_content
        except Exception as e:
            self.print_error(f"Error previewing stash: {str(e)}")
            input("Press Enter to continue...")
            return ""
    
    def apply_stash_interactive(self) -> None:
        """Interactive stash application."""
        stashes = self.list_stashes_with_metadata()
        if not stashes:
            self.print_info("No stashes to apply!")
            input("Press Enter to continue...")
            return
        
        # Create selection list
        stash_choices = [f"{s['name']} ({s['id']})" for s in stashes]
        choice = self.get_choice("Select stash to apply:", stash_choices)
        
        # Find selected stash
        selected_stash = None
        for stash in stashes:
            if f"{stash['name']} ({stash['id']})" == choice:
                selected_stash = stash
                break
        
        if not selected_stash:
            return
        
        # Choose apply method
        apply_choices = ["Apply (keep stash)", "Pop (apply and delete)"]
        apply_method = self.get_choice("How to apply stash:", apply_choices)
        
        keep_stash = "keep stash" in apply_method
        
        if self.apply_stash(selected_stash['id'], keep_stash):
            action = "applied" if keep_stash else "popped"
            self.print_success(f"Stash '{selected_stash['name']}' {action} successfully!")
        
        input("Press Enter to continue...")
    
    def apply_stash(self, stash_id: str, keep: bool = True) -> bool:
        """
        Apply a stash to the working directory.
        
        Args:
            stash_id: Git stash ID to apply
            keep: Whether to keep the stash after applying (True for apply, False for pop)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = ['git', 'stash', 'apply' if keep else 'pop', stash_id]
            
            if self.run_git_command(cmd, show_output=False):
                # If popping, remove metadata
                if not keep:
                    metadata = self._load_metadata()
                    if stash_id in metadata:
                        del metadata[stash_id]
                        self._save_metadata(metadata)
                return True
            
            return False
        except Exception as e:
            self.print_error(f"Error applying stash: {str(e)}")
            return False
    
    def delete_stash_interactive(self) -> None:
        """Interactive stash deletion."""
        stashes = self.list_stashes_with_metadata()
        if not stashes:
            self.print_info("No stashes to delete!")
            input("Press Enter to continue...")
            return
        
        # Create selection list
        stash_choices = [f"{s['name']} ({s['id']})" for s in stashes]
        choice = self.get_choice("Select stash to delete:", stash_choices)
        
        # Find selected stash
        selected_stash = None
        for stash in stashes:
            if f"{stash['name']} ({stash['id']})" == choice:
                selected_stash = stash
                break
        
        if not selected_stash:
            return
        
        # Confirm deletion
        if self.get_feature_config('confirm_deletions'):
            if not self.confirm(f"Delete stash '{selected_stash['name']}'?", False):
                return
        
        if self.delete_stash(selected_stash['id']):
            self.print_success(f"Stash '{selected_stash['name']}' deleted successfully!")
        
        input("Press Enter to continue...")
    
    def delete_stash(self, stash_id: str) -> bool:
        """
        Delete a specific stash.
        
        Args:
            stash_id: Git stash ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.run_git_command(['git', 'stash', 'drop', stash_id], show_output=False):
                # Remove metadata
                metadata = self._load_metadata()
                if stash_id in metadata:
                    del metadata[stash_id]
                    self._save_metadata(metadata)
                return True
            
            return False
        except Exception as e:
            self.print_error(f"Error deleting stash: {str(e)}")
            return False
    
    def search_stashes_interactive(self) -> None:
        """Interactive stash search."""
        query = self.get_input("Enter search query (name, description, or content)")
        if not query:
            return
        
        results = self.search_stashes(query)
        
        self.clear_screen()
        self.print_with_emoji(f"Search Results for '{query}'\n" + "=" * 30, "🔍")
        
        if not results:
            self.print_info("No matching stashes found!")
        else:
            for i, stash in enumerate(results, 1):
                print(f"{i}. {stash['name']} ({stash['id']})")
                if stash['description']:
                    print(f"   Description: {stash['description']}")
                print(f"   Branch: {stash['branch']}")
                if stash['created_at']:
                    print(f"   Created: {self.format_timestamp(stash['created_at'])}")
                print()
        
        input("Press Enter to continue...")
    
    def search_stashes(self, query: str) -> List[Dict[str, Any]]:
        """
        Search stashes by name, description, or content.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching stashes
        """
        if not query:
            return []
        
        stashes = self.list_stashes_with_metadata()
        query_lower = query.lower()
        matching_stashes = []
        
        for stash in stashes:
            # Search in name, description, and git message
            searchable_text = ' '.join([
                stash.get('name', ''),
                stash.get('description', ''),
                stash.get('git_message', ''),
                stash.get('branch', '')
            ]).lower()
            
            if query_lower in searchable_text:
                matching_stashes.append(stash)
                continue
            
            # Also search in stash content
            try:
                stash_content = self.run_git_command(['git', 'stash', 'show', '-p', stash['id']], capture_output=True)
                if stash_content and query_lower in stash_content.lower():
                    matching_stashes.append(stash)
            except:
                pass  # Skip content search if it fails
        
        return matching_stashes