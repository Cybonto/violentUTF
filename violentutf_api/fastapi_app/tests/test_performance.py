# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Performance tests for Asset Management System (Issue #280).

This module provides comprehensive performance tests to validate that
all operations meet the <500ms response time requirement and handle
concurrent load efficiently.
"""

import asyncio
import statistics
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset_inventory import AssetType, CriticalityLevel, DatabaseAsset, Environment, SecurityClassification
from app.schemas.asset_schemas import AssetCreate
from app.services.asset_management.asset_service import AssetService
from app.services.asset_management.audit_service import AuditService


class TestAssetManagementPerformance:
    """Performance tests for asset management system."""
    
    # Performance thresholds
    MAX_RESPONSE_TIME_MS = 500
    MAX_BULK_OPERATION_TIME_MS = 2000
    MIN_CONCURRENT_USERS = 10
    MAX_CONCURRENT_USERS = 50
    
    @pytest.fixture
    def performance_auth_headers(self) -> Dict[str, str]:
        """Authentication headers for performance testing."""
        return {"Authorization": "Bearer performance_test_token"}
    
    @pytest.fixture
    async def performance_test_assets(self, async_session: AsyncSession) -> List[DatabaseAsset]:
        """Create a large dataset for performance testing."""
        assets = []
        
        # Create 1000 test assets for performance testing
        for i in range(1000):
            asset = DatabaseAsset(
                name=f"Performance Test Asset {i:04d}",
                asset_type=AssetType.POSTGRESQL if i % 3 == 0 else (
                    AssetType.SQLITE if i % 3 == 1 else AssetType.DUCKDB
                ),
                unique_identifier=f"perf-test-{i:04d}",
                location=f"perf-server-{i//50}.company.com:5432" if i % 3 == 0 else (
                    f"/data/perf-{i:04d}.db" if i % 3 == 1 else f"/analytics/perf-{i:04d}.duckdb"
                ),
                security_classification=SecurityClassification.INTERNAL if i % 2 == 0 else SecurityClassification.CONFIDENTIAL,
                criticality_level=CriticalityLevel.MEDIUM if i % 2 == 0 else CriticalityLevel.HIGH,
                environment=Environment.DEVELOPMENT if i % 4 == 0 else (
                    Environment.TESTING if i % 4 == 1 else (
                        Environment.STAGING if i % 4 == 2 else Environment.PRODUCTION
                    )
                ),
                discovery_method="automated_performance_test",
                discovery_timestamp=datetime.now(timezone.utc),
                confidence_score=85 + (i % 15),  # Vary between 85-99
                database_version=f"1{i % 5}.{i % 10}",
                estimated_size_mb=1024 + (i * 10),
                table_count=10 + (i % 50),
                owner_team=f"team-{i % 10}",
                technical_contact=f"team-{i % 10}@company.com",
                created_by="performance_test_user",
                updated_by="performance_test_user"
            )
            async_session.add(asset)
            assets.append(asset)
            
            # Commit in batches to avoid memory issues
            if i % 100 == 99:
                await async_session.commit()
        
        await async_session.commit()
        
        # Refresh all assets to get their IDs
        for asset in assets:
            await async_session.refresh(asset)
        
        return assets
    
    @pytest.mark.asyncio
    async def test_api_list_assets_response_time(
        self,
        async_client: AsyncClient,
        performance_test_assets: List[DatabaseAsset],
        performance_auth_headers: Dict[str, str]
    ):
        """Test that list assets API meets response time requirements."""
        # Warm up the database
        await async_client.get("/api/v1/assets/?limit=10", headers=performance_auth_headers)
        
        # Measure response times for different page sizes
        test_cases = [
            {"limit": 10, "skip": 0},
            {"limit": 50, "skip": 0}, 
            {"limit": 100, "skip": 0},
            {"limit": 100, "skip": 500},  # Middle page
            {"limit": 100, "skip": 900},  # Near end
        ]
        
        response_times = []
        
        for test_case in test_cases:
            start_time = time.time()
            
            response = await async_client.get(
                f"/api/v1/assets/?limit={test_case['limit']}&skip={test_case['skip']}",
                headers=performance_auth_headers
            )
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            response_times.append(response_time_ms)
            
            # Assert response is successful and meets time requirement
            assert response.status_code == 200
            assert response_time_ms < self.MAX_RESPONSE_TIME_MS, \
                f"List assets response time {response_time_ms:.2f}ms exceeds {self.MAX_RESPONSE_TIME_MS}ms limit"
            
            # Verify response contains expected data
            data = response.json()
            assert len(data) <= test_case['limit']
        
        # Performance statistics
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        print(f"List Assets Performance - Avg: {avg_response_time:.2f}ms, Max: {max_response_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_api_get_single_asset_response_time(
        self,
        async_client: AsyncClient,
        performance_test_assets: List[DatabaseAsset],
        performance_auth_headers: Dict[str, str]
    ):
        """Test that get single asset API meets response time requirements."""
        # Test getting different assets
        test_assets = performance_test_assets[:10]  # Test first 10 assets
        response_times = []
        
        for asset in test_assets:
            start_time = time.time()
            
            response = await async_client.get(
                f"/api/v1/assets/{asset.id}",
                headers=performance_auth_headers
            )
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            response_times.append(response_time_ms)
            
            assert response.status_code == 200
            assert response_time_ms < self.MAX_RESPONSE_TIME_MS, \
                f"Get asset response time {response_time_ms:.2f}ms exceeds {self.MAX_RESPONSE_TIME_MS}ms limit"
        
        avg_response_time = statistics.mean(response_times)
        print(f"Get Single Asset Performance - Avg: {avg_response_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_api_create_asset_response_time(
        self,
        async_client: AsyncClient,
        performance_auth_headers: Dict[str, str]
    ):
        """Test that create asset API meets response time requirements."""
        response_times = []
        
        # Test creating 10 assets
        for i in range(10):
            asset_payload = {
                "name": f"Performance Create Test {i}",
                "asset_type": "POSTGRESQL",
                "unique_identifier": f"perf-create-{i}-{uuid.uuid4()}",
                "location": f"perf-create-{i}.test.com:5432",
                "security_classification": "INTERNAL",
                "criticality_level": "MEDIUM",
                "environment": "DEVELOPMENT",
                "discovery_method": "manual",
                "confidence_score": 95,
                "technical_contact": f"perf-test-{i}@test.com"
            }
            
            start_time = time.time()
            
            response = await async_client.post(
                "/api/v1/assets/",
                json=asset_payload,
                headers=performance_auth_headers
            )
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            response_times.append(response_time_ms)
            
            assert response.status_code == 201
            assert response_time_ms < self.MAX_RESPONSE_TIME_MS, \
                f"Create asset response time {response_time_ms:.2f}ms exceeds {self.MAX_RESPONSE_TIME_MS}ms limit"
        
        avg_response_time = statistics.mean(response_times)
        print(f"Create Asset Performance - Avg: {avg_response_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_api_search_assets_response_time(
        self,
        async_client: AsyncClient,
        performance_test_assets: List[DatabaseAsset],
        performance_auth_headers: Dict[str, str]
    ):
        """Test that search assets API meets response time requirements."""
        search_queries = [
            "Performance",
            "PostgreSQL", 
            "team-1",
            "5432",
            "Asset 0001"
        ]
        
        response_times = []
        
        for query in search_queries:
            search_payload = {
                "query": query,
                "limit": 50,
                "offset": 0
            }
            
            start_time = time.time()
            
            response = await async_client.post(
                "/api/v1/assets/search",
                json=search_payload,
                headers=performance_auth_headers
            )
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            response_times.append(response_time_ms)
            
            assert response.status_code == 200
            assert response_time_ms < self.MAX_RESPONSE_TIME_MS, \
                f"Search assets response time {response_time_ms:.2f}ms exceeds {self.MAX_RESPONSE_TIME_MS}ms limit"
            
            # Verify response structure
            data = response.json()
            assert "results" in data
            assert "execution_time" in data
        
        avg_response_time = statistics.mean(response_times)
        print(f"Search Assets Performance - Avg: {avg_response_time:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_concurrent_api_requests(
        self,
        async_client: AsyncClient,
        performance_test_assets: List[DatabaseAsset],
        performance_auth_headers: Dict[str, str]
    ):
        """Test API performance under concurrent load."""
        
        async def make_request(endpoint: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> float:
            """Make a single API request and return response time."""
            start_time = time.time()
            
            if method == "GET":
                response = await async_client.get(endpoint, headers=performance_auth_headers)
            elif method == "POST":
                response = await async_client.post(endpoint, json=payload, headers=performance_auth_headers)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            assert response.status_code in [200, 201, 202]
            return response_time
        
        # Define concurrent test scenarios
        RequestTuple = Tuple[str, str, Optional[Dict[str, Any]]]
        
        scenario_1: List[RequestTuple] = [("/api/v1/assets/?limit=20", "GET", None)] * 10
        
        scenario_2_part1: List[RequestTuple] = [("/api/v1/assets/?limit=10", "GET", None)] * 5
        scenario_2_part2: List[RequestTuple] = [("/api/v1/assets/search", "POST", {"query": "Performance", "limit": 10, "offset": 0})] * 5
        scenario_2: List[RequestTuple] = scenario_2_part1 + scenario_2_part2
        
        scenario_3_part1: List[RequestTuple] = [("/api/v1/assets/?limit=50", "GET", None)] * 3
        scenario_3_part2: List[RequestTuple] = [("/api/v1/assets/search", "POST", {"query": "test", "limit": 20, "offset": 0})] * 3
        scenario_3_part3: List[RequestTuple] = [("/api/v1/assets", "POST", {
            "name": f"Concurrent Test {uuid.uuid4()}",
            "asset_type": "SQLITE",
            "unique_identifier": f"concurrent-{uuid.uuid4()}",
            "location": "/tmp/concurrent.db",
            "security_classification": "INTERNAL",
            "criticality_level": "LOW",
            "environment": "TESTING",
            "discovery_method": "manual",
            "confidence_score": 85
        })] * 4
        scenario_3: List[RequestTuple] = scenario_3_part1 + scenario_3_part2 + scenario_3_part3
        
        concurrent_scenarios: List[List[RequestTuple]] = [scenario_1, scenario_2, scenario_3]
        
        for scenario_idx, scenario in enumerate(concurrent_scenarios):
            print(f"Testing concurrent scenario {scenario_idx + 1}")
            
            # Execute all requests concurrently
            tasks = [make_request(endpoint, method, payload) for endpoint, method, payload in scenario]
            response_times = await asyncio.gather(*tasks)
            
            # Analyze results
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
            
            print(f"Concurrent Scenario {scenario_idx + 1} - "
                  f"Avg: {avg_response_time:.2f}ms, "
                  f"Max: {max_response_time:.2f}ms, "
                  f"P95: {p95_response_time:.2f}ms")
            
            # Performance assertions
            assert avg_response_time < self.MAX_RESPONSE_TIME_MS, \
                f"Average response time {avg_response_time:.2f}ms exceeds limit"
            assert p95_response_time < self.MAX_RESPONSE_TIME_MS * 1.5, \
                f"95th percentile response time {p95_response_time:.2f}ms exceeds 1.5x limit"
    
    @pytest.mark.asyncio
    async def test_service_layer_performance(self, async_session: AsyncSession):
        """Test service layer performance for bulk operations."""
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Test bulk asset creation
        bulk_assets = []
        for i in range(100):
            asset_data = AssetCreate(
                name=f"Service Performance Test {i}",
                asset_type=AssetType.SQLITE,
                unique_identifier=f"service-perf-{i}-{uuid.uuid4()}",
                location=f"/tmp/service-perf-{i}.db",
                security_classification=SecurityClassification.INTERNAL,
                criticality_level=CriticalityLevel.LOW,
                environment=Environment.TESTING,
                discovery_method="performance_test",
                confidence_score=85
            )
            bulk_assets.append(asset_data)
        
        # Measure bulk creation time
        start_time = time.time()
        
        created_assets = []
        for asset_data in bulk_assets:
            created_asset = await asset_service.create_asset(asset_data, "perf_test_user")
            created_assets.append(created_asset)
        
        end_time = time.time()
        bulk_create_time_ms = (end_time - start_time) * 1000
        
        print(f"Bulk creation of 100 assets: {bulk_create_time_ms:.2f}ms")
        assert bulk_create_time_ms < 10000, f"Bulk creation time {bulk_create_time_ms:.2f}ms too slow"
        
        # Test bulk retrieval
        start_time = time.time()
        
        retrieved_assets = await asset_service.list_assets(skip=0, limit=1000, filters={})
        
        end_time = time.time()
        bulk_retrieve_time_ms = (end_time - start_time) * 1000
        
        print(f"Bulk retrieval of assets: {bulk_retrieve_time_ms:.2f}ms")
        assert bulk_retrieve_time_ms < self.MAX_RESPONSE_TIME_MS, \
            f"Bulk retrieval time {bulk_retrieve_time_ms:.2f}ms exceeds limit"
        
        assert len(retrieved_assets) >= 100  # Should include our created assets
    
    @pytest.mark.asyncio
    async def test_database_query_performance(self, async_session: AsyncSession, performance_test_assets: List[DatabaseAsset]):
        """Test raw database query performance."""
        from sqlalchemy import func, select

        # Test simple select performance
        start_time = time.time()
        
        result = await async_session.execute(
            select(DatabaseAsset).limit(100)
        )
        assets = result.scalars().all()
        
        end_time = time.time()
        simple_query_time_ms = (end_time - start_time) * 1000
        
        print(f"Simple select query (100 rows): {simple_query_time_ms:.2f}ms")
        assert simple_query_time_ms < 100, f"Simple query too slow: {simple_query_time_ms:.2f}ms"
        assert len(assets) == 100
        
        # Test filtered query performance
        start_time = time.time()
        
        result = await async_session.execute(
            select(DatabaseAsset).where(
                DatabaseAsset.asset_type == AssetType.POSTGRESQL
            ).limit(50)
        )
        filtered_assets = result.scalars().all()
        
        end_time = time.time()
        filtered_query_time_ms = (end_time - start_time) * 1000
        
        print(f"Filtered query (PostgreSQL assets): {filtered_query_time_ms:.2f}ms")
        assert filtered_query_time_ms < 200, f"Filtered query too slow: {filtered_query_time_ms:.2f}ms"
        
        # Test aggregation query performance
        start_time = time.time()
        
        result = await async_session.execute(
            select(
                DatabaseAsset.asset_type,
                func.count(DatabaseAsset.id).label('count')
            ).group_by(DatabaseAsset.asset_type)
        )
        aggregation_results = result.all()
        
        end_time = time.time()
        aggregation_query_time_ms = (end_time - start_time) * 1000
        
        print(f"Aggregation query (count by type): {aggregation_query_time_ms:.2f}ms")
        assert aggregation_query_time_ms < 300, f"Aggregation query too slow: {aggregation_query_time_ms:.2f}ms"
        assert len(aggregation_results) > 0
    
    @pytest.mark.asyncio
    async def test_search_performance_with_large_dataset(
        self,
        async_session: AsyncSession,
        performance_test_assets: List[DatabaseAsset]
    ):
        """Test search performance with large dataset."""
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        search_terms = [
            "Performance",      # Should match many assets
            "Asset 0001",       # Should match specific assets
            "team-5",           # Should match team-related assets
            "postgresql",       # Should match by type
            "nonexistent"       # Should match nothing
        ]
        
        for search_term in search_terms:
            start_time = time.time()
            
            results = await asset_service.search_assets(
                search_term=search_term,
                limit=100,
                offset=0
            )
            
            end_time = time.time()
            search_time_ms = (end_time - start_time) * 1000
            
            print(f"Search '{search_term}': {search_time_ms:.2f}ms, {len(results)} results")
            
            assert search_time_ms < self.MAX_RESPONSE_TIME_MS, \
                f"Search for '{search_term}' took {search_time_ms:.2f}ms, exceeds limit"
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(
        self,
        async_client: AsyncClient,
        performance_test_assets: List[DatabaseAsset],
        performance_auth_headers: Dict[str, str]
    ):
        """Test memory usage doesn't grow excessively under load."""
        import os

        import psutil

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make many requests
        for i in range(50):
            response = await async_client.get(
                f"/api/v1/assets/?limit=20&skip={i * 20}",
                headers=performance_auth_headers
            )
            assert response.status_code == 200
        
        # Check memory usage after load
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Memory usage - Initial: {initial_memory:.2f}MB, Final: {final_memory:.2f}MB, Increase: {memory_increase:.2f}MB")
        
        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100, f"Memory increase {memory_increase:.2f}MB too high"
    
    @pytest.mark.asyncio 
    async def test_response_time_consistency(
        self,
        async_client: AsyncClient,
        performance_test_assets: List[DatabaseAsset],
        performance_auth_headers: Dict[str, str]
    ):
        """Test that response times are consistent across multiple requests."""
        # Make 20 identical requests and measure consistency
        response_times = []
        
        for _ in range(20):
            start_time = time.time()
            
            response = await async_client.get(
                "/api/v1/assets/?limit=50",
                headers=performance_auth_headers
            )
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            response_times.append(response_time_ms)
            
            assert response.status_code == 200
        
        # Calculate statistics
        avg_time = statistics.mean(response_times)
        std_dev = statistics.stdev(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        
        print(f"Response time consistency - Avg: {avg_time:.2f}ms, "
              f"StdDev: {std_dev:.2f}ms, Min: {min_time:.2f}ms, Max: {max_time:.2f}ms")
        
        # Standard deviation should be reasonable (less than 50% of average)
        assert std_dev < avg_time * 0.5, f"Response times too inconsistent: {std_dev:.2f}ms std dev"
        
        # All responses should meet the performance requirement
        assert max_time < self.MAX_RESPONSE_TIME_MS, \
            f"Maximum response time {max_time:.2f}ms exceeds limit"