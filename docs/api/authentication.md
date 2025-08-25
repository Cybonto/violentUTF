# ViolentUTF API Authentication Guide

Complete documentation for the ViolentUTF authentication system, covering Keycloak SSO, JWT token management, APISIX gateway authentication, and frontend integration.

## 🏗️ Authentication Architecture

ViolentUTF uses a **Keycloak-centric authentication system** with APISIX gateway protection:

1. **Keycloak SSO** - Primary identity provider for user authentication
2. **JWT Tokens** - For authenticated communication between frontend and backend
3. **APISIX Gateway** - Single entry point with cryptographic verification
4. **API Keys** - Alternative authentication for automation and CI/CD

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Streamlit  │───▶│  Keycloak   │───▶│   APISIX    │───▶│   FastAPI   │
│  Frontend   │    │     SSO     │    │  Gateway    │    │   Backend   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
   User Login         OAuth2 Token       JWT Validation      API Processing
```

## 🔐 Authentication Methods

### 1. JWT Bearer Token (Primary)

The primary authentication method for interactive use and Streamlit integration.

#### Obtaining JWT Token

**Via API Endpoint:**
```bash
curl -X POST http://localhost:9080/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Via CLI Tool:**
```bash
python3 violentutf_api/jwt_cli.py login
```

#### Using JWT Token

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "X-API-Gateway: APISIX" \
     http://localhost:9080/api/v1/auth/me
```

### 2. API Key Authentication (Automation)

For automated systems, CI/CD pipelines, and non-interactive use.

#### Creating API Key

```bash
# Using CLI tool
python3 violentutf_api/jwt_cli.py keys create --name "Production Key"

# Using API endpoint
curl -X POST http://localhost:9080/api/v1/keys \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{
    "name": "CI/CD Pipeline Key",
    "permissions": ["api:access", "pyrit:run", "garak:run"]
  }'
```

#### Using API Key

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
     -H "X-API-Gateway: APISIX" \
     http://localhost:9080/api/v1/auth/me
```

## 🎫 JWT Token Management

### Token Structure

ViolentUTF JWT tokens contain the following claims:

```json
{
  "preferred_username": "user@example.com",
  "email": "user@example.com",
  "name": "User Display Name",
  "sub": "user-uuid",
  "roles": ["ai-api-access"],
  "iat": 1640995200,
  "exp": 1640998800
}
```

**Required Claims:**
- `preferred_username` - User identifier
- `email` - User email address
- `name` - Display name
- `sub` - Subject identifier
- `roles` - Must include `ai-api-access`
- `iat` - Issued at timestamp (REQUIRED)
- `exp` - Expiration timestamp (REQUIRED)

### Token Lifecycle

#### Creation Process

**Primary Flow: Keycloak SSO Authentication**
```python
# 1. User authenticates via Keycloak SSO in Streamlit
keycloak_token = st.session_state.get('access_token')
decoded = jwt.decode(keycloak_token, options={"verify_signature": False})

# 2. Create ViolentUTF-specific JWT for FastAPI
from utils.jwt_manager import jwt_manager
api_token = jwt_manager.create_token(decoded)
```

**Development/Fallback: Environment Credentials**
```python
# Only when Keycloak is unavailable - uses configured service account
keycloak_data = {
    "preferred_username": os.getenv('KEYCLOAK_USERNAME', 'violentutf.web'),
    "email": "violentutf@example.com",
    "name": "ViolentUTF User",
    "sub": "violentutf-user",
    "roles": ["ai-api-access"]
}
api_token = jwt_manager.create_token(keycloak_data)
```

#### Automatic Refresh

ViolentUTF implements **proactive token refresh** to prevent authentication failures:

- **Refresh Trigger**: 10 minutes before token expiry
- **Background Monitoring**: Continuous token validity checking
- **Seamless Updates**: Session state updated automatically
- **Error Recovery**: Graceful handling of refresh failures

