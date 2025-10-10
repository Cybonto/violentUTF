# SQLite Migration Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the SQLite migration (PyRIT v0.10.0+) in ViolentUTF production environments.

**Migration Context**: PyRIT v0.10.0rc0 migrated from DuckDB to SQLite for memory storage. This guide covers the deployment process for aligning ViolentUTF with this upstream change.

**Related Documentation**:
- [ADR-003: SQLite Alignment Strategy](../adr/003-sqlite-alignment-strategy.md)
- [Issue #269: SQLite Migration](https://github.com/Cybonto/violentUTF/issues/269)
- [Issue #328: Production Deployment](https://github.com/Cybonto/violentUTF/issues/328)

## Pre-Deployment Checklist

Before deploying the SQLite migration:

- [ ] All tests passing in staging environment
- [ ] Performance validation complete (ADR-003 benchmarks met)
- [ ] Data migration validation complete
- [ ] Rollback plan tested and validated
- [ ] Downtime window scheduled and communicated
- [ ] Backup strategy verified
- [ ] Stakeholder approval obtained

## Deployment Steps

### Step 1: Create Final Production Backup

**Purpose**: Ensure all DuckDB files are backed up before migration.

```bash
# Navigate to repository root
cd /path/to/violentUTF

# Run backup script with verification
./scripts/migration-management/backup_duckdb_files.sh --verify-checksums

# Verify backup integrity
./scripts/migration-management/verify_backup_integrity.sh
```

**Validation**:
- Backup directory created with timestamp
- Checksums generated and verified
- Backup manifest created with metadata
- All DuckDB files backed up successfully

### Step 2: Stop Services

**Purpose**: Ensure clean shutdown before dependency changes.

```bash
# Stop all Docker services
docker-compose down

# Verify all services stopped
docker ps
# Should show no violentutf-related containers
```

**Downtime Begins**: Note the time for downtime tracking.

### Step 3: Upgrade PyRIT Dependency

**Purpose**: Install PyRIT v0.10.0+ with SQLite support.

```bash
# Activate virtual environment
source .vitutf/bin/activate

# Upgrade PyRIT to v0.10.0rc0 or later
pip install --upgrade 'pyrit>=0.10.0rc0'

# Verify installation
pip list | grep pyrit
# Should show pyrit 0.10.0rc0 or later
```

**Expected Changes**:
- PyRIT version upgraded from 0.9.0 to 0.10.0+
- DuckDB dependency automatically removed
- SQLite becomes the storage backend

### Step 4: Start Services

**Purpose**: Bring services back online with new PyRIT version.

```bash
# Start Docker services
docker-compose up -d

# Monitor service startup
docker-compose logs -f
# Watch for any errors during startup
# Press Ctrl+C to exit log monitoring
```

**Expected Behavior**:
- Services start successfully
- PyRIT initializes SQLite databases automatically
- No DuckDB-related errors in logs

### Step 5: Verify Service Health

**Purpose**: Confirm all services are running and healthy.

```bash
# Run health check script
./check_services.sh

# Expected output:
# ✓ APISIX Gateway: healthy
# ✓ Keycloak SSO: healthy
# ✓ FastAPI Backend: healthy
# ✓ Streamlit Dashboard: healthy
```

**Manual Verification**:
```bash
# Test API endpoint
curl http://localhost:9080/health

# Test Streamlit
curl http://localhost:8501
```

**Downtime Ends**: If all health checks pass, note the time.

### Step 6: Run Smoke Tests

**Purpose**: Validate critical functionality post-deployment.

```bash
# Run all smoke tests
pytest tests/smoke_tests/ -v

# Expected results:
# - test_api_health.py: 4 passed
# - test_database_connectivity.py: 4 passed
# Total: 8 passed
```

**If Tests Fail**: Proceed to Rollback section immediately.

### Step 7: Verify Database Migration

**Purpose**: Confirm SQLite databases are being used.

```bash
# Check for SQLite database files
find app_data/violentutf -name "*.db" -type f

# Verify file types
file app_data/violentutf/pyrit_memory_*.db
# Should show: "SQLite 3.x database"

# Check database sizes
ls -lh app_data/violentutf/pyrit_memory_*.db
```

**Expected State**:
- New SQLite database files present
- Old DuckDB files remain (archived, not deleted)
- SQLite files functional and accessible

### Step 8: Monitor Post-Deployment Health

**Purpose**: Continuous monitoring for 24-48 hours post-deployment.

```bash
# Start health monitoring (runs for 24 hours)
./scripts/migration-management/monitor_production_health.sh \
    --interval 60 \
    --duration 1440 \
    --report reports/migration_health_$(date +%Y%m%d).json
```

**Monitoring Includes**:
- API endpoint health and response times
- Database file accessibility and sizes
- Error rates in application logs
- System resource usage

**Alert Thresholds**:
- API response time > 5 seconds
- HTTP 500 errors detected
- Database files inaccessible
- Error rate > 10%

### Step 9: User Validation

**Purpose**: Validate key user workflows function correctly.

Test these workflows manually or with automated tests:

1. **User Authentication**:
   - Navigate to http://localhost:8501
   - Log in with test credentials
   - Verify successful authentication

2. **Create Generator**:
   - Create a new generator configuration
   - Verify it saves successfully

3. **Import Dataset**:
   - Import a test dataset
   - Verify dataset appears in UI

4. **Run PyRIT Orchestrator**:
   - Execute a simple PyRIT workflow
   - Verify conversation data stores correctly
   - Check SQLite database for new entries

5. **Delete Resources**:
   - Delete test generator and dataset
   - Verify cleanup successful

### Step 10: Document Deployment

**Purpose**: Record deployment details for audit trail.

Create deployment record:
```bash
# Create deployment report
cat > reports/deployment_$(date +%Y%m%d).md << EOF
# SQLite Migration Deployment

## Deployment Details
- Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- PyRIT Version: $(pip show pyrit | grep Version)
- Downtime: [START_TIME] to [END_TIME]
- Duration: [X minutes]

## Validation Results
- Service Health: ✓ All services healthy
- Smoke Tests: ✓ 8/8 passed
- User Workflows: ✓ All workflows functional
- Database Migration: ✓ SQLite databases operational

## Issues Encountered
- [List any issues and resolutions]

## Next Steps
- Monitor for 30-day validation period
- Schedule DuckDB cleanup for [DATE + 30 days]
- Update documentation as needed
EOF
```

## Post-Deployment Tasks

### 30-Day Validation Period

During the 30-day validation period:

1. **Daily Health Checks**:
   ```bash
   ./check_services.sh
   pytest tests/smoke_tests/ -v
   ```

2. **Weekly Performance Review**:
   - Review response time metrics
   - Check error rates
   - Monitor database file sizes
   - Review user feedback

3. **Monthly Cleanup** (After 30 days):
   ```bash
   # Archive old DuckDB files
   ./scripts/migration-management/archive_duckdb_files.sh

   # Clean up archived backups (optional)
   rm -rf backups/duckdb_backup_*
   ```

## Rollback Procedure

If critical issues are discovered, rollback immediately:

### Emergency Rollback Steps

```bash
# 1. Stop services
docker-compose down

# 2. Revert PyRIT version
source .vitutf/bin/activate
pip install 'pyrit>=0.4.0,<0.10.0'

# 3. Restore DuckDB files from latest backup
LATEST_BACKUP=$(ls -t backups/ | grep duckdb_backup | head -1)
rsync -av "backups/${LATEST_BACKUP}/" app_data/violentutf/

# 4. Verify backup restoration
./scripts/migration-management/verify_backup_integrity.sh \
    --backup-dir "backups/${LATEST_BACKUP}"

# 5. Restart services
docker-compose up -d

# 6. Verify rollback successful
./check_services.sh
pytest tests/smoke_tests/ -v
```

### Rollback Validation

After rollback:
- [ ] All services healthy
- [ ] DuckDB databases accessible
- [ ] PyRIT operations functional
- [ ] User workflows working
- [ ] No errors in logs

### Post-Rollback Actions

1. **Root Cause Analysis**:
   - Identify what caused the rollback
   - Document issues encountered
   - Plan remediation steps

2. **Communication**:
   - Notify stakeholders of rollback
   - Explain issues encountered
   - Provide timeline for retry

3. **Plan Remediation**:
   - Fix identified issues
   - Test in staging environment
   - Schedule new deployment window

## Troubleshooting

### Issue: PyRIT Import Errors

**Symptoms**: `ModuleNotFoundError: No module named 'pyrit'` or similar

**Solution**:
```bash
source .vitutf/bin/activate
pip install --upgrade 'pyrit>=0.10.0rc0'
```

### Issue: Database File Not Found

**Symptoms**: `FileNotFoundError` for database files

**Solution**:
```bash
# Check if database directory exists
ls -la app_data/violentutf/

# If missing, create directory
mkdir -p app_data/violentutf/

# Restart services to initialize databases
docker-compose restart
```

### Issue: Service Won't Start

**Symptoms**: Docker containers crash or fail to start

**Solution**:
```bash
# Check logs for errors
docker-compose logs violentutf-api
docker-compose logs streamlit

# Common issues:
# - Port conflicts: Check with `lsof -i :8501` and `lsof -i :9080`
# - Permissions: Check file permissions on app_data/
# - Dependencies: Verify requirements.txt up to date
```

### Issue: Slow Performance

**Symptoms**: Response times > 5 seconds

**Solution**:
```bash
# Check SQLite database size
ls -lh app_data/violentutf/*.db

# Optimize SQLite databases
sqlite3 app_data/violentutf/pyrit_memory_*.db "VACUUM;"
sqlite3 app_data/violentutf/pyrit_memory_*.db "ANALYZE;"

# Enable WAL mode for better concurrency
sqlite3 app_data/violentutf/pyrit_memory_*.db "PRAGMA journal_mode=WAL;"
```

### Issue: Database Locked Errors

**Symptoms**: `database is locked` errors in logs

**Solution**:
```bash
# Enable WAL mode
for db in app_data/violentutf/*.db; do
    sqlite3 "$db" "PRAGMA journal_mode=WAL;"
done

# Adjust timeout settings
sqlite3 app_data/violentutf/*.db "PRAGMA busy_timeout=5000;"

# Restart services
docker-compose restart
```

## Monitoring and Alerts

### Key Metrics to Monitor

1. **API Response Times**:
   - Threshold: < 5 seconds
   - Alert: Response time > 5s for 5 consecutive requests

2. **Error Rates**:
   - Threshold: < 1% error rate
   - Alert: Error rate > 5% over 5-minute window

3. **Database File Sizes**:
   - Threshold: < 1GB per database
   - Alert: Database file > 1GB

4. **Service Health**:
   - Threshold: All services healthy
   - Alert: Any service unhealthy for > 1 minute

### Monitoring Commands

```bash
# API health check
curl -f http://localhost:9080/health || echo "API unhealthy"

# Database file sizes
du -sh app_data/violentutf/*.db

# Error count in logs (last hour)
docker-compose logs --since 1h | grep -i error | wc -l

# Service status
docker-compose ps
```

## Success Criteria

Deployment is considered successful when:

- [ ] All services healthy for 24 hours
- [ ] Smoke tests passing consistently
- [ ] No critical errors in logs
- [ ] User workflows functional
- [ ] Performance within acceptable thresholds (< 50% slower than DuckDB baseline)
- [ ] SQLite databases operational
- [ ] No rollback required

## References

- [ADR-003: SQLite Alignment Strategy](../adr/003-sqlite-alignment-strategy.md)
- [PyRIT Documentation](https://github.com/Azure/PyRIT)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [ViolentUTF Architecture Overview](../database/architecture-overview.md)

## Support

For issues or questions:
- GitHub Issues: https://github.com/Cybonto/violentUTF/issues
- Documentation: `/docs/`
- Troubleshooting Guides: `/docs/troubleshooting/`
