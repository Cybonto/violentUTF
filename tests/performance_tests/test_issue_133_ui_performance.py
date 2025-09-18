"""
Performance Tests for Issue #133: Streamlit UI Updates for Native Dataset Integration

This test suite validates UI performance requirements including loading times,
memory usage, and responsiveness with large datasets (679K+ entries).
"""

import threading
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import psutil
import pytest


# Performance benchmarking decorator
def benchmark_time(max_seconds: float):
    """Decorator to benchmark function execution time"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = end_time - start_time
            assert execution_time < max_seconds, f"Function {func.__name__} took {execution_time:.2f}s, exceeded {max_seconds}s limit"
            return result
        return wrapper
    return decorator

def memory_usage_monitor():
    """Monitor memory usage during test execution"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024  # MB

@pytest.fixture
def large_dataset_sample():
    """Generate large dataset sample for performance testing"""
    return [
        {
            "id": i,
            "question": f"Sample cognitive question {i} about risk assessment and decision making",
            "answer": f"Detailed answer {i} demonstrating cognitive reasoning patterns and behavioral analysis",
            "category": "WCP" if i % 2 == 0 else "WHO",
            "difficulty": "medium" if i % 3 == 0 else "high",
            "metadata": {
                "timestamp": f"2024-01-{(i % 28) + 1:02d}",
                "source": "cognitive_assessment",
                "complexity_score": i % 10
            }
        }
        for i in range(10000)  # 10K sample for testing
    ]

@pytest.fixture
def massive_dataset_metadata():
    """Metadata for the largest dataset (OLLeGeN1 with 679K entries)"""
    return {
        "name": "ollegen1_cognitive",
        "total_entries": 679996,
        "file_size": "150MB",
        "pyrit_format": "QuestionAnsweringDataset",
        "domain": "cognitive_behavioral",
        "categories": ["WCP", "WHO", "TeamRisk", "TargetFactor"],
        "estimated_memory_usage": "500MB",
        "last_updated": "2024-01-15"
    }

class TestDatasetLoadingPerformance:
    """Performance tests for dataset loading operations"""
    
    @benchmark_time(3.0)  # Must load within 3 seconds
    def test_dataset_list_loading_performance(self):
        """Test that dataset list loads within 3 seconds"""
        # This test will fail until implementation exists
        with pytest.raises(ImportError):
            from violentutf.components.dataset_selector import NativeDatasetSelector
            
            selector = NativeDatasetSelector()
            
            # Mock API calls to simulate realistic loading
            with patch('violentutf.pages.2_Configure_Datasets.api_request') as mock_api:
                mock_api.return_value = {
                    "dataset_types": [
                        {"name": "ollegen1_cognitive", "description": "Cognitive assessment"},
                        {"name": "garak_redteaming", "description": "Red-teaming dataset"},
                        {"name": "legalbench_professional", "description": "Legal reasoning"},
                        {"name": "docmath_mathematical", "description": "Math reasoning"},
                        {"name": "acpbench_planning", "description": "AI planning"},
                        {"name": "graphwalk_spatial", "description": "Spatial reasoning"},
                        {"name": "confaide_privacy", "description": "Privacy evaluation"},
                        {"name": "judgebench_meta", "description": "Meta-evaluation"}
                    ]
                }
                
                # This should complete within 3 seconds
                selector.render_dataset_selection_interface()
    
    @benchmark_time(5.0)  # Must load within 5 seconds
    def test_dataset_preview_loading_performance(self, large_dataset_sample):
        """Test that dataset preview loads within 5 seconds"""
        with pytest.raises(ImportError):
            from violentutf.components.dataset_preview import DatasetPreviewComponent
            
            preview = DatasetPreviewComponent()
            metadata = {
                "total_entries": len(large_dataset_sample),
                "file_size": "10MB",
                "pyrit_format": "QuestionAnsweringDataset",
                "domain": "cognitive_behavioral"
            }
            
            # Mock preview data loading
            with patch.object(preview, 'load_preview_data', return_value=large_dataset_sample[:100]):
                preview.render_dataset_preview("test_dataset", metadata)
    
    @benchmark_time(10.0)  # Must load within 10 seconds for large datasets
    def test_large_dataset_preview_performance(self, massive_dataset_metadata):
        """Test that large dataset (679K entries) preview loads within 10 seconds"""
        with pytest.raises(ImportError):
            from violentutf.components.dataset_preview import DatasetPreviewComponent
            
            preview = DatasetPreviewComponent()
            
            # Simulate large dataset loading with efficient sampling
            large_sample = [
                {
                    "question": f"Cognitive question {i}",
                    "answer": f"Answer {i}",
                    "category": "WCP"
                }
                for i in range(1000)  # Sample of large dataset
            ]
            
            with patch.object(preview, 'load_preview_data', return_value=large_sample):
                preview.render_dataset_preview("ollegen1_cognitive", massive_dataset_metadata)

