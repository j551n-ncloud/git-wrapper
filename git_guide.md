# How Git Works 🌳

```
    ██████╗ ██╗████████╗
   ██╔════╝ ██║╚══██╔══╝
   ██║  ███╗██║   ██║   
   ██║   ██║██║   ██║   
   ╚██████╔╝██║   ██║   
    ╚═════╝ ╚═╝   ╚═╝   
```

Git is a distributed version control system that tracks changes in your code over time. Think of it as a time machine for your project files!

## The Three Trees of Git

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Working   │    │   Staging   │    │    Local    │
│  Directory  │───▶│    Area     │───▶│ Repository  │
│             │    │  (Index)    │    │   (.git)    │
└─────────────┘    └─────────────┘    └─────────────┘
     📝 Edit          🎭 Stage          📦 Commit
```

### Working Directory
- Your actual project files
- Where you make changes
- Untracked modifications live here

### Staging Area (Index)
- Prepares changes for commit
- Like a "draft" of your next commit
- You choose what goes here

### Repository (.git folder)
- Permanent record of commits
- Complete project history
- Where Git stores everything

## Basic Git Workflow

```
     ┌─────────────────────────────────────────┐
     │            BASIC GIT FLOW               │
     └─────────────────────────────────────────┘
              
┌─────────┐  git add   ┌─────────┐  git commit  ┌──────────┐
│ Working │ ────────▶  │ Staging │ ───────────▶ │   Repo   │
│   Dir   │            │  Area   │              │ (.git)   │
└─────────┘            └─────────┘              └──────────┘
     △                                               │
     │                                               │
     └───────────────── git checkout ────────────────┘
```

## Essential Git Commands

### Starting a Repository
```bash
git init           # Create new Git repository
git clone <url>    # Copy existing repository
```

### Basic Operations
```bash
git status         # Check current state
git add <file>     # Stage specific file
git add .          # Stage all changes
git commit -m "message"  # Commit staged changes
```

### Viewing History
```bash
git log            # View commit history
git log --oneline  # Condensed history
git diff           # See unstaged changes
git diff --staged  # See staged changes
```

## Branch Visualization

```
                Master Branch
                     │
      A──────B──────C──────D
                    │
                    └──E──────F    Feature Branch
                              │
                              └──G    Bug Fix Branch

Legend:
A, B, C, D, E, F, G = Commits
│ = Branch connection
└ = Branch point
```

## Branching Commands

```bash
git branch                    # List branches
git branch <branch-name>      # Create new branch
git checkout <branch-name>    # Switch to branch
git checkout -b <branch-name> # Create and switch
git merge <branch-name>       # Merge branch
git branch -d <branch-name>   # Delete branch
```

## Git States Diagram

```
    File Lifecycle in Git

┌─────────────┐    git add     ┌─────────────┐
│ Untracked   │ ─────────────▶ │   Staged    │
│             │                │             │
└─────────────┘                └─────────────┘
                                       │
                                       │ git commit
                                       ▼
┌─────────────┐               ┌─────────────┐
│  Modified   │ ◀─────────────│ Unmodified  │
│             │   edit file   │ (Committed) │
└─────────────┘               └─────────────┘
       │                               ▲
       │                               │
       └─────── git add ────────────────┘
```

## Remote Repository Workflow

```
    Local Repository          Remote Repository (GitHub/GitLab)
                                        
┌──────────────────┐                  ┌──────────────────┐
│                  │    git push      │                  │
│   Local Repo     │ ────────────────▶│  Remote Repo     │
│                  │                  │                  │
│  ┌─────────────┐ │                  │  ┌─────────────┐ │
│  │   master    │ │                  │  │   master    │ │
│  │   feature   │ │                  │  │   feature   │ │
│  └─────────────┘ │                  │  └─────────────┘ │
└──────────────────┘                  └──────────────────┘
         ▲                                       │
         │                                       │
         └──────────── git pull ─────────────────┘
