#!/bin/bash
#
# Fix ModuleNotFoundError for template_service in Enterprise environment
# This script ensures the template_service.py file is properly synced to the Docker container
#

echo "🔧 Fixing Enterprise Environment Module Import Error..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "error")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "success")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "info")
            echo -e "${YELLOW}ℹ️  $message${NC}"
            ;;
    esac
}

# Check if we're in the ViolentUTF directory
if [ ! -f "setup_macos_new.sh" ] && [ ! -f "setup_linux_new.sh" ]; then
    print_status "error" "This script must be run from the ViolentUTF root directory"
    exit 1
fi

# Step 1: Check if file exists on host
print_status "info" "Checking if template_service.py exists on host..."
if [ -f "violentutf_api/fastapi_app/app/services/report_system/template_service.py" ]; then
    print_status "success" "File exists on host"
else
    print_status "error" "File missing on host! Please ensure you have the latest code."
    exit 1
fi

# Step 2: Check if API container is running
print_status "info" "Checking if violentutf_api container is running..."
if docker ps --format '{{.Names}}' | grep -q '^violentutf_api$'; then
    print_status "success" "Container is running"
else
    print_status "error" "Container not running. Starting it now..."
    docker-compose -f violentutf_api/docker-compose.yml up -d api
    sleep 10
fi

# Step 3: Copy the entire report_system directory to ensure all files are synced
print_status "info" "Syncing report_system files to container..."
docker exec violentutf_api mkdir -p /app/app/services/report_system/

# Copy all report_system files
docker cp violentutf_api/fastapi_app/app/services/report_system/. violentutf_api:/app/app/services/report_system/ 2>/dev/null

if [ $? -eq 0 ]; then
    print_status "success" "Files copied successfully"
else
    print_status "error" "Failed to copy files. Trying alternative method..."

    # Alternative: Copy files one by one
    for file in violentutf_api/fastapi_app/app/services/report_system/*.py; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            docker cp "$file" violentutf_api:/app/app/services/report_system/"$filename"
        fi
    done
fi

# Step 4: Fix permissions inside container
print_status "info" "Fixing file permissions..."
docker exec violentutf_api chown -R app:app /app/app/services/report_system/
docker exec violentutf_api chmod -R 755 /app/app/services/report_system/

# Step 5: Verify files exist in container
print_status "info" "Verifying files in container..."
FILES_IN_CONTAINER=$(docker exec violentutf_api ls -la /app/app/services/report_system/ 2>/dev/null | grep -c "\.py$")

if [ "$FILES_IN_CONTAINER" -gt 0 ]; then
    print_status "success" "Found $FILES_IN_CONTAINER Python files in container"
    echo ""
    echo "Files in container:"
    docker exec violentutf_api ls -la /app/app/services/report_system/
else
    print_status "error" "No Python files found in container!"
fi

# Step 6: Create __init__.py files if missing
print_status "info" "Ensuring __init__.py files exist..."
docker exec violentutf_api touch /app/app/services/__init__.py
docker exec violentutf_api touch /app/app/services/report_system/__init__.py

# Step 7: Restart the API container
print_status "info" "Restarting API container..."
docker restart violentutf_api

# Wait for container to be ready
print_status "info" "Waiting for API to be ready..."
sleep 15

# Step 8: Check API health
print_status "info" "Checking API health..."
HEALTH_CHECK=$(curl -s http://localhost:9080/api/v1/health 2>/dev/null)

if [ $? -eq 0 ] && [ ! -z "$HEALTH_CHECK" ]; then
    print_status "success" "API is healthy!"
    echo ""
    echo "Health check response:"
    echo "$HEALTH_CHECK" | jq . 2>/dev/null || echo "$HEALTH_CHECK"
else
    print_status "error" "API health check failed. Checking logs..."
    echo ""
    echo "Recent API logs:"
    docker logs violentutf_api --tail 20
fi

# Step 9: Additional diagnostics
echo ""
print_status "info" "Running diagnostics..."

# Check Python path in container
echo "Python path in container:"
docker exec violentutf_api python -c "import sys; print('\n'.join(sys.path))"

# Check if module can be imported
echo ""
echo "Testing module import:"
docker exec violentutf_api python -c "from app.services.report_system.template_service import TemplateService; print('✅ Module imported successfully!')" 2>&1

# Step 10: Enterprise-specific fixes
if [ -f "/.dockerenv" ]; then
    print_status "info" "Running in Docker environment - skipping Enterprise-specific fixes"
else
    print_status "info" "Applying Enterprise-specific fixes..."

    # Check Docker Desktop file sharing
    if command -v docker >/dev/null 2>&1; then
        DOCKER_VERSION=$(docker version --format '{{.Server.Version}}')
        print_status "info" "Docker version: $DOCKER_VERSION"

        # Add current directory to Docker file sharing if on macOS
        if [[ "$OSTYPE" == "darwin"* ]]; then
            print_status "info" "macOS detected - ensure $(pwd) is in Docker Desktop file sharing"
        fi
    fi
fi

echo ""
print_status "success" "Fix script completed!"
echo ""
echo "Next steps:"
echo "1. If the API is still not healthy, check Docker Desktop file sharing settings"
echo "2. Ensure $(pwd) is in the allowed paths"
echo "3. Try running: ./check_services.sh"
echo "4. If issues persist, run: docker-compose -f violentutf_api/docker-compose.yml build --no-cache api"
