#!/usr/bin/env bash
# Comprehensive ViolentUTF Fix Script with Diagnostics
# Consolidates all fix scripts into one with proper diagnostics and branching

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script version
VERSION="3.0.0"

# Global variables
ISSUES_FOUND=0
FIXES_APPLIED=0
BACKUP_DIR=".violentutf_backups/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="fix_violentutf_$(date +%Y%m%d_%H%M%S).log"

# Function to print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Function to print section headers
print_section() {
    echo ""
    print_color "$BLUE" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_color "$BLUE" "$1"
    print_color "$BLUE" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Show help
show_help() {
    cat << EOF
ViolentUTF Comprehensive Fix Script v${VERSION}

Usage: $0 [OPTIONS]

OPTIONS:
    --diagnose-only     Only run diagnostics without applying fixes
    --fix-api-keys      Fix API key and consumer issues
    --fix-gsai          Fix GSAi routing and authentication
    --fix-permissions   Fix APISIX admin permissions
    --fix-network       Fix Docker network connectivity issues
    --fix-all           Apply all fixes (default)
    --backup            Create backup before applying fixes (default: true)
    --no-backup         Skip backup creation
    --rollback [dir]    Rollback to a previous backup
    --force             Apply fixes without confirmation
    --verbose           Show detailed output
    --log               Log all output to file
    --help, -h          Show this help message

EXAMPLES:
    $0                  # Run full diagnostics and apply all fixes
    $0 --diagnose-only  # Only show issues without fixing
    $0 --fix-gsai       # Only fix GSAi-related issues
    $0 --rollback       # List available backups and rollback
    $0 --force --no-log # Apply all fixes without prompting or logging

This script diagnoses and fixes common ViolentUTF issues:
- API key authentication and synchronization
- GSAi routing configuration (key-auth removal)
- SSL certificate and verification issues
- APISIX admin permissions
- Consumer registration and management
- Docker network connectivity
- Service health checks
EOF
}

# Parse command line arguments
DIAGNOSE_ONLY=false
FIX_API_KEYS=false
FIX_GSAI=false
FIX_PERMISSIONS=false
FIX_NETWORK=false
FIX_ALL=true
FORCE=false
CREATE_BACKUP=true
ROLLBACK=false
ROLLBACK_DIR=""
VERBOSE=false
LOG_OUTPUT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --diagnose-only)
            DIAGNOSE_ONLY=true
            FIX_ALL=false
            shift
            ;;
        --fix-api-keys)
            FIX_API_KEYS=true
            FIX_ALL=false
            shift
            ;;
        --fix-gsai)
            FIX_GSAI=true
            FIX_ALL=false
            shift
            ;;
        --fix-permissions)
            FIX_PERMISSIONS=true
            FIX_ALL=false
            shift
            ;;
        --fix-network)
            FIX_NETWORK=true
            FIX_ALL=false
            shift
            ;;
        --fix-all)
            FIX_ALL=true
            shift
            ;;
        --backup)
            CREATE_BACKUP=true
            shift
            ;;
        --no-backup)
            CREATE_BACKUP=false
            shift
            ;;
        --rollback)
            ROLLBACK=true
            DIAGNOSE_ONLY=true
            FIX_ALL=false
            if [[ $# -gt 1 ]] && [[ ! "$2" =~ ^-- ]]; then
                ROLLBACK_DIR="$2"
                shift
            fi
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --log)
            LOG_OUTPUT=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            print_color "$RED" "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# If specific fixes requested, disable fix-all
if [ "$FIX_API_KEYS" = true ] || [ "$FIX_GSAI" = true ] || [ "$FIX_PERMISSIONS" = true ] || [ "$FIX_NETWORK" = true ]; then
    FIX_ALL=false
fi

# Setup logging
if [ "$LOG_OUTPUT" = true ]; then
    exec > >(tee -a "$LOG_FILE")
    exec 2>&1
    print_color "$BLUE" "📝 Logging output to: $LOG_FILE"
fi

# Header
print_color "$GREEN" "╔═══════════════════════════════════════════════════╗"
print_color "$GREEN" "║   ViolentUTF Comprehensive Fix Script v${VERSION}    ║"
print_color "$GREEN" "╚═══════════════════════════════════════════════════╝"

# Backup functions
create_backup() {
    if [ "$CREATE_BACKUP" = false ] || [ "$DIAGNOSE_ONLY" = true ]; then
        return 0
    fi
    
    print_section "💾 Creating Backup"
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup APISIX routes
    echo -n "Backing up APISIX routes... "
    curl -s -H "X-API-KEY: $ADMIN_KEY" http://localhost:9180/apisix/admin/routes > "$BACKUP_DIR/apisix_routes.json" 2>/dev/null
    print_color "$GREEN" "✅"
    
    # Backup APISIX consumers
    echo -n "Backing up APISIX consumers... "
    curl -s -H "X-API-KEY: $ADMIN_KEY" http://localhost:9180/apisix/admin/consumers > "$BACKUP_DIR/apisix_consumers.json" 2>/dev/null
    print_color "$GREEN" "✅"
    
    # Backup environment files
    echo -n "Backing up environment files... "
    [ -f "apisix/.env" ] && cp "apisix/.env" "$BACKUP_DIR/"
    [ -f "violentutf/.env" ] && cp "violentutf/.env" "$BACKUP_DIR/"
    [ -f "violentutf_api/fastapi_app/.env" ] && cp "violentutf_api/fastapi_app/.env" "$BACKUP_DIR/fastapi.env"
    print_color "$GREEN" "✅"
    
    echo ""
    print_color "$GREEN" "✅ Backup created: $BACKUP_DIR"
}

list_backups() {
    print_section "📁 Available Backups"
    
    if [ ! -d ".violentutf_backups" ]; then
        print_color "$YELLOW" "No backups found"
        return 1
    fi
    
    local backups=($(ls -1d .violentutf_backups/*/ 2>/dev/null | sort -r))
    if [ ${#backups[@]} -eq 0 ]; then
        print_color "$YELLOW" "No backups found"
        return 1
    fi
    
    echo "Found ${#backups[@]} backup(s):"
    echo ""
    for i in "${!backups[@]}"; do
        local backup_name=$(basename "${backups[$i]}")
        echo "$((i+1)). $backup_name"
    done
    echo ""
    return 0
}

perform_rollback() {
    print_section "⏮️  Rollback"
    
    local backup_to_use=""
    
    if [ -n "$ROLLBACK_DIR" ]; then
        if [ -d ".violentutf_backups/$ROLLBACK_DIR" ]; then
            backup_to_use=".violentutf_backups/$ROLLBACK_DIR"
        else
            print_color "$RED" "❌ Backup not found: $ROLLBACK_DIR"
            return 1
        fi
    else
        if ! list_backups; then
            return 1
        fi
        
        read -p "Select backup number to rollback to: " -n 1 -r
        echo ""
        
        local backups=($(ls -1d .violentutf_backups/*/ 2>/dev/null | sort -r))
        local selected=$((REPLY - 1))
        
        if [ $selected -ge 0 ] && [ $selected -lt ${#backups[@]} ]; then
            backup_to_use="${backups[$selected]}"
        else
            print_color "$RED" "❌ Invalid selection"
            return 1
        fi
    fi
    
    print_color "$YELLOW" "⚠️  Rolling back to: $(basename "$backup_to_use")"
    
    if [ "$FORCE" = false ]; then
        read -p "Are you sure? (y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_color "$YELLOW" "Rollback cancelled"
            return 0
        fi
    fi
    
    # Restore routes
    if [ -f "$backup_to_use/apisix_routes.json" ]; then
        echo -n "Restoring APISIX routes... "
        local routes=$(jq -r '.list[].value' "$backup_to_use/apisix_routes.json" 2>/dev/null)
        if [ -n "$routes" ]; then
            echo "$routes" | while IFS= read -r route; do
                local route_id=$(echo "$route" | jq -r '.id')
                curl -s -X PUT "http://localhost:9180/apisix/admin/routes/$route_id" \
                    -H "X-API-KEY: $ADMIN_KEY" \
                    -H "Content-Type: application/json" \
                    -d "$route" > /dev/null 2>&1
            done
            print_color "$GREEN" "✅"
        else
            print_color "$YELLOW" "⚠️  No routes to restore"
        fi
    fi
    
    # Restore consumers
    if [ -f "$backup_to_use/apisix_consumers.json" ]; then
        echo -n "Restoring APISIX consumers... "
        local consumers=$(jq -r '.list[].value' "$backup_to_use/apisix_consumers.json" 2>/dev/null)
        if [ -n "$consumers" ]; then
            echo "$consumers" | while IFS= read -r consumer; do
                local username=$(echo "$consumer" | jq -r '.username')
                curl -s -X PUT "http://localhost:9180/apisix/admin/consumers/$username" \
                    -H "X-API-KEY: $ADMIN_KEY" \
                    -H "Content-Type: application/json" \
                    -d "$consumer" > /dev/null 2>&1
            done
            print_color "$GREEN" "✅"
        else
            print_color "$YELLOW" "⚠️  No consumers to restore"
        fi
    fi
    
    print_color "$GREEN" "✅ Rollback completed"
}

# Handle rollback if requested
if [ "$ROLLBACK" = true ]; then
    # Load admin key for rollback
    if [ -f "apisix/.env" ]; then
        ADMIN_KEY=$(grep "^APISIX_ADMIN_KEY=" apisix/.env | cut -d'=' -f2)
    fi
    
    if [ -z "$ADMIN_KEY" ]; then
        print_color "$RED" "❌ Cannot rollback: APISIX admin key not found"
        exit 1
    fi
    
    perform_rollback
    exit $?
fi

# Check prerequisites
print_section "🔍 Checking Prerequisites"

if ! command_exists jq; then
    print_color "$RED" "❌ jq is required but not installed"
    echo "   Install with: brew install jq (macOS) or apt-get install jq (Linux)"
    exit 1
fi

if ! command_exists curl; then
    print_color "$RED" "❌ curl is required but not installed"
    exit 1
fi

print_color "$GREEN" "✅ All prerequisites met"

# Load environment variables
print_section "🔐 Loading Environment Configuration"

# Check for required env files
if [ ! -f "apisix/.env" ]; then
    print_color "$RED" "❌ apisix/.env not found"
    echo "   Run setup script first"
    exit 1
fi

if [ ! -f "violentutf/.env" ]; then
    print_color "$RED" "❌ violentutf/.env not found"
    echo "   Run setup script first"
    exit 1
fi

if [ ! -f "ai-tokens.env" ]; then
    print_color "$RED" "❌ ai-tokens.env not found"
    echo "   Create from ai-tokens.env.sample"
    exit 1
fi

# Load environment variables
ADMIN_KEY=$(grep "^APISIX_ADMIN_KEY=" apisix/.env | cut -d'=' -f2)
VIOLENTUTF_API_KEY=$(grep "^VIOLENTUTF_API_KEY=" violentutf/.env | cut -d'=' -f2)
source ai-tokens.env

print_color "$GREEN" "✅ Environment configuration loaded"

# Create backup before fixes (if not diagnose-only mode)
if [ "$DIAGNOSE_ONLY" = false ] && [ "$CREATE_BACKUP" = true ]; then
    create_backup
fi

# Diagnostic functions
diagnose_api_keys() {
    local issues=0
    
    print_section "🔑 Diagnosing API Key Configuration"
    
    # Check ViolentUTF API key
    if [ -z "$VIOLENTUTF_API_KEY" ]; then
        print_color "$RED" "❌ VIOLENTUTF_API_KEY not found in violentutf/.env"
        ((issues++))
    else
        print_color "$GREEN" "✅ ViolentUTF API key found: ${VIOLENTUTF_API_KEY:0:12}...${VIOLENTUTF_API_KEY: -4}"
    fi
    
    # Check FastAPI API key
    FASTAPI_API_KEY=$(grep "^VIOLENTUTF_API_KEY=" violentutf_api/fastapi_app/.env 2>/dev/null | cut -d'=' -f2 || echo "")
    if [ -n "$FASTAPI_API_KEY" ] && [ "$FASTAPI_API_KEY" != "$VIOLENTUTF_API_KEY" ]; then
        print_color "$YELLOW" "⚠️  FastAPI has different API key: ${FASTAPI_API_KEY:0:12}...${FASTAPI_API_KEY: -4}"
        ((issues++))
    fi
    
    # Check consumers
    echo ""
    echo "📋 Checking APISIX Consumers:"
    CONSUMERS=$(curl -s -H "X-API-KEY: $ADMIN_KEY" http://localhost:9180/apisix/admin/consumers 2>/dev/null)
    
    if [ -z "$CONSUMERS" ] || ! echo "$CONSUMERS" | jq -e '.list' >/dev/null 2>&1; then
        print_color "$RED" "❌ Failed to fetch consumers from APISIX"
        ((issues++))
    else
        # Check for expected consumers
        for consumer in "violentutf-api" "violentutf-user" "violentutf_api_user"; do
            if echo "$CONSUMERS" | jq -e --arg name "$consumer" '.list[].value | select(.username == $name)' >/dev/null 2>&1; then
                print_color "$GREEN" "✅ Consumer '$consumer' exists"
            else
                print_color "$RED" "❌ Consumer '$consumer' missing"
                ((issues++))
            fi
        done
        
        # Check if API key is registered
        FOUND_KEY=$(echo "$CONSUMERS" | jq -r --arg key "$VIOLENTUTF_API_KEY" '.list[].value | select(.plugins."key-auth".key == $key) | .username' | head -1)
        if [ -n "$FOUND_KEY" ]; then
            print_color "$GREEN" "✅ API key registered to consumer: $FOUND_KEY"
        else
            print_color "$RED" "❌ API key not registered to any consumer"
            ((issues++))
        fi
    fi
    
    return $issues
}

diagnose_gsai_routes() {
    local issues=0
    
    print_section "🌐 Diagnosing GSAi Routes"
    
    # Check if GSAi is enabled
    if [ "${OPENAPI_1_ENABLED:-false}" != "true" ]; then
        print_color "$YELLOW" "⚠️  GSAi (OPENAPI_1) is not enabled in ai-tokens.env"
        return 0
    fi
    
    echo "GSAi Configuration:"
    echo "  ID: ${OPENAPI_1_ID:-not set}"
    echo "  Base URL: ${OPENAPI_1_BASE_URL:-not set}"
    echo "  Auth Token: ${OPENAPI_1_AUTH_TOKEN:0:20}..."
    echo "  SSL Verify: ${OPENAPI_1_SSL_VERIFY:-not set (defaults to true)}"
    
    # Check routes
    echo ""
    echo "🛣️  Checking GSAi Routes:"
    
    for route_id in 9001 9101; do
        ROUTE=$(curl -s -H "X-API-KEY: $ADMIN_KEY" http://localhost:9180/apisix/admin/routes/$route_id 2>/dev/null)
        
        if echo "$ROUTE" | jq -e '.value' >/dev/null 2>&1; then
            URI=$(echo "$ROUTE" | jq -r '.value.uri')
            PLUGINS=$(echo "$ROUTE" | jq -r '.value.plugins | keys | join(", ")')
            
            echo ""
            echo "Route $route_id ($URI):"
            echo "  Plugins: $PLUGINS"
            
            # Check for key-auth plugin (should NOT be present for GSAi)
            if echo "$ROUTE" | jq -e '.value.plugins."key-auth"' >/dev/null 2>&1; then
                print_color "$RED" "  ❌ Has key-auth plugin (causes auth header conflicts)"
                ((issues++))
            else
                print_color "$GREEN" "  ✅ No key-auth plugin (correct)"
            fi
            
            # Check SSL verification
            SSL_VERIFY=$(echo "$ROUTE" | jq -r '.value.plugins."ai-proxy".ssl_verify // .value.upstream.tls.verify // "not set"' 2>/dev/null)
            if [[ "$OPENAPI_1_BASE_URL" =~ ^https:// ]]; then
                local expected_verify="${OPENAPI_1_SSL_VERIFY:-true}"
                if [ "$SSL_VERIFY" != "$expected_verify" ] && [ "$SSL_VERIFY" != "not set" ]; then
                    print_color "$RED" "  ❌ SSL verification mismatch (route: $SSL_VERIFY, expected: $expected_verify)"
                    ((issues++))
                elif [ "$SSL_VERIFY" = "not set" ] && [ "$expected_verify" = "false" ]; then
                    print_color "$YELLOW" "  ⚠️  SSL verification not explicitly set (should be: false for self-signed certs)"
                    ((issues++))
                fi
            fi
            
            # Check endpoint configuration
            if echo "$ROUTE" | jq -e '.value.plugins."ai-proxy"' >/dev/null 2>&1; then
                ENDPOINT=$(echo "$ROUTE" | jq -r '.value.plugins."ai-proxy".override.endpoint // "not set"')
                if [[ "$ENDPOINT" == *"host.docker.internal"* ]] && [[ "$OPENAPI_1_BASE_URL" != *"localhost"* ]]; then
                    print_color "$YELLOW" "  ⚠️  Endpoint uses host.docker.internal: $ENDPOINT"
                fi
            fi
        else
            print_color "$RED" "❌ Route $route_id not found"
            ((issues++))
        fi
    done
    
    # Test GSAi connectivity
    echo ""
    echo "🧪 Testing GSAi Connectivity:"
    
    # Test without API key (correct for GSAi routes without key-auth)
    echo -n "  APISIX → GSAi: "
    HTTP_CODE=$(curl -s -w "%{http_code}" -o /dev/null \
        -H "Content-Type: application/json" \
        -X POST \
        http://localhost:9080/ai/gsai-api-1/chat/completions \
        -d '{"model": "llama3211b", "messages": [{"role": "user", "content": "test"}], "max_tokens": 1}' 2>&1)
    
    case $HTTP_CODE in
        200) print_color "$GREEN" "✅ Success" ;;
        401) print_color "$RED" "❌ Unauthorized (missing/invalid API key)" ; ((issues++)) ;;
        403) 
            print_color "$RED" "❌ Forbidden"
            # Get detailed error
            local ERROR_RESPONSE=$(curl -s -H "Content-Type: application/json" -X POST \
                http://localhost:9080/ai/gsai-api-1/chat/completions \
                -d '{"model": "llama3211b", "messages": [{"role": "user", "content": "test"}], "max_tokens": 1}' 2>&1)
            if echo "$ERROR_RESPONSE" | grep -q "Invalid key=value pair"; then
                echo "      ⚠️  GSAi expecting different auth format - check route plugins"
            elif echo "$ERROR_RESPONSE" | grep -q "Invalid API key"; then
                echo "      ⚠️  API key rejected by consumer auth"
            else
                echo "      ⚠️  GSAi rejected request (check model access)"
            fi
            ((issues++))
            ;;
        500) 
            print_color "$RED" "❌ Server Error"
            # Check APISIX logs for SSL errors
            local APISIX_LOG=$(docker logs apisix-apisix-1 --tail 10 2>&1 | grep -i "ssl\|certificate" | tail -1)
            if [ -n "$APISIX_LOG" ]; then
                echo "      ⚠️  SSL/Certificate issue detected"
                [ "$VERBOSE" = true ] && echo "      Log: $APISIX_LOG"
            fi
            ((issues++))
            ;;
        502) print_color "$RED" "❌ Bad Gateway (upstream unreachable)" ; ((issues++)) ;;
        504) print_color "$RED" "❌ Gateway Timeout (upstream timeout)" ; ((issues++)) ;;
        *) print_color "$RED" "❌ Failed (HTTP $HTTP_CODE)" ; ((issues++)) ;;
    esac
    
    # Test direct to GSAi
    if [ -n "$OPENAPI_1_BASE_URL" ] && [ -n "$OPENAPI_1_AUTH_TOKEN" ]; then
        echo -n "  Direct → GSAi: "
        CURL_OPTS="-s -w %{http_code} -o /dev/null"
        [ "${OPENAPI_1_SSL_VERIFY:-true}" = "false" ] && CURL_OPTS="$CURL_OPTS -k"
        
        HTTP_CODE=$(curl $CURL_OPTS \
            -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
            -H "Content-Type: application/json" \
            -X POST \
            "$OPENAPI_1_BASE_URL/api/v1/chat/completions" \
            -d '{"model": "llama3211b", "messages": [{"role": "user", "content": "test"}], "max_tokens": 1}' 2>&1)
        
        case $HTTP_CODE in
            200) print_color "$GREEN" "✅ Success" ;;
            403) print_color "$YELLOW" "⚠️  Token/Model access issue" ;;
            *) print_color "$RED" "❌ Failed (HTTP $HTTP_CODE)" ;;
        esac
    fi
    
    return $issues
}

