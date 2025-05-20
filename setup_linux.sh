#!/usr/bin/env bash
# setup_linux.sh (API Version)

# --- Global Keycloak API Variables ---
KEYCLOAK_SERVER_URL="http://localhost:8080"
ADMIN_USER="admin"
ADMIN_PASS="admin" # From your docker-compose.yml
MASTER_REALM="master"
ADMIN_CLIENT_ID="admin-cli"
ACCESS_TOKEN="" # Will be populated by get_keycloak_admin_token

# Function to generate a random secure string
generate_secure_string() {
    openssl rand -base64 32 | tr -d '\n' | tr -d '\r' | tr -d '/' | tr -d '+' | tr -d '=' | cut -c1-32
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
# Returns the HTTP status code in global variable API_CALL_STATUS and response body in API_CALL_RESPONSE
make_api_call() {
    local method="$1"
    local endpoint_path="$2"
    local data_arg="$3"
    local full_url="${KEYCLOAK_SERVER_URL}/admin${endpoint_path}" # Note: /admin path
    local response_output response_file http_code

    response_file=$(mktemp) 

    local curl_opts=(-s -w "%{http_code}" -o "${response_file}" \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -X "${method}")

    if [ -n "$data_arg" ]; then
        curl_opts+=(-H "Content-Type: application/json")
        if [ -f "$data_arg" ]; then 
            curl_opts+=(--data-binary "@${data_arg}")
        else 
            curl_opts+=(--data-binary "${data_arg}")
        fi
    fi
    
    echo "Executing API call: ${method} ${full_url}"
    http_code=$(curl "${curl_opts[@]}" "${full_url}")

    API_CALL_RESPONSE=$(cat "${response_file}")
    rm -f "${response_file}"
    API_CALL_STATUS=$http_code
}


echo "Starting ViolentUTF Nightly and Keycloak Setup for Linux (API Version)..."

# ---------------------------------------------------------------
# 1. Check Docker and Docker Compose
# ---------------------------------------------------------------
echo "Step 1: Checking Docker and Docker Compose..."
if ! command -v docker &> /dev/null; then
    echo "Docker could not be found. Please install Docker."
    echo "Visit [https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/) for installation instructions."
    exit 1
fi

DOCKER_COMPOSE_CMD="docker compose"
if ! docker compose version &> /dev/null; then
    echo "Docker Compose (V2 CLI plugin) could not be found. Trying older 'docker-compose'..."
    if ! command -v docker-compose &> /dev/null; then
        echo "Neither 'docker compose' nor 'docker-compose' found."
        echo "Ensure you have Docker Engine with the Compose plugin installed and running."
        exit 1
    else
        DOCKER_COMPOSE_CMD="docker-compose"
        echo "Found older 'docker-compose'. Will use that."
    fi
fi
echo "Using Docker Compose command: $DOCKER_COMPOSE_CMD"


if ! docker info &> /dev/null || ! docker ps &> /dev/null; then
    echo "Docker daemon is not running or current user cannot connect to it."
    echo "Please start Docker service and ensure you have permissions (e.g., add user to 'docker' group)."
    exit 1
fi
echo "Docker and Docker Compose check passed."

# ---------------------------------------------------------------
# 2. Copy and populate keycloak/.env
# ---------------------------------------------------------------
echo "Step 2: Setting up keycloak/.env..."
KEYCLOAK_ENV_DIR="keycloak"
KEYCLOAK_ENV_SAMPLE="${KEYCLOAK_ENV_DIR}/env.sample"
KEYCLOAK_ENV_FILE="${KEYCLOAK_ENV_DIR}/.env"

if [ ! -f "$KEYCLOAK_ENV_SAMPLE" ]; then
    echo "Error: $KEYCLOAK_ENV_SAMPLE not found!"
    mkdir -p "$KEYCLOAK_ENV_DIR"
    echo "POSTGRES_PASSWORD=replace_key" > "$KEYCLOAK_ENV_SAMPLE"
    echo "Created a dummy ${KEYCLOAK_ENV_SAMPLE}. Please review it."
fi

cp "$KEYCLOAK_ENV_SAMPLE" "$KEYCLOAK_ENV_FILE"
echo "Copied $KEYCLOAK_ENV_SAMPLE to $KEYCLOAK_ENV_FILE."

TEMP_FILE_ENV_REPLACE=$(mktemp)
cp "$KEYCLOAK_ENV_FILE" "$TEMP_FILE_ENV_REPLACE"
COUNT_REPLACE_KEY=$(grep -o "replace_key" "$TEMP_FILE_ENV_REPLACE" | wc -l)
for (( i=1; i<=$COUNT_REPLACE_KEY; i++ )); do
    SECURE_VAL=$(generate_secure_string)
    awk -v val="$SECURE_VAL" '/replace_key/ && !done {sub(/replace_key/, val); done=1} 1' "$TEMP_FILE_ENV_REPLACE" > "$KEYCLOAK_ENV_FILE"
    cp "$KEYCLOAK_ENV_FILE" "$TEMP_FILE_ENV_REPLACE" 
done
rm "$TEMP_FILE_ENV_REPLACE"
echo "Replaced 'replace_key' placeholders in $KEYCLOAK_ENV_FILE with secure random strings."
echo "Keycloak .env file generated:"
cat "$KEYCLOAK_ENV_FILE"

# ---------------------------------------------------------------
# 3. Check Keycloak stack and launch if not running
# ---------------------------------------------------------------
echo "Step 3: Checking and launching Keycloak Docker stack..."
KEYCLOAK_SERVICE_NAME_IN_COMPOSE="keycloak"

KEYCLOAK_SETUP_NEEDED=true
if ${DOCKER_COMPOSE_CMD} -f "${KEYCLOAK_ENV_DIR}/docker-compose.yml" ps -q ${KEYCLOAK_SERVICE_NAME_IN_COMPOSE} 2>/dev/null | grep -q .; then
    CONTAINER_ID=$(${DOCKER_COMPOSE_CMD} -f "${KEYCLOAK_ENV_DIR}/docker-compose.yml" ps -q ${KEYCLOAK_SERVICE_NAME_IN_COMPOSE} 2>/dev/null)
    if [ -n "$CONTAINER_ID" ]; then
      if docker inspect -f '{{.State.Running}}' "$CONTAINER_ID" 2>/dev/null | grep -q "true"; then
        echo "Keycloak service '${KEYCLOAK_SERVICE_NAME_IN_COMPOSE}' appears to be already running. Skipping to step 8."
        KEYCLOAK_SETUP_NEEDED=false
      fi
    fi
fi

if [ "$KEYCLOAK_SETUP_NEEDED" = true ]; then
    echo "Keycloak stack not found or not running. Proceeding with setup."
    ORIGINAL_DIR=$(pwd)
    cd "$KEYCLOAK_ENV_DIR" || { echo "Failed to cd into $KEYCLOAK_ENV_DIR"; exit 1; }
    
    echo "Launching Docker Compose for Keycloak..."
    if ${DOCKER_COMPOSE_CMD} up -d; then
        echo "Keycloak stack started successfully."
        echo "Waiting for Keycloak to be fully operational..."
        RETRY_COUNT=0
        MAX_RETRIES=30 
        SUCCESS=false
        until [ $RETRY_COUNT -ge $MAX_RETRIES ]; do
            RETRY_COUNT=$((RETRY_COUNT+1))
            HTTP_STATUS_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "${KEYCLOAK_SERVER_URL}/realms/master")
            if [ "$HTTP_STATUS_HEALTH" -eq 200 ]; then
                echo "Keycloak is up and responding."
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
    cd "$ORIGINAL_DIR" 
