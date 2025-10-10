# ViolentUTF Data Storage Locations Guide

This document provides a comprehensive overview of where ViolentUTF stores score data, dashboard data, and other persistent information.

## Overview

ViolentUTF uses a hybrid storage approach:
- **SQLite**: For FastAPI application data (API keys, orchestrator configs)
- **DuckDB**: For PyRIT memory, user configurations, and security testing data
- **JSON**: For configuration files and templates

## Primary Database Locations

### 1. FastAPI Application Database (SQLite)
- **Path**: `/app/app_data/violentutf.db` (in container)
- **Local Path**: `./violentutf_api/fastapi_app/app_data/violentutf.db`
- **Configuration**: Set via `DATABASE_URL` environment variable
- **Default**: `sqlite+aiosqlite:///./app_data/violentutf.db`
- **Stores**:
  - API keys and authentication data
  - Orchestrator configurations
  - Orchestrator executions and results
  - COB report templates and schedules
  - User sessions

### 2. PyRIT Memory Database (DuckDB)
- **Base Path**: `/app/app_data/violentutf/` (in container)
- **Local Path**: `./violentutf/app_data/violentutf/`
- **Configuration**: Set via `PYRIT_MEMORY_DB_PATH` environment variable
- **Database Naming**: `pyrit_memory_{user_hash}.db`
  - User hash is generated using SHA256 of username + salt
  - Salt is configured via `PYRIT_DB_SALT` environment variable
- **Example**: `pyrit_memory_101ccf21e3aae051.db`
- **Stores**:
  - PyRIT conversations and memory
  - Generator configurations (per user)
  - Scorer configurations (per user)
  - Dataset configurations and prompts
  - Converter configurations
  - User session data
  - Security test results

## Database Tables and Their Purpose

### SQLite Tables (FastAPI Database)

1. **api_keys**
   - API key management for programmatic access
   - User associations and permissions

2. **orchestrator_configurations**
   - Orchestrator setup and parameters
   - PyRIT orchestrator identifiers

3. **orchestrator_executions**
   - Execution history and status
   - Input/output data for each run
   - Performance metrics

4. **cob_templates**
   - Report template configurations
   - AI analysis prompts

5. **cob_schedules**
   - Scheduled report generation
   - Frequency and timing settings

6. **cob_reports**
   - Generated report instances
   - Content blocks and AI analysis results

### DuckDB Tables (PyRIT Memory)

1. **generators**
   - AI model configurations
   - Test results and status
   - User-specific parameters

2. **scorers**
   - Security scorer configurations
   - Scorer parameters and test results

3. **datasets**
   - Dataset metadata and configuration
   - Source type and import status

4. **dataset_prompts**
   - Individual prompts within datasets
   - Metadata and indexing

5. **converters**
   - Prompt converter configurations
   - Transformation parameters

6. **user_sessions**
   - Session state storage
   - User context preservation

7. **conversations** (PyRIT native)
   - Complete conversation history
   - Security testing interactions

8. **orchestrator_results** (PyRIT native)
   - Detailed results from orchestrator runs
   - Score data and vulnerability findings

## Data Access Patterns

### 1. User Isolation
- Each user has their own DuckDB database file
- Database filename is derived from salted username hash
- Ensures complete data isolation between users

### 2. Service Access
- **Streamlit App**: Accesses DuckDB via `DuckDBManager`
- **FastAPI Service**: Uses both SQLite (via SQLAlchemy) and DuckDB
- **PyRIT Framework**: Direct access to DuckDB for memory operations

### 3. Configuration Hierarchy
```
Environment Variables
  ├── APP_DATA_DIR (base directory)
  ├── PYRIT_MEMORY_DB_PATH (PyRIT specific)
  ├── DATABASE_URL (FastAPI SQLite)
  └── PYRIT_DB_SALT (user isolation)
```

## Score Data Storage Locations

### 1. Real-time Scores
- **Location**: DuckDB `orchestrator_results` table
- **Format**: JSON with score values, timestamps, and metadata
- **Access**: Via PyRIT memory interface or direct DuckDB queries

### 2. Aggregated Scores
- **Location**: SQLite `orchestrator_executions.results` column
- **Format**: JSON summary of execution results
- **Access**: Via FastAPI endpoints

### 3. Dashboard Metrics
- **Primary Source**: DuckDB queries for user-specific data
- **Cached Data**: SQLite for cross-user analytics
- **Real-time Updates**: Streamed from PyRIT memory

## File System Storage

### 1. Configuration Files
- **Path**: `./violentutf/parameters/`
- **Contents**: YAML configurations for generators, scorers, orchestrators

### 2. Dataset Files
- **Path**: `./violentutf/app_data/violentutf/datasets/`
- **Contents**: CSV files, Garak datasets, custom prompt lists

### 3. Custom Components
- **Path**: `./violentutf/custom_targets/`
- **Contents**: Python files for custom PyRIT targets

### 4. Export/Report Files
- **Path**: Configured per deployment
- **Default**: `./app_data/exports/`
- **Contents**: Generated reports, exported data

## Database Connection Examples

### Accessing DuckDB (Python)
```python
from violentutf_api.fastapi_app.app.db.duckdb_manager import DuckDBManager

# Get manager for specific user
manager = DuckDBManager(username="user@example.com")

# List all scorers
scorers = manager.list_scorers()

# Get execution results
results = manager.get_orchestrator_results(execution_id)
```

### Accessing SQLite (Python)
```python
from violentutf_api.fastapi_app.app.db.database import get_session
from violentutf_api.fastapi_app.app.models.orchestrator import OrchestratorExecution

async with get_session() as session:
    executions = await session.query(OrchestratorExecution).all()
```

## Backup and Recovery

### Critical Data Locations
1. **User Data**: `./violentutf/app_data/violentutf/pyrit_memory_*.db`
2. **Application Data**: `./violentutf_api/fastapi_app/app_data/violentutf.db`
3. **Configurations**: `./violentutf/parameters/`

### Backup Strategy
- Regular snapshots of app_data directories
- Export critical configurations to version control
- User-specific database exports via API endpoints

## Security Considerations

1. **Data Isolation**: User data is cryptographically separated
2. **Access Control**: All database access requires authentication
3. **Encryption**: Sensitive data (API keys) stored encrypted
4. **Audit Trail**: All operations logged with user attribution

## Troubleshooting

### Common Issues
1. **Missing Database**: Check APP_DATA_DIR permissions
2. **User Data Not Found**: Verify PYRIT_DB_SALT consistency
3. **Score Data Missing**: Check orchestrator execution status

### Useful Commands
```bash
# Find all database files
find . -name "*.db" -o -name "*.sqlite"

# Check database size
du -h ./app_data/violentutf/

# Verify user hash
echo -n "username:salt" | sha256sum
```

## Related Documentation
- [PyRIT Memory Architecture](https://github.com/Azure/PyRIT/docs/memory)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [SQLAlchemy Async Guide](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html)
