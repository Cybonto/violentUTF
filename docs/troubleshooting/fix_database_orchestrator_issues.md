# Implementation Guide: Fixing Database and Orchestrator Issues

## Overview

This guide provides concrete implementation steps to fix the database connection and orchestrator management issues in ViolentUTF.

## Phase 1: Immediate Fixes (Quick Wins)

### 1.1 Fix User Context Consistency

**File**: `violentutf/utils/user_context_manager.py` (new file)

```python
"""Centralized user context management for consistent database access"""
import hashlib
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class UserContextManager:
    """Ensures consistent user identification across all services"""
    
    @staticmethod
    def get_canonical_username(session_state: Dict[str, Any]) -> str:
        """Get consistent username from session state"""
        # Priority order for username resolution
        if "user_info" in session_state:
            user_info = session_state["user_info"]
            # Try multiple fields in order of preference
            username = (
                user_info.get("preferred_username") or
                user_info.get("username") or
                user_info.get("email", "").split("@")[0] or
                "unknown_user"
            )
        elif "username" in session_state:
            username = session_state["username"]
        else:
            username = "unknown_user"
        
        # Normalize username (lowercase, no spaces)
        username = username.lower().strip().replace(" ", "_")
        logger.debug(f"Canonical username resolved: {username}")
        return username
    
    @staticmethod
    def get_user_db_path(username: str) -> str:
        """Get consistent database path for user"""
        # Use consistent salt from environment
        salt = os.getenv("PYRIT_DB_SALT", "violentutf_salt_2025")
        
        # Create consistent hash
        user_hash = hashlib.sha256(f"{salt}:{username}".encode()).hexdigest()[:16]
        
        # Use shared memory directory
        memory_dir = os.getenv("VIOLENTUTF_MEMORY_DIR", "/app/app_data/violentutf/memory")
        os.makedirs(memory_dir, exist_ok=True)
        
        db_path = os.path.join(memory_dir, f"pyrit_memory_{user_hash}.db")
        logger.info(f"User DB path for {username}: {db_path}")
        return db_path
```

### 1.2 Update Configure Scorer Page

**File**: `violentutf/pages/4_Configure_Scorers.py` (modifications)

Add at the top:
```python
from utils.user_context_manager import UserContextManager
```

Update the `create_compatible_api_token` function:
```python
def create_compatible_api_token():
    """Create a FastAPI-compatible token using JWT manager with consistent user context"""
    try:
        from utils.jwt_manager import jwt_manager
        
        # Use centralized user context manager
        canonical_username = UserContextManager.get_canonical_username(st.session_state)
        
        # Create consistent user context
        user_context = {
            "sub": canonical_username,
            "username": canonical_username,
            "preferred_username": canonical_username,
            "email": f"{canonical_username}@violentutf.local"
        }
        
        logger.info(f"Creating API token for canonical user: {canonical_username}")
        
        # Create token with canonical user context
        api_token = jwt_manager.create_token(user_context)
        
        if api_token:
            st.session_state["api_token"] = api_token
            st.session_state["canonical_username"] = canonical_username
            return api_token
        else:
            st.error("🚨 Security Error: JWT secret key not configured.")
            return None
            
    except Exception as e:
        st.error("❌ Failed to generate API token.")
        logger.error(f"Token creation failed: {e}")
        return None
```

### 1.3 Add Session State Debugging

**File**: `violentutf/pages/4_Configure_Scorers.py` (add to sidebar)

```python
# Add to the sidebar (in handle_authentication_and_sidebar)
with st.sidebar:
    with st.expander("🔧 Debug Info", expanded=False):
        if st.button("🔄 Clear Cache & Refresh"):
            st.cache_data.clear()
            st.session_state.clear()
            st.rerun()
        
        st.caption("Current User Context:")
        canonical_user = UserContextManager.get_canonical_username(st.session_state)
        st.code(canonical_user)
        
        st.caption("Database Path:")
        db_path = UserContextManager.get_user_db_path(canonical_user)
        st.code(db_path)
        
        if os.path.exists(db_path):
            st.success("✅ Database file exists")
            file_size = os.path.getsize(db_path) / 1024 / 1024  # MB
            st.caption(f"Size: {file_size:.2f} MB")
        else:
            st.warning("⚠️ Database file not found")
```

## Phase 2: Orchestrator Management Improvements

