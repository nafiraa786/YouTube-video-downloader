"""
YouTube Video Downloader Backend API
Production-ready Flask application with yt-dlp integration
Handles video metadata fetching and secure file downloads
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional
from pathlib import Path

# Fix Unicode encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import yt_dlp
from urllib.parse import urlparse

try:
    from waitress import serve
    HAS_WAITRESS = True
except ImportError:
    HAS_WAITRESS = False

# ============================================================================
# Configuration & Setup
# ============================================================================

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for frontend communication
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000", "http://localhost:5000", "http://localhost:8000", "http://127.0.0.1:3000", "http://127.0.0.1:5000", "http://127.0.0.1:8000"]}})

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('yt_downloader.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# Constants & Configuration
# ============================================================================

# Directories
BASE_DIR = Path(__file__).parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
TEMP_DIR = BASE_DIR / "temp"

# Ensure directories exist
DOWNLOADS_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Configuration
CONFIG = {
    'MAX_DURATION': 3600,  # 1 hour max
    'MAX_FILE_SIZE': 5 * 1024 * 1024 * 1024,  # 5GB
    'SUPPORTED_FORMATS': ['mp4', 'mp3', 'webm', 'mkv'],
    'CLEANUP_INTERVAL': 3600,  # Clean up old files every hour
    'FILE_RETENTION_HOURS': 24,  # Delete files after 24 hours
}

# ============================================================================
# Utility Functions
# ============================================================================

def validate_youtube_url(url: str) -> bool:
    """
    Validate if URL is a valid YouTube URL
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        hostname_lower = hostname.lower()
        
        youtube_domains = ['youtube.com', 'youtu.be', 'youtube.co', 'ytimg.com']
        return any(domain in hostname_lower for domain in youtube_domains)
    except Exception as e:
        logger.warning(f"URL validation error: {e}")
        return False

def is_safe_filename(filename: str) -> bool:
    """
    Check if filename is safe (no path traversal attempts)
    """
    dangerous_chars = ['..', '/', '\\', '\0', '\n', '\r']
    return not any(char in filename for char in dangerous_chars)

