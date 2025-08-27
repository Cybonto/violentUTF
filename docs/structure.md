# ViolentUTF Project Structure

## **Project Root Directory Structure**

```
ViolentUTF_nightly/
├── 📄 Setup Scripts & Configuration
│   ├── setup_macos.sh                 # macOS setup script (main)
│   ├── setup_linux.sh                 # Linux setup script
│   ├── setup_windows.bat              # Windows setup script
│   ├── launch_violentutf.sh           # Streamlit launcher script
│   ├── check_services.sh              # Service status checker
│   ├── ai-tokens.env                  # AI provider API keys
│   ├── ai-tokens.env.sample           # AI tokens template
│   ├── setup_macos_mcp_complete.md    # MCP setup documentation
│   ├── setup_macos_mcp_fix.patch      # MCP setup patches
│   ├── temporaryfiles.md              # Temporary files tracking
│   └── CLAUDE.md                      # Project instructions for Claude Code
│
├── 🔐 Authentication & Gateway
│   ├── keycloak/                      # Keycloak SSO service
│   │   ├── docker-compose.yml
│   │   ├── env.sample
│   │   ├── realm-export.json          # Keycloak realm configuration
│   │   └── README.md                  # Keycloak setup guide
│   ├── apisix/                        # APISIX API Gateway
│   │   ├── docker-compose.yml
│   │   ├── conf/
│   │   │   ├── config.yaml.template
│   │   │   ├── dashboard.yaml.template
│   │   │   ├── nginx.conf.template
│   │   │   └── prometheus.yml
│   │   ├── configure_routes.sh         # Main route configuration
│   │   ├── configure_mcp_routes.sh     # MCP-specific routes
│   │   ├── verify_routes.sh            # Route verification
│   │   ├── remove_routes.sh            # Route cleanup
│   │   ├── env.sample
│   │   ├── logs/                       # APISIX logs
│   │   └── README.md                   # APISIX setup guide
│   └── certs/                          # SSL certificates
│       ├── cert.pem
│       ├── key.pem
│       └── openssl.cnf
│
├── 🚀 ViolentUTF Core Application
│   ├── violentutf/                    # Main Streamlit application
│   │   ├── Home.py                    # Main entry point
│   │   ├── pages/                     # Streamlit pages
│   │   │   ├── 0_Start.py             # Start page with JWT authentication
│   │   │   ├── 1_Configure_Generators.py # Generator management
│   │   │   ├── 2_Configure_Datasets.py   # Dataset configuration
│   │   │   ├── 3_Configure_Converters.py # Converter setup
│   │   │   ├── 4_Configure_Scorers.py    # Scorer configuration
│   │   │   ├── 5_Dashboard.py            # Main dashboard
│   │   │   ├── 5_Dashboard_2.py          # Alternative dashboards
│   │   │   ├── 5_Dashboard_3.py
│   │   │   ├── IronUTF.py                # Defense module
│   │   │   └── Simple_Chat.py            # Chat interface
│   │   ├── utils/                     # Utility modules
│   │   │   ├── auth_utils.py          # Authentication utilities
│   │   │   ├── auth_utils_keycloak.py # Keycloak auth handler
│   │   │   ├── jwt_manager.py         # JWT token management
│   │   │   ├── token_manager.py       # Legacy token management
│   │   │   ├── mcp_client.py          # MCP client utilities
│   │   │   ├── mcp_integration.py     # MCP integration layer
│   │   │   ├── mcp_context_manager.py # MCP context management
│   │   │   ├── mcp_resource_browser.py # MCP resource browser
│   │   │   ├── mcp_scorer_integration.py # MCP scorer integration
│   │   │   ├── mcp_command_handler.py # MCP command handling
│   │   │   ├── user_context.py        # User context management
│   │   │   ├── logging.py             # Logging configuration
│   │   │   └── error_handling.py      # Error handling
│   │   ├── generators/                # Generator configuration
│   │   │   └── generator_config.py
│   │   ├── converters/                # Converter modules
│   │   │   ├── converter_config.py
│   │   │   └── converter_application.py
│   │   ├── orchestrators/             # Orchestrator modules
│   │   │   ├── orchestrator_config.py
│   │   │   └── orchestrator_application.py
│   │   ├── scorers/                   # Scorer modules
│   │   │   ├── scorer_config.py
│   │   │   └── scorer_application.py
│   │   ├── util_datasets/             # Dataset utilities
│   │   │   ├── data_loaders.py
│   │   │   └── dataset_transformations.py
│   │   ├── custom_targets/            # Custom PyRIT targets
│   │   │   └── apisix_ai_gateway.py
│   │   ├── parameters/                # Configuration files
│   │   │   ├── default_parameters.yaml
│   │   │   ├── generators.yaml
│   │   │   ├── orchestrators.json
│   │   │   └── scorers.yaml
│   │   ├── app_data/                  # Application data
│   │   │   ├── simplechat/            # Simple chat configurations
│   │   │   └── violentutf/            # ViolentUTF specific data
│   │   │       ├── cache/
│   │   │       ├── api_memory/        # Orchestrator memory databases
│   │   │       ├── datasets/          # Garak datasets
│   │   │       │   └── garak/         # Garak test datasets
│   │   │       ├── parameters/
│   │   │       ├── templates/         # Template files
│   │   │       │   └── jailbreaks/    # Jailbreak templates
│   │   │       └── *.db               # PyRIT memory databases
│   │   ├── app_logs/                  # Application logs
│   │   │   └── app.log
│   │   ├── reporting/                 # Reporting modules
│   │   ├── sample_run/                # Sample outputs
│   │   ├── requirements.txt           # Python dependencies
│   │   ├── env.sample                 # Environment template
│   │   ├── Dockerfile                 # Docker configuration
│   │   └── README.md                  # ViolentUTF documentation
│   └── violentutf_logs/               # Runtime logs
│       └── streamlit.log              # Streamlit application logs
│
├── 🔧 API Services
│   └── violentutf_api/                # FastAPI services
│       ├── docker-compose.yml
│       ├── jwt_cli.py                 # JWT CLI tool
│       └── fastapi_app/               # FastAPI application
│           ├── Dockerfile
│           ├── main.py                # FastAPI entry point
│           ├── requirements.txt
│           ├── requirements-minimal.txt
│           ├── app/
│           │   ├── api/               # API routes
│           │   │   ├── routes.py      # Main router
│           │   │   ├── v1/            # API v1 endpoints
│           │   │   └── endpoints/     # Individual endpoints
│           │   │       ├── auth.py    # Authentication endpoints
│           │   │       ├── health.py  # Health check
│           │   │       ├── jwt_keys.py # JWT key management
│           │   │       ├── generators.py # Generator management
│           │   │       ├── orchestrators.py # Orchestrator management
│           │   │       ├── datasets.py # Dataset management
│           │   │       ├── converters.py # Converter management
│           │   │       ├── scorers.py # Scorer management
│           │   │       ├── sessions.py # Session management
│           │   │       ├── files.py   # File operations
│           │   │       ├── config.py  # Configuration management
│           │   │       ├── database.py # Database operations
│           │   │       ├── redteam.py # Red team operations
│           │   │       ├── apisix_admin.py # APISIX admin
│           │   │       └── echo.py    # Testing endpoints
│           │   ├── core/              # Core modules
│           │   │   ├── config.py      # Configuration
│           │   │   ├── security.py    # Security functions
│           │   │   ├── auth.py        # Authentication logic
│           │   │   ├── error_handling.py # Error handling
│           │   │   ├── logging.py     # Logging setup
│           │   │   ├── rate_limiting.py # Rate limiting
│           │   │   ├── validation.py  # Input validation
│           │   │   ├── password_policy.py # Password policies
│           │   │   ├── security_check.py # Security checks
│           │   │   ├── security_headers.py # Security headers
│           │   │   └── security_logging.py # Security logging
│           │   ├── db/                # Database layer
│           │   │   ├── database.py    # Database connection
│           │   │   ├── duckdb_manager.py # DuckDB management
│           │   │   └── migrations/    # Database migrations
│           │   ├── mcp/               # MCP server implementation
│           │   │   ├── config.py      # MCP configuration
│           │   │   ├── auth.py        # MCP authentication
│           │   │   ├── oauth_proxy.py # OAuth proxy
│           │   │   ├── apisix_routes.py # APISIX integration
│           │   │   ├── server/        # MCP server core
│           │   │   │   ├── base.py    # Base server class
│           │   │   │   └── transports.py # Transport implementations
│           │   │   ├── tools/         # MCP tools
│           │   │   │   ├── generators.py # Generator tools
│           │   │   │   ├── orchestrators.py # Orchestrator tools
│           │   │   │   ├── introspection.py # Tool discovery
│           │   │   │   ├── executor.py # Tool executor
│           │   │   │   └── generator.py # Tool generator
│           │   │   ├── prompts/       # MCP prompts
│           │   │   │   ├── security.py # Security prompts
│           │   │   │   ├── testing.py # Testing prompts
│           │   │   │   └── base.py    # Base prompt class
│           │   │   ├── resources/     # MCP resources
│           │   │   │   ├── manager.py # Resource manager
│           │   │   │   ├── datasets.py # Dataset resources
│           │   │   │   ├── configuration.py # Config resources
│           │   │   │   └── base.py    # Base resource class
│           │   │   ├── tests/         # MCP tests
│           │   │   └── utils/         # MCP utilities
│           │   ├── models/            # Data models
│           │   │   ├── auth.py        # Auth models
│           │   │   ├── api_key.py     # API key models
│           │   │   └── orchestrator.py # Orchestrator models
│           │   ├── schemas/           # Pydantic schemas
│           │   │   ├── auth.py        # Auth schemas
│           │   │   ├── generators.py  # Generator schemas
│           │   │   ├── orchestrator.py # Orchestrator schemas
│           │   │   ├── datasets.py    # Dataset schemas
│           │   │   ├── converters.py  # Converter schemas
│           │   │   ├── scorers.py     # Scorer schemas
│           │   │   ├── sessions.py    # Session schemas
│           │   │   ├── files.py       # File schemas
│           │   │   ├── config.py      # Config schemas
│           │   │   └── database.py    # Database schemas
│           │   ├── services/          # Business logic services
│           │   │   ├── pyrit_integration.py # PyRIT integration
│           │   │   ├── garak_integration.py # Garak integration
│           │   │   ├── generator_integration_service.py
│           │   │   ├── scorer_integration_service.py
│           │   │   ├── dataset_integration_service.py
│           │   │   ├── pyrit_orchestrator_service.py
│           │   │   └── keycloak_verification.py
│           │   └── utils/             # FastAPI utilities
│           ├── app_data/              # FastAPI data
│           │   ├── config/
│           │   ├── sessions/
│           │   └── violentutf/        # PyRIT memory databases
│           ├── config/                # Configuration files
│           ├── test_config/           # Test configurations
│           ├── test_data/             # Test data
│           ├── venv_api/              # Virtual environment
│           ├── diagnose_user_context.py # Diagnostic tools
│           ├── migrate_user_context.py # Migration tools
│           ├── verify_redteam_install.py # Installation verification
│           ├── test_phase3.py         # Phase 3 tests
│           ├── test_phase3_minimal.py
│           └── test_phase3_standalone.py
│
├── 📚 Documentation
│   └── docs/                          # Project documentation
│       ├── structure.md               # This file
│       ├── api/                       # API documentation
│       │   ├── README.md              # API documentation hub
│       │   ├── authentication.md      # Authentication guide
│       │   ├── endpoints.md           # API endpoints reference
│       │   ├── gateway.md             # APISIX gateway guide
│       │   ├── frameworks.md          # Framework integration
│       │   ├── deployment.md          # Deployment guide
│       │   ├── audit_api.md           # Audit API documentation
│       │   └── mcp-client.md          # MCP client documentation
│       ├── guides/                    # User guides
│       │   ├── README.md              # Guides index
│       │   ├── Guide_IronUTF.md       # IronUTF defense module
│       │   ├── Guide_RedTeaming_GenAIsystems.md # Red teaming methodology
│       │   ├── Guide_Scorers.md       # PyRIT scorers guide
│       │   ├── Guide_SSO_with_KeyCloak.md # SSO setup guide
│       │   ├── Guide_SimpleChat_enhancementStrip.md # Chat enhancements
│       │   └── Guide_SimpleChat_mcp-workflows.md # MCP workflows
│       ├── mcp/                       # MCP documentation
│       │   ├── README.md              # MCP overview
│       │   ├── architecture.md        # MCP architecture
│       │   ├── configuration.md       # MCP configuration
│       │   ├── development.md         # MCP development guide
│       │   ├── troubleshooting.md     # MCP troubleshooting
│       │   ├── api-reference.md       # MCP API reference
│       │   ├── mcp_endpoints_working.md # Working endpoints
│       │   ├── anthropic_mcp.md       # Official MCP spec
│       │   ├── violentutf_mcp_design.md # Design documentation
│       │   ├── violentutf_mcp_dev.md  # Development notes
│       │   ├── fastapi_mcp_docs.txt   # FastAPI MCP docs
│       │   ├── fastapi_mcp_examples.txt # MCP examples
│       │   └── api/                   # MCP API documentation
│       │       ├── README.md          # MCP API hub
│       │       ├── mcp-client.md      # MCP client API
│       │       ├── mcp-integration.md # MCP integration API
│       │       ├── mcp-context-manager.md # Context manager API
│       │       ├── mcp-resource-browser.md # Resource browser API
│       │       └── mcp-scorer-integration.md # Scorer integration API
│       ├── troubleshooting/           # Troubleshooting guides
│       │   ├── DOCKER_NETWORK_TROUBLESHOOTING.md
│       │   ├── cert_preparation.md
│       │   ├── lesson_memoryManagement.md
│       │   └── mcp-connection.md
│       ├── fixes/                     # Fix documentation
│       │   └── scorer_timeout_optimization.md
│       ├── violentUTF_programSteps/   # Step-by-step guides
│       │   ├── 0_HomePage.md
│       │   ├── 1_WelcomePage.md
│       │   ├── 2_ConfigureGenerators.md
│       │   ├── 3_ConfigureDatasets.md
│       │   ├── 4_ConfigureConverters.md
│       │   ├── 5_ConfigureScoringEngine.md
│       │   ├── 6_ConfigureOrchestrators.md
│       │   └── 7_Reporting.md
│       ├── pyrit-orchestrator.txt     # PyRIT orchestrator notes
│       ├── pyrit_garak_alignment_analysis.md # Analysis documentation
│       ├── simpleChat_nextgen.md      # Next-gen chat features
│       ├── violentutf_Dash.md         # Dashboard documentation
│       ├── __DevPlan.md               # Development planning
│       ├── __SystemEngineering.md     # System engineering notes
│       └── __temp.md                  # Temporary documentation
│
├── 🧪 Testing Framework
│   └── tests/                         # Comprehensive test suite
│       ├── README.md                  # Testing documentation
│       ├── conftest.py                # Test configuration
│       ├── pytest.ini                 # PyTest configuration
│       ├── run_tests.sh               # Test runner
│       ├── run_enhanced_tests.sh      # Enhanced test runner
│       ├── test_services.sh           # Service testing
│       ├── api_tests/                 # API-specific tests
│       │   ├── README.md
│       │   ├── run_api_tests.sh
│       │   ├── conftest.py
│       │   ├── pytest.ini
│       │   └── test_*.py              # Individual API tests
│       ├── mcp_tests/                 # MCP-specific tests
│       │   ├── chatclient/            # Chat client tests
│       │   ├── config/                # Test configurations
│       │   └── app_data/              # Test data
│       ├── utils/                     # Test utilities
│       │   ├── keycloak_auth.py
│       │   └── __init__.py
│       ├── app_data/                  # Test application data
│       └── test_*.py                  # Individual test files
│
├── 📊 Application Data & Storage
│   ├── app_data/                      # Shared application data
│   │   ├── simplechat/                # Simple Chat data
│   │   └── violentutf/                # ViolentUTF data
│   ├── config/                        # Configuration storage
│   └── violentutf_logs/               # Application logs
│
├── 🔧 Development Files
│   ├── node_modules/                  # Node.js dependencies
│   ├── package.json                   # Node.js package file
│   ├── package-lock.json              # Package lock file
│   ├── temp.md                        # Temporary files
│   ├── audit.md                       # Audit documentation
│   ├── setup_notes.md                 # Setup notes
│   ├── setup_macos_mcp_updates.md     # MCP update notes
│   ├── add_mcp_routes.patch           # MCP routing patches
│   └── note_SetupScriptonWindows.md   # Windows setup notes
│
└── 🗃️ Generated Files (Created by Setup)
    ├── keycloak/.env                  # Keycloak environment (generated)
    ├── apisix/conf/config.yaml        # APISIX config (generated)
    ├── apisix/conf/dashboard.yaml     # APISIX dashboard config (generated)
    ├── violentutf/.env                # ViolentUTF environment (generated)
    └── violentutf_api/fastapi_app/.env # FastAPI environment (generated)
```

