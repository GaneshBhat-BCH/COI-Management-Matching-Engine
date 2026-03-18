@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
TITLE COI Management Matching Engine - Quick Launcher

echo ====================================================
echo      COI MANAGEMENT MATCHING ENGINE
echo ====================================================
echo.
echo Cleaning up port 8001...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

echo Launching server via PM2...
pm2 start ecosystem.config.js
pm2 save

echo.
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
powershell -Command "& {Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Server failed to start after 60 seconds! Please check PM2 logs for errors.', 'Critical', 'ERROR')}"
goto :end_script

:server_running
echo.
echo ====================================================
echo      SERVER IS RUNNING!
echo      http://localhost:8001/
echo ====================================================
echo.
powershell -Command "& {Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::MsgBox('Server is UP and RUNNING!\n\nAPI: http://localhost:8001/\n\nClick OK to continue', 'Information', 'SUCCESS')}"

:end_script
echo.
echo Done.
pause
