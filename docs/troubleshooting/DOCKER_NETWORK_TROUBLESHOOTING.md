# Docker Network Troubleshooting Guide

## Common Issues After Setup

### 1. "Cannot connect to APISIX gateway" Error
**Cause**: FastAPI container cannot reach APISIX container
**Solution**:
```bash
# Check container connectivity (using Python since nc might not be available)
docker exec violentutf_api python -c "import requests; print(requests.get('http://apisix-apisix-1:9080').status_code)"

# Reconnect containers to shared network
docker network connect vutf-network violentutf_api
docker network connect vutf-network apisix-apisix-1

# Restart FastAPI service
docker restart violentutf_api
```

### 2. "Generator type 'None'" Error
**Cause**: Field mapping issue in generator service
**Solution**: Restart FastAPI container to reload code
```bash
docker restart violentutf_api
```

### 3. Authentication Issues
**Cause**: JWT secret mismatch between services
**Solution**: Verify and sync JWT secrets
```bash
grep JWT_SECRET_KEY violentutf/.env
grep JWT_SECRET_KEY violentutf_api/fastapi_app/.env
# Values should match
```

### 4. Cross-User Generator Access Issues
**Cause**: User context mismatch in orchestrator names
**Solution**: Check username consistency
```bash
# In Streamlit, verify username
grep KEYCLOAK_USERNAME violentutf/.env
```

## Verification Commands
```bash
# Check all containers are running
docker ps --filter "name=apisix\|keycloak\|violentutf"

# Check network connectivity
docker network inspect vutf-network

# Test API endpoints
curl http://localhost:9080/api/v1/health
curl http://localhost:9080/api/v1/generators
```
