# PostgreSQL Database Schema Documentation - Keycloak SSO

## Schema Overview

**Database**: `keycloak`
**Version**: PostgreSQL 15
**Purpose**: Authentication and authorization for ViolentUTF platform
**Owner**: Infrastructure Team
**Last Updated**: 2025-09-18

This document provides comprehensive schema documentation for the PostgreSQL database supporting Keycloak SSO authentication in the ViolentUTF platform.

## Database Configuration

### Connection Details
- **Host**: `postgres` (Docker container)
- **Port**: 5432 (internal)
- **Database Name**: `keycloak`
- **Default User**: `keycloak`
- **Network**: `postgres-network`, `vutf-network`
- **Volume**: `postgres_data:/var/lib/postgresql/data`

### Keycloak Integration
- **Keycloak Version**: 26.1.4
- **Driver**: PostgreSQL JDBC
- **Connection Pool**: Managed by Keycloak
- **Transaction Isolation**: READ_COMMITTED
- **Auto-commit**: Disabled (managed transactions)

## Expected Schema Structure

*Note: This documentation represents the expected Keycloak schema structure. Actual table details would be obtained through direct database inspection in a production environment.*

### Core Authentication Tables

#### realm
```sql
CREATE TABLE realm (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    display_name_html TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    ssl_required VARCHAR(20),
    registration_allowed BOOLEAN DEFAULT FALSE,
    registration_email_as_username BOOLEAN DEFAULT FALSE,
    remember_me BOOLEAN DEFAULT FALSE,
    verify_email BOOLEAN DEFAULT FALSE,
    login_with_email_allowed BOOLEAN DEFAULT TRUE,
    duplicate_emails_allowed BOOLEAN DEFAULT FALSE,
    reset_password_allowed BOOLEAN DEFAULT FALSE,
    edit_username_allowed BOOLEAN DEFAULT FALSE,
    brute_force_protected BOOLEAN DEFAULT FALSE,
    permanent_lockout BOOLEAN DEFAULT FALSE,
    max_failure_wait_seconds INTEGER DEFAULT 900,
    minimum_quick_login_wait_seconds INTEGER DEFAULT 60,
    wait_increment_seconds INTEGER DEFAULT 60,
    quick_login_check_milli_seconds BIGINT DEFAULT 1000,
    max_delta_time_seconds INTEGER DEFAULT 43200,
    failure_factor INTEGER DEFAULT 30,
    default_locale VARCHAR(255),
    default_roles VARCHAR(255),
    password_policy TEXT,
    otp_policy_counter INTEGER DEFAULT 0,
    otp_policy_window INTEGER DEFAULT 1,
    otp_policy_period INTEGER DEFAULT 30,
    otp_policy_digits INTEGER DEFAULT 6,
    otp_policy_alg VARCHAR(36) DEFAULT 'HmacSHA1',
    otp_policy_type VARCHAR(36) DEFAULT 'totp',
    browser_flow VARCHAR(36),
    registration_flow VARCHAR(36),
    direct_grant_flow VARCHAR(36),
    reset_credentials_flow VARCHAR(36),
    client_auth_flow VARCHAR(36),
    offline_session_idle_timeout INTEGER DEFAULT 2592000,
    revoke_refresh_token BOOLEAN DEFAULT FALSE,
    access_token_life_implicit INTEGER DEFAULT 900,
    login_lifespan INTEGER DEFAULT 1800,
    sso_session_idle_timeout INTEGER DEFAULT 1800,
    sso_session_max_lifespan INTEGER DEFAULT 36000,
    sso_session_idle_timeout_remember_me INTEGER DEFAULT 0,
    sso_session_max_lifespan_remember_me INTEGER DEFAULT 0,
    offline_session_max_lifespan INTEGER DEFAULT 5184000,
    offline_session_max_lifespan_enabled BOOLEAN DEFAULT FALSE,
    access_code_lifespan INTEGER DEFAULT 60,
    access_code_lifespan_user_action INTEGER DEFAULT 300,
    access_code_lifespan_login INTEGER DEFAULT 1800,
    action_token_generated_by_admin_lifespan INTEGER DEFAULT 43200,
    action_token_generated_by_user_lifespan INTEGER DEFAULT 300,
    oauth2_device_code_lifespan INTEGER DEFAULT 600,
    oauth2_device_polling_interval INTEGER DEFAULT 5,
    enabled_event_types VARCHAR(255),
    events_enabled BOOLEAN DEFAULT FALSE,
    events_expiration BIGINT,
    admin_events_enabled BOOLEAN DEFAULT FALSE,
    admin_events_details_enabled BOOLEAN DEFAULT FALSE,
    master_admin_client VARCHAR(36),
    internationalization_enabled BOOLEAN DEFAULT FALSE,
    supported_locales VARCHAR(255),
    browser_security_headers TEXT,
    smtp_server TEXT,
    login_theme VARCHAR(255),
    account_theme VARCHAR(255),
    admin_theme VARCHAR(255),
    email_theme VARCHAR(255)
);
```

