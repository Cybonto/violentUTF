#!/bin/bash
# Comprehensive ViolentUTF Stack Health Check Script
# Consolidates all test and diagnostic scripts into one interactive tool

set -e

# Script configuration
SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CACHE_FILE="/tmp/violentutf_stack_cache.json"
LOG_FILE="/tmp/violentutf_stack_check.log"

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Icons
CHECK_MARK="✅"
CROSS_MARK="❌"
WARNING_SIGN="⚠️"
INFO_SIGN="ℹ️"
ROCKET="🚀"
GEAR="⚙️"
LOCK="🔐"
NETWORK="🌐"
DATABASE="💾"
API="📡"

# Print functions
print_success() { echo -e "${GREEN}${CHECK_MARK} $1${NC}"; }
print_error() { echo -e "${RED}${CROSS_MARK} $1${NC}"; }
print_warning() { echo -e "${YELLOW}${WARNING_SIGN} $1${NC}"; }
print_info() { echo -e "${BLUE}${INFO_SIGN} $1${NC}"; }
print_header() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} ${BOLD}$1${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
}
print_subheader() {
    echo -e "\n${CYAN}┌────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│${NC} $1"
    echo -e "${CYAN}└────────────────────────────────────────┘${NC}"
}

# Logging
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Spinner function for long operations
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='⣾⣽⣻⢿⡿⣟⣯⣷'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# Global variables for credentials
APISIX_ADMIN_KEY=""
APISIX_API_KEY=""
AUTH_USERNAME=""
AUTH_PASSWORD=""
ENVIRONMENT=""
SAVE_CREDENTIALS=false

# Load cached credentials if they exist
load_cached_credentials() {
    if [ -f "$CACHE_FILE" ]; then
        if command -v jq &> /dev/null; then
            APISIX_ADMIN_KEY=$(jq -r '.apisix_admin_key // empty' "$CACHE_FILE" 2>/dev/null || echo "")
            APISIX_API_KEY=$(jq -r '.apisix_api_key // empty' "$CACHE_FILE" 2>/dev/null || echo "")
            AUTH_USERNAME=$(jq -r '.auth_username // empty' "$CACHE_FILE" 2>/dev/null || echo "")
            ENVIRONMENT=$(jq -r '.environment // empty' "$CACHE_FILE" 2>/dev/null || echo "")
        fi
    fi
}

# Save credentials to cache
save_credentials() {
    if [ "$SAVE_CREDENTIALS" = true ]; then
        cat > "$CACHE_FILE" <<EOF
{
  "apisix_admin_key": "$APISIX_ADMIN_KEY",
  "apisix_api_key": "$APISIX_API_KEY",
  "auth_username": "$AUTH_USERNAME",
  "environment": "$ENVIRONMENT",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
        chmod 600 "$CACHE_FILE"
        print_success "Credentials saved to cache (valid for this session)"
    fi
}

# Get credentials interactively
get_credentials() {
    print_header "${LOCK} Credential Setup"

    # Load cached credentials
    load_cached_credentials

    # Environment selection
    if [ -z "$ENVIRONMENT" ]; then
        echo -e "\n${BOLD}Select Environment:${NC}"
        echo "1) Development (local)"
        echo "2) Staging"
        echo "3) Production"
        echo -n "Enter choice [1-3]: "
        read -r env_choice

        case $env_choice in
            1) ENVIRONMENT="dev" ;;
            2) ENVIRONMENT="staging" ;;
            3) ENVIRONMENT="production" ;;
            *) ENVIRONMENT="dev" ;;
        esac
    fi

    echo -e "\n${BOLD}Environment: ${CYAN}$ENVIRONMENT${NC}"

    # APISIX Admin Key
    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo -n "Enter APISIX Admin Key (press Enter for default): "
        read -r -s input_key
        echo
        if [ -z "$input_key" ]; then
            case $ENVIRONMENT in
                dev) APISIX_ADMIN_KEY="Ds1fynPj1Zqv9hrucePsCZ35wEF4Its4" ;;
                *) APISIX_ADMIN_KEY="" ;;
            esac
        else
            APISIX_ADMIN_KEY="$input_key"
        fi
    else
        echo "Using cached APISIX Admin Key"
    fi

    # APISIX API Key (for consumer)
    if [ -z "$APISIX_API_KEY" ]; then
        echo -n "Enter APISIX API Key for requests (press Enter to discover): "
        read -r -s input_api_key
        echo
        APISIX_API_KEY="$input_api_key"
    else
        echo "Using cached APISIX API Key"
    fi

    # Auth credentials for API access
    if [ -z "$AUTH_USERNAME" ]; then
        echo -n "Enter API username (optional): "
        read -r AUTH_USERNAME
    else
        echo "Using cached username: $AUTH_USERNAME"
    fi

    if [ -n "$AUTH_USERNAME" ] && [ -z "$AUTH_PASSWORD" ]; then
        echo -n "Enter API password: "
        read -r -s AUTH_PASSWORD
        echo
    fi

    # Ask to save credentials
    if [ "$SAVE_CREDENTIALS" = false ]; then
        echo -n "Save credentials for this session? (y/n): "
        read -r save_choice
        if [[ "$save_choice" =~ ^[Yy]$ ]]; then
            SAVE_CREDENTIALS=true
            save_credentials
        fi
    fi

    # Set URLs based on environment
    case $ENVIRONMENT in
        dev)
            APISIX_URL="http://localhost:9080"
            APISIX_ADMIN_URL="http://localhost:9180"
            KEYCLOAK_URL="http://localhost:8080"
            FASTAPI_URL="http://localhost:8000"
            STREAMLIT_URL="http://localhost:8501"
            ;;
        staging|production)
            APISIX_URL="${APISIX_URL:-http://localhost:9080}"
            APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"
            KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
            FASTAPI_URL="${FASTAPI_URL:-http://localhost:8000}"
            STREAMLIT_URL="${STREAMLIT_URL:-http://localhost:8501}"
            ;;
    esac
}

