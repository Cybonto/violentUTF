#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Debug authentication flow for OpenAPI providers."""

import os
import sys

# Add the FastAPI app to path dynamically
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, "violentutf_api", "fastapi_app"))

try:
    import requests
    from app.api.endpoints.generators import get_openapi_provider_config
except ImportError:
    # print(f"Import error: {e}")  # Debug print removed
    # print("Make sure you are running this from the correct directory and dependencies are installed.")
    # Debug print removed
    sys.exit(1)

print("=== Debug OpenAPI Authentication Flow ===\n")

# Check if settings are loaded
# print("1. Checking settings...")  # Debug print removed
# print(f"   OPENAPI_ENABLED: {settings.OPENAPI_ENABLED}")  # Debug print removed
# print(f"   OPENAPI_1_ENABLED: {getattr(settings, 'OPENAPI_1_ENABLED', 'NOT SET')}")  # Debug print removed
# print(f"   OPENAPI_1_ID: {getattr(settings, 'OPENAPI_1_ID', 'NOT SET')}")  # Debug print removed

# Test the provider config function
print("\n2. Testing get_openapi_provider_config('gsai-api-1')...")
config = get_openapi_provider_config("gsai-api-1")
if config:
    print("   Config found!")
    # print(f"   - ID: {config.get('id')}")  # Debug print removed
    # print(f"   - Name: {config.get('name')}")  # Debug print removed
    # print(f"   - Base URL: {config.get('base_url')}")  # Debug print removed
    # print(f"   - Auth Type: {config.get('auth_type')}")  # Debug print removed
    if config.get("auth_token"):
        token = config.get("auth_token")
        masked = token[:4] + "..." + token[-4:] if len(token) > 8 else "***"
    # print(f"   - Auth Token: {masked}")  # Debug print removed
    else:
        # print("   - Auth Token: NOT FOUND!")  # Debug print removed
        pass
else:
    # print("   No config found!")  # Debug print removed
    pass

# Test direct API call
if config and config.get("auth_token") and config.get("base_url"):
    print("\n3. Testing direct API call to GSAI...")
    headers = {
        "Authorization": f"Bearer {config['auth_token']}",
        "Content-Type": "application/json",
    }

    # Test models endpoint
    models_url = f"{config['base_url']}/api/v1/models"
    # print(f"   Testing: GET {models_url}")  # Debug print removed
    try:
        response = requests.get(models_url, headers=headers, verify=False, timeout=10)
        # print(f"   Response: {response.status_code}")  # Debug print removed
        if response.status_code == 200:
            # print("   ✓ Models endpoint works with token")  # Debug print removed
            pass
        else:
            # print(f"   ✗ Models endpoint failed: {response.text[:200]}")  # Debug print removed
            pass
    except (requests.exceptions.RequestException, requests.exceptions.Timeout):
        # print(f"   ✗ Request Error: {e}")  # Debug print removed
        pass
    except (ValueError, TypeError, OSError):
        # print(f"   ✗ Unexpected Error: {e}")  # Debug print removed
        pass

    # Test chat completions endpoint
    chat_url = f"{config['base_url']}/api/v1/chat/completions"
    # print(f"\n   Testing: POST {chat_url}")  # Debug print removed
    payload = {
        "model": "claude_3_5_sonnet",
        "messages": [{"role": "user", "content": "test"}],
    }
    try:
        response = requests.post(chat_url, headers=headers, json=payload, verify=False, timeout=10)
        # print(f"   Response: {response.status_code}")  # Debug print removed
        if response.status_code == 200:
            # print("   ✓ Chat endpoint works with token")  # Debug print removed
            pass
        elif response.status_code == 401:
            # print("   ✗ 401 Unauthorized - token is invalid or expired")  # Debug print removed
            # print(f"   Response: {response.text[:200]}")  # Debug print removed
            pass
        else:
            # print(f"   ✗ Chat endpoint failed: {response.text[:200]}")  # Debug print removed
            pass
    except (requests.exceptions.RequestException, requests.exceptions.Timeout):
        # print(f"   ✗ Request Error: {e}")  # Debug print removed
        pass
    except (ValueError, TypeError, OSError):
        # print(f"   ✗ Unexpected Error: {e}")  # Debug print removed
        pass

print("\n4. Checking environment variables directly...")
for key in ["OPENAPI_1_AUTH_TOKEN", "OPENAPI_GSAI_API_1_AUTH_TOKEN"]:
    value = os.environ.get(key)
    if value:
        masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
        # print(f"   {key}: {masked}")  # Debug print removed
    else:
        # print(f"   {key}: NOT SET")  # Debug print removed
        pass
