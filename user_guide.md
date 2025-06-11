# Interactive Git Wrapper - Complete Guide & Cheat Sheet

## 🚀 Overview
The Interactive Git Wrapper (`gw`) is a user-friendly command-line tool that simplifies Git operations through interactive menus and streamlined workflows. Perfect for developers who want Git's power without memorizing complex commands.

---

## 📋 Quick Command Reference

### Direct Commands
```bash
gw                 # Launch interactive menu (main interface)
gw status          # Show repository status
gw commit          # Quick commit workflow  
gw sync            # Pull and push changes
gw push            # Open push operations menu
gw config          # Open configuration menu
```

### How Interactive Menus Work
- Run `gw` to enter the main menu
- Use number keys (1, 2, 3...) to select options
- Navigate through submenus for complex operations
- All operations are guided with prompts and confirmations

---

## 🎯 When to Use Each Function

### 📊 **Show Status** - Use When:
- Starting work on a project
- Checking what files have changed
- Seeing current branch and recent commits
- Verifying repository state before operations

**What it shows:**
- Current branch name
- Modified/staged/untracked files
- Last 5 commits
- Working directory status

---

### 💾 **Quick Commit** - Use When:
- You have changes ready to commit
- Want to commit all modified files at once
- Need a fast commit workflow
- Working on feature development

**Process:**
1. Shows all changed files
2. Asks to add all changes
3. Prompts for commit message
4. Optionally pushes to remote(s)

**Best for:** Daily development workflow, quick saves

---

### 🔄 **Sync (Pull & Push)** - Use When:
- Starting work session (pull latest)
- Ending work session (push changes)
- Collaborating with team members
- Keeping branch up to date with remote

**What it does:**
1. Pulls latest changes from remote
2. Pushes your local commits
3. Keeps you synchronized with team

**Best for:** Team collaboration, daily sync routine

---

### 📤 **Push Operations** - Use When:

#### **Single Remote Push**
- Working with one main repository
- Standard GitHub/GitLab workflow
- Simple project setup

#### **Multiple Remote Push**
- Managing forks and upstream
- Deploying to multiple environments
- Backup to multiple Git hosts

#### **All Remotes Push**
- Synchronizing mirrors
- Multi-platform deployment
- Ensuring all backups are current

**Best for:** Complex deployment scenarios, backup strategies

---

### 🌿 **Branch Operations** - Use When:

#### **Create New Branch**
- Starting new features
- Experimenting with changes
- Creating hotfix branches
- Isolating development work

#### **Switch Branch**
- Moving between features
- Reviewing different versions
- Testing various approaches
- Code reviews

#### **Delete Branch**
- Cleaning up completed features
- Removing experimental branches
- Maintaining repository hygiene

**Best for:** Feature development, experimentation, maintenance

---

### 🔗 **Remote Management** - Use When:

#### **Add Remote**
- Setting up new repositories
- Adding upstream sources
- Connecting to deployment targets
- Creating backup locations

#### **Set Default Remote**
- Streamlining daily workflows
- Working with multiple remotes
- Reducing command complexity

#### **Remove Remote**
- Cleaning up old connections
- Removing deprecated services
- Simplifying remote list

**Best for:** Repository setup, maintenance, workflow optimization

---

## 🏃‍♂️ Correct Command Usage

### For Multi-Remote Push:
```bash
gw push                    # Opens push operations menu
# Then select:
# 1. Push to single remote
# 2. Push to multiple remotes    ← Select this
# 3. Push to all remotes
# 4. Back to main menu
```

### For Branch Operations:
```bash
gw                        # Opens main menu
# Then select: Branch Operations
# Then choose: Create/Switch/List/Delete
```

### For Remote Management:
```bash
gw                        # Opens main menu  
# Then select: Remote Management
# Then choose: Add/Remove/List/Change URL/Set Default
```

**Important**: The tool uses interactive menus, not command-line arguments. All `→` arrows in examples represent menu navigation, not actual command syntax.

### Daily Development Workflow
```
1. gw sync           # Get latest changes
2. gw                # Enter interactive mode
   → Branch Operations → Create new branch
3. [Make changes]
4. gw commit         # Commit changes
5. gw push           # Enter push menu, select option
```

### Multi-Remote Deployment
```
1. gw commit         # Commit final changes
2. gw push           # Enter push operations menu
   → Select "Push to multiple remotes"
   → Choose staging + production
3. gw                # Check status/remotes if needed
```

### Project Setup
```
1. gw                # Enter interactive mode
   → Initialize Repository
2. gw                # Enter interactive mode again
   → Remote Management → Add remote
3. gw config         # Set name/email
4. gw commit         # Initial commit
5. gw push           # Push to remote
```

