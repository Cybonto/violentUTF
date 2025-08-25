# OpenAPI Setup Troubleshooting Guide

## Overview
This guide helps diagnose and fix issues when OpenAPI routes are not being created during setup.

## Quick Diagnostic Steps

### 1. Run the Debug Script
```bash
./debug-openapi-setup.sh
```
This will check:
- ai-tokens.env configuration
- OpenAPI spec accessibility
- APISIX connectivity
- Required functions
- Syntax validation

### 2. Check Service Status
```bash
./check_services.sh
```
Ensure all services are running:
- APISIX (port 9080/9180)
- Keycloak (port 8080)
- ViolentUTF API (port 8000)

### 3. Verify Environment Variables
```bash
# Load your config
source ai-tokens.env

# Check key variables
echo "OPENAPI_ENABLED: $OPENAPI_ENABLED"
echo "OPENAPI_1_ENABLED: $OPENAPI_1_ENABLED"
echo "OPENAPI_1_ID: $OPENAPI_1_ID"
echo "OPENAPI_1_BASE_URL: $OPENAPI_1_BASE_URL"
echo "OPENAPI_1_SPEC_PATH: $OPENAPI_1_SPEC_PATH"
echo "OPENAPI_1_AUTH_TYPE: $OPENAPI_1_AUTH_TYPE"
```

## Common Issues and Solutions

### Issue 1: "No OpenAPI routes created"

**Symptoms:**
- Setup completes without errors
- No routes visible in APISIX
- ViolentUTF UI shows no OpenAPI providers

**Diagnostic Commands:**
```bash
# Check APISIX routes
curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     "$APISIX_ADMIN_URL/apisix/admin/routes" | \
     grep -o '"id":"openapi-[^"]*"'

# Test OpenAPI spec manually
curl -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
     "$OPENAPI_1_BASE_URL$OPENAPI_1_SPEC_PATH"
```

**Solutions:**
1. **Check ai-tokens.env syntax:**
   ```bash
   # Ensure no spaces around = signs
   OPENAPI_1_ENABLED=true  # ✅ Correct
   OPENAPI_1_ENABLED = true  # ❌ Wrong
   ```

2. **Verify OpenAPI spec accessibility:**
   ```bash
   # Test the parsing script
   python3 test-openapi-parsing.py "$OPENAPI_1_BASE_URL$OPENAPI_1_SPEC_PATH" "$OPENAPI_1_ID"
   ```

3. **Check APISIX readiness:**
   ```bash
   # Manually test APISIX admin API
   curl -H "X-API-KEY: $APISIX_ADMIN_KEY" "$APISIX_ADMIN_URL/apisix/admin/routes"
   ```

### Issue 2: "Authentication failures during spec fetch"

**Symptoms:**
- Setup shows SSL/authentication errors
- Spec fetch fails with 401/403 errors

**Solutions:**
1. **For Bearer Token Auth:**
   ```bash
   # Test token validity
   curl -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
        "$OPENAPI_1_BASE_URL$OPENAPI_1_SPEC_PATH"
   ```

2. **For SSL Certificate Issues:**
   ```bash
   # The setup script has SSL bypass built-in, but you can test manually
   curl -k -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
        "$OPENAPI_1_BASE_URL$OPENAPI_1_SPEC_PATH"
   ```

3. **For Corporate Proxy:**
   ```bash
   # Run the Zscaler certificate script if available
   ./get-zscaler-certs.sh
   ```

### Issue 3: "APISIX admin API not ready"

**Symptoms:**
- Setup fails with "APISIX admin API failed to become ready"
- Connection refused errors

**Solutions:**
1. **Check Docker containers:**
   ```bash
   docker ps | grep apisix
   docker logs apisix-apisix-1
   ```

2. **Verify APISIX configuration:**
   ```bash
   # Check if APISIX is listening on the right ports
   docker exec apisix-apisix-1 netstat -ln | grep 9180
   ```

3. **Restart APISIX:**
   ```bash
   docker restart apisix-apisix-1
   # Wait 30 seconds, then retry setup
   ```

### Issue 4: "Provider validation failures"

**Symptoms:**
- Setup reports provider validation errors
- Invalid configuration messages

**Solutions:**
1. **Check Provider ID format:**
   ```bash
   # Provider ID must be alphanumeric + hyphens only
   OPENAPI_1_ID=gsai-api-1  # ✅ Correct
   OPENAPI_1_ID="gsai api 1"  # ❌ Wrong (spaces)
   OPENAPI_1_ID=gsai_api_1  # ❌ Wrong (underscores)
   ```

2. **Validate URL format:**
   ```bash
   # Base URL must include protocol
   OPENAPI_1_BASE_URL=https://api.example.com  # ✅ Correct
   OPENAPI_1_BASE_URL=api.example.com  # ❌ Wrong (no protocol)
   ```

3. **Check spec path:**
   ```bash
   # Spec path must start with /
   OPENAPI_1_SPEC_PATH=/openapi.json  # ✅ Correct
   OPENAPI_1_SPEC_PATH=openapi.json  # ❌ Wrong (no leading /)
   ```

