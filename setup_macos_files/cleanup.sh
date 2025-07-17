#!/usr/bin/env bash
# cleanup.sh - Cleanup and maintenance operations

# Function to perform cleanup
perform_cleanup() {
    echo "Starting cleanup process..."
    
    # 0. Backup user configurations before cleanup
    backup_user_configs
    
    # 1. Gracefully shutdown ViolentUTF Streamlit server
    graceful_streamlit_shutdown
    
    # 2. Stop and remove containers
    cleanup_containers
    
    # 3. Remove configuration files but preserve directories
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
        find "apisix/conf" -name "*.template" -exec cp {} "/tmp/apisix_templates/" \; 2>/dev/null || true
        
        # Remove all config files
        rm -rf "apisix/conf/"*
        
        # Move templates back
        mkdir -p "apisix/conf"
        cp "/tmp/apisix_templates/"* "apisix/conf/" 2>/dev/null || true
        rm -rf "/tmp/apisix_templates"
        echo "Cleaned apisix/conf/ (preserved templates)"
    fi
    
    # Remove APISIX .env
    if [ -f "apisix/.env" ]; then
        rm "apisix/.env"
        echo "Removed apisix/.env"
    fi
    
    # ViolentUTF files
    if [ -f "violentutf/.env" ]; then
        rm "violentutf/.env"
        echo "Removed violentutf/.env"
    fi
    
    # FastAPI files
    if [ -f "violentutf_api/fastapi_app/.env" ]; then
        rm "violentutf_api/fastapi_app/.env"
        echo "Removed violentutf_api/fastapi_app/.env"
    fi
    
    echo "✅ Standard cleanup completed"
    echo "📝 User configurations (AI tokens, app data) have been preserved"
}

# Function to perform deep cleanup
perform_deep_cleanup() {
    echo "⚠️  Starting DEEP cleanup process..."
    echo "This will remove ALL Docker data on your system!"
    
    # Backup user configurations first
    backup_user_configs
    
    # Perform deep Docker cleanup
    deep_cleanup_docker
    
    # Remove all configuration files (including user data)
    echo "Removing ALL configuration files..."
    
    # Remove all .env files
    find . -name ".env" -type f -delete 2>/dev/null || true
    
    # Remove all generated config files
    find apisix/conf -type f ! -name "*.template" -delete 2>/dev/null || true
    
    # Remove logs
    rm -rf violentutf_logs/ 2>/dev/null || true
    rm -rf apisix/logs/ 2>/dev/null || true
    rm -rf tmp/ 2>/dev/null || true
    
    # Remove backup files
    find . -name "*.bak*" -type f -delete 2>/dev/null || true
    
    echo "✅ Deep cleanup completed"
    echo "⚠️  ALL Docker data and configuration files have been removed!"
    echo "📝 User configurations have been backed up and can be restored on next setup"
}

# Function to cleanup specific service
cleanup_specific_service() {
    local service_name="$1"
    echo "Cleaning up specific service: $service_name"
    
    case "$service_name" in
        "keycloak")
            cleanup_keycloak_service
            ;;
        "apisix")
            cleanup_apisix_service
            ;;
        "violentutf"|"api")
            cleanup_violentutf_service
            ;;
        *)
            echo "Unknown service: $service_name"
            echo "Available services: keycloak, apisix, violentutf"
            return 1
            ;;
    esac
}

# Helper function to cleanup Keycloak service
cleanup_keycloak_service() {
    echo "Cleaning up Keycloak service..."
    
    local original_dir=$(pwd)
    
    if [ -d "keycloak" ]; then
        cd "keycloak" || return 1
        ${DOCKER_COMPOSE_CMD:-docker-compose} down -v 2>/dev/null || true
        rm -f .env
        cd "$original_dir"
        echo "✅ Keycloak service cleaned up"
    else
        echo "Keycloak directory not found"
    fi
}

# Helper function to cleanup APISIX service
cleanup_apisix_service() {
    echo "Cleaning up APISIX service..."
    
    local original_dir=$(pwd)
    
    if [ -d "apisix" ]; then
        cd "apisix" || return 1
        ${DOCKER_COMPOSE_CMD:-docker-compose} down -v 2>/dev/null || true
        rm -f .env
        
        # Clean config files but preserve templates
        if [ -d "conf" ]; then
            find conf -type f ! -name "*.template" -delete 2>/dev/null || true
        fi
        
        cd "$original_dir"
        echo "✅ APISIX service cleaned up"
    else
        echo "APISIX directory not found"
    fi
}

