# ViolentUTF Database Behavior Analysis Report

**Date**: July 17, 2025  
**Author**: System Analysis  
**Purpose**: Investigation of potential database switching or time-based database behaviors

## Executive Summary

This analysis investigates reports of potential database switching behavior in ViolentUTF, particularly around midnight or time-based triggers that might cause data loss or database file switching. Based on the comprehensive investigation, no evidence of automatic database switching at midnight or time-based rotation was found in the codebase.

## Database Architecture Overview

ViolentUTF uses a dual database architecture:

### 1. ViolentUTF SQLite Database (`violentutf.db`)
- **Purpose**: Application configuration and persistent results  
- **Location**: `/app/app_data/violentutf.db` (inside Docker container)
- **Content**: Orchestrator results, configurations, API keys, user sessions
- **Persistence**: Permanent, survives across sessions

### 2. PyRIT DuckDB Databases (`pyrit_memory_<hash>.db`)
- **Purpose**: Framework execution data (temporary)
- **Location**: `/app_data/violentutf/` directory
- **Naming**: User-specific files based on SHA256 hash of username + salt
- **Content**: Conversation flows, prompt/response pairs, scoring results
- **Persistence**: Can be cleaned up after analysis

## Key Findings

### 1. No Time-Based Database Rotation Found

After comprehensive analysis of the codebase:
- **No midnight triggers** or time-based database switching logic found
- **No automatic rotation** mechanisms detected
- **No scheduled cleanup** jobs that would create new database files
- **No time-based file naming** patterns in database creation

### 2. Database File Creation Pattern

Analysis of existing PyRIT memory database files shows:
- Multiple files exist for different users (hash-based naming)
- Some files were created at identical timestamps (e.g., 2025-07-10 09:38:29)
- This suggests batch initialization or testing rather than time-based rotation

### 3. Database Persistence Mechanism

The database files are created based on:
- **User Context**: Each user gets a unique database file
- **Hash-based Naming**: `pyrit_memory_{sha256_hash}.db`
- **Salt-based Security**: Uses `PYRIT_DB_SALT` environment variable
- **Persistent Storage**: Files remain until manually cleaned

## Database Management Code Analysis

### DuckDBManager (`duckdb_manager.py`)
- Creates user-specific database files
- No time-based logic or rotation mechanisms
- Uses consistent hashing for filename generation
- Implements table schema validation and recreation on conflicts

### PyRIT Memory Bridge (`pyrit_memory_bridge.py`)
- Manages user-specific PyRIT memory instances
- Caches memory connections for performance
- No automatic cleanup or rotation logic
- Provides manual cleanup methods with age-based filtering

## Potential Causes of Perceived Database Switching

If users are experiencing data loss or "database switching," possible causes include:

### 1. **User Context Changes**
- Different login credentials generate different database files
- Username or salt changes would create new database files
- OAuth token refresh might change user context

### 2. **Environment Variable Changes**
- `PYRIT_DB_SALT` modification would change database filenames
- `APP_DATA_DIR` changes would look for databases in different locations

### 3. **Container Restarts**
- If volume mounting is misconfigured, data might not persist
- Docker container recreation without proper volume mapping

### 4. **Schema Conflicts**
- The code includes logic to recreate databases on schema conflicts
- Foreign key or cascade errors trigger database recreation

### 5. **Manual Cleanup**
- Scripts exist for database cleanup (`cleanup_dashboard_data.py`)
- Administrators might be running cleanup scripts

## Recommendations

### 1. **Monitoring and Logging**
- Add logging for database file creation/selection
- Log user context and hash generation
- Monitor for environment variable changes

### 2. **Data Persistence Verification**
- Ensure Docker volumes are properly configured
- Verify that database directories are correctly mounted
- Check file permissions on database directories

### 3. **User Context Stability**
- Ensure consistent user identification across sessions
- Verify JWT token handling doesn't change user context
- Check OAuth token refresh behavior

### 4. **Backup Strategy**
- Implement regular backups of both database types
- Consider versioned backups before major operations
- Document recovery procedures

### 5. **Investigation Steps for Data Loss**
If data loss is reported:
1. Check if multiple database files exist for the user
2. Verify the current `PYRIT_DB_SALT` value
3. Review container logs for database recreation events
4. Check volume mounting configuration
5. Verify user authentication consistency

## Related Documentation

- [Memory Management Guide](lesson_memoryManagement.md) - Detailed memory architecture
- [Database Cleanup Guide](../guides/Guide_Database_Cleanup.md) - Cleanup procedures
- [User Context Standardization](../guides/user_context_standardization.md) - User identification
- **[Database Switching Analysis](./Database_Switching_Analysis.md)** - Root cause analysis of orchestrator-driven database switching
- **[Implementation Analysis](./Database_Switching_Implementation_Analysis.md)** - Strategic implementation recommendations
- **[Implementation Guide](./fix_database_orchestrator_issues.md)** - Step-by-step fix instructions

## **CRITICAL UPDATE: Database Switching Issue Identified**

**New Finding**: Further investigation has revealed a **critical database switching issue** in the Enterprise environment where users lose their configurations after ~1500 prompts and ~10 minutes. This is **NOT** time-based rotation but rather **orchestrator-driven database switching**.

### Root Cause
The orchestrator service creates new database files (`orchestrator_memory_{orchestrator_id[:8]}.db`) for each orchestrator instance and overwrites the global CentralMemory instance, causing users to lose access to their original configurations.

### **IMMEDIATE ACTION REQUIRED**
**Implement Phase 1 fixes immediately** to resolve critical user impact:

1. **Consistent Database Path** - Use user-specific paths instead of random orchestrator IDs
2. **Basic Connection Pooling** - Prevent database lock conflicts

**Timeline**: 1-2 days
**Risk**: LOW
**Impact**: Solves 95% of the problem with minimal changes

See [Database Switching Analysis](./Database_Switching_Analysis.md) for complete details and [Implementation Analysis](./Database_Switching_Implementation_Analysis.md) for strategic recommendations.

## Conclusion

**Original Analysis**: No evidence of automatic midnight database switching or time-based rotation was found in the ViolentUTF codebase.

**Critical Discovery**: A separate orchestrator-driven database switching issue has been identified that causes users to lose their configurations after processing ~1500 prompts. This requires immediate Phase 1 fixes to restore system stability.

Database files are created based on user context and remain persistent unless manually cleaned or recreated due to schema conflicts. The newly discovered orchestrator issue requires immediate attention to prevent further user frustration and data loss.