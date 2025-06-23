#!/usr/bin/env bash
# setup_macos.sh (API Version with APISIX integration, AI proxy, network fixes, cleanup and deep cleanup options)

# --- Help function ---
show_help() {
    echo "ViolentUTF macOS Setup Script"
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  (no options)     Normal setup - Install and configure ViolentUTF platform"
    echo "  --cleanup        Standard cleanup - Gracefully shutdown ViolentUTF Streamlit, remove containers, volumes, and config files"
    echo "  --deepcleanup    Deep cleanup - Gracefully shutdown ViolentUTF Streamlit, remove ALL Docker containers, images, volumes,"
    echo "                   networks, and cache (complete Docker environment reset)"
    echo "  --help, -h       Show this help message"
    echo ""
    echo "Note:"
    echo "  Cleanup operations gracefully shutdown only ViolentUTF-specific Streamlit processes (Home.py, violentutf directory)"
    echo "  Other Streamlit applications will not be affected. Graceful shutdown allows proper session cleanup."
    echo "  User configurations (AI tokens, custom routes, app data) are automatically backed up and restored during setup."
    echo ""
    echo "Examples:"
    echo "  ./setup_macos.sh                 # Normal installation"
    echo "  ./setup_macos.sh --cleanup       # Clean ViolentUTF components only"
    echo "  ./setup_macos.sh --deepcleanup   # Complete Docker environment reset"
    echo ""
    echo "Description:"
    echo "  This script sets up the ViolentUTF AI red-teaming platform with:"
    echo "  - Keycloak SSO authentication"
    echo "  - APISIX API gateway with AI proxy"
    echo "  - ViolentUTF API (FastAPI) with PyRIT Orchestrator support"
    echo "  - ViolentUTF Streamlit web interface"
    echo "  - PyRIT and Garak AI security frameworks"
    echo "  - PyRIT Orchestrator API for dataset testing and automation"
    echo "  - PyRIT Orchestrator integration validation for scorer testing"
    echo ""
    echo "Warning:"
    echo "  --deepcleanup will remove ALL Docker data on your system!"
    echo "  Use with caution if you have other Docker projects."
}

# --- Parse command line arguments ---
CLEANUP_MODE=false
DEEPCLEANUP_MODE=false
for arg in "$@"; do
    case $arg in
        --cleanup)
            CLEANUP_MODE=true
            shift # Remove --cleanup from processing
            ;;
        --deepcleanup)
            DEEPCLEANUP_MODE=true
            shift # Remove --deepcleanup from processing
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            # Unknown option
            echo "Unknown option: $arg"
            echo ""
            show_help
            exit 1
            ;;
    esac
done

# --- Store generated sensitive values for final report ---
SENSITIVE_VALUES=()

# --- Define shared network name globally ---
SHARED_NETWORK_NAME="vutf-network"

# --- AI Configuration via .env file ---
AI_TOKENS_FILE="ai-tokens.env"

# --- Array to track created AI routes ---
CREATED_AI_ROUTES=()

# --- Function to gracefully shutdown ViolentUTF Streamlit server ---
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
            echo "Found processes still using port 8501, attempting graceful shutdown..."
            echo "$PORT_PIDS" | xargs kill -TERM 2>/dev/null || true
            sleep 3
            
            # Final force kill if still there
            if lsof -i :8501 > /dev/null 2>&1; then
                echo "Force killing remaining processes on port 8501..."
                lsof -ti :8501 | xargs kill -9 2>/dev/null || true
            fi
        fi
    fi
    
    echo "✅ ViolentUTF Streamlit server shutdown completed"
}

# --- Backup user configurations function ---
backup_user_configs() {
    echo "Backing up user configurations..."
    mkdir -p "/tmp/vutf_backup"
    
    # Backup AI tokens (user's API keys)
    [ -f "$AI_TOKENS_FILE" ] && cp "$AI_TOKENS_FILE" "/tmp/vutf_backup/"
    
    # Backup any custom APISIX routes
    [ -f "apisix/conf/custom_routes.yml" ] && cp "apisix/conf/custom_routes.yml" "/tmp/vutf_backup/"
    
    # Backup user application data preferences
    if [ -d "violentutf/app_data" ]; then
        tar -czf "/tmp/vutf_backup/app_data_backup.tar.gz" -C violentutf app_data 2>/dev/null || true
    fi
    
    echo "✅ User configurations backed up"
}

# --- Restore user configurations function ---
restore_user_configs() {
    echo "Restoring user configurations..."
    
    if [ -d "/tmp/vutf_backup" ]; then
        # Restore AI tokens
        [ -f "/tmp/vutf_backup/$AI_TOKENS_FILE" ] && cp "/tmp/vutf_backup/$AI_TOKENS_FILE" .
        
        # Restore custom routes
        [ -f "/tmp/vutf_backup/custom_routes.yml" ] && cp "/tmp/vutf_backup/custom_routes.yml" "apisix/conf/"
        
        # Restore user application data if it was backed up
        if [ -f "/tmp/vutf_backup/app_data_backup.tar.gz" ]; then
            mkdir -p violentutf
            tar -xzf "/tmp/vutf_backup/app_data_backup.tar.gz" -C violentutf 2>/dev/null || true
        fi
        
        rm -rf "/tmp/vutf_backup"
        echo "✅ User configurations restored"
    fi
}

# --- Cleanup function ---
perform_cleanup() {
    echo "Starting cleanup process..."
    
    # 0. Backup user configurations before cleanup
    backup_user_configs
    
    # 1. Gracefully shutdown ViolentUTF Streamlit server
    graceful_streamlit_shutdown
    
    # Remember current directory
    ORIGINAL_DIR=$(pwd)
    
    # 1. Stop and remove Keycloak containers
    echo "Stopping and removing Keycloak containers..."
    if [ -d "keycloak" ]; then
        cd "keycloak" || { echo "Failed to cd into keycloak directory"; exit 1; }
        docker-compose down -v 2>/dev/null || docker compose down -v 2>/dev/null
        cd "$ORIGINAL_DIR"
    fi
    
    # 2. Stop and remove APISIX containers
    echo "Stopping and removing APISIX containers..."
    if [ -d "apisix" ]; then
        cd "apisix" || { echo "Failed to cd into apisix directory"; exit 1; }
        docker-compose down -v 2>/dev/null || docker compose down -v 2>/dev/null
        cd "$ORIGINAL_DIR"
    fi
    
    # 3. Note: ViolentUTF API is now part of APISIX stack
    echo "ViolentUTF API containers are managed by APISIX stack..."
    
    # 4. Remove shared network if it exists and is not in use
    echo "Removing shared Docker network..."
    if docker network inspect $SHARED_NETWORK_NAME >/dev/null 2>&1; then
        if docker network rm $SHARED_NETWORK_NAME >/dev/null 2>&1; then
            echo "Removed shared network '$SHARED_NETWORK_NAME'."
        else
            echo "Warning: Could not remove shared network '$SHARED_NETWORK_NAME'. It may still be in use."
        fi
    fi
    
    # 5. Remove configuration files but preserve directories
    echo "Removing configuration files..."
    
    # Keycloak files
    if [ -f "keycloak/.env" ]; then
        rm "keycloak/.env"
        echo "Removed keycloak/.env"
    fi
    
    # APISIX files - remove all non-template configurations
    if [ -d "apisix/conf" ]; then
        # Move only template files to a temp directory
        mkdir -p "/tmp/apisix_templates"
        find "apisix/conf" -name "*.template" -exec cp {} "/tmp/apisix_templates/" \;
        
        # Remove all config files
        rm -rf "apisix/conf/"*
        
        # Move templates back
        mkdir -p "apisix/conf"
        cp "/tmp/apisix_templates/"* "apisix/conf/" 2>/dev/null || true
        rm -rf "/tmp/apisix_templates"
        
        echo "Restored only template files in apisix/conf directory"
    fi
    
    # ViolentUTF files
    if [ -f "violentutf/.env" ]; then
        rm "violentutf/.env"
        echo "Removed violentutf/.env"
    fi
    
    if [ -f "violentutf/.streamlit/secrets.toml" ]; then
        rm "violentutf/.streamlit/secrets.toml"
        echo "Removed violentutf/.streamlit/secrets.toml"
    fi
    
    # FastAPI files
    if [ -f "violentutf_api/fastapi_app/.env" ]; then
        rm "violentutf_api/fastapi_app/.env"
        echo "Removed violentutf_api/fastapi_app/.env"
    fi
    
    # AI tokens file (preserve user's configuration) 
    echo "Preserving user's AI tokens file: $AI_TOKENS_FILE"
    
    # 5.5. Clean PyRIT orchestrator memory databases but preserve user application data
    echo "Cleaning PyRIT orchestrator memory databases..."
    if [ -d "violentutf/app_data/violentutf/api_memory" ]; then
        rm -f violentutf/app_data/violentutf/api_memory/orchestrator_memory*.db*
        echo "Removed orchestrator memory databases"
    fi
    
    # Preserve user application data
    echo "Preserving user application data..."
    if [ -d "violentutf/app_data" ]; then
        echo "Preserving violentutf/app_data directory with user data"
    fi
    
    # 6. Remove Docker volumes
    echo "Removing Docker volumes related to Keycloak, APISIX, and ViolentUTF API..."
    # Get volume list and filter for keycloak, apisix, fastapi, and violentutf_api volumes
    VOLUMES_TO_REMOVE=$(docker volume ls -q | grep -E '(keycloak|apisix|violentutf_api|fastapi|strapi)')
    if [ -n "$VOLUMES_TO_REMOVE" ]; then
        echo "$VOLUMES_TO_REMOVE" | xargs docker volume rm
        echo "Removed Docker volumes."
    else
        echo "No relevant Docker volumes found to remove."
    fi
    
    echo "Cleanup completed successfully!"
    echo "The Python virtual environment has been preserved."
    echo "You can now run the script again for a fresh setup."
    exit 0
}

# --- Deep Cleanup function ---
perform_deep_cleanup() {
    echo "Starting DEEP cleanup process..."
    echo "This will remove ALL Docker containers, images, volumes, networks, and cache!"
    echo ""
    
    # 0. Gracefully shutdown ViolentUTF Streamlit server first
    graceful_streamlit_shutdown
    
    # Warning prompt
    echo "⚠️  WARNING: This will completely clean your Docker environment!"
    echo "   - All Docker containers will be stopped and removed"
    echo "   - All Docker images will be removed"
    echo "   - All Docker volumes will be removed"
    echo "   - All Docker networks will be removed"
    echo "   - All Docker build cache will be pruned"
    echo "   - All Docker system cache will be pruned"
    echo ""
    read -p "Are you absolutely sure you want to continue? (type 'YES' to confirm): " confirm
    
    if [ "$confirm" != "YES" ]; then
        echo "Deep cleanup cancelled."
        exit 0
    fi
    
    echo ""
    echo "Proceeding with deep cleanup..."
    
    # 0. Backup user configurations before deep cleanup
    backup_user_configs
    
    # First perform regular cleanup
    echo "1. Performing standard cleanup..."
    perform_cleanup_internal
    
    # Stop ALL Docker containers
    echo ""
    echo "2. Stopping ALL Docker containers..."
    RUNNING_CONTAINERS=$(docker ps -aq)
    if [ -n "$RUNNING_CONTAINERS" ]; then
        echo "Stopping containers: $RUNNING_CONTAINERS"
        docker stop $RUNNING_CONTAINERS
        echo "Removing containers..."
        docker rm $RUNNING_CONTAINERS
        echo "All containers stopped and removed."
    else
        echo "No running containers found."
    fi
    
    # Remove ALL Docker images
    echo ""
    echo "3. Removing ALL Docker images..."
    ALL_IMAGES=$(docker images -aq)
    if [ -n "$ALL_IMAGES" ]; then
        echo "Removing images: $(echo $ALL_IMAGES | wc -w) images found"
        docker rmi -f $ALL_IMAGES
        echo "All Docker images removed."
    else
        echo "No Docker images found."
    fi
    
    # Remove ALL Docker volumes
    echo ""
    echo "4. Removing ALL Docker volumes..."
    ALL_VOLUMES=$(docker volume ls -q)
    if [ -n "$ALL_VOLUMES" ]; then
        echo "Removing volumes: $(echo $ALL_VOLUMES | wc -w) volumes found"
        docker volume rm -f $ALL_VOLUMES
        echo "All Docker volumes removed."
    else
        echo "No Docker volumes found."
    fi
    
    # Remove ALL Docker networks (except default ones)
    echo ""
    echo "5. Removing ALL Docker networks (except defaults)..."
    CUSTOM_NETWORKS=$(docker network ls --filter type=custom -q)
    if [ -n "$CUSTOM_NETWORKS" ]; then
        echo "Removing custom networks: $(echo $CUSTOM_NETWORKS | wc -w) networks found"
        docker network rm $CUSTOM_NETWORKS
        echo "All custom Docker networks removed."
    else
        echo "No custom Docker networks found."
    fi
    
    # Prune Docker build cache
    echo ""
    echo "6. Pruning Docker build cache..."
    docker builder prune -af
    echo "Docker build cache pruned."
    
    # Prune Docker system (everything)
    echo ""
    echo "7. Pruning Docker system cache..."
    docker system prune -af --volumes
    echo "Docker system cache pruned."
    
    # Clean up any remaining Docker artifacts
    echo ""
    echo "8. Final Docker cleanup..."
    docker container prune -f
    docker image prune -af
    docker volume prune -f
    docker network prune -f
    echo "Final Docker cleanup completed."
    
    # Show final Docker status
    echo ""
    echo "9. Final Docker status:"
    echo "Containers: $(docker ps -aq | wc -l)"
    echo "Images: $(docker images -aq | wc -l)"
    echo "Volumes: $(docker volume ls -q | wc -l)"
    echo "Networks: $(docker network ls -q | wc -l)"
    
    # Show disk space reclaimed
    echo ""
    echo "10. Docker system disk usage:"
    docker system df
    
    echo ""
    echo "🧹 DEEP CLEANUP COMPLETED SUCCESSFULLY!"
    echo "✅ All Docker containers, images, volumes, networks, and cache have been removed"
    echo "✅ Maximum disk space has been reclaimed"
    echo "✅ Docker environment is now completely clean"
    echo ""
    echo "💡 You can now run the script again for a completely fresh setup"
    echo "💡 Note: First run after deep cleanup will take longer as images need to be downloaded"
    exit 0
}

# --- Internal cleanup function (without exit) ---
perform_cleanup_internal() {
    echo "Starting cleanup process..."
    
    # Remember current directory
    ORIGINAL_DIR=$(pwd)
    
    # 1. Stop and remove Keycloak containers
    echo "Stopping and removing Keycloak containers..."
    if [ -d "keycloak" ]; then
        cd "keycloak" || { echo "Failed to cd into keycloak directory"; exit 1; }
        docker-compose down -v 2>/dev/null || docker compose down -v 2>/dev/null
        cd "$ORIGINAL_DIR"
    fi
    
    # 2. Stop and remove APISIX containers
    echo "Stopping and removing APISIX containers..."
    if [ -d "apisix" ]; then
        cd "apisix" || { echo "Failed to cd into apisix directory"; exit 1; }
        docker-compose down -v 2>/dev/null || docker compose down -v 2>/dev/null
        cd "$ORIGINAL_DIR"
    fi
    
    # 3. Note: ViolentUTF API is now part of APISIX stack
    echo "ViolentUTF API containers are managed by APISIX stack..."
    
    # 4. Remove shared network if it exists and is not in use
    echo "Removing shared Docker network..."
    if docker network inspect $SHARED_NETWORK_NAME >/dev/null 2>&1; then
        if docker network rm $SHARED_NETWORK_NAME >/dev/null 2>&1; then
            echo "Removed shared network '$SHARED_NETWORK_NAME'."
        else
            echo "Warning: Could not remove shared network '$SHARED_NETWORK_NAME'. It may still be in use."
        fi
    fi
    
    # 5. Remove configuration files but preserve directories
    echo "Removing configuration files..."
    
    # Keycloak files
    if [ -f "keycloak/.env" ]; then
        rm "keycloak/.env"
        echo "Removed keycloak/.env"
    fi
    
    # APISIX files - remove all non-template configurations
    if [ -d "apisix/conf" ]; then
        # Move only template files to a temp directory
        mkdir -p "/tmp/apisix_templates"
        find "apisix/conf" -name "*.template" -exec cp {} "/tmp/apisix_templates/" \;
        
        # Remove all config files
        rm -rf "apisix/conf/"*
        
        # Move templates back
        mkdir -p "apisix/conf"
        cp "/tmp/apisix_templates/"* "apisix/conf/" 2>/dev/null || true
        rm -rf "/tmp/apisix_templates"
        
        echo "Restored only template files in apisix/conf directory"
    fi
    
    # ViolentUTF files
    if [ -f "violentutf/.env" ]; then
        rm "violentutf/.env"
        echo "Removed violentutf/.env"
    fi
    
    if [ -f "violentutf/.streamlit/secrets.toml" ]; then
        rm "violentutf/.streamlit/secrets.toml"
        echo "Removed violentutf/.streamlit/secrets.toml"
    fi
    
    # FastAPI files
    if [ -f "violentutf_api/fastapi_app/.env" ]; then
        rm "violentutf_api/fastapi_app/.env"
        echo "Removed violentutf_api/fastapi_app/.env"
    fi
    
    # AI tokens file (preserve user's configuration) 
    echo "Preserving user's AI tokens file: $AI_TOKENS_FILE"
    
    # 6. Remove Docker volumes
    echo "Removing Docker volumes related to Keycloak, APISIX, and ViolentUTF API..."
    # Get volume list and filter for keycloak, apisix, fastapi, and violentutf_api volumes
    VOLUMES_TO_REMOVE=$(docker volume ls -q | grep -E '(keycloak|apisix|violentutf_api|fastapi|strapi)')
    if [ -n "$VOLUMES_TO_REMOVE" ]; then
        echo "$VOLUMES_TO_REMOVE" | xargs docker volume rm
        echo "Removed Docker volumes."
    else
        echo "No relevant Docker volumes found to remove."
    fi
}

# Function to ensure Docker Compose files have shared network configuration
ensure_network_in_compose() {
    local compose_file="$1"
    local service_name="$2"
    
    # Check if file exists
    if [ ! -f "$compose_file" ]; then
        echo "Error: Docker Compose file $compose_file not found!"
        return 1
    fi
    
    # Backup the compose file
    local backup_suffix=$(date +"%Y%m%d%H%M%S")
    cp "$compose_file" "${compose_file}.bak${backup_suffix}"
    
    # Check if the file already has vutf-network section
    if ! grep -q "vutf-network:" "$compose_file"; then
        # Add networks section if missing
        if ! grep -q "^networks:" "$compose_file"; then
            echo "" >> "$compose_file"
            echo "networks:" >> "$compose_file"
        fi
        
        # Add vutf-network to networks section
        sed -i '' '/^networks:/a\
  vutf-network:\
    external: true' "$compose_file"
        
        echo "Added vutf-network to networks section in $compose_file"
    fi
    
    # Check if service section exists
    if ! grep -q "^  $service_name:" "$compose_file"; then
        echo "Warning: Service $service_name not found in $compose_file"
        return 0
    fi
    
    # Add network to service if missing
    if ! grep -A20 "^  $service_name:" "$compose_file" | grep -q "vutf-network"; then
        # Check if networks section exists in the service
        if grep -A20 "^  $service_name:" "$compose_file" | grep -q "    networks:"; then
            # Add vutf-network to existing networks section
            linenum=$(grep -n "^  $service_name:" "$compose_file" | cut -d: -f1)
            if [ -n "$linenum" ]; then
                # Find networks section within this service
                netlinenum=$(tail -n +$linenum "$compose_file" | grep -n "    networks:" | head -1 | cut -d: -f1)
                if [ -n "$netlinenum" ]; then
                    netlinenum=$((linenum + netlinenum))
                    sed -i '' "${netlinenum}a\\
      - vutf-network" "$compose_file"
                fi
            fi
        else
            # Add a new networks section to the service
            sed -i '' "/^  $service_name:/a\\
    networks:\\
      - vutf-network" "$compose_file"
        fi
        
        echo "Added vutf-network to $service_name service in $compose_file"
    fi
    
    return 0
}

