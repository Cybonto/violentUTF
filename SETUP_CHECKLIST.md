# ViolentUTF Setup Checklist

## Pre-Setup Requirements

### 1. AI-Gov-API Service
- [ ] Ensure AI-Gov-API is running in Docker (`docker ps | grep ai-gov-api`)
- [ ] If not running, start it from `/Users/tamnguyen/Documents/GitHub/ai-gov-api`:
  ```bash
  cd /Users/tamnguyen/Documents/GitHub/ai-gov-api
  docker-compose up -d
  ```

### 2. Configuration Files
- [ ] `ai-tokens.env` configured with correct API keys:
  - OpenAI API key (if using OpenAI)
  - Anthropic API key (if using Anthropic)
  - OpenAPI provider settings (GSAi configured with `test_adm_xTyRonIu1c9GY79U3vccWg`)

- [ ] `apisix/.env` contains APISIX admin key:
  ```
  APISIX_ADMIN_KEY=TdOqcDnp2xKyOsxRHS8sJ8U94ECbagJv
  ```

### 3. Clean State
- [ ] Run deep cleanup if needed:
  ```bash
  ./setup_macos_new.sh --deepcleanup
  ```

## Setup Process

### Run Setup
```bash
./setup_macos_new.sh
```

## Post-Setup Verification

### 1. Check Services
```bash
# Check all containers are running
docker ps

# Expected services:
# - keycloak-keycloak-1 (auth)
# - keycloak-postgres-1 (auth DB)
# - apisix-apisix-1 (API gateway)
# - apisix-etcd-1 (APISIX config)
# - violentutf-api-fastapi-1 (ViolentUTF API)
# - violentutf-streamlit-1 (UI)
# - ai-gov-api-app-1 (AI provider proxy)
# - ai-gov-api-db-1 (AI provider DB)
```

### 2. Test GSAi Integration
```bash
# Test through APISIX gateway
curl -X POST http://localhost:9080/ai/gsai-api-1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer any_key" \
  -d '{
    "model": "claude_3_haiku",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 10
  }'

# Expected: Successful response with AI completion
```

### 3. Access UI
- Streamlit UI: http://localhost:8501
- AI-Gov-API docs: http://localhost:8081/docs
- Keycloak admin: http://localhost:8080

## Known Issues & Fixes

### Issue 1: GSAi 500 Internal Server Error
**Cause**: Database not initialized for AI-Gov-API
**Fix**: The setup script now automatically runs migrations. If still issues:
```bash
docker exec ai-gov-api-app-1 alembic upgrade head
```

### Issue 2: Docker Build Failures
**Cause**: Ubuntu package version pins incompatible with Debian base
**Fix**: Already fixed in Dockerfiles (removed version pins)

### Issue 3: Network Routing
**Cause**: Docker containers can't reach external IPs directly
**Fix**: Routes now use Docker service names (e.g., `ai-gov-api-app-1:8080`)

## Zscaler/Corporate Proxy Support (Staging)

### Automatic Detection and Configuration
The setup script now automatically detects Zscaler via multiple methods:
1. **Force Flag**: Set `FORCE_ZSCALER=true` or use `--force-zscaler` flag
2. **SSL Test**: Detects if curl fails to reach `https://sh.rustup.rs`
3. **Certificate Files**: Checks for Zscaler certificates in `violentutf_api/fastapi_app/`
4. **Environment Variables**: Checks for `ZSCALER_ENABLED` or `CORPORATE_PROXY`

When detected:
- Updates `docker-compose.yml` to use `Dockerfile.zscaler`
- Reverts to standard `Dockerfile` when no proxy is detected

### Required Certificate Files
Place these in `violentutf_api/fastapi_app/`:
- `zscaler.crt` - Zscaler root certificate
- `zscaler.pem` - Zscaler certificate in PEM format (optional)
- `CA.crt` - Corporate CA certificate

### How It Works
1. **Phase 1**: SSL detection runs before services start
2. If Zscaler detected: `docker-compose.yml` updated to use `Dockerfile.zscaler`
3. **Phase 5**: Services built with proper certificate handling
4. `Dockerfile.zscaler` includes:
   - Certificate installation before package downloads
   - Environment variables for curl/pip certificate handling
   - Proper certificate bundle configuration for Rust installation

### Usage Options for Staging

#### Option 1: Automatic with Certificate Generation
```bash
# Enable automatic certificate generation (macOS only)
export FORCE_ZSCALER=true
export AUTO_GENERATE_CERTS=true
./setup_macos_new.sh
```

#### Option 2: Force Zscaler Mode
```bash
# Force Zscaler mode (requires certificates to be in place)
export FORCE_ZSCALER=true
./setup_macos_new.sh
```

#### Option 3: Use Simplified Dockerfile (bypasses SSL)
```bash
# Creates a Dockerfile with curl -k flag
./fix-zscaler-build.sh
./setup_macos_new.sh
```

#### Option 4: Manual Override
```bash
# Force use of Dockerfile.zscaler
sed -i 's|dockerfile: Dockerfile|dockerfile: Dockerfile.zscaler|g' apisix/docker-compose.yml

# Then run setup
./setup_macos_new.sh
```

## Environment-Specific Configuration

### Development (Current)
- GSAi endpoint: `http://192.168.131.5:8081` (mapped to `ai-gov-api-app-1:8080` internally)
- Auth token: `test_adm_xTyRonIu1c9GY79U3vccWg`

### Staging
- Update `ai-tokens.env`:
  ```env
  OPENAPI_1_BASE_URL=https://api.dev.gsai.mcaas.fcs.gsa.gov
  OPENAPI_1_AUTH_TOKEN=<staging_token>
  ```
- Routes will automatically use HTTPS endpoint
- Ensure SSL certificates are properly configured

## Models Available
- `claude_3_5_sonnet`
- `claude_3_7_sonnet`
- `claude_3_haiku`
- `llama3211b`
- `cohere_english_v3`

Note: Do NOT use OpenAI model names like `gpt-3.5-turbo` with GSAi