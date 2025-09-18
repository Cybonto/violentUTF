# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Test configuration and fixtures for Issue #280 Asset Management System.

This module provides comprehensive test fixtures, database setup, and
utilities for testing the asset management system with high test coverage.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Generator, List, Union, Any, Optional
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.db.database import Base, get_session
from app.models.asset_inventory import (
    DatabaseAsset, 
    AssetRelationship, 
    AssetAuditLog,
    AssetType,
    SecurityClassification,
    CriticalityLevel,
    Environment,
    ValidationStatus,
    RelationshipType,
    RelationshipStrength,
    ChangeType
)
from app.schemas.asset_schemas import AssetCreate, AssetUpdate
from app.services.asset_management.asset_service import AssetService
from app.services.asset_management.audit_service import AuditService
from app.services.asset_management.validation_service import ValidationService
from app.services.asset_management.conflict_resolution_service import ConflictResolutionService


# Test database configuration
SQLITE_TEST_URL = "sqlite+aiosqlite:///./test_asset_management.db"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async engine for testing."""
    engine = create_async_engine(
        SQLITE_TEST_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for testing."""
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(async_session) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with database session override."""
    
    async def override_get_session():
        yield async_session
    
    app.dependency_overrides[get_session] = override_get_session
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_current_user() -> Dict[str, Union[str, List[str]]]:
    """Mock current user for authentication testing."""
    return {
        "username": "test_user",
        "email": "test@example.com",
        "roles": ["asset_manager"]
    }


# Asset test data fixtures
@pytest.fixture
def sample_asset_data() -> AssetCreate:
    """Create sample asset data for testing."""
    return AssetCreate(
        name="Test PostgreSQL Database",
        asset_type=AssetType.POSTGRESQL,
        unique_identifier="test-postgres-001",
        location="localhost:5432",
        security_classification=SecurityClassification.INTERNAL,
        criticality_level=CriticalityLevel.MEDIUM,
        environment=Environment.DEVELOPMENT,
        discovery_method="manual",
        confidence_score=95,
        connection_string="postgresql://user:pass@localhost:5432/testdb",
        network_location="10.0.1.100:5432",
        database_version="14.5",
        estimated_size_mb=1024,
        table_count=15,
        owner_team="development",
        technical_contact="dev-team@company.com",
        business_contact="product-owner@company.com",
        purpose_description="Development database for testing",
        encryption_enabled=True,
        access_restricted=True,
        backup_configured=True,
        compliance_requirements={"gdpr": True, "soc2": False}
    )


@pytest.fixture
def sample_asset_data_list() -> List[AssetCreate]:
    """Create list of sample asset data for bulk testing."""
    return [
        AssetCreate(
            name="Production PostgreSQL",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="prod-postgres-001",
            location="prod-db-1.company.com:5432",
            security_classification=SecurityClassification.CONFIDENTIAL,
            criticality_level=CriticalityLevel.CRITICAL,
            environment=Environment.PRODUCTION,
            discovery_method="automated",
            confidence_score=98,
            connection_string="postgresql://prod_user:***@prod-db-1:5432/maindb",
            technical_contact="dba-team@company.com",
            backup_configured=True,
            compliance_requirements={"gdpr": True, "soc2": True}
        ),
        AssetCreate(
            name="Analytics DuckDB",
            asset_type=AssetType.DUCKDB,
            unique_identifier="analytics-duckdb-001",
            location="/data/analytics/main.duckdb",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.HIGH,
            environment=Environment.PRODUCTION,
            discovery_method="automated",
            confidence_score=92,
            file_path="/data/analytics/main.duckdb",
            technical_contact="analytics-team@company.com",
            backup_configured=False
        ),
        AssetCreate(
            name="Test SQLite DB",
            asset_type=AssetType.SQLITE,
            unique_identifier="test-sqlite-001",
            location="/tmp/test.db",
            security_classification=SecurityClassification.PUBLIC,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="manual",
            confidence_score=85,
            file_path="/tmp/test.db",
            technical_contact="test-team@company.com"
        )
    ]


@pytest.fixture
def sample_asset_update() -> AssetUpdate:
    """Create sample asset update data for testing."""
    return AssetUpdate(
        name="Updated PostgreSQL Database",
        purpose_description="Updated development database for enhanced testing",
        estimated_size_mb=2048,
        table_count=25,
        technical_contact="new-dev-team@company.com"
    )


@pytest_asyncio.fixture
async def sample_database_asset(async_session: AsyncSession) -> DatabaseAsset:
    """Create and persist a sample database asset for testing."""
    asset = DatabaseAsset(
        name="Sample Database Asset",
        asset_type=AssetType.POSTGRESQL,
        unique_identifier="sample-postgres-001",
        location="localhost:5432",
        security_classification=SecurityClassification.INTERNAL,
        criticality_level=CriticalityLevel.MEDIUM,
        environment=Environment.DEVELOPMENT,
        discovery_method="test",
        discovery_timestamp=datetime.now(timezone.utc),
        confidence_score=95,
        created_by="test_user",
        updated_by="test_user"
    )
    
    async_session.add(asset)
    await async_session.commit()
    await async_session.refresh(asset)
    return asset


@pytest_asyncio.fixture
async def sample_asset_relationship(
    async_session: AsyncSession,
    sample_database_asset: DatabaseAsset
) -> AssetRelationship:
    """Create and persist a sample asset relationship for testing."""
    # Create a second asset for the relationship
    target_asset = DatabaseAsset(
        name="Target Database Asset",
        asset_type=AssetType.SQLITE,
        unique_identifier="target-sqlite-001",
        location="/tmp/target.db",
        security_classification=SecurityClassification.INTERNAL,
        criticality_level=CriticalityLevel.LOW,
        environment=Environment.TESTING,
        discovery_method="test",
        discovery_timestamp=datetime.now(timezone.utc),
        confidence_score=90,
        created_by="test_user",
        updated_by="test_user"
    )
    
    async_session.add(target_asset)
    await async_session.commit()
    await async_session.refresh(target_asset)
    
    # Create relationship
    relationship = AssetRelationship(
        source_asset_id=sample_database_asset.id,
        target_asset_id=target_asset.id,
        relationship_type=RelationshipType.DEPENDS_ON,
        relationship_strength=RelationshipStrength.MEDIUM,
        description="Test dependency relationship",
        discovered_method="test",
        confidence_score=85,
        created_by="test_user",
        updated_by="test_user"
    )
    
    async_session.add(relationship)
    await async_session.commit()
    await async_session.refresh(relationship)
    return relationship


@pytest_asyncio.fixture
async def sample_audit_log(
    async_session: AsyncSession,
    sample_database_asset: DatabaseAsset
) -> AssetAuditLog:
    """Create and persist a sample audit log for testing."""
    audit_log = AssetAuditLog(
        asset_id=sample_database_asset.id,
        change_type=ChangeType.CREATE,
        field_changed="name",
        new_value="Sample Database Asset",
        change_reason="Initial creation",
        changed_by="test_user",
        change_source="API",
        compliance_relevant=True,
        timestamp=datetime.now(timezone.utc)
    )
    
    async_session.add(audit_log)
    await async_session.commit()
    await async_session.refresh(audit_log)
    return audit_log


# Service fixtures
@pytest.fixture
def asset_service(async_session: AsyncSession) -> AssetService:
    """Create asset service for testing."""
    audit_service = AuditService(async_session)
    return AssetService(async_session, audit_service)


@pytest.fixture
def audit_service(async_session: AsyncSession) -> AuditService:
    """Create audit service for testing."""
    return AuditService(async_session)


@pytest.fixture
def validation_service() -> ValidationService:
    """Create validation service for testing."""
    return ValidationService()


@pytest.fixture
def conflict_resolution_service(async_session: AsyncSession) -> ConflictResolutionService:
    """Create conflict resolution service for testing."""
    return ConflictResolutionService(async_session)


# Mock fixtures for external dependencies
@pytest.fixture
def mock_discovery_service():
    """Mock discovery service for integration testing."""
    mock = MagicMock()
    mock.process_discovery_report = AsyncMock()
    mock.validate_discovery_data = AsyncMock()
    return mock


@pytest.fixture
def mock_auth_service():
    """Mock authentication service for API testing."""
    mock = MagicMock()
    mock.get_current_user = AsyncMock()
    mock.verify_token = AsyncMock()
    return mock


# Performance testing fixtures
@pytest.fixture
def performance_test_data() -> List[AssetCreate]:
    """Generate large dataset for performance testing."""
    assets = []
    for i in range(1000):
        assets.append(AssetCreate(
            name=f"Performance Test Asset {i:04d}",
            asset_type=AssetType.POSTGRESQL if i % 2 == 0 else AssetType.SQLITE,
            unique_identifier=f"perf-test-{i:04d}",
            location=f"server-{i//10}.company.com:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.TESTING,
            discovery_method="performance_test",
            confidence_score=95,
            technical_contact=f"team-{i//100}@company.com"
        ))
    return assets


# Utility functions for testing
def assert_asset_equals(actual: DatabaseAsset, expected: AssetCreate, created_by: str = "test_user"):
    """Assert that a database asset matches the expected creation data."""
    assert actual.name == expected.name
    assert actual.asset_type == expected.asset_type
    assert actual.unique_identifier == expected.unique_identifier
    assert actual.location == expected.location
    assert actual.security_classification == expected.security_classification
    assert actual.criticality_level == expected.criticality_level
    assert actual.environment == expected.environment
    assert actual.discovery_method == expected.discovery_method
    assert actual.confidence_score == expected.confidence_score
    assert actual.created_by == created_by
    assert actual.updated_by == created_by
    assert actual.is_deleted is False


def create_test_asset_dict(
    name: str = "Test Asset",
    asset_type: str = "POSTGRESQL",
    unique_id: Optional[str] = None
) -> Dict:
    """Create a test asset dictionary for API testing."""
    if unique_id is None:
        unique_id = f"test-asset-{uuid.uuid4()}"
    
    return {
        "name": name,
        "asset_type": asset_type,
        "unique_identifier": unique_id,
        "location": "localhost:5432",
        "security_classification": "INTERNAL",
        "criticality_level": "MEDIUM",
        "environment": "DEVELOPMENT",
        "discovery_method": "manual",
        "confidence_score": 95,
        "technical_contact": "test@example.com"
    }


# Test database cleanup utilities
@pytest_asyncio.fixture(autouse=True)
async def cleanup_database(async_session: AsyncSession):
    """Clean up database after each test."""
    yield
    # This runs after each test
    try:
        # Clean up any remaining test data
        await async_session.rollback()
    except Exception:
        pass