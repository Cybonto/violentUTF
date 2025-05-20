#!/usr/bin/env bash
# setup_macos.sh (API Version with APISIX integration, network fixes, and cleanup option)

# --- Parse command line arguments ---
CLEANUP_MODE=false
for arg in "$@"; do
    case $arg in
        --cleanup)
            CLEANUP_MODE=true
            shift # Remove --cleanup from processing
            ;;
        *)
            # Unknown option
            echo "Unknown option: $arg"
            echo "Usage: $0 [--cleanup]"
            exit 1
            ;;
    esac
done

# --- Store generated sensitive values for final report ---
SENSITIVE_VALUES=()

# --- Define shared network name globally ---
SHARED_NETWORK_NAME="vutf-network"

# --- Cleanup function ---
perform_cleanup() {
    echo "Starting cleanup process..."
    
    # Remember current directory
    ORIGINAL_DIR=$(pwd)
    
    # 1. Stop and remove Keycloak containers
    echo "Stopping and removing Keycloak containers..."
    if [ -d "keycloak" ]; then
        cd "keycloak" || { echo "Failed to cd into keycloak directory"; exit 1; }
        docker-compose down -v 2>/dev/null || docker compose down -v 2>/dev/null
        cd "$ORIGINAL_DIR"
    fi
    
    # 2. Stop and remove APISIX containers
    echo "Stopping and removing APISIX containers..."
    if [ -d "apisix" ]; then
        cd "apisix" || { echo "Failed to cd into apisix directory"; exit 1; }
        docker-compose down -v 2>/dev/null || docker compose down -v 2>/dev/null
        cd "$ORIGINAL_DIR"
    fi
    
    # 3. Remove shared network if it exists and is not in use
    echo "Removing shared Docker network..."
    if docker network inspect $SHARED_NETWORK_NAME >/dev/null 2>&1; then
        if docker network rm $SHARED_NETWORK_NAME >/dev/null 2>&1; then
            echo "Removed shared network '$SHARED_NETWORK_NAME'."
        else
            echo "Warning: Could not remove shared network '$SHARED_NETWORK_NAME'. It may still be in use."
        fi
    fi
    
    # 4. Remove configuration files but preserve directories
    echo "Removing configuration files..."
    
    # Keycloak files
    if [ -f "keycloak/.env" ]; then
        rm "keycloak/.env"
        echo "Removed keycloak/.env"
    fi
    
    # APISIX files - remove all non-template configurations
    if [ -d "apisix/conf" ]; then
        # Move only template files to a temp directory
        mkdir -p "/tmp/apisix_templates"
        find "apisix/conf" -name "*.template" -exec cp {} "/tmp/apisix_templates/" \;
        
        # Remove all config files
        rm -rf "apisix/conf/"*
        
        # Move templates back
        mkdir -p "apisix/conf"
        cp "/tmp/apisix_templates/"* "apisix/conf/" 2>/dev/null || true
        rm -rf "/tmp/apisix_templates"
        
        echo "Restored only template files in apisix/conf directory"
    fi
    
    # ViolentUTF files
    if [ -f "violentutf/.env" ]; then
        rm "violentutf/.env"
        echo "Removed violentutf/.env"
    fi
    
    if [ -f "violentutf/.streamlit/secrets.toml" ]; then
        rm "violentutf/.streamlit/secrets.toml"
        echo "Removed violentutf/.streamlit/secrets.toml"
    fi
    
    # 5. Remove Docker volumes
    echo "Removing Docker volumes related to Keycloak and APISIX..."
    # Get volume list and filter for keycloak and apisix volumes
    VOLUMES_TO_REMOVE=$(docker volume ls -q | grep -E '(keycloak|apisix)')
    if [ -n "$VOLUMES_TO_REMOVE" ]; then
        echo "$VOLUMES_TO_REMOVE" | xargs docker volume rm
        echo "Removed Docker volumes."
    else
        echo "No relevant Docker volumes found to remove."
    fi
    
    echo "Cleanup completed successfully!"
    echo "The Python virtual environment has been preserved."
    echo "You can now run the script again for a fresh setup."
    exit 0
}

# Function to ensure Docker Compose files have shared network configuration
ensure_network_in_compose() {
    local compose_file="$1"
    local service_name="$2"
    
    # Check if file exists
    if [ ! -f "$compose_file" ]; then
        echo "Error: Docker Compose file $compose_file not found!"
        return 1
    fi
    
    # Backup the compose file
    local backup_suffix=$(date +"%Y%m%d%H%M%S")
    cp "$compose_file" "${compose_file}.bak${backup_suffix}"
    
    # Check if the file already has vutf-network section
    if ! grep -q "vutf-network:" "$compose_file"; then
        # Add networks section if missing
        if ! grep -q "^networks:" "$compose_file"; then
            echo "" >> "$compose_file"
            echo "networks:" >> "$compose_file"
        fi
        
        # Add vutf-network to networks section
        sed -i '' '/^networks:/a\
  vutf-network:\
    external: true' "$compose_file"
        
        echo "Added vutf-network to networks section in $compose_file"
    fi
    
    # Check if service section exists
    if ! grep -q "^  $service_name:" "$compose_file"; then
        echo "Warning: Service $service_name not found in $compose_file"
        return 0
    fi
    
    # Add network to service if missing
    if ! grep -A20 "^  $service_name:" "$compose_file" | grep -q "vutf-network"; then
        # Check if networks section exists in the service
        if grep -A20 "^  $service_name:" "$compose_file" | grep -q "    networks:"; then
            # Add vutf-network to existing networks section
            linenum=$(grep -n "^  $service_name:" "$compose_file" | cut -d: -f1)
            if [ -n "$linenum" ]; then
                # Find networks section within this service
                netlinenum=$(tail -n +$linenum "$compose_file" | grep -n "    networks:" | head -1 | cut -d: -f1)
                if [ -n "$netlinenum" ]; then
                    netlinenum=$((linenum + netlinenum))
                    sed -i '' "${netlinenum}a\\
      - vutf-network" "$compose_file"
                fi
            fi
        else
            # Add a new networks section to the service
            sed -i '' "/^  $service_name:/a\\
    networks:\\
      - vutf-network" "$compose_file"
        fi
        
        echo "Added vutf-network to $service_name service in $compose_file"
    fi
    
    return 0
}

# If cleanup mode, perform cleanup and exit
if [ "$CLEANUP_MODE" = true ]; then
    perform_cleanup
fi

# --- Global Keycloak API Variables ---
KEYCLOAK_SERVER_URL="http://localhost:8080"
ADMIN_USER="admin"
ADMIN_PASS="admin" # From your docker-compose.yml
MASTER_REALM="master"
ADMIN_CLIENT_ID="admin-cli"
ACCESS_TOKEN="" # Will be populated by get_keycloak_admin_token

# --- Global APISIX Variables ---
APISIX_URL="http://localhost:9080"
APISIX_ADMIN_URL="http://localhost:9180"
APISIX_DASHBOARD_URL="http://localhost:9001"

# Function to generate a random secure string
generate_secure_string() {
    openssl rand -base64 32 | tr -d '\n' | tr -d '\r' | tr -d '/' | tr -d '+' | tr -d '=' | cut -c1-32
}

# Function to backup and prepare config file from template
prepare_config_from_template() {
    local template_file="$1"
    local target_file="${template_file%.template}"
    local backup_suffix=$(date +"%Y%m%d%H%M%S")
    
    # Check if template exists
    if [ ! -f "$template_file" ]; then
        echo "Error: Template file $template_file not found!"
        return 1
    fi
    
    # Backup existing file if it exists
    if [ -f "$target_file" ]; then
        cp "$target_file" "${target_file}.bak${backup_suffix}"
        echo "Backed up $target_file to ${target_file}.bak${backup_suffix}"
    fi
    
    # Copy template to target
    cp "$template_file" "$target_file"
    echo "Created $target_file from template"
    
    return 0
}

