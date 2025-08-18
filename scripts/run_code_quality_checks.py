#!/usr/bin/env python3
"""Run all code quality checks locally to match GitHub Actions.

This helps identify and fix issues before pushing to PR.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def run_command(
    cmd: str, description: str, continue_on_error: bool = False, capture_output: bool = False
) -> Tuple[bool, Optional[str]]:
    """Run a command and report results.

    Args:
        cmd: Command to execute
        description: Description of what the command does
        continue_on_error: Whether to continue on error
        capture_output: Whether to capture and return output

    Returns:
        Tuple of (success, output)
    """
    print(f"\n{BLUE}{BOLD}{'='*60}{RESET}")
    print(f"{BLUE}{BOLD}{description}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"Command: {cmd}")

    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"{GREEN}✓ {description} passed{RESET}")
                return True, result.stdout
            else:
                print(f"{RED}✗ {description} failed{RESET}")
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print(result.stderr)
                return False, result.stdout + result.stderr
        else:
            result = subprocess.run(cmd, shell=True)
            if result.returncode == 0:
                print(f"{GREEN}✓ {description} passed{RESET}")
                return True, None
            else:
                print(f"{RED}✗ {description} failed{RESET}")
                if not continue_on_error:
                    return False, None
                else:
                    print(f"{YELLOW}  (continuing despite error){RESET}")
                    return False, None
    except Exception as e:
        print(f"{RED}✗ Error running {description}: {e}{RESET}")
        return False, str(e)


def install_tools() -> bool:
    """Install required tools."""
    print(f"{BLUE}{BOLD}Installing required tools...{RESET}")
    tools = [
        "black",
        "isort",
        "flake8",
        "flake8-docstrings",
        "flake8-annotations",
        "bandit",
        "safety",
        "pylint",
        "mypy",
    ]

    cmd = f"pip install --upgrade {' '.join(tools)}"
    success, _ = run_command(cmd, "Tool installation")
    return success


def run_black_check() -> Tuple[bool, Optional[str]]:
    """Run Black formatter check."""
    return run_command("black --check --diff . --verbose", "Black formatter check")


def run_black_fix() -> Tuple[bool, Optional[str]]:
    """Run Black formatter to fix issues."""
    return run_command("black . --verbose", "Black formatter (fix mode)")


def run_isort_check() -> Tuple[bool, Optional[str]]:
    """Run isort import sorter check."""
    return run_command("isort --check-only --diff . --profile black", "isort import sorter check")


def run_isort_fix() -> Tuple[bool, Optional[str]]:
    """Run isort to fix import order."""
    return run_command("isort . --profile black", "isort import sorter (fix mode)")


def run_flake8() -> Tuple[bool, Optional[str]]:
    """Run flake8 linter."""
    return run_command("flake8 . --count --statistics --show-source", "Flake8 linter")


def run_pylint() -> Tuple[bool, Optional[str]]:
    """Run pylint on Python files."""
    # Note: This continues on error as per the workflow
    return run_command(
        'find . -name "*.py" -not -path "./tests/*" | xargs pylint --rcfile=.pylintrc || true',
        "Pylint",
        continue_on_error=True,
    )


def run_mypy() -> Tuple[bool, Optional[str]]:
    """Run mypy type checker."""
    # Note: This continues on error as per the workflow
    return run_command("mypy --install-types --non-interactive . || true", "MyPy type checker", continue_on_error=True)


def run_bandit() -> Tuple[bool, Optional[str]]:
    """Run Bandit security scanner."""
    success, _ = run_command(
        "bandit -r . -f json -o bandit-report.json", "Bandit security scanner", capture_output=True
    )

    # Parse and display results
    if os.path.exists("bandit-report.json"):
        with open("bandit-report.json", "r") as f:
            data = json.load(f)
            issues = data.get("results", [])

            print(f"\n{BOLD}Security scan results:{RESET}")
            print(f"Total security issues found: {len(issues)}")

            if issues:
                print(f"\n{YELLOW}Top security issues:{RESET}")
                for i, issue in enumerate(issues[:10]):
                    print(f"  {i+1}. {issue['test_name']}: {issue['filename']}:{issue['line_number']}")
                    print(f"     Severity: {issue['issue_severity']} | Confidence: {issue['issue_confidence']}")

                # Count by severity
                severity_counts = {}
                for issue in issues:
                    sev = issue["issue_severity"]
                    severity_counts[sev] = severity_counts.get(sev, 0) + 1

                print(f"\n{BOLD}Issues by severity:{RESET}")
                for sev, count in sorted(severity_counts.items()):
                    color = RED if sev == "HIGH" else YELLOW if sev == "MEDIUM" else ""
                    print(f"  {color}{sev}: {count}{RESET}")

    return success, None


def run_safety_check() -> Tuple[bool, Optional[str]]:
    """Run safety dependency scanner."""
    success, _ = run_command(
        "safety check --json --output safety-report.json || true",
        "Safety dependency check",
        continue_on_error=True,
        capture_output=True,
    )

    # Parse and display results
    if os.path.exists("safety-report.json"):
        with open("safety-report.json", "r") as f:
            data = json.load(f)
            vulns = data.get("vulnerabilities", [])

            print(f"\n{BOLD}Dependency vulnerability results:{RESET}")
            print(f"Vulnerable dependencies found: {len(vulns)}")

            if vulns:
                print(f"\n{RED}Vulnerable packages:{RESET}")
                for i, vuln in enumerate(vulns[:5]):
                    print(f"  {i+1}. {vuln['package_name']}=={vuln['analyzed_version']}")
                    print(f"     Vulnerability: {vuln.get('vulnerability_id', 'N/A')}")
                    print(f"     Severity: {vuln.get('severity', 'Unknown')}")

                if len(vulns) > 5:
                    print(f"  ... and {len(vulns) - 5} more")

    return success, None


def main() -> int:
    """Run all code quality checks and report results."""
    print(f"{BLUE}{BOLD}ViolentUTF Code Quality Check Runner{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print("This script runs the same checks as GitHub Actions locally.")
    print("You can fix issues before pushing to avoid CI failures.\n")

    # Check if we should fix or just check
    fix_mode = "--fix" in sys.argv

    if fix_mode:
        print(f"{YELLOW}{BOLD}Running in FIX mode - will automatically fix formatting issues{RESET}")
    else:
        print(f"{YELLOW}{BOLD}Running in CHECK mode - will only report issues{RESET}")
        print(f"{YELLOW}Run with --fix to automatically fix formatting issues{RESET}")

    # Install tools if requested
    if "--install" in sys.argv:
        if not install_tools():
            print(f"{RED}Failed to install tools. Exiting.{RESET}")
            sys.exit(1)

    # Track results
    results = {}

    # Run checks
    if fix_mode:
        # In fix mode, run fixers
        results["Black (fix)"] = run_black_fix()[0]
        results["isort (fix)"] = run_isort_fix()[0]
    else:
        # In check mode, just check
        results["Black"] = run_black_check()[0]
        results["isort"] = run_isort_check()[0]

    # These always run in check mode
    results["Flake8"] = run_flake8()[0]
    results["Pylint"] = run_pylint()[0]
    results["MyPy"] = run_mypy()[0]
    results["Bandit"] = run_bandit()[0]
    results["Safety"] = run_safety_check()[0]

    # Summary
    print(f"\n{BLUE}{BOLD}{'='*60}{RESET}")
    print(f"{BLUE}{BOLD}Summary{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    all_passed = True
    for check, passed in results.items():
        if passed:
            print(f"{GREEN}✓ {check}{RESET}")
        else:
            print(f"{RED}✗ {check}{RESET}")
            all_passed = False

    if all_passed:
        print(f"\n{GREEN}{BOLD}All checks passed! 🎉{RESET}")
        return 0
    else:
        print(f"\n{RED}{BOLD}Some checks failed.{RESET}")
        if not fix_mode:
            print(f"{YELLOW}Run with --fix to automatically fix formatting issues.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
