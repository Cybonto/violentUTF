# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Discovery Integration Service for Issue #280 Asset Management System.

This module provides integration with Issue #279 discovery system,
enabling automated asset registration and data synchronization.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from app.models.asset_inventory import AssetType, CriticalityLevel, DatabaseAsset, Environment, SecurityClassification
from app.schemas.asset_schemas import (
    AssetCreate,
    DiscoveredAsset,
    DiscoveryReport,
    ImportResult,
)
from app.services.asset_management.asset_service import AssetService
from app.services.asset_management.validation_service import ValidationService


class DiscoveryIntegrationService:
    """Service class for discovery system integration."""

    def __init__(self, asset_service: AssetService, validation_service: ValidationService) -> None:
        """Initialize the discovery integration service.

        Args:
            asset_service: Asset service for CRUD operations
            validation_service: Validation service for data quality
        """
        self.asset_service = asset_service
        self.validation_service = validation_service

    async def process_discovery_report(self, discovery_report: DiscoveryReport) -> ImportResult:
        """Process discovery report and create/update assets.

        Args:
            discovery_report: Discovery report from external system

        Returns:
            Import result with statistics and errors
        """
        start_time = datetime.now(timezone.utc)
        results = ImportResult(
            created_count=0,
            updated_count=0,
            error_count=0,
            skipped_count=0,
            conflicts=[],
            errors={},
            processing_duration=0.0,
        )

        for discovered_asset in discovery_report.assets:
            try:
                # Map discovery data to asset schema
                asset_data = self.map_discovery_to_asset(discovered_asset)

                # Validate asset data
                validation_result = await self.validation_service.validate_asset_data(asset_data)
                if not validation_result.is_valid:
                    results.error_count += 1
                    results.errors[discovered_asset.identifier] = validation_result.errors
                    continue

                # Check for existing asset
                existing_asset = await self.asset_service.find_by_identifier(asset_data.unique_identifier)

                if existing_asset:
                    # Determine if we should update the existing asset
                    if self.should_update_asset(existing_asset, discovered_asset):
                        await self.asset_service.update_from_discovery(
                            existing_asset.id, asset_data, discovered_asset.metadata
                        )
                        results.updated_count += 1
                    else:
                        results.skipped_count += 1
                else:
                    # Create new asset
                    await self.asset_service.create_asset(asset_data, created_by="discovery-system")
                    results.created_count += 1

            except Exception as e:
                results.error_count += 1
                results.errors[discovered_asset.identifier] = [str(e)]

        # Calculate processing duration
        end_time = datetime.now(timezone.utc)
        results.processing_duration = (end_time - start_time).total_seconds()

        return results

    def map_discovery_to_asset(self, discovered_asset: DiscoveredAsset) -> AssetCreate:
        """Map discovery data to asset creation schema.

        Args:
            discovered_asset: Discovered asset data

        Returns:
            Asset creation data
        """
        # Map asset type from discovery type
        asset_type = self._map_asset_type(discovered_asset.type)

        # Infer security classification based on discovery metadata
        security_classification = self._infer_security_classification(discovered_asset)

        # Infer criticality level based on discovery metadata
        criticality_level = self._infer_criticality_level(discovered_asset)

        # Infer environment based on location or metadata
        environment = self._infer_environment(discovered_asset)

        # Extract technical metadata
        estimated_size_mb = discovered_asset.metadata.get("size_mb")
        table_count = discovered_asset.metadata.get("table_count")
        database_version = discovered_asset.metadata.get("version")

        # Create asset data
        asset_data = AssetCreate(
            name=discovered_asset.name,
            asset_type=asset_type,
            unique_identifier=discovered_asset.identifier,
            location=discovered_asset.location,
            security_classification=security_classification,
            criticality_level=criticality_level,
            environment=environment,
            discovery_method="automated_discovery",
            confidence_score=discovered_asset.confidence,
            estimated_size_mb=estimated_size_mb,
            table_count=table_count,
            database_version=database_version,
            # Additional metadata from discovery
            connection_string=discovered_asset.metadata.get("connection_string"),
            network_location=discovered_asset.metadata.get("network_location"),
            file_path=discovered_asset.metadata.get("file_path"),
            encryption_enabled=discovered_asset.metadata.get("encryption_enabled", False),
            backup_configured=discovered_asset.metadata.get("backup_configured", False),
            compliance_requirements=discovered_asset.metadata.get("compliance_requirements"),
        )

        return asset_data

    def should_update_asset(self, existing_asset: DatabaseAsset, discovered_asset: DiscoveredAsset) -> bool:
        """Determine if existing asset should be updated with discovery data.

        Args:
            existing_asset: Existing asset from database
            discovered_asset: Newly discovered asset data

        Returns:
            True if asset should be updated, False otherwise
        """
        # Update if discovery is more recent
        if hasattr(existing_asset, "discovery_timestamp"):
            if discovered_asset.discovery_timestamp > existing_asset.discovery_timestamp:
                return True

        # Update if discovery has higher confidence
        if hasattr(existing_asset, "confidence_score"):
            if discovered_asset.confidence > existing_asset.confidence_score:
                return True

        # Update if significant new metadata is available
        if self._has_significant_new_metadata(existing_asset, discovered_asset):
            return True

        return False

    def _map_asset_type(self, discovery_type: str) -> AssetType:
        """Map discovery asset type to internal asset type.

        Args:
            discovery_type: Asset type from discovery system

        Returns:
            Mapped asset type
        """
        type_mapping = {
            "postgresql": AssetType.POSTGRESQL,
            "postgres": AssetType.POSTGRESQL,
            "sqlite": AssetType.SQLITE,
            "duckdb": AssetType.DUCKDB,
            "file": AssetType.FILE_STORAGE,
            "config": AssetType.CONFIGURATION,
            "configuration": AssetType.CONFIGURATION,
        }

        return type_mapping.get(discovery_type.lower(), AssetType.FILE_STORAGE)

    def _infer_security_classification(self, discovered_asset: DiscoveredAsset) -> SecurityClassification:
        """Infer security classification from discovery data.

        Args:
            discovered_asset: Discovered asset data

        Returns:
            Inferred security classification
        """
        # Check for explicit classification in metadata
        if "security_classification" in discovered_asset.metadata:
            classification = discovered_asset.metadata["security_classification"].upper()
            try:
                return SecurityClassification(classification)
            except ValueError:
                pass

        # Infer from location or name patterns
        location_lower = discovered_asset.location.lower()
        name_lower = discovered_asset.name.lower()

        # Production or customer data suggests higher classification
        if any(
            keyword in location_lower or keyword in name_lower
            for keyword in ["prod", "production", "customer", "client", "private"]
        ):
            return SecurityClassification.CONFIDENTIAL

        # Development or test data is typically internal
        if any(
            keyword in location_lower or keyword in name_lower for keyword in ["dev", "development", "test", "staging"]
        ):
            return SecurityClassification.INTERNAL

        # Default to internal for discovered assets
        return SecurityClassification.INTERNAL

    def _infer_criticality_level(self, discovered_asset: DiscoveredAsset) -> CriticalityLevel:
        """Infer criticality level from discovery data.

        Args:
            discovered_asset: Discovered asset data

        Returns:
            Inferred criticality level
        """
        # Check for explicit criticality in metadata
        if "criticality" in discovered_asset.metadata:
            criticality = discovered_asset.metadata["criticality"].upper()
            try:
                return CriticalityLevel(criticality)
            except ValueError:
                pass

        location_lower = discovered_asset.location.lower()
        name_lower = discovered_asset.name.lower()

        # Production databases are typically high criticality
        if any(
            keyword in location_lower or keyword in name_lower for keyword in ["prod", "production", "customer", "main"]
        ):
            return CriticalityLevel.HIGH

        # Large databases might be more critical
        size_mb = discovered_asset.metadata.get("size_mb", 0)
        if size_mb and size_mb > 10000:  # 10GB+
            return CriticalityLevel.HIGH
        elif size_mb and size_mb > 1000:  # 1GB+
            return CriticalityLevel.MEDIUM

        # Default to medium criticality
        return CriticalityLevel.MEDIUM

    def _infer_environment(self, discovered_asset: DiscoveredAsset) -> Environment:
        """Infer environment from discovery data.

        Args:
            discovered_asset: Discovered asset data

        Returns:
            Inferred environment
        """
        # Check for explicit environment in metadata
        if "environment" in discovered_asset.metadata:
            env = discovered_asset.metadata["environment"].upper()
            try:
                return Environment(env)
            except ValueError:
                pass

        location_lower = discovered_asset.location.lower()
        name_lower = discovered_asset.name.lower()

        # Environment inference from location/name patterns
        if any(keyword in location_lower or keyword in name_lower for keyword in ["prod", "production"]):
            return Environment.PRODUCTION
        elif any(keyword in location_lower or keyword in name_lower for keyword in ["staging", "stage"]):
            return Environment.STAGING
        elif any(keyword in location_lower or keyword in name_lower for keyword in ["test", "testing"]):
            return Environment.TESTING
        elif any(keyword in location_lower or keyword in name_lower for keyword in ["dev", "development"]):
            return Environment.DEVELOPMENT

        # Default to development for discovered assets
        return Environment.DEVELOPMENT

    def _has_significant_new_metadata(self, existing_asset: DatabaseAsset, discovered_asset: DiscoveredAsset) -> bool:
        """Check if discovery has significant new metadata.

        Args:
            existing_asset: Existing asset from database
            discovered_asset: Newly discovered asset data

        Returns:
            True if significant new metadata is available
        """
        # Check for new size information
        new_size = discovered_asset.metadata.get("size_mb")
        if new_size and (not hasattr(existing_asset, "estimated_size_mb") or not existing_asset.estimated_size_mb):
            return True

        # Check for new version information
        new_version = discovered_asset.metadata.get("version")
        if new_version and (not hasattr(existing_asset, "database_version") or not existing_asset.database_version):
            return True

        # Check for new connection information
        new_connection = discovered_asset.metadata.get("connection_string")
        if new_connection and (
            not hasattr(existing_asset, "connection_string") or not existing_asset.connection_string
        ):
            return True

        return False

    async def validate_discovery_data(self, discovery_report: DiscoveryReport) -> dict:
        """Validate discovery report data before processing.

        Args:
            discovery_report: Discovery report to validate

        Returns:
            Validation summary
        """
        validation_summary = {
            "total_assets": len(discovery_report.assets),
            "valid_assets": 0,
            "invalid_assets": 0,
            "validation_errors": {},
            "warnings": [],
        }

        for discovered_asset in discovery_report.assets:
            try:
                asset_data = self.map_discovery_to_asset(discovered_asset)
                validation_result = await self.validation_service.validate_asset_data(asset_data)

                if validation_result.is_valid:
                    validation_summary["valid_assets"] += 1
                else:
                    validation_summary["invalid_assets"] += 1
                    validation_summary["validation_errors"][discovered_asset.identifier] = validation_result.errors

                # Add warnings
                if validation_result.warnings:
                    validation_summary["warnings"].extend(validation_result.warnings)

            except Exception as e:
                validation_summary["invalid_assets"] += 1
                validation_summary["validation_errors"][discovered_asset.identifier] = [str(e)]

        return validation_summary

    def get_discovery_statistics(self) -> dict:
        """Get discovery integration statistics.

        Returns:
            Dictionary with discovery statistics
        """
        return {
            "total_discovery_reports_processed": 0,
            "total_assets_discovered": 0,
            "total_assets_created": 0,
            "total_assets_updated": 0,
            "average_processing_time": 0.0,
            "error_rate": 0.0,
            "last_discovery_run": None,
        }

    def configure_discovery_mapping(self, mapping_config: Dict[str, Any]) -> None:
        """Configure discovery data mapping rules.

        Args:
            mapping_config: Configuration for data mapping
        """
        # This would allow customization of the mapping logic
        # Implementation would store and use custom mapping rules
        # TODO: Implement custom mapping configuration storage
