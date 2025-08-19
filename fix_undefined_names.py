#!/usr/bin/env python3
"""Fix undefined names in various files"""

import re

# Fix dataset_monitoring.py - missing config parameter
file_path = "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/app/core/dataset_monitoring.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix __init__ to include config parameter
content = re.sub(
    r'def __init__\(self: "DatasetMonitor"\) -> None:',
    'def __init__(self: "DatasetMonitor", config: Optional[MonitoringConfig] = None) -> None:',
    content,
)

# Add import for MonitoringConfig
if "from typing import" in content and "Optional" not in content:
    content = re.sub(r"from typing import ([^)]+)", r"from typing import \1, Optional", content)

with open(file_path, "w") as f:
    f.write(content)
print(f"Fixed {file_path}")

# Fix dataset_recovery.py - missing config parameter
file_path = "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/app/core/dataset_recovery.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix __init__ to include config parameter
content = re.sub(
    r'def __init__\(self: "DatasetRecoveryManager", dataset_id: str, user_id: str\) -> None:',
    'def __init__(self: "DatasetRecoveryManager", dataset_id: str, user_id: str, config: Optional[RecoveryConfig] = None) -> None:',
    content,
)

with open(file_path, "w") as f:
    f.write(content)
print(f"Fixed {file_path}")

# Fix security_logging.py - missing logger_name parameter
file_path = "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/app/core/security_logging.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix __init__ to include logger_name parameter
content = re.sub(
    r'def __init__\(self: "SecurityLogger"\) -> None:',
    'def __init__(self: "SecurityLogger", logger_name: str = __name__) -> None:',
    content,
)

with open(file_path, "w") as f:
    f.write(content)
print(f"Fixed {file_path}")

# Fix validation.py - missing detail parameter
file_path = "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/app/core/validation.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix __init__ to include detail parameter
content = re.sub(
    r'def __init__\(self: "DatasetValidationException"\) -> None:',
    'def __init__(self: "DatasetValidationException", detail: str = "Validation failed") -> None:',
    content,
)

with open(file_path, "w") as f:
    f.write(content)
print(f"Fixed {file_path}")

# Fix introspection.py - missing app parameter
file_path = "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/app/mcp/tools/introspection.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix __init__ to include app parameter
content = re.sub(
    r'def __init__\(self: "IntrospectionTools"\) -> None:',
    'def __init__(self: "IntrospectionTools", app: Optional[Any] = None) -> None:',
    content,
)

# Add import for Any
if "from typing import" in content and "Any" not in content:
    content = re.sub(r"from typing import ([^)]+)", r"from typing import \1, Any", content)

with open(file_path, "w") as f:
    f.write(content)
print(f"Fixed {file_path}")

# Fix auth.py schemas - missing Any import
file_path = "/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app/app/schemas/auth.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix the Any import - remove quotes or add to imports
content = re.sub(r'"Any"', "Any", content)

# Ensure Any is imported
if "from typing import" in content and "Any" not in content:
    content = re.sub(r"from typing import ([^)]+)", r"from typing import \1, Any", content)

with open(file_path, "w") as f:
    f.write(content)
print(f"Fixed {file_path}")

print("Completed fixing undefined names")
