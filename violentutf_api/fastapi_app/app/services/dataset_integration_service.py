# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


async def get_dataset_prompts(
    dataset_id: str, sample_size: Optional[int] = None, user_context: Optional[str] = None
) -> List[str]:
    """Get prompts from dataset for orchestrator execution."""
    try:
        # Get dataset configuration
        dataset_config = await _get_dataset_by_id(dataset_id, user_context)

        if not dataset_config:
            raise ValueError(f"Dataset not found: {dataset_id}")

        logger.info(
            f"Found dataset config for {dataset_id}: {dataset_config.get('name')} (source: {dataset_config.get('source_type')})"
        )

        # Extract prompts based on dataset type
        prompts = []

        if dataset_config["source_type"] == "native":
            prompts = await _get_native_dataset_prompts(dataset_config)
        elif dataset_config["source_type"] == "local":
            prompts = await _get_local_dataset_prompts(dataset_config)
        elif dataset_config["source_type"] == "memory":
            prompts = await _get_memory_dataset_prompts(dataset_config, sample_size, user_context)
        elif dataset_config["source_type"] == "converter":
            prompts = await _get_converter_dataset_prompts(dataset_config)
        elif dataset_config["source_type"] == "transform":
            prompts = await _get_transform_dataset_prompts(dataset_config)
        elif dataset_config["source_type"] == "combination":
            prompts = await _get_combination_dataset_prompts(dataset_config)
        else:
            raise ValueError(f"Unsupported dataset source type: {dataset_config['source_type']}")

        # Apply sampling if requested
        if sample_size and len(prompts) > sample_size:
            import random

            prompts = random.sample(prompts, sample_size)

        logger.info(f"Loaded {len(prompts)} prompts from dataset {dataset_id}")
        return prompts

    except Exception as e:
        logger.error(f"Error getting dataset prompts: {e}")
        raise


async def _get_dataset_by_id(dataset_id: str, user_context: Optional[str] = None) -> Dict[str, Any]:
    """Get dataset configuration by ID from backend service."""
    try:
        # Get datasets directly from DuckDB without authentication context
        # This is safe for internal service - to - service calls
        from app.db.duckdb_manager import get_duckdb_manager

        # Use the provided user context or fall back to web interface user
        username = user_context or "violentutf.web"
        db_manager = get_duckdb_manager(username)

        # Handle memory dataset IDs (memory_0, memory_1, etc.)
        if dataset_id.startswith("memory_"):
            # Convert memory_0 to Memory Dataset 0 format
            dataset_number = dataset_id.replace("memory_", "")
            dataset_name = f"Memory Dataset {dataset_number}"

            # Return a mock memory dataset configuration
            return {
                "id": dataset_id,
                "name": dataset_name,
                "source_type": "memory",
                "status": "active",
                "description": f"PyRIT memory dataset {dataset_number}",
                "prompt_count": 10,  # Mock count
            }

        # For other datasets, try to get from DuckDB
        try:
            datasets_data = db_manager.list_datasets()

            # Find the specific dataset by ID
            for dataset_data in datasets_data:
                if dataset_data.get("id") == dataset_id or dataset_data.get("name") == dataset_id:
                    # Get the full dataset with prompts
                    full_dataset = db_manager.get_dataset(dataset_id)
                    if full_dataset:
                        return {
                            "id": full_dataset.get("id"),
                            "name": full_dataset.get("name"),
                            "source_type": full_dataset.get("source_type", "local"),
                            "status": full_dataset.get("status", "active"),
                            "description": full_dataset.get("description", ""),
                            "prompt_count": full_dataset.get("prompt_count", 0),
                            "prompts": full_dataset.get("prompts", []),
                        }
                    else:
                        return {
                            "id": dataset_data.get("id"),
                            "name": dataset_data.get("name"),
                            "source_type": dataset_data.get("source_type", "local"),
                            "status": dataset_data.get("status", "active"),
                            "description": dataset_data.get("description", ""),
                            "prompt_count": dataset_data.get("prompt_count", 0),
                        }
        except Exception as db_error:
            logger.warning(f"Could not access dataset database: {db_error}")

        # If not found, return None
        logger.warning(f"Dataset not found: {dataset_id}")
        return None

    except Exception as e:
        logger.error(f"Error calling dataset service: {e}")
        return None


