/**
 * YouTube Video Downloader - Frontend Application
 * Modern, responsive vanilla JavaScript application
 * No external dependencies required (uses Tailwind CSS via CDN)
 */

// ============================================================================
// Configuration & Constants
// ============================================================================


// ---------------- Queue State & SSE ----------------
const queueState = {
    jobs: new Map(),
    es: null,
};

function renderQueue() {
    if (!elements.queueList) return;
    elements.queueList.innerHTML = '';
    const jobs = Array.from(queueState.jobs.values()).sort((a,b)=> new Date(a.created_at || 0) - new Date(b.created_at || 0));
    if (jobs.length === 0) {
        elements.queueList.innerHTML = '<div class="text-sm text-gray-500">Queue is empty</div>';
        return;
    }

    for (const job of jobs) {
        const card = document.createElement('div');
        card.className = 'flex items-center gap-3 p-2 rounded bg-gray-900/40 border border-gray-700';

        const meta = document.createElement('div');
        meta.className = 'flex-1';
        const title = job.title || job.url || 'Untitled';
        const status = job.status || 'queued';
        const percent = job.progress != null ? job.progress : 0;

        meta.innerHTML = `
            <div class="font-medium truncate">${escapeHtml(title)}</div>
            <div class="text-xs text-gray-400">${job.url ? job.url.replace(/^https?:\/\//,'') : ''}</div>
        `;

        const right = document.createElement('div');
        right.className = 'w-36 text-right';
        const badge = document.createElement('div');
        badge.className = 'text-xs mb-2';
        badge.innerHTML = `<span class="px-2 py-1 rounded text-xs ${status === 'completed' ? 'bg-green-600' : status === 'failed' ? 'bg-red-600' : 'bg-yellow-600'}">${status}</span>`;

        const barWrap = document.createElement('div');
        barWrap.className = 'w-full bg-gray-800 rounded-full h-2 overflow-hidden mt-1';
        const bar = document.createElement('div');
        bar.className = 'h-full bg-gradient-to-r from-red-500 to-red-400';
        bar.style.width = `${percent}%`;
        barWrap.appendChild(bar);

        right.appendChild(badge);
        right.appendChild(barWrap);

        card.appendChild(meta);
        card.appendChild(right);

        // If completed, add download link
        if (job.filename) {
            const link = document.createElement('a');
            link.href = `${CONFIG.API_BASE_URL.replace(/\/api$/,'')}/api/file/${encodeURIComponent(job.filename)}`;
            link.className = 'ml-3 text-sm text-green-300 hover:underline';
            link.textContent = 'Download';
            right.appendChild(link);
        }

        elements.queueList.appendChild(card);
    }
}

function setJob(job) {
    if (!job || !job.id) return;
    queueState.jobs.set(job.id, job);
    renderQueue();
}

function updateJobFromEvent(ev) {
    const existing = queueState.jobs.get(ev.job_id) || { id: ev.job_id };
    const merged = { ...existing, ...(ev.data || {} ) };
    queueState.jobs.set(ev.job_id, merged);
    renderQueue();
}

async function fetchJobsFromServer(){
    try{
        const res = await fetch(`${CONFIG.API_BASE_URL}/queue`);
        if(!res.ok) return;
        const data = await res.json();
        const jobs = data.jobs || [];
        jobs.forEach(j=> queueState.jobs.set(j.id, j));
        renderQueue();
    }catch(e){ console.error('Failed to fetch jobs', e) }
}

function connectSSE(){
    try{
        const url = `${CONFIG.API_BASE_URL}/stream`;
        if (queueState.es) queueState.es.close();
        const es = new EventSource(url);
        queueState.es = es;
        es.onmessage = async (e) => {
            try{
                const ev = JSON.parse(e.data);
                if(ev.type === 'job_enqueued'){
                    // fetch job detail
                    try{
                        const detail = await fetch(`${CONFIG.API_BASE_URL}/queue/${ev.job_id}`);
                        if(detail.ok){
                            const jd = await detail.json();
                            if(jd.success && jd.job) setJob(jd.job);
                        }
                    }catch(err){ console.error('fetch job detail', err) }
                } else if(ev.type === 'job_progress' || ev.type === 'job_retry'){
                    updateJobFromEvent(ev);
                } else if(ev.type === 'job_done' || ev.type === 'job_failed'){
                    updateJobFromEvent(ev);
                }
            }catch(err){ console.error('SSE parse', err) }
        };
        es.onerror = (err) => { console.error('SSE error', err); }
    }catch(e){ console.error('SSE init failed', e) }
}

