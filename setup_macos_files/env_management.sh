#!/usr/bin/env bash
# env_management.sh - Environment file creation, backup, and restoration

# Function to create AI tokens template
create_ai_tokens_template() {
    if [ ! -f "$AI_TOKENS_FILE" ]; then
        log_detail "Creating AI tokens configuration file: $AI_TOKENS_FILE"
        cat > "$AI_TOKENS_FILE" << 'EOF'
# AI Provider Tokens and Settings
# Set to true/false to enable/disable providers
# Add your actual API keys replacing the placeholder values

# OpenAI Configuration
OPENAI_ENABLED=false
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic Configuration  
ANTHROPIC_ENABLED=false
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Ollama Configuration (local, no API key needed)
OLLAMA_ENABLED=true
OLLAMA_ENDPOINT=http://localhost:11434/v1/chat/completions

# Open WebUI Configuration
OPEN_WEBUI_ENABLED=false
OPEN_WEBUI_ENDPOINT=http://localhost:3000/ollama/v1/chat/completions
OPEN_WEBUI_API_KEY=your_open_webui_api_key_here

# OpenAPI Provider Configuration
# Support for any OpenAPI-compliant API (including GSAi, custom APIs, etc.)
OPENAPI_ENABLED=false

# OpenAPI Provider 1 - Example: GSAi API (Local Development)
OPENAPI_1_ENABLED=false
OPENAPI_1_ID=gsai-api-local
OPENAPI_1_NAME="GSAi API Local"
OPENAPI_1_BASE_URL=https://localhost
OPENAPI_1_SPEC_PATH=/openapi.json
OPENAPI_1_AUTH_TYPE=bearer
OPENAPI_1_AUTH_TOKEN=your_gsai_bearer_token_here
OPENAPI_1_CUSTOM_HEADERS=""

# OpenAPI Provider 2 - Example: Custom API
OPENAPI_2_ENABLED=false
OPENAPI_2_ID=custom-api-1
OPENAPI_2_NAME="Custom API Provider 1"
OPENAPI_2_BASE_URL=https://api.example.com
OPENAPI_2_SPEC_PATH=/openapi.json
OPENAPI_2_AUTH_TYPE=api_key
OPENAPI_2_AUTH_TOKEN=your_api_key_here
OPENAPI_2_CUSTOM_HEADERS=""

# OpenAPI Provider 3 - Example: Another Custom API
OPENAPI_3_ENABLED=false
OPENAPI_3_ID=custom-api-2
OPENAPI_3_NAME="Custom API Provider 2"
OPENAPI_3_BASE_URL=https://api.another-example.com:8080
OPENAPI_3_SPEC_PATH=/v1/openapi.json
OPENAPI_3_AUTH_TYPE=basic
OPENAPI_3_AUTH_TOKEN=base64_encoded_credentials_here
OPENAPI_3_CUSTOM_HEADERS=""

# Available AUTH_TYPE values:
# - bearer: Uses Authorization: Bearer {token}
# - api_key: Uses X-API-Key: {token}
# - basic: Uses Authorization: Basic {token} (token should be base64 encoded)

# Routes will be created at:
# - Chat: http://localhost:9080/ai/{PROVIDER_ID}/chat/completions
# - Models: http://localhost:9080/ai/{PROVIDER_ID}/models
# - Target: {BASE_URL}/api/v1/chat/completions and {BASE_URL}/api/v1/models
EOF
        log_success "Created $AI_TOKENS_FILE template"
        log_detail "Please edit $AI_TOKENS_FILE to add your actual API keys"
    else
        log_detail "AI tokens file already exists: $AI_TOKENS_FILE"
    fi
}

# Function to load AI tokens from .env file
load_ai_tokens() {
    if [ -f "$AI_TOKENS_FILE" ]; then
        log_debug "Loading AI tokens from $AI_TOKENS_FILE..."
        set -a  # automatically export all variables
        source "$AI_TOKENS_FILE"
        set +a  # turn off automatic export
        if [ -z "$AI_TOKENS_LOADED" ]; then
            log_debug "AI tokens loaded"
            export AI_TOKENS_LOADED=1
        fi
        return 0
    else
        log_warn "AI tokens file not found: $AI_TOKENS_FILE"
        create_ai_tokens_template
        return 1
    fi
}

