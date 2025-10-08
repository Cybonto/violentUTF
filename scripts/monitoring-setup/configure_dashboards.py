#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Configure Grafana Dashboards.

Issue #270 - Automated Grafana dashboard provisioning

This script automates the creation and provisioning of Grafana dashboards
for ViolentUTF database performance monitoring.

Usage:
    python3 configure_dashboards.py [--grafana-url URL] [--update]
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
DASHBOARDS_DIR = PROJECT_ROOT / "dashboards"


class GrafanaDashboardConfigurator:
    """Automated Grafana dashboard configuration and provisioning."""

    def __init__(
        self,
        grafana_url: str = "http://localhost:3000",
        username: str = "admin",
        password: str = "admin",
    ) -> None:
        """
        Initialize dashboard configurator.

        Args:
            grafana_url: Grafana base URL
            username: Grafana admin username
            password: Grafana admin password
        """
        self.grafana_url = grafana_url.rstrip("/")
        self.api_url = f"{self.grafana_url}/api"
        self.auth = (username, password)
        self.session = requests.Session()
        self.session.auth = self.auth

    def validate_grafana_connection(self) -> Tuple[bool, str]:
        """
        Validate connection to Grafana API.

        Returns:
            Tuple of (success, error message if any)
        """
        try:
            response = self.session.get(f"{self.grafana_url}/api/health", timeout=5)

            if response.status_code == 200:
                logger.info("Grafana connection validated successfully")
                return (True, "")
            else:
                return (False, f"Grafana returned status {response.status_code}")

        except requests.exceptions.ConnectionError:
            return (False, f"Cannot connect to Grafana at {self.grafana_url}")
        except Exception as e:
            return (False, f"Connection error: {str(e)}")

    def load_dashboard_json(self, dashboard_file: Path) -> Optional[Dict]:
        """
        Load and validate dashboard JSON file.

        Args:
            dashboard_file: Path to dashboard JSON file

        Returns:
            Dashboard JSON data or None if invalid
        """
        try:
            with open(dashboard_file, "r", encoding="utf-8") as f:
                dashboard_data = json.load(f)

            # Validate required fields
            required_fields = ["title", "panels"]
            for field in required_fields:
                if field not in dashboard_data:
                    logger.error("Dashboard %s missing required field: %s", dashboard_file.name, field)
                    return None

            logger.info("Loaded dashboard: %s", dashboard_data.get("title"))
            return dashboard_data

        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in %s: %s", dashboard_file.name, e)
            return None
        except Exception as e:
            logger.error("Error loading %s: %s", dashboard_file.name, e)
            return None

    def get_existing_dashboard(self, uid: str) -> Optional[Dict]:
        """
        Get existing dashboard by UID.

        Args:
            uid: Dashboard UID

        Returns:
            Dashboard data if exists, None otherwise
        """
        try:
            response = self.session.get(f"{self.api_url}/dashboards/uid/{uid}", timeout=5)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.warning("Unexpected response when checking dashboard %s: %s", uid, response.status_code)
                return None

        except Exception as e:
            logger.warning("Error checking existing dashboard %s: %s", uid, e)
            return None

    def provision_dashboard(self, dashboard_data: Dict, update_existing: bool = False) -> Tuple[bool, str]:
        """
        Provision dashboard to Grafana.

        Args:
            dashboard_data: Dashboard JSON data
            update_existing: If True, update existing dashboard

        Returns:
            Tuple of (success, message)
        """
        uid = dashboard_data.get("uid")
        title = dashboard_data.get("title", "Unknown")

        # Check if dashboard already exists
        existing = self.get_existing_dashboard(uid) if uid else None

        if existing and not update_existing:
            logger.info("Dashboard '%s' already exists (use --update to replace)", title)
            return (True, "Dashboard already exists")

        # Prepare dashboard payload
        payload = {
            "dashboard": dashboard_data,
            "overwrite": update_existing,
            "message": "Provisioned by configure_dashboards.py",
        }

        try:
            response = self.session.post(f"{self.api_url}/dashboards/db", json=payload, timeout=10)

            if response.status_code in [200, 201]:
                result = response.json()
                action = "Updated" if existing else "Created"
                logger.info("%s dashboard '%s' (UID: %s)", action, title, uid)
                return (True, result.get("url", ""))
            else:
                logger.error("Failed to provision dashboard '%s': %s - %s", title, response.status_code, response.text)
                return (False, response.text)

        except Exception as e:
            logger.error("Exception provisioning dashboard '%s': %s", title, e)
            return (False, str(e))

    def provision_all_dashboards(self, update_existing: bool = False) -> Dict[str, bool]:
        """
        Provision all dashboards from dashboards directory.

        Args:
            update_existing: If True, update existing dashboards

        Returns:
            Dict mapping dashboard names to provision success status
        """
        results = {}

        if not DASHBOARDS_DIR.exists():
            logger.error("Dashboards directory not found: %s", DASHBOARDS_DIR)
            return results

        dashboard_files = list(DASHBOARDS_DIR.glob("*.json"))

        if not dashboard_files:
            logger.warning("No dashboard files found in %s", DASHBOARDS_DIR)
            return results

        logger.info("Found %s dashboard files", len(dashboard_files))

        for dashboard_file in dashboard_files:
            dashboard_data = self.load_dashboard_json(dashboard_file)

            if not dashboard_data:
                results[dashboard_file.name] = False
                continue

            success, _ = self.provision_dashboard(dashboard_data, update_existing)
            results[dashboard_file.name] = success

        return results

    def validate_dashboard_datasources(self) -> Tuple[bool, List[str]]:
        """
        Validate that required datasources are configured in Grafana.

        Returns:
            Tuple of (success, list of missing datasources)
        """
        try:
            response = self.session.get(f"{self.api_url}/datasources", timeout=5)

            if response.status_code != 200:
                logger.error("Failed to fetch datasources from Grafana")
                return (False, [])

            datasources = response.json()
            datasource_names = [ds.get("name") for ds in datasources]

            # Check for required Prometheus datasource
            if "Prometheus" not in datasource_names:
                logger.warning("Prometheus datasource not found in Grafana")
                return (False, ["Prometheus"])

            logger.info("All required datasources are configured")
            return (True, [])

        except Exception as e:
            logger.error("Error validating datasources: %s", e)
            return (False, [])

    def list_dashboards(self) -> List[Dict]:
        """
        List all dashboards in Grafana.

        Returns:
            List of dashboard metadata
        """
        try:
            response = self.session.get(f"{self.api_url}/search?type=dash-db", timeout=5)

            if response.status_code == 200:
                dashboards = response.json()
                logger.info("Found %s dashboards in Grafana", len(dashboards))
                return dashboards
            else:
                logger.error("Failed to list dashboards: %s", response.status_code)
                return []

        except Exception as e:
            logger.error("Error listing dashboards: %s", e)
            return []


