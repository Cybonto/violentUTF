#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""PostgreSQL Configuration Extraction Script for Issue #265.

This script extracts PostgreSQL configuration from Keycloak Docker Compose files
and creates configuration baselines for drift detection.
"""

import json
import logging
import os
import subprocess  # nosec B404
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

# Add the FastAPI app to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent / "violentutf_api" / "fastapi_app"))

try:
    from app.services.config_monitoring import ConfigurationMonitoringService
except ImportError as e:
    print(f"Warning: Could not import configuration monitoring service: {e}")
    ConfigurationMonitoringService = None

logger = logging.getLogger(__name__)


class PostgreSQLConfigExtractor:
    """Extract PostgreSQL configuration from Docker Compose and container environment."""

    def __init__(self, keycloak_dir: str = "./keycloak") -> None:
        """Initialize the extractor.

        Args:
            keycloak_dir: Path to the Keycloak directory containing docker-compose.yml
        """
        self.keycloak_dir = Path(keycloak_dir)
        self.docker_compose_path = self.keycloak_dir / "docker-compose.yml"

    def extract_docker_compose_config(self) -> Dict[str, Any]:
        """Extract PostgreSQL configuration from docker-compose.yml.

        Returns:
            Dictionary containing PostgreSQL configuration
        """
        if not self.docker_compose_path.exists():
            raise FileNotFoundError(f"Docker Compose file not found: {self.docker_compose_path}")

        with open(self.docker_compose_path, "r", encoding="utf-8") as f:
            compose_config = yaml.safe_load(f)

        # Extract PostgreSQL service configuration
        postgres_config = {}
        keycloak_config = {}

        if "services" in compose_config:
            # PostgreSQL service configuration
            if "postgres" in compose_config["services"]:
                postgres_service = compose_config["services"]["postgres"]
                postgres_config.update(
                    {
                        "image": postgres_service.get("image"),
                        "environment": postgres_service.get("environment", {}),
                        "volumes": postgres_service.get("volumes", []),
                        "ports": postgres_service.get("ports", []),
                        "healthcheck": postgres_service.get("healthcheck", {}),
                        "restart": postgres_service.get("restart", "no"),
                        "networks": postgres_service.get("networks", []),
                    }
                )

            # Keycloak database configuration
            if "keycloak" in compose_config["services"]:
                keycloak_service = compose_config["services"]["keycloak"]
                keycloak_env = keycloak_service.get("environment", {})

                # Extract database-related environment variables
                db_env_vars = {key: value for key, value in keycloak_env.items() if key.startswith("KC_DB")}
                keycloak_config.update(db_env_vars)

        return {
            "postgres_service": postgres_config,
            "keycloak_db_config": keycloak_config,
            "networks": compose_config.get("networks", {}),
            "volumes": compose_config.get("volumes", {}),
        }

    def extract_runtime_config(self) -> Optional[Dict[str, Any]]:
        """Extract runtime PostgreSQL configuration from running container.

        Returns:
            Dictionary containing runtime configuration or None if not available
        """
        try:
            # Check if PostgreSQL container is running
            result = subprocess.run(  # nosec B603 B607
                ["docker", "ps", "--filter", "name=postgres", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=True,
            )

            container_names = result.stdout.strip().split("\n")
            postgres_containers = [name for name in container_names if "postgres" in name and name]

            if not postgres_containers:
                logger.warning("No running PostgreSQL containers found")
                return None

            container_name = postgres_containers[0]

            # Extract PostgreSQL configuration
            config = {}

            # Get PostgreSQL version
            version_result = subprocess.run(  # nosec B603 B607
                ["docker", "exec", container_name, "psql", "--version"], capture_output=True, text=True, check=True
            )
            config["postgresql_version"] = version_result.stdout.strip()

            # Get current database settings
            settings_query = """
                SELECT name, setting, unit, category, short_desc
                FROM pg_settings
                WHERE category IN (
                    'Connections and Authentication / Connection Settings',
                    'Connections and Authentication / Authentication',
                    'Resource Usage / Memory',
                    'Resource Usage / Kernel Resources',
                    'Write-Ahead Log / Settings',
                    'Replication / Sending Servers'
                )
                ORDER BY category, name;
            """

            settings_result = subprocess.run(  # nosec B603 B607
                [
                    "docker",
                    "exec",
                    container_name,
                    "psql",
                    "-U",
                    "keycloak",
                    "-d",
                    "keycloak",
                    "-c",
                    settings_query,
                    "--no-align",
                    "--tuples-only",
                    "--field-separator=|",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse settings
            settings = {}
            for line in settings_result.stdout.strip().split("\n"):
                if line and "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        name, setting, unit = parts[0], parts[1], parts[2]
                        settings[name] = {"value": setting, "unit": unit if unit else None}

            config["runtime_settings"] = settings

            # Get database list
            db_list_result = subprocess.run(  # nosec B603 B607
                [
                    "docker",
                    "exec",
                    container_name,
                    "psql",
                    "-U",
                    "keycloak",
                    "-c",
                    "\\l",
                    "--no-align",
                    "--tuples-only",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            databases = []
            for line in db_list_result.stdout.strip().split("\n"):
                if line and "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        databases.append({"name": parts[0], "owner": parts[1], "encoding": parts[2]})

            config["databases"] = databases

            return config

        except subprocess.CalledProcessError as e:
            logger.error("Failed to extract runtime PostgreSQL config: %s", e)
            return None
        except Exception as e:
            logger.error("Unexpected error extracting runtime config: %s", e)
            return None

    def extract_complete_config(self) -> Dict[str, Any]:
        """Extract complete PostgreSQL configuration from all sources.

        Returns:
            Complete configuration dictionary
        """
        config = {
            "service_name": "keycloak",
            "config_type": "postgresql",
            "extraction_timestamp": datetime.now().isoformat(),
            "static_config": {},
            "runtime_config": {},
            "metadata": {"extractor_version": "1.0.0", "source_files": [str(self.docker_compose_path)]},
        }

        # Extract static configuration from Docker Compose
        try:
            static_config = self.extract_docker_compose_config()
            config["static_config"] = static_config
            logger.info("Successfully extracted static PostgreSQL configuration")
        except Exception as e:
            logger.error("Failed to extract static config: %s", e)
            config["static_config"] = {}

        # Extract runtime configuration
        runtime_config = self.extract_runtime_config()
        if runtime_config:
            config["runtime_config"] = runtime_config
            logger.info("Successfully extracted runtime PostgreSQL configuration")
        else:
            logger.warning("Could not extract runtime PostgreSQL configuration")
            config["runtime_config"] = {}

        return config


async def create_postgresql_baseline(output_file: Optional[str] = None) -> str:
    """Create PostgreSQL configuration baseline.

    Args:
        output_file: Optional file to save the baseline configuration

    Returns:
        Baseline ID if created successfully
    """
    extractor = PostgreSQLConfigExtractor()
    config = extractor.extract_complete_config()

    # Save to file if requested
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, default=str)

        logger.info("Configuration saved to %s", output_path)

    # Create baseline using monitoring service
    if ConfigurationMonitoringService:
        try:
            service = ConfigurationMonitoringService()
            baseline_id = await service.create_baseline(
                service_name=config["service_name"],
                config_type=config["config_type"],
                config_path=str(extractor.docker_compose_path),
                config_data=config,
            )

            logger.info("Created PostgreSQL baseline with ID: %s", baseline_id)
            return baseline_id

        except Exception as e:
            logger.error("Failed to create baseline: %s", e)
            raise
    else:
        logger.warning("Configuration monitoring service not available")
        return "service_unavailable"


def main() -> None:
    """Extract PostgreSQL configuration and create baseline."""
    import argparse
    import asyncio

    # Fix pandas import for timestamp
    try:
        import pandas as pd

        globals()["pd"] = pd
    except ImportError:
        # Fallback to datetime if pandas not available
        class pd:
            @staticmethod
            def Timestamp() -> datetime:
                return datetime.now()

        globals()["pd"] = pd

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Extract PostgreSQL configuration and create baseline")
    parser.add_argument("--keycloak-dir", default="./keycloak", help="Path to Keycloak directory (default: ./keycloak)")
    parser.add_argument("--output", help="Output file to save configuration (optional)")
    parser.add_argument(
        "--create-baseline", action="store_true", help="Create configuration baseline in monitoring system"
    )

    args = parser.parse_args()

    # Change to script directory for relative paths
    script_dir = Path(__file__).parent.parent.parent
    os.chdir(script_dir)

    extractor = PostgreSQLConfigExtractor(args.keycloak_dir)

    try:
        if args.create_baseline:
            baseline_id = asyncio.run(create_postgresql_baseline(args.output))
            print(f"✅ PostgreSQL baseline created: {baseline_id}")
        else:
            config = extractor.extract_complete_config()

            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, default=str)

                print(f"✅ Configuration saved to {output_path}")
            else:
                print(json.dumps(config, indent=2, default=str))

    except Exception as e:
        logger.error("Failed to extract PostgreSQL configuration: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
