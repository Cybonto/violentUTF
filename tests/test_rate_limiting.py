#!/usr/bin/env python3
# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Test script to verify rate limiting is working correctly.

SECURITY: Tests that authentication endpoints properly enforce rate limits
"""
import asyncio
import json
import time
from typing import Any, Dict, List

import aiohttp

# Test configuration
API_BASE_URL = "http://localhost:8000/api/v1"
TEST_ENDPOINTS = {
    "/auth/token": {
        "method": "POST",
        "data": {"username": "test", "password": "test"},
        "expected_limit": 5,  # 5 per minute
        "content_type": "application/x-www-form-urlencoded",
    },
    "/auth/token/info": {"method": "GET", "expected_limit": 30, "requires_auth": True},  # 30 per minute
}


async def test_rate_limiting() -> Any:
    """Test rate limiting on authentication endpoints."""
    print("🔒 Testing Rate Limiting Implementation")
    print("=" * 50)

    results = {}

    async with aiohttp.ClientSession() as session:
        for endpoint, config in TEST_ENDPOINTS.items():
            print(f"\n📍 Testing endpoint: {endpoint}")
            print(f"   Expected limit: {config['expected_limit']} requests/minute")

            url = f"{API_BASE_URL}{endpoint}"
            method = config["method"]

            # Prepare request data
            headers = {"Content-Type": "application/json"}
            data = None

            if config.get("content_type") == "application/x-www-form-urlencoded":
                headers["Content-Type"] = "application/x-www-form-urlencoded"
                if config.get("data"):
                    data = "&".join([f"{k}={v}" for k, v in config["data"].items()])
            elif config.get("data"):
                data = json.dumps(config["data"])

            # Test rapid requests to trigger rate limiting
            responses = []
            start_time = time.time()

            # Send requests rapidly (more than the limit)
            test_count = config["expected_limit"] + 5
            print(f"   Sending {test_count} rapid requests...")

            for i in range(test_count):
                try:
                    if method == "GET":
                        async with session.get(url, headers=headers) as response:
                            responses.append(
                                {"status": response.status, "request_num": i + 1, "time": time.time() - start_time}
                            )
                    elif method == "POST":
                        async with session.post(url, headers=headers, data=data) as response:
                            responses.append(
                                {"status": response.status, "request_num": i + 1, "time": time.time() - start_time}
                            )

                    # Small delay between requests to simulate realistic usage
                    await asyncio.sleep(0.1)

                except Exception as e:
                    responses.append(
                        {"status": "ERROR", "error": str(e), "request_num": i + 1, "time": time.time() - start_time}
                    )

            # Analyze results
            rate_limited = [r for r in responses if r["status"] == 429]
            successful = [r for r in responses if r["status"] in [200, 201, 401, 403]]
            errors = [r for r in responses if r["status"] not in [200, 201, 401, 403, 429]]

            print("   Results:")
            print(f"   ✅ Successful requests: {len(successful)}")
            print(f"   🛑 Rate limited (429): {len(rate_limited)}")
            print(f"   ❌ Other errors: {len(errors)}")

            # Check if rate limiting is working
            if len(rate_limited) > 0:
                print(f"   ✅ PASS: Rate limiting is working! Blocked {len(rate_limited)} requests")
                first_rate_limit = min([r["request_num"] for r in rate_limited])
                print(f"   📊 First rate limit hit at request #{first_rate_limit}")
            else:
                print("   ❌ FAIL: Rate limiting not working - no 429 responses")

            results[endpoint] = {
                "total_requests": len(responses),
                "successful": len(successful),
                "rate_limited": len(rate_limited),
                "errors": len(errors),
                "working": len(rate_limited) > 0,
            }

    # Summary
    print("\n" + "=" * 50)
    print("📊 RATE LIMITING TEST SUMMARY")
    print("=" * 50)

    total_tests = len(results)
    passing_tests = sum(1 for r in results.values() if r["working"])

    for endpoint, result in results.items():
        status = "✅ PASS" if result["working"] else "❌ FAIL"
        print(f"{status} {endpoint}: {result['rate_limited']}/{result['total_requests']} requests rate limited")

    print(f"\n🎯 Overall: {passing_tests}/{total_tests} endpoints properly rate limited")

    if passing_tests == total_tests:
        print("🛡️ SUCCESS: Rate limiting is properly implemented!")
        return True
    else:
        print("⚠️  WARNING: Some endpoints are missing rate limiting!")
        return False


if __name__ == "__main__":
    print("Starting rate limiting test...")
    print("Make sure the ViolentUTF API is running on localhost:8000")
    print()

    try:
        success = asyncio.run(test_rate_limiting())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        exit(1)
