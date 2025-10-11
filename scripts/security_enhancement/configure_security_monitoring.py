#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Security Monitoring Configuration CLI

Command-line interface for configuring real-time security monitoring
and threat detection.

Issue #273: Phase 6.2 - Database Encryption and Security Enhancement

Usage:
    python3 configure_security_monitoring.py --real-time
    python3 configure_security_monitoring.py --threat-type brute-force
    python3 configure_security_monitoring.py --setup-anomaly-detection
    python3 configure_security_monitoring.py --setup-dashboard
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.security_enhancement.core.security_monitor import (  # noqa: E402
    SecurityMonitor,
)


def configure_brute_force_detection(verbose: bool = False) -> Dict[str, Any]:
    """
    Configure brute force attack detection

    Args:
        verbose: Enable verbose output

    Returns:
        Configuration status dictionary
    """
    if verbose:
        print("Configuring brute force attack detection...")

    monitor = SecurityMonitor()
    result = monitor.configure_monitoring_rule(
        rule_name="brute_force_detection",
        event="failed_login",
        threshold=5,
        window_minutes=5,
    )

    if result.get("status") == "configured":
        if verbose:
            print("  ✓ Brute force detection configured (5 failed logins in 5 minutes)")
    else:
        if verbose:
            print("  ✗ Failed to configure brute force detection")

    return result


def configure_privilege_escalation_detection(verbose: bool = False) -> Dict[str, Any]:
    """
    Configure privilege escalation detection

    Args:
        verbose: Enable verbose output

    Returns:
        Configuration status dictionary
    """
    if verbose:
        print("Configuring privilege escalation detection...")

    monitor = SecurityMonitor()
    result = monitor.configure_monitoring_rule(
        rule_name="privilege_escalation",
        event="privilege_change",
        condition="non_admin_granting_admin",
    )

    if result.get("status") == "configured":
        if verbose:
            print("  ✓ Privilege escalation detection configured (non-admin granting admin)")
    else:
        if verbose:
            print("  ✗ Failed to configure privilege escalation detection")

    return result


def configure_data_exfiltration_detection(verbose: bool = False) -> Dict[str, Any]:
    """
    Configure data exfiltration detection

    Args:
        verbose: Enable verbose output

    Returns:
        Configuration status dictionary
    """
    if verbose:
        print("Configuring data exfiltration detection...")

    monitor = SecurityMonitor()
    result = monitor.configure_monitoring_rule(
        rule_name="data_exfiltration",
        event="large_data_export",
        threshold=1000,
        window_minutes=60,
    )

    if result.get("status") == "configured":
        if verbose:
            print("  ✓ Data exfiltration detection configured (1000+ records in 60 minutes)")
    else:
        if verbose:
            print("  ✗ Failed to configure data exfiltration detection")

    return result


