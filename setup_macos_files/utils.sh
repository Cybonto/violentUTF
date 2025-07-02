#!/usr/bin/env bash
# utils.sh - Common utility functions used across setup modules

# Function to generate a random secure string
generate_random_string() {
    local length=${1:-32}
    openssl rand -base64 32 | tr -d '\n' | tr -d '\r' | tr -d '/' | tr -d '+' | tr -d '=' | cut -c1-${length}
}

# Alias for compatibility
generate_secure_string() {
    generate_random_string "$@"
}

# Function to replace placeholder in a file with a value
replace_in_file() {
    local file="$1"
    local placeholder="$2"
    local value="$3"
    local description="$4"
    
    # For macOS compatibility, use sed with backup extension
    sed -i '' "s|${placeholder}|${value}|g" "$file"
    
    # Store for final report if description is provided
    if [ -n "$description" ]; then
        SENSITIVE_VALUES+=("$description: $value")
    fi
    
    echo "Replaced $placeholder in $file"
}

# Function to backup and prepare config file from template
backup_and_prepare_config() {
    local template_file="$1"
    local target_file="${template_file%.template}"
    local backup_suffix=$(date +"%Y%m%d%H%M%S")
    
    # Check if template exists
    if [ ! -f "$template_file" ]; then
        echo "Error: Template file $template_file not found!"
        return 1
    fi
    
    # Backup existing file if it exists
    if [ -f "$target_file" ]; then
        cp "$target_file" "${target_file}.bak${backup_suffix}"
        echo "Backed up $target_file to ${target_file}.bak${backup_suffix}"
    fi
    
    # Copy template to target
    cp "$template_file" "$target_file"
    echo "Created $target_file from template"
    
    return 0
}

# Alias for compatibility
prepare_config_from_template() {
    backup_and_prepare_config "$@"
}

