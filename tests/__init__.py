# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
ViolentUTF Testing Suite

This package contains comprehensive tests for the ViolentUTF API system,
including unit tests, integration tests, and endpoint verification.

Test Categories:
- Unit Tests: Direct FastAPI testing with mocked dependencies
- Integration Tests: Full APISIX Gateway routing validation
- Endpoint Tests: Page-specific endpoint verification
- System Tests: Complete workflow validation

Usage:
    # Run all tests
    ./run_tests.sh

    # Run specific test categories
    python3 -m pytest test_unit_api_endpoints.py -v
    python3 -m pytest test_apisix_integration.py -v
    python3 test_start_page_endpoints.py
"""

__version__ = "1.0.0"
__author__ = "ViolentUTF Team"