def format_size(bytes_size: int) -> str:
    """
    Format bytes to human readable size
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def format_duration(seconds: int) -> str:
    """
    Format seconds to HH:MM:SS
    """
    if not seconds:
        return "Unknown"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

def get_video_info_from_yt_dlp(url: str) -> Optional[Dict]:
    """
    Extract video information using yt-dlp
    """
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            'no_check_certificates': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return None
            
            # Validate duration
            duration = info.get('duration', 0)
            if duration and duration > CONFIG['MAX_DURATION']:
                logger.warning(f"Video duration exceeds limit: {duration}s")
                return None
            
            # Extract formats
            formats = []
            if 'formats' in info:
                for fmt in info['formats']:
                    if fmt.get('vcodec') != 'none' and fmt.get('height'):
                        formats.append({
                            'format_id': fmt.get('format_id'),
                            'height': fmt.get('height'),
                            'ext': fmt.get('ext'),
                            'filesize': fmt.get('filesize'),
                        })
            
            # Sort by height descending
            formats.sort(key=lambda x: x.get('height', 0), reverse=True)
            
            # Remove duplicates
            seen = set()
            unique_formats = []
            for fmt in formats:
                key = (fmt['height'], fmt['ext'])
                if key not in seen:
                    seen.add(key)
                    unique_formats.append(fmt)
            
            return {
                'title': info.get('title', 'Unknown'),
                'url': url,
                'duration': duration,
                'thumbnail_url': info.get('thumbnail'),
                'channel_name': info.get('channel', 'Unknown Channel'),
                'view_count': info.get('view_count', 0),
                'upload_date': info.get('upload_date', 'Unknown'),
                'formats': unique_formats[:5],  # Limit to top 5 quality options
            }
            
    except Exception as e:
        logger.error(f"Error extracting video info: {e}")
        return None

def cleanup_old_files():
    """
    Clean up files older than FILE_RETENTION_HOURS
    """
    try:
        now = datetime.now().timestamp()
        retention_seconds = CONFIG['FILE_RETENTION_HOURS'] * 3600
        
        for file_path in DOWNLOADS_DIR.glob('*'):
            if file_path.is_file():
                file_age = now - file_path.stat().st_mtime
                if file_age > retention_seconds:
                    file_path.unlink()
                    logger.info(f"Deleted old file: {file_path.name}")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

def download_video_with_yt_dlp(url: str, format_type: str, quality: str = 'best') -> Optional[Tuple[str, str]]:
    """
    Download video using yt-dlp
    Returns tuple of (file_path, filename) or None on error
    """
    try:
        # Prepare ydl options based on format
        if format_type == 'mp3':
            # For MP3, just get best audio format available
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(DOWNLOADS_DIR / '%(title)s.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
                'no_check_certificates': True,
            }
        elif format_type == 'mp4':
            # Map quality to format string
            quality_map = {
                '1080': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                '720': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
                '360': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
                'best': 'bestvideo+bestaudio/best',
            }
            
            format_string = quality_map.get(quality, 'bestvideo+bestaudio/best')
            
            ydl_opts = {
                'format': format_string,
                'outtmpl': str(DOWNLOADS_DIR / '%(title)s.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
                'no_check_certificates': True,
            }
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        # Add common options
        ydl_opts.update({
            'socket_timeout': 30,
            'retries': 3,
            'fragment_retries': 3,
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            file_path = DOWNLOADS_DIR / Path(filename).name
            
            logger.info(f"Downloaded: {filename}")
            return str(file_path), Path(filename).name
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        return None

# ============================================================================
# API Routes
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'success': True,
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
    }), 200

@app.route('/api/video-info', methods=['POST'])
@limiter.limit("30 per hour")
def get_video_info():
    """
    Fetch video information
    POST /api/video-info
    Body: { "url": "https://youtube.com/watch?v=..." }
    """
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing URL in request body'
            }), 400
        
        url = data.get('url', '').strip()
        
        # Validate URL
        if not url:
            return jsonify({
                'success': False,
                'error': 'URL cannot be empty'
            }), 400
        
        if len(url) > 200:
            return jsonify({
                'success': False,
                'error': 'URL is too long'
            }), 400
        
        if not validate_youtube_url(url):
            return jsonify({
                'success': False,
                'error': 'Invalid YouTube URL'
            }), 400
        
        logger.info(f"Fetching info for: {url[:50]}...")
        
        # Get video info
        video_info = get_video_info_from_yt_dlp(url)
        
        if not video_info:
            return jsonify({
                'success': False,
                'error': 'Could not fetch video information. The video may be unavailable or private.'
            }), 400
        
        return jsonify({
            'success': True,
            'data': video_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error in get_video_info: {e}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while fetching video information'
        }), 500

@app.route('/api/download', methods=['POST'])
@limiter.limit("20 per hour")
def download_video():
    """
    Download video
    POST /api/download
    Body: { "url": "...", "format": "mp4|mp3", "quality": "1080|720|360|best" }
    """
    try:
        data = request.get_json()
        
        if not data or 'url' not in data or 'format' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing url or format in request body'
            }), 400
        
        url = data.get('url', '').strip()
        format_type = data.get('format', '').lower()
        quality = data.get('quality', 'best').lower()
        
        # Validation
        if not url or not validate_youtube_url(url):
            return jsonify({
                'success': False,
                'error': 'Invalid YouTube URL'
            }), 400
        
        if format_type not in ['mp4', 'mp3']:
            return jsonify({
                'success': False,
                'error': f'Invalid format. Supported: {", ".join(CONFIG["SUPPORTED_FORMATS"])}'
            }), 400
        
        logger.info(f"Starting download: {url[:50]}... (format: {format_type}, quality: {quality})")
        
        # Download video
        result = download_video_with_yt_dlp(url, format_type, quality)
        
        if not result:
            return jsonify({
                'success': False,
                'error': 'Failed to download video. Please check the URL and try again.'
            }), 400
        
        file_path, filename = result
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'Downloaded file not found'
            }), 500
        
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > CONFIG['MAX_FILE_SIZE']:
            os.remove(file_path)
            return jsonify({
                'success': False,
                'error': f'File size exceeds maximum limit ({format_size(CONFIG["MAX_FILE_SIZE"])})'
            }), 400
        
        logger.info(f"Download complete: {filename} ({format_size(file_size)})")
        
        # Return download URL
        download_url = f"/api/file/{os.path.basename(file_path)}"
        
        return jsonify({
            'success': True,
            'download_url': download_url,
            'filename': filename,
            'file_size': file_size,
            'formatted_size': format_size(file_size),
        }), 200
        
    except Exception as e:
        logger.error(f"Error in download_video: {e}")
        return jsonify({
            'success': False,
            'error': 'An error occurred during download'
        }), 500

@app.route('/api/file/<filename>', methods=['GET'])
@limiter.limit("100 per hour")
def serve_file(filename):
    """
    Serve downloaded file for download
    """
    try:
        # Security: prevent path traversal
        if not is_safe_filename(filename) or '..' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
        
        file_path = DOWNLOADS_DIR / filename
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        if not file_path.is_file():
            return jsonify({'error': 'Invalid file'}), 400
        
        logger.info(f"Serving file: {filename}")
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Error serving file: {e}")
        return jsonify({'error': 'Error serving file'}), 500

# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded"""
    return jsonify({
        'success': False,
        'error': 'Rate limit exceeded. Please try again later.'
    }), 429

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {e}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == '__main__':
    # Cleanup old files on startup
    cleanup_old_files()
    
    # Log startup
    logger.info("=" * 60)
    logger.info("YouTube Video Downloader Backend Started [RUNNING]")
    logger.info(f"Downloads folder: {DOWNLOADS_DIR}")
    logger.info("=" * 60)
    
    # Run Flask app
    try:
        if HAS_WAITRESS:
            logger.info("Starting with Waitress WSGI server on 127.0.0.1:5000...")
            sys.stdout.flush()
            sys.stderr.flush()
            # Waitress serve() is a blocking call, it will run forever
            serve(app, host='127.0.0.1', port=5000, threads=10)
        else:
            logger.info("Starting with Flask development server on 127.0.0.1:5000...")
            sys.stdout.flush()
            sys.stderr.flush()
            app.run(
                host='127.0.0.1',
                port=5000,
                debug=False,
                use_reloader=False,
                threaded=True,
            )
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.stdout.flush()
    except OSError as e:
        logger.error(f"OS Error (port already in use?): {e}")
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