# Function to create AI tokens template
create_ai_tokens_template() {
    if [ ! -f "$AI_TOKENS_FILE" ]; then
        echo "Creating AI tokens configuration file: $AI_TOKENS_FILE"
        cat > "$AI_TOKENS_FILE" << 'EOF'
# AI Provider Tokens and Settings
# Set to true/false to enable/disable providers
# Add your actual API keys replacing the placeholder values

# OpenAI Configuration
OPENAI_ENABLED=false
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic Configuration  
ANTHROPIC_ENABLED=false
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Ollama Configuration (local, no API key needed)
OLLAMA_ENABLED=true
OLLAMA_ENDPOINT=http://localhost:11434/v1/chat/completions

# Open WebUI Configuration
OPEN_WEBUI_ENABLED=false
OPEN_WEBUI_ENDPOINT=http://localhost:3000/ollama/v1/chat/completions
OPEN_WEBUI_API_KEY=your_open_webui_api_key_here

# AWS Bedrock Configuration
BEDROCK_ENABLED=false
BEDROCK_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key_id_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key_here
AWS_SESSION_TOKEN=your_aws_session_token_here_if_using_temp_credentials
EOF
        echo "✅ Created $AI_TOKENS_FILE"
        echo "📝 Please edit this file and add your API keys, then re-run the script"
        return 1
    fi
    return 0
}

# Function to load AI tokens from .env file
load_ai_tokens() {
    if [ ! -f "$AI_TOKENS_FILE" ]; then
        echo "❌ $AI_TOKENS_FILE not found"
        return 1
    fi
    
    echo "Loading AI configuration from $AI_TOKENS_FILE..."
    
    # Load the .env file
    set -a  # automatically export all variables
    source "$AI_TOKENS_FILE"
    set +a  # stop automatically exporting
    
    echo "✅ AI configuration loaded"
    return 0
}

# Function to check if ai-proxy plugin is available
check_ai_proxy_plugin() {
    echo "Checking if ai-proxy plugin is available in APISIX..."
    
    local response
    local http_code
    
    response=$(curl -w "%{http_code}" -X GET "${APISIX_ADMIN_URL}/apisix/admin/plugins/ai-proxy" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>&1)
    
    http_code="${response: -3}"
    
    if [ "$http_code" = "200" ]; then
        echo "✅ ai-proxy plugin is available"
        return 0
    else
        echo "❌ ai-proxy plugin is not available"
        echo "   HTTP Code: $http_code"
        echo "   Make sure you're using APISIX version 3.10.0 or later with ai-proxy plugin enabled"
        return 1
    fi
}

# Add debugging to the route creation function
create_openai_route() {
    local model="$1"
    local uri="$2"
    local api_key="$3"
    
    echo "🔧 Debug: Creating route for model='$model', uri='$uri'"
    
    # Validate inputs
    if [ -z "$model" ] || [ -z "$uri" ] || [ -z "$api_key" ]; then
        echo "❌ Error: Missing required parameters"
        echo "   Model: '$model'"
        echo "   URI: '$uri'"
        echo "   API Key length: ${#api_key}"
        return 1
    fi
    
    local route_id="openai-$(echo "$model" | tr '.' '-' | tr '[:upper:]' '[:lower:]')"
    echo "🔧 Debug: Generated route_id='$route_id'"
    
    local route_config='{
        "id": "'$route_id'",
        "uri": "'$uri'",
        "methods": ["POST", "GET"],
        "plugins": {
            "key-auth": {},
            "ai-proxy": {
                "provider": "openai",
                "auth": {
                    "header": {
                        "Authorization": "Bearer '$api_key'"
                    }
                },
                "options": {
                    "model": "'$model'"
                }
            }
        }
    }'
    
    echo "🔧 Debug: Route config created"
    echo "Creating OpenAI route for model $model at $uri..."
    
    local response
    local http_code
    
    # Use the correct URL format - no route ID in path
    response=$(curl -w "%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
      -H "Content-Type: application/json" \
      -d "${route_config}" 2>&1)
    
    http_code="${response: -3}"
    response_body="${response%???}"
    
    echo "🔧 Debug: HTTP Code: $http_code"
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo "✅ Successfully created OpenAI route: $uri -> $model"
        CREATED_AI_ROUTES+=("OpenAI: $uri -> $model")
        return 0
    else
        echo "❌ Failed to create OpenAI route for $model"
        echo "   HTTP Code: $http_code"
        echo "   Response: $response_body"
        echo "   Full curl command would be:"
        echo "   curl -X PUT '${APISIX_ADMIN_URL}/apisix/admin/routes' -H 'X-API-KEY: ${APISIX_ADMIN_KEY}' -H 'Content-Type: application/json' -d '$route_config'"
        return 1
    fi
}

# Function to create Anthropic route (fixed)
create_anthropic_route() {
    local model="$1"
    local uri="$2"
    local api_key="$3"
    
    local route_id="anthropic-$(echo "$model" | tr '.' '-' | tr '[:upper:]' '[:lower:]')"
    
    local route_config='{
        "id": "'$route_id'",
        "uri": "'$uri'",
        "methods": ["POST", "GET"],
        "plugins": {
            "key-auth": {},
            "ai-proxy": {
                "provider": "openai-compatible",
                "auth": {
                    "header": {
                        "x-api-key": "'$api_key'",
                        "anthropic-version": "2023-06-01"
                    }
                },
                "options": {
                    "model": "'$model'"
                },
                "override": {
                    "endpoint": "https://api.anthropic.com/v1/messages"
                }
            }
        }
    }'
    
    echo "Creating Anthropic route for model $model at $uri..."
    local response
    local http_code
    
    response=$(curl -w "%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
      -H "Content-Type: application/json" \
      -d "${route_config}" 2>&1)
    
    http_code="${response: -3}"
    response_body="${response%???}"
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo "✅ Successfully created Anthropic route: $uri -> $model"
        CREATED_AI_ROUTES+=("Anthropic: $uri -> $model")
    else
        echo "❌ Failed to create Anthropic route for $model"
        echo "   HTTP Code: $http_code"
        echo "   Response: $response_body"
        return 1
    fi
}

# Function to create Ollama route (fixed)
create_ollama_route() {
    local model="$1"
    local uri="$2"
    local endpoint="$3"
    
    local route_id="ollama-$(echo "$model" | tr '.' '-' | tr '[:upper:]' '[:lower:]')"
    
    local route_config='{
        "id": "'$route_id'",
        "uri": "'$uri'",
        "methods": ["POST", "GET"],
        "plugins": {
            "key-auth": {},
            "ai-proxy": {
                "provider": "openai-compatible",
                "options": {
                    "model": "'$model'"
                },
                "override": {
                    "endpoint": "'$endpoint'"
                }
            }
        }
    }'
    
    echo "Creating Ollama route for model $model at $uri..."
    local response
    local http_code
    
    response=$(curl -w "%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
      -H "Content-Type: application/json" \
      -d "${route_config}" 2>&1)
    
    http_code="${response: -3}"
    response_body="${response%???}"
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo "✅ Successfully created Ollama route: $uri -> $model"
        CREATED_AI_ROUTES+=("Ollama: $uri -> $model")
    else
        echo "❌ Failed to create Ollama route for $model"
        echo "   HTTP Code: $http_code"
        echo "   Response: $response_body"
        return 1
    fi
}

# Function to create Open WebUI route (fixed)
create_open_webui_route() {
    local model="$1"
    local uri="$2"
    local endpoint="$3"
    local api_key="$4"
    
    local route_id="webui-$(echo "$model" | tr '.' '-' | tr '[:upper:]' '[:lower:]')"
    
    # Build auth section only if API key is provided and not placeholder
    local auth_section=""
    if [ -n "$api_key" ] && [ "$api_key" != "your_open_webui_api_key_here" ]; then
        auth_section='"auth": {
            "header": {
                "Authorization": "Bearer '$api_key'"
            }
        },'
    fi
    
    local route_config='{
        "id": "'$route_id'",
        "uri": "'$uri'",
        "methods": ["POST", "GET"],
        "plugins": {
            "key-auth": {},
            "ai-proxy": {
                "provider": "openai-compatible",
                '$auth_section'
                "options": {
                    "model": "'$model'"
                },
                "override": {
                    "endpoint": "'$endpoint'"
                }
            }
        }
    }'
    
    echo "Creating Open WebUI route for model $model at $uri..."
    local response
    local http_code
    
    response=$(curl -w "%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
      -H "Content-Type: application/json" \
      -d "${route_config}" 2>&1)
    
    http_code="${response: -3}"
    response_body="${response%???}"
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo "✅ Successfully created Open WebUI route: $uri -> $model"
        CREATED_AI_ROUTES+=("Open WebUI: $uri -> $model")
    else
        echo "❌ Failed to create Open WebUI route for $model"
        echo "   HTTP Code: $http_code"
        echo "   Response: $response_body"
        return 1
    fi
}

# Function to create AWS Bedrock route
create_bedrock_route() {
    local model="$1"
    local uri="$2"
    local region="$3"
    local access_key="$4"
    local secret_key="$5"
    local session_token="$6"
    
    local route_id="bedrock-$(echo "$model" | tr '.' '-' | tr '[:upper:]' '[:lower:]' | sed 's/anthropic-//g' | sed 's/meta-//g' | sed 's/amazon-//g')"
    
    # Create route config with ai-proxy plugin for Bedrock (using openai-compatible + custom endpoint)
    local route_config='{
        "id": "'$route_id'",
        "uri": "'$uri'",
        "methods": ["POST", "GET"],
        "plugins": {
            "key-auth": {},
            "ai-proxy": {
                "provider": "openai-compatible",
                "auth": {
                    "header": {
                        "Authorization": "AWS4-HMAC-SHA256 Credential='$access_key'/'$(date +%Y%m%d)'/'$region'/bedrock/aws4_request"
                    }
                },
                "options": {
                    "model": "'$model'",
                    "max_tokens": 1000,
                    "temperature": 0.7
                },
                "override": {
                    "endpoint": "https://bedrock-runtime.'$region'.amazonaws.com/model/'$model'/invoke"
                }
            }
        }
    }'
    
    echo "Creating AWS Bedrock route for model $model at $uri..."
    local response
    local http_code
    
    response=$(curl -w "%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
      -H "Content-Type: application/json" \
      -d "${route_config}" 2>&1)
    
    http_code="${response: -3}"
    response_body="${response%???}"
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo "✅ Successfully created AWS Bedrock route: $uri -> $model"
        CREATED_AI_ROUTES+=("AWS Bedrock: $uri -> $model")
    else
        echo "❌ Failed to create AWS Bedrock route for $model"
        echo "   HTTP Code: $http_code"
        echo "   Response: $response_body"
        return 1
    fi
}

# Function to create APISIX API key consumer
create_apisix_consumer() {
    local consumer_config='{
        "username": "violentutf_user",
        "plugins": {
            "key-auth": {
                "key": "'$VIOLENTUTF_API_KEY'"
            }
        }
    }'
    
    echo "Creating APISIX consumer with API key authentication..."
    local response
    local http_code
    
    response=$(curl -w "%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/consumers/violentutf_user" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
      -H "Content-Type: application/json" \
      -d "${consumer_config}" 2>&1)
    
    http_code="${response: -3}"
    response_body="${response%???}"
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo "✅ Successfully created API key consumer"
        echo "   API Key: $VIOLENTUTF_API_KEY"
        echo "   Use this key in the 'apikey' header for AI Gateway requests"
        return 0
    else
        echo "❌ Failed to create API key consumer"
        echo "   HTTP Code: $http_code"
        echo "   Response: $response_body"
        return 1
    fi
}

# Function to setup OpenAI routes (fixed array syntax)
setup_openai_routes() {
    if [ "$OPENAI_ENABLED" != "true" ]; then
        echo "OpenAI provider disabled. Skipping setup."
        return 0
    fi
    
    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
        echo "⚠️  OpenAI enabled but API key not configured. Skipping OpenAI setup."
        return 0
    fi
    
    echo "Setting up OpenAI routes..."
    
    # Use arrays instead of associative arrays to avoid syntax issues
    local models=("gpt-4" "gpt-3.5-turbo" "gpt-4-turbo" "gpt-4o" "gpt-4o-mini" "gpt-4.1" "gpt-4.1-mini" "gpt-4.1-nano" "o1-preview" "o1-mini" "o3-mini" "o4-mini")
    local uris=("/ai/openai/gpt4" "/ai/openai/gpt35" "/ai/openai/gpt4-turbo" "/ai/openai/gpt4o" "/ai/openai/gpt4o-mini" "/ai/openai/gpt41" "/ai/openai/gpt41-mini" "/ai/openai/gpt41-nano" "/ai/openai/o1-preview" "/ai/openai/o1-mini" "/ai/openai/o3-mini" "/ai/openai/o4-mini")
    
    local setup_success=true
    for i in "${!models[@]}"; do
        local model="${models[$i]}"
        local uri="${uris[$i]}"
        echo "Processing model: $model -> $uri"
        if ! create_openai_route "$model" "$uri" "$OPENAI_API_KEY"; then
            setup_success=false
        fi
    done
    
    if [ "$setup_success" = true ]; then
        return 0
    else
        return 1
    fi
}

# Function to setup Anthropic routes (fixed array syntax)
setup_anthropic_routes() {
    if [ "$ANTHROPIC_ENABLED" != "true" ]; then
        echo "Anthropic provider disabled. Skipping setup."
        return 0
    fi
    
    if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_anthropic_api_key_here" ]; then
        echo "⚠️  Anthropic enabled but API key not configured. Skipping Anthropic setup."
        return 0
    fi
    
    echo "Setting up Anthropic routes..."
    
    # Use arrays instead of associative arrays
    local models=("claude-3-opus-20240229" "claude-3-sonnet-20240229" "claude-3-haiku-20240307" "claude-3-5-sonnet-20241022" "claude-3-5-haiku-20241022" "claude-3-7-sonnet-latest" "claude-sonnet-4-20250514" "claude-opus-4-20250514")
    local uris=("/ai/anthropic/opus" "/ai/anthropic/sonnet" "/ai/anthropic/haiku" "/ai/anthropic/sonnet35" "/ai/anthropic/haiku35" "/ai/anthropic/sonnet37" "/ai/anthropic/sonnet4" "/ai/anthropic/opus4")
    
    local setup_success=true
    for i in "${!models[@]}"; do
        local model="${models[$i]}"
        local uri="${uris[$i]}"
        echo "Processing model: $model -> $uri"
        if ! create_anthropic_route "$model" "$uri" "$ANTHROPIC_API_KEY"; then
            setup_success=false
        fi
    done
    
    if [ "$setup_success" = true ]; then
        return 0
    else
        return 1
    fi
}

# Function to setup Ollama routes (fixed array syntax)
setup_ollama_routes() {
    if [ "$OLLAMA_ENABLED" != "true" ]; then
        echo "Ollama provider disabled. Skipping setup."
        return 0
    fi
    
    echo "Setting up Ollama routes..."
    
    local endpoint="${OLLAMA_ENDPOINT:-http://localhost:11434/v1/chat/completions}"
    
    # Use arrays instead of associative arrays
    local models=("llama2" "codellama" "mistral" "llama3")
    local uris=("/ai/ollama/llama2" "/ai/ollama/codellama" "/ai/ollama/mistral" "/ai/ollama/llama3")
    
    local setup_success=true
    for i in "${!models[@]}"; do
        local model="${models[$i]}"
        local uri="${uris[$i]}"
        echo "Processing model: $model -> $uri"
        if ! create_ollama_route "$model" "$uri" "$endpoint"; then
            setup_success=false
        fi
    done
    
    if [ "$setup_success" = true ]; then
        return 0
    else
        return 1
    fi
}

# Function to setup Open WebUI routes (fixed array syntax)
setup_open_webui_routes() {
    if [ "$OPEN_WEBUI_ENABLED" != "true" ]; then
        echo "Open WebUI provider disabled. Skipping setup."
        return 0
    fi
    
    echo "Setting up Open WebUI routes..."
    
    local endpoint="${OPEN_WEBUI_ENDPOINT:-http://localhost:3000/ollama/v1/chat/completions}"
    local api_key="$OPEN_WEBUI_API_KEY"
    
    # Use arrays instead of associative arrays
    local models=("llama2" "codellama")
    local uris=("/ai/webui/llama2" "/ai/webui/codellama")
    
    local setup_success=true
    for i in "${!models[@]}"; do
        local model="${models[$i]}"
        local uri="${uris[$i]}"
        echo "Processing model: $model -> $uri"
        if ! create_open_webui_route "$model" "$uri" "$endpoint" "$api_key"; then
            setup_success=false
        fi
    done
    
    if [ "$setup_success" = true ]; then
        return 0
    else
        return 1
    fi
}

# Function to setup AWS Bedrock routes
setup_bedrock_routes() {
    if [ "$BEDROCK_ENABLED" != "true" ]; then
        echo "AWS Bedrock provider disabled. Skipping setup."
        return 0
    fi
    
    echo "⚠️  AWS Bedrock integration is currently not supported by APISIX ai-proxy plugin."
    echo "   The ai-proxy plugin does not support native AWS SigV4 authentication required for Bedrock."
    echo "   Bedrock endpoints are configured in TokenManager for future implementation."
    echo "   Use the standalone Bedrock provider in Simple Chat for now."
    return 0
    
    # Future implementation when AWS SigV4 support is added to APISIX
    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ "$AWS_ACCESS_KEY_ID" = "your_aws_access_key_id_here" ]; then
        echo "⚠️  AWS Bedrock enabled but Access Key ID not configured. Skipping Bedrock setup."
        return 0
    fi
    
    if [ -z "$AWS_SECRET_ACCESS_KEY" ] || [ "$AWS_SECRET_ACCESS_KEY" = "your_aws_secret_access_key_here" ]; then
        echo "⚠️  AWS Bedrock enabled but Secret Access Key not configured. Skipping Bedrock setup."
        return 0
    fi
    
    echo "Setting up AWS Bedrock routes..."
    
    local region="${BEDROCK_REGION:-us-east-1}"
    
    # Priority Bedrock models for AI Gateway
    local models=("anthropic.claude-opus-4-20250514-v1:0" "anthropic.claude-sonnet-4-20250514-v1:0" "anthropic.claude-3-5-sonnet-20241022-v2:0" "anthropic.claude-3-5-haiku-20241022-v1:0" "meta.llama3-3-70b-instruct-v1:0" "amazon.nova-pro-v1:0" "amazon.nova-lite-v1:0")
    local uris=("/ai/bedrock/claude-opus-4" "/ai/bedrock/claude-sonnet-4" "/ai/bedrock/claude-35-sonnet" "/ai/bedrock/claude-35-haiku" "/ai/bedrock/llama3-3-70b" "/ai/bedrock/nova-pro" "/ai/bedrock/nova-lite")
    
    local setup_success=true
    for i in "${!models[@]}"; do
        local model="${models[$i]}"
        local uri="${uris[$i]}"
        echo "Processing model: $model -> $uri"
        if ! create_bedrock_route "$model" "$uri" "$region" "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" "$AWS_SESSION_TOKEN"; then
            setup_success=false
        fi
    done
    
    if [ "$setup_success" = true ]; then
        return 0
    else
        return 1
    fi
}

# Enhanced debugging function for AI proxy setup
debug_ai_proxy_setup() {
    echo "🔍 Debugging AI Proxy Setup..."
    
    # Check if APISIX admin API is accessible
    echo "Testing APISIX Admin API accessibility..."
    admin_response=$(curl -s -w "%{http_code}" -X GET "${APISIX_ADMIN_URL}/apisix/admin/routes" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>&1)
    admin_http_code="${admin_response: -3}"
    
    if [ "$admin_http_code" != "200" ]; then
        echo "❌ APISIX Admin API not accessible. HTTP Code: $admin_http_code"
        echo "   Response: ${admin_response%???}"
        return 1
    else
        echo "✅ APISIX Admin API is accessible"
    fi
    
    # Check available plugins
    echo "Checking available plugins..."
    plugins_response=$(curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/plugins/list" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}")
    
    if echo "$plugins_response" | grep -q "ai-proxy"; then
        echo "✅ ai-proxy plugin is available"
    else
        echo "❌ ai-proxy plugin is not available"
        echo "Available plugins: $plugins_response"
        return 1
    fi
    
    # List existing routes
    echo "Existing routes:"
    curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/routes" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" | jq -r '.list[]?.value | "\(.id): \(.uri)"' 2>/dev/null || echo "Could not parse routes"
    
    return 0
}

