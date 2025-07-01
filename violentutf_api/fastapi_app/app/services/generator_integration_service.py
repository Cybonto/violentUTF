import logging
import os
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)


async def execute_generator_prompt(generator_name: str, prompt: str, conversation_id: str = None) -> Dict[str, Any]:
    """Execute prompt through configured generator"""
    try:
        # Get generator configuration by calling the backend function directly
        generator_config = await get_generator_by_name(generator_name)

        if not generator_config:
            raise ValueError(
                f"Generator '{generator_name}' not found. Please configure this generator first in the 'Configure Generators' page."
            )

        # Execute prompt based on generator type
        generator_type = generator_config.get("type", "unknown")
        logger.info(f"Executing generator '{generator_name}' with type '{generator_type}'")
        logger.info(f"Full generator config: {generator_config}")

        # Handle both naming conventions for AI Gateway (case-insensitive)
        if generator_type.lower() in ["apisix_ai_gateway", "ai gateway"]:
            logger.info(f"Executing APISIX AI Gateway generator for '{generator_name}'")
            return await _execute_apisix_generator(generator_config, prompt, conversation_id)
        else:
            logger.warning(
                f"Generator '{generator_name}' has unsupported type '{generator_type}'. Only 'AI Gateway' (apisix_ai_gateway) is supported."
            )
            logger.warning(f"Generator config keys: {list(generator_config.keys())}")
            return await _execute_generic_generator(generator_config, prompt, conversation_id)

    except Exception as e:
        logger.error(f"Error executing generator prompt: {e}")
        return {"success": False, "response": f"Error: {str(e)}", "error": str(e)}


