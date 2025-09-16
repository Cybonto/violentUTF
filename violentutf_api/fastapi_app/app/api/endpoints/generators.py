# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""FastAPI endpoints for generator management.

Implements API backend for 1_Configure_Generators.py page
SECURITY: Enhanced with secure error handling to prevent information disclosure
"""
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

import httpx
import requests
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.error_handling import safe_error_response, validation_error
from app.db.duckdb_manager import get_duckdb_manager
from app.models.auth import User
from app.schemas.generators import (
    APIXModelsResponse,
    GeneratorCreateRequest,
    GeneratorDeleteResponse,
    GeneratorInfo,
    GeneratorParameter,
    GeneratorParametersResponse,
    GeneratorsListResponse,
    GeneratorTypesResponse,
    GeneratorUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_apisix_endpoint_for_model(provider: str, model: str) -> Optional[str]:
    """Map AI provider and model to APISIX endpoint path.

    Based on the setup_macos.sh AI proxy route configuration
    """
    # OpenAI model mappings

    if provider == "openai":
        openai_mappings = {
            "gpt-4": "/ai/openai/gpt4",
            "gpt-3.5-turbo": "/ai/openai/gpt35",
            "gpt-4-turbo": "/ai/openai/gpt4-turbo",
            "gpt-4o": "/ai/openai/gpt4o",
            "gpt-4o-mini": "/ai/openai/gpt4o-mini",
            "gpt-4.1": "/ai/openai/gpt41",
            "gpt-4.1-mini": "/ai/openai/gpt41-mini",
            "gpt-4.1-nano": "/ai/openai/gpt41-nano",
            "o1-preview": "/ai/openai/o1-preview",
            "o1-mini": "/ai/openai/o1-mini",
            "o3-mini": "/ai/openai/o3-mini",
            "o4-mini": "/ai/openai/o4-mini",
        }
        return openai_mappings.get(model)

    # Anthropic model mappings
    elif provider == "anthropic":
        anthropic_mappings = {
            "claude-3-opus-20240229": "/ai/anthropic/claude3-opus",
            "claude-3-sonnet-20240229": "/ai/anthropic/claude3-sonnet",
            "claude-3-haiku-20240307": "/ai/anthropic/claude3-haiku",
            "claude-3-5-sonnet-20241022": "/ai/anthropic/claude35-sonnet",
            "claude-3-5-haiku-20241022": "/ai/anthropic/claude35-haiku",
            "claude-3-7-sonnet-latest": "/ai/anthropic/sonnet37",
            "claude-sonnet-4-20250514": "/ai/anthropic/sonnet4",
            "claude-opus-4-20250514": "/ai/anthropic/opus4",
        }
        return anthropic_mappings.get(model)

    # Ollama model mappings
    elif provider == "ollama":
        ollama_mappings = {
            "llama2": "/ai/ollama/llama2",
            "codellama": "/ai/ollama/codellama",
            "mistral": "/ai/ollama/mistral",
            "llama3": "/ai/ollama/llama3",
        }
        return ollama_mappings.get(model)

    # Open WebUI model mappings
    elif provider == "webui":
        webui_mappings = {
            "llama2": "/ai/webui/llama2",
            "codellama": "/ai/webui/codellama",
        }
        return webui_mappings.get(model)

    # AWS Bedrock - REMOVED (not supported)

    # GSAi (Government Services AI) - Static route we created
    elif provider == "openapi-gsai":
        # Use the static GSAi route we configured in the setup
        return "/ai/gsai-api-1/chat/completions"

    # OpenAPI provider mappings
    elif provider.startswith("openapi-"):
        # For OpenAPI providers, we need to find the chat completions endpoint
        # The model is passed as a parameter, not part of the URL
        provider_id = provider.replace("openapi-", "")

        # Query APISIX to find the chat completions route
        try:
            # When running in Docker, use container name; when local, use localhost
            apisix_admin_url = os.getenv("APISIX_ADMIN_URL", "http://apisix:9180")
            apisix_admin_key = os.getenv("APISIX_ADMIN_KEY", "2exEp0xPj8qlOBABX3tAQkVz6OANnVRB")

            logger.info("Querying APISIX admin API at %s for OpenAPI routes", apisix_admin_url)
            response = requests.get(
                f"{apisix_admin_url}/apisix/admin/routes",
                headers={"X-API-KEY": apisix_admin_key},
                timeout=5,
            )

            if response.status_code == 200:
                routes_data = response.json()
                if "list" in routes_data:
                    # Log total routes found
                    total_routes = len(routes_data["list"])
                    openapi_routes = [
                        r for r in routes_data["list"] if r.get("value", {}).get("id", "").startswith("openapi-")
                    ]
                    logger.info(
                        "Found %s total routes, %s OpenAPI routes",
                        total_routes,
                        len(openapi_routes),
                    )

                    for route_item in routes_data["list"]:
                        route = route_item.get("value", {})
                        route_id = route.get("id", "")
                        uri = route.get("uri", "")

                        # Log routes that match the provider
                        if route_id.startswith(f"openapi-{provider_id}-"):
                            logger.debug("Checking route: id=%s, uri=%s", route_id, uri)

                        # Look for the chat completions endpoint for this provider
                        # Pattern: /openapi/{provider-id}/api/v1/chat/completions
                        if (
                            route_id.startswith(f"openapi-{provider_id}-")
                            and uri.endswith("/chat/completions")
                            and f"/openapi/{provider_id}/" in uri
                        ):
                            logger.info("Found OpenAPI chat endpoint for %s: %s", provider, uri)
                            return str(uri)

                    # If no chat/completions endpoint found, try looking for "converse" operation
                    for route_item in routes_data["list"]:
                        route = route_item.get("value", {})
                        route_id = route.get("id", "")
                        uri = route.get("uri", "")

                        if (
                            route_id.startswith(f"openapi-{provider_id}-")
                            and "converse" in route_id.lower()
                            and f"/openapi/{provider_id}/" in uri
                        ):
                            logger.info(
                                "Found OpenAPI converse endpoint for %s: %s",
                                provider,
                                uri,
                            )
                            return str(uri)

            else:
                logger.error("Failed to query APISIX admin API: HTTP %s", response.status_code)
                logger.error("Response: %s", response.text)

            logger.warning("No chat completions endpoint found for OpenAPI provider %s", provider)
        except requests.exceptions.RequestException as e:
            logger.error("Network error querying APISIX admin API: %s", e)
        except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
            # Handle data processing, missing keys, attribute access, type, and database errors
            logger.error(
                "Error finding OpenAPI endpoint for %s/%s: %s",
                provider,
                model,
                e,
                exc_info=True,
            )

        return None

    return None


# DuckDB storage replaces in-memory storage
# _generators_store: Dict[str, Dict[str, object]] = {} - REMOVED

# Generator type definitions (this would normally come from a configuration file or database)
GENERATOR_TYPE_DEFINITIONS = {
    "AI Gateway": {
        "description": "APISIX AI Gateway integration for multiple AI providers",
        "category": "gateway",
        "parameters": [
            {
                "name": "provider",
                "type": "selectbox",
                "description": "AI Provider",
                "required": True,
                "default": "openai",
                "options": ["openai", "anthropic", "ollama", "webui", "openapi-gsai"],
                "category": "configuration",
            },
            {
                "name": "model",
                "type": "selectbox",
                "description": "AI Model",
                "required": True,
                "default": "gpt-3.5-turbo",
                "options": [],  # Dynamically loaded
                "category": "configuration",
            },
            {
                "name": "api_key",
                "type": "str",
                "description": "API Key",
                "required": False,
                "default": "",
                "category": "configuration",
            },
            {
                "name": "endpoint",
                "type": "str",
                "description": "Custom Endpoint URL",
                "required": False,
                "default": "",
                "category": "configuration",
            },
            {
                "name": "temperature",
                "type": "float",
                "description": "Temperature",
                "required": False,
                "default": 0.7,
                "category": "model",
                "step": 0.1,
            },
            {
                "name": "max_tokens",
                "type": "int",
                "description": "Max Tokens",
                "required": False,
                "default": 1000,
                "category": "model",
            },
            {
                "name": "top_p",
                "type": "float",
                "description": "Top P",
                "required": False,
                "default": 1.0,
                "category": "model",
                "step": 0.05,
            },
        ],
    },
    "HTTPTarget": {
        "description": "Generic HTTP REST API Target",
        "category": "generic",
        "parameters": [
            {
                "name": "endpoint",
                "type": "str",
                "description": "HTTP Endpoint URL",
                "required": True,
                "default": "",
                "category": "configuration",
            },
            {
                "name": "method",
                "type": "selectbox",
                "description": "HTTP Method",
                "required": True,
                "default": "POST",
                "options": ["GET", "POST", "PUT", "PATCH"],
                "category": "configuration",
            },
            {
                "name": "headers",
                "type": "dict",
                "description": "HTTP Headers",
                "required": False,
                "default": {"Content-Type": "application/json"},
                "category": "configuration",
            },
            {
                "name": "timeout",
                "type": "int",
                "description": "Request Timeout (seconds)",
                "required": False,
                "default": 30,
                "category": "configuration",
            },
        ],
    },
}


# Dynamic model discovery from APISIX routes
def discover_apisix_models(provider: str) -> List[str]:
    """Dynamically discover available models for a provider by querying APISIX routes

    This replaces hardcoded model lists with real-time discovery
    """
    try:

        apisix_admin_url = os.getenv("APISIX_ADMIN_URL", "http://localhost:9180")
        apisix_admin_key = os.getenv("APISIX_ADMIN_KEY", "2exEp0xPj8qlOBABX3tAQkVz6OANnVRB")

        # Query APISIX for all routes
        response = requests.get(
            f"{apisix_admin_url}/apisix/admin/routes",
            headers={"X-API-KEY": apisix_admin_key},
            timeout=10,
        )

        if response.status_code != 200:
            logger.warning("Failed to query APISIX routes: %s", response.status_code)
            return get_fallback_models(provider)

        routes_data = response.json()
        models = []

        # Extract models from routes matching the provider
        if "list" in routes_data:
            for route_item in routes_data["list"]:
                route = route_item.get("value", {})
                uri = route.get("uri", "")

                # Match provider-specific URI patterns
                if provider == "openai" and uri.startswith("/ai/openai/"):
                    # Extract model from URI like /ai/openai/gpt4 -> gpt-4
                    model_key = uri.replace("/ai/openai/", "")
                    actual_model = map_uri_to_model("openai", model_key)
                    if actual_model:
                        models.append(actual_model)

                elif provider == "anthropic" and uri.startswith("/ai/anthropic/"):
                    # Extract model from URI like /ai/anthropic/opus -> claude-3-opus-20240229
                    model_key = uri.replace("/ai/anthropic/", "")
                    actual_model = map_uri_to_model("anthropic", model_key)
                    if actual_model:
                        models.append(actual_model)

                elif provider == "ollama" and uri.startswith("/ai/ollama/"):
                    # Extract model from URI like /ai/ollama/llama2 -> llama2
                    model_key = uri.replace("/ai/ollama/", "")
                    models.append(model_key)

                elif provider == "webui" and uri.startswith("/ai/webui/"):
                    # Extract model from URI like /ai/webui/llama2 -> llama2
                    model_key = uri.replace("/ai/webui/", "")
                    models.append(model_key)

                elif provider.startswith("openapi-") and uri.startswith("/ai/openapi/"):
                    # Extract OpenAPI provider routes
                    # URI format: /ai/openapi/{provider-id}/{path}
                    parts = uri.split("/")
                    if len(parts) >= 4:
                        provider_id = parts[3]
                        if provider == f"openapi-{provider_id}":
                            # Get operation ID from route description or ID
                            route_id = route.get("id", "")
                            desc = route.get("desc", "")

                            # Extract operation ID from route ID
                            # New format: openapi-{provider-id}-{operation-id}-{hash}
                            if route_id.startswith(f"openapi-{provider_id}-"):
                                # Remove prefix
                                temp = route_id.replace(f"openapi-{provider_id}-", "")
                                # Remove the last -xxxxxxxx (8 char hash)
                                if len(temp) > 9 and temp[-9] == "-":
                                    operation_id = temp[:-9]
                                else:
                                    operation_id = temp
                                # Convert back from safe format
                                operation_id = operation_id.replace("-", "_")
                                models.append(operation_id)
                            elif desc and ":" in desc:
                                # Fallback: extract from description
                                operation_id = desc.split(":")[-1].strip()
                                models.append(operation_id)

        # Remove duplicates and sort
        models = list(set(models))
        models.sort()

        if models:
            logger.info(
                "Discovered %s models for provider %s: %s",
                len(models),
                provider,
                models,
            )
            return models
        else:
            logger.warning("No models discovered for provider %s, using fallback", provider)
            return get_fallback_models(provider)

    except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
        # Handle data processing, missing keys, attribute access, type, and database errors
        logger.error("Error discovering models for provider %s: %s", provider, e)
        return get_fallback_models(provider)


def map_uri_to_model(provider: str, uri_key: str) -> str:
    """Map URI key back to actual model name based on setup_macos.sh configuration"""
    # OpenAI URI mappings (reverse of setup_macos.sh)

    if provider == "openai":
        uri_to_model = {
            "gpt4": "gpt-4",
            "gpt35": "gpt-3.5-turbo",
            "gpt4-turbo": "gpt-4-turbo",
            "gpt4o": "gpt-4o",
            "gpt4o-mini": "gpt-4o-mini",
            "gpt41": "gpt-4.1",
            "gpt41-mini": "gpt-4.1-mini",
            "gpt41-nano": "gpt-4.1-nano",
            "o1-preview": "o1-preview",
            "o1-mini": "o1-mini",
            "o3-mini": "o3-mini",
            "o4-mini": "o4-mini",
        }
        return uri_to_model.get(uri_key, uri_key)  # Fallback to uri_key if not found

    # Anthropic URI mappings
    elif provider == "anthropic":
        uri_to_model = {
            "claude3-opus": "claude-3-opus-20240229",
            "claude3-sonnet": "claude-3-sonnet-20240229",
            "claude3-haiku": "claude-3-haiku-20240307",
            "claude35-sonnet": "claude-3-5-sonnet-20241022",
            "claude35-haiku": "claude-3-5-haiku-20241022",
            "sonnet37": "claude-3-7-sonnet-latest",
            "sonnet4": "claude-sonnet-4-20250514",
            "opus4": "claude-opus-4-20250514",
        }
        return uri_to_model.get(uri_key, uri_key)  # Fallback to uri_key if not found

    # OpenAPI URI mappings
    elif provider.startswith("openapi-"):
        # For OpenAPI, the URI key is the operation ID
        # Just return it as-is
        return uri_key

    return uri_key


def get_fallback_models(provider: str) -> List[str]:
    """Fallback model lists if APISIX discovery fails"""
    fallback_mappings = {
        "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"],
        "anthropic": [
            "claude-3-sonnet-20240229",
            "claude-3-5-sonnet-20241022",
            "claude-3-haiku-20240307",
        ],
        "ollama": ["llama2", "codellama", "mistral", "llama3"],
        "webui": ["llama2", "codellama"],
    }

    # For OpenAPI providers, return empty list as models are discovered dynamically
    if provider.startswith("openapi-"):
        # Exception: GSAi has hardcoded models since models endpoint has issues
        if provider == "openapi-gsai":
            return [
                "claude_3_5_sonnet",
                "claude_3_7_sonnet",
                "claude_3_haiku",
                "llama3211b",
                "cohere_english_v3",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-2.5-pro-preview-05-06",
            ]
        return []

    return fallback_mappings.get(provider, [])


# === Phase 1: Dynamic Model Discovery ===


async def discover_openapi_models_from_provider(provider_id: str, base_url: str, auth_token: str) -> List[str]:
    """Discover available models directly from OpenAPI provider's /api/v1/models endpoint

    Phase 1 Enhancement: Query actual provider APIs for real-time model discovery
    """
    try:

        # Construct models endpoint URL
        models_url = f"{base_url.rstrip('/')}/api/v1/models"
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Accept": "application/json",
        }

        logger.info("Discovering models from %s at %s", provider_id, models_url)

        # Configure SSL verification - disable for corporate environments with proxy/self-signed certs
        # TODO: Make this configurable via environment variable for security
        ssl_verify = False  # Disabled for corporate proxy compatibility
        if not ssl_verify:
            logger.warning(
                "SSL verification disabled for %s - ensure network security",
                provider_id,
            )

        async with httpx.AsyncClient(timeout=10.0, verify=ssl_verify) as client:
            response = await client.get(models_url, headers=headers)

        if response.status_code == 200:
            data = response.json()

            # Parse OpenAI-compatible models response
            if "data" in data and isinstance(data["data"], list):
                models = [model["id"] for model in data["data"] if "id" in model]
                logger.info(
                    "Successfully discovered %s models from %s: %s",
                    len(models),
                    provider_id,
                    models,
                )
                return models
            else:
                logger.warning(
                    "Unexpected response format from %s: missing 'data' array",
                    provider_id,
                )
                return []

        elif response.status_code == 403:
            logger.error("Authentication failed for %s: Invalid or expired token", provider_id)
            return []
        elif response.status_code == 404:
            logger.warning("Models endpoint not found for %s: %s", provider_id, models_url)
            return []
        elif response.status_code == 429:
            logger.warning("Rate limited by %s, falling back to cached models", provider_id)
            return []
        else:
            logger.warning(
                "Failed to discover models from %s: HTTP %s",
                provider_id,
                response.status_code,
            )
            return []

    except httpx.TimeoutException:
        logger.warning("Timeout while discovering models from %s", provider_id)
        return []
    except httpx.RequestError as e:
        logger.error("Network error discovering models from %s: %s", provider_id, e)
        return []
    except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
        # Handle data processing, missing keys, attribute access, type, and database errors
        logger.error("Unexpected error discovering models from %s: %s", provider_id, e)
        return []


def get_openapi_provider_config(provider_id: str) -> Dict[str, Optional[str]]:
    """Get configuration for an OpenAPI provider from settings

    Phase 1 Enhancement: Centralized provider configuration mapping
    """
    # Try numbered format first (OPENAPI_1_*, OPENAPI_2_*, etc.)

    for i in range(1, 11):  # Support up to 10 providers
        # Use getattr to access settings dynamically
        id_value = getattr(settings, f"OPENAPI_{i}_ID", None)
        if id_value == provider_id:
            return {
                "id": provider_id,
                "name": getattr(settings, f"OPENAPI_{i}_NAME", None),
                "base_url": getattr(settings, f"OPENAPI_{i}_BASE_URL", None),
                "auth_token": getattr(settings, f"OPENAPI_{i}_AUTH_TOKEN", None),
                "auth_type": getattr(settings, f"OPENAPI_{i}_AUTH_TYPE", "bearer"),
            }

    # Try direct format (OPENAPI_{PROVIDER_ID}_*, e.g., OPENAPI_GSAI_API_1_*)
    provider_key = provider_id.upper().replace("-", "_")
    base_url = getattr(settings, f"OPENAPI_{provider_key}_BASE_URL", None)
    auth_token = getattr(settings, f"OPENAPI_{provider_key}_AUTH_TOKEN", None)

    if base_url and auth_token:
        return {
            "id": provider_id,
            "name": getattr(settings, f"OPENAPI_{provider_key}_NAME", f"OpenAPI {provider_id}"),
            "base_url": base_url,
            "auth_token": auth_token,
            "auth_type": getattr(settings, f"OPENAPI_{provider_key}_AUTH_TYPE", "bearer"),
        }

    return {
        "id": provider_id,
        "name": None,
        "base_url": None,
        "auth_token": None,
        "auth_type": None,
    }


async def discover_apisix_models_enhanced(provider: str) -> List[str]:
    """Enhanced model discovery that queries actual OpenAPI providers

    Phase 1 Enhancement: Dynamic model discovery with fallback to route parsing
    """
    if provider.startswith("openapi-"):

        provider_id = provider.replace("openapi-", "")

        # Special handling for GSAi - use hardcoded models since models endpoint has issues
        if provider_id == "gsai":
            logger.info("Using hardcoded models for GSAi (models endpoint not working)")
            return [
                "claude_3_5_sonnet",
                "claude_3_7_sonnet",
                "claude_3_haiku",
                "llama3211b",
                "cohere_english_v3",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-2.5-pro-preview-05-06",
            ]

        # Get provider configuration
        config = get_openapi_provider_config(provider_id)

        logger.info(
            "Configuration for %s: base_url=%s, auth_token=%s",
            provider_id,
            "***" if config["base_url"] else None,
            "***" if config["auth_token"] else None,
        )

        if config["base_url"] and config["auth_token"]:
            logger.info(
                "Attempting dynamic model discovery for %s at %s",
                provider_id,
                config["base_url"],
            )

            # Try to discover models from actual provider API
            models = await discover_openapi_models_from_provider(provider_id, config["base_url"], config["auth_token"])

            if models:
                logger.info(
                    "✅ Dynamic discovery successful for %s: found %s models: %s",
                    provider_id,
                    len(models),
                    models,
                )
                return models
            else:
                logger.warning(
                    "❌ Dynamic discovery failed for %s, falling back to route parsing",
                    provider_id,
                )
        else:
            logger.warning(
                "❌ Missing configuration for %s: base_url=%s, auth_token=%s",
                provider_id,
                bool(config["base_url"]),
                bool(config["auth_token"]),
            )
            logger.info("Config details: %s", config)

    # Fallback to existing route-based discovery
    return discover_apisix_models(provider)


@router.get(
    "/types",
    response_model=GeneratorTypesResponse,
    summary="Get available generator types",
)
async def get_generator_types(
    current_user: User = Depends(get_current_user),
) -> GeneratorTypesResponse:
    """Get list of available generator types."""
    try:

        logger.info("User %s requested generator types", current_user.username)

        generator_types = list(GENERATOR_TYPE_DEFINITIONS.keys())

        return GeneratorTypesResponse(generator_types=generator_types, total=len(generator_types))
    except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
        # Handle data processing, missing keys, attribute access, type, and database errors
        logger.error("Error getting generator types: %s", e)
        raise safe_error_response("Failed to retrieve generator types", status_code=500) from e


@router.get(
    "/types/{generator_type}/params",
    response_model=GeneratorParametersResponse,
    summary="Get parameter definitions for a generator type",
)
async def get_generator_type_params(
    generator_type: str, current_user: User = Depends(get_current_user)
) -> GeneratorParametersResponse:
    """Get parameter definitions for a specific generator type."""
    try:

        logger.info(
            "User %s requested params for type: %s",
            current_user.username,
            generator_type,
        )

        if generator_type not in GENERATOR_TYPE_DEFINITIONS:
            raise safe_error_response("Generator type not found", status_code=404)

        type_def: Dict[str, object] = cast(Dict[str, object], GENERATOR_TYPE_DEFINITIONS[generator_type])

        # For AI Gateway, dynamically add OpenAPI providers to options
        if generator_type == "AI Gateway":
            # Make a copy to avoid modifying the original
            type_def = type_def.copy()
            type_def["parameters"] = [cast(Dict[str, object], param.copy()) for param in type_def["parameters"]]

            # Find the provider parameter and add enabled providers
            for param in type_def["parameters"]:
                if param["name"] == "provider":
                    # Get enabled base providers by checking settings flags
                    base_providers = []

                    # Check each provider's ENABLED flag from settings
                    if settings.OPENAI_ENABLED:
                        base_providers.append("openai")
                    if settings.ANTHROPIC_ENABLED:
                        base_providers.append("anthropic")
                    if settings.OLLAMA_ENABLED:
                        base_providers.append("ollama")
                    if settings.OPEN_WEBUI_ENABLED:
                        base_providers.append("webui")

                    # Discover OpenAPI providers (only if OPENAPI_ENABLED=true)
                    openapi_providers = []
                    logger.info("OPENAPI_ENABLED setting: %s", settings.OPENAPI_ENABLED)
                    if settings.OPENAPI_ENABLED:
                        try:
                            openapi_providers = get_openapi_providers()
                            logger.info(
                                "Successfully discovered OpenAPI providers: %s",
                                openapi_providers,
                            )
                        except (
                            ValueError,
                            KeyError,
                            AttributeError,
                            TypeError,
                            OSError,
                        ) as e:
                            # Handle data processing, missing keys, attribute access, type, and database errors
                            logger.error("Error discovering OpenAPI providers: %s", e)
                            openapi_providers = []
                    else:
                        logger.warning("OpenAPI providers disabled by OPENAPI_ENABLED setting")

                    # Combine all enabled providers
                    all_providers = base_providers + openapi_providers
                    param["options"] = all_providers

                    logger.info("Final enabled providers list: %s", all_providers)
                    logger.info(
                        "Base providers: %s, OpenAPI providers: %s",
                        base_providers,
                        openapi_providers,
                    )
                    logger.info(
                        "Settings - OPENAI: %s, ANTHROPIC: %s, OLLAMA: %s, OPEN_WEBUI: %s, OPENAPI: %s",
                        settings.OPENAI_ENABLED,
                        settings.ANTHROPIC_ENABLED,
                        settings.OLLAMA_ENABLED,
                        settings.OPEN_WEBUI_ENABLED,
                        settings.OPENAPI_ENABLED,
                    )
                    break

            # Populate model options for all enabled providers
            for param in type_def["parameters"]:
                if param["name"] == "model":
                    all_models = []
                    # Get models for all enabled providers
                    if settings.OPENAI_ENABLED:
                        all_models.extend(get_fallback_models("openai"))
                    if settings.ANTHROPIC_ENABLED:
                        all_models.extend(get_fallback_models("anthropic"))
                    if settings.OLLAMA_ENABLED:
                        all_models.extend(get_fallback_models("ollama"))
                    if settings.OPEN_WEBUI_ENABLED:
                        all_models.extend(get_fallback_models("webui"))

                    # Add OpenAPI models if enabled
                    if settings.OPENAPI_ENABLED:
                        try:
                            openapi_providers = get_openapi_providers()
                            for provider in openapi_providers:
                                try:
                                    # Use enhanced discovery to get real models from API
                                    models = await discover_apisix_models_enhanced(provider)
                                    if models:
                                        all_models.extend(models)
                                        logger.info("Added %d models for OpenAPI provider %s", len(models), provider)
                                except Exception as e:
                                    logger.warning("Failed to get models for OpenAPI provider %s: %s", provider, e)
                        except Exception as e:
                            logger.error("Error getting OpenAPI providers for model discovery: %s", e)

                    # Remove duplicates and sort
                    unique_models = sorted(list(set(all_models)))
                    param["options"] = unique_models
                    model_preview = unique_models[:5] + (["..."] if len(unique_models) > 5 else [])
                    logger.info("Populated model options with %d models: %s", len(unique_models), model_preview)
                    break

        parameters = [GeneratorParameter(**param) for param in type_def["parameters"]]

        return GeneratorParametersResponse(generator_type=generator_type, parameters=parameters)
    except HTTPException:  # pylint: disable=try-except-raise
        raise
    except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
        # Handle data processing, missing keys, attribute access, type, and database errors
        logger.error("Error getting params for generator type %s: %s", generator_type, e)
        raise safe_error_response("Failed to retrieve generator parameters", status_code=500) from e


@router.get("", response_model=GeneratorsListResponse, summary="Get configured generators")
async def get_generators(
    current_user: User = Depends(get_current_user),
) -> GeneratorsListResponse:
    """Get list of configured generators."""
    try:

        user_id = current_user.username
        logger.info("User %s requested generators list", user_id)

        # Get generators from DuckDB
        db_manager = get_duckdb_manager(user_id)
        generators_data = db_manager.list_generators()

        generators = []
        for gen_data in generators_data:
            # Parse last_test_time safely
            last_test_time = None
            if gen_data.get("test_results") and gen_data.get("test_results", {}).get("last_time"):
                try:
                    last_time_str = gen_data.get("test_results", {}).get("last_time")
                    if isinstance(last_time_str, str):
                        last_test_time = datetime.fromisoformat(last_time_str)
                except (ValueError, TypeError) as e:
                    logger.warning(
                        "Failed to parse last_test_time for generator %s: %s",
                        gen_data["id"],
                        e,
                    )
                    last_test_time = None

            generators.append(
                GeneratorInfo(
                    id=gen_data["id"],
                    name=gen_data["name"],
                    type=gen_data["type"],
                    status=gen_data.get("status", "ready"),
                    parameters=gen_data["parameters"],
                    created_at=gen_data["created_at"],
                    updated_at=gen_data["updated_at"],
                    last_test_result=(
                        gen_data.get("test_results", {}).get("last_result") if gen_data.get("test_results") else None
                    ),
                    last_test_time=last_test_time,
                )
            )

        return GeneratorsListResponse(generators=generators, total=len(generators))
    except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
        # Handle data processing, missing keys, attribute access, type, and database errors
        logger.error("Error getting generators: %s", e)
        raise safe_error_response("Failed to retrieve generators", status_code=500) from e


@router.post("", response_model=GeneratorInfo, summary="Create a new generator")
async def create_generator(
    request: GeneratorCreateRequest, current_user: User = Depends(get_current_user)
) -> GeneratorInfo:
    """Create a new generator configuration."""
    try:

        user_id = current_user.username
        logger.info("User %s creating generator: %s", user_id, request.name)

        # Get DuckDB manager
        db_manager = get_duckdb_manager(user_id)

        # Check if generator name already exists for this user
        existing_generator = db_manager.get_generator_by_name(request.name)
        if existing_generator:
            raise validation_error("Generator name already exists")

        # Validate generator type
        if request.type not in GENERATOR_TYPE_DEFINITIONS:
            raise validation_error("Invalid generator type specified")

        # Create generator in DuckDB
        generator_id = db_manager.create_generator(
            name=request.name,
            generator_type=request.type,
            parameters=request.parameters,
        )

        # Get the created generator to return with proper timestamps
        created_generator = db_manager.get_generator(generator_id)
        if not created_generator:
            raise HTTPException(status_code=500, detail="Failed to retrieve created generator")

        logger.info(
            "Generator '%s' created successfully with ID: %s",
            request.name,
            generator_id,
        )

        return GeneratorInfo(
            id=generator_id,
            name=request.name,
            type=request.type,
            status="ready",
            parameters=request.parameters,
            created_at=created_generator["created_at"],
            updated_at=created_generator["updated_at"],
        )

    except HTTPException:  # pylint: disable=try-except-raise
        raise
    except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
        # Handle data processing, missing keys, attribute access, type, and database errors
        logger.error("Error creating generator %s: %s", request.name, e)
        raise safe_error_response("Failed to create generator", status_code=500) from e


@router.delete(
    "/{generator_id}",
    response_model=GeneratorDeleteResponse,
    summary="Delete a generator",
)
async def delete_generator(
    generator_id: str, current_user: User = Depends(get_current_user)
) -> GeneratorDeleteResponse:
    """Delete a generator configuration."""
    try:

        user_id = current_user.username
        logger.info("User %s deleting generator: %s", user_id, generator_id)

        # Get DuckDB manager and find generator
        db_manager = get_duckdb_manager(user_id)
        generator_data = db_manager.get_generator(generator_id)

        if not generator_data:
            raise safe_error_response("Generator not found", status_code=404)

        generator_name = generator_data["name"]

        # Delete generator from DuckDB
        deleted = db_manager.delete_generator(generator_id)
        if not deleted:
            raise safe_error_response("Failed to delete generator", status_code=500)

        logger.info("Generator '%s' deleted successfully", generator_name)

        return GeneratorDeleteResponse(
            success=True,
            message=f"Generator '{generator_name}' deleted successfully",
            deleted_at=datetime.utcnow(),
        )

    except HTTPException:  # pylint: disable=try-except-raise
        raise
    except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
        # Handle data processing, missing keys, attribute access, type, and database errors
        logger.error("Error deleting generator %s: %s", generator_id, e)
        raise safe_error_response("Failed to delete generator", status_code=500) from e


@router.get(
    "/apisix/models",
    response_model=APIXModelsResponse,
    summary="Get available models from APISIX AI Gateway",
)
async def get_apisix_models(
    provider: str = Query(..., description="AI provider name"),
    current_user: User = Depends(get_current_user),
) -> object:
    """Get available models for a specific APISIX AI Gateway provider."""
    try:

        logger.info("User %s requested models for provider: %s", current_user.username, provider)

        # Phase 1 Enhancement: Use enhanced discovery with OpenAPI provider support
        logger.info("Discovering models for provider: %s", provider)
        models = await discover_apisix_models_enhanced(provider)

        if not models:
            logger.warning("No models discovered for provider: %s", provider)
            raise safe_error_response("Provider not supported or no models available", status_code=404)

        logger.info("Found %s models for provider %s: %s", len(models), provider, models)

        return APIXModelsResponse(provider=provider, models=models, total=len(models))

    except HTTPException:  # pylint: disable=try-except-raise
        raise
    except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
        # Handle data processing, missing keys, attribute access, type, and database errors
        logger.error("Error getting APISIX models for provider %s: %s", provider, e)
        raise safe_error_response("Failed to retrieve models", status_code=500) from e


@router.put("/{generator_id}", response_model=GeneratorInfo, summary="Update a generator")
async def update_generator(
    generator_id: str,
    request: GeneratorUpdateRequest,
    current_user: User = Depends(get_current_user),
) -> GeneratorInfo:
    """Update an existing generator configuration."""
    try:

        user_id = current_user.username
        logger.info("User %s updating generator: %s", user_id, generator_id)

        # Get DuckDB manager and find generator
        db_manager = get_duckdb_manager(user_id)
        generator_data = db_manager.get_generator(generator_id)

        if not generator_data:
            raise safe_error_response("Generator not found", status_code=404)

        # Prepare update data
        update_params = {}

        # Check name conflicts if name is being updated
        if request.name is not None and request.name != generator_data["name"]:
            existing_generator = db_manager.get_generator_by_name(request.name)
            if existing_generator:
                raise validation_error("Generator name already exists")
            # Note: DuckDB manager doesn't support name updates in current implementation
            # Would need to add this functionality if name updates are required

        if request.parameters is not None:
            update_params["parameters"] = request.parameters

        # Update generator in DuckDB
        if update_params:
            # Update parameters specifically
            if "parameters" in update_params:
                db_manager.update_generator(generator_id, update_params["parameters"])
            # Refresh generator data
            updated_generator_data = db_manager.get_generator(generator_id)
            if updated_generator_data:
                generator_data = updated_generator_data

        logger.info("Generator %s updated successfully", generator_id)

        return GeneratorInfo(
            id=generator_data["id"],
            name=generator_data["name"],
            type=generator_data["type"],
            status=generator_data["status"],
            parameters=generator_data["parameters"],
            created_at=generator_data["created_at"],
            updated_at=generator_data["updated_at"],
            last_test_result=(
                generator_data.get("test_results", {}).get("last_result")
                if generator_data.get("test_results")
                else None
            ),
            last_test_time=(
                generator_data.get("test_results", {}).get("last_time") if generator_data.get("test_results") else None
            ),
        )

    except HTTPException:  # pylint: disable=try-except-raise
        raise
    except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
        # Handle data processing, missing keys, attribute access, type, and database errors
        logger.error("Error updating generator %s: %s", generator_id, e)
        raise safe_error_response("Failed to update generator", status_code=500) from e


def get_openapi_providers() -> List[str]:
    """Discover available OpenAPI providers from APISIX routes"""
    try:

        apisix_admin_url = os.getenv("APISIX_ADMIN_URL", "http://localhost:9180")
        apisix_admin_key = os.getenv("APISIX_ADMIN_KEY", "2exEp0xPj8qlOBABX3tAQkVz6OANnVRB")

        response = requests.get(
            f"{apisix_admin_url}/apisix/admin/routes",
            headers={"X-API-KEY": apisix_admin_key},
            timeout=10,
        )

        if response.status_code != 200:
            return []

        routes_data = response.json()
        providers = set()

        if "list" in routes_data:
            for route_item in routes_data["list"]:
                route = route_item.get("value", {})
                uri = route.get("uri", "")

                # Match OpenAPI URI pattern: /ai/openapi/{provider-id}/...
                if uri.startswith("/ai/openapi/"):
                    parts = uri.split("/")
                    if len(parts) >= 4:
                        provider_id = parts[3]
                        providers.add(f"openapi-{provider_id}")

                # Special case: Match GSAi pattern: /ai/gsai-api-1/...
                elif uri.startswith("/ai/gsai-api-1/"):
                    providers.add("openapi-gsai")

        return sorted(list(providers))

    except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
        # Handle data processing, missing keys, attribute access, type, and database errors
        logger.error("Error discovering OpenAPI providers: %s", e)
        return []


@router.get(
    "/apisix/openapi-providers",
    response_model=List[str],
    summary="Get list of available OpenAPI providers",
)
async def get_openapi_providers_endpoint(
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Get list of available OpenAPI providers."""
    try:

        providers = get_openapi_providers()
        return providers
    except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
        # Handle data processing, missing keys, attribute access, type, and database errors
        logger.error("Error getting OpenAPI providers: %s", e)
        raise HTTPException(
            status_code=500,
            detail=safe_error_response("Failed to get OpenAPI providers"),
        ) from e


