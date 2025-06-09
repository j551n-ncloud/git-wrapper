# Interactive Git Wrapper (gw)

![License](https://img.shields.io/badge/license-MIT-green)
![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)
![Git Version](https://img.shields.io/badge/git-2.0%2B-red)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![Status](https://img.shields.io/badge/status-stable-brightgreen)

🚀 **A powerful, user-friendly interactive command-line interface for Git operations** that transforms complex Git workflows into intuitive menu-driven experiences. Perfect for developers who want to streamline their version control workflow without memorizing complex Git commands.

**Created by:** [Johannes Nguyen](https://j551n.com)

---

## ✨ Key Features

### 🎯 **Multi-Remote Management**
- Push to single, multiple, or all remotes with one command
- Set default remotes for streamlined operations
- Visual feedback for multi-remote operations
- Intelligent remote detection and configuration

### 🌿 **Advanced Branch Operations**
- Interactive branch creation and switching
- Safe branch deletion with confirmations
- Branch listing with current branch highlighting
- Seamless branch management workflow

### 📊 **Smart Repository Insights**
- Real-time repository status display
- Uncommitted changes detection
- Current branch information
- Clean working directory indicators

### ⚙️ **Intelligent Configuration**
- Persistent user preferences
- Auto-push capabilities
- Customizable emoji display
- Default branch and remote settings

### 🔄 **Streamlined Workflows**
- One-command sync (pull + push)
- Quick commit with interactive prompts
- Bulk operations across multiple remotes
- Repository initialization and cloning

---

## 🚀 Quick Start

### Interactive Mode
```bash
gw
```

### Direct Commands
```bash
gw status    # Show comprehensive repository status
gw commit    # Interactive commit workflow with smart prompts
gw sync      # Pull latest changes and push commits
gw config    # Open configuration management
gw push      # Advanced push operations menu
```

---

## 📦 Installation

### Prerequisites
- **Git 2.0+**: Must be installed and accessible in PATH
- **Python 3.6+**: Required runtime environment

### Quick Install (Recommended)

#### macOS & Linux
```bash
# Download and install in one command
curl -o /usr/local/bin/gw https://raw.githubusercontent.com/j551n-ncloud/git-wrapper/main/git_wrapper.py && chmod +x /usr/local/bin/gw

# Verify installation
gw
```

#### Windows (PowerShell as Administrator)
```powershell
# Create installation directory
$installDir = "$env:USERPROFILE\bin"
New-Item -ItemType Directory -Force -Path $installDir

# Download script
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/j551n-ncloud/git-wrapper/main/git_wrapper.py" -OutFile "$installDir\gw.py"

# Create wrapper batch file
@'
@echo off
python "%~dp0gw.py" %*
'@ | Out-File -FilePath "$installDir\gw.bat" -Encoding ascii

# Add to PATH
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$installDir*") {
    [Environment]::SetEnvironmentVariable("PATH", "$userPath;$installDir", "User")
}
```

### Manual Installation

#### macOS
```bash
# Install dependencies via Homebrew
brew install git python

# Create local bin directory
mkdir -p ~/.local/bin

# Download and setup
curl -o ~/.local/bin/gw https://raw.githubusercontent.com/j551n-ncloud/git-wrapper/main/git_wrapper.py
chmod +x ~/.local/bin/gw

# Add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### Ubuntu/Debian
```bash
# Install dependencies
sudo apt update && sudo apt install -y git python3 curl

# Setup script
mkdir -p ~/.local/bin
curl -o ~/.local/bin/gw https://raw.githubusercontent.com/j551n-ncloud/git-wrapper/main/git_wrapper.py
chmod +x ~/.local/bin/gw

# Add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### CentOS/RHEL/Fedora
```bash
# Install dependencies
# For CentOS/RHEL: sudo yum install -y git python3 curl
# For Fedora: sudo dnf install -y git python3 curl

# Follow same setup as Ubuntu
mkdir -p ~/.local/bin
curl -o ~/.local/bin/gw https://raw.githubusercontent.com/j551n-ncloud/git-wrapper/main/git_wrapper.py
chmod +x ~/.local/bin/gw

echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

## 🎮 Usage Guide

### Interactive Menu System

Launch the interactive interface:
```bash
gw
```

**Main Menu Features:**
- 📊 **Repository Status**: Comprehensive overview of your repo state
- 💾 **Quick Commit**: Streamlined commit process with smart prompts
- 🔄 **Sync Operations**: One-command pull and push workflow
- 📤 **Advanced Push**: Multi-remote push with granular control
- 🌿 **Branch Management**: Complete branch lifecycle operations
- 🔗 **Remote Management**: Add, remove, and configure remotes
- ⚙️ **Configuration**: Personalize your Git workflow

### Advanced Push Operations

The wrapper provides sophisticated push capabilities:

```bash
gw push
```

**Push Options:**
- **Single Remote**: Push to one selected remote
- **Multiple Remotes**: Choose specific remotes for push
- **All Remotes**: Push to every configured remote
- **Visual Feedback**: See success/failure for each remote

### Configuration Management

Customize your workflow:
```bash
gw config
```

**Configuration Options:**
- User name and email
- Default branch (main/master)
- Default remote preference
- Auto-push after commits
- Emoji display toggle

---

## 📁 Configuration

Settings are stored in `~/.gitwrapper_config.json`:

```json
{
  "name": "Johannes Nguyen",
  "email": "your.email@example.com",
  "default_branch": "main",
  "default_remote": "origin",
  "auto_push": true,
  "show_emoji": true
}
```

---

## 🔧 Troubleshooting

### Common Issues

**Command not found**
```bash
# Check if gw is in PATH
which gw

# If not found, add to PATH or use full path
export PATH="$PATH:/path/to/gw"
```

**Git not available**
```bash
# Verify Git installation
git --version

# Install if missing (macOS)
brew install git

# Install if missing (Ubuntu)
sudo apt install git
```

**Permission denied**
```bash
# Make script executable
chmod +x /path/to/gw
```

### Platform-Specific Issues

**Windows Unicode Issues**
- Use Windows Terminal for better emoji support
- Disable emojis in config if characters don't display properly

**macOS PATH Issues**
- Add to both `~/.bashrc` and `~/.zshrc` for compatibility
- Restart terminal after PATH changes

---

## 🌟 Advanced Features

### Multi-Remote Workflows
Perfect for developers maintaining multiple remotes (origin, upstream, mirrors):
- Push to development and production remotes simultaneously
- Selective remote operations with visual confirmation
- Default remote management for streamlined operations

### Repository Initialization
- Smart initialization with configuration inheritance
- Remote setup during initialization
- Branch naming consistency

### Branch Management
- Safe operations with confirmation prompts
- Current branch awareness
- Local and remote branch handling

---

## 🤝 Contributing

We welcome contributions! Here's how to get started:

```bash
# Fork and clone
git clone https://github.com/j551n-ncloud/git-wrapper.git
cd git-wrapper

# Create feature branch
git checkout -b feature/your-feature

# Make changes and test
python git_wrapper.py

# Commit and push
git add .
git commit -m "Add your feature"
git push origin feature/your-feature
```

**Contribution Guidelines:**
- Test on multiple platforms
- Follow existing code style
- Add documentation for new features
- Include error handling for edge cases

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🔗 Links

- **Homepage**: [https://j551n.com](https://j551n.com)
- **Repository**: [https://github.com/j551n-ncloud/git-wrapper](https://github.com/j551n-ncloud/git-wrapper)
- **Issues**: [Report bugs or request features](https://github.com/j551n-ncloud/git-wrapper/issues)

---

## 🎯 Why Use Git Wrapper?

**For Beginners:**
- No need to memorize complex Git commands
- Clear prompts and confirmations prevent mistakes
- Visual feedback makes Git operations transparent

**For Professionals:**
- Multi-remote operations save time
- Consistent workflows across projects
- Quick access to advanced Git features

**For Teams:**
- Standardized Git workflows
- Reduced training time for new developers
- Consistent branching and remote management

---

*Created with ❤️ by [Johannes Nguyen](https://j551n.com)*
