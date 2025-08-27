#!/usr/bin/env python3
"""
Diagnose formatting differences between local and CI environment.
"""

import os
import subprocess  # nosec B404 - needed for code quality checks
import sys


def run_command(cmd) -> str:
    """Run a command and return output."""
    try:
        # Convert string command to list for safer execution without shell=True
        if isinstance(cmd, str):
            import shlex

            cmd = shlex.split(cmd)
        result = subprocess.run(cmd, capture_output=True, text=True)  # nosec B603 - controlled input
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"


def main() -> None:
    print("=== Formatting Diagnostics ===\n")

    # Check versions
    print("1. Tool Versions:")
    print(f"Python: {sys.version}")
    print(f"Black: {run_command('black --version').strip()}")
    print(f"isort: {run_command('isort --version').strip()}")

    # Check configuration
    print("\n2. Configuration Files:")
    config_files = ["pyproject.toml", ".black", "setup.cfg", ".flake8"]
    for cf in config_files:
        if os.path.exists(cf):
            print(f"✓ Found {cf}")
        else:
            print(f"✗ Missing {cf}")

    # Check specific files mentioned in PR
    print("\n3. Checking specific files from PR #50:")
    problem_files = [
        "violentutf/pages/3_Configure_Converters.py",
        "violentutf/pages/1_Configure_Generators.py",
        "violentutf/pages/4_Configure_Scorers.py",
        "violentutf/pages/IronUTF.py",
    ]

    for pf in problem_files:
        if os.path.exists(pf):
            # Check if Black would change it
            result = run_command(f'black --check --diff "{pf}"')
            if "would be reformatted" in result:
                print(f"✗ {pf} - needs formatting")
                print(f"  Changes: {result[:200]}...")
            else:
                print(f"✓ {pf} - properly formatted")

            # Check file encoding
            with open(pf, "rb") as f:
                first_bytes = f.read(3)
                if first_bytes == b"\xef\xbb\xbf":
                    print(f"  ⚠️  Has UTF-8 BOM")

            # Check line endings
            with open(pf, "rb") as f:
                content = f.read()
                if b"\r\n" in content:
                    print(f"  ⚠️  Has CRLF line endings")
                elif b"\r" in content:
                    print(f"  ⚠️  Has CR line endings")
        else:
            print(f"✗ {pf} - file not found")

    # Check for any files Black would change
    print("\n4. Running Black check on all Python files:")
    result = run_command("black --check violentutf/ violentutf_api/ tests/ 2>&1")
    if "would be reformatted" in result:
        print("✗ Some files need formatting:")
        print(result)
    else:
        print("✓ All files properly formatted")

    # Check git status
    print("\n5. Git Status:")
    print(run_command("git status --porcelain"))

    # Check for mixed line endings
    print("\n6. Checking for line ending issues:")
    result = run_command('git ls-files -z | xargs -0 file | grep -E "CRLF|CR" | head -10')
    if result.strip():
        print("Files with non-LF line endings:")
        print(result)
    else:
        print("✓ No line ending issues found")


if __name__ == "__main__":
    main()
