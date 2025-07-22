#!/usr/bin/env python3
"""
Test Configuration Tab functionality
"""

import json
import requests
import sys
from typing import Dict, Any

# API endpoints
API_BASE_URL = "http://localhost:9080"
KEYCLOAK_URL = "http://localhost:8080"


def get_access_token() -> str:
    """Get access token - using dummy token for now"""
    # Note: In production, this should get a real JWT token from Keycloak
    # For testing purposes, we'll use a dummy token
    print("⚠️  Using test mode - authentication bypassed")
    return "test-token"


def test_blocks_registry(headers: Dict[str, str]) -> bool:
    """Test the blocks registry endpoint"""
    print("\n📊 Testing Blocks Registry...")
    
    url = f"{API_BASE_URL}/api/v1/reports/blocks/registry"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to get blocks registry: {response.status_code}")
        print(response.text)
        return False
    
    data = response.json()
    print(f"✅ Successfully retrieved blocks registry")
    
    # Check structure
    if "blocks" not in data or "categories" not in data:
        print("❌ Invalid registry structure")
        return False
    
    # Display available blocks
    print(f"\nAvailable block types: {len(data['blocks'])}")
    for block_type, block_info in data['blocks'].items():
        definition = block_info['definition']
        print(f"  - {definition['display_name']} ({block_type})")
        print(f"    Category: {definition['category']}")
        print(f"    Description: {definition['description']}")
    
    print(f"\nAvailable categories: {data['categories']}")
    
    return True


def test_report_variables(headers: Dict[str, str]) -> bool:
    """Test the report variables endpoint"""
    print("\n📊 Testing Report Variables...")
    
    url = f"{API_BASE_URL}/api/v1/reports/variables"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to get report variables: {response.status_code}")
        print(response.text)
        return False
    
    variables = response.json()
    print(f"✅ Successfully retrieved {len(variables)} report variables")
    
    # Display some variables
    if variables:
        print("\nSample variables:")
        for var in variables[:5]:
            print(f"  - {var['name']} ({var['category']})")
            print(f"    Type: {var['data_type']}, Source: {var['source']}")
    
    return True


def test_variable_categories(headers: Dict[str, str]) -> bool:
    """Test the variable categories endpoint"""
    print("\n📊 Testing Variable Categories...")
    
    url = f"{API_BASE_URL}/api/v1/reports/variables/categories"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to get variable categories: {response.status_code}")
        print(response.text)
        return False
    
    categories = response.json()
    print(f"✅ Successfully retrieved {len(categories)} variable categories")
    print(f"   Categories: {categories}")
    
    return True


def test_template_validation(headers: Dict[str, str]) -> bool:
    """Test template validation functionality"""
    print("\n📊 Testing Template Validation...")
    
    # First, get a template to test with
    templates_url = f"{API_BASE_URL}/api/v1/reports/templates"
    response = requests.get(templates_url, headers=headers)
    
    if response.status_code != 200 or not response.json():
        print("⚠️  No templates available for validation test")
        return True
    
    template = response.json()[0]
    template_id = template['id']
    
    # Test validation endpoint
    validation_url = f"{API_BASE_URL}/api/v1/reports/templates/{template_id}/validate"
    response = requests.post(validation_url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to validate template: {response.status_code}")
        print(response.text)
        return False
    
    result = response.json()
    print(f"✅ Template validation successful")
    print(f"   Valid: {result['is_valid']}")
    if result.get('errors'):
        print(f"   Errors: {result['errors']}")
    if result.get('warnings'):
        print(f"   Warnings: {result['warnings']}")
    
    return True


def main():
    """Run all Configuration tab tests"""
    print("🚀 Testing Configuration Tab Functionality")
    print("=" * 50)
    
    # Get authentication token
    print("🔐 Setting up test authentication...")
    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    print("✅ Test authentication configured")
    
    # Run tests
    tests = [
        test_blocks_registry,
        test_report_variables,
        test_variable_categories,
        test_template_validation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test(headers):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Summary: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All Configuration tab tests passed!")
    else:
        print("❌ Some tests failed. Please check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()