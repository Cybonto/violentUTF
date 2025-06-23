
# Setup Notes for ViolentUTF - Red Teaming Platform

## Overview
This platform includes:
- **Keycloak** for SSO authentication
- **APISIX** for API gateway and proxy
- **AI Proxy** supporting multiple LLM providers
- **ViolentUTF** Python application with Streamlit

## Prerequisites

### For All Platforms
- **Docker Desktop** - Required for Keycloak and APISIX containers
- **Python 3.9+** - Required for the ViolentUTF application
- **Available Ports**: 8080 (Keycloak), 9080 (APISIX), 9180 (APISIX Admin), 9001 (APISIX Dashboard), 8501 (Streamlit)

### For Windows
- This script uses winget for installing Python. If you prefer Chocolatey or any other package manager, replace that portion accordingly.
- `py --version` is the recommended approach on Windows to use the Python launcher.
- After Python is installed via winget, you may need to open a new terminal or rerun the script to ensure the Python path is recognized.

### For Mac OS
- **Docker Desktop for Mac** must be installed and running
- **Python 3.9+** must be installed before running the script
- **Homebrew** (optional but recommended): `brew install python3`
- Make the script executable:
```bash
chmod +x setup_macos.sh
```

### For Linux
- This example script is tailored to Debian/Ubuntu using apt-get.
- For Fedora, CentOS, Arch, or other distros, replace the package manager commands as appropriate (dnf, yum, pacman, etc.).
- If your distribution's python3 is older than 3.9, you may need an additional repository (e.g., ppa:deadsnakes/ppa for Ubuntu) or compile from source.
- Make the script executable before running it:
```bash
chmod +x setup_linux.sh
```

## AI Provider Configuration

### Supported Providers
- **OpenAI** (GPT-4, GPT-3.5-turbo, GPT-4-turbo)
- **Anthropic** (Claude-3 Opus, Sonnet, Haiku)
- **Ollama** (Local LLMs: llama2, codellama, mistral, llama3)
- **Open WebUI** (Web interface for local LLMs)

### AI Configuration File
The script creates `ai-tokens.env` with the following structure:
```env
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
```

**Important**: Edit this file with your actual API keys before running the script for full AI functionality.

## Running the Setup

### First Time Setup
```bash
./setup_macos.sh
```

### Cleanup and Fresh Start
```bash
./setup_macos.sh --cleanup
```
This removes all containers, volumes, and configuration files while preserving:
- Python virtual environment
- AI tokens configuration file
- Template files

## Service Access Information

After successful setup, you can access:

### Keycloak Admin Console
- **URL**: http://localhost:8080
- **Username**: admin
- **Password**: admin

### APISIX Gateway
- **Main URL**: http://localhost:9080
- **Admin API**: http://localhost:9180
- **Dashboard**: http://localhost:9001

### ViolentUTF Application
- **URL**: http://localhost:8501

### AI Proxy Endpoints
Base URL: `http://localhost:9080/ai/`

**OpenAI routes:**
- `/ai/openai/gpt4` → GPT-4
- `/ai/openai/gpt35` → GPT-3.5-turbo
- `/ai/openai/gpt4-turbo` → GPT-4-turbo

**Anthropic routes:**
- `/ai/anthropic/opus` → Claude-3 Opus
- `/ai/anthropic/sonnet` → Claude-3 Sonnet
- `/ai/anthropic/haiku` → Claude-3 Haiku

**Ollama routes:**
- `/ai/ollama/llama2` → Llama2
- `/ai/ollama/codellama` → CodeLlama
- `/ai/ollama/mistral` → Mistral
- `/ai/ollama/llama3` → Llama3

### AI Gateway Authentication
The AI Gateway uses **API key authentication** for secure access. Each setup run generates a unique 32-character API key.

**Key Features:**
- ✅ **Dynamic generation**: New secure key generated on each setup run
- ✅ **Environment integration**: Automatically saved to `violentutf/.env`
- ✅ **Zero configuration**: No manual setup required

**Usage:** Include the API key in the `apikey` header:
```bash
curl -X POST http://localhost:9080/ai/openai/gpt4 \
  -H "apikey: YOUR_GENERATED_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

**Finding Your API Key:**
- Displayed in setup output as "ViolentUTF AI Gateway API Key"
- Stored in `violentutf/.env` as `VIOLENTUTF_API_KEY`
- Used automatically by the Streamlit application

## Directory Structure
```
project/
├── setup_macos.sh              # Main setup script
├── ai-tokens.env               # AI provider configuration
├── keycloak/
│   ├── docker-compose.yml      # Keycloak containers
│   ├── env.sample              # Environment template
│   ├── .env                    # Generated environment (secure)
│   └── realm-export.json       # Keycloak realm configuration
├── apisix/
│   ├── docker-compose.yml      # APISIX containers
│   └── conf/
│       ├── config.yaml.template     # APISIX config template
│       ├── dashboard.yaml.template  # Dashboard config template
│       ├── config.yaml              # Generated config (secure)
│       └── dashboard.yaml           # Generated config (secure)
├── violentutf/
│   ├── Home.py                 # Main Streamlit application
│   ├── requirements.txt        # Python dependencies
│   ├── env.sample              # Environment template
│   ├── .env                    # Generated environment (secure)
│   └── .streamlit/
│       ├── secrets.toml.sample # Secrets template
│       └── secrets.toml        # Generated secrets (secure)
└── .vitutf/                    # Python virtual environment
```

## Security Notes

### Generated Secrets
The script automatically generates secure random values for:
- Keycloak database passwords
- Keycloak client secrets
- APISIX admin API keys
- APISIX dashboard credentials
- **ViolentUTF AI Gateway API key** (32-character secure string)
- Application secrets

**Important**: These are displayed at the end of setup. Save them securely!

### Network Security
- All services communicate via a shared Docker network (`vutf-network`)
- APISIX acts as a reverse proxy for enhanced security
- Keycloak provides SSO authentication

## Troubleshooting

### Common Issues
1. **Docker not running**: Ensure Docker Desktop is started
2. **Port conflicts**: Check if ports 8080, 9080, 9180, 9001, 8501 are available
3. **Python version**: Ensure Python 3.9+ is installed
4. **Permission errors**: Make sure script is executable (`chmod +x setup_macos.sh`)

### AI Gateway Issues

#### "Failed to get response from AI Gateway" Error
This typically indicates an API key authentication problem:

**Solution 1: Restart Streamlit Application**
```bash
# Stop current Streamlit app (Ctrl+C)
cd violentutf
streamlit run Home.py
```

**Solution 2: Verify API Key**
```bash
# Check if API key exists in environment file
cat violentutf/.env | grep VIOLENTUTF_API_KEY

