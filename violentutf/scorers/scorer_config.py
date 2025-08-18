# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

# scorers/scorer_config.py

"""
Module: Scorer Configuration

Contains functions for loading available Scorer classes, retrieving Scorer parameters,
and managing Scorer configurations.

Key Functions:
- list_scorer_types(): List all available Scorer types from pyrit.score.
- get_scorer_params(scorer_type): Retrieve detailed parameters for a Scorer's __init__ method.
- instantiate_scorer(scorer_type, params): Instantiate a Scorer class with provided parameters.
- add_scorer(scorer_name, scorer_type, params): Add a new Scorer configuration.
- load_scorers(): Load all configured Scorer configurations from the parameter file.
- get_scorer(scorer_name): Retrieve and instantiate a configured Scorer by name.
- delete_scorer(scorer_name): Delete a configured Scorer.
- test_scorer_async(scorer_name, sample_input): Test a configured Scorer asynchronously.
- test_scorer(scorer_name, sample_input): Synchronous wrapper to test a configured Scorer.
- update_parameter_file(configured_scorers): Update the YAML parameter file with current Scorer configurations.

Dependencies:
- logging
- inspect
- yaml
- os
- asyncio
- pathlib.Path
- typing
- pyrit.score
- pyrit.models
- pyrit.prompt_target
- utils.logging
- utils.error_handling
"""

import asyncio
import collections.abc  # To check for Callable if needed, though not typical for scorers
import inspect
import logging
import os
from pathlib import Path
from typing import Tuple  # Added Tuple here
from typing import Any, Dict, List, Literal, Optional, Type, Union, get_args, get_origin, get_type_hints

# PyRIT imports
import pyrit.score as score  # Import the pyrit.score module as score
import yaml
from pyrit.models import Score  # Import Score class from pyrit.models
from pyrit.models import PromptRequestPiece
from pyrit.prompt_target import PromptChatTarget, PromptShieldTarget
from pyrit.score import Scorer, TrueFalseQuestion  # Import Scorer class
from utils.error_handling import (
    ScorerConfigurationError,
    ScorerDeletionError,
    ScorerInstantiationError,
    ScorerLoadingError,
    ScorerTestingError,
)

# Project-specific imports
from utils.logging import get_logger

# Configure logger
logger = get_logger(__name__)

# Define the parameter file path
PARAMETER_FILE = Path("parameters/scorers.yaml")


def list_scorer_types() -> List[str]:
    """
    Lists all available concrete Scorer types defined in pyrit.score.

    Returns:
        List[str]: A list of available Scorer class names.
    """
    available_scorers = []
    try:
        # Use pyrit.score.__all__ if available and maintained, otherwise inspect members
        if hasattr(score, "__all__"):
            all_names = score.__all__
            for name in all_names:
                obj = getattr(score, name)
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, Scorer)
                    and obj is not Scorer
                    and not inspect.isabstract(obj)
                ):
                    available_scorers.append(name)
        else:
            # Fallback to inspecting all members
            for name, obj in inspect.getmembers(score):
                if inspect.isclass(obj) and issubclass(obj, Scorer) and obj is not Scorer:
                    # Double check it's defined in pyrit.score, not just imported there
                    if hasattr(obj, "__module__") and obj.__module__.startswith("pyrit.score"):
                        if not inspect.isabstract(obj):
                            available_scorers.append(name)

        available_scorers.sort()  # Sort for consistency
        logger.debug(f"Available scorer types: {available_scorers}")
        return available_scorers
    except Exception as e:
        logger.error(f"Error listing scorer types: {e}", exc_info=True)
        return []


