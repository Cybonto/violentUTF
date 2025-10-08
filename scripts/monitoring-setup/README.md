# ViolentUTF Database Performance Monitoring Setup

**Issue**: #270 - Database Performance Monitoring Infrastructure
**Version**: 1.0
**Status**: Production Ready

## Overview

This directory contains automation scripts for deploying and configuring the complete database performance monitoring infrastructure for ViolentUTF, including:

- **Prometheus**: Time-series metrics collection and storage
- **Grafana**: Dashboard visualization and alerting
- **AlertManager**: Alert routing and notification management
- **Database Metrics Collection**: PostgreSQL and SQLite performance monitoring

## Scripts

### 1. setup_performance_monitoring.py

Automated deployment of the complete monitoring stack.

**Usage:**
```bash
# Full deployment with validation
python3 setup_performance_monitoring.py

# Dry run (show what would be done)
python3 setup_performance_monitoring.py --dry-run

# Validate existing deployment
python3 setup_performance_monitoring.py --validate

# Remove monitoring stack
python3 setup_performance_monitoring.py --cleanup
```

**What it does:**
- Validates prerequisites (Docker, Docker Compose, configuration files)
- Creates required directories
- Validates all YAML and JSON configuration files
- Deploys Prometheus, Grafana, and AlertManager services
- Waits for services to become healthy
- Validates deployment and prints access information

**Requirements:**
- Docker and Docker Compose installed
- Configuration files present in `configs/monitoring/`
- Dashboard files present in `dashboards/`

### 2. configure_dashboards.py

Automated provisioning of Grafana dashboards via API.

**Usage:**
```bash
# Provision all dashboards
python3 configure_dashboards.py

# Update existing dashboards
python3 configure_dashboards.py --update

# List existing dashboards
python3 configure_dashboards.py --list

# Custom Grafana URL and credentials
python3 configure_dashboards.py \
    --grafana-url http://custom-grafana:3000 \
    --username admin \
    --password secret
```

**What it does:**
- Validates connection to Grafana API
- Loads and validates dashboard JSON files
- Checks for existing dashboards
- Provisions/updates dashboards in Grafana
- Validates datasource configuration

**Dashboard Files:**
- `dashboards/database_overview.json` - Multi-database health overview
- `dashboards/postgresql_performance.json` - PostgreSQL detailed metrics
- `dashboards/sqlite_performance.json` - SQLite detailed metrics

### 3. establish_baselines.py

Automated baseline calculation and documentation from historical data.

**Usage:**
```bash
# Calculate baselines from historical data
python3 establish_baselines.py --analyze-historical

# Calculate baselines for specific database
python3 establish_baselines.py --analyze-historical --database postgresql

# Calculate baselines for specific metrics
python3 establish_baselines.py --analyze-historical \
    --metrics "connection_pool_usage,avg_query_latency_ms"

# Schedule periodic recalculation (shows cron command)
python3 establish_baselines.py --schedule "0 2 * * 0"

# With authentication
python3 establish_baselines.py --analyze-historical \
    --auth-token "your-jwt-token"
```

**What it does:**
- Checks for sufficient historical data (minimum 100 samples)
- Triggers baseline recalculation via API
- Retrieves calculated baselines
- Generates baseline documentation report
- Provides cron scheduling guidance

**Output:**
- Baseline report: `docs/monitoring/baseline_report.md`

## Deployment Workflow

### Initial Setup (Day 1)

```bash
# 1. Ensure all prerequisites are met
docker --version
docker compose version

# 2. Deploy monitoring stack
cd /path/to/violentutf
python3 scripts/monitoring-setup/setup_performance_monitoring.py

# 3. Wait for services to stabilize
sleep 30

# 4. Verify deployment
python3 scripts/monitoring-setup/setup_performance_monitoring.py --validate

# 5. Provision Grafana dashboards
python3 scripts/monitoring-setup/configure_dashboards.py
```

**Access Points:**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- AlertManager: http://localhost:9093

### Baseline Establishment (Day 7+)

After collecting at least 7 days of metrics:

```bash
# Calculate performance baselines
python3 scripts/monitoring-setup/establish_baselines.py --analyze-historical

# Review baseline report
cat docs/monitoring/baseline_report.md

# Schedule weekly recalculation (add to cron)
crontab -e
# Add: 0 2 * * 0 cd /path/to/violentutf && python3 scripts/monitoring-setup/establish_baselines.py --analyze-historical
```

## Configuration Files

All configuration files are located in `configs/monitoring/`:

