# APISIX Gateway Configuration Guide

Complete documentation for configuring and managing the APISIX Gateway that protects and routes the ViolentUTF API. This guide covers setup, security, routing, and troubleshooting.

## 🏗️ Gateway Architecture

APISIX serves as the **single entry point** for all ViolentUTF API requests, providing security, routing, and management capabilities:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │───▶│   APISIX        │───▶│   FastAPI       │
│  (Streamlit,    │    │   Gateway       │    │   Service       │
│   CLI, SDK)     │    │   Port: 9080    │    │   Port: 8000    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │                      │
                               ▼                      ▼
                        ┌─────────────────┐    ┌─────────────────┐
                        │   Keycloak      │    │   PyRIT/Garak   │
                        │   (Auth)        │    │   Frameworks    │
                        │   Port: 8080    │    │                 │
                        └─────────────────┘    └─────────────────┘
```

## 🎯 Core Functions

### 1. Security Gateway
- **Blocks direct FastAPI access** - All requests must go through APISIX
- **Authentication validation** - JWT tokens and API keys
- **Rate limiting** - Configurable request throttling
- **CORS management** - Cross-origin request handling

### 2. API Routing
- **Intelligent routing** - Path-based endpoint routing
- **Load balancing** - Multiple backend support
- **Request transformation** - Header injection and modification
- **Response processing** - Status code management

### 3. Monitoring & Management
- **Real-time metrics** - Prometheus integration
- **Health monitoring** - Service status tracking
- **Dashboard access** - Web-based management
- **Logging** - Comprehensive request logging

## 🚀 Quick Setup

### Prerequisites
- Docker and Docker Compose
- APISIX configuration templates
- Network connectivity to FastAPI service

### 1. Start APISIX Stack
```bash
cd apisix
docker compose up -d
```

### 2. Configure Routes
```bash
./configure_routes.sh
```

### 3. Start ViolentUTF API
```bash
cd ../violentutf_api  
docker compose up -d
```

### 4. Verify Setup
```bash
cd ../apisix
./verify_routes.sh
```

## 📋 Configuration Scripts

### `configure_routes.sh`
Configures all necessary APISIX routes for the ViolentUTF API.

**What it does:**
- Creates upstream pointing to FastAPI service
- Configures routes for all API endpoints
- Sets up CORS and proxy headers
- Enables authentication passthrough

**Usage:**
```bash
cd apisix
./configure_routes.sh
```

**Key Routes Configured:**

| Route ID | Path | Methods | Description |
|----------|------|---------|-------------|
| 1001 | `/health` | GET | Health check (no auth) |
| 1002 | `/docs*` | GET | FastAPI documentation |
| 1003 | `/openapi.json` | GET | OpenAPI schema |
| 1004 | `/redoc*` | GET | ReDoc documentation |
| 2001 | `/api/v1/auth/*` | ALL | Authentication endpoints |
| 2002 | `/api/v1/database/*` | ALL | Database management |
| 2003 | `/api/v1/sessions*` | ALL | Session management |
| 2004 | `/api/v1/config/*` | ALL | Configuration management |
| 2005 | `/api/v1/files*` | ALL | File management |
| 2006 | `/api/v1/keys/*` | ALL | JWT key management |
| 2007 | `/api/v1/test/*` | ALL | Test endpoints |

### `verify_routes.sh`
Verifies that routes are properly configured and working.

**What it checks:**
- APISIX gateway connectivity
- Route configuration status
- Health endpoint accessibility
- API documentation access
- Protected endpoint behavior

**Usage:**
```bash
cd apisix
./verify_routes.sh
```

**Expected Output:**
```
✅ APISIX Gateway: Responding
✅ Health Endpoint: Accessible
✅ API Documentation: Accessible
✅ Protected Endpoints: Require Authentication
✅ All routes configured successfully
```

### `remove_routes.sh`
Removes all ViolentUTF API routes from APISIX.

**What it does:**
- Deletes all configured routes
- Removes upstream configuration
- Provides clean slate for reconfiguration

**Usage:**
```bash
cd apisix
./remove_routes.sh
```

## 🔧 Detailed Configuration

### Route Configuration Structure

Each route follows this pattern:

```json
{
  "id": "route_id",
  "uri": "/api/v1/endpoint/*",
  "methods": ["GET", "POST", "PUT", "DELETE"],
  "upstream": {
    "nodes": {
      "fastapi:8000": 1
    },
    "type": "roundrobin",
    "scheme": "http"
  },
  "plugins": {
    "cors": {
      "allow_origins": "*",
      "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
      "allow_headers": "*"
    },
    "proxy-rewrite": {
      "headers": {
        "X-Real-IP": "$remote_addr",
        "X-Forwarded-For": "$proxy_add_x_forwarded_for",
        "X-Forwarded-Host": "$host",
        "X-API-Gateway": "APISIX"
      }
    }
  }
}
```

### Upstream Configuration

The FastAPI upstream is configured as:

```json
{
  "id": "violentutf-api",
  "nodes": {
    "fastapi:8000": 1
  },
  "type": "roundrobin",
  "scheme": "http",
  "timeout": {
    "connect": 6,
    "send": 60,
    "read": 60
  },
  "keepalive_pool": {
    "size": 320,
    "idle_timeout": 60,
    "requests": 1000
  }
}
```

## 🔒 Security Configuration

### CORS Settings
```json
{
  "cors": {
    "allow_origins": "*",
    "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
    "allow_headers": "Authorization,Content-Type,X-API-Key,X-Real-IP,X-Forwarded-For,X-API-Gateway",
    "expose_headers": "X-RateLimit-Limit,X-RateLimit-Remaining",
    "max_age": 86400,
    "allow_credentials": true
  }
}
```

### Proxy Headers
APISIX automatically adds these headers to all requests:

```
X-Real-IP: 192.168.1.100
X-Forwarded-For: 192.168.1.100
X-Forwarded-Host: localhost:9080
X-API-Gateway: APISIX
```

**Security Note**: The `X-API-Gateway: APISIX` header is critical for FastAPI to accept requests.

### Rate Limiting
Rate limiting is configured at the APISIX level:

```json
{
  "limit-req": {
    "rate": 100,
    "burst": 50,
    "rejected_code": 429,
    "nodelay": false
  },
  "limit-count": {
    "count": 1000,
    "time_window": 3600,
    "rejected_code": 429
  }
}
```

## 🌐 Network Configuration

### Docker Network
All services communicate through the `vutf-network`:

```yaml
networks:
  vutf-network:
    external: true
  apisix_network:
    driver: bridge
```

### Service URLs

**External (Client Access):**
- APISIX Gateway: http://localhost:9080
- APISIX Admin: http://localhost:9180
- APISIX Dashboard: http://localhost:9001

**Internal (Container Network):**
- FastAPI Service: http://fastapi:8000
- Keycloak: http://keycloak:8080
- etcd: http://etcd:2379

### Port Mapping

| Service | External Port | Internal Port | Description |
|---------|--------------|---------------|-------------|
| APISIX Gateway | 9080 | 9080 | API requests |
| APISIX Admin | 9180 | 9180 | Admin API |
| APISIX Dashboard | 9001 | 9000 | Web interface |
| Prometheus | 9091 | 9091 | Metrics |
| Grafana | 3000 | 3000 | Monitoring |

## 📊 Monitoring & Observability

### Prometheus Metrics
APISIX exports comprehensive metrics:

**Endpoint**: http://localhost:9091/apisix/prometheus/metrics

**Key Metrics:**
- `apisix_http_requests_total` - Total HTTP requests
- `apisix_http_request_duration_seconds` - Request duration
- `apisix_upstream_status` - Upstream health status
- `apisix_bandwidth` - Network bandwidth usage

### Grafana Dashboard
Pre-configured Grafana dashboard available at http://localhost:3000

**Default Login:**
- Username: admin
- Password: admin

**Key Dashboards:**
- APISIX Overview
- Request Performance
- Error Rate Analysis
- Upstream Health

### Health Monitoring

**APISIX Health Check:**
```bash
curl http://localhost:9080/health
```

**Admin API Health:**
```bash
curl http://localhost:9180/apisix/admin/routes \
  -H "X-API-KEY: $APISIX_ADMIN_KEY"
```

**Upstream Status:**
```bash
curl http://localhost:9180/apisix/admin/upstreams/violentutf-api \
  -H "X-API-KEY: $APISIX_ADMIN_KEY"
```

## 🔧 Advanced Configuration

### Custom Route Creation

To add new routes manually:

```bash
# Create route
curl -X PUT http://localhost:9180/apisix/admin/routes/custom-route \
  -H "X-API-KEY: $APISIX_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "/api/v1/custom/*",
    "methods": ["GET", "POST"],
    "upstream": {
      "nodes": {"fastapi:8000": 1}
    },
    "plugins": {
      "cors": {},
      "proxy-rewrite": {
        "headers": {
          "X-API-Gateway": "APISIX"
        }
      }
    }
  }'
```

### SSL/TLS Configuration

For production HTTPS setup:

```json
{
  "ssl": {
    "cert": "path/to/certificate.crt",
    "key": "path/to/private.key",
    "sni": "api.violentutf.com"
  }
}
```

### Load Balancing

For multiple FastAPI instances:

```json
{
  "upstream": {
    "nodes": {
      "fastapi1:8000": 1,
      "fastapi2:8000": 1,
      "fastapi3:8000": 1
    },
    "type": "roundrobin"
  }
}
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Routes Not Accessible (404 Errors)

**Symptoms:**
```bash
curl http://localhost:9080/api/v1/auth/me
# Returns: 404 Not Found
```

**Diagnosis:**
```bash
# Check if routes are configured
./verify_routes.sh

# List all routes
curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     http://localhost:9180/apisix/admin/routes
```

**Solution:**
```bash
# Reconfigure routes
./remove_routes.sh
./configure_routes.sh
```

#### 2. Gateway Errors (502/503)

**Symptoms:**
```bash
curl http://localhost:9080/health
# Returns: 502 Bad Gateway or 503 Service Unavailable
```

**Diagnosis:**
```bash
# Check FastAPI service status
cd ../violentutf_api
docker compose ps

# Check APISIX logs
cd ../apisix
docker compose logs apisix
```

**Solution:**
```bash
# Restart FastAPI service
cd ../violentutf_api
docker compose restart fastapi

# Or restart entire APISIX stack
cd ../apisix
docker compose restart
```

#### 3. Authentication Failures

**Symptoms:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:9080/api/v1/auth/me
# Returns: 401 Unauthorized
```

**Diagnosis:**
```bash
# Check if X-API-Gateway header is included
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-API-Gateway: APISIX" \
     http://localhost:9080/api/v1/auth/me

# Verify token validity
python3 -c "
import jwt
import os
from dotenv import load_dotenv
load_dotenv('violentutf/.env')
secret = os.getenv('JWT_SECRET_KEY')
try:
    decoded = jwt.decode('$TOKEN', secret, algorithms=['HS256'])
    print('Token valid:', decoded)
except Exception as e:
    print('Token invalid:', e)
"
```

#### 4. CORS Issues

**Symptoms:**
```
Access to fetch at 'http://localhost:9080/api/v1/auth/me' from origin 'http://localhost:8501' has been blocked by CORS policy
```

**Solution:**
```bash
# Check CORS configuration in routes
curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     http://localhost:9180/apisix/admin/routes/2001 | jq .value.plugins.cors

# Reconfigure with proper CORS if needed
./configure_routes.sh
```

### Debugging Commands

**Check APISIX Status:**
```bash
# Gateway health
curl http://localhost:9080/health

# Admin API
curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     http://localhost:9180/apisix/admin/routes

# Upstream status
curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     http://localhost:9180/apisix/admin/upstreams/violentutf-api
```

**Test API Endpoints:**
```bash
# Health (no auth)
curl http://localhost:9080/health

# Protected endpoint (with auth)
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-API-Gateway: APISIX" \
     http://localhost:9080/api/v1/auth/me

# Documentation (no auth)
curl http://localhost:9080/docs
```

**Monitor Logs:**
```bash
# APISIX logs
docker logs apisix_apisix_1 -f

# FastAPI logs (through APISIX)
cd ../violentutf_api
docker compose logs fastapi -f

# Access logs
docker exec apisix_apisix_1 tail -f /usr/local/apisix/logs/access.log
```

### Configuration Validation

**Validate Route Configuration:**
```bash
# Check route syntax
curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     http://localhost:9180/apisix/admin/routes/2001 | jq .

# Test route accessibility
curl -I http://localhost:9080/api/v1/auth/token/info
```

**Validate Upstream Health:**
```bash
# Check upstream connectivity
curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     http://localhost:9180/apisix/admin/upstreams/violentutf-api/healthcheck

# Manual upstream test (from APISIX container)
docker exec apisix_apisix_1 curl http://fastapi:8000/health
```

## 📈 Performance Optimization

### Connection Pooling
```json
{
  "keepalive_pool": {
    "size": 320,
    "idle_timeout": 60,
    "requests": 1000
  }
}
```

### Request Buffering
```json
{
  "proxy-buffering": {
    "buffer_size": "8k",
    "buffer_number": 8
  }
}
```

### Timeout Configuration
```json
{
  "timeout": {
    "connect": 6,
    "send": 60,
    "read": 60
  }
}
```

## 🔄 Maintenance Operations

### Route Updates
```bash
# Update existing route
curl -X PUT http://localhost:9180/apisix/admin/routes/2001 \
  -H "X-API-KEY: $APISIX_ADMIN_KEY" \
  -d @updated-route.json

# Reload configuration
curl -X POST http://localhost:9180/apisix/admin/plugins/reload \
  -H "X-API-KEY: $APISIX_ADMIN_KEY"
```

### Backup Configuration
```bash
# Export all routes
curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     http://localhost:9180/apisix/admin/routes > routes-backup.json

# Export upstreams
curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     http://localhost:9180/apisix/admin/upstreams > upstreams-backup.json
```

### Log Rotation
```bash
# Rotate access logs
docker exec apisix_apisix_1 logrotate /etc/logrotate.d/apisix

# Clean old logs
docker exec apisix_apisix_1 find /usr/local/apisix/logs -name "*.log.*" -mtime +7 -delete
```

## 🎛️ Dashboard Management

### APISIX Dashboard
Access the web-based management interface at http://localhost:9001

**Features:**
- Visual route management
- Real-time metrics
- Plugin configuration
- SSL certificate management

**Default Login:**
- Username: admin
- Password: admin

### Dashboard Configuration
```json
{
  "authentication": {
    "secret": "secret",
    "expire_time": 3600,
    "users": [
      {
        "username": "admin",
        "password": "admin"
      }
    ]
  }
}
```

## 🔗 Integration Points

### Keycloak Integration
APISIX can integrate with Keycloak for advanced authentication:

```json
{
  "openid-connect": {
    "client_id": "apisix",
    "client_secret": "secret",
    "discovery": "http://keycloak:8080/realms/ViolentUTF/.well-known/openid_configuration"
  }
}
```

### External Services
Configure routes to external services:

```json
{
  "upstream": {
    "nodes": {
      "external-api.example.com:443": 1
    },
    "scheme": "https"
  }
}
```

---

**🔒 Security Note**: Always use the APISIX gateway for production deployments. Direct FastAPI access should be blocked by firewall rules and container network isolation.

**📋 Best Practices**: 
- Regularly update APISIX admin keys
- Monitor gateway logs for suspicious activity
- Use HTTPS in production environments
- Implement proper rate limiting for your use case