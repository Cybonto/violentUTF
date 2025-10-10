# Troubleshooting: Dataset Integration Issues

## Overview

This comprehensive troubleshooting guide addresses common issues encountered when working with ViolentUTF's dataset integration system. The guide covers dataset conversion problems, configuration errors, performance issues, and integration challenges across all supported dataset types.

## Quick Diagnostic Checklist

Before diving into specific troubleshooting procedures, run through this quick diagnostic checklist:

```yaml
Pre_Troubleshooting_Checklist:
  system_status:
    - "Verify all ViolentUTF services are running: ./check_services.sh"
    - "Check system resources: memory, CPU, and storage availability"
    - "Validate network connectivity and API accessibility"
    - "Confirm authentication and access permissions"

  dataset_basics:
    - "Verify dataset file exists and is accessible"
    - "Check dataset file format and structure"
    - "Validate dataset size and processing requirements"
    - "Confirm dataset type and converter compatibility"

  configuration_validation:
    - "Review dataset configuration parameters"
    - "Check for required dependencies and libraries"
    - "Validate environment variables and settings"
    - "Confirm PyRIT integration status"
```

## Common Dataset Integration Issues

### Dataset Conversion Problems

#### Issue: Dataset Conversion Fails with Format Errors

**Symptoms:**
- Conversion process stops with validation errors
- "Unsupported format" or "Invalid dataset structure" messages
- Partial conversion with missing data
- Converter crashes or becomes unresponsive

**Diagnostic Steps:**
```bash
# Verify dataset format and structure
python -m violentutf.utils.dataset_validator \
  --dataset-path /path/to/dataset \
  --validate-format \
  --verbose

# Check converter compatibility
python -m violentutf.converters.check_compatibility \
  --dataset-type TARGET_TYPE \
  --file-path /path/to/dataset

# Validate file integrity
file /path/to/dataset
head -50 /path/to/dataset  # For text-based formats
```

**Common Causes and Solutions:**

1. **Incorrect File Format**
   - **Cause**: Dataset file is in unexpected format (e.g., expecting JSON but file is CSV)
   - **Solution**: Verify dataset format matches expected converter input
   ```bash
   # Check actual file format
   file /path/to/dataset

   # Use appropriate converter
   python -m violentutf.converters.auto_detect \
     --file-path /path/to/dataset
   ```

2. **Corrupted or Incomplete Dataset Files**
   - **Cause**: File corruption during download or transfer
   - **Solution**: Re-download dataset and verify checksums
   ```bash
   # Verify file integrity
   sha256sum /path/to/dataset

   # Compare with known good checksum
   # Re-download if corruption detected
   ```

3. **Missing Required Fields**
   - **Cause**: Dataset missing required columns or fields for conversion
   - **Solution**: Review dataset schema requirements and data preprocessing
   ```python
   # Check required fields for dataset type
   from violentutf.converters import get_required_fields
   required_fields = get_required_fields("OllaGen1")
   print(f"Required fields: {required_fields}")
   ```

4. **Encoding Issues**
   - **Cause**: Character encoding problems (UTF-8, ASCII, etc.)
   - **Solution**: Specify correct encoding or convert file encoding
   ```bash
   # Check file encoding
   file -i /path/to/dataset

   # Convert encoding if needed
   iconv -f ISO-8859-1 -t UTF-8 input.txt > output.txt
   ```

#### Issue: Data Integrity Problems After Conversion

**Symptoms:**
- Missing data in converted dataset
- Incorrect data types or values
- Inconsistent record counts
- Validation errors in converted dataset

**Diagnostic Steps:**
```bash
# Compare source and converted data statistics
python -m violentutf.utils.data_comparison \
  --source /path/to/original \
  --converted /path/to/converted \
  --generate-report

# Validate converted dataset integrity
python -m violentutf.validators.dataset_integrity \
  --dataset-path /path/to/converted \
  --thorough-check
```

