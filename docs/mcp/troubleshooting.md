# ViolentUTF MCP Troubleshooting Guide

## Common Issues and Solutions

### Server Startup Issues

#### MCP Server Fails to Start

**Symptoms:**
- Server exits immediately on startup
- Error messages about missing configuration
- Import errors for MCP modules

**Diagnosis:**
```bash
# Check configuration
python -c "from app.mcp.config import mcp_settings; print(mcp_settings.dict())"

# Verify MCP dependencies
pip list | grep mcp

# Check environment variables
env | grep -E "(MCP_|KEYCLOAK_|APISIX_|JWT_)"
```

**Solutions:**

1. **Missing Dependencies:**
   ```bash
   pip install model-context-protocol
   pip install httpx pydantic-settings
   ```

2. **Configuration Issues:**
   ```bash
   # Set required environment variables
   export JWT_SECRET_KEY="your-secret-key-here"
   export KEYCLOAK_URL="http://keycloak:8080"
   export APISIX_BASE_URL="http://apisix-apisix-1:9080"
   ```

3. **Path Issues:**
   ```bash
   # Ensure APP_DATA_DIR exists and is writable
   mkdir -p /app/app_data/violentutf
   chmod 755 /app/app_data/violentutf
   ```

#### Docker Container Issues

**Symptoms:**
- Container exits with code 1
- Network connectivity issues
- Permission denied errors

**Diagnosis:**
```bash
# Check container logs
docker logs violentutf-api

# Verify network connectivity
docker exec violentutf-api ping keycloak
docker exec violentutf-api ping apisix-apisix-1

# Check file permissions
docker exec violentutf-api ls -la /app/app_data/
```

**Solutions:**

1. **Network Issues:**
   ```bash
   # Verify Docker network exists
   docker network ls | grep vutf-network

   # Recreate network if needed
   docker network create vutf-network
   ```

2. **Volume Mount Issues:**
   ```yaml
   # In docker-compose.yml
   services:
     violentutf-api:
       volumes:
         - ./app_data:/app/app_data:rw
         - ./logs:/app/logs:rw
   ```

### Authentication Problems

#### JWT Token Issues

**Symptoms:**
- "auth_token_missing" errors
- "auth_token_expired" errors
- Invalid signature errors

**Diagnosis:**
```bash
# Check JWT secret configuration
echo $JWT_SECRET_KEY | wc -c  # Should be 32+ characters

# Test token creation
python -c "
from app.mcp.auth import MCPAuthHandler
import asyncio
handler = MCPAuthHandler()
result = asyncio.run(handler.get_auth_headers())
print(result)
"

# Decode JWT token (for debugging)
python -c "
import jwt
token = 'your-token-here'
decoded = jwt.decode(token, options={'verify_signature': False})
print(decoded)
"
```

**Solutions:**

1. **Missing JWT Secret:**
   ```bash
   # Generate strong secret
   python -c "import secrets; print(secrets.token_hex(32))"
   export JWT_SECRET_KEY="generated-secret-here"
   ```

2. **Token Expiration:**
   ```bash
   # Increase token expiry time
   export ACCESS_TOKEN_EXPIRE_MINUTES=60
   ```

3. **Clock Skew Issues:**
   ```bash
   # Synchronize system time
   sudo ntpdate -s time.nist.gov
   ```

#### Keycloak Authentication Issues

**Symptoms:**
- Cannot connect to Keycloak
- OAuth flow failures
- Invalid redirect URI errors

**Diagnosis:**
```bash
# Test Keycloak connectivity
curl -I $KEYCLOAK_URL/auth/realms/$KEYCLOAK_REALM

# Check Keycloak client configuration
curl -X GET "$KEYCLOAK_URL/auth/admin/realms/$KEYCLOAK_REALM/clients" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Verify OAuth endpoints
curl "$KEYCLOAK_URL/auth/realms/$KEYCLOAK_REALM/.well-known/openid_configuration"
```

**Solutions:**

