import customtkinter as ctk
from PIL import Image
import socket
import qrcode
import threading
import math
import time
import sys

class Spinner(ctk.CTkCanvas):
    def __init__(self, master, size=50, color="#4f46e5", bg_color="#0f1115", **kwargs):
        super().__init__(master, width=size, height=size, bg=bg_color, highlightthickness=0, **kwargs)
        self.size = size
        self.color = color
        self.angle = 0
        self.animating = True
        self.arc = self.create_arc(5, 5, size-5, size-5, start=0, extent=90, outline=self.color, width=4, style="arc")
        self.animate()
        
    def animate(self):
        if not self.animating:
            return
        self.angle = (self.angle - 15) % 360
        self.itemconfig(self.arc, start=self.angle)
        self.after(30, self.animate)
        
    def stop(self):
        self.animating = False

class OpenCamGUI(ctk.CTk):
    def __init__(self, server_manager, vcam_manager):
        super().__init__()
        
        self.server_manager = server_manager
        self.vcam_manager = vcam_manager
        
        # Setup Window
        self.title("OpenCam - Studio")
        self.geometry("1200x650")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        
        self.configure(fg_color="#0f1117")
        
        # Theme colors - Clean dark theme
        self.bg_color = "#0f1117"
        self.surface_color = "#181b23"
        self.card_border = "#2a2d3d"
        self.primary_color = "#6366f1"
        self.primary_hover = "#4f46e5"
        self.danger_color = "#e11d48"
        self.text_primary = "#f8fafc"
        self.text_secondary = "#94a3b8"
        
        # Font setup
        self.font_logo = ctk.CTkFont(family="Inter", size=42, weight="bold")
        self.font_title = ctk.CTkFont(family="Inter", size=24, weight="bold")
        self.font_h2 = ctk.CTkFont(family="Inter", size=16, weight="bold")
        self.font_body = ctk.CTkFont(family="Inter", size=14)
        self.font_small = ctk.CTkFont(family="Inter", size=12)
        
        # Get Local IP
        self.local_ip = self.get_local_ip()
        self.url = f"https://{self.local_ip}:5000"
        
        self.setup_ui()
        self.show_splash_screen()
        
        # Start checking after animation
        self.after(2000, self.check_driver)

    def show_splash_screen(self):
        self.splash = ctk.CTkFrame(self, fg_color=self.bg_color)
        self.splash.place(x=0, y=0, relwidth=1, relheight=1)
        
        # Logo and Title
        ctk.CTkLabel(self.splash, text="OpenCam", font=self.font_logo, text_color=self.text_primary).place(relx=0.5, rely=0.4, anchor="center")
        ctk.CTkLabel(self.splash, text="S T U D I O", font=ctk.CTkFont(family="Inter", size=14, weight="bold"), text_color=self.primary_color).place(relx=0.5, rely=0.46, anchor="center")
        
        self.spinner = Spinner(self.splash, size=40, color=self.primary_color, bg_color=self.bg_color)
        self.spinner.place(relx=0.5, rely=0.6, anchor="center")
        
        self.loading_text = ctk.CTkLabel(self.splash, text="Initializing components...", font=self.font_small, text_color=self.text_secondary)
        self.loading_text.place(relx=0.5, rely=0.67, anchor="center")

    def hide_splash_screen(self):
        if hasattr(self, 'splash'):
            self.spinner.stop()
            self.splash.destroy()

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def check_driver(self):
        if hasattr(self, 'splash') and self.splash.winfo_exists():
            self.loading_text.configure(text="Checking video driver...")
        
        if not self.vcam_manager.is_driver_installed():
            self.hide_splash_screen()
            self.show_driver_warning()
        else:
            if hasattr(self, 'splash') and self.splash.winfo_exists():
                self.loading_text.configure(text="Starting web server...")
            self.after(500, self._start_services)

    def _start_services(self):
        self.hide_splash_screen()
        self.hide_driver_warning()
        self.vcam_manager.start()
        self.server_manager.start()

    def install_driver_action(self):
        self.driver_btn.configure(state="disabled")
        
        def update_text(msg):
            self.after(0, lambda: self.driver_btn.configure(text=msg))

        def task():
            success = self.vcam_manager.install_driver(progress_callback=update_text)
            if success:
                # Reboot services smoothly
                self.after(0, self.check_driver)
            else:
                self.after(0, lambda: self.driver_btn.configure(state="normal", text="Error. Retry"))
                
        threading.Thread(target=task, daemon=True).start()

    def show_driver_warning(self):
        self.driver_btn.configure(state="normal", text="Install OpenCam (Admin)")
        self.driver_warning_frame.pack(side="top", fill="x", pady=(0, 20), before=self.preview_frame)
        self.preview_label.configure(text="Waiting for driver...", text_color=self.text_secondary)

    def hide_driver_warning(self):
        self.driver_warning_frame.pack_forget()
        self.preview_label.configure(text="Waiting for connection...", text_color=self.text_secondary)

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=0, minsize=320)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Sidebar (Left) - Glass Card
        self.sidebar = ctk.CTkFrame(self, fg_color=self.surface_color, corner_radius=0, border_width=1, border_color=self.card_border)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Logo
        title_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        title_frame.pack(fill="x", padx=25, pady=(20, 10))
        ctk.CTkLabel(title_frame, text="OpenCam", font=self.font_title, text_color=self.text_primary).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Studio Receiver", font=self.font_small, text_color=self.primary_color).pack(anchor="w")
        
        # QR Code Card - Glass styling
        qr_card = ctk.CTkFrame(self.sidebar, fg_color=self.surface_color, corner_radius=15, border_width=1, border_color=self.card_border)
        qr_card.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(qr_card, text="Scan to connect", font=self.font_body, text_color=self.text_secondary).pack(pady=(10, 5))
        
        qr = qrcode.QRCode(box_size=4, border=1)
        qr.add_data(self.url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        self.qr_ctk_image = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 160))
        ctk.CTkLabel(qr_card, image=self.qr_ctk_image, text="").pack(pady=(0, 10))
        
        url_entry = ctk.CTkEntry(qr_card, font=self.font_small, fg_color=self.surface_color, border_color=self.card_border, justify="center")
        url_entry.pack(fill="x", padx=15, pady=(0, 5))
        url_entry.insert(0, self.url)
        url_entry.configure(state="readonly")
        
        ctk.CTkLabel(qr_card, text="⚠️ Accept the security certificate\non your phone to continue", 
                     font=ctk.CTkFont(family="Inter", size=11), text_color="#f59e0b",
                     justify="center").pack(pady=(0, 12))
        
        settings_card = ctk.CTkFrame(self.sidebar, fg_color=self.surface_color, corner_radius=15, border_width=1, border_color=self.card_border)
        settings_card.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(settings_card, text="Video Quality", font=self.font_h2, text_color=self.text_primary).pack(anchor="w", padx=20, pady=(15, 10))
        
        ctk.CTkLabel(settings_card, text="Resolution", font=self.font_small, text_color=self.text_secondary).pack(anchor="w", padx=20)
        self.res_var = ctk.StringVar(value="1280x720")
        res_dropdown = ctk.CTkOptionMenu(settings_card, variable=self.res_var, values=["1920x1080", "1280x720", "640x480", "480x360"], command=self.on_settings_change,
                                             fg_color=self.bg_color, button_color=self.primary_color, button_hover_color=self.primary_hover,
                                             font=self.font_small, height=32, state="normal")
        res_dropdown.pack(fill="x", padx=20, pady=(5, 15))
        
        ctk.CTkLabel(settings_card, text="Framerate (FPS)", font=self.font_small, text_color=self.text_secondary).pack(anchor="w", padx=20)
        self.fps_var = ctk.StringVar(value="30 FPS")
        fps_dropdown = ctk.CTkOptionMenu(settings_card, variable=self.fps_var, values=["60 FPS", "30 FPS", "24 FPS", "15 FPS", "10 FPS"], command=self.on_settings_change,
                                             fg_color=self.bg_color, button_color=self.primary_color, button_hover_color=self.primary_hover,
                                             font=self.font_small, height=32, state="normal")
        fps_dropdown.pack(fill="x", padx=20, pady=(5, 20))

        # 2. Main Content Area (Right)
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        
        # Driver Warning Banner
        self.driver_warning_frame = ctk.CTkFrame(self.main_content, fg_color=self.danger_color, corner_radius=12)
        
        warning_lbl = ctk.CTkLabel(self.driver_warning_frame, text="⚠️ Missing driver", font=self.font_h2, text_color="white")
        warning_lbl.pack(side="left", padx=20, pady=15)
        
        self.driver_btn = ctk.CTkButton(self.driver_warning_frame, text="Install OpenCam (Admin)", font=self.font_body,
                                       fg_color="#9f1239", hover_color="#881337", corner_radius=8,
                                       command=self.install_driver_action)
        self.driver_btn.pack(side="right", padx=20, pady=15)

        # Preview Frame - Glass styling
        self.preview_frame = ctk.CTkFrame(self.main_content, fg_color=self.surface_color, corner_radius=20, border_width=1, border_color=self.card_border)
        self.preview_frame.pack(side="top", fill="both", expand=True)
        self.preview_frame.grid_rowconfigure(0, weight=1)
        self.preview_frame.grid_columnconfigure(0, weight=1)
        
        self.preview_label = ctk.CTkLabel(self.preview_frame, text="Starting...", font=self.font_h2, text_color=self.text_secondary)
        self.preview_label.grid(row=0, column=0)
        
        # Log Console
        self.log_console = ctk.CTkTextbox(self.main_content, height=120, fg_color=self.surface_color, border_width=1, border_color=self.card_border, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_console.pack(side="bottom", fill="x", pady=(20, 0))
        self.log_console.configure(state="disabled")
        
        # Setup stdout redirection
        class StdoutRedirector:
            def __init__(self, text_widget, is_stderr=False):
                self.text_widget = text_widget
                self.original = sys.__stderr__ if is_stderr else sys.__stdout__
            def write(self, string):
                self.text_widget.configure(state="normal")
                self.text_widget.insert("end", string)
                self.text_widget.see("end")
                self.text_widget.configure(state="disabled")
                if self.original is not None:
                    try:
                        self.original.write(string)
                    except:
                        pass
            def flush(self):
                if self.original is not None:
                    try:
                        self.original.flush()
                    except:
                        pass
        
        sys.stdout = StdoutRedirector(self.log_console, False)
        sys.stderr = StdoutRedirector(self.log_console, True)
        print("Application started.")

    def on_settings_change(self, choice=None):
        res = self.res_var.get().split('x')
        width, height = int(res[0]), int(res[1])
        fps = int(self.fps_var.get().split()[0])
        
        self.vcam_manager.set_format(width, height, fps)
        self.server_manager.send_settings_to_phone(width, height, fps)

    def update_preview(self, frame_rgb):
        import cv2
        import time
        
        # Throttle GUI preview to ~15fps (Tkinter can't handle more)
        now = time.time()
        if not hasattr(self, '_last_preview_time'):
            self._last_preview_time = 0
        if now - self._last_preview_time < 0.066:  # ~15fps
            return
        self._last_preview_time = now
        
        preview_width = self.preview_frame.winfo_width() - 4
        preview_height = self.preview_frame.winfo_height() - 4
        
        if preview_width > 10 and preview_height > 10:
            h, w, _ = frame_rgb.shape
            ratio = min(preview_width/w, preview_height/h)
            new_w, new_h = int(w*ratio), int(h*ratio)
            
            # Use INTER_AREA for high-quality downscaling
            resized = cv2.resize(frame_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
            img = Image.fromarray(resized)
            
            self.after(0, lambda: self._set_preview_image(img))

    def _set_preview_image(self, img):
        from PIL import ImageTk
        photo = ImageTk.PhotoImage(image=img)
        self.preview_label.configure(image=photo, text="")
        self.preview_label.image = photo

    def on_closing(self):
        import os
        try:
            self.vcam_manager.stop()
        except:
            pass
        try:
            self.server_manager.stop()
        except:
            pass
        try:
            self.destroy()
        except:
            pass
        # Force exit — Flask/WebSocket threads can block shutdown otherwise
        os._exit(0)