```python
def _attempt_proactive_refresh(self):
    """Attempt to proactively refresh the token before it expires"""
    try:
        if not self._should_refresh():
            return
            
        self._refresh_in_progress = True
        new_token = self._create_fresh_token()
        
        if new_token:
            st.session_state['api_token'] = new_token
            self._last_refresh_time = time.time()
            logger.info("JWT token refreshed successfully")
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
```

#### Token Validation

**Basic Validation (Level 1 Endpoints):**
- Token signature verification
- Required claims presence (`iat`, `exp`, `roles`)
- Token expiration check
- Role-based access control

**Enhanced Validation (Level 2 Endpoints):**
- All basic validation requirements
- APISIX API key verification
- Enhanced claims validation
- Session state verification

## 🔑 Keycloak SSO Integration

### Configuration

Keycloak is configured with the ViolentUTF realm and multiple clients:

```bash
# Environment Configuration
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=ViolentUTF
KEYCLOAK_CLIENT_ID=violentutf-web
KEYCLOAK_CLIENT_SECRET=<generated_secret>
```

### OAuth2 Flow

**1. Authorization Code Flow (Streamlit)**
```python
# OAuth2 configuration in .streamlit/secrets.toml
[keycloak]
client_id = "violentutf-web"
client_secret = "your_client_secret"
server_metadata_url = "http://localhost:8080/realms/ViolentUTF/.well-known/openid_configuration"
```

**2. Resource Owner Password Credentials (CLI/Testing)**
```bash
curl -X POST http://localhost:8080/realms/ViolentUTF/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=violentutf-api" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "username=$USERNAME" \
  -d "password=$PASSWORD"
```

### User Roles and Permissions

**Required Role: `ai-api-access`**
- Grants access to ViolentUTF API endpoints
- Required in JWT token `roles` claim
- Configured in Keycloak user management

**Role Assignment:**
```bash
# Via Keycloak Admin Console
1. Navigate to Users → [User] → Role Mapping
2. Assign "ai-api-access" role
3. Verify role appears in token claims
```

## 🌐 APISIX Gateway Authentication

### Admin Key Configuration

ViolentUTF uses **admin key-based route configuration** for APISIX:

```bash
# Auto-generated during setup
APISIX_ADMIN_KEY=<generated_admin_key>
APISIX_GATEWAY_SECRET=<shared_hmac_secret>
```

### OpenAPI Provider Authentication

APISIX automatically handles authentication for OpenAPI providers through the `proxy-rewrite` plugin:

**Bearer Token Authentication**:
```json
{
  "proxy-rewrite": {
    "headers": {
      "set": {
        "Authorization": "Bearer <provider_token>"
      }
    }
  }
}
```

**API Key Authentication**:
```json
{
  "proxy-rewrite": {
    "headers": {
      "set": {
        "X-API-Key": "<provider_api_key>"
      }
    }
  }
}
```

This dual-layer authentication ensures:
1. **Gateway Level**: Clients authenticate to APISIX using `apikey` header
2. **Provider Level**: APISIX authenticates to upstream APIs using configured credentials

#### Configuration in ai-tokens.env

```bash
# OpenAPI Provider 1
OPENAPI_1_ENABLED=true
OPENAPI_1_AUTH_TYPE=bearer
OPENAPI_1_AUTH_TOKEN=sk-your-provider-token

# OpenAPI Provider 2  
OPENAPI_2_ENABLED=true
OPENAPI_2_AUTH_TYPE=api_key
OPENAPI_2_API_KEY=your-api-key
OPENAPI_2_API_KEY_HEADER=X-Custom-Key
```

### Cryptographic Verification

FastAPI verifies requests come from APISIX using HMAC signatures:

```python
# APISIX adds verification headers
headers = {
    "X-API-Gateway": "APISIX",
    "X-APISIX-Signature": hmac_signature,
    "X-APISIX-Timestamp": current_timestamp
}

# FastAPI verification process
signature_payload = f"{method}:{path}:{timestamp}"
expected_signature = hmac.new(
    gateway_secret.encode(),
    signature_payload.encode(),
    hashlib.sha256
).hexdigest()
```

