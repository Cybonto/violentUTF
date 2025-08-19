#!/usr/bin/env python3
"""Fix indentation issues in generator_config.py"""

import re

file_path = "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf/generators/generator_config.py"

with open(file_path, "r") as f:
    lines = f.readlines()

fixed_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    fixed_lines.append(line)

    # Check if this is a function definition
    if line.strip().startswith("def ") and ":" in line:
        # Check if next line is a docstring
        if i + 1 < len(lines) and lines[i + 1].strip().startswith('"""'):
            fixed_lines.append(lines[i + 1])  # Add the docstring
            i += 2

            # Now check the line after the docstring
            if i < len(lines):
                code_line = lines[i]
                # Check if the code line has incorrect indentation (not 8 spaces for methods)
                if code_line.strip() and not code_line.startswith("        "):
                    # Fix the indentation - add 8 spaces (2 levels of indentation for methods)
                    if line.startswith("    def "):  # This is a method
                        fixed_lines.append("        " + code_line.lstrip())
                    else:  # This is a top-level function
                        fixed_lines.append("    " + code_line.lstrip())
                else:
                    fixed_lines.append(code_line)
        else:
            i += 1
    else:
        i += 1

# Write the fixed content back
with open(file_path, "w") as f:
    f.writelines(fixed_lines)

print(f"Fixed indentation in {file_path}")
