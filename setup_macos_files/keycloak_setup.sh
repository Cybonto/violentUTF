#!/usr/bin/env bash
# keycloak_setup.sh - Keycloak setup and configuration functions

# Function to get Keycloak admin token
get_keycloak_admin_token() {
    echo "Obtaining Keycloak admin access token..."
    
    # Keycloak settings
    local KEYCLOAK_SERVER_URL="http://localhost:8080"
    local KEYCLOAK_ADMIN_USERNAME="admin"
    local KEYCLOAK_ADMIN_PASSWORD="admin"
    
    # Get admin token
    local TOKEN_RESPONSE=$(curl -s -k -X POST "$KEYCLOAK_SERVER_URL/realms/master/protocol/openid-connect/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$KEYCLOAK_ADMIN_USERNAME" \
        -d "password=$KEYCLOAK_ADMIN_PASSWORD" \
        -d "grant_type=password" \
        -d "client_id=admin-cli")
    
    if [ $? -ne 0 ]; then
        echo "Error: Could not connect to Keycloak server at $KEYCLOAK_SERVER_URL"
        return 1
    fi
    
    # Extract access token
    KEYCLOAK_ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r .access_token)
    
    if [ -z "$KEYCLOAK_ACCESS_TOKEN" ] || [ "$KEYCLOAK_ACCESS_TOKEN" == "null" ]; then
        echo "Error: Could not obtain Keycloak admin access token. Response: $TOKEN_RESPONSE"
        return 1
    fi
    
    echo "✅ Successfully obtained Keycloak admin access token"
    export KEYCLOAK_ACCESS_TOKEN
    return 0
}

# Function to make Keycloak API calls
make_api_call() {
    local METHOD="$1"
    local ENDPOINT="$2"
    local DATA_FILE="$3"
    local KEYCLOAK_SERVER_URL="http://localhost:8080"
    
    if [ -z "$KEYCLOAK_ACCESS_TOKEN" ]; then
        echo "Error: No Keycloak access token available"
        return 1
    fi
    
    local CURL_CMD="curl -s -k -X $METHOD"
    CURL_CMD="$CURL_CMD -H \"Authorization: Bearer $KEYCLOAK_ACCESS_TOKEN\""
    CURL_CMD="$CURL_CMD -H \"Content-Type: application/json\""
    
    if [ -n "$DATA_FILE" ] && [ -f "$DATA_FILE" ]; then
        CURL_CMD="$CURL_CMD -d @$DATA_FILE"
    fi
    
    CURL_CMD="$CURL_CMD -w \"\\n%{http_code}\""
    CURL_CMD="$CURL_CMD \"${KEYCLOAK_SERVER_URL}/admin${ENDPOINT}\""
    
    # Execute the curl command
    local RESPONSE=$(eval $CURL_CMD)
    API_CALL_STATUS=$(echo "$RESPONSE" | tail -n 1)
    # Fix for macOS head command - use sed instead
    API_CALL_RESPONSE=$(echo "$RESPONSE" | sed '$d')
    
    export API_CALL_STATUS
    export API_CALL_RESPONSE
}

