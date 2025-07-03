#!/bin/bash

# Phase 2 Configuration Verification Script
# This script verifies APISIX_ADMIN_URL and container networking

set -e

echo "=== Phase 2: Core Configuration Verification ==="
echo

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# Check required commands
for cmd in docker; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}❌ Required command '$cmd' not found${NC}"
        exit 1
    fi
done

echo "Step 1: Verify APISIX_ADMIN_URL Configuration"
echo "============================================="

# Check if FastAPI container is running
if ! docker ps | grep -q violentutf_api; then
    print_status 1 "FastAPI container is not running"
    echo "Please start services with: cd apisix && docker compose up -d"
    exit 1
fi

# Check APISIX_ADMIN_URL in container
echo "Checking APISIX_ADMIN_URL in FastAPI container..."
admin_url=$(docker exec violentutf_api printenv APISIX_ADMIN_URL 2>/dev/null || echo "NOT SET")

if [ "$admin_url" = "NOT SET" ] || [ -z "$admin_url" ]; then
    print_status 1 "APISIX_ADMIN_URL is not set in container"
    echo "   This is critical for endpoint discovery"
elif [[ "$admin_url" == *"apisix"*":9180" ]]; then
    print_status 0 "APISIX_ADMIN_URL is set: $admin_url"
    
    # Determine the correct hostname
    if [[ "$admin_url" == "http://apisix:9180" ]]; then
        echo "   ⚠️  Using short hostname 'apisix'"
    elif [[ "$admin_url" == "http://apisix-apisix-1:9180" ]]; then
        echo "   ✓ Using full container name 'apisix-apisix-1'"
    fi
else
    print_status 1 "APISIX_ADMIN_URL has unexpected value: $admin_url"
fi

# Check .env file
echo
echo "Checking .env file configuration..."
if [ -f "violentutf_api/fastapi_app/.env" ]; then
    env_url=$(grep "^APISIX_ADMIN_URL=" violentutf_api/fastapi_app/.env | cut -d'=' -f2)
    if [ -n "$env_url" ]; then
        echo "   .env file has: $env_url"
    else
        echo "   .env file missing APISIX_ADMIN_URL"
    fi
fi

echo
echo "Step 2: Verify Container Networking"
echo "==================================="

# Check if containers are on vutf-network
echo "Checking Docker networks..."
fastapi_networks=$(docker inspect violentutf_api -f '{{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{end}}' 2>/dev/null)
apisix_networks=$(docker inspect apisix-apisix-1 -f '{{range $key, $value := .NetworkSettings.Networks}}{{$key}} {{end}}' 2>/dev/null || echo "")

if [[ "$fastapi_networks" == *"vutf-network"* ]]; then
    print_status 0 "FastAPI is on vutf-network"
else
    print_status 1 "FastAPI is NOT on vutf-network"
    echo "   Networks: $fastapi_networks"
fi

if [[ "$apisix_networks" == *"vutf-network"* ]] || [[ "$apisix_networks" == *"apisix_apisix_network"* ]]; then
    print_status 0 "APISIX is on shared network"
else
    print_status 1 "APISIX network configuration issue"
    echo "   Networks: $apisix_networks"
fi

# Test connectivity with both possible hostnames
echo
echo "Testing connectivity from FastAPI to APISIX admin..."

# Try short hostname first
test_short=$(docker exec violentutf_api sh -c 'curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://apisix:9180/apisix/admin/health 2>/dev/null' || echo "000")

# Try full container name
test_full=$(docker exec violentutf_api sh -c 'curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://apisix-apisix-1:9180/apisix/admin/health 2>/dev/null' || echo "000")

if [ "$test_short" = "200" ]; then
    print_status 0 "Can reach APISIX admin via 'apisix:9180'"
else
    print_status 1 "Cannot reach APISIX admin via 'apisix:9180' (HTTP $test_short)"
fi

if [ "$test_full" = "200" ]; then
    print_status 0 "Can reach APISIX admin via 'apisix-apisix-1:9180'"
else
    print_status 1 "Cannot reach APISIX admin via 'apisix-apisix-1:9180' (HTTP $test_full)"
fi

# Check actual APISIX container name
echo
echo "Verifying APISIX container names..."
apisix_container=$(docker ps --filter "name=apisix" --format "table {{.Names}}" | grep -v "NAMES" | grep -v "dashboard" | head -1)
if [ -n "$apisix_container" ]; then
    echo "   APISIX container name: $apisix_container"
fi

echo
echo "Step 3: Network Inspection"
echo "========================="

# Inspect vutf-network
echo "Inspecting vutf-network..."
network_exists=$(docker network ls | grep -c "vutf-network" || echo "0")
if [ "$network_exists" -gt 0 ]; then
    print_status 0 "vutf-network exists"
    
    # Get containers on network
    containers_on_network=$(docker network inspect vutf-network -f '{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null || echo "none")
    echo "   Containers on vutf-network: $containers_on_network"
else
    print_status 1 "vutf-network does not exist"
    echo "   Run setup script to create the network"
fi

echo
echo "Step 4: Recommendations"
echo "======================"

# Provide recommendations based on findings
if [ "$test_short" = "200" ] && [ "$admin_url" != "http://apisix:9180" ]; then
    echo "⚠️  Container can reach APISIX via 'apisix:9180' but APISIX_ADMIN_URL is set to '$admin_url'"
    echo "   Consider updating docker-compose.yml to use: APISIX_ADMIN_URL=http://apisix:9180"
elif [ "$test_full" = "200" ] && [ "$admin_url" != "http://apisix-apisix-1:9180" ]; then
    echo "⚠️  Container can reach APISIX via 'apisix-apisix-1:9180' but APISIX_ADMIN_URL is set to '$admin_url'"
    echo "   Consider updating to use the working hostname"
fi

if [ "$test_short" != "200" ] && [ "$test_full" != "200" ]; then
    echo "❌ Cannot reach APISIX admin from FastAPI container"
    echo "   This will prevent endpoint discovery for OpenAPI providers"
    echo
    echo "   Troubleshooting steps:"
    echo "   1. Check if APISIX is running: docker ps | grep apisix"
    echo "   2. Restart services: cd apisix && docker compose restart"
    echo "   3. Check logs: docker logs violentutf_api --tail 50"
else
    echo "✅ Network connectivity is working"
    echo "   FastAPI can discover OpenAPI endpoints through APISIX"
fi

echo
echo "=== Phase 2 Verification Complete ==="