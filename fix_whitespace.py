#!/usr/bin/env python3
"""Fix W293 whitespace issues - blank lines with whitespace"""

import os
import re


def fix_whitespace(file_path):
    """Remove trailing whitespace from blank lines"""
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()

        # Remove trailing whitespace from each line
        fixed_lines = []
        for line in lines:
            # If line is only whitespace, make it empty
            if line.strip() == "":
                fixed_lines.append("\n")
            else:
                # Remove trailing whitespace but keep the newline
                fixed_lines.append(line.rstrip() + "\n" if line.endswith("\n") else line.rstrip())

        # Write back the fixed content
        with open(file_path, "w") as f:
            f.writelines(fixed_lines)

        return True
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


# Get all Python files with W293 issues
import subprocess

result = subprocess.run(["flake8", ".", "--select=W293"], capture_output=True, text=True)
files_with_issues = set()

for line in result.stdout.split("\n"):
    if line and "agent_orchestrator" not in line:
        # Extract file path from flake8 output
        parts = line.split(":")
        if len(parts) >= 2:
            file_path = parts[0]
            if file_path.endswith(".py"):
                files_with_issues.add(file_path)

print(f"Found {len(files_with_issues)} files with W293 issues")

# Fix each file
fixed_count = 0
for file_path in files_with_issues:
    if fix_whitespace(file_path):
        fixed_count += 1
        print(f"Fixed {file_path}")

print(f"Fixed {fixed_count} files")
