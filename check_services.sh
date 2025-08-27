#!/bin/bash

# ViolentUTF Services Status Checker

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "=========================================="
echo "📊 ViolentUTF Services Status"
echo "=========================================="
echo ""

# Function to check service
check_service() {
    local name=$1
    local check_command=$2

    echo -n "Checking $name... "

    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
        return 0
    else
        echo -e "${RED}✗ Not Running${NC}"
        return 1
    fi
}

# Function to check Docker container
check_container() {
    local name=$1
    local container=$2

    echo -n "Checking $name... "

    status=$(docker ps --filter "name=$container" --format "{{.Status}}" 2>/dev/null | head -1)

    if [ -n "$status" ]; then
        if [[ "$status" == *"healthy"* ]]; then
            echo -e "${GREEN}✓ Healthy${NC}"
        elif [[ "$status" == *"unhealthy"* ]]; then
            echo -e "${RED}✗ Unhealthy${NC}"
        else
            echo -e "${YELLOW}⚠ Running (health unknown)${NC}"
        fi
        return 0
    else
        echo -e "${RED}✗ Not Running${NC}"
        return 1
    fi
}

# Check Docker daemon
echo "Docker Services:"
echo "----------------"
check_service "Docker daemon" "docker info"

if [ $? -eq 0 ]; then
    # Check containers
    check_container "Keycloak" "keycloak"
    check_container "Keycloak DB" "keycloak-postgres"
    check_container "APISIX" "apisix"
    check_container "APISIX etcd" "etcd"
    check_container "FastAPI" "violentutf_api"
fi

echo ""
echo "Web Services:"
echo "-------------"

# Check web endpoints
check_service "Keycloak (8080)" "curl -s -o /dev/null -w '%{http_code}' http://localhost:8080 | grep -E '200|302|303'"
check_service "APISIX Gateway (9080)" "curl -s -o /dev/null -w '%{http_code}' http://localhost:9080 | grep -E '404|200'"
check_service "APISIX Admin (9180)" "curl -s -o /dev/null -w '%{http_code}' http://localhost:9180 | grep -E '401|200'"
check_service "Streamlit (8501)" "curl -s -o /dev/null -w '%{http_code}' http://localhost:8501 | grep -E '200|302'"

echo ""
echo "API Endpoints:"
echo "--------------"

# Check API endpoints
check_service "FastAPI Health" "curl -s http://localhost:9080/api/v1/health | grep -q healthy"
check_service "Keycloak OIDC" "curl -s http://localhost:8080/realms/ViolentUTF/.well-known/openid-configuration | grep -q issuer"

echo ""
echo "=========================================="

# Summary
total=$(docker ps -q | wc -l | tr -d ' ')
echo ""
echo "Summary: $total Docker containers running"

# Check for Streamlit process
if pgrep -f "streamlit run" > /dev/null; then
    echo -e "Streamlit app: ${GREEN}Running${NC} (PID: $(pgrep -f 'streamlit run'))"
else
    echo -e "Streamlit app: ${YELLOW}Not Running${NC}"
    echo "  Start with: ./launch_violentutf.sh"
fi

echo ""
