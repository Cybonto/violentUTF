#!/usr/bin/env python3
# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Debug OpenAPI authentication configuration."""

import os
import sys

# Check environment variables
print("=== OpenAPI Environment Variables ===")
env_vars = os.environ
openapi_vars = {k: v for k, v in env_vars.items() if "OPENAPI" in k}

if not openapi_vars:
    print("No OPENAPI environment variables found!")
else:
    for key, value in sorted(openapi_vars.items()):
        if "TOKEN" in key or "KEY" in key or "SECRET" in key:
            # Mask sensitive values
            masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            print(f"{key}: {masked}")
        else:
            print(f"{key}: {value}")

print("\n=== Expected Variable Names ===")
provider_id = "gsai-api-1"
provider_key = provider_id.upper().replace("-", "_")
print(f"Provider ID: {provider_id}")
print(f"Provider Key: {provider_key}")
print(f"Expected AUTH_TOKEN var: OPENAPI_{provider_key}_AUTH_TOKEN")
print(f"Expected BASE_URL var: OPENAPI_{provider_key}_BASE_URL")

# Check numbered format
print("\n=== Checking Numbered Format ===")
for i in range(1, 5):
    id_var = f"OPENAPI_{i}_ID"
    if id_var in env_vars:
        print(f"{id_var}: {env_vars[id_var]}")
        if env_vars[id_var] == provider_id:
            print(f"  Found match! Looking for OPENAPI_{i}_AUTH_TOKEN")
            token_var = f"OPENAPI_{i}_AUTH_TOKEN"
            if token_var in env_vars:
                print(f"  {token_var}: Found")
            else:
                print(f"  {token_var}: NOT FOUND")
