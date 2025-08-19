#!/bin/bash
# Script to cleanly restart APISIX stack in Docker Desktop

echo "🧹 Cleaning and restarting APISIX stack..."

# Change to apisix directory
cd apisix || { echo "APISIX directory not found"; exit 1; }

# Stop all containers
echo "📦 Stopping APISIX containers..."
docker-compose down

# Remove specific problem volumes while preserving data
echo "🗑️  Cleaning up APISIX runtime files..."

# Option 1: Clean specific files from volume (preserves etcd data)
docker run --rm -v apisix_apisix_logs:/logs alpine sh -c "rm -f /logs/worker_events.sock /logs/nginx.pid" 2>/dev/null
docker run --rm -v apisix_apisix_conf:/conf alpine sh -c "rm -f /conf/nginx.pid" 2>/dev/null

# Option 2: If Option 1 doesn't work, remove and recreate logs volume only
# docker volume rm apisix_apisix_logs 2>/dev/null || true

# Wait a moment for cleanup
sleep 2

# Start containers again
echo "🚀 Starting APISIX containers..."
docker-compose up -d

# Wait for APISIX to be ready
echo "⏳ Waiting for APISIX to be ready..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -s --max-time 5 http://localhost:9180 >/dev/null 2>&1; then
        echo "✅ APISIX is ready!"
        
        # Show container status
        echo ""
        echo "📊 Container Status:"
        docker-compose ps
        break
    fi
    echo "Waiting for APISIX... (attempt $attempt/$max_attempts)"
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ APISIX failed to start properly"
    echo "📋 Container logs:"
    docker-compose logs --tail=50 apisix
    exit 1
fi

echo "✅ APISIX stack restarted successfully!"