## **Key Components Explanation**

### 🔐 **Authentication & Security**
- **Keycloak**: Identity and access management for SSO
- **APISIX**: API gateway with authentication, rate limiting, and AI proxy
- **JWT Tokens**: Secure authentication between services with automatic refresh
- **IronUTF**: AI endpoint defense module with prompt filtering
- **Secrets Management**: Centralized secret generation and distribution

### 🚀 **ViolentUTF Core**
- **Streamlit App**: Web interface for AI red-teaming with MCP integration
- **PyRIT Integration**: Microsoft PyRIT framework for security testing
- **Garak Integration**: AI system vulnerability testing with pre-built datasets
- **MCP Client**: Model Context Protocol client for external tool integration
- **Custom Targets**: Custom PyRIT targets for APISIX AI Gateway integration
- **Generators**: AI prompt generation and model configuration systems
- **Scorers**: Response evaluation and scoring with PyRIT scorers
- **Datasets**: Pre-built Garak datasets and custom test datasets

### 🔧 **API Services**
- **FastAPI**: REST API for programmatic access with comprehensive endpoints
- **MCP Server**: Model Context Protocol server with 23+ tools and 12+ prompts
- **Health Monitoring**: Service health checks and monitoring
- **Rate Limiting**: Request throttling and security
- **JWT CLI**: Command-line tool for JWT and API key management
- **Database Integration**: DuckDB for PyRIT memory and session management