# Function to replace placeholder in a file with a value
replace_in_file() {
    local file="$1"
    local placeholder="$2"
    local value="$3"
    local description="$4"
    
    # For macOS compatibility, use sed with backup extension
    sed -i '' "s|${placeholder}|${value}|g" "$file"
    
    # Store for final report if description is provided
    if [ -n "$description" ]; then
        SENSITIVE_VALUES+=("$description: $value")
    fi
    
    echo "Replaced $placeholder in $file"
}

# Function to obtain Keycloak admin access token
get_keycloak_admin_token() {
    echo "Attempting to obtain Keycloak admin access token..."
    local token_response
    token_response=$(curl -s -X POST "${KEYCLOAK_SERVER_URL}/realms/${MASTER_REALM}/protocol/openid-connect/token" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=${ADMIN_USER}" \
      -d "password=${ADMIN_PASS}" \
      -d "grant_type=password" \
      -d "client_id=${ADMIN_CLIENT_ID}")

    ACCESS_TOKEN=$(echo "${token_response}" | jq -r .access_token)

    if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "null" ]; then
        echo "Error: Could not obtain Keycloak admin access token."
        echo "Response: ${token_response}"
        exit 1
    fi
    echo "Successfully obtained Keycloak admin access token."
}

# Function to make an authenticated API call to Keycloak
# Usage: make_api_call <HTTP_METHOD> <ENDPOINT_PATH_FROM_ADMIN_ROOT> [JSON_DATA_FILE_PATH or JSON_STRING]
# Example: make_api_call "GET" "/realms"
# Example: make_api_call "POST" "/realms" "path/to/realm.json"
# Example: make_api_call "PUT" "/realms/myrealm/users/userid/reset-password" '{"type":"password", "value":"newpass", "temporary":false}'
# Returns the HTTP status code in global variable API_CALL_STATUS and response body in API_CALL_RESPONSE
make_api_call() {
    local method="$1"
    local endpoint_path="$2"
    local data_arg="$3"
    local full_url="${KEYCLOAK_SERVER_URL}/admin${endpoint_path}" # Note: /admin path
    local response_output response_file http_code

    response_file=$(mktemp) # Create a temporary file to store the response body

    local curl_opts=(-s -w "%{http_code}" -o "${response_file}" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -X "${method}")

    if [ -n "$data_arg" ]; then
        curl_opts+=(-H "Content-Type: application/json")
        if [ -f "$data_arg" ]; then # If it's a file path
            curl_opts+=(--data-binary "@${data_arg}")
        else # Assume it's a JSON string
            curl_opts+=(--data-binary "${data_arg}")
        fi
    fi

    echo "Executing API call: ${method} ${full_url}"
    http_code=$(curl "${curl_opts[@]}" "${full_url}")

    API_CALL_RESPONSE=$(cat "${response_file}")
    rm -f "${response_file}"
    API_CALL_STATUS=$http_code

    # Basic logging of request and response for debugging
    # echo "API Request: ${method} ${full_url}"
    # if [ -n "$data_arg" ]; then echo "Request Data: $(cat "$data_arg" 2>/dev/null || echo "$data_arg")"; fi
    # echo "API Status: ${API_CALL_STATUS}"
    # echo "API Response: ${API_CALL_RESPONSE}"
}

# Enhanced network test function
test_network_connectivity() {
    local from_container="$1"
    local to_service="$2"
    local to_port="$3"
    local container_id
    
    # Find the container ID for the service
    container_id=$(docker ps --filter "name=${from_container}" --format "{{.ID}}" | head -n 1)
    if [ -z "$container_id" ]; then
        echo "Container '${from_container}' not found!"
        return 1
    fi
    
    echo "⚙️ Testing connectivity from ${from_container} to ${to_service}:${to_port}..."
    
    # Test 1: Basic ping (network layer)
    echo "Running ping test (network layer)..."
    if docker exec $container_id ping -c 2 $to_service &>/dev/null; then
        echo "✓ Ping successful - network layer connectivity confirmed"
    else
        echo "✗ Ping failed - DNS resolution or network connectivity issue"
        
        # Try to diagnose DNS resolution
        echo "Checking DNS resolution inside container..."
        docker exec $container_id cat /etc/resolv.conf
        docker exec $container_id nslookup $to_service 2>/dev/null || true
        
        # Show network list for diagnosis
        echo "Networks for $from_container container:"
        docker inspect --format='{{range $net,$v := .NetworkSettings.Networks}}{{$net}} {{end}}' $container_id
        
        return 1
    fi
    
    # Test 2: Try HTTP connection (application layer)
    echo "Running HTTP test (application layer)..."
    if docker exec $container_id curl -s -o /dev/null -w "%{http_code}" "http://${to_service}:${to_port}" 2>/dev/null; then
        echo "✓ HTTP connection successful - application layer connectivity confirmed"
        return 0
    else
        echo "✗ HTTP connection failed - service may not be accepting connections"
        return 1
    fi
}


echo "Starting ViolentUTF Nightly with Keycloak and APISIX Setup for macOS..."

# ---------------------------------------------------------------
# 1. Check Docker and Docker Compose
# ---------------------------------------------------------------
echo "Step 1: Checking Docker and Docker Compose..."
if ! command -v docker &> /dev/null; then
    echo "Docker could not be found. Please install Docker Desktop for Mac."
    echo "Visit https://docs.docker.com/desktop/install/mac-install/ for installation instructions."
    exit 1
fi

DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version &> /dev/null; then
    echo "Docker Compose (V2 CLI plugin) could not be found. Trying older 'docker-compose'..."
    if ! command -v docker-compose &> /dev/null; then
        echo "Neither 'docker compose' nor 'docker-compose' found."
        echo "Ensure you have Docker Desktop for Mac installed and running."
        exit 1
    else
        DOCKER_COMPOSE_CMD="docker-compose"
        echo "Found older 'docker-compose'. Will use that."
    fi
fi
echo "Using Docker Compose command: $DOCKER_COMPOSE_CMD"


if ! docker info &> /dev/null || ! docker ps &> /dev/null; then
    echo "Docker daemon is not running or current user cannot connect to it."
    echo "Please start Docker Desktop and ensure it's running."
    exit 1
fi
echo "Docker and Docker Compose check passed."

# Create a shared network for all services
echo "Ensuring shared Docker network exists..."
if ! docker network inspect $SHARED_NETWORK_NAME >/dev/null 2>&1; then
    echo "Creating shared Docker network '$SHARED_NETWORK_NAME'..."
    docker network create $SHARED_NETWORK_NAME
    echo "Shared network created."
else
    echo "Shared network '$SHARED_NETWORK_NAME' already exists."
fi

# ---------------------------------------------------------------
# SECTION A: KEYCLOAK SETUP
# ---------------------------------------------------------------
echo "SECTION A: SETTING UP KEYCLOAK"

# ---------------------------------------------------------------
# 2. Copy and populate keycloak/.env
# ---------------------------------------------------------------
echo "Step 2: Setting up keycloak/.env..."
KEYCLOAK_ENV_DIR="keycloak"
KEYCLOAK_ENV_SAMPLE="${KEYCLOAK_ENV_DIR}/env.sample"
KEYCLOAK_ENV_FILE="${KEYCLOAK_ENV_DIR}/.env"

