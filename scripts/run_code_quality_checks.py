#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.


"""Run all code quality checks locally to match GitHub Actions.

This helps identify and fix issues before pushing to PR.
"""

import json
import os
import subprocess  # nosec B404 - needed for code quality checks
import sys
from pathlib import Path
from typing import Optional, Union

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def run_command(
    cmd: Union[str, list[str]],
    description: str,
    continue_on_error: bool = False,
    capture_output: bool = False,
) -> tuple[bool, Optional[str]]:
    """Run a command and report results."""
    print(f"\n{BLUE}{BOLD}{'='*60}{RESET}")

    print(f"{BLUE}{BOLD}{description}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"Command: {cmd}")

    try:
        if capture_output:
            # Convert string command to list for safer execution without shell=True
            if isinstance(cmd, str):
                import shlex

                cmd = shlex.split(cmd)
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)  # nosec B603 - controlled input
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
            # Convert string command to list for safer execution without shell=True
            if isinstance(cmd, str):
                import shlex

                cmd = shlex.split(cmd)
            result = subprocess.run(cmd, text=True, check=False)  # nosec B603 - controlled input
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
    except (subprocess.SubprocessError, OSError) as e:
        print(f"{RED}✗ Process error running {description}: {e}{RESET}")
        return False, str(e)
    except (ValueError, TypeError) as e:
        print(f"{RED}✗ Unexpected error running {description}: {e}{RESET}")
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


def run_black_check() -> tuple[bool, Optional[str]]:
    """Run Black formatter check."""
    return run_command("black --check --diff . --verbose", "Black formatter check")


def run_black_fix() -> tuple[bool, Optional[str]]:
    """Run Black formatter to fix issues."""
    return run_command("black . --verbose", "Black formatter (fix mode)")


def run_isort_check() -> tuple[bool, Optional[str]]:
    """Run isort import sorter check."""
    return run_command("isort --check-only --diff . --profile black", "isort import sorter check")


def run_isort_fix() -> tuple[bool, Optional[str]]:
    """Run isort to fix import order."""
    return run_command("isort . --profile black", "isort import sorter (fix mode)")


def run_flake8() -> tuple[bool, Optional[str]]:
    """Run flake8 linter."""
    return run_command("flake8 . --count --statistics --show-source", "Flake8 linter")


def run_pylint() -> tuple[bool, Optional[str]]:
    """Run pylint on Python files."""
    # Note: This continues on error as per the workflow

    return run_command(
        'find . -name "*.py" -not -path "./tests/*" | xargs pylint --rcfile=.pylintrc || true',
        "Pylint",
        continue_on_error=True,
    )


def run_mypy() -> tuple[bool, Optional[str]]:
    """Run mypy type checker."""
    # Note: This continues on error as per the workflow

    return run_command(
        "mypy --install-types --non-interactive . || true",
        "MyPy type checker",
        continue_on_error=True,
    )


def run_bandit() -> tuple[bool, Optional[str]]:
    """Run Bandit security scanner."""
    success, _ = run_command(
        "bandit -r . -f json -o bandit-report.json",
        "Bandit security scanner",
        capture_output=True,
    )

    # Parse and display results
    if os.path.exists("bandit-report.json"):
        with open("bandit-report.json", "r", encoding="utf-8") as f:
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
                severity_counts: dict[str, int] = {}
                for issue in issues:
                    sev = issue["issue_severity"]
                    severity_counts[sev] = severity_counts.get(sev, 0) + 1

                print(f"\n{BOLD}Issues by severity:{RESET}")
                for sev, count in sorted(severity_counts.items()):
                    color = RED if sev == "HIGH" else YELLOW if sev == "MEDIUM" else ""
                    print(f"  {color}{sev}: {count}{RESET}")

    return success, None


def run_safety_check() -> tuple[bool, Optional[str]]:
    """Run safety dependency scanner."""
    success, _ = run_command(
        "safety check --save-json safety-report.json",
        "Safety dependency check",
        continue_on_error=True,
        capture_output=True,
    )

    # Parse and display results
    if os.path.exists("safety-report.json"):
        with open("safety-report.json", "r", encoding="utf-8") as f:
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


