#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""PyRIT API Compatibility Analysis Script

This script analyzes the API differences between PyRIT DuckDBMemory (v0.4.0)
and SQLiteMemory (v0.10.0rc0) to assess migration compatibility.
"""

import inspect
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Optional


def analyze_sqlite_memory_api() -> Dict[str, Any]:
    """Analyze SQLiteMemory API from PyRIT v0.10.0rc0."""
    try:
        from pyrit.memory import SQLiteMemory

        methods_info = {}

        # Get all public methods
        for name in dir(SQLiteMemory):
            if name.startswith("_"):
                continue

            attr = getattr(SQLiteMemory, name)
            if callable(attr):
                try:
                    sig = inspect.signature(attr)
                    methods_info[name] = {
                        "signature": str(sig),
                        "is_async": inspect.iscoroutinefunction(attr),
                        "type": "method",
                    }
                except (ValueError, TypeError):
                    methods_info[name] = {
                        "signature": "N/A",
                        "is_async": False,
                        "type": "method",
                    }
            else:
                methods_info[name] = {"type": "attribute"}

        # Get constructor information
        constructor_sig = inspect.signature(SQLiteMemory.__init__)

        return {
            "class_name": "SQLiteMemory",
            "constructor": str(constructor_sig),
            "methods": methods_info,
            "module": "pyrit.memory",
        }

    except ImportError as e:
        print(f"Error importing SQLiteMemory: {e}")
        sys.exit(1)


def get_duckdb_api_reference() -> Dict[str, Any]:
    """Get reference API for DuckDBMemory from current codebase usage.

    Based on pyrit_memory_bridge.py usage patterns.
    """
    return {
        "class_name": "DuckDBMemory",
        "constructor": "(db_path: str)",
        "methods": {
            "add_seed_prompts_to_memory_async": {
                "signature": ("(prompts: List[SeedPrompt], added_by: str = None) -> None"),
                "is_async": True,
                "type": "method",
                "usage": "Store seed prompts to memory",
                "note": ("DuckDB version may not require added_by parameter"),
            },
            "get_prompt_request_pieces": {
                "signature": (
                    "(labels: List[str] = None, offset: int = 0, limit: int = None) -> List[PromptRequestPiece]"
                ),
                "is_async": False,
                "type": "method",
                "usage": "Retrieve prompt pieces with filtering",
            },
            "dispose_engine": {
                "signature": "() -> None",
                "is_async": False,
                "type": "method",
                "usage": "Close database connection",
            },
        },
        "module": "pyrit.memory",
    }


def compare_apis(duckdb_api: Dict[str, Any], sqlite_api: Dict[str, Any]) -> Dict[str, Any]:
    """Compare DuckDB and SQLite APIs for compatibility."""
    comparison = {
        "constructor_compatible": True,
        "method_compatibility": {},
        "breaking_changes": [],
        "new_methods": [],
        "deprecated_methods": [],
        "signature_changes": [],
    }

    # Check constructor compatibility
    if "db_path" not in sqlite_api["constructor"]:
        comparison["constructor_compatible"] = False
        comparison["breaking_changes"].append("Constructor: db_path parameter not found in SQLiteMemory")

    # Compare methods used in pyrit_memory_bridge.py
    for method_name, method_info in duckdb_api["methods"].items():
        if method_name in sqlite_api["methods"]:
            sqlite_method = sqlite_api["methods"][method_name]

            # Check if async status matches
            if method_info["is_async"] != sqlite_method.get("is_async", False):
                comparison["signature_changes"].append(
                    f"{method_name}: async status changed "
                    f"({method_info['is_async']} -> "
                    f"{sqlite_method.get('is_async', False)})"
                )

            comparison["method_compatibility"][method_name] = {
                "compatible": True,
                "duckdb_signature": method_info["signature"],
                "sqlite_signature": sqlite_method["signature"],
                "notes": "Method exists in both APIs",
            }
        else:
            comparison["method_compatibility"][method_name] = {
                "compatible": False,
                "duckdb_signature": method_info["signature"],
                "sqlite_signature": "N/A",
                "notes": "Method not found in SQLiteMemory",
            }
            comparison["deprecated_methods"].append(method_name)

    # Find new methods in SQLiteMemory
    duckdb_methods = set(duckdb_api["methods"].keys())
    sqlite_methods = set([k for k, v in sqlite_api["methods"].items() if v.get("type") == "method"])
    new_methods = sqlite_methods - duckdb_methods
    comparison["new_methods"] = list(new_methods)

    return comparison


def analyze_pyrit_memory_bridge_usage() -> Dict[str, Any]:
    """Analyze how pyrit_memory_bridge.py uses DuckDBMemory."""
    bridge_usage = {
        "critical_methods": [
            "add_seed_prompts_to_memory_async",
            "get_prompt_request_pieces",
            "dispose_engine",
        ],
        "usage_patterns": {
            "add_seed_prompts_to_memory_async": {
                "description": ("Store prompts in batches with metadata and labels"),
                "parameters_used": ["prompts"],
                "critical": True,
            },
            "get_prompt_request_pieces": {
                "description": "Retrieve prompts with label filtering",
                "parameters_used": ["labels", "offset", "limit"],
                "critical": True,
            },
            "dispose_engine": {
                "description": "Clean up database connections",
                "parameters_used": [],
                "critical": True,
            },
        },
        "migration_considerations": [
            "User-specific database paths must be supported",
            "Batch operations with metadata must work",
            "Label-based filtering is essential",
            "Pagination support required",
            "Connection cleanup must be reliable",
        ],
    }
    return bridge_usage


def generate_report(output_path: Optional[Path] = None) -> Dict[str, Any]:
    """Generate comprehensive API compatibility report."""
    print("Analyzing PyRIT API compatibility...")

    # Get API information
    sqlite_api = analyze_sqlite_memory_api()
    duckdb_api = get_duckdb_api_reference()
    bridge_usage = analyze_pyrit_memory_bridge_usage()

    # Compare APIs
    comparison = compare_apis(duckdb_api, sqlite_api)

    # Build report
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "pyrit_version": "0.10.0rc0",
        "analysis": {
            "sqlite_api": sqlite_api,
            "duckdb_api_reference": duckdb_api,
            "comparison": comparison,
            "bridge_usage": bridge_usage,
        },
        "summary": {
            "constructor_compatible": comparison["constructor_compatible"],
            "critical_methods_compatible": all(
                comparison["method_compatibility"].get(method, {}).get("compatible", False)
                for method in bridge_usage["critical_methods"]
            ),
            "breaking_changes_count": len(comparison["breaking_changes"]),
            "new_methods_count": len(comparison["new_methods"]),
            "deprecated_methods_count": len(comparison["deprecated_methods"]),
        },
        "recommendations": [],
    }

    # Generate recommendations
    if report["summary"]["critical_methods_compatible"]:
        report["recommendations"].append("✅ All critical methods are compatible - migration is feasible")
    else:
        report["recommendations"].append("⚠️ Some critical methods are not compatible - adapter pattern may be needed")

    if report["summary"]["breaking_changes_count"] == 0:
        report["recommendations"].append("✅ No breaking changes detected for current usage")
    else:
        report["recommendations"].append(
            f"⚠️ {report['summary']['breaking_changes_count']} " f"breaking changes need to be addressed"
        )

    if report["summary"]["new_methods_count"] > 0:
        report["recommendations"].append(
            f"ℹ️ {report['summary']['new_methods_count']} " f"new methods available for potential enhancements"
        )

    # Save report if path provided
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {output_path}")

    return report


def print_summary(report: Dict[str, Any]) -> None:
    """Print human-readable summary of the analysis."""
    print("\n" + "=" * 80)
    print("PyRIT API COMPATIBILITY ANALYSIS SUMMARY")
    print("=" * 80)

    print(f"\nTimestamp: {report['timestamp']}")
    print(f"PyRIT Version: {report['pyrit_version']}")

    print("\n--- Constructor Compatibility ---")
    if report["summary"]["constructor_compatible"]:
        print("✅ Constructor is compatible")
    else:
        print("❌ Constructor has compatibility issues")

    print("\n--- Critical Methods Compatibility ---")
    comparison = report["analysis"]["comparison"]
    for method in report["analysis"]["bridge_usage"]["critical_methods"]:
        compat = comparison["method_compatibility"].get(method, {})
        if compat.get("compatible", False):
            print(f"✅ {method}")
        else:
            print(f"❌ {method}")

    print("\n--- Breaking Changes ---")
    if comparison["breaking_changes"]:
        for change in comparison["breaking_changes"]:
            print(f"⚠️ {change}")
    else:
        print("✅ No breaking changes detected")

    print("\n--- New Methods (Sample) ---")
    new_methods = comparison["new_methods"][:5]
    for method in new_methods:
        print(f"ℹ️ {method}")
    if len(comparison["new_methods"]) > 5:
        print(f"... and {len(comparison['new_methods']) - 5} more")

    print("\n--- Recommendations ---")
    for rec in report["recommendations"]:
        print(rec)

    print("\n" + "=" * 80)


def main() -> None:
    """Execute PyRIT API compatibility analysis."""
    # Determine output path
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    output_path = repo_root / "reports" / "pyrit_api_compatibility_analysis.json"

    # Generate and print report
    report = generate_report(output_path)
    print_summary(report)

    # Exit with appropriate code
    if not report["summary"]["critical_methods_compatible"]:
        print("\n⚠️ Migration may require significant code changes")
        sys.exit(1)
    elif report["summary"]["breaking_changes_count"] > 0:
        print("\n⚠️ Migration is possible but requires careful testing")
        sys.exit(0)
    else:
        print("\n✅ Migration appears safe to proceed")
        sys.exit(0)


if __name__ == "__main__":
    main()
