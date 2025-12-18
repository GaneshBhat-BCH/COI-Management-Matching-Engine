@echo off
SETLOCAL EnableDelayedExpansion
TITLE COI Management - One-Click Launcher
cd /d "%~dp0"

echo ====================================================
echo      COI Management Matching Engine
echo      Automated Setup and Launch
echo ====================================================
echo.

REM === STEP 1: Check/Install Python ===
echo [1/4] Checking Python...
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
    echo [INFO] Python not found. Installing via winget...
    where winget >nul 2>&1
    if !errorlevel! equ 0 (
        winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
        echo [INFO] Python installed. Please RESTART this script.
        powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Python installed! Please run this script again.', 'Information,OkOnly', 'Restart Required')"
        exit /b
    ) else (
        powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Python is required but winget is not available. Please install Python from python.org', 'Critical,OkOnly', 'Error')"
        exit /b
    )
)
echo [SUCCESS] Python found: !PYTHON_EXE!

REM === STEP 2: Create Virtual Environment ===
echo [2/4] Setting up Virtual Environment...
if not exist "backend\venv" (
    echo [INFO] Creating venv...
    !PYTHON_EXE! -m venv backend\venv
    if !errorlevel! neq 0 (
        powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Failed to create virtual environment!', 'Critical,OkOnly', 'Error')"
        exit /b
    )
    set NEEDS_INSTALL=1
) else (
    echo [SUCCESS] Virtual environment exists
    set NEEDS_INSTALL=0
)

REM === STEP 3: Install Dependencies ===
if !NEEDS_INSTALL! equ 1 (
    echo [3/4] Installing Python packages...
    call backend\venv\Scripts\activate
    python -m pip install --upgrade pip --quiet
    python -m pip install -r backend\requirements.txt --quiet
    if !errorlevel! neq 0 (
        powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Failed to install dependencies!', 'Critical,OkOnly', 'Error')"
        exit /b
    )
    echo [SUCCESS] Dependencies installed
) else (
    echo [3/4] Dependencies already installed
)

REM === STEP 4: Initialize Database ===
echo [4/4] Checking Database...
call backend\venv\Scripts\activate
python backend\init_db.py >nul 2>&1
if !errorlevel! neq 0 (
    echo [WARNING] Database initialization had issues (may already exist)
)

REM === STEP 5: Start Server ===
echo.
echo ====================================================
echo      Starting Server...
echo ====================================================
echo.

REM Kill any existing process on port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Start server in background
start /B python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

REM Wait for server to start
echo [INFO] Waiting for server to start...
timeout /t 5 /nobreak >nul

REM Health check
curl -s http://localhost:8000/ >nul 2>&1
if !errorlevel! equ 0 (
    powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Project is UP and RUNNING!`n`nAPI: http://localhost:8000/docs`n`nClick OK to keep running or close to stop.', 'Information,OkOnly', 'Success')"
    echo.
    echo [SUCCESS] Server is running at http://localhost:8000/docs
    echo Press any key to STOP the server...
    pause >nul
    
    REM Stop server
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
        taskkill /F /PID %%a >nul 2>&1
    )
    echo [INFO] Server stopped.
) else (
    powershell -Command "Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Server failed to start! Check the console for errors.', 'Critical,OkOnly', 'Error')"
)

exit /b