def get_scorer_params(scorer_type: str) -> List[Dict[str, Any]]:
    """
    Retrieves detailed parameters for the specified Scorer type's __init__ method.

    Includes type information, requirement status, defaults, and flags complex types.

    Parameters:
        scorer_type (str): The name of the Scorer class.

    Returns:
        List[Dict[str, Any]]: A list of parameter definitions.

    Raises:
        ScorerLoadingError: If the scorer type is not found or params can't be retrieved.
    """
    try:
        scorer_class = getattr(score, scorer_type)
    except AttributeError:
        logger.error(f"Scorer type '{scorer_type}' not found in pyrit.score module.")
        raise ScorerLoadingError(f"Scorer type '{scorer_type}' not found.")

    try:
        init_method = scorer_class.__init__
        if init_method is object.__init__:
            logger.debug(f"Scorer '{scorer_type}' uses default object.__init__, no parameters.")
            return []
        init_signature = inspect.signature(init_method)
    except ValueError as e:
        logger.error(f"Could not get signature for {scorer_type}.__init__: {e}. Assuming no parameters.")
        return []
    except TypeError as e:
        logger.error(f"TypeError getting signature for {scorer_type}.__init__: {e}. Assuming no parameters.")
        return []

    try:
        type_hints = get_type_hints(init_method)
    except Exception as e:
        logger.warning(f"Could not get type hints for {scorer_type}.__init__: {e}. Type info may be incomplete.")
        type_hints = {}

    param_definitions = []
    for param_name, param in init_signature.parameters.items():
        if param.name == "self" or param.kind in [param.VAR_POSITIONAL, param.VAR_KEYWORD]:
            continue

        raw_annotation = type_hints.get(param_name, Any)
        origin_type = get_origin(raw_annotation)
        type_args = get_args(raw_annotation)

        primary_type = raw_annotation
        literal_choices = None
        type_str = (
            str(raw_annotation)
            .replace("typing.", "")
            .replace("pyrit.score.", "")
            .replace("pyrit.prompt_target.", "")
            .replace("pathlib.", "")
        )

        # --- Determine Primary Type, Literal Choices, and String Representation ---
        if origin_type is Literal:
            literal_choices = list(get_args(raw_annotation))
            if literal_choices:
                primary_type = type(literal_choices[0])
                type_str = f"Literal[{', '.join(repr(choice) for choice in literal_choices)}]"
            else:
                primary_type = Any
                type_str = "Literal[]"
        elif origin_type is Union:
            non_none_types = [t for t in type_args if t is not type(None)]
            if len(non_none_types) == 1:
                primary_type = non_none_types[0]
                inner_origin = get_origin(primary_type)
                inner_args = get_args(primary_type)
                if inner_origin is Literal:
                    literal_choices = list(inner_args)
                    if literal_choices:
                        type_str = f"Optional[Literal[{', '.join(repr(choice) for choice in literal_choices)}]]"
                        primary_type = type(literal_choices[0])
                    else:
                        type_str = "Optional[Literal[]]"
                        primary_type = Any
                else:
                    inner_type_str = (
                        str(primary_type).replace("typing.", "").replace("pyrit.", "").replace("pathlib.", "")
                    )
                    type_str = f"Optional[{inner_type_str}]"
            else:
                primary_type = Union
                type_str = str(raw_annotation).replace("typing.", "").replace("pyrit.", "")
        elif origin_type is list or origin_type is List:
            primary_type = list
            type_str = f"List[{str(type_args[0]).replace('typing.', '') if type_args else 'Any'}]"
        elif origin_type is tuple or origin_type is Tuple:
            primary_type = tuple
            type_str = f"Tuple[{', '.join(str(t).replace('typing.', '') for t in type_args)}]" if type_args else "Tuple"
        else:
            if isinstance(raw_annotation, type):
                primary_type = raw_annotation
            else:
                primary_type = Any
                type_str = str(raw_annotation).replace("typing.", "").replace("pyrit.", "").replace("pathlib.", "")

        # --- Identify Complex Types to Skip in Generic UI ---
        complex_types_to_skip = (
            PromptChatTarget,
            PromptShieldTarget,
            Scorer,
            Path,
            TrueFalseQuestion,
            collections.abc.Callable,
        )
        skip_in_ui = isinstance(primary_type, type) and issubclass(primary_type, complex_types_to_skip)
        if (
            primary_type is list
            and type_args
            and isinstance(type_args[0], type)
            and issubclass(type_args[0], complex_types_to_skip)
        ):
            skip_in_ui = True
        if isinstance(raw_annotation, type) and issubclass(raw_annotation, complex_types_to_skip):
            skip_in_ui = True

        # --- Get Default Value ---
        default_value = None if param.default == param.empty else param.default

        param_info = {
            "name": param_name,
            "type_str": type_str,
            "raw_type": raw_annotation,
            "primary_type": primary_type,
            "literal_choices": literal_choices,
            "required": param.default == param.empty,
            "default": default_value,
            "skip_in_ui": skip_in_ui,
            "description": param_name.replace("_", " ").capitalize(),
        }
        param_definitions.append(param_info)

    logger.debug(f"Parameters for scorer '{scorer_type}': {param_definitions}")
    return param_definitions


