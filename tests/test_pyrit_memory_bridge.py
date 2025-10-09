# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Comprehensive Test Suite for PyRITMemoryBridge - Issue #327.

Tests all PyRIT memory operations including:
- Memory initialization and caching
- Prompt storage and retrieval
- Dataset statistics and management
- Cleanup operations
- User isolation

Follows TDD methodology for issue #327 Phase 4.3.6.
"""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Check if SQLiteMemory is available (PyRIT v0.10.0rc0+)
try:
    from pyrit.common.singleton import Singleton
    from pyrit.memory import SQLiteMemory

    SQLITE_MEMORY_AVAILABLE = True
except ImportError:
    SQLITE_MEMORY_AVAILABLE = False
    SQLiteMemory = None
    Singleton = None

# Import the service to test
from violentutf_api.fastapi_app.app.services.pyrit_memory_bridge import (
    PyRITMemoryBridge,
    UserContextManager,
)

# Skip all tests if SQLiteMemory not available
pytestmark = pytest.mark.skipif(
    not SQLITE_MEMORY_AVAILABLE, reason="SQLiteMemory not available - requires PyRIT v0.10.0rc0+ (issue #323)"
)


@pytest.fixture
def temp_memory_dir():
    """Create a temporary directory for PyRIT memory databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set environment variable for test
        old_dir = os.environ.get("PYRIT_MEMORY_DIR")
        os.environ["PYRIT_MEMORY_DIR"] = tmpdir
        yield tmpdir
        # Restore original
        if old_dir:
            os.environ["PYRIT_MEMORY_DIR"] = old_dir
        else:
            os.environ.pop("PYRIT_MEMORY_DIR", None)


@pytest.fixture
def memory_bridge(temp_memory_dir):
    """Create a PyRITMemoryBridge instance for testing."""
    bridge = PyRITMemoryBridge()
    yield bridge
    # Cleanup: close all connections and clear singleton
    bridge.close_memory_connections()
    if SQLiteMemory in Singleton._instances:
        del Singleton._instances[SQLiteMemory]


class TestUserContextManager:
    """Test UserContextManager for user isolation."""

    def test_get_user_hash_consistency(self):
        """Test that user hash is consistent for same user_id."""
        hash1 = UserContextManager.get_user_hash("test_user")
        hash2 = UserContextManager.get_user_hash("test_user")
        assert hash1 == hash2
        assert len(hash1) == 16  # Should be 16 chars

    def test_get_user_hash_different_users(self):
        """Test that different users get different hashes."""
        hash1 = UserContextManager.get_user_hash("user1")
        hash2 = UserContextManager.get_user_hash("user2")
        assert hash1 != hash2

    def test_get_user_memory_path(self, temp_memory_dir):
        """Test memory path generation."""
        path = UserContextManager.get_user_memory_path("test_user")
        assert path.startswith(temp_memory_dir)
        assert path.endswith(".db")
        assert "pyrit_memory_" in path


class TestMemoryInitialization:
    """Test memory initialization and caching."""

    @pytest.mark.asyncio
    async def test_get_or_create_user_memory_sqlite(self, memory_bridge):
        """Test that get_or_create_user_memory returns SQLiteMemory instance."""
        memory = await memory_bridge.get_or_create_user_memory("test_user")
        assert memory is not None
        assert isinstance(memory, SQLiteMemory)

    @pytest.mark.asyncio
    async def test_memory_caching(self, memory_bridge):
        """Test that memory instances are cached per user."""
        memory1 = await memory_bridge.get_or_create_user_memory("test_user")
        memory2 = await memory_bridge.get_or_create_user_memory("test_user")
        # Should return same instance from cache
        assert memory1 is memory2

    @pytest.mark.asyncio
    async def test_different_users_different_memory(self, memory_bridge):
        """Test that different users get different memory instances."""
        memory1 = await memory_bridge.get_or_create_user_memory("user1")
        memory2 = await memory_bridge.get_or_create_user_memory("user2")
        assert memory1 is not memory2

    @pytest.mark.asyncio
    async def test_memory_file_created(self, memory_bridge, temp_memory_dir):
        """Test that SQLite database file is created."""
        await memory_bridge.get_or_create_user_memory("test_user")
        # Check that a .db file exists
        db_files = list(Path(temp_memory_dir).glob("pyrit_memory_*.db"))
        assert len(db_files) >= 1


