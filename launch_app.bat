@echo off
setlocal enabledelayedexpansion
title RIMS AI Auditor Pro - Auto-Setup Launcher

echo [SYSTEM] Initializing RIMS AI Auditor...
set SCRIPT_PATH=%~dp0
cd /d "%SCRIPT_PATH%"

:: --- 1. SEARCH FOR PYTHON ---
set PY_CMD=none

if exist "%SCRIPT_PATH%python_env\python.exe" (
    set PY_CMD="%SCRIPT_PATH%python_env\python.exe"
    echo [INFO] Using local Python environment found in 'python_env'.
) else (
    python --version >nul 2>&1
    if !errorlevel! equ 0 (
        set PY_CMD=python
    ) else (
        :: --- 2. AUTO-DOWNLOAD LOGIC ---
        echo [WARNING] Python was not found on your system.
        set /p choice="[PROMPT] Would you like to automatically download a portable Python environment? (Y/N): "
        if /i "!choice!" neq "Y" exit

        echo [SYSTEM] Downloading Portable Python 3.12 (approx. 10MB)...
        powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.12.3/python-3.12.3-embed-amd64.zip', 'python_portable.zip')"
        
        if not exist "python_portable.zip" (
            echo [ERROR] Download failed. Please check your internet connection.
            pause
            exit
        )

        echo [SYSTEM] Extracting Python...
        if not exist "python_env" mkdir "python_env"
        tar -xf python_portable.zip -C python_env
        del python_portable.zip

        :: FIX THE EMBEDDED PATH ISSUE AUTOMATICALLY
        echo [SYSTEM] Configuring local environment...
        if exist "python_env\python312._pth" (
            echo python312.zip> "python_env\python312._pth"
            echo .>> "python_env\python312._pth"
            echo import site>> "python_env\python312._pth"
        )

        :: DOWNLOAD PIP (Embeddable versions don't have it)
        echo [SYSTEM] Bootstrapping pip (Package Manager)...
        powershell -Command "(New-Object System.Net.WebClient).DownloadFile('https://bootstrap.pypa.io/get-pip.py', 'get-pip.py')"
        "%SCRIPT_PATH%python_env\python.exe" get-pip.py --no-warn-script-location
        del get-pip.py

        set PY_CMD="%SCRIPT_PATH%python_env\python.exe"
        echo [SUCCESS] Portable Python is ready.
    )
)

:: --- 3. PIP & DEPENDENCY CHECK ---
echo [SYSTEM] Verifying dependencies...

:: Check if streamlit is already installed
%PY_CMD% -c "import streamlit" >nul 2>&1
if !errorlevel! neq 0 (
    echo [SYSTEM] Installing libraries from requirements.txt...
    %PY_CMD% -m pip install --upgrade pip
    %PY_CMD% -m pip install -r requirements.txt
    if !errorlevel! equ 0 (
        echo setup_complete > .setup_done
        echo [SUCCESS] Environment is fully configured.
    ) else (
        echo [ERROR] Library installation failed.
        pause
        exit
    )
)

:: --- 4. LAUNCH ---
echo [SYSTEM] Launching RIMS AI Auditor Pro...
%PY_CMD% -m streamlit run resume_analyzer_pro.py

if !errorlevel! neq 0 (
    echo.
    echo [ERROR] The application crashed. 
    echo Suggestion: Delete the 'python_env' folder and restart this script to re-download.
)
pause