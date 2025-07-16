#!/bin/bash
# Fix Keycloak client configuration for ViolentUTF

echo "🔧 Fixing Keycloak ViolentUTF Client Configuration"
echo "================================================"

# Source the keycloak setup functions
source setup_macos_files/keycloak_setup.sh

# Get admin token
echo "Getting Keycloak admin token..."
get_keycloak_admin_token

TARGET_REALM_NAME="ViolentUTF"

# Try to read client secret from secrets.toml if it exists
SECRETS_FILE="violentutf/.streamlit/secrets.toml"
if [ -f "$SECRETS_FILE" ]; then
    CLIENT_SECRET=$(grep -A1 '\[auth.keycloak\]' "$SECRETS_FILE" | grep 'client_secret' | cut -d'"' -f2)
    if [ -z "$CLIENT_SECRET" ]; then
        echo "Error: Could not extract client_secret from $SECRETS_FILE"
        exit 1
    fi
else
    echo "Error: $SECRETS_FILE not found. Please run setup first."
    exit 1
fi

# Create or update violentutf client
echo "Creating/updating violentutf client..."
CLIENT_CONFIG=$(cat <<EOF
{
    "clientId": "violentutf",
    "name": "ViolentUTF Application",
    "description": "ViolentUTF Streamlit Application",
    "rootUrl": "http://localhost:8501",
    "adminUrl": "http://localhost:8501",
    "baseUrl": "http://localhost:8501",
    "enabled": true,
    "clientAuthenticatorType": "client-secret",
    "secret": "$CLIENT_SECRET",
    "redirectUris": ["http://localhost:8501/oauth2callback", "http://localhost:8501/*"],
    "webOrigins": ["http://localhost:8501"],
    "publicClient": false,
    "protocol": "openid-connect",
    "attributes": {
        "post.logout.redirect.uris": "http://localhost:8501/"
    },
    "standardFlowEnabled": true,
    "implicitFlowEnabled": false,
    "directAccessGrantsEnabled": true,
    "serviceAccountsEnabled": false
}
EOF
)

# First, try to get existing client
make_api_call "GET" "/realms/${TARGET_REALM_NAME}/clients?clientId=violentutf"
if [ "$API_CALL_STATUS" -eq 200 ]; then
    KC_CLIENT_UUID=$(echo "$API_CALL_RESPONSE" | sed '$d' | jq -r '.[0].id')
    if [ -n "$KC_CLIENT_UUID" ] && [ "$KC_CLIENT_UUID" != "null" ]; then
        echo "Client exists with UUID: $KC_CLIENT_UUID"
        echo "Updating client configuration..."
        
        # Update the client
        echo "$CLIENT_CONFIG" > /tmp/client-update.json
        make_api_call "PUT" "/realms/${TARGET_REALM_NAME}/clients/${KC_CLIENT_UUID}" "/tmp/client-update.json"
        rm -f /tmp/client-update.json
        
        if [ "$API_CALL_STATUS" -eq 204 ]; then
            echo "✅ Client updated successfully"
        else
            echo "❌ Failed to update client. Status: $API_CALL_STATUS"
        fi
    else
        echo "Client not found, creating new one..."
        # Create new client
        echo "$CLIENT_CONFIG" > /tmp/client-create.json
        make_api_call "POST" "/realms/${TARGET_REALM_NAME}/clients" "/tmp/client-create.json"
        rm -f /tmp/client-create.json
        
        if [ "$API_CALL_STATUS" -eq 201 ]; then
            echo "✅ Client created successfully"
        else
            echo "❌ Failed to create client. Status: $API_CALL_STATUS"
            echo "Response: $API_CALL_RESPONSE"
        fi
    fi
else
    echo "Error checking for client. Status: $API_CALL_STATUS"
fi

echo ""
echo "✅ ViolentUTF client configuration complete!"
echo ""
echo "Client Details:"
echo "  Client ID: violentutf"
echo "  Client Secret: [REDACTED]"
echo "  Redirect URI: http://localhost:8501/oauth2callback"
echo ""
echo "Please restart Streamlit for changes to take effect."