# Test basic connectivity
test_connectivity() {
    print_subheader "${NETWORK} Testing Network Connectivity"

    local services=(
        "APISIX Gateway|$APISIX_URL|404"
        "APISIX Admin|$APISIX_ADMIN_URL/apisix/admin/routes|401,200"
        "Keycloak|$KEYCLOAK_URL/realms/ViolentUTF/.well-known/openid-configuration|200,404"
        "Streamlit UI|$STREAMLIT_URL|200"
    )

    for service in "${services[@]}"; do
        IFS='|' read -r name url expected <<< "$service"
        echo -n "Testing $name: "

        response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")

        if [[ ",$expected," == *",$response,"* ]]; then
            print_success "HTTP $response"
        elif [ "$response" = "000" ]; then
            print_error "Connection failed"
        else
            print_warning "HTTP $response (expected $expected)"
        fi
    done
}

# Check Docker services
check_docker_services() {
    print_subheader "${GEAR} Checking Docker Services"

    if ! command -v docker &> /dev/null; then
        print_error "Docker not installed"
        return 1
    fi

    local expected_services=(
        "apisix-apisix"
        "apisix-etcd"
        "keycloak"
        "postgres"
        "violentutf_api"
    )

    for service in "${expected_services[@]}"; do
        echo -n "Checking $service: "
        if docker ps --format "table {{.Names}}" | grep -q "$service"; then
            print_success "Running"
        else
            print_warning "Not running or different name"
        fi
    done
}

