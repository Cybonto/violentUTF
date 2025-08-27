#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Summary script to check scorer executions in the database
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import jwt
import requests
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / "violentutf" / ".env"
if env_path.exists():
    load_dotenv(env_path)

# API Configuration
API_BASE_URL = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
if API_BASE_URL.endswith("/api"):
    API_BASE_URL = API_BASE_URL[:-4]
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY"))

API_ENDPOINTS = {
    "orchestrators": f"{API_BASE_URL}/api/v1/orchestrators",
    "orchestrator_executions": f"{API_BASE_URL}/api/v1/orchestrators/{{orchestrator_id}}/executions",
    "execution_results": f"{API_BASE_URL}/api/v1/orchestrators/executions/{{execution_id}}/results",
}


def create_jwt_token():
    """Create a JWT token directly"""
    if not JWT_SECRET_KEY:
        return None

    now = datetime.utcnow()
    payload = {
        "sub": "violentutf.web",
        "username": "violentutf.web",
        "email": "violentutf@example.com",
        "exp": now + timedelta(hours=1),
        "iat": now,
        "roles": ["ai-api-access"],
        "token_type": "api_token",
        "preferred_username": "violentutf.web",
        "name": "ViolentUTF User",
    }

    try:
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")
    except Exception:
        return None


def get_auth_headers():
    """Get authentication headers for API requests"""
    token = create_jwt_token()
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "X-API-Gateway": "APISIX"}

    apisix_api_key = os.getenv("VIOLENTUTF_API_KEY") or os.getenv("APISIX_API_KEY") or os.getenv("AI_GATEWAY_API_KEY")
    if apisix_api_key:
        headers["apikey"] = apisix_api_key

    return headers


def make_api_request(url, headers):
    """Make API request with error handling"""
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def main():
    """Main function to summarize scorer executions"""
    print("🚀 ViolentUTF Scorer Execution Database Summary")
    print("=" * 60)

    if not JWT_SECRET_KEY:
        print("❌ JWT_SECRET_KEY not found in environment")
        return

    headers = get_auth_headers()
    if not headers:
        print("❌ Failed to create authentication headers")
        return

    # Get all orchestrators
    print("\n📋 Fetching orchestrators...")
    orchestrators = make_api_request(API_ENDPOINTS["orchestrators"], headers)
    if not orchestrators:
        print("❌ Failed to fetch orchestrators")
        return

    print(f"✅ Found {len(orchestrators)} orchestrators")

    # Analyze orchestrators and executions
    scorer_orchestrators = []
    total_executions = 0
    scorer_executions = 0
    execution_details = []

    print("\n🔍 Analyzing orchestrators and executions...")

    for orch in orchestrators:
        # Check if scorer-related
        is_scorer = False
        if "scorer" in orch.get("name", "").lower():
            is_scorer = True
        elif "scorer" in orch.get("orchestrator_type", "").lower():
            is_scorer = True

        if is_scorer:
            scorer_orchestrators.append(orch)

        # Get executions for this orchestrator
        if "orchestrator_id" in orch:
            url = API_ENDPOINTS["orchestrator_executions"].format(orchestrator_id=orch["orchestrator_id"])
            executions = make_api_request(url, headers)

            if executions:
                total_executions += len(executions)

                for exec in executions:
                    if exec.get("has_scorer_results"):
                        scorer_executions += 1
                        execution_details.append(
                            {
                                "orchestrator_name": orch["name"],
                                "orchestrator_type": orch["orchestrator_type"],
                                "execution_id": exec["id"],
                                "execution_name": exec.get("execution_name", "N/A"),
                                "status": exec.get("status", "N/A"),
                                "created_at": exec.get("started_at", "N/A"),
                            }
                        )

    # Print summary
    print("\n📊 Database Summary:")
    print(f"   Total Orchestrators: {len(orchestrators)}")
    print(f"   Scorer-Related Orchestrators: {len(scorer_orchestrators)}")
    print(f"   Total Executions: {total_executions}")
    print(f"   Executions with Scorer Results: {scorer_executions}")

    # Show orchestrator type breakdown
    orch_types = defaultdict(int)
    for orch in orchestrators:
        orch_types[orch["orchestrator_type"]] += 1

    print("\n📈 Orchestrators by Type:")
    for orch_type, count in sorted(orch_types.items(), key=lambda x: x[1], reverse=True):
        is_scorer = "scorer" in orch_type.lower()
        marker = " 🎯" if is_scorer else ""
        print(f"   {orch_type}: {count}{marker}")

    # Show scorer orchestrators
    if scorer_orchestrators:
        print(f"\n🎯 Scorer Orchestrators ({len(scorer_orchestrators)}):")
        for orch in scorer_orchestrators[:10]:  # Show first 10
            print(f"   - {orch['name']} ({orch['orchestrator_type']})")
            print(f"     ID: {orch['orchestrator_id']}")
            print(f"     Created: {orch.get('created_at', 'N/A')}")

    # Show executions with scorer results
    if execution_details:
        print(f"\n🎯 Executions with Scorer Results ({len(execution_details)}):")
        for i, exec_detail in enumerate(execution_details[:5], 1):  # Show first 5
            print(f"\n   {i}. {exec_detail['execution_name']}")
            print(f"      Orchestrator: {exec_detail['orchestrator_name']}")
            print(f"      Type: {exec_detail['orchestrator_type']}")
            print(f"      Status: {exec_detail['status']}")
            print(f"      Created: {exec_detail['created_at']}")
            print(f"      ID: {exec_detail['execution_id']}")

            # Try to get full results for the first execution
            if i == 1:
                print("\n      🔍 Fetching full results for this execution...")
                url = API_ENDPOINTS["execution_results"].format(execution_id=exec_detail["execution_id"])
                results = make_api_request(url, headers)
                if results and results.get("scores"):
                    print("      ✅ Scorer results found!")
                    scores = results["scores"]
                    if isinstance(scores, list):
                        print(f"      Number of scores: {len(scores)}")
                        # Show sample score structure
                        if scores:
                            print("      Sample score structure:")
                            sample = scores[0]
                            if isinstance(sample, dict):
                                for key in sample.keys():
                                    print(f"         - {key}")
    else:
        print("\n⚠️  No executions with scorer results found in the database")

    print("\n✅ Summary complete!")


if __name__ == "__main__":
    main()
