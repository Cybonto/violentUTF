#!/usr/bin/env python3
"""
Test module for Issue #280: Asset Management Database System - API Tests

This module contains comprehensive integration tests for the asset management API endpoints
following Test-Driven Development (TDD) principles.
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'violentutf_api', 'fastapi_app'))

from main import app

from app.models.asset_inventory import (
    AssetType,
    CriticalityLevel,
    DatabaseAsset,
    Environment,
    SecurityClassification,
    ValidationStatus,
)


class TestAssetCRUDAPI:
    """Test cases for Asset CRUD API endpoints."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    async def async_client(self) -> AsyncClient:
        """Create async test client."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        """Provide authentication headers for testing."""
        # Mock JWT token - in real implementation, would get from auth system
        return {
            "Authorization": "Bearer mock_jwt_token",
            "Content-Type": "application/json"
        }

    @pytest.fixture
    def valid_asset_payload(self) -> Dict[str, Any]:
        """Provide valid asset creation payload."""
        return {
            "name": "Test PostgreSQL Database",
            "asset_type": "POSTGRESQL",
            "unique_identifier": "test-postgres-01",
            "location": "test-server.company.com",
            "connection_string": "postgresql://user:pass@test-server:5432/testdb",
            "network_location": "10.0.1.50:5432",
            "security_classification": "INTERNAL",
            "criticality_level": "MEDIUM",
            "environment": "DEVELOPMENT",
            "encryption_enabled": True,
            "access_restricted": True,
            "database_version": "13.7",
            "estimated_size_mb": 512,
            "table_count": 10,
            "owner_team": "Engineering",
            "technical_contact": "engineer@company.com",
            "business_contact": "product@company.com",
            "purpose_description": "Development database for testing",
            "discovery_method": "manual_registration",
            "confidence_score": 100,
            "backup_configured": False,
            "compliance_requirements": {
                "gdpr": False,
                "soc2": True
            },
            "documentation_url": "https://wiki.company.com/test-db"
        }

    @pytest.mark.asyncio
    async def test_create_asset_success(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        valid_asset_payload: Dict[str, Any],
    ) -> None:
        """Test successful asset creation via API."""
        response = await async_client.post(
            "/api/v1/assets/",
            json=valid_asset_payload,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        # Verify response structure
        assert "id" in data
        assert data["name"] == valid_asset_payload["name"]
        assert data["asset_type"] == valid_asset_payload["asset_type"]
        assert data["unique_identifier"] == valid_asset_payload["unique_identifier"]
        assert data["security_classification"] == valid_asset_payload["security_classification"]
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_create_asset_validation_error(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
    ) -> None:
        """Test asset creation with validation errors."""
        invalid_payload = {
            "name": "A",  # Too short
            "asset_type": "INVALID_TYPE",  # Invalid enum
            "unique_identifier": "",  # Empty identifier
            "security_classification": "RESTRICTED",
            "encryption_enabled": False,  # Should require encryption for restricted
            "confidence_score": 150  # Out of valid range
        }
        
        response = await async_client.post(
            "/api/v1/assets/",
            json=invalid_payload,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_data = response.json()
        assert "detail" in error_data

    @pytest.mark.asyncio
    async def test_create_asset_duplicate_identifier(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        valid_asset_payload: Dict[str, Any],
    ) -> None:
        """Test asset creation with duplicate identifier."""
        # Create first asset
        response1 = await async_client.post(
            "/api/v1/assets/",
            json=valid_asset_payload,
            headers=auth_headers
        )
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Try to create second asset with same identifier
        response2 = await async_client.post(
            "/api/v1/assets/",
            json=valid_asset_payload,
            headers=auth_headers
        )
        
        assert response2.status_code == status.HTTP_409_CONFLICT
        error_data = response2.json()
        assert "duplicate" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_asset_by_id_success(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        valid_asset_payload: Dict[str, Any],
    ) -> None:
        """Test retrieving asset by ID."""
        # Create asset first
        create_response = await async_client.post(
            "/api/v1/assets/",
            json=valid_asset_payload,
            headers=auth_headers
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        asset_id = create_response.json()["id"]
        
        # Get asset by ID
        response = await async_client.get(
            f"/api/v1/assets/{asset_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == asset_id
        assert data["name"] == valid_asset_payload["name"]

    @pytest.mark.asyncio
    async def test_get_asset_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
    ) -> None:
        """Test retrieving non-existent asset."""
        non_existent_id = str(uuid.uuid4())
        
        response = await async_client.get(
            f"/api/v1/assets/{non_existent_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_list_assets_success(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        valid_asset_payload: Dict[str, Any],
    ) -> None:
        """Test listing assets with pagination."""
        # Create multiple assets
        for i in range(3):
            payload = valid_asset_payload.copy()
            payload["unique_identifier"] = f"test-asset-{i}"
            payload["name"] = f"Test Asset {i}"
            
            response = await async_client.post(
                "/api/v1/assets/",
                json=payload,
                headers=auth_headers
            )
            assert response.status_code == status.HTTP_201_CREATED
        
        # List assets
        response = await async_client.get(
            "/api/v1/assets/?skip=0&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    @pytest.mark.asyncio
    async def test_list_assets_with_filters(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        valid_asset_payload: Dict[str, Any],
    ) -> None:
        """Test listing assets with filtering."""
        # Create assets with different types
        postgres_payload = valid_asset_payload.copy()
        postgres_payload["unique_identifier"] = "postgres-asset"
        postgres_payload["asset_type"] = "POSTGRESQL"
        
        sqlite_payload = valid_asset_payload.copy()
        sqlite_payload["unique_identifier"] = "sqlite-asset"
        sqlite_payload["asset_type"] = "SQLITE"
        
        await async_client.post("/api/v1/assets/", json=postgres_payload, headers=auth_headers)
        await async_client.post("/api/v1/assets/", json=sqlite_payload, headers=auth_headers)
        
        # Filter by asset type
        response = await async_client.get(
            "/api/v1/assets/?asset_type=POSTGRESQL",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(asset["asset_type"] == "POSTGRESQL" for asset in data)

    @pytest.mark.asyncio
    async def test_update_asset_success(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        valid_asset_payload: Dict[str, Any],
    ) -> None:
        """Test successful asset update."""
        # Create asset first
        create_response = await async_client.post(
            "/api/v1/assets/",
            json=valid_asset_payload,
            headers=auth_headers
        )
        asset_id = create_response.json()["id"]
        
        # Update asset
        update_payload = {
            "name": "Updated Database Name",
            "confidence_score": 95,
            "technical_contact": "updated@company.com"
        }
        
        response = await async_client.put(
            f"/api/v1/assets/{asset_id}",
            json=update_payload,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Database Name"
        assert data["confidence_score"] == 95
        assert data["technical_contact"] == "updated@company.com"

    @pytest.mark.asyncio
    async def test_patch_asset_success(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        valid_asset_payload: Dict[str, Any],
    ) -> None:
        """Test successful partial asset update."""
        # Create asset first
        create_response = await async_client.post(
            "/api/v1/assets/",
            json=valid_asset_payload,
            headers=auth_headers
        )
        asset_id = create_response.json()["id"]
        
        # Patch asset (partial update)
        patch_payload = {
            "confidence_score": 85
        }
        
        response = await async_client.patch(
            f"/api/v1/assets/{asset_id}",
            json=patch_payload,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["confidence_score"] == 85
        # Other fields should remain unchanged
        assert data["name"] == valid_asset_payload["name"]

    @pytest.mark.asyncio
    async def test_delete_asset_success(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        valid_asset_payload: Dict[str, Any],
    ) -> None:
        """Test successful asset deletion (soft delete)."""
        # Create asset first
        create_response = await async_client.post(
            "/api/v1/assets/",
            json=valid_asset_payload,
            headers=auth_headers
        )
        asset_id = create_response.json()["id"]
        
        # Delete asset
        response = await async_client.delete(
            f"/api/v1/assets/{asset_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify asset is not accessible after deletion
        get_response = await async_client.get(
            f"/api/v1/assets/{asset_id}",
            headers=auth_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_api_authentication_required(
        self,
        async_client: AsyncClient,
        valid_asset_payload: Dict[str, Any],
    ) -> None:
        """Test that API endpoints require authentication."""
        # Test without auth headers
        response = await async_client.post(
            "/api/v1/assets/",
            json=valid_asset_payload
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_api_invalid_token(
        self,
        async_client: AsyncClient,
        valid_asset_payload: Dict[str, Any],
    ) -> None:
        """Test API with invalid authentication token."""
        invalid_headers = {
            "Authorization": "Bearer invalid_token",
            "Content-Type": "application/json"
        }
        
        response = await async_client.post(
            "/api/v1/assets/",
            json=valid_asset_payload,
            headers=invalid_headers
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestBulkOperationsAPI:
    """Test cases for Bulk Operations API endpoints."""

    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        """Provide authentication headers for testing."""
        return {
            "Authorization": "Bearer mock_jwt_token",
            "Content-Type": "application/json"
        }

    @pytest.fixture
    def bulk_import_payload(self) -> Dict[str, Any]:
        """Provide bulk import payload for testing."""
        return {
            "source": "discovery_scanner",
            "assets": [
                {
                    "name": "Bulk Asset 1",
                    "asset_type": "POSTGRESQL",
                    "unique_identifier": "bulk-asset-1",
                    "location": "bulk1.company.com",
                    "security_classification": "INTERNAL",
                    "criticality_level": "MEDIUM",
                    "environment": "DEVELOPMENT",
                    "discovery_method": "automated_scan",
                    "confidence_score": 85
                },
                {
                    "name": "Bulk Asset 2",
                    "asset_type": "SQLITE",
                    "unique_identifier": "bulk-asset-2",
                    "location": "/var/lib/data/bulk2.db",
                    "security_classification": "INTERNAL",
                    "criticality_level": "LOW",
                    "environment": "DEVELOPMENT",
                    "discovery_method": "automated_scan",
                    "confidence_score": 80
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_bulk_import_assets_success(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        bulk_import_payload: Dict[str, Any],
    ) -> None:
        """Test successful bulk asset import."""
        response = await async_client.post(
            "/api/v1/assets/bulk-import",
            json=bulk_import_payload,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        
        # Verify response structure
        assert "job_id" in data
        assert data["status"] == "processing"
        assert data["assets_count"] == 2

    @pytest.mark.asyncio
    async def test_bulk_import_status_check(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        bulk_import_payload: Dict[str, Any],
    ) -> None:
        """Test checking bulk import job status."""
        # Start bulk import
        import_response = await async_client.post(
            "/api/v1/assets/bulk-import",
            json=bulk_import_payload,
            headers=auth_headers
        )
        job_id = import_response.json()["job_id"]
        
        # Check job status
        status_response = await async_client.get(
            f"/api/v1/assets/import-status/{job_id}",
            headers=auth_headers
        )
        
        assert status_response.status_code == status.HTTP_200_OK
        status_data = status_response.json()
        assert "job_id" in status_data
        assert "status" in status_data
        assert status_data["job_id"] == job_id

    @pytest.mark.asyncio
    async def test_bulk_validate_batch(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        bulk_import_payload: Dict[str, Any],
    ) -> None:
        """Test bulk validation before import."""
        response = await async_client.post(
            "/api/v1/assets/validate-batch",
            json=bulk_import_payload,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify validation response
        assert "valid_count" in data
        assert "invalid_count" in data
        assert "validation_errors" in data

    @pytest.mark.asyncio
    async def test_bulk_update_assets(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
    ) -> None:
        """Test bulk asset updates."""
        # First create some assets to update
        asset_ids = []
        for i in range(2):
            create_payload = {
                "name": f"Update Test Asset {i}",
                "asset_type": "POSTGRESQL",
                "unique_identifier": f"update-test-{i}",
                "location": f"update{i}.company.com",
                "security_classification": "INTERNAL",
                "criticality_level": "MEDIUM",
                "environment": "DEVELOPMENT",
                "discovery_method": "manual",
                "confidence_score": 80
            }
            
            response = await async_client.post(
                "/api/v1/assets/",
                json=create_payload,
                headers=auth_headers
            )
            asset_ids.append(response.json()["id"])
        
        # Bulk update
        bulk_update_payload = {
            "updates": [
                {
                    "asset_id": asset_ids[0],
                    "fields": {
                        "confidence_score": 95,
                        "technical_contact": "updated@company.com"
                    }
                },
                {
                    "asset_id": asset_ids[1],
                    "fields": {
                        "confidence_score": 90,
                        "backup_configured": True
                    }
                }
            ]
        }
        
        response = await async_client.post(
            "/api/v1/assets/bulk-update",
            json=bulk_update_payload,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED


class TestRelationshipAPI:
    """Test cases for Asset Relationship API endpoints."""

    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        """Provide authentication headers for testing."""
        return {
            "Authorization": "Bearer mock_jwt_token",
            "Content-Type": "application/json"
        }

    @pytest.fixture
    async def sample_assets(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
    ) -> List[str]:
        """Create sample assets for relationship testing."""
        asset_ids = []
        
        for i in range(2):
            payload = {
                "name": f"Relationship Test Asset {i}",
                "asset_type": "POSTGRESQL",
                "unique_identifier": f"rel-test-{i}",
                "location": f"rel{i}.company.com",
                "security_classification": "INTERNAL",
                "criticality_level": "MEDIUM",
                "environment": "PRODUCTION",
                "discovery_method": "manual",
                "confidence_score": 90
            }
            
            response = await async_client.post(
                "/api/v1/assets/",
                json=payload,
                headers=auth_headers
            )
            asset_ids.append(response.json()["id"])
        
        return asset_ids

    @pytest.mark.asyncio
    async def test_create_asset_relationship(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        sample_assets: List[str],
    ) -> None:
        """Test creating an asset relationship."""
        source_id, target_id = sample_assets
        
        relationship_payload = {
            "source_asset_id": source_id,
            "target_asset_id": target_id,
            "relationship_type": "DEPENDS_ON",
            "relationship_strength": "STRONG",
            "bidirectional": False,
            "description": "Source depends on target for data",
            "discovered_method": "configuration_analysis",
            "confidence_score": 90
        }
        
        response = await async_client.post(
            "/api/v1/relationships/",
            json=relationship_payload,
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert data["source_asset_id"] == source_id
        assert data["target_asset_id"] == target_id
        assert data["relationship_type"] == "DEPENDS_ON"

    @pytest.mark.asyncio
    async def test_get_asset_relationships(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        sample_assets: List[str],
    ) -> None:
        """Test retrieving relationships for a specific asset."""
        source_id, target_id = sample_assets
        
        # Create relationship first
        relationship_payload = {
            "source_asset_id": source_id,
            "target_asset_id": target_id,
            "relationship_type": "CONNECTED_TO",
            "relationship_strength": "MEDIUM",
            "discovered_method": "network_analysis",
            "confidence_score": 85
        }
        
        await async_client.post(
            "/api/v1/relationships/",
            json=relationship_payload,
            headers=auth_headers
        )
        
        # Get relationships for source asset
        response = await async_client.get(
            f"/api/v1/assets/{source_id}/relationships",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_get_relationship_graph(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        sample_assets: List[str],
    ) -> None:
        """Test retrieving relationship graph."""
        source_id, target_id = sample_assets
        
        # Create relationship
        relationship_payload = {
            "source_asset_id": source_id,
            "target_asset_id": target_id,
            "relationship_type": "SERVES_DATA_TO",
            "relationship_strength": "CRITICAL",
            "discovered_method": "data_flow_analysis",
            "confidence_score": 95
        }
        
        await async_client.post(
            "/api/v1/relationships/",
            json=relationship_payload,
            headers=auth_headers
        )
        
        # Get relationship graph
        response = await async_client.get(
            f"/api/v1/relationships/graph?asset_ids={source_id}&max_depth=2",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify graph structure
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) >= 2
        assert len(data["edges"]) >= 1

    @pytest.mark.asyncio
    async def test_delete_relationship(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
        sample_assets: List[str],
    ) -> None:
        """Test deleting an asset relationship."""
        source_id, target_id = sample_assets
        
        # Create relationship first
        relationship_payload = {
            "source_asset_id": source_id,
            "target_asset_id": target_id,
            "relationship_type": "BACKED_UP_TO",
            "relationship_strength": "WEAK",
            "discovered_method": "backup_configuration",
            "confidence_score": 75
        }
        
        create_response = await async_client.post(
            "/api/v1/relationships/",
            json=relationship_payload,
            headers=auth_headers
        )
        relationship_id = create_response.json()["id"]
        
        # Delete relationship
        response = await async_client.delete(
            f"/api/v1/relationships/{relationship_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestAPIPerformance:
    """Test cases for API performance requirements."""

    @pytest.fixture
    def auth_headers(self) -> Dict[str, str]:
        """Provide authentication headers for testing."""
        return {
            "Authorization": "Bearer mock_jwt_token",
            "Content-Type": "application/json"
        }

    @pytest.mark.asyncio
    async def test_api_response_time_under_500ms(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
    ) -> None:
        """Test that API responses are under 500ms."""
        import time

        # Test GET /assets/ endpoint
        start_time = time.time()
        response = await async_client.get(
            "/api/v1/assets/?limit=10",
            headers=auth_headers
        )
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        assert response.status_code == status.HTTP_200_OK
        assert response_time_ms < 500, f"Response time {response_time_ms}ms exceeds 500ms limit"

    @pytest.mark.asyncio
    async def test_api_concurrent_requests(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
    ) -> None:
        """Test API handling of concurrent requests."""
        import asyncio

        # Create multiple concurrent requests
        tasks = []
        for i in range(10):
            task = async_client.get(
                "/api/v1/assets/",
                headers=auth_headers
            )
            tasks.append(task)
        
        # Execute concurrently
        responses = await asyncio.gather(*tasks)
        
        # Verify all requests succeeded
        for response in responses:
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_large_dataset_pagination_performance(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str],
    ) -> None:
        """Test pagination performance with large datasets."""
        import time

        # Test large limit (simulating large dataset pagination)
        start_time = time.time()
        response = await async_client.get(
            "/api/v1/assets/?limit=1000&skip=0",
            headers=auth_headers
        )
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        assert response.status_code == status.HTTP_200_OK
        assert response_time_ms < 1000, f"Large pagination response time {response_time_ms}ms exceeds 1000ms limit"


if __name__ == "__main__":
    pytest.main([__file__])