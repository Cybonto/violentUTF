#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Script to check for authentication and token issues that might affect scorer retrieval.

Focuses on the token lifecycle and user context consistency.
"""

import hashlib
import os
import sys
from datetime import datetime

import duckdb
import jwt

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(__file__), "violentutf"))
sys.path.append(os.path.join(os.path.dirname(__file__), "violentutf_api/fastapi_app"))

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_section(title: str) -> None:
    """Print a section header with formatting."""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_success(msg: str) -> None:
    """Print a success message with formatting."""
    print(f"{GREEN}✅ {msg}{RESET}")


def print_error(msg: str) -> None:
    """Print an error message with formatting."""
    print(f"{RED}❌ {msg}{RESET}")


def print_warning(msg: str) -> None:
    """Print a warning message with formatting."""
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def check_environment_setup() -> None:
    """Check if environment is properly configured."""
    print_section("ENVIRONMENT CONFIGURATION CHECK")

    required_vars = {
        "JWT_SECRET_KEY": "Required for token creation/validation",
        "PYRIT_DB_SALT": "Required for database file naming",
        "APP_DATA_DIR": "Directory where databases are stored",
        "VIOLENTUTF_API_URL": "API endpoint URL",
        "KEYCLOAK_USERNAME": "Default username for authentication",
    }

    optional_vars = {
        "VIOLENTUTF_API_KEY": "APISIX API key",
        "APISIX_API_KEY": "Alternative APISIX API key",
        "AI_GATEWAY_API_KEY": "AI Gateway API key",
    }

    missing_required = []

    print("Required environment variables:")
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            if var == "JWT_SECRET_KEY":
                print_success(f"{var}: ****** ({desc})")
            else:
                print_success(f"{var}: {value} ({desc})")
        else:
            print_error(f"{var}: NOT SET ({desc})")
            missing_required.append(var)

    print("\nOptional environment variables:")
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        if value:
            print_success(f"{var}: ****** ({desc})")
        else:
            print_warning(f"{var}: Not set ({desc})")

    return len(missing_required) == 0


def analyze_token_lifecycle() -> None:
    """Analyze the complete token lifecycle."""
    print_section("TOKEN LIFECYCLE ANALYSIS")

    try:
        from violentutf.utils.jwt_manager import JWTManager
        from violentutf.utils.user_context_manager import UserContextManager
        from violentutf_api.fastapi_app.app.core.user_context_manager import FastAPIUserContextManager
    except ImportError as e:
        print_error(f"Failed to import modules: {e}")
        return

    # Step 1: Token Creation
    print("\n1. TOKEN CREATION (Streamlit side):")
    jwt_manager = JWTManager()

    # Test different user contexts
    test_cases = [
        {
            "name": "Default SSO User",
            "context": {
                "sub": "violentutf.web",
                "preferred_username": "violentutf.web",
                "name": "ViolentUTF Web User",
                "email": "violentutf@example.com",
            },
        },
        {
            "name": "Named User",
            "context": {
                "sub": "tam.nguyen",
                "preferred_username": "tam.nguyen",
                "name": "Tam Nguyen",
                "email": "tam.nguyen@protonmail.com",
            },
        },
    ]

    tokens_created = {}

    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        context = test_case["context"]

        # Get canonical username
        canonical = UserContextManager.get_canonical_username()
        print(f"  Input username: {context['preferred_username']}")
        print(f"  Canonical username: {canonical}")

        # Create token
        token = jwt_manager.create_token(context)
        if token:
            print_success("Token created")
            tokens_created[test_case["name"]] = {"token": token, "canonical": canonical, "context": context}

            # Decode token
            decoded = jwt.decode(token, options={"verify_signature": False})
            print(f"  Token 'sub': {decoded.get('sub')}")
            print(f"  Token 'username': {decoded.get('username')}")
            print(f"  Token expires: {datetime.fromtimestamp(decoded.get('exp', 0))}")
        else:
            print_error("Failed to create token")

    # Step 2: Token Processing (API side)
    print("\n2. TOKEN PROCESSING (FastAPI side):")

    for name, token_data in tokens_created.items():
        print(f"\nProcessing token for: {name}")
        token = token_data["token"]
        expected_canonical = token_data["canonical"]

        # Decode token
        decoded = jwt.decode(token, options={"verify_signature": False})

        # Extract canonical username as FastAPI would
        extracted = FastAPIUserContextManager.extract_canonical_username(decoded)
        print(f"  Expected canonical: {expected_canonical}")
        print(f"  Extracted canonical: {extracted}")

        if expected_canonical == extracted:
            print_success("Username extraction consistent")
        else:
            print_error("USERNAME MISMATCH - This will cause scorer isolation!")

    return tokens_created


def check_database_access_pattern(tokens_created: list) -> None:
    """Check how databases are accessed with different tokens."""
    print_section("DATABASE ACCESS PATTERN CHECK")

    salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")
    app_data_dir = os.getenv("APP_DATA_DIR", "./app_data/violentutf")

    print("Database configuration:")
    print(f"  Salt: {salt}")
    print(f"  Data directory: {app_data_dir}")

    # Check which database files would be accessed
    db_access_map = {}

    for name, token_data in tokens_created.items():
        canonical = token_data["canonical"]

        # Calculate database filename
        salt_bytes = salt.encode("utf-8")
        hashed_username = hashlib.sha256(salt_bytes + canonical.encode("utf-8")).hexdigest()
        db_filename = f"pyrit_memory_{hashed_username}.db"
        db_path = os.path.join(app_data_dir, db_filename)

        print(f"\n{name} (canonical: {canonical}):")
        print(f"  DB file: {db_filename}")
        print(f"  Full path: {db_path}")

        db_access_map[canonical] = db_path

        # Check if file exists and has scorers
        if os.path.exists(db_path):
            print_success("Database file exists")

            try:
                with duckdb.connect(db_path) as conn:
                    # Check scorers
                    result = conn.execute(
                        """
                        SELECT COUNT(*) as count,
                               GROUP_CONCAT(DISTINCT user_id) as users
                        FROM scorers
                    """
                    ).fetchone()

                    if result:
                        count = result[0]
                        users = result[1]
                        print(f"  Scorers in DB: {count}")
                        print(f"  User IDs in DB: {users}")

                        if users and canonical not in str(users):
                            print_error(f"USER ID MISMATCH! DB has '{users}' but token has '{canonical}'")

                        # Show sample scorers
                        scorers = conn.execute(
                            """
                            SELECT name, type, user_id, created_at
                            FROM scorers
                            ORDER BY created_at DESC
                            LIMIT 3
                        """
                        ).fetchall()

                        if scorers:
                            print("  Recent scorers:")
                            for scorer in scorers:
                                print(f"    - {scorer[0]} ({scorer[1]}) by '{scorer[2]}'")
            except Exception as e:
                print_error(f"Error reading database: {e}")
        else:
            print_warning("Database file does not exist")

    return db_access_map


def test_api_with_different_users() -> None:
    """Test API access with different user contexts."""
    print_section("API ACCESS WITH DIFFERENT USERS")

    import requests

    API_BASE_URL = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
    API_BASE_URL = API_BASE_URL.rstrip("/api").rstrip("/")

    try:
        from violentutf.utils.jwt_manager import JWTManager
    except ImportError as e:
        print_error(f"Failed to import modules: {e}")
        return

    jwt_manager = JWTManager()

    # Test with different canonical usernames
    test_users = [
        ("violentutf.web", {"preferred_username": "violentutf.web", "sub": "violentutf.web"}),
        ("tam.nguyen", {"preferred_username": "tam.nguyen", "sub": "tam.nguyen"}),
    ]

    for canonical, context in test_users:
        print(f"\nTesting API with canonical user: {canonical}")

        # Create token
        token = jwt_manager.create_token(context)
        if not token:
            print_error("Failed to create token")
            continue

        # Make API request
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "X-API-Gateway": "APISIX"}

        apisix_api_key = os.getenv("VIOLENTUTF_API_KEY") or os.getenv("APISIX_API_KEY")
        if apisix_api_key:
            headers["apikey"] = apisix_api_key

        try:
            # Get scorers
            response = requests.get(f"{API_BASE_URL}/api/v1/scorers", headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                total = data.get("total", 0)
                print_success(f"API returned {total} scorers")

                if total > 0:
                    print("  First few scorers:")
                    for scorer in data.get("scorers", [])[:3]:
                        print(f"    - {scorer['name']} ({scorer['type']})")
            else:
                print_error(f"API request failed: {response.status_code}")

            # Get token info to see what user API sees
            response = requests.get(f"{API_BASE_URL}/api/v1/auth/token/info", headers=headers, timeout=10)

            if response.status_code == 200:
                token_info = response.json()
                api_username = token_info.get("username")
                print(f"  API sees username as: {api_username}")

                if api_username != canonical:
                    print_error(f"USERNAME MISMATCH! Expected '{canonical}', API sees '{api_username}'")
        except Exception as e:
            print_error(f"API request failed: {e}")


def suggest_fixes() -> None:
    """Suggest fixes based on findings."""
    print_section("SUGGESTED FIXES")

    print("\n1. IMMEDIATE FIX - Ensure consistent user context:")
    print("   - Stop all services")
    print("   - Clear existing database files:")
    print("     rm ./app_data/violentutf/pyrit_memory_*.db")
    print("   - Restart services:")
    print("     ./launch_violentutf.sh")
    print("   - Recreate scorers through UI")

    print("\n2. CHECK TOKEN CONSISTENCY:")
    print("   - In Streamlit pages, ensure using UserContextManager.get_user_context_for_token()")
    print("   - In API endpoints, ensure using FastAPIUserContextManager.extract_canonical_username()")

    print("\n3. DEBUG IN STREAMLIT:")
    print("   Add this to Configure Scorers page after token creation:")
    print(
        """
    # Debug token
    if st.session_state.get("api_token"):
        decoded = jwt.decode(st.session_state["api_token"], options={"verify_signature": False})
        st.info(f"Token username: {decoded.get('sub')}")
    """
    )

    print("\n4. VERIFY DATABASE ACCESS:")
    print("   Run check_api_scorers.py to see what's in the database")
    print("   Check that user_id in scorers table matches canonical username")

    print("\n5. FORCE REFRESH:")
    print("   - Clear browser cache (Ctrl+Shift+R)")
    print("   - Restart Streamlit")
    print("   - Navigate to Configure Scorers page")


def main() -> None:
    """Execute the main authentication check."""
    print(f"{GREEN}ViolentUTF Scorer Authentication Issues Check{RESET}")
    print("This script checks for authentication and token issues affecting scorers")

    # Check environment
    env_ok = check_environment_setup()
    if not env_ok:
        print_error("\nFix environment configuration issues before proceeding!")
        return

    # Analyze token lifecycle
    tokens = analyze_token_lifecycle()

    if tokens:
        # Check database access
        check_database_access_pattern(tokens)

        # Test API with different users
        test_api_with_different_users()

    # Suggest fixes
    suggest_fixes()

    print(f"\n{BLUE}{'='*60}{RESET}")
    print("Run the suggested fixes and then test again.")


if __name__ == "__main__":
    main()
