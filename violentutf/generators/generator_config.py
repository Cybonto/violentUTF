# generators/generator_config.py

import asyncio
import json  # Ensure json is imported
import math  # Ensure math is imported
import os
import uuid  # Ensure uuid is imported
from typing import Any, Dict, List, Optional

import yaml

# Use the centralized logging setup
from utils.logging import get_logger

# Configure logger for this module FIRST
logger = get_logger(__name__)

# Import CentralMemory ONLY IF NEEDED elsewhere in this module (currently not needed)
# from pyrit.memory import CentralMemory
import httpx  # Needed for test_generator_async exception handling

# PyRIT imports
from pyrit.models import (
    PromptRequestPiece,
    PromptRequestResponse,
    construct_response_from_request,
)

# Note: PromptResponseError is not explicitly needed here as errors are strings
from pyrit.prompt_target import HTTPTarget  # Keep original import name
from pyrit.prompt_target import PromptChatTarget  # Base class for chat targets
from pyrit.prompt_target import PromptTarget  # Base class for all targets
from pyrit.prompt_target import (
    AzureBlobStorageTarget,
    AzureMLChatTarget,
    CrucibleTarget,
    GandalfTarget,
    HuggingFaceChatTarget,
    HuggingFaceEndpointTarget,
    OpenAIDALLETarget,
    OpenAITTSTarget,
)

# --- Import Custom Targets ---
# OpenAI_Completion removed - use AI Gateway instead

# --- Import APISIX Gateway Target ---
logger.info("Attempting to import APISIX AI Gateway target...")
try:
    from custom_targets.apisix_ai_gateway import APISIXAIGatewayTarget

    if APISIXAIGatewayTarget:
        logger.info("Successfully imported custom target: APISIXAIGatewayTarget.")
    else:
        logger.warning(
            "Import statement succeeded but APISIXAIGatewayTarget variable is still None/False."
        )
        APISIXAIGatewayTarget = None
except ImportError as import_err:
    logger.error(
        f"Could not import APISIXAIGatewayTarget: {import_err}. Please ensure custom_targets/apisix_ai_gateway.py exists and is valid."
    )
    APISIXAIGatewayTarget = None
except Exception as e:
    logger.exception(
        f"An unexpected error occurred during import of APISIXAIGatewayTarget: {e}"
    )
    APISIXAIGatewayTarget = None
# --- End Custom Target Imports ---


# --- Constants ---
CONFIG_DIR = "parameters"
GENERATORS_CONFIG_FILENAME = "generators.yaml"
GENERATORS_CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, GENERATORS_CONFIG_FILENAME)
DEFAULT_PARAMS_FILENAME = "default_parameters.yaml"
DEFAULT_PARAMS_FILE_PATH = os.path.join(CONFIG_DIR, DEFAULT_PARAMS_FILENAME)

# --- Default Parameters Section Removed ---
# OpenAI_Completion removed - parameters no longer needed


# In-memory storage for Generator configurations (loaded from file)
_generators_cache: Dict[str, "Generator"] = {}

# Mapping of generator type names (user-facing) to Python classes
logger.debug(
    f"Defining GENERATOR_TYPE_CLASSES. APISIXAIGatewayTarget is: {APISIXAIGatewayTarget}"
)
GENERATOR_TYPE_CLASSES = {
    # Keep only the main generator types for streamlined interface
    **({"AI Gateway": APISIXAIGatewayTarget} if APISIXAIGatewayTarget else {}),
    "HTTP REST": HTTPTarget,  # Renamed from HTTPTarget
}
logger.debug(
    f"GENERATOR_TYPE_CLASSES defined with keys: {list(GENERATOR_TYPE_CLASSES.keys())}"
)

