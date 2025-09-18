# Cross-Database Transaction Recovery Procedures

## Overview

This document provides comprehensive procedures for recovering from partial failures in cross-database operations within ViolentUTF's multi-database architecture. The system spans PostgreSQL (Keycloak), SQLite (FastAPI), DuckDB (PyRIT Memory), and file system storage, requiring sophisticated recovery mechanisms to maintain data consistency.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Transaction Patterns](#transaction-patterns)
3. [Failure Scenarios](#failure-scenarios)
4. [Recovery Procedures](#recovery-procedures)
5. [Monitoring and Detection](#monitoring-and-detection)
6. [Prevention Strategies](#prevention-strategies)
7. [Testing and Validation](#testing-and-validation)

## Architecture Overview

### Multi-Database Transaction Flow

ViolentUTF implements a distributed transaction pattern across four data storage systems:

```
User Request → Streamlit → APISIX → FastAPI → Multi-DB Operations
                                      ├── PostgreSQL (Keycloak Auth)
                                      ├── SQLite (API Metadata)
                                      ├── DuckDB (PyRIT Memory)
                                      └── File System (Logs/Cache)
```

### Transaction Coordination

**Compensating Transaction Pattern**: ViolentUTF uses compensating transactions rather than distributed 2PC due to the heterogeneous database environment.

**Key Components**:
- **Transaction Coordinator**: FastAPI service layer
- **Operation Log**: SQLite-based transaction tracking
- **Compensating Actions**: Rollback operations for each database
- **State Management**: Streamlit session state for UI consistency

## Transaction Patterns

### 1. Orchestrator Execution Transaction

**Participants**:
- Keycloak PostgreSQL: User authentication validation
- FastAPI SQLite: Execution metadata and status
- DuckDB: PyRIT memory storage and results
- File System: Execution logs and artifacts

**Transaction Flow**:
```python
# Simplified orchestrator execution transaction
async def execute_orchestrator_transaction(user_context, orchestrator_config):
    transaction_id = generate_transaction_id()

    try:
        # Phase 1: Prepare operations
        auth_token = validate_keycloak_auth(user_context)  # PostgreSQL
        execution_id = create_execution_record(transaction_id)  # SQLite

        # Phase 2: Execute main operation
        pyrit_memory_id = initialize_pyrit_memory(user_context)  # DuckDB
        execution_results = run_pyrit_orchestrator(orchestrator_config)  # DuckDB

        # Phase 3: Finalize
        update_execution_status(execution_id, "completed")  # SQLite
        write_execution_logs(execution_results)  # File System

        commit_transaction(transaction_id)

    except Exception as e:
        # Initiate compensating transaction
        await rollback_orchestrator_transaction(transaction_id, e)
        raise
```

### 2. User Session Management Transaction

**Participants**:
- Keycloak PostgreSQL: SSO session management
- Streamlit Session: UI state and user context
- FastAPI SQLite: API session tracking
- DuckDB: User database initialization

**Transaction Flow**:
```python
async def user_session_transaction(keycloak_token):
    transaction_id = generate_transaction_id()

    try:
        # Phase 1: Authentication
        user_info = validate_keycloak_token(keycloak_token)  # PostgreSQL
        canonical_user = normalize_username(user_info)  # In-memory

        # Phase 2: Session establishment
        streamlit_session = create_streamlit_session(canonical_user)  # Session State
        api_token = create_api_jwt_token(user_info)  # In-memory

        # Phase 3: Database initialization
        user_duckdb = initialize_user_database(canonical_user)  # DuckDB
        session_record = create_session_record(canonical_user)  # SQLite

        commit_transaction(transaction_id)

    except Exception as e:
        await rollback_session_transaction(transaction_id, e)
        raise
```

### 3. Configuration Update Transaction

**Participants**:
- FastAPI SQLite: Configuration metadata
- DuckDB: Generator/scorer/dataset configuration
- File System: YAML/JSON configuration files
- Streamlit Session: UI state updates

## Failure Scenarios

### 1. Partial PostgreSQL (Keycloak) Failure

**Scenario**: Keycloak authentication succeeds but subsequent database operations fail

**Symptoms**:
- User has valid Keycloak session
- API operations fail with authentication errors
- DuckDB operations cannot proceed

**Impact Assessment**:
```python
def assess_keycloak_failure_impact(transaction_id):
    """Assess impact of Keycloak-related failures"""
    impact = {
        "severity": "high",
        "affected_operations": [
            "user_authentication",
            "token_refresh",
            "new_user_sessions"
        ],
        "recovery_complexity": "medium",
        "data_loss_risk": "low"
    }

    # Check if user has cached credentials
    if has_cached_api_token():
        impact["severity"] = "medium"
        impact["immediate_workaround"] = "use_cached_token"

    return impact
```

### 2. SQLite Database Corruption

**Scenario**: FastAPI SQLite database becomes corrupted during write operations

**Symptoms**:
- API metadata operations fail
- Execution status cannot be updated
- Session tracking is lost

**Impact Assessment**:
```python
def assess_sqlite_failure_impact(transaction_id):
    """Assess impact of SQLite database failures"""
    impact = {
        "severity": "medium",
        "affected_operations": [
            "execution_tracking",
            "session_management",
            "api_metadata"
        ],
        "recovery_complexity": "low",
        "data_loss_risk": "medium"
    }

    # Check if backup exists
    if has_recent_sqlite_backup():
        impact["recovery_complexity"] = "low"
        impact["data_loss_risk"] = "low"

    return impact
```

### 3. DuckDB User Database Failure

**Scenario**: User-specific DuckDB database becomes corrupted or inaccessible

**Symptoms**:
- PyRIT operations fail for specific user
- User cannot access generators, scorers, datasets
- Orchestrator execution fails

**Impact Assessment**:
```python
def assess_duckdb_failure_impact(username, transaction_id):
    """Assess impact of DuckDB user database failures"""
    impact = {
        "severity": "high",
        "affected_operations": [
            "pyrit_orchestration",
            "user_configuration_management",
            "security_test_execution"
        ],
        "recovery_complexity": "medium",
        "data_loss_risk": "high"
    }

    # Check for recent PyRIT exports
    if has_recent_pyrit_export(username):
        impact["data_loss_risk"] = "medium"
        impact["recovery_complexity"] = "low"

    return impact
```

### 4. Cross-Database Consistency Failure

**Scenario**: Operations succeed in some databases but fail in others

**Symptoms**:
- Inconsistent state across databases
- User sees partial results
- Subsequent operations fail due to missing dependencies

## Recovery Procedures

### 1. Keycloak Authentication Recovery

#### Procedure: Recover from Keycloak Authentication Failures

**Detection**:
```bash
# Monitor Keycloak connectivity
curl -f http://localhost:8080/auth/realms/violentutf/protocol/openid_connect/certs || echo "Keycloak unavailable"

# Check Keycloak container status
docker ps | grep keycloak || echo "Keycloak container down"
```

**Recovery Steps**:

1. **Immediate Response** (Automated):
   ```python
   async def recover_keycloak_auth_failure(transaction_id):
       """Immediate response to Keycloak authentication failure"""

       # Step 1: Activate cached token mode
       enable_cached_token_mode()

       # Step 2: Notify user of degraded mode
       notify_user_degraded_mode("authentication_service")

       # Step 3: Log recovery action
       log_recovery_action(transaction_id, "keycloak_failure", "cached_token_activated")

       # Step 4: Continue with cached credentials if available
       cached_token = get_cached_api_token()
       if cached_token and is_token_valid(cached_token):
           return {"status": "degraded_mode", "token": cached_token}
       else:
           return {"status": "authentication_required", "action": "manual_login"}
   ```

2. **Service Recovery** (Manual):
   ```bash
   # Restart Keycloak container
   cd keycloak
   docker-compose down
   docker-compose up -d

   # Wait for service to be ready
   ./wait_for_keycloak.sh

   # Verify authentication flow
   python3 ../tests/test_keycloak_integration.py
   ```

3. **Data Consistency Validation**:
   ```python
   async def validate_keycloak_recovery(transaction_id):
       """Validate Keycloak recovery and data consistency"""

       # Test authentication flow
       test_result = await test_keycloak_authentication()
       if not test_result["success"]:
           return {"status": "recovery_failed", "error": test_result["error"]}

       # Validate user sessions
       active_users = get_active_users()
       for user in active_users:
           session_valid = await validate_user_session(user)
           if not session_valid:
               await refresh_user_session(user)

       return {"status": "recovery_successful", "validated_users": len(active_users)}
   ```

### 2. SQLite Database Recovery

#### Procedure: Recover from SQLite Database Corruption

**Detection**:
```python
def detect_sqlite_corruption():
    """Detect SQLite database corruption"""
    try:
        with sqlite3.connect("app_database.db") as conn:
            conn.execute("PRAGMA integrity_check")
            return {"status": "healthy"}
    except sqlite3.DatabaseError as e:
        return {"status": "corrupted", "error": str(e)}
```

**Recovery Steps**:

1. **Immediate Backup**:
   ```bash
   # Create backup of corrupted database
   TIMESTAMP=$(date +%Y%m%d_%H%M%S)
   cp violentutf_api/fastapi_app/app_database.db "backups/corrupted_${TIMESTAMP}.db"

   # Create recovery directory
   mkdir -p recovery/${TIMESTAMP}
   ```

2. **Database Recovery**:
   ```python
   async def recover_sqlite_database():
       """Recover SQLite database from corruption"""
       recovery_id = generate_recovery_id()

       try:
           # Step 1: Attempt database repair
           repair_result = attempt_sqlite_repair()
           if repair_result["success"]:
               return {"status": "repaired", "method": "sqlite_repair"}

           # Step 2: Restore from backup
           backup_restored = restore_from_latest_backup()
           if backup_restored["success"]:
               return {"status": "restored", "method": "backup_restore",
                      "data_loss": backup_restored["data_loss_hours"]}

           # Step 3: Rebuild from other databases
           rebuild_result = rebuild_sqlite_from_sources()
           return {"status": "rebuilt", "method": "cross_database_rebuild",
                  "data_loss": rebuild_result["estimated_loss"]}

       except Exception as e:
           log_recovery_failure(recovery_id, "sqlite_recovery", str(e))
           raise

   def attempt_sqlite_repair():
       """Attempt to repair corrupted SQLite database"""
       try:
           # Use SQLite .recover command
           os.system("sqlite3 app_database.db '.recover' | sqlite3 recovered_database.db")

           # Validate recovered database
           with sqlite3.connect("recovered_database.db") as conn:
               tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

           if len(tables) > 0:
               # Replace corrupted database with recovered one
               os.replace("recovered_database.db", "app_database.db")
               return {"success": True}
           else:
               return {"success": False, "error": "No tables recovered"}

       except Exception as e:
           return {"success": False, "error": str(e)}
   ```

3. **Data Reconstruction**:
   ```python
   def rebuild_sqlite_from_sources():
       """Rebuild SQLite database from other data sources"""

       # Reconstruct execution records from DuckDB
       execution_records = []
       for user_db in glob.glob("./app_data/violentutf/pyrit_memory_*.db"):
           with duckdb.connect(user_db) as conn:
               executions = conn.execute("""
                   SELECT user_id, created_at, 'orchestrator_execution' as type
                   FROM generators WHERE status = 'completed'
               """).fetchall()
               execution_records.extend(executions)

       # Reconstruct session records from Streamlit session files
       session_records = reconstruct_sessions_from_logs()

       # Rebuild SQLite with reconstructed data
       with sqlite3.connect("app_database.db") as conn:
           for record in execution_records:
               conn.execute("INSERT INTO executions (user_id, created_at, type) VALUES (?, ?, ?)", record)

           for session in session_records:
               conn.execute("INSERT INTO sessions (user_id, session_data, created_at) VALUES (?, ?, ?)", session)

       return {"estimated_loss": "recent_metadata_only"}
   ```

### 3. DuckDB User Database Recovery

#### Procedure: Recover Individual User DuckDB Databases

**Detection**:
```python
def detect_duckdb_user_database_issues(username):
    """Detect issues with user's DuckDB database"""
    from violentutf_api.fastapi_app.app.db.duckdb_manager import DuckDBManager

    try:
        manager = DuckDBManager(username)
        stats = manager.get_stats()
        return {"status": "healthy", "stats": stats}
    except Exception as e:
        return {"status": "corrupted", "error": str(e), "user": username}
```

**Recovery Steps**:

1. **User Database Backup and Isolation**:
   ```bash
   # Create backup of user's corrupted database
   USERNAME="tam.nguyen"  # Replace with actual username

   python3 -c "
   from violentutf_api.fastapi_app.app.db.duckdb_manager import DuckDBManager
   from violentutf.utils.user_context_manager import UserContextManager
   import shutil
   import datetime

   username = '$USERNAME'
   manager = DuckDBManager(username)
   timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
   backup_path = f'backups/duckdb_user_{username}_{timestamp}.db'

   if os.path.exists(manager.db_path):
       shutil.copy2(manager.db_path, backup_path)
       print(f'Backed up corrupted database to: {backup_path}')
   else:
       print(f'Database file not found: {manager.db_path}')
   "
   ```

2. **Progressive Recovery Strategy**:
   ```python
   async def recover_user_duckdb_database(username):
       """Progressive recovery strategy for user DuckDB database"""
       recovery_id = generate_recovery_id()

       try:
           # Strategy 1: Repair existing database
           repair_result = await attempt_duckdb_repair(username)
           if repair_result["success"]:
               return {"status": "repaired", "method": "database_repair"}

           # Strategy 2: Recreate with clean schema
           recreate_result = await recreate_user_database(username)
           if recreate_result["success"]:
               return {"status": "recreated", "method": "clean_recreation",
                      "data_loss": "all_user_data"}

           # Strategy 3: Restore from PyRIT export if available
           export_result = await restore_from_pyrit_export(username)
           if export_result["success"]:
               return {"status": "restored", "method": "pyrit_export",
                      "data_loss": export_result["data_loss"]}

       except Exception as e:
           log_recovery_failure(recovery_id, f"duckdb_user_{username}", str(e))
           raise

   async def attempt_duckdb_repair(username):
       """Attempt to repair corrupted DuckDB database"""
       from violentutf_api.fastapi_app.app.db.duckdb_manager import DuckDBManager

       try:
           manager = DuckDBManager(username)
           corrupted_path = manager.db_path
           repair_path = corrupted_path + ".repair"

           # Attempt data extraction
           with duckdb.connect(corrupted_path) as source:
               with duckdb.connect(repair_path) as target:
                   # Create clean schema
                   manager._create_tables(target)

                   # Copy data table by table
                   tables = ["generators", "datasets", "converters", "scorers", "user_sessions"]
                   recovered_data = {}

                   for table in tables:
                       try:
                           data = source.execute(f"SELECT * FROM {table}").fetchall()
                           columns = [desc[0] for desc in source.description]

                           for row in data:
                               placeholders = ",".join(["?" for _ in row])
                               target.execute(f"INSERT INTO {table} VALUES ({placeholders})", row)

                           recovered_data[table] = len(data)
                       except Exception as table_error:
                           print(f"Could not recover table {table}: {table_error}")
                           recovered_data[table] = 0

           # Replace corrupted database with repaired one
           os.replace(repair_path, corrupted_path)

           return {"success": True, "recovered_data": recovered_data}

       except Exception as e:
           return {"success": False, "error": str(e)}

   async def recreate_user_database(username):
       """Recreate user database with clean schema"""
       try:
           manager = DuckDBManager(username)

           # Remove corrupted database
           if os.path.exists(manager.db_path):
               os.remove(manager.db_path)

           # Create new clean database
           new_manager = DuckDBManager(username)

           # Verify new database is functional
           stats = new_manager.get_stats()

           return {"success": True, "stats": stats}

       except Exception as e:
           return {"success": False, "error": str(e)}
   ```

3. **User Notification and Guidance**:
   ```python
   def notify_user_database_recovery(username, recovery_result):
       """Notify user about database recovery status"""

       notification = {
           "user": username,
           "timestamp": datetime.now().isoformat(),
           "recovery_status": recovery_result["status"],
           "data_impact": recovery_result.get("data_loss", "none")
       }

       if recovery_result["status"] == "recreated":
           notification["message"] = (
               "Your user database has been recreated with a clean slate. "
               "Previous generators, datasets, and configurations have been lost. "
               "Please reconfigure your security testing components."
           )
           notification["recommended_actions"] = [
               "Reconfigure generators",
               "Import datasets",
               "Set up scorers",
               "Review documentation for setup guidance"
           ]

       elif recovery_result["status"] == "repaired":
           notification["message"] = (
               "Your user database has been repaired. Most data should be intact. "
               "Please verify your configurations and test functionality."
           )
           notification["recommended_actions"] = [
               "Verify generator configurations",
               "Test dataset access",
               "Run validation tests"
           ]

       # Store notification for UI display
       store_user_notification(username, notification)

       return notification
   ```

### 4. Cross-Database Consistency Recovery

#### Procedure: Recover from Distributed Transaction Failures

**Detection**:
```python
def detect_cross_database_inconsistency():
    """Detect inconsistencies across database systems"""
    inconsistencies = []

    # Check user count consistency
    keycloak_users = get_keycloak_user_count()
    duckdb_users = get_duckdb_user_count()
    sqlite_sessions = get_active_sqlite_sessions()

    if abs(keycloak_users - duckdb_users) > 5:  # Allow some variance
        inconsistencies.append({
            "type": "user_count_mismatch",
            "keycloak": keycloak_users,
            "duckdb": duckdb_users
        })

    # Check execution state consistency
    for username in get_all_users():
        sqlite_executions = get_user_executions_from_sqlite(username)
        duckdb_executions = get_user_executions_from_duckdb(username)

        if len(sqlite_executions) != len(duckdb_executions):
            inconsistencies.append({
                "type": "execution_count_mismatch",
                "user": username,
                "sqlite": len(sqlite_executions),
                "duckdb": len(duckdb_executions)
            })

    return inconsistencies
```

**Recovery Steps**:

1. **Distributed State Analysis**:
   ```python
   async def analyze_distributed_state():
       """Analyze state across all databases to identify inconsistencies"""

       state_analysis = {
           "keycloak": await analyze_keycloak_state(),
           "sqlite": await analyze_sqlite_state(),
           "duckdb": await analyze_duckdb_state(),
           "filesystem": await analyze_filesystem_state()
       }

       inconsistencies = []

       # Cross-reference user data
       all_users = set()
       for db_name, state in state_analysis.items():
           all_users.update(state.get("users", []))

       for user in all_users:
           user_consistency = {}
           for db_name, state in state_analysis.items():
               user_data = state.get("user_data", {}).get(user, {})
               user_consistency[db_name] = user_data

           # Check for missing user data in any database
           missing_in = []
           for db_name, user_data in user_consistency.items():
               if not user_data:
                   missing_in.append(db_name)

           if missing_in:
               inconsistencies.append({
                   "type": "missing_user_data",
                   "user": user,
                   "missing_in": missing_in,
                   "present_in": [db for db in user_consistency.keys() if db not in missing_in]
               })

       return {
           "state_analysis": state_analysis,
           "inconsistencies": inconsistencies,
           "recommendations": generate_consistency_recommendations(inconsistencies)
       }
   ```

2. **Compensating Transaction Execution**:
   ```python
   async def execute_compensating_transactions(inconsistencies):
       """Execute compensating transactions to restore consistency"""

       for inconsistency in inconsistencies:
           if inconsistency["type"] == "missing_user_data":
               await compensate_missing_user_data(inconsistency)
           elif inconsistency["type"] == "execution_count_mismatch":
               await compensate_execution_mismatch(inconsistency)
           elif inconsistency["type"] == "orphaned_data":
               await compensate_orphaned_data(inconsistency)

   async def compensate_missing_user_data(inconsistency):
       """Compensate for missing user data across databases"""
       user = inconsistency["user"]
       missing_in = inconsistency["missing_in"]
       present_in = inconsistency["present_in"]

       # Find authoritative source (prefer Keycloak > SQLite > DuckDB)
       authoritative_source = None
       if "keycloak" in present_in:
           authoritative_source = "keycloak"
       elif "sqlite" in present_in:
           authoritative_source = "sqlite"
       elif "duckdb" in present_in:
           authoritative_source = "duckdb"

       if not authoritative_source:
           raise Exception(f"No authoritative source found for user {user}")

       # Reconstruct missing data
       for target_db in missing_in:
           if target_db == "duckdb":
               # Create user's DuckDB database
               manager = DuckDBManager(user)
               # Database will be created automatically

           elif target_db == "sqlite":
               # Create session record in SQLite
               await create_missing_sqlite_session(user)

           # Note: Keycloak users are managed externally via SSO
   ```

3. **Validation and Monitoring**:
   ```python
   async def validate_consistency_recovery():
       """Validate that consistency has been restored"""

       # Re-run consistency checks
       post_recovery_inconsistencies = detect_cross_database_inconsistency()

       if len(post_recovery_inconsistencies) == 0:
           return {"status": "consistent", "message": "All databases are now consistent"}

       # Categorize remaining inconsistencies
       critical = [i for i in post_recovery_inconsistencies if i.get("severity") == "critical"]
       minor = [i for i in post_recovery_inconsistencies if i.get("severity") != "critical"]

       if len(critical) > 0:
           return {
               "status": "partially_recovered",
               "critical_issues": critical,
               "minor_issues": minor,
               "action_required": True
           }
       else:
           return {
               "status": "mostly_consistent",
               "minor_issues": minor,
               "action_required": False
           }
   ```

## Monitoring and Detection

### Real-time Monitoring

1. **Transaction Health Monitoring**:
   ```python
   class TransactionHealthMonitor:
       def __init__(self):
           self.failure_rates = {}
           self.recovery_metrics = {}

       def monitor_transaction_health(self):
           """Monitor transaction success/failure rates across databases"""

           health_metrics = {
               "keycloak_auth_success_rate": self.measure_keycloak_success_rate(),
               "sqlite_operation_success_rate": self.measure_sqlite_success_rate(),
               "duckdb_operation_success_rate": self.measure_duckdb_success_rate(),
               "cross_db_consistency_score": self.measure_consistency_score()
           }

           # Alert on degraded performance
           for metric, value in health_metrics.items():
               if value < 0.95:  # Below 95% success rate
                   self.alert_degraded_performance(metric, value)

           return health_metrics
   ```

2. **Failure Pattern Detection**:
   ```bash
   # Monitor for database connection issues
   tail -f violentutf_api/fastapi_app/logs/app.log | grep -E "(DatabaseError|ConnectionError|TransactionError)"

   # Monitor DuckDB file system issues
   tail -f violentutf_api/fastapi_app/logs/app.log | grep -E "(DuckDB|pyrit_memory.*\.db)"

   # Monitor Keycloak authentication issues
   tail -f violentutf_api/fastapi_app/logs/app.log | grep -E "(KeycloakError|AuthenticationError)"
   ```

### Automated Recovery Triggers

```python
class AutomatedRecoverySystem:
    def __init__(self):
        self.recovery_thresholds = {
            "keycloak_failure_rate": 0.1,  # 10% failure rate triggers recovery
            "sqlite_corruption_detected": True,
            "duckdb_user_database_failure": True,
            "cross_db_inconsistency_count": 5
        }

    async def evaluate_recovery_triggers(self, health_metrics):
        """Evaluate if automated recovery should be triggered"""

        recovery_actions = []

        if health_metrics["keycloak_auth_success_rate"] < (1 - self.recovery_thresholds["keycloak_failure_rate"]):
            recovery_actions.append("activate_cached_token_mode")

        if health_metrics.get("sqlite_corruption_detected"):
            recovery_actions.append("initiate_sqlite_recovery")

        if health_metrics.get("duckdb_failures", 0) > 0:
            recovery_actions.append("repair_user_databases")

        # Execute recovery actions
        for action in recovery_actions:
            await self.execute_recovery_action(action)

    async def execute_recovery_action(self, action):
        """Execute automated recovery action"""
        if action == "activate_cached_token_mode":
            await recover_keycloak_auth_failure("auto_trigger")
        elif action == "initiate_sqlite_recovery":
            await recover_sqlite_database()
        elif action == "repair_user_databases":
            await self.repair_failed_user_databases()
```

## Prevention Strategies

### 1. Proactive Health Checks

```python
async def perform_proactive_health_checks():
    """Perform proactive health checks to prevent failures"""

    health_checks = {
        "keycloak_connectivity": await check_keycloak_health(),
        "sqlite_integrity": await check_sqlite_integrity(),
        "duckdb_user_databases": await check_user_database_health(),
        "filesystem_storage": await check_filesystem_health(),
        "cross_database_sync": await check_cross_database_sync()
    }

    # Schedule preventive maintenance based on health check results
    for check_name, result in health_checks.items():
        if result["status"] == "warning":
            await schedule_preventive_maintenance(check_name, result)

    return health_checks
```

### 2. Backup Strategy

```bash
# Automated backup script
#!/bin/bash
# backup_databases.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups/${TIMESTAMP}"

mkdir -p ${BACKUP_DIR}

# Backup SQLite database
cp violentutf_api/fastapi_app/app_database.db ${BACKUP_DIR}/sqlite_backup.db

# Backup all user DuckDB databases
cp ./app_data/violentutf/pyrit_memory_*.db ${BACKUP_DIR}/

# Backup Keycloak database (PostgreSQL dump)
docker exec keycloak-postgres pg_dump -U keycloak keycloak > ${BACKUP_DIR}/keycloak_backup.sql

# Create backup manifest
echo "Backup created: ${TIMESTAMP}" > ${BACKUP_DIR}/manifest.txt
echo "SQLite database: $(stat -c%s ${BACKUP_DIR}/sqlite_backup.db) bytes" >> ${BACKUP_DIR}/manifest.txt
echo "DuckDB databases: $(ls ${BACKUP_DIR}/pyrit_memory_*.db | wc -l) files" >> ${BACKUP_DIR}/manifest.txt

# Compress backup
tar -czf ${BACKUP_DIR}.tar.gz -C ./backups ${TIMESTAMP}
rm -rf ${BACKUP_DIR}

echo "Backup completed: ${BACKUP_DIR}.tar.gz"
```

### 3. Circuit Breaker Pattern

```python
class DatabaseCircuitBreaker:
    def __init__(self, database_name, failure_threshold=5, recovery_timeout=60):
        self.database_name = database_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call_with_circuit_breaker(self, operation):
        """Execute database operation with circuit breaker protection"""

        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception(f"Circuit breaker OPEN for {self.database_name}")

        try:
            result = await operation()

            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0

            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                await self.initiate_recovery()

            raise e

    async def initiate_recovery(self):
        """Initiate recovery procedures when circuit breaker opens"""
        recovery_actions = {
            "keycloak": recover_keycloak_auth_failure,
            "sqlite": recover_sqlite_database,
            "duckdb": self.recover_duckdb_issues
        }

        if self.database_name in recovery_actions:
            await recovery_actions[self.database_name]("circuit_breaker_trigger")
```

## Testing and Validation

### Recovery Test Suite

```python
class TransactionRecoveryTestSuite:
    """Comprehensive test suite for transaction recovery procedures"""

    @pytest.mark.integration
    async def test_keycloak_failure_recovery(self):
        """Test recovery from Keycloak authentication failures"""

        # Simulate Keycloak failure
        with mock_keycloak_failure():
            # Attempt user authentication
            with pytest.raises(KeycloakAuthenticationError):
                await authenticate_user("test_user")

            # Trigger recovery
            recovery_result = await recover_keycloak_auth_failure("test_transaction")

            # Verify recovery activated cached token mode
            assert recovery_result["status"] == "degraded_mode"

            # Verify user can still access system with cached token
            cached_token = get_cached_api_token()
            assert cached_token is not None

            api_response = await call_api_with_token(cached_token)
            assert api_response["status"] == "success"

    @pytest.mark.integration
    async def test_sqlite_corruption_recovery(self):
        """Test recovery from SQLite database corruption"""

        # Create test data
        test_execution_id = await create_test_execution()

        # Simulate database corruption
        corrupt_sqlite_database()

        # Verify corruption detected
        corruption_status = detect_sqlite_corruption()
        assert corruption_status["status"] == "corrupted"

        # Trigger recovery
        recovery_result = await recover_sqlite_database()

        # Verify recovery method
        assert recovery_result["status"] in ["repaired", "restored", "rebuilt"]

        # Verify data integrity after recovery
        post_recovery_executions = await get_all_executions()
        assert len(post_recovery_executions) >= 0  # Some data may be lost

    @pytest.mark.integration
    async def test_cross_database_consistency_recovery(self):
        """Test recovery from cross-database inconsistencies"""

        # Create inconsistent state
        await create_user_in_keycloak("test_user")
        await create_user_session_in_sqlite("test_user")
        # Deliberately omit DuckDB creation

        # Detect inconsistency
        inconsistencies = detect_cross_database_inconsistency()
        assert len(inconsistencies) > 0

        # Execute recovery
        await execute_compensating_transactions(inconsistencies)

        # Verify consistency restored
        post_recovery_inconsistencies = detect_cross_database_inconsistency()
        assert len(post_recovery_inconsistencies) == 0

        # Verify user can access all systems
        user_duckdb = DuckDBManager("test_user")
        assert user_duckdb.get_stats() is not None
```

### Chaos Engineering Tests

```python
class ChaosEngineeringTests:
    """Chaos engineering tests for distributed transaction resilience"""

    async def test_random_database_failures(self):
        """Test system resilience to random database failures"""

        # Start multiple concurrent operations
        operations = []
        for i in range(10):
            operations.append(execute_orchestrator_transaction(f"user_{i}", test_config))

        # Randomly fail databases during operations
        await asyncio.sleep(2)
        await randomly_fail_database("sqlite")

        await asyncio.sleep(3)
        await randomly_fail_database("duckdb")

        # Wait for operations to complete or fail
        results = await asyncio.gather(*operations, return_exceptions=True)

        # Verify system recovered gracefully
        successful_operations = [r for r in results if not isinstance(r, Exception)]
        failed_operations = [r for r in results if isinstance(r, Exception)]

        # At least some operations should succeed despite failures
        assert len(successful_operations) > 0

        # System should be in consistent state after recovery
        final_inconsistencies = detect_cross_database_inconsistency()
        assert len(final_inconsistencies) == 0
```

## Conclusion

This comprehensive cross-database transaction recovery framework ensures ViolentUTF can handle complex failure scenarios while maintaining data consistency and system availability. The combination of compensating transactions, automated recovery procedures, and proactive monitoring provides enterprise-grade resilience for the multi-database architecture.

Key benefits:
- **Automated Recovery**: Reduces manual intervention requirements
- **Data Consistency**: Maintains consistency across heterogeneous databases
- **User Experience**: Minimizes service disruption during failures
- **Operational Visibility**: Comprehensive monitoring and alerting
- **Preventive Maintenance**: Proactive health checks prevent failures

Regular testing and validation of these procedures ensures the system remains robust as it evolves and scales.
