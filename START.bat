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

REM Start backend in a new window
echo Starting backend server on http://127.0.0.1:5000...
start "YT Downloader - Backend" cmd /k "cd backend && python simple_run.py"

REM Wait a few seconds for backend to start
timeout /t 3 /nobreak

REM Start frontend in a new window
echo Starting frontend server on http://localhost:8000...
start "YT Downloader - Frontend" cmd /k "cd frontend && python -m http.server 8000"

REM Wait a few seconds then open browser
timeout /t 2 /nobreak

REM Try to open the application in default browser
echo Opening application in browser...
start http://localhost:8000

echo.
echo YouTube Video Downloader is now running!
echo Frontend: http://localhost:8000
echo Backend API: http://127.0.0.1:5000/api
echo.
echo Press CTRL+C in each window to stop the servers.
pause
