#!/usr/bin/env python3
"""
Test script for Phase 1 OpenAPI Integration
Tests dynamic model discovery with GSAi API
"""

import asyncio
import os
import sys
from typing import Dict, List, Optional

import httpx

# Add the FastAPI app to the Python path
sys.path.append("/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app")

from app.api.endpoints.generators import (
    discover_apisix_models_enhanced,
    discover_openapi_models_from_provider,
    get_openapi_provider_config,
)


async def test_gsai_direct_api():
    """Test direct GSAi API call"""
    print("🧪 Test 1: Direct GSAi API Model Discovery")
    print("=" * 50)

    # GSAi API configuration from ai-tokens.env
    base_url = "https://api.dev.gsai.mcaas.fcs.gsa.gov"
    auth_token = "test_user_redacted"  # Using the redacted token from user's example

    try:
        models = await discover_openapi_models_from_provider("gsai-api-1", base_url, auth_token)

        if models:
            print(f"✅ SUCCESS: Discovered {len(models)} models from GSAi API")
            print("📋 Models found:")
            for i, model in enumerate(models, 1):
                print(f"   {i}. {model}")

            # Verify expected models from user's sample response
            expected_models = [
                "claude_3_5_sonnet",
                "claude_3_7_sonnet",
                "claude_3_haiku",
                "llama3211b",
                "cohere_english_v3",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-2.5-pro-preview-05-06",
                "text-embedding-005",
            ]

            found_models = set(models)
            expected_set = set(expected_models)

            if found_models == expected_set:
                print("✅ All expected models found!")
            else:
                missing = expected_set - found_models
                extra = found_models - expected_set
                if missing:
                    print(f"⚠️  Missing models: {missing}")
                if extra:
                    print(f"ℹ️  Extra models: {extra}")

        else:
            print("❌ FAILED: No models discovered")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print()


def test_provider_config():
    """Test provider configuration mapping"""
    print("🧪 Test 2: Provider Configuration Mapping")
    print("=" * 50)

    # Test with the actual GSAi configuration
    config = get_openapi_provider_config("gsai-api-1")

    print(f"Provider ID: {config['id']}")
    print(f"Name: {config['name']}")
    print(f"Base URL: {config['base_url']}")
    print(f"Auth Token: {'***' + config['auth_token'][-4:] if config['auth_token'] else 'None'}")
    print(f"Auth Type: {config['auth_type']}")

    if config["base_url"] and config["auth_token"]:
        print("✅ Configuration loaded successfully")
    else:
        print("❌ Configuration incomplete")
        print("💡 Make sure OPENAPI_1_* environment variables are set")

    print()


async def test_enhanced_discovery():
    """Test enhanced discovery function"""
    print("🧪 Test 3: Enhanced Discovery Function")
    print("=" * 50)

    try:
        models = await discover_apisix_models_enhanced("openapi-gsai-api-1")

        if models:
            print(f"✅ SUCCESS: Enhanced discovery found {len(models)} models")
            print("📋 Models found:")
            for i, model in enumerate(models, 1):
                print(f"   {i}. {model}")
        else:
            print("❌ Enhanced discovery returned no models")
            print("💡 This might fall back to route-based discovery if API call fails")

    except Exception as e:
        print(f"❌ ERROR in enhanced discovery: {e}")

    print()


def test_environment_variables():
    """Test that environment variables are properly set"""
    print("🧪 Test 4: Environment Variables Check")
    print("=" * 50)

    # Check for GSAi configuration
    vars_to_check = [
        "OPENAPI_ENABLED",
        "OPENAPI_1_ENABLED",
        "OPENAPI_1_ID",
        "OPENAPI_1_NAME",
        "OPENAPI_1_BASE_URL",
        "OPENAPI_1_AUTH_TOKEN",
    ]

    all_set = True
    for var in vars_to_check:
        value = os.getenv(var)
        if value:
            if "TOKEN" in var:
                print(f"✅ {var}: ***{value[-4:]}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Not set")
            all_set = False

    if all_set:
        print("\n✅ All required environment variables are set")
    else:
        print("\n❌ Some environment variables are missing")
        print("💡 Check your ai-tokens.env file and ensure setup script loaded them")

    print()


async def main():
    """Run all tests"""
    print("🚀 Phase 1 OpenAPI Integration Tests")
    print("=" * 60)
    print("Testing dynamic model discovery with GSAi API")
    print()

    # Test environment variables first
    test_environment_variables()

    # Test provider configuration
    test_provider_config()

    # Test direct API call
    await test_gsai_direct_api()

    # Test enhanced discovery
    await test_enhanced_discovery()

    print("🎯 Test Summary")
    print("=" * 60)
    print("If all tests passed:")
    print("✅ OpenAPI model discovery is working")
    print("✅ GSAi API integration is functional")
    print("✅ FastAPI endpoints should return real model lists")
    print()
    print("Next steps:")
    print("1. Restart FastAPI container to apply changes")
    print("2. Test from ViolentUTF Streamlit interface")
    print("3. Verify GSAi models appear in AI Gateway configuration")


if __name__ == "__main__":
    # Load environment variables from ai-tokens.env
    from dotenv import load_dotenv

    load_dotenv("ai-tokens.env")

    asyncio.run(main())
