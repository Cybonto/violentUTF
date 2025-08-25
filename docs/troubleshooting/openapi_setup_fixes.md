# OpenAPI Setup Fixes Applied to setup_macos.sh

## Overview
Applied fixes from `refresh-openapi-routes.sh` to the `setup_openapi_routes()` function in `setup_macos.sh` to resolve key issues with OpenAPI route creation.

## Issues Fixed

### 1. SSL Certificate Handling
**Problem**: Intermittent SSL connectivity tests could fail in corporate proxy environments.
**Fix**: Always use `-k` flag for curl requests to bypass SSL verification.

**Before**:
```bash
if ! curl -s --connect-timeout 5 --max-time 10 "${base_url%/}${spec_path}" > /dev/null 2>&1; then
    echo "⚠️  SSL connectivity issue detected, testing with insecure connection..."
    curl_args+=(-k)
fi
```

**After**:
```bash
# Always use -k flag for SSL bypass in corporate proxy environments
# This ensures compatibility with Zscaler and other corporate proxies
curl_args+=(-k)
echo "   Using --insecure flag to bypass SSL verification for corporate proxy compatibility"
```

### 2. Python Script Missing sys Import
**Problem**: The inline Python script was missing the `sys` import, causing failures when errors occurred.
**Fix**: Added proper imports and error handling.

**Before**:
```python
python3 -c "
import json
with open('$endpoints_file', 'r') as f:
    # ... processing code
"
```

**After**:
```python
python3 -c "
import json
import sys

try:
    with open('$endpoints_file', 'r') as f:
        # ... processing code
except Exception as e:
    print(f\"Error processing endpoints: {e}\", file=sys.stderr)
    sys.exit(1)
"
```

### 3. Route Creation Logic Simplification
**Problem**: Complex `ai-proxy` plugin configuration was causing route creation failures.
**Fix**: Simplified to use `proxy-rewrite` with `upstream` configuration, which is more reliable.

**Before**:
```json
{
  "plugins": {
    "key-auth": {},
    "ai-proxy": {
      "provider": "openai-compatible",
      "auth": { /* complex auth config */ },
      "options": { "model": "..." },
      "override": { "endpoint": "..." }
    }
  }
}
```

**After**:
```json
{
  "upstream": {
    "type": "roundrobin",
    "nodes": { "hostname:port": 1 },
    "scheme": "https"
  },
  "plugins": {
    "key-auth": {},
    "proxy-rewrite": {
      "regex_uri": ["^/ai/openapi/provider_id(.*)", "$1"]
    }
  }
}
```

### 4. Enhanced Error Handling and Logging
**Problem**: Limited error information when route creation failed.
**Fix**: Added comprehensive error logging and progress tracking.

**Improvements**:
- Added endpoint processing counter
- Enhanced error response logging
- Better progress visibility
- More detailed failure information

### 5. Hostname and Port Handling
**Problem**: Port extraction from URLs was inconsistent.
**Fix**: Proper hostname and port extraction with fallback defaults.

**Added**:
```bash
# Extract hostname and port from base_url for upstream configuration
local hostname=$(echo "$base_url" | sed -E 's|https?://([^/]+).*|\1|')
local scheme="https"
local port=443
if [[ "$base_url" == http://* ]]; then
    scheme="http"
    port=80
fi

# Handle explicit port in hostname
if [[ "$hostname" == *:* ]]; then
    port=$(echo "$hostname" | cut -d: -f2)
    hostname=$(echo "$hostname" | cut -d: -f1)
fi
```

## Files Modified

1. **`/Users/tamnguyen/Documents/GitHub/ViolentUTF/setup_macos.sh`**
   - Updated `fetch_openapi_spec()` function (lines ~1369-1373)
   - Updated `setup_openapi_routes()` function (lines ~1792-1806)
   - Updated `create_openapi_route()` function (lines ~1595-1646)

## Testing Recommendations

1. **Test SSL Bypass**: Verify that OpenAPI specs can be fetched from corporate proxy environments
2. **Test Route Creation**: Confirm that APISIX routes are actually created and functional
3. **Test Error Handling**: Verify that proper errors are logged when things fail
4. **Test Different URL Formats**: Test with various hostname:port combinations

## Next Steps

1. Run the updated setup script to verify fixes work
2. Monitor logs for any remaining issues
3. Test actual OpenAPI endpoint proxying through APISIX
4. Consider adding integration tests for OpenAPI setup

## Files Referenced

- Source fixes: `refresh-openapi-routes.sh`
- Updated file: `setup_macos.sh`
- Functions modified:
  - `fetch_openapi_spec()`
  - `setup_openapi_routes()`
  - `create_openapi_route()`