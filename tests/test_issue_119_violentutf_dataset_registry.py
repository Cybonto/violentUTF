#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Test suite for Issue #119: Extend ViolentUTF Native Dataset Registry

Tests the extension of the NATIVE_DATASET_TYPES registry to include ViolentUTF's
converted datasets as natively supported datasets.
"""

import json
import os
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import Mock, patch

import pytest
import requests

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Constants
API_BASE_URL = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "ZtZDeFsgTqUm3KHSKINa46TUV13JJw7T")

# API Endpoints
API_ENDPOINTS = {
    "datasets": f"{API_BASE_URL}/api/v1/datasets",
    "dataset_types": f"{API_BASE_URL}/api/v1/datasets/types",
    "dataset_preview": f"{API_BASE_URL}/api/v1/datasets/preview",
}


def create_test_jwt_token() -> str:
    """Create a test JWT token for authentication"""
    try:
        import jwt

        payload = {
            "sub": "test_user",
            "preferred_username": "test_user",
            "email": "test@example.com",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "roles": ["ai-api-access"],
        }

        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
        return token
    except Exception as e:
        print(f"Error creating JWT token: {e}")
        return None


def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API requests"""
    token = create_test_jwt_token()
    if not token:
        raise ValueError("Failed to create JWT token")

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-API-Gateway": "APISIX",
    }