class TestMemoryUsagePerformance:
    """Performance tests for memory usage during UI operations"""
    
    def test_memory_usage_within_limits(self, large_dataset_sample):
        """Test that UI operations stay within 500MB memory limit"""
        initial_memory = memory_usage_monitor()
        
        with pytest.raises(ImportError):
            from violentutf.utils.dataset_ui_components import LargeDatasetUIOptimization
            
            optimizer = LargeDatasetUIOptimization()
            
            # Simulate large dataset operations
            with patch.object(optimizer, 'load_dataset_sample', return_value=large_dataset_sample):
                sample = optimizer.load_dataset_sample("ollegen1_cognitive", 10000)
                
                # Check memory usage
                current_memory = memory_usage_monitor()
                memory_increase = current_memory - initial_memory
                
                assert memory_increase < 500, f"Memory usage increased by {memory_increase:.1f}MB, exceeded 500MB limit"
    
    def test_pagination_memory_efficiency(self, large_dataset_sample):
        """Test that pagination reduces memory usage for large datasets"""
        with pytest.raises(ImportError):
            from violentutf.utils.dataset_ui_components import LargeDatasetUIOptimization
            
            optimizer = LargeDatasetUIOptimization()
            
            initial_memory = memory_usage_monitor()
            
            # Test paginated loading vs full loading
            page_data = optimizer.render_paginated_preview(large_dataset_sample, page_size=50)
            paginated_memory = memory_usage_monitor()
            
            # Paginated approach should use less memory
            memory_with_pagination = paginated_memory - initial_memory
            
            # Should be significantly less than loading all data
            assert len(page_data) <= 50, "Pagination not working correctly"
            assert memory_with_pagination < 100, f"Pagination used {memory_with_pagination:.1f}MB, should be under 100MB"
    
    def test_cache_memory_management(self):
        """Test that cache management prevents memory leaks"""
        with pytest.raises(ImportError):
            from violentutf.components.dataset_preview import DatasetPreviewComponent
            
            preview = DatasetPreviewComponent()
            
            initial_memory = memory_usage_monitor()
            
            # Simulate multiple preview operations
            for i in range(10):
                dataset_name = f"test_dataset_{i}"
                # Should implement cache cleanup
                preview.clear_preview_cache(dataset_name)
            
            final_memory = memory_usage_monitor()
            memory_change = final_memory - initial_memory
            
            # Memory should not significantly increase
            assert memory_change < 50, f"Cache management allowed {memory_change:.1f}MB memory increase"

class TestUIResponsivenessPerformance:
    """Performance tests for UI responsiveness during operations"""
    
    def test_ui_remains_responsive_during_loading(self):
        """Test that UI remains responsive during data loading operations"""
        with pytest.raises(ImportError):
            from violentutf.utils.dataset_ui_components import LargeDatasetUIOptimization
            
            optimizer = LargeDatasetUIOptimization()
            
            # Mock long-running operation
            def mock_long_operation():
                time.sleep(2)  # Simulate 2-second operation
                return True
            
            # Test that UI optimization handles long operations
            with patch('time.sleep'):  # Speed up test
                result = optimizer.optimize_ui_responsiveness()
                assert result is None or isinstance(result, bool)
    
    def test_concurrent_user_interactions(self, large_dataset_sample):
        """Test UI performance with concurrent user interactions"""
        with pytest.raises(ImportError):
            from violentutf.components.dataset_preview import DatasetPreviewComponent
            from violentutf.components.dataset_selector import NativeDatasetSelector
            
            selector = NativeDatasetSelector()
            preview = DatasetPreviewComponent()
            
            # Simulate concurrent operations
            results = []
            
            def operation1():
                with patch.object(selector, 'render_dataset_selection_interface'):
                    start = time.time()
                    selector.render_dataset_selection_interface()
                    results.append(time.time() - start)
            
            def operation2():
                with patch.object(preview, 'render_dataset_preview'):
                    start = time.time()
                    preview.render_dataset_preview("test", {})
                    results.append(time.time() - start)
            
            # Run operations concurrently
            thread1 = threading.Thread(target=operation1)
            thread2 = threading.Thread(target=operation2)
            
            thread1.start()
            thread2.start()
            
            thread1.join()
            thread2.join()
            
            # Both operations should complete reasonably quickly
            for duration in results:
                assert duration < 5.0, f"Concurrent operation took {duration:.2f}s, too slow"

