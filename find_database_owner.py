#!/usr/bin/env python3
"""
Find which username was used to create the existing PyRIT database
"""

import hashlib
import os

import duckdb
from dotenv import load_dotenv

# Load environment
load_dotenv("violentutf/.env")
salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")

# The existing database
db_path = "app_data/violentutf/pyrit_memory_1d7475808c75215f7b43cf48d9c2dfa930dd8876175ea18e47ed772ddf5db2ef.db"

print(f"Checking database: {db_path}")
print(f"Using salt: {salt}")
print("=" * 60)

# First, let's see what's in the database
try:
    conn = duckdb.connect(db_path, read_only=True)

    # Check if there are any user-specific tables
    tables = conn.execute("SHOW TABLES").fetchall()
    print(f"\nTables in database: {[t[0] for t in tables]}")

    # Check scores table for any username hints
    if any("scores" in t[0] for t in tables):
        print("\nChecking scores table...")
        sample = conn.execute("SELECT DISTINCT scorer_name FROM scores LIMIT 5").fetchall()
        print(f"Sample scorer names: {sample}")

    # Check for any user_id columns
    for table in tables:
        table_name = table[0]
        try:
            columns = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            user_cols = [c[1] for c in columns if "user" in c[1].lower()]
            if user_cols:
                print(f"\nTable {table_name} has user columns: {user_cols}")
                # Get sample values
                for col in user_cols:
                    try:
                        sample = conn.execute(f"SELECT DISTINCT {col} FROM {table_name} LIMIT 5").fetchall()
                        print(f"  {col} values: {[s[0] for s in sample if s[0]]}")
                    except:
                        pass
        except:
            pass

    conn.close()
except Exception as e:
    print(f"Error reading database: {e}")

print("\n" + "=" * 60)
print("Testing username hash combinations...")

# Now test various username patterns
test_patterns = []

# Add specific enterprise patterns
enterprise_prefixes = ["enterprise", "ent", "corp", "prod", "production"]
enterprise_suffixes = ["user", "admin", "web", "api", "service"]

for prefix in enterprise_prefixes:
    for suffix in enterprise_suffixes:
        test_patterns.extend([f"{prefix}.{suffix}", f"{prefix}_{suffix}", f"{prefix}-{suffix}", f"{prefix}{suffix}"])

# Add more specific patterns
test_patterns.extend(
    [
        "system",
        "default",
        "init",
        "setup",
        "install",
        "bootstrap",
        "seed",
        "initial",
        "first_run",
        "firstrun",
        "startup",
    ]
)

# Test each pattern
target_hash = "1d7475808c75215f7b43cf48d9c2dfa930dd8876175ea18e47ed772ddf5db2ef"
found = False

for username in test_patterns:
    salt_bytes = salt.encode("utf-8")
    username_bytes = username.encode("utf-8")
    hashed = hashlib.sha256(salt_bytes + username_bytes).hexdigest()

    if hashed == target_hash:
        print(f"\n✅ FOUND! Username '{username}' created this database!")
        found = True
        break

if not found:
    print("\n❌ Could not determine the username that created this database.")
    print("   The database may have been created with a different salt or")
    print("   through a different mechanism.")
