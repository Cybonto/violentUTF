#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.


"""Pre-commit Performance Optimizer

Analyzes and optimizes pre-commit hook performance
"""

import subprocess  # nosec B404 - needed for controlled pre-commit performance testing
import sys
import time
from pathlib import Path
from typing import Any, Dict


def time_hook(hook_name: str, config_file: str = ".pre-commit-config.yaml") -> tuple[float, bool]:
    """Time how long a specific hook takes to run."""
    print(f"⏱️  Timing {hook_name}...")

    start_time = time.time()
    try:
        result = subprocess.run(  # nosec B603 B607 - controlled pre-commit execution for performance testing
            ["pre-commit", "run", hook_name, "--config", config_file, "--all-files"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        end_time = time.time()
        duration = end_time - start_time

        status = "✅ PASSED" if result.returncode == 0 else "❌ FAILED"
        print(f"  {status} {hook_name}: {duration:.2f}s")

        return duration, result.returncode == 0

    except subprocess.TimeoutExpired:
        print(f"  ⏱️  TIMEOUT {hook_name}: >60s")
        return 60.0, False
    except Exception as e:
        print(f"  ❌ ERROR {hook_name}: {e}")
        return 0.0, False


def benchmark_configs() -> dict:
    """Benchmark full vs fast pre-commit configs."""
    print("🏁 Benchmarking Pre-commit Configurations")

    print("=" * 50)

    # Test hooks that are common to both configs
    common_hooks = [
        "check-json",
        "check-yaml",
        "check-ast",
        "black",
        "trailing-whitespace",
    ]

    results: Dict[str, Dict[str, Any]] = {}

    for config_name, config_file in [
        ("Full Config", ".pre-commit-config.yaml"),
        ("Fast Config", ".pre-commit-config-fast.yaml"),
    ]:
        if not Path(config_file).exists():
            print(f"⚠️  {config_file} not found, skipping...")
            continue

        print(f"\n📊 Testing {config_name} ({config_file})")
        print("-" * 30)

        total_time: float = 0.0
        hook_times = {}

        for hook in common_hooks:
            duration, _ = time_hook(hook, config_file)
            total_time += duration
            hook_times[hook] = duration

        results[config_name] = {"total_time": total_time, "hook_times": hook_times}

        print(f"🎯 Total time for {config_name}: {total_time:.2f}s")

    # Compare results
    if len(results) == 2:
        from typing import cast

        full_time = cast(float, results["Full Config"]["total_time"])
        fast_time = cast(float, results["Fast Config"]["total_time"])
        speedup = full_time / fast_time if fast_time > 0 else 0

        print("\n🚀 Performance Improvement:")
        print(f"  Full config: {full_time:.2f}s")
        print(f"  Fast config: {fast_time:.2f}s")
        print(f"  Speedup: {speedup:.1f}x faster")

    return results


def create_staged_only_hooks() -> None:
    """Create hooks that only run on staged files for maximum speed."""
    print("💡 Optimization Tips:")
    print("1. Use 'types_or' to limit file processing")
    print("2. Add 'files' patterns to target specific directories")
    print("3. Use 'exclude' to skip large directories")
    print("4. Consider 'pass_filenames: false' for whole-repo checks")


def main() -> int:
    """Execute optimization."""
    print("🎯 Pre-commit Performance Optimization")

    print("=" * 50)

    # Check if fast config exists
    if not Path(".pre-commit-config-fast.yaml").exists():
        print("❌ Fast config not found. Run this first:")
        print("   - Create .pre-commit-config-fast.yaml")
        return 1

    # Benchmark both configurations
    benchmark_configs()

    # Show optimization recommendations
    print("\n💡 Speed Optimization Recommendations:")
    print("=" * 40)
    print("1. Use fast config for local development:")
    print("   bash scripts/setup_fast_precommit.sh")
    print("")
    print("2. Run full checks before pushing:")
    print("   pre-commit run --all-files")
    print("")
    print("3. Use file-specific hooks when possible:")
    print("   pre-commit run --files app/core/auth.py")
    print("")
    print("4. Consider CI/CD for expensive checks (mypy, pylint)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