class TestPromptOperations:
    """Test prompt storage and retrieval operations."""

    @pytest.mark.asyncio
    async def test_store_prompts_to_pyrit_memory(self, memory_bridge):
        """Test storing prompts to PyRIT memory."""
        prompts = ["Test prompt 1", "Test prompt 2", "Test prompt 3"]
        metadata = [{}, {}, {}]

        count = await memory_bridge.store_prompts_to_pyrit_memory(
            prompts=prompts,
            metadata=metadata,
            dataset_id="test_dataset",
            user_id="test_user",
        )

        assert count == 3

    @pytest.mark.asyncio
    async def test_store_prompts_with_metadata(self, memory_bridge):
        """Test storing prompts with custom metadata."""
        prompts = ["Prompt with metadata"]
        metadata = [{"custom_key": "custom_value", "index": 0}]

        count = await memory_bridge.store_prompts_to_pyrit_memory(
            prompts=prompts,
            metadata=metadata,
            dataset_id="test_dataset",
            user_id="test_user",
        )

        assert count == 1

        # Retrieve and verify metadata
        result, total = await memory_bridge.get_prompts_from_pyrit_memory(
            dataset_id="test_dataset",
            user_id="test_user",
            include_metadata=True,
        )

        assert len(result) >= 1
        # Check that our custom metadata is included
        assert any(item.get("metadata", {}).get("custom_key") == "custom_value" for item in result)

    @pytest.mark.asyncio
    async def test_store_prompts_batch_processing(self, memory_bridge):
        """Test batch processing for large prompt sets."""
        # Create 250 prompts (should be split into 3 batches of 100)
        prompts = [f"Prompt {i}" for i in range(250)]
        metadata = [{} for _ in range(250)]

        count = await memory_bridge.store_prompts_to_pyrit_memory(
            prompts=prompts,
            metadata=metadata,
            dataset_id="large_dataset",
            user_id="test_user",
            batch_size=100,
        )

        assert count == 250

    @pytest.mark.asyncio
    async def test_get_prompts_from_pyrit_memory(self, memory_bridge):
        """Test retrieving prompts from PyRIT memory."""
        # First store some prompts
        prompts = ["Prompt A", "Prompt B", "Prompt C"]
        metadata = [{}, {}, {}]
        await memory_bridge.store_prompts_to_pyrit_memory(
            prompts=prompts,
            metadata=metadata,
            dataset_id="retrieve_test",
            user_id="test_user",
        )

        # Retrieve prompts
        result, total = await memory_bridge.get_prompts_from_pyrit_memory(
            dataset_id="retrieve_test",
            user_id="test_user",
            include_metadata=False,
        )

        assert len(result) >= 3
        assert total >= 3
        # Result should be list of strings when include_metadata=False
        assert all(isinstance(p, str) for p in result)

    @pytest.mark.asyncio
    async def test_get_prompts_with_metadata(self, memory_bridge):
        """Test retrieving prompts with metadata."""
        # Store prompts
        prompts = ["Prompt 1"]
        metadata = [{"key": "value"}]
        await memory_bridge.store_prompts_to_pyrit_memory(
            prompts=prompts,
            metadata=metadata,
            dataset_id="metadata_test",
            user_id="test_user",
        )

        # Retrieve with metadata
        result, total = await memory_bridge.get_prompts_from_pyrit_memory(
            dataset_id="metadata_test",
            user_id="test_user",
            include_metadata=True,
        )

        assert len(result) >= 1
        assert total >= 1
        # Result should be list of dicts when include_metadata=True
        assert all(isinstance(p, dict) for p in result)

    @pytest.mark.asyncio
    async def test_get_prompts_pagination(self, memory_bridge):
        """Test pagination of prompt retrieval."""
        # Store 50 prompts
        prompts = [f"Prompt {i}" for i in range(50)]
        metadata = [{} for _ in range(50)]
        await memory_bridge.store_prompts_to_pyrit_memory(
            prompts=prompts,
            metadata=metadata,
            dataset_id="pagination_test",
            user_id="test_user",
        )

        # Get first page
        result1, total = await memory_bridge.get_prompts_from_pyrit_memory(
            dataset_id="pagination_test",
            user_id="test_user",
            offset=0,
            limit=20,
        )

        assert len(result1) <= 20
        assert total >= 50

        # Get second page
        result2, total = await memory_bridge.get_prompts_from_pyrit_memory(
            dataset_id="pagination_test",
            user_id="test_user",
            offset=20,
            limit=20,
        )

        assert len(result2) <= 20


