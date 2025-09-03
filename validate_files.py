#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Comprehensive validation script for code quality and implementation completeness."""

import ast
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, cast


class CodeValidator:
    """Advanced code validator for production readiness."""

    def __init__(self) -> None:
        """Initialize the validator with validation rules."""
        self.validation_rules = {
            "mock_implementations": self._check_mock_implementations,
            "empty_functions": self._check_empty_functions,
            "placeholder_comments": self._check_placeholder_comments,
            "unimplemented_methods": self._check_unimplemented_methods,
            "syntax_errors": self._check_syntax_errors,
            "import_issues": self._check_import_issues,
        }

    def _check_mock_implementations(self, content: str, lines: List[str]) -> List[str]:
        """Check for mock implementations that need real code."""
        issues = []

        # Check if this is a test file - test files are allowed to have mocks
        is_test_file = (
            "test_" in content.lower()
            or "import pytest" in content
            or "from unittest.mock import" in content
            or "import unittest" in content
            or "TestCase" in content
        )

        if is_test_file:
            # For test files, only check for problematic mock patterns
            problematic_patterns = [
                r"def\s+mock_\w+.*:\s*pass\s*$",  # Empty mock functions
                r"mock_\w+\s*=\s*None",  # Mock variables set to None
                r'mock_\w+\s*=\s*".*placeholder.*"',  # Placeholder mock values
            ]
        else:
            # For non-test files, check for any mock-like implementations
            problematic_patterns = [
                r"\bmock_\w+",  # mock_ variables
                r"def\s+mock_\w+",  # mock_ functions
                r"class\s+Mock\w+",  # Mock classes
                r"def\s+\w*stub\w*",  # stub functions
                r"def\s+\w*fake\w*",  # fake functions
            ]

        for i, line in enumerate(lines, 1):
            # Skip lines that are clearly legitimate unittest.mock usage
            if any(
                keyword in line
                for keyword in [
                    "unittest.mock",
                    "from unittest.mock",
                    "import Mock",
                    "@patch",
                    "@mock.patch",
                    "MagicMock",
                    "Mock()",
                    "patch(",
                ]
            ):
                continue

            for pattern in problematic_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Additional context check for test files
                    if is_test_file:
                        # Look for context that suggests this is a real implementation issue
                        context_lines = lines[max(0, i - 3) : i + 2]
                        context = " ".join(context_lines)
                        if any(
                            keyword in context.lower()
                            for keyword in [
                                "todo",
                                "fixme",
                                "placeholder",
                                "not implemented",
                            ]
                        ):
                            issues.append(f"Line {i}: Problematic mock implementation - {line.strip()}")
                    else:
                        issues.append(f"Line {i}: Mock implementation detected - {line.strip()}")

        return issues

    def _check_empty_functions(self, content: str, lines: List[str]) -> List[str]:
        """Check for functions with only pass statements."""
        issues = []

        try:
            tree = ast.parse(content)

            class FunctionVisitor(ast.NodeVisitor):
                def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                    # Check if function body only contains pass
                    if (
                        len(node.body) == 1
                        and isinstance(node.body[0], ast.Pass)
                        and not self._is_abstract_method(node)
                    ):
                        issues.append(f"Line {node.lineno}: Empty function '{node.name}' with only pass")

                    # Check for functions with just docstring and pass
                    elif (
                        len(node.body) == 2
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[1], ast.Pass)
                        and not self._is_abstract_method(node)
                    ):
                        issues.append(f"Line {node.lineno}: Function '{node.name}' only has docstring and pass")

                    self.generic_visit(node)

                def _is_abstract_method(self, node: ast.FunctionDef) -> bool:
                    """Check if this is an abstract method that should have pass."""
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
                            return True
                        elif isinstance(decorator, ast.Attribute) and decorator.attr == "abstractmethod":
                            return True
                    return False

            visitor = FunctionVisitor()
            visitor.visit(tree)

        except SyntaxError as e:
            issues.append(f"Syntax error prevented function analysis: {e}")

        return issues

    def _check_placeholder_comments(self, content: str, lines: List[str]) -> List[str]:
        """Check for placeholder comments that indicate incomplete code."""
        issues = []

        placeholder_patterns = [
            r"#\s*TODO(?!.*implemented)",  # TODO without "implemented"
            r"#\s*FIXME",
            r"#\s*XXX",
            r"#\s*HACK",
            r"#\s*PLACEHOLDER(?!\s*mock)",  # PLACEHOLDER but not when describing mock values
            r"#\s*NOT\s+IMPLEMENTED",
            r"raise\s+NotImplementedError",
        ]

        for i, line in enumerate(lines, 1):
            # Skip lines that are clearly documentation or legitimate usage
            if any(
                indicator in line
                for indicator in [
                    '"""',
                    "'''",
                    "docstring",
                    "Check for",
                    "methods that raise",
                ]
            ):
                continue

            for pattern in placeholder_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Additional context check for false positives
                    if "placeholder" in line.lower():
                        # Check if this is in a regex pattern or comment describing what to check
                        if any(
                            context in line.lower()
                            for context in [
                                "pattern",
                                "regex",
                                "check for",
                                "detect",
                                "# ",
                                "mock values",
                            ]
                        ):
                            continue

                    issues.append(f"Line {i}: Placeholder code detected - {line.strip()}")

        return issues

    def _check_unimplemented_methods(self, content: str, lines: List[str]) -> List[str]:
        """Check for methods that raise NotImplementedError."""
        issues = []

        try:
            tree = ast.parse(content)

            class NotImplementedVisitor(ast.NodeVisitor):
                def visit_Raise(self, node: ast.Raise) -> None:
                    if isinstance(node.exc, ast.Call):
                        if isinstance(node.exc.func, ast.Name):
                            if node.exc.func.id == "NotImplementedError":
                                issues.append(f"Line {node.lineno}: NotImplementedError found")
                    self.generic_visit(node)

            visitor = NotImplementedVisitor()
            visitor.visit(tree)

        except SyntaxError as e:
            issues.append(f"Syntax error prevented NotImplementedError analysis: {e}")

        return issues

    def _check_syntax_errors(self, content: str, lines: List[str]) -> List[str]:
        """Check for Python syntax errors."""
        issues = []

        try:
            ast.parse(content)
        except SyntaxError as e:
            issues.append(f"Line {e.lineno or 'unknown'}: Syntax error - {e.msg}")

        return issues

    def _check_import_issues(self, content: str, lines: List[str]) -> List[str]:
        """Check for import-related issues."""
        issues: List[str] = []

        # Check for unused imports (basic check)
        import_pattern = r"^\s*(?:from\s+\S+\s+)?import\s+(.+)$"
        imported_names = set()

        for _, line in enumerate(lines, 1):
            match = re.match(import_pattern, line)
            if match:
                imports = match.group(1)
                # Simple parsing - could be more sophisticated
                names = [name.strip().split(" as ")[0] for name in imports.split(",")]
                for name in names:
                    if name and not name.startswith("("):
                        imported_names.add(name.split(".")[0])

        # Check if imports are used in the code (basic heuristic check)
        for import_name in imported_names:
            if import_name not in ["*"] and import_name not in content:
                # Use basic text search as a heuristic - not perfect but catches obvious cases
                # Only report if import name is longer than 3 chars to reduce false positives
                if len(import_name) > 3 and import_name.isalpha():
                    # Check if it's a common import that might be used indirectly
                    common_imports = {
                        "typing",
                        "datetime",
                        "pathlib",
                        "argparse",
                        "json",
                        "logging",
                        "unittest",
                        "pytest",
                        "asyncio",
                        "subprocess",
                    }
                    if import_name.lower() not in common_imports:
                        issues.append(
                            f"Potentially unused import: {import_name} " f"(heuristic check - may have false positives)"
                        )

        return issues

    def validate_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate a single file and return comprehensive results."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            all_issues = []
            rule_results = {}

            for rule_name, rule_func in self.validation_rules.items():
                try:
                    rule_issues = rule_func(content, lines)
                    rule_results[rule_name] = {
                        "passed": len(rule_issues) == 0,
                        "issues": rule_issues,
                        "count": len(rule_issues),
                    }
                    all_issues.extend(rule_issues)
                except Exception as e:
                    rule_results[rule_name] = {
                        "passed": False,
                        "issues": [f"Rule execution failed: {e}"],
                        "count": 1,
                    }
                    all_issues.append(f"Rule '{rule_name}' failed: {e}")

            return {
                "file_path": str(file_path),
                "total_issues": len(all_issues),
                "all_issues": all_issues,
                "rule_results": rule_results,
                "passed": len(all_issues) == 0,
                "file_stats": {
                    "lines": len(lines),
                    "size_bytes": len(content),
                    "non_empty_lines": len([line for line in lines if line.strip()]),
                },
            }

        except Exception as e:
            return {
                "file_path": str(file_path),
                "total_issues": 1,
                "all_issues": [f"Error reading file: {e}"],
                "rule_results": {},
                "passed": False,
                "file_stats": {},
            }

    def validate_directory(self, directory: Path, pattern: str = "*.py") -> Dict[str, Any]:
        """Validate all Python files in a directory."""
        files_to_check = list(directory.rglob(pattern))
        results = []

        total_issues = 0
        total_files = len(files_to_check)
        passed_files = 0

        for file_path in files_to_check:
            result = self.validate_file(file_path)
            results.append(result)
            total_issues += result["total_issues"]
            if result["passed"]:
                passed_files += 1

        return {
            "directory": str(directory),
            "total_files": total_files,
            "passed_files": passed_files,
            "failed_files": total_files - passed_files,
            "total_issues": total_issues,
            "file_results": results,
            "summary": {
                "pass_rate": ((passed_files / total_files * 100) if total_files > 0 else 0),
                "avg_issues_per_file": ((total_issues / total_files) if total_files > 0 else 0),
            },
        }