@router.get(
    "/apisix/openapi-models",
    response_model=Dict[str, List[str]],
    summary="Get models for all OpenAPI providers",
)
async def get_all_openapi_models(
    current_user: User = Depends(get_current_user),
) -> Dict[str, List[str]]:
    """Get available models for all configured OpenAPI providers

    Phase 1 Enhancement: Provides comprehensive model listing for debugging and validation
    """
    try:

        logger.info("User %s requested models for all OpenAPI providers", current_user.username)

        providers = get_openapi_providers()
        all_models = {}

        if not providers:
            logger.info("No OpenAPI providers found")
            return {}

        # Discover models for each provider
        for provider in providers:
            # provider_id = provider.replace("openapi-", "")  # F841: unused variable

            try:
                models = await discover_apisix_models_enhanced(provider)
                all_models[provider] = models
                logger.info("Provider %s: found %s models", provider, len(models))
            except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
                # Handle data processing, missing keys, attribute access, type, and database errors
                logger.error("Error discovering models for %s: %s", provider, e)
                all_models[provider] = []

        total_models = sum(len(models) for models in all_models.values())
        logger.info(
            "Total models discovered across %s providers: %s",
            len(providers),
            total_models,
        )

        return all_models

    except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
        # Handle data processing, missing keys, attribute access, type, and database errors
        logger.error("Error getting OpenAPI models: %s", e)
        raise HTTPException(status_code=500, detail=safe_error_response("Failed to get OpenAPI models")) from e


