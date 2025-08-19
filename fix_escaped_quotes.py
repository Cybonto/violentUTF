#!/usr/bin/env python3
"""Fix escaped quotes in files"""

import re

files_to_fix = [
    "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf/converters/converter_config.py",
    "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf/generators/generator_config.py",
    "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/app/core/security.py",
    "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/app/services/generator_integration_service.py",
]

for file_path in files_to_fix:
    with open(file_path, "r") as f:
        content = f.read()

    # Replace escaped quotes in docstrings
    content = re.sub(r'\\"""', '"""', content)
    content = re.sub(r'\\"', '"', content)

    # Fix lines where docstring and code are on the same line
    # Pattern: """docstring text""" followed by code on same line
    content = re.sub(r'"""([^"]+)"""\s+([a-zA-Z_])', r'"""\1"""\n    \2', content)

    # Fix escaped newline characters in strings
    content = re.sub(r"\\n", "\n", content)

    with open(file_path, "w") as f:
        f.write(content)
    print(f"Fixed {file_path}")

print("Completed fixing escaped quotes")