# Helper function to cleanup ViolentUTF service
cleanup_violentutf_service() {
    echo "Cleaning up ViolentUTF service..."
    
    # Gracefully shutdown Streamlit
    graceful_streamlit_shutdown
    
    # Remove environment files
    rm -f violentutf/.env
    rm -f violentutf_api/fastapi_app/.env
    
    echo "✅ ViolentUTF service cleaned up"
}

# Function to perform dashboard data cleanup
perform_dashboard_cleanup() {
    echo "🧹 Starting dashboard data cleanup..."
    echo "This will remove PyRIT memory databases, scores, and execution history"
    
    # Ask for confirmation unless in quiet mode
    if [ "${VUTF_VERBOSITY:-1}" -ge 1 ]; then
        echo ""
        echo "⚠️  WARNING: This will permanently delete:"
        echo "   - All PyRIT memory databases (conversation history)"
        echo "   - All scoring results and execution data"
        echo "   - All orchestrator execution history"
        echo "   - All dashboard analytics data"
        echo ""
        read -p "Are you sure you want to continue? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Dashboard cleanup cancelled."
            return 0
        fi
    fi
    
    # 1. Clean up PyRIT memory databases
    cleanup_pyrit_databases
    
    # 2. Clean up FastAPI application databases
    cleanup_fastapi_databases
    
    # 3. Clean up Streamlit app data
    cleanup_streamlit_app_data
    
    # 4. Clean up logs related to executions
    cleanup_execution_logs
    
    # 5. Restart containers to ensure clean state
    restart_containers_for_clean_state
    
    echo "✅ Dashboard data cleanup completed"
    echo "📊 All scoring results, execution history, and memory databases have been removed"
    echo "🔄 Containers restarted to ensure clean application state"
}

# Helper function to cleanup PyRIT memory databases
cleanup_pyrit_databases() {
    echo "Cleaning up PyRIT memory databases..."
    
    # Find and remove PyRIT memory database files
    local db_patterns=(
        "pyrit_memory_*.db"
        "orchestrator_memory_*.db"
        "*memory*.db"
        "*pyrit*.db"
    )
    
    local cleaned_count=0
    
    # 1. Clean host filesystem locations
    local search_paths=(
        "violentutf/app_data/violentutf"
        "violentutf_api/fastapi_app/app_data"
        "violentutf_api/fastapi_app/app_data/violentutf"
        "app_data"
        "."
    )
    
    for search_path in "${search_paths[@]}"; do
        if [ -d "$search_path" ]; then
            echo "  Checking host $search_path for PyRIT databases..."
            
            for pattern in "${db_patterns[@]}"; do
                local found_files
                found_files=$(find "$search_path" -name "$pattern" -type f 2>/dev/null)
                
                if [ -n "$found_files" ]; then
                    while IFS= read -r db_file; do
                        if [ -f "$db_file" ]; then
                            rm -f "$db_file"
                            echo "    Removed host file: $db_file"
                            ((cleaned_count++))
                        fi
                    done <<< "$found_files"
                fi
            done
            
            # Also remove WAL and SHM files (SQLite auxiliary files)
            find "$search_path" -name "*.db-wal" -o -name "*.db-shm" -type f -delete 2>/dev/null || true
        fi
    done
    
    # 2. Clean database files inside running containers
    cleanup_container_databases
    
    if [ $cleaned_count -eq 0 ]; then
        echo "  No PyRIT database files found to clean"
    else
        echo "  Cleaned $cleaned_count PyRIT database files"
    fi
}