diagnose_permissions() {
    local issues=0
    
    print_section "🔐 Diagnosing APISIX Admin Permissions"
    
    APISIX_ADMIN_FILE="violentutf_api/fastapi_app/app/api/endpoints/apisix_admin.py"
    
    if [ -f "$APISIX_ADMIN_FILE" ]; then
        if grep -q '"violentutf.web"' "$APISIX_ADMIN_FILE"; then
            print_color "$GREEN" "✅ User 'violentutf.web' is in allowed users list"
        else
            print_color "$RED" "❌ User 'violentutf.web' is NOT in allowed users list"
            echo "   This causes '403 Forbidden' errors in Simple Chat"
            ((issues++))
        fi
    else
        print_color "$YELLOW" "⚠️  Cannot check permissions - file not found: $APISIX_ADMIN_FILE"
    fi
    
    return $issues
}

diagnose_network() {
    local issues=0
    
    print_section "🌐 Diagnosing Network Connectivity"
    
    # Check Docker network
    echo "🐳 Docker Network Status:"
    if docker network inspect vutf-network >/dev/null 2>&1; then
        print_color "$GREEN" "✅ Docker network 'vutf-network' exists"
        
        # List connected containers
        local containers=$(docker network inspect vutf-network -f '{{range .Containers}}{{.Name}} {{end}}' 2>/dev/null)
        if [ -n "$containers" ]; then
            echo "   Connected containers: $containers"
        else
            print_color "$YELLOW" "   ⚠️  No containers connected to network"
            ((issues++))
        fi
    else
        print_color "$RED" "❌ Docker network 'vutf-network' not found"
        ((issues++))
    fi
    
    # Check service connectivity
    echo ""
    echo "🔌 Service Connectivity:"
    
    # APISIX health check
    echo -n "  APISIX (9080): "
    if curl -s --max-time 2 http://localhost:9080/health >/dev/null 2>&1; then
        print_color "$GREEN" "✅ Reachable"
    else
        print_color "$RED" "❌ Not reachable"
        ((issues++))
    fi
    
    # APISIX Admin API
    echo -n "  APISIX Admin (9180): "
    if curl -s --max-time 2 -H "X-API-KEY: $ADMIN_KEY" http://localhost:9180/apisix/admin/routes >/dev/null 2>&1; then
        print_color "$GREEN" "✅ Reachable"
    else
        print_color "$RED" "❌ Not reachable"
        ((issues++))
    fi
    
    # Keycloak
    echo -n "  Keycloak (8080): "
    if curl -s --max-time 2 http://localhost:8080/health >/dev/null 2>&1; then
        print_color "$GREEN" "✅ Reachable"
    else
        print_color "$RED" "❌ Not reachable"
        ((issues++))
    fi
    
    # FastAPI
    echo -n "  FastAPI (8000): "
    if curl -s --max-time 2 http://localhost:8000/health >/dev/null 2>&1; then
        print_color "$GREEN" "✅ Reachable"
    else
        print_color "$RED" "❌ Not reachable"
        ((issues++))
    fi
    
    # Streamlit
    echo -n "  Streamlit (8501): "
    if curl -s --max-time 2 http://localhost:8501/health >/dev/null 2>&1; then
        print_color "$GREEN" "✅ Reachable"
    else
        print_color "$YELLOW" "⚠️  Not reachable (may be normal if not running)"
    fi
    
    # Check container-to-container connectivity
    echo ""
    echo "🔗 Container-to-Container Connectivity:"
    
    # Test APISIX -> Keycloak
    echo -n "  APISIX → Keycloak: "
    if docker exec apisix-apisix-1 curl -s --max-time 2 http://keycloak:8080/health >/dev/null 2>&1; then
        print_color "$GREEN" "✅ Connected"
    else
        print_color "$RED" "❌ Connection failed"
        ((issues++))
    fi
    
    # Test APISIX -> FastAPI
    echo -n "  APISIX → FastAPI: "
    if docker exec apisix-apisix-1 curl -s --max-time 2 http://violentutf_api:8000/health >/dev/null 2>&1; then
        print_color "$GREEN" "✅ Connected"
    else
        print_color "$RED" "❌ Connection failed"
        ((issues++))
    fi
    
    return $issues
}

