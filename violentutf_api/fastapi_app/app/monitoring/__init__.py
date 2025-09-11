# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Monitoring Module

Provides comprehensive monitoring capabilities for ViolentUTF platform
including performance monitoring, resource monitoring, and system health monitoring.
"""

__version__ = "1.0.0"

# Import all monitoring modules
from . import performance_monitor

__all__ = [
    "performance_monitor",
]
