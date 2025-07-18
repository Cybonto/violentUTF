# Enterprise Environment: Duplicate app_data Folders Fix

## Issue Description
In enterprise environments, you might see two `app_data` folders under the FastAPI instance's `/app` folder. This is caused by conflicting volume mounts in the Docker configuration.

## Root Cause
The docker-compose.yml has overlapping volume mounts:
```yaml
volumes:
  - ../violentutf_api/fastapi_app:/app              # Maps entire directory including app_data if it exists
  - fastapi_data:/app/app_data                      # Creates a separate volume mount at same location
  - ../violentutf/app_data/violentutf:/app/app_data/violentutf
```

## Solutions

### Option 1: Exclude app_data from the main mount (Recommended)
Create a `.dockerignore` file in `violentutf_api/fastapi_app/`:
```
app_data/
logs/
*.pyc
__pycache__/
.env.local
.env.*.local
```

### Option 2: Modify docker-compose.yml
Update the volume mounts to avoid conflicts:
```yaml
volumes:
  # Mount only the app code directory
  - ../violentutf_api/fastapi_app/app:/app/app
  - ../violentutf_api/fastapi_app/main.py:/app/main.py
  - ../violentutf_api/fastapi_app/requirements.txt:/app/requirements.txt
  # Mount data directories separately
  - fastapi_data:/app/app_data
  - fastapi_config:/app/config
  - ../violentutf/app_data/violentutf:/app/app_data/violentutf
```

### Option 3: Use named volumes only
Remove the host directory mount and use only named volumes:
```yaml
volumes:
  - fastapi_code:/app/app            # For code (optional, for development)
  - fastapi_data:/app/app_data       # For data
  - fastapi_config:/app/config       # For config
  - ../violentutf/app_data/violentutf:/app/app_data/violentutf
```

## Verification Steps

1. Check current mounts inside container:
   ```bash
   docker exec violentutf_api df -h | grep app
   docker exec violentutf_api ls -la /app/
   ```

2. Check for duplicate directories:
   ```bash
   docker exec violentutf_api find /app -name "app_data" -type d
   ```

3. Verify data persistence:
   ```bash
   docker exec violentutf_api ls -la /app/app_data/
   docker exec violentutf_api ls -la /app/app_data/violentutf/
   ```

## Enterprise-Specific Considerations

1. **Persistent Storage**: Ensure your enterprise storage solution properly backs up the Docker volumes
2. **Permissions**: The container runs as user `fastapi` (UID 1000), ensure volume permissions match
3. **Network Policies**: The duplicate folders might cause issues with security scanning tools

## Clean Migration Steps

1. **Backup existing data**:
   ```bash
   docker exec violentutf_api tar -czf /tmp/app_data_backup.tar.gz -C /app app_data/
   docker cp violentutf_api:/tmp/app_data_backup.tar.gz ./app_data_backup.tar.gz
   ```

2. **Stop services**:
   ```bash
   docker-compose -f apisix/docker-compose.yml down
   ```

3. **Apply the fix** (choose one of the options above)

4. **Restart services**:
   ```bash
   docker-compose -f apisix/docker-compose.yml up -d
   ```

5. **Verify fix**:
   ```bash
   docker exec violentutf_api find /app -name "app_data" -type d
   # Should show only one app_data directory
   ```

## Related Files
- `/violentutf_api/fastapi_app/Dockerfile` - Creates app_data directory
- `/apisix/docker-compose.yml` - Contains volume mount configuration
- `/violentutf_api/fastapi_app/.dockerignore` - Should exclude app_data

## Support
If issues persist, check:
1. Docker version compatibility
2. Enterprise storage driver limitations
3. SELinux or AppArmor policies that might affect volume mounts