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

# Advanced OpenAPI diagnostics for 500 errors
test_openapi_advanced_diagnostics() {
    print_header "🔬 Advanced OpenAPI Diagnostics for 500 Error"

    local PROVIDER_ID="${1:-gsai-api-1}"
    local OPENAPI_ROUTE_PREFIX="/ai/openapi"

    echo -e "\n${BOLD}Phase 1: Route Configuration Analysis${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # 1. Get route configuration from APISIX Admin API
    echo -e "\n${CYAN}1.1 Fetching OpenAPI route configurations:${NC}"
    local routes_response=$(curl -s -X GET "http://localhost:9180/apisix/admin/routes" \
        -H "X-API-KEY: $APISIX_ADMIN_KEY" 2>/dev/null)

    if [ $? -eq 0 ]; then
        echo "$routes_response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
routes = data.get('list', [])
openapi_routes = [r['value'] for r in routes if r['value']['id'].startswith('openapi-$PROVIDER_ID')]
print(f'  Found {len(openapi_routes)} OpenAPI routes for $PROVIDER_ID')
for route in openapi_routes:
    print(f'  • Route ID: {route[\"id\"]}')
    print(f'    URI: {route.get(\"uri\", \"N/A\")}')
    upstream = route.get('upstream', {})
    nodes = upstream.get('nodes', {})
    for node in nodes:
        print(f'    Upstream: {node}')
    # Check for TLS configuration
    tls_config = upstream.get('tls', {})
    if tls_config:
        print(f'    TLS Verify: {tls_config.get(\"verify\", \"default\")}')
    else:
        print('    TLS Config: Not configured ⚠️')
    # Check proxy-rewrite
    plugins = route.get('plugins', {})
    if 'proxy-rewrite' in plugins:
        rewrite = plugins['proxy-rewrite']
        if 'regex_uri' in rewrite:
            print(f'    Regex URI: {rewrite[\"regex_uri\"]}')
        headers = rewrite.get('headers', {}).get('set', {})
        if 'Host' in headers:
            print(f'    Host Header: {headers[\"Host\"][:30]}...')
        else:
            print('    Host Header: Not set ⚠️')
" 2>/dev/null || echo "  Error parsing routes"
    else
        echo "  ❌ Failed to fetch routes from APISIX Admin API"
    fi

    echo -e "\n${BOLD}Phase 2: SSL/TLS Connectivity Test${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # 2. Test direct connectivity from APISIX container to upstream
    echo -e "\n${CYAN}2.1 Testing direct HTTPS connection from APISIX container:${NC}"

    # Get the actual upstream URL and auth token
    local UPSTREAM_URL="https://api.dev.gsai.mcaas.fcs.gsa.gov"
    local AUTH_TOKEN="${OPENAPI_1_AUTH_TOKEN:-$OPENAPI_AUTH_TOKEN}"

    echo "  Testing: $UPSTREAM_URL/api/v1/models"

    # Test with curl from inside APISIX container
    docker exec apisix-apisix-1 sh -c "
        echo '  2.1.1 DNS Resolution:'
        nslookup api.dev.gsai.mcaas.fcs.gsa.gov 2>/dev/null | grep -A1 'Name:' | tail -1 | sed 's/^/    /'

        echo '  2.1.2 Basic connectivity (without auth):'
        curl -s -o /dev/null -w '    HTTP Status: %{http_code}, Time: %{time_total}s\n' \
            -k --connect-timeout 5 \
            'https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/models' 2>/dev/null || echo '    ❌ Connection failed'

        echo '  2.1.3 With Bearer token:'
        if [ -n \"$AUTH_TOKEN\" ]; then
            curl -s -o /dev/null -w '    HTTP Status: %{http_code}, Time: %{time_total}s\n' \
                -k --connect-timeout 5 \
                -H \"Authorization: Bearer $AUTH_TOKEN\" \
                'https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/models' 2>/dev/null || echo '    ❌ Connection failed'
        else
            echo '    ⚠️ No auth token configured'
        fi

        echo '  2.1.4 SSL Certificate details:'
        echo | openssl s_client -connect api.dev.gsai.mcaas.fcs.gsa.gov:443 2>/dev/null | \
            grep -E '(subject=|issuer=|Verify return code)' | head -3 | sed 's/^/    /'
    " 2>/dev/null || echo "  ❌ Failed to execute tests in APISIX container"

    echo -e "\n${BOLD}Phase 3: Request Flow Analysis${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # 3. Test the full request flow with detailed debugging
    echo -e "\n${CYAN}3.1 Testing full request flow through APISIX:${NC}"

    # Create a test request with tracking headers
    local REQUEST_ID="test-$(date +%s)"

    echo "  Request ID: $REQUEST_ID"
    echo "  Testing: GET $APISIX_URL${OPENAPI_ROUTE_PREFIX}/$PROVIDER_ID/v1/models"

    # Make request with verbose output
    local full_response=$(curl -v -s \
        -X GET "$APISIX_URL${OPENAPI_ROUTE_PREFIX}/$PROVIDER_ID/v1/models" \
        -H "apikey: $APISIX_API_KEY" \
        -H "X-Request-ID: $REQUEST_ID" \
        -w "\n===METRICS===\nHTTP_CODE:%{http_code}\nTIME_TOTAL:%{time_total}\nTIME_CONNECT:%{time_connect}\nTIME_STARTTRANSFER:%{time_starttransfer}\n" \
        2>&1)

    # Parse response
    local http_code=$(echo "$full_response" | grep "HTTP_CODE:" | cut -d: -f2)
    local time_total=$(echo "$full_response" | grep "TIME_TOTAL:" | cut -d: -f2)

    echo "  Response:"
    echo "    HTTP Status: $http_code"
    echo "    Total Time: ${time_total}s"

    if [ "$http_code" = "500" ]; then
        echo -e "\n  ${RED}500 Error Details:${NC}"
        # Extract error body
        echo "$full_response" | grep -A10 "500 Internal Server Error" | head -15 | sed 's/^/    /'

        # Check APISIX error logs
        echo -e "\n  ${CYAN}3.2 APISIX Error Logs (last 10 lines):${NC}"
        docker logs apisix-apisix-1 2>&1 | grep -E "(error|ERROR|failed|Failed)" | tail -10 | sed 's/^/    /'
    fi

    echo -e "\n${BOLD}Phase 4: Authentication Token Validation${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # 4. Validate authentication token configuration
    echo -e "\n${CYAN}4.1 Checking authentication configuration:${NC}"

    # Check if token is configured in route
    echo "$routes_response" | python3 -c "
import sys, json
data = json.load(sys.stdin)
routes = data.get('list', [])
for r in routes:
    route = r['value']
    if route['id'].startswith('openapi-$PROVIDER_ID'):
        plugins = route.get('plugins', {})
        if 'proxy-rewrite' in plugins:
            headers = plugins['proxy-rewrite'].get('headers', {}).get('set', {})
            if 'Authorization' in headers:
                auth_value = headers['Authorization']
                if '\${' in auth_value:
                    print(f'  Route {route[\"id\"]}: Uses variable substitution')
                elif 'Bearer' in auth_value:
                    print(f'  Route {route[\"id\"]}: Has Bearer token (first 20 chars): {auth_value[:20]}...')
                else:
                    print(f'  Route {route[\"id\"]}: Unknown auth format')
            else:
                print(f'  Route {route[\"id\"]}: ⚠️ No Authorization header configured')
" 2>/dev/null

    # Check environment variables
    echo -e "\n  ${CYAN}4.2 Environment variables:${NC}"
    if [ -n "$OPENAPI_1_AUTH_TOKEN" ]; then
        echo "    OPENAPI_1_AUTH_TOKEN: Set (${#OPENAPI_1_AUTH_TOKEN} chars)"
    else
        echo "    OPENAPI_1_AUTH_TOKEN: ⚠️ Not set"
    fi

    echo -e "\n${BOLD}Phase 5: Summary and Recommendations${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    echo -e "\n${CYAN}Diagnosis Summary:${NC}"

    # Analyze results and provide recommendations
    if [ "$http_code" = "500" ]; then
        echo "  ${RED}Primary Issue: 500 Internal Server Error${NC}"
        echo ""
        echo "  Possible causes:"
        echo "    1. SSL/TLS handshake failure with upstream"
        echo "    2. Missing or invalid authentication token"
        echo "    3. Incorrect Host header for SNI"
        echo "    4. Request transformation error"
        echo ""
        echo "  ${YELLOW}Recommended actions:${NC}"
        echo "    1. Run setup_macos.sh to recreate routes with SSL fixes"
        echo "    2. Verify OPENAPI_1_AUTH_TOKEN is set correctly"
        echo "    3. Check APISIX error logs for detailed error messages"
        echo "    4. Ensure routes have 'tls.verify: false' for corporate certs"
    elif [ "$http_code" = "404" ]; then
        echo "  ${RED}Primary Issue: 404 Not Found${NC}"
        echo ""
        echo "  The route is not matching. Check:"
        echo "    1. Route URI patterns in APISIX"
        echo "    2. Path prefix configuration"
        echo "    3. Route priority conflicts"
    elif [ "$http_code" = "200" ]; then
        echo "  ${GREEN}✅ OpenAPI routes are working correctly${NC}"
    else
        echo "  ${YELLOW}Unexpected status: $http_code${NC}"
    fi
}

# Helper functions for diagnostic tree
diag_print_level() {
    local level=$1
    local msg=$2
    case $level in
        1) echo -e "\n${BOLD}${BLUE}═══ LEVEL $level: $msg ═══${NC}" ;;
        2) echo -e "\n${CYAN}  ── Level $level: $msg ──${NC}" ;;
        3) echo -e "\n${YELLOW}    ∙ Level $level: $msg${NC}" ;;
    esac
}