1. **Connection Issues:**
   ```bash
   # Check Keycloak is running
   docker ps | grep keycloak

   # Verify network connectivity
   docker exec violentutf-api nslookup keycloak
   ```

2. **Client Configuration:**
   ```bash
   # Update redirect URIs in Keycloak
   # Add: http://localhost:9080/mcp/oauth/callback
   ```

3. **Realm/Client Issues:**
   ```bash
   # Verify client exists and is enabled
   # Check client secret matches environment variable
   export KEYCLOAK_CLIENT_SECRET="correct-secret"
   ```

### APISIX Gateway Issues

#### Route Configuration Problems

**Symptoms:**
- 404 errors for MCP endpoints
- CORS issues with web clients
- Rate limiting triggering incorrectly

**Diagnosis:**
```bash
# Check APISIX routes
curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     "$APISIX_ADMIN_URL/apisix/admin/routes"

# Test MCP health endpoint
curl -v "http://localhost:9080/mcp/health"

# Check APISIX logs
docker logs apisix-apisix-1
```

**Solutions:**

1. **Missing Routes:**
   ```bash
   # Run route configuration script
   cd apisix && ./configure_mcp_routes.sh

   # Verify routes were created
   curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
        "$APISIX_ADMIN_URL/apisix/admin/routes" | jq '.list.list[] | .value'
   ```

2. **CORS Issues:**
   ```bash
   # Update CORS settings
   curl -X PATCH "$APISIX_ADMIN_URL/apisix/admin/routes/mcp-sse" \
     -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     -d '{
       "plugins": {
         "cors": {
           "allow_origins": "*",
           "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
           "allow_headers": "*",
           "allow_credentials": true
         }
       }
     }'
   ```

3. **Rate Limiting:**
   ```bash
   # Increase rate limits
   curl -X PATCH "$APISIX_ADMIN_URL/apisix/admin/routes/mcp-api" \
     -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     -d '{
       "plugins": {
         "rate-limit": {
           "count": 1000,
           "time_window": 60
         }
       }
     }'
   ```

#### Gateway Connectivity Issues

**Symptoms:**
- Connection refused errors
- Timeout errors
- Upstream server errors

**Diagnosis:**
```bash
# Check APISIX status
curl -i http://localhost:9080/apisix/status

# Verify upstream servers
curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     "$APISIX_ADMIN_URL/apisix/admin/upstreams"

# Test direct API connectivity
curl http://violentutf-api:8000/health
```

**Solutions:**

1. **APISIX Not Running:**
   ```bash
   # Restart APISIX
   docker-compose restart apisix-apisix-1

   # Check APISIX configuration
   docker exec apisix-apisix-1 apisix configtest
   ```

2. **Upstream Issues:**
   ```bash
   # Verify ViolentUTF API is healthy
   docker exec violentutf-api curl localhost:8000/health

   # Update upstream configuration
   curl -X PUT "$APISIX_ADMIN_URL/apisix/admin/upstreams/violentutf-api" \
     -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     -d '{
       "nodes": {
         "violentutf-api:8000": 1
       },
       "type": "roundrobin",
       "checks": {
         "active": {
           "http_path": "/health",
           "healthy": {
             "interval": 2,
             "successes": 1
           }
         }
       }
     }'
   ```

### Tool Execution Issues

#### Tool Not Found Errors

**Symptoms:**
- "tool_not_found" errors
- Empty tool list
- Tool discovery failures

**Diagnosis:**
```bash
# Check tool registry
python -c "
from app.mcp.tools import tool_registry
import asyncio

async def check_tools():
    await tool_registry.discover_tools()
    tools = await tool_registry.list_tools()
    print(f'Total tools: {len(tools)}')
    for tool in tools[:5]:
        print(f'  - {tool.name}')

asyncio.run(check_tools())
"

# Verify specialized tools
python -c "
from app.mcp.tools.generators import generator_tools
from app.mcp.tools.orchestrators import orchestrator_tools
print(f'Generator tools: {len(generator_tools.get_tools())}')
print(f'Orchestrator tools: {len(orchestrator_tools.get_tools())}')
"
```

