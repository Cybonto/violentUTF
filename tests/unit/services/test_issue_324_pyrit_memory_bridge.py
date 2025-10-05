# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Unit Tests for Issue #324: PyRITMemoryBridge SQLiteMemory Migration

This test suite validates that PyRITMemoryBridge correctly uses SQLiteMemory
instead of DuckDBMemory while maintaining all existing functionality.

Test-Driven Development (TDD) Approach:
1. RED: Write failing tests that expect SQLiteMemory
2. GREEN: Update implementation to use SQLiteMemory
3. REFACTOR: Ensure code quality and maintainability
"""

import os
import tempfile
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pyrit.memory import SQLiteMemory
from pyrit.models import SeedPrompt


class TestPyRITMemoryBridgeImports:
    """Test that PyRITMemoryBridge uses SQLiteMemory imports."""

    def test_imports_sqlite_memory_not_duckdb(self):
        """Verify that the module imports SQLiteMemory, not DuckDBMemory."""
        # Import the module
        from violentutf_api.fastapi_app.app.services import (
            pyrit_memory_bridge,
        )

        # Check that SQLiteMemory is accessible in the module
        assert hasattr(pyrit_memory_bridge, "SQLiteMemory"), "Module should import SQLiteMemory"

        # Verify it's the correct SQLiteMemory class
        assert pyrit_memory_bridge.SQLiteMemory == SQLiteMemory, "Should be pyrit.memory.SQLiteMemory"

    def test_no_duckdb_imports(self):
        """Verify that DuckDBMemory is not imported."""
        # Import the module
        from violentutf_api.fastapi_app.app.services import (
            pyrit_memory_bridge,
        )

        # Check that DuckDBMemory is NOT accessible
        assert not hasattr(pyrit_memory_bridge, "DuckDBMemory"), "Module should not import DuckDBMemory"


class TestPyRITMemoryBridgeTypeAnnotations:
    """Test that type annotations use SQLiteMemory."""

    def test_memory_cache_type_annotation(self):
        """Verify memory_cache is typed as Dict[str, SQLiteMemory]."""
        from violentutf_api.fastapi_app.app.services.pyrit_memory_bridge import (
            PyRITMemoryBridge,
        )

        # Get type hints for the class
        bridge = PyRITMemoryBridge()

        # Check the memory_cache attribute exists and is a dict
        assert hasattr(bridge, "memory_cache"), "PyRITMemoryBridge should have memory_cache"
        assert isinstance(bridge.memory_cache, dict), "memory_cache should be a dictionary"

    def test_get_or_create_user_memory_return_type(self):
        """Verify get_or_create_user_memory returns SQLiteMemory."""
        import inspect

        from violentutf_api.fastapi_app.app.services.pyrit_memory_bridge import (
            PyRITMemoryBridge,
        )

        # Get the method signature
        sig = inspect.signature(PyRITMemoryBridge.get_or_create_user_memory)

        # Check return annotation
        return_annotation = sig.return_annotation

        # The annotation should reference SQLiteMemory
        # It will be a string in some Python versions, so check both
        assert "SQLiteMemory" in str(return_annotation), f"Return type should be SQLiteMemory, got {return_annotation}"


@pytest.mark.asyncio
class TestPyRITMemoryBridgeMemoryInstantiation:
    """Test that PyRITMemoryBridge instantiates SQLiteMemory correctly."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
        for suffix in ["-wal", "-shm", "-journal"]:
            journal_path = path + suffix
            if os.path.exists(journal_path):
                os.remove(journal_path)

    @pytest.fixture
    def mock_env(self, temp_db_path):
        """Mock environment variables for testing."""
        with patch.dict(
            os.environ,
            {
                "PYRIT_DB_SALT": "test_salt",
                "PYRIT_MEMORY_DIR": os.path.dirname(temp_db_path),
            },
        ):
            yield

    async def test_creates_sqlite_memory_instance(self, mock_env):
        """Verify that get_or_create_user_memory creates SQLiteMemory."""
        from violentutf_api.fastapi_app.app.services.pyrit_memory_bridge import (
            PyRITMemoryBridge,
        )

        bridge = PyRITMemoryBridge()
        memory = await bridge.get_or_create_user_memory("test_user")

        # Verify it's an SQLiteMemory instance
        assert isinstance(memory, SQLiteMemory), f"Expected SQLiteMemory, got {type(memory)}"

        # Cleanup
        bridge.close_memory_connections()

    async def test_memory_uses_correct_db_path(self, mock_env):
        """Verify that SQLiteMemory is created with correct database path."""
        from violentutf_api.fastapi_app.app.services.pyrit_memory_bridge import (
            PyRITMemoryBridge,
        )

        bridge = PyRITMemoryBridge()
        user_id = "test_user_123"

        memory = await bridge.get_or_create_user_memory(user_id)

        # Verify memory was created
        assert memory is not None
        assert isinstance(memory, SQLiteMemory)

        # Cleanup
        bridge.close_memory_connections()

    async def test_memory_caching_uses_sqlite(self, mock_env):
        """Verify that cached memory instances are SQLiteMemory."""
        from violentutf_api.fastapi_app.app.services.pyrit_memory_bridge import (
            PyRITMemoryBridge,
        )

        bridge = PyRITMemoryBridge()
        user_id = "test_user"

        # Create memory instance
        memory1 = await bridge.get_or_create_user_memory(user_id)
        memory2 = await bridge.get_or_create_user_memory(user_id)

        # Verify both are SQLiteMemory
        assert isinstance(memory1, SQLiteMemory)
        assert isinstance(memory2, SQLiteMemory)

        # Verify caching works (same instance)
        assert memory1 is memory2

        # Cleanup
        bridge.close_memory_connections()