# Helper function to cleanup databases inside Docker containers
cleanup_container_databases() {
    echo "  Cleaning databases inside running containers..."
    
    # Check if FastAPI container is running
    if docker ps --format "{{.Names}}" | grep -q "violentutf_api"; then
        echo "    Cleaning FastAPI container databases..."
        
        # Find and remove database files inside the container
        local container_db_files
        container_db_files=$(docker exec violentutf_api find /app -name "*.db" -o -name "*.db-*" -type f 2>/dev/null || true)
        
        if [ -n "$container_db_files" ]; then
            while IFS= read -r db_file; do
                if [ -n "$db_file" ]; then
                    docker exec violentutf_api rm -f "$db_file" 2>/dev/null || true
                    echo "      Removed container file: $db_file"
                    ((cleaned_count++))
                fi
            done <<< "$container_db_files"
        fi
        
        # Clean PyRIT memory directories inside container
        docker exec violentutf_api find /app/app_data -name "*memory*" -type d -exec rm -rf {} + 2>/dev/null || true
        docker exec violentutf_api find /app/app_data -name "*pyrit*" -type d -exec rm -rf {} + 2>/dev/null || true
        
        # Clean temporary and cache files
        docker exec violentutf_api find /app -name "*.tmp" -o -name "temp_*" -type f -delete 2>/dev/null || true
        docker exec violentutf_api find /app/app_data -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
        
        echo "    FastAPI container databases cleaned"
    else
        echo "    FastAPI container not running, skipping container cleanup"
    fi
    
    # Check for other ViolentUTF containers that might have data
    local other_containers
    other_containers=$(docker ps --format "{{.Names}}" | grep -E "(streamlit|violentutf)" | grep -v "violentutf_api" || true)
    
    if [ -n "$other_containers" ]; then
        while IFS= read -r container_name; do
            if [ -n "$container_name" ]; then
                echo "    Cleaning $container_name container..."
                docker exec "$container_name" find / -name "*.db" -o -name "*memory*.db" -type f -delete 2>/dev/null || true
            fi
        done <<< "$other_containers"
    fi
}

# Helper function to cleanup FastAPI application databases
cleanup_fastapi_databases() {
    echo "Cleaning up FastAPI application databases..."
    
    local cleaned_count=0
    
    # FastAPI SQLite databases
    local fastapi_db_patterns=(
        "violentutf.db"
        "violentutf_api.db"
        "app.db"
        "fastapi.db"
    )
    
    local fastapi_paths=(
        "violentutf_api/fastapi_app"
        "violentutf_api/fastapi_app/app_data"
        "."
    )
    
    for search_path in "${fastapi_paths[@]}"; do
        if [ -d "$search_path" ]; then
            for pattern in "${fastapi_db_patterns[@]}"; do
                local db_file="$search_path/$pattern"
                if [ -f "$db_file" ]; then
                    rm -f "$db_file"
                    echo "    Removed: $db_file"
                    ((cleaned_count++))
                    
                    # Remove associated WAL and SHM files
                    rm -f "${db_file}-wal" "${db_file}-shm" 2>/dev/null || true
                fi
            done
        fi
    done
    
    if [ $cleaned_count -eq 0 ]; then
        echo "  No FastAPI database files found to clean"
    else
        echo "  Cleaned $cleaned_count FastAPI database files"
    fi
}

# Helper function to cleanup Streamlit app data
cleanup_streamlit_app_data() {
    echo "Cleaning up Streamlit app data..."
    
    local cleaned_items=0
    
    # Remove Streamlit session state and cache files
    local streamlit_paths=(
        "violentutf/.streamlit"
        ".streamlit"
        "violentutf/app_data"
    )
    
    for path in "${streamlit_paths[@]}"; do
        if [ -d "$path" ]; then
            # Remove cache and session files but preserve configuration
            find "$path" -name "*.cache" -o -name "session_*" -o -name "*.pkl" -type f -delete 2>/dev/null || true
            find "$path" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
            ((cleaned_items++))
        fi
    done
    
    # Remove temporary files
    find violentutf -name "*.tmp" -o -name "temp_*" -type f -delete 2>/dev/null || true
    
    if [ $cleaned_items -eq 0 ]; then
        echo "  No Streamlit app data found to clean"
    else
        echo "  Cleaned Streamlit app data from $cleaned_items locations"
    fi
}