**Solutions:**

1. **Schema Mapping Issues**
   ```python
   # Review and adjust schema mapping
   from violentutf.converters import get_schema_mapping
   mapping = get_schema_mapping("source_format", "target_format")

   # Customize mapping for specific dataset
   custom_mapping = {
       "source_field": "target_field",
       "data_transformation": "custom_function"
   }
   ```

2. **Data Type Conversion Problems**
   ```python
   # Implement custom data type conversion
   def custom_type_converter(value, target_type):
       try:
           return target_type(value)
       except (ValueError, TypeError):
           return None  # Or default value
   ```

3. **Missing Data Handling**
   ```python
   # Configure missing data handling strategy
   missing_data_strategy = {
       "drop_missing": False,
       "fill_strategy": "default_value",
       "validation_level": "strict"
   }
   ```

### Configuration and Parameter Issues

#### Issue: Configuration Validation Errors

**Symptoms:**
- "Invalid configuration" error messages
- Parameter out of range errors
- Configuration file parsing errors
- Incompatible parameter combinations

**Diagnostic Steps:**
```bash
# Validate configuration file
python -m violentutf.utils.config_validator \
  --config-file /path/to/config.yaml \
  --schema-validation

# Check parameter ranges and compatibility
python -m violentutf.utils.parameter_checker \
  --dataset-type DATASET_TYPE \
  --config-file /path/to/config.yaml
```

**Solutions:**

1. **Parameter Range Validation**
   ```yaml
   # Example: OllaGen1 valid parameter ranges
   OllaGen1_valid_ranges:
     scenario_limit: [1, 169999]
     question_types: ["WCP", "WHO", "TeamRisk", "TargetFactor"]
     complexity_level: ["basic", "medium", "high"]
   ```

2. **Configuration File Syntax**
   ```yaml
   # Correct YAML syntax
   dataset_config:
     type: "OllaGen1"
     parameters:
       scenario_limit: 10000
       question_types: ["WCP", "WHO"]
     validation:
       enabled: true
   ```

3. **Dependency Validation**
   ```bash
   # Check required dependencies
   python -m violentutf.utils.dependency_checker \
     --dataset-type DATASET_TYPE \
     --install-missing
   ```

#### Issue: PyRIT Integration Failures

**Symptoms:**
- PyRIT compatibility errors
- Orchestrator initialization failures
- Target configuration problems
- Memory or scorer integration issues

**Diagnostic Steps:**
```bash
# Test PyRIT integration
python -m violentutf.utils.pyrit_integration_test \
  --dataset-type DATASET_TYPE \
  --verbose

# Check PyRIT compatibility
python -c "import pyrit; print(pyrit.__version__)"

# Validate target configuration
python -m violentutf.targets.validate_configuration \
  --target-type CUSTOM_TARGET
```

**Solutions:**

1. **PyRIT Version Compatibility**
   ```bash
   # Install compatible PyRIT version
   pip install pyrit==X.Y.Z  # Replace with compatible version

   # Update requirements if needed
   pip install -r violentutf/requirements.txt
   ```

2. **Target Configuration**
   ```python
   # Verify target configuration
   from violentutf.custom_targets import CustomTarget

   target_config = {
       "endpoint_url": "http://localhost:9080/api/v1",
       "authentication": "bearer_token",
       "timeout": 30
   }

   target = CustomTarget(**target_config)
   ```

3. **Memory Integration**
   ```python
   # Configure PyRIT memory integration
   from pyrit.memory import DuckDBMemory

   memory = DuckDBMemory(db_path="./pyrit_memory.db")
   # Ensure proper cleanup and connection management
   ```

### Performance and Resource Issues

#### Issue: Slow Processing or System Unresponsiveness

**Symptoms:**
- Extended processing times for datasets
- System becomes unresponsive during evaluation
- High CPU or memory usage
- Timeout errors

