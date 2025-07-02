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
        echo ""
        echo "🐍 Creating new Python virtual environment..."
        echo "📍 Location: $(pwd)/$venv_dir"
        echo "🔧 Using Python: $python_cmd"
        
        # Try different methods to create virtual environment
        echo "⏳ Attempting to create virtual environment..."
        if ! $python_cmd -m venv "$venv_dir"; then
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
        
        # Verify activation worked
        if [ -z "$VIRTUAL_ENV" ]; then
            echo "❌ Virtual environment activation failed (VIRTUAL_ENV not set)"
            return 1
        fi
        
        echo "✅ Virtual environment activated at: $VIRTUAL_ENV"
        
        # Force PATH update to ensure venv binaries are found first
        export PATH="$VIRTUAL_ENV/bin:$PATH"
    else
        echo "❌ Failed to activate virtual environment"
        return 1
    fi
    
    # Upgrade pip - use the python from virtual environment
    echo "📦 Upgrading pip to latest version..."
    if command -v python &> /dev/null; then
        python -m pip install --upgrade pip
    elif command -v python3 &> /dev/null; then
        python3 -m pip install --upgrade pip
    else
        $python_cmd -m pip install --upgrade pip
    fi
    echo "✅ Pip upgraded successfully"
    
    return 0
}

# Function to install Streamlit and dependencies
install_streamlit_dependencies() {
    local requirements_file="$1"
    
    echo "📦 Installing Streamlit and dependencies..."
    
    # Determine which python command to use
    local pip_cmd=""
    
    # If in virtual environment, use its Python
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "📍 Using virtual environment at: $VIRTUAL_ENV"
        # In venv, python should always exist
        if [ -x "$VIRTUAL_ENV/bin/python" ]; then
            pip_cmd="$VIRTUAL_ENV/bin/python -m pip"
        else
            echo "❌ Virtual environment Python not found!"
            return 1
        fi
    else
        echo "⚠️  Warning: Not in a virtual environment"
        # Fall back to system Python
        if command -v python &> /dev/null; then
            pip_cmd="python -m pip"
        elif command -v python3 &> /dev/null; then
            pip_cmd="python3 -m pip"
        else
            echo "❌ No Python command found in PATH"
            return 1
        fi
    fi
    
    echo "📦 Using pip command: $pip_cmd"
    
    # Install Streamlit
    echo "Installing Streamlit..."
    echo "📦 Running: $pip_cmd install streamlit"
    echo "⏳ This may take a few minutes..."
    $pip_cmd install streamlit
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install Streamlit"
        return 1
    fi
    
    echo "✅ Streamlit installed successfully"
    
    # Install from requirements.txt if it exists
    if [ -f "$requirements_file" ]; then
        echo ""
        echo "📋 Found requirements.txt, installing dependencies..."
        echo "📦 Running: $pip_cmd install -r $requirements_file"
        echo "⏳ This may take several minutes..."
        $pip_cmd install -r "$requirements_file"
    else
        echo ""
        echo "📋 No requirements.txt found, installing common ViolentUTF dependencies..."
        echo "📦 Installing the following packages:"
        echo "   • python-dotenv (for environment variables)"
        echo "   • streamlit-authenticator (for authentication)"
        echo "   • streamlit-option-menu (for UI components)"
        echo "   • pyrit (Microsoft's AI Red Team framework)"
        echo "   • garak (LLM vulnerability scanner)"
        echo "   • duckdb (database for PyRIT)"
        echo "   • pandas, numpy (data processing)"
        echo "   • pydantic (data validation)"
        echo "   • httpx, aiohttp (HTTP clients)"
        echo "   • python-jose (JWT handling)"
        echo "   • python-multipart (form data)"
        echo ""
        echo "⏳ This may take several minutes..."
        # Install common dependencies for ViolentUTF
        $pip_cmd install \
            python-dotenv \
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
            python-multipart
    fi
    
    echo "✅ Dependencies installed successfully"
    
    # Quick check for python-dotenv since it's critical
    echo ""
    echo "🔍 Verifying critical dependencies..."
    if ! $pip_cmd show python-dotenv &> /dev/null; then
        echo "⚠️  python-dotenv not found, installing it now..."
        $pip_cmd install python-dotenv
    else
        echo "✅ python-dotenv is installed"
    fi
    
    return 0
}

