# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Tests for database configuration tuning functionality."""

from __future__ import annotations

import os
import sys
import tempfile
from typing import Any, Dict

import pytest

# Add scripts directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts/performance-optimization"))


@pytest.fixture
def temp_config_dir() -> Any:
    """Create temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestConfigurationTuner:
    """Test configuration tuning functionality."""

    def test_tuner_initialization(self) -> None:
        """Test configuration tuner can be initialized."""
        from tune_configurations import ConfigurationTuner

        tuner = ConfigurationTuner()
        assert tuner is not None
        assert hasattr(tuner, "analyze_workload")
        assert hasattr(tuner, "recommend_config")
        assert hasattr(tuner, "apply_config")

    def test_analyze_sqlite_workload(self) -> None:
        """Test SQLite workload analysis."""
        from tune_configurations import ConfigurationTuner

        tuner = ConfigurationTuner()

        workload = {
            "read_operations": 1000,
            "write_operations": 100,
            "concurrent_connections": 10,
            "avg_query_time": 50,
        }

        analysis = tuner.analyze_workload(workload, "sqlite")

        assert analysis is not None
        assert "workload_type" in analysis
        assert "recommendations" in analysis

    def test_recommend_sqlite_config(self) -> None:
        """Test SQLite configuration recommendations."""
        from tune_configurations import ConfigurationTuner

        tuner = ConfigurationTuner()

        workload = {"read_heavy": True, "write_operations": 100}

        config = tuner.recommend_config(workload, "sqlite")

        assert config is not None
        assert "journal_mode" in config
        assert "cache_size" in config
        assert "synchronous" in config
        assert "page_size" in config

    def test_recommend_duckdb_config(self) -> None:
        """Test DuckDB configuration recommendations."""
        from tune_configurations import ConfigurationTuner

        tuner = ConfigurationTuner()

        workload = {"memory_usage": "high", "analytics_heavy": True}

        config = tuner.recommend_config(workload, "duckdb")

        assert config is not None
        assert "memory_limit" in config
        assert "threads" in config

    def test_recommend_postgres_config(self) -> None:
        """Test PostgreSQL configuration recommendations."""
        from tune_configurations import ConfigurationTuner

        tuner = ConfigurationTuner()

        workload = {
            "concurrent_connections": 100,
            "memory_available": "8GB",
            "workload_type": "mixed",
        }

        config = tuner.recommend_config(workload, "postgres")

        assert config is not None
        assert "max_connections" in config
        assert "shared_buffers" in config
        assert "work_mem" in config
        assert "effective_cache_size" in config

    def test_validate_configuration(self) -> None:
        """Test configuration validation."""
        from tune_configurations import ConfigurationTuner

        tuner = ConfigurationTuner()

        config = {
            "cache_size": -2000,
            "page_size": 4096,
            "synchronous": "NORMAL",
            "journal_mode": "WAL",
        }

        validation = tuner.validate_config(config, "sqlite")

        assert validation is not None
        assert "valid" in validation
        assert "errors" in validation

    def test_apply_sqlite_configuration(self, temp_config_dir: str) -> None:
        """Test applying SQLite configuration."""
        from tune_configurations import ConfigurationTuner

        tuner = ConfigurationTuner()

        config = {
            "cache_size": -2000,
            "page_size": 4096,
            "synchronous": "NORMAL",
            "journal_mode": "WAL",
        }

        config_path = os.path.join(temp_config_dir, "sqlite_config.py")
        result = tuner.apply_config(config, "sqlite", config_path)

        assert result is True
        assert os.path.exists(config_path)

    def test_backup_configuration(self, temp_config_dir: str) -> None:
        """Test configuration backup creation."""
        from tune_configurations import ConfigurationTuner

        tuner = ConfigurationTuner()

        # Create a dummy config file
        config_path = os.path.join(temp_config_dir, "test_config.py")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("# Test config\nCACHE_SIZE = 1000\n")

        backup_path = tuner.backup_config(config_path)

        assert backup_path is not None
        assert os.path.exists(backup_path)

    def test_restore_configuration(self, temp_config_dir: str) -> None:
        """Test configuration restoration."""
        from tune_configurations import ConfigurationTuner

        tuner = ConfigurationTuner()

        # Create original and backup
        config_path = os.path.join(temp_config_dir, "test_config.py")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("# Original config\n")

        backup_path = tuner.backup_config(config_path)

        # Modify original
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("# Modified config\n")

        # Restore
        result = tuner.restore_config(backup_path, config_path)

        assert result is True

        # Verify restoration
        with open(config_path, encoding="utf-8") as f:
            content = f.read()
            assert "Original config" in content

    def test_calculate_optimal_cache_size(self) -> None:
        """Test optimal cache size calculation."""
        from tune_configurations import ConfigurationTuner

        tuner = ConfigurationTuner()

        available_memory = 8 * 1024 * 1024 * 1024  # 8GB in bytes
        cache_size = tuner.calculate_cache_size(available_memory, "sqlite")

        assert cache_size is not None
        # SQLite uses negative values for KB units, so absolute value should be > 0
        assert abs(cache_size) > 0

    def test_calculate_connection_pool_size(self) -> None:
        """Test connection pool size calculation."""
        from tune_configurations import ConfigurationTuner

        tuner = ConfigurationTuner()

        workload = {"concurrent_users": 100, "avg_query_time": 50}

        pool_size = tuner.calculate_pool_size(workload)

        assert pool_size is not None
        assert pool_size > 0
        assert pool_size <= workload["concurrent_users"]

    def test_generate_config_report(self, temp_config_dir: str) -> None:
        """Test configuration report generation."""
        from tune_configurations import ConfigurationTuner

        tuner = ConfigurationTuner()

        config = {
            "cache_size": -2000,
            "page_size": 4096,
            "synchronous": "NORMAL",
            "journal_mode": "WAL",
        }

        report_path = os.path.join(temp_config_dir, "config_report.json")
        tuner.generate_report(config, report_path)

        assert os.path.exists(report_path)

    def test_compare_configurations(self) -> None:
        """Test configuration comparison."""
        from tune_configurations import ConfigurationTuner

        tuner = ConfigurationTuner()

        old_config = {"cache_size": -1000, "page_size": 4096}
        new_config = {"cache_size": -2000, "page_size": 4096}

        comparison = tuner.compare_configs(old_config, new_config)

        assert comparison is not None
        assert "changes" in comparison
        assert "cache_size" in comparison["changes"]


class TestWorkloadAnalysis:
    """Test workload analysis utilities."""

    def test_classify_workload_type(self) -> None:
        """Test workload type classification."""
        from tune_configurations import classify_workload

        metrics = {"read_operations": 900, "write_operations": 100}

        workload_type = classify_workload(metrics)

        assert workload_type is not None
        assert workload_type in ["read_heavy", "write_heavy", "balanced"]

    def test_calculate_resource_requirements(self) -> None:
        """Test resource requirement calculation."""
        from tune_configurations import calculate_resource_requirements

        workload = {
            "concurrent_users": 100,
            "avg_query_size": 1024,
            "operations_per_second": 1000,
        }

        requirements = calculate_resource_requirements(workload)

        assert requirements is not None
        assert "memory" in requirements
        assert "connections" in requirements