if [ ! -f "$KEYCLOAK_ENV_SAMPLE" ]; then
    echo "Error: $KEYCLOAK_ENV_SAMPLE not found!"
    echo "Please create it with 'replace_key' placeholders for values like POSTGRES_PASSWORD."
    echo "Example content for keycloak/env.sample:"
    echo "POSTGRES_PASSWORD=replace_key"
    # Create dummy if not exists for script to proceed
    mkdir -p "$KEYCLOAK_ENV_DIR"
    echo "POSTGRES_PASSWORD=replace_key" > "$KEYCLOAK_ENV_SAMPLE"
    echo "Created a dummy ${KEYCLOAK_ENV_SAMPLE}. Please review it."
fi

cp "$KEYCLOAK_ENV_SAMPLE" "$KEYCLOAK_ENV_FILE"
echo "Copied $KEYCLOAK_ENV_SAMPLE to $KEYCLOAK_ENV_FILE."

TEMP_FILE_ENV_REPLACE=$(mktemp)
cp "$KEYCLOAK_ENV_FILE" "$TEMP_FILE_ENV_REPLACE"
# Count occurrences of replace_key
COUNT_REPLACE_KEY=$(grep -o "replace_key" "$TEMP_FILE_ENV_REPLACE" | wc -l)
for (( i=1; i<=$COUNT_REPLACE_KEY; i++ )); do
    SECURE_VAL=$(generate_secure_string)
    awk -v val="$SECURE_VAL" '/replace_key/ && !done {sub(/replace_key/, val); done=1} 1' "$TEMP_FILE_ENV_REPLACE" > "$KEYCLOAK_ENV_FILE"
    cp "$KEYCLOAK_ENV_FILE" "$TEMP_FILE_ENV_REPLACE" # Update temp file for next iteration
    
    # Store for final report - grab the key that was replaced
    if [ $i -eq 1 ]; then
        SENSITIVE_VALUES+=("Keycloak Postgres Password: $SECURE_VAL")
    fi
done
rm "$TEMP_FILE_ENV_REPLACE"
echo "Replaced 'replace_key' placeholders in $KEYCLOAK_ENV_FILE with secure random strings."
echo "Keycloak .env file generated."

# ---------------------------------------------------------------
# 3. Check Keycloak stack and launch if not running
# ---------------------------------------------------------------
echo "Step 3: Checking and launching Keycloak Docker stack..."
KEYCLOAK_SERVICE_NAME_IN_COMPOSE="keycloak" # As defined in your docker-compose.yml

KEYCLOAK_SETUP_NEEDED=true
# Check if the service is running using docker compose ps
if ${DOCKER_COMPOSE_CMD} -f "${KEYCLOAK_ENV_DIR}/docker-compose.yml" ps -q ${KEYCLOAK_SERVICE_NAME_IN_COMPOSE} 2>/dev/null | grep -q .; then
    CONTAINER_ID=$(${DOCKER_COMPOSE_CMD} -f "${KEYCLOAK_ENV_DIR}/docker-compose.yml" ps -q ${KEYCLOAK_SERVICE_NAME_IN_COMPOSE} 2>/dev/null)
    if [ -n "$CONTAINER_ID" ]; then
      if docker inspect -f '{{.State.Running}}' "$CONTAINER_ID" 2>/dev/null | grep -q "true"; then
        echo "Keycloak service '${KEYCLOAK_SERVICE_NAME_IN_COMPOSE}' appears to be already running."
        KEYCLOAK_SETUP_NEEDED=false
      fi
    fi
fi

if [ "$KEYCLOAK_SETUP_NEEDED" = true ]; then
    echo "Keycloak stack not found or not running. Proceeding with setup."
    # Store current directory and cd into keycloak dir
    ORIGINAL_DIR=$(pwd)
    cd "$KEYCLOAK_ENV_DIR" || { echo "Failed to cd into $KEYCLOAK_ENV_DIR"; exit 1; }
    
    # Ensure docker-compose.yml has network configuration
    echo "Ensuring Keycloak docker-compose.yml has proper network configuration..."
    ensure_network_in_compose "docker-compose.yml" "keycloak"
    
    echo "Launching Docker Compose for Keycloak..."
    if ${DOCKER_COMPOSE_CMD} up -d; then
        echo "Keycloak stack started successfully."
        echo "Waiting for Keycloak to be fully operational (this might take a minute or two)..."
        RETRY_COUNT=0
        MAX_RETRIES=30 # ~5 minutes
        SUCCESS=false
        until [ $RETRY_COUNT -ge $MAX_RETRIES ]; do
            RETRY_COUNT=$((RETRY_COUNT+1))
            # Check Keycloak health/ready endpoint (not admin API, no token needed for this one)
            HTTP_STATUS_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "${KEYCLOAK_SERVER_URL}/realms/master")
            if [ "$HTTP_STATUS_HEALTH" -eq 200 ]; then
                echo "Keycloak is up and responding on its main endpoint."
                SUCCESS=true
                break
            fi
            echo "Keycloak not ready yet (attempt $RETRY_COUNT/$MAX_RETRIES, status $HTTP_STATUS_HEALTH). Waiting 10 seconds..."
            sleep 10
        done

        if [ "$SUCCESS" = false ]; then
            echo "Keycloak did not become ready in time. Please check Docker logs."
            ${DOCKER_COMPOSE_CMD} logs ${KEYCLOAK_SERVICE_NAME_IN_COMPOSE}
            cd "$ORIGINAL_DIR"
            exit 1
        fi
    else
        echo "Failed to start Keycloak stack. Check Docker Compose logs."
        ${DOCKER_COMPOSE_CMD} logs
        cd "$ORIGINAL_DIR"
        exit 1
    fi
    cd "$ORIGINAL_DIR" # Return to the original directory

    # Ensure the container is connected to the shared network
    echo "Ensuring Keycloak container is connected to shared network..."
    KEYCLOAK_CONTAINER=$(docker ps --filter "name=keycloak" --format "{{.ID}}" | head -n 1)
    if [ -n "$KEYCLOAK_CONTAINER" ]; then
        # Check if already connected
        if ! docker inspect "$KEYCLOAK_CONTAINER" | grep -q "\"$SHARED_NETWORK_NAME\""; then
            echo "Manually connecting Keycloak container to shared network..."
            docker network connect $SHARED_NETWORK_NAME $KEYCLOAK_CONTAINER
            echo "Keycloak container connected to $SHARED_NETWORK_NAME"
        else
            echo "Keycloak container already connected to $SHARED_NETWORK_NAME"
        fi
    fi
fi


