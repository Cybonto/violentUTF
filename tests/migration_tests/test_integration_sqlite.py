# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Integration Tests for SQLite Migration - Issue #327.

Tests full API workflows with SQLite backend including:
- Generator lifecycle (create → test → update → delete)
- Dataset lifecycle (import → query → delete)
- Scorer operations
- Converter operations
- Session management
- Concurrent access patterns

Requires running services: FastAPI backend, APISIX gateway.
"""

import asyncio
import os
import tempfile
from typing import Any, Dict, List
from uuid import uuid4

import pytest
from httpx import AsyncClient

# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:9080")
TEST_USER_TOKEN = os.getenv("TEST_USER_TOKEN", "test-token")


@pytest.fixture
def test_headers():
    """Common headers for API requests."""
    return {
        "Authorization": f"Bearer {TEST_USER_TOKEN}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def test_user_id():
    """Generate a unique test user ID."""
    return f"test_user_{uuid4().hex[:8]}"


class TestGeneratorWorkflow:
    """Test complete generator lifecycle."""

    @pytest.mark.asyncio
    async def test_full_generator_workflow(self, test_headers, test_user_id):
        """Test: create → get → update → list → delete generator."""
        async with AsyncClient(base_url=API_BASE_URL) as client:
            # 1. Create generator
            create_payload = {
                "name": f"test_generator_{uuid4().hex[:8]}",
                "type": "openai",
                "parameters": {
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 100,
                },
            }

            response = await client.post(
                "/api/v1/generators",
                json=create_payload,
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code in [200, 201], f"Create failed: {response.text}"
            gen_data = response.json()
            gen_id = gen_data.get("id") or gen_data.get("generator_id")
            assert gen_id is not None

            # 2. Get generator by ID
            response = await client.get(
                f"/api/v1/generators/{gen_id}",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code == 200
            retrieved = response.json()
            assert retrieved["name"] == create_payload["name"]
            assert retrieved["type"] == create_payload["type"]

            # 3. Update generator
            update_payload = {
                "parameters": {
                    "model": "gpt-4",
                    "temperature": 0.9,  # Changed
                    "max_tokens": 150,  # Changed
                },
            }

            response = await client.put(
                f"/api/v1/generators/{gen_id}",
                json=update_payload,
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code == 200

            # 4. List generators (should include ours)
            response = await client.get(
                "/api/v1/generators",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code == 200
            generators = response.json()
            assert any(g.get("id") == gen_id or g.get("generator_id") == gen_id for g in generators)

            # 5. Delete generator
            response = await client.delete(
                f"/api/v1/generators/{gen_id}",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code in [200, 204]

            # 6. Verify deletion
            response = await client.get(
                f"/api/v1/generators/{gen_id}",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_generator_user_isolation(self, test_headers):
        """Test that different users cannot access each other's generators."""
        user1_id = f"user1_{uuid4().hex[:8]}"
        user2_id = f"user2_{uuid4().hex[:8]}"

        async with AsyncClient(base_url=API_BASE_URL) as client:
            # User 1 creates a generator
            create_payload = {
                "name": f"user1_gen_{uuid4().hex[:8]}",
                "type": "openai",
                "parameters": {"model": "gpt-4"},
            }

            response = await client.post(
                "/api/v1/generators",
                json=create_payload,
                headers={**test_headers, "X-User-ID": user1_id},
            )
            assert response.status_code in [200, 201]
            gen_data = response.json()
            gen_id = gen_data.get("id") or gen_data.get("generator_id")

            # User 2 tries to access it
            response = await client.get(
                f"/api/v1/generators/{gen_id}",
                headers={**test_headers, "X-User-ID": user2_id},
            )
            # Should not be found (404) or forbidden (403)
            assert response.status_code in [403, 404]

            # Cleanup
            await client.delete(
                f"/api/v1/generators/{gen_id}",
                headers={**test_headers, "X-User-ID": user1_id},
            )


