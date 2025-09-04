#!/usr/bin/env bash
# Diagnose APISIX FastAPI route configuration

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Get inputs
if [ -z "$APISIX_ADMIN_KEY" ]; then
    echo -n "Enter APISIX admin key: "
    read -s APISIX_ADMIN_KEY
    echo
fi

APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"

print_header "APISIX FastAPI Route Diagnosis"
echo "This script will find why /api/* routes aren't proxying to FastAPI correctly."
echo

# Get all routes and examine the /api/* route
print_info "1. Getting APISIX route configuration..."
routes_response=$(curl -s "$APISIX_ADMIN_URL/apisix/admin/routes" -H "X-API-KEY: $APISIX_ADMIN_KEY")

if [ $? -ne 0 ]; then
    print_error "Failed to connect to APISIX admin API"
    exit 1
fi

print_success "Connected to APISIX admin API"

# Find the /api/* route
api_route=$(echo "$routes_response" | jq -r '.list[] | select(.value.uri == "/api/*")')

if [ "$api_route" = "" ] || [ "$api_route" = "null" ]; then
    print_error "No /api/* route found in APISIX!"
    print_info "Available routes:"
    echo "$routes_response" | jq -r '.list[].value | .uri + " (" + .id + ")"' | head -10
    echo
    print_warning "This is why FastAPI endpoints aren't working - no proxy route exists!"
    print_info "You need to create a route that proxies /api/* to your FastAPI container"
    exit 1
else
    print_success "Found /api/* route in APISIX"
fi

print_header "API Route Analysis"

# Extract key information
route_id=$(echo "$api_route" | jq -r '.value.id')
route_uri=$(echo "$api_route" | jq -r '.value.uri')
route_methods=$(echo "$api_route" | jq -r '.value.methods[]?' | tr '\n' ',' | sed 's/,$//')
route_upstream=$(echo "$api_route" | jq -r '.value.upstream')
route_plugins=$(echo "$api_route" | jq -r '.value.plugins')

print_info "Route ID: $route_id"
print_info "Route URI: $route_uri"
print_info "Methods: $route_methods"

echo
print_info "Upstream Configuration:"
echo "$route_upstream" | jq '.'

echo
print_info "Plugins Configuration:"
echo "$route_plugins" | jq '.'

# Check upstream target
upstream_nodes=$(echo "$route_upstream" | jq -r '.nodes // empty')
if [ -n "$upstream_nodes" ]; then
    print_success "Upstream nodes configured:"
    echo "$upstream_nodes" | jq '.'

    # Extract target host/port
    target=$(echo "$upstream_nodes" | jq -r 'keys[]' | head -1)
    print_info "Target: $target"

    # Check if target is reachable from APISIX
    if [[ "$target" == *":"* ]]; then
        host=$(echo "$target" | cut -d: -f1)
        port=$(echo "$target" | cut -d: -f2)
        print_info "Testing connectivity to $host:$port..."

        # Simple connectivity test (this might not work from outside APISIX container)
        if timeout 3 bash -c "</dev/tcp/$host/$port" 2>/dev/null; then
            print_success "Target is reachable"
        else
            print_warning "Cannot reach target (may be normal if testing from outside Docker network)"
        fi
    fi
else
    print_error "No upstream nodes configured!"
    print_warning "This means the /api/* route doesn't know where to proxy requests"
fi

# Check for problematic plugins
print_header "Plugin Analysis"

# Check for authentication plugins
auth_plugins=$(echo "$route_plugins" | jq -r 'keys[]' | grep -E "(auth|jwt|key|oauth)" || echo "")
if [ -n "$auth_plugins" ]; then
    print_warning "Authentication plugins found: $auth_plugins"
    print_info "These might be blocking access. Check plugin configuration:"
    for plugin in $auth_plugins; do
        echo "  $plugin:"
        echo "$route_plugins" | jq ".\"$plugin\""
    done
else
    print_info "No authentication plugins found on /api/* route"
fi

# Check for proxy-rewrite or other transformation plugins
transform_plugins=$(echo "$route_plugins" | jq -r 'keys[]' | grep -E "(rewrite|transform|modify)" || echo "")
if [ -n "$transform_plugins" ]; then
    print_info "Transformation plugins found: $transform_plugins"
    for plugin in $transform_plugins; do
        echo "  $plugin:"
        echo "$route_plugins" | jq ".\"$plugin\""
    done
fi

# Check route status
route_status=$(echo "$api_route" | jq -r '.value.status')
if [ "$route_status" = "1" ]; then
    print_success "Route is enabled (status: 1)"
elif [ "$route_status" = "0" ]; then
    print_error "Route is disabled (status: 0) - This is the problem!"
else
    print_warning "Route status: $route_status"
fi

print_header "Diagnosis Summary"

if [ "$route_status" = "0" ]; then
    print_error "PROBLEM FOUND: /api/* route is DISABLED"
    echo "  Solution: Enable the route with status: 1"
elif [ -z "$upstream_nodes" ] || [ "$upstream_nodes" = "{}" ]; then
    print_error "PROBLEM FOUND: No upstream configuration"
    echo "  Solution: Configure upstream to point to FastAPI container"
elif [ -n "$auth_plugins" ]; then
    print_warning "POTENTIAL PROBLEM: Authentication plugins may be misconfigured"
    echo "  Solution: Check auth plugin configuration or temporarily disable"
else
    print_warning "Route appears configured correctly, but may have other issues"
    echo "  - Check Docker network connectivity"
    echo "  - Verify FastAPI container is running and accessible"
    echo "  - Check APISIX error logs for more details"
fi

echo
print_info "Next steps to fix the issues:"
echo "1. Fix the /api/* route configuration (based on problems found above)"
echo "2. Restart APISIX to apply changes"
echo "3. Test endpoints again"
echo "4. This should fix both empty model options and 404 conversation errors"