if [ "$KEYCLOAK_SETUP_NEEDED" = true ]; then
    get_keycloak_admin_token # Obtain admin token for subsequent API calls

    # ---------------------------------------------------------------
    # 4. Import realm-export.json to Keycloak via API
    # ---------------------------------------------------------------
    echo "Step 4: Importing Keycloak realm via API..."
    REALM_EXPORT_FILE="${KEYCLOAK_ENV_DIR}/realm-export.json"

    if [ ! -f "$REALM_EXPORT_FILE" ]; then
        echo "Error: $REALM_EXPORT_FILE not found!"
        exit 1
    fi
    
    # Extract realm name from the export file
    TARGET_REALM_NAME=$(jq -r .realm "$REALM_EXPORT_FILE")
    if [ -z "$TARGET_REALM_NAME" ] || [ "$TARGET_REALM_NAME" == "null" ]; then
        echo "Error: Could not extract realm name from $REALM_EXPORT_FILE"
        exit 1
    fi
    echo "Target realm name: $TARGET_REALM_NAME"

    # Check if realm already exists
    make_api_call "GET" "/realms/${TARGET_REALM_NAME}"
    if [ "$API_CALL_STATUS" -eq 200 ]; then
        echo "Realm '$TARGET_REALM_NAME' already exists. Deleting and re-importing."
        make_api_call "DELETE" "/realms/${TARGET_REALM_NAME}"
        if [ "$API_CALL_STATUS" -ne 204 ]; then # 204 No Content is success for DELETE
            echo "Failed to delete existing realm '$TARGET_REALM_NAME'. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
            exit 1
        fi
        echo "Existing realm '$TARGET_REALM_NAME' deleted."
    elif [ "$API_CALL_STATUS" -ne 404 ]; then # 404 Not Found is okay (realm doesn't exist)
        echo "Error checking for realm '$TARGET_REALM_NAME'. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi

    echo "Importing realm '$TARGET_REALM_NAME' from $REALM_EXPORT_FILE via API..."
    make_api_call "POST" "/realms" "$REALM_EXPORT_FILE"
    if [ "$API_CALL_STATUS" -eq 201 ]; then # 201 Created is success for POST
        echo "Realm '$TARGET_REALM_NAME' imported successfully via API."
    else
        echo "Failed to import realm '$TARGET_REALM_NAME' via API. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi

    # ---------------------------------------------------------------
    # 5. Copy violentutf env.sample and secrets.toml.sample
    # ---------------------------------------------------------------
    echo "Step 5: Setting up violentutf .env and secrets.toml..."
    VIOLENTUTF_DIR="violentutf"
    VIOLENTUTF_ENV_SAMPLE="${VIOLENTUTF_DIR}/env.sample"
    VIOLENTUTF_ENV_FILE="${VIOLENTUTF_DIR}/.env"
    VIOLENTUTF_SECRETS_DIR="${VIOLENTUTF_DIR}/.streamlit"
    VIOLENTUTF_SECRETS_SAMPLE="${VIOLENTUTF_SECRETS_DIR}/secrets.toml.sample"
    VIOLENTUTF_SECRETS_FILE="${VIOLENTUTF_SECRETS_DIR}/secrets.toml"

    if [ ! -f "$VIOLENTUTF_ENV_SAMPLE" ]; then
        echo "Warning: $VIOLENTUTF_ENV_SAMPLE not found. Creating a dummy one."
        mkdir -p "$VIOLENTUTF_DIR"
        {
            echo "KEYCLOAK_CLIENT_SECRET=replace_client_secret"
            echo "KEYCLOAK_USERNAME=testuser"
            echo "KEYCLOAK_PASSWORD=replace_password"
            echo "PYRIT_DB_SALT=replace_pyrit_salt"
        } > "$VIOLENTUTF_ENV_SAMPLE"
    fi
    cp "$VIOLENTUTF_ENV_SAMPLE" "$VIOLENTUTF_ENV_FILE"
    echo "Copied $VIOLENTUTF_ENV_SAMPLE to $VIOLENTUTF_ENV_FILE."

    mkdir -p "$VIOLENTUTF_SECRETS_DIR"
    if [ ! -f "$VIOLENTUTF_SECRETS_SAMPLE" ]; then
        echo "Warning: $VIOLENTUTF_SECRETS_SAMPLE not found. Creating a dummy one."
        {
            echo "client_secret = \"replace_client_secret\""
            echo "cookie_secret = \"replace_cookie_secret\""
        } > "$VIOLENTUTF_SECRETS_SAMPLE"
    fi
    cp "$VIOLENTUTF_SECRETS_SAMPLE" "$VIOLENTUTF_SECRETS_FILE"
    echo "Copied $VIOLENTUTF_SECRETS_SAMPLE to $VIOLENTUTF_SECRETS_FILE."

    # ---------------------------------------------------------------
    # 6. Keycloak API changes for ViolentUTF realm/client
    # ---------------------------------------------------------------
    echo "Step 6: Configuring ViolentUTF client in Keycloak via API..."
    VUTF_REALM_NAME="$TARGET_REALM_NAME" # Should be "ViolentUTF"
    VUTF_CLIENT_ID_TO_CONFIGURE="violentutf" # As per your realm-export.json

    # Get internal client ID (UUID) for the 'violentutf' client
    make_api_call "GET" "/realms/${VUTF_REALM_NAME}/clients?clientId=${VUTF_CLIENT_ID_TO_CONFIGURE}"
    if [ "$API_CALL_STATUS" -ne 200 ]; then
        echo "Error: Could not get client info for '${VUTF_CLIENT_ID_TO_CONFIGURE}'. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi
    KC_CLIENT_UUID=$(echo "$API_CALL_RESPONSE" | jq -r '.[0].id') # Assumes unique client ID returns one item in array
    if [ -z "$KC_CLIENT_UUID" ] || [ "$KC_CLIENT_UUID" == "null" ]; then
        echo "Error: Client '${VUTF_CLIENT_ID_TO_CONFIGURE}' not found in realm '${VUTF_REALM_NAME}' via API."
        exit 1
    fi
    echo "Found client '${VUTF_CLIENT_ID_TO_CONFIGURE}' with UUID '${KC_CLIENT_UUID}'."

    # Regenerate client secret
    echo "Regenerating client secret for '${VUTF_CLIENT_ID_TO_CONFIGURE}' via API..."
    make_api_call "POST" "/realms/${VUTF_REALM_NAME}/clients/${KC_CLIENT_UUID}/client-secret"
    if [ "$API_CALL_STATUS" -ne 200 ]; then # POST to this endpoint returns 200 with the new secret
        echo "Error: Failed to regenerate client secret via API. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi
    NEW_CLIENT_SECRET=$(echo "$API_CALL_RESPONSE" | jq -r .value)
    if [ -z "$NEW_CLIENT_SECRET" ] || [ "$NEW_CLIENT_SECRET" == "null" ]; then
        echo "Error: Failed to parse new client secret from API response."
        exit 1
    fi
    echo "New client secret generated via API."
    SENSITIVE_VALUES+=("Keycloak Client Secret: $NEW_CLIENT_SECRET")

    # Update violentutf/.env and violentutf/.streamlit/secrets.toml
    sed -i '' "s|^KEYCLOAK_CLIENT_SECRET=.*|KEYCLOAK_CLIENT_SECRET=${NEW_CLIENT_SECRET}|" "$VIOLENTUTF_ENV_FILE"
    escaped_new_client_secret=$(printf '%s\n' "$NEW_CLIENT_SECRET" | sed 's/[\&/]/\\&/g; s/"/\\"/g') # Escape for sed and ensure quotes in TOML are handled
    sed -i '' "s|^client_secret =.*|client_secret = \"${escaped_new_client_secret}\"|" "$VIOLENTUTF_SECRETS_FILE"
    echo "Updated KEYCLOAK_CLIENT_SECRET in $VIOLENTUTF_ENV_FILE and client_secret in $VIOLENTUTF_SECRETS_FILE."

    # Read KEYCLOAK_USERNAME from violentutf/.env
    # Use awk for more robust parsing, allowing for spaces around '=' and trimming whitespace.
    KEYCLOAK_APP_USERNAME=$(awk -F= '/^KEYCLOAK_USERNAME[[:space:]]*=/ {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' "$VIOLENTUTF_ENV_FILE")
    
    if [ -z "$KEYCLOAK_APP_USERNAME" ]; then
        echo "Warning: KEYCLOAK_USERNAME not found or is empty in $VIOLENTUTF_ENV_FILE."
        KEYCLOAK_APP_USERNAME="testuser" 
        echo "Defaulting KEYCLOAK_USERNAME to 'testuser'."
        # Check if the line exists to update, otherwise append
        if grep -q "^KEYCLOAK_USERNAME[[:space:]]*=" "$VIOLENTUTF_ENV_FILE"; then
            sed -i '' "s|^KEYCLOAK_USERNAME[[:space:]]*=.*|KEYCLOAK_USERNAME=${KEYCLOAK_APP_USERNAME}|" "$VIOLENTUTF_ENV_FILE"
        else
            echo "KEYCLOAK_USERNAME=${KEYCLOAK_APP_USERNAME}" >> "$VIOLENTUTF_ENV_FILE"
        fi
        echo "Updated $VIOLENTUTF_ENV_FILE with default username."
    fi
    echo "Using KEYCLOAK_USERNAME: $KEYCLOAK_APP_USERNAME"
    SENSITIVE_VALUES+=("Keycloak Username: $KEYCLOAK_APP_USERNAME")

    # Check if user exists, if not, create
    make_api_call "GET" "/realms/${VUTF_REALM_NAME}/users?username=${KEYCLOAK_APP_USERNAME}&exact=true" # Added exact=true for precise match
    if [ "$API_CALL_STATUS" -ne 200 ]; then
        echo "Error checking for user '${KEYCLOAK_APP_USERNAME}'. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi
    
    # jq needs to handle an empty array if user not found, or an array with one user if found
    USER_EXISTS_ID=$(echo "$API_CALL_RESPONSE" | jq -r 'if type == "array" and length > 0 then .[0].id else null end')
    
    if [ "$USER_EXISTS_ID" == "null" ] || [ -z "$USER_EXISTS_ID" ]; then
        echo "User '${KEYCLOAK_APP_USERNAME}' not found. Creating user via API..."
        USER_CREATE_PAYLOAD="{\"username\":\"${KEYCLOAK_APP_USERNAME}\", \"enabled\":true}"
        make_api_call "POST" "/realms/${VUTF_REALM_NAME}/users" "${USER_CREATE_PAYLOAD}"
        
        if [ "$API_CALL_STATUS" -ne 201 ]; then
            echo "Error: Failed to create user '${KEYCLOAK_APP_USERNAME}' via API. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
            exit 1
        fi
        # Re-fetch user to get ID, as POST might not return it directly or only in Location header
        make_api_call "GET" "/realms/${VUTF_REALM_NAME}/users?username=${KEYCLOAK_APP_USERNAME}&exact=true"
        if [ "$API_CALL_STATUS" -ne 200 ]; then
             echo "Error fetching newly created user '${KEYCLOAK_APP_USERNAME}'. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
             exit 1
        fi
        USER_EXISTS_ID=$(echo "$API_CALL_RESPONSE" | jq -r 'if type == "array" and length > 0 then .[0].id else null end')
        if [ "$USER_EXISTS_ID" == "null" ] || [ -z "$USER_EXISTS_ID" ]; then
            echo "Error: Failed to retrieve ID for newly created user '${KEYCLOAK_APP_USERNAME}'."
            exit 1
        fi
        echo "User '${KEYCLOAK_APP_USERNAME}' created with ID '${USER_EXISTS_ID}'."
    else
        echo "User '${KEYCLOAK_APP_USERNAME}' already exists with ID '${USER_EXISTS_ID}'."
    fi

    # Create/Reset credential for the user
    echo "Setting a new password for user '${KEYCLOAK_APP_USERNAME}' via API..."
    NEW_USER_PASSWORD=$(generate_secure_string)
    PASSWORD_RESET_PAYLOAD="{\"type\":\"password\", \"value\":\"${NEW_USER_PASSWORD}\", \"temporary\":false}"
    make_api_call "PUT" "/realms/${VUTF_REALM_NAME}/users/${USER_EXISTS_ID}/reset-password" "${PASSWORD_RESET_PAYLOAD}"
    if [ "$API_CALL_STATUS" -ne 204 ]; then # 204 No Content is success
        echo "Error: Failed to set password for user '${KEYCLOAK_APP_USERNAME}' via API. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi
    echo "Password for user '${KEYCLOAK_APP_USERNAME}' has been set via API."
    SENSITIVE_VALUES+=("Keycloak User Password: $NEW_USER_PASSWORD")

    # Update KEYCLOAK_PASSWORD in violentutf/.env
    # Use a temporary file for sed to avoid issues with in-place editing on some macOS sed versions with certain patterns
    TMP_ENV_FILE=$(mktemp)
    sed "s|^KEYCLOAK_PASSWORD[[:space:]]*=.*|KEYCLOAK_PASSWORD=${NEW_USER_PASSWORD}|" "$VIOLENTUTF_ENV_FILE" > "$TMP_ENV_FILE" && mv "$TMP_ENV_FILE" "$VIOLENTUTF_ENV_FILE"
    echo "Updated KEYCLOAK_PASSWORD in $VIOLENTUTF_ENV_FILE."

    # ---------------------------------------------------------------
    # 7. Generate secure secrets for PYRIT_DB_SALT and cookie_secret
    # ---------------------------------------------------------------
    echo "Step 7: Generating other secure secrets..."
    NEW_PYRIT_SALT=$(generate_secure_string)
    NEW_COOKIE_SECRET=$(generate_secure_string)

    sed -i '' "s|^PYRIT_DB_SALT[[:space:]]*=.*|PYRIT_DB_SALT=${NEW_PYRIT_SALT}|" "$VIOLENTUTF_ENV_FILE"
    escaped_new_cookie_secret=$(printf '%s\n' "$NEW_COOKIE_SECRET" | sed 's/[\&/]/\\&/g; s/"/\\"/g')
    sed -i '' "s|^cookie_secret[[:space:]]*=.*|cookie_secret = \"${escaped_new_cookie_secret}\"|" "$VIOLENTUTF_SECRETS_FILE"
    echo "Updated PYRIT_DB_SALT in $VIOLENTUTF_ENV_FILE and cookie_secret in $VIOLENTUTF_SECRETS_FILE."
    SENSITIVE_VALUES+=("PYRIT DB Salt: $NEW_PYRIT_SALT")
    SENSITIVE_VALUES+=("Cookie Secret: $NEW_COOKIE_SECRET")

    echo "Keycloak client and user configuration complete via API."
