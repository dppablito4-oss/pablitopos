import tkinter as tk
import ttkbootstrap as tb
from PIL import Image, ImageTk
import os

class SplashScreen(tb.Toplevel):
    def __init__(self, parent, logo_path=None, duration=3000):
        super().__init__(parent)
        self.parent = parent
        self.duration = duration
        self.overrideredirect(True)  # Remove window decorations
        
        # Center the splash screen
        width = 500
        height = 300
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Set background color (dark theme)
        self.configure(background='#0f172a')
        
        # Main container
        frame = tb.Frame(self, bootstyle="bg")
        frame.pack(fill="both", expand=True)
        
        # Logo
        if logo_path and os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                # Resize logo if needed
                img = img.resize((120, 120), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(img)
                lbl_logo = tb.Label(frame, image=self.logo_img, background='#0f172a')
                lbl_logo.pack(pady=(40, 20))
            except Exception:
                pass
        
        # App Title
        lbl_title = tb.Label(
            frame, 
            text="PABLITO POS", 
            font=("Segoe UI", 24, "bold"), 
            foreground="#ffffff",
            background='#0f172a'
        )
        lbl_title.pack(pady=(0, 10))
        
        # Loading text
        self.lbl_status = tb.Label(
            frame, 
            text="Iniciando sistema...", 
            font=("Segoe UI", 10), 
            foreground="#94a3b8",
            background='#0f172a'
        )
        self.lbl_status.pack(pady=(0, 20))
        
        # Progress bar
        self.progress = tb.Progressbar(
            frame, 
            orient="horizontal", 
            length=300, 
            mode="indeterminate",
            bootstyle="success-striped"
        )
        self.progress.pack(pady=(0, 20))
        self.progress.start(10)
        
        # Force update
        self.update()

    def update_status(self, text):
        self.lbl_status.config(text=text)
        self.update()

    def finish(self):
        # 1. Mostrar ventana principal primero
        try:
            self.parent.deiconify()
            self.parent.update() # Forzar renderizado
        except Exception:
            pass
            
        # 2. Detener animación y cerrar splash
        try:
            self.progress.stop()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
