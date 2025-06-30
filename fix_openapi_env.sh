#!/usr/bin/env bash
# Quick fix script to add OpenAPI provider configuration to FastAPI .env file

echo "🔧 Fixing OpenAPI environment configuration for FastAPI container"
echo "================================================================="

# Load ai-tokens.env
if [ -f "ai-tokens.env" ]; then
    echo "Loading configuration from ai-tokens.env..."
    set -a
    source ai-tokens.env
    set +a
else
    echo "❌ ai-tokens.env not found"
    exit 1
fi

# Check if FastAPI .env exists
if [ ! -f "violentutf_api/fastapi_app/.env" ]; then
    echo "❌ FastAPI .env file not found"
    exit 1
fi

echo "Current OPENAPI_ENABLED: ${OPENAPI_ENABLED}"
echo "Current OPENAPI_1_ENABLED: ${OPENAPI_1_ENABLED}"
echo "Current OPENAPI_1_ID: ${OPENAPI_1_ID}"

# Remove existing OpenAPI configuration
echo "Removing existing OpenAPI configuration..."
sed -i '' '/^# OpenAPI Provider/,/^$/d' violentutf_api/fastapi_app/.env

# Add OpenAPI provider configurations
if [ "$OPENAPI_ENABLED" = "true" ]; then
    echo "Adding OpenAPI provider configurations..."
    
    cat >> violentutf_api/fastapi_app/.env <<EOF

# OpenAPI Provider Configurations (for dynamic model discovery)
# Added by fix_openapi_env.sh script

EOF

    # Add configured providers
    for i in {1..10}; do
        local enabled_var="OPENAPI_${i}_ENABLED"
        local id_var="OPENAPI_${i}_ID"
        local name_var="OPENAPI_${i}_NAME"
        local base_url_var="OPENAPI_${i}_BASE_URL"
        local auth_token_var="OPENAPI_${i}_AUTH_TOKEN"
        local auth_type_var="OPENAPI_${i}_AUTH_TYPE"
        local spec_path_var="OPENAPI_${i}_SPEC_PATH"
        
        # Check if this provider is enabled and configured
        if [ "${!enabled_var}" = "true" ] && [ -n "${!id_var}" ]; then
            echo "  Adding OpenAPI provider $i: ${!id_var}"
            
            cat >> violentutf_api/fastapi_app/.env <<EOF
# OpenAPI Provider $i Configuration
${enabled_var}=${!enabled_var}
${id_var}=${!id_var}
${name_var}=${!name_var}
${base_url_var}=${!base_url_var}
${auth_token_var}=${!auth_token_var}
${auth_type_var}=${!auth_type_var:-bearer}
${spec_path_var}=${!spec_path_var}

EOF
        fi
    done
    
    echo "✅ Added OpenAPI provider configurations"
else
    echo "ℹ️  OPENAPI_ENABLED=false, skipping provider configurations"
fi

echo ""
echo "Verifying configuration..."
if grep -q "OPENAPI_1_BASE_URL" violentutf_api/fastapi_app/.env; then
    echo "✅ OpenAPI provider configuration found in FastAPI .env"
    echo "📋 OpenAPI variables in FastAPI .env:"
    grep "OPENAPI_1_" violentutf_api/fastapi_app/.env | sed 's/AUTH_TOKEN=.*/AUTH_TOKEN=***[REDACTED]***/'
else
    echo "❌ OpenAPI provider configuration not found in FastAPI .env"
fi

echo ""
echo "🔄 Restarting FastAPI container to apply changes..."
if docker ps --filter "name=violentutf_api" --format "{{.Names}}" | grep -q violentutf_api; then
    docker restart violentutf_api
    echo "✅ FastAPI container restarted"
    
    echo ""
    echo "⏳ Waiting for container to be ready..."
    sleep 5
    
    echo "📊 Testing OpenAPI debug endpoint..."
    if curl -s -m 5 http://localhost:9080/health >/dev/null 2>&1; then
        echo "✅ FastAPI container is responsive"
        echo ""
        echo "🎯 Next steps:"
        echo "1. Test OpenAPI debug endpoint: curl http://localhost:9080/api/v1/generators/apisix/openapi-debug"
        echo "2. Check ViolentUTF Streamlit interface for GSAi models"
        echo "3. Monitor FastAPI logs: docker logs violentutf_api -f | grep -i openapi"
    else
        echo "⚠️  FastAPI container may still be starting up"
    fi
else
    echo "❌ FastAPI container is not running"
    echo "💡 Start it with: docker-compose up -d"
fi