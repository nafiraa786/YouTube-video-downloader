@echo off
REM YouTube Video Downloader - Start Script for Windows
REM This script starts both the backend and frontend servers

echo Starting YouTube Video Downloader...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Start backend in a new window on PORT 8001 (serves frontend files)
echo Starting backend server on http://127.0.0.1:8001...
start "YT Downloader - Backend" cmd /k "cd backend && set PORT=8001 && set DEBUG=1 && python app.py"

REM Wait a few seconds for backend to start
timeout /t 3 /nobreak

REM Open the application in the default browser (served by backend)
echo Opening application in browser...
start http://127.0.0.1:8001

REM Frontend served statically from backend; React/Vite dev server not started.
echo Frontend served from backend at http://127.0.0.1:8001

echo.
echo YouTube Video Downloader is now running!
echo Frontend + Backend: http://127.0.0.1:8001
echo Backend API: http://127.0.0.1:8001/api
echo.
echo Press CTRL+C in each window to stop the servers.
pause
