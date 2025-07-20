# Advanced Git Features

This directory contains the advanced features for the Interactive Git Wrapper. The features are implemented as modular components that extend the base functionality.

## Architecture

### Base Manager (`base_manager.py`)
The `BaseFeatureManager` class provides common functionality for all feature managers:

- **Git Operations**: Common Git command execution and repository management
- **Configuration Management**: Feature-specific configuration handling
- **User Interface**: Consistent UI helpers and formatting
- **File Operations**: JSON file handling and directory management
- **Error Handling**: Standardized error handling and user feedback

### Feature Managers

Each feature is implemented as a separate manager class that inherits from `BaseFeatureManager`:

1. **StashManager** (`stash_manager.py`)
   - Enhanced stash management with metadata
   - Named stashes and search capabilities
   - Interactive stash operations

2. **CommitTemplateEngine** (`commit_template_engine.py`)
   - Commit message templates and validation
   - Conventional commit support
   - Custom template management

3. **BranchWorkflowManager** (`branch_workflow_manager.py`)
   - Automated branch workflows (Git Flow, GitHub Flow, etc.)
   - Feature branch lifecycle management
   - Workflow configuration and rollback

4. **ConflictResolver** (`conflict_resolver.py`)
   - Interactive merge conflict resolution
   - Multiple resolution strategies
   - Editor integration

5. **RepositoryHealthDashboard** (`repository_health_dashboard.py`)
   - Repository health analysis and monitoring
   - Branch analysis and cleanup recommendations
   - Repository statistics and metrics

6. **SmartBackupSystem** (`smart_backup_system.py`)
   - Automated repository backup
   - Multi-remote backup support
   - Backup restoration and management

## Configuration

Advanced features are configured through the main configuration file (`~/.gitwrapper_config.json`) under the `advanced_features` section:

```json
{
  "advanced_features": {
    "stash_management": {
      "auto_name_stashes": true,
      "max_stashes": 50
    },
    "commit_templates": {
      "default_template": "conventional",
      "auto_suggest": true
    },
    "branch_workflows": {
      "default_workflow": "github_flow",
      "auto_track_remotes": true,
      "base_branch": "main"
    },
    "conflict_resolution": {
      "preferred_editor": "code",
      "auto_stage_resolved": true
    },
    "health_dashboard": {
      "stale_branch_days": 30,
      "large_file_threshold_mb": 10,
      "auto_refresh": true
    },
    "backup_system": {
      "backup_remotes": ["backup", "mirror"],
      "auto_backup_branches": ["main", "develop"],
      "retention_days": 90
    }
  }
}
```

## Integration

Features are integrated into the main git wrapper through:

1. **Lazy Loading**: Features are only loaded when accessed to improve startup performance
2. **Menu Integration**: Advanced features appear in the main menu when in a Git repository
3. **Configuration Merging**: Feature configurations are merged with existing configuration
4. **Error Handling**: Graceful degradation if features are not available

## Development Status

- ✅ **Task 1**: Base setup and project structure (COMPLETED)
- ⏳ **Task 2**: StashManager implementation (PENDING)
- ⏳ **Task 3**: CommitTemplateEngine implementation (PENDING)
- ⏳ **Task 4**: BranchWorkflowManager implementation (PENDING)
- ⏳ **Task 5**: ConflictResolver implementation (PENDING)
- ⏳ **Task 6**: RepositoryHealthDashboard implementation (PENDING)
- ⏳ **Task 7**: SmartBackupSystem implementation (PENDING)
- ⏳ **Task 8**: Menu integration and finalization (PENDING)

## Testing

Run the base setup test to verify the foundation:

```bash
python3 test_base_setup.py
```

This test verifies:
- All modules can be imported correctly
- Configuration is loaded properly
- Feature managers can be initialized
- Lazy loading is working correctly