# PM2 Setup and Deployment Script for Windows VM

$PORT = 8001
$APP_NAME = "coi-backend"

Write-Host "--- Starting PM2 Deployment Strategy ---" -ForegroundColor Cyan

# 1. Port Cleanup: Kill any process running on port 8000
Write-Host "1. Checking for existing processes on port $PORT..." -ForegroundColor Yellow
$processId = Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess

if ($processId) {
    Write-Host "Found process $processId using port $PORT. Attempting to terminate..." -ForegroundColor Magenta
    try {
        Stop-Process -Id $processId -Force
        Write-Host "Process $processId terminated successfully." -ForegroundColor Green
    } catch {
        Write-Host "Failed to terminate process $processId. You might need to run this script as Administrator." -ForegroundColor Red
    }
} else {
    Write-Host "No process found running on port $PORT." -ForegroundColor Green
}

# 2. Check for Node.js and PM2
Write-Host "2. Verifying Node.js and PM2 existence..." -ForegroundColor Yellow
if (!(Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Node.js is not installed. Please install Node.js before running this script." -ForegroundColor Red
    exit 1
}

if (!(Get-Command pm2 -ErrorAction SilentlyContinue)) {
    Write-Host "PM2 not found. Installing PM2 globally via npm..." -ForegroundColor Magenta
    npm install pm2 -g
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install PM2. Please check your internet connection and npm configuration." -ForegroundColor Red
        exit 1
    }
}

# 3. Start/Restart Application via PM2
Write-Host "3. Launching application via PM2..." -ForegroundColor Yellow
pm2 delete $APP_NAME 2>$null
pm2 start ecosystem.config.js

if ($LASTEXITCODE -eq 0) {
    Write-Host "Application '$APP_NAME' started successfully via PM2." -ForegroundColor Green
    pm2 status $APP_NAME
} else {
    Write-Host "Failed to start application via PM2." -ForegroundColor Red
}

# 4. Save PM2 list for persistence (if pm2-windows-startup is configured)
pm2 save

Write-Host "--- Setup Complete ---" -ForegroundColor Cyan
Write-Host "To monitor logs, run: pm2 logs $APP_NAME"
