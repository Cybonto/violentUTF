# MCP Connection Troubleshooting

## Overview

This guide helps diagnose and resolve common MCP connection issues in ViolentUTF. Follow these steps systematically to identify and fix problems.

## Quick Diagnostics

### 1. Check Service Status

```bash
# Check if MCP server is running
curl -X GET http://localhost:9080/health

# Check APISIX gateway status  
curl -X GET http://localhost:9080/apisix/admin/routes \
  -H "X-API-KEY: your-admin-key"

# Check ViolentUTF API
curl -X GET http://localhost:9080/api/v1/health
```

### 2. Test MCP Endpoint

```bash
# Test MCP SSE endpoint directly
curl -N -X POST http://localhost:9080/mcp/sse/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-API-Gateway: APISIX" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'
```

### 3. Verify Authentication

```python
from violentutf.utils.jwt_manager import jwt_manager

# Check JWT token availability
token = jwt_manager.get_valid_token()
if not token:
    print("No JWT token available")
else:
    print(f"Token available: {token[:20]}...")
```

## Common Issues and Solutions

### Issue: "Connection refused" or "Failed to connect to MCP server"

**Symptoms:**
- MCPConnectionError exceptions
- Client initialization returns False
- Health check fails

**Diagnosis:**
```python
import requests

# Test base connectivity
try:
    response = requests.get("http://localhost:9080/health", timeout=5)
    print(f"Gateway status: {response.status_code}")
except Exception as e:
    print(f"Gateway unreachable: {e}")
```

**Solutions:**
1. Verify services are running:
   ```bash
   docker-compose ps
   # Should show violentutf-api, apisix, keycloak as "Up"
   ```

2. Check APISIX routes configured:
   ```bash
   cd apisix && ./configure_routes.sh
   ```

3. Verify network connectivity:
   ```bash
   # Check if services can communicate
   docker network inspect vutf-network
   ```

4. Check environment variables:
   ```bash
   echo $VIOLENTUTF_API_URL
   # Should be http://localhost:9080 (not :8000)
   ```

### Issue: "Authentication failed" or 401 Unauthorized

**Symptoms:**
- MCPAuthenticationError
- "No authentication token provided" errors
- API returns 401 status

**Diagnosis:**
```python
# Check authentication setup
import os

print("Keycloak token:", bool(st.session_state.get('access_token')))
print("Environment auth:", bool(os.getenv('KEYCLOAK_USERNAME')))
print("JWT secret:", bool(os.getenv('JWT_SECRET_KEY')))
```

**Solutions:**
1. Set environment credentials:
   ```bash
   export KEYCLOAK_USERNAME=your_username
   export KEYCLOAK_PASSWORD=your_password
   export JWT_SECRET_KEY=your_secret_key
   ```

2. Ensure JWT secret matches API:
   ```bash
   # In violentutf/.env and violentutf_api/.env
   JWT_SECRET_KEY=same_secret_key_value
   ```

3. Refresh authentication:
   ```python
   from utils.jwt_manager import jwt_manager
   
   # Force token refresh
   jwt_manager.access_token = None
   new_token = jwt_manager.get_valid_token()
   ```

### Issue: "Direct access not allowed. Use the API gateway"

**Symptoms:**
- API rejects requests
- "Missing X-API-Gateway header" errors

**Diagnosis:**
```python
# Check if using correct URL
client = MCPClientSync()
print(f"Base URL: {client.client.base_url}")
print(f"MCP endpoint: {client.client.mcp_endpoint}")
# Should use port 9080, not 8000
```

**Solutions:**
1. Use APISIX gateway URL:
   ```python
   # Correct
   client = MCPClientSync(base_url="http://localhost:9080")
   
   # Wrong - direct API access
   # client = MCPClientSync(base_url="http://localhost:8000")
   ```

2. Verify headers include gateway marker:
   ```python
   headers = client.client._get_auth_headers()
   assert headers.get("X-API-Gateway") == "APISIX"
   ```