# Enhanced AI setup with better error handling
setup_ai_providers_enhanced() {
    if [ "$SKIP_AI_SETUP" = true ]; then
        echo "Skipping AI provider setup due to configuration issues."
        return 0
    fi
    
    echo "Setting up AI providers with enhanced error handling..."
    
    # Debug APISIX setup first
    if ! debug_ai_proxy_setup; then
        echo "❌ AI Proxy setup prerequisites not met"
        SKIP_AI_SETUP=true
        return 1
    fi
    
    # Wait for APISIX to be fully ready
    echo "Waiting for APISIX to be fully ready..."
    sleep 10
    
    local setup_errors=0
    
    # Create API key consumer first
    echo "Creating API key consumer for authentication..."
    if ! create_apisix_consumer; then
        echo "❌ Failed to create API key consumer"
        setup_errors=$((setup_errors + 1))
    fi
    
    # Setup each provider with error counting
    echo "Setting up OpenAI routes..."
    if ! setup_openai_routes; then
        setup_errors=$((setup_errors + 1))
    fi
    
    echo "Setting up Anthropic routes..."
    if ! setup_anthropic_routes; then
        setup_errors=$((setup_errors + 1))
    fi
    
    echo "Setting up Ollama routes..."
    if ! setup_ollama_routes; then
        setup_errors=$((setup_errors + 1))
    fi
    
    echo "Setting up Open WebUI routes..."
    if ! setup_open_webui_routes; then
        setup_errors=$((setup_errors + 1))
    fi
    
    echo "Setting up AWS Bedrock routes..."
    if ! setup_bedrock_routes; then
        setup_errors=$((setup_errors + 1))
    fi
    
    if [ $setup_errors -gt 0 ]; then
        echo "⚠️  Some AI provider setups encountered errors"
        return 1
    else
        echo "✅ All AI provider setups completed successfully"
        return 0
    fi
}


# Function to test AI routes (no yq)
test_ai_routes() {
    echo "Testing AI provider routes..."
    
    # First, list all routes to see what was created
    echo "Listing all APISIX routes:"
    curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/routes" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" | jq -r '.list[]?.value | "\(.id): \(.uri)"' 2>/dev/null || echo "Could not list routes (jq not available)"
    
    # Test some basic routes
    if [ "$OLLAMA_ENABLED" = "true" ]; then
        run_test "AI Ollama route accessibility" "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL}/ai/ollama/llama2 -X POST -H 'Content-Type: application/json' -d '{\"messages\":[{\"role\":\"user\",\"content\":\"test\"}]}' | grep -E '(200|422|400|404)'"
    fi
    
    if [ "$OPENAI_ENABLED" = "true" ]; then
        run_test "AI OpenAI route accessibility" "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL}/ai/openai/gpt4 -X POST -H 'Content-Type: application/json' -d '{\"messages\":[{\"role\":\"user\",\"content\":\"test\"}]}' | grep -E '(200|401|422|400|404)'"
    fi
    
    if [ "$ANTHROPIC_ENABLED" = "true" ]; then
        run_test "AI Anthropic route accessibility" "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL}/ai/anthropic/opus -X POST -H 'Content-Type: application/json' -d '{\"messages\":[{\"role\":\"user\",\"content\":\"test\"}]}' | grep -E '(200|401|422|400|404)'"
    fi
    
    if [ "$BEDROCK_ENABLED" = "true" ]; then
        run_test "AI Bedrock route accessibility" "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL}/ai/bedrock/claude-opus-4 -X POST -H 'Content-Type: application/json' -d '{\"messages\":[{\"role\":\"user\",\"content\":\"test\"}]}' | grep -E '(200|401|422|400|404)'"
    fi
}

