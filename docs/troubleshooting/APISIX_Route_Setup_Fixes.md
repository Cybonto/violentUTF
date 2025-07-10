# APISIX Route Setup Fixes

## Issues Resolved

### Problem: ❌ APISIX admin API is not ready - cannot setup OpenAPI routes

**Root Cause:** The setup scripts were using hardcoded fallback admin keys instead of loading the actual admin key from `apisix/.env`.

### Issues Found and Fixed:

1. **Hardcoded Admin Keys**
   - `ai_providers_setup.sh` was using `${APISIX_ADMIN_KEY:-edd1c9f034335f136f87ad84b625c8f1}`
   - This fallback key didn't match the actual generated key in `apisix/.env`
   - All route creation functions were failing due to authentication

2. **Missing Wait Logic**
   - `wait_for_apisix_ready()` function was referenced but didn't exist
   - No proper readiness checks before attempting route creation
   - Scripts were trying to create routes before APISIX was fully initialized

3. **Inconsistent Environment Loading**
   - Some functions loaded `apisix/.env`, others didn't
   - Race conditions between setup phases

## Solutions Implemented:

### ✅ Fixed Admin Key Loading
Updated all functions in `ai_providers_setup.sh` to properly load admin key:

```bash
# Load APISIX admin key from .env file
if [ -f "apisix/.env" ]; then
    source "apisix/.env"
fi

if [ -z "$APISIX_ADMIN_KEY" ]; then
    echo "❌ ERROR: APISIX_ADMIN_KEY not found"
    return 1
fi

local admin_key="$APISIX_ADMIN_KEY"
```

### ✅ Added Proper Wait Logic
Created `wait_for_apisix_ready()` function in `apisix_setup.sh`:

- **Phase 1**: Wait for admin port to respond (max 60 seconds)
- **Phase 2**: Wait for admin API with authentication (max 45 seconds)
- **Total timeout**: 105 seconds with detailed progress logging

### ✅ Enhanced Consumer Registration
Added `register_api_key_consumer()` function:
- Creates API key consumer for route authentication
- Handles existing consumer gracefully
- Proper error handling and status reporting

### ✅ Improved OpenAPI Setup
Enhanced `openapi_setup.sh`:
- Dynamic base URL support (no hardcoded production URLs)
- Simplified authentication (removed dual auth complexity)
- Health checks for OpenAPI providers
- Better error handling and logging

## Current Status

The setup now properly:

1. **Waits for APISIX** to be fully ready before creating routes
2. **Loads correct admin keys** from environment files
3. **Creates routes successfully** for OpenAI, Anthropic, and OpenAPI providers
4. **Validates provider health** before route creation
5. **Provides detailed logging** for troubleshooting

## Testing

You can now run `./setup_macos_new.sh` and it will:
- ✅ Wait for APISIX to be ready
- ✅ Load the correct admin key from `apisix/.env`
- ✅ Create OpenAI routes (if enabled and API key configured)
- ✅ Create Anthropic routes (if enabled and API key configured)
- ✅ Create GSAi API routes (if enabled) at:
  - `http://localhost:9080/ai/gsai-api-1/chat/completions`
  - `http://localhost:9080/ai/gsai-api-1/models`

## Log Files

Setup logs are available at:
- `./tmp/violentutf_openapi_setup.log` - OpenAPI provider setup details

## Manual Testing

Verify APISIX is working:
```bash
# Test admin API access
source apisix/.env
curl -H "X-API-KEY: $APISIX_ADMIN_KEY" http://localhost:9180/apisix/admin/routes

# Test route creation (after running setup)
curl -H "X-API-Key: your_api_key" http://localhost:9080/ai/gsai-api-1/models
```

The fixes ensure robust, reliable route creation with proper error handling and detailed feedback.