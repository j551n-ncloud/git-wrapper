#!/usr/bin/env python3
"""
Conflict Resolver for Advanced Git Features

This module provides interactive conflict resolution capabilities including:
- Conflict detection and listing
- Visual conflict preview
- Multiple resolution strategies
- Editor integration
- Merge finalization
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from .base_manager import BaseFeatureManager


class ConflictResolver(BaseFeatureManager):
    """
    Interactive conflict resolution manager.
    
    Provides comprehensive conflict resolution capabilities including:
    - Automatic conflict detection
    - Visual conflict preview with highlighting
    - Multiple resolution strategies (ours, theirs, manual)
    - Editor integration for manual resolution
    - Complete merge workflow management
    """
    
    def __init__(self, git_wrapper):
        """Initialize the ConflictResolver."""
        super().__init__(git_wrapper)
        self.editor = self._get_configured_editor()
        self.conflict_markers = {
            'start': '<<<<<<<',
            'separator': '=======',
            'end': '>>>>>>>'
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for conflict resolution."""
        return {
            'preferred_editor': 'code',
            'auto_stage_resolved': True,
            'show_line_numbers': True,
            'highlight_conflicts': True,
            'backup_before_resolve': True
        }
    
    def interactive_menu(self) -> None:
        """Display the interactive conflict resolution menu."""
        while True:
            self.show_feature_header("Git Conflict Resolver")
            
            if not self.is_git_repo():
                self.print_error("Not in a Git repository!")
                input("\nPress Enter to return to main menu...")
                return
            
            # Check if we're in a merge state
            merge_head_exists = (Path('.git') / 'MERGE_HEAD').exists()
            conflicted_files = self.list_conflicted_files()
            
            if not merge_head_exists and not conflicted_files:
                self.print_info("No merge conflicts detected.")
                print("\nOptions:")
                print("1. Check for conflicts")
                print("2. Configure conflict resolution settings")
                print("3. Return to main menu")
                
                choice = self.get_input("\nSelect option (1-3): ", "3")
                
                if choice == "1":
                    self._check_for_conflicts()
                elif choice == "2":
                    self._configure_settings()
                else:
                    break
            else:
                self._show_conflict_status(conflicted_files)
                print("\nConflict Resolution Options:")
                print("1. List conflicted files")
                print("2. Preview conflicts")
                print("3. Resolve conflicts interactively")
                print("4. Open file in editor")
                print("5. Finalize merge")
                print("6. Abort merge")
                print("7. Return to main menu")
                
                choice = self.get_input("\nSelect option (1-7): ", "3")
                
                if choice == "1":
                    self._list_conflicts_detailed()
                elif choice == "2":
                    self._preview_conflicts_menu()
                elif choice == "3":
                    self.interactive_conflict_resolution()
                elif choice == "4":
                    self._open_file_in_editor_menu()
                elif choice == "5":
                    if self.finalize_merge():
                        break
                elif choice == "6":
                    if self.abort_merge():
                        break
                else:
                    break
    
    def list_conflicted_files(self) -> List[str]:
        """
        List all files with merge conflicts.
        
        Returns:
            List of file paths that have conflicts
        """
        try:
            # Get files with conflicts using git status
            result = self.run_git_command(['git', 'status', '--porcelain'], capture_output=True)
            if not result:
                return []
            
            conflicted_files = []
            for line in result.split('\n'):
                if line.strip():
                    # Look for unmerged files (UU, AA, DD, AU, UA, DU, UD)
                    status = line[:2]
                    if 'U' in status or status in ['AA', 'DD']:
                        file_path = line[3:].strip()
                        conflicted_files.append(file_path)
            
            return conflicted_files
            
        except Exception as e:
            self.print_error(f"Error listing conflicted files: {str(e)}")
            return []
    
    def show_conflict_side_by_side(self, file_path: str) -> str:
        """
        Show conflicts in a side-by-side diff format.
        
        Args:
            file_path: Path to the conflicted file
            
        Returns:
            Side-by-side formatted conflict display
        """
        try:
            if not Path(file_path).exists():
                return f"File not found: {file_path}"
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if not self._has_conflict_markers(content):
                return f"No conflict markers found in {file_path}"
            
            lines = content.split('\n')
            conflicts = self._extract_conflicts(lines)
            
            if not conflicts:
                return "No conflicts found"
            
            result_lines = []
            show_emoji = self.config.get('show_emoji', True)
            
            # Header
            header_text = self.format_with_emoji(f"Side-by-side diff: {file_path}", "📄")
            result_lines.append(header_text)
            result_lines.append("═" * 80)
            
            for i, conflict in enumerate(conflicts, 1):
                conflict_text = self.format_with_emoji(f"Conflict #{i}:", "🔥")
                result_lines.append(f"\n{conflict_text}")
                result_lines.append("─" * 80)
                
                # Create side-by-side layout
                ours_lines = conflict['ours']
                theirs_lines = conflict['theirs']
                max_lines = max(len(ours_lines), len(theirs_lines))
                
                # Column headers
                left_header = self.format_with_emoji("OURS (Current)", "🔴")
                right_header = self.format_with_emoji("THEIRS (Incoming)", "🔵")
                result_lines.append(f"{left_header:<38} │ {right_header}")
                result_lines.append("─" * 38 + "─┼─" + "─" * 38)
                
                # Side-by-side content
                for j in range(max_lines):
                    left_line = ours_lines[j] if j < len(ours_lines) else ""
                    right_line = theirs_lines[j] if j < len(theirs_lines) else ""
                    
                    # Truncate long lines
                    left_display = (left_line[:35] + "...") if len(left_line) > 35 else left_line
                    right_display = (right_line[:35] + "...") if len(right_line) > 35 else right_line
                    
                    result_lines.append(f"{left_display:<38} │ {right_display}")
            
            return '\n'.join(result_lines)
            
        except Exception as e:
            return f"Error creating side-by-side view: {str(e)}"
    
    def show_conflict_preview(self, file_path: str) -> str:
        """
        Show a preview of conflicts in a file with visual highlighting.
        
        Args:
            file_path: Path to the conflicted file
            
        Returns:
            Formatted conflict preview string
        """
        try:
            if not Path(file_path).exists():
                return f"File not found: {file_path}"
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if not self._has_conflict_markers(content):
                return f"No conflict markers found in {file_path}"
            
            preview_lines = []
            lines = content.split('\n')
            in_conflict = False
            conflict_section = ""
            line_num = 1
            conflict_count = 0
            
            show_line_numbers = self.get_feature_config('show_line_numbers')
            show_emoji = self.config.get('show_emoji', True)
            
            # Add header with file info
            preview_lines.append(f"📄 File: {file_path}" if show_emoji else f"File: {file_path}")
            preview_lines.append("─" * 50)
            
            for line in lines:
                line_prefix = f"{line_num:4d}: " if show_line_numbers else ""
                
                if line.startswith(self.conflict_markers['start']):
                    in_conflict = True
                    conflict_section = "ours"
                    conflict_count += 1
                    branch_name = line[7:].strip() if len(line) > 7 else "HEAD"
                    marker = "🔴" if show_emoji else "<<<"
                    preview_lines.append(f"{line_prefix}{marker} OURS (Current: {branch_name})")
                elif line.startswith(self.conflict_markers['separator']):
                    conflict_section = "theirs"
                    marker = "🟡" if show_emoji else "==="
                    preview_lines.append(f"{line_prefix}{marker} SEPARATOR {'═' * 25}")
                elif line.startswith(self.conflict_markers['end']):
                    in_conflict = False
                    branch_name = line[7:].strip() if len(line) > 7 else "incoming"
                    marker = "🔵" if show_emoji else ">>>"
                    preview_lines.append(f"{line_prefix}{marker} THEIRS (Incoming: {branch_name})")
                else:
                    if in_conflict:
                        if conflict_section == "ours":
                            prefix = "  🔴 " if show_emoji else "  < "
                        else:  # theirs
                            prefix = "  🔵 " if show_emoji else "  > "
                        preview_lines.append(f"{line_prefix}{prefix}{line}")
                    else:
                        preview_lines.append(f"{line_prefix}    {line}")
                
                line_num += 1
            
            # Add footer with conflict summary
            preview_lines.append("─" * 50)
            summary_emoji = "⚡" if show_emoji else "!"
            preview_lines.append(f"{summary_emoji} Found {conflict_count} conflict(s) in {line_num - 1} lines")
            
            return '\n'.join(preview_lines)
            
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"
    
    def resolve_conflict(self, file_path: str, strategy: str) -> bool:
        """
        Resolve a conflict using the specified strategy.
        
        Args:
            file_path: Path to the conflicted file
            strategy: Resolution strategy ('ours', 'theirs', 'auto', 'manual')
            
        Returns:
            True if resolution was successful
        """
        try:
            if not Path(file_path).exists():
                self.print_error(f"File not found: {file_path}")
                return False
            
            if strategy == 'manual':
                return self.open_in_editor(file_path)
            
            # Create backup if configured
            if self.get_feature_config('backup_before_resolve'):
                self._create_backup(file_path)
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if not self._has_conflict_markers(content):
                self.print_info(f"No conflicts found in {file_path}")
                return True
            
            resolved_content = self._resolve_with_strategy(content, strategy)
            
            if resolved_content is None:
                if strategy == 'auto':
                    self.print_error(f"Auto-resolution failed for {file_path} - conflicts are too complex")
                else:
                    self.print_error(f"Failed to resolve conflicts in {file_path}")
                return False
            
            # Write resolved content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(resolved_content)
            
            # Stage the resolved file if configured
            if self.get_feature_config('auto_stage_resolved'):
                self.run_git_command(['git', 'add', file_path])
                if strategy == 'auto':
                    self.print_success(f"Auto-resolved and staged {file_path}")
                else:
                    self.print_success(f"Resolved and staged {file_path}")
            else:
                if strategy == 'auto':
                    self.print_success(f"Auto-resolved {file_path} (not staged)")
                else:
                    self.print_success(f"Resolved {file_path} (not staged)")
            
            return True
            
        except Exception as e:
            self.print_error(f"Error resolving conflict in {file_path}: {str(e)}")
            return False
    
    def open_in_editor(self, file_path: str) -> bool:
        """
        Open a conflicted file in the configured editor.
        
        Args:
            file_path: Path to the file to open
            
        Returns:
            True if editor was opened successfully
        """
        try:
            if not Path(file_path).exists():
                self.print_error(f"File not found: {file_path}")
                return False
            
            editor_cmd = self._get_editor_command(file_path)
            if not editor_cmd:
                self.print_error("No editor configured")
                return False
            
            self.print_working(f"Opening {file_path} in {self.editor}...")
            
            # Run editor command
            result = subprocess.run(editor_cmd, shell=True)
            
            if result.returncode == 0:
                self.print_success(f"Editor closed. Check if conflicts are resolved in {file_path}")
                
                # Ask if user wants to stage the file
                if self.confirm(f"Stage {file_path} after editing?", True):
                    self.run_git_command(['git', 'add', file_path])
                    self.print_success(f"Staged {file_path}")
                
                return True
            else:
                self.print_error("Editor exited with error")
                return False
                
        except Exception as e:
            self.print_error(f"Error opening editor: {str(e)}")
            return False
    
    def finalize_merge(self) -> bool:
        """
        Finalize the merge after all conflicts are resolved.
        
        Returns:
            True if merge was finalized successfully
        """
        try:
            # Check if there are still unresolved conflicts
            conflicted_files = self.list_conflicted_files()
            if conflicted_files:
                self.print_error("Cannot finalize merge - unresolved conflicts remain:")
                for file_path in conflicted_files:
                    print(f"  - {file_path}")
                return False
            
            # Check if we're in a merge state
            if not (Path('.git') / 'MERGE_HEAD').exists():
                self.print_info("No merge in progress")
                return True
            
            self.print_working("Finalizing merge...")
            
            # Commit the merge
            success = self.run_git_command(['git', 'commit', '--no-edit'])
            
            if success:
                self.print_success("Merge completed successfully!")
                return True
            else:
                self.print_error("Failed to finalize merge")
                return False
                
        except Exception as e:
            self.print_error(f"Error finalizing merge: {str(e)}")
            return False
    
    def abort_merge(self) -> bool:
        """
        Abort the current merge operation.
        
        Returns:
            True if merge was aborted successfully
        """
        try:
            if not (Path('.git') / 'MERGE_HEAD').exists():
                self.print_info("No merge in progress")
                return True
            
            if not self.confirm("Are you sure you want to abort the merge? This will discard all conflict resolutions.", False):
                return False
            
            self.print_working("Aborting merge...")
            
            success = self.run_git_command(['git', 'merge', '--abort'])
            
            if success:
                self.print_success("Merge aborted successfully!")
                return True
            else:
                self.print_error("Failed to abort merge")
                return False
                
        except Exception as e:
            self.print_error(f"Error aborting merge: {str(e)}")
            return False
    
    def interactive_conflict_resolution(self) -> bool:
        """
        Interactive workflow for resolving all conflicts.
        
        Returns:
            True if all conflicts were resolved
        """
        conflicted_files = self.list_conflicted_files()
        if not conflicted_files:
            self.print_info("No conflicts to resolve")
            return True
        
        self.print_info(f"Found {len(conflicted_files)} conflicted files")
        
        for i, file_path in enumerate(conflicted_files, 1):
            self.clear_screen()
            print(f"Resolving conflict {i}/{len(conflicted_files)}: {file_path}")
            print("=" * 50)
            
            # Show conflict preview
            preview = self.show_conflict_preview(file_path)
            print(preview[:1000] + "..." if len(preview) > 1000 else preview)
            
            print("\nResolution options:")
            print("1. Use ours (current branch)")
            print("2. Use theirs (incoming branch)")
            print("3. Try auto-resolution")
            print("4. Edit manually")
            print("5. Skip this file")
            print("6. Abort conflict resolution")
            
            choice = self.get_input(f"\nHow do you want to resolve {file_path}? (1-6): ")
            
            if choice == "1":
                if self.resolve_conflict(file_path, 'ours'):
                    self.print_success(f"Resolved {file_path} using 'ours'")
                else:
                    self.print_error(f"Failed to resolve {file_path}")
            elif choice == "2":
                if self.resolve_conflict(file_path, 'theirs'):
                    self.print_success(f"Resolved {file_path} using 'theirs'")
                else:
                    self.print_error(f"Failed to resolve {file_path}")
            elif choice == "3":
                if self.resolve_conflict(file_path, 'auto'):
                    self.print_success(f"Auto-resolved {file_path}")
                else:
                    self.print_error(f"Auto-resolution failed for {file_path}. Try manual resolution.")
            elif choice == "4":
                if self.resolve_conflict(file_path, 'manual'):
                    self.print_success(f"Opened {file_path} for manual editing")
                else:
                    self.print_error(f"Failed to open {file_path} in editor")
            elif choice == "5":
                self.print_info(f"Skipped {file_path}")
                continue
            elif choice == "6":
                self.print_info("Conflict resolution aborted")
                return False
            
            if i < len(conflicted_files):
                input("\nPress Enter to continue to next file...")
        
        # Check if all conflicts are resolved
        remaining_conflicts = self.list_conflicted_files()
        if not remaining_conflicts:
            self.print_success("All conflicts resolved!")
            if self.confirm("Finalize the merge now?", True):
                return self.finalize_merge()
        else:
            self.print_info(f"{len(remaining_conflicts)} conflicts still need resolution")
        
        return len(remaining_conflicts) == 0
    
    # Private helper methods
    
    def _get_configured_editor(self) -> str:
        """Get the configured editor for conflict resolution."""
        # Try feature config first
        editor = self.get_feature_config('preferred_editor')
        if editor:
            return editor
        
        # Try git config
        git_editor = self.run_git_command(['git', 'config', '--get', 'core.editor'], capture_output=True)
        if git_editor:
            return git_editor
        
        # Try environment variables
        for env_var in ['VISUAL', 'EDITOR']:
            editor = os.environ.get(env_var)
            if editor:
                return editor
        
        # Default editors by platform
        import platform
        system = platform.system().lower()
        if system == 'darwin':  # macOS
            return 'open -t'
        elif system == 'windows':
            return 'notepad'
        else:  # Linux and others
            return 'nano'
    
    def _get_editor_command(self, file_path: str) -> str:
        """Get the complete editor command for opening a file."""
        editor = self.editor
        
        # Handle special cases
        if editor == 'code':
            return f'code --wait "{file_path}"'
        elif editor == 'subl':
            return f'subl --wait "{file_path}"'
        elif editor.startswith('open'):
            return f'{editor} "{file_path}"'
        else:
            return f'{editor} "{file_path}"'
    
    def _has_conflict_markers(self, content: str) -> bool:
        """Check if content has conflict markers."""
        return (self.conflict_markers['start'] in content and 
                self.conflict_markers['separator'] in content and 
                self.conflict_markers['end'] in content)
    
    def _resolve_with_strategy(self, content: str, strategy: str) -> Optional[str]:
        """
        Resolve conflicts using the specified strategy.
        
        Args:
            content: File content with conflict markers
            strategy: 'ours', 'theirs', or 'auto'
            
        Returns:
            Resolved content or None if failed
        """
        if strategy not in ['ours', 'theirs', 'auto']:
            return None
        
        if strategy == 'auto':
            return self._auto_resolve_conflicts(content)
        
        lines = content.split('\n')
        resolved_lines = []
        in_conflict = False
        conflict_section = None
        
        for line in lines:
            if line.startswith(self.conflict_markers['start']):
                in_conflict = True
                conflict_section = 'ours'
                continue
            elif line.startswith(self.conflict_markers['separator']):
                conflict_section = 'theirs'
                continue
            elif line.startswith(self.conflict_markers['end']):
                in_conflict = False
                conflict_section = None
                continue
            
            if not in_conflict:
                resolved_lines.append(line)
            elif conflict_section == strategy:
                resolved_lines.append(line)
        
        return '\n'.join(resolved_lines)
    
    def _auto_resolve_conflicts(self, content: str) -> Optional[str]:
        """
        Automatically resolve simple conflicts using heuristics.
        
        Args:
            content: File content with conflict markers
            
        Returns:
            Resolved content or None if auto-resolution not possible
        """
        lines = content.split('\n')
        conflicts = self._extract_conflicts_with_context(lines)
        
        if not conflicts:
            return content
        
        resolved_lines = []
        line_index = 0
        
        for conflict in conflicts:
            # Add lines before conflict
            while line_index < conflict['start_line']:
                resolved_lines.append(lines[line_index])
                line_index += 1
            
            # Try to auto-resolve this conflict
            resolution = self._resolve_single_conflict_auto(conflict)
            if resolution is None:
                # Cannot auto-resolve, return None
                return None
            
            resolved_lines.extend(resolution)
            
            # Skip to after the conflict
            line_index = conflict['end_line'] + 1
        
        # Add remaining lines
        while line_index < len(lines):
            resolved_lines.append(lines[line_index])
            line_index += 1
        
        return '\n'.join(resolved_lines)
    
    def _extract_conflicts_with_context(self, lines: List[str]) -> List[Dict[str, Any]]:
        """
        Extract conflicts with line number context.
        
        Args:
            lines: List of file lines
            
        Returns:
            List of conflict dictionaries with line positions
        """
        conflicts = []
        current_conflict = None
        conflict_section = None
        
        for i, line in enumerate(lines):
            if line.startswith(self.conflict_markers['start']):
                current_conflict = {
                    'start_line': i,
                    'ours': [],
                    'theirs': [],
                    'ours_start': i + 1
                }
                conflict_section = 'ours'
            elif line.startswith(self.conflict_markers['separator']) and current_conflict:
                current_conflict['separator_line'] = i
                current_conflict['theirs_start'] = i + 1
                conflict_section = 'theirs'
            elif line.startswith(self.conflict_markers['end']) and current_conflict:
                current_conflict['end_line'] = i
                conflicts.append(current_conflict)
                current_conflict = None
                conflict_section = None
            elif current_conflict and conflict_section:
                current_conflict[conflict_section].append(line)
        
        return conflicts
    
    def _resolve_single_conflict_auto(self, conflict: Dict[str, Any]) -> Optional[List[str]]:
        """
        Try to automatically resolve a single conflict.
        
        Args:
            conflict: Conflict dictionary with 'ours' and 'theirs' sections
            
        Returns:
            List of resolved lines or None if cannot auto-resolve
        """
        ours = conflict['ours']
        theirs = conflict['theirs']
        
        # Strategy 1: If one side is empty, use the other
        if not ours and theirs:
            return theirs
        elif ours and not theirs:
            return ours
        
        # Strategy 2: If both sides are identical, use either
        if ours == theirs:
            return ours
        
        # Strategy 3: If one side is a subset of the other, use the superset
        if self._is_subset_lines(ours, theirs):
            return theirs
        elif self._is_subset_lines(theirs, ours):
            return ours
        
        # Strategy 4: Simple whitespace-only differences
        ours_stripped = [line.strip() for line in ours]
        theirs_stripped = [line.strip() for line in theirs]
        if ours_stripped == theirs_stripped:
            # Prefer the version with more consistent indentation
            return ours if len(''.join(ours)) >= len(''.join(theirs)) else theirs
        
        # Strategy 5: Import/include statements - merge both
        if self._are_import_statements(ours) and self._are_import_statements(theirs):
            return self._merge_import_statements(ours, theirs)
        
        # Cannot auto-resolve
        return None
    
    def _is_subset_lines(self, subset: List[str], superset: List[str]) -> bool:
        """Check if one list of lines is a subset of another."""
        if len(subset) >= len(superset):
            return False
        
        subset_str = '\n'.join(subset).strip()
        superset_str = '\n'.join(superset).strip()
        
        return subset_str in superset_str
    
    def _are_import_statements(self, lines: List[str]) -> bool:
        """Check if lines are import/include statements."""
        if not lines:
            return False
        
        import_patterns = [
            r'^\s*import\s+',
            r'^\s*from\s+.*\s+import\s+',
            r'^\s*#include\s*<',
            r'^\s*#include\s*"',
            r'^\s*require\s*\(',
            r'^\s*const\s+.*\s*=\s*require\s*\(',
        ]
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            is_import = any(re.match(pattern, line) for pattern in import_patterns)
            if not is_import:
                return False
        
        return True
    
    def _merge_import_statements(self, ours: List[str], theirs: List[str]) -> List[str]:
        """Merge import statements from both sides."""
        # Combine and deduplicate import statements
        all_imports = set()
        
        for line in ours + theirs:
            line = line.strip()
            if line:
                all_imports.add(line)
        
        # Sort imports for consistency
        return sorted(list(all_imports))
    
    def _extract_conflicts(self, lines: List[str]) -> List[Dict[str, List[str]]]:
        """
        Extract conflict sections from file lines.
        
        Args:
            lines: List of file lines
            
        Returns:
            List of conflict dictionaries with 'ours' and 'theirs' sections
        """
        conflicts = []
        current_conflict = None
        in_conflict = False
        conflict_section = None
        
        for line in lines:
            if line.startswith(self.conflict_markers['start']):
                in_conflict = True
                conflict_section = 'ours'
                current_conflict = {'ours': [], 'theirs': []}
            elif line.startswith(self.conflict_markers['separator']):
                conflict_section = 'theirs'
            elif line.startswith(self.conflict_markers['end']):
                in_conflict = False
                if current_conflict:
                    conflicts.append(current_conflict)
                    current_conflict = None
                conflict_section = None
            elif in_conflict and current_conflict and conflict_section:
                current_conflict[conflict_section].append(line)
        
        return conflicts
    
    def _create_backup(self, file_path: str) -> bool:
        """Create a backup of the file before resolving conflicts."""
        try:
            backup_path = f"{file_path}.conflict_backup"
            import shutil
            shutil.copy2(file_path, backup_path)
            return True
        except Exception:
            return False
    
    def _show_conflict_status(self, conflicted_files: List[str]) -> None:
        """Show current conflict status."""
        if conflicted_files:
            self.print_error(f"Found {len(conflicted_files)} conflicted files:")
            for file_path in conflicted_files:
                print(f"  {self.format_with_emoji(file_path, '🔥')}")
        else:
            self.print_success("No conflicts detected")
    
    def _check_for_conflicts(self) -> None:
        """Check for conflicts and display status."""
        self.print_working("Checking for conflicts...")
        conflicted_files = self.list_conflicted_files()
        
        if conflicted_files:
            self.print_error(f"Found {len(conflicted_files)} conflicted files:")
            for file_path in conflicted_files:
                print(f"  - {file_path}")
        else:
            self.print_success("No conflicts found")
        
        input("\nPress Enter to continue...")
    
    def _list_conflicts_detailed(self) -> None:
        """Show detailed list of conflicts."""
        conflicted_files = self.list_conflicted_files()
        
        if not conflicted_files:
            self.print_success("No conflicts found")
            input("\nPress Enter to continue...")
            return
        
        self.clear_screen()
        print("Conflicted Files Details")
        print("=" * 50)
        
        for i, file_path in enumerate(conflicted_files, 1):
            print(f"\n{i}. {file_path}")
            
            # Count conflicts in file
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                conflict_count = content.count(self.conflict_markers['start'])
                print(f"   Conflicts: {conflict_count}")
                
                # Show file size
                file_size = Path(file_path).stat().st_size
                print(f"   Size: {file_size} bytes")
                
            except Exception as e:
                print(f"   Error reading file: {str(e)}")
        
        input("\nPress Enter to continue...")
    
    def _preview_conflicts_menu(self) -> None:
        """Menu for previewing conflicts in files."""
        conflicted_files = self.list_conflicted_files()
        
        if not conflicted_files:
            self.print_success("No conflicts to preview")
            input("\nPress Enter to continue...")
            return
        
        while True:
            self.clear_screen()
            print("Preview Conflicts")
            print("=" * 30)
            
            for i, file_path in enumerate(conflicted_files, 1):
                print(f"{i}. {file_path}")
            
            print(f"{len(conflicted_files) + 1}. Return to conflict menu")
            
            choice = self.get_input(f"\nSelect file to preview (1-{len(conflicted_files) + 1}): ")
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(conflicted_files):
                    file_path = conflicted_files[choice_num - 1]
                    self.clear_screen()
                    print(f"Conflict Preview: {file_path}")
                    print("=" * 50)
                    preview = self.show_conflict_preview(file_path)
                    print(preview)
                    input("\nPress Enter to continue...")
                elif choice_num == len(conflicted_files) + 1:
                    break
                else:
                    self.print_error("Invalid choice")
                    input("Press Enter to continue...")
            except ValueError:
                self.print_error("Please enter a valid number")
                input("Press Enter to continue...")
    
    def _open_file_in_editor_menu(self) -> None:
        """Menu for opening files in editor."""
        conflicted_files = self.list_conflicted_files()
        
        if not conflicted_files:
            self.print_success("No conflicted files to edit")
            input("\nPress Enter to continue...")
            return
        
        self.clear_screen()
        print("Open File in Editor")
        print("=" * 30)
        
        for i, file_path in enumerate(conflicted_files, 1):
            print(f"{i}. {file_path}")
        
        choice = self.get_input(f"\nSelect file to edit (1-{len(conflicted_files)}): ")
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(conflicted_files):
                file_path = conflicted_files[choice_num - 1]
                self.open_in_editor(file_path)
            else:
                self.print_error("Invalid choice")
        except ValueError:
            self.print_error("Please enter a valid number")
        
        input("Press Enter to continue...")
    
    def _configure_settings(self) -> None:
        """Configure conflict resolution settings."""
        while True:
            self.clear_screen()
            print("Conflict Resolution Settings")
            print("=" * 40)
            
            config = self.get_feature_config()
            print(f"1. Preferred Editor: {config.get('preferred_editor', 'Not set')}")
            print(f"2. Auto-stage resolved files: {config.get('auto_stage_resolved', True)}")
            print(f"3. Show line numbers: {config.get('show_line_numbers', True)}")
            print(f"4. Backup before resolve: {config.get('backup_before_resolve', True)}")
            print("5. Return to conflict menu")
            
            choice = self.get_input("\nSelect setting to change (1-5): ", "5")
            
            if choice == "1":
                editor = self.get_input("Enter preferred editor command: ", config.get('preferred_editor', ''))
                if editor:
                    self.set_feature_config('preferred_editor', editor)
                    self.editor = editor
                    self.print_success("Editor updated")
            elif choice == "2":
                auto_stage = self.confirm("Auto-stage resolved files?", config.get('auto_stage_resolved', True))
                self.set_feature_config('auto_stage_resolved', auto_stage)
                self.print_success("Auto-stage setting updated")
            elif choice == "3":
                show_numbers = self.confirm("Show line numbers in previews?", config.get('show_line_numbers', True))
                self.set_feature_config('show_line_numbers', show_numbers)
                self.print_success("Line numbers setting updated")
            elif choice == "4":
                backup = self.confirm("Create backup before resolving?", config.get('backup_before_resolve', True))
                self.set_feature_config('backup_before_resolve', backup)
                self.print_success("Backup setting updated")
            else:
                break
            
            input("Press Enter to continue...")