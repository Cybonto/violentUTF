#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""PyRIT SQLiteMemory Compatibility Test Suite

This test suite validates that SQLiteMemory from PyRIT v0.10.0rc0 is
compatible with the usage patterns in pyrit_memory_bridge.py.
"""

import os
import tempfile
from typing import List

import pytest
import pytest_asyncio
from pyrit.memory import SQLiteMemory
from pyrit.models import SeedPrompt


class TestSQLiteMemoryBasicOperations:
    """Test basic CRUD operations with SQLiteMemory."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
        for suffix in ["-wal", "-shm", "-journal"]:
            journal_path = path + suffix
            if os.path.exists(journal_path):
                os.remove(journal_path)

    @pytest.fixture
    def memory(self, temp_db_path):
        """Create a SQLiteMemory instance."""
        mem = SQLiteMemory(db_path=temp_db_path)
        yield mem
        mem.dispose_engine()

    def test_memory_initialization_with_path(self, temp_db_path):
        """Test SQLiteMemory initialization with custom path."""
        memory = SQLiteMemory(db_path=temp_db_path)
        assert memory is not None
        memory.dispose_engine()

    def test_memory_initialization_default(self):
        """Test SQLiteMemory initialization with default path."""
        memory = SQLiteMemory()
        assert memory is not None
        memory.dispose_engine()

    @pytest.mark.asyncio
    async def test_add_seed_prompts_single(self, memory):
        """Test adding a single seed prompt."""
        prompts = [
            SeedPrompt(
                value="Test prompt",
                data_type="text",
                metadata={"test_key": "test_value"},
                added_by="test_user",
            )
        ]

        await memory.add_seed_prompts_to_memory_async(prompts=prompts, added_by="test_user")

        # Verify prompt was stored
        retrieved = memory.get_seed_prompts()
        assert len(retrieved) >= 1
        assert any(p.value == "Test prompt" for p in retrieved)

    @pytest.mark.asyncio
    async def test_add_seed_prompts_batch(self, memory):
        """Test adding multiple seed prompts in batch."""
        prompts = [
            SeedPrompt(
                value=f"Test prompt {i}",
                data_type="text",
                metadata={"index": str(i), "batch": "test_batch"},
                added_by="test_user",
            )
            for i in range(100)
        ]

        await memory.add_seed_prompts_to_memory_async(prompts=prompts, added_by="test_user")

        # Verify all prompts were stored
        retrieved = memory.get_seed_prompts()
        assert len(retrieved) >= 100

    @pytest.mark.asyncio
    async def test_add_seed_prompts_with_metadata(self, memory):
        """Test adding prompts with rich metadata."""
        prompts = [
            SeedPrompt(
                value="Test prompt with metadata",
                data_type="text",
                metadata={
                    "dataset_id": "test_dataset",
                    "import_batch": "1",
                    "user_id": "test_user",
                    "category": "test",
                },
                added_by="test_user",
            )
        ]

        await memory.add_seed_prompts_to_memory_async(prompts=prompts, added_by="test_user")

        # Verify metadata was stored
        retrieved = memory.get_seed_prompts(metadata={"dataset_id": "test_dataset"})
        assert len(retrieved) >= 1
        assert retrieved[0].metadata["dataset_id"] == "test_dataset"


