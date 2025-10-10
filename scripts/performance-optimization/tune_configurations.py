# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Configuration tuning tool for database optimization."""

from __future__ import annotations

import argparse
import os
import shutil
from datetime import datetime
from typing import Any, Dict

from utils.report_generator import ReportGenerator


class ConfigurationTuner:
    """Tune database configurations for optimal performance."""

    def __init__(self: ConfigurationTuner) -> None:
        """Initialize configuration tuner."""
        self.report_generator = ReportGenerator()

    def analyze_workload(self: ConfigurationTuner, workload: Dict[str, Any], db_type: str) -> Dict[str, Any]:
        """Analyze workload characteristics.

        Args:
            workload: Workload metrics
            db_type: Type of database

        Returns:
            Workload analysis results
        """
        analysis: Dict[str, Any] = {"workload_type": "unknown", "recommendations": []}

        # Classify workload
        read_ops = workload.get("read_operations", 0)
        write_ops = workload.get("write_operations", 0)
        total_ops = read_ops + write_ops

        if total_ops > 0:
            read_ratio = read_ops / total_ops

            if read_ratio > 0.8:
                analysis["workload_type"] = "read_heavy"
                analysis["recommendations"].append("Enable aggressive caching")
            elif read_ratio < 0.2:
                analysis["workload_type"] = "write_heavy"
                analysis["recommendations"].append("Optimize write performance")
            else:
                analysis["workload_type"] = "balanced"

        return analysis

    def recommend_config(self: ConfigurationTuner, workload: Dict[str, Any], db_type: str) -> Dict[str, Any]:
        """Recommend optimal configuration.

        Args:
            workload: Workload characteristics
            db_type: Type of database

        Returns:
            Recommended configuration
        """
        config: Dict[str, Any] = {}

        if db_type == "sqlite":
            config = self._recommend_sqlite_config(workload)
        elif db_type == "postgres":
            config = self._recommend_postgres_config(workload)
        # DuckDB support removed - PyRIT migrated to SQLite in v0.10.0rc0 (issue #269)

        return config

    def _recommend_sqlite_config(self: ConfigurationTuner, workload: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend SQLite configuration.

        Args:
            workload: Workload characteristics

        Returns:
            SQLite configuration
        """
        # Default configuration
        config = {
            "journal_mode": "WAL",
            "cache_size": -2000,  # 2MB cache
            "synchronous": "NORMAL",
            "page_size": 4096,
        }

        # Adjust for read-heavy workloads
        if workload.get("read_heavy"):
            config["cache_size"] = -8000  # 8MB cache
            config["synchronous"] = "NORMAL"

        # Adjust for write-heavy workloads
        if workload.get("write_operations", 0) > 1000:
            config["synchronous"] = "NORMAL"
            config["wal_autocheckpoint"] = 1000

        return config

    # DuckDB configuration method removed - PyRIT migrated to SQLite in v0.10.0rc0 (issue #269)

    def _recommend_postgres_config(self: ConfigurationTuner, workload: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend PostgreSQL configuration.

        Args:
            workload: Workload characteristics

        Returns:
            PostgreSQL configuration
        """
        config = {
            "max_connections": 100,
            "shared_buffers": "256MB",
            "work_mem": "4MB",
            "effective_cache_size": "1GB",
        }

        # Adjust for high concurrency
        concurrent_conns = workload.get("concurrent_connections", 0)
        if concurrent_conns > 100:
            config["max_connections"] = concurrent_conns + 20
            config["shared_buffers"] = "512MB"

        return config

    def validate_config(self: ConfigurationTuner, config: Dict[str, Any], db_type: str) -> Dict[str, Any]:
        """Validate configuration settings.

        Args:
            config: Configuration to validate
            db_type: Type of database

        Returns:
            Validation results
        """
        validation = {"valid": True, "errors": []}

        if db_type == "sqlite":
            # Validate SQLite config
            if "cache_size" in config and config["cache_size"] == 0:
                validation["valid"] = False
                validation["errors"].append("cache_size cannot be 0")

            if "synchronous" in config:
                valid_modes = ["OFF", "NORMAL", "FULL"]
                if config["synchronous"] not in valid_modes:
                    validation["valid"] = False
                    validation["errors"].append(f"Invalid synchronous mode: {config['synchronous']}")

        return validation

    def apply_config(
        self: ConfigurationTuner,
        config: Dict[str, Any],
        db_type: str,
        config_path: str,
    ) -> bool:
        """Apply configuration settings.

        Args:
            config: Configuration to apply
            db_type: Type of database
            config_path: Path to save configuration

        Returns:
            True if configuration was applied successfully
        """
        # Ensure output directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # Generate configuration file
        if db_type == "sqlite":
            return self._write_sqlite_config(config, config_path)
        elif db_type == "postgres":
            return self._write_postgres_config(config, config_path)
        # DuckDB support removed - PyRIT migrated to SQLite in v0.10.0rc0 (issue #269)

        return False

    def _write_sqlite_config(self: ConfigurationTuner, config: Dict[str, Any], config_path: str) -> bool:
        """Write SQLite configuration file.

        Args:
            config: Configuration settings
            config_path: Path to save configuration

        Returns:
            True if successful
        """
        lines = [
            "# SQLite Configuration - Auto-generated",
            f"# Generated: {datetime.now().isoformat()}",
            "",
            "SQLITE_CONFIG = {",
        ]

        for key, value in config.items():
            if isinstance(value, str):
                lines.append(f'    "{key}": "{value}",')
            else:
                lines.append(f'    "{key}": {value},')

        lines.append("}")

        with open(config_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return True

    # DuckDB config writer removed - PyRIT migrated to SQLite in v0.10.0rc0 (issue #269)

    def _write_postgres_config(self: ConfigurationTuner, config: Dict[str, Any], config_path: str) -> bool:
        """Write PostgreSQL configuration file.

        Args:
            config: Configuration settings
            config_path: Path to save configuration

        Returns:
            True if successful
        """
        lines = [
            "# PostgreSQL Configuration - Auto-generated",
            f"# Generated: {datetime.now().isoformat()}",
            "",
        ]

        for key, value in config.items():
            lines.append(f"{key} = {value}")

        with open(config_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return True

    def backup_config(self: ConfigurationTuner, config_path: str) -> str:
        """Create backup of configuration file.

        Args:
            config_path: Path to configuration file

        Returns:
            Path to backup file
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{config_path}.backup_{timestamp}"

        shutil.copy2(config_path, backup_path)

        return backup_path

    def restore_config(self: ConfigurationTuner, backup_path: str, config_path: str) -> bool:
        """Restore configuration from backup.

        Args:
            backup_path: Path to backup file
            config_path: Path to restore configuration

        Returns:
            True if successful
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        shutil.copy2(backup_path, config_path)

        return True

    def calculate_cache_size(self: ConfigurationTuner, available_memory: int, db_type: str) -> int:
        """Calculate optimal cache size.

        Args:
            available_memory: Available memory in bytes
            db_type: Type of database

        Returns:
            Recommended cache size
        """
        if db_type == "sqlite":
            # Use 25% of available memory for cache
            cache_mb = (available_memory // (1024 * 1024)) // 4
            return -cache_mb  # Negative for KB units
        elif db_type == "postgres":
            # Use 50% of available memory for PostgreSQL
            return (available_memory // (1024 * 1024)) // 2
        else:
            # Default to 25% for unknown types
            cache_mb = (available_memory // (1024 * 1024)) // 4
            return cache_mb

    def calculate_pool_size(self: ConfigurationTuner, workload: Dict[str, Any]) -> int:
        """Calculate optimal connection pool size.

        Args:
            workload: Workload characteristics

        Returns:
            Recommended pool size
        """
        concurrent_users = workload.get("concurrent_users", 10)
        avg_query_time = workload.get("avg_query_time", 100)

        # Simple formula: users * (1 + query_time/1000)
        pool_size = int(concurrent_users * (1 + avg_query_time / 1000))

        # Cap at reasonable maximum
        return min(pool_size, 100)

    def generate_report(self: ConfigurationTuner, config: Dict[str, Any], output_path: str) -> None:
        """Generate configuration report.

        Args:
            config: Configuration data
            output_path: Path to save report
        """
        self.report_generator.generate_json_report(config, output_path)

    def compare_configs(
        self: ConfigurationTuner,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compare two configurations.

        Args:
            old_config: Old configuration
            new_config: New configuration

        Returns:
            Comparison results
        """
        comparison = {"changes": {}}

        # Find changed keys
        all_keys = set(old_config.keys()) | set(new_config.keys())

        for key in all_keys:
            old_val = old_config.get(key)
            new_val = new_config.get(key)

            if old_val != new_val:
                comparison["changes"][key] = {"old": old_val, "new": new_val}

        return comparison


def classify_workload(metrics: Dict[str, Any]) -> str:
    """Classify workload type.

    Args:
        metrics: Workload metrics

    Returns:
        Workload classification
    """
    read_ops = metrics.get("read_operations", 0)
    write_ops = metrics.get("write_operations", 0)
    total = read_ops + write_ops

    if total == 0:
        return "unknown"

    read_ratio = read_ops / total

    if read_ratio > 0.7:
        return "read_heavy"
    elif read_ratio < 0.3:
        return "write_heavy"
    else:
        return "balanced"


def calculate_resource_requirements(workload: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate resource requirements.

    Args:
        workload: Workload characteristics

    Returns:
        Resource requirements
    """
    concurrent_users = workload.get("concurrent_users", 10)
    ops_per_second = workload.get("operations_per_second", 100)

    # Simple estimation based on operations per second and concurrent users
    memory_mb = max(concurrent_users * 10, ops_per_second // 10)  # 10MB per user or ops scaling
    connections = concurrent_users + 10  # Buffer

    return {"memory": f"{memory_mb}MB", "connections": connections}


def main() -> None:
    """Tune database configurations."""
    parser = argparse.ArgumentParser(description="Tune database configurations")
    parser.add_argument("--db-type", required=True, help="Database type")
    parser.add_argument("--apply-optimizations", action="store_true", help="Apply optimizations")
    parser.add_argument("--output", default="config_report.json", help="Output report path")

    args = parser.parse_args()

    tuner = ConfigurationTuner()

    # Example workload for demonstration
    workload = {
        "read_operations": 900,
        "write_operations": 100,
        "concurrent_connections": 50,
    }

    print(f"Analyzing workload for {args.db_type}...")

    analysis = tuner.analyze_workload(workload, args.db_type)
    print(f"Workload type: {analysis['workload_type']}")

    config = tuner.recommend_config(workload, args.db_type)
    print("\nRecommended configuration:")
    for key, value in config.items():
        print(f"  {key}: {value}")

    if args.apply_optimizations:
        config_path = f"configs/database-tuning/{args.db_type}_config.py"
        print(f"\nApplying configuration to: {config_path}")
        success = tuner.apply_config(config, args.db_type, config_path)
        print(f"Result: {'Success' if success else 'Failed'}")

    # Generate report
    report_data = {"analysis": analysis, "configuration": config}
    tuner.generate_report(report_data, args.output)
    print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()