# Helper function to cleanup execution logs
cleanup_execution_logs() {
    echo "Cleaning up execution logs..."
    
    local cleaned_count=0
    
    # Log file patterns related to executions and scoring
    local log_patterns=(
        "*execution*.log"
        "*scoring*.log"
        "*orchestrator*.log"
        "*pyrit*.log"
        "violentutf*.log"
    )
    
    local log_paths=(
        "violentutf_logs"
        "logs"
        "violentutf/logs"
        "violentutf_api/fastapi_app/logs"
        "."
    )
    
    for log_path in "${log_paths[@]}"; do
        if [ -d "$log_path" ]; then
            for pattern in "${log_patterns[@]}"; do
                local found_logs
                found_logs=$(find "$log_path" -name "$pattern" -type f 2>/dev/null)
                
                if [ -n "$found_logs" ]; then
                    while IFS= read -r log_file; do
                        if [ -f "$log_file" ]; then
                            rm -f "$log_file"
                            echo "    Removed: $log_file"
                            ((cleaned_count++))
                        fi
                    done <<< "$found_logs"
                fi
            done
        fi
    done
    
    if [ $cleaned_count -eq 0 ]; then
        echo "  No execution log files found to clean"
    else
        echo "  Cleaned $cleaned_count execution log files"
    fi
}

# Helper function to restart containers for clean state
restart_containers_for_clean_state() {
    echo "Restarting containers to ensure clean application state..."
    
    # Restart FastAPI container if running
    if docker ps --format "{{.Names}}" | grep -q "violentutf_api"; then
        echo "  Restarting FastAPI container..."
        docker restart violentutf_api >/dev/null 2>&1 || true
        
        # Wait for container to be healthy
        echo "  Waiting for FastAPI container to be ready..."
        local wait_count=0
        while [ $wait_count -lt 30 ]; do
            if docker exec violentutf_api curl -s http://localhost:8000/health >/dev/null 2>&1; then
                echo "  FastAPI container is ready"
                break
            fi
            sleep 2
            ((wait_count++))
        done
        
        if [ $wait_count -eq 30 ]; then
            echo "  Warning: FastAPI container may not be fully ready yet"
        fi
    fi
    
    # Kill any running Streamlit processes (since it runs on host)
    echo "  Stopping any running Streamlit processes..."
    pkill -f "streamlit.*violentutf" 2>/dev/null || true
    pkill -f "streamlit run Dashboard.py" 2>/dev/null || true
    pkill -f "streamlit run Home.py" 2>/dev/null || true
    
    # Give processes time to stop
    sleep 3
    
    # Restart Streamlit if it was running before
    restart_streamlit_if_needed
    
    echo "  Container restart completed"
}

# Helper function to restart Streamlit after cleanup
restart_streamlit_if_needed() {
    echo "  Restarting Streamlit application..."
    
    # Check if we're in the ViolentUTF directory or can find it
    local violentutf_dir=""
    if [ -d "violentutf" ]; then
        violentutf_dir="$(pwd)/violentutf"
    elif [ -d "../violentutf" ]; then
        violentutf_dir="$(cd .. && pwd)/violentutf"
    elif [ -f "Home.py" ]; then
        violentutf_dir="$(pwd)"
    else
        echo "    Warning: Cannot locate ViolentUTF Streamlit directory"
        echo "    You may need to manually restart Streamlit using:"
        echo "    ./launch_violentutf.sh"
        return 1
    fi
    
    echo "    Located ViolentUTF directory: $violentutf_dir"
    
    # Create a background launch script
    local restart_script="/tmp/restart_violentutf_streamlit.sh"
    cat > "$restart_script" <<EOF
#!/bin/bash
echo "🔄 Restarting ViolentUTF Streamlit after dashboard cleanup..."
cd "$violentutf_dir" || exit 1

# Activate virtual environment if it exists
if [ -d ".vitutf" ]; then
    source .vitutf/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Start Streamlit in background
nohup streamlit run Home.py --server.port=8501 --server.address=localhost --browser.gatherUsageStats=false > /tmp/streamlit_restart.log 2>&1 &

echo "✅ Streamlit restarted in background (PID: \$!)"
echo "🌐 Dashboard available at: http://localhost:8501"
EOF
    
    # Make script executable and run it
    chmod +x "$restart_script"
    bash "$restart_script" &
    
    # Give Streamlit time to start
    sleep 5
    
    # Check if Streamlit is running
    if pgrep -f "streamlit.*Home.py" >/dev/null 2>&1; then
        echo "    ✅ Streamlit successfully restarted"
        echo "    🌐 Dashboard available at: http://localhost:8501"
    else
        echo "    ⚠️  Streamlit restart may have failed"
        echo "    📝 Check /tmp/streamlit_restart.log for details"
        echo "    🔧 Manual restart: ./launch_violentutf.sh"
    fi
    
    # Clean up restart script
    rm -f "$restart_script"
}