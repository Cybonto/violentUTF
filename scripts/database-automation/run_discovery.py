#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Command-line interface for ViolentUTF database discovery system.

Implements GitHub Issue #279 requirements.
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import click
import yaml

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from discovery.models import DiscoveryConfig, DiscoveryReport  # noqa: E402
from discovery.orchestrator import DiscoveryOrchestrator  # noqa: E402
from discovery.utils import setup_logging  # noqa: E402


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--log-file", type=str, help="Log file path")
@click.pass_context
def cli(ctx, verbose: bool, log_file: str) -> None:  # noqa: ANN001
    """Database Discovery CLI - Issue #279 Implementation."""
    ctx.ensure_object(dict)

    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logger = setup_logging("discovery_cli", log_level, log_file)
    ctx.obj["logger"] = logger

    logger.info("ViolentUTF Database Discovery CLI started")


@cli.command()
@click.option("--config", "-c", "config_file", type=click.Path(exists=True), help="Configuration file path")
@click.option("--output-dir", "-o", type=str, help="Output directory for reports")
@click.option(
    "--format", "output_format", type=click.Choice(["json", "markdown", "both"]), default="both", help="Output format"
)
@click.option("--parallel/--sequential", default=True, help="Use parallel processing")
@click.option("--timeout", type=int, default=300, help="Maximum execution time in seconds")
@click.option("--scan-path", multiple=True, help="Additional scan paths")
@click.option("--exclude-container", is_flag=True, help="Disable container discovery")
@click.option("--exclude-network", is_flag=True, help="Disable network discovery")
@click.option("--exclude-filesystem", is_flag=True, help="Disable filesystem discovery")
@click.option("--exclude-code", is_flag=True, help="Disable code discovery")
@click.option("--exclude-security", is_flag=True, help="Disable security scanning")
@click.pass_context
def run(
    ctx: click.Context,  # type: ignore[no-untyped-def]
    config_file: str,
    output_dir: str,
    output_format: str,
    parallel: bool,
    timeout: int,
    scan_path: tuple,
    exclude_container: bool,
    exclude_network: bool,
    exclude_filesystem: bool,
    exclude_code: bool,
    exclude_security: bool,
) -> None:
    """Execute full database discovery process."""
    logger = ctx.obj["logger"]

    try:
        # Load configuration
        if config_file:
            discovery_config = load_config_file(config_file, logger)
        else:
            discovery_config = create_default_violentutf_config()

        # Apply CLI overrides
        if scan_path:
            discovery_config.scan_paths.extend(list(scan_path))

        discovery_config.enable_parallel_processing = parallel
        discovery_config.max_execution_time_seconds = timeout

        if exclude_container:
            discovery_config.enable_container_discovery = False
        if exclude_network:
            discovery_config.enable_network_discovery = False
        if exclude_filesystem:
            discovery_config.enable_filesystem_discovery = False
        if exclude_code:
            discovery_config.enable_code_discovery = False
        if exclude_security:
            discovery_config.enable_security_scanning = False

        logger.info(f"Starting discovery with timeout: {timeout}s")
        logger.info(
            f"Enabled modules: Container={discovery_config.enable_container_discovery}, "
            f"Network={discovery_config.enable_network_discovery}, "
            f"Filesystem={discovery_config.enable_filesystem_discovery}, "
            f"Code={discovery_config.enable_code_discovery}, "
            f"Security={discovery_config.enable_security_scanning}"
        )

        # Execute discovery
        orchestrator = DiscoveryOrchestrator(discovery_config)

        start_time = time.time()
        report = orchestrator.execute_full_discovery()
        execution_time = time.time() - start_time

        logger.info(f"Discovery completed in {execution_time:.2f} seconds")
        logger.info(f"Found {report.total_discoveries} databases")

        # Save report
        if output_dir:
            report_dir = Path(output_dir)
            report_dir.mkdir(parents=True, exist_ok=True)
        else:
            report_dir = None

        saved_dir = orchestrator.save_report(report, str(report_dir) if report_dir else None)

        # Display summary
        display_summary(report, logger)

        click.echo(f"\nReport saved to: {saved_dir}")

        # Exit with error code if high-severity security findings
        if report.high_severity_findings > 0:
            logger.warning(f"Found {report.high_severity_findings} high-severity security findings")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Discovery interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        if ctx.obj.get("verbose"):
            import traceback

            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option("--output", "-o", type=click.Path(), help="Output configuration file path")
