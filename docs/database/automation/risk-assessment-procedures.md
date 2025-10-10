# Risk Assessment Automation Procedures

## Overview

This document provides comprehensive operational procedures for the ViolentUTF Risk Assessment Automation Framework implemented in Issue #282. The framework provides NIST RMF-compliant risk scoring, automated vulnerability analysis, and continuous risk monitoring for database infrastructure.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Installation and Setup](#installation-and-setup)
3. [Daily Operations](#daily-operations)
4. [Automated Assessment Procedures](#automated-assessment-procedures)
5. [Risk Alert Management](#risk-alert-management)
6. [Compliance Reporting](#compliance-reporting)
7. [Performance Monitoring](#performance-monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance Procedures](#maintenance-procedures)
10. [Security Considerations](#security-considerations)

## System Architecture

### Core Components

The Risk Assessment Automation Framework consists of:

- **NIST RMF Risk Engine**: Implements 6-step NIST RMF process with 1-25 scale risk scoring
- **Vulnerability Assessment Service**: NIST NVD integration with CVE analysis
- **Security Control Assessor**: NIST SP 800-53 control evaluation
- **Compliance Engine**: Multi-framework compliance assessment (GDPR, SOC 2, NIST CSF)
- **Risk Alerting System**: Real-time risk monitoring with 15-minute alert triggers
- **Trend Analyzer**: Predictive risk analysis with 90% accuracy target

### Performance Requirements

- Risk calculation: ≤ 500ms per asset
- Vulnerability scan: ≤ 10 minutes per asset
- Control assessment: ≤ 2 minutes per asset
- Alert triggering: ≤ 15 minutes for high-risk conditions
- Compliance assessment: ≥ 95% accuracy
- System scalability: 50+ concurrent assessments

## Installation and Setup

### Prerequisites

```bash
# Python dependencies
pip install sqlalchemy asyncpg psycopg2-binary
pip install fastapi uvicorn pydantic
pip install nvdlib  # For NIST NVD integration
pip install asyncio aiofiles

# Database requirements
PostgreSQL 12+ with the following extensions:
- pg_trgm (for text search)
- btree_gin (for composite indexes)
```

### Database Schema Creation

```bash
# Initialize database schema
cd /path/to/violentutf
python scripts/database-automation/risk_assessment.py --operation create_schema

# Verify schema creation
psql -d violentutf -c "\dt risk*"
```

### Configuration

1. **Database Connection Setup**:
```bash
# Set environment variables
export DATABASE_URL="postgresql://violentutf:password@localhost/violentutf"
export ASYNC_DATABASE_URL="postgresql+asyncpg://violentutf:password@localhost/violentutf"
export NIST_NVD_API_KEY="your-nvd-api-key"
```

2. **API Configuration**:
```bash
# Configure FastAPI application
export VIOLENTUTF_API_HOST="0.0.0.0"
export VIOLENTUTF_API_PORT="8000"
export VIOLENTUTF_LOG_LEVEL="INFO"
```

3. **Risk Assessment Configuration**:
```bash
# Configure risk thresholds
export RISK_HIGH_THRESHOLD="15.0"
export RISK_CRITICAL_THRESHOLD="20.0"
export VULNERABILITY_SCAN_FREQUENCY_DAYS="30"
export CONTROL_ASSESSMENT_FREQUENCY_DAYS="90"
```

## Daily Operations

### Morning Checklist

1. **System Health Check**:
```bash
# Check service status
curl -f http://localhost:8000/health || echo "API service down"

# Check database connectivity
python -c "
import asyncpg
import asyncio
async def check_db():
    conn = await asyncpg.connect('$DATABASE_URL')
    result = await conn.fetchval('SELECT COUNT(*) FROM database_assets')
    print(f'Database responsive: {result} assets')
    await conn.close()
asyncio.run(check_db())
"
```

2. **Alert Review**:
```bash
# Check for critical overnight alerts
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/risk/alerts?alert_level=critical&unresolved_only=true"

# Review escalated alerts
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/risk/alerts?escalated=true"
```

3. **Performance Metrics**:
```bash
# Check assessment performance
tail -n 100 /var/log/violentutf/risk_assessment.log | grep "duration" | tail -10

# Check alert response times
psql -d violentutf -c "
SELECT
    alert_level,
    AVG(EXTRACT(EPOCH FROM (acknowledged_at - triggered_at))/60) as avg_response_minutes
FROM risk_alerts
WHERE triggered_at >= CURRENT_DATE - INTERVAL '24 hours'
  AND acknowledged_at IS NOT NULL
GROUP BY alert_level;
"
```

### Evening Procedures

1. **Daily Assessment Summary**:
```bash
# Generate daily risk assessment report
python scripts/database-automation/risk_assessment.py \
  --operation generate_compliance_report \
  --framework all \
  --output-file /var/reports/daily_risk_$(date +%Y%m%d).json
```

2. **System Cleanup**:
```bash
# Process pending alerts
python scripts/database-automation/risk_assessment.py --operation process_alerts

# Schedule next day's assessments
python scripts/database-automation/risk_assessment.py --operation schedule_assessments
```

## Automated Assessment Procedures

### Risk Assessment Scheduling

The system automatically schedules risk assessments based on:
- Asset criticality level
- Previous risk scores
- Compliance requirements
- Industry best practices

```bash
# Manual assessment scheduling for all assets
python scripts/database-automation/risk_assessment.py --operation schedule_assessments

# Schedule specific asset assessment
curl -X POST -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  "http://localhost:8000/api/v1/risk/assessments" \
  -d '{
    "asset_id": "uuid-here",
    "assessment_method": "automated",
    "include_vulnerabilities": true,
    "include_controls": true,
    "force_refresh": false
  }'
```

### Assessment Frequency

| Risk Level | Criticality | Assessment Frequency |
|------------|-------------|---------------------|
| Critical (21-25) | Critical | Monthly (30 days) |
| Very High (16-20) | High | Bi-monthly (60 days) |
| High (11-15) | Medium | Quarterly (90 days) |
| Medium (6-10) | Low | Semi-annually (180 days) |
| Low (1-5) | Any | Annually (365 days) |

### Bulk Assessment Operations

```bash
# Trigger bulk risk assessment
curl -X POST -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  "http://localhost:8000/api/v1/risk/score/bulk" \
  -d '{
    "asset_ids": ["uuid1", "uuid2", "uuid3"],
    "assessment_method": "automated",
    "include_vulnerabilities": true,
    "include_controls": true
  }'

# Monitor bulk assessment progress
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/risk/assessments/bulk-status/{job_id}"
```

## Risk Alert Management

### Alert Types and Thresholds

1. **Risk Score Alerts**:
   - High Risk: Score ≥ 15.0 (warning level)
   - Critical Risk: Score ≥ 20.0 (critical level)
   - Risk Increase: >2.0 point increase within 24 hours

2. **Vulnerability Alerts**:
   - Critical Vulnerabilities: Any CVSS ≥ 9.0 (emergency level)
   - High Vulnerabilities: CVSS ≥ 7.0 with available exploits
   - Vulnerability Count: >10 new vulnerabilities

3. **Control Assessment Alerts**:
   - Control Effectiveness: Overall effectiveness <70%
   - Critical Control Gaps: Missing P1 controls
   - Control Deterioration: >20% effectiveness decrease

### Alert Response Procedures

#### Critical Alerts (15-minute response required)

1. **Immediate Actions**:
```bash
# Acknowledge critical alert
curl -X POST -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/risk/alerts/{alert_id}/acknowledge"

# Get alert details and context
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/risk/alerts/{alert_id}"
```

2. **Assessment and Investigation**:
```bash
# Get latest risk assessment for affected asset
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/risk/assessments/{asset_id}"

# Check vulnerability details
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/risk/vulnerabilities/{asset_id}"
```

3. **Escalation Procedure**:
   - 0-15 minutes: Security team notification
   - 15-30 minutes: Team lead escalation
   - 30-60 minutes: Management escalation
   - 60+ minutes: Executive escalation

#### Alert Resolution

```bash
# Resolve alert after remediation
curl -X POST -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/risk/alerts/{alert_id}/resolve"

# Verify remediation with new assessment
curl -X POST -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  "http://localhost:8000/api/v1/risk/assessments" \
  -d '{
    "asset_id": "affected-asset-uuid",
    "force_refresh": true
  }'
```

### Alert Configuration

```bash
# Configure asset-specific alert thresholds
curl -X POST -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  "http://localhost:8000/api/v1/risk/alerts/configure" \
  -d '{
    "asset_id": "uuid-here",
    "risk_threshold": 15.0,
    "alert_level": "critical",
    "notification_channels": ["email", "webhook"],
    "escalation_rules": {
      "max_escalations": 3,
      "escalation_interval_minutes": 15
    },
    "enabled": true
  }'
```

## Compliance Reporting

### Automated Compliance Assessment

The system provides automated compliance assessment for:
- **GDPR**: General Data Protection Regulation
- **SOC 2**: Service Organization Control 2
- **NIST CSF**: NIST Cybersecurity Framework
- **ISO 27001**: Information Security Management
- **PCI DSS**: Payment Card Industry Data Security Standard

### Daily Compliance Reports

```bash
# Generate comprehensive compliance report
python scripts/database-automation/risk_assessment.py \
  --operation generate_compliance_report \
  --framework all \
  --output-file compliance_report_$(date +%Y%m%d).json

# Framework-specific reports
python scripts/database-automation/risk_assessment.py \
  --operation generate_compliance_report \
  --framework gdpr \
  --output-file gdpr_compliance_$(date +%Y%m%d).json
```

### Compliance Monitoring

```bash
# Check compliance status via API
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/risk/analytics/compliance?framework=gdpr"

# Get compliance trends
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/risk/analytics/trends?days=30"
```

### Monthly Compliance Procedures

1. **Compliance Gap Analysis**:
```sql
-- Identify assets with compliance issues
SELECT
    da.name, da.criticality_level,
    ca.overall_compliance_score,
    ca.gdpr_compliance_score,
    ca.soc2_compliance_score
FROM database_assets da
JOIN compliance_assessments ca ON da.id = ca.asset_id
WHERE ca.overall_compliance_score < 0.95
ORDER BY da.criticality_level DESC, ca.overall_compliance_score ASC;
```

2. **Remediation Planning**:
```bash
# Generate remediation recommendations
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/risk/analytics/recommendations?framework=all"
```

## Performance Monitoring

### Key Performance Indicators (KPIs)

1. **Assessment Performance**:
   - Risk calculation time: Target ≤ 500ms
   - Vulnerability scan time: Target ≤ 10 minutes
   - System availability: Target ≥ 99.5%

2. **Accuracy Metrics**:
   - Compliance assessment accuracy: Target ≥ 95%
   - Risk prediction accuracy: Target ≥ 90%
   - False positive rate: Target ≤ 5%

3. **Operational Metrics**:
   - Alert response time: Target ≤ 15 minutes
   - Assessment coverage: Target 100% of assets
   - Data freshness: Target ≤ 24 hours

### Performance Monitoring Queries

```sql
-- Assessment performance metrics
SELECT
    assessment_method,
    AVG(assessment_duration_seconds) as avg_duration_seconds,
    COUNT(*) as total_assessments,
    COUNT(CASE WHEN assessment_duration_seconds > 0.5 THEN 1 END) as slow_assessments
FROM risk_assessments
WHERE assessment_date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY assessment_method;

-- Alert response time analysis
SELECT
    alert_level,
    AVG(EXTRACT(EPOCH FROM (acknowledged_at - triggered_at))/60) as avg_response_minutes,
    MAX(EXTRACT(EPOCH FROM (acknowledged_at - triggered_at))/60) as max_response_minutes,
    COUNT(*) as total_alerts
FROM risk_alerts
WHERE triggered_at >= CURRENT_DATE - INTERVAL '7 days'
  AND acknowledged_at IS NOT NULL
GROUP BY alert_level;

-- System coverage analysis
SELECT
    COUNT(DISTINCT da.id) as total_assets,
    COUNT(DISTINCT ra.asset_id) as assessed_assets,
    ROUND(100.0 * COUNT(DISTINCT ra.asset_id) / COUNT(DISTINCT da.id), 2) as coverage_percentage
FROM database_assets da
LEFT JOIN risk_assessments ra ON da.id = ra.asset_id
  AND ra.assessment_date >= CURRENT_DATE - INTERVAL '30 days';
```

### Performance Optimization

```bash
# Database maintenance for performance
python scripts/database-automation/risk_assessment.py --operation cleanup_old_data --retention-days 365

# Reindex database tables
psql -d violentutf -c "REINDEX TABLE risk_assessments;"
psql -d violentutf -c "REINDEX TABLE vulnerability_assessments;"
psql -d violentutf -c "ANALYZE;"
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Assessment Timeout Issues

**Symptoms**: Risk assessments taking >500ms, API timeouts

**Diagnosis**:
```bash
# Check assessment performance
grep "duration" /var/log/violentutf/risk_assessment.log | tail -20

# Check database performance
psql -d violentutf -c "
SELECT
    query,
    calls,
    mean_time,
    stddev_time
FROM pg_stat_statements
WHERE query LIKE '%risk_assessments%'
ORDER BY mean_time DESC
LIMIT 10;
"
```

**Solutions**:
- Increase database connection pool size
- Optimize slow queries with additional indexes
- Implement assessment result caching
- Scale to multiple worker processes

#### 2. NIST NVD API Rate Limiting

**Symptoms**: Vulnerability scans failing, HTTP 429 errors

**Diagnosis**:
```bash
# Check NVD API logs
grep "nvd" /var/log/violentutf/vulnerability_service.log | tail -10

# Check API rate limiting
curl -I "https://services.nvd.nist.gov/rest/json/cves/1.0/"
```

**Solutions**:
- Implement exponential backoff
- Use NVD API key for higher rate limits
- Implement intelligent caching
- Batch vulnerability requests

#### 3. Alert Delivery Failures

**Symptoms**: Alerts not triggering, notification failures

**Diagnosis**:
```bash
# Check alert processing
python scripts/database-automation/risk_assessment.py --operation process_alerts

# Check alert delivery status
psql -d violentutf -c "
SELECT
    alert_level,
    COUNT(*) as total_alerts,
    COUNT(CASE WHEN notification_sent = true THEN 1 END) as delivered_alerts,
    AVG(notification_attempts) as avg_attempts
FROM risk_alerts
WHERE triggered_at >= CURRENT_DATE - INTERVAL '24 hours'
GROUP BY alert_level;
"
```

**Solutions**:
- Verify notification service configuration
- Check network connectivity
- Implement retry mechanisms
- Configure alternative notification channels

#### 4. Database Performance Issues

**Symptoms**: Slow queries, high CPU usage, connection timeouts

**Diagnosis**:
```bash
# Check database performance
psql -d violentutf -c "
SELECT
    datname,
    numbackends,
    xact_commit,
    xact_rollback,
    blks_read,
    blks_hit,
    tup_returned,
    tup_fetched
FROM pg_stat_database
WHERE datname = 'violentutf';
"

# Check slow queries
psql -d violentutf -c "
SELECT
    query,
    calls,
    total_time,
    mean_time,
    stddev_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"
```

**Solutions**:
- Create additional database indexes
- Implement query optimization
- Increase shared_buffers and work_mem
- Set up read replicas for reporting

## Maintenance Procedures

### Weekly Maintenance

1. **Data Cleanup**:
```bash
# Clean up old assessment data (retain 1 year)
python scripts/database-automation/risk_assessment.py \
  --operation cleanup_old_data \
  --retention-days 365
```

2. **Performance Analysis**:
```bash
# Generate weekly performance report
psql -d violentutf -f scripts/reports/weekly_performance_report.sql > weekly_report_$(date +%Y%m%d).txt
```

3. **Security Review**:
```bash
# Review access logs
tail -1000 /var/log/violentutf/access.log | grep -E "(POST|PUT|DELETE)" | head -20

# Check for failed authentication attempts
grep "authentication failed" /var/log/violentutf/api.log | wc -l
```

### Monthly Maintenance

1. **Schema Updates**:
```bash
# Check for schema migrations
python scripts/database-automation/risk_assessment.py --operation migrate_data
```

2. **Compliance Audit**:
```bash
# Generate monthly compliance audit
python scripts/database-automation/risk_assessment.py \
  --operation generate_compliance_report \
  --framework all \
  --output-file monthly_compliance_audit_$(date +%Y%m).json
```

3. **Capacity Planning**:
```bash
# Analyze database growth
psql -d violentutf -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### Quarterly Maintenance

1. **Disaster Recovery Testing**:
```bash
# Test database backup and restore procedures
pg_dump violentutf > backup_test_$(date +%Y%m%d).sql
createdb violentutf_test
psql violentutf_test < backup_test_$(date +%Y%m%d).sql
```

2. **Security Assessment**:
```bash
# Run security assessment on the risk assessment system
python scripts/security/assess_risk_system.py --comprehensive
```

3. **Performance Optimization**:
```bash
# Comprehensive database optimization
psql -d violentutf -c "VACUUM FULL ANALYZE;"
psql -d violentutf -c "REINDEX DATABASE violentutf;"
```

## Security Considerations

### Access Control

1. **API Authentication**:
   - All API endpoints require JWT authentication
   - Role-based access control (RBAC) for different operations
   - API rate limiting to prevent abuse

2. **Database Security**:
   - Database connections use SSL/TLS encryption
   - Separate database users for different services
   - Regular security patches and updates

3. **Data Protection**:
   - Sensitive data encrypted at rest
   - PII data properly classified and protected
   - Audit logging for all data access

### Compliance and Auditing

1. **Audit Trail**:
```bash
# Review audit logs
tail -100 /var/log/violentutf/audit.log | grep -E "(CREATE|UPDATE|DELETE)"

# Check data access patterns
psql -d violentutf -c "
SELECT
    username,
    action,
    table_name,
    COUNT(*) as access_count
FROM audit_log
WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY username, action, table_name
ORDER BY access_count DESC;
"
```

2. **Compliance Monitoring**:
```bash
# Monitor compliance status
curl -H "Authorization: Bearer $API_TOKEN" \
  "http://localhost:8000/api/v1/risk/analytics/compliance-status"
```

### Incident Response

1. **Security Incident Detection**:
   - Monitor for unusual risk score changes
   - Alert on critical vulnerability discoveries
   - Track compliance violations

2. **Response Procedures**:
   - Immediate assessment of affected assets
   - Risk score recalculation
   - Compliance impact analysis
   - Remediation tracking

## API Reference Quick Guide

### Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/risk/assessments` | POST | Trigger risk assessment |
| `/api/v1/risk/assessments/{asset_id}` | GET | Get latest assessment |
| `/api/v1/risk/score` | POST | Real-time risk scoring |
| `/api/v1/risk/vulnerabilities/scan` | POST | Trigger vulnerability scan |
| `/api/v1/risk/alerts` | GET | Get active alerts |
| `/api/v1/risk/analytics/trends` | GET | Risk trend analysis |

### Authentication

All API requests require JWT token in Authorization header:
```bash
Authorization: Bearer <jwt_token>
```

### Error Handling

Standard HTTP status codes:
- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 404: Not Found
- 500: Internal Server Error

## Support and Contact Information

- **Technical Issues**: Submit ticket to IT Security team
- **Compliance Questions**: Contact Compliance Officer
- **Emergency Response**: Use security incident response procedures
- **System Documentation**: See `/docs/api/` for detailed API documentation

---

**Document Version**: 1.0
**Last Updated**: 2025-01-19
**Next Review Date**: 2025-04-19
**Document Owner**: Security Engineering Team