diag_print_test() {
    echo -e "${BOLD}Testing:${NC} $1"
}

# Comprehensive OpenAPI debugging with diagnostic decision tree
comprehensive_openapi_debug() {
    echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║         OPENAPI DIAGNOSTIC DECISION TREE                  ║${NC}"
    echo -e "${BOLD}${BLUE}║                  Environment: $ENVIRONMENT                ║${NC}"
    echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"

    # Simple counters for results
    local passed=0
    local failed=0
    local warned=0
    local ROOT_CAUSE=""

    echo -e "\n${BOLD}${BLUE}═══ LEVEL 1: APISIX Accessibility ═══${NC}"
    echo -e "${BOLD}Testing:${NC} Can we connect to APISIX Admin API?"

    local admin_response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 \
        "$APISIX_ADMIN_URL/apisix/admin/routes" \
        -H "X-API-KEY: $APISIX_ADMIN_KEY" 2>/dev/null)

    if [ "$admin_response" != "200" ]; then
        echo -e "  ${RED}✗ FAIL${NC}: Cannot reach APISIX Admin API (HTTP $admin_response)"
        ((failed++))

        echo -e "\n${CYAN}  ── Level 2: Investigating APISIX connectivity ──${NC}"
        echo -e "${BOLD}Testing:${NC} Is APISIX container running?"

        if docker ps | grep -q "apisix-apisix"; then
            echo -e "  ${GREEN}✓ PASS${NC}: APISIX container is running"
            ((passed++))

            echo -e "\n${YELLOW}    ∙ Level 3: Network configuration check${NC}"
            echo -e "${BOLD}Testing:${NC} Is port 9180 exposed?"

            if docker port apisix-apisix | grep -q "9180"; then
                echo -e "  ${GREEN}✓ PASS${NC}: Port 9180 is exposed"
                ((passed++))
                echo -e "  ${YELLOW}Debug: Admin URL: $APISIX_ADMIN_URL${NC}"
                echo -e "  ${YELLOW}Debug: Check Admin Key correctness${NC}"
                ROOT_CAUSE="APISIX Admin API key might be incorrect"
            else
                echo -e "  ${RED}✗ FAIL${NC}: Port 9180 not exposed"
                ((failed++))
                echo -e "  ${YELLOW}Debug: Port mapping issue detected${NC}"
                ROOT_CAUSE="APISIX Admin port not properly exposed"
            fi
        else
            echo -e "  ${RED}✗ FAIL${NC}: APISIX container not running"
            ((failed++))
            echo -e "  ${YELLOW}Debug: Container status:${NC}"
            docker ps -a | grep apisix | head -3
            ROOT_CAUSE="APISIX container is down - restart required"
        fi
    else
        echo -e "  ${GREEN}✓ PASS${NC}: APISIX Admin API is accessible"
        ((passed++))

        echo -e "\n${CYAN}  ── Level 2: Route Existence Check ──${NC}"

        # Load OpenAPI configuration
        if [ -f "$REPO_ROOT/ai-tokens.env" ]; then
            OPENAPI_ID=$(grep "^OPENAPI_1_ID=" "$REPO_ROOT/ai-tokens.env" | cut -d'=' -f2 | cut -d'#' -f1 | tr -d ' ')
            OPENAPI_URL=$(grep "^OPENAPI_1_BASE_URL=" "$REPO_ROOT/ai-tokens.env" | cut -d'=' -f2 | cut -d'#' -f1 | tr -d ' ')
            echo "  Configuration loaded: ID=$OPENAPI_ID"
        else
            echo -e "  ${YELLOW}⚠ Warning: ai-tokens.env not found at $REPO_ROOT${NC}"
            OPENAPI_ID=""
        fi

        echo -e "${BOLD}Testing:${NC} Looking for OpenAPI routes with ID: ${OPENAPI_ID:-[NOT SET]}"

        local route_list=$(curl -s "$APISIX_ADMIN_URL/apisix/admin/routes" \
            -H "X-API-KEY: $APISIX_ADMIN_KEY" 2>/dev/null)

        local route_count=0
        if [ -n "$OPENAPI_ID" ]; then
            route_count=$(echo "$route_list" | grep -o "\"id\":\"[^\"]*${OPENAPI_ID}[^\"]*\"" | wc -l | tr -d ' ')
        fi

        echo "  Found $route_count routes"

        if [ "${route_count:-0}" -eq 0 ]; then
            echo -e "  ${RED}✗ FAIL${NC}: No OpenAPI routes found"
            ((failed++))

            if [ -z "$OPENAPI_ID" ]; then
                echo -e "  ${YELLOW}Debug: OPENAPI_ID is not configured${NC}"
                ROOT_CAUSE="OpenAPI provider not configured in ai-tokens.env"
            else
                echo -e "  ${YELLOW}Debug: Expected routes with ID pattern: openapi-${OPENAPI_ID}-*${NC}"
                echo -e "  ${YELLOW}Debug: Total routes in APISIX: $(echo "$route_list" | grep -c '"id"')${NC}"
                ROOT_CAUSE="OpenAPI routes not configured - setup required"
            fi
        else
            echo -e "  ${GREEN}✓ PASS${NC}: Found $route_count OpenAPI routes"
            ((passed++))

            echo -e "\n${CYAN}  ── Level 3: Route Configuration Analysis ──${NC}"
            echo -e "${BOLD}Testing:${NC} Checking route configuration"

            # Check for regex_uri
            local models_route_id="openapi-${OPENAPI_ID}-models"
            local route_id=$(echo "$route_list" | grep -o "\"id\":\"${models_route_id}[^\"]*\"" | head -1 | cut -d'"' -f4)

            if [ -n "$route_id" ]; then
                echo "  Route ID found: $route_id"
                local route_config=$(curl -s "$APISIX_ADMIN_URL/apisix/admin/routes/$route_id" \
                    -H "X-API-KEY: $APISIX_ADMIN_KEY" 2>/dev/null)

                if echo "$route_config" | grep -q "regex_uri"; then
                    echo -e "  ${GREEN}✓ PASS${NC}: Path rewriting configured"
                    ((passed++))
                    ROOT_CAUSE="System configured correctly"

                    # Show the actual regex_uri configuration for verification
                    local regex_pattern=$(echo "$route_config" | grep -o '"regex_uri":\[[^]]*\]' | head -1)
                    if [ -n "$regex_pattern" ]; then
                        echo -e "  ${CYAN}Debug: $regex_pattern${NC}"
                    fi

                    # LEVEL 4: Test actual endpoint functionality
                    echo -e "\n${CYAN}  ── Level 4: Endpoint Functionality Test ──${NC}"
                    echo -e "${BOLD}Testing:${NC} Can we reach the models endpoint?"

                    # If no API key provided, try to discover one first
                    if [ -z "$APISIX_API_KEY" ] || [ "$APISIX_API_KEY" = " " ]; then
                        echo "  No API key provided, discovering..."
                        local temp_consumers=$(curl -s "$APISIX_ADMIN_URL/apisix/admin/consumers" \
                            -H "X-API-KEY: $APISIX_ADMIN_KEY" 2>/dev/null)

                        APISIX_API_KEY=$(echo "$temp_consumers" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for item in data.get('list', []):
        plugins = item.get('value', {}).get('plugins', {})
        if 'key-auth' in plugins:
            print(plugins['key-auth'].get('key', ''))
            break
except:
    pass
" 2>/dev/null)

                        if [ -n "$APISIX_API_KEY" ]; then
                            echo "  Discovered key: ${APISIX_API_KEY:0:10}..."
                        fi
                    fi

                    local test_url="$APISIX_URL/ai/openapi/$OPENAPI_ID/api/v1/models"
                    local test_response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 \
                        "$test_url" \
                        -H "apikey: $APISIX_API_KEY" 2>/dev/null)

                    case $test_response in
                        200)
                            echo -e "  ${GREEN}✓ PASS${NC}: Endpoint is working (HTTP 200)"
                            ((passed++))
                            ROOT_CAUSE="System fully operational"
                            ;;
                        401|403)
                            echo -e "  ${RED}✗ FAIL${NC}: Authentication failed (HTTP $test_response)"
                            ((failed++))
                            echo -e "  ${YELLOW}Debug: API key used: ${APISIX_API_KEY:0:10}...${NC}"

                            # Try to discover correct consumer key
                            echo -e "\n${YELLOW}    ∙ Level 5: Authentication Investigation${NC}"
                            echo -e "${BOLD}Test 5.1:${NC} Discovering available consumer keys"
                            echo "  Fetching consumers from: $APISIX_ADMIN_URL"

                            local consumers=$(curl -s "$APISIX_ADMIN_URL/apisix/admin/consumers" \
                                -H "X-API-KEY: $APISIX_ADMIN_KEY" 2>/dev/null)

                            # Debug: Check if consumers were fetched
                            if [ -z "$consumers" ]; then
                                echo -e "  ${RED}✗${NC} No consumers data received"
                                ROOT_CAUSE="Cannot fetch consumers - check APISIX Admin Key"
                            elif echo "$consumers" | grep -q "error"; then
                                echo -e "  ${RED}✗${NC} Error fetching consumers"
                                echo "  Response: $(echo "$consumers" | head -1)"
                                ROOT_CAUSE="Error accessing consumer configuration"
                            else
                                # Get consumer keys more reliably
                                local consumer_keys=$(echo "$consumers" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for item in data.get('list', []):
        plugins = item.get('value', {}).get('plugins', {})
        if 'key-auth' in plugins:
            print(plugins['key-auth'].get('key', ''))
except:
    pass
" 2>/dev/null)

                            if [ -n "$consumer_keys" ]; then
                                echo -e "  ${GREEN}✓${NC} Found consumer keys:"
                                echo "$consumer_keys" | while read -r key; do
                                    if [ -n "$key" ]; then
                                        echo "    - ${key:0:10}..."
                                    fi
                                done

                                # Test with first valid discovered key
                                local first_key=$(echo "$consumer_keys" | grep -v "^$" | head -1)
                                echo -e "\n${BOLD}Test 5.2:${NC} Testing with discovered key"
                                echo "  Using key: ${first_key:0:10}..."

                                local retry_response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 \
                                    "$test_url" \
                                    -H "apikey: $first_key" 2>/dev/null)

                                if [ "$retry_response" = "200" ]; then
                                    echo -e "  ${GREEN}✓${NC} Success with discovered key!"
                                    echo -e "  ${YELLOW}Automatically updating API key for this session${NC}"
                                    # Update the global variable with the working key
                                    APISIX_API_KEY="$first_key"
                                    ROOT_CAUSE="System fully operational (key updated)"
                                else
                                    echo -e "  ${RED}✗${NC} Still failing with discovered key (HTTP $retry_response)"

                                    # Check route's authentication configuration
                                    echo -e "\n${BOLD}Test 5.3:${NC} Checking route authentication plugins"

                                    if echo "$route_config" | grep -q '"key-auth"'; then
                                        echo -e "  ${GREEN}✓${NC} Route has key-auth plugin"

                                        # Check if consumer exists and has proper configuration
                                        echo -e "\n${BOLD}Test 5.4:${NC} Checking consumer configuration"
                                        local consumer_list=$(echo "$consumers" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for item in data.get('list', []):
        consumer = item.get('value', {})
        username = consumer.get('username', 'unknown')
        plugins = consumer.get('plugins', {})
        if 'key-auth' in plugins:
            key = plugins['key-auth'].get('key', '')
            print(f'{username}: {key[:10]}...')
except:
    pass
" 2>/dev/null)

                                        if [ -n "$consumer_list" ]; then
                                            echo -e "  Consumers with key-auth:"
                                            echo "$consumer_list" | sed 's/^/    /'
                                        fi

                                        # Test if it's actually the proxy-rewrite overriding auth
                                        echo -e "\n${BOLD}Test 5.5:${NC} Checking proxy-rewrite headers"
                                        local proxy_headers=$(echo "$route_config" | grep -o '"headers":{[^}]*}')
                                        if echo "$proxy_headers" | grep -q "Authorization"; then
                                            echo -e "  ${YELLOW}⚠${NC} Route is overriding Authorization header"
                                            echo -e "  This may conflict with API key authentication"
                                            ROOT_CAUSE="Route proxy-rewrite is overriding Authorization header"
                                        else
                                            ROOT_CAUSE="API key authentication issue - consumer lacks permissions or route misconfigured"
                                        fi
                                    else
                                        echo -e "  ${RED}✗${NC} Route does NOT have key-auth plugin!"
                                        echo -e "  Available plugins: $(echo "$route_plugins" | grep -o '"[^"]*":' | tr -d '":' | tr '\n' ' ')"
                                        ROOT_CAUSE="Route is missing key-auth plugin"
                                    fi
                                fi
                            else
                                echo -e "  ${RED}✗${NC} No consumer keys found"
                                ROOT_CAUSE="No consumers configured with key-auth"
                            fi
                            fi  # End of consumers check
                            ;;
                        404)
                            echo -e "  ${RED}✗ FAIL${NC}: Route not found (HTTP 404)"
                            ((failed++))
                            echo -e "  ${YELLOW}Debug: Testing URL: $test_url${NC}"
                            echo -e "  ${YELLOW}Debug: API Key: ${APISIX_API_KEY:0:10}...${NC}"

                            # LEVEL 5: Deep dive into 404 issue
                            echo -e "\n${YELLOW}    ∙ Level 5: Deep 404 Investigation${NC}"

                            # Test 1: Check if route is actually registered in APISIX
                            echo -e "${BOLD}Test 5.1:${NC} Is route registered and enabled?"
                            local route_status=$(echo "$route_config" | grep -o '"status":[0-9]*' | cut -d':' -f2)
                            if [ "$route_status" = "1" ] || [ -z "$route_status" ]; then
                                echo -e "  ${GREEN}✓${NC} Route is enabled (status: ${route_status:-1})"
                            else
                                echo -e "  ${RED}✗${NC} Route is DISABLED (status: $route_status)"
                                ROOT_CAUSE="Route is disabled in APISIX"
                            fi

                            # Only continue if route is enabled
                            if [ "$route_status" != "0" ]; then

                            # Test 2: Verify upstream configuration
                            echo -e "${BOLD}Test 5.2:${NC} Checking upstream configuration"
                            local upstream_host=$(echo "$route_config" | grep -o '"nodes":{"[^"]*"' | cut -d'"' -f4 | cut -d':' -f1)
                            local upstream_scheme=$(echo "$route_config" | grep -o '"scheme":"[^"]*"' | cut -d'"' -f4)
                            echo -e "  Upstream: ${upstream_scheme:-https}://$upstream_host"
                            echo -e "  Nodes in config: $(echo "$route_config" | grep -o '"nodes":{[^}]*}' | head -1)"

                            # Test 3: Check exact URI pattern matching
                            echo -e "${BOLD}Test 5.3:${NC} URI pattern analysis"
                            local route_uri=$(echo "$route_config" | grep -o '"uri":"[^"]*"' | cut -d'"' -f4)
                            echo -e "  Route URI pattern: $route_uri"
                            echo -e "  Request path: /ai/openapi/$OPENAPI_ID/api/v1/models"
                            echo -e "  Regex rewrite: $(echo "$regex_pattern")"

                            # Test if the URI matches
                            if [[ "/ai/openapi/$OPENAPI_ID/api/v1/models" == $route_uri* ]]; then
                                echo -e "  ${GREEN}✓${NC} URI pattern matches"
                            else
                                echo -e "  ${RED}✗${NC} URI pattern mismatch!"
                                echo -e "  ${YELLOW}Debug: Expected prefix: $route_uri${NC}"
                            fi

                            # Test 4: Check if Authorization header is configured in proxy-rewrite
                            echo -e "${BOLD}Test 5.4:${NC} Authorization header configuration"
                            local auth_header=$(echo "$route_config" | grep -o '"Authorization":"[^"]*"' | cut -d'"' -f4)
                            if [ -n "$auth_header" ]; then
                                echo -e "  ${GREEN}✓${NC} Authorization header is configured in proxy-rewrite"
                                echo -e "  Header value: ${auth_header:0:30}..."

                                # Extract the token for display
                                local bearer_token="${auth_header#Bearer }"

                                # Test from debuq container if available
                                if docker ps --format "{{.Names}}" | grep -q "violentutf-debuq"; then
                                    echo -e "  Testing upstream with configured token from debuq container..."
                                    local upstream_test_url="${upstream_scheme:-https}://$upstream_host/api/v1/models"

                                    local container_response=$(docker exec violentutf-debuq sh -c \
                                        "curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 \
                                        -H 'Authorization: $auth_header' \
                                        '$upstream_test_url'" 2>/dev/null)

                                    if [ "$container_response" = "200" ]; then
                                        echo -e "  ${GREEN}✓${NC} Upstream accepts the configured token (HTTP 200)"
                                    elif [ "$container_response" = "401" ]; then
                                        echo -e "  ${RED}✗${NC} Token is rejected by upstream (HTTP 401)"
                                        ROOT_CAUSE="The API token in proxy-rewrite is invalid or expired"
                                    elif [ "$container_response" = "000" ] || [ -z "$container_response" ]; then
                                        echo -e "  ${RED}✗${NC} Cannot reach upstream from container network"
                                        ROOT_CAUSE="Network connectivity issue from Docker network to upstream"
                                    else
                                        echo -e "  ${YELLOW}⚠${NC} Upstream returned HTTP $container_response"
                                    fi
                                else
                                    echo -e "  ${CYAN}ℹ${NC} Debuq container not running - cannot test upstream directly"
                                    echo -e "  ${CYAN}  Run: docker-compose -f docker-compose.debuq.standalone.yml up -d${NC}"
                                fi
                            else
                                echo -e "  ${RED}✗${NC} No Authorization header in proxy-rewrite!"
                                echo -e "  ${YELLOW}Run fix_staging_openapi_routes.sh with correct API key${NC}"
                                ROOT_CAUSE="Missing Authorization header in proxy-rewrite plugin"
                            fi

                                # Test 5: Check proxy-rewrite configuration details
                                echo -e "${BOLD}Test 5.5:${NC} Proxy-rewrite plugin details"
                                local proxy_rewrite=$(echo "$route_config" | grep -o '"proxy-rewrite":{[^}]*}')
                                echo -e "  Plugin config: $proxy_rewrite"

                                # Check if headers are being set
                                if echo "$proxy_rewrite" | grep -q '"headers"'; then
                                    echo -e "  ${GREEN}✓${NC} Headers are being modified"
                                    local auth_header=$(echo "$route_config" | grep -o '"Authorization":"[^"]*"' | cut -d'"' -f4)
                                    if [ -n "$auth_header" ]; then
                                        echo -e "  ${GREEN}✓${NC} Authorization header is set: ${auth_header:0:20}..."
                                    fi
                                fi

                                # Test 6: Check methods allowed
                                echo -e "${BOLD}Test 5.6:${NC} HTTP methods configuration"
                                local methods=$(echo "$route_config" | grep -o '"methods":\[[^]]*\]' | sed 's/"methods"://')
                                if [ -n "$methods" ] && [ "$methods" != "[]" ]; then
                                    echo -e "  Allowed methods: $methods"
                                    # Check if GET is included for models endpoint
                                    if [[ "$route_id" == *"models"* ]] && ! echo "$methods" | grep -q "GET"; then
                                        echo -e "  ${RED}✗${NC} GET method missing for models endpoint!"
                                        ROOT_CAUSE="Models endpoint requires GET method but it's not configured"
                                    else
                                        echo -e "  ${GREEN}✓${NC} Methods configured correctly"
                                    fi
                                else
                                    echo -e "  ${RED}✗${NC} No HTTP methods configured!"
                                    echo -e "  ${YELLOW}This route will not match any requests${NC}"
                                    ROOT_CAUSE="Route has no HTTP methods configured - will never match"
                                fi

                                # Test 7: Route configuration completeness
                                echo -e "${BOLD}Test 5.7:${NC} Route configuration completeness check"

                                # Check if route has all required components
                                local has_upstream=$(echo "$route_config" | grep -q '"upstream"' && echo "yes" || echo "no")
                                local has_methods=$(echo "$route_config" | grep -q '"methods":\[' && echo "yes" || echo "no")
                                local has_uri=$(echo "$route_config" | grep -q '"uri"' && echo "yes" || echo "no")
                                local has_plugins=$(echo "$route_config" | grep -q '"plugins"' && echo "yes" || echo "no")

                                echo -e "  Has upstream: $([ "$has_upstream" = "yes" ] && echo "${GREEN}✓${NC}" || echo "${RED}✗${NC}")"
                                echo -e "  Has methods: $([ "$has_methods" = "yes" ] && echo "${GREEN}✓${NC}" || echo "${RED}✗${NC}")"
                                echo -e "  Has URI: $([ "$has_uri" = "yes" ] && echo "${GREEN}✓${NC}" || echo "${RED}✗${NC}")"
                                echo -e "  Has plugins: $([ "$has_plugins" = "yes" ] && echo "${GREEN}✓${NC}" || echo "${RED}✗${NC}")"

                                if [ "$has_upstream" = "no" ] || [ "$has_methods" = "no" ] || [ "$has_uri" = "no" ]; then
                                    ROOT_CAUSE="Route configuration is incomplete - missing required components"
                                fi

                                # Test 8: Check for route ID suffix issue
                                echo -e "${BOLD}Test 5.8:${NC} Route ID suffix analysis"
                                echo -e "  Current route ID: $route_id"
                                if [[ "$route_id" == *"-" ]]; then
                                    echo -e "  ${YELLOW}⚠ Route ID ends with dash only (no suffix)${NC}"
                                    echo -e "  ${YELLOW}  This might indicate incomplete route creation${NC}"
                                    if [ -z "$ROOT_CAUSE" ]; then
                                        ROOT_CAUSE="Route ID format issue - missing suffix after dash"
                                    fi
                                else
                                    echo -e "  ${GREEN}✓${NC} Route ID has proper suffix"
                                fi
                            else
                                echo -e "  ${RED}✗${NC} Cannot reach upstream from container"
                                echo -e "  ${YELLOW}Debug: Response:${NC}"
                                echo "$container_response" | grep -E "failed|error|refused|timeout" | head -5
                                ROOT_CAUSE="Network connectivity issue from APISIX to upstream"
                            fi
                            ;;
                        502|503)
                            echo -e "  ${YELLOW}⚠ WARN${NC}: Gateway error (HTTP $test_response)"
                            ((warned++))
                            ROOT_CAUSE="Upstream service is down or unreachable"
                            ;;
                        *)
                            echo -e "  ${YELLOW}⚠ WARN${NC}: Unexpected response (HTTP $test_response)"
                            ((warned++))
                            ROOT_CAUSE="Unknown issue - check APISIX logs"
                            ;;
                    esac
                else
                    echo -e "  ${RED}✗ FAIL${NC}: Path rewriting not configured"
                    ((failed++))

                    # Check if route has upstream configured
                    if echo "$route_config" | grep -q '"nodes"'; then
                        echo -e "  ${YELLOW}Debug: Upstream is configured but regex_uri is missing${NC}"
                        ROOT_CAUSE="Routes missing regex_uri configuration for path rewriting"
                    else
                        echo -e "  ${YELLOW}Debug: Route has no upstream configuration${NC}"
                        ROOT_CAUSE="Route is incomplete - missing both upstream and rewrite"
                    fi
                fi
            else
                echo -e "  ${RED}✗ FAIL${NC}: Cannot find models route"
                ((failed++))
                echo -e "  ${YELLOW}Debug: Looking for pattern: ${models_route_id}*${NC}"
                echo -e "  ${YELLOW}Debug: Available route IDs:${NC}"
                echo "$route_list" | grep -o '"id":"[^"]*"' | head -5 | sed 's/^/    /'
                ROOT_CAUSE="Route IDs don't match expected pattern"
            fi
        fi
    fi

    # Summary
    echo -e "\n${BOLD}${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}DIAGNOSTIC COMPLETE${NC}"
    echo -e "${BOLD}${BLUE}════════════════════════════════════════════════════════${NC}"

    echo -e "\n${BOLD}Test Results:${NC}"
    echo -e "  ${GREEN}✓ Passed: $passed${NC}"
    echo -e "  ${YELLOW}⚠ Warnings: $warned${NC}"
    echo -e "  ${RED}✗ Failed: $failed${NC}"

    echo -e "\n${BOLD}Root Cause:${NC}"
    if [[ "$ROOT_CAUSE" == *"correctly"* ]]; then
        echo -e "  ${GREEN}$ROOT_CAUSE${NC}"
    else
        echo -e "  ${RED}$ROOT_CAUSE${NC}"
    fi

    # Provide recommended action based on root cause
    echo -e "\n${BOLD}Recommended Action:${NC}"
    case "$ROOT_CAUSE" in
        *"restart required"*)
            echo "  Run: docker-compose restart apisix"
            ;;
        *"setup required"*)
            echo "  Run: ./setup_macos.sh --openapi-setup"
            ;;
        *"regex_uri"*|*"path rewriting"*)
            echo "  Run: ./scripts/fix_staging_openapi_routes.sh"
            ;;
        *"URI or ID pattern issue"*)
            echo "  1. Check route IDs: curl -s $APISIX_ADMIN_URL/apisix/admin/routes -H 'X-API-KEY: $APISIX_ADMIN_KEY' | jq '.list[].value.id'"
            echo "  2. Verify route URIs match exactly with request paths"
            echo "  3. Re-run setup with: ./setup_macos.sh --cleanup && ./setup_macos.sh"
            ;;
        *"Network connectivity"*)
            echo "  1. Check container network: docker exec apisix-apisix ping -c 1 api.dev.gsai.mcaas.fcs.gsa.gov"
            echo "  2. Verify SSL certificates: docker exec apisix-apisix wget --spider -S https://api.dev.gsai.mcaas.fcs.gsa.gov"
            echo "  3. Check Docker DNS: docker exec apisix-apisix nslookup api.dev.gsai.mcaas.fcs.gsa.gov"
            ;;
        *"External routing issue"*)
            echo "  1. Test from inside container: docker exec -it apisix-apisix sh"
            echo "  2. Run: curl -H 'apikey: YOUR_KEY' http://127.0.0.1:9080/ai/openapi/gsai-api-1/api/v1/models"
            echo "  3. Check external URL configuration in environment"
            ;;
        *"Route is disabled"*)
            echo "  Enable the route:"
            echo "    curl -X PATCH $APISIX_ADMIN_URL/apisix/admin/routes/$route_id \\"
            echo "      -H 'X-API-KEY: $APISIX_ADMIN_KEY' \\"
            echo "      -d '{\"status\": 1}'"
            ;;
        *"API key"*)
            echo "  1. Check APISIX Admin Key in docker-compose.yml"
            echo "  2. Verify: grep admin_key docker-compose.yml"
            echo "  3. Get consumer keys: curl -s $APISIX_ADMIN_URL/apisix/admin/consumers -H 'X-API-KEY: ADMIN_KEY'"
            ;;
        *"port not properly exposed"*)
            echo "  Check docker-compose.yml port mappings for 9180"
            ;;
        *"ai-tokens.env"*)
            echo "  Configure OpenAPI provider in ai-tokens.env:"
            echo "    OPENAPI_1_ID=gsai-api-1"
            echo "    OPENAPI_1_ENABLED=true"
            echo "    OPENAPI_1_BASE_URL=<provider_url>"
            echo "    OPENAPI_1_API_KEY=<api_key>"
            ;;
        *"operational"*|*"correctly"*)
            echo -e "  ${GREEN}No action needed - system operational${NC}"
            ;;
        *)
            echo "  Review APISIX logs: docker logs apisix-apisix --tail 50"
            echo "  Check route details: curl -s $APISIX_ADMIN_URL/apisix/admin/routes/$route_id -H 'X-API-KEY: $APISIX_ADMIN_KEY' | jq"
            ;;
    esac
}