def run_pytest() -> tuple[bool, Optional[str]]:
    """Run pytest unit tests (matches GitHub PR quick-test job)."""
    success, output = run_command(
        "pytest tests/unit -v -m 'not slow' -x --tb=short --maxfail=5 -n auto --no-header --no-summary -q",
        "Pytest unit tests (GitHub PR equivalent)",
        continue_on_error=True,
        capture_output=True,
    )

    # Check if tests exist
    if not os.path.exists("tests/unit"):
        print(f"{YELLOW}No tests/unit directory found, skipping pytest{RESET}")
        return True, None

    # Count test files
    test_files = []
    if os.path.exists("tests/unit"):
        for _, _, files in os.walk("tests/unit"):
            test_files.extend([f for f in files if f.startswith("test_") and f.endswith(".py")])

    if not test_files:
        print(f"{YELLOW}No test files found in tests/unit/, skipping pytest{RESET}")
        return True, None

    print(f"\n{BOLD}Test execution results:{RESET}")
    print(f"Found {len(test_files)} test files")

    if output and "FAILED" not in output:
        print(f"{GREEN}All unit tests passed{RESET}")
    elif output and "FAILED" in output:
        print(f"{RED}Some unit tests failed{RESET}")
        # Show failed test summary
        failed_lines = [line for line in output.split("\n") if "FAILED" in line]
        if failed_lines:
            print(f"\n{YELLOW}Failed tests:{RESET}")
            for line in failed_lines[:5]:  # Show first 5 failures
                print(f"  {line}")
            if len(failed_lines) > 5:
                print(f"  ... and {len(failed_lines) - 5} more")

    return success, output


