#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Check what the API actually returns for scorers."""

import subprocess  # nosec B404 # needed for controlled docker command execution

import requests


def check_api_scorers() -> None:
    """Check what the API returns for scorers list."""
    print("\n" + "=" * 80)
    print("🔍 API Scorer Check")
    print("=" * 80)

    # Get a token from the running Streamlit app or generate one
    # For now, let's check directly through APISIX

    # Try to get scorers through APISIX
    try:
        # First, let's check if APISIX is responding
        print("\n📡 Checking APISIX gateway...")
        health_response = requests.get("http://localhost:9080/health", timeout=5)
        print(f"   APISIX health check: {health_response.status_code}")
    except Exception as e:
        print(f"   ❌ APISIX not responding: {e}")
        return

    # Check what database the API is using
    print("\n📁 Checking FastAPI database...")
    try:
        result = subprocess.run(
            ["docker", "logs", "violentutf_api", "--tail", "20"], capture_output=True, text=True, check=False
        )  # nosec B603 B607 # controlled docker command execution
        logs = result.stdout

        # Look for database initialization logs
        for line in logs.split("\n"):
            if "DuckDB tables initialized" in line and "violentutf.web" in line:
                print(f"   Recent DB operation: {line.strip()}")

    except Exception as e:
        print(f"   ❌ Could not check logs: {e}")

    # Check the database file directly
    print("\n🔍 Direct database check...")
    try:
        from pathlib import Path

        import duckdb

        # Get the expected database path
        result = subprocess.run(  # nosec B603 B607 # controlled docker command execution
            ["docker", "exec", "violentutf_api", "printenv", "PYRIT_DB_SALT"],
            capture_output=True,
            text=True,
            check=True,
        )
        salt = result.stdout.strip()

        import hashlib

        username = "violentutf.web"
        salt_bytes = salt.encode("utf-8")
        hash_val = hashlib.sha256(salt_bytes + username.encode("utf-8")).hexdigest()
        db_filename = f"pyrit_memory_{hash_val}.db"

        print(f"   Expected DB file: {db_filename}")

        # Check multiple locations
        db_locations = [
            Path("./violentutf_api/fastapi_app/app_data/violentutf"),
            Path("./app_data/violentutf"),
            Path("./violentutf/app_data/violentutf"),
        ]

        for db_dir in db_locations:
            db_path = db_dir / db_filename
            if db_path.exists():
                print(f"   ✅ Found at: {db_path}")

                with duckdb.connect(str(db_path)) as conn:
                    # Check scorers
                    result = conn.execute(
                        """
                        SELECT COUNT(*) FROM scorers WHERE user_id = 'violentutf.web'
                    """
                    ).fetchone()
                    print(f"   Scorers in DB: {result[0]}")

                    # List first few
                    scorers = conn.execute(
                        """
                        SELECT id, name, created_at
                        FROM scorers
                        WHERE user_id = 'violentutf.web'
                        ORDER BY created_at DESC
                        LIMIT 5
                    """
                    ).fetchall()

                    if scorers:
                        print("   Recent scorers:")
                        for scorer in scorers:
                            print(f"     - {scorer[1]} (ID: {scorer[0][:8]}...)")
                break
        else:
            print("   ❌ Database file not found!")

    except Exception as e:
        print(f"   Error checking database: {e}")

    # Check container's view of the database
    print("\n🐳 Container database check...")
    try:
        # Execute a Python script inside the container to check the database
        check_script = """
import duckdb
from pathlib import Path
db_path = Path("./app_data/violentutf").glob("pyrit_memory_*.db")
for db in db_path:
    print(f"Found DB: {db.name}")
    try:
        with duckdb.connect(str(db)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM scorers WHERE user_id = \\'violentutf.web\\'").fetchone()
            print(f"  Scorers: {count[0]}")
    except Exception as e:
        print(f"  Error: {e}")
"""

        result = subprocess.run(  # nosec B603 B607 # controlled docker command execution
            ["docker", "exec", "violentutf_api", "python", "-c", check_script],
            capture_output=True,
            text=True,
            check=False,
        )
        print(result.stdout)
        if result.stderr:
            print(f"   Errors: {result.stderr}")

    except Exception as e:
        print(f"   Error checking container: {e}")


if __name__ == "__main__":
    check_api_scorers()
