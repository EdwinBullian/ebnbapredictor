@echo off
title EB NBA Predictor
cd /d "%~dp0"

echo Starting Flask backend...
start "EB Predictor — Backend" cmd /k "venv\Scripts\python server.py"

echo Waiting for backend to load models...
timeout /t 5 /nobreak >nul

echo Starting Next.js frontend...
start "EB Predictor — Frontend" cmd /k "npm run dev"

echo.
echo ============================================
echo   EB NBA Predictor is starting up!
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo ============================================
echo.

timeout /t 8 /nobreak >nul
start http://localhost:3000
