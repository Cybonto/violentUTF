# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Custom exceptions for database discovery system."""


class DiscoveryError(Exception):
    """Base exception for discovery-related errors."""


class ContainerDiscoveryError(DiscoveryError):
    """Exception raised during container discovery operations."""


class NetworkDiscoveryError(DiscoveryError):
    """Exception raised during network discovery operations."""


class FilesystemDiscoveryError(DiscoveryError):
    """Exception raised during filesystem discovery operations."""


class CodeDiscoveryError(DiscoveryError):
    """Exception raised during code analysis operations."""


class SecurityScanError(DiscoveryError):
    """Exception raised during security scanning operations."""


class ValidationError(DiscoveryError):
    """Exception raised during result validation."""


class ConfigurationError(DiscoveryError):
    """Exception raised for invalid configuration."""


class DiscoveryPermissionError(DiscoveryError):
    """Exception raised when insufficient permissions for discovery operations."""


class DiscoveryTimeoutError(DiscoveryError):
    """Exception raised when discovery operations exceed time limits."""
