#!/bin/bash
# Helper script for CI to handle multiple docker-compose files

set -e

# Function to start all services
start_services() {
    echo "Starting ViolentUTF services..."

    # Start services in order
    echo "1. Starting Keycloak..."
    docker compose -f keycloak/docker-compose.yml up -d

    echo "2. Starting APISIX..."
    docker compose -f apisix/docker-compose.yml up -d

    echo "3. Starting API..."
    docker compose -f violentutf_api/docker-compose.yml up -d

    echo "Services started. Waiting for health checks..."
    sleep 30
}

# Function to stop all services
stop_services() {
    echo "Stopping ViolentUTF services..."
    docker compose -f violentutf_api/docker-compose.yml down
    docker compose -f apisix/docker-compose.yml down
    docker compose -f keycloak/docker-compose.yml down
}

# Function to check service health
check_health() {
    echo "Checking service health..."
    ./scripts/wait-for-services.sh
}

# Main logic
case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    health)
        check_health
        ;;
    restart)
        stop_services
        start_services
        ;;
    *)
        echo "Usage: $0 {start|stop|health|restart}"
        exit 1
        ;;
esac