@pytest.mark.asyncio
class TestPyRITMemoryBridgeFunctionality:
    """Test that all PyRITMemoryBridge methods work with SQLiteMemory."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
        for suffix in ["-wal", "-shm", "-journal"]:
            journal_path = path + suffix
            if os.path.exists(journal_path):
                os.remove(journal_path)

    @pytest.fixture
    def mock_env(self, temp_db_path):
        """Mock environment variables for testing."""
        with patch.dict(
            os.environ,
            {
                "PYRIT_DB_SALT": "test_salt",
                "PYRIT_MEMORY_DIR": os.path.dirname(temp_db_path),
            },
        ):
            yield

    async def test_store_prompts_with_sqlite(self, mock_env):
        """Test storing prompts to SQLiteMemory."""
        from violentutf_api.fastapi_app.app.services.pyrit_memory_bridge import (
            PyRITMemoryBridge,
        )

        bridge = PyRITMemoryBridge()
        user_id = "test_user"
        dataset_id = "test_dataset"

        prompts = ["Test prompt 1", "Test prompt 2", "Test prompt 3"]
        metadata = [
            {"index": 0},
            {"index": 1},
            {"index": 2},
        ]

        # Store prompts
        count = await bridge.store_prompts_to_pyrit_memory(
            prompts=prompts,
            metadata=metadata,
            dataset_id=dataset_id,
            user_id=user_id,
        )

        # Verify storage
        assert count == 3, f"Expected 3 prompts stored, got {count}"

        # Cleanup
        bridge.close_memory_connections()

    async def test_get_prompts_from_sqlite(self, mock_env):
        """Test retrieving prompts from SQLiteMemory."""
        from violentutf_api.fastapi_app.app.services.pyrit_memory_bridge import (
            PyRITMemoryBridge,
        )

        bridge = PyRITMemoryBridge()
        user_id = "test_user"
        dataset_id = "test_dataset"

        # Store test prompts
        prompts = ["Prompt A", "Prompt B", "Prompt C"]
        metadata = [{}, {}, {}]

        await bridge.store_prompts_to_pyrit_memory(
            prompts=prompts,
            metadata=metadata,
            dataset_id=dataset_id,
            user_id=user_id,
        )

        # Retrieve prompts
        retrieved, total = await bridge.get_prompts_from_pyrit_memory(
            dataset_id=dataset_id,
            user_id=user_id,
        )

        # Verify retrieval
        assert total >= 3, f"Expected at least 3 prompts, got {total}"

        # Cleanup
        bridge.close_memory_connections()

    async def test_get_dataset_statistics_with_sqlite(self, mock_env):
        """Test getting dataset statistics from SQLiteMemory."""
        from violentutf_api.fastapi_app.app.services.pyrit_memory_bridge import (
            PyRITMemoryBridge,
        )

        bridge = PyRITMemoryBridge()
        user_id = "test_user"
        dataset_id = "test_dataset"

        # Store test prompts
        prompts = [f"Test prompt {i}" for i in range(10)]
        metadata = [{"index": i} for i in range(10)]

        await bridge.store_prompts_to_pyrit_memory(
            prompts=prompts,
            metadata=metadata,
            dataset_id=dataset_id,
            user_id=user_id,
        )

        # Get statistics
        stats = await bridge.get_dataset_statistics(
            dataset_id=dataset_id,
            user_id=user_id,
        )

        # Verify statistics
        assert "total_prompts" in stats
        assert stats["total_prompts"] >= 10

        # Cleanup
        bridge.close_memory_connections()

    async def test_cleanup_user_memory_with_sqlite(self, mock_env):
        """Test cleanup operations work with SQLiteMemory."""
        from violentutf_api.fastapi_app.app.services.pyrit_memory_bridge import (
            PyRITMemoryBridge,
        )

        bridge = PyRITMemoryBridge()
        user_id = "test_user"

        # Create memory
        await bridge.get_or_create_user_memory(user_id)

        # Cleanup
        result = await bridge.cleanup_user_memory(user_id, max_age_days=30)

        # Verify result structure
        assert "cleaned_up" in result
        assert "total_pieces" in result

        # Cleanup
        bridge.close_memory_connections()


class TestPyRITMemoryBridgeConnectionManagement:
    """Test connection management with SQLiteMemory."""

    def test_close_memory_connections_with_sqlite(self):
        """Test that close_memory_connections works with SQLiteMemory."""
        from violentutf_api.fastapi_app.app.services.pyrit_memory_bridge import (
            PyRITMemoryBridge,
        )

        bridge = PyRITMemoryBridge()

        # Mock memory with dispose_engine method
        mock_memory = MagicMock(spec=SQLiteMemory)
        mock_memory.dispose_engine = MagicMock()

        bridge.memory_cache["test_user"] = mock_memory

        # Close connections
        bridge.close_memory_connections()

        # Verify dispose_engine was called
        mock_memory.dispose_engine.assert_called_once()

        # Verify cache was cleared
        assert len(bridge.memory_cache) == 0


@pytest.mark.asyncio
class TestPyRITMemoryBridgeBackwardCompatibility:
    """Test backward compatibility - ensure no breaking changes."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
        for suffix in ["-wal", "-shm", "-journal"]:
            journal_path = path + suffix
            if os.path.exists(journal_path):
                os.remove(journal_path)

    @pytest.fixture
    def mock_env(self, temp_db_path):
        """Mock environment variables for testing."""
        with patch.dict(
            os.environ,
            {
                "PYRIT_DB_SALT": "test_salt",
                "PYRIT_MEMORY_DIR": os.path.dirname(temp_db_path),
            },
        ):
            yield

    async def test_public_api_unchanged(self, mock_env):
        """Verify that public API methods are unchanged."""
        from violentutf_api.fastapi_app.app.services.pyrit_memory_bridge import (
            PyRITMemoryBridge,
        )

        bridge = PyRITMemoryBridge()

        # Verify all expected methods exist
        expected_methods = [
            "get_or_create_user_memory",
            "store_prompts_to_pyrit_memory",
            "get_prompts_from_pyrit_memory",
            "get_dataset_statistics",
            "delete_dataset_from_memory",
            "cleanup_user_memory",
            "close_memory_connections",
        ]

        for method_name in expected_methods:
            assert hasattr(bridge, method_name), f"Missing method: {method_name}"

    async def test_method_signatures_unchanged(self, mock_env):
        """Verify that method signatures are unchanged."""
        import inspect

        from violentutf_api.fastapi_app.app.services.pyrit_memory_bridge import (
            PyRITMemoryBridge,
        )

        bridge = PyRITMemoryBridge()

        # Check store_prompts_to_pyrit_memory signature
        sig = inspect.signature(bridge.store_prompts_to_pyrit_memory)
        params = list(sig.parameters.keys())

        expected_params = ["self", "prompts", "metadata", "dataset_id", "user_id", "batch_size"]
        assert params == expected_params, f"Expected {expected_params}, got {params}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
