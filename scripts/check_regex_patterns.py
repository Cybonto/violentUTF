#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Validates that regex patterns haven't been corrupted by automated tools.

This script is designed to be run in CI/CD pipelines and pre-commit hooks.
"""

import re
import sys
from pathlib import Path
from typing import Any

# ANSI color codes for output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# Invalid patterns that indicate corruption
INVALID_PATTERNS = [
    # Regex patterns with spaces in character ranges
    (
        r"(?<![\w\]])\[[A-Za-z]+\s+-\s+[A-Za-z]+\]",
        "Spaces in character range (e.g., [A-Z])",
    ),
    (r"(?<![\w\]])\[[a-z]+\s+-\s+[a-z]+\]", "Spaces in lowercase range (e.g., [a-z])"),
    (r"(?<![\w\]])\[[A-Z]+\s+-\s+[A-Z]+\]", "Spaces in uppercase range (e.g., [A-Z])"),
    (r"(?<![\w\]])\[[0-9]+\s+-\s+[0-9]+\]", "Spaces in digit range (e.g., [0-9])"),
    # Content-Type strings with spaces (more specific patterns)
    (
        r'"(text|application|image|video|audio)\s+/\s+[^"]+"',
        "Spaces in quoted content type (should be no spaces)",
    ),
    (
        r"'(text|application|image|video|audio)\s+/\s+[^']+'",
        "Spaces in quoted content type (should be no spaces)",
    ),
    # Encoding strings with spaces
    (r'"utf\s+-\s+8"', "Spaces in UTF-8 string (should be utf-8)"),
    (r"'utf\s+-\s+8'", "Spaces in UTF-8 string (should be utf-8)"),
    (r'\.encode\(["\']utf\s+-\s+8["\']\)', "Spaces in encode() call"),
    (r'\.decode\(["\']utf\s+-\s+8["\']\)', "Spaces in decode() call"),
]

# Files or patterns to exclude from checking
EXCLUDE_PATTERNS = [
    "__pycache__",
    ".git",
    ".pytest_cache",
    "node_modules",
    "venv",
    ".env",
    "*.pyc",
    "*.pyo",
    "*.log",
]


def should_check_file(filepath: str) -> bool:
    """Determine if a file should be checked."""
    path = Path(filepath)

    # Check exclusions
    for pattern in EXCLUDE_PATTERNS:
        if pattern in str(path):
            return False

    # Only check Python files
    return path.suffix == ".py"


def check_file(filepath: str) -> list[dict[str, Any] | str]:
    """Check a file for corrupted regex patterns."""
    errors: list[dict[str, Any] | str] = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return [f"Error reading {filepath}: {e}"]

    # Check each line for issues
    lines = content.split("\n")
    for line_num, line in enumerate(lines, 1):
        # Skip comments and docstrings
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        # Check for invalid patterns
        for pattern, description in INVALID_PATTERNS:
            matches = re.findall(pattern, line)
            if matches:
                errors.append(
                    {
                        "file": filepath,
                        "line": line_num,
                        "pattern": matches[0],
                        "description": description,
                        "content": line.strip(),
                    }
                )

    return errors


def main(files: list[str]) -> int:
    """Check files for corrupted regex patterns."""
    all_errors = []
    files_checked = 0

    for filepath in files:
        if should_check_file(filepath):
            files_checked += 1
            errors = check_file(filepath)
            all_errors.extend(errors)

    # Report results
    if all_errors:
        print(f"{RED}❌ Regex Pattern Validation Failed{RESET}")
        print(f"\nFound {len(all_errors)} issue(s) in {files_checked} file(s):\n")

        # Group errors by file
        errors_by_file: dict[str, list] = {}
        for error in all_errors:
            if isinstance(error, dict):
                file = error["file"]
                if file not in errors_by_file:
                    errors_by_file[file] = []
                errors_by_file[file].append(error)
            else:
                print(f"  {error}")

        # Print grouped errors
        for file, file_errors in errors_by_file.items():
            print(f"{YELLOW}📄 {file}:{RESET}")
            for error in file_errors:
                if isinstance(error, dict):
                    print(f"  Line {error['line']}: {error['description']}")
                    print(f"    Found: {error['pattern']}")
                    print(f"    Code: {error['content'][:80]}...")
                print()

        print(f"{RED}Please fix these issues before committing.{RESET}")
        print("\nCommon fixes:")
        print("  - Remove spaces in character ranges: [A-Z]")
        print("  - Remove spaces in digit ranges: [0-9]")
        print("  - Remove spaces in content types: text/plain")
        print("  - Remove spaces in encoding: utf-8")

        return 1
    else:
        print(f"{GREEN}✅ All regex patterns are valid{RESET}")
        print(f"Checked {files_checked} Python file(s)")
        return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_regex_patterns.py <file1> [file2] ...")
        print("Or: find . -name '*.py' -type f | xargs python check_regex_patterns.py")
        sys.exit(1)

    exit_code = main(sys.argv[1:])
    sys.exit(exit_code)