#### user_entity
```sql
CREATE TABLE user_entity (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    email VARCHAR(255),
    email_constraint VARCHAR(255),
    email_verified BOOLEAN DEFAULT FALSE,
    enabled BOOLEAN DEFAULT FALSE,
    federation_link VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    realm_id VARCHAR(36) NOT NULL,
    username VARCHAR(255),
    created_timestamp BIGINT,
    service_account_client_link VARCHAR(255),
    not_before INTEGER DEFAULT 0,
    CONSTRAINT fk_user_realm FOREIGN KEY (realm_id) REFERENCES realm(id)
);

CREATE UNIQUE INDEX idx_user_email ON user_entity(realm_id, email_constraint);
CREATE UNIQUE INDEX idx_user_username ON user_entity(realm_id, username);
CREATE INDEX idx_user_realm ON user_entity(realm_id);
```

#### user_session
```sql
CREATE TABLE user_session (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    auth_method VARCHAR(255),
    ip_address VARCHAR(255),
    last_session_refresh INTEGER,
    login_username VARCHAR(255),
    realm_id VARCHAR(255),
    remember_me BOOLEAN DEFAULT FALSE,
    started INTEGER,
    user_id VARCHAR(36),
    user_session_state INTEGER,
    broker_session_id VARCHAR(255),
    broker_user_id VARCHAR(255)
);

CREATE INDEX idx_user_session_user ON user_session(user_id);
CREATE INDEX idx_user_session_realm ON user_session(realm_id);
```

#### client
```sql
CREATE TABLE client (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    enabled BOOLEAN DEFAULT FALSE,
    full_scope_allowed BOOLEAN DEFAULT FALSE,
    client_id VARCHAR(255),
    not_before INTEGER,
    public_client BOOLEAN DEFAULT FALSE,
    secret VARCHAR(255),
    base_url VARCHAR(255),
    bearer_only BOOLEAN DEFAULT FALSE,
    management_url VARCHAR(255),
    surrogate_auth_required BOOLEAN DEFAULT FALSE,
    realm_id VARCHAR(36),
    protocol VARCHAR(255),
    node_rereg_timeout INTEGER DEFAULT 0,
    frontchannel_logout BOOLEAN DEFAULT FALSE,
    consent_required BOOLEAN DEFAULT FALSE,
    name VARCHAR(255),
    service_accounts_enabled BOOLEAN DEFAULT FALSE,
    client_authenticator_type VARCHAR(255),
    root_url VARCHAR(255),
    description VARCHAR(255),
    registration_token VARCHAR(255),
    standard_flow_enabled BOOLEAN DEFAULT TRUE,
    implicit_flow_enabled BOOLEAN DEFAULT FALSE,
    direct_access_grants_enabled BOOLEAN DEFAULT FALSE,
    always_display_in_console BOOLEAN DEFAULT FALSE,
    CONSTRAINT fk_client_realm FOREIGN KEY (realm_id) REFERENCES realm(id)
);

CREATE UNIQUE INDEX idx_client_client_id ON client(realm_id, client_id);
CREATE INDEX idx_client_realm ON client(realm_id);
```

### Authentication and Authorization Tables

#### client_session
```sql
CREATE TABLE client_session (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    client_id VARCHAR(36),
    redirect_uri VARCHAR(255),
    state VARCHAR(255),
    timestamp INTEGER,
    session_id VARCHAR(36),
    auth_method VARCHAR(255),
    realm_id VARCHAR(255),
    auth_user_id VARCHAR(36),
    current_action VARCHAR(36),
    CONSTRAINT fk_client_session_session FOREIGN KEY (session_id) REFERENCES user_session(id)
);

CREATE INDEX idx_client_session_session ON client_session(session_id);
```

#### role_entity
```sql
CREATE TABLE role_entity (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    client_role BOOLEAN DEFAULT FALSE,
    client_realm_constraint VARCHAR(255),
    description VARCHAR(255),
    name VARCHAR(255),
    realm_id VARCHAR(36),
    client_id VARCHAR(36),
    realm VARCHAR(36),
    CONSTRAINT fk_role_realm FOREIGN KEY (realm_id) REFERENCES realm(id),
    CONSTRAINT fk_role_client FOREIGN KEY (client_id) REFERENCES client(id)
);

CREATE UNIQUE INDEX idx_role_name ON role_entity(name, client_id);
CREATE INDEX idx_role_realm ON role_entity(realm_id);
```

