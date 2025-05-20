@echo off
setlocal enabledelayedexpansion

REM === Global Keycloak API Variables ===
set "KEYCLOAK_SERVER_URL=http://localhost:8080"
set "ADMIN_USER=admin"
set "ADMIN_PASS=admin"
set "MASTER_REALM=master"
set "ADMIN_CLIENT_ID=admin-cli"
set "ACCESS_TOKEN="

REM Function-like section to generate a random secure string using PowerShell
:generate_secure_string
set "_psc_rand=powershell -NoProfile -Command "$bytes = New-Object byte[] 32; (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($bytes); Write-Host ([Convert]::ToBase64String($bytes) -replace '[/+=]' | ForEach-Object { $_.Substring(0, [System.Math]::Min($_.Length, 32)) })""
for /f "delims=" %%s in ('!_psc_rand!') do set "%1=%%s"
goto :eof

REM Function-like section to obtain Keycloak admin access token using PowerShell
:get_keycloak_admin_token
echo Attempting to obtain Keycloak admin access token...
set "token_payload=client_id=!ADMIN_CLIENT_ID!&grant_type=password&username=!ADMIN_USER!&password=!ADMIN_PASS!"
set "token_url=!KEYCLOAK_SERVER_URL!/realms/!MASTER_REALM!/protocol/openid-connect/token"

set "ps_get_token_command=powershell -NoProfile -Command ^
    try { ^
        $response = Invoke-RestMethod -Uri '!token_url!' -Method Post -Body '!token_payload!' -ContentType 'application/x-www-form-urlencoded'; ^
        Write-Output $response.access_token; ^
        exit 0; ^
    } catch { ^
        Write-Error $_.Exception.Message; ^
        Write-Error $_.Exception.Response.StatusCode; ^
        Write-Error ($_.Exception.Response.GetResponseStream() | Out-String); ^
        exit 1; ^
    }"

for /f "delims=" %%t in ('!ps_get_token_command!') do set "ACCESS_TOKEN=%%t"

if not defined ACCESS_TOKEN (
    echo Error: Could not obtain Keycloak admin access token. PowerShell script might have failed.
    goto :eof_error
)
if "!ACCESS_TOKEN!"=="" (
    echo Error: Obtained empty Keycloak admin access token.
    goto :eof_error
)
echo Successfully obtained Keycloak admin access token.
goto :eof


REM Function-like section to make an authenticated API call to Keycloak using PowerShell
REM Usage: call :make_api_call <HTTP_METHOD> <ENDPOINT_PATH_FROM_ADMIN_ROOT> [JSON_DATA_OR_FILE_PATH_VAR_NAME] <RESPONSE_VAR_NAME> <STATUS_CODE_VAR_NAME>
REM Example: call :make_api_call "GET" "/realms" "" API_RESPONSE API_STATUS
REM Example: set "REALM_JSON_FILE=path\to\realm.json" & call :make_api_call "POST" "/realms" REALM_JSON_FILE API_RESPONSE API_STATUS
REM Example: set "USER_PAYLOAD={'username':'test','enabled':true}" & call :make_api_call "POST" "/realms/myrealm/users" USER_PAYLOAD API_RESPONSE API_STATUS
:make_api_call
set "_METHOD=%~1"
set "_ENDPOINT_PATH=%~2"
set "_DATA_VAR_NAME=%~3"
set "_RESPONSE_VAR=%~4"
set "_STATUS_VAR=%~5"

set "_FULL_URL=!KEYCLOAK_SERVER_URL!/admin!_ENDPOINT_PATH!"
set "_HEADERS=@{'Authorization'='Bearer !ACCESS_TOKEN!'}"
set "_BODY_PARAM="
set "_CONTENT_TYPE_PARAM="

if defined _DATA_VAR_NAME (
    set "_DATA_VALUE=!%_DATA_VAR_NAME%!"
    set "_CONTENT_TYPE_PARAM=; $headers.'Content-Type' = 'application/json'"
    REM Check if _DATA_VALUE is a file path or JSON string
    if exist "!_DATA_VALUE!" (
        set "_BODY_PARAM=; $bodyContent = Get-Content -Path '!_DATA_VALUE!' -Raw; $body = ConvertFrom-Json $bodyContent"
    ) else (
        REM Escape single quotes in JSON string for PowerShell if it's direct JSON
        set "_ESCAPED_DATA_VALUE=!_DATA_VALUE:'=''!"
        set "_BODY_PARAM=; $body = ConvertFrom-Json '!_ESCAPED_DATA_VALUE!'"
    )
)

echo Executing API call: !_METHOD! !_FULL_URL!
set "ps_api_call_command=powershell -NoProfile -Command ^
    $uri = '!_FULL_URL!'; ^
    $method = '!_METHOD!'; ^
    $headers = !_HEADERS! !_CONTENT_TYPE_PARAM!; ^
    $body = $null !_BODY_PARAM!; ^
    try { ^
        $response = Invoke-RestMethod -Uri $uri -Method $method -Headers $headers -Body ($body | ConvertTo-Json -Depth 10 -Compress) -ErrorAction Stop; ^
        Write-Output ('STATUS_CODE:200'); ^
        Write-Output ('RESPONSE_BODY:' + ($response | ConvertTo-Json -Depth 10 -Compress)); ^
    } catch [Microsoft.PowerShell.Commands.HttpResponseException] { ^
        Write-Output ('STATUS_CODE:' + $_.Exception.Response.StatusCode.value__); ^
        $errorResponse = ''; ^
        if ($_.Exception.Response.Content) { $errorResponse = $_.Exception.Response.Content; } ^
        Write-Output ('RESPONSE_BODY:' + $errorResponse); ^
    } catch { ^
        Write-Output ('STATUS_CODE:500'); ^
        Write-Output ('RESPONSE_BODY:Unknown PowerShell error: ' + $_.Exception.Message); ^
    }"
    
REM Clear previous values
set "%_RESPONSE_VAR%="
set "%_STATUS_VAR%="

for /f "tokens=1,* delims=:" %%a in ('!ps_api_call_command!') do (
    if "%%a"=="STATUS_CODE" set "%_STATUS_VAR%=%%b"
    if "%%a"=="RESPONSE_BODY" set "%_RESPONSE_VAR%=%%b"
)
goto :eof


echo Starting ViolentUTF Nightly and Keycloak Setup for Windows (API Version)...

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
where docker-compose >nul 2>nul
if %errorlevel% NEQ 0 (
    where docker-compose >nul 2>nul
    if %errorlevel% NEQ 0 (
        echo Docker Compose (docker compose or docker-compose) could not be found.
        goto :eof_error
    ) else (
        set "DOCKER_COMPOSE_CMD=docker-compose"
    )
)
echo Using Docker Compose command: !DOCKER_COMPOSE_CMD!
docker ps >nul 2>nul
if %errorlevel% NEQ 0 (
    echo Docker daemon is not running. Please start Docker Desktop.
    goto :eof_error
)
echo Docker and Docker Compose check passed.

REM ---------------------------------------------------------------
REM 2. Copy and populate keycloak\.env
REM ---------------------------------------------------------------
echo Step 2: Setting up keycloak\.env...
set "KEYCLOAK_ENV_DIR=keycloak"
set "KEYCLOAK_ENV_SAMPLE=!KEYCLOAK_ENV_DIR!\env.sample"
set "KEYCLOAK_ENV_FILE=!KEYCLOAK_ENV_DIR!\.env"

if not exist "!KEYCLOAK_ENV_SAMPLE!" (
    echo Error: !KEYCLOAK_ENV_SAMPLE! not found!
    if not exist "!KEYCLOAK_ENV_DIR!" mkdir "!KEYCLOAK_ENV_DIR!"
    echo POSTGRES_PASSWORD=replace_key > "!KEYCLOAK_ENV_SAMPLE!"
    echo Created a dummy !KEYCLOAK_ENV_SAMPLE!.
)
copy /Y "!KEYCLOAK_ENV_SAMPLE!" "!KEYCLOAK_ENV_FILE!" >nul
echo Copied !KEYCLOAK_ENV_SAMPLE! to !KEYCLOAK_ENV_FILE!.

echo Replacing 'replace_key' placeholders in !KEYCLOAK_ENV_FILE!...
:replace_loop_keycloak_env_api
  set "ps_check_replace_key=powershell -NoProfile -Command \"(Get-Content -Path '!KEYCLOAK_ENV_FILE!' -Raw) -match 'replace_key'\""
  for /f "delims=" %%c in ('!ps_check_replace_key!') do (
    if "%%c"=="False" goto :replace_loop_keycloak_env_api_done
  )
  call :generate_secure_string UNIQUE_RANDOM_VAL_API
  powershell -NoProfile -Command "$content = Get-Content -Path '!KEYCLOAK_ENV_FILE!' -Raw; $newContent = $content -replace 'replace_key', '!UNIQUE_RANDOM_VAL_API!', 1; Set-Content -Path '!KEYCLOAK_ENV_FILE!' -Value $newContent -NoNewline -Encoding Ascii"
  goto :replace_loop_keycloak_env_api
:replace_loop_keycloak_env_api_done
echo 'replace_key' placeholders in !KEYCLOAK_ENV_FILE! processed.
echo Keycloak .env file content:
type "!KEYCLOAK_ENV_FILE!"

REM ---------------------------------------------------------------
REM 3. Check Keycloak stack and launch if not running
REM ---------------------------------------------------------------
echo Step 3: Checking and launching Keycloak Docker stack...
set "KEYCLOAK_SERVICE_NAME_IN_COMPOSE=keycloak"
set "KEYCLOAK_SETUP_NEEDED=true"

set "CHECK_KC_RUNNING_CMD=!DOCKER_COMPOSE_CMD! -f \"!KEYCLOAK_ENV_DIR!\docker-compose.yml\" ps -q !KEYCLOAK_SERVICE_NAME_IN_COMPOSE!"
set "KC_CONTAINER_ID="
for /f "delims=" %%i in ('!CHECK_KC_RUNNING_CMD! 2^>nul') do set "KC_CONTAINER_ID=%%i"

if defined KC_CONTAINER_ID (
    docker inspect -f "{{.State.Running}}" !KC_CONTAINER_ID! 2>nul | findstr "true" >nul
    if %errorlevel% EQU 0 (
        echo Keycloak service '!KEYCLOAK_SERVICE_NAME_IN_COMPOSE!' appears to be already running. Skipping to step 8.
        set "KEYCLOAK_SETUP_NEEDED=false"
    )
)

if "!KEYCLOAK_SETUP_NEEDED!"=="true" (
    echo Keycloak stack not found or not running. Proceeding with setup.
    pushd "!KEYCLOAK_ENV_DIR!"
    if errorlevel 1 ( echo Failed to cd into !KEYCLOAK_ENV_DIR!; goto :eof_error )
    
    echo Launching Docker Compose for Keycloak...
    !DOCKER_COMPOSE_CMD! up -d
    if errorlevel 1 (
        echo Failed to start Keycloak stack. Check Docker Compose logs.
        !DOCKER_COMPOSE_CMD! logs
        popd
        goto :eof_error
    )
    echo Keycloak stack started successfully.
    echo Waiting for Keycloak to be fully operational...
    set "RETRY_COUNT=0"
    set "MAX_RETRIES=30"
    set "KEYCLOAK_READY=false"
    :wait_keycloak_loop_api
    if !RETRY_COUNT! GEQ !MAX_RETRIES! goto :keycloak_not_ready_api
    set /a RETRY_COUNT+=1
    set "ps_check_kc_health=powershell -NoProfile -Command try { $response = Invoke-WebRequest -Uri '!KEYCLOAK_SERVER_URL!/realms/master' -UseBasicParsing -TimeoutSec 5; if ($response.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
    !ps_check_kc_health!
    if errorlevel 1 (
        echo Keycloak not ready yet (attempt !RETRY_COUNT!/!MAX_RETRIES!). Waiting 10 seconds...
        timeout /t 10 /nobreak >nul
        goto :wait_keycloak_loop_api
    )
    echo Keycloak is up and responding.
    set "KEYCLOAK_READY=true"
    :keycloak_not_ready_api
    if "!KEYCLOAK_READY!"=="false" (
        echo Keycloak did not become ready in time. Please check Docker logs.
        !DOCKER_COMPOSE_CMD! logs !KEYCLOAK_SERVICE_NAME_IN_COMPOSE!
        popd
        goto :eof_error
    )
    popd
)


if "!KEYCLOAK_SETUP_NEEDED!"=="true" (
    call :get_keycloak_admin_token
    if errorlevel 1 goto :eof_error

    REM ---------------------------------------------------------------
    REM 4. Import realm-export.json to Keycloak via API
    REM ---------------------------------------------------------------
    echo Step 4: Importing Keycloak realm via API...
    set "REALM_EXPORT_FILE_PATH=!KEYCLOAK_ENV_DIR!\realm-export.json"

    if not exist "!REALM_EXPORT_FILE_PATH!" (
        echo Error: !REALM_EXPORT_FILE_PATH! not found!
        goto :eof_error
    )
    
    set "ps_get_realm_name=powershell -NoProfile -Command \"(Get-Content -Path '!REALM_EXPORT_FILE_PATH!' -Raw | ConvertFrom-Json).realm\""
    for /f "delims=" %%N in ('!ps_get_realm_name!') do set "TARGET_REALM_NAME=%%N"

    if not defined TARGET_REALM_NAME (
        echo Error: Could not extract realm name from !REALM_EXPORT_FILE_PATH!
        goto :eof_error
    )
    echo Target realm name: !TARGET_REALM_NAME!

    call :make_api_call "GET" "/realms/!TARGET_REALM_NAME!" "" API_REALM_CHECK_RESPONSE API_REALM_CHECK_STATUS
    if "!API_REALM_CHECK_STATUS!"=="200" (
        echo Realm '!TARGET_REALM_NAME!' already exists. Deleting and re-importing.
        call :make_api_call "DELETE" "/realms/!TARGET_REALM_NAME!" "" API_REALM_DELETE_RESPONSE API_REALM_DELETE_STATUS
        if not "!API_REALM_DELETE_STATUS!"=="204" (
            echo Failed to delete existing realm '!TARGET_REALM_NAME!'. Status: !API_REALM_DELETE_STATUS!
            echo Response: !API_REALM_DELETE_RESPONSE!
            goto :eof_error
        )
        echo Existing realm '!TARGET_REALM_NAME!' deleted.
    ) else if not "!API_REALM_CHECK_STATUS!"=="404" (
        echo Error checking for realm '!TARGET_REALM_NAME!'. Status: !API_REALM_CHECK_STATUS!
        echo Response: !API_REALM_CHECK_RESPONSE!
        goto :eof_error
    )

    echo Importing realm '!TARGET_REALM_NAME!' from !REALM_EXPORT_FILE_PATH! via API...
    set "REALM_FILE_VAR_FOR_API=!REALM_EXPORT_FILE_PATH!"
    call :make_api_call "POST" "/realms" REALM_FILE_VAR_FOR_API API_REALM_IMPORT_RESPONSE API_REALM_IMPORT_STATUS
    if "!API_REALM_IMPORT_STATUS!"=="201" (
        echo Realm '!TARGET_REALM_NAME!' imported successfully via API.
    ) else (
        echo Failed to import realm '!TARGET_REALM_NAME!' via API. Status: !API_REALM_IMPORT_STATUS!
        echo Response: !API_REALM_IMPORT_RESPONSE!
        goto :eof_error
    )

    REM ---------------------------------------------------------------
    REM 5. Copy violentutf env.sample and secrets.toml.sample
    REM ---------------------------------------------------------------
    echo Step 5: Setting up violentutf .env and secrets.toml...
    set "VIOLENTUTF_DIR=violentutf"
    set "VIOLENTUTF_ENV_SAMPLE=!VIOLENTUTF_DIR!\env.sample"
    set "VIOLENTUTF_ENV_FILE=!VIOLENTUTF_DIR!\.env"
    set "VIOLENTUTF_SECRETS_DIR=!VIOLENTUTF_DIR!\.streamlit"
    set "VIOLENTUTF_SECRETS_SAMPLE=!VIOLENTUTF_SECRETS_DIR!\secrets.toml.sample"
    set "VIOLENTUTF_SECRETS_FILE=!VIOLENTUTF_SECRETS_DIR!\secrets.toml"

    if not exist "!VIOLENTUTF_ENV_SAMPLE!" (
        if not exist "!VIOLENTUTF_DIR!" mkdir "!VIOLENTUTF_DIR!"
        (
            echo KEYCLOAK_CLIENT_SECRET=replace_client_secret
            echo KEYCLOAK_USERNAME=testuser
            echo KEYCLOAK_PASSWORD=replace_password
            echo PYRIT_DB_SALT=replace_pyrit_salt
        ) > "!VIOLENTUTF_ENV_SAMPLE!"
    )
    copy /Y "!VIOLENTUTF_ENV_SAMPLE!" "!VIOLENTUTF_ENV_FILE!" >nul
    echo Copied !VIOLENTUTF_ENV_SAMPLE! to !VIOLENTUTF_ENV_FILE!.

    if not exist "!VIOLENTUTF_SECRETS_DIR!" mkdir "!VIOLENTUTF_SECRETS_DIR!"
    if not exist "!VIOLENTUTF_SECRETS_SAMPLE!" (
        (
            echo client_secret = "replace_client_secret"
            echo cookie_secret = "replace_cookie_secret"
        ) > "!VIOLENTUTF_SECRETS_SAMPLE!"
    )
    copy /Y "!VIOLENTUTF_SECRETS_SAMPLE!" "!VIOLENTUTF_SECRETS_FILE!" >nul
    echo Copied !VIOLENTUTF_SECRETS_SAMPLE! to !VIOLENTUTF_SECRETS_FILE!.

    REM ---------------------------------------------------------------
    REM 6. Keycloak API changes for ViolentUTF realm/client
    REM ---------------------------------------------------------------
    echo Step 6: Configuring ViolentUTF client in Keycloak via API...
    set "VUTF_REALM_NAME=!TARGET_REALM_NAME!"
    set "VUTF_CLIENT_ID_TO_CONFIGURE=violentutf"

    call :make_api_call "GET" "/realms/!VUTF_REALM_NAME!/clients?clientId=!VUTF_CLIENT_ID_TO_CONFIGURE!" "" API_CLIENT_INFO_RESP API_CLIENT_INFO_STATUS
    if not "!API_CLIENT_INFO_STATUS!"=="200" (
        echo Error: Could not get client info for '!VUTF_CLIENT_ID_TO_CONFIGURE!'. Status: !API_CLIENT_INFO_STATUS!
        echo Response: !API_CLIENT_INFO_RESP!
        goto :eof_error
    )
    
    set "ps_get_client_uuid=powershell -NoProfile -Command \"(!API_CLIENT_INFO_RESP! | ConvertFrom-Json).[0].id\""
    for /f "delims=" %%U in ('!ps_get_client_uuid!') do set "KC_CLIENT_UUID=%%U"

    if not defined KC_CLIENT_UUID (
        echo Error: Client '!VUTF_CLIENT_ID_TO_CONFIGURE!' not found in realm '!VUTF_REALM_NAME!' via API.
        goto :eof_error
    )
    echo Found client '!VUTF_CLIENT_ID_TO_CONFIGURE!' with UUID '!KC_CLIENT_UUID!'.

    echo Regenerating client secret for '!VUTF_CLIENT_ID_TO_CONFIGURE!' via API...
    call :make_api_call "POST" "/realms/!VUTF_REALM_NAME!/clients/!KC_CLIENT_UUID!/client-secret" "" API_SECRET_RESP API_SECRET_STATUS
    if not "!API_SECRET_STATUS!"=="200" (
        echo Error: Failed to regenerate client secret via API. Status: !API_SECRET_STATUS!
        echo Response: !API_SECRET_RESP!
        goto :eof_error
    )
    set "ps_get_secret_value=powershell -NoProfile -Command \"(!API_SECRET_RESP! | ConvertFrom-Json).value\""
    for /f "delims=" %%S in ('!ps_get_secret_value!') do set "NEW_CLIENT_SECRET=%%S"
    
    if not defined NEW_CLIENT_SECRET (
        echo Error: Failed to parse new client secret from API response.
        goto :eof_error
    )
    echo New client secret generated via API.

    powershell -NoProfile -Command "(Get-Content -Path '!VIOLENTUTF_ENV_FILE!') | ForEach-Object { $_ -replace '^KEYCLOAK_CLIENT_SECRET=.*$', ('KEYCLOAK_CLIENT_SECRET=' + '!NEW_CLIENT_SECRET!') } | Set-Content -Path '!VIOLENTUTF_ENV_FILE!' -Encoding Ascii"
    powershell -NoProfile -Command "$newClientSecret = '!NEW_CLIENT_SECRET!'; $tomlContent = Get-Content -Path '!VIOLENTUTF_SECRETS_FILE!' -Raw; $tomlContent -replace '(?m)^client_secret\s*=\s*\".*\"$', ('client_secret = \"' + $newClientSecret + '\"') | Set-Content -Path '!VIOLENTUTF_SECRETS_FILE!' -Encoding UTF8"
    echo Updated KEYCLOAK_CLIENT_SECRET in !VIOLENTUTF_ENV_FILE! and client_secret in !VIOLENTUTF_SECRETS_FILE!.

    set "KEYCLOAK_APP_USERNAME="
    for /f "tokens=1,* delims==" %%a in ('type "!VIOLENTUTF_ENV_FILE!" ^| findstr /B /C:"KEYCLOAK_USERNAME="') do (
        set "KEYCLOAK_APP_USERNAME=%%b"
    )
    if not defined KEYCLOAK_APP_USERNAME (
        set "KEYCLOAK_APP_USERNAME=testuser"
        echo KEYCLOAK_USERNAME=!KEYCLOAK_APP_USERNAME!>> "!VIOLENTUTF_ENV_FILE!"
    )
    echo Using KEYCLOAK_USERNAME: !KEYCLOAK_APP_USERNAME!

    call :make_api_call "GET" "/realms/!VUTF_REALM_NAME!/users?username=!KEYCLOAK_APP_USERNAME!" "" API_USER_CHECK_RESP API_USER_CHECK_STATUS
    if not "!API_USER_CHECK_STATUS!"=="200" (
        echo Error checking for user '!KEYCLOAK_APP_USERNAME!'. Status: !API_USER_CHECK_STATUS!
        echo Response: !API_USER_CHECK_RESP!
        goto :eof_error
    )
    set "ps_get_user_id=powershell -NoProfile -Command \"(!API_USER_CHECK_RESP! | ConvertFrom-Json).[0].id\""
    set "USER_EXISTS_ID="
    for /f "delims=" %%I in ('!ps_get_user_id!') do set "USER_EXISTS_ID=%%I"

    if not defined USER_EXISTS_ID (
        echo User '!KEYCLOAK_APP_USERNAME!' not found. Creating user via API...
        set "USER_CREATE_PAYLOAD={'username':'!KEYCLOAK_APP_USERNAME!','enabled':true}"
        call :make_api_call "POST" "/realms/!VUTF_REALM_NAME!/users" USER_CREATE_PAYLOAD API_USER_CREATE_RESP API_USER_CREATE_STATUS
        if not "!API_USER_CREATE_STATUS!"=="201" (
            echo Error: Failed to create user '!KEYCLOAK_APP_USERNAME!' via API. Status: !API_USER_CREATE_STATUS!
            echo Response: !API_USER_CREATE_RESP!
            goto :eof_error
        )
        call :make_api_call "GET" "/realms/!VUTF_REALM_NAME!/users?username=!KEYCLOAK_APP_USERNAME!" "" API_USER_CHECK_RESP_AGAIN API_USER_CHECK_STATUS_AGAIN
        set "ps_get_user_id_again=powershell -NoProfile -Command \"(!API_USER_CHECK_RESP_AGAIN! | ConvertFrom-Json).[0].id\""
        for /f "delims=" %%I in ('!ps_get_user_id_again!') do set "USER_EXISTS_ID=%%I"
        if not defined USER_EXISTS_ID (
            echo Error: Failed to retrieve ID for newly created user '!KEYCLOAK_APP_USERNAME!'.
            goto :eof_error
        )
        echo User '!KEYCLOAK_APP_USERNAME!' created with ID '!USER_EXISTS_ID!'.
    ) else (
        echo User '!KEYCLOAK_APP_USERNAME!' already exists with ID '!USER_EXISTS_ID!'.
    )

    echo Setting a new password for user '!KEYCLOAK_APP_USERNAME!' via API...
    call :generate_secure_string NEW_USER_PASSWORD_API
    set "PASSWORD_RESET_PAYLOAD={'type':'password','value':'!NEW_USER_PASSWORD_API!','temporary':false}"
    call :make_api_call "PUT" "/realms/!VUTF_REALM_NAME!/users/!USER_EXISTS_ID!/reset-password" PASSWORD_RESET_PAYLOAD API_PASS_RESET_RESP API_PASS_RESET_STATUS
    if not "!API_PASS_RESET_STATUS!"=="204" (
        echo Error: Failed to set password for user '!KEYCLOAK_APP_USERNAME!' via API. Status: !API_PASS_RESET_STATUS!
        echo Response: !API_PASS_RESET_RESP!
        goto :eof_error
    )
    echo Password for user '!KEYCLOAK_APP_USERNAME!' has been set via API.

    powershell -NoProfile -Command "(Get-Content -Path '!VIOLENTUTF_ENV_FILE!') | ForEach-Object { $_ -replace '^KEYCLOAK_PASSWORD=.*$', ('KEYCLOAK_PASSWORD=' + '!NEW_USER_PASSWORD_API!') } | Set-Content -Path '!VIOLENTUTF_ENV_FILE!' -Encoding Ascii"
    echo Updated KEYCLOAK_PASSWORD in !VIOLENTUTF_ENV_FILE!.

    REM ---------------------------------------------------------------
    REM 7. Generate secure secrets for PYRIT_DB_SALT and cookie_secret
    REM ---------------------------------------------------------------
    echo Step 7: Generating other secure secrets...
    call :generate_secure_string NEW_PYRIT_SALT_API
    call :generate_secure_string NEW_COOKIE_SECRET_API

    powershell -NoProfile -Command "(Get-Content -Path '!VIOLENTUTF_ENV_FILE!') | ForEach-Object { $_ -replace '^PYRIT_DB_SALT=.*$', ('PYRIT_DB_SALT=' + '!NEW_PYRIT_SALT_API!') } | Set-Content -Path '!VIOLENTUTF_ENV_FILE!' -Encoding Ascii"
    powershell -NoProfile -Command "$newCookieSecret = '!NEW_COOKIE_SECRET_API!'; $tomlContent = Get-Content -Path '!VIOLENTUTF_SECRETS_FILE!' -Raw; $tomlContent -replace '(?m)^cookie_secret\s*=\s*\".*\"$', ('cookie_secret = \"' + $newCookieSecret + '\"') | Set-Content -Path '!VIOLENTUTF_SECRETS_FILE!' -Encoding UTF8"
    echo Updated PYRIT_DB_SALT in !VIOLENTUTF_ENV_FILE! and cookie_secret in !VIOLENTUTF_SECRETS_FILE!.

    echo Keycloak client and user configuration complete via API.
) else (
    echo Skipped Keycloak setup steps 4-7 as stack was already running.
)

REM ---------------------------------------------------------------
REM 8. Check Python executable (py -3 or python)
REM ---------------------------------------------------------------
echo Step 8: Determining Python command...
set "PYTHON_CMD=py -3"
!PYTHON_CMD! --version >nul 2>nul
if errorlevel 1 (
    set "PYTHON_CMD=python"
    !PYTHON_CMD! --version >nul 2>nul
    if errorlevel 1 (
        echo Python 3.9+ not found using 'py -3' or 'python'. Please install Python.
        goto :eof_error
    )
)
echo Using '!PYTHON_CMD!' for Python operations.
for /f "tokens=2 delims=." %%v in ('!PYTHON_CMD! --version 2^>^&1 ^| findstr /R /C:"Python 3\.[0-9][0-9]*"') do set "PY_MINOR_VERSION=%%v"
if not defined PY_MINOR_VERSION (
    for /f "tokens=2 delims=." %%v in ('!PYTHON_CMD! --version 2^>^&1 ^| findstr /R /C:"Python 3\.[0-9]"') do set "PY_MINOR_VERSION=%%v"
)
if defined PY_MINOR_VERSION (
    if !PY_MINOR_VERSION! LSS 9 (
        echo Your Python version 3.!PY_MINOR_VERSION! is less than 3.9. Please upgrade.
        goto :eof_error
    )
) else (
    echo Could not reliably determine Python 3 minor version. Proceeding with caution.
)
echo Python version check passed.

REM ---------------------------------------------------------------
REM 9. Proceed with the rest of the existing script
REM ---------------------------------------------------------------
echo Step 9: Proceeding with existing ViolentUTF Python setup...

!PYTHON_CMD! -m ensurepip --upgrade >nul 2>nul
!PYTHON_CMD! -m pip install --upgrade pip >nul
if errorlevel 1 ( echo Failed to upgrade pip.; goto :eof_error )

set "VENV_DIR=.vitutf"
if exist "!VENV_DIR!\Scripts\activate.bat" (
    echo Virtual environment '!VENV_DIR!' already exists.
) else (
    echo Creating virtual environment in !VENV_DIR!...
    !PYTHON_CMD! -m venv "!VENV_DIR!"
    if errorlevel 1 ( echo Failed to create virtual environment.; goto :eof_error )
    echo Created virtual environment in !VENV_DIR!.
)

if not exist ".gitignore" (
    echo !VENV_DIR! > .gitignore
) else (
    findstr /L /C:"!VENV_DIR!" .gitignore >nul
    if errorlevel 1 ( echo !VENV_DIR! >> .gitignore )
)

echo Activating virtual environment: !VENV_DIR!
call "!VENV_DIR!\Scripts\activate.bat"
if errorlevel 1 ( echo Failed to activate venv.; goto :eof_error )

set "REQUIREMENTS_FILE_PY=violentutf\requirements.txt"
if not exist "!REQUIREMENTS_FILE_PY!" (
    set "REQUIREMENTS_FILE_PY=requirements.txt"
)
if exist "!REQUIREMENTS_FILE_PY!" (
    echo Installing packages from !REQUIREMENTS_FILE_PY!...
    pip install --upgrade pip >nul
    pip install -r "!REQUIREMENTS_FILE_PY!"
    if errorlevel 1 ( echo Failed to install packages.; goto :eof_error )
    echo Package installation complete.
) else (
    echo Warning: No requirements.txt found.
)

echo Launching the Streamlit application...
if exist "violentutf\Home.py" (
    pushd "violentutf"
    streamlit run Home.py
    popd
) else if exist "Home.py" (
    streamlit run Home.py
) else (
    echo Could not find Home.py.
    goto :eof_error
)

echo Setup script finished successfully.
goto :eof

:eof_error
echo.
echo An error occurred. Setup did not complete.
exit /b 1

:eof
endlocal