# Check APISIX configuration
check_apisix_config() {
    print_subheader "${API} APISIX Configuration Check"

    # Check consumers
    echo -e "\n${BOLD}Checking APISIX Consumers:${NC}"
    consumers=$(curl -s "$APISIX_ADMIN_URL/apisix/admin/consumers" \
        -H "X-API-KEY: $APISIX_ADMIN_KEY" 2>/dev/null)

    if [ $? -eq 0 ]; then
        consumer_count=$(echo "$consumers" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    consumers = data.get('list', [])
    print(len(consumers))
    for item in consumers:
        consumer = item.get('value', {})
        username = consumer.get('username', 'unknown')
        plugins = consumer.get('plugins', {})
        if 'key-auth' in plugins:
            key = plugins['key-auth'].get('key', '')
            print(f'  - {username}: {key[:8]}...' if len(key) > 8 else f'  - {username}: {key}')
except:
    print('0')
" 2>/dev/null || echo "0")

        if [ "$consumer_count" != "0" ]; then
            print_success "Found consumers with API keys"

            # If no API key provided, use the first found
            if [ -z "$APISIX_API_KEY" ]; then
                APISIX_API_KEY=$(echo "$consumers" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for item in data.get('list', []):
        consumer = item.get('value', {})
        plugins = consumer.get('plugins', {})
        if 'key-auth' in plugins:
            print(plugins['key-auth'].get('key', ''))
            break
except:
    pass
" 2>/dev/null)
                if [ -n "$APISIX_API_KEY" ]; then
                    print_info "Using discovered API key: ${APISIX_API_KEY:0:8}..."
                fi
            fi
        else
            print_warning "No consumers found"
        fi
    else
        print_error "Failed to query consumers"
    fi

    # Check routes
    echo -e "\n${BOLD}Checking APISIX Routes:${NC}"
    routes=$(curl -s "$APISIX_ADMIN_URL/apisix/admin/routes" \
        -H "X-API-KEY: $APISIX_ADMIN_KEY" 2>/dev/null)

    if [ $? -eq 0 ]; then
        route_info=$(echo "$routes" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    routes = data.get('list', [])

    # Count route types
    api_routes = 0
    openapi_routes = 0
    ai_routes = 0

    for item in routes:
        route = item.get('value', {})
        uri = route.get('uri', '')
        if uri.startswith('/api/'):
            api_routes += 1
        elif '/openapi/' in uri:
            openapi_routes += 1
        elif uri.startswith('/ai/'):
            ai_routes += 1

    print(f'  FastAPI routes: {api_routes}')
    print(f'  OpenAPI routes: {openapi_routes}')
    print(f'  AI routes: {ai_routes}')
    print(f'  Total routes: {len(routes)}')
except Exception as e:
    print(f'  Error parsing routes: {e}')
" 2>/dev/null)
        echo "$route_info"
    else
        print_error "Failed to query routes"
    fi
}

# Check OpenAPI configuration
check_openapi_config() {
    print_subheader "🔌 OpenAPI Configuration Check"

    # Check ai-tokens.env
    echo -e "\n${BOLD}Checking ai-tokens.env:${NC}"
    if [ -f "$REPO_ROOT/ai-tokens.env" ]; then
        OPENAPI_ID=$(grep "^OPENAPI_1_ID=" "$REPO_ROOT/ai-tokens.env" | cut -d'=' -f2 | cut -d'#' -f1 | tr -d ' ')
        OPENAPI_ENABLED=$(grep "^OPENAPI_1_ENABLED=" "$REPO_ROOT/ai-tokens.env" | cut -d'=' -f2 | cut -d'#' -f1 | tr -d ' ')
        OPENAPI_URL=$(grep "^OPENAPI_1_BASE_URL=" "$REPO_ROOT/ai-tokens.env" | cut -d'=' -f2 | cut -d'#' -f1 | tr -d ' ')

        echo "  OPENAPI_1_ENABLED: $OPENAPI_ENABLED"
        echo "  OPENAPI_1_ID: $OPENAPI_ID"
        echo "  OPENAPI_1_BASE_URL: $OPENAPI_URL"

        if [ "$OPENAPI_ENABLED" = "true" ]; then
            # Check for OpenAPI routes
            echo -e "\n${BOLD}Checking OpenAPI Routes:${NC}"
            routes=$(curl -s "$APISIX_ADMIN_URL/apisix/admin/routes" \
                -H "X-API-KEY: $APISIX_ADMIN_KEY" 2>/dev/null | \
                python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    found = False
    for item in data.get('list', []):
        route = item.get('value', {})
        uri = route.get('uri', '')
        if '$OPENAPI_ID' in uri:
            print(f'  ✓ {uri}')
            found = True
    if not found:
        print('  ✗ No routes found for $OPENAPI_ID')
except:
    print('  ✗ Error checking routes')
" 2>/dev/null)
            echo "$routes"
        fi
    else
        print_warning "ai-tokens.env not found"
    fi
}

# Test API endpoints
test_api_endpoints() {
    print_subheader "${ROCKET} Testing API Endpoints"

    # Get auth token if credentials provided
    local auth_header=""
    if [ -n "$AUTH_USERNAME" ] && [ -n "$AUTH_PASSWORD" ]; then
        echo -n "Getting auth token: "
        token=$(curl -s -X POST "$APISIX_URL/api/v1/auth/login" \
            -H "Content-Type: application/json" \
            -d "{\"username\": \"$AUTH_USERNAME\", \"password\": \"$AUTH_PASSWORD\"}" | \
            python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

        if [ -n "$token" ]; then
            auth_header="Authorization: Bearer $token"
            print_success "Token obtained"
        else
            print_warning "Failed to get token"
        fi
    fi

    # Test endpoints
    local endpoints=(
        "Health Check|/api/v1/health|200|"
        "Generator Types|/api/v1/generators/types|200,401,403|$auth_header"
        "Orchestrator Types|/api/v1/orchestrators/types|200,401,403|$auth_header"
        "API Docs|/api/docs|200|"
        "API ReDoc|/api/redoc|200|"
    )

    for endpoint in "${endpoints[@]}"; do
        IFS='|' read -r name path expected auth <<< "$endpoint"
        echo -n "Testing $name: "

        if [ -n "$auth" ]; then
            response=$(curl -s -o /dev/null -w "%{http_code}" \
                -H "$auth" \
                "$APISIX_URL$path" 2>/dev/null || echo "000")
        else
            response=$(curl -s -o /dev/null -w "%{http_code}" \
                "$APISIX_URL$path" 2>/dev/null || echo "000")
        fi

        if [[ ",$expected," == *",$response,"* ]]; then
            print_success "HTTP $response"
        else
            print_warning "HTTP $response (expected $expected)"
        fi
    done
}

# Test OpenAPI provider
test_openapi_provider() {
    if [ "$OPENAPI_ENABLED" != "true" ]; then
        return
    fi

    print_subheader "🤖 Testing OpenAPI Provider"

    echo -e "\n${BOLD}1. Testing Model Discovery Endpoint:${NC}"
    echo -n "  GET /ai/openapi/$OPENAPI_ID/api/v1/models: "

    # Test models endpoint
    response=$(curl -s "$APISIX_URL/ai/openapi/$OPENAPI_ID/api/v1/models" \
        -H "apikey: $APISIX_API_KEY" \
        -w "\nHTTP_STATUS:%{http_code}" 2>/dev/null)

    http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d':' -f2)

    case $http_status in
        200)
            print_success "HTTP 200"
            # Parse and display available models
            echo "  Available models:"
            echo "$response" | grep -v "HTTP_STATUS:" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    models = data.get('data', [])
    if models:
        for model in models[:5]:  # Show first 5 models
            print(f'    • {model.get(\"id\", \"unknown\")}')
        if len(models) > 5:
            print(f'    ... and {len(models)-5} more')
    else:
        print('    (No models found)')
except Exception as e:
    print(f'    (Error parsing response: {e})')
" 2>/dev/null
            ;;
        401) print_error "Authentication failed (HTTP 401)" ;;
        404) print_error "Route not found (HTTP 404)" ;;
        429) print_warning "Rate limited (HTTP 429)" ;;
        *) print_warning "HTTP $http_status" ;;
    esac

    echo -e "\n${BOLD}2. Testing Chat Completions Endpoint:${NC}"
    echo -n "  POST /ai/openapi/$OPENAPI_ID/api/v1/chat/completions: "

    # Test chat completions with minimal payload
    response=$(curl -s -X POST "$APISIX_URL/ai/openapi/$OPENAPI_ID/api/v1/chat/completions" \
        -H "apikey: $APISIX_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"model": "claude_3_5_sonnet", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 10}' \
        -w "\nHTTP_STATUS:%{http_code}" \
        --max-time 30 2>/dev/null)

    http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d':' -f2)

    case $http_status in
        200)
            print_success "HTTP 200"
            echo "  Response validation:"
            # Validate response structure
            echo "$response" | grep -v "HTTP_STATUS:" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    checks = []
    if 'object' in data and data['object'] == 'chat.completion':
        checks.append('✓ Valid completion object')
    if 'choices' in data and len(data['choices']) > 0:
        checks.append('✓ Contains choices')
    if 'model' in data:
        checks.append(f'✓ Model: {data[\"model\"]}')
    if 'created' in data:
        checks.append('✓ Has timestamp')
    for check in checks:
        print(f'    {check}')