#### user_role_mapping
```sql
CREATE TABLE user_role_mapping (
    role_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    PRIMARY KEY (role_id, user_id),
    CONSTRAINT fk_user_role_user FOREIGN KEY (user_id) REFERENCES user_entity(id),
    CONSTRAINT fk_user_role_role FOREIGN KEY (role_id) REFERENCES role_entity(id)
);

CREATE INDEX idx_user_role_mapping_user ON user_role_mapping(user_id);
CREATE INDEX idx_user_role_mapping_role ON user_role_mapping(role_id);
```

### Configuration and Metadata Tables

#### realm_attribute
```sql
CREATE TABLE realm_attribute (
    name VARCHAR(255) NOT NULL,
    realm_id VARCHAR(36) NOT NULL,
    value TEXT,
    PRIMARY KEY (name, realm_id),
    CONSTRAINT fk_realm_attr_realm FOREIGN KEY (realm_id) REFERENCES realm(id)
);
```

#### client_attributes
```sql
CREATE TABLE client_attributes (
    client_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    value TEXT,
    PRIMARY KEY (client_id, name),
    CONSTRAINT fk_client_attr_client FOREIGN KEY (client_id) REFERENCES client(id)
);
```

#### user_attribute
```sql
CREATE TABLE user_attribute (
    name VARCHAR(255) NOT NULL,
    value VARCHAR(255),
    user_id VARCHAR(36) NOT NULL,
    id VARCHAR(36) DEFAULT gen_random_uuid() PRIMARY KEY,
    CONSTRAINT fk_user_attr_user FOREIGN KEY (user_id) REFERENCES user_entity(id)
);

CREATE INDEX idx_user_attribute ON user_attribute(user_id);
CREATE INDEX idx_user_attr_name ON user_attribute(name, value);
```

### Events and Audit Tables

#### event_entity
```sql
CREATE TABLE event_entity (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    client_id VARCHAR(255),
    details_json VARCHAR(2550),
    error VARCHAR(255),
    ip_address VARCHAR(255),
    realm_id VARCHAR(255),
    session_id VARCHAR(255),
    event_time BIGINT,
    type VARCHAR(255),
    user_id VARCHAR(255),
    details_json_long_value TEXT
);

CREATE INDEX idx_event_time ON event_entity(realm_id, event_time);
CREATE INDEX idx_event_user ON event_entity(realm_id, user_id);
CREATE INDEX idx_event_type ON event_entity(realm_id, type);
```

#### admin_event_entity
```sql
CREATE TABLE admin_event_entity (
    id VARCHAR(36) NOT NULL PRIMARY KEY,
    admin_event_time BIGINT,
    realm_id VARCHAR(255),
    operation_type VARCHAR(255),
    auth_realm_id VARCHAR(255),
    auth_client_id VARCHAR(255),
    auth_user_id VARCHAR(255),
    ip_address VARCHAR(255),
    resource_path VARCHAR(2550),
    representation TEXT,
    error VARCHAR(255),
    resource_type VARCHAR(64)
);

CREATE INDEX idx_admin_event_time ON admin_event_entity(realm_id, admin_event_time);
CREATE INDEX idx_admin_event_user ON admin_event_entity(realm_id, auth_user_id);
```

## Data Relationships and Constraints

### Primary Relationships
1. **Realm → User**: One realm contains many users
2. **User → Session**: One user can have multiple sessions
3. **User → Role**: Many-to-many relationship through user_role_mapping
4. **Client → Session**: One client can have multiple sessions
5. **Realm → Client**: One realm contains many clients

### Foreign Key Constraints
- All entities reference their parent realm
- User sessions link to users and clients
- Role mappings link users to roles
- Attributes link to their parent entities

### Cascading Rules
- **ON DELETE CASCADE**: Child records deleted when parent is removed
- **ON UPDATE CASCADE**: Foreign keys updated when parent key changes
- **Referential Integrity**: Enforced at database level

## Performance Optimization

### Indexing Strategy
- **Primary Keys**: Clustered indexes on all primary keys
- **Foreign Keys**: Non-clustered indexes on all foreign key columns
- **Lookup Columns**: Indexes on frequently searched columns (username, email, client_id)
- **Composite Indexes**: Multi-column indexes for common query patterns

