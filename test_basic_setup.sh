#!/usr/bin/env bash
# test_basic_setup.sh - Test just the modular function loading and basic setup

echo "Testing basic modular setup..."

# Set up environment like the main script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_MODULES_DIR="$SCRIPT_DIR/setup_macos_files"
CLEANUP_MODE=false
DEEPCLEANUP_MODE=false
SHARED_NETWORK_NAME="vutf-network"
AI_TOKENS_FILE="ai-tokens.env"
SENSITIVE_VALUES=()
CREATED_AI_ROUTES=()

# Load modules
modules=(
    "utils.sh"
    "env_management.sh" 
    "docker_setup.sh"
    "ssl_setup.sh"
)

for module in "${modules[@]}"; do
    if [ -f "$SETUP_MODULES_DIR/$module" ]; then
        source "$SETUP_MODULES_DIR/$module"
        echo "✅ Loaded: $module"
    else
        echo "❌ Missing: $module"
        exit 1
    fi
done

echo ""
echo "Testing basic functions..."

# Test Docker verification
echo "Testing Docker setup..."
if verify_docker_setup; then
    echo "✅ Docker verification works"
else
    echo "❌ Docker verification failed"
fi

# Test network creation
echo "Testing network creation..."
if create_shared_network; then
    echo "✅ Network creation works"
else
    echo "❌ Network creation failed"
fi

# Test secret generation
echo "Testing secret generation..."
if generate_all_secrets; then
    echo "✅ Secret generation works"
    echo "Generated secrets count: ${#SENSITIVE_VALUES[@]}"
else
    echo "❌ Secret generation failed"
fi

echo ""
echo "🎉 Basic setup test completed!"
echo "Ready for full setup test"