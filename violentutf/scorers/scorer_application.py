# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

# scorers/scorer_application.py

"""
Module: Scorer Application

Contains functions to apply Scorers to inputs or datasets.

Key Functions:
- apply_scorer_to_input(scorer_instance, input_data): Applies a Scorer to a single input.
- apply_scorer_to_dataset(scorer_instance, dataset): Applies a Scorer to an entire dataset.

Dependencies:
- pyrit.models (for PromptRequestPiece, SeedPromptDataset, Score)
- utils.logging
- utils.error_handling
"""

import asyncio
import logging
from typing import List

from pyrit.models import PromptRequestPiece, Score, SeedPrompt, SeedPromptDataset
from pyrit.score import Scorer
from utils.error_handling import ScorerApplicationError
from utils.logging import get_logger

# Configure logger
logger = get_logger(__name__)


async def apply_scorer_to_input(scorer_instance: Scorer, input_data: PromptRequestPiece) -> List[Score]:
    """
    Applies the given Scorer to a single input data.

    Parameters:
        scorer_instance (Scorer): The Scorer instance to use.
        input_data (PromptRequestPiece): The data to score.

    Returns:
        scores (List[Score]): The scores returned by the Scorer.

    Raises:
        ScorerApplicationError: If scoring fails.

    Dependencies:
        - The Scorer instance must be properly instantiated.
        - The input_data must be properly formatted.
    """
    try:
        scores = await scorer_instance.score_async(input_data)
        logger.debug(f"Applied scorer to input_data. Scores: {scores}")
        return scores
    except Exception as e:
        logger.error(f"Error applying scorer to input: {e}")
        raise ScorerApplicationError(f"Error applying scorer to input: {e}") from e


def apply_scorer_to_input_sync(scorer_instance: Scorer, input_data: PromptRequestPiece) -> List[Score]:
    """
    Synchronous wrapper to apply the given Scorer to a single input data.

    Parameters:
        scorer_instance (Scorer): The Scorer instance to use.
        input_data (PromptRequestPiece): The data to score.

    Returns:
        scores (List[Score]): The scores returned by the Scorer.

    Raises:
        ScorerApplicationError: If scoring fails.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        scores = loop.run_until_complete(apply_scorer_to_input(scorer_instance, input_data))
        loop.close()
        return scores
    except Exception as e:
        logger.error(f"Error applying scorer to input data synchronously: {e}")
        raise ScorerApplicationError(f"Error applying scorer to input data synchronously: {e}") from e


async def apply_scorer_to_dataset(scorer_instance: Scorer, dataset: SeedPromptDataset) -> List[Score]:
    """
    Applies the given Scorer to an entire dataset.

    Parameters:
        scorer_instance (Scorer): The Scorer instance to use.
        dataset (SeedPromptDataset): The dataset containing prompts to score.

    Returns:
        scores (List[Score]): A list of scores for each prompt in the dataset.

    Raises:
        ScorerApplicationError: If scoring fails.

    Dependencies:
        - The Scorer instance must be properly instantiated.
        - The dataset must contain valid prompts.
    """
    all_scores = []
    try:
        # Collect all PromptRequestPieces from the dataset
        # Assuming dataset.prompts is a list of SeedPrompts
        # Convert SeedPrompts to PromptRequestPieces
        request_pieces = []
        for seed_prompt in dataset.prompts:
            # Create a PromptRequestPiece for each seed_prompt
            prp = PromptRequestPiece(
                role="user", original_value=seed_prompt.value, original_value_data_type=seed_prompt.data_type
            )
            request_pieces.append(prp)

        # Apply the scorer to each request piece asynchronously
        tasks = []
        for request_piece in request_pieces:
            task = scorer_instance.score_async(request_piece)
            tasks.append(task)

        scored_results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, scores in enumerate(scored_results):
            if isinstance(scores, Exception):
                logger.error(f"Error scoring request_piece '{request_pieces[i].id}': {scores}")
                raise ScorerApplicationError(
                    f"Error scoring request_piece '{request_pieces[i].id}': {scores}"
                ) from scores
            else:
                all_scores.extend(scores)
                logger.debug(f"Scored request_piece '{request_pieces[i].id}': {scores}")

        dataset_name = dataset.name if hasattr(dataset, "name") else "Unnamed Dataset"
        logger.info(f"Applied scorer to dataset '{dataset_name}'. Total scores: {len(all_scores)}")
        return all_scores
    except Exception as e:
        logger.error(f"Error applying scorer to dataset: {e}")
        raise ScorerApplicationError(f"Error applying scorer to dataset: {e}") from e


def apply_scorer_to_dataset_sync(scorer_instance: Scorer, dataset: SeedPromptDataset) -> List[Score]:
    """
    Synchronous wrapper to apply the Scorer to an entire dataset.

    Parameters:
        scorer_instance (Scorer): The Scorer instance to use.
        dataset (SeedPromptDataset): The dataset containing prompts to score.

    Returns:
        scores (List[Score]): A list of scores for each prompt in the dataset.

    Raises:
        ScorerApplicationError: If scoring fails.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        scores = loop.run_until_complete(apply_scorer_to_dataset(scorer_instance, dataset))
        loop.close()
        return scores
    except Exception as e:
        logger.error(f"Error applying scorer to dataset synchronously: {e}")
        raise ScorerApplicationError(f"Error applying scorer to dataset synchronously: {e}") from e
