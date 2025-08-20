#!/usr/bin/env python3
# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Script to verify how the Streamlit Configure Scorers page is making API calls
and to check for any issues in the request/response chain.
"""

import json
import os
import sys
import time
from datetime import datetime

import requests

# Configuration
API_BASE_URL = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
API_BASE_URL = API_BASE_URL.rstrip("/api").rstrip("/")

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")


def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")


def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def print_info(msg):
    print(f"ℹ️  {msg}")


def intercept_streamlit_api_calls():
    """
    This function shows what API calls the Streamlit page should be making.
    Run this to understand the expected behavior.
    """
    print(f"\n{BLUE}STREAMLIT API CALL SEQUENCE{RESET}")
    print("=" * 60)

    print("\n1. On page load, Streamlit should:")
    print("   a) Check authentication (access_token)")
    print("   b) Create API token if needed")
    print("   c) Call load_scorer_types_from_api()")
    print("   d) Call load_scorers_from_api()")

    print("\n2. Expected API calls:")
    print(f"   - GET {API_BASE_URL}/api/v1/scorers/types")
    print(f"   - GET {API_BASE_URL}/api/v1/scorers")

    print("\n3. Required headers:")
    print("   - Authorization: Bearer <token>")
    print("   - Content-Type: application/json")
    print("   - X-API-Gateway: APISIX")
    print("   - apikey: <APISIX_API_KEY> (if configured)")


def test_direct_api_access():
    """Test direct access to the API without going through Streamlit"""
    print(f"\n{BLUE}DIRECT API ACCESS TEST{RESET}")
    print("=" * 60)

    # First, we need a valid token
    # Import JWT manager to create a token
    sys.path.append(os.path.join(os.path.dirname(__file__), "violentutf"))

    try:
        from violentutf.utils.jwt_manager import JWTManager
        from violentutf.utils.user_context_manager import UserContextManager

        jwt_manager = JWTManager()
        user_context = UserContextManager.get_user_context_for_token()
        api_token = jwt_manager.create_token(user_context)

        if api_token:
            print_success(f"Created API token for user: {user_context['preferred_username']}")
        else:
            print_error("Failed to create API token")
            return
    except Exception as e:
        print_error(f"Error creating token: {e}")
        return

    # Test scorers endpoint
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json", "X-API-Gateway": "APISIX"}

    apisix_api_key = os.getenv("VIOLENTUTF_API_KEY") or os.getenv("APISIX_API_KEY")
    if apisix_api_key:
        headers["apikey"] = apisix_api_key

    print("\nTesting scorers endpoint...")
    print(f"URL: {API_BASE_URL}/api/v1/scorers")
    print(f"Headers: {list(headers.keys())}")

    try:
        start_time = time.time()
        response = requests.get(f"{API_BASE_URL}/api/v1/scorers", headers=headers, timeout=30)
        elapsed = time.time() - start_time

        print(f"\nResponse time: {elapsed:.2f}s")
        print(f"Status code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print_success("API request successful")
            print(f"Total scorers: {data.get('total', 0)}")
            print(f"By category: {data.get('by_category', {})}")

            scorers = data.get("scorers", [])
            if scorers:
                print("\nScorers found:")
                for scorer in scorers[:5]:
                    print(f"  - {scorer['name']} ({scorer['type']}) - Created: {scorer.get('created_at', 'Unknown')}")

            return data
        else:
            print_error(f"API request failed: {response.status_code}")
            print(f"Response: {response.text}")

            # Try to parse error details
            try:
                error_data = response.json()
                if "detail" in error_data:
                    print(f"Error detail: {error_data['detail']}")
            except:
                pass

    except requests.exceptions.Timeout:
        print_error("Request timed out after 30 seconds")
    except requests.exceptions.ConnectionError as e:
        print_error(f"Connection error: {e}")
    except Exception as e:
        print_error(f"Unexpected error: {e}")

    return None


def check_streamlit_session_state():
    """Check what should be in Streamlit session state"""
    print(f"\n{BLUE}STREAMLIT SESSION STATE CHECK{RESET}")
    print("=" * 60)

    print("\nKey session state variables for scorers:")
    print("1. st.session_state.api_scorers - Dictionary of configured scorers")
    print("2. st.session_state.api_scorer_types - Scorer categories from API")
    print("3. st.session_state.api_token - API authentication token")
    print("4. st.session_state.access_token - Keycloak SSO token")

    print("\nTo debug in Streamlit, add this code to the page:")
    print(
        """
    # Debug session state
    with st.expander("🔍 Debug Info", expanded=False):
        st.write("API Scorers:", st.session_state.get("api_scorers", {}))
        st.write("Total scorers:", len(st.session_state.get("api_scorers", {})))
        st.write("API Token exists:", bool(st.session_state.get("api_token")))
        st.write("Access Token exists:", bool(st.session_state.get("access_token")))
    """
    )


def test_scorer_creation():
    """Test creating a scorer through the API"""
    print(f"\n{BLUE}SCORER CREATION TEST{RESET}")
    print("=" * 60)

    # Get token
    sys.path.append(os.path.join(os.path.dirname(__file__), "violentutf"))

    try:
        from violentutf.utils.jwt_manager import JWTManager
        from violentutf.utils.user_context_manager import UserContextManager

        jwt_manager = JWTManager()
        user_context = UserContextManager.get_user_context_for_token()
        api_token = jwt_manager.create_token(user_context)

        if not api_token:
            print_error("Failed to create API token")
            return
    except Exception as e:
        print_error(f"Error creating token: {e}")
        return

    # Create a test scorer
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json", "X-API-Gateway": "APISIX"}

    apisix_api_key = os.getenv("VIOLENTUTF_API_KEY") or os.getenv("APISIX_API_KEY")
    if apisix_api_key:
        headers["apikey"] = apisix_api_key

    test_scorer = {
        "name": f"test_scorer_{int(time.time())}",
        "scorer_type": "SubStringScorer",
        "parameters": {"substring": "test", "category": "test_category"},
    }

    print(f"Creating test scorer: {test_scorer['name']}")

    try:
        response = requests.post(f"{API_BASE_URL}/api/v1/scorers", headers=headers, json=test_scorer, timeout=30)

        if response.status_code == 200:
            data = response.json()
            print_success("Scorer created successfully")
            print(f"Scorer ID: {data.get('scorer', {}).get('id')}")

            # Now list scorers again
            print("\nListing scorers after creation...")
            response = requests.get(f"{API_BASE_URL}/api/v1/scorers", headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                print_success(f"Found {data.get('total', 0)} scorers after creation")
        else:
            print_error(f"Failed to create scorer: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print_error(f"Error creating scorer: {e}")


def check_common_issues():
    """Check for common issues that prevent scorers from showing"""
    print(f"\n{BLUE}COMMON ISSUES CHECK{RESET}")
    print("=" * 60)

    issues_found = []

    # Check 1: API URL configuration
    api_url = os.getenv("VIOLENTUTF_API_URL")
    if not api_url:
        issues_found.append("VIOLENTUTF_API_URL environment variable not set")
    elif "localhost" in api_url and "9080" not in api_url:
        issues_found.append("API URL might be pointing to wrong port (should be 9080 for APISIX)")

    # Check 2: JWT Secret
    if not os.getenv("JWT_SECRET_KEY"):
        issues_found.append("JWT_SECRET_KEY not set - token creation will fail")

    # Check 3: Database salt
    if not os.getenv("PYRIT_DB_SALT"):
        print_warning("PYRIT_DB_SALT not set - using default (may cause issues)")

    # Check 4: APISIX connectivity
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        if response.status_code != 200:
            issues_found.append(f"APISIX gateway not responding properly (status: {response.status_code})")
    except:
        issues_found.append("Cannot connect to APISIX gateway")

    if issues_found:
        print_error("Issues found:")
        for issue in issues_found:
            print(f"  - {issue}")
    else:
        print_success("No common issues detected")

    return issues_found


def provide_troubleshooting_steps():
    """Provide step-by-step troubleshooting"""
    print(f"\n{BLUE}TROUBLESHOOTING STEPS{RESET}")
    print("=" * 60)

    print("\n1. VERIFY SERVICES ARE RUNNING:")
    print("   ./check_services.sh")
    print("   - All services should show as 'healthy'")

    print("\n2. CHECK BROWSER CONSOLE:")
    print("   - Open browser developer tools (F12)")
    print("   - Check Console tab for JavaScript errors")
    print("   - Check Network tab for failed API requests")

    print("\n3. CLEAR STREAMLIT CACHE:")
    print("   - Stop Streamlit (Ctrl+C)")
    print("   - Clear cache: rm -rf ~/.streamlit/cache")
    print("   - Restart Streamlit")

    print("\n4. CHECK DATABASE CONSISTENCY:")
    print("   cd violentutf_api/fastapi_app")
    print("   python check_api_scorers.py")

    print("\n5. VERIFY USER CONTEXT:")
    print("   - Run test_scorer_api_chain.py")
    print("   - Check if canonical username is consistent")

    print("\n6. MANUAL REFRESH IN UI:")
    print("   - Go to Configure Scorers page")
    print("   - Press F5 or Ctrl+R to refresh")
    print("   - Check if scorers appear")

    print("\n7. CHECK LOGS:")
    print("   - Streamlit logs: Check terminal where Streamlit is running")
    print("   - API logs: docker logs violentutf_api")
    print("   - APISIX logs: docker logs apisix")


def main():
    """Main execution"""
    print(f"{GREEN}ViolentUTF Streamlit Scorer API Verification{RESET}")
    print("This script verifies the Streamlit -> API communication for scorers")

    # Show expected behavior
    intercept_streamlit_api_calls()

    # Test direct API access
    api_data = test_direct_api_access()

    # Check session state expectations
    check_streamlit_session_state()

    # Test scorer creation
    test_scorer_creation()

    # Check common issues
    issues = check_common_issues()

    # Provide troubleshooting steps
    provide_troubleshooting_steps()

    # Summary
    print(f"\n{BLUE}SUMMARY{RESET}")
    print("=" * 60)

    if api_data and api_data.get("total", 0) > 0:
        print_success("API is returning scorers correctly")
        print("If scorers aren't showing in UI:")
        print("  1. Check browser cache/refresh")
        print("  2. Verify Streamlit session state")
        print("  3. Check for JavaScript errors in browser console")
    else:
        print_error("API is not returning scorers")
        print("Follow the troubleshooting steps above")


if __name__ == "__main__":
    main()
