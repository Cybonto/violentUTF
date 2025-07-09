#!/usr/bin/env python3
"""
Emergency fix script for corrupted regex patterns.
This script can automatically fix common regex pattern corruptions.
"""
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

# Pattern fixes - order matters!
PATTERN_FIXES = [
    # Character range fixes
    (r"\[([A-Za-z0-9])\s+-\s+([A-Za-z0-9])\]", r"[\1-\2]", "Fix character range spaces"),
    (r"\[([a-z])\s+-\s+([a-z])\]", r"[\1-\2]", "Fix lowercase range spaces"),
    (r"\[([A-Z])\s+-\s+([A-Z])\]", r"[\1-\2]", "Fix uppercase range spaces"),
    (r"\[([0-9])\s+-\s+([0-9])\]", r"[\1-\2]", "Fix digit range spaces"),
    # More complex character class fixes
    (r"\[([A-Za-z0-9._%-]+)\s+-\s+([A-Za-z0-9._%-]+)\]", r"[\1-\2]", "Fix complex character range"),
    # Content-Type fixes
    (r'"(text|application|image|video|audio)\s+/\s+([^"]+)"', r'"\1/\2"', "Fix content-type in double quotes"),
    (r"'(text|application|image|video|audio)\s+/\s+([^']+)'", r"'\1/\2'", "Fix content-type in single quotes"),
    # UTF-8 encoding fixes
    (r'"utf\s+-\s+8"', r'"utf-8"', "Fix UTF-8 in double quotes"),
    (r"'utf\s+-\s+8'", r"'utf-8'", "Fix UTF-8 in single quotes"),
    (r'\.encode\((["\'])utf\s+-\s+8\1\)', r".encode(\1utf-8\1)", "Fix UTF-8 in encode()"),
    (r'\.decode\((["\'])utf\s+-\s+8\1\)', r".decode(\1utf-8\1)", "Fix UTF-8 in decode()"),
    # Fix other common MIME types
    (r'"text\s+/\s+csv"', r'"text/csv"', "Fix text/csv"),
    (r'"text\s+/\s+plain"', r'"text/plain"', "Fix text/plain"),
    (r'"text\s+/\s+html"', r'"text/html"', "Fix text/html"),
    (r'"application\s+/\s+json"', r'"application/json"', "Fix application/json"),
    (r'"application\s+/\s+x\s+-\s+yaml"', r'"application/x-yaml"', "Fix application/x-yaml"),
    (r'"text\s+/\s+yaml"', r'"text/yaml"', "Fix text/yaml"),
    (r'"text\s+/\s+tab\s+-\s+separated\s+-\s+values"', r'"text/tab-separated-values"', "Fix TSV content type"),
]

# Known good patterns for validation
KNOWN_GOOD_PATTERNS = {
    "JWT_TOKEN": r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$",
    "USERNAME": r"^[a-zA-Z0-9_-]+$",
    "EMAIL": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    "SAFE_IDENTIFIER": r"^[a-zA-Z0-9_-]+$",
}


def create_backup(filepath):
    """Create a backup of the file before fixing."""
    backup_path = f"{filepath}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    return backup_path


def fix_file(filepath, dry_run=False):
    """Fix regex patterns in a file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            original_content = f.read()
    except Exception as e:
        print(f"{RED}Error reading {filepath}: {e}{RESET}")
        return False, []

    content = original_content
    fixes_applied = []

    # Apply each fix pattern
    for pattern, replacement, description in PATTERN_FIXES:
        matches = re.findall(pattern, content)
        if matches:
            if not dry_run:
                content = re.sub(pattern, replacement, content)
            fixes_applied.append(
                {"description": description, "count": len(matches), "examples": matches[:3]}  # Show first 3 examples
            )

    # Check if any fixes were applied
    if not fixes_applied:
        return False, []

    # Write the fixed content
    if not dry_run:
        # Create backup first
        backup_path = create_backup(filepath)
        print(f"  {BLUE}Created backup: {backup_path}{RESET}")

        # Write fixed content
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    return True, fixes_applied


def validate_common_patterns(filepath):
    """Validate that common patterns match known good patterns."""
    warnings = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except:
        return warnings

    # Check for common pattern definitions
    for pattern_name, known_good in KNOWN_GOOD_PATTERNS.items():
        # Look for pattern definitions
        pattern_match = re.search(rf'{pattern_name}\s*=\s*re\.compile\(r["\']([^"\']+)["\']\)', content)
        if pattern_match:
            found_pattern = pattern_match.group(1)
            if found_pattern != known_good:
                warnings.append(f"Pattern {pattern_name} doesn't match known good pattern")

    return warnings


def main(files, dry_run=False):
    """Main function to fix files."""
    print(f"{YELLOW}{'DRY RUN - ' if dry_run else ''}Regex Pattern Fix Tool{RESET}")
    print("=" * 60)

    total_fixes = 0
    files_fixed = 0

    for filepath in files:
        if not filepath.endswith(".py"):
            continue

        fixed, fixes = fix_file(filepath, dry_run)

        if fixed:
            files_fixed += 1
            print(f"\n{GREEN}✓ {'Would fix' if dry_run else 'Fixed'} {filepath}{RESET}")
            for fix in fixes:
                total_fixes += fix["count"]
                print(f"  - {fix['description']}: {fix['count']} occurrence(s)")
                for example in fix["examples"]:
                    print(f"    Example: {example}")

        # Validate patterns
        warnings = validate_common_patterns(filepath)
        if warnings:
            print(f"{YELLOW}  Warnings:{RESET}")
            for warning in warnings:
                print(f"    - {warning}")

    # Summary
    print(f"\n{'-' * 60}")
    if total_fixes > 0:
        print(f"{GREEN}{'Would fix' if dry_run else 'Fixed'} {total_fixes} pattern(s) in {files_fixed} file(s){RESET}")
        if dry_run:
            print(f"\n{YELLOW}Run without --dry-run to apply fixes{RESET}")
    else:
        print(f"{GREEN}No fixes needed!{RESET}")

    return 0 if total_fixes == 0 else (0 if not dry_run else 1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix corrupted regex patterns")
    parser.add_argument("files", nargs="+", help="Files to fix")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fixed without making changes")

    args = parser.parse_args()

    exit_code = main(args.files, args.dry_run)
    sys.exit(exit_code)
