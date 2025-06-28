#!/usr/bin/env python3
"""
Test script for orchestrator dataset testing functionality
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta

import requests

# Add project paths
sys.path.append("/Users/tamnguyen/Documents/GitHub/ViolentUTF_nightly/violentutf")

# Load environment
from dotenv import load_dotenv

load_dotenv("/Users/tamnguyen/Documents/GitHub/ViolentUTF_nightly/violentutf/.env")


def create_test_token():
    """Create a test JWT token for authentication"""
    import jwt

    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        print("❌ JWT_SECRET_KEY not found in environment")
        return None

    payload = {
        "preferred_username": "test_user",
        "email": "test@example.com",
        "name": "Test User",
        "sub": "test-user",
        "roles": ["ai-api-access"],
        "iat": int(time.time()),
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
    }

    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


def get_auth_headers():
    """Get authentication headers"""
    token = create_test_token()
    if not token:
        return None

    apisix_api_key = os.getenv("VIOLENTUTF_API_KEY")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-API-Gateway": "APISIX",
    }

    if apisix_api_key:
        headers["apikey"] = apisix_api_key

    return headers


def test_orchestrator_types():
    """Test orchestrator types endpoint"""
    print("🔍 Testing orchestrator types discovery...")

    headers = get_auth_headers()
    if not headers:
        return False

    try:
        response = requests.get(
            "http://localhost:9080/api/v1/orchestrators/types",
            headers=headers,
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {len(data)} orchestrator types")
            for orch_type in data:
                print(
                    f"  - {orch_type.get('name', 'Unknown')}: {orch_type.get('description', 'No description')[:50]}..."
                )
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def test_dataset_endpoints():
    """Test dataset endpoints"""
    print("📊 Testing dataset endpoints...")

    headers = get_auth_headers()
    if not headers:
        return False

    try:
        response = requests.get(
            "http://localhost:9080/api/v1/datasets", headers=headers, timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            datasets = data.get("datasets", [])
            print(f"✅ Found {len(datasets)} datasets")
            for dataset in datasets:
                print(
                    f"  - {dataset.get('name', 'Unknown')}: {dataset.get('prompt_count', 0)} prompts"
                )
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def test_generator_endpoints():
    """Test generator endpoints"""
    print("⚙️ Testing generator endpoints...")

    headers = get_auth_headers()
    if not headers:
        return False

    try:
        response = requests.get(
            "http://localhost:9080/api/v1/generators", headers=headers, timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            generators = data.get("generators", [])
            print(f"✅ Found {len(generators)} generators")
            for generator in generators:
                print(
                    f"  - {generator.get('name', 'Unknown')}: {generator.get('type', 'Unknown')}"
                )
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def main():
    """Main test function"""
    print("🧪 Testing Orchestrator Dataset Testing Implementation")
    print("=" * 60)

    # Test authentication setup
    print("🔐 Testing authentication setup...")
    headers = get_auth_headers()
    if not headers:
        print("❌ Authentication setup failed")
        return False
    print("✅ Authentication setup successful")
    print()

    # Test individual endpoints
    tests = [
        ("Orchestrator Types", test_orchestrator_types),
        ("Dataset Endpoints", test_dataset_endpoints),
        ("Generator Endpoints", test_generator_endpoints),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        result = test_func()
        results.append((test_name, result))
        print()

    # Summary
    print("📋 Test Results Summary:")
    print("-" * 30)
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\n🎉 All tests passed! Dataset testing functionality should work.")
        print("\n📝 Next steps:")
        print("1. Navigate to the Configure Datasets page in ViolentUTF")
        print("2. Select a dataset (e.g., 'Memory Dataset 0')")
        print("3. Select a generator for testing")
        print("4. Click 'Run Dataset Test'")
        print("5. The orchestrator should execute the test and display results")
    else:
        print(
            f"\n⚠️ {len(results) - passed} tests failed. Please check the configuration."
        )

    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
