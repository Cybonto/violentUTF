# Dataset Logging Analysis Guide

## Overview

ViolentUTF includes a comprehensive dataset integration logging system that tracks all dataset operations, conversions, and activities for audit trails, debugging capabilities, and operational monitoring. This guide covers how to use the logging analysis tools effectively.

## Table of Contents

1. [Logging Architecture](#logging-architecture)
2. [Log Structure](#log-structure)
3. [Analysis Tools](#analysis-tools)
4. [Common Analysis Scenarios](#common-analysis-scenarios)
5. [Performance Monitoring](#performance-monitoring)
6. [Security and Compliance](#security-and-compliance)
7. [Troubleshooting](#troubleshooting)
8. [Configuration](#configuration)

## Logging Architecture

### Components

The dataset logging system consists of several key components:

- **DatasetLogger**: Main logging component with structured logging
- **DatasetAuditLogger**: Specialized logger for audit trail requirements
- **EnhancedLogAnalyzer**: Advanced log analysis and query capabilities
- **CentralizedHandler**: Optional centralized logging support
- **Performance Monitoring**: Metrics collection with minimal overhead

### Log Levels

```python
DEBUG    # Detailed information for diagnosing problems
INFO     # General information about dataset operations
WARNING  # Something unexpected happened but operation continued
ERROR    # Operation failed due to an error
CRITICAL # Serious error that might abort the program
```

### Environment-Specific Configuration

- **Development**: DEBUG level, 7-day retention, synchronous logging
- **Staging**: INFO level, 14-day retention, asynchronous logging
- **Production**: INFO level, 30-day retention, asynchronous logging

## Log Structure

### Standard Log Entry

```json
{
    "timestamp": "2024-01-15T10:30:00Z",
    "level": "INFO",
    "logger": "violentutf.datasets",
    "message": "Dataset creation completed successfully",
    "module": "datasets",
    "function": "create_dataset",
    "line": 425,
    "operation": "dataset_import",
    "dataset_id": "dataset_123",
    "dataset_type": "harmbench",
    "user_id": "user_456",
    "session_id": "session_789",
    "correlation_id": "corr_abc123",
    "environment": "production"
}
```

### Operation-Specific Fields

#### Dataset Operations
```json
{
    "operation": "dataset_conversion",
    "dataset_type": "ollegen1_cognitive",
    "conversion_strategy": "cognitive_assessment_to_qa",
    "input_format": "csv",
    "output_format": "QuestionAnsweringDataset",
    "input_size": 169999,
    "output_size": 679996,
    "processing_time_seconds": 45.0
}
```

#### Performance Metrics
```json
{
    "performance_category": "dataset_metrics",
    "metric_name": "dataset_creation_time",
    "metric_value": 2.5,
    "metric_unit": "seconds",
    "threshold": 5.0,
    "memory_usage_mb": 256.8
}
```

#### Security Events
```json
{
    "security_category": "dataset_operation",
    "event_type": "unauthorized_access_attempt",
    "severity": "high",
    "details": {
        "attempted_dataset": "sensitive_data",
        "source_ip": "192.168.1.100"
    }
}
```

#### Audit Trail Events
```json
{
    "event_type": "user_action",
    "action": "dataset_deletion",
    "resource": "dataset:critical_dataset",
    "user_id": "admin_user",
    "ip_address": "10.0.0.1",
    "user_agent": "Mozilla/5.0...",
    "result": "success"
}
```

## Analysis Tools

### EnhancedLogAnalyzer

The main tool for analyzing dataset logs.

```python
from app.core.dataset_logging import get_log_analyzer

analyzer = get_log_analyzer()

# Read logs with filters
logs = analyzer.read_logs(
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2),
    operation="dataset_conversion",
    user_id="specific_user"
)

# Analyze performance
performance = analyzer.analyze_performance(logs)

# Find errors
errors = analyzer.find_errors(logs)

# Get operation trace
trace = analyzer.get_operation_trace("correlation_123")
```

### Performance Analysis

```python
# Analyze performance trends for specific metrics
trends = analyzer.analyze_performance_trends(
    metric_name="dataset_creation_time",
    hours=24
)

print(f"Average: {trends['avg_value']} seconds")
print(f"Peak: {trends['max_value']} seconds")
print(f"Threshold violations: {trends['threshold_violations']}")
```

### Security Analysis

```python
# Find security events
security_events = analyzer.find_security_events(
    severity="high",
    start_time=datetime.now() - timedelta(hours=24)
)

# Find compliance violations
violations = analyzer.find_compliance_violations(
    start_time=datetime.now() - timedelta(days=7)
)
```

### Compliance Reporting

```python
# Generate comprehensive compliance report
report = analyzer.generate_compliance_report(
    start_time=datetime.now() - timedelta(days=30)
)

print(f"Compliance rate: {report['compliance_rate']:.2f}%")
print(f"Active users: {len(report['active_users'])}")
print(f"Datasets accessed: {len(report['accessed_datasets'])}")
```

## Common Analysis Scenarios

### 1. Investigating Failed Dataset Operations

```python
# Find all failed operations in the last 24 hours
start_time = datetime.now() - timedelta(hours=24)
logs = analyzer.read_logs(start_time=start_time)
errors = analyzer.find_errors(logs)

for error in errors:
    print(f"Error at {error['timestamp']}")
    print(f"Operation: {error.get('operation', 'Unknown')}")
    print(f"Dataset: {error.get('dataset_id', 'Unknown')}")
    print(f"User: {error.get('user_id', 'Unknown')}")
    print(f"Message: {error['message']}")
    print("-" * 50)
```

### 2. Performance Bottleneck Analysis

```python
# Find slow operations
slow_operations = []
for log in logs:
    if (log.get('operation_time_seconds', 0) > 30 and 
        'operation_time_seconds' in log):
        slow_operations.append(log)

# Analyze by operation type
from collections import defaultdict
by_operation = defaultdict(list)
for op in slow_operations:
    by_operation[op.get('operation', 'unknown')].append(
        op['operation_time_seconds']
    )

for operation, times in by_operation.items():
    avg_time = sum(times) / len(times)
    print(f"{operation}: {avg_time:.2f}s average ({len(times)} samples)")
```

### 3. User Activity Analysis

```python
# Analyze user activity patterns
user_activity = defaultdict(lambda: {
    'operations': 0,
    'datasets_accessed': set(),
    'errors': 0
})

for log in logs:
    user_id = log.get('user_id')
    if user_id:
        user_activity[user_id]['operations'] += 1
        if dataset_id := log.get('dataset_id'):
            user_activity[user_id]['datasets_accessed'].add(dataset_id)
        if log.get('level') == 'ERROR':
            user_activity[user_id]['errors'] += 1

# Most active users
sorted_users = sorted(
    user_activity.items(),
    key=lambda x: x[1]['operations'],
    reverse=True
)
```

### 4. Dataset Conversion Tracking

```python
# Track specific dataset through conversion pipeline
correlation_id = "conv-12345"
trace = analyzer.get_operation_trace(correlation_id)

print("Conversion Timeline:")
for entry in trace:
    timestamp = entry['timestamp']
    message = entry['message']
    operation = entry.get('operation', 'Unknown')
    print(f"{timestamp} [{operation}] {message}")
```

### 5. Security Incident Investigation

```python
# Investigate security incidents
security_events = analyzer.find_security_events(
    severity="high",
    start_time=datetime.now() - timedelta(hours=1)
)

for event in security_events:
    print(f"Security Event: {event.get('event_type')}")
    print(f"Time: {event['timestamp']}")
    print(f"User: {event.get('user_id', 'Unknown')}")
    print(f"Details: {event.get('details', {})}")
    
    # Get related events by correlation ID
    if corr_id := event.get('correlation_id'):
        related = analyzer.get_operation_trace(corr_id)
        print(f"Related events: {len(related)}")
```

## Performance Monitoring

### Key Metrics to Monitor

1. **Dataset Creation Time**
   - Threshold: 30 seconds
   - Alerts: >60 seconds

2. **Memory Usage**
   - Threshold: 512 MB
   - Alerts: >1 GB

3. **Conversion Rate**
   - Target: >95% success rate
   - Alerts: <90% success rate

4. **API Response Time**
   - Threshold: 5 seconds
   - Alerts: >10 seconds

### Setting Up Monitoring

```python
# Monitor performance with custom thresholds
def monitor_dataset_operations():
    analyzer = get_log_analyzer()
    last_hour = datetime.now() - timedelta(hours=1)
    
    # Check creation times
    creation_times = analyzer.analyze_performance_trends(
        "dataset_creation_time", 
        hours=1
    )
    
    if creation_times.get('avg_value', 0) > 30:
        alert(f"Average creation time exceeded: {creation_times['avg_value']}s")
    
    # Check error rates
    logs = analyzer.read_logs(start_time=last_hour)
    errors = analyzer.find_errors(logs)
    error_rate = len(errors) / len(logs) if logs else 0
    
    if error_rate > 0.1:  # 10% error rate threshold
        alert(f"High error rate detected: {error_rate:.2%}")
```

### Performance Dashboard Queries

```python
# Generate performance dashboard data
def get_dashboard_metrics(hours=24):
    analyzer = get_log_analyzer()
    start_time = datetime.now() - timedelta(hours=hours)
    logs = analyzer.read_logs(start_time=start_time)
    
    metrics = analyzer.analyze_performance(logs)
    
    return {
        'total_operations': metrics['total_operations'],
        'success_rate': (metrics['successful_operations'] / 
                        metrics['total_operations'] * 100 
                        if metrics['total_operations'] > 0 else 0),
        'avg_processing_time': metrics['avg_processing_time'],
        'memory_peak': metrics['memory_usage']['peak'],
        'errors_last_hour': len(analyzer.find_errors(logs))
    }
```

## Security and Compliance

### Audit Trail Analysis

```python
# Generate audit report for compliance
def generate_audit_report(start_date, end_date):
    analyzer = get_log_analyzer()
    
    # Get all audit events
    logs = analyzer.read_logs(
        start_time=start_date,
        end_time=end_date
    )
    
    # Filter audit events
    audit_events = [
        log for log in logs 
        if log.get('event_type') in ['user_action', 'data_access']
    ]
    
    # Group by user
    user_actions = defaultdict(list)
    for event in audit_events:
        user_id = event.get('user_id')
        if user_id:
            user_actions[user_id].append(event)
    
    return {
        'period': f"{start_date} to {end_date}",
        'total_events': len(audit_events),
        'unique_users': len(user_actions),
        'user_actions': dict(user_actions)
    }
```

### Compliance Checks

```python
# Check for compliance violations
def check_compliance():
    analyzer = get_log_analyzer()
    violations = analyzer.find_compliance_violations()
    
    critical_violations = [
        v for v in violations 
        if v.get('severity') in ['high', 'critical']
    ]
    
    if critical_violations:
        return {
            'status': 'CRITICAL',
            'violations': len(critical_violations),
            'details': critical_violations
        }
    elif violations:
        return {
            'status': 'WARNING',
            'violations': len(violations),
            'details': violations
        }
    else:
        return {'status': 'COMPLIANT'}
```

## Troubleshooting

### Common Issues and Solutions

#### 1. High Memory Usage

**Symptoms:**
- Memory usage metrics showing >90% utilization
- Performance degradation
- Out of memory errors

**Investigation:**
```python
# Analyze memory usage patterns
memory_logs = [
    log for log in logs 
    if 'memory_mb' in log and log['memory_mb'] > 500
]

# Group by operation
memory_by_operation = defaultdict(list)
for log in memory_logs:
    operation = log.get('operation', 'unknown')
    memory_by_operation[operation].append(log['memory_mb'])
```

**Solutions:**
- Reduce chunk size in dataset configuration
- Enable adaptive chunk sizing
- Increase memory limits
- Review large dataset processing strategies

#### 2. Slow Dataset Conversions

**Symptoms:**
- Conversion times >30 seconds
- Timeout errors
- User complaints about slow processing

**Investigation:**
```python
# Find conversion bottlenecks
slow_conversions = [
    log for log in logs 
    if (log.get('operation') == 'dataset_conversion' and 
        log.get('processing_time_seconds', 0) > 30)
]

# Analyze by dataset type
conversion_times = defaultdict(list)
for log in slow_conversions:
    dataset_type = log.get('dataset_type', 'unknown')
    conversion_times[dataset_type].append(log['processing_time_seconds'])
```

**Solutions:**
- Optimize conversion strategies
- Enable parallel processing
- Implement caching for frequent conversions
- Use streaming for large datasets

#### 3. Authentication Failures

**Symptoms:**
- High number of 401/403 errors
- Security alerts
- Users unable to access datasets

**Investigation:**
```python
# Find authentication issues
auth_failures = [
    log for log in logs 
    if (log.get('level') == 'ERROR' and 
        any(keyword in log.get('message', '').lower() 
            for keyword in ['auth', 'unauthorized', 'forbidden']))
]

# Group by user
failed_users = defaultdict(int)
for log in auth_failures:
    user_id = log.get('user_id', 'unknown')
    failed_users[user_id] += 1
```

**Solutions:**
- Check token expiration
- Verify user permissions
- Review JWT configuration
- Check APISIX gateway rules

### Performance Debugging

#### Profiling Dataset Operations

```python
from app.core.dataset_logging import monitor_performance

@monitor_performance(threshold_seconds=10.0)
def analyze_slow_operation(dataset_id):
    """Analyze a specific slow operation"""
    analyzer = get_log_analyzer()
    
    # Get all logs for this dataset
    dataset_logs = analyzer.read_logs(dataset_id=dataset_id)
    
    # Analyze performance
    performance = analyzer.analyze_performance(dataset_logs)
    
    return {
        'dataset_id': dataset_id,
        'total_operations': performance['total_operations'],
        'avg_time': performance['avg_processing_time'],
        'success_rate': (performance['successful_operations'] / 
                        performance['total_operations']),
        'bottlenecks': identify_bottlenecks(dataset_logs)
    }

def identify_bottlenecks(logs):
    """Identify performance bottlenecks"""
    bottlenecks = []
    
    # Check for memory issues
    high_memory = [l for l in logs if l.get('memory_mb', 0) > 800]
    if high_memory:
        bottlenecks.append({
            'type': 'memory',
            'severity': 'high' if len(high_memory) > 10 else 'medium',
            'count': len(high_memory)
        })
    
    # Check for slow operations
    slow_ops = [l for l in logs if l.get('operation_time_seconds', 0) > 30]
    if slow_ops:
        bottlenecks.append({
            'type': 'slow_operations',
            'severity': 'high' if len(slow_ops) > 5 else 'medium',
            'count': len(slow_ops)
        })
    
    return bottlenecks
```

## Configuration

### Environment Variables

```bash
# Basic logging configuration
DATASET_LOG_LEVEL=INFO
DATASET_CONSOLE_LOG_LEVEL=INFO
DATASET_FILE_LOG_LEVEL=DEBUG
DATASET_ENABLE_FILE_LOGGING=true
DATASET_LOG_DIR=logs/datasets

# Rotation and retention
DATASET_LOG_ROTATION_INTERVAL=midnight
DATASET_LOG_RETENTION_DAYS=30
DATASET_MAX_LOG_FILE_SIZE_MB=100
DATASET_LOG_BACKUP_COUNT=10
DATASET_LOG_COMPRESSION=true

# Performance optimization
DATASET_ASYNC_LOGGING=true
DATASET_LOG_BUFFER_SIZE=1024
DATASET_PERFORMANCE_SAMPLING_RATE=0.1
DATASET_MAX_LOG_MESSAGE_SIZE=10000

# Features
DATASET_ENABLE_STRUCTURED_LOGGING=true
DATASET_ENABLE_PERFORMANCE_TRACKING=true
DATASET_ENABLE_AUDIT_TRAILS=true
DATASET_ENABLE_CENTRALIZED_LOGGING=false

# Security
DATASET_LOG_SENSITIVE_DATA=false
DATASET_AUDIT_LOG_RETENTION_DAYS=90
```

### Centralized Logging Setup

```bash
# Enable centralized logging
DATASET_ENABLE_CENTRALIZED_LOGGING=true
DATASET_CENTRALIZED_ENDPOINT=https://logs.example.com/api/ingest
DATASET_CENTRALIZED_API_KEY=your-api-key
```

### Production Recommendations

```bash
# Production environment settings
ENVIRONMENT=production
DATASET_LOG_LEVEL=INFO
DATASET_CONSOLE_LOG_LEVEL=WARNING
DATASET_ASYNC_LOGGING=true
DATASET_LOG_RETENTION_DAYS=90
DATASET_PERFORMANCE_SAMPLING_RATE=0.05
DATASET_ENABLE_CENTRALIZED_LOGGING=true
```

## Advanced Analysis Examples

### Custom Metrics Collection

```python
def collect_custom_metrics():
    """Collect custom business metrics from logs"""
    analyzer = get_log_analyzer()
    logs = analyzer.read_logs(
        start_time=datetime.now() - timedelta(days=1)
    )
    
    metrics = {
        'datasets_created_24h': 0,
        'unique_users_24h': set(),
        'conversion_success_rate': 0,
        'avg_dataset_size': 0,
        'top_dataset_types': defaultdict(int)
    }
    
    dataset_sizes = []
    conversions = {'success': 0, 'total': 0}
    
    for log in logs:
        # Count dataset creations
        if log.get('operation') == 'dataset_import':
            metrics['datasets_created_24h'] += 1
            if size := log.get('prompt_count'):
                dataset_sizes.append(size)
        
        # Track unique users
        if user_id := log.get('user_id'):
            metrics['unique_users_24h'].add(user_id)
        
        # Track conversions
        if log.get('operation') == 'dataset_conversion':
            conversions['total'] += 1
            if log.get('level') != 'ERROR':
                conversions['success'] += 1
        
        # Count dataset types
        if dataset_type := log.get('dataset_type'):
            metrics['top_dataset_types'][dataset_type] += 1
    
    # Calculate derived metrics
    metrics['unique_users_24h'] = len(metrics['unique_users_24h'])
    if conversions['total'] > 0:
        metrics['conversion_success_rate'] = (
            conversions['success'] / conversions['total'] * 100
        )
    if dataset_sizes:
        metrics['avg_dataset_size'] = sum(dataset_sizes) / len(dataset_sizes)
    
    return metrics
```

### Anomaly Detection

```python
def detect_anomalies():
    """Detect anomalies in dataset operations"""
    analyzer = get_log_analyzer()
    
    # Get baseline metrics (last 7 days)
    baseline_start = datetime.now() - timedelta(days=7)
    baseline_end = datetime.now() - timedelta(days=1)
    baseline_logs = analyzer.read_logs(
        start_time=baseline_start,
        end_time=baseline_end
    )
    
    # Get current metrics (last 24 hours)
    current_start = datetime.now() - timedelta(days=1)
    current_logs = analyzer.read_logs(start_time=current_start)
    
    # Calculate baseline averages
    baseline_metrics = analyzer.analyze_performance(baseline_logs)
    current_metrics = analyzer.analyze_performance(current_logs)
    
    anomalies = []
    
    # Check for significant deviations
    if current_metrics['avg_processing_time'] > baseline_metrics['avg_processing_time'] * 2:
        anomalies.append({
            'type': 'performance_degradation',
            'severity': 'high',
            'current': current_metrics['avg_processing_time'],
            'baseline': baseline_metrics['avg_processing_time']
        })
    
    if current_metrics['failed_operations'] > baseline_metrics['failed_operations'] * 3:
        anomalies.append({
            'type': 'error_spike',
            'severity': 'high',
            'current': current_metrics['failed_operations'],
            'baseline': baseline_metrics['failed_operations']
        })
    
    return anomalies
```

This comprehensive guide provides the foundation for effective analysis of dataset logging in ViolentUTF. Regular monitoring and analysis of these logs will help maintain optimal performance, security, and compliance of dataset operations.