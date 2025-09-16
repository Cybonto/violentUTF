# APISIX Docker Desktop Restart Issue

## Problem Description

When stopping and starting the entire ViolentUTF stack in Docker Desktop, APISIX fails to restart with the following error:

```
nginx: [emerg] bind() to unix:/usr/local/apisix/logs/worker_events.sock failed (98: Address already in use)
```

This occurs because Docker Desktop doesn't always properly clean up Unix socket files when containers are stopped, and APISIX attempts to bind to an existing socket file on restart.

## Root Cause

1. **Socket File Persistence**: The Unix socket file `/usr/local/apisix/logs/worker_events.sock` persists in the Docker volume after container shutdown
2. **Docker Desktop Behavior**: Unlike Docker on Linux, Docker Desktop for macOS doesn't always clean up these files properly
3. **APISIX Startup**: APISIX doesn't check for and remove stale socket files before attempting to bind

## Solutions Implemented

### Solution 1: Clean Restart Script

Created `apisix_clean_restart.sh` to handle the cleanup and restart process:

```bash
#!/bin/bash
# Script to cleanly restart APISIX stack in Docker Desktop

# Features:
- Stops all APISIX containers gracefully
- Cleans up stale socket and PID files from volumes
- Restarts containers with health checks
- Provides clear feedback on service status
```

**Usage:**
```bash
cd /path/to/ViolentUTF
./apisix_clean_restart.sh
```

### Solution 2: Docker Compose Override

Created `apisix/docker-compose.override.yml` to automatically clean up socket files on container startup:

```yaml
version: '3.8'

services:
  apisix:
    # Clean up socket files before starting APISIX
    entrypoint: ["/bin/sh", "-c"]
    command: |
      "rm -f /usr/local/apisix/logs/worker_events.sock /usr/local/apisix/logs/nginx.pid 2>/dev/null || true
      apisix start"

    # Add health check for better monitoring
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9180/apisix/admin/routes", "-H", "X-API-KEY: ${APISIX_ADMIN_KEY:-edd1c9f034335f136f87ad84b625c8f1}"]
      interval: 10s
      timeout: 10s
      retries: 5
      start_period: 30s

    # Handle PID 1 signal issues
    init: true

    # Ensure clean shutdown
    stop_grace_period: 30s
```

This override file:
- Automatically removes stale socket files on startup
- Adds proper health checking
- Uses `init: true` to handle PID 1 signal issues properly
- Provides graceful shutdown period

### Solution 3: Setup Script Enhancement

Updated `setup_macos_files/apisix_setup.sh` to include socket cleanup logic during setup:

```bash
# Clean specific files from volume (preserves etcd data)
docker run --rm -v apisix_apisix_logs:/logs alpine sh -c "rm -f /logs/worker_events.sock /logs/nginx.pid" 2>/dev/null
```

## Verification

After implementing these solutions:

1. **Test Normal Restart**:
   ```bash
   cd apisix
   docker-compose down
   docker-compose up -d
   # Should start without socket errors
   ```

2. **Test Clean Restart Script**:
   ```bash
   ./apisix_clean_restart.sh
   # Should show successful restart with health checks
   ```

3. **Check Service Health**:
   ```bash
   docker-compose ps
   curl -s http://localhost:9180 | jq .
   ```

## Additional Notes

- The socket cleanup is safe and doesn't affect APISIX data or configuration
- The `docker-compose.override.yml` file is automatically loaded by Docker Compose
- The clean restart script provides verbose feedback for troubleshooting
- This issue is specific to Docker Desktop; native Docker on Linux typically doesn't exhibit this behavior

## Related Issues

- Docker Desktop for Mac file system handling
- APISIX worker_events module socket management
- Unix domain socket cleanup in containerized environments
