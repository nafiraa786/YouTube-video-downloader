#!/bin/bash
# YouTube Video Downloader - Windows Development Server (Bash version)

echo "🚀 Starting YouTube Video Downloader Backend (Development Mode)..."
echo ""

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed or not in PATH"
    echo "Please install Python 3.8+ from https://www.python.org/"
    exit 1
fi

# Install requirements
echo "📦 Installing dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Start Flask development server
echo ""
echo "✓ Starting Flask server on http://127.0.0.1:5000"
echo "  Press Ctrl+C to stop the server"
echo ""

python app.py
