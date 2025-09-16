# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Stress Testing Module

Provides comprehensive stress testing capabilities including memory exhaustion,
disk space management, network failure simulation, and system resilience testing.

Key Components:
- StressTester: Core stress testing orchestration
- MemoryExhaustionTester: Memory stress testing and exhaustion simulation
- DiskSpaceTester: Disk space exhaustion and management testing
- NetworkFailureTester: Network connectivity failure simulation
- ResilienceTester: System resilience and recovery testing

SECURITY: All stress tests are for defensive system validation only.
"""

import gc
import os
import random
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import requests


class StressTestType(Enum):
    """Types of stress tests available"""
    MEMORY_EXHAUSTION = "memory_exhaustion"
    DISK_SPACE_EXHAUSTION = "disk_space_exhaustion"
    NETWORK_FAILURE = "network_failure"
    CPU_OVERLOAD = "cpu_overload"
    CONCURRENT_REQUESTS = "concurrent_requests"
    RESOURCE_CONTENTION = "resource_contention"


class StressTestResult(Enum):
    """Stress test result classifications"""
    PASSED = "passed"
    FAILED = "failed"
    PARTIALLY_PASSED = "partially_passed"
    INCONCLUSIVE = "inconclusive"


@dataclass
class StressTestMetrics:
    """Stress test execution metrics"""
    test_id: str
    test_type: StressTestType
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    result: StressTestResult
    peak_memory_mb: float
    peak_cpu_percent: float
    disk_space_consumed_mb: float
    network_requests_made: int
    errors_encountered: List[str]
    warnings: List[str]
    recovery_time_seconds: float
    system_stability_score: float  # 0-100
    additional_metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def passed(self) -> bool:
        """Check if stress test passed"""
        return self.result == StressTestResult.PASSED
        
    @property
    def system_remained_stable(self) -> bool:
        """Check if system remained stable during stress test"""
        return self.system_stability_score >= 70.0


class MemoryExhaustionTester:
    """Memory stress testing and exhaustion simulation"""
    
    def __init__(self) -> None:
        """Initialize MemoryExhaustionTester.
        
        Sets up memory stress testing with empty lists for tracking
        allocated memory and allocation history.
        """
        self.allocated_memory: List[bytes] = []
        self.allocation_history: List[Dict[str, Any]] = []
        
    def simulate_memory_exhaustion(
        self,
        target_memory_mb: int,
        allocation_rate_mb_per_second: int = 10,
        test_recovery: bool = True
    ) -> StressTestMetrics:
        """
        Simulate memory exhaustion conditions
        
        Args:
            target_memory_mb: Target memory consumption in MB
            allocation_rate_mb_per_second: Rate of memory allocation
            test_recovery: Whether to test memory recovery mechanisms
            
        Returns:
            StressTestMetrics: Test execution results
        """
        test_id = f"memory_exhaustion_{int(time.time())}"
        start_time = datetime.now(timezone.utc)
        errors = []
        warnings = []
        
        # Get initial memory state
        # initial_memory = psutil.virtual_memory()  # Available if needed
        process = psutil.Process()
        initial_process_memory = process.memory_info().rss / 1024 / 1024
        
        peak_memory_mb = initial_process_memory
        peak_cpu_percent = 0
        recovery_start_time = None
        
        try:
            # Phase 1: Gradual memory allocation
            allocated_mb = 0
            allocation_chunk = 1024 * 1024  # 1MB chunks
            
            while allocated_mb < target_memory_mb:
                try:
                    # Allocate memory in chunks
                    chunk = bytearray(allocation_chunk)
                    # Fill with random data to prevent optimization
                    for i in range(0, len(chunk), 1024):
                        chunk[i] = random.randint(0, 255)
                        
                    self.allocated_memory.append(chunk)
                    allocated_mb += 1
                    
                    # Track metrics
                    current_memory = process.memory_info().rss / 1024 / 1024
                    current_cpu = process.cpu_percent(interval=0.1)
                    
                    peak_memory_mb = max(peak_memory_mb, current_memory)
                    peak_cpu_percent = max(peak_cpu_percent, current_cpu)
                    
                    self.allocation_history.append({
                        "timestamp": time.time(),
                        "allocated_mb": allocated_mb,
                        "process_memory_mb": current_memory,
                        "system_memory_percent": psutil.virtual_memory().percent
                    })
                    
                    # Check for system stability
                    if psutil.virtual_memory().percent > 95:
                        warnings.append("System memory usage exceeded 95%")
                        break
                        
                    # Throttle allocation rate
                    time.sleep(1.0 / allocation_rate_mb_per_second)
                    
                except MemoryError as e:
                    errors.append(f"Memory allocation failed at {allocated_mb}MB: {str(e)}")
                    break
                except Exception as e:
                    errors.append(f"Unexpected error during allocation: {str(e)}")
                    break
                    
            # Phase 2: Test system behavior under memory pressure
            if not errors:
                try:
                    # Attempt basic operations under memory pressure
                    test_operations = [
                        self._test_file_operations,
                        self._test_network_request,
                        self._test_computation
                    ]
                    
                    for operation in test_operations:
                        try:
                            operation()
                        except Exception as e:
                            warnings.append(f"Operation failed under memory pressure: {str(e)}")
                            
                except Exception as e:
                    errors.append(f"System behavior test failed: {str(e)}")
                    
            # Phase 3: Recovery testing
            if test_recovery:
                recovery_start_time = time.time()
                
                try:
                    # Clear allocated memory
                    self.allocated_memory.clear()
                    gc.collect()
                    
                    # Wait for memory to be released
                    recovery_timeout = 30  # 30 seconds timeout
                    recovery_start = time.time()
                    
                    while (time.time() - recovery_start) < recovery_timeout:
                        current_memory = process.memory_info().rss / 1024 / 1024
                        if current_memory <= initial_process_memory * 1.1:  # Within 10% of initial
                            break
                        time.sleep(1)
                    else:
                        warnings.append("Memory recovery took longer than expected")
                        
                except Exception as e:
                    errors.append(f"Memory recovery failed: {str(e)}")
                    
        except Exception as e:
            errors.append(f"Critical error during memory exhaustion test: {str(e)}")
            
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Calculate recovery time
        recovery_time = 0
        if recovery_start_time:
            recovery_time = time.time() - recovery_start_time
            
        # Determine test result
        if not errors and len(warnings) == 0:
            result = StressTestResult.PASSED
            stability_score = 100.0
        elif not errors and len(warnings) <= 2:
            result = StressTestResult.PARTIALLY_PASSED
            stability_score = 75.0
        elif errors:
            result = StressTestResult.FAILED
            stability_score = 30.0
        else:
            result = StressTestResult.INCONCLUSIVE
            stability_score = 50.0
            
        return StressTestMetrics(
            test_id=test_id,
            test_type=StressTestType.MEMORY_EXHAUSTION,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            result=result,
            peak_memory_mb=peak_memory_mb,
            peak_cpu_percent=peak_cpu_percent,
            disk_space_consumed_mb=0,
            network_requests_made=1,  # Network test request
            errors_encountered=errors,
            warnings=warnings,
            recovery_time_seconds=recovery_time,
            system_stability_score=stability_score,
            additional_metrics={
                "allocated_memory_mb": len(self.allocated_memory),
                "allocation_history_entries": len(self.allocation_history),
                "target_memory_mb": target_memory_mb,
                "allocation_rate_mb_per_second": allocation_rate_mb_per_second
            }
        )
        
    def _test_file_operations(self) -> None:
        """Test file operations under memory pressure"""
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            tmp.write(b"test data under memory pressure")
            tmp.flush()
            
    def _test_network_request(self) -> None:
        """Test network requests under memory pressure"""
        try:
            requests.get("http://localhost:9080/api/v1/health", timeout=5)
        except Exception:
            pass  # Network issues expected under stress
            
    def _test_computation(self) -> int:
        """Test computational operations under memory pressure"""
        # Simple computation that should work even under memory pressure
        result = sum(range(1000))
        return result


class DiskSpaceTester:
    """Disk space exhaustion and management testing"""
    
    def __init__(self) -> None:
        """Initialize DiskSpaceTester.
        
        Sets up disk space testing with an empty list for tracking
        temporary files created during testing.
        """
        self.temp_files: List[Path] = []
        
    def simulate_disk_exhaustion(
        self,
        target_disk_usage_mb: int,
        test_directory: Optional[Path] = None,
        test_cleanup: bool = True
    ) -> StressTestMetrics:
        """
        Simulate disk space exhaustion conditions
        
        Args:
            target_disk_usage_mb: Target disk space to consume
            test_directory: Directory to use for disk space test
            test_cleanup: Whether to test cleanup mechanisms
            
        Returns:
            StressTestMetrics: Test execution results
        """
        test_id = f"disk_exhaustion_{int(time.time())}"
        start_time = datetime.now(timezone.utc)
        errors = []
        warnings = []
        
        # Setup test directory
        if test_directory is None:
            test_directory = Path(tempfile.mkdtemp(prefix="disk_stress_test_"))
        else:
            test_directory.mkdir(exist_ok=True)
            
        # Get initial disk usage
        initial_usage = shutil.disk_usage(test_directory)
        initial_free_gb = initial_usage.free / (1024 ** 3)
        
        disk_consumed_mb = 0
        peak_cpu_percent = 0
        recovery_start_time = None
        
        try:
            # Phase 1: Fill disk space with test files
            file_counter = 0
            file_size_mb = 10  # 10MB per file
            
            while disk_consumed_mb < target_disk_usage_mb:
                try:
                    file_path = test_directory / f"stress_test_file_{file_counter}.dat"
                    
                    # Create file with random data
                    with open(file_path, 'wb') as f:
                        # Write in chunks to avoid memory issues
                        chunk_size = 1024 * 1024  # 1MB chunks
                        for _ in range(file_size_mb):
                            chunk = os.urandom(chunk_size)
                            f.write(chunk)
                            
                    self.temp_files.append(file_path)
                    disk_consumed_mb += file_size_mb
                    file_counter += 1
                    
                    # Check available disk space
                    current_usage = shutil.disk_usage(test_directory)
                    current_free_gb = current_usage.free / (1024 ** 3)
                    
                    if current_free_gb < 1:  # Less than 1GB free
                        warnings.append("Disk space critically low (<1GB free)")
                        break
                        
                    # Monitor CPU usage
                    peak_cpu_percent = max(peak_cpu_percent, psutil.cpu_percent(interval=0.1))
                    
                    # Small delay to prevent overwhelming the system
                    time.sleep(0.1)
                    
                except OSError as e:
                    if "No space left on device" in str(e):
                        warnings.append("Disk space exhausted - target reached")
                        break
                    else:
                        errors.append(f"Disk write error: {str(e)}")
                        break
                except Exception as e:
                    errors.append(f"Unexpected error during disk fill: {str(e)}")
                    break
                    
            # Phase 2: Test system behavior with low disk space
            if not errors:
                try:
                    # Test logging and temporary file operations
                    self._test_low_disk_operations(test_directory)
                    
                except Exception as e:
                    warnings.append(f"Low disk operations test failed: {str(e)}")
                    
            # Phase 3: Cleanup and recovery testing
            if test_cleanup:
                recovery_start_time = time.time()
                
                try:
                    # Remove test files
                    for file_path in self.temp_files:
                        try:
                            file_path.unlink()
                        except FileNotFoundError:
                            pass  # Already deleted
                        except Exception as e:
                            warnings.append(f"File cleanup warning: {str(e)}")
                            
                    # Remove test directory
                    try:
                        test_directory.rmdir()
                    except OSError:
                        # Directory not empty - try harder
                        shutil.rmtree(test_directory, ignore_errors=True)
                        
                except Exception as e:
                    errors.append(f"Cleanup failed: {str(e)}")
                    
        except Exception as e:
            errors.append(f"Critical error during disk exhaustion test: {str(e)}")
            
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Calculate recovery time
        recovery_time = 0
        if recovery_start_time:
            recovery_time = time.time() - recovery_start_time
            
        # Determine test result
        if not errors and len(warnings) <= 1:
            result = StressTestResult.PASSED
            stability_score = 90.0
        elif not errors and len(warnings) <= 3:
            result = StressTestResult.PARTIALLY_PASSED
            stability_score = 70.0
        elif errors:
            result = StressTestResult.FAILED
            stability_score = 40.0
        else:
            result = StressTestResult.INCONCLUSIVE
            stability_score = 50.0
            
        return StressTestMetrics(
            test_id=test_id,
            test_type=StressTestType.DISK_SPACE_EXHAUSTION,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            result=result,
            peak_memory_mb=psutil.Process().memory_info().rss / 1024 / 1024,
            peak_cpu_percent=peak_cpu_percent,
            disk_space_consumed_mb=disk_consumed_mb,
            network_requests_made=0,
            errors_encountered=errors,
            warnings=warnings,
            recovery_time_seconds=recovery_time,
            system_stability_score=stability_score,
            additional_metrics={
                "files_created": len(self.temp_files),
                "target_disk_usage_mb": target_disk_usage_mb,
                "initial_free_gb": initial_free_gb,
                "test_directory": str(test_directory)
            }
        )
        
    def _test_low_disk_operations(self, test_directory: Path) -> None:
        """Test operations under low disk space conditions"""
        # Test small file creation
        test_file = test_directory / "low_disk_test.txt"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("Testing operations under low disk space")
            
        # Test file reading
        with open(test_file, 'r', encoding='utf-8') as f:
            _ = f.read()  # Read file content for testing
            
        # Cleanup test file
        test_file.unlink()


class NetworkFailureTester:
    """Network connectivity failure simulation and testing"""
    
    def __init__(self, base_url: str = "http://localhost:9080") -> None:
        """Initialize NetworkFailureTester.
        
        Args:
            base_url: Base URL for network connectivity testing.
                     Defaults to 'http://localhost:9080'.
        """
        self.base_url = base_url
        self.network_test_results: List[Dict[str, Any]] = []
        
    def simulate_network_failure(
        self,
        failure_scenarios: List[str],
        test_duration_seconds: int = 60,
        recovery_test: bool = True
    ) -> StressTestMetrics:
        """
        Simulate network failure conditions and test system resilience
        
        Args:
            failure_scenarios: List of failure types to simulate
            test_duration_seconds: Duration of network failure simulation
            recovery_test: Whether to test recovery mechanisms
            
        Returns:
            StressTestMetrics: Test execution results
        """
        test_id = f"network_failure_{int(time.time())}"
        start_time = datetime.now(timezone.utc)
        errors = []
        warnings = []
        
        network_requests_made = 0
        recovery_start_time = None
        
        available_scenarios = [
            "connection_timeout",
            "dns_resolution_failure",
            "http_500_errors",
            "partial_response_corruption",
            "slow_response_times"
        ]
        
        # Validate scenarios
        valid_scenarios = [s for s in failure_scenarios if s in available_scenarios]
        if len(valid_scenarios) != len(failure_scenarios):
            warnings.append("Some failure scenarios were not recognized")
            
        try:
            # Phase 1: Test normal network operations
            baseline_response_time = self._test_network_baseline()
            network_requests_made += 1
            
            # Phase 2: Simulate each failure scenario
            for scenario in valid_scenarios:
                try:
                    scenario_results = self._simulate_scenario(scenario, test_duration_seconds // len(valid_scenarios))
                    network_requests_made += scenario_results.get("requests_made", 0)
                    
                    if scenario_results.get("errors"):
                        warnings.extend(scenario_results["errors"])
                        
                except Exception as e:
                    errors.append(f"Scenario {scenario} failed: {str(e)}")
                    
            # Phase 3: Test system recovery
            if recovery_test:
                recovery_start_time = time.time()
                
                try:
                    # Test gradual recovery
                    recovery_attempts = 5
                    successful_recoveries = 0
                    
                    for attempt in range(recovery_attempts):
                        try:
                            response = requests.get(f"{self.base_url}/api/v1/health", timeout=10)
                            if response.status_code == 200:
                                successful_recoveries += 1
                            network_requests_made += 1
                            
                        except Exception as e:
                            warnings.append(f"Recovery attempt {attempt + 1} failed: {str(e)}")
                            
                        time.sleep(2)  # Wait between attempts
                        
                    if successful_recoveries < recovery_attempts // 2:
                        warnings.append("Poor network recovery performance")
                        
                except Exception as e:
                    errors.append(f"Network recovery test failed: {str(e)}")
                    
        except Exception as e:
            errors.append(f"Critical error during network failure test: {str(e)}")
            
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Calculate recovery time
        recovery_time = 0
        if recovery_start_time:
            recovery_time = time.time() - recovery_start_time
            
        # Determine test result
        if not errors and len(warnings) <= 2:
            result = StressTestResult.PASSED
            stability_score = 85.0
        elif not errors and len(warnings) <= 5:
            result = StressTestResult.PARTIALLY_PASSED
            stability_score = 65.0
        elif len(errors) <= 2:
            result = StressTestResult.PARTIALLY_PASSED
            stability_score = 45.0
        else:
            result = StressTestResult.FAILED
            stability_score = 25.0
            
        return StressTestMetrics(
            test_id=test_id,
            test_type=StressTestType.NETWORK_FAILURE,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            result=result,
            peak_memory_mb=psutil.Process().memory_info().rss / 1024 / 1024,
            peak_cpu_percent=psutil.cpu_percent(interval=1),
            disk_space_consumed_mb=0,
            network_requests_made=network_requests_made,
            errors_encountered=errors,
            warnings=warnings,
            recovery_time_seconds=recovery_time,
            system_stability_score=stability_score,
            additional_metrics={
                "scenarios_tested": valid_scenarios,
                "test_duration_seconds": test_duration_seconds,
                "baseline_response_time_ms": baseline_response_time,
                "network_test_results": len(self.network_test_results)
            }
        )
        
    def _test_network_baseline(self) -> float:
        """Test baseline network performance"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/v1/health", timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            self.network_test_results.append({
                "type": "baseline",
                "response_time_ms": response_time,
                "status_code": response.status_code,
                "success": response.status_code == 200
            })
            
            return response_time
            
        except Exception as e:
            self.network_test_results.append({
                "type": "baseline",
                "response_time_ms": 30000,
                "status_code": 0,
                "success": False,
                "error": str(e)
            })
            return 30000  # Assume poor baseline
            
    def _simulate_scenario(self, scenario: str, duration_seconds: int) -> Dict[str, Any]:
        """Simulate specific network failure scenario"""
        results = {
            "scenario": scenario,
            "requests_made": 0,
            "errors": [],
            "warnings": []
        }
        
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time:
            try:
                if scenario == "connection_timeout":
                    # Simulate timeout by using very short timeout
                    requests.get(f"{self.base_url}/api/v1/health", timeout=0.001)
                elif scenario == "http_500_errors":
                    # Try to trigger server errors
                    requests.post(f"{self.base_url}/api/v1/invalid_endpoint", timeout=10)
                elif scenario == "slow_response_times":
                    # Simulate slow responses by making multiple rapid requests
                    requests.get(f"{self.base_url}/api/v1/health", timeout=30)
                else:
                    # Generic network request for other scenarios
                    requests.get(f"{self.base_url}/api/v1/health", timeout=10)
                    
                results["requests_made"] += 1
                time.sleep(1)  # Delay between requests
                
            except requests.exceptions.Timeout:
                results["warnings"].append(f"Timeout in scenario {scenario}")
            except requests.exceptions.ConnectionError:
                results["warnings"].append(f"Connection error in scenario {scenario}")
            except Exception as e:
                results["errors"].append(f"Error in scenario {scenario}: {str(e)}")
                
        return results


