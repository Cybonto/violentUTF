#!/usr/bin/env bash
# streamlit_setup.sh - Streamlit application setup

# Function to ensure Streamlit is ready
ensure_streamlit_ready() {
    local streamlit_dir="$1"

    log_detail "Checking Streamlit environment..."

    # Check if virtual environment exists
    if [ ! -d "$streamlit_dir/.vitutf" ]; then
        log_progress "Creating Python virtual environment..."
        cd "$streamlit_dir"
        python3 -m venv .vitutf

        # Activate and install requirements
        source .vitutf/bin/activate

        if [ -f "requirements.txt" ]; then
            log_progress "Installing Python requirements..."
            pip install --upgrade pip
            pip install -r requirements.txt
        fi

        deactivate
        cd ..
    fi

    return 0
}

# Function to setup Streamlit
setup_streamlit() {
    log_detail "Setting up Streamlit application..."

    local STREAMLIT_DIR="violentutf"

    if [ ! -d "$STREAMLIT_DIR" ]; then
        log_error "Streamlit directory not found: $STREAMLIT_DIR"
        return 1
    fi

    # Ensure Streamlit environment is ready
    ensure_streamlit_ready "$STREAMLIT_DIR"

    log_success "Streamlit setup completed"
    return 0
}
