#!/usr/bin/env bash
# validate_https_config.sh - Validate HTTPS configuration for OpenAPI providers

# Source utilities if not already loaded
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v parse_url &> /dev/null; then
    source "$SCRIPT_DIR/utils.sh"
fi

# Function to validate HTTPS configuration for a provider
validate_provider_https_config() {
    local provider_num="$1"
    local provider_id="${2:-}"
    
    # Get environment variables
    local base_url_var="OPENAPI_${provider_num}_BASE_URL"
    local use_https_var="OPENAPI_${provider_num}_USE_HTTPS"
    local ssl_verify_var="OPENAPI_${provider_num}_SSL_VERIFY"
    local ca_cert_var="OPENAPI_${provider_num}_CA_CERT_PATH"
    local enabled_var="OPENAPI_${provider_num}_ENABLED"
    
    local base_url="${!base_url_var:-}"
    local use_https="${!use_https_var:-auto}"
    local ssl_verify="${!ssl_verify_var:-true}"
    local ca_cert_path="${!ca_cert_var:-}"
    local enabled="${!enabled_var:-false}"
    
    # Skip if provider is not enabled
    if [ "$enabled" != "true" ]; then
        return 0
    fi
    
    echo "🔍 Validating HTTPS configuration for OpenAPI provider $provider_num${provider_id:+ ($provider_id)}..."
    
    local has_error=false
    local has_warning=false
    
    # Extract scheme from URL
    local url_scheme=$(parse_url "$base_url" scheme)
    
    # Check 1: Conflicting scheme settings
    if [ "$use_https" != "auto" ]; then
        if [[ "$use_https" = "true" && "$url_scheme" = "http" ]]; then
            echo "   ⚠️  WARNING: URL uses http:// but USE_HTTPS=true. Will force HTTPS."
            echo "      Consider updating BASE_URL to use https://"
            has_warning=true
        elif [[ "$use_https" = "false" && "$url_scheme" = "https" ]]; then
            echo "   ⚠️  WARNING: URL uses https:// but USE_HTTPS=false. Will force HTTP."
            echo "      This may cause connection failures!"
            has_warning=true
        fi
    fi
    
    # Determine effective scheme
    local effective_scheme
    if [ "$use_https" = "auto" ]; then
        effective_scheme="$url_scheme"
    elif [ "$use_https" = "true" ]; then
        effective_scheme="https"
    else
        effective_scheme="http"
    fi
    
    # Check 2: SSL verification with HTTP
    if [[ "$effective_scheme" = "http" && "$ssl_verify" = "true" ]]; then
        echo "   ℹ️  INFO: SSL_VERIFY=true but using HTTP. SSL verification will be ignored."
    fi
    
    # Check 3: CA certificate path validation
    if [ -n "$ca_cert_path" ]; then
        if [ ! -f "$ca_cert_path" ]; then
            echo "   ❌ ERROR: CA certificate file not found: $ca_cert_path"
            has_error=true
        else
            echo "   ✅ Custom CA certificate found: $ca_cert_path"
            
            # Verify it's a valid certificate
            if ! openssl x509 -in "$ca_cert_path" -noout 2>/dev/null; then
                echo "   ❌ ERROR: Invalid certificate format in: $ca_cert_path"
                has_error=true
            fi
        fi
    fi
    
    # Check 4: GSAi-specific validation
    if [[ "$provider_id" == *"gsai"* ]] || [[ "$base_url" == *"gsai"* ]] || [[ "$base_url" == *"ai-gov"* ]]; then
        echo "   🔍 Detected GSAi provider - applying enterprise checks..."
        
        if [[ "$effective_scheme" = "https" && "$ssl_verify" = "false" ]]; then
            echo "   ⚠️  WARNING: GSAi with HTTPS but SSL_VERIFY=false"
            echo "      For production, enable SSL verification and provide CA certificate"
            has_warning=true
        fi
        
        # Check for common enterprise CA paths if no custom CA provided
        if [[ "$effective_scheme" = "https" && -z "$ca_cert_path" ]]; then
            local common_ca_paths=(
                "/etc/ssl/certs/ca-certificates.crt"
                "/etc/pki/tls/certs/ca-bundle.crt"
                "/usr/local/share/ca-certificates"
                "/etc/ssl/certs"
            )
            
            local ca_found=false
            for ca_path in "${common_ca_paths[@]}"; do
                if [ -e "$ca_path" ]; then
                    ca_found=true
                    break
                fi
            done
            
            if ! $ca_found; then
                echo "   ⚠️  WARNING: No CA certificate path specified for HTTPS GSAi"
                echo "      System CA certificates may not include enterprise CA"
                has_warning=true
            fi
        fi
    fi
    
    # Check 5: Security recommendations
    if [[ "$effective_scheme" = "https" && "$ssl_verify" = "false" ]]; then
        echo "   ⚠️  SECURITY WARNING: HTTPS with SSL_VERIFY=false is insecure!"
        echo "      Only use this for development/testing with self-signed certificates"
        has_warning=true
    fi
    
    # Summary
    if $has_error; then
        echo "   ❌ Validation FAILED - Please fix errors before proceeding"
        return 1
    elif $has_warning; then
        echo "   ⚠️  Validation completed with warnings"
        return 0
    else
        echo "   ✅ HTTPS configuration validated successfully"
        echo "      Scheme: $effective_scheme, SSL Verify: $ssl_verify"
        return 0
    fi
}

# Function to validate all OpenAPI providers
validate_all_providers() {
    echo "=== Validating HTTPS Configuration for OpenAPI Providers ==="
    
    local has_errors=false
    
    # Check up to 10 providers
    for i in {1..10}; do
        local enabled_var="OPENAPI_${i}_ENABLED"
        local id_var="OPENAPI_${i}_ID"
        
        if [ "${!enabled_var}" = "true" ]; then
            local provider_id="${!id_var:-}"
            if ! validate_provider_https_config "$i" "$provider_id"; then
                has_errors=true
            fi
            echo ""  # Blank line between providers
        fi
    done
    
    if $has_errors; then
        echo "❌ Some providers have configuration errors. Please fix them before proceeding."
        return 1
    else
        echo "✅ All enabled providers passed validation"
        return 0
    fi
}

# Main execution - only if run directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    # Load ai-tokens.env if it exists
    if [ -f "ai-tokens.env" ]; then
        source "ai-tokens.env"
    elif [ -f "../ai-tokens.env" ]; then
        source "../ai-tokens.env"
    else
        echo "❌ ai-tokens.env not found"
        exit 1
    fi
    
    validate_all_providers
fi