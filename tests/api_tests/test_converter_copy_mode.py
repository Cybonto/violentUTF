#!/usr/bin/env python3
"""
Test to verify converter COPY mode creates new datasets correctly.

This is a simplified test focused on verifying the fix for the issue
where converters in COPY mode didn't actually create new datasets.
"""

import json
import os
import sys
import time
import uuid

import requests

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
API_BASE_URL = "http://localhost:9080"
JWT_SECRET_KEY = "ZtZDeFsgTqUm3KHSKINa46TUV13JJw7T"  # nosec B105 - test JWT secret


def create_jwt_token():
    """Create a test JWT token"""
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

        return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    except Exception as e:
        print(f"Error creating JWT: {e}")
        return None


def get_headers():
    """Get API request headers"""
    token = create_jwt_token()
    if not token:
        raise ValueError("Failed to create JWT token")

    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "X-API-Gateway": "APISIX"}


def test_converter_copy_mode():
    """Test that converter COPY mode creates a new dataset"""
    headers = get_headers()

    print("\n🧪 Testing Converter COPY Mode Dataset Creation\n")

    # Step 1: Create a source dataset
    print("1️⃣ Creating source dataset...")
    dataset_payload = {
        "name": f"test_source_{uuid.uuid4().hex[:8]}",
        "source_type": "native",
        "dataset_type": "adv_bench",
        "config": {},
    }

    response = requests.post(f"{API_BASE_URL}/api/v1/datasets", json=dataset_payload, headers=headers, timeout=30)

    if response.status_code not in [200, 201]:
        print(f"❌ Failed to create dataset: Status {response.status_code}: {response.text}")
        return False

    dataset_data = response.json()
    source_dataset_id = dataset_data["dataset"]["id"]
    source_dataset_name = dataset_data["dataset"]["name"]
    prompt_count = dataset_data["dataset"]["prompt_count"]
    print(f"✅ Created dataset '{source_dataset_name}' with {prompt_count} prompts")

    # Step 2: Create a converter
    print("\n2️⃣ Creating ROT13 converter...")
    converter_payload = {
        "name": f"test_converter_{uuid.uuid4().hex[:8]}",
        "converter_type": "ROT13Converter",
        "parameters": {"append_description": True},
    }

    response = requests.post(f"{API_BASE_URL}/api/v1/converters", json=converter_payload, headers=headers, timeout=30)

    if response.status_code not in [200, 201]:
        print(f"❌ Failed to create converter: {response.text}")
        return False

    converter_data = response.json()
    converter_id = converter_data["converter"]["id"]
    converter_name = converter_data["converter"]["name"]
    print(f"✅ Created converter '{converter_name}'")

    # Step 3: Apply converter in COPY mode
    print("\n3️⃣ Applying converter in COPY mode...")
    new_dataset_name = f"converted_copy_{uuid.uuid4().hex[:8]}"
    apply_payload = {
        "dataset_id": source_dataset_id,
        "mode": "copy",
        "new_dataset_name": new_dataset_name,
        "save_to_memory": False,
    }

    response = requests.post(
        f"{API_BASE_URL}/api/v1/converters/{converter_id}/apply", json=apply_payload, headers=headers, timeout=30
    )

    if response.status_code != 200:
        print(f"❌ Failed to apply converter: {response.text}")
        return False

    apply_result = response.json()
    print("✅ Converter applied successfully:")
    print(f"   - Success: {apply_result['success']}")
    print(f"   - New dataset: '{apply_result['dataset_name']}'")
    print(f"   - New dataset ID: {apply_result['dataset_id']}")
    print(f"   - Converted prompts: {apply_result['converted_count']}")

    # Step 4: Verify the new dataset exists
    print("\n4️⃣ Verifying new dataset was created...")
    new_dataset_id = apply_result["dataset_id"]

    response = requests.get(f"{API_BASE_URL}/api/v1/datasets/{new_dataset_id}", headers=headers, timeout=30)

    if response.status_code != 200:
        print(f"❌ New dataset not found: {response.text}")
        return False

    new_dataset = response.json()
    print("✅ New dataset verified:")
    print(f"   - Name: {new_dataset['name']}")
    print(f"   - Source type: {new_dataset['source_type']}")
    print(f"   - Prompt count: {new_dataset['prompt_count']}")

    # Step 5: List all datasets to confirm it appears
    print("\n5️⃣ Listing all datasets to confirm...")
    response = requests.get(f"{API_BASE_URL}/api/v1/datasets", headers=headers, timeout=30)

    if response.status_code == 200:
        datasets = response.json()["datasets"]
        dataset_names = [ds["name"] for ds in datasets]

        if new_dataset_name in dataset_names:
            print(f"✅ New dataset '{new_dataset_name}' appears in dataset list")
        else:
            print(f"⚠️  New dataset '{new_dataset_name}' not found in list")
            print(f"   Available datasets: {dataset_names}")

    # Cleanup
    print("\n🧹 Cleaning up test resources...")
    # Delete converter
    requests.delete(f"{API_BASE_URL}/api/v1/converters/{converter_id}", headers=headers, timeout=30)
    # Delete datasets
    requests.delete(f"{API_BASE_URL}/api/v1/datasets/{source_dataset_id}", headers=headers, timeout=30)
    requests.delete(f"{API_BASE_URL}/api/v1/datasets/{new_dataset_id}", headers=headers, timeout=30)

    print("\n✅ TEST PASSED: Converter COPY mode successfully creates new datasets!")
    return True


if __name__ == "__main__":
    try:
        success = test_converter_copy_mode()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