# Definitions of parameters required for each generator type
# (GENERATOR_PARAMS dictionary remains largely the same as provided previously,
# ensuring it aligns with the classes in GENERATOR_TYPE_CLASSES)
GENERATOR_PARAMS = {
    # --- AI Gateway Target ---
    "AI Gateway": [
        # Configuration parameters (left column)
        {
            "name": "provider",
            "type": "selectbox",
            "options": ["openai", "anthropic", "ollama", "webui"],
            "required": True,
            "default": "openai",
            "description": "AI Provider (openai, anthropic, ollama, webui)",
            "category": "configuration",
        },
        {
            "name": "model",
            "type": "selectbox",
            "options": [],  # Will be populated dynamically
            "required": True,
            "description": "Model Name (dynamically loaded from APISIX)",
            "category": "configuration",
        },
        {
            "name": "max_requests_per_minute",
            "type": "int",
            "required": False,
            "description": "Max requests per minute (optional, for rate limiting)",
            "category": "configuration",
        },
        # Model parameters (right column)
        {
            "name": "temperature",
            "type": "float",
            "required": False,
            "default": 0.7,
            "description": "Temperature (0.0-2.0)",
            "step": 0.05,
            "category": "model",
        },
        {
            "name": "max_tokens",
            "type": "int",
            "required": False,
            "default": 1000,
            "description": "Max Tokens (max completion length)",
            "category": "model",
        },
        {
            "name": "top_p",
            "type": "float",
            "required": False,
            "default": 1.0,
            "description": "Top P (0.0-1.0)",
            "step": 0.05,
            "category": "model",
        },
        {
            "name": "frequency_penalty",
            "type": "float",
            "required": False,
            "default": 0.0,
            "description": "Frequency Penalty (-2.0 to 2.0)",
            "step": 0.1,
            "category": "model",
        },
        {
            "name": "presence_penalty",
            "type": "float",
            "required": False,
            "default": 0.0,
            "description": "Presence Penalty (-2.0 to 2.0)",
            "step": 0.1,
            "category": "model",
        },
        {
            "name": "seed",
            "type": "int",
            "required": False,
            "description": "Random seed for reproducibility (optional)",
            "category": "model",
        },
    ],
    # --- Renamed HTTPTarget key ---
    "HTTP REST": [
        {
            "name": "http_request",
            "type": "str",
            "required": True,
            "description": "HTTP Request string (use {PROMPT} placeholder)",
        },
        {
            "name": "prompt_regex_string",
            "type": "str",
            "required": False,
            "description": "Prompt placeholder regex (default: {PROMPT})",
            "default": "{PROMPT}",
        },
        {
            "name": "use_tls",
            "type": "bool",
            "required": False,
            "description": "Use TLS (HTTPS) (default: True)",
            "default": True,
        },
        {
            "name": "max_requests_per_minute",
            "type": "int",
            "required": False,
            "description": "Max requests per minute (optional)",
        },
    ],
    "AzureBlobStorageTarget": [
        {
            "name": "container_url",
            "type": "str",
            "required": True,
            "description": "Azure Storage Container URL (or set AZURE_STORAGE_ACCOUNT_CONTAINER_URL env var)",
        },
        {
            "name": "sas_token",
            "type": "str",
            "required": False,
            "description": "SAS Token (or set AZURE_STORAGE_ACCOUNT_SAS_TOKEN env var)",
        },
        {
            "name": "blob_content_type",
            "type": "str",
            "required": False,
            "description": "Blob Content Type (default: PLAIN_TEXT)",
            "default": "PLAIN_TEXT",
        },
        {
            "name": "max_requests_per_minute",
            "type": "int",
            "required": False,
            "description": "Max requests per minute (optional)",
        },
    ],
    "OpenAIDALLETarget": [
        {
            "name": "endpoint",
            "type": "str",
            "required": True,
            "description": "Endpoint URL (e.g., https://YOUR_RESOURCE.openai.azure.com/ or https://api.openai.com/v1)",
        },
        {
            "name": "api_key",
            "type": "str",
            "required": True,
            "description": "API Key (or set env var like OPENAI_API_KEY or AZURE_OPENAI_DALLE_KEY)",
        },
        {
            "name": "deployment_name",
            "type": "str",
            "required": False,
            "description": "Azure Deployment Name (Required & Used ONLY for Azure endpoints)",
        },
        {
            "name": "api_version",
            "type": "str",
            "required": False,
            "description": "API Version (Required for Azure; ignored for standard OpenAI)",
            "default": "2024-06-01",
        },
        {
            "name": "dalle_version",
            "type": "str",
            "required": False,
            "description": 'DALL-E version ("dall-e-2" or "dall-e-3")',
            "default": "dall-e-3",
        },
        {
            "name": "image_size",
            "type": "str",
            "required": False,
            "description": 'Image Size ("1024x1024", "1792x1024", "1024x1792" for D3; "256x256", "512x512", "1024x1024" for D2)',
            "default": "1024x1024",
        },
        {
            "name": "num_images",
            "type": "int",
            "required": False,
            "description": "Number of images (always 1 for DALL-E 3)",
            "default": 1,
        },
        {
            "name": "quality",
            "type": "str",
            "required": False,
            "description": 'Image quality ("standard", "hd") (D3 only)',
            "default": "standard",
        },
        {
            "name": "style",
            "type": "str",
            "required": False,
            "description": 'Image style ("natural", "vivid") (D3 only)',
            "default": "vivid",
        },
        {
            "name": "use_aad_auth",
            "type": "bool",
            "required": False,
            "description": "Use Azure AD Auth (Azure ONLY)",
            "default": False,
        },
        {
            "name": "headers",
            "type": "dict",
            "required": False,
            "description": "Additional Request Headers (JSON string in UI, optional)",
        },
        {
            "name": "max_requests_per_minute",
            "type": "int",
            "required": False,
            "description": "Max requests per minute (optional)",
        },
    ],
    "OpenAITTSTarget": [
        {
            "name": "endpoint",
            "type": "str",
            "required": True,
            "description": "Endpoint URL (e.g., https://YOUR_RESOURCE.openai.azure.com/ or https://api.openai.com/v1)",
        },
        {
            "name": "api_key",
            "type": "str",
            "required": True,
            "description": "API Key (or set env var like OPENAI_API_KEY or AZURE_OPENAI_TTS_KEY)",
        },
        {
            "name": "deployment_name",
            "type": "str",
            "required": False,
            "description": "Azure Deployment Name (Required & Used ONLY for Azure endpoints)",
        },
        {
            "name": "api_version",
            "type": "str",
            "required": False,
            "description": "API Version (Required for Azure; ignored for standard OpenAI)",
            "default": "2024-03-01-preview",
        },
        {
            "name": "model",
            "type": "str",
            "required": False,
            "description": 'Model ("tts-1" or "tts-1-hd")',
            "default": "tts-1",
        },
        {
            "name": "voice",
            "type": "str",
            "required": False,
            "description": 'Voice (e.g., "alloy", "echo", "fable", "onyx", "nova", "shimmer")',
            "default": "alloy",
        },
        {
            "name": "response_format",
            "type": "str",
            "required": False,
            "description": 'Response format (e.g., "mp3", "opus", "aac", "flac")',
            "default": "mp3",
        },
        {
            "name": "language",
            "type": "str",
            "required": False,
            "description": 'Language code (e.g., "en", "es", "fr")',
            "default": "en",
        },
        {
            "name": "use_aad_auth",
            "type": "bool",
            "required": False,
            "description": "Use Azure AD Auth (Azure ONLY)",
            "default": False,
        },
        {
            "name": "headers",
            "type": "dict",
            "required": False,
            "description": "Additional Request Headers (JSON string in UI, optional)",
        },
        {
            "name": "max_requests_per_minute",
            "type": "int",
            "required": False,
            "description": "Max requests per minute (optional)",
        },
    ],
    "AzureMLChatTarget": [
        {
            "name": "endpoint",
            "type": "str",
            "required": True,
            "description": "Azure ML Endpoint URL (or set AZURE_ML_MANAGED_ENDPOINT env var)",
        },
        {
            "name": "api_key",
            "type": "str",
            "required": True,
            "description": "Azure ML API Key (or set AZURE_ML_KEY env var)",
        },
        {
            "name": "max_new_tokens",
            "type": "int",
            "required": False,
            "description": "Max new tokens (default: 400)",
            "default": 400,
        },
        {
            "name": "temperature",
            "type": "float",
            "required": False,
            "description": "Sampling temperature (default: 1.0)",
            "default": 1.0,
            "step": 0.05,
        },
        {
            "name": "top_p",
            "type": "float",
            "required": False,
            "description": "Top P (default: 1.0)",
            "default": 1.0,
            "step": 0.05,
        },
        {
            "name": "repetition_penalty",
            "type": "float",
            "required": False,
            "description": "Repetition penalty (default: 1.2)",
            "default": 1.2,
            "step": 0.1,
        },
        {
            "name": "max_requests_per_minute",
            "type": "int",
            "required": False,
            "description": "Max requests per minute (optional)",
        },
    ],
    "CrucibleTarget": [
        {
            "name": "endpoint",
            "type": "str",
            "required": True,
            "description": "Crucible Endpoint URL",
        },
        {
            "name": "api_key",
            "type": "str",
            "required": False,
            "description": "Crucible API Key (optional, or set CRUCIBLE_API_KEY env var)",
        },
        {
            "name": "max_requests_per_minute",
            "type": "int",
            "required": False,
            "description": "Max requests per minute (optional)",
        },
    ],
    "GandalfTarget": [
        {
            "name": "level",
            "type": "str",
            "required": True,
            "description": "Gandalf Level (e.g., LEVEL_1, LEVEL_7 - see PyRIT GandalfLevel enum)",
        },
        {
            "name": "max_requests_per_minute",
            "type": "int",
            "required": False,
            "description": "Max requests per minute (optional)",
        },
    ],
    "HuggingFaceChatTarget": [
        {
            "name": "model_id",
            "type": "str",
            "required": False,
            "description": "Model ID from Hugging Face Hub (Required if no model_path)",
        },
        {
            "name": "model_path",
            "type": "str",
            "required": False,
            "description": "Local path to the model (Required if no model_id)",
        },
        {
            "name": "hf_access_token",
            "type": "str",
            "required": False,
            "description": "Hugging Face Access Token (optional, or set HUGGINGFACE_TOKEN env var)",
        },
        {
            "name": "use_cuda",
            "type": "bool",
            "required": False,
            "description": "Use CUDA GPU (default: False)",
            "default": False,
        },
        {
            "name": "tensor_format",
            "type": "str",
            "required": False,
            "description": 'Tensor format (default: "pt")',
            "default": "pt",
        },
        {
            "name": "necessary_files",
            "type": "list",
            "required": False,
            "description": "Necessary files (comma-separated, optional)",
        },
        {
            "name": "max_new_tokens",
            "type": "int",
            "required": False,
            "description": "Max new tokens (default: 20)",
            "default": 20,
        },
        {
            "name": "temperature",
            "type": "float",
            "required": False,
            "description": "Temperature (default: 1.0)",
            "default": 1.0,
            "step": 0.05,
        },
        {
            "name": "top_p",
            "type": "float",
            "required": False,
            "description": "Top P (default: 1.0)",
            "default": 1.0,
            "step": 0.05,
        },
        {
            "name": "skip_special_tokens",
            "type": "bool",
            "required": False,
            "description": "Skip special tokens (default: True)",
            "default": True,
        },
        {
            "name": "trust_remote_code",
            "type": "bool",
            "required": False,
            "description": "Trust remote code (default: False)",
            "default": False,
        },
        {
            "name": "device_map",
            "type": "str",
            "required": False,
            "description": "Device map (optional)",
        },
        {
            "name": "torch_dtype",
            "type": "str",
            "required": False,
            "description": 'Torch data type (e.g. "auto", "float16") (optional)',
        },
        {
            "name": "attn_implementation",
            "type": "str",
            "required": False,
            "description": "Attention implementation (optional)",
        },
    ],
    "HuggingFaceEndpointTarget": [
        {
            "name": "hf_token",
            "type": "str",
            "required": True,
            "description": "Hugging Face Token (or set HUGGINGFACE_TOKEN env var)",
        },
        {
            "name": "endpoint",
            "type": "str",
            "required": True,
            "description": "Endpoint URL",
        },
        {
            "name": "model_id",
            "type": "str",
            "required": True,
            "description": "Model ID associated with the endpoint",
        },
        {
            "name": "max_tokens",
            "type": "int",
            "required": False,
            "description": "Max tokens (default: 400)",
            "default": 400,
        },
        {
            "name": "temperature",
            "type": "float",
            "required": False,
            "description": "Temperature (default: 1.0)",
            "default": 1.0,
            "step": 0.05,
        },
        {
            "name": "top_p",
            "type": "float",
            "required": False,
            "description": "Top P (default: 1.0)",
            "default": 1.0,
            "step": 0.05,
        },
        {
            "name": "verbose",
            "type": "bool",
            "required": False,
            "description": "Verbose output (default: False)",
            "default": False,
        },
    ],
}