# Function to update FastAPI .env with AI provider flags
update_fastapi_env() {
    local fastapi_env_file="violentutf_api/fastapi_app/.env"
    
    log_detail "Updating FastAPI environment with AI provider flags and tokens..."
    
    # Load AI tokens first
    load_ai_tokens
    
    if [ ! -f "$fastapi_env_file" ]; then
        log_debug "Creating FastAPI .env file..."
        touch "$fastapi_env_file"
    fi
    
    # Update provider flags
    local providers=("OPENAI" "ANTHROPIC" "OLLAMA" "OPEN_WEBUI" "OPENAPI")
    
    for provider in "${providers[@]}"; do
        local enabled_var="${provider}_ENABLED"
        local enabled_value="${!enabled_var:-false}"
        
        # Update or add the provider flag
        if grep -q "^${enabled_var}=" "$fastapi_env_file"; then
            sed -i '' "s/^${enabled_var}=.*/${enabled_var}=${enabled_value}/" "$fastapi_env_file"
        else
            echo "${enabled_var}=${enabled_value}" >> "$fastapi_env_file"
        fi
    done
    
    # Update API keys from ai-tokens.env
    # Note: Always update API keys if they exist, regardless of enabled status
    # This ensures keys are available when providers are enabled later
    if [ -n "$OPENAI_API_KEY" ] && [ "$OPENAI_API_KEY" != "your_openai_api_key_here" ]; then
        if grep -q "^OPENAI_API_KEY=" "$fastapi_env_file"; then
            sed -i '' "s/^OPENAI_API_KEY=.*/OPENAI_API_KEY=${OPENAI_API_KEY}/" "$fastapi_env_file"
        else
            echo "OPENAI_API_KEY=${OPENAI_API_KEY}" >> "$fastapi_env_file"
        fi
        log_detail "Added OpenAI API key to FastAPI environment"
    fi
    
    if [ -n "$ANTHROPIC_API_KEY" ] && [ "$ANTHROPIC_API_KEY" != "your_anthropic_api_key_here" ]; then
        if grep -q "^ANTHROPIC_API_KEY=" "$fastapi_env_file"; then
            sed -i '' "s/^ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}/" "$fastapi_env_file"
        else
            echo "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}" >> "$fastapi_env_file"
        fi
        log_detail "Added Anthropic API key to FastAPI environment"
    fi
    
    log_success "FastAPI environment updated with provider flags and API keys"
}

# Function to backup user configurations
backup_user_configs() {
    log_detail "Backing up user configurations..."
    
    # Create backup directory
    mkdir -p "/tmp/vutf_backup"
    
    # Backup AI tokens (user's API keys)
    [ -f "$AI_TOKENS_FILE" ] && cp "$AI_TOKENS_FILE" "/tmp/vutf_backup/"
    
    # Backup any custom APISIX routes
    [ -f "apisix/conf/custom_routes.yml" ] && cp "apisix/conf/custom_routes.yml" "/tmp/vutf_backup/"
    
    # Backup user application data preferences
    if [ -d "violentutf/app_data" ]; then
        tar -czf "/tmp/vutf_backup/app_data_backup.tar.gz" -C violentutf app_data 2>/dev/null || true
    fi
    
    log_debug "User configurations backed up to /tmp/vutf_backup"
}

# Function to restore user configurations
restore_user_configs() {
    echo "Restoring user configurations..."
    
    if [ -d "/tmp/vutf_backup" ]; then
        # Restore AI tokens
        [ -f "/tmp/vutf_backup/$AI_TOKENS_FILE" ] && cp "/tmp/vutf_backup/$AI_TOKENS_FILE" .
        
        # Restore custom routes
        [ -f "/tmp/vutf_backup/custom_routes.yml" ] && cp "/tmp/vutf_backup/custom_routes.yml" "apisix/conf/"
        
        # Restore user application data if it was backed up
        if [ -f "/tmp/vutf_backup/app_data_backup.tar.gz" ]; then
            mkdir -p violentutf
            tar -xzf "/tmp/vutf_backup/app_data_backup.tar.gz" -C violentutf 2>/dev/null || true
        fi
        
        rm -rf "/tmp/vutf_backup"
        echo "✅ User configurations restored"
    else
        echo "No backup directory found to restore from"
    fi
}

