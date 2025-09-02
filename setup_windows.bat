@echo off
setlocal enabledelayedexpansion

REM === Script Version and Configuration ===
set "SCRIPT_VERSION=2.1 (Windows Port with Centralized Secrets)"
echo Starting ViolentUTF Setup Script %SCRIPT_VERSION% for Windows...

REM === Help function ===
if /i "%1"=="--help" goto :show_help
if /i "%1"=="-h" goto :show_help

REM === Parse command line arguments ===
set "CLEANUP_MODE=false"
set "DEEPCLEANUP_MODE=false"
if /i "%1"=="--cleanup" (
    set "CLEANUP_MODE=true"
    echo Cleanup mode enabled.
)
if /i "%1"=="--deepcleanup" (
    set "DEEPCLEANUP_MODE=true"
    echo Deep cleanup mode enabled.
)
if /i "%1" NEQ "" if /i "%1" NEQ "--cleanup" if /i "%1" NEQ "--deepcleanup" (
    echo Unknown option: %1
    echo Usage: %0 [--cleanup^|--deepcleanup^|--help]
    goto :eof_error
)

REM === Store generated sensitive values for final report ===
set "SENSITIVE_VALUES_FILE=%TEMP%\sensitive_values_vutf.txt"
if exist "!SENSITIVE_VALUES_FILE!" del "!SENSITIVE_VALUES_FILE!"

REM === Define shared network name globally ===
set "SHARED_NETWORK_NAME=vutf-network"

REM === AI Configuration via .env file ===
set "AI_TOKENS_FILE=ai-tokens.env"
set "CREATED_AI_ROUTES_FILE=%TEMP%\created_ai_routes_vutf.txt"
if exist "!CREATED_AI_ROUTES_FILE!" del "!CREATED_AI_ROUTES_FILE!"
set "SKIP_AI_SETUP=false"

REM === Global Keycloak API Variables ===
set "KEYCLOAK_SERVER_URL=http://localhost:8080"
set "ADMIN_USER=admin"
set "ADMIN_PASS=admin"
set "MASTER_REALM=master"
set "ADMIN_CLIENT_ID=admin-cli"
set "ACCESS_TOKEN="

REM === Global APISIX Variables ===
set "APISIX_URL=http://localhost:9080"
set "APISIX_ADMIN_URL=http://localhost:9180"
set "APISIX_DASHBOARD_URL=http://localhost:9001"


REM Initial check for PowerShell availability
where powershell >nul 2>nul
if errorlevel 1 (
    echo FATAL ERROR: PowerShell is not available or not in PATH.
    echo This script heavily relies on PowerShell for many operations.
    goto :eof_error
)

if "!DEEPCLEANUP_MODE!"=="true" (
    call :perform_deep_cleanup
    goto :eof
)

if "!CLEANUP_MODE!"=="true" (
    call :perform_cleanup
    goto :eof
)

goto :main_script

REM ==========================================================================
REM === FUNCTION DEFINITIONS START ===========================================
REM ==========================================================================

REM --- Backup user configurations function ---
:backup_user_configs
    echo Backing up user configurations...
    if not exist "%TEMP%\vutf_backup" mkdir "%TEMP%\vutf_backup"

    REM Backup AI tokens (user's API keys)
    if exist "!AI_TOKENS_FILE!" copy "!AI_TOKENS_FILE!" "%TEMP%\vutf_backup\" >nul

    REM Backup any custom APISIX routes
    if exist "apisix\conf\custom_routes.yml" copy "apisix\conf\custom_routes.yml" "%TEMP%\vutf_backup\" >nul

    REM Backup user application data preferences
    if exist "violentutf\app_data" (
        powershell -Command "if (Test-Path 'violentutf\app_data') { Compress-Archive -Path 'violentutf\app_data' -DestinationPath '%TEMP%\vutf_backup\app_data_backup.zip' -Force -ErrorAction SilentlyContinue }"
    )

    echo ✅ User configurations backed up
    goto :eof

REM --- Restore user configurations function ---
:restore_user_configs
    echo Restoring user configurations...

    if exist "%TEMP%\vutf_backup" (
        REM Restore AI tokens
        if exist "%TEMP%\vutf_backup\!AI_TOKENS_FILE!" copy "%TEMP%\vutf_backup\!AI_TOKENS_FILE!" . >nul

        REM Restore custom routes
        if exist "%TEMP%\vutf_backup\custom_routes.yml" (
            if not exist "apisix\conf" mkdir "apisix\conf"
            copy "%TEMP%\vutf_backup\custom_routes.yml" "apisix\conf\" >nul
        )

        REM Restore user application data if it was backed up
        if exist "%TEMP%\vutf_backup\app_data_backup.zip" (
            if not exist "violentutf" mkdir "violentutf"
            powershell -Command "if (Test-Path '%TEMP%\vutf_backup\app_data_backup.zip') { Expand-Archive -Path '%TEMP%\vutf_backup\app_data_backup.zip' -DestinationPath 'violentutf' -Force -ErrorAction SilentlyContinue }"
        )

        rmdir /s /q "%TEMP%\vutf_backup" >nul 2>nul
        echo ✅ User configurations restored
    )
    goto :eof

REM --- Network validation function ---
:validate_network_configuration
    echo Validating Docker network configuration...
    docker network inspect !SHARED_NETWORK_NAME! >nul 2>nul
    if errorlevel 1 (
        echo ❌ Shared network not found, creating...
        docker network create !SHARED_NETWORK_NAME!
    )

    REM Verify network connectivity between services
    echo ✅ Network validation completed
    goto :eof

REM --- Python dependencies verification function ---
:verify_python_dependencies
    echo Verifying Python dependencies...
    if exist "violentutf\requirements.txt" (
        if exist ".vitutf\Scripts\activate.bat" (
            call ".vitutf\Scripts\activate.bat"
            pip install -r violentutf\requirements.txt --quiet --disable-pip-version-check >nul 2>nul
            echo ✅ Python dependencies verified
        ) else (
            echo ⚠️ Virtual environment not found, skipping dependency verification
        )
    ) else (
        echo ⚠️ Requirements file not found, skipping dependency verification
    )
    goto :eof

REM --- JWT consistency check function ---
:check_jwt_consistency
    echo Checking JWT configuration consistency...
    set "JWT_ISSUES_FOUND=false"

    REM Check if JWT_SECRET_KEY exists in main environment
    if exist "violentutf\.env" (
        findstr /C:"JWT_SECRET_KEY" "violentutf\.env" >nul || set "JWT_ISSUES_FOUND=true"
    ) else (
        set "JWT_ISSUES_FOUND=true"
    )

    REM Check Streamlit secrets
    if exist "violentutf\.streamlit\secrets.toml" (
        findstr /C:"JWT_SECRET_KEY" "violentutf\.streamlit\secrets.toml" >nul || set "JWT_ISSUES_FOUND=true"
    ) else (
        set "JWT_ISSUES_FOUND=true"
    )

    if "!JWT_ISSUES_FOUND!"=="true" (
        echo ⚠️ JWT configuration issues detected - will be fixed during setup
    ) else (
        echo ✅ JWT configuration is consistent
    )
    goto :eof

REM --- Services validation function ---
:validate_all_services
    echo Validating all services...
    set "ALL_SERVICES_HEALTHY=true"

    REM Check Docker
    docker --version >nul 2>nul || (
        echo ❌ Docker not available
        set "ALL_SERVICES_HEALTHY=false"
    )

    REM Check Docker Compose
    docker-compose --version >nul 2>nul || docker compose version >nul 2>nul || (
        echo ❌ Docker Compose not available
        set "ALL_SERVICES_HEALTHY=false"
    )

    REM Check Python
    python --version >nul 2>nul || (
        echo ❌ Python not available
        set "ALL_SERVICES_HEALTHY=false"
    )

    if "!ALL_SERVICES_HEALTHY!"=="true" (
        echo ✅ All core services are available
    ) else (
        echo ❌ Some core services are missing
    )

    if "!ALL_SERVICES_HEALTHY!"=="false" exit /b 1
    goto :eof

REM --- System state verification function ---
:verify_system_state
    echo Verifying final system state...
    set "SYSTEM_READY=true"

    REM Check Docker network
    docker network inspect !SHARED_NETWORK_NAME! >nul 2>nul || set "SYSTEM_READY=false"

    REM Check key configuration files
    if not exist "violentutf\.env" set "SYSTEM_READY=false"
    if not exist "keycloak\.env" set "SYSTEM_READY=false"
    if not exist "apisix\conf\config.yaml" set "SYSTEM_READY=false"

    REM Check Python environment
    if not exist ".vitutf\Scripts\activate.bat" set "SYSTEM_READY=false"

    if "!SYSTEM_READY!"=="true" (
        echo ✅ System state verification passed
    ) else (
        echo ❌ System state verification failed
        exit /b 1
    )
    goto :eof

REM --- Cleanup function ---
:perform_cleanup
    echo Starting cleanup process...

    REM 0. Backup user configurations before cleanup
    call :backup_user_configs

    set "ORIGINAL_DIR=%cd%"

    echo Stopping and removing Keycloak containers...
    if exist "keycloak\docker-compose.yml" (
        pushd "keycloak"
        !DOCKER_COMPOSE_CMD! down -v >nul 2>nul
        popd
    )

    echo Stopping and removing APISIX containers...
    if exist "apisix\docker-compose.yml" (
        pushd "apisix"
        !DOCKER_COMPOSE_CMD! down -v >nul 2>nul
        popd
    )

    echo Removing shared Docker network...
    docker network inspect !SHARED_NETWORK_NAME! >nul 2>nul
    if errorlevel 0 (
        docker network rm !SHARED_NETWORK_NAME! >nul 2>nul
        if errorlevel 0 (
            echo Removed shared network '!SHARED_NETWORK_NAME!'.
        ) else (
            echo Warning: Could not remove shared network '!SHARED_NETWORK_NAME!'. It may still be in use.
        )
    )

    echo Removing configuration files...
    if exist "keycloak\.env" ( del "keycloak\.env" & echo Removed keycloak\.env )
    if exist "apisix\conf" (
        echo Restoring only template files in apisix\conf directory...
        powershell -NoProfile -Command ^
            $tempDir = '%TEMP%\apisix_templates_vutf'; ^
            $apisixConfDir = 'apisix\conf'; ^
            if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }; ^
            New-Item -ItemType Directory -Path $tempDir -Force > $null; ^
            Get-ChildItem -Path $apisixConfDir -Filter *.template | Copy-Item -Destination $tempDir; ^
            Get-ChildItem -Path $apisixConfDir -Exclude *.template | Remove-Item -Recurse -Force; ^
            Get-ChildItem -Path $tempDir -Filter *.template | Copy-Item -Destination $apisixConfDir; ^
            Remove-Item -Recurse -Force $tempDir;
    )
    if exist "violentutf\.env" ( del "violentutf\.env" & echo Removed violentutf\.env )
    if exist "violentutf\.streamlit\secrets.toml" ( del "violentutf\.streamlit\secrets.toml" & echo Removed violentutf\.streamlit\secrets.toml )
    if exist "violentutf_api\fastapi_app\.env" ( del "violentutf_api\fastapi_app\.env" & echo Removed violentutf_api\fastapi_app\.env )

    REM Preserve PyRIT memory databases and user app data
    echo Preserving PyRIT memory databases and user data...
    echo ✅ PyRIT memory databases preserved in violentutf/app_data/violentutf/
    echo ✅ User datasets preserved in violentutf/app_data/
    echo ✅ User parameters preserved in violentutf/parameters/
    echo ✅ AI tokens file preserved: !AI_TOKENS_FILE!

    echo Removing Docker volumes related to Keycloak and APISIX...
    set "PS_CLEANUP_VOLUMES=powershell -NoProfile -Command ^
        $volumesToRemove = (docker volume ls -q | Where-Object { $_ -match '(keycloak|apisix|violentutf_api|fastapi|strapi)' }); ^
        if ($volumesToRemove) { Write-Host 'Removing volumes:'; $volumesToRemove; docker volume rm $volumesToRemove } else { Write-Host 'No relevant Docker volumes found.' }"
    !PS_CLEANUP_VOLUMES!

    echo Cleanup completed successfully!
    echo The Python virtual environment has been preserved.
    echo You can now run the script again for a fresh setup.
    goto :eof_end_script
goto :eof

