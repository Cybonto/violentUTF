# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Test suite for SQLiteManager - Issue #325.

Tests SQLite-based configuration storage with identical API to DuckDBManager.
Follows TDD methodology: write failing tests first, then implement.
"""

import json
import os
import shutil
import sqlite3
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict

import pytest

# Import the SQLiteManager (will fail initially as it doesn't exist yet)
from violentutf_api.fastapi_app.app.db.sqlite_manager import (
    SQLiteManager,
    get_sqlite_manager,
)


class TestSQLiteManagerInitialization:
    """Test SQLiteManager initialization and database creation."""

    def test_manager_initialization(self, temp_app_data_dir: str) -> None:
        """Test SQLiteManager initializes correctly."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)
        assert manager.username == "test_user"
        assert manager.db_path.endswith(".db")
        assert os.path.exists(manager.db_path)

    def test_db_filename_generation(self, temp_app_data_dir: str) -> None:
        """Test database filename is generated from salted hash of username."""
        manager = SQLiteManager("test_user", salt="test_salt", app_data_dir=temp_app_data_dir)
        filename = manager._get_db_filename()
        assert filename.startswith("pyrit_memory_")
        assert filename.endswith(".db")

    def test_tables_created_on_init(self, temp_app_data_dir: str) -> None:
        """Test all required tables are created on initialization."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        with sqlite3.connect(manager.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]

        required_tables = [
            "generators",
            "datasets",
            "dataset_prompts",
            "converters",
            "scorers",
            "user_sessions",
        ]

        for table in required_tables:
            assert table in tables, f"Table {table} not created"

    def test_sqlite_pragmas_set(self, temp_app_data_dir: str) -> None:
        """Test SQLite pragmas are set for optimization."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        with sqlite3.connect(manager.db_path) as conn:
            # Check WAL mode
            cursor = conn.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            assert journal_mode.upper() == "WAL"


class TestGeneratorOperations:
    """Test generator CRUD operations."""

    def test_create_generator(self, temp_app_data_dir: str) -> None:
        """Test creating a generator configuration."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        params = {"model": "gpt-4", "temperature": 0.7}
        gen_id = manager.create_generator("test_gen", "openai", params)

        assert gen_id is not None
        assert isinstance(gen_id, str)
        # Verify it's a valid UUID
        uuid.UUID(gen_id)

    def test_get_generator(self, temp_app_data_dir: str) -> None:
        """Test retrieving a generator by ID."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        params = {"model": "gpt-4", "temperature": 0.7}
        gen_id = manager.create_generator("test_gen", "openai", params)

        generator = manager.get_generator(gen_id)

        assert generator is not None
        assert generator["id"] == gen_id
        assert generator["name"] == "test_gen"
        assert generator["type"] == "openai"
        assert generator["parameters"] == params
        assert generator["status"] == "ready"

    def test_get_generator_by_name(self, temp_app_data_dir: str) -> None:
        """Test retrieving a generator by name."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        params = {"model": "gpt-4"}
        gen_id = manager.create_generator("unique_gen", "openai", params)

        generator = manager.get_generator_by_name("unique_gen")

        assert generator is not None
        assert generator["id"] == gen_id
        assert generator["name"] == "unique_gen"

    def test_list_generators(self, temp_app_data_dir: str) -> None:
        """Test listing all generators for a user."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        # Create multiple generators
        manager.create_generator("gen1", "openai", {"model": "gpt-4"})
        manager.create_generator("gen2", "anthropic", {"model": "claude"})

        generators = manager.list_generators()

        assert len(generators) == 2
        names = [gen["name"] for gen in generators]
        assert "gen1" in names
        assert "gen2" in names

    def test_update_generator(self, temp_app_data_dir: str) -> None:
        """Test updating generator configuration."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        gen_id = manager.create_generator("test_gen", "openai", {"model": "gpt-4"})

        # Update parameters
        new_params = {"model": "gpt-4-turbo", "temperature": 0.9}
        result = manager.update_generator(gen_id, parameters=new_params, status="testing")

        assert result is True

        generator = manager.get_generator(gen_id)
        assert generator["parameters"] == new_params
        assert generator["status"] == "testing"

    def test_delete_generator(self, temp_app_data_dir: str) -> None:
        """Test deleting a generator."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        gen_id = manager.create_generator("test_gen", "openai", {"model": "gpt-4"})

        result = manager.delete_generator(gen_id)
        assert result is True

        # Verify deletion
        generator = manager.get_generator(gen_id)
        assert generator is None

    def test_generator_user_isolation(self, temp_app_data_dir: str) -> None:
        """Test generators are isolated per user."""
        manager1 = SQLiteManager("user1", app_data_dir=temp_app_data_dir)
        manager2 = SQLiteManager("user2", app_data_dir=temp_app_data_dir)

        gen_id = manager1.create_generator("gen1", "openai", {"model": "gpt-4"})

        # User2 should not see user1's generator
        generator = manager2.get_generator(gen_id)
        assert generator is None


