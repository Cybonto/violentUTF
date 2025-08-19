# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

# datasets/dataset_transformations.py

"""
Module: Dataset Transformations.

Contains functions for combining and transforming datasets.

Key Functions:
- combine_datasets(datasets_list): Combines multiple SeedPromptDatasets into one.
- transform_dataset_with_template(dataset, template_content): Applies a prompt template to a dataset.
- apply_template_to_prompt(prompt, template): Applies the template to a single prompt.

Dependencies:
- pyrit.models (SeedPrompt, SeedPromptDataset)
- Jinja2 for templating
- utils.error_handling
- utils.logging
"""

import logging
from typing import Any, Dict, List

from jinja2 import Environment, exceptions, select_autoescape
from pyrit.models import SeedPrompt, SeedPromptDataset
from utils.error_handling import TemplateError
from utils.logging import get_logger

logger = get_logger(__name__)


def combine_datasets(datasets_list: List[SeedPromptDataset]) -> SeedPromptDataset:
    """
    Combines multiple SeedPromptDatasets into one dataset.

    Parameters:
        datasets_list (list): A list of SeedPromptDataset objects to combine.

    Returns:
        combined_dataset (SeedPromptDataset): The combined SeedPromptDataset.

    Raises:
        ValueError: If datasets cannot be combined due to incompatibility.

    Upstream functions:
        - flow_combine_datasets() in 'pages/3_ConfigureDatasets.py'

    Downstream functions:
        - None

    Dependencies:
        - pyrit.models.SeedPromptDataset
    """
    try:
        combined_prompts = []
        for dataset in datasets_list:
            if not isinstance(dataset, SeedPromptDataset):
                logger.error("All items in datasets_list must be SeedPromptDataset instances.")
                raise ValueError("All items in datasets_list must be SeedPromptDataset instances.")
            combined_prompts.extend(dataset.prompts)
        combined_dataset = SeedPromptDataset(prompts=combined_prompts)
        logger.info(f"Combined {len(datasets_list)} datasets into one with {len(combined_prompts)} prompts.")
        return combined_dataset
    except Exception as e:
        logger.exception(f"Error combining datasets: {e}")
        raise ValueError(f"Error combining datasets: {e}") from e


def transform_dataset_with_template(dataset: SeedPromptDataset, template_content: str) -> SeedPromptDataset:
    """
    Applies a prompt template to the given dataset.

    Parameters:
        dataset (SeedPromptDataset): The dataset to transform.
        template_content (str): The content of the prompt template.

    Returns:
        transformed_dataset (SeedPromptDataset): The transformed dataset.

    Raises:
        TemplateError: If the template is invalid.

    Upstream functions:
        - flow_transform_datasets() in 'pages/3_ConfigureDatasets.py'

    Downstream functions:
        - apply_template_to_prompt()

    Dependencies:
        - Jinja2
        - utils.error_handling
    """
    try:
        env = Environment(
            autoescape=select_autoescape(
                enabled_extensions=["html", "xml", "j2", "jinja", "jinja2"], default_for_string=True, default=True
            )
        )
        template = env.from_string(template_content)
        transformed_prompts = []
        for prompt in dataset.prompts:
            transformed_prompt = apply_template_to_prompt(prompt, template)
            transformed_prompts.append(transformed_prompt)
        transformed_dataset = SeedPromptDataset(prompts=transformed_prompts)
        logger.info(f"Transformed dataset with template. Total transformed prompts: {len(transformed_prompts)}")
        return transformed_dataset
    except exceptions.TemplateError as e:
        logger.exception(f"Error in template: {e}")
        raise TemplateError(f"Error in template: {e}") from e
    except Exception as e:
        logger.exception(f"Error transforming dataset with template: {e}")
        raise TemplateError(f"Error transforming dataset with template: {e}") from e


def apply_template_to_prompt(prompt: SeedPrompt, template) -> SeedPrompt:
    """
    Applies the prompt template to a single SeedPrompt.

    Parameters:
        prompt (SeedPrompt): The original prompt.
        template (Template): Compiled Jinja2 Template object.

    Returns:
        transformed_prompt (SeedPrompt): The transformed SeedPrompt.

    Raises:
        TemplateError: If rendering the template fails.

    Upstream functions:
        - transform_dataset_with_template()

    Downstream functions:
        - None

    Dependencies:
        - Jinja2
        - pyrit.models.SeedPrompt
    """
    try:
        # Prepare context for the template rendering
        context = prompt.__dict__
        context = {k: v for k, v in context.items() if not k.startswith("_")}
        # Render the template
        rendered_value = template.render(**context)
        # Create a new SeedPrompt with the transformed value
        transformed_prompt = SeedPrompt(
            value=rendered_value,
            data_type=prompt.data_type,
            metadata=prompt.metadata,
            # Copy other necessary attributes
            id=prompt.id,
            name=prompt.name,
            dataset_name=prompt.dataset_name,
            harm_categories=prompt.harm_categories,
            description=prompt.description,
            authors=prompt.authors,
            groups=prompt.groups,
            source=prompt.source,
            date_added=prompt.date_added,
            added_by=prompt.added_by,
            parameters=prompt.parameters,
            prompt_group_id=prompt.prompt_group_id,
            prompt_group_alias=prompt.prompt_group_alias,
            sequence=prompt.sequence,
        )
        logger.debug(f"Applied template to prompt ID {prompt.id}")
        return transformed_prompt
    except exceptions.TemplateError as e:
        logger.exception(f"Error rendering template for prompt ID {prompt.id}: {e}")
        raise TemplateError(f"Error rendering template for prompt ID {prompt.id}: {e}") from e
    except Exception as e:
        logger.exception(f"Error applying template to prompt ID {prompt.id}: {e}")
        raise TemplateError(f"Error applying template to prompt ID {prompt.id}: {e}") from e