### Route Security

**Protected Routes:**
- All `/api/v1/*` endpoints require authentication
- JWT token validation performed by FastAPI
- APISIX provides gateway-level protection

**Public Routes:**
- `/health` - Health check endpoint
- `/docs`, `/redoc` - API documentation
- `/openapi.json` - OpenAPI schema

## 🎨 Frontend Integration

### Streamlit Authentication Pattern

**All Streamlit pages must implement this exact authentication pattern:**

```python
def main():
    # MANDATORY: Use centralized authentication handler
    from utils.auth_utils import handle_authentication_and_sidebar
    handle_authentication_and_sidebar("Page Name")
    
    # MANDATORY: Check authentication status
    has_keycloak_token = bool(st.session_state.get('access_token'))
    has_env_credentials = bool(os.getenv('KEYCLOAK_USERNAME'))
    
    if not has_keycloak_token and not has_env_credentials:
        st.warning("⚠️ Authentication required")
        return
    
    # MANDATORY: Ensure API token exists
    if not st.session_state.get('api_token'):
        api_token = create_compatible_api_token()
        if not api_token:
            st.error("❌ Failed to generate API token")
            return
```

### API Request Headers

**Standard header generation function:**

```python
def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API requests through APISIX Gateway"""
    try:
        from utils.jwt_manager import jwt_manager
        
        # Get valid token (automatically handles refresh if needed)
        token = jwt_manager.get_valid_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-API-Gateway": "APISIX"  # Gateway identification
        }
        
        # Add APISIX API key for AI model access
        apisix_api_key = (
            os.getenv("VIOLENTUTF_API_KEY") or 
            os.getenv("APISIX_API_KEY") or
            os.getenv("AI_GATEWAY_API_KEY")
        )
        if apisix_api_key:
            headers["apikey"] = apisix_api_key
        
        return headers
    except Exception as e:
        logger.error(f"Failed to get auth headers: {e}")
        return {}
```

### Sidebar Status Display

Real-time authentication status in Streamlit sidebar:

```python
def show_authenticated_sidebar(page_name: str = "") -> str:
    if has_api_token and has_ai_access:
        try:
            from utils.jwt_manager import jwt_manager
            status, minutes_remaining = jwt_manager.get_refresh_status()
            
            if status == "refreshing":
                st.info("🔄 AI Gateway: Refreshing Token...")
            elif status == "expired":
                st.error("⏰ AI Gateway: Token Expired")
            elif status == "expiring_soon":
                st.warning(f"⚠️ AI Gateway: Expires in {minutes_remaining}m")
            else:  # active
                st.success(f"🚀 AI Gateway: Active ({minutes_remaining}m left)")
        except Exception as e:
            st.error(f"🔑 API: Auth Failed - {str(e)}")
```

## 🔧 Environment Configuration

### Streamlit Environment (`violentutf/.env`)

```bash
# JWT Configuration (shared with FastAPI)
JWT_SECRET_KEY=<generated_secret>

# APISIX Gateway Configuration
VIOLENTUTF_API_KEY=<generated_api_key>
VIOLENTUTF_API_URL=http://localhost:9080

# Keycloak Configuration (Primary Authentication)
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=ViolentUTF
KEYCLOAK_USERNAME=violentutf.web
KEYCLOAK_PASSWORD=<generated_password>
KEYCLOAK_CLIENT_ID=violentutf-web
KEYCLOAK_CLIENT_SECRET=<generated_secret>
```

### FastAPI Environment (`violentutf_api/fastapi_app/.env`)

