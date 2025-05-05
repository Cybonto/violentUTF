cd # Setup Notes for OllaDeck - Red Teaming Home
## For Windows
- This script uses winget for installing Python. If you prefer Chocolatey or any other package manager, replace that portion accordingly.
- py --version is the recommended approach on Windows to use the Python launcher.
- After Python is installed via winget, you may need to open a new terminal or rerun the script to ensure the Python path is recognized.
## For Mac OS
- You need to install Python version 3.9 or above before running the script
- You need to make the script executable
```
chmod +x setup_macos.sh
```

## For Linux
- This example script is tailored to Debian/Ubuntu using apt-get.
- For Fedora, CentOS, Arch, or other distros, replace the package manager commands as appropriate (dnf, yum, pacman, etc.).
- If your distribution’s python3 is older than 3.9, you may need an additional repository (e.g., ppa:deadsnakes/ppa for Ubuntu) or compile from source.
- You need to make the script executable before running it
```
chmod +x setup_linux.sh
```
