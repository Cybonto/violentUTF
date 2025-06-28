# orchestrators/orchestrator_config.py

"""
Module: orchestrator_config

Contains functions for Orchestrator configuration and management.

Key Functions:
- list_orchestrator_types()
- get_orchestrator_params(orchestrator_class)
- add_orchestrator(name, orchestrator_class, parameters)
- delete_orchestrator(name)
- load_orchestrators()
- get_orchestrator(name)

Dependencies:
- PyRIT Orchestrator classes
- Utils modules for error handling and logging
- Configuration storage mechanisms (e.g., files or databases)
"""

import asyncio
import inspect
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

# Import PyRIT Orchestrator classes
import pyrit.orchestrator as pyrit_orchestrator
from pyrit.orchestrator import Orchestrator
from utils.error_handling import (OrchestratorConfigurationError,
                                  OrchestratorDeletionError,
                                  OrchestratorInstantiationError,
                                  OrchestratorLoadingError)
from utils.logging import get_logger

logger = get_logger(__name__)

CONFIG_FILE_PATH = Path("parameters/orchestrators.json")


def list_orchestrator_types() -> List[str]:
    """
    Lists available Orchestrator types/classes from PyRIT.

    Returns:
        List[str]: A list of available Orchestrator class names.

    Raises:
        OrchestratorLoadingError: If unable to retrieve orchestrator types.

    Dependencies:
        - pyrit.orchestrator
    """
    try:
        orchestrator_classes = []
        for name, obj in inspect.getmembers(pyrit_orchestrator):
            if (
                inspect.isclass(obj)
                and issubclass(obj, Orchestrator)
                and obj != Orchestrator
            ):
                orchestrator_classes.append(name)
        logger.debug(f"Available Orchestrator types: {orchestrator_classes}")
        return orchestrator_classes
    except Exception as e:
        logger.error(f"Error listing Orchestrator types: {e}")
        raise OrchestratorLoadingError(f"Error listing Orchestrator types: {e}")


def get_orchestrator_params(orchestrator_class: str) -> List[Dict[str, Any]]:
    """
    Retrieves the parameters required for the specified Orchestrator class.

    Parameters:
        orchestrator_class (str): The class name of the Orchestrator.

    Returns:
        List[Dict[str, Any]]: A list of parameter definitions.

    Raises:
        OrchestratorLoadingError: If the specified class is not found.

    Dependencies:
        - pyrit.orchestrator
        - inspect
    """
    try:
        # Get the class from pyrit.orchestrator by name
        clazz = getattr(pyrit_orchestrator, orchestrator_class, None)
        if clazz is None:
            raise OrchestratorLoadingError(
                f"Orchestrator class '{orchestrator_class}' not found in pyrit.orchestrator module."
            )

        sig = inspect.signature(clazz.__init__)
        params_list = []

        for param in sig.parameters.values():
            if param.name == "self":
                continue  # Skip 'self' parameter

            param_info = {
                "name": param.name,
                "default": (
                    param.default if param.default != inspect.Parameter.empty else None
                ),
                "annotation": (
                    param.annotation
                    if param.annotation != inspect.Parameter.empty
                    else None
                ),
                "required": param.default == inspect.Parameter.empty,
            }

            # Handle Optional types
            if (
                hasattr(param_info["annotation"], "__origin__")
                and param_info["annotation"].__origin__ == Union
            ):
                types = [
                    t for t in param_info["annotation"].__args__ if t != type(None)
                ]
                if types:
                    param_info["annotation"] = types[0]

            # Convert annotation to a string for display purposes
            param_info["type_str"] = str(param_info["annotation"])

            params_list.append(param_info)

        logger.debug(f"Parameters for '{orchestrator_class}': {params_list}")
        return params_list
    except Exception as e:
        logger.error(
            f"Error getting parameters for Orchestrator '{orchestrator_class}': {e}"
        )
        raise OrchestratorLoadingError(
            f"Error getting parameters for Orchestrator '{orchestrator_class}': {e}"
        )


def load_orchestrators() -> Dict[str, Dict[str, Any]]:
    """
    Loads the existing Orchestrator configurations.

    Returns:
        Dict[str, Dict[str, Any]]: A dictionary of Orchestrator configurations.

    Raises:
        OrchestratorLoadingError: If unable to load configurations.

    Dependencies:
        - Reads from 'parameters/orchestrators.json'
    """
    try:
        if CONFIG_FILE_PATH.exists():
            with open(CONFIG_FILE_PATH, "r") as f:
                orchestrators = json.load(f)
            logger.debug(f"Loaded orchestrators: {orchestrators}")
            return orchestrators
        else:
            # Return empty dict if config file doesn't exist
            logger.debug("No existing orchestrator configurations found.")
            return {}
    except Exception as e:
        logger.error(f"Error loading orchestrators: {e}")
        raise OrchestratorLoadingError(f"Error loading orchestrators: {e}")


def save_orchestrators(orchestrators: Dict[str, Dict[str, Any]]) -> None:
    """
    Saves the Orchestrator configurations to the config file.

    Parameters:
        orchestrators (Dict[str, Dict[str, Any]]): The Orchestrator configurations to save.

    Raises:
        OrchestratorConfigurationError: If unable to save configurations.

    Dependencies:
        - Writes to 'parameters/orchestrators.json'
    """
    try:
        # Ensure the directory exists
        CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE_PATH, "w") as f:
            json.dump(orchestrators, f, indent=4)
        logger.debug("Orchestrator configurations saved successfully.")
    except Exception as e:
        logger.error(f"Error saving orchestrators: {e}")
        raise OrchestratorConfigurationError(f"Error saving orchestrators: {e}")


