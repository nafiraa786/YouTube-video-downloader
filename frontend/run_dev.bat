@echo off
REM YouTube Video Downloader - Frontend Development Server
REM This serves the frontend via Python's built-in HTTP server

echo 🚀 Starting YouTube Video Downloader Frontend (Development Mode)...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    pause
    exit /b 1
)

echo ✓ Starting frontend server on http://127.0.0.1:8000
echo   Press Ctrl+C to stop
echo.
echo 📖 Open your browser and go to: http://127.0.0.1:8000
echo.

REM Start Python HTTP server
python -m http.server 8000

pause
