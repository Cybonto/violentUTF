# Database Switching Issue Analysis

## Problem Summary

In the Enterprise environment, after sending approximately 1500 prompts and waiting ~10 minutes, the ViolentUTF application switches to a new database file where configured scorers, generators, and other data are no longer visible.

## Root Cause Analysis

After examining the codebase, I've identified the **primary cause** of the database switching issue:

### 1. **Orchestrator Instance Recreation with New Database Files**

The issue occurs in the `pyrit_orchestrator_service.py` file where each orchestrator instance creates its own database file:

```python
# In create_orchestrator_instance (line 166):
api_memory_file = os.path.join(api_memory_dir, f"orchestrator_memory_{orchestrator_id[:8]}.db")
api_memory = DuckDBMemory(db_path=api_memory_file)
CentralMemory.set_memory_instance(api_memory)
```

**Critical Issue**: Every time a new orchestrator is created, it:
1. Creates a new database file named `orchestrator_memory_{orchestrator_id[:8]}.db`
2. Sets this as the global CentralMemory instance
3. All subsequent operations use this NEW database file
4. The previous database file (with user configurations) is abandoned

### 2. **Orchestrator Lifecycle Management**

The orchestrator instances are stored in memory but are not persistent:

```python
# In PyRITOrchestratorService.__init__:
self._orchestrator_instances: Dict[str, Orchestrator] = {}
```

When orchestrator instances are garbage collected or the service restarts, they need to be recreated from the database. However, the recreation process creates a NEW database file each time.

### 3. **Database File Proliferation**

Over time, the system creates multiple database files:
- `orchestrator_memory_12345678.db` (from first orchestrator)
- `orchestrator_memory_87654321.db` (from second orchestrator)  
- `orchestrator_memory_abcdef12.db` (from third orchestrator)
- etc.

Each switch to a new orchestrator means switching to a new database file, losing access to previous configurations.

## Timeline of the Issue

1. **Initial State**: User creates generators, scorers, datasets in the first database file
2. **~1500 Prompts**: Memory pressure or timeout causes orchestrator instance cleanup
3. **~10 Minutes**: Background processes or new requests trigger orchestrator recreation
4. **Database Switch**: New orchestrator creates new database file and sets it as global memory
5. **Data Loss**: Previous configurations are no longer accessible

## Code Evidence

### A. Orchestrator Database Creation Logic
```python
# violentutf_api/fastapi_app/app/services/pyrit_orchestrator_service.py:166
api_memory_file = os.path.join(api_memory_dir, f"orchestrator_memory_{orchestrator_id[:8]}.db")
api_memory = DuckDBMemory(db_path=api_memory_file)
CentralMemory.set_memory_instance(api_memory)  # ⚠️ OVERWRITES GLOBAL MEMORY
```

### B. User-Specific Database Logic
```python
# violentutf_api/fastapi_app/app/services/dataset_integration_service.py:248
salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")
user_hash = hashlib.sha256((salt + user_id).encode("utf-8")).hexdigest()
user_db_filename = f"pyrit_memory_{user_hash}.db"  # ⚠️ DIFFERENT NAMING PATTERN
```

### C. DuckDB Manager User-Specific Logic
```python
# violentutf_api/fastapi_app/app/db/duckdb_manager.py:51
hashed_username = hashlib.sha256(salt_bytes + self.username.encode("utf-8")).hexdigest()
return f"pyrit_memory_{hashed_username}.db"  # ⚠️ FULL HASH, NOT TRUNCATED
```

## Contributing Factors

### 1. **Inconsistent Database Naming**
- Orchestrator service: `orchestrator_memory_{orchestrator_id[:8]}.db` (8 chars)
- User service: `pyrit_memory_{user_hash}.db` (full hash)
- DuckDB manager: `pyrit_memory_{hashed_username}.db` (full hash)

### 2. **Global Memory Instance Overwriting**
```python
CentralMemory.set_memory_instance(api_memory)
```
This overwrites the global memory instance, affecting all subsequent operations.

### 3. **No Orchestrator Instance Pooling**
Each orchestrator is created fresh instead of reusing existing instances, leading to frequent database file creation.

### 4. **Memory Pressure and Garbage Collection**
After processing ~1500 prompts, memory pressure likely triggers cleanup of orchestrator instances, forcing recreation.

## Impact Assessment

### Data Affected
- Generator configurations
- Scorer configurations  
- Dataset configurations
- Previous test results
- User session data

### Operations Affected
- Configure Generators page shows empty list
- Configure Scorers page shows empty list
- Dashboard shows no historical data
- API calls fail to find previously configured resources

## Immediate Fixes

### 1. **Use Consistent Database Path**
```python
# Instead of creating new files, use consistent user-specific path
def get_user_memory_path(user_id: str) -> str:
    salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")
    user_hash = hashlib.sha256((salt + user_id).encode("utf-8")).hexdigest()
    return f"/app/app_data/violentutf/pyrit_memory_{user_hash}.db"
```

### 2. **Implement Database Connection Pooling**
```python
class DatabaseConnectionManager:
    def __init__(self):
        self._connections = {}
        self._lock = asyncio.Lock()
    
    async def get_connection(self, db_path: str):
        async with self._lock:
            if db_path not in self._connections:
                self._connections[db_path] = DuckDBMemory(db_path=db_path)
            return self._connections[db_path]
```

### 3. **Implement Orchestrator Instance Pooling**
```python
class OrchestratorPool:
    def __init__(self, max_instances: int = 10):
        self._pool = {}
        self._max_instances = max_instances
    
    def get_or_create(self, config: Dict) -> Orchestrator:
        key = self._get_config_key(config)
        if key in self._pool:
            return self._pool[key]
        # Create new instance only if needed
```

## Long-term Solutions

### 1. **Centralized Memory Management**
Create a single memory management service that ensures all operations use the same database file per user.

### 2. **Database Migration Strategy**
Implement a migration strategy to consolidate data from multiple database files into a single user-specific file.

### 3. **Health Monitoring**
Add monitoring to detect when database switching occurs and alert administrators.

### 4. **Session Persistence**
Ensure orchestrator instances persist across requests and are properly cleaned up only when explicitly terminated.

## Testing Recommendations

1. **Load Testing**: Test with sustained load of 1500+ prompts
2. **Memory Monitoring**: Monitor memory usage during extended operations
3. **Database File Monitoring**: Track creation of new database files
4. **Orchestrator Lifecycle Testing**: Test orchestrator creation/destruction patterns

## Conclusion

The database switching issue is caused by the orchestrator service creating new database files for each orchestrator instance instead of reusing existing user-specific database files. This causes data loss when orchestrator instances are recreated after memory pressure or timeouts.

The fix requires implementing consistent database path management, connection pooling, and orchestrator instance pooling to ensure data persistence across the application lifecycle.