def configure_configuration_tampering_detection(
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Configure configuration tampering detection

    Args:
        verbose: Enable verbose output

    Returns:
        Configuration status dictionary
    """
    if verbose:
        print("Configuring configuration tampering detection...")

    monitor = SecurityMonitor()
    result = monitor.configure_monitoring_rule(
        rule_name="config_tampering",
        event="security_config_change",
        condition="unauthorized_user",
    )

    if result.get("status") == "configured":
        if verbose:
            print("  ✓ Configuration tampering detection configured (unauthorized user)")
    else:
        if verbose:
            print("  ✗ Failed to configure configuration tampering detection")

    return result


def setup_anomaly_detection(
    baseline_days: int = 30,
    deviation_threshold: int = 3,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Configure anomaly detection system.

    Args:
        baseline_days: Number of days for baseline calculation
        deviation_threshold: Standard deviations for anomaly detection
        verbose: Enable verbose output

    Returns:
        Configuration status dictionary
    """
    if verbose:
        print("Setting up anomaly detection...")
        print(f"  Baseline period: {baseline_days} days")
        print(f"  Deviation threshold: {deviation_threshold} std devs")

    monitor = SecurityMonitor()
    result = monitor.setup_anomaly_detection(
        baseline_period_days=baseline_days,
        deviation_threshold=deviation_threshold,
    )

    if result.get("status") == "configured":
        if verbose:
            print("  ✓ Anomaly detection configured")
    else:
        if verbose:
            print("  ✗ Failed to configure anomaly detection")

    return result


def configure_alert_thresholds(
    critical: int = 30,
    warning: int = 60,
    info: int = 90,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Configure alert thresholds

    Args:
        critical: Days before critical alert
        warning: Days before warning alert
        info: Days before info alert
        verbose: Enable verbose output

    Returns:
        Configuration status dictionary
    """
    if verbose:
        print("Configuring alert thresholds...")
        print(f"  Critical: {critical} days")
        print(f"  Warning: {warning} days")
        print(f"  Info: {info} days")

    monitor = SecurityMonitor()
    result = monitor.configure_alerts(
        critical_threshold=critical,
        warning_threshold=warning,
        info_threshold=info,
    )

    if result.get("status") == "configured":
        if verbose:
            print("  ✓ Alert thresholds configured")
    else:
        if verbose:
            print("  ✗ Failed to configure alert thresholds")

    return result


def setup_dashboard(verbose: bool = False) -> Dict[str, Any]:
    """
    Configure security monitoring dashboard.

    Args:
        verbose: Enable verbose output

    Returns:
        Dashboard setup status dictionary
    """
    if verbose:
        print("Setting up security monitoring dashboard...")

    monitor = SecurityMonitor()
    result = monitor.setup_dashboard()

    if result.get("dashboard_status") == "configured":
        if verbose:
            print("  ✓ Dashboard configured with features:")
            for feature in result.get("features", []):
                print(f"    - {feature}")
    else:
        if verbose:
            print("  ✗ Failed to setup dashboard")

    return result


def validate_monitoring_configuration(verbose: bool = False) -> Dict[str, Any]:
    """
    Validate security monitoring configuration

    Args:
        verbose: Enable verbose output

    Returns:
        Validation results dictionary
    """
    if verbose:
        print("Validating security monitoring configuration...")

    monitor = SecurityMonitor()
    result = monitor.validate_monitoring()

    if result.get("valid"):
        if verbose:
            print(f"  ✓ Monitoring configuration valid " f"({result.get('rules_count', 0)} rules)")
    else:
        if verbose:
            print("  ✗ Monitoring configuration invalid")

    return result


def configure_real_time_monitoring(verbose: bool = False) -> Dict[str, Any]:
    """
    Configure comprehensive real-time security monitoring

    Args:
        verbose: Enable verbose output

    Returns:
        Combined configuration status
    """
    result = {
        "components": {},
        "all_configured": False,
    }

    if verbose:
        print("=" * 60)
        print("Configuring real-time security monitoring")
        print("=" * 60)
        print()

    # Configure brute force detection
    brute_force_result = configure_brute_force_detection(verbose=verbose)
    result["components"]["brute_force_detection"] = brute_force_result

    if verbose:
        print()

    # Configure privilege escalation detection
    privilege_escalation_result = configure_privilege_escalation_detection(verbose=verbose)
    result["components"]["privilege_escalation_detection"] = privilege_escalation_result

    if verbose:
        print()

    # Configure data exfiltration detection
    data_exfiltration_result = configure_data_exfiltration_detection(verbose=verbose)
    result["components"]["data_exfiltration_detection"] = data_exfiltration_result

    if verbose:
        print()

    # Configure configuration tampering detection
    config_tampering_result = configure_configuration_tampering_detection(verbose=verbose)
    result["components"]["config_tampering_detection"] = config_tampering_result

    if verbose:
        print()

    # Setup anomaly detection
    anomaly_result = setup_anomaly_detection(verbose=verbose)
    result["components"]["anomaly_detection"] = anomaly_result

    if verbose:
        print()

    # Configure alert thresholds
    alert_result = configure_alert_thresholds(verbose=verbose)
    result["components"]["alert_thresholds"] = alert_result

    if verbose:
        print()

    # Setup dashboard
    dashboard_result = setup_dashboard(verbose=verbose)
    result["components"]["dashboard"] = dashboard_result

    if verbose:
        print()

    # Validate configuration
    validation_result = validate_monitoring_configuration(verbose=verbose)
    result["components"]["validation"] = validation_result

    # Check if all components are configured
    result["all_configured"] = all(
        component.get("status") == "configured"
        or component.get("dashboard_status") == "configured"
        or component.get("valid") is True
        for component in result["components"].values()
        if isinstance(component, dict)
    )

    if verbose:
        print()
        print("=" * 60)
        if result["all_configured"]:
            print("✓ Real-time security monitoring configured")
        else:
            print("✗ Not all monitoring components configured")
        print("=" * 60)

    return result


def main(argv: Optional[List[str]] = None) -> int:
    """Execute main CLI entry point."""
    parser = argparse.ArgumentParser(description="Configure real-time security monitoring")

    parser.add_argument(
        "--real-time",
        action="store_true",
        help="Configure comprehensive real-time monitoring",
    )

    parser.add_argument(
        "--threat-type",
        choices=[
            "brute-force",
            "privilege-escalation",
            "data-exfiltration",
            "config-tampering",
        ],
        help="Configure specific threat detection",
    )

    parser.add_argument(
        "--setup-anomaly-detection",
        action="store_true",
        help="Setup anomaly detection",
    )

    parser.add_argument(
        "--baseline-days",
        type=int,
        default=30,
        help="Baseline period in days (default: 30)",
    )

    parser.add_argument(
        "--deviation-threshold",
        type=int,
        default=3,
        help="Standard deviations for anomaly (default: 3)",
    )

    parser.add_argument(
        "--setup-dashboard",
        action="store_true",
        help="Setup security monitoring dashboard",
    )

    parser.add_argument(
        "--configure-alerts",
        action="store_true",
        help="Configure alert thresholds",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate monitoring configuration",
    )

    parser.add_argument(
        "--report-format",
        choices=["json", "yaml", "html"],
        default="json",
        help="Output report format",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Report output directory",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args(argv)

    if args.real_time:
        report = configure_real_time_monitoring(verbose=args.verbose)
    elif args.threat_type == "brute-force":
        report = configure_brute_force_detection(verbose=args.verbose)
    elif args.threat_type == "privilege-escalation":
        report = configure_privilege_escalation_detection(verbose=args.verbose)
    elif args.threat_type == "data-exfiltration":
        report = configure_data_exfiltration_detection(verbose=args.verbose)
    elif args.threat_type == "config-tampering":
        report = configure_configuration_tampering_detection(verbose=args.verbose)
    elif args.setup_anomaly_detection:
        report = setup_anomaly_detection(
            baseline_days=args.baseline_days,
            deviation_threshold=args.deviation_threshold,
            verbose=args.verbose,
        )
    elif args.setup_dashboard:
        report = setup_dashboard(verbose=args.verbose)
    elif args.configure_alerts:
        report = configure_alert_thresholds(verbose=args.verbose)
    elif args.validate:
        report = validate_monitoring_configuration(verbose=args.verbose)
    else:
        # Default to real-time monitoring
        report = configure_real_time_monitoring(verbose=args.verbose)

    # Output report
    if args.report_format == "json":
        if not args.verbose:
            output = json.dumps(report, indent=2)
            print(output)

        if args.output_dir:
            output_path = Path(args.output_dir) / "security_monitoring_config_report.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(report, indent=2))
            if args.verbose:
                print(f"\nReport saved to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