**Diagnostic Steps:**
```bash
# Monitor system resources
top -p $(pgrep -f violentutf)
htop  # If available

# Check memory usage patterns
python -m violentutf.utils.memory_profiler \
  --dataset-type DATASET_TYPE \
  --scenario-count 10000

# Profile processing performance
python -m violentutf.utils.performance_profiler \
  --config-file /path/to/config.yaml \
  --profile-output profile_results.txt
```

**Solutions:**

1. **Memory Optimization**
   ```yaml
   # Enable memory optimization settings
   performance_config:
     memory_management: true
     progressive_loading: true
     batch_size: 1000
     cleanup_frequency: 100
   ```

2. **Processing Optimization**
   ```yaml
   # Optimize processing parameters
   processing_optimization:
     parallel_processing: false  # For resource-constrained systems
     scenario_limit: 5000       # Reduce for initial testing
     timeout_per_request: 60    # Increase for slow systems
   ```

3. **Resource Allocation**
   ```bash
   # Adjust system resource limits
   ulimit -m 2048000  # Set memory limit (KB)
   ulimit -v 4096000  # Set virtual memory limit

   # Use nice to adjust process priority
   nice -n 10 python dataset_evaluation.py
   ```

#### Issue: Out of Memory Errors

**Symptoms:**
- "Out of memory" or "MemoryError" exceptions
- System swap usage increases dramatically
- Process killed by system (OOM killer)
- Gradual memory leaks during processing

**Diagnostic Steps:**
```bash
# Monitor memory usage over time
python -m violentutf.utils.memory_monitor \
  --duration 300 \
  --interval 5 \
  --output memory_usage.log

# Check for memory leaks
python -m violentutf.utils.memory_leak_detector \
  --test-duration 60 \
  --iterations 10
```

**Solutions:**

1. **Enable File Splitting**
   ```yaml
   # Automatic file splitting for large datasets
   file_processing:
     enable_splitting: true
     max_chunk_size: "50MB"
     overlap_size: 100  # Records
     cleanup_chunks: true
   ```

2. **Progressive Loading**
   ```python
   # Implement progressive loading strategy
   def progressive_dataset_loader(dataset_path, chunk_size=1000):
       for chunk in read_dataset_chunks(dataset_path, chunk_size):
           yield process_chunk(chunk)
           # Explicit garbage collection
           import gc
           gc.collect()
   ```

3. **Memory Monitoring and Limits**
   ```python
   # Set memory limits and monitoring
   import resource
   import psutil

   # Set memory limit (in bytes)
   resource.setrlimit(resource.RLIMIT_AS, (2048*1024*1024, -1))

   # Monitor memory usage
   process = psutil.Process()
   memory_usage = process.memory_info().rss / 1024 / 1024  # MB
   ```

### Integration and Compatibility Issues

#### Issue: Service Dependencies Not Available

**Symptoms:**
- "Service unavailable" errors
- Connection timeouts to required services
- Authentication failures
- API endpoint not responding

**Diagnostic Steps:**
```bash
# Check service status
./check_services.sh --detailed

# Test individual service connectivity
curl -i http://localhost:8501  # Streamlit
curl -i http://localhost:9080/health  # FastAPI
curl -i http://localhost:8080  # Keycloak

# Check service logs
docker-compose logs -f violentutf_api
docker-compose logs -f keycloak
```

**Solutions:**

1. **Service Startup**
   ```bash
   # Start required services
   cd violentutf_api && docker-compose up -d
   cd keycloak && docker-compose up -d
   cd apisix && docker-compose up -d

   # Wait for services to initialize
   sleep 30

   # Verify service health
   ./check_services.sh
   ```

2. **Authentication Configuration**
   ```bash
   # Reset authentication if needed
   python violentutf_api/fastapi_app/diagnose_user_context.py

   # Verify API token configuration
   export VIOLENTUTF_API_TOKEN="your_token_here"
   ```