@click.option("--violentutf", is_flag=True, help="Generate ViolentUTF-specific configuration")
@click.pass_context
def config(ctx: click.Context, output: str, violentutf: bool) -> None:  # type: ignore[no-untyped-def]
    """Generate discovery configuration file."""
    logger = ctx.obj["logger"]

    try:
        if violentutf:
            config_data = create_default_violentutf_config()
            logger.info("Generated ViolentUTF-specific configuration")
        else:
            config_data = DiscoveryConfig()
            logger.info("Generated default configuration")

        # Convert to dictionary for serialization
        config_dict = {
            "discovery": {
                "container_discovery": config_data.enable_container_discovery,
                "network_discovery": config_data.enable_network_discovery,
                "filesystem_discovery": config_data.enable_filesystem_discovery,
                "code_discovery": config_data.enable_code_discovery,
                "security_scanning": config_data.enable_security_scanning,
            },
            "container": {
                "scan_compose_files": config_data.scan_compose_files,
                "compose_file_patterns": config_data.compose_file_patterns,
            },
            "network": {
                "network_ranges": config_data.network_ranges,
                "database_ports": config_data.database_ports,
                "timeout_seconds": config_data.network_timeout_seconds,
                "max_concurrent_scans": config_data.max_concurrent_scans,
            },
            "filesystem": {
                "scan_paths": config_data.scan_paths,
                "file_extensions": config_data.file_extensions,
                "max_file_size_mb": config_data.max_file_size_mb,
            },
            "code_analysis": {
                "code_extensions": config_data.code_extensions,
                "exclude_patterns": config_data.exclude_patterns,
            },
            "security": {
                "secrets_baseline_file": config_data.secrets_baseline_file,
                "bandit_config_file": config_data.bandit_config_file,
                "exclude_security_paths": config_data.exclude_security_paths,
            },
            "performance": {
                "max_execution_time_seconds": config_data.max_execution_time_seconds,
                "max_memory_usage_mb": config_data.max_memory_usage_mb,
                "enable_parallel_processing": config_data.enable_parallel_processing,
                "max_workers": config_data.max_workers,
            },
            "output": {
                "output_format": config_data.output_format,
                "include_raw_data": config_data.include_raw_data,
                "include_security_details": config_data.include_security_details,
                "validation_enabled": config_data.validation_enabled,
            },
        }

        if output:
            output_path = Path(output)
        else:
            suffix = "_violentutf" if violentutf else ""
            output_path = Path(f"discovery_config{suffix}.yml")

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

        click.echo(f"Configuration saved to: {output_path}")

    except Exception as e:
        logger.error(f"Failed to generate configuration: {e}")
        sys.exit(1)


@cli.command()
@click.option("--report-id", "-r", required=True, help="Report ID to display")
@click.option(
    "--format", "output_format", type=click.Choice(["summary", "detailed"]), default="summary", help="Display format"
)
@click.option("--show-security", is_flag=True, help="Show security findings")
@click.pass_context
def show(
    ctx: click.Context, report_id: str, output_format: str, show_security: bool
) -> None:  # type: ignore[no-untyped-def]
    """Display discovery report."""
    logger = ctx.obj["logger"]

    try:
        # Look for report files
        report_file = None

        # Check current directory
        json_file = Path(f"{report_id}.json")
        if json_file.exists():
            report_file = json_file
        else:
            # Check reports directory
            reports_dir = Path("reports")
            if reports_dir.exists():
                for report_dir in reports_dir.iterdir():
                    if report_dir.is_dir():
                        json_file = report_dir / f"{report_id}.json"
                        if json_file.exists():
                            report_file = json_file
                            break

        if not report_file:
            click.echo(f"Report {report_id} not found")
            sys.exit(1)

        # Load and display report
        with open(report_file, "r", encoding="utf-8") as f:
            report_data = json.load(f)

        display_report(report_data, output_format, show_security)

    except Exception as e:
        logger.error(f"Failed to display report: {e}")
        sys.exit(1)