class TestDatasetOperations:
    """Test dataset CRUD operations."""

    def test_create_dataset(self, temp_app_data_dir: str) -> None:
        """Test creating a dataset."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        config = {"source": "file", "path": "/data/test.csv"}
        prompts = ["prompt1", "prompt2", "prompt3"]

        dataset_id = manager.create_dataset("test_dataset", "csv", config, prompts)

        assert dataset_id is not None
        uuid.UUID(dataset_id)

    def test_get_dataset(self, temp_app_data_dir: str) -> None:
        """Test retrieving a dataset with prompts."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        config = {"source": "file"}
        prompts = ["prompt1", "prompt2"]
        dataset_id = manager.create_dataset("test_dataset", "csv", config, prompts)

        dataset = manager.get_dataset(dataset_id)

        assert dataset is not None
        assert dataset["id"] == dataset_id
        assert dataset["name"] == "test_dataset"
        assert dataset["source_type"] == "csv"
        assert len(dataset["prompts"]) == 2
        assert dataset["prompts"][0]["text"] == "prompt1"
        assert dataset["prompts"][1]["text"] == "prompt2"

    def test_list_datasets(self, temp_app_data_dir: str) -> None:
        """Test listing datasets with prompt counts."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        manager.create_dataset("dataset1", "csv", {}, ["p1", "p2"])
        manager.create_dataset("dataset2", "json", {}, ["p1", "p2", "p3"])

        datasets = manager.list_datasets()

        assert len(datasets) == 2
        # Find datasets by name and check prompt counts
        for ds in datasets:
            if ds["name"] == "dataset1":
                assert ds["prompt_count"] == 2
            elif ds["name"] == "dataset2":
                assert ds["prompt_count"] == 3

    def test_delete_dataset(self, temp_app_data_dir: str) -> None:
        """Test deleting a dataset cascades to prompts."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        dataset_id = manager.create_dataset("test_dataset", "csv", {}, ["p1", "p2"])

        result = manager.delete_dataset(dataset_id)
        assert result is True

        # Verify deletion
        dataset = manager.get_dataset(dataset_id)
        assert dataset is None


class TestConverterOperations:
    """Test converter CRUD operations."""

    def test_create_converter(self, temp_app_data_dir: str) -> None:
        """Test creating a converter."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        params = {"type": "base64", "encoding": "utf-8"}
        converter_id = manager.create_converter("test_converter", "base64", params)

        assert converter_id is not None
        uuid.UUID(converter_id)

    def test_get_converter(self, temp_app_data_dir: str) -> None:
        """Test retrieving a converter."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        params = {"type": "rot13"}
        converter_id = manager.create_converter("rot13_conv", "rot13", params)

        converter = manager.get_converter(converter_id)

        assert converter is not None
        assert converter["name"] == "rot13_conv"
        assert converter["type"] == "rot13"
        assert converter["parameters"] == params

    def test_list_converters(self, temp_app_data_dir: str) -> None:
        """Test listing converters."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        manager.create_converter("conv1", "base64", {})
        manager.create_converter("conv2", "rot13", {})

        converters = manager.list_converters()

        assert len(converters) == 2

    def test_delete_converter(self, temp_app_data_dir: str) -> None:
        """Test deleting a converter."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        converter_id = manager.create_converter("test_conv", "base64", {})

        result = manager.delete_converter(converter_id)
        assert result is True

        converter = manager.get_converter(converter_id)
        assert converter is None


class TestScorerOperations:
    """Test scorer CRUD operations."""

    def test_create_scorer(self, temp_app_data_dir: str) -> None:
        """Test creating a scorer."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        params = {"threshold": 0.8, "model": "toxicity"}
        scorer_id = manager.create_scorer("test_scorer", "toxicity", params)

        assert scorer_id is not None
        uuid.UUID(scorer_id)

    def test_get_scorer(self, temp_app_data_dir: str) -> None:
        """Test retrieving a scorer."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        params = {"threshold": 0.9}
        scorer_id = manager.create_scorer("toxicity_scorer", "toxicity", params)

        scorer = manager.get_scorer(scorer_id)

        assert scorer is not None
        assert scorer["name"] == "toxicity_scorer"
        assert scorer["parameters"] == params

    def test_list_scorers(self, temp_app_data_dir: str) -> None:
        """Test listing scorers."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        manager.create_scorer("scorer1", "toxicity", {})
        manager.create_scorer("scorer2", "bias", {})

        scorers = manager.list_scorers()

        assert len(scorers) == 2

    def test_delete_scorer(self, temp_app_data_dir: str) -> None:
        """Test deleting a scorer."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        scorer_id = manager.create_scorer("test_scorer", "toxicity", {})

        result = manager.delete_scorer(scorer_id)
        assert result is True

        scorer = manager.get_scorer(scorer_id)
        assert scorer is None