class TestDatasetWorkflow:
    """Test complete dataset lifecycle."""

    @pytest.mark.asyncio
    async def test_full_dataset_workflow(self, test_headers, test_user_id):
        """Test: import → query → get stats → delete dataset."""
        async with AsyncClient(base_url=API_BASE_URL) as client:
            # 1. Import dataset
            dataset_name = f"test_dataset_{uuid4().hex[:8]}"
            import_payload = {
                "name": dataset_name,
                "prompts": [
                    "Test prompt 1",
                    "Test prompt 2",
                    "Test prompt 3",
                ],
                "metadata": [
                    {"index": 0},
                    {"index": 1},
                    {"index": 2},
                ],
            }

            response = await client.post(
                "/api/v1/datasets/import",
                json=import_payload,
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code in [200, 201], f"Import failed: {response.text}"
            dataset_data = response.json()
            dataset_id = dataset_data.get("id") or dataset_data.get("dataset_id")
            assert dataset_id is not None

            # 2. Query dataset prompts
            response = await client.get(
                f"/api/v1/datasets/{dataset_id}/prompts",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code == 200
            prompts_data = response.json()
            prompts = prompts_data.get("prompts", prompts_data)
            assert len(prompts) >= 3

            # 3. Get dataset statistics
            response = await client.get(
                f"/api/v1/datasets/{dataset_id}/stats",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code == 200
            stats = response.json()
            assert stats.get("total_prompts", 0) >= 3

            # 4. List datasets
            response = await client.get(
                "/api/v1/datasets",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code == 200
            datasets = response.json()
            assert any(d.get("id") == dataset_id or d.get("name") == dataset_name for d in datasets)

            # 5. Delete dataset
            response = await client.delete(
                f"/api/v1/datasets/{dataset_id}",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_dataset_pagination(self, test_headers, test_user_id):
        """Test dataset query with pagination."""
        async with AsyncClient(base_url=API_BASE_URL) as client:
            # Import dataset with many prompts
            prompts = [f"Prompt {i}" for i in range(50)]
            import_payload = {
                "name": f"paginated_dataset_{uuid4().hex[:8]}",
                "prompts": prompts,
                "metadata": [{} for _ in prompts],
            }

            response = await client.post(
                "/api/v1/datasets/import",
                json=import_payload,
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code in [200, 201]
            dataset_data = response.json()
            dataset_id = dataset_data.get("id") or dataset_data.get("dataset_id")

            # Query first page
            response = await client.get(
                f"/api/v1/datasets/{dataset_id}/prompts?offset=0&limit=20",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code == 200
            page1 = response.json()
            prompts_page1 = page1.get("prompts", page1)
            assert len(prompts_page1) <= 20

            # Query second page
            response = await client.get(
                f"/api/v1/datasets/{dataset_id}/prompts?offset=20&limit=20",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code == 200
            page2 = response.json()
            prompts_page2 = page2.get("prompts", page2)
            assert len(prompts_page2) <= 20

            # Cleanup
            await client.delete(
                f"/api/v1/datasets/{dataset_id}",
                headers={**test_headers, "X-User-ID": test_user_id},
            )


class TestConverterWorkflow:
    """Test converter operations."""

    @pytest.mark.asyncio
    async def test_create_and_list_converters(self, test_headers, test_user_id):
        """Test creating and listing converters."""
        async with AsyncClient(base_url=API_BASE_URL) as client:
            # Create converter
            create_payload = {
                "name": f"test_converter_{uuid4().hex[:8]}",
                "type": "base64",
                "parameters": {},
            }

            response = await client.post(
                "/api/v1/converters",
                json=create_payload,
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code in [200, 201]
            conv_data = response.json()
            conv_id = conv_data.get("id") or conv_data.get("converter_id")

            # List converters
            response = await client.get(
                "/api/v1/converters",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code == 200
            converters = response.json()
            assert any(c.get("id") == conv_id for c in converters)

            # Delete converter
            response = await client.delete(
                f"/api/v1/converters/{conv_id}",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code in [200, 204]


class TestScorerWorkflow:
    """Test scorer operations."""

    @pytest.mark.asyncio
    async def test_create_and_list_scorers(self, test_headers, test_user_id):
        """Test creating and listing scorers."""
        async with AsyncClient(base_url=API_BASE_URL) as client:
            # Create scorer
            create_payload = {
                "name": f"test_scorer_{uuid4().hex[:8]}",
                "type": "sentiment",
                "parameters": {},
            }

            response = await client.post(
                "/api/v1/scorers",
                json=create_payload,
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code in [200, 201]
            scorer_data = response.json()
            scorer_id = scorer_data.get("id") or scorer_data.get("scorer_id")

            # List scorers
            response = await client.get(
                "/api/v1/scorers",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code == 200
            scorers = response.json()
            assert any(s.get("id") == scorer_id for s in scorers)

            # Delete scorer
            response = await client.delete(
                f"/api/v1/scorers/{scorer_id}",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code in [200, 204]


class TestSessionWorkflow:
    """Test session management."""

    @pytest.mark.asyncio
    async def test_save_and_retrieve_session(self, test_headers, test_user_id):
        """Test saving and retrieving user sessions."""
        async with AsyncClient(base_url=API_BASE_URL) as client:
            # Save session
            session_payload = {
                "session_id": f"session_{uuid4().hex[:8]}",
                "session_data": {
                    "test_key": "test_value",
                    "timestamp": "2025-01-01T00:00:00Z",
                },
            }

            response = await client.post(
                "/api/v1/sessions",
                json=session_payload,
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code in [200, 201]

            # Retrieve session
            session_id = session_payload["session_id"]
            response = await client.get(
                f"/api/v1/sessions/{session_id}",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code == 200
            session = response.json()
            assert session["session_id"] == session_id
            assert session["session_data"]["test_key"] == "test_value"


class TestConcurrentAccess:
    """Test concurrent access patterns."""

    @pytest.mark.asyncio
    async def test_concurrent_generator_creation(self, test_headers, test_user_id):
        """Test multiple users creating generators concurrently."""
        async with AsyncClient(base_url=API_BASE_URL) as client:

            async def create_generator(user_suffix: int):
                """Create a generator for a user."""
                user_id = f"{test_user_id}_{user_suffix}"
                payload = {
                    "name": f"concurrent_gen_{user_suffix}_{uuid4().hex[:4]}",
                    "type": "openai",
                    "parameters": {"model": "gpt-4"},
                }

                response = await client.post(
                    "/api/v1/generators",
                    json=payload,
                    headers={**test_headers, "X-User-ID": user_id},
                )
                return response.status_code, user_id, response.json()

            # Create 10 generators concurrently
            tasks = [create_generator(i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all succeeded
            successful = sum(1 for r in results if not isinstance(r, Exception) and r[0] in [200, 201])
            assert successful >= 8, f"Only {successful}/10 concurrent creates succeeded"

    @pytest.mark.asyncio
    async def test_concurrent_dataset_imports(self, test_headers, test_user_id):
        """Test multiple users importing datasets concurrently."""
        async with AsyncClient(base_url=API_BASE_URL) as client:

            async def import_dataset(user_suffix: int):
                """Import a dataset for a user."""
                user_id = f"{test_user_id}_{user_suffix}"
                payload = {
                    "name": f"concurrent_dataset_{user_suffix}",
                    "prompts": [f"Prompt {i}" for i in range(100)],
                    "metadata": [{} for _ in range(100)],
                }

                response = await client.post(
                    "/api/v1/datasets/import",
                    json=payload,
                    headers={**test_headers, "X-User-ID": user_id},
                )
                return response.status_code, user_id

            # Import 5 datasets concurrently
            tasks = [import_dataset(i) for i in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all succeeded
            successful = sum(1 for r in results if not isinstance(r, Exception) and r[0] in [200, 201])
            assert successful >= 4, f"Only {successful}/5 concurrent imports succeeded"

    @pytest.mark.asyncio
    async def test_no_database_locks(self, test_headers, test_user_id):
        """Test that concurrent operations don't cause database locks."""
        async with AsyncClient(base_url=API_BASE_URL) as client:

            async def mixed_operations(op_id: int):
                """Perform mixed read/write operations."""
                # Create
                create_resp = await client.post(
                    "/api/v1/generators",
                    json={
                        "name": f"lock_test_{op_id}",
                        "type": "openai",
                        "parameters": {},
                    },
                    headers={**test_headers, "X-User-ID": test_user_id},
                )

                # List
                list_resp = await client.get(
                    "/api/v1/generators",
                    headers={**test_headers, "X-User-ID": test_user_id},
                )

                return create_resp.status_code, list_resp.status_code

            # Run 20 mixed operations concurrently
            tasks = [mixed_operations(i) for i in range(20)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for database lock errors or exceptions
            errors = [r for r in results if isinstance(r, Exception)]
            assert len(errors) == 0, f"Database lock errors occurred: {errors}"

            # Verify most operations succeeded
            successful = sum(1 for r in results if not isinstance(r, Exception) and all(s in [200, 201] for s in r))
            assert successful >= 15, f"Only {successful}/20 operations succeeded"


class TestErrorHandling:
    """Test API error handling with SQLite backend."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_generator(self, test_headers, test_user_id):
        """Test getting a generator that doesn't exist."""
        async with AsyncClient(base_url=API_BASE_URL) as client:
            response = await client.get(
                f"/api/v1/generators/{uuid4()}",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_dataset(self, test_headers, test_user_id):
        """Test deleting a dataset that doesn't exist."""
        async with AsyncClient(base_url=API_BASE_URL) as client:
            response = await client.delete(
                f"/api/v1/datasets/{uuid4()}",
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            # Should be idempotent (200/204) or 404
            assert response.status_code in [200, 204, 404]

    @pytest.mark.asyncio
    async def test_invalid_payload(self, test_headers, test_user_id):
        """Test creating generator with invalid payload."""
        async with AsyncClient(base_url=API_BASE_URL) as client:
            # Missing required fields
            response = await client.post(
                "/api/v1/generators",
                json={"invalid": "data"},
                headers={**test_headers, "X-User-ID": test_user_id},
            )
            assert response.status_code in [400, 422]  # Bad request or validation error