def run_docker_validation() -> tuple[bool, Optional[str]]:
    """Run Docker validation (matches GitHub PR docker-lint job)."""
    docker_success = True

    output_parts = []

    # Check if Docker files exist

    dockerfiles = list(Path(".").glob("**/Dockerfile*"))
    compose_files = list(Path(".").glob("**/docker-compose*.yml")) + list(Path(".").glob("**/docker-compose*.yaml"))

    if not dockerfiles and not compose_files:
        print(f"{YELLOW}No Docker files found, skipping Docker validation{RESET}")
        return True, None

    print(f"\n{BLUE}{BOLD}Docker Validation{RESET}")
    print(f"Found {len(dockerfiles)} Dockerfile(s) and {len(compose_files)} Docker Compose file(s)")

    # Validate Docker Compose files (we can do this without Hadolint)
    if compose_files:
        print(f"\n{BOLD}Validating Docker Compose files:{RESET}")
        for compose_file in compose_files:
            try:
                # Check if file contains actual services or just comments
                with open(compose_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    # Skip files that are just comments/documentation
                    non_comment_lines = [
                        line.strip()
                        for line in content.split("\n")
                        if line.strip() and not line.strip().startswith("#")
                    ]
                    if not non_comment_lines:
                        print(f"{YELLOW}⚠ {compose_file}: Documentation/comment file only{RESET}")
                        continue

                result = subprocess.run(  # nosec B603 B607 - controlled docker-compose validation
                    ["docker-compose", "-f", str(compose_file), "config"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                if result.returncode == 0:
                    print(f"{GREEN}✓ {compose_file}{RESET}")
                else:
                    print(f"{RED}✗ {compose_file}: {result.stderr.strip()}{RESET}")
                    docker_success = False
                    output_parts.append(f"Docker Compose validation failed for {compose_file}")
            except subprocess.TimeoutExpired:
                print(f"{RED}✗ {compose_file}: Validation timeout{RESET}")
                docker_success = False
            except FileNotFoundError:
                print(f"{YELLOW}⚠ docker-compose not found in PATH, skipping compose validation{RESET}")
                break

    # Basic Dockerfile syntax check (without Hadolint)
    if dockerfiles:
        print(f"\n{BOLD}Basic Dockerfile validation:{RESET}")
        for dockerfile in dockerfiles:
            try:
                # Basic syntax check - ensure it starts with FROM
                with open(dockerfile, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        print(f"{RED}✗ {dockerfile}: Empty file{RESET}")
                        docker_success = False
                    elif not any(line.strip().upper().startswith("FROM ") for line in content.split("\n")):
                        print(f"{RED}✗ {dockerfile}: No FROM instruction found{RESET}")
                        docker_success = False
                    else:
                        print(f"{GREEN}✓ {dockerfile}: Basic syntax OK{RESET}")
            except (OSError, ValueError, TypeError) as e:
                print(f"{RED}✗ {dockerfile}: {str(e)}{RESET}")
                docker_success = False

    output_text = "; ".join(output_parts) if output_parts else None
    return docker_success, output_text


def run_trivy_scan() -> tuple[bool, Optional[str]]:
    """Run Trivy security scan (matches GitHub PR security-scan job)."""
    # Check if trivy is available

    try:
        result = subprocess.run(
            ["trivy", "--version"], capture_output=True, timeout=10, check=False
        )  # nosec B603 B607 - controlled version check
        if result.returncode != 0:
            print(
                f"{YELLOW}Trivy not installed. Install with: "
                f"curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | "
                f"sh -s -- -b /usr/local/bin{RESET}"
            )
            return True, "Trivy not available"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print(f"{YELLOW}Trivy not found. This is optional but recommended for security scanning.{RESET}")
        print(
            f"{YELLOW}Install with: brew install trivy  # or "
            f"curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh{RESET}"
        )
        return True, "Trivy not available"

    success, output = run_command(
        "trivy fs --severity CRITICAL,HIGH --format table --quiet .",
        "Trivy security scan (GitHub PR equivalent)",
        continue_on_error=True,
        capture_output=True,
    )

    if output and "Total:" in output:
        # Parse trivy output for summary
        lines = output.split("\n")
        summary_lines = [line for line in lines if "Total:" in line or "Critical:" in line or "High:" in line]
        if summary_lines:
            print(f"\n{BOLD}Security scan summary:{RESET}")
            for line in summary_lines:
                if "Critical:" in line and not line.endswith(": 0"):
                    print(f"{RED}{line}{RESET}")
                elif "High:" in line and not line.endswith(": 0"):
                    print(f"{YELLOW}{line}{RESET}")
                else:
                    print(line)

    return success, output


def main() -> int:
    """Run all quality checks."""
    print(f"{BLUE}{BOLD}ViolentUTF Code Quality Check Runner{RESET}")

    print(f"{BLUE}{'='*60}{RESET}")
    print("This script runs the same checks as GitHub Actions locally.")
    print("You can fix issues before pushing to avoid CI failures.\n")

    # Check command line options
    fix_mode = "--fix" in sys.argv
    github_mode = "--github" in sys.argv
    comprehensive_mode = "--comprehensive" in sys.argv or not github_mode

    if github_mode:
        print(f"{YELLOW}{BOLD}Running in GITHUB mode - matches online PR validation exactly{RESET}")
        print("This includes: Black, isort, Flake8, Pytest, Docker validation, and Trivy security scan")
    elif comprehensive_mode:
        print(f"{YELLOW}{BOLD}Running in COMPREHENSIVE mode - includes extra checks beyond GitHub{RESET}")
        print("This includes: All GitHub checks + MyPy, Pylint, Bandit, and Safety dependency scanning")

    if fix_mode:
        print(f"{YELLOW}{BOLD}AUTO-FIX enabled - will automatically fix formatting issues{RESET}")
    else:
        print(f"{YELLOW}Run with --fix to automatically fix formatting issues{RESET}")

    print(f"\n{CYAN}Available modes:{RESET}")
    print("  --github          Match GitHub PR validation exactly")
    print("  --comprehensive   Full comprehensive checks (default)")
    print("  --fix             Auto-fix formatting issues")
    print("  --install         Install missing tools")

    # Install tools if requested
    if "--install" in sys.argv:
        if not install_tools():
            print(f"{RED}Failed to install tools. Exiting.{RESET}")
            sys.exit(1)

    # Track results
    results = {}

    # === CORE FORMATTING CHECKS (both modes) ===
    if fix_mode:
        # In fix mode, run fixers
        results["Black (fix)"] = run_black_fix()[0]
        results["isort (fix)"] = run_isort_fix()[0]
    else:
        # In check mode, just check
        results["Black"] = run_black_check()[0]
        results["isort"] = run_isort_check()[0]

    # === LINTING (both modes) ===
    results["Flake8"] = run_flake8()[0]

    # === GITHUB PR SPECIFIC CHECKS ===
    if github_mode or comprehensive_mode:
        results["Pytest Unit Tests"] = run_pytest()[0]
        results["Docker Validation"] = run_docker_validation()[0]
        results["Trivy Security Scan"] = run_trivy_scan()[0]

    # === COMPREHENSIVE MODE EXTRAS ===
    if comprehensive_mode:
        results["Pylint"] = run_pylint()[0]
        results["MyPy"] = run_mypy()[0]
        results["Bandit"] = run_bandit()[0]
        results["Safety"] = run_safety_check()[0]

    # Summary
    print(f"\n{BLUE}{BOLD}{'='*60}{RESET}")
    mode_text = "GitHub PR" if github_mode else "Comprehensive"
    print(f"{BLUE}{BOLD}Summary - {mode_text} Mode{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")

    all_passed = True
    failed_checks = []
    passed_checks = []

    for check, passed in results.items():
        if passed:
            print(f"{GREEN}✓ {check}{RESET}")
            passed_checks.append(check)
        else:
            print(f"{RED}✗ {check}{RESET}")
            failed_checks.append(check)
            all_passed = False

    print(f"\n{BOLD}Results: {len(passed_checks)} passed, {len(failed_checks)} failed{RESET}")

    if all_passed:
        print(f"\n{GREEN}{BOLD}🎉 All checks passed!{RESET}")
        if github_mode:
            print(f"{GREEN}Your code will pass GitHub PR validation!{RESET}")
        else:
            print(f"{GREEN}Your code meets comprehensive quality standards!{RESET}")
        return 0
    else:
        print(f"\n{RED}{BOLD}Some checks failed:{RESET}")
        for check in failed_checks:
            print(f"  • {check}")

        if not fix_mode:
            print(f"\n{YELLOW}💡 Run with --fix to automatically fix formatting issues{RESET}")

        if github_mode:
            print(f"\n{RED}❌ Your PR will likely fail GitHub validation{RESET}")
        else:
            print(f"\n{YELLOW}⚠️  Fix these issues before creating a PR{RESET}")

        return 1


if __name__ == "__main__":
    sys.exit(main())