else
    echo "Skipped Keycloak setup steps 4-7 as stack was already running."
fi # End of KEYCLOAK_SETUP_NEEDED conditional block

# ---------------------------------------------------------------
# SECTION B: APISIX SETUP
# ---------------------------------------------------------------
echo "SECTION B: SETTING UP APISIX"

# ---------------------------------------------------------------
# B1. Process templates and set up APISIX configuration files
# ---------------------------------------------------------------
echo "Step B1: Processing APISIX configuration templates..."

# Verify templates exist
if [ ! -f "apisix/conf/config.yaml.template" ]; then
    echo "Error: apisix/conf/config.yaml.template not found!"
    echo "Please create the template files first."
    exit 1
fi

if [ ! -f "apisix/conf/dashboard.yaml.template" ]; then
    echo "Error: apisix/conf/dashboard.yaml.template not found!"
    echo "Please create the template files first."
    exit 1
fi

# Generate secure keys for APISIX
APISIX_ADMIN_KEY=$(generate_secure_string)
APISIX_DASHBOARD_SECRET=$(generate_secure_string)
APISIX_DASHBOARD_PASSWORD=$(generate_secure_string)
APISIX_KEYRING_VALUE_1=$(generate_secure_string | cut -c1-16) # Truncate to 16 chars for keyring
APISIX_KEYRING_VALUE_2=$(generate_secure_string | cut -c1-16) # Truncate to 16 chars for keyring

# Store for final report
SENSITIVE_VALUES+=("APISIX Admin API Key: $APISIX_ADMIN_KEY")
SENSITIVE_VALUES+=("APISIX Dashboard JWT Secret: $APISIX_DASHBOARD_SECRET")
SENSITIVE_VALUES+=("APISIX Dashboard Admin Password: $APISIX_DASHBOARD_PASSWORD")
SENSITIVE_VALUES+=("APISIX Keyring Value 1: $APISIX_KEYRING_VALUE_1")
SENSITIVE_VALUES+=("APISIX Keyring Value 2: $APISIX_KEYRING_VALUE_2")