# Test API key manually
curl -H "apikey: YOUR_API_KEY" -H "Content-Type: application/json" \
  -X POST http://localhost:9080/ai/openai/gpt4 \
  -d '{"messages":[{"role":"user","content":"test"}]}'
```

**Solution 3: Regenerate API Key**
```bash
# Run setup again to generate new API key
./setup_macos.sh
```

#### API Key Not Loading in Application
If the Streamlit app shows "Using fallback API key" in logs:

1. **Check file permissions**: `ls -la violentutf/.env`
2. **Verify file content**: `cat violentutf/.env | grep VIOLENTUTF_API_KEY`
3. **Restart application**: The token manager loads environment on startup

### Testing the Setup
The script includes comprehensive testing that checks:
- Docker container connectivity
- Service accessibility
- Network communication between containers
- Configuration file validity
- AI proxy functionality
- **API key authentication** for AI Gateway routes

### Logs and Debugging
View container logs:
```bash
# Keycloak logs
cd keycloak && docker-compose logs

# APISIX logs  
cd apisix && docker-compose logs
```

### Reset Individual Components
```bash
# Reset only Keycloak
cd keycloak && docker-compose down -v

# Reset only APISIX
cd apisix && docker-compose down -v

# Reset shared network
docker network rm vutf-network
```

## Advanced Configuration

### Custom AI Providers
To add custom AI providers, edit the route creation functions in the setup script and add entries to the AI configuration file.

### APISIX Plugins
Additional APISIX plugins can be configured by editing `apisix/conf/config.yaml.template` before running setup.

### Scaling
For production use, consider:
- External databases for Keycloak
- Load balancing for APISIX
- Persistent storage for AI model caches
- SSL/TLS certificates for secure communication

## Architecture Changes (v2.0)

### Authentication Migration: OIDC → API Key

**Previous Version**: Used OpenID Connect (OIDC) for AI Gateway authentication
- ❌ Complex JWT token flow
- ❌ Network connectivity issues between APISIX and Keycloak  
- ❌ Bearer token management complexity

**Current Version**: Uses API key authentication
- ✅ **Simple and reliable**: Direct API key in header
- ✅ **Dynamic generation**: New key per setup run
- ✅ **Automatic integration**: No manual configuration
- ✅ **Development-friendly**: Easier debugging and testing

### Why API Key Authentication Was Chosen

The migration to API key authentication was primarily driven by **development and setup reliability** concerns:

1. **Network Connectivity Issues**: APISIX containers often failed to reach Keycloak's OIDC discovery endpoints during startup
2. **Container Dependencies**: Complex service orchestration required careful timing of container starts
3. **Development Complexity**: JWT token validation added debugging complexity for AI Gateway testing
4. **Setup Reliability**: Docker network issues frequently broke OIDC flow in development environments

### Production Considerations

⚠️ **Important**: For production deployments, **OpenID Connect (OIDC) is recommended** over API key authentication:

**OIDC Advantages in Production:**
- ✅ **Token expiration**: JWT tokens have built-in expiry for enhanced security
- ✅ **Centralized authentication**: Unified identity management across all services
- ✅ **Audit capabilities**: Comprehensive logging and user attribution
- ✅ **Role-based access**: Fine-grained permissions and scopes
- ✅ **Standard compliance**: Industry-standard OAuth 2.0/OIDC protocols
- ✅ **Revocation**: Ability to invalidate tokens immediately

**API Key Limitations in Production:**
- ❌ **No expiration**: Keys remain valid indefinitely unless manually rotated
- ❌ **Limited attribution**: Harder to track individual user actions
- ❌ **Rotation complexity**: Manual key management across services
- ❌ **Security risk**: Long-lived credentials increase exposure window

**Production Migration Path:**
```bash
# For production, configure OIDC by editing route creation functions
# Replace 'key-auth' plugin with 'openid-connect' in setup scripts
# Example OIDC configuration:
plugins:
  openid-connect:
    discovery: "http://keycloak:8080/auth/realms/your-realm/.well-known/openid_configuration"
    client_id: "your-client-id"
    client_secret: "your-client-secret"
    scope: "openid profile"
```

### Migration Impact
- **Development**: Current API key approach provides reliable setup experience
- **Production**: Plan migration to OIDC for enhanced security and compliance
- **Existing users**: Run `./setup_macos.sh` to migrate automatically
- **API consumers**: Update to use `apikey` header instead of `Authorization: Bearer`
- **No breaking changes**: Streamlit application updated automatically

## Support
For issues specific to:
- **Keycloak**: Check Keycloak documentation
- **APISIX**: Check APISIX documentation  
- **AI Gateway Authentication**: Follow troubleshooting guide above
- **AI Provider Integration**: Verify API keys in `ai-tokens.env`
- **ViolentUTF**: Check Python dependencies and Streamlit logs
