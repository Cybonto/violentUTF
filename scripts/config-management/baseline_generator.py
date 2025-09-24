#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Configuration Baseline Generator for Issue #265.

This script generates comprehensive configuration baselines for all ViolentUTF services
and stores them in the configuration monitoring system.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Add the FastAPI app to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent / "violentutf_api" / "fastapi_app"))

try:
    from app.services.config_monitoring import ConfigurationMonitoringService
except ImportError as e:
    print(f"Warning: Could not import configuration monitoring service: {e}")
    ConfigurationMonitoringService = None

logger = logging.getLogger(__name__)


class BaselineGenerator:
    """Generate configuration baselines for all ViolentUTF services."""

    def __init__(self, project_root: str = ".") -> None:
        """Initialize the baseline generator.

        Args:
            project_root: Path to the ViolentUTF project root
        """
        self.project_root = Path(project_root)
        self.config_service = ConfigurationMonitoringService() if ConfigurationMonitoringService else None

    def extract_keycloak_config(self) -> Dict[str, Any]:
        """Extract Keycloak PostgreSQL configuration."""
        keycloak_dir = self.project_root / "keycloak"
        docker_compose_path = keycloak_dir / "docker-compose.yml"

        if not docker_compose_path.exists():
            logger.warning("Keycloak docker-compose.yml not found: %s", docker_compose_path)
            return {}

        with open(docker_compose_path, "r", encoding="utf-8") as f:
            compose_config = yaml.safe_load(f)

        # Extract relevant configuration
        config = {
            "service_type": "authentication",
            "database_type": "postgresql",
            "container_config": {},
            "environment_variables": {},
            "network_config": {},
            "volume_config": {},
            "health_check": {},
        }

        services = compose_config.get("services", {})

        # PostgreSQL configuration
        if "postgres" in services:
            postgres = services["postgres"]
            config["container_config"]["postgres"] = {
                "image": postgres.get("image"),
                "restart": postgres.get("restart"),
                "ports": postgres.get("ports", []),
            }
            config["environment_variables"]["postgres"] = postgres.get("environment", {})
            config["health_check"]["postgres"] = postgres.get("healthcheck", {})

        # Keycloak configuration
        if "keycloak" in services:
            keycloak = services["keycloak"]
            config["container_config"]["keycloak"] = {
                "image": keycloak.get("image"),
                "command": keycloak.get("command"),
                "ports": keycloak.get("ports", []),
                "depends_on": keycloak.get("depends_on", {}),
            }

            # Extract database-related environment variables
            keycloak_env = keycloak.get("environment", {})
            db_env = {k: v for k, v in keycloak_env.items() if k.startswith("KC_")}
            config["environment_variables"]["keycloak"] = db_env

        # Network and volume configuration
        config["network_config"] = compose_config.get("networks", {})
        config["volume_config"] = compose_config.get("volumes", {})

        return config

    def extract_fastapi_config(self) -> Dict[str, Any]:
        """Extract FastAPI SQLite configuration."""
        fastapi_dir = self.project_root / "violentutf_api" / "fastapi_app"

        config = {
            "service_type": "api",
            "database_type": "sqlite",
            "application_config": {},
            "database_config": {},
            "environment_variables": {},
            "docker_config": {},
        }

        # Extract from config.py
        config_file = fastapi_dir / "app" / "core" / "config.py"
        if config_file.exists():
            config_content = self._extract_python_config(config_file)
            config["application_config"] = config_content

        # Extract from database.py
        db_file = fastapi_dir / "app" / "db" / "database.py"
        if db_file.exists():
            db_content = self._extract_database_config(db_file)
            config["database_config"] = db_content

        # Extract Docker configuration
        dockerfile = fastapi_dir / "Dockerfile"
        if dockerfile.exists():
            docker_content = self._extract_dockerfile_config(dockerfile)
            config["docker_config"] = docker_content

        # Extract environment variables from .env.sample
        env_sample = fastapi_dir / ".env.sample"
        if env_sample.exists():
            env_content = self._extract_env_config(env_sample)
            config["environment_variables"] = env_content

        return config

    def extract_apisix_config(self) -> Dict[str, Any]:
        """Extract APISIX gateway configuration."""
        apisix_dir = self.project_root / "apisix"

        config = {
            "service_type": "gateway",
            "gateway_config": {},
            "docker_config": {},
            "route_config": {},
            "plugin_config": {},
        }

        # Main APISIX configuration
        apisix_config_file = apisix_dir / "conf" / "config.yaml"
        if apisix_config_file.exists():
            with open(apisix_config_file, "r", encoding="utf-8") as f:
                apisix_config = yaml.safe_load(f)
            config["gateway_config"] = apisix_config

        # Docker Compose configuration
        docker_compose_file = apisix_dir / "docker-compose.yml"
        if docker_compose_file.exists():
            with open(docker_compose_file, "r", encoding="utf-8") as f:
                compose_config = yaml.safe_load(f)
            config["docker_config"] = compose_config

        # Dashboard configuration
        dashboard_config_file = apisix_dir / "conf" / "dashboard.yaml"
        if dashboard_config_file.exists():
            with open(dashboard_config_file, "r", encoding="utf-8") as f:
                dashboard_config = yaml.safe_load(f)
            config["plugin_config"]["dashboard"] = dashboard_config

        return config

    def extract_duckdb_config(self) -> Dict[str, Any]:
        """Extract DuckDB PyRIT configuration."""
        fastapi_dir = self.project_root / "violentutf_api" / "fastapi_app"

        config = {
            "service_type": "data_storage",
            "database_type": "duckdb",
            "manager_config": {},
            "security_config": {},
            "table_schemas": {},
        }

        # Extract from duckdb_manager.py
        duckdb_file = fastapi_dir / "app" / "db" / "duckdb_manager.py"
        if duckdb_file.exists():
            duckdb_content = self._extract_duckdb_manager_config(duckdb_file)
            config.update(duckdb_content)

        return config

    def _extract_python_config(self, file_path: Path) -> Dict[str, Any]:
        """Extract configuration from Python config file."""
        config = {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract class-based configuration (simplified)
            lines = content.split("\n")
            in_settings_class = False

            for line in lines:
                line = line.strip()

                if "class Settings" in line:
                    in_settings_class = True
                    continue

                if in_settings_class and line.startswith("class ") and "Settings" not in line:
                    break

                if in_settings_class and ":" in line and "=" in line:
                    # Extract variable assignments
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        var_name = parts[0].split(":")[0].strip()
                        var_value = parts[1].strip()

                        # Clean up the value
                        if var_value.startswith('"') and var_value.endswith('"'):
                            var_value = var_value[1:-1]
                        elif var_value == "True":
                            var_value = True
                        elif var_value == "False":
                            var_value = False
                        elif var_value.isdigit():
                            var_value = int(var_value)

                        config[var_name] = var_value

        except Exception as e:
            logger.warning("Could not parse Python config file %s: %s", file_path, e)

        return config

    def _extract_database_config(self, file_path: Path) -> Dict[str, Any]:
        """Extract database configuration from database.py."""
        config = {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract key configuration patterns
            if "DATABASE_URL" in content:
                config["connection_type"] = "async"
                config["database_url_pattern"] = "sqlite+aiosqlite"

            if "create_async_engine" in content:
                config["engine_type"] = "async"

            if "async_sessionmaker" in content:
                config["session_type"] = "async"

            # Extract engine parameters
            if "echo=" in content:
                config["echo_enabled"] = "development"

            if "future=True" in content:
                config["future_compatibility"] = True

        except Exception as e:
            logger.warning("Could not parse database config file %s: %s", file_path, e)

        return config

    def _extract_dockerfile_config(self, file_path: Path) -> Dict[str, Any]:
        """Extract configuration from Dockerfile."""
        config = {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()

                if line.startswith("FROM "):
                    config["base_image"] = line.replace("FROM ", "")
                elif line.startswith("EXPOSE "):
                    config["exposed_ports"] = line.replace("EXPOSE ", "").split()
                elif line.startswith("WORKDIR "):
                    config["working_directory"] = line.replace("WORKDIR ", "")
                elif line.startswith("CMD ") or line.startswith("ENTRYPOINT "):
                    config["startup_command"] = line

        except Exception as e:
            logger.warning("Could not parse Dockerfile %s: %s", file_path, e)

        return config

    def _extract_env_config(self, file_path: Path) -> Dict[str, Any]:
        """Extract environment variables from .env file."""
        config = {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()

                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()

        except Exception as e:
            logger.warning("Could not parse env file %s: %s", file_path, e)

        return config

    def _extract_duckdb_manager_config(self, file_path: Path) -> Dict[str, Any]:
        """Extract DuckDB manager configuration."""
        config = {"manager_config": {}, "security_config": {}, "table_schemas": {}}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract security configurations
            if "ALLOWED_UPDATE_COLUMNS" in content:
                config["security_config"]["allowed_update_columns"] = True

            if "ALLOWED_TABLES" in content:
                config["security_config"]["table_whitelist"] = True

            # Extract table creation patterns
            if "CREATE TABLE" in content:
                config["table_schemas"]["auto_generated"] = True

            # Extract connection patterns
            if "duckdb.connect" in content:
                config["manager_config"]["connection_type"] = "direct"

            if "db_path" in content:
                config["manager_config"]["path_based"] = True

        except Exception as e:
            logger.warning("Could not parse DuckDB manager file %s: %s", file_path, e)

        return config

    async def generate_all_baselines(self) -> List[str]:
        """Generate baselines for all services.

        Returns:
            List of baseline IDs created
        """
        baseline_ids = []

        # Service configurations to extract
        services = [
            ("keycloak", "postgresql", self.extract_keycloak_config),
            ("fastapi", "sqlite", self.extract_fastapi_config),
            ("apisix", "gateway", self.extract_apisix_config),
            ("pyrit", "duckdb", self.extract_duckdb_config),
        ]

        for service_name, config_type, extractor_func in services:
            try:
                logger.info("Extracting configuration for %s (%s)", service_name, config_type)

                config_data = extractor_func()

                if not config_data:
                    logger.warning("No configuration data extracted for %s", service_name)
                    continue

                # Add metadata
                config_data["baseline_metadata"] = {
                    "generated_at": datetime.now().isoformat(),
                    "generator_version": "1.0.0",
                    "service_name": service_name,
                    "config_type": config_type,
                }

                if self.config_service:
                    baseline_id = await self.config_service.create_baseline(
                        service_name=service_name,
                        config_type=config_type,
                        config_path=f"/{service_name}/",
                        config_data=config_data,
                    )

                    baseline_ids.append(baseline_id)
                    logger.info("Created baseline %s for %s", baseline_id, service_name)
                else:
                    logger.warning("Configuration service not available")

            except Exception as e:
                logger.error("Failed to create baseline for %s: %s", service_name, e)

        return baseline_ids

    async def generate_baseline_report(self, baseline_ids: List[str]) -> Dict[str, Any]:
        """Generate a comprehensive baseline report.

        Args:
            baseline_ids: List of created baseline IDs

        Returns:
            Baseline report dictionary
        """
        report = {
            "generation_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_baselines": len(baseline_ids),
                "successful_baselines": baseline_ids,
                "generator_version": "1.0.0",
            },
            "service_coverage": {},
            "configuration_summary": {},
            "validation_results": {},
        }

        if not self.config_service:
            return report

        # Analyze each baseline
        for baseline_id in baseline_ids:
            try:
                baseline = await self.config_service.get_baseline(baseline_id)
                if baseline:
                    service_name = baseline.service_name
                    config_type = baseline.config_type

                    report["service_coverage"][service_name] = {
                        "config_type": config_type,
                        "baseline_id": baseline_id,
                        "created_at": baseline.created_at.isoformat(),
                        "config_size": len(str(baseline.config_data)),
                    }

                    # Analyze configuration content
                    config_keys = list(baseline.config_data.keys()) if isinstance(baseline.config_data, dict) else []
                    report["configuration_summary"][service_name] = {
                        "top_level_keys": config_keys[:10],  # First 10 keys
                        "total_keys": len(config_keys),
                        "has_security_config": any(
                            "password" in str(k).lower() or "secret" in str(k).lower() for k in config_keys
                        ),
                        "has_network_config": any(
                            "port" in str(k).lower() or "host" in str(k).lower() for k in config_keys
                        ),
                    }

            except Exception as e:
                logger.error("Failed to analyze baseline %s: %s", baseline_id, e)

        # Overall statistics
        stats = await self.config_service.get_baseline_statistics()
        report["system_statistics"] = stats

        return report


async def main() -> None:
    """Generate configuration baselines for all ViolentUTF services."""
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Generate configuration baselines for all ViolentUTF services")
    parser.add_argument(
        "--project-root", default=".", help="Path to ViolentUTF project root (default: current directory)"
    )
    parser.add_argument(
        "--output-dir", default="./docs/development/issue_265/", help="Directory to save baseline reports"
    )
    parser.add_argument(
        "--services",
        nargs="+",
        choices=["keycloak", "fastapi", "apisix", "pyrit"],
        help="Specific services to process (default: all)",
    )

    args = parser.parse_args()

    # Change to project root
    os.chdir(args.project_root)

    generator = BaselineGenerator(args.project_root)

    try:
        print("🔧 Generating configuration baselines...")

        baseline_ids = await generator.generate_all_baselines()

        if baseline_ids:
            print(f"✅ Created {len(baseline_ids)} configuration baselines")
            for baseline_id in baseline_ids:
                print(f"   📋 {baseline_id}")

            # Generate report
            report = await generator.generate_baseline_report(baseline_ids)

            # Save report
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            report_file = output_dir / f"baseline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)

            print(f"📊 Baseline report saved to {report_file}")
        else:
            print("❌ No baselines were created")
            sys.exit(1)

    except Exception as e:
        logger.error("Failed to generate baselines: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
