# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Conflict Resolution Service for Issue #280 Asset Management System.

This module provides sophisticated conflict detection and resolution for asset management,
including duplicate detection, similarity scoring, and automated resolution strategies.
"""

import difflib
from typing import List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset_inventory import DatabaseAsset
from app.schemas.asset_schemas import (
    AssetCreate,
    ConflictCandidate,
    ConflictResolution,
    ConflictType,
    ResolutionAction,
)


class ConflictResolutionService:
    """Service class for asset conflict detection and resolution."""

    def __init__(self, db: AsyncSession, similarity_threshold: float = 0.85) -> None:
        """Initialize the conflict resolution service.

        Args:
            db: Database session
            similarity_threshold: Minimum similarity score for potential conflicts
        """
        self.db = db
        self.similarity_threshold = similarity_threshold

    async def detect_conflicts(self, new_asset: AssetCreate) -> List[ConflictCandidate]:
        """Detect potential conflicts with existing assets.

        Args:
            new_asset: New asset data to check for conflicts

        Returns:
            List of conflict candidates sorted by confidence score
        """
        candidates = []

        # Check for exact identifier match
        exact_match = await self._find_exact_identifier_match(new_asset.unique_identifier)
        if exact_match:
            candidates.append(
                ConflictCandidate(
                    existing_asset_id=exact_match.id,
                    conflict_type=ConflictType.EXACT_IDENTIFIER,
                    confidence_score=1.0,
                    details={
                        "existing_name": exact_match.name,
                        "existing_location": exact_match.location,
                        "match_reason": "Exact unique identifier match",
                    },
                )
            )

        # Check for similar assets using fuzzy matching
        similar_assets = await self._find_similar_assets(new_asset)
        for asset in similar_assets:
            similarity_score = self._calculate_similarity_score(new_asset, asset)
            if similarity_score >= self.similarity_threshold:
                candidates.append(
                    ConflictCandidate(
                        existing_asset_id=asset.id,
                        conflict_type=ConflictType.SIMILAR_ATTRIBUTES,
                        confidence_score=similarity_score,
                        details={
                            "existing_name": asset.name,
                            "existing_location": asset.location,
                            "similarity_factors": self._get_similarity_factors(new_asset, asset),
                            "match_reason": f"High similarity score: {similarity_score:.2f}",
                        },
                    )
                )

        # Check for location overlap
        location_conflicts = await self._find_location_conflicts(new_asset)
        for asset in location_conflicts:
            if not any(c.existing_asset_id == asset.id for c in candidates):
                candidates.append(
                    ConflictCandidate(
                        existing_asset_id=asset.id,
                        conflict_type=ConflictType.LOCATION_OVERLAP,
                        confidence_score=0.8,
                        details={
                            "existing_name": asset.name,
                            "existing_location": asset.location,
                            "match_reason": "Location overlap detected",
                        },
                    )
                )

        # Sort by confidence score (highest first)
        return sorted(candidates, key=lambda x: x.confidence_score, reverse=True)

    def resolve_conflict_automatically(self, conflict: ConflictCandidate, new_asset: AssetCreate) -> ConflictResolution:
        """Attempt automatic conflict resolution based on rules.

        Args:
            conflict: Conflict candidate to resolve
            new_asset: New asset data

        Returns:
            Conflict resolution recommendation
        """
        if conflict.conflict_type == ConflictType.EXACT_IDENTIFIER and conflict.confidence_score >= 0.95:
            # High confidence exact match - recommend merge
            return ConflictResolution(
                action=ResolutionAction.MERGE,
                automatic=True,
                reason="Exact identifier match with high confidence",
                metadata={
                    "merge_strategy": "update_existing",
                    "priority_fields": ["confidence_score", "last_modified", "discovery_timestamp"],
                },
            )

        elif conflict.confidence_score >= 0.95:
            # Very high similarity - recommend update existing
            return ConflictResolution(
                action=ResolutionAction.UPDATE_EXISTING,
                automatic=True,
                reason="Very high similarity suggests same asset with updated information",
                metadata={"update_strategy": "selective_update", "confidence_threshold": conflict.confidence_score},
            )

        elif conflict.confidence_score >= 0.90:
            # High similarity - require manual review
            return ConflictResolution(
                action=ResolutionAction.MANUAL_REVIEW,
                automatic=False,
                reason="High similarity requires manual review to determine appropriate action",
                metadata={
                    "review_priority": "high",
                    "suggested_actions": ["merge", "update_existing", "create_separate"],
                },
            )

        elif conflict.confidence_score >= self.similarity_threshold:
            # Medium similarity - flag for review but allow creation
            return ConflictResolution(
                action=ResolutionAction.CREATE_SEPARATE,
                automatic=True,
                reason="Medium similarity confidence, creating as separate asset with review flag",
                metadata={"review_flag": True, "review_priority": "medium"},
            )

        else:
            # Low similarity - create as separate asset
            return ConflictResolution(
                action=ResolutionAction.CREATE_SEPARATE,
                automatic=True,
                reason="Low similarity confidence, treating as separate asset",
                metadata={"review_flag": False},
            )

    async def _find_exact_identifier_match(self, unique_identifier: str) -> Optional[DatabaseAsset]:
        """Find asset with exact unique identifier match.

        Args:
            unique_identifier: Unique identifier to search for

        Returns:
            Existing asset if found, None otherwise
        """
        result = await self.db.execute(
            select(DatabaseAsset).where(
                and_(DatabaseAsset.unique_identifier == unique_identifier, DatabaseAsset.is_deleted.is_(False))
            )
        )
        return result.scalar_one_or_none()

    async def _find_similar_assets(self, new_asset: AssetCreate) -> List[DatabaseAsset]:
        """Find assets with similar attributes.

        Args:
            new_asset: New asset to compare against

        Returns:
            List of potentially similar assets
        """
        # Search for assets with similar names, types, or locations
        name_similarity = f"%{new_asset.name.split()[0]}%" if new_asset.name else "%"
        location_similarity = f"%{new_asset.location.split('.')[0]}%" if new_asset.location else "%"

        result = await self.db.execute(
            select(DatabaseAsset).where(
                and_(
                    DatabaseAsset.is_deleted.is_(False),
                    or_(
                        # Same asset type and similar location
                        and_(
                            DatabaseAsset.asset_type == new_asset.asset_type,
                            DatabaseAsset.location.ilike(location_similarity),
                        ),
                        # Similar name and same asset type
                        and_(
                            DatabaseAsset.name.ilike(name_similarity), DatabaseAsset.asset_type == new_asset.asset_type
                        ),
                        # Exact location match
                        DatabaseAsset.location == new_asset.location,
                    ),
                )
            )
        )
        return result.scalars().all()

    async def _find_location_conflicts(self, new_asset: AssetCreate) -> List[DatabaseAsset]:
        """Find assets with overlapping locations.

        Args:
            new_asset: New asset to check for location conflicts

        Returns:
            List of assets with location conflicts
        """
        # Check for same file path (for file-based assets)
        if new_asset.file_path:
            result = await self.db.execute(
                select(DatabaseAsset).where(
                    and_(DatabaseAsset.file_path == new_asset.file_path, DatabaseAsset.is_deleted.is_(False))
                )
            )
            return result.scalars().all()

        # Check for same network location
        if new_asset.network_location:
            result = await self.db.execute(
                select(DatabaseAsset).where(
                    and_(
                        DatabaseAsset.network_location == new_asset.network_location,
                        DatabaseAsset.is_deleted.is_(False),
                    )
                )
            )
            return result.scalars().all()

        return []

    def _calculate_similarity_score(self, new_asset: AssetCreate, existing_asset: DatabaseAsset) -> float:
        """Calculate similarity score between two assets.

        Args:
            new_asset: New asset data
            existing_asset: Existing asset from database

        Returns:
            Similarity score between 0.0 and 1.0
        """
        scores = []
        weights = []

        # Name similarity (weight: 0.3)
        if new_asset.name and existing_asset.name:
            name_similarity = difflib.SequenceMatcher(None, new_asset.name.lower(), existing_asset.name.lower()).ratio()
            scores.append(name_similarity)
            weights.append(0.3)

        # Location similarity (weight: 0.25)
        if new_asset.location and existing_asset.location:
            location_similarity = difflib.SequenceMatcher(
                None, new_asset.location.lower(), existing_asset.location.lower()
            ).ratio()
            scores.append(location_similarity)
            weights.append(0.25)

        # Asset type match (weight: 0.2)
        if new_asset.asset_type == existing_asset.asset_type:
            scores.append(1.0)
        else:
            scores.append(0.0)
        weights.append(0.2)

        # Environment match (weight: 0.1)
        if new_asset.environment == existing_asset.environment:
            scores.append(1.0)
        else:
            scores.append(0.5)  # Partial score for different environments
        weights.append(0.1)

        # Technical metadata similarity (weight: 0.15)
        tech_score = 0.0
        tech_factors = 0

        if new_asset.database_version and existing_asset.database_version:
            if new_asset.database_version == existing_asset.database_version:
                tech_score += 1.0
            tech_factors += 1

        if new_asset.estimated_size_mb and existing_asset.estimated_size_mb:
            # Size similarity within 20% tolerance
            size_diff = abs(new_asset.estimated_size_mb - existing_asset.estimated_size_mb)
            max_size = max(new_asset.estimated_size_mb, existing_asset.estimated_size_mb)
            if max_size > 0:
                size_similarity = max(0, 1 - (size_diff / (max_size * 0.2)))
                tech_score += size_similarity
            tech_factors += 1

        if tech_factors > 0:
            scores.append(tech_score / tech_factors)
            weights.append(0.15)

        # Calculate weighted average
        if scores and weights:
            total_weight = sum(weights)
            weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
            return weighted_sum / total_weight

        return 0.0

    def _get_similarity_factors(self, new_asset: AssetCreate, existing_asset: DatabaseAsset) -> dict:
        """Get detailed similarity factors for analysis.

        Args:
            new_asset: New asset data
            existing_asset: Existing asset from database

        Returns:
            Dictionary with similarity factor details
        """
        factors = {}

        # Name similarity
        if new_asset.name and existing_asset.name:
            name_similarity = difflib.SequenceMatcher(None, new_asset.name.lower(), existing_asset.name.lower()).ratio()
            factors["name_similarity"] = round(name_similarity, 3)

        # Location similarity
        if new_asset.location and existing_asset.location:
            location_similarity = difflib.SequenceMatcher(
                None, new_asset.location.lower(), existing_asset.location.lower()
            ).ratio()
            factors["location_similarity"] = round(location_similarity, 3)

        # Exact matches
        factors["asset_type_match"] = new_asset.asset_type == existing_asset.asset_type
        factors["environment_match"] = new_asset.environment == existing_asset.environment

        # Technical metadata
        if new_asset.database_version and existing_asset.database_version:
            factors["version_match"] = new_asset.database_version == existing_asset.database_version

        return factors

    async def get_conflict_statistics(self) -> dict:
        """Get conflict detection statistics.

        Returns:
            Dictionary with conflict statistics
        """
        # This would be implemented to provide analytics
        # on conflict detection patterns and resolution success rates
        return {
            "total_conflicts_detected": 0,
            "automatic_resolutions": 0,
            "manual_reviews_required": 0,
            "average_similarity_score": 0.0,
            "common_conflict_types": [],
        }

    def configure_similarity_threshold(self, threshold: float) -> None:
        """Configure similarity threshold for conflict detection.

        Args:
            threshold: New similarity threshold (0.0 to 1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self.similarity_threshold = threshold
        else:
            raise ValueError("Similarity threshold must be between 0.0 and 1.0")

    def get_resolution_recommendations(self, conflicts: List[ConflictCandidate]) -> List[ConflictResolution]:
        """Get resolution recommendations for multiple conflicts.

        Args:
            conflicts: List of conflict candidates

        Returns:
            List of resolution recommendations
        """
        return [self.resolve_conflict_automatically(conflict, None) for conflict in conflicts]