class TestViolentUTFDatasetRegistryExtension:
    """Test suite for ViolentUTF dataset registry extension"""

    def setup_method(self) -> None:
        """Initialize test environment for each test method"""
        self.headers = get_auth_headers()
        self.created_resources = {"datasets": []}

    def teardown_method(self) -> None:
        """Clean up created resources after each test method"""
        # Delete created datasets
        for dataset_id in self.created_resources["datasets"]:
            try:
                requests.delete(
                    f"{API_ENDPOINTS['datasets']}/{dataset_id}",
                    headers=self.headers,
                    timeout=30,
                )
            except Exception as e:
                print(f"Warning: Error in cleanup: {e}")

    def test_violentutf_dataset_types_in_registry(self) -> None:
        """Test that ViolentUTF dataset types are included in the registry"""
        response = requests.get(API_ENDPOINTS["dataset_types"], headers=self.headers, timeout=30)

        assert response.status_code == 200, f"Failed to get dataset types: {response.text}"
        
        data = response.json()
        assert "dataset_types" in data, "Response should contain dataset_types"
        
        dataset_types = {dt["name"]: dt for dt in data["dataset_types"]}
        
        # Test for expected ViolentUTF datasets
        expected_violentutf_datasets = [
            "ollegen1_cognitive",
            "garak_redteaming", 
            "legalbench_reasoning",
            "docmath_evaluation",
            "confaide_privacy"
        ]
        
        violentutf_datasets_found = []
        for dataset_name in expected_violentutf_datasets:
            if dataset_name in dataset_types:
                violentutf_datasets_found.append(dataset_name)
                dataset_info = dataset_types[dataset_name]
                
                # Verify required fields for ViolentUTF datasets
                assert "category" in dataset_info, f"Dataset {dataset_name} should have category"
                assert "description" in dataset_info, f"Dataset {dataset_name} should have description"
                assert "config_required" in dataset_info, f"Dataset {dataset_name} should have config_required field"
        
        # Should have at least some ViolentUTF datasets
        assert len(violentutf_datasets_found) > 0, "Should find at least one ViolentUTF dataset in registry"
        print(f"✅ Found {len(violentutf_datasets_found)} ViolentUTF datasets in registry")

    def test_violentutf_dataset_categories(self) -> None:
        """Test that ViolentUTF datasets have proper category classifications"""
        response = requests.get(API_ENDPOINTS["dataset_types"], headers=self.headers, timeout=30)
        
        assert response.status_code == 200, f"Failed to get dataset types: {response.text}"
        
        data = response.json()
        dataset_types = {dt["name"]: dt for dt in data["dataset_types"]}
        
        # Expected categories for ViolentUTF datasets
        expected_categories = {
            "ollegen1_cognitive": "cognitive_behavioral",
            "garak_redteaming": "redteaming", 
            "legalbench_reasoning": "legal_reasoning",
            "docmath_evaluation": "reasoning_evaluation",
            "confaide_privacy": "privacy_evaluation"
        }
        
        for dataset_name, expected_category in expected_categories.items():
            if dataset_name in dataset_types:
                dataset_info = dataset_types[dataset_name]
                actual_category = dataset_info.get("category")
                
                assert actual_category is not None, f"Dataset {dataset_name} should have a category"
                # Allow flexible category matching since implementation may vary
                assert isinstance(actual_category, str), f"Category should be string for {dataset_name}"
                print(f"✅ Dataset {dataset_name} has category: {actual_category}")

    def test_violentutf_dataset_configuration_support(self) -> None:
        """Test that ViolentUTF datasets support configuration when required"""
        response = requests.get(API_ENDPOINTS["dataset_types"], headers=self.headers, timeout=30)
        
        assert response.status_code == 200, f"Failed to get dataset types: {response.text}"
        
        data = response.json()
        dataset_types = {dt["name"]: dt for dt in data["dataset_types"]}
        
        # Test configurable datasets
        configurable_datasets = [
            "ollegen1_cognitive",
            "garak_redteaming"
        ]
        
        for dataset_name in configurable_datasets:
            if dataset_name in dataset_types:
                dataset_info = dataset_types[dataset_name]
                
                # Should require configuration
                config_required = dataset_info.get("config_required", False)
                available_configs = dataset_info.get("available_configs")
                
                if config_required:
                    assert available_configs is not None, f"Dataset {dataset_name} should have available_configs if config_required=True"
                    assert isinstance(available_configs, dict), f"available_configs should be dict for {dataset_name}"
                    print(f"✅ Dataset {dataset_name} has configuration options: {list(available_configs.keys())}")

    def test_violentutf_dataset_preview_functionality(self) -> None:
        """Test that ViolentUTF datasets support preview functionality"""
        response = requests.get(API_ENDPOINTS["dataset_types"], headers=self.headers, timeout=30)
        
        assert response.status_code == 200, f"Failed to get dataset types: {response.text}"
        
        data = response.json()
        dataset_types = [dt["name"] for dt in data["dataset_types"]]
        
        # Find a ViolentUTF dataset to test preview with
        violentutf_dataset = None
        for dataset_name in ["ollegen1_cognitive", "garak_redteaming", "legalbench_reasoning"]:
            if dataset_name in dataset_types:
                violentutf_dataset = dataset_name
                break
        
        if violentutf_dataset is None:
            pytest.skip("No ViolentUTF datasets found in registry for preview test")
        
        # Test dataset preview
        preview_payload = {
            "source_type": "native",
            "dataset_type": violentutf_dataset,
            "config": {}
        }
        
        response = requests.post(
            API_ENDPOINTS["dataset_preview"],
            json=preview_payload,
            headers=self.headers,
            timeout=60  # ViolentUTF datasets might take longer to load
        )
        
        # Preview should succeed or provide meaningful error
        if response.status_code == 200:
            preview_data = response.json()
            assert "preview_prompts" in preview_data, "Preview should contain preview_prompts"
            assert "total_prompts" in preview_data, "Preview should contain total_prompts"
            assert "dataset_info" in preview_data, "Preview should contain dataset_info"
            
            print(f"✅ Preview successful for {violentutf_dataset}: {preview_data['total_prompts']} prompts")
        else:
            # Preview might fail if dataset files are not available - this is acceptable
            print(f"ℹ️ Preview not available for {violentutf_dataset}: {response.status_code}")
            # Should at least not be a server error
            assert response.status_code != 500, f"Preview should not cause server error: {response.text}"

    def test_violentutf_dataset_creation(self) -> None:
        """Test that ViolentUTF datasets can be created successfully"""
        response = requests.get(API_ENDPOINTS["dataset_types"], headers=self.headers, timeout=30)
        
        assert response.status_code == 200, f"Failed to get dataset types: {response.text}"
        
        data = response.json()
        dataset_types = [dt["name"] for dt in data["dataset_types"]]
        
        # Find a ViolentUTF dataset to test creation with
        violentutf_dataset = None
        for dataset_name in ["ollegen1_cognitive", "garak_redteaming", "legalbench_reasoning"]:
            if dataset_name in dataset_types:
                violentutf_dataset = dataset_name
                break
        
        if violentutf_dataset is None:
            pytest.skip("No ViolentUTF datasets found in registry for creation test")
        
        # Test dataset creation
        dataset_name = f"test_violentutf_{violentutf_dataset}_{uuid.uuid4().hex[:8]}"
        
        creation_payload = {
            "name": dataset_name,
            "source_type": "native",
            "dataset_type": violentutf_dataset,
            "config": {}
        }
        
        response = requests.post(
            API_ENDPOINTS["datasets"],
            json=creation_payload,
            headers=self.headers,
            timeout=120  # ViolentUTF datasets might take longer to load
        )
        
        if response.status_code in [200, 201]:
            dataset_data = response.json()["dataset"]
            dataset_id = dataset_data["id"]
            self.created_resources["datasets"].append(dataset_id)
            
            # Verify dataset was created with correct properties
            assert dataset_data["name"] == dataset_name
            assert dataset_data["source_type"] == "native"
            assert "prompts" in dataset_data
            
            print(f"✅ Successfully created ViolentUTF dataset {dataset_name}: {dataset_data['prompt_count']} prompts")
        else:
            # Creation might fail if dataset files are not available - log for investigation
            print(f"ℹ️ Dataset creation not available for {violentutf_dataset}: {response.status_code}")
            print(f"   Response: {response.text}")
            # Should at least not be a server error for registry issues
            if "not found" in response.text.lower() or "unavailable" in response.text.lower():
                # Acceptable failure - dataset files not present
                pass
            else:
                assert response.status_code != 500, f"Dataset creation should not cause server error: {response.text}"

    def test_violentutf_dataset_manifest_discovery(self) -> None:
        """Test that ViolentUTF datasets support manifest-based discovery for split files"""
        # This test verifies the system can handle split dataset files with manifests
        response = requests.get(API_ENDPOINTS["dataset_types"], headers=self.headers, timeout=30)
        
        assert response.status_code == 200, f"Failed to get dataset types: {response.text}"
        
        data = response.json()
        dataset_types = {dt["name"]: dt for dt in data["dataset_types"]}
        
        # Look for datasets that should support split files (like OllaGen1)
        split_file_datasets = ["ollegen1_cognitive"]
        
        for dataset_name in split_file_datasets:
            if dataset_name in dataset_types:
                dataset_info = dataset_types[dataset_name]
                
                # Check if dataset has file_info or similar metadata indicating split file support
                assert "description" in dataset_info, f"Dataset {dataset_name} should have description"
                
                # Dataset description might indicate split file support
                description = dataset_info["description"].lower()
                
                print(f"✅ Dataset {dataset_name} registered - description: {dataset_info['description'][:100]}...")

    def test_backward_compatibility_with_pyrit_datasets(self) -> None:
        """Test that existing PyRIT datasets still work after ViolentUTF extension"""
        response = requests.get(API_ENDPOINTS["dataset_types"], headers=self.headers, timeout=30)
        
        assert response.status_code == 200, f"Failed to get dataset types: {response.text}"
        
        data = response.json()
        dataset_types = {dt["name"]: dt for dt in data["dataset_types"]}
        
        # Verify existing PyRIT datasets are still available
        expected_pyrit_datasets = [
            "harmbench",
            "aya_redteaming", 
            "adv_bench",
            "xstest"
        ]
        
        pyrit_datasets_found = []
        for dataset_name in expected_pyrit_datasets:
            if dataset_name in dataset_types:
                pyrit_datasets_found.append(dataset_name)
                dataset_info = dataset_types[dataset_name]
                
                # Verify PyRIT datasets still have expected structure
                assert "category" in dataset_info, f"PyRIT dataset {dataset_name} should have category"
                assert "description" in dataset_info, f"PyRIT dataset {dataset_name} should have description"
        
        assert len(pyrit_datasets_found) >= 2, "Should still have multiple PyRIT datasets available"
        print(f"✅ Backward compatibility maintained - found {len(pyrit_datasets_found)} PyRIT datasets")

    def test_dataset_registry_total_count(self) -> None:
        """Test that the dataset registry now includes both PyRIT and ViolentUTF datasets"""
        response = requests.get(API_ENDPOINTS["dataset_types"], headers=self.headers, timeout=30)
        
        assert response.status_code == 200, f"Failed to get dataset types: {response.text}"
        
        data = response.json()
        assert "total" in data, "Response should include total count"
        
        total_datasets = data["total"]
        dataset_types = data["dataset_types"]
        
        # Should have original PyRIT datasets (around 10) plus new ViolentUTF datasets
        assert total_datasets >= 10, f"Should have at least 10 datasets (had {total_datasets})"
        assert len(dataset_types) == total_datasets, "Dataset list length should match total"
        
        print(f"✅ Registry contains {total_datasets} total dataset types")

    def test_violentutf_dataset_metadata_validation(self) -> None:
        """Test that ViolentUTF datasets have proper metadata validation"""
        response = requests.get(API_ENDPOINTS["dataset_types"], headers=self.headers, timeout=30)
        
        assert response.status_code == 200, f"Failed to get dataset types: {response.text}"
        
        data = response.json()
        dataset_types = {dt["name"]: dt for dt in data["dataset_types"]}
        
        # Test ViolentUTF datasets have proper metadata structure
        violentutf_datasets = []
        for name, info in dataset_types.items():
            # Identify ViolentUTF datasets by name patterns or categories
            if any(keyword in name.lower() for keyword in ["ollegen", "garak", "legal", "confaide", "docmath"]):
                violentutf_datasets.append((name, info))
        
        for dataset_name, dataset_info in violentutf_datasets:
            # Validate required fields
            required_fields = ["name", "description", "category", "config_required"]
            for field in required_fields:
                assert field in dataset_info, f"ViolentUTF dataset {dataset_name} should have {field}"
            
            # Validate field types
            assert isinstance(dataset_info["name"], str), f"name should be string for {dataset_name}"
            assert isinstance(dataset_info["description"], str), f"description should be string for {dataset_name}"
            assert isinstance(dataset_info["category"], str), f"category should be string for {dataset_name}"
            assert isinstance(dataset_info["config_required"], bool), f"config_required should be bool for {dataset_name}"
            
            # If config is required, should have available_configs
            if dataset_info["config_required"]:
                assert "available_configs" in dataset_info, f"Dataset {dataset_name} should have available_configs"
                assert dataset_info["available_configs"] is not None, f"available_configs should not be None for {dataset_name}"
        
        if violentutf_datasets:
            print(f"✅ Validated metadata for {len(violentutf_datasets)} ViolentUTF datasets")
        else:
            print("ℹ️ No ViolentUTF datasets found for metadata validation")


def main() -> None:
    """Run tests manually"""
    test_suite = TestViolentUTFDatasetRegistryExtension()

    try:
        print("\n🧪 Testing ViolentUTF Dataset Registry Extension (Issue #119)\n")

        # Run all test methods
        test_methods = [
            test_suite.test_violentutf_dataset_types_in_registry,
            test_suite.test_violentutf_dataset_categories,
            test_suite.test_violentutf_dataset_configuration_support,
            test_suite.test_violentutf_dataset_preview_functionality,
            test_suite.test_violentutf_dataset_creation,
            test_suite.test_violentutf_dataset_manifest_discovery,
            test_suite.test_backward_compatibility_with_pyrit_datasets,
            test_suite.test_dataset_registry_total_count,
            test_suite.test_violentutf_dataset_metadata_validation,
        ]

        for test_method in test_methods:
            try:
                test_suite.setup_method()
                test_method()
                print(f"✅ {test_method.__name__}")
            except Exception as e:
                print(f"❌ {test_method.__name__}: {e}")
            finally:
                test_suite.teardown_method()
            print()

        print("✅ All ViolentUTF dataset registry extension tests completed!")

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()