## Manual Setup Testing

### Test Individual Functions
```bash
# Source the script functions
source setup_macos.sh

# Load environment
source ai-tokens.env

# Test APISIX readiness
wait_for_apisix_admin_api

# Test provider validation
validate_openapi_provider 1 "$OPENAPI_1_ID" "$OPENAPI_1_NAME" \
  "$OPENAPI_1_BASE_URL" "$OPENAPI_1_SPEC_PATH" "$OPENAPI_1_AUTH_TYPE"

# Test spec fetching
mkdir -p /tmp/test_openapi
fetch_openapi_spec "$OPENAPI_1_BASE_URL" "$OPENAPI_1_SPEC_PATH" \
  "$OPENAPI_1_AUTH_TYPE" "$OPENAPI_1_AUTH_TOKEN" "" "" \
  "/tmp/test_openapi/spec.json"

# Test spec validation
validate_openapi_spec "/tmp/test_openapi/spec.json"

# Test endpoint parsing
parse_openapi_endpoints "/tmp/test_openapi/spec.json" \
  "$OPENAPI_1_ID" "/tmp/test_openapi/endpoints.json"
```

### Run Only OpenAPI Setup
```bash
# Source everything and run just OpenAPI setup
source ai-tokens.env
source setup_macos.sh
setup_openapi_routes
```

## Logs and Debugging

### Enable Detailed Logging
```bash
# Run setup with verbose output
set -x  # Enable bash debugging
./setup_macos.sh
set +x  # Disable bash debugging
```

### Check Container Logs
```bash
# APISIX logs
docker logs apisix-apisix-1 --tail 50

# ViolentUTF API logs
docker logs violentutf_api --tail 50

# Keycloak logs (if relevant)
docker logs keycloak-keycloak-1 --tail 50
```

### APISIX Route Inspection
```bash
# List all routes
curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     "$APISIX_ADMIN_URL/apisix/admin/routes" | jq .

# List only OpenAPI routes
curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     "$APISIX_ADMIN_URL/apisix/admin/routes" | \
     jq '.list[] | select(.value.id | startswith("openapi-"))'

# Check specific route
curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     "$APISIX_ADMIN_URL/apisix/admin/routes/openapi-gsai-api-1-XXXXXX"
```

## Expected Results

### Successful Setup
After successful OpenAPI setup, you should see:
1. **Setup output:**
   ```
   ✅ APISIX admin API is ready
   ✅ All 1 OpenAPI provider(s) passed validation
   ✅ Found X endpoints
   ✅ Successfully created: X routes
   ✅ Provider gsai-api-1 setup completed: X routes created
   ```

2. **APISIX routes:**
   ```bash
   curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" \
        "$APISIX_ADMIN_URL/apisix/admin/routes" | \
        grep "openapi-gsai-api-1"
   ```

3. **ViolentUTF UI:**
   - OpenAPI providers appear in generator configuration
   - Models/operations are discoverable
   - Can create generators with OpenAPI provider

### Testing Routes
```bash
# Test a created route
curl -H "X-API-KEY: $VIOLENTUTF_API_KEY" \
     "http://localhost:9080/ai/openapi/gsai-api-1/some-endpoint"
```

## Recovery Steps

### Clean State Recovery
```bash
# Clear all OpenAPI routes
source ai-tokens.env
source setup_macos.sh
clear_openapi_routes

# Restart setup
./setup_macos.sh
```

### Docker Reset (if needed)
```bash
# Nuclear option - restart all containers
docker restart apisix-apisix-1 keycloak-keycloak-1 violentutf_api

# Wait for services to be ready
./check_services.sh
```

## Getting Help

### Information to Collect
When reporting issues, include:
1. Output of `./debug-openapi-setup.sh`
2. Content of your `ai-tokens.env` (redact sensitive tokens)
3. Output of `./check_services.sh`
4. Any error messages from setup
5. APISIX logs: `docker logs apisix-apisix-1 --tail 50`

### Test Files Created
The fixes include these helpful test files:
- `test-openapi-fixes.sh` - Automated test suite
- `debug-openapi-setup.sh` - Interactive debugging
- `test-openapi-parsing.py` - Spec parsing validation
- This troubleshooting guide

### Configuration Reference
For your GSAi API configuration:
```bash
OPENAPI_ENABLED=true
OPENAPI_1_ENABLED=true
OPENAPI_1_ID=gsai-api-1                              # Must be alphanumeric + hyphens
OPENAPI_1_NAME="GSAi API Latest"                     # Display name
OPENAPI_1_BASE_URL=https://api.dev.gsai.mcaas.fcs.gsa.gov    # Must include https://
OPENAPI_1_SPEC_PATH=/openapi.json                   # Must start with /
OPENAPI_1_AUTH_TYPE=bearer                          # bearer, api_key, basic, or none
OPENAPI_1_AUTH_TOKEN=your_actual_token              # Your bearer token
```

This configuration should work with the implemented fixes.