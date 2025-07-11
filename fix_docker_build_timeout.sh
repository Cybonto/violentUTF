#!/usr/bin/env bash
# Fix Docker build timeout issues for ViolentUTF

echo "🔧 Fixing Docker build timeout issues..."

# Ensure Docker daemon has proper timeout settings
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📝 Configuring Docker for macOS..."
    # Docker Desktop settings
    cat > ~/Library/Group\ Containers/group.com.docker/settings.json.tmp << 'EOF'
{
  "buildkit": true,
  "experimental": false,
  "features": {
    "buildkit": true
  }
}
EOF
    
    # Only update if Docker Desktop settings exist
    if [ -f ~/Library/Group\ Containers/group.com.docker/settings.json ]; then
        echo "   ⚠️  Docker Desktop settings found - please manually increase timeout in Docker Desktop preferences"
    fi
fi

# Create a temporary requirements file without large packages
echo "📦 Creating optimized requirements file..."
cd /Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app

# Backup original requirements
cp requirements.txt requirements.txt.backup

# Create a version without the problematic packages for initial build
grep -v -E "(boto3|botocore|torch|transformers)" requirements.txt > requirements-fast.txt

# Add the large packages at the end with specific versions to avoid dependency resolution
cat >> requirements-fast.txt << 'EOF'

# Large packages installed last with fixed versions
botocore==1.38.13
boto3==1.38.13
# torch and transformers can be installed post-deployment if needed
EOF

echo "🐳 Rebuilding FastAPI container with optimized approach..."

# Stop existing containers
cd /Users/tamnguyen/Documents/GitHub/ViolentUTF
docker-compose -f apisix/docker-compose.yml stop fastapi 2>/dev/null

# Try building with increased network timeout
export DOCKER_BUILDKIT=1
export BUILDKIT_STEP_LOG_MAX_SIZE=50000000

echo "   Building with extended timeouts..."
cd apisix
docker-compose build --no-cache --progress=plain fastapi 2>&1 | tee ../build.log

# Check if build succeeded
if [ $? -eq 0 ]; then
    echo "✅ Build succeeded!"
    
    # Restore original requirements
    cd ../violentutf_api/fastapi_app
    mv requirements.txt.backup requirements.txt
    
    # Start the container
    cd ../../apisix
    docker-compose up -d fastapi
    
    echo "🎉 FastAPI container rebuilt successfully!"
else
    echo "❌ Build failed. Checking alternative solutions..."
    
    # Alternative: Use pre-built image approach
    echo "🔄 Trying alternative solution with pre-downloaded packages..."
    
    # Create a directory for pre-downloaded wheels
    mkdir -p /tmp/vutf-wheels
    cd /tmp/vutf-wheels
    
    # Download the problematic packages separately
    echo "   Downloading packages with pip download..."
    pip download --timeout 600 --retries 10 botocore==1.38.13 boto3==1.38.13
    
    if [ $? -eq 0 ]; then
        echo "   ✅ Packages downloaded successfully"
        
        # Copy to build context
        cp *.whl /Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/
        
        echo "   📝 Creating Dockerfile.fix for offline installation..."
        cd /Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app
        
        # Create a modified Dockerfile that uses local wheels
        sed 's|RUN pip install --no-cache-dir --timeout 600 --retries 10 -r requirements-prebuild.txt|COPY *.whl /tmp/wheels/\nRUN pip install --no-cache-dir /tmp/wheels/*.whl|' Dockerfile > Dockerfile.fix
        
        echo "   🏗️ Building with local wheels..."
        docker build -f Dockerfile.fix -t violentutf-api-fixed .
        
        # Clean up
        rm -f *.whl
        rm -f Dockerfile.fix
    fi
fi

echo ""
echo "📋 Next steps:"
echo "1. If the build succeeded, run: cd /Users/tamnguyen/Documents/GitHub/ViolentUTF && ./check_services.sh"
echo "2. If issues persist, try using a faster internet connection or corporate proxy"
echo "3. As a last resort, you can skip boto3 for now and install it inside the running container"

# Restore original requirements if needed
cd /Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app
if [ -f requirements.txt.backup ]; then
    mv requirements.txt.backup requirements.txt
fi