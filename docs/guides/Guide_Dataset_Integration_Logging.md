# Dataset Integration Logging System Guide

## Overview

The Dataset Integration Logging System provides comprehensive logging capabilities for all dataset operations in ViolentUTF. It tracks conversions, imports, exports, and other dataset-related activities with structured logging, performance metrics, and advanced analysis capabilities.

## Features

### 1. Structured Logging
- JSON-formatted logs for machine readability
- Hierarchical log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Correlation IDs for tracking related operations
- User and session context tracking

### 2. Performance Tracking
- Operation timing and throughput metrics
- Memory usage monitoring
- Chunk processing statistics
- Retry attempt tracking

### 3. Log Management
- Automatic log rotation (size-based or time-based)
- Configurable retention policies
- Log compression for archived files
- Environment-specific configurations

### 4. Analysis Tools
- Log querying and filtering
- Performance analysis
- Error tracking and reporting
- Operation trace reconstruction

## Configuration

### Environment Variables

Configure the logging system using environment variables:

```bash
# Environment
export ENVIRONMENT=development  # development, staging, production

# Log Levels
export DATASET_LOG_LEVEL=INFO
export DATASET_CONSOLE_LOG_LEVEL=INFO
export DATASET_FILE_LOG_LEVEL=DEBUG

# File Logging
export DATASET_ENABLE_FILE_LOGGING=true
export DATASET_LOG_DIR=logs/datasets
export DATASET_LOG_FILE_PREFIX=dataset_ops
export DATASET_MAX_LOG_FILE_SIZE_MB=100
export DATASET_LOG_BACKUP_COUNT=10
export DATASET_LOG_COMPRESSION=true

# Rotation and Retention
export DATASET_LOG_ROTATION_INTERVAL=midnight
export DATASET_LOG_RETENTION_DAYS=30

# Performance
export DATASET_ASYNC_LOGGING=true
export DATASET_LOG_BUFFER_SIZE=1024

# Features
export DATASET_ENABLE_METRICS=true
export DATASET_ENABLE_CORRELATION_ID=true
export DATASET_ENABLE_STRUCTURED_LOGGING=true
export DATASET_ENABLE_PERFORMANCE_TRACKING=true
```

### Environment-Specific Defaults

The system automatically configures appropriate defaults based on the environment:

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| Log Level | DEBUG | INFO | INFO |
| Console Level | DEBUG | INFO | WARNING |
| File Level | DEBUG | DEBUG | INFO |
| Retention Days | 7 | 14 | 30 |
| Async Logging | False | True | True |

## Usage Examples

### Basic Logging

```python
from app.core.dataset_logging import dataset_logger

# Simple logging
dataset_logger.info("Starting dataset import", dataset_id="ds_001")
dataset_logger.error("Import failed", error="File not found")
```

### Operation Context

Use the operation context manager for automatic tracking:

```python
from app.core.dataset_logging import dataset_logger

with dataset_logger.operation_context(
    operation="dataset_conversion",
    dataset_id="ds_001",
    dataset_type="harmbench",
    user_id="user123"
) as logger:
    # Your operation code here
    logger.log_chunk_progress(0, 10, 1000, success=True)
    logger.log_memory_usage(150.5)
    # Operation timing is automatically tracked
```

### Correlation Tracking

Track related operations across services:

```python
# Set correlation ID for related operations
correlation_id = dataset_logger.set_correlation_id()

# Use the same correlation ID across multiple operations
with dataset_logger.operation_context(
    "import",
    correlation_id=correlation_id
):
    # Import operation
    pass

with dataset_logger.operation_context(
    "conversion",
    correlation_id=correlation_id
):
    # Conversion operation
    pass
```

### User Context

Set user context for all subsequent operations:

```python
dataset_logger.set_user_context(
    user_id="user123",
    session_id="session456"
)

# All subsequent logs will include user context
dataset_logger.info("User action logged")
```

### Performance Metrics

Track detailed performance metrics:

```python
# Reset metrics for new operation
dataset_logger.reset_metrics()

# Log various metrics
dataset_logger.log_chunk_progress(
    chunk_index=0,
    total_chunks=10,
    chunk_size=1000,
    success=True,
    processing_time=1.5
)

dataset_logger.log_memory_usage(256.7, operation="processing")

dataset_logger.log_retry_attempt(
    attempt=1,
    max_attempts=3,
    error=ConnectionError("Timeout")
)

# Finalize and get metrics
metrics = dataset_logger.finalize_metrics()
rates = metrics.calculate_rates()
print(f"Success rate: {rates['success_rate']:.2%}")
```

## Log Analysis

### Reading Logs

```python
from app.core.dataset_logging import log_analyzer
from datetime import datetime, timedelta

# Read all logs
logs = log_analyzer.read_logs()

# Filter logs
logs = log_analyzer.read_logs(
    start_time=datetime.now() - timedelta(hours=1),
    operation="dataset_import",
    user_id="user123"
)
```

### Performance Analysis

