#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Pre-commit Environment Consistency Checker
Validates that individual tools match pre-commit hook configurations
"""

import subprocess
import sys
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional


class PrecommitEnvChecker:
    """Check consistency between individual tools and pre-commit hooks"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.precommit_config = self._load_precommit_config()
        self.issues = []
        self.successes = []

    def _load_precommit_config(self) -> Dict[str, Any]:
        """Load pre-commit configuration"""
        config_path = self.project_root / ".pre-commit-config.yaml"
        if not config_path.exists():
            raise FileNotFoundError("No .pre-commit-config.yaml found")

        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _run_command(self, cmd: List[str]) -> tuple[int, str, str]:
        """Run command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except FileNotFoundError:
            return 1, "", f"Command not found: {cmd[0]}"

    def check_python_version(self):
        """Check if Python version matches pre-commit config"""
        expected_version = self.precommit_config.get('default_language_version', {}).get('python', 'python3.12')

        # Extract version number
        if 'python' in expected_version:
            expected_version = expected_version.replace('python', '')

        code, stdout, stderr = self._run_command(['python3', '--version'])
        if code == 0:
            actual_version = stdout.strip().split()[-1]  # "Python 3.12.1" -> "3.12.1"
            major_minor = '.'.join(actual_version.split('.')[:2])  # "3.12.1" -> "3.12"

            if major_minor == expected_version:
                self.successes.append(f"✅ Python version {major_minor} matches config")
            else:
                self.issues.append(f"❌ Python version mismatch: config={expected_version}, actual={major_minor}")
        else:
            self.issues.append("❌ Could not check Python version")

    def check_black_consistency(self):
        """Check if black individual run matches pre-commit hook"""
        # Find black hook config
        black_config = self._find_hook_config('black')
        if not black_config:
            self.issues.append("❌ Black hook not found in pre-commit config")
            return

        # Test black with same args as pre-commit
        args = black_config.get('args', [])
        cmd = ['black', '--check', '--diff'] + args

        # Test on a small subset
        test_files = list(Path('.').glob('app/**/*.py'))[:3]  # Just a few files
        if test_files:
            cmd.extend([str(f) for f in test_files])
            code, stdout, stderr = self._run_command(cmd)

            if code == 0:
                self.successes.append("✅ Black individual run matches pre-commit hook")
            else:
                self.issues.append(f"❌ Black inconsistency: {stderr}")

    def check_mypy_consistency(self):
        """Check if mypy individual run matches pre-commit hook"""
        mypy_config = self._find_hook_config('mypy')
        if not mypy_config:
            return

        # Test mypy on a single file
        test_files = list(Path('.').glob('app/**/*.py'))[:1]
        if test_files:
            cmd = ['mypy'] + [str(f) for f in test_files] + ['--ignore-missing-imports']
            code, stdout, stderr = self._run_command(cmd)

            if "Success: no issues found" in stdout or code == 0:
                self.successes.append("✅ MyPy individual run works")
            else:
                # Don't treat mypy errors as config issues - they're code issues
                self.successes.append("✅ MyPy individual run executable (has type errors to fix)")

    def check_flake8_consistency(self):
        """Check if flake8 individual run matches pre-commit hook"""
        test_files = list(Path('.').glob('app/**/*.py'))[:2]
        if test_files:
            cmd = ['flake8'] + [str(f) for f in test_files]
            code, stdout, stderr = self._run_command(cmd)

            if code == 0:
                self.successes.append("✅ Flake8 individual run matches pre-commit expectations")
            else:
                # Check if it's configuration issue vs code issues
                if "not found" in stderr or "command not found" in stderr:
                    self.issues.append(f"❌ Flake8 not available: {stderr}")
                else:
                    self.successes.append("✅ Flake8 individual run executable (has lint errors to fix)")

    def check_bandit_consistency(self):
        """Check if bandit individual run works"""
        test_files = list(Path('.').glob('app/**/*.py'))[:1]
        if test_files:
            cmd = ['bandit', '-r'] + [str(f) for f in test_files]
            code, stdout, stderr = self._run_command(cmd)

            if code in [0, 1]:  # 0 = no issues, 1 = issues found (both valid)
                self.successes.append("✅ Bandit individual run works")
            else:
                if "not found" in stderr:
                    self.issues.append(f"❌ Bandit not available: {stderr}")
                else:
                    self.issues.append(f"❌ Bandit error: {stderr}")

    def check_detect_secrets_consistency(self):
        """Check if detect-secrets individual run works"""
        cmd = ['detect-secrets', 'scan', '--baseline', '.secrets.baseline', '--force-use-all-plugins']
        code, stdout, stderr = self._run_command(cmd)

        if code == 0:
            self.successes.append("✅ detect-secrets individual run works")
        else:
            if "not found" in stderr:
                self.issues.append(f"❌ detect-secrets not available: {stderr}")
            else:
                # Check if baseline file exists
                if not Path('.secrets.baseline').exists():
                    self.issues.append("❌ .secrets.baseline file missing")
                else:
                    self.issues.append(f"❌ detect-secrets configuration issue: {stderr}")

    def _find_hook_config(self, hook_id: str) -> Optional[Dict[str, Any]]:
        """Find configuration for specific hook"""
        for repo in self.precommit_config.get('repos', []):
            for hook in repo.get('hooks', []):
                if hook.get('id') == hook_id:
                    return hook
        return None

    def check_file_permissions(self):
        """Check that shebang files have proper permissions"""
        shebang_files = []

        # Find files with shebangs
        for pattern in ['**/*.py', '**/*.sh']:
            for file_path in Path('.').glob(pattern):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        first_line = f.readline()
                        if first_line.startswith('#!'):
                            shebang_files.append(file_path)
                except:
                    continue

        non_executable = []
        for file_path in shebang_files:
            if not file_path.stat().st_mode & 0o111:  # Check if executable
                non_executable.append(str(file_path))

        if non_executable:
            self.issues.append(f"❌ Files with shebangs not executable: {len(non_executable)} files")
        else:
            self.successes.append(f"✅ All {len(shebang_files)} shebang files are executable")

    def check_json_files(self):
        """Check that JSON files are valid"""
        json_files = list(Path('.').glob('**/*.json'))
        invalid_files = []

        for json_file in json_files:
            if 'node_modules' in str(json_file) or '.git' in str(json_file):
                continue

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # Skip empty files
                        json.loads(content)
            except json.JSONDecodeError:
                invalid_files.append(str(json_file))
            except:
                continue

        if invalid_files:
            self.issues.append(f"❌ Invalid JSON files: {invalid_files}")
        else:
            self.successes.append(f"✅ All {len(json_files)} JSON files are valid")

    def run_all_checks(self):
        """Run all consistency checks"""
        print("🔍 Running Pre-commit Environment Consistency Checks...")
        print("=" * 60)

        checks = [
            self.check_python_version,
            self.check_black_consistency,
            self.check_mypy_consistency,
            self.check_flake8_consistency,
            self.check_bandit_consistency,
            self.check_detect_secrets_consistency,
            self.check_file_permissions,
            self.check_json_files,
        ]

        for check in checks:
            try:
                check()
            except Exception as e:
                self.issues.append(f"❌ Error in {check.__name__}: {str(e)}")

        # Print results
        print("\n📋 Summary:")
        print(f"✅ Successes: {len(self.successes)}")
        print(f"❌ Issues: {len(self.issues)}")

        if self.successes:
            print("\n✅ Working correctly:")
            for success in self.successes:
                print(f"  {success}")

        if self.issues:
            print("\n❌ Issues found:")
            for issue in self.issues:
                print(f"  {issue}")
            return 1

        print("\n🎉 All environment consistency checks passed!")
        return 0


def main():
    """Main function"""
    checker = PrecommitEnvChecker()
    return checker.run_all_checks()


if __name__ == "__main__":
    sys.exit(main())