# Function to create all environment files
create_env_files() {
    echo "Creating environment files for all services..."
    
    # Create AI tokens template if needed
    create_ai_tokens_template
    
    # Create Keycloak .env
    create_keycloak_env
    
    # Create APISIX .env
    create_apisix_env
    
    # Create ViolentUTF .env
    create_violentutf_env
    
    # Create FastAPI .env
    create_fastapi_env
    
    echo "✅ All environment files created"
}

# Helper function to create Keycloak environment file
create_keycloak_env() {
    local env_file="keycloak/.env"
    
    if [ ! -f "$env_file" ]; then
        echo "Creating Keycloak environment file..."
        local postgres_password=$(generate_random_string 32)
        local keycloak_admin_password=$(generate_random_string 16)
        
        cat > "$env_file" << EOF
# PostgreSQL password for Keycloak database
POSTGRES_PASSWORD=${postgres_password}

# Keycloak admin credentials (auto-generated, save these!)
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=${keycloak_admin_password}
EOF
        echo "✅ Created $env_file"
        echo "⚠️  IMPORTANT: Save the Keycloak admin password: ${keycloak_admin_password}"
    else
        echo "Keycloak .env already exists: $env_file (preserving existing credentials)"
    fi
}

# Helper function to create APISIX environment file
create_apisix_env() {
    local env_file="apisix/.env"
    
    if [ ! -f "$env_file" ]; then
        echo "Creating APISIX environment file..."
        local admin_key=$(generate_random_string 32)
        
        cat > "$env_file" << EOF
# APISIX Configuration
APISIX_ADMIN_KEY=${admin_key}
EOF
        echo "✅ Created $env_file"
    else
        echo "APISIX .env already exists: $env_file"
    fi
}

# Helper function to create ViolentUTF environment file
create_violentutf_env() {
    local env_file="violentutf/.env"
    
    if [ ! -f "$env_file" ]; then
        echo "Creating ViolentUTF environment file..."
        local client_secret=$(generate_random_string 32)
        local user_password=$(generate_random_string 32)
        local apisix_secret=$(generate_random_string 32)
        local pyrit_salt=$(generate_random_string 32)
        local jwt_secret=$(generate_random_string 32)
        local api_key=$(generate_random_string 32)
        
        cat > "$env_file" << EOF
KEYCLOAK_URL=http://localhost:8080/
KEYCLOAK_REALM=ViolentUTF
KEYCLOAK_CLIENT_ID=violentutf
KEYCLOAK_CLIENT_SECRET=${client_secret}
KEYCLOAK_USERNAME=violentutf.web
KEYCLOAK_PASSWORD=${user_password}
KEYCLOAK_APISIX_CLIENT_ID=apisix
KEYCLOAK_APISIX_CLIENT_SECRET=${apisix_secret}
OPENAI_CHAT_DEPLOYMENT='OpenAI API'
OPENAI_CHAT_ENDPOINT=https://api.openai.com/v1/responses
OPENAI_CHAT_KEY=***
PYRIT_DB_SALT=${pyrit_salt}
JWT_SECRET_KEY=${jwt_secret}
VIOLENTUTF_API_KEY=${api_key}
VIOLENTUTF_API_URL=http://localhost:9080/api
KEYCLOAK_URL_BASE=http://localhost:9080/auth
AI_PROXY_BASE_URL=http://localhost:9080/ai
EOF
        echo "✅ Created $env_file"
    else
        echo "ViolentUTF .env already exists: $env_file"
    fi
}

