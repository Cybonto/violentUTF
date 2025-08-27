#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.

"""
Interactive script to choose pre-commit speed configuration
"""

import shutil
import subprocess
import sys
from pathlib import Path


def backup_current_hook() -> None:
    """Backup current pre-commit hook"""
    hook_path = Path(".git/hooks/pre-commit")
    if hook_path.exists():
        backup_path = Path(".git/hooks/pre-commit.backup")
        shutil.copy(hook_path, backup_path)
        print("💾 Backed up current pre-commit hook")


def install_config(config_name, config_file, estimated_time) -> bool:
    """Install specific pre-commit configuration"""
    try:
        # Install the configuration
        subprocess.run(["pre-commit", "install", "--config", config_file], check=True)
        print(f"✅ Installed {config_name}")
        print(f"   Config file: {config_file}")
        print(f"   Estimated time: {estimated_time}")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Failed to install {config_name}")
        return False


def show_menu() -> None:
    """Show speed configuration menu"""
    print("🚀 Pre-commit Speed Configuration")
    print("=" * 40)
    print()
    print("Choose your pre-commit speed:")
    print()
    print("1. 🐌 Full (Complete) - ~3-5 seconds")
    print("   ✅ All 25+ hooks including mypy, pylint, bandit")
    print("   🎯 Best for: Final validation before push")
    print()
    print("2. ⚡ Fast (Balanced) - ~0.7 seconds")
    print("   ✅ Essential hooks: syntax, formatting, basic security")
    print("   🎯 Best for: Regular development commits")
    print()
    print("3. 🏃 Ultra-Fast (Critical) - ~0.3 seconds")
    print("   ✅ Only critical: syntax errors, large files, secrets")
    print("   🎯 Best for: Frequent small commits")
    print()
    print("4. 📊 Benchmark all configurations")
    print()
    print("5. 🔄 Restore original configuration")
    print()


def benchmark_all() -> None:
    """Benchmark all available configurations"""
    configs = [
        ("Full", ".pre-commit-config.yaml", "Complete validation"),
        ("Fast", ".pre-commit-config-fast.yaml", "Balanced speed/quality"),
        ("Ultra-Fast", ".pre-commit-config-ultrafast.yaml", "Critical checks only"),
    ]

    print("🏁 Benchmarking all configurations...")
    print("=" * 40)

    for name, config_file, description in configs:
        if not Path(config_file).exists():
            print(f"⚠️  {config_file} not found, skipping...")
            continue

        print(f"\n📊 Testing {name} ({description})")
        try:
            import time

            start = time.time()
            result = subprocess.run(
                ["pre-commit", "run", "check-ast", "--config", config_file, "--all-files"],
                capture_output=True,
                timeout=30,
            )
            duration = time.time() - start

            status = "✅" if result.returncode == 0 else "⚠️"
            print(f"   {status} {name}: {duration:.2f}s")

        except subprocess.TimeoutExpired:
            print(f"   ⏱️  {name}: >30s (timeout)")
        except Exception as e:
            print(f"   ❌ {name}: Error - {e}")


def main() -> int:
    """Main interactive function"""
    while True:
        show_menu()

        try:
            choice = input("Enter your choice (1-5): ").strip()
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            return 0

        if choice == "1":
            backup_current_hook()
            if install_config("Full Configuration", ".pre-commit-config.yaml", "3-5 seconds"):
                print("\n💡 Use this for final validation before pushing to main branch")
            break

        elif choice == "2":
            if not Path(".pre-commit-config-fast.yaml").exists():
                print("❌ Fast config not found. Creating...")
                # The file should already exist from earlier in this conversation
            backup_current_hook()
            if install_config("Fast Configuration", ".pre-commit-config-fast.yaml", "~0.7 seconds"):
                print("\n💡 Perfect for regular GitHub Desktop commits")
            break

        elif choice == "3":
            if not Path(".pre-commit-config-ultrafast.yaml").exists():
                print("❌ Ultra-fast config not found. Creating...")
            backup_current_hook()
            if install_config("Ultra-Fast Configuration", ".pre-commit-config-ultrafast.yaml", "~0.3 seconds"):
                print("\n💡 Great for frequent small commits and rapid iteration")
            break

        elif choice == "4":
            benchmark_all()
            input("\nPress Enter to continue...")
            continue

        elif choice == "5":
            backup_path = Path(".git/hooks/pre-commit.backup")
            if backup_path.exists():
                shutil.copy(backup_path, Path(".git/hooks/pre-commit"))
                print("✅ Restored original pre-commit configuration")
            else:
                subprocess.run(["pre-commit", "install"], check=True)
                print("✅ Reinstalled default pre-commit configuration")
            break

        else:
            print("❌ Invalid choice. Please enter 1-5.")
            continue

    print("\n🎉 Pre-commit configuration updated!")
    print("\n🔄 To change later, run: python3 scripts/choose_precommit_speed.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
