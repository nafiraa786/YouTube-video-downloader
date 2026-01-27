#!/bin/bash
# YouTube Video Downloader - Production Deployment Script

echo "🚀 Starting YouTube Video Downloader Production Server..."

# Change to backend directory
cd "$(dirname "$0")"

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run with Gunicorn (production-ready WSGI server)
echo "✓ Starting Gunicorn server on 0.0.0.0:5000..."
gunicorn \
    --workers 4 \
    --worker-class sync \
    --bind 0.0.0.0:5000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    app:app

echo "Server stopped."
