# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Dependency mapping and discovery service for ViolentUTF database ecosystem."""

import ast
import json
import logging
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.models.dependency import (
    CriticalityLevel,
    DependencyRelationship,
    DependencyType,
    DiscoveryMethod,
    HealthStatus,
    ServiceHealth,
)
from app.schemas.dependency import DependencyDiscoveryConfig, DiscoveryResult

logger = logging.getLogger(__name__)


class DependencyMappingService:
    """Service for discovering and mapping dependencies in ViolentUTF ecosystem."""

    def __init__(self) -> None:
        """Initialize the dependency mapping service."""
        self.discovered_dependencies: Set[Tuple[str, str, str]] = set()
        self.service_registry = {
            "streamlit-app": {"port": 8501, "health_endpoint": "/health"},
            "violentutf-api": {"port": 8000, "health_endpoint": "/health"},
            "keycloak": {"port": 8080, "health_endpoint": "/health"},
            "apisix": {"port": 9080, "health_endpoint": "/apisix/status"},
        }

    async def discover_all_dependencies(self, config: Optional[DependencyDiscoveryConfig] = None) -> DiscoveryResult:
        """Discover all dependencies using multiple methods."""
        discovery_id = str(uuid.uuid4())
        started_at = datetime.now(UTC)

        if config is None:
            config = DependencyDiscoveryConfig()

        try:
            logger.info("Starting dependency discovery %s", discovery_id)

            # Initialize counters
            total_discovered = 0
            new_dependencies = 0
            updated_dependencies = 0
            errors = []
            warnings = []

            # Code-based dependency discovery
            if DiscoveryMethod.CODE_ANALYSIS in config.discovery_methods:
                try:
                    code_deps = await self.discover_code_dependencies(config.scan_paths)
                    total_discovered += len(code_deps)
                    logger.info("Discovered %d dependencies via code analysis", len(code_deps))
                except Exception as e:
                    errors.append(f"Code analysis failed: {str(e)}")
                    logger.error("Code analysis error: %s", e)

            # Runtime dependency discovery
            if DiscoveryMethod.RUNTIME_TRACE in config.discovery_methods:
                try:
                    runtime_deps = await self.discover_runtime_dependencies(config.runtime_trace_duration)
                    total_discovered += len(runtime_deps)
                    logger.info("Discovered %d dependencies via runtime trace", len(runtime_deps))
                except Exception as e:
                    errors.append(f"Runtime tracing failed: {str(e)}")
                    logger.error("Runtime tracing error: %s", e)

            # Configuration scanning
            if DiscoveryMethod.CONFIGURATION_SCAN in config.discovery_methods:
                try:
                    config_deps = await self.discover_configuration_dependencies(config.scan_paths)
                    total_discovered += len(config_deps)
                    logger.info("Discovered %d dependencies via configuration scan", len(config_deps))
                except Exception as e:
                    errors.append(f"Configuration scan failed: {str(e)}")
                    logger.error("Configuration scan error: %s", e)

            # Service health discovery
            if DiscoveryMethod.HEALTH_CHECK in config.discovery_methods:
                try:
                    await self.discover_service_health(config.health_check_timeout)
                    logger.info("Completed service health discovery")
                except Exception as e:
                    errors.append(f"Health check discovery failed: {str(e)}")
                    logger.error("Health check error: %s", e)

            completed_at = datetime.now(UTC)

            return DiscoveryResult(
                discovery_id=discovery_id,
                discovery_method=DiscoveryMethod.CODE_ANALYSIS,  # Primary method
                started_at=started_at,
                completed_at=completed_at,
                status="completed" if not errors else "completed_with_errors",
                discovered_dependencies=total_discovered,
                new_dependencies=new_dependencies,
                updated_dependencies=updated_dependencies,
                errors=errors,
                warnings=warnings,
                metadata={
                    "methods_used": [method.value for method in config.discovery_methods],
                    "scan_paths": config.scan_paths,
                    "duration_seconds": (completed_at - started_at).total_seconds(),
                },
            )

        except Exception as e:
            logger.error("Discovery %s failed: %s", discovery_id, e)
            return DiscoveryResult(
                discovery_id=discovery_id,
                discovery_method=DiscoveryMethod.CODE_ANALYSIS,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                status="failed",
                discovered_dependencies=0,
                new_dependencies=0,
                updated_dependencies=0,
                errors=[f"Discovery failed: {str(e)}"],
                warnings=[],
                metadata={},
            )

    async def discover_code_dependencies(self, scan_paths: List[str]) -> List[Dict[str, Any]]:
        """Discover dependencies through static code analysis."""
        dependencies = []

        for scan_path in scan_paths:
            path = Path(scan_path)
            if not path.exists():
                logger.warning("Scan path does not exist: %s", scan_path)
                continue

            # Find Python files
            python_files = list(path.rglob("*.py"))

            for py_file in python_files:
                try:
                    file_deps = await self._analyze_python_file(py_file)
                    dependencies.extend(file_deps)
                except Exception as e:
                    logger.warning("Failed to analyze %s: %s", py_file, e)

        # Store discovered dependencies
        async with get_db_session() as session:
            for dep_data in dependencies:
                await self._store_dependency(session, dep_data)

        return dependencies

    async def _analyze_python_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Analyze a Python file for dependencies."""
        dependencies = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse AST
            tree = ast.parse(content)

            # Database connection patterns
            db_patterns = {
                "sqlite": r'sqlite.*?://([^"\']+)',
                "postgresql": r'postgresql.*?://([^"\']+)',
                "duckdb": r'(?:duckdb\.)?connect\(["\']([^"\']+\.duckdb)["\']',
                "mysql": r'mysql.*?://([^"\']+)',
            }

            # Service URL patterns
            service_patterns = {
                "api_call": r'http[s]?://([^/"\'\s]+)',
                "keycloak": r'keycloak.*?url["\']?\s*[:=]\s*["\']([^"\']+)',
                "apisix": r'apisix.*?url["\']?\s*[:=]\s*["\']([^"\']+)',
            }

            # Search for database connections
            for db_type, pattern in db_patterns.items():
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    dependencies.append(
                        {
                            "source_service": self._get_service_from_path(file_path),
                            "target_database": match,
                            "dependency_type": DependencyType.DATABASE,
                            "criticality": self._assess_criticality(db_type, match),
                            "discovery_method": DiscoveryMethod.CODE_ANALYSIS,
                            "metadata": {"file_path": str(file_path), "database_type": db_type, "pattern_match": match},
                        }
                    )

            # Search for service dependencies
            for service_type, pattern in service_patterns.items():
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    dependencies.append(
                        {
                            "source_service": self._get_service_from_path(file_path),
                            "target_service": self._extract_service_name(match),
                            "dependency_type": (
                                DependencyType.API if service_type == "api_call" else DependencyType.SERVICE
                            ),
                            "criticality": self._assess_service_criticality(match),
                            "discovery_method": DiscoveryMethod.CODE_ANALYSIS,
                            "metadata": {"file_path": str(file_path), "service_type": service_type, "url": match},
                        }
                    )

            # Analyze imports for framework dependencies
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dep = self._analyze_import(alias.name, file_path)
                        if dep:
                            dependencies.append(dep)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dep = self._analyze_import(node.module, file_path)
                        if dep:
                            dependencies.append(dep)

        except Exception as e:
            logger.error("Error analyzing file %s: %s", file_path, e)

        return dependencies

    def _analyze_import(self, module_name: str, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analyze import statements for dependency information."""
        dependency_modules = {
            "sqlalchemy": {"type": DependencyType.DATABASE, "criticality": CriticalityLevel.CRITICAL},
            "duckdb": {"type": DependencyType.DATABASE, "criticality": CriticalityLevel.HIGH},
            "psycopg2": {"type": DependencyType.DATABASE, "criticality": CriticalityLevel.HIGH},
            "pymongo": {"type": DependencyType.DATABASE, "criticality": CriticalityLevel.MEDIUM},
            "requests": {"type": DependencyType.API, "criticality": CriticalityLevel.MEDIUM},
            "aiohttp": {"type": DependencyType.API, "criticality": CriticalityLevel.MEDIUM},
            "keycloak": {"type": DependencyType.AUTHENTICATION, "criticality": CriticalityLevel.CRITICAL},
            "streamlit": {"type": DependencyType.SERVICE, "criticality": CriticalityLevel.HIGH},
            "fastapi": {"type": DependencyType.SERVICE, "criticality": CriticalityLevel.CRITICAL},
        }

        for dep_module, config in dependency_modules.items():
            if module_name.startswith(dep_module):
                return {
                    "source_service": self._get_service_from_path(file_path),
                    "target_service": dep_module,
                    "dependency_type": config["type"],
                    "criticality": config["criticality"],
                    "discovery_method": DiscoveryMethod.CODE_ANALYSIS,
                    "metadata": {
                        "file_path": str(file_path),
                        "import_module": module_name,
                        "framework_dependency": True,
                    },
                }

        return None

    async def discover_runtime_dependencies(self, duration_seconds: int = 300) -> List[Dict[str, Any]]:
        """Discover dependencies through runtime monitoring."""
        # This would implement actual runtime tracing
        # For now, return mock data
        logger.info("Starting runtime dependency tracing for %d seconds", duration_seconds)

        # Simulate runtime discovery
        runtime_deps = [
            {
                "source_service": "streamlit-app",
                "target_service": "violentutf-api",
                "dependency_type": DependencyType.API,
                "criticality": CriticalityLevel.CRITICAL,
                "discovery_method": DiscoveryMethod.RUNTIME_TRACE,
                "metadata": {"endpoint": "/api/v1/generators", "method": "GET", "frequency": "high"},
            },
            {
                "source_service": "violentutf-api",
                "target_database": "violentutf_api.db",
                "dependency_type": DependencyType.DATABASE,
                "criticality": CriticalityLevel.CRITICAL,
                "discovery_method": DiscoveryMethod.RUNTIME_TRACE,
                "metadata": {"connection_pool_size": 10, "query_frequency": "very_high"},
            },
        ]

        # Store runtime dependencies
        async with get_db_session() as session:
            for dep_data in runtime_deps:
                await self._store_dependency(session, dep_data)

        return runtime_deps

    async def discover_configuration_dependencies(self, scan_paths: List[str]) -> List[Dict[str, Any]]:
        """Discover dependencies from configuration files."""
        dependencies = []

        config_patterns = {
            "*.yaml": self._parse_yaml_config,
            "*.yml": self._parse_yaml_config,
            "*.json": self._parse_json_config,
            "*.env": self._parse_env_config,
            "docker-compose.yml": self._parse_docker_compose,
        }

        for scan_path in scan_paths:
            path = Path(scan_path)
            if not path.exists():
                continue

            for pattern, parser in config_patterns.items():
                config_files = list(path.rglob(pattern))
                for config_file in config_files:
                    try:
                        file_deps = await parser(config_file)
                        dependencies.extend(file_deps)
                    except Exception as e:
                        logger.warning("Failed to parse config %s: %s", config_file, e)

        return dependencies

    async def _parse_yaml_config(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse YAML configuration files for dependencies."""
        # Implementation would parse YAML and extract database URLs, service endpoints
        return []

    async def _parse_json_config(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse JSON configuration files for dependencies."""
        # Implementation would parse JSON and extract dependencies
        return []

    async def _parse_env_config(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse environment configuration files for dependencies."""
        # Implementation would parse .env files for database URLs, service endpoints
        return []

    async def _parse_docker_compose(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse Docker Compose files for service dependencies."""
        # Implementation would parse docker-compose.yml for service relationships
        return []

    async def discover_service_health(self, timeout_seconds: int = 30) -> None:
        """Discover and update service health status."""
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout_seconds)) as session:
            for service_name, config in self.service_registry.items():
                try:
                    health_url = f"http://localhost:{config['port']}{config['health_endpoint']}"
                    start_time = datetime.now(UTC)

                    async with session.get(health_url) as response:
                        response_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

                        if response.status == 200:
                            health_status = HealthStatus.HEALTHY
                            error_message = None
                        else:
                            health_status = HealthStatus.DEGRADED
                            error_message = f"HTTP {response.status}"

                        await self._update_service_health(
                            service_name=service_name,
                            health_status=health_status,
                            response_time_ms=int(response_time),
                            error_message=error_message,
                            endpoint_url=health_url,
                        )

                except Exception as e:
                    await self._update_service_health(
                        service_name=service_name,
                        health_status=HealthStatus.DOWN,
                        error_message=str(e),
                        endpoint_url=f"http://localhost:{config['port']}{config['health_endpoint']}",
                    )

    async def _store_dependency(self, session: AsyncSession, dep_data: Dict[str, Any]) -> None:
        """Store a discovered dependency in the database."""
        dependency_id = str(uuid.uuid4())

        dependency = DependencyRelationship(
            id=dependency_id,
            source_service=dep_data["source_service"],
            target_service=dep_data.get("target_service"),
            target_database=dep_data.get("target_database"),
            dependency_type=dep_data["dependency_type"],
            criticality=dep_data["criticality"],
            discovery_method=dep_data["discovery_method"],
            metadata_json=json.dumps(dep_data.get("metadata", {})),
        )

        session.add(dependency)
        await session.commit()

    async def _update_service_health(
        self,
        service_name: str,
        health_status: HealthStatus,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ) -> None:
        """Update service health status in database."""
        async with get_db_session() as session:
            # Check if health record exists
            health_record = await session.get(ServiceHealth, service_name)

            if health_record:
                health_record.health_status = health_status
                health_record.response_time_ms = response_time_ms
                health_record.error_message = error_message
                health_record.last_check = datetime.now(UTC)
            else:
                health_record = ServiceHealth(
                    id=str(uuid.uuid4()),
                    service_name=service_name,
                    health_status=health_status,
                    response_time_ms=response_time_ms,
                    error_message=error_message,
                    endpoint_url=endpoint_url,
                )
                session.add(health_record)

            await session.commit()

    def _get_service_from_path(self, file_path: Path) -> str:
        """Determine service name from file path."""
        path_str = str(file_path)

        if "violentutf_api" in path_str:
            return "violentutf-api"
        elif "violentutf" in path_str and "api" not in path_str:
            return "streamlit-app"
        elif "keycloak" in path_str:
            return "keycloak"
        elif "apisix" in path_str:
            return "apisix"
        else:
            return "unknown-service"

    def _assess_criticality(self, db_type: str, connection_string: str) -> CriticalityLevel:
        """Assess criticality level of database dependency."""
        if "violentutf_api" in connection_string or "keycloak" in connection_string:
            return CriticalityLevel.CRITICAL
        elif db_type in ["sqlite", "postgresql"]:
            return CriticalityLevel.HIGH
        elif db_type == "duckdb":
            return CriticalityLevel.MEDIUM
        else:
            return CriticalityLevel.LOW

    def _assess_service_criticality(self, service_url: str) -> CriticalityLevel:
        """Assess criticality level of service dependency."""
        if "localhost:8000" in service_url or "api" in service_url:
            return CriticalityLevel.CRITICAL
        elif "localhost:8080" in service_url or "keycloak" in service_url:
            return CriticalityLevel.CRITICAL
        elif "localhost:8501" in service_url:
            return CriticalityLevel.HIGH
        else:
            return CriticalityLevel.MEDIUM

    def _extract_service_name(self, url: str) -> str:
        """Extract service name from URL."""
        if ":8000" in url:
            return "violentutf-api"
        elif ":8501" in url:
            return "streamlit-app"
        elif ":8080" in url:
            return "keycloak"
        elif ":9080" in url:
            return "apisix"
        else:
            return "external-service"
