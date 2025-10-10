# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Red Team Installation Verification Tool.

Verify that required red teaming packages are properly installed.

"""

import importlib
import sys
from typing import Optional


def verify_package(package_name: str, import_name: Optional[str] = None) -> bool:
    """Verify that a package is properly installed and importable.

    Args:
        package_name: Name of the package to verify
        import_name: Optional import name if different from package name

    Returns:
        bool: True if package is available and importable

    """
    import_name = import_name or package_name

    try:
        # Try to import the module
        module = importlib.import_module(import_name)

        # Check if module has version info
        if hasattr(module, "__version__"):
            pass  # Version info available

        return True

    except ImportError:
        # Package not available or not properly installed
        return False
    except Exception:
        # Other error during import
        return False


def main() -> None:
    """Run main verification function."""
    print("🔍 Verifying Red Team Package Installation...")

    # List of critical packages for FastAPI red teaming service
    packages_to_verify = [
        ("pyrit", "pyrit"),
        # ("garak", "garak"),  # Disabled for startup - can be installed manually if needed
        ("requests", "requests"),
        ("pydantic", "pydantic"),
        ("fastapi", "fastapi"),
        # Note: streamlit runs in separate container, not needed for FastAPI service
    ]

    all_good = True

    for package_name, import_name in packages_to_verify:
        if verify_package(package_name, import_name):
            print(f"   ✅ {package_name}: Available")
        else:
            print(f"   ❌ {package_name}: Not available or not properly installed")
            all_good = False

    if all_good:
        print("\n🎉 All red team packages are properly installed!")
        return
    else:
        print("\n⚠️ Some packages are missing or not properly installed.")
        print("Please install missing packages using:")
        print("   pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()