async def _get_native_dataset_prompts(dataset_config: Dict) -> List[str]:
    """Get prompts from native dataset."""
    # Extract prompts from native dataset.
    dataset_type = dataset_config.get("dataset_type")
    logger.debug(f"Processing native dataset of type: {dataset_type}")

    # Get prompts from the dataset configuration
    prompts = dataset_config.get("prompts", [])
    logger.info(f"Native dataset {dataset_config.get('name')} has {len(prompts)} prompts")

    if isinstance(prompts, list):
        # Extract text values from prompt objects
        text_prompts = []
        for prompt in prompts:
            if isinstance(prompt, dict):
                # Check different possible keys for prompt text
                if "text" in prompt:
                    text_prompts.append(prompt["text"])
                elif "value" in prompt:
                    text_prompts.append(prompt["value"])
                else:
                    text_prompts.append(str(prompt))
            else:
                text_prompts.append(str(prompt))
        return text_prompts

    return []


async def _get_local_dataset_prompts(dataset_config: Dict) -> List[str]:
    """Get prompts from local uploaded dataset."""
    # Extract prompts from local dataset.
    prompts = dataset_config.get("prompts", [])

    # Similar extraction logic as native datasets
    text_prompts = []
    for prompt in prompts:
        if isinstance(prompt, dict):
            # Check different possible keys for prompt text
            if "text" in prompt:
                text_prompts.append(prompt["text"])
            elif "value" in prompt:
                text_prompts.append(prompt["value"])
            else:
                text_prompts.append(str(prompt))
        else:
            text_prompts.append(str(prompt))

    return text_prompts


async def _get_memory_dataset_prompts(
    dataset_config: Dict, limit: Optional[int] = None, user_context: Optional[str] = None
) -> List[str]:
    """Get prompts from PyRIT memory dataset using real memory database access."""
    try:
        dataset_id = dataset_config.get("id", "memory_0")
        dataset_name = dataset_config.get("name", "Unknown")

        logger.info(f"Loading memory dataset prompts for {dataset_name} (ID: {dataset_id})")

        # Try to access real PyRIT memory database
        prompts = await _load_real_memory_dataset_prompts(dataset_id, limit, user_context)

        if prompts:
            logger.info(f"Loaded {len(prompts)} real prompts from PyRIT memory dataset {dataset_name}")
            return prompts
        else:
            logger.warning(f"No prompts found in PyRIT memory for dataset {dataset_id}")
            # Return empty list instead of mock data - let calling code handle appropriately
            return []

    except Exception as e:
        logger.error(f"Error accessing PyRIT memory dataset {dataset_id}: {e}")
        # Return empty list instead of fallback mock data
        return []


async def _load_real_memory_dataset_prompts(
    dataset_id: str, limit: Optional[int] = None, user_id: Optional[str] = None
) -> List[str]:
    """Load actual prompts from PyRIT memory database files - WITH USER ISOLATION."""
    try:
        # Try active PyRIT memory instance first
        prompts = await _get_prompts_from_active_memory(dataset_id, limit)
        if prompts:
            return prompts

        # Fall back to direct database file access
        return await _get_prompts_from_database_files(dataset_id, limit, user_id)

    except Exception as e:
        logger.error(f"Error loading real memory dataset prompts: {e}")
        return []