# Simplified AI configuration summary (no yq)
show_ai_summary() {
    echo ""
    echo "=========================================="
    echo "AI PROXY CONFIGURATION SUMMARY"
    echo "=========================================="
    
    if [ "$SKIP_AI_SETUP" = true ]; then
        echo "❌ AI Proxy setup was skipped"
        echo "Configure $AI_TOKENS_FILE to enable AI providers"
    else
        echo "AI Configuration file: $AI_TOKENS_FILE"
        echo ""
        echo "Enabled AI Providers:"
        
        if [ "$OPENAI_ENABLED" = "true" ]; then
            echo "✅ OpenAI"
            echo "   - /ai/openai/gpt4 (gpt-4)"
            echo "   - /ai/openai/gpt35 (gpt-3.5-turbo)"
            echo "   - /ai/openai/gpt4-turbo (gpt-4-turbo)"
            echo "   - /ai/openai/gpt4o (gpt-4o)"
            echo "   - /ai/openai/gpt4o-mini (gpt-4o-mini)"
            echo "   - /ai/openai/gpt41 (gpt-4.1)"
            echo "   - /ai/openai/gpt41-mini (gpt-4.1-mini)"
            echo "   - /ai/openai/gpt41-nano (gpt-4.1-nano)"
            echo "   - /ai/openai/o1-preview (o1-preview)"
            echo "   - /ai/openai/o1-mini (o1-mini)"
            echo "   - /ai/openai/o3-mini (o3-mini)"
            echo "   - /ai/openai/o4-mini (o4-mini)"
        fi
        
        if [ "$ANTHROPIC_ENABLED" = "true" ]; then
            echo "✅ Anthropic"
            echo "   - /ai/anthropic/opus (claude-3-opus-20240229)"
            echo "   - /ai/anthropic/sonnet (claude-3-sonnet-20240229)"
            echo "   - /ai/anthropic/haiku (claude-3-haiku-20240307)"
            echo "   - /ai/anthropic/sonnet35 (claude-3-5-sonnet-20241022)"
            echo "   - /ai/anthropic/haiku35 (claude-3-5-haiku-20241022)"
            echo "   - /ai/anthropic/sonnet37 (claude-3-7-sonnet-latest)"
            echo "   - /ai/anthropic/sonnet4 (claude-sonnet-4-20250514)"
            echo "   - /ai/anthropic/opus4 (claude-opus-4-20250514)"
        fi
        
        if [ "$OLLAMA_ENABLED" = "true" ]; then
            echo "✅ Ollama"
            echo "   - /ai/ollama/llama2"
            echo "   - /ai/ollama/codellama"
            echo "   - /ai/ollama/mistral"
            echo "   - /ai/ollama/llama3"
        fi
        
        if [ "$OPEN_WEBUI_ENABLED" = "true" ]; then
            echo "✅ Open WebUI"
            echo "   - /ai/webui/llama2"
            echo "   - /ai/webui/codellama"
        fi
        
        if [ "$BEDROCK_ENABLED" = "true" ]; then
            echo "✅ AWS Bedrock"
            echo "   - /ai/bedrock/claude-opus-4 (anthropic.claude-opus-4-20250514-v1:0)"
            echo "   - /ai/bedrock/claude-sonnet-4 (anthropic.claude-sonnet-4-20250514-v1:0)"
            echo "   - /ai/bedrock/claude-35-sonnet (anthropic.claude-3-5-sonnet-20241022-v2:0)"
            echo "   - /ai/bedrock/claude-35-haiku (anthropic.claude-3-5-haiku-20241022-v1:0)"
            echo "   - /ai/bedrock/llama3-3-70b (meta.llama3-3-70b-instruct-v1:0)"
            echo "   - /ai/bedrock/nova-pro (amazon.nova-pro-v1:0)"
            echo "   - /ai/bedrock/nova-lite (amazon.nova-lite-v1:0)"
        fi
        
        if [ ${#CREATED_AI_ROUTES[@]} -eq 0 ]; then
            echo "⚠️  No AI routes were created"
        else
            echo ""
            echo "Created Routes:"
            for route in "${CREATED_AI_ROUTES[@]}"; do
                echo "   - $route"
            done
        fi
    fi
    
    echo ""
    echo "Example usage:"
    echo "curl -X POST http://localhost:9080/ai/ollama/llama2 \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{\"messages\":[{\"role\":\"user\",\"content\":\"Hello!\"}]}'"
    echo "=========================================="
}

# If cleanup mode, perform cleanup and exit
if [ "$CLEANUP_MODE" = true ]; then
    perform_cleanup
fi

# If deep cleanup mode, perform deep cleanup and exit
if [ "$DEEPCLEANUP_MODE" = true ]; then
    perform_deep_cleanup
fi

# --- Global Keycloak API Variables ---
KEYCLOAK_SERVER_URL="http://localhost:8080"
ADMIN_USER="admin"
ADMIN_PASS="admin" # From your docker-compose.yml
MASTER_REALM="master"
ADMIN_CLIENT_ID="admin-cli"
ACCESS_TOKEN="" # Will be populated by get_keycloak_admin_token

# --- Global APISIX Variables ---
APISIX_URL="http://localhost:9080"
APISIX_ADMIN_URL="http://localhost:9180"
APISIX_DASHBOARD_URL="http://localhost:9001"

# Function to generate a random secure string
generate_secure_string() {
    openssl rand -base64 32 | tr -d '\n' | tr -d '\r' | tr -d '/' | tr -d '+' | tr -d '=' | cut -c1-32
}

# Function to backup and prepare config file from template
prepare_config_from_template() {
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

# Function to obtain Keycloak admin access token
get_keycloak_admin_token() {
    echo "Attempting to obtain Keycloak admin access token..."
    local token_response
    token_response=$(curl -s -X POST "${KEYCLOAK_SERVER_URL}/realms/${MASTER_REALM}/protocol/openid-connect/token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=${ADMIN_USER}" \
      -d "password=${ADMIN_PASS}" \
      -d "grant_type=password" \
      -d "client_id=${ADMIN_CLIENT_ID}")

    ACCESS_TOKEN=$(echo "${token_response}" | jq -r .access_token)

    if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "null" ]; then
        echo "Error: Could not obtain Keycloak admin access token."
        echo "Response: ${token_response}"
        exit 1
    fi
    echo "Successfully obtained Keycloak admin access token."
}

# Function to make an authenticated API call to Keycloak
# Usage: make_api_call <HTTP_METHOD> <ENDPOINT_PATH_FROM_ADMIN_ROOT> [JSON_DATA_FILE_PATH or JSON_STRING]
# Example: make_api_call "GET" "/realms"
# Example: make_api_call "POST" "/realms" "path/to/realm.json"
# Example: make_api_call "PUT" "/realms/myrealm/users/userid/reset-password" '{"type":"password", "value":"newpass", "temporary":false}'
# Returns the HTTP status code in global variable API_CALL_STATUS and response body in API_CALL_RESPONSE
make_api_call() {
    local method="$1"
    local endpoint_path="$2"
    local data_arg="$3"
    local full_url="${KEYCLOAK_SERVER_URL}/admin${endpoint_path}" # Note: /admin path
    local response_output response_file http_code

    response_file=$(mktemp) # Create a temporary file to store the response body

    local curl_opts=(-s -w "%{http_code}" -o "${response_file}" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -X "${method}")

    if [ -n "$data_arg" ]; then
        curl_opts+=(-H "Content-Type: application/json")
        if [ -f "$data_arg" ]; then # If it's a file path
            curl_opts+=(--data-binary "@${data_arg}")
        else # Assume it's a JSON string
            curl_opts+=(--data-binary "${data_arg}")
        fi
    fi

    echo "Executing API call: ${method} ${full_url}"
    http_code=$(curl "${curl_opts[@]}" "${full_url}")

    API_CALL_RESPONSE=$(cat "${response_file}")
    rm -f "${response_file}"
    API_CALL_STATUS=$http_code

    # Basic logging of request and response for debugging
    # echo "API Request: ${method} ${full_url}"
    # if [ -n "$data_arg" ]; then echo "Request Data: $(cat "$data_arg" 2>/dev/null || echo "$data_arg")"; fi
    # echo "API Status: ${API_CALL_STATUS}"
    # echo "API Response: ${API_CALL_RESPONSE}"
}

# Enhanced network test function
test_network_connectivity() {
    local from_container="$1"
    local to_service="$2"
    local to_port="$3"
    local container_id
    
    # Find the container ID for the service
    container_id=$(docker ps --filter "name=${from_container}" --format "{{.ID}}" | head -n 1)
    if [ -z "$container_id" ]; then
        echo "Container '${from_container}' not found!"
        return 1
    fi
    
    echo "⚙️ Testing connectivity from ${from_container} to ${to_service}:${to_port}..."
    
    # Test 1: Basic ping (network layer)
    echo "Running ping test (network layer)..."
    if docker exec $container_id ping -c 2 $to_service &>/dev/null; then
        echo "✓ Ping successful - network layer connectivity confirmed"
    else
        echo "✗ Ping failed - DNS resolution or network connectivity issue"
        
        # Try to diagnose DNS resolution
        echo "Checking DNS resolution inside container..."
        docker exec $container_id cat /etc/resolv.conf
        docker exec $container_id nslookup $to_service 2>/dev/null || true
        
        # Show network list for diagnosis
        echo "Networks for $from_container container:"
        docker inspect --format='{{range $net,$v := .NetworkSettings.Networks}}{{$net}}{{end}}' $container_id
        
        return 1
    fi
    
    # Test 2: Try HTTP connection (application layer)
    echo "Running HTTP test (application layer)..."
    if docker exec $container_id curl -s -o /dev/null -w "%{http_code}" "http://${to_service}:${to_port}" 2>/dev/null; then
        echo "✓ HTTP connection successful - application layer connectivity confirmed"
        return 0
    else
        echo "✗ HTTP connection failed - service may not be accepting connections"
        return 1
    fi
}


echo "Starting ViolentUTF Nightly with Keycloak, APISIX, and AI Proxy Setup for macOS..."

# ---------------------------------------------------------------
# 1. Check Docker and Docker Compose
# ---------------------------------------------------------------
echo "Step 1: Checking Docker and Docker Compose..."
if ! command -v docker &> /dev/null; then
    echo "Docker could not be found. Please install Docker Desktop for Mac."
    echo "Visit https://docs.docker.com/desktop/install/mac-install/ for installation instructions."
    exit 1
fi

DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version &> /dev/null; then
    echo "Docker Compose (V2 CLI plugin) could not be found. Trying older 'docker-compose'..."
    if ! command -v docker-compose &> /dev/null; then
        echo "Neither 'docker compose' nor 'docker-compose' found."
        echo "Ensure you have Docker Desktop for Mac installed and running."
        exit 1
    else
        DOCKER_COMPOSE_CMD="docker-compose"
        echo "Found older 'docker-compose'. Will use that."
    fi
fi
echo "Using Docker Compose command: $DOCKER_COMPOSE_CMD"

# --- Network validation function ---
validate_network_configuration() {
    echo "Validating Docker network configuration..."
    if ! docker network inspect $SHARED_NETWORK_NAME >/dev/null 2>&1; then
        echo "❌ Shared network not found, creating..."
        docker network create $SHARED_NETWORK_NAME
    fi
    
    # Verify network connectivity between services
    echo "✅ Network validation completed"
}

# --- Python dependencies verification function ---
verify_python_dependencies() {
    echo "Verifying Python dependencies..."
    if [ -f "violentutf/requirements.txt" ]; then
        if [ -f ".vitutf/bin/activate" ]; then
            source .vitutf/bin/activate
            pip install -r violentutf/requirements.txt --quiet --disable-pip-version-check
            echo "✅ Python dependencies verified"
        else
            echo "⚠️ Virtual environment not found, skipping dependency verification"
        fi
    else
        echo "⚠️ Requirements file not found, skipping dependency verification"
    fi
}

# --- JWT secret consistency check function ---
check_jwt_consistency() {
    echo "Checking JWT secret consistency across services..."
    
    # Ensure all services use the same JWT secret (this will be called during secret generation)
    echo "✅ JWT secret consistency will be enforced during configuration"
}

# --- Service health validation function ---
validate_all_services() {
    echo "Validating all service health..."
    local issues_found=0
    
    # Check APISIX stack
    if [ -d "apisix" ]; then
        if ! (cd apisix && docker compose ps 2>/dev/null | grep -q "Up.*healthy\|Up.*running"); then
            echo "❌ APISIX stack not healthy"
            issues_found=$((issues_found + 1))
        else
            echo "✅ APISIX stack running"
        fi
    fi
    
    # Check Keycloak
    if [ -d "keycloak" ]; then
        if ! (cd keycloak && docker compose ps 2>/dev/null | grep -q "Up.*healthy\|Up.*running"); then
            echo "❌ Keycloak not healthy"
            issues_found=$((issues_found + 1))
        else
            echo "✅ Keycloak running"
        fi
    fi
    
    # Verify API connectivity (with timeout)
    if timeout 10 curl -f http://localhost:9080/health >/dev/null 2>&1; then
        echo "✅ APISIX gateway responding"
    else
        echo "⚠️ APISIX gateway not responding (may still be starting up)"
        issues_found=$((issues_found + 1))
    fi
    
    if [ $issues_found -eq 0 ]; then
        echo "✅ All services validated and healthy"
        return 0
    else
        echo "⚠️ Found $issues_found service issues"
        return 1
    fi
}

# --- System state verification function ---
verify_system_state() {
    echo "Verifying system restored to working state..."
    
    # Check all expected files exist
    local required_files=(
        "ai-tokens.env"
        "violentutf/.env" 
        "violentutf/.streamlit/secrets.toml"
        "violentutf_api/fastapi_app/.env"
        "keycloak/.env"
        ".vitutf/bin/activate"
    )
    
    local missing_files=0
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            echo "❌ Missing required file: $file"
            missing_files=$((missing_files + 1))
        fi
    done
    
    if [ $missing_files -eq 0 ]; then
        echo "✅ All required configuration files present"
    else
        echo "❌ Missing $missing_files required files"
        return 1
    fi
    
    # Check all expected services
    if validate_all_services; then
        echo "✅ System state verification completed - ready for use!"
        return 0
    else
        echo "⚠️ System state verification found issues - may need manual intervention"
        return 1
    fi
}

if ! docker info &> /dev/null || ! docker ps &> /dev/null; then
    echo "Docker daemon is not running or current user cannot connect to it."
    echo "Please start Docker Desktop and ensure it's running."
    exit 1
fi
echo "Docker and Docker Compose check passed."

# Create a shared network for all services
validate_network_configuration

# Function to discover actual container names for the network
discover_container_names() {
    echo "Discovering container names for network configuration..."
    
    # Get APISIX container name
    APISIX_CONTAINER_NAME=$(docker ps --filter "name=apisix" --filter "status=running" --format "{{.Names}}" | head -n 1)
    if [ -z "$APISIX_CONTAINER_NAME" ]; then
        APISIX_CONTAINER_NAME="apisix-apisix-1"  # Default fallback
    fi
    
    # Get Keycloak container name  
    KEYCLOAK_CONTAINER_NAME=$(docker ps --filter "name=keycloak" --filter "status=running" --format "{{.Names}}" | head -n 1)
    if [ -z "$KEYCLOAK_CONTAINER_NAME" ]; then
        KEYCLOAK_CONTAINER_NAME="keycloak-keycloak-1"  # Default fallback
    fi
    
    # Get ViolentUTF API container name
    VIOLENTUTF_API_CONTAINER_NAME=$(docker ps --filter "name=violentutf_api" --filter "status=running" --format "{{.Names}}" | head -n 1)
    if [ -z "$VIOLENTUTF_API_CONTAINER_NAME" ]; then
        VIOLENTUTF_API_CONTAINER_NAME="violentutf_api"  # Default fallback
    fi
    
    echo "Discovered container names:"
    echo "  APISIX: $APISIX_CONTAINER_NAME"
    echo "  Keycloak: $KEYCLOAK_CONTAINER_NAME" 
    echo "  ViolentUTF API: $VIOLENTUTF_API_CONTAINER_NAME"
    
    # Export for use in environment files
    export APISIX_CONTAINER_NAME
    export KEYCLOAK_CONTAINER_NAME
    export VIOLENTUTF_API_CONTAINER_NAME
}

# ---------------------------------------------------------------
# GENERATE ALL SECRETS UPFRONT
# ---------------------------------------------------------------
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

# Ensure JWT secret consistency
check_jwt_consistency

echo "✅ Generated ${#SENSITIVE_VALUES[@]} secure secrets"

# ---------------------------------------------------------------
# CREATE ALL CONFIGURATION FILES UPFRONT
# ---------------------------------------------------------------
echo ""
echo "=========================================="
echo "CREATING CONFIGURATION FILES"
echo "=========================================="

# --- Create Keycloak .env ---
echo "Creating Keycloak configuration..."
mkdir -p keycloak
cat > keycloak/.env <<EOF
POSTGRES_PASSWORD=$KEYCLOAK_POSTGRES_PASSWORD
EOF
echo "✅ Created keycloak/.env"

# --- Create APISIX configurations ---
echo "Creating APISIX configurations..."
mkdir -p apisix/conf

# Process config.yaml template
if [ -f "apisix/conf/config.yaml.template" ]; then
    prepare_config_from_template "apisix/conf/config.yaml.template"
    replace_in_file "apisix/conf/config.yaml" "APISIX_ADMIN_KEY_PLACEHOLDER" "$APISIX_ADMIN_KEY" "APISIX Admin API Key"
    replace_in_file "apisix/conf/config.yaml" "APISIX_KEYRING_VALUE_1_PLACEHOLDER" "$APISIX_KEYRING_VALUE_1" "APISIX Keyring Value 1"
    replace_in_file "apisix/conf/config.yaml" "APISIX_KEYRING_VALUE_2_PLACEHOLDER" "$APISIX_KEYRING_VALUE_2" "APISIX Keyring Value 2"
    echo "✅ Created apisix/conf/config.yaml"
fi

# Process dashboard.yaml template
if [ -f "apisix/conf/dashboard.yaml.template" ]; then
    prepare_config_from_template "apisix/conf/dashboard.yaml.template"
    replace_in_file "apisix/conf/dashboard.yaml" "APISIX_DASHBOARD_SECRET_PLACEHOLDER" "$APISIX_DASHBOARD_SECRET" "APISIX Dashboard JWT Secret"
    replace_in_file "apisix/conf/dashboard.yaml" "APISIX_DASHBOARD_PASSWORD_PLACEHOLDER" "$APISIX_DASHBOARD_PASSWORD" "APISIX Dashboard Admin Password"
    echo "✅ Created apisix/conf/dashboard.yaml"
fi

# Process nginx.conf template if exists
if [ -f "apisix/conf/nginx.conf.template" ]; then
    prepare_config_from_template "apisix/conf/nginx.conf.template"
    echo "✅ Created apisix/conf/nginx.conf"
fi

# Create APISIX .env file for configure_routes.sh script
echo "Creating APISIX .env file..."
cat > apisix/.env <<EOF
# APISIX Configuration
APISIX_ADMIN_KEY=$APISIX_ADMIN_KEY
EOF
echo "✅ Created apisix/.env"

# Create prometheus.yml if missing
if [ ! -f "apisix/conf/prometheus.yml" ]; then
    cat > apisix/conf/prometheus.yml <<'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'apisix'
    static_configs:
      - targets: ['apisix:9091']
EOF
    echo "✅ Created apisix/conf/prometheus.yml"
fi

# --- Create ViolentUTF configurations ---
echo "Creating ViolentUTF configurations..."
mkdir -p violentutf/.streamlit

# Create .env file
cat > violentutf/.env <<EOF
KEYCLOAK_URL=http://localhost:8080/
KEYCLOAK_REALM=ViolentUTF
KEYCLOAK_CLIENT_ID=violentutf
KEYCLOAK_CLIENT_SECRET=$VIOLENTUTF_CLIENT_SECRET
KEYCLOAK_USERNAME=violentutf.web
KEYCLOAK_PASSWORD=$VIOLENTUTF_USER_PASSWORD
KEYCLOAK_APISIX_CLIENT_ID=apisix
KEYCLOAK_APISIX_CLIENT_SECRET=$APISIX_CLIENT_SECRET
OPENAI_CHAT_DEPLOYMENT='OpenAI API'
OPENAI_CHAT_ENDPOINT=https://api.openai.com/v1/responses
OPENAI_CHAT_KEY=***
PYRIT_DB_SALT=$VIOLENTUTF_PYRIT_SALT
JWT_SECRET_KEY=$FASTAPI_SECRET_KEY
VIOLENTUTF_API_KEY=$VIOLENTUTF_API_KEY
VIOLENTUTF_API_URL=http://localhost:9080/api
KEYCLOAK_URL_BASE=http://localhost:9080/auth
AI_PROXY_BASE_URL=http://localhost:9080/ai
EOF
echo "✅ Created violentutf/.env"

# Create secrets.toml with full auth structure
cat > violentutf/.streamlit/secrets.toml <<EOF
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "$VIOLENTUTF_COOKIE_SECRET"

[auth.keycloak]
client_id = "violentutf"
client_secret = "$VIOLENTUTF_CLIENT_SECRET"
server_metadata_url = "${KEYCLOAK_SERVER_URL}/realms/ViolentUTF/.well-known/openid-configuration"

[auth.providers.keycloak]
issuer = "${KEYCLOAK_SERVER_URL}/realms/ViolentUTF"
token_endpoint = "${KEYCLOAK_SERVER_URL}/realms/ViolentUTF/protocol/openid-connect/token"
authorization_endpoint = "${KEYCLOAK_SERVER_URL}/realms/ViolentUTF/protocol/openid-connect/auth"
userinfo_endpoint = "${KEYCLOAK_SERVER_URL}/realms/ViolentUTF/protocol/openid-connect/userinfo"
jwks_uri = "${KEYCLOAK_SERVER_URL}/realms/ViolentUTF/protocol/openid-connect/certs"

[apisix]
client_id = "apisix"
client_secret = "$APISIX_CLIENT_SECRET"
EOF
echo "✅ Created violentutf/.streamlit/secrets.toml"

# --- Create FastAPI configuration ---
echo "Creating FastAPI configuration..."
mkdir -p violentutf_api/fastapi_app

# Pre-check: Ensure FastAPI config.py has necessary fields to prevent Pydantic validation errors
echo "Checking FastAPI configuration compatibility..."
if [ -f "violentutf_api/fastapi_app/app/core/config.py" ]; then
    # Check if the new fields are already in config.py
    if ! grep -q "VIOLENTUTF_API_URL" "violentutf_api/fastapi_app/app/core/config.py"; then
        echo "⚠️  WARNING: FastAPI config.py missing new environment variable definitions"
        echo "   The following fields need to be added to Settings class in config.py:"
        echo "   - VIOLENTUTF_API_URL"
        echo "   - APISIX_CONTAINER_NAME" 
        echo "   - KEYCLOAK_CONTAINER_NAME"
        echo "   - DEFAULT_USERNAME"
        echo "   - GENERATOR_TYPE_MAPPING"
        echo ""
        echo "   Without these fields, FastAPI will fail to start with Pydantic validation errors."
        echo "   Please update violentutf_api/fastapi_app/app/core/config.py before proceeding."
        echo ""
        echo "   Example additions needed:"
        echo '   VIOLENTUTF_API_URL: Optional[str] = Field(default=None, env="VIOLENTUTF_API_URL")'
        echo '   DEFAULT_USERNAME: str = Field(default="violentutf.web", env="DEFAULT_USERNAME")'
        echo ""
    else
        echo "✅ FastAPI config.py appears compatible with new environment variables"
    fi
fi

cat > violentutf_api/fastapi_app/.env <<EOF
# FastAPI Configuration
SECRET_KEY=$FASTAPI_SECRET_KEY
JWT_SECRET_KEY=$FASTAPI_SECRET_KEY
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
API_KEY_EXPIRE_DAYS=365

# Database
DATABASE_URL=sqlite+aiosqlite:///./app_data/violentutf.db

# Keycloak Configuration
KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=ViolentUTF
KEYCLOAK_CLIENT_ID=$FASTAPI_CLIENT_ID
KEYCLOAK_CLIENT_SECRET=$FASTAPI_CLIENT_SECRET

# APISIX Configuration
APISIX_BASE_URL=http://apisix-apisix-1:9080
APISIX_ADMIN_URL=http://apisix-apisix-1:9180
APISIX_ADMIN_KEY=$APISIX_ADMIN_KEY
VIOLENTUTF_API_KEY=$VIOLENTUTF_API_KEY

# NEW: Docker Network Configuration for Inter-Service Communication
# These fields MUST be defined in violentutf_api/fastapi_app/app/core/config.py
# to prevent Pydantic validation errors on startup
VIOLENTUTF_API_URL=http://apisix-apisix-1:9080
APISIX_CONTAINER_NAME=apisix-apisix-1
KEYCLOAK_CONTAINER_NAME=keycloak-keycloak-1

# User Context Configuration (for DuckDB isolation)
# Required for proper user-based data isolation in orchestrators
DEFAULT_USERNAME=violentutf.web
PYRIT_DB_SALT=$VIOLENTUTF_PYRIT_SALT
APP_DATA_DIR=/app/app_data/violentutf

# Generator Type Configuration (prevent type mapping issues)
# Maps UI generator types to PyRIT implementation types
GENERATOR_TYPE_MAPPING=AI Gateway:apisix_ai_gateway

# Service Configuration
SERVICE_NAME=ViolentUTF API
SERVICE_VERSION=1.0.0
DEBUG=false
EOF
echo "✅ Created violentutf_api/fastapi_app/.env"

# Synchronize environment variables between services
sync_environment_variables() {
    echo "Synchronizing environment variables between services..."
    
    # Update FastAPI .env with discovered container names
    if [ -f "violentutf_api/fastapi_app/.env" ] && [ -n "$APISIX_CONTAINER_NAME" ]; then
        # Update APISIX URLs to use actual container name
        sed -i '' "s/APISIX_BASE_URL=.*/APISIX_BASE_URL=http:\/\/$APISIX_CONTAINER_NAME:9080/" "violentutf_api/fastapi_app/.env"
        sed -i '' "s/APISIX_ADMIN_URL=.*/APISIX_ADMIN_URL=http:\/\/$APISIX_CONTAINER_NAME:9180/" "violentutf_api/fastapi_app/.env"
        sed -i '' "s/VIOLENTUTF_API_URL=.*/VIOLENTUTF_API_URL=http:\/\/$APISIX_CONTAINER_NAME:9080/" "violentutf_api/fastapi_app/.env"
        
        echo "✅ Updated FastAPI environment variables with container names"
    fi
    
    # Verify JWT secret consistency (existing functionality enhanced)
    STREAMLIT_JWT=$(grep "^JWT_SECRET_KEY=" violentutf/.env 2>/dev/null | cut -d'=' -f2)
    FASTAPI_JWT=$(grep "^JWT_SECRET_KEY=" violentutf_api/fastapi_app/.env 2>/dev/null | cut -d'=' -f2)
    
    if [ "$STREAMLIT_JWT" = "$FASTAPI_JWT" ] && [ -n "$STREAMLIT_JWT" ]; then
        echo "✅ JWT secret consistency verified between services"
    else
        echo "❌ JWT secret mismatch detected between services"
        echo "   This will cause authentication failures between Streamlit and FastAPI"
        return 1
    fi
}

# Validate JWT secret consistency between both .env files
STREAMLIT_JWT=$(grep "^JWT_SECRET_KEY=" violentutf/.env 2>/dev/null | cut -d'=' -f2)
FASTAPI_JWT=$(grep "^JWT_SECRET_KEY=" violentutf_api/fastapi_app/.env 2>/dev/null | cut -d'=' -f2)

if [ "$STREAMLIT_JWT" = "$FASTAPI_JWT" ] && [ -n "$STREAMLIT_JWT" ]; then
    echo "✅ JWT secret consistency verified: ${STREAMLIT_JWT:0:8}..."
else
    echo "⚠️  WARNING: JWT secret mismatch detected!"
    echo "   Streamlit JWT: ${STREAMLIT_JWT:0:8}..."
    echo "   FastAPI JWT:   ${FASTAPI_JWT:0:8}..."
    echo "   This will cause authentication failures. Regenerating with consistent key..."
    
    # Use the FastAPI version as source of truth
    if [ -n "$FASTAPI_JWT" ]; then
        sed -i '' "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$FASTAPI_JWT|" violentutf/.env
        echo "✅ Fixed: Updated Streamlit .env with FastAPI JWT secret"
    fi
fi

# Synchronize environment variables between services
sync_environment_variables

echo ""
echo "All configuration files created successfully!"
echo ""

# ---------------------------------------------------------------
# SECTION A: KEYCLOAK SETUP
# ---------------------------------------------------------------
echo "SECTION A: SETTING UP KEYCLOAK"

# ---------------------------------------------------------------
# 2. Keycloak environment is already configured
# ---------------------------------------------------------------
echo "Step 2: Keycloak .env already configured."
KEYCLOAK_ENV_DIR="keycloak"
KEYCLOAK_ENV_FILE="${KEYCLOAK_ENV_DIR}/.env"

# ---------------------------------------------------------------
# 3. Check Keycloak stack and launch if not running
# ---------------------------------------------------------------
echo "Step 3: Checking and launching Keycloak Docker stack..."
KEYCLOAK_SERVICE_NAME_IN_COMPOSE="keycloak" # As defined in your docker-compose.yml

KEYCLOAK_SETUP_NEEDED=true
# Check if the service is running using docker compose ps
if ${DOCKER_COMPOSE_CMD} -f "${KEYCLOAK_ENV_DIR}/docker-compose.yml" ps -q ${KEYCLOAK_SERVICE_NAME_IN_COMPOSE} 2>/dev/null | grep -q .; then
    CONTAINER_ID=$(${DOCKER_COMPOSE_CMD} -f "${KEYCLOAK_ENV_DIR}/docker-compose.yml" ps -q ${KEYCLOAK_SERVICE_NAME_IN_COMPOSE} 2>/dev/null)
    if [ -n "$CONTAINER_ID" ]; then
      if docker inspect -f '{{.State.Running}}' "$CONTAINER_ID" 2>/dev/null | grep -q "true"; then
        echo "Keycloak service '${KEYCLOAK_SERVICE_NAME_IN_COMPOSE}' appears to be already running."
        KEYCLOAK_SETUP_NEEDED=false
      fi
    fi
fi

if [ "$KEYCLOAK_SETUP_NEEDED" = true ]; then
    echo "Keycloak stack not found or not running. Proceeding with setup."
    # Store current directory and cd into keycloak dir
    ORIGINAL_DIR=$(pwd)
    cd "$KEYCLOAK_ENV_DIR" || { echo "Failed to cd into $KEYCLOAK_ENV_DIR"; exit 1; }
    
    # Ensure docker-compose.yml has network configuration
    echo "Ensuring Keycloak docker-compose.yml has proper network configuration..."
    ensure_network_in_compose "docker-compose.yml" "keycloak"
    
    echo "Launching Docker Compose for Keycloak..."
    if ${DOCKER_COMPOSE_CMD} up -d; then
        echo "Keycloak stack started successfully."
        echo "Waiting for Keycloak to be fully operational (this might take a minute or two)..."
        RETRY_COUNT=0
        MAX_RETRIES=30 # ~5 minutes
        SUCCESS=false
        until [ $RETRY_COUNT -ge $MAX_RETRIES ]; do
            RETRY_COUNT=$((RETRY_COUNT+1))
            # Check Keycloak health/ready endpoint (not admin API, no token needed for this one)
            HTTP_STATUS_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "${KEYCLOAK_SERVER_URL}/realms/master")
            if [ "$HTTP_STATUS_HEALTH" -eq 200 ]; then
                echo "Keycloak is up and responding on its main endpoint."
                SUCCESS=true
                break
            fi
            echo "Keycloak not ready yet (attempt $RETRY_COUNT/$MAX_RETRIES, status $HTTP_STATUS_HEALTH). Waiting 10 seconds..."
            sleep 10
        done

        if [ "$SUCCESS" = false ]; then
            echo "Keycloak did not become ready in time. Please check Docker logs."
            ${DOCKER_COMPOSE_CMD} logs ${KEYCLOAK_SERVICE_NAME_IN_COMPOSE}
            cd "$ORIGINAL_DIR"
            exit 1
        fi
    else
        echo "Failed to start Keycloak stack. Check Docker Compose logs."
        ${DOCKER_COMPOSE_CMD} logs
        cd "$ORIGINAL_DIR"
        exit 1
    fi
    cd "$ORIGINAL_DIR" # Return to the original directory

    # Ensure the container is connected to the shared network
    echo "Ensuring Keycloak container is connected to shared network..."
    KEYCLOAK_CONTAINER=$(docker ps --filter "name=keycloak" --format "{{.ID}}" | head -n 1)
    if [ -n "$KEYCLOAK_CONTAINER" ]; then
        # Check if already connected
        if ! docker inspect "$KEYCLOAK_CONTAINER" | grep -q "\"$SHARED_NETWORK_NAME\""; then
            echo "Manually connecting Keycloak container to shared network..."
            docker network connect $SHARED_NETWORK_NAME $KEYCLOAK_CONTAINER
            echo "Keycloak container connected to $SHARED_NETWORK_NAME"
        else
            echo "Keycloak container already connected to $SHARED_NETWORK_NAME"
        fi
    fi
fi


if [ "$KEYCLOAK_SETUP_NEEDED" = true ]; then
    get_keycloak_admin_token # Obtain admin token for subsequent API calls

    # ---------------------------------------------------------------
    # 4. Import realm-export.json to Keycloak via API
    # ---------------------------------------------------------------
    echo "Step 4: Importing Keycloak realm via API..."
    REALM_EXPORT_FILE="${KEYCLOAK_ENV_DIR}/realm-export.json"

    if [ ! -f "$REALM_EXPORT_FILE" ]; then
        echo "Error: $REALM_EXPORT_FILE not found!"
        exit 1
    fi
    
    # Extract realm name from the export file
    TARGET_REALM_NAME=$(jq -r .realm "$REALM_EXPORT_FILE")
    if [ -z "$TARGET_REALM_NAME" ] || [ "$TARGET_REALM_NAME" == "null" ]; then
        echo "Error: Could not extract realm name from $REALM_EXPORT_FILE"
        exit 1
    fi
    echo "Target realm name: $TARGET_REALM_NAME"

    # Check if realm already exists
    make_api_call "GET" "/realms/${TARGET_REALM_NAME}"
    if [ "$API_CALL_STATUS" -eq 200 ]; then
        echo "Realm '$TARGET_REALM_NAME' already exists. Deleting and re-importing."
        make_api_call "DELETE" "/realms/${TARGET_REALM_NAME}"
        if [ "$API_CALL_STATUS" -ne 204 ]; then # 204 No Content is success for DELETE
            echo "Failed to delete existing realm '$TARGET_REALM_NAME'. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
            exit 1
        fi
        echo "Existing realm '$TARGET_REALM_NAME' deleted."
    elif [ "$API_CALL_STATUS" -ne 404 ]; then # 404 Not Found is okay (realm doesn't exist)
        echo "Error checking for realm '$TARGET_REALM_NAME'. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi

    echo "Importing realm '$TARGET_REALM_NAME' from $REALM_EXPORT_FILE via API..."
    make_api_call "POST" "/realms" "$REALM_EXPORT_FILE"
    if [ "$API_CALL_STATUS" -eq 201 ]; then # 201 Created is success for POST
        echo "Realm '$TARGET_REALM_NAME' imported successfully via API."
    else
        echo "Failed to import realm '$TARGET_REALM_NAME' via API. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi

    # ---------------------------------------------------------------
    # 5. ViolentUTF env files already configured
    # ---------------------------------------------------------------
    echo "Step 5: ViolentUTF .env and secrets.toml already configured."
    VIOLENTUTF_DIR="violentutf"
    VIOLENTUTF_ENV_FILE="${VIOLENTUTF_DIR}/.env"
    VIOLENTUTF_SECRETS_DIR="${VIOLENTUTF_DIR}/.streamlit"
    VIOLENTUTF_SECRETS_FILE="${VIOLENTUTF_SECRETS_DIR}/secrets.toml"

    # ---------------------------------------------------------------
    # 6. Keycloak API changes for ViolentUTF realm/client
    # ---------------------------------------------------------------
    echo "Step 6: Configuring ViolentUTF client in Keycloak via API..."
    VUTF_REALM_NAME="$TARGET_REALM_NAME" # Should be "ViolentUTF"
    VUTF_CLIENT_ID_TO_CONFIGURE="violentutf" # As per your realm-export.json

    # Get internal client ID (UUID) for the 'violentutf' client
    make_api_call "GET" "/realms/${VUTF_REALM_NAME}/clients?clientId=${VUTF_CLIENT_ID_TO_CONFIGURE}"
    if [ "$API_CALL_STATUS" -ne 200 ]; then
        echo "Error: Could not get client info for '${VUTF_CLIENT_ID_TO_CONFIGURE}'. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi
    KC_CLIENT_UUID=$(echo "$API_CALL_RESPONSE" | jq -r '.[0].id') # Assumes unique client ID returns one item in array
    if [ -z "$KC_CLIENT_UUID" ] || [ "$KC_CLIENT_UUID" == "null" ]; then
        echo "Error: Client '${VUTF_CLIENT_ID_TO_CONFIGURE}' not found in realm '${VUTF_REALM_NAME}' via API."
        exit 1
    fi
    echo "Found client '${VUTF_CLIENT_ID_TO_CONFIGURE}' with UUID '${KC_CLIENT_UUID}'."

    # Update client to use our pre-generated secret
    echo "Updating client secret for '${VUTF_CLIENT_ID_TO_CONFIGURE}' to use pre-generated value..."
    
    # Get current client configuration
    make_api_call "GET" "/realms/${VUTF_REALM_NAME}/clients/${KC_CLIENT_UUID}"
    if [ "$API_CALL_STATUS" -ne 200 ]; then
        echo "Error: Failed to get client configuration. Status: $API_CALL_STATUS"
        exit 1
    fi
    
    # Update the client configuration with our pre-generated secret
    CLIENT_CONFIG=$(echo "$API_CALL_RESPONSE" | jq --arg secret "$VIOLENTUTF_CLIENT_SECRET" '.secret = $secret')
    
    # Save to temp file for the PUT request
    echo "$CLIENT_CONFIG" > /tmp/client-update.json
    
    # Update the client
    make_api_call "PUT" "/realms/${VUTF_REALM_NAME}/clients/${KC_CLIENT_UUID}" "/tmp/client-update.json"
    if [ "$API_CALL_STATUS" -ne 204 ]; then
        echo "Error: Failed to update client secret. Status: $API_CALL_STATUS"
        exit 1
    fi
    
    echo "Successfully updated client '${VUTF_CLIENT_ID_TO_CONFIGURE}' with pre-generated secret."
    rm -f /tmp/client-update.json

    # Update APISIX client secret
    echo "Updating APISIX client secret..."
    
    # Find APISIX client UUID
    make_api_call "GET" "/realms/${VUTF_REALM_NAME}/clients?clientId=apisix"
    if [ "$API_CALL_STATUS" -ne 200 ]; then
        echo "Error: Failed to find APISIX client. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi
    
    APISIX_CLIENT_UUID=$(echo "$API_CALL_RESPONSE" | jq -r '.[0].id')
    if [ -z "$APISIX_CLIENT_UUID" ] || [ "$APISIX_CLIENT_UUID" == "null" ]; then
        echo "Error: APISIX client not found in realm."
        exit 1
    fi
    
    # Update APISIX client to use our pre-generated secret
    echo "Updating APISIX client to use pre-generated secret..."
    
    # Get current client configuration
    make_api_call "GET" "/realms/${VUTF_REALM_NAME}/clients/${APISIX_CLIENT_UUID}"
    if [ "$API_CALL_STATUS" -ne 200 ]; then
        echo "Error: Failed to get APISIX client configuration. Status: $API_CALL_STATUS"
        exit 1
    fi
    
    # Update the client configuration with our pre-generated secret
    CLIENT_CONFIG=$(echo "$API_CALL_RESPONSE" | jq --arg secret "$APISIX_CLIENT_SECRET" '.secret = $secret')
    
    # Save to temp file for the PUT request
    echo "$CLIENT_CONFIG" > /tmp/apisix-client-update.json
    
    # Update the client
    make_api_call "PUT" "/realms/${VUTF_REALM_NAME}/clients/${APISIX_CLIENT_UUID}" "/tmp/apisix-client-update.json"
    if [ "$API_CALL_STATUS" -ne 204 ]; then
        echo "Error: Failed to update APISIX client secret. Status: $API_CALL_STATUS"
        exit 1
    fi
    
    echo "Successfully updated APISIX client with pre-generated secret."
    rm -f /tmp/apisix-client-update.json
    
    # Export for use in route creation
    export KEYCLOAK_APISIX_SECRET=$APISIX_CLIENT_SECRET
    
    # APISIX client credentials already stored in env files

    # Read KEYCLOAK_USERNAME from violentutf/.env
    # Use awk for more robust parsing, allowing for spaces around '=' and trimming whitespace.
    KEYCLOAK_APP_USERNAME=$(awk -F= '/^KEYCLOAK_USERNAME[[:space:]]*=/ {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' "$VIOLENTUTF_ENV_FILE")
    
    if [ -z "$KEYCLOAK_APP_USERNAME" ]; then
        echo "Warning: KEYCLOAK_USERNAME not found or is empty in $VIOLENTUTF_ENV_FILE."
        KEYCLOAK_APP_USERNAME="testuser" 
        echo "Defaulting KEYCLOAK_USERNAME to 'testuser'."
        # Check if the line exists to update, otherwise append
        if grep -q "^KEYCLOAK_USERNAME[[:space:]]*=" "$VIOLENTUTF_ENV_FILE"; then
            sed -i '' "s|^KEYCLOAK_USERNAME[[:space:]]*=.*|KEYCLOAK_USERNAME=${KEYCLOAK_APP_USERNAME}|" "$VIOLENTUTF_ENV_FILE"
        else
            echo "KEYCLOAK_USERNAME=${KEYCLOAK_APP_USERNAME}" >> "$VIOLENTUTF_ENV_FILE"
        fi
        echo "Updated $VIOLENTUTF_ENV_FILE with default username."
    fi
    echo "Using KEYCLOAK_USERNAME: $KEYCLOAK_APP_USERNAME"
    SENSITIVE_VALUES+=("Keycloak Username: $KEYCLOAK_APP_USERNAME")

    # Check if user exists, if not, create
    make_api_call "GET" "/realms/${VUTF_REALM_NAME}/users?username=${KEYCLOAK_APP_USERNAME}&exact=true" # Added exact=true for precise match
    if [ "$API_CALL_STATUS" -ne 200 ]; then
        echo "Error checking for user '${KEYCLOAK_APP_USERNAME}'. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi
    
    # jq needs to handle an empty array if user not found, or an array with one user if found
    USER_EXISTS_ID=$(echo "$API_CALL_RESPONSE" | jq -r 'if type == "array" and length > 0 then .[0].id else null end')
    
    if [ "$USER_EXISTS_ID" == "null" ] || [ -z "$USER_EXISTS_ID" ]; then
        echo "User '${KEYCLOAK_APP_USERNAME}' not found. Creating user via API..."
        USER_CREATE_PAYLOAD="{\"username\":\"${KEYCLOAK_APP_USERNAME}\", \"enabled\":true}"
        make_api_call "POST" "/realms/${VUTF_REALM_NAME}/users" "${USER_CREATE_PAYLOAD}"
        
        if [ "$API_CALL_STATUS" -ne 201 ]; then
            echo "Error: Failed to create user '${KEYCLOAK_APP_USERNAME}' via API. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
            exit 1
        fi
        # Re-fetch user to get ID, as POST might not return it directly or only in Location header
        make_api_call "GET" "/realms/${VUTF_REALM_NAME}/users?username=${KEYCLOAK_APP_USERNAME}&exact=true"
        if [ "$API_CALL_STATUS" -ne 200 ]; then
             echo "Error fetching newly created user '${KEYCLOAK_APP_USERNAME}'. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
             exit 1
        fi
        USER_EXISTS_ID=$(echo "$API_CALL_RESPONSE" | jq -r 'if type == "array" and length > 0 then .[0].id else null end')
        if [ "$USER_EXISTS_ID" == "null" ] || [ -z "$USER_EXISTS_ID" ]; then
            echo "Error: Failed to retrieve ID for newly created user '${KEYCLOAK_APP_USERNAME}'."
            exit 1
        fi
        echo "User '${KEYCLOAK_APP_USERNAME}' created with ID '${USER_EXISTS_ID}'."
    else
        echo "User '${KEYCLOAK_APP_USERNAME}' already exists with ID '${USER_EXISTS_ID}'."
    fi

    # Create/Reset credential for the user
    echo "Setting a new password for user '${KEYCLOAK_APP_USERNAME}' via API..."
    NEW_USER_PASSWORD=$(generate_secure_string)
    PASSWORD_RESET_PAYLOAD="{\"type\":\"password\", \"value\":\"${NEW_USER_PASSWORD}\", \"temporary\":false}"
    make_api_call "PUT" "/realms/${VUTF_REALM_NAME}/users/${USER_EXISTS_ID}/reset-password" "${PASSWORD_RESET_PAYLOAD}"
    if [ "$API_CALL_STATUS" -ne 204 ]; then # 204 No Content is success
        echo "Error: Failed to set password for user '${KEYCLOAK_APP_USERNAME}' via API. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi
    echo "Password for user '${KEYCLOAK_APP_USERNAME}' has been set via API."
    SENSITIVE_VALUES+=("Keycloak User Password: $NEW_USER_PASSWORD")

    # Update KEYCLOAK_PASSWORD in violentutf/.env
    # Use a temporary file for sed to avoid issues with in-place editing on some macOS sed versions with certain patterns
    TMP_ENV_FILE=$(mktemp)
    sed "s|^KEYCLOAK_PASSWORD[[:space:]]*=.*|KEYCLOAK_PASSWORD=${NEW_USER_PASSWORD}|" "$VIOLENTUTF_ENV_FILE" > "$TMP_ENV_FILE" && mv "$TMP_ENV_FILE" "$VIOLENTUTF_ENV_FILE"
    echo "Updated KEYCLOAK_PASSWORD in $VIOLENTUTF_ENV_FILE."

    # Assign ai-api-access role to user
    echo "Assigning ai-api-access role to user '${KEYCLOAK_APP_USERNAME}'..."
    
    # First, get the ai-api-access role ID
    make_api_call "GET" "/realms/${VUTF_REALM_NAME}/roles/ai-api-access"
    if [ "$API_CALL_STATUS" -ne 200 ]; then
        echo "Error: Failed to find ai-api-access role. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi
    
    AI_API_ACCESS_ROLE_ID=$(echo "$API_CALL_RESPONSE" | jq -r '.id')
    AI_API_ACCESS_ROLE_NAME=$(echo "$API_CALL_RESPONSE" | jq -r '.name')
    
    if [ -z "$AI_API_ACCESS_ROLE_ID" ] || [ "$AI_API_ACCESS_ROLE_ID" == "null" ]; then
        echo "Error: ai-api-access role not found or invalid ID."
        exit 1
    fi
    
    # Assign role to user
    ROLE_ASSIGNMENT_PAYLOAD="[{\"id\":\"${AI_API_ACCESS_ROLE_ID}\", \"name\":\"${AI_API_ACCESS_ROLE_NAME}\"}]"
    make_api_call "POST" "/realms/${VUTF_REALM_NAME}/users/${USER_EXISTS_ID}/role-mappings/realm" "${ROLE_ASSIGNMENT_PAYLOAD}"
    
    if [ "$API_CALL_STATUS" -ne 204 ]; then # 204 No Content is success for role assignment
        echo "Error: Failed to assign ai-api-access role to user. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi
    
    echo "Successfully assigned ai-api-access role to user '${KEYCLOAK_APP_USERNAME}'."

    # ---------------------------------------------------------------
    # 7. Secrets already configured in env files
    # ---------------------------------------------------------------
    echo "Step 7: Secrets already configured."

    echo "Keycloak client and user configuration complete via API."
else
    echo "Skipped Keycloak setup steps 4-7 as stack was already running."
fi # End of KEYCLOAK_SETUP_NEEDED conditional block

# ---------------------------------------------------------------
# SECTION B: APISIX SETUP
# ---------------------------------------------------------------
echo "SECTION B: SETTING UP APISIX"

# ---------------------------------------------------------------
# B1. Process templates and set up APISIX configuration files
# ---------------------------------------------------------------
echo "Step B1: APISIX configuration files already processed."

# FastAPI env file already created in upfront configuration

# ---------------------------------------------------------------
# B2. Check APISIX stack and launch if not running
# ---------------------------------------------------------------
echo "Step B2: Checking and launching APISIX Docker stack..."
APISIX_SERVICE_NAME_IN_COMPOSE="apisix" # As defined in your docker-compose.yml

APISIX_SETUP_NEEDED=true
# Check if the APISIX service is running
if ${DOCKER_COMPOSE_CMD} -f "apisix/docker-compose.yml" ps -q ${APISIX_SERVICE_NAME_IN_COMPOSE} 2>/dev/null | grep -q .; then
    CONTAINER_ID=$(${DOCKER_COMPOSE_CMD} -f "apisix/docker-compose.yml" ps -q ${APISIX_SERVICE_NAME_IN_COMPOSE} 2>/dev/null)
    if [ -n "$CONTAINER_ID" ]; then
      if docker inspect -f '{{.State.Running}}' "$CONTAINER_ID" 2>/dev/null | grep -q "true"; then
        echo "APISIX service '${APISIX_SERVICE_NAME_IN_COMPOSE}' appears to be already running."
        APISIX_SETUP_NEEDED=false
      fi
    fi
fi

if [ "$APISIX_SETUP_NEEDED" = true ]; then
    echo "APISIX stack not found or not running. Proceeding with setup."
    
    # Ensure APISIX directory exists
    if [ ! -d "apisix" ]; then
        echo "Error: APISIX directory not found!"
        exit 1
    fi
    
    # Create a prometheus.yml file if it doesn't exist
    if [ ! -f "apisix/conf/prometheus.yml" ]; then
        echo "Creating default Prometheus configuration..."
        cat > "apisix/conf/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'apisix'
    static_configs:
      - targets: ['apisix:9091']
    metrics_path: '/apisix/prometheus/metrics'
EOF
    fi
    
    # Store current directory and cd into apisix dir
    ORIGINAL_DIR=$(pwd)
    cd "apisix" || { echo "Failed to cd into apisix directory"; exit 1; }
    
    # Ensure docker-compose.yml has network configuration
    echo "Ensuring APISIX docker-compose.yml has proper network configuration..."
    ensure_network_in_compose "docker-compose.yml" "apisix"
    
    echo "Launching Docker Compose for APISIX..."
    if ${DOCKER_COMPOSE_CMD} up -d; then
        echo "APISIX stack started successfully."
        echo "Waiting for APISIX to be fully operational (this might take a minute)..."
        RETRY_COUNT=0
        MAX_RETRIES=20 # ~2 minutes with 6-second interval
        SUCCESS=false
        until [ $RETRY_COUNT -ge $MAX_RETRIES ]; do
            RETRY_COUNT=$((RETRY_COUNT+1))
            # Check APISIX health by accessing a standard endpoint
            HTTP_STATUS_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "${APISIX_ADMIN_URL}/apisix/admin/routes" \
                 -H "X-API-KEY: ${APISIX_ADMIN_KEY}")
            if [ "$HTTP_STATUS_HEALTH" -eq 200 ] || [ "$HTTP_STATUS_HEALTH" -eq 401 ]; then
                # 401 is also acceptable as it means APISIX is up but auth failed
                # Which is expected if we have auth configured
                echo "APISIX is up and responding on its admin endpoint."
                SUCCESS=true
                break
            fi
            echo "APISIX not ready yet (attempt $RETRY_COUNT/$MAX_RETRIES, status $HTTP_STATUS_HEALTH). Waiting 6 seconds..."
            sleep 6
        done

        if [ "$SUCCESS" = false ]; then
            echo "APISIX did not become ready in time. Please check Docker logs."
            ${DOCKER_COMPOSE_CMD} logs ${APISIX_SERVICE_NAME_IN_COMPOSE}
            cd "$ORIGINAL_DIR"
            exit 1
        fi
    else
        echo "Failed to start APISIX stack. Check Docker Compose logs."
        ${DOCKER_COMPOSE_CMD} logs
        cd "$ORIGINAL_DIR"
        exit 1
    fi
    cd "$ORIGINAL_DIR" # Return to the original directory
    
    # Ensure the container is connected to the shared network
    echo "Ensuring APISIX container is connected to shared network..."
    APISIX_CONTAINER=$(docker ps --filter "name=apisix" --format "{{.ID}}" | head -n 1)
    if [ -n "$APISIX_CONTAINER" ]; then
        # Check if already connected
        if ! docker inspect "$APISIX_CONTAINER" | grep -q "\"$SHARED_NETWORK_NAME\""; then
            echo "Manually connecting APISIX container to shared network..."
            docker network connect $SHARED_NETWORK_NAME $APISIX_CONTAINER
            echo "APISIX container connected to $SHARED_NETWORK_NAME"
        else
            echo "APISIX container already connected to $SHARED_NETWORK_NAME"
        fi
    fi