# Process the config.yaml template
prepare_config_from_template "apisix/conf/config.yaml.template"
replace_in_file "apisix/conf/config.yaml" "APISIX_ADMIN_KEY_PLACEHOLDER" "$APISIX_ADMIN_KEY" "APISIX Admin API Key"
replace_in_file "apisix/conf/config.yaml" "APISIX_KEYRING_VALUE_1_PLACEHOLDER" "$APISIX_KEYRING_VALUE_1" "APISIX Keyring Value 1"
replace_in_file "apisix/conf/config.yaml" "APISIX_KEYRING_VALUE_2_PLACEHOLDER" "$APISIX_KEYRING_VALUE_2" "APISIX Keyring Value 2"
echo "Processed config.yaml template with secure values"

# Process the dashboard.yaml template
prepare_config_from_template "apisix/conf/dashboard.yaml.template"
replace_in_file "apisix/conf/dashboard.yaml" "APISIX_DASHBOARD_SECRET_PLACEHOLDER" "$APISIX_DASHBOARD_SECRET" "APISIX Dashboard JWT Secret"
replace_in_file "apisix/conf/dashboard.yaml" "APISIX_DASHBOARD_PASSWORD_PLACEHOLDER" "$APISIX_DASHBOARD_PASSWORD" "APISIX Dashboard Admin Password"
echo "Processed dashboard.yaml template with secure secrets"

# Process nginx.conf template if it exists
if [ -f "apisix/conf/nginx.conf.template" ]; then
    prepare_config_from_template "apisix/conf/nginx.conf.template"
    echo "Processed nginx.conf template"
fi

# ---------------------------------------------------------------
# B2. Check APISIX stack and launch if not running
# ---------------------------------------------------------------
echo "Step B2: Checking and launching APISIX Docker stack..."
APISIX_SERVICE_NAME_IN_COMPOSE="apisix" # As defined in your docker-compose.yml

APISIX_SETUP_NEEDED=true
# Check if the APISIX service is running
if ${DOCKER_COMPOSE_CMD} -f "apisix/docker-compose.yml" ps -q ${APISIX_SERVICE_NAME_IN_COMPOSE} 2>/dev/null | grep -q .; then
    CONTAINER_ID=$(${DOCKER_COMPOSE_CMD} -f "apisix/docker-compose.yml" ps -q ${APISIX_SERVICE_NAME_IN_COMPOSE} 2>/dev/null)
    if [ -n "$CONTAINER_ID" ]; then
      if docker inspect -f '{{.State.Running}}' "$CONTAINER_ID" 2>/dev/null | grep -q "true"; then
        echo "APISIX service '${APISIX_SERVICE_NAME_IN_COMPOSE}' appears to be already running."
        APISIX_SETUP_NEEDED=false
      fi
    fi
fi

if [ "$APISIX_SETUP_NEEDED" = true ]; then
    echo "APISIX stack not found or not running. Proceeding with setup."
    
    # Ensure APISIX directory exists
    if [ ! -d "apisix" ]; then
        echo "Error: APISIX directory not found!"
        exit 1
    fi
    
    # Create a prometheus.yml file if it doesn't exist
    if [ ! -f "apisix/conf/prometheus.yml" ]; then
        echo "Creating default Prometheus configuration..."
        cat > "apisix/conf/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'apisix'
    static_configs:
      - targets: ['apisix:9091']
    metrics_path: '/apisix/prometheus/metrics'
EOF
    fi
    
    # Store current directory and cd into apisix dir
    ORIGINAL_DIR=$(pwd)
    cd "apisix" || { echo "Failed to cd into apisix directory"; exit 1; }
    
    # Ensure docker-compose.yml has network configuration
    echo "Ensuring APISIX docker-compose.yml has proper network configuration..."
    ensure_network_in_compose "docker-compose.yml" "apisix"
    
    echo "Launching Docker Compose for APISIX..."
    if ${DOCKER_COMPOSE_CMD} up -d; then
        echo "APISIX stack started successfully."
        echo "Waiting for APISIX to be fully operational (this might take a minute)..."
        RETRY_COUNT=0
        MAX_RETRIES=20 # ~2 minutes with 6-second interval
        SUCCESS=false
        until [ $RETRY_COUNT -ge $MAX_RETRIES ]; do
            RETRY_COUNT=$((RETRY_COUNT+1))
            # Check APISIX health by accessing a standard endpoint
            HTTP_STATUS_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "${APISIX_ADMIN_URL}/apisix/admin/routes" \
                 -H "X-API-KEY: ${APISIX_ADMIN_KEY}")
            if [ "$HTTP_STATUS_HEALTH" -eq 200 ] || [ "$HTTP_STATUS_HEALTH" -eq 401 ]; then
                # 401 is also acceptable as it means APISIX is up but auth failed
                # Which is expected if we have auth configured
                echo "APISIX is up and responding on its admin endpoint."
                SUCCESS=true
                break
            fi
            echo "APISIX not ready yet (attempt $RETRY_COUNT/$MAX_RETRIES, status $HTTP_STATUS_HEALTH). Waiting 6 seconds..."
            sleep 6
        done

        if [ "$SUCCESS" = false ]; then
            echo "APISIX did not become ready in time. Please check Docker logs."
            ${DOCKER_COMPOSE_CMD} logs ${APISIX_SERVICE_NAME_IN_COMPOSE}
            cd "$ORIGINAL_DIR"
            exit 1
        fi
    else
        echo "Failed to start APISIX stack. Check Docker Compose logs."
        ${DOCKER_COMPOSE_CMD} logs
        cd "$ORIGINAL_DIR"
        exit 1
    fi
    cd "$ORIGINAL_DIR" # Return to the original directory
    
    # Ensure the container is connected to the shared network
    echo "Ensuring APISIX container is connected to shared network..."
    APISIX_CONTAINER=$(docker ps --filter "name=apisix" --format "{{.ID}}" | head -n 1)
    if [ -n "$APISIX_CONTAINER" ]; then
        # Check if already connected
        if ! docker inspect "$APISIX_CONTAINER" | grep -q "\"$SHARED_NETWORK_NAME\""; then
            echo "Manually connecting APISIX container to shared network..."
            docker network connect $SHARED_NETWORK_NAME $APISIX_CONTAINER
            echo "APISIX container connected to $SHARED_NETWORK_NAME"
        else
            echo "APISIX container already connected to $SHARED_NETWORK_NAME"
        fi
    fi
    
    # ---------------------------------------------------------------
    # B3. Configure APISIX routes to Keycloak if needed
    # ---------------------------------------------------------------
    echo "Step B3: Configuring APISIX routes to Keycloak..."
    
    # Add a route in APISIX to proxy requests to Keycloak
    # This example creates a route that forwards all requests with prefix /auth to Keycloak
    
    # Create a route to proxy to Keycloak
    echo "Creating APISIX route to Keycloak..."
    ROUTE_ID="keycloak-route"
    ROUTE_CONFIG='{
      "uri": "/auth/*",
      "name": "keycloak-proxy",
      "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
      "upstream": {
        "type": "roundrobin",
        "nodes": {
          "keycloak:8080": 1
        }
      },
      "plugins": {
        "proxy-rewrite": {
          "regex_uri": ["^/auth/(.*)", "/$1"]
        }
      }
    }'
    
    # Send API request to create the route
    curl -i -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/${ROUTE_ID}" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
      -H "Content-Type: application/json" \
      -d "${ROUTE_CONFIG}"
    
    if [ $? -eq 0 ]; then
      echo "Successfully configured APISIX route to Keycloak."
    else
      echo "Warning: Failed to configure APISIX route to Keycloak. You may need to do this manually."
    fi
    
    echo "APISIX setup complete."
