#!/usr/bin/env python3
# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Cross-platform test runner for ViolentUTF.

Specifically designed to work on Windows, macOS, and Linux.
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List


def find_requirements_files() -> List[str]:
    """Find all requirements*.txt files in the project."""
    req_files = []
    for root, _dirs, files in os.walk("."):
        # Skip virtual environment directories
        if "venv" in root or ".venv" in root or "env" in root:
            continue

        for file in files:
            if file.startswith("requirements") and file.endswith(".txt"):
                req_files.append(os.path.join(root, file))

    return req_files


def install_dependencies(req_files: List[str]) -> None:
    """Install dependencies from requirements files."""
    print("Installing test dependencies...")

    # Install core test dependencies first
    core_deps = ["pytest", "pytest-cov", "pytest-timeout", "pytest-xdist"]
    for dep in core_deps:
        subprocess.run([sys.executable, "-m", "pip", "install", dep], check=False)

    # Install from each requirements file with timeout
    for req_file in req_files:
        print(f"Installing from {req_file}")
        try:
            # Skip heavy ML dependencies in CI to avoid timeout
            # Filter out large packages that cause timeouts
            with open(req_file, "r") as f:
                lines = f.readlines()

            # Create temporary requirements file without heavy packages
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
                for line in lines:
                    # Skip heavy ML packages that cause timeouts in CI
                    if not any(
                        pkg in line.lower()
                        for pkg in ["torch", "transformers", "docling", "weasyprint", "sentence-transformers", "peft"]
                    ):
                        tmp.write(line)
                tmp_file = tmp.name

            # Install with timeout
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", tmp_file],
                check=False,
                timeout=180,  # 3 minutes timeout
                capture_output=True,
                text=True,
            )

            # Clean up temp file
            os.unlink(tmp_file)

            if result.returncode != 0:
                print(f"Warning: Some packages failed to install from {req_file}")
        except subprocess.TimeoutExpired:
            print(f"Warning: Installation timed out for {req_file}, continuing...")
        except Exception as e:
            print(f"Warning: Failed to install from {req_file}: {e}")


def find_test_files(test_dir: str = "tests/unit") -> List[str]:
    """Find Python test files in the specified directory."""
    test_files = []

    if os.path.isdir(test_dir):
        # Use pathlib for better cross-platform support
        test_path = Path(test_dir)
        py_files = list(test_path.rglob("*.py"))

        # Filter out __init__.py and non-test files
        test_files = [
            str(f)
            for f in py_files
            if f.name != "__init__.py" and (f.name.startswith("test_") or f.name.endswith("_test.py"))
        ]

    return test_files


def run_tests(test_dir: str = "tests/unit", coverage: bool = True, parallel: bool = True) -> int:
    """Run pytest with coverage reporting."""
    test_files = find_test_files(test_dir)

    if not test_files:
        print(f"Warning: No test files found in {test_dir}")
        create_empty_results()
        return 0

    print(f"Found {len(test_files)} test files in {test_dir}")

    # Build pytest command
    cmd = [sys.executable, "-m", "pytest", test_dir, "-v"]

    if coverage:
        cmd.extend(["--cov=violentutf", "--cov=violentutf_api", "--cov-report=xml", "--cov-report=term-missing"])

    cmd.extend(["--timeout=300"])

    if parallel:
        # Use number of CPUs for parallel execution
        cmd.extend(["-n", "auto"])

    # Add JUnit XML output
    cmd.extend(["--junit-xml=junit.xml"])

    print(f"Running command: {' '.join(cmd)}")

    # Run tests
    result = subprocess.run(cmd)

    return result.returncode


def create_empty_results() -> None:
    """Create empty test result files for CI compatibility."""
    print("Creating empty test results...")

    # Create minimal JUnit XML
    junit_xml = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
    <testsuite name="empty" tests="0" errors="0" failures="0" skipped="0">
        <testcase name="no_tests_found" classname="empty">
            <skipped message="No test files found"/>
        </testcase>
    </testsuite>
</testsuites>"""

    with open("junit.xml", "w", encoding="utf-8") as f:
        f.write(junit_xml)

    # Create minimal coverage XML
    coverage_xml = """<?xml version="1.0" encoding="utf-8"?>
<coverage version="1">
    <packages/>
</coverage>"""

    with open("coverage.xml", "w", encoding="utf-8") as f:
        f.write(coverage_xml)


def main() -> None:
    """Run the test suite."""
    parser = argparse.ArgumentParser(description="Cross-platform test runner for ViolentUTF")
    parser.add_argument("--test-dir", default="tests/unit", help="Directory containing tests")
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage reporting")
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel test execution")
    parser.add_argument("--install-deps", action="store_true", help="Install dependencies before running tests")

    args = parser.parse_args()

    # Change to project root if we're in scripts directory
    if os.path.basename(os.getcwd()) == "scripts":
        os.chdir("..")

    # Install dependencies if requested
    if args.install_deps:
        req_files = find_requirements_files()
        if req_files:
            install_dependencies(req_files)
        else:
            print("No requirements files found")

    # Run tests
    exit_code = run_tests(test_dir=args.test_dir, coverage=not args.no_coverage, parallel=not args.no_parallel)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