# Main Keycloak setup function
setup_keycloak() {
    echo ""
    echo "==========================================="
    echo "Setting up Keycloak"
    echo "==========================================="
    
    local KEYCLOAK_DIR="keycloak"
    local DOCKER_COMPOSE_CMD="docker compose"
    
    # Check if legacy docker-compose is being used
    if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null 2>&1; then
        if command -v docker-compose &> /dev/null; then
            DOCKER_COMPOSE_CMD="docker-compose"
        else
            echo "Error: Neither 'docker compose' nor 'docker-compose' is available"
            return 1
        fi
    fi
    
    cd "$KEYCLOAK_DIR" || return 1
    
    # Start Keycloak if not already running
    echo "Starting Keycloak services..."
    $DOCKER_COMPOSE_CMD up -d
    
    # Wait for Keycloak to be ready
    echo "Waiting for Keycloak to be ready..."
    local RETRY_COUNT=0
    local MAX_RETRIES=30
    local SUCCESS=false
    
    until [ $RETRY_COUNT -ge $MAX_RETRIES ]; do
        RETRY_COUNT=$((RETRY_COUNT+1))
        # Check Keycloak health
        local HTTP_STATUS=$(curl -s -k -o /dev/null -w "%{http_code}" "http://localhost:8080/realms/master")
        if [ "$HTTP_STATUS" -eq 200 ]; then
            echo "✅ Keycloak is up and responding"
            SUCCESS=true
            break
        fi
        echo "Keycloak not ready yet (attempt $RETRY_COUNT/$MAX_RETRIES). Waiting 10 seconds..."
        sleep 10
    done
    
    if [ "$SUCCESS" = false ]; then
        echo "❌ Keycloak did not become ready in time"
        $DOCKER_COMPOSE_CMD logs keycloak
        cd ..
        return 1
    fi
    
    # Disable SSL requirement for master realm
    echo "Disabling SSL requirement for master realm..."
    local KEYCLOAK_CONTAINER=$(docker ps --filter "name=keycloak" --format "{{.Names}}" | grep -E "keycloak-keycloak|keycloak_keycloak" | head -n 1)
    if [ -n "$KEYCLOAK_CONTAINER" ]; then
        docker exec "$KEYCLOAK_CONTAINER" /opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password admin
        docker exec "$KEYCLOAK_CONTAINER" /opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=NONE
        echo "✅ SSL requirement disabled for master realm"
    fi
    
    # Get admin token
    if ! get_keycloak_admin_token; then
        echo "❌ Failed to get Keycloak admin token"
        cd ..
        return 1
    fi
    
    # Import ViolentUTF realm
    echo "Importing ViolentUTF realm..."
    local REALM_EXPORT_FILE="realm-export.json"
    
    if [ ! -f "$REALM_EXPORT_FILE" ]; then
        echo "❌ Error: $REALM_EXPORT_FILE not found!"
        cd ..
        return 1
    fi
    
    # Extract realm name
    local TARGET_REALM_NAME=$(jq -r .realm "$REALM_EXPORT_FILE")
    if [ -z "$TARGET_REALM_NAME" ] || [ "$TARGET_REALM_NAME" == "null" ]; then
        echo "❌ Error: Could not extract realm name from $REALM_EXPORT_FILE"
        cd ..
        return 1
    fi
    echo "Target realm name: $TARGET_REALM_NAME"
    
    # Check if realm already exists
    make_api_call "GET" "/realms/${TARGET_REALM_NAME}"
    if [ "$API_CALL_STATUS" -eq 200 ]; then
        echo "Realm '$TARGET_REALM_NAME' already exists. Deleting and re-importing..."
        make_api_call "DELETE" "/realms/${TARGET_REALM_NAME}"
        if [ "$API_CALL_STATUS" -ne 204 ]; then
            echo "❌ Failed to delete existing realm"
            cd ..
            return 1
        fi
        echo "Existing realm deleted"
    fi
    
    # Import the realm
    echo "Importing realm from $REALM_EXPORT_FILE..."
    make_api_call "POST" "/realms" "$REALM_EXPORT_FILE"
    if [ "$API_CALL_STATUS" -eq 201 ]; then
        echo "✅ Realm '$TARGET_REALM_NAME' imported successfully"
        
        # Disable SSL requirement for the imported realm
        echo "Disabling SSL requirement for realm '$TARGET_REALM_NAME'..."
        docker exec "$KEYCLOAK_CONTAINER" /opt/keycloak/bin/kcadm.sh update realms/${TARGET_REALM_NAME} -s sslRequired=NONE
        echo "✅ SSL requirement disabled for realm '$TARGET_REALM_NAME'"
    else
        echo "❌ Failed to import realm. Status: $API_CALL_STATUS"
        echo "Response: $API_CALL_RESPONSE"
        cd ..
        return 1
    fi
    
    # Configure ViolentUTF client
    echo "Configuring ViolentUTF client..."
    local VUTF_CLIENT_ID="violentutf"
    
    # Get client UUID
    make_api_call "GET" "/realms/${TARGET_REALM_NAME}/clients?clientId=${VUTF_CLIENT_ID}"
    if [ "$API_CALL_STATUS" -ne 200 ]; then
        echo "❌ Error: Could not get client info for 'violentutf'"
        cd ..
        return 1
    fi
    
    local KC_CLIENT_UUID=$(echo "$API_CALL_RESPONSE" | sed '$d' | jq -r '.[0].id')
    if [ -z "$KC_CLIENT_UUID" ] || [ "$KC_CLIENT_UUID" == "null" ]; then
        echo "❌ Error: Client 'violentutf' not found"
        cd ..
        return 1
    fi
    echo "Found client '${VUTF_CLIENT_ID}' with UUID '${KC_CLIENT_UUID}'"
    
    # Update client secret using PUT method (like original setup)
    if [ -n "$VIOLENTUTF_CLIENT_SECRET" ]; then
        echo "Updating client secret for 'violentutf'..."
        
        # Get current client configuration
        make_api_call "GET" "/realms/${TARGET_REALM_NAME}/clients/${KC_CLIENT_UUID}"
        if [ "$API_CALL_STATUS" -ne 200 ]; then
            echo "❌ Error: Failed to get client configuration"
            cd ..
            return 1
        fi
        
        # Update the client configuration with our pre-generated secret
        local CLIENT_CONFIG=$(echo "$API_CALL_RESPONSE" | sed '$d' | jq --arg secret "$VIOLENTUTF_CLIENT_SECRET" '.secret = $secret')
        
        # Save to temp file for the PUT request
        echo "$CLIENT_CONFIG" > /tmp/client-update.json
        
        # Update the client
        make_api_call "PUT" "/realms/${TARGET_REALM_NAME}/clients/${KC_CLIENT_UUID}" "/tmp/client-update.json"
        rm -f /tmp/client-update.json
        
        if [ "$API_CALL_STATUS" -eq 204 ]; then
            echo "✅ Successfully updated client 'violentutf' with pre-generated secret"
        else
            echo "❌ Error: Failed to update client secret. Status: $API_CALL_STATUS"
            cd ..
            return 1
        fi
    fi
    
    # Configure APISIX client
    echo "Configuring APISIX client..."
    local APISIX_CLIENT_ID="apisix"
    
    # Get client UUID
    make_api_call "GET" "/realms/${TARGET_REALM_NAME}/clients?clientId=${APISIX_CLIENT_ID}"
    if [ "$API_CALL_STATUS" -ne 200 ]; then
        echo "⚠️  Warning: Could not get APISIX client info"
    else
        local APISIX_CLIENT_UUID=$(echo "$API_CALL_RESPONSE" | sed '$d' | jq -r '.[0].id')
        if [ -n "$APISIX_CLIENT_UUID" ] && [ "$APISIX_CLIENT_UUID" != "null" ]; then
            echo "Found APISIX client with UUID '${APISIX_CLIENT_UUID}'"
            
            # Update APISIX client secret if needed
            if [ -n "$APISIX_CLIENT_SECRET" ]; then
                echo "Updating APISIX client secret..."
                
                # Get current client configuration
                make_api_call "GET" "/realms/${TARGET_REALM_NAME}/clients/${APISIX_CLIENT_UUID}"
                if [ "$API_CALL_STATUS" -eq 200 ]; then
                    # Update the client configuration with our pre-generated secret
                    local APISIX_CONFIG=$(echo "$API_CALL_RESPONSE" | sed '$d' | jq --arg secret "$APISIX_CLIENT_SECRET" '.secret = $secret')
                    
                    # Save to temp file for the PUT request
                    echo "$APISIX_CONFIG" > /tmp/apisix-update.json
                    
                    # Update the client
                    make_api_call "PUT" "/realms/${TARGET_REALM_NAME}/clients/${APISIX_CLIENT_UUID}" "/tmp/apisix-update.json"
                    rm -f /tmp/apisix-update.json
                    
                    if [ "$API_CALL_STATUS" -eq 204 ]; then
                        echo "✅ Successfully updated APISIX client secret"
                    else
                        echo "⚠️  Warning: Could not update APISIX client secret"
                    fi
                fi
            fi
        fi
    fi
    
    # Create ViolentUTF users if needed
    create_violentutf_users "$TARGET_REALM_NAME"
    
    cd ..
    echo "✅ Keycloak setup completed"
    return 0
}