# Fix functions
fix_api_keys() {
    print_section "🔧 Fixing API Key Issues"
    
    if [ "$DIAGNOSE_ONLY" = true ]; then
        return 0
    fi
    
    # Use FastAPI key if different and exists
    FASTAPI_API_KEY=$(grep "^VIOLENTUTF_API_KEY=" violentutf_api/fastapi_app/.env 2>/dev/null | cut -d'=' -f2 || echo "")
    if [ -n "$FASTAPI_API_KEY" ] && [ "$FASTAPI_API_KEY" != "$VIOLENTUTF_API_KEY" ]; then
        echo "Using FastAPI API key for consumer creation"
        API_KEY="$FASTAPI_API_KEY"
    else
        API_KEY="$VIOLENTUTF_API_KEY"
    fi
    
    # Create/update consumers
    echo "Creating/updating APISIX consumers..."
    for consumer in "violentutf-api" "violentutf-user" "violentutf_api_user"; do
        echo -n "  $consumer: "
        RESPONSE=$(curl -s -w "%{http_code}" -X PUT "http://localhost:9180/apisix/admin/consumers/$consumer" \
            -H "X-API-KEY: $ADMIN_KEY" \
            -H "Content-Type: application/json" \
            -d "{
                \"username\": \"$consumer\",
                \"plugins\": {
                    \"key-auth\": {
                        \"key\": \"$API_KEY\"
                    }
                }
            }" -o /dev/null)
        
        if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "201" ]; then
            print_color "$GREEN" "✅ Updated"
            ((FIXES_APPLIED++))
        else
            print_color "$RED" "❌ Failed (HTTP $RESPONSE)"
        fi
    done
}

