#!/usr/bin/env bash
# test_refactored_setup.sh - Simple test to verify refactored setup loads properly

echo "Testing refactored setup script..."

# Test module loading
SCRIPT_DIR="/Users/tamnguyen/Documents/GitHub/ViolentUTF"
SETUP_MODULES_DIR="$SCRIPT_DIR/setup_macos_files"

# Check if all expected modules exist
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

echo "Checking module files..."
missing_modules=0

for module in "${modules[@]}"; do
    if [ -f "$SETUP_MODULES_DIR/$module" ]; then
        echo "✅ Found: $module"
    else
        echo "❌ Missing: $module"
        missing_modules=$((missing_modules + 1))
    fi
done

echo ""
if [ $missing_modules -eq 0 ]; then
    echo "✅ All modules found successfully!"
    echo "🚀 Refactored setup structure is complete"
else
    echo "❌ $missing_modules modules are missing"
    exit 1
fi

# Test syntax of main setup script
echo ""
echo "Testing syntax of new setup script..."
if bash -n "$SCRIPT_DIR/setup_macos_new.sh"; then
    echo "✅ setup_macos_new.sh syntax is valid"
else
    echo "❌ setup_macos_new.sh has syntax errors"
    exit 1
fi

echo ""
echo "🎉 Refactored setup test completed successfully!"
echo "📝 To use the refactored setup: ./setup_macos_new.sh"