function escapeHtml(str){
    if(!str) return '';
    return String(str).replace(/[&<>\"']/g, function(c){
        return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
}

// Resolve API base dynamically for local dev: if frontend served on localhost, prefer backend port 8001
const _LOCAL_API = (location.hostname === '127.0.0.1' || location.hostname === 'localhost')
    ? `${location.protocol}//${location.hostname}:8001/api`
    : 'http://localhost:5000/api';

const CONFIG = {
    API_BASE_URL: _LOCAL_API,
    MAX_URL_LENGTH: 200,
    SUPPORTED_DOMAINS: ['youtube.com', 'youtu.be', 'youtube.co', 'ytimg.com'],
    DEBOUNCE_DELAY: 500,
    NOTIFICATION_TIMEOUT: 5000,
};

// ============================================================================
// State Management
// ============================================================================

const appState = {
    currentVideoInfo: null,
    selectedFormat: null,
    selectedQuality: null,
    isLoading: false,
    isDownloading: false,
    theme: localStorage.getItem('theme') || 'dark',
    includeSubs: false,
    subsLangs: null,
};

// ============================================================================
// DOM Elements
// ============================================================================

const elements = {
    root: document.getElementById('root'),
    themeToggle: document.getElementById('themeToggle'),
    sunIcon: document.getElementById('sunIcon'),
    moonIcon: document.getElementById('moonIcon'),
    downloadForm: document.getElementById('downloadForm'),
    urlInput: document.getElementById('urlInput'),
    pasteBtn: document.getElementById('pasteBtn'),
    includeSubsCheckbox: null,
    subsLangInput: null,
    expandPlaylistCheckbox: null,
    addToQueueBtn: null,
    batchToggleBtn: null,
    batchTextarea: null,
    submitBtn: document.getElementById('submitBtn'),
    submitBtnText: document.getElementById('submitBtnText'),
    submitSpinner: document.getElementById('submitSpinner'),
    errorMessage: document.getElementById('errorMessage'),
    loadingState: document.getElementById('loadingState'),
    previewSection: document.getElementById('previewSection'),
    thumbnail: document.getElementById('thumbnail'),
    videoTitle: document.getElementById('videoTitle'),
    videoChannel: document.getElementById('videoChannel'),
    videoDuration: document.getElementById('videoDuration'),
    videoQuality: document.getElementById('videoQuality'),
    formatOptions: document.getElementById('formatOptions'),
    qualityContainer: document.getElementById('qualityContainer'),
    qualityOptions: document.getElementById('qualityOptions'),
    downloadBtn: document.getElementById('downloadBtn'),
    downloadBtnText: document.getElementById('downloadBtnText'),
    downloadSpinner: document.getElementById('downloadSpinner'),
    progressSection: document.getElementById('progressSection'),
    progressBar: document.getElementById('progressBar'),
    progressPercent: document.getElementById('progressPercent'),
    successNotification: document.getElementById('successNotification'),
    successMessage: document.getElementById('successMessage'),
    queueSection: document.getElementById('queueSection'),
    queueList: document.getElementById('queueList'),
    clearQueueBtn: document.getElementById('clearQueueBtn'),
    quickResult: document.getElementById('quickResult'),
    quickThumb: document.getElementById('quickThumb'),
    quickTitle: document.getElementById('quickTitle'),
    quickMeta: document.getElementById('quickMeta'),
    quickMp4Btn: document.getElementById('quickMp4Btn'),
    quickMp3Btn: document.getElementById('quickMp3Btn'),
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Format seconds to readable time string (HH:MM:SS)
 */
function formatDuration(seconds) {
    if (!seconds) return 'Unknown';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    return `${minutes}:${String(secs).padStart(2, '0')}`;
}

/**
 * Format bytes to readable file size
 */
function formatFileSize(bytes) {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(2)} ${units[unitIndex]}`;
}

/**
 * Validate YouTube URL format
 */
function isValidYoutubeUrl(url) {
    try {
        const urlObj = new URL(url);
        const hostname = urlObj.hostname.toLowerCase();
        return CONFIG.SUPPORTED_DOMAINS.some(domain => hostname.includes(domain));
    } catch {
        return false;
    }
}

/**
 * Show error message
 */
function showError(message) {
    elements.errorMessage.textContent = message;
    elements.errorMessage.classList.remove('hidden');
    elements.errorMessage.classList.add('animate-fade-in');
    
    setTimeout(() => {
        elements.errorMessage.classList.add('hidden');
    }, 6000);
}

/**
 * Show success notification
 */
function showSuccess(message) {
    elements.successMessage.textContent = message;
    elements.successNotification.classList.remove('hidden');
    elements.successNotification.classList.add('animate-fade-in-out');
    
    setTimeout(() => {
        elements.successNotification.classList.add('hidden');
    }, CONFIG.NOTIFICATION_TIMEOUT);
}

/**
 * Set loading state
 */
function setLoading(isLoading, message = 'Fetching video information...') {
    appState.isLoading = isLoading;
    
    if (isLoading) {
        elements.loadingState.querySelector('p').textContent = message;
        elements.loadingState.classList.remove('hidden');
        elements.previewSection.classList.add('hidden');
        elements.submitBtn.disabled = true;
        elements.submitBtnText.textContent = 'Loading...';
        elements.submitSpinner.classList.remove('hidden');
    } else {
        elements.loadingState.classList.add('hidden');
        elements.submitBtn.disabled = false;
        elements.submitBtnText.textContent = 'Get Video Info';
        elements.submitSpinner.classList.add('hidden');
    }
}

/**
 * Hide error message
 */
function hideError() {
    elements.errorMessage.classList.add('hidden');
}

// ============================================================================
// Theme Management
// ============================================================================

/**
 * Initialize theme
 */
function initializeTheme() {
    applyTheme(appState.theme);
}

/**
 * Apply theme (dark/light)
 */
function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    
    if (theme === 'dark') {
        elements.sunIcon.classList.add('hidden');
        elements.moonIcon.classList.remove('hidden');
        elements.root.classList.remove('light');
        elements.root.classList.add('dark');
    } else {
        elements.sunIcon.classList.remove('hidden');
        elements.moonIcon.classList.add('hidden');
        elements.root.classList.remove('dark');
        elements.root.classList.add('light');
    }
    
    localStorage.setItem('theme', theme);
    appState.theme = theme;
}

/**
 * Toggle theme
 */
function toggleTheme() {
    const newTheme = appState.theme === 'dark' ? 'light' : 'dark';
    applyTheme(newTheme);
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch video information from backend
 */
async function fetchVideoInfo(url) {
    try {
        setLoading(true, 'Fetching video information...');
        hideError();

        const response = await fetch(`${CONFIG.API_BASE_URL}/video-info`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            body: JSON.stringify({ url: url.trim() }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `Server error: ${response.status}`);
        }

        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Failed to fetch video information');
        }

        appState.currentVideoInfo = data.data;
        displayVideoPreview(data.data);
        setLoading(false);
        
    } catch (error) {
        console.error('Fetch video info error:', error);
        showError(error.message || 'Failed to fetch video. Please check the URL and try again.');
        setLoading(false);
        elements.previewSection.classList.add('hidden');
    }
}

/**
 * Download video with selected options
 */
async function downloadVideo() {
    if (!appState.currentVideoInfo || !appState.selectedFormat) {
        showError('Please select a format before downloading');
        return;
    }

    try {
        elements.downloadBtn.disabled = true;
        elements.downloadBtnText.textContent = 'Starting...';
        elements.downloadSpinner.classList.remove('hidden');
        elements.progressSection.classList.remove('hidden');

        const payload = {
            url: appState.currentVideoInfo.url,
            format: appState.selectedFormat,
            quality: appState.selectedQuality,
            include_subs: !!appState.includeSubs,
            subs_langs: appState.subsLangs || null,
        };

        // Start download
        const response = await fetch(`${CONFIG.API_BASE_URL}/download`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || 'Download failed');
        }

        const data = await response.json();

        if (data.success && data.download_url) {
            // Initiate download
            const link = document.createElement('a');
            link.href = data.download_url;
            link.download = data.filename || 'video.mp4';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            showSuccess(`✓ ${data.filename} downloaded successfully!`);
            
            // Reset download button
            setTimeout(() => {
                elements.downloadBtn.disabled = false;
                elements.downloadBtnText.textContent = 'Download';
                elements.downloadSpinner.classList.add('hidden');
                elements.progressSection.classList.add('hidden');
                elements.progressBar.style.width = '0%';
            }, 1000);
        } else {
            throw new Error(data.error || 'Download failed');
        }

    } catch (error) {
        console.error('Download error:', error);
        showError(error.message || 'Failed to download video. Please try again.');
        elements.downloadBtn.disabled = false;
        elements.downloadBtnText.textContent = 'Download';
        elements.downloadSpinner.classList.add('hidden');
        elements.progressSection.classList.add('hidden');
    }
}

/**
 * Enqueue current video or a batch of items
 */
async function addToQueueBatch(items) {
    try {
        const payload = { items };
        const res = await fetch(`${CONFIG.API_BASE_URL}/queue`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.error || 'Failed to enqueue');
        }
        const data = await res.json();
        if (data.success) {
            showSuccess(`Added ${data.job_ids?.length || data.count || 1} item(s) to queue`);
            fetchJobsFromServer();
        } else {
            throw new Error(data.error || 'Enqueue failed');
        }
    } catch (err) {
        showError(err.message || 'Failed to add to queue');
    }
}

// ============================================================================
// UI Rendering Functions
// ============================================================================

/**
 * Display video preview information
 */
function displayVideoPreview(videoInfo) {
    // Basic info
    elements.thumbnail.src = videoInfo.thumbnail_url || '';
    elements.thumbnail.alt = videoInfo.title || 'Video thumbnail';
    elements.videoTitle.textContent = videoInfo.title || 'Untitled Video';
    
    // Channel info
    if (videoInfo.channel_name) {
        elements.videoChannel.innerHTML = `
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M18 9.5a8.5 8.5 0 11-17 0 8.5 8.5 0 0117 0z"/>
            </svg>
            <span>${videoInfo.channel_name}</span>
        `;
    }

    // Duration
    if (videoInfo.duration) {
        const durationText = formatDuration(videoInfo.duration);
        elements.videoDuration.innerHTML = `
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00-.293.707l-2.828 2.829a1 1 0 101.414 1.414L8 10.414V6z" clip-rule="evenodd"/>
            </svg>
            <span>${durationText}</span>
        `;
    }

    // Quality badge
    const maxQuality = videoInfo.formats?.reduce((max, f) => {
        const quality = parseInt(f.height) || 0;
        return quality > max ? quality : max;
    }, 0) || 0;

    let qualityBadge = 'Standard';
    let qualityColor = 'bg-slate-600';
    
    if (maxQuality >= 1080) {
        qualityBadge = '4K Ultra HD';
        qualityColor = 'bg-purple-600';
    } else if (maxQuality >= 720) {
        qualityBadge = 'HD';
        qualityColor = 'bg-blue-600';
    }

    elements.videoQuality.innerHTML = `<span class="px-2 py-1 rounded text-xs font-semibold ${qualityColor}">📺 ${qualityBadge}</span>`;

    // Format options
    renderFormatOptions(videoInfo.formats);

    // Show preview
    elements.previewSection.classList.remove('hidden');
    elements.previewSection.classList.add('animate-fade-in');

    // Also populate quick hero result if present
    if (elements.quickResult) {
        elements.quickThumb.src = videoInfo.thumbnail_url || '';
        elements.quickTitle.textContent = videoInfo.title || 'Untitled';
        elements.quickMeta.textContent = `${videoInfo.channel_name || ''} • ${formatDuration(videoInfo.duration) || ''}`;
        elements.quickResult.classList.remove('hidden');
        // wire quick buttons
        if (elements.quickMp4Btn){
            elements.quickMp4Btn.onclick = () => {
                appState.selectedFormat = 'mp4';
                appState.selectedQuality = 'best';
                downloadVideo();
            }
        }
        if (elements.quickMp3Btn){
            elements.quickMp3Btn.onclick = () => {
                appState.selectedFormat = 'mp3';
                appState.selectedQuality = 'best';
                downloadVideo();
            }
        }
    }
}

/**
 * Render format selection options
 */
function renderFormatOptions(formats) {
    elements.formatOptions.innerHTML = '';
    appState.selectedFormat = null;
    
    const formatTypes = {
        'mp4': { label: '📹 MP4 Video', icon: '🎬' },
        'mp3': { label: '🎵 MP3 Audio', icon: '🎵' },
    };

    // Add MP4 option if available — detect by height or non-audio extension
    const hasVideo = formats && formats.some(f => (f.height && parseInt(f.height) > 0) || (f.ext && f.ext !== 'mp3'));
    if (hasVideo) {
        const option = document.createElement('label');
        option.className = 'format-option flex items-center cursor-pointer';
        option.innerHTML = `
            <input type="radio" name="format" value="mp4" class="w-4 h-4 text-red-500">
            <span class="ml-3 flex-1 font-medium">📹 MP4 Video</span>
        `;
        elements.formatOptions.appendChild(option);
    }

    // Add MP3 option
    const option = document.createElement('label');
    option.className = 'format-option flex items-center cursor-pointer';
    option.innerHTML = `
        <input id="mp3Radio" type="radio" name="format" value="mp3" class="w-4 h-4 text-red-500">
        <span id="mp3FormatLabel" class="ml-3 flex-1 font-medium">🎵 MP3 Audio</span>
    `;
    elements.formatOptions.appendChild(option);

    // Add event listeners
    document.querySelectorAll('input[name="format"]').forEach(input => {
        input.addEventListener('change', (e) => {
            appState.selectedFormat = e.target.value;
            renderQualityOptions(formats, e.target.value);
        });
    });
}

/**
 * Render quality selection options
 */
function renderQualityOptions(formats, format) {
    if (format === 'mp3') {
        elements.qualityContainer.classList.add('hidden');
        appState.selectedQuality = 'best';
        return;
    }

    if (format === 'mp4' && formats && formats.length > 0) {
        // detect actual best available height from formats
        const maxAvail = formats.reduce((mx, f) => {
            const h = parseInt(f.height) || 0; return h > mx ? h : mx;
        }, 0);
        const bestLabel = maxAvail > 0 ? `Best Available (${maxAvail}p)` : 'Best Available';

        const qualities = [
            { id: 'best', label: bestLabel, minHeight: 0 },
            { id: '1080', label: '1080p (Full HD)', minHeight: 1080 },
            { id: '720', label: '720p (HD)', minHeight: 720 },
            { id: '360', label: '360p (SD)', minHeight: 360 },
        ];

        elements.qualityOptions.innerHTML = '';
        
        qualities.forEach(quality => {
            const hasQuality = formats.some(f => 
                !f.height || parseInt(f.height) >= quality.minHeight
            );

            if (hasQuality || quality.id === 'best') {
                const label = document.createElement('label');
                label.className = 'quality-option flex items-center cursor-pointer';
                label.style.opacity = hasQuality ? '1' : '0.5';
                label.title = hasQuality ? '' : 'This quality may not be available for this video';
                label.innerHTML = `
                    <input  type="radio" name="quality" value="${quality.id}" class="w-4 h-4 text-red-500" ${quality.id === 'best' ? 'checked' : ''}>
                    <span class="ml-2 text-sm">${quality.label}</span>
                `;
                elements.qualityOptions.appendChild(label);
            }
        });

        document.querySelectorAll('input[name="quality"]').forEach(input => {
            input.addEventListener('change', (e) => {
                appState.selectedQuality = e.target.value;
            });
        });

        // Set default quality to best
        appState.selectedQuality = 'best';
        elements.qualityContainer.classList.remove('hidden');
    }
}

// ============================================================================
// Event Listeners
// ============================================================================

/**
 * Initialize event listeners
 */
function initializeEventListeners() {
    // Theme toggle
    elements.themeToggle.addEventListener('click', toggleTheme);

    // Paste button
    elements.pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                elements.urlInput.value = text;
                elements.urlInput.focus();
            }
        } catch (error) {
            showError('Unable to access clipboard. Please paste manually.');
        }
    });

    // Add to queue button (created dynamically)
    if (elements.addToQueueBtn) {
        elements.addToQueueBtn.addEventListener('click', async () => {
            const url = elements.urlInput.value.trim();
            if (!url || !isValidYoutubeUrl(url)) {
                showError('Enter a valid YouTube URL before adding to queue');
                return;
            }

            const item = {
                url,
                format: appState.selectedFormat || 'mp4',
                quality: appState.selectedQuality || 'best',
                include_subs: !!appState.includeSubs,
                subs_langs: appState.subsLangs || null,
            };
            await addToQueueBatch([item]);
        });
    }

    // Batch toggle and textarea handling
    if (elements.batchToggleBtn) {
        elements.batchToggleBtn.addEventListener('click', () => {
            const t = elements.batchTextarea;
            if (!t) return;
            t.classList.toggle('hidden');
        });
    }

    if (elements.batchTextarea) {
        // Add a quick enqueue from textarea: Ctrl+Enter
        elements.batchTextarea.addEventListener('keydown', async (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                const lines = elements.batchTextarea.value.split('\n').map(l => l.trim()).filter(Boolean);
                const items = lines.filter(isValidYoutubeUrl).map(url => ({ url, format: 'mp4' }));
                if (items.length === 0) {
                    showError('No valid URLs found in batch input');
                    return;
                }
                await addToQueueBatch(items);
                elements.batchTextarea.value = '';
                elements.batchTextarea.classList.add('hidden');
            }
        });
    }

    // Form submission
    elements.downloadForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const url = elements.urlInput.value.trim();

        // Validation
        if (!url) {
            showError('Please enter a YouTube URL');
            return;
        }

        if (url.length > CONFIG.MAX_URL_LENGTH) {
            showError('URL is too long');
            return;
        }

        if (!isValidYoutubeUrl(url)) {
            showError('Invalid YouTube URL. Please check and try again.');
            return;
        }

        fetchVideoInfo(url);
    });

    // Download button
    elements.downloadBtn.addEventListener('click', downloadVideo);

    // Clear queue button (UI only)
    if (elements.clearQueueBtn){
        elements.clearQueueBtn.addEventListener('click', () => {
            queueState.jobs.clear();
            renderQueue();
        });
    }

    // URL input auto-clear error on focus
    elements.urlInput.addEventListener('focus', hideError);

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + V to paste when URL input is focused
        if (e.key === 'v' && (e.ctrlKey || e.metaKey) && document.activeElement === elements.urlInput) {
            navigator.clipboard.readText().then(text => {
                elements.urlInput.value = text;
            }).catch(console.error);
        }
    });
}

// ============================================================================
// Initialization
// ============================================================================

/**
 * Initialize application
 */
function initialize() {
    console.log('🚀 Initializing YouTube Video Downloader...');
    
    // Initialize theme
    initializeTheme();
    
    // Initialize event listeners
    initializeEventListeners();

    // Dynamically create small controls under the URL input for advanced features
    
    
    // Check for auto-paste on page load (if clipboard has YouTube URL)
    navigator.clipboard.readText().then(text => {
        if (isValidYoutubeUrl(text)) {
            elements.urlInput.value = text;
        }
    }).catch(() => {
        // Clipboard access denied or empty, that's okay
    });

    console.log('✓ Application initialized successfully');
}

// Start application when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}