fix_gsai_routes() {
    print_section "🔧 Fixing GSAi Routes"
    
    if [ "$DIAGNOSE_ONLY" = true ]; then
        return 0
    fi
    
    if [ "${OPENAPI_1_ENABLED:-false}" != "true" ]; then
        print_color "$YELLOW" "⚠️  GSAi not enabled - skipping"
        return 0
    fi
    
    # Determine scheme and host
    SCHEME="http"
    if [[ "$OPENAPI_1_BASE_URL" =~ ^https:// ]]; then
        SCHEME="https"
    fi
    
    HOST_PORT=$(echo "$OPENAPI_1_BASE_URL" | sed -E 's|https?://||' | sed 's|/.*||')
    
    echo "Configuration:"
    echo "  Upstream: $SCHEME://$HOST_PORT"
    echo "  SSL Verify: ${OPENAPI_1_SSL_VERIFY:-true}"
    
    # Update chat route (9001) - NO key-auth for GSAi
    echo ""
    echo "Updating GSAi chat route (9001)..."
    UPDATE_RESPONSE=$(curl -s -X PUT "http://localhost:9180/apisix/admin/routes/9001" \
      -H "X-API-KEY: $ADMIN_KEY" \
      -H "Content-Type: application/json" \
      -d "{
        \"uri\": \"/ai/gsai-api-1/chat/completions\",
        \"name\": \"gsai-api-1-chat-completions\",
        \"methods\": [\"POST\"],
        \"upstream\": {
          \"type\": \"roundrobin\",
          \"scheme\": \"$SCHEME\",
          \"nodes\": {
            \"$HOST_PORT\": 1
          }
        },
        \"plugins\": {
          \"ai-proxy\": {
            \"provider\": \"openai-compatible\",
            \"auth\": {
              \"header\": {
                \"Authorization\": \"Bearer $OPENAPI_1_AUTH_TOKEN\"
              }
            },
            \"model\": {
              \"passthrough\": true
            },
            \"override\": {
              \"endpoint\": \"$OPENAPI_1_BASE_URL/api/v1/chat/completions\"
            },
            \"timeout\": 30000,
            \"keepalive\": true,
            \"keepalive_timeout\": 60000,
            \"keepalive_pool\": 30,
            \"ssl_verify\": ${OPENAPI_1_SSL_VERIFY:-true}
          },
          \"cors\": {
            \"allow_origins\": \"http://localhost:8501,http://localhost:3000\",
            \"allow_methods\": \"GET,POST,OPTIONS\",
            \"allow_headers\": \"Authorization,Content-Type,X-Requested-With,apikey,X-API-KEY\",
            \"allow_credential\": true,
            \"max_age\": 3600
          }
        }
      }")
    
    if echo "$UPDATE_RESPONSE" | grep -q '"id":"9001"'; then
        print_color "$GREEN" "✅ Route 9001 updated"
        ((FIXES_APPLIED++))
    else
        print_color "$RED" "❌ Failed to update route 9001"
        echo "Response: $UPDATE_RESPONSE"
    fi
    
    # Update models route (9101) - NO key-auth for GSAi
    echo ""
    echo "Updating GSAi models route (9101)..."
    UPDATE_RESPONSE=$(curl -s -X PUT "http://localhost:9180/apisix/admin/routes/9101" \
      -H "X-API-KEY: $ADMIN_KEY" \
      -H "Content-Type: application/json" \
      -d "{
        \"uri\": \"/ai/gsai-api-1/models\",
        \"name\": \"gsai-api-1-models\",
        \"methods\": [\"GET\"],
        \"upstream\": {
          \"type\": \"roundrobin\",
          \"scheme\": \"$SCHEME\",
          \"nodes\": {
            \"$HOST_PORT\": 1
          }
        },
        \"plugins\": {
          \"proxy-rewrite\": {
            \"uri\": \"/api/v1/models\",
            \"headers\": {
              \"set\": {
                \"Authorization\": \"Bearer $OPENAPI_1_AUTH_TOKEN\"
              }
            }
          },
          \"cors\": {
            \"allow_origins\": \"http://localhost:8501,http://localhost:3000\",
            \"allow_methods\": \"GET,POST,OPTIONS\",
            \"allow_headers\": \"Authorization,Content-Type,X-Requested-With,apikey,X-API-KEY\",
            \"allow_credential\": true,
            \"max_age\": 3600
          }
        }
      }")
    
    if echo "$UPDATE_RESPONSE" | grep -q '"id":"9101"'; then
        print_color "$GREEN" "✅ Route 9101 updated"
        ((FIXES_APPLIED++))
    else
        print_color "$RED" "❌ Failed to update route 9101"
    fi
}

