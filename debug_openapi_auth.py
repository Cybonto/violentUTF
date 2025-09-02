#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Debug OpenAPI authentication configuration."""

import os

# Check environment variables
print("=== OpenAPI Environment Variables ===")
env_vars = os.environ
openapi_vars = {k: v for k, v in env_vars.items() if "OPENAPI" in k}

if not openapi_vars:
    # print("No OPENAPI environment variables found!")  # Debug print removed
    pass
else:
    for key, value in sorted(openapi_vars.items()):
        if "TOKEN" in key or "KEY" in key or "SECRET" in key:
            # Mask sensitive values
            masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            # print(f"{key}: {masked}")  # Debug print removed
        else:
            # print(f"{key}: {value}")  # Debug print removed
            pass

print("\n=== Expected Variable Names ===")
provider_id = "gsai-api-1"
provider_key = provider_id.upper().replace("-", "_")
# print(f"Provider ID: {provider_id}")  # Debug print removed
# print(f"Provider Key: {provider_key}")  # Debug print removed
# print(f"Expected AUTH_TOKEN var: OPENAPI_{provider_key}_AUTH_TOKEN")  # Debug print removed
# print(f"Expected BASE_URL var: OPENAPI_{provider_key}_BASE_URL")  # Debug print removed

# Check numbered format
print("\n=== Checking Numbered Format ===")
for i in range(1, 5):
    id_var = f"OPENAPI_{i}_ID"
    if id_var in env_vars:
        # print(f"{id_var}: {env_vars[id_var]}")  # Debug print removed
        if env_vars[id_var] == provider_id:
            # print(f"  Found match! Looking for OPENAPI_{i}_AUTH_TOKEN")  # Debug print removed
            token_var = f"OPENAPI_{i}_AUTH_TOKEN"
            if token_var in env_vars:
                # print(f"  {token_var}: Found")  # Debug print removed
                pass
            else:
                # print(f"  {token_var}: NOT FOUND")  # Debug print removed
                pass
