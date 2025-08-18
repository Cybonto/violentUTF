#!/usr/bin/env python3
# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Verify PyRIT and Garak installation
This script checks that the AI red-teaming frameworks are properly installed
"""

import importlib
import sys


def verify_package(package_name, import_name=None):
    """Verify a package can be imported"""
    if import_name is None:
        import_name = package_name

    try:
        module = importlib.import_module(import_name)
        print(f"✅ {package_name} installed successfully")
        if hasattr(module, "__version__"):
            print(f"   Version: {module.__version__}")
        return True
    except ImportError as e:
        print(f"❌ {package_name} import failed: {e}")
        return False
    except Exception as e:
        print(f"⚠️  {package_name} import warning: {e}")
        return True  # Some packages may have import warnings but still work


def main():
    """Main verification function"""
    print("Verifying AI red-teaming frameworks installation...")
    print("-" * 50)

    all_good = True

    # Check PyRIT
    print("Checking PyRIT...")
    if not verify_package("PyRIT", "pyrit"):
        all_good = False

    # Check Garak
    print("\nChecking Garak...")
    if not verify_package("Garak", "garak"):
        all_good = False

    # Check MCP SDK
    print("\nChecking MCP SDK...")
    if not verify_package("MCP", "mcp"):
        all_good = False

    # Check SSE Starlette
    print("\nChecking SSE Starlette...")
    if not verify_package("SSE-Starlette", "sse_starlette"):
        all_good = False

    print("-" * 50)

    if all_good:
        print("✅ All required packages verified successfully!")
        sys.exit(0)
    else:
        print("❌ Some packages failed verification. Check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
