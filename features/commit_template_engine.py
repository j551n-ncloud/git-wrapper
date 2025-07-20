#!/usr/bin/env python3
"""
CommitTemplateEngine - Advanced Commit Message Templates

This module provides commit message template functionality including:
- Predefined templates for conventional commits
- Custom template creation and management
- Template validation and application
- Interactive template selection interface
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from features.base_manager import BaseFeatureManager


class CommitTemplateEngine(BaseFeatureManager):
    """
    Advanced Commit Template Engine with conventional commit support.
    
    Provides template management including predefined templates,
    custom template creation, and validation capabilities.
    """
    
    def __init__(self, git_wrapper):
        """
        Initialize the CommitTemplateEngine.
        
        Args:
            git_wrapper: Reference to the main InteractiveGitWrapper instance
        """
        super().__init__(git_wrapper)
        self.templates_file = Path.home() / '.gitwrapper_templates.json'
        self.default_templates = self._load_default_templates()
        self._ensure_templates_file()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for commit template engine."""
        return {
            'default_template': 'conventional',
            'auto_suggest': True,
            'validate_conventional': True,
            'show_template_preview': True,
            'max_subject_length': 50,
            'max_body_line_length': 72
        }
    
    def _load_default_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Load default commit message templates.
        
        Returns:
            Dictionary containing default templates
        """
        return {
            'feat': {
                'name': 'Feature',
                'pattern': 'feat({scope}): {description}\n\n{body}\n\n{footer}',
                'fields': ['scope', 'description', 'body', 'footer'],
                'required': ['description'],
                'conventional': True,
                'description': 'A new feature',
                'examples': [
                    'feat(auth): add OAuth2 login support',
                    'feat: implement user dashboard'
                ]
            },
            'fix': {
                'name': 'Bug Fix',
                'pattern': 'fix({scope}): {description}\n\n{body}\n\n{footer}',
                'fields': ['scope', 'description', 'body', 'footer'],
                'required': ['description'],
                'conventional': True,
                'description': 'A bug fix',
                'examples': [
                    'fix(api): handle null response in user endpoint',
                    'fix: resolve memory leak in data processing'
                ]
            },
            'docs': {
                'name': 'Documentation',
                'pattern': 'docs({scope}): {description}\n\n{body}',
                'fields': ['scope', 'description', 'body'],
                'required': ['description'],
                'conventional': True,
                'description': 'Documentation only changes',
                'examples': [
                    'docs(readme): update installation instructions',
                    'docs: add API usage examples'
                ]
            },
            'style': {
                'name': 'Style',
                'pattern': 'style({scope}): {description}\n\n{body}',
                'fields': ['scope', 'description', 'body'],
                'required': ['description'],
                'conventional': True,
                'description': 'Changes that do not affect the meaning of the code',
                'examples': [
                    'style: fix indentation in main.py',
                    'style(css): improve button styling'
                ]
            },
            'refactor': {
                'name': 'Refactor',
                'pattern': 'refactor({scope}): {description}\n\n{body}\n\n{footer}',
                'fields': ['scope', 'description', 'body', 'footer'],
                'required': ['description'],
                'conventional': True,
                'description': 'A code change that neither fixes a bug nor adds a feature',
                'examples': [
                    'refactor(auth): simplify login validation logic',
                    'refactor: extract common utility functions'
                ]
            },
            'test': {
                'name': 'Test',
                'pattern': 'test({scope}): {description}\n\n{body}',
                'fields': ['scope', 'description', 'body'],
                'required': ['description'],
                'conventional': True,
                'description': 'Adding missing tests or correcting existing tests',
                'examples': [
                    'test(api): add unit tests for user service',
                    'test: improve test coverage for auth module'
                ]
            },
            'chore': {
                'name': 'Chore',
                'pattern': 'chore({scope}): {description}\n\n{body}',
                'fields': ['scope', 'description', 'body'],
                'required': ['description'],
                'conventional': True,
                'description': 'Other changes that don\'t modify src or test files',
                'examples': [
                    'chore: update dependencies',
                    'chore(build): configure webpack for production'
                ]
            },
            'perf': {
                'name': 'Performance',
                'pattern': 'perf({scope}): {description}\n\n{body}\n\n{footer}',
                'fields': ['scope', 'description', 'body', 'footer'],
                'required': ['description'],
                'conventional': True,
                'description': 'A code change that improves performance',
                'examples': [
                    'perf(db): optimize user query with indexing',
                    'perf: reduce bundle size by lazy loading'
                ]
            },
            'ci': {
                'name': 'CI/CD',
                'pattern': 'ci({scope}): {description}\n\n{body}',
                'fields': ['scope', 'description', 'body'],
                'required': ['description'],
                'conventional': True,
                'description': 'Changes to CI configuration files and scripts',
                'examples': [
                    'ci: add automated testing workflow',
                    'ci(github): update deployment pipeline'
                ]
            },
            'build': {
                'name': 'Build',
                'pattern': 'build({scope}): {description}\n\n{body}',
                'fields': ['scope', 'description', 'body'],
                'required': ['description'],
                'conventional': True,
                'description': 'Changes that affect the build system or external dependencies',
                'examples': [
                    'build: upgrade webpack to version 5',
                    'build(deps): update React to latest version'
                ]
            },
            'revert': {
                'name': 'Revert',
                'pattern': 'revert: {description}\n\n{body}',
                'fields': ['description', 'body'],
                'required': ['description'],
                'conventional': True,
                'description': 'Reverts a previous commit',
                'examples': [
                    'revert: remove experimental feature',
                    'revert: "feat: add user dashboard"'
                ]
            }
        }
    
    def _ensure_templates_file(self) -> None:
        """Ensure the templates file exists and is properly initialized."""
        if not self.templates_file.exists():
            # Initialize with default templates
            initial_data = {
                'templates': self.default_templates.copy(),
                'custom_templates': {},
                'created_at': time.time(),
                'version': '1.0'
            }
            self._save_templates(initial_data)
    
    def _load_templates(self) -> Dict[str, Any]:
        """
        Load templates from JSON file.
        
        Returns:
            Dictionary containing all templates and metadata
        """
        templates_data = self.load_json_file(self.templates_file, {})
        
        # Ensure required structure exists
        if 'templates' not in templates_data:
            templates_data['templates'] = self.default_templates.copy()
        if 'custom_templates' not in templates_data:
            templates_data['custom_templates'] = {}
        
        return templates_data
    
    def _save_templates(self, templates_data: Dict[str, Any]) -> bool:
        """
        Save templates to JSON file.
        
        Args:
            templates_data: Dictionary containing templates and metadata
            
        Returns:
            True if successful, False otherwise
        """
        templates_data['updated_at'] = time.time()
        return self.save_json_file(self.templates_file, templates_data)    

    def get_all_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available templates (default + custom).
        
        Returns:
            Dictionary containing all templates
        """
        templates_data = self._load_templates()
        all_templates = {}
        
        # Add default templates
        all_templates.update(templates_data.get('templates', {}))
        
        # Add custom templates
        all_templates.update(templates_data.get('custom_templates', {}))
        
        return all_templates
    
    def get_template(self, template_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific template by key.
        
        Args:
            template_key: Template identifier
            
        Returns:
            Template dictionary or None if not found
        """
        all_templates = self.get_all_templates()
        return all_templates.get(template_key)
    
    def validate_template_structure(self, template: Dict[str, Any]) -> List[str]:
        """
        Validate template structure and return any errors.
        
        Args:
            template: Template dictionary to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Required fields
        required_fields = ['name', 'pattern', 'fields', 'required']
        for field in required_fields:
            if field not in template:
                errors.append(f"Missing required field: {field}")
        
        # Validate pattern contains placeholders for required fields
        if 'pattern' in template and 'required' in template:
            pattern = template['pattern']
            required = template['required']
            
            for req_field in required:
                placeholder = f"{{{req_field}}}"
                if placeholder not in pattern:
                    errors.append(f"Required field '{req_field}' not found in pattern")
        
        # Validate fields list
        if 'fields' in template and not isinstance(template['fields'], list):
            errors.append("Fields must be a list")
        
        if 'required' in template and not isinstance(template['required'], list):
            errors.append("Required must be a list")
        
        return errors
    
    def validate_conventional_commit(self, message: str) -> Dict[str, Any]:
        """
        Validate a commit message against conventional commit format.
        
        Args:
            message: Commit message to validate
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': [],
            'parsed': {}
        }
        
        if not message:
            result['errors'].append("Commit message cannot be empty")
            return result
        
        lines = message.split('\n')
        subject = lines[0].strip()
        
        # Basic conventional commit pattern: type(scope): description
        pattern = r'^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\([^)]+\))?: .+'
        match = re.match(pattern, subject)
        
        if not match:
            result['errors'].append("Subject line does not follow conventional commit format")
            result['errors'].append("Expected format: type(scope): description")
            return result
        
        # Parse components
        type_match = re.match(r'^([^(:]+)', subject)
        scope_match = re.search(r'\(([^)]+)\)', subject)
        desc_match = re.search(r': (.+)$', subject)
        
        if type_match:
            result['parsed']['type'] = type_match.group(1)
        if scope_match:
            result['parsed']['scope'] = scope_match.group(1)
        if desc_match:
            result['parsed']['description'] = desc_match.group(1)
        
        # Validate subject length
        max_subject_length = self.get_feature_config('max_subject_length')
        if len(subject) > max_subject_length:
            result['warnings'].append(f"Subject line is {len(subject)} characters (recommended: {max_subject_length})")
        
        # Validate description starts with lowercase (conventional commits style)
        if desc_match:
            description = desc_match.group(1)
            if description and description[0].isupper():
                result['warnings'].append("Description should start with lowercase letter")
            
            # Check for period at end
            if description.endswith('.'):
                result['warnings'].append("Description should not end with a period")
        
        # Validate body line lengths
        max_body_length = self.get_feature_config('max_body_line_length')
        for i, line in enumerate(lines[1:], 2):
            if line.strip() and len(line) > max_body_length:
                result['warnings'].append(f"Line {i} is {len(line)} characters (recommended: {max_body_length})")
        
        # If we got here, basic format is valid
        result['valid'] = True
        
        return result
    
    def create_custom_template(self, key: str, template: Dict[str, Any]) -> bool:
        """
        Create a new custom template.
        
        Args:
            key: Unique identifier for the template
            template: Template dictionary
            
        Returns:
            True if successful, False otherwise
        """
        # Validate template structure
        errors = self.validate_template_structure(template)
        if errors:
            for error in errors:
                self.print_error(f"Template validation error: {error}")
            return False
        
        try:
            templates_data = self._load_templates()
            
            # Add to custom templates
            templates_data['custom_templates'][key] = template
            templates_data['custom_templates'][key]['created_at'] = time.time()
            templates_data['custom_templates'][key]['custom'] = True
            
            return self._save_templates(templates_data)
        except Exception as e:
            self.print_error(f"Error creating custom template: {str(e)}")
            return False
    
    def update_template(self, key: str, template: Dict[str, Any]) -> bool:
        """
        Update an existing template.
        
        Args:
            key: Template identifier
            template: Updated template dictionary
            
        Returns:
            True if successful, False otherwise
        """
        # Validate template structure
        errors = self.validate_template_structure(template)
        if errors:
            for error in errors:
                self.print_error(f"Template validation error: {error}")
            return False
        
        try:
            templates_data = self._load_templates()
            
            # Check if it's a default template (can't be modified directly)
            if key in templates_data.get('templates', {}):
                # Create a custom override
                templates_data['custom_templates'][key] = template
                templates_data['custom_templates'][key]['updated_at'] = time.time()
                templates_data['custom_templates'][key]['custom'] = True
                templates_data['custom_templates'][key]['overrides_default'] = True
            elif key in templates_data.get('custom_templates', {}):
                # Update existing custom template
                templates_data['custom_templates'][key].update(template)
                templates_data['custom_templates'][key]['updated_at'] = time.time()
            else:
                self.print_error(f"Template '{key}' not found")
                return False
            
            return self._save_templates(templates_data)
        except Exception as e:
            self.print_error(f"Error updating template: {str(e)}")
            return False
    
    def delete_template(self, key: str) -> bool:
        """
        Delete a custom template.
        
        Args:
            key: Template identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            templates_data = self._load_templates()
            
            # Can only delete custom templates
            if key in templates_data.get('custom_templates', {}):
                del templates_data['custom_templates'][key]
                return self._save_templates(templates_data)
            elif key in templates_data.get('templates', {}):
                self.print_error("Cannot delete default templates")
                return False
            else:
                self.print_error(f"Template '{key}' not found")
                return False
        except Exception as e:
            self.print_error(f"Error deleting template: {str(e)}")
            return False
    
    def reset_to_defaults(self) -> bool:
        """
        Reset templates to default configuration.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            initial_data = {
                'templates': self.default_templates.copy(),
                'custom_templates': {},
                'created_at': time.time(),
                'version': '1.0'
            }
            return self._save_templates(initial_data)
        except Exception as e:
            self.print_error(f"Error resetting templates: {str(e)}")
            return False
    
    def interactive_menu(self) -> None:
        """Display the interactive commit template menu."""
        while True:
            self.show_feature_header("Commit Template Engine")
            
            if not self.is_git_repo():
                self.print_error("Not in a Git repository!")
                input("Press Enter to continue...")
                return
            
            # Show template statistics
            all_templates = self.get_all_templates()
            default_count = len(self.default_templates)
            custom_count = len(all_templates) - default_count
            
            print(f"{self.format_with_emoji('Available Templates:', '📝')} {len(all_templates)} ({default_count} default, {custom_count} custom)")
            
            # Show current default template
            default_template = self.get_feature_config('default_template')
            print(f"{self.format_with_emoji('Default Template:', '🎯')} {default_template}")
            print()
            
            options = [
                "Use template for commit",
                "List all templates",
                "Create custom template",
                "Edit template",
                "Delete custom template",
                "Validate commit message",
                "Template settings",
                "Back to main menu"
            ]
            
            choice = self.get_choice("Template Operations:", options)
            
            if "Use template for commit" in choice:
                self.select_and_apply_template()
            elif "List all templates" in choice:
                self.show_all_templates()
            elif "Create custom template" in choice:
                self.create_custom_template_interactive()
            elif "Edit template" in choice:
                self.edit_template_interactive()
            elif "Delete custom template" in choice:
                self.delete_template_interactive()
            elif "Validate commit message" in choice:
                self.validate_commit_message_interactive()
            elif "Template settings" in choice:
                self.template_settings_menu()
            elif "Back to main menu" in choice:
                break    

    def select_and_apply_template(self) -> None:
        """Interactive template selection and application for commit."""
        self.clear_screen()
        print(f"{self.format_with_emoji('Select Commit Template', '📝')}\n" + "=" * 25)
        
        # Check if there are staged changes
        status = self.run_git_command(['git', 'status', '--porcelain', '--cached'], capture_output=True)
        if not status:
            self.print_info("No staged changes found!")
            if self.confirm("Stage all changes and continue?"):
                if not self.run_git_command(['git', 'add', '.'], show_output=False):
                    self.print_error("Failed to stage changes")
                    input("Press Enter to continue...")
                    return
            else:
                input("Press Enter to continue...")
                return
        
        # Get all templates
        all_templates = self.get_all_templates()
        if not all_templates:
            self.print_error("No templates available!")
            input("Press Enter to continue...")
            return
        
        # Create template selection menu
        template_choices = []
        template_keys = []
        
        # Group templates by category
        conventional_templates = []
        custom_templates = []
        
        for key, template in all_templates.items():
            if template.get('conventional', False):
                conventional_templates.append((key, template))
            else:
                custom_templates.append((key, template))
        
        # Add conventional templates first
        if conventional_templates:
            template_choices.append("--- Conventional Commits ---")
            template_keys.append(None)
            
            for key, template in sorted(conventional_templates):
                choice_text = f"{template['name']} ({key}) - {template.get('description', '')}"
                template_choices.append(choice_text)
                template_keys.append(key)
        
        # Add custom templates
        if custom_templates:
            template_choices.append("--- Custom Templates ---")
            template_keys.append(None)
            
            for key, template in sorted(custom_templates):
                choice_text = f"{template['name']} ({key}) - {template.get('description', '')}"
                template_choices.append(choice_text)
                template_keys.append(key)
        
        # Add option to skip template
        template_choices.append("--- Other Options ---")
        template_keys.append(None)
        template_choices.append("Skip template (manual commit)")
        template_keys.append('skip')
        
        # Get user selection
        choice = self.get_choice("Select a template:", template_choices)
        
        # Find selected template key
        selected_key = None
        for i, choice_text in enumerate(template_choices):
            if choice == choice_text:
                selected_key = template_keys[i]
                break
        
        if selected_key is None or selected_key == 'skip':
            self.print_info("Skipping template...")
            input("Press Enter to continue...")
            return
        
        # Get selected template
        selected_template = all_templates[selected_key]
        
        # Apply template
        commit_message = self.apply_template_interactive(selected_template)
        if commit_message:
            # Show preview if enabled
            if self.get_feature_config('show_template_preview'):
                self.show_commit_preview(commit_message)
                if not self.confirm("Proceed with this commit message?"):
                    input("Press Enter to continue...")
                    return
            
            # Create commit
            if self.create_commit_with_message(commit_message):
                self.print_success("Commit created successfully!")
            else:
                self.print_error("Failed to create commit")
        
        input("Press Enter to continue...")
    
    def apply_template_interactive(self, template: Dict[str, Any]) -> Optional[str]:
        """
        Apply a template interactively by collecting field values.
        
        Args:
            template: Template dictionary to apply
            
        Returns:
            Generated commit message or None if cancelled
        """
        self.clear_screen()
        print(f"{self.format_with_emoji('Apply Template:', '📝')} {template['name']}\n" + "=" * 30)
        
        # Show template description and examples
        if template.get('description'):
            print(f"Description: {template['description']}")
        
        if template.get('examples'):
            print("\nExamples:")
            for example in template['examples'][:2]:  # Show first 2 examples
                print(f"  • {example}")
        
        print(f"\nTemplate Pattern:\n{template['pattern']}")
        print("\n" + "-" * 40)
        
        # Collect field values
        field_values = {}
        fields = template.get('fields', [])
        required_fields = template.get('required', [])
        
        for field in fields:
            is_required = field in required_fields
            prompt = f"Enter {field}" + (" (required)" if is_required else " (optional)")
            
            # Provide field-specific hints
            if field == 'scope':
                prompt += " [e.g., api, ui, auth, docs]"
            elif field == 'description':
                prompt += " [brief description of the change]"
            elif field == 'body':
                prompt += " [detailed explanation, press Enter for none]"
            elif field == 'footer':
                prompt += " [breaking changes, closes #123, press Enter for none]"
            
            while True:
                value = self.get_input(prompt)
                
                if is_required and not value.strip():
                    self.print_error(f"{field} is required!")
                    continue
                
                field_values[field] = value.strip()
                break
        
        # Apply template
        try:
            commit_message = self.apply_template(template, field_values)
            return commit_message
        except Exception as e:
            self.print_error(f"Error applying template: {str(e)}")
            return None
    
    def apply_template(self, template: Dict[str, Any], context: Dict[str, str]) -> str:
        """
        Apply a template with the given context values.
        
        Args:
            template: Template dictionary
            context: Dictionary of field values
            
        Returns:
            Generated commit message
        """
        pattern = template['pattern']
        
        # Replace placeholders with context values
        for field, value in context.items():
            placeholder = f"{{{field}}}"
            if placeholder in pattern:
                pattern = pattern.replace(placeholder, value)
        
        # Remove empty optional sections
        lines = pattern.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip empty lines that would result from empty optional fields
            if line.strip() == '' and len(cleaned_lines) > 0 and cleaned_lines[-1].strip() == '':
                continue
            cleaned_lines.append(line)
        
        # Remove trailing empty lines
        while cleaned_lines and cleaned_lines[-1].strip() == '':
            cleaned_lines.pop()
        
        return '\n'.join(cleaned_lines)
    
    def show_commit_preview(self, commit_message: str) -> None:
        """
        Show a preview of the commit message.
        
        Args:
            commit_message: Commit message to preview
        """
        self.clear_screen()
        print("📋 Commit Message Preview\n" + "=" * 25)
        
        # Validate if conventional commit validation is enabled
        if self.get_feature_config('validate_conventional'):
            validation_result = self.validate_conventional_commit(commit_message)
            
            if validation_result['valid']:
                self.print_success("✓ Valid conventional commit format")
            else:
                self.print_error("✗ Invalid conventional commit format")
                for error in validation_result['errors']:
                    print(f"  • {error}")
            
            if validation_result['warnings']:
                print("\nWarnings:")
                for warning in validation_result['warnings']:
                    print(f"  ⚠ {warning}")
        
        print("\nCommit Message:")
        print("-" * 40)
        print(commit_message)
        print("-" * 40)
        
        # Show commit stats
        lines = commit_message.split('\n')
        subject_line = lines[0] if lines else ""
        
        print(f"\nStats:")
        print(f"  Subject length: {len(subject_line)} characters")
        print(f"  Total lines: {len(lines)}")
        print(f"  Body lines: {len(lines) - 1}")
    
    def create_commit_with_message(self, commit_message: str) -> bool:
        """
        Create a commit with the given message.
        
        Args:
            commit_message: Commit message to use
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Write commit message to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(commit_message)
                temp_file = f.name
            
            # Create commit using the message file
            cmd = ['git', 'commit', '-F', temp_file]
            result = self.run_git_command(cmd, show_output=False)
            
            # Clean up temporary file
            import os
            os.unlink(temp_file)
            
            return result
        except Exception as e:
            self.print_error(f"Error creating commit: {str(e)}")
            return False
    
    def show_all_templates(self) -> None:
        """Display all available templates with details."""
        self.clear_screen()
        print(f"{self.format_with_emoji('All Templates', '📝')}\n" + "=" * 15)
        
        all_templates = self.get_all_templates()
        if not all_templates:
            self.print_info("No templates available!")
            input("Press Enter to continue...")
            return
        
        # Group templates
        conventional_templates = []
        custom_templates = []
        
        for key, template in all_templates.items():
            if template.get('conventional', False):
                conventional_templates.append((key, template))
            else:
                custom_templates.append((key, template))
        
        # Show conventional templates
        if conventional_templates:
            print("🔧 Conventional Commit Templates:")
            print("-" * 35)
            
            for key, template in sorted(conventional_templates):
                print(f"  {key}: {template['name']}")
                print(f"    Description: {template.get('description', 'N/A')}")
                print(f"    Pattern: {template['pattern'][:60]}{'...' if len(template['pattern']) > 60 else ''}")
                if template.get('examples'):
                    print(f"    Example: {template['examples'][0]}")
                print()
        
        # Show custom templates
        if custom_templates:
            print("🎨 Custom Templates:")
            print("-" * 20)
            
            for key, template in sorted(custom_templates):
                print(f"  {key}: {template['name']}")
                print(f"    Description: {template.get('description', 'N/A')}")
                print(f"    Pattern: {template['pattern'][:60]}{'...' if len(template['pattern']) > 60 else ''}")
                if template.get('created_at'):
                    print(f"    Created: {self.format_timestamp(template['created_at'])}")
                print()
        
        input("Press Enter to continue...")
    
    def create_custom_template_interactive(self) -> None:
        """Interactive custom template creation."""
        self.clear_screen()
        print("🎨 Create Custom Template\n" + "=" * 25)
        
        print("Create a new custom commit message template.")
        print("Use {field_name} syntax for placeholders.\n")
        
        # Get template details
        key = self.get_input("Template key (unique identifier)")
        if not key:
            self.print_error("Template key is required!")
            input("Press Enter to continue...")
            return
        
        # Check if key already exists
        if self.get_template(key):
            if not self.confirm(f"Template '{key}' already exists. Overwrite?"):
                return
        
        name = self.get_input("Template name")
        if not name:
            self.print_error("Template name is required!")
            input("Press Enter to continue...")
            return
        
        description = self.get_input("Description (optional)")
        
        print("\nEnter the template pattern. Use {field_name} for placeholders.")
        print("Example: feat({scope}): {description}\\n\\n{body}")
        pattern = self.get_input("Template pattern")
        
        if not pattern:
            self.print_error("Template pattern is required!")
            input("Press Enter to continue...")
            return
        
        # Extract fields from pattern
        import re
        field_matches = re.findall(r'\{([^}]+)\}', pattern)
        fields = list(set(field_matches))  # Remove duplicates
        
        if not fields:
            self.print_error("Template pattern must contain at least one field placeholder!")
            input("Press Enter to continue...")
            return
        
        print(f"\nDetected fields: {', '.join(fields)}")
        
        # Get required fields
        required_fields = []
        for field in fields:
            if self.confirm(f"Is '{field}' required?", True):
                required_fields.append(field)
        
        # Ask if it's a conventional commit template
        is_conventional = self.confirm("Is this a conventional commit template?", False)
        
        # Create template
        template = {
            'name': name,
            'pattern': pattern,
            'fields': fields,
            'required': required_fields,
            'conventional': is_conventional,
            'description': description
        }
        
        # Add examples if desired
        if self.confirm("Add example usage?", False):
            examples = []
            while True:
                example = self.get_input("Example (press Enter to finish)")
                if not example:
                    break
                examples.append(example)
            
            if examples:
                template['examples'] = examples
        
        # Save template
        if self.create_custom_template(key, template):
            self.print_success(f"Custom template '{key}' created successfully!")
        else:
            self.print_error("Failed to create custom template!")
        
        input("Press Enter to continue...")
    
    def edit_template_interactive(self) -> None:
        """Interactive template editing."""
        all_templates = self.get_all_templates()
        if not all_templates:
            self.print_info("No templates available to edit!")
            input("Press Enter to continue...")
            return
        
        # Create selection list (only show custom templates and allow overriding defaults)
        template_choices = []
        template_keys = []
        
        for key, template in sorted(all_templates.items()):
            if template.get('custom', False):
                choice_text = f"{template['name']} ({key}) - Custom"
            else:
                choice_text = f"{template['name']} ({key}) - Default (will create custom override)"
            
            template_choices.append(choice_text)
            template_keys.append(key)
        
        choice = self.get_choice("Select template to edit:", template_choices)
        
        # Find selected template
        selected_key = None
        for i, choice_text in enumerate(template_choices):
            if choice == choice_text:
                selected_key = template_keys[i]
                break
        
        if not selected_key:
            return
        
        template = all_templates[selected_key]
        
        # Edit template (simplified - just allow editing description and pattern)
        self.clear_screen()
        print(f"✏️ Edit Template: {template['name']}\n" + "=" * 30)
        
        print(f"Current pattern: {template['pattern']}")
        print(f"Current description: {template.get('description', 'N/A')}")
        print()
        
        new_pattern = self.get_input("New pattern (press Enter to keep current)", template['pattern'])
        new_description = self.get_input("New description (press Enter to keep current)", template.get('description', ''))
        
        # Update template
        updated_template = template.copy()
        updated_template['pattern'] = new_pattern
        updated_template['description'] = new_description
        
        # Re-extract fields from pattern
        import re
        field_matches = re.findall(r'\{([^}]+)\}', new_pattern)
        updated_template['fields'] = list(set(field_matches))
        
        if self.update_template(selected_key, updated_template):
            self.print_success(f"Template '{selected_key}' updated successfully!")
        else:
            self.print_error("Failed to update template!")
        
        input("Press Enter to continue...")
    
    def delete_template_interactive(self) -> None:
        """Interactive template deletion."""
        templates_data = self._load_templates()
        custom_templates = templates_data.get('custom_templates', {})
        
        if not custom_templates:
            self.print_info("No custom templates available to delete!")
            input("Press Enter to continue...")
            return
        
        # Create selection list
        template_choices = []
        template_keys = []
        
        for key, template in sorted(custom_templates.items()):
            choice_text = f"{template['name']} ({key})"
            template_choices.append(choice_text)
            template_keys.append(key)
        
        choice = self.get_choice("Select template to delete:", template_choices)
        
        # Find selected template
        selected_key = None
        for i, choice_text in enumerate(template_choices):
            if choice == choice_text:
                selected_key = template_keys[i]
                break
        
        if not selected_key:
            return
        
        template = custom_templates[selected_key]
        
        # Confirm deletion
        if not self.confirm(f"Delete template '{template['name']}' ({selected_key})?", False):
            return
        
        if self.delete_template(selected_key):
            self.print_success(f"Template '{selected_key}' deleted successfully!")
        else:
            self.print_error("Failed to delete template!")
        
        input("Press Enter to continue...")
    
    def validate_commit_message_interactive(self) -> None:
        """Interactive commit message validation."""
        self.clear_screen()
        print("✅ Validate Commit Message\n" + "=" * 25)
        
        message = self.get_input("Enter commit message to validate")
        if not message:
            return
        
        result = self.validate_conventional_commit(message)
        
        print(f"\nValidation Results:")
        print("-" * 20)
        
        if result['valid']:
            self.print_success("✓ Valid conventional commit format")
            
            if result['parsed']:
                print("\nParsed components:")
                for key, value in result['parsed'].items():
                    print(f"  {key}: {value}")
        else:
            self.print_error("✗ Invalid conventional commit format")
        
        if result['errors']:
            print("\nErrors:")
            for error in result['errors']:
                print(f"  • {error}")
        
        if result['warnings']:
            print("\nWarnings:")
            for warning in result['warnings']:
                print(f"  ⚠ {warning}")
        
        input("\nPress Enter to continue...")
    
    def template_settings_menu(self) -> None:
        """Template settings configuration menu."""
        while True:
            self.clear_screen()
            print("⚙️ Template Settings\n" + "=" * 18)
            
            # Show current settings
            config = self.get_feature_config()
            print("Current Settings:")
            print(f"  Default template: {config.get('default_template', 'N/A')}")
            print(f"  Auto suggest: {config.get('auto_suggest', False)}")
            print(f"  Validate conventional: {config.get('validate_conventional', True)}")
            print(f"  Show preview: {config.get('show_template_preview', True)}")
            print(f"  Max subject length: {config.get('max_subject_length', 50)}")
            print(f"  Max body line length: {config.get('max_body_line_length', 72)}")
            print()
            
            options = [
                "Change default template",
                "Toggle auto suggest",
                "Toggle conventional validation",
                "Toggle template preview",
                "Set subject length limit",
                "Set body line length limit",
                "Reset to defaults",
                "Back to template menu"
            ]
            
            choice = self.get_choice("Settings:", options)
            
            if "Change default template" in choice:
                self._change_default_template()
            elif "Toggle auto suggest" in choice:
                current = config.get('auto_suggest', True)
                self.set_feature_config('auto_suggest', not current)
                self.print_success(f"Auto suggest {'enabled' if not current else 'disabled'}")
                input("Press Enter to continue...")
            elif "Toggle conventional validation" in choice:
                current = config.get('validate_conventional', True)
                self.set_feature_config('validate_conventional', not current)
                self.print_success(f"Conventional validation {'enabled' if not current else 'disabled'}")
                input("Press Enter to continue...")
            elif "Toggle template preview" in choice:
                current = config.get('show_template_preview', True)
                self.set_feature_config('show_template_preview', not current)
                self.print_success(f"Template preview {'enabled' if not current else 'disabled'}")
                input("Press Enter to continue...")
            elif "Set subject length limit" in choice:
                self._set_length_limit('max_subject_length', 'subject')
            elif "Set body line length limit" in choice:
                self._set_length_limit('max_body_line_length', 'body line')
            elif "Reset to defaults" in choice:
                if self.confirm("Reset all template settings to defaults?", False):
                    default_config = self._get_default_config()
                    self.update_feature_config(default_config)
                    self.print_success("Settings reset to defaults!")
                    input("Press Enter to continue...")
            elif "Back to template menu" in choice:
                break
    
    def _change_default_template(self) -> None:
        """Change the default template setting."""
        all_templates = self.get_all_templates()
        if not all_templates:
            self.print_error("No templates available!")
            input("Press Enter to continue...")
            return
        
        template_choices = []
        template_keys = []
        
        for key, template in sorted(all_templates.items()):
            choice_text = f"{template['name']} ({key})"
            template_choices.append(choice_text)
            template_keys.append(key)
        
        choice = self.get_choice("Select default template:", template_choices)
        
        # Find selected template
        selected_key = None
        for i, choice_text in enumerate(template_choices):
            if choice == choice_text:
                selected_key = template_keys[i]
                break
        
        if selected_key:
            self.set_feature_config('default_template', selected_key)
            self.print_success(f"Default template set to '{selected_key}'")
        
        input("Press Enter to continue...")
    
    def _set_length_limit(self, config_key: str, description: str) -> None:
        """Set a length limit configuration."""
        current = self.get_feature_config(config_key)
        
        try:
            new_limit = int(self.get_input(f"Enter {description} length limit", str(current)))
            if new_limit > 0:
                self.set_feature_config(config_key, new_limit)
                self.print_success(f"{description.title()} length limit set to {new_limit}")
            else:
                self.print_error("Length limit must be positive!")
        except ValueError:
            self.print_error("Invalid number!")
        
        input("Press Enter to continue...")