**Solutions:**

1. **Tool Discovery Issues:**
   ```bash
   # Reinitialize tool registry
   python -c "
   from app.mcp.tools import tool_registry
   import asyncio
   asyncio.run(tool_registry.discover_tools())
   "
   ```

2. **Missing FastAPI App:**
   ```bash
   # Ensure FastAPI app is properly initialized
   # Check app mounting in main.py
   from app.mcp.server import mcp_server
   mcp_server.mount_to_app(app)
   ```

3. **Import Errors:**
   ```bash
   # Check for import issues
   python -c "
   try:
       from app.mcp.tools.generators import GeneratorConfigurationTools
       from app.mcp.tools.orchestrators import OrchestratorManagementTools
       print('✅ Tool imports successful')
   except Exception as e:
       print(f'❌ Import error: {e}')
   "
   ```

#### Tool Execution Failures

**Symptoms:**
- "execution_failed" errors
- Timeout errors
- API connectivity issues

**Diagnosis:**
```bash
# Test tool execution directly
python -c "
from app.mcp.tools.generators import generator_tools
import asyncio

async def test_tool():
    result = await generator_tools.execute_tool(
        'list_generators',
        {},
        {'token': 'test-token'}
    )
    print(result)

asyncio.run(test_tool())
"

# Check API connectivity
curl -H "Authorization: Bearer test-token" \
     http://localhost:8000/api/v1/generators
```

**Solutions:**

1. **Timeout Issues:**
   ```bash
   # Increase timeout settings
   export MCP_TOOL_TIMEOUT_SECONDS=120
   ```

2. **Authentication Issues:**
   ```bash
   # Verify API token
   python -c "
   from app.mcp.auth import MCPAuthHandler
   import asyncio

   async def test_auth():
       handler = MCPAuthHandler()
       headers = await handler.get_auth_headers()
       print('Auth headers:', headers)

   asyncio.run(test_auth())
   "
   ```

3. **API Server Issues:**
   ```bash
   # Check ViolentUTF API health
   curl http://localhost:8000/health

   # Verify API endpoints
   curl http://localhost:8000/api/v1/generators
   ```

### Resource Access Issues

#### Resource Not Found Errors

**Symptoms:**
- "resource_not_found" errors
- Invalid URI format errors
- Cache lookup failures

**Diagnosis:**
```bash
# Test resource manager
python -c "
from app.mcp.resources import resource_registry
import asyncio

async def test_resources():
    await resource_registry.initialize()
    resources = await resource_registry.list_resources()
    print(f'Available resources: {len(resources)}')
    for resource in resources[:3]:
        print(f'  - {resource.uri}: {resource.name}')

asyncio.run(test_resources())
"

# Check resource URI parsing
python -c "
from app.mcp.resources.manager import resource_manager

test_uris = [
    'violentutf://generator/test-id',
    'violentutf://dataset/test-dataset'
]

for uri in test_uris:
    try:
        resource_type, resource_id = resource_manager._parse_resource_uri(uri)
        print(f'✅ {uri} -> {resource_type}/{resource_id}')
    except Exception as e:
        print(f'❌ {uri} -> Error: {e}')
"
```

**Solutions:**

1. **Resource Manager Issues:**
   ```bash
   # Reinitialize resource manager
   python -c "
   from app.mcp.resources import resource_registry
   import asyncio
   asyncio.run(resource_registry.initialize())
   "
   ```

2. **Cache Issues:**
   ```bash
   # Clear resource cache
   python -c "
   from app.mcp.resources import resource_registry
   resource_registry.clear_cache()
   print('Cache cleared')
   "
   ```

3. **API Access Issues:**
   ```bash
   # Test API endpoints directly
   curl http://localhost:8000/api/v1/generators
   curl http://localhost:8000/api/v1/datasets
   curl http://localhost:8000/api/v1/orchestrators
   ```

#### Cache Performance Issues

**Symptoms:**
- Slow resource access
- Memory usage issues
- Cache miss errors

