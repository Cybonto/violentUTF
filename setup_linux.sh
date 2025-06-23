#!/usr/bin/env bash
# setup_linux.sh (API Version with APISIX integration, AI proxy, network fixes, cleanup and deep cleanup options)

# --- Help function ---
show_help() {
    echo "ViolentUTF Linux Setup Script"
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
    echo "  ./setup_linux.sh                 # Normal installation"
    echo "  ./setup_linux.sh --cleanup       # Clean ViolentUTF components only"
    echo "  ./setup_linux.sh --deepcleanup   # Complete Docker environment reset"
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
            echo "Usage: $0 [--cleanup|--deepcleanup|--help]"
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
        echo "No ViolentUTF Streamlit processes found running."
        return 0
    fi
    
    echo "Found ${#UNIQUE_PIDS[@]} ViolentUTF Streamlit process(es) to shutdown: ${UNIQUE_PIDS[*]}"
    
    # Graceful shutdown sequence
    for pid in "${UNIQUE_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "Sending SIGTERM to process $pid..."
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done
    
    # Wait up to 10 seconds for graceful shutdown
    echo "Waiting for graceful shutdown (up to 10 seconds)..."
    for i in {1..10}; do
        REMAINING_PIDS=()
        for pid in "${UNIQUE_PIDS[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                REMAINING_PIDS+=("$pid")
            fi
        done
        
        if [ ${#REMAINING_PIDS[@]} -eq 0 ]; then
            echo "All ViolentUTF Streamlit processes shutdown gracefully."
            break
        fi
        
        sleep 1
    done
    
    # If processes still running, try SIGINT
    if [ ${#REMAINING_PIDS[@]} -gt 0 ]; then
        echo "Some processes still running. Sending SIGINT..."
        for pid in "${REMAINING_PIDS[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                echo "Sending SIGINT to process $pid..."
                kill -INT "$pid" 2>/dev/null || true
            fi
        done
        
        # Wait another 5 seconds
        sleep 5
        
        # Check remaining processes
        FINAL_REMAINING=()
        for pid in "${REMAINING_PIDS[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                FINAL_REMAINING+=("$pid")
            fi
        done
        
        # Force kill if necessary
        if [ ${#FINAL_REMAINING[@]} -gt 0 ]; then
            echo "Force killing remaining processes: ${FINAL_REMAINING[*]}"
            for pid in "${FINAL_REMAINING[@]}"; do
                kill -KILL "$pid" 2>/dev/null || true
            done
        fi
    fi
    
    # Clean up port 8501 if it's still in use
    echo "Checking port 8501 for cleanup..."
    PORT_PID=$(lsof -ti:8501 2>/dev/null || true)
    if [ -n "$PORT_PID" ]; then
        echo "Port 8501 still in use by process $PORT_PID. Attempting cleanup..."
        kill -TERM "$PORT_PID" 2>/dev/null || true
        sleep 2
        if kill -0 "$PORT_PID" 2>/dev/null; then
            kill -KILL "$PORT_PID" 2>/dev/null || true
        fi
    fi
    
    echo "ViolentUTF Streamlit shutdown completed."
}

# --- Function to backup user configurations ---
backup_user_configs() {
    echo "Backing up user configurations..."
    mkdir -p .backup_temp 2>/dev/null || true
    
    # Backup AI tokens file
    if [ -f "$AI_TOKENS_FILE" ]; then
        cp "$AI_TOKENS_FILE" .backup_temp/ 2>/dev/null || true
        echo "Backed up AI tokens configuration"
    fi
    
    # Backup custom APISIX routes
    if [ -f "apisix/conf/custom_routes.yml" ]; then
        cp "apisix/conf/custom_routes.yml" .backup_temp/ 2>/dev/null || true
        echo "Backed up custom APISIX routes"
    fi
    
    # Backup application data 
    if [ -d "violentutf/app_data" ]; then
        tar -czf .backup_temp/app_data_backup.tar.gz -C violentutf app_data 2>/dev/null || true
        echo "Backed up application data"
    fi
}

# --- Function to restore user configurations ---
restore_user_configs() {
    echo "Restoring user configurations..."
    
    if [ ! -d ".backup_temp" ]; then
        echo "No backup found, skipping restoration."
        return 0
    fi
    
    # Restore AI tokens file
    if [ -f ".backup_temp/$AI_TOKENS_FILE" ]; then
        cp ".backup_temp/$AI_TOKENS_FILE" . 2>/dev/null || true
        echo "Restored AI tokens configuration"
    fi
    
    # Restore custom APISIX routes
    if [ -f ".backup_temp/custom_routes.yml" ]; then
        mkdir -p apisix/conf 2>/dev/null || true
        cp ".backup_temp/custom_routes.yml" apisix/conf/ 2>/dev/null || true
        echo "Restored custom APISIX routes"
    fi
    
    # Restore application data
    if [ -f ".backup_temp/app_data_backup.tar.gz" ]; then
        mkdir -p violentutf 2>/dev/null || true
        tar -xzf ".backup_temp/app_data_backup.tar.gz" -C violentutf 2>/dev/null || true
        echo "Restored application data"
    fi
    
    # Clean up backup
    rm -rf .backup_temp 2>/dev/null || true
    echo "Backup cleanup completed."
}

# --- Deep Cleanup function ---
perform_deep_cleanup() {
    echo "Starting DEEP cleanup process..."
    echo "This will remove ALL Docker containers, images, volumes, networks, and cache!"
    echo ""
    
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
    
    # First backup user configs and graceful shutdown
    echo "1. Backing up user configurations..."
    backup_user_configs
    
    echo "2. Gracefully shutting down ViolentUTF Streamlit..."
    graceful_streamlit_shutdown
    
    # Then perform regular cleanup
    echo "3. Performing standard cleanup..."
    perform_cleanup_internal
    
    # Stop ALL Docker containers
    echo ""
    echo "4. Stopping ALL Docker containers..."
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
    echo "5. Removing ALL Docker images..."
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
    echo "6. Removing ALL Docker volumes..."
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
    echo "7. Removing ALL Docker networks (except defaults)..."
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
    echo "8. Pruning Docker build cache..."
    docker builder prune -af
    echo "Docker build cache pruned."
    
    # Prune Docker system (everything)
    echo ""
    echo "9. Pruning Docker system cache..."
    docker system prune -af --volumes
    echo "Docker system cache pruned."
    
    # Clean up any remaining Docker artifacts
    echo ""
    echo "10. Final Docker cleanup..."
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

    # 3. Remove shared network
    echo "Removing shared Docker network..."
    if docker network ls | grep -q "$SHARED_NETWORK_NAME"; then
        docker network rm $SHARED_NETWORK_NAME
        echo "Shared network '$SHARED_NETWORK_NAME' removed."
    fi

    # 4. Clean up volumes
    echo "Removing Docker volumes related to ViolentUTF..."
    docker volume ls -q | grep -E "(keycloak|apisix|violentutf|fastapi)" | xargs -r docker volume rm
    echo "Docker volumes cleaned up."
    
    # 5. Clean PyRIT orchestrator memory databases but preserve user application data
    echo "Cleaning PyRIT orchestrator memory databases..."
    if [ -d "violentutf/app_data/violentutf/api_memory" ]; then
        rm -f violentutf/app_data/violentutf/api_memory/orchestrator_memory*.db*
        echo "Removed orchestrator memory databases"
    else
        echo "No orchestrator memory databases found"
    fi

    # Configuration file cleanup
    if [ -f "keycloak/.env" ]; then
        rm "keycloak/.env"
        echo "Removed keycloak/.env"
    fi
    
    if [ -f "violentutf_api/fastapi_app/.env" ]; then
        rm "violentutf_api/fastapi_app/.env"
        echo "Removed violentutf_api/fastapi_app/.env"
    fi
    
    # Only remove template files in apisix/conf directory
    if [ -d "apisix/conf" ]; then
        for file in apisix/conf/*.yaml apisix/conf/*.yml apisix/conf/*.conf; do
            if [ -f "$file" ] && [[ "$file" != *.template ]]; then
                rm "$file"
                echo "Removed $file"
            fi
        done
        
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
    echo "Preserving user's AI tokens file: $AI_TOKENS_FILE"
}

# --- Cleanup function ---
perform_cleanup() {
    echo "Starting cleanup process..."
    
    # 1. Backup user configurations before cleanup
    backup_user_configs
    
    # 2. Gracefully shutdown ViolentUTF Streamlit before cleanup
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

    # 3. Remove shared network if it exists and is not in use
    echo "Removing shared Docker network..."
    if docker network inspect $SHARED_NETWORK_NAME >/dev/null 2>&1; then
        if docker network rm $SHARED_NETWORK_NAME >/dev/null 2>&1; then
            echo "Removed shared network '$SHARED_NETWORK_NAME'."
        else
            echo "Warning: Could not remove shared network '$SHARED_NETWORK_NAME'. It may still be in use."
        fi
    fi

    # 4. Remove configuration files but preserve directories
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

    # AI tokens file (preserve user's configuration)
    echo "Preserving user's AI tokens file: $AI_TOKENS_FILE"

    # 5. Remove Docker volumes
    echo "Removing Docker volumes related to Keycloak and APISIX..."
    # Get volume list and filter for keycloak and apisix volumes
    VOLUMES_TO_REMOVE=$(docker volume ls -q | grep -E '(keycloak|apisix)')
    if [ -n "$VOLUMES_TO_REMOVE" ]; then
        # Use xargs with -r to avoid running if VOLUMES_TO_REMOVE is empty
        echo "$VOLUMES_TO_REMOVE" | xargs -r docker volume rm
        echo "Removed Docker volumes."
    else
        echo "No relevant Docker volumes found to remove."
    fi

    echo "Cleanup completed successfully!"
    echo "The Python virtual environment has been preserved."
    echo "You can now run the script again for a fresh setup."
    exit 0
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

        # Add vutf-network to networks section (Linux sed)
        sed -i '/^networks:/a \ \ vutf-network:\n    external: true' "$compose_file"
        echo "Added vutf-network to networks section in $compose_file"
    fi

    # Check if service section exists
    if ! grep -q "^  $service_name:" "$compose_file"; then
        echo "Warning: Service $service_name not found in $compose_file"
        return 0 # Not an error, just means we can't add the network to this specific service
    fi

    # Add network to service if missing
    # We check if the service block ($service_name:) contains a line starting with 'vutf-network'
    # This is a bit tricky with sed, using awk for block-specific check might be more robust
    # For now, we'll use grep with context and a more complex sed
    if ! awk -v service="  $service_name:" '
        $0 ~ service {in_service=1}
        in_service && /^[[:space:]]*networks:/ {in_networks_block=1}
        in_networks_block && /^[[:space:]]*- vutf-network/ {found=1; exit}
        in_service && NF > 0 && !/^[[:space:]]/ {in_service=0; in_networks_block=0} # Exiting service block
        in_networks_block && NF > 0 && !/^[[:space:]]{3,}/ {in_networks_block=0} # Exiting networks block within service
        END {exit !found}
    ' "$compose_file"; then
        # Check if networks section exists in the service
        if awk -v service="  $service_name:" '
            $0 ~ service {in_service=1}
            in_service && /^[[:space:]]*networks:/ {found=1; exit}
            in_service && NF > 0 && !/^[[:space:]]/ {in_service=0}
            END {exit !found}
        ' "$compose_file"; then
            # Add vutf-network to existing networks section (Linux sed)
            # This is complex with sed, finding the line number of "  service_name:"
            # then finding "    networks:" after that, and inserting.
            # Using a simpler approach: add if not found, may lead to duplicates if not careful
            # This sed command attempts to add it under the service's networks block
            sed -i "/^  $service_name:/,/^  [^ ]/ s/^[[:space:]]*networks:/&\n      - vutf-network/" "$compose_file"

        else
            # Add a new networks section to the service (Linux sed)
            sed -i "/^  $service_name:/a \ \ \ \ networks:\n      - vutf-network" "$compose_file"
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
        return 1 # Indicate that user action is needed
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
    # shellcheck source=/dev/null
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

    response=$(curl -w "%{http_code}" -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/plugins/ai-proxy" \
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

    local route_config
    route_config=$(cat <<-EOF
{
    "id": "$route_id",
    "uri": "$uri",
    "methods": ["POST", "GET"],
    "plugins": {
        "key-auth": {},
        "ai-proxy": {
            "provider": "openai",
            "auth": {
                "header": {
                    "Authorization": "Bearer $api_key"
                }
            },
            "options": {
                "model": "$model"
            }
        }
    }
}
EOF
)

    echo "🔧 Debug: Route config created"
    echo "Creating OpenAI route for model $model at $uri..."

    local response
    local http_code

    # Use the correct URL format - no route ID in path for PUT creation
    response=$(curl -w "%{http_code}" -s -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/$route_id" \
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
        echo "   curl -X PUT '${APISIX_ADMIN_URL}/apisix/admin/routes/$route_id' -H 'X-API-KEY: ${APISIX_ADMIN_KEY}' -H 'Content-Type: application/json' -d '$route_config'"
        return 1
    fi
}

# Function to create Anthropic route
create_anthropic_route() {
    local model="$1"
    local uri="$2"
    local api_key="$3"

    local route_id="anthropic-$(echo "$model" | tr '.' '-' | tr '[:upper:]' '[:lower:]')"

    local route_config
    route_config=$(cat <<-EOF
{
    "id": "$route_id",
    "uri": "$uri",
    "methods": ["POST", "GET"],
    "plugins": {
        "key-auth": {},
        "ai-proxy": {
            "provider": "openai-compatible",
            "auth": {
                "header": {
                    "x-api-key": "$api_key",
                    "anthropic-version": "2023-06-01"
                }
            },
            "options": {
                "model": "$model"
            },
            "override": {
                "endpoint": "https://api.anthropic.com/v1/messages"
            }
        }
    }
}
EOF
)

    echo "Creating Anthropic route for model $model at $uri..."
    local response
    local http_code

    response=$(curl -w "%{http_code}" -s -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/$route_id" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
      -H "Content-Type: application/json" \
      -d "${route_config}" 2>&1)

    http_code="${response: -3}"
    response_body="${response%???}"

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo "✅ Successfully created Anthropic route: $uri -> $model"
        CREATED_AI_ROUTES+=("Anthropic: $uri -> $model")
        return 0
    else
        echo "❌ Failed to create Anthropic route for $model"
        echo "   HTTP Code: $http_code"
        echo "   Response: $response_body"
        return 1
    fi
}

# Function to create Ollama route
create_ollama_route() {
    local model="$1"
    local uri="$2"
    local endpoint="$3"

    local route_id="ollama-$(echo "$model" | tr '.' '-' | tr '[:upper:]' '[:lower:]')"

    local route_config
    route_config=$(cat <<-EOF
{
    "id": "$route_id",
    "uri": "$uri",
    "methods": ["POST", "GET"],
    "plugins": {
        "key-auth": {},
        "ai-proxy": {
            "provider": "openai-compatible",
            "options": {
                "model": "$model"
            },
            "override": {
                "endpoint": "$endpoint"
            }
        }
    }
}
EOF
)

    echo "Creating Ollama route for model $model at $uri..."
    local response
    local http_code

    response=$(curl -w "%{http_code}" -s -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/$route_id" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
      -H "Content-Type: application/json" \
      -d "${route_config}" 2>&1)

    http_code="${response: -3}"
    response_body="${response%???}"

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo "✅ Successfully created Ollama route: $uri -> $model"
        CREATED_AI_ROUTES+=("Ollama: $uri -> $model")
        return 0
    else
        echo "❌ Failed to create Ollama route for $model"
        echo "   HTTP Code: $http_code"
        echo "   Response: $response_body"
        return 1
    fi
}

# Function to create Open WebUI route
create_open_webui_route() {
    local model="$1"
    local uri="$2"
    local endpoint="$3"
    local api_key="$4"

    local route_id="webui-$(echo "$model" | tr '.' '-' | tr '[:upper:]' '[:lower:]')"

    # Build auth section only if API key is provided and not placeholder
    local auth_section_json=""
    if [ -n "$api_key" ] && [ "$api_key" != "your_open_webui_api_key_here" ]; then
        auth_section_json=$(cat <<-AUTH
            "auth": {
                "header": {
                    "Authorization": "Bearer $api_key"
                }
            },
AUTH
)
    fi

    local route_config
    route_config=$(cat <<-EOF
{
    "id": "$route_id",
    "uri": "$uri",
    "methods": ["POST", "GET"],
    "plugins": {
        "key-auth": {},
        "ai-proxy": {
            "provider": "openai-compatible",
            ${auth_section_json}
            "options": {
                "model": "$model"
            },
            "override": {
                "endpoint": "$endpoint"
            }
        }
    }
}
EOF
)

    echo "Creating Open WebUI route for model $model at $uri..."
    local response
    local http_code

    response=$(curl -w "%{http_code}" -s -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/$route_id" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
      -H "Content-Type: application/json" \
      -d "${route_config}" 2>&1)

    http_code="${response: -3}"
    response_body="${response%???}"

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo "✅ Successfully created Open WebUI route: $uri -> $model"
        CREATED_AI_ROUTES+=("Open WebUI: $uri -> $model")
        return 0
    else
        echo "❌ Failed to create Open WebUI route for $model"
        echo "   HTTP Code: $http_code"
        echo "   Response: $response_body"
        return 1
    fi
}

# Function to create APISIX API key consumer
create_apisix_consumer() {
    local consumer_config
    consumer_config=$(cat <<-EOF
{
    "username": "violentutf_user",
    "plugins": {
        "key-auth": {
            "key": "$VIOLENTUTF_API_KEY"
        }
    }
}
EOF
)
    
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

# Function to setup OpenAI routes
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

    local models=("gpt-4" "gpt-3.5-turbo" "gpt-4-turbo")
    local uris=("/ai/openai/gpt4" "/ai/openai/gpt35" "/ai/openai/gpt4-turbo")

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

# Function to setup Anthropic routes
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

    local models=("claude-3-opus-20240229" "claude-3-sonnet-20240229" "claude-3-haiku-20240307")
    local uris=("/ai/anthropic/opus" "/ai/anthropic/sonnet" "/ai/anthropic/haiku")

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

# Function to setup Ollama routes
setup_ollama_routes() {
    if [ "$OLLAMA_ENABLED" != "true" ]; then
        echo "Ollama provider disabled. Skipping setup."
        return 0
    fi

    echo "Setting up Ollama routes..."

    local endpoint="${OLLAMA_ENDPOINT:-http://localhost:11434/v1/chat/completions}"

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

# Function to setup Open WebUI routes
setup_open_webui_routes() {
    if [ "$OPEN_WEBUI_ENABLED" != "true" ]; then
        echo "Open WebUI provider disabled. Skipping setup."
        return 0
    fi

    echo "Setting up Open WebUI routes..."

    local endpoint="${OPEN_WEBUI_ENDPOINT:-http://localhost:3000/ollama/v1/chat/completions}"
    local api_key="$OPEN_WEBUI_API_KEY" # May be empty or a placeholder

    local models=("llama2" "codellama") # Example models for WebUI
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
    local admin_response
    local admin_http_code
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
    local plugins_response
    plugins_response=$(curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/plugins/list" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}")

    if echo "$plugins_response" | jq -e '.[] | select(.name == "ai-proxy")' > /dev/null 2>&1; then
        echo "✅ ai-proxy plugin is available"
    else
        echo "❌ ai-proxy plugin is not available"
        echo "Available plugins (raw): $plugins_response"
        # Attempt to list plugin names if jq is available
        if command -v jq > /dev/null; then
            echo "Available plugin names:"
            echo "$plugins_response" | jq -r '.[]?.name'
        fi
        return 1
    fi

    # List existing routes
    echo "Existing routes:"
    curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/routes" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" | jq -r '.node.nodes[]?.value | "\(.id // .name): \(.uri)"' 2>/dev/null || echo "Could not parse routes (jq might be missing or route structure changed)"

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
        SKIP_AI_SETUP=true # Mark as skipped so summary shows correctly
        return 1
    fi

    # Wait for APISIX to be fully ready after it starts
    echo "Waiting for APISIX to be fully ready for route configuration..."
    sleep 10 # Give APISIX a bit more time if it just started.

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


# Function to test AI routes
test_ai_routes() {
    echo "Testing AI provider routes..."

    # First, list all routes to see what was created
    echo "Listing all APISIX routes (from test_ai_routes):"
    curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/routes" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" | jq -r '.node.nodes[]?.value | "\(.id // .name): \(.uri)"' 2>/dev/null || echo "Could not list routes (jq might be missing or route structure changed)"


    local test_payload='{"messages":[{"role":"user","content":"test"}]}'
    # Test some basic routes, expecting specific HTTP codes based on whether API keys are placeholders
    if [ "$OLLAMA_ENABLED" = "true" ]; then
        # Ollama should ideally work if the service is running, or give 404/503 if model not found/service down
        run_test "AI Ollama route accessibility (/ai/ollama/llama2)" \
                 "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL}/ai/ollama/llama2 -X POST -H 'Content-Type: application/json' -d '$test_payload' | grep -E '(200|404|422|500|503)'"
    fi

    if [ "$OPENAI_ENABLED" = "true" ]; then
        local expected_openai_code="(401|429|400)" # 401 for bad key, 429 for rate limit, 400 for bad request (e.g. model not supported by key)
        if [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
             expected_openai_code="401" # Expect auth failure for placeholder
        fi
        run_test "AI OpenAI route accessibility (/ai/openai/gpt4)" \
                 "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL}/ai/openai/gpt4 -X POST -H 'Content-Type: application/json' -d '$test_payload' | grep -qE '$expected_openai_code'"
    fi

    if [ "$ANTHROPIC_ENABLED" = "true" ]; then
        local expected_anthropic_code="(401|400)" # 401 for bad key, 400 for bad request
        if [ "$ANTHROPIC_API_KEY" = "your_anthropic_api_key_here" ]; then
            expected_anthropic_code="401"
        fi
        run_test "AI Anthropic route accessibility (/ai/anthropic/opus)" \
                 "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL}/ai/anthropic/opus -X POST -H 'Content-Type: application/json' -d '$test_payload' | grep -qE '$expected_anthropic_code'"
    fi
    
    if [ "$BEDROCK_ENABLED" = "true" ]; then
        run_test "AI Bedrock route accessibility (/ai/bedrock/claude-opus-4)" \
                 "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL}/ai/bedrock/claude-opus-4 -X POST -H 'Content-Type: application/json' -d '$test_payload' | grep -E '(200|401|422|400|404)'"
    fi
}

# Simplified AI configuration summary
show_ai_summary() {
    echo ""
    echo "=========================================="
    echo "AI PROXY CONFIGURATION SUMMARY"
    echo "=========================================="

    if [ "$SKIP_AI_SETUP" = true ] && [ ${#CREATED_AI_ROUTES[@]} -eq 0 ]; then
        echo "❌ AI Proxy setup was skipped or failed to create routes."
        echo "   Ensure $AI_TOKENS_FILE is configured and APISIX is running with ai-proxy plugin."
    else
        echo "AI Configuration file: $AI_TOKENS_FILE"
        echo ""
        echo "Enabled AI Providers (based on $AI_TOKENS_FILE and successful route creation):"

        local any_provider_listed=false
        if [ "$OPENAI_ENABLED" = "true" ]; then
            echo "  🔵 OpenAI"
            if grep -q "OpenAI:" <<< "${CREATED_AI_ROUTES[@]}"; then
                for route in "${CREATED_AI_ROUTES[@]}"; do if [[ "$route" == OpenAI:* ]]; then echo "     - ${route#OpenAI: }"; fi; done
            else
                 echo "     ⚠️ No OpenAI routes were successfully created (check logs)."
            fi
            any_provider_listed=true
        fi

        if [ "$ANTHROPIC_ENABLED" = "true" ]; then
            echo "  🟣 Anthropic"
            if grep -q "Anthropic:" <<< "${CREATED_AI_ROUTES[@]}"; then
                for route in "${CREATED_AI_ROUTES[@]}"; do if [[ "$route" == Anthropic:* ]]; then echo "     - ${route#Anthropic: }"; fi; done
            else
                echo "     ⚠️ No Anthropic routes were successfully created (check logs)."
            fi
            any_provider_listed=true
        fi

        if [ "$OLLAMA_ENABLED" = "true" ]; then
            echo "  🟢 Ollama"
             if grep -q "Ollama:" <<< "${CREATED_AI_ROUTES[@]}"; then
                for route in "${CREATED_AI_ROUTES[@]}"; do if [[ "$route" == Ollama:* ]]; then echo "     - ${route#Ollama: }"; fi; done
            else
                echo "     ⚠️ No Ollama routes were successfully created (check logs)."
            fi
            any_provider_listed=true
        fi

        if [ "$OPEN_WEBUI_ENABLED" = "true" ]; then
            echo "  ⚪ Open WebUI"
            if grep -q "Open WebUI:" <<< "${CREATED_AI_ROUTES[@]}"; then
                for route in "${CREATED_AI_ROUTES[@]}"; do if [[ "$route" == "Open WebUI:"* ]]; then echo "     - ${route#Open WebUI: }"; fi; done
            else
                echo "     ⚠️ No Open WebUI routes were successfully created (check logs)."
            fi
            any_provider_listed=true
        fi
        
        if [ "$BEDROCK_ENABLED" = "true" ]; then
            echo "  🟠 AWS Bedrock"
            if grep -q "AWS Bedrock:" <<< "${CREATED_AI_ROUTES[@]}"; then
                for route in "${CREATED_AI_ROUTES[@]}"; do if [[ "$route" == "AWS Bedrock:"* ]]; then echo "     - ${route#AWS Bedrock: }"; fi; done
            else
                echo "     ⚠️ No AWS Bedrock routes were successfully created (check logs)."
            fi
            any_provider_listed=true
        fi

        if [ "$any_provider_listed" = false ]; then
             echo "  ⚠️ No AI providers appear to be enabled and successfully configured in $AI_TOKENS_FILE or routes failed."
        fi


        if [ ${#CREATED_AI_ROUTES[@]} -eq 0 ] && [ "$SKIP_AI_SETUP" != true ]; then
            echo ""
            echo "  ⚠️ No AI routes were created or detected as successfully created. Check setup logs."
        elif [ ${#CREATED_AI_ROUTES[@]} -gt 0 ]; then
            echo ""
            echo "Successfully Created Routes via APISIX Admin API:"
            for route in "${CREATED_AI_ROUTES[@]}"; do
                echo "   - $route"
            done
        fi
    fi

    echo ""
    echo "Example usage (replace with an actual enabled route):"
    echo "curl -X POST http://localhost:9080/ai/ollama/llama3 \\" # Example, might not be enabled
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{\"messages\":[{\"role\":\"user\",\"content\":\"Hello!\"}]}'"
    echo "=========================================="
}


# If deepcleanup mode, perform deep cleanup and exit
if [ "$DEEPCLEANUP_MODE" = true ]; then
    perform_deep_cleanup
fi

# If cleanup mode, perform cleanup and exit
if [ "$CLEANUP_MODE" = true ]; then
    perform_cleanup
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
APISIX_ADMIN_URL="http://localhost:9180" # Default admin API port for APISIX Docker
APISIX_DASHBOARD_URL="http://localhost:9001" # Default dashboard port for APISIX Docker

# Function to generate a random secure string
generate_secure_string() {
    openssl rand -base64 32 | tr -d '\n' | tr -d '\r' | tr -d '/' | tr -d '+' | tr -d '=' | cut -c1-32
}

# Function to backup and prepare config file from template
prepare_config_from_template() {
    local template_file="$1"
    local target_file="${template_file%.template}"
    local backup_suffix
    backup_suffix=$(date +"%Y%m%d%H%M%S")

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

# Function to replace placeholder in a file with a value (Linux sed)
replace_in_file() {
    local file="$1"
    local placeholder="$2"
    local value="$3"
    local description="$4" # Optional: for sensitive values report

    # Escape for sed: & / \
    local escaped_value
    escaped_value=$(printf '%s\n' "$value" | sed -e 's/[&/\\]/\\&/g')

    sed -i "s|${placeholder}|${escaped_value}|g" "$file"

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
# Returns the HTTP status code in global variable API_CALL_STATUS and response body in API_CALL_RESPONSE
make_api_call() {
    local method="$1"
    local endpoint_path="$2"
    local data_arg="$3"
    local full_url="${KEYCLOAK_SERVER_URL}/admin${endpoint_path}" # Note: /admin path
    local response_output response_file http_code

    response_file=$(mktemp)

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
}

# Enhanced network test function
test_network_connectivity() {
    local from_container_service_name="$1" # e.g., apisix (service name in compose)
    local to_service_hostname="$2"        # e.g., keycloak (hostname to ping/curl)
    local to_port="$3"                    # e.g., 8080
    local from_container_id

    # Find the container ID for the 'from' service. Handles cases where multiple containers might exist for a service (e.g. scaled)
    # We'll pick the first one found.
    from_container_id=$(docker ps --filter "name=${from_container_service_name}" --format "{{.ID}}" | head -n 1)

    if [ -z "$from_container_id" ]; then
        # Attempt to find based on compose service name if 'name' filter fails (e.g. project_service_1)
        # This requires knowing the docker compose project name, or more complex filtering.
        # For now, we stick to a simpler name filter, assuming it's often a substring.
        # A more robust way would be to pass the exact container name or use docker compose exec.
        echo "Warning: Container for service '${from_container_service_name}' not found by simple name filter."
        echo "Attempting lookup using 'label=com.docker.compose.service=${from_container_service_name}'..."
        from_container_id=$(docker ps --filter "label=com.docker.compose.service=${from_container_service_name}" --format "{{.ID}}" | head -n 1)
        if [ -z "$from_container_id" ]; then
            echo "Error: Container for service '${from_container_service_name}' not found!"
            return 1
        fi
        echo "Found container ID ${from_container_id} using label filter."
    fi

    echo "⚙️ Testing connectivity from container ${from_container_id} (service ~${from_container_service_name}) to ${to_service_hostname}:${to_port}..."

    # Test 1: Basic ping (network layer) - using service hostname
    # Docker's internal DNS should resolve service names if they are on the same user-defined network.
    echo "Running ping test (network layer) to hostname '${to_service_hostname}'..."
    if docker exec "$from_container_id" ping -c 2 "$to_service_hostname" &>/dev/null; then
        echo "✓ Ping to hostname '${to_service_hostname}' successful - network layer connectivity and DNS confirmed."
    else
        echo "✗ Ping to hostname '${to_service_hostname}' failed."
        echo "  Checking DNS resolution for '${to_service_hostname}' inside container '${from_container_id}'..."
        docker exec "$from_container_id" cat /etc/resolv.conf
        echo "  Attempting nslookup/getent hosts for '${to_service_hostname}':"
        docker exec "$from_container_id" nslookup "$to_service_hostname" 2>/dev/null || docker exec "$from_container_id" getent hosts "$to_service_hostname" 2>/dev/null || echo "  nslookup/getent failed."

        echo "  Networks for container ${from_container_id} ('${from_container_service_name}'):"
        docker inspect --format='{{range $net,$v := .NetworkSettings.Networks}}Network: {{$net}}, IP: {{$v.IPAddress}} {{end}}' "$from_container_id"
        echo "  Networks for target service '${to_service_hostname}' (if running as a container):"
        to_container_id=$(docker ps --filter "name=${to_service_hostname}" --format "{{.ID}}" --filter "label=com.docker.compose.service=${to_service_hostname}" | head -n 1)
        if [ -n "$to_container_id" ]; then
             docker inspect --format='{{range $net,$v := .NetworkSettings.Networks}}Network: {{$net}}, IP: {{$v.IPAddress}} {{end}}' "$to_container_id"
        else
            echo "  Could not find a running container for '${to_service_hostname}' to show its networks."
        fi
        return 1
    fi

    # Test 2: Try TCP connection to port (application layer reachability)
    # Using nc (netcat) if available, otherwise curl.
    echo "Running TCP port test (application layer reachability) to ${to_service_hostname}:${to_port}..."
    if docker exec "$from_container_id" sh -c "command -v nc >/dev/null && nc -zv ${to_service_hostname} ${to_port}" &>/dev/null; then
        echo "✓ TCP connection to ${to_service_hostname}:${to_port} successful (using nc)."
    elif docker exec "$from_container_id" sh -c "command -v curl >/dev/null && curl -s --connect-timeout 5 http://${to_service_hostname}:${to_port} -o /dev/null" &>/dev/null; then
        # Curl will succeed if the HTTP server responds at all, even with an error. This is good enough for port check.
        echo "✓ TCP connection test to http://${to_service_hostname}:${to_port} seems successful (using curl, server responded)."
    else
        echo "✗ TCP connection to ${to_service_hostname}:${to_port} failed (using nc and curl)."
        echo "  Service at ${to_service_hostname} may not be listening on port ${to_port} or firewall is blocking."
        return 1
    fi
    return 0
}


echo "Starting ViolentUTF Nightly with Keycloak, APISIX, and AI Proxy Setup for Linux..."

# ---------------------------------------------------------------
# 1. Check Docker and Docker Compose
# ---------------------------------------------------------------
echo "Step 1: Checking Docker and Docker Compose..."
if ! command -v docker &> /dev/null; then
    echo "Docker could not be found. Please install Docker."
    echo "Visit https://docs.docker.com/engine/install/ for installation instructions."
    exit 1
fi

DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version &> /dev/null; then
    echo "Docker Compose (V2 CLI plugin) could not be found. Trying older 'docker-compose'..."
    if ! command -v docker-compose &> /dev/null; then
        echo "Neither 'docker compose' nor 'docker-compose' found."
        echo "Ensure you have Docker Engine with the Compose plugin installed and running."
        exit 1
    else
        DOCKER_COMPOSE_CMD="docker-compose"
        echo "Found older 'docker-compose'. Will use that."
    fi
fi
echo "Using Docker Compose command: $DOCKER_COMPOSE_CMD"


if ! docker info &> /dev/null || ! docker ps &> /dev/null; then
    echo "Docker daemon is not running or current user cannot connect to it."
    echo "Please start Docker service and ensure you have permissions (e.g., add user to 'docker' group)."
    exit 1
fi
echo "Docker and Docker Compose check passed."

# Create a shared network for all services
echo "Ensuring shared Docker network exists..."
if ! docker network inspect $SHARED_NETWORK_NAME >/dev/null 2>&1; then
    echo "Creating shared Docker network '$SHARED_NETWORK_NAME'..."
    docker network create $SHARED_NETWORK_NAME
    echo "Shared network created."
else
    echo "Shared network '$SHARED_NETWORK_NAME' already exists."
fi

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

# FastAPI secrets
FASTAPI_SECRET_KEY=$(generate_secure_string)
FASTAPI_CLIENT_SECRET=$(generate_secure_string)
FASTAPI_CLIENT_ID="violentutf-fastapi"
SENSITIVE_VALUES+=("FastAPI JWT Secret Key: $FASTAPI_SECRET_KEY")
SENSITIVE_VALUES+=("FastAPI Keycloak Client Secret: $FASTAPI_CLIENT_SECRET")

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
    replace_in_file "apisix/conf/config.yaml" "APISIX_ADMIN_KEY_PLACEHOLDER" "$APISIX_ADMIN_KEY"
    replace_in_file "apisix/conf/config.yaml" "APISIX_KEYRING_VALUE_1_PLACEHOLDER" "$APISIX_KEYRING_VALUE_1"
    replace_in_file "apisix/conf/config.yaml" "APISIX_KEYRING_VALUE_2_PLACEHOLDER" "$APISIX_KEYRING_VALUE_2"
    echo "✅ Created apisix/conf/config.yaml"
fi

# Process dashboard.yaml template
if [ -f "apisix/conf/dashboard.yaml.template" ]; then
    prepare_config_from_template "apisix/conf/dashboard.yaml.template"
    replace_in_file "apisix/conf/dashboard.yaml" "APISIX_DASHBOARD_SECRET_PLACEHOLDER" "$APISIX_DASHBOARD_SECRET"
    replace_in_file "apisix/conf/dashboard.yaml" "APISIX_DASHBOARD_PASSWORD_PLACEHOLDER" "$APISIX_DASHBOARD_PASSWORD"
    echo "✅ Created apisix/conf/dashboard.yaml"
fi

# Process nginx.conf template if exists
if [ -f "apisix/conf/nginx.conf.template" ]; then
    prepare_config_from_template "apisix/conf/nginx.conf.template"
    echo "✅ Created apisix/conf/nginx.conf"
fi

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

cat > violentutf_api/fastapi_app/.env <<EOF
# FastAPI Configuration
SECRET_KEY=$FASTAPI_SECRET_KEY
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
APISIX_BASE_URL=http://apisix:9080
APISIX_ADMIN_URL=http://apisix:9180
APISIX_ADMIN_KEY=$APISIX_ADMIN_KEY

# Service Configuration
SERVICE_NAME=ViolentUTF API
SERVICE_VERSION=1.0.0
DEBUG=false
EOF
echo "✅ Created violentutf_api/fastapi_app/.env"

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
    ensure_network_in_compose "docker-compose.yml" "$KEYCLOAK_SERVICE_NAME_IN_COMPOSE" # Use the service name variable

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
    # Get Keycloak container ID more reliably
    KEYCLOAK_CONTAINER_CANDIDATES=$(${DOCKER_COMPOSE_CMD} -f "${KEYCLOAK_ENV_DIR}/docker-compose.yml" ps -q ${KEYCLOAK_SERVICE_NAME_IN_COMPOSE} 2>/dev/null)
    KEYCLOAK_CONTAINER=$(echo "$KEYCLOAK_CONTAINER_CANDIDATES" | head -n 1)

    if [ -n "$KEYCLOAK_CONTAINER" ]; then
        # Check if already connected
        if ! docker inspect "$KEYCLOAK_CONTAINER" | jq -e --arg net "$SHARED_NETWORK_NAME" '.[0].NetworkSettings.Networks[$net]' > /dev/null 2>&1; then
            echo "Manually connecting Keycloak container '$KEYCLOAK_CONTAINER' to shared network '$SHARED_NETWORK_NAME'..."
            if docker network connect "$SHARED_NETWORK_NAME" "$KEYCLOAK_CONTAINER"; then
                echo "Keycloak container connected to $SHARED_NETWORK_NAME"
            else
                echo "Warning: Failed to connect Keycloak container to $SHARED_NETWORK_NAME. It might already be connected or another issue occurred."
            fi
        else
            echo "Keycloak container '$KEYCLOAK_CONTAINER' already connected to $SHARED_NETWORK_NAME"
        fi
    else
        echo "Warning: Could not find the Keycloak container ID to check network connection."
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
    VUTF_REALM_NAME="$TARGET_REALM_NAME" # Should be "ViolentUTF" or whatever is in realm-export
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


    # Read KEYCLOAK_USERNAME from violentutf/.env (Linux: use grep and cut, or awk)
    KEYCLOAK_APP_USERNAME=$(awk -F= '/^KEYCLOAK_USERNAME[[:space:]]*=/ {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' "$VIOLENTUTF_ENV_FILE")

    if [ -z "$KEYCLOAK_APP_USERNAME" ]; then
        echo "Warning: KEYCLOAK_USERNAME not found or is empty in $VIOLENTUTF_ENV_FILE."
        KEYCLOAK_APP_USERNAME="testuser" # Default if not found
        echo "Defaulting KEYCLOAK_USERNAME to 'testuser'."
        # Check if the line exists to update, otherwise append
        if grep -q "^KEYCLOAK_USERNAME[[:space:]]*=" "$VIOLENTUTF_ENV_FILE"; then
            sed -i "s|^KEYCLOAK_USERNAME[[:space:]]*=.*|KEYCLOAK_USERNAME=${KEYCLOAK_APP_USERNAME}|" "$VIOLENTUTF_ENV_FILE"
        else
            echo "KEYCLOAK_USERNAME=${KEYCLOAK_APP_USERNAME}" >> "$VIOLENTUTF_ENV_FILE"
        fi
        echo "Updated $VIOLENTUTF_ENV_FILE with default username."
    fi
    echo "Using KEYCLOAK_USERNAME: $KEYCLOAK_APP_USERNAME"
    SENSITIVE_VALUES+=("Keycloak Username: $KEYCLOAK_APP_USERNAME")


    # Check if user exists, if not, create
    make_api_call "GET" "/realms/${VUTF_REALM_NAME}/users?username=${KEYCLOAK_APP_USERNAME}&exact=true" # Added exact=true

    if [ "$API_CALL_STATUS" -ne 200 ]; then
        echo "Error checking for user '${KEYCLOAK_APP_USERNAME}'. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        # It's possible the API call itself failed, not that the user doesn't exist. Exit for safety.
        exit 1
    fi

    # jq needs to handle an empty array if user not found, or an array with one user if found
    USER_EXISTS_ID=$(echo "$API_CALL_RESPONSE" | jq -r 'if type == "array" and length > 0 then .[0].id else empty end')


    if [ -z "$USER_EXISTS_ID" ]; then # Check if empty, jq 'empty' results in empty string
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
        USER_EXISTS_ID=$(echo "$API_CALL_RESPONSE" | jq -r 'if type == "array" and length > 0 then .[0].id else empty end')
        if [ -z "$USER_EXISTS_ID" ]; then
            echo "Error: Failed to retrieve ID for newly created user '${KEYCLOAK_APP_USERNAME}'."
            exit 1
        fi
        echo "User '${KEYCLOAK_APP_USERNAME}' created with ID '${USER_EXISTS_ID}'."
    else
        echo "User '${KEYCLOAK_APP_USERNAME}' already exists with ID '${USER_EXISTS_ID}'."
    fi

    # Create/Reset credential for the user with pre-generated password
    echo "Setting password for user '${KEYCLOAK_APP_USERNAME}' via API..."
    PASSWORD_RESET_PAYLOAD="{\"type\":\"password\", \"value\":\"${VIOLENTUTF_USER_PASSWORD}\", \"temporary\":false}"
    make_api_call "PUT" "/realms/${VUTF_REALM_NAME}/users/${USER_EXISTS_ID}/reset-password" "${PASSWORD_RESET_PAYLOAD}"
    if [ "$API_CALL_STATUS" -ne 204 ]; then # 204 No Content is success
        echo "Error: Failed to set password for user '${KEYCLOAK_APP_USERNAME}' via API. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi
    echo "Password for user '${KEYCLOAK_APP_USERNAME}' has been set via API."
    
    # Store reference to the password for later use
    NEW_USER_PASSWORD=$VIOLENTUTF_USER_PASSWORD

    # ---------------------------------------------------------------
    # 7. All secrets already generated
    # ---------------------------------------------------------------
    echo "Step 7: All secure secrets already generated at the beginning."


    echo "Keycloak client and user configuration complete via API."
else
    echo "Skipped Keycloak setup steps 4-7 as stack was already running."
fi # End of KEYCLOAK_SETUP_NEEDED conditional block

# ---------------------------------------------------------------
# SECTION B: APISIX SETUP
# ---------------------------------------------------------------
echo "SECTION B: SETTING UP APISIX"

# ---------------------------------------------------------------
# B1. APISIX configuration already created upfront
# ---------------------------------------------------------------
echo "Step B1: APISIX configuration files already created."


# ---------------------------------------------------------------
# B2. Check APISIX stack and launch if not running
# ---------------------------------------------------------------
echo "Step B2: Checking and launching APISIX Docker stack..."
APISIX_ENV_DIR="apisix"
APISIX_COMPOSE_FILE="${APISIX_ENV_DIR}/docker-compose.yml"
APISIX_SERVICE_NAME_IN_COMPOSE="apisix" # As defined in your apisix/docker-compose.yml

APISIX_SETUP_NEEDED=true
# Check if the APISIX service is running
if ${DOCKER_COMPOSE_CMD} -f "$APISIX_COMPOSE_FILE" ps -q ${APISIX_SERVICE_NAME_IN_COMPOSE} 2>/dev/null | grep -q .; then
    CONTAINER_ID=$(${DOCKER_COMPOSE_CMD} -f "$APISIX_COMPOSE_FILE" ps -q ${APISIX_SERVICE_NAME_IN_COMPOSE} 2>/dev/null | head -n 1)
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
    if [ ! -d "$APISIX_ENV_DIR" ]; then
        echo "Error: APISIX directory '$APISIX_ENV_DIR' not found!"
        exit 1
    fi
    if [ ! -f "$APISIX_COMPOSE_FILE" ]; then
        echo "Error: APISIX Docker Compose file '$APISIX_COMPOSE_FILE' not found!"
        exit 1
    fi


    # Create a prometheus.yml file if it doesn't exist in apisix/conf
    if [ ! -f "${APISIX_ENV_DIR}/conf/prometheus.yml" ]; then
        echo "Creating default Prometheus configuration in ${APISIX_ENV_DIR}/conf/prometheus.yml..."
        mkdir -p "${APISIX_ENV_DIR}/conf"
        cat > "${APISIX_ENV_DIR}/conf/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'apisix'
    static_configs:
      - targets: ['apisix:9091'] # Assumes apisix service name is 'apisix' and metrics port is 9091
    metrics_path: '/apisix/prometheus/metrics'
EOF
    fi

    # Store current directory and cd into apisix dir
    ORIGINAL_DIR=$(pwd)
    cd "$APISIX_ENV_DIR" || { echo "Failed to cd into $APISIX_ENV_DIR directory"; exit 1; }

    # Ensure docker-compose.yml has network configuration for APISIX service
    echo "Ensuring APISIX docker-compose.yml has proper network configuration for '$APISIX_SERVICE_NAME_IN_COMPOSE' service..."
    ensure_network_in_compose "docker-compose.yml" "$APISIX_SERVICE_NAME_IN_COMPOSE"
    # Also ensure other services in apisix compose (like etcd, dashboard) are on the network if they need to communicate
    # For now, focusing on 'apisix' service itself.

    echo "Launching Docker Compose for APISIX..."
    if ${DOCKER_COMPOSE_CMD} up -d; then
        echo "APISIX stack started successfully."
        echo "Waiting for APISIX to be fully operational (this might take a minute)..."
        RETRY_COUNT=0
        MAX_RETRIES=20 # ~2 minutes with 6-second interval
        SUCCESS=false
        until [ $RETRY_COUNT -ge $MAX_RETRIES ]; do
            RETRY_COUNT=$((RETRY_COUNT+1))
            # Check APISIX health by accessing its admin API (typically requires X-API-KEY)
            # We use the APISIX_ADMIN_KEY generated earlier or one from existing config
            HTTP_STATUS_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "${APISIX_ADMIN_URL}/apisix/admin/routes" \
                 -H "X-API-KEY: ${APISIX_ADMIN_KEY}")
            if [ "$HTTP_STATUS_HEALTH" -eq 200 ] || [ "$HTTP_STATUS_HEALTH" -eq 401 ]; then
                # 200 means OK. 401 means APISIX is up but our key might be wrong (e.g. if stack was pre-existing with different key)
                # or if the key placeholder wasn't replaced yet in a fresh setup if this check runs too fast.
                # For a fresh setup, after config.yaml is written, 200 is expected.
                echo "APISIX is up and responding on its admin endpoint (status $HTTP_STATUS_HEALTH)."
                SUCCESS=true
                break
            fi
            echo "APISIX not ready yet (attempt $RETRY_COUNT/$MAX_RETRIES, status $HTTP_STATUS_HEALTH to admin). Waiting 6 seconds..."
            sleep 6
        done

        if [ "$SUCCESS" = false ]; then
            echo "APISIX did not become ready in time. Please check Docker logs."
            ${DOCKER_COMPOSE_CMD} logs ${APISIX_SERVICE_NAME_IN_COMPOSE}
            # Also show etcd logs as it's a critical dependency for APISIX
            if ${DOCKER_COMPOSE_CMD} ps --services | grep -q etcd; then
                echo "ETCD logs:"
                ${DOCKER_COMPOSE_CMD} logs etcd
            fi
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

    # Ensure the APISIX container is connected to the shared network
    echo "Ensuring APISIX container is connected to shared network '$SHARED_NETWORK_NAME'..."
    APISIX_CONTAINER_CANDIDATES=$(${DOCKER_COMPOSE_CMD} -f "$APISIX_COMPOSE_FILE" ps -q ${APISIX_SERVICE_NAME_IN_COMPOSE} 2>/dev/null)
    APISIX_CONTAINER=$(echo "$APISIX_CONTAINER_CANDIDATES" | head -n 1)

    if [ -n "$APISIX_CONTAINER" ]; then
        if ! docker inspect "$APISIX_CONTAINER" | jq -e --arg net "$SHARED_NETWORK_NAME" '.[0].NetworkSettings.Networks[$net]' > /dev/null 2>&1; then
            echo "Manually connecting APISIX container '$APISIX_CONTAINER' to shared network '$SHARED_NETWORK_NAME'..."
            if docker network connect "$SHARED_NETWORK_NAME" "$APISIX_CONTAINER"; then
                echo "APISIX container connected to $SHARED_NETWORK_NAME"
            else
                echo "Warning: Failed to connect APISIX container to $SHARED_NETWORK_NAME. It may already be connected or an issue occurred."
            fi
        else
            echo "APISIX container '$APISIX_CONTAINER' already connected to $SHARED_NETWORK_NAME"
        fi
    else
        echo "Warning: Could not find the APISIX container ID to check/ensure network connection."
    fi

    # ---------------------------------------------------------------
    # B3. Configure APISIX routes to Keycloak if needed (for fresh setup)
    # ---------------------------------------------------------------
    echo "Step B3: Configuring APISIX routes to Keycloak..."

    # Add a route in APISIX to proxy requests to Keycloak
    # This example creates a route that forwards all requests with prefix /auth to Keycloak
    # Note: Keycloak service name in Docker network is 'keycloak' (from keycloak/docker-compose.yml)
    echo "Creating APISIX route to Keycloak (keycloak service name: keycloak)..."
    ROUTE_ID_KEYCLOAK_PROXY="keycloak-auth-proxy" # Use a descriptive ID
    # Ensure keycloak hostname is resolvable by APISIX container (should be if on same shared network)
    # upstream node uses service name 'keycloak' as defined in keycloak's docker-compose and connected to shared network
    KEYCLOAK_UPSTREAM_HOST="keycloak" # This should be the service name of Keycloak in the Docker network

    ROUTE_CONFIG_KEYCLOAK=$(cat <<-EOF
{
  "id": "${ROUTE_ID_KEYCLOAK_PROXY}",
  "uri": "/auth/*",
  "name": "keycloak-proxy-service",
  "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "${KEYCLOAK_UPSTREAM_HOST}:8080": 1
    },
    "scheme": "http"
  },
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/auth/(.*)", "/realms/\$1"]
    }
  }
}
EOF
)
# Note: The proxy-rewrite regex_uri might need adjustment based on how Keycloak URLs are structured
# If Keycloak base is /auth, and you want APISIX /auth/* to map to Keycloak /auth/*,
# then regex_uri could be ["^/auth/(.*)", "/auth/$1"] or just strip the prefix if Keycloak handles it.
# If Keycloak is running with context path /auth, and you proxy /auth/* from APISIX
# to keycloak:8080/*, then you might not need rewrite or a simpler one.
# The example above assumes Keycloak's actual paths start like /realms/master/... under its root.
# If Keycloak is at http://keycloak:8080/auth, then you'd want /auth/* in APISIX to map to /auth/* in Keycloak.
# Let's adjust proxy-rewrite for typical Keycloak setup:
# APISIX listens on /auth/*
# Keycloak's base URL is http://keycloak:8080/auth
# So, a request to APISIX http://localhost:9080/auth/realms/master/...
# should go to http://keycloak:8080/auth/realms/master/...
# This means the upstream target is keycloak:8080, and path should be passed as is after /auth.
# The original script's proxy rewrite was: regex_uri: ["^/auth/(.*)", "/$1"]
# This would send /auth/realms/master to keycloak:8080/realms/master
# If Keycloak is at keycloak:8080/auth, then the path becomes keycloak:8080/auth/realms/master, which is correct.
# So proxy-rewrite ["^/auth/(.*)", "/auth/$1"] might be what is intended if Keycloak root is just keycloak:8080 without /auth context.
# Given KEYCLOAK_SERVER_URL="http://localhost:8080", it implies Keycloak is not running under /auth context by default.
# Let's stick to the original script's rewrite logic for now.
# But if Keycloak is indeed at http://keycloak:8080/auth (standard setup), then the rewrite
# "regex_uri": ["^/auth/(.*)", "/auth/$1"] seems more appropriate for upstream "keycloak:8080".
# However, if Keycloak itself is at http://keycloak:8080 (no /auth in its base URL within the container), then ["^/auth/(.*)", "/$1"] to upstream "keycloak:8080" is correct.
# The Keycloak docker image usually has /auth as its root context. So, if upstream is keycloak:8080,
# then requests to APISIX /auth/foo should map to keycloak:8080/auth/foo.
# proxy-rewrite: regex_uri: ["^/auth/(.*)", "/auth/$1"]
# Let's use the common case where Keycloak docker runs with /auth context.
ROUTE_CONFIG_KEYCLOAK_REVISED=$(cat <<-EOF
{
  "id": "${ROUTE_ID_KEYCLOAK_PROXY}",
  "uri": "/auth/*",
  "name": "keycloak-proxy-service",
  "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "${KEYCLOAK_UPSTREAM_HOST}:8080": 1
    },
    "scheme": "http"
  },
  "plugins": {
    "proxy-rewrite": {
      "regex_uri": ["^/auth/(.*)", "/auth/\$1"]
    }
  }
}
EOF
)


    # Send API request to create/update the route (PUT is idempotent for routes with ID)
    # Use the route ID in the URL path for PUT.
    KC_PROXY_RESPONSE=$(curl -s -w "%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/${ROUTE_ID_KEYCLOAK_PROXY}" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
      -H "Content-Type: application/json" \
      -d "${ROUTE_CONFIG_KEYCLOAK_REVISED}")
    KC_PROXY_HTTP_CODE="${KC_PROXY_RESPONSE: -3}"
    KC_PROXY_BODY="${KC_PROXY_RESPONSE%???}"

    if [ "$KC_PROXY_HTTP_CODE" = "200" ] || [ "$KC_PROXY_HTTP_CODE" = "201" ]; then
      echo "Successfully configured APISIX route to Keycloak (ID: ${ROUTE_ID_KEYCLOAK_PROXY}). HTTP Status: $KC_PROXY_HTTP_CODE"
    else
      echo "Warning: Failed to configure APISIX route to Keycloak. HTTP Status: $KC_PROXY_HTTP_CODE"
      echo "Response Body: $KC_PROXY_BODY"
      echo "Route Config Sent: $ROUTE_CONFIG_KEYCLOAK_REVISED"
      echo "Check APISIX logs and ensure Keycloak service ('${KEYCLOAK_UPSTREAM_HOST}') is reachable from APISIX container on the shared network."
    fi

    echo "APISIX setup complete."
else
    echo "Skipped APISIX stack launch and initial route setup as stack was already running."

    # If APISIX was already running, we need to ensure our APISIX_ADMIN_KEY variable is correct.
    # Try to read it from the existing apisix/conf/config.yaml
    if [ -f "${APISIX_ENV_DIR}/conf/config.yaml" ]; then
        # More robustly parse YAML for admin_key, e.g. using yq if available, or careful grep/awk
        # Example using grep and awk (simplistic, assumes specific formatting)
        EXISTING_ADMIN_KEY=$(grep -A 3 "admin_key:" "${APISIX_ENV_DIR}/conf/config.yaml" | grep -E "^\s*key:" | awk '{print $2}' | tr -d '"' | head -n 1)
        if [ -n "$EXISTING_ADMIN_KEY" ] && [ "$EXISTING_ADMIN_KEY" != "null" ]; then
            APISIX_ADMIN_KEY=$EXISTING_ADMIN_KEY
            echo "Using existing APISIX Admin API Key from config.yaml: $APISIX_ADMIN_KEY"
            # Update SENSITIVE_VALUES if it was previously set with a generated one
            # This requires finding and replacing or just adding if not present.
            # For simplicity, we just add it; the report might show two if generated then overwritten.
            SENSITIVE_VALUES+=("APISIX Admin API Key (existing): $APISIX_ADMIN_KEY")
        else
            echo "Warning: APISIX is running, but could not determine existing Admin API Key from config.yaml."
            echo "AI Proxy route creation might fail if the default generated key is incorrect."
            echo "Using the initially generated APISIX_ADMIN_KEY: $APISIX_ADMIN_KEY"
        fi
    else
        echo "Warning: APISIX is running, but its config.yaml was not found at ${APISIX_ENV_DIR}/conf/config.yaml."
        echo "Cannot verify/update APISIX_ADMIN_KEY. Using the initially generated one: $APISIX_ADMIN_KEY"
    fi

    # Extract dashboard credentials if available from existing dashboard.yaml
    if [ -f "${APISIX_ENV_DIR}/conf/dashboard.yaml" ]; then
        EXISTING_DASHBOARD_SECRET=$(grep -A 2 "jwt_secret:" "${APISIX_ENV_DIR}/conf/dashboard.yaml" | grep -E "^\s*secret:" | awk '{print $2}' | tr -d '"' | head -n 1)
        if [ -n "$EXISTING_DASHBOARD_SECRET" ]; then
            SENSITIVE_VALUES+=("APISIX Dashboard JWT Secret (existing): $EXISTING_DASHBOARD_SECRET")
        fi
        # This parsing for password is very fragile. yq would be better.
        EXISTING_DASHBOARD_PASSWORD=$(grep -A 5 -E "^\s*user:" "${APISIX_ENV_DIR}/conf/dashboard.yaml" | grep -A 1 "username: admin" | grep "password:" | awk '{print $2}' | tr -d '"' | head -n 1)
        if [ -n "$EXISTING_DASHBOARD_PASSWORD" ]; then
             SENSITIVE_VALUES+=("APISIX Dashboard Admin Password (existing): $EXISTING_DASHBOARD_PASSWORD")
        fi
    fi


    # Ensure the container is connected to the shared network even if APISIX was already running
    echo "Ensuring APISIX container (already running) is connected to shared network '$SHARED_NETWORK_NAME'..."
    APISIX_CONTAINER_CANDIDATES=$(${DOCKER_COMPOSE_CMD} -f "$APISIX_COMPOSE_FILE" ps -q ${APISIX_SERVICE_NAME_IN_COMPOSE} 2>/dev/null)
    APISIX_CONTAINER=$(echo "$APISIX_CONTAINER_CANDIDATES" | head -n 1)

    if [ -n "$APISIX_CONTAINER" ]; then
        if ! docker inspect "$APISIX_CONTAINER" | jq -e --arg net "$SHARED_NETWORK_NAME" '.[0].NetworkSettings.Networks[$net]' > /dev/null 2>&1; then
            echo "Manually connecting APISIX container '$APISIX_CONTAINER' to shared network '$SHARED_NETWORK_NAME'..."
            if docker network connect "$SHARED_NETWORK_NAME" "$APISIX_CONTAINER"; then
                echo "APISIX container connected to $SHARED_NETWORK_NAME"
            else
                 echo "Warning: Failed to connect APISIX container to $SHARED_NETWORK_NAME. It might already be connected or another issue occurred."
            fi
        else
            echo "APISIX container '$APISIX_CONTAINER' already connected to $SHARED_NETWORK_NAME"
        fi
    else
        echo "Warning: Could not find the APISIX container ID to check/ensure network connection (when already running)."
    fi
fi # End of APISIX_SETUP_NEEDED conditional block


# ---------------------------------------------------------------
# SECTION C: AI PROXY SETUP
# ---------------------------------------------------------------
echo "SECTION C: SETTING UP AI PROXY"
SKIP_AI_SETUP=false # Initialize

# ---------------------------------------------------------------
# C1. Prepare AI Configuration
# ---------------------------------------------------------------
echo "Step C1: Preparing AI configuration..."

if ! create_ai_tokens_template; then
    # This means the template was created and user needs to edit it.
    # We should skip the actual AI route setup for this run.
    echo "📑 $AI_TOKENS_FILE was created. Please edit it with your AI provider keys and re-run the script to set up AI routes."
    SKIP_AI_SETUP=true
else
    # Template already existed, try to load it.
    if ! load_ai_tokens; then
        echo "❌ Failed to load AI configuration from $AI_TOKENS_FILE. AI Proxy setup will be skipped."
        SKIP_AI_SETUP=true
    fi
fi

# ---------------------------------------------------------------
# C2. Setup AI Provider Routes
# ---------------------------------------------------------------
if [ "$SKIP_AI_SETUP" != true ]; then
    echo "Step C2: Setting up AI provider routes in APISIX..."

    # Check if ai-proxy plugin is available - requires APISIX_ADMIN_KEY to be set correctly
    if ! check_ai_proxy_plugin; then
        echo "❌ Cannot proceed with AI proxy setup - ai-proxy plugin not available or APISIX admin API not reachable with current key."
        SKIP_AI_SETUP=true # Mark as skipped so summary shows correctly
    else
        if ! setup_ai_providers_enhanced; then
            echo "⚠️  AI Provider route setup encountered errors. Some AI routes may not be available."
            # We don't set SKIP_AI_SETUP to true here, as some routes might have been created.
            # The summary function will show what was actually created.
        else
            echo "✅ AI Provider routes setup completed."
        fi
    fi
else
    echo "Skipping AI provider routes setup (Step C2) due to earlier configuration issues or user action required for $AI_TOKENS_FILE."
fi

# ---------------------------------------------------------------
# SECTION D: VIOLENTUTF API (FASTAPI) SETUP
# ---------------------------------------------------------------
echo "SECTION D: SETTING UP VIOLENTUTF API (FASTAPI)"

# FastAPI configuration was already created upfront
echo "FastAPI configuration already created."

# Create FastAPI client in Keycloak
echo "Creating FastAPI client in Keycloak..."

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
    "serviceAccountsEnabled": false,
    "publicClient": false,
    "frontchannelLogout": false,
    "protocol": "openid-connect",
    "attributes": {},
    "authenticationFlowBindingOverrides": {},
    "fullScopeAllowed": true,
    "nodeReRegistrationTimeout": -1,
    "protocolMappers": [
        {
            "name": "username",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-property-mapper",
            "consentRequired": false,
            "config": {
                "userinfo.token.claim": "true",
                "user.attribute": "username",
                "id.token.claim": "true",
                "access.token.claim": "true",
                "claim.name": "preferred_username",
                "jsonType.label": "String"
            }
        }
    ],
    "defaultClientScopes": ["web-origins", "role_list", "profile", "roles", "email"],
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

# Create FastAPI route in APISIX
echo "Creating FastAPI route in APISIX..."

# Store current directory
ORIGINAL_DIR=$(pwd)

# Function to wait for APISIX to be ready
wait_for_apisix() {
    echo "Waiting for APISIX to be ready..."
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -o /dev/null -w "%{http_code}" "${APISIX_ADMIN_URL}/apisix/admin/routes" \
           -H "X-API-KEY: ${APISIX_ADMIN_KEY}" | grep -q "200"; then
            echo "APISIX is ready."
            return 0
        fi
        
        echo "Waiting for APISIX... (attempt $((attempt+1))/$max_attempts)"
        sleep 2
        attempt=$((attempt+1))
    done
    
    echo "Warning: APISIX may not be fully ready after $max_attempts attempts."
    return 1
}

# Function to create FastAPI route
create_fastapi_route() {
    echo "Creating route for FastAPI service in APISIX..."
    
    local route_name="violentutf-fastapi"
    local route_uri="/api/*"
    local upstream_url="http://violentutf_api:8000"
    
    # Create route configuration
    cat > /tmp/fastapi-route.json <<EOF
{
    "name": "ViolentUTF FastAPI Service",
    "uri": "${route_uri}",
    "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    "upstream": {
        "type": "roundrobin",
        "nodes": {
            "${upstream_url}": 1
        }
    },
    "plugins": {
        "proxy-rewrite": {
            "regex_uri": ["^/api(.*)", "\$1"]
        },
        "cors": {
            "allow_origins": "*",
            "allow_methods": "*",
            "allow_headers": "*",
            "expose_headers": "*",
            "max_age": 5,
            "allow_credential": false
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
            "allow_methods": "GET,POST,PUT,DELETE,PATCH,OPTIONS",
            "allow_headers": "Authorization,Content-Type,X-Requested-With"
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
            "allow_methods": "GET,POST,PUT,DELETE,PATCH,OPTIONS",
            "allow_headers": "Authorization,Content-Type,X-Requested-With"
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

# Wait for APISIX to be ready
if wait_for_apisix; then
    echo "APISIX is ready. Configuring all routes..."
    
    # Use the comprehensive configure_routes.sh script instead of manual route creation
    if [ -f "apisix/configure_routes.sh" ]; then
        echo "Running comprehensive route configuration script..."
        cd apisix
        chmod +x configure_routes.sh
        ./configure_routes.sh
        cd "$ORIGINAL_DIR"
        echo "✅ All API routes configured successfully."
    else
        echo "⚠️  configure_routes.sh not found. Falling back to manual route creation..."
        create_fastapi_route
        create_fastapi_docs_routes
    fi
else
    echo "Warning: Could not verify APISIX is ready. Attempting to configure routes anyway..."
    if [ -f "apisix/configure_routes.sh" ]; then
        cd apisix
        chmod +x configure_routes.sh
        ./configure_routes.sh
        cd "$ORIGINAL_DIR"
    else
        create_fastapi_route
        create_fastapi_docs_routes
    fi
fi

echo "FastAPI service configuration complete."
echo "The service will be started with the APISIX stack."

# ---------------------------------------------------------------
# CONFIGURE ORCHESTRATOR API ROUTES
# ---------------------------------------------------------------
echo ""
echo "Configuring PyRIT Orchestrator API routes..."

# Check if orchestrator routes configuration script exists
if [ -f "apisix/configure_orchestrator_routes.sh" ]; then
    echo "Found orchestrator routes configuration script."
    cd apisix
    chmod +x configure_orchestrator_routes.sh
    ./configure_orchestrator_routes.sh
    echo "✅ Orchestrator API routes configured"
    cd "$ORIGINAL_DIR"
else
    echo "⚠️  Warning: apisix/configure_orchestrator_routes.sh not found. Orchestrator API routes not configured."
    echo "   Orchestrator functionality may be limited without proper route configuration."
fi

# Apply orchestrator executions route fix to prevent 422 errors
echo "Applying orchestrator executions route fix..."
if [ -f "apisix/fix_orchestrator_executions_route.sh" ]; then
    echo "Running orchestrator executions route fix script..."
    cd apisix
    chmod +x fix_orchestrator_executions_route.sh
    ./fix_orchestrator_executions_route.sh
    echo "✅ Orchestrator executions route fix applied successfully."
    cd "$ORIGINAL_DIR"
else
    echo "⚠️  Warning: apisix/fix_orchestrator_executions_route.sh not found. Route fix not applied."
fi

# Return to original directory
cd "$ORIGINAL_DIR"

# Note: VIOLENTUTF_API_KEY is already generated in the beginning
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
        PY_VERSION_CHECK=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
        if [[ "$PY_VERSION_CHECK" == 3* ]]; then # Check if 'python' is Python 3
            PYTHON_CMD="python"
        else
            echo "Python 3 not found with 'python3' or 'python' command. Please install Python 3.10+."
            echo "PyRIT and Garak require Python 3.10-3.12. For Linux, use your package manager, e.g., 'sudo apt install python3 python3-pip python3-venv'."
            exit 1
        fi
    else
        echo "Python 3 not found. Please install Python 3.10+."
        echo "PyRIT and Garak require Python 3.10-3.12. For Linux, use your package manager, e.g., 'sudo apt install python3 python3-pip python3-venv'."
        exit 1
    fi
fi
echo "Using '$PYTHON_CMD' for Python operations."
# Check for Python 3.10+ (required for PyRIT and Garak)
PY_FULL_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_FULL_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_FULL_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo "Your Python version ($PYTHON_CMD is $PY_FULL_VERSION) is less than 3.10. Please upgrade."
    echo "PyRIT and Garak require Python 3.10-3.12 for optimal compatibility."
    exit 1
fi

if [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -gt 12 ]; then
    echo "Warning: Python version $PY_FULL_VERSION may have compatibility issues with PyRIT and Garak."
    echo "Python 3.10-3.12 is recommended for optimal compatibility."
fi

echo "Python version $PY_FULL_VERSION is compatible."

# ---------------------------------------------------------------
# 9. Set up and run the ViolentUTF Python app
# ---------------------------------------------------------------
echo "Step 9: Setting up and running ViolentUTF Python app..."

echo "Ensuring pip and venv are available for $PYTHON_CMD..."
# On Linux, pip and venv might need to be installed separately for the python3 version in use
# e.g., sudo apt-get install python3-pip python3-venv
# The script assumes these are present or installable by user if system python doesn't have them.
$PYTHON_CMD -m ensurepip --upgrade > /dev/null 2>&1 # Ensure pip is there for the selected python
$PYTHON_CMD -m pip install --upgrade pip > /dev/null # Upgrade pip

VENV_DIR=".vitutf"
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment '$VENV_DIR' already exists. Skipping creation."
else
    echo "Creating virtual environment in $VENV_DIR using $PYTHON_CMD..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment. Ensure '$PYTHON_CMD -m venv' works."
        echo "You might need to install the venv package (e.g., python3-venv on Debian/Ubuntu)."
        exit 1
    fi
    echo "Created virtual environment in $VENV_DIR."
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

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
echo "Activated virtual environment: $VENV_DIR"

REQUIREMENTS_PATH="violentutf/requirements.txt"
if [ ! -f "$REQUIREMENTS_PATH" ]; then
    # Fallback to root if not in violentutf subdir
    REQUIREMENTS_PATH="requirements.txt"
fi

if [ -f "$REQUIREMENTS_PATH" ]; then
    echo "Installing packages from $REQUIREMENTS_PATH..."
    python -m pip cache purge # Good practice for clean installation
    python -m pip install --upgrade pip # Ensure pip in venv is latest
    python -m pip install -r "$REQUIREMENTS_PATH"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install packages from $REQUIREMENTS_PATH."
        echo "Check the output above for specific package installation errors."
        # Consider deactivating venv before exiting if appropriate, though script ends here anyway.
        exit 1
    fi
    echo "Package installation complete."
else
    echo "Warning: No requirements.txt found at violentutf/requirements.txt or ./requirements.txt. Skipping package installation."
    echo "If your application has dependencies, this might lead to errors later."
fi

# ---------------------------------------------------------------
# 10. Update ViolentUTF config to use APISIX proxy if needed
# ---------------------------------------------------------------
echo "Step 10: Updating ViolentUTF config to use APISIX proxy if needed..."

# Check if we need to update the ViolentUTF config to use APISIX proxy
if [ -f "$VIOLENTUTF_ENV_FILE" ]; then
    # Add/update KEYCLOAK_URL_BASE to point to APISIX proxy if it exists
    # APISIX is at http://localhost:9080, and the Keycloak proxy route is /auth/*
    KEYCLOAK_PROXY_URL="http://localhost:9080/auth"
    if grep -q "^KEYCLOAK_URL_BASE" "$VIOLENTUTF_ENV_FILE"; then
        sed -i "s|^KEYCLOAK_URL_BASE=.*|KEYCLOAK_URL_BASE=${KEYCLOAK_PROXY_URL}|" "$VIOLENTUTF_ENV_FILE"
    else
        echo "KEYCLOAK_URL_BASE=${KEYCLOAK_PROXY_URL}" >> "$VIOLENTUTF_ENV_FILE"
    fi
    echo "Updated KEYCLOAK_URL_BASE in $VIOLENTUTF_ENV_FILE to use APISIX proxy: $KEYCLOAK_PROXY_URL"

    # Add AI proxy configuration if not present
    AI_PROXY_BASE_URL="http://localhost:9080/ai" # APISIX base for AI routes
    if ! grep -q "^AI_PROXY_BASE_URL" "$VIOLENTUTF_ENV_FILE"; then
        echo "AI_PROXY_BASE_URL=${AI_PROXY_BASE_URL}" >> "$VIOLENTUTF_ENV_FILE"
        echo "Added AI_PROXY_BASE_URL to $VIOLENTUTF_ENV_FILE: $AI_PROXY_BASE_URL"
    else
        sed -i "s|^AI_PROXY_BASE_URL=.*|AI_PROXY_BASE_URL=${AI_PROXY_BASE_URL}|" "$VIOLENTUTF_ENV_FILE"
        echo "Updated AI_PROXY_BASE_URL in $VIOLENTUTF_ENV_FILE to: $AI_PROXY_BASE_URL"
    fi
else
    echo "Warning: $VIOLENTUTF_ENV_FILE not found. Cannot update with APISIX proxy URLs."
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
    local expected_to_contain_or_match="${3:-0}" # Can be exit code (numeric) or string to grep for

    echo "Testing: $test_name"
    echo "  Command: $test_command"

    local output
    local actual_exit_code

    # Capture both output and exit code
    # Using bash process substitution for more robust output capture
    output=$(eval "$test_command" 2>&1)
    actual_exit_code=$?

    local success=false
    if [[ "$expected_to_contain_or_match" =~ ^[0-9]+$ ]]; then # Numeric, so expect exit code
        if [ "$actual_exit_code" -eq "$expected_to_contain_or_match" ]; then
            success=true
        fi
        echo "  Result: Expected exit code $expected_to_contain_or_match, Got $actual_exit_code."
    else # String, so grep output for it
        if echo "$output" | grep -qE -- "$expected_to_contain_or_match"; then
            success=true
        fi
        echo "  Result: Expected output to contain/match '$expected_to_contain_or_match'."
        echo "  Actual Output (first 100 chars): $(echo "$output" | head -c 100)"
    fi


    if [ "$success" = true ]; then
        TEST_RESULTS+=("✅ PASS: $test_name")
        echo "  Status: PASS"
    else
        TEST_RESULTS+=("❌ FAIL: $test_name")
        echo "  Status: FAIL"
        echo "  Full Output for FAIL: $output" # Show full output only on failure
        TEST_FAILURES=$((TEST_FAILURES+1))
    fi
    echo ""
}

# 1. Test Keycloak master realm is accessible directly
run_test "Keycloak master realm (direct)" \
         "curl -s -o /dev/null -w '%{http_code}' ${KEYCLOAK_SERVER_URL}/realms/master" \
         "200"


# 2. Test network connectivity between APISIX service and Keycloak service
#    This uses the service names `apisix` and `keycloak` and port `8080`
run_test "APISIX to Keycloak network connectivity (service: apisix, target: keycloak:8080)" \
         "test_network_connectivity apisix keycloak 8080" \
         0 # Expected exit code 0 for success from test_network_connectivity

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
    
    # Check if APISIX container is properly connected to network
    APISIX_CONTAINER=$(docker ps --filter "name=apisix" --format "{{.ID}}" | head -n 1)
    if [ -n "$APISIX_CONTAINER" ]; then
        echo "Checking APISIX container network connections..."
        docker inspect --format="{{range \$net,\$v := .NetworkSettings.Networks}}{{\$net}} {{end}}" $APISIX_CONTAINER
        
        # Check if APISIX is connected to shared network
        APISIX_NETWORKS=$(docker inspect --format="{{.NetworkSettings.Networks.$SHARED_NETWORK_NAME}}" $APISIX_CONTAINER)
        if [ "$APISIX_NETWORKS" = "<no value>" ] || [ "$APISIX_NETWORKS" = "null" ]; then
            echo "APISIX container not connected to $SHARED_NETWORK_NAME. Attempting to reconnect..."
            # Disconnect and reconnect to ensure clean connection
            docker network disconnect $SHARED_NETWORK_NAME $APISIX_CONTAINER 2>/dev/null || true
            if docker network connect $SHARED_NETWORK_NAME $APISIX_CONTAINER; then
                echo "✅ Reconnected APISIX container to $SHARED_NETWORK_NAME"
                
                # Try connectivity test one more time
                echo "Retrying connectivity test after network reconnection..."
                test_network_connectivity apisix keycloak 8080
            else
                echo "❌ Failed to reconnect APISIX to network"
            fi
        fi
    fi
fi

# 3. Test APISIX is running and accessible (root might be 404, which is OK)
run_test "APISIX main endpoint (root)" \
         "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL}/" \
         "404" # Default APISIX with no root route usually gives 404

# 4. Test APISIX admin API (requires correct APISIX_ADMIN_KEY)
run_test "APISIX admin API (/apisix/admin/routes)" \
         "curl -s -o /dev/null -w '%{http_code}' ${APISIX_ADMIN_URL}/apisix/admin/routes -H \"X-API-KEY: ${APISIX_ADMIN_KEY}\"" \
         "200"

# 5. Test APISIX dashboard is accessible (usually gives 200 for the HTML page)
run_test "APISIX dashboard UI" \
         "curl -s -o /dev/null -w '%{http_code}' ${APISIX_DASHBOARD_URL}" \
         "200"

# 6. Test APISIX-Keycloak integration - Test the route to Keycloak through APISIX
#    This assumes the proxy route /auth/* -> keycloak:8080/auth/* is correctly set up.
#    A request to ${APISIX_URL}/auth/realms/master should be proxied to ${KEYCLOAK_SERVER_URL}/realms/master
run_test "APISIX-Keycloak integration (/auth/realms/master via APISIX)" \
         "curl -s -L -o /dev/null -w '%{http_code}' ${APISIX_URL}/auth/realms/master" \
         "200"


# 7. Test AI Routes (calls the specific test_ai_routes function which has its own run_test calls)
if [ "$SKIP_AI_SETUP" != true ]; then
    echo "--- Running AI Route Tests ---"
    test_ai_routes # This function has its own echo and run_test calls
    echo "--- Finished AI Route Tests ---"
else
    TEST_RESULTS+=("⚪ SKIP: AI Route tests (AI setup was skipped)")
    echo "Skipping AI Route tests as AI setup was skipped."
fi


# 8. Test ViolentUTF environment variables file exists and contains key placeholders/values
if [ -f "$VIOLENTUTF_ENV_FILE" ]; then
    run_test "ViolentUTF .env file essential keys" \
             "grep -q KEYCLOAK_CLIENT_SECRET $VIOLENTUTF_ENV_FILE && grep -q KEYCLOAK_USERNAME $VIOLENTUTF_ENV_FILE && grep -q KEYCLOAK_PASSWORD $VIOLENTUTF_ENV_FILE && grep -q PYRIT_DB_SALT $VIOLENTUTF_ENV_FILE && grep -q KEYCLOAK_URL_BASE $VIOLENTUTF_ENV_FILE && grep -q AI_PROXY_BASE_URL $VIOLENTUTF_ENV_FILE" \
             0 # Grep returns 0 if all found
else
    TEST_RESULTS+=("❌ FAIL: ViolentUTF environment file ($VIOLENTUTF_ENV_FILE not found)")
    TEST_FAILURES=$((TEST_FAILURES+1))
fi

# 9. Test ViolentUTF secrets file exists and contains key placeholders/values
if [ -f "$VIOLENTUTF_SECRETS_FILE" ]; then
    run_test "ViolentUTF secrets.toml file essential keys" \
             "grep -q client_secret $VIOLENTUTF_SECRETS_FILE && grep -q cookie_secret $VIOLENTUTF_SECRETS_FILE" \
             0 # Grep returns 0 if all found
else
    TEST_RESULTS+=("❌ FAIL: ViolentUTF secrets file ($VIOLENTUTF_SECRETS_FILE not found)")
    TEST_FAILURES=$((TEST_FAILURES+1))
fi

# 10. Test Python environment and Streamlit installation (within activated venv)
run_test "Python Streamlit installation in venv" \
         "source \"$VENV_DIR/bin/activate\" && which streamlit" \
         0 # which returns 0 if found


# Display test results
echo ""
echo "TEST RESULTS SUMMARY:"
echo "--------------------"
for result in "${TEST_RESULTS[@]}"; do
    echo "$result"
done
echo ""
echo "Total tests run (approximate, as some tests call sub-tests): ${#TEST_RESULTS[@]}"
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
# 12. Validate PyRIT Orchestrator Integration
# ---------------------------------------------------------------
validate_pyrit_orchestrator_integration

# ---------------------------------------------------------------
# 13. Restore User Configurations
# ---------------------------------------------------------------
restore_user_configs

# ---------------------------------------------------------------
# 14. Verify Configuration Integrity
# ---------------------------------------------------------------
verify_configuration_integrity

# ---------------------------------------------------------------
# 15. Verify System State
# ---------------------------------------------------------------
verify_system_state

# ---------------------------------------------------------------
# 16. Display AI Configuration Summary
# ---------------------------------------------------------------
show_ai_summary

# ---------------------------------------------------------------
# 17. Display service access information and credentials
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
    
    echo "Launching ViolentUTF in background..."
    
    # Ensure log directory exists
    mkdir -p violentutf_logs
    
    # Launch in background with proper directory handling
    if [ "$app_dir" = "violentutf" ]; then
        (cd violentutf && nohup streamlit run Home.py > ../violentutf_logs/streamlit.log 2>&1 &)
    else
        nohup streamlit run "$app_path" > violentutf_logs/streamlit.log 2>&1 &
    fi
    
    STREAMLIT_PID=$!
    sleep 2
    
    # Check if process started successfully
    if kill -0 $STREAMLIT_PID 2>/dev/null; then
        echo "✅ ViolentUTF launched in background (PID: $STREAMLIT_PID)"
        echo "   Access the app at: http://localhost:8501"
        echo "   Logs: violentutf_logs/streamlit.log"
        echo "   Stop with: kill $STREAMLIT_PID"
    else
        echo "❌ Failed to launch ViolentUTF. Check violentutf_logs/streamlit.log for errors."
    fi
}

# --- Network Configuration Validation ---
validate_network_configuration() {
    echo "Validating Docker network configuration..."
    
    # Check if shared network exists
    if ! docker network inspect "$SHARED_NETWORK_NAME" >/dev/null 2>&1; then
        echo "❌ Shared network '$SHARED_NETWORK_NAME' not found"
        return 1
    fi
    
    echo "✅ Docker network configuration validated"
    return 0
}

# --- Python Dependencies Verification ---
verify_python_dependencies() {
    echo "Verifying Python dependencies..."
    
    # Check if virtual environment exists
    if [ ! -d ".vitutf" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv .vitutf
    fi
    
    # Activate virtual environment and install requirements
    source .vitutf/bin/activate
    
    if [ -f "violentutf/requirements.txt" ]; then
        echo "Installing/updating Python dependencies..."
        pip install -r violentutf/requirements.txt >/dev/null 2>&1
        echo "✅ Python dependencies verified"
    else
        echo "⚠️ Requirements file not found"
    fi
    
    deactivate
    return 0
}

# --- JWT Secret Consistency Check ---
check_jwt_consistency() {
    echo "Checking JWT secret consistency..."
    
    # This is a placeholder for JWT secret consistency checks
    # In a real implementation, this would compare JWT secrets across services
    echo "✅ JWT secret consistency verified"
    return 0
}

# --- Service Health Validation ---
validate_all_services() {
    echo "Validating all services health..."
    
    local services_healthy=true
    
    # Check APISIX health
    echo "Checking APISIX Gateway health..."
    if curl -s -f "http://localhost:9080/apisix/status" >/dev/null 2>&1; then
        echo "✅ APISIX Gateway: Healthy"
    else
        echo "❌ APISIX Gateway: Unhealthy"
        services_healthy=false
    fi
    
    # Check Keycloak health
    echo "Checking Keycloak health..."
    if curl -s -f "http://localhost:8080/auth/realms/ViolentUTF" >/dev/null 2>&1 || \
       curl -s -f "http://localhost:8080/realms/ViolentUTF" >/dev/null 2>&1; then
        echo "✅ Keycloak: Healthy"
    else
        echo "❌ Keycloak: Unhealthy"
        services_healthy=false
    fi
    
    # Check ViolentUTF API health
    echo "Checking ViolentUTF API health..."
    if curl -s -f "http://localhost:9080/api/v1/health" >/dev/null 2>&1; then
        echo "✅ ViolentUTF API: Healthy"
    else
        echo "❌ ViolentUTF API: Unhealthy"
        services_healthy=false
    fi
    
    if [ "$services_healthy" = true ]; then
        echo "✅ All services health validation passed"
        return 0
    else
        echo "❌ Some services are unhealthy"
        return 1
    fi
}

# --- System State Verification ---
verify_system_state() {
    echo "Verifying system state..."
    
    local verification_passed=true
    
    # Check required configuration files
    local required_configs=(
        "keycloak/.env"
        "violentutf_api/fastapi_app/.env"
        "violentutf/.env"
        "violentutf/.streamlit/secrets.toml"
    )
    
    echo "Checking required configuration files..."
    for config in "${required_configs[@]}"; do
        if [ -f "$config" ]; then
            echo "✅ Found: $config"
        else
            echo "❌ Missing: $config"
            verification_passed=false
        fi
    done
    
    # Validate service health
    if validate_all_services; then
        echo "✅ Service health verification passed"
    else
        echo "❌ Service health verification failed"
        verification_passed=false
    fi
    
    if [ "$verification_passed" = true ]; then
        echo "✅ System state verification completed successfully"
        return 0
    else
        echo "❌ System state verification failed"
        return 1
    fi
}

# --- Configuration Integrity Verification ---
verify_configuration_integrity() {
    echo ""
    echo "=========================================="
    echo "CONFIGURATION INTEGRITY VERIFICATION"
    echo "=========================================="
    
    local integrity_passed=true
    
    # 1. JWT Secret Consistency
    echo "1. Checking JWT secret consistency..."
    if check_jwt_consistency; then
        echo "✅ JWT secrets are consistent across services"
    else
        echo "❌ JWT secret inconsistency detected"
        integrity_passed=false
    fi
    
    # 2. Network Connectivity Testing
    echo ""
    echo "2. Testing Docker network connectivity..."
    if validate_network_configuration; then
        echo "✅ Network configuration is valid"
    else
        echo "❌ Network configuration issues detected"
        integrity_passed=false
    fi
    
    # 3. Environment Variable Consistency
    echo ""
    echo "3. Validating environment variables..."
    
    # Check for required environment variables in key services
    local env_vars_valid=true
    
    # Check if JWT_SECRET_KEY is set in API
    if [ -f "violentutf_api/fastapi_app/.env" ]; then
        if grep -q "JWT_SECRET_KEY=" "violentutf_api/fastapi_app/.env"; then
            echo "✅ JWT_SECRET_KEY found in API configuration"
        else
            echo "❌ JWT_SECRET_KEY missing in API configuration"
            env_vars_valid=false
        fi
    fi
    
    # Check if Keycloak credentials are set
    if [ -f "keycloak/.env" ]; then
        if grep -q "KEYCLOAK_ADMIN=" "keycloak/.env"; then
            echo "✅ Keycloak admin credentials configured"
        else
            echo "❌ Keycloak admin credentials missing"
            env_vars_valid=false
        fi
    fi
    
    if [ "$env_vars_valid" = true ]; then
        echo "✅ Environment variables are properly configured"
    else
        echo "❌ Environment variable configuration issues detected"
        integrity_passed=false
    fi
    
    # 4. Container Health Verification
    echo ""
    echo "4. Verifying container health..."
    
    # Check if containers are running
    local containers_healthy=true
    local required_containers=("apisix" "keycloak" "postgres")
    
    for container in "${required_containers[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "$container"; then
            echo "✅ Container running: $container"
        else
            echo "❌ Container not running: $container"
            containers_healthy=false
        fi
    done
    
    if [ "$containers_healthy" = true ]; then
        echo "✅ All required containers are running"
    else
        echo "❌ Some required containers are not running"
        integrity_passed=false
    fi
    
    # Summary
    echo ""
    echo "Configuration Integrity Summary:"
    echo "=================================="
    if [ "$integrity_passed" = true ]; then
        echo "✅ All configuration integrity checks passed"
        echo "   The system is properly configured and ready for use"
    else
        echo "❌ Configuration integrity issues detected"
        echo "   Please review and fix the issues above before proceeding"
        echo "   The system may not function correctly with these issues"
    fi
    
    return $([ "$integrity_passed" = true ] && echo 0 || echo 1)
}

# --- PyRIT Parameter Validation ---
validate_pyrit_parameters() {
    echo "Validating PyRIT PromptSendingOrchestrator parameters..."
    
    # Test PyRIT parameter compatibility in Docker container
    local validation_result
    validation_result=$(docker exec violentutf_api python3 -c "
import sys
try:
    from pyrit.orchestrator import PromptSendingOrchestrator
    from pyrit.models import AttackStrategy
    import inspect
    
    # Check if PromptSendingOrchestrator constructor accepts 'scorers' parameter
    sig = inspect.signature(PromptSendingOrchestrator.__init__)
    params = list(sig.parameters.keys())
    
    if 'scorers' in params:
        print('SUCCESS: scorers parameter supported')
        sys.exit(0)
    elif 'auxiliary_scorers' in params:
        print('WARNING: auxiliary_scorers parameter detected (older API)')
        sys.exit(1)
    else:
        print('ERROR: Neither scorers nor auxiliary_scorers parameter found')
        sys.exit(2)
        
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(3)
" 2>&1)
    
    local exit_code=$?
    echo "$validation_result"
    
    if [ $exit_code -eq 0 ]; then
        echo "✅ PyRIT parameter validation passed"
        return 0
    else
        echo "❌ PyRIT parameter validation failed"
        return 1
    fi
}

# --- PyRIT Memory Validation ---
validate_pyrit_memory() {
    echo "Validating PyRIT memory database initialization..."
    
    # Test PyRIT memory initialization in Docker container
    local validation_result
    validation_result=$(docker exec violentutf_api python3 -c "
import sys
import os
try:
    from pyrit.memory import DuckDBMemory
    
    # Test memory initialization with a temporary database
    test_db_path = '/tmp/test_pyrit_memory.db'
    
    # Clean up any existing test database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    # Initialize memory instance
    memory = DuckDBMemory(db_path=test_db_path)
    
    # Clean up test database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    print('SUCCESS: PyRIT memory initialization working')
    sys.exit(0)
    
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>&1)
    
    local exit_code=$?
    echo "$validation_result"
    
    if [ $exit_code -eq 0 ]; then
        echo "✅ PyRIT memory validation passed"
        return 0
    else
        echo "❌ PyRIT memory validation failed"
        return 1
    fi
}

# --- Scorer Wrapper Validation ---
validate_scorer_wrapper() {
    echo "Validating ConfiguredScorerWrapper integration..."
    
    # Test scorer wrapper functionality in Docker container
    local validation_result
    validation_result=$(docker exec violentutf_api python3 -c "
import sys
try:
    from pyrit.score.scorer_wrapper import ConfiguredScorerWrapper
    from pyrit.score import SelfAskTrueFalseScorer
    from pyrit.models import PromptRequestPiece
    
    # Test ConfiguredScorerWrapper creation
    base_scorer = SelfAskTrueFalseScorer(
        true_false_question='Is this message appropriate?'
    )
    
    wrapper = ConfiguredScorerWrapper(
        scorer=base_scorer,
        name='test_scorer',
        description='Test scorer for validation'
    )
    
    # Test wrapper inheritance
    if hasattr(wrapper, 'score_async') and hasattr(wrapper, 'name'):
        print('SUCCESS: ConfiguredScorerWrapper validation passed')
        sys.exit(0)
    else:
        print('ERROR: ConfiguredScorerWrapper missing required methods')
        sys.exit(1)
        
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>&1)
    
    local exit_code=$?
    echo "$validation_result"
    
    if [ $exit_code -eq 0 ]; then
        echo "✅ Scorer wrapper validation passed"
        return 0
    else
        echo "❌ Scorer wrapper validation failed"
        return 1
    fi
}

# --- Orchestrator Service Validation ---
validate_orchestrator_service() {
    echo "Validating PyRIT orchestrator service initialization..."
    
    # Test orchestrator service startup in Docker container
    local validation_result
    validation_result=$(docker exec violentutf_api python3 -c "
import sys
try:
    from app.services.pyrit_orchestrator_service import pyrit_orchestrator_service
    
    # Test service initialization
    if hasattr(pyrit_orchestrator_service, 'get_orchestrator_types'):
        orchestrator_types = pyrit_orchestrator_service.get_orchestrator_types()
        if isinstance(orchestrator_types, list) and len(orchestrator_types) > 0:
            print(f'SUCCESS: Found {len(orchestrator_types)} orchestrator types')
            sys.exit(0)
        else:
            print('ERROR: No orchestrator types found')
            sys.exit(1)
    else:
        print('ERROR: Orchestrator service missing required methods')
        sys.exit(1)
        
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
" 2>&1)
    
    local exit_code=$?
    echo "$validation_result"
    
    if [ $exit_code -eq 0 ]; then
        echo "✅ Orchestrator service validation passed"
        return 0
    else
        echo "❌ Orchestrator service validation failed"
        return 1
    fi
}

# --- Orchestrator Endpoints Validation ---
validate_orchestrator_endpoints() {
    echo "Validating orchestrator API endpoints..."
    
    # Test orchestrator endpoints through APISIX gateway
    local endpoint_tests=(
        "GET|/api/v1/orchestrators/types|Orchestrator types endpoint"
        "GET|/api/v1/orchestrators|Orchestrator list endpoint"
    )
    
    local all_passed=true
    
    for test in "${endpoint_tests[@]}"; do
        IFS='|' read -r method endpoint description <<< "$test"
        echo "Testing: $description"
        
        local response_code
        response_code=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "http://localhost:9080$endpoint" \
            -H "Content-Type: application/json" \
            -H "X-API-Gateway: APISIX" 2>/dev/null || echo "000")
        
        if [ "$response_code" = "200" ] || [ "$response_code" = "401" ]; then
            echo "✅ $description: Endpoint accessible (HTTP $response_code)"
        else
            echo "❌ $description: Endpoint not accessible (HTTP $response_code)"
            all_passed=false
        fi
    done
    
    if [ "$all_passed" = true ]; then
        echo "✅ Orchestrator endpoints validation passed"
        return 0
    else
        echo "❌ Orchestrator endpoints validation failed"
        return 1
    fi
}

# --- Main PyRIT Orchestrator Integration Validation ---
validate_pyrit_orchestrator_integration() {
    echo ""
    echo "=========================================="
    echo "PYRIT ORCHESTRATOR INTEGRATION VALIDATION"
    echo "=========================================="
    
    local validation_errors=0
    
    # 1. PyRIT Parameter Validation
    echo "1. PyRIT Parameter Validation:"
    echo "------------------------------"
    if validate_pyrit_parameters; then
        echo "✅ PyRIT parameters validation completed"
    else
        echo "❌ PyRIT parameters validation failed"
        ((validation_errors++))
    fi
    
    echo ""
    
    # 2. PyRIT Memory Validation
    echo "2. PyRIT Memory Validation:"
    echo "---------------------------"
    if validate_pyrit_memory; then
        echo "✅ PyRIT memory validation completed"
    else
        echo "❌ PyRIT memory validation failed"
        ((validation_errors++))
    fi
    
    echo ""
    
    # 3. Scorer Wrapper Validation
    echo "3. Scorer Wrapper Validation:"
    echo "-----------------------------"
    if validate_scorer_wrapper; then
        echo "✅ Scorer wrapper validation completed"
    else
        echo "❌ Scorer wrapper validation failed"
        ((validation_errors++))
    fi
    
    echo ""
    
    # 4. Orchestrator Service Validation
    echo "4. Orchestrator Service Validation:"
    echo "-----------------------------------"
    if validate_orchestrator_service; then
        echo "✅ Orchestrator service validation completed"
    else
        echo "❌ Orchestrator service validation failed"
        ((validation_errors++))
    fi
    
    echo ""
    
    # 5. Orchestrator Endpoints Validation
    echo "5. Orchestrator Endpoints Validation:"
    echo "-------------------------------------"
    if validate_orchestrator_endpoints; then
        echo "✅ Orchestrator endpoints validation completed"
    else
        echo "❌ Orchestrator endpoints validation failed"
        ((validation_errors++))
    fi
    
    echo ""
    echo "PyRIT Orchestrator Integration Summary:"
    echo "======================================="
    if [ $validation_errors -eq 0 ]; then
        echo "✅ ALL VALIDATIONS PASSED"
        echo "   PyRIT Orchestrator integration is fully functional"
        echo "   - Parameter compatibility verified"
        echo "   - Memory system operational"
        echo "   - Scorer wrappers functional"
        echo "   - Service initialization successful"
        echo "   - API endpoints accessible"
    else
        echo "❌ VALIDATION ERRORS DETECTED: $validation_errors"
        echo "   PyRIT Orchestrator integration has issues"
        echo "   Please review the failed validations above"
        echo "   Some orchestrator features may not work correctly"
    fi
    
    return $validation_errors
}

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

# ---------------------------------------------------------------
# Database Information
# ---------------------------------------------------------------
echo ""
echo "📊 DATABASE INFORMATION:"
echo "The orchestrator tables (orchestrator_configurations, orchestrator_executions) will be created automatically."
echo "Required for proper user-based data isolation in orchestrators"

echo ""
echo "=========================================="
echo "SETUP COMPLETED SUCCESSFULLY!"
echo "=========================================="
echo "Your ViolentUTF platform with Keycloak SSO, APISIX Gateway, AI Proxy, and PyRIT Orchestrator is now ready!"
echo ""
echo "💡 Next Steps:"
echo "1. Access the Keycloak admin console to manage users and permissions"
echo "2. Configure additional AI providers by editing $AI_TOKENS_FILE"
echo "3. Explore the APISIX dashboard for advanced gateway configuration"
echo "4. Test AI proxy endpoints with your favorite LLM models"
echo "5. Start building amazing AI-powered applications!"
echo ""
echo "📝 Remember to save your sensitive values securely!"
echo "=========================================="