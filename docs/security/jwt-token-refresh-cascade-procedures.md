# JWT Token Refresh Cascade Procedures

## Overview

This document provides comprehensive procedures for JWT token refresh propagation through ViolentUTF's multi-service authentication architecture. The system implements a cascading token refresh pattern across Keycloak → APISIX → FastAPI → MCP Server to maintain seamless authentication during long-running security testing operations.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Token Refresh Flow](#token-refresh-flow)
3. [Cascade Procedures](#cascade-procedures)
4. [Failure Scenarios and Recovery](#failure-scenarios-and-recovery)
5. [Monitoring and Validation](#monitoring-and-validation)
6. [Testing Framework](#testing-framework)
7. [Troubleshooting Guide](#troubleshooting-guide)

## Architecture Overview

### Multi-Service Token Architecture

ViolentUTF implements a layered JWT token system across four authentication boundaries:

```
User Session → Streamlit → APISIX → FastAPI → MCP Server
    ↓              ↓         ↓        ↓        ↓
Keycloak       JWT Token  API Key   JWT    OAuth 2.0
Session        (30min)   (Gateway) Token   PKCE
```

### Token Types and Lifecycles

1. **Keycloak Session Token**: Long-lived SSO session (8 hours)
2. **Streamlit JWT Token**: Medium-lived API access (30 minutes)
3. **APISIX API Key**: Static gateway authentication
4. **FastAPI JWT Token**: Same as Streamlit JWT (shared secret)
5. **MCP OAuth 2.0 Token**: Short-lived MCP access (15 minutes)

### Refresh Trigger Points

- **Proactive Refresh**: 10 minutes before expiry
- **Reactive Refresh**: On authentication failure
- **Cascade Refresh**: When upstream token refreshes
- **Manual Refresh**: User-initiated or administrative

## Token Refresh Flow

### 1. Streamlit JWT Token Refresh

**Primary Refresh Logic**:
```python
# From JWTManager.get_valid_token()
def get_valid_token(self) -> Optional[str]:
    """Get valid JWT token with proactive refresh"""

    current_time = int(time.time())
    token_exp = st.session_state.get("api_token_exp", 0)

    # Proactive refresh if expiring in next 10 minutes
    if current_time >= (token_exp - self._refresh_buffer):  # 600 seconds
        logger.info("JWT token expiring soon, attempting proactive refresh")
        self._attempt_proactive_refresh()

    # Check if token is expired or will expire very soon (5 minutes)
    if current_time >= (token_exp - 300):
        logger.info("JWT token expired or expiring soon, refresh needed")
        self._clear_token()
        return None

    return str(st.session_state["api_token"])
```

**Refresh Process**:
```python
async def refresh_streamlit_jwt_token():
    """Refresh Streamlit JWT token from Keycloak session"""

    # Step 1: Validate Keycloak session
    keycloak_token = get_keycloak_session_token()
    if not keycloak_token or is_keycloak_token_expired(keycloak_token):
        return {"status": "keycloak_expired", "action": "redirect_to_login"}

    # Step 2: Extract user context
    user_context = extract_user_context_from_keycloak(keycloak_token)
    canonical_username = UserContextManager.normalize_username(user_context["preferred_username"])

    # Step 3: Create new JWT token
    new_jwt_payload = {
        "sub": canonical_username,
        "username": canonical_username,
        "email": user_context.get("email", f"{canonical_username}@violentutf.local"),
        "name": user_context.get("name", canonical_username),
        "roles": user_context.get("roles", ["ai-api-access"]),
        "iat": int(time.time()),
        "exp": int(time.time()) + 1800,  # 30 minutes
        "token_type": "access"
    }

    # Step 4: Sign new token
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    new_token = jwt.encode(new_jwt_payload, jwt_secret, algorithm="HS256")

    # Step 5: Update session state
    st.session_state["api_token"] = new_token
    st.session_state["api_token_exp"] = new_jwt_payload["exp"]
    st.session_state["api_token_created"] = new_jwt_payload["iat"]

    return {"status": "refreshed", "token": new_token, "expires_at": new_jwt_payload["exp"]}
```

### 2. APISIX Gateway Token Validation

**APISIX Token Handling**:
```lua
-- APISIX JWT validation (conceptual)
local jwt = require "resty.jwt"

function validate_jwt_token(token)
    local jwt_secret = os.getenv("JWT_SECRET_KEY")
    local jwt_obj = jwt:verify(jwt_secret, token)

    if not jwt_obj.valid then
        return {valid = false, error = "invalid_signature"}
    end

    local current_time = ngx.time()
    if jwt_obj.payload.exp < current_time then
        return {valid = false, error = "token_expired"}
    end

    -- Check if token expires soon (5 minutes)
    if jwt_obj.payload.exp < (current_time + 300) then
        return {valid = true, refresh_recommended = true, user = jwt_obj.payload.sub}
    end

    return {valid = true, user = jwt_obj.payload.sub}
end
```

**APISIX Refresh Recommendations**:
```bash
# APISIX response headers for refresh recommendations
HTTP/1.1 200 OK
X-Token-Status: expiring_soon
X-Token-Expires-At: 1640995200
X-Refresh-Recommended: true
X-User-Context: tam.nguyen
```

### 3. FastAPI Token Processing

**FastAPI Authentication Dependency**:
```python
# From FastAPI auth dependency
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from JWT token with refresh cascade support"""

    try:
        # Decode and validate token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        username = payload.get("sub")

        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Check token expiry and trigger cascade refresh if needed
        current_time = int(time.time())
        token_exp = payload.get("exp", 0)

        # If token expires in next 5 minutes, add refresh header
        if token_exp < (current_time + 300):
            # Signal upstream to refresh
            response.headers["X-Token-Refresh-Required"] = "true"
            response.headers["X-Token-Expires-At"] = str(token_exp)

        return {"username": username, "token_status": "valid"}

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired",
            headers={"X-Token-Status": "expired"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### 4. MCP Server OAuth 2.0 Refresh

**MCP OAuth Token Management**:
```python
# From MCP OAuth proxy
class MCPOAuthProxy:
    def __init__(self):
        self.token_cache = {}
        self.refresh_tokens = {}

    async def get_valid_mcp_token(self, user_context):
        """Get valid MCP token with OAuth 2.0 PKCE refresh"""

        user_id = user_context["username"]
        cached_token = self.token_cache.get(user_id)

        # Check if cached token is still valid
        if cached_token and not self.is_token_expired(cached_token):
            # Check if refresh needed (2 minutes before expiry)
            if self.token_expires_soon(cached_token, buffer=120):
                await self.refresh_mcp_token(user_id)

            return self.token_cache[user_id]

        # Token expired or missing, need fresh authentication
        return await self.authenticate_mcp_user(user_context)

    async def refresh_mcp_token(self, user_id):
        """Refresh MCP token using OAuth 2.0 refresh token"""

        refresh_token = self.refresh_tokens.get(user_id)
        if not refresh_token:
            # No refresh token available, need re-authentication
            raise MCPAuthenticationRequired("No refresh token available")

        # OAuth 2.0 refresh token flow
        refresh_payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id
        }

        response = await self.mcp_auth_client.post("/oauth/token", data=refresh_payload)

        if response.status_code == 200:
            token_data = response.json()

            # Update token cache
            self.token_cache[user_id] = {
                "access_token": token_data["access_token"],
                "expires_at": int(time.time()) + token_data["expires_in"],
                "token_type": token_data["token_type"]
            }

            # Update refresh token if provided
            if "refresh_token" in token_data:
                self.refresh_tokens[user_id] = token_data["refresh_token"]

            return self.token_cache[user_id]
        else:
            # Refresh failed, need re-authentication
            raise MCPAuthenticationRequired("Token refresh failed")
```

## Cascade Procedures

### 1. Upstream-Triggered Refresh Cascade

**Keycloak Session Refresh → All Downstream**:
```python
async def cascade_refresh_from_keycloak():
    """Cascade refresh triggered by Keycloak session update"""

    cascade_results = {
        "trigger": "keycloak_session_refresh",
        "timestamp": datetime.now().isoformat(),
        "stages": {}
    }

    try:
        # Stage 1: Refresh Streamlit JWT
        streamlit_result = await refresh_streamlit_jwt_token()
        cascade_results["stages"]["streamlit_jwt"] = streamlit_result

        if streamlit_result["status"] != "refreshed":
            raise CascadeRefreshError("Streamlit JWT refresh failed")

        # Stage 2: Validate APISIX will accept new token
        apisix_validation = await validate_token_with_apisix(streamlit_result["token"])
        cascade_results["stages"]["apisix_validation"] = apisix_validation

        # Stage 3: Update FastAPI token context (automatic via new requests)
        # FastAPI will receive new token on next request

        # Stage 4: Refresh MCP tokens for active sessions
        active_mcp_sessions = get_active_mcp_sessions()
        mcp_refresh_results = []

        for session in active_mcp_sessions:
            try:
                mcp_result = await refresh_mcp_token(session["user_id"])
                mcp_refresh_results.append({
                    "user": session["user_id"],
                    "status": "refreshed",
                    "expires_at": mcp_result["expires_at"]
                })
            except Exception as e:
                mcp_refresh_results.append({
                    "user": session["user_id"],
                    "status": "failed",
                    "error": str(e)
                })

        cascade_results["stages"]["mcp_refresh"] = mcp_refresh_results
        cascade_results["overall_status"] = "success"

        return cascade_results

    except Exception as e:
        cascade_results["overall_status"] = "failed"
        cascade_results["error"] = str(e)

        # Attempt recovery
        await attempt_cascade_recovery(cascade_results)

        return cascade_results
```

### 2. Downstream-Triggered Refresh Cascade

**MCP Token Expiry → Upstream Refresh Check**:
```python
async def cascade_refresh_from_mcp_expiry(user_context):
    """Cascade refresh triggered by MCP token expiry"""

    # Check if upstream tokens are still valid
    streamlit_token_status = check_streamlit_token_status(user_context["username"])

    if streamlit_token_status["status"] == "expired":
        # Upstream token also expired, trigger full cascade
        return await cascade_refresh_from_keycloak()

    elif streamlit_token_status["status"] == "expiring_soon":
        # Refresh upstream proactively
        await refresh_streamlit_jwt_token()

    # Refresh only MCP token
    mcp_refresh_result = await refresh_mcp_token(user_context["username"])

    return {
        "trigger": "mcp_token_expiry",
        "scope": "mcp_only",
        "result": mcp_refresh_result
    }
```

### 3. Proactive Refresh Cascade

**Scheduled Proactive Refresh**:
```python
class ProactiveRefreshScheduler:
    def __init__(self):
        self.refresh_intervals = {
            "streamlit_jwt": 1200,  # 20 minutes (for 30-minute tokens)
            "mcp_oauth": 600,       # 10 minutes (for 15-minute tokens)
        }

    async def schedule_proactive_refresh(self):
        """Schedule proactive refresh for all active sessions"""

        active_users = get_active_users()

        for user in active_users:
            # Check if user needs proactive refresh
            user_tokens = get_user_token_status(user)

            refresh_needed = []

            # Check Streamlit JWT
            if user_tokens["streamlit_jwt"]["expires_in"] < 600:  # 10 minutes
                refresh_needed.append("streamlit_jwt")

            # Check MCP OAuth
            if user_tokens.get("mcp_oauth", {}).get("expires_in", 0) < 300:  # 5 minutes
                refresh_needed.append("mcp_oauth")

            if refresh_needed:
                await self.execute_proactive_refresh(user, refresh_needed)

    async def execute_proactive_refresh(self, username, token_types):
        """Execute proactive refresh for specific token types"""

        refresh_results = {
            "user": username,
            "timestamp": datetime.now().isoformat(),
            "token_types": token_types,
            "results": {}
        }

        for token_type in token_types:
            try:
                if token_type == "streamlit_jwt":
                    # Simulate user context for refresh
                    user_context = get_user_context_for_refresh(username)
                    result = await refresh_streamlit_jwt_token_for_user(user_context)
                    refresh_results["results"][token_type] = result

                elif token_type == "mcp_oauth":
                    result = await refresh_mcp_token(username)
                    refresh_results["results"][token_type] = result

            except Exception as e:
                refresh_results["results"][token_type] = {
                    "status": "failed",
                    "error": str(e)
                }

        return refresh_results
```

## Failure Scenarios and Recovery

### 1. Keycloak Session Expired

**Detection**:
```python
def detect_keycloak_session_expiry():
    """Detect Keycloak session expiry"""

    try:
        keycloak_token = st.session_state.get("access_token")
        if not keycloak_token:
            return {"status": "no_session", "action": "redirect_to_login"}

        # Decode without verification to check expiry
        payload = jwt.decode(keycloak_token, options={"verify_signature": False})

        current_time = int(time.time())
        exp_time = payload.get("exp", 0)

        if current_time >= exp_time:
            return {"status": "expired", "action": "redirect_to_login"}

        if current_time >= (exp_time - 300):  # 5 minutes buffer
            return {"status": "expiring_soon", "action": "attempt_refresh"}

        return {"status": "valid", "expires_in": exp_time - current_time}

    except Exception as e:
        return {"status": "invalid", "error": str(e), "action": "redirect_to_login"}
```

**Recovery Procedure**:
```python
async def recover_from_keycloak_expiry():
    """Recover from Keycloak session expiry"""

    # Step 1: Clear all downstream tokens
    clear_all_session_tokens()

    # Step 2: Redirect to Keycloak login
    keycloak_login_url = build_keycloak_login_url()

    # Step 3: Store recovery context for post-login restoration
    recovery_context = {
        "pre_expiry_user": st.session_state.get("canonical_username"),
        "active_page": st.session_state.get("current_page"),
        "pending_operations": get_pending_operations(),
        "timestamp": datetime.now().isoformat()
    }

    store_recovery_context(recovery_context)

    # Step 4: Initiate redirect
    st.session_state["auth_required"] = True
    st.session_state["keycloak_login_url"] = keycloak_login_url

    return {"status": "redirecting_to_login", "url": keycloak_login_url}

def clear_all_session_tokens():
    """Clear all tokens from session state"""
    tokens_to_clear = [
        "access_token",
        "api_token",
        "api_token_exp",
        "api_token_created",
        "canonical_username"
    ]

    for token_key in tokens_to_clear:
        st.session_state.pop(token_key, None)
```

### 2. JWT Secret Key Rotation

**Detection and Handling**:
```python
async def handle_jwt_secret_rotation():
    """Handle JWT secret key rotation across services"""

    rotation_steps = {
        "preparation": "Generate new JWT secret",
        "gradual_rollout": "Deploy new secret to services",
        "token_migration": "Migrate existing tokens",
        "cleanup": "Remove old secret"
    }

    rotation_status = {}

    # Step 1: Generate new JWT secret
    new_jwt_secret = generate_secure_jwt_secret()
    rotation_status["new_secret_generated"] = True

    # Step 2: Deploy to services in order
    deployment_order = ["fastapi", "streamlit", "apisix"]

    for service in deployment_order:
        try:
            await deploy_jwt_secret_to_service(service, new_jwt_secret)
            rotation_status[f"{service}_updated"] = True

            # Wait for service to restart/reload
            await wait_for_service_ready(service)

        except Exception as e:
            rotation_status[f"{service}_failed"] = str(e)
            # Rollback on failure
            await rollback_jwt_secret_rotation(deployment_order[:deployment_order.index(service)])
            raise

    # Step 3: Migrate existing tokens
    active_users = get_active_users()
    migration_results = []

    for user in active_users:
        try:
            # Generate new token with new secret
            user_context = get_user_context(user)
            new_token = create_jwt_token_with_secret(user_context, new_jwt_secret)

            # Update user session
            update_user_session_token(user, new_token)

            migration_results.append({"user": user, "status": "migrated"})

        except Exception as e:
            migration_results.append({"user": user, "status": "failed", "error": str(e)})

    rotation_status["user_migration"] = migration_results

    return rotation_status
```

### 3. APISIX Gateway Authentication Failure

**Detection**:
```bash
# Monitor APISIX authentication failures
tail -f apisix/logs/access.log | grep -E "(401|403)" | grep -v "health_check"

# Check APISIX gateway status
curl -s http://localhost:9080/health | jq '.status'
```

**Recovery Procedure**:
```python
async def recover_from_apisix_auth_failure():
    """Recover from APISIX gateway authentication failures"""

    # Step 1: Diagnose the failure
    diagnosis = await diagnose_apisix_auth_failure()

    if diagnosis["cause"] == "invalid_jwt_secret":
        # JWT secret mismatch between APISIX and other services
        await synchronize_jwt_secrets()

    elif diagnosis["cause"] == "expired_api_key":
        # APISIX API key expired or invalid
        await refresh_apisix_api_key()

    elif diagnosis["cause"] == "route_configuration":
        # APISIX route configuration issue
        await reconfigure_apisix_routes()

    # Step 2: Validate recovery
    validation_result = await validate_apisix_recovery()

    if validation_result["success"]:
        # Step 3: Notify users that service is restored
        await notify_service_restored("apisix_gateway")
    else:
        # Escalate to manual intervention
        await escalate_apisix_failure(diagnosis, validation_result)

    return {
        "diagnosis": diagnosis,
        "recovery_attempted": True,
        "validation": validation_result
    }

async def diagnose_apisix_auth_failure():
    """Diagnose APISIX authentication failure"""

    # Test JWT validation
    test_token = get_test_jwt_token()
    jwt_test = await test_apisix_jwt_validation(test_token)

    # Test API key validation
    api_key = os.getenv("VIOLENTUTF_API_KEY")
    api_key_test = await test_apisix_api_key(api_key)

    # Check route configuration
    route_config = await get_apisix_route_configuration()

    return {
        "jwt_validation": jwt_test,
        "api_key_validation": api_key_test,
        "route_configuration": route_config,
        "cause": determine_primary_cause(jwt_test, api_key_test, route_config)
    }
```

### 4. MCP OAuth 2.0 Token Failure

**Detection and Recovery**:
```python
async def recover_from_mcp_oauth_failure(user_context):
    """Recover from MCP OAuth 2.0 token failures"""

    recovery_strategies = [
        "refresh_token_flow",
        "re_authentication_flow",
        "fallback_authentication"
    ]

    for strategy in recovery_strategies:
        try:
            if strategy == "refresh_token_flow":
                result = await attempt_mcp_token_refresh(user_context)

            elif strategy == "re_authentication_flow":
                result = await re_authenticate_mcp_user(user_context)

            elif strategy == "fallback_authentication":
                result = await fallback_mcp_authentication(user_context)

            if result["status"] == "success":
                return {"recovery_strategy": strategy, "result": result}

        except Exception as e:
            logger.warning("MCP recovery strategy %s failed: %s", strategy, e)
            continue

    # All strategies failed
    return {"recovery_strategy": "none", "status": "failed", "action": "manual_intervention"}

async def attempt_mcp_token_refresh(user_context):
    """Attempt MCP token refresh using OAuth 2.0 refresh token"""

    refresh_token = get_mcp_refresh_token(user_context["username"])

    if not refresh_token:
        raise MCPRefreshTokenNotAvailable()

    # OAuth 2.0 refresh flow
    refresh_payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": MCP_CLIENT_ID,
        "client_secret": MCP_CLIENT_SECRET
    }

    response = await mcp_auth_client.post("/oauth/token", data=refresh_payload)

    if response.status_code == 200:
        token_data = response.json()

        # Store new tokens
        store_mcp_tokens(user_context["username"], token_data)

        return {
            "status": "success",
            "method": "refresh_token",
            "expires_in": token_data["expires_in"]
        }
    else:
        raise MCPTokenRefreshFailed(response.text)
```

## Monitoring and Validation

### Real-time Token Status Monitoring

```python
class TokenStatusMonitor:
    def __init__(self):
        self.monitoring_intervals = {
            "token_status_check": 60,  # Every minute
            "cascade_health_check": 300,  # Every 5 minutes
            "proactive_refresh_check": 600  # Every 10 minutes
        }

    async def monitor_token_cascade_health(self):
        """Monitor health of token cascade across all services"""

        health_report = {
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "users": {},
            "overall_health": "unknown"
        }

        # Check service-level token health
        services = ["keycloak", "streamlit", "apisix", "fastapi", "mcp"]

        for service in services:
            health_report["services"][service] = await self.check_service_token_health(service)

        # Check user-level token health
        active_users = get_active_users()

        for user in active_users:
            health_report["users"][user] = await self.check_user_token_health(user)

        # Determine overall health
        health_report["overall_health"] = self.calculate_overall_health(health_report)

        # Alert on issues
        if health_report["overall_health"] in ["degraded", "critical"]:
            await self.alert_token_cascade_issues(health_report)

        return health_report

    async def check_service_token_health(self, service):
        """Check token health for a specific service"""

        if service == "keycloak":
            return await self.check_keycloak_health()
        elif service == "streamlit":
            return await self.check_streamlit_token_health()
        elif service == "apisix":
            return await self.check_apisix_auth_health()
        elif service == "fastapi":
            return await self.check_fastapi_auth_health()
        elif service == "mcp":
            return await self.check_mcp_oauth_health()

    async def check_user_token_health(self, username):
        """Check token health for a specific user"""

        user_health = {
            "username": username,
            "tokens": {},
            "cascade_integrity": "unknown"
        }

        # Check Streamlit JWT
        jwt_status = get_user_jwt_status(username)
        user_health["tokens"]["streamlit_jwt"] = jwt_status

        # Check MCP OAuth if user has active session
        if has_active_mcp_session(username):
            mcp_status = get_user_mcp_token_status(username)
            user_health["tokens"]["mcp_oauth"] = mcp_status

        # Check cascade integrity
        user_health["cascade_integrity"] = self.validate_user_token_cascade(user_health["tokens"])

        return user_health

    def validate_user_token_cascade(self, user_tokens):
        """Validate that user's tokens are properly cascaded"""

        issues = []

        # Check token expiry synchronization
        jwt_expires = user_tokens.get("streamlit_jwt", {}).get("expires_at", 0)
        mcp_expires = user_tokens.get("mcp_oauth", {}).get("expires_at", 0)

        # MCP token should not outlive JWT token
        if mcp_expires > jwt_expires:
            issues.append("mcp_token_outlives_jwt")

        # Check token validity consistency
        jwt_valid = user_tokens.get("streamlit_jwt", {}).get("valid", False)
        mcp_valid = user_tokens.get("mcp_oauth", {}).get("valid", False)

        if mcp_valid and not jwt_valid:
            issues.append("mcp_valid_jwt_invalid")

        if len(issues) == 0:
            return "healthy"
        elif len(issues) <= 2:
            return "degraded"
        else:
            return "critical"
```

### Token Cascade Metrics

```python
class TokenCascadeMetrics:
    def __init__(self):
        self.metrics = {
            "refresh_success_rate": [],
            "cascade_latency": [],
            "token_lifetime_utilization": [],
            "failure_recovery_time": []
        }

    def record_refresh_event(self, event_type, duration, success):
        """Record token refresh event metrics"""

        timestamp = time.time()

        event_data = {
            "timestamp": timestamp,
            "event_type": event_type,  # "proactive", "reactive", "cascade"
            "duration_ms": duration * 1000,
            "success": success
        }

        if event_type == "cascade":
            self.metrics["cascade_latency"].append(event_data)

        self.metrics["refresh_success_rate"].append(event_data)

        # Calculate rolling success rate
        recent_events = [e for e in self.metrics["refresh_success_rate"]
                        if timestamp - e["timestamp"] < 3600]  # Last hour

        success_rate = sum(1 for e in recent_events if e["success"]) / len(recent_events) if recent_events else 1.0

        return {
            "current_success_rate": success_rate,
            "event_recorded": event_data
        }

    def get_cascade_performance_summary(self):
        """Get summary of cascade performance metrics"""

        current_time = time.time()
        last_24h = current_time - 86400

        # Filter recent metrics
        recent_refreshes = [e for e in self.metrics["refresh_success_rate"] if e["timestamp"] > last_24h]
        recent_cascades = [e for e in self.metrics["cascade_latency"] if e["timestamp"] > last_24h]

        return {
            "last_24h_summary": {
                "total_refresh_events": len(recent_refreshes),
                "successful_refreshes": sum(1 for e in recent_refreshes if e["success"]),
                "success_rate": sum(1 for e in recent_refreshes if e["success"]) / len(recent_refreshes) if recent_refreshes else 1.0,
                "cascade_events": len(recent_cascades),
                "avg_cascade_latency_ms": sum(e["duration_ms"] for e in recent_cascades) / len(recent_cascades) if recent_cascades else 0
            },
            "performance_indicators": self.calculate_performance_indicators(recent_refreshes, recent_cascades)
        }

    def calculate_performance_indicators(self, refresh_events, cascade_events):
        """Calculate key performance indicators"""

        if not refresh_events:
            return {"status": "insufficient_data"}

        success_rate = sum(1 for e in refresh_events if e["success"]) / len(refresh_events)
        avg_cascade_latency = sum(e["duration_ms"] for e in cascade_events) / len(cascade_events) if cascade_events else 0

        # Performance thresholds
        indicators = {
            "token_refresh_health": "healthy" if success_rate >= 0.95 else "degraded" if success_rate >= 0.8 else "critical",
            "cascade_performance": "healthy" if avg_cascade_latency < 1000 else "degraded" if avg_cascade_latency < 3000 else "critical",
            "overall_assessment": "healthy"
        }

        # Overall assessment is worst of individual indicators
        if any(status == "critical" for status in indicators.values()):
            indicators["overall_assessment"] = "critical"
        elif any(status == "degraded" for status in indicators.values()):
            indicators["overall_assessment"] = "degraded"

        return indicators
```

## Testing Framework

### Cascade Refresh Testing

```python
class TokenCascadeTestSuite:
    """Comprehensive test suite for token refresh cascade"""

    @pytest.mark.integration
    async def test_proactive_refresh_cascade(self):
        """Test proactive refresh cascade across all services"""

        # Setup: Create user with tokens near expiry
        test_user = "cascade_test_user"

        # Create tokens that will expire in 8 minutes (trigger proactive refresh)
        jwt_token = create_test_jwt_token(test_user, expires_in=480)  # 8 minutes
        mcp_token = create_test_mcp_token(test_user, expires_in=360)  # 6 minutes

        # Store tokens in session
        store_test_user_tokens(test_user, jwt_token, mcp_token)

        # Trigger proactive refresh check
        refresh_result = await trigger_proactive_refresh_check(test_user)

        # Verify cascade occurred
        assert refresh_result["triggered"] == True
        assert "streamlit_jwt" in refresh_result["refreshed_tokens"]
        assert "mcp_oauth" in refresh_result["refreshed_tokens"]

        # Verify new tokens have extended expiry
        new_jwt_status = get_user_jwt_status(test_user)
        new_mcp_status = get_user_mcp_token_status(test_user)

        assert new_jwt_status["expires_in"] > 1200  # > 20 minutes
        assert new_mcp_status["expires_in"] > 600   # > 10 minutes

        # Verify tokens are valid and consistent
        jwt_valid = await validate_jwt_token(new_jwt_status["token"])
        mcp_valid = await validate_mcp_token(new_mcp_status["token"])

        assert jwt_valid["valid"] == True
        assert mcp_valid["valid"] == True
        assert jwt_valid["user"] == mcp_valid["user"] == test_user

    @pytest.mark.integration
    async def test_reactive_refresh_cascade(self):
        """Test reactive refresh cascade on token expiry"""

        test_user = "reactive_test_user"

        # Create expired JWT token
        expired_jwt = create_test_jwt_token(test_user, expires_in=-300)  # Expired 5 minutes ago
        store_test_user_tokens(test_user, expired_jwt, None)

        # Attempt API operation that should trigger reactive refresh
        with pytest.raises(TokenExpiredError):
            await make_test_api_call(test_user)

        # Simulate Keycloak session still valid
        mock_valid_keycloak_session(test_user)

        # Trigger reactive refresh
        refresh_result = await trigger_reactive_refresh(test_user)

        # Verify refresh succeeded
        assert refresh_result["status"] == "success"
        assert refresh_result["new_jwt_token"] is not None

        # Verify API call now succeeds
        api_result = await make_test_api_call(test_user)
        assert api_result["status"] == "success"

    @pytest.mark.integration
    async def test_cascade_failure_recovery(self):
        """Test recovery from cascade refresh failures"""

        test_user = "failure_test_user"

        # Setup: Create user with expiring tokens
        jwt_token = create_test_jwt_token(test_user, expires_in=300)
        mcp_token = create_test_mcp_token(test_user, expires_in=180)
        store_test_user_tokens(test_user, jwt_token, mcp_token)

        # Simulate Keycloak failure during refresh
        with mock_keycloak_failure():
            refresh_result = await trigger_proactive_refresh_check(test_user)

            # Verify graceful failure handling
            assert refresh_result["status"] == "partial_failure"
            assert "keycloak_unavailable" in refresh_result["errors"]

        # Simulate recovery
        restore_keycloak_service()

        # Retry refresh
        recovery_result = await retry_failed_refresh(test_user)

        # Verify successful recovery
        assert recovery_result["status"] == "recovered"
        assert recovery_result["all_tokens_refreshed"] == True

    @pytest.mark.load
    async def test_concurrent_cascade_refresh(self):
        """Test cascade refresh under concurrent load"""

        # Create multiple users with tokens expiring soon
        test_users = [f"load_test_user_{i}" for i in range(50)]

        for user in test_users:
            jwt_token = create_test_jwt_token(user, expires_in=480)  # 8 minutes
            mcp_token = create_test_mcp_token(user, expires_in=360)  # 6 minutes
            store_test_user_tokens(user, jwt_token, mcp_token)

        # Trigger concurrent refresh for all users
        refresh_tasks = [trigger_proactive_refresh_check(user) for user in test_users]

        start_time = time.time()
        refresh_results = await asyncio.gather(*refresh_tasks, return_exceptions=True)
        end_time = time.time()

        # Verify performance under load
        total_duration = end_time - start_time
        assert total_duration < 30, "Concurrent refresh should complete within 30 seconds"

        # Verify success rate
        successful_refreshes = sum(1 for r in refresh_results if isinstance(r, dict) and r.get("status") == "success")
        success_rate = successful_refreshes / len(test_users)

        assert success_rate >= 0.95, "At least 95% of concurrent refreshes should succeed"

        # Verify no token conflicts
        for i, user in enumerate(test_users):
            if not isinstance(refresh_results[i], Exception):
                user_jwt = get_user_jwt_status(user)
                assert user_jwt["user"] == user, "Token should belong to correct user"
```

### Performance Testing

```python
class CascadePerformanceTests:
    """Performance testing for token cascade operations"""

    @pytest.mark.performance
    async def test_cascade_latency_requirements(self):
        """Test that cascade refresh meets latency requirements"""

        test_user = "performance_test_user"

        # Create tokens near expiry
        jwt_token = create_test_jwt_token(test_user, expires_in=300)
        mcp_token = create_test_mcp_token(test_user, expires_in=180)
        store_test_user_tokens(test_user, jwt_token, mcp_token)

        # Measure cascade refresh latency
        start_time = time.time()
        refresh_result = await trigger_proactive_refresh_check(test_user)
        end_time = time.time()

        cascade_latency = (end_time - start_time) * 1000  # Convert to milliseconds

        # Verify latency requirements
        assert cascade_latency < 2000, "Cascade refresh should complete within 2 seconds"
        assert refresh_result["status"] == "success"

        # Verify no performance degradation in API calls
        api_start = time.time()
        api_result = await make_test_api_call(test_user)
        api_end = time.time()

        api_latency = (api_end - api_start) * 1000
        assert api_latency < 500, "API calls should remain fast after cascade refresh"

    @pytest.mark.performance
    async def test_cascade_memory_usage(self):
        """Test memory usage during cascade refresh operations"""

        import psutil
        import gc

        process = psutil.Process()

        # Baseline memory usage
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform multiple cascade refreshes
        test_users = [f"memory_test_user_{i}" for i in range(20)]

        for user in test_users:
            jwt_token = create_test_jwt_token(user, expires_in=300)
            mcp_token = create_test_mcp_token(user, expires_in=180)
            store_test_user_tokens(user, jwt_token, mcp_token)

            await trigger_proactive_refresh_check(user)

        # Measure peak memory usage
        gc.collect()
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_increase = peak_memory - baseline_memory

        # Verify memory usage is reasonable
        assert memory_increase < 50, "Memory increase should be less than 50MB for 20 users"

        # Cleanup and verify memory is released
        for user in test_users:
            cleanup_test_user_tokens(user)

        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_leak = final_memory - baseline_memory
        assert memory_leak < 10, "Memory leak should be less than 10MB"
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Token Refresh Loops

**Symptoms**:
- Continuous token refresh attempts
- High CPU usage in authentication components
- Users experiencing authentication delays

**Diagnosis**:
```python
def diagnose_refresh_loops():
    """Diagnose token refresh loops"""

    recent_refreshes = get_recent_refresh_events(timeframe=300)  # Last 5 minutes

    user_refresh_counts = {}
    for event in recent_refreshes:
        user = event["user"]
        user_refresh_counts[user] = user_refresh_counts.get(user, 0) + 1

    # Identify users with excessive refreshes
    problematic_users = {user: count for user, count in user_refresh_counts.items() if count > 5}

    if problematic_users:
        return {
            "issue": "refresh_loops_detected",
            "affected_users": problematic_users,
            "total_refresh_events": len(recent_refreshes)
        }

    return {"issue": "none", "refresh_activity": "normal"}
```

**Solution**:
```python
async def fix_refresh_loops(affected_users):
    """Fix token refresh loops"""

    for user in affected_users:
        # Step 1: Clear all cached tokens
        clear_user_token_cache(user)

        # Step 2: Reset refresh timestamps
        reset_user_refresh_timestamps(user)

        # Step 3: Force full re-authentication
        force_user_reauthentication(user)

        # Step 4: Validate fix
        await asyncio.sleep(30)  # Wait for stabilization

        post_fix_refreshes = get_user_refresh_events(user, timeframe=300)

        if len(post_fix_refreshes) <= 2:
            logger.info("Refresh loop fixed for user %s", user)
        else:
            logger.error("Refresh loop persists for user %s", user)
```

#### 2. Cross-Service Token Sync Issues

**Symptoms**:
- API calls succeed in some services but fail in others
- Inconsistent user authentication state
- "Token not recognized" errors

**Diagnosis**:
```bash
# Check JWT secret consistency across services
echo "Checking JWT secrets..."

# Streamlit environment
grep "JWT_SECRET_KEY" violentutf/.env

# FastAPI environment
grep "JWT_SECRET_KEY" violentutf_api/fastapi_app/.env

# APISIX configuration
docker exec apisix-gateway env | grep JWT_SECRET_KEY

# Verify all secrets match
python3 -c "
import os
from pathlib import Path

secrets = {}

# Read from different locations
env_files = [
    'violentutf/.env',
    'violentutf_api/fastapi_app/.env'
]

for env_file in env_files:
    if Path(env_file).exists():
        with open(env_file) as f:
            for line in f:
                if 'JWT_SECRET_KEY=' in line:
                    secret = line.strip().split('=', 1)[1]
                    secrets[env_file] = secret[:8] + '...'
                    break

print('JWT Secret previews:')
for location, preview in secrets.items():
    print(f'{location}: {preview}')

if len(set(secrets.values())) == 1:
    print('✓ All secrets match')
else:
    print('✗ Secret mismatch detected')
"
```

**Solution**:
```bash
# Synchronize JWT secrets across all services
#!/bin/bash

# Generate new shared JWT secret
NEW_JWT_SECRET=$(openssl rand -base64 64)

echo "Updating JWT secret across all services..."

# Update Streamlit .env
sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=${NEW_JWT_SECRET}/" violentutf/.env

# Update FastAPI .env
sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=${NEW_JWT_SECRET}/" violentutf_api/fastapi_app/.env

# Update APISIX environment
docker exec apisix-gateway env JWT_SECRET_KEY="${NEW_JWT_SECRET}"

# Restart services to pick up new secret
docker-compose restart apisix-gateway fastapi

echo "JWT secret synchronized. Restarting Streamlit..."
# Streamlit restart needed manually
```

#### 3. MCP OAuth Token Issues

**Symptoms**:
- MCP operations fail with authentication errors
- "OAuth token expired" messages
- MCP server connection failures

**Diagnosis**:
```python
async def diagnose_mcp_oauth_issues(username):
    """Diagnose MCP OAuth token issues"""

    diagnosis = {
        "user": username,
        "mcp_token_status": "unknown",
        "oauth_flow_status": "unknown",
        "server_connectivity": "unknown"
    }

    # Check token status
    mcp_token = get_mcp_token(username)
    if mcp_token:
        diagnosis["mcp_token_status"] = "present"

        if is_token_expired(mcp_token):
            diagnosis["mcp_token_status"] = "expired"
        else:
            diagnosis["mcp_token_status"] = "valid"
    else:
        diagnosis["mcp_token_status"] = "missing"

    # Check OAuth flow
    refresh_token = get_mcp_refresh_token(username)
    if refresh_token:
        try:
            test_refresh = await test_oauth_refresh(refresh_token)
            diagnosis["oauth_flow_status"] = "working" if test_refresh["success"] else "failing"
        except Exception as e:
            diagnosis["oauth_flow_status"] = f"error: {e}"
    else:
        diagnosis["oauth_flow_status"] = "no_refresh_token"

    # Check server connectivity
    try:
        mcp_health = await check_mcp_server_health()
        diagnosis["server_connectivity"] = "healthy" if mcp_health["status"] == "ok" else "degraded"
    except Exception as e:
        diagnosis["server_connectivity"] = f"error: {e}"

    return diagnosis
```

**Solution**:
```python
async def fix_mcp_oauth_issues(username, diagnosis):
    """Fix MCP OAuth issues based on diagnosis"""

    if diagnosis["mcp_token_status"] in ["missing", "expired"]:
        if diagnosis["oauth_flow_status"] == "working":
            # Try refresh flow
            refresh_result = await refresh_mcp_token(username)
            if refresh_result["status"] == "success":
                return {"fix": "token_refreshed", "status": "resolved"}

        # Fall back to re-authentication
        auth_result = await re_authenticate_mcp_user(username)
        if auth_result["status"] == "success":
            return {"fix": "re_authenticated", "status": "resolved"}

    elif diagnosis["server_connectivity"] != "healthy":
        # Server issue, wait and retry
        await asyncio.sleep(10)
        retry_result = await retry_mcp_connection(username)
        return {"fix": "server_retry", "status": retry_result["status"]}

    return {"fix": "none", "status": "unresolved", "action": "manual_intervention"}
```

### Emergency Procedures

#### Complete Token System Reset

```bash
#!/bin/bash
# emergency_token_reset.sh

echo "EMERGENCY: Resetting complete token system"

# 1. Stop all services
docker-compose down

# 2. Clear all token caches
rm -rf ./app_data/violentutf/token_cache/*
rm -rf ./violentutf_api/fastapi_app/token_cache/*

# 3. Generate new JWT secret
NEW_JWT_SECRET=$(openssl rand -base64 64)

# 4. Update all configuration files
echo "JWT_SECRET_KEY=${NEW_JWT_SECRET}" > violentutf/.env.new
echo "JWT_SECRET_KEY=${NEW_JWT_SECRET}" > violentutf_api/fastapi_app/.env.new

# 5. Backup old configs and replace
mv violentutf/.env violentutf/.env.backup
mv violentutf_api/fastapi_app/.env violentutf_api/fastapi_app/.env.backup
mv violentutf/.env.new violentutf/.env
mv violentutf_api/fastapi_app/.env.new violentutf_api/fastapi_app/.env

# 6. Restart services
docker-compose up -d

# 7. Wait for services to be ready
./wait_for_services.sh

# 8. Clear all user sessions (forces re-authentication)
python3 -c "
import streamlit as st
import glob
import os

# Clear Streamlit session files
session_files = glob.glob('./.streamlit/session_state/*')
for session_file in session_files:
    os.remove(session_file)

print('All user sessions cleared. Users will need to re-authenticate.')
"

echo "Emergency token reset complete. All users must re-authenticate."
```

## Conclusion

This comprehensive JWT Token Refresh Cascade documentation provides enterprise-grade procedures for maintaining seamless authentication across ViolentUTF's multi-service architecture. The cascading refresh system ensures that long-running security testing operations can continue uninterrupted while maintaining proper security boundaries.

Key benefits:
- **Seamless User Experience**: Proactive refresh prevents authentication interruptions
- **Security Compliance**: Regular token rotation maintains security posture
- **Operational Resilience**: Comprehensive failure recovery procedures
- **Performance Optimization**: Efficient cascade algorithms minimize latency
- **Monitoring Visibility**: Real-time token health monitoring and alerting

The procedures are designed to handle both normal operations and emergency scenarios, ensuring the authentication system remains robust and reliable as the platform scales.