except Exception as e:
    print(f'    ✗ Invalid response format: {e}')
" 2>/dev/null
            ;;
        401) print_error "Authentication failed (HTTP 401)" ;;
        404) print_error "Route not found (HTTP 404)" ;;
        429)
            print_warning "Rate limited (HTTP 429)"
            echo "  Rate limit details:"
            echo "$response" | grep -v "HTTP_STATUS:" | python3 -m json.tool 2>/dev/null | grep -E "(message|retry)" | head -3 | sed 's/^/    /'
            ;;
        500|502|503) print_error "Server error (HTTP $http_status)" ;;
        000) print_error "Request timeout (30s)" ;;
        *) print_warning "HTTP $http_status" ;;
    esac

    echo -e "\n${BOLD}3. Testing Embeddings Endpoint:${NC}"
    echo -n "  POST /ai/openapi/$OPENAPI_ID/api/v1/embeddings: "

    # Test embeddings endpoint
    response=$(curl -s -X POST "$APISIX_URL/ai/openapi/$OPENAPI_ID/api/v1/embeddings" \
        -H "apikey: $APISIX_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"model": "cohere_english_v3", "input": "test"}' \
        -w "\nHTTP_STATUS:%{http_code}" \
        --max-time 10 2>/dev/null)

    http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d':' -f2)

    case $http_status in
        200)
            print_success "HTTP 200"
            echo "  Response validation:"
            echo "$response" | grep -v "HTTP_STATUS:" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'object' in data and data['object'] == 'list':
        print('    ✓ Valid embedding response')
    if 'data' in data and len(data['data']) > 0:
        print(f'    ✓ Contains {len(data[\"data\"])} embedding(s)')
    if 'model' in data:
        print(f'    ✓ Model: {data[\"model\"]}')