async def _get_prompts_from_active_memory(dataset_id: str, limit: Optional[int]) -> List[str]:
    """Try to get prompts from active PyRIT memory instance."""
    try:
        from pyrit.memory import CentralMemory

        memory_instance = CentralMemory.get_memory_instance()
        if not memory_instance:
            return []

        logger.info(f"Found active PyRIT memory instance for dataset {dataset_id}")

        # Get conversation pieces from memory that could be prompts
        conversation_pieces = memory_instance.get_conversation()

        prompts = []
        for piece in conversation_pieces:
            if piece.role == "user" and piece.original_value:
                prompts.append(piece.original_value)

        if prompts:
            logger.info(f"Extracted {len(prompts)} prompts from active PyRIT memory")
            # Apply configurable limit if specified
            if limit and limit > 0:
                return prompts[:limit]
            return prompts

        return []

    except ValueError:
        logger.info("No active PyRIT memory instance found")
        return []
    except Exception as e:
        logger.warning(f"Error accessing active memory instance: {e}")
        return []


async def _get_prompts_from_database_files(dataset_id: str, limit: Optional[int], user_id: Optional[str]) -> List[str]:
    """Get prompts from direct database file access with user isolation."""
    try:
        # Security validation
        if not user_id:
            logger.error(f"Cannot load memory dataset {dataset_id} without user context - security violation prevented")
            return []

        # Get user-specific database paths
        db_paths = _get_user_prompts_database_paths(user_id)

        # Try to extract prompts from found database files
        for db_path in db_paths:
            prompts = await _extract_prompts_from_db_file(db_path, user_id, limit)
            if prompts:
                return prompts

        logger.info(f"No PyRIT memory data found for dataset {dataset_id}")
        return []

    except Exception as e:
        logger.error(f"Error accessing database files: {e}")
        return []


def _get_user_prompts_database_paths(user_id: str) -> List[str]:
    """Get paths to user-specific database files for prompt loading."""
    import hashlib

    # Generate the user's specific database filename
    salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")
    user_hash = hashlib.sha256((salt + user_id).encode("utf-8")).hexdigest()
    user_db_filename = f"pyrit_memory_{user_hash}.db"

    # Only check the user's specific database file in known locations
    memory_db_paths = []
    potential_paths = [
        "/app/app_data/violentutf",  # Docker API memory
        "./app_data/violentutf",  # Relative app data
    ]

    for base_path in potential_paths:
        if os.path.exists(base_path):
            user_db_path = os.path.join(base_path, user_db_filename)
            if os.path.exists(user_db_path):
                memory_db_paths.append(user_db_path)
                logger.info(f"Found user-specific database for {user_id}: {user_db_filename}")
                break  # Only use the first found user database

    return memory_db_paths


async def _extract_prompts_from_db_file(db_path: str, user_id: str, limit: Optional[int]) -> List[str]:
    """Extract prompts from a specific database file."""
    try:
        import sqlite3

        # Security check
        user_db_filename = _get_prompts_user_db_filename(user_id)
        if user_db_filename not in db_path:
            logger.error(f"Security violation: Attempted to access non-user database: {db_path}")
            return []

        logger.info(f"Reading user-specific PyRIT memory database: {db_path}")
        prompts = []

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Build query with optional limit
            query = _build_prompts_query(limit)
            cursor.execute(query)

            rows = cursor.fetchall()
            for row in rows:
                if row[0] and len(row[0].strip()) > 0:
                    prompts.append(row[0].strip())

        if prompts:
            logger.info(f"Extracted {len(prompts)} prompts from PyRIT database {db_path}")

        return prompts

    except Exception as db_error:
        logger.debug(f"Error accessing database {db_path}: {db_error}")
        return []


def _get_prompts_user_db_filename(user_id: str) -> str:
    """Get user-specific database filename for prompts."""
    import hashlib

    salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")
    user_hash = hashlib.sha256((salt + user_id).encode("utf-8")).hexdigest()
    return f"pyrit_memory_{user_hash}.db"


def _build_prompts_query(limit: Optional[int]) -> str:
    """Build SQL query for prompt extraction with optional limit."""
    query = """
        SELECT original_value FROM PromptRequestPieces
        WHERE role = 'user' AND original_value IS NOT NULL
        AND LENGTH(original_value) > 0
        AND original_value NOT LIKE '%Native harmbench prompt%'
        AND original_value NOT LIKE '%Native % prompt %'
        AND original_value NOT LIKE '%Sample % prompt %'
        AND original_value NOT LIKE '%Test prompt%'
        AND original_value NOT LIKE '%mock%'
        AND original_value NOT LIKE '%test prompt%'
        ORDER BY timestamp DESC
    """

    if limit and limit > 0:
        query += f" LIMIT {limit}"

    return query


