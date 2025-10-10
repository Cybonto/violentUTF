# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Validation Service for Issue #280 Asset Management System.

This module provides comprehensive data validation for asset management,
including business rule validation and data quality checks.
"""

import re
from typing import List

from app.models.asset_inventory import AssetType, Environment, SecurityClassification
from app.schemas.asset_schemas import AssetCreate, ValidationResult


class ValidationService:
    """Service class for asset data validation."""

    def __init__(self) -> None:
        """Initialize the validation service."""
        self.validation_rules = self._load_validation_rules()
        self._current_warnings = []

    def _load_validation_rules(self) -> dict:
        """Load validation rules configuration.

        Returns:
            Dictionary of validation rules
        """
        return {
            "min_name_length": 3,
            "max_name_length": 255,
            "max_description_length": 2000,
            "required_production_backup": True,
            "restricted_encryption_required": True,
            "email_pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        }

    async def validate_asset_data(self, asset_data: AssetCreate) -> ValidationResult:
        """Comprehensive asset data validation.

        Args:
            asset_data: Asset data to validate

        Returns:
            Validation result with errors and warnings
        """
        errors: List[str] = []
        warnings: List[str] = []

        # Required field validation
        errors.extend(self._validate_required_fields(asset_data))

        # Security classification validation
        errors.extend(self._validate_security_classification_rules(asset_data))

        # Environment consistency validation
        validation_result = self._validate_environment_consistency(asset_data)
        errors.extend(validation_result["errors"])
        warnings.extend(validation_result["warnings"])

        # Technical validation
        errors.extend(self._validate_technical_fields(asset_data))

        # Contact validation
        errors.extend(self._validate_contacts(asset_data))

        # Business rule validation
        errors.extend(self._validate_business_rules(asset_data))

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _validate_required_fields(self, asset_data: AssetCreate) -> List[str]:
        """Validate required fields.

        Args:
            asset_data: Asset data to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Name validation
        if not asset_data.name or len(asset_data.name.strip()) < self.validation_rules["min_name_length"]:
            errors.append(f"Asset name must be at least {self.validation_rules['min_name_length']} characters")

        if asset_data.name and len(asset_data.name) > self.validation_rules["max_name_length"]:
            errors.append(f"Asset name must not exceed {self.validation_rules['max_name_length']} characters")

        # Location validation
        if not asset_data.location or not asset_data.location.strip():
            errors.append("Asset location is required")

        # Unique identifier validation
        if not asset_data.unique_identifier or not asset_data.unique_identifier.strip():
            errors.append("Unique identifier is required")

        # Discovery method validation
        if not asset_data.discovery_method or not asset_data.discovery_method.strip():
            errors.append("Discovery method is required")

        return errors

    def _validate_security_classification_rules(self, asset_data: AssetCreate) -> List[str]:
        """Validate security classification rules.

        Args:
            asset_data: Asset data to validate

        Returns:
            List of validation errors
        """
        errors = []

        if asset_data.security_classification == SecurityClassification.RESTRICTED:
            if not asset_data.encryption_enabled:
                errors.append("Restricted assets must have encryption enabled")

            if not asset_data.technical_contact:
                errors.append("Restricted assets must have a technical contact")

            if asset_data.access_restricted is False:
                errors.append("Restricted assets must have access restrictions enabled")

        return errors

    def _validate_environment_consistency(self, asset_data: AssetCreate) -> dict:
        """Validate environment consistency rules.

        Args:
            asset_data: Asset data to validate

        Returns:
            Dictionary with errors and warnings
        """
        errors = []
        warnings = []

        if asset_data.environment == Environment.PRODUCTION:
            # Production assets should have backup configured
            if not asset_data.backup_configured:
                errors.append("Production assets must have backup configured")

            # Production assets should not be classified as public
            if asset_data.security_classification == SecurityClassification.PUBLIC:
                warnings.append("Production assets should not be classified as public")

            # Production assets should have technical contact
            if not asset_data.technical_contact:
                warnings.append("Production assets should have a technical contact")

            # Production assets should have business contact
            if not asset_data.business_contact:
                warnings.append("Production assets should have a business contact")

        elif asset_data.environment == Environment.DEVELOPMENT:
            # Development assets with high criticality should be reviewed
            from app.models.asset_inventory import CriticalityLevel

            if asset_data.criticality_level in [CriticalityLevel.HIGH, CriticalityLevel.CRITICAL]:
                warnings.append("Development assets with high criticality should be reviewed")

        return {"errors": errors, "warnings": warnings}

    def _validate_technical_fields(self, asset_data: AssetCreate) -> List[str]:
        """Validate technical fields based on asset type.

        Args:
            asset_data: Asset data to validate

        Returns:
            List of validation errors
        """
        errors = []

        # PostgreSQL-specific validation
        if asset_data.asset_type == AssetType.POSTGRESQL:
            if asset_data.connection_string and not self._validate_postgres_connection_string(
                asset_data.connection_string
            ):
                errors.append("Invalid PostgreSQL connection string format")

        # SQLite-specific validation
        elif asset_data.asset_type == AssetType.SQLITE:
            if asset_data.file_path and not asset_data.file_path.endswith((".db", ".sqlite", ".sqlite3")):
                warnings = getattr(self, "_current_warnings", [])
                warnings.append("SQLite file should typically have .db, .sqlite, or .sqlite3 extension")
                self._current_warnings = warnings

        # File storage validation
        elif asset_data.asset_type == AssetType.FILE_STORAGE:
            if not asset_data.file_path:
                errors.append("File storage assets must have a file path specified")

        # Size validation
        if asset_data.estimated_size_mb is not None and asset_data.estimated_size_mb < 0:
            errors.append("Estimated size cannot be negative")

        # Table count validation
        if asset_data.table_count is not None and asset_data.table_count < 0:
            errors.append("Table count cannot be negative")

        return errors

    def _validate_contacts(self, asset_data: AssetCreate) -> List[str]:
        """Validate contact information.

        Args:
            asset_data: Asset data to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Technical contact email validation
        if asset_data.technical_contact:
            if not self._validate_email_format(asset_data.technical_contact):
                errors.append("Technical contact must be a valid email address")

        # Business contact email validation
        if asset_data.business_contact:
            if not self._validate_email_format(asset_data.business_contact):
                errors.append("Business contact must be a valid email address")

        return errors

    def _validate_business_rules(self, asset_data: AssetCreate) -> List[str]:
        """Validate business-specific rules.

        Args:
            asset_data: Asset data to validate

        Returns:
            List of validation errors
        """
        errors = []

        # High criticality assets should have documentation
        from app.models.asset_inventory import CriticalityLevel

        if asset_data.criticality_level == CriticalityLevel.CRITICAL:
            if not asset_data.documentation_url:
                errors.append("Critical assets should have documentation URL")

            if not asset_data.purpose_description:
                errors.append("Critical assets should have a purpose description")

        # Confidence score validation
        if asset_data.confidence_score < 50:
            errors.append("Asset confidence score is too low (minimum 50)")

        return errors

    def _validate_postgres_connection_string(self, connection_string: str) -> bool:
        """Validate PostgreSQL connection string format.

        Args:
            connection_string: Connection string to validate

        Returns:
            True if valid, False otherwise
        """
        # Basic PostgreSQL connection string pattern
        # postgresql://[user[:password]@][netloc][:port][/dbname][?param1=value1&...]
        postgres_pattern = r"^postgresql://(?:[^:]+(?::[^@]*)?@)?[^:/]+(?::\d+)?(?:/[^?]*)?(?:\?.*)?$"
        return bool(re.match(postgres_pattern, connection_string))

    def _validate_email_format(self, email: str) -> bool:
        """Validate email format.

        Args:
            email: Email address to validate

        Returns:
            True if valid, False otherwise
        """
        return bool(re.match(self.validation_rules["email_pattern"], email))

    def _validate_url_format(self, url: str) -> bool:
        """Validate URL format.

        Args:
            url: URL to validate

        Returns:
            True if valid, False otherwise
        """
        url_pattern = r"^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$"
        return bool(re.match(url_pattern, url))

    async def validate_batch(self, assets: List[AssetCreate]) -> dict:
        """Validate a batch of assets.

        Args:
            assets: List of assets to validate

        Returns:
            Dictionary with validation results
        """
        results = {"valid_count": 0, "invalid_count": 0, "validation_errors": {}, "validation_warnings": {}}

        for asset in assets:
            validation_result = await self.validate_asset_data(asset)

            if validation_result.is_valid:
                results["valid_count"] += 1
            else:
                results["invalid_count"] += 1
                results["validation_errors"][asset.unique_identifier] = validation_result.errors

            if validation_result.warnings:
                results["validation_warnings"][asset.unique_identifier] = validation_result.warnings

        return results

    def get_validation_rules(self) -> dict:
        """Get current validation rules.

        Returns:
            Dictionary of validation rules
        """
        return self.validation_rules.copy()

    def update_validation_rules(self, new_rules: dict) -> None:
        """Update validation rules.

        Args:
            new_rules: New validation rules to apply
        """
        self.validation_rules.update(new_rules)
