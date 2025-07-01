#!/usr/bin/env python3
"""
Test the complete authentication flow to verify the fix
"""
import os
import sys

sys.path.append("violentutf")


# Set up a mock Streamlit session state
class MockSessionState:
    def __init__(self):
        self._state = {}

    def get(self, key, default=None):
        return self._state.get(key, default)

    def __setitem__(self, key, value):
        self._state[key] = value

    def __getitem__(self, key):
        return self._state[key]

    def __contains__(self, key):
        return key in self._state

    def pop(self, key, default=None):
        return self._state.pop(key, default)

    def keys(self):
        return self._state.keys()


# Mock streamlit.session_state
import streamlit as st

st.session_state = MockSessionState()


# Mock streamlit functions to prevent errors
def mock_error(*args, **kwargs):
    print(f"STREAMLIT ERROR: {args}")


def mock_warning(*args, **kwargs):
    print(f"STREAMLIT WARNING: {args}")


def mock_info(*args, **kwargs):
    print(f"STREAMLIT INFO: {args}")


st.error = mock_error
st.warning = mock_warning
st.info = mock_info

print("=== AUTHENTICATION FLOW TEST ===")

# 1. Test JWT Manager initialization
try:
    from violentutf.utils.jwt_manager import JWTManager

    jwt_manager = JWTManager()
    print("✅ JWT Manager initialized successfully")
    print(f"   JWT Secret available: {bool(jwt_manager._get_jwt_secret())}")
except Exception as e:
    print(f"❌ JWT Manager initialization failed: {e}")
    sys.exit(1)

# 2. Test token creation with environment credentials
try:
    keycloak_data = {
        "preferred_username": os.getenv("KEYCLOAK_USERNAME", "violentutf.web"),
        "email": "test@violentutf.local",
        "name": "Test User",
        "sub": os.getenv("KEYCLOAK_USERNAME", "violentutf.web"),
        "roles": ["ai-api-access"],
    }

    token = jwt_manager.create_token(keycloak_data)
    print(f"✅ Token creation successful: {bool(token)}")
    if token:
        print(f"   Token stored in session: {'api_token' in st.session_state}")
except Exception as e:
    print(f"❌ Token creation failed: {e}")
    sys.exit(1)

# 3. Test authentication utils with the new validation
try:
    from violentutf.utils.auth_utils_keycloak import _clear_invalid_jwt_tokens

    # Store the token in session state
    st.session_state["api_token"] = token

    print("✅ Token stored in session state")
    print(f"   Token before validation: {bool(st.session_state.get('api_token'))}")

    # This should NOT clear the token anymore with our fix
    _clear_invalid_jwt_tokens()

    print(f"   Token after validation: {bool(st.session_state.get('api_token'))}")

    if st.session_state.get("api_token"):
        print("✅ Token validation fix successful - token was NOT cleared")
    else:
        print("❌ Token was incorrectly cleared - fix failed")

except Exception as e:
    print(f"❌ Authentication utils test failed: {e}")

# 4. Test API request flow
try:
    import requests

    current_token = st.session_state.get("api_token")
    if current_token:
        headers = {
            "Authorization": f"Bearer {current_token}",
            "Content-Type": "application/json",
            "X-API-Gateway": "APISIX",
        }

        response = requests.get("http://localhost:9080/api/v1/auth/token/info", headers=headers, timeout=5)
        print(f"✅ API request successful: {response.status_code == 200}")
        if response.status_code == 200:
            data = response.json()
            print(f"   API returned username: {data.get('username')}")
        else:
            print(f"   API error: {response.status_code} - {response.text[:100]}")
    else:
        print("❌ No token available for API test")

except Exception as e:
    print(f"❌ API request test failed: {e}")

print("\n=== TEST COMPLETE ===")

# Summary
token_created = bool(jwt_manager.create_token(keycloak_data))
token_persisted = bool(st.session_state.get("api_token"))
api_accessible = False

try:
    if st.session_state.get("api_token"):
        headers = {"Authorization": f'Bearer {st.session_state["api_token"]}', "X-API-Gateway": "APISIX"}
        response = requests.get("http://localhost:9080/api/v1/auth/token/info", headers=headers, timeout=5)
        api_accessible = response.status_code == 200
except:
    pass

print("\nSUMMARY:")
print(f"✅ Token Creation:    {token_created}")
print(f"✅ Token Persistence: {token_persisted}")
print(f"✅ API Access:       {api_accessible}")

if token_created and token_persisted and api_accessible:
    print("\n🎉 AUTHENTICATION FLOW WORKING CORRECTLY!")
    print("   The JWT signature validation fix resolved the issue.")
else:
    print("\n❌ AUTHENTICATION FLOW STILL HAS ISSUES")
    print("   Further investigation needed.")
