@echo off
REM YouTube Video Downloader - Windows Development Server
REM Start this to run the backend in development mode

echo 🚀 Starting YouTube Video Downloader Backend (Development Mode)...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

REM Install requirements
echo 📦 Installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

REM Start Flask development server (default PORT=8001)
echo.
set PORT=8001
set DEBUG=1
echo ✓ Starting Flask server on http://127.0.0.1:8001
echo   Press Ctrl+C to stop the server
echo.

python app.py

pause