### Team Collaboration
```
1. gw sync           # Sync with team changes
2. gw                # Enter interactive mode
   → Branch Operations → Switch to existing branch
3. [Make changes]
4. gw commit         # Commit work
5. gw sync           # Final sync before merge
```

---

## ⚡ Quick Tips & Best Practices

### 🎯 Efficiency Tips
- **Set Default Remote**: Configure your primary remote to speed up operations
- **Use Auto-Push**: Enable auto-push after commits for streamlined workflow  
- **Emoji Display**: Keep emojis enabled for better visual feedback
- **Quick Commands**: Use `gw commit` and `gw sync` for daily tasks

### 🛡️ Safety Features
- **Confirmation Prompts**: All destructive operations ask for confirmation
- **Status Checks**: Shows current state before operations
- **Error Handling**: Clear error messages with suggested solutions
- **Multi-Remote Feedback**: Individual success/failure for each remote

### 📚 Learning Path
1. **Start Simple**: Use `gw status` and `gw commit` first
2. **Add Remotes**: Learn remote management for collaboration
3. **Branch Workflow**: Master branch operations for feature development
4. **Advanced Push**: Use multi-remote features for complex deployments

---

## 🔧 Configuration Options

### User Settings
- **Name/Email**: Git identity for commits
- **Default Branch**: Usually 'main' or 'master'
- **Default Remote**: Primary remote for operations
- **Auto Push**: Automatically push after commits
- **Show Emoji**: Visual indicators in output

### Access Configuration
```bash
gw config           # Interactive configuration menu
```

---

## 🚨 Troubleshooting

### Common Issues

**"Not a Git Repository"**
- Solution: Run `gw init` or navigate to a Git repository

**"No Remotes Configured"** 
- Solution: Use `gw remote → add` to add remote repositories

**"Push Failed"**
- Check internet connection
- Verify remote URL and permissions
- Use `gw sync` to pull latest changes first

**"Branch Already Exists"**
- Choose different branch name
- Switch to existing branch instead

### Getting Help
- Run `gw` and select "❓ Help" for built-in documentation
- Use `Ctrl+C` to exit any operation safely
- All operations show clear success/failure messages

---

## 📖 Menu Navigation Guide

### Main Menu Structure
```
📊 Repository Status
├── 💾 Quick Commit
├── 🔄 Sync (Pull & Push)  
├── 📤 Push Operations
│   ├── Push to single remote
│   ├── Push to multiple remotes
│   └── Push to all remotes
├── 🌿 Branch Operations
│   ├── Create new branch
│   ├── Switch to existing branch
│   ├── List all branches
│   └── Delete branch
├── 🔗 Remote Management
│   ├── Add remote
│   ├── Remove remote
│   ├── Set default remote
│   └── Change remote URL
└── ⚙️ Configuration
```

### Navigation Tips
- Use number keys to select menu options
- Press `Enter` to confirm selections
- Use `Ctrl+C` to exit or go back
- Default options shown in `[brackets]`
- Multi-select with comma separation: `1,3,5`

---

## 🎯 Use Case Examples

### Solo Developer
```bash
# Daily routine
gw sync              # Start day with latest code
gw commit            # Commit feature work
gw push              # Enter push menu, select remote
```

### Team Lead  
```bash
# Managing multiple remotes
gw push              # Enter push operations
                     # → Select "Push to multiple remotes"
                     # → Choose staging + production
gw                   # Check remote status in main menu
gw sync              # Stay current with team
```

### Open Source Contributor
```bash
# Fork workflow
gw                   # Enter interactive mode
                     # → Remote Management → Add remote (upstream)
gw sync              # Sync with upstream
gw                   # → Branch Operations → Create new branch
gw push              # → Push to single remote (your fork)
```

### DevOps Engineer
```bash
# Multi-environment deployment
gw commit            # Commit deployment config
gw push              # Enter push operations
                     # → Select "Push to all remotes"
gw                   # → Remote Management → List remotes
```

---

## 🏆 Advanced Features

### Multi-Remote Operations
- **Selective Push**: Choose specific remotes for targeted deployment
- **Batch Operations**: Push to multiple remotes with single command
- **Status Tracking**: Individual success/failure reporting per remote
- **Default Remote**: Set primary remote for streamlined operations

### Smart Workflows
- **Auto-Configuration**: Applies saved settings to new repositories
- **Upstream Tracking**: Automatically sets up branch tracking
- **Status Integration**: Shows repository state in all menus
- **Error Recovery**: Clear guidance when operations fail

### Customization
- **Emoji Toggle**: Clean output for scripting environments
- **Default Values**: Remembers your preferences
- **Branch Naming**: Supports any branch naming convention
- **Remote Aliases**: Use meaningful names for deployment targets

