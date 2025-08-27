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
