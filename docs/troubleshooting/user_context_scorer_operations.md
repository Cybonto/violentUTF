# User Context Analysis for Scorer Operations

## Issue Summary

Inconsistent user identification across the ViolentUTF system is causing data isolation issues, particularly affecting scorer operations (creation, listing, deletion).

## Root Cause Analysis

### 1. **Username Inconsistency**
The system is using different identifiers for the same user across different operations:
- **Keycloak SSO**: Uses `preferred_username` (e.g., "violentutf.web") as the account name
- **Display Name**: Sometimes "Tam Nguyen" is used as a display name
- **JWT Tokens**: Should use `sub` claim (username) but sometimes inconsistent

### 2. **User Context Flow**

#### Streamlit Side (Token Creation)
```python
# violentutf/utils/user_context.py
def get_consistent_username() -> str:
    # Priority:
    # 1. Keycloak preferred_username from SSO token
    # 2. Environment variable KEYCLOAK_USERNAME
    # 3. Default fallback
    
    if "access_token" in st.session_state:
        payload = jwt.decode(st.session_state["access_token"], options={"verify_signature": False})
        preferred_username = payload.get("preferred_username")  # e.g., "violentutf.web"
        if preferred_username:
            return preferred_username
    return os.getenv("KEYCLOAK_USERNAME", "violentutf.web")
```

#### JWT Token Creation
```python
# violentutf/utils/jwt_manager.py
def create_token(self, keycloak_token_data: Dict[str, Any]) -> Optional[str]:
    # ALWAYS use preferred_username as the unique identifier
    username = keycloak_token_data.get("preferred_username") or keycloak_token_data.get("sub", "user")
    
    payload = {
        "sub": username,  # This is what FastAPI will use
        "username": username,
        "email": email,
        # ...
    }
```

#### FastAPI Side (User Extraction)
```python
# violentutf_api/fastapi_app/app/core/auth.py
async def _authenticate_jwt(self, token: str) -> User:
    payload = decode_token(token)
    username = payload.get("sub")  # Always uses 'sub' claim
    
    # IMPORTANT: Always use 'sub' claim as username, never 'name' or 'display_name'
    user = User(username=username, ...)
    return user
```

#### DuckDB Operations
```python
# violentutf_api/fastapi_app/app/db/duckdb_manager.py
class DuckDBManager:
    def __init__(self, username: str, ...):
        self.username = username  # This determines data isolation
        
    def create_scorer(self, name: str, scorer_type: str, parameters: Dict[str, Any]) -> str:
        # Inserts with user_id = self.username
        conn.execute("""
            INSERT INTO scorers (id, name, type, parameters, user_id)
            VALUES (?, ?, ?, ?, ?)
        """, [scorer_id, name, scorer_type, json.dumps(parameters), self.username])
```

### 3. **Identified Issues**

1. **Display Name vs Account Name**: If Keycloak is configured with a display name (e.g., "Tam Nguyen") different from the account name (e.g., "violentutf.web"), data might be stored under the wrong user context.

2. **Token Inconsistency**: If JWT tokens are created with different user identifiers at different times, operations will fail to find previously created items.

3. **Hardcoded Defaults**: Some places in the code have hardcoded "violentutf.web" as a fallback, which can mask the real issue.

## Current Implementation Safeguards

1. **Consistent Username Function**: `get_consistent_username()` ensures the same username is used across all Streamlit pages.

2. **JWT Manager**: Always uses `preferred_username` from Keycloak as the primary identifier.

3. **FastAPI Auth**: Correctly extracts username from `sub` claim and warns about deprecated fields.

4. **Migration Tools**: Scripts exist to migrate data between user contexts if needed.

## Recommendations

### 1. **Immediate Fix**
If experiencing scorer operation issues:
```bash
# Check which user contexts have data
cd violentutf_api/fastapi_app
python diagnose_user_context.py

# If data is under wrong user, migrate it
python migrate_user_context.py --from "Display Name" --to "violentutf.web"
```

### 2. **Configuration Check**
Ensure Keycloak is configured consistently:
- Account name (preferred_username) should be "violentutf.web"
- Display name can be different but won't be used for data isolation

### 3. **Debugging Steps**
1. Check JWT token contents:
   ```python
   import jwt
   token = st.session_state.get("api_token")
   payload = jwt.decode(token, options={"verify_signature": False})
   print(f"Token username (sub): {payload.get('sub')}")
   ```

2. Verify DuckDB username:
   ```python
   from app.db.duckdb_manager import get_duckdb_manager
   db = get_duckdb_manager(current_user.username)
   print(f"DuckDB username: {db.username}")
   ```

### 4. **Long-term Solution**
- Enforce consistent username usage across all components
- Add validation to ensure username consistency
- Consider adding user ID mapping table to handle display names separately

## Testing Scorer Operations

To verify scorer operations are working correctly:

1. **Create a scorer** through the Streamlit UI
2. **List scorers** - should see the created scorer
3. **Delete the scorer** - should succeed
4. **List again** - scorer should be gone

If any step fails, check:
- JWT token username matches expected value
- DuckDB is using the same username for all operations
- No display name/account name confusion

## Code References

- User context: `violentutf/utils/user_context.py`
- JWT creation: `violentutf/utils/jwt_manager.py`
- FastAPI auth: `violentutf_api/fastapi_app/app/core/auth.py`
- DuckDB operations: `violentutf_api/fastapi_app/app/db/duckdb_manager.py`
- Scorer endpoints: `violentutf_api/fastapi_app/app/api/endpoints/scorers.py`
- Migration script: `violentutf_api/fastapi_app/migrate_user_context.py`
- Diagnostic script: `violentutf_api/fastapi_app/diagnose_user_context.py`