@cli.command()
@click.option("--days", type=int, default=7, help="Show reports from last N days")
@click.pass_context
def list_reports(ctx: click.Context, days: int) -> None:  # type: ignore[no-untyped-def]
    """List available discovery reports."""
    logger = ctx.obj["logger"]

    try:
        reports = find_reports(days)

        if not reports:
            click.echo("No reports found")
            return

        click.echo(f"Discovery Reports (last {days} days):")
        click.echo("-" * 50)

        for report in reports:
            click.echo(f"ID: {report['id']}")
            click.echo(f"Date: {report['date']}")
            click.echo(f"Databases: {report['databases']}")
            click.echo(f"Execution Time: {report['execution_time']:.2f}s")
            if report["security_findings"] > 0:
                click.echo(f"Security Findings: {report['security_findings']}")
            click.echo("-" * 30)

    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def validate(ctx: click.Context) -> None:  # type: ignore[no-untyped-def]
    """Validate ViolentUTF environment for discovery."""
    logger = ctx.obj["logger"]

    try:
        click.echo("Validating ViolentUTF environment...")

        validation_results = validate_environment(logger)

        click.echo("\nValidation Results:")
        click.echo("=" * 50)

        all_passed = True
        for check, result in validation_results.items():
            status = "✓ PASS" if result["passed"] else "✗ FAIL"
            click.echo(f"{check}: {status}")
            if result["message"]:
                click.echo(f"  {result['message']}")
            if not result["passed"]:
                all_passed = False

        click.echo("=" * 50)

        if all_passed:
            click.echo("Environment validation PASSED")
        else:
            click.echo("Environment validation FAILED")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)


def load_config_file(config_path: str, logger: logging.Logger) -> DiscoveryConfig:
    """Load configuration from file."""
    config_file = Path(config_path)

    with open(config_file, "r", encoding="utf-8") as f:
        if config_file.suffix.lower() in [".yml", ".yaml"]:
            config_data = yaml.safe_load(f)
        else:
            config_data = json.load(f)

    logger.info(f"Loaded configuration from: {config_path}")

    # Convert to DiscoveryConfig
    return DiscoveryConfig(
        enable_container_discovery=config_data.get("discovery", {}).get("container_discovery", True),
        enable_network_discovery=config_data.get("discovery", {}).get("network_discovery", True),
        enable_filesystem_discovery=config_data.get("discovery", {}).get("filesystem_discovery", True),
        enable_code_discovery=config_data.get("discovery", {}).get("code_discovery", True),
        enable_security_scanning=config_data.get("discovery", {}).get("security_scanning", True),
        scan_compose_files=config_data.get("container", {}).get("scan_compose_files", True),
        compose_file_patterns=config_data.get("container", {}).get(
            "compose_file_patterns", ["docker-compose*.yml", "docker-compose*.yaml"]
        ),
        network_ranges=config_data.get("network", {}).get("network_ranges", ["127.0.0.1", "localhost"]),
        database_ports=config_data.get("network", {}).get("database_ports", [5432, 3306, 1433, 27017, 6379]),
        network_timeout_seconds=config_data.get("network", {}).get("timeout_seconds", 5),
        max_concurrent_scans=config_data.get("network", {}).get("max_concurrent_scans", 10),
        scan_paths=config_data.get("filesystem", {}).get("scan_paths", []),
        file_extensions=config_data.get("filesystem", {}).get(
            "file_extensions", [".db", ".sqlite", ".sqlite3", ".duckdb"]
        ),
        max_file_size_mb=config_data.get("filesystem", {}).get("max_file_size_mb", 1000),
        code_extensions=config_data.get("code_analysis", {}).get(
            "code_extensions", [".py", ".yml", ".yaml", ".json", ".env"]
        ),
        exclude_patterns=config_data.get("code_analysis", {}).get(
            "exclude_patterns", ["__pycache__", ".git", "node_modules", ".venv", "venv", ".pytest_cache"]
        ),
        secrets_baseline_file=config_data.get("security", {}).get("secrets_baseline_file"),
        bandit_config_file=config_data.get("security", {}).get("bandit_config_file"),
        exclude_security_paths=config_data.get("security", {}).get("exclude_security_paths", ["tests/", "test/"]),
        max_execution_time_seconds=config_data.get("performance", {}).get("max_execution_time_seconds", 300),
        max_memory_usage_mb=config_data.get("performance", {}).get("max_memory_usage_mb", 512),
        enable_parallel_processing=config_data.get("performance", {}).get("enable_parallel_processing", True),
        max_workers=config_data.get("performance", {}).get("max_workers", 4),
        output_format=config_data.get("output", {}).get("output_format", "json"),
        include_raw_data=config_data.get("output", {}).get("include_raw_data", False),
        include_security_details=config_data.get("output", {}).get("include_security_details", True),
        validation_enabled=config_data.get("output", {}).get("validation_enabled", True),
    )


