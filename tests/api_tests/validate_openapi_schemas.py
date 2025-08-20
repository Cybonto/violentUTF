#!/usr/bin/env python3
# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Enhanced OpenAPI schema validation for API contract testing.
Validates OpenAPI 3.0 specifications and ensures compatibility.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema
import requests
from openapi_spec_validator import validate_spec
from openapi_spec_validator.exceptions import OpenAPIValidationError

logger = logging.getLogger(__name__)

# OpenAPI 3.0 Schema for validation
OPENAPI_3_0_SCHEMA = {
    "type": "object",
    "required": ["openapi", "info", "paths"],
    "properties": {
        "openapi": {"type": "string", "pattern": "^3\\.0\\.[0-9]+(\\.[0-9]+)*$"},
        "info": {
            "type": "object",
            "required": ["title", "version"],
            "properties": {
                "title": {"type": "string"},
                "version": {"type": "string"},
                "description": {"type": "string"},
                "contact": {"type": "object"},
                "license": {"type": "object"},
            },
        },
        "paths": {"type": "object", "patternProperties": {"^/": {"type": "object"}}},
        "components": {"type": "object"},
        "security": {"type": "array"},
        "servers": {"type": "array"},
    },
}


class OpenAPIValidator:
    """Enhanced OpenAPI schema validator for contract testing."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_schema_file(self, schema_path: Path) -> bool:
        """Validate OpenAPI schema file."""
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)

            return self._validate_schema_dict(schema, str(schema_path))

        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON in {schema_path}: {e}")
            return False
        except FileNotFoundError:
            self.errors.append(f"Schema file not found: {schema_path}")
            return False
        except Exception as e:
            self.errors.append(f"Error reading {schema_path}: {e}")
            return False

    def validate_dynamic_schema(self, app_url: str = None) -> bool:
        """Validate dynamically generated OpenAPI schema from FastAPI app."""
        if not app_url:
            app_url = f"{self.base_url}/openapi.json"

        try:
            response = requests.get(app_url, timeout=10)
            response.raise_for_status()

            schema = response.json()
            return self._validate_schema_dict(schema, f"dynamic schema from {app_url}")

        except requests.RequestException as e:
            self.errors.append(f"Failed to fetch dynamic schema from {app_url}: {e}")
            return False
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON in dynamic schema: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Error validating dynamic schema: {e}")
            return False

    def _validate_schema_dict(self, schema: Dict[str, Any], source: str) -> bool:
        """Validate OpenAPI schema dictionary."""
        success = True

        # Basic structure validation
        try:
            jsonschema.validate(schema, OPENAPI_3_0_SCHEMA)
        except jsonschema.ValidationError as e:
            self.errors.append(f"Schema structure validation failed for {source}: {e.message}")
            success = False

        # OpenAPI 3.0 specification validation
        try:
            validate_spec(schema)
        except OpenAPIValidationError as e:
            self.errors.append(f"OpenAPI 3.0 validation failed for {source}: {e}")
            success = False
        except Exception as e:
            self.errors.append(f"OpenAPI validation error for {source}: {e}")
            success = False

        # Additional ViolentUTF-specific validations
        if success:
            success = self._validate_violentutf_specific(schema, source)

        return success

    def _validate_violentutf_specific(self, schema: Dict[str, Any], source: str) -> bool:
        """Validate ViolentUTF-specific API contract requirements."""
        success = True

        # Check for required authentication schemes
        components = schema.get("components", {})
        security_schemes = components.get("securitySchemes", {})

        expected_auth_schemes = ["bearerAuth", "apiKeyAuth"]
        for scheme in expected_auth_schemes:
            if scheme not in security_schemes:
                self.warnings.append(f"Missing expected security scheme '{scheme}' in {source}")

        # Check for required API endpoints
        paths = schema.get("paths", {})
        required_endpoints = [
            "/api/v1/generators",
            "/api/v1/scorers",
            "/api/v1/orchestrators",
            "/api/v1/datasets",
            "/api/v1/converters",
        ]

        for endpoint in required_endpoints:
            if endpoint not in paths:
                self.warnings.append(f"Missing expected endpoint '{endpoint}' in {source}")

        # Check for health check endpoint
        if "/health" not in paths and "/api/v1/health" not in paths:
            self.warnings.append(f"Missing health check endpoint in {source}")

        # Validate error response schemas
        if not self._validate_error_responses(schema, source):
            success = False

        return success

    def _validate_error_responses(self, schema: Dict[str, Any], source: str) -> bool:
        """Validate that error responses follow consistent format."""
        paths = schema.get("paths", {})

        for path, path_obj in paths.items():
            for method, method_obj in path_obj.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    responses = method_obj.get("responses", {})

                    # Check for error response codes
                    error_codes = ["400", "401", "403", "404", "422", "500"]
                    for code in error_codes:
                        if code in responses:
                            response_schema = (
                                responses[code].get("content", {}).get("application/json", {}).get("schema", {})
                            )

                            # Validate error response structure
                            if not self._is_valid_error_schema(response_schema):
                                self.errors.append(
                                    f"Invalid error response schema for {method.upper()} {path} {code} in {source}"
                                )
                                return False

        return True

    def _is_valid_error_schema(self, schema: Dict[str, Any]) -> bool:
        """Check if error response schema follows expected format."""
        if not schema:
            return True  # No schema defined is acceptable

        # Expected error response should have detail field
        properties = schema.get("properties", {})
        return "detail" in properties or "message" in properties or "error" in properties

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of validation results."""
        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }

    def print_results(self):
        """Print validation results to console."""
        if not self.errors and not self.warnings:
            print("✅ All OpenAPI schemas are valid!")
            return

        if self.errors:
            print("❌ Validation Errors:")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings:
            print("⚠️  Validation Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")

        print(f"\nSummary: {len(self.errors)} errors, {len(self.warnings)} warnings")


def main():
    """Main validation function for CLI usage."""
    logging.basicConfig(level=logging.INFO)

    validator = OpenAPIValidator()
    success = True

    # Find and validate all OpenAPI schema files
    schema_files = list(Path(".").glob("**/openapi*.json"))
    schema_files.extend(list(Path(".").glob("**/swagger*.json")))

    if schema_files:
        print(f"Found {len(schema_files)} schema files to validate...")
        for schema_file in schema_files:
            print(f"Validating {schema_file}...")
            if not validator.validate_schema_file(schema_file):
                success = False
    else:
        print("No static schema files found.")

    # Try to validate dynamic schema from FastAPI app
    print("Attempting to validate dynamic schema from FastAPI app...")
    if not validator.validate_dynamic_schema():
        print("Dynamic schema validation failed, but continuing...")

    # Print results
    validator.print_results()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
