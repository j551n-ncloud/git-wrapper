# Git Wrapper (gw) - What It Looks Like

## Running `gw` (Interactive Mode)

### Main Menu - In Git Repository
```
==================================================
🚀 Interactive Git Wrapper
==================================================
📁 Directory: my-project
📊 Status: 🟢 Git Repository
==================================================
🌿 Current Branch: main
📝 Uncommitted Changes: 3 files
--------------------------------------------------
  1. 📊 Show Status
  2. 💾 Quick Commit
  3. 🔄 Sync (Pull & Push)
  4. 📤 Push Operations
  5. 🌿 Branch Operations
  6. 📋 View Changes
  7. 📜 View History
  8. 🔗 Remote Management
  9. ⚙️ Configuration
  10. ❓ Help
  11. 🚪 Exit

Enter your choice (1-11): 
```

### Main Menu - Not a Git Repository
```
==================================================
🚀 Interactive Git Wrapper
==================================================
📁 Directory: new-folder
📊 Status: 🔴 Not a Git Repository
==================================================
  1. 🎯 Initialize Repository
  2. 📥 Clone Repository
  3. ⚙️ Configuration
  4. ❓ Help
  5. 🚪 Exit

Enter your choice (1-5): 
```

## Quick Commit Flow
```
💾 Quick Commit
====================
Files to be added:
 M src/main.py
 M README.md
?? new-file.txt

Add all changes? [Y/n]: y

Enter commit message: Add new feature and update docs

🔄 Adding all changes...
🔄 Committing with message: 'Add new feature and update docs'
✅ Commit successful!
Push to remote(s)? [Y/n]: y
```

## Push Operations Menu
```
📤 Push Operations
====================
Current branch: main
Available remotes: origin, backup, github
------------------------------
Push Options:
  1. Push to single remote
  2. Push to multiple remotes
  3. Push to all remotes
  4. Back to main menu

Enter choice number: 2

Branch to push [main]: main

Select remotes to push to:
(Enter comma-separated numbers, e.g., 1,3,4)
  1. origin
  2. backup
  3. github

Enter choice numbers: 1,3

ℹ️  Pushing main to: origin, github
🔄 Pushing to origin...
✅ ✓ Pushed to origin
🔄 Pushing to github...
✅ ✓ Pushed to github

Summary: 2/2 remotes successful

Press Enter to continue...
```

## Repository Status View
```
📊 Repository Status
==============================
🌿 Current branch: main

📝 Working Directory Status:
On branch main
Your branch is up to date with 'origin/main'.

Changes to be committed:
  (use "git reset HEAD <file>..." to unstage)
        modified:   src/main.py

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
        modified:   README.md

📜 Recent commits:
a1b2c3d Add new feature and update docs
e4f5g6h Fix bug in user authentication
h7i8j9k Update dependencies
k0l1m2n Initial commit

Press Enter to continue...
```

## Remote Management
```
🔗 Remote Management
=========================
Current remotes:
  origin: https://github.com/user/repo.git (default)
  backup: https://gitlab.com/user/repo.git
  github: https://github.com/user/repo-mirror.git

Remote Operations:
  1. Add remote
  2. Remove remote
  3. List remotes
  4. Change remote URL
  5. Set default remote
  6. Back to main menu

Enter choice number: 1

Remote name [origin]: backup
Remote URL: https://gitlab.com/user/repo.git
🔄 Adding remote 'backup'...
✅ Remote 'backup' added successfully!

Press Enter to continue...
```

## Branch Operations
```
🌿 Branch Operations
=========================
Current branch: main

Branch Operations:
  1. Create new branch
  2. Switch to existing branch
  3. List all branches
  4. Delete branch
  5. Back to main menu

Enter choice number: 1

Enter new branch name: feature/new-dashboard
🔄 Creating new branch: feature/new-dashboard
✅ Created and switched to branch: feature/new-dashboard

Press Enter to continue...
```

## Configuration Menu
```
⚙️ Configuration
====================
Name: John Doe
Email: john@example.com
Default Branch: main
Default Remote: origin
Auto Push: True
Show Emoji: True
------------------------------
Configuration Options:
  1. Set Name
  2. Set Email
  3. Set Default Branch
  4. Set Default Remote
  5. Toggle Auto Push
  6. Toggle Emoji
  7. Back to main menu

Enter choice number: 5
✅ Auto Push disabled!
```

## Direct Commands

### `gw status`
```
📊 Repository Status
==============================
🌿 Current branch: main

📝 Working Directory Status:
On branch main
nothing to commit, working tree clean

📜 Recent commits:
a1b2c3d Add new feature and update docs
e4f5g6h Fix bug in user authentication
h7i8j9k Update dependencies

Press Enter to continue...
```

### `gw commit`
```
💾 Quick Commit
====================
Files to be added:
 M src/main.py

Add all changes? [Y/n]: y

Enter commit message: Fix authentication bug
🔄 Adding all changes...
🔄 Committing with message: 'Fix authentication bug'
✅ Commit successful!
Push to remote(s)? [Y/n]: n

Press Enter to continue...
```

### `gw sync`
```
🔄 Sync Repository
====================
Branch to sync [main]: main

Select remote for sync:
  1. origin (default)
  2. backup

Enter choice number: 1
🔄 Syncing with origin/main
🔄 Pulling latest changes...
🔄 Pushing local commits...
✅ Sync completed successfully!

Press Enter to continue...
```

### `gw push`
Opens the full push operations menu shown above.

### `gw config`
Opens the configuration menu shown above.

## Error Messages
```
❌ Git command failed: git push origin main
Details: error: failed to push some refs to 'origin'

Press Enter to continue...
```

## Confirmation Prompts
```
Are you sure you want to delete branch 'old-feature'? [y/N]: n
```

```
Push main to ALL 3 remotes? [y/N]: y
```
