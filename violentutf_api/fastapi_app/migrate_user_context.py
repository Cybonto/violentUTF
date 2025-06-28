#!/usr/bin/env python3
"""
User Context Migration Script for ViolentUTF

This script migrates data from one user context to another to fix
the user context mismatch between Keycloak display names and account names.

Usage:
    python migrate_user_context.py --from "Tam Nguyen" --to "violentutf.web"
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.db.duckdb_manager import DuckDBManager

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
    logger.info(f"Migrating generators from '{from_user}' to '{to_user}'")

    # Get database managers for both users
    from_db = DuckDBManager(from_user)
    to_db = DuckDBManager(to_user)

    # Get generators from source user
    source_generators = from_db.list_generators()

    if not source_generators:
        logger.info(f"No generators found for user '{from_user}'")
        return 0

    logger.info(f"Found {len(source_generators)} generators to migrate")

    migrated_count = 0

    for generator in source_generators:
        try:
            # Check if generator already exists for target user
            existing = to_db.get_generator(generator["id"])
            if existing:
                logger.warning(
                    f"Generator '{generator['name']}' already exists for user '{to_user}', skipping"
                )
                continue

            # Create generator for target user
            new_id = to_db.create_generator(
                name=generator["name"],
                generator_type=generator["type"],
                parameters=generator["parameters"],
            )

            logger.info(
                f"Migrated generator '{generator['name']}' (ID: {generator['id']} -> {new_id})"
            )
            migrated_count += 1

        except Exception as e:
            logger.error(f"Failed to migrate generator '{generator['name']}': {e}")

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
    logger.info(f"Migrating datasets from '{from_user}' to '{to_user}'")

    from_db = DuckDBManager(from_user)
    to_db = DuckDBManager(to_user)

    source_datasets = from_db.list_datasets()

    if not source_datasets:
        logger.info(f"No datasets found for user '{from_user}'")
        return 0

    logger.info(f"Found {len(source_datasets)} datasets to migrate")

    migrated_count = 0

    for dataset in source_datasets:
        try:
            # Get full dataset with prompts
            full_dataset = from_db.get_dataset(dataset["id"])
            if not full_dataset:
                logger.warning(
                    f"Could not load full dataset '{dataset['name']}', skipping"
                )
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

            logger.info(
                f"Migrated dataset '{dataset['name']}' (ID: {dataset['id']} -> {new_id})"
            )
            migrated_count += 1

        except Exception as e:
            logger.error(f"Failed to migrate dataset '{dataset['name']}': {e}")

    return migrated_count


def main():
    parser = argparse.ArgumentParser(description="Migrate ViolentUTF user context data")
    parser.add_argument(
        "--from",
        dest="from_user",
        required=True,
        help="Source user context (e.g., 'Tam Nguyen')",
    )
    parser.add_argument(
        "--to",
        dest="to_user",
        required=True,
        help="Target user context (e.g., 'violentutf.web')",
    )
    parser.add_argument(
        "--generators-only", action="store_true", help="Migrate only generators"
    )
    parser.add_argument(
        "--datasets-only", action="store_true", help="Migrate only datasets"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )

    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    logger.info(f"Migration: '{args.from_user}' -> '{args.to_user}'")

    total_migrated = 0

    # Migrate generators
    if not args.datasets_only:
        if args.dry_run:
            from_db = DuckDBManager(args.from_user)
            generators = from_db.list_generators()
            logger.info(f"Would migrate {len(generators)} generators")
            for gen in generators:
                logger.info(f"  - {gen['name']} ({gen['type']})")
        else:
            migrated_generators = migrate_generators(args.from_user, args.to_user)
            total_migrated += migrated_generators
            logger.info(f"Migrated {migrated_generators} generators")

    # Migrate datasets
    if not args.generators_only:
        if args.dry_run:
            from_db = DuckDBManager(args.from_user)
            datasets = from_db.list_datasets()
            logger.info(f"Would migrate {len(datasets)} datasets")
            for ds in datasets:
                logger.info(f"  - {ds['name']} ({ds['prompt_count']} prompts)")
        else:
            migrated_datasets = migrate_datasets(args.from_user, args.to_user)
            total_migrated += migrated_datasets
            logger.info(f"Migrated {migrated_datasets} datasets")

    if not args.dry_run:
        logger.info(
            f"Migration completed successfully. Total items migrated: {total_migrated}"
        )
    else:
        logger.info(
            "Dry run completed. Use --dry-run=false to perform actual migration."
        )


if __name__ == "__main__":
    main()