# Helper function to create FastAPI environment file
create_fastapi_env() {
    local env_file="violentutf_api/fastapi_app/.env"
    
    if [ ! -f "$env_file" ]; then
        echo "Creating FastAPI environment file..."
        local jwt_secret=$(generate_random_string 32)
        local api_key=$(generate_random_string 32)
        
        cat > "$env_file" << EOF
# JWT Configuration
JWT_SECRET_KEY=${jwt_secret}
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# API Configuration
VIOLENTUTF_API_KEY=${api_key}
VIOLENTUTF_API_URL=http://localhost:9080

# Keycloak Configuration
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=ViolentUTF
KEYCLOAK_CLIENT_ID=violentutf

# Database Configuration
PYRIT_DB_SALT=$(generate_random_string 32)

# Provider Flags (will be updated by update_fastapi_env)
OPENAI_ENABLED=false
ANTHROPIC_ENABLED=false
OLLAMA_ENABLED=true
OPEN_WEBUI_ENABLED=false
OPENAPI_ENABLED=false
EOF
        echo "✅ Created $env_file"
    else
        echo "FastAPI .env already exists: $env_file"
    fi
}

# Function to generate all environment files (CRITICAL: After secrets are generated)
generate_all_env_files() {
    log_detail "Creating configuration files..."
    
    # Ensure secrets are available
    if [ -z "$KEYCLOAK_POSTGRES_PASSWORD" ]; then
        echo "❌ Error: Secrets not generated! Must call generate_all_secrets first."
        return 1
    fi
    
    # Create Keycloak .env
    log_detail "Creating Keycloak configuration..."
    mkdir -p keycloak
    cat > keycloak/.env <<EOF
POSTGRES_PASSWORD=$KEYCLOAK_POSTGRES_PASSWORD
KEYCLOAK_ADMIN_USERNAME=$KEYCLOAK_ADMIN_USERNAME
KEYCLOAK_ADMIN_PASSWORD=$KEYCLOAK_ADMIN_PASSWORD
EOF
    echo "✅ Created keycloak/.env"
    
    # Create APISIX configurations
    log_detail "Creating APISIX configurations..."
    mkdir -p apisix/conf
    
    # Critical: Remove any directories that should be files
    for file in config.yaml dashboard.yaml prometheus.yml; do
        if [ -d "apisix/conf/$file" ]; then
            echo "⚠️  Removing incorrectly created directory: apisix/conf/$file"
            rm -rf "apisix/conf/$file"
        fi
    done
    
    # Process config.yaml template if it exists
    if [ -f "apisix/conf/config.yaml.template" ]; then
        prepare_config_from_template "apisix/conf/config.yaml.template"
        
        # Verify it was created as a file, not a directory
        if [ -f "apisix/conf/config.yaml" ]; then
            replace_in_file "apisix/conf/config.yaml" "APISIX_ADMIN_KEY_PLACEHOLDER" "$APISIX_ADMIN_KEY" "APISIX Admin API Key"
            replace_in_file "apisix/conf/config.yaml" "APISIX_KEYRING_VALUE_1_PLACEHOLDER" "$APISIX_KEYRING_VALUE_1" "APISIX Keyring Value 1"
            replace_in_file "apisix/conf/config.yaml" "APISIX_KEYRING_VALUE_2_PLACEHOLDER" "$APISIX_KEYRING_VALUE_2" "APISIX Keyring Value 2"
            echo "✅ Created apisix/conf/config.yaml"
        else
            echo "❌ Failed to create config.yaml as a file"
        fi
    fi
    
    # Process dashboard.yaml template if it exists
    if [ -f "apisix/conf/dashboard.yaml.template" ]; then
        prepare_config_from_template "apisix/conf/dashboard.yaml.template"
        
        # Verify it was created as a file, not a directory
        if [ -f "apisix/conf/dashboard.yaml" ]; then
            replace_in_file "apisix/conf/dashboard.yaml" "APISIX_DASHBOARD_SECRET_PLACEHOLDER" "$APISIX_DASHBOARD_SECRET" "APISIX Dashboard JWT Secret"
            replace_in_file "apisix/conf/dashboard.yaml" "APISIX_DASHBOARD_PASSWORD_PLACEHOLDER" "$APISIX_DASHBOARD_PASSWORD" "APISIX Dashboard Admin Password"
            echo "✅ Created apisix/conf/dashboard.yaml"
        else
            echo "❌ Failed to create dashboard.yaml as a file"
        fi
    fi
    
    # Create prometheus.yml configuration file
    cat > apisix/conf/prometheus.yml <<EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'apisix'
    static_configs:
      - targets: ['apisix-apisix-1:9091']
    metrics_path: /apisix/prometheus/metrics
EOF
    echo "✅ Created apisix/conf/prometheus.yml"
    
    # Create APISIX .env file
    cat > apisix/.env <<EOF
# APISIX Configuration
APISIX_ADMIN_KEY=$APISIX_ADMIN_KEY
EOF
    echo "✅ Created apisix/.env"
    
    # Create ViolentUTF configurations
    log_detail "Creating ViolentUTF configurations..."
    mkdir -p violentutf/.streamlit
    
    # Create ViolentUTF .env file
    cat > violentutf/.env <<EOF
KEYCLOAK_URL=http://localhost:8080/
KEYCLOAK_REALM=ViolentUTF
KEYCLOAK_CLIENT_ID=violentutf
KEYCLOAK_CLIENT_SECRET=$VIOLENTUTF_CLIENT_SECRET
KEYCLOAK_USERNAME=violentutf.web
KEYCLOAK_PASSWORD=$VIOLENTUTF_USER_PASSWORD
PYRIT_DB_SALT=$VIOLENTUTF_PYRIT_SALT
JWT_SECRET_KEY=$FASTAPI_SECRET_KEY
VIOLENTUTF_API_KEY=$VIOLENTUTF_API_KEY
VIOLENTUTF_API_URL=http://localhost:9080/api
KEYCLOAK_URL_BASE=http://localhost:9080/auth
AI_PROXY_BASE_URL=http://localhost:9080/ai
EOF
    echo "✅ Created violentutf/.env"
    
    # Create secrets.toml
    cat > violentutf/.streamlit/secrets.toml <<EOF
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "$VIOLENTUTF_COOKIE_SECRET"

[auth.keycloak]
client_id = "violentutf"
client_secret = "$VIOLENTUTF_CLIENT_SECRET"
server_metadata_url = "http://localhost:8080/realms/ViolentUTF/.well-known/openid-configuration"

[auth.providers.keycloak]
issuer = "http://localhost:8080/realms/ViolentUTF"
token_endpoint = "http://localhost:8080/realms/ViolentUTF/protocol/openid-connect/token"
authorization_endpoint = "http://localhost:8080/realms/ViolentUTF/protocol/openid-connect/auth"
userinfo_endpoint = "http://localhost:8080/realms/ViolentUTF/protocol/openid-connect/userinfo"
jwks_uri = "http://localhost:8080/realms/ViolentUTF/protocol/openid-connect/certs"

[apisix]
client_id = "apisix"
client_secret = "$APISIX_CLIENT_SECRET"
EOF
    echo "✅ Created violentutf/.streamlit/secrets.toml"
    
    # Create FastAPI configuration
    log_detail "Creating FastAPI configuration..."
    mkdir -p violentutf_api/fastapi_app
    
    # Check if we're overwriting an existing file with preserved credentials
    local existing_api_key=""
    local existing_openai_key=""
    local existing_anthropic_key=""
    if [ -f "violentutf_api/fastapi_app/.env" ]; then
        existing_api_key=$(grep "^VIOLENTUTF_API_KEY=" violentutf_api/fastapi_app/.env | cut -d'=' -f2- || echo "")
        existing_openai_key=$(grep "^OPENAI_API_KEY=" violentutf_api/fastapi_app/.env | cut -d'=' -f2- || echo "")
        existing_anthropic_key=$(grep "^ANTHROPIC_API_KEY=" violentutf_api/fastapi_app/.env | cut -d'=' -f2- || echo "")
    fi
    
    # Use existing API key if available
    if [ -n "$existing_api_key" ]; then
        VIOLENTUTF_API_KEY="$existing_api_key"
    fi
    
    cat > violentutf_api/fastapi_app/.env <<EOF
# FastAPI Configuration
SECRET_KEY=$FASTAPI_SECRET_KEY
JWT_SECRET_KEY=$FASTAPI_SECRET_KEY
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
API_KEY_EXPIRE_DAYS=365

# Database
DATABASE_URL=sqlite+aiosqlite:///./app_data/violentutf.db

# Keycloak Configuration
KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=ViolentUTF
KEYCLOAK_CLIENT_ID=$FASTAPI_CLIENT_ID
KEYCLOAK_CLIENT_SECRET=$FASTAPI_CLIENT_SECRET

# APISIX Configuration
APISIX_BASE_URL=http://apisix-apisix-1:9080
APISIX_ADMIN_URL=http://apisix-apisix-1:9180
APISIX_ADMIN_KEY=$APISIX_ADMIN_KEY
VIOLENTUTF_API_KEY=$VIOLENTUTF_API_KEY
VIOLENTUTF_API_URL=http://apisix-apisix-1:9080

# Service Configuration
DEFAULT_USERNAME=violentutf.web
PYRIT_DB_SALT=$VIOLENTUTF_PYRIT_SALT
SERVICE_NAME="ViolentUTF API"
SERVICE_VERSION=1.0.0
DEBUG=false

# AI Provider Configuration (from ai-tokens.env)
OPENAI_ENABLED=${OPENAI_ENABLED:-false}
ANTHROPIC_ENABLED=${ANTHROPIC_ENABLED:-false}
OLLAMA_ENABLED=${OLLAMA_ENABLED:-false}
OPEN_WEBUI_ENABLED=${OPEN_WEBUI_ENABLED:-false}
OPENAPI_ENABLED=${OPENAPI_ENABLED:-false}
EOF

    # Add AI provider keys if they exist (from ai-tokens.env or preserved)
    if [ -n "$existing_openai_key" ]; then
        echo "OPENAI_API_KEY=$existing_openai_key" >> violentutf_api/fastapi_app/.env
    elif [ -n "$OPENAI_API_KEY" ] && [ "$OPENAI_API_KEY" != "your_openai_api_key_here" ]; then
        echo "OPENAI_API_KEY=$OPENAI_API_KEY" >> violentutf_api/fastapi_app/.env
    fi
    
    if [ -n "$existing_anthropic_key" ]; then
        echo "ANTHROPIC_API_KEY=$existing_anthropic_key" >> violentutf_api/fastapi_app/.env
    elif [ -n "$ANTHROPIC_API_KEY" ] && [ "$ANTHROPIC_API_KEY" != "your_anthropic_api_key_here" ]; then
        echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" >> violentutf_api/fastapi_app/.env
    fi
    
    # Add Ollama endpoint if configured
    if [ -n "$OLLAMA_ENDPOINT" ] && [ "$OLLAMA_ENABLED" = "true" ]; then
        echo "OLLAMA_ENDPOINT=$OLLAMA_ENDPOINT" >> violentutf_api/fastapi_app/.env
    fi
    
    # Add Open WebUI configuration if enabled
    if [ "$OPEN_WEBUI_ENABLED" = "true" ]; then
        [ -n "$OPEN_WEBUI_ENDPOINT" ] && echo "OPEN_WEBUI_ENDPOINT=$OPEN_WEBUI_ENDPOINT" >> violentutf_api/fastapi_app/.env
        [ -n "$OPEN_WEBUI_API_KEY" ] && [ "$OPEN_WEBUI_API_KEY" != "your_open_webui_api_key_here" ] && echo "OPEN_WEBUI_API_KEY=$OPEN_WEBUI_API_KEY" >> violentutf_api/fastapi_app/.env
    fi
    echo "✅ Created violentutf_api/fastapi_app/.env"
    
    echo "✅ All configuration files created successfully"
    return 0
}

