#!/usr/bin/env python3
"""Generate performance report from benchmark results."""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    """Generate performance report from benchmark data."""
    parser = argparse.ArgumentParser(description="Generate performance report")
    parser.add_argument("--benchmark-file", help="Benchmark JSON file")
    parser.add_argument("--memory-file", help="Memory profile file")
    parser.add_argument("--output", help="Output report file", default="performance_report.md")
    args = parser.parse_args()

    report_content = ["# Performance Report", ""]
    report_content.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_content.append("")

    # Process benchmark results if available
    if args.benchmark_file and Path(args.benchmark_file).exists():
        try:
            with open(args.benchmark_file, "r") as f:
                benchmark_data = json.load(f)
            report_content.append("## Benchmark Results")
            report_content.append("")
            report_content.append(f"Benchmark data loaded: {len(benchmark_data)} entries")
            report_content.append("")
        except Exception as e:
            report_content.append(f"Error loading benchmark data: {e}")
            report_content.append("")

    # Process memory profile if available
    if args.memory_file and Path(args.memory_file).exists():
        report_content.append("## Memory Profile")
        report_content.append("")
        try:
            with open(args.memory_file, "r") as f:
                memory_data = f.read()
            report_content.append(f"Memory profiling data loaded: {len(memory_data)} bytes")
            report_content.append("")
        except Exception as e:
            report_content.append(f"Error loading memory data: {e}")
            report_content.append("")

    # If no data available, add placeholder
    if not (args.benchmark_file or args.memory_file):
        report_content.append("No performance data available yet.")
        report_content.append("")
        report_content.append("This report will be populated when benchmark and memory profiling data is available.")

    # Write report
    with open(args.output, "w") as f:
        f.write("\n".join(report_content))

    print(f"Performance report written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
