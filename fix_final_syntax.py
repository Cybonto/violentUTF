#!/usr/bin/env python3
"""Fix final syntax errors with docstrings on same line as code"""

import re

# Fix converter_config.py line 387
file_path = "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf/converters/converter_config.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix the malformed docstring on line 387
content = re.sub(
    r'"""Create converter instance based on parameter requirements.""" if not init_param_names:',
    '"""Create converter instance based on parameter requirements."""\n    if not init_param_names:',
    content,
)

with open(file_path, "w") as f:
    f.write(content)
print(f"Fixed {file_path}")

# Fix generator_config.py line 1133
file_path = "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf/generators/generator_config.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix the malformed docstring
content = re.sub(
    r'"""Send test prompt to target instance.""" request = PromptRequestResponse\(',
    '"""Send test prompt to target instance."""\n    request = PromptRequestResponse(',
    content,
)

with open(file_path, "w") as f:
    f.write(content)
print(f"Fixed {file_path}")

# Fix security.py line 232
file_path = "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/app/core/security.py"
with open(file_path, "r") as f:
    lines = f.readlines()

# Find and fix line with backslash issues
for i, line in enumerate(lines):
    if i == 231:  # Line 232 in 1-indexed
        if "\\n\\n\\n" in line:
            lines[i] = line.replace("\\n\\n\\n", "\n\n\n")

with open(file_path, "w") as f:
    f.writelines(lines)
print(f"Fixed {file_path}")

# Fix generator_integration_service.py line 69
file_path = "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/app/services/generator_integration_service.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix multiple statements on one line with docstring
content = re.sub(
    r'"""Setup APISIX request URL with endpoint mapping.""" endpoint = _get_apisix_endpoint_for_model\(provider, model\)',
    '"""Setup APISIX request URL with endpoint mapping."""\n    endpoint = _get_apisix_endpoint_for_model(provider, model)',
    content,
)

# Also fix other lines that got concatenated
content = re.sub(
    r'raise ValueError\(f"No APISIX endpoint for {provider}/{model}"\)     base_url = os\.getenv\("VIOLENTUTF_API_URL", "http://apisix-apisix-1:9080"\) url = f"{base_url}{endpoint}" logger\.info\(f"APISIX request URL: {url}"\) return url',
    """raise ValueError(f"No APISIX endpoint for {provider}/{model}")
    base_url = os.getenv("VIOLENTUTF_API_URL", "http://apisix-apisix-1:9080")
    url = f"{base_url}{endpoint}"
    logger.info(f"APISIX request URL: {url}")
    return url""",
    content,
)

with open(file_path, "w") as f:
    f.write(content)
print(f"Fixed {file_path}")

print("Completed fixing final syntax errors")
