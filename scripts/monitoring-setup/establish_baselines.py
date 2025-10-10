#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Establish Performance Baselines.

Issue #270 - Automated baseline calculation and documentation

This script analyzes historical database performance metrics and establishes
statistical baselines for anomaly detection and alerting.

Usage:
    python3 establish_baselines.py [--analyze-historical] [--database TYPE]
        --metrics METRIC1,METRIC2 --schedule CRON
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
DOCS_DIR = PROJECT_ROOT / "docs" / "monitoring"


class BaselineEstablisher:
    """Automated baseline calculation and documentation."""

    def __init__(
        self,
        api_base_url: str = "http://localhost:9080/api/v1",
        auth_token: Optional[str] = None,
    ) -> None:
        """
        Initialize baseline establisher.

        Args:
            api_base_url: ViolentUTF API base URL
            auth_token: JWT authentication token
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.auth_token = auth_token
        self.headers = {}

        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"

    def check_data_availability(
        self, db_type: Optional[str] = None, hours_back: int = 168  # 7 days
    ) -> Tuple[bool, int, str]:
        """
        Check if sufficient historical data is available.

        Args:
            db_type: Database type filter (postgresql, sqlite, or None for all)
            hours_back: Hours of historical data to check

        Returns:
            Tuple of (sufficient data available, sample count, message)
        """
        try:
            import requests

            # Construct API endpoint
            if db_type:
                endpoint = f"{self.api_base_url}/monitoring/database/" f"{db_type}/metrics?hours_back={hours_back}"
            else:
                endpoint = f"{self.api_base_url}/monitoring/metrics" f"?hours_back={hours_back}"

            response = requests.get(endpoint, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                count = data.get("count", 0)

                if count < 100:
                    return (
                        False,
                        count,
                        f"Insufficient data: {count} samples " f"(minimum 100 required)",
                    )
                else:
                    return (True, count, f"Sufficient data available: {count} samples")
            else:
                return (False, 0, f"API error: {response.status_code}")

        except ImportError:
            logger.error("requests library not available")
            return (False, 0, "Missing requests library")
        except Exception as e:
            logger.error("Error checking data availability: %s", e)
            return (False, 0, str(e))

    def calculate_baselines(
        self, db_type: Optional[str] = None, metric_types: Optional[List[str]] = None
    ) -> Tuple[bool, Dict]:
        """
        Calculate performance baselines from historical data.

        Args:
            db_type: Database type filter
            metric_types: List of specific metrics to baseline

        Returns:
            Tuple of (success, baseline results dict)
        """
        try:
            import requests

            # Construct API request
            endpoint = f"{self.api_base_url}/monitoring/database/baselines/recalculate"
            payload = {}

            if db_type:
                payload["db_type"] = db_type

            if metric_types:
                payload["metric_types"] = metric_types

            db_desc = db_type or "all databases"
            logger.info("Requesting baseline recalculation for %s", db_desc)

            response = requests.post(endpoint, json=payload, headers=self.headers, timeout=30)

            if response.status_code == 200:
                result = response.json()
                logger.info("Baseline calculation job created: %s", result.get("job_id"))
                return (True, result)
            else:
                logger.error("Baseline calculation failed: %s - %s", response.status_code, response.text)
                return (False, {"error": response.text})

        except ImportError:
            logger.error("requests library not available")
            return (False, {"error": "Missing requests library"})
        except Exception as e:
            logger.error("Error calculating baselines: %s", e)
            return (False, {"error": str(e)})

    def retrieve_baselines(
        self, db_type: Optional[str] = None, metric_types: Optional[List[str]] = None
    ) -> Tuple[bool, List[Dict]]:
        """
        Retrieve calculated baselines from API.

        Args:
            db_type: Database type filter
            metric_types: Metric type filter

        Returns:
            Tuple of (success, list of baseline records)
        """
        try:
            import requests

            # Construct API request
            endpoint = f"{self.api_base_url}/monitoring/database/baselines"
            params = {}

            if db_type:
                params["db_type"] = db_type

            if metric_types:
                params["metric_types"] = ",".join(metric_types)

            response = requests.get(endpoint, params=params, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                baselines = data.get("baselines", [])
                logger.info("Retrieved %s baseline records", len(baselines))
                return (True, baselines)
            else:
                logger.error("Failed to retrieve baselines: %s", response.status_code)
                return (False, [])

        except ImportError:
            logger.error("requests library not available")
            return (False, [])
        except Exception as e:
            logger.error("Error retrieving baselines: %s", e)
            return (False, [])

    def generate_baseline_report(self, baselines: List[Dict], output_file: Optional[Path] = None) -> bool:
        """
        Generate baseline documentation report.

        Args:
            baselines: List of baseline records
            output_file: Output file path
                (defaults to docs/monitoring/baseline_report.md)

        Returns:
            True if successful, False otherwise
        """
        if output_file is None:
            DOCS_DIR.mkdir(parents=True, exist_ok=True)
            output_file = DOCS_DIR / "baseline_report.md"

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                # Write report header
                f.write("# Database Performance Baseline Report\n\n")
                f.write(f"**Generated**: {datetime.now().isoformat()}\n")
                f.write(f"**Total Baselines**: {len(baselines)}\n\n")

                # Group baselines by database type
                postgres_baselines = [b for b in baselines if b.get("db_type") == "postgresql"]
                sqlite_baselines = [b for b in baselines if b.get("db_type") == "sqlite"]

                # PostgreSQL baselines
                if postgres_baselines:
                    f.write("## PostgreSQL (Keycloak) Baselines\n\n")
                    f.write("| Metric | Baseline | Std Dev | Normal Range | Samples |\n")
                    f.write("|--------|----------|---------|--------------|----------|\n")

                    for baseline in postgres_baselines:
                        metric_type = baseline.get("metric_type", "Unknown")
                        baseline_value = baseline.get("baseline_value", 0)
                        std_dev = baseline.get("std_deviation", 0)
                        normal_range = baseline.get("normal_range", {})
                        sample_size = baseline.get("sample_size", 0)

                        range_str = f"{normal_range.get('min', 0):.2f} - " f"{normal_range.get('max', 0):.2f}"

                        f.write(
                            f"| {metric_type} | {baseline_value:.2f} | "
                            f"{std_dev:.2f} | {range_str} | {sample_size} |\n"
                        )

                    f.write("\n")

                # SQLite baselines
                if sqlite_baselines:
                    f.write("## SQLite (FastAPI) Baselines\n\n")
                    f.write("| Metric | Baseline | Std Dev | Normal Range | Samples |\n")
                    f.write("|--------|----------|---------|--------------|----------|\n")

                    for baseline in sqlite_baselines:
                        metric_type = baseline.get("metric_type", "Unknown")
                        baseline_value = baseline.get("baseline_value", 0)
                        std_dev = baseline.get("std_deviation", 0)
                        normal_range = baseline.get("normal_range", {})
                        sample_size = baseline.get("sample_size", 0)

                        range_str = f"{normal_range.get('min', 0):.2f} - " f"{normal_range.get('max', 0):.2f}"

                        f.write(
                            f"| {metric_type} | {baseline_value:.2f} | "
                            f"{std_dev:.2f} | {range_str} | {sample_size} |\n"
                        )

                    f.write("\n")

                # Add recommendations
                f.write("## Recommendations\n\n")
                f.write("1. Review baselines for accuracy and adjust alert thresholds if needed\n")
                f.write("2. Schedule baseline recalculation weekly to adapt to changing patterns\n")
                f.write("3. Monitor for persistent baseline violations indicating capacity issues\n")
                f.write("4. Document any planned changes that may affect performance baselines\n\n")

            logger.info("Baseline report generated: %s", output_file)
            return True

        except Exception as e:
            logger.error("Error generating baseline report: %s", e)
            return False

    def schedule_recalculation(self, cron_expression: str = "0 2 * * 0") -> bool:  # Weekly at 2 AM on Sunday
        """
        Schedule periodic baseline recalculation (placeholder).

        Args:
            cron_expression: Cron expression for scheduling

        Returns:
            True if successful, False otherwise
        """
        logger.info("Baseline recalculation scheduling requested: %s", cron_expression)
        logger.info("Note: Automated scheduling requires systemd timer or cron configuration")
        logger.info("Add the following to crontab for automated recalculation:")
        logger.info(
            "  %s cd %s && python3 scripts/monitoring-setup/establish_baselines.py --analyze-historical",
            cron_expression,
            PROJECT_ROOT,
        )

        return True


def main() -> int:
    """Execute main baseline establishment workflow."""
    parser = argparse.ArgumentParser(description="Establish ViolentUTF Performance Baselines")
    parser.add_argument(
        "--analyze-historical",
        action="store_true",
        help="Analyze historical data and calculate baselines",
    )
    parser.add_argument("--database", choices=["postgresql", "sqlite"], help="Filter by database type")
    parser.add_argument("--metrics", help="Comma-separated list of specific metrics to baseline")
    parser.add_argument(
        "--schedule",
        help="Cron expression for periodic recalculation (e.g., '0 2 * * 0')",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:9080/api/v1",
        help="ViolentUTF API base URL",
    )
    parser.add_argument("--auth-token", help="JWT authentication token")

    args = parser.parse_args()

    establisher = BaselineEstablisher(api_base_url=args.api_url, auth_token=args.auth_token)

    # Parse metric types if provided
    metric_types = None
    if args.metrics:
        metric_types = [m.strip() for m in args.metrics.split(",")]

    # Schedule mode
    if args.schedule:
        logger.info("Configuring baseline recalculation schedule...")
        success = establisher.schedule_recalculation(args.schedule)
        return 0 if success else 1

    # Check data availability
    logger.info("Checking historical data availability...")
    has_data, _, message = establisher.check_data_availability(db_type=args.database)

    logger.info(message)

    if not has_data:
        logger.warning(
            "Insufficient historical data for reliable baselines. "
            "Continue monitoring and retry after collecting more data."
        )
        return 1

    # Analyze historical and calculate baselines
    if args.analyze_historical:
        logger.info("Calculating performance baselines...")
        success, result = establisher.calculate_baselines(db_type=args.database, metric_types=metric_types)

        if not success:
            logger.error("Baseline calculation failed")
            return 1

        logger.info("Baseline calculation initiated. Job ID: %s", result.get("job_id"))

        # Wait a moment for calculation to complete (in production, poll job status)
        import time

        logger.info("Waiting for baseline calculation to complete...")
        time.sleep(5)

    # Retrieve and document baselines
    logger.info("Retrieving calculated baselines...")
    success, baselines = establisher.retrieve_baselines(db_type=args.database, metric_types=metric_types)

    if not success or not baselines:
        logger.warning("No baselines available yet")
        return 1

    # Generate baseline report
    logger.info("Generating baseline documentation...")
    success = establisher.generate_baseline_report(baselines)

    if not success:
        logger.error("Failed to generate baseline report")
        return 1

    # Print summary
    logger.info("%s", "\n" + "=" * 60)
    logger.info("BASELINE ESTABLISHMENT SUMMARY")
    logger.info("=" * 60)
    logger.info("Total baselines established: %s", len(baselines))

    postgres_count = sum(1 for b in baselines if b.get("db_type") == "postgresql")
    sqlite_count = sum(1 for b in baselines if b.get("db_type") == "sqlite")

    logger.info("PostgreSQL baselines: %s", postgres_count)
    logger.info("SQLite baselines: %s", sqlite_count)
    logger.info("Report generated: %s", DOCS_DIR / "baseline_report.md")
    logger.info("%s", "=" * 60 + "\n")

    logger.info("Baseline establishment completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