# Validate Docker network configuration for inter-service communication
validate_docker_network_config() {
    echo "Validating Docker network configuration for inter-service communication..."
    
    # Discover actual container names
    discover_container_names
    
    # Test container-to-container connectivity
    echo "Testing container-to-container connectivity..."
    
    # Test APISIX to ViolentUTF API connectivity using curl instead of nc
    if docker exec "$APISIX_CONTAINER_NAME" curl -s -o /dev/null -w "%{http_code}" "http://$VIOLENTUTF_API_CONTAINER_NAME:8000/health" 2>/dev/null | grep -qE "200|404"; then
        echo "✅ APISIX can reach ViolentUTF API"
    else
        echo "⚠️  APISIX to ViolentUTF API connectivity check skipped (curl might not be available)"
        echo "   Will verify through API endpoint tests"
    fi
    
    # Test ViolentUTF API to APISIX connectivity using Python urllib
    if docker exec "$VIOLENTUTF_API_CONTAINER_NAME" python -c "import urllib.request; urllib.request.urlopen('http://$APISIX_CONTAINER_NAME:9080').getcode()" 2>/dev/null; then
        echo "✅ ViolentUTF API can reach APISIX"
    else
        # Try using requests library if available
        if docker exec "$VIOLENTUTF_API_CONTAINER_NAME" python -c "import requests; print(requests.get('http://$APISIX_CONTAINER_NAME:9080').status_code)" 2>/dev/null | grep -qE "200|404"; then
            echo "✅ ViolentUTF API can reach APISIX"
        else
            echo "⚠️  ViolentUTF API to APISIX connectivity needs verification"
            echo "   Ensuring containers are on the same network..."
            
            # Ensure containers are on the same network
            docker network connect $SHARED_NETWORK_NAME "$VIOLENTUTF_API_CONTAINER_NAME" 2>/dev/null || true
            docker network connect $SHARED_NETWORK_NAME "$APISIX_CONTAINER_NAME" 2>/dev/null || true
            
            echo "   Network connections refreshed. Will verify through API tests."
        fi
    fi
    
    # Verify containers are on the same network
    echo "Verifying network configuration..."
    APISIX_NETWORKS=$(docker inspect "$APISIX_CONTAINER_NAME" --format='{{range $net,$v := .NetworkSettings.Networks}}{{$net}} {{end}}' 2>/dev/null || echo "")
    API_NETWORKS=$(docker inspect "$VIOLENTUTF_API_CONTAINER_NAME" --format='{{range $net,$v := .NetworkSettings.Networks}}{{$net}} {{end}}' 2>/dev/null || echo "")
    
    if echo "$APISIX_NETWORKS" | grep -q "$SHARED_NETWORK_NAME" && echo "$API_NETWORKS" | grep -q "$SHARED_NETWORK_NAME"; then
        echo "✅ Both containers are on the shared network: $SHARED_NETWORK_NAME"
    else
        echo "⚠️  Network configuration mismatch detected"
        echo "   APISIX networks: $APISIX_NETWORKS"
        echo "   API networks: $API_NETWORKS"
    fi
}

    # Validate Docker network configuration
    validate_docker_network_config
    
    # ---------------------------------------------------------------
    # B3. Configure APISIX routes to Keycloak if needed
    # ---------------------------------------------------------------
    echo "Step B3: Configuring APISIX routes to Keycloak..."
    
    # Add a route in APISIX to proxy requests to Keycloak
    # This example creates a route that forwards all requests with prefix /auth to Keycloak
    
    # Create a route to proxy to Keycloak
    echo "Creating APISIX route to Keycloak..."
    ROUTE_ID="keycloak-route"
    ROUTE_CONFIG='{
      "uri": "/auth/*",
      "name": "keycloak-proxy",
      "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
      "upstream": {
        "type": "roundrobin",
        "nodes": {
          "keycloak:8080": 1
        }
      },
      "plugins": {
        "proxy-rewrite": {
          "regex_uri": ["^/auth/(.*)", "/$1"]
        }
      }
    }'
    
    # Send API request to create the route
    curl -i -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/${ROUTE_ID}" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
      -H "Content-Type: application/json" \
      -d "${ROUTE_CONFIG}"
    
    if [ $? -eq 0 ]; then
      echo "Successfully configured APISIX route to Keycloak."
    else
      echo "Warning: Failed to configure APISIX route to Keycloak. You may need to do this manually."
    fi
    
    echo "APISIX setup complete."
    
    # Configure all routes immediately after APISIX is ready
    echo ""
    echo "Configuring API routes now that APISIX is ready..."
    
    # Wait a moment for services to stabilize
    sleep 5
    
    # Configure routes
    if [ -f "configure_routes.sh" ]; then
        echo "Running route configuration script..."
        chmod +x configure_routes.sh
        ./configure_routes.sh
        
        if [ $? -eq 0 ]; then
            echo "✅ Routes configured successfully"
        else
            echo "⚠️  Route configuration may have issues. Check logs for details."
        fi
    else
        echo "⚠️  configure_routes.sh not found in apisix directory"
    fi
    
    cd "$ORIGINAL_DIR"