# Function to gracefully shutdown ViolentUTF Streamlit server
graceful_streamlit_shutdown() {
    echo "Gracefully shutting down ViolentUTF Streamlit server..."
    
    # Find ViolentUTF Streamlit processes
    STREAMLIT_PIDS=()
    
    # Check for Home.py process (ViolentUTF main entry point)
    HOME_PY_PIDS=$(pgrep -f "streamlit.*Home.py" 2>/dev/null || true)
    if [ -n "$HOME_PY_PIDS" ]; then
        STREAMLIT_PIDS+=($HOME_PY_PIDS)
    fi
    
    # Check for violentutf directory processes
    VIOLENTUTF_PIDS=$(pgrep -f "streamlit.*violentutf" 2>/dev/null || true)
    if [ -n "$VIOLENTUTF_PIDS" ]; then
        STREAMLIT_PIDS+=($VIOLENTUTF_PIDS)
    fi
    
    # Remove duplicates and process shutdown
    UNIQUE_PIDS=($(printf "%s\n" "${STREAMLIT_PIDS[@]}" | sort -u))
    
    if [ ${#UNIQUE_PIDS[@]} -eq 0 ]; then
        echo "No ViolentUTF Streamlit processes found to shutdown"
        return 0
    fi
    
    echo "Found ${#UNIQUE_PIDS[@]} ViolentUTF Streamlit process(es) to shutdown gracefully"
    
    # Send SIGTERM for graceful shutdown
    for pid in "${UNIQUE_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "Sending graceful shutdown signal to process $pid..."
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done
    
    # Wait for graceful shutdown (up to 15 seconds)
    echo "Waiting for graceful shutdown (up to 15 seconds)..."
    WAIT_COUNT=0
    MAX_WAIT=15
    
    while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
        REMAINING_PIDS=()
        for pid in "${UNIQUE_PIDS[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                REMAINING_PIDS+=($pid)
            fi
        done
        
        if [ ${#REMAINING_PIDS[@]} -eq 0 ]; then
            echo "✅ All ViolentUTF Streamlit processes shutdown gracefully"
            break
        fi
        
        sleep 1
        WAIT_COUNT=$((WAIT_COUNT + 1))
    done
    
    # If processes still running, use SIGINT (Ctrl+C equivalent)
    REMAINING_PIDS=()
    for pid in "${UNIQUE_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            REMAINING_PIDS+=($pid)
        fi
    done
    
    if [ ${#REMAINING_PIDS[@]} -gt 0 ]; then
        echo "Some processes still running, sending interrupt signal (SIGINT)..."
        for pid in "${REMAINING_PIDS[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                kill -INT "$pid" 2>/dev/null || true
            fi
        done
        
        # Wait another 5 seconds
        sleep 5
        
        # Check again
        FINAL_REMAINING=()
        for pid in "${REMAINING_PIDS[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                FINAL_REMAINING+=($pid)
            fi
        done
        
        if [ ${#FINAL_REMAINING[@]} -gt 0 ]; then
            echo "⚠️  Some processes still running after graceful attempts, using force kill as last resort..."
            for pid in "${FINAL_REMAINING[@]}"; do
                if kill -0 "$pid" 2>/dev/null; then
                    kill -9 "$pid" 2>/dev/null || true
                fi
            done
        fi
    fi
    
    # Final cleanup: check port 8501 and handle any remaining processes
    if lsof -i :8501 > /dev/null 2>&1; then
        echo "Checking port 8501 for any remaining processes..."
        PORT_PIDS=$(lsof -ti :8501 2>/dev/null || true)
        if [ -n "$PORT_PIDS" ]; then
            echo "Found processes on port 8501, terminating..."
            for pid in $PORT_PIDS; do
                kill -9 "$pid" 2>/dev/null || true
            done
        fi
    fi
    
    echo "✅ ViolentUTF Streamlit server shutdown completed"
}

# Function to ensure Docker Compose files have shared network configuration
ensure_network_in_compose() {
    local compose_file="$1"
    local service_name="$2"
    
    if [ ! -f "$compose_file" ]; then
        echo "Warning: Compose file $compose_file not found"
        return 1
    fi
    
    # Check if the service already has the network configured
    if grep -q "vutf-network" "$compose_file"; then
        echo "Network already configured in $compose_file"
        return 0
    fi
    
    echo "Adding shared network configuration to $compose_file for service $service_name"
    
    # Add network configuration (this is a simplified version)
    # In practice, this would need more sophisticated YAML manipulation
    local backup_suffix=$(date +"%Y%m%d%H%M%S")
    cp "$compose_file" "${compose_file}.bak${backup_suffix}"
    
    # Add network configuration
    cat >> "$compose_file" << EOF

networks:
  vutf-network:
    external: true
EOF
    
    echo "Added network configuration to $compose_file"
}

# Function to test network connectivity between containers
test_network_connectivity() {
    local from_container="$1"
    local to_service="$2"
    local port="$3"
    
    # Find the container ID/name for the from_container
    local container_id=$(docker ps --filter "name=$from_container" --format "{{.ID}}" | head -n 1)
    
    if [ -z "$container_id" ]; then
        echo "Container $from_container not found"
        return 1
    fi
    
    # Test connectivity
    if docker exec "$container_id" nc -z "$to_service" "$port" 2>/dev/null; then
        echo "✅ Connection from $from_container to $to_service:$port successful"
        return 0
    else
        echo "❌ Connection from $from_container to $to_service:$port failed"
        return 1
    fi
}

# Function to run tests with proper formatting
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "Testing $test_name... "
    
    if eval "$test_command" >/dev/null 2>&1; then
        echo "✅ PASS"
        return 0
    else
        echo "❌ FAIL"
        return 1
    fi
}

# Function to generate all secrets upfront
generate_all_secrets() {
    echo ""
    echo "=========================================="
    echo "GENERATING ALL SECURE SECRETS"
    echo "=========================================="
    echo "Generating secure secrets for all services..."

    # Keycloak admin credentials (hardcoded in docker-compose)
    SENSITIVE_VALUES+=("Keycloak Admin Username: admin")
    SENSITIVE_VALUES+=("Keycloak Admin Password: admin")

    # Keycloak PostgreSQL password (for new setups)
    KEYCLOAK_POSTGRES_PASSWORD=$(generate_secure_string)
    SENSITIVE_VALUES+=("Keycloak PostgreSQL Password: $KEYCLOAK_POSTGRES_PASSWORD")

    # ViolentUTF application secrets
    VIOLENTUTF_CLIENT_SECRET=$(generate_secure_string)
    VIOLENTUTF_COOKIE_SECRET=$(generate_secure_string)
    VIOLENTUTF_PYRIT_SALT=$(generate_secure_string)
    VIOLENTUTF_API_KEY=$(generate_secure_string)
    VIOLENTUTF_USER_PASSWORD=$(generate_secure_string)
    SENSITIVE_VALUES+=("ViolentUTF Keycloak Client Secret: $VIOLENTUTF_CLIENT_SECRET")
    SENSITIVE_VALUES+=("ViolentUTF Cookie Secret: $VIOLENTUTF_COOKIE_SECRET")
    SENSITIVE_VALUES+=("ViolentUTF PyRIT DB Salt: $VIOLENTUTF_PYRIT_SALT")
    SENSITIVE_VALUES+=("ViolentUTF AI Gateway API Key: $VIOLENTUTF_API_KEY")
    SENSITIVE_VALUES+=("ViolentUTF User Password: $VIOLENTUTF_USER_PASSWORD")

    # APISIX secrets
    APISIX_ADMIN_KEY=$(generate_secure_string)
    APISIX_DASHBOARD_SECRET=$(generate_secure_string)
    APISIX_DASHBOARD_PASSWORD=$(generate_secure_string)
    APISIX_KEYRING_VALUE_1=$(generate_secure_string | cut -c1-16)
    APISIX_KEYRING_VALUE_2=$(generate_secure_string | cut -c1-16)
    APISIX_CLIENT_SECRET=$(generate_secure_string)
    SENSITIVE_VALUES+=("APISIX Admin API Key: $APISIX_ADMIN_KEY")
    SENSITIVE_VALUES+=("APISIX Dashboard Username: admin")
    SENSITIVE_VALUES+=("APISIX Dashboard JWT Secret: $APISIX_DASHBOARD_SECRET")
    SENSITIVE_VALUES+=("APISIX Dashboard Admin Password: $APISIX_DASHBOARD_PASSWORD")
    SENSITIVE_VALUES+=("APISIX Keyring Value 1: $APISIX_KEYRING_VALUE_1")
    SENSITIVE_VALUES+=("APISIX Keyring Value 2: $APISIX_KEYRING_VALUE_2")
    SENSITIVE_VALUES+=("APISIX Keycloak Client Secret: $APISIX_CLIENT_SECRET")

    # FastAPI secrets - ALWAYS regenerate for consistency
    echo "🆕 Generating new FastAPI secrets (ensuring fresh configuration)"
    FASTAPI_SECRET_KEY=$(generate_secure_string)
    FASTAPI_CLIENT_SECRET=$(generate_secure_string)
    FASTAPI_CLIENT_ID="violentutf-fastapi"
    SENSITIVE_VALUES+=("FastAPI JWT Secret Key: $FASTAPI_SECRET_KEY")
    SENSITIVE_VALUES+=("FastAPI Keycloak Client Secret: $FASTAPI_CLIENT_SECRET")

    # Export variables for use in other modules
    export KEYCLOAK_POSTGRES_PASSWORD
    export VIOLENTUTF_CLIENT_SECRET VIOLENTUTF_COOKIE_SECRET VIOLENTUTF_PYRIT_SALT
    export VIOLENTUTF_API_KEY VIOLENTUTF_USER_PASSWORD
    export APISIX_ADMIN_KEY APISIX_DASHBOARD_SECRET APISIX_DASHBOARD_PASSWORD
    export APISIX_KEYRING_VALUE_1 APISIX_KEYRING_VALUE_2 APISIX_CLIENT_SECRET
    export FASTAPI_SECRET_KEY FASTAPI_CLIENT_SECRET FASTAPI_CLIENT_ID

    echo "✅ Generated ${#SENSITIVE_VALUES[@]} secure secrets"
    return 0
}

# Function to display all generated secrets at the end of setup
display_generated_secrets() {
    echo ""
    echo "=================================================="
    echo "🔐 GENERATED SECRETS AND CREDENTIALS"
    echo "=================================================="
    echo ""
    echo "⚠️  IMPORTANT: Store these secrets securely!"
    echo "   These secrets are required for system operation and recovery."
    echo ""
    
    # Display secrets organized by service
    echo "🛡️  Authentication & API Keys:"
    echo "   FastAPI Secret Key: $FASTAPI_SECRET_KEY"
    echo "   ViolentUTF API Key: $VIOLENTUTF_API_KEY"
    echo "   PyRIT Database Salt: $VIOLENTUTF_PYRIT_SALT"
    echo ""
    
    echo "👤 User Account Credentials:"
    echo "   ViolentUTF User Password: $VIOLENTUTF_USER_PASSWORD"
    echo "   ViolentUTF Cookie Secret: $VIOLENTUTF_COOKIE_SECRET"
    echo "   Keycloak Admin: admin / admin (default)"
    echo ""
    
    echo "🔑 Service Client Secrets:"
    echo "   ViolentUTF Client Secret: $VIOLENTUTF_CLIENT_SECRET"
    echo "   FastAPI Client Secret: $FASTAPI_CLIENT_SECRET"
    echo "   APISIX Client Secret: $APISIX_CLIENT_SECRET"
    echo ""
    
    echo "🌐 APISIX Gateway Secrets:"
    echo "   APISIX Admin Key: $APISIX_ADMIN_KEY"
    echo "   APISIX Dashboard Secret: $APISIX_DASHBOARD_SECRET"
    echo "   APISIX Dashboard Password: $APISIX_DASHBOARD_PASSWORD"
    echo "   APISIX Keyring Value 1: $APISIX_KEYRING_VALUE_1"
    echo "   APISIX Keyring Value 2: $APISIX_KEYRING_VALUE_2"
    echo ""
    
    echo "🗄️  Database Credentials:"
    echo "   Keycloak Postgres Password: $KEYCLOAK_POSTGRES_PASSWORD"
    echo ""
    
    echo "=================================================="
    echo "💾 Secret Storage Locations:"
    echo "   • Keycloak: keycloak/.env"
    echo "   • APISIX: apisix/.env, apisix/conf/config.yaml, apisix/conf/dashboard.yaml"
    echo "   • ViolentUTF: violentutf/.env, violentutf/.streamlit/secrets.toml"
    echo "   • FastAPI: violentutf_api/fastapi_app/.env"
    echo "=================================================="
    echo ""
}

# Function to launch Streamlit in a new terminal window
launch_streamlit_in_new_terminal() {
    echo ""
    echo "🚀 Launching ViolentUTF Streamlit Web Interface..."
    
    # Get the current working directory
    local current_dir=$(pwd)
    local streamlit_dir="$current_dir/violentutf"
    
    # Check if violentutf directory exists
    if [ ! -d "$streamlit_dir" ]; then
        echo "❌ ViolentUTF directory not found at $streamlit_dir"
        return 1
    fi
    
    # Check and setup Streamlit if needed
    if [ -f "$SETUP_MODULES_DIR/streamlit_setup.sh" ]; then
        source "$SETUP_MODULES_DIR/streamlit_setup.sh"
        if ! ensure_streamlit_ready "$streamlit_dir"; then
            echo "❌ Failed to prepare Streamlit environment"
            return 1
        fi
    fi
    
    # Create a launch script that will be executed in the new terminal
    local launch_script="/tmp/launch_violentutf_streamlit.sh"
    cat > "$launch_script" <<EOF
#!/bin/bash
echo "🌟 Starting ViolentUTF Streamlit Application..."
echo "📂 Working directory: $streamlit_dir"
echo "🌐 Application will be available at: http://localhost:8501"
echo ""
echo "⚠️  Note: Keep this terminal window open to keep the application running"
echo "   Press Ctrl+C to stop the application"
echo ""

# Change to the violentutf directory
cd "$streamlit_dir" || exit 1

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🐍 Activating Python virtual environment..."
    source .venv/bin/activate
fi

# Launch Streamlit
echo "🚀 Starting Streamlit server..."
streamlit run Home.py --server.port=8501 --server.address=0.0.0.0 --browser.gatherUsageStats=false
EOF
    
    # Make the script executable
    chmod +x "$launch_script"
    
    # Launch new Terminal window on macOS
    osascript <<EOF
tell application "Terminal"
    activate
    set newTab to do script "bash '$launch_script'"
    set custom title of newTab to "ViolentUTF Streamlit Server"
end tell
EOF
    
    # Clean up the temporary script after a short delay
    sleep 2
    rm -f "$launch_script"
    
    echo "✅ ViolentUTF Streamlit launched in new terminal window"
    echo "🌐 Access the web interface at: http://localhost:8501"
    echo ""
}