def check_file(file_path: Path) -> List[str]:
    """Legacy function for backward compatibility."""
    validator = CodeValidator()
    result = validator.validate_file(file_path)
    return cast(List[str], result["all_issues"])


def generate_report(results: Dict[str, Any], output_file: Optional[Path] = None) -> str:
    """Generate a comprehensive validation report."""
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("CODE VALIDATION REPORT")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated: {__import__('datetime').datetime.now()}")
    report_lines.append("")

    if "directory" in results:
        # Directory validation report
        report_lines.append(f"Directory: {results['directory']}")
        report_lines.append(f"Total Files: {results['total_files']}")
        report_lines.append(f"Passed Files: {results['passed_files']}")
        report_lines.append(f"Failed Files: {results['failed_files']}")
        report_lines.append(f"Total Issues: {results['total_issues']}")
        report_lines.append(f"Pass Rate: {results['summary']['pass_rate']:.1f}%")
        report_lines.append("")

        for file_result in results["file_results"]:
            if not file_result["passed"]:
                report_lines.append(f"\nFAILED: {file_result['file_path']}")
                report_lines.append("-" * 40)
                for issue in file_result["all_issues"]:
                    report_lines.append(f"  • {issue}")
    else:
        # Single file validation report
        report_lines.append(f"File: {results['file_path']}")
        report_lines.append(f"Status: {'PASSED' if results['passed'] else 'FAILED'}")
        report_lines.append(f"Total Issues: {results['total_issues']}")
        report_lines.append("")

        if not results["passed"]:
            report_lines.append("Issues Found:")
            report_lines.append("-" * 20)
            for issue in results["all_issues"]:
                report_lines.append(f"  • {issue}")

    report_lines.append("\n" + "=" * 80)
    report_content = "\n".join(report_lines)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_content)

    return report_content