class TestSQLiteMemoryQueryOperations:
    """Test query and filtering operations."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
        for suffix in ["-wal", "-shm", "-journal"]:
            journal_path = path + suffix
            if os.path.exists(journal_path):
                os.remove(journal_path)

    @pytest.fixture
    def memory(self, temp_db_path):
        """Create a SQLiteMemory instance."""
        mem = SQLiteMemory(db_path=temp_db_path)
        yield mem
        mem.dispose_engine()

    async def _populate_memory(self, memory):
        """Helper to populate memory with test data."""
        prompts = []
        for i in range(50):
            prompts.append(
                SeedPrompt(
                    value=f"Dataset A prompt {i}",
                    data_type="text",
                    metadata={
                        "dataset_id": "dataset_a",
                        "category": f"category_{i % 5}",
                    },
                    added_by="test_user",
                )
            )
        for i in range(30):
            prompts.append(
                SeedPrompt(
                    value=f"Dataset B prompt {i}",
                    data_type="text",
                    metadata={
                        "dataset_id": "dataset_b",
                        "category": f"category_{i % 3}",
                    },
                    added_by="test_user",
                )
            )

        await memory.add_seed_prompts_to_memory_async(prompts=prompts, added_by="test_user")

    @pytest.mark.asyncio
    async def test_get_all_prompts(self, memory):
        """Test retrieving all prompts."""
        await self._populate_memory(memory)
        prompts = memory.get_seed_prompts()
        assert len(prompts) >= 80

    @pytest.mark.asyncio
    async def test_get_prompts_with_metadata_filter(self, memory):
        """Test filtering prompts by metadata."""
        await self._populate_memory(memory)
        prompts = memory.get_seed_prompts(metadata={"dataset_id": "dataset_a"})
        assert len(prompts) >= 50
        assert all(p.metadata.get("dataset_id") == "dataset_a" for p in prompts)

    @pytest.mark.asyncio
    async def test_get_prompts_with_value_search(self, memory):
        """Test searching prompts by value."""
        await self._populate_memory(memory)
        prompts = memory.get_seed_prompts(value="Dataset A prompt 10")
        assert len(prompts) >= 1
        assert prompts[0].value == "Dataset A prompt 10"

    @pytest.mark.asyncio
    async def test_get_prompts_with_multiple_filters(self, memory):
        """Test filtering with multiple criteria."""
        await self._populate_memory(memory)
        prompts = memory.get_seed_prompts(metadata={"dataset_id": "dataset_a", "category": "category_2"})
        # Should get prompts where i % 5 == 2 (i.e., 2, 7, 12, 17, ...)
        assert len(prompts) >= 10


class TestSQLiteMemoryConnectionManagement:
    """Test connection management and cleanup."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
        for suffix in ["-wal", "-shm", "-journal"]:
            journal_path = path + suffix
            if os.path.exists(journal_path):
                os.remove(journal_path)

    def test_dispose_engine(self, temp_db_path):
        """Test proper engine disposal."""
        memory = SQLiteMemory(db_path=temp_db_path)
        memory.dispose_engine()
        # Should not raise an error

    def test_multiple_dispose_calls(self, temp_db_path):
        """Test that multiple dispose calls don't cause errors."""
        memory = SQLiteMemory(db_path=temp_db_path)
        memory.dispose_engine()
        memory.dispose_engine()  # Should not raise

    @pytest.mark.asyncio
    async def test_reopen_database(self, temp_db_path):
        """Test reopening an existing database."""
        # Create and populate database
        memory1 = SQLiteMemory(db_path=temp_db_path)
        prompts = [
            SeedPrompt(
                value="Test prompt",
                data_type="text",
                metadata={"test": "value"},
                added_by="test_user",
            )
        ]
        await memory1.add_seed_prompts_to_memory_async(prompts=prompts, added_by="test_user")
        memory1.dispose_engine()

        # Reopen and verify data persisted
        memory2 = SQLiteMemory(db_path=temp_db_path)
        retrieved = memory2.get_seed_prompts()
        assert len(retrieved) >= 1
        assert any(p.value == "Test prompt" for p in retrieved)
        memory2.dispose_engine()


