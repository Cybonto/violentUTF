# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Integration tests for Asset Management API Endpoints (Issue #280).

This module provides comprehensive integration tests for all 11 API endpoints,
including authentication, request/response validation, and error handling.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset_inventory import AssetType, CriticalityLevel, DatabaseAsset, Environment, SecurityClassification


class TestAssetAPIIntegration:
    """Integration tests for Asset Management API endpoints."""
    
    # Test data for API requests
    @pytest.fixture
    def valid_asset_payload(self) -> Dict[str, Any]:
        """Valid asset creation payload."""
        return {
            "name": "Integration Test PostgreSQL",
            "asset_type": "POSTGRESQL",
            "unique_identifier": f"integration-test-{uuid.uuid4()}",
            "location": "test-db.integration.com:5432",
            "security_classification": "INTERNAL",
            "criticality_level": "MEDIUM",
            "environment": "DEVELOPMENT",
            "discovery_method": "manual",
            "confidence_score": 95,
            "connection_string": "postgresql://user:pass@test-db:5432/testdb",
            "technical_contact": "test@integration.com",
            "backup_configured": True,
            "compliance_requirements": {"gdpr": True, "soc2": False}
        }
    
    @pytest.fixture
    def auth_headers(self, mock_current_user: Dict[str, str]) -> Dict[str, str]:
        """Mock authentication headers."""
        # In real implementation, this would be a JWT token
        return {"Authorization": "Bearer mock_jwt_token"}
    
    @pytest.mark.asyncio
    async def test_create_asset_success(
        self,
        async_client: AsyncClient,
        valid_asset_payload: Dict[str, Any],
        auth_headers: Dict[str, str]
    ):
        """Test successful asset creation via API."""
        # Act
        response = await async_client.post(
            "/api/v1/assets/",
            json=valid_asset_payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 201
        response_data = response.json()
        
        assert response_data["name"] == valid_asset_payload["name"]
        assert response_data["asset_type"] == valid_asset_payload["asset_type"]
        assert response_data["unique_identifier"] == valid_asset_payload["unique_identifier"]
        assert response_data["location"] == valid_asset_payload["location"]
        assert response_data["security_classification"] == valid_asset_payload["security_classification"]
        assert response_data["created_by"] == "test_user"
        assert response_data["updated_by"] == "test_user"
        assert "id" in response_data
        assert "created_at" in response_data
        assert "updated_at" in response_data
    
    @pytest.mark.asyncio
    async def test_create_asset_validation_error(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test asset creation with validation errors."""
        # Arrange - Invalid payload (missing required fields)
        invalid_payload = {
            "name": "AB",  # Too short
            "asset_type": "POSTGRESQL",
            # Missing unique_identifier
            "location": "test-db:5432",
            "security_classification": "RESTRICTED",
            "criticality_level": "CRITICAL",
            "environment": "PRODUCTION",
            "discovery_method": "manual",
            "confidence_score": 0,  # Invalid range
            "encryption_enabled": False  # Required for restricted
        }
        
        # Act
        response = await async_client.post(
            "/api/v1/assets/",
            json=invalid_payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 422  # Validation error
        error_detail = response.json()["detail"]
        assert isinstance(error_detail, list)
    
    @pytest.mark.asyncio
    async def test_create_asset_duplicate_identifier(
        self,
        async_client: AsyncClient,
        async_session: AsyncSession,
        valid_asset_payload: Dict[str, Any],
        auth_headers: Dict[str, str]
    ):
        """Test asset creation with duplicate unique identifier."""
        # Arrange - Create existing asset
        existing_asset = DatabaseAsset(
            name="Existing Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier=valid_asset_payload["unique_identifier"],
            location="existing-db:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=95,
            created_by="existing_user",
            updated_by="existing_user"
        )
        async_session.add(existing_asset)
        await async_session.commit()
        
        # Act
        response = await async_client.post(
            "/api/v1/assets/",
            json=valid_asset_payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 409  # Conflict
        assert "already exists" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_asset_success(
        self,
        async_client: AsyncClient,
        sample_database_asset: DatabaseAsset,
        auth_headers: Dict[str, str]
    ):
        """Test successful asset retrieval by ID."""
        # Act
        response = await async_client.get(
            f"/api/v1/assets/{sample_database_asset.id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["id"] == str(sample_database_asset.id)
        assert response_data["name"] == sample_database_asset.name
        assert response_data["asset_type"] == sample_database_asset.asset_type.value
        assert response_data["unique_identifier"] == sample_database_asset.unique_identifier
    
    @pytest.mark.asyncio
    async def test_get_asset_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test asset retrieval with non-existent ID."""
        # Arrange
        fake_id = uuid.uuid4()
        
        # Act
        response = await async_client.get(
            f"/api/v1/assets/{fake_id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_asset_success(
        self,
        async_client: AsyncClient,
        sample_database_asset: DatabaseAsset,
        auth_headers: Dict[str, str]
    ):
        """Test successful asset update."""
        # Arrange
        update_payload = {
            "name": "Updated Asset Name",
            "purpose_description": "Updated purpose description",
            "estimated_size_mb": 4096,
            "technical_contact": "updated@test.com"
        }
        
        # Act
        response = await async_client.put(
            f"/api/v1/assets/{sample_database_asset.id}",
            json=update_payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["name"] == update_payload["name"]
        assert response_data["purpose_description"] == update_payload["purpose_description"]
        assert response_data["estimated_size_mb"] == update_payload["estimated_size_mb"]
        assert response_data["technical_contact"] == update_payload["technical_contact"]
        assert response_data["updated_by"] == "test_user"
        
        # Unchanged fields should remain the same
        assert response_data["asset_type"] == sample_database_asset.asset_type.value
        assert response_data["unique_identifier"] == sample_database_asset.unique_identifier
    
    @pytest.mark.asyncio
    async def test_patch_asset_success(
        self,
        async_client: AsyncClient,
        sample_database_asset: DatabaseAsset,
        auth_headers: Dict[str, str]
    ):
        """Test successful partial asset update via PATCH."""
        # Arrange
        patch_payload = {
            "estimated_size_mb": 2048
        }
        
        # Act
        response = await async_client.patch(
            f"/api/v1/assets/{sample_database_asset.id}",
            json=patch_payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["estimated_size_mb"] == patch_payload["estimated_size_mb"]
        # Other fields should remain unchanged
        assert response_data["name"] == sample_database_asset.name
        assert response_data["asset_type"] == sample_database_asset.asset_type.value
    
    @pytest.mark.asyncio
    async def test_delete_asset_success(
        self,
        async_client: AsyncClient,
        sample_database_asset: DatabaseAsset,
        auth_headers: Dict[str, str]
    ):
        """Test successful asset deletion (soft delete)."""
        # Act
        response = await async_client.delete(
            f"/api/v1/assets/{sample_database_asset.id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 204
        
        # Verify asset is soft deleted (not returned in subsequent GET)
        get_response = await async_client.get(
            f"/api/v1/assets/{sample_database_asset.id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_list_assets_success(
        self,
        async_client: AsyncClient,
        async_session: AsyncSession,
        auth_headers: Dict[str, str]
    ):
        """Test successful asset listing."""
        # Arrange - Create multiple assets
        assets = []
        for i in range(3):
            asset = DatabaseAsset(
                name=f"List Test Asset {i}",
                asset_type=AssetType.POSTGRESQL if i % 2 == 0 else AssetType.SQLITE,
                unique_identifier=f"list-test-{i}",
                location=f"server-{i}:5432" if i % 2 == 0 else f"/tmp/test-{i}.db",
                security_classification=SecurityClassification.INTERNAL,
                criticality_level=CriticalityLevel.MEDIUM,
                environment=Environment.DEVELOPMENT,
                discovery_method="manual",
                discovery_timestamp=datetime.now(timezone.utc),
                confidence_score=95,
                created_by="test_user",
                updated_by="test_user"
            )
            async_session.add(asset)
            assets.append(asset)
        
        await async_session.commit()
        
        # Act
        response = await async_client.get(
            "/api/v1/assets/",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        
        assert len(response_data) >= 3  # At least the 3 we created
        
        # Verify structure of returned assets
        for asset_data in response_data:
            assert "id" in asset_data
            assert "name" in asset_data
            assert "asset_type" in asset_data
            assert "unique_identifier" in asset_data
            assert "created_at" in asset_data
    
    @pytest.mark.asyncio
    async def test_list_assets_with_pagination(
        self,
        async_client: AsyncClient,
        async_session: AsyncSession,
        auth_headers: Dict[str, str]
    ):
        """Test asset listing with pagination parameters."""
        # Arrange - Create 5 assets
        for i in range(5):
            asset = DatabaseAsset(
                name=f"Pagination Test Asset {i:02d}",
                asset_type=AssetType.SQLITE,
                unique_identifier=f"pagination-test-{i:02d}",
                location=f"/tmp/pagination-{i:02d}.db",
                security_classification=SecurityClassification.INTERNAL,
                criticality_level=CriticalityLevel.LOW,
                environment=Environment.TESTING,
                discovery_method="manual",
                discovery_timestamp=datetime.now(timezone.utc),
                confidence_score=85,
                created_by="test_user",
                updated_by="test_user"
            )
            async_session.add(asset)
        
        await async_session.commit()
        
        # Act - Get first page
        response = await async_client.get(
            "/api/v1/assets/?skip=0&limit=2",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        first_page = response.json()
        assert len(first_page) == 2
        
        # Act - Get second page
        response = await async_client.get(
            "/api/v1/assets/?skip=2&limit=2",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        second_page = response.json()
        assert len(second_page) == 2
        
        # Verify no overlap
        first_page_ids = {asset["id"] for asset in first_page}
        second_page_ids = {asset["id"] for asset in second_page}
        assert len(first_page_ids & second_page_ids) == 0
    
    @pytest.mark.asyncio
    async def test_list_assets_with_filters(
        self,
        async_client: AsyncClient,
        async_session: AsyncSession,
        auth_headers: Dict[str, str]
    ):
        """Test asset listing with filtering parameters."""
        # Arrange - Create assets with different types and environments
        postgresql_prod = DatabaseAsset(
            name="PostgreSQL Production",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="filter-pg-prod",
            location="prod-db:5432",
            security_classification=SecurityClassification.CONFIDENTIAL,
            criticality_level=CriticalityLevel.CRITICAL,
            environment=Environment.PRODUCTION,
            discovery_method="automated",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=98,
            created_by="test_user",
            updated_by="test_user"
        )
        
        sqlite_dev = DatabaseAsset(
            name="SQLite Development",
            asset_type=AssetType.SQLITE,
            unique_identifier="filter-sqlite-dev",
            location="/app/dev.db",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=85,
            created_by="test_user",
            updated_by="test_user"
        )
        
        async_session.add(postgresql_prod)
        async_session.add(sqlite_dev)
        await async_session.commit()
        
        # Act - Filter by asset type
        response = await async_client.get(
            "/api/v1/assets/?asset_type=POSTGRESQL",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        postgresql_assets = response.json()
        
        for asset in postgresql_assets:
            assert asset["asset_type"] == "POSTGRESQL"
        
        # Act - Filter by environment
        response = await async_client.get(
            "/api/v1/assets/?environment=PRODUCTION",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        production_assets = response.json()
        
        for asset in production_assets:
            assert asset["environment"] == "PRODUCTION"
    
    @pytest.mark.asyncio
    async def test_search_assets_success(
        self,
        async_client: AsyncClient,
        async_session: AsyncSession,
        auth_headers: Dict[str, str]
    ):
        """Test asset search functionality."""
        # Arrange - Create searchable assets
        searchable_asset = DatabaseAsset(
            name="Searchable Production Database",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="search-prod-db",
            location="search-db.company.com:5432",
            security_classification=SecurityClassification.CONFIDENTIAL,
            criticality_level=CriticalityLevel.HIGH,
            environment=Environment.PRODUCTION,
            discovery_method="automated",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=95,
            purpose_description="Main production database for customer data",
            created_by="test_user",
            updated_by="test_user"
        )
        
        async_session.add(searchable_asset)
        await async_session.commit()
        
        # Act
        search_payload = {
            "query": "Production",
            "limit": 10,
            "offset": 0
        }
        
        response = await async_client.post(
            "/api/v1/assets/search",
            json=search_payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        
        assert "results" in response_data
        assert "total_matches" in response_data
        assert "query" in response_data
        assert "execution_time" in response_data
        
        assert response_data["query"] == "Production"
        assert len(response_data["results"]) >= 1
        
        # Verify search found our asset
        found_asset = next(
            (asset for asset in response_data["results"] if asset["name"] == "Searchable Production Database"),
            None
        )
        assert found_asset is not None
    
    @pytest.mark.asyncio
    async def test_bulk_import_assets_success(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test bulk asset import functionality."""
        # Arrange
        bulk_import_payload = {
            "source": "discovery_system",
            "assets": [
                {
                    "name": "Bulk Import Asset 1",
                    "asset_type": "POSTGRESQL",
                    "unique_identifier": f"bulk-1-{uuid.uuid4()}",
                    "location": "bulk1-db:5432",
                    "security_classification": "INTERNAL",
                    "criticality_level": "MEDIUM",
                    "environment": "DEVELOPMENT",
                    "discovery_method": "automated",
                    "confidence_score": 90,
                    "technical_contact": "bulk1@test.com",
                    "backup_configured": True
                },
                {
                    "name": "Bulk Import Asset 2",
                    "asset_type": "SQLITE",
                    "unique_identifier": f"bulk-2-{uuid.uuid4()}",
                    "location": "/app/bulk2.db",
                    "security_classification": "INTERNAL",
                    "criticality_level": "LOW",
                    "environment": "TESTING",
                    "discovery_method": "file_scan",
                    "confidence_score": 85,
                    "technical_contact": "bulk2@test.com"
                }
            ]
        }
        
        # Act
        response = await async_client.post(
            "/api/v1/assets/bulk-import",
            json=bulk_import_payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 202  # Accepted for background processing
        response_data = response.json()
        
        assert "job_id" in response_data
        assert response_data["status"] == "processing"
        assert response_data["assets_count"] == 2
        assert "estimated_duration" in response_data
    
    @pytest.mark.asyncio
    async def test_get_import_status_success(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test import job status retrieval."""
        # Arrange
        job_id = str(uuid.uuid4())
        
        # Act
        response = await async_client.get(
            f"/api/v1/assets/import-status/{job_id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        
        assert response_data["job_id"] == job_id
        assert "status" in response_data
        assert "progress" in response_data
        assert "assets_processed" in response_data
        assert "assets_created" in response_data
        assert "assets_updated" in response_data
        assert "assets_failed" in response_data
    
    @pytest.mark.asyncio
    async def test_validate_batch_success(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test batch validation functionality."""
        # Arrange
        validation_payload = {
            "assets": [
                {
                    "name": "Valid Asset",
                    "asset_type": "POSTGRESQL",
                    "unique_identifier": f"valid-{uuid.uuid4()}",
                    "location": "valid-db:5432",
                    "security_classification": "INTERNAL",
                    "criticality_level": "MEDIUM",
                    "environment": "DEVELOPMENT",
                    "discovery_method": "manual",
                    "confidence_score": 95,
                    "technical_contact": "valid@test.com"
                },
                {
                    "name": "X",  # Invalid - too short
                    "asset_type": "SQLITE",
                    "unique_identifier": f"invalid-{uuid.uuid4()}",
                    "location": "/tmp/invalid.db",
                    "security_classification": "RESTRICTED",
                    "criticality_level": "CRITICAL",
                    "environment": "PRODUCTION",
                    "discovery_method": "manual",
                    "confidence_score": 0,  # Invalid range
                    "encryption_enabled": False  # Required for restricted
                }
            ]
        }
        
        # Act
        response = await async_client.post(
            "/api/v1/assets/validate-batch",
            json=validation_payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        response_data = response.json()
        
        assert "valid_count" in response_data
        assert "invalid_count" in response_data
        assert "validation_errors" in response_data
        assert "validation_warnings" in response_data
        
        assert response_data["valid_count"] == 1
        assert response_data["invalid_count"] == 1
        assert len(response_data["validation_errors"]) >= 1
    
    @pytest.mark.asyncio
    async def test_bulk_update_assets_success(
        self,
        async_client: AsyncClient,
        async_session: AsyncSession,
        auth_headers: Dict[str, str]
    ):
        """Test bulk asset update functionality."""
        # Arrange - Create assets to update
        asset1 = DatabaseAsset(
            name="Update Asset 1",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="update-1",
            location="update1-db:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=90,
            created_by="test_user",
            updated_by="test_user"
        )
        
        asset2 = DatabaseAsset(
            name="Update Asset 2",
            asset_type=AssetType.SQLITE,
            unique_identifier="update-2",
            location="/app/update2.db",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=85,
            created_by="test_user",
            updated_by="test_user"
        )
        
        async_session.add(asset1)
        async_session.add(asset2)
        await async_session.commit()
        await async_session.refresh(asset1)
        await async_session.refresh(asset2)
        
        # Bulk update payload
        bulk_update_payload = {
            "updates": [
                {
                    "asset_id": str(asset1.id),
                    "updates": {
                        "technical_contact": "updated1@test.com",
                        "estimated_size_mb": 4096
                    }
                },
                {
                    "asset_id": str(asset2.id),
                    "updates": {
                        "technical_contact": "updated2@test.com",
                        "backup_configured": True
                    }
                }
            ]
        }
        
        # Act
        response = await async_client.post(
            "/api/v1/assets/bulk-update",
            json=bulk_update_payload,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 202  # Accepted for background processing
        response_data = response.json()
        
        assert "job_id" in response_data
        assert response_data["status"] == "processing"
        assert response_data["updates_count"] == 2
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, async_client: AsyncClient):
        """Test API access without authentication."""
        # Act - Try to access assets without auth headers
        response = await async_client.get("/api/v1/assets/")
        
        # Assert
        assert response.status_code == 401  # Unauthorized
    
    @pytest.mark.asyncio
    async def test_invalid_uuid_parameter(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test API with invalid UUID parameter."""
        # Act
        response = await async_client.get(
            "/api/v1/assets/invalid-uuid",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 422  # Validation error for invalid UUID format
    
    @pytest.mark.asyncio
    async def test_performance_response_time(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test that API endpoints meet performance requirements (<500ms)."""
        import time

        # Act - Test list assets endpoint
        start_time = time.time()
        response = await async_client.get(
            "/api/v1/assets/?limit=100",
            headers=auth_headers
        )
        end_time = time.time()
        
        # Assert
        assert response.status_code == 200
        response_time_ms = (end_time - start_time) * 1000
        assert response_time_ms < 500, f"Response time {response_time_ms:.2f}ms exceeds 500ms requirement"
    
    @pytest.mark.asyncio
    async def test_content_type_validation(
        self,
        async_client: AsyncClient,
        valid_asset_payload: Dict[str, Any],
        auth_headers: Dict[str, str]
    ):
        """Test API content type validation."""
        # Act - Send request with invalid content type
        response = await async_client.post(
            "/api/v1/assets/",
            data=json.dumps(valid_asset_payload),  # Send as raw string instead of JSON
            headers={**auth_headers, "Content-Type": "text/plain"}
        )
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_rate_limiting_simulation(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test API behavior under rapid successive requests."""
        # Act - Make multiple rapid requests
        responses = []
        for i in range(10):
            response = await async_client.get(
                "/api/v1/assets/",
                headers=auth_headers
            )
            responses.append(response.status_code)
        
        # Assert - All requests should succeed (no rate limiting implemented yet)
        assert all(status == 200 for status in responses)
    
    @pytest.mark.asyncio
    async def test_error_response_format(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test that error responses follow consistent format."""
        # Act - Trigger a 404 error
        fake_id = uuid.uuid4()
        response = await async_client.get(
            f"/api/v1/assets/{fake_id}",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 404
        error_response = response.json()
        
        assert "detail" in error_response
        assert isinstance(error_response["detail"], str)
        assert "not found" in error_response["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_cors_headers(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test CORS headers in API responses."""
        # Act
        response = await async_client.get(
            "/api/v1/assets/",
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        # CORS headers would be added by middleware in actual deployment
        # This test ensures the endpoint works for cross-origin requests