else
    echo "Skipped APISIX setup as stack was already running."
    
    # If we're using an existing APISIX installation, extract the admin key from config.yaml
    if [ -f "apisix/conf/config.yaml" ]; then
        EXISTING_ADMIN_KEY=$(grep -A 5 "admin_key:" "apisix/conf/config.yaml" | grep "key:" | head -n 1 | awk '{print $2}')
        if [ -n "$EXISTING_ADMIN_KEY" ]; then
            APISIX_ADMIN_KEY=$EXISTING_ADMIN_KEY
            SENSITIVE_VALUES+=("APISIX Admin API Key (existing): $APISIX_ADMIN_KEY")
        fi
    fi

    # Extract dashboard credentials if available
    if [ -f "apisix/conf/dashboard.yaml" ]; then
        EXISTING_DASHBOARD_SECRET=$(grep "secret:" "apisix/conf/dashboard.yaml" | head -n 1 | awk '{print $2}')
        if [ -n "$EXISTING_DASHBOARD_SECRET" ]; then
            SENSITIVE_VALUES+=("APISIX Dashboard JWT Secret (existing): $EXISTING_DASHBOARD_SECRET")
        fi
        
        EXISTING_DASHBOARD_PASSWORD=$(grep -A 3 "users:" "apisix/conf/dashboard.yaml" | grep "password:" | head -n 1 | awk '{print $2}')
        if [ -n "$EXISTING_DASHBOARD_PASSWORD" ]; then
            SENSITIVE_VALUES+=("APISIX Dashboard Admin Password (existing): $EXISTING_DASHBOARD_PASSWORD")
        fi
    fi
    
    # Ensure the container is connected to the shared network
    echo "Ensuring APISIX container is connected to shared network..."
    APISIX_CONTAINER=$(docker ps --filter "name=apisix" --format "{{.ID}}" | head -n 1)
    if [ -n "$APISIX_CONTAINER" ]; then
        # Check if already connected
        if ! docker inspect "$APISIX_CONTAINER" | grep -q "\"$SHARED_NETWORK_NAME\""; then
            echo "Manually connecting APISIX container to shared network..."
            docker network connect $SHARED_NETWORK_NAME $APISIX_CONTAINER
            echo "APISIX container connected to $SHARED_NETWORK_NAME"
        else
            echo "APISIX container already connected to $SHARED_NETWORK_NAME"
        fi
    fi
fi # End of APISIX_SETUP_NEEDED conditional block

# ---------------------------------------------------------------
# SECTION C: VIOLENTUTF PYTHON APP SETUP
# ---------------------------------------------------------------
echo "SECTION C: SETTING UP VIOLENTUTF PYTHON APP"

# ---------------------------------------------------------------
# 8. Check Python executable (python or python3)
# ---------------------------------------------------------------
echo "Step 8: Determining Python command..."
PYTHON_CMD="python3" # Default to python3
if ! command -v python3 &> /dev/null; then
    if command -v python &> /dev/null; then
        PY_VERSION_CHECK=$(python --version 2>&1 | awk '{print $2}')
        if [[ "$PY_VERSION_CHECK" == 3* ]]; then # Check if 'python' is Python 3
            PYTHON_CMD="python"
        else
            echo "Python 3 not found with 'python3' or 'python' command. Please install Python 3.9+."
            echo "You can install Python on macOS using 'brew install python3' or from python.org."
            exit 1
        fi
    else
        echo "Python 3 not found. Please install Python 3.9+."
        echo "You can install Python on macOS using 'brew install python3' or from python.org."
        exit 1
    fi
fi
echo "Using '$PYTHON_CMD' for Python operations."
# Further check for Python 3.9+
PY_FULL_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo $PY_FULL_VERSION | cut -d. -f1)
PY_MINOR=$(echo $PY_FULL_VERSION | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
    echo "Your Python version ($PYTHON_CMD is $PY_FULL_VERSION) is less than 3.9. Please upgrade."
    exit 1
fi
echo "Python version $PY_FULL_VERSION is sufficient."

# ---------------------------------------------------------------
# 9. Set up and run the ViolentUTF Python app
# ---------------------------------------------------------------
echo "Step 9: Setting up and running ViolentUTF Python app..."

# === START OF ORIGINAL SCRIPT (ADJUSTED) ===
echo "Ensuring pip is up to date for $PYTHON_CMD..."
$PYTHON_CMD -m ensurepip --upgrade 2>/dev/null
$PYTHON_CMD -m pip install --upgrade pip

VENV_DIR=".vitutf"
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment '$VENV_DIR' already exists. Skipping creation."
else
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "Created virtual environment in $VENV_DIR using $PYTHON_CMD."
fi

if [ ! -f ".gitignore" ]; then
    echo ".gitignore not found. Creating .gitignore."
    echo "$VENV_DIR" > .gitignore
else
    if ! grep -Fxq "$VENV_DIR" .gitignore; then
        echo "$VENV_DIR" >> .gitignore
        echo "Added '$VENV_DIR' to .gitignore."
    else
        echo "'$VENV_DIR' is already in .gitignore."
    fi
fi

source "$VENV_DIR/bin/activate"
echo "Activated virtual environment: $VENV_DIR"

REQUIREMENTS_PATH="violentutf/requirements.txt"
if [ ! -f "$REQUIREMENTS_PATH" ]; then
    # Fallback to root if not in violentutf subdir
    REQUIREMENTS_PATH="requirements.txt" 
fi

if [ -f "$REQUIREMENTS_PATH" ]; then
    echo "Installing packages from $REQUIREMENTS_PATH..."
    python -m pip cache purge # Good practice on macOS sometimes
    python -m pip install --upgrade pip
    python -m pip install -r "$REQUIREMENTS_PATH"
    echo "Package installation complete."
else
    echo "Warning: No requirements.txt found at violentutf/requirements.txt or ./requirements.txt. Skipping package installation."
fi

# ---------------------------------------------------------------
# 10. Update ViolentUTF config to use APISIX proxy if needed
# ---------------------------------------------------------------
echo "Step 10: Updating ViolentUTF config to use APISIX proxy if needed..."

# Check if we need to update the ViolentUTF config to use APISIX proxy
if [ -f "$VIOLENTUTF_ENV_FILE" ]; then
    # Add/update KEYCLOAK_URL_BASE to point to APISIX proxy if it exists
    if grep -q "^KEYCLOAK_URL_BASE" "$VIOLENTUTF_ENV_FILE"; then
        sed -i '' "s|^KEYCLOAK_URL_BASE=.*|KEYCLOAK_URL_BASE=http://localhost:9080/auth|" "$VIOLENTUTF_ENV_FILE"
    else
        echo "KEYCLOAK_URL_BASE=http://localhost:9080/auth" >> "$VIOLENTUTF_ENV_FILE"
    fi
    echo "Updated KEYCLOAK_URL_BASE in $VIOLENTUTF_ENV_FILE to use APISIX proxy."
fi

echo "ViolentUTF configuration updated for APISIX integration."

# ---------------------------------------------------------------
# 11. Test all components of the stacks
# ---------------------------------------------------------------
echo ""
echo "=========================================="
echo "TESTING ALL COMPONENTS"
echo "=========================================="
echo "Running comprehensive tests for Keycloak, APISIX, and their integration..."

TEST_RESULTS=()
TEST_FAILURES=0

# Function to run a test and record the result
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_exit_code="${3:-0}"
    
    echo "Testing: $test_name"
    
    # Capture both output and exit code
    local output
    output=$(eval "$test_command" 2>&1)
    local actual_exit_code=$?
    
    if [ $actual_exit_code -eq $expected_exit_code ]; then
        TEST_RESULTS+=("✅ PASS: $test_name")
        echo "  Result: PASS"
    else
        TEST_RESULTS+=("❌ FAIL: $test_name (Exit code: $actual_exit_code, Expected: $expected_exit_code)")
        echo "  Result: FAIL (Exit code: $actual_exit_code, Expected: $expected_exit_code)"
        echo "  Output: $output"
        TEST_FAILURES=$((TEST_FAILURES+1))
    fi
    echo ""
}

