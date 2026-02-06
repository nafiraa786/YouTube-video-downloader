"""
YouTube Video Downloader Backend API
Production-ready Flask application with yt-dlp integration
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Tuple, Optional
from pathlib import Path

# Fix Unicode encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import yt_dlp
from urllib.parse import urlparse
from http.client import HTTPException
import time
import threading
import uuid
import queue as _queue
import json

try:
    from waitress import serve
    HAS_WAITRESS = True
except ImportError:
    HAS_WAITRESS = False

# ============================================================================
# Configuration & Setup
# ============================================================================

app = Flask(__name__)

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

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
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Directories
BASE_DIR = Path(__file__).parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Frontend directory (optional serving of static frontend files)
FRONTEND_DIR = BASE_DIR.parent / 'frontend'

# Optional cookies file (Netscape cookie file / cookies.txt)
COOKIES_FILE = BASE_DIR / 'cookies.txt'

# Common user-agents to rotate if a request fails
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
]

# Log yt-dlp version (helpful when debugging player/API failures)
try:
    ytdlp_version = getattr(yt_dlp, '__version__', None) or getattr(yt_dlp, 'version', None)
    logger.info(f"yt-dlp version: {ytdlp_version}")
except Exception:
    logger.debug("Could not determine yt-dlp version")


CONFIG = {
    'MAX_DURATION': 3600,
    'MAX_FILE_SIZE': 5 * 1024 * 1024 * 1024,
    'SUPPORTED_FORMATS': ['mp4', 'mp3'],
    'FILE_RETENTION_HOURS': 24,
}

# ============================================================================
# Utility Functions
# ============================================================================

def validate_youtube_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return any(domain in hostname.lower() for domain in ['youtube.com', 'youtu.be'])
    except:
        return False

def is_safe_filename(filename: str) -> bool:
    dangerous_chars = ['..', '/', '\\', '\0']
    return not any(char in filename for char in dangerous_chars)

def format_size(bytes_size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

# ============================================================================
# Core Logic
# ============================================================================

# Simple in-memory job queue and event system (for demo/dev)
JOBS = {}
JOBS_LOCK = threading.Lock()
EVENT_QUEUE = _queue.Queue()

def push_event(event: dict):
    try:
        EVENT_QUEUE.put_nowait(event)
    except Exception:
        logger.debug('Event queue full or closed')


def get_video_info_from_yt_dlp(url: str) -> Optional[Dict]:
    try:
        # Base options used for metadata fetch
        base_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'socket_timeout': 15,
            'http_headers': {
                'Referer': 'https://www.youtube.com/'
            }
        }

        if COOKIES_FILE.exists():
            base_opts['cookiefile'] = str(COOKIES_FILE)

        info = None
        # Try multiple attempts rotating user-agent to reduce transient API errors
        for attempt in range(3):
            ua = USER_AGENTS[attempt % len(USER_AGENTS)]
            opts = dict(base_opts)
            opts['http_headers'] = dict(base_opts.get('http_headers', {}))
            opts['http_headers']['User-Agent'] = ua

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    break
            except Exception as e:
                logger.warning('Info attempt %d failed: %s', attempt + 1, repr(e))
                time.sleep(1 + attempt)

        if not info:
            logger.error('Failed to fetch video info after multiple attempts')
            return None

        formats = []
        for f in info.get('formats', []):
            if f.get('vcodec') != 'none' and f.get('height'):
                formats.append({
                    'format_id': f.get('format_id'),
                    'height': f.get('height'),
                    'ext': f.get('ext'),
                })

        # Collect available subtitles (both uploaded and automatic)
        subtitles = {}
        for k, v in (info.get('subtitles') or {}).items():
            subtitles.setdefault(k, {})['manual'] = True
        for k, v in (info.get('automatic_captions') or {}).items():
            subtitles.setdefault(k, {})['automatic'] = True

        return {
            'title': info.get('title', 'Unknown'),
            'url': url,
            'duration': info.get('duration'),
            'thumbnail_url': info.get('thumbnail'),
            'channel_name': info.get('channel'),
            'formats': sorted(formats, key=lambda x: x['height'], reverse=True)[:5],
            'subtitles': subtitles,
        }
    except Exception as e:
        logger.error('Info error: %s', repr(e))
        return None

def download_video_with_yt_dlp(url: str, format_type: str, quality: str = 'best', include_subs: bool = False, subs_langs: Optional[list] = None) -> Optional[Tuple[str, str]]:
    try:
        # Define output template
        out_tmpl = str(DOWNLOADS_DIR / '%(title)s.%(ext)s')
        
        # Base options with common headers and timeouts to avoid 403 errors
        base_opts = {
            'outtmpl': out_tmpl,
            'socket_timeout': 30,
            'http_headers': {
                'Referer': 'https://www.youtube.com/'
            }
        }

        if COOKIES_FILE.exists():
            base_opts['cookiefile'] = str(COOKIES_FILE)

        # Add concurrency optimizations for fragment downloads (helps DASH/HLS)
        concurrent_fragments = int(os.environ.get('CONCURRENT_FRAGMENTS', '4'))

        if format_type == 'mp3':
            ydl_opts = {
                **base_opts,
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
        else:
            # For MP4, quality mapping
            quality_map = {
                '1080': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
                '720': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
                '360': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
                'best': 'bestvideo+bestaudio/best',
            }
            ydl_opts = {
                **base_opts,
                'format': quality_map.get(quality, 'bestvideo+bestaudio/best'),
                'merge_output_format': 'mp4',
            }

        # optional subtitles
        if include_subs:
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            if subs_langs:
                # yt-dlp accepts comma-separated languages
                ydl_opts['subtitleslangs'] = ','.join(subs_langs)

        # concurrent fragments for faster downloads of segmented media
        ydl_opts['concurrent_fragment_downloads'] = concurrent_fragments

        # Attempt download with UA rotation and retries to reduce chance of throttling/403
        last_exc = None
        for attempt in range(3):
            ua = USER_AGENTS[attempt % len(USER_AGENTS)]
            opts = dict(ydl_opts)
            opts['http_headers'] = dict(ydl_opts.get('http_headers', {}))
            opts['http_headers']['User-Agent'] = ua

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    file_path = ydl.prepare_filename(info)

                    if format_type == 'mp3':
                        file_path = os.path.splitext(file_path)[0] + '.mp3'
                    elif not file_path.endswith('.mp4') and format_type == 'mp4':
                        file_path = os.path.splitext(file_path)[0] + '.mp4'

                    return file_path, os.path.basename(file_path)
            except Exception as e:
                last_exc = e
                logger.warning('Download attempt %d failed: %s', attempt + 1, repr(e))
                time.sleep(2 + attempt * 2)

        # If we reach here, all attempts failed
        if last_exc:
            logger.error('Download error after retries: %s', repr(last_exc))
            # If this looks like a 403/400, give actionable advice
            err_text = repr(last_exc)
            if 'HTTP Error 403' in err_text or 'HTTP Error 400' in err_text:
                logger.error('HTTP 4xx error detected. Ensure yt-dlp is up-to-date (`pip install -U yt-dlp`) and consider placing a valid cookies.txt at %s for restricted content.', COOKIES_FILE)

        return None
    except Exception as e:
        logger.exception('Unexpected download error: %s', repr(e))
        return None


def _progress_hook(job_id, d):
    # d contains keys like status, downloaded_bytes, total_bytes, speed, eta
    try:
        status = d.get('status')
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if not job:
                return
            if status == 'downloading':
                downloaded = d.get('downloaded_bytes') or d.get('downloaded_bytes_estimate') or 0
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                percent = None
                if total:
                    percent = int(downloaded / total * 100)
                job['progress'] = percent if percent is not None else job.get('progress', 0)
                job['speed'] = d.get('speed')
                job['eta'] = d.get('eta')
                job['status'] = 'running'
            elif status == 'finished':
                job['progress'] = 100
                job['status'] = 'finalizing'
            elif status == 'error':
                job['status'] = 'error'
                job['message'] = d.get('error')

        # push event
        push_event({'type': 'job_progress', 'job_id': job_id, 'data': job})
    except Exception as e:
        logger.debug('Progress hook error: %s', repr(e))


def download_job(job_id: str):
    """Process a single job using yt-dlp with progress hooks."""
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        job['status'] = 'running'

    url = job['url']
    fmt = job.get('format', 'mp4')
    quality = job.get('quality', 'best')

    out_tmpl = str(DOWNLOADS_DIR / '%(title)s.%(ext)s')

    opts = {
        'outtmpl': out_tmpl,
        'socket_timeout': 30,
        'continuedl': True,
        'http_headers': {'Referer': 'https://www.youtube.com/'},
        'progress_hooks': [lambda d: _progress_hook(job_id, d)],
    }

    if COOKIES_FILE.exists():
        opts['cookiefile'] = str(COOKIES_FILE)

    if job.get('format_type') == 'mp3' or fmt == 'mp3':
        opts.update({'format': 'bestaudio/best', 'postprocessors': [{
            'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]})
    else:
        quality_map = {
            '1080': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            '720': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            '360': 'bestvideo[height<=360]+bestaudio/best[height<=360]',
            'best': 'bestvideo+bestaudio/best',
        }
        opts.update({'format': quality_map.get(quality, 'bestvideo+bestaudio/best'), 'merge_output_format': 'mp4'})

    # subtitles
    if job.get('include_subs'):
        opts['writesubtitles'] = True
        opts['writeautomaticsub'] = True
        if job.get('subs_langs'):
            opts['subtitleslangs'] = ','.join(job.get('subs_langs'))

    # concurrent fragments for faster segmented downloads
    opts['concurrent_fragment_downloads'] = int(os.environ.get('CONCURRENT_FRAGMENTS', '4'))

    last_exc = None
    for attempt in range(3):
        ua = USER_AGENTS[attempt % len(USER_AGENTS)]
        opts['http_headers']['User-Agent'] = ua
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                if fmt == 'mp3':
                    file_path = os.path.splitext(file_path)[0] + '.mp3'
                with JOBS_LOCK:
                    JOBS[job_id]['status'] = 'completed'
                    JOBS[job_id]['progress'] = 100
                    JOBS[job_id]['filename'] = os.path.basename(file_path)
                push_event({'type': 'job_done', 'job_id': job_id, 'file': JOBS[job_id]['filename']})
                return
        except Exception as e:
            last_exc = e
            logger.warning('Download attempt %d for job %s failed: %s', attempt + 1, job_id, repr(e))
            with JOBS_LOCK:
                JOBS[job_id]['status'] = 'retrying'
                JOBS[job_id]['message'] = repr(e)
            push_event({'type': 'job_retry', 'job_id': job_id, 'attempt': attempt + 1, 'error': repr(e)})
            time.sleep(2 + attempt * 2)

    # all attempts exhausted
    with JOBS_LOCK:
        JOBS[job_id]['status'] = 'failed'
        JOBS[job_id]['message'] = repr(last_exc)
    push_event({'type': 'job_failed', 'job_id': job_id, 'error': repr(last_exc)})


def worker_loop():
    logger.info('Background worker started')
    while True:
        job_to_process = None
        with JOBS_LOCK:
            for jid, j in JOBS.items():
                if j.get('status') == 'pending':
                    job_to_process = jid
                    j['status'] = 'queued'
                    break

        if job_to_process:
            try:
                download_job(job_to_process)
            except Exception as e:
                logger.error('Worker error processing %s: %s', job_to_process, repr(e))
        else:
            time.sleep(1)


# Start background worker thread
worker_thread = threading.Thread(target=worker_loop, daemon=True)
worker_thread.start()


# ---------- Cookies management API ----------
@app.route('/api/cookies', methods=['GET'])
def cookies_status():
    """Return whether a cookies.txt is present and its size."""
    exists = COOKIES_FILE.exists()
    size = None
    if exists:
        try:
            size = os.path.getsize(COOKIES_FILE)
        except Exception:
            size = None
    return jsonify({'exists': exists, 'size': size})


@app.route('/api/upload-cookies', methods=['POST'])
def upload_cookies():
    """Upload a cookies.txt (Netscape format). Field name: 'cookies' or 'file'."""
    if 'cookies' in request.files:
        f = request.files['cookies']
    elif 'file' in request.files:
        f = request.files['file']
    else:
        return jsonify({'success': False, 'error': 'No file provided; use form field `cookies` or `file`.'}), 400

    filename = secure_filename(f.filename or 'cookies.txt')
    # Ensure it's a text file and plausible
    if not filename.lower().endswith(('.txt', '.cookies')) and filename != 'cookies.txt':
        filename = 'cookies.txt'

    try:
        # Save to the canonical cookies path used by the downloader
        f.save(str(COOKIES_FILE))
        logger.info('Saved cookies to %s', COOKIES_FILE)
        return jsonify({'success': True, 'message': 'Cookies uploaded'}), 201
    except Exception as e:
        logger.error('Failed to save cookies: %s', repr(e))
        return jsonify({'success': False, 'error': 'Failed to save cookies'}), 500


@app.route('/api/cookies', methods=['DELETE'])
def delete_cookies():
    try:
        if COOKIES_FILE.exists():
            COOKIES_FILE.unlink()
            return jsonify({'success': True, 'message': 'Cookies deleted'})
        return jsonify({'success': False, 'error': 'No cookies present'}), 404
    except Exception as e:
        logger.error('Failed to delete cookies: %s', repr(e))
        return jsonify({'success': False, 'error': 'Failed to delete cookies'}), 500


# ---------------- Queue API & Events ----------------
@app.route('/api/queue', methods=['POST'])
def enqueue():
    data = request.get_json() or {}

    # Bulk enqueue: accept 'items' list where each item is {url, format?, quality?}
    items = data.get('items')
    created = []
    if items and isinstance(items, list):
        for it in items:
            url = it.get('url')
            if not url or not validate_youtube_url(url):
                continue
            fmt = it.get('format', data.get('format', 'mp4'))
            quality = it.get('quality', data.get('quality', 'best'))
            meta = get_video_info_from_yt_dlp(url) or {}
            job_id = str(uuid.uuid4())
            with JOBS_LOCK:
                JOBS[job_id] = {
                    'id': job_id,
                    'url': url,
                    'title': meta.get('title'),
                    'thumbnail_url': meta.get('thumbnail_url'),
                    'format': fmt,
                    'quality': quality,
                    'status': 'pending',
                    'progress': 0,
                    'speed': None,
                    'eta': None,
                    'filename': None,
                    'message': None,
                    'created_at': datetime.utcnow().isoformat()
                }
            push_event({'type': 'job_enqueued', 'job_id': job_id, 'url': url})
            created.append(job_id)

        if created:
            return jsonify({'success': True, 'job_ids': created}), 201
        return jsonify({'success': False, 'error': 'No valid items to enqueue'}), 400

    # Single enqueue path
    url = data.get('url')
    if not url or not validate_youtube_url(url):
        return jsonify({'success': False, 'error': 'Invalid URL'}), 400
    # Support optional playlist/channel expansion when 'expand' or options.expand_playlist provided
    expand = False
    if isinstance(data.get('options'), dict) and data['options'].get('expand_playlist'):
        expand = True
    if data.get('expand') or data.get('expand_playlist'):
        expand = True

    fmt = data.get('format', 'mp4')
    quality = data.get('quality', 'best')

    include_subs = bool(data.get('include_subs'))
    subs_langs = data.get('subs_langs') or None

    if expand:
        try:
            logger.info('Expanding playlist/channel for URL: %s', url)
            with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
                info = ydl.extract_info(url, download=False)
            entries = info.get('entries') or []
            created_ids = []
            max_items = int(os.environ.get('MAX_PLAYLIST_ITEMS', '200'))
            count = 0
            for entry in entries:
                if count >= max_items:
                    break
                entry_url = entry.get('webpage_url') or entry.get('url')
                if not entry_url:
                    continue
                meta = {
                    'title': entry.get('title'),
                    'thumbnail_url': entry.get('thumbnail'),
                }
                job_id = str(uuid.uuid4())
                with JOBS_LOCK:
                    JOBS[job_id] = {
                        'id': job_id,
                        'url': entry_url,
                        'title': meta.get('title'),
                        'thumbnail_url': meta.get('thumbnail_url'),
                        'format': fmt,
                        'quality': quality,
                        'status': 'pending',
                        'progress': 0,
                        'speed': None,
                        'eta': None,
                        'filename': None,
                        'message': None,
                        'created_at': datetime.utcnow().isoformat()
                    }
                push_event({'type': 'job_enqueued', 'job_id': job_id, 'url': entry_url})
                created_ids.append(job_id)
                count += 1

            if created_ids:
                return jsonify({'success': True, 'job_ids': created_ids, 'count': len(created_ids)}), 201
            return jsonify({'success': False, 'error': 'No entries found in playlist'}), 400
        except Exception as e:
            logger.exception('Playlist expansion failed for %s', url)
            return jsonify({'success': False, 'error': 'Playlist expansion failed', 'detail': str(e)}), 500

    meta = get_video_info_from_yt_dlp(url) or {}
    job_id = str(uuid.uuid4())
    with JOBS_LOCK:
        JOBS[job_id] = {
            'id': job_id,
            'url': url,
            'title': meta.get('title'),
            'thumbnail_url': meta.get('thumbnail_url'),
            'format': fmt,
            'quality': quality,
            'include_subs': include_subs,
            'subs_langs': subs_langs,
            'status': 'pending',
            'progress': 0,
            'speed': None,
            'eta': None,
            'filename': None,
            'message': None,
            'created_at': datetime.utcnow().isoformat()
        }

    push_event({'type': 'job_enqueued', 'job_id': job_id, 'url': url})
    return jsonify({'success': True, 'job_id': job_id}), 201


@app.route('/api/queue', methods=['GET'])
def list_jobs():
    with JOBS_LOCK:
        return jsonify({'jobs': list(JOBS.values())})


@app.route('/api/queue/<job_id>', methods=['GET'])
def get_job(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        return jsonify({'success': True, 'job': job})


@app.route('/api/stream')
def stream_events():
    def event_stream():
        while True:
            try:
                ev = EVENT_QUEUE.get()
                data = json.dumps(ev)
                yield f"data: {data}\n\n"
            except GeneratorExit:
                break
            except Exception:
                time.sleep(0.5)

    return app.response_class(event_stream(), mimetype='text/event-stream')

# ============================================================================
# API Routes
# ============================================================================

@app.route('/api/video-info', methods=['POST'])
def get_video_info():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url or not validate_youtube_url(url):
        return jsonify({'success': False, 'error': 'Invalid URL'}), 400
    
    info = get_video_info_from_yt_dlp(url)
    if info:
        return jsonify({'success': True, 'data': info})
    return jsonify({'success': False, 'error': 'Video unavailable'}), 404


@app.route('/api/expand', methods=['POST'])
def expand_playlist():
    data = request.get_json() or {}
    url = data.get('url')
    if not url or not validate_youtube_url(url):
        return jsonify({'success': False, 'error': 'Invalid URL'}), 400

    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
            info = ydl.extract_info(url, download=False)
        entries = info.get('entries') or []
        max_items = int(os.environ.get('MAX_PLAYLIST_ITEMS', '200'))
        result = []
        count = 0
        for e in entries:
            if count >= max_items:
                break
            result.append({
                'title': e.get('title'),
                'url': e.get('webpage_url') or e.get('url'),
                'thumbnail': e.get('thumbnail'),
                'duration': e.get('duration')
            })
            count += 1
        return jsonify({'success': True, 'entries': result})
    except Exception as e:
        logger.exception('Expand error')
        return jsonify({'success': False, 'error': 'Failed to expand playlist', 'detail': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    data = request.get_json()
    url = data.get('url')
    fmt = data.get('format', 'mp4')
    quality = data.get('quality', 'best')
    include_subs = bool(data.get('include_subs'))
    subs_langs = data.get('subs_langs') or None

    result = download_video_with_yt_dlp(url, fmt, quality, include_subs=include_subs, subs_langs=subs_langs)
    if result:
        file_path, filename = result
        return jsonify({
            'success': True,
            'download_url': f"/api/file/{filename}",
            'filename': filename
        })
    return jsonify({'success': False, 'error': 'Download failed'}), 500


@app.route('/api/subtitles', methods=['POST'])
def list_subtitles():
    data = request.get_json() or {}
    url = data.get('url')
    if not url or not validate_youtube_url(url):
        return jsonify({'success': False, 'error': 'Invalid URL'}), 400

    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
            info = ydl.extract_info(url, download=False)

        subs = {}
        for k, v in (info.get('subtitles') or {}).items():
            subs[k] = {'manual': True}
        for k, v in (info.get('automatic_captions') or {}).items():
            subs.setdefault(k, {})['automatic'] = True

        return jsonify({'success': True, 'subtitles': subs})
    except Exception as e:
        logger.exception('Subtitles listing failed')
        return jsonify({'success': False, 'error': 'Failed to list subtitles', 'detail': str(e)}), 500


@app.route('/api/download-subtitles', methods=['POST'])
def download_subtitles():
    data = request.get_json() or {}
    url = data.get('url')
    lang = data.get('lang')
    if not url or not validate_youtube_url(url) or not lang:
        return jsonify({'success': False, 'error': 'Missing url or lang'}), 400

    out_tmpl = str(DOWNLOADS_DIR / '%(title)s.%(ext)s')
    opts = {'outtmpl': out_tmpl, 'skip_download': True, 'writesubtitles': True, 'subtitlesformat': 'vtt', 'subtitleslangs': lang}
    if COOKIES_FILE.exists():
        opts['cookiefile'] = str(COOKIES_FILE)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # yt-dlp will write subtitle file next to output; try to locate it
            filename = ydl.prepare_filename(info)
            base = os.path.splitext(filename)[0]
            possible = [base + '.' + ext for ext in ('vtt', 'srt')]
            for p in possible:
                if os.path.exists(p):
                    return jsonify({'success': True, 'file': os.path.basename(p), 'download_url': f"/api/file/{os.path.basename(p)}"})
        return jsonify({'success': False, 'error': 'Subtitle not found after download'}), 404
    except Exception as e:
        logger.exception('Subtitle download failed')
        return jsonify({'success': False, 'error': 'Failed to download subtitles', 'detail': str(e)}), 500


@app.route('/api/queue/<job_id>/cancel', methods=['POST'])
def cancel_job(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        if job.get('status') in ('pending', 'queued'):
            job['status'] = 'cancelled'
            push_event({'type': 'job_cancelled', 'job_id': job_id})
            return jsonify({'success': True, 'job_id': job_id})
        return jsonify({'success': False, 'error': 'Cannot cancel running or completed job'}), 400

@app.route('/api/file/<filename>')
def serve_file(filename):
    if not is_safe_filename(filename):
        return "Invalid filename", 400
    return send_file(DOWNLOADS_DIR / filename, as_attachment=True)


# Serve frontend static files (index, app.js, favicon, etc.) when present
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    # Prioritize API routes (they are defined above). This catch-all serves
    # files from the frontend directory when running the app as a single server.
    if not FRONTEND_DIR.exists():
        return "Frontend not available", 404

    if path == '' or path == 'index.html':
        return send_file(FRONTEND_DIR / 'index.html')

    candidate = FRONTEND_DIR / path
    if candidate.exists() and candidate.is_file():
        return send_file(candidate)

    # If a file isn't found, return 404 so browser can fallback
    return "Not Found", 404

if __name__ == '__main__':
    # Allow overriding host/port via environment for flexibility in development
    host = os.environ.get('HOST', '127.0.0.1')
    try:
        port = int(os.environ.get('PORT', '8001'))
    except ValueError:
        port = 8001

    debug_env = os.environ.get('DEBUG', '').lower()
    debug = True if debug_env in ('1', 'true', 'yes') else False

    bind_info = f"{host}:{port}"
    logger.info(f"Starting server on http://{bind_info} (debug={debug})")

    if HAS_WAITRESS:
        serve(app, host=host, port=port)
    else:
        app.run(host=host, port=port, debug=debug)