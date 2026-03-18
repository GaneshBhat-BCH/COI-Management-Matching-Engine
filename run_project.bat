@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
TITLE COI Management Matching Engine - Quick Launcher

echo ====================================================
echo      COI MANAGEMENT MATCHING ENGINE
echo ====================================================
echo.

REM Start server
echo [5/5] Starting Server...
pushd backend

echo Cleaning up port 8001...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

echo Launching server...
start /B venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

echo Waiting for server to start...
set "max_retries=30"
set "retry_count=0"

:wait_loop
timeout /t 2 /nobreak >nul
curl -s http://localhost:8001/ >nul 2>&1
if !errorlevel! equ 0 (
    goto :server_running
)

set /a "retry_count+=1"
if !retry_count! lss !max_retries! (
    goto :wait_loop
)

echo ERROR: Server failed to start after 60 seconds.
powershell -Command "& {Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Server failed to start after 60 seconds! Please check the terminal for errors.', 'Critical', 'ERROR')}"
goto :end_script

:server_running
echo.
echo ====================================================
echo      SERVER IS RUNNING!
echo      http://localhost:8001/
echo ====================================================
echo.
powershell -Command "& {Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Server is UP and RUNNING!\n\nAPI: http://localhost:8001/\n\nClick OK to keep running', 'Information', 'SUCCESS')}"
echo.
echo Press any key to STOP the server...
pause >nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
echo Server stopped.

:end_script
popd
echo.
echo Setup finished.
pause