# --- Core Functions ---


def load_generators() -> Dict[str, "Generator"]:
    """Loads Generator configurations from the YAML file."""
    #     global _generators_cache  # TODO: Remove or use this global
    if not os.path.isfile(GENERATORS_CONFIG_FILE_PATH):
        logger.info(
            f"Generator config file not found at {GENERATORS_CONFIG_FILE_PATH}. Starting empty."
        )
        _generators_cache = {}
        return _generators_cache
    try:
        with open(GENERATORS_CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not isinstance(data, dict):
            logger.error(
                f"Invalid format in {GENERATORS_CONFIG_FILE_PATH}: Expected a dictionary, got {type(data)}. Loading empty config."
            )
            _generators_cache = {}
            return _generators_cache

        loaded_generators = {}
        for name, info in data.items():
            if not isinstance(info, dict):
                logger.warning(
                    f"Skipping invalid entry '{name}': Expected a dictionary."
                )
                continue
            generator_type = info.get("generator_type")
            parameters = info.get("parameters")
            if not generator_type or not isinstance(parameters, dict):
                logger.warning(
                    f"Skipping entry '{name}': Missing or invalid 'generator_type' or 'parameters'."
                )
                continue

            if (
                generator_type not in GENERATOR_TYPE_CLASSES
                or GENERATOR_TYPE_CLASSES[generator_type] is None
            ):
                logger.warning(
                    f"Skipping entry '{name}': Unknown or unavailable generator_type '{generator_type}'. Check imports and definition."
                )
                continue
            try:
                gen = Generator(
                    name=name, generator_type=generator_type, parameters=parameters
                )
                loaded_generators[name] = gen
            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"Error initializing generator '{name}' from config: {e}")
            except Exception as e:
                logger.exception(f"Unexpected error initializing generator '{name}'.")

        _generators_cache = loaded_generators
        logger.info(
            f"Generators loaded successfully from {GENERATORS_CONFIG_FILE_PATH}. Count: {len(_generators_cache)}"
        )
        return _generators_cache
    except (yaml.YAMLError, IOError) as e:
        logger.error(
            f"Error reading or parsing {GENERATORS_CONFIG_FILE_PATH}: {e}",
            exc_info=True,
        )
        _generators_cache = {}
        return _generators_cache
    except Exception as e:
        logger.exception(
            f"Unexpected error loading generators from {GENERATORS_CONFIG_FILE_PATH}."
        )
        _generators_cache = {}
        return _generators_cache