async def _execute_apisix_generator(generator_config: Dict, prompt: str, conversation_id: str) -> Dict[str, Any]:
    """Execute prompt through APISIX AI Gateway"""
    try:
        # Get APISIX endpoint for generator
        provider = generator_config["parameters"]["provider"]
        model = generator_config["parameters"]["model"]

        logger.info(f"Executing APISIX generator: provider={provider}, model={model}")

        # Map to APISIX endpoint
        endpoint = _get_apisix_endpoint_for_model(provider, model)

        if not endpoint:
            raise ValueError(f"No APISIX endpoint for {provider}/{model}")

        # Make request to APISIX
        # When running in Docker, use container name; when running locally, use localhost
        base_url = os.getenv("VIOLENTUTF_API_URL", "http://apisix-apisix-1:9080")
        url = f"{base_url}{endpoint}"

        logger.info(f"APISIX request URL: {url}")

        # Build payload based on provider type
        if provider == "anthropic":
            # Anthropic format
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "model": model,
                "temperature": generator_config["parameters"].get("temperature", 0.7),
                "max_tokens": generator_config["parameters"].get("max_tokens", 1000),
            }
        elif provider.startswith("openapi-"):
            # OpenAPI format - always include model in payload
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}]
            }
            # Add optional parameters if the OpenAPI spec supports them
            if generator_config["parameters"].get("temperature") is not None:
                payload["temperature"] = generator_config["parameters"].get("temperature", 0.7)
            if generator_config["parameters"].get("max_tokens") is not None:
                payload["max_tokens"] = generator_config["parameters"].get("max_tokens", 1000)
            logger.info(f"OpenAPI request payload: {payload}")
        else:
            # OpenAI format - handle o1-series models differently
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}]}

            # o1-series models don't support temperature or max_tokens
            if model and not model.startswith("o1"):
                payload["temperature"] = generator_config["parameters"].get("temperature", 0.7)
                payload["max_tokens"] = generator_config["parameters"].get("max_tokens", 1000)
            else:
                logger.info(f"Using o1-series model '{model}' - skipping temperature and max_tokens parameters")

        headers = {"Content-Type": "application/json", "X-API-Gateway": "APISIX"}

        # Handle authentication based on provider type
        if provider.startswith("openapi-"):
            # OpenAPI providers need Bearer token from their configuration
            # Get the provider configuration to find auth token
            provider_id = provider.replace("openapi-", "")
            from app.api.endpoints.generators import get_openapi_provider_config
            provider_config = get_openapi_provider_config(provider_id)
            
            if provider_config and provider_config.get("auth_token"):
                headers["Authorization"] = f"Bearer {provider_config['auth_token']}"
                logger.info(f"Added Bearer token for OpenAPI provider {provider}")
            else:
                logger.warning(f"No auth token found for OpenAPI provider {provider}")
        else:
            # Add API key for APISIX key-auth plugin (for built-in providers)
            api_key = os.getenv("VIOLENTUTF_API_KEY") or os.getenv("APISIX_API_KEY")
            if api_key:
                headers["apikey"] = api_key
            else:
                logger.warning("No APISIX API key found in environment - requests may fail")

        response = requests.post(url, json=payload, headers=headers, timeout=30)

        logger.info(f"APISIX response status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            # Extract response based on provider
            if provider == "openai" or provider.startswith("openapi-"):
                # OpenAI and OpenAPI providers use the same response format
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            elif provider == "anthropic":
                content = result.get("content", [{}])[0].get("text", "")
            else:
                content = str(result.get("response", result))

            logger.info(f"Successfully got response from {provider}/{model}, content length: {len(content)}")

            return {"success": True, "response": content, "provider": provider, "model": model}
        else:
            logger.error(f"APISIX request failed: {response.status_code} - {response.text[:200]}")

            # Handle common APISIX errors with helpful messages
            if response.status_code == 502:
                # Bad Gateway - AI provider not accessible
                return {
                    "success": False,
                    "response": f"AI provider not accessible. Please check your APISIX configuration and {provider.upper()} API credentials.",
                    "error": f"502 Bad Gateway - {provider} service unavailable",
                }
            elif response.status_code == 401:
                # Unauthorized - API key issue
                return {
                    "success": False,
                    "response": f"Authentication failed. Please check your {provider.upper()} API key configuration.",
                    "error": "401 Unauthorized",
                }
            else:
                return {
                    "success": False,
                    "response": f"API Error: {response.status_code} - {response.text}",
                    "error": f"HTTP {response.status_code}",
                }

    except Exception as e:
        logger.error(f"APISIX generator exception: {e}")

        # Return proper error for connection issues
        if "Connection refused" in str(e) or "Failed to establish a new connection" in str(e):
            return {
                "success": False,
                "response": f"Cannot connect to APISIX gateway at {base_url}. Please ensure APISIX is running.",
                "error": "Connection refused",
            }

        return {"success": False, "response": f"Generator execution error: {str(e)}", "error": str(e)}


async def _execute_generic_generator(generator_config: Dict, prompt: str, conversation_id: str) -> Dict[str, Any]:
    """Execute prompt through generic generator"""
    # Generic generators are not yet implemented
    generator_type = generator_config.get("type", "unknown")
    generator_name = generator_config.get("name", "unknown")

    logger.error(f"Attempted to execute unsupported generator type: {generator_type} (name: {generator_name})")

    return {
        "success": False,
        "response": f"Generator type '{generator_type}' is not yet supported. Only 'AI Gateway' (apisix_ai_gateway) generators are currently implemented.",
        "error": f"Unsupported generator type: {generator_type}",
        "generator_type": generator_type,
        "generator_name": generator_name,
    }


def _get_apisix_endpoint_for_model(provider: str, model: str) -> str:
    """Get APISIX endpoint for provider/model combination"""
    
    # Handle OpenAPI providers
    if provider.startswith("openapi-"):
        # Use the function from generators.py to get the endpoint
        from app.api.endpoints.generators import get_apisix_endpoint_for_model
        endpoint = get_apisix_endpoint_for_model(provider, model)
        if endpoint:
            return endpoint
        # If no endpoint found, log detailed error
        logger.error(f"No APISIX endpoint found for OpenAPI provider {provider} with model {model}")
        return None

    # Map model names to APISIX route endpoints
    # These should match the configured APISIX AI proxy routes
    model_endpoint_mapping = {
        # OpenAI models
        "gpt-3.5-turbo": "/ai/openai/gpt35",
        "gpt-4": "/ai/openai/gpt4",
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
        # Anthropic models
        "claude-3-haiku-20240307": "/ai/anthropic/haiku",
        "claude-3-sonnet-20240229": "/ai/anthropic/sonnet",
        "claude-3-opus-20240229": "/ai/anthropic/opus",
        "claude-3-5-sonnet-20241022": "/ai/anthropic/sonnet35",
        "claude-3-5-haiku-20241022": "/ai/anthropic/haiku35",
        "claude-3-7-sonnet-latest": "/ai/anthropic/sonnet37",
        "claude-opus-4-20250514": "/ai/anthropic/opus4",
        "claude-sonnet-4-20250514": "/ai/anthropic/sonnet4",
    }

    # First try exact model match
    endpoint = model_endpoint_mapping.get(model)
    if endpoint:
        return endpoint

    # Fallback to provider-based generic endpoints
    provider_endpoint_mapping = {
        "openai": "/ai/openai/v1/chat/completions",
        "anthropic": "/ai/anthropic/v1/messages",
        "ollama": "/ai/ollama/api/chat",
        "webui": "/ai/webui/v1/chat/completions",
    }

    return provider_endpoint_mapping.get(provider)


async def get_generator_by_name(generator_name: str, user_context: str = None) -> Dict[str, Any]:
    """Get generator configuration by name from backend service"""
    try:
        # Get generators from DuckDB using proper user context
        from app.db.duckdb_manager import get_duckdb_manager

        # Use provided user context or fallback to default
        # For orchestrator calls, the user context should be passed from the authenticated request
        user_id = user_context or "violentutf.api"  # Fallback for backward compatibility
        logger.info(f"Getting generator '{generator_name}' for user '{user_id}'")

        db_manager = get_duckdb_manager(user_id)
        generators_data = db_manager.list_generators()

        logger.info(f"Found {len(generators_data)} generators for user '{user_id}'")

        # Find the specific generator by name
        for generator_data in generators_data:
            logger.debug(f"Checking generator: {generator_data.get('name')} (type: {generator_data.get('type')})")
            if generator_data.get("name") == generator_name:
                # Format the generator data to match expected structure
                result = {
                    "id": generator_data.get("id"),
                    "name": generator_data.get("name"),
                    "type": generator_data.get("type"),  # Fixed: was looking for "generator_type"
                    "parameters": generator_data.get("parameters", {}),
                    "status": generator_data.get("status", "active"),
                    "provider": generator_data.get("parameters", {}).get("provider"),
                    "model": generator_data.get("parameters", {}).get("model"),
                }
                logger.info(f"Found generator '{generator_name}' with type '{result.get('type')}'")
                return result

        # If not found, log available generators and return None
        available_names = [gen.get("name") for gen in generators_data]
        logger.error(f"Generator '{generator_name}' not found in database for user '{user_id}'")
        logger.error(f"Available generators for user '{user_id}': {available_names}")
        return None

    except Exception as e:
        logger.error(f"Error getting generator by name: {e}")
        # Return None to indicate database error
        return None