### Issue: "SSE connection terminated unexpectedly"

**Symptoms:**
- Partial responses
- "Connection reset by peer"
- Incomplete JSON-RPC messages

**Diagnosis:**
```python
# Test SSE stream directly
import httpx

async def test_sse_stream():
    headers = {
        "Authorization": f"Bearer {jwt_manager.get_valid_token()}",
        "X-API-Gateway": "APISIX"
    }
    
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:9080/mcp/sse/",
            json={"jsonrpc":"2.0","method":"initialize","params":{},"id":1},
            headers=headers
        ) as response:
            async for line in response.aiter_lines():
                print(f"SSE: {line}")
```

**Solutions:**
1. Increase timeout:
   ```python
   client = MCPClientSync(timeout=60.0)  # 60 second timeout
   ```

2. Check APISIX proxy settings:
   ```yaml
   # In apisix/conf/config.yaml
   nginx_config:
     http:
       proxy_read_timeout: 300s
       proxy_send_timeout: 300s
   ```

3. Verify SSE support:
   ```bash
   # Check APISIX error logs
   docker logs apisix 2>&1 | grep -i "sse\|stream"
   ```

### Issue: "Tool not found" or empty tool list

**Symptoms:**
- `list_tools()` returns empty list
- Tool execution fails with "not found"
- No API endpoints discovered

**Diagnosis:**
```python
# Check MCP introspection
client = MCPClientSync()
client.initialize()

# List available tools
tools = client.list_tools()
print(f"Found {len(tools)} tools")

# Check specific endpoints
for tool in tools[:5]:
    print(f"- {tool['name']}: {tool.get('description', 'No description')}")
```

**Solutions:**
1. Verify API endpoints exist:
   ```bash
   # Check API docs
   curl http://localhost:9080/docs
   ```

2. Check introspection patterns:
   ```python
   # In violentutf_api/mcp/tools/introspection.py
   INCLUDE_PATTERNS = [
       r"^/api/v1/orchestrators",
       r"^/api/v1/generators",
       # Add missing patterns
   ]
   ```

3. Restart services:
   ```bash
   docker-compose restart violentutf-api
   ```

## Advanced Debugging

### Enable Debug Logging

```python
import logging

# Enable debug for MCP client
logging.getLogger('violentutf.utils.mcp_client').setLevel(logging.DEBUG)

# Enable debug for httpx (network requests)
logging.getLogger('httpx').setLevel(logging.DEBUG)

# Enable debug for JWT manager
logging.getLogger('violentutf.utils.jwt_manager').setLevel(logging.DEBUG)
```

### Trace Network Requests

```python
import httpx

# Create client with event hooks
def log_request(request):
    print(f"Request: {request.method} {request.url}")
    print(f"Headers: {dict(request.headers)}")

def log_response(response):
    print(f"Response: {response.status_code}")
    
client = httpx.Client(
    event_hooks={'request': [log_request], 'response': [log_response]}
)
```

### Check JWT Token Contents

```python
import jwt
import json

token = jwt_manager.get_valid_token()
if token:
    # Decode without verification to inspect
    decoded = jwt.decode(token, options={"verify_signature": False})
    print(json.dumps(decoded, indent=2))
    
    # Check expiration
    import time
    exp = decoded.get('exp', 0)
    remaining = exp - time.time()
    print(f"Token expires in: {remaining/60:.1f} minutes")
```

### Monitor SSE Events