### 2.1 Create Orchestrator Pool

**File**: `violentutf_api/fastapi_app/app/services/orchestrator_pool.py` (new file)

```python
"""Orchestrator instance pooling for better resource management"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from collections import OrderedDict

logger = logging.getLogger(__name__)

class OrchestratorPool:
    """Manages a pool of orchestrator instances for reuse"""
    
    def __init__(self, max_instances: int = 20, ttl_minutes: int = 30):
        self._pool: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._max_instances = max_instances
        self._ttl = timedelta(minutes=ttl_minutes)
        self._lock = asyncio.Lock()
    
    def _get_pool_key(self, config: Dict[str, Any]) -> str:
        """Generate unique key for orchestrator configuration"""
        import json
        import hashlib
        
        # Create deterministic key from config
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    async def get_or_create(self, orchestrator_id: str, config: Dict[str, Any], 
                           create_func) -> Any:
        """Get existing orchestrator or create new one"""
        async with self._lock:
            # Check if orchestrator exists and is not expired
            if orchestrator_id in self._pool:
                entry = self._pool[orchestrator_id]
                if datetime.now() - entry["created_at"] < self._ttl:
                    logger.info(f"Reusing orchestrator {orchestrator_id} from pool")
                    # Move to end (LRU behavior)
                    self._pool.move_to_end(orchestrator_id)
                    return entry["instance"]
                else:
                    # Expired - remove it
                    logger.info(f"Orchestrator {orchestrator_id} expired, removing from pool")
                    self._cleanup_instance(entry["instance"])
                    del self._pool[orchestrator_id]
            
            # Create new instance
            logger.info(f"Creating new orchestrator {orchestrator_id}")
            instance = await create_func(config)
            
            # Add to pool
            self._pool[orchestrator_id] = {
                "instance": instance,
                "config": config,
                "created_at": datetime.now()
            }
            
            # Evict oldest if pool is full
            while len(self._pool) > self._max_instances:
                oldest_id, oldest_entry = self._pool.popitem(last=False)
                logger.info(f"Evicting oldest orchestrator {oldest_id} from pool")
                self._cleanup_instance(oldest_entry["instance"])
            
            return instance
    
    def _cleanup_instance(self, instance: Any):
        """Clean up orchestrator instance"""
        try:
            if hasattr(instance, 'dispose_db_engine'):
                instance.dispose_db_engine()
        except Exception as e:
            logger.error(f"Error cleaning up orchestrator: {e}")
    
    async def clear_expired(self):
        """Remove expired orchestrators from pool"""
        async with self._lock:
            expired_ids = []
            for orch_id, entry in self._pool.items():
                if datetime.now() - entry["created_at"] >= self._ttl:
                    expired_ids.append(orch_id)
            
            for orch_id in expired_ids:
                entry = self._pool.pop(orch_id)
                self._cleanup_instance(entry["instance"])
                logger.info(f"Cleared expired orchestrator {orch_id}")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            "total_instances": len(self._pool),
            "max_instances": self._max_instances,
            "ttl_minutes": self._ttl.total_seconds() / 60,
            "oldest_age_minutes": (
                (datetime.now() - min(e["created_at"] for e in self._pool.values())).total_seconds() / 60
                if self._pool else 0
            )
        }
```

### 2.2 Update PyRIT Orchestrator Service

**File**: `violentutf_api/fastapi_app/app/services/pyrit_orchestrator_service.py` (modifications)

Add imports:
```python
from .orchestrator_pool import OrchestratorPool
```

Update the `__init__` method:
```python
def __init__(self):
    self.memory = None
    self._orchestrator_instances: Dict[str, Orchestrator] = {}
    self._orchestrator_scorers: Dict[str, List] = {}
    self._orchestrator_metadata: Dict[str, Dict[str, Any]] = {}
    self._orchestrator_registry = self._discover_orchestrator_types()
    self._orchestrator_pool = OrchestratorPool(max_instances=20, ttl_minutes=30)
    self._initialize_memory()
```

