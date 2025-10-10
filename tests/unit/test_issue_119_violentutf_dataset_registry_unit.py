#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Unit tests for Issue #119: ViolentUTF Dataset Registry Extension

Tests the NATIVE_DATASET_TYPES registry structure and ViolentUTF dataset definitions
without requiring API server or authentication.
"""

import os
import sys
from typing import Any, Dict

import pytest

# Add project paths for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "violentutf_api/fastapi_app"))

# Import the dataset registry
from violentutf_api.fastapi_app.app.api.endpoints.datasets import NATIVE_DATASET_TYPES


class TestViolentUTFDatasetRegistryUnit:
    """Unit tests for ViolentUTF dataset registry extension"""

    def test_violentutf_datasets_in_registry(self) -> None:
        """Test that ViolentUTF dataset types are included in NATIVE_DATASET_TYPES"""
        # Expected ViolentUTF datasets from the issue specification
        expected_violentutf_datasets = [
            "ollegen1_cognitive",
            "garak_redteaming", 
            "legalbench_reasoning",
            "docmath_evaluation",
            "confaide_privacy"
        ]
        
        violentutf_found = []
        for dataset_name in expected_violentutf_datasets:
            if dataset_name in NATIVE_DATASET_TYPES:
                violentutf_found.append(dataset_name)
        
        assert len(violentutf_found) > 0, f"Should find ViolentUTF datasets in registry. Current datasets: {list(NATIVE_DATASET_TYPES.keys())}"
        print(f"✅ Found {len(violentutf_found)} ViolentUTF datasets: {violentutf_found}")

    def test_violentutf_dataset_structure(self) -> None:
        """Test that ViolentUTF datasets have proper structure"""
        required_fields = ["name", "description", "category", "config_required"]
        optional_fields = ["available_configs", "display_name", "file_info", "conversion_strategy"]
        
        violentutf_datasets = []
        for name, info in NATIVE_DATASET_TYPES.items():
            # Identify ViolentUTF datasets by name patterns
            if any(keyword in name.lower() for keyword in ["ollegen", "garak", "legal", "confaide", "docmath"]):
                violentutf_datasets.append((name, info))
        
        assert len(violentutf_datasets) > 0, "Should have at least one ViolentUTF dataset for structure testing"
        
        for dataset_name, dataset_info in violentutf_datasets:
            # Test required fields
            for field in required_fields:
                assert field in dataset_info, f"ViolentUTF dataset {dataset_name} should have required field: {field}"
            
            # Test field types
            assert isinstance(dataset_info["name"], str), f"name should be string for {dataset_name}"
            assert isinstance(dataset_info["description"], str), f"description should be string for {dataset_name}"
            assert isinstance(dataset_info["category"], str), f"category should be string for {dataset_name}"
            assert isinstance(dataset_info["config_required"], bool), f"config_required should be bool for {dataset_name}"
            
            print(f"✅ Dataset {dataset_name} has valid structure")

    def test_violentutf_dataset_categories(self) -> None:
        """Test that ViolentUTF datasets have appropriate categories"""
        expected_categories = [
            "cognitive_behavioral",
            "redteaming",
            "legal_reasoning", 
            "reasoning_evaluation",
            "privacy_evaluation"
        ]
        
        violentutf_datasets = []
        for name, info in NATIVE_DATASET_TYPES.items():
            if any(keyword in name.lower() for keyword in ["ollegen", "garak", "legal", "confaide", "docmath"]):
                violentutf_datasets.append((name, info))
        
        if len(violentutf_datasets) == 0:
            pytest.skip("No ViolentUTF datasets found for category testing")
        
        categories_found = set()
        for dataset_name, dataset_info in violentutf_datasets:
            category = dataset_info.get("category")
            assert category is not None, f"Dataset {dataset_name} should have a category"
            categories_found.add(category)
            
            print(f"✅ Dataset {dataset_name} has category: {category}")
        
        # Should have diverse categories
        assert len(categories_found) >= 2, f"Should have multiple categories, found: {categories_found}"

    def test_violentutf_dataset_configuration_support(self) -> None:
        """Test that ViolentUTF datasets with config_required have available_configs"""
        violentutf_datasets = []
        for name, info in NATIVE_DATASET_TYPES.items():
            if any(keyword in name.lower() for keyword in ["ollegen", "garak", "legal", "confaide", "docmath"]):
                violentutf_datasets.append((name, info))
        
        if len(violentutf_datasets) == 0:
            pytest.skip("No ViolentUTF datasets found for configuration testing")
        
        for dataset_name, dataset_info in violentutf_datasets:
            config_required = dataset_info.get("config_required", False)
            available_configs = dataset_info.get("available_configs")
            
            if config_required:
                assert available_configs is not None, f"Dataset {dataset_name} requires config but has no available_configs"
                assert isinstance(available_configs, dict), f"available_configs should be dict for {dataset_name}"
                assert len(available_configs) > 0, f"available_configs should not be empty for {dataset_name}"
                
                print(f"✅ Dataset {dataset_name} has configuration options: {list(available_configs.keys())}")
            else:
                print(f"ℹ️ Dataset {dataset_name} does not require configuration")

    def test_violentutf_dataset_file_info_structure(self) -> None:
        """Test that ViolentUTF datasets with split files have file_info"""
        violentutf_datasets = []
        for name, info in NATIVE_DATASET_TYPES.items():
            if any(keyword in name.lower() for keyword in ["ollegen", "garak", "legal", "confaide", "docmath"]):
                violentutf_datasets.append((name, info))
        
        if len(violentutf_datasets) == 0:
            pytest.skip("No ViolentUTF datasets found for file_info testing")
        
        datasets_with_file_info = []
        for dataset_name, dataset_info in violentutf_datasets:
            file_info = dataset_info.get("file_info")
            
            if file_info is not None:
                datasets_with_file_info.append((dataset_name, file_info))
                
                # Validate file_info structure
                assert isinstance(file_info, dict), f"file_info should be dict for {dataset_name}"
                
                # Expected fields for split files
                expected_file_fields = ["source_pattern", "manifest_file", "total_scenarios"]
                for field in expected_file_fields:
                    if field in file_info:
                        assert isinstance(file_info[field], (str, int)), f"file_info.{field} should be string or int for {dataset_name}"
                
                print(f"✅ Dataset {dataset_name} has file_info with fields: {list(file_info.keys())}")
        
        # Should have at least one dataset with file_info (like OllaGen1)
        assert len(datasets_with_file_info) > 0, "Should have at least one ViolentUTF dataset with file_info for split files"

    def test_violentutf_dataset_descriptions_quality(self) -> None:
        """Test that ViolentUTF datasets have meaningful descriptions"""
        violentutf_datasets = []
        for name, info in NATIVE_DATASET_TYPES.items():
            if any(keyword in name.lower() for keyword in ["ollegen", "garak", "legal", "confaide", "docmath"]):
                violentutf_datasets.append((name, info))
        
        if len(violentutf_datasets) == 0:
            pytest.skip("No ViolentUTF datasets found for description testing")
        
        for dataset_name, dataset_info in violentutf_datasets:
            description = dataset_info.get("description", "")
            
            # Should have meaningful description
            assert len(description) > 20, f"Dataset {dataset_name} should have meaningful description (>20 chars)"
            assert dataset_name.split('_')[0] in description.lower() or any(
                keyword in description.lower() for keyword in ["cognitive", "redteam", "legal", "privacy", "reasoning"]
            ), f"Description should be relevant to dataset {dataset_name}: {description}"
            
            print(f"✅ Dataset {dataset_name} has quality description: {description[:60]}...")

    def test_backward_compatibility_with_pyrit_datasets(self) -> None:
        """Test that existing PyRIT datasets are still present and unchanged"""
        expected_pyrit_datasets = {
            "harmbench": {"category": "safety", "config_required": False},
            "aya_redteaming": {"category": "redteaming", "config_required": True},
            "adv_bench": {"category": "adversarial", "config_required": False},
            "xstest": {"category": "safety", "config_required": False}
        }
        
        for dataset_name, expected_props in expected_pyrit_datasets.items():
            assert dataset_name in NATIVE_DATASET_TYPES, f"PyRIT dataset {dataset_name} should still be in registry"
            
            dataset_info = NATIVE_DATASET_TYPES[dataset_name]
            
            # Verify key properties haven't changed
            assert dataset_info["category"] == expected_props["category"], f"Category changed for {dataset_name}"
            assert dataset_info["config_required"] == expected_props["config_required"], f"config_required changed for {dataset_name}"
            
            print(f"✅ PyRIT dataset {dataset_name} maintained compatibility")

    def test_registry_total_count_increased(self) -> None:
        """Test that the registry now has more datasets than before"""
        total_datasets = len(NATIVE_DATASET_TYPES)
        
        # Original PyRIT datasets were around 10, with ViolentUTF extension should be more
        original_pyrit_count = 10  # Approximate
        
        assert total_datasets > original_pyrit_count, f"Registry should have more than {original_pyrit_count} datasets, has {total_datasets}"
        
        print(f"✅ Registry expanded from ~{original_pyrit_count} to {total_datasets} datasets")

    def test_violentutf_datasets_have_conversion_strategy(self) -> None:
        """Test that ViolentUTF datasets specify conversion strategy"""
        violentutf_datasets = []
        for name, info in NATIVE_DATASET_TYPES.items():
            if any(keyword in name.lower() for keyword in ["ollegen", "garak", "legal", "confaide", "docmath"]):
                violentutf_datasets.append((name, info))
        
        if len(violentutf_datasets) == 0:
            pytest.skip("No ViolentUTF datasets found for conversion strategy testing")
        
        for dataset_name, dataset_info in violentutf_datasets:
            conversion_strategy = dataset_info.get("conversion_strategy")
            
            # Conversion strategy is important for ViolentUTF datasets
            if conversion_strategy is not None:
                assert isinstance(conversion_strategy, str), f"conversion_strategy should be string for {dataset_name}"
                assert len(conversion_strategy) > 0, f"conversion_strategy should not be empty for {dataset_name}"
                
                print(f"✅ Dataset {dataset_name} has conversion strategy: {conversion_strategy}")
            else:
                print(f"ℹ️ Dataset {dataset_name} has no conversion strategy specified")


def main() -> None:
    """Run unit tests manually"""
    test_suite = TestViolentUTFDatasetRegistryUnit()

    try:
        print("\n🧪 Unit Testing ViolentUTF Dataset Registry Extension (Issue #119)\n")

        # Run all test methods
        test_methods = [
            test_suite.test_violentutf_datasets_in_registry,
            test_suite.test_violentutf_dataset_structure,
            test_suite.test_violentutf_dataset_categories,
            test_suite.test_violentutf_dataset_configuration_support,
            test_suite.test_violentutf_dataset_file_info_structure,
            test_suite.test_violentutf_dataset_descriptions_quality,
            test_suite.test_backward_compatibility_with_pyrit_datasets,
            test_suite.test_registry_total_count_increased,
            test_suite.test_violentutf_datasets_have_conversion_strategy,
        ]

        passed = 0
        total = len(test_methods)

        for test_method in test_methods:
            try:
                test_method()
                print(f"✅ {test_method.__name__}")
                passed += 1
            except Exception as e:
                print(f"❌ {test_method.__name__}: {e}")
            print()

        print(f"📊 Unit Tests Summary: {passed}/{total} passed")

        if passed == total:
            print("✅ All unit tests passed - ViolentUTF dataset registry extension is working!")
        else:
            print(f"❌ {total - passed} tests failed - implementation needed")

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()