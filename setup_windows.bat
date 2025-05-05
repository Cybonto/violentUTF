@echo off
REM ---------------------------------------------------------------
REM 1. Check Python version (3.9 or above)
REM    Using "py --version" which is standard on most Windows setups.
REM ---------------------------------------------------------------
for /f "tokens=2 delims= " %%i in ('py --version 2^>nul') do (
    set FULL_PY_VERSION=%%i
)

if NOT DEFINED FULL_PY_VERSION (
    echo "Python not found. Installing latest stable Python via winget..."
    winget install -e --id Python.Python.3
    echo "Please restart your terminal or rerun this script after installation."
    exit /b 1
) else (
    echo "Found Python version: %FULL_PY_VERSION%"
)

REM Check major and minor version
for /f "tokens=1,2 delims=." %%a in ("%FULL_PY_VERSION%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)

if %PY_MAJOR% LSS 3 (
    goto InstallPython
) else if %PY_MAJOR% EQU 3 (
    if %PY_MINOR% LSS 9 (
        goto InstallPython
    )
)

echo "Python 3.9 or above is already installed."
goto SetupEnv

:InstallPython
echo "Installing latest stable Python via winget..."
winget install -e --id Python.Python.3
echo "Please restart your terminal or rerun this script after installation."
exit /b 1

:SetupEnv

REM ---------------------------------------------------------------
REM 2. Install all packages necessary for a python virtual env
REM    (pip is usually included with Python >= 3.4, but ensure it's upgraded)
REM ---------------------------------------------------------------
py -m ensurepip --upgrade
py -m pip install --upgrade pip
REM (Optional) py -m pip install virtualenv (no longer strictly needed if using venv)

REM ---------------------------------------------------------------
REM 3. Create the virtual environment (.vitutf)
REM ---------------------------------------------------------------
if exist ".vitutf" (
    echo "Virtual environment '.vitutf' already exists. Skipping creation."
) else (
    py -m venv .vitutf
    echo "Created virtual environment in .vitutf"
)

REM ---------------------------------------------------------------
REM 4. Ensure .gitignore exists and ignores .vitutf
REM ---------------------------------------------------------------
if not exist ".gitignore" (
    echo ".gitignore not found. Creating .gitignore."
    echo .vitutf> .gitignore
) else (
    findstr /c:"\.vitutf" .gitignore >nul 2>&1
    if errorlevel 1 (
        echo .vitutf>> .gitignore
        echo "Added '.vitutf' to .gitignore."
    ) else (
        echo "'.vitutf' is already in .gitignore."
    )
)

REM ---------------------------------------------------------------
REM 5. Install python packages from requirements.txt
REM ---------------------------------------------------------------
call .\.vitutf\Scripts\activate
if exist "requirements.txt" (
    pip install --upgrade pip
    pip install -r requirements.txt
) else (
    echo "No requirements.txt found. Skipping package installation."
)

REM ---------------------------------------------------------------
REM 6. Launch Streamlit application (RedTeam_Home.py)
REM ---------------------------------------------------------------
echo "Launching the Streamlit application..."
streamlit run Home.py