# Main function to check and setup Streamlit
check_and_setup_streamlit() {
    local violentutf_dir="${1:-violentutf}"
    
    echo ""
    echo "===================================="
    echo "🔍 Checking Streamlit installation..."
    echo "===================================="
    
    # Change to violentutf directory
    if [ ! -d "$violentutf_dir" ]; then
        echo "❌ ViolentUTF directory not found at $violentutf_dir"
        return 1
    fi
    
    cd "$violentutf_dir" || return 1
    
    # Check for virtual environment
    local venv_dir=".vitutf"
    local using_venv=false
    
    if [ -d "$venv_dir" ]; then
        echo "Found existing virtual environment at $venv_dir"
        if [ -f "$venv_dir/bin/activate" ]; then
            source "$venv_dir/bin/activate"
            
            # Verify activation
            if [ -n "$VIRTUAL_ENV" ]; then
                using_venv=true
                # Ensure venv binaries are first in PATH
                export PATH="$VIRTUAL_ENV/bin:$PATH"
                echo "✅ Activated virtual environment: $VIRTUAL_ENV"
            else
                echo "⚠️  Failed to activate existing virtual environment"
                using_venv=false
            fi
        else
            echo "⚠️  Virtual environment missing activate script"
            using_venv=false
        fi
    fi
    
    # Determine which python command to use for testing
    local test_python_cmd=""
    local test_streamlit_cmd=""
    
    # If in venv, use venv commands
    if [ -n "$VIRTUAL_ENV" ]; then
        test_python_cmd="$VIRTUAL_ENV/bin/python"
        test_streamlit_cmd="$VIRTUAL_ENV/bin/streamlit"
    else
        # Use system commands
        if command -v python &> /dev/null; then
            test_python_cmd="python"
        elif command -v python3 &> /dev/null; then
            test_python_cmd="python3"
        fi
        test_streamlit_cmd="streamlit"
    fi
    
    # Check if Streamlit is installed in the right place
    if [ -n "$test_streamlit_cmd" ] && command -v "$test_streamlit_cmd" &> /dev/null; then
        local streamlit_version=$($test_streamlit_cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        echo "✅ Streamlit is already installed (version $streamlit_version)"
        echo "📍 Location: $(which $test_streamlit_cmd)"
        
        # Verify it works with the same Python
        if [ -n "$test_python_cmd" ] && $test_python_cmd -c "import streamlit" 2>/dev/null; then
            echo "✅ Streamlit import test passed"
            # Also verify python-dotenv while we're at it
            if $test_python_cmd -c "import dotenv" 2>/dev/null; then
                echo "✅ python-dotenv import test passed"
                cd .. || true
                return 0
            else
                echo "⚠️  python-dotenv import failed, will install dependencies"
            fi
        else
            echo "⚠️  Streamlit import failed, reinstalling..."
        fi
    else
        echo "📋 Streamlit not found in expected location, will install it"
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
    
    # Check if requirements.txt exists in current directory
    if [ -f "$requirements_file" ]; then
        echo "📋 Found requirements.txt in $(pwd)"
    else
        echo "📋 No requirements.txt found in $(pwd), will install default dependencies"
    fi
    
    if ! install_streamlit_dependencies "$requirements_file"; then
        echo "❌ Failed to install Streamlit dependencies"
        cd .. || true
        return 1
    fi
    
    # Final verification - use the same Python that installed packages
    local verify_python_cmd=""
    if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
        verify_python_cmd="$VIRTUAL_ENV/bin/python"
    elif command -v python &> /dev/null; then
        verify_python_cmd="python"
    elif command -v python3 &> /dev/null; then
        verify_python_cmd="python3"
    else
        echo "❌ No Python found for verification"
        cd .. || true
        return 1
    fi
    
    # Also ensure streamlit command is from venv if in venv
    local streamlit_cmd="streamlit"
    if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/streamlit" ]; then
        streamlit_cmd="$VIRTUAL_ENV/bin/streamlit"
    fi
    
    # Final verification
    if command -v "$streamlit_cmd" &> /dev/null && $verify_python_cmd -c "import streamlit" 2>/dev/null; then
        echo ""
        echo "===================================="
        echo "✅ Streamlit setup completed successfully!"
        echo "===================================="
        echo "📍 Virtual environment: $(pwd)/$venv_dir"
        echo "🔧 Python version: $($verify_python_cmd --version 2>&1)"
        echo "📍 Python location: $verify_python_cmd"
        echo "📦 Streamlit version: $($streamlit_cmd --version 2>&1)"
        echo "📍 Streamlit location: $(which $streamlit_cmd)"
        echo "🌐 Ready to launch at: http://localhost:8501"
        echo "===================================="
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