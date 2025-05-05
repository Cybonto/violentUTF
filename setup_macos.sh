#!/usr/bin/env bash

# ---------------------------------------------------------------
# This script assumes Python 3.9+ is already installed on your system.
# It does NOT check for Python or install it. 
# ---------------------------------------------------------------

# ---------------------------------------------------------------
# 2. Install/upgrade pip and venv-related packages
# ---------------------------------------------------------------
python3 -m ensurepip --upgrade 2>/dev/null
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
    pip cache purge
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