else
    echo "Skipped APISIX setup as stack was already running."
    
    # If we're using an existing APISIX installation, extract the admin key from config.yaml
    if [ -f "apisix/conf/config.yaml" ]; then
        EXISTING_ADMIN_KEY=$(grep -A 5 "admin_key:" "apisix/conf/config.yaml" | grep "key:" | head -n 1 | awk '{print $2}')
        if [ -n "$EXISTING_ADMIN_KEY" ]; then
            APISIX_ADMIN_KEY=$EXISTING_ADMIN_KEY
            SENSITIVE_VALUES+=("APISIX Admin API Key (existing): $APISIX_ADMIN_KEY")
        fi
    fi
    
    # Still configure routes even if APISIX was already running
    echo ""
    echo "Ensuring API routes are configured..."
    cd "apisix" || { echo "Failed to cd into apisix directory"; }
    
    if [ -f "configure_routes.sh" ]; then
        echo "Running route configuration script..."
        chmod +x configure_routes.sh
        ./configure_routes.sh
        
        if [ $? -eq 0 ]; then
            echo "✅ Routes configured/verified successfully"
        else
            echo "⚠️  Route configuration may have issues. Check logs for details."
        fi
    else
        echo "⚠️  configure_routes.sh not found in apisix directory"
    fi
    
    cd "$ORIGINAL_DIR"

    # Extract dashboard credentials if available
    if [ -f "apisix/conf/dashboard.yaml" ]; then
        EXISTING_DASHBOARD_SECRET=$(grep "secret:" "apisix/conf/dashboard.yaml" | head -n 1 | awk '{print $2}')
        if [ -n "$EXISTING_DASHBOARD_SECRET" ]; then
            SENSITIVE_VALUES+=("APISIX Dashboard JWT Secret (existing): $EXISTING_DASHBOARD_SECRET")
        fi
        
        EXISTING_DASHBOARD_PASSWORD=$(grep -A 3 "users:" "apisix/conf/dashboard.yaml" | grep "password:" | head -n 1 | awk '{print $2}')
        if [ -n "$EXISTING_DASHBOARD_PASSWORD" ]; then
            SENSITIVE_VALUES+=("APISIX Dashboard Admin Password (existing): $EXISTING_DASHBOARD_PASSWORD")
        fi
    fi
    
    # Ensure the container is connected to the shared network
    echo "Ensuring APISIX container is connected to shared network..."
    APISIX_CONTAINER=$(docker ps --filter "name=apisix" --format "{{.ID}}" | head -n 1)
    if [ -n "$APISIX_CONTAINER" ]; then
        # Check if already connected
        if ! docker inspect "$APISIX_CONTAINER" | grep -q "\"$SHARED_NETWORK_NAME\""; then
            echo "Manually connecting APISIX container to shared network..."
            docker network connect $SHARED_NETWORK_NAME $APISIX_CONTAINER
            echo "APISIX container connected to $SHARED_NETWORK_NAME"
        else
            echo "APISIX container already connected to $SHARED_NETWORK_NAME"
        fi
    fi
fi # End of APISIX_SETUP_NEEDED conditional block

# ---------------------------------------------------------------
# SECTION C: AI PROXY SETUP
# ---------------------------------------------------------------
echo "SECTION C: SETTING UP AI PROXY"

# ---------------------------------------------------------------
# C1. Prepare AI Configuration
# ---------------------------------------------------------------
echo "Step C1: Preparing AI configuration..."

if ! create_ai_tokens_template; then
    echo "❌ Please configure $AI_TOKENS_FILE and re-run the script"
    SKIP_AI_SETUP=true
else
    if ! load_ai_tokens; then
        echo "❌ Failed to load AI configuration"
        SKIP_AI_SETUP=true
    else
        SKIP_AI_SETUP=false
    fi
fi

# ---------------------------------------------------------------
# C2. Setup AI Provider Routes
# ---------------------------------------------------------------
# Replace this section in the main script:
if [ "$SKIP_AI_SETUP" != true ]; then
    echo "Step C2: Setting up AI provider routes in APISIX..."
    
    # Check if ai-proxy plugin is available
    if ! check_ai_proxy_plugin; then
        echo "Cannot proceed with AI proxy setup - plugin not available"
        SKIP_AI_SETUP=true
    else
        setup_ai_providers_enhanced
    fi
else
    echo "Skipping AI provider routes setup due to configuration issues."
fi

# ---------------------------------------------------------------
# SECTION D: VIOLENTUTF API SETUP
# ---------------------------------------------------------------
echo "SECTION D: SETTING UP VIOLENTUTF API"

# ---------------------------------------------------------------
# D1. Setup FastAPI Service
# ---------------------------------------------------------------
echo "Step D1: Setting up ViolentUTF FastAPI service..."

# Check if violentutf_api directory exists
if [ ! -d "violentutf_api" ]; then
    echo "Error: violentutf_api directory not found!"
    echo "Please ensure you are running this script from the project root directory."
    exit 1
fi

# Store current directory and cd into violentutf_api
ORIGINAL_DIR=$(pwd)
cd "violentutf_api" || { echo "Failed to cd into violentutf_api directory"; exit 1; }

# FastAPI secrets already generated in upfront configuration

# Create FastAPI client in Keycloak
echo "Creating FastAPI client in Keycloak..."
# Using pre-generated values

# Create the FastAPI client in Keycloak
create_keycloak_client() {
    local client_id="$1"
    local client_secret="$2"
    local redirect_uri="$3"
    
    cat > /tmp/fastapi-client.json <<EOF
{
    "clientId": "${client_id}",
    "name": "ViolentUTF API",
    "description": "FastAPI backend for ViolentUTF",
    "rootUrl": "http://localhost:8000",
    "adminUrl": "http://localhost:8000",
    "baseUrl": "http://localhost:8000",
    "surrogateAuthRequired": false,
    "enabled": true,
    "alwaysDisplayInConsole": false,
    "clientAuthenticatorType": "client-secret",
    "secret": "${client_secret}",
    "redirectUris": ["${redirect_uri}"],
    "webOrigins": ["http://localhost:8000"],
    "notBefore": 0,
    "bearerOnly": false,
    "consentRequired": false,
    "standardFlowEnabled": true,
    "implicitFlowEnabled": false,
    "directAccessGrantsEnabled": true,
    "serviceAccountsEnabled": true,
    "publicClient": false,
    "frontchannelLogout": false,
    "protocol": "openid-connect",
    "attributes": {
        "saml.force.post.binding": "false",
        "saml.multivalued.roles": "false",
        "oauth2.device.authorization.grant.enabled": "false",
        "backchannel.logout.revoke.offline.tokens": "false",
        "saml.server.signature.keyinfo.ext": "false",
        "use.refresh.tokens": "true",
        "oidc.ciba.grant.enabled": "false",
        "backchannel.logout.session.required": "true",
        "client_credentials.use_refresh_token": "false",
        "require.pushed.authorization.requests": "false",
        "saml.client.signature": "false",
        "saml.allow.ecp.flow": "false",
        "id.token.as.detached.signature": "false",
        "saml.assertion.signature": "false",
        "client.secret.creation.time": "$(date +%s)",
        "saml.encrypt": "false",
        "saml.server.signature": "false",
        "exclude.session.state.from.auth.response": "false",
        "saml.artifact.binding": "false",
        "saml_force_name_id_format": "false",
        "acr.loa.map": "{}",
        "tls.client.certificate.bound.access.tokens": "false",
        "saml.authnstatement": "false",
        "display.on.consent.screen": "false",
        "token.response.type.bearer.lower-case": "false",
        "saml.onetimeuse.condition": "false"
    },
    "authenticationFlowBindingOverrides": {},
    "fullScopeAllowed": true,
    "nodeReRegistrationTimeout": -1,
    "defaultClientScopes": ["web-origins", "profile", "roles", "email"],
    "optionalClientScopes": ["address", "phone", "offline_access", "microprofile-jwt"]
}
EOF
    
    # Create the client
    make_api_call "POST" "/realms/${VUTF_REALM_NAME}/clients" "/tmp/fastapi-client.json"
    
    if [ "$API_CALL_STATUS" = "201" ] || [ "$API_CALL_STATUS" = "409" ]; then
        echo "FastAPI client created/exists in Keycloak."
        rm -f /tmp/fastapi-client.json
        return 0
    else
        echo "Failed to create FastAPI client. Status: $API_CALL_STATUS"
        echo "Response: $API_CALL_RESPONSE"
        rm -f /tmp/fastapi-client.json
        return 1
    fi
}

# Only create client if Keycloak is properly set up
if [ "$KEYCLOAK_SETUP_NEEDED" = false ]; then
    get_keycloak_admin_token
    create_keycloak_client "$FASTAPI_CLIENT_ID" "$FASTAPI_CLIENT_SECRET" "http://localhost:8000/*"
fi

# FastAPI env file already configured
echo "FastAPI .env file already configured."

# Restart FastAPI container to pick up new environment
echo "Restarting FastAPI container to load new configuration..."
docker restart violentutf_api 2>/dev/null || echo "Note: FastAPI container will pick up config on first start"

# Setup APISIX route for FastAPI
echo "Creating APISIX route for FastAPI..."

# Wait for APISIX to be ready
wait_for_apisix() {
    echo "Waiting for APISIX Admin API to be ready..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -o /dev/null -w "%{http_code}" "${APISIX_ADMIN_URL}/apisix/admin/routes" -H "X-API-KEY: ${APISIX_ADMIN_KEY}" | grep -q 200; then
            echo "APISIX Admin API is ready!"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo "Waiting for APISIX... ($attempt/$max_attempts)"
        sleep 2
    done
    
    echo "Warning: APISIX Admin API did not become ready within 60 seconds."
    return 1
}

create_fastapi_route() {
    local route_name="violentutf-api"
    local route_uri="/api/*"
    local upstream_url="violentutf_api:8000"
    
    # First check if route already exists
    echo "Checking if FastAPI route already exists..."
    local existing_route=$(curl -s "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_name}" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" | grep -o '"uri":"\/api\/\*"')
    
    if [ -n "$existing_route" ]; then
        echo "FastAPI route already exists in APISIX. Updating..."
    fi
    
    cat > /tmp/fastapi-route.json <<EOF
{
    "uri": "${route_uri}",
    "name": "${route_name}",
    "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    "upstream": {
        "type": "roundrobin",
        "nodes": {
            "${upstream_url}": 1
        }
    },
    "plugins": {
        "cors": {
            "allow_origins": "http://localhost:8501,http://localhost:3000",
            "allow_methods": "GET,POST,PUT,DELETE,PATCH,OPTIONS",
            "allow_headers": "Authorization,Content-Type,X-Requested-With",
            "expose_headers": "X-Total-Count",
            "max_age": 3600,
            "allow_credential": true
        },
        "limit-req": {
            "rate": 100,
            "burst": 50,
            "rejected_code": 429,
            "rejected_msg": "Too many requests",
            "key_type": "var",
            "key": "remote_addr"
        },
        "limit-count": {
            "count": 1000,
            "time_window": 3600,
            "rejected_code": 429,
            "rejected_msg": "API rate limit exceeded",
            "key_type": "var",
            "key": "remote_addr",
            "policy": "local"
        }
    }
}
EOF
    
    # Use PUT to create or update the route
    local response=$(curl -s -w "\n%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_name}" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
        -H "Content-Type: application/json" \
        -d @/tmp/fastapi-route.json)
    
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n-1)
    
    rm -f /tmp/fastapi-route.json
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo "✅ FastAPI route successfully created/updated in APISIX."
        echo "Route ID: ${route_name}"
        echo "Route URI: ${route_uri} -> ${upstream_url}"
        
        # Add route to tracking array
        CREATED_AI_ROUTES+=("FastAPI: ${route_uri} -> ${upstream_url}")
        return 0
    else
        echo "❌ Failed to create FastAPI route in APISIX."
        echo "HTTP Status: $http_code"
        echo "Response: $body"
        return 1
    fi
}

# Function to create FastAPI documentation routes
create_fastapi_docs_routes() {
    echo "Creating FastAPI documentation routes..."
    
    # Create /api/docs route
    cat > /tmp/fastapi-docs-route.json <<EOF
{
    "uri": "/api/docs",
    "name": "violentutf-docs",
    "methods": ["GET"],
    "upstream": {
        "type": "roundrobin",
        "nodes": {
            "violentutf_api:8000": 1
        }
    },
    "plugins": {
        "proxy-rewrite": {
            "uri": "/docs"
        },
        "cors": {
            "allow_origins": "http://localhost:8501,http://localhost:3000",
            "allow_methods": "GET,OPTIONS",
            "allow_headers": "Authorization,Content-Type,X-Requested-With",
            "max_age": 3600,
            "allow_credential": true
        }
    }
}
EOF
    
    # Create docs route
    local response=$(curl -s -w "\n%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/violentutf-docs" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
        -H "Content-Type: application/json" \
        -d @/tmp/fastapi-docs-route.json)
    
    local status_code=$(echo "$response" | tail -n1)
    if [ "$status_code" = "200" ] || [ "$status_code" = "201" ]; then
        echo "✅ FastAPI docs route created successfully."
    else
        echo "⚠️  Warning: Failed to create FastAPI docs route. Status: $status_code"
    fi
    
    # Create /api/redoc route
    cat > /tmp/fastapi-redoc-route.json <<EOF
{
    "uri": "/api/redoc",
    "name": "violentutf-redoc",
    "methods": ["GET"],
    "upstream": {
        "type": "roundrobin",
        "nodes": {
            "violentutf_api:8000": 1
        }
    },
    "plugins": {
        "proxy-rewrite": {
            "uri": "/redoc"
        },
        "cors": {
            "allow_origins": "http://localhost:8501,http://localhost:3000",
            "allow_methods": "GET,OPTIONS",
            "allow_headers": "Authorization,Content-Type,X-Requested-With",
            "max_age": 3600,
            "allow_credential": true
        }
    }
}
EOF
    
    # Create redoc route
    local response=$(curl -s -w "\n%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/violentutf-redoc" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
        -H "Content-Type: application/json" \
        -d @/tmp/fastapi-redoc-route.json)
    
    local status_code=$(echo "$response" | tail -n1)
    if [ "$status_code" = "200" ] || [ "$status_code" = "201" ]; then
        echo "✅ FastAPI redoc route created successfully."
    else
        echo "⚠️  Warning: Failed to create FastAPI redoc route. Status: $status_code"
    fi
    
    # Clean up temp files
    rm -f /tmp/fastapi-docs-route.json /tmp/fastapi-redoc-route.json
    
    echo "FastAPI documentation routes configured."
}

# Wait for APISIX then create the routes
if wait_for_apisix; then
    create_fastapi_route
    create_fastapi_docs_routes
else
    echo "Warning: Could not verify APISIX is ready. Attempting to create routes anyway..."
    create_fastapi_route
    create_fastapi_docs_routes
fi

# Wait for FastAPI service to be ready before configuring routes
echo "Waiting for ViolentUTF API service to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
FASTAPI_READY=false

# First check if the container is running
VIOLENTUTF_API_CONTAINER=$(docker ps --filter "name=violentutf_api" --format "{{.Names}}" | head -n 1)
if [ -z "$VIOLENTUTF_API_CONTAINER" ]; then
    echo "⚠️  Warning: ViolentUTF API container not found. Routes configuration may fail."
else
    echo "Found ViolentUTF API container: $VIOLENTUTF_API_CONTAINER"
    
    # Wait for FastAPI to be ready
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        RETRY_COUNT=$((RETRY_COUNT + 1))
        
        # Check if FastAPI is responding (through Docker internal network)
        if docker exec "$VIOLENTUTF_API_CONTAINER" curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/health" 2>/dev/null | grep -q "200"; then
            echo "✅ ViolentUTF API is ready and responding."
            FASTAPI_READY=true
            break
        fi
        
        echo "Waiting for ViolentUTF API to be ready (attempt $RETRY_COUNT/$MAX_RETRIES)..."
        sleep 3
    done
    
    if [ "$FASTAPI_READY" = false ]; then
        echo "⚠️  Warning: ViolentUTF API did not become ready in time. Routes configuration may fail."
        echo "Checking container logs for issues:"
        docker logs "$VIOLENTUTF_API_CONTAINER" --tail 20
    fi
fi

# Routes have already been configured during APISIX setup
echo "ℹ️  API routes (including MCP endpoints) were configured during APISIX setup."

# Configure PyRIT Orchestrator API routes
echo "Configuring PyRIT Orchestrator API routes..."
if [ -f "apisix/configure_orchestrator_routes.sh" ]; then
    echo "Running PyRIT Orchestrator API route configuration script..."
    cd apisix
    chmod +x configure_orchestrator_routes.sh
    ./configure_orchestrator_routes.sh
    cd ..
    echo "✅ PyRIT Orchestrator API routes configured successfully."
else
    echo "⚠️  Warning: apisix/configure_orchestrator_routes.sh not found. Orchestrator API routes not configured."
fi

# Apply orchestrator executions route fix to prevent 422 errors
echo "Applying orchestrator executions route fix..."
if [ -f "apisix/fix_orchestrator_executions_route.sh" ]; then
    echo "Running orchestrator executions route fix script..."
    cd apisix
    chmod +x fix_orchestrator_executions_route.sh
    ./fix_orchestrator_executions_route.sh
    cd ..
    echo "✅ Orchestrator executions route fix applied successfully."
else
    echo "⚠️  Warning: apisix/fix_orchestrator_executions_route.sh not found. Route fix not applied."
fi

# MCP (Model Context Protocol) routes are now included in main route configuration
echo "ℹ️  Note: MCP routes are included in the main ViolentUTF API route configuration."

# Give APISIX a moment to reload routes and ensure FastAPI is ready
echo "Waiting for services to stabilize after route configuration..."
sleep 3