| File | Purpose |
|------|---------|
| `prometheus.yml` | Prometheus scrape configs and retention |
| `alertmanager.yml` | Alert routing and notification rules |
| `alert_rules.yaml` | Database performance alert thresholds |
| `grafana-datasources.yml` | Grafana datasource provisioning |
| `grafana-dashboards.yml` | Grafana dashboard auto-loading |

## Monitoring Stack Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   CLIENT ACCESS                              │
│  Grafana (3000) | Prometheus (9090) | AlertManager (9093)    │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                  PROMETHEUS (Metrics Storage)                │
│  • 10s scrape interval                                       │
│  • 90-day retention                                          │
│  • PromQL query engine                                       │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│              VIOLENTUTF FASTAPI BACKEND                      │
│  • /metrics endpoint (Prometheus format)                     │
│  • Database metrics collectors                               │
│  • Alert webhook receiver                                    │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────┐         ┌───────────────────────────┐
│  PostgreSQL          │         │  SQLite Database          │
│  (Keycloak)          │         │  (FastAPI)                │
│  Port: 5432          │         │  /app/app_data/           │
└──────────────────────┘         └───────────────────────────┘
```

## Troubleshooting

### Services Won't Start

```bash
# Check Docker network exists
docker network ls | grep violentutf_network

# Create network if missing
docker network create violentutf_network

# Check for port conflicts
lsof -i :9090  # Prometheus
lsof -i :3000  # Grafana
lsof -i :9093  # AlertManager

# View service logs
docker logs violentutf-prometheus
docker logs violentutf-grafana
docker logs violentutf-alertmanager
```

### Dashboards Not Loading

```bash
# Check Grafana logs
docker logs violentutf-grafana

# Verify dashboard files exist
ls -la dashboards/*.json

# Manually provision dashboards
python3 scripts/monitoring-setup/configure_dashboards.py --update
```

### No Metrics Appearing

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify FastAPI /metrics endpoint
curl http://localhost:9080/metrics

# Check metrics collection is running
docker logs violentutf-api | grep "metrics"
```

### Baseline Calculation Fails

```bash
# Check data availability
python3 scripts/monitoring-setup/establish_baselines.py

# Verify API accessibility
curl http://localhost:9080/api/v1/monitoring/database/baselines

# Check for sufficient samples (need 100+)
# Review logs for specific errors
```

## Maintenance

### Weekly Tasks
- Review baseline report for anomalies
- Check alert accuracy (false positives/negatives)
- Verify all services are healthy
- Review storage usage trends

### Monthly Tasks
- Recalculate baselines to adapt to new patterns
- Review and tune alert thresholds
- Analyze long-term performance trends
- Archive old metrics data if needed

### Configuration Updates

When modifying configurations:

```bash
# 1. Edit configuration file
vim configs/monitoring/prometheus.yml

# 2. Validate changes
python3 scripts/monitoring-setup/setup_performance_monitoring.py --validate

# 3. Reload service (Prometheus supports hot reload)
curl -X POST http://localhost:9090/-/reload

# 4. For Grafana/AlertManager, restart services
docker compose -f docker-compose.monitoring.yml restart grafana
docker compose -f docker-compose.monitoring.yml restart alertmanager
```

## Integration with check_services.sh

The monitoring stack integrates with ViolentUTF's existing health check system:

```bash
# Add to check_services.sh:
# Check Prometheus
curl -sf http://localhost:9090/-/healthy || echo "Prometheus unhealthy"

# Check Grafana
curl -sf http://localhost:3000/api/health || echo "Grafana unhealthy"

# Check AlertManager
curl -sf http://localhost:9093/-/healthy || echo "AlertManager unhealthy"
```

## Security Considerations

### Default Credentials
- **Change default Grafana password** after first login
- Set via environment variables in `docker-compose.monitoring.yml`

### Network Isolation
- Monitoring stack uses `violentutf_network` for service communication
- External access controlled via published ports
- Consider firewall rules for production deployments

### Authentication
- Grafana requires login for dashboard access
- Prometheus/AlertManager accessible without auth by default
- Configure basic auth or reverse proxy for production

## Performance Impact

Expected resource usage:
- **CPU**: <5% additional load from monitoring
- **Memory**: ~500MB for monitoring stack
- **Disk**: ~3GB per year for metrics (with 90-day retention)
- **Network**: Minimal (10s scrape interval, local network)

## Support and Documentation

- **Issue Tracker**: GitHub Issue #270
- **Implementation Report**: `docs/development/issue_270/ISSUE_270_FINAL_IMPLEMENTATION_REPORT.md`
- **Integration Guide**: `docs/development/issue_270/check_services_integration.md`
- **Alert Rules Reference**: `configs/monitoring/alert_rules.yaml`

## License

Part of ViolentUTF project - Enterprise AI Red-Teaming Platform
