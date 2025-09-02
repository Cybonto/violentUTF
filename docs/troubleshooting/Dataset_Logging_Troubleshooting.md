# Dataset Logging Troubleshooting Guide

## Overview

This guide provides solutions for common issues encountered with the ViolentUTF dataset logging system, including performance problems, configuration issues, and debugging techniques.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Common Issues](#common-issues)
3. [Performance Problems](#performance-problems)
4. [Configuration Issues](#configuration-issues)
5. [Log Analysis Problems](#log-analysis-problems)
6. [Emergency Procedures](#emergency-procedures)
7. [Debug Commands](#debug-commands)

## Quick Diagnostics

### Health Check Script

```python
#!/usr/bin/env python3
"""Quick health check for dataset logging system"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from app.core.dataset_logging import dataset_logger, get_log_analyzer

def health_check():
    """Perform comprehensive health check"""
    results = {
        'timestamp': datetime.now().isoformat(),
        'status': 'HEALTHY',
        'issues': [],
        'warnings': []
    }
    
    # 1. Check logging configuration
    config = dataset_logger.config
    if not config.enable_file_logging:
        results['warnings'].append("File logging is disabled")
    
    # 2. Check log directory
    if not config.log_dir.exists():
        results['issues'].append(f"Log directory missing: {config.log_dir}")
        results['status'] = 'ERROR'
    
    # 3. Check log file permissions
    try:
        test_file = config.log_dir / "test_write.tmp"
        test_file.write_text("test")
        test_file.unlink()
    except Exception as e:
        results['issues'].append(f"Cannot write to log directory: {e}")
        results['status'] = 'ERROR'
    
    # 4. Check recent log activity
    try:
        analyzer = get_log_analyzer()
        recent_logs = analyzer.read_logs(
            start_time=datetime.now() - timedelta(hours=1)
        )
        if not recent_logs:
            results['warnings'].append("No recent log activity")
    except Exception as e:
        results['issues'].append(f"Cannot read logs: {e}")
        results['status'] = 'ERROR'
    
    # 5. Check system resources
    try:
        import psutil
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage(str(config.log_dir)).percent
        
        if memory_percent > 90:
            results['warnings'].append(f"High memory usage: {memory_percent}%")
        if disk_percent > 90:
            results['warnings'].append(f"High disk usage: {disk_percent}%")
    except ImportError:
        results['warnings'].append("psutil not available for system monitoring")
    except Exception as e:
        results['warnings'].append(f"Cannot check system resources: {e}")
    
    # 6. Test logging functionality
    try:
        dataset_logger.info("Health check test message")
    except Exception as e:
        results['issues'].append(f"Cannot write log messages: {e}")
        results['status'] = 'ERROR'
    
    if results['warnings'] and results['status'] == 'HEALTHY':
        results['status'] = 'WARNING'
    
    return results

if __name__ == "__main__":
    result = health_check()
    print(json.dumps(result, indent=2))
    exit(0 if result['status'] == 'HEALTHY' else 1)
```

### Quick Status Check

```bash
# Save as check_logging_status.sh
#!/bin/bash

echo "=== Dataset Logging Status Check ==="
echo "Timestamp: $(date)"
echo

# Check environment variables
echo "Environment Configuration:"
echo "ENVIRONMENT: ${ENVIRONMENT:-not set}"
echo "DATASET_LOG_LEVEL: ${DATASET_LOG_LEVEL:-not set}"
echo "DATASET_LOG_DIR: ${DATASET_LOG_DIR:-not set}"
echo

# Check log directory
LOG_DIR="${DATASET_LOG_DIR:-logs/datasets}"
echo "Log Directory Status:"
if [ -d "$LOG_DIR" ]; then
    echo "✓ Directory exists: $LOG_DIR"
    echo "  Files: $(ls -1 "$LOG_DIR" | wc -l)"
    echo "  Size: $(du -sh "$LOG_DIR" 2>/dev/null | cut -f1)"
    echo "  Permissions: $(ls -ld "$LOG_DIR" | cut -d' ' -f1)"
else
    echo "✗ Directory missing: $LOG_DIR"
fi
echo

# Check recent activity
echo "Recent Activity:"
if [ -d "$LOG_DIR" ]; then
    RECENT_FILE=$(find "$LOG_DIR" -name "*.log" -mtime -1 | head -1)
    if [ -n "$RECENT_FILE" ]; then
        echo "✓ Recent log file: $(basename "$RECENT_FILE")"
        echo "  Last modified: $(stat -f "%Sm" "$RECENT_FILE" 2>/dev/null || stat -c "%y" "$RECENT_FILE" 2>/dev/null)"
        echo "  Size: $(ls -lh "$RECENT_FILE" | awk '{print $5}')"
        echo "  Recent entries: $(tail -n 5 "$RECENT_FILE" | wc -l)"
    else
        echo "⚠ No recent log files found"
    fi
else
    echo "✗ Cannot check - log directory missing"
fi
echo

# Check disk space
echo "Disk Space:"
df -h "$LOG_DIR" 2>/dev/null | tail -1 | awk '{print "  Available: " $4 " (" $5 " used)"}'
echo

echo "=== End Status Check ==="
```

## Common Issues

### Issue 1: No Logs Being Generated

**Symptoms:**
- Empty log directory
- No log files created
- Operations not being logged

**Diagnosis:**
```python
# Check logging configuration
from app.core.dataset_logging import dataset_logger

config = dataset_logger.config
print(f"File logging enabled: {config.enable_file_logging}")
print(f"Log directory: {config.log_dir}")
print(f"Log level: {config.log_level}")
print(f"Logger level: {dataset_logger.logger.level}")
print(f"Handlers: {len(dataset_logger.logger.handlers)}")
```

**Solutions:**

1. **Enable file logging:**
```bash
export DATASET_ENABLE_FILE_LOGGING=true
```

2. **Check log level:**
```bash
export DATASET_LOG_LEVEL=DEBUG
export DATASET_FILE_LOG_LEVEL=DEBUG
```

3. **Verify directory permissions:**
```bash
mkdir -p logs/datasets
chmod 755 logs/datasets
```

4. **Force handler setup:**
```python
from app.core.dataset_logging import DatasetLogger, LogConfig
from pathlib import Path

config = LogConfig(
    enable_file_logging=True,
    log_dir=Path("logs/datasets"),
    log_level="DEBUG"
)
logger = DatasetLogger("test", config)
logger.info("Test message")
```

### Issue 2: Log Files Too Large

**Symptoms:**
- Log files consuming excessive disk space
- Performance degradation
- Disk space warnings

**Diagnosis:**
```bash
# Check log file sizes
find logs/datasets -name "*.log*" -exec ls -lh {} \; | sort -k5 -hr

# Check total usage
du -sh logs/datasets/
```

**Solutions:**

1. **Enable compression:**
```bash
export DATASET_LOG_COMPRESSION=true
```

2. **Reduce retention period:**
```bash
export DATASET_LOG_RETENTION_DAYS=7
```

3. **Decrease log file size:**
```bash
export DATASET_MAX_LOG_FILE_SIZE_MB=50
```

4. **Increase backup count for better rotation:**
```bash
export DATASET_LOG_BACKUP_COUNT=20
```

5. **Manual cleanup:**
```bash
# Remove logs older than 7 days
find logs/datasets -name "*.log*" -mtime +7 -delete

# Compress existing logs
gzip logs/datasets/*.log
```

### Issue 3: Performance Impact

**Symptoms:**
- Slow API responses
- High CPU usage
- Memory leaks

**Diagnosis:**
```python
# Check performance settings
from app.core.dataset_logging import dataset_logger

config = dataset_logger.config
print(f"Async logging: {config.async_logging}")
print(f"Performance tracking: {config.enable_performance_tracking}")
print(f"Sampling rate: {config.performance_sampling_rate}")
print(f"Buffer size: {config.buffer_size}")

# Monitor current impact
import time
start = time.time()
for i in range(1000):
    dataset_logger.info(f"Test message {i}")
end = time.time()
print(f"1000 messages took {end - start:.2f} seconds")
```

**Solutions:**

1. **Enable async logging:**
```bash
export DATASET_ASYNC_LOGGING=true
export DATASET_LOG_BUFFER_SIZE=2048
```

2. **Reduce performance sampling:**
```bash
export DATASET_PERFORMANCE_SAMPLING_RATE=0.01  # 1% sampling
```

3. **Optimize log levels:**
```bash
export DATASET_LOG_LEVEL=INFO
export DATASET_CONSOLE_LOG_LEVEL=WARNING
```

4. **Limit message size:**
```bash
export DATASET_MAX_LOG_MESSAGE_SIZE=5000
```

### Issue 4: Missing Correlation IDs

**Symptoms:**
- Difficulty tracing operations
- Fragmented log entries
- Cannot follow operation flow

**Diagnosis:**
```python
# Check correlation ID configuration
from app.core.dataset_logging import dataset_logger

print(f"Correlation ID enabled: {dataset_logger.config.enable_correlation_id}")
print(f"Current correlation ID: {dataset_logger.correlation_id}")

# Test correlation ID generation
correlation_id = dataset_logger.set_correlation_id()
print(f"Generated correlation ID: {correlation_id}")
```

**Solutions:**

1. **Enable correlation IDs:**
```bash
export DATASET_ENABLE_CORRELATION_ID=true
```

2. **Ensure proper usage in code:**
```python
# Always use operation context
with dataset_logger.operation_context(
    operation="test_operation",
    dataset_id="test_dataset"
):
    # All logs in this context will have the same correlation ID
    dataset_logger.info("Starting operation")
    # ... operation code ...
    dataset_logger.info("Operation completed")
```

3. **Manual correlation ID setting:**
```python
# For long-running operations
correlation_id = dataset_logger.set_correlation_id("custom_id_123")
```

### Issue 5: Centralized Logging Failures

**Symptoms:**
- Logs not appearing in centralized system
- Network errors in logs
- Missing log entries

**Diagnosis:**
```python
# Check centralized logging configuration
from app.core.dataset_logging import dataset_logger

config = dataset_logger.config
print(f"Centralized logging enabled: {config.enable_centralized_logging}")
print(f"Endpoint: {config.centralized_endpoint}")
print(f"API key configured: {bool(config.centralized_api_key)}")

# Test endpoint connectivity
if config.centralized_endpoint:
    import requests
    try:
        response = requests.get(config.centralized_endpoint, timeout=5)
        print(f"Endpoint status: {response.status_code}")
    except Exception as e:
        print(f"Endpoint error: {e}")
```

**Solutions:**

1. **Check network connectivity:**
```bash
# Test endpoint reachability
curl -I https://your-log-endpoint.com/api/logs

# Check DNS resolution
nslookup your-log-endpoint.com
```

2. **Verify credentials:**
```bash
export DATASET_CENTRALIZED_API_KEY=your-valid-api-key
```

3. **Enable fallback logging:**
```bash
export DATASET_ENABLE_FILE_LOGGING=true  # Ensure local logs as backup
```

4. **Check handler status:**
```python
# Inspect centralized handler
for handler in dataset_logger.logger.handlers:
    if hasattr(handler, 'endpoint'):
        print(f"Centralized handler: {handler.endpoint}")
        print(f"Buffer size: {handler.buffer_size}")
        print(f"Worker thread alive: {handler.worker_thread.is_alive()}")
```

## Performance Problems

### High Memory Usage

**Symptoms:**
- Memory usage constantly increasing
- Out of memory errors
- System slowdown

**Diagnosis:**
```python
import psutil
import gc
from app.core.dataset_logging import dataset_logger

# Check current memory usage
process = psutil.Process()
print(f"RSS Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")
print(f"VMS Memory: {process.memory_info().vms / 1024 / 1024:.2f} MB")

# Check for memory leaks in logging
gc.collect()
before = process.memory_info().rss

# Generate many log messages
for i in range(10000):
    dataset_logger.info(f"Test message {i}")

gc.collect()
after = process.memory_info().rss
print(f"Memory increase: {(after - before) / 1024 / 1024:.2f} MB")
```

**Solutions:**

1. **Enable message size limits:**
```bash
export DATASET_MAX_LOG_MESSAGE_SIZE=1000
```

2. **Reduce buffer sizes:**
```bash
export DATASET_LOG_BUFFER_SIZE=512
```

3. **Disable memory-intensive features:**
```bash
export DATASET_ENABLE_PERFORMANCE_MONITORING=false
export DATASET_PERFORMANCE_SAMPLING_RATE=0.01
```

4. **Clean up logger resources:**
```python
# Proper cleanup
dataset_logger.close()
```

### Slow Log Processing

**Symptoms:**
- Delayed log writes
- API timeouts
- Queue full errors

**Diagnosis:**
```python
import time
from app.core.dataset_logging import dataset_logger

# Test logging speed
start = time.time()
for i in range(1000):
    dataset_logger.info(f"Speed test {i}")
duration = time.time() - start
print(f"1000 messages in {duration:.2f}s ({1000/duration:.0f} msg/s)")

# Check async queue status
if hasattr(dataset_logger, '_async_queue'):
    print(f"Queue size: {dataset_logger._async_queue.qsize()}")
    print(f"Queue maxsize: {dataset_logger._async_queue.maxsize}")
```

**Solutions:**

1. **Optimize async settings:**
```bash
export DATASET_ASYNC_LOGGING=true
export DATASET_LOG_BUFFER_SIZE=4096
```

2. **Reduce log verbosity:**
```bash
export DATASET_LOG_LEVEL=WARNING
```

3. **Use performance decorator sparingly:**
```python
# Only monitor critical functions
@monitor_performance(threshold_seconds=30.0)
def critical_function():
    pass
```

## Configuration Issues

### Environment Variable Problems

**Common Problems:**
- Variables not being read
- Type conversion errors
- Missing required variables

**Diagnosis Script:**
```python
#!/usr/bin/env python3
"""Diagnose environment variable issues"""

import os
from app.core.dataset_logging import LogConfig

def check_env_vars():
    """Check all dataset logging environment variables"""
    expected_vars = {
        'ENVIRONMENT': str,
        'DATASET_LOG_LEVEL': str,
        'DATASET_ENABLE_FILE_LOGGING': bool,
        'DATASET_LOG_DIR': str,
        'DATASET_MAX_LOG_FILE_SIZE_MB': int,
        'DATASET_LOG_RETENTION_DAYS': int,
        'DATASET_ASYNC_LOGGING': bool,
        'DATASET_PERFORMANCE_SAMPLING_RATE': float,
    }
    
    print("Environment Variable Check:")
    print("-" * 40)
    
    for var_name, var_type in expected_vars.items():
        value = os.getenv(var_name)
        print(f"{var_name}: {value}")
        
        if value is not None:
            try:
                if var_type == bool:
                    converted = value.lower() == 'true'
                elif var_type == int:
                    converted = int(value)
                elif var_type == float:
                    converted = float(value)
                else:
                    converted = value
                print(f"  ✓ Converts to {var_type.__name__}: {converted}")
            except Exception as e:
                print(f"  ✗ Conversion error: {e}")
        else:
            print(f"  - Not set (will use default)")
    
    print("\nTesting LogConfig creation:")
    try:
        config = LogConfig.from_environment()
        print("✓ LogConfig created successfully")
        print(f"  Log level: {config.log_level}")
        print(f"  Log dir: {config.log_dir}")
        print(f"  Async: {config.async_logging}")
    except Exception as e:
        print(f"✗ LogConfig creation failed: {e}")

if __name__ == "__main__":
    check_env_vars()
```

### File Permission Issues

**Diagnosis:**
```bash
# Check log directory permissions
LOG_DIR="${DATASET_LOG_DIR:-logs/datasets}"
echo "Directory: $LOG_DIR"
ls -ld "$LOG_DIR"

# Check parent directory permissions
ls -ld "$(dirname "$LOG_DIR")"

# Test write permissions
echo "test" > "$LOG_DIR/test_write.tmp" && rm "$LOG_DIR/test_write.tmp" && echo "✓ Write OK" || echo "✗ Write failed"
```

**Solutions:**
```bash
# Fix directory permissions
mkdir -p logs/datasets
chmod 755 logs/datasets
chown $(whoami) logs/datasets

# Fix parent directory if needed
chmod 755 logs
```

## Log Analysis Problems

### Cannot Read Log Files

**Symptoms:**
- Empty results from log analyzer
- File not found errors
- Encoding issues

**Diagnosis:**
```python
from pathlib import Path
from app.core.dataset_logging import get_log_analyzer

analyzer = get_log_analyzer()
print(f"Log directory: {analyzer.log_dir}")
print(f"Directory exists: {analyzer.log_dir.exists()}")

if analyzer.log_dir.exists():
    log_files = list(analyzer.log_dir.glob("*.log*"))
    print(f"Log files found: {len(log_files)}")
    for file in log_files[:5]:  # Show first 5
        print(f"  {file.name} - {file.stat().st_size} bytes")

# Test reading
try:
    logs = analyzer.read_logs()
    print(f"Logs read successfully: {len(logs)}")
except Exception as e:
    print(f"Error reading logs: {e}")
```

**Solutions:**

1. **Fix file encoding:**
```python
# Check file encoding
import chardet

log_file = Path("logs/datasets/dataset_ops_20240115.log")
if log_file.exists():
    with open(log_file, 'rb') as f:
        sample = f.read(10000)
        encoding = chardet.detect(sample)
        print(f"Detected encoding: {encoding}")
```

2. **Repair corrupted log files:**
```bash
# Check for non-UTF8 characters
grep -axv '.*' logs/datasets/*.log || echo "Files are clean"

# Remove problematic lines
sed -i '/[^\x00-\x7F]/d' logs/datasets/dataset_ops_*.log
```

### JSON Parsing Errors

**Symptoms:**
- JSONDecodeError in logs
- Partial log entries
- Mixed format logs

**Diagnosis:**
```python
import json
from pathlib import Path

def check_json_validity(log_file):
    """Check JSON validity of log entries"""
    valid_lines = 0
    invalid_lines = 0
    
    with open(log_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
                valid_lines += 1
            except json.JSONDecodeError as e:
                invalid_lines += 1
                if invalid_lines <= 5:  # Show first 5 errors
                    print(f"Line {line_num}: {e}")
                    print(f"Content: {line[:100]}...")
    
    print(f"Valid JSON lines: {valid_lines}")
    print(f"Invalid JSON lines: {invalid_lines}")

# Check all log files
log_dir = Path("logs/datasets")
for log_file in log_dir.glob("*.log"):
    print(f"\nChecking {log_file.name}:")
    check_json_validity(log_file)
```

**Solutions:**

1. **Enable structured logging consistently:**
```bash
export DATASET_ENABLE_STRUCTURED_LOGGING=true
```

2. **Clean invalid entries:**
```python
#!/usr/bin/env python3
"""Clean invalid JSON entries from log files"""

import json
import shutil
from pathlib import Path

def clean_log_file(log_file):
    """Remove invalid JSON lines from log file"""
    backup_file = log_file.with_suffix('.log.backup')
    shutil.copy2(log_file, backup_file)
    
    valid_lines = []
    with open(log_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
                valid_lines.append(line)
            except json.JSONDecodeError:
                continue  # Skip invalid lines
    
    with open(log_file, 'w') as f:
        for line in valid_lines:
            f.write(line + '\n')
    
    print(f"Cleaned {log_file.name}: kept {len(valid_lines)} valid lines")

# Clean all log files
log_dir = Path("logs/datasets")
for log_file in log_dir.glob("*.log"):
    clean_log_file(log_file)
```

## Emergency Procedures

### Complete Logging Failure

**Emergency Reset:**
```bash
#!/bin/bash
# Emergency logging reset script

echo "=== EMERGENCY LOGGING RESET ==="

# 1. Stop any running services
echo "1. Stopping services..."
# Add your service stop commands here

# 2. Backup existing logs
echo "2. Backing up existing logs..."
BACKUP_DIR="logs_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r logs/datasets/* "$BACKUP_DIR/" 2>/dev/null || echo "No existing logs to backup"

# 3. Clean log directory
echo "3. Cleaning log directory..."
rm -rf logs/datasets/*

# 4. Reset permissions
echo "4. Resetting permissions..."
mkdir -p logs/datasets
chmod 755 logs/datasets

# 5. Reset environment variables
echo "5. Resetting environment..."
export DATASET_ENABLE_FILE_LOGGING=true
export DATASET_LOG_LEVEL=INFO
export DATASET_ASYNC_LOGGING=true
export DATASET_ENABLE_STRUCTURED_LOGGING=true

# 6. Test logging
echo "6. Testing logging..."
python3 -c "
from app.core.dataset_logging import dataset_logger
dataset_logger.info('Emergency reset test - logging restored')
print('Logging test completed')
"

echo "=== EMERGENCY RESET COMPLETE ==="
echo "Backup location: $BACKUP_DIR"
```

### Disk Space Emergency

**Quick Cleanup:**
```bash
#!/bin/bash
# Emergency disk space cleanup

echo "=== EMERGENCY DISK CLEANUP ==="

LOG_DIR="${DATASET_LOG_DIR:-logs/datasets}"

# Check current usage
echo "Current disk usage:"
du -sh "$LOG_DIR"
df -h "$LOG_DIR"

# 1. Compress uncompressed logs
echo "1. Compressing logs..."
find "$LOG_DIR" -name "*.log" -mtime +1 -exec gzip {} \;

# 2. Remove old compressed logs
echo "2. Removing logs older than 3 days..."
find "$LOG_DIR" -name "*.log.gz" -mtime +3 -delete

# 3. Truncate current logs if too large
echo "3. Truncating large current logs..."
find "$LOG_DIR" -name "*.log" -size +100M -exec truncate -s 50M {} \;

# 4. Show final usage
echo "Final disk usage:"
du -sh "$LOG_DIR"
df -h "$LOG_DIR"

echo "=== CLEANUP COMPLETE ==="
```

## Debug Commands

### Comprehensive Debug Script

```python
#!/usr/bin/env python3
"""Comprehensive debug script for dataset logging"""

import json
import os
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

def debug_logging_system():
    """Run comprehensive debugging"""
    debug_info = {
        'timestamp': datetime.now().isoformat(),
        'python_version': sys.version,
        'working_directory': os.getcwd(),
        'environment_variables': {},
        'configuration': {},
        'file_system': {},
        'functionality': {},
        'errors': []
    }
    
    # 1. Environment variables
    env_vars = [k for k in os.environ.keys() if k.startswith('DATASET_')]
    for var in env_vars:
        debug_info['environment_variables'][var] = os.environ[var]
    
    # 2. Configuration testing
    try:
        from app.core.dataset_logging import LogConfig, DatasetLogger
        config = LogConfig.from_environment()
        debug_info['configuration'] = {
            'environment': config.environment,
            'log_level': config.log_level,
            'enable_file_logging': config.enable_file_logging,
            'log_dir': str(config.log_dir),
            'async_logging': config.async_logging,
            'enable_structured_logging': config.enable_structured_logging,
            'enable_performance_tracking': config.enable_performance_tracking,
            'enable_centralized_logging': config.enable_centralized_logging
        }
    except Exception as e:
        debug_info['errors'].append(f"Configuration error: {e}")
        debug_info['errors'].append(traceback.format_exc())
    
    # 3. File system checks
    try:
        log_dir = Path(debug_info['configuration'].get('log_dir', 'logs/datasets'))
        debug_info['file_system'] = {
            'log_dir_exists': log_dir.exists(),
            'log_dir_writable': os.access(log_dir.parent, os.W_OK) if log_dir.parent.exists() else False,
            'log_files_count': len(list(log_dir.glob('*.log*'))) if log_dir.exists() else 0,
            'total_size_mb': sum(f.stat().st_size for f in log_dir.glob('*') if f.is_file()) / 1024 / 1024 if log_dir.exists() else 0
        }
    except Exception as e:
        debug_info['errors'].append(f"File system error: {e}")
    
    # 4. Functionality testing
    try:
        logger = DatasetLogger("debug_test")
        
        # Test basic logging
        logger.info("Debug test message")
        
        # Test structured logging
        logger.info("Structured test", test_field="test_value", test_number=123)
        
        # Test operation context
        with logger.operation_context("debug_operation", dataset_id="debug_dataset"):
            logger.info("Context test message")
        
        debug_info['functionality']['basic_logging'] = True
        debug_info['functionality']['structured_logging'] = True
        debug_info['functionality']['operation_context'] = True
        
    except Exception as e:
        debug_info['errors'].append(f"Functionality error: {e}")
        debug_info['errors'].append(traceback.format_exc())
    
    # 5. Log analysis testing
    try:
        from app.core.dataset_logging import get_log_analyzer
        analyzer = get_log_analyzer()
        recent_logs = analyzer.read_logs(
            start_time=datetime.now() - timedelta(hours=1)
        )
        debug_info['functionality']['log_analysis'] = True
        debug_info['functionality']['recent_logs_count'] = len(recent_logs)
    except Exception as e:
        debug_info['errors'].append(f"Log analysis error: {e}")
    
    return debug_info

if __name__ == "__main__":
    print("=== DATASET LOGGING DEBUG REPORT ===")
    debug_result = debug_logging_system()
    print(json.dumps(debug_result, indent=2, default=str))
    
    if debug_result['errors']:
        print(f"\n⚠️  {len(debug_result['errors'])} errors found!")
        sys.exit(1)
    else:
        print("\n✅ All checks passed!")
        sys.exit(0)
```

### Log Validation Script

```python
#!/usr/bin/env python3
"""Validate log file integrity and format"""

import json
import gzip
from collections import defaultdict
from datetime import datetime
from pathlib import Path

def validate_log_files(log_dir):
    """Validate all log files in directory"""
    log_dir = Path(log_dir)
    results = {
        'total_files': 0,
        'valid_files': 0,
        'invalid_files': 0,
        'total_entries': 0,
        'valid_entries': 0,
        'invalid_entries': 0,
        'issues': [],
        'statistics': defaultdict(int)
    }
    
    for log_file in log_dir.glob('*.log*'):
        results['total_files'] += 1
        file_valid = True
        
        try:
            # Open file (handle gzipped files)
            if log_file.suffix == '.gz':
                f = gzip.open(log_file, 'rt')
            else:
                f = open(log_file, 'r')
            
            with f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    results['total_entries'] += 1
                    
                    try:
                        entry = json.loads(line)
                        results['valid_entries'] += 1
                        
                        # Collect statistics
                        if 'level' in entry:
                            results['statistics'][f"level_{entry['level']}"] += 1
                        if 'operation' in entry:
                            results['statistics'][f"operation_{entry['operation']}"] += 1
                        
                        # Validate required fields
                        required_fields = ['timestamp', 'level', 'message']
                        missing_fields = [f for f in required_fields if f not in entry]
                        if missing_fields:
                            results['issues'].append(
                                f"{log_file.name}:{line_num} - Missing fields: {missing_fields}"
                            )
                        
                        # Validate timestamp format
                        if 'timestamp' in entry:
                            try:
                                datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                            except ValueError:
                                results['issues'].append(
                                    f"{log_file.name}:{line_num} - Invalid timestamp: {entry['timestamp']}"
                                )
                        
                    except json.JSONDecodeError as e:
                        results['invalid_entries'] += 1
                        file_valid = False
                        results['issues'].append(
                            f"{log_file.name}:{line_num} - JSON error: {e}"
                        )
        
        except Exception as e:
            file_valid = False
            results['issues'].append(f"{log_file.name} - File error: {e}")
        
        if file_valid:
            results['valid_files'] += 1
        else:
            results['invalid_files'] += 1
    
    return results

if __name__ == "__main__":
    import sys
    log_dir = sys.argv[1] if len(sys.argv) > 1 else "logs/datasets"
    
    print(f"Validating log files in: {log_dir}")
    results = validate_log_files(log_dir)
    
    print(f"\nValidation Results:")
    print(f"Files: {results['valid_files']}/{results['total_files']} valid")
    print(f"Entries: {results['valid_entries']}/{results['total_entries']} valid")
    
    if results['issues']:
        print(f"\nIssues found ({len(results['issues'])}):")
        for issue in results['issues'][:10]:  # Show first 10
            print(f"  - {issue}")
        if len(results['issues']) > 10:
            print(f"  ... and {len(results['issues']) - 10} more")
    
    print(f"\nStatistics:")
    for key, count in sorted(results['statistics'].items()):
        print(f"  {key}: {count}")
```

This troubleshooting guide provides comprehensive solutions for common dataset logging issues in ViolentUTF. Use the diagnostic scripts to identify problems quickly and apply the appropriate solutions based on the specific symptoms you encounter.