def save_generators() -> bool:
    """Saves the current state of the generator cache to the YAML file."""
    #     global _generators_cache  # TODO: Remove or use this global
    data_to_save = {}
    for name, gen_instance in _generators_cache.items():
        if isinstance(gen_instance, Generator):
            # Ensure parameters are serializable (e.g., convert float NaN/inf)
            serializable_params = {}
            for k, v in gen_instance.parameters.items():
                if isinstance(v, float):
                    if math.isnan(v):
                        serializable_params[k] = "NaN"
                    elif math.isinf(v):
                        serializable_params[k] = "Infinity" if v > 0 else "-Infinity"
                    else:
                        serializable_params[k] = v
                else:
                    serializable_params[k] = v

            data_to_save[name] = {
                "generator_type": gen_instance.generator_type,
                "parameters": serializable_params,  # Save cleaned params
            }
        else:
            logger.warning(
                f"Skipping save for '{name}': not a valid Generator instance."
            )
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(GENERATORS_CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(data_to_save, f, default_flow_style=False, sort_keys=False)
        logger.info(
            f"Generators saved successfully to {GENERATORS_CONFIG_FILE_PATH}. Count: {len(data_to_save)}"
        )
        return True
    except (IOError, yaml.YAMLError) as e:
        logger.error(
            f"Error writing generators to {GENERATORS_CONFIG_FILE_PATH}: {e}",
            exc_info=True,
        )
        return False
    except Exception as e:
        logger.exception(
            f"Unexpected error saving generators to {GENERATORS_CONFIG_FILE_PATH}."
        )
        return False


def get_generators() -> Dict[str, "Generator"]:
    """Retrieves the current dictionary of loaded Generator instances."""
    #     global _generators_cache  # TODO: Remove or use this global
    if not _generators_cache:
        logger.debug("Generator cache empty, loading from file.")
        load_generators()
    return {
        name: gen
        for name, gen in _generators_cache.items()
        if isinstance(gen, Generator)
    }


def add_generator(
    generator_name: str, generator_type: str, parameters: Dict[str, Any]
) -> "Generator":
    """Adds a new Generator configuration."""
    #     global _generators_cache  # TODO: Remove or use this global
    if generator_name in _generators_cache:
        raise ValueError(f"Generator name '{generator_name}' already exists.")
    if (
        generator_type not in GENERATOR_TYPE_CLASSES
        or GENERATOR_TYPE_CLASSES[generator_type] is None
    ):
        if generator_type in GENERATOR_PARAMS:
            raise KeyError(
                f"Generator type '{generator_type}' class failed to import or is unavailable."
            )
        else:
            raise KeyError(f"Generator type '{generator_type}' is not recognized.")
    try:
        new_gen = Generator(
            name=generator_name, generator_type=generator_type, parameters=parameters
        )
        _generators_cache[generator_name] = new_gen
        if not save_generators():
            logger.warning(
                f"Generator '{generator_name}' added to cache, but failed to save."
            )
        else:
            logger.info(f"Generator '{generator_name}' added and saved.")
        return new_gen
    except (ValueError, TypeError, KeyError) as e:
        logger.error(f"Failed to add generator '{generator_name}': {e}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error adding generator '{generator_name}'.")
        raise


def delete_generator(generator_name: str) -> bool:
    """Deletes a Generator configuration."""
    #     global _generators_cache  # TODO: Remove or use this global
    if generator_name not in _generators_cache:
        raise KeyError(f"Cannot delete: Generator '{generator_name}' does not exist.")
    try:
        del _generators_cache[generator_name]
        success = save_generators()
        if success:
            logger.info(f"Generator '{generator_name}' deleted.")
        else:
            logger.error(
                f"Generator '{generator_name}' deleted from cache, but failed to save changes to file."
            )
        return success
    except Exception as e:
        logger.exception(f"Unexpected error deleting generator '{generator_name}'.")
        return False


def configure_generator(generator_name: str, parameters: Dict[str, Any]) -> "Generator":
    """Updates the parameters of an existing Generator."""
    #     global _generators_cache  # TODO: Remove or use this global
    if generator_name not in _generators_cache:
        raise KeyError(
            f"Cannot configure: Generator '{generator_name}' does not exist."
        )
    try:
        gen_instance = _generators_cache[generator_name]
        if not isinstance(gen_instance, Generator):
            raise TypeError(
                f"Entry '{generator_name}' is not a valid Generator instance."
            )
        gen_instance.update_parameters(parameters)
        if not save_generators():
            logger.warning(f"Generator '{generator_name}' updated, but failed to save.")
        else:
            logger.info(f"Generator '{generator_name}' configured successfully.")
        return gen_instance
    except (ValueError, TypeError, KeyError) as e:
        logger.error(f"Failed to configure generator '{generator_name}': {e}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error configuring generator '{generator_name}'.")
        raise


async def test_generator_async(generator_name: str) -> tuple[bool, str]:
    """
    Tests a configured Generator by sending a simple prompt via its instance.
    Handles PyRIT PromptTarget instances.
    Logs pass/fail status explicitly.
    """
    #     global _generators_cache  # TODO: Remove or use this global
    if generator_name not in _generators_cache:
        error_msg = f"Cannot test: Generator '{generator_name}' does not exist."
        logger.error(error_msg)
        raise KeyError(error_msg)  # Raise error to be caught upstream

    generator_instance_wrapper = _generators_cache[generator_name]
    if not isinstance(generator_instance_wrapper, Generator):
        error_msg = f"Cannot test: Entry '{generator_name}' in cache is not a valid Generator instance."
        logger.error(error_msg)
        return False, error_msg  # Return failure

    target_instance = generator_instance_wrapper.instance

    if not target_instance:
        error_msg = f"Cannot test '{generator_name}': Target instance is not available. Instantiation failed?"
        logger.error(error_msg)
        return False, error_msg  # Return failure

    logger.info(
        f"Initiating test for generator '{generator_name}' (Target Type: {type(target_instance).__name__})..."
    )
    test_prompt = (
        "This is a short test prompt from the configuration utility. Respond briefly."
    )
    success = False
    message = "Test initialization failed."

    try:
        if isinstance(target_instance, PromptTarget):
            logger.debug(f"Testing '{generator_name}' as PyRIT PromptTarget...")
            # Create a minimal PromptRequestResponse for testing
            request = PromptRequestResponse(
                request_pieces=[
                    PromptRequestPiece(
                        role="user",
                        original_value=test_prompt,
                        converted_value=test_prompt,
                        conversation_id=str(uuid.uuid4()),
                        sequence=0,
                        prompt_target_identifier=target_instance.get_identifier(),
                        original_value_data_type="text",
                        converted_value_data_type="text",
                    )
                ]
            )
            # Call the target's send_prompt_async method
            response_request = await target_instance.send_prompt_async(
                prompt_request=request
            )

            # Interpret PyRIT response
            if (
                response_request
                and response_request.request_pieces
                and len(response_request.request_pieces) > 1
            ):
                assistant_response_piece = response_request.request_pieces[-1]
                if assistant_response_piece.role == "assistant":
                    # Use string literal 'none' for comparison
                    if (
                        assistant_response_piece.response_error == "none"
                        and assistant_response_piece.converted_value
                    ):
                        success = True
                        message = f"Test successful. Received response snippet: {assistant_response_piece.converted_value[:100]}..."
                        logger.debug(
                            f"Full test response for '{generator_name}': {assistant_response_piece.converted_value}"
                        )
                    elif (
                        assistant_response_piece.response_error
                        and assistant_response_piece.response_error != "none"
                    ):
                        message = f"Test failed. API returned error: {assistant_response_piece.response_error}. Details: {assistant_response_piece.original_value}"
                    elif not assistant_response_piece.converted_value:
                        message = "Test failed. Received an empty or invalid response content from assistant (error='none')."
                    else:
                        message = "Test failed. Unknown response state."
                else:
                    message = f"Test failed. Expected assistant role in response, got '{assistant_response_piece.role}'."
            else:
                message = "Test failed. Invalid or empty response structure received from target."
        else:
            message = f"Test failed. Target instance type '{type(target_instance).__name__}' is not a PromptTarget."

    except NotImplementedError:
        message = f"Test failed. Generator '{generator_name}' (Type: {generator_instance_wrapper.generator_type}) does not support async sending."
        logger.error(message)
    except Exception as e:
        message = f"Test failed. Unexpected error during execution: {e}"
        logger.exception(
            f"Unexpected error during test execution for '{generator_name}'."
        )
        if isinstance(e, httpx.HTTPStatusError):
            try:
                message += f" Response body: {e.response.text[:500]}"
            except Exception:
                pass

    if success:
        logger.info(f"Test result for '{generator_name}': PASSED. Message: {message}")
    else:
        logger.error(f"Test result for '{generator_name}': FAILED. Message: {message}")

    return success, message


def get_generator_by_name(generator_name: str) -> Optional["Generator"]:
    """Retrieves a specific Generator instance by name."""
    #     global _generators_cache  # TODO: Remove or use this global
    gen = _generators_cache.get(generator_name)
    if not gen:
        logger.debug(f"Generator '{generator_name}' not in cache, attempting reload.")
        load_generators()
        gen = _generators_cache.get(generator_name)
        if not gen:
            logger.warning(f"Generator '{generator_name}' not found even after reload.")
            return None

    if isinstance(gen, Generator):
        if not gen.instance:
            try:
                gen.instantiate_target()
            except Exception as e:
                logger.error(
                    f"Failed to instantiate target for '{generator_name}' on retrieval: {e}"
                )
        return gen
    elif gen is not None:
        logger.error(
            f"Entry '{generator_name}' in cache is not a valid Generator instance (type: {type(gen)})."
        )
        return None
    else:
        return None


def list_generator_types() -> List[str]:
    """
    Returns a list of available Generator type names in the defined order.
    Filters out types whose classes failed to import.
    """
    valid_types = [
        name for name, cls in GENERATOR_TYPE_CLASSES.items() if cls is not None
    ]
    logger.debug(f"Listing valid generator types: {valid_types}")
    return valid_types


def get_apisix_models_for_provider(provider: str) -> List[str]:
    """Get available models for a specific APISIX provider."""
    try:
        # Import here to avoid circular imports
        from utils.token_manager import TokenManager

        token_manager = TokenManager()
        endpoints = token_manager.get_apisix_endpoints()

        provider_models = endpoints.get(provider, {})
        models = list(provider_models.keys())

        logger.debug(f"Found {len(models)} models for provider '{provider}': {models}")
        return sorted(models)

    except Exception as e:
        logger.error(f"Error getting APISIX models for provider '{provider}': {e}")
        # Return fallback models based on provider
        fallback_models = {
            "openai": ["gpt-4", "gpt-3.5-turbo", "gpt-4o"],
            "anthropic": ["claude-3-sonnet-20240229", "claude-3-5-sonnet-20241022"],
            "ollama": ["llama2", "codellama"],
            "webui": ["llama2", "codellama"],
        }
        return fallback_models.get(provider, ["default-model"])


def get_generator_params(generator_type: str) -> List[Dict[str, Any]]:
    """Retrieves the parameter definitions for a specific Generator type."""
    if (
        generator_type == "HTTP REST"
        and "HTTP REST" not in GENERATOR_PARAMS
        and "HTTPTarget" in GENERATOR_PARAMS
    ):
        logger.warning("Using 'HTTPTarget' params for 'HTTP REST' request.")
        return [param.copy() for param in GENERATOR_PARAMS["HTTPTarget"]]

    if generator_type not in GENERATOR_PARAMS:
        raise KeyError(
            f"Parameter definitions not found for generator type '{generator_type}'."
        )

    # Deep copy the parameters to avoid modifying the original
    params = json.loads(json.dumps(GENERATOR_PARAMS[generator_type]))

    # For AI Gateway, dynamically populate model options based on default provider
    if generator_type == "AI Gateway":
        for param in params:
            if param["name"] == "model":
                # Get default provider
                provider_param = next(
                    (p for p in params if p["name"] == "provider"), None
                )
                default_provider = (
                    provider_param.get("default", "openai")
                    if provider_param
                    else "openai"
                )

                # Populate model options for default provider
                models = get_apisix_models_for_provider(default_provider)
                param["options"] = models
                if models:
                    param["default"] = models[0]

                logger.debug(
                    f"Populated {len(models)} model options for APISIX provider '{default_provider}'"
                )
                break

    return params


# --- Generator Wrapper Class ---
class Generator:
    """
    A wrapper class for target instances (PyRIT PromptTarget or standalone)
    managed by this application.
    """

    def __init__(self, name: str, generator_type: str, parameters: Dict[str, Any]):
        """Initializes the Generator wrapper."""
        if not name:
            raise ValueError("Generator name cannot be empty.")
        if (
            generator_type not in GENERATOR_TYPE_CLASSES
            or GENERATOR_TYPE_CLASSES[generator_type] is None
        ):
            if generator_type in GENERATOR_PARAMS:
                raise KeyError(
                    f"Generator type '{generator_type}' class failed to import or is unavailable."
                )
            else:
                raise KeyError(f"Invalid or unknown generator_type: '{generator_type}'")

        self.name: str = name
        self.generator_type: str = generator_type
        self.parameters: Dict[str, Any] = parameters.copy()
        self.instance: Optional[Any] = None  # Can hold PromptTarget or other types
        self._target_class: type = GENERATOR_TYPE_CLASSES[generator_type]

        logger.debug(
            f"Initializing Generator wrapper for '{self.name}' (Type: {self.generator_type})"
        )
        self.validate_parameters()
        self.instantiate_target()

    @property
    def prompt_target(self):
        """Compatibility property to access the instance as prompt_target."""
        return self.instance

    def validate_parameters(self):
        """Validates the stored parameters."""
        logger.debug(f"Validating parameters for '{self.name}'...")
        try:
            param_defs = get_generator_params(self.generator_type)
        except KeyError:
            logger.error(
                f"Cannot validate parameters: Definitions not found for '{self.generator_type}'."
            )
            raise

        required_param_names = {p["name"] for p in param_defs if p["required"]}
        provided_params = self.parameters
        missing_required = set()

        for req_param in required_param_names:
            is_missing = req_param not in provided_params or provided_params[
                req_param
            ] in [None, ""]
            if is_missing:
                env_var_value = None
                # Basic Env Var Check (example)
                if req_param == "api_key" and self.generator_type in [
                    "OpenAIDALLETarget",
                    "OpenAITTSTarget",
                ]:
                    env_var_value = (
                        os.environ.get("OPENAI_API_KEY")
                        or os.environ.get("AZURE_OPENAI_CHAT_KEY")
                        or os.environ.get("AZURE_OPENAI_DALLE_KEY")
                        or os.environ.get("AZURE_OPENAI_TTS_KEY")
                    )
                # Add more env var checks...

                if not env_var_value:
                    missing_required.add(req_param)
                else:
                    logger.debug(
                        f"Required param '{req_param}' for '{self.name}' seems provided by env var."
                    )

        if missing_required:
            raise ValueError(
                f"Missing required parameter(s) for '{self.name}': {', '.join(sorted(missing_required))}."
            )

        # Basic Type Check (can be improved)
        for p_def in param_defs:
            p_name = p_def["name"]
            p_type_str = p_def["type"]
            if p_name in self.parameters and self.parameters[p_name] is not None:
                current_value = self.parameters[p_name]
                actual_type = type(current_value)

                if (
                    p_name == "headers"
                    and p_type_str == "dict"
                    and isinstance(current_value, str)
                ):
                    try:
                        parsed_val = (
                            json.loads(current_value) if current_value.strip() else None
                        )
                        if parsed_val is not None and not isinstance(parsed_val, dict):
                            raise ValueError(
                                f"Invalid JSON object provided for 'headers'."
                            )
                        self.parameters[p_name] = parsed_val
                        current_value = self.parameters[p_name]
                        if current_value is None:
                            continue
                        actual_type = type(current_value)
                    except json.JSONDecodeError:
                        raise ValueError(
                            f"Invalid JSON string provided for 'headers' parameter '{p_name}'."
                        )

                mismatch = False
                if p_type_str == "selectbox":
                    continue  # Skip Python type check

                if p_type_str == "int":
                    if not isinstance(current_value, int):
                        if (
                            isinstance(current_value, float)
                            and current_value.is_integer()
                        ):
                            self.parameters[p_name] = int(current_value)
                        else:
                            mismatch = True
                elif p_type_str == "float":
                    if not isinstance(current_value, (float, int)):
                        mismatch = True
                    elif isinstance(current_value, int):
                        self.parameters[p_name] = float(current_value)
                elif p_type_str == "bool" and not isinstance(current_value, bool):
                    mismatch = True
                elif p_type_str == "str" and not isinstance(current_value, str):
                    pass  # Allow conversion
                elif p_type_str == "list" and not isinstance(current_value, list):
                    mismatch = True
                elif p_type_str == "dict" and not isinstance(current_value, dict):
                    mismatch = True

                if mismatch:
                    logger.error(
                        f"Type mismatch for '{p_name}' in '{self.name}'. Expected '{p_type_str}', got '{actual_type.__name__}'. Value: {current_value}"
                    )

        logger.debug(f"Parameters validated for '{self.name}'.")

    def instantiate_target(self):
        """Instantiates the underlying target class."""
        logger.info(
            f"Attempting to instantiate target for '{self.name}' (Type: {self.generator_type})"
        )
        target_class = self._target_class
        init_params = self.parameters.copy()

        # Parameter Cleaning specific to PyRIT OpenAI targets
        is_azure_target_flag = init_params.pop("is_azure_target", None)
        if self.generator_type in [
            "OpenAIChatTarget",
            "OpenAIDALLETarget",
            "OpenAITTSTarget",
        ]:
            endpoint_val = init_params.get("endpoint", "").lower()
            is_azure = "openai.azure.com" in endpoint_val
            if not is_azure:
                init_params.pop("deployment_name", None)
                init_params.pop("api_version", None)
                init_params.pop("use_aad_auth", None)
                logger.debug(
                    f"Non-Azure endpoint detected for '{self.name}'. Removed Azure-specific params."
                )
            else:
                logger.debug(
                    f"Azure endpoint detected for '{self.name}'. Keeping Azure-specific params."
                )

        # Filter out None values before passing to ANY constructor
        cleaned_params = {k: v for k, v in init_params.items() if v is not None}
        logger.debug(f"Parameters after filtering None values: {cleaned_params}")

        # Log parameters (mask secrets)
        log_params = cleaned_params.copy()
        for key in list(log_params.keys()):
            if (
                "key" in key.lower()
                or "token" in key.lower()
                or "secret" in key.lower()
            ):
                log_params[key] = "****"
            elif key == "headers" and isinstance(log_params[key], dict):
                log_params[key] = {
                    h_k: (
                        "****" if "auth" in h_k.lower() or "key" in h_k.lower() else h_v
                    )
                    for h_k, h_v in log_params[key].items()
                }
        logger.debug(
            f"Passing final parameters to {self.generator_type}.__init__: {log_params}"
        )

        try:
            self.instance = target_class(**cleaned_params)
            logger.info(f"Successfully instantiated target for '{self.name}'.")
        except (TypeError, ValueError) as e:
            import inspect

            try:
                sig = inspect.signature(target_class.__init__)
                valid_params = list(sig.parameters.keys())
                invalid_passed = {
                    k: v
                    for k, v in cleaned_params.items()
                    if k not in valid_params and k != "self"
                }
                if invalid_passed:
                    logger.error(
                        f"Invalid parameters passed to {self.generator_type}: {invalid_passed}"
                    )
            except Exception:
                pass
            logger.error(
                f"Parameter error instantiating {self.generator_type} for '{self.name}': {e}",
                exc_info=True,
            )
            self.instance = None
            raise ValueError(
                f"Parameter error instantiating {self.generator_type}: {e}"
            ) from e
        except Exception as e:
            logger.exception(
                f"Unexpected error instantiating {self.generator_type} for '{self.name}'."
            )
            self.instance = None
            raise

    def save(self) -> bool:
        """Saves the current state of all generators."""
        logger.debug(
            f"Instance save method called for '{self.name}'. Triggering global save."
        )
        return save_generators()

    def update_parameters(self, parameters: Dict[str, Any]):
        """Updates parameters and re-instantiates the target."""
        logger.info(f"Updating parameters for generator '{self.name}'...")
        self.parameters.update(parameters)
        try:
            self.validate_parameters()
            self.instantiate_target()
            logger.info(
                f"Parameters for '{self.name}' updated and target instance refreshed."
            )
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Failed to update parameters for '{self.name}': {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error updating parameters for '{self.name}'.")
            raise


# --- End Generator Wrapper Class ---
