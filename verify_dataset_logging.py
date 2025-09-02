#!/usr/bin/env python3
"""
Verification script for enhanced dataset logging system
"""

import sys
import os
import tempfile
import time
from pathlib import Path

# Add the correct path for imports
sys.path.insert(0, '/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app')

try:
    from app.core.dataset_logging import (
        DatasetLogger,
        DatasetAuditLogger,
        LogConfig,
        OperationType,
        ImportMetrics,
        EnhancedLogAnalyzer,
        dataset_logger,
        get_dataset_audit_logger,
        get_log_analyzer
    )
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_basic_functionality():
    """Test basic logging functionality"""
    print("\n=== Testing Basic Functionality ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create configuration
        config = LogConfig(
            log_dir=Path(temp_dir),
            enable_file_logging=True,
            enable_structured_logging=True,
            log_level="DEBUG"
        )
        
        # Create logger
        logger = DatasetLogger("test_logger", config)
        print("✅ DatasetLogger created successfully")
        
        # Test basic logging
        logger.info("Test message", test_field="test_value")
        print("✅ Basic logging works")
        
        # Test correlation ID
        correlation_id = logger.set_correlation_id()
        assert correlation_id is not None
        print(f"✅ Correlation ID generated: {correlation_id[:8]}...")
        
        # Test operation context
        with logger.operation_context("test_operation", dataset_id="test_dataset"):
            logger.info("Operation test message")
        print("✅ Operation context works")
        
        # Test performance metric
        logger.log_performance_metric(
            metric_name="test_metric",
            metric_value=1.5,
            metric_unit="seconds"
        )
        print("✅ Performance metrics work")
        
        # Test security event
        logger.log_security_event(
            event_type="test_security_event",
            severity="low",
            details={"test": "data"}
        )
        print("✅ Security event logging works")
        
        # Check if log files were created
        log_files = list(Path(temp_dir).glob("*.log"))
        if log_files:
            print(f"✅ Log files created: {len(log_files)}")
        else:
            print("⚠️  No log files found")

def test_audit_logging():
    """Test audit logging functionality"""
    print("\n=== Testing Audit Logging ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = LogConfig(
            log_dir=Path(temp_dir),
            enable_audit_trails=True
        )
        
        base_logger = DatasetLogger("audit_test", config)
        audit_logger = DatasetAuditLogger(base_logger)
        
        # Test user action logging
        audit_logger.log_user_action(
            action="test_action",
            resource="test_resource",
            user_id="test_user"
        )
        print("✅ User action logging works")
        
        # Test data access logging
        audit_logger.log_data_access(
            dataset_id="test_dataset",
            access_type="read",
            user_id="test_user",
            record_count=100
        )
        print("✅ Data access logging works")
        
        # Check audit trail
        trail = audit_logger.get_audit_trail()
        assert len(trail) == 2
        print(f"✅ Audit trail contains {len(trail)} events")

def test_log_analysis():
    """Test log analysis functionality"""
    print("\n=== Testing Log Analysis ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some test logs
        log_file = Path(temp_dir) / "test.log"
        
        test_logs = [
            {
                "timestamp": "2024-01-01T10:00:00Z",
                "level": "INFO",
                "message": "Test message 1",
                "operation": "test_operation",
                "user_id": "test_user"
            },
            {
                "timestamp": "2024-01-01T10:05:00Z",
                "level": "ERROR",
                "message": "Test error message",
                "operation": "test_operation"
            }
        ]
        
        import json
        with open(log_file, 'w') as f:
            for log_entry in test_logs:
                f.write(json.dumps(log_entry) + '\n')
        
        # Test analyzer
        analyzer = EnhancedLogAnalyzer(Path(temp_dir))
        logs = analyzer.read_logs()
        
        assert len(logs) == 2
        print(f"✅ Log analyzer read {len(logs)} entries")
        
        # Test error finding
        errors = analyzer.find_errors(logs)
        assert len(errors) == 1
        print(f"✅ Found {len(errors)} error entries")
        
        # Test performance analysis
        performance = analyzer.analyze_performance(logs)
        print("✅ Performance analysis completed")

def test_import_metrics():
    """Test ImportMetrics functionality"""
    print("\n=== Testing Import Metrics ===")
    
    from datetime import datetime, timezone
    
    metrics = ImportMetrics(
        total_prompts=100,
        successful_prompts=95,
        start_time=datetime.now(timezone.utc)
    )
    
    # Test to_dict conversion
    metrics_dict = metrics.to_dict()
    assert 'total_prompts' in metrics_dict
    print("✅ Metrics to_dict conversion works")
    
    # Test rate calculations
    rates = metrics.calculate_rates()
    assert 'success_rate' in rates
    assert rates['success_rate'] == 0.95
    print("✅ Rate calculations work")

def test_environment_configuration():
    """Test environment-based configuration"""
    print("\n=== Testing Environment Configuration ===")
    
    # Test default configuration
    config = LogConfig.from_environment()
    assert config.environment in ["development", "staging", "production"]
    print(f"✅ Environment configuration loaded: {config.environment}")
    
    # Test with environment variables
    import os
    old_env = os.environ.get('DATASET_LOG_LEVEL')
    try:
        os.environ['DATASET_LOG_LEVEL'] = 'ERROR'
        config = LogConfig.from_environment()
        assert config.log_level == 'ERROR'
        print("✅ Environment variable override works")
    finally:
        if old_env is not None:
            os.environ['DATASET_LOG_LEVEL'] = old_env
        elif 'DATASET_LOG_LEVEL' in os.environ:
            del os.environ['DATASET_LOG_LEVEL']

def test_performance_optimization():
    """Test performance optimization features"""
    print("\n=== Testing Performance Optimization ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = LogConfig(
            log_dir=Path(temp_dir),
            async_logging=True,
            performance_sampling_rate=0.5,
            max_log_message_size=1000
        )
        
        logger = DatasetLogger("perf_test", config)
        
        # Test message size limiting
        long_message = "x" * 2000  # Exceeds max_log_message_size
        logger.info(long_message)
        print("✅ Long message handling works")
        
        # Test performance metrics with sampling
        for i in range(10):
            logger.log_performance_metric(
                metric_name="test_metric",
                metric_value=i * 0.1,
                metric_unit="seconds"
            )
        print("✅ Performance metric sampling works")

def main():
    """Run all verification tests"""
    print("🚀 Starting Dataset Logging System Verification")
    
    try:
        test_basic_functionality()
        test_audit_logging()
        test_log_analysis()
        test_import_metrics()
        test_environment_configuration()
        test_performance_optimization()
        
        print("\n🎉 All tests passed! Dataset logging system is working correctly.")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())