def instantiate_scorer(scorer_type: str, params: Dict[str, Any]) -> Scorer:
    """
    Instantiates a Scorer class with the provided parameters.

    Parameters:
        scorer_type (str): The name of the Scorer class.
        params (Dict[str, Any]): Parameters required to instantiate the Scorer.

    Returns:
        Scorer: An instance of the specified Scorer class.

    Raises:
        ScorerLoadingError: If the scorer type is not found.
        ScorerInstantiationError: If instantiation fails.
    """
    logger.debug(f"Attempting to instantiate scorer '{scorer_type}' with params: {params}")
    try:
        scorer_class = getattr(score, scorer_type)
    except AttributeError as e:
        logger.error(f"Scorer type '{scorer_type}' not found.")
        raise ScorerLoadingError(f"Scorer type '{scorer_type}' not found.") from e

    try:
        init_method = scorer_class.__init__
        if init_method is object.__init__:
            scorer_init_params = {}
        else:
            scorer_init_params = inspect.signature(init_method).parameters
    except (ValueError, TypeError) as e:
        logger.error(f"Could not get/parse signature for {scorer_type}.__init__: {e}. Assuming no named params needed.")
        scorer_init_params = {}

    # Determine the names of parameters, excluding self, *args, **kwargs
    init_param_names = [
        pname
        for pname, p in scorer_init_params.items()
        if pname != "self" and p.kind in [inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY]
    ]
    logger.debug(f"Found __init__ param names for {scorer_type}: {init_param_names}")

    if not init_param_names:
        if params:
            logger.warning(
                f"Scorer '{scorer_type}' takes no parameters, but received: {list(params.keys())}. Ignoring them."
            )
        try:
            scorer_instance = scorer_class()
            logger.info(f"Scorer '{scorer_type}' instantiated without parameters.")
        except TypeError as te:
            logger.error(f"TypeError during instantiation of zero-arg scorer '{scorer_type}': {te}", exc_info=True)
            raise ScorerInstantiationError(f"TypeError instantiating {scorer_type}(): {te}") from te
    else:
        # Filter and validate parameters
        filtered_params = {k: v for k, v in params.items() if k in init_param_names}
        logger.debug(f"Filtered params for {scorer_type}: {filtered_params}")

        required_param_names = {
            p.name
            for p in scorer_init_params.values()
            if p.name in init_param_names and p.default == inspect.Parameter.empty
        }
        missing_required = required_param_names - set(filtered_params.keys())

        if missing_required:
            params_safe_log = {k: ("***" if "key" in k.lower() else v) for k, v in filtered_params.items()}
            logger.error(
                f"Missing required parameters for {scorer_type}: {missing_required}. Provided: {params_safe_log}"
            )
            raise ScorerInstantiationError(f"Missing required parameters for {scorer_type}: {missing_required}")

        try:
            scorer_instance = scorer_class(**filtered_params)
            params_safe_log = {k: ("***" if "key" in k.lower() else v) for k, v in filtered_params.items()}
            logger.info(f"Scorer '{scorer_type}' instantiated with parameters: {params_safe_log}")
        except TypeError as te:
            params_safe_log = {k: ("***" if "key" in k.lower() else v) for k, v in filtered_params.items()}
            logger.error(
                f"TypeError during instantiation of '{scorer_type}' with params {params_safe_log}: {te}", exc_info=True
            )
            raise ScorerInstantiationError(
                f"TypeError instantiating {scorer_type}: {te}. Check parameter types/counts."
            ) from te

    return scorer_instance


