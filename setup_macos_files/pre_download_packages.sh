#!/usr/bin/env bash
# pre_download_packages.sh - Pre-download large Python packages to avoid timeouts

# Function to pre-download packages
pre_download_large_packages() {
    log_detail "Pre-downloading large Python packages..."
    
    # Create a temporary directory for downloads
    local download_dir="/tmp/vutf_pip_cache"
    mkdir -p "$download_dir"
    
    # List of large packages that often timeout
    local large_packages=(
        "botocore==1.38.13"
        "boto3==1.38.13"
        "torch>=2.7.1"
        "transformers>=4.52.1"
    )
    
    # Try to download packages
    log_info "Downloading packages that commonly cause timeouts..."
    for package in "${large_packages[@]}"; do
        log_debug "Downloading $package..."
        if pip download --dest "$download_dir" --timeout 600 --retries 10 "$package" >/dev/null 2>&1; then
            log_success "Downloaded $package"
        else
            log_warn "Failed to download $package (will retry during build)"
        fi
    done
    
    # Create a requirements file that references local wheels
    if ls "$download_dir"/*.whl >/dev/null 2>&1; then
        log_info "Creating optimized requirements file..."
        
        # Copy wheels to FastAPI build context
        if [ -d "../violentutf_api/fastapi_app" ]; then
            cp "$download_dir"/*.whl ../violentutf_api/fastapi_app/ 2>/dev/null || true
            log_success "Copied pre-downloaded packages to build context"
        fi
    fi
    
    # Clean up
    rm -rf "$download_dir"
}

# Export the function for use in other modules
export -f pre_download_large_packages