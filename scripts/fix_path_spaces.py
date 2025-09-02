#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Fix directory paths with spaces that cause Windows CI failures.

This script renames directories with spaces to use underscores.
"""

import os
import shutil
import sys


def find_paths_with_spaces(root_dir: str = ".") -> list[tuple[str, str]]:
    """Find all paths containing spaces."""
    paths_with_spaces = []

    for root, dirs, files in os.walk(root_dir):
        # Skip git and virtual environment directories
        if ".git" in root or "venv" in root or ".venv" in root:
            continue

        # Check directories
        for dirname in dirs:
            if " " in dirname:
                full_path = os.path.join(root, dirname)
                paths_with_spaces.append(("dir", full_path))

        # Check files
        for filename in files:
            if " " in filename:
                full_path = os.path.join(root, filename)
                paths_with_spaces.append(("file", full_path))

    return paths_with_spaces


def fix_path_spaces(dry_run: bool = False) -> None:
    """Fix paths with spaces by replacing them with underscores."""
    paths = find_paths_with_spaces()

    if not paths:
        print("No paths with spaces found.")
        return

    print(f"Found {len(paths)} paths with spaces:")

    # Sort by path depth (deepest first) to avoid parent/child conflicts
    paths.sort(key=lambda x: x[1].count(os.sep), reverse=True)

    for path_type, path in paths:
        new_path = path.replace(" ", "_")
        print(f"\n{path_type.upper()}: {path}")
        print(f"  -> {new_path}")

        if not dry_run:
            try:
                if os.path.exists(path):
                    # Create parent directory if needed
                    parent_dir = os.path.dirname(new_path)
                    if parent_dir and not os.path.exists(parent_dir):
                        os.makedirs(parent_dir, exist_ok=True)

                    # Move the file/directory
                    shutil.move(path, new_path)
                    print("  ✓ Fixed")
                else:
                    print("  ⚠ Path no longer exists, skipping")
            except Exception as e:
                print(f"  ✗ Error: {e}")
        else:
            print("  (dry run - no changes made)")


def main() -> None:
    """Run the path space fixing process."""
    print("Path Space Fixer for ViolentUTF")

    print("=" * 50)

    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if dry_run:
        print("Running in DRY RUN mode - no changes will be made\n")
    else:
        print("Running in FIX mode - paths will be renamed\n")
        response = input("Are you sure you want to rename paths? (y/N): ")
        if response.lower() != "y":
            print("Aborted.")
            return

    fix_path_spaces(dry_run=dry_run)

    print("\nDone!")

    if dry_run:
        print("\nTo apply fixes, run without --dry-run flag")


if __name__ == "__main__":
    main()