---

## 🔧 Additional Git Commands (Not in Tool)

### Useful Git Commands to Know

#### **File Operations**
```bash
git add -p                    # Interactive staging (stage parts of files)
git checkout -- <file>       # Discard changes in specific file
git restore <file>            # Restore file to last commit (Git 2.23+)
git clean -fd                 # Remove untracked files and directories
git stash                     # Temporarily save changes
git stash pop                 # Restore stashed changes
git stash list                # List all stashes
```

#### **Advanced History & Inspection**
```bash
git log --graph --oneline     # Visual branch history
git log --author="Name"       # Commits by specific author
git log --since="2 weeks ago" # Commits in time range
git blame <file>              # See who changed each line
git show <commit>             # Show specific commit details
git diff HEAD~1               # Compare with previous commit
git diff <branch1>..<branch2> # Compare branches
```

#### **Branch & Merge Operations**
```bash
git merge --no-ff <branch>    # Merge with merge commit
git rebase <branch>           # Rebase current branch
git rebase -i HEAD~3          # Interactive rebase (last 3 commits)
git cherry-pick <commit>      # Apply specific commit to current branch
git branch -r                 # List remote branches
git branch -vv                # Show tracking branches
```

#### **Undoing Operations**
```bash
git reset --soft HEAD~1       # Undo last commit, keep changes staged
git reset --hard HEAD~1       # Undo last commit, discard changes
git revert <commit>           # Create new commit that undoes changes
git reflog                    # See all recent HEAD movements
git bisect start              # Start binary search for bugs
```

#### **Remote & Collaboration**
```bash
git fetch --all               # Fetch from all remotes
git pull --rebase             # Pull with rebase instead of merge
git push --force-with-lease   # Safer force push
git remote prune origin       # Clean up deleted remote branches
git ls-remote origin          # List all remote branches
```

#### **Configuration & Aliases**
```bash
git config --global user.name "Name"     # Set global username
git config --global user.email "email"   # Set global email
git config --global alias.st status      # Create 'git st' alias
git config --global alias.co checkout    # Create 'git co' alias
git config --global alias.br branch      # Create 'git br' alias
git config --global alias.cm commit      # Create 'git cm' alias
```

#### **Advanced Workflow Commands**
```bash
git tag v1.0.0                # Create lightweight tag
git tag -a v1.0.0 -m "Release 1.0.0"  # Create annotated tag
git push origin --tags        # Push all tags
git worktree add ../feature   # Create linked working directory
git submodule add <repo>      # Add git submodule
git archive --format=zip HEAD # Create zip of current state
```

#### **Debugging & Analysis**
```bash
git fsck                      # Check repository integrity
git gc                        # Garbage collect and optimize
git count-objects -vH         # Show repository size info
git shortlog -sn              # Contributor statistics
git log --stat                # Show file change statistics
git whatchanged              # Show files changed in each commit
```

### 💡 Pro Tips for Advanced Git

#### **Useful Aliases to Add**
```bash
# Add these to your ~/.gitconfig or run with git config --global
git config --global alias.unstage 'reset HEAD --'
git config --global alias.last 'log -1 HEAD'
git config --global alias.visual '!gitk'
git config --global alias.pushall '!git remote | xargs -L1 git push --all'
git config --global alias.graph 'log --graph --pretty=format:"%h -%d %s (%cr)" --abbrev-commit --date=relative --all'
```

#### **When to Use These Commands**
- **git stash**: When you need to quickly switch branches with uncommitted changes
- **git rebase -i**: Clean up commit history before pushing to shared branches
- **git cherry-pick**: Apply specific fixes from other branches
- **git reflog**: Recovery when you accidentally reset or lose commits
- **git bisect**: Find the commit that introduced a bug
- **git worktree**: Work on multiple branches simultaneously

#### **Safety Commands**
```bash
git status                    # Always check status before operations
git diff --cached             # Review staged changes before commit
git log --oneline -10         # Quick overview of recent commits
git branch -a                 # See all branches before switching
```

### 🚨 Commands to Use Carefully
- `git reset --hard` - Permanently discards changes
- `git push --force` - Can overwrite others' work
- `git rebase` on shared branches - Can cause conflicts for teammates
- `git clean -fd` - Permanently deletes untracked files

### 🔄 Workflow Integration
Use these commands alongside the Interactive Git Wrapper:
1. Use `gw` for daily operations (commit, push, sync)
2. Use raw Git commands for advanced operations
3. Use `git stash` before running `gw sync` if you have uncommitted changes
4. Use `git log --graph` to visualize complex branch histories

---

*Created by Johannes Nguyen | Enhanced with multi-remote push support*

**Happy Git-ing! 🎉**
