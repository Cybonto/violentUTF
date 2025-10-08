# Database Performance Monitoring Integration with check_services.sh

## Overview

This document describes how to integrate database performance monitoring checks into the existing `check_services.sh` health validation script.

## Integration Points

### 1. Database Metrics Collection Health

Add check for metrics collectors:

```bash
# Check PostgreSQL metrics collector
check_postgres_metrics() {
    echo "Checking PostgreSQL metrics collection..."

    # Test metrics collection endpoint
    response=$(curl -s -X GET "http://localhost:9080/api/v1/monitoring/database/overview" \
        -H "Authorization: Bearer $AUTH_TOKEN")

    if echo "$response" | grep -q '"overall_status":"healthy"'; then
        echo "  ✓ PostgreSQL metrics collection: OK"
        return 0
    else
        echo "  ✗ PostgreSQL metrics collection: FAILED"
        return 1
    fi
}

# Check SQLite metrics collector
check_sqlite_metrics() {
    echo "Checking SQLite metrics collection..."

    # Similar implementation as PostgreSQL
    # Check for SQLite database in response
}
```

### 2. Baseline Status Check

Add check for baseline availability:

```bash
check_performance_baselines() {
    echo "Checking performance baselines..."

    response=$(curl -s -X GET "http://localhost:9080/api/v1/monitoring/database/baselines" \
        -H "Authorization: Bearer $AUTH_TOKEN")

    baseline_count=$(echo "$response" | jq -r '.baselines | length')

    if [ "$baseline_count" -gt 0 ]; then
        echo "  ✓ Performance baselines: $baseline_count baselines active"
        return 0
    else
        echo "  ⚠ Performance baselines: No baselines calculated yet"
        return 0  # Warning, not failure
    fi
}
```

### 3. Alert Status Check

Add check for active database alerts:

```bash
check_database_alerts() {
    echo "Checking database performance alerts..."

    response=$(curl -s -X GET "http://localhost:9080/api/v1/monitoring/alerts?severity=critical" \
        -H "Authorization: Bearer $AUTH_TOKEN")

    critical_count=$(echo "$response" | jq -r '. | length')

    if [ "$critical_count" -eq 0 ]; then
        echo "  ✓ Database alerts: No critical alerts"
        return 0
    else
        echo "  ⚠ Database alerts: $critical_count critical alerts active"
        return 1
    fi
}
```

### 4. Integration into Main Check

Add to main check sequence in `check_services.sh`:

```bash
# After existing service checks
echo ""
echo "=== Database Performance Monitoring ==="

check_postgres_metrics
check_sqlite_metrics
check_performance_baselines
check_database_alerts

echo ""
```

## Authentication

The monitoring endpoints require JWT authentication. The check script should:

1. Use service account credentials or
2. Use a monitoring-specific API key

Example authentication setup:

```bash
# Get auth token for monitoring checks
AUTH_TOKEN=$(get_monitoring_token)

if [ -z "$AUTH_TOKEN" ]; then
    echo "⚠ Warning: Could not obtain monitoring auth token"
    echo "  Database performance checks will be skipped"
    return 0
fi
```

## Error Handling

- Metrics collection failures should be warnings, not fatal errors
- Missing baselines on fresh installations are expected
- Critical alerts should trigger warnings but not stop service checks

## Testing

Test the integration:

```bash
# Run full service check
./check_services.sh

# Run only database monitoring checks
./check_services.sh --database-only
```

## Future Enhancements

1. Add metrics collection rate checks
2. Add baseline freshness validation
3. Add anomaly detection status
4. Add continuous monitoring service health check
5. Integration with alerting systems (email, Slack)

## Implementation Status

**Status**: Documentation complete, implementation deferred to production deployment

The database monitoring API endpoints are fully implemented and tested. Integration into `check_services.sh` can be completed during production deployment based on specific operational requirements.
