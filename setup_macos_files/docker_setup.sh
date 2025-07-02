#!/usr/bin/env bash
# docker_setup.sh - Docker network creation and container management

# Function to create shared network
create_shared_network() {
    echo "Creating shared Docker network: $SHARED_NETWORK_NAME"
    
    # Check if network already exists
    if docker network inspect "$SHARED_NETWORK_NAME" >/dev/null 2>&1; then
        echo "✅ Network '$SHARED_NETWORK_NAME' already exists"
        return 0
    fi
    
    # Create the network
    if docker network create "$SHARED_NETWORK_NAME" >/dev/null 2>&1; then
        echo "✅ Created shared network '$SHARED_NETWORK_NAME'"
        return 0
    else
        echo "❌ Failed to create shared network '$SHARED_NETWORK_NAME'"
        return 1
    fi
}

# Function to verify Docker setup
verify_docker_setup() {
    echo "Verifying Docker setup..."
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null || ! docker ps &> /dev/null; then
        echo "❌ Docker daemon is not running or current user cannot connect to it."
        echo "Please start Docker Desktop and ensure it's running."
        exit 1
    fi
    
    # Check Docker Compose
    local compose_cmd=""
    if command -v docker-compose &> /dev/null; then
        compose_cmd="docker-compose"
    elif docker compose version &> /dev/null; then
        compose_cmd="docker compose"
    else
        echo "❌ Docker Compose not found. Please install Docker Compose."
        exit 1
    fi
    
    # Export for use in other modules
    export DOCKER_COMPOSE_CMD="$compose_cmd"
    
    echo "✅ Docker and Docker Compose check passed"
    echo "Using Docker Compose command: $compose_cmd"
}

# Function to cleanup containers
cleanup_containers() {
    echo "Cleaning up ViolentUTF containers..."
    
    # Remember current directory
    local original_dir=$(pwd)
    
    # Stop and remove Keycloak containers
    echo "Stopping Keycloak containers..."
    if [ -d "keycloak" ]; then
        cd "keycloak" || { echo "Failed to cd into keycloak directory"; exit 1; }
        ${DOCKER_COMPOSE_CMD:-docker-compose} down -v 2>/dev/null || true
        cd "$original_dir"
    fi
    
    # Stop and remove APISIX containers
    echo "Stopping APISIX containers..."
    if [ -d "apisix" ]; then
        cd "apisix" || { echo "Failed to cd into apisix directory"; exit 1; }
        ${DOCKER_COMPOSE_CMD:-docker-compose} down -v 2>/dev/null || true
        cd "$original_dir"
    fi
    
    # Remove shared network if it exists and is not in use
    echo "Removing shared Docker network..."
    if docker network inspect "$SHARED_NETWORK_NAME" >/dev/null 2>&1; then
        if docker network rm "$SHARED_NETWORK_NAME" >/dev/null 2>&1; then
            echo "✅ Removed shared network '$SHARED_NETWORK_NAME'"
        else
            echo "⚠️  Could not remove shared network '$SHARED_NETWORK_NAME'. It may still be in use."
        fi
    fi
    
    echo "✅ Container cleanup completed"
}

# Function to perform deep cleanup of Docker
deep_cleanup_docker() {
    echo "⚠️  Performing deep Docker cleanup - this will remove ALL Docker data!"
    
    # Graceful shutdown first
    graceful_streamlit_shutdown
    
    # Regular cleanup
    cleanup_containers
    
    # Deep clean everything
    echo "Removing all Docker containers..."
    docker container rm -f $(docker container ls -aq) 2>/dev/null || true
    
    echo "Removing all Docker images..."
    docker image rm -f $(docker image ls -aq) 2>/dev/null || true
    
    echo "Removing all Docker volumes..."
    docker volume rm $(docker volume ls -q) 2>/dev/null || true
    
    echo "Removing all Docker networks..."
    docker network rm $(docker network ls -q) 2>/dev/null || true
    
    echo "Pruning Docker system..."
    docker system prune -af --volumes 2>/dev/null || true
    
    echo "✅ Deep Docker cleanup completed"
    echo "⚠️  All Docker data has been removed from your system!"
}