#!/bin/bash

# Quick fix script for GSAi network issues
# Run this if FastAPI cannot discover GSAi models

echo "=== GSAi Network Fix Script ==="
echo "This script fixes common network issues for GSAi integration"
echo

# Check required commands
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    echo "Please install Docker before running this script"
    exit 1
fi

# Check if FastAPI container is running
if ! docker ps | grep -q violentutf_api; then
    echo "❌ FastAPI container is not running"
    echo "Please start the services first with: docker-compose up -d"
    exit 1
fi

# Fix APISIX_ADMIN_URL if needed
echo "Checking APISIX_ADMIN_URL in FastAPI container..."
current_url=$(docker exec violentutf_api sh -c 'echo $APISIX_ADMIN_URL' 2>/dev/null)

if [ "$current_url" != "http://apisix-apisix-1:9180" ]; then
    echo "⚠️  APISIX_ADMIN_URL is not set correctly: '$current_url'"
    echo "Setting correct value..."
    
    # Update the .env file in the container
    # Note: This modifies the container's environment file
    if docker exec violentutf_api sh -c 'echo "APISIX_ADMIN_URL=http://apisix-apisix-1:9180" >> /app/.env' 2>/dev/null; then
        echo "✅ APISIX_ADMIN_URL has been added to container .env file"
        echo "⚠️  IMPORTANT: You must restart the FastAPI container for changes to take effect:"
        echo "   docker restart violentutf_api"
    else
        echo "❌ Failed to update .env file in container"
        echo "You may need to update the docker-compose.yml environment section instead"
    fi
else
    echo "✅ APISIX_ADMIN_URL is already correctly set"
fi

# Test connectivity
echo
echo "Testing connectivity..."
test_result=$(docker exec violentutf_api sh -c 'curl -s --max-time 5 -w "HTTP_CODE:%{http_code}" http://apisix-apisix-1:9180/apisix/admin/health' 2>/dev/null)

if [[ "$test_result" == *"HTTP_CODE:200"* ]]; then
    echo "✅ FastAPI can reach APISIX admin API"
else
    echo "❌ FastAPI still cannot reach APISIX admin API"
    echo "This may require checking Docker network configuration"
fi

echo
echo "To verify the fix worked, run: ./test_gsai_integration.sh"