# Function to backup user configurations
backup_existing_configs() {
    log_detail "Backing up user configurations and credentials..."
    mkdir -p "/tmp/vutf_backup"
    
    # Backup AI tokens (user's API keys)
    [ -f "$AI_TOKENS_FILE" ] && cp "$AI_TOKENS_FILE" "/tmp/vutf_backup/"
    
    # Backup all .env files (preserve credentials)
    [ -f "keycloak/.env" ] && cp "keycloak/.env" "/tmp/vutf_backup/keycloak.env"
    [ -f "apisix/.env" ] && cp "apisix/.env" "/tmp/vutf_backup/apisix.env"
    [ -f "violentutf/.env" ] && cp "violentutf/.env" "/tmp/vutf_backup/violentutf.env"
    [ -f "violentutf_api/fastapi_app/.env" ] && cp "violentutf_api/fastapi_app/.env" "/tmp/vutf_backup/fastapi.env"
    
    # Backup Streamlit secrets
    [ -f "violentutf/.streamlit/secrets.toml" ] && cp "violentutf/.streamlit/secrets.toml" "/tmp/vutf_backup/streamlit_secrets.toml"
    
    # Backup any custom APISIX routes
    [ -f "apisix/conf/custom_routes.yml" ] && cp "apisix/conf/custom_routes.yml" "/tmp/vutf_backup/"
    
    # Backup user application data preferences
    if [ -d "violentutf/app_data" ]; then
        tar -czf "/tmp/vutf_backup/app_data_backup.tar.gz" -C violentutf app_data 2>/dev/null || true
    fi
    
    log_success "User configurations and credentials backed up"
}

