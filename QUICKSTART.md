# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Windows Users

**Step 1: Install Prerequisites**
- Download Python: https://www.python.org/downloads/
- During installation, CHECK "Add Python to PATH"
- Download FFmpeg: https://ffmpeg.org/download.html

**Step 2: Start Backend**
```cmd
cd backend
run_dev.bat
```
Wait for: `Running on http://127.0.0.1:5000`

**Step 3: Start Frontend** (New Command Prompt)
```cmd
cd frontend
run_dev.bat
```
Wait for: `Serving HTTP on 127.0.0.1 port 8000`

**Step 4: Open in Browser**
```
http://localhost:8000
```

---

### Mac Users

**Step 1: Install Prerequisites**
```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 ffmpeg
```

**Step 2: Start Backend**
```bash
cd backend
chmod +x run_dev.sh
./run_dev.sh
```

**Step 3: Start Frontend** (New Terminal)
```bash
cd frontend
chmod +x run_dev.sh
./run_dev.sh
```

**Step 4: Open Browser**
```
http://localhost:8000
```

---

### Linux Users

**Step 1: Install Prerequisites**
```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3-pip ffmpeg
```

**Step 2: Start Backend**
```bash
cd backend
chmod +x run_dev.sh
./run_dev.sh
```

**Step 3: Start Frontend** (New Terminal)
```bash
cd frontend
chmod +x run_dev.sh
./run_dev.sh
```

**Step 4: Open Browser**
```
http://localhost:8000
```

---

## 🧪 Test the Application

### Test 1: Video Information (Browser)
1. Go to http://localhost:8000
2. Paste: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
3. Click "Get Video Info"
4. Should see video preview

### Test 2: API Health Check
```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{
  "success": true,
  "status": "ok"
}
```

### Test 3: Download Video
```bash
curl -X POST http://localhost:5000/api/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "mp3",
    "quality": "best"
  }'
```

---

## 🐛 Troubleshooting Quick Fixes

### "Python not found"
- **Windows**: Reinstall Python, check "Add to PATH"
- **Mac/Linux**: Try `python3` instead of `python`

### "FFmpeg not found"
- **Windows**: Download from ffmpeg.org, add to PATH
- **Mac**: `brew install ffmpeg`
- **Linux**: `sudo apt-get install ffmpeg`

### "Port 5000 in use"
```bash
# Kill process using port 5000
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Mac/Linux
lsof -i :5000
kill -9 <PID>
```

### CORS Error
- Ensure backend is running on port 5000
- Ensure frontend is running on port 8000
- Check browser console for actual error

---

## 📁 Project Structure Explained

```
yt-downloader/
├── frontend/              # Frontend UI
│   ├── index.html        # Main page
│   ├── app.js            # JavaScript logic
│   ├── styles.css        # Styling
│   └── run_dev.bat       # Start frontend
│
├── backend/              # Flask API
│   ├── app.py            # Main Flask app
│   ├── requirements.txt   # Python packages
│   ├── downloads/        # Downloaded videos
│   └── run_dev.bat       # Start backend
│
└── README.md             # Full documentation
```

---

## 🎯 Next Steps

1. **Customize UI**: Edit `frontend/styles.css` and `frontend/index.html`
2. **Change API URL**: Edit `frontend/app.js` - `CONFIG.API_BASE_URL`
3. **Deploy**: See DEPLOYMENT.md for production setup
4. **Extend**: Add database, analytics, user accounts, etc.

---

## 📚 Learn More

- Frontend code: `frontend/app.js` (200 lines, well-commented)
- Backend code: `backend/app.py` (400 lines, well-commented)
- Full docs: `README.md`
- Deployment: `DEPLOYMENT.md`

---

**Need help?** Check README.md Troubleshooting section.

Happy downloading! 🎉
