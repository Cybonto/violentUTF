#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Test runner for Asset Management System (Issue #280).

This script runs the comprehensive test suite for the asset management system
and generates coverage reports to verify the 90% minimum coverage requirement.
"""

import sys
import subprocess
import os
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {description} failed with exit code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def main():
    """Run the comprehensive test suite for asset management."""
    print("Asset Management System - Comprehensive Test Suite")
    print("Issue #280 - Testing for 90% minimum code coverage")
    
    # Change to the FastAPI app directory
    fastapi_dir = Path(__file__).parent.parent
    os.chdir(fastapi_dir)
    print(f"Working directory: {os.getcwd()}")
    
    # Test commands to run
    test_commands = [
        # Install test dependencies
        {
            "cmd": [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            "description": "Installing requirements"
        },
        {
            "cmd": [sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio", "pytest-cov", "coverage"],
            "description": "Installing test dependencies"
        },
        
        # Run individual test modules
        {
            "cmd": [sys.executable, "-m", "pytest", "tests/conftest.py", "-v", "--tb=short"],
            "description": "Testing configuration and fixtures"
        },
        {
            "cmd": [sys.executable, "-m", "pytest", "tests/test_models.py", "-v", "--tb=short"],
            "description": "Testing database models"
        },
        {
            "cmd": [sys.executable, "-m", "pytest", "tests/test_asset_service.py", "-v", "--tb=short"],
            "description": "Testing AssetService"
        },
        {
            "cmd": [sys.executable, "-m", "pytest", "tests/test_validation_service.py", "-v", "--tb=short"],
            "description": "Testing ValidationService"
        },
        {
            "cmd": [sys.executable, "-m", "pytest", "tests/test_conflict_resolution_service.py", "-v", "--tb=short"],
            "description": "Testing ConflictResolutionService"
        },
        {
            "cmd": [sys.executable, "-m", "pytest", "tests/test_audit_service.py", "-v", "--tb=short"],
            "description": "Testing AuditService"
        },
        {
            "cmd": [sys.executable, "-m", "pytest", "tests/test_discovery_integration_service.py", "-v", "--tb=short"],
            "description": "Testing DiscoveryIntegrationService"
        },
        {
            "cmd": [sys.executable, "-m", "pytest", "tests/test_api_integration.py", "-v", "--tb=short"],
            "description": "Testing API integration"
        },
        {
            "cmd": [sys.executable, "-m", "pytest", "tests/test_migrations.py", "-v", "--tb=short"],
            "description": "Testing database migrations"
        },
        {
            "cmd": [sys.executable, "-m", "pytest", "tests/test_performance.py", "-v", "--tb=short", "-m", "not slow"],
            "description": "Testing performance (quick tests only)"
        },
        
        # Run comprehensive test suite with coverage
        {
            "cmd": [
                sys.executable, "-m", "pytest",
                "tests/test_models.py",
                "tests/test_asset_service.py", 
                "tests/test_validation_service.py",
                "tests/test_conflict_resolution_service.py",
                "tests/test_audit_service.py",
                "tests/test_discovery_integration_service.py",
                "tests/test_api_integration.py",
                "tests/test_migrations.py",
                "--cov=app/models/asset_inventory",
                "--cov=app/services/asset_management",
                "--cov=app/api/v1/assets",
                "--cov=app/schemas/asset_schemas",
                "--cov-report=html:htmlcov",
                "--cov-report=term-missing",
                "--cov-report=xml",
                "--cov-fail-under=90",
                "-v"
            ],
            "description": "Running comprehensive test suite with coverage analysis"
        },
        
        # Generate coverage report summary
        {
            "cmd": [sys.executable, "-m", "coverage", "report", "--show-missing"],
            "description": "Generating coverage report summary"
        }
    ]
    
    # Track results
    passed_tests = 0
    failed_tests = 0
    
    # Run all test commands
    for test_cmd in test_commands:
        success = run_command(test_cmd["cmd"], test_cmd["description"])
        if success:
            passed_tests += 1
        else:
            failed_tests += 1
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST EXECUTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total test commands: {len(test_commands)}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! Asset Management System ready for production.")
        print("\nKey achievements:")
        print("✅ Comprehensive test suite implemented")
        print("✅ 90% minimum code coverage achieved")  
        print("✅ All service layer components tested")
        print("✅ API integration tests passing")
        print("✅ Database migration tests passing")
        print("✅ Performance requirements validated")
        
        # Check if coverage reports were generated
        coverage_files = [
            "htmlcov/index.html",
            "coverage.xml",
            ".coverage"
        ]
        
        print("\nCoverage reports generated:")
        for coverage_file in coverage_files:
            if os.path.exists(coverage_file):
                print(f"✅ {coverage_file}")
            else:
                print(f"❌ {coverage_file} (not found)")
        
        return 0
    else:
        print(f"\n❌ {failed_tests} test command(s) failed. Please review the errors above.")
        print("\nNext steps:")
        print("1. Review failed test output")
        print("2. Fix any issues in the codebase") 
        print("3. Re-run tests to verify fixes")
        print("4. Ensure 90% code coverage is achieved")
        
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)