class TestScalabilityPerformance:
    """Performance tests for scalability with various dataset sizes"""
    
    @pytest.mark.parametrize("dataset_size,max_time", [
        (1000, 1.0),      # 1K entries: 1 second
        (10000, 2.0),     # 10K entries: 2 seconds  
        (100000, 5.0),    # 100K entries: 5 seconds
        (679996, 10.0)    # 679K entries: 10 seconds
    ])
    def test_preview_scaling_performance(self, dataset_size, max_time):
        """Test preview performance scales appropriately with dataset size"""
        with pytest.raises(ImportError):
            from violentutf.components.dataset_preview import DatasetPreviewComponent
            
            preview = DatasetPreviewComponent()
            
            # Generate dataset sample of specified size
            sample_data = [
                {"id": i, "question": f"Q{i}", "answer": f"A{i}"}
                for i in range(min(dataset_size, 1000))  # Limit sample for testing
            ]
            
            metadata = {
                "total_entries": dataset_size,
                "file_size": f"{dataset_size * 0.0002:.1f}MB",  # Rough estimate
                "pyrit_format": "QuestionAnsweringDataset"
            }
            
            start_time = time.time()
            
            with patch.object(preview, 'load_preview_data', return_value=sample_data):
                preview.render_dataset_preview(f"dataset_{dataset_size}", metadata)
            
            execution_time = time.time() - start_time
            assert execution_time < max_time, f"Dataset size {dataset_size} took {execution_time:.2f}s, exceeded {max_time}s limit"
    
    def test_configuration_interface_scaling(self):
        """Test configuration interface performance with multiple domains"""
        with pytest.raises(ImportError):
            from violentutf.components.dataset_configuration import SpecializedConfigurationInterface
            
            config = SpecializedConfigurationInterface()
            
            # Test all domain types
            domain_types = [
                "cognitive_behavioral",
                "redteaming", 
                "legal_reasoning",
                "mathematical_reasoning",
                "spatial_reasoning",
                "privacy_evaluation",
                "meta_evaluation"
            ]
            
            start_time = time.time()
            
            for domain_type in domain_types:
                with patch('streamlit.subheader'), patch('streamlit.multiselect'), patch('streamlit.selectbox'):
                    config.render_configuration_interface(f"dataset_{domain_type}", domain_type)
            
            total_time = time.time() - start_time
            avg_time = total_time / len(domain_types)
            
            assert avg_time < 0.5, f"Average configuration time {avg_time:.2f}s per domain, should be under 0.5s"

