#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.

"""
Verify GitHub Desktop is using fast pre-commit configuration
"""

import subprocess
import sys
import time
from pathlib import Path


def check_git_hook_config() -> bool:
    """Check what configuration the Git hook is using"""
    hook_path = Path(".git/hooks/pre-commit")
    if not hook_path.exists():
        return False, "No pre-commit hook found"

    with open(hook_path, "r") as f:
        content = f.read()

    if ".pre-commit-config-ultrafast.yaml" in content:
        return True, "Ultra-fast configuration (0.3s)"
    elif ".pre-commit-config-fast.yaml" in content:
        return True, "Fast configuration (0.7s)"
    elif ".pre-commit-config.yaml" in content:
        return False, "Full configuration (3.3s) - SLOW!"
    else:
        return False, "Unknown configuration"


def test_ultrafast_performance() -> bool:
    """Test ultra-fast configuration performance"""
    print("🏃 Testing ultra-fast configuration performance...")

    start_time = time.time()
    try:
        result = subprocess.run(
            ["pre-commit", "run", "--config", ".pre-commit-config-ultrafast.yaml", "--all-files"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        duration = time.time() - start_time

        if result.returncode == 0:
            return True, f"✅ Completed in {duration:.2f}s - All checks passed"
        else:
            return False, f"⚠️  Completed in {duration:.2f}s - Some checks failed (normal)"

    except subprocess.TimeoutExpired:
        return False, "❌ Timed out (>30s) - Configuration not optimized"
    except Exception as e:
        return False, f"❌ Error: {e}"


def main() -> None:
    """Main verification function"""
    print("🔍 GitHub Desktop Pre-commit Speed Verification")
    print("=" * 55)

    # Check Git hook configuration
    print("\n1. Checking Git Hook Configuration:")
    is_fast, config_info = check_git_hook_config()

    if is_fast:
        print(f"   ✅ {config_info}")
    else:
        print(f"   ❌ {config_info}")
        print("   💡 Run: bash scripts/setup_fast_github_desktop.sh")
        return 1

    # Test performance
    print("\n2. Testing Performance:")
    success, perf_info = test_ultrafast_performance()
    print(f"   {perf_info}")

    # Show what's checked
    print("\n3. What GitHub Desktop Will Check:")
    print("   ✅ Python syntax errors (prevents broken code)")
    print("   ✅ Large files >5MB (prevents repo bloat)")
    print("   ✅ JSON validation (prevents config breakage)")
    print("   ✅ Trailing whitespace (auto-fixes)")
    print("   ✅ Critical hardcoded secrets (security)")

    print("\n4. What's Skipped for Speed:")
    print("   ⏸️  MyPy type checking")
    print("   ⏸️  Pylint static analysis")
    print("   ⏸️  Full bandit security scan")
    print("   ⏸️  Test structure validation")
    print("   ⏸️  Documentation linting")

    print(f"\n🎯 Result: GitHub Desktop commits will be **{config_info.split('(')[1].split(')')[0]}** fast!")
    print("\n💡 To run full checks before pushing:")
    print("   pre-commit run --all-files --config .pre-commit-config.yaml")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