Update `create_orchestrator_instance` to use the pool:
```python
async def create_orchestrator_instance(self, config: Dict[str, Any]) -> str:
    """Create and configure orchestrator instance using pool"""
    orchestrator_id = str(uuid.uuid4())
    
    # Use pool to get or create instance
    async def _create_new_instance(config):
        # Existing creation logic here
        orchestrator_type = config["orchestrator_type"]
        parameters = config["parameters"]
        user_context = config.get("user_context")
        
        # ... rest of the existing creation code ...
        
        return orchestrator_instance
    
    # Get from pool or create new
    orchestrator_instance = await self._orchestrator_pool.get_or_create(
        orchestrator_id, config, _create_new_instance
    )
    
    # Store in local registry too
    self._orchestrator_instances[orchestrator_id] = orchestrator_instance
    
    return orchestrator_id
```

## Phase 3: Database Connection Management

### 3.1 Create Connection Manager

**File**: `violentutf_api/fastapi_app/app/services/db_connection_manager.py` (new file)

```python
"""Database connection management to prevent conflicts"""
import asyncio
import logging
import os
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    """Manages database connections to prevent concurrent access issues"""
    
    def __init__(self):
        self._connections: Dict[str, Any] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
    
    async def get_lock(self, db_path: str) -> asyncio.Lock:
        """Get or create lock for database path"""
        async with self._global_lock:
            if db_path not in self._locks:
                self._locks[db_path] = asyncio.Lock()
            return self._locks[db_path]
    
    @asynccontextmanager
    async def get_connection(self, db_path: str):
        """Get database connection with proper locking"""
        lock = await self.get_lock(db_path)
        
        async with lock:
            try:
                # For DuckDB, we need to ensure single writer
                if db_path not in self._connections:
                    from pyrit.memory import DuckDBMemory
                    self._connections[db_path] = DuckDBMemory(db_path=db_path)
                    logger.info(f"Created new connection for {db_path}")
                
                yield self._connections[db_path]
                
            except Exception as e:
                logger.error(f"Database connection error for {db_path}: {e}")
                # Remove failed connection
                if db_path in self._connections:
                    del self._connections[db_path]
                raise
    
    def close_all(self):
        """Close all connections"""
        for db_path, conn in self._connections.items():
            try:
                if hasattr(conn, 'dispose_engine'):
                    conn.dispose_engine()
                logger.info(f"Closed connection for {db_path}")
            except Exception as e:
                logger.error(f"Error closing connection for {db_path}: {e}")
        
        self._connections.clear()
        self._locks.clear()

# Global instance
db_connection_manager = DatabaseConnectionManager()
```

### 3.2 Update Memory Bridge to Use Connection Manager

**File**: `violentutf_api/fastapi_app/app/services/pyrit_memory_bridge.py` (modifications)

Add import:
```python
from .db_connection_manager import db_connection_manager
```

Update `get_or_create_user_memory` method:
```python
async def get_or_create_user_memory(self, user_id: str) -> DuckDBMemory:
    """Get or create user-specific PyRIT memory instance with connection management"""
    memory_path = self.user_context_manager.get_user_memory_path(user_id)
    
    # Use connection manager to avoid conflicts
    async with db_connection_manager.get_connection(memory_path) as memory:
        return memory
```

## Phase 4: Add Health Checks and Monitoring

### 4.1 Create Health Check Endpoint

**File**: `violentutf_api/fastapi_app/app/api/endpoints/health.py` (new file)

```python
"""Health check endpoints for monitoring system status"""
from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.services.pyrit_orchestrator_service import pyrit_orchestrator_service
from app.services.db_connection_manager import db_connection_manager
import os

router = APIRouter()

@router.get("/health/orchestrators")
async def check_orchestrator_health(current_user=Depends(get_current_user)):
    """Check orchestrator pool health"""
    pool_stats = pyrit_orchestrator_service._orchestrator_pool.get_pool_stats()
    
    return {
        "status": "healthy" if pool_stats["total_instances"] < pool_stats["max_instances"] else "warning",
        "pool_stats": pool_stats,
        "active_instances": len(pyrit_orchestrator_service._orchestrator_instances)
    }

@router.get("/health/database")
async def check_database_health(current_user=Depends(get_current_user)):
    """Check database connection health"""
    from utils.user_context_manager import UserContextManager
    
    # Get user's database path
    username = current_user.username
    db_path = UserContextManager.get_user_db_path(username)
    
    return {
        "status": "healthy" if os.path.exists(db_path) else "warning",
        "user_db_path": db_path,
        "exists": os.path.exists(db_path),
        "size_mb": os.path.getsize(db_path) / 1024 / 1024 if os.path.exists(db_path) else 0,
        "active_connections": len(db_connection_manager._connections)
    }
```

