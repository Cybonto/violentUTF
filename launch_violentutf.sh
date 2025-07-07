#!/bin/bash

# ViolentUTF Streamlit Application Launcher
# This script provides multiple options to launch the Streamlit app

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "=========================================="
echo "🚀 ViolentUTF Application Launcher"
echo "=========================================="

# Source the streamlit setup functions if available
if [ -f "setup_macos_files/streamlit_setup.sh" ]; then
    source setup_macos_files/streamlit_setup.sh
    
    # Check and setup Streamlit environment
    if ! ensure_streamlit_ready "violentutf"; then
        echo -e "${RED}Failed to setup Streamlit environment${NC}"
        exit 1
    fi
    
    # Re-activate venv after setup (in case it was created)
    if [ -d "violentutf/.vitutf" ]; then
        source violentutf/.vitutf/bin/activate
    fi
else
    # Fallback to old method
    if [ -d "violentutf/.vitutf" ]; then
        echo "🐍 Activating Python virtual environment..."
        source violentutf/.vitutf/bin/activate
    elif [ -d ".vitutf" ]; then
        echo "🐍 Activating Python virtual environment..."
        source .vitutf/bin/activate
    else
        echo -e "${YELLOW}Warning: Virtual environment not found, using system Python${NC}"
    fi
fi

# Check if Home.py exists
if [ -f "violentutf/Home.py" ]; then
    APP_PATH="violentutf/Home.py"
    APP_DIR="violentutf"
elif [ -f "Home.py" ]; then
    APP_PATH="Home.py"
    APP_DIR="."
else
    echo -e "${RED}Error: Home.py not found!${NC}"
    exit 1
fi

# Function to check if Streamlit is already running
check_streamlit_running() {
    if lsof -ti:8501 > /dev/null 2>&1; then
        echo -e "${YELLOW}Warning: Streamlit appears to be already running on port 8501${NC}"
        echo "PID: $(lsof -ti:8501)"
        read -p "Do you want to kill the existing process? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill $(lsof -ti:8501)
            sleep 2
        else
            echo "Exiting without launching new instance."
            exit 0
        fi
    fi
}

# Function to launch in new terminal
launch_new_terminal() {
    # Create a launch script with full paths
    cat > /tmp/launch_violentutf_session.sh <<EOF
#!/bin/bash
cd "$SCRIPT_DIR"
if [ -d "violentutf/.vitutf" ]; then
    source violentutf/.vitutf/bin/activate
elif [ -d ".vitutf" ]; then
    source .vitutf/bin/activate
fi
echo "🚀 Starting ViolentUTF application..."
echo "   Access the app at: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""
# Change to app directory and run streamlit
cd "$SCRIPT_DIR/$APP_DIR"
streamlit run "$(basename "$SCRIPT_DIR/$APP_PATH")"
EOF
    chmod +x /tmp/launch_violentutf_session.sh
    osascript -e 'tell app "Terminal" to do script "/tmp/launch_violentutf_session.sh"'
}

# Check if streamlit is already running
check_streamlit_running

# Show launch options
echo ""
echo "Launch Options:"
echo "1) New Terminal window (recommended)"
echo "2) Background process (logs to file)"
echo "3) Foreground (current terminal)"
echo "4) Cancel"
echo ""
read -p "Select option (1-4) [1]: " choice
choice=${choice:-1}

case $choice in
    1)
        echo -e "${GREEN}Launching in new Terminal window...${NC}"
        launch_new_terminal
        echo -e "${GREEN}✓ Launched successfully!${NC}"
        echo "Access the app at: http://localhost:8501"
        ;;
    2)
        echo -e "${GREEN}Launching in background...${NC}"
        mkdir -p violentutf_logs
        cd $APP_DIR
        nohup streamlit run $(basename $APP_PATH) > ../violentutf_logs/streamlit.log 2>&1 &
        PID=$!
        cd ..
        echo -e "${GREEN}✓ Launched successfully!${NC}"
        echo "PID: $PID"
        echo "Access the app at: http://localhost:8501"
        echo "Logs: violentutf_logs/streamlit.log"
        echo "Stop with: kill $PID"
        ;;
    3)
        echo -e "${GREEN}Launching in foreground...${NC}"
        echo "Press Ctrl+C to stop"
        cd $APP_DIR
        streamlit run $(basename $APP_PATH)
        cd ..
        ;;
    4)
        echo "Launch cancelled."
        ;;
    *)
        echo -e "${RED}Invalid option${NC}"
        exit 1
        ;;
esac