# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Tests for Configuration Baseline functionality - Issue #265."""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict

import pytest

# These imports will fail initially (RED phase of TDD)
from violentutf_api.fastapi_app.app.services.config_monitoring import (
    ConfigurationBaseline,
    ConfigurationMonitoringService,
)


class TestConfigurationBaseline:
    """Test ConfigurationBaseline class functionality."""

    def test_create_baseline_postgresql(self):
        """Test creating baseline for PostgreSQL configuration."""
        # GIVEN: PostgreSQL configuration data
        config_data = {
            "host": "postgres",
            "port": 5432,
            "database": "keycloak",
            "username": "keycloak"
        }
        
        # WHEN: Creating baseline
        baseline = ConfigurationBaseline(
            service_name="keycloak",
            config_type="postgresql",
            config_path="/keycloak/docker-compose.yml",
            config_data=config_data
        )
        
        # THEN: Baseline should be created with proper hash
        assert baseline.service_name == "keycloak"
        assert baseline.config_type == "postgresql"
        assert baseline.baseline_hash is not None
        assert len(baseline.baseline_hash) == 64  # SHA-256

    def test_create_baseline_sqlite(self):
        """Test creating baseline for SQLite configuration."""
        # GIVEN: SQLite configuration data
        config_data = {
            "database_url": "sqlite+aiosqlite:///./app_data/violentutf_api.db",
            "echo": True,
            "future": True
        }
        
        # WHEN: Creating baseline
        baseline = ConfigurationBaseline(
            service_name="fastapi",
            config_type="sqlite",
            config_path="/app/db/database.py",
            config_data=config_data
        )
        
        # THEN: Baseline should be created correctly
        assert baseline.service_name == "fastapi"
        assert baseline.config_type == "sqlite"
        assert baseline.config_data == config_data

    def test_create_baseline_duckdb(self):
        """Test creating baseline for DuckDB configuration."""
        # GIVEN: DuckDB configuration data
        config_data = {
            "db_path": "/app/app_data/violentutf/pyrit_memory_{hash}.db",
            "salt": "default_salt_2025",
            "app_data_dir": "/app/app_data/violentutf"
        }
        
        # WHEN: Creating baseline
        baseline = ConfigurationBaseline(
            service_name="pyrit",
            config_type="duckdb",
            config_path="/app/db/duckdb_manager.py",
            config_data=config_data
        )
        
        # THEN: Baseline should be created correctly
        assert baseline.service_name == "pyrit"
        assert baseline.config_type == "duckdb"

    def test_create_baseline_application_config(self):
        """Test creating baseline for application configuration."""
        # GIVEN: Application configuration data
        config_data = {
            "PROJECT_NAME": "ViolentUTF API",
            "ENVIRONMENT": "development",
            "DEBUG": True,
            "DATABASE_URL": None
        }
        
        # WHEN: Creating baseline
        baseline = ConfigurationBaseline(
            service_name="violentutf_api",
            config_type="application",
            config_path="/app/core/config.py",
            config_data=config_data
        )
        
        # THEN: Baseline should be created correctly
        assert baseline.service_name == "violentutf_api"
        assert baseline.config_type == "application"

    def test_baseline_hash_consistency(self):
        """Test that identical configurations produce same hash."""
        # GIVEN: Identical configuration data
        config_data = {"key": "value", "number": 123}
        
        # WHEN: Creating two baselines with same data
        baseline1 = ConfigurationBaseline("test", "test", "/test", config_data)
        baseline2 = ConfigurationBaseline("test", "test", "/test", config_data)
        
        # THEN: Hashes should be identical
        assert baseline1.baseline_hash == baseline2.baseline_hash

    def test_baseline_hash_different_data(self):
        """Test that different configurations produce different hashes."""
        # GIVEN: Different configuration data
        config_data1 = {"key": "value1"}
        config_data2 = {"key": "value2"}
        
        # WHEN: Creating baselines with different data
        baseline1 = ConfigurationBaseline("test", "test", "/test", config_data1)
        baseline2 = ConfigurationBaseline("test", "test", "/test", config_data2)
        
        # THEN: Hashes should be different
        assert baseline1.baseline_hash != baseline2.baseline_hash

    def test_baseline_serialization(self):
        """Test baseline can be serialized and deserialized."""
        # GIVEN: Configuration baseline
        config_data = {"key": "value", "nested": {"item": 123}}
        baseline = ConfigurationBaseline("test", "test", "/test", config_data)
        
        # WHEN: Serializing and deserializing
        serialized = baseline.to_dict()
        restored = ConfigurationBaseline.from_dict(serialized)
        
        # THEN: Restored baseline should match original
        assert restored.service_name == baseline.service_name
        assert restored.config_type == baseline.config_type
        assert restored.config_path == baseline.config_path
        assert restored.baseline_hash == baseline.baseline_hash
        assert restored.config_data == baseline.config_data

    def test_baseline_validation(self):
        """Test baseline validation rules."""
        # GIVEN: Invalid baseline parameters
        config_data = {"key": "value"}
        
        # WHEN/THEN: Invalid parameters should raise errors
        with pytest.raises(ValueError, match="Service name cannot be empty"):
            ConfigurationBaseline("", "test", "/test", config_data)
        
        with pytest.raises(ValueError, match="Config type cannot be empty"):
            ConfigurationBaseline("test", "", "/test", config_data)
        
        with pytest.raises(ValueError, match="Config path cannot be empty"):
            ConfigurationBaseline("test", "test", "", config_data)
        
        with pytest.raises(ValueError, match="Config data cannot be empty"):
            ConfigurationBaseline("test", "test", "/test", {})