### 📡 **MCP (Model Context Protocol) Integration**
- **MCP Server**: Production-ready server with SSE transport
- **Tool Interface**: 23+ specialized tools for generator and orchestrator management
- **Resource Interface**: Access to generators, datasets, and configurations
- **Prompt Interface**: 12+ security testing prompts with dynamic arguments
- **OAuth Proxy**: Complete OAuth 2.0 integration with PKCE support
- **Client Libraries**: Python client libraries for MCP integration

### 🌐 **Architecture**
- **Containerized**: All services run in Docker containers with health checks
- **Network Isolation**: Services communicate through Docker network (`vutf-network`)
- **Gateway Pattern**: All external access through APISIX gateway
- **SSO Integration**: Unified authentication across all services
- **MCP Protocol**: Standard Model Context Protocol for AI tool integration

## **Important Files**

### **Setup & Configuration**
- `setup_*.sh|bat`: Platform-specific setup scripts with MCP support
- `ai-tokens.env`: AI provider API keys (OpenAI, Anthropic, Ollama, etc.)
- `CLAUDE.md`: Instructions for Claude Code development
- `temporaryfiles.md`: Tracking of temporary files for cleanup

### **Security & Authentication**
- `violentutf/.streamlit/secrets.toml`: Keycloak SSO configuration
- `*/.env`: Service-specific environment variables (auto-generated)
- `violentutf/utils/jwt_manager.py`: JWT token management with auto-refresh
- `violentutf_api/jwt_cli.py`: Command-line JWT and API key management

