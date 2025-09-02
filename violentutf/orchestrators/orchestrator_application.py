# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Orchestrator Application module.

Module: orchestrator_application

Contains functions to run Orchestrators.

Key Functions:
- test_orchestrator(orchestrator: Orchestrator) -> bool
- run_orchestrator(orchestrator: Orchestrator)

Dependencies:
- PyRIT Orchestrator classes
- Utils modules for error handling and logging

"""

import asyncio
import inspect

from pyrit.orchestrator import Orchestrator
from utils.error_handling import OrchestratorExecutionError, OrchestratorTestingError
from utils.logging import get_logger

logger = get_logger(__name__)


async def test_orchestrator(orchestrator: Orchestrator) -> bool:
    """Test the configured Orchestrator.

    Parameters:
        orchestrator (Orchestrator): The Orchestrator instance to test.

    Returns:
        bool: True if the Orchestrator test is successful.

    Raises:
        OrchestratorTestingError: If the test fails.

    Dependencies:
        - Orchestrator's own test methods or a simple operation

    """
    try:

        orchestrator_name = orchestrator.get_identifier().get("name", "unknown")
        logger.info(f"Testing Orchestrator '{orchestrator_name}'")
        # For testing purposes, we will just validate that the orchestrator can be instantiated

        # Additional validation can be added here if necessary

        logger.info("Orchestrator instantiation successful.")
        return True
    except Exception as e:
        logger.error(f"Error testing Orchestrator '{orchestrator_name}': {e}")
        raise OrchestratorTestingError(f"Error testing Orchestrator '{orchestrator_name}': {e}") from e


async def run_orchestrator(orchestrator: Orchestrator) -> None:
    """Run the configured Orchestrator.

    Parameters:
        orchestrator (Orchestrator): The Orchestrator instance to run.

    Raises:
        OrchestratorExecutionError: If the execution fails.

    Dependencies:
        - Orchestrator's run or execute methods
    """
    try:

        orchestrator_name = orchestrator.get_identifier().get("name", "unknown")
        logger.info(f"Running Orchestrator '{orchestrator_name}'")
        # Depending on the Orchestrator type, we may need to call different methods

        # For orchestrators with 'run_attack_async' method
        if hasattr(orchestrator, "run_attack_async"):
            # Depending on the method signature, we may need to pass required parameters
            method = getattr(orchestrator, "run_attack_async")
            sig = inspect.signature(method)
            params = sig.parameters

            # Prepare dummy or default parameters
            kwargs = {}
            if "objective" in params:
                kwargs["objective"] = "This is a sample objective."

            logger.debug(f"Calling 'run_attack_async' with parameters: {kwargs}")
            if asyncio.iscoroutinefunction(method):
                await method(**kwargs)
            else:
                method(**kwargs)
            logger.info("Orchestrator run completed successfully.")
        else:
            logger.error("Orchestrator does not have a 'run_attack_async' method.")
            raise OrchestratorExecutionError("Orchestrator does not have a 'run_attack_async' method.")
    except Exception as e:
        logger.error(f"Error running Orchestrator '{orchestrator_name}': {e}")
        raise OrchestratorExecutionError(f"Error running Orchestrator '{orchestrator_name}': {e}") from e
