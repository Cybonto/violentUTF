#!/usr/bin/env python3
"""
Test script to verify requirements-automation.txt dependencies.
"""


def test_optional_dependencies():
    """Test if optional dependencies are available."""
    print("Testing optional dependencies from requirements-automation.txt...")
    print("=" * 60)

    dependencies = [
        ("python-on-whales", "python_on_whales", "Docker container inspection"),
        ("python-nmap", "nmap", "Network scanning"),
        ("astroid", "astroid", "Enhanced AST analysis"),
        ("libcst", "libcst", "Concrete syntax tree"),
        ("parso", "parso", "Python parser"),
        ("rich", "rich", "Enhanced console output"),
        ("click", "click", "CLI framework"),
        ("tabulate", "tabulate", "Table formatting"),
        ("fuzzywuzzy", "fuzzywuzzy", "Fuzzy string matching"),
        ("send2trash", "send2trash", "Safe file operations"),
        ("PyYAML", "yaml", "YAML processing"),
        ("toml", "toml", "TOML processing"),
        ("sqlparse", "sqlparse", "SQL parsing"),
    ]

    available = []
    missing = []

    for pkg_name, import_name, description in dependencies:
        try:
            __import__(import_name)
            available.append((pkg_name, description))
            print(f"✅ {pkg_name:20} - {description}")
        except ImportError:
            missing.append((pkg_name, description))
            print(f"❌ {pkg_name:20} - {description}")

    print("=" * 60)
    print(f"Available: {len(available)}/{len(dependencies)}")
    print(f"Missing: {len(missing)}")

    if missing:
        print("\nTo install missing dependencies:")
        print("pip install -r requirements-automation.txt")
        print("\nOr install individually:")
        for pkg_name, description in missing:
            print(f"pip install {pkg_name}")

    return len(missing) == 0


if __name__ == "__main__":
    all_available = test_optional_dependencies()

    print("\n" + "=" * 60)
    if all_available:
        print("🎉 All optional dependencies are available!")
        print("Full discovery functionality is enabled.")
    else:
        print("⚠️  Some optional dependencies are missing.")
        print("Core functionality works, but some features may be limited.")

    print("\nTo test core functionality (works without optional deps):")
    print("python3 test_discovery_basic.py")

    print("\nTo test full functionality (requires optional deps):")
    print("python3 run_discovery.py run --exclude-network --timeout 30")
