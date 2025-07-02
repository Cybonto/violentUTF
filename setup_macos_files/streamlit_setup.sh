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
                # Print info to stderr so it doesn't interfere with return value
                echo "Found Python: $cmd (version $version)" >&2
                break
            fi
        fi
    done
    
    if [ -z "$python_cmd" ]; then
        echo "❌ No suitable Python found (requires Python 3.8+)" >&2
        return 1
    fi
    
    # Only return the command itself
    echo "$python_cmd"
}

# Function to setup Python virtual environment
setup_python_venv() {
    local venv_dir="$1"
    local python_cmd="${2:-python3}"
    
    echo "🐍 Setting up Python virtual environment..."
    echo "Using Python command: $python_cmd"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$venv_dir" ]; then
        echo "Creating new virtual environment at $venv_dir..."
        
        # Try different methods to create virtual environment
        if ! $python_cmd -m venv "$venv_dir" 2>/dev/null; then
            echo "⚠️  First attempt failed, trying alternative methods..."
            
            # Try virtualenv if available
            if command -v virtualenv &> /dev/null; then
                echo "Using virtualenv command..."
                virtualenv -p $python_cmd "$venv_dir"
            elif $python_cmd -m pip show virtualenv &> /dev/null; then
                echo "Using python -m virtualenv..."
                $python_cmd -m virtualenv "$venv_dir"
            else
                echo "Installing virtualenv..."
                $python_cmd -m pip install virtualenv
                if [ $? -eq 0 ]; then
                    $python_cmd -m virtualenv "$venv_dir"
                else
                    # Last resort: try to install python3-venv if on Ubuntu/Debian
                    if command -v apt-get &> /dev/null; then
                        echo "Installing python3-venv package..."
                        sudo apt-get update && sudo apt-get install -y python3-venv
                        $python_cmd -m venv "$venv_dir"
                    else
                        echo "❌ Failed to create virtual environment"
                        return 1
                    fi
                fi
            fi
        fi
        
        # Verify virtual environment was created
        if [ ! -d "$venv_dir" ] || [ ! -f "$venv_dir/bin/activate" ]; then
            echo "❌ Virtual environment creation failed"
            return 1
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
    
    # Upgrade pip - use the python from virtual environment
    echo "Upgrading pip..."
    if command -v python &> /dev/null; then
        python -m pip install --upgrade pip --quiet
    elif command -v python3 &> /dev/null; then
        python3 -m pip install --upgrade pip --quiet
    else
        $python_cmd -m pip install --upgrade pip --quiet
    fi
    
    return 0
}

# Function to install Streamlit and dependencies
install_streamlit_dependencies() {
    local requirements_file="$1"
    
    echo "📦 Installing Streamlit and dependencies..."
    
    # Determine which python command to use
    local pip_cmd="python -m pip"
    if ! command -v python &> /dev/null; then
        if command -v python3 &> /dev/null; then
            pip_cmd="python3 -m pip"
        else
            echo "❌ No Python command found in PATH"
            return 1
        fi
    fi
    
    # Check if we're in a virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        echo "⚠️  Warning: Not in a virtual environment"
    fi
    
    # Install Streamlit
    echo "Installing Streamlit..."
    $pip_cmd install streamlit --quiet
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install Streamlit"
        return 1
    fi
    
    # Install from requirements.txt if it exists
    if [ -f "$requirements_file" ]; then
        echo "Installing dependencies from requirements.txt..."
        $pip_cmd install -r "$requirements_file" --quiet
    else
        echo "Installing common ViolentUTF dependencies..."
        # Install common dependencies for ViolentUTF
        $pip_cmd install \
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
    
    # Determine which python command to use for testing
    local test_python_cmd="python"
    if ! command -v python &> /dev/null; then
        if command -v python3 &> /dev/null; then
            test_python_cmd="python3"
        fi
    fi
    
    # Check if Streamlit is installed
    if command -v streamlit &> /dev/null; then
        local streamlit_version=$(streamlit --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        echo "✅ Streamlit is already installed (version $streamlit_version)"
        
        # Verify it works
        if $test_python_cmd -c "import streamlit" 2>/dev/null; then
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
    
    # Final verification - determine which python to use
    local verify_python_cmd="python"
    if ! command -v python &> /dev/null; then
        if command -v python3 &> /dev/null; then
            verify_python_cmd="python3"
        fi
    fi
    
    # Final verification
    if command -v streamlit &> /dev/null && $verify_python_cmd -c "import streamlit" 2>/dev/null; then
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