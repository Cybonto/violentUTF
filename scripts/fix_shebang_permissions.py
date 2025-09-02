#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Automated script to fix shebang permissions for all files."""

import subprocess  # nosec B404 - needed for controlled git command execution
import sys
from pathlib import Path


def find_shebang_files() -> tuple[list, list]:
    """Find all files with shebangs that aren't executable"""
    shebang_files = []

    non_executable = []

    # Search common file extensions
    patterns = ["**/*.py", "**/*.sh", "**/*.pl", "**/*.rb"]

    for pattern in patterns:
        for file_path in Path(".").glob(pattern):
            path_str = str(file_path)
            # Skip common directories that shouldn't be tracked
            skip_dirs = [
                "node_modules",
                ".git",
                ".vitutf",
                "venv",
                ".venv",
                "__pycache__",
                ".mypy_cache",
            ]
            if any(skip_dir in path_str for skip_dir in skip_dirs):
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("#!"):
                        shebang_files.append(file_path)
                        # Check if executable
                        if not file_path.stat().st_mode & 0o111:
                            non_executable.append(file_path)
            except Exception:  # nosec B112 - acceptable exception handling

                continue
    return shebang_files, non_executable


def fix_permissions(files: list[Path]) -> tuple[list[Path], list[Path]]:
    """Fix permissions using git add --chmod=+x"""
    fixed = []

    failed = []

    # Process in batches to avoid command line length limits
    batch_size = 50
    for i in range(0, len(files), batch_size):
        batch = files[i : i + batch_size]
        file_paths = [str(f) for f in batch]

        try:
            subprocess.run(
                ["git", "add", "--chmod=+x"] + file_paths, check=True
            )  # nosec B603 B607 - controlled git command with validated file paths
            fixed.extend(batch)
            print(f"✅ Fixed {len(batch)} files in batch {i//batch_size + 1}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to fix batch {i//batch_size + 1}: {e}")
            failed.extend(batch)

    return fixed, failed


def main() -> int:
    """Run the shebang permission fixing process."""
    print("🔧 Finding files with shebangs that need executable permissions...")

    all_shebang, non_executable = find_shebang_files()

    print(f"📊 Found {len(all_shebang)} files with shebangs")
    print(f"🔧 {len(non_executable)} files need permission fixes")

    if not non_executable:
        print("🎉 All shebang files already have correct permissions!")
        return 0

    print(f"\n🔧 Fixing permissions for {len(non_executable)} files...")
    fixed, failed = fix_permissions(non_executable)

    print("\n📋 Results:")
    print(f"✅ Fixed: {len(fixed)} files")
    print(f"❌ Failed: {len(failed)} files")

    if failed:
        print("\n❌ Failed files:")
        for f in failed[:10]:  # Show first 10
            print(f"  {f}")
        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more")
        return 1

    print("🎉 All shebang permissions fixed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