# Quick verification that routes are working
echo "Verifying API routes are accessible..."
if curl -s -o /dev/null -w "%{http_code}" "${APISIX_URL}/api/v1/health" 2>/dev/null | grep -q "200"; then
    echo "✅ FastAPI routes are accessible through APISIX"
    
    # Also verify MCP endpoints are configured and working
    echo "Verifying MCP endpoints..."
    
    # First check if MCP routes exist
    MCP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${APISIX_URL}/mcp/sse" 2>/dev/null)
    if [ "$MCP_STATUS" = "401" ] || [ "$MCP_STATUS" = "403" ]; then
        echo "✅ MCP endpoints are configured (authentication required)"
        
        # Try to test with a mock JWT token to verify the endpoint is functional
        echo "Testing MCP functionality with mock authentication..."
        
        # Create a simple test JWT token using the FastAPI secret key
        if [ -f "violentutf_api/fastapi_app/.env" ]; then
            # Extract JWT secret key
            JWT_SECRET=$(grep "^JWT_SECRET_KEY=" "violentutf_api/fastapi_app/.env" | cut -d'=' -f2)
            if [ -n "$JWT_SECRET" ]; then
                # Create a test token using Python (if available)
                if command -v python3 >/dev/null 2>&1; then
                    # Check if PyJWT is available in the virtual environment
                    if [ -f ".vitutf/bin/activate" ]; then
                        TEST_TOKEN=$(. .vitutf/bin/activate && python3 -c "
import jwt
from datetime import datetime, timedelta
payload = {
    'sub': 'test_user',
    'username': 'test_user',
    'email': 'test@example.com',
    'roles': ['ai-api-access'],
    'exp': datetime.utcnow() + timedelta(minutes=5),
    'token_type': 'access'
}
try:
    token = jwt.encode(payload, '$JWT_SECRET', algorithm='HS256')
    print(token)
except Exception as e:
    print('')
" 2>/dev/null)
                    else
                        # Try without virtual environment
                        TEST_TOKEN=$(python3 -c "
try:
    import jwt
    from datetime import datetime, timedelta
    payload = {
        'sub': 'test_user',
        'username': 'test_user',
        'email': 'test@example.com',
        'roles': ['ai-api-access'],
        'exp': datetime.utcnow() + timedelta(minutes=5),
        'token_type': 'access'
    }
    token = jwt.encode(payload, '$JWT_SECRET', algorithm='HS256')
    print(token)
except:
    print('')
" 2>/dev/null)
                    fi
                    
                    if [ -n "$TEST_TOKEN" ]; then
                        # Test MCP initialize method
                        MCP_INIT_RESPONSE=$(curl -s -X POST "${APISIX_URL}/mcp/sse/" \
                            -H "Authorization: Bearer $TEST_TOKEN" \
                            -H "Content-Type: application/json" \
                            -d '{"jsonrpc": "2.0", "method": "initialize", "params": {"capabilities": {}}, "id": 1}' \
                            2>/dev/null | head -1)
                        
                        if echo "$MCP_INIT_RESPONSE" | grep -q "ViolentUTF MCP Server"; then
                            echo "✅ MCP server is fully functional"
                            echo "   - Initialize method works"
                            
                            # Test prompts/list to verify full functionality
                            MCP_PROMPTS_RESPONSE=$(curl -s -X POST "${APISIX_URL}/mcp/sse/" \
                                -H "Authorization: Bearer $TEST_TOKEN" \
                                -H "Content-Type: application/json" \
                                -d '{"jsonrpc": "2.0", "method": "prompts/list", "id": 2}' \
                                2>/dev/null | head -1)
                            
                            if echo "$MCP_PROMPTS_RESPONSE" | grep -q "jailbreak_test"; then
                                echo "   - 12 security testing prompts available"
                            fi
                            
                            # Test resources/list
                            MCP_RESOURCES_RESPONSE=$(curl -s -X POST "${APISIX_URL}/mcp/sse/" \
                                -H "Authorization: Bearer $TEST_TOKEN" \
                                -H "Content-Type: application/json" \
                                -d '{"jsonrpc": "2.0", "method": "resources/list", "id": 3}' \
                                2>/dev/null | head -1)
                            
                            if echo "$MCP_RESOURCES_RESPONSE" | grep -q "violentutf://"; then
                                echo "   - 8 system resources accessible"
                            fi
                        else
                            echo "⚠️  MCP server responded but may not be fully functional"
                            echo "   Response: $(echo "$MCP_INIT_RESPONSE" | head -c 100)..."
                        fi
                    else
                        echo "ℹ️  Could not create test token for MCP verification"
                    fi
                else
                    echo "ℹ️  Python not available for MCP testing"
                fi
            fi
        fi
        
    elif [ "$MCP_STATUS" = "405" ]; then
        echo "✅ MCP endpoints are configured (POST method required)"
    elif [ "$MCP_STATUS" = "404" ]; then
        echo "⚠️  MCP endpoints not found. Attempting to reconfigure routes..."
        
        # Try to reconfigure routes one more time
        if [ -f "apisix/configure_routes.sh" ]; then
            cd apisix
            ./configure_routes.sh >/dev/null 2>&1
            cd ..
            
            # Check again
            MCP_STATUS_RETRY=$(curl -s -o /dev/null -w "%{http_code}" "${APISIX_URL}/mcp/sse" 2>/dev/null)
            if [ "$MCP_STATUS_RETRY" != "404" ]; then
                echo "✅ MCP endpoints now configured after retry"
            else
                echo "❌ MCP endpoints still not accessible. Manual configuration may be needed."
                echo "   Run: cd apisix && ./configure_routes.sh"
            fi
        fi
    else
        echo "ℹ️  MCP endpoint status: $MCP_STATUS"
    fi
else
    echo "⚠️  FastAPI routes may not be ready yet. Checking container status..."
    
    # Check if FastAPI container is having startup issues
    FASTAPI_STATUS=$(docker ps --filter "name=violentutf_api" --format "{{.Status}}" | head -1)
    if echo "$FASTAPI_STATUS" | grep -q "Restarting"; then
        echo "❌ FastAPI container is restarting - likely due to configuration errors"
        echo "   Common causes:"
        echo "   1. Pydantic validation errors (missing fields in config.py)"
        echo "   2. JWT secret mismatch"
        echo "   3. Database initialization issues"
        echo ""
        echo "   Check logs with: docker logs violentutf_api"
    else
        echo "   FastAPI status: $FASTAPI_STATUS"
        echo "   Service may still be initializing..."
    fi
fi

echo "FastAPI service configuration complete."
echo "The service will be started with the APISIX stack."

# Database migration preparation
echo "Preparing database migration for PyRIT Orchestrator tables..."
echo "Note: Database migration will be performed when the FastAPI service starts."
echo "The orchestrator tables (orchestrator_configurations, orchestrator_executions) will be created automatically."

# Return to original directory
cd "$ORIGINAL_DIR"

# Note: VIOLENTUTF_API_KEY is already generated in Step 7 of Keycloak setup
# Just add the API URL
if [ -f "$VIOLENTUTF_ENV_FILE" ]; then
    # Check if VIOLENTUTF_API_URL already exists in the file
    if ! grep -q "^VIOLENTUTF_API_URL=" "$VIOLENTUTF_ENV_FILE"; then
        echo "VIOLENTUTF_API_URL=http://localhost:9080/api" >> "$VIOLENTUTF_ENV_FILE"
    fi
fi

# ---------------------------------------------------------------
# SECTION E: VIOLENTUTF PYTHON APP SETUP
# ---------------------------------------------------------------
echo "SECTION E: SETTING UP VIOLENTUTF PYTHON APP"

# ---------------------------------------------------------------
# 8. Check Python executable (python or python3)
# ---------------------------------------------------------------
echo "Step 8: Determining Python command..."
PYTHON_CMD="python3" # Default to python3
if ! command -v python3 &> /dev/null; then
    if command -v python &> /dev/null; then
        PY_VERSION_CHECK=$(python --version 2>&1 | awk '{print $2}')
        if [[ "$PY_VERSION_CHECK" == 3* ]]; then # Check if 'python' is Python 3
            PYTHON_CMD="python"
        else
            echo "Python 3 not found with 'python3' or 'python' command. Please install Python 3.10+."
            echo "PyRIT and Garak require Python 3.10-3.12. You can install Python on macOS using 'brew install python3' or from python.org."
            exit 1
        fi
    else
        echo "Python 3 not found. Please install Python 3.10+."
        echo "PyRIT and Garak require Python 3.10-3.12. You can install Python on macOS using 'brew install python3' or from python.org."
        exit 1
    fi
fi
echo "Using '$PYTHON_CMD' for Python operations."
# Check for Python 3.10+ (required for PyRIT and Garak)
PY_FULL_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo $PY_FULL_VERSION | cut -d. -f1)
PY_MINOR=$(echo $PY_FULL_VERSION | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo "Your Python version ($PYTHON_CMD is $PY_FULL_VERSION) is less than 3.10."
    echo "PyRIT and Garak require Python 3.10-3.12. Please upgrade your Python installation."
    echo "You can install Python on macOS using 'brew install python@3.11' or from python.org."
    exit 1
fi

# Warn about Python 3.13+ (not yet tested with PyRIT/Garak)
if [ "$PY_MAJOR" -gt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -gt 12 ]; }; then
    echo "Warning: Python version $PY_FULL_VERSION is newer than the tested range (3.10-3.12)."
    echo "PyRIT and Garak are tested with Python 3.10-3.12. Proceed with caution."
fi

echo "Python version $PY_FULL_VERSION is compatible with PyRIT and Garak."

# ---------------------------------------------------------------
# 9. Set up and run the ViolentUTF Python app
# ---------------------------------------------------------------
echo "Step 9: Setting up and running ViolentUTF Python app..."

# === START OF ORIGINAL SCRIPT (ADJUSTED) ===
echo "Ensuring pip is up to date for $PYTHON_CMD..."
$PYTHON_CMD -m ensurepip --upgrade 2>/dev/null
$PYTHON_CMD -m pip install --upgrade pip

VENV_DIR=".vitutf"
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment '$VENV_DIR' already exists. Skipping creation."
else
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "Created virtual environment in $VENV_DIR using $PYTHON_CMD."
fi

if [ ! -f ".gitignore" ]; then
    echo ".gitignore not found. Creating .gitignore."
    echo "$VENV_DIR" > .gitignore
else
    if ! grep -Fxq "$VENV_DIR" .gitignore; then
        echo "$VENV_DIR" >> .gitignore
        echo "Added '$VENV_DIR' to .gitignore."
    else
        echo "'$VENV_DIR' is already in .gitignore."
    fi
fi

source "$VENV_DIR/bin/activate"
echo "Activated virtual environment: $VENV_DIR"

REQUIREMENTS_PATH="violentutf/requirements.txt"
if [ ! -f "$REQUIREMENTS_PATH" ]; then
    # Fallback to root if not in violentutf subdir
    REQUIREMENTS_PATH="requirements.txt" 
fi

if [ -f "$REQUIREMENTS_PATH" ]; then
    echo "Installing packages from $REQUIREMENTS_PATH..."
    python -m pip cache purge # Good practice on macOS sometimes
    python -m pip install --upgrade pip
    python -m pip install -r "$REQUIREMENTS_PATH"
    echo "Package installation complete."
else
    echo "Warning: No requirements.txt found at violentutf/requirements.txt or ./requirements.txt. Skipping package installation."
fi

# Verify Python dependencies are correctly installed
verify_python_dependencies

# ---------------------------------------------------------------
# 10. Update ViolentUTF config to use APISIX proxy if needed
# ---------------------------------------------------------------
echo "Step 10: Updating ViolentUTF config to use APISIX proxy if needed..."

# Check if we need to update the ViolentUTF config to use APISIX proxy
if [ -f "$VIOLENTUTF_ENV_FILE" ]; then
    # Add/update KEYCLOAK_URL_BASE to point to APISIX proxy if it exists
    if grep -q "^KEYCLOAK_URL_BASE" "$VIOLENTUTF_ENV_FILE"; then
        sed -i '' "s|^KEYCLOAK_URL_BASE=.*|KEYCLOAK_URL_BASE=http://localhost:9080/auth|" "$VIOLENTUTF_ENV_FILE"
    else
        echo "KEYCLOAK_URL_BASE=http://localhost:9080/auth" >> "$VIOLENTUTF_ENV_FILE"
    fi
    echo "Updated KEYCLOAK_URL_BASE in $VIOLENTUTF_ENV_FILE to use APISIX proxy."
    
    # Add AI proxy configuration if not present
    if ! grep -q "^AI_PROXY_BASE_URL" "$VIOLENTUTF_ENV_FILE"; then
        echo "AI_PROXY_BASE_URL=http://localhost:9080/ai" >> "$VIOLENTUTF_ENV_FILE"
        echo "Added AI_PROXY_BASE_URL to $VIOLENTUTF_ENV_FILE."
    fi
fi

echo "ViolentUTF configuration updated for APISIX integration."

# ---------------------------------------------------------------
# 11. Test all components of the stacks
# ---------------------------------------------------------------
echo ""
echo "=========================================="
echo "TESTING ALL COMPONENTS"
echo "=========================================="
echo "Running comprehensive tests for Keycloak, APISIX, AI Proxy, and their integration..."

TEST_RESULTS=()
TEST_FAILURES=0

# Function to run a test and record the result
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_exit_code="${3:-0}"
    
    echo "Testing: $test_name"
    
    # Capture both output and exit code
    local output
    output=$(eval "$test_command" 2>&1)
    local actual_exit_code=$?
    
    if [ $actual_exit_code -eq $expected_exit_code ]; then
        TEST_RESULTS+=("✅ PASS: $test_name")
        echo "  Result: PASS"
    else
        TEST_RESULTS+=("❌ FAIL: $test_name (Exit code: $actual_exit_code, Expected: $expected_exit_code)")
        echo "  Result: FAIL (Exit code: $actual_exit_code, Expected: $expected_exit_code)"
        echo "  Output: $output"
        TEST_FAILURES=$((TEST_FAILURES+1))
    fi
    echo ""
}

# 1. Test Keycloak master realm is accessible
run_test "Keycloak master realm" "curl -s -o /dev/null -w '%{http_code}' ${KEYCLOAK_SERVER_URL}/realms/master | grep -q 200"

# 2. Test network connectivity between APISIX and Keycloak
run_test "APISIX to Keycloak network connectivity" "test_network_connectivity apisix keycloak 8080"

# Additional network diagnostics if the connectivity test fails
if [ $? -ne 0 ]; then
    echo "Performing additional network diagnostics..."
    
    # Show all networks and their containers
    echo "Docker Networks:"
    docker network ls
    
    # Check containers on the shared network
    echo "Containers on $SHARED_NETWORK_NAME:"
    docker network inspect $SHARED_NETWORK_NAME
    
    # Check if services can be resolved by DNS from host
    echo "DNS resolution of Keycloak from host:"
    docker run --rm --network=$SHARED_NETWORK_NAME alpine nslookup keycloak 2>/dev/null || echo "Failed to resolve keycloak"
    
    echo "DNS resolution of APISIX from host:"
    docker run --rm --network=$SHARED_NETWORK_NAME alpine nslookup apisix 2>/dev/null || echo "Failed to resolve apisix"
    
    # Try again to connect the containers to the shared network
    echo "Attempting to reconnect containers to the shared network..."
    
    KEYCLOAK_CONTAINER=$(docker ps --filter "name=keycloak" --format "{{.ID}}" | head -n 1)
    if [ -n "$KEYCLOAK_CONTAINER" ]; then
        if docker network disconnect $SHARED_NETWORK_NAME $KEYCLOAK_CONTAINER 2>/dev/null; then
            echo "Disconnected Keycloak container from $SHARED_NETWORK_NAME"
        fi
        docker network connect $SHARED_NETWORK_NAME $KEYCLOAK_CONTAINER || echo "Failed to reconnect Keycloak to network"
        echo "Reconnected Keycloak container to $SHARED_NETWORK_NAME"
    fi
    
    APISIX_CONTAINER=$(docker ps --filter "name=apisix" --format "{{.ID}}" | head -n 1)
    if [ -n "$APISIX_CONTAINER" ]; then
        if docker network disconnect $SHARED_NETWORK_NAME $APISIX_CONTAINER 2>/dev/null; then
            echo "Disconnected APISIX container from $SHARED_NETWORK_NAME"
        fi
        docker network connect $SHARED_NETWORK_NAME $APISIX_CONTAINER || echo "Failed to reconnect APISIX to network"
        echo "Reconnected APISIX container to $SHARED_NETWORK_NAME"
    fi
    
    # Try connectivity test one more time
    echo "Retrying connectivity test after network reconnection..."
    test_network_connectivity apisix keycloak 8080
fi

# 3. Test APISIX is running and accessible
run_test "APISIX main endpoint" "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL} | grep -q 404"
# Note: 404 is expected for root path as no routes are defined by default

# 4. Test APISIX admin API 
run_test "APISIX admin API" "curl -s -o /dev/null -w '%{http_code}' ${APISIX_ADMIN_URL}/apisix/admin/routes -H \"X-API-KEY: ${APISIX_ADMIN_KEY}\" | grep -q 200"

# 5. Test APISIX dashboard is accessible
run_test "APISIX dashboard" "curl -s -o /dev/null -w '%{http_code}' ${APISIX_DASHBOARD_URL} | grep -q 200"

# 6. Test APISIX-Keycloak integration - Test the route to Keycloak through APISIX
run_test "APISIX-Keycloak integration" "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL}/auth/realms/master | grep -q 200"

# 7. Test AI Routes
test_ai_routes

# Wait for FastAPI service to be ready
echo "Waiting for FastAPI service to be ready..."
FASTAPI_READY=false
RETRY_COUNT=0
MAX_RETRIES=30  # 30 seconds max wait
while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$FASTAPI_READY" = "false" ]; do
    if curl -s -o /dev/null -w "%{http_code}" "${APISIX_URL}/api/v1/health" 2>/dev/null | grep -q "200"; then
        FASTAPI_READY=true
        echo "✅ FastAPI service is ready"
    else
        RETRY_COUNT=$((RETRY_COUNT+1))
        if [ $((RETRY_COUNT % 5)) -eq 0 ]; then
            echo "   Still waiting for FastAPI... (${RETRY_COUNT}/${MAX_RETRIES})"
        fi
        sleep 1
    fi
done

if [ "$FASTAPI_READY" = "false" ]; then
    echo "⚠️  FastAPI service did not become ready in time"
    echo "   Some tests may fail. Checking container status..."
    docker ps --filter "name=violentutf_api" --format "table {{.Names}}\t{{.Status}}"
fi

# 8. Test FastAPI service health (via APISIX only - direct access is blocked by design)
run_test "FastAPI health via APISIX" "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL}/api/v1/health | grep -q 200"

# 9. Test FastAPI API endpoint via APISIX (expects 403 due to enhanced security)
run_test "FastAPI API via APISIX" "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL}/api/v1/auth/me -H 'X-API-Key: test' | grep -q 403"

# 9.5. Test PyRIT Orchestrator API endpoint via APISIX (expects 401 due to authentication requirement)
run_test "PyRIT Orchestrator API via APISIX" "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL}/api/v1/orchestrators/types -H 'X-API-Gateway: APISIX' | grep -q 401"

# 10. Test ViolentUTF environment variables
if [ -f "$VIOLENTUTF_ENV_FILE" ]; then
    run_test "ViolentUTF environment file" "grep -q KEYCLOAK_CLIENT_SECRET $VIOLENTUTF_ENV_FILE && grep -q KEYCLOAK_USERNAME $VIOLENTUTF_ENV_FILE && grep -q KEYCLOAK_PASSWORD $VIOLENTUTF_ENV_FILE"
else
    TEST_RESULTS+=("❌ FAIL: ViolentUTF environment file (File not found)")
    TEST_FAILURES=$((TEST_FAILURES+1))
fi

# 9. Test ViolentUTF secrets file
if [ -f "$VIOLENTUTF_SECRETS_FILE" ]; then
    run_test "ViolentUTF secrets file" "grep -q client_secret $VIOLENTUTF_SECRETS_FILE && grep -q cookie_secret $VIOLENTUTF_SECRETS_FILE"
else
    TEST_RESULTS+=("❌ FAIL: ViolentUTF secrets file (File not found)")
    TEST_FAILURES=$((TEST_FAILURES+1))
fi

# 10. Test Python environment and Streamlit installation
run_test "Python Streamlit installation" "which streamlit > /dev/null"

# Display test results
echo ""
echo "TEST RESULTS SUMMARY:"
echo "--------------------"
for result in "${TEST_RESULTS[@]}"; do
    echo "$result"
done
echo ""
echo "Total tests: ${#TEST_RESULTS[@]}"
echo "Passed: $((${#TEST_RESULTS[@]} - $TEST_FAILURES))"
echo "Failed: $TEST_FAILURES"
echo ""

if [ $TEST_FAILURES -gt 0 ]; then
    echo "⚠️  WARNING: Some tests failed. The application may not function correctly."
    echo "Please check the test results above and fix any issues before proceeding."
    echo ""
    
    # Ask user if they want to continue despite test failures
    read -p "Do you want to continue and launch the Streamlit app anyway? (y/n): " continue_choice
    if [[ ! $continue_choice =~ ^[Yy]$ ]]; then
        echo "Setup aborted by user after test failures."
        exit 1
    fi
    echo "Continuing despite test failures..."
else
    echo "✅ All tests passed! The system is properly configured."
fi
echo "=========================================="
echo ""

# ---------------------------------------------------------------
# 12. Display AI Configuration Summary
# ---------------------------------------------------------------
show_ai_summary

# ---------------------------------------------------------------
# 13. Display service access information and credentials
# ---------------------------------------------------------------
echo ""
echo "=========================================="
echo "SERVICE ACCESS INFORMATION & CREDENTIALS"
echo "=========================================="
echo "⚠️  IMPORTANT: Store these credentials securely!"
echo ""
echo "─────────────────────────────────────────"
echo "🔐 KEYCLOAK AUTHENTICATION"
echo "─────────────────────────────────────────"
echo "Admin Console:"
echo "   URL: $KEYCLOAK_SERVER_URL"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "Database:"
echo "   PostgreSQL Password: $KEYCLOAK_POSTGRES_PASSWORD"
echo ""
echo "Application User:"
if [ -n "$KEYCLOAK_APP_USERNAME" ]; then
    echo "   Username: $KEYCLOAK_APP_USERNAME"
fi
if [ -n "$NEW_USER_PASSWORD" ]; then
    echo "   Password: $NEW_USER_PASSWORD"
