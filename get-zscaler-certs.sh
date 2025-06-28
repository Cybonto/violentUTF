#!/bin/bash
# Script to export Zscaler certificates on macOS

echo "Exporting Zscaler certificates..."

# Find and export Zscaler certificate from System keychain
security find-certificate -c "Zscaler" -p /Library/Keychains/System.keychain > zscaler.crt 2>/dev/null

# Also check for any CA certificates
security find-certificate -c "Zscaler Root CA" -p /Library/Keychains/System.keychain > CA.crt 2>/dev/null

# If no Zscaler cert found, try to find any corporate CA
if [ ! -s zscaler.crt ]; then
    echo "No Zscaler certificate found, looking for corporate CAs..."
    security find-certificate -a -p /Library/Keychains/System.keychain | grep -A 50 -B 5 "CA" > CA.crt
fi

# Copy to FastAPI directory
if [ -s zscaler.crt ] || [ -s CA.crt ]; then
    echo "Copying certificates to FastAPI directory..."
    [ -s zscaler.crt ] && cp zscaler.crt violentutf_api/fastapi_app/
    [ -s CA.crt ] && cp CA.crt violentutf_api/fastapi_app/
    echo "✅ Certificates copied successfully"
    echo ""
    echo "Found certificates:"
    [ -s zscaler.crt ] && echo "  - zscaler.crt"
    [ -s CA.crt ] && echo "  - CA.crt"
else
    echo "❌ No certificates found. You may need to export them manually."
    echo ""
    echo "To manually export certificates:"
    echo "1. Open Keychain Access"
    echo "2. Find your Zscaler or corporate CA certificate"
    echo "3. Right-click and export as .crt format"
    echo "4. Copy to violentutf_api/fastapi_app/"
fi