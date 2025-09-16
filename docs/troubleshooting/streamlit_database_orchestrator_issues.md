# Streamlit Database and Orchestrator Management Issues

## Summary of Findings

Based on the code examination, there are several issues with how Streamlit pages manage database connections and orchestrators that can lead to the problems described:

1. **Database File Path Determination Issues**
2. **Orchestrator Instance Management Problems**
3. **Session State and Instance Persistence**
4. **Concurrency and Race Conditions**

## 1. Database File Path Determination

### Issue: User-Specific Database Files with Hashing

The system uses user-specific database files with hashed names to isolate data between users:

```python
# From dataset_integration_service.py
salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")
user_hash = hashlib.sha256((salt + user_id).encode("utf-8")).hexdigest()
user_db_filename = f"pyrit_memory_{user_hash}.db"
```

**Problem**: The hashing mechanism means:
- Different user contexts (e.g., "admin" vs canonical username) could generate different hashes
- This leads to looking for the wrong database file
- Results in "no data found" even when data exists

### Issue: Multiple Database Locations

The system checks multiple locations for database files:

```python
potential_paths = [
    "/app/app_data/violentutf",  # Docker API memory
    "./app_data/violentutf",      # Relative app data
]
```

**Problem**:
- Streamlit and API service may use different paths
- Database files created in one location might not be found by another service

## 2. Orchestrator Instance Management

### Issue: Orchestrator Recreation vs Reuse

From `pyrit_orchestrator_service.py`:

```python
async def execute_orchestrator(self, orchestrator_id: str, execution_config: Dict[str, Any]) -> Dict[str, Any]:
    # Check if orchestrator instance exists in memory
    if orchestrator_id not in self._orchestrator_instances:
        # Try to reload orchestrator from database
        logger.info(f"Orchestrator {orchestrator_id} not in memory, attempting to reload from database")
        success = await self._reload_orchestrator_from_db(orchestrator_id, user_context)
```

**Problem**:
- Orchestrators are recreated when not found in memory
- Each recreation creates a new database connection
- This can lead to database locking issues with SQLite/DuckDB

### Issue: API Service Creates Separate Memory Instances

```python
# From pyrit_orchestrator_service.py
if memory is None:
    # Create API-specific memory if needed
    api_memory_dir = os.path.join("/app/app_data/violentutf", "api_memory")
    api_memory_file = os.path.join(api_memory_dir, f"orchestrator_memory_{orchestrator_id[:8]}.db")
    api_memory = DuckDBMemory(db_path=api_memory_file)
```

**Problem**:
- API service creates its own memory instances to avoid conflicts
- These are separate from Streamlit's memory instances
- Data written by one may not be visible to the other

## 3. Session State Management

### Issue: No Orchestrator Instance Caching in Streamlit

The Configure Scorer page doesn't maintain orchestrator instances between executions:

```python
# Each test creates a new orchestrator
orchestrator_response = api_request("POST", API_ENDPOINTS["orchestrator_create"], json=orchestrator_payload)
```

**Problem**:
- Every test execution creates a new orchestrator
- No reuse of existing orchestrators
- Leads to resource exhaustion and database connection issues

## 4. Concurrency and Timing Issues

### Issue: Database Lock Contention

DuckDB and SQLite have limitations with concurrent access:
- DuckDB allows only one writer at a time
- SQLite has similar restrictions
- Multiple orchestrator instances trying to access the same database file can cause conflicts

### Issue: Asynchronous Operations Without Proper Synchronization

The code uses async operations but doesn't properly synchronize database access:

```python
# Multiple async operations may try to access the database simultaneously
results = await orchestrator.send_prompts_async(...)
```

## Root Causes

1. **User Context Inconsistency**: Different parts of the system may use different user identifiers (e.g., "admin" vs full username), leading to different database file lookups.

2. **Database Isolation Strategy**: The user-specific database approach with hashing makes debugging difficult and can lead to "lost" data when user context changes.

3. **No Connection Pooling**: Each orchestrator creates its own database connection without proper pooling or reuse.

4. **Lack of Central Memory Management**: Streamlit and API services manage memory independently, leading to conflicts.

## Recommendations

### 1. Implement Consistent User Context

Create a centralized user context management system that ensures the same user identifier is used throughout:

```python
class UserContextManager:
    @staticmethod
    def get_canonical_username(user_info: Dict[str, Any]) -> str:
        # Always return the same username format
        return user_info.get("preferred_username", user_info.get("username", "unknown"))
```

### 2. Implement Orchestrator Instance Pooling

Create a pool of orchestrator instances that can be reused:

```python
class OrchestratorPool:
    def __init__(self, max_instances: int = 10):
        self._pool = {}
        self._max_instances = max_instances

    def get_or_create(self, config: Dict) -> Orchestrator:
        # Reuse existing instance or create new one
        key = self._get_config_key(config)
        if key in self._pool:
            return self._pool[key]
        # Create new instance with proper cleanup of old ones
```

### 3. Use Shared Memory Path Configuration

Ensure all services use the same memory path:

```python
def get_shared_memory_path() -> str:
    # Use environment variable with consistent default
    return os.getenv("VIOLENTUTF_MEMORY_PATH", "/app/app_data/violentutf/shared_memory")
```

### 4. Implement Database Connection Management

Use a connection manager to prevent concurrent access issues:

```python
class DatabaseConnectionManager:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._connections = {}

    async def get_connection(self, db_path: str):
        async with self._lock:
            # Ensure only one connection per database file
            if db_path not in self._connections:
                self._connections[db_path] = await self._create_connection(db_path)
            return self._connections[db_path]
```

### 5. Add Debugging and Monitoring

Add comprehensive logging to track:
- User context changes
- Database file paths being used
- Orchestrator instance creation/reuse
- Database connection lifecycle

```python
logger.info(f"User context: {user_context}, DB path: {db_path}, Orchestrator ID: {orch_id}")
```

## Immediate Workarounds

1. **Clear Session State**: Add a button to clear Streamlit session state and force recreation of connections.

2. **Use Single User Mode**: For testing, use a fixed user context to avoid hashing issues.

3. **Increase Timeouts**: Add longer timeouts for database operations to handle lock contention.

4. **Manual Database Path**: Add an environment variable to override automatic path determination.

## Testing Recommendations

1. Test with multiple concurrent users to identify race conditions
2. Monitor database file creation and access patterns
3. Add integration tests that verify data persistence across service boundaries
4. Implement health checks for database connections

## Conclusion

The issues stem from a combination of user context management, database isolation strategies, and lack of proper connection pooling. The system needs a more centralized approach to memory management and better coordination between Streamlit and API services.