# --- Configuration Management Functions ---


def add_scorer(scorer_name: str, scorer_type: str, params: Dict[str, Any]) -> Scorer:
    """
    Adds a new Scorer configuration after validating instantiation.

    Parameters:
        scorer_name: Unique name for this configuration.
        scorer_type: The Scorer class name.
        params: Parameters required to instantiate the Scorer.

    Returns:
        The instantiated Scorer object.

    Raises:
        ScorerConfigurationError: If the name exists or saving fails.
        ScorerInstantiationError: If instantiation fails.
    """
    configured_scorers = load_scorers()
    if scorer_name in configured_scorers:
        logger.error(f"Scorer name '{scorer_name}' already exists.")
        raise ScorerConfigurationError(f"Scorer name '{scorer_name}' already exists.")

    # Try instantiating first to validate type and params before saving
    try:
        # Note: For scorers needing Path objects, ensure params contains Path instances
        # or add conversion logic here/in instantiate_scorer if needed.
        # Example: Convert string paths to Path objects if required by __init__
        params_processed = params.copy()
        # Potential Path conversion (if UI provides strings but Scorer needs Path):
        # scorer_class_ref = getattr(score, scorer_type, None)
        # if scorer_class_ref:
        #    sig = inspect.signature(scorer_class_ref.__init__)
        #    hints = get_type_hints(scorer_class_ref.__init__)
        #    for name, value in params_processed.items():
        #        if name in sig.parameters and hints.get(name) is Path and isinstance(value, str):
        #             params_processed[name] = Path(value)

        scorer_instance = instantiate_scorer(scorer_type, params_processed)
    except (ScorerLoadingError, ScorerInstantiationError) as e:
        # Re-raise errors related to loading/instantiation
        raise e
    except Exception as e:
        # Catch other potential errors during pre-processing or instantiation
        logger.exception(f"Unexpected error during pre-save instantiation check for {scorer_type}: {e}")
        raise ScorerInstantiationError(f"Validation failed for {scorer_type}: {e}") from e

    # Save configuration if instantiation was successful
    configured_scorers[scorer_name] = {
        "type": scorer_type,
        # Store the original params provided, assuming UI handles types correctly
        # If Path conversion happened, decide whether to store string or Path object in YAML
        "params": params,
    }
    update_parameter_file(configured_scorers)
    logger.info(f"Scorer '{scorer_name}' of type '{scorer_type}' added.")
    return scorer_instance


def load_scorers() -> Dict[str, Dict[str, Any]]:
    """
    Loads all configured Scorer configurations from the parameter file.

    Returns:
        Dict[str, Dict[str, Any]]: Scorer configurations keyed by name.
                                   Inner dict has 'type' and 'params'.
    """
    if not PARAMETER_FILE.exists():
        logger.debug(f"Parameter file '{PARAMETER_FILE}' not found. Returning empty configuration.")
        return {}
    try:
        with open(PARAMETER_FILE, "r") as f:
            # Use yaml.FullLoader or yaml.Loader if needing to load custom Python objects (like Path)
            # For simple types, safe_load is best. If storing Path objects, need custom handling or use Loader.
            data = yaml.safe_load(f)
            if data is None:
                data = {}
            logger.debug(f"Loaded scorer configurations ({len(data)} items).")
            return data
    except yaml.YAMLError as ye:
        logger.error(f"Error parsing YAML file '{PARAMETER_FILE}': {ye}", exc_info=True)
        raise ScorerConfigurationError(f"Error parsing scorer configurations file: {ye}") from ye
    except Exception as e:
        logger.error(f"Error loading scorer configurations: {e}", exc_info=True)
        raise ScorerConfigurationError(f"Error loading scorer configurations: {e}") from e