```

### Remote Commands
```bash
git remote add origin <url>    # Add remote repository
git push origin <branch>       # Push to remote
git pull origin <branch>       # Pull from remote
git fetch                      # Download remote changes
```

## Commit Tree Structure

```
    How Git Stores History

         HEAD
          │
          ▼
      [master]
          │
          ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ Commit  │◀───│ Commit  │◀───│ Commit  │
    │   C3    │    │   C2    │    │   C1    │
    │         │    │         │    │         │
    └─────────┘    └─────────┘    └─────────┘
         │              │              │
         ▼              ▼              ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │  Tree   │    │  Tree   │    │  Tree   │
    │ (files) │    │ (files) │    │ (files) │
    └─────────┘    └─────────┘    └─────────┘
```

## Merge vs Rebase

### Merge
```
    Before Merge:                After Merge:
    
    A───B───C  master           A───B───C───M  master
        │                           │       │
        D───E  feature              D───E───┘  
```

### Rebase
```
    Before Rebase:               After Rebase:
    
    A───B───C  master           A───B───C───D'───E'  master
        │
        D───E  feature          (feature branch history rewritten)
```

## Why Can't I Switch Branches? 🚫

### The Branch Switching Problem
```
    ❌ SCENARIO: Can't switch from dev to main
    
    [dev branch] - Current branch
    ┌─────────────────────────┐
    │ Working Directory:      │
    │ ├── file1.txt (modified)│  ← Unstaged changes
    │ ├── newfile.txt (new)   │  ← Untracked file
    │ └── staged.txt (staged) │  ← Staged changes
    └─────────────────────────┘
             │
             ▼
    $ git checkout main
    error: Your local changes would be overwritten by checkout.
    Please commit your changes or stash them before switching.
```

### Why This Happens:
Git protects you from losing work! When you have:
- **Modified files** that differ from the target branch
- **Staged changes** not yet committed
- **New files** that would conflict

### Solutions:

#### Option 1: Commit Your Changes
```bash
git add .
git commit -m "WIP: working on feature"
git checkout main
```

#### Option 2: Stash Your Changes  
```bash
git stash push -m "dev branch work in progress"
git checkout main
# Do your work on main...
git checkout dev
git stash pop  # Resume your work
```

#### Option 3: Force Switch (⚠️ DANGEROUS)
```bash
git checkout main --force  # LOSES uncommitted changes!
```

### Visual Example:
```
    BEFORE (blocked):
    [dev] Working Dir: file1.txt*, newfile.txt
          ↑ Can't switch - would lose changes
    
    AFTER stash:
    [dev] Working Dir: clean ✓
          Stash: {file1.txt*, newfile.txt}
          ↓ Now can switch!
    [main] Working Dir: clean ✓
    
    AFTER stash pop:
    [dev] Working Dir: file1.txt*, newfile.txt  
          ↑ Changes restored!
```

## Common Git Scenarios

### Undoing Changes
```bash
git checkout -- <file>     # Discard working dir changes
git reset HEAD <file>      # Unstage file
git reset --soft HEAD~1    # Undo last commit (keep changes)
git reset --hard HEAD~1    # Undo last commit (lose changes)
```

### Stashing Work - Your Safety Net!
```bash
git stash                  # Save current work temporarily
git stash pop              # Restore stashed work
git stash list             # View all stashes
git stash apply            # Apply stash without removing it
git stash drop             # Delete a stash
git stash clear            # Delete all stashes
```

#### What is Git Stash?
```
    🎒 STASH = Temporary Storage for Unfinished Work
    
    Working Directory (dirty)     Stash (clean slate)
    ┌─────────────────────┐      ┌─────────────────────┐
    │ file1.txt (modified)│ ──▶  │ Saved changes:      │
    │ file2.txt (new)     │      │ - file1.txt mods    │
    │ file3.txt (staged)  │      │ - file2.txt new     │
    └─────────────────────┘      │ - file3.txt staged  │
             │                   └─────────────────────┘
             ▼                              │
    ┌─────────────────────┐                │
    │ Clean Working Dir   │ ◀──────────────┘
    │ (can switch branch) │     git stash pop
    └─────────────────────┘
