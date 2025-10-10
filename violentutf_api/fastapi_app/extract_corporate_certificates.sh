#!/bin/bash
# Corporate Certificate Extraction Script
# Based on docs/guides/zscaler-setup.md and existing documentation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="$SCRIPT_DIR"

echo "🔍 Extracting corporate certificates for Docker build..."

# Function to extract Zscaler certificates on macOS
extract_macos_certificates() {
    echo "📱 Detected macOS - extracting certificates from Keychain..."

    # Extract Zscaler certificates from System keychain
    if security find-certificate -a -p /Library/Keychains/System.keychain 2>/dev/null | grep -q "Zscaler"; then
        echo "✅ Found Zscaler certificates in System keychain"
        security find-certificate -a -p /Library/Keychains/System.keychain 2>/dev/null | \
            awk '/BEGIN CERTIFICATE/,/END CERTIFICATE/' | \
            grep -A 20 -B 5 "Zscaler" > "$CERT_DIR/zscaler.crt" 2>/dev/null || true

        if [ -s "$CERT_DIR/zscaler.crt" ]; then
            echo "✅ Extracted Zscaler certificates to zscaler.crt"
        fi
    fi

    # Extract all root certificates that might be corporate
    if security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain > "$CERT_DIR/zscaler.pem" 2>/dev/null; then
        if [ -s "$CERT_DIR/zscaler.pem" ]; then
            echo "✅ Extracted system root certificates to zscaler.pem"
        fi
    fi
}

# Function to check for existing certificates
check_existing_certificates() {
    echo "🔍 Checking for existing certificate files..."

    for cert_file in "zscaler.crt" "CA.crt" "zscaler.pem" "enterprise-ca.crt" "corporate.crt"; do
        if [ -f "$CERT_DIR/$cert_file" ]; then
            echo "✅ Found existing certificate: $cert_file"
        fi
    done
}

# Function to validate certificates
validate_certificates() {
    echo "🔐 Validating certificate files..."

    for cert_file in "$CERT_DIR"/*.crt "$CERT_DIR"/*.pem; do
        if [ -f "$cert_file" ] && [ -s "$cert_file" ]; then
            # Check if it's a valid certificate
            if openssl x509 -in "$cert_file" -noout -text >/dev/null 2>&1; then
                echo "✅ Valid certificate: $(basename "$cert_file")"
            elif grep -q "BEGIN CERTIFICATE" "$cert_file" 2>/dev/null; then
                echo "ℹ️  Certificate format detected: $(basename "$cert_file")"
            else
                echo "⚠️  Invalid certificate format: $(basename "$cert_file")"
            fi
        fi
    done
}

# Main execution
main() {
    echo "🏢 Corporate Certificate Extraction for Docker Build"
    echo "📁 Working directory: $CERT_DIR"
    echo ""

    # Check for existing certificates first
    check_existing_certificates

    # Extract certificates based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        extract_macos_certificates
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "🐧 Linux detected - checking for corporate certificates in standard locations..."
        # Check common corporate certificate locations
        for cert_path in "/etc/ssl/certs" "/usr/local/share/ca-certificates" "/etc/ca-certificates"; do
            if [ -d "$cert_path" ]; then
                find "$cert_path" -name "*zscaler*" -o -name "*corporate*" -o -name "*enterprise*" 2>/dev/null | while read -r cert; do
                    if [ -f "$cert" ]; then
                        cp "$cert" "$CERT_DIR/" 2>/dev/null || true
                        echo "✅ Copied: $(basename "$cert")"
                    fi
                done
            fi
        done
    else
        echo "ℹ️  Unsupported OS for automatic extraction: $OSTYPE"
        echo "ℹ️  Please manually copy your corporate certificates to this directory:"
        echo "   - $CERT_DIR/zscaler.crt"
        echo "   - $CERT_DIR/CA.crt"
        echo "   - $CERT_DIR/enterprise-ca.crt"
    fi

    echo ""
    validate_certificates

    echo ""
    echo "📋 Summary:"
    cert_count=$(find "$CERT_DIR" -name "*.crt" -o -name "*.pem" | wc -l)
    echo "   Found $cert_count certificate files"
    echo "   These will be automatically included in the Docker build"
    echo ""
    echo "🚀 Ready to run Docker build with corporate certificate support!"
    echo ""
    echo "💡 Tip: If Docker build still fails with SSL errors, the comprehensive"
    echo "   SSL bypass in the Dockerfile will handle the remaining issues."
}

# Check if running as script (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
