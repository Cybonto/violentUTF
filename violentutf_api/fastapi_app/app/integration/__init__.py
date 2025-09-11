# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Integration Module

Provides comprehensive integration testing and validation capabilities
for ViolentUTF platform components including service integration,
data consistency validation, and cross-service communication testing.
"""

__version__ = "1.0.0"

# Import all integration modules
from . import cross_service, data_consistency, service_integration

__all__ = [
    "service_integration",
    "data_consistency",
    "cross_service",
]
