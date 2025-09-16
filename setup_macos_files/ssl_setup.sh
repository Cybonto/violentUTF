#!/usr/bin/env bash
# ssl_setup.sh - SSL and certificate handling for Zscaler/corporate proxy

# Function to update docker-compose to use Dockerfile.zscaler
update_dockerfile_for_zscaler() {
    local compose_file="apisix/docker-compose.yml"

    echo "   Updating docker-compose to use Dockerfile.zscaler..."

    # Check if docker-compose file exists
    if [ ! -f "$compose_file" ]; then
        echo "   ⚠️  docker-compose.yml not found at $compose_file"
        return 1
    fi

    # Check if Dockerfile.zscaler exists
    if [ ! -f "violentutf_api/fastapi_app/Dockerfile.zscaler" ]; then
        echo "   ⚠️  Dockerfile.zscaler not found, using standard Dockerfile with certificates"
        return 1
    fi

    # Backup the original file
    cp "$compose_file" "${compose_file}.backup"

    # Update the dockerfile line in docker-compose
    # Change from "dockerfile: Dockerfile" to "dockerfile: Dockerfile.zscaler"
    if grep -q "dockerfile: Dockerfile.zscaler" "$compose_file"; then
        echo "   ✅ docker-compose.yml already configured for Zscaler"
    else
        sed -i.tmp 's|dockerfile: Dockerfile|dockerfile: Dockerfile.zscaler|g' "$compose_file"
        if [ $? -eq 0 ]; then
            echo "   ✅ Updated docker-compose.yml to use Dockerfile.zscaler"
            rm -f "${compose_file}.tmp"
        else
            echo "   ❌ Failed to update docker-compose.yml"
            mv "${compose_file}.backup" "$compose_file"
            return 1
        fi
    fi

    return 0
}

# Function to revert docker-compose to use standard Dockerfile
revert_to_standard_dockerfile() {
    local compose_file="apisix/docker-compose.yml"

    echo "   Reverting docker-compose to use standard Dockerfile..."

    if [ ! -f "$compose_file" ]; then
        return 1
    fi

    # Check if currently using Dockerfile.zscaler
    if grep -q "dockerfile: Dockerfile.zscaler" "$compose_file"; then
        sed -i.tmp 's|dockerfile: Dockerfile.zscaler|dockerfile: Dockerfile|g' "$compose_file"
        if [ $? -eq 0 ]; then
            echo "   ✅ Reverted docker-compose.yml to use standard Dockerfile"
            rm -f "${compose_file}.tmp"
        fi
    fi

    return 0
}

# Function to detect and handle SSL certificate issues
handle_ssl_certificate_issues() {
    log_detail "Checking for SSL certificate issues (Zscaler/Corporate proxy)..."

    local ssl_issue_detected=false

    # Method 1: Check for force flag (for staging environments)
    if [ "$FORCE_ZSCALER" = "true" ] || [ "$1" = "--force-zscaler" ]; then
        echo "⚠️  FORCE_ZSCALER enabled - using Zscaler configuration"
        ssl_issue_detected=true
    fi

    # Method 2: Test if we can reach common SSL sites
    if [ "$ssl_issue_detected" != true ] && ! curl -s --connect-timeout 5 https://sh.rustup.rs > /dev/null 2>&1; then
        echo "⚠️  Detected SSL certificate verification issues (curl test failed)"
        ssl_issue_detected=true
    fi

    # Method 3: Check if Zscaler certificates exist (even if curl works)
    if [ -f "violentutf_api/fastapi_app/zscaler.crt" ] || [ -f "violentutf_api/fastapi_app/CA.crt" ] || [ -f "violentutf_api/fastapi_app/zscaler.pem" ]; then
        echo "⚠️  Found Zscaler/CA certificates - assuming corporate proxy environment"
        ssl_issue_detected=true
    fi

    # Method 4: Check for ZSCALER environment variable
    if [ -n "$ZSCALER_ENABLED" ] || [ -n "$CORPORATE_PROXY" ]; then
        echo "⚠️  ZSCALER_ENABLED or CORPORATE_PROXY environment variable set"
        ssl_issue_detected=true
    fi

    if [ "$ssl_issue_detected" = true ]; then
        echo "📌 SSL/Proxy environment detected, configuring appropriate Dockerfile..."

        # First, try to generate certificates automatically if script exists
        if [ -f "./get-zscaler-certs.sh" ] && [ "$AUTO_GENERATE_CERTS" = "true" ]; then
            echo "   Attempting automatic certificate generation..."
            if ./get-zscaler-certs.sh 2>/dev/null; then
                echo "   ✅ Certificates generated automatically"
            else
                echo "   ⚠️  Automatic certificate generation failed (may not be available on this system)"
            fi
        fi

        # Check if certificates already exist or were just generated
        if [ -f "violentutf_api/fastapi_app/zscaler.crt" ] || [ -f "violentutf_api/fastapi_app/CA.crt" ] || [ -f "violentutf_api/fastapi_app/zscaler.pem" ]; then
            echo "✅ Found Zscaler/CA certificates in FastAPI directory"

            # Update docker-compose to use Dockerfile.zscaler
            update_dockerfile_for_zscaler

            echo "   The Dockerfile.zscaler will handle certificates for SSL verification"
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
                    # Update docker-compose to use Dockerfile.zscaler
                    update_dockerfile_for_zscaler
                    export SSL_WORKAROUND_APPLIED=true
                    return 0
                fi
            fi
        fi

        # If forced, use Dockerfile.zscaler anyway
        if [ "$FORCE_ZSCALER" = "true" ]; then
            echo "⚠️  FORCE_ZSCALER set - using Dockerfile.zscaler"
            echo "   WARNING: Build may fail without proper certificates!"
            echo "   Consider using fix-zscaler-build.sh to create a Dockerfile with curl -k"
            update_dockerfile_for_zscaler
            export SSL_WORKAROUND_APPLIED=true
            return 0
        fi

        echo "⚠️  Continuing without SSL certificate fix - builds may fail"
        export SSL_WORKAROUND_APPLIED=false
        return 1
    else
        log_success "SSL connectivity test passed - no corporate proxy detected"
        # Revert to standard Dockerfile if no Zscaler needed
        revert_to_standard_dockerfile
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
