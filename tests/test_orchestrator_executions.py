#!/usr/bin/env python3
"""Test script to verify orchestrator executions endpoint"""

import requests
import json
import os
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_BASE_URL = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080").rstrip("/api").rstrip("/")
if not API_BASE_URL:
    API_BASE_URL = "http://localhost:9080"

# Get JWT token from environment or create one
jwt_token = os.getenv("TEST_JWT_TOKEN", "")

if not jwt_token:
    # Try to create a token using the JWT manager approach
    try:
        from violentutf.utils.jwt_manager import jwt_manager

        test_user_data = {
            "preferred_username": "test_user",
            "email": "test@example.com",
            "name": "Test User",
            "sub": "test-user-id",
            "roles": ["ai-api-access"],
        }
        jwt_token = jwt_manager.create_token(test_user_data)
    except Exception as e:
        print(f"Failed to create JWT token: {e}")
        print("Please set TEST_JWT_TOKEN environment variable")
        exit(1)

# Headers
headers = {"Authorization": f"Bearer {jwt_token}", "Content-Type": "application/json", "X-API-Gateway": "APISIX"}

print(f"Testing orchestrator executions endpoint...")
print(f"API Base URL: {API_BASE_URL}")
print(f"JWT Token (first 20 chars): {jwt_token[:20]}...")
print("-" * 50)

# Test 1: List all executions
print("\nTest 1: GET /api/v1/orchestrators/executions")
url = f"{API_BASE_URL}/api/v1/orchestrators/executions"
print(f"URL: {url}")

try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")

    if response.status_code == 200:
        data = response.json()
        print(f"Success! Response: {json.dumps(data, indent=2)}")
    else:
        print(f"Error Response: {response.text}")

        # If we get a 422 error, it might be treating 'executions' as a UUID
        if response.status_code == 422:
            print("\n⚠️  Getting 422 error - 'executions' is being treated as a UUID parameter")
            print("This suggests the wildcard route is catching the request before the specific route")

except Exception as e:
    print(f"Request failed: {e}")

# Test 2: Try the direct FastAPI endpoint (to verify the endpoint exists)
print("\n" + "-" * 50)
print("\nTest 2: Direct FastAPI test (bypassing APISIX)")
direct_url = "http://localhost:8000/api/v1/orchestrators/executions"
print(f"URL: {direct_url}")

try:
    # Remove APISIX-specific header for direct test
    direct_headers = headers.copy()
    direct_headers.pop("X-API-Gateway", None)

    response = requests.get(direct_url, headers=direct_headers)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        print("✓ Endpoint exists in FastAPI")
    elif response.status_code == 401:
        print("✓ Endpoint exists but requires authentication (expected)")
    elif response.status_code == 403:
        print("⚠️  Endpoint blocked - likely requires APISIX gateway header")
    else:
        print(f"Response: {response.text}")

except Exception as e:
    print(f"Request failed: {e}")

# Test 3: Check APISIX routes
print("\n" + "-" * 50)
print("\nTest 3: Check APISIX routes configuration")
admin_key = os.getenv("APISIX_ADMIN_KEY")
if admin_key:
    admin_url = "http://localhost:9180/apisix/admin/routes"
    admin_headers = {"X-API-KEY": admin_key}

    try:
        response = requests.get(admin_url, headers=admin_headers)
        if response.status_code == 200:
            routes = response.json()
            print("APISIX Routes related to orchestrators:")
            for route_id, route in routes.get("node", {}).get("nodes", {}).items():
                if "orchestrator" in str(route.get("uri", "")):
                    print(f"\nRoute ID: {route_id}")
                    print(f"URI: {route.get('uri')}")
                    print(f"Methods: {route.get('methods')}")
    except Exception as e:
        print(f"Failed to check APISIX routes: {e}")
else:
    print("APISIX_ADMIN_KEY not found in environment")

print("\n" + "=" * 50)
print("DIAGNOSIS:")
print("-" * 50)

print(
    """
The issue is that the APISIX route pattern '/api/v1/orchestrators*' is matching
'/api/v1/orchestrators/executions' and treating 'executions' as a UUID parameter.

SOLUTION:
We need to create a specific route for '/api/v1/orchestrators/executions' that
takes precedence over the wildcard route. This can be done by:

1. Adding a specific route in APISIX for the executions endpoint
2. Ensuring it has a lower route ID (higher priority) than the wildcard route

The endpoint URL in the dashboard files is correct and doesn't need to be changed.
The issue is with the APISIX routing configuration.
"""
)
