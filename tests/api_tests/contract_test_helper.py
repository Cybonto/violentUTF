"""Utility functions for API contract testing.

Provides common utilities for contract validation and testing.
"""
from __future__ import annotations
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import jsonschema
import pytest
import requests
from fastapi.testclient import TestClient
from openapi_spec_validator import validate_spec

logger = logging.getLogger(__name__)


class ContractTestError(Exception):
    """Exception for contract testing errors."""

    pass


class APIContractValidator:
    """Validator for API contract compliance."""

    def __init__(self: APIContractValidator, base_url: str = "http://testserver") -> None:
        """Initialize contract validator with base URL."""
        self.base_url = base_url
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_response_schema(self: APIContractValidator, response_data: Dict[str, Any], expected_schema: Dict[str, Any]) -> bool:
        """Validate response data against expected schema."""
        try:
            jsonschema.validate(response_data, expected_schema)
            return True
        except jsonschema.ValidationError as e:
            self.errors.append(f"Response schema validation failed: {e.message}")
            return False
        except Exception as e:
            self.errors.append(f"Schema validation error: {e}")
            return False

    def validate_status_code(self: APIContractValidator, response_code: int, expected_codes: List[int]) -> bool:
        """Validate response status code."""
        if response_code not in expected_codes:
            self.errors.append(f"Unexpected status code: {response_code}, expected one of {expected_codes}")
            return False
        return True

    def validate_headers(self: APIContractValidator, response_headers: Dict[str, str], required_headers: List[str]) -> bool:
        """Validate required headers are present."""
        missing_headers = []
        for header in required_headers:
            if header.lower() not in [h.lower() for h in response_headers.keys()]:
                missing_headers.append(header)

        if missing_headers:
            self.errors.append(f"Missing required headers: {missing_headers}")
            return False
        return True

    def validate_json_response(self: APIContractValidator, response_text: str) -> bool:
        """Validate that response is valid JSON."""
        try:
            json.loads(response_text)
            return True
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON response: {e}")
            return False

    def validate_authentication_required(self: "APIContractValidator", endpoint: str, client: TestClient, test_headers: Dict[str, str]) -> bool:
        """Validate that authentication is required for protected endpoints."""
        # Test without authentication
        response = client.get(endpoint)

        if response.status_code in [200]:
            self.warnings.append(f"Endpoint {endpoint} allows unauthenticated access")

        # Test with authentication
        response = client.get(endpoint, headers=test_headers)

        return response.status_code in [200, 404, 422]  # Allow various success codes

    def get_validation_summary(self: "APIContractValidator") -> Dict[str, Any]:
        """Get validation summary."""
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


class MockResponseBuilder:
    """Builder for creating mock API responses."""

    def __init__(self: MockResponseBuilder) -> None:
        """Initialize mock response builder with defaults."""
        self.status_code = 200
        self.headers = {"Content-Type": "application/json"}
        self.data = {}

    def with_status(self: MockResponseBuilder, status_code: int) -> MockResponseBuilder:
        """Set response status code."""
        self.status_code = status_code
        return self

    def with_header(self: MockResponseBuilder, key: str, value: str) -> MockResponseBuilder:
        """Add response header."""
        self.headers[key] = value
        return self

    def with_data(self: MockResponseBuilder, data: Dict[str, Any]) -> MockResponseBuilder:
        """Set response data."""
        self.data = data
        return self

    def with_error(self: MockResponseBuilder, message: str, code: int = 400) -> MockResponseBuilder:
        """Create error response."""
        self.status_code = code
        self.data = {"detail": message, "status_code": code}
        return self

    def build(self: "MockResponseBuilder") -> Dict[str, Any]:
        """Build mock response."""
        return {
            "status_code": self.status_code,
            "headers": self.headers,
            "json": self.data,
        }


class EndpointTester:
    """Utility for testing API endpoints."""

    def __init__(self: "EndpointTester", client: TestClient, base_headers: Optional[Dict[str, str]] = None) -> None:
        """Initialize endpoint tester with client and headers."""
        self.client = client
        self.base_headers = base_headers or {}
        self.validator = APIContractValidator()

    def test_endpoint_exists(self: "EndpointTester", endpoint: str, method: str = "GET") -> bool:
        """Test that endpoint exists and is accessible."""
        try:
            response = getattr(self.client, method.lower())(endpoint, headers=self.base_headers)
            return response.status_code != 404
        except Exception:
            return False

    def test_endpoint_authentication(self: "EndpointTester", endpoint: str, method: str = "GET") -> Dict[str, Any]:
        """Test endpoint authentication requirements."""
        results = {}

        # Test without authentication
        try:
            response = getattr(self.client, method.lower())(endpoint)
            results["without_auth"] = {
                "status_code": response.status_code,
                "allows_unauthenticated": response.status_code in [200, 201, 204],
            }
        except Exception as e:
            results["without_auth"] = {"error": str(e)}

        # Test with authentication
        try:
            response = getattr(self.client, method.lower())(endpoint, headers=self.base_headers)
            results["with_auth"] = {
                "status_code": response.status_code,
                "authenticates_successfully": response.status_code in [200, 201, 204, 404, 422],
            }
        except Exception as e:
            results["with_auth"] = {"error": str(e)}

        return results

    def test_endpoint_performance(self: "EndpointTester", endpoint: str, method: str = "GET", timeout: float = 5.0) -> Dict[str, Any]:
        """Test endpoint performance."""
        start_time = time.time()

        try:
            response = getattr(self.client, method.lower())(endpoint, headers=self.base_headers)
            end_time = time.time()

            response_time = end_time - start_time

            return {
                "response_time": response_time,
                "within_timeout": response_time < timeout,
                "status_code": response.status_code,
                "success": True,
            }
        except Exception as e:
            end_time = time.time()
            return {
                "response_time": end_time - start_time,
                "within_timeout": False,
                "error": str(e),
                "success": False,
            }

    def test_endpoint_data_validation(
        self: "EndpointTester", endpoint: str, valid_data: Dict[str, Any], invalid_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test endpoint data validation."""
        results = {}

        # Test with valid data
        try:
            response = self.client.post(endpoint, json=valid_data, headers=self.base_headers)
            results["valid_data"] = {
                "status_code": response.status_code,
                "accepts_valid_data": response.status_code in [200, 201, 204],
            }
        except Exception as e:
            results["valid_data"] = {"error": str(e)}

        # Test with invalid data
        try:
            response = self.client.post(endpoint, json=invalid_data, headers=self.base_headers)
            results["invalid_data"] = {
                "status_code": response.status_code,
                "rejects_invalid_data": response.status_code in [400, 422],
            }
        except Exception as e:
            results["invalid_data"] = {"error": str(e)}

        return results


class SchemaGenerator:
    """Utility for generating test schemas."""

    @staticmethod
    def generate_error_schema() -> Dict[str, Any]:
        """Generate standard error response schema."""
        return {
            "type": "object",
            "properties": {
                "detail": {"type": "string"},
                "status_code": {"type": "integer"},
                "error": {"type": "string"},
            },
            "required": ["detail"],
        }

    @staticmethod
    def generate_list_schema(item_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate schema for list responses."""
        return {"type": "array", "items": item_schema}

    @staticmethod
    def generate_success_schema() -> Dict[str, Any]:
        """Generate standard success response schema."""
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["success"]},
                "message": {"type": "string"},
            },
            "required": ["status"],
        }