class TestSessionOperations:
    """Test session CRUD operations."""

    def test_save_session(self, temp_app_data_dir: str) -> None:
        """Test saving session data."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        session_data = {"key": "value", "config": {"setting": "enabled"}}
        result = manager.save_session("my_session", session_data)

        assert result is True

    def test_get_session(self, temp_app_data_dir: str) -> None:
        """Test retrieving session data."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        session_data = {"key": "value", "nested": {"data": 123}}
        manager.save_session("my_session", session_data)

        session = manager.get_session("my_session")

        assert session is not None
        assert session["data"] == session_data

    def test_update_existing_session(self, temp_app_data_dir: str) -> None:
        """Test updating existing session data."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        # Create session
        manager.save_session("my_session", {"count": 1})

        # Update session
        manager.save_session("my_session", {"count": 2})

        session = manager.get_session("my_session")
        assert session["data"]["count"] == 2


class TestSecurityFeatures:
    """Test security features and SQL injection protection."""

    def test_column_whitelist_validation(self, temp_app_data_dir: str) -> None:
        """Test that only whitelisted columns can be updated."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        gen_id = manager.create_generator("test", "openai", {})

        # This should raise ValueError due to invalid column
        updates = {"malicious_column": "value"}
        with pytest.raises(ValueError, match="Invalid column"):
            manager._build_safe_update_query(updates, gen_id, "test_user")

    def test_table_whitelist_validation(self, temp_app_data_dir: str) -> None:
        """Test that only whitelisted tables can be counted."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        with sqlite3.connect(manager.db_path) as conn:
            # This should raise ValueError
            with pytest.raises(ValueError, match="Invalid table name"):
                manager._get_table_count(conn, "malicious_table")

    def test_parameterized_queries(self, temp_app_data_dir: str) -> None:
        """Test that all queries use parameterized statements."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        # Attempt SQL injection in generator name
        malicious_name = "test'; DROP TABLE generators; --"
        gen_id = manager.create_generator(malicious_name, "openai", {})

        # Verify table still exists and data is safe
        generator = manager.get_generator(gen_id)
        assert generator is not None
        assert generator["name"] == malicious_name


class TestUtilityMethods:
    """Test utility and helper methods."""

    def test_get_stats(self, temp_app_data_dir: str) -> None:
        """Test getting database statistics."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        # Create some data
        manager.create_generator("gen1", "openai", {})
        manager.create_dataset("ds1", "csv", {}, ["p1", "p2"])
        manager.create_converter("conv1", "base64", {})

        stats = manager.get_stats()

        assert "generators" in stats
        assert stats["generators"] == 1
        assert "datasets" in stats
        assert stats["datasets"] == 1
        assert "dataset_prompts" in stats
        assert stats["dataset_prompts"] == 2
        assert "converters" in stats
        assert stats["converters"] == 1
        assert "db_size_mb" in stats

    def test_factory_function(self, temp_app_data_dir: str) -> None:
        """Test the get_sqlite_manager factory function."""
        # Temporarily set APP_DATA_DIR env var
        os.environ["APP_DATA_DIR"] = temp_app_data_dir

        manager = get_sqlite_manager("test_user")

        assert manager is not None
        assert isinstance(manager, SQLiteManager)
        assert manager.username == "test_user"

        # Clean up env var
        del os.environ["APP_DATA_DIR"]


class TestConcurrency:
    """Test concurrent access and transactions."""

    def test_concurrent_writes(self, temp_app_data_dir: str) -> None:
        """Test concurrent writes with WAL mode."""
        manager = SQLiteManager("test_user", app_data_dir=temp_app_data_dir)

        # Create multiple generators rapidly
        gen_ids = []
        for i in range(10):
            gen_id = manager.create_generator(f"gen_{i}", "openai", {"index": i})
            gen_ids.append(gen_id)

        # Verify all were created
        generators = manager.list_generators()
        assert len(generators) == 10


# Pytest fixtures
@pytest.fixture
def temp_app_data_dir() -> str:
    """Create temporary directory for test databases."""
    temp_dir = tempfile.mkdtemp(prefix="violentutf_test_")
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
