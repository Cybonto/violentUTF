import logging
import os
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


async def get_dataset_prompts(
    dataset_id: str,
    sample_size: Optional[int] = None,
    user_context: Optional[str] = None,
) -> List[str]:
    """Get prompts from dataset for orchestrator execution"""
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
            prompts = await _get_memory_dataset_prompts(dataset_config)
        elif dataset_config["source_type"] == "converter":
            prompts = await _get_converter_dataset_prompts(dataset_config)
        elif dataset_config["source_type"] == "transform":
            prompts = await _get_transform_dataset_prompts(dataset_config)
        elif dataset_config["source_type"] == "combination":
            prompts = await _get_combination_dataset_prompts(dataset_config)
        else:
            raise ValueError(
                f"Unsupported dataset source type: {dataset_config['source_type']}"
            )

        # Apply sampling if requested
        if sample_size and len(prompts) > sample_size:
            import random

            prompts = random.sample(prompts, sample_size)

        logger.info(f"Loaded {len(prompts)} prompts from dataset {dataset_id}")
        return prompts

    except Exception as e:
        logger.error(f"Error getting dataset prompts: {e}")
        raise


async def _get_dataset_by_id(
    dataset_id: str, user_context: Optional[str] = None
) -> Dict[str, Any]:
    """Get dataset configuration by ID from backend service"""
    try:
        # Get datasets directly from DuckDB without authentication context
        # This is safe for internal service-to-service calls
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
                if (
                    dataset_data.get("id") == dataset_id
                    or dataset_data.get("name") == dataset_id
                ):
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
    """Get prompts from native dataset"""
    # Extract prompts from native dataset
    dataset_type = dataset_config.get("dataset_type")

    # Get prompts from the dataset configuration
    prompts = dataset_config.get("prompts", [])
    logger.info(
        f"Native dataset {dataset_config.get('name')} has {len(prompts)} prompts"
    )

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
    """Get prompts from local uploaded dataset"""
    # Extract prompts from local dataset
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


async def _get_memory_dataset_prompts(dataset_config: Dict) -> List[str]:
    """Get prompts from PyRIT memory dataset using real memory database access"""
    try:
        dataset_id = dataset_config.get("id", "memory_0")
        dataset_name = dataset_config.get("name", "Unknown")

        logger.info(
            f"Loading memory dataset prompts for {dataset_name} (ID: {dataset_id})"
        )

        # Try to access real PyRIT memory database
        prompts = await _load_real_memory_dataset_prompts(dataset_id)

        if prompts:
            logger.info(
                f"Loaded {len(prompts)} real prompts from PyRIT memory dataset {dataset_name}"
            )
            return prompts
        else:
            logger.warning(f"No prompts found in PyRIT memory for dataset {dataset_id}")
            # Return empty list instead of mock data - let calling code handle appropriately
            return []

    except Exception as e:
        logger.error(f"Error accessing PyRIT memory dataset {dataset_id}: {e}")
        # Return empty list instead of fallback mock data
        return []


async def _load_real_memory_dataset_prompts(dataset_id: str) -> List[str]:
    """Load actual prompts from PyRIT memory database files"""
    try:
        import os
        import sqlite3

        from pyrit.memory import CentralMemory

        prompts = []

        # First try to get prompts from active PyRIT memory instance
        try:
            memory_instance = CentralMemory.get_memory_instance()
            if memory_instance:
                logger.info(
                    f"Found active PyRIT memory instance for dataset {dataset_id}"
                )

                # Get conversation pieces from memory that could be prompts
                # Look for user-role pieces that contain the original prompts
                conversation_pieces = memory_instance.get_conversation()

                for piece in conversation_pieces:
                    if piece.role == "user" and piece.original_value:
                        # Add user prompts from memory
                        prompts.append(piece.original_value)

                if prompts:
                    logger.info(
                        f"Extracted {len(prompts)} prompts from active PyRIT memory"
                    )
                    return prompts[:50]  # Limit for performance

        except ValueError:
            logger.info(
                "No active PyRIT memory instance found, trying direct database access"
            )

        # If no active memory or no prompts found, try direct database file access
        memory_db_paths = []

        # Check common PyRIT memory database locations
        potential_paths = [
            "/app/app_data/violentutf/api_memory",  # Docker API memory
            "./violentutf/app_data/violentutf",  # Local Streamlit memory
            os.path.expanduser("~/.pyrit"),  # User PyRIT directory
            "./app_data/violentutf",  # Relative app data
        ]

        for base_path in potential_paths:
            if os.path.exists(base_path):
                # Look for any .db files that might contain memory data
                for file in os.listdir(base_path):
                    if file.endswith(".db") and "memory" in file.lower():
                        db_path = os.path.join(base_path, file)
                        memory_db_paths.append(db_path)

        # Try to extract prompts from found database files
        for db_path in memory_db_paths:
            try:
                logger.info(f"Attempting to read PyRIT memory database: {db_path}")

                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()

                    # Query for prompt request pieces with user role
                    cursor.execute(
                        """
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
                        LIMIT 50
                    """
                    )

                    rows = cursor.fetchall()
                    for row in rows:
                        if row[0] and len(row[0].strip()) > 0:
                            prompts.append(row[0].strip())

                if prompts:
                    logger.info(
                        f"Extracted {len(prompts)} prompts from PyRIT database {db_path}"
                    )
                    return prompts

            except sqlite3.Error as db_error:
                logger.debug(f"Could not read database {db_path}: {db_error}")
                continue
            except Exception as db_error:
                logger.debug(f"Error accessing database {db_path}: {db_error}")
                continue

        logger.info(f"No PyRIT memory data found for dataset {dataset_id}")
        return []

    except Exception as e:
        logger.error(f"Error loading real memory dataset prompts: {e}")
        return []


async def _get_converter_dataset_prompts(dataset_config: Dict) -> List[str]:
    """Get prompts from converter-generated dataset"""
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

        logger.info(
            f"Extracted {len(text_prompts)} prompts from converter dataset {dataset_config.get('name')}"
        )
        return text_prompts

    except Exception as e:
        logger.error(f"Error loading converter dataset prompts: {e}")
        return []


async def _get_transform_dataset_prompts(dataset_config: Dict) -> List[str]:
    """Get prompts from transform-generated dataset"""
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

        logger.info(
            f"Extracted {len(text_prompts)} prompts from transform dataset {dataset_config.get('name')}"
        )
        return text_prompts

    except Exception as e:
        logger.error(f"Error loading transform dataset prompts: {e}")
        return []


async def _get_combination_dataset_prompts(dataset_config: Dict) -> List[str]:
    """Get prompts from combination dataset (combines multiple datasets)"""
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

        logger.info(
            f"Extracted {len(text_prompts)} prompts from combination dataset {dataset_config.get('name')}"
        )
        return text_prompts

    except Exception as e:
        logger.error(f"Error loading combination dataset prompts: {e}")
        return []