3. **Network Configuration**
   ```yaml
   # docker-compose.yml network configuration
   networks:
     violentutf-network:
       driver: bridge

   services:
     api:
       networks:
         - violentutf-network
   ```

#### Issue: Version Compatibility Problems

**Symptoms:**
- "Incompatible version" warnings or errors
- Unexpected behavior after updates
- Missing features or functions
- Import errors for specific modules

**Diagnostic Steps:**
```bash
# Check version compatibility
python -m violentutf.utils.version_checker \
  --check-all-dependencies

# Verify specific component versions
python -c "import violentutf; print(violentutf.__version__)"
python -c "import pyrit; print(pyrit.__version__)"
python -c "import streamlit; print(streamlit.__version__)"
```

**Solutions:**

1. **Version Synchronization**
   ```bash
   # Update to compatible versions
   pip install -r violentutf/requirements.txt --upgrade

   # Pin specific versions if needed
   pip install pyrit==1.0.0 streamlit==1.28.0
   ```

2. **Virtual Environment Reset**
   ```bash
   # Create fresh virtual environment
   python -m venv .vitutf_new
   source .vitutf_new/bin/activate
   pip install -r violentutf/requirements.txt
   pip install -r violentutf_api/fastapi_app/requirements.txt
   ```

## Dataset-Specific Troubleshooting

### OllaGen1 Cognitive Behavioral Assessment Issues

**Common Problems:**
```yaml
OllaGen1_Specific_Issues:
  question_type_errors:
    symptoms: "Invalid question type specified"
    solution: "Use only: WCP, WHO, TeamRisk, TargetFactor"

  scenario_limit_exceeded:
    symptoms: "Scenario limit exceeds dataset size"
    solution: "Maximum 169,999 scenarios available"

  memory_issues_large_datasets:
    symptoms: "Memory exhaustion with >50,000 scenarios"
    solution: "Enable progressive loading or reduce scenario count"
```

### Garak Red-Teaming Integration Issues

**Common Problems:**
```yaml
Garak_Specific_Issues:
  vulnerability_scanner_timeout:
    symptoms: "Garak scans timeout or fail to complete"
    solution: "Increase timeout settings and reduce scan scope"

  false_positive_rates:
    symptoms: "High number of false positive vulnerability reports"
    solution: "Adjust sensitivity thresholds and enable manual validation"

  model_compatibility:
    symptoms: "Target model not compatible with Garak scanners"
    solution: "Verify model API compatibility and update target configuration"
```

### LegalBench Legal Reasoning Issues

**Common Problems:**
```yaml
LegalBench_Specific_Issues:
  jurisdiction_accuracy:
    symptoms: "Incorrect legal analysis for specific jurisdictions"
    solution: "Specify jurisdiction context and legal framework"

  professional_standard_alignment:
    symptoms: "Results don't align with professional legal standards"
    solution: "Validate with legal professionals and adjust criteria"

  complex_case_processing:
    symptoms: "Poor performance on complex legal scenarios"
    solution: "Increase processing time limits and enable advanced analysis"
```

## Emergency Recovery Procedures

### System Recovery Workflow

```bash
#!/bin/bash
# Emergency recovery script

echo "Starting ViolentUTF emergency recovery..."

# 1. Stop all services
echo "Stopping services..."
docker-compose down --remove-orphans

# 2. Backup current data
echo "Creating backup..."
timestamp=$(date +%Y%m%d_%H%M%S)
mkdir -p backups/$timestamp
cp -r app_data backups/$timestamp/
cp -r *.db backups/$timestamp/ 2>/dev/null || true

# 3. Clean temporary files
echo "Cleaning temporary files..."
rm -rf app_data/violentutf/cache/*
rm -rf /tmp/violentutf_*

# 4. Restart services
echo "Restarting services..."
./setup_macos_new.sh --cleanup
./setup_macos_new.sh

# 5. Verify system health
echo "Verifying system health..."
./check_services.sh

echo "Recovery complete. Check output above for any errors."
```