# Keep old function name for compatibility
troubleshoot_openapi_404() {
    print_subheader "🔍 Troubleshooting OpenAPI 404 Errors"

    # Load OpenAPI configuration if not already loaded
    if [ -z "$OPENAPI_ID" ] && [ -f "$REPO_ROOT/ai-tokens.env" ]; then
        OPENAPI_ID=$(grep "^OPENAPI_1_ID=" "$REPO_ROOT/ai-tokens.env" | cut -d'=' -f2 | cut -d'#' -f1 | tr -d ' ')
        OPENAPI_ENABLED=$(grep "^OPENAPI_1_ENABLED=" "$REPO_ROOT/ai-tokens.env" | cut -d'=' -f2 | cut -d'#' -f1 | tr -d ' ')
        OPENAPI_URL=$(grep "^OPENAPI_1_BASE_URL=" "$REPO_ROOT/ai-tokens.env" | cut -d'=' -f2 | cut -d'#' -f1 | tr -d ' ')
    fi

    echo "Analyzing why OpenAPI routes return 404..."
    echo "  Configuration loaded:"
    echo "    Provider ID: ${OPENAPI_ID:-not set}"
    echo "    Base URL: ${OPENAPI_URL:-not set}"
    echo

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
        # Determine protocol based on URL
        if [[ "$OPENAPI_URL" == https://* ]]; then
            container_url="https://$upstream_host/api/v1/models"
        else
            container_url="http://$upstream_host/api/v1/models"
        fi

        container_test=$(docker exec apisix-apisix sh -c "curl -s -I --max-time 3 '$container_url' 2>/dev/null | head -1" 2>/dev/null)
        if [ -n "$container_test" ] && echo "$container_test" | grep -q "HTTP"; then
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
        echo "8) Advanced OpenAPI Diagnostics (500 Error)"
        echo "9) Update Credentials"
        echo "10) Clear Cache"
        echo "11) Exit"

        echo -n -e "\n${BOLD}Enter choice [1-11]:${NC} "
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
                comprehensive_openapi_debug
                ;;
            8)
                test_openapi_advanced_diagnostics
                ;;
            9)
                APISIX_ADMIN_KEY=""
                APISIX_API_KEY=""
                AUTH_USERNAME=""
                AUTH_PASSWORD=""
                get_credentials
                ;;
            10)
                rm -f "$CACHE_FILE"
                print_success "Cache cleared"
                ;;
            11)
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