# Function to create ViolentUTF users
create_violentutf_users() {
    local REALM_NAME="$1"
    
    echo "Creating ViolentUTF users..."
    
    # Create violentutf.web user
    local USER_JSON=$(cat <<EOF
{
    "username": "violentutf.web",
    "enabled": true,
    "emailVerified": true,
    "firstName": "ViolentUTF",
    "lastName": "Web User",
    "email": "violentutf.web@violentutf.local",
    "credentials": [{
        "type": "password",
        "value": "${VIOLENTUTF_USER_PASSWORD:-password123}",
        "temporary": false
    }]
}
EOF
)
    
    echo "$USER_JSON" > /tmp/user.json
    make_api_call "POST" "/realms/${REALM_NAME}/users" "/tmp/user.json"
    rm -f /tmp/user.json
    
    if [ "$API_CALL_STATUS" -eq 201 ]; then
        echo "✅ ViolentUTF user created successfully"
        echo "   Username: violentutf.web"
        echo "   Password: ${VIOLENTUTF_USER_PASSWORD:-password123}"
    elif [ "$API_CALL_STATUS" -eq 409 ]; then
        echo "ℹ️  ViolentUTF user already exists"
        echo "   Username: violentutf.web"
        echo "   Password: ${VIOLENTUTF_USER_PASSWORD:-password123}"
    else
        echo "⚠️  Could not create ViolentUTF user. Status: $API_CALL_STATUS"
    fi
}

# Function to verify Keycloak is properly configured
verify_keycloak_setup() {
    echo "Verifying Keycloak setup..."
    
    # Check if Keycloak is running
    if ! docker ps | grep -q keycloak; then
        echo "❌ Keycloak container is not running"
        return 1
    fi
    
    # Check master realm
    local MASTER_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080/realms/master/.well-known/openid-configuration")
    if [ "$MASTER_STATUS" -ne 200 ]; then
        echo "❌ Keycloak master realm is not accessible"
        return 1
    fi
    
    # Check ViolentUTF realm
    local VUTF_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080/realms/ViolentUTF/.well-known/openid-configuration")
    if [ "$VUTF_STATUS" -ne 200 ]; then
        echo "❌ ViolentUTF realm is not accessible"
        return 1
    fi
    
    echo "✅ Keycloak is properly configured"
    return 0
}