def get_scorer(scorer_name: str) -> Scorer:
    """
    Retrieves and instantiates a configured Scorer by name.

    Parameters:
        scorer_name: The name of the Scorer configuration.

    Returns:
        Scorer: The instantiated Scorer object.

    Raises:
        ScorerConfigurationError: If the scorer config is not found.
        ScorerInstantiationError: If instantiation fails.
    """
    configured_scorers = load_scorers()
    if scorer_name not in configured_scorers:
        logger.error(f"Scorer configuration '{scorer_name}' not found.")
        raise ScorerConfigurationError(f"Scorer configuration '{scorer_name}' not found.")

    scorer_config = configured_scorers[scorer_name]
    scorer_type = scorer_config.get("type")
    params = scorer_config.get("params", {})  # Default to empty dict if params missing

    if not scorer_type:
        logger.error(f"Scorer configuration '{scorer_name}' is missing the 'type' field.")
        raise ScorerConfigurationError(f"Scorer configuration '{scorer_name}' is invalid (missing type).")

    # Handle potential Path object conversion if stored as string in YAML
    # (Requires knowing which parameters expect Path)
    try:
        # Example: If 'likert_scale_path' needs to be Path, convert it
        # This ideally uses info from get_scorer_params but that adds complexity here.
        # Manual conversion based on known scorer types:
        params_processed = params.copy()
        if (
            scorer_type == "SelfAskLikertScorer"
            and "likert_scale_path" in params_processed
            and isinstance(params_processed["likert_scale_path"], str)
        ):
            params_processed["likert_scale_path"] = Path(params_processed["likert_scale_path"])
        # Add similar conversions for SelfAskCategoryScorer, SelfAskScaleScorer, SelfAskTrueFalseScorer if needed
        elif (
            scorer_type == "SelfAskCategoryScorer"
            and "content_classifier" in params_processed
            and isinstance(params_processed["content_classifier"], str)
        ):
            params_processed["content_classifier"] = Path(params_processed["content_classifier"])
        elif scorer_type == "SelfAskScaleScorer":
            if "scale_arguments_path" in params_processed and isinstance(
                params_processed.get("scale_arguments_path"), str
            ):
                params_processed["scale_arguments_path"] = Path(params_processed["scale_arguments_path"])
            if "system_prompt_path" in params_processed and isinstance(params_processed.get("system_prompt_path"), str):
                params_processed["system_prompt_path"] = Path(params_processed["system_prompt_path"])
        # Add more conversions as necessary based on scorer __init__ signatures requiring Path

        scorer_instance = instantiate_scorer(scorer_type, params_processed)
        logger.debug(f"Retrieved and instantiated scorer '{scorer_name}' of type '{scorer_type}'.")
        return scorer_instance
    except (ScorerLoadingError, ScorerInstantiationError) as e:
        logger.error(f"Failed to instantiate scorer '{scorer_name}' from config: {e}")
        raise e  # Re-raise specific errors
    except Exception as e:
        logger.exception(f"Unexpected error getting scorer '{scorer_name}': {e}")
        raise ScorerInstantiationError(f"Unexpected error getting scorer '{scorer_name}': {e}") from e


