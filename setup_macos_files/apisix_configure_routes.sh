#!/bin/bash

# Source logging utilities
source "$(dirname "$0")/logging_utils.sh"

# APISIX Route Configuration Script for ViolentUTF API
# This script configures APISIX to proxy ViolentUTF API endpoints
#
# IMPORTANT: This script should be run from the HOST machine, not inside a container
# It uses localhost to communicate with APISIX admin API exposed on the host
#
# DO NOT MODIFY THE URLS IN THIS FILE - they are correct for host execution
# If you need container-to-container communication, that's handled by the application code

set -e

# CONTEXT DETECTION - Determine if we're running on host or in container
if [ -f /.dockerenv ]; then
    echo "❌ ERROR: This script should not be run inside a Docker container!"
    echo "Please run this script from your host machine."
    exit 1
fi

# APISIX Admin URL - localhost is CORRECT here as this runs on the host
# DO NOT CHANGE TO CONTAINER NAMES - this script runs outside containers
APISIX_ADMIN_URL="http://localhost:9180"

# SECURITY: Load admin key from apisix/.env file - NO hardcoded secrets
if [ -f apisix/.env ]; then
    ADMIN_KEY=$(grep "APISIX_ADMIN_KEY=" apisix/.env | cut -d'=' -f2)
elif [ -f .env ]; then
    ADMIN_KEY=$(grep "APISIX_ADMIN_KEY=" .env | cut -d'=' -f2)
fi

if [ -z "$ADMIN_KEY" ]; then
    echo "❌ ERROR: APISIX_ADMIN_KEY not found in .env file"
    echo "Please ensure APISIX_ADMIN_KEY is set in apisix/.env"
    exit 1
fi

# FastAPI upstream uses Docker service name for container-to-container communication
# This is the internal Docker network name, NOT localhost
FASTAPI_UPSTREAM="http://violentutf_api:8000"  # Internal Docker service name

log_detail "Configuring APISIX routes for ViolentUTF API..."
log_debug "Including orchestrator routes configuration..."
log_debug "Running from: $(pwd)"
log_debug "Admin URL: $APISIX_ADMIN_URL (localhost is correct for host execution)"

# Function to create/update upstream
create_upstream() {
    log_detail "Creating upstream for ViolentUTF API..."
    local upstream_response=$(curl -s -H "X-API-KEY: $ADMIN_KEY" -X PUT -d '{
        "type": "roundrobin",
        "nodes": {
            "violentutf_api:8000": 1
        },
        "timeout": {
            "connect": 60,
            "send": 60,
            "read": 60
        },
        "keepalive_pool": {
            "idle_timeout": 60,
            "requests": 1000,
            "size": 320
        },
        "retry_timeout": 0,
        "scheme": "http",
        "desc": "ViolentUTF FastAPI Service"
    }' "$APISIX_ADMIN_URL/apisix/admin/upstreams/violentutf-api")
    log_debug "Upstream creation response: $upstream_response"
}

# Function to create route
create_route() {
    local route_id=$1
    local route_path=$2
    local methods=$3
    local desc=$4
    local priority=${5:-0}  # Optional priority parameter, default 0
    
    log_detail "Creating route: $desc"
    
    # Build the JSON with priority if specified
    local route_json="{
        \"uri\": \"$route_path\",
        \"methods\": $methods,
        \"upstream_id\": \"violentutf-api\","
    
    # Add priority if greater than 0
    if [ "$priority" -gt 0 ]; then
        route_json="${route_json}
        \"priority\": $priority,"
    fi
    
    route_json="${route_json}
        \"plugins\": {
            \"cors\": {
                \"allow_origins\": \"*\",
                \"allow_methods\": \"GET,POST,PUT,DELETE,OPTIONS\",
                \"allow_headers\": \"Content-Type,Authorization,X-Real-IP,X-Forwarded-For,X-Forwarded-Host,X-API-Gateway\"
            },
            \"proxy-rewrite\": {
                \"headers\": {
                    \"set\": {
                        \"X-Real-IP\": \"\$remote_addr\",
                        \"X-Forwarded-For\": \"\$proxy_add_x_forwarded_for\",
                        \"X-Forwarded-Host\": \"\$host\",
                        \"X-API-Gateway\": \"APISIX\"
                    }
                }
            }
        },
        \"desc\": \"$desc\"
    }"
    
    local response=$(curl -s -H "X-API-KEY: $ADMIN_KEY" -X PUT -d "$route_json" "$APISIX_ADMIN_URL/apisix/admin/routes/$route_id")
    log_debug "Route creation response: $response"
}

