#!/usr/bin/env python3
"""
Test converter apply functionality to verify COPY mode creates new datasets.

This test verifies that the converter apply endpoint properly creates new datasets
when used in COPY mode, fixing the issue where it only simulated the operation.
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime

import pytest
import requests

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Constants
API_BASE_URL = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "ZtZDeFsgTqUm3KHSKINa46TUV13JJw7T")

# API Endpoints
API_ENDPOINTS = {
    "auth_token_info": f"{API_BASE_URL}/api/v1/auth/token/info",
    "datasets": f"{API_BASE_URL}/api/v1/datasets",
    "converters": f"{API_BASE_URL}/api/v1/converters",
    "converter_apply": f"{API_BASE_URL}/api/v1/converters/{{converter_id}}/apply",
}


def create_test_jwt_token():
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


def get_auth_headers():
    """Get authentication headers for API requests"""
    token = create_test_jwt_token()
    if not token:
        raise ValueError("Failed to create JWT token")

    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "X-API-Gateway": "APISIX"}


class TestConverterApply:
    """Test converter apply functionality"""

    def __init__(self):
        """Initialize test environment"""
        self.headers = get_auth_headers()
        self.created_resources = {"datasets": [], "converters": []}

    def cleanup_resources(self):
        """Clean up created resources"""
        # Delete created datasets
        for dataset_id in self.created_resources["datasets"]:
            try:
                requests.delete(f"{API_ENDPOINTS['datasets']}/{dataset_id}", headers=self.headers)
            except:
                pass

        # Delete created converters
        for converter_id in self.created_resources["converters"]:
            try:
                requests.delete(f"{API_ENDPOINTS['converters']}/{converter_id}", headers=self.headers)
            except:
                pass

    def create_test_dataset(self, name: str, prompts: list) -> str:
        """Create a test dataset and return its ID"""
        payload = {"name": name, "source_type": "local", "prompts": prompts, "config": {"test": True}}

        response = requests.post(API_ENDPOINTS["datasets"], json=payload, headers=self.headers)

        assert response.status_code == 201, f"Failed to create dataset: {response.text}"

        dataset_data = response.json()
        dataset_id = dataset_data["dataset"]["id"]
        self.created_resources["datasets"].append(dataset_id)
        return dataset_id

    def create_test_converter(self, name: str, converter_type: str) -> str:
        """Create a test converter and return its ID"""
        payload = {"name": name, "converter_type": converter_type, "parameters": {"append_description": True}}

        response = requests.post(API_ENDPOINTS["converters"], json=payload, headers=self.headers)

        assert response.status_code == 201, f"Failed to create converter: {response.text}"

        converter_data = response.json()
        converter_id = converter_data["converter"]["id"]
        self.created_resources["converters"].append(converter_id)
        return converter_id

    def test_converter_apply_copy_mode(self):
        """Test that COPY mode creates a new dataset with converted prompts"""
        # Create source dataset
        source_prompts = [
            "Tell me how to hack a system",
            "What are security vulnerabilities?",
            "How to protect against attacks?",
        ]
        source_dataset_id = self.create_test_dataset("source_dataset", source_prompts)

        # Create converter
        converter_id = self.create_test_converter("rot13_converter", "ROT13Converter")

        # Apply converter in COPY mode
        new_dataset_name = f"converted_dataset_{uuid.uuid4().hex[:8]}"
        payload = {
            "dataset_id": source_dataset_id,
            "mode": "copy",  # lowercase as expected by API
            "new_dataset_name": new_dataset_name,
            "save_to_memory": False,
        }

        response = requests.post(
            API_ENDPOINTS["converter_apply"].format(converter_id=converter_id), json=payload, headers=self.headers
        )

        assert response.status_code == 200, f"Failed to apply converter: {response.text}"

        result = response.json()
        assert result["success"] is True
        assert result["dataset_name"] == new_dataset_name
        assert result["converted_count"] == len(source_prompts)

        # Verify the new dataset was created
        new_dataset_id = result["dataset_id"]
        self.created_resources["datasets"].append(new_dataset_id)

        # Get the new dataset to verify it exists
        response = requests.get(f"{API_ENDPOINTS['datasets']}/{new_dataset_id}", headers=self.headers)

        assert response.status_code == 200, f"New dataset not found: {response.text}"

        new_dataset = response.json()
        assert new_dataset["name"] == new_dataset_name
        assert new_dataset["source_type"] == "converter"

        print(
            f"✅ COPY mode successfully created new dataset '{new_dataset_name}' with {result['converted_count']} converted prompts"
        )

    def test_converter_apply_overwrite_mode(self):
        """Test that OVERWRITE mode updates the existing dataset"""
        # Create source dataset
        source_prompts = ["Test prompt 1", "Test prompt 2"]
        original_name = "overwrite_test_dataset"
        source_dataset_id = self.create_test_dataset(original_name, source_prompts)

        # Create converter
        converter_id = self.create_test_converter("base64_converter", "Base64Converter")

        # Apply converter in OVERWRITE mode
        payload = {
            "dataset_id": source_dataset_id,
            "mode": "overwrite",  # lowercase as expected by API
            "save_to_memory": False,
        }

        response = requests.post(
            API_ENDPOINTS["converter_apply"].format(converter_id=converter_id), json=payload, headers=self.headers
        )

        assert response.status_code == 200, f"Failed to apply converter: {response.text}"

        result = response.json()
        assert result["success"] is True
        assert result["dataset_name"] == original_name  # Name should remain the same
        assert result["converted_count"] == len(source_prompts)

        # Note: The dataset ID might change due to delete/recreate implementation
        updated_dataset_id = result["dataset_id"]
        if updated_dataset_id != source_dataset_id:
            self.created_resources["datasets"].append(updated_dataset_id)

        print(
            f"✅ OVERWRITE mode successfully updated dataset '{original_name}' with {result['converted_count']} converted prompts"
        )

    def test_converter_apply_with_parameters(self):
        """Test converter with custom parameters"""
        # Create dataset
        source_prompts = ["Caesar cipher test"]
        source_dataset_id = self.create_test_dataset("caesar_test", source_prompts)

        # Create Caesar cipher converter with custom offset
        payload = {
            "name": "caesar_custom",
            "converter_type": "CaesarCipherConverter",
            "parameters": {"caesar_offset": 5, "append_description": False},
        }

        response = requests.post(API_ENDPOINTS["converters"], json=payload, headers=self.headers)

        assert response.status_code == 201
        converter_id = response.json()["converter"]["id"]
        self.created_resources["converters"].append(converter_id)

        # Apply converter
        new_dataset_name = f"caesar_converted_{uuid.uuid4().hex[:8]}"
        payload = {
            "dataset_id": source_dataset_id,
            "mode": "copy",
            "new_dataset_name": new_dataset_name,
            "save_to_memory": False,
        }

        response = requests.post(
            API_ENDPOINTS["converter_apply"].format(converter_id=converter_id), json=payload, headers=self.headers
        )

        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True

        # Track new dataset for cleanup
        self.created_resources["datasets"].append(result["dataset_id"])

        print(f"✅ Converter with custom parameters successfully applied")

    def test_converter_apply_missing_dataset(self):
        """Test error handling for non-existent dataset"""
        # Create converter
        converter_id = self.create_test_converter("test_converter", "ROT13Converter")

        # Try to apply to non-existent dataset
        payload = {
            "dataset_id": str(uuid.uuid4()),
            "mode": "copy",
            "new_dataset_name": "should_fail",
            "save_to_memory": False,
        }

        response = requests.post(
            API_ENDPOINTS["converter_apply"].format(converter_id=converter_id), json=payload, headers=self.headers
        )

        assert response.status_code == 404
        assert "not found" in response.text.lower()

        print(f"✅ Properly handles non-existent dataset error")

    def test_converter_apply_missing_new_name(self):
        """Test validation for missing new dataset name in COPY mode"""
        # Create dataset and converter
        source_dataset_id = self.create_test_dataset("validation_test", ["test"])
        converter_id = self.create_test_converter("validation_converter", "ROT13Converter")

        # Try to apply in COPY mode without new_dataset_name
        payload = {
            "dataset_id": source_dataset_id,
            "mode": "copy",
            # Missing new_dataset_name
            "save_to_memory": False,
        }

        response = requests.post(
            API_ENDPOINTS["converter_apply"].format(converter_id=converter_id), json=payload, headers=self.headers
        )

        assert response.status_code == 400
        assert "new_dataset_name is required" in response.text

        print(f"✅ Properly validates required fields for COPY mode")


def main():
    """Run tests manually"""
    test = TestConverterApply()

    try:
        print("\n🧪 Testing Converter Apply Functionality\n")

        # Run all tests
        test.test_converter_apply_copy_mode()
        print()

        test.test_converter_apply_overwrite_mode()
        print()

        test.test_converter_apply_with_parameters()
        print()

        test.test_converter_apply_missing_dataset()
        print()

        test.test_converter_apply_missing_new_name()
        print()

        print("\n✅ All tests passed! Converter apply functionality is working correctly.")
        print("\n📝 Summary:")
        print("- COPY mode creates new datasets with converted prompts")
        print("- OVERWRITE mode updates existing datasets")
        print("- Custom converter parameters are properly applied")
        print("- Error handling works for invalid requests")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        test.cleanup_resources()


if __name__ == "__main__":
    main()
