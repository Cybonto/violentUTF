# converters/converter_application.py

"""
Module: Converter Application

Contains functions to apply converters to prompts and datasets.

Key Functions:
- apply_converter_to_prompt(converter, prompt): Applies a converter to a single prompt.
- apply_converter_to_dataset(converter, dataset): Applies a converter to an entire dataset.
- preview_converter_effect(converter, prompt): Returns a preview of applying converter to a prompt.

Dependencies:
- pyrit.models (SeedPrompt, SeedPromptDataset)
- pyrit.prompt_converter
- asyncio
- typing
- utils.error_handling
- utils.logging
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from pyrit.models import SeedPrompt, SeedPromptDataset
from pyrit.prompt_converter import PromptConverter
from utils.error_handling import ConverterApplicationError
from utils.logging import get_logger

logger = get_logger(__name__)


async def apply_converter_to_prompt(
    converter: PromptConverter, prompt: SeedPrompt
) -> SeedPrompt:
    """
    Applies a converter to a single prompt asynchronously.

    Parameters:
        converter (PromptConverter): The converter instance to apply.
        prompt (SeedPrompt): The prompt to which the converter will be applied.

    Returns:
        transformed_prompt (SeedPrompt): The transformed prompt.

    Raises:
        ConverterApplicationError: If application fails.

    Dependencies:
        - asyncio
        - pyrit.prompt_converter
    """
    try:
        # Handle input and output data types
        input_type = prompt.data_type
        # Apply the converter
        converter_result = await converter.convert_async(
            prompt=prompt.value, input_type=input_type
        )
        transformed_value = converter_result.output_text
        output_type = converter_result.output_type

        # Create a new SeedPrompt with the transformed value
        transformed_prompt = SeedPrompt(
            id=prompt.id,
            value=transformed_value,
            value_sha256=None,
            data_type=output_type,
            name=prompt.name,
            dataset_name=prompt.dataset_name,
            harm_categories=prompt.harm_categories,
            description=prompt.description,
            authors=prompt.authors,
            groups=prompt.groups,
            source=prompt.source,
            date_added=prompt.date_added,
            added_by=prompt.added_by,
            metadata=prompt.metadata,
            parameters=prompt.parameters,
            prompt_group_id=prompt.prompt_group_id,
            prompt_group_alias=prompt.prompt_group_alias,
            sequence=prompt.sequence,
        )

        logger.debug(f"Applied converter to prompt ID {prompt.id}")
        return transformed_prompt

    except Exception as e:
        logger.error(f"Error applying converter to prompt ID {prompt.id}: {e}")
        raise ConverterApplicationError(
            f"Error applying converter to prompt ID {prompt.id}: {e}"
        ) from e


async def apply_converter_to_dataset(
    converter: PromptConverter, dataset: SeedPromptDataset
) -> SeedPromptDataset:
    """
    Applies a converter to each prompt in a dataset asynchronously.

    Parameters:
        converter (PromptConverter): The converter instance to apply.
        dataset (SeedPromptDataset): The dataset to which the converter will be applied.

    Returns:
        transformed_dataset (SeedPromptDataset): The transformed dataset.

    Raises:
        ConverterApplicationError: If application fails.

    Dependencies:
        - asyncio
    """
    try:
        transformed_prompts = []
        # Create a list of tasks
        tasks = [
            apply_converter_to_prompt(converter, prompt) for prompt in dataset.prompts
        ]
        # Run tasks concurrently
        transformed_prompts = await asyncio.gather(*tasks)

        transformed_dataset = SeedPromptDataset(
            prompts=transformed_prompts,
            data_type=transformed_prompts[0].data_type,
            name=dataset.name,
            dataset_name=dataset.dataset_name,
            harm_categories=dataset.harm_categories,
            description=dataset.description,
            authors=dataset.authors,
            groups=dataset.groups,
            source=dataset.source,
            date_added=dataset.date_added,
            added_by=dataset.added_by,
        )
        logger.info(
            f"Applied converter to dataset with {len(dataset.prompts)} prompts."
        )
        return transformed_dataset

    except Exception as e:
        logger.error(f"Error applying converter to dataset: {e}")
        raise ConverterApplicationError(
            f"Error applying converter to dataset: {e}"
        ) from e


async def preview_converter_effect(
    converter: PromptConverter, prompt: SeedPrompt
) -> str:
    """
    Applies a converter to a single prompt asynchronously and returns the transformed value.

    Parameters:
        converter (PromptConverter): The converter instance to apply.
        prompt (SeedPrompt): The prompt to which the converter will be applied.

    Returns:
        transformed_value (str): The transformed prompt value.

    Raises:
        ConverterApplicationError: If application fails.

    Dependencies:
        - asyncio
    """
    try:
        transformed_prompt = await apply_converter_to_prompt(converter, prompt)
        return transformed_prompt.value
    except Exception as e:
        logger.error(f"Error previewing converter effect: {e}")
        raise ConverterApplicationError(
            f"Error previewing converter effect: {e}"
        ) from e


def apply_converter_to_dataset_sync(
    converter: PromptConverter, dataset: SeedPromptDataset
) -> SeedPromptDataset:
    """
    Synchronous wrapper to apply a converter to a dataset.

    Parameters:
        converter (PromptConverter): The converter instance to apply.
        dataset (SeedPromptDataset): The dataset to which the converter will be applied.

    Returns:
        transformed_dataset (SeedPromptDataset): The transformed dataset.

    Raises:
        ConverterApplicationError: If application fails.

    Dependencies:
        - asyncio
    """
    try:
        # Use asyncio.run to execute the coroutine
        transformed_dataset = asyncio.run(
            apply_converter_to_dataset(converter, dataset)
        )
        return transformed_dataset
    except Exception as e:
        logger.error(f"Error in apply_converter_to_dataset_sync: {e}")
        raise ConverterApplicationError(
            f"Error applying converter to dataset (sync): {e}"
        ) from e


def apply_converter_to_prompt_sync(
    converter: PromptConverter, prompt: SeedPrompt
) -> SeedPrompt:
    """
    Synchronous wrapper to apply a converter to a single prompt.

    Parameters:
        converter (PromptConverter): The converter instance to apply.
        prompt (SeedPrompt): The prompt to which the converter will be applied.

    Returns:
        transformed_prompt (SeedPrompt): The transformed prompt.

    Raises:
        ConverterApplicationError: If application fails.

    Dependencies:
        - asyncio
    """
    try:
        # Use asyncio.run to execute the coroutine
        transformed_prompt = asyncio.run(apply_converter_to_prompt(converter, prompt))
        return transformed_prompt
    except Exception as e:
        logger.error(f"Error in apply_converter_to_prompt_sync: {e}")
        raise ConverterApplicationError(
            f"Error applying converter to prompt (sync): {e}"
        ) from e