# Create upstream first
create_upstream

log_detail "Creating ViolentUTF API routes..."

# Health check endpoints (no auth required)
create_route "1001" "/health" "[\"GET\"]" "Health check endpoint"
create_route "1005" "/api/v1/health" "[\"GET\"]" "API v1 health check endpoint"

# API Documentation endpoints
create_route "1002" "/docs*" "[\"GET\"]" "FastAPI documentation"
create_route "1003" "/openapi.json" "[\"GET\"]" "OpenAPI schema"
create_route "1004" "/redoc*" "[\"GET\"]" "ReDoc documentation"

# Authentication endpoints
create_route "2001" "/api/v1/auth/*" "[\"GET\", \"POST\", \"PUT\", \"DELETE\"]" "Authentication endpoints"

# Database management endpoints
create_route "2002" "/api/v1/database/*" "[\"GET\", \"POST\", \"PUT\", \"DELETE\"]" "Database management endpoints"

# Session management endpoints
create_route "2003" "/api/v1/sessions*" "[\"GET\", \"POST\", \"PUT\", \"DELETE\"]" "Session management endpoints"

# Configuration endpoints
create_route "2004" "/api/v1/config/*" "[\"GET\", \"POST\", \"PUT\", \"DELETE\"]" "Configuration management endpoints"

# File management endpoints
create_route "2005" "/api/v1/files*" "[\"GET\", \"POST\", \"PUT\", \"DELETE\"]" "File management endpoints"

# JWT Keys endpoints
create_route "2006" "/api/v1/keys/*" "[\"GET\", \"POST\", \"PUT\", \"DELETE\"]" "JWT keys endpoints"

# Test endpoints
create_route "2007" "/api/v1/test/*" "[\"GET\", \"POST\", \"PUT\", \"DELETE\"]" "Test endpoints"

# Debug endpoints (for JWT troubleshooting)
create_route "2015" "/api/v1/debug/*" "[\"GET\", \"POST\", \"PUT\", \"DELETE\"]" "Debug endpoints"

# Generator management endpoints
create_route "2008" "/api/v1/generators*" "[\"GET\", \"POST\", \"PUT\", \"DELETE\"]" "Generator management endpoints"

# Dataset management endpoints
create_route "2009" "/api/v1/datasets*" "[\"GET\", \"POST\", \"PUT\", \"DELETE\"]" "Dataset management endpoints"

# Converter management endpoints
create_route "2010" "/api/v1/converters*" "[\"GET\", \"POST\", \"PUT\", \"DELETE\"]" "Converter management endpoints"

# Scorer management endpoints
create_route "2011" "/api/v1/scorers*" "[\"GET\", \"POST\", \"PUT\", \"DELETE\"]" "Scorer management endpoints"

# Red-teaming endpoints (PyRIT and Garak)
create_route "2012" "/api/v1/redteam*" "[\"GET\", \"POST\", \"PUT\", \"DELETE\"]" "Red-teaming endpoints (PyRIT and Garak)"

# Orchestrator executions endpoint (specific route before wildcard with high priority)
create_route "2012a" "/api/v1/orchestrators/executions" "[\"GET\"]" "List all orchestrator executions" 100

# Orchestrator management endpoints (wildcard - must come after specific routes)
create_route "2013" "/api/v1/orchestrators*" "[\"GET\", \"POST\", \"PUT\", \"DELETE\"]" "Orchestrator management endpoints"

# APISIX admin endpoints for IronUTF
create_route "2014" "/api/v1/apisix-admin*" "[\"GET\", \"POST\", \"PUT\", \"DELETE\"]" "APISIX admin endpoints for IronUTF"

# MCP (Model Context Protocol) endpoints
create_route "3001" "/mcp/*" "[\"GET\", \"POST\", \"OPTIONS\"]" "MCP Server-Sent Events endpoint"

# MCP OAuth endpoints
create_route "3002" "/mcp/oauth/*" "[\"GET\", \"POST\"]" "MCP OAuth proxy endpoints"

