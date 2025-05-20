**Important Prerequisites for the Windows script:**

1.  **Docker Desktop for Windows:** Must be installed and running, with the `docker` and `docker compose` CLI tools available in your PATH.
2.  **Windows PowerShell:** Available by default on modern Windows systems. The script relies on it for secure random string generation and some file manipulations.
3.  **Python for Windows:** Must be installed (Python 3.9+), and the `py.exe` launcher (or `python.exe`) should be in your PATH.
4.  **`jq.exe`:** You'll need to download `jq` for Windows and place `jq.exe` in a directory that's in your PATH, or specify the full path to it in the script. You can get it from the official `jq` website.
5.  **`kcadm.bat` (Keycloak Admin CLI):**
    * Download the Keycloak server distribution (`.zip`) from the Keycloak website.
    * Extract it. The `kcadm.bat` script is in the `bin` directory of the extracted Keycloak distribution.
    * You'll need to either add this `bin` directory to your PATH or modify the `KCADM_CMD` variable in the script to point to the full path of `kcadm.bat`.
6.  **Sample Files**:
    * Ensure `keycloak\env.sample` exists (e.g., `POSTGRES_PASSWORD=replace_key`).
    * Ensure `violentutf\env.sample` exists (e.g., `KEYCLOAK_CLIENT_SECRET=replace_key`, `KEYCLOAK_USERNAME=your_user`, etc.).
    * Ensure `violentutf\.streamlit\secrets.toml.sample` exists (e.g., `client_secret = "replace_key"`).
    The script will attempt to create basic dummy versions if they are missing, but you should prepare them.

**Before Running:**

1.  **Thoroughly review the script**, especially the `KCADM_PATH` variable and any paths to tools like `jq.exe` if they are not in your system PATH.
2.  **Test in a safe environment.**
3.  Make sure your `.sample` files (`keycloak\env.sample`, `violentutf\env.sample`, `violentutf\.streamlit\secrets.toml.sample`) are in place and have the `replace_key` placeholders where needed.

This script is considerably more complex than its Bash counterparts due to the limitations of traditional batch scripting, hence the reliance on PowerShell for more advanced operations.