# Function to restore user configurations
restore_user_configs() {
    echo "Restoring user configurations..."
    
    if [ -d "/tmp/vutf_backup" ]; then
        # Restore AI tokens
        [ -f "/tmp/vutf_backup/$AI_TOKENS_FILE" ] && cp "/tmp/vutf_backup/$AI_TOKENS_FILE" .
        
        # Restore .env files (preserve credentials)
        if [ -f "/tmp/vutf_backup/keycloak.env" ]; then
            mkdir -p keycloak
            cp "/tmp/vutf_backup/keycloak.env" "keycloak/.env"
            echo "  ✓ Restored Keycloak credentials"
        fi
        
        if [ -f "/tmp/vutf_backup/apisix.env" ]; then
            mkdir -p apisix
            cp "/tmp/vutf_backup/apisix.env" "apisix/.env"
            echo "  ✓ Restored APISIX credentials"
        fi
        
        if [ -f "/tmp/vutf_backup/violentutf.env" ]; then
            mkdir -p violentutf
            cp "/tmp/vutf_backup/violentutf.env" "violentutf/.env"
            echo "  ✓ Restored ViolentUTF credentials"
        fi
        
        if [ -f "/tmp/vutf_backup/fastapi.env" ]; then
            mkdir -p violentutf_api/fastapi_app
            cp "/tmp/vutf_backup/fastapi.env" "violentutf_api/fastapi_app/.env"
            echo "  ✓ Restored FastAPI credentials"
        fi
        
        # Restore Streamlit secrets
        if [ -f "/tmp/vutf_backup/streamlit_secrets.toml" ]; then
            mkdir -p violentutf/.streamlit
            cp "/tmp/vutf_backup/streamlit_secrets.toml" "violentutf/.streamlit/secrets.toml"
            echo "  ✓ Restored Streamlit secrets"
        fi
        
        # Restore custom routes
        [ -f "/tmp/vutf_backup/custom_routes.yml" ] && cp "/tmp/vutf_backup/custom_routes.yml" "apisix/conf/"
        
        # Restore user application data if it was backed up
        if [ -f "/tmp/vutf_backup/app_data_backup.tar.gz" ]; then
            mkdir -p violentutf
            tar -xzf "/tmp/vutf_backup/app_data_backup.tar.gz" -C violentutf 2>/dev/null || true
            echo "  ✓ Restored application data"
        fi
        
        rm -rf "/tmp/vutf_backup"
        echo "✅ User configurations restored"
    else
        echo "No backup found to restore"
    fi
}