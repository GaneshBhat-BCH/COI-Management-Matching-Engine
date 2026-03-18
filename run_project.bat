@echo off
cd /d "%~dp0"
echo Starting COI Management Matching Engine...
pm2 start ecosystem.config.js
pm2 save
echo.
echo Server is starting via PM2.
echo Check status with: pm2 status
pause