fix_permissions() {
    print_section "🔧 Fixing APISIX Admin Permissions"
    
    if [ "$DIAGNOSE_ONLY" = true ]; then
        return 0
    fi
    
    APISIX_ADMIN_FILE="violentutf_api/fastapi_app/app/api/endpoints/apisix_admin.py"
    
    if [ -f "$APISIX_ADMIN_FILE" ]; then
        if ! grep -q '"violentutf.web"' "$APISIX_ADMIN_FILE"; then
            print_color "$YELLOW" "⚠️  Manual fix required:"
            echo "   Edit: $APISIX_ADMIN_FILE"
            echo "   Find: allowed_users = [\"admin\", \"keycloak_user\"]"
            echo "   Replace: allowed_users = [\"admin\", \"violentutf.web\", \"keycloak_user\"]"
            echo "   Then: docker restart violentutf_api"
        else
            print_color "$GREEN" "✅ Permissions already correct"
        fi
    fi
}

fix_network() {
    print_section "🔧 Fixing Network Issues"
    
    if [ "$DIAGNOSE_ONLY" = true ]; then
        return 0
    fi
    
    # Check if Docker network exists
    if ! docker network inspect vutf-network >/dev/null 2>&1; then
        echo "Creating Docker network..."
        if docker network create vutf-network; then
            print_color "$GREEN" "✅ Created vutf-network"
            ((FIXES_APPLIED++))
        else
            print_color "$RED" "❌ Failed to create network"
        fi
    fi
    
    # Restart disconnected containers
    echo ""
    echo "Checking container connectivity..."
    
    local services=("apisix-apisix-1" "keycloak" "keycloak-postgres" "violentutf_api")
    for service in "${services[@]}"; do
        if docker ps --format "{{.Names}}" | grep -q "^$service$"; then
            # Check if connected to network
            if ! docker network inspect vutf-network -f '{{range .Containers}}{{.Name}}{{end}}' | grep -q "$service"; then
                echo -n "  Reconnecting $service to network... "
                if docker network connect vutf-network "$service" 2>/dev/null; then
                    print_color "$GREEN" "✅"
                    ((FIXES_APPLIED++))
                else
                    print_color "$YELLOW" "⚠️  Already connected or failed"
                fi
            fi
        fi
    done
    
    # Restart services if needed
    echo ""
    echo "Checking service health..."
    
    # Restart APISIX if not healthy
    if ! curl -s --max-time 2 http://localhost:9080/health >/dev/null 2>&1; then
        echo -n "  Restarting APISIX... "
        if docker restart apisix-apisix-1 >/dev/null 2>&1; then
            sleep 5
            print_color "$GREEN" "✅"
            ((FIXES_APPLIED++))
        else
            print_color "$RED" "❌ Failed"
        fi
    fi
    
    # Restart FastAPI if not healthy
    if ! curl -s --max-time 2 http://localhost:8000/health >/dev/null 2>&1; then
        echo -n "  Restarting FastAPI... "
        if docker restart violentutf_api >/dev/null 2>&1; then
            sleep 3
            print_color "$GREEN" "✅"
            ((FIXES_APPLIED++))
        else
            print_color "$RED" "❌ Failed"
        fi
    fi
}

