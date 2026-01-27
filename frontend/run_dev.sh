#!/bin/bash
# YouTube Video Downloader - Frontend Development Server

echo "🚀 Starting YouTube Video Downloader Frontend (Development Mode)..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python is not installed"
    exit 1
fi

echo "✓ Starting frontend server on http://127.0.0.1:8000"
echo "  Press Ctrl+C to stop"
echo ""
echo "📖 Open your browser and go to: http://127.0.0.1:8000"
echo ""

# Start Python HTTP server
python3 -m http.server 8000
