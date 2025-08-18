# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Fixture to create a TestClient with authentication headers.
"""

import json
import os
import sys

import pytest
from api.v1.endpoints.targets import router as targets_router
from core.security import get_current_user
from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "violentutf_api", "fastapi_app"))

from keycloak import KeycloakOpenID

# Add project root to sys.path
# Add violentutf_api/fastapi_app to path for imports


# Create a new FastAPI app for testing
app = FastAPI()

# Include the targets router
app.include_router(targets_router, prefix="/api/v1", dependencies=[Depends(get_current_user)])

client = TestClient(app)

# Load environment variables from .env file
load_dotenv()

# Keycloak Configuration (from environment variables)
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM")
CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID")
CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET")  # For confidential clients ONLY
USERNAME = os.environ.get("KEYCLOAK_USERNAME")
PASSWORD = os.environ.get("KEYCLOAK_PASSWORD")

# Validate Environment Variables
if not all([KEYCLOAK_URL, KEYCLOAK_REALM, CLIENT_ID, USERNAME, PASSWORD]):
    raise ValueError("Missing required environment variables. Check your .env file.")

# Initialize Keycloak Client
keycloak_openid = KeycloakOpenID(
    server_url=KEYCLOAK_URL,
    client_id=CLIENT_ID,
    realm_name=KEYCLOAK_REALM,
    client_secret_key=CLIENT_SECRET,  # Only needed for confidential clients
    verify=False,  # Set to True in production
)

# Get the access token from Keycloak
token_response = keycloak_openid.token(username=USERNAME, password=PASSWORD)
token = token_response.get("access_token")

# Define headers for authenticated requests
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}


@pytest.fixture(scope="function")
def test_client():
    with TestClient(app) as c:
        c.headers.update(headers)
        yield c


def test_get_targets(test_client):
    """
    Test the GET /api/v1/targets endpoint.
    """
    # Create a test target
    url = "/api/v1/targets"
    target_payload = {
        "name": "Test OpenAIChatTarget",
        "type": "PromptTarget",
        "provider": "OpenAIChatTarget",
        "description": "A test OpenAIChatTarget for unit testing",
        "parameters": {
            "api_key": os.environ.get("OPENAI_API_KEY", "sk-test"),
            "model": "gpt-3.5-turbo",
            "endpoint": "https://api.openai.com/v1",
        },
    }
    response = test_client.post(url, json=target_payload)
    assert response.status_code == 201, f"Expected status code 201, got {response.status_code}"
    json_data = response.json()
    target_id = json_data["id"]
    print("Created target:", json.dumps(json_data, indent=2))

    try:
        # Retrieve all targets
        response = test_client.get(url)
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        json_data = response.json()
        assert "targets" in json_data, "Response JSON should contain 'targets' key"
        print("GET /api/v1/targets response:", json.dumps(json_data, indent=2))

    finally:
        # Delete the target
        url = f"/api/v1/targets/{target_id}"
        response = test_client.delete(url)
        assert response.status_code == 204, f"Expected status code 204, got {response.status_code}"
        print(f"Deleted target {target_id}")


def test_get_target_by_id(test_client):
    """
    Test the GET /api/v1/targets/{target_id} endpoint.
    """
    # Create a test target
    url = "/api/v1/targets"
    target_payload = {
        "name": "Test OpenAIChatTarget",
        "type": "PromptTarget",
        "provider": "OpenAIChatTarget",
        "description": "A test OpenAIChatTarget for unit testing",
        "parameters": {
            "api_key": os.environ.get("OPENAI_API_KEY", "sk-test"),
            "model": "gpt-3.5-turbo",
            "endpoint": "https://api.openai.com/v1",
        },
    }
    response = test_client.post(url, json=target_payload)
    assert response.status_code == 201, f"Expected status code 201, got {response.status_code}"
    json_data = response.json()
    target_id = json_data["id"]
    print("Created target:", json.dumps(json_data, indent=2))

    try:
        # Retrieve the target by ID
        url = f"/api/v1/targets/{target_id}"
        response = test_client.get(url)
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        json_data = response.json()
        assert json_data["id"] == target_id, f"Expected target ID {target_id}, got {json_data['id']}"
        print(
            f"GET /api/v1/targets/{target_id} response:",
            json.dumps(json_data, indent=2),
        )
    finally:
        # Delete the target
        url = f"/api/v1/targets/{target_id}"
        response = test_client.delete(url)
        assert response.status_code == 204, f"Expected status code 204, got {response.status_code}"
        print(f"Deleted target {target_id}")


def create_openai_target(test_client):
    """
    Helper function to create an OpenAIChatTarget and return its ID.
    """
    url = "/api/v1/targets"
    target_payload = {
        "name": "Test OpenAIChatTarget",
        "type": "PromptTarget",
        "provider": "OpenAIChatTarget",
        "description": "A test OpenAIChatTarget for unit testing",
        "parameters": {
            "api_key": os.environ.get("OPENAI_API_KEY", "sk-test"),
            "model": "gpt-3.5-turbo",
            "endpoint": "https://api.openai.com/v1",
        },
    }
    response = test_client.post(url, json=target_payload)
    assert response.status_code == 201, f"Expected status code 201, got {response.status_code}"
    json_data = response.json()
    target_id = json_data["id"]
    return target_id


def test_update_target(test_client):
    """
    Test updating a target.
    """
    # First, create the target
    target_id = create_openai_target(test_client)

    # Prepare the data to update the target
    update_data = {
        "name": "Updated OpenAIChatTarget",
        "description": "Updated description",
    }

    try:
        response = test_client.put(f"/api/v1/targets/{target_id}", json=update_data)
        if response.status_code != 200:
            print("Error details:", response.json())
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        target = response.json()
        assert target["name"] == update_data["name"], "Updated target name mismatch"
        assert target["description"] == update_data["description"], "Updated target description mismatch"

    finally:
        # Delete the target
        url = f"/api/v1/targets/{target_id}"
        response = test_client.delete(url)
        assert response.status_code == 204, f"Expected status code 204, got {response.status_code}"
        print(f"Deleted target {target_id}")


def test_test_target(test_client):
    """
    Test the /api/v1/targets/{target_id}/test endpoint.
    """
    # First, create the target
    target_id = create_openai_target(test_client)

    # Prepare the test prompt
    test_prompt = "Hello, how are you?"
    test_request = {"test_prompt": test_prompt}

    try:
        response = test_client.post(f"/api/v1/targets/{target_id}/test", json=test_request)
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        test_response = response.json()
        assert test_response["success"], "The test should be successful"
        assert "response" in test_response, "Response should contain 'response' field"

        print(f"Test response: {test_response['response']}")
    finally:
        # Delete the target
        url = f"/api/v1/targets/{target_id}"
        response = test_client.delete(url)
        assert response.status_code == 204, f"Expected status code 204, got {response.status_code}"
        print(f"Deleted target {target_id}")


def test_delete_target(test_client):
    """
    Test deleting a target.
    """
    # Create a test target
    target_id = create_openai_target(test_client)
    print(f"Created target {target_id}")

    # Delete the target
    url = f"/api/v1/targets/{target_id}"
    response = test_client.delete(url)
    assert response.status_code == 204, f"Expected status code 204, got {response.status_code}"
    print(f"Deleted target {target_id}")

    # Verify deletion
    response = test_client.get(url)
    assert response.status_code == 404, "Deleted target should not be found"
    print(
        f"GET /api/v1/targets/{target_id} after deletion response:",
        response.status_code,
    )


def test_test_target_invalid_api_key(test_client):
    """
    Test testing a target with an invalid API key.
    """
    # Prepare target data with an invalid API key
    target_payload = {
        "name": "OpenAI Invalid Key Target",
        "type": "PromptTarget",
        "provider": "OpenAIChatTarget",
        "description": "Test target with invalid API key",
        "parameters": {
            "api_key": "invalid_api_key",  # Invalid API key
            "model": "gpt-3.5-turbo",
            "endpoint": "https://api.openai.com/v1",
        },
    }

    # Create the target
    url = "/api/v1/targets"
    response = test_client.post(url, json=target_payload)
    assert response.status_code == 201, f"Expected status code 201, got {response.status_code}"
    target = response.json()
    target_id = target["id"]

    # Prepare the test prompt
    test_request = {"test_prompt": "Hello, how are you?"}

    try:
        response = test_client.post(f"/api/v1/targets/{target_id}/test", json=test_request)
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        test_response = response.json()
        assert not test_response["success"], "The test should fail due to invalid API key"
        assert "error" in test_response, "Response should contain 'error' field"
        print(f"Test error: {test_response['error']}")
    finally:
        # Delete the target
        url = f"/api/v1/targets/{target_id}"
        response = test_client.delete(url)
        assert response.status_code == 204, f"Expected status code 204, got {response.status_code}"
        print(f"Deleted target {target_id}")


def test_test_target_special_characters(test_client):
    """
    Test testing a target with special characters in the prompt.
    """
    # Create the target
    target_id = create_openai_target(test_client)

    # Prepare a prompt with special characters
    test_prompt = "𝒯𝑒𝓈𝓉𝒾𝓃𝑔 special characters! ©®👍🏽🚀✨"

    test_request = {"test_prompt": test_prompt}

    try:
        response = test_client.post(f"/api/v1/targets/{target_id}/test", json=test_request)
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        test_response = response.json()
        assert test_response["success"], "The test should be successful with special characters"
        assert "response" in test_response, "Response should contain 'response' field"

        print(f"Test response: {test_response['response']}")
    finally:
        # Delete the target
        url = f"/api/v1/targets/{target_id}"
        response = test_client.delete(url)
        assert response.status_code == 204, f"Expected status code 204, got {response.status_code}"
        print(f"Deleted target {target_id}")
