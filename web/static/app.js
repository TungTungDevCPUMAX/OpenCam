// DOM Elements
const startBtn = document.getElementById('start-btn');
const stopBtn = document.getElementById('stop-btn');
const startControls = document.getElementById('start-controls');
const statusBadge = document.getElementById('status-badge');
const recordingDot = document.getElementById('recording-dot');
const localVideo = document.getElementById('local-video');
const infoText = document.getElementById('info-text');
const statsPanel = document.getElementById('stats-panel');
const statRes = document.getElementById('stat-res');
const statFps = document.getElementById('stat-fps');
const flipBtn = document.getElementById('flip-btn');
const overlayControls = document.getElementById('video-overlay-controls');
const videoContainer = document.getElementById('video-container');

// Mobile Debugger
const debugContainer = document.getElementById('mobile-debug');
const debugContent = document.getElementById('mobile-debug-content');
let debugMode = false; // Set to true from PC to enable

function logDebug(msg, isError = false) {
    const time = new Date().toISOString().split('T')[1].slice(0, -1);
    const fullMsg = `[${time}] ${isError ? 'ERROR: ' : ''}${msg}`;
    console.log(fullMsg);
    
    // Send to PC Server
    fetch('/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ msg: fullMsg })
    }).catch(e => console.error("Failed to send log to PC", e));
}

window.onerror = function(msg, url, line) {
    logDebug(`${msg} (L${line})`, true);
};

// State
let localStream = null;
let wakeLock = null;
let ws = null;
let captureInterval = null;
let currentFacingMode = 'environment';
let fallbackMode = false;
let sending = false;

// Hidden canvas for frame capture
const canvas = document.createElement('canvas');
const ctx = canvas.getContext('2d');

// Quality settings
let jpegQuality = 0.85;
let targetFps = 30;
let currentWidth = 1280;
let currentHeight = 720;

// ====== TOUCH / SCROLL LOCK ======
// Prevent ALL scrolling, bouncing, pull-to-refresh on iOS/Android
document.addEventListener('touchmove', function(e) {
    e.preventDefault();
}, { passive: false });

document.addEventListener('gesturestart', function(e) {
    e.preventDefault();
});

document.addEventListener('gesturechange', function(e) {
    e.preventDefault();
});

// ====== CAMERA HELPERS ======
async function restartCamera() {
    if (localStream) {
        localStream.getTracks().forEach(t => t.stop());
    }
    localStream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
            facingMode: currentFacingMode,
            width: { ideal: currentWidth },
            height: { ideal: currentHeight },
            frameRate: { ideal: targetFps }
        }
    });
    localVideo.srcObject = localStream;
    updateStatsUI();

    // Restart capture interval at new FPS
    if (captureInterval) {
        clearInterval(captureInterval);
        captureInterval = setInterval(captureAndSend, 1000 / targetFps);
    }
}

flipBtn.addEventListener('click', async () => {
    currentFacingMode = currentFacingMode === 'environment' ? 'user' : 'environment';
    if (localStream) {
        await restartCamera();
    }
});

// ====== WAKE LOCK ======
async function requestWakeLock() {
    try {
        if ('wakeLock' in navigator) {
            wakeLock = await navigator.wakeLock.request('screen');
        }
    } catch (err) {
        console.error(err);
    }
}

function releaseWakeLock() {
    if (wakeLock) {
        wakeLock.release();
        wakeLock = null;
    }
}

// ====== STATS ======
function updateStatsUI() {
    if (localStream) {
        const track = localStream.getVideoTracks()[0];
        const settings = track.getSettings();
        statRes.textContent = `${settings.width}x${settings.height}`;
        statFps.textContent = `${settings.frameRate || targetFps}`;
        statsPanel.style.display = 'flex';
    } else {
        statsPanel.style.display = 'none';
    }
}

let inFlightRequests = 0;
const MAX_IN_FLIGHT = 2;

// ====== CORE CAPTURE LOOP ======
function captureAndSend() {
    if (!localVideo.videoWidth) return;
    
    // In fallback mode, limit concurrent requests to avoid memory leaks
    if (fallbackMode && inFlightRequests >= MAX_IN_FLIGHT) return;
    // In WS mode, ensure we only process one frame at a time
    if (!fallbackMode && sending) return;
    
    sending = true;
    
    canvas.width = localVideo.videoWidth;
    canvas.height = localVideo.videoHeight;
    
    ctx.drawImage(localVideo, 0, 0, canvas.width, canvas.height);
    
    // Balance quality and performance
    let quality = 0.85; // Good crisp quality but lightweight
    if (targetFps >= 60 || currentWidth >= 1920) {
        quality = 0.70;
    } else if (targetFps >= 30 && currentWidth >= 1280) {
        quality = 0.75;
    } else {
        quality = 0.80;
    }

    canvas.toBlob(blob => {
        if (blob) {
            if (fallbackMode) {
                inFlightRequests++;
                sending = false; // Allow next frame capture immediately!
                
                fetch('/frame', {
                    method: 'POST',
                    body: blob,
                    headers: { 'Content-Type': 'application/octet-stream' }
                })
                .then(r => r.json())
                .then(cmd => {
                    if (cmd && cmd.type === 'settings' && 
                        (cmd.width !== currentWidth || cmd.height !== currentHeight || cmd.fps !== targetFps)) {
                        currentWidth = cmd.width;
                        currentHeight = cmd.height;
                        targetFps = cmd.fps;
                        restartCamera();
                    }
                })
                .catch(e => {})
                .finally(() => {
                    inFlightRequests--;
                });
            } else if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(blob);
                sending = false;
            } else {
                sending = false;
            }
        } else {
            sending = false;
        }
    }, 'image/jpeg', quality);
}