## Phase 5: Configuration Updates

### 5.1 Environment Variables

Add to `.env` files:

```bash
# Consistent memory configuration
VIOLENTUTF_MEMORY_DIR=/app/app_data/violentutf/memory
PYRIT_DB_SALT=violentutf_salt_2025

# Orchestrator pool settings
ORCHESTRATOR_POOL_SIZE=20
ORCHESTRATOR_TTL_MINUTES=30

# Database connection settings
DB_CONNECTION_TIMEOUT=30
DB_MAX_RETRIES=3
```

### 5.2 Docker Volume Configuration

Update `docker-compose.yml`:

```yaml
services:
  api:
    volumes:
      - violentutf_memory:/app/app_data/violentutf/memory
  
  streamlit:
    volumes:
      - violentutf_memory:/app/app_data/violentutf/memory

volumes:
  violentutf_memory:
    driver: local
```

## Testing the Fixes

### Test Script

Create `tests/test_db_orchestrator_fixes.py`:

```python
"""Test database and orchestrator fixes"""
import asyncio
import pytest
from utils.user_context_manager import UserContextManager

def test_consistent_user_context():
    """Test that user context is consistent"""
    session_state = {
        "user_info": {
            "username": "admin",
            "preferred_username": "admin@violentutf.local"
        }
    }
    
    username = UserContextManager.get_canonical_username(session_state)
    assert username == "admin@violentutf.local"
    
    # Test path consistency
    path1 = UserContextManager.get_user_db_path(username)
    path2 = UserContextManager.get_user_db_path(username)
    assert path1 == path2

@pytest.mark.asyncio
async def test_orchestrator_pool():
    """Test orchestrator pooling"""
    from app.services.orchestrator_pool import OrchestratorPool
    
    pool = OrchestratorPool(max_instances=2)
    
    # Mock create function
    async def create_mock(config):
        return {"id": config["id"], "created": True}
    
    # Test reuse
    inst1 = await pool.get_or_create("orch1", {"id": "1"}, create_mock)
    inst2 = await pool.get_or_create("orch1", {"id": "1"}, create_mock)
    
    assert inst1 is inst2  # Should be same instance

@pytest.mark.asyncio  
async def test_connection_manager():
    """Test database connection management"""
    from app.services.db_connection_manager import DatabaseConnectionManager
    
    manager = DatabaseConnectionManager()
    
    # Test concurrent access prevention
    async with manager.get_connection("/tmp/test.db") as conn1:
        # This should wait until conn1 is released
        async def concurrent_access():
            async with manager.get_connection("/tmp/test.db") as conn2:
                return conn2
        
        # Should not raise an error
        task = asyncio.create_task(concurrent_access())
        # Give it time to try accessing
        await asyncio.sleep(0.1)
        
    # Now it should complete
    conn2 = await task
    assert conn2 is not None
```

## Deployment Steps

1. **Stop all services**:
   ```bash
   docker-compose down
   ```

2. **Clear existing data** (optional, for clean start):
   ```bash
   docker volume rm violentutf_memory
   ```

3. **Deploy code changes**:
   ```bash
   # Copy new files
   cp utils/user_context_manager.py violentutf/utils/
   cp services/orchestrator_pool.py violentutf_api/fastapi_app/app/services/
   cp services/db_connection_manager.py violentutf_api/fastapi_app/app/services/
   ```

4. **Update environment files**:
   ```bash
   echo "VIOLENTUTF_MEMORY_DIR=/app/app_data/violentutf/memory" >> .env
   echo "PYRIT_DB_SALT=violentutf_salt_2025" >> .env
   ```

5. **Restart services**:
   ```bash
   docker-compose up -d
   ```

6. **Monitor logs**:
   ```bash
   docker-compose logs -f api streamlit
   ```

## Monitoring

After deployment, monitor for:

1. **Consistent user contexts**: Check logs for "Canonical username resolved"
2. **Database path consistency**: Verify same paths are used across services
3. **Orchestrator reuse**: Look for "Reusing orchestrator from pool" messages
4. **Connection management**: Monitor for database lock errors

## Rollback Plan

If issues persist:

1. Revert code changes
2. Clear Docker volumes
3. Restart with original configuration
4. Document specific error messages for further investigation