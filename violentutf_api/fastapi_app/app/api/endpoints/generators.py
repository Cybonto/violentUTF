"""
FastAPI endpoints for generator management
Implements API backend for 1_Configure_Generators.py page
SECURITY: Enhanced with secure error handling to prevent information disclosure
"""
import asyncio
import time
import uuid
import os
import requests
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from app.schemas.generators import (
    GeneratorTypesResponse,
    GeneratorParametersResponse, 
    GeneratorsListResponse,
    GeneratorCreateRequest,
    GeneratorUpdateRequest,
    GeneratorInfo,
    APIXModelsResponse,
    GeneratorDeleteResponse,
    GeneratorError,
    GeneratorParameter
)
from app.core.auth import get_current_user
from app.core.error_handling import safe_error_response, validation_error
from app.db.duckdb_manager import get_duckdb_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_apisix_endpoint_for_model(provider: str, model: str) -> str:
    """
    Map AI provider and model to APISIX endpoint path
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
            "o4-mini": "/ai/openai/o4-mini"
        }
        return openai_mappings.get(model)
    
    # Anthropic model mappings
    elif provider == "anthropic":
        anthropic_mappings = {
            "claude-3-opus-20240229": "/ai/anthropic/opus",
            "claude-3-sonnet-20240229": "/ai/anthropic/sonnet", 
            "claude-3-haiku-20240307": "/ai/anthropic/haiku",
            "claude-3-5-sonnet-20241022": "/ai/anthropic/sonnet35",
            "claude-3-5-haiku-20241022": "/ai/anthropic/haiku35",
            "claude-3-7-sonnet-latest": "/ai/anthropic/sonnet37",
            "claude-sonnet-4-20250514": "/ai/anthropic/sonnet4",
            "claude-opus-4-20250514": "/ai/anthropic/opus4"
        }
        return anthropic_mappings.get(model)
    
    # Ollama model mappings
    elif provider == "ollama":
        ollama_mappings = {
            "llama2": "/ai/ollama/llama2",
            "codellama": "/ai/ollama/codellama", 
            "mistral": "/ai/ollama/mistral",
            "llama3": "/ai/ollama/llama3"
        }
        return ollama_mappings.get(model)
    
    # Open WebUI model mappings
    elif provider == "webui":
        webui_mappings = {
            "llama2": "/ai/webui/llama2",
            "codellama": "/ai/webui/codellama"
        }
        return webui_mappings.get(model)
    
    # AWS Bedrock model mappings (when supported)
    elif provider == "bedrock":
        bedrock_mappings = {
            "anthropic.claude-opus-4-20250514-v1:0": "/ai/bedrock/claude-opus-4",
            "anthropic.claude-sonnet-4-20250514-v1:0": "/ai/bedrock/claude-sonnet-4",
            "anthropic.claude-3-5-sonnet-20241022-v2:0": "/ai/bedrock/claude-35-sonnet",
            "anthropic.claude-3-5-haiku-20241022-v1:0": "/ai/bedrock/claude-35-haiku",
            "meta.llama3-3-70b-instruct-v1:0": "/ai/bedrock/llama3-3-70b",
            "amazon.nova-pro-v1:0": "/ai/bedrock/nova-pro",
            "amazon.nova-lite-v1:0": "/ai/bedrock/nova-lite"
        }
        return bedrock_mappings.get(model)
    
    return None

# DuckDB storage replaces in-memory storage
# _generators_store: Dict[str, Dict[str, Any]] = {} - REMOVED

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
                "options": ["openai", "anthropic", "ollama", "webui"],
                "category": "configuration"
            },
            {
                "name": "model",
                "type": "selectbox", 
                "description": "AI Model",
                "required": True,
                "default": "gpt-3.5-turbo",
                "options": [],  # Dynamically loaded
                "category": "configuration"
            },
            {
                "name": "api_key",
                "type": "str",
                "description": "API Key",
                "required": False,
                "default": "",
                "category": "configuration"
            },
            {
                "name": "endpoint",
                "type": "str", 
                "description": "Custom Endpoint URL",
                "required": False,
                "default": "",
                "category": "configuration"
            },
            {
                "name": "temperature",
                "type": "float",
                "description": "Temperature",
                "required": False,
                "default": 0.7,
                "category": "model",
                "step": 0.1
            },
            {
                "name": "max_tokens",
                "type": "int",
                "description": "Max Tokens",
                "required": False,
                "default": 1000,
                "category": "model"
            },
            {
                "name": "top_p",
                "type": "float",
                "description": "Top P",
                "required": False,
                "default": 1.0,
                "category": "model",
                "step": 0.05
            }
        ]
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
                "category": "configuration"
            },
            {
                "name": "method",
                "type": "selectbox",
                "description": "HTTP Method",
                "required": True,
                "default": "POST",
                "options": ["GET", "POST", "PUT", "PATCH"],
                "category": "configuration"
            },
            {
                "name": "headers",
                "type": "dict",
                "description": "HTTP Headers",
                "required": False,
                "default": {"Content-Type": "application/json"},
                "category": "configuration"
            },
            {
                "name": "timeout",
                "type": "int",
                "description": "Request Timeout (seconds)",
                "required": False,
                "default": 30,
                "category": "configuration"
            }
        ]
    }
}

# Dynamic model discovery from APISIX routes
def discover_apisix_models(provider: str) -> List[str]:
    """
    Dynamically discover available models for a provider by querying APISIX routes
    This replaces hardcoded model lists with real-time discovery
    """
    try:
        
        apisix_admin_url = os.getenv("APISIX_ADMIN_URL", "http://localhost:9180")
        apisix_admin_key = os.getenv("APISIX_ADMIN_KEY", "2exEp0xPj8qlOBABX3tAQkVz6OANnVRB")
        
        # Query APISIX for all routes
        response = requests.get(
            f"{apisix_admin_url}/apisix/admin/routes",
            headers={"X-API-KEY": apisix_admin_key},
            timeout=10
        )
        
        if response.status_code != 200:
            logger.warning(f"Failed to query APISIX routes: {response.status_code}")
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
        
        # Remove duplicates and sort
        models = list(set(models))
        models.sort()
        
        if models:
            logger.info(f"Discovered {len(models)} models for provider {provider}: {models}")
            return models
        else:
            logger.warning(f"No models discovered for provider {provider}, using fallback")
            return get_fallback_models(provider)
            
    except Exception as e:
        logger.error(f"Error discovering models for provider {provider}: {e}")
        return get_fallback_models(provider)

def map_uri_to_model(provider: str, uri_key: str) -> str:
    """
    Map URI key back to actual model name based on setup_macos.sh configuration
    """
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
            "o4-mini": "o4-mini"
        }
        return uri_to_model.get(uri_key)
    
    # Anthropic URI mappings
    elif provider == "anthropic":
        uri_to_model = {
            "opus": "claude-3-opus-20240229",
            "sonnet": "claude-3-sonnet-20240229",
            "haiku": "claude-3-haiku-20240307",
            "sonnet35": "claude-3-5-sonnet-20241022",
            "haiku35": "claude-3-5-haiku-20241022",
            "sonnet37": "claude-3-7-sonnet-latest",
            "sonnet4": "claude-sonnet-4-20250514",
            "opus4": "claude-opus-4-20250514"
        }
        return uri_to_model.get(uri_key)
    
    return uri_key

def get_fallback_models(provider: str) -> List[str]:
    """
    Fallback model lists if APISIX discovery fails
    """
    fallback_mappings = {
        "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"],
        "anthropic": ["claude-3-sonnet-20240229", "claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
        "ollama": ["llama2", "codellama", "mistral", "llama3"],
        "webui": ["llama2", "codellama"]
    }
    return fallback_mappings.get(provider, [])


@router.get("/types", response_model=GeneratorTypesResponse, summary="Get available generator types")
async def get_generator_types(current_user = Depends(get_current_user)):
    """Get list of available generator types"""
    try:
        logger.info(f"User {current_user.username} requested generator types")
        
        generator_types = list(GENERATOR_TYPE_DEFINITIONS.keys())
        
        return GeneratorTypesResponse(
            generator_types=generator_types,
            total=len(generator_types)
        )
    except Exception as e:
        logger.error(f"Error getting generator types: {e}")
        raise safe_error_response("Failed to retrieve generator types", status_code=500)


@router.get("/types/{generator_type}/params", response_model=GeneratorParametersResponse, 
           summary="Get parameter definitions for a generator type")
async def get_generator_type_params(
    generator_type: str, 
    current_user = Depends(get_current_user)
):
    """Get parameter definitions for a specific generator type"""
    try:
        logger.info(f"User {current_user.username} requested params for type: {generator_type}")
        
        if generator_type not in GENERATOR_TYPE_DEFINITIONS:
            raise safe_error_response("Generator type not found", status_code=404)
        
        type_def = GENERATOR_TYPE_DEFINITIONS[generator_type]
        parameters = [GeneratorParameter(**param) for param in type_def["parameters"]]
        
        return GeneratorParametersResponse(
            generator_type=generator_type,
            parameters=parameters
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting params for generator type {generator_type}: {e}")
        raise safe_error_response("Failed to retrieve generator parameters", status_code=500)


@router.get("", response_model=GeneratorsListResponse, summary="Get configured generators")
async def get_generators(current_user = Depends(get_current_user)):
    """Get list of configured generators"""
    try:
        user_id = current_user.username
        logger.info(f"User {user_id} requested generators list")
        
        # Get generators from DuckDB
        db_manager = get_duckdb_manager(user_id)
        generators_data = db_manager.list_generators()
        
        generators = []
        for gen_data in generators_data:
            generators.append(GeneratorInfo(
                id=gen_data['id'],
                name=gen_data['name'],
                type=gen_data['type'],
                status=gen_data.get('status', 'ready'),
                parameters=gen_data['parameters'],
                created_at=gen_data['created_at'],
                updated_at=gen_data['updated_at'],
                last_test_result=gen_data.get('test_results', {}).get('last_result') if gen_data.get('test_results') else None,
                last_test_time=datetime.fromisoformat(gen_data.get('test_results', {}).get('last_time')) if gen_data.get('test_results') and gen_data.get('test_results', {}).get('last_time') else None
            ))
        
        return GeneratorsListResponse(
            generators=generators,
            total=len(generators)
        )
    except Exception as e:
        logger.error(f"Error getting generators: {e}")
        raise safe_error_response("Failed to retrieve generators", status_code=500)


@router.post("", response_model=GeneratorInfo, summary="Create a new generator")
async def create_generator(
    request: GeneratorCreateRequest,
    current_user = Depends(get_current_user)
):
    """Create a new generator configuration"""
    try:
        user_id = current_user.username
        logger.info(f"User {user_id} creating generator: {request.name}")
        
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
            parameters=request.parameters
        )
        
        # Get the created generator to return with proper timestamps
        created_generator = db_manager.get_generator(generator_id)
        
        logger.info(f"Generator '{request.name}' created successfully with ID: {generator_id}")
        
        return GeneratorInfo(
            id=generator_id,
            name=request.name,
            type=request.type,
            status='ready',
            parameters=request.parameters,
            created_at=created_generator['created_at'],
            updated_at=created_generator['updated_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating generator {request.name}: {e}")
        raise safe_error_response("Failed to create generator", status_code=500)





@router.delete("/{generator_id}", response_model=GeneratorDeleteResponse, 
              summary="Delete a generator")
async def delete_generator(
    generator_id: str,
    current_user = Depends(get_current_user)
):
    """Delete a generator configuration"""
    try:
        user_id = current_user.username
        logger.info(f"User {user_id} deleting generator: {generator_id}")
        
        # Get DuckDB manager and find generator
        db_manager = get_duckdb_manager(user_id)
        generator_data = db_manager.get_generator(generator_id)
        
        if not generator_data:
            raise safe_error_response("Generator not found", status_code=404)
        
        generator_name = generator_data['name']
        
        # Delete generator from DuckDB
        deleted = db_manager.delete_generator(generator_id)
        if not deleted:
            raise safe_error_response("Failed to delete generator", status_code=500)
        
        logger.info(f"Generator '{generator_name}' deleted successfully")
        
        return GeneratorDeleteResponse(
            success=True,
            message=f"Generator '{generator_name}' deleted successfully",
            deleted_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting generator {generator_id}: {e}")
        raise safe_error_response("Failed to delete generator", status_code=500)


@router.get("/apisix/models", response_model=APIXModelsResponse, 
           summary="Get available models from APISIX AI Gateway")
async def get_apisix_models(
    provider: str = Query(..., description="AI provider name"),
    current_user = Depends(get_current_user)
):
    """Get available models for a specific APISIX AI Gateway provider"""
    try:
        logger.info(f"User {current_user.username} requested models for provider: {provider}")
        
        # Dynamically discover models from APISIX routes
        logger.info(f"Discovering models for provider: {provider}")
        models = discover_apisix_models(provider)
        
        if not models:
            logger.warning(f"No models discovered for provider: {provider}")
            raise safe_error_response("Provider not supported or no models available", status_code=404)
        
        logger.info(f"Found {len(models)} models for provider {provider}: {models}")
        
        return APIXModelsResponse(
            provider=provider,
            models=models,
            total=len(models)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting APISIX models for provider {provider}: {e}")
        raise safe_error_response("Failed to retrieve models", status_code=500)


@router.put("/{generator_id}", response_model=GeneratorInfo, summary="Update a generator")
async def update_generator(
    generator_id: str,
    request: GeneratorUpdateRequest,
    current_user = Depends(get_current_user)
):
    """Update an existing generator configuration"""
    try:
        user_id = current_user.username
        logger.info(f"User {user_id} updating generator: {generator_id}")
        
        # Get DuckDB manager and find generator
        db_manager = get_duckdb_manager(user_id)
        generator_data = db_manager.get_generator(generator_id)
        
        if not generator_data:
            raise safe_error_response("Generator not found", status_code=404)
        
        # Prepare update data
        update_params = {}
        
        # Check name conflicts if name is being updated
        if request.name is not None and request.name != generator_data['name']:
            existing_generator = db_manager.get_generator_by_name(request.name)
            if existing_generator:
                raise validation_error("Generator name already exists")
            # Note: DuckDB manager doesn't support name updates in current implementation
            # Would need to add this functionality if name updates are required
            
        if request.parameters is not None:
            update_params['parameters'] = request.parameters
            
        # Update generator in DuckDB
        if update_params:
            db_manager.update_generator(generator_id, **update_params)
            # Refresh generator data
            generator_data = db_manager.get_generator(generator_id)
        
        logger.info(f"Generator {generator_id} updated successfully")
        
        return GeneratorInfo(
            id=generator_data['id'],
            name=generator_data['name'],
            type=generator_data['type'],
            status=generator_data['status'],
            parameters=generator_data['parameters'],
            created_at=generator_data['created_at'],
            updated_at=generator_data['updated_at'],
            last_test_result=generator_data.get('test_results', {}).get('last_result') if generator_data.get('test_results') else None,
            last_test_time=generator_data.get('test_results', {}).get('last_time') if generator_data.get('test_results') else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating generator {generator_id}: {e}")
        raise safe_error_response("Failed to update generator", status_code=500)




