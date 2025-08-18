# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

# utils/error_handling.py

"""
Module: Error Handling

Contains custom exception classes and error handling utilities.

Key Classes:
- DatasetLoadingError(Exception): Raised when a dataset fails to load.
- DatasetParsingError(Exception): Raised when parsing a dataset fails.
- TemplateError(Exception): Raised when template processing fails.
- ConverterLoadingError(Exception): Raised when loading or instantiating a converter fails.
- ConverterApplicationError(Exception): Raised when applying a converter fails.
- ScorerLoadingError(Exception): Raised when loading or instantiating a Scorer fails.
- ScorerInstantiationError(Exception): Raised when instantiating a Scorer fails.
- ScorerConfigurationError(Exception): Raised when there is a configuration error with a Scorer.
- ScorerDeletionError(Exception): Raised when deleting a Scorer fails.
- ScorerTestingError(Exception): Raised when testing a Scorer fails.
- ScorerApplicationError(Exception): Raised when applying a Scorer fails.
- OrchestratorLoadingError(Exception)
- OrchestratorInstantiationError(Exception)
- OrchestratorConfigurationError(Exception)
- OrchestratorDeletionError(Exception)
- OrchestratorTestingError(Exception)
- OrchestratorExecutionError(Exception)
- (Other existing exception classes)

Dependencies:
- logging
"""

import logging


class DatasetLoadingError(Exception):
    """
    Exception raised when a dataset fails to load.

    Parameters:
        message (str): Description of the error.
    """

    def __init__(self, message: str):
        super().__init__(message)


class DatasetParsingError(Exception):
    """
    Exception raised when parsing a dataset fails.

    Parameters:
        message (str): Description of the error.
    """

    def __init__(self, message: str):
        super().__init__(message)


class TemplateError(Exception):
    """
    Exception raised when template processing fails.

    Parameters:
        message (str): Description of the error.
    """

    def __init__(self, message: str):
        super().__init__(message)


class ConverterLoadingError(Exception):
    """
    Exception raised when loading or instantiating a converter fails.

    Parameters:
        message (str): Description of the error.
    """

    def __init__(self, message: str):
        super().__init__(message)


class ConverterApplicationError(Exception):
    """
    Exception raised when applying a converter to a prompt or dataset fails.

    Parameters:
        message (str): Description of the error.
    """

    def __init__(self, message: str):
        super().__init__(message)


class ScorerLoadingError(Exception):
    """
    Exception raised when loading or instantiating a Scorer fails.

    Parameters:
        message (str): Description of the error.
    """

    def __init__(self, message: str):
        super().__init__(message)


class ScorerInstantiationError(Exception):
    """
    Exception raised when instantiating a Scorer fails.

    Parameters:
        message (str): Description of the error.
    """

    def __init__(self, message: str):
        super().__init__(message)


class ScorerConfigurationError(Exception):
    """
    Exception raised when there is a configuration error with a Scorer.

    Parameters:
        message (str): Description of the error.
    """

    def __init__(self, message: str):
        super().__init__(message)


class ScorerDeletionError(Exception):
    """
    Exception raised when deleting a Scorer fails.

    Parameters:
        message (str): Description of the error.
    """

    def __init__(self, message: str):
        super().__init__(message)


class ScorerTestingError(Exception):
    """
    Exception raised when testing a Scorer fails.

    Parameters:
        message (str): Description of the error.
    """

    def __init__(self, message: str):
        super().__init__(message)


class ScorerApplicationError(Exception):
    """
    Exception raised when applying a Scorer fails.

    Parameters:
        message (str): Description of the error.
    """

    def __init__(self, message: str):
        super().__init__(message)


class OrchestratorLoadingError(Exception):
    """Exception raised when an Orchestrator fails to load."""

    pass


class OrchestratorInstantiationError(Exception):
    """Exception raised when an Orchestrator cannot be instantiated."""

    pass


class OrchestratorConfigurationError(Exception):
    """Exception raised when there is a configuration error with an Orchestrator."""

    pass


class OrchestratorDeletionError(Exception):
    """Exception raised when deleting an Orchestrator fails."""

    pass


class OrchestratorTestingError(Exception):
    """Exception raised when testing an Orchestrator fails."""

    pass


class OrchestratorExecutionError(Exception):
    """Exception raised when executing an Orchestrator fails."""

    pass