def add_orchestrator(
    name: str, orchestrator_class: str, parameters: Dict[str, Any]
) -> Orchestrator:
    """
    Adds a new Orchestrator configuration and saves it.

    Parameters:
        name (str): The unique name for the Orchestrator.
        orchestrator_class (str): The class name of the Orchestrator.
        parameters (Dict[str, Any]): The parameters for the Orchestrator.

    Returns:
        Orchestrator: An instance of the configured Orchestrator.

    Raises:
        OrchestratorConfigurationError: If there is an error in configuration.
        OrchestratorInstantiationError: If the Orchestrator cannot be instantiated.

    Dependencies:
        - pyrit.orchestrator
        - load_orchestrators()
        - get_orchestrator_params()
        - save_orchestrators()
    """
    try:
        # Check if the name already exists
        existing_orchestrators = load_orchestrators()
        if name in existing_orchestrators:
            raise OrchestratorConfigurationError(
                f"An Orchestrator with the name '{name}' already exists."
            )

        # Get the class from pyrit.orchestrator
        clazz = getattr(pyrit_orchestrator, orchestrator_class, None)
        if clazz is None:
            raise OrchestratorLoadingError(
                f"Orchestrator class '{orchestrator_class}' not found in pyrit.orchestrator module."
            )

        # Get parameters required by the class
        param_defs = get_orchestrator_params(orchestrator_class)

        # Prepare kwargs for instantiation
        init_kwargs = {}
        for param_def in param_defs:
            param_name = param_def["name"]
            if param_name in parameters:
                init_kwargs[param_name] = parameters[param_name]
            elif param_def["required"]:
                raise OrchestratorConfigurationError(
                    f"Required parameter '{param_name}' not provided for Orchestrator '{name}'."
                )

        # Instantiate the Orchestrator
        orchestrator_instance = clazz(**init_kwargs)

        # Save the configuration
        existing_orchestrators[name] = {
            "class": orchestrator_class,
            "parameters": parameters,
        }
        save_orchestrators(existing_orchestrators)

        logger.info(
            f"Orchestrator '{name}' of type '{orchestrator_class}' added successfully."
        )
        return orchestrator_instance
    except (OrchestratorConfigurationError, OrchestratorLoadingError) as e:
        logger.error(f"Error adding Orchestrator '{name}': {e}")
        raise
    except Exception as e:
        logger.exception(f"Error instantiating Orchestrator '{name}': {e}")
        raise OrchestratorInstantiationError(
            f"Error instantiating Orchestrator '{name}': {e}"
        )


def delete_orchestrator(name: str) -> bool:
    """
    Deletes the Orchestrator configuration with the given name.

    Parameters:
        name (str): The name of the Orchestrator to delete.

    Returns:
        bool: True if the Orchestrator was deleted, False if not found.

    Raises:
        OrchestratorDeletionError: If unable to delete the Orchestrator.

    Dependencies:
        - load_orchestrators()
        - save_orchestrators()
    """
    try:
        orchestrators = load_orchestrators()
        if name in orchestrators:
            del orchestrators[name]
            save_orchestrators(orchestrators)
            logger.info(f"Orchestrator '{name}' deleted successfully.")
            return True
        else:
            logger.warning(f"Orchestrator '{name}' not found for deletion.")
            return False
    except Exception as e:
        logger.error(f"Error deleting Orchestrator '{name}': {e}")
        raise OrchestratorDeletionError(f"Error deleting Orchestrator '{name}': {e}")


def get_orchestrator(name: str) -> Orchestrator:
    """
    Retrieves the Orchestrator instance with the given name.

    Parameters:
        name (str): The name of the Orchestrator to retrieve.

    Returns:
        Orchestrator: The Orchestrator instance.

    Raises:
        OrchestratorLoadingError: If unable to retrieve the Orchestrator.

    Dependencies:
        - load_orchestrators()
        - pyrit.orchestrator
        - get_orchestrator_params()
    """
    try:
        orchestrators = load_orchestrators()
        if name not in orchestrators:
            raise OrchestratorLoadingError(f"Orchestrator '{name}' not found.")

        orchestrator_config = orchestrators[name]
        orchestrator_class = orchestrator_config["class"]
        parameters = orchestrator_config["parameters"]

        # Get the class from pyrit.orchestrator
        clazz = getattr(pyrit_orchestrator, orchestrator_class, None)
        if clazz is None:
            raise OrchestratorLoadingError(
                f"Orchestrator class '{orchestrator_class}' not found in pyrit.orchestrator module."
            )

        # Get parameters required by the class
        param_defs = get_orchestrator_params(orchestrator_class)

        # Prepare kwargs for instantiation
        init_kwargs = {}
        for param_def in param_defs:
            param_name = param_def["name"]
            if param_name in parameters:
                init_kwargs[param_name] = parameters[param_name]
            elif param_def["required"]:
                raise OrchestratorConfigurationError(
                    f"Required parameter '{param_name}' not found in saved configuration for Orchestrator '{name}'."
                )

        # Instantiate the Orchestrator
        orchestrator_instance = clazz(**init_kwargs)
        logger.info(f"Orchestrator '{name}' instantiated successfully.")
        return orchestrator_instance
    except Exception as e:
        logger.error(f"Error retrieving Orchestrator '{name}': {e}")
        raise OrchestratorLoadingError(f"Error retrieving Orchestrator '{name}': {e}")
