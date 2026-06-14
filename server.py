import os
import sys
import json
import threading
import cv2
import numpy as np
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sock import Sock
from werkzeug.serving import make_server

# Support PyInstaller path
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'web', 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'web', 'static')
else:
    template_folder = "web/templates"
    static_folder = "web/static"

app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
sock = Sock(app)

# Global frame callback, active WebSocket, and settings
_on_frame_callback = None
_active_ws = None
_latest_settings = None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/cert_download")
def download_cert():
    import os
    from flask import send_from_directory
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    dir_path = os.path.join(appdata, "OpenCam", "certs")
    return send_from_directory(dir_path, "cert.pem", as_attachment=True, mimetype="application/x-x509-ca-cert")

@app.route("/log", methods=["POST"])
def receive_log():
    try:
        data = request.json
        print(f"[PHONE] {data.get('msg', '')}", flush=True)
        return jsonify({"status": "ok"})
    except Exception:
        return jsonify({"status": "error"})

@app.route("/frame", methods=["POST"])
def receive_frame_http():
    """Fallback route for iOS Safari which strictly blocks WebSockets over self-signed SSL."""
    try:
        data = request.data
        if data:
            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None and _on_frame_callback:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                _on_frame_callback(img_rgb)
        
        # Return settings if they exist so the phone can poll them
        if _latest_settings:
            return jsonify(_latest_settings)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@sock.route("/ws")
def ws_handler(ws):
    """Bidirectional WebSocket: receives JPEG frames, sends settings commands."""
    global _active_ws
    _active_ws = ws
    print("WebSocket connected")
    try:
        while True:
            data = ws.receive()
            if data is None:
                break
            
            # Binary data = JPEG frame from phone
            if isinstance(data, bytes):
                nparr = np.frombuffer(data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if img is not None and _on_frame_callback:
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    _on_frame_callback(img_rgb)
            # Text data = JSON command (ignored from phone for now)
    except Exception as e:
        print(f"WebSocket closed: {e}")
    finally:
        _active_ws = None


class ServerManager:
    def __init__(self, host="0.0.0.0", port=5000, cert_path="cert.pem", key_path="key.pem"):
        self.host = host
        self.port = port
        self.cert_path = cert_path
        self.key_path = key_path
        self.server = None
        self.thread = None

    def start(self):
        print(f"Starting server on https://{self.host}:{self.port}")
        self.server = make_server(self.host, self.port, app, ssl_context=(self.cert_path, self.key_path))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.thread.join(timeout=2.0)

    def set_frame_callback(self, callback):
        global _on_frame_callback
        _on_frame_callback = callback

    def send_settings_to_phone(self, width, height, fps):
        """Send resolution/fps settings to the phone via WebSocket or save for HTTP fallback."""
        global _latest_settings
        cmd = {
            "type": "settings",
            "width": width,
            "height": height,
            "fps": fps
        }
        _latest_settings = cmd
        if _active_ws:
            try:
                _active_ws.send(json.dumps(cmd))
            except Exception as e:
                print(f"Error sending settings via WS: {e}")