**Diagnosis:**
```bash
# Check cache statistics
python -c "
from app.mcp.resources import resource_registry
stats = resource_registry.get_cache_stats()
print('Cache stats:', stats)
"

# Monitor memory usage
ps aux | grep python
docker stats violentutf-api
```

**Solutions:**

1. **Cache Tuning:**
   ```bash
   # Adjust cache settings
   export MCP_RESOURCE_CACHE_TTL=600  # 10 minutes
   export MCP_RESOURCE_CACHE_SIZE=2000
   export MCP_RESOURCE_PREFETCH=true
   ```

2. **Memory Optimization:**
   ```bash
   # Reduce cache size if memory constrained
   export MCP_RESOURCE_CACHE_SIZE=500
   export MCP_RESOURCE_CACHE_MEMORY_LIMIT="256MB"
   ```

### Client Connection Issues

#### SSE Transport Problems

**Symptoms:**
- Connection failures from MCP clients
- EventSource errors in browser
- Transport timeout issues

**Diagnosis:**
```bash
# Test SSE endpoint directly
curl -H "Accept: text/event-stream" \
     -H "Cache-Control: no-cache" \
     "http://localhost:9080/mcp/sse"

# Check browser developer tools for EventSource errors
# Verify CORS headers
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: authorization" \
     -X OPTIONS \
     "http://localhost:9080/mcp/sse"
```

**Solutions:**

1. **CORS Configuration:**
   ```bash
   # Update CORS settings for SSE
   curl -X PATCH "$APISIX_ADMIN_URL/apisix/admin/routes/mcp-sse" \
     -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     -d '{
       "plugins": {
         "cors": {
           "allow_origins": "*",
           "allow_methods": "GET,POST,OPTIONS",
           "allow_headers": "authorization,content-type,cache-control",
           "allow_credentials": true,
           "expose_headers": "content-type"
         }
       }
     }'
   ```

2. **SSE Headers:**
   ```python
   # Verify SSE response headers
   response.headers["Content-Type"] = "text/event-stream"
   response.headers["Cache-Control"] = "no-cache"
   response.headers["Connection"] = "keep-alive"
   ```

#### OAuth Flow Issues

**Symptoms:**
- Redirect URI mismatch errors
- State parameter validation failures
- PKCE verification errors

**Diagnosis:**
```bash
# Test OAuth endpoints
curl "http://localhost:9080/mcp/oauth/authorize?client_id=test&redirect_uri=http://localhost:3000/callback&state=test123"

# Check OAuth configuration
curl "http://localhost:9080/mcp/oauth/.well-known/configuration"

# Verify Keycloak OAuth endpoints
curl "$KEYCLOAK_URL/auth/realms/$KEYCLOAK_REALM/.well-known/openid_configuration"
```

**Solutions:**

1. **Redirect URI Configuration:**
   ```bash
   # Add redirect URI to Keycloak client
   # Navigate to Keycloak Admin Console
   # Client Settings -> Valid Redirect URIs
   # Add: http://localhost:3000/auth/callback
   ```

2. **State Parameter Issues:**
   ```python
   # Ensure state parameter is properly handled
   import secrets
   state = secrets.token_urlsafe(32)
   ```

3. **PKCE Configuration:**
   ```python
   # Verify PKCE implementation
   import hashlib
   import base64
   import secrets

   code_verifier = secrets.token_urlsafe(32)
   code_challenge = base64.urlsafe_b64encode(
       hashlib.sha256(code_verifier.encode()).digest()
   ).decode().rstrip('=')
   ```

## Performance Troubleshooting

### High Memory Usage

**Symptoms:**
- Out of memory errors
- Slow response times
- Container restarts

**Diagnosis:**
```bash
# Monitor memory usage
docker stats violentutf-api

# Check Python memory usage
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"

# Profile memory usage
pip install memory-profiler
python -m memory_profiler your_script.py
```

**Solutions:**

1. **Cache Optimization:**
   ```bash
   # Reduce cache sizes
   export MCP_RESOURCE_CACHE_SIZE=500
   export MCP_RESOURCE_CACHE_MEMORY_LIMIT="256MB"
   ```