fi


if [ "$KEYCLOAK_SETUP_NEEDED" = true ]; then
    get_keycloak_admin_token

    # ---------------------------------------------------------------
    # 4. Import realm-export.json to Keycloak via API
    # ---------------------------------------------------------------
    echo "Step 4: Importing Keycloak realm via API..."
    REALM_EXPORT_FILE="${KEYCLOAK_ENV_DIR}/realm-export.json"

    if [ ! -f "$REALM_EXPORT_FILE" ]; then
        echo "Error: $REALM_EXPORT_FILE not found!"
        exit 1
    fi
    
    TARGET_REALM_NAME=$(jq -r .realm "$REALM_EXPORT_FILE")
    if [ -z "$TARGET_REALM_NAME" ] || [ "$TARGET_REALM_NAME" == "null" ]; then
        echo "Error: Could not extract realm name from $REALM_EXPORT_FILE"
        exit 1
    fi
    echo "Target realm name: $TARGET_REALM_NAME"

    make_api_call "GET" "/realms/${TARGET_REALM_NAME}"
    if [ "$API_CALL_STATUS" -eq 200 ]; then
        echo "Realm '$TARGET_REALM_NAME' already exists. Deleting and re-importing."
        make_api_call "DELETE" "/realms/${TARGET_REALM_NAME}"
        if [ "$API_CALL_STATUS" -ne 204 ]; then 
            echo "Failed to delete existing realm '$TARGET_REALM_NAME'. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
            exit 1
        fi
        echo "Existing realm '$TARGET_REALM_NAME' deleted."
    elif [ "$API_CALL_STATUS" -ne 404 ]; then 
        echo "Error checking for realm '$TARGET_REALM_NAME'. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi

    echo "Importing realm '$TARGET_REALM_NAME' from $REALM_EXPORT_FILE via API..."
    make_api_call "POST" "/realms" "$REALM_EXPORT_FILE"
    if [ "$API_CALL_STATUS" -eq 201 ]; then 
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
    VUTF_REALM_NAME="$TARGET_REALM_NAME" 
    VUTF_CLIENT_ID_TO_CONFIGURE="violentutf" 

    make_api_call "GET" "/realms/${VUTF_REALM_NAME}/clients?clientId=${VUTF_CLIENT_ID_TO_CONFIGURE}"
    if [ "$API_CALL_STATUS" -ne 200 ]; then
        echo "Error: Could not get client info for '${VUTF_CLIENT_ID_TO_CONFIGURE}'. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi
    KC_CLIENT_UUID=$(echo "$API_CALL_RESPONSE" | jq -r '.[0].id') 
    if [ -z "$KC_CLIENT_UUID" ] || [ "$KC_CLIENT_UUID" == "null" ]; then
        echo "Error: Client '${VUTF_CLIENT_ID_TO_CONFIGURE}' not found in realm '${VUTF_REALM_NAME}' via API."
        exit 1
    fi
    echo "Found client '${VUTF_CLIENT_ID_TO_CONFIGURE}' with UUID '${KC_CLIENT_UUID}'."

    echo "Regenerating client secret for '${VUTF_CLIENT_ID_TO_CONFIGURE}' via API..."
    make_api_call "POST" "/realms/${VUTF_REALM_NAME}/clients/${KC_CLIENT_UUID}/client-secret"
    if [ "$API_CALL_STATUS" -ne 200 ]; then 
        echo "Error: Failed to regenerate client secret via API. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi
    NEW_CLIENT_SECRET=$(echo "$API_CALL_RESPONSE" | jq -r .value)
    if [ -z "$NEW_CLIENT_SECRET" ] || [ "$NEW_CLIENT_SECRET" == "null" ]; then
        echo "Error: Failed to parse new client secret from API response."
        exit 1
    fi
    echo "New client secret generated via API."

    sed -i "s|^KEYCLOAK_CLIENT_SECRET=.*|KEYCLOAK_CLIENT_SECRET=${NEW_CLIENT_SECRET}|" "$VIOLENTUTF_ENV_FILE"
    escaped_new_client_secret=$(printf '%s\n' "$NEW_CLIENT_SECRET" | sed 's/[\&/]/\\&/g; s/"/\\"/g') 
    sed -i "s|^client_secret =.*|client_secret = \"${escaped_new_client_secret}\"|" "$VIOLENTUTF_SECRETS_FILE"
    echo "Updated KEYCLOAK_CLIENT_SECRET in $VIOLENTUTF_ENV_FILE and client_secret in $VIOLENTUTF_SECRETS_FILE."

    KEYCLOAK_APP_USERNAME=$(grep "^KEYCLOAK_USERNAME=" "$VIOLENTUTF_ENV_FILE" | cut -d'=' -f2-)
    if [ -z "$KEYCLOAK_APP_USERNAME" ]; then
        KEYCLOAK_APP_USERNAME="testuser" 
        echo "KEYCLOAK_USERNAME=${KEYCLOAK_APP_USERNAME}" >> "$VIOLENTUTF_ENV_FILE" 
    fi
    echo "Using KEYCLOAK_USERNAME: $KEYCLOAK_APP_USERNAME"

    make_api_call "GET" "/realms/${VUTF_REALM_NAME}/users?username=${KEYCLOAK_APP_USERNAME}"
    if [ "$API_CALL_STATUS" -ne 200 ]; then
        echo "Error checking for user '${KEYCLOAK_APP_USERNAME}'. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi
    
    USER_EXISTS_ID=$(echo "$API_CALL_RESPONSE" | jq -r '.[0].id') 
    
    if [ -z "$USER_EXISTS_ID" ] || [ "$USER_EXISTS_ID" == "null" ]; then
        echo "User '${KEYCLOAK_APP_USERNAME}' not found. Creating user via API..."
        USER_CREATE_PAYLOAD="{\"username\":\"${KEYCLOAK_APP_USERNAME}\", \"enabled\":true}"
        make_api_call "POST" "/realms/${VUTF_REALM_NAME}/users" "${USER_CREATE_PAYLOAD}"
        if [ "$API_CALL_STATUS" -ne 201 ]; then
            echo "Error: Failed to create user '${KEYCLOAK_APP_USERNAME}' via API. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
            exit 1
        fi
        make_api_call "GET" "/realms/${VUTF_REALM_NAME}/users?username=${KEYCLOAK_APP_USERNAME}"
        USER_EXISTS_ID=$(echo "$API_CALL_RESPONSE" | jq -r '.[0].id')
        if [ -z "$USER_EXISTS_ID" ] || [ "$USER_EXISTS_ID" == "null" ]; then
            echo "Error: Failed to retrieve ID for newly created user '${KEYCLOAK_APP_USERNAME}'."
            exit 1
        fi
        echo "User '${KEYCLOAK_APP_USERNAME}' created with ID '${USER_EXISTS_ID}'."
    else
        echo "User '${KEYCLOAK_APP_USERNAME}' already exists with ID '${USER_EXISTS_ID}'."
    fi

    echo "Setting a new password for user '${KEYCLOAK_APP_USERNAME}' via API..."
    NEW_USER_PASSWORD=$(generate_secure_string)
    PASSWORD_RESET_PAYLOAD="{\"type\":\"password\", \"value\":\"${NEW_USER_PASSWORD}\", \"temporary\":false}"
    make_api_call "PUT" "/realms/${VUTF_REALM_NAME}/users/${USER_EXISTS_ID}/reset-password" "${PASSWORD_RESET_PAYLOAD}"
    if [ "$API_CALL_STATUS" -ne 204 ]; then 
        echo "Error: Failed to set password for user '${KEYCLOAK_APP_USERNAME}' via API. Status: $API_CALL_STATUS, Response: $API_CALL_RESPONSE"
        exit 1
    fi
    echo "Password for user '${KEYCLOAK_APP_USERNAME}' has been set via API."

    sed -i "s|^KEYCLOAK_PASSWORD=.*|KEYCLOAK_PASSWORD=${NEW_USER_PASSWORD}|" "$VIOLENTUTF_ENV_FILE"
    echo "Updated KEYCLOAK_PASSWORD in $VIOLENTUTF_ENV_FILE."

    # ---------------------------------------------------------------
    # 7. Generate secure secrets for PYRIT_DB_SALT and cookie_secret
    # ---------------------------------------------------------------
    echo "Step 7: Generating other secure secrets..."
    NEW_PYRIT_SALT=$(generate_secure_string)
    NEW_COOKIE_SECRET=$(generate_secure_string)

    sed -i "s|^PYRIT_DB_SALT=.*|PYRIT_DB_SALT=${NEW_PYRIT_SALT}|" "$VIOLENTUTF_ENV_FILE"
    escaped_new_cookie_secret=$(printf '%s\n' "$NEW_COOKIE_SECRET" | sed 's/[\&/]/\\&/g; s/"/\\"/g')
    sed -i "s|^cookie_secret =.*|cookie_secret = \"${escaped_new_cookie_secret}\"|" "$VIOLENTUTF_SECRETS_FILE"
    echo "Updated PYRIT_DB_SALT in $VIOLENTUTF_ENV_FILE and cookie_secret in $VIOLENTUTF_SECRETS_FILE."

    echo "Keycloak client and user configuration complete via API."
