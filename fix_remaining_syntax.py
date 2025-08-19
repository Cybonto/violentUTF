#!/usr/bin/env python3
"""Fix remaining syntax errors in files"""

import re

files_to_fix = [
    "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf/converters/converter_config.py",
    "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf/generators/generator_config.py",
    "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/app/core/security.py",
    "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/app/services/generator_integration_service.py",
]

for file_path in files_to_fix:
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()

        # Check line 388 in converter_config.py, 1133 in generator_config.py
        # Line 233 in security.py, line 69 in generator_integration_service.py
        for i, line in enumerate(lines):
            # Remove unexpected character after line continuation
            if "\\" in line and i < len(lines) - 1:
                # Check if there's a character after the backslash
                if line.rstrip().endswith("\\") and len(line.rstrip()) > 0:
                    # Check the next line
                    next_line = lines[i + 1] if i + 1 < len(lines) else ""
                    # If next line starts with odd characters, it might be malformed
                    if next_line.strip().startswith("\\") or next_line.strip().startswith("\\n"):
                        lines[i] = line.rstrip()[:-1] + "\n"  # Remove the backslash
                        lines[i + 1] = next_line.lstrip("\\").lstrip()

        with open(file_path, "w") as f:
            f.writelines(lines)
        print(f"Fixed {file_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

print("Completed fixing remaining syntax errors")