### **Application Logic**
- `violentutf/Home.py`: Main Streamlit application entry
- `violentutf/pages/0_Start.py`: Start page with JWT authentication
- `violentutf_api/fastapi_app/main.py`: FastAPI service entry
- `violentutf_api/fastapi_app/app/mcp/`: MCP server implementation

### **Testing & Validation**
- `tests/run_tests.sh`: Comprehensive test runner
- `apisix/verify_routes.sh`: Route verification and testing
- `check_services.sh`: Service status monitoring
- `tests/api_tests/`: API endpoint testing with authentication
- `tests/mcp_tests/`: MCP protocol and integration testing

## **Development Workflow**

1. **Setup**: Run `setup_macos.sh` (or platform equivalent)
2. **Configure**: Edit `ai-tokens.env` with your AI provider API keys
3. **Access**: Use http://localhost:8501 for Streamlit UI
4. **API**: Use http://localhost:9080/api for REST API
5. **MCP**: Use http://localhost:9080/mcp/sse for MCP protocol
6. **Monitor**: Use `check_services.sh` for status checks
7. **Test**: Use `tests/run_tests.sh` for comprehensive testing

## **Security Architecture**

- **No Direct Access**: Services only accessible through APISIX gateway
- **Authentication Required**: All requests require valid JWT or API key
- **Rate Limited**: Automatic request throttling and abuse prevention
- **Encrypted Communication**: All inter-service communication secured
- **Secret Rotation**: All secrets auto-generated and rotatable
- **MCP Security**: Model Context Protocol with OAuth 2.0 and JWT integration
- **Defense Modules**: IronUTF for real-time AI endpoint protection

## **MCP Integration Architecture**

- **Server-Sent Events**: JSON-RPC 2.0 over SSE transport
- **Tool Management**: 23+ specialized tools for security testing
- **Prompt Library**: 12+ security testing prompts with argument injection
- **Resource Access**: Dynamic access to generators, datasets, and configurations
- **Authentication**: Full OAuth 2.0 proxy with PKCE support
- **Client Compatibility**: Ready for Claude Desktop, VS Code, and custom applications

## **Data Storage & Management**

- **PyRIT Memory**: DuckDB databases for conversation and test result storage
- **Application Data**: Structured storage for configurations and datasets
- **Session Management**: Persistent session data across service restarts
- **Garak Datasets**: Pre-built vulnerability testing datasets
- **Template System**: Jailbreak and prompt templates for security testing
- **Configuration Management**: YAML and JSON configuration files
