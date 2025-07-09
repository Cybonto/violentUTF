#!/usr/bin/env python3
"""
Dynamic OpenAPI schema generation from FastAPI app.
Generates OpenAPI schemas for contract testing and validation.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_test_environment():
    """Setup environment for schema generation."""
    os.environ.update(
        {
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
    )


def generate_openapi_schema(output_file: str = "generated_openapi.json") -> bool:
    """Generate OpenAPI schema from FastAPI app."""
    try:
        setup_test_environment()

        # Import with authentication mocking
        from tests.api_tests.test_auth_mock import ContractTestingPatches

        with ContractTestingPatches():
            logger.info("Importing FastAPI app...")
            from violentutf_api.fastapi_app.app.main import app

            logger.info("Generating OpenAPI schema...")
            schema = app.openapi()

            # Enhance schema with ViolentUTF-specific metadata
            schema = enhance_schema_metadata(schema)

            # Write schema to file
            output_path = Path(output_file)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)

            logger.info(f"OpenAPI schema generated successfully: {output_path}")

            # Validate the generated schema
            return validate_generated_schema(schema)

    except ImportError as e:
        logger.error(f"Could not import FastAPI app: {e}")
        return create_minimal_schema(output_file)
    except Exception as e:
        logger.error(f"Error generating OpenAPI schema: {e}")
        return create_minimal_schema(output_file)


def enhance_schema_metadata(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Enhance OpenAPI schema with ViolentUTF-specific metadata."""
    # Update info section
    schema["info"].update(
        {
            "title": "ViolentUTF API",
            "description": "AI Red-teaming Platform API with enterprise authentication",
            "version": "1.0.0",
            "contact": {"name": "ViolentUTF API Support", "url": "https://github.com/Cybonto/violentUTF"},
            "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        }
    )

    # Add servers
    schema["servers"] = [
        {"url": "http://localhost:9080", "description": "APISIX Gateway (Production)"},
        {"url": "http://localhost:8000", "description": "FastAPI Direct (Development)"},
    ]

    # Add security schemes
    if "components" not in schema:
        schema["components"] = {}
    if "securitySchemes" not in schema["components"]:
        schema["components"]["securitySchemes"] = {}

    schema["components"]["securitySchemes"].update(
        {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token from Keycloak authentication",
            },
            "apiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "apikey",
                "description": "API key for APISIX gateway access",
            },
        }
    )

    # Add global security
    schema["security"] = [{"bearerAuth": []}, {"apiKeyAuth": []}]

    # Add common error response schemas
    if "schemas" not in schema["components"]:
        schema["components"]["schemas"] = {}

    schema["components"]["schemas"].update(
        {
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "detail": {"type": "string", "description": "Error message"},
                    "error": {"type": "string", "description": "Error type"},
                    "status_code": {"type": "integer", "description": "HTTP status code"},
                },
                "required": ["detail"],
            },
            "HealthResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["healthy", "unhealthy"]},
                    "version": {"type": "string"},
                    "timestamp": {"type": "string", "format": "date-time"},
                },
                "required": ["status"],
            },
        }
    )

    return schema


def validate_generated_schema(schema: Dict[str, Any]) -> bool:
    """Validate the generated OpenAPI schema."""
    try:
        from tests.api_tests.validate_openapi_schemas import OpenAPIValidator

        validator = OpenAPIValidator()
        if validator._validate_schema_dict(schema, "generated schema"):
            logger.info("Generated schema validation passed")
            return True
        else:
            logger.error("Generated schema validation failed")
            for error in validator.errors:
                logger.error(f"  - {error}")
            return False

    except ImportError:
        logger.warning("Could not import OpenAPI validator, skipping validation")
        return True
    except Exception as e:
        logger.error(f"Error validating generated schema: {e}")
        return False


def create_minimal_schema(output_file: str) -> bool:
    """Create minimal OpenAPI schema as fallback."""
    logger.info("Creating minimal OpenAPI schema as fallback...")

    minimal_schema = {
        "openapi": "3.0.0",
        "info": {
            "title": "ViolentUTF API",
            "version": "1.0.0",
            "description": "AI Red-teaming Platform API (Minimal Schema)",
        },
        "servers": [{"url": "http://localhost:9080", "description": "APISIX Gateway"}],
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health Check",
                    "operationId": "health_check",
                    "responses": {
                        "200": {
                            "description": "Health status",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object", "properties": {"status": {"type": "string"}}}
                                }
                            },
                        }
                    },
                }
            },
            "/api/v1/generators": {
                "get": {
                    "summary": "List Generators",
                    "operationId": "list_generators",
                    "responses": {
                        "200": {
                            "description": "List of generators",
                            "content": {"application/json": {"schema": {"type": "array", "items": {"type": "object"}}}},
                        }
                    },
                }
            },
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
                "apiKeyAuth": {"type": "apiKey", "in": "header", "name": "apikey"},
            }
        },
        "security": [{"bearerAuth": []}, {"apiKeyAuth": []}],
    }

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(minimal_schema, f, indent=2, ensure_ascii=False)

        logger.info(f"Minimal OpenAPI schema created: {output_file}")
        return True

    except Exception as e:
        logger.error(f"Error creating minimal schema: {e}")
        return False


def main():
    """Main function for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate OpenAPI schema for ViolentUTF API")
    parser.add_argument("--output", default="generated_openapi.json", help="Output file for generated schema")
    parser.add_argument("--validate", action="store_true", help="Validate generated schema")

    args = parser.parse_args()

    # Generate schema
    success = generate_openapi_schema(args.output)

    if success and args.validate:
        # Additional validation
        try:
            from tests.api_tests.validate_openapi_schemas import OpenAPIValidator

            validator = OpenAPIValidator()
            if validator.validate_schema_file(Path(args.output)):
                logger.info("✅ Schema validation passed")
            else:
                logger.error("❌ Schema validation failed")
                validator.print_results()
                sys.exit(1)
        except ImportError:
            logger.warning("OpenAPI validator not available")

    if success:
        logger.info("✅ OpenAPI schema generation completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ OpenAPI schema generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
