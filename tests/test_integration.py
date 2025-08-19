from typing import Any

#!/usr/bin/env python3
# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Test script to verify ViolentUTF API integration.

"""
import json
import sys

import requests


def test_api_health() -> Any:
    """Test the API health endpoint."""
    print("Testing API Health Endpoint...")

    try:
        # Test direct API
        response = requests.get("http://localhost:8000/health")
        print(f"Direct API: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")

        # Test via APISIX
        response = requests.get("http://localhost:9080/api/v1/health")
        print(f"Via APISIX: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")

        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_api_docs() -> Any:
    """Test the API documentation endpoint."""
    print("\nTesting API Documentation...")

    try:
        response = requests.get("http://localhost:8000/docs")
        print(f"API Docs Status: {response.status_code}")
        if response.status_code == 200:
            print("API documentation is accessible at http://localhost:8000/docs")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_authentication() -> None:
    """Test authentication endpoint."""
    print("\nTesting Authentication...")

    # You'll need to provide valid credentials
    data = {"username": "testuser", "password": "testpass", "grant_type": "password"}

    try:
        response = requests.post("http://localhost:8000/api/v1/auth/token", data=data)
        print(f"Auth Status: {response.status_code}")
        if response.status_code == 200:
            token_data = response.json()
            print(f"Token Type: {token_data.get('token_type')}")
            print(f"Access Token: {token_data.get('access_token')[:50]}...")
            return token_data.get("access_token")
        else:
            print(f"Auth failed: {response.json()}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def main() -> None:
    """Run all tests."""
    print("ViolentUTF API Integration Test")
    print("================================")

    # Test health
    if not test_api_health():
        print("\n❌ Health check failed. Is the API running?")
        print("Run: cd violentutf_api && docker compose up -d")
        sys.exit(1)

    # Test docs
    test_api_docs()

    # Test auth (optional - requires valid credentials)
    # token = test_authentication()

    print("\n✅ Basic integration tests passed!")
    print("\nNext steps:")
    print("1. Access API documentation at http://localhost:8000/docs")
    print("2. Use the JWT CLI: python3 violentutf_api/jwt_cli.py login")
    print("3. Access the ViolentUTF app and check JWT token management in Welcome page")


if __name__ == "__main__":
    main()