### Data Recovery Procedures

```bash
# Recover from backup
restore_backup() {
    backup_date=$1
    echo "Restoring from backup: $backup_date"

    # Stop services
    docker-compose down

    # Restore data
    cp -r backups/$backup_date/app_data ./
    cp backups/$backup_date/*.db ./ 2>/dev/null || true

    # Restart services
    ./setup_macos_new.sh
}

# Database recovery
recover_database() {
    echo "Recovering database..."

    # Backup current state
    cp violentutf.db violentutf.db.corrupted

    # Initialize new database
    python -m violentutf.database.initialize --fresh

    # Attempt data recovery from backup
    python -m violentutf.database.recover --source violentutf.db.corrupted
}
```

## Prevention and Monitoring

### Preventive Measures

```yaml
Prevention_Best_Practices:
  regular_maintenance:
    - "Run ./check_services.sh daily"
    - "Monitor system resources and performance"
    - "Keep regular backups of datasets and configurations"
    - "Update dependencies and system components regularly"

  monitoring_setup:
    - "Enable logging for all components"
    - "Set up disk space and memory monitoring"
    - "Configure alerts for service failures"
    - "Monitor API response times and error rates"

  testing_procedures:
    - "Test configurations with small datasets before full runs"
    - "Validate new datasets before processing"
    - "Run integration tests after system updates"
    - "Perform periodic end-to-end system tests"
```

### Monitoring and Alerting

```bash
# System monitoring script
#!/bin/bash
# monitor_system.sh

# Check disk space
disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $disk_usage -gt 85 ]; then
    echo "WARNING: Disk usage is ${disk_usage}%"
fi

# Check memory usage
memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ $memory_usage -gt 85 ]; then
    echo "WARNING: Memory usage is ${memory_usage}%"
fi

# Check service health
if ! ./check_services.sh > /dev/null 2>&1; then
    echo "ERROR: Service health check failed"
fi

# Check recent errors in logs
error_count=$(grep -c "ERROR" violentutf_logs/app.log 2>/dev/null || echo 0)
if [ $error_count -gt 10 ]; then
    echo "WARNING: ${error_count} errors in recent logs"
fi
```

## Getting Additional Help

### Support Resources

1. **Built-in Diagnostics**
   ```bash
   # Run comprehensive diagnostics
   python -m violentutf.utils.system_diagnostics \
     --full-check \
     --output diagnostics_report.txt
   ```

2. **Log Analysis**
   ```bash
   # Analyze logs for common issues
   python -m violentutf.utils.log_analyzer \
     --log-file violentutf_logs/app.log \
     --detect-patterns \
     --suggest-solutions
   ```

3. **Community Support**
   - GitHub Issues: Report bugs and request features
   - Documentation: Check latest troubleshooting updates
   - Community Forums: Share experiences and solutions

4. **Professional Support**
   - Enterprise Support: Available for enterprise deployments
   - Consultation Services: Expert guidance for complex issues
   - Custom Integration: Support for specialized requirements

### Escalation Procedures

```yaml
Issue_Escalation_Matrix:
  severity_1_critical:
    description: "System completely non-functional"
    response_time: "Immediate"
    escalation: "Direct to senior support"

  severity_2_high:
    description: "Major functionality impaired"
    response_time: "Within 2 hours"
    escalation: "Standard support with priority"

  severity_3_medium:
    description: "Minor functionality issues"
    response_time: "Within 24 hours"
    escalation: "Standard support queue"

  severity_4_low:
    description: "Enhancement requests or minor issues"
    response_time: "Within 1 week"
    escalation: "Community support or feature request"
```

Remember to always include relevant log files, configuration details, and system information when seeking support. This troubleshooting guide should resolve most common issues, but don't hesitate to reach out for additional assistance when needed.
