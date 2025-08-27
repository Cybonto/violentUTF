#!/bin/bash
# Script to wait for all services to be ready in CI environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
MAX_WAIT_TIME=300  # 5 minutes
SLEEP_INTERVAL=5

# Services to check
declare -A SERVICES=(
    ["Keycloak"]="http://localhost:8080/health/ready"
    ["APISIX"]="http://localhost:9091/apisix/admin/routes"
    ["FastAPI"]="http://localhost:8000/health"
    ["Streamlit"]="http://localhost:8501/"
)

# Function to check if a service is ready
check_service() {
    local name=$1
    local url=$2
    local response

    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")

    if [[ "$response" == "200" ]] || [[ "$response" == "401" ]] || [[ "$response" == "302" ]]; then
        return 0
    else
        return 1
    fi
}

# Function to wait for a service
wait_for_service() {
    local name=$1
    local url=$2
    local elapsed=0

    echo -e "${YELLOW}Waiting for $name to be ready...${NC}"

    while [ $elapsed -lt $MAX_WAIT_TIME ]; do
        if check_service "$name" "$url"; then
            echo -e "${GREEN}✓ $name is ready${NC}"
            return 0
        fi

        echo -n "."
        sleep $SLEEP_INTERVAL
        elapsed=$((elapsed + SLEEP_INTERVAL))
    done

    echo -e "\n${RED}✗ $name failed to become ready within ${MAX_WAIT_TIME}s${NC}"
    return 1
}

# Main execution
echo "=== Waiting for ViolentUTF services to be ready ==="
echo ""

# Track overall success
all_ready=true

# Check each service
for service in "${!SERVICES[@]}"; do
    if ! wait_for_service "$service" "${SERVICES[$service]}"; then
        all_ready=false
    fi
done

echo ""

# Additional checks for Docker services
if command -v docker &> /dev/null; then
    echo "=== Docker Service Status ==="
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
fi

# Summary
if $all_ready; then
    echo -e "${GREEN}All services are ready!${NC}"
    exit 0
else
    echo -e "${RED}Some services failed to become ready${NC}"

    # Print debugging information
    echo ""
    echo "=== Debugging Information ==="

    # Check Docker logs if available
    if command -v docker &> /dev/null; then
        echo "Recent Docker logs:"
        for container in $(docker ps -a --format "{{.Names}}"); do
            echo "--- $container ---"
            docker logs --tail 20 "$container" 2>&1 || true
            echo ""
        done
    fi

    # Check network connectivity
    echo "Network connectivity:"
    curl -s -o /dev/null -w "Keycloak: %{http_code}\n" http://localhost:8080 || echo "Keycloak: Failed"
    curl -s -o /dev/null -w "APISIX: %{http_code}\n" http://localhost:9080 || echo "APISIX: Failed"
    curl -s -o /dev/null -w "FastAPI: %{http_code}\n" http://localhost:8000 || echo "FastAPI: Failed"
    curl -s -o /dev/null -w "Streamlit: %{http_code}\n" http://localhost:8501 || echo "Streamlit: Failed"

    exit 1
fi
