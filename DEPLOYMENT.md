# COI Management Matching Engine - Deployment Guide (PM2)

This document explains how to deploy and manage the FastAPI backend using PM2 on a Windows VM.

## Prerequisites
- **Node.js**: Required to run PM2.
- **Python 3.10+**: Ensure the virtual environment is created in `backend/venv`.
- **PowerShell**: Used for the setup script.

## Initial Setup
Run the provided setup script from the project root using PowerShell:

```powershell
.\setup_pm2.ps1
```

The script will:
1. Kill any existing process running on port 8001.
2. Check for (and install if missing) PM2.
3. Start the FastAPI application using `ecosystem.config.js`.

## Management Commands

### Essential PM2 Commands

- **Check Status**: `pm2 status COI-Management-Matching-Engine`
- **View Logs**: `pm2 logs COI-Management-Matching-Engine`
- **Restart**: `pm2 restart COI-Management-Matching-Engine`
- **Stop**: `pm2 stop COI-Management-Matching-Engine`
- **Delete**: `pm2 delete COI-Management-Matching-Engine`

## Persistence (Startup on Boot)
To ensure the application starts automatically when the VM reboots:
1. Install `pm2-windows-startup` or `pm2-windows-service`.
2. Run `pm2 save` after starting the application to save the process list.
