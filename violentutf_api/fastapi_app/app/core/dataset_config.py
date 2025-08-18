# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Dataset Import Configuration System

This module provides enhanced configuration management for dataset imports
with adaptive settings, validation, and environment variable support.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DatasetImportConfig:
    """Enhanced configuration with adaptive and context-aware settings"""

    # Basic limits
    preview_limit: int = 10
    chunk_size: int = 1000
    max_import_size: int = 0  # 0 = unlimited

    # PyRIT integration
    use_pyrit_memory: bool = True
    pyrit_batch_size: int = 100
    preserve_metadata: bool = True

    # Performance optimization
    enable_streaming: bool = True
    enable_progress_tracking: bool = True
    adaptive_chunk_size: bool = True
    max_memory_mb: int = 512

    # Error handling
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_partial_import: bool = True

    # User context
    enable_user_isolation: bool = True
    cleanup_on_failure: bool = True

    # Advanced features
    enable_duplicate_detection: bool = False
    enable_content_validation: bool = True
    enable_statistics_tracking: bool = True

    # Concurrency settings
    max_concurrent_imports: int = 3
    max_concurrent_chunks: int = 5

    # Storage settings
    storage_mode: str = "dual"  # "dual", "pyrit_only", "violentutf_only"
    backup_enabled: bool = True

    @classmethod
    def from_env(cls) -> "DatasetImportConfig":
        """Load configuration from environment variables"""

        def get_bool_env(key: str, default: bool) -> bool:
            return os.getenv(key, str(default)).lower() == "true"

        def get_int_env(key: str, default: int) -> int:
            try:
                return int(os.getenv(key, str(default)))
            except ValueError:
                logger.warning(f"Invalid integer value for {key}, using default: {default}")
                return default

        def get_float_env(key: str, default: float) -> float:
            try:
                return float(os.getenv(key, str(default)))
            except ValueError:
                logger.warning(f"Invalid float value for {key}, using default: {default}")
                return default

        config = cls(
            preview_limit=get_int_env("DATASET_PREVIEW_LIMIT", 10),
            chunk_size=get_int_env("DATASET_CHUNK_SIZE", 1000),
            max_import_size=get_int_env("DATASET_MAX_IMPORT_SIZE", 0),
            use_pyrit_memory=get_bool_env("DATASET_USE_PYRIT_MEMORY", True),
            pyrit_batch_size=get_int_env("DATASET_PYRIT_BATCH_SIZE", 100),
            preserve_metadata=get_bool_env("DATASET_PRESERVE_METADATA", True),
            enable_streaming=get_bool_env("DATASET_ENABLE_STREAMING", True),
            enable_progress_tracking=get_bool_env("DATASET_ENABLE_PROGRESS", True),
            adaptive_chunk_size=get_bool_env("DATASET_ADAPTIVE_CHUNK_SIZE", True),
            max_memory_mb=get_int_env("DATASET_MAX_MEMORY_MB", 512),
            max_retries=get_int_env("DATASET_MAX_RETRIES", 3),
            retry_delay=get_float_env("DATASET_RETRY_DELAY", 1.0),
            enable_partial_import=get_bool_env("DATASET_ENABLE_PARTIAL_IMPORT", True),
            enable_user_isolation=get_bool_env("DATASET_ENABLE_USER_ISOLATION", True),
            cleanup_on_failure=get_bool_env("DATASET_CLEANUP_ON_FAILURE", True),
            enable_duplicate_detection=get_bool_env("DATASET_ENABLE_DUPLICATE_DETECTION", False),
            enable_content_validation=get_bool_env("DATASET_ENABLE_CONTENT_VALIDATION", True),
            enable_statistics_tracking=get_bool_env("DATASET_ENABLE_STATISTICS_TRACKING", True),
            max_concurrent_imports=get_int_env("DATASET_MAX_CONCURRENT_IMPORTS", 3),
            max_concurrent_chunks=get_int_env("DATASET_MAX_CONCURRENT_CHUNKS", 5),
            storage_mode=os.getenv("DATASET_STORAGE_MODE", "dual"),
            backup_enabled=get_bool_env("DATASET_BACKUP_ENABLED", True),
        )

        # Validate configuration
        config.validate()

        logger.info(f"Dataset import configuration loaded: {config}")
        return config

    def validate(self) -> None:
        """Validate configuration values"""
        errors = []

        # Validate numeric ranges
        if self.preview_limit < 1 or self.preview_limit > 1000:
            errors.append("preview_limit must be between 1 and 1000")

        if self.chunk_size < 10 or self.chunk_size > 10000:
            errors.append("chunk_size must be between 10 and 10000")

        if self.max_import_size < 0:
            errors.append("max_import_size must be non-negative (0 = unlimited)")

        if self.pyrit_batch_size < 1 or self.pyrit_batch_size > 1000:
            errors.append("pyrit_batch_size must be between 1 and 1000")

        if self.max_memory_mb < 64 or self.max_memory_mb > 8192:
            errors.append("max_memory_mb must be between 64 and 8192")

        if self.max_retries < 1 or self.max_retries > 10:
            errors.append("max_retries must be between 1 and 10")

        if self.retry_delay < 0.1 or self.retry_delay > 60.0:
            errors.append("retry_delay must be between 0.1 and 60.0 seconds")

        if self.max_concurrent_imports < 1 or self.max_concurrent_imports > 10:
            errors.append("max_concurrent_imports must be between 1 and 10")

        if self.max_concurrent_chunks < 1 or self.max_concurrent_chunks > 20:
            errors.append("max_concurrent_chunks must be between 1 and 20")

        # Validate string values
        valid_storage_modes = ["dual", "pyrit_only", "violentutf_only"]
        if self.storage_mode not in valid_storage_modes:
            errors.append(f"storage_mode must be one of: {valid_storage_modes}")

        # Validate logical constraints
        if self.chunk_size > self.max_import_size > 0:
            errors.append("chunk_size cannot be larger than max_import_size")

        if self.pyrit_batch_size > self.chunk_size:
            errors.append("pyrit_batch_size cannot be larger than chunk_size")

        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)

    def get_effective_chunk_size(self, dataset_size: int = 0, avg_prompt_size: int = 0) -> int:
        """Calculate effective chunk size based on dataset characteristics"""
        if not self.adaptive_chunk_size:
            return self.chunk_size

        try:
            # Calculate optimal chunk size based on memory constraints
            if avg_prompt_size > 0:
                memory_per_chunk = self.max_memory_mb * 1024 * 1024 * 0.7  # 70% of max memory
                calculated_size = int(memory_per_chunk / avg_prompt_size)

                # Clamp to reasonable bounds
                return max(100, min(calculated_size, self.chunk_size))

            # If no average prompt size, use dataset size hints
            if dataset_size > 0:
                if dataset_size > 10000:
                    return min(2000, self.chunk_size)
                elif dataset_size > 1000:
                    return min(1000, self.chunk_size)
                else:
                    return min(500, self.chunk_size)

        except Exception as e:
            logger.warning(f"Error calculating effective chunk size: {e}")

        return self.chunk_size

    def get_effective_retry_config(self, dataset_type: str = "") -> Dict[str, Any]:
        """Get retry configuration based on dataset type"""
        # Some datasets might need different retry strategies
        retry_config = {
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "backoff_factor": 2.0,
            "timeout": 30.0,
        }

        # Adjust for specific dataset types
        if dataset_type in ["harmbench", "wmdp"]:
            # These datasets might be larger and need more time
            retry_config["timeout"] = 60.0
            retry_config["retry_delay"] = min(self.retry_delay * 2, 5.0)

        return retry_config

    def should_use_pyrit_memory(self) -> bool:
        """Determine if PyRIT memory should be used based on configuration"""
        return self.use_pyrit_memory and self.storage_mode in ["dual", "pyrit_only"]

    def should_use_violentutf_db(self) -> bool:
        """Determine if ViolentUTF database should be used based on configuration"""
        return self.storage_mode in ["dual", "violentutf_only"]

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization"""
        return {
            "preview_limit": self.preview_limit,
            "chunk_size": self.chunk_size,
            "max_import_size": self.max_import_size,
            "use_pyrit_memory": self.use_pyrit_memory,
            "pyrit_batch_size": self.pyrit_batch_size,
            "preserve_metadata": self.preserve_metadata,
            "enable_streaming": self.enable_streaming,
            "enable_progress_tracking": self.enable_progress_tracking,
            "adaptive_chunk_size": self.adaptive_chunk_size,
            "max_memory_mb": self.max_memory_mb,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "enable_partial_import": self.enable_partial_import,
            "enable_user_isolation": self.enable_user_isolation,
            "cleanup_on_failure": self.cleanup_on_failure,
            "enable_duplicate_detection": self.enable_duplicate_detection,
            "enable_content_validation": self.enable_content_validation,
            "enable_statistics_tracking": self.enable_statistics_tracking,
            "max_concurrent_imports": self.max_concurrent_imports,
            "max_concurrent_chunks": self.max_concurrent_chunks,
            "storage_mode": self.storage_mode,
            "backup_enabled": self.backup_enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetImportConfig":
        """Create configuration from dictionary"""
        return cls(**data)

    def __str__(self) -> str:
        """String representation of configuration"""
        return f"DatasetImportConfig(chunk_size={self.chunk_size}, max_import_size={self.max_import_size}, storage_mode={self.storage_mode})"


# Configuration validation functions
def validate_dataset_config(dataset_type: str, config: Dict[str, Any]) -> None:
    """Validate dataset-specific configuration"""
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a dictionary")

    # Define required/optional parameters for each dataset type
    dataset_requirements = {
        "harmbench": {"optional": ["source", "source_type", "cache", "data_home"]},
        "many_shot_jailbreaking": {"optional": []},
        "decoding_trust_stereotypes": {
            "optional": [
                "source",
                "source_type",
                "cache",
                "data_home",
                "stereotype_topics",
                "target_groups",
                "system_prompt_type",
            ]
        },
        "seclists_bias_testing": {
            "optional": [
                "source",
                "source_type",
                "cache",
                "data_home",
                "random_seed",
                "country",
                "region",
                "nationality",
                "gender",
                "skin_color",
            ]
        },
        "wmdp": {"optional": ["source", "source_type", "cache", "data_home", "categories"]},
        "adv_bench": {"optional": ["source", "source_type", "cache", "data_home"]},
        "aya_redteaming": {"optional": ["source", "source_type", "cache", "data_home", "languages"]},
        "forbidden_questions": {"optional": ["source", "source_type", "cache", "data_home"]},
        "pku_safe_rlhf": {"optional": ["source", "source_type", "cache", "data_home", "split"]},
        "xstest": {"optional": ["source", "source_type", "cache", "data_home"]},
    }

    if dataset_type not in dataset_requirements:
        raise ValueError(f"Unknown dataset type: {dataset_type}")

    requirements = dataset_requirements[dataset_type]

    # Check for unknown parameters
    allowed_params = set(requirements.get("required", []) + requirements.get("optional", []))
    unknown_params = set(config.keys()) - allowed_params

    if unknown_params:
        logger.warning(f"Unknown parameters for {dataset_type}: {unknown_params}")

    # Validate parameter types and values
    for param, value in config.items():
        if param in ["cache"]:
            if not isinstance(value, bool):
                raise ValueError(f"Parameter '{param}' must be a boolean")
        elif param in ["random_seed"]:
            if not isinstance(value, int):
                raise ValueError(f"Parameter '{param}' must be an integer")
        elif param in [
            "source",
            "source_type",
            "data_home",
            "country",
            "region",
            "nationality",
            "gender",
            "skin_color",
            "split",
        ]:
            if not isinstance(value, str):
                raise ValueError(f"Parameter '{param}' must be a string")
        elif param in ["stereotype_topics", "target_groups", "categories", "languages"]:
            if not isinstance(value, list):
                raise ValueError(f"Parameter '{param}' must be a list")

    logger.debug(f"Configuration validation passed for {dataset_type}")


# Environment configuration helper
def setup_dataset_environment() -> None:
    """Setup environment variables for dataset import if not already set"""
    default_env_vars = {
        "DATASET_PREVIEW_LIMIT": "10",
        "DATASET_CHUNK_SIZE": "1000",
        "DATASET_MAX_IMPORT_SIZE": "0",
        "DATASET_USE_PYRIT_MEMORY": "true",
        "DATASET_PYRIT_BATCH_SIZE": "100",
        "DATASET_PRESERVE_METADATA": "true",
        "DATASET_ENABLE_STREAMING": "true",
        "DATASET_ENABLE_PROGRESS": "true",
        "DATASET_ADAPTIVE_CHUNK_SIZE": "true",
        "DATASET_MAX_MEMORY_MB": "512",
        "DATASET_MAX_RETRIES": "3",
        "DATASET_RETRY_DELAY": "1.0",
        "DATASET_ENABLE_PARTIAL_IMPORT": "true",
        "DATASET_ENABLE_USER_ISOLATION": "true",
        "DATASET_CLEANUP_ON_FAILURE": "true",
        "DATASET_ENABLE_DUPLICATE_DETECTION": "false",
        "DATASET_ENABLE_CONTENT_VALIDATION": "true",
        "DATASET_ENABLE_STATISTICS_TRACKING": "true",
        "DATASET_MAX_CONCURRENT_IMPORTS": "3",
        "DATASET_MAX_CONCURRENT_CHUNKS": "5",
        "DATASET_STORAGE_MODE": "dual",
        "DATASET_BACKUP_ENABLED": "true",
    }

    for key, default_value in default_env_vars.items():
        if key not in os.environ:
            os.environ[key] = default_value

    logger.info("Dataset environment setup completed")


# Global configuration instance
_global_config: Optional[DatasetImportConfig] = None


def get_global_config() -> DatasetImportConfig:
    """Get the global dataset import configuration"""
    global _global_config
    if _global_config is None:
        _global_config = DatasetImportConfig.from_env()
    return _global_config


def reset_global_config() -> None:
    """Reset the global configuration (useful for testing)"""
    global _global_config
    _global_config = None
