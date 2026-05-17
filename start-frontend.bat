@echo off
title QuantBot Frontend
cd /d "%~dp0frontend"
echo Starting QuantBot Frontend on http://localhost:3000 ...
echo.
npm run dev
pause
