#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Validation script to demonstrate the pre-commit process improvements"""

import subprocess  # nosec B404 - needed for pre-commit validation testing
import sys
from pathlib import Path


def run_command(cmd: str, description: str = "") -> bool:
    """Run command and return success status"""
    print(f"🔍 {description}")

    try:
        # Split command for safe execution without shell=True
        cmd_parts = cmd.split()
        result = subprocess.run(
            cmd_parts, capture_output=True, text=True, timeout=30, check=False
        )  # nosec B603 # controlled input
        if result.returncode == 0:
            print(f"✅ PASSED: {description}")
            return True
        else:
            print(f"❌ FAILED: {description}")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}...")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏱️  TIMEOUT: {description}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {description} - {str(e)}")
        return False


def main() -> int:
    """Execute validation"""
    print("🎯 Pre-commit Process Improvements Validation")

    print("=" * 60)

    results = []

    # Test 1: Core hook validation
    print("\\n📋 Testing Core Pre-commit Hooks:")
    core_hooks = [
        "check-json",
        "check-yaml",
        "check-shebang-scripts-are-executable",
        "name-tests-test",
    ]

    for hook in core_hooks:
        success = run_command(f"pre-commit run {hook} --all-files", f"Core hook: {hook}")
        results.append((f"Core hook {hook}", success))

    # Test 2: Configuration tracking files exist
    print("\\n📁 Testing Configuration Tracking:")
    config_files = [
        ".pre-commit-config-version.md",
        "scripts/precommit_env_check.py",
        "scripts/fix_shebang_permissions.py",
        "scripts/precommit_process_improvement.md",
    ]

    for file_path in config_files:
        exists = Path(file_path).exists()
        print(f"{'✅' if exists else '❌'} Configuration file: {file_path}")
        results.append((f"Config file {file_path}", exists))

    # Test 3: Automated tools work
    print("\\n🔧 Testing Automated Tools:")

    # Test shebang fixer
    success = run_command("python3 scripts/fix_shebang_permissions.py", "Shebang permission fixer")
    results.append(("Shebang fixer", success))

    # Test environment checker
    success = run_command("python3 scripts/precommit_env_check.py", "Environment consistency checker")
    results.append(("Environment checker", success))

    # Test 4: JSON validation specifically
    print("\\n📄 Testing JSON Validation:")
    success = run_command("pre-commit run check-json --all-files", "JSON validation across all files")
    results.append(("JSON validation", success))

    # Test 5: Configuration backup system
    print("\\n💾 Testing Configuration Backup System:")
    backup_files = list(Path(".").glob(".pre-commit-config.yaml.backup-*"))
    if backup_files:
        print(f"✅ Found {len(backup_files)} configuration backups")
        results.append(("Configuration backups", True))
    else:
        print("❌ No configuration backups found")
        results.append(("Configuration backups", False))

    # Summary
    print("\\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY:")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    print(f"✅ Passed: {passed}/{total} tests")
    print(f"❌ Failed: {total - passed}/{total} tests")

    if passed == total:
        print("\\n🎉 ALL PROCESS IMPROVEMENTS VALIDATED SUCCESSFULLY!")
        print("\\n🚀 Benefits Achieved:")
        print("   • Systematic error resolution with automation")
        print("   • Version control tracking for hook configurations")
        print("   • Environment consistency validation")
        print("   • Documented workflows and emergency procedures")
        return 0
    else:
        print("\\n⚠️  Some improvements need attention:")
        for name, success in results:
            if not success:
                print(f"   • {name}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
