#!/usr/bin/env bash

# You may want to detect your distribution and use the appropriate package manager.
# Below is an example assuming a Debian/Ubuntu-based system (apt). 
# Adjust for Fedora (dnf), CentOS (yum), Arch (pacman), etc.

# ---------------------------------------------------------------
# 1. Check Python 3.9+ installation
# ---------------------------------------------------------------
PY_VERSION=$(python3 --version 2>/dev/null | awk '{print $2}')
if [ -z "$PY_VERSION" ]; then
    echo "Python 3 not found. Installing latest Python via apt..."
    sudo apt-get update
    # If you specifically want Python 3.9+ on older distros, you may need a PPA or a different approach
    sudo apt-get install -y python3 python3-pip python3-venv
else
    echo "Found Python version: $PY_VERSION"
fi

PY_VERSION=$(python3 --version 2>/dev/null | awk '{print $2}')  # re-check after install
IFS='.' read -ra VER <<< "$PY_VERSION"
PY_MAJOR=${VER[0]}
PY_MINOR=${VER[1]}

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
    echo "Your system Python is less than 3.9."
    echo "You may need to install a newer Python version from a PPA or source. Exiting..."
    exit 1
fi

# ---------------------------------------------------------------
# 2. Ensure pip and venv are set up
# ---------------------------------------------------------------
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv
python3 -m pip install --upgrade pip

# ---------------------------------------------------------------
# 3. Create the virtual environment (.vitutf)
# ---------------------------------------------------------------
if [ -d ".vitutf" ]; then
    echo "Virtual environment '.vitutf' already exists. Skipping creation."
else
    python3 -m venv .vitutf
    echo "Created virtual environment in .vitutf"
fi

# ---------------------------------------------------------------
# 4. Ensure .gitignore exists and ignores .vitutf
# ---------------------------------------------------------------
if [ ! -f ".gitignore" ]; then
    echo ".gitignore not found. Creating .gitignore."
    echo ".vitutf" > .gitignore
else
    if ! grep -Fxq ".vitutf" .gitignore; then
        echo ".vitutf" >> .gitignore
        echo "Added '.vitutf' to .gitignore."
    else
        echo "'.vitutf' is already in .gitignore."
    fi
fi

# ---------------------------------------------------------------
# 5. Install python packages from requirements.txt
# ---------------------------------------------------------------
source .vitutf/bin/activate
if [ -f "requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "No requirements.txt found. Skipping package installation."
fi

# ---------------------------------------------------------------
# 6. Launch Streamlit application (RedTeam_Home.py)
# ---------------------------------------------------------------
echo "Launching the Streamlit application..."
streamlit run Home.py