async def _get_converter_dataset_prompts(dataset_config: Dict) -> List[str]:
    """Get prompts from converter - generated dataset."""
    try:
        logger.info(f"Loading converter dataset: {dataset_config.get('name')}")

        # Converter datasets store their prompts in the database with prompt_text field
        # First check if we have prompts directly in the config
        prompts = dataset_config.get("prompts", [])

        text_prompts = []
        for prompt in prompts:
            if isinstance(prompt, dict):
                # Check different possible keys for prompt text
                if "text" in prompt:
                    text_prompts.append(prompt["text"])
                elif "value" in prompt:
                    text_prompts.append(prompt["value"])
                elif "converted_value" in prompt:
                    # Converter datasets may have converted_value field
                    text_prompts.append(prompt["converted_value"])
                elif "original_value" in prompt:
                    # Fallback to original value if converted not available
                    text_prompts.append(prompt["original_value"])
                elif "prompt_text" in prompt:
                    # DuckDB structure uses prompt_text field
                    text_prompts.append(prompt["prompt_text"])
                else:
                    text_prompts.append(str(prompt))
            else:
                text_prompts.append(str(prompt))

        logger.info(f"Extracted {len(text_prompts)} prompts from converter dataset {dataset_config.get('name')}")
        return text_prompts

    except Exception as e:
        logger.error(f"Error loading converter dataset prompts: {e}")
        return []


async def _get_transform_dataset_prompts(dataset_config: Dict) -> List[str]:
    """Get prompts from transform - generated dataset."""
    try:
        logger.info(f"Loading transform dataset: {dataset_config.get('name')}")

        # Transform datasets are similar to converter datasets but may have different structure
        prompts = dataset_config.get("prompts", [])

        text_prompts = []
        for prompt in prompts:
            if isinstance(prompt, dict):
                # Check for transformed content
                if "transformed_value" in prompt:
                    text_prompts.append(prompt["transformed_value"])
                elif "text" in prompt:
                    text_prompts.append(prompt["text"])
                elif "value" in prompt:
                    text_prompts.append(prompt["value"])
                elif "prompt_text" in prompt:
                    # DuckDB structure uses prompt_text field
                    text_prompts.append(prompt["prompt_text"])
                else:
                    text_prompts.append(str(prompt))
            else:
                text_prompts.append(str(prompt))

        logger.info(f"Extracted {len(text_prompts)} prompts from transform dataset {dataset_config.get('name')}")
        return text_prompts

    except Exception as e:
        logger.error(f"Error loading transform dataset prompts: {e}")
        return []


async def _get_combination_dataset_prompts(dataset_config: Dict) -> List[str]:
    """Get prompts from combination dataset (combines multiple datasets)."""
    try:
        logger.info(f"Loading combination dataset: {dataset_config.get('name')}")

        # Combination datasets merge prompts from multiple source datasets
        prompts = dataset_config.get("prompts", [])

        text_prompts = []
        for prompt in prompts:
            if isinstance(prompt, dict):
                # Check different possible keys for prompt text
                if "text" in prompt:
                    text_prompts.append(prompt["text"])
                elif "value" in prompt:
                    text_prompts.append(prompt["value"])
                elif "prompt_text" in prompt:
                    # DuckDB structure uses prompt_text field
                    text_prompts.append(prompt["prompt_text"])
                else:
                    text_prompts.append(str(prompt))
            else:
                text_prompts.append(str(prompt))

        logger.info(f"Extracted {len(text_prompts)} prompts from combination dataset {dataset_config.get('name')}")
        return text_prompts

    except Exception as e:
        logger.error(f"Error loading combination dataset prompts: {e}")
        return []