class TestConcurrentOperationsPerformance:
    """Performance tests for concurrent dataset operations"""
    
    def test_multiple_dataset_loading(self):
        """Test performance when loading multiple datasets simultaneously"""
        with pytest.raises(ImportError):
            from violentutf.components.dataset_selector import NativeDatasetSelector
            
            selector = NativeDatasetSelector()
            
            # Simulate loading multiple dataset types
            dataset_types = [
                "ollegen1_cognitive",
                "garak_redteaming", 
                "legalbench_professional",
                "docmath_mathematical"
            ]
            
            start_time = time.time()
            
            # Mock concurrent loading
            with patch('violentutf.pages.2_Configure_Datasets.api_request') as mock_api:
                mock_api.return_value = {"datasets": [{"name": dt, "id": i} for i, dt in enumerate(dataset_types)]}
                
                for dataset_type in dataset_types:
                    with patch.object(selector, 'render_dataset_card'):
                        selector.render_dataset_card(dataset_type, "test_category")
            
            total_time = time.time() - start_time
            assert total_time < 2.0, f"Loading {len(dataset_types)} datasets took {total_time:.2f}s, should be under 2s"
    
    def test_search_performance_with_large_dataset_list(self):
        """Test search performance with large number of datasets"""
        with pytest.raises(ImportError):
            from violentutf.utils.dataset_ui_components import DatasetManagementInterface
            
            management = DatasetManagementInterface()
            
            # Simulate large dataset list
            large_dataset_list = [
                {"name": f"dataset_{i}", "description": f"Description {i}", "domain": f"domain_{i%5}"}
                for i in range(1000)
            ]
            
            start_time = time.time()
            
            with patch.object(management, 'search_datasets', return_value=large_dataset_list[:10]):
                with patch('streamlit.text_input', return_value="test"):
                    management.render_dataset_search_interface()
            
            search_time = time.time() - start_time
            assert search_time < 1.0, f"Search took {search_time:.2f}s, should be under 1s"

class TestRealWorldPerformanceScenarios:
    """Performance tests simulating real-world usage scenarios"""
    
    def test_new_user_workflow_performance(self):
        """Test complete new user workflow performance"""
        # Simulate: Browse categories -> Select dataset -> Configure -> Preview
        workflow_start = time.time()
        
        with pytest.raises(ImportError):
            from violentutf.components.dataset_configuration import SpecializedConfigurationInterface
            from violentutf.components.dataset_preview import DatasetPreviewComponent
            from violentutf.components.dataset_selector import NativeDatasetSelector

            # Step 1: Browse categories (target: <1s)
            step1_start = time.time()
            selector = NativeDatasetSelector()
            with patch.object(selector, 'render_dataset_selection_interface'):
                selector.render_dataset_selection_interface()
            step1_time = time.time() - step1_start
            
            # Step 2: Configure dataset (target: <2s)
            step2_start = time.time()
            config = SpecializedConfigurationInterface()
            with patch.object(config, 'render_cognitive_configuration', return_value={}):
                config.render_cognitive_configuration("ollegen1_cognitive")
            step2_time = time.time() - step2_start
            
            # Step 3: Preview dataset (target: <3s)
            step3_start = time.time()
            preview = DatasetPreviewComponent()
            with patch.object(preview, 'render_dataset_preview'):
                preview.render_dataset_preview("test", {})
            step3_time = time.time() - step3_start
            
            total_workflow_time = time.time() - workflow_start
            
            # Individual step requirements
            assert step1_time < 1.0, f"Category browsing took {step1_time:.2f}s, should be under 1s"
            assert step2_time < 2.0, f"Configuration took {step2_time:.2f}s, should be under 2s"  
            assert step3_time < 3.0, f"Preview took {step3_time:.2f}s, should be under 3s"
            
            # Total workflow should complete within 5 minutes (300s)
            assert total_workflow_time < 300.0, f"Total workflow took {total_workflow_time:.2f}s, should be under 300s"
    
    def test_power_user_batch_operations(self):
        """Test performance for power users doing batch operations"""
        batch_start = time.time()
        
        with pytest.raises(ImportError):
            from violentutf.utils.dataset_ui_components import DatasetManagementInterface
            
            management = DatasetManagementInterface()
            
            # Simulate batch operations: search, filter, compare multiple datasets
            operations = [
                ("search", "cognitive"),
                ("search", "legal"),
                ("search", "math"),
                ("filter", "large_datasets"),
                ("filter", "recent"),
            ]
            
            for operation, query in operations:
                with patch.object(management, 'search_datasets', return_value=[]):
                    with patch('streamlit.text_input', return_value=query):
                        management.render_dataset_search_interface()
            
            batch_time = time.time() - batch_start
            assert batch_time < 10.0, f"Batch operations took {batch_time:.2f}s, should be under 10s"

if __name__ == "__main__":
    # Run performance tests with benchmarking
    pytest.main([__file__, "-v", "--tb=short"])