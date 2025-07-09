#!/usr/bin/env python3
"""
Debug authentication flow for OpenAPI providers
"""
import os
import sys

import requests

# Add the FastAPI app to path
sys.path.insert(0, "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app")

from app.api.endpoints.generators import get_openapi_provider_config
from app.core.config import settings

print("=== Debug OpenAPI Authentication Flow ===\n")

# Check if settings are loaded
print("1. Checking settings...")
print(f"   OPENAPI_ENABLED: {settings.OPENAPI_ENABLED}")
print(f"   OPENAPI_1_ENABLED: {getattr(settings, 'OPENAPI_1_ENABLED', 'NOT SET')}")
print(f"   OPENAPI_1_ID: {getattr(settings, 'OPENAPI_1_ID', 'NOT SET')}")

# Test the provider config function
print("\n2. Testing get_openapi_provider_config('gsai-api-1')...")
config = get_openapi_provider_config("gsai-api-1")
if config:
    print(f"   Config found!")
    print(f"   - ID: {config.get('id')}")
    print(f"   - Name: {config.get('name')}")
    print(f"   - Base URL: {config.get('base_url')}")
    print(f"   - Auth Type: {config.get('auth_type')}")
    if config.get("auth_token"):
        token = config.get("auth_token")
        masked = token[:4] + "..." + token[-4:] if len(token) > 8 else "***"
        print(f"   - Auth Token: {masked}")
    else:
        print(f"   - Auth Token: NOT FOUND!")
else:
    print("   No config found!")

# Test direct API call
if config and config.get("auth_token") and config.get("base_url"):
    print("\n3. Testing direct API call to GSAI...")
    headers = {"Authorization": f"Bearer {config['auth_token']}", "Content-Type": "application/json"}

    # Test models endpoint
    models_url = f"{config['base_url']}/api/v1/models"
    print(f"   Testing: GET {models_url}")
    try:
        response = requests.get(models_url, headers=headers, verify=False, timeout=10)
        print(f"   Response: {response.status_code}")
        if response.status_code == 200:
            print("   ✓ Models endpoint works with token")
        else:
            print(f"   ✗ Models endpoint failed: {response.text[:200]}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test chat completions endpoint
    chat_url = f"{config['base_url']}/api/v1/chat/completions"
    print(f"\n   Testing: POST {chat_url}")
    payload = {"model": "claude_3_5_sonnet", "messages": [{"role": "user", "content": "test"}]}
    try:
        response = requests.post(chat_url, headers=headers, json=payload, verify=False, timeout=10)
        print(f"   Response: {response.status_code}")
        if response.status_code == 200:
            print("   ✓ Chat endpoint works with token")
        elif response.status_code == 401:
            print("   ✗ 401 Unauthorized - token is invalid or expired")
            print(f"   Response: {response.text[:200]}")
        else:
            print(f"   ✗ Chat endpoint failed: {response.text[:200]}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

print("\n4. Checking environment variables directly...")
for key in ["OPENAPI_1_AUTH_TOKEN", "OPENAPI_GSAI_API_1_AUTH_TOKEN"]:
    value = os.environ.get(key)
    if value:
        masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
        print(f"   {key}: {masked}")
    else:
        print(f"   {key}: NOT SET")
