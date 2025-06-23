# Windows Setup Script Guide

**Important Prerequisites for the Windows Setup Script (`setup_windows.bat`)**

This script automates the setup of the ViolentUTF environment on Windows. Due to the nature of Windows Batch scripting, it heavily relies on PowerShell for many operations.

## Key Features (Updated)

- **Automated Secret Generation**: All secrets are generated upfront before Docker services start
- **No User Prompts**: Setup runs completely unattended
- **Background Streamlit Launch**: Application launches in background, terminal remains available
- **Consolidated Credentials Display**: All secrets shown in one organized section at the end

1.  **Docker Desktop for Windows:**
    * Must be installed and running.
    * Ensure it's operating in **Linux container mode** (usually the default).
    * The `docker` and `docker compose` (or `docker-compose`) CLI tools must be available in your system's PATH. The script will attempt to detect which compose command to use.

2.  **Windows PowerShell:**
    * Required for most script operations, including API calls, JSON handling, secure random string generation, and advanced file manipulations.
    * **Execution Policy:** You may need to adjust your PowerShell execution policy to allow scripts to run. Open PowerShell as an administrator and run `Set-ExecutionPolicy RemoteSigned` or `Set-ExecutionPolicy Unrestricted`. You can check your current policy with `Get-ExecutionPolicy`.

3.  **Python for Windows:**
    * Python 3.9 or newer must be installed.
    * The `py.exe` launcher (typically installed with Python from python.org) or `python.exe` should be in your PATH. The script will attempt to find a suitable Python 3.9+ installation.
    * Ensure `pip` is available and the `venv` module is installed (usually included with Python installations from python.org).

4.  **Sample Configuration Files**:
    * The script expects `.sample` files to exist and will use them as templates. If they are missing, it may attempt to create basic dummy versions, but it's best to have your project's intended sample files in place.
    * `keycloak\env.sample`: For Keycloak environment variables (e.g., `POSTGRES_PASSWORD=replace_key`).
    * `apisix\conf\config.yaml.template`: For APISIX core configuration.
    * `apisix\conf\dashboard.yaml.template`: For APISIX dashboard configuration.
    * `violentutf\env.sample`: For the ViolentUTF application's environment variables (e.g., `KEYCLOAK_CLIENT_SECRET=replace_key`, `KEYCLOAK_USERNAME=testuser`, etc.).
    * `violentutf\.streamlit\secrets.toml.sample`: For Streamlit secrets (e.g., `client_secret = "replace_key"`).
    * `ai-tokens.env` (optional before first run): For AI provider API keys. If not present, the script will create a template named `ai-tokens.env`. You will need to populate this file with your actual API keys and re-run the script (or relevant parts) to fully configure AI proxy routes.

**Before Running:**

1.  **Thoroughly review the `setup_windows.bat` script.** Understand the operations it performs, especially those involving PowerShell and Docker.
2.  **Backup your data:** If you have existing configurations or Docker volumes that might conflict, back them up. The `--cleanup` option is destructive.
3.  **Run in a Test Environment First:** If possible, test the script in a non-critical environment.
4.  **Check `*.template` and `*.sample` files:** Ensure they are present in their respective directories (`keycloak`, `apisix/conf`, `violentutf`, `violentutf/.streamlit`) and contain the expected placeholders (e.g., `replace_key`, `APISIX_ADMIN_KEY_PLACEHOLDER`).
5.  **Run as Administrator (Recommended):** While not strictly required for all operations, running the script as an administrator can prevent permission issues with Docker, network configuration, or file system access in protected locations (though the script primarily works in the local directory).

## What the Script Does

The updated script performs the following operations in order:

1. **Secret Generation Phase**
   - Generates all 14 secure secrets upfront
   - Creates all configuration files with actual secrets (no placeholders)
   - Eliminates circular dependencies between services

2. **Service Setup Phase**
   - Sets up Keycloak (authentication service)
   - Sets up APISIX (API gateway)
   - Configures AI proxy routes
   - Sets up FastAPI service in APISIX stack
   - Installs Python dependencies

3. **Testing Phase**
   - Runs comprehensive tests on all services
   - Continues even if some tests fail (no prompts)

4. **Final Phase**
   - Displays all credentials in organized sections
   - Launches Streamlit app in background
   - Shows next steps and important URLs

## Running the Script

```batch
# Normal setup
setup_windows.bat

# Clean up everything and start fresh
setup_windows.bat --cleanup
```

## Expected Output

At the end of setup, you'll see:

```
==========================================
SERVICE ACCESS INFORMATION AND CREDENTIALS
==========================================
[All your credentials organized by service]

==========================================
SETUP COMPLETED SUCCESSFULLY!
==========================================

Launching ViolentUTF in background...
✓ ViolentUTF launched in background (PID: xxxx)
   Access the app at: http://localhost:8501
   Logs: violentutf_logs\streamlit.log
```

## Troubleshooting

- **PowerShell Execution Policy**: If you see PowerShell errors, run as Administrator: `Set-ExecutionPolicy RemoteSigned`
- **Docker Not Running**: Ensure Docker Desktop is running before starting the script
- **Port Conflicts**: Check that ports 8080, 8501, 9080, 9180, 8000 are not in use
- **Streamlit Won't Start**: Check `violentutf_logs\streamlit.log` for errors

## Post-Setup

After successful setup:
1. Access Streamlit app at http://localhost:8501
2. Access Keycloak admin at http://localhost:8080 (admin/admin)
3. Access APISIX dashboard at http://localhost:9001
4. All API endpoints available through APISIX at http://localhost:9080

Save the displayed credentials securely - you'll need them for system administration.