class TestDatasetStatistics:
    """Test dataset statistics operations."""

    @pytest.mark.asyncio
    async def test_get_dataset_statistics(self, memory_bridge):
        """Test getting statistics for a dataset."""
        # Store some prompts
        prompts = [f"Prompt {i}" for i in range(10)]
        metadata = [{} for _ in range(10)]
        await memory_bridge.store_prompts_to_pyrit_memory(
            prompts=prompts,
            metadata=metadata,
            dataset_id="stats_test",
            user_id="test_user",
        )

        # Get statistics
        stats = await memory_bridge.get_dataset_statistics(dataset_id="stats_test", user_id="test_user")

        assert stats is not None
        assert "total_prompts" in stats
        assert stats["total_prompts"] >= 10
        assert "dataset_id" in stats
        assert stats["dataset_id"] == "stats_test"

    @pytest.mark.asyncio
    async def test_get_dataset_statistics_empty_dataset(self, memory_bridge):
        """Test statistics for non-existent dataset."""
        stats = await memory_bridge.get_dataset_statistics(dataset_id="nonexistent", user_id="test_user")

        assert stats is not None
        assert stats["total_prompts"] == 0


class TestDatasetDeletion:
    """Test dataset deletion operations."""

    @pytest.mark.asyncio
    async def test_delete_dataset_from_memory(self, memory_bridge):
        """Test deleting a dataset from memory."""
        # Store prompts
        prompts = ["Delete me 1", "Delete me 2"]
        metadata = [{}, {}]
        await memory_bridge.store_prompts_to_pyrit_memory(
            prompts=prompts,
            metadata=metadata,
            dataset_id="delete_test",
            user_id="test_user",
        )

        # Delete dataset
        success = await memory_bridge.delete_dataset_from_memory(dataset_id="delete_test", user_id="test_user")

        assert success is True

        # Verify deletion - should have 0 prompts now
        stats = await memory_bridge.get_dataset_statistics(dataset_id="delete_test", user_id="test_user")
        assert stats["total_prompts"] == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_dataset(self, memory_bridge):
        """Test deleting a dataset that doesn't exist."""
        success = await memory_bridge.delete_dataset_from_memory(dataset_id="nonexistent", user_id="test_user")

        # Should still return True (idempotent operation)
        assert success is True


class TestCleanupOperations:
    """Test cleanup and maintenance operations."""

    @pytest.mark.asyncio
    async def test_cleanup_user_memory(self, memory_bridge):
        """Test cleaning up old prompts from memory."""
        # Store some prompts
        prompts = ["Old prompt 1", "Old prompt 2"]
        metadata = [{}, {}]
        await memory_bridge.store_prompts_to_pyrit_memory(
            prompts=prompts,
            metadata=metadata,
            dataset_id="cleanup_test",
            user_id="test_user",
        )

        # Run cleanup (with max_age_days=0 should delete recent prompts too)
        result = await memory_bridge.cleanup_user_memory(user_id="test_user", max_age_days=0)

        assert result is not None
        assert "prompts_deleted" in result

    @pytest.mark.asyncio
    async def test_cleanup_preserves_recent_data(self, memory_bridge):
        """Test that cleanup preserves recent data."""
        # Store prompts
        prompts = ["Recent prompt"]
        metadata = [{}]
        await memory_bridge.store_prompts_to_pyrit_memory(
            prompts=prompts,
            metadata=metadata,
            dataset_id="preserve_test",
            user_id="test_user",
        )

        # Run cleanup with max_age_days=30 (should preserve recent data)
        result = await memory_bridge.cleanup_user_memory(user_id="test_user", max_age_days=30)

        # Verify data still exists
        stats = await memory_bridge.get_dataset_statistics(dataset_id="preserve_test", user_id="test_user")
        assert stats["total_prompts"] >= 1


