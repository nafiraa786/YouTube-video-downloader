# 🎬 YouTube Video Downloader

> A production-ready, modern web application for downloading YouTube videos with a professional UI, security features, and performance optimization.

## 📋 Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Development](#development)
- [Production Deployment](#production-deployment)
- [API Documentation](#api-documentation)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Technical Stack](#technical-stack)

## ✨ Features

### User Experience
- 🌓 **Dark/Light Mode**: Beautiful theme toggle with system preference detection
- 📱 **Fully Responsive**: Optimized for mobile, tablet, and desktop
- ⚡ **Lightning Fast**: Optimized frontend with minimal bundle size
- 🎨 **Modern UI**: Clean, minimal design inspired by ChatGPT and Google
- 🔍 **Auto-Paste Detection**: Automatically detects YouTube URLs in clipboard
- 🎯 **Video Preview**: Thumbnail, title, duration, channel info before download

### Download Options
- 📹 **Multiple Formats**: MP4 video and MP3 audio
- 🎬 **Quality Selection**: Choose from available resolutions (1080p, 720p, 360p)
- 📊 **Progress Indicator**: Real-time download progress tracking
- 💾 **Smart Download**: Efficient streaming and conversion

### Backend Security
- 🔐 **Input Validation**: URL and format validation
- 🚫 **Rate Limiting**: Protection against abuse (20-50 requests/hour)
- 📦 **File Size Limits**: Maximum 5GB per file
- ⏱️ **Duration Limits**: Maximum 1 hour videos
- 🧹 **Auto Cleanup**: Automatic removal of old files
- 🛡️ **CORS Protection**: Restricted to configured origins
- 🔍 **Path Traversal Protection**: Safe filename handling

### Performance
- ⚡ **Async Processing**: Non-blocking downloads
- 🚀 **Optimized API**: Fast metadata extraction
- 🔄 **Efficient Streaming**: Minimal memory footprint
- 📉 **CDN Ready**: Static assets optimized for CDN delivery

## 📁 Project Structure

```
yt-downloader/
├── frontend/                    # Frontend application
│   ├── index.html              # Main HTML template
│   ├── app.js                  # Frontend JavaScript logic
│   ├── styles.css              # Custom CSS styles
│   ├── run_dev.bat             # Windows dev server
│   └── run_dev.sh              # Linux/Mac dev server
│
├── backend/                     # Flask backend API
│   ├── app.py                  # Main Flask application
│   ├── requirements.txt         # Python dependencies
│   ├── .env.example            # Example environment variables
│   ├── run_dev.bat             # Windows development server
│   ├── run_dev.sh              # Linux/Mac development server
│   ├── run_production.sh        # Production deployment script
│   ├── downloads/              # Downloaded files directory
│   ├── temp/                   # Temporary processing files
│   └── yt_downloader.log       # Application logs
│
├── README.md                    # This file
└── DEPLOYMENT.md               # Production deployment guide
```

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** - Download from [python.org](https://www.python.org/downloads/)
- **FFmpeg** - Required for video conversion
  - **Windows**: `choco install ffmpeg` (with Chocolatey) or download from [ffmpeg.org](https://ffmpeg.org/download.html)
  - **macOS**: `brew install ffmpeg`
  - **Linux**: `sudo apt-get install ffmpeg`

### Windows Quick Start

1. **Clone/Download the project**
```bash
# Navigate to the project directory
cd yt-downloader
```

2. **Start Backend** (Terminal 1)
```bash
cd backend
run_dev.bat
```
Expected output: `Running on http://127.0.0.1:5000`

3. **Start Frontend** (Terminal 2)
```bash
cd frontend
run_dev.bat
```
Expected output: `Serving HTTP on 127.0.0.1 port 8000`

4. **Open in Browser**
```
http://localhost:8000
```

### Linux/Mac Quick Start

```bash
# Terminal 1 - Backend
cd backend
chmod +x run_dev.sh
./run_dev.sh

# Terminal 2 - Frontend
cd frontend
chmod +x run_dev.sh
./run_dev.sh

# Then open http://localhost:8000 in your browser
```

## 📦 Installation

### Complete Installation Guide

#### Step 1: Install Python & FFmpeg

**Windows:**
```powershell
# Using Chocolatey (recommended)
choco install python ffmpeg

# Or download manually from https://www.python.org/ and https://ffmpeg.org/download.html
```

**macOS:**
```bash
# Using Homebrew
brew install python@3.11 ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install python3.11 python3-pip ffmpeg
```

#### Step 2: Clone or Download Project

```bash
# If using git
git clone <repository-url>
cd yt-downloader

# Or download ZIP and extract
```

#### Step 3: Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

If you encounter issues, try:
```bash
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt
```

#### Step 4: Verify Installation

```bash
# Check Python version
python --version
# Expected: Python 3.8+

# Check FFmpeg
ffmpeg -version
# Expected: ffmpeg version X.X

# Test yt-dlp
python -c "import yt_dlp; print(yt_dlp.__version__)"
# Expected: yt-dlp version
```

## 💻 Development

### Running Development Servers

#### Windows

```batch
@echo off
REM Terminal 1
cd backend
run_dev.bat

REM Terminal 2
cd frontend
run_dev.bat
```

#### Linux/Mac

```bash
# Terminal 1
cd backend
chmod +x run_dev.sh
./run_dev.sh

# Terminal 2
cd frontend
chmod +x run_dev.sh
./run_dev.sh
```

### Development Ports

- **Frontend**: http://127.0.0.1:8000
- **Backend API**: http://127.0.0.1:5000
- **API Health**: http://127.0.0.1:5000/api/health

### Frontend Configuration

Edit `frontend/app.js` to change the API endpoint:

```javascript
const CONFIG = {
    API_BASE_URL: 'http://localhost:5000/api',  // Change this
    // ... other config
};
```

### Backend Configuration

1. Copy `.env.example` to `.env`:
```bash
cp backend/.env.example backend/.env
```

2. Edit `backend/.env` with your settings:
```env
FLASK_ENV=development
MAX_DURATION_SECONDS=3600
MAX_FILE_SIZE_MB=5120
```

### Testing Endpoints

Use curl or Postman to test the API:

```bash
# Test health
curl http://localhost:5000/api/health

# Test video info
curl -X POST http://localhost:5000/api/video-info \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  }'

# Test download
curl -X POST http://localhost:5000/api/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "mp4",
    "quality": "720"
  }'
```

## 🌐 Production Deployment

### Prerequisites for Production

- Linux server (Ubuntu 20.04+ recommended)
- Domain name (optional, for SSL)
- SSL certificate (from Let's Encrypt, etc.)
- Nginx or Apache reverse proxy
- Systemd or supervisor for process management

### Deployment Steps

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete production deployment guide.

### Quick Production Setup (Linux)

```bash
# 1. Clone project
git clone <repository-url> /opt/yt-downloader
cd /opt/yt-downloader

# 2. Install dependencies
pip install -r backend/requirements.txt
pip install gunicorn

# 3. Start backend with Gunicorn
cd backend
gunicorn \
  --workers 4 \
  --bind 0.0.0.0:5000 \
  --timeout 120 \
  app:app &

# 4. Serve frontend with Nginx (configure separately)
# See DEPLOYMENT.md for Nginx config
```

### Production Considerations

- ✅ Use HTTPS/SSL
- ✅ Set up Nginx reverse proxy
- ✅ Use Gunicorn + Systemd
- ✅ Enable CORS for your domain
- ✅ Set rate limits appropriately
- ✅ Monitor logs and performance
- ✅ Regular backups of download logs
- ✅ Implement file cleanup
- ✅ Use environment variables for secrets

## 📚 API Documentation

### Base URL
- Development: `http://127.0.0.1:5000/api`
- Production: `https://yourdomain.com/api`

### Endpoints

#### 1. Health Check
```
GET /api/health
```

**Response (200):**
```json
{
  "success": true,
  "status": "ok",
  "timestamp": "2024-01-27T12:00:00"
}
```

#### 2. Get Video Information
```
POST /api/video-info
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "title": "Video Title",
    "url": "https://youtube.com/watch?v=...",
    "duration": 3600,
    "thumbnail_url": "https://...",
    "channel_name": "Channel Name",
    "view_count": 1000000,
    "upload_date": "20240101",
    "formats": [
      {
        "format_id": "22",
        "height": 720,
        "ext": "mp4",
        "filesize": null
      }
    ]
  }
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "Invalid YouTube URL"
}
```

#### 3. Download Video
```
POST /api/download
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "format": "mp4",
  "quality": "720"
}
```

**Parameters:**
- `url` (string, required): YouTube video URL
- `format` (string, required): "mp4" or "mp3"
- `quality` (string, optional): "1080", "720", "360", or "best" (default: "best")

**Response (200):**
```json
{
  "success": true,
  "download_url": "/api/file/video_title.mp4",
  "filename": "video_title.mp4",
  "file_size": 123456789,
  "formatted_size": "117.74 MB"
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": "Failed to download video"
}
```

#### 4. Serve Downloaded File
```
GET /api/file/{filename}
```

**Response:** Binary file download

### Rate Limiting

- **Default**: 200 requests/day, 50/hour per IP
- **Video Info**: 30 requests/hour
- **Download**: 20 requests/hour
- **File Serve**: 100 requests/hour

**Rate Limit Exceeded Response (429):**
```json
{
  "success": false,
  "error": "Rate limit exceeded. Please try again later."
}
```

### Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid URL, format, etc.) |
| 404 | Not Found (file doesn't exist) |
| 429 | Too Many Requests (rate limited) |
| 500 | Internal Server Error |

## 🔐 Security

### Features Implemented

1. **Input Validation**
   - YouTube URL validation
   - Format and quality verification
   - File size and duration limits

2. **Rate Limiting**
   - Per-IP request limits
   - Endpoint-specific rate limits
   - Prevents abuse and DoS attacks

3. **File Security**
   - Path traversal protection
   - Safe filename handling
   - Automatic file cleanup after 24 hours

4. **CORS Protection**
   - Restricted to configured origins only
   - Prevents unauthorized cross-origin requests

5. **Process Isolation**
   - Downloads run in isolated subprocess
   - Memory limits enforced
   - Timeout protection

### Best Practices

**For Users:**
- Only download videos you have permission to download
- Respect copyright laws
- Use responsibly

**For Administrators:**
- Keep software updated (`pip install --upgrade yt-dlp`)
- Monitor logs for suspicious activity
- Implement additional firewalls/WAF
- Use HTTPS in production
- Regular security audits
- Keep Python packages updated

## 🐛 Troubleshooting

### Issue: "Python is not installed"

**Solution:**
1. Download Python from [python.org](https://www.python.org/downloads/)
2. During installation, check "Add Python to PATH"
3. Restart terminal/command prompt
4. Verify: `python --version`

### Issue: "FFmpeg is not installed"

**Solution:**
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use Chocolatey: `choco install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt-get install ffmpeg`

### Issue: "yt-dlp version is out of date"

**Solution:**
```bash
pip install --upgrade yt-dlp
```

### Issue: CORS Error ("Access to XMLHttpRequest blocked")

**Solution:**
1. Ensure both servers are running
2. Check `frontend/app.js` - verify correct API_BASE_URL
3. In `backend/app.py`, check CORS configuration
4. Verify ports: Frontend (8000), Backend (5000)

### Issue: Download fails with "Could not fetch video information"

**Solution:**
1. Verify URL is correct (copy directly from YouTube)
2. Check if video is public/not private
3. Update yt-dlp: `pip install --upgrade yt-dlp`
4. Check backend logs for detailed error
5. Some videos may have regional restrictions

### Issue: "File size exceeds maximum limit"

**Solution:**
1. This is a security feature (default 5GB)
2. Edit `backend/app.py` - change `CONFIG['MAX_FILE_SIZE']`
3. Or download lower quality (360p instead of 1080p)

### Issue: Port already in use

**Backend port 5000 in use:**
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :5000
kill -9 <PID>
```

**Frontend port 8000 in use:**
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>
```

### Check Logs

**Backend logs:**
```bash
# Live logs (Linux/Mac)
tail -f backend/yt_downloader.log

# Windows
type backend\yt_downloader.log
```

## 🔧 Technical Stack

### Frontend
- **HTML5**: Semantic markup
- **CSS3**: Modern styling with Tailwind CSS (CDN)
- **Vanilla JavaScript**: No dependencies, ~200 lines
- **Features**: Dark mode, responsive, accessibility

### Backend
- **Python 3.8+**: Core language
- **Flask 2.3**: Web framework
- **yt-dlp**: YouTube video downloader
- **Flask-CORS**: Cross-Origin Resource Sharing
- **Flask-Limiter**: Rate limiting
- **Gunicorn**: Production WSGI server

### Deployment
- **Nginx**: Reverse proxy
- **Systemd**: Process management (Linux)
- **SSL/TLS**: HTTPS encryption
- **Docker**: Optional containerization

### Performance
- **Response Time**: <500ms for metadata
- **Concurrent Downloads**: Multiple simultaneous
- **Memory Usage**: <100MB baseline
- **Storage**: Configurable cleanup

## 📄 License

This project is provided as-is for personal and educational use. Respect copyright laws and YouTube's terms of service.

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit improvements

## 📞 Support

For issues and questions:
1. Check this README and Troubleshooting section
2. Review backend logs: `yt_downloader.log`
3. Test API endpoints with curl/Postman
4. Check browser console for frontend errors

---

**Built with ❤️ for efficient video downloading**

Last Updated: January 2024