# Main diagnostic flow
main() {
    local total_issues=0
    
    # Run diagnostics
    if diagnose_api_keys; then
        :
    else
        total_issues=$((total_issues + $?))
    fi
    
    if diagnose_gsai_routes; then
        :
    else
        total_issues=$((total_issues + $?))
    fi
    
    if diagnose_permissions; then
        :
    else
        total_issues=$((total_issues + $?))
    fi
    
    if diagnose_network; then
        :
    else
        total_issues=$((total_issues + $?))
    fi
    
    ISSUES_FOUND=$total_issues
    
    # Summary
    print_section "📊 Diagnostic Summary"
    
    if [ $ISSUES_FOUND -eq 0 ]; then
        print_color "$GREEN" "✅ No issues found!"
    else
        print_color "$YELLOW" "⚠️  Found $ISSUES_FOUND issue(s)"
        
        if [ "$DIAGNOSE_ONLY" = false ]; then
            echo ""
            if [ "$FORCE" = false ]; then
                read -p "Apply fixes? (y/N) " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    print_color "$YELLOW" "Fixes cancelled"
                    exit 0
                fi
            fi
            
            # Apply fixes based on options
            if [ "$FIX_ALL" = true ] || [ "$FIX_API_KEYS" = true ]; then
                fix_api_keys
            fi
            
            if [ "$FIX_ALL" = true ] || [ "$FIX_GSAI" = true ]; then
                fix_gsai_routes
            fi
            
            if [ "$FIX_ALL" = true ] || [ "$FIX_PERMISSIONS" = true ]; then
                fix_permissions
            fi
            
            if [ "$FIX_ALL" = true ] || [ "$FIX_NETWORK" = true ]; then
                fix_network
            fi
            
            # Final summary
            print_section "✨ Fix Summary"
            print_color "$GREEN" "Applied $FIXES_APPLIED fix(es)"
            
            if [ $FIXES_APPLIED -gt 0 ]; then
                echo ""
                print_color "$BLUE" "Next steps:"
                echo "1. Test GSAi access: curl http://localhost:9080/ai/gsai-api-1/chat/completions"
                echo "2. Restart Streamlit if running: docker restart violentutf-streamlit-1"
                echo "3. Check logs if issues persist: docker logs apisix-apisix-1 --tail 20"
                echo "4. Run with --verbose for detailed diagnostics"
            fi
            
            echo ""
            print_color "$BLUE" "💡 Troubleshooting Tips:"
            echo "• For 403 errors: Check if GSAi route has key-auth plugin (should NOT have it)"
            echo "• For SSL errors: Set OPENAPI_1_SSL_VERIFY=false in ai-tokens.env"
            echo "• For API key issues: Ensure all consumers use the same key"
            echo "• Run './fix_violentutf_issues.sh --rollback' to undo changes if needed"
        fi
    fi
}

# Run main function
main