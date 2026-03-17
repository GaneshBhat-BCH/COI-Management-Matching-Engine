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

## Persistence (Stay alive after logout / boot)
The `setup_pm2.ps1` script automatically configures persistence using `pm2-windows-startup`. This ensures:
1. The application stays alive even after you close the VM user session/logout.
2. The application automatically starts when the VM reboots.

**Note**: You must run the setup script as **Administrator** for persistence configuration to succeed.

To manually save the current process list at any time, run:
```powershell
pm2 save
```