def create_default_violentutf_config() -> DiscoveryConfig:
    """Create ViolentUTF-specific configuration."""
    current_dir = Path.cwd()

    return DiscoveryConfig(
        enable_container_discovery=True,
        enable_network_discovery=True,
        enable_filesystem_discovery=True,
        enable_code_discovery=True,
        enable_security_scanning=True,
        scan_compose_files=True,
        compose_file_patterns=["docker-compose*.yml", "docker-compose*.yaml"],
        network_ranges=["127.0.0.1"],
        database_ports=[5432, 8080, 9080, 8501, 3306, 1433, 27017, 6379],
        network_timeout_seconds=5,
        max_concurrent_scans=10,
        scan_paths=[
            str(current_dir),
            str(current_dir / "violentutf_api" / "fastapi_app" / "app_data"),
            str(current_dir / "violentutf" / "app_data"),
            str(current_dir / "keycloak"),
            str(current_dir / "apisix"),
        ],
        file_extensions=[".db", ".sqlite", ".sqlite3", ".duckdb"],
        max_file_size_mb=1000,
        code_extensions=[".py", ".yml", ".yaml", ".json", ".env"],
        exclude_patterns=[
            "__pycache__",
            ".git",
            "node_modules",
            ".venv",
            "venv",
            ".pytest_cache",
            "violentutf_logs",
            "test_",
            "tests/",
        ],
        exclude_security_paths=["tests/", "test/", "violentutf_logs/"],
        max_execution_time_seconds=300,
        max_memory_usage_mb=512,
        enable_parallel_processing=True,
        max_workers=4,
        output_format="json",
        include_raw_data=False,
        include_security_details=True,
        validation_enabled=True,
    )


def display_summary(report: DiscoveryReport, logger: logging.Logger) -> None:
    """Display discovery summary."""
    click.echo("\n" + "=" * 60)
    click.echo("DISCOVERY SUMMARY")
    click.echo("=" * 60)

    click.echo(f"Report ID: {report.report_id}")
    click.echo(f"Execution Time: {report.execution_time_seconds:.2f} seconds")
    click.echo(f"Total Databases: {report.total_discoveries}")

    if report.type_counts:
        click.echo("\nDatabase Types:")
        for db_type, count in report.type_counts.items():
            click.echo(f"  {db_type.value.title()}: {count}")

    if report.method_counts:
        click.echo("\nDiscovery Methods:")
        for method, count in report.method_counts.items():
            click.echo(f"  {method.value.replace('_', ' ').title()}: {count}")

    if report.confidence_distribution:
        click.echo("\nConfidence Levels:")
        for confidence, count in report.confidence_distribution.items():
            click.echo(f"  {confidence.value.title()}: {count}")

    if report.security_findings_count > 0:
        click.echo(f"\nSecurity Findings: {report.security_findings_count}")
        if report.credential_exposures > 0:
            click.echo(f"  Credential Exposures: {report.credential_exposures}")
        if report.high_severity_findings > 0:
            click.echo(f"  High Severity: {report.high_severity_findings}")

    click.echo(f"\nValidated Discoveries: {report.validated_discoveries}")
    if report.validation_errors > 0:
        click.echo(f"Validation Errors: {report.validation_errors}")


def display_report(report_data: dict[str, Any], format_type: str, show_security: bool) -> None:
    """Display detailed report."""
    click.echo(f"Report ID: {report_data['report_id']}")
    click.echo(f"Generated: {report_data['generated_at']}")
    click.echo(f"Execution Time: {report_data['execution_time_seconds']:.2f}s")
    click.echo(f"Total Databases: {report_data['total_discoveries']}")

    if format_type == "detailed" and "databases" in report_data:
        click.echo("\nDiscovered Databases:")
        click.echo("-" * 40)

        for i, db in enumerate(report_data["databases"], 1):
            click.echo(f"{i}. {db['name']}")
            click.echo(f"   Type: {db['database_type']}")
            click.echo(f"   Method: {db['discovery_method']}")
            click.echo(f"   Confidence: {db['confidence_level']} ({db['confidence_score']:.2f})")

            if db.get("host"):
                click.echo(f"   Host: {db['host']}:{db.get('port', 'N/A')}")
            if db.get("file_path"):
                click.echo(f"   File: {db['file_path']}")

            if show_security and db.get("security_findings"):
                click.echo(f"   Security Findings: {len(db['security_findings'])}")
                for finding in db["security_findings"][:3]:
                    click.echo(f"     - {finding['severity'].upper()}: {finding['description']}")

            click.echo()