# 1. Test Keycloak is running and accessible
# run_test "Keycloak master realm" "code=$(curl -s -o /dev/null -w '%{http_code}' ${KEYCLOAK_SERVER_URL}/realms/master) && [[ $code -ge 200 && $code -lt 400 ]]"
# Skip this one because KeyCloak redirect mechanism. Passing of no 2 and other items should cover no 1.

# 2. Test Keycloak master realm is accessible
run_test "Keycloak master realm" "curl -s -o /dev/null -w '%{http_code}' ${KEYCLOAK_SERVER_URL}/realms/master | grep -q 200"

# 3. Test network connectivity between APISIX and Keycloak
run_test "APISIX to Keycloak network connectivity" "test_network_connectivity apisix keycloak 8080"

# Additional network diagnostics if the connectivity test fails
if [ $? -ne 0 ]; then
    echo "Performing additional network diagnostics..."
    
    # Show all networks and their containers
    echo "Docker Networks:"
    docker network ls
    
    # Check containers on the shared network
    echo "Containers on $SHARED_NETWORK_NAME:"
    docker network inspect $SHARED_NETWORK_NAME
    
    # Check if services can be resolved by DNS from host
    echo "DNS resolution of Keycloak from host:"
    docker run --rm --network=$SHARED_NETWORK_NAME alpine nslookup keycloak 2>/dev/null || echo "Failed to resolve keycloak"
    
    echo "DNS resolution of APISIX from host:"
    docker run --rm --network=$SHARED_NETWORK_NAME alpine nslookup apisix 2>/dev/null || echo "Failed to resolve apisix"
    
    # Try again to connect the containers to the shared network
    echo "Attempting to reconnect containers to the shared network..."
    
    KEYCLOAK_CONTAINER=$(docker ps --filter "name=keycloak" --format "{{.ID}}" | head -n 1)
    if [ -n "$KEYCLOAK_CONTAINER" ]; then
        if docker network disconnect $SHARED_NETWORK_NAME $KEYCLOAK_CONTAINER 2>/dev/null; then
            echo "Disconnected Keycloak container from $SHARED_NETWORK_NAME"
        fi
        docker network connect $SHARED_NETWORK_NAME $KEYCLOAK_CONTAINER || echo "Failed to reconnect Keycloak to network"
        echo "Reconnected Keycloak container to $SHARED_NETWORK_NAME"
    fi
    
    APISIX_CONTAINER=$(docker ps --filter "name=apisix" --format "{{.ID}}" | head -n 1)
    if [ -n "$APISIX_CONTAINER" ]; then
        if docker network disconnect $SHARED_NETWORK_NAME $APISIX_CONTAINER 2>/dev/null; then
            echo "Disconnected APISIX container from $SHARED_NETWORK_NAME"
        fi
        docker network connect $SHARED_NETWORK_NAME $APISIX_CONTAINER || echo "Failed to reconnect APISIX to network"
        echo "Reconnected APISIX container to $SHARED_NETWORK_NAME"
    fi
    
    # Try connectivity test one more time
    echo "Retrying connectivity test after network reconnection..."
    test_network_connectivity apisix keycloak 8080
fi

# 4. Test APISIX is running and accessible
run_test "APISIX main endpoint" "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL} | grep -q 404"
# Note: 404 is expected for root path as no routes are defined by default

# 5. Test APISIX admin API 
run_test "APISIX admin API" "curl -s -o /dev/null -w '%{http_code}' ${APISIX_ADMIN_URL}/apisix/admin/routes -H \"X-API-KEY: ${APISIX_ADMIN_KEY}\" | grep -q 200"

# 6. Test APISIX dashboard is accessible
run_test "APISIX dashboard" "curl -s -o /dev/null -w '%{http_code}' ${APISIX_DASHBOARD_URL} | grep -q 200"

# 7. Test APISIX-Keycloak integration - Test the route to Keycloak through APISIX
run_test "APISIX-Keycloak integration" "curl -s -o /dev/null -w '%{http_code}' ${APISIX_URL}/auth/realms/master | grep -q 200"

# 8. Test ViolentUTF environment variables
if [ -f "$VIOLENTUTF_ENV_FILE" ]; then
    run_test "ViolentUTF environment file" "grep -q KEYCLOAK_CLIENT_SECRET $VIOLENTUTF_ENV_FILE && grep -q KEYCLOAK_USERNAME $VIOLENTUTF_ENV_FILE && grep -q KEYCLOAK_PASSWORD $VIOLENTUTF_ENV_FILE"
else
    TEST_RESULTS+=("❌ FAIL: ViolentUTF environment file (File not found)")
    TEST_FAILURES=$((TEST_FAILURES+1))
fi

# 9. Test ViolentUTF secrets file
if [ -f "$VIOLENTUTF_SECRETS_FILE" ]; then
    run_test "ViolentUTF secrets file" "grep -q client_secret $VIOLENTUTF_SECRETS_FILE && grep -q cookie_secret $VIOLENTUTF_SECRETS_FILE"
else
    TEST_RESULTS+=("❌ FAIL: ViolentUTF secrets file (File not found)")
    TEST_FAILURES=$((TEST_FAILURES+1))
fi

# 10. Test Python environment and Streamlit installation
run_test "Python Streamlit installation" "which streamlit > /dev/null"

# Display test results
echo ""
echo "TEST RESULTS SUMMARY:"
echo "--------------------"
for result in "${TEST_RESULTS[@]}"; do
    echo "$result"
done
echo ""
echo "Total tests: ${#TEST_RESULTS[@]}"
echo "Passed: $((${#TEST_RESULTS[@]} - $TEST_FAILURES))"
echo "Failed: $TEST_FAILURES"
echo ""

if [ $TEST_FAILURES -gt 0 ]; then
    echo "⚠️  WARNING: Some tests failed. The application may not function correctly."
    echo "Please check the test results above and fix any issues before proceeding."
    echo ""
    
    # Ask user if they want to continue despite test failures
    read -p "Do you want to continue and launch the Streamlit app anyway? (y/n): " continue_choice
    if [[ ! $continue_choice =~ ^[Yy]$ ]]; then
        echo "Setup aborted by user after test failures."
        exit 1
    fi
    echo "Continuing despite test failures..."
else
    echo "✅ All tests passed! The system is properly configured."
fi
echo "=========================================="
echo ""

# ---------------------------------------------------------------
# 12. Display sensitive values report
# ---------------------------------------------------------------
echo ""
echo "=========================================="
echo "SENSITIVE VALUES GENERATED DURING SETUP"
echo "=========================================="
echo "IMPORTANT: Store these values securely. They're needed for administration."
echo ""
for value in "${SENSITIVE_VALUES[@]}"; do
    echo "$value"
done
echo ""
echo "=========================================="
echo ""

# ---------------------------------------------------------------
# 13. Launch the Streamlit app
# ---------------------------------------------------------------
echo "Step 13: Launching the Streamlit application..."
# Assuming Home.py is in the violentutf directory and scripts are run from project root
if [ -f "violentutf/Home.py" ]; then
    cd violentutf || { echo "Failed to cd into violentutf directory"; exit 1; }
    streamlit run Home.py
    cd ..
elif [ -f "Home.py" ]; then
    streamlit run Home.py
else
    echo "Error: Home.py not found in violentutf/ or current directory. Cannot start application."
    exit 1
fi

echo "Setup script finished."