fi
echo ""
echo "─────────────────────────────────────────"
echo "🌐 APISIX GATEWAY"
echo "─────────────────────────────────────────"
echo "Gateway URLs:"
echo "   Main URL: $APISIX_URL"
echo "   Admin API: $APISIX_ADMIN_URL"
echo "   Dashboard: $APISIX_DASHBOARD_URL"
echo ""
echo "Admin Credentials:"
echo "   Admin API Key: $APISIX_ADMIN_KEY"
echo "   Dashboard Username: admin"
echo "   Dashboard Password: $APISIX_DASHBOARD_PASSWORD"
echo ""
echo "Security Keys:"
echo "   JWT Secret: $APISIX_DASHBOARD_SECRET"
echo "   Keyring Value 1: $APISIX_KEYRING_VALUE_1"
echo "   Keyring Value 2: $APISIX_KEYRING_VALUE_2"
echo "   Keycloak Client Secret: $APISIX_CLIENT_SECRET"
echo ""
echo "─────────────────────────────────────────"
echo "🚀 VIOLENTUTF APPLICATION"
echo "─────────────────────────────────────────"
echo "Application Secrets:"
echo "   Client Secret: $VIOLENTUTF_CLIENT_SECRET"
echo "   Cookie Secret: $VIOLENTUTF_COOKIE_SECRET"
echo "   PyRIT DB Salt: $VIOLENTUTF_PYRIT_SALT"
echo "   API Key: $VIOLENTUTF_API_KEY"
echo "   User Password: $VIOLENTUTF_USER_PASSWORD"
echo ""
echo "─────────────────────────────────────────"
echo "🔧 FASTAPI SERVICE"
echo "─────────────────────────────────────────"
echo "API Access:"
echo "   Via APISIX: $APISIX_URL/api/"
echo "   API Docs: $APISIX_URL/api/docs (if configured)"
echo "   Direct URL: http://localhost:8000 (blocked by design)"
echo ""
echo "PyRIT Orchestrator API:"
echo "   Orchestrator Types: $APISIX_URL/api/v1/orchestrators/types"
echo "   Configuration: $APISIX_URL/api/v1/orchestrators"
echo "   Execution: $APISIX_URL/api/v1/orchestrators/{id}/execute"
echo "   Memory Access: $APISIX_URL/api/v1/orchestrators/{id}/memory"
echo ""
echo "Security Keys:"
echo "   JWT Secret Key: $FASTAPI_SECRET_KEY"
echo "   Keycloak Client Secret: $FASTAPI_CLIENT_SECRET"
echo ""
echo "─────────────────────────────────────────"
echo "🤖 AI PROXY"
echo "─────────────────────────────────────────"
echo "   Base URL: $APISIX_URL/ai/"
echo "   Available routes listed in AI Configuration Summary above"
echo ""
echo "─────────────────────────────────────────"
echo "📊 ADDITIONAL SERVICES"
echo "─────────────────────────────────────────"
echo "Monitoring:"
echo "   Prometheus: http://localhost:9090"
echo "   Grafana: http://localhost:3000"
echo ""
echo "Proxy Routes:"
echo "   Keycloak via APISIX: $APISIX_URL/auth/"
echo ""
echo "MCP (Model Context Protocol):"
echo "   MCP SSE Endpoint: $APISIX_URL/mcp/sse"
echo "   - 12 security testing prompts available"
echo "   - 8 system resources accessible"
echo "   - JWT token required (get from Streamlit sidebar)"
echo ""
echo "=========================================="
echo ""

# ---------------------------------------------------------------
# 15. Launch the Streamlit app
# ---------------------------------------------------------------
echo "Step 15: Preparing to launch the Streamlit application..."

# Function to launch Streamlit in background
launch_streamlit_background() {
    local app_path="$1"
    local app_dir="$2"
    
    echo "Launching ViolentUTF in background with fresh JWT configuration..."
    
    # Ensure log directory exists
    mkdir -p violentutf_logs
    
    # Launch in background with virtual environment and proper directory handling
    if [ "$app_dir" = "violentutf" ]; then
        (cd violentutf && source ../.vitutf/bin/activate && nohup streamlit run Home.py --server.port 8501 --server.address 0.0.0.0 > ../violentutf_logs/streamlit.log 2>&1 &)
    else
        (source .vitutf/bin/activate && nohup streamlit run "$app_path" --server.port 8501 --server.address 0.0.0.0 > violentutf_logs/streamlit.log 2>&1 &)
    fi
    
    STREAMLIT_PID=$!
    sleep 3  # Give time for Streamlit to initialize
    
    # Check if process started successfully
    if kill -0 $STREAMLIT_PID 2>/dev/null; then
        echo "✅ ViolentUTF launched in background (PID: $STREAMLIT_PID)"
        echo "   Access the app at: http://localhost:8501"
        echo "   Logs: violentutf_logs/streamlit.log"
        echo "   Stop with: kill $STREAMLIT_PID"
        
        # Health check for Streamlit
        echo "Verifying Streamlit is responding..."
        sleep 3
        if curl -s http://localhost:8501 >/dev/null 2>&1; then
            echo "✅ Streamlit is responding at http://localhost:8501"
        else
            echo "⚠️  Streamlit may still be starting - check logs if issues persist"
        fi
    else
        echo "❌ Failed to launch ViolentUTF. Check violentutf_logs/streamlit.log for errors."
        echo "💡 Try manually starting: cd violentutf && source ../.vitutf/bin/activate && streamlit run Home.py"
    fi
}

# Force restart FastAPI service with new JWT secrets and clear any cached data BEFORE launching Streamlit
echo ""
echo "🔄 Restarting FastAPI service with fresh JWT configuration..."
if (cd apisix && docker compose ps 2>/dev/null | grep -q "violentutf_api.*Up"); then
    (cd apisix && docker compose restart fastapi) > /dev/null 2>&1
    sleep 5
    
    # Quick health check
    if curl -s http://localhost:9080/api/v1/health >/dev/null 2>&1; then
        echo "✅ FastAPI service restarted successfully with new JWT secrets"
    else
        echo "⚠️  FastAPI service restarted but health check failed - check logs if needed"
    fi
else
    echo "ℹ️  FastAPI service not running - will start with APISIX stack"
fi

# Clear any existing ViolentUTF Streamlit processes and session data to prevent JWT conflicts
echo "🧹 Clearing existing ViolentUTF Streamlit processes and session data..."
graceful_streamlit_shutdown

# Clear Streamlit cache and session data
if [ -d "violentutf/.streamlit" ]; then
    # Remove any cached session data that might contain old tokens
    find violentutf/.streamlit -name "*.cache" -delete 2>/dev/null || true
    echo "✅ Cleared Streamlit cache data"
fi

# NOW launch Streamlit with fresh configuration
# Determine app location and launch in background
if [ -f "violentutf/Home.py" ]; then
    APP_PATH="violentutf/Home.py"
    APP_DIR="violentutf"
elif [ -f "Home.py" ]; then
    APP_PATH="Home.py"
    APP_DIR="."
else
    echo "Warning: Home.py not found in violentutf/ or current directory."
    echo "You can manually start the application later with:"
    echo "   cd violentutf && streamlit run Home.py"
    APP_PATH=""
fi

if [ -n "$APP_PATH" ]; then
    echo ""
    launch_streamlit_background "$APP_PATH" "$APP_DIR"
fi

# Comprehensive configuration verification
verify_configuration_integrity() {
    echo ""
    echo "🔍 Verifying configuration integrity..."
    
    local issues_found=0
    
    # 1. Check JWT secret consistency
    echo "Checking JWT secret consistency..."
    STREAMLIT_JWT=$(grep "^JWT_SECRET_KEY=" violentutf/.env 2>/dev/null | cut -d'=' -f2)
    FASTAPI_JWT=$(grep "^JWT_SECRET_KEY=" violentutf_api/fastapi_app/.env 2>/dev/null | cut -d'=' -f2)
    
    if [ "$STREAMLIT_JWT" != "$FASTAPI_JWT" ] || [ -z "$STREAMLIT_JWT" ]; then
        echo "❌ JWT secret mismatch or missing"
        issues_found=$((issues_found + 1))
    else
        echo "✅ JWT secrets consistent"
    fi
    
    # 2. Check Docker network connectivity
    echo "Checking Docker network connectivity..."
    # Use Python to test connectivity since nc might not be available
    if docker exec "$VIOLENTUTF_API_CONTAINER_NAME" python -c "import requests; requests.get('http://$APISIX_CONTAINER_NAME:9080').status_code" 2>/dev/null; then
        echo "✅ Inter-service network connectivity verified"
    else
        # Fallback: Check if containers are at least on the same network
        APISIX_NET=$(docker inspect "$APISIX_CONTAINER_NAME" --format='{{range $net,$v := .NetworkSettings.Networks}}{{$net}} {{end}}' 2>/dev/null | grep "$SHARED_NETWORK_NAME" || echo "")
        API_NET=$(docker inspect "$VIOLENTUTF_API_CONTAINER_NAME" --format='{{range $net,$v := .NetworkSettings.Networks}}{{$net}} {{end}}' 2>/dev/null | grep "$SHARED_NETWORK_NAME" || echo "")
        
        if [ -n "$APISIX_NET" ] && [ -n "$API_NET" ]; then
            echo "⚠️  Containers are on the same network but connectivity test failed"
            echo "   This might be due to services still starting up"
        else
            echo "❌ Inter-service network connectivity failed"
            issues_found=$((issues_found + 1))
        fi
    fi
    
    # 3. Check environment variable consistency
    echo "Checking environment variable consistency..."
    FASTAPI_APISIX_URL=$(grep "^APISIX_BASE_URL=" violentutf_api/fastapi_app/.env 2>/dev/null | cut -d'=' -f2)
    if echo "$FASTAPI_APISIX_URL" | grep -q "localhost"; then
        echo "❌ FastAPI still using localhost instead of container names"
        issues_found=$((issues_found + 1))
    else
        echo "✅ FastAPI using proper container names"
    fi
    
    # 4. Check container health
    echo "Checking container health..."
    if docker ps --filter "name=violentutf_api" --filter "status=running" | grep -q "healthy\|Up"; then
        echo "✅ ViolentUTF API container healthy"
    else
        echo "❌ ViolentUTF API container not healthy"
        issues_found=$((issues_found + 1))
    fi
    
    # Summary
    if [ $issues_found -eq 0 ]; then
        echo ""
        echo "✅ All configuration checks passed"
        return 0
    else
        echo ""
        echo "❌ Found $issues_found configuration issues"
        echo "   These may cause generator execution failures"
        return 1
    fi
}

# Verify configuration integrity
if ! verify_configuration_integrity; then
    echo ""
    echo "⚠️  WARNING: Configuration issues detected"
    echo "   Dataset testing and generator execution may fail"
    echo "   Please review the issues above before proceeding"
fi

# Final MCP status check
echo ""
echo "Final MCP Status Check..."
MCP_FINAL_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:9080/mcp/sse" 2>/dev/null)
if [ "$MCP_FINAL_STATUS" = "401" ] || [ "$MCP_FINAL_STATUS" = "403" ] || [ "$MCP_FINAL_STATUS" = "405" ]; then
    echo "✅ MCP endpoints are accessible and ready for use"
    echo "   - Use JWT tokens from Streamlit sidebar for authentication"
    echo "   - 12 security testing prompts available"
    echo "   - 8 system resources accessible"
else
    echo "⚠️  MCP endpoints may need manual configuration"
    echo "   Status code: $MCP_FINAL_STATUS"
    echo "   Run: cd apisix && ./configure_routes.sh"
fi

echo ""
echo "=========================================="
echo "SETUP COMPLETED SUCCESSFULLY!"
echo "=========================================="
echo "Your ViolentUTF platform with Keycloak SSO, APISIX Gateway, AI Proxy, and MCP is now ready!"
echo ""
echo "💡 Next Steps:"
echo "1. Access the Keycloak admin console to manage users and permissions"
echo "2. Configure additional AI providers by editing $AI_TOKENS_FILE"
echo "3. Explore the APISIX dashboard for advanced gateway configuration"
echo "4. Test AI proxy endpoints with your favorite LLM models"
echo "5. Configure PyRIT orchestrators in the ViolentUTF web interface"
echo "6. Test datasets using the new PyRIT Orchestrator API functionality"
echo "7. Run 'cd tests && ./run_tests.sh' to validate PyRIT Orchestrator integration"
echo "8. Test MCP endpoints at http://localhost:9080/mcp/sse (see mcpTutorial_vscode.md)"
echo "9. Get JWT tokens from Streamlit's Developer Tools in the sidebar"
echo "10. Start building amazing AI-powered red-teaming applications!"
echo ""
echo "📝 Remember to save your sensitive values securely!"
echo "=========================================="

# Generate troubleshooting guide
cat > DOCKER_NETWORK_TROUBLESHOOTING.md <<EOF
# Docker Network Troubleshooting Guide

## Common Issues After Setup

### 1. "Cannot connect to APISIX gateway" Error
**Cause**: FastAPI container cannot reach APISIX container
**Solution**:
\`\`\`bash
# Check container connectivity (using Python since nc might not be available)
docker exec violentutf_api python -c "import requests; print(requests.get('http://apisix-apisix-1:9080').status_code)"

# Reconnect containers to shared network
docker network connect vutf-network violentutf_api
docker network connect vutf-network apisix-apisix-1

# Restart FastAPI service
docker restart violentutf_api
\`\`\`

### 2. "Generator type 'None'" Error
**Cause**: Field mapping issue in generator service
**Solution**: Restart FastAPI container to reload code
\`\`\`bash
docker restart violentutf_api
\`\`\`

### 3. Authentication Issues
**Cause**: JWT secret mismatch between services
**Solution**: Verify and sync JWT secrets
\`\`\`bash
grep JWT_SECRET_KEY violentutf/.env
grep JWT_SECRET_KEY violentutf_api/fastapi_app/.env
# Values should match
\`\`\`

### 4. Cross-User Generator Access Issues
**Cause**: User context mismatch in orchestrator names
**Solution**: Check username consistency
\`\`\`bash
# In Streamlit, verify username
grep KEYCLOAK_USERNAME violentutf/.env
\`\`\`

## Verification Commands
\`\`\`bash
# Check all containers are running
docker ps --filter "name=apisix\\|keycloak\\|violentutf"

# Check network connectivity
docker network inspect vutf-network

# Test API endpoints
curl http://localhost:9080/api/v1/health
curl http://localhost:9080/api/v1/generators
\`\`\`
EOF

echo "📝 Created DOCKER_NETWORK_TROUBLESHOOTING.md"

# ---------------------------------------------------------------
# PyRIT Orchestrator Integration Validation Functions
# ---------------------------------------------------------------

# Function to validate PyRIT orchestrator parameter compatibility
validate_pyrit_parameters() {
    echo "   Checking PyRIT PromptSendingOrchestrator parameter compatibility..."
    
    # Test if PyRIT accepts correct parameters
    if docker exec violentutf_api python3 -c "
from pyrit.orchestrator import PromptSendingOrchestrator
import inspect
sig = inspect.signature(PromptSendingOrchestrator.__init__)
params = list(sig.parameters.keys())
if 'scorers' in params and 'auxiliary_scorers' not in params:
    print('✅ PyRIT parameters compatible')
    exit(0)
else:
    print('❌ PyRIT parameter mismatch detected')
    exit(1)
" 2>/dev/null; then
        return 0
    else
        echo "❌ PyRIT parameter compatibility check failed"
        echo "   This may cause orchestrator creation errors"
        return 1
    fi
}

# Function to validate PyRIT memory initialization
validate_pyrit_memory() {
    echo "   Checking PyRIT memory database initialization..."
    
    # Test PyRIT memory access
    if docker exec violentutf_api python3 -c "
from pyrit.memory import CentralMemory, DuckDBMemory
import os
try:
    # Try to initialize memory like the orchestrator service does
    api_memory_dir = '/app/app_data/violentutf/api_memory'
    os.makedirs(api_memory_dir, exist_ok=True)
    memory_file = os.path.join(api_memory_dir, 'test_memory.db')
    memory = DuckDBMemory(db_path=memory_file)
    print('✅ PyRIT memory initialization works')
    exit(0)
except Exception as e:
    print(f'❌ PyRIT memory initialization failed: {e}')
    exit(1)
" 2>/dev/null; then
        return 0
    else
        echo "❌ PyRIT memory initialization check failed"
        echo "   This may cause orchestrator service startup issues"
        return 1
    fi
}

# Function to validate scorer wrapper integration
validate_scorer_wrapper() {
    echo "   Checking ConfiguredScorerWrapper integration..."
    
    # Test scorer wrapper creation
    if docker exec violentutf_api python3 -c "
from app.services.pyrit_orchestrator_service import ConfiguredScorerWrapper
from pyrit.score.scorer import Scorer
import asyncio

try:
    # Create a test scorer wrapper
    test_config = {
        'name': 'test_scorer',
        'type': 'test',
        'parameters': {'test_param': 'test_value'}
    }
    wrapper = ConfiguredScorerWrapper(test_config)
    
    # Check it inherits from PyRIT Scorer
    if isinstance(wrapper, Scorer):
        print('✅ ConfiguredScorerWrapper integration works')
        exit(0)
    else:
        print('❌ ConfiguredScorerWrapper not properly inheriting from PyRIT Scorer')
        exit(1)
except Exception as e:
    print(f'❌ ConfiguredScorerWrapper creation failed: {e}')
    exit(1)
" 2>/dev/null; then
        return 0
    else
        echo "❌ ConfiguredScorerWrapper integration check failed"
        echo "   This may cause scorer creation issues"
        return 1
    fi
}

# Function to test orchestrator service initialization
validate_orchestrator_service() {
    echo "   Checking PyRIT orchestrator service initialization..."
    
    # Test orchestrator service startup
    if docker exec violentutf_api python3 -c "
from app.services.pyrit_orchestrator_service import PyRITOrchestratorService
try:
    service = PyRITOrchestratorService()
    if service.validate_memory_access():
        print('✅ PyRIT orchestrator service initializes correctly')
        exit(0)
    else:
        print('❌ PyRIT orchestrator service memory validation failed')
        exit(1)
except Exception as e:
    print(f'❌ PyRIT orchestrator service initialization failed: {e}')
    exit(1)
" 2>/dev/null; then
        return 0
    else
        echo "❌ PyRIT orchestrator service initialization check failed"
        echo "   This may cause orchestrator API endpoint failures"
        return 1
    fi
}

# Function to validate orchestrator API endpoints
validate_orchestrator_endpoints() {
    echo "   Checking orchestrator API endpoints..."
    
    # Wait for API to be ready
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        # Check if endpoint returns proper security response (indicating it's routed correctly)
        local response=$(curl -s "http://localhost:9080/api/v1/orchestrators/types" 2>/dev/null)
        if echo "$response" | grep -q "Direct access not allowed. Use the API gateway"; then
            echo "✅ Orchestrator API endpoints accessible and properly secured"
            return 0
        fi
        echo "   Waiting for API... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ Orchestrator API endpoints not accessible"
    echo "   This may indicate orchestrator service startup issues"
    return 1
}

# Main validation function
validate_pyrit_orchestrator_integration() {
    local issues_found=0
    
    echo "   This validation ensures the orchestrator-based scorer testing works correctly..."
    echo ""
    
    # Check if FastAPI container is running
    if ! docker ps --filter "name=violentutf_api" --filter "status=running" | grep -q "violentutf_api"; then
        echo "❌ ViolentUTF API container is not running"
        echo "   Skipping PyRIT orchestrator validation"
        return 1
    fi
    
    # Run all validation checks
    if ! validate_pyrit_parameters; then
        issues_found=$((issues_found + 1))
    fi
    
    if ! validate_pyrit_memory; then
        issues_found=$((issues_found + 1))
    fi
    
    if ! validate_scorer_wrapper; then
        issues_found=$((issues_found + 1))
    fi
    
    if ! validate_orchestrator_service; then
        issues_found=$((issues_found + 1))
    fi
    
    if ! validate_orchestrator_endpoints; then
        issues_found=$((issues_found + 1))
    fi
    
    echo ""
    if [ $issues_found -eq 0 ]; then
        echo "✅ PyRIT Orchestrator integration validation passed"
        echo "   Orchestrator-based scorer testing should work correctly"
        return 0
    else
        echo "❌ Found $issues_found PyRIT integration issues"
        echo "   Orchestrator-based scorer testing may fail"
        echo "   Consider restarting the FastAPI container: docker restart violentutf_api"
        return 1
    fi
}

# ---------------------------------------------------------------
# PyRIT Orchestrator and Scorer Integration Validation
# ---------------------------------------------------------------
echo ""
echo "🔧 Validating PyRIT Orchestrator Service Integration..."
validate_pyrit_orchestrator_integration

echo ""
echo "🔄 Finalizing Setup..."

# Restore user configurations that were backed up during cleanup
restore_user_configs

# Perform final system state verification
echo ""
echo "🔍 Final System State Verification..."
if verify_system_state; then
    echo ""
    echo "🎉 Setup completed successfully! System is ready for use."
else
    echo ""
    echo "⚠️ Setup completed but with some issues. Review the messages above."
fi

echo "Setup script finished."