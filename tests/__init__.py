# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
ViolentUTF Testing Suite.

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
