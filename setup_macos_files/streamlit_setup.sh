#!/usr/bin/env bash
# streamlit_setup.sh - Streamlit installation and setup functions

# Function to find the best Python interpreter
find_python() {
    local python_cmd=""
    
    # Check common Python commands in order of preference
    for cmd in python3.11 python3.10 python3.9 python3.8 python3 python; do
        if command -v $cmd &> /dev/null; then
            local version=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
            local major=$(echo $version | cut -d. -f1)
            local minor=$(echo $version | cut -d. -f2)
            
            # Ensure Python 3.8+ for Streamlit compatibility
            if [ "$major" -eq 3 ] && [ "$minor" -ge 8 ]; then
                python_cmd=$cmd
                echo "Found Python: $cmd (version $version)"
                break
            fi
        fi
    done
    
    if [ -z "$python_cmd" ]; then
        echo "❌ No suitable Python found (requires Python 3.8+)"
        return 1
    fi
    
    echo "$python_cmd"
}

# Function to setup Python virtual environment
setup_python_venv() {
    local venv_dir="$1"
    local python_cmd="${2:-python3}"
    
    echo "🐍 Setting up Python virtual environment..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$venv_dir" ]; then
        echo "Creating new virtual environment at $venv_dir..."
        $python_cmd -m venv "$venv_dir"
        
        if [ $? -ne 0 ]; then
            echo "❌ Failed to create virtual environment"
            echo "Trying to install venv module..."
            
            # Try to install python3-venv if on Ubuntu/Debian
            if command -v apt-get &> /dev/null; then
                echo "Installing python3-venv package..."
                sudo apt-get update && sudo apt-get install -y python3-venv
            fi
            
            # Retry creating venv
            $python_cmd -m venv "$venv_dir" || return 1
        fi
    fi
    
    # Activate virtual environment
    if [ -f "$venv_dir/bin/activate" ]; then
        source "$venv_dir/bin/activate"
        echo "✅ Virtual environment activated"
    else
        echo "❌ Failed to activate virtual environment"
        return 1
    fi
    
    # Upgrade pip
    echo "Upgrading pip..."
    python -m pip install --upgrade pip --quiet
    
    return 0
}

# Function to install Streamlit and dependencies
install_streamlit_dependencies() {
    local requirements_file="$1"
    
    echo "📦 Installing Streamlit and dependencies..."
    
    # Check if we're in a virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        echo "⚠️  Warning: Not in a virtual environment"
    fi
    
    # Install Streamlit
    echo "Installing Streamlit..."
    python -m pip install streamlit --quiet
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install Streamlit"
        return 1
    fi
    
    # Install from requirements.txt if it exists
    if [ -f "$requirements_file" ]; then
        echo "Installing dependencies from requirements.txt..."
        python -m pip install -r "$requirements_file" --quiet
    else
        echo "Installing common ViolentUTF dependencies..."
        # Install common dependencies for ViolentUTF
        python -m pip install \
            streamlit-authenticator \
            streamlit-option-menu \
            pyrit \
            garak \
            duckdb \
            pandas \
            numpy \
            pydantic \
            httpx \
            aiohttp \
            python-jose \
            python-multipart \
            --quiet
    fi
    
    echo "✅ Dependencies installed successfully"
    return 0
}

# Main function to check and setup Streamlit
check_and_setup_streamlit() {
    local violentutf_dir="${1:-violentutf}"
    
    echo ""
    echo "🔍 Checking Streamlit installation..."
    
    # Change to violentutf directory
    if [ ! -d "$violentutf_dir" ]; then
        echo "❌ ViolentUTF directory not found at $violentutf_dir"
        return 1
    fi
    
    cd "$violentutf_dir" || return 1
    
    # Check for virtual environment
    local venv_dir=".venv"
    local using_venv=false
    
    if [ -d "$venv_dir" ]; then
        echo "Found existing virtual environment"
        source "$venv_dir/bin/activate"
        using_venv=true
    fi
    
    # Check if Streamlit is installed
    if command -v streamlit &> /dev/null; then
        local streamlit_version=$(streamlit --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        echo "✅ Streamlit is already installed (version $streamlit_version)"
        
        # Verify it works
        if python -c "import streamlit" 2>/dev/null; then
            echo "✅ Streamlit import test passed"
            cd .. || true
            return 0
        else
            echo "⚠️  Streamlit command found but import failed, reinstalling..."
        fi
    else
        echo "📋 Streamlit not found, will install it"
    fi
    
    # If not using venv, create one
    if [ "$using_venv" = false ]; then
        echo "No virtual environment found, creating one..."
        
        # Find suitable Python
        local python_cmd=$(find_python)
        if [ -z "$python_cmd" ]; then
            echo "❌ Cannot proceed without Python 3.8+"
            cd .. || true
            return 1
        fi
        
        # Setup virtual environment
        if ! setup_python_venv "$venv_dir" "$python_cmd"; then
            echo "❌ Failed to setup virtual environment"
            cd .. || true
            return 1
        fi
    fi
    
    # Install Streamlit and dependencies
    local requirements_file="requirements.txt"
    if ! install_streamlit_dependencies "$requirements_file"; then
        echo "❌ Failed to install Streamlit dependencies"
        cd .. || true
        return 1
    fi
    
    # Final verification
    if command -v streamlit &> /dev/null && python -c "import streamlit" 2>/dev/null; then
        echo "✅ Streamlit setup completed successfully"
        cd .. || true
        return 0
    else
        echo "❌ Streamlit setup verification failed"
        cd .. || true
        return 1
    fi
}

# Function to ensure Streamlit is ready before launching
ensure_streamlit_ready() {
    local violentutf_dir="${1:-violentutf}"
    
    echo "🚀 Preparing to launch Streamlit..."
    
    # First check and setup if needed
    if ! check_and_setup_streamlit "$violentutf_dir"; then
        echo "❌ Failed to setup Streamlit"
        return 1
    fi
    
    # Additional checks for runtime requirements
    cd "$violentutf_dir" || return 1
    
    # Check for Home.py
    if [ ! -f "Home.py" ]; then
        echo "❌ Home.py not found in $violentutf_dir"
        cd .. || true
        return 1
    fi
    
    # Check for critical directories
    for dir in pages utils app_data; do
        if [ ! -d "$dir" ]; then
            echo "⚠️  Creating missing directory: $dir"
            mkdir -p "$dir"
        fi
    done
    
    # Check for .streamlit directory and config
    if [ ! -d ".streamlit" ]; then
        echo "⚠️  Creating .streamlit directory"
        mkdir -p .streamlit
    fi
    
    cd .. || true
    echo "✅ Streamlit is ready to launch"
    return 0
}