def main() -> int:
    """Execute main dashboard configuration workflow."""
    parser = argparse.ArgumentParser(description="Configure ViolentUTF Grafana Dashboards")
    parser.add_argument(
        "--grafana-url",
        default="http://localhost:3000",
        help="Grafana base URL (default: http://localhost:3000)",
    )
    parser.add_argument("--username", default="admin", help="Grafana admin username (default: admin)")
    parser.add_argument("--password", default="admin", help="Grafana admin password (default: admin)")
    parser.add_argument("--update", action="store_true", help="Update existing dashboards")
    parser.add_argument("--list", action="store_true", help="List existing dashboards and exit")

    args = parser.parse_args()

    configurator = GrafanaDashboardConfigurator(
        grafana_url=args.grafana_url, username=args.username, password=args.password
    )

    # Validate Grafana connection
    logger.info("Validating Grafana connection...")
    connection_valid, error = configurator.validate_grafana_connection()

    if not connection_valid:
        logger.error("Grafana connection failed: %s", error)
        logger.error("Make sure Grafana is running and accessible")
        return 1

    # List mode
    if args.list:
        logger.info("Listing existing dashboards...")
        dashboards = configurator.list_dashboards()

        if dashboards:
            logger.info("\nExisting dashboards:")
            for dashboard in dashboards:
                logger.info("  - %s (UID: %s)", dashboard.get("title"), dashboard.get("uid"))
        else:
            logger.info("No dashboards found")

        return 0

    # Validate datasources
    logger.info("Validating datasources...")
    datasources_valid, missing = configurator.validate_dashboard_datasources()

    if not datasources_valid:
        logger.error("Missing required datasources: %s", ", ".join(missing))
        logger.error("Make sure Prometheus datasource is configured in Grafana")
        return 1

    # Provision all dashboards
    logger.info("Provisioning dashboards...")
    results = configurator.provision_all_dashboards(update_existing=args.update)

    # Print summary
    logger.info("%s", "\n" + "=" * 60)
    logger.info("DASHBOARD PROVISIONING SUMMARY")
    logger.info("=" * 60)

    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)

    for dashboard_name, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        logger.info("%s: %s", dashboard_name, status)

    logger.info("=" * 60)
    logger.info("Total: %s/%s dashboards provisioned", success_count, total_count)
    logger.info("%s", "=" * 60 + "\n")

    if success_count == total_count:
        logger.info("All dashboards provisioned successfully!")
        logger.info("Access dashboards at: %s/dashboards", args.grafana_url)
        return 0
    else:
        logger.error("Some dashboards failed to provision")
        return 1


if __name__ == "__main__":
    sys.exit(main())