2. **Garbage Collection:**
   ```python
   # Force garbage collection
   import gc
   gc.collect()
   ```

3. **Container Limits:**
   ```yaml
   # In docker-compose.yml
   services:
     violentutf-api:
       deploy:
         resources:
           limits:
             memory: 2G
           reservations:
             memory: 1G
   ```

### High CPU Usage

**Symptoms:**
- Slow response times
- High system load
- Timeout errors

**Diagnosis:**
```bash
# Monitor CPU usage
top -p $(pgrep -f "python.*mcp")

# Profile CPU usage
python -m cProfile -s cumulative your_script.py

# Check for CPU-intensive operations
htop
```

**Solutions:**

1. **Concurrency Limits:**
   ```bash
   # Reduce concurrent operations
   export MCP_CONCURRENT_TOOL_LIMIT=5
   export MCP_TOOL_WORKER_THREADS=2
   ```

2. **Algorithm Optimization:**
   ```python
   # Use more efficient algorithms
   # Optimize database queries
   # Implement caching for expensive operations
   ```

### Database Performance Issues

**Symptoms:**
- Slow query responses
- Connection pool exhaustion
- Database lock timeouts

**Diagnosis:**
```bash
# Check database connections
python -c "
from app.database import engine
print(f'Pool size: {engine.pool.size()}')
print(f'Checked in: {engine.pool.checkedin()}')
print(f'Checked out: {engine.pool.checkedout()}')
"

# Monitor database performance
# For SQLite
sqlite3 your_database.db ".schema"

# Check slow queries
# Enable query logging in database configuration
```

**Solutions:**

1. **Connection Pool Tuning:**
   ```bash
   # Increase pool size
   export MCP_DB_POOL_SIZE=30
   export MCP_DB_MAX_OVERFLOW=50
   ```

2. **Query Optimization:**
   ```python
   # Add database indexes
   # Optimize queries with EXPLAIN
   # Use query result caching
   ```

## Debugging Tools and Scripts

### Health Check Script

Create `scripts/health-check.sh`:

```bash
#!/bin/bash
set -e

echo "🔍 ViolentUTF MCP Health Check"
echo "================================"

# Check MCP server health
echo "Checking MCP server health..."
if curl -f -s http://localhost:9080/mcp/health > /dev/null; then
    echo "✅ MCP server is healthy"
else
    echo "❌ MCP server health check failed"
    exit 1
fi

# Check tool availability
echo "Checking tool availability..."
TOOL_COUNT=$(python -c "
from app.mcp.tools import tool_registry
import asyncio

async def count_tools():
    await tool_registry.discover_tools()
    tools = await tool_registry.list_tools()
    return len(tools)

print(asyncio.run(count_tools()))
" 2>/dev/null || echo "0")

if [ "$TOOL_COUNT" -gt 0 ]; then
    echo "✅ $TOOL_COUNT tools available"
else
    echo "❌ No tools available"
    exit 1
fi

# Check resource access
echo "Checking resource access..."
RESOURCE_COUNT=$(python -c "
from app.mcp.resources import resource_registry
import asyncio

async def count_resources():
    await resource_registry.initialize()
    resources = await resource_registry.list_resources()
    return len(resources)

try:
    print(asyncio.run(count_resources()))
except:
    print('0')
" 2>/dev/null)

echo "✅ $RESOURCE_COUNT resources accessible"

# Check authentication
echo "Checking authentication..."
if python -c "
from app.mcp.auth import MCPAuthHandler
import asyncio

async def test_auth():
    handler = MCPAuthHandler()
    headers = await handler.get_auth_headers()
    return len(headers) > 0

try:
    result = asyncio.run(test_auth())
    exit(0 if result else 1)
except:
    exit(1)
" 2>/dev/null; then
    echo "✅ Authentication working"
else
    echo "⚠️  Authentication may have issues"
fi

echo "🎉 Health check completed successfully"
```

### Diagnostic Script

