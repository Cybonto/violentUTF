# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Unit tests for ConflictResolutionService (Issue #280).

This module provides comprehensive unit tests for the ConflictResolutionService class,
covering duplicate detection algorithms, confidence scoring, and resolution strategies.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset_inventory import AssetType, CriticalityLevel, DatabaseAsset, Environment, SecurityClassification
from app.schemas.asset_schemas import AssetCreate
from app.services.asset_management.conflict_resolution_service import (
    ConflictCandidate,
    ConflictResolution,
    ConflictResolutionService,
    ConflictType,
    ResolutionAction,
)


class TestConflictResolutionService:
    """Test cases for ConflictResolutionService class."""
    
    @pytest.mark.asyncio
    async def test_detect_conflicts_exact_identifier_match(
        self, 
        async_session: AsyncSession, 
        conflict_resolution_service: ConflictResolutionService
    ):
        """Test conflict detection with exact identifier match."""
        # Arrange - Create existing asset
        existing_asset = DatabaseAsset(
            name="Existing Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="duplicate-identifier",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=95,
            created_by="test_user",
            updated_by="test_user"
        )
        async_session.add(existing_asset)
        await async_session.commit()
        await async_session.refresh(existing_asset)
        
        # New asset with same identifier
        new_asset = AssetCreate(
            name="New Asset",
            asset_type=AssetType.SQLITE,
            unique_identifier="duplicate-identifier",  # Same as existing
            location="/tmp/new.db",
            security_classification=SecurityClassification.PUBLIC,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="automated",
            confidence_score=90
        )
        
        # Act
        conflicts = await conflict_resolution_service.detect_conflicts(new_asset)
        
        # Assert
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.EXACT_IDENTIFIER
        assert conflicts[0].confidence_score == 1.0  # Perfect match
        assert conflicts[0].existing_asset.id == existing_asset.id
    
    @pytest.mark.asyncio
    async def test_detect_conflicts_similar_attributes(
        self, 
        async_session: AsyncSession, 
        conflict_resolution_service: ConflictResolutionService
    ):
        """Test conflict detection with similar attributes."""
        # Arrange - Create existing asset
        existing_asset = DatabaseAsset(
            name="Production Database",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="prod-db-001",
            location="prod-server.company.com:5432",
            security_classification=SecurityClassification.CONFIDENTIAL,
            criticality_level=CriticalityLevel.CRITICAL,
            environment=Environment.PRODUCTION,
            discovery_method="automated",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=98,
            created_by="discovery_system",
            updated_by="discovery_system"
        )
        async_session.add(existing_asset)
        await async_session.commit()
        await async_session.refresh(existing_asset)
        
        # New asset with similar attributes but different identifier
        similar_asset = AssetCreate(
            name="Production Database",  # Same name
            asset_type=AssetType.POSTGRESQL,  # Same type
            unique_identifier="prod-db-002",  # Different identifier
            location="prod-server.company.com:5432",  # Same location
            security_classification=SecurityClassification.CONFIDENTIAL,
            criticality_level=CriticalityLevel.CRITICAL,
            environment=Environment.PRODUCTION,
            discovery_method="manual",  # Different discovery method
            confidence_score=95
        )
        
        # Act
        conflicts = await conflict_resolution_service.detect_conflicts(similar_asset)
        
        # Assert
        assert len(conflicts) >= 1
        similarity_conflict = next(
            (c for c in conflicts if c.conflict_type == ConflictType.SIMILAR_ATTRIBUTES), 
            None
        )
        assert similarity_conflict is not None
        assert similarity_conflict.confidence_score >= 0.85  # High similarity threshold
        assert similarity_conflict.existing_asset.id == existing_asset.id
    
    @pytest.mark.asyncio
    async def test_detect_conflicts_no_matches(
        self, 
        async_session: AsyncSession, 
        conflict_resolution_service: ConflictResolutionService
    ):
        """Test conflict detection with no matches."""
        # Arrange - Create existing asset
        existing_asset = DatabaseAsset(
            name="PostgreSQL Database",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="postgres-001",
            location="db1.company.com:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=95,
            created_by="test_user",
            updated_by="test_user"
        )
        async_session.add(existing_asset)
        await async_session.commit()
        
        # Completely different asset
        different_asset = AssetCreate(
            name="Analytics DuckDB",
            asset_type=AssetType.DUCKDB,
            unique_identifier="analytics-duckdb-001",
            location="/data/analytics.duckdb",
            security_classification=SecurityClassification.PUBLIC,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="automated",
            confidence_score=80
        )
        
        # Act
        conflicts = await conflict_resolution_service.detect_conflicts(different_asset)
        
        # Assert
        assert len(conflicts) == 0
    
    @pytest.mark.asyncio
    async def test_calculate_similarity_score_high_similarity(
        self, 
        conflict_resolution_service: ConflictResolutionService
    ):
        """Test similarity score calculation for highly similar assets."""
        # Arrange
        existing_asset = DatabaseAsset(
            name="Main Database",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="main-db-001",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.HIGH,
            environment=Environment.PRODUCTION
        )
        
        new_asset = AssetCreate(
            name="Main Database",  # Same name
            asset_type=AssetType.POSTGRESQL,  # Same type
            unique_identifier="main-db-002",  # Different identifier
            location="localhost:5432",  # Same location
            security_classification=SecurityClassification.INTERNAL,  # Same classification
            criticality_level=CriticalityLevel.HIGH,  # Same criticality
            environment=Environment.PRODUCTION,  # Same environment
            discovery_method="automated",
            confidence_score=95
        )
        
        # Act
        similarity_score = conflict_resolution_service.calculate_similarity_score(new_asset, existing_asset)
        
        # Assert
        assert similarity_score >= 0.9  # Very high similarity
    
    @pytest.mark.asyncio
    async def test_calculate_similarity_score_medium_similarity(
        self, 
        conflict_resolution_service: ConflictResolutionService
    ):
        """Test similarity score calculation for moderately similar assets."""
        # Arrange
        existing_asset = DatabaseAsset(
            name="Database Server",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="db-server-001",
            location="server1.company.com:5432",
            security_classification=SecurityClassification.CONFIDENTIAL,
            criticality_level=CriticalityLevel.CRITICAL,
            environment=Environment.PRODUCTION
        )
        
        new_asset = AssetCreate(
            name="Database Server",  # Same name
            asset_type=AssetType.POSTGRESQL,  # Same type
            unique_identifier="db-server-002",  # Different identifier
            location="server2.company.com:5432",  # Different location
            security_classification=SecurityClassification.INTERNAL,  # Different classification
            criticality_level=CriticalityLevel.HIGH,  # Different criticality
            environment=Environment.STAGING,  # Different environment
            discovery_method="automated",
            confidence_score=90
        )
        
        # Act
        similarity_score = conflict_resolution_service.calculate_similarity_score(new_asset, existing_asset)
        
        # Assert
        assert 0.5 <= similarity_score < 0.9  # Medium similarity
    
    @pytest.mark.asyncio
    async def test_calculate_similarity_score_low_similarity(
        self, 
        conflict_resolution_service: ConflictResolutionService
    ):
        """Test similarity score calculation for low similarity assets."""
        # Arrange
        existing_asset = DatabaseAsset(
            name="PostgreSQL Production",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="pg-prod-001",
            location="prod-db.company.com:5432",
            security_classification=SecurityClassification.RESTRICTED,
            criticality_level=CriticalityLevel.CRITICAL,
            environment=Environment.PRODUCTION
        )
        
        new_asset = AssetCreate(
            name="Test SQLite",  # Different name
            asset_type=AssetType.SQLITE,  # Different type
            unique_identifier="test-sqlite-001",  # Different identifier
            location="/tmp/test.db",  # Different location
            security_classification=SecurityClassification.PUBLIC,  # Different classification
            criticality_level=CriticalityLevel.LOW,  # Different criticality
            environment=Environment.TESTING,  # Different environment
            discovery_method="manual",
            confidence_score=80
        )
        
        # Act
        similarity_score = conflict_resolution_service.calculate_similarity_score(new_asset, existing_asset)
        
        # Assert
        assert similarity_score < 0.5  # Low similarity
    
    def test_resolve_conflict_automatically_exact_match_high_confidence(
        self, 
        conflict_resolution_service: ConflictResolutionService
    ):
        """Test automatic resolution for exact match with high confidence."""
        # Arrange
        existing_asset = DatabaseAsset(
            name="Exact Match Asset",
            unique_identifier="exact-match-001"
        )
        
        conflict = ConflictCandidate(
            existing_asset=existing_asset,
            conflict_type=ConflictType.EXACT_IDENTIFIER,
            confidence_score=0.95
        )
        
        new_asset = AssetCreate(
            name="Same Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="exact-match-001",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="automated",
            confidence_score=98
        )
        
        # Act
        resolution = conflict_resolution_service.resolve_conflict_automatically(conflict, new_asset)
        
        # Assert
        assert resolution.action == ResolutionAction.MERGE
        assert resolution.automatic is True
        assert "Exact identifier match with high confidence" in resolution.reason
    
    def test_resolve_conflict_automatically_similar_high_confidence(
        self, 
        conflict_resolution_service: ConflictResolutionService
    ):
        """Test automatic resolution for similar attributes with high confidence."""
        # Arrange
        existing_asset = DatabaseAsset(
            name="Similar Asset",
            unique_identifier="similar-001"
        )
        
        conflict = ConflictCandidate(
            existing_asset=existing_asset,
            conflict_type=ConflictType.SIMILAR_ATTRIBUTES,
            confidence_score=0.92
        )
        
        new_asset = AssetCreate(
            name="Similar Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="similar-002",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="automated",
            confidence_score=95
        )
        
        # Act
        resolution = conflict_resolution_service.resolve_conflict_automatically(conflict, new_asset)
        
        # Assert
        assert resolution.action == ResolutionAction.MANUAL_REVIEW
        assert resolution.automatic is False
        assert "High similarity requires manual review" in resolution.reason
    
    def test_resolve_conflict_automatically_low_confidence(
        self, 
        conflict_resolution_service: ConflictResolutionService
    ):
        """Test automatic resolution for low confidence similarity."""
        # Arrange
        existing_asset = DatabaseAsset(
            name="Different Asset",
            unique_identifier="different-001"
        )
        
        conflict = ConflictCandidate(
            existing_asset=existing_asset,
            conflict_type=ConflictType.SIMILAR_ATTRIBUTES,
            confidence_score=0.70
        )
        
        new_asset = AssetCreate(
            name="Somewhat Similar Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="somewhat-similar-001",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="automated",
            confidence_score=85
        )
        
        # Act
        resolution = conflict_resolution_service.resolve_conflict_automatically(conflict, new_asset)
        
        # Assert
        assert resolution.action == ResolutionAction.CREATE_SEPARATE
        assert resolution.automatic is True
        assert "Low similarity confidence, treating as separate asset" in resolution.reason
    
    @pytest.mark.asyncio
    async def test_find_exact_identifier_match(
        self, 
        async_session: AsyncSession, 
        conflict_resolution_service: ConflictResolutionService
    ):
        """Test finding exact identifier matches."""
        # Arrange - Create asset with specific identifier
        target_identifier = "exact-match-test-001"
        existing_asset = DatabaseAsset(
            name="Exact Match Test",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier=target_identifier,
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=95,
            created_by="test_user",
            updated_by="test_user"
        )
        async_session.add(existing_asset)
        await async_session.commit()
        await async_session.refresh(existing_asset)
        
        # Act
        found_asset = await conflict_resolution_service.find_exact_identifier_match(target_identifier)
        
        # Assert
        assert found_asset is not None
        assert found_asset.id == existing_asset.id
        assert found_asset.unique_identifier == target_identifier
    
    @pytest.mark.asyncio
    async def test_find_exact_identifier_match_not_found(
        self, 
        async_session: AsyncSession, 
        conflict_resolution_service: ConflictResolutionService
    ):
        """Test finding exact identifier match when none exists."""
        # Act
        found_asset = await conflict_resolution_service.find_exact_identifier_match("non-existent-identifier")
        
        # Assert
        assert found_asset is None
    
    @pytest.mark.asyncio
    async def test_find_similar_assets(
        self, 
        async_session: AsyncSession, 
        conflict_resolution_service: ConflictResolutionService
    ):
        """Test finding similar assets based on name, location, and type."""
        # Arrange - Create multiple assets with varying similarity
        assets = [
            DatabaseAsset(
                name="Production Database",
                asset_type=AssetType.POSTGRESQL,
                unique_identifier="prod-001",
                location="prod-server:5432",
                security_classification=SecurityClassification.CONFIDENTIAL,
                criticality_level=CriticalityLevel.CRITICAL,
                environment=Environment.PRODUCTION,
                discovery_method="automated",
                discovery_timestamp=datetime.now(timezone.utc),
                confidence_score=98,
                created_by="system",
                updated_by="system"
            ),
            DatabaseAsset(
                name="Development Database",
                asset_type=AssetType.POSTGRESQL,
                unique_identifier="dev-001",
                location="dev-server:5432",
                security_classification=SecurityClassification.INTERNAL,
                criticality_level=CriticalityLevel.MEDIUM,
                environment=Environment.DEVELOPMENT,
                discovery_method="manual",
                discovery_timestamp=datetime.now(timezone.utc),
                confidence_score=90,
                created_by="dev_user",
                updated_by="dev_user"
            ),
            DatabaseAsset(
                name="Analytics Data",
                asset_type=AssetType.DUCKDB,
                unique_identifier="analytics-001",
                location="/data/analytics.duckdb",
                security_classification=SecurityClassification.INTERNAL,
                criticality_level=CriticalityLevel.HIGH,
                environment=Environment.PRODUCTION,
                discovery_method="automated",
                discovery_timestamp=datetime.now(timezone.utc),
                confidence_score=95,
                created_by="analytics_system",
                updated_by="analytics_system"
            )
        ]
        
        for asset in assets:
            async_session.add(asset)
        await async_session.commit()
        
        # Test finding similar PostgreSQL databases
        new_asset = AssetCreate(
            name="Production Database",  # Same as first asset
            asset_type=AssetType.POSTGRESQL,  # Same as first two assets
            unique_identifier="prod-002",
            location="prod-server:5432",  # Same as first asset
            security_classification=SecurityClassification.CONFIDENTIAL,
            criticality_level=CriticalityLevel.CRITICAL,
            environment=Environment.PRODUCTION,
            discovery_method="automated",
            confidence_score=97
        )
        
        # Act
        similar_assets = await conflict_resolution_service.find_similar_assets(new_asset)
        
        # Assert
        assert len(similar_assets) >= 1
        
        # Should find the first asset as most similar
        most_similar = similar_assets[0]
        assert most_similar.name == "Production Database"
        assert most_similar.asset_type == AssetType.POSTGRESQL
        assert most_similar.location == "prod-server:5432"
    
    @pytest.mark.asyncio
    async def test_conflict_resolution_with_multiple_candidates(
        self, 
        async_session: AsyncSession, 
        conflict_resolution_service: ConflictResolutionService
    ):
        """Test conflict resolution with multiple candidate matches."""
        # Arrange - Create multiple potentially conflicting assets
        assets = [
            DatabaseAsset(
                name="Main Database",
                asset_type=AssetType.POSTGRESQL,
                unique_identifier="main-001",
                location="server1:5432",
                security_classification=SecurityClassification.INTERNAL,
                criticality_level=CriticalityLevel.HIGH,
                environment=Environment.PRODUCTION,
                discovery_method="automated",
                discovery_timestamp=datetime.now(timezone.utc),
                confidence_score=95,
                created_by="system",
                updated_by="system"
            ),
            DatabaseAsset(
                name="Main Database",  # Same name
                asset_type=AssetType.POSTGRESQL,  # Same type
                unique_identifier="main-002",
                location="server2:5432",  # Different server
                security_classification=SecurityClassification.CONFIDENTIAL,  # Different classification
                criticality_level=CriticalityLevel.CRITICAL,  # Different criticality
                environment=Environment.PRODUCTION,  # Same environment
                discovery_method="manual",
                discovery_timestamp=datetime.now(timezone.utc),
                confidence_score=90,
                created_by="dba",
                updated_by="dba"
            )
        ]
        
        for asset in assets:
            async_session.add(asset)
        await async_session.commit()
        
        # New asset similar to both existing assets
        new_asset = AssetCreate(
            name="Main Database",  # Same name as both
            asset_type=AssetType.POSTGRESQL,  # Same type as both
            unique_identifier="main-003",
            location="server3:5432",  # Different location
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.HIGH,
            environment=Environment.PRODUCTION,
            discovery_method="automated",
            confidence_score=93
        )
        
        # Act
        conflicts = await conflict_resolution_service.detect_conflicts(new_asset)
        
        # Assert
        assert len(conflicts) >= 2  # Should detect conflicts with both existing assets
        
        # Conflicts should be sorted by confidence score (highest first)
        assert conflicts[0].confidence_score >= conflicts[1].confidence_score
        
        # All conflicts should be similar attributes type (no exact identifier match)
        for conflict in conflicts:
            assert conflict.conflict_type == ConflictType.SIMILAR_ATTRIBUTES
    
    @pytest.mark.asyncio
    async def test_conflict_resolution_threshold_configuration(
        self, 
        async_session: AsyncSession
    ):
        """Test that similarity threshold can be configured."""
        # Arrange - Create service with custom threshold
        custom_threshold = 0.75
        custom_service = ConflictResolutionService(async_session, similarity_threshold=custom_threshold)
        
        # Create existing asset
        existing_asset = DatabaseAsset(
            name="Threshold Test",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="threshold-001",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=90,
            created_by="test_user",
            updated_by="test_user"
        )
        async_session.add(existing_asset)
        await async_session.commit()
        
        # Create new asset with moderate similarity
        moderate_similarity_asset = AssetCreate(
            name="Threshold Test",  # Same name
            asset_type=AssetType.SQLITE,  # Different type
            unique_identifier="threshold-002",
            location="/tmp/test.db",  # Different location
            security_classification=SecurityClassification.PUBLIC,  # Different classification
            criticality_level=CriticalityLevel.LOW,  # Different criticality
            environment=Environment.TESTING,  # Different environment
            discovery_method="automated",
            confidence_score=85
        )
        
        # Act
        conflicts = await custom_service.detect_conflicts(moderate_similarity_asset)
        
        # Assert - The result depends on whether the calculated similarity meets the threshold
        # This tests that the threshold is being applied correctly
        if conflicts:
            assert all(c.confidence_score >= custom_threshold for c in conflicts)
        
        # Verify the threshold is actually being used
        assert custom_service.similarity_threshold == custom_threshold