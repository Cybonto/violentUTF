# Credential Preservation in ViolentUTF Setup

## Overview
This document describes the modifications made to the ViolentUTF setup scripts to preserve credentials during cleanup operations and reuse existing credentials on subsequent setups.

## Problem Statement
Previously, the `--cleanup` flag would remove all generated .env files containing important credentials like API keys, passwords, and secrets. This required users to update their configurations with new credentials after every cleanup, which was inconvenient for development and testing workflows.

## Solution Implemented

### 1. Modified Cleanup Script
**File**: `setup_macos_files/cleanup.sh`

The cleanup script was updated to preserve .env files during standard cleanup operations:
- Added logic to skip deletion of .env files when cleaning configuration directories
- Added explicit logging to show which .env files were preserved
- Only deep cleanup (`--deepcleanup`) will now remove .env files

Key changes:
```bash
# Remove all config files EXCEPT .env files
find "apisix/conf" -type f ! -name "*.template" ! -name ".env" -delete 2>/dev/null || true

# NOTE: .env files are preserved to maintain credentials
echo "📝 Preserved .env files:"
[ -f "keycloak/.env" ] && echo "  ✓ keycloak/.env"
[ -f "apisix/.env" ] && echo "  ✓ apisix/.env"
[ -f "violentutf/.env" ] && echo "  ✓ violentutf/.env"
[ -f "violentutf_api/fastapi_app/.env" ] && echo "  ✓ violentutf_api/fastapi_app/.env"
```

### 2. Updated Secret Generation
**File**: `setup_macos_files/utils.sh`

The `generate_all_secrets()` function was completely rewritten to:
- Check for existing .env files before generating new secrets
- Load and reuse existing credentials when available
- Only generate new secrets for missing values
- Provide detailed logging about which credentials are being reused vs newly generated

Example logic:
```bash
# Check for existing Keycloak credentials
if [ -f "keycloak/.env" ]; then
    log_detail "Found existing Keycloak credentials, reusing..."
    source keycloak/.env
    # Use existing values if available
    KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-}"
    
    # Generate new passwords only if not found
    if [ -z "$KEYCLOAK_ADMIN_PASSWORD" ]; then
        KEYCLOAK_ADMIN_PASSWORD=$(generate_secure_string)
        log_detail "Generated new Keycloak admin password"
    else
        log_detail "Reusing existing Keycloak admin password"
    fi
```

### 3. Enhanced Backup/Restore Functions
**File**: `setup_macos_files/env_management.sh`

Updated the backup and restore functions to handle .env files:

**Backup function** now includes:
- Backing up all .env files to `/tmp/vutf_backup/`
- Backing up Streamlit secrets.toml
- Preserving the exact credentials for later restoration

**Restore function** now includes:
- Restoring all backed-up .env files to their original locations
- Creating necessary directories if they don't exist
- Providing feedback about which files were restored

### 4. Fixed Display of Credentials
**File**: `setup_macos_files/utils.sh`

Updated `display_generated_secrets()` to show the actual Keycloak admin password instead of a placeholder, making it easier for users to access their systems after setup.

## Benefits

1. **Credential Persistence**: Users can run `--cleanup` without losing their configured credentials
2. **Seamless Re-setup**: Running setup again will automatically use existing credentials
3. **Development Workflow**: Easier testing and development as credentials remain stable
4. **Security**: Credentials are still generated securely when needed, but preserved when appropriate
5. **User Experience**: No need to update client configurations after cleanup operations

## Usage

### Standard Cleanup (Preserves Credentials)
```bash
./setup_macos_new.sh --cleanup
```
This will clean up containers and configurations but preserve all .env files and credentials.

### Deep Cleanup (Removes Everything)
```bash
./setup_macos_new.sh --deepcleanup
```
This will remove everything including .env files and all credentials.

### Re-setup with Existing Credentials
```bash
./setup_macos_new.sh
```
If .env files exist from a previous setup, they will be automatically detected and reused.

## Important Notes

1. The backup/restore mechanism ensures that even if files are accidentally removed, they can be recovered from `/tmp/vutf_backup/` during the same session.

2. For security reasons, some credentials (like APISIX dashboard passwords) are always regenerated to ensure they remain secure.

3. The system maintains consistency by ensuring that shared secrets (like API keys) are synchronized across services when reusing credentials.

4. Users should still securely store their credentials externally for disaster recovery purposes.