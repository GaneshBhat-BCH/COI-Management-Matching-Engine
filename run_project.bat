@echo off
SETLOCAL EnableDelayedExpansion
TITLE COI Management - One-Click Launcher
COLOR 0A
cd /d "%~dp0"

echo.
echo ====================================================
echo      COI MANAGEMENT MATCHING ENGINE
echo      Automated Setup and Launch
echo ====================================================
echo.
echo [INFO] Starting automated setup...
echo.

REM === STEP 1: Check/Install Python ===
echo [STEP 1/5] Checking Python...
echo ------------------------------------------------
set PYTHON_EXE=
where python >nul 2>&1
if !errorlevel! equ 0 (
    set PYTHON_EXE=python
) else (
    where py >nul 2>&1
    if !errorlevel! equ 0 (
        set PYTHON_EXE=py
    ) else (
        where python3 >nul 2>&1
        if !errorlevel! equ 0 (
            set PYTHON_EXE=python3
        )
    )
)

if "!PYTHON_EXE!"=="" (
    echo [!] Python not found. Installing via winget...
    echo [*] This may take 2-3 minutes...
    where winget >nul 2>&1
    if !errorlevel! equ 0 (
        winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
        echo [SUCCESS] Python installed. Please RESTART this script.
        powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Python installed! Please run this script again.', 'Information,OkOnly', 'Restart Required')"
        exit /b
    ) else (
        powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Python is required but winget is not available. Please install Python from python.org', 'Critical,OkOnly', 'Error')"
        exit /b
    )
)
echo [SUCCESS] Python found: !PYTHON_EXE!
echo.

REM === STEP 2: Create Virtual Environment ===
echo [STEP 2/5] Setting up Virtual Environment...
echo ------------------------------------------------
if not exist "backend\venv" (
    echo [*] Creating virtual environment...
    echo [*] Please wait (30-60 seconds)...
    !PYTHON_EXE! -m venv backend\venv
    if !errorlevel! neq 0 (
        powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Failed to create virtual environment!', 'Critical,OkOnly', 'Error')"
        exit /b
    )
    echo [SUCCESS] Virtual environment created
    set NEEDS_INSTALL=1
) else (
    echo [SUCCESS] Virtual environment already exists
    set NEEDS_INSTALL=0
)
echo.

REM === STEP 3: Install Dependencies ===
echo [STEP 3/5] Installing Python Packages...
echo ------------------------------------------------
if !NEEDS_INSTALL! equ 1 (
    echo [*] Installing dependencies...
    echo [*] This may take 2-5 minutes on first run...
    echo [*] Progress: [..................] 0%%
    call backend\venv\Scripts\activate
    python -m pip install --upgrade pip >nul 2>&1
    echo [*] Progress: [####..............] 20%%
    python -m pip install -r backend\requirements.txt
    if !errorlevel! neq 0 (
        powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Failed to install dependencies!', 'Critical,OkOnly', 'Error')"
        exit /b
    )
    echo [*] Progress: [##################] 100%%
    echo [SUCCESS] All packages installed
) else (
    echo [SUCCESS] Dependencies already installed (skipping)
)
echo.

REM === STEP 4: Initialize Database ===
echo [STEP 4/5] Initializing Database...
echo ------------------------------------------------
call backend\venv\Scripts\activate
echo [*] Checking database schema...
python backend\init_db.py >nul 2>&1
if !errorlevel! neq 0 (
    echo [WARNING] Database initialization had issues (may already exist)
) else (
    echo [SUCCESS] Database ready
)
echo.

REM === STEP 5: Start Server ===
echo [STEP 5/5] Starting Server...
echo ------------------------------------------------
echo [*] Cleaning up any existing processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo [*] Launching FastAPI server...
start /B python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 >nul 2>&1

echo [*] Waiting for server to start...
echo [*] Progress: [####..............] 25%%
timeout /t 2 /nobreak >nul
echo [*] Progress: [########..........] 50%%
timeout /t 2 /nobreak >nul
echo [*] Progress: [############......] 75%%
timeout /t 2 /nobreak >nul
echo [*] Progress: [##################] 100%%

REM Health check
curl -s http://localhost:8000/ >nul 2>&1
if !errorlevel! equ 0 (
    echo.
    echo ====================================================
    echo      SERVER IS RUNNING!
    echo ====================================================
    echo      API Docs: http://localhost:8000/docs
    echo ====================================================
    echo.
    powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Project is UP and RUNNING!`n`nAPI Documentation:`nhttp://localhost:8000/docs`n`nClick OK to keep server running.`nClose the console window to stop.', 'Information,OkOnly', 'SUCCESS - Server Ready')"
    echo [INFO] Server is running. Press any key to STOP the server...
    pause >nul
    
    REM Stop server
    echo [*] Stopping server...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    echo [SUCCESS] Server stopped cleanly.
) else (
    echo [ERROR] Server failed to start!
    powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Server failed to start! Check the console for errors.', 'Critical,OkOnly', 'Error')"
)

pause
exit /b
