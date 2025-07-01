#!/usr/bin/env python3
"""
APISIX Gateway Authentication Configuration Script
Configures HMAC-based authentication between APISIX and FastAPI
"""

import hashlib
import hmac
import json
import os
import sys
import time
from typing import Optional

import requests


class APISIXGatewayAuth:
    """Manage APISIX Gateway Authentication configuration"""

    def __init__(self, admin_url: str = "http://localhost:9180", admin_key: str = ""):
        self.admin_url = admin_url.rstrip("/")
        self.admin_key = admin_key
        self.headers = {"X-API-KEY": admin_key, "Content-Type": "application/json"}

    def generate_hmac_signature(
        self, gateway_secret: str, method: str, path: str, timestamp: Optional[str] = None
    ) -> tuple:
        """
        Generate HMAC signature for APISIX gateway authentication

        Args:
            gateway_secret: Shared secret between APISIX and FastAPI
            method: HTTP method (GET, POST, etc.)
            path: Request path
            timestamp: Unix timestamp (if None, current time is used)

        Returns:
            Tuple of (signature, timestamp)
        """
        if timestamp is None:
            timestamp = str(int(time.time()))

        # Create signature payload: METHOD:PATH:TIMESTAMP
        signature_payload = f"{method}:{path}:{timestamp}"

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            gateway_secret.encode("utf-8"), signature_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        return signature, timestamp

    def test_authentication(self, gateway_secret: str, fastapi_url: str = "http://localhost:8000") -> bool:
        """
        Test HMAC authentication with FastAPI

        Args:
            gateway_secret: Shared secret
            fastapi_url: FastAPI base URL

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Test endpoint
            method = "GET"
            path = "/health"

            # Generate signature
            signature, timestamp = self.generate_hmac_signature(gateway_secret, method, path)

            # Test headers
            test_headers = {
                "X-API-Gateway": "APISIX",
                "X-APISIX-Signature": signature,
                "X-APISIX-Timestamp": timestamp,
            }

            # Make test request
            response = requests.get(f"{fastapi_url}{path}", headers=test_headers, timeout=10)

            if response.status_code == 200:
                print("✅ Gateway authentication test successful")
                return True
            else:
                print(f"❌ Gateway authentication test failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Gateway authentication test error: {str(e)}")
            return False

    def configure_plugin_config(self, gateway_secret: str) -> bool:
        """
        Configure APISIX plugin for gateway authentication

        Args:
            gateway_secret: Shared secret for HMAC

        Returns:
            True if configuration successful, False otherwise
        """
        try:
            # Plugin configuration for global use
            plugin_config = {
                "id": "gateway-auth-global",
                "plugins": {
                    "serverless - pre - function": {
                        "phase": "rewrite",
                        "functions": [
                            """
                            return function(conf, ctx)
                                local ngx = ngx
                                local ngx_time = ngx.time
                                local resty_hmac = require("resty.hmac")

                                -- Get current timestamp
                                local timestamp = tostring(ngx_time())

                                -- Get request details
                                local method = ngx.var.request_method
                                local path = ngx.var.uri

                                -- Create signature payload
                                local signature_payload = method .. ":" .. path .. ":" .. timestamp

                                -- Generate HMAC signature
                                local hmac_sha256 = resty_hmac:new("{gateway_secret}", resty_hmac.ALGOS.SHA256)
                                hmac_sha256:update(signature_payload)
                                local signature = hmac_sha256:final()

                                -- Convert to hex
                                local signature_hex = ""
                                for i = 1, #signature do
                                    signature_hex = signature_hex .. string.format("%02x", signature:byte(i))
                                end

                                -- Add headers
                                ngx.req.set_header("X-API-Gateway", "APISIX")
                                ngx.req.set_header("X-APISIX-Signature", signature_hex)
                                ngx.req.set_header("X-APISIX-Timestamp", timestamp)
                            end
                            """
                        ],
                    }
                },
            }

            # Apply to plugin configs
            response = requests.put(
                f"{self.admin_url}/apisix/admin/plugin_configs/gateway-auth-global",
                headers=self.headers,
                json=plugin_config,
                timeout=10,
            )

            if response.status_code in [200, 201]:
                print("✅ APISIX gateway authentication plugin configured")
                return True
            else:
                print(f"❌ Failed to configure APISIX plugin: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error configuring APISIX plugin: {str(e)}")
            return False


def main():
    """Main configuration function"""
    print("🔐 APISIX Gateway Authentication Configuration")
    print("=" * 50)

    # Get configuration from environment
    admin_url = os.getenv("APISIX_ADMIN_URL", "http://localhost:9180")
    admin_key = os.getenv("APISIX_ADMIN_KEY", "")
    gateway_secret = os.getenv("APISIX_GATEWAY_SECRET", "")
    fastapi_url = os.getenv("FASTAPI_URL", "http://localhost:8000")

    if not admin_key:
        print("❌ APISIX_ADMIN_KEY environment variable not set")
        sys.exit(1)

    if not gateway_secret:
        print("❌ APISIX_GATEWAY_SECRET environment variable not set")
        print("💡 Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'")
        sys.exit(1)

    # Initialize configurator
    auth = APISIXGatewayAuth(admin_url, admin_key)

    # Test signature generation
    print("🧪 Testing HMAC signature generation...")
    signature, timestamp = auth.generate_hmac_signature(gateway_secret, "GET", "/health")
    print(f"✅ Generated signature: {signature[:16]}...")
    print(f"✅ Timestamp: {timestamp}")

    # Configure APISIX plugin
    print("\n⚙️  Configuring APISIX plugin...")
    if auth.configure_plugin_config(gateway_secret):
        print("✅ APISIX plugin configuration complete")
    else:
        print("❌ APISIX plugin configuration failed")
        sys.exit(1)

    # Test authentication
    print("\n🧪 Testing gateway authentication...")
    if auth.test_authentication(gateway_secret, fastapi_url):
        print("✅ Gateway authentication working correctly")
    else:
        print("⚠️  Gateway authentication test failed (FastAPI may not be running)")

    print("\n✅ APISIX Gateway Authentication setup complete!")
    print("\n📋 Next steps:")
    print("1. Restart APISIX to load the new plugin configuration")
    print("2. Update all APISIX routes to use the gateway authentication")
    print("3. Test API endpoints through APISIX gateway")
    print("4. Monitor logs for authentication events")


if __name__ == "__main__":
    main()
