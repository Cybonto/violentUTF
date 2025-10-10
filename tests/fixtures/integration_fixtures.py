# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Integration Test Fixtures

This module provides test fixtures for integration testing in the ViolentUTF
end-to-end testing framework.

SECURITY: All test data is for defensive security research only.
"""

from typing import Any, Dict, List


def create_integration_test_data() -> Dict[str, Any]:
    """
    Create integration test data fixtures for end-to-end testing.
    
    Returns test data for validating integration between different
    ViolentUTF platform components and services.
    """
    return {
        "service_endpoints": {
            "keycloak": {
                "base_url": "http://localhost:8080",
                "realm": "violentutf",
                "client_id": "violentutf-client",
                "test_endpoints": [
                    "/auth/realms/violentutf/protocol/openid-connect/auth",
                    "/auth/realms/violentutf/protocol/openid-connect/token",
                    "/auth/realms/violentutf/protocol/openid-connect/userinfo"
                ]
            },
            "apisix_gateway": {
                "base_url": "http://localhost:9080",
                "admin_url": "http://localhost:9001",
                "test_endpoints": [
                    "/api/v1/datasets",
                    "/api/v1/converters",
                    "/api/v1/evaluations",
                    "/health"
                ]
            },
            "fastapi_backend": {
                "base_url": "http://localhost:8000",
                "test_endpoints": [
                    "/health",
                    "/api/v1/datasets/list",
                    "/api/v1/converters/status",
                    "/api/v1/evaluations/results"
                ]
            },
            "streamlit_frontend": {
                "base_url": "http://localhost:8501",
                "test_pages": [
                    "/",
                    "Configure_Datasets",
                    "Configure_Converters",
                    "Dashboard"
                ]
            },
            "mcp_server": {
                "base_url": "http://localhost:9080/mcp/sse",
                "protocol": "json-rpc-2.0-over-sse",
                "test_endpoints": [
                    "/mcp/sse",
                    "/mcp/tools/list",
                    "/mcp/resources/list"
                ]
            }
        },
        "integration_test_scenarios": {
            "authentication_flow_integration": {
                "scenario_description": "Complete authentication flow across all services",
                "test_steps": [
                    "user_initiates_login_via_streamlit",
                    "streamlit_redirects_to_keycloak",
                    "keycloak_authenticates_user",
                    "jwt_token_issued_and_stored",
                    "token_validated_by_apisix_gateway",
                    "authenticated_requests_to_fastapi_backend"
                ],
                "expected_outcome": "seamless_authentication_across_all_services",
                "failure_scenarios": [
                    "keycloak_service_unavailable",
                    "token_validation_failure",
                    "gateway_authentication_rejection"
                ]
            },
            "dataset_operation_integration": {
                "scenario_description": "Complete dataset operation across all components",
                "test_steps": [
                    "user_selects_dataset_via_streamlit",
                    "request_routed_through_apisix_gateway",
                    "fastapi_processes_dataset_request",
                    "dataset_stored_in_duckdb",
                    "pyrit_orchestrator_initialized",
                    "results_displayed_in_streamlit"
                ],
                "expected_outcome": "complete_dataset_operation_workflow",
                "failure_scenarios": [
                    "gateway_routing_failure",
                    "database_connection_failure",
                    "orchestrator_initialization_failure"
                ]
            },
            "mcp_protocol_integration": {
                "scenario_description": "MCP protocol integration across all services",
                "test_steps": [
                    "mcp_server_tool_registration",
                    "mcp_client_tool_discovery",
                    "tool_execution_via_mcp_protocol",
                    "results_propagation_through_services",
                    "ui_update_with_mcp_results"
                ],
                "expected_outcome": "seamless_mcp_protocol_integration",
                "failure_scenarios": [
                    "mcp_server_unavailable",
                    "tool_registration_failure",
                    "protocol_communication_error"
                ]
            }
        },
        "component_dependencies": {
            "keycloak_dependencies": {
                "required_services": ["postgresql_keycloak"],
                "dependent_services": ["apisix_gateway", "streamlit_frontend"],
                "health_check_endpoint": "/auth/realms/violentutf/.well-known/openid-configuration"
            },
            "apisix_dependencies": {
                "required_services": ["etcd", "keycloak"],
                "dependent_services": ["streamlit_frontend"],
                "upstream_services": ["fastapi_backend"],
                "health_check_endpoint": "/health"
            },
            "fastapi_dependencies": {
                "required_services": ["duckdb", "pyrit_framework"],
                "dependent_services": ["apisix_gateway"],
                "health_check_endpoint": "/health"
            },
            "streamlit_dependencies": {
                "required_services": ["apisix_gateway", "keycloak"],
                "health_check_method": "http_status_check"
            },
            "mcp_server_dependencies": {
                "required_services": ["fastapi_backend"],
                "protocol_requirements": ["sse_support", "json_rpc_2.0"],
                "health_check_endpoint": "/mcp/sse"
            }
        },
        "integration_validation_criteria": {
            "service_communication": {
                "max_inter_service_latency_ms": 100,
                "max_request_timeout_seconds": 30,
                "required_success_rate": 0.99
            },
            "data_consistency": {
                "cross_service_data_synchronization": "eventual_consistency",
                "max_synchronization_delay_seconds": 5,
                "data_integrity_validation": "checksum_based"
            },
            "error_propagation": {
                "error_handling_strategy": "graceful_degradation",
                "error_recovery_time_seconds": 60,
                "user_notification_requirements": "user_friendly_messages"
            },
            "performance_integration": {
                "end_to_end_response_time_seconds": 5,
                "concurrent_user_capacity": 10,
                "resource_sharing_efficiency": 0.8
            }
        }
    }


def create_mock_service_responses() -> Dict[str, Any]:
    """
    Create mock service responses for integration testing.
    
    Returns mock responses that simulate real service interactions
    for testing integration scenarios.
    """
    return {
        "keycloak_mock_responses": {
            "token_endpoint_success": {
                "access_token": "mock_access_token_12345",
                "refresh_token": "mock_refresh_token_67890", 
                "token_type": "Bearer",
                "expires_in": 3600
            },
            "userinfo_endpoint_success": {
                "sub": "test_user_id",
                "preferred_username": "test_security_researcher",
                "email": "test@violentutf.com",
                "roles": ["security_analyst"]
            },
            "authentication_failure": {
                "error": "invalid_grant",
                "error_description": "Invalid user credentials"
            }
        },
        "fastapi_mock_responses": {
            "dataset_list_success": {
                "datasets": [
                    {"id": "garak_001", "name": "Garak Security Dataset", "type": "security_evaluation"},
                    {"id": "ollegen1_001", "name": "OllaGen1 Cognitive Dataset", "type": "cognitive_evaluation"}
                ],
                "total_count": 2,
                "status": "success"
            },
            "conversion_status_success": {
                "conversion_id": "conv_12345",
                "status": "in_progress",
                "progress_percent": 45,
                "estimated_completion_time": 120
            },
            "health_check_success": {
                "status": "healthy",
                "timestamp": "2025-01-09T10:00:00Z",
                "services": {
                    "database": "healthy",
                    "pyrit_integration": "healthy",
                    "mcp_server": "healthy"
                }
            }
        },
        "mcp_mock_responses": {
            "tools_list_success": {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "tools": [
                        {"name": "dataset_converter_tool", "description": "Convert datasets to PyRIT format"},
                        {"name": "evaluation_orchestrator_tool", "description": "Orchestrate dataset evaluations"}
                    ]
                }
            },
            "tool_execution_success": {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "execution_id": "exec_789",
                    "status": "completed",
                    "result_data": {"conversion_successful": True, "records_processed": 1500}
                }
            }
        }
    }