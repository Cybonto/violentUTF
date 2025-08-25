#!/usr/bin/env python3
"""
Test script to verify that all endpoints used in 0_Start.py are properly routed through APISIX
Run this script to ensure the Start page will work correctly with the API
"""

import os
import re
from typing import Dict, List, Tuple

import requests

# Configuration
APISIX_BASE_URL = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
START_PAGE_PATH = "../violentutf/pages/0_Start.py"


def extract_endpoints_from_start_page() -> List[str]:
    """Extract all API endpoints from the Start and Configure Generators pages"""
    endpoints = []

    # Check Start page, Configure Generators page, and Configure Datasets page
    page_files = [
        "../violentutf/pages/0_Start.py",
        "../violentutf/pages/1_Configure_Generators.py",
        "../violentutf/pages/2_Configure_Datasets.py",
        "../violentutf/pages/3_Configure_Converters.py",
        "../violentutf/pages/4_Configure_Scorers.py",
    ]

    for page_file in page_files:
        try:
            with open(page_file, "r") as f:
                content = f.read()

            # Extract from API_ENDPOINTS dictionary
            endpoint_pattern = r'"([^"]+)": f"\{API_BASE_URL\}([^"]+)"'
            matches = re.findall(endpoint_pattern, content)

            for endpoint_name, endpoint_path in matches:
                endpoints.append(endpoint_path)

        except FileNotFoundError:
            print(f"⚠️  Could not find {page_file}")
            continue

    return sorted(list(set(endpoints)))


def test_apisix_connectivity() -> bool:
    """Test basic APISIX connectivity"""
    try:
        response = requests.get(f"{APISIX_BASE_URL}/health", timeout=10)
        return response.status_code == 200
    except requests.ConnectionError:
        return False


def test_endpoint_routing(endpoint: str) -> Tuple[str, int, str]:
    """Test if an endpoint is routed through APISIX"""
    headers = {
        "Authorization": "Bearer test_token",
        "X-Real-IP": "127.0.0.1",
        "X-Forwarded-For": "127.0.0.1",
        "X-Forwarded-Host": "localhost:9080",
        "X-API-Gateway": "APISIX",
    }

    try:
        response = requests.get(f"{APISIX_BASE_URL}{endpoint}", headers=headers, timeout=10)

        if response.status_code == 404:
            return "❌ NOT ROUTED", response.status_code, "Route not configured in APISIX"
        elif response.status_code in [401, 403]:
            return "✅ ROUTED", response.status_code, "Authentication required (expected)"
        elif response.status_code == 200:
            return "✅ ROUTED", response.status_code, "Accessible"
        else:
            return "⚠️  ROUTED", response.status_code, "Unexpected status"

    except requests.ConnectionError:
        return "❌ CONNECTION", 0, "Cannot connect to APISIX"
    except Exception as e:
        return "❌ ERROR", 0, str(e)


def main():
    """Main test function"""
    print("🚀 Testing 0_Start.py API Endpoints Through APISIX")
    print("=" * 60)
    print()

    # Test APISIX connectivity
    print("🔌 Testing APISIX Gateway connectivity...")
    if test_apisix_connectivity():
        print(f"✅ APISIX Gateway is running at {APISIX_BASE_URL}")
    else:
        print(f"❌ APISIX Gateway is NOT running at {APISIX_BASE_URL}")
        print("   💡 Start APISIX: cd apisix && docker compose up -d")
        return False

    print()

    # Extract endpoints from Start page
    print("📋 Extracting endpoints from 0_Start.py...")
    try:
        endpoints = extract_endpoints_from_start_page()
        print(f"   Found {len(endpoints)} unique endpoints")
    except Exception as e:
        print(f"❌ Error reading Start page: {e}")
        return False

    print()

    # Test each endpoint
    print("🔍 Testing endpoint routing through APISIX...")
    print("-" * 80)
    print(f"{'Endpoint':<40} {'Status':<15} {'Code':<8} {'Description'}")
    print("-" * 80)

    all_routed = True
    not_routed = []

    for endpoint in endpoints:
        status, code, description = test_endpoint_routing(endpoint)
        print(f"{endpoint:<40} {status:<15} {code:<8} {description}")

        if "NOT ROUTED" in status:
            all_routed = False
            not_routed.append(endpoint)

    print("-" * 80)
    print()

    # Summary
    if all_routed:
        print("✅ ALL ENDPOINTS ARE PROPERLY ROUTED!")
        print("   The 0_Start.py page should work correctly with the API.")
    else:
        print("❌ SOME ENDPOINTS ARE NOT ROUTED!")
        print("   The following endpoints need route configuration:")
        for endpoint in not_routed:
            print(f"   - {endpoint}")
        print()
        print("💡 Fix by running: cd apisix && ./configure_routes.sh")

    print()

    # Additional information
    print("📖 Additional Information:")
    print(f"   - APISIX Gateway: {APISIX_BASE_URL}")
    print("   - APISIX Dashboard: http://localhost:9001")
    print("   - APISIX Admin API: http://localhost:9180")
    print(f"   - Start page path: {START_PAGE_PATH}")
    print()
    print("🛠️  Next Steps:")
    if not all_routed:
        print("   1. Configure APISIX routes: cd apisix && ./configure_routes.sh")
        print("   2. Verify routes: cd apisix && ./verify_routes.sh")
        print("   3. Start FastAPI service: cd violentutf_api && docker compose up -d")
        print("   4. Test Start page in Streamlit app")
    else:
        print("   1. Start FastAPI service: cd violentutf_api && docker compose up -d")
        print("   2. Test Start page in Streamlit app")
        print("   3. Check authentication with valid JWT tokens")

    return all_routed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