# Generic API catch-all route (lowest priority)
log_detail "Creating generic API catch-all route..."
local catchall_response=$(curl -s -H "X-API-KEY: $ADMIN_KEY" -X PUT -d "{
    \"id\": \"violentutf-api\",
    \"uri\": \"/api/*\",
    \"name\": \"violentutf-api\",
    \"methods\": [\"GET\", \"POST\", \"PUT\", \"DELETE\", \"OPTIONS\", \"PATCH\"],
    \"upstream\": {
        \"type\": \"roundrobin\",
        \"nodes\": {
            \"violentutf_api:8000\": 1
        },
        \"timeout\": {
            \"connect\": 60,
            \"send\": 60,
            \"read\": 60
        },
        \"scheme\": \"http\",
        \"pass_host\": \"pass\",
        \"hash_on\": \"vars\"
    },
    \"priority\": 1,
    \"plugins\": {
        \"cors\": {
            \"allow_origins\": \"http://localhost:8501,http://localhost:3000\",
            \"allow_methods\": \"GET,POST,PUT,DELETE,PATCH,OPTIONS\",
            \"allow_headers\": \"Authorization,Content-Type,X-Requested-With\",
            \"allow_credential\": true,
            \"expose_headers\": \"X-Total-Count\",
            \"max_age\": 3600
        },
        \"proxy-rewrite\": {
            \"headers\": {
                \"set\": {
                    \"X-Real-IP\": \"\$remote_addr\",
                    \"X-Forwarded-For\": \"\$proxy_add_x_forwarded_for\",
                    \"X-Forwarded-Host\": \"\$host\",
                    \"X-API-Gateway\": \"APISIX\"
                }
            }
        },
        \"limit-req\": {
            \"rate\": 100,
            \"burst\": 50,
            \"key_type\": \"var\",
            \"key\": \"remote_addr\",
            \"rejected_code\": 429,
            \"rejected_msg\": \"Too many requests\",
            \"policy\": \"local\",
            \"nodelay\": false,
            \"allow_degradation\": false
        },
        \"limit-count\": {
            \"count\": 1000,
            \"time_window\": 3600,
            \"key_type\": \"var\",
            \"key\": \"remote_addr\",
            \"rejected_code\": 429,
            \"rejected_msg\": \"API rate limit exceeded\",
            \"policy\": \"local\",
            \"show_limit_quota_header\": true,
            \"allow_degradation\": false
        }
    }
}" $APISIX_ADMIN_URL/apisix/admin/routes/violentutf-api)
log_debug "Catchall route response: $catchall_response"

log_success "APISIX route configuration completed!"

# Show route summary in verbose mode
if should_log 2; then
    echo "📋 Configured routes:"
    echo "  - Health: http://localhost:9080/health"
    echo "  - API Health: http://localhost:9080/api/v1/health"
    echo "  - API Docs: http://localhost:9080/docs"
    echo "  - Auth: http://localhost:9080/api/v1/auth/*"
    echo "  - Database: http://localhost:9080/api/v1/database/*"
    echo "  - Sessions: http://localhost:9080/api/v1/sessions*"
    echo "  - Config: http://localhost:9080/api/v1/config/*"
    echo "  - Files: http://localhost:9080/api/v1/files*"
    echo "  - JWT Keys: http://localhost:9080/api/v1/keys/*"
    echo "  - Test: http://localhost:9080/api/v1/test/*"
    echo "  - Generators: http://localhost:9080/api/v1/generators*"
    echo "  - Datasets: http://localhost:9080/api/v1/datasets*"
    echo "  - Converters: http://localhost:9080/api/v1/converters*"
    echo "  - Scorers: http://localhost:9080/api/v1/scorers*"
    echo "  - Red-teaming: http://localhost:9080/api/v1/redteam*"
    echo "  - Orchestrators: http://localhost:9080/api/v1/orchestrators*"
    echo "  - APISIX Admin: http://localhost:9080/api/v1/apisix-admin*"
    echo "  - MCP SSE: http://localhost:9080/mcp/*"
    echo "  - MCP OAuth: http://localhost:9080/mcp/oauth/*"
    echo
    echo "🔍 You can verify routes with:"
    echo "  curl -H 'X-API-KEY: $ADMIN_KEY' $APISIX_ADMIN_URL/apisix/admin/routes"
    echo
    echo "🔍 To verify routes, visit: http://localhost:9001/routes (APISIX Dashboard)"
    echo "📊 Admin API: $APISIX_ADMIN_URL"
    echo
    echo "🧪 Test with:"
    echo "curl http://localhost:9080/health"
    echo "curl -H 'Authorization: Bearer <token>' http://localhost:9080/api/v1/auth/token/info"
fi