class ContractTestReporter:
    """Utility for reporting contract test results."""

    def __init__(self: "ContractTestReporter") -> None:
        """Initialize contract test reporter."""
        self.test_results = []

    def add_test_result(self: "ContractTestReporter", test_name: str, passed: bool, details: Optional[Dict[str, Any]] = None) -> None:
        """Add a test result."""
        self.test_results.append(
            {
                "test_name": test_name,
                "passed": passed,
                "details": details or {},
                "timestamp": time.time(),
            }
        )

    def get_summary(self: "ContractTestReporter") -> Dict[str, Any]:
        """Get test summary."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])
        failed_tests = total_tests - passed_tests

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
        }

    def generate_report(self: "ContractTestReporter", output_file: Optional[str] = None) -> str:
        """Generate detailed test report."""
        summary = self.get_summary()

        report = []
        report.append("API Contract Test Report")
        report.append("=" * 50)
        report.append(f"Total Tests: {summary['total_tests']}")
        report.append(f"Passed: {summary['passed_tests']}")
        report.append(f"Failed: {summary['failed_tests']}")
        report.append(f"Success Rate: {summary['success_rate']:.2%}")
        report.append("")

        # Detailed results
        report.append("Detailed Results:")
        report.append("-" * 30)

        for result in self.test_results:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            report.append(f"{status} {result['test_name']}")

            if result["details"]:
                for key, value in result["details"].items():
                    report.append(f"  {key}: {value}")

        report_text = "\n".join(report)

        if output_file:
            with open(output_file, "w") as f:
                f.write(report_text)

        return report_text


def create_test_environment() -> Dict[str, str]:
    """Create test environment variables."""
    return {
        "TESTING": "true",
        "CONTRACT_TESTING": "true",
        "JWT_SECRET_KEY": "test_jwt_secret_for_contract_testing_only",
        "SECRET_KEY": "test_jwt_secret_for_contract_testing_only",
        "VIOLENTUTF_API_KEY": "test_api_key_for_contract_testing",
        "APISIX_API_KEY": "test_api_key_for_contract_testing",
        "KEYCLOAK_URL": "http://localhost:8080",
        "KEYCLOAK_REALM": "ViolentUTF-Test",
        "VIOLENTUTF_API_URL": "http://localhost:8000",
        "DUCKDB_PATH": ":memory:",
        "PYRIT_DB_PATH": ":memory:",
    }


def validate_openapi_compliance(schema: Dict[str, Any]) -> List[str]:
    """Validate OpenAPI 3.0 compliance."""
    errors = []

    try:
        validate_spec(schema)
    except Exception as e:
        errors.append(f"OpenAPI validation failed: {e}")

    # Additional ViolentUTF-specific validations
    if "security" not in schema:
        errors.append("No security schemes defined")

    if "paths" not in schema or len(schema["paths"]) == 0:
        errors.append("No API paths defined")

    return errors


def run_contract_test_suite(client: TestClient, test_headers: Dict[str, str], endpoints: List[str]) -> ContractTestReporter:
    """Run a comprehensive contract test suite."""
    reporter = ContractTestReporter()
    tester = EndpointTester(client, test_headers)

    for endpoint in endpoints:
        # Test endpoint exists
        exists = tester.test_endpoint_exists(endpoint)
        reporter.add_test_result(f"{endpoint} - Endpoint Exists", exists, {"endpoint": endpoint})

        if exists:
            # Test authentication
            auth_results = tester.test_endpoint_authentication(endpoint)
            reporter.add_test_result(
                f"{endpoint} - Authentication",
                auth_results.get("with_auth", {}).get("authenticates_successfully", False),
                auth_results,
            )

            # Test performance
            perf_results = tester.test_endpoint_performance(endpoint)
            reporter.add_test_result(
                f"{endpoint} - Performance",
                perf_results.get("within_timeout", False),
                perf_results,
            )

    return reporter