```python
# Analyze performance metrics
performance = log_analyzer.analyze_performance(logs)
print(f"Average processing time: {performance['avg_processing_time']:.2f}s")
print(f"Peak memory usage: {performance['memory_usage']['peak']:.2f} MB")
```

### Error Tracking

```python
# Find all errors
errors = log_analyzer.find_errors()
for error in errors:
    print(f"Error: {error['message']} at {error['timestamp']}")
```

### Operation Tracing

```python
# Get complete trace of an operation
trace = log_analyzer.get_operation_trace("correlation-id-123")
for entry in trace:
    print(f"{entry['timestamp']}: {entry['message']}")
```

### Summary Reports

```python
# Generate comprehensive report
report = log_analyzer.generate_summary_report(
    start_time=datetime.now() - timedelta(days=1)
)

print(f"Total operations: {report['performance']['total_operations']}")
print(f"Error rate: {report['errors']['error_rate']:.2%}")
print(f"Operations by type: {report['operations']}")
```

## Log Format Examples

### JSON Log Entry (Structured Logging)

```json
{
    "timestamp": "2025-08-18T10:30:00Z",
    "level": "INFO",
    "logger": "violentutf.datasets",
    "message": "Dataset conversion completed",
    "operation": "dataset_conversion",
    "dataset_id": "ds_001",
    "dataset_type": "harmbench",
    "user_id": "user123",
    "correlation_id": "conv-12345",
    "environment": "production",
    "operation_elapsed_seconds": 45.2,
    "metrics": {
        "total_prompts": 1000,
        "successful_prompts": 998,
        "processing_time_seconds": 45.2
    }
}
```

### Console Output (Structured Formatter)

```
2025-08-18 10:30:00 - violentutf.datasets - INFO - Dataset conversion completed [correlation_id=conv-12345, operation=dataset_conversion, dataset_id=ds_001, user_id=user123]
```

## Performance Considerations

### Overhead Minimization

The logging system is optimized for minimal overhead:
- Early exit for disabled log levels
- Async logging in production environments
- Buffered I/O for file operations
- Performance overhead < 5% when properly configured

### Best Practices

1. **Use appropriate log levels**:
   - DEBUG: Detailed diagnostic information
   - INFO: General informational messages
   - WARNING: Warning messages for potential issues
   - ERROR: Error events that don't stop the application
   - CRITICAL: Critical problems that may cause application failure

2. **Structure your logs**:
   - Always include relevant context (dataset_id, user_id, etc.)
   - Use correlation IDs for related operations
   - Include measurable metrics where applicable

3. **Manage log volume**:
   - Configure appropriate retention policies
   - Use log rotation to prevent disk space issues
   - Enable compression for archived logs

4. **Monitor performance**:
   - Regularly analyze logs for performance trends
   - Track error rates and patterns
   - Use metrics to identify bottlenecks

## Troubleshooting

### Common Issues

1. **Logs not appearing**:
   - Check log level configuration
   - Verify file permissions for log directory
   - Ensure logging is enabled

2. **High disk usage**:
   - Adjust retention policies
   - Enable log compression
   - Reduce log level in production

3. **Performance impact**:
   - Disable debug logging in production
   - Use async logging for high-throughput scenarios
   - Increase buffer size for better batching

### Debug Commands

```bash
# Check current log files
ls -la logs/datasets/

# View recent logs
tail -f logs/datasets/dataset_ops_$(date +%Y%m%d).log

# Check log file sizes
du -sh logs/datasets/*

# Analyze compressed logs
zcat logs/datasets/*.gz | jq '.'
```

## Integration with ViolentUTF

The logging system integrates seamlessly with existing ViolentUTF infrastructure:

- **PyRIT Integration**: Logs all PyRIT memory operations
- **Dataset Conversions**: Tracks all conversion strategies and outcomes
- **API Operations**: Correlates with API request logging
- **Authentication**: Includes user context from Keycloak tokens
- **Monitoring**: Compatible with existing monitoring solutions

## API Reference

### Core Classes

- `DatasetLogger`: Main logging interface
- `LogConfig`: Configuration management
- `ImportMetrics`: Metrics collection
- `LogAnalyzer`: Log analysis utilities

### Key Methods

- `operation_context()`: Context manager for operations
- `set_correlation_id()`: Set/generate correlation ID
- `set_user_context()`: Set user session info
- `log_chunk_progress()`: Log streaming progress
- `log_memory_usage()`: Track memory consumption
- `log_retry_attempt()`: Record retry attempts
- `analyze_performance()`: Analyze performance metrics
- `find_errors()`: Query error logs
- `generate_summary_report()`: Create comprehensive reports

## Security Considerations

- Logs may contain sensitive information - ensure proper access controls
- Use log sanitization for PII data
- Configure appropriate retention policies for compliance
- Encrypt archived logs if required
- Monitor for suspicious patterns in logs

## Future Enhancements

Planned improvements include:
- Real-time log streaming
- Advanced anomaly detection
- Machine learning-based log analysis
- Integration with external logging services
- Custom dashboards and visualizations
