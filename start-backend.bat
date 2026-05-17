@echo off
title QuantBot Backend
cd /d "%~dp0backend"
echo Starting QuantBot Backend on http://localhost:8002 ...
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
pause
