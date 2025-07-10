#!/usr/bin/env bash
# ssl_setup.sh - SSL and certificate handling for Zscaler/corporate proxy

# Function to detect and handle SSL certificate issues
handle_ssl_certificate_issues() {
    log_detail "Checking for SSL certificate issues (Zscaler/Corporate proxy)..."
    
    # Test if we can reach common SSL sites
    if ! curl -s --connect-timeout 5 https://sh.rustup.rs > /dev/null 2>&1; then
        echo "⚠️  Detected SSL certificate verification issues (likely Zscaler or corporate proxy)"
        
        # Check if certificates already exist
        if [ -f "violentutf_api/fastapi_app/zscaler.crt" ] || [ -f "violentutf_api/fastapi_app/CA.crt" ]; then
            echo "✅ Found Zscaler/CA certificates in FastAPI directory"
            echo "   The Dockerfile will use these certificates for SSL verification"
            export SSL_WORKAROUND_APPLIED=true
            return 0
        fi
        
        echo ""
        echo "📌 You need to add your Zscaler/CA certificates for the build to work."
        echo ""
        echo "Option 1 (Automatic - macOS only):"
        echo "   ./get-zscaler-certs.sh"
        echo ""
        echo "Option 2 (Manual):"
        echo "   1. Export your Zscaler certificate (usually from Keychain or Certificate Manager)"
        echo "   2. Copy the certificates to the FastAPI directory:"
        echo "      cp zscaler.crt violentutf_api/fastapi_app/"
        echo "      cp CA.crt violentutf_api/fastapi_app/"
        echo ""
        
        # Ask user if they want to try automatic export
        if [ -f "./get-zscaler-certs.sh" ]; then
            read -p "Would you like to try automatic certificate export? (y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                if ./get-zscaler-certs.sh; then
                    export SSL_WORKAROUND_APPLIED=true
                    return 0
                fi
            fi
        fi
        
        echo "⚠️  Continuing without SSL certificate fix - builds may fail"
        export SSL_WORKAROUND_APPLIED=false
        return 1
    else
        log_success "SSL connectivity test passed - no corporate proxy detected"
        export SSL_WORKAROUND_APPLIED=false
        return 0
    fi
}

# Function to install Zscaler certificates
install_zscaler_certs() {
    echo "Installing Zscaler/CA certificates..."
    
    # This would contain the logic from the original script
    # For now, just a placeholder implementation
    
    local cert_files=("violentutf_api/fastapi_app/zscaler.crt" "violentutf_api/fastapi_app/CA.crt")
    local certs_found=false
    
    for cert_file in "${cert_files[@]}"; do
        if [ -f "$cert_file" ]; then
            echo "✅ Found certificate: $cert_file"
            certs_found=true
        fi
    done
    
    if [ "$certs_found" = true ]; then
        echo "✅ Zscaler/CA certificates are available"
        return 0
    else
        echo "❌ No Zscaler/CA certificates found"
        return 1
    fi
}

# Function to configure SSL bypass
configure_ssl_bypass() {
    echo "Configuring SSL bypass for corporate environments..."
    
    # Set environment variable for other scripts to use
    export SSL_WORKAROUND_APPLIED=true
    
    echo "✅ SSL bypass configuration applied"
    echo "   All curl commands will use -k flag for SSL bypass"
    
    return 0
}