### Query Optimization
- **Authentication Queries**: Optimized for username/email lookup
- **Session Queries**: Optimized for session validation and cleanup
- **Role Queries**: Optimized for permission checking
- **Audit Queries**: Optimized for event retrieval and reporting

### Performance Characteristics
- **Read-Heavy Workload**: Optimized for authentication and authorization checks
- **Write Operations**: Insert-heavy for sessions and events
- **Batch Operations**: Cleanup operations for expired sessions and events
- **Concurrent Access**: High concurrency support for authentication

## Security Considerations

### Data Encryption
- **Passwords**: Hashed using bcrypt with configurable rounds
- **Tokens**: Encrypted using Keycloak's internal encryption
- **Sensitive Attributes**: Encrypted at application level
- **Database Encryption**: Available through PostgreSQL encryption features

### Access Control
- **Database User**: Limited to Keycloak service account
- **Network Access**: Restricted to internal Docker networks
- **Connection Security**: SSL/TLS enabled for connections
- **Privilege Escalation**: Minimal database privileges granted

### Audit Trail
- **Login Events**: Tracked in event_entity table
- **Administrative Actions**: Tracked in admin_event_entity table
- **Configuration Changes**: Logged with full details
- **Data Retention**: Configurable retention periods for audit data

## Maintenance and Operations

### Regular Maintenance
- **Session Cleanup**: Automatic cleanup of expired sessions
- **Event Cleanup**: Periodic cleanup of old audit events
- **Index Maintenance**: PostgreSQL automatic index maintenance
- **Statistics Update**: Automatic statistics updates for query optimization

### Monitoring Points
- **Connection Count**: Monitor active database connections
- **Query Performance**: Monitor slow queries and optimization opportunities
- **Table Size Growth**: Monitor growth of sessions and events tables
- **Lock Contention**: Monitor for blocking and deadlocks

### Backup Strategy
- **Full Backups**: Daily full database backups
- **Incremental Backups**: Hourly transaction log backups
- **Point-in-Time Recovery**: Available through PostgreSQL WAL
- **Cross-Region Replication**: Available for disaster recovery

## ViolentUTF Integration

### Realm Configuration
- **Realm Name**: `violentutf`
- **Client Applications**: ViolentUTF Streamlit UI, FastAPI Backend
- **User Federation**: Local user management (no external federation)
- **Session Configuration**: 30-minute idle timeout, 8-hour maximum session

### Client Configuration
- **violentutf-ui**: Public client for Streamlit application
- **violentutf-api**: Confidential client for FastAPI backend
- **Token Exchange**: OAuth 2.0 Authorization Code flow
- **JWT Configuration**: RS256 signing, 15-minute token lifetime

### Role Configuration
- **ai-api-access**: Basic access role for ViolentUTF users
- **admin**: Administrative access for platform management
- **security-analyst**: Enhanced access for security testing
- **read-only**: Limited access for auditing and monitoring

### Custom Attributes
- **department**: User's organizational department
- **clearance_level**: Security clearance level for access control
- **last_training**: Date of last security training
- **approved_tools**: List of approved security tools for user

## Troubleshooting

### Common Issues
1. **Connection Failures**: Check network connectivity and credentials
2. **Session Timeouts**: Review session configuration and user activity
3. **Role Assignment Issues**: Verify role mappings and client configuration
4. **Performance Degradation**: Monitor query performance and index usage

### Diagnostic Queries
```sql
-- Check active sessions
SELECT COUNT(*) FROM user_session WHERE user_session_state = 0;

-- Check recent login events
SELECT type, COUNT(*) FROM event_entity
WHERE event_time > extract(epoch from now() - interval '1 hour') * 1000
GROUP BY type;

-- Check client configuration
SELECT client_id, enabled, protocol FROM client WHERE realm_id = 'violentutf';

-- Check user activity
SELECT u.username, COUNT(s.id) as active_sessions
FROM user_entity u
LEFT JOIN user_session s ON u.id = s.user_id
WHERE u.realm_id = 'violentutf'
GROUP BY u.username;
```

### Recovery Procedures
1. **Database Corruption**: Restore from backup, verify data integrity
2. **Authentication Failure**: Check client configuration and certificates
3. **Performance Issues**: Analyze query plans, update statistics, rebuild indexes
4. **Data Inconsistency**: Run consistency checks, repair foreign key violations

---

**Document Information**
- **Classification**: INTERNAL
- **Review Cycle**: Quarterly
- **Next Review**: 2025-12-18
- **Contact**: Infrastructure Team, Database Administrator
- **Related Documents**: Database Inventory, Risk Assessment, Operational Procedures
