@echo off
title QuantBot - All Services
echo ========================================
echo   QuantBot - Starting All Services
echo ========================================
echo.

echo [1/2] Starting Backend on http://localhost:8002 ...
start "QuantBot Backend" cmd /c "cd /d %~dp0backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload"

timeout /t 3 /nobreak >nul

echo [2/2] Starting Frontend on http://localhost:3000 ...
start "QuantBot Frontend" cmd /c "cd /d %~dp0frontend && npm run dev"

echo.
echo ========================================
echo   All services started!
echo   Backend:  http://localhost:8002
echo   Frontend: http://localhost:3000
echo   API Docs: http://localhost:8002/docs
echo ========================================
echo.
pause