```python
class SSEDebugger:
    """Debug SSE event stream"""
    
    def __init__(self):
        self.events = []
        
    async def debug_sse_stream(self, client, method, params=None):
        """Capture and analyze SSE events"""
        headers = client._get_auth_headers()
        
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": 1
        }
        
        async with httpx.AsyncClient() as http_client:
            async with http_client.stream(
                "POST",
                client.mcp_endpoint,
                json=request_data,
                headers=headers,
                timeout=30.0
            ) as response:
                print(f"Response status: {response.status_code}")
                
                async for line in response.aiter_lines():
                    if line:
                        print(f"SSE Line: {line}")
                        self.events.append(line)
                        
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                print(f"Parsed data: {data}")
                            except json.JSONDecodeError as e:
                                print(f"JSON parse error: {e}")
```

## Environment Verification Script

Create a diagnostic script `check_mcp_setup.py`:

```python
#!/usr/bin/env python3
"""MCP Setup Diagnostic Script"""

import os
import sys
import requests
import json
from datetime import datetime

def check_environment():
    """Check environment variables"""
    print("=== Environment Variables ===")
    required_vars = [
        "VIOLENTUTF_API_URL",
        "KEYCLOAK_USERNAME",
        "JWT_SECRET_KEY",
        "APISIX_API_KEY"
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        status = "✓" if value else "✗"
        display_value = value[:20] + "..." if value and len(value) > 20 else value
        print(f"{status} {var}: {display_value or 'NOT SET'}")
    
def check_services():
    """Check service connectivity"""
    print("\n=== Service Status ===")
    
    services = [
        ("APISIX Gateway", "http://localhost:9080/health"),
        ("ViolentUTF API", "http://localhost:9080/api/v1/health"),
        ("Keycloak", "http://localhost:8080/health"),
    ]
    
    for name, url in services:
        try:
            response = requests.get(url, timeout=5)
            status = "✓" if response.status_code == 200 else "!"
            print(f"{status} {name}: {response.status_code}")
        except Exception as e:
            print(f"✗ {name}: {type(e).__name__}")
            
def check_mcp_connection():
    """Check MCP specific endpoints"""
    print("\n=== MCP Connection ===")
    
    try:
        from violentutf.utils.jwt_manager import jwt_manager
        token = jwt_manager.get_valid_token()
        
        if token:
            print("✓ JWT token available")
            
            # Test MCP endpoint
            headers = {
                "Authorization": f"Bearer {token}",
                "X-API-Gateway": "APISIX",
                "Content-Type": "application/json"
            }
            
            # Test health through MCP
            response = requests.post(
                "http://localhost:9080/mcp/sse/",
                headers=headers,
                json={"jsonrpc":"2.0","method":"initialize","params":{},"id":1},
                timeout=10
            )
            
            if response.status_code == 200:
                print("✓ MCP endpoint accessible")
            else:
                print(f"! MCP endpoint returned: {response.status_code}")
        else:
            print("✗ No JWT token available")
            
    except Exception as e:
        print(f"✗ MCP check failed: {e}")

if __name__ == "__main__":
    print(f"MCP Diagnostic Report - {datetime.now()}")
    print("=" * 50)
    
    check_environment()
    check_services()
    check_mcp_connection()
    
    print("\n" + "=" * 50)
    print("Run with DEBUG=1 for verbose output")
```

## Getting Help

If you're still experiencing issues:

1. **Check Logs**:
   ```bash
   # APISIX logs
   docker logs apisix --tail 100
   
   # API logs
   docker logs violentutf-api --tail 100
   ```

2. **Create Minimal Reproduction**:
   ```python
   # Save as test_mcp_minimal.py
   from violentutf.utils.mcp_client import MCPClientSync
   
   client = MCPClientSync()
   print(f"Initializing: {client.initialize()}")
   print(f"Health check: {client.health_check()}")
   ```

3. **Report Issue** with:
   - Diagnostic script output
   - Error messages and stack traces
   - Environment details (OS, Python version)
   - Docker compose status

## Related Documentation

- [MCP Client API Reference](../api/mcp-client.md)
- [Integration Guide](../guides/mcp-integration.md)
- [Testing Guide](../guides/testing-mcp.md)
- [Authentication Guide](../../violentutf_api_keymanagement.md)