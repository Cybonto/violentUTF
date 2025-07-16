#!/usr/bin/env python3
"""
Pre-commit check script to identify all potential CI failures before committing.
Run this before every commit to ensure your code will pass GitHub Actions checks.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


class PreCommitChecker:
    """Comprehensive pre-commit checker for ViolentUTF project."""

    def __init__(self, fix=False, verbose=False):
        self.fix = fix
        self.verbose = verbose
        self.issues = []
        self.fixed = []
        self.warnings = []

    def log(self, message, level="info"):
        """Log messages with color coding."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if level == "error":
            print(f"{RED}[{timestamp}] ✗ {message}{RESET}")
        elif level == "success":
            print(f"{GREEN}[{timestamp}] ✓ {message}{RESET}")
        elif level == "warning":
            print(f"{YELLOW}[{timestamp}] ⚠ {message}{RESET}")
        elif level == "info":
            print(f"{BLUE}[{timestamp}] ℹ {message}{RESET}")
        elif level == "header":
            print(f"\n{CYAN}{BOLD}{'='*70}{RESET}")
            print(f"{CYAN}{BOLD}{message}{RESET}")
            print(f"{CYAN}{BOLD}{'='*70}{RESET}")

    def run_command(self, cmd, description, check_only=True):
        """Run a command and capture output."""
        if self.verbose:
            self.log(f"Running: {cmd}", "info")

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                return True, result.stdout
            else:
                if check_only:
                    self.issues.append((description, result.stdout + result.stderr))
                return False, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            self.issues.append((description, "Command timed out"))
            return False, "Command timed out"
        except Exception as e:
            self.issues.append((description, str(e)))
            return False, str(e)

    def check_black(self):
        """Check Python code formatting with Black."""
        self.log("Checking Python formatting with Black...", "header")

        success, output = self.run_command("black --check --diff . 2>&1", "Black formatting")

        if not success and self.fix:
            self.log("Fixing Black formatting issues...", "warning")
            fix_success, _ = self.run_command("black .", "Black fix", check_only=False)
            if fix_success:
                self.fixed.append("Black formatting")
                return True
        return success

    def check_isort(self):
        """Check import sorting with isort."""
        self.log("Checking import sorting with isort...", "header")

        success, output = self.run_command("isort --check-only --diff . --profile black 2>&1", "Import sorting")

        if not success and self.fix:
            self.log("Fixing import sorting issues...", "warning")
            fix_success, _ = self.run_command("isort . --profile black", "isort fix", check_only=False)
            if fix_success:
                self.fixed.append("Import sorting")
                return True
        return success

    def check_flake8(self):
        """Check code quality with flake8."""
        self.log("Checking code quality with flake8...", "header")

        # Create a temporary flake8 config if .flake8 doesn't exist
        if not os.path.exists(".flake8"):
            with open(".flake8", "w") as f:
                f.write(
                    """[flake8]
max-line-length = 120
extend-ignore = E203, W503, E501, E226
exclude = .git,__pycache__,.venv,venv,build,dist,*.egg-info
"""
                )

        success, output = self.run_command("flake8 . --count --statistics", "Flake8 linting")

        if not success:
            # Parse flake8 output for common issues
            lines = output.split("\n")
            error_counts = {}
            for line in lines:
                if ":" in line and len(line.split(":")) >= 4:
                    parts = line.split(":")
                    if len(parts) >= 4 and parts[3].strip():
                        error_parts = parts[3].strip().split()
                        if error_parts:
                            error_code = error_parts[0]
                            error_counts[error_code] = error_counts.get(error_code, 0) + 1

            if error_counts:
                self.log("Common flake8 issues:", "warning")
                for code, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"  {code}: {count} occurrences")

        return success

    def check_file_paths(self):
        """Check for problematic file paths (spaces, special characters)."""
        self.log("Checking for problematic file paths...", "header")

        issues = []
        for root, dirs, files in os.walk("."):
            # Skip .git and other hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["venv", "__pycache__"]]

            for name in files + dirs:
                if " " in name:
                    issues.append(f"Space in filename: {os.path.join(root, name)}")
                if any(char in name for char in ["<", ">", ":", '"', "|", "?", "*"]):
                    issues.append(f"Windows-incompatible character: {os.path.join(root, name)}")

        if issues:
            self.issues.append(("File path issues", "\n".join(issues)))
            return False
        return True

    def check_large_files(self):
        """Check for large files that shouldn't be committed."""
        self.log("Checking for large files...", "header")

        MAX_SIZE_MB = 10
        large_files = []

        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["venv", "__pycache__"]]

            for file in files:
                filepath = os.path.join(root, file)
                try:
                    size_mb = os.path.getsize(filepath) / (1024 * 1024)
                    if size_mb > MAX_SIZE_MB:
                        large_files.append(f"{filepath}: {size_mb:.1f}MB")
                except (OSError, IOError):
                    pass  # Skip files that can't be accessed

        if large_files:
            self.warnings.append(("Large files", "\n".join(large_files)))

        return True

    def check_secrets(self):
        """Enhanced check for potential secrets in code."""
        self.log("Checking for potential secrets...", "header")
        
        import re

        # Pattern-based detection
        secret_patterns = [
            (r"password\s*=\s*['\"](?!<REDACTED>)[^'\"]+['\"]", "Hardcoded password"),
            (r"api_key\s*=\s*['\"](?!<REDACTED>)[^'\"]+['\"]", "Hardcoded API key"),
            (r"secret\s*=\s*['\"](?!<REDACTED>)[^'\"]+['\"]", "Hardcoded secret"),
            (r"token\s*=\s*['\"](?!<REDACTED>)[^'\"]+['\"]", "Hardcoded token"),
            (r"private_key\s*=\s*['\"](?!<REDACTED>)[^'\"]+['\"]", "Private key"),
            (r"CLIENT_SECRET\s*=\s*['\"](?!<REDACTED>)[^'\"]+['\"]", "Client secret"),
            (r"KEYCLOAK_.*_PASSWORD\s*=\s*['\"](?!<REDACTED>)[^'\"]+['\"]", "Keycloak password"),
        ]
        
        # High-entropy string patterns (likely secrets)
        entropy_patterns = [
            (r"['\"][a-zA-Z0-9]{32,}['\"]", "High-entropy string (possible secret)"),
            (r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", "Bearer token"),
            (r"[a-fA-F0-9]{40}", "SHA1 hash (possible token)"),
            (r"[a-fA-F0-9]{64}", "SHA256 hash (possible secret)"),
        ]
        
        # Load known secrets from baseline file
        known_secrets = []
        baseline_file = ".secrets-baseline"
        if os.path.exists(baseline_file):
            try:
                with open(baseline_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "|" in line:
                            secret, reason = line.split("|", 1)
                            if secret and not secret.startswith("<") and "placeholder" not in reason.lower():
                                known_secrets.append(secret)
            except Exception:
                pass
        
        # Add any additional hardcoded secrets to check
        known_secrets.extend([
            "TDfUNK2bpHzoTbncvGArrhbSG7dGcJ9q",
            "Dp28YSkBmwO4eOLFT1mLh4pZ930wLNKl",
        ])

        issues = []
        entropy_warnings = []
        
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ["venv", "__pycache__", "node_modules"]]

            for file in files:
                # Expanded file types including .md and .sh
                if (file.endswith((".py", ".yml", ".yaml", ".json", ".md", ".sh", ".bash", ".txt", ".toml", ".ini", ".cfg", ".conf")) 
                    and not file.endswith((".example", ".template"))
                    and not file.startswith("test_")):
                    
                    filepath = os.path.join(root, file)
                    
                    # Skip .env files entirely (they should be in .gitignore)
                    if ".env" in file:
                        issues.append(f"Environment file should not be committed: {filepath}")
                        continue
                    
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                            lines = content.split("\n")
                            
                            # Check for known exposed secrets
                            for secret in known_secrets:
                                if secret in content:
                                    for i, line in enumerate(lines):
                                        if secret in line:
                                            issues.append(f"KNOWN EXPOSED SECRET '{secret}' in {filepath}:{i+1}")
                            
                            # Check pattern-based secrets
                            for pattern, desc in secret_patterns:
                                matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                                for match in matches:
                                    # Find line number
                                    line_no = content[:match.start()].count('\n') + 1
                                    # Don't flag if it's in a comment or docstring
                                    line = lines[line_no - 1] if line_no <= len(lines) else ""
                                    if not line.strip().startswith(("#", "//", "*", "/*")):
                                        issues.append(f"{desc} in {filepath}:{line_no}")
                            
                            # Check high-entropy patterns (but be more lenient)
                            for pattern, desc in entropy_patterns:
                                matches = re.finditer(pattern, content)
                                for match in matches:
                                    value = match.group()
                                    line_no = content[:match.start()].count('\n') + 1
                                    line = lines[line_no - 1] if line_no <= len(lines) else ""
                                    
                                    # Skip if in comments, test files, or documentation examples
                                    if (not line.strip().startswith(("#", "//", "*", "/*")) and
                                        "example" not in filepath.lower() and
                                        "test" not in filepath.lower() and
                                        "/docs/" not in filepath and
                                        ".git/" not in filepath and
                                        "pip-audit-report" not in filepath and
                                        "package-lock.json" not in filepath and
                                        len(value) > 20):  # Only flag reasonably long strings
                                        
                                        # Skip common false positives
                                        if any(fp in value.lower() for fp in ["sha256", "sha1", "md5", "hash", "digest", "checksum"]):
                                            continue
                                            
                                        # Add to warnings, not issues
                                        entropy_warnings.append(f"{desc}: {value[:20]}... in {filepath}:{line_no}")
                                        
                    except (OSError, IOError, UnicodeDecodeError):
                        pass  # Skip files that can't be read

        # Report entropy warnings separately and limit them
        if entropy_warnings:
            self.warnings.append(("Possible secrets (high-entropy strings)", "\n".join(entropy_warnings[:20])))

        if issues:
            # This is now a blocking issue, not a warning
            self.issues.append(("Exposed secrets detected", "\n".join(issues)))
            return False
            
        return True

    def check_yaml_files(self):
        """Check YAML files for syntax errors."""
        self.log("Checking YAML files...", "header")

        yaml_files = []
        for root, dirs, files in os.walk("."):
            for file in files:
                if file.endswith((".yml", ".yaml")):
                    yaml_files.append(os.path.join(root, file))

        if yaml_files:
            try:
                import yaml

                for yaml_file in yaml_files:
                    try:
                        with open(yaml_file, "r") as f:
                            yaml.safe_load(f)
                    except yaml.YAMLError as e:
                        self.issues.append((f"YAML syntax error in {yaml_file}", str(e)))
                        return False
            except ImportError:
                self.warnings.append(("YAML check skipped", "Install PyYAML for YAML validation"))

        return True

    def check_json_files(self):
        """Check JSON files for syntax errors."""
        self.log("Checking JSON files...", "header")

        json_files = []
        for root, dirs, files in os.walk("."):
            for file in files:
                if file.endswith(".json"):
                    json_files.append(os.path.join(root, file))

        for json_file in json_files:
            try:
                with open(json_file, "r") as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                self.issues.append((f"JSON syntax error in {json_file}", str(e)))
                return False

        return True

    def check_dockerfile(self):
        """Check Dockerfile best practices."""
        self.log("Checking Dockerfiles...", "header")

        dockerfiles = []
        for root, dirs, files in os.walk("."):
            for file in files:
                if file == "Dockerfile" or file.endswith(".dockerfile"):
                    dockerfiles.append(os.path.join(root, file))

        for dockerfile in dockerfiles:
            try:
                with open(dockerfile, "r") as f:
                    content = f.read()
                    # Basic checks
                    if "COPY . ." in content and "dockerignore" not in os.listdir(os.path.dirname(dockerfile)):
                        self.warnings.append(
                            (
                                f"Dockerfile warning in {dockerfile}",
                                "COPY . . without .dockerignore file",
                            )
                        )
            except (OSError, IOError, UnicodeDecodeError):
                pass  # Skip files that can't be read

        return True

    def run_all_checks(self):
        """Run all pre-commit checks."""
        self.log("ViolentUTF Pre-Commit Checker", "header")
        self.log(f"Mode: {'FIX' if self.fix else 'CHECK ONLY'}", "info")

        checks = [
            ("Python Formatting", self.check_black),
            ("Import Sorting", self.check_isort),
            ("Code Quality", self.check_flake8),
            ("File Paths", self.check_file_paths),
            ("Large Files", self.check_large_files),
            ("Secrets Scan", self.check_secrets),
            ("YAML Syntax", self.check_yaml_files),
            ("JSON Syntax", self.check_json_files),
            ("Dockerfile", self.check_dockerfile),
        ]

        results = {}
        for name, check_func in checks:
            try:
                results[name] = check_func()
            except Exception as e:
                self.log(f"Error running {name}: {e}", "error")
                results[name] = False

        # Summary
        self.log("Summary", "header")

        # Show results
        all_passed = True
        for name, passed in results.items():
            if passed:
                self.log(f"{name}: PASSED", "success")
            else:
                self.log(f"{name}: FAILED", "error")
                all_passed = False

        # Show fixed items
        if self.fixed:
            self.log("\nFixed Issues:", "header")
            for item in self.fixed:
                self.log(f"Fixed: {item}", "success")

        # Show remaining issues
        if self.issues:
            self.log("\nRemaining Issues:", "header")
            for issue, details in self.issues:
                self.log(f"{issue}:", "error")
                if self.verbose:
                    print(f"  {details[:500]}...")

        # Show warnings
        if self.warnings:
            self.log("\nWarnings:", "header")
            for warning, details in self.warnings:
                self.log(f"{warning}:", "warning")
                if self.verbose:
                    print(f"  {details[:200]}...")

        # Final status
        if all_passed:
            self.log("\nAll checks passed! Safe to commit. 🎉", "success")
            return 0
        else:
            self.log("\nSome checks failed! Fix issues before committing.", "error")
            if not self.fix:
                self.log("Run with --fix to automatically fix formatting issues", "info")
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Pre-commit checker for ViolentUTF project")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix issues where possible",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )

    args = parser.parse_args()

    checker = PreCommitChecker(fix=args.fix, verbose=args.verbose)
    sys.exit(checker.run_all_checks())


if __name__ == "__main__":
    main()