class TestMemoryConnections:
    """Test memory connection management."""

    def test_close_memory_connections(self, memory_bridge):
        """Test closing all memory connections."""
        # This should not raise an error
        memory_bridge.close_memory_connections()

    @pytest.mark.asyncio
    async def test_close_memory_connections_with_sqlite(self, memory_bridge):
        """Test closing connections with active SQLite instances."""
        # Create some memory instances
        await memory_bridge.get_or_create_user_memory("user1")
        await memory_bridge.get_or_create_user_memory("user2")

        # Close all connections
        memory_bridge.close_memory_connections()

        # Memory cache should be empty
        assert len(memory_bridge.memory_cache) == 0


class TestUserIsolation:
    """Test user isolation and data separation."""

    @pytest.mark.asyncio
    async def test_users_have_separate_databases(self, memory_bridge, temp_memory_dir):
        """Test that different users get separate database files."""
        await memory_bridge.get_or_create_user_memory("user1")
        await memory_bridge.get_or_create_user_memory("user2")

        # Should have 2 different database files
        db_files = list(Path(temp_memory_dir).glob("pyrit_memory_*.db"))
        assert len(db_files) >= 2

    @pytest.mark.asyncio
    async def test_users_cannot_access_other_data(self, memory_bridge):
        """Test that users cannot access other users' data."""
        # User1 stores prompts
        prompts1 = ["User1 prompt"]
        metadata1 = [{}]
        await memory_bridge.store_prompts_to_pyrit_memory(
            prompts=prompts1,
            metadata=metadata1,
            dataset_id="user1_dataset",
            user_id="user1",
        )

        # User2 tries to access user1's dataset
        result, total = await memory_bridge.get_prompts_from_pyrit_memory(
            dataset_id="user1_dataset",
            user_id="user2",  # Different user
        )

        # Should return empty (no cross-user access)
        assert total == 0 or len(result) == 0

    @pytest.mark.asyncio
    async def test_user_data_isolation_in_stats(self, memory_bridge):
        """Test that statistics are isolated per user."""
        # User1 stores prompts
        await memory_bridge.store_prompts_to_pyrit_memory(
            prompts=["User1 data"],
            metadata=[{}],
            dataset_id="shared_dataset_name",
            user_id="user1",
        )

        # User2 checks stats for same dataset name
        stats = await memory_bridge.get_dataset_statistics(
            dataset_id="shared_dataset_name",
            user_id="user2",
        )

        # Should be 0 (different user's database)
        assert stats["total_prompts"] == 0


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_store_empty_prompts_list(self, memory_bridge):
        """Test storing empty prompts list."""
        count = await memory_bridge.store_prompts_to_pyrit_memory(
            prompts=[],
            metadata=[],
            dataset_id="empty_test",
            user_id="test_user",
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_get_prompts_with_zero_limit(self, memory_bridge):
        """Test retrieving prompts with limit=0."""
        result, total = await memory_bridge.get_prompts_from_pyrit_memory(
            dataset_id="any_dataset",
            user_id="test_user",
            limit=0,
        )

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_large_offset_pagination(self, memory_bridge):
        """Test pagination with offset larger than total results."""
        # Store a few prompts
        await memory_bridge.store_prompts_to_pyrit_memory(
            prompts=["Prompt 1", "Prompt 2"],
            metadata=[{}, {}],
            dataset_id="offset_test",
            user_id="test_user",
        )

        # Request with large offset
        result, total = await memory_bridge.get_prompts_from_pyrit_memory(
            dataset_id="offset_test",
            user_id="test_user",
            offset=1000,
            limit=10,
        )

        assert len(result) == 0
        assert total >= 2