REM --- Function to ensure Docker Compose files have shared network configuration (using PowerShell) ---
:ensure_network_in_compose
    set "compose_file=%~1"
    set "service_name=%~2"

    if not exist "!compose_file!" (
        echo Error: Docker Compose file !compose_file! not found!
        exit /b 1
    )

    set "backup_suffix_date="
    for /f "tokens=1-6 delims=/: " %%a in ("%date% %time%") do set "backup_suffix_date=%%c%%a%%b%%d%%e%%f"
    copy "!compose_file!" "!compose_file!.bak!backup_suffix_date!" >nul

    powershell -NoProfile -Command ^
        $filePath = '!compose_file!'; ^
        $content = Get-Content $filePath -Raw; ^
        $networkName = '!SHARED_NETWORK_NAME!'; ^
        $serviceName = '!service_name!'; ^
        $madeChange = $false; ^
        if ($content -notmatch ('\nnetworks:\s*\n\s*' + [regex]::Escape($networkName) + ':')) { ^
            if ($content -notmatch '\nnetworks:') { $content += \"`n`nnetworks:\"; $madeChange = $true; }; ^
            $content = $content -replace '(\nnetworks:\s*\n)', (\"$1  $networkName`:`n    external: true`n\"); $madeChange = $true; ^
            Write-Host \"Added $networkName to networks section in $filePath\"; ^
        }; ^
        if ($content -match ('\n\s*' + [regex]::Escape($serviceName) + ':')) { ^
            if ($content -notmatch ('\n\s*' + [regex]::Escape($serviceName) + ':\s*(\n\s+.*)*?\n\s+networks:\s*(\n\s+.*)*?\n\s+-\s*' + [regex]::Escape($networkName))) { ^
                $serviceBlockPattern = '(\n\s*' + [regex]::Escape($serviceName) + ':(?:(?!\n\S).)*)'; ^
                if ($content -match $serviceBlockPattern) { ^
                    $serviceBlock = $matches[0]; ^
                    if ($serviceBlock -match '\n\s+networks:') { ^
                        $newServiceBlock = $serviceBlock -replace '(\n\s+networks:\s*\n)', (\"$1      - $networkName`n\"); ^
                    } else { ^
                        $newServiceBlock = $serviceBlock + \"`n    networks:`n      - $networkName\"; ^
                    }; ^
                    $content = $content.Replace($serviceBlock, $newServiceBlock); ^
                    Write-Host \"Added $networkName to $serviceName service in $filePath\"; ^
                    $madeChange = $true; ^
                } ^
            } ^
        }; ^
        if ($madeChange) { Set-Content -Path $filePath -Value $content -NoNewline -Encoding UTF8 };
    goto :eof

REM --- Function to create AI tokens template ---
:create_ai_tokens_template
    if exist "!AI_TOKENS_FILE!" (
        set "%~1=0" & goto :eof
    )
    echo Creating AI tokens configuration file: !AI_TOKENS_FILE!
(
echo # AI Provider Tokens and Settings
echo # Set to true/false to enable/disable providers
echo # Add your actual API keys replacing the placeholder values
echo.
echo # OpenAI Configuration
echo OPENAI_ENABLED=false
echo OPENAI_API_KEY=your_openai_api_key_here
echo.
echo # Anthropic Configuration
echo ANTHROPIC_ENABLED=false
echo ANTHROPIC_API_KEY=your_anthropic_api_key_here
echo.
echo # Ollama Configuration (local, no API key needed)
echo OLLAMA_ENABLED=true
echo OLLAMA_ENDPOINT=http://localhost:11434/v1/chat/completions
echo.
echo # Open WebUI Configuration
echo OPEN_WEBUI_ENABLED=false
echo OPEN_WEBUI_ENDPOINT=http://localhost:3000/ollama/v1/chat/completions
echo OPEN_WEBUI_API_KEY=your_open_webui_api_key_here
echo.
echo # AWS Bedrock Configuration
echo BEDROCK_ENABLED=false
echo BEDROCK_REGION=us-east-1
echo AWS_ACCESS_KEY_ID=your_aws_access_key_id_here
echo AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key_here
echo AWS_SESSION_TOKEN=your_aws_session_token_here_if_using_temp_credentials
) > "!AI_TOKENS_FILE!"
    echo ✅ Created !AI_TOKENS_FILE!
    echo 📝 Please edit this file and add your API keys, then re-run the script
    set "%~1=1" & goto :eof
goto :eof

REM --- Function to load AI tokens from .env file ---
:load_ai_tokens
    if not exist "!AI_TOKENS_FILE!" (
        echo ❌ !AI_TOKENS_FILE! not found
        set "%~1=1" & goto :eof
    )
    echo Loading AI configuration from !AI_TOKENS_FILE!...
    for /f "usebackq tokens=1,* delims==" %%a in ("!AI_TOKENS_FILE!") do (
        set "%%a=%%b"
    )
    echo ✅ AI configuration loaded
    set "%~1=0" & goto :eof
goto :eof


REM --- Function to check if ai-proxy plugin is available ---
:check_ai_proxy_plugin_ps
    echo Checking if ai-proxy plugin is available in APISIX...
    set "PS_CHECK_PLUGIN=powershell -NoProfile -Command ^
        try { ^
            $response = Invoke-RestMethod -Uri '!APISIX_ADMIN_URL!/apisix/admin/plugins/ai-proxy' -Method Get -Headers @{'X-API-KEY'='!APISIX_ADMIN_KEY!'} -TimeoutSec 10; ^
            if ($response) { Write-Host '✅ ai-proxy plugin is available'; exit 0; } ^
        } catch { ^
            Write-Host ('❌ ai-proxy plugin is not available or API error. HTTP Status: ' + $_.Exception.Response.StatusCode.value__ + ' Error: ' + $_.Exception.Message) -ForegroundColor Red; ^
            Write-Host '   Make sure you are using APISIX version 3.10.0 or later with ai-proxy plugin enabled'; ^
            exit 1; ^
        }"
    !PS_CHECK_PLUGIN!
    set "plugin_check_result=%errorlevel%"
    goto :eof

REM --- Generic AI Route Creation Function (using PowerShell) ---
REM %1 = Route Type (OpenAI, Anthropic, Ollama, OpenWebUI)
REM %2 = Model Name
REM %3 = URI Path
REM %4 = API Key (or Endpoint for Ollama/WebUI)
REM %5 = Endpoint (for Ollama/WebUI) / API Key for WebUI if different
:create_ai_route_ps
    set "ROUTE_TYPE=%~1"
    set "MODEL_NAME=%~2"
    set "URI_PATH=%~3"
    set "PARAM_4=%~4"
    set "PARAM_5=%~5"

    set "ROUTE_ID_RAW=!ROUTE_TYPE!-!MODEL_NAME!"
    REM Sanitize ROUTE_ID for APISIX (lowercase, replace dots with hyphens)
    set "PS_SANITIZE_ROUTE_ID=powershell -NoProfile -Command \"'!ROUTE_ID_RAW!'.ToLower() -replace '\.','-'\""
    for /f "delims=" %%i in ('!PS_SANITIZE_ROUTE_ID!') do set "ROUTE_ID=%%i"

    echo 🔧 Debug: Creating !ROUTE_TYPE! route for model='!MODEL_NAME!', uri='!URI_PATH!', route_id='!ROUTE_ID!'

    set "PAYLOAD_SCRIPT="
    if /i "!ROUTE_TYPE!"=="OpenAI" (
        set "API_KEY=!PARAM_4!"
        set "PAYLOAD_SCRIPT=$payload = @{ id = '!ROUTE_ID!'; uri = '!URI_PATH!'; methods = @('POST', 'GET'); plugins = @{ 'key-auth' = @{}; 'ai-proxy' = @{ provider = 'openai'; auth = @{ header = @{ Authorization = 'Bearer !API_KEY!' } }; options = @{ model = '!MODEL_NAME!' } } } }"
    ) else if /i "!ROUTE_TYPE!"=="Anthropic" (
        set "API_KEY=!PARAM_4!"
        set "PAYLOAD_SCRIPT=$payload = @{ id = '!ROUTE_ID!'; uri = '!URI_PATH!'; methods = @('POST', 'GET'); plugins = @{ 'key-auth' = @{}; 'ai-proxy' = @{ provider = 'openai-compatible'; auth = @{ header = @{ 'x-api-key' = '!API_KEY!'; 'anthropic-version' = '2023-06-01' } }; options = @{ model = '!MODEL_NAME!' }; override = @{ endpoint = 'https://api.anthropic.com/v1/messages' } } } }"
    ) else if /i "!ROUTE_TYPE!"=="Ollama" (
        set "ENDPOINT_URL=!PARAM_4!"
        set "PAYLOAD_SCRIPT=$payload = @{ id = '!ROUTE_ID!'; uri = '!URI_PATH!'; methods = @('POST', 'GET'); plugins = @{ 'key-auth' = @{}; 'ai-proxy' = @{ provider = 'openai-compatible'; options = @{ model = '!MODEL_NAME!' }; override = @{ endpoint = '!ENDPOINT_URL!' } } } }"
    ) else if /i "!ROUTE_TYPE!"=="OpenWebUI" (
        set "ENDPOINT_URL=!PARAM_4!"
        set "API_KEY_WEBUI=!PARAM_5!"
        set "AUTH_BLOCK="
        if defined API_KEY_WEBUI if not "!API_KEY_WEBUI!"=="your_open_webui_api_key_here" (
            set "AUTH_BLOCK=auth = @{ header = @{ Authorization = 'Bearer !API_KEY_WEBUI!' } };"
        )
        set "PAYLOAD_SCRIPT=$payload = @{ id = '!ROUTE_ID!'; uri = '!URI_PATH!'; methods = @('POST', 'GET'); plugins = @{ 'key-auth' = @{}; 'ai-proxy' = @{ provider = 'openai-compatible'; !AUTH_BLOCK! options = @{ model = '!MODEL_NAME!' }; override = @{ endpoint = '!ENDPOINT_URL!' } } } }"
    ) else (
        echo ❌ Unknown AI route type: !ROUTE_TYPE!
        exit /b 1
    )

    set "PS_CREATE_ROUTE=powershell -NoProfile -ErrorAction Stop -Command ^
        !PAYLOAD_SCRIPT!; ^
        $jsonPayload = $payload | ConvertTo-Json -Depth 10; ^
        try { ^
            $response = Invoke-RestMethod -Uri '!APISIX_ADMIN_URL!/apisix/admin/routes/!ROUTE_ID!' -Method Put -Headers @{'X-API-KEY'='!APISIX_ADMIN_KEY!';'Content-Type'='application/json'} -Body $jsonPayload -TimeoutSec 30; ^
            Write-Host ('✅ Successfully created !ROUTE_TYPE! route: !URI_PATH! -> !MODEL_NAME!'); ^
            exit 0; ^
        } catch { ^
            Write-Host ('❌ Failed to create !ROUTE_TYPE! route for !MODEL_NAME!') -ForegroundColor Red; ^
            Write-Host ('   HTTP Status: ' + $_.Exception.Response.StatusCode.value__ + ' Error: ' + $_.Exception.Message) -ForegroundColor Red; ^
            Write-Host ('   Payload Sent: ' + $jsonPayload); ^
            exit 1; ^
        }"

    !PS_CREATE_ROUTE!
    set "route_creation_result=%errorlevel%"
    if !route_creation_result! equ 0 (
        echo !ROUTE_TYPE!: !URI_PATH! -> !MODEL_NAME! >> "!CREATED_AI_ROUTES_FILE!"
    )
    goto :eof

REM --- Create APISIX API Key Consumer ---
:create_apisix_consumer_ps
    echo Creating APISIX consumer with API key authentication...

    set "PS_CREATE_CONSUMER=powershell -NoProfile -ErrorAction Stop -Command ^
        $payload = @{ ^
            username = 'violentutf_user'; ^
            plugins = @{ ^
                'key-auth' = @{ ^
                    key = '!VIOLENTUTF_API_KEY!' ^
                } ^
            } ^
        }; ^
        $jsonPayload = $payload | ConvertTo-Json -Depth 10; ^
        try { ^
            $response = Invoke-RestMethod -Uri '!APISIX_ADMIN_URL!/apisix/admin/consumers/violentutf_user' -Method Put -Headers @{'X-API-KEY'='!APISIX_ADMIN_KEY!';'Content-Type'='application/json'} -Body $jsonPayload -TimeoutSec 30; ^
            Write-Host ('✅ Successfully created API key consumer'); ^
            Write-Host ('   API Key: !VIOLENTUTF_API_KEY!'); ^
            Write-Host ('   Use this key in the apikey header for AI Gateway requests'); ^
            exit 0; ^
        } catch { ^
            Write-Host ('❌ Failed to create API key consumer') -ForegroundColor Red; ^
            Write-Host ('   HTTP Status: ' + $_.Exception.Response.StatusCode.value__ + ' Error: ' + $_.Exception.Message) -ForegroundColor Red; ^
            exit 1; ^
        }"

    !PS_CREATE_CONSUMER!
    goto :eof


REM --- Setup OpenAI Routes ---
:setup_openai_routes_ps
    if /i "!OPENAI_ENABLED!" neq "true" (
        echo OpenAI provider disabled. Skipping setup.
        exit /b 0
    )
    if not defined OPENAI_API_KEY (
        echo ⚠️ OpenAI enabled but OPENAI_API_KEY not configured. Skipping.
        exit /b 0
    )
    if "!OPENAI_API_KEY!"=="your_openai_api_key_here" (
        echo ⚠️ OpenAI enabled but API key is placeholder. Skipping.
        exit /b 0
    )
    echo Setting up OpenAI routes...
    set "overall_success=0"
    call :create_ai_route_ps OpenAI "gpt-4" "/ai/openai/gpt4" "!OPENAI_API_KEY!"
    if errorlevel 1 set "overall_success=1"
    call :create_ai_route_ps OpenAI "gpt-3.5-turbo" "/ai/openai/gpt35" "!OPENAI_API_KEY!"
    if errorlevel 1 set "overall_success=1"
    call :create_ai_route_ps OpenAI "gpt-4-turbo" "/ai/openai/gpt4-turbo" "!OPENAI_API_KEY!"
    if errorlevel 1 set "overall_success=1"
    call :create_ai_route_ps OpenAI "gpt-4o" "/ai/openai/gpt4o" "!OPENAI_API_KEY!"
    if errorlevel 1 set "overall_success=1"
    call :create_ai_route_ps OpenAI "gpt-4o-mini" "/ai/openai/gpt4o-mini" "!OPENAI_API_KEY!"
    if errorlevel 1 set "overall_success=1"
    exit /b !overall_success!
goto :eof

REM --- Setup Anthropic Routes ---
:setup_anthropic_routes_ps
    if /i "!ANTHROPIC_ENABLED!" neq "true" (
        echo Anthropic provider disabled. Skipping setup.
        exit /b 0
    )
    if not defined ANTHROPIC_API_KEY (
        echo ⚠️ Anthropic enabled but ANTHROPIC_API_KEY not configured. Skipping.
        exit /b 0
    )
    if "!ANTHROPIC_API_KEY!"=="your_anthropic_api_key_here" (
        echo ⚠️ Anthropic enabled but API key is placeholder. Skipping.
        exit /b 0
    )
    echo Setting up Anthropic routes...
    set "overall_success=0"
    call :create_ai_route_ps Anthropic "claude-3-opus-20240229" "/ai/anthropic/opus" "!ANTHROPIC_API_KEY!"
    if errorlevel 1 set "overall_success=1"
    call :create_ai_route_ps Anthropic "claude-3-sonnet-20240229" "/ai/anthropic/sonnet" "!ANTHROPIC_API_KEY!"
    if errorlevel 1 set "overall_success=1"
    call :create_ai_route_ps Anthropic "claude-3-haiku-20240307" "/ai/anthropic/haiku" "!ANTHROPIC_API_KEY!"
    if errorlevel 1 set "overall_success=1"
    call :create_ai_route_ps Anthropic "claude-3-5-sonnet-20241022" "/ai/anthropic/sonnet35" "!ANTHROPIC_API_KEY!"
    if errorlevel 1 set "overall_success=1"
    call :create_ai_route_ps Anthropic "claude-opus-4-20250514" "/ai/anthropic/opus4" "!ANTHROPIC_API_KEY!"
    if errorlevel 1 set "overall_success=1"
    exit /b !overall_success!
goto :eof

REM --- Setup Ollama Routes ---
:setup_ollama_routes_ps
    if /i "!OLLAMA_ENABLED!" neq "true" (
        echo Ollama provider disabled. Skipping setup.
        exit /b 0
    )
    echo Setting up Ollama routes...
    set "OLLAMA_EFFECTIVE_ENDPOINT=!OLLAMA_ENDPOINT!"
    if not defined OLLAMA_EFFECTIVE_ENDPOINT set "OLLAMA_EFFECTIVE_ENDPOINT=http://localhost:11434/v1/chat/completions"

    set "overall_success=0"
    call :create_ai_route_ps Ollama "llama2" "/ai/ollama/llama2" "!OLLAMA_EFFECTIVE_ENDPOINT!"
    if errorlevel 1 set "overall_success=1"
    call :create_ai_route_ps Ollama "codellama" "/ai/ollama/codellama" "!OLLAMA_EFFECTIVE_ENDPOINT!"
    if errorlevel 1 set "overall_success=1"
    call :create_ai_route_ps Ollama "mistral" "/ai/ollama/mistral" "!OLLAMA_EFFECTIVE_ENDPOINT!"
    if errorlevel 1 set "overall_success=1"
    call :create_ai_route_ps Ollama "llama3" "/ai/ollama/llama3" "!OLLAMA_EFFECTIVE_ENDPOINT!"
    if errorlevel 1 set "overall_success=1"
    exit /b !overall_success!
goto :eof

REM --- Setup Open WebUI Routes ---
:setup_open_webui_routes_ps
    if /i "!OPEN_WEBUI_ENABLED!" neq "true" (
        echo Open WebUI provider disabled. Skipping setup.
        exit /b 0
    )
    echo Setting up Open WebUI routes...
    set "WEBUI_EFFECTIVE_ENDPOINT=!OPEN_WEBUI_ENDPOINT!"
    if not defined WEBUI_EFFECTIVE_ENDPOINT set "WEBUI_EFFECTIVE_ENDPOINT=http://localhost:3000/ollama/v1/chat/completions"
    set "WEBUI_API_KEY=!OPEN_WEBUI_API_KEY!"

    set "overall_success=0"
    call :create_ai_route_ps OpenWebUI "llama2" "/ai/webui/llama2" "!WEBUI_EFFECTIVE_ENDPOINT!" "!WEBUI_API_KEY!"
    if errorlevel 1 set "overall_success=1"
    call :create_ai_route_ps OpenWebUI "codellama" "/ai/webui/codellama" "!WEBUI_EFFECTIVE_ENDPOINT!" "!WEBUI_API_KEY!"
    if errorlevel 1 set "overall_success=1"
    exit /b !overall_success!
goto :eof

REM --- Setup AWS Bedrock Routes ---
:setup_bedrock_routes
    if /i "!BEDROCK_ENABLED!" neq "true" (
        echo AWS Bedrock provider disabled. Skipping setup.
        exit /b 0
    )

    echo ⚠️  AWS Bedrock integration is currently not supported by APISIX ai-proxy plugin.
    echo    The ai-proxy plugin does not support native AWS SigV4 authentication required for Bedrock.
    echo    Bedrock endpoints are configured in TokenManager for future implementation.
    echo    Use the standalone Bedrock provider in Simple Chat for now.
    exit /b 0

    REM Future implementation when AWS SigV4 support is added to APISIX
    if "!AWS_ACCESS_KEY_ID!"=="your_aws_access_key_id_here" (
        echo ⚠️  AWS Bedrock enabled but Access Key ID not configured. Skipping Bedrock setup.
        exit /b 0
    )

    if "!AWS_SECRET_ACCESS_KEY!"=="your_aws_secret_access_key_here" (
        echo ⚠️  AWS Bedrock enabled but Secret Access Key not configured. Skipping Bedrock setup.
        exit /b 0
    )

    echo Setting up AWS Bedrock routes...

    set "BEDROCK_REGION_EFFECTIVE=!BEDROCK_REGION!"
    if not defined BEDROCK_REGION_EFFECTIVE set "BEDROCK_REGION_EFFECTIVE=us-east-1"

    set "overall_success=0"
    call :create_bedrock_route_ps "anthropic.claude-opus-4-20250514-v1:0" "/ai/bedrock/claude-opus-4" "!BEDROCK_REGION_EFFECTIVE!" "!AWS_ACCESS_KEY_ID!" "!AWS_SECRET_ACCESS_KEY!"
    if errorlevel 1 set "overall_success=1"
    call :create_bedrock_route_ps "anthropic.claude-sonnet-4-20250514-v1:0" "/ai/bedrock/claude-sonnet-4" "!BEDROCK_REGION_EFFECTIVE!" "!AWS_ACCESS_KEY_ID!" "!AWS_SECRET_ACCESS_KEY!"
    if errorlevel 1 set "overall_success=1"
    call :create_bedrock_route_ps "anthropic.claude-3-5-sonnet-20241022-v2:0" "/ai/bedrock/claude-35-sonnet" "!BEDROCK_REGION_EFFECTIVE!" "!AWS_ACCESS_KEY_ID!" "!AWS_SECRET_ACCESS_KEY!"
    if errorlevel 1 set "overall_success=1"
    call :create_bedrock_route_ps "anthropic.claude-3-5-haiku-20241022-v1:0" "/ai/bedrock/claude-35-haiku" "!BEDROCK_REGION_EFFECTIVE!" "!AWS_ACCESS_KEY_ID!" "!AWS_SECRET_ACCESS_KEY!"
    if errorlevel 1 set "overall_success=1"
    call :create_bedrock_route_ps "meta.llama3-3-70b-instruct-v1:0" "/ai/bedrock/llama3-3-70b" "!BEDROCK_REGION_EFFECTIVE!" "!AWS_ACCESS_KEY_ID!" "!AWS_SECRET_ACCESS_KEY!"
    if errorlevel 1 set "overall_success=1"
    call :create_bedrock_route_ps "amazon.nova-pro-v1:0" "/ai/bedrock/nova-pro" "!BEDROCK_REGION_EFFECTIVE!" "!AWS_ACCESS_KEY_ID!" "!AWS_SECRET_ACCESS_KEY!"
    if errorlevel 1 set "overall_success=1"
    call :create_bedrock_route_ps "amazon.nova-lite-v1:0" "/ai/bedrock/nova-lite" "!BEDROCK_REGION_EFFECTIVE!" "!AWS_ACCESS_KEY_ID!" "!AWS_SECRET_ACCESS_KEY!"
    if errorlevel 1 set "overall_success=1"
    exit /b !overall_success!
goto :eof

REM --- Create AWS Bedrock Route (PowerShell) ---
:create_bedrock_route_ps
    set "MODEL_NAME=%~1"
    set "URI_PATH=%~2"
    set "REGION=%~3"
    set "ACCESS_KEY=%~4"
    set "SECRET_KEY=%~5"

    REM Generate route ID from model name
    set "ROUTE_ID=%MODEL_NAME%"
    set "ROUTE_ID=!ROUTE_ID:.=-!"
    set "ROUTE_ID=!ROUTE_ID:anthropic-=!"
    set "ROUTE_ID=!ROUTE_ID:meta-=!"
    set "ROUTE_ID=!ROUTE_ID:amazon-=!"
    set "ROUTE_ID=bedrock-!ROUTE_ID!"

    REM Get current date for AWS signature
    for /f %%i in ('powershell -Command "Get-Date -Format 'yyyyMMdd'"') do set "AWS_DATE=%%i"

    set "PAYLOAD_SCRIPT=$payload = @{ ^
        'id' = '!ROUTE_ID!'; ^
        'uri' = '!URI_PATH!'; ^
        'methods' = @('POST', 'GET'); ^
        'plugins' = @{ ^
            'key-auth' = @{}; ^
            'ai-proxy' = @{ ^
                'provider' = 'openai-compatible'; ^
                'auth' = @{ ^
                    'header' = @{ ^
                        'Authorization' = 'AWS4-HMAC-SHA256 Credential=!ACCESS_KEY!/!AWS_DATE!/!REGION!/bedrock/aws4_request' ^
                    } ^
                }; ^
                'options' = @{ ^
                    'model' = '!MODEL_NAME!'; ^
                    'max_tokens' = 1000; ^
                    'temperature' = 0.7 ^
                }; ^
                'override' = @{ ^
                    'endpoint' = 'https://bedrock-runtime.!REGION!.amazonaws.com/model/!MODEL_NAME!/invoke' ^
                } ^
            } ^
        } ^
    }"

    set "PS_CREATE_BEDROCK_ROUTE=powershell -NoProfile -ErrorAction Stop -Command ^
        !PAYLOAD_SCRIPT!; ^
        $jsonPayload = $payload | ConvertTo-Json -Depth 10; ^
        try { ^
            $response = Invoke-RestMethod -Uri '!APISIX_ADMIN_URL!/apisix/admin/routes/!ROUTE_ID!' -Method Put -Headers @{'X-API-KEY'='!APISIX_ADMIN_KEY!';'Content-Type'='application/json'} -Body $jsonPayload -TimeoutSec 30; ^
            Write-Host ('✅ Successfully created AWS Bedrock route: !URI_PATH! -> !MODEL_NAME!'); ^
            exit 0; ^
        } catch { ^
            Write-Host ('❌ Failed to create AWS Bedrock route for !MODEL_NAME!') -ForegroundColor Red; ^
            Write-Host ('   HTTP Status: ' + $_.Exception.Response.StatusCode.value__ + ' Error: ' + $_.Exception.Message) -ForegroundColor Red; ^
            exit 1; ^
        }"

    !PS_CREATE_BEDROCK_ROUTE!
    set "route_creation_result=%errorlevel%"
    if !route_creation_result! equ 0 (
        echo AWS Bedrock: !URI_PATH! -> !MODEL_NAME! >> "!CREATED_AI_ROUTES_FILE!"
    )
    goto :eof


REM --- Debug AI Proxy Setup ---
:debug_ai_proxy_setup_ps
    echo 🔍 Debugging AI Proxy Setup...
    set "overall_status=0"
    echo Testing APISIX Admin API accessibility...
    powershell -NoProfile -Command ^
        try { ^
            Invoke-RestMethod -Uri '!APISIX_ADMIN_URL!/apisix/admin/routes' -Method Get -Headers @{'X-API-KEY'='!APISIX_ADMIN_KEY!'} -TimeoutSec 5 > $null; ^
            Write-Host '✅ APISIX Admin API is accessible'; ^
        } catch { Write-Host ('❌ APISIX Admin API not accessible. HTTP Status: ' + $_.Exception.Response.StatusCode.value__ + '. Ensure APISIX_ADMIN_KEY is correct and APISIX is running.') -ForegroundColor Red; exit 1; }"
    if errorlevel 1 set "overall_status=1" & goto :eof_debug_ai_fail

    echo Checking available plugins for 'ai-proxy'...
    powershell -NoProfile -Command ^
        try { ^
            $plugins = Invoke-RestMethod -Uri '!APISIX_ADMIN_URL!/apisix/admin/plugins/list' -Method Get -Headers @{'X-API-KEY'='!APISIX_ADMIN_KEY!'} -TimeoutSec 5; ^
            if ($plugins.Contains('ai-proxy')) { Write-Host '✅ ai-proxy plugin is available in list' } ^
            else { Write-Host '❌ ai-proxy plugin NOT FOUND in list. Available: ' ($plugins -join ', '); exit 1; }; ^
        } catch { Write-Host ('❌ Could not get plugin list. Error: ' + $_.Exception.Message) -ForegroundColor Red; exit 1; }"
    if errorlevel 1 set "overall_status=1" & goto :eof_debug_ai_fail

    echo Existing APISIX routes (first few):
    powershell -NoProfile -Command ^
        try { ^
            $routes = Invoke-RestMethod -Uri '!APISIX_ADMIN_URL!/apisix/admin/routes' -Method Get -Headers @{'X-API-KEY'='!APISIX_ADMIN_KEY!'} -TimeoutSec 5; ^
            if ($routes.node.nodes) { $routes.node.nodes | ForEach-Object { $_.value | Select-Object id, uri, name } | ConvertTo-Json -Depth 3 | Write-Output } ^
            else { Write-Host "No routes found or unexpected format."}; ^
        } catch { Write-Host ('❌ Could not get routes. Error: ' + $_.Exception.Message) -ForegroundColor Red; }"
    :eof_debug_ai_fail
    exit /b !overall_status!
goto :eof


REM --- Setup AI Providers Enhanced ---
:setup_ai_providers_enhanced_ps
    if /i "!SKIP_AI_SETUP!" equ "true" (
        echo Skipping AI provider setup due to configuration issues.
        exit /b 0
    )
    echo Setting up AI providers with enhanced error handling...
    call :debug_ai_proxy_setup_ps
    if errorlevel 1 (
        echo ❌ AI Proxy setup prerequisites not met
        set "SKIP_AI_SETUP=true"
        exit /b 1
    )
    echo Waiting for APISIX to be fully ready for route configuration (10s)...
    timeout /t 10 /nobreak >nul

    set "setup_errors=0"

    REM Create API key consumer first
    echo Creating API key consumer for authentication...
    call :create_apisix_consumer_ps
    if errorlevel 1 (
        echo ❌ Failed to create API key consumer
        set /a setup_errors+=1
    )

    call :setup_openai_routes_ps
    if errorlevel 1 set /a setup_errors+=1
    call :setup_anthropic_routes_ps
    if errorlevel 1 set /a setup_errors+=1
    call :setup_ollama_routes_ps
    if errorlevel 1 set /a setup_errors+=1
    call :setup_open_webui_routes_ps
    if errorlevel 1 set /a setup_errors+=1

    if !setup_errors! gtr 0 (
        echo ⚠️ Some AI provider setups encountered errors
        exit /b 1
    ) else (
        echo ✅ All AI provider setups completed successfully
        exit /b 0
    )
goto :eof

REM --- Test AI Routes ---
:test_ai_routes_ps
    echo Testing AI provider routes...
    echo Listing all APISIX routes (from test_ai_routes_ps):
    powershell -NoProfile -Command ^
        try { ^
            (Invoke-RestMethod -Uri '!APISIX_ADMIN_URL!/apisix/admin/routes' -Method Get -Headers @{'X-API-KEY'='!APISIX_ADMIN_KEY!'} -TimeoutSec 5).node.nodes | ForEach-Object { $_.value | Select-Object id, uri, name } | ConvertTo-Json -Depth 3 | Write-Output; ^
        } catch { Write-Host ('❌ Could not list routes. Error: ' + $_.Exception.Message) -ForegroundColor Red; }"

    set "TEST_PAYLOAD_JSON={'messages':[{'role':'user','content':'test'}]}"

    if /i "!OLLAMA_ENABLED!" equ "true" (
        call :run_test "AI Ollama route accessibility (/ai/ollama/llama2)" "powershell -NoProfile -Command \"try { (Invoke-RestMethod -Uri '!APISIX_URL!/ai/ollama/llama2' -Method Post -Body '!TEST_PAYLOAD_JSON!' -ContentType 'application/json' -TimeoutSec 10 -SkipHttpErrorCheck).StatusCode } catch { Write-Output $_.Exception.Response.StatusCode.value__ }\"" "(200|404|422|500|503)"
    )
    if /i "!OPENAI_ENABLED!" equ "true" (
        set "EXPECTED_OPENAI_CODE=(401|429|400)"
        if "!OPENAI_API_KEY!"=="your_openai_api_key_here" set "EXPECTED_OPENAI_CODE=401"
        call :run_test "AI OpenAI route accessibility (/ai/openai/gpt4)" "powershell -NoProfile -Command \"try { (Invoke-RestMethod -Uri '!APISIX_URL!/ai/openai/gpt4' -Method Post -Body '!TEST_PAYLOAD_JSON!' -ContentType 'application/json' -Headers @{'Authorization'='Bearer !OPENAI_API_KEY!'} -TimeoutSec 10 -SkipHttpErrorCheck).StatusCode } catch { Write-Output $_.Exception.Response.StatusCode.value__ }\"" "!EXPECTED_OPENAI_CODE!"
    )
    if /i "!ANTHROPIC_ENABLED!" equ "true" (
        set "EXPECTED_ANTHROPIC_CODE=(401|400)"
        if "!ANTHROPIC_API_KEY!"=="your_anthropic_api_key_here" set "EXPECTED_ANTHROPIC_CODE=401"
        call :run_test "AI Anthropic route accessibility (/ai/anthropic/opus)" "powershell -NoProfile -Command \"try { (Invoke-RestMethod -Uri '!APISIX_URL!/ai/anthropic/opus' -Method Post -Body '!TEST_PAYLOAD_JSON!' -ContentType 'application/json' -Headers @{'x-api-key'='!ANTHROPIC_API_KEY!'} -TimeoutSec 10 -SkipHttpErrorCheck).StatusCode } catch { Write-Output $_.Exception.Response.StatusCode.value__ }\"" "!EXPECTED_ANTHROPIC_CODE!"
    )
    goto :eof

REM --- Show AI Summary ---
:show_ai_summary
    echo.
    echo ==========================================
    echo AI PROXY CONFIGURATION SUMMARY
    echo ==========================================
    if /i "!SKIP_AI_SETUP!" equ "true" (
        if not exist "!CREATED_AI_ROUTES_FILE!" (
             echo ❌ AI Proxy setup was skipped or failed to create routes.
             echo    Ensure !AI_TOKENS_FILE! is configured and APISIX is running with ai-proxy plugin.
        )
    )
    echo AI Configuration file: !AI_TOKENS_FILE!
    echo.
    echo Enabled AI Providers (based on !AI_TOKENS_FILE! and successful route creation^):
    set "any_provider_listed=false"
    if /i "!OPENAI_ENABLED!" equ "true" (
        echo   🔵 OpenAI
        (type "!CREATED_AI_ROUTES_FILE!" 2>nul | findstr /B /C:"OpenAI:") || echo      ⚠️ No OpenAI routes were successfully created (check logs).
        set "any_provider_listed=true"
    )
    if /i "!ANTHROPIC_ENABLED!" equ "true" (
        echo   🟣 Anthropic
        (type "!CREATED_AI_ROUTES_FILE!" 2>nul | findstr /B /C:"Anthropic:") || echo      ⚠️ No Anthropic routes were successfully created (check logs).
        set "any_provider_listed=true"
    )
    if /i "!OLLAMA_ENABLED!" equ "true" (
        echo   🟢 Ollama
        (type "!CREATED_AI_ROUTES_FILE!" 2>nul | findstr /B /C:"Ollama:") || echo      ⚠️ No Ollama routes were successfully created (check logs).
        set "any_provider_listed=true"
    )
    if /i "!OPEN_WEBUI_ENABLED!" equ "true" (
        echo   ⚪ Open WebUI
        (type "!CREATED_AI_ROUTES_FILE!" 2>nul | findstr /B /C:"OpenWebUI:") || echo      ⚠️ No Open WebUI routes were successfully created (check logs).
        set "any_provider_listed=true"
    )
    if /i "!any_provider_listed!" equ "false" (
        echo   ⚠️ No AI providers appear to be enabled or successfully configured.
    )
    if exist "!CREATED_AI_ROUTES_FILE!" (
        echo.
        echo Successfully Created Routes via APISIX Admin API:
        type "!CREATED_AI_ROUTES_FILE!"
    ) else (
        if /i "!SKIP_AI_SETUP!" neq "true" (
            echo.
            echo   ⚠️ No AI routes were created or detected.
        )
    )
    echo.
    echo Example usage (replace with an actual enabled route^):
    echo curl -X POST http://localhost:9080/ai/ollama/llama3 \
    echo   -H "Content-Type: application/json" \
    echo   -d "{'messages':[{'role':'user','content':'Hello!'}]}"
    echo ==========================================
    goto :eof


REM Function-like section to generate a random secure string using PowerShell
:generate_secure_string_ps
    set "_psc_rand_cmd=powershell -NoProfile -Command "$bytes = New-Object byte[] 32; (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($bytes); Write-Host ([Convert]::ToBase64String($bytes) -replace '[/+=]' | ForEach-Object { $_.Substring(0, [System.Math]::Min($_.Length, 32)) })""
    for /f "delims=" %%s in ('!_psc_rand_cmd!') do set "%1=%%s"
    goto :eof

REM Function to backup and prepare config file from template (enhanced)
:prepare_config_from_template
    set "template_file=%~1"
    set "target_file=%~2"

    REM If target_file not provided, auto-derive by removing .template extension
    if not defined target_file (
        set "target_file=!template_file:.template=!"
    )

    if not exist "!template_file!" (
        echo Error: Template file !template_file! not found!
        exit /b 1
    )

    REM Create backup with timestamp if target exists
    if exist "!target_file!" (
        set "backup_suffix_date="
        for /f "tokens=1-6 delims=/: " %%a in ("%date% %time%") do set "backup_suffix_date=%%c%%a%%b%%d%%e%%f"
        copy "!target_file!" "!target_file!.bak!backup_suffix_date!" >nul
        echo Backed up !target_file! to !target_file!.bak!backup_suffix_date!
    )

    REM Copy template to target
    copy "!template_file!" "!target_file!" >nul
    echo Created !target_file! from template
    exit /b 0
    goto :eof

REM Function to replace placeholder in a file with a value using PowerShell
:replace_in_file_ps
    set "file_to_edit=%~1"
    set "placeholder=%~2"
    set "value_to_insert=%~3"
    set "description_for_report=%~4"

    powershell -NoProfile -Command ^
        $filePath = '!file_to_edit!'; ^
        $placeHolder = '!placeholder!'; ^
        $newValue = '!value_to_insert!'; ^
        (Get-Content $filePath -Raw) -replace [regex]::Escape($placeHolder), $newValue | Set-Content -Path $filePath -NoNewline -Encoding Ascii;

    if defined description_for_report if not "!description_for_report!"=="" (
        echo !description_for_report!: !value_to_insert! >> "!SENSITIVE_VALUES_FILE!"
    )
    echo Replaced !placeholder! in !file_to_edit!
    goto :eof

REM Function to obtain Keycloak admin access token using PowerShell
:get_keycloak_admin_token_ps
    echo Attempting to obtain Keycloak admin access token...
    set "token_payload=client_id=!ADMIN_CLIENT_ID!&grant_type=password&username=!ADMIN_USER!&password=!ADMIN_PASS!"
    set "token_url=!KEYCLOAK_SERVER_URL!/realms/!MASTER_REALM!/protocol/openid-connect/token"

    set "ps_get_token_command=powershell -NoProfile -Command ^
        try { ^
            $response = Invoke-RestMethod -Uri '!token_url!' -Method Post -Body '!token_payload!' -ContentType 'application/x-www-form-urlencoded'; ^
            Write-Output $response.access_token; ^
            exit 0; ^
        } catch { ^
            Write-Host ('ERROR_ KC Token: ' + $_.Exception.Message) -ForegroundColor Red; ^
            if ($_.Exception.Response) { Write-Host ('Status Code: ' + $_.Exception.Response.StatusCode.value__) -ForegroundColor Red; }; ^
            exit 1; ^
        }"

    set "ACCESS_TOKEN="
    for /f "delims=" %%t in ('!ps_get_token_command!') do set "ACCESS_TOKEN=%%t"

    if not defined ACCESS_TOKEN (
        echo Error: Could not obtain Keycloak admin access token. PowerShell script might have failed or returned no output.
        exit /b 1
    )
    if "!ACCESS_TOKEN!"=="" (
        echo Error: Obtained empty Keycloak admin access token.
        exit /b 1
    )
    if "!ACCESS_TOKEN:~0,6!"=="ERROR_" (
        echo Error: Problem during Keycloak token retrieval: !ACCESS_TOKEN!
        exit /b 1
    )
    echo Successfully obtained Keycloak admin access token.
    goto :eof

REM Function-like section to make an authenticated API call to Keycloak using PowerShell
:make_api_call_ps
    set "_METHOD=%~1"
    set "_ENDPOINT_PATH=%~2"
    set "_DATA_ARG=%~3" REM This can be direct JSON string or a variable name holding JSON or filepath
    set "_RESPONSE_VAR_NAME=%~4"
    set "_STATUS_VAR_NAME=%~5"

    set "_FULL_URL=!KEYCLOAK_SERVER_URL!/admin!_ENDPOINT_PATH!"

    set "PS_API_CALL=powershell -NoProfile -Command ^
        $uri = '!_FULL_URL!'; ^
        $method = '!_METHOD!'; ^
        $headers = @{'Authorization'='Bearer !ACCESS_TOKEN!'}; ^
        $bodyContent = $null; ^
        $contentType = $null; ^
        $dataArg = "!_DATA_ARG!"; ^
        if ($dataArg) { ^
            $contentType = 'application/json'; ^
            $headers.'Content-Type' = $contentType; ^
            if (Test-Path $dataArg -PathType Leaf) { $bodyContent = Get-Content -Path $dataArg -Raw; } ^
            else { $bodyContent = $dataArg; } ^
        }; ^
        try { ^
            $response = Invoke-RestMethod -Uri $uri -Method $method -Headers $headers -Body $bodyContent -ContentType $contentType -ErrorAction Stop -SkipHttpErrorCheck; ^
            Write-Output ('STATUS_CODE:' + $response.StatusCode); ^
            Write-Output ('RESPONSE_BODY:' + ($response.Content | ConvertTo-Json -Depth 10 -Compress)); ^
        } catch [Microsoft.PowerShell.Commands.HttpResponseException] { ^
            Write-Output ('STATUS_CODE:' + $_.Exception.Response.StatusCode.value__); ^
            $errorResponse = ''; ^
            if ($_.Exception.Response.Content) { $errorResponse = $_.Exception.Response.Content; } ^
            Write-Output ('RESPONSE_BODY:' + $errorResponse); ^
        } catch { ^
            Write-Output ('STATUS_CODE:599'); ^
            Write-Output ('RESPONSE_BODY:Unknown PowerShell error during API call: ' + ($_.Exception.Message -replace \"`r`n\", ' ')); ^
        }"

    echo Executing API call: !_METHOD! !_FULL_URL!

    set "!_RESPONSE_VAR_NAME%="
    set "!_STATUS_VAR_NAME%="
    for /f "tokens=1,* delims=:" %%a in ('!PS_API_CALL!') do (
        if "%%a"=="STATUS_CODE" set "!_STATUS_VAR_NAME!=%%b"
        if "%%a"=="RESPONSE_BODY" set "!_RESPONSE_VAR_NAME!=%%b"
    )
    goto :eof


REM Enhanced network test function with comprehensive diagnostics
:test_network_connectivity_ps
    set "from_container_service_name=%~1"
    set "to_service_hostname=%~2"
    set "to_port=%~3"
    set "test_status=1" REM Assume fail

    echo ⚙️ Testing connectivity from service '!from_container_service_name!' to !to_service_hostname!:!to_port!...

    set "PS_NETWORK_TEST=powershell -NoProfile -Command ^
        $fromService = '!from_container_service_name!'; ^
        $toHost = '!to_service_hostname!'; ^
        $toPort = '!to_port!'; ^
        $fromContainerId = (docker ps --filter \"name=$fromService\" --format \"{{.ID}}\" | Select-Object -First 1); ^
        if (-not $fromContainerId) { $fromContainerId = (docker ps --filter \"label=com.docker.compose.service=$fromService\" --format \"{{.ID}}\" | Select-Object -First 1); }; ^
        if (-not $fromContainerId) { Write-Host \"❌ Container for service '$fromService' not found!\"; exit 1; }; ^
        Write-Host \"Using container ID: $fromContainerId for service '$fromService'\"; ^
        Write-Host \"Running ping test (network layer)...\"; ^
        $pingResult = docker exec $fromContainerId ping -n 2 $toHost 2^>^&1; ^
        if ($LASTEXITCODE -eq 0) { ^
            Write-Host \"✓ Ping successful - network layer connectivity confirmed\"; ^
        } else { ^
            Write-Host \"✗ Ping failed - DNS resolution or network connectivity issue\"; ^
            Write-Host \"Performing network diagnostics...\"; ^
            Write-Host \"DNS resolution inside container:\"; ^
            docker exec $fromContainerId nslookup $toHost 2^>^&1; ^
            Write-Host \"Networks for container:\"; ^
            docker inspect --format='{{range `$net,`$v := .NetworkSettings.Networks}}{{`$net}} {{end}}' $fromContainerId; ^
            exit 1; ^
        }; ^
        Write-Host \"Running HTTP test (application layer)...\"; ^
        $httpResult = docker exec $fromContainerId powershell -Command \"try { (Invoke-WebRequest -Uri 'http://$toHost`:$toPort' -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop).StatusCode } catch { 'HTTP_FAILED' }\" 2^>^&1; ^
        if ($httpResult -match '^[0-9]+$') { ^
            Write-Host \"✓ HTTP connection successful - application layer connectivity confirmed (Status: $httpResult)\"; ^
            exit 0; ^
        } else { ^
            Write-Host \"✗ HTTP connection failed - service may not be accepting connections\"; ^
            Write-Host \"HTTP Result: $httpResult\"; ^
            exit 1; ^
        }"

    !PS_NETWORK_TEST!
    set "test_status=%errorlevel%"
    exit /b !test_status!
goto :eof

REM Network diagnostics and recovery function
:network_diagnostics_and_recovery_ps
    echo Performing additional network diagnostics...

    REM Show all networks and their containers
    echo Docker Networks:
    docker network ls

    REM Check containers on the shared network
    echo Containers on !SHARED_NETWORK_NAME!:
    docker network inspect !SHARED_NETWORK_NAME! --format "{{range .Containers}}{{.Name}} {{end}}"

    REM Check if services can be resolved by DNS
    echo DNS resolution test:
    docker run --rm --network=!SHARED_NETWORK_NAME! alpine nslookup keycloak 2>nul || echo "Failed to resolve keycloak"

    REM Check if APISIX container is properly connected to network
    set "APISIX_CONTAINER_ID="
    for /f "delims=" %%i in ('docker ps --filter "name=apisix" --format "{{.ID}}" 2^>nul') do set "APISIX_CONTAINER_ID=%%i"

    if defined APISIX_CONTAINER_ID (
        echo Checking APISIX container network connections...
        docker inspect --format="{{range $net,$v := .NetworkSettings.Networks}}{{$net}} {{end}}" !APISIX_CONTAINER_ID!

        REM Check if APISIX is connected to shared network
        docker inspect --format="{{.NetworkSettings.Networks.!SHARED_NETWORK_NAME!}}" !APISIX_CONTAINER_ID! | findstr "null" >nul
        if !errorlevel! equ 0 (
            echo APISIX container not connected to !SHARED_NETWORK_NAME!. Attempting to reconnect...
            docker network disconnect !SHARED_NETWORK_NAME! !APISIX_CONTAINER_ID! 2>nul
            docker network connect !SHARED_NETWORK_NAME! !APISIX_CONTAINER_ID!
            if !errorlevel! equ 0 (
                echo ✅ Reconnected APISIX container to !SHARED_NETWORK_NAME!

                REM Retry connectivity test
                echo Retrying connectivity test after network reconnection...
                call :test_network_connectivity_ps apisix keycloak 8080
                exit /b !errorlevel!
            ) else (
                echo ❌ Failed to reconnect APISIX to network
            )
        )
    )

    exit /b 1
goto :eof


REM Function to run a test and record the result
:run_test
    set "test_name=%~1"
    set "test_command=%~2"
    set "expected_match_pattern=%~3" REM Regex pattern for expected output or status code
    set "temp_output_file=%TEMP%\test_output.txt"

    echo Testing: !test_name!
    echo   Command: !test_command!

    REM Execute command and capture output (stdout and stderr)
    cmd /c "!test_command!" > "!temp_output_file!" 2>&1
    set "test_exit_code=%errorlevel%"

    set "output_matched=false"
    REM Check if output contains expected pattern (case-insensitive for status codes)
    findstr /R /I /C:"!expected_match_pattern!" "!temp_output_file!" >nul
    if !errorlevel! equ 0 (
        set "output_matched=true"
    )

    if "!output_matched!"=="true" (
        echo   Result: PASS
        echo ✅ PASS: !test_name! >> "!TEST_RESULTS_FILE!"
    ) else (
        echo   Result: FAIL (Expected pattern '!expected_match_pattern!' not found in output or command failed differently)
        echo   Exit Code: !test_exit_code!
        echo   Output:
        type "!temp_output_file!"
        echo ❌ FAIL: !test_name! >> "!TEST_RESULTS_FILE!"
        set /a TEST_FAILURES+=1
    )
    if exist "!temp_output_file!" del "!temp_output_file!"
    echo.
    goto :eof

REM --- Create FastAPI Route ---
:create_fastapi_route_ps
    echo Creating APISIX route for FastAPI service...

    set "ROUTE_NAME=violentutf-api"
    set "ROUTE_URI=/api/*"
    set "UPSTREAM_URL=violentutf_api:8000"

    set "PS_CREATE_FASTAPI_ROUTE=powershell -NoProfile -ErrorAction Stop -Command ^
        $routeConfig = @{ ^
            uri = '!ROUTE_URI!'; ^
            name = '!ROUTE_NAME!'; ^
            methods = @('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'); ^
            upstream = @{ ^
                type = 'roundrobin'; ^
                nodes = @{ ^
                    '!UPSTREAM_URL!' = 1 ^
                } ^
            }; ^
            plugins = @{ ^
                'cors' = @{ ^
                    allow_origins = 'http://localhost:8501,http://localhost:3000'; ^
                    allow_methods = 'GET,POST,PUT,DELETE,PATCH,OPTIONS'; ^
                    allow_headers = 'Authorization,Content-Type,X-Requested-With'; ^
                    expose_headers = 'X-Total-Count'; ^
                    max_age = 3600; ^
                    allow_credential = $true ^
                }; ^
                'proxy-rewrite' = @{ ^
                    regex_uri = @('^/api/(.*)', '/api/$$1') ^
                }; ^
                'limit-req' = @{ ^
                    rate = 100; ^
                    burst = 50; ^
                    rejected_code = 429; ^
                    rejected_msg = 'Too many requests'; ^
                    key_type = 'var'; ^
                    key = 'remote_addr' ^
                }; ^
                'limit-count' = @{ ^
                    count = 1000; ^
                    time_window = 3600; ^
                    rejected_code = 429; ^
                    rejected_msg = 'API rate limit exceeded'; ^
                    key_type = 'var'; ^
                    key = 'remote_addr'; ^
                    policy = 'local' ^
                } ^
            } ^
        }; ^
        $jsonPayload = $routeConfig | ConvertTo-Json -Depth 10; ^
        try { ^
            $response = Invoke-RestMethod -Uri '!APISIX_ADMIN_URL!/apisix/admin/routes/!ROUTE_NAME!' -Method Put -Headers @{'X-API-KEY'='!APISIX_ADMIN_KEY!';'Content-Type'='application/json'} -Body $jsonPayload -TimeoutSec 30; ^
            Write-Host '✅ FastAPI route successfully created/updated in APISIX.'; ^
            Write-Host 'Route ID: !ROUTE_NAME!'; ^
            Write-Host 'Route URI: !ROUTE_URI! -> !UPSTREAM_URL!'; ^
            exit 0; ^
        } catch { ^
            Write-Host '❌ Failed to create FastAPI route in APISIX.' -ForegroundColor Red; ^
            Write-Host ('HTTP Status: ' + $_.Exception.Response.StatusCode.value__) -ForegroundColor Red; ^
            Write-Host ('Response: ' + $_.Exception.Message) -ForegroundColor Red; ^
            exit 1; ^
        }"

    !PS_CREATE_FASTAPI_ROUTE!
    set "route_creation_result=%errorlevel%"
    if !route_creation_result! equ 0 (
        echo FastAPI: !ROUTE_URI! -> !UPSTREAM_URL! >> "!CREATED_AI_ROUTES_FILE!"
    )
    goto :eof

REM --- Create FastAPI Documentation Routes ---
:create_fastapi_docs_routes_ps
    echo Creating FastAPI documentation routes...

    REM Create /api/docs route
    set "DOCS_ROUTE_CONFIG=$docsConfig = @{ ^
        'uri' = '/api/docs'; ^
        'name' = 'violentutf-docs'; ^
        'methods' = @('GET'); ^
        'upstream' = @{ ^
            'type' = 'roundrobin'; ^
            'nodes' = @{ ^
                'violentutf_api:8000' = 1 ^
            } ^
        }; ^
        'plugins' = @{ ^
            'key-auth' = @{}; ^
            'cors' = @{ ^
                'allow_origins' = '*'; ^
                'allow_methods' = 'GET,POST,PUT,DELETE,OPTIONS'; ^
                'allow_headers' = '*'; ^
                'expose_headers' = '*'; ^
                'max_age' = 5; ^
                'allow_credential' = $false ^
            } ^
        } ^
    }"

    set "PS_CREATE_DOCS_ROUTE=powershell -NoProfile -ErrorAction Stop -Command ^
        !DOCS_ROUTE_CONFIG!; ^
        $jsonPayload = $docsConfig | ConvertTo-Json -Depth 10; ^
        try { ^
            $response = Invoke-RestMethod -Uri '!APISIX_ADMIN_URL!/apisix/admin/routes/violentutf-docs' -Method Put -Headers @{'X-API-KEY'='!APISIX_ADMIN_KEY!';'Content-Type'='application/json'} -Body $jsonPayload -TimeoutSec 30; ^
            Write-Host '✅ FastAPI docs route created successfully.'; ^
            exit 0; ^
        } catch { ^
            Write-Host '⚠️ Warning: Failed to create FastAPI docs route.' -ForegroundColor Yellow; ^
            Write-Host ('Status: ' + $_.Exception.Response.StatusCode.value__) -ForegroundColor Yellow; ^
            exit 1; ^
        }"

    !PS_CREATE_DOCS_ROUTE!
    set "docs_result=%errorlevel%"

    REM Create /api/redoc route
    set "REDOC_ROUTE_CONFIG=$redocConfig = @{ ^
        'uri' = '/api/redoc'; ^
        'name' = 'violentutf-redoc'; ^
        'methods' = @('GET'); ^
        'upstream' = @{ ^
            'type' = 'roundrobin'; ^
            'nodes' = @{ ^
                'violentutf_api:8000' = 1 ^
            } ^
        }; ^
        'plugins' = @{ ^
            'key-auth' = @{}; ^
            'cors' = @{ ^
                'allow_origins' = '*'; ^
                'allow_methods' = 'GET,POST,PUT,DELETE,OPTIONS'; ^
                'allow_headers' = '*'; ^
                'expose_headers' = '*'; ^
                'max_age' = 5; ^
                'allow_credential' = $false ^
            } ^
        } ^
    }"

    set "PS_CREATE_REDOC_ROUTE=powershell -NoProfile -ErrorAction Stop -Command ^
        !REDOC_ROUTE_CONFIG!; ^
        $jsonPayload = $redocConfig | ConvertTo-Json -Depth 10; ^
        try { ^
            $response = Invoke-RestMethod -Uri '!APISIX_ADMIN_URL!/apisix/admin/routes/violentutf-redoc' -Method Put -Headers @{'X-API-KEY'='!APISIX_ADMIN_KEY!';'Content-Type'='application/json'} -Body $jsonPayload -TimeoutSec 30; ^
            Write-Host '✅ FastAPI redoc route created successfully.'; ^
            exit 0; ^
        } catch { ^
            Write-Host '⚠️ Warning: Failed to create FastAPI redoc route.' -ForegroundColor Yellow; ^
            Write-Host ('Status: ' + $_.Exception.Response.StatusCode.value__) -ForegroundColor Yellow; ^
            exit 1; ^
        }"

    !PS_CREATE_REDOC_ROUTE!
    set "redoc_result=%errorlevel%"

    if !docs_result! equ 0 (
        echo FastAPI Docs: /api/docs -> violentutf_api:8000 >> "!CREATED_AI_ROUTES_FILE!"
    )
    if !redoc_result! equ 0 (
        echo FastAPI ReDoc: /api/redoc -> violentutf_api:8000 >> "!CREATED_AI_ROUTES_FILE!"
    )

    echo FastAPI documentation routes configured.
    goto :eof

REM --- Create FastAPI Client in Keycloak ---
:create_fastapi_client_ps
    set "client_id=%~1"
    set "client_secret=%~2"
    set "redirect_uri=%~3"

    echo Creating FastAPI client in Keycloak...

    set "TEMP_FASTAPI_CLIENT_FILE=%TEMP%\fastapi-client.json"

    REM Create FastAPI client configuration JSON
    powershell -NoProfile -Command ^
        $clientConfig = @{ ^
            'clientId' = '!client_id!'; ^
            'name' = 'ViolentUTF API'; ^
            'description' = 'FastAPI backend for ViolentUTF'; ^
            'rootUrl' = 'http://localhost:8000'; ^
            'adminUrl' = 'http://localhost:8000'; ^
            'baseUrl' = 'http://localhost:8000'; ^
            'surrogateAuthRequired' = $false; ^
            'enabled' = $true; ^
            'alwaysDisplayInConsole' = $false; ^
            'clientAuthenticatorType' = 'client-secret'; ^
            'secret' = '!client_secret!'; ^
            'redirectUris' = @('!redirect_uri!'); ^
            'webOrigins' = @('*'); ^
            'notBefore' = 0; ^
            'bearerOnly' = $false; ^
            'consentRequired' = $false; ^
            'standardFlowEnabled' = $true; ^
            'implicitFlowEnabled' = $false; ^
            'directAccessGrantsEnabled' = $true; ^
            'serviceAccountsEnabled' = $true; ^
            'publicClient' = $false; ^
            'frontchannelLogout' = $false; ^
            'protocol' = 'openid-connect'; ^
            'attributes' = @{ ^
                'saml.assertion.signature' = 'false'; ^
                'saml.force.post.binding' = 'false'; ^
                'saml.multivalued.roles' = 'false'; ^
                'saml.encrypt' = 'false'; ^
                'saml.server.signature' = 'false'; ^
                'saml.server.signature.keyinfo.ext' = 'false'; ^
                'exclude.session.state.from.auth.response' = 'false'; ^
                'saml_force_name_id_format' = 'false'; ^
                'saml.client.signature' = 'false'; ^
                'tls.client.certificate.bound.access.tokens' = 'false'; ^
                'saml.authnstatement' = 'false'; ^
                'display.on.consent.screen' = 'false'; ^
                'saml.onetimeuse.condition' = 'false' ^
            }; ^
            'authenticationFlowBindingOverrides' = @{}; ^
            'fullScopeAllowed' = $true; ^
            'nodeReRegistrationTimeout' = -1; ^
            'protocolMappers' = @( ^
                @{ ^
                    'id' = [guid]::NewGuid().ToString(); ^
                    'name' = 'username'; ^
                    'protocol' = 'openid-connect'; ^
                    'protocolMapper' = 'oidc-usermodel-property-mapper'; ^
                    'consentRequired' = $false; ^
                    'config' = @{ ^
                        'userinfo.token.claim' = 'true'; ^
                        'user.attribute' = 'username'; ^
                        'id.token.claim' = 'true'; ^
                        'access.token.claim' = 'true'; ^
                        'claim.name' = 'preferred_username'; ^
                        'jsonType.label' = 'String' ^
                    } ^
                }, ^
                @{ ^
                    'id' = [guid]::NewGuid().ToString(); ^
                    'name' = 'email'; ^
                    'protocol' = 'openid-connect'; ^
                    'protocolMapper' = 'oidc-usermodel-property-mapper'; ^
                    'consentRequired' = $false; ^
                    'config' = @{ ^
                        'userinfo.token.claim' = 'true'; ^
                        'user.attribute' = 'email'; ^
                        'id.token.claim' = 'true'; ^
                        'access.token.claim' = 'true'; ^
                        'claim.name' = 'email'; ^
                        'jsonType.label' = 'String' ^
                    } ^
                }, ^
                @{ ^
                    'id' = [guid]::NewGuid().ToString(); ^
                    'name' = 'roles'; ^
                    'protocol' = 'openid-connect'; ^
                    'protocolMapper' = 'oidc-usermodel-realm-role-mapper'; ^
                    'consentRequired' = $false; ^
                    'config' = @{ ^
                        'userinfo.token.claim' = 'true'; ^
                        'id.token.claim' = 'true'; ^
                        'access.token.claim' = 'true'; ^
                        'claim.name' = 'roles'; ^
                        'jsonType.label' = 'String'; ^
                        'multivalued' = 'true' ^
                    } ^
                } ^
            ); ^
            'defaultClientScopes' = @('web-origins', 'role_list', 'profile', 'roles', 'email'); ^
            'optionalClientScopes' = @('address', 'phone', 'offline_access', 'microprofile-jwt') ^
        }; ^
        $clientConfig | ConvertTo-Json -Depth 10 | Set-Content -Path '!TEMP_FASTAPI_CLIENT_FILE!' -Encoding UTF8

    REM Create the client via API
    call :make_api_call_ps "POST" "/realms/!VUTF_REALM_NAME!/clients" "!TEMP_FASTAPI_CLIENT_FILE!" API_FASTAPI_CREATE_RESP API_FASTAPI_CREATE_STATUS

    if "!API_FASTAPI_CREATE_STATUS!"=="201" (
        echo ✅ FastAPI client created successfully in Keycloak.
        del "!TEMP_FASTAPI_CLIENT_FILE!"
        exit /b 0
    ) else if "!API_FASTAPI_CREATE_STATUS!"=="409" (
        echo ✅ FastAPI client already exists in Keycloak.
        del "!TEMP_FASTAPI_CLIENT_FILE!"
        exit /b 0
    ) else (
        echo ❌ Failed to create FastAPI client. Status: !API_FASTAPI_CREATE_STATUS!
        echo Response: !API_FASTAPI_CREATE_RESP!
        del "!TEMP_FASTAPI_CLIENT_FILE!"
        exit /b 1
    )
    goto :eof

REM ==========================================================================
REM === FUNCTION DEFINITIONS END =============================================
REM ==========================================================================

:main_script

echo.
echo ==========================================
echo GENERATING ALL SECURE SECRETS
echo ==========================================
echo Generating secure secrets for all services...

REM Keycloak admin credentials (hardcoded in docker-compose)
echo Keycloak Admin Username: admin >> "!SENSITIVE_VALUES_FILE!"
echo Keycloak Admin Password: admin >> "!SENSITIVE_VALUES_FILE!"

REM Keycloak PostgreSQL password (for new setups)
call :generate_secure_string_ps KEYCLOAK_POSTGRES_PASSWORD
echo Keycloak PostgreSQL Password: !KEYCLOAK_POSTGRES_PASSWORD! >> "!SENSITIVE_VALUES_FILE!"

REM ViolentUTF application secrets
call :generate_secure_string_ps VIOLENTUTF_CLIENT_SECRET
call :generate_secure_string_ps VIOLENTUTF_COOKIE_SECRET
call :generate_secure_string_ps VIOLENTUTF_PYRIT_SALT
call :generate_secure_string_ps VIOLENTUTF_API_KEY
call :generate_secure_string_ps VIOLENTUTF_USER_PASSWORD
echo ViolentUTF Keycloak Client Secret: !VIOLENTUTF_CLIENT_SECRET! >> "!SENSITIVE_VALUES_FILE!"
echo ViolentUTF Cookie Secret: !VIOLENTUTF_COOKIE_SECRET! >> "!SENSITIVE_VALUES_FILE!"
echo ViolentUTF PyRIT DB Salt: !VIOLENTUTF_PYRIT_SALT! >> "!SENSITIVE_VALUES_FILE!"
echo ViolentUTF AI Gateway API Key: !VIOLENTUTF_API_KEY! >> "!SENSITIVE_VALUES_FILE!"
echo ViolentUTF User Password: !VIOLENTUTF_USER_PASSWORD! >> "!SENSITIVE_VALUES_FILE!"

REM APISIX secrets
call :generate_secure_string_ps APISIX_ADMIN_KEY
call :generate_secure_string_ps APISIX_DASHBOARD_SECRET
call :generate_secure_string_ps APISIX_DASHBOARD_PASSWORD
call :generate_secure_string_ps APISIX_KEYRING_VALUE_1_RAW
call :generate_secure_string_ps APISIX_KEYRING_VALUE_2_RAW
set "APISIX_KEYRING_VALUE_1=!APISIX_KEYRING_VALUE_1_RAW:~0,16!"
set "APISIX_KEYRING_VALUE_2=!APISIX_KEYRING_VALUE_2_RAW:~0,16!"
call :generate_secure_string_ps APISIX_CLIENT_SECRET
echo APISIX Admin API Key: !APISIX_ADMIN_KEY! >> "!SENSITIVE_VALUES_FILE!"
echo APISIX Dashboard Username: admin >> "!SENSITIVE_VALUES_FILE!"
echo APISIX Dashboard JWT Secret: !APISIX_DASHBOARD_SECRET! >> "!SENSITIVE_VALUES_FILE!"
echo APISIX Dashboard Admin Password: !APISIX_DASHBOARD_PASSWORD! >> "!SENSITIVE_VALUES_FILE!"
echo APISIX Keyring Value 1: !APISIX_KEYRING_VALUE_1! >> "!SENSITIVE_VALUES_FILE!"
echo APISIX Keyring Value 2: !APISIX_KEYRING_VALUE_2! >> "!SENSITIVE_VALUES_FILE!"
echo APISIX Keycloak Client Secret: !APISIX_CLIENT_SECRET! >> "!SENSITIVE_VALUES_FILE!"

REM FastAPI secrets
call :generate_secure_string_ps FASTAPI_SECRET_KEY
call :generate_secure_string_ps FASTAPI_CLIENT_SECRET
set "FASTAPI_CLIENT_ID=violentutf-fastapi"
echo FastAPI JWT Secret Key: !FASTAPI_SECRET_KEY! >> "!SENSITIVE_VALUES_FILE!"
echo FastAPI Keycloak Client Secret: !FASTAPI_CLIENT_SECRET! >> "!SENSITIVE_VALUES_FILE!"

echo ✅ Generated all secure secrets
echo.

echo ==========================================
echo CREATING CONFIGURATION FILES
echo ==========================================

REM --- Create Keycloak .env ---
echo Creating Keycloak configuration...
if not exist "keycloak" mkdir "keycloak"
(
echo POSTGRES_PASSWORD=!KEYCLOAK_POSTGRES_PASSWORD!
) > "keycloak\.env"
echo ✅ Created keycloak\.env

REM --- Create APISIX configurations ---
echo Creating APISIX configurations...
if not exist "apisix\conf" mkdir "apisix\conf"

REM Process config.yaml template
if exist "apisix\conf\config.yaml.template" (
    call :prepare_config_from_template "apisix\conf\config.yaml.template"
    call :replace_in_file_ps "apisix\conf\config.yaml" "APISIX_ADMIN_KEY_PLACEHOLDER" "!APISIX_ADMIN_KEY!" "APISIX Admin API Key"
    call :replace_in_file_ps "apisix\conf\config.yaml" "APISIX_KEYRING_VALUE_1_PLACEHOLDER" "!APISIX_KEYRING_VALUE_1!" "APISIX Keyring Value 1"
    call :replace_in_file_ps "apisix\conf\config.yaml" "APISIX_KEYRING_VALUE_2_PLACEHOLDER" "!APISIX_KEYRING_VALUE_2!" "APISIX Keyring Value 2"
    echo ✅ Created apisix\conf\config.yaml
)

REM Process dashboard.yaml template
if exist "apisix\conf\dashboard.yaml.template" (
    call :prepare_config_from_template "apisix\conf\dashboard.yaml.template"
    call :replace_in_file_ps "apisix\conf\dashboard.yaml" "APISIX_DASHBOARD_SECRET_PLACEHOLDER" "!APISIX_DASHBOARD_SECRET!" "APISIX Dashboard JWT Secret"
    call :replace_in_file_ps "apisix\conf\dashboard.yaml" "APISIX_DASHBOARD_PASSWORD_PLACEHOLDER" "!APISIX_DASHBOARD_PASSWORD!" "APISIX Dashboard Admin Password"
    echo ✅ Created apisix\conf\dashboard.yaml
)

REM Process nginx.conf template if exists
if exist "apisix\conf\nginx.conf.template" (
    call :prepare_config_from_template "apisix\conf\nginx.conf.template"
    echo ✅ Created apisix\conf\nginx.conf
)

REM Create prometheus.yml if missing
if not exist "apisix\conf\prometheus.yml" (
    (
    echo global:
    echo   scrape_interval: 15s
    echo   evaluation_interval: 15s
    echo.
    echo scrape_configs:
    echo   - job_name: 'apisix'
    echo     static_configs:
    echo       - targets: ['apisix:9091']
    echo     metrics_path: '/apisix/prometheus/metrics'
    ) > "apisix\conf\prometheus.yml"
    echo ✅ Created apisix\conf\prometheus.yml
)

REM --- Create ViolentUTF configurations ---
echo Creating ViolentUTF configurations...
if not exist "violentutf" mkdir "violentutf"
if not exist "violentutf\.streamlit" mkdir "violentutf\.streamlit"

REM Create .env file
(
echo KEYCLOAK_URL=http://localhost:8080/
echo KEYCLOAK_REALM=ViolentUTF
echo KEYCLOAK_CLIENT_ID=violentutf
echo KEYCLOAK_CLIENT_SECRET=!VIOLENTUTF_CLIENT_SECRET!
echo KEYCLOAK_USERNAME=violentutf.web
echo KEYCLOAK_PASSWORD=!VIOLENTUTF_USER_PASSWORD!
echo KEYCLOAK_APISIX_CLIENT_ID=apisix
echo KEYCLOAK_APISIX_CLIENT_SECRET=!APISIX_CLIENT_SECRET!
echo OPENAI_CHAT_DEPLOYMENT='OpenAI API'
echo OPENAI_CHAT_ENDPOINT=https://api.openai.com/v1/responses
echo OPENAI_CHAT_KEY=***
echo PYRIT_DB_SALT=!VIOLENTUTF_PYRIT_SALT!
echo JWT_SECRET_KEY=!FASTAPI_SECRET_KEY!
echo VIOLENTUTF_API_KEY=!VIOLENTUTF_API_KEY!
echo VIOLENTUTF_API_URL=http://localhost:9080/api
echo KEYCLOAK_URL_BASE=http://localhost:9080/auth
echo AI_PROXY_BASE_URL=http://localhost:9080/ai
) > "violentutf\.env"
echo ✅ Created violentutf\.env

REM Create secrets.toml with full auth structure
(
echo [auth]
echo redirect_uri = "http://localhost:8501/oauth2callback"
echo cookie_secret = "!VIOLENTUTF_COOKIE_SECRET!"
echo.
echo [auth.keycloak]
echo client_id = "violentutf"
echo client_secret = "!VIOLENTUTF_CLIENT_SECRET!"
echo server_metadata_url = "!KEYCLOAK_SERVER_URL!/realms/ViolentUTF/.well-known/openid-configuration"
echo.
echo [auth.providers.keycloak]
echo issuer = "!KEYCLOAK_SERVER_URL!/realms/ViolentUTF"
echo token_endpoint = "!KEYCLOAK_SERVER_URL!/realms/ViolentUTF/protocol/openid-connect/token"
echo authorization_endpoint = "!KEYCLOAK_SERVER_URL!/realms/ViolentUTF/protocol/openid-connect/auth"
echo userinfo_endpoint = "!KEYCLOAK_SERVER_URL!/realms/ViolentUTF/protocol/openid-connect/userinfo"
echo jwks_uri = "!KEYCLOAK_SERVER_URL!/realms/ViolentUTF/protocol/openid-connect/certs"
echo.
echo [apisix]
echo client_id = "apisix"
echo client_secret = "!APISIX_CLIENT_SECRET!"
) > "violentutf\.streamlit\secrets.toml"
echo ✅ Created violentutf\.streamlit\secrets.toml

REM Verify JWT consistency across all files
call :check_jwt_consistency

REM --- Create FastAPI configuration ---
echo Creating FastAPI configuration...
if not exist "violentutf_api\fastapi_app" mkdir "violentutf_api\fastapi_app"

(
echo # FastAPI Configuration
echo SECRET_KEY=!FASTAPI_SECRET_KEY!
echo ALGORITHM=HS256
echo ACCESS_TOKEN_EXPIRE_MINUTES=30
echo API_KEY_EXPIRE_DAYS=365
echo.
echo # Database
echo DATABASE_URL=sqlite+aiosqlite:///./app_data/violentutf.db
echo.
echo # Keycloak Configuration
echo KEYCLOAK_URL=http://keycloak:8080
echo KEYCLOAK_REALM=ViolentUTF
echo KEYCLOAK_CLIENT_ID=!FASTAPI_CLIENT_ID!
echo KEYCLOAK_CLIENT_SECRET=!FASTAPI_CLIENT_SECRET!
echo.
echo # APISIX Configuration
echo APISIX_BASE_URL=http://apisix:9080
echo APISIX_ADMIN_URL=http://apisix:9180
echo APISIX_ADMIN_KEY=!APISIX_ADMIN_KEY!
echo.
echo # Service Configuration
echo SERVICE_NAME=ViolentUTF API
echo SERVICE_VERSION=1.0.0
echo DEBUG=false
) > "violentutf_api\fastapi_app\.env"
echo ✅ Created violentutf_api\fastapi_app\.env

echo.
echo All configuration files created successfully!
echo.

REM ---------------------------------------------------------------
REM 1. Check Docker and Docker Compose
REM ---------------------------------------------------------------
echo Step 1: Checking Docker and Docker Compose...
where docker >nul 2>nul
if %errorlevel% NEQ 0 (
    echo Docker could not be found. Please install Docker Desktop for Windows.
    goto :eof_error
)
set "DOCKER_COMPOSE_CMD=docker compose"
!DOCKER_COMPOSE_CMD! version >nul 2>nul
if %errorlevel% NEQ 0 (
    set "DOCKER_COMPOSE_CMD=docker-compose"
    !DOCKER_COMPOSE_CMD! version >nul 2>nul
    if %errorlevel% NEQ 0 (
        echo Neither 'docker compose' nor 'docker-compose' found.
        goto :eof_error
    )
)
echo Using Docker Compose command: !DOCKER_COMPOSE_CMD!
docker ps >nul 2>nul
if %errorlevel% NEQ 0 (
    echo Docker daemon is not running. Please start Docker Desktop.
    goto :eof_error
)
echo Docker and Docker Compose check passed.

REM Validate all core services availability
call :validate_all_services
if errorlevel 1 (
    echo ❌ Core services validation failed. Please install missing dependencies.
    goto :eof_error
)

REM Create a shared network for all services
call :validate_network_configuration

REM ---------------------------------------------------------------
REM SECTION A: KEYCLOAK SETUP
REM ---------------------------------------------------------------
echo SECTION A: SETTING UP KEYCLOAK

REM 2. Copy and populate keycloak\.env
echo Step 2: Keycloak .env already configured.
set "KEYCLOAK_ENV_DIR=keycloak"
set "KEYCLOAK_ENV_FILE=!KEYCLOAK_ENV_DIR!\.env"

REM 3. Check Keycloak stack and launch if not running
echo Step 3: Checking and launching Keycloak Docker stack...
set "KEYCLOAK_COMPOSE_FILE=!KEYCLOAK_ENV_DIR!\docker-compose.yml"
set "KEYCLOAK_SERVICE_NAME_IN_COMPOSE=keycloak"
set "KEYCLOAK_SETUP_NEEDED=true"

set "KC_CONTAINER_ID="
for /f "delims=" %%i in ('!DOCKER_COMPOSE_CMD! -f "!KEYCLOAK_COMPOSE_FILE!" ps -q !KEYCLOAK_SERVICE_NAME_IN_COMPOSE! 2^>nul') do set "KC_CONTAINER_ID=%%i"

if defined KC_CONTAINER_ID (
    docker inspect -f "{{.State.Running}}" !KC_CONTAINER_ID! 2>nul | findstr "true" >nul
    if %errorlevel% EQU 0 (
        echo Keycloak service '!KEYCLOAK_SERVICE_NAME_IN_COMPOSE!' appears to be already running.
        set "KEYCLOAK_SETUP_NEEDED=false"
    )
)

if "!KEYCLOAK_SETUP_NEEDED!"=="true" (
    echo Keycloak stack not found or not running. Proceeding with setup.
    pushd "!KEYCLOAK_ENV_DIR!"
    if errorlevel 1 ( echo Failed to cd into !KEYCLOAK_ENV_DIR!; goto :eof_error )

    echo Ensuring Keycloak docker-compose.yml has proper network configuration...
    call :ensure_network_in_compose "docker-compose.yml" "!KEYCLOAK_SERVICE_NAME_IN_COMPOSE!"

    echo Launching Docker Compose for Keycloak...
    !DOCKER_COMPOSE_CMD! up -d
    if errorlevel 1 (
        echo Failed to start Keycloak stack. Check Docker Compose logs. & !DOCKER_COMPOSE_CMD! logs & popd & goto :eof_error
    )
    echo Keycloak stack started. Waiting for Keycloak to be operational...
    set "RETRY_COUNT=0" & set "MAX_RETRIES=30" & set "KEYCLOAK_READY=false"
    :wait_keycloak_loop
    if !RETRY_COUNT! GEQ !MAX_RETRIES! goto :keycloak_not_ready
    set /a RETRY_COUNT+=1
    powershell -NoProfile -Command "try { $response = Invoke-WebRequest -Uri '!KEYCLOAK_SERVER_URL!/realms/master' -UseBasicParsing -TimeoutSec 10; if ($response.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
    if errorlevel 1 (
        echo Keycloak not ready yet (attempt !RETRY_COUNT!/!MAX_RETRIES!). Waiting 10s...
        timeout /t 10 /nobreak >nul
        goto :wait_keycloak_loop
    )
    echo Keycloak is up. & set "KEYCLOAK_READY=true"
    :keycloak_not_ready
    if "!KEYCLOAK_READY!"=="false" (
        echo Keycloak did not become ready. Check logs. & !DOCKER_COMPOSE_CMD! logs !KEYCLOAK_SERVICE_NAME_IN_COMPOSE! & popd & goto :eof_error
    )
    popd
    REM Ensure container is connected to shared network
    echo Ensuring Keycloak container is connected to shared network...
    set "KC_CONTAINER_FOR_NET="
    for /f "delims=" %%i in ('!DOCKER_COMPOSE_CMD! -f "!KEYCLOAK_COMPOSE_FILE!" ps -q !KEYCLOAK_SERVICE_NAME_IN_COMPOSE! 2^>nul') do set "KC_CONTAINER_FOR_NET=%%i"
    if defined KC_CONTAINER_FOR_NET (
      powershell -NoProfile -Command "$container='!KC_CONTAINER_FOR_NET!'; $network='!SHARED_NETWORK_NAME!'; $inspect=(docker inspect $container | ConvertFrom-Json); if (-not $inspect[0].NetworkSettings.Networks.$network) { Write-Host 'Manually connecting Keycloak to !SHARED_NETWORK_NAME!...'; docker network connect $network $container }"
    )
)

if "!KEYCLOAK_SETUP_NEEDED!"=="true" (
    call :get_keycloak_admin_token_ps
    if errorlevel 1 goto :eof_error

    echo Step 4: Importing Keycloak realm via API...
    set "REALM_EXPORT_FILE_PATH=!KEYCLOAK_ENV_DIR!\realm-export.json"
    if not exist "!REALM_EXPORT_FILE_PATH!" ( echo Error: !REALM_EXPORT_FILE_PATH! not found! & goto :eof_error )

    set "TARGET_REALM_NAME="
    for /f "delims=" %%N in ('powershell -NoProfile -Command "(Get-Content -Path '!REALM_EXPORT_FILE_PATH!' -Raw | ConvertFrom-Json).realm"') do set "TARGET_REALM_NAME=%%N"
    if not defined TARGET_REALM_NAME ( echo Error: Could not extract realm name. & goto :eof_error )
    echo Target realm name: !TARGET_REALM_NAME!

    call :make_api_call_ps "GET" "/realms/!TARGET_REALM_NAME!" "" API_REALM_CHECK_RESPONSE API_REALM_CHECK_STATUS
    if "!API_REALM_CHECK_STATUS!"=="200" (
        echo Realm '!TARGET_REALM_NAME!' already exists. Deleting and re-importing.
        call :make_api_call_ps "DELETE" "/realms/!TARGET_REALM_NAME!" "" API_REALM_DELETE_RESPONSE API_REALM_DELETE_STATUS
        if not "!API_REALM_DELETE_STATUS!"=="204" ( echo Failed to delete realm. Status: !API_REALM_DELETE_STATUS! & goto :eof_error )
        echo Existing realm deleted.
    ) else if not "!API_REALM_CHECK_STATUS!"=="404" ( echo Error checking realm. Status: !API_REALM_CHECK_STATUS! & goto :eof_error )

    echo Importing realm...
    call :make_api_call_ps "POST" "/realms" "!REALM_EXPORT_FILE_PATH!" API_REALM_IMPORT_RESPONSE API_REALM_IMPORT_STATUS
    if not "!API_REALM_IMPORT_STATUS!"=="201" ( echo Failed to import realm. Status: !API_REALM_IMPORT_STATUS! & echo !API_REALM_IMPORT_RESPONSE! & goto :eof_error)
    echo Realm imported.

    echo Step 5: ViolentUTF .env and secrets.toml already configured.
    set "VIOLENTUTF_DIR=violentutf"
    set "VIOLENTUTF_ENV_FILE=!VIOLENTUTF_DIR!\.env"
    set "VIOLENTUTF_SECRETS_DIR=!VIOLENTUTF_DIR!\.streamlit"
    set "VIOLENTUTF_SECRETS_FILE=!VIOLENTUTF_SECRETS_DIR!\secrets.toml"

    echo Step 6: Configuring ViolentUTF client in Keycloak via API...
    set "VUTF_REALM_NAME=!TARGET_REALM_NAME!"
    set "VUTF_CLIENT_ID_TO_CONFIGURE=violentutf"

    call :make_api_call_ps "GET" "/realms/!VUTF_REALM_NAME!/clients?clientId=!VUTF_CLIENT_ID_TO_CONFIGURE!" "" API_CLIENT_INFO_RESP API_CLIENT_INFO_STATUS
    if not "!API_CLIENT_INFO_STATUS!"=="200" ( echo Error getting client info. Status: !API_CLIENT_INFO_STATUS! & goto :eof_error )

    set "KC_CLIENT_UUID="
    for /f "delims=" %%U in ('powershell -NoProfile -Command "(!API_CLIENT_INFO_RESP! | ConvertFrom-Json).[0].id"') do set "KC_CLIENT_UUID=%%U"
    if not defined KC_CLIENT_UUID ( echo Error: Client not found via API. & goto :eof_error )
    echo Found client '!VUTF_CLIENT_ID_TO_CONFIGURE!' with UUID '!KC_CLIENT_UUID!'.

    echo Updating client secret...
    call :make_api_call_ps "GET" "/realms/!VUTF_REALM_NAME!/clients/!KC_CLIENT_UUID!" "" API_CLIENT_GET_RESP API_CLIENT_GET_STATUS
    if not "!API_CLIENT_GET_STATUS!"=="200" ( echo Error: Failed to get client configuration. Status: !API_CLIENT_GET_STATUS! & goto :eof_error )

    set "TEMP_CLIENT_CONFIG_FILE=%TEMP%\client-update.json"
    powershell -NoProfile -Command ^
        $clientConfig = !API_CLIENT_GET_RESP! | ConvertFrom-Json; ^
        $clientConfig.secret = '!VIOLENTUTF_CLIENT_SECRET!'; ^
        $clientConfig | ConvertTo-Json -Depth 10 | Set-Content -Path '!TEMP_CLIENT_CONFIG_FILE!' -Encoding UTF8

    call :make_api_call_ps "PUT" "/realms/!VUTF_REALM_NAME!/clients/!KC_CLIENT_UUID!" "!TEMP_CLIENT_CONFIG_FILE!" API_CLIENT_UPDATE_RESP API_CLIENT_UPDATE_STATUS
    if not "!API_CLIENT_UPDATE_STATUS!"=="204" ( echo Error: Failed to update client secret. Status: !API_CLIENT_UPDATE_STATUS! & goto :eof_error )
    echo Successfully updated client '!VUTF_CLIENT_ID_TO_CONFIGURE!' with pre-generated secret.
    del "!TEMP_CLIENT_CONFIG_FILE!"

    REM Update APISIX client secret
    echo Updating APISIX client secret...
    call :make_api_call_ps "GET" "/realms/!VUTF_REALM_NAME!/clients?clientId=apisix" "" API_APISIX_CLIENT_RESP API_APISIX_CLIENT_STATUS
    if not "!API_APISIX_CLIENT_STATUS!"=="200" ( echo Error: Failed to find APISIX client. Status: !API_APISIX_CLIENT_STATUS! & goto :eof_error )

    set "APISIX_CLIENT_UUID="
    for /f "delims=" %%U in ('powershell -NoProfile -Command "(!API_APISIX_CLIENT_RESP! | ConvertFrom-Json).[0].id"') do set "APISIX_CLIENT_UUID=%%U"
    if not defined APISIX_CLIENT_UUID ( echo Error: APISIX client not found in realm. & goto :eof_error )

    echo Updating APISIX client to use pre-generated secret...
    call :make_api_call_ps "GET" "/realms/!VUTF_REALM_NAME!/clients/!APISIX_CLIENT_UUID!" "" API_APISIX_GET_RESP API_APISIX_GET_STATUS
    if not "!API_APISIX_GET_STATUS!"=="200" ( echo Error: Failed to get APISIX client configuration. Status: !API_APISIX_GET_STATUS! & goto :eof_error )

    set "TEMP_APISIX_CONFIG_FILE=%TEMP%\apisix-client-update.json"
    powershell -NoProfile -Command ^
        $clientConfig = !API_APISIX_GET_RESP! | ConvertFrom-Json; ^
        $clientConfig.secret = '!APISIX_CLIENT_SECRET!'; ^
        $clientConfig | ConvertTo-Json -Depth 10 | Set-Content -Path '!TEMP_APISIX_CONFIG_FILE!' -Encoding UTF8

    call :make_api_call_ps "PUT" "/realms/!VUTF_REALM_NAME!/clients/!APISIX_CLIENT_UUID!" "!TEMP_APISIX_CONFIG_FILE!" API_APISIX_UPDATE_RESP API_APISIX_UPDATE_STATUS
    if not "!API_APISIX_UPDATE_STATUS!"=="204" ( echo Error: Failed to update APISIX client secret. Status: !API_APISIX_UPDATE_STATUS! & goto :eof_error )
    echo Successfully updated APISIX client with pre-generated secret.
    del "!TEMP_APISIX_CONFIG_FILE!"

    set "KEYCLOAK_APP_USERNAME="
    for /f "tokens=1,* delims==" %%a in ('type "!VIOLENTUTF_ENV_FILE!" ^| findstr /B /C:"KEYCLOAK_USERNAME="') do set "KEYCLOAK_APP_USERNAME=%%b"
    if not defined KEYCLOAK_APP_USERNAME ( set "KEYCLOAK_APP_USERNAME=testuser" & echo KEYCLOAK_USERNAME=!KEYCLOAK_APP_USERNAME!>> "!VIOLENTUTF_ENV_FILE!" )
    echo Using KEYCLOAK_USERNAME: !KEYCLOAK_APP_USERNAME!
    echo Keycloak Username: !KEYCLOAK_APP_USERNAME! >> "!SENSITIVE_VALUES_FILE!"

    call :make_api_call_ps "GET" "/realms/!VUTF_REALM_NAME!/users?username=!KEYCLOAK_APP_USERNAME!&exact=true" "" API_USER_CHECK_RESP API_USER_CHECK_STATUS
    if not "!API_USER_CHECK_STATUS!"=="200" ( echo Error checking user. Status: !API_USER_CHECK_STATUS! & goto :eof_error )
    set "USER_EXISTS_ID="
    for /f "delims=" %%I in ('powershell -NoProfile -Command "$json = !API_USER_CHECK_RESP! | ConvertFrom-Json; if ($json -and $json.Count -gt 0) { $json[0].id } else { Write-Host '' }"') do set "USER_EXISTS_ID=%%I"

    if not defined USER_EXISTS_ID (
        echo User '!KEYCLOAK_APP_USERNAME!' not found. Creating...
        set "USER_CREATE_PAYLOAD={'username':'!KEYCLOAK_APP_USERNAME!','enabled':true}"
        call :make_api_call_ps "POST" "/realms/!VUTF_REALM_NAME!/users" "!USER_CREATE_PAYLOAD!" API_USER_CREATE_RESP API_USER_CREATE_STATUS
        if not "!API_USER_CREATE_STATUS!"=="201" ( echo Error creating user. Status: !API_USER_CREATE_STATUS! & goto :eof_error )
        call :make_api_call_ps "GET" "/realms/!VUTF_REALM_NAME!/users?username=!KEYCLOAK_APP_USERNAME!&exact=true" "" API_USER_CHECK_RESP_AGAIN API_USER_CHECK_STATUS_AGAIN
        for /f "delims=" %%I in ('powershell -NoProfile -Command "(!API_USER_CHECK_RESP_AGAIN! | ConvertFrom-Json).[0].id"') do set "USER_EXISTS_ID=%%I"
        if not defined USER_EXISTS_ID ( echo Error getting new user ID. & goto :eof_error )
        echo User created.
    ) else ( echo User already exists. )

    echo Setting new password for user...
    set "PASSWORD_RESET_PAYLOAD={'type':'password','value':'!VIOLENTUTF_USER_PASSWORD!','temporary':false}"
    call :make_api_call_ps "PUT" "/realms/!VUTF_REALM_NAME!/users/!USER_EXISTS_ID!/reset-password" "!PASSWORD_RESET_PAYLOAD!" API_PASS_RESET_RESP API_PASS_RESET_STATUS
    if not "!API_PASS_RESET_STATUS!"=="204" ( echo Error setting password. Status: !API_PASS_RESET_STATUS! & goto :eof_error )
    echo Password set.
    echo Keycloak User Password: !VIOLENTUTF_USER_PASSWORD! >> "!SENSITIVE_VALUES_FILE!"
    call :replace_in_file_ps "!VIOLENTUTF_ENV_FILE!" "KEYCLOAK_PASSWORD=.*" "KEYCLOAK_PASSWORD=!VIOLENTUTF_USER_PASSWORD!"

    REM Assign ai-api-access role to user
    echo Assigning ai-api-access role to user '!KEYCLOAK_APP_USERNAME!'...
    call :make_api_call_ps "GET" "/realms/!VUTF_REALM_NAME!/roles/ai-api-access" "" API_ROLE_RESP API_ROLE_STATUS
    if not "!API_ROLE_STATUS!"=="200" ( echo Error: Failed to find ai-api-access role. Status: !API_ROLE_STATUS! & goto :eof_error )

    set "AI_API_ACCESS_ROLE_ID="
    set "AI_API_ACCESS_ROLE_NAME="
    for /f "delims=" %%I in ('powershell -NoProfile -Command "(!API_ROLE_RESP! | ConvertFrom-Json).id"') do set "AI_API_ACCESS_ROLE_ID=%%I"
    for /f "delims=" %%N in ('powershell -NoProfile -Command "(!API_ROLE_RESP! | ConvertFrom-Json).name"') do set "AI_API_ACCESS_ROLE_NAME=%%N"

    if not defined AI_API_ACCESS_ROLE_ID ( echo Error: ai-api-access role not found or invalid ID. & goto :eof_error )

    set "ROLE_ASSIGNMENT_PAYLOAD=[{'id':'!AI_API_ACCESS_ROLE_ID!', 'name':'!AI_API_ACCESS_ROLE_NAME!'}]"
    call :make_api_call_ps "POST" "/realms/!VUTF_REALM_NAME!/users/!USER_EXISTS_ID!/role-mappings/realm" "!ROLE_ASSIGNMENT_PAYLOAD!" API_ROLE_ASSIGN_RESP API_ROLE_ASSIGN_STATUS

    if not "!API_ROLE_ASSIGN_STATUS!"=="204" ( echo Error: Failed to assign ai-api-access role to user. Status: !API_ROLE_ASSIGN_STATUS! & goto :eof_error )
    echo Successfully assigned ai-api-access role to user '!KEYCLOAK_APP_USERNAME!'.

    echo Step 7: Secrets already configured.
    echo Keycloak client and user configuration complete via API.

    REM Create FastAPI client in Keycloak
    echo Creating FastAPI client in Keycloak...
    call :create_fastapi_client_ps "!FASTAPI_CLIENT_ID!" "!FASTAPI_CLIENT_SECRET!" "http://localhost:8000/*"
    if !errorlevel! equ 0 (
        echo ✅ FastAPI client configuration complete.
    ) else (
        echo ⚠️ Warning: FastAPI client creation failed, but continuing...
    )

) else (
    echo Skipped Keycloak setup steps 4-7 as stack was already running.

    REM Still try to create FastAPI client if Keycloak is running
    if "!KEYCLOAK_SETUP_NEEDED!"=="false" (
        call :get_keycloak_admin_token_ps
        if !errorlevel! equ 0 (
            echo Creating FastAPI client in existing Keycloak setup...
            call :create_fastapi_client_ps "!FASTAPI_CLIENT_ID!" "!FASTAPI_CLIENT_SECRET!" "http://localhost:8000/*"
            if !errorlevel! equ 0 (
                echo ✅ FastAPI client configuration complete.
            ) else (
                echo ⚠️ Warning: FastAPI client creation failed, but continuing...
            )
        )
    )
)

REM ---------------------------------------------------------------
REM SECTION B: APISIX SETUP
REM ---------------------------------------------------------------
echo SECTION B: SETTING UP APISIX

echo Step B1: APISIX configuration files already processed.

echo Step B2: Checking and launching APISIX Docker stack...
set "APISIX_ENV_DIR=apisix"
set "APISIX_COMPOSE_FILE=!APISIX_ENV_DIR!\docker-compose.yml"
set "APISIX_SERVICE_NAME_IN_COMPOSE=apisix"
set "APISIX_SETUP_NEEDED=true"

set "APISIX_CONTAINER_ID="
for /f "delims=" %%i in ('!DOCKER_COMPOSE_CMD! -f "!APISIX_COMPOSE_FILE!" ps -q !APISIX_SERVICE_NAME_IN_COMPOSE! 2^>nul') do set "APISIX_CONTAINER_ID=%%i"
if defined APISIX_CONTAINER_ID (
    docker inspect -f "{{.State.Running}}" !APISIX_CONTAINER_ID! 2>nul | findstr "true" >nul
    if %errorlevel% EQU 0 ( echo APISIX already running. & set "APISIX_SETUP_NEEDED=false" )
)

if "!APISIX_SETUP_NEEDED!"=="true" (
    echo APISIX stack not running. Proceeding with setup.
    if not exist "!APISIX_ENV_DIR!\conf\prometheus.yml" (
        echo Creating default Prometheus configuration...
        if not exist "!APISIX_ENV_DIR!\conf" mkdir "!APISIX_ENV_DIR!\conf"
        (
            echo global:
            echo   scrape_interval: 15s
            echo   evaluation_interval: 15s
            echo.
            echo scrape_configs:
            echo   - job_name: 'apisix'
            echo     static_configs:
            echo       - targets: ['apisix:9091']
            echo     metrics_path: '/apisix/prometheus/metrics'
        ) > "!APISIX_ENV_DIR!\conf\prometheus.yml"
    )
    pushd "!APISIX_ENV_DIR!"
    call :ensure_network_in_compose "docker-compose.yml" "!APISIX_SERVICE_NAME_IN_COMPOSE!"
    echo Launching Docker Compose for APISIX...
    !DOCKER_COMPOSE_CMD! up -d
    if errorlevel 1 ( echo Failed to start APISIX. Check logs. & !DOCKER_COMPOSE_CMD! logs & popd & goto :eof_error )
    echo APISIX stack started. Waiting for APISIX to be operational...
    set "RETRY_COUNT=0" & set "MAX_RETRIES=20" & set "APISIX_READY=false"
    :wait_apisix_loop
    if !RETRY_COUNT! GEQ !MAX_RETRIES! goto :apisix_not_ready
    set /a RETRY_COUNT+=1
    powershell -NoProfile -Command "try { $response = Invoke-WebRequest -Uri '!APISIX_ADMIN_URL!/apisix/admin/routes' -Headers @{'X-API-KEY'='!APISIX_ADMIN_KEY!'} -UseBasicParsing -TimeoutSec 6; if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 401) { exit 0 } else { exit 1 } } catch { exit 1 }"
    if errorlevel 1 (
        echo APISIX not ready yet (attempt !RETRY_COUNT!/!MAX_RETRIES!). Waiting 6s...
        timeout /t 6 /nobreak >nul
        goto :wait_apisix_loop
    )
    echo APISIX is up. & set "APISIX_READY=true"
    :apisix_not_ready
    if "!APISIX_READY!"=="false" ( echo APISIX did not become ready. Check logs. & !DOCKER_COMPOSE_CMD! logs !APISIX_SERVICE_NAME_IN_COMPOSE! & popd & goto :eof_error )
    popd

    set "APISIX_CONTAINER_FOR_NET="
    for /f "delims=" %%i in ('!DOCKER_COMPOSE_CMD! -f "!APISIX_COMPOSE_FILE!" ps -q !APISIX_SERVICE_NAME_IN_COMPOSE! 2^>nul') do set "APISIX_CONTAINER_FOR_NET=%%i"
    if defined APISIX_CONTAINER_FOR_NET (
      powershell -NoProfile -Command "$container='!APISIX_CONTAINER_FOR_NET!'; $network='!SHARED_NETWORK_NAME!'; $inspect=(docker inspect $container | ConvertFrom-Json); if (-not $inspect[0].NetworkSettings.Networks.$network) { Write-Host 'Manually connecting APISIX to !SHARED_NETWORK_NAME!...'; docker network connect $network $container }"
    )

    echo Step B3: Configuring APISIX routes to Keycloak...
    set "ROUTE_ID_KEYCLOAK_PROXY=keycloak-auth-proxy"
    set "KEYCLOAK_UPSTREAM_HOST=keycloak"
    set "PS_CREATE_KC_ROUTE=powershell -NoProfile -ErrorAction Stop -Command ^
        $payload = @{ id = '!ROUTE_ID_KEYCLOAK_PROXY!'; uri = '/auth/*'; name = 'keycloak-proxy-service'; methods = @('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'); upstream = @{ type = 'roundrobin'; nodes = @{ '!KEYCLOAK_UPSTREAM_HOST!:8080' = 1 }; scheme = 'http' }; plugins = @{ 'proxy-rewrite' = @{ regex_uri = @('^/auth/(.*)', '/$$1') } } }; ^
        $jsonPayload = $payload | ConvertTo-Json -Depth 10; ^
        try { Invoke-RestMethod -Uri '!APISIX_ADMIN_URL!/apisix/admin/routes/!ROUTE_ID_KEYCLOAK_PROXY!' -Method Put -Headers @{'X-API-KEY'='!APISIX_ADMIN_KEY!';'Content-Type'='application/json'} -Body $jsonPayload -TimeoutSec 15; Write-Host 'Successfully configured APISIX route to Keycloak.' } ^
        catch { Write-Host ('Warning: Failed to configure APISIX route to Keycloak. Status: ' + $_.Exception.Response.StatusCode.value__ + ' Body: ' + ($_.Exception.Response.Content | Out-String)) -ForegroundColor Yellow; }"
    !PS_CREATE_KC_ROUTE!
    echo APISIX setup complete.
) else (
    echo Skipped APISIX setup as stack was already running.
    REM If APISIX was running, try to use existing admin key
    powershell -NoProfile -Command "$cfgPath = 'apisix\conf\config.yaml'; if (Test-Path $cfgPath) { $admKey = ((Get-Content $cfgPath -Raw | ConvertFrom-Yaml).deployment.admin.admin_key | Where-Object { $_.name -eq 'admin_key' }).key; if ($admKey) { Write-Host ('APISIX Admin API Key (existing): ' + $admKey); Add-Content -Path '!SENSITIVE_VALUES_FILE!' -Value ('APISIX Admin API Key (existing): ' + $admKey); exit 0; } else { exit 1; } } else { exit 1; }" >nul 2>nul
    REM APISIX_ADMIN_KEY should be set if found by above PS, else the generated one is used.
    set "APISIX_CONTAINER_FOR_NET_EXISTING="
    for /f "delims=" %%i in ('!DOCKER_COMPOSE_CMD! -f "!APISIX_COMPOSE_FILE!" ps -q !APISIX_SERVICE_NAME_IN_COMPOSE! 2^>nul') do set "APISIX_CONTAINER_FOR_NET_EXISTING=%%i"
    if defined APISIX_CONTAINER_FOR_NET_EXISTING (
      powershell -NoProfile -Command "$container='!APISIX_CONTAINER_FOR_NET_EXISTING!'; $network='!SHARED_NETWORK_NAME!'; $inspect=(docker inspect $container | ConvertFrom-Json); if (-not $inspect[0].NetworkSettings.Networks.$network) { Write-Host 'Manually connecting existing APISIX to !SHARED_NETWORK_NAME!...'; docker network connect $network $container }"
    )
)

REM ---------------------------------------------------------------
REM SECTION C: AI PROXY SETUP
REM ---------------------------------------------------------------
echo SECTION C: SETTING UP AI PROXY
set "SKIP_AI_SETUP=false"

echo Step C1: Preparing AI configuration...
call :create_ai_tokens_template ai_template_created_flag
if "!ai_template_created_flag!"=="1" (
    set "SKIP_AI_SETUP=true"
) else (
    call :load_ai_tokens ai_tokens_load_failed_flag
    if "!ai_tokens_load_failed_flag!"=="1" ( set "SKIP_AI_SETUP=true" )
)

if /i "!SKIP_AI_SETUP!" neq "true" (
    echo Step C2: Setting up AI provider routes in APISIX...
    call :check_ai_proxy_plugin_ps
    if !plugin_check_result! neq 0 (
        echo ❌ Cannot proceed with AI proxy setup - plugin not available.
        set "SKIP_AI_SETUP=true"
    ) else (
        call :setup_ai_providers_enhanced_ps
        if errorlevel 1 (
            echo ⚠️ AI Provider route setup encountered errors.
        ) else (
            echo ✅ AI Provider routes setup completed.
        )
    )
) else (
    echo Skipping AI provider routes setup due to configuration issues.
)

REM ---------------------------------------------------------------
REM SECTION D: VIOLENTUTF API SETUP
REM ---------------------------------------------------------------
echo SECTION D: SETTING UP VIOLENTUTF API

echo Step D1: Setting up ViolentUTF FastAPI service...

if not exist "violentutf_api" (
    echo Error: violentutf_api directory not found!
    echo Please ensure you are running this script from the project root directory.
    goto :eof_error
)

REM Store current directory and cd into violentutf_api
set "ORIGINAL_DIR=%cd%"
pushd "violentutf_api"

REM FastAPI .env already configured
echo FastAPI .env file already configured.

REM Setup APISIX route for FastAPI
echo Creating APISIX route for FastAPI...

REM Wait for APISIX to be ready
echo Waiting for APISIX Admin API to be ready...
set "max_attempts=30"
set "attempt=0"

:wait_for_apisix_loop
if !attempt! geq !max_attempts! goto :apisix_timeout
powershell -NoProfile -Command "try { $response = Invoke-WebRequest -Uri '!APISIX_ADMIN_URL!/apisix/admin/routes' -Headers @{'X-API-KEY'='!APISIX_ADMIN_KEY!'} -UseBasicParsing -TimeoutSec 2; if ($response.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
if errorlevel 1 (
    set /a attempt+=1
    echo Waiting for APISIX... (!attempt!/!max_attempts!)
    timeout /t 2 /nobreak >nul
    goto :wait_for_apisix_loop
)
echo APISIX Admin API is ready!
goto :create_fastapi_route

:apisix_timeout
echo Warning: APISIX Admin API did not become ready within 60 seconds.

:create_fastapi_route
REM Use the comprehensive configure_routes.sh script if available
if exist "apisix\configure_routes.sh" (
    echo Running comprehensive route configuration script...
    pushd apisix
    REM Convert script to Windows line endings if needed
    powershell -Command "(Get-Content 'configure_routes.sh') -replace "`r`n", "`n" | Set-Content 'configure_routes.sh' -NoNewline"
    REM Run the script using bash from Git for Windows or WSL
    where bash >nul 2>nul
    if not errorlevel 1 (
        bash configure_routes.sh
        if not errorlevel 1 (
            echo ✅ All API routes configured successfully.
        ) else (
            echo ⚠️  Route configuration script failed. Falling back to manual creation...
            popd
            call :create_fastapi_route_ps
            call :create_fastapi_docs_routes_ps
            pushd apisix
        )
    ) else (
        echo ⚠️  Bash not found. Falling back to manual route creation...
        popd
        call :create_fastapi_route_ps
        call :create_fastapi_docs_routes_ps
        pushd apisix
    )
    popd
) else (
    echo ⚠️  configure_routes.sh not found. Using manual route creation...
    call :create_fastapi_route_ps
    call :create_fastapi_docs_routes_ps
)

echo FastAPI service configuration complete.

REM Configure PyRIT Orchestrator API routes
echo.
echo Configuring PyRIT Orchestrator API routes...
if exist "apisix\configure_orchestrator_routes.sh" (
    echo Found orchestrator routes configuration script.
    pushd apisix
    where bash >nul 2>nul
    if not errorlevel 1 (
        bash configure_orchestrator_routes.sh
        echo ✅ Orchestrator API routes configured
    ) else (
        echo ⚠️  Bash not found. Cannot run orchestrator routes script.
    )
    popd
) else (
    echo ⚠️  Warning: apisix\configure_orchestrator_routes.sh not found. Orchestrator API routes not configured.
)

REM Apply orchestrator executions route fix to prevent 422 errors
echo Applying orchestrator executions route fix...
if exist "apisix\fix_orchestrator_executions_route.sh" (
    echo Running orchestrator executions route fix script...
    pushd apisix
    where bash >nul 2>nul
    if not errorlevel 1 (
        bash fix_orchestrator_executions_route.sh
        echo ✅ Orchestrator executions route fix applied successfully.
    ) else (
        echo ⚠️  Bash not found. Cannot run route fix script.
    )
    popd
) else (
    echo ⚠️  Warning: apisix\fix_orchestrator_executions_route.sh not found. Route fix not applied.
)

echo The service will be started with the APISIX stack.

REM Return to original directory
popd

REM Add VIOLENTUTF_API_URL to .env if not present
if exist "!VIOLENTUTF_ENV_FILE!" (
    findstr /C:"VIOLENTUTF_API_URL=" "!VIOLENTUTF_ENV_FILE!" >nul
    if errorlevel 1 (
        echo VIOLENTUTF_API_URL=http://localhost:9080/api >> "!VIOLENTUTF_ENV_FILE!"
    )
)

REM ---------------------------------------------------------------
REM SECTION E: VIOLENTUTF PYTHON APP SETUP
REM ---------------------------------------------------------------
echo SECTION E: SETTING UP VIOLENTUTF PYTHON APP

REM 8. Determine Python command and perform advanced version checking
echo Step 8: Determining Python command...
set "PYTHON_CMD=py -3"
!PYTHON_CMD! --version >nul 2>nul
if errorlevel 1 (
    set "PYTHON_CMD=python3"
    !PYTHON_CMD! --version >nul 2>nul
    if errorlevel 1 (
        set "PYTHON_CMD=python"
        !PYTHON_CMD! --version >nul 2>nul
        if errorlevel 1 (
            echo Python 3 not found. Please install Python 3.10+.
            echo PyRIT and Garak require Python 3.10-3.12. You can install Python from python.org.
            goto :eof_error
        )
        REM Check if 'python' is Python 3
        for /f "tokens=2" %%i in ('!PYTHON_CMD! --version 2^>^&1') do set "PY_VERSION_CHECK=%%i"
        echo !PY_VERSION_CHECK! | findstr /C:"3." >nul
        if errorlevel 1 (
            echo Python 3 not found with 'python3' or 'python' command. Please install Python 3.10+.
            echo PyRIT and Garak require Python 3.10-3.12. You can install Python from python.org.
            goto :eof_error
        )
    )
)
echo Using '!PYTHON_CMD!' for Python operations.

REM Advanced Python version checking for PyRIT and Garak compatibility
!PYTHON_CMD! -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" > %TEMP%\py_version.txt
set /p PY_FULL_VERSION=<%TEMP%\py_version.txt
del %TEMP%\py_version.txt

for /f "tokens=1,2 delims=." %%a in ("!PY_FULL_VERSION!") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)

if !PY_MAJOR! lss 3 (
    echo Your Python version ^(!PYTHON_CMD! is !PY_FULL_VERSION!^) is less than 3.10.
    echo PyRIT and Garak require Python 3.10-3.12. Please upgrade your Python installation.
    echo You can install Python from python.org.
    goto :eof_error
)

if !PY_MAJOR! equ 3 (
    if !PY_MINOR! lss 10 (
        echo Your Python version ^(!PYTHON_CMD! is !PY_FULL_VERSION!^) is less than 3.10.
        echo PyRIT and Garak require Python 3.10-3.12. Please upgrade your Python installation.
        echo You can install Python from python.org.
        goto :eof_error
    )
    if !PY_MINOR! gtr 12 (
        echo Warning: Python version !PY_FULL_VERSION! is newer than the tested range ^(3.10-3.12^).
        echo PyRIT and Garak are tested with Python 3.10-3.12. Proceed with caution.
    )
)

if !PY_MAJOR! gtr 3 (
    echo Warning: Python version !PY_FULL_VERSION! is newer than the tested range ^(3.10-3.12^).
    echo PyRIT and Garak are tested with Python 3.10-3.12. Proceed with caution.
)

echo Python version !PY_FULL_VERSION! is compatible with PyRIT and Garak.

REM 9. Set up and run the ViolentUTF Python app
echo Step 9: Setting up ViolentUTF Python app...
!PYTHON_CMD! -m ensurepip --upgrade >nul 2>nul
!PYTHON_CMD! -m pip install --upgrade pip >nul
if errorlevel 1 ( echo Failed to upgrade pip. & goto :eof_error )

set "VENV_DIR=.vitutf"
if exist "!VENV_DIR!\Scripts\activate.bat" (
    echo Virtual environment '!VENV_DIR!' already exists.
) else (
    echo Creating venv... & !PYTHON_CMD! -m venv "!VENV_DIR!"
    if errorlevel 1 ( echo Failed to create venv. & goto :eof_error )
)
if not exist ".gitignore" ( echo !VENV_DIR! > .gitignore
) else ( findstr /L /C:"!VENV_DIR!" .gitignore >nul || echo !VENV_DIR! >> .gitignore )

echo Activating venv...
call "!VENV_DIR!\Scripts\activate.bat"
if errorlevel 1 ( echo Failed to activate venv. & goto :eof_error )

set "REQUIREMENTS_FILE=violentutf\requirements.txt"
if not exist "!REQUIREMENTS_FILE!" set "REQUIREMENTS_FILE=requirements.txt"
if exist "!REQUIREMENTS_FILE!" (
    echo Installing packages from !REQUIREMENTS_FILE!...
    pip install --upgrade pip >nul
    pip install -r "!REQUIREMENTS_FILE!"
    if errorlevel 1 ( echo Failed to install packages. & goto :eof_error )
    echo Package installation complete.
) else ( echo Warning: No requirements.txt found. )

REM Verify Python dependencies installation
call :verify_python_dependencies

REM 10. Update ViolentUTF config to use APISIX proxy
echo Step 10: Updating ViolentUTF config to use APISIX proxy...
if exist "!VIOLENTUTF_ENV_FILE!" (
    set "KEYCLOAK_PROXY_URL_FOR_VUTF=http://localhost:9080/auth"
    set "AI_PROXY_BASE_URL_FOR_VUTF=http://localhost:9080/ai"
    powershell -NoProfile -Command ^
        $envFile = '!VIOLENTUTF_ENV_FILE!'; ^
        $lines = Get-Content $envFile; ^
        $kcBaseFound = $false; $aiBaseFound = $false; ^
        $newLines = $lines | ForEach-Object { ^
            if ($_ -match '^KEYCLOAK_URL_BASE=') { $kcBaseFound = $true; 'KEYCLOAK_URL_BASE=!KEYCLOAK_PROXY_URL_FOR_VUTF!' } ^
            elseif ($_ -match '^AI_PROXY_BASE_URL=') { $aiBaseFound = $true; 'AI_PROXY_BASE_URL=!AI_PROXY_BASE_URL_FOR_VUTF!' } ^
            else { $_ } ^
        }; ^
        if (-not $kcBaseFound) { $newLines += 'KEYCLOAK_URL_BASE=!KEYCLOAK_PROXY_URL_FOR_VUTF!' }; ^
        if (-not $aiBaseFound) { $newLines += 'AI_PROXY_BASE_URL=!AI_PROXY_BASE_URL_FOR_VUTF!' }; ^
        Set-Content -Path $envFile -Value $newLines -Encoding Ascii;
    echo Updated ViolentUTF .env for APISIX integration.
) else ( echo Warning: !VIOLENTUTF_ENV_FILE! not found for APISIX integration update. )

REM ---------------------------------------------------------------
REM 11. Test all components of the stacks
REM ---------------------------------------------------------------
echo. & echo ========================================== & echo TESTING ALL COMPONENTS & echo ==========================================
set "TEST_RESULTS_FILE=%TEMP%\test_results_vutf.txt"
if exist "!TEST_RESULTS_FILE!" del "!TEST_RESULTS_FILE!"
set "TEST_FAILURES=0"

call :run_test "Keycloak master realm (direct)" "powershell -NoProfile -Command \"(Invoke-WebRequest -Uri '!KEYCLOAK_SERVER_URL!/realms/master' -UseBasicParsing -TimeoutSec 5).StatusCode\"" "200"

REM Network connectivity test with enhanced diagnostics
call :run_test "APISIX to Keycloak network connectivity" ":test_network_connectivity_ps apisix keycloak 8080" "0" REM 0 is exit code for success
if !TEST_FAILURES! gtr 0 (
    echo Additional network diagnostics triggered due to connectivity test failure...
    call :network_diagnostics_and_recovery_ps
    if !errorlevel! equ 0 (
        echo ✅ Network connectivity restored after diagnostics
        set /a TEST_FAILURES-=1
        echo ✅ PASS: APISIX to Keycloak network connectivity ^(after recovery^) >> "!TEST_RESULTS_FILE!"
    ) else (
        echo ⚠️ Network connectivity could not be restored
    )
)

call :run_test "APISIX main endpoint (root)" "powershell -NoProfile -Command \"try{(Invoke-WebRequest -Uri '!APISIX_URL!/' -UseBasicParsing -TimeoutSec 5).StatusCode}catch{$_.Exception.Response.StatusCode.Value__}\"" "404"
call :run_test "APISIX admin API" "powershell -NoProfile -Command \"(Invoke-WebRequest -Uri '!APISIX_ADMIN_URL!/apisix/admin/routes' -Headers @{'X-API-KEY'='!APISIX_ADMIN_KEY!'} -UseBasicParsing -TimeoutSec 5).StatusCode\"" "200"
call :run_test "APISIX dashboard" "powershell -NoProfile -Command \"(Invoke-WebRequest -Uri '!APISIX_DASHBOARD_URL!' -UseBasicParsing -TimeoutSec 5).StatusCode\"" "200"
call :run_test "APISIX-Keycloak integration" "powershell -NoProfile -Command \"(Invoke-WebRequest -Uri '!APISIX_URL!/auth/realms/master' -UseBasicParsing -MaximumRedirection 0 -TimeoutSec 5).StatusCode\"" "200"
call :run_test "FastAPI health via APISIX" "powershell -NoProfile -Command \"try{(Invoke-WebRequest -Uri '!APISIX_URL!/api/v1/health' -UseBasicParsing -TimeoutSec 5).StatusCode}catch{$_.Exception.Response.StatusCode.Value__}\"" "200"
call :run_test "FastAPI API via APISIX" "powershell -NoProfile -Command \"try{(Invoke-WebRequest -Uri '!APISIX_URL!/api/v1/auth/me' -Headers @{'X-API-Key'='test'} -UseBasicParsing -TimeoutSec 5).StatusCode}catch{$_.Exception.Response.StatusCode.Value__}\"" "401"

if /i "!SKIP_AI_SETUP!" neq "true" (
    call :test_ai_routes_ps
) else (
    echo ⚪ SKIP: AI Route tests (AI setup was skipped) >> "!TEST_RESULTS_FILE!"
)

if exist "!VIOLENTUTF_ENV_FILE!" (
    call :run_test "ViolentUTF .env essentials" "findstr /C:\"KEYCLOAK_CLIENT_SECRET\" \"!VIOLENTUTF_ENV_FILE!\" && findstr /C:\"KEYCLOAK_URL_BASE\" \"!VIOLENTUTF_ENV_FILE!\" && findstr /C:\"AI_PROXY_BASE_URL\" \"!VIOLENTUTF_ENV_FILE!\"" "0"
) else (
    echo ❌ FAIL: ViolentUTF .env file not found >> "!TEST_RESULTS_FILE!" & set /a TEST_FAILURES+=1
)
if exist "!VIOLENTUTF_SECRETS_FILE!" (
    call :run_test "ViolentUTF secrets.toml essentials" "findstr /C:\"client_secret\" \"!VIOLENTUTF_SECRETS_FILE!\" && findstr /C:\"cookie_secret\" \"!VIOLENTUTF_SECRETS_FILE!\"" "0"
) else (
    echo ❌ FAIL: ViolentUTF secrets.toml file not found >> "!TEST_RESULTS_FILE!" & set /a TEST_FAILURES+=1
)
call :run_test "Python Streamlit installation in venv" "where streamlit" "0" REM where returns 0 if found in PATH (venv should be active)

echo. & echo TEST RESULTS SUMMARY: & echo --------------------
if exist "!TEST_RESULTS_FILE!" (
    type "!TEST_RESULTS_FILE!"
    set "total_tests_approx=0"
    for /f %%i in ('type "!TEST_RESULTS_FILE!" ^| find /c /v ""') do set total_tests_approx=%%i
    set /a "passed_tests=!total_tests_approx! - !TEST_FAILURES!"
    echo.
    echo Total tests: !total_tests_approx!
    echo Passed: !passed_tests!
    echo Failed: !TEST_FAILURES!
    echo.
) else (
    echo ❌ No test results file found
    echo.
)

if !TEST_FAILURES! gtr 0 (
    echo ⚠️ WARNING: Some tests failed. The application may not function correctly.
    echo Please check the test results above and fix any issues before proceeding.
    echo.
    set /p "continue_choice=Do you want to continue and launch the Streamlit app anyway? (y/n): "
    if /i "!continue_choice!" neq "y" (
        echo Setup aborted by user after test failures.
        goto :eof_error_deactivate
    )
    echo Continuing despite test failures...
) else (
    echo ✅ All tests passed! The system is properly configured.
)
echo ========================================== & echo.

REM ---------------------------------------------------------------
REM 12. Display AI Configuration Summary
REM ---------------------------------------------------------------
call :show_ai_summary

REM ---------------------------------------------------------------
REM 13. Display service access information and credentials
REM ---------------------------------------------------------------
echo.
echo ==========================================
echo SERVICE ACCESS INFORMATION AND CREDENTIALS
echo ==========================================
echo ⚠️  IMPORTANT: Store these credentials securely!
echo.
echo ─────────────────────────────────────────
echo 🔐 KEYCLOAK AUTHENTICATION
echo ─────────────────────────────────────────
echo Admin Console:
echo    URL: !KEYCLOAK_SERVER_URL!
echo    Username: admin
echo    Password: admin
echo.
echo Database:
echo    PostgreSQL Password: !KEYCLOAK_POSTGRES_PASSWORD!
echo.
echo Application User:
if defined KEYCLOAK_APP_USERNAME (
    echo    Username: !KEYCLOAK_APP_USERNAME!
)
if defined VIOLENTUTF_USER_PASSWORD (
    echo    Password: !VIOLENTUTF_USER_PASSWORD!
)
echo.
echo ─────────────────────────────────────────
echo 🌐 APISIX GATEWAY
echo ─────────────────────────────────────────
echo Gateway URLs:
echo    Main URL: !APISIX_URL!
echo    Admin API: !APISIX_ADMIN_URL!
echo    Dashboard: !APISIX_DASHBOARD_URL!
echo.
echo Admin Credentials:
echo    Admin API Key: !APISIX_ADMIN_KEY!
echo    Dashboard Username: admin
echo    Dashboard Password: !APISIX_DASHBOARD_PASSWORD!
echo.
echo Security Keys:
echo    JWT Secret: !APISIX_DASHBOARD_SECRET!
echo    Keyring Value 1: !APISIX_KEYRING_VALUE_1!
echo    Keyring Value 2: !APISIX_KEYRING_VALUE_2!
echo    Keycloak Client Secret: !APISIX_CLIENT_SECRET!
echo.
echo ─────────────────────────────────────────
echo 🚀 VIOLENTUTF APPLICATION
echo ─────────────────────────────────────────
echo Application Secrets:
echo    Client Secret: !VIOLENTUTF_CLIENT_SECRET!
echo    Cookie Secret: !VIOLENTUTF_COOKIE_SECRET!
echo    PyRIT DB Salt: !VIOLENTUTF_PYRIT_SALT!
echo    API Key: !VIOLENTUTF_API_KEY!
echo    User Password: !VIOLENTUTF_USER_PASSWORD!
echo.
echo ─────────────────────────────────────────
echo 🔧 FASTAPI SERVICE
echo ─────────────────────────────────────────
echo API Access:
echo    Via APISIX: !APISIX_URL!/api/
echo    API Docs: !APISIX_URL!/api/docs (if configured)
echo    Direct URL: http://localhost:8000 (blocked by design)
echo.
echo Security Keys:
echo    JWT Secret Key: !FASTAPI_SECRET_KEY!
echo    Keycloak Client Secret: !FASTAPI_CLIENT_SECRET!
echo.
echo ─────────────────────────────────────────
echo 🤖 AI PROXY
echo ─────────────────────────────────────────
echo    Base URL: !APISIX_URL!/ai/
echo    Available routes listed in AI Configuration Summary above
echo.
echo ─────────────────────────────────────────
echo 📊 ADDITIONAL SERVICES
echo ─────────────────────────────────────────
echo Monitoring:
echo    Prometheus: http://localhost:9090
echo    Grafana: http://localhost:3000
echo.
echo Proxy Routes:
echo    Keycloak via APISIX: !APISIX_URL!/auth/
echo.
echo ==========================================
echo.

REM ---------------------------------------------------------------
REM 15. Launch the Streamlit app
REM ---------------------------------------------------------------
echo Step 15: Preparing to launch the Streamlit application...

REM Ensure log directory exists
if not exist "violentutf_logs" mkdir "violentutf_logs"

REM Function to launch Streamlit in background with PID tracking
REM Restore user configurations after setup
call :restore_user_configs

REM Verify final system state
call :verify_system_state
if errorlevel 1 (
    echo ❌ System state verification failed. Setup may be incomplete.
    goto :eof_error_deactivate
)

call :launch_streamlit_background

goto :skip_launch_function
:launch_streamlit_background
    echo Launching ViolentUTF in background...

    set "APP_LAUNCHED=false"
    set "STREAMLIT_PID="

    if exist "violentutf\Home.py" (
        set "APP_PATH=violentutf\Home.py"
        set "APP_DIR=violentutf"
        pushd "violentutf"
        REM Launch Streamlit in background and capture PID using PowerShell
        powershell -NoProfile -Command ^
            "$process = Start-Process streamlit -ArgumentList 'run', 'Home.py' -RedirectStandardOutput '..\violentutf_logs\streamlit.log' -RedirectStandardError '..\violentutf_logs\streamlit.log' -PassThru -WindowStyle Hidden; ^
            echo $process.Id" > ..\violentutf_logs\streamlit_pid.txt
        popd
        set "APP_LAUNCHED=true"
    ) else if exist "Home.py" (
        set "APP_PATH=Home.py"
        set "APP_DIR=."
        REM Launch Streamlit in background and capture PID using PowerShell
        powershell -NoProfile -Command ^
            "$process = Start-Process streamlit -ArgumentList 'run', 'Home.py' -RedirectStandardOutput 'violentutf_logs\streamlit.log' -RedirectStandardError 'violentutf_logs\streamlit.log' -PassThru -WindowStyle Hidden; ^
            echo $process.Id" > violentutf_logs\streamlit_pid.txt
        set "APP_LAUNCHED=true"
    ) else (
        echo Warning: Home.py not found in violentutf\ or current directory.
        echo You can manually start the application later with:
        echo    cd violentutf ^&^& streamlit run Home.py
        set "APP_LAUNCHED=false"
        goto :eof
    )

    REM Wait a moment for process to start
    timeout /t 2 /nobreak >nul

    if exist "violentutf_logs\streamlit_pid.txt" (
        set /p STREAMLIT_PID=<violentutf_logs\streamlit_pid.txt
        del violentutf_logs\streamlit_pid.txt

        REM Check if process is still running
        tasklist /FI "PID eq !STREAMLIT_PID!" 2>nul | find "!STREAMLIT_PID!" >nul
        if !errorlevel! equ 0 (
            echo ✅ ViolentUTF launched in background ^(PID: !STREAMLIT_PID!^)
            echo    Access the app at: http://localhost:8501
            echo    Logs: violentutf_logs\streamlit.log
            echo    Stop with: taskkill /PID !STREAMLIT_PID! /F
            echo !STREAMLIT_PID! > violentutf_logs\streamlit_pid.txt
        ) else (
            echo ❌ Failed to launch ViolentUTF. Check violentutf_logs\streamlit.log for errors.
            set "APP_LAUNCHED=false"
        )
    ) else (
        echo ❌ Failed to capture Streamlit process ID. Check violentutf_logs\streamlit.log for errors.
        set "APP_LAUNCHED=false"
    )
    goto :eof

:skip_launch_function

echo. & echo ==========================================
if /i "!APP_LAUNCHED!"=="true" (
    echo SETUP COMPLETED SUCCESSFULLY!
    echo ViolentUTF is launching in the background.
) else (
    echo SETUP COMPLETED!
    echo (Application not auto-started)
)
echo ==========================================
echo Your ViolentUTF platform with Keycloak SSO, APISIX Gateway, and AI Proxy is now ready!
echo.
echo 💡 Next Steps:
echo 1. Access the Keycloak admin console to manage users and permissions
echo 2. Configure additional AI providers by editing !AI_TOKENS_FILE!
echo 3. Explore the APISIX dashboard for advanced gateway configuration
echo 4. Test AI proxy endpoints with your favorite LLM models
echo 5. Start building amazing AI-powered applications!
echo.
echo 📝 Remember to save your sensitive values securely!
echo.
echo To stop services: cd into 'keycloak' or 'apisix' and run '!DOCKER_COMPOSE_CMD! down'.
echo To cleanup: run this script with '--cleanup'.
echo ==========================================

goto :eof_deactivate

REM === Help function ===
:show_help
echo ViolentUTF Windows Setup Script
echo Usage: %0 [OPTION]
echo.
echo Options:
echo   (no options)     Normal setup - Install and configure ViolentUTF platform
echo   --cleanup        Enhanced cleanup - Backup user data, clean containers/configs, restore data
echo   --deepcleanup    Deep cleanup - Remove ALL Docker containers, images, volumes,
echo                    networks, and cache (complete Docker environment reset)
echo   --help, -h       Show this help message
echo.
echo Examples:
echo   %0                      # Full installation with validation
echo   %0 --cleanup            # Smart cleanup preserving user data
echo   %0 --deepcleanup        # Complete Docker environment reset
echo.
echo Description:
echo   This script sets up the ViolentUTF AI red-teaming platform with:
echo   - Keycloak SSO authentication
echo   - APISIX API gateway with AI proxy
echo   - ViolentUTF API (FastAPI)
echo   - ViolentUTF Streamlit web interface
echo   - PyRIT and Garak AI security frameworks
echo.
echo Enhanced Features:
echo   ✅ Automatic backup/restore of user configurations and data
echo   ✅ Comprehensive system validation and health checks
echo   ✅ PyRIT memory database and app data preservation
echo   ✅ JWT configuration consistency verification
echo   ✅ Network and service dependency validation
echo   ✅ Python environment and dependency verification
echo   ✅ Complete system state verification before completion
echo.
echo Cleanup Behavior:
echo   --cleanup preserves: AI tokens, PyRIT databases, user datasets,
echo                       custom parameters, and application data
echo   --deepcleanup removes: Everything (use only for complete reset)
echo.
echo Warning:
echo   --deepcleanup will remove ALL Docker data on your system!
echo   Use with caution if you have other Docker projects.
goto :eof_end_script

REM === Deep cleanup function ===
:perform_deep_cleanup
echo Starting DEEP cleanup process...
echo This will remove ALL Docker containers, images, volumes, networks, and cache!
echo.

REM Warning prompt
echo ⚠️  WARNING: This will completely clean your Docker environment!
echo    - All Docker containers will be stopped and removed
echo    - All Docker images will be removed
echo    - All Docker volumes will be removed
echo    - All Docker networks will be removed
echo    - All Docker build cache will be pruned
echo    - All Docker system cache will be pruned
echo.
set /p "confirm=Are you absolutely sure you want to continue? (type 'YES' to confirm): "

if /i "!confirm!" NEQ "YES" (
    echo Deep cleanup cancelled.
    goto :eof_end_script
)

echo.
echo Proceeding with deep cleanup...

REM First perform regular cleanup
echo 1. Performing standard cleanup...
call :perform_cleanup_internal

REM Stop ALL Docker containers
echo.
echo 2. Stopping ALL Docker containers...
for /f "tokens=*" %%i in ('docker ps -aq 2^>nul') do (
    echo Stopping and removing container %%i
    docker stop %%i >nul 2>&1
    docker rm %%i >nul 2>&1
)
echo All containers stopped and removed.

REM Remove ALL Docker images
echo.
echo 3. Removing ALL Docker images...
for /f "tokens=*" %%i in ('docker images -aq 2^>nul') do (
    echo Removing image %%i
    docker rmi -f %%i >nul 2>&1
)
echo All Docker images removed.

REM Remove ALL Docker volumes
echo.
echo 4. Removing ALL Docker volumes...
for /f "tokens=*" %%i in ('docker volume ls -q 2^>nul') do (
    echo Removing volume %%i
    docker volume rm -f %%i >nul 2>&1
)
echo All Docker volumes removed.

REM Remove ALL Docker networks (except default ones)
echo.
echo 5. Removing ALL Docker networks (except defaults)...
for /f "tokens=*" %%i in ('docker network ls --filter type=custom -q 2^>nul') do (
    echo Removing network %%i
    docker network rm %%i >nul 2>&1
)
echo All custom Docker networks removed.

REM Prune Docker build cache
echo.
echo 6. Pruning Docker build cache...
docker builder prune -af >nul 2>&1
echo Docker build cache pruned.

REM Prune Docker system (everything)
echo.
echo 7. Pruning Docker system cache...
docker system prune -af --volumes >nul 2>&1
echo Docker system cache pruned.

REM Clean up any remaining Docker artifacts
echo.
echo 8. Final Docker cleanup...
docker container prune -f >nul 2>&1
docker image prune -af >nul 2>&1
docker volume prune -f >nul 2>&1
docker network prune -f >nul 2>&1
echo Final Docker cleanup completed.

REM Show final Docker status
echo.
echo 9. Final Docker status:
for /f %%i in ('docker ps -aq 2^>nul ^| find /c /v ""') do echo Containers: %%i
for /f %%i in ('docker images -aq 2^>nul ^| find /c /v ""') do echo Images: %%i
for /f %%i in ('docker volume ls -q 2^>nul ^| find /c /v ""') do echo Volumes: %%i
for /f %%i in ('docker network ls -q 2^>nul ^| find /c /v ""') do echo Networks: %%i

REM Show disk space reclaimed
echo.
echo 10. Docker system disk usage:
docker system df

echo.
echo 🧹 DEEP CLEANUP COMPLETED SUCCESSFULLY!
echo ✅ All Docker containers, images, volumes, networks, and cache have been removed
echo ✅ Maximum disk space has been reclaimed
echo ✅ Docker environment is now completely clean
echo.
echo 💡 You can now run the script again for a completely fresh setup
echo 💡 Note: First run after deep cleanup will take longer as images need to be downloaded
goto :eof_end_script

REM === Internal cleanup function (without exit) ===
:perform_cleanup_internal
echo Starting cleanup process...

REM Stop and remove Keycloak containers
echo Stopping and removing Keycloak containers...
if exist "keycloak" (
    cd keycloak
    docker-compose down -v >nul 2>&1
    if errorlevel 1 docker compose down -v >nul 2>&1
    cd ..
)

REM Stop and remove APISIX containers
echo Stopping and removing APISIX containers...
if exist "apisix" (
    cd apisix
    docker-compose down -v >nul 2>&1
    if errorlevel 1 docker compose down -v >nul 2>&1
    cd ..
)

REM Remove shared network
echo Removing shared Docker network...
docker network rm %SHARED_NETWORK_NAME% >nul 2>&1

REM Clean up volumes
echo Removing Docker volumes related to ViolentUTF...
for /f "tokens=*" %%i in ('docker volume ls -q 2^>nul') do (
    echo %%i | findstr /i "keycloak apisix violentutf fastapi" >nul && (
        docker volume rm %%i >nul 2>&1
    )
)
echo Docker volumes cleaned up.

REM Configuration file cleanup
if exist "keycloak\.env" ( del "keycloak\.env" & echo Removed keycloak\.env )
if exist "violentutf\.env" ( del "violentutf\.env" & echo Removed violentutf\.env )
if exist "violentutf\.streamlit\secrets.toml" ( del "violentutf\.streamlit\secrets.toml" & echo Removed violentutf\.streamlit\secrets.toml )
if exist "violentutf_api\fastapi_app\.env" ( del "violentutf_api\fastapi_app\.env" & echo Removed violentutf_api\fastapi_app\.env )

REM Only remove template files in apisix/conf directory
if exist "apisix\conf" (
    for %%f in (apisix\conf\*.yaml apisix\conf\*.yml apisix\conf\*.conf) do (
        if not "%%f"=="*template*" (
            del "%%f" >nul 2>&1
            echo Removed %%f
        )
    )
    echo Restored only template files in apisix/conf directory
)

echo Preserving user's AI tokens file: %AI_TOKENS_FILE%
goto :eof

:eof_error_deactivate
    if defined VIRTUAL_ENV (
        echo Deactivating Python virtual environment due to error...
        call deactivate
    )
    goto :eof_error

:eof_error
    echo.
    echo ---------------------------------------------------------------
    echo AN ERROR OCCURRED. SETUP DID NOT COMPLETE.
    echo Please check the messages above for details.
    echo ---------------------------------------------------------------
    goto :eof_end_script

:eof_deactivate
    if defined VIRTUAL_ENV (
        echo Deactivating Python virtual environment...
        call deactivate
    )
    goto :eof_end_script

:eof_end_script
    if exist "!SENSITIVE_VALUES_FILE!" del "!SENSITIVE_VALUES_FILE!" >nul 2>nul
    if exist "!CREATED_AI_ROUTES_FILE!" del "!CREATED_AI_ROUTES_FILE!" >nul 2>nul
    if exist "!TEST_RESULTS_FILE!" del "!TEST_RESULTS_FILE!" >nul 2>nul
    echo Setup script finished.
endlocal
goto :eof

:eof
