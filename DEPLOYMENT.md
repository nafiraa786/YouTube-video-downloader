# 🚀 Production Deployment Guide

Complete guide for deploying YouTube Video Downloader to production on Ubuntu/Linux servers.

## 📋 Table of Contents

1. [Server Setup](#server-setup)
2. [Application Installation](#application-installation)
3. [Nginx Configuration](#nginx-configuration)
4. [SSL/HTTPS Setup](#sslhttps-setup)
5. [Systemd Service](#systemd-service)
6. [Performance Optimization](#performance-optimization)
7. [Monitoring & Logging](#monitoring--logging)
8. [Maintenance](#maintenance)

## 🖥️ Server Setup

### Minimum Requirements

- **OS**: Ubuntu 20.04 LTS or newer
- **CPU**: 2 cores
- **RAM**: 2GB
- **Storage**: 20GB (for logs and temporary files)
- **Bandwidth**: 5Mbps+

### System Update

```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y build-essential libssl-dev libffi-dev
```

### Install Python & FFmpeg

```bash
sudo apt-get install -y python3.11 python3.11-dev python3-pip ffmpeg

# Verify installation
python3 --version
ffmpeg -version
```

### Create Application User

```bash
# Create dedicated user
sudo useradd -m -s /bin/bash yt-downloader

# Give permissions to home directory
sudo chmod 755 /home/yt-downloader
```

## 📦 Application Installation

### 1. Download Application

```bash
# Clone or download repository
cd /opt
sudo git clone <repository-url> yt-downloader
# OR
sudo unzip yt-downloader.zip -d yt-downloader

# Set ownership
sudo chown -R yt-downloader:yt-downloader /opt/yt-downloader
```

### 2. Install Python Dependencies

```bash
cd /opt/yt-downloader/backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Create Environment Configuration

```bash
# Copy example config
cp .env.example .env

# Edit configuration
nano .env
```

**Recommended .env for Production:**

```env
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-very-secure-random-key-generate-with-python-secrets
HOST=127.0.0.1
PORT=5000

# CORS - Update to your domain
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Rate limiting
RATE_LIMIT_DEFAULT=200 per day, 50 per hour

# File limits
MAX_DURATION_SECONDS=3600
MAX_FILE_SIZE_MB=5120
FILE_RETENTION_HOURS=24
CLEANUP_INTERVAL_SECONDS=3600

# Logging
LOG_LEVEL=INFO
LOG_FILE=yt_downloader.log
```

### 4. Create Directories with Permissions

```bash
cd /opt/yt-downloader/backend

# Create downloads directory
sudo mkdir -p downloads
sudo chown yt-downloader:yt-downloader downloads
sudo chmod 755 downloads

# Create temp directory
sudo mkdir -p temp
sudo chown yt-downloader:yt-downloader temp
sudo chmod 755 temp

# Create logs directory
sudo mkdir -p logs
sudo chown yt-downloader:yt-downloader logs
sudo chmod 755 logs
```

## 🌐 Nginx Configuration

### Install Nginx

```bash
sudo apt-get install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Configure Nginx Reverse Proxy

Create `/etc/nginx/sites-available/yt-downloader`:

```nginx
# Upstream Flask backend
upstream flask_backend {
    server 127.0.0.1:5000;
    keepalive 32;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=general:10m rate=50r/m;
limit_req_zone $binary_remote_addr zone=download:10m rate=10r/m;

# HTTP redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates (from Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL security best practices
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;

    # Client limits
    client_max_body_size 10M;
    client_body_timeout 120;

    # Frontend static files
    location / {
        alias /opt/yt-downloader/frontend/;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        expires 1h;
        add_header Cache-Control "public, immutable";
    }

    # API endpoints with rate limiting
    location /api/ {
        limit_req zone=general burst=100 nodelay;

        proxy_pass http://flask_backend;
        proxy_http_version 1.1;
        
        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Download endpoints - higher rate limit
    location /api/download {
        limit_req zone=download burst=20 nodelay;

        proxy_pass http://flask_backend;
        proxy_http_version 1.1;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 120s;
        proxy_send_timeout 180s;
        proxy_read_timeout 180s;
    }

    # File serving
    location /api/file/ {
        limit_req zone=general burst=200 nodelay;

        proxy_pass http://flask_backend;
        proxy_http_version 1.1;
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Optimize for file downloads
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # Deny access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    location ~ ~$ {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Logging
    access_log /var/log/nginx/yt-downloader_access.log;
    error_log /var/log/nginx/yt-downloader_error.log;
}
```

### Enable Nginx Site

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/yt-downloader /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

## 🔒 SSL/HTTPS Setup

### Install Certbot (Let's Encrypt)

```bash
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com

# Verify
sudo certbot certificates
```

### Auto-Renewal

```bash
# Enable auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# Test renewal
sudo certbot renew --dry-run
```

## 🔧 Systemd Service

Create `/etc/systemd/system/yt-downloader.service`:

```ini
[Unit]
Description=YouTube Video Downloader Flask Backend
After=network.target

[Service]
Type=notify
User=yt-downloader
WorkingDirectory=/opt/yt-downloader/backend
Environment="PATH=/opt/yt-downloader/backend/venv/bin"
ExecStart=/opt/yt-downloader/backend/venv/bin/gunicorn \
    --workers 4 \
    --worker-class sync \
    --bind 127.0.0.1:5000 \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info \
    --pid /run/yt-downloader.pid \
    app:app

# Restart policy
Restart=on-failure
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

# Process management
PrivateTmp=yes
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=yes

# Resource limits
MemoryLimit=512M
CPUQuota=75%

[Install]
WantedBy=multi-user.target
```

### Enable Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable on startup
sudo systemctl enable yt-downloader

# Start service
sudo systemctl start yt-downloader

# Check status
sudo systemctl status yt-downloader

# View logs
sudo journalctl -u yt-downloader -f
```

## ⚡ Performance Optimization

### 1. Gunicorn Workers

Edit `yt-downloader.service` - adjust workers based on CPU cores:

```bash
# For 2 cores: 2 workers + 1 = 3
# For 4 cores: 4 workers + 1 = 5
--workers 4
```

### 2. Python Optimization

```bash
# Add to .env
PYTHONOPTIMIZE=2
PYTHONDONTWRITEBYTECODE=1
```

### 3. System Tuning

```bash
# Increase file descriptors
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf

# Increase connection backlog
sudo sysctl -w net.core.somaxconn=4096
sudo sysctl -w net.ipv4.tcp_max_syn_backlog=4096
```

### 4. Enable Swap (if low RAM)

```bash
# Create 2GB swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 📊 Monitoring & Logging

### View Logs

```bash
# Application logs
tail -f /opt/yt-downloader/backend/logs/error.log
tail -f /opt/yt-downloader/backend/logs/access.log

# Systemd logs
sudo journalctl -u yt-downloader -f

# Nginx logs
sudo tail -f /var/log/nginx/yt-downloader_error.log
sudo tail -f /var/log/nginx/yt-downloader_access.log
```

### Monitor Resources

```bash
# Install monitoring tools
sudo apt-get install -y htop nethogs iotop

# Monitor system
htop

# Monitor network
sudo nethogs

# Monitor disk I/O
sudo iotop
```

### Prometheus/Grafana (Optional)

```bash
# Install Prometheus
sudo apt-get install -y prometheus

# Add job to /etc/prometheus/prometheus.yml
- job_name: 'yt-downloader'
  static_configs:
    - targets: ['localhost:5000']
```

## 🧹 Maintenance

### Regular Tasks

#### Daily
```bash
# Check service status
sudo systemctl status yt-downloader

# Monitor logs for errors
grep ERROR /opt/yt-downloader/backend/logs/error.log
```

#### Weekly
```bash
# Clear old downloaded files
find /opt/yt-downloader/backend/downloads -type f -mtime +7 -delete

# Clean temp files
find /opt/yt-downloader/backend/temp -type f -mtime +1 -delete

# Check disk usage
du -sh /opt/yt-downloader/backend/downloads
```

#### Monthly
```bash
# Update packages
sudo apt-get update && sudo apt-get upgrade -y

# Update Python packages
cd /opt/yt-downloader/backend
source venv/bin/activate
pip install --upgrade pip
pip install --upgrade -r requirements.txt

# Update yt-dlp specifically
pip install --upgrade yt-dlp
```

### Backup Strategy

```bash
#!/bin/bash
# Backup script - save to /etc/cron.daily/yt-downloader-backup

BACKUP_DIR="/backups/yt-downloader"
APP_DIR="/opt/yt-downloader"
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR

# Backup logs
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz $APP_DIR/backend/logs/

# Remove old backups (keep 30 days)
find $BACKUP_DIR -name "logs_*.tar.gz" -mtime +30 -delete

echo "Backup completed: logs_$DATE.tar.gz"
```

### Restart Service

```bash
# Graceful restart
sudo systemctl restart yt-downloader

# Check it restarted
sudo systemctl status yt-downloader

# Verify API is responding
curl https://yourdomain.com/api/health
```

### Troubleshooting Production Issues

#### Service Won't Start

```bash
# Check systemd logs
sudo journalctl -u yt-downloader -n 50

# Test Flask app directly
cd /opt/yt-downloader/backend
source venv/bin/activate
python app.py
```

#### High Memory Usage

```bash
# Check memory limits
systemctl cat yt-downloader | grep Memory

# Reduce workers or enable swap
sudo free -h
```

#### Nginx Connection Issues

```bash
# Check upstream
sudo nginx -t

# Monitor connections
sudo netstat -tulpn | grep nginx
```

#### Slow Downloads

```bash
# Check Gunicorn workers
ps aux | grep gunicorn

# Monitor network
sudo iftop

# Check bandwidth limits
```

## 🔐 Security Checklist

- ✅ HTTPS/SSL enabled
- ✅ Firewall configured (UFW)
- ✅ Rate limiting enabled
- ✅ Failed login attempts blocked
- ✅ Regular security updates
- ✅ Log monitoring enabled
- ✅ Backups automated
- ✅ CORS properly configured
- ✅ File permissions restricted
- ✅ Sensitive files protected

### UFW Firewall Setup

```bash
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw status
```

## 📈 Scaling (Advanced)

For high traffic scenarios:

1. **Load Balancing** - Use HAProxy in front of multiple instances
2. **Reverse Proxy Caching** - Cache responses with Varnish
3. **Redis** - For session storage and caching
4. **Database** - For analytics (PostgreSQL)
5. **CDN** - Serve static files from CloudFlare/Akamai
6. **Kubernetes** - Container orchestration for massive scale

---

**Last Updated**: January 2024
**Maintainer**: Your Team