@router.get("/apisix/openapi-debug", summary="Debug OpenAPI provider configurations")
async def debug_openapi_providers(
    current_user: User = Depends(get_current_user),
) -> Dict[str, object]:
    """Debug endpoint for OpenAPI provider configurations

    Phase 1 Enhancement: Provides detailed debugging information
    """
    try:

        logger.info("User %s requested OpenAPI debug information", current_user.username)

        debug_info: Dict[str, object] = {
            "openapi_enabled": settings.OPENAPI_ENABLED,
            "discovered_providers": [],
            "provider_configs": {},
            "environment_check": {},
            "routes_check": {},
        }

        # Get discovered providers
        providers = get_openapi_providers()
        debug_info["discovered_providers"] = providers

        # Check configuration for each provider
        for provider in providers:
            provider_id = provider.replace("openapi-", "")
            config = get_openapi_provider_config(provider_id)

            # Mask sensitive information
            safe_config = config.copy()
            auth_token = safe_config.get("auth_token")
            if auth_token and isinstance(auth_token, str) and len(auth_token) >= 4:
                safe_config["auth_token"] = f"***{auth_token[-4:]}"

            cast(Dict[str, Any], debug_info["provider_configs"])[provider] = safe_config

        # Also check settings directly for debugging
        debug_info["settings_check"] = {}
        for i in range(1, 11):
            enabled = getattr(settings, f"OPENAPI_{i}_ENABLED", None)
            if enabled:
                cast(Dict[str, Any], debug_info["settings_check"])[f"provider_{i}"] = {
                    "enabled": enabled,
                    "id": getattr(settings, f"OPENAPI_{i}_ID", None),
                    "name": getattr(settings, f"OPENAPI_{i}_NAME", None),
                    "base_url": getattr(settings, f"OPENAPI_{i}_BASE_URL", None),
                    "auth_token": ("***" if getattr(settings, f"OPENAPI_{i}_AUTH_TOKEN", None) else None),
                    "auth_type": getattr(settings, f"OPENAPI_{i}_AUTH_TYPE", None),
                }

        # Check environment variables
        env_vars = [
            "OPENAPI_ENABLED",
            "OPENAPI_1_ENABLED",
            "OPENAPI_1_ID",
            "OPENAPI_1_NAME",
            "OPENAPI_1_BASE_URL",
            "OPENAPI_1_AUTH_TYPE",
        ]

        for var in env_vars:
            value = os.getenv(var)
            if "TOKEN" in var and value:
                cast(Dict[str, Any], debug_info["environment_check"])[var] = f"***{value[-4:]}"
            else:
                cast(Dict[str, Any], debug_info["environment_check"])[var] = bool(value)

        # Check APISIX routes
        try:
            apisix_admin_url = os.getenv("APISIX_ADMIN_URL", "http://localhost:9180")
            apisix_admin_key = os.getenv("APISIX_ADMIN_KEY", "2exEp0xPj8qlOBABX3tAQkVz6OANnVRB")

            response = requests.get(
                f"{apisix_admin_url}/apisix/admin/routes",
                headers={"X-API-KEY": apisix_admin_key},
                timeout=5,
            )

            if response.status_code == 200:
                routes_data = response.json()
                openapi_routes = []

                if "list" in routes_data:
                    for route_item in routes_data["list"]:
                        route = route_item.get("value", {})
                        uri = route.get("uri", "")
                        if uri.startswith("/ai/openapi/"):
                            openapi_routes.append(
                                {
                                    "id": route.get("id", ""),
                                    "uri": uri,
                                    "desc": route.get("desc", ""),
                                }
                            )

                debug_info["routes_check"] = {
                    "status": "success",
                    "total_openapi_routes": len(openapi_routes),
                    "routes": openapi_routes[:10],  # Limit to first 10 for readability
                }
            else:
                debug_info["routes_check"] = {
                    "status": "error",
                    "http_code": response.status_code,
                }
        except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
            # Handle data processing, missing keys, attribute access, type, and database errors
            debug_info["routes_check"] = {"status": "error", "error": str(e)}

        return debug_info

    except (ValueError, KeyError, AttributeError, TypeError, OSError) as e:
        # Handle data processing, missing keys, attribute access, type, and database errors
        logger.error("Error in OpenAPI debug endpoint: %s", e)
        raise HTTPException(
            status_code=500,
            detail=safe_error_response("Failed to get debug information"),
        ) from e
