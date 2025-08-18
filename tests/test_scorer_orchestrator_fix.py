#!/usr/bin/env python3
# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Test script to verify scorer orchestrator creation fix"""

import json
from datetime import datetime

import requests

# Configuration
API_BASE_URL = "http://localhost:9080"  # APISIX Gateway

# Test JWT token (matches FastAPI secret)
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJlbWFpbCI6InRlc3RAdGVzdC5jb20iLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJ0ZXN0X3VzZXIiLCJleHAiOjk5OTk5OTk5OTl9.K6pX5GqMDZ8PQBoFJGwvIhbVHtQvh7kKoCHbZrjfQ_I"

headers = {"Authorization": f"Bearer {JWT_TOKEN}", "Content-Type": "application/json", "X-API-Gateway": "APISIX"}


def test_orchestrator_creation():
    """Test creating an orchestrator for scorer testing"""
    print("🧪 Testing Orchestrator Creation for Scorer Testing")
    print("=" * 60)

    # Create test orchestrator configuration (simulating scorer test)
    orchestrator_params = {
        "objective_target": {"type": "configured_generator", "generator_name": "TestGenerator"},
        "scorers": [
            {
                "type": "configured_scorer",
                "scorer_id": "test-scorer-id",
                "scorer_name": "TestScorer",
                "scorer_config": {
                    "id": "test-scorer-id",
                    "name": "TestScorer",
                    "type": "SubStringScorer",
                    "parameters": {"substring": "test"},
                },
            }
        ],
        "batch_size": 3,
        "user_context": "test_user",
        # NOTE: No metadata field here - this was causing the issue
    }

    orchestrator_payload = {
        "name": f"scorer_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "orchestrator_type": "PromptSendingOrchestrator",
        "description": "Testing scorer orchestrator creation",
        "parameters": orchestrator_params,
        "tags": ["scorer_test"],
        "save_results": False,
    }

    print("\n📝 Orchestrator payload:")
    print(json.dumps(orchestrator_payload, indent=2))

    # Make request
    response = requests.post(f"{API_BASE_URL}/api/v1/orchestrators", headers=headers, json=orchestrator_payload)

    print(f"\n📡 Response status: {response.status_code}")

    if response.status_code == 200:
        print("✅ Orchestrator created successfully!")
        result = response.json()
        print(f"   Orchestrator ID: {result.get('orchestrator_id')}")
        return True
    else:
        print("❌ Failed to create orchestrator")
        print(f"   Response: {response.text}")
        return False


if __name__ == "__main__":
    # Test orchestrator creation
    success = test_orchestrator_creation()

    if success:
        print("\n✅ Fix verified! Orchestrator creation should work in scorer testing.")
    else:
        print("\n❌ Issue still exists. Check the error message above.")