Create `scripts/diagnose.py`:

```python
#!/usr/bin/env python3
"""MCP Diagnostic Script"""

import asyncio
import os
import sys
from typing import Dict, Any

async def diagnose_mcp() -> Dict[str, Any]:
    """Run comprehensive MCP diagnostics"""
    results = {
        "environment": {},
        "configuration": {},
        "tools": {},
        "resources": {},
        "authentication": {},
        "connectivity": {}
    }

    # Environment checks
    env_vars = [
        "MCP_SERVER_NAME", "JWT_SECRET_KEY", "KEYCLOAK_URL",
        "APISIX_BASE_URL", "VIOLENTUTF_API_URL"
    ]

    for var in env_vars:
        results["environment"][var] = {
            "set": bool(os.getenv(var)),
            "value": os.getenv(var, "")[:20] + "..." if os.getenv(var) else None
        }

    # Configuration checks
    try:
        from app.mcp.config import mcp_settings
        results["configuration"]["valid"] = True
        results["configuration"]["settings"] = {
            "server_name": mcp_settings.MCP_SERVER_NAME,
            "tools_enabled": mcp_settings.MCP_ENABLE_TOOLS,
            "resources_enabled": mcp_settings.MCP_ENABLE_RESOURCES,
            "transport_type": mcp_settings.MCP_TRANSPORT_TYPE
        }
    except Exception as e:
        results["configuration"]["valid"] = False
        results["configuration"]["error"] = str(e)

    # Tool checks
    try:
        from app.mcp.tools import tool_registry
        await tool_registry.discover_tools()
        tools = await tool_registry.list_tools()

        results["tools"]["discovered"] = True
        results["tools"]["count"] = len(tools)
        results["tools"]["sample_tools"] = [tool.name for tool in tools[:5]]
    except Exception as e:
        results["tools"]["discovered"] = False
        results["tools"]["error"] = str(e)

    # Resource checks
    try:
        from app.mcp.resources import resource_registry
        await resource_registry.initialize()
        resources = await resource_registry.list_resources()

        results["resources"]["accessible"] = True
        results["resources"]["count"] = len(resources)
        results["resources"]["cache_stats"] = resource_registry.get_cache_stats()
    except Exception as e:
        results["resources"]["accessible"] = False
        results["resources"]["error"] = str(e)

    # Authentication checks
    try:
        from app.mcp.auth import MCPAuthHandler
        handler = MCPAuthHandler()
        headers = await handler.get_auth_headers()

        results["authentication"]["working"] = True
        results["authentication"]["headers_count"] = len(headers)
    except Exception as e:
        results["authentication"]["working"] = False
        results["authentication"]["error"] = str(e)

    return results

def print_results(results: Dict[str, Any]):
    """Print diagnostic results in a readable format"""
    print("🔍 ViolentUTF MCP Diagnostic Report")
    print("=" * 50)

    for category, data in results.items():
        print(f"\n📋 {category.upper()}:")

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, bool):
                    status = "✅" if value else "❌"
                    print(f"  {status} {key}")
                else:
                    print(f"    {key}: {value}")
        else:
            print(f"    {data}")

if __name__ == "__main__":
    try:
        results = asyncio.run(diagnose_mcp())
        print_results(results)

        # Determine overall health
        critical_issues = [
            not results["configuration"].get("valid", False),
            not results["tools"].get("discovered", False),
            not results["authentication"].get("working", False)
        ]

        if any(critical_issues):
            print("\n❌ Critical issues detected")
            sys.exit(1)
        else:
            print("\n✅ System appears healthy")
            sys.exit(0)

    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        sys.exit(1)
```

### Log Analysis Script

Create `scripts/analyze-logs.py`:

