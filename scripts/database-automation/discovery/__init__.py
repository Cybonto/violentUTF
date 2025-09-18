# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
ViolentUTF Database Discovery System

Automated discovery scripts for database detection across containers,
services, file systems, and source code.

Issue #279 Implementation
"""

from .exceptions import (
    CodeDiscoveryError,
    ConfigurationError,
    ContainerDiscoveryError,
    DiscoveryError,
    DiscoveryPermissionError,
    DiscoveryTimeoutError,
    FilesystemDiscoveryError,
    NetworkDiscoveryError,
    SecurityScanError,
    ValidationError,
)
from .models import (
    CodeReference,
    ConfidenceLevel,
    ContainerInfo,
    DatabaseDiscovery,
    DatabaseFile,
    DatabaseType,
    DiscoveryConfig,
    DiscoveryMethod,
    DiscoveryReport,
    NetworkService,
    SecurityFinding,
)
from .utils import (
    calculate_confidence_score,
    create_report_directory,
    detect_database_type_from_content,
    detect_database_type_from_extension,
    format_file_size,
    generate_database_id,
    is_likely_test_file,
    load_yaml_config,
    measure_execution_time,
    normalize_host,
    parse_connection_string,
    sanitize_for_logging,
    setup_logging,
    validate_file_path,
    validate_sqlite_database,
)

__version__ = "1.0.0"
__author__ = "ViolentUTF Team"
__description__ = "Automated Database Discovery System for ViolentUTF"

__all__ = [
    # Models
    "DatabaseType",
    "DiscoveryMethod",
    "ConfidenceLevel",
    "DatabaseDiscovery",
    "DiscoveryReport",
    "DiscoveryConfig",
    "NetworkService",
    "ContainerInfo",
    "DatabaseFile",
    "CodeReference",
    "SecurityFinding",
    # Exceptions
    "DiscoveryError",
    "ContainerDiscoveryError",
    "NetworkDiscoveryError",
    "FilesystemDiscoveryError",
    "CodeDiscoveryError",
    "SecurityScanError",
    "ValidationError",
    "ConfigurationError",
    "DiscoveryPermissionError",
    "DiscoveryTimeoutError",
    # Utilities
    "setup_logging",
    "generate_database_id",
    "calculate_confidence_score",
    "validate_file_path",
    "detect_database_type_from_extension",
    "detect_database_type_from_content",
    "validate_sqlite_database",
    "parse_connection_string",
    "sanitize_for_logging",
    "load_yaml_config",
    "measure_execution_time",
    "format_file_size",
    "is_likely_test_file",
    "normalize_host",
    "create_report_directory",
]
