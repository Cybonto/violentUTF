#!/usr/bin/env bash
# certificate_management.sh - SSL Certificate detection and management for APISIX

# Common enterprise CA certificate locations
CERT_SEARCH_PATHS=(
    # System-wide locations
    "/etc/ssl/certs/ca-certificates.crt"              # Debian/Ubuntu
    "/etc/pki/tls/certs/ca-bundle.crt"               # RHEL/CentOS/Fedora
    "/etc/ssl/ca-bundle.pem"                          # OpenSUSE
    "/etc/ssl/cert.pem"                               # macOS/BSD
    "/usr/local/share/ca-certificates"                # Custom certificates directory
    "/etc/pki/ca-trust/source/anchors"                # RHEL/CentOS 7+
    
    # Enterprise-specific locations
    "/etc/ssl/certs/enterprise-ca.crt"
    "/etc/ssl/certs/company-ca.crt"
    "/usr/local/share/ca-certificates/enterprise"
    
    # User-specific locations
    "$HOME/.ssl/certs"
    "$HOME/.certificates"
    "$HOME/certificates"
)

# Function to detect available CA certificates
detect_ca_certificates() {
    echo "🔍 Detecting CA certificates on the system..."
    
    local found_certs=()
    
    for cert_path in "${CERT_SEARCH_PATHS[@]}"; do
        if [ -f "$cert_path" ]; then
            # Verify it's a valid certificate
            if openssl x509 -in "$cert_path" -noout 2>/dev/null; then
                found_certs+=("$cert_path")
                echo "   ✅ Found valid certificate: $cert_path"
            fi
        elif [ -d "$cert_path" ]; then
            # Search for .crt, .pem, .cer files in directory
            while IFS= read -r -d '' cert_file; do
                if openssl x509 -in "$cert_file" -noout 2>/dev/null; then
                    found_certs+=("$cert_file")
                    echo "   ✅ Found valid certificate: $cert_file"
                fi
            done < <(find "$cert_path" -type f \( -name "*.crt" -o -name "*.pem" -o -name "*.cer" \) -print0 2>/dev/null)
        fi
    done
    
    if [ ${#found_certs[@]} -eq 0 ]; then
        echo "   ℹ️  No custom CA certificates found in common locations"
        echo "   ℹ️  System will use default CA trust store"
    else
        echo "   📊 Found ${#found_certs[@]} CA certificate(s)"
    fi
    
    # Return array as newline-separated string
    printf '%s\n' "${found_certs[@]}"
}

# Function to validate a certificate file
validate_certificate() {
    local cert_path="$1"
    
    if [ ! -f "$cert_path" ]; then
        echo "❌ Certificate file not found: $cert_path"
        return 1
    fi
    
    echo "🔍 Validating certificate: $cert_path"
    
    # Check if it's a valid X.509 certificate
    if ! openssl x509 -in "$cert_path" -noout 2>/dev/null; then
        echo "   ❌ Invalid certificate format"
        return 1
    fi
    
    # Get certificate details
    local subject=$(openssl x509 -in "$cert_path" -noout -subject 2>/dev/null | sed 's/subject=//')
    local issuer=$(openssl x509 -in "$cert_path" -noout -issuer 2>/dev/null | sed 's/issuer=//')
    local dates=$(openssl x509 -in "$cert_path" -noout -dates 2>/dev/null)
    
    echo "   📋 Subject: $subject"
    echo "   📋 Issuer: $issuer"
    echo "   📋 $dates"
    
    # Check if certificate is expired
    if ! openssl x509 -in "$cert_path" -noout -checkend 0 2>/dev/null; then
        echo "   ⚠️  WARNING: Certificate is expired!"
        return 1
    fi
    
    echo "   ✅ Certificate is valid"
    return 0
}

# Function to import CA certificate to APISIX container
import_ca_to_apisix() {
    local cert_path="$1"
    local container_name="${2:-apisix-apisix-1}"
    
    echo "📥 Importing CA certificate to APISIX container..."
    
    # Validate certificate first
    if ! validate_certificate "$cert_path"; then
        return 1
    fi
    
    # Check if container is running
    if ! docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
        echo "❌ APISIX container '$container_name' is not running"
        return 1
    fi
    
    # Create SSL directory in container if it doesn't exist
    docker exec "$container_name" mkdir -p /usr/local/apisix/conf/ssl/ca 2>/dev/null
    
    # Copy certificate to container
    local cert_filename=$(basename "$cert_path")
    if docker cp "$cert_path" "${container_name}:/usr/local/apisix/conf/ssl/ca/${cert_filename}"; then
        echo "   ✅ Certificate copied to container"
    else
        echo "   ❌ Failed to copy certificate to container"
        return 1
    fi
    
    # Create a combined CA bundle in the container
    echo "   🔧 Creating combined CA bundle..."
    docker exec "$container_name" sh -c '
        ca_bundle="/usr/local/apisix/conf/ssl/ca/ca-bundle.crt"
        > "$ca_bundle"
        
        # Add system CAs first
        if [ -f "/etc/ssl/certs/ca-certificates.crt" ]; then
            cat "/etc/ssl/certs/ca-certificates.crt" >> "$ca_bundle"
        elif [ -f "/etc/pki/tls/certs/ca-bundle.crt" ]; then
            cat "/etc/pki/tls/certs/ca-bundle.crt" >> "$ca_bundle"
        fi
        
        # Add custom CAs
        for cert in /usr/local/apisix/conf/ssl/ca/*.crt; do
            if [ -f "$cert" ] && [ "$cert" != "$ca_bundle" ]; then
                echo "" >> "$ca_bundle"
                cat "$cert" >> "$ca_bundle"
            fi
        done
        
        echo "CA bundle created with $(grep -c "BEGIN CERTIFICATE" "$ca_bundle") certificates"
    '
    
    # Update APISIX configuration to use the CA bundle
    echo "   🔧 Updating APISIX configuration..."
    docker exec "$container_name" sh -c '
        config_file="/usr/local/apisix/conf/config.yaml"
        ca_bundle="/usr/local/apisix/conf/ssl/ca/ca-bundle.crt"
        
        # Check if nginx_config section exists
        if ! grep -q "nginx_config:" "$config_file"; then
            echo "" >> "$config_file"
            echo "nginx_config:" >> "$config_file"
            echo "  http:" >> "$config_file"
            echo "    lua_ssl_trusted_certificate: $ca_bundle" >> "$config_file"
        elif ! grep -q "lua_ssl_trusted_certificate:" "$config_file"; then
            # Add under nginx_config.http
            sed -i "/nginx_config:/,/^[^ ]/ { /http:/a\\    lua_ssl_trusted_certificate: $ca_bundle" "$config_file"
        fi
    '
    
    echo "   ✅ CA certificate imported successfully"
    echo "   ℹ️  You may need to restart APISIX for changes to take effect"
    return 0
}

# Function to setup CA certificates for all OpenAPI providers
setup_provider_certificates() {
    echo "🔐 Setting up CA certificates for OpenAPI providers..."
    
    # Load AI tokens configuration
    if [ -f "./ai-tokens.env" ]; then
        source "./ai-tokens.env"
    else
        echo "⚠️  ai-tokens.env not found"
        return 1
    fi
    
    local setup_count=0
    
    # Check each provider
    for i in {1..10}; do
        local enabled_var="OPENAPI_${i}_ENABLED"
        local ca_cert_var="OPENAPI_${i}_CA_CERT_PATH"
        local name_var="OPENAPI_${i}_NAME"
        
        if [ "${!enabled_var}" = "true" ] && [ -n "${!ca_cert_var}" ]; then
            local ca_cert_path="${!ca_cert_var}"
            local provider_name="${!name_var:-Provider $i}"
            
            echo ""
            echo "📌 Processing certificates for $provider_name..."
            
            if import_ca_to_apisix "$ca_cert_path"; then
                setup_count=$((setup_count + 1))
            fi
        fi
    done
    
    if [ $setup_count -gt 0 ]; then
        echo ""
        echo "✅ Imported CA certificates for $setup_count provider(s)"
        
        # Restart APISIX to apply changes
        echo "🔄 Restarting APISIX to apply certificate changes..."
        docker restart apisix-apisix-1
        
        # Wait for APISIX to be ready
        local retries=0
        while [ $retries -lt 10 ]; do
            if curl -s http://localhost:9080/apisix/admin/routes -H "X-API-KEY: test" >/dev/null 2>&1; then
                echo "✅ APISIX restarted successfully"
                break
            fi
            echo "⏳ Waiting for APISIX to be ready..."
            sleep 2
            retries=$((retries + 1))
        done
    else
        echo "ℹ️  No providers have custom CA certificates configured"
    fi
    
    return 0
}

# Function to test SSL connection with custom CA
test_ssl_connection() {
    local url="$1"
    local ca_cert_path="${2:-}"
    
    echo "🔒 Testing SSL connection to: $url"
    
    local curl_opts="-s -I --max-time 10"
    
    if [ -n "$ca_cert_path" ] && [ -f "$ca_cert_path" ]; then
        echo "   Using CA certificate: $ca_cert_path"
        curl_opts="$curl_opts --cacert $ca_cert_path"
    else
        echo "   Using system CA certificates"
    fi
    
    if curl $curl_opts "$url" >/dev/null 2>&1; then
        echo "   ✅ SSL connection successful"
        return 0
    else
        echo "   ❌ SSL connection failed"
        
        # Try to get more details about the failure
        echo "   🔍 SSL error details:"
        curl -v $curl_opts "$url" 2>&1 | grep -E "(SSL|certificate|verify)" | sed 's/^/      /'
        
        return 1
    fi
}

# Main execution - only if run directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    case "${1:-}" in
        detect)
            detect_ca_certificates
            ;;
        validate)
            if [ -z "$2" ]; then
                echo "Usage: $0 validate <certificate-path>"
                exit 1
            fi
            validate_certificate "$2"
            ;;
        import)
            if [ -z "$2" ]; then
                echo "Usage: $0 import <certificate-path> [container-name]"
                exit 1
            fi
            import_ca_to_apisix "$2" "${3:-apisix-apisix-1}"
            ;;
        setup)
            setup_provider_certificates
            ;;
        test)
            if [ -z "$2" ]; then
                echo "Usage: $0 test <https-url> [ca-cert-path]"
                exit 1
            fi
            test_ssl_connection "$2" "${3:-}"
            ;;
        *)
            echo "Certificate Management for ViolentUTF APISIX"
            echo ""
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  detect                    - Detect CA certificates on the system"
            echo "  validate <cert-path>      - Validate a certificate file"
            echo "  import <cert-path>        - Import CA certificate to APISIX"
            echo "  setup                     - Setup certificates for all providers"
            echo "  test <url> [ca-cert]      - Test SSL connection"
            echo ""
            ;;
    esac
fi