# Fix Script Migration Guide

## Overview

The ViolentUTF fix scripts have been consolidated into a single comprehensive script `fix_violentutf_issues.sh` (v3.0.0) that provides better diagnostics, backup/rollback capabilities, and more robust fixes.

## Migration from Old Scripts

### Old Scripts → New Consolidated Script

| Old Script | New Command |
|------------|-------------|
| `diagnose_api_key_issue.sh` | `./fix_violentutf_issues.sh --diagnose-only` |
| `fix_enterprise_api_key.sh` | `./fix_violentutf_issues.sh --fix-api-keys` |
| `fix_gsai_ai_proxy.sh` | `./fix_violentutf_issues.sh --fix-gsai` |
| `fix_gsai_auth.sh` | `./fix_violentutf_issues.sh --fix-gsai` |
| `fix_gsai_bearer_token.sh` | `./fix_violentutf_issues.sh --fix-gsai` |

## New Features

### 1. Backup and Rollback
- **Automatic Backup**: Creates backups before applying fixes
- **Rollback**: Restore previous configuration if fixes cause issues
```bash
# List available backups and rollback
./fix_violentutf_issues.sh --rollback

# Skip backup creation
./fix_violentutf_issues.sh --no-backup
```

### 2. Enhanced Diagnostics
- **Network Connectivity**: Tests Docker network and service health
- **SSL Certificate**: Detects and reports SSL verification issues
- **Detailed Error Analysis**: Provides specific error context

### 3. Selective Fixes
```bash
# Fix only specific issues
./fix_violentutf_issues.sh --fix-api-keys     # API key and consumer issues
./fix_violentutf_issues.sh --fix-gsai         # GSAi routing issues
./fix_violentutf_issues.sh --fix-permissions  # APISIX admin permissions
./fix_violentutf_issues.sh --fix-network      # Docker network issues

# Combine multiple fixes
./fix_violentutf_issues.sh --fix-api-keys --fix-gsai
```

### 4. Logging and Verbose Output
```bash
# Enable detailed output
./fix_violentutf_issues.sh --verbose

# Log all output to file
./fix_violentutf_issues.sh --log
```

## Common Use Cases

### Enterprise Environment GSAi Issues
If you're experiencing GSAi authentication issues in enterprise environments:
```bash
# First diagnose the issue
./fix_violentutf_issues.sh --diagnose-only

# Then apply GSAi-specific fixes
./fix_violentutf_issues.sh --fix-gsai --verbose
```

### API Key Synchronization
When API keys are out of sync across services:
```bash
# Fix API key issues with automatic backup
./fix_violentutf_issues.sh --fix-api-keys
```

### Complete System Check and Fix
For a comprehensive diagnostic and fix:
```bash
# Run full diagnostics and apply all fixes
./fix_violentutf_issues.sh

# Force fixes without prompts
./fix_violentutf_issues.sh --force
```

### Recovery from Failed Fixes
If fixes cause issues:
```bash
# List available backups and select one to restore
./fix_violentutf_issues.sh --rollback

# Or specify a specific backup
./fix_violentutf_issues.sh --rollback 20250723_141523
```

## Key Improvements

1. **GSAi Route Configuration**
   - Correctly removes `key-auth` plugin from GSAi routes
   - Respects `OPENAPI_1_SSL_VERIFY` setting
   - Handles self-signed certificates properly

2. **API Key Management**
   - Synchronizes keys across all services
   - Creates all required consumers
   - Prioritizes FastAPI key if different

3. **Network Diagnostics**
   - Verifies Docker network connectivity
   - Tests service-to-service communication
   - Automatically reconnects disconnected containers

4. **Error Recovery**
   - Creates timestamped backups before changes
   - Allows easy rollback to previous state
   - Provides detailed error messages with solutions

## Deprecation Notice

The following scripts are deprecated and will be removed in a future release:
- `diagnose_api_key_issue.sh`
- `fix_enterprise_api_key.sh`
- `fix_gsai_ai_proxy.sh`
- `fix_gsai_auth.sh`
- `fix_gsai_bearer_token.sh`

Please update your workflows to use the consolidated `fix_violentutf_issues.sh` script.

## Troubleshooting

### Script Requirements
- `jq` for JSON processing
- `curl` for API calls
- Docker access for network diagnostics
- Write permissions for backup directory

### Common Issues

1. **"jq is required but not installed"**
   ```bash
   # macOS
   brew install jq

   # Linux
   apt-get install jq
   ```

2. **"Cannot rollback: APISIX admin key not found"**
   - Ensure `apisix/.env` exists with `APISIX_ADMIN_KEY`

3. **Network fixes fail**
   - Ensure Docker daemon is running
   - Check Docker permissions

## Support

For issues or feature requests, please report at:
https://github.com/anthropics/claude-code/issues
