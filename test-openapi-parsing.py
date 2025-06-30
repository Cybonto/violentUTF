#!/usr/bin/env python3
"""
Test script to diagnose OpenAPI spec parsing issues
This replicates the parsing logic from setup_macos.sh
"""

import json
import os
import ssl
import sys
import urllib.error
import urllib.request


def test_openapi_parsing(spec_url, provider_id="test"):
    """Test OpenAPI spec parsing with detailed error reporting"""

    print(f"🔍 Testing OpenAPI spec parsing")
    print(f"Spec URL: {spec_url}")
    print(f"Provider ID: {provider_id}")
    print("=" * 50)

    try:
        # Step 1: Fetch the spec
        print("📥 Fetching OpenAPI spec...")

        # Handle SSL certificate issues (Zscaler/corporate proxy)
        ssl_context = None
        try:
            # Try with default SSL context first
            with urllib.request.urlopen(spec_url, timeout=30) as response:
                spec_content = response.read().decode("utf-8")
            print(f"✅ Successfully fetched spec ({len(spec_content)} bytes)")
        except urllib.error.URLError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                print("⚠️  SSL certificate verification failed - trying with unverified SSL context")
                print("   This is common with Zscaler or corporate proxy environments")

                # Create unverified SSL context as fallback
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                with urllib.request.urlopen(spec_url, timeout=30, context=ssl_context) as response:
                    spec_content = response.read().decode("utf-8")
                print(f"✅ Successfully fetched spec with unverified SSL ({len(spec_content)} bytes)")
                print("💡 Consider running ./get-zscaler-certs.sh to properly handle SSL certificates")
            else:
                raise

        # Step 2: Parse JSON
        print("📝 Parsing JSON...")
        try:
            spec = json.loads(spec_content)
            print("✅ Valid JSON format")
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            return False

        # Step 3: Check OpenAPI version
        print("🔍 Checking OpenAPI version...")
        openapi_version = spec.get("openapi", spec.get("swagger", "unknown"))
        print(f"📋 OpenAPI version: {openapi_version}")

        # Step 4: Check basic structure
        print("🏗️  Checking spec structure...")

        info = spec.get("info", {})
        print(f"📋 Title: {info.get('title', 'No title')}")
        print(f"📋 Version: {info.get('version', 'No version')}")

        servers = spec.get("servers", [])
        print(f"📋 Servers: {len(servers)} found")
        for i, server in enumerate(servers):
            print(f"   Server {i+1}: {server.get('url', 'No URL')}")

        # Step 5: Check paths section (this is where parsing likely fails)
        print("🛣️  Checking paths section...")
        paths = spec.get("paths", {})
        print(f"📋 Paths found: {len(paths)}")

        if not paths:
            print("❌ No paths found in OpenAPI spec - this would cause parsing to fail")
            return False

        # Step 6: Parse endpoints (replicate the setup_macos.sh logic)
        print("🔧 Parsing endpoints...")
        endpoints = []

        for path, path_item in paths.items():
            print(f"   Processing path: {path}")

            if not isinstance(path_item, dict):
                print(f"      ⚠️  Path item is not a dict: {type(path_item)}")
                continue

            if "$ref" in path_item:
                print(f"      ⚠️  Path contains $ref - skipping")
                continue

            # Check each HTTP method
            methods_found = 0
            for method in ["get", "post", "put", "delete", "patch", "head", "options"]:
                if method in path_item:
                    methods_found += 1
                    operation = path_item[method]
                    operation_id = operation.get("operationId")

                    if not operation_id:
                        # Generate operation ID
                        operation_id = f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}"

                    endpoint = {
                        "path": path,
                        "method": method.upper(),
                        "operationId": operation_id,
                        "summary": operation.get("summary", ""),
                        "description": operation.get("description", ""),
                        "tags": operation.get("tags", []),
                    }

                    endpoints.append(endpoint)
                    print(f"      ✅ {method.upper()}: {operation_id}")

            if methods_found == 0:
                print(f"      ⚠️  No HTTP methods found in path")

        print(f"🎯 Total endpoints extracted: {len(endpoints)}")

        if len(endpoints) == 0:
            print("❌ No endpoints extracted - this explains the parsing failure")
            print("\n🔍 Possible reasons:")
            print("   1. All paths contain only $ref references")
            print("   2. No HTTP methods defined in path items")
            print("   3. Paths section is empty")
            print("   4. Invalid path structure")
            return False
        else:
            print("✅ Successfully parsed endpoints")
            print("\n📋 Sample endpoints:")
            for i, endpoint in enumerate(endpoints[:5]):  # Show first 5
                print(f"   {i+1}. {endpoint['method']} {endpoint['path']} ({endpoint['operationId']})")
            if len(endpoints) > 5:
                print(f"   ... and {len(endpoints) - 5} more")

        return True

    except urllib.error.URLError as e:
        print(f"❌ Network error fetching spec: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 test-openapi-parsing.py <spec_url> [provider_id]")
        print("Example: python3 test-openapi-parsing.py https://api.example.com/openapi.json")
        sys.exit(1)

    spec_url = sys.argv[1]
    provider_id = sys.argv[2] if len(sys.argv) > 2 else "test"

    success = test_openapi_parsing(spec_url, provider_id)
    sys.exit(0 if success else 1)
