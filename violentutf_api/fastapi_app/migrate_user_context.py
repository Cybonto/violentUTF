#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
User Context Migration Script for ViolentUTF

This script migrates data from one user context to another to fix
the user context mismatch between Keycloak display names and account names.

Usage:
    python migrate_user_context.py --from "Tam Nguyen" --to "violentutf.web"
"""

import argparse
import logging
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.db.duckdb_manager import DuckDBManager  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_generators(from_user: str, to_user: str) -> int:
    """
    Migrate generators from one user context to another

    Args:
        from_user: Source user context (e.g., "Tam Nguyen")
        to_user: Target user context (e.g., "violentutf.web")

    Returns:
        Number of generators migrated
    """
    logger.info("Migrating generators from '%s' to '%s'", from_user, to_user)

    # Get database managers for both users
    from_db = DuckDBManager(from_user)
    to_db = DuckDBManager(to_user)

    # Get generators from source user
    source_generators = from_db.list_generators()

    if not source_generators:
        logger.info("No generators found for user '%s'", from_user)
        return 0

    logger.info("Found %d generators to migrate", len(source_generators))

    migrated_count = 0

    for generator in source_generators:
        try:
            # Check if generator already exists for target user
            existing = to_db.get_generator(generator["id"])
            if existing:
                logger.warning("Generator '%s' already exists for user '%s', skipping", generator["name"], to_user)
                continue

            # Create generator for target user
            new_id = to_db.create_generator(
                name=generator["name"], generator_type=generator["type"], parameters=generator["parameters"]
            )

            logger.info("Migrated generator '%s' (ID: %s -> %s)", generator["name"], generator["id"], new_id)
            migrated_count += 1

        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Failed to migrate generator '%s': %s", generator["name"], e)
        except (OSError, IOError, TypeError) as e:
            logger.error("Unexpected error migrating generator '%s': %s", generator["name"], e)

    return migrated_count


def migrate_datasets(from_user: str, to_user: str) -> int:
    """
    Migrate datasets from one user context to another

    Args:
        from_user: Source user context
        to_user: Target user context

    Returns:
        Number of datasets migrated
    """
    logger.info("Migrating datasets from '%s' to '%s'", from_user, to_user)

    from_db = DuckDBManager(from_user)
    to_db = DuckDBManager(to_user)

    source_datasets = from_db.list_datasets()

    if not source_datasets:
        logger.info("No datasets found for user '%s'", from_user)
        return 0

    logger.info("Found %d datasets to migrate", len(source_datasets))

    migrated_count = 0

    for dataset in source_datasets:
        try:
            # Get full dataset with prompts
            full_dataset = from_db.get_dataset(dataset["id"])
            if not full_dataset:
                logger.warning("Could not load full dataset '%s', skipping", dataset["name"])
                continue

            # Extract prompts
            prompts = [prompt["text"] for prompt in full_dataset["prompts"]]

            # Create dataset for target user
            new_id = to_db.create_dataset(
                name=dataset["name"],
                source_type=dataset["source_type"],
                configuration=dataset["configuration"],
                prompts=prompts,
            )

            logger.info("Migrated dataset '%s' (ID: %s -> %s)", dataset["name"], dataset["id"], new_id)
            migrated_count += 1

        except (ValueError, KeyError, AttributeError) as e:
            logger.error("Failed to migrate dataset '%s': %s", dataset["name"], e)
        except (OSError, IOError, TypeError) as e:
            logger.error("Unexpected error migrating dataset '%s': %s", dataset["name"], e)

    return migrated_count


def main():
    parser = argparse.ArgumentParser(description="Migrate ViolentUTF user context data")
    parser.add_argument("--from", dest="from_user", required=True, help="Source user context (e.g., 'Tam Nguyen')")
    parser.add_argument("--to", dest="to_user", required=True, help="Target user context (e.g., 'violentutf.web')")
    parser.add_argument("--generators-only", action="store_true", help="Migrate only generators")
    parser.add_argument("--datasets-only", action="store_true", help="Migrate only datasets")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without making changes")

    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    logger.info("Migration: '%s' -> '%s'", args.from_user, args.to_user)

    total_migrated = 0

    # Migrate generators
    if not args.datasets_only:
        if args.dry_run:
            from_db = DuckDBManager(args.from_user)
            generators = from_db.list_generators()
            logger.info("Would migrate %d generators", len(generators))
            for gen in generators:
                logger.info("  - %s (%s)", gen["name"], gen["type"])
        else:
            migrated_generators = migrate_generators(args.from_user, args.to_user)
            total_migrated += migrated_generators
            logger.info("Migrated %d generators", migrated_generators)

    # Migrate datasets
    if not args.generators_only:
        if args.dry_run:
            from_db = DuckDBManager(args.from_user)
            datasets = from_db.list_datasets()
            logger.info("Would migrate %d datasets", len(datasets))
            for ds in datasets:
                logger.info("  - %s (%s prompts)", ds["name"], ds["prompt_count"])
        else:
            migrated_datasets = migrate_datasets(args.from_user, args.to_user)
            total_migrated += migrated_datasets
            logger.info("Migrated %d datasets", migrated_datasets)

    if not args.dry_run:
        logger.info("Migration completed successfully. Total items migrated: %d", total_migrated)
    else:
        logger.info("Dry run completed. Use --dry-run=false to perform actual migration.")


if __name__ == "__main__":
    main()
