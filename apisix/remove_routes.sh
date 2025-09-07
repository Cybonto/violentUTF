#!/bin/bash

# APISIX Route Removal Script for ViolentUTF API
# This script removes all ViolentUTF API routes from APISIX

set -e

APISIX_ADMIN_URL="http://localhost:9180"
# SECURITY: Load admin key from environment - NO hardcoded secrets
ADMIN_KEY="${APISIX_ADMIN_KEY:-}"
if [ -z "$ADMIN_KEY" ]; then
    echo "❌ ERROR: APISIX_ADMIN_KEY environment variable not set"
    exit 1
fi

echo "🗑️  Removing APISIX routes for ViolentUTF API..."

# Function to remove route
remove_route() {
    local route_id=$1
    local desc=$2

    echo "❌ Removing route $route_id: $desc"
    curl -s -H "X-API-KEY: $ADMIN_KEY" -X DELETE "$APISIX_ADMIN_URL/apisix/admin/routes/$route_id" || true
}

# Remove all ViolentUTF routes
remove_route "1001" "Health check endpoint"
remove_route "1002" "FastAPI documentation"
remove_route "1003" "OpenAPI schema"
remove_route "1004" "ReDoc documentation"
remove_route "2001" "Authentication endpoints"
remove_route "2002" "Database management endpoints"
remove_route "2003" "Session management endpoints"
remove_route "2004" "Configuration management endpoints"
remove_route "2005" "File management endpoints"
remove_route "2006" "JWT keys endpoints"
remove_route "2007" "Test endpoints"
remove_route "2008" "Generator management endpoints"
remove_route "2009" "Dataset management endpoints"
remove_route "2010" "Converter management endpoints"
remove_route "2011" "Scorer management endpoints"
remove_route "2012" "Red-teaming endpoints"
remove_route "2012a" "List orchestrator executions"
remove_route "2013" "Orchestrator management endpoints"
remove_route "2014" "APISIX admin endpoints"
remove_route "2015" "Debug endpoints"
remove_route "3001" "MCP SSE endpoints"
remove_route "3002" "MCP OAuth proxy endpoints"
remove_route "3099" "OpenAPI discovery endpoint"

# Remove AI Gateway routes (OpenAPI and other providers)
echo
echo "🗑️  Removing AI Gateway routes..."
remove_route "9001" "OpenAPI chat completions"
remove_route "9101" "OpenAPI models"

# Remove OpenAI routes
for model_route in "openai-gpt-3-5-turbo" "openai-gpt-4" "openai-gpt-4-turbo" "openai-gpt-4o" "openai-gpt-4o-mini" "openai-gpt-4-1106-preview" "openai-gpt-4-vision-preview"; do
    remove_route "$model_route" "OpenAI $model_route"
done

# Remove Anthropic routes  
for model_route in "anthropic-claude-3-opus-20240229" "anthropic-claude-3-sonnet-20240229" "anthropic-claude-3-haiku-20240307" "anthropic-claude-3-5-sonnet-20241022" "anthropic-claude-3-5-haiku-20241022"; do
    remove_route "$model_route" "Anthropic $model_route"
done

echo
echo "🗑️  Removing upstream..."
curl -s -H "X-API-KEY: $ADMIN_KEY" -X DELETE "$APISIX_ADMIN_URL/apisix/admin/upstreams/violentutf-api" || true

echo
echo "✅ All ViolentUTF API routes and upstream removed!"
echo
echo "ℹ️  To reconfigure routes, run: ./configure_routes.sh"