def main() -> None:
    """Run validation script on codebase."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate Python code for production readiness")
    parser.add_argument(
        "paths",
        nargs="*",
        default=[
            "tests/test_dataset_logging_comprehensive.py",
            "violentutf_api/fastapi_app/app/core/dataset_logging.py",
        ],
        help="Files or directories to validate",
    )
    parser.add_argument("--report", type=str, help="Generate detailed report to file")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument(
        "--directory",
        action="store_true",
        help="Treat paths as directories to scan recursively",
    )

    args = parser.parse_args()

    validator = CodeValidator()
    all_results = []
    total_issues = 0

    for path_str in args.paths:
        path = Path(path_str)

        if not path.exists():
            print(f"Path not found: {path_str}")
            continue

        if args.directory or path.is_dir():
            result = validator.validate_directory(path)
            all_results.append(result)
            total_issues += result["total_issues"]

            print(f"\nDirectory: {path}")
            print(
                f"Files: {result['total_files']}, "
                f"Passed: {result['passed_files']}, "
                f"Failed: {result['failed_files']}, "
                f"Issues: {result['total_issues']}"
            )

            if args.verbose:
                for file_result in result["file_results"]:
                    if not file_result["passed"]:
                        print(f"\n  FAILED: {file_result['file_path']}")
                        for issue in file_result["all_issues"]:
                            print(f"    - {issue}")
        else:
            result = validator.validate_file(path)
            all_results.append(result)
            total_issues += result["total_issues"]

            status = "PASSED" if result["passed"] else "FAILED"
            print(f"\n{status}: {path} ({result['total_issues']} issues)")

            if not result["passed"] or args.verbose:
                for issue in result["all_issues"]:
                    print(f"  - {issue}")

    # Generate report if requested
    if args.report:
        if len(all_results) == 1:
            generate_report(all_results[0], Path(args.report))
        else:
            # Combine results for multiple files/directories
            combined_result: Dict[str, Any] = {
                "total_issues": total_issues,
                "file_results": [],
            }
            for result in all_results:
                if "file_results" in result:
                    combined_result["file_results"].extend(result["file_results"])
                else:
                    combined_result["file_results"].append(result)

            generate_report(combined_result, Path(args.report))

        print(f"\nDetailed report saved to: {args.report}")

    # Exit with error code if issues found
    if total_issues > 0:
        print(f"\nValidation completed with {total_issues} issues found.")
        sys.exit(1)
    else:
        print("\nAll files passed validation!")
        sys.exit(0)


if __name__ == "__main__":
    main()
