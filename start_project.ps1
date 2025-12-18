# PowerShell script to handle AI Backend Startup
# This replaces run_hidden.vbs for systems where WSH is disabled

function Check-ApiHealthy {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/" -UseBasicParsing -ErrorAction SilentlyContinue
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "      AI Backend Startup Controller" -ForegroundColor Cyan
Write-Host "      COI Management Matching Engine" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 1. Initial Health Check
if (-not (Check-ApiHealthy)) {
    Write-Host "[INFO] Backend not responding. Starting cold launch..." -ForegroundColor Yellow
    
    # Run setup
    Write-Host "[INFO] Running environment setup..." -ForegroundColor Gray
    Start-Process cmd -ArgumentList "/c setup_env.bat --auto" -Wait -NoNewWindow
    
    # Run DB init
    Write-Host "[INFO] Initializing database..." -ForegroundColor Gray
    Start-Process cmd -ArgumentList "/c init_db.bat --auto" -Wait -NoNewWindow
    
    # Run Backend
    Write-Host "[INFO] Launching backend server..." -ForegroundColor Green
    Start-Process cmd -ArgumentList "/c run_backend.bat --background" -NoNewWindow
}

# 2. Wait and verify
Write-Host "[INFO] Waiting for service to become healthy..." -ForegroundColor Gray
$maxRetries = 30
$retryCount = 0
$success = $false

while ($retryCount -lt $maxRetries) {
    Start-Sleep -Seconds 2
    if (Check-ApiHealthy) {
        $success = $true
        break
    }
    $retryCount++
}

if ($success) {
    Write-Host "`n[SUCCESS] Project is now UP and Ready!" -ForegroundColor Green
    Write-Host "[INFO] API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
    Add-Type -AssemblyName Microsoft.VisualBasic
    [Microsoft.VisualBasic.Interaction]::MsgBox("Project is now UP and Ready!`nAPI Documentation: http://localhost:8000/docs", "Information,OkOnly", "Startup Success")
} else {
    Write-Host "`n[ERROR] Project failed to start automatically." -ForegroundColor Red
    Write-Host "[INFO] Please run 'run_backend.bat' manually to see logs." -ForegroundColor Gray
    Add-Type -AssemblyName Microsoft.VisualBasic
    [Microsoft.VisualBasic.Interaction]::MsgBox("Project failed to start automatically.`nPlease run 'run_backend.bat' manually to see what's wrong.", "Critical,OkOnly", "Startup Error")
}
