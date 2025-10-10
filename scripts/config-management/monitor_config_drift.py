#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Configuration Drift Monitoring Tool for ViolentUTF - Issue #266.

Real-time monitoring and alerting for configuration drift detection.
"""

import hashlib
import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import schedule
import yaml
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ConfigurationMonitoringRule:
    """Represents a configuration monitoring rule."""

    rule_id: str
    service: str
    environment: str
    file_patterns: List[str]
    check_interval_seconds: int = 300  # 5 minutes default
    drift_threshold_percentage: float = 5.0  # 5% drift threshold
    alert_on_change: bool = True
    alert_on_drift: bool = True
    notification_channels: List[str] = field(default_factory=lambda: ["database"])
    active: bool = True


@dataclass
class ConfigurationAlert:
    """Represents a configuration alert."""

    alert_id: str
    rule_id: str
    alert_type: str  # 'drift', 'change', 'validation_error', 'service_unavailable'
    severity: str  # 'low', 'medium', 'high', 'critical'
    service: str
    environment: str
    affected_files: List[str]
    alert_message: str
    alert_data: Dict[str, Any] = field(default_factory=dict)
    created_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False
    resolved: bool = False


class ConfigurationMonitor:
    """Main configuration drift monitoring engine."""

    def __init__(self, database_path: str = "config_monitoring.db", config_path: str = "monitor_config.yaml") -> None:
        """Initialize the configuration monitor.

        Args:
            database_path: Path to SQLite database for monitoring data
            config_path: Path to monitoring configuration file
        """
        self.database_path = database_path
        self.config_path = config_path
        self.monitoring_rules: Dict[str, ConfigurationMonitoringRule] = {}
        self.file_observers: Dict[str, Observer] = {}
        self.baseline_checksums: Dict[str, str] = {}
        self.alert_handlers: Dict[str, Callable] = {}
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None

        self._setup_database()
        self._load_monitoring_configuration()
        self._setup_alert_handlers()

    def _setup_database(self) -> None:
        """Set up SQLite database for monitoring data."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS monitoring_rules (
                rule_id TEXT PRIMARY KEY,
                service TEXT NOT NULL,
                environment TEXT NOT NULL,
                file_patterns TEXT NOT NULL,
                check_interval_seconds INTEGER NOT NULL,
                drift_threshold_percentage REAL NOT NULL,
                alert_on_change BOOLEAN NOT NULL,
                alert_on_drift BOOLEAN NOT NULL,
                notification_channels TEXT NOT NULL,
                active BOOLEAN NOT NULL,
                created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS configuration_baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                environment TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_checksum TEXT NOT NULL,
                file_content_preview TEXT,
                baseline_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(service, environment, file_path)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS configuration_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT NOT NULL,
                service TEXT NOT NULL,
                environment TEXT NOT NULL,
                file_path TEXT NOT NULL,
                change_type TEXT NOT NULL,
                old_checksum TEXT,
                new_checksum TEXT,
                drift_percentage REAL,
                change_details TEXT,
                detected_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                rule_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                service TEXT NOT NULL,
                environment TEXT NOT NULL,
                affected_files TEXT NOT NULL,
                alert_message TEXT NOT NULL,
                alert_data TEXT,
                acknowledged BOOLEAN DEFAULT FALSE,
                resolved BOOLEAN DEFAULT FALSE,
                created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged_timestamp TIMESTAMP,
                resolved_timestamp TIMESTAMP
            )
        """
        )

        conn.commit()
        conn.close()

    def _load_monitoring_configuration(self) -> None:
        """Load monitoring configuration from file."""
        config_file = Path(self.config_path)

        # Create default configuration if it doesn't exist
        if not config_file.exists():
            self._create_default_monitoring_config(config_file)

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            for rule_data in config_data.get("monitoring_rules", []):
                rule = ConfigurationMonitoringRule(
                    rule_id=rule_data["rule_id"],
                    service=rule_data["service"],
                    environment=rule_data["environment"],
                    file_patterns=rule_data["file_patterns"],
                    check_interval_seconds=rule_data.get("check_interval_seconds", 300),
                    drift_threshold_percentage=rule_data.get("drift_threshold_percentage", 5.0),
                    alert_on_change=rule_data.get("alert_on_change", True),
                    alert_on_drift=rule_data.get("alert_on_drift", True),
                    notification_channels=rule_data.get("notification_channels", ["database"]),
                    active=rule_data.get("active", True),
                )

                self.monitoring_rules[rule.rule_id] = rule
                self._store_monitoring_rule(rule)

            logger.info("Loaded %s monitoring rules", len(self.monitoring_rules))

        except Exception as e:
            logger.error("Error loading monitoring configuration: %s", e)

    def _create_default_monitoring_config(self, config_file: Path) -> None:
        """Create default monitoring configuration file."""
        default_config = {
            "monitoring_rules": [
                {
                    "rule_id": "apisix_config_monitor",
                    "service": "apisix",
                    "environment": "all",
                    "file_patterns": ["apisix/conf/*.yaml", "apisix/conf/*.yml"],
                    "check_interval_seconds": 300,
                    "drift_threshold_percentage": 3.0,
                    "alert_on_change": True,
                    "alert_on_drift": True,
                    "notification_channels": ["database", "log"],
                    "active": True,
                },
                {
                    "rule_id": "keycloak_config_monitor",
                    "service": "keycloak",
                    "environment": "all",
                    "file_patterns": ["keycloak/realm-export.json"],
                    "check_interval_seconds": 600,
                    "drift_threshold_percentage": 5.0,
                    "alert_on_change": True,
                    "alert_on_drift": True,
                    "notification_channels": ["database", "log"],
                    "active": True,
                },
                {
                    "rule_id": "violentutf_api_config_monitor",
                    "service": "violentutf_api",
                    "environment": "all",
                    "file_patterns": [
                        "violentutf_api/fastapi_app/.env*",
                        "violentutf_api/fastapi_app/app/core/config.py",
                    ],
                    "check_interval_seconds": 300,
                    "drift_threshold_percentage": 2.0,
                    "alert_on_change": True,
                    "alert_on_drift": True,
                    "notification_channels": ["database", "log"],
                    "active": True,
                },
            ],
            "notification_settings": {
                "email": {
                    "enabled": False,
                    "smtp_server": "localhost",
                    "smtp_port": 587,
                    "username": "",
                    "password": "",
                    "recipients": [],
                },
                "webhook": {"enabled": False, "url": "", "headers": {}},
            },
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)

        logger.info("Created default monitoring configuration: %s", config_file)

    def _setup_alert_handlers(self) -> None:
        """Set up alert notification handlers."""
        self.alert_handlers = {
            "database": self._handle_database_alert,
            "log": self._handle_log_alert,
            "email": self._handle_email_alert,
            "webhook": self._handle_webhook_alert,
            "console": self._handle_console_alert,
        }

    def start_monitoring(self) -> None:
        """Start the configuration monitoring system."""
        if self.running:
            logger.warning("Monitoring is already running")
            return

        logger.info("Starting configuration monitoring system")
        self.running = True

        # Initialize baselines
        self._initialize_baselines()

        # Start file system watchers
        self._start_file_watchers()

        # Start scheduled monitoring
        self._start_scheduled_monitoring()

        logger.info("Configuration monitoring system started")

    def stop_monitoring(self) -> None:
        """Stop the configuration monitoring system."""
        if not self.running:
            logger.warning("Monitoring is not running")
            return

        logger.info("Stopping configuration monitoring system")
        self.running = False

        # Stop file system watchers
        for observer in self.file_observers.values():
            observer.stop()
            observer.join()

        self.file_observers.clear()

        # Stop scheduled monitoring
        schedule.clear()

        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)

        logger.info("Configuration monitoring system stopped")

    def _initialize_baselines(self) -> None:
        """Initialize configuration baselines."""
        logger.info("Initializing configuration baselines")

        for rule in self.monitoring_rules.values():
            if not rule.active:
                continue

            for pattern in rule.file_patterns:
                for file_path in Path(".").glob(pattern):
                    if file_path.is_file():
                        self._create_or_update_baseline(rule.service, rule.environment, str(file_path))

    def _create_or_update_baseline(self, service: str, environment: str, file_path: str) -> None:
        """Create or update baseline for a configuration file."""
        try:
            full_path = Path(file_path)
            if not full_path.exists():
                return

            # Calculate checksum
            checksum = self._calculate_file_checksum(full_path)

            # Get content preview
            content_preview = self._get_file_preview(full_path)

            # Store baseline
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO configuration_baselines
                (service, environment, file_path, file_checksum, file_content_preview)
                VALUES (?, ?, ?, ?, ?)
            """,
                (service, environment, file_path, checksum, content_preview),
            )

            conn.commit()
            conn.close()

            # Cache checksum
            self.baseline_checksums[file_path] = checksum

            logger.debug("Updated baseline for %s", file_path)

        except Exception as e:
            logger.error("Error creating baseline for %s: %s", file_path, e)

    def _start_file_watchers(self) -> None:
        """Start file system watchers for real-time monitoring."""
        for rule in self.monitoring_rules.values():
            if not rule.active:
                continue

            for pattern in rule.file_patterns:
                # Get directory to watch
                watch_dir = Path(pattern).parent if "*" not in str(Path(pattern).parent) else Path(".")

                if watch_dir not in self.file_observers:
                    event_handler = ConfigurationFileHandler(self, rule)
                    observer = Observer()
                    observer.schedule(event_handler, str(watch_dir), recursive=True)
                    observer.start()

                    self.file_observers[str(watch_dir)] = observer
                    logger.debug("Started file watcher for %s", watch_dir)

    def _start_scheduled_monitoring(self) -> None:
        """Start scheduled monitoring checks."""
        # Schedule periodic drift checks
        for rule in self.monitoring_rules.values():
            if not rule.active:
                continue

            # Schedule periodic check
            check_interval = rule.check_interval_seconds
            schedule.every(check_interval).seconds.do(self._perform_scheduled_check, rule.rule_id)

        # Schedule daily cleanup
        schedule.every().day.at("02:00").do(self._cleanup_old_data)

        # Start scheduler thread
        self.monitor_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.monitor_thread.start()

    def _run_scheduler(self) -> None:
        """Run the scheduled monitoring tasks."""
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def _perform_scheduled_check(self, rule_id: str) -> None:
        """Perform a scheduled monitoring check."""
        rule = self.monitoring_rules.get(rule_id)
        if not rule or not rule.active:
            return

        logger.debug("Performing scheduled check for rule %s", rule_id)

        for pattern in rule.file_patterns:
            for file_path in Path(".").glob(pattern):
                if file_path.is_file():
                    self._check_file_for_drift(rule, str(file_path))

    def _check_file_for_drift(self, rule: ConfigurationMonitoringRule, file_path: str) -> None:
        """Check a file for configuration drift."""
        try:
            # Calculate current checksum
            current_checksum = self._calculate_file_checksum(Path(file_path))

            # Get baseline checksum
            baseline_checksum = self.baseline_checksums.get(file_path)
            if not baseline_checksum:
                # No baseline, create one
                self._create_or_update_baseline(rule.service, rule.environment, file_path)
                return

            # Check for changes
            if current_checksum != baseline_checksum:
                # Calculate drift percentage (simplified)
                drift_percentage = self._calculate_drift_percentage(file_path, baseline_checksum, current_checksum)

                # Record change
                self._record_configuration_change(
                    rule.rule_id,
                    rule.service,
                    rule.environment,
                    file_path,
                    "drift_detected",
                    baseline_checksum,
                    current_checksum,
                    drift_percentage,
                )

                # Check if alert should be triggered
                if rule.alert_on_drift and drift_percentage > rule.drift_threshold_percentage:
                    self._trigger_alert(
                        rule,
                        "drift",
                        "medium",
                        [file_path],
                        f"Configuration drift detected in {file_path}: {drift_percentage:.1f}% change",
                        {"drift_percentage": drift_percentage, "file_path": file_path},
                    )
                elif rule.alert_on_change:
                    self._trigger_alert(
                        rule,
                        "change",
                        "low",
                        [file_path],
                        f"Configuration change detected in {file_path}",
                        {"drift_percentage": drift_percentage, "file_path": file_path},
                    )

                # Update baseline
                self.baseline_checksums[file_path] = current_checksum
                self._create_or_update_baseline(rule.service, rule.environment, file_path)

        except Exception as e:
            logger.error("Error checking drift for %s: %s", file_path, e)

    def _calculate_drift_percentage(self, file_path: str, baseline_checksum: str, current_checksum: str) -> float:
        """Calculate drift percentage between two configurations.

        Args:
            file_path: Path to configuration file
            baseline_checksum: Baseline checksum
            current_checksum: Current checksum

        Returns:
            Drift percentage (0-100)
        """
        # Simplified drift calculation based on file size and checksum difference
        try:
            file_size = Path(file_path).stat().st_size

            # Convert checksums to integers for comparison
            baseline_int = int(baseline_checksum[:8], 16)
            current_int = int(current_checksum[:8], 16)

            # Calculate difference as percentage
            diff = abs(baseline_int - current_int)
            max_val = max(baseline_int, current_int)

            if max_val == 0:
                return 0.0

            # Normalize by file size for better accuracy
            drift_percentage = (diff / max_val) * 100

            # Adjust based on file size (larger files might have smaller relative changes)
            if file_size > 10000:  # Files larger than 10KB
                drift_percentage *= 0.8

            return min(drift_percentage, 100.0)

        except Exception as e:
            logger.debug("Error calculating drift percentage: %s", e)
            return 50.0  # Default to moderate drift if calculation fails

    def _trigger_alert(
        self,
        rule: ConfigurationMonitoringRule,
        alert_type: str,
        severity: str,
        affected_files: List[str],
        message: str,
        data: Dict[str, Any],
    ) -> None:
        """Trigger a configuration alert."""
        alert = ConfigurationAlert(
            alert_id=f"{rule.rule_id}_{alert_type}_{int(time.time())}",
            rule_id=rule.rule_id,
            alert_type=alert_type,
            severity=severity,
            service=rule.service,
            environment=rule.environment,
            affected_files=affected_files,
            alert_message=message,
            alert_data=data,
        )

        # Store alert in database
        self._store_alert(alert)

        # Send notifications
        for channel in rule.notification_channels:
            if channel in self.alert_handlers:
                try:
                    self.alert_handlers[channel](alert)
                except Exception as e:
                    logger.error("Error sending alert to %s: %s", channel, e)

        logger.info("Alert triggered: %s - %s", alert.alert_id, alert.alert_message)

    def _record_configuration_change(
        self,
        rule_id: str,
        service: str,
        environment: str,
        file_path: str,
        change_type: str,
        old_checksum: str,
        new_checksum: str,
        drift_percentage: float,
    ) -> None:
        """Record a configuration change in the database."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO configuration_changes
            (rule_id, service, environment, file_path, change_type,
             old_checksum, new_checksum, drift_percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (rule_id, service, environment, file_path, change_type, old_checksum, new_checksum, drift_percentage),
        )

        conn.commit()
        conn.close()

    def _store_alert(self, alert: ConfigurationAlert) -> None:
        """Store alert in database."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO alerts
            (alert_id, rule_id, alert_type, severity, service, environment,
             affected_files, alert_message, alert_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                alert.alert_id,
                alert.rule_id,
                alert.alert_type,
                alert.severity,
                alert.service,
                alert.environment,
                ",".join(alert.affected_files),
                alert.alert_message,
                json.dumps(alert.alert_data),
            ),
        )

        conn.commit()
        conn.close()

    def _store_monitoring_rule(self, rule: ConfigurationMonitoringRule) -> None:
        """Store monitoring rule in database."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO monitoring_rules
            (rule_id, service, environment, file_patterns, check_interval_seconds,
             drift_threshold_percentage, alert_on_change, alert_on_drift,
             notification_channels, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                rule.rule_id,
                rule.service,
                rule.environment,
                ",".join(rule.file_patterns),
                rule.check_interval_seconds,
                rule.drift_threshold_percentage,
                rule.alert_on_change,
                rule.alert_on_drift,
                ",".join(rule.notification_channels),
                rule.active,
            ),
        )

        conn.commit()
        conn.close()

    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file."""
        if not file_path.exists():
            return ""

        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error("Error calculating checksum for %s: %s", file_path, e)
            return "error"

    def _get_file_preview(self, file_path: Path, max_length: int = 500) -> str:
        """Get a preview of file content."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(max_length)
                if len(content) == max_length:
                    content += "..."
                return content
        except Exception as e:
            logger.debug("Could not read file preview for %s: %s", file_path, e)
            return f"<Error reading file: {e}>"

    def _cleanup_old_data(self) -> None:
        """Clean up old monitoring data."""
        try:
            cutoff_date = datetime.now() - timedelta(days=30)
            cutoff_timestamp = cutoff_date.isoformat()

            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()

            # Clean up old configuration changes
            cursor.execute(
                """
                DELETE FROM configuration_changes
                WHERE detected_timestamp < ?
            """,
                (cutoff_timestamp,),
            )

            # Clean up resolved alerts older than 7 days
            alert_cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute(
                """
                DELETE FROM alerts
                WHERE resolved = TRUE AND resolved_timestamp < ?
            """,
                (alert_cutoff,),
            )

            conn.commit()
            conn.close()

            logger.info("Cleaned up old monitoring data")

        except Exception as e:
            logger.error("Error cleaning up old data: %s", e)

    # Alert handlers
    def _handle_database_alert(self, alert: ConfigurationAlert) -> None:
        """Handle database alert (already stored by default)."""
        # Alert is already stored in database - no additional action needed
        return

    def _handle_log_alert(self, alert: ConfigurationAlert) -> None:
        """Handle log alert."""
        log_level = {
            "low": logging.INFO,
            "medium": logging.WARNING,
            "high": logging.ERROR,
            "critical": logging.CRITICAL,
        }.get(alert.severity, logging.INFO)

        logger.log(log_level, "CONFIG ALERT [%s]: %s", alert.severity.upper(), alert.alert_message)

    def _handle_console_alert(self, alert: ConfigurationAlert) -> None:
        """Handle console alert."""
        print("\n*** CONFIGURATION ALERT ***")
        print(f"ID: {alert.alert_id}")
        print(f"Service: {alert.service} ({alert.environment})")
        print(f"Type: {alert.alert_type}")
        print(f"Severity: {alert.severity}")
        print(f"Message: {alert.alert_message}")
        print(f"Files: {', '.join(alert.affected_files)}")
        print(f"Time: {alert.created_timestamp}")
        print("****************************\n")

    def _handle_email_alert(self, alert: ConfigurationAlert) -> None:
        """Handle email alert."""
        # Email functionality would be implemented here
        logger.debug("Email alert would be sent for %s", alert.alert_id)

    def _handle_webhook_alert(self, alert: ConfigurationAlert) -> None:
        """Handle webhook alert."""
        # Webhook functionality would be implemented here
        logger.debug("Webhook alert would be sent for %s", alert.alert_id)

    def get_active_alerts(
        self, service: Optional[str] = None, environment: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get active (unresolved) alerts."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        query = "SELECT * FROM alerts WHERE resolved = FALSE"
        params = []

        if service:
            query += " AND service = ?"
            params.append(service)

        if environment:
            query += " AND environment = ?"
            params.append(environment)

        query += " ORDER BY created_timestamp DESC"

        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return results

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE alerts
            SET acknowledged = TRUE, acknowledged_timestamp = ?
            WHERE alert_id = ?
        """,
            (datetime.now().isoformat(), alert_id),
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if success:
            logger.info("Alert %s acknowledged", alert_id)

        return success

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE alerts
            SET resolved = TRUE, resolved_timestamp = ?
            WHERE alert_id = ?
        """,
            (datetime.now().isoformat(), alert_id),
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if success:
            logger.info("Alert %s resolved", alert_id)

        return success


class ConfigurationFileHandler(FileSystemEventHandler):
    """File system event handler for configuration files."""

    def __init__(self, monitor: ConfigurationMonitor, rule: ConfigurationMonitoringRule) -> None:
        """Initialize the file handler.

        Args:
            monitor: Configuration monitor instance
            rule: Monitoring rule
        """
        self.monitor = monitor
        self.rule = rule
        super().__init__()

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = event.src_path

        # Check if file matches any of the rule patterns
        for pattern in self.rule.file_patterns:
            if Path(file_path).match(pattern):
                logger.debug("Configuration file modified: %s", file_path)

                # Wait a moment for file write to complete
                time.sleep(0.5)

                # Check for drift
                self.monitor._check_file_for_drift(self.rule, file_path)  # pylint: disable=protected-access
                break


def main() -> None:
    """Run configuration monitoring from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="ViolentUTF Configuration Drift Monitor")
    parser.add_argument("--start", action="store_true", help="Start monitoring daemon")
    parser.add_argument("--stop", action="store_true", help="Stop monitoring daemon")
    parser.add_argument("--status", action="store_true", help="Show monitoring status")
    parser.add_argument("--alerts", action="store_true", help="Show active alerts")
    parser.add_argument("--acknowledge", help="Acknowledge alert by ID")
    parser.add_argument("--resolve", help="Resolve alert by ID")
    parser.add_argument("--config", default="monitor_config.yaml", help="Configuration file path")
    parser.add_argument("--database", default="config_monitoring.db", help="Database file path")
    parser.add_argument("--service", help="Filter by service")
    parser.add_argument("--environment", help="Filter by environment")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize monitor
    monitor = ConfigurationMonitor(args.database, args.config)

    if args.start:
        print("Starting configuration monitoring...")
        monitor.start_monitoring()

        try:
            # Keep running until interrupted
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping configuration monitoring...")
            monitor.stop_monitoring()

    elif args.stop:
        print("Stopping configuration monitoring...")
        monitor.stop_monitoring()

    elif args.alerts:
        alerts = monitor.get_active_alerts(args.service, args.environment)

        if alerts:
            print(f"Active Alerts ({len(alerts)}):")
            for alert in alerts:
                ack_status = "ACK" if alert["acknowledged"] else "---"
                print(f"  [{ack_status}] {alert['alert_id']}: {alert['service']}/{alert['environment']}")
                print(f"       {alert['severity'].upper()}: {alert['alert_message']}")
                print(f"       Created: {alert['created_timestamp']}")
                print()
        else:
            print("No active alerts")

    elif args.acknowledge:
        success = monitor.acknowledge_alert(args.acknowledge)
        if success:
            print(f"Alert {args.acknowledge} acknowledged")
        else:
            print(f"Failed to acknowledge alert {args.acknowledge}")

    elif args.resolve:
        success = monitor.resolve_alert(args.resolve)
        if success:
            print(f"Alert {args.resolve} resolved")
        else:
            print(f"Failed to resolve alert {args.resolve}")

    elif args.status:
        # Show monitoring status
        rules_count = len([r for r in monitor.monitoring_rules.values() if r.active])
        alerts = monitor.get_active_alerts()

        print("Configuration Monitoring Status:")
        print(f"  Active Rules: {rules_count}")
        print(f"  Active Alerts: {len(alerts)}")
        print(f"  Database: {args.database}")
        print(f"  Configuration: {args.config}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