```

#### When to Use Stash:
- Need to quickly switch branches
- Pull updates but have uncommitted changes  
- Emergency bug fix while working on feature
- Experiment with code without committing

## Git Configuration

```
    ┌─────────────────────────────────────┐
    │           Git Config Levels         │
    ├─────────────────────────────────────┤
    │  System   │  Global  │   Local      │
    │   (all)   │  (user)  │ (project)    │
    │           │          │              │
    │ /etc/git  │ ~/.git   │ .git/config  │
    └─────────────────────────────────────┘
```

### Setup Commands
```bash
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
git config --global init.defaultBranch main
```

## Best Practices

```
    🎯 COMMIT MESSAGE FORMAT
    
    <type>(<scope>): <subject>
    
    <body>
    
    <footer>
    
    Examples:
    feat(auth): add login functionality
    fix(ui): resolve button alignment issue
    docs(readme): update installation guide
```

### The Seven Rules of Great Commit Messages
1. Separate subject from body with blank line
2. Limit subject line to 50 characters
3. Capitalize the subject line
4. Don't end subject line with period
5. Use imperative mood in subject line
6. Wrap body at 72 characters
7. Use body to explain what and why vs. how

## Git Workflow Models

### Gitflow
```
    master   ────●────●────●────●────●────
                  │    │    │    │    │
    develop  ────●────●────●────●────●────
                 │    │    │    │
    feature   ───┴──●─┴────│────│
                      │    │    │
    release   ────────┴──●─┴────│
                          │    │
    hotfix    ────────────────●─┴
```

## Advanced Stash Techniques

### Stash Specific Files
```bash
git stash push -m "message" -- file1.txt file2.txt
git stash push --include-untracked  # Include new files
git stash push --keep-index         # Keep staged changes
```

### Stash Management
```
    📚 STASH STACK (Last In, First Out)
    
    stash@{0}: WIP on dev: bug fix in progress
    stash@{1}: WIP on feature: half-done component  
    stash@{2}: WIP on main: emergency hotfix
    
    Commands:
    git stash list              # Show all stashes
    git stash show stash@{1}    # Show specific stash
    git stash apply stash@{1}   # Apply specific stash
    git stash drop stash@{1}    # Delete specific stash
```

### Real-World Stash Workflow
```
    💼 TYPICAL DEVELOPER DAY:
    
    09:00 - Working on feature branch
    │
    10:30 - URGENT: Production bug needs fix!
    │       git stash push -m "feature half done"
    │       git checkout main
    │       git pull origin main
    │       git checkout -b hotfix/urgent-bug
    │       [fix bug, commit, push, merge]
    │
    11:00 - Back to feature work
    │       git checkout feature-branch  
    │       git stash pop
    │       [continue working...]
```

## Troubleshooting ASCII Helper

```
    🚨 COMMON ISSUES & SOLUTIONS 🚨
    
    Problem: "detached HEAD state"
    Solution: git checkout <branch-name>
    
    Problem: Merge conflicts
    Solution: 
    1. Edit conflicted files
    2. git add <resolved-files>
    3. git commit
    
    Problem: Want to undo last commit
    Solution: git reset --soft HEAD~1
    
    Problem: Accidentally committed to wrong branch
    Solution: 
    1. git log (copy commit hash)
    2. git reset --hard HEAD~1
    3. git checkout <correct-branch>
    4. git cherry-pick <commit-hash>
    
    Problem: Can't switch branches (uncommitted changes)
    Solution: 
    1. git stash (save work temporarily)
    2. git checkout <other-branch>
    3. [do work on other branch]
    4. git checkout <original-branch>
    5. git stash pop (restore work)
    
    Problem: Added file on wrong branch
    Solution:
    1. git stash (if uncommitted)
    2. git checkout <correct-branch>
    3. git stash pop
    4. git add . && git commit
    
    Problem: Stash conflicts when popping
    Solution:
    1. git stash pop (will show conflicts)
    2. Resolve conflicts manually
    3. git add <resolved-files>
    4. git stash drop (clean up the stash)
```

---

```
    ╔═══════════════════════════════════════╗
    ║  Remember: Git is about collaboration ║
    ║  and preserving history. Every commit ║
    ║  tells a story of your project! 📖    ║
    ╚═══════════════════════════════════════╝
```

**Happy Git-ing!** 🚀
