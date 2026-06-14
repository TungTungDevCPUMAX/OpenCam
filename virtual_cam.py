import os
import ctypes
import urllib.request
import subprocess
import threading
import pyvirtualcam
import numpy as np

class VirtualCamManager:
    def __init__(self, name="OpenCam"):
        self.name = name
        self.cam = None
        self._running = False
        self._lock = threading.Lock()
        self._frame = None
        self._thread = None
        
        self.width = 1280
        self.height = 720
        self.fps = 30

    def is_driver_installed(self):
        # A simple check: try to initialize pyvirtualcam with our device name
        try:
            with pyvirtualcam.Camera(width=1280, height=720, fps=30, backend="unitycapture", device=self.name) as _:
                return True
        except Exception:
            return False

    def install_driver(self, progress_callback=None):
        """Downloads UnityCapture DLLs and registers them as 'OpenCam'"""
        def log(msg):
            print(msg)
            if progress_callback:
                progress_callback(msg)
                
        log(f"Installation de {self.name}...")
        
        # URLs for UnityCapture
        dll_32 = "https://github.com/schellingb/UnityCapture/raw/master/Install/UnityCaptureFilter32.dll"
        dll_64 = "https://github.com/schellingb/UnityCapture/raw/master/Install/UnityCaptureFilter64.dll"
        
        # Use APPDATA so the DLLs persist when running as a PyInstaller OneFile executable
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        dir_path = os.path.join(appdata, "OpenCam", "driver")
        os.makedirs(dir_path, exist_ok=True)
        
        path_32 = os.path.join(dir_path, "UnityCaptureFilter32.dll")
        path_64 = os.path.join(dir_path, "UnityCaptureFilter64.dll")
        
        try:
            if not os.path.exists(path_32):
                log("Downloading 32-bit...")
                urllib.request.urlretrieve(dll_32, path_32)
                
            if not os.path.exists(path_64):
                log("Downloading 64-bit...")
                urllib.request.urlretrieve(dll_64, path_64)
        except Exception as e:
            log(f"Download error: {e}")
            return False

        # Register DLLs via PowerShell to properly trigger UAC and wait
        import subprocess
        try:
            log("Demande des droits Administrateur...")
            
            # 64-bit driver registration
            arg_64 = f"'/s', '/i:UnityCaptureDevices=1', '/i:UnityCaptureName=\"{self.name}\"', '\"{path_64}\"'"
            # 32-bit driver registration
            arg_32 = f"'/s', '/i:UnityCaptureDevices=1', '/i:UnityCaptureName=\"{self.name}\"', '\"{path_32}\"'"
            
            log("Enregistrement des filtres...")
            # Use PowerShell to run regsvr32 as Admin and wait for completion
            ps_64 = f"Start-Process regsvr32 -ArgumentList {arg_64} -Verb RunAs -Wait -WindowStyle Hidden"
            subprocess.run(['powershell', '-Command', ps_64], check=True)
            
            ps_32 = f"Start-Process regsvr32 -ArgumentList {arg_32} -Verb RunAs -Wait -WindowStyle Hidden"
            subprocess.run(['powershell', '-Command', ps_32], check=True)
            
            log(f"{self.name} installed successfully!")
            return True
        except Exception as e:
            log(f"Installation error: {e}")
            return False

    def update_frame(self, frame):
        """Receives an OpenCV frame (BGR or RGB) and pushes it to the virtual camera"""
        with self._lock:
            # OpenCV provides BGR, pyvirtualcam expects RGB. 
            # Often frames are already RGB depending on how we decode them. 
            # We will handle RGB vs BGR at the caller level.
            self._frame = frame

    def set_format(self, width, height, fps):
        with self._lock:
            self.width = width
            self.height = height
            self.fps = fps
            # Restart camera if running
            was_running = self._running
        
        if was_running:
            self.stop()
            self.start()

    def _run(self):
        try:
            print(f"Starting virtual camera '{self.name}' at {self.width}x{self.height} {self.fps}FPS")
            with pyvirtualcam.Camera(width=self.width, height=self.height, fps=self.fps, backend="unitycapture", device=self.name) as cam:
                print(f"Virtual camera started: {cam.device}")
                self.cam = cam
                while self._running:
                    with self._lock:
                        frame_to_send = self._frame
                    
                    if frame_to_send is not None:
                        # Ensure frame is the right size
                        if frame_to_send.shape[1] != self.width or frame_to_send.shape[0] != self.height:
                            import cv2
                            # Use INTER_AREA for high-quality downscaling (e.g. 1080p to 720p)
                            frame_to_send = cv2.resize(frame_to_send, (self.width, self.height), interpolation=cv2.INTER_AREA)
                        
                        # UnityCapture / pyvirtualcam expects RGBA or RGB
                        cam.send(frame_to_send)
                        cam.sleep_until_next_frame()
                    else:
                        import time
                        time.sleep(1.0 / self.fps)
        except Exception as e:
            print(f"Virtual camera error: {e}")
            self._running = False

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.cam = None
