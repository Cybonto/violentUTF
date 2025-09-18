# ViolentUTF Database Architecture Overview

## Executive Summary

ViolentUTF employs a multi-database architecture designed to optimize performance, security, and scalability for AI red-teaming operations. The system uses PostgreSQL for identity management, SQLite for application data, DuckDB for user-specific configurations and PyRIT memory storage, and file-based storage for configurations and datasets.

## Database Architecture Design Principles

### 1. **Separation of Concerns**
- **Identity Data**: PostgreSQL handles all authentication and authorization data
- **Application Data**: SQLite manages shared application state and system configuration
- **User Data**: DuckDB provides isolated, user-specific storage for configurations and test data
- **File Storage**: File system handles static configurations, datasets, and reports

### 2. **Security by Design**
- User isolation through separate DuckDB instances per user
- Hash-based database naming to prevent enumeration attacks
- JWT-based authentication for all database access
- No direct database access from external clients

### 3. **Performance Optimization**
- DuckDB for analytics workloads and large dataset processing
- SQLite for lightweight, transactional operations
- PostgreSQL for complex identity relationships
- File system for static content delivery

## Database Components

### PostgreSQL Database
**Purpose**: Keycloak identity and access management
**Location**: Docker container `postgres:15`
**Access Pattern**: Keycloak service only

#### Schema Overview
```sql
-- Core identity tables
users                 -- User accounts and profiles
roles                 -- Role definitions
permissions          -- Permission mappings
user_role_mapping    -- User-role relationships
sessions             -- Active user sessions
realm_config         -- Keycloak realm configuration

-- Authentication
credentials          -- Password hashes and metadata
federated_identity   -- External identity provider links
user_attributes      -- Extended user properties
```

#### Data Characteristics
- **Volume**: Low to medium (hundreds to thousands of users)
- **Access Pattern**: Read-heavy during authentication, write-light
- **Consistency**: ACID compliance required for identity operations
- **Backup**: Critical - contains all user identity data

### SQLite Database
**Purpose**: FastAPI application data and shared state
**Location**: `./app_data/violentutf_api.db`
**Access Pattern**: FastAPI backend only

#### Schema Overview
```sql
-- Application management
api_keys             -- API key management
user_sessions        -- Application session data
audit_logs           -- Security and operation logging
system_config        -- Application configuration
rate_limits          -- Rate limiting counters

-- Operational data
health_checks        -- Service health monitoring
error_logs           -- Application error tracking
```

#### Data Characteristics
- **Volume**: Medium (thousands to tens of thousands of records)
- **Access Pattern**: Mixed read/write during operations
- **Consistency**: ACID for critical operations, eventual consistency acceptable for logs
- **Backup**: Important - contains operational state

### DuckDB Stores
**Purpose**: User-specific configurations and PyRIT memory storage
**Location**: `./app_data/violentutf/pyrit_memory_{user_hash}.db`
**Access Pattern**: User-isolated, per-session access

#### Schema Overview
```sql
-- ViolentUTF Configuration Tables
generators           -- AI generator configurations
datasets             -- Dataset metadata and prompts
dataset_prompts      -- Individual prompt storage
scorers              -- Scorer configurations
converters           -- Converter settings
user_sessions        -- User-specific session data

-- PyRIT Memory Tables (auto-created by PyRIT)
conversations        -- Conversation threads
prompt_request_responses -- Individual prompt/response pairs
embeddings           -- Vector embeddings for similarity
memory_labels        -- Conversation categorization
```

#### User Isolation Strategy
```python
# Database filename generation
salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")
hashed_username = hashlib.sha256(
    salt.encode() + username.encode()
).hexdigest()
db_filename = f"pyrit_memory_{hashed_username}.db"
```

#### Data Characteristics
- **Volume**: High per user (potentially millions of conversation records)
- **Access Pattern**: Analytics-heavy, append-mostly for conversations
- **Consistency**: Eventual consistency acceptable, analytics optimized
- **Backup**: User-specific - can be selective based on user importance

### File System Storage
**Purpose**: Static configurations, datasets, and reports
**Location**: Various directories under `./app_data/`
**Access Pattern**: Direct file I/O from multiple services

#### Directory Structure
```
app_data/
├── violentutf/
│   ├── cache/              # Temporary cache files
│   ├── datasets/           # Garak and custom datasets
│   │   └── garak/         # Pre-built Garak test datasets
│   ├── parameters/        # YAML/JSON configuration files
│   ├── templates/         # Jailbreak and prompt templates
│   └── *.db              # DuckDB user databases
├── config/               # System configuration files
└── reports/             # Generated test reports
```

#### Data Characteristics
- **Volume**: Medium to large (GB of datasets and reports)
- **Access Pattern**: Read-heavy for datasets, write-heavy for reports
- **Consistency**: File system consistency
- **Backup**: Selective - datasets are replaceable, reports may be valuable

## Data Flow Patterns

### 1. **Authentication Flow**
```
User → Streamlit → APISIX → Keycloak → PostgreSQL
                          ↓
                    FastAPI → SQLite (session)
                          ↓
                    DuckDB Manager → User-specific DuckDB
```

### 2. **Configuration Management**
```
User → Streamlit → FastAPI → DuckDB Manager → User DuckDB
                         ↓
                    SQLite (audit log)
```

