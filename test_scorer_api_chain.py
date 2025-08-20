#!/usr/bin/env python3
# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Comprehensive test script to trace why scorers aren't being displayed in the UI.
Tests the complete API response chain from database to UI.
"""

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import jwt
import requests

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(__file__), "violentutf"))
sys.path.append(os.path.join(os.path.dirname(__file__), "violentutf_api/fastapi_app"))

# Import required modules
try:
    from violentutf.utils.jwt_manager import JWTManager
    from violentutf.utils.user_context_manager import UserContextManager
    from violentutf_api.fastapi_app.app.core.user_context_manager import FastAPIUserContextManager

    print("✅ Successfully imported user context managers")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure to run this from the project root directory")
    sys.exit(1)

# Configuration
API_BASE_URL = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
API_BASE_URL = API_BASE_URL.rstrip("/api").rstrip("/")
SCORERS_ENDPOINT = f"{API_BASE_URL}/api/v1/scorers"

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")


def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")


def print_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def print_info(msg):
    print(f"ℹ️  {msg}")


def check_database_file():
    """Check if database file exists with correct permissions"""
    print_section("1. DATABASE FILE CHECK")

    # Get database path
    salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")
    app_data_dir = os.getenv("APP_DATA_DIR", "./app_data/violentutf")

    # Test various username formats
    test_usernames = ["ViolentUTF Web User", "violentutf.web", "Tam Nguyen", "tam.nguyen", "tam.nguyen@protonmail.com"]

    print(f"Salt: {salt}")
    print(f"App data directory: {app_data_dir}")

    db_files_found = {}

    for username in test_usernames:
        # Normalize username
        streamlit_normalized = UserContextManager.normalize_username(username)
        fastapi_normalized = FastAPIUserContextManager.normalize_username(username)

        print(f"\nUsername: '{username}'")
        print(f"  Streamlit normalized: '{streamlit_normalized}'")
        print(f"  FastAPI normalized: '{fastapi_normalized}'")

        if streamlit_normalized != fastapi_normalized:
            print_error(f"Normalization mismatch! Streamlit: '{streamlit_normalized}', FastAPI: '{fastapi_normalized}'")
        else:
            print_success("Normalization consistent")

        # Calculate database filename
        salt_bytes = salt.encode("utf-8")
        hashed_username = hashlib.sha256(salt_bytes + streamlit_normalized.encode("utf-8")).hexdigest()
        db_filename = f"pyrit_memory_{hashed_username}.db"
        db_path = os.path.join(app_data_dir, db_filename)

        print(f"  Expected DB path: {db_path}")

        if os.path.exists(db_path):
            print_success(f"Database file exists")
            file_size = os.path.getsize(db_path) / 1024  # KB
            print(f"  File size: {file_size:.2f} KB")
            db_files_found[streamlit_normalized] = db_path

            # Check for scorers in database
            try:
                import duckdb

                with duckdb.connect(db_path) as conn:
                    result = conn.execute(
                        "SELECT COUNT(*) FROM scorers WHERE user_id = ?", [streamlit_normalized]
                    ).fetchone()
                    scorer_count = result[0] if result else 0
                    print(f"  Scorers in DB: {scorer_count}")

                    if scorer_count > 0:
                        # Show scorer details
                        scorers = conn.execute(
                            """
                            SELECT id, name, type, created_at
                            FROM scorers
                            WHERE user_id = ?
                            ORDER BY created_at DESC
                            LIMIT 5
                        """,
                            [streamlit_normalized],
                        ).fetchall()

                        print("  Recent scorers:")
                        for scorer in scorers:
                            print(f"    - {scorer[1]} ({scorer[2]}) - ID: {scorer[0][:8]}...")
            except Exception as e:
                print_error(f"Error reading database: {e}")
        else:
            print_warning("Database file not found")

    return db_files_found


def test_jwt_token_creation():
    """Test JWT token creation with different user contexts"""
    print_section("2. JWT TOKEN CREATION TEST")

    jwt_manager = JWTManager()

    # Test token creation with different user contexts
    test_contexts = [
        {
            "sub": "violentutf.web",
            "preferred_username": "violentutf.web",
            "name": "ViolentUTF Web User",
            "email": "violentutf@example.com",
        },
        {
            "sub": "tam.nguyen",
            "preferred_username": "tam.nguyen",
            "name": "Tam Nguyen",
            "email": "tam.nguyen@protonmail.com",
        },
    ]

    tokens = {}

    for context in test_contexts:
        print(f"\nTesting context: {context['preferred_username']}")

        # Get canonical username
        canonical = UserContextManager.get_canonical_username(context)
        print(f"  Canonical username: '{canonical}'")

        # Create token
        token = jwt_manager.create_token(context)
        if token:
            print_success("Token created successfully")

            # Decode and verify
            decoded = jwt.decode(token, options={"verify_signature": False})
            print(f"  Token 'sub' claim: '{decoded.get('sub')}'")
            print(f"  Token 'username' claim: '{decoded.get('username')}'")

            # Extract canonical username from token
            extracted = FastAPIUserContextManager.extract_canonical_username(decoded)
            print(f"  FastAPI extracted: '{extracted}'")

            if extracted == canonical:
                print_success("Token username matches canonical")
            else:
                print_error(f"Token username mismatch! Expected: '{canonical}', Got: '{extracted}'")

            tokens[context["preferred_username"]] = token
        else:
            print_error("Failed to create token")

    return tokens


def test_api_authentication(tokens):
    """Test API authentication with different tokens"""
    print_section("3. API AUTHENTICATION TEST")

    for username, token in tokens.items():
        print(f"\nTesting with token for: {username}")

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "X-API-Gateway": "APISIX"}

        # Add APISIX API key if available
        apisix_api_key = os.getenv("VIOLENTUTF_API_KEY") or os.getenv("APISIX_API_KEY")
        if apisix_api_key:
            headers["apikey"] = apisix_api_key

        try:
            # Test token info endpoint
            response = requests.get(f"{API_BASE_URL}/api/v1/auth/token/info", headers=headers, timeout=10)

            if response.status_code == 200:
                print_success("Token authentication successful")
                token_info = response.json()
                print(f"  API sees username as: '{token_info.get('username')}'")
                print(f"  Full token info: {json.dumps(token_info, indent=2)}")
            else:
                print_error(f"Token authentication failed: {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print_error(f"API request failed: {e}")


def test_scorers_endpoint(tokens):
    """Test the scorers endpoint with different tokens"""
    print_section("4. SCORERS ENDPOINT TEST")

    all_results = {}

    for username, token in tokens.items():
        print(f"\nTesting scorers endpoint with token for: {username}")

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "X-API-Gateway": "APISIX"}

        # Add APISIX API key if available
        apisix_api_key = os.getenv("VIOLENTUTF_API_KEY") or os.getenv("APISIX_API_KEY")
        if apisix_api_key:
            headers["apikey"] = apisix_api_key

        try:
            response = requests.get(SCORERS_ENDPOINT, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                scorers = data.get("scorers", [])
                total = data.get("total", 0)

                print_success(f"API request successful - Found {total} scorers")

                if scorers:
                    print("  Scorers returned:")
                    for scorer in scorers[:5]:  # Show first 5
                        print(f"    - {scorer['name']} ({scorer['type']}) - ID: {scorer['id'][:8]}...")
                else:
                    print_warning("No scorers returned by API")

                all_results[username] = {"success": True, "total": total, "scorers": scorers}
            else:
                print_error(f"API request failed: {response.status_code}")
                print(f"  Response: {response.text}")

                all_results[username] = {"success": False, "status_code": response.status_code, "error": response.text}
        except Exception as e:
            print_error(f"API request exception: {e}")
            all_results[username] = {"success": False, "error": str(e)}

    return all_results


def check_streamlit_api_call():
    """Check how Streamlit is making the API call"""
    print_section("5. STREAMLIT API CALL CHECK")

    print("Checking Streamlit configuration...")

    # Check environment variables
    env_vars = {
        "VIOLENTUTF_API_URL": os.getenv("VIOLENTUTF_API_URL"),
        "JWT_SECRET_KEY": "***" if os.getenv("JWT_SECRET_KEY") else None,
        "PYRIT_DB_SALT": os.getenv("PYRIT_DB_SALT"),
        "APP_DATA_DIR": os.getenv("APP_DATA_DIR"),
        "KEYCLOAK_USERNAME": os.getenv("KEYCLOAK_USERNAME"),
    }

    print("\nEnvironment variables:")
    for key, value in env_vars.items():
        if value:
            print_success(f"{key}: {value}")
        else:
            print_warning(f"{key}: Not set")

    # Simulate Streamlit's API call
    print("\nSimulating Streamlit's load_scorers_from_api()...")

    # Create a token as Streamlit would
    jwt_manager = JWTManager()
    user_context = UserContextManager.get_user_context_for_token()
    canonical_username = user_context["preferred_username"]

    print(f"Canonical username for token: '{canonical_username}'")

    api_token = jwt_manager.create_token(user_context)
    if api_token:
        print_success("Created API token")

        # Make the same API call as Streamlit
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "X-API-Gateway": "APISIX",
        }

        apisix_api_key = os.getenv("VIOLENTUTF_API_KEY") or os.getenv("APISIX_API_KEY")
        if apisix_api_key:
            headers["apikey"] = apisix_api_key

        try:
            response = requests.get(SCORERS_ENDPOINT, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                print_success(f"API call successful - {data.get('total', 0)} scorers")
                return data
            else:
                print_error(f"API call failed: {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print_error(f"API call exception: {e}")
    else:
        print_error("Failed to create API token")

    return None


def generate_summary(db_files, api_results):
    """Generate a summary of findings"""
    print_section("SUMMARY AND RECOMMENDATIONS")

    # Check for user context issues
    canonical_users = set()
    for username in ["ViolentUTF Web User", "violentutf.web", "Tam Nguyen", "tam.nguyen", "tam.nguyen@protonmail.com"]:
        canonical = UserContextManager.normalize_username(username)
        canonical_users.add(canonical)

    print(f"\nUnique canonical usernames: {canonical_users}")

    if len(canonical_users) > 1:
        print_warning("Multiple canonical usernames detected - this may cause data fragmentation")

    # Check database consistency
    print("\nDatabase files found:")
    for username, path in db_files.items():
        print(f"  - {username}: {path}")

    # Check API results consistency
    print("\nAPI results summary:")
    for username, result in api_results.items():
        if result["success"]:
            print(f"  - {username}: {result['total']} scorers")
        else:
            print(f"  - {username}: Failed")

    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS:")

    if len(canonical_users) > 1:
        print("\n1. USER CONTEXT ISSUE DETECTED")
        print("   - Multiple canonical usernames are being used")
        print("   - This causes data to be stored in different database files")
        print("   - Solution: Ensure consistent username normalization")

    # Check for specific issues
    all_empty = all(result.get("total", 0) == 0 for result in api_results.values() if result.get("success"))
    if all_empty and db_files:
        print("\n2. API RETURNING EMPTY RESULTS")
        print("   - Database files exist but API returns no scorers")
        print("   - Possible causes:")
        print("     a) Username mismatch between token and database")
        print("     b) Database connection issue in API")
        print("     c) Query filtering issue")

    # Check for authentication issues
    auth_failures = [username for username, result in api_results.items() if not result.get("success")]
    if auth_failures:
        print("\n3. AUTHENTICATION FAILURES")
        print(f"   - Failed for users: {auth_failures}")
        print("   - Check JWT token creation and validation")


def main():
    """Main test execution"""
    print(f"{GREEN}ViolentUTF Scorer API Chain Test{RESET}")
    print("This script traces why scorers aren't being displayed in the UI")

    # Run all tests
    db_files = check_database_file()
    tokens = test_jwt_token_creation()
    test_api_authentication(tokens)
    api_results = test_scorers_endpoint(tokens)
    streamlit_data = check_streamlit_api_call()

    # Generate summary
    generate_summary(db_files, api_results)

    # Final verdict
    print("\n" + "=" * 60)
    print("FINAL VERDICT:")

    if streamlit_data and streamlit_data.get("total", 0) > 0:
        print_success("Scorers SHOULD be visible in the UI")
        print("If they're not showing, check:")
        print("  1. Browser cache - try hard refresh (Ctrl+Shift+R)")
        print("  2. Streamlit session state - try restarting Streamlit")
        print("  3. Network issues - check browser console for errors")
    else:
        print_error("Scorers will NOT be visible in the UI")
        print("Fix the issues identified above")


if __name__ == "__main__":
    main()
