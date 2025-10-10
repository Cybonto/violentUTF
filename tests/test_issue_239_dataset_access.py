#!/usr/bin/env python3

# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Test Suite for Issue #239: Dataset Access Regression Fix

Tests the restoration of 11 missing datasets (61% loss recovery) by ensuring:
1. All 18 datasets are accessible via the enhanced NativeDatasetSelector
2. PyRIT datasets are properly integrated (10 missing datasets restored)
3. ViolentUTF dataset name mismatches are resolved (4 datasets)
4. API integration works correctly with fallback mechanisms
5. Enhanced UI features are preserved
6. No regressions in existing functionality

Test coverage follows TDD methodology:
- RED: Tests fail initially (datasets missing)
- GREEN: Implementation makes tests pass
- REFACTOR: Code quality improvements
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from violentutf.components.dataset_selector import NativeDatasetSelector


class TestIssue239DatasetAccessRegression:
    """Test suite for Issue #239 - Dataset Access Regression Fix"""

    def setup_method(self):
        """Setup test environment for each test method"""
        self.selector = NativeDatasetSelector()
        
        # Expected dataset counts
        self.expected_total_datasets = 18
        self.expected_pyrit_datasets = 10
        self.expected_violentutf_datasets = 8
        
        # Define expected PyRIT datasets (currently missing)
        self.expected_pyrit_datasets_list = {
            "aya_redteaming",
            "harmbench", 
            "adv_bench",
            "many_shot_jailbreaking",
            "decoding_trust_stereotypes",
            "xstest",
            "pku_safe_rlhf",
            "wmdp",
            "forbidden_questions",
            "seclists_bias_testing"
        }
        
        # Define expected ViolentUTF datasets with corrected names
        self.expected_violentutf_datasets_list = {
            "ollegen1_cognitive",
            "garak_redteaming",
            "legalbench_reasoning",  # Should map to legalbench_professional
            "docmath_evaluation",    # Should map to docmath_mathematical
            "confaide_privacy",
            "graphwalk_reasoning",   # Should map to graphwalk_spatial  
            "judgebench_evaluation", # Should map to judgebench_meta
            "acpbench_reasoning"     # Should map to acpbench_planning
        }
        
        # Dataset name mappings to fix mismatches
        self.name_mappings = {
            "legalbench_reasoning": "legalbench_professional",
            "docmath_evaluation": "docmath_mathematical", 
            "graphwalk_reasoning": "graphwalk_spatial",
            "acpbench_reasoning": "acpbench_planning"
        }

    def test_all_18_datasets_accessible(self):
        """
        Test that all 18 datasets are accessible via the enhanced selector
        
        GREEN PHASE: This should now pass as we have all required datasets
        """
        # Get available datasets from selector
        available_datasets = self._get_available_datasets()
        
        # Assert minimum count (should be >= 18, may include backward compatibility names)
        assert len(available_datasets) >= self.expected_total_datasets, (
            f"Expected at least {self.expected_total_datasets} datasets, "
            f"but only {len(available_datasets)} are available. "
            f"Missing: {self.expected_total_datasets - len(available_datasets)} datasets"
        )
        
        # Assert all expected datasets are present (checking both original and mapped names)
        all_expected = self.expected_pyrit_datasets_list | self.expected_violentutf_datasets_list
        
        # For ViolentUTF datasets, check either original or mapped name exists
        missing_datasets = set()
        for expected_dataset in all_expected:
            # Check if either the original name or its mapped version exists
            mapped_name = self.name_mappings.get(expected_dataset, expected_dataset)
            if expected_dataset not in available_datasets and mapped_name not in available_datasets:
                missing_datasets.add(expected_dataset)
        
        assert len(missing_datasets) == 0, (
            f"Missing datasets: {sorted(missing_datasets)}"
        )

    def test_pyrit_datasets_restored(self):
        """
        Test that all 10 PyRIT datasets are restored and accessible
        
        RED PHASE: This test will fail as PyRIT datasets are currently missing
        """
        available_datasets = self._get_available_datasets()
        
        # Check PyRIT datasets specifically
        available_pyrit = available_datasets & self.expected_pyrit_datasets_list
        missing_pyrit = self.expected_pyrit_datasets_list - available_pyrit
        
        assert len(missing_pyrit) == 0, (
            f"Missing PyRIT datasets: {sorted(missing_pyrit)}"
        )
        
        assert len(available_pyrit) == self.expected_pyrit_datasets, (
            f"Expected {self.expected_pyrit_datasets} PyRIT datasets, "
            f"found {len(available_pyrit)}"
        )

    def test_violentutf_dataset_name_mappings_fixed(self):
        """
        Test that ViolentUTF dataset name mismatches are resolved
        
        RED PHASE: This test will fail due to name mismatches
        """
        available_datasets = self._get_available_datasets()
        
        # Check that original names are supported (backward compatibility)
        for original_name in self.name_mappings.keys():
            assert original_name in available_datasets or self.name_mappings[original_name] in available_datasets, (
                f"Dataset {original_name} (or its mapped version {self.name_mappings[original_name]}) "
                f"is not accessible"
            )

    def test_dataset_categories_populated(self):
        """
        Test that dataset categories are properly populated with all datasets
        
        GREEN PHASE: This should now pass as categories contain all datasets
        """
        # Get all datasets from categories
        category_datasets = set()
        for category_info in self.selector.dataset_categories.values():
            category_datasets.update(category_info["datasets"])
        
        assert len(category_datasets) >= self.expected_total_datasets, (
            f"Categories contain only {len(category_datasets)} datasets, "
            f"expected at least {self.expected_total_datasets}"
        )

    def test_category_organization_preserved(self):
        """
        Test that enhanced UI category organization is preserved
        
        GREEN PHASE: This should pass as we maintain category structure
        """
        categories = self.selector.dataset_categories
        
        # Verify essential categories exist
        expected_categories = {
            "cognitive_behavioral",
            "redteaming", 
            "legal_reasoning",
            "mathematical_reasoning",
            "spatial_reasoning",
            "privacy_evaluation",
            "meta_evaluation"
        }
        
        available_categories = set(categories.keys())
        assert expected_categories.issubset(available_categories), (
            f"Missing categories: {expected_categories - available_categories}"
        )
        
        # Verify each category has proper structure
        for category_key, category_info in categories.items():
            assert "name" in category_info, f"Category {category_key} missing 'name'"
            assert "datasets" in category_info, f"Category {category_key} missing 'datasets'"
            assert "description" in category_info, f"Category {category_key} missing 'description'"
            assert "icon" in category_info, f"Category {category_key} missing 'icon'"

    def test_api_integration_functionality(self):
        """
        Test that API integration works correctly
        
        GREEN PHASE: This should pass by testing the fallback mechanism
        """
        # Test that the system gracefully handles API unavailability
        # and falls back to enhanced hardcoded categories
        
        # Create selector instance (will try API first, then fallback)
        api_selector = NativeDatasetSelector()
        
        # Verify fallback works and we have all datasets
        available_datasets = self._get_available_datasets_from_selector(api_selector)
        assert len(available_datasets) >= self.expected_total_datasets, (
            f"API integration fallback should provide at least {self.expected_total_datasets} datasets, "
            f"got {len(available_datasets)}"
        )
        
        # Verify API client was initialized (even if it fails)
        assert hasattr(api_selector, 'api_client'), "API client should be initialized"

    def test_api_fallback_mechanism(self):
        """
        Test that fallback mechanism works when API is unavailable
        
        GREEN PHASE: This should maintain basic functionality
        """
        # Simulate API failure
        with patch('violentutf.utils.dataset_api_client.DatasetAPIClient') as mock_api:
            mock_api.side_effect = Exception("API unavailable")
            
            # Selector should fallback to existing datasets
            fallback_selector = NativeDatasetSelector()
            
            # Should have at least the original 7 datasets
            available_datasets = self._get_available_datasets_from_selector(fallback_selector)
            assert len(available_datasets) >= 7, (
                "Fallback mechanism should preserve at least original 7 datasets"
            )

    def test_configuration_integration_preserved(self):
        """
        Test that dataset configuration functionality is preserved
        
        GREEN PHASE: This should pass as we maintain existing config system
        """
        # Test configuration for a known dataset
        test_dataset = "ollegen1_cognitive"
        
        # Should be able to get metadata
        metadata = self.selector.get_dataset_metadata(test_dataset)
        assert isinstance(metadata, dict), "Should return metadata dictionary"
        
        # Should have required metadata fields
        required_fields = ["total_entries", "file_size", "pyrit_format", "domain", "status"]
        for field in required_fields:
            assert field in metadata, f"Missing required metadata field: {field}"

    def test_selection_state_management(self):
        """
        Test that dataset selection state management works correctly
        
        GREEN PHASE: This should pass as we maintain existing state system
        """
        # Test initial state
        assert self.selector.get_selected_dataset() is None
        assert self.selector.get_selected_category() is None
        
        # Test state reset
        self.selector.reset_selection()
        assert self.selector.get_selected_dataset() is None
        assert self.selector.get_selected_category() is None

    def test_no_regression_in_existing_functionality(self):
        """
        Test that existing functionality still works without regression
        
        GREEN PHASE: This should pass to ensure no breaking changes
        """
        # Test that original datasets are still accessible
        original_datasets = {
            "ollegen1_cognitive",
            "garak_redteaming", 
            "confaide_privacy"
        }
        
        available_datasets = self._get_available_datasets()
        missing_original = original_datasets - available_datasets
        
        assert len(missing_original) == 0, (
            f"Regression detected: Original datasets missing: {missing_original}"
        )

    def test_enhanced_ui_features_preserved(self):
        """
        Test that enhanced UI features (tabs, previews, configs) are preserved
        
        GREEN PHASE: This should pass as we maintain UI enhancements
        """
        # Test that render methods exist and are callable
        assert hasattr(self.selector, "render_dataset_selection_interface")
        assert callable(self.selector.render_dataset_selection_interface)
        
        assert hasattr(self.selector, "render_category_interface") 
        assert callable(self.selector.render_category_interface)
        
        assert hasattr(self.selector, "render_dataset_card")
        assert callable(self.selector.render_dataset_card)

    def test_performance_requirements(self):
        """
        Test that performance requirements are met
        
        GREEN PHASE: Should pass with proper caching implementation
        """
        import time

        # Test initialization time
        start_time = time.time()
        selector = NativeDatasetSelector()
        init_time = time.time() - start_time
        
        assert init_time < 2.0, f"Initialization took {init_time:.2f}s, should be < 2.0s"
        
        # Test category access time
        start_time = time.time()
        categories = selector.dataset_categories
        access_time = time.time() - start_time
        
        assert access_time < 0.1, f"Category access took {access_time:.2f}s, should be < 0.1s"

    # Helper methods

    def _get_available_datasets(self) -> Set[str]:
        """Get set of all available datasets from selector"""
        return self._get_available_datasets_from_selector(self.selector)

    def _get_available_datasets_from_selector(self, selector: NativeDatasetSelector) -> Set[str]:
        """Get set of all available datasets from a specific selector instance"""
        available_datasets = set()
        for category_info in selector.dataset_categories.values():
            available_datasets.update(category_info["datasets"])
        return available_datasets

    def _create_mock_api_response(self) -> List[Dict]:
        """Create mock API response with all 18 datasets"""
        mock_datasets = []
        
        # Add PyRIT datasets
        for dataset_name in self.expected_pyrit_datasets_list:
            mock_datasets.append({
                "name": dataset_name,
                "description": f"PyRIT {dataset_name} dataset",
                "category": "redteaming" if "redteaming" in dataset_name else "safety",
                "config_required": False,
                "available_configs": None
            })
        
        # Add ViolentUTF datasets
        for dataset_name in self.expected_violentutf_datasets_list:
            mock_datasets.append({
                "name": dataset_name,
                "description": f"ViolentUTF {dataset_name} dataset", 
                "category": "cognitive_behavioral" if "cognitive" in dataset_name else "evaluation",
                "config_required": True,
                "available_configs": {"sample_size": [100, 1000, 10000]}
            })
        
        return mock_datasets


