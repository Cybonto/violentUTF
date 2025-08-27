#!/bin/bash
# Temporary fix for Rust/base2048 build issue with garak

echo "Checking for Rust build issues with garak..."

# Check if we're on ARM64 architecture (Apple Silicon)
if [[ $(uname -m) == "arm64" ]] || [[ $(uname -m) == "aarch64" ]]; then
    echo "Detected ARM64 architecture. Applying temporary garak workaround..."

    # Backup original requirements.txt
    cp violentutf_api/fastapi_app/requirements.txt violentutf_api/fastapi_app/requirements.txt.backup

    # Comment out garak temporarily
    sed -i '' 's/^garak/# garak  # Temporarily disabled due to ARM64 Rust build issue/' violentutf_api/fastapi_app/requirements.txt

    echo "✅ Temporarily disabled garak in requirements.txt"
    echo "   Original backed up to requirements.txt.backup"
    echo ""
    echo "You can now run ./setup_macos.sh"
    echo ""
    echo "To restore garak later, run:"
    echo "  mv violentutf_api/fastapi_app/requirements.txt.backup violentutf_api/fastapi_app/requirements.txt"
else
    echo "Non-ARM64 architecture detected. No changes needed."
fi