### 3. **Security Testing Execution**
```
User → Streamlit → FastAPI → PyRIT → DuckDB (memory)
                         ↓         ↓
                    SQLite (log) → File System (reports)
```

### 4. **MCP Tool Access**
```
MCP Client → APISIX → MCP Server → FastAPI → DuckDB/Files
                              ↓
                         User Context → SQLite
```

## Database Integration Patterns

### 1. **User Context Propagation**
All database operations include user context to ensure proper isolation:

```python
# Example: Generator creation
def create_generator(user_context: UserContext, generator_config: dict):
    # Get user-specific DuckDB
    db_manager = get_duckdb_manager(user_context.username)

    # Store in user database
    generator_id = db_manager.create_generator(
        name=generator_config["name"],
        generator_type=generator_config["type"],
        parameters=generator_config["parameters"]
    )

    # Log operation in shared SQLite
    audit_log(user_context.user_id, "generator_created", generator_id)

    return generator_id
```

### 2. **Cross-Database Transactions**
For operations spanning multiple databases, implement compensating transactions:

```python
async def execute_orchestrator(user_id: str, orchestrator_config: dict):
    try:
        # 1. Update SQLite with execution start
        session.add(OrchestratorExecution(
            user_id=user_id,
            status="started",
            config=orchestrator_config
        ))
        await session.commit()

        # 2. Load configuration from DuckDB
        db_manager = get_duckdb_manager(username)
        generator = db_manager.get_generator(orchestrator_config["generator_id"])

        # 3. Execute in PyRIT (creates DuckDB memory records)
        results = await pyrit_orchestrator.execute(generator, dataset)

        # 4. Update SQLite with completion
        execution.status = "completed"
        execution.results_summary = results.summary
        await session.commit()

    except Exception as e:
        # Compensating transaction
        execution.status = "failed"
        execution.error = str(e)
        await session.commit()
        raise
```

## Performance Considerations

### 1. **Database-Specific Optimizations**

#### PostgreSQL (Keycloak)
- Connection pooling through HikariCP
- Read replicas for high-availability deployments
- Regular VACUUM and ANALYZE operations

#### SQLite (FastAPI)
- WAL mode for better concurrency
- Appropriate journal mode for deployment
- Connection pooling for multiple workers

#### DuckDB (User Data)
- Columnar storage for analytics queries
- Automatic query optimization
- Compression for large datasets

### 2. **Caching Strategy**
```python
# Multi-level caching
L1: In-memory application cache (FastAPI)
L2: Redis cache (future enhancement)
L3: Database query optimization
L4: File system cache for static assets
```

### 3. **Query Optimization**
- Index strategy per database type
- Query planning and analysis
- Batch operations for bulk data
- Pagination for large result sets

## Backup and Recovery Strategy

### 1. **Backup Tiers**
- **Tier 1 (Critical)**: PostgreSQL identity data - Daily automated backups
- **Tier 2 (Important)**: SQLite application data - Daily automated backups
- **Tier 3 (User-specific)**: DuckDB user data - Configurable per user importance
- **Tier 4 (Replaceable)**: File system datasets - Weekly snapshots

### 2. **Recovery Procedures**
```bash
# PostgreSQL recovery
docker exec postgres pg_dump keycloak > backup_$(date +%Y%m%d).sql

# SQLite recovery
cp app_data/violentutf_api.db app_data/violentutf_api.db.backup

# DuckDB user recovery
cp app_data/violentutf/pyrit_memory_*.db backups/user_data/

# File system recovery
rsync -av app_data/ backups/file_data/
```

## Security Considerations

### 1. **Access Control**
- Database-level user isolation
- Application-level authorization
- Network isolation through Docker networks
- No direct database access from external clients

### 2. **Data Encryption**
- TLS for all database connections
- Encrypted storage for sensitive data
- Hash-based user database naming
- JWT token-based access control

### 3. **Audit and Monitoring**
- All database operations logged
- Performance monitoring per database
- Security event detection
- Data access pattern analysis

## Migration and Evolution Strategy

### 1. **Schema Evolution**
- Database-specific migration strategies
- Version-controlled schema changes
- Backward compatibility considerations
- Data migration procedures

### 2. **Technology Migration**
Current migration initiatives:
- **DuckDB Deprecation**: Evaluating migration from DuckDB to PostgreSQL for user data
- **Redis Introduction**: Planned caching layer addition
- **Sharding Strategy**: Future horizontal scaling approach

### 3. **Scaling Considerations**
- Horizontal scaling patterns
- Database sharding strategies
- Read replica implementation
- Microservice data patterns

## Conclusion

ViolentUTF's multi-database architecture provides a robust foundation for AI security testing operations. The design balances performance, security, and scalability while maintaining clear separation of concerns. Regular review and optimization of this architecture ensures continued alignment with platform growth and security requirements.

## Related Documentation
- [Component Interaction Maps](../architecture/component-diagrams/database-interaction-map.puml)
- [Data Flow Diagrams](../architecture/data-flows/)
- [ADR: Database Technology Choices](../adr/001-database-technology-choices.md)
- [ADR: DuckDB Deprecation Strategy](../adr/002-duckdb-deprecation-strategy.md)