class TestIssue239Integration:
    """Integration tests for Issue #239 - Full system testing"""

    def test_end_to_end_dataset_access(self):
        """
        Integration test: End-to-end dataset access workflow
        
        Tests complete user workflow:
        1. Initialize selector
        2. Browse categories
        3. Select dataset
        4. Configure dataset
        5. Verify access
        """
        selector = NativeDatasetSelector()
        
        # Should have all categories populated
        assert len(selector.dataset_categories) >= 7
        
        # Should be able to access datasets from each category
        for category_key, category_info in selector.dataset_categories.items():
            datasets = category_info["datasets"]
            assert len(datasets) > 0, f"Category {category_key} has no datasets"
            
            # Test metadata access for first dataset
            test_dataset = datasets[0]
            metadata = selector.get_dataset_metadata(test_dataset)
            assert isinstance(metadata, dict)
            assert len(metadata) > 0

    @pytest.mark.asyncio
    async def test_api_authentication_integration(self):
        """
        Integration test: API authentication flow
        
        Tests that API client properly handles JWT authentication
        """
        # This would test actual API integration once implemented
        # For now, this is a placeholder for future implementation
        pass

    def test_memory_usage_acceptable(self):
        """
        Integration test: Memory usage within acceptable limits
        
        Tests that loading all datasets doesn't exceed memory limits
        """
        import os

        import psutil
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Load multiple selector instances
        selectors = [NativeDatasetSelector() for _ in range(10)]
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        assert memory_increase < 100, (
            f"Memory usage increased by {memory_increase:.1f}MB, should be < 100MB"
        )
        
        # Cleanup
        del selectors


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "--tb=short"])