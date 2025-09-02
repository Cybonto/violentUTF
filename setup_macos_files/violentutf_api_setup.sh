#!/usr/bin/env bash
# violentutf_api_setup.sh - FastAPI service configuration and startup

# Function to setup ViolentUTF API
setup_violentutf_api() {
    echo "Setting up ViolentUTF API service..."

    # The ViolentUTF API is now integrated with APISIX
    # This function primarily ensures environment configuration is correct

    # Configure FastAPI environment
    configure_fastapi_env

    # Update AI provider flags
    update_fastapi_env

    echo "✅ ViolentUTF API configuration completed"
    echo "📝 Note: API service is started with APISIX container stack"

    return 0
}

# Function to configure FastAPI environment
configure_fastapi_env() {
    echo "Configuring FastAPI environment..."

    local fastapi_env_file="violentutf_api/fastapi_app/.env"

    if [ ! -f "$fastapi_env_file" ]; then
        echo "❌ FastAPI .env file not found: $fastapi_env_file"
        return 1
    fi

    # Ensure required environment variables are set
    local required_vars=("JWT_SECRET_KEY" "VIOLENTUTF_API_KEY" "PYRIT_DB_SALT")

    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$fastapi_env_file"; then
            echo "⚠️  Missing required variable: $var"
            echo "${var}=$(generate_random_string 32)" >> "$fastapi_env_file"
            echo "   Added $var to FastAPI environment"
        fi
    done

    echo "✅ FastAPI environment configuration verified"
    return 0
}

# Function to verify API health
verify_api_health() {
    echo "Verifying API health..."

    local max_retries=10
    local retry_count=0

    # Wait for API to be accessible through APISIX
    while [ $retry_count -lt $max_retries ]; do
        if curl -s http://localhost:9080/api/v1/health >/dev/null 2>&1; then
            echo "✅ ViolentUTF API is healthy and accessible"

            # Get API health details
            local health_response=$(curl -s http://localhost:9080/api/v1/health 2>/dev/null || echo "{}")
            local api_status=$(echo "$health_response" | jq -r '.status' 2>/dev/null || echo "unknown")

            echo "📊 API Status: $api_status"
            return 0
        fi

        echo "Waiting for API health... (attempt $((retry_count + 1))/$max_retries)"
        sleep 5
        retry_count=$((retry_count + 1))
    done

    echo "❌ API health check failed - service may not be accessible"
    return 1
}