// ====== START ======
async function start() {
    try {
        // Hide start button, show overlay controls
        startControls.classList.add('hidden');
        overlayControls.classList.add('visible');
        infoText.textContent = "Connecting...";
        document.body.classList.add('streaming');

        await requestWakeLock();

        // Get camera
        localStream = await navigator.mediaDevices.getUserMedia({
            audio: false,
            video: {
                facingMode: currentFacingMode,
                width: { ideal: currentWidth },
                height: { ideal: currentHeight },
                frameRate: { ideal: targetFps }
            }
        });
        logDebug(`Camera acquired: ${localStream.getVideoTracks()[0].label}`);
        localVideo.srcObject = localStream;
        updateStatsUI();

        // Connect WebSocket
        const wsUrl = `wss://${window.location.host}/ws`;
        logDebug(`Connecting WS to ${wsUrl}...`);
        
        ws = new WebSocket(wsUrl);
        ws.binaryType = 'arraybuffer';

        ws.onopen = () => {
            logDebug('WS Connected successfully!');
            statusBadge.textContent = 'Connected';
            statusBadge.className = 'status-badge connected';
            recordingDot.classList.add('active');
            infoText.textContent = "Streaming...";
            stopBtn.classList.remove('hidden');

            // Start capturing
            captureInterval = setInterval(captureAndSend, 1000 / targetFps);
        };

        ws.onmessage = (event) => {
            // Receive settings from PC
            if (typeof event.data === 'string') {
                try {
                    const cmd = JSON.parse(event.data);
                    if (cmd.type === 'settings') {
                        console.log(`Settings received: ${cmd.width}x${cmd.height} @ ${cmd.fps}fps`);
                        currentWidth = cmd.width;
                        currentHeight = cmd.height;
                        targetFps = cmd.fps;
                        restartCamera();
                    }
                } catch (e) {
                    logDebug(`WS JSON Error: ${e.message}`, true);
                }
            }
        };

        ws.onclose = (event) => {
            logDebug(`WS Closed (Code: ${event.code})`, true);
            if (!fallbackMode && event.code === 1006 && !captureInterval) {
                // If it closes immediately with 1006 before we even start capturing, it's the iOS SSL block!
                logDebug("Activating iOS HTTP fallback mode...", true);
                fallbackMode = true;
                statusBadge.textContent = 'iOS Mode (Fallback)';
                statusBadge.className = 'status-badge connected';
                recordingDot.classList.add('active');
                infoText.textContent = "HTTP streaming...";
                stopBtn.classList.remove('hidden');
                captureInterval = setInterval(captureAndSend, 1000 / targetFps);
            } else if (!fallbackMode) {
                stop();
            }
        };

        ws.onerror = (error) => {
            logDebug(`WS Error! SSL certificate blocked or network issue.`, true);
            // Don't stop() here, wait for onclose to trigger fallback
        };

    } catch (err) {
        logDebug(`GLOBAL ERROR: ${err.name} - ${err.message}`, true);
        infoText.textContent = `Error: ${err.message}`;
        startControls.classList.remove('hidden');
        overlayControls.classList.remove('visible');
        document.body.classList.remove('streaming');
    }
}

// ====== STOP ======
function stop() {
    if (captureInterval) {
        clearInterval(captureInterval);
        captureInterval = null;
    }

    if (ws) {
        ws.close();
        ws = null;
    }

    if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
        localStream = null;
    }

    localVideo.srcObject = null;
    releaseWakeLock();

    statusBadge.textContent = 'Disconnected';
    statusBadge.className = 'status-badge disconnected';
    recordingDot.classList.remove('active');
    infoText.textContent = "Ready to stream";

    startControls.classList.remove('hidden');
    overlayControls.classList.remove('visible');
    stopBtn.classList.add('hidden');
    document.body.classList.remove('streaming');
    updateStatsUI();
}

// ====== EVENT LISTENERS ======
startBtn.addEventListener('click', start);
stopBtn.addEventListener('click', stop);
window.addEventListener('beforeunload', stop);