else
    echo "Skipped Keycloak setup steps 4-7 as stack was already running."
fi 

# ---------------------------------------------------------------
# 8. Check Python executable (python or python3)
# ---------------------------------------------------------------
echo "Step 8: Determining Python command..."
PYTHON_CMD="python3" 
if ! command -v python3 &> /dev/null; then
    if command -v python &> /dev/null; then
        PY_VERSION_CHECK=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
        if [[ "$PY_VERSION_CHECK" == 3* ]]; then 
            PYTHON_CMD="python"
        else
            echo "Python 3 not found with 'python3' or 'python' command. Please install Python 3.9+."
            exit 1
        fi
    else
        echo "Python 3 not found. Please install Python 3.9+."
        exit 1
    fi
fi
echo "Using '$PYTHON_CMD' for Python operations."

PY_FULL_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo $PY_FULL_VERSION | cut -d. -f1)
PY_MINOR=$(echo $PY_FULL_VERSION | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
    echo "Your system Python ($PYTHON_CMD version $PY_FULL_VERSION) is less than 3.9."
    echo "Please ensure Python 3.9+ is available and correctly identified by '$PYTHON_CMD'."
    exit 1
fi
echo "Python version $PY_FULL_VERSION is sufficient."

# ---------------------------------------------------------------
# 9. Proceed with the rest of the existing script
# ---------------------------------------------------------------
echo "Step 9: Proceeding with existing ViolentUTF Python setup..."

# === START OF ORIGINAL SCRIPT (ADJUSTED) ===
sudo apt-get update > /dev/null # Suppress output for apt-get update
sudo apt-get install -y python3-pip python3-venv > /dev/null # Suppress output
$PYTHON_CMD -m pip install --upgrade pip > /dev/null # Suppress output

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
    REQUIREMENTS_PATH="requirements.txt" 
fi

if [ -f "$REQUIREMENTS_PATH" ]; then
    echo "Installing packages from $REQUIREMENTS_PATH..."
    python -m pip install --upgrade pip > /dev/null
    python -m pip install -r "$REQUIREMENTS_PATH"
    echo "Package installation complete."
else
    echo "Warning: No requirements.txt found at violentutf/requirements.txt or ./requirements.txt. Skipping package installation."
fi

echo "Launching the Streamlit application..."
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