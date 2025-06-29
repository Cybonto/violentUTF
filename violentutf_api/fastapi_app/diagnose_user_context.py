#!/usr/bin/env python3
"""
Diagnostic script for ViolentUTF user context issues

This script helps diagnose user context mismatches that prevent
scorer testing from working properly.
"""

import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.db.duckdb_manager import DuckDBManager


def diagnose_user_contexts():
    """Diagnose what user contexts have data"""
    print("🔍 ViolentUTF User Context Diagnostic")
    print("=" * 50)

    # Common user contexts to check
    user_contexts = [
        "violentutf.web",  # Default account name
        "Tam Nguyen",  # Display name
        "tam.nguyen",  # Possible account variation
        "admin",  # Possible admin account
        "user",  # Generic user
    ]

    total_generators = 0
    total_datasets = 0

    for user_context in user_contexts:
        print(f"\n👤 Checking user context: '{user_context}'")
        print("-" * 30)

        try:
            db = DuckDBManager(user_context)

            # Check generators
            generators = db.list_generators()
            print(f"  📡 Generators: {len(generators)}")
            for gen in generators[:3]:  # Show first 3
                print(f"    • {gen['name']} ({gen['type']})")
            if len(generators) > 3:
                print(f"    • ... and {len(generators) - 3} more")
            total_generators += len(generators)

            # Check datasets
            datasets = db.list_datasets()
            print(f"  📊 Datasets: {len(datasets)}")
            for ds in datasets[:3]:  # Show first 3
                print(f"    • {ds['name']} ({ds['prompt_count']} prompts)")
            if len(datasets) > 3:
                print(f"    • ... and {len(datasets) - 3} more")
            total_datasets += len(datasets)

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print(f"\n📈 Summary:")
    print(f"  Total generators across all contexts: {total_generators}")
    print(f"  Total datasets across all contexts: {total_datasets}")

    if total_generators == 0:
        print(f"\n⚠️  ISSUE FOUND: No generators configured in any user context")
        print(f"   SOLUTION: Go to 'Configure Generators' page and create a generator")
        print(f"   Example: Create an 'AI Gateway' generator with provider and model")

    if total_generators > 0:
        print(f"\n💡 If scorer testing fails despite having generators:")
        print(f"   1. Note which user context has generators above")
        print(f"   2. Run migration script to move data to 'violentutf.web':")
        print(f'      python3 migrate_user_context.py --from "SOURCE_USER" --to "violentutf.web"')


if __name__ == "__main__":
    diagnose_user_contexts()
