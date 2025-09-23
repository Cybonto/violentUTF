# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Database migration for dependency mapping and impact analysis tables.

This migration creates the tables needed for the dependency mapping and impact
analysis system as specified in Issue #264.
"""

from sqlalchemy.sql import text

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from db.database import get_db_session


async def migrate_up():
    """Apply the migration - create dependency mapping tables."""
    async with get_db_session() as session:
        # Create dependency_relationships table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS dependency_relationships (
                id TEXT PRIMARY KEY,
                source_service TEXT NOT NULL,
                target_service TEXT NULL,
                target_database TEXT NULL,
                dependency_type TEXT NOT NULL CHECK (dependency_type IN (
                    'database', 'service', 'api', 'authentication', 'configuration', 'network'
                )),
                criticality TEXT NOT NULL CHECK (criticality IN (
                    'critical', 'high', 'medium', 'low'
                )),
                discovery_method TEXT NOT NULL CHECK (discovery_method IN (
                    'code_analysis', 'runtime_trace', 'configuration_scan', 'manual', 'health_check'
                )),
                connection_string TEXT NULL,
                metadata_json TEXT NULL,
                last_verified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create index for source_service lookups
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_dependency_source_service 
            ON dependency_relationships(source_service)
        """))
        
        # Create index for target_service lookups
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_dependency_target_service 
            ON dependency_relationships(target_service)
        """))
        
        # Create index for target_database lookups
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_dependency_target_database 
            ON dependency_relationships(target_database)
        """))
        
        # Create service_health table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS service_health (
                id TEXT PRIMARY KEY,
                service_name TEXT NOT NULL UNIQUE,
                health_status TEXT NOT NULL CHECK (health_status IN (
                    'healthy', 'degraded', 'down', 'unknown'
                )),
                last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                response_time_ms INTEGER NULL,
                error_message TEXT NULL,
                dependencies_status TEXT NULL,
                endpoint_url TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create index for service_name lookups
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_service_health_name 
            ON service_health(service_name)
        """))
        
        # Create impact_analyses table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS impact_analyses (
                id TEXT PRIMARY KEY,
                change_description TEXT NOT NULL,
                proposed_changes TEXT NOT NULL,
                impact_assessment TEXT NOT NULL,
                risk_score INTEGER NOT NULL CHECK (risk_score >= 1 AND risk_score <= 10),
                affected_services TEXT NULL,
                rollback_plan TEXT NULL,
                deployment_sequence TEXT NULL,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                implemented BOOLEAN DEFAULT FALSE,
                implementation_date TIMESTAMP NULL,
                implementation_notes TEXT NULL
            )
        """))
        
        # Create index for created_by lookups
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_impact_analyses_created_by 
            ON impact_analyses(created_by)
        """))
        
        # Create index for implementation status
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_impact_analyses_implemented 
            ON impact_analyses(implemented)
        """))
        
        # Create dependency_matrices table
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS dependency_matrices (
                id TEXT PRIMARY KEY,
                matrix_version TEXT NOT NULL,
                matrix_data TEXT NOT NULL,
                services_snapshot TEXT NOT NULL,
                databases_snapshot TEXT NOT NULL,
                discovery_metadata TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT NOT NULL,
                is_current BOOLEAN DEFAULT FALSE
            )
        """))
        
        # Create index for matrix version lookups
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_dependency_matrices_version 
            ON dependency_matrices(matrix_version)
        """))
        
        # Create index for current matrix
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_dependency_matrices_current 
            ON dependency_matrices(is_current)
        """))
        
        await session.commit()


async def migrate_down():
    """Rollback the migration - drop dependency mapping tables."""
    async with get_db_session() as session:
        # Drop tables in reverse order to avoid foreign key issues
        await session.execute(text("DROP TABLE IF EXISTS dependency_matrices"))
        await session.execute(text("DROP TABLE IF EXISTS impact_analyses"))
        await session.execute(text("DROP TABLE IF EXISTS service_health"))
        await session.execute(text("DROP TABLE IF EXISTS dependency_relationships"))
        
        await session.commit()


async def check_migration_needed():
    """Check if this migration needs to be applied."""
    async with get_db_session() as session:
        try:
            # Check if dependency_relationships table exists
            result = await session.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='dependency_relationships'
            """))
            return result.fetchone() is None
        except Exception:
            return True


if __name__ == "__main__":
    import asyncio
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    async def main():
        """Run the migration."""
        if await check_migration_needed():
            logger.info("Running dependency mapping tables migration...")
            await migrate_up()
            logger.info("Migration completed successfully")
        else:
            logger.info("Migration already applied - dependency mapping tables exist")
    
    asyncio.run(main())