```bash
# JWT Configuration (shared with Streamlit)
SECRET_KEY=<same_as_jwt_secret_key>
JWT_SECRET_KEY=<same_as_streamlit>

# APISIX Gateway Configuration
APISIX_BASE_URL=http://apisix:9080
APISIX_ADMIN_URL=http://apisix:9180
APISIX_ADMIN_KEY=<generated_admin_key>
APISIX_GATEWAY_SECRET=<shared_hmac_secret>
VIOLENTUTF_API_KEY=<generated_api_key>

# Keycloak Integration
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=ViolentUTF
KEYCLOAK_CLIENT_ID=violentutf-api
KEYCLOAK_CLIENT_SECRET=<generated_secret>
```

## 🚨 Troubleshooting

### Common Authentication Issues

#### "JWT token has invalid signature"

**Cause**: Mismatched JWT secrets between Streamlit and FastAPI

**Solution**:
```bash
# Check secret consistency
echo "FastAPI: $(grep '^JWT_SECRET_KEY=' violentutf_api/fastapi_app/.env | cut -d'=' -f2 | head -c 8)..."
echo "Streamlit: $(grep '^JWT_SECRET_KEY=' violentutf/.env | cut -d'=' -f2 | head -c 8)..."

# Synchronize secrets if different
FASTAPI_JWT=$(grep '^JWT_SECRET_KEY=' violentutf_api/fastapi_app/.env | cut -d'=' -f2)
sed -i '' "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$FASTAPI_JWT|" violentutf/.env
```

#### "Direct access not allowed. Use the API gateway."

**Cause**: Request not going through APISIX gateway

**Solution**:
```bash
# Ensure X-API-Gateway header is present
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-API-Gateway: APISIX" \
     http://localhost:9080/api/v1/auth/me
```

#### "Missing required JWT claim: iat"

**Cause**: JWT token missing issued-at timestamp

**Solution**:
```python
# Ensure iat claim in token creation
payload = {
    'preferred_username': username,
    'email': email,
    'iat': int(time.time()),  # Required
    'exp': int(time.time()) + 1800
}
```

#### "Not authenticated" (Level 2 Endpoints)

**Cause**: Missing APISIX API key for enhanced endpoints

**Solution**:
```bash
# Include apikey header for orchestrator endpoints
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-API-Gateway: APISIX" \
     -H "apikey: $APISIX_API_KEY" \
     http://localhost:9080/api/v1/orchestrators
```

### OpenAPI Authentication Troubleshooting

#### "401 Unauthorized" from OpenAPI Provider

**Cause**: APISIX not forwarding authentication headers to upstream

**Solution 1**: Update routes using the provided script
```bash
cd apisix && ./update_openapi_auth.sh
```

**Solution 2**: Manually verify route configuration
```bash
# Check if authentication headers are configured
curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     http://localhost:9180/apisix/admin/routes | \
     jq '.list[] | select(.value.uri | contains("/ai/openapi/")) | 
         {id: .key, auth: .value.plugins."proxy-rewrite".headers.set}'
```

**Solution 3**: Test authentication directly
```bash
# Verify your token works with the provider
curl -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
     https://api.provider.com/v1/models
```

#### "Authentication failed. Please check your OPENAPI-{ID} API key configuration"

**Cause**: Missing or incorrect authentication configuration in generator_integration_service

**Solution**: Ensure ai-tokens.env has correct provider configuration
```bash
# Check provider configuration
grep "OPENAPI_1_" ai-tokens.env

# Required fields:
# OPENAPI_1_ENABLED=true
# OPENAPI_1_ID=provider-id
# OPENAPI_1_AUTH_TYPE=bearer|api_key|basic
# OPENAPI_1_AUTH_TOKEN=<token> (for bearer)
# OPENAPI_1_API_KEY=<key> (for api_key)
```

### Debugging Commands

**Check Service Status:**
```bash
# Verify Keycloak
curl http://localhost:8080/realms/ViolentUTF

# Verify APISIX Gateway
curl http://localhost:9080/health

# Verify FastAPI (through gateway)
curl -H "X-API-Gateway: APISIX" http://localhost:9080/api/v1/health
```

