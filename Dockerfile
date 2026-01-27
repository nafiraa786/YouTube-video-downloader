# Multi-stage build for YouTube Video Downloader

# Stage 1: Backend
FROM python:3.11-slim as backend-builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy backend code
COPY backend/ .

# Stage 2: Frontend
FROM node:18-alpine as frontend-builder

WORKDIR /app

# Frontend doesn't need building for vanilla JS
COPY frontend/ .

# Stage 3: Production
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create application user
RUN useradd -m -s /bin/bash appuser

# Copy Python dependencies from backend-builder
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy application files
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# Create necessary directories
RUN mkdir -p /app/backend/downloads /app/backend/temp /app/backend/logs && \
    chown -R appuser:appuser /app

# Switch to app user
USER appuser

WORKDIR /app/backend

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Expose ports
EXPOSE 5000 8000

# Run gunicorn
CMD ["gunicorn", \
     "--workers", "4", \
     "--worker-class", "sync", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "app:app"]
