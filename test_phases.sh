#!/usr/bin/env bash
# test_phases.sh - Test the first few phases of setup

echo "Testing modular setup phases..."

# Set up environment like the main script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_MODULES_DIR="$SCRIPT_DIR/setup_macos_files"
CLEANUP_MODE=false
DEEPCLEANUP_MODE=false
SHARED_NETWORK_NAME="vutf-network"
AI_TOKENS_FILE="ai-tokens.env"
SENSITIVE_VALUES=()
CREATED_AI_ROUTES=()

# Load all modules
modules=(
    "utils.sh"
    "env_management.sh" 
    "docker_setup.sh"
    "ssl_setup.sh"
    "keycloak_setup.sh"
    "apisix_setup.sh"
    "ai_providers_setup.sh"
    "openapi_setup.sh"
    "violentutf_api_setup.sh"
    "validation.sh"
    "cleanup.sh"
)

for module in "${modules[@]}"; do
    if [ -f "$SETUP_MODULES_DIR/$module" ]; then
        source "$SETUP_MODULES_DIR/$module"
        echo "Loaded module: $module"
    else
        echo "Warning: Module $module not found"
    fi
done

echo ""
echo "🚀 Testing ViolentUTF Setup Phases"

# Phase 1: Prerequisites and Environment Preparation  
echo ""
echo "=== Phase 1: Prerequisites and Environment Preparation ==="
verify_docker_setup
handle_ssl_certificate_issues
create_shared_network
backup_existing_configs

# Phase 2: AI Configuration Loading
echo ""
echo "=== Phase 2: AI Configuration Loading ==="
create_ai_tokens_template
load_ai_tokens

# Phase 3: Secret Generation
echo ""
echo "=== Phase 3: Secret Generation ==="
generate_all_secrets

# Phase 4: Configuration File Creation
echo ""
echo "=== Phase 4: Configuration File Creation ==="
generate_all_env_files

echo ""
echo "🎉 First 4 phases completed successfully!"
echo "Environment files created:"
ls -la keycloak/.env apisix/.env violentutf/.env violentutf_api/fastapi_app/.env 2>/dev/null || echo "Some files missing"