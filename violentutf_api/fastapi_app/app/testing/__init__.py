"""
Testing framework modules for ViolentUTF testing infrastructure.
Provides comprehensive testing utilities for performance validation,
UI testing, workflow usability, and error UX validation.
"""

__version__ = "1.0.0"

# Import all testing modules
from . import error_ux, ui_performance, workflow_usability

__all__ = [
    "ui_performance",
    "workflow_usability", 
    "error_ux",
]