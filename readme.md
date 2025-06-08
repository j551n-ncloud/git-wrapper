# Interactive Git Wrapper (gw)

![License](https://img.shields.io/badge/license-MIT-green)
![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)
![Git Version](https://img.shields.io/badge/git-2.0%2B-red)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![Status](https://img.shields.io/badge/status-stable-brightgreen)
![Version](https://img.shields.io/badge/version-1.0.0-orange)

🚀 A user-friendly, interactive command-line interface for Git operations that simplifies version control with intuitive menus and smart defaults.

**Created by:** [Johannes Nguyen](https://j551n.com)

## Features

- **Interactive Menu System**: Navigate Git operations through numbered menus
- **Smart Repository Detection**: Automatically detects Git repositories and adapts interface
- **Visual Feedback**: Emoji indicators and colored output for better user experience
- **Configuration Management**: Save and manage user preferences
- **Quick Commands**: Direct command execution for common operations
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Beginner Friendly**: Clear prompts and confirmations for destructive operations

## Quick Start

```bash
# Interactive mode
gw

# Direct commands
gw status    # Show repository status
gw commit    # Quick commit workflow
gw sync      # Pull and push changes
gw config    # Open configuration menu
```

## Installation

### Prerequisites

- **Git**: Must be installed and available in your system PATH
- **Python 3.6+**: Required to run the script

### Option 1: Quick Install (Recommended)

#### macOS and Linux

```bash
# Download the script
curl -O https://raw.githubusercontent.com/yourusername/git-wrapper/main/gw.py

# Make it executable
chmod +x gw.py

# Move to a directory in your PATH
sudo mv gw.py /usr/local/bin/gw

# Test installation
gw --help
```

#### Windows (PowerShell)

```powershell
# Download the script
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/yourusername/git-wrapper/main/gw.py" -OutFile "gw.py"

# Create a batch file wrapper
@echo off
python "%~dp0gw.py" %*
# Save this as gw.bat

# Move both files to a directory in your PATH (e.g., C:\Windows\System32)
# Or add the directory containing the files to your PATH
```

### Option 2: Manual Installation

#### macOS

1. **Install Git and Python** (if not already installed):
   ```bash
   # Install Homebrew (if not installed)
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   
   # Install Git and Python
   brew install git python
   ```

2. **Download and setup the script**:
   ```bash
   # Create a directory for local scripts
   mkdir -p ~/.local/bin
   
   # Download the script
   curl -o ~/.local/bin/gw.py https://raw.githubusercontent.com/yourusername/git-wrapper/main/gw.py
   
   # Make it executable
   chmod +x ~/.local/bin/gw.py
   
   # Create a symlink for easier access
   ln -s ~/.local/bin/gw.py ~/.local/bin/gw
   
   # Add to PATH (add this line to your ~/.zshrc or ~/.bash_profile)
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
   
   # Reload your shell configuration
   source ~/.zshrc
   ```

#### Linux (Ubuntu/Debian)

1. **Install Git and Python**:
   ```bash
   sudo apt update
   sudo apt install git python3 python3-pip curl
   ```

2. **Download and setup the script**:
   ```bash
   # Create a directory for local scripts
   mkdir -p ~/.local/bin
   
   # Download the script
   curl -o ~/.local/bin/gw.py https://raw.githubusercontent.com/yourusername/git-wrapper/main/gw.py
   
   # Make it executable
   chmod +x ~/.local/bin/gw.py
   
   # Create a symlink
   ln -s ~/.local/bin/gw.py ~/.local/bin/gw
   
   # Add to PATH (add this line to your ~/.bashrc or ~/.zshrc)
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   
   # Reload your shell configuration
   source ~/.bashrc
   ```

#### Linux (CentOS/RHEL/Fedora)

1. **Install Git and Python**:
   ```bash
   # For CentOS/RHEL
   sudo yum install git python3 curl
   
   # For Fedora
   sudo dnf install git python3 curl
   ```

2. **Follow the same setup steps as Ubuntu/Debian above**

#### Windows

1. **Install Git and Python**:
   - Download and install Git from [git-scm.com](https://git-scm.com/download/win)
   - Download and install Python from [python.org](https://www.python.org/downloads/windows/)
   - During Python installation, make sure to check "Add Python to PATH"

2. **Download and setup the script**:
   ```powershell
   # Create a directory for scripts
   New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\bin"
   
   # Download the script
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/yourusername/git-wrapper/main/gw.py" -OutFile "$env:USERPROFILE\bin\gw.py"
   
   # Create a batch file wrapper
   @"
   @echo off
   python "$env:USERPROFILE\bin\gw.py" %*
   "@ | Out-File -FilePath "$env:USERPROFILE\bin\gw.bat" -Encoding ascii
   
   # Add to PATH (run this in an Administrator PowerShell)
   $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
   [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$env:USERPROFILE\bin", "User")
   ```

3. **Alternative Windows Installation using Chocolatey**:
   ```powershell
   # Install Chocolatey (if not installed)
   Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   
   # Install Git and Python
   choco install git python
   
   # Then follow the manual setup steps above
   ```

### Option 3: Development Installation

If you want to contribute or modify the script:

```bash
# Clone the repository
git clone https://github.com/yourusername/git-wrapper.git
cd git-wrapper

# Make it executable
chmod +x gw.py

# Create a symlink to your local bin
ln -s $(pwd)/gw.py ~/.local/bin/gw

# Or add the project directory to your PATH
echo 'export PATH="$(pwd):$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Verification

Test your installation:

```bash
# Check if gw is accessible
gw

# Verify Git is available
git --version

# Check Python version
python --version  # or python3 --version on some systems
```

## Usage

### Interactive Mode

Simply run `gw` to enter the interactive menu system:

```bash
gw
```

The interface will show:
- Current directory and Git repository status
- Available operations based on repository state
- Branch information and uncommitted changes

### Direct Commands

Execute specific operations directly:

```bash
gw status    # Show detailed repository status
gw commit    # Interactive commit workflow
gw sync      # Pull latest changes and push commits
gw config    # Open configuration settings
```

### First-Time Setup

1. Run `gw config` to set up your Git configuration:
   - Set your name and email
   - Configure default branch (main/master)
   - Set preferences for auto-push and emoji display

2. Navigate to a Git repository or initialize a new one using the interface

## Configuration

The wrapper stores configuration in `~/.gitwrapper_config.json`:

```json
{
  "name": "Your Name",
  "email": "your.email@example.com",
  "default_branch": "main",
  "auto_push": true,
  "show_emoji": true
}
```

## Troubleshooting

### Common Issues

1. **"Git is not installed or not available in PATH"**
   - Install Git or ensure it's in your system PATH
   - Test with `git --version`

2. **"gw: command not found"**
   - The script isn't in your PATH
   - Use the full path to the script or follow installation steps again

3. **Permission denied**
   - Make sure the script is executable: `chmod +x gw.py`

4. **Python not found**
   - Install Python 3.6+ or use `python3` instead of `python`

### Windows-Specific Issues

1. **Script doesn't run**
   - Ensure Python is in your PATH
   - Try running: `python gw.py` instead of `gw`

2. **Emoji display issues**
   - Use Windows Terminal or ConEmu for better Unicode support
   - Disable emojis in configuration if needed

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test on multiple platforms
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- Create an issue on GitHub for bugs or feature requests
- Check existing issues for solutions to common problems
- Contribute improvements and fixes via pull requests
