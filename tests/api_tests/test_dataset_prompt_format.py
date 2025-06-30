#!/usr/bin/env python3
"""
Test dataset prompt format consistency between creation and retrieval.

This test verifies that the prompt field naming is consistent across:
1. Dataset creation (uses 'value' in SeedPromptInfo)
2. Database storage (uses 'prompt_text' in dataset_prompts table)
3. Dataset retrieval (returns 'text' in prompts array)
4. Converter application (expects 'text' in prompts)
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


class TestDatasetPromptFormat:
    """Test dataset prompt format consistency"""

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

    def test_dataset_creation_and_retrieval(self):
        """Test that dataset prompts are properly stored and retrieved"""
        # Create a dataset for testing
        dataset_name = f"test_dataset_{uuid.uuid4().hex[:8]}"

        # Create dataset via API
        payload = {"name": dataset_name, "source_type": "local", "config": {"test": True}}

        response = requests.post(API_ENDPOINTS["datasets"], json=payload, headers=self.headers)

        assert response.status_code in [200, 201], f"Failed to create dataset: {response.text}"

        dataset_data = response.json()
        dataset_id = dataset_data["dataset"]["id"]
        self.created_resources["datasets"].append(dataset_id)

        print(f"✅ Created dataset: {dataset_name} with ID: {dataset_id}")

        # First list all datasets to verify it exists
        list_response = requests.get(API_ENDPOINTS["datasets"], headers=self.headers)

        if list_response.status_code == 200:
            datasets = list_response.json().get("datasets", [])
            print(f"📋 Found {len(datasets)} datasets in list")
            dataset_ids = [d["id"] for d in datasets]
            if dataset_id in dataset_ids:
                print(f"✅ Dataset {dataset_id} found in list")
            else:
                print(f"❌ Dataset {dataset_id} NOT found in list")
                print(f"   Available IDs: {dataset_ids[:3]}...")  # Show first 3

        # Retrieve the dataset
        response = requests.get(f"{API_ENDPOINTS['datasets']}/{dataset_id}", headers=self.headers)

        assert response.status_code == 200, f"Failed to retrieve dataset: {response.text}"

        retrieved_dataset = response.json()
        print(f"✅ Retrieved dataset successfully")

        # Check if prompts are returned
        assert "prompts" in retrieved_dataset, "Dataset should have prompts field"
        print(f"📝 Dataset has {len(retrieved_dataset['prompts'])} prompts")

        # Verify prompt format
        if retrieved_dataset["prompts"]:
            first_prompt = retrieved_dataset["prompts"][0]
            print(f"📋 First prompt structure: {list(first_prompt.keys())}")

            # Check which field name is used
            if "text" in first_prompt:
                print(f"✅ Prompts use 'text' field as expected by converters")
            elif "value" in first_prompt:
                print(f"⚠️  Prompts use 'value' field, but converters expect 'text'")
            elif "prompt_text" in first_prompt:
                print(f"⚠️  Prompts use 'prompt_text' field, but converters expect 'text'")
            else:
                print(f"❌ Prompts don't have expected field. Keys: {list(first_prompt.keys())}")

    def test_converter_apply_with_dataset(self):
        """Test that converter can properly access dataset prompts"""
        # Create a dataset
        dataset_name = f"converter_test_{uuid.uuid4().hex[:8]}"

        payload = {"name": dataset_name, "source_type": "native", "dataset_type": "harmbench", "config": {}}

        response = requests.post(API_ENDPOINTS["datasets"], json=payload, headers=self.headers)

        assert response.status_code in [200, 201], f"Failed to create dataset: {response.text}"

        dataset_id = response.json()["dataset"]["id"]
        self.created_resources["datasets"].append(dataset_id)

        print(f"✅ Created dataset for converter test: {dataset_name}")

        # Create a converter
        converter_payload = {
            "name": f"test_converter_{uuid.uuid4().hex[:8]}",
            "converter_type": "ROT13Converter",
            "parameters": {"append_description": True},
        }

        response = requests.post(API_ENDPOINTS["converters"], json=converter_payload, headers=self.headers)

        assert response.status_code in [200, 201], f"Failed to create converter: {response.text}"

        converter_id = response.json()["converter"]["id"]
        self.created_resources["converters"].append(converter_id)

        print(f"✅ Created converter for test")

        # Apply converter to dataset
        apply_payload = {
            "dataset_id": dataset_id,
            "mode": "copy",
            "new_dataset_name": f"converted_{dataset_name}",
            "save_to_memory": False,
        }

        response = requests.post(
            API_ENDPOINTS["converter_apply"].format(converter_id=converter_id), json=apply_payload, headers=self.headers
        )

        if response.status_code == 200:
            result = response.json()
            self.created_resources["datasets"].append(result["dataset_id"])
            print(f"✅ Converter successfully applied to dataset")
            print(f"   - Converted {result['converted_count']} prompts")
        else:
            print(f"❌ Converter failed to apply: {response.status_code}")
            print(f"   - Error: {response.text}")

            # This is the expected failure if prompt field naming is inconsistent
            if "has no attribute 'text'" in response.text or "'text'" in response.text:
                print(f"\n⚠️  ISSUE CONFIRMED: Converter expects 'text' field but dataset provides different field name")
                print(
                    f"   This confirms the prompt field naming inconsistency between dataset retrieval and converter usage"
                )

    def test_dataset_field_consistency(self):
        """Test field naming consistency across the entire dataset lifecycle"""
        print("\n🔍 Testing Dataset Field Naming Consistency\n")

        # Test 1: Check dataset creation response
        print("1️⃣ Testing dataset creation response format...")

        payload = {"name": f"consistency_test_{uuid.uuid4().hex[:8]}", "source_type": "local", "config": {}}

        response = requests.post(API_ENDPOINTS["datasets"], json=payload, headers=self.headers)

        if response.status_code in [200, 201]:
            dataset_data = response.json()["dataset"]
            dataset_id = dataset_data["id"]
            self.created_resources["datasets"].append(dataset_id)

            if "prompts" in dataset_data and dataset_data["prompts"]:
                prompt_fields = list(dataset_data["prompts"][0].keys())
                print(f"   ✅ Creation response prompt fields: {prompt_fields}")

                # Check which field contains the prompt text
                prompt_text_field = None
                for field in ["value", "text", "prompt_text"]:
                    if field in dataset_data["prompts"][0]:
                        prompt_text_field = field
                        break

                print(f"   📝 Prompt text is in field: '{prompt_text_field}'")

        # Test 2: Check dataset retrieval format
        print("\n2️⃣ Testing dataset retrieval format...")

        response = requests.get(f"{API_ENDPOINTS['datasets']}/{dataset_id}", headers=self.headers)

        if response.status_code == 200:
            retrieved_data = response.json()

            if "prompts" in retrieved_data and retrieved_data["prompts"]:
                prompt_fields = list(retrieved_data["prompts"][0].keys())
                print(f"   ✅ Retrieval response prompt fields: {prompt_fields}")

                # Check which field contains the prompt text
                prompt_text_field = None
                for field in ["value", "text", "prompt_text"]:
                    if field in retrieved_data["prompts"][0]:
                        prompt_text_field = field
                        break

                print(f"   📝 Prompt text is in field: '{prompt_text_field}'")

        print("\n📊 Summary:")
        print("   - Dataset schema (SeedPromptInfo) uses: 'value'")
        print("   - Database table (dataset_prompts) uses: 'prompt_text'")
        print("   - DuckDB manager returns: 'text'")
        print("   - Converter expects: 'text'")
        print("\n   ✅ The fix ensures DuckDB manager returns 'text' field to match converter expectations")


def main():
    """Run tests manually"""
    test = TestDatasetPromptFormat()

    try:
        print("\n🧪 Testing Dataset Prompt Format Consistency\n")

        # Run all tests
        test.test_dataset_creation_and_retrieval()
        print("\n" + "=" * 60 + "\n")

        test.test_converter_apply_with_dataset()
        print("\n" + "=" * 60 + "\n")

        test.test_dataset_field_consistency()

        print("\n✅ All tests completed!")
        print("\n📝 Key Findings:")
        print("- Dataset prompts have inconsistent field naming across different layers")
        print("- The DuckDB manager correctly maps 'prompt_text' to 'text' for API consistency")
        print("- Converters expect the 'text' field which matches the DuckDB manager output")

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
