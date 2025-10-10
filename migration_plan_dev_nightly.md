# Migration Analysis: dev_backup to dev_nightly

## Summary of Changes in dev_backup (after commit 7913bed)

### Key Commits:
1. **7913bed** - Sync dev_nightly with main: include merge commit from PR #182
2. **16762be** - Update setup
3. **e463185** - Improved supports for enterprise env with Zscaler
4. **39bd1ee** - LOCALLY WORKING VERSION - MAC OS
5. **251cd30** - Add explicit support for zscaler during setup
6. **7dc1064** - Update Dockerfile.zscaler
7. **4369a38** - Add better route setup

## Critical Changes Made in dev_backup

### 1. Provider-Agnostic Setup (Most Important)
The main fix was removing all GSAi-specific hardcoding and making the setup provider-agnostic.

#### Files Modified:
- `setup_macos_files/openapi_setup.sh`
- `setup_macos_files/apisix_setup.sh`
- `setup_macos_files/env_management.sh`

### 2. Specific Changes in openapi_setup.sh

#### BEFORE (GSAi-specific):
```bash
# Lines 119-130: GSAi-specific Docker handling
if [[ "$provider_id" == *"gsai"* ]] && docker network inspect vutf-network 2>/dev/null | grep -q "ai-gov-api-app-1"; then
    host_port="ai-gov-api-app-1:8080"
```

#### AFTER (Provider-agnostic):
```bash
# Generic Docker handling for ALL providers
if docker network inspect vutf-network 2>/dev/null | grep -q "apisix-apisix-1"; then
    # Check for custom API containers on vutf-network
    local custom_container=$(docker network inspect vutf-network 2>/dev/null | jq -r '.[] | .Containers | to_entries[] | select(.value.Name | contains("app") or contains("api")) | .value.Name' | head -1)
```

#### SSL Verification Logic Changed:
```bash
# BEFORE: Provider-specific SSL logic
if [[ "$provider_id" == *"gsai"* ]]; then
    scheme="http"  # FORCED HTTP for GSAi
    ssl_verify="false"
fi

# AFTER: Based on --zscaler flag and scheme
if [[ "$FORCE_ZSCALER" == "true" ]]; then
    ssl_verify="false"  # Zscaler intercepts SSL
elif [[ "$scheme" == "https" ]]; then
    ssl_verify="true"   # Regular HTTPS
else
    ssl_verify="false"  # HTTP doesn't need SSL
fi
```

### 3. Changes in apisix_setup.sh

- Removed "GSAi now uses HTTP" comments
- Changed from GSAi-specific to generic certificate handling
- Updated comments to be provider-agnostic

### 4. Changes in env_management.sh

- Changed example from "GSAi API" to generic "OpenAPI Provider"
- Removed GSAi-specific references

### 5. Added --zscaler Flag Support

In `setup_macos_new.sh`:
```bash
--zscaler)
    export FORCE_ZSCALER=true
    export AUTO_GENERATE_CERTS=true
    echo "🔐 Zscaler/corporate proxy support enabled"
```

### 6. Dockerfile.zscaler Updates

- Removed `zscaler.pem` reference (file doesn't exist)
- Kept only `zscaler.crt` and `CA.crt`
- Aligned with standard Dockerfile structure

## Current State Analysis

### dev_nightly vs dev_backup

dev_nightly has MANY more features (280 files changed, 76093 insertions vs 1692 deletions):
- New Report Setup functionality
- COB (Close of Business) reports
- Enhanced dashboard features
- Documentation improvements
- Linux setup support
- Many new test files
- Certificate management improvements

However, dev_nightly still has the OLD provider-specific code that we fixed in dev_backup.

## Migration Strategy

### Files to Update in dev_nightly:

1. **setup_macos_files/openapi_setup.sh**
   - Remove GSAi-specific logic (lines 119-130, 189-199, 330-337)
   - Update SSL verification to use FORCE_ZSCALER
   - Make route creation provider-agnostic

2. **setup_macos_files/apisix_setup.sh**
   - Remove GSAi comments (lines 5-8, 13, 255-256, 262, 397-398, 459)
   - Update to use FORCE_ZSCALER for SSL decisions

3. **setup_macos_files/env_management.sh**
   - Update example providers to be generic
   - Remove GSAi references

4. **setup_macos_new.sh**
   - Already has --zscaler flag support (good!)

5. **violentutf_api/fastapi_app/Dockerfile.zscaler**
   - Remove `zscaler.pem` reference (already done)
   - Ensure consistent with standard Dockerfile

## Detailed Migration Plan

### Phase 1: Backup Current State
```bash
git checkout dev_nightly
git checkout -b dev_nightly_migration_backup
```

### Phase 2: Apply Provider-Agnostic Fixes

#### A. Fix openapi_setup.sh
1. Lines 115-147: Replace GSAi-specific Docker logic with generic logic
2. Lines 186-197: Replace provider-specific SSL with FORCE_ZSCALER logic
3. Lines 199-201: Change condition from GSAi-specific to auth-type based
4. Lines 336-338: Change from GSAi-specific to auth-type based

#### B. Fix apisix_setup.sh
1. Line 5: Remove "deprecated since GSAi" comment
2. Line 8: Remove GSAi note
3. Line 13: Change "Check for ai-gov-api stack (GSAi)" to generic
4. Lines 255-261: Update SSL certificate logic
5. Line 262: Update comment
6. Lines 397-398: Remove GSAi reference
7. Line 459: Remove GSAi reference

#### C. Fix env_management.sh
1. Line 31: Remove GSAi reference
2. Lines 34-37: Change example to generic
3. Line 41: Change token placeholder

### Phase 3: Testing Strategy

1. Test with HTTP provider (no SSL)
2. Test with HTTPS provider (with SSL)
3. Test with --zscaler flag (SSL bypass)
4. Test with staging GSAi endpoint

### Phase 4: Validation

Ensure that:
- Setup respects URL scheme from ai-tokens.env
- No hardcoded provider-specific logic remains
- SSL verification works correctly with/without --zscaler
- All providers work identically

## Risk Assessment

### Low Risk:
- Changes are isolated to setup scripts
- Core functionality unchanged
- Already tested in dev_backup

### Medium Risk:
- dev_nightly has many new features that might interact
- Need to ensure new Report/COB features aren't affected

### Mitigation:
- Create backup branch first
- Test thoroughly in dev environment
- Have rollback plan ready

## Implementation Order

1. Create backup branch
2. Apply openapi_setup.sh changes
3. Apply apisix_setup.sh changes
4. Apply env_management.sh changes
5. Test basic setup
6. Test with various providers
7. Test new features (Reports, COB)
8. Commit and push

## Commands to Execute

```bash
# 1. Backup
git checkout dev_nightly
git checkout -b dev_nightly_pre_migration_backup
git push origin dev_nightly_pre_migration_backup

# 2. Create working branch
git checkout -b dev_nightly_provider_agnostic_fix

# 3. Apply changes (manual editing required)

# 4. Test
./setup_macos_new.sh --cleanup
./setup_macos_new.sh
./setup_macos_new.sh --zscaler  # Test with Zscaler

# 5. Commit
git add -A
git commit -m "Apply provider-agnostic fixes from dev_backup

- Remove all GSAi-specific hardcoding
- Make setup respect URL schemes from ai-tokens.env
- Add proper SSL verification based on --zscaler flag
- Align with fixes from commits 16762be through 4369a38"

# 6. Push
git push origin dev_nightly_provider_agnostic_fix
```