except Exception as e:
    print(f'    ✗ Invalid response: {e}')
" 2>/dev/null
            ;;
        401) print_error "Authentication failed (HTTP 401)" ;;
        403)
            print_warning "Forbidden (HTTP 403)"
            echo "    Note: Embeddings endpoint may not be available in GSAi"
            ;;
        404) print_error "Route not found (HTTP 404)" ;;
        422)
            print_warning "Invalid request (HTTP 422)"
            echo "  Error details:"
            echo "$response" | grep -v "HTTP_STATUS:" | python3 -m json.tool 2>/dev/null | grep -E "(detail|message)" | head -3 | sed 's/^/    /'
            ;;
        429) print_warning "Rate limited (HTTP 429)" ;;
        *) print_warning "HTTP $http_status" ;;
    esac

    echo -e "\n${BOLD}4. Testing Route Authentication:${NC}"
    echo -n "  Testing without API key: "

    # Test without authentication
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        "$APISIX_URL/ai/openapi/$OPENAPI_ID/api/v1/models" 2>/dev/null)

    if [ "$response" = "401" ]; then
        print_success "Correctly rejected (HTTP 401)"
    else
        print_warning "HTTP $response (expected 401)"
    fi

    echo -n "  Testing with invalid API key: "

    # Test with invalid key
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "apikey: invalid_key_12345" \
        "$APISIX_URL/ai/openapi/$OPENAPI_ID/api/v1/models" 2>/dev/null)

    if [ "$response" = "401" ]; then
        print_success "Correctly rejected (HTTP 401)"
    else
        print_warning "HTTP $response (expected 401)"
    fi

    echo -e "\n${BOLD}5. Testing Response Times:${NC}"

    # Test response time for models endpoint (should be fast)
    echo -n "  Models endpoint latency: "

    # Use Python for cross-platform millisecond timing
    latency=$(python3 -c "
import time
import urllib.request
import urllib.error
start = time.time()
try:
    req = urllib.request.Request(
        '$APISIX_URL/ai/openapi/$OPENAPI_ID/api/v1/models',
        headers={'apikey': '$APISIX_API_KEY'}
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        response.read()
except:
    pass
end = time.time()
print(int((end - start) * 1000))
" 2>/dev/null)

    if [ -z "$latency" ]; then
        print_error "Failed to measure"
    elif [ $latency -lt 1000 ]; then
        print_success "${latency}ms"
    elif [ $latency -lt 3000 ]; then
        print_warning "${latency}ms (slow)"
    else
        print_error "${latency}ms (very slow)"
    fi
}

# Troubleshoot OpenAPI 404 errors
troubleshoot_openapi_404() {
    print_subheader "🔍 Troubleshooting OpenAPI 404 Errors"

    echo "Analyzing why OpenAPI routes return 404..."

    # Get detailed route info
    route_details=$(curl -s "$APISIX_ADMIN_URL/apisix/admin/routes" \
        -H "X-API-KEY: $APISIX_ADMIN_KEY" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    found_routes = []
    for item in data.get('list', []):
        route = item.get('value', {})
        uri = route.get('uri', '')
        if '$OPENAPI_ID' in uri:
            found_routes.append(route)

    if found_routes:
        print('\\nFound OpenAPI routes in APISIX:')
        for r in found_routes:
            print(f\"\\n  Route URI: {r.get('uri', 'unknown')}\")
            print(f\"  Route ID: {r.get('id', 'unknown')}\")
            print(f\"  Status: {'ENABLED' if r.get('status', 1) == 1 else 'DISABLED'}\")

            # Check upstream configuration
            upstream = r.get('upstream', {})
            if not upstream:
                print('  ❌ PROBLEM: No upstream configured!')
                print('     This route has no backend target defined.')
            elif 'nodes' not in upstream or not upstream.get('nodes'):
                print('  ❌ PROBLEM: No upstream nodes defined!')
                print('     The upstream exists but has no target servers.')
            else:
                nodes = upstream.get('nodes', {})
                if nodes:
                    print('  Upstream targets:')
                    for node, weight in nodes.items():
                        print(f'    - {node} (weight: {weight})')
                else:
                    print('  ❌ PROBLEM: Empty upstream nodes!')

            # Check plugins
            plugins = r.get('plugins', {})
            if plugins:
                print(f'  Plugins: {list(plugins.keys())}')
                if 'key-auth' in plugins:
                    print('    ✓ Authentication required (key-auth)')
                if 'proxy-rewrite' in plugins:
                    rewrite = plugins.get('proxy-rewrite', {})
                    print('  Proxy-rewrite configuration:')
                    if 'uri' in rewrite:
                        print(f'    URI rewrite: {rewrite[\"uri\"]}')
                    if 'scheme' in rewrite:
                        print(f'    Scheme: {rewrite[\"scheme\"]}')
                    if 'host' in rewrite:
                        print(f'    Host: {rewrite[\"host\"]}')
                    if 'headers' in rewrite:
                        print(f'    Headers: {rewrite[\"headers\"]}')

            # Check if route is disabled
            if r.get('status', 1) == 0:
                print('  ❌ PROBLEM: Route is DISABLED!')
    else:
        print('\\n❌ No routes found for provider ID: $OPENAPI_ID')
        print('   This explains the 404 errors - routes need to be created.')
except Exception as e:
    print(f'Error analyzing routes: {e}')
" 2>/dev/null)

    if [ -n "$route_details" ]; then
        echo "$route_details"
    fi

    echo -e "\n${BOLD}Diagnosis Summary:${NC}"

    # Check if routes exist
    routes_exist=$(echo "$route_details" | grep -c "Route URI:" || echo "0")

    if [ "$routes_exist" = "0" ]; then
        print_error "No OpenAPI routes found in APISIX"
        echo "  Solution: Run setup script to create routes"
    else
        # Check for common issues
        if echo "$route_details" | grep -q "No upstream configured"; then
            print_error "Routes exist but have no upstream configuration"
            echo "  Solution: Routes need to be configured with upstream targets"
            echo "  Run: ./setup_macos.sh to reconfigure"
        elif echo "$route_details" | grep -q "DISABLED"; then
            print_error "Routes exist but are disabled"
            echo "  Solution: Enable the routes in APISIX configuration"
        elif echo "$route_details" | grep -q "Empty upstream nodes"; then
            print_error "Routes have upstream but no target nodes"
            echo "  Solution: Configure upstream nodes in route configuration"
        else
            print_warning "Routes appear configured but still return 404"
            echo "  Possible causes:"
            echo "  - Network connectivity to upstream target"
            echo "  - Upstream service not running"
            echo "  - Incorrect upstream URL in configuration"
        fi
    fi

    echo -e "\n${BOLD}Testing Direct Upstream Connectivity:${NC}"

    # Test if we can reach the upstream directly
    if [ -n "$OPENAPI_URL" ]; then
        echo -n "  Testing direct connection to $OPENAPI_URL: "

        # Extract just the hostname from the URL
        upstream_host=$(echo "$OPENAPI_URL" | sed 's|https\?://||' | sed 's|/.*||' | cut -d':' -f1)
        upstream_port=$(echo "$OPENAPI_URL" | sed 's|https\?://||' | sed 's|/.*||' | grep ':' | cut -d':' -f2 || echo "443")

        # Test connectivity from host
        if timeout 3 bash -c "echo > /dev/tcp/$upstream_host/$upstream_port" 2>/dev/null; then
            print_success "Reachable from host"
        else
            print_error "Not reachable from host"
        fi

        # Test connectivity from APISIX container
        echo -n "  Testing from APISIX container: "
        container_test=$(docker exec apisix-apisix sh -c "curl -s -I --max-time 3 https://$upstream_host/api/v1/models 2>/dev/null | head -1" 2>/dev/null)
        if echo "$container_test" | grep -q "HTTP"; then
            http_status=$(echo "$container_test" | grep -oE "[0-9]{3}")
            print_success "Reachable (HTTP $http_status)"
        else
            print_error "Not reachable from container"
        fi

        # Test SSL certificate if HTTPS
        if [[ "$OPENAPI_URL" == https://* ]]; then
            echo -n "  Testing SSL certificate: "
            cert_check=$(timeout 3 openssl s_client -connect "$upstream_host:$upstream_port" -servername "$upstream_host" </dev/null 2>/dev/null | openssl x509 -noout 2>&1)
            if [ $? -eq 0 ]; then
                print_success "Valid SSL certificate"
            else
                print_warning "SSL certificate issue or unreachable"
            fi
        fi
    fi

    echo -e "\n${BOLD}Checking APISIX Proxy Configuration:${NC}"

    # Check if proxy-rewrite might be causing issues
    if echo "$route_details" | grep -q "proxy-rewrite"; then
        echo "  ⚠️ Routes use proxy-rewrite plugin"
        echo "  This can modify the request path/headers"

        # Check for common proxy-rewrite issues
        if echo "$route_details" | grep -q "URI rewrite:"; then
            echo "  URI is being rewritten - verify the target path is correct"
        fi

        if echo "$route_details" | grep -q "Scheme: http" && [[ "$OPENAPI_URL" == https://* ]]; then
            print_error "MISMATCH: Route uses HTTP but upstream needs HTTPS!"
            echo "  This is likely causing the 404 errors"
        fi
    fi

    echo -e "\n${BOLD}Checking Raw Route Configuration:${NC}"

    # Get one route's complete configuration to check for regex_uri
    sample_route_id="openapi-${OPENAPI_ID}-models-"
    echo "  Fetching raw config for route: $sample_route_id"

    raw_route=$(curl -s "${APISIX_ADMIN_URL}/apisix/admin/routes/${sample_route_id}" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null)

    if echo "$raw_route" | grep -q '"id"'; then
        echo "  Raw proxy-rewrite configuration:"
        echo "$raw_route" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    route = data.get('value', {})
    plugins = route.get('plugins', {})
    proxy_rewrite = plugins.get('proxy-rewrite', {})

    print('    Full proxy-rewrite config:')
    for key, value in proxy_rewrite.items():
        if key == 'regex_uri':
            print(f'      ✓ {key}: {value}')
        else:
            print(f'      {key}: {value}')

    if 'regex_uri' not in proxy_rewrite:
        print('      ❌ regex_uri: NOT FOUND')
except Exception as e:
    print(f'    Error parsing: {e}')
" 2>/dev/null
    else
        print_error "Could not fetch route configuration"
    fi

    echo -e "\n${BOLD}Recommended Actions:${NC}"
    echo "1. Verify OPENAPI_1_ID in ai-tokens.env matches: $OPENAPI_ID"
    echo "2. Check OPENAPI_1_BASE_URL is correct: $OPENAPI_URL"
    echo "3. Re-run setup script for your environment"
    echo "4. If using staging/production, ensure proper network access to GSAi"

    # Additional recommendations based on findings
    if echo "$route_details" | grep -q "Scheme: http" && [[ "$OPENAPI_URL" == https://* ]]; then
        echo -e "\n${BOLD}${RED}CRITICAL FIX NEEDED:${NC}"
        echo "  The routes are configured for HTTP but GSAi requires HTTPS"
        echo "  Update route configuration to use scheme: https"
    fi
}

# Generate summary report
generate_report() {
    print_header "📊 Stack Health Summary"

    echo -e "\n${BOLD}Environment:${NC} $ENVIRONMENT"
    echo -e "${BOLD}Timestamp:${NC} $(date)"
    echo -e "${BOLD}Log file:${NC} $LOG_FILE"

    if [ "$SAVE_CREDENTIALS" = true ]; then
        echo -e "${BOLD}Credentials cached:${NC} Yes (${CACHE_FILE})"
    fi

    echo -e "\n${BOLD}Quick Actions:${NC}"
    echo "  • Review logs: cat $LOG_FILE"
    echo "  • Clear cache: rm -f $CACHE_FILE"
    echo "  • Re-run checks: $0"

    if [ -n "$OPENAPI_ID" ] && [ "$OPENAPI_ID" = "custom-api-1" ]; then
        print_warning "\nDetected potential OpenAPI misconfiguration:"
        echo "  OPENAPI_1_ID is set to 'custom-api-1' (default)"
        echo "  Consider changing to 'gsai-api-1' if using GSAi"
    fi
}

# Interactive menu
show_menu() {
    while true; do
        print_header "ViolentUTF Stack Check v${SCRIPT_VERSION}"
        echo -e "\n${BOLD}Select Test Category:${NC}"
        echo "1) Quick Health Check (Basic connectivity)"
        echo "2) Full System Check (All tests)"
        echo "3) APISIX Configuration"
        echo "4) API Endpoints"
        echo "5) OpenAPI Provider"
        echo "6) Docker Services"
        echo "7) Troubleshoot OpenAPI 404"
        echo "8) Update Credentials"
        echo "9) Clear Cache"
        echo "10) Exit"

        echo -n -e "\n${BOLD}Enter choice [1-10]:${NC} "
        read -r choice

        case $choice in
            1)
                test_connectivity
                ;;
            2)
                test_connectivity
                check_docker_services
                check_apisix_config
                check_openapi_config
                test_api_endpoints
                test_openapi_provider
                generate_report
                ;;
            3)
                check_apisix_config
                ;;
            4)
                test_api_endpoints
                ;;
            5)
                check_openapi_config
                test_openapi_provider
                ;;
            6)
                check_docker_services
                ;;
            7)
                troubleshoot_openapi_404
                ;;
            8)
                APISIX_ADMIN_KEY=""
                APISIX_API_KEY=""
                AUTH_USERNAME=""
                AUTH_PASSWORD=""
                get_credentials
                ;;
            9)
                rm -f "$CACHE_FILE"
                print_success "Cache cleared"
                ;;
            10)
                echo "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Invalid choice"
                ;;
        esac

        echo -n -e "\n${BOLD}Press Enter to continue...${NC}"
        read -r
    done
}

# Main execution
main() {
    # Initialize log
    echo "=== ViolentUTF Stack Check Started ===" > "$LOG_FILE"
    log "Script version: $SCRIPT_VERSION"

    # Get credentials
    get_credentials

    # Run menu or execute single test if specified
    if [ $# -gt 0 ]; then
        case "$1" in
            --quick)
                test_connectivity
                ;;
            --full)
                test_connectivity
                check_docker_services
                check_apisix_config
                check_openapi_config
                test_api_endpoints
                test_openapi_provider
                generate_report
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --quick    Run quick health check"
                echo "  --full     Run full system check"
                echo "  --help     Show this help"
                echo ""
                echo "Without options, interactive menu is shown"
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    else
        show_menu
    fi

    # Save credentials if requested
    if [ "$SAVE_CREDENTIALS" = true ]; then
        save_credentials
    fi
}

# Trap errors and cleanup
trap 'echo -e "\n${RED}Script interrupted${NC}"; exit 1' INT TERM

# Run main function
main "$@"