@pytest.mark.asyncio
class TestConfigurationMonitoringService:
    """Test ConfigurationMonitoringService class functionality."""

    async def test_create_baseline_service(self):
        """Test creating baseline through monitoring service."""
        # GIVEN: Configuration monitoring service
        service = ConfigurationMonitoringService()
        config_data = {"host": "postgres", "port": 5432}
        
        # WHEN: Creating baseline
        baseline_id = await service.create_baseline(
            service_name="test_service",
            config_type="postgresql",
            config_path="/test/config",
            config_data=config_data
        )
        
        # THEN: Baseline should be created with ID
        assert baseline_id is not None
        assert isinstance(baseline_id, str)
        assert len(baseline_id) > 0

    async def test_get_baseline_by_id(self):
        """Test retrieving baseline by ID."""
        # GIVEN: Created baseline
        service = ConfigurationMonitoringService()
        config_data = {"host": "postgres", "port": 5432}
        baseline_id = await service.create_baseline(
            service_name="test_service",
            config_type="postgresql",
            config_path="/test/config",
            config_data=config_data
        )
        
        # WHEN: Retrieving baseline by ID
        retrieved_baseline = await service.get_baseline(baseline_id)
        
        # THEN: Retrieved baseline should match created one
        assert retrieved_baseline is not None
        assert retrieved_baseline.service_name == "test_service"
        assert retrieved_baseline.config_type == "postgresql"
        assert retrieved_baseline.config_data == config_data

    async def test_list_baselines_for_service(self):
        """Test listing baselines for a specific service."""
        # GIVEN: Multiple baselines for different services
        service = ConfigurationMonitoringService()
        
        # Create baselines for test_service
        await service.create_baseline("test_service", "postgresql", "/test1", {"key": "value1"})
        await service.create_baseline("test_service", "sqlite", "/test2", {"key": "value2"})
        
        # Create baseline for different service
        await service.create_baseline("other_service", "postgresql", "/test3", {"key": "value3"})
        
        # WHEN: Listing baselines for test_service
        test_service_baselines = await service.list_baselines_for_service("test_service")
        
        # THEN: Only test_service baselines should be returned
        assert len(test_service_baselines) == 2
        assert all(b.service_name == "test_service" for b in test_service_baselines)

    async def test_update_baseline(self):
        """Test updating existing baseline."""
        # GIVEN: Existing baseline
        service = ConfigurationMonitoringService()
        original_config = {"host": "postgres", "port": 5432}
        baseline_id = await service.create_baseline(
            "test_service", "postgresql", "/test", original_config
        )
        
        # WHEN: Updating baseline with new configuration
        updated_config = {"host": "postgres", "port": 5433, "timeout": 30}
        success = await service.update_baseline(baseline_id, updated_config)
        
        # THEN: Baseline should be updated
        assert success is True
        updated_baseline = await service.get_baseline(baseline_id)
        assert updated_baseline.config_data == updated_config
        assert updated_baseline.baseline_hash != hashlib.sha256(
            json.dumps(original_config, sort_keys=True).encode()
        ).hexdigest()

    async def test_delete_baseline(self):
        """Test deleting baseline."""
        # GIVEN: Existing baseline
        service = ConfigurationMonitoringService()
        baseline_id = await service.create_baseline(
            "test_service", "postgresql", "/test", {"key": "value"}
        )
        
        # WHEN: Deleting baseline
        success = await service.delete_baseline(baseline_id)
        
        # THEN: Baseline should be deleted
        assert success is True
        deleted_baseline = await service.get_baseline(baseline_id)
        assert deleted_baseline is None

    async def test_get_baseline_statistics(self):
        """Test getting baseline statistics."""
        # GIVEN: Multiple baselines
        service = ConfigurationMonitoringService()
        await service.create_baseline("service1", "postgresql", "/test1", {"key": "value1"})
        await service.create_baseline("service2", "sqlite", "/test2", {"key": "value2"})
        await service.create_baseline("service3", "duckdb", "/test3", {"key": "value3"})
        
        # WHEN: Getting statistics
        stats = await service.get_baseline_statistics()
        
        # THEN: Statistics should be correct
        assert stats["total_baselines"] >= 3
        assert stats["services_count"] >= 3
        assert "postgresql" in stats["config_types"]
        assert "sqlite" in stats["config_types"]
        assert "duckdb" in stats["config_types"]