**Test Authentication Flow:**
```bash
# 1. Get Keycloak token
KEYCLOAK_TOKEN=$(curl -X POST http://localhost:8080/realms/ViolentUTF/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&client_id=violentutf-api&username=$USER&password=$PASS" \
  | jq -r .access_token)

# 2. Get ViolentUTF JWT
VUTF_TOKEN=$(curl -X POST http://localhost:9080/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$USER&password=$PASS" \
  | jq -r .access_token)

# 3. Test API access
curl -H "Authorization: Bearer $VUTF_TOKEN" \
     -H "X-API-Gateway: APISIX" \
     http://localhost:9080/api/v1/auth/me
```

**Monitor JWT Refresh:**
```python
from utils.jwt_manager import jwt_manager
status = jwt_manager.get_refresh_status()
print(f"Refresh status: {status}")

token = jwt_manager.get_valid_token()
print(f"Valid token available: {bool(token)}")
```

## 🔒 Security Best Practices

### JWT Secret Management
- **Shared Secret**: Same `JWT_SECRET_KEY` used by Streamlit and FastAPI
- **Environment Only**: Never stored in code or configuration files
- **Auto-Generation**: Generated by setup script using cryptographically secure methods
- **Regular Rotation**: Rotate secrets periodically for enhanced security

### Token Security
- **Default Expiry**: 30 minutes for JWT tokens
- **Proactive Refresh**: 10-minute buffer prevents authentication failures
- **Secure Storage**: Tokens stored in session state, never persisted
- **Role Verification**: `ai-api-access` role required for all operations

### Gateway Security
- **Cryptographic Verification**: HMAC signatures prevent gateway bypass
- **Admin Key Protection**: Secure admin keys for route configuration
- **Direct Access Blocking**: FastAPI only accepts APISIX-routed requests
- **Header Validation**: Proper gateway identification headers required

## 📚 API Endpoints

### Authentication Endpoints

#### `POST /api/v1/auth/token`
Obtain JWT access token

**Request:**
```bash
curl -X POST http://localhost:9080/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user&password=pass"
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

#### `GET /api/v1/auth/me`
Get current user information

**Request:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-API-Gateway: APISIX" \
     http://localhost:9080/api/v1/auth/me
```

**Response:**
```json
{
  "username": "user@example.com",
  "email": "user@example.com",
  "roles": ["ai-api-access"]
}
```

#### `POST /api/v1/auth/refresh`
Refresh access token

**Request:**
```bash
curl -X POST http://localhost:9080/api/v1/auth/refresh \
  -H "Authorization: Bearer $TOKEN"
```

### API Key Management Endpoints

#### `POST /api/v1/keys`
Create new API key

**Request:**
```json
{
  "name": "Production Key",
  "permissions": ["api:access", "pyrit:run", "garak:run"]
}
```

#### `GET /api/v1/keys`
List all API keys for current user

#### `DELETE /api/v1/keys/{key_id}`
Revoke an API key

## 🔄 Token Lifecycle Management

### Creation
1. User authenticates via Keycloak SSO
2. Keycloak returns OAuth2 token with user info
3. ViolentUTF creates internal JWT with required claims
4. JWT stored in session state for API access

### Validation
1. API request includes JWT in Authorization header
2. FastAPI validates token signature using shared secret
3. Claims validation (required fields, roles, expiry)
4. User context created from token claims

### Refresh
1. JWT manager monitors token expiry (10-minute buffer)
2. Proactive refresh triggered before expiry
3. New token created with same user data
4. Session state updated seamlessly

### Expiry
1. Token expires after 30 minutes (configurable)
2. Automatic refresh prevents user-visible failures
3. Manual refresh available via API endpoint
4. Emergency token recreation if refresh fails

---

**🔒 Security Notice**: This authentication system is designed for security testing environments. Always use HTTPS in production and follow enterprise security guidelines for token management and secret rotation.