class StressTester:
    """
    Main stress testing orchestration system
    
    Coordinates different types of stress tests and provides comprehensive
    system resilience validation capabilities.
    """
    
    def __init__(self, base_url: str = "http://localhost:9080") -> None:
        """Initialize StressTestSuite.
        
        Args:
            base_url: Base URL for stress testing endpoints.
                     Defaults to 'http://localhost:9080'.
        """
        self.base_url = base_url
        self.memory_tester = MemoryExhaustionTester()
        self.disk_tester = DiskSpaceTester()
        self.network_tester = NetworkFailureTester(base_url)
        self.test_results: List[StressTestMetrics] = []
        
    def run_comprehensive_stress_test(
        self,
        test_config: Dict[str, Any]
    ) -> Dict[str, StressTestMetrics]:
        """
        Run comprehensive stress testing suite
        
        Args:
            test_config: Configuration for stress tests
            
        Returns:
            Dict[str, StressTestMetrics]: Results from all stress tests
        """
        results = {}
        
        # Memory exhaustion test
        if test_config.get("test_memory_exhaustion", True):
            memory_config = test_config.get("memory_config", {
                "target_memory_mb": 100,
                "allocation_rate_mb_per_second": 10,
                "test_recovery": True
            })
            
            results["memory_exhaustion"] = self.memory_tester.simulate_memory_exhaustion(**memory_config)
            self.test_results.append(results["memory_exhaustion"])
            
        # Disk space exhaustion test
        if test_config.get("test_disk_exhaustion", True):
            disk_config = test_config.get("disk_config", {
                "target_disk_usage_mb": 50,
                "test_cleanup": True
            })
            
            results["disk_exhaustion"] = self.disk_tester.simulate_disk_exhaustion(**disk_config)
            self.test_results.append(results["disk_exhaustion"])
            
        # Network failure test
        if test_config.get("test_network_failure", True):
            network_config = test_config.get("network_config", {
                "failure_scenarios": ["connection_timeout", "http_500_errors"],
                "test_duration_seconds": 30,
                "recovery_test": True
            })
            
            results["network_failure"] = self.network_tester.simulate_network_failure(**network_config)
            self.test_results.append(results["network_failure"])
            
        return results
        
    def get_stress_test_summary(self) -> Dict[str, Any]:
        """Get comprehensive stress test summary"""
        if not self.test_results:
            return {"message": "No stress tests completed"}
            
        passed_tests = sum(1 for result in self.test_results if result.passed)
        total_tests = len(self.test_results)
        
        avg_stability_score = sum(result.system_stability_score for result in self.test_results) / total_tests
        total_errors = sum(len(result.errors_encountered) for result in self.test_results)
        total_warnings = sum(len(result.warnings) for result in self.test_results)
        
        return {
            "total_stress_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate_percent": (passed_tests / total_tests) * 100,
            "average_system_stability_score": avg_stability_score,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "test_types_completed": list(set(result.test_type.value for result in self.test_results)),
            "overall_system_resilience": "high" if avg_stability_score >= 80 else
                                        "medium" if avg_stability_score >= 60 else "low"
        }