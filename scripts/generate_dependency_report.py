#!/usr/bin/env python3
"""Generate dependency report from outdated package info."""
import argparse
import glob
import json
import sys
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Generate dependency report")
    parser.add_argument("--outdated-files", help="Pattern for outdated JSON files")
    parser.add_argument("--safety-file", help="Safety report JSON file")
    parser.add_argument("--output", help="Output report file", default="dependency-report.md")
    args = parser.parse_args()

    report_content = ["# Dependency Report", ""]
    report_content.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_content.append("")

    # Process outdated dependencies
    if args.outdated_files:
        outdated_count = 0
        report_content.append("## Outdated Dependencies")
        report_content.append("")

        for pattern in args.outdated_files.split():
            for file_path in glob.glob(pattern):
                try:
                    with open(file_path, "r") as f:
                        outdated_data = json.load(f)
                    outdated_count += len(outdated_data)
                    report_content.append(f"- Found {len(outdated_data)} outdated packages in {file_path}")
                except Exception as e:
                    report_content.append(f"- Error processing {file_path}: {e}")

        if outdated_count == 0:
            report_content.append("All dependencies are up to date!")
        report_content.append("")

    # Process safety vulnerabilities
    if args.safety_file and Path(args.safety_file).exists():
        report_content.append("## Security Vulnerabilities")
        report_content.append("")
        try:
            with open(args.safety_file, "r") as f:
                safety_data = json.load(f)

            if isinstance(safety_data, list) and len(safety_data) > 0:
                report_content.append(f"Found {len(safety_data)} security vulnerabilities:")
                for vuln in safety_data[:5]:  # Show first 5
                    report_content.append(
                        f"- {vuln.get('package', 'Unknown')}: {vuln.get('vulnerability', 'Unknown issue')}"
                    )
                if len(safety_data) > 5:
                    report_content.append(f"- ... and {len(safety_data) - 5} more")
            else:
                report_content.append("No security vulnerabilities found!")
        except Exception as e:
            report_content.append(f"Error processing safety report: {e}")
        report_content.append("")

    # Add recommendations
    report_content.append("## Recommendations")
    report_content.append("")
    report_content.append("1. Review and update outdated dependencies regularly")
    report_content.append("2. Address security vulnerabilities immediately")
    report_content.append("3. Consider using pip-compile for reproducible builds")
    report_content.append("4. Enable Dependabot for automated updates")

    # Write report
    with open(args.output, "w") as f:
        f.write("\n".join(report_content))

    print(f"Dependency report written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
