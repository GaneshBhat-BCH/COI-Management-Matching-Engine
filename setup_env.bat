@echo off
TITLE COI Management Matching Engine - Environment Setup
echo ====================================================
echo      Setting up AI Backend Environment
echo      COI Management Matching Engine
echo ====================================================

cd /d "%~dp0"

REM 1. Check Python
set PYTHON_EXE=
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_EXE=python
) else (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_EXE=py
    ) else (
        where python3 >nul 2>&1
        if %errorlevel% equ 0 (
            set PYTHON_EXE=python3
        )
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from python.org and check "Add to PATH".
    pause
    exit /b
)

echo [INFO] Using %PYTHON_EXE% for setup.
%PYTHON_EXE% --version

REM 2. Create Virtual Environment if it doesn't exist
if not exist "backend\venv" (
    echo [INFO] Creating Virtual Environment (backend/venv)...
    %PYTHON_EXE% -m venv backend\venv
    set NEEDS_INSTALL=true
) else (
    echo [INFO] Virtual Environment already exists.
    if "%~1"=="--auto" (
        set NEEDS_INSTALL=false
    ) else (
        set /p REINSTALL="Do you want to re-install/update dependencies? (y/n): "
    )
)

if /i "%REINSTALL%"=="y" set NEEDS_INSTALL=true

REM 3. Install Dependencies if needed
if "%NEEDS_INSTALL%"=="true" (
    echo [INFO] Installing/Updating requirements...
    call backend\venv\Scripts\activate
    python -m pip install --upgrade pip
    python -m pip install -r backend\requirements.txt
) else (
    echo [INFO] Skipping dependency installation for speed.
)

REM 4. Check .env
if not exist "backend\.env" (
    echo.
    echo [WARNING] backend\.env file is MISSING!
    echo Please create it using the template or copy your API keys.
) else (
    echo [INFO] .env file found.
)

echo.
echo ====================================================
echo      Setup Complete! 
echo ====================================================

if "%~1"=="--auto" exit /b

set /p RUN_INIT="Do you want to initialize the database now? (y/n): "
if /i "%RUN_INIT%"=="y" (
    call init_db.bat
)

echo.
echo You can now use 'run_backend.bat' to start the server.
pause