def find_reports(days: int) -> list:
    """Find discovery reports from the last N days."""
    import datetime

    reports = []
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)

    # Check current directory and reports directory
    search_dirs = [Path.cwd(), Path.cwd() / "reports"]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue

        for item in search_dir.iterdir():
            if item.is_file() and item.suffix == ".json" and "discovery_" in item.name:
                try:
                    with open(item, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    report_date = datetime.datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))

                    if report_date >= cutoff_date:
                        reports.append(
                            {
                                "id": data["report_id"],
                                "date": report_date.strftime("%Y-%m-%d %H:%M:%S"),
                                "databases": data["total_discoveries"],
                                "execution_time": data["execution_time_seconds"],
                                "security_findings": data.get("security_findings_count", 0),
                                "file": str(item),
                            }
                        )
                except (json.JSONDecodeError, KeyError):
                    continue
            elif item.is_dir() and item.name.startswith("discovery_"):
                # Check subdirectories
                for json_file in item.glob("*.json"):
                    try:
                        with open(json_file, "r", encoding="utf-8") as f:
                            data = json.load(f)

                        report_date = datetime.datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))

                        if report_date >= cutoff_date:
                            reports.append(
                                {
                                    "id": data["report_id"],
                                    "date": report_date.strftime("%Y-%m-%d %H:%M:%S"),
                                    "databases": data["total_discoveries"],
                                    "execution_time": data["execution_time_seconds"],
                                    "security_findings": data.get("security_findings_count", 0),
                                    "file": str(json_file),
                                }
                            )
                    except (json.JSONDecodeError, KeyError):
                        continue

    return sorted(reports, key=lambda x: x["date"], reverse=True)


def validate_environment(logger: logging.Logger) -> dict[str, dict[str, Any]]:
    """Validate ViolentUTF environment for discovery."""
    results = {}

    # Check if we're in ViolentUTF directory
    current_dir = Path.cwd()
    violentutf_indicators = [
        current_dir / "violentutf_api",
        current_dir / "violentutf",
        current_dir / "keycloak",
        current_dir / "apisix",
    ]

    violentutf_found = any(path.exists() for path in violentutf_indicators)
    results["ViolentUTF Directory"] = {
        "passed": violentutf_found,
        "message": "ViolentUTF directory structure detected" if violentutf_found else "Not in ViolentUTF directory",
    }

    # Check Python dependencies
    required_modules = ["yaml", "pathlib"]
    optional_modules = ["python_on_whales", "nmap", "detect_secrets", "bandit"]

    missing_required = []
    missing_optional = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_required.append(module)

    for module in optional_modules:
        try:
            __import__(module)
        except ImportError:
            missing_optional.append(module)

    results["Required Dependencies"] = {
        "passed": len(missing_required) == 0,
        "message": (
            f'Missing: {", ".join(missing_required)}' if missing_required else "All required dependencies available"
        ),
    }

    results["Optional Dependencies"] = {
        "passed": len(missing_optional) == 0,
        "message": (
            f'Missing: {", ".join(missing_optional)}' if missing_optional else "All optional dependencies available"
        ),
    }

    # Check file permissions
    test_file = current_dir / "test_permissions.tmp"
    try:
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("test")
        test_file.unlink()
        file_perms_ok = True
    except (PermissionError, OSError):
        file_perms_ok = False

    results["File Permissions"] = {
        "passed": file_perms_ok,
        "message": "Can read/write files" if file_perms_ok else "Insufficient file permissions",
    }

    # Check Docker availability (optional)
    docker_available = False
    try:
        import subprocess  # nosec B404 # Needed for Docker availability check

        result = subprocess.run(["docker", "--version"], capture_output=True, timeout=5, check=False)  # nosec B607 B603
        docker_available = result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    results["Docker Access"] = {
        "passed": True,  # Optional
        "message": "Docker available" if docker_available else "Docker not available (optional)",
    }

    return results


if __name__ == "__main__":
    cli.main(prog_name="run_discovery")
