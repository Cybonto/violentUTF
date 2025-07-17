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
    
    echo "✅ Dashboard data cleanup completed"
    echo "📊 All scoring results, execution history, and memory databases have been removed"
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
    
    # Check common PyRIT database locations
    local search_paths=(
        "violentutf/app_data/violentutf"
        "violentutf_api/fastapi_app/app_data"
        "violentutf_api/fastapi_app/app_data/violentutf"
        "app_data"
        "."
    )
    
    for search_path in "${search_paths[@]}"; do
        if [ -d "$search_path" ]; then
            echo "  Checking $search_path for PyRIT databases..."
            
            for pattern in "${db_patterns[@]}"; do
                local found_files
                found_files=$(find "$search_path" -name "$pattern" -type f 2>/dev/null)
                
                if [ -n "$found_files" ]; then
                    while IFS= read -r db_file; do
                        if [ -f "$db_file" ]; then
                            rm -f "$db_file"
                            echo "    Removed: $db_file"
                            ((cleaned_count++))
                        fi
                    done <<< "$found_files"
                fi
            done
            
            # Also remove WAL and SHM files (SQLite auxiliary files)
            find "$search_path" -name "*.db-wal" -o -name "*.db-shm" -type f -delete 2>/dev/null || true
        fi
    done
    
    if [ $cleaned_count -eq 0 ]; then
        echo "  No PyRIT database files found to clean"
    else
        echo "  Cleaned $cleaned_count PyRIT database files"
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