def delete_scorer(scorer_name: str) -> bool:
    """
    Deletes a configured Scorer.

    Parameters:
        scorer_name: The name of the Scorer configuration to delete.

    Returns:
        True if deletion was successful, False if the Scorer was not found.

    Raises:
        ScorerDeletionError: If saving the updated configurations fails.
    """
    configured_scorers = load_scorers()
    if scorer_name not in configured_scorers:
        logger.warning(f"Scorer configuration '{scorer_name}' not found. Cannot delete.")
        return False
    try:
        del configured_scorers[scorer_name]
        update_parameter_file(configured_scorers)
        logger.info(f"Scorer configuration '{scorer_name}' deleted.")
        return True
    except ScorerConfigurationError as e:  # Catch specific error from update_parameter_file
        logger.error(f"Failed to save configuration after deleting scorer '{scorer_name}': {e}")
        raise ScorerDeletionError(f"Failed to save configuration after deleting scorer '{scorer_name}': {e}") from e
    except Exception as e:
        logger.error(f"Error deleting scorer configuration '{scorer_name}': {e}", exc_info=True)
        raise ScorerDeletionError(f"Error deleting scorer configuration '{scorer_name}': {e}") from e


async def test_scorer_async(scorer_name: str, sample_input: PromptRequestPiece) -> List[Score]:
    """
    Tests a configured Scorer asynchronously with a sample input.

    Parameters:
        scorer_name: The name of the configured Scorer to test.
        sample_input: The input data (PromptRequestPiece) to score.

    Returns:
        List[Score]: The Scorer's output on the sample input.

    Raises:
        ScorerConfigurationError: If the scorer config is not found.
        ScorerInstantiationError: If scorer instantiation fails.
        ScorerTestingError: If scoring the sample input fails.
    """
    # get_scorer handles loading and instantiation errors
    scorer_instance = get_scorer(scorer_name)
    try:
        logger.debug(f"Testing scorer '{scorer_name}' with input: {sample_input}")
        # Scorer methods are async, so await directly
        scores = await scorer_instance.score_async(sample_input)
        logger.info(f"Scorer '{scorer_name}' tested successfully. Scores: {scores}")
        return scores
    except Exception as e:
        logger.error(f"Error testing scorer '{scorer_name}': {e}", exc_info=True)
        raise ScorerTestingError(f"Error testing scorer '{scorer_name}': {e}") from e


# Keep sync wrapper if needed by parts of the app that aren't async
def test_scorer(scorer_name: str, sample_input: PromptRequestPiece) -> List[Score]:
    """
    Synchronous wrapper to test a configured Scorer with a sample input.

    Parameters:
        scorer_name: The name of the configured Scorer to test.
        sample_input: The input data (PromptRequestPiece) to score.

    Returns:
        List[Score]: The Scorer's output on the sample input.
    """
    try:
        # Get or create an event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # 'RuntimeError: There is no current event loop...'
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # If loop is already running (e.g., in Jupyter), create a task
            # This might require await if called from an async context
            logger.warning(
                "Running test_scorer within an existing event loop. Consider calling test_scorer_async directly."
            )
            # Note: Cannot run sync test_scorer reliably within an already running event loop.
            # It might be better to enforce using test_scorer_async in async contexts.
            raise ScorerTestingError(
                "Cannot run sync test_scorer reliably within an already running event loop. Use test_scorer_async."
            )
        else:
            result = loop.run_until_complete(test_scorer_async(scorer_name, sample_input))
            return result
    except Exception as e:
        logger.error(f"Error in sync wrapper test_scorer for '{scorer_name}': {e}", exc_info=True)
        # Re-raise or handle as appropriate
        raise e


def update_parameter_file(configured_scorers: Dict[str, Any]) -> None:
    """
    Updates the YAML parameter file with the current Scorer configurations.

    Parameters:
        configured_scorers: The current configurations to save.

    Raises:
        ScorerConfigurationError: If updating the parameter file fails.
    """
    try:
        PARAMETER_FILE.parent.mkdir(parents=True, exist_ok=True)  # Use pathlib's mkdir
        with open(PARAMETER_FILE, "w") as f:
            # Use default_flow_style=False for better readability
            yaml.safe_dump(configured_scorers, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Scorer configurations updated in '{PARAMETER_FILE}'.")
    except Exception as e:
        logger.error(f"Error updating scorer parameter file '{PARAMETER_FILE}': {e}", exc_info=True)
        raise ScorerConfigurationError(f"Error updating scorer parameter file: {e}") from e