```python
#!/usr/bin/env python3
"""MCP Log Analysis Script"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List

def analyze_mcp_logs(log_file: str) -> Dict:
    """Analyze MCP server logs for patterns and issues"""

    analysis = {
        "total_lines": 0,
        "error_count": 0,
        "warning_count": 0,
        "tool_executions": Counter(),
        "resource_accesses": Counter(),
        "auth_failures": 0,
        "performance_issues": [],
        "common_errors": Counter()
    }

    with open(log_file, 'r') as f:
        for line in f:
            analysis["total_lines"] += 1

            try:
                # Try to parse as JSON log
                log_entry = json.loads(line.strip())
                level = log_entry.get("level", "").upper()
                message = log_entry.get("message", "")

            except json.JSONDecodeError:
                # Fall back to text parsing
                if "ERROR" in line:
                    level = "ERROR"
                elif "WARNING" in line:
                    level = "WARNING"
                else:
                    level = "INFO"
                message = line.strip()

            # Count log levels
            if level == "ERROR":
                analysis["error_count"] += 1
                analysis["common_errors"][message[:100]] += 1
            elif level == "WARNING":
                analysis["warning_count"] += 1

            # Track tool executions
            if "Executing tool:" in message:
                tool_match = re.search(r"Executing tool: (\w+)", message)
                if tool_match:
                    analysis["tool_executions"][tool_match.group(1)] += 1

            # Track resource accesses
            if "Reading resource:" in message:
                resource_match = re.search(r"violentutf://(\w+)/", message)
                if resource_match:
                    analysis["resource_accesses"][resource_match.group(1)] += 1

            # Track authentication failures
            if "auth" in message.lower() and ("fail" in message.lower() or "error" in message.lower()):
                analysis["auth_failures"] += 1

            # Track performance issues
            if "timeout" in message.lower() or "slow" in message.lower():
                analysis["performance_issues"].append(message[:200])

    return analysis

def print_analysis(analysis: Dict):
    """Print log analysis results"""
    print("📊 MCP Log Analysis Report")
    print("=" * 40)

    print(f"Total log lines: {analysis['total_lines']}")
    print(f"Errors: {analysis['error_count']}")
    print(f"Warnings: {analysis['warning_count']}")
    print(f"Auth failures: {analysis['auth_failures']}")

    print(f"\n🔧 Top Tool Executions:")
    for tool, count in analysis['tool_executions'].most_common(5):
        print(f"  {tool}: {count}")

    print(f"\n📊 Resource Access Patterns:")
    for resource_type, count in analysis['resource_accesses'].most_common(5):
        print(f"  {resource_type}: {count}")

    if analysis['common_errors']:
        print(f"\n❌ Common Errors:")
        for error, count in analysis['common_errors'].most_common(3):
            print(f"  {count}x: {error}")

    if analysis['performance_issues']:
        print(f"\n⚠️  Performance Issues:")
        for issue in analysis['performance_issues'][:3]:
            print(f"  {issue}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python analyze-logs.py <log_file>")
        sys.exit(1)

    log_file = sys.argv[1]
    try:
        analysis = analyze_mcp_logs(log_file)
        print_analysis(analysis)
    except FileNotFoundError:
        print(f"❌ Log file not found: {log_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)
```

## Getting Help

### Log Collection

When reporting issues, collect these logs:

```bash
# MCP Server logs
docker logs violentutf-api > mcp-server.log

# APISIX logs
docker logs apisix-apisix-1 > apisix.log

# Keycloak logs
docker logs keycloak > keycloak.log

# System information
docker ps > docker-status.log
docker network ls > networks.log
```

### Issue Reporting Template

When reporting issues, include:

1. **Environment Information:**
   - OS and version
   - Docker and Docker Compose versions
   - ViolentUTF version

2. **Configuration:**
   - Relevant environment variables (sanitized)
   - Docker Compose configuration
   - APISIX route configuration

3. **Steps to Reproduce:**
   - Exact commands or actions
   - Expected vs actual behavior
   - Error messages and logs

4. **Diagnostic Output:**
   - Health check results
   - Diagnostic script output
   - Relevant log excerpts

### Community Resources

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Comprehensive guides and references
- **Discord/Slack**: Community discussions and support

---

*For more configuration options, see [Configuration Guide](./configuration.md).*
*For API usage details, see [API Reference](./api-reference.md).*
