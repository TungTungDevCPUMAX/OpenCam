import os
import sys

import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# Ensure certificates are generated before starting the server
from cert_gen import generate_self_signed_cert
local_ip = get_local_ip()
cert_path, key_path = generate_self_signed_cert(ip_address=local_ip)

from server import ServerManager
from virtual_cam import VirtualCamManager
from gui import OpenCamGUI

def main():
    # 1. Initialize Managers
    vcam_manager = VirtualCamManager(name="OpenCam")
    server_manager = ServerManager(host="0.0.0.0", port=5000, cert_path=cert_path, key_path=key_path)

    # 2. Setup GUI
    app = OpenCamGUI(server_manager, vcam_manager)

    # 3. Define Frame Callback
    # When a frame is received from WebRTC, send it to VirtualCam and GUI
    def on_frame_received(frame_rgb):
        vcam_manager.update_frame(frame_rgb)
        app.update_preview(frame_rgb)

    server_manager.set_frame_callback(on_frame_received)

    # 4. Start GUI Main Loop
    # Note: The server and vcam will be started by the GUI after checking driver installation
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

if __name__ == "__main__":
    main()
