# OpenCam

Turn your iOS device into a high-quality PC webcam effortlessly via local network.

![OpenCam Banner](https://github.com/TungTungDevCPUMAX/OpenCam/blob/main/web/static/Logo.png?raw=true)

OpenCam allows you to use your iPhone or iPad as a wireless webcam for your Windows PC over a local Wi-Fi connection. It utilizes a custom Python backend to bridge the high-quality mobile camera directly into OBS, Zoom, Teams, or Discord using a virtual camera driver.

## Features
- **High-Quality Wireless Video:** Uses standard WebSockets and HTTP for low latency, high-quality streams.
- **Easy Setup:** Auto-generates local SSL certificates so you can securely access the camera via your browser without installing a dedicated iOS app.
- **Adjustable Settings:** Control Resolution and Framerate from your PC to balance quality and mobile battery usage.
- **Auto Driver Installation:** Automatically installs the required virtual camera drivers for Windows.
- **QR Code Pairing:** Simply scan the QR code from the PC app with your phone to connect!

## Requirements
- Windows 10/11
- Python 3.9+
- iOS Device (iPhone/iPad) on the **same Wi-Fi network**.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/TungTungDevCPUMAX/OpenCam.git
   cd OpenCam
   ```

2. **Set up a virtual environment (recommended):**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Start the application:**
   ```bash
   python main.py
   ```
2. **Install Driver (First Time):**
   If this is your first time running OpenCam, the GUI will prompt you to install the OpenCam virtual camera driver. Click the button to grant admin rights and install it.

3. **Connect Your Phone:**
   - The OpenCam PC application will display a **QR Code**.
   - Open your iPhone's camera and scan the QR Code.
   - Accept the security certificate prompt (since it uses a self-signed local SSL certificate for secure camera access).
   - Tap "Start OpenCam" on your phone!

4. **Use as Webcam:**
   You can now select "OpenCam" as a video source in your favorite software like OBS Studio, Zoom, Discord, etc.

## Build (Executable)

If you want to package OpenCam into a standalone `.exe` file to run without Python, you can use PyInstaller. Since the app serves web files, you must include the `web/` folder:

1. **Install PyInstaller:**
   ```bash
   pip install pyinstaller
   ```
2. **Build the application:**
   ```bash
   pyinstaller --noconfirm --onefile --windowed --add-data "web;web" --name "OpenCam" main.py
   ```
3. Your executable will be ready as a single file in the `dist/` directory!

## Settings
You can adjust the camera resolution and framerate directly from the desktop application. If your phone is overheating or draining battery too quickly, lower the resolution to `640x480` and the framerate to `24 FPS`.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
Created by [TungTungDevCPUMAX](https://github.com/TungTungDevCPUMAX)
