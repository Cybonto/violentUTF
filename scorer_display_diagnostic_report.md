# Scorer Display Issue Diagnostic Report

## Problem Statement
8 scorers exist in the database (confirmed by check_api_scorers.py) but they don't appear in the Streamlit UI after page refresh.

## Root Cause Analysis

### 1. User Context Inconsistency
Based on the documentation in `docs/guides/user_context_standardization.md` and `docs/troubleshooting/user_context_scorer_operations.md`, the primary issue is **inconsistent user identification** across the system.

**Key Finding**: Different username formats are being used:
- Keycloak SSO: `violentutf.web`
- Display Name: `Tam Nguyen` or `ViolentUTF Web User`
- Email format: `tam.nguyen@protonmail.com`

This causes data fragmentation where scorers are stored under different user contexts in the database.

### 2. API Response Chain

The API response chain works as follows:

1. **Streamlit Page Load** (`4_Configure_Scorers.py`):
   ```python
   # Line 255-262: Load scorers from API
   def load_scorers_from_api():
       data = api_request("GET", API_ENDPOINTS["scorers"])
       if data:
           scorers_dict = {scorer["name"]: scorer for scorer in data.get("scorers", [])}
           st.session_state.api_scorers = scorers_dict
   ```

2. **API Request** (with authentication):
   ```python
   # Line 112-203: API request with auth headers
   def api_request(method: str, url: str, **kwargs):
       headers = get_auth_headers()  # Gets JWT token
   ```

3. **FastAPI Endpoint** (`scorers.py`):
   ```python
   # Line 393-451: List scorers
   async def list_scorers(current_user=Depends(get_current_user)):
       user_id = current_user.username
       db_manager = get_duckdb_manager(user_id)
       scorers_data = db_manager.list_scorers()
   ```

4. **Database Query** (`duckdb_manager.py`):
   ```python
   # Line 639-662: List scorers for user
   def list_scorers(self):
       results = conn.execute("""
           SELECT ... FROM scorers WHERE user_id = ? ORDER BY created_at DESC
       """, [self.username])
   ```

### 3. Potential Issues Identified

1. **Username Mismatch**: The username in the JWT token might not match the username stored in the database
2. **Token Creation**: The Streamlit page creates tokens using `UserContextManager.get_user_context_for_token()`
3. **Token Extraction**: FastAPI extracts username from token using `current_user.username`
4. **Database Isolation**: DuckDB queries filter by `user_id = self.username`

## Diagnostic Scripts Created

### 1. `test_scorer_api_chain.py`
Comprehensive test that:
- Checks database files for different username formats
- Tests JWT token creation and normalization
- Verifies API authentication
- Tests the scorers endpoint with different tokens
- Simulates Streamlit's API call

### 2. `verify_streamlit_scorer_api.py`
Verifies Streamlit -> API communication:
- Shows expected API call sequence
- Tests direct API access
- Provides troubleshooting steps
- Tests scorer creation

### 3. `check_scorer_auth_issues.py`
Focuses on authentication issues:
- Checks environment configuration
- Analyzes token lifecycle
- Verifies database access patterns
- Tests API with different user contexts

## Recommended Solutions

### Immediate Fix
1. **Run the diagnostic script**:
   ```bash
   python test_scorer_api_chain.py
   ```
   This will identify the exact username mismatch.

2. **Check current user context**:
   ```bash
   cd violentutf_api/fastapi_app
   python check_api_scorers.py
   ```
   Note the "Checking user" output.

3. **If username mismatch is found**, the system has a user context standardization solution implemented. Ensure:
   - Both Streamlit and FastAPI use the same normalization rules
   - The `UserContextManager` classes are properly configured

### Long-term Solution
1. **Implement consistent user normalization** across all components
2. **Add debug logging** to trace user context through the entire flow
3. **Consider adding a user mapping table** to handle different username formats

## Testing the Fix

After applying fixes:

1. **Clear and restart**:
   ```bash
   # Stop all services
   docker-compose down

   # Clear problematic data (optional)
   rm ./app_data/violentutf/pyrit_memory_*.db

   # Restart
   ./launch_violentutf.sh
   ```

2. **Create a test scorer** through the UI

3. **Verify it appears** after page refresh

4. **Run diagnostic again** to confirm fix:
   ```bash
   python test_scorer_api_chain.py
   ```

## Additional Notes

- The system already has user context managers implemented to handle this issue
- The fix involves ensuring these managers are used consistently
- No code changes to the API endpoints or database layer should be needed
- The issue is primarily about ensuring the correct username format is used throughout
