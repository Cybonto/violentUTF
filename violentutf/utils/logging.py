# utils/logging.py

"""
Module: Logging

Setup and configuration for application-wide logging.

Key Functions:
- setup_logging(): Configures the logging settings. Should be called once at application start.
- get_logger(name): Returns a logger instance with the specified name.

Dependencies:
- logging
- os
"""

import logging
import os
import sys

# Simple flag to ensure setup runs only once per Python process execution
_setup_done = False

# Define handler names for uniqueness checks
_FILE_HANDLER_NAME = 'app_file_handler'
_CONSOLE_HANDLER_NAME = 'app_console_handler'

def setup_logging(log_level=logging.DEBUG, console_level=logging.INFO):
    """
    Configures the logging settings for the application.

    Sets up a file handler (DEBUG level by default) writing to 'app_logs/app.log'
    and a console handler (INFO level by default). Prevents duplicate handler
    creation and sets specified third-party libraries to WARNING level.

    Should be called explicitly once near the application entry point.

    Parameters:
        log_level (int): The minimum level for the file log. Defaults to logging.DEBUG.
        console_level (int): The minimum level for the console log. Defaults to logging.INFO.

    Returns:
        None
    """
    global _setup_done
    if _setup_done:
        # Prevent re-running setup in the same process
        return

    log_dir = 'app_logs'
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        # Handle potential permission errors gracefully
        print(f"Error creating log directory '{log_dir}': {e}", file=sys.stderr)
        # Optionally, fall back to console-only logging or raise the error
        # For now, we'll proceed but file logging might fail
        pass

    log_file = os.path.join(log_dir, 'app.log')

    # Define a consistent, detailed format
    log_format = '%(asctime)s [%(levelname)-8s] [%(name)s:%(funcName)s:%(lineno)d] - %(message)s'
    formatter = logging.Formatter(log_format)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level) # Set root logger level to the lowest level needed by any handler

    # --- File Handler ---
    # Check if our specific file handler already exists
    if not any(h.name == _FILE_HANDLER_NAME for h in root_logger.handlers):
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            file_handler.name = _FILE_HANDLER_NAME # Name the handler
            root_logger.addHandler(file_handler)
        except (OSError, IOError) as e:
            # Handle potential file opening errors
            print(f"Error setting up file log handler for '{log_file}': {e}", file=sys.stderr)


    # --- Console Handler ---
    # Check if our specific console handler already exists
    if not any(h.name == _CONSOLE_HANDLER_NAME for h in root_logger.handlers):
        console_handler = logging.StreamHandler(sys.stdout) # Log to stdout
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        console_handler.name = _CONSOLE_HANDLER_NAME # Name the handler
        root_logger.addHandler(console_handler)

    # --- Reduce Verbosity of Third-Party Libraries ---
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    # Add other verbose libraries here if needed

    # --- Mark setup as done ---
    _setup_done = True
    logging.getLogger(__name__).info("Logging setup completed.") # Log completion using the new setup

def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger instance with the specified name.

    Assumes setup_logging() has been called previously at application startup.

    Parameters:
        name (str): The name of the logger (usually __name__).

    Returns:
        logging.Logger: Configured logger instance.
    """
    # Setup is no longer called implicitly here.
    # It relies on the initial call in the main application entry point (e.g., Home.py).
    return logging.getLogger(name)