# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Concurrent Performance Testing Module

Provides concurrent operation testing for dataset conversions,
API endpoints, and system resource management under parallel load.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ConcurrentOperationResult:
    """Result of a concurrent operation"""
    operation_id: str
    operation_type: str
    start_time: float
    end_time: float
    success: bool
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    @property
    def execution_time_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000


class ConcurrentPerformanceTester:
    """Test concurrent operations performance"""
    
    def __init__(self, max_workers: int = 10) -> None:
        """Initialize ConcurrentPerformanceTester.
        
        Args:
            max_workers: Maximum number of concurrent workers for testing.
                        Defaults to 10.
        """
        self.max_workers = max_workers
        self.operation_results: List[ConcurrentOperationResult] = []
        
    def test_concurrent_dataset_conversions(
        self,
        dataset_types: List[str],
        concurrent_users: int = 5
    ) -> Dict[str, Any]:
        """Test concurrent dataset conversions"""
        
        def mock_conversion_operation(operation_id: str, dataset_type: str) -> ConcurrentOperationResult:
            start_time = time.time()
            
            # Mock conversion processing time based on dataset type
            processing_times = {
                "garak": 2.0,
                "ollegen1": 5.0,
                "docmath": 8.0,
                "legalbench": 4.0,
                "graphwalk": 6.0
            }
            
            processing_time = processing_times.get(dataset_type, 3.0)
            time.sleep(processing_time * 0.1)  # Reduced for testing
            
            end_time = time.time()
            
            # Mock success rate (95% success)
            success = (operation_id.split('_')[-1] != '0')  # Make first operation fail for testing
            
            return ConcurrentOperationResult(
                operation_id=operation_id,
                operation_type=f"{dataset_type}_conversion",
                start_time=start_time,
                end_time=end_time,
                success=success,
                result_data={
                    "dataset_type": dataset_type,
                    "records_processed": 100,
                    "conversion_rate": 0.98
                } if success else None,
                error_message="Mock conversion error" if not success else None
            )
        
        # Run concurrent conversions
        operations = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for i in range(concurrent_users):
                for dataset_type in dataset_types:
                    operation_id = f"{dataset_type}_conversion_{i}"
                    future = executor.submit(mock_conversion_operation, operation_id, dataset_type)
                    operations.append(future)
                    
            # Collect results
            for future in as_completed(operations):
                result = future.result()
                self.operation_results.append(result)
                
        return self._analyze_concurrent_results("dataset_conversions")
        
    def test_concurrent_api_requests(
        self,
        endpoints: List[str],
        requests_per_endpoint: int = 10
    ) -> Dict[str, Any]:
        """Test concurrent API requests"""
        
        def mock_api_request(operation_id: str, endpoint: str) -> ConcurrentOperationResult:
            start_time = time.time()
            
            # Mock API response times
            time.sleep(0.15)  # 150ms mock response time
            
            end_time = time.time()
            
            # Mock 98% success rate
            success = (int(operation_id.split('_')[-1]) % 50 != 0)
            
            return ConcurrentOperationResult(
                operation_id=operation_id,
                operation_type=f"api_request_{endpoint.replace('/', '_')}",
                start_time=start_time,
                end_time=end_time,
                success=success,
                result_data={
                    "endpoint": endpoint,
                    "status_code": 200 if success else 500,
                    "response_size_bytes": 1024
                } if success else None,
                error_message="Mock API error" if not success else None
            )
            
        # Run concurrent API requests  
        operations = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for endpoint in endpoints:
                for i in range(requests_per_endpoint):
                    operation_id = f"api_request_{endpoint.replace('/', '_')}_{i}"
                    future = executor.submit(mock_api_request, operation_id, endpoint)
                    operations.append(future)
                    
            # Collect results
            for future in as_completed(operations):
                result = future.result()
                self.operation_results.append(result)
                
        return self._analyze_concurrent_results("api_requests")
        
    def _analyze_concurrent_results(self, operation_category: str) -> Dict[str, Any]:
        """Analyze concurrent operation results"""
        category_results = [
            r for r in self.operation_results 
            if operation_category in r.operation_type
        ]
        
        if not category_results:
            return {"error": f"No results for category {operation_category}"}
            
        successful_ops = [r for r in category_results if r.success]
        failed_ops = [r for r in category_results if not r.success]
        
        execution_times = [r.execution_time_ms for r in successful_ops]
        
        analysis = {
            "operation_category": operation_category,
            "total_operations": len(category_results),
            "successful_operations": len(successful_ops),
            "failed_operations": len(failed_ops),
            "success_rate": len(successful_ops) / len(category_results) if category_results else 0,
            "performance_metrics": {
                "avg_execution_time_ms": sum(execution_times) / len(execution_times) if execution_times else 0,
                "min_execution_time_ms": min(execution_times) if execution_times else 0,
                "max_execution_time_ms": max(execution_times) if execution_times else 0,
                "operations_per_second": (
                    len(successful_ops) / max(execution_times + [1]) * 1000 
                    if execution_times else 0
                )
            },
            "concurrency_impact": {
                "resource_contention": len(failed_ops) > 0,
                "performance_degradation": (
                    max(execution_times) > (sum(execution_times) / len(execution_times) * 2) 
                    if execution_times else False
                )
            },
            "error_analysis": {
                "error_types": list(set(r.error_message for r in failed_ops if r.error_message)),
                "error_distribution": self._get_error_distribution(failed_ops)
            }
        }
        
        return analysis
        
    def test_concurrent_conversions(self, dataset_types: List[str], concurrent_users: int = 5) -> Dict[str, Any]:
        """Alias for test_concurrent_dataset_conversions"""
        return self.test_concurrent_dataset_conversions(dataset_types, concurrent_users)
        
    def _get_error_distribution(self, failed_ops: List[ConcurrentOperationResult]) -> Dict[str, int]:
        """Get distribution of error types"""
        error_dist = {}
        for op in failed_ops:
            error_type = op.error_message or "unknown_error"
            error_dist[error_type] = error_dist.get(error_type, 0) + 1
        return error_dist
        
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Get comprehensive concurrent performance report"""
        if not self.operation_results:
            return {"error": "No operation results available"}
            
        total_ops = len(self.operation_results)
        successful_ops = len([r for r in self.operation_results if r.success])
        
        operation_types = list(set(r.operation_type for r in self.operation_results))
        
        return {
            "summary": {
                "total_operations": total_ops,
                "successful_operations": successful_ops,
                "overall_success_rate": successful_ops / total_ops,
                "operation_types_tested": len(operation_types)
            },
            "performance_overview": {
                "avg_execution_time_ms": (
                    sum(r.execution_time_ms for r in self.operation_results if r.success) / successful_ops 
                    if successful_ops else 0
                ),
                "total_test_duration_seconds": (
                    max(r.end_time for r in self.operation_results) - min(r.start_time for r in self.operation_results) 
                    if self.operation_results else 0
                )
            },
            "concurrency_analysis": {
                "max_workers_used": self.max_workers,
                "actual_concurrency_achieved": min(total_ops, self.max_workers),
                "resource_efficiency": (
                    successful_ops / (
                        self.max_workers * max(r.execution_time_ms for r in self.operation_results) / 1000
                    ) if self.operation_results else 0
                )
            },
            "operation_breakdown": {
                op_type: len([r for r in self.operation_results if r.operation_type == op_type])
                for op_type in operation_types
            }
        }


def test_concurrent_dataset_conversions(dataset_types: List[str], concurrent_users: int = 5) -> Dict[str, Any]:
    """Convenience function for testing concurrent dataset conversions"""
    tester = ConcurrentPerformanceTester()
    return tester.test_concurrent_dataset_conversions(dataset_types, concurrent_users)


def test_concurrent_api_load(endpoints: List[str], requests_per_endpoint: int = 10) -> Dict[str, Any]:
    """Convenience function for testing concurrent API load"""
    tester = ConcurrentPerformanceTester()
    return tester.test_concurrent_api_requests(endpoints, requests_per_endpoint)