class TestSQLiteMemoryPyRITBridgeCompatibility:
    """Test compatibility with pyrit_memory_bridge.py usage patterns."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
        for suffix in ["-wal", "-shm", "-journal"]:
            journal_path = path + suffix
            if os.path.exists(journal_path):
                os.remove(journal_path)

    @pytest.fixture
    def memory(self, temp_db_path):
        """Create a SQLiteMemory instance."""
        mem = SQLiteMemory(db_path=temp_db_path)
        yield mem
        mem.dispose_engine()

    @pytest.mark.asyncio
    async def test_bridge_add_prompts_pattern(self, memory):
        """Test the add prompts pattern used in pyrit_memory_bridge.py."""
        # Simulate the bridge usage pattern
        dataset_id = "test_dataset"
        user_id = "test_user"
        batch_size = 100

        prompts = []
        for i in range(250):
            metadata = {
                "dataset_id": dataset_id,
                "import_batch": str(i // batch_size),
                "user_id": user_id,
            }
            prompt = SeedPrompt(
                value=f"Test prompt {i}",
                data_type="text",
                metadata=metadata,
                added_by=user_id,
            )
            prompts.append(prompt)

        # Store in batches
        for batch_start in range(0, len(prompts), batch_size):
            batch = prompts[batch_start : batch_start + batch_size]
            await memory.add_seed_prompts_to_memory_async(prompts=batch, added_by=user_id)

        # Verify storage
        all_prompts = memory.get_seed_prompts(metadata={"dataset_id": dataset_id})
        assert len(all_prompts) >= 250

    @pytest.mark.asyncio
    async def test_bridge_get_prompts_pattern(self, memory):
        """Test the get prompts pattern used in pyrit_memory_bridge.py."""
        # Add test data
        dataset_id = "test_dataset"
        user_id = "test_user"

        prompts = [
            SeedPrompt(
                value=f"Test prompt {i}",
                data_type="text",
                metadata={"dataset_id": dataset_id, "user_id": user_id},
                added_by=user_id,
            )
            for i in range(100)
        ]

        await memory.add_seed_prompts_to_memory_async(prompts=prompts, added_by=user_id)

        # Test retrieval with metadata filtering
        retrieved = memory.get_seed_prompts(metadata={"dataset_id": dataset_id, "user_id": user_id})

        assert len(retrieved) >= 100

    @pytest.mark.asyncio
    async def test_bridge_user_isolation_pattern(self, memory):
        """Test user isolation pattern from pyrit_memory_bridge.py."""
        # Add data for multiple users
        for user_id in ["user1", "user2", "user3"]:
            prompts = [
                SeedPrompt(
                    value=f"{user_id} prompt {i}",
                    data_type="text",
                    metadata={"user_id": user_id},
                    added_by=user_id,
                )
                for i in range(10)
            ]
            await memory.add_seed_prompts_to_memory_async(prompts=prompts, added_by=user_id)

        # Verify isolation
        user1_prompts = memory.get_seed_prompts(metadata={"user_id": "user1"})
        assert len(user1_prompts) >= 10
        assert all("user1" in p.value for p in user1_prompts)


class TestSQLiteMemoryErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
        for suffix in ["-wal", "-shm", "-journal"]:
            journal_path = path + suffix
            if os.path.exists(journal_path):
                os.remove(journal_path)

    @pytest.fixture
    def memory(self, temp_db_path):
        """Create a SQLiteMemory instance."""
        mem = SQLiteMemory(db_path=temp_db_path)
        yield mem
        mem.dispose_engine()

    @pytest.mark.asyncio
    async def test_empty_prompts_list(self, memory):
        """Test adding empty prompts list."""
        await memory.add_seed_prompts_to_memory_async(prompts=[], added_by="test_user")
        # Should not raise an error

    @pytest.mark.asyncio
    async def test_query_empty_database(self, memory):
        """Test querying empty database."""
        prompts = memory.get_seed_prompts()
        assert prompts == []

    @pytest.mark.asyncio
    async def test_query_nonexistent_metadata(self, memory):
        """Test querying with non-existent metadata."""
        prompts = [
            SeedPrompt(
                value="Test",
                data_type="text",
                metadata={"key1": "value1"},
                added_by="test_user",
            )
        ]
        await memory.add_seed_prompts_to_memory_async(prompts=prompts, added_by="test_user")

        retrieved = memory.get_seed_prompts(metadata={"nonexistent_key": "nonexistent_value"})
        assert retrieved == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
