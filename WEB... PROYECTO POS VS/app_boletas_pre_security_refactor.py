import os
import sys
import shutil
import subprocess
import sqlite3
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Optional, List, Callable, cast
import ttkbootstrap as tb
from ttkbootstrap.dialogs import Messagebox
import threading

from PIL import Image, ImageTk
import random
import string
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
except ImportError:
    canvas = None  # por si no está instalado reportlab

try:
    import qrcode
except ImportError:
    qrcode = None  # por si no está instalado qrcode

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.drawing.image import Image as XLImage
except ImportError:
    Workbook = None  # por si no está instalado openpyxl

# ------------------ CONFIGURACIÓN Y MÓDULOS ------------------ #
from settings import APPDATA_PATH, DB_PATH, PDF_DIR, BACKUP_DIR, IGV_PORCENTAJE
from utils import (
    build_whatsapp_message,
    configure_logging,
    create_backup,
    ensure_country_prefix,
    format_phone_display,
    generar_reporte,
    is_valid_email,
    normalize_phone_number,
)

from app_core.email_templates import generate_email_html
from app_core.logging_setup import setup_error_logging
from app_core.ui_helpers import OnboardingTour, TooltipManager


configure_logging(APPDATA_PATH)
setup_error_logging(APPDATA_PATH)
from db_connection import Database
from db_setup import init_db

# Repositorios
from repositories import (
    CompanyRepository,
    ClientRepository,
    ProductRepository,
    SaleRepository,
    SettingsRepository,
)

# Servicios
from services import (
    CommunicationService,
    CompanyService,
    ClientService,
    PdfService,
    ProductService,
    SaleService,
    SecurityService,
)
from ui import (
    CustomerDisplayManager,
    ClientUIManager,
    DashboardUIManager,
    HistoryUIManager,
    ProductUIManager,
    SalesUIHelpers,
    SalesUIManager,
)

class App(tb.Window):
    # Declare common dynamic attributes for static type checkers
    frame_dashboard: Any = None
    frame_sales: Any = None
    frame_update_info: Any = None
    frame_history: Any = None
    frame_profile: Any = None
    dashboard_manager: Any = None
    history_manager: Any = None
    logo_label: Any = None
    logo_preview_label: Any = None
    current_company_data: Optional[dict] = None
    main_logo_image: Any = None
    entry_client_search: Any = None
    entry_product_catalog_search: Any = None
    entry_search_prod: Any = None
    entry_search_cli: Any = None
    tooltip_manager: TooltipManager
    onboarding_tour: OnboardingTour

    def __init__(self):
        super().__init__(themename="cyborg")
        self.title("Sistema de Emisión de Comprobantes - PABLITO_POS")
        self.geometry("1100x650")
        self.minsize(1000, 600)
        self.set_app_icon(self)
        self.center_window(self, 1100, 650)
        
        # Inicializar UI Managers
        self.client_ui = ClientUIManager(self)
        self.product_ui = ProductUIManager(self)
        self.sales_ui = SalesUIManager(self)
        
        # Crear backup automático al iniciar
        create_backup()

        # Estilo extra
        style = tb.Style()
        style.configure("Treeview", rowheight=24)

        # Capa de datos / servicios
        db = Database(DB_PATH)
        self.company_repo = CompanyRepository(db)
        self.client_repo = ClientRepository(db)
        self.product_repo = ProductRepository(db)
        self.sale_repo = SaleRepository(db)
        self.settings_repo = SettingsRepository(db)

        self.company_service = CompanyService(self.company_repo)
        self.client_service = ClientService(self.client_repo)
        self.product_service = ProductService(self.product_repo)
        self.settings_service = SecurityService(self.settings_repo)
        self.sale_service = SaleService(self.sale_repo, self.client_repo, self.settings_service)
        self.pdf_service = PdfService(self.company_service, self.client_repo, self.sale_repo)
        self.comm_service = CommunicationService()
        self.customer_display = CustomerDisplayManager(self, self.settings_repo)

        self.current_client = None
        self.selected_product = None
        self.sale_items = []
        self.last_pdf_path = None
        self.series = "B001"
        self.entry_search_prod = None
        self.entry_search_cli = None
        self._debounce_jobs: dict[str, str] = {}
        self.loading_overlay: Optional[tb.Toplevel] = None
        self._loading_progress: Optional[tb.Progressbar] = None
        self._active_view = "dashboard"
        self._mousewheel_bound = False
        self.tooltip_manager = TooltipManager(self)
        self.onboarding_tour = OnboardingTour(self)
        
        # Iniciar en selección de perfil
        self.show_profile_selection()

        # Configurar Atajos de Teclado (Hotkeys)
        self.setup_hotkeys()

        # Compatibilidad global con rueda del ratón
        self._setup_global_mousewheel_support()

        # Verificar si se usa el PIN por defecto (1234) y forzar cambio
        if self.settings_repo.get_pin() == "1234":
            self.after(1000, self.open_force_change_pin_window)

    def setup_hotkeys(self):
        """Configura los atajos de teclado globales para la aplicación."""
        # --- NAVEGACIÓN ---
        self.bind("<Control-Key-1>", lambda e: self.switch_view("dashboard"))
        self.bind("<Control-Key-2>", lambda e: self.switch_view("sales"))
        self.bind("<Control-Key-3>", lambda e: self.switch_view("update"))
        self.bind("<Control-Key-4>", lambda e: self.switch_view("history"))
        
        # --- VENTAS ---
        self.bind("<F3>", self.focus_product_search)
        self.bind("<Control-f>", self.focus_product_search)
        self.bind("<F4>", self.focus_client_search)
        self.bind("<F5>", lambda e: self.sales_ui.reset_sale_form())
        self.bind("<F10>", lambda e: self.sales_ui.save_sale_and_generate_pdf())
        self.bind("<Control-Return>", lambda e: self.sales_ui.save_sale_and_generate_pdf())
        self.bind("<Delete>", self.delete_item_shortcut)
        
        # --- SISTEMA ---
        self.bind("<Escape>", self.on_escape)
        self.bind("<F1>", self.show_shortcuts_help)

    # --- COMPATIBILIDAD GLOBAL CON SCROLL ---
    def _setup_global_mousewheel_support(self) -> None:
        if self._mousewheel_bound:
            return
        self.bind_all("<MouseWheel>", self._on_global_mousewheel, add="+")
        self.bind_all("<Button-4>", lambda e: self._on_global_mousewheel_linux(e, -1), add="+")
        self.bind_all("<Button-5>", lambda e: self._on_global_mousewheel_linux(e, 1), add="+")
        self._mousewheel_bound = True

    def _on_global_mousewheel(self, event: tk.Event) -> str:
        target = self._locate_scroll_target(event.widget)
        if target:
            delta = -int(event.delta / 120) if event.delta else 0
            if delta:
                try:
                    target.yview_scroll(delta, "units")
                except Exception:
                    pass
        return "break"

    def _on_global_mousewheel_linux(self, event: tk.Event, direction: int) -> str:
        target = self._locate_scroll_target(event.widget)
        if target:
            try:
                target.yview_scroll(direction, "units")
            except Exception:
                pass
        return "break"

    @staticmethod
    def _locate_scroll_target(widget: tk.Misc | None) -> Any:
        current = widget
        while current is not None:
            if hasattr(current, "yview_scroll") and callable(getattr(current, "yview_scroll")):
                return current
            current = getattr(current, "master", None)
        return None

    def make_modal(
        self,
        window: tk.Toplevel,
        *,
        parent: tk.Misc | None = None,
        focus: bool = True,
        topmost: bool = False,
    ) -> None:
        if not window:
            return
        host = cast(tk.Misc, parent) if parent is not None else cast(tk.Misc, self)
        window.transient(host)  # type: ignore[arg-type]
        window.lift(host)  # type: ignore[arg-type]
        if topmost:
            try:
                window.attributes("-topmost", True)
            except Exception:
                pass
        try:
            window.grab_set()
        except Exception:
            pass
        try:
            window.bell()
        except Exception:
            pass
        if focus:
            try:
                window.focus_set()
                window.focus_force()
            except Exception:
                pass

    def create_scrollable_dialog_body(
        self,
        window: tk.Toplevel,
        *,
        padding: int | tuple[int, int] = 12,
    ) -> tb.Frame:
        container = tb.Frame(window)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0, bd=0)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tb.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)

        body = tb.Frame(canvas, padding=padding)
        window_id = canvas.create_window((0, 0), window=body, anchor="nw")

        def _on_body_configure(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event: tk.Event) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        body.bind("<Configure>", _on_body_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        return body

    # --- AYUDAS CONTEXTUALES ---
    def add_help_tooltip(
        self,
        widget: tk.Widget | None,
        text: str,
        *,
        delay: int = 1500,
        wraplength: int = 260,
    ) -> None:
        self.tooltip_manager.add(widget, text, delay=delay, wraplength=wraplength)

    def register_default_tooltips(self) -> None:
        self.tooltip_manager.register_defaults()

    # --- TUTORIAL GUIADO ---
    def maybe_start_onboarding(self) -> None:
        self.onboarding_tour.maybe_start()

    def start_onboarding_tour(self, force: bool = False) -> None:
        self.onboarding_tour.start(force=force)

    def restart_onboarding_tour(self) -> None:
        self.onboarding_tour.restart()

    # --- UTILIDADES DE TEMA ---
    @staticmethod
    def _color_luminance(color: str) -> float:
        color = color.lstrip("#")
        if len(color) == 3:
            color = "".join(ch * 2 for ch in color)
        try:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
        except ValueError:
            return 255.0
        return 0.299 * r + 0.587 * g + 0.114 * b

    def _base_background_color(self) -> str:
        style = getattr(self, "style", tb.Style())
        bg = style.lookup("TFrame", "background")
        return bg or "#ffffff"

    def is_dark_theme(self) -> bool:
        return self._color_luminance(self._base_background_color()) < 140

    def apply_chrome_styles(self) -> None:
        ttk_style = ttk.Style()
        is_dark = self.is_dark_theme()
        top_bg = "#0f172a" if is_dark else "#e2e8f0"

        ttk_style.configure("AppTopBar.TFrame", background=top_bg, borderwidth=0)
        ttk_style.configure("AppContent.TFrame", background=self._base_background_color())

        if hasattr(self, "top_bar") and self.top_bar.winfo_exists():
            self.top_bar.configure(style="AppTopBar.TFrame")
        if hasattr(self, "nav_frame") and self.nav_frame.winfo_exists():
            self.nav_frame.configure(style="AppTopBar.TFrame")
        if hasattr(self, "content_area") and self.content_area.winfo_exists():
            self.content_area.configure(style="AppContent.TFrame")

        toggle_style = "light-outline" if is_dark else "secondary-outline"
        if hasattr(self, "btn_theme_toggle") and self.btn_theme_toggle.winfo_exists():
            self.btn_theme_toggle.configure(bootstyle=toggle_style)
        if hasattr(self, "btn_back") and self.btn_back.winfo_exists():
            self.btn_back.configure(bootstyle=toggle_style)

    # --- HANDLERS DE ATAJOS ---
    def focus_product_search(self, event=None):
        """Pone el foco en el buscador de productos (Pestaña Ventas)."""
        self.switch_view("sales")
        widget = getattr(self, 'entry_search_prod', None)
        if widget:
            widget.focus_set()
            widget.select_range(0, tk.END)

    def focus_client_search(self, event=None):
        """Pone el foco en el buscador de clientes (Pestaña Ventas)."""
        self.switch_view("sales")
        widget = getattr(self, 'entry_search_cli', None)
        if widget:
            widget.focus_set()
            widget.select_range(0, tk.END)

    def delete_item_shortcut(self, event):
        """Elimina ítem si estamos en la vista de ventas."""
        # Verificar si el frame de ventas está visible
        if self.frame_sales.winfo_ismapped():
            self.sales_ui.delete_selected_item()

    def on_escape(self, event):
        """Manejo de tecla ESC."""
        # Quitar foco de cualquier widget para evitar escrituras accidentales
        self.focus_set()

    def show_shortcuts_help(self, event=None):
        """Muestra ventana de ayuda con los atajos."""
        msg = """ATAJOS DE TECLADO (MODO PRO)

NAVEGACIÓN:
[Ctrl + 1]  Dashboard
[Ctrl + 2]  Ventas / Boletas
[Ctrl + 3]  Actualizar Info
[Ctrl + 4]  Historial

VENTAS:
[F3] o [Ctrl+F]  Buscar Producto
[F4]             Buscar Cliente
[F5]             Nueva Venta (Limpiar)
[F10] o [Ctrl+Enter]  COBRAR (Guardar)
[Supr]           Eliminar Ítem
[Enter]          Agregar Producto / Confirmar

SISTEMA:
[F1]   Esta Ayuda
[ESC]  Cancelar / Quitar Foco
"""
        self.show_info("⌨ Atajos de Teclado", msg)

    def setup_uppercase_var(self, *vars):
        """Configura variables (StringVar) para que forcen mayúsculas."""
        for var in vars:
            def callback(var_name, index, mode, v=var):
                try:
                    val = v.get()
                    if val and val != val.upper():
                        v.set(val.upper())
                except Exception:
                    pass
            var.trace_add("write", callback)

    def setup_uppercase_entry(self, *entries):
        """Configura widgets Entry para que forcen mayúsculas al escribir."""
        def on_key_release(event):
            entry = event.widget
            try:
                val = entry.get()
                if val != val.upper():
                    # Guardar posición del cursor
                    idx = entry.index(tk.INSERT)
                    # Convertir y reemplazar
                    entry.delete(0, tk.END)
                    entry.insert(0, val.upper())
                    # Restaurar cursor
                    entry.icursor(idx)
            except Exception:
                pass
        
        for entry in entries:
            entry.bind("<KeyRelease>", on_key_release, add="+")

    def on_search_debounce(self, key: str, callback: Callable[[], None], delay: int = 500) -> None:
        """Retrasa búsquedas costosas hasta que el usuario deja de escribir."""
        job_id = self._debounce_jobs.get(key)
        if job_id:
            try:
                self.after_cancel(job_id)
            except Exception:
                pass

        self._debounce_jobs[key] = self.after(delay, callback)

    def show_loading(self, text: str = "Procesando...") -> None:
        """Muestra un overlay modal ligero para indicar procesos en curso."""
        self.hide_loading()

        overlay = tb.Toplevel(master=self)
        overlay.overrideredirect(True)
        overlay.transient(self)
        try:
            overlay.attributes("-topmost", True)
        except Exception:
            pass

        self.update_idletasks()
        width = max(self.winfo_width(), 300)
        height = max(self.winfo_height(), 200)
        w, h = 320, 140
        x = self.winfo_rootx() + (width // 2) - (w // 2)
        y = self.winfo_rooty() + (height // 2) - (h // 2)
        overlay.geometry(f"{w}x{h}+{x}+{y}")

        overlay.configure(cursor="arrow")

        frame = tb.Frame(overlay, padding=20, bootstyle="dark")
        frame.pack(fill="both", expand=True)

        tb.Label(frame, text=f"⏳ {text}", font=("Helvetica", 12, "bold")).pack(pady=(0, 15))
        progress = tb.Progressbar(frame, mode="indeterminate", bootstyle="info")
        progress.pack(fill="x")
        progress.start(10)

        try:
            overlay.grab_set()
        except Exception:
            pass

        self.loading_overlay = overlay
        self._loading_progress = progress
        overlay.update()

    def hide_loading(self) -> None:
        """Cierra el overlay de carga si está visible."""
        overlay = getattr(self, "loading_overlay", None)
        if overlay:
            try:
                if self._loading_progress:
                    self._loading_progress.stop()
            except Exception:
                pass
            try:
                overlay.grab_release()
            except Exception:
                pass
            try:
                overlay.destroy()
            except Exception:
                pass
        self.loading_overlay = None
        self._loading_progress = None

    def validate_numeric(self, proposed: str, max_len: Optional[int] = None) -> bool:
        """Valida que solo se ingresen dígitos y respeta un máximo opcional."""
        if proposed == "":
            return True
        if not proposed.isdigit():
            return False
        if max_len is not None and len(proposed) > max_len:
            return False
        return True

    def ask_pin(self, title="Verificar PIN", allow_recovery=True):
        """Solicita el PIN de seguridad con opción de recuperación opcional."""
        pin_var = tk.StringVar()
        
        dialog = tb.Toplevel(master=self)
        dialog.title(title)
        dialog.geometry("350x280")
        self.set_app_icon(dialog)
        self.center_window(dialog, 350, 280)
        self.make_modal(dialog)
        
        # Título
        tb.Label(dialog, text="🔐 PIN de Administrador", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        # Entry para PIN
        tb.Label(dialog, text="Ingrese su PIN:", font=("Helvetica", 10)).pack(pady=5)
        entry = tb.Entry(dialog, show="●", textvariable=pin_var, justify="center", font=("Helvetica", 14))
        entry.pack(pady=5, padx=20, fill="x", ipady=5)
        entry.focus_set()
        
        confirmed = False
        forgot_password = False
        
        def on_confirm(event=None):
            nonlocal confirmed
            confirmed = True
            dialog.destroy()
        
        def on_forgot():
            nonlocal forgot_password
            forgot_password = True
            dialog.destroy()
            
        entry.bind("<Return>", on_confirm)
        
        # Botones
        btn_frame = tb.Frame(dialog)
        btn_frame.pack(pady=15)
        
        tb.Button(btn_frame, text="✓ Confirmar", bootstyle="success", command=on_confirm, width=12).pack(side="left", padx=5)
        tb.Button(btn_frame, text="✗ Cancelar", bootstyle="secondary", command=dialog.destroy, width=12).pack(side="left", padx=5)
        
        # Botón de recuperación (Solo si está permitido)
        if allow_recovery:
            tb.Button(dialog, text="¿Olvidé mi contraseña?", bootstyle="link", command=on_forgot).pack(pady=5)
        
        self.wait_window(dialog)
        
        # Si presionó "Olvidé mi contraseña"
        if forgot_password:
            self.show_recovery_selector()
            return False
        
        # Validar PIN
        if not confirmed or not pin_var.get():
            return False
            
        if self.settings_service.verify_pin(pin_var.get()):
            return True
        else:
            self.show_error("Acceso Denegado", "PIN incorrecto.")
            return False

    def show_recovery_selector(self):
        """Paso 1: Elegir método de recuperación."""
        dialog = tb.Toplevel(master=self)
        dialog.title("Método de Recuperación")
        dialog.geometry("400x300")
        self.set_app_icon(dialog)
        self.center_window(dialog, 400, 300)
        self.make_modal(dialog)

        tb.Label(
            dialog, 
            text="¿Cómo deseas recuperar tu acceso?", 
            font=("Helvetica", 12, "bold"),
            bootstyle="primary"
        ).pack(pady=20)

        # Opción A: Código de Respaldo
        btn_backup = tb.Button(
            dialog,
            text="🔑 Usar Código de Respaldo\n(Lista de 10 códigos)",
            bootstyle="info-outline",
            command=lambda: [dialog.destroy(), self.show_backup_code_dialog()],
            width=30
        )
        btn_backup.pack(pady=10, ipady=5)

        # Opción B: Generador App
        btn_app = tb.Button(
            dialog,
            text="📱 Usar Código Autenticador (App Externa)",
            bootstyle="warning-outline",
            command=lambda: [dialog.destroy(), self.show_rescue_dialog()],
            width=30
        )
        btn_app.pack(pady=10, ipady=5)

        tb.Button(dialog, text="Cancelar", bootstyle="secondary", command=dialog.destroy).pack(pady=20)

    def show_backup_code_dialog(self):
        """Paso 2A: Ingresar código de respaldo de un solo uso."""
        dialog = tb.Toplevel(master=self)
        dialog.title("Código de Respaldo")
        dialog.geometry("400x250")
        self.set_app_icon(dialog)
        self.center_window(dialog, 400, 250)
        self.make_modal(dialog)

        tb.Label(dialog, text="Ingrese uno de sus códigos de respaldo:", font=("Helvetica", 10)).pack(pady=15)
        
        code_var = tk.StringVar()
        entry = tb.Entry(
            dialog, 
            textvariable=code_var, 
            font=("Courier New", 14, "bold"), 
            justify="center",
            width=15
        )
        entry.pack(pady=10, ipady=5)
        entry.focus_set()
        
        # Forzar mayúsculas
        self.setup_uppercase_entry(entry)

        def verify_code():
            code = code_var.get().strip()
            if not code: return
            
            if self.settings_service.consume_backup_code(code):
                dialog.destroy()
                self.show_success("Acceso Recuperado", "Código válido aceptado.\nEl código ha sido eliminado de su lista.")
                self.settings_service.force_reset_pin()
                self.open_force_change_pin_window()
            else:
                self.show_error("Error", "Código inválido o ya utilizado.")
                entry.delete(0, tk.END)

        entry.bind("<Return>", lambda e: verify_code())

        tb.Button(dialog, text="Verificar Código", bootstyle="success", command=verify_code).pack(pady=15)

    def show_rescue_dialog(self):
        """Muestra el diálogo de recuperación con desafío matemático."""
        # Generar el código de desafío
        challenge = self.settings_service.generate_challenge_code()
        
        dialog = tb.Toplevel(master=self)
        dialog.title("🔓 Recuperación de Acceso")
        dialog.geometry("450x450")
        self.set_app_icon(dialog)
        self.center_window(dialog, 450, 450)
        self.make_modal(dialog)
        
        # Título
        tb.Label(
            dialog, 
            text="Sistema de Recuperación Maestro", 
            font=("Helvetica", 14, "bold"),
            bootstyle="warning"
        ).pack(pady=15)
        
        # Instrucciones
        instructions = """Para recuperar el acceso, necesitas tu Generador de Códigos.

1. Ingresa el siguiente código en tu APP autenticadora:
2. La APP te dará una respuesta de 6 caracteres
3. Ingresa esa respuesta aquí abajo para continuar."""
        
        tb.Label(dialog, text=instructions, font=("Helvetica", 9), justify="left").pack(pady=10, padx=20)
        
        # Mostrar el código de desafío en GRANDE
        challenge_frame = tb.Frame(dialog, bootstyle="dark")
        challenge_frame.pack(pady=15, padx=20, fill="x")
        
        tb.Label(challenge_frame, text="CÓDIGO DE VERIFICADOR:", font=("Helvetica", 10)).pack()
        tb.Label(
            challenge_frame, 
            text=challenge, 
            font=("Courier New", 32, "bold"),
            bootstyle="warning"
        ).pack(pady=10)
        
        # Entry para la respuesta
        tb.Label(dialog, text="Ingresa la respuesta (6 caracteres):", font=("Helvetica", 10)).pack(pady=5)
        response_var = tk.StringVar()
        entry_response = tb.Entry(
            dialog, 
            textvariable=response_var, 
            justify="center", 
            font=("Courier New", 16, "bold"),
            width=10
        )
        entry_response.pack(pady=5, ipady=5)
        entry_response.focus_set()
        
        def validate_response():
            response = response_var.get().strip()
            
            if not response:
                self.show_warning("Atención", "Debes ingresar la respuesta.")
                return
            
            if self.settings_service.verify_master_response(challenge, response):
                dialog.destroy()
                self.show_info("✓ Verificación Exitosa", "Código correcto. Ahora debes establecer un nuevo PIN.")
                # Resetear PIN a 1234
                self.settings_service.force_reset_pin()
                # Abrir ventana para cambiar PIN obligatoriamente
                self.open_force_change_pin_window()
            else:
                self.show_error("✗ Código Incorrecto", "Digite correctamente. Verifica tu APP autenticadora.")
        
        # Botones
        btn_frame = tb.Frame(dialog)
        btn_frame.pack(pady=15)
        
        tb.Button(btn_frame, text="Verificar", bootstyle="success", command=validate_response, width=15).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Cancelar", bootstyle="secondary", command=dialog.destroy, width=15).pack(side="left", padx=5)

    def open_force_change_pin_window(self):
        """Ventana modal que obliga a cambiar el PIN después de recuperación."""
        dialog = tb.Toplevel(master=self)
        dialog.title("⚠ Cambio de PIN Obligatorio")
        dialog.geometry("400x320")  # Aumentado
        self.set_app_icon(dialog)   # Icono agregado
        self.center_window(dialog, 400, 320)
        self.make_modal(dialog)
        
        # Evitar que se cierre con X
        def do_nothing():
            self.show_warning("Atención", "Debes establecer un nuevo PIN para continuar.")
        
        dialog.protocol("WM_DELETE_WINDOW", do_nothing)
        
        # Título
        tb.Label(
            dialog, 
            text="🔒 Establecer Nuevo PIN", 
            font=("Helvetica", 14, "bold"),
            bootstyle="danger"
        ).pack(pady=15)
        
        tb.Label(
            dialog, 
            text="Por seguridad, debes establecer un nuevo PIN ahora.",
            font=("Helvetica", 9)
        ).pack(pady=5)
        
        # Form frame
        form = tb.Frame(dialog)
        form.pack(pady=20, padx=30, fill="x")
        
        tb.Label(form, text="Nuevo PIN:").grid(row=0, column=0, sticky="e", padx=5, pady=10)
        new_pin_var = tk.StringVar()
        entry_new = tb.Entry(form, show="●", textvariable=new_pin_var, justify="center", font=("Helvetica", 12))
        entry_new.grid(row=0, column=1, sticky="ew", padx=5, pady=10, ipady=3)
        entry_new.focus_set()
        
        tb.Label(form, text="Confirmar PIN:").grid(row=1, column=0, sticky="e", padx=5, pady=10)
        confirm_pin_var = tk.StringVar()
        entry_confirm = tb.Entry(form, show="●", textvariable=confirm_pin_var, justify="center", font=("Helvetica", 12))
        entry_confirm.grid(row=1, column=1, sticky="ew", padx=5, pady=10, ipady=3)
        
        form.columnconfigure(1, weight=1)
        
        def save_new_pin():
            new_pin = new_pin_var.get().strip()
            confirm_pin = confirm_pin_var.get().strip()
            
            if not new_pin or not confirm_pin:
                self.show_warning("Atención", "Ambos campos son obligatorios.")
                return
            
            if len(new_pin) < 4:
                self.show_warning("Atención", "El PIN debe tener al menos 4 dígitos.")
                return
            
            if new_pin != confirm_pin:
                self.show_error("Error", "Los PINs no coinciden.")
                return
            
            # Guardar el nuevo PIN
            self.settings_service.repo.set_pin(new_pin)
            dialog.destroy()
            self.show_info("✓ PIN Actualizado", f"Tu nuevo PIN ha sido establecido correctamente.\n\nRecuérdalo bien.")
        
        tb.Button(dialog, text="Guardar PIN", bootstyle="success", command=save_new_pin, width=20).pack(pady=15)

    # --- VENTANAS EMERGENTES PERSONALIZADAS ---
    
    def show_custom_message(self, title, message, icon_name="info", bootstyle="info", buttons=None):
        """
        Muestra un mensaje personalizado con el estilo de la app y el logo.
        
        Args:
            title (str): Título de la ventana
            message (str): Mensaje a mostrar
            icon_name (str): Nombre del icono (info, warning, error, question)
            bootstyle (str): Estilo de bootstrap (info, warning, danger, success, primary)
            buttons (list): Lista de diccionarios [{'text': 'OK', 'command': func, 'style': 'primary'}]
                            Si es None, muestra solo un botón OK.
        """
        dialog = tb.Toplevel(master=self)
        dialog.title(title)
        dialog.geometry("420x250")
        self.center_window(dialog, 420, 250)
        self.make_modal(dialog)
        
        # Intentar poner el icono de la app
        try:
            self.set_app_icon(dialog)
        except:
            pass
            
        # Contenedor principal
        main_frame = tb.Frame(dialog, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Header con Icono y Título
        header_frame = tb.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 15))
        
        # Icono (emoji por ahora, podría ser imagen)
        icons = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "question": "❓",
            "success": "✅"
        }
        icon_char = icons.get(icon_name, "ℹ️")
        
        # Título grande con color
        tb.Label(
            header_frame, 
            text=f"{icon_char}  {title}", 
            font=("Helvetica", 14, "bold"), 
            bootstyle=bootstyle
        ).pack(side="left")
        
        # Mensaje
        msg_frame = tb.Frame(main_frame)
        msg_frame.pack(fill="both", expand=True)
        
        tb.Label(
            msg_frame, 
            text=message, 
            font=("Helvetica", 10), 
            wraplength=380,
            justify="left"
        ).pack(pady=10, anchor="w")
        
        # Botones
        btn_frame = tb.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(15, 0))
        
        result = None
        
        if buttons is None:
            # Botón OK por defecto
            def on_ok():
                dialog.destroy()
            
            tb.Button(
                btn_frame, 
                text="Aceptar", 
                bootstyle=bootstyle, 
                command=on_ok,
                width=15
            ).pack(side="right")
            
            # Bind Enter key
            dialog.bind("<Return>", lambda e: on_ok())
            
        else:
            # Botones personalizados
            for btn in buttons:
                # Wrapper para capturar el comando y cerrar
                cmd = btn.get('command', lambda: None)
                
                def make_cmd(c):
                    def wrapper():
                        c()
                        dialog.destroy()
                    return wrapper
                
                tb.Button(
                    btn_frame,
                    text=btn.get('text', 'Button'),
                    bootstyle=btn.get('style', 'secondary'),
                    command=make_cmd(cmd),
                    width=12
                ).pack(side="right", padx=5)

        self.wait_window(dialog)
        return result

    def show_info(self, title, message):
        self.show_custom_message(title, message, "info", "info")

    def show_warning(self, title, message):
        self.show_custom_message(title, message, "warning", "warning")

    def show_error(self, title, message):
        self.show_custom_message(title, message, "error", "danger")

    def show_toast(self, title, message, level="success", duration=3200):
        """Muestra una notificación sutil en la parte superior de la ventana."""
        is_dark = self.is_dark_theme()
        success_bg = "#1DB954" if is_dark else "#2ECC71"
        palette = {
            "success": (success_bg, "#ffffff"),
            "info": (success_bg, "#ffffff"),  # usamos verde también para notificaciones informativas
            "warning": ("#ffc107", "#212529"),
            "error": ("#dc3545", "#ffffff"),
        }

        bg_color, fg_color = palette.get(level, (success_bg, "#ffffff"))

        try:
            self.update_idletasks()
            toast = tk.Toplevel(self)
            toast.overrideredirect(True)
            toast.attributes("-topmost", True)
            toast.configure(bg=bg_color, highlightthickness=0)

            container = tk.Frame(toast, bg=bg_color, padx=16, pady=12, highlightthickness=0, bd=0)
            container.pack(fill="both", expand=True)

            labels: list[tk.Label] = []
            if title:
                lbl_title = tk.Label(
                    container,
                    text=title,
                    font=("Segoe UI", 10, "bold"),
                    bg=bg_color,
                    fg=fg_color,
                    anchor="w",
                )
                lbl_title.pack(anchor="w")
                labels.append(lbl_title)
            if message:
                lbl_msg = tk.Label(
                    container,
                    text=message,
                    font=("Segoe UI", 9),
                    bg=bg_color,
                    fg=fg_color,
                    justify="left",
                    anchor="w",
                )
                lbl_msg.pack(anchor="w", pady=(4, 0))
                labels.append(lbl_msg)

            def apply_colors():
                try:
                    toast.configure(bg=bg_color, highlightthickness=0)
                    container.configure(bg=bg_color)
                    for lbl in labels:
                        lbl.configure(bg=bg_color, fg=fg_color)
                except tk.TclError:
                    pass

            apply_colors()
            toast.after_idle(apply_colors)

            toast.update_idletasks()

            parent_x = self.winfo_rootx()
            parent_y = self.winfo_rooty()
            parent_w = max(self.winfo_width(), 1)

            width = toast.winfo_width()
            height = toast.winfo_height()

            x = parent_x + parent_w - width - 24
            y = parent_y + 20

            toast.geometry(f"{width}x{height}+{int(x)}+{int(y)}")

            def close_toast(*_):
                if toast.winfo_exists():
                    toast.destroy()

            toast.after(duration, close_toast)
            toast.bind("<Button-1>", close_toast)
        except Exception:
            self.show_custom_message(title, message, level, level)

    def show_success(self, title, message, use_toast=False, duration=3200):
        if use_toast:
            self.show_toast(title, message, level="success", duration=duration)
        else:
            self.show_custom_message(title, message, "success", "success")

    def show_question(self, title, message):
        """
        Muestra diálogo de confirmación Sí/No.
        Retorna True si el usuario elige Sí, False si elige No.
        """
        result = False
        
        def on_yes():
            nonlocal result
            result = True
        
        def on_no():
            nonlocal result
            result = False
            
        buttons = [
            {'text': 'No', 'command': on_no, 'style': 'secondary'},
            {'text': 'Sí', 'command': on_yes, 'style': 'primary'}
        ]
        
        self.show_custom_message(title, message, "question", "primary", buttons)
        return result

    def show_profile_selection(self):
        """Muestra la pantalla de selección de perfiles (Grid de Tarjetas) - Estilo Cyberpunk."""
        # Limpiar ventana
        for widget in self.winfo_children():
            widget.destroy()
            
        self.title("Seleccionar Perfil - PABLITO_POS")
        
        # Fondo principal (asegurar que ocupe todo)
        bg_frame = tb.Frame(self)
        bg_frame.pack(fill="both", expand=True)
        
        # Botón Config PIN / Seguridad (Top Right)
        btn_sec = tb.Button(
            bg_frame, 
            text="🛡 Seguridad", 
            bootstyle="secondary-outline", 
            command=self.open_security_dashboard
        )
        btn_sec.place(relx=0.98, rely=0.02, anchor="ne")

        # Botón Config Correo
        btn_email = tb.Button(
            bg_frame,
            text="📧 Config Correo",
            bootstyle="secondary-outline",
            command=self.open_email_config_dialog
        )
        btn_email.place(relx=0.88, rely=0.02, anchor="ne")
        self.add_help_tooltip(btn_email, "Configura el envío de comprobantes por correo electrónico.")
        
        # Contenedor Central (Centrado en pantalla)
        center_container = tb.Frame(bg_frame)
        center_container.place(relx=0.5, rely=0.5, anchor="center")

        # Título Cyberpunk con efecto RGB
        self.title_label = tb.Label(
            center_container, 
            text=">> PABLITO_POS SYSTEM <<", 
            font=("Segoe UI", 28, "bold"), 
            bootstyle="danger"
        )
        self.title_label.pack(pady=(0, 10))
        
        # Iniciar animación RGB
        self.animate_rgb(self.title_label)
        
        # Subtítulo
        tb.Label(
            center_container,
            text="TOQUE EL PERFIL PARA COMENZAR",
            font=("Segoe UI", 12, "bold"),
            bootstyle="light"
        ).pack(pady=(0, 40))
        
        # Grid de Tarjetas
        cards_frame = tb.Frame(center_container)
        cards_frame.pack()

        # Obtener perfiles
        profiles = self.company_service.get_all_profiles()
        if not profiles:
            self.company_service.create_profile("Mi Empresa Default", "20000000001")
            profiles = self.company_service.get_all_profiles()
            
        # Grid de tarjetas (Máximo 5 columnas)
        columns = 5
        for i, p in enumerate(profiles):
            row = i // columns
            col = i % columns
            self.create_profile_card(cards_frame, p, row, col)
            
        # Botones de Backup (Bottom Center)
        backup_frame = tb.Frame(bg_frame)
        backup_frame.place(relx=0.5, rely=0.95, anchor="s")
        
        btn_backup = tb.Button(
            backup_frame,
            text="💾 Crear Backup",
            bootstyle="info",
            command=self.create_manual_backup,
            width=20
        )
        btn_backup.pack(side="left", padx=10)
        self.add_help_tooltip(btn_backup, "Genera una copia de seguridad inmediata de la base de datos.")

        btn_restore = tb.Button(
            backup_frame,
            text="📥 Restaurar Backup",
            bootstyle="warning",
            command=self.restore_backup,
            width=20
        )
        btn_restore.pack(side="left", padx=10)
        self.add_help_tooltip(btn_restore, "Restaurar un respaldo previo desde un archivo .zip.")

    def animate_rgb(self, label, step=0):
        """Efecto RGB para el título."""
        # Colores Neón: Rojo, Amarillo, Verde, Cian, Azul, Magenta
        colors = ["#ff0000", "#ffff00", "#00ff00", "#00ffff", "#0000ff", "#ff00ff"]
        
        # Verificar si el widget aún existe
        try:
            if not label.winfo_exists():
                return
        except:
            return
            
        # Cambiar color
        current_color = colors[step % len(colors)]
        try:
            label.configure(foreground=current_color)
        except:
            pass
            
        # Programar siguiente cambio (velocidad: 600 ms)
        self.after(600, lambda: self.animate_rgb(label, step + 1))

    def change_pin_dialog(self):
        """Diálogo seguro para cambiar el PIN de administrador."""
        # Diálogo para cambiar PIN
        dialog = tb.Toplevel(master=self)
        dialog.title("Cambiar PIN de Seguridad")
        dialog.geometry("400x350")
        self.set_app_icon(dialog)
        self.center_window(dialog, 400, 350)
        self.make_modal(dialog)

        tb.Label(dialog, text="🔐 Actualizar PIN de Seguridad", font=("Helvetica", 12, "bold"), bootstyle="primary").pack(pady=15)

        frame = tb.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)

        # 1. PIN Actual
        tb.Label(frame, text="PIN Actual:").pack(anchor="w", pady=(5, 0))
        entry_current = tb.Entry(frame, show="*", justify="center")
        entry_current.pack(fill="x", pady=(0, 10))

        # 2. Nuevo PIN
        tb.Label(frame, text="Nuevo PIN (mín 4 dígitos):").pack(anchor="w", pady=(5, 0))
        entry_new = tb.Entry(frame, show="*", justify="center")
        entry_new.pack(fill="x", pady=(0, 10))

        # 3. Confirmar Nuevo PIN
        tb.Label(frame, text="Confirmar Nuevo PIN:").pack(anchor="w", pady=(5, 0))
        entry_confirm = tb.Entry(frame, show="*", justify="center")
        entry_confirm.pack(fill="x", pady=(0, 10))

        entry_current.focus_set()

        def save_new_pin():
            current_pin = entry_current.get().strip()
            new_pin = entry_new.get().strip()
            confirm_pin = entry_confirm.get().strip()

            # Validaciones
            real_current_pin = self.settings_repo.get_pin()
            
            if current_pin != real_current_pin:
                self.show_error("Error", "El PIN actual es incorrecto.")
                return

            if len(new_pin) < 4:
                self.show_warning("Atención", "El nuevo PIN debe tener al menos 4 dígitos.")
                return

            if new_pin != confirm_pin:
                self.show_error("Error", "Los nuevos PIN no coinciden.")
                return

            if new_pin == "1234":
                self.show_warning("Seguridad", "No puede usar '1234' como PIN. Elija uno más seguro.")
                return

            # Guardar
            try:
                self.settings_service.change_pin(current_pin, new_pin)
                self.show_success("Éxito", "PIN actualizado correctamente.\nNo olvide su nuevo PIN.")
                dialog.destroy()
            except Exception as e:
                self.show_error("Error", str(e))

        tb.Button(dialog, text="Guardar Nuevo PIN", bootstyle="success", command=save_new_pin, width=20).pack(pady=10)
        
        dialog.bind("<Return>", lambda e: save_new_pin())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        
        self.wait_window(dialog)

    def open_security_dashboard(self):
        """Panel de control de seguridad y códigos de respaldo."""
        if not self.ask_pin("Acceso a Seguridad", allow_recovery=False):
            return

        win = tb.Toplevel(master=self)
        win.title("Gestión de Seguridad")
        win.geometry("600x500")
        self.set_app_icon(win)
        self.center_window(win, 600, 500)
        self.make_modal(win)

        body = self.create_scrollable_dialog_body(win, padding=16)

        # Header
        tb.Label(
            body, 
            text="🛡 Códigos de Recuperación de Emergencia", 
            font=("Helvetica", 16, "bold"),
            bootstyle="danger"
        ).pack(pady=(20, 10))

        tb.Label(
            body,
            text="Estos códigos permiten acceder si olvida su PIN.\nGuárdelos en un lugar seguro (impresos o en un archivo).",
            justify="center",
            bootstyle="secondary"
        ).pack(pady=(0, 20))

        # Área de texto para códigos
        frame_codes = tb.Frame(body, padding=10, bootstyle="dark")
        frame_codes.pack(fill="both", expand=True, padx=20, pady=10)

        from tkinter.scrolledtext import ScrolledText
        txt_codes = ScrolledText(frame_codes, height=10, font=("Consolas", 12), state="disabled")
        txt_codes.pack(fill="both", expand=True)

        def refresh_codes():
            codes = self.settings_service.get_backup_codes()
            txt_codes.config(state="normal")
            txt_codes.delete("1.0", tk.END)
            if codes:
                for code in codes:
                    txt_codes.insert(tk.END, f"{code}\n")
            else:
                txt_codes.insert(tk.END, "No hay códigos activos.\nGenere nuevos códigos para asegurar su acceso.")
            txt_codes.config(state="disabled")

        refresh_codes()

        # Botones de Acción
        btn_frame = tb.Frame(body, padding=20)
        btn_frame.pack(fill="x")

        def generate_new():
            if self.show_question("¿Generar nuevos códigos?\nEsto invalidará los códigos anteriores.", "Confirmar"):
                self.settings_service.generate_new_backup_codes()
                refresh_codes()
                self.show_success("Éxito", "Nuevos códigos generados.")

        def save_to_file():
            codes = self.settings_service.get_backup_codes()
            if not codes:
                self.show_warning("Atención", "No hay códigos para guardar.")
                return
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt")],
                title="Guardar Códigos de Recuperación",
                initialfile="PABLITO_POS_BACKUP_CODES.txt"
            )
            if filename:
                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write("=========================================\n")
                        f.write(" CÓDIGOS DE RECUPERACIÓN - PABLITO POS\n")
                        f.write("=========================================\n")
                        f.write("Guarde este archivo en un lugar seguro.\n")
                        f.write("Cada código sirve para UN solo uso.\n\n")
                        for code in codes:
                            f.write(f"[ ] {code}\n")
                        f.write("\nGenerado el: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    self.show_success("Guardado", f"Códigos guardados en:\n{filename}")
                except Exception as e:
                    self.show_error("Error", f"No se pudo guardar el archivo:\n{e}")

        tb.Button(
            btn_frame, 
            text="🔄 Generar Nuevos", 
            command=self.change_pin_dialog
        ).pack(side="right", padx=5)

    def create_profile_card(self, parent, profile, row, col):
        """Crea una tarjeta visual para un perfil - Estilo Cyberpunk."""
        p_id = profile["id"]
        name = profile["name"]
        logo_path = profile["logo_path"]
        
        # Frame para borde neón (simulado con padding y background)
        # Usamos un frame contenedor para el borde
        border_frame = tb.Frame(parent, bootstyle="info", padding=2) 
        border_frame.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")
        
        # Tarjeta interior (fondo oscuro)
        card = tb.Frame(border_frame, bootstyle="dark", padding=15)
        card.pack(fill="both", expand=True)
        
        # Efecto Hover: Cambiar color del borde
        def on_enter(e):
            border_frame.configure(bootstyle="success") # Verde al pasar mouse
            
        def on_leave(e):
            border_frame.configure(bootstyle="info") # Azul/Cian normal
            
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        
        # Logo Preview
        if logo_path and os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                img.thumbnail((120, 120)) # Un poco más grande
                photo = ImageTk.PhotoImage(img)
                lbl_img = tb.Label(card, image=photo, bootstyle="inverse-dark")
                setattr(lbl_img, "_photo_ref", photo)
                lbl_img.pack(pady=(0, 15))
                # Bind hover al logo también
                lbl_img.bind("<Enter>", on_enter)
                lbl_img.bind("<Leave>", on_leave)
            except:
                tb.Label(card, text="[NO LOGO]", font=("Courier New", 12, "bold"), bootstyle="secondary").pack(pady=(20, 35))
        else:
            tb.Label(card, text="[NO LOGO]", font=("Courier New", 12, "bold"), bootstyle="secondary").pack(pady=(20, 35))
            
        # Nombre (Estilo etiqueta digital)
        name_lbl = tb.Label(
            card, 
            text=name.upper(), 
            font=("Segoe UI", 11, "bold"), 
            wraplength=180, 
            justify="center",
            bootstyle="inverse-dark"
        )
        name_lbl.pack(pady=(0, 15))
        name_lbl.bind("<Enter>", on_enter)
        name_lbl.bind("<Leave>", on_leave)
        
        # Botones
        btn_frame = tb.Frame(card, bootstyle="dark")
        btn_frame.pack(fill="x")
        
        # Botón Entrar (Grande, estilo neón)
        tb.Button(
            btn_frame, 
            text="ENTRAR", 
            bootstyle="primary", # Azul neón
            command=lambda: self.select_profile(p_id),
            width=10
        ).pack(side="top", fill="x", pady=(0, 10))
        
        # Botones de acción (Iconos pequeños abajo)
        action_frame = tb.Frame(btn_frame, bootstyle="dark")
        action_frame.pack(side="top", fill="x")
        action_frame.columnconfigure((0, 1), weight=1)
        
        tb.Button(
            action_frame, 
            text="⚙", 
            bootstyle="warning-outline", 
            width=4, 
            command=lambda: self.edit_profile_dialog(p_id)
        ).grid(row=0, column=0, padx=2, sticky="ew")
        
        tb.Button(
            action_frame, 
            text="🗑", 
            bootstyle="danger-outline", 
            width=4, 
            command=lambda: self.delete_profile_action(p_id)
        ).grid(row=0, column=1, padx=2, sticky="ew")

    def delete_profile_action(self, profile_id):
        if not self.ask_pin("Eliminar Perfil"): return
        
        confirm = self.show_question("¿Está seguro de eliminar este perfil?\nSe ocultará de la lista pero se mantendrá el historial.", "Confirmar Eliminación")
        if confirm == "Yes":
            self.company_service.delete_profile(profile_id)
            self.show_profile_selection()

    def select_profile(self, profile_id):
        """Carga el perfil seleccionado y construye la UI principal."""
        self.current_company_id = profile_id
        self.current_company_data = self.company_service.get_profile(profile_id)
        
        # Limpiar ventana
        for widget in self.winfo_children():
            widget.destroy()
            
        self.title(f"Sistema POS - {(self.current_company_data or {}).get('name', 'Empresa')}")
        self.build_main_ui()

    def build_main_ui(self):
        """Construye la interfaz principal de la aplicación con Navegación por Botones."""
        # 1. Barra Superior (Header + Navegación)
        self.top_bar = tb.Frame(self)
        self.top_bar.pack(fill="x", side="top")
        
        # Contenedor de botones de navegación (Centrado o Izquierda)
        self.nav_frame = tb.Frame(self.top_bar)
        self.nav_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.nav_buttons: list[tb.Button] = []

        # Estilo base uniforme (Elegante y sobrio)
        base_style = "secondary-outline" if self.is_dark_theme() else "primary-outline"
        
        self.btn_nav_dashboard = tb.Button(self.nav_frame, text="Dashboard", bootstyle=base_style, command=lambda: self.switch_view("dashboard"))
        self.btn_nav_dashboard.pack(side="left", padx=2)
        self.nav_buttons.append(self.btn_nav_dashboard)
        
        self.btn_nav_sales = tb.Button(self.nav_frame, text="Ventas", bootstyle=base_style, command=lambda: self.switch_view("sales"))
        self.btn_nav_sales.pack(side="left", padx=2)
        self.nav_buttons.append(self.btn_nav_sales)
        
        self.btn_nav_update = tb.Button(self.nav_frame, text="Actualizar Info", bootstyle=base_style, command=lambda: self.switch_view("update"))
        self.btn_nav_update.pack(side="left", padx=2)
        self.nav_buttons.append(self.btn_nav_update)
        
        self.btn_nav_history = tb.Button(self.nav_frame, text="Historial de comprobantes", bootstyle=base_style, command=lambda: self.switch_view("history"))
        self.btn_nav_history.pack(side="left", padx=2)
        self.nav_buttons.append(self.btn_nav_history)

        self.btn_verify = tb.Button(self.nav_frame, text="🔍 Verificar Comprobante", bootstyle="danger-outline", command=self.open_verify_window)
        self.btn_verify.pack(side="left", padx=2)
        
        self.btn_export = tb.Button(self.nav_frame, text="📊 Exportar (informe)", bootstyle="info-outline", command=self.open_export_dialog)
        self.btn_export.pack(side="left", padx=2)

        # Botón Cambiar Perfil (Derecha)
        current_theme = self.style.theme_use()
        toggle_icon = "☀️" if current_theme == "cyborg" else "🌙"

        self.btn_guided_tour = tb.Button(
            self.top_bar,
            text="Guía",
            bootstyle="info-outline",
            command=self.restart_onboarding_tour,
            width=6,
        )
        self.btn_guided_tour.pack(side="right", padx=5, pady=10)

        self.btn_theme_toggle = tb.Button(
            self.top_bar,
            text=toggle_icon,
            bootstyle="light-outline",
            command=self.toggle_theme,
            width=4
        )
        self.btn_theme_toggle.pack(side="right", padx=5, pady=10)

        self.btn_back = tb.Button(self.top_bar, text="VER PERFIL", bootstyle="light-outline", command=self.show_profile_selection)
        self.btn_back.pack(side="right", padx=10, pady=10)
        
        # 2. Área de Contenido Principal
        self.content_area = tb.Frame(self, style="AppContent.TFrame")
        self.content_area.pack(fill="both", expand=True, padx=10, pady=10)

        # Crear los frames de las vistas (pero no empaquetarlos aún)
        self.frame_dashboard = tb.Frame(self.content_area)
        self.frame_sales = tb.Frame(self.content_area)
        self.frame_update_info = tb.Frame(self.content_area)
        self.frame_history = tb.Frame(self.content_area)

        # Construir las UIs internas
        self.dashboard_manager = DashboardUIManager(self, self.frame_dashboard, self.sale_service)
        self.dashboard_manager.build_ui()
        self.sales_ui.build_sales_ui()
        self.build_update_info_ui()
        self.history_manager = HistoryUIManager(self, self.frame_history)
        self.history_manager.build_ui()
        
        self.refresh_search_shortcut_targets()
        self.load_main_logo()

        self.apply_chrome_styles()
        self.register_default_tooltips()
        self.after(1200, self.maybe_start_onboarding)
        
        # Mostrar vista por defecto
        self.switch_view("dashboard")

        # Map legacy attribute names expected by hotkeys
        if hasattr(self, "entry_product_catalog_search"):
            self.entry_search_prod = self.entry_product_catalog_search
        if hasattr(self, "entry_client_search"):
            self.entry_search_cli = self.entry_client_search

    def switch_view(self, view_name):
        """Cambia la vista visible en el área de contenido."""
        self._active_view = view_name
        # Ocultar todas las vistas
        for frame in [self.frame_dashboard, self.frame_sales, self.frame_update_info, self.frame_history]:
            frame.pack_forget()
            
        # Mostrar la seleccionada
        if view_name == "dashboard":
            self.frame_dashboard.pack(fill="both", expand=True)
            if getattr(self, "dashboard_manager", None):
                self.dashboard_manager.refresh_dashboard()
        elif view_name == "sales":
            self.frame_sales.pack(fill="both", expand=True)
        elif view_name == "update":
            self.frame_update_info.pack(fill="both", expand=True)
        elif view_name == "history":
            self.frame_history.pack(fill="both", expand=True)
            if getattr(self, "history_manager", None):
                self.history_manager.refresh_tree()
            
        # Actualizar estilos de botones (RGB Activo)
        self.update_nav_buttons(view_name)

    def toggle_theme(self):
        """Alterna entre los temas claro y oscuro."""
        try:
            style = self.style
        except AttributeError:
            style = tb.Style()

        current = style.theme_use()
        new_theme = "cosmo" if current == "cyborg" else "cyborg"
        style.theme_use(new_theme)

        if hasattr(self, "btn_theme_toggle"):
            icon = "☀️" if new_theme == "cyborg" else "🌙"
            self.btn_theme_toggle.configure(text=icon)

        self.apply_chrome_styles()

        if getattr(self, "dashboard_manager", None):
            self.dashboard_manager.on_theme_changed()

        if getattr(self, "history_manager", None):
            self.history_manager.refresh_tree()

        active = getattr(self, "_active_view", "dashboard")
        self.update_nav_buttons(active)

    def update_nav_buttons(self, active_view):
        """Actualiza el estilo de los botones y activa el efecto RGB en el seleccionado."""
        # 1. Resetear todos a estilo base
        base_style = "secondary-outline" if self.is_dark_theme() else "primary-outline"
        buttons = {
            "dashboard": self.btn_nav_dashboard,
            "sales": self.btn_nav_sales,
            "update": self.btn_nav_update,
            "history": self.btn_nav_history
        }
        
        # Detener animación anterior si existe
        self.stop_rgb_animation()
        
        for view, btn in buttons.items():
            if view == active_view:
                # Este es el activo -> Iniciar RGB
                self.animate_active_button(btn)
            else:
                # Inactivo -> Estilo base
                btn.configure(bootstyle=base_style)

    def stop_rgb_animation(self):
        """Detiene cualquier animación RGB en curso en los botones."""
        if hasattr(self, '_rgb_job') and self._rgb_job:
            self.after_cancel(self._rgb_job)
            self._rgb_job = None

    def animate_active_button(self, btn, step=0):
        """Anima el color del botón activo (Efecto RGB Gamer)."""
        # Ciclo de colores neón: Primary -> Info -> Success -> Warning -> Danger -> Secondary
        colors = ["primary", "info", "success", "warning", "danger"]
        
        # Calcular color actual
        current_color = colors[step % len(colors)]
        
        # Aplicar estilo (relleno sólido para destacar)
        try:
            btn.configure(bootstyle=current_color)
        except:
            return # Si el botón ya no existe
            
        # Programar siguiente cambio (velocidad: 500ms)
        self._rgb_job = self.after(500, lambda: self.animate_active_button(btn, step + 1))

    def refresh_search_shortcut_targets(self):
        """Actualiza las referencias usadas por los atajos de búsqueda rápidos."""
        self.entry_search_prod = getattr(self, "entry_product_catalog_search", None)
        self.entry_search_cli = getattr(self, "entry_client_search", None)

    

    def edit_profile_dialog(self, profile_id):
        """Abre un diálogo para editar el perfil (Logo, Datos)."""
        if not self.ask_pin("Editar Perfil"): return

        profile = self.company_service.get_profile(profile_id)
        if not profile: return
        
        win = tb.Toplevel(master=self)
        win.title("Editar Perfil")
        win.geometry("580x620")
        self.set_app_icon(win)
        self.center_window(win, 580, 620)
        self.make_modal(win)
        body = self.create_scrollable_dialog_body(win, padding=18)

        lf = tb.Labelframe(body, text="Datos de la Empresa", padding=15)
        lf.pack(fill="both", expand=True)
        lf.columnconfigure(1, weight=1)
        
        # Campos
        entries = {}
        fields = [
            ("Nombre:", "name"),
            ("RUC:", "ruc"),
            ("Dirección:", "address"),
            ("Teléfono:", "phone"),
            ("Email:", "email"),
            ("Web:", "website"),
            ("Pie de página:", "footer_message")
        ]
        
        for i, (label, key) in enumerate(fields):
            tb.Label(lf, text=label).grid(row=i, column=0, sticky="e", padx=5, pady=5)
            entry = tb.Entry(lf)
            entry.grid(row=i, column=1, sticky="we", padx=5, pady=5)
            entry.insert(0, profile.get(key, ""))
            entries[key] = entry
            
        # Forzar mayúsculas
        self.setup_uppercase_entry(*entries.values())
            
        # Logo
        row_logo = len(fields)
        tb.Label(lf, text="Logo:").grid(row=row_logo, column=0, sticky="ne", padx=5, pady=5)
        logo_path_var = tk.StringVar(value=profile.get("logo_path") or "")
        
        def select_logo():
            path = filedialog.askopenfilename(
                title="Seleccionar logo",
                filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.bmp"), ("Todos", "*.*")]
            )
            if path:
                logo_path_var.set(path)
        
        btn_logo = tb.Button(lf, text="Seleccionar logo", bootstyle="secondary-outline", command=select_logo)
        btn_logo.grid(row=row_logo, column=1, sticky="w", padx=5, pady=5)
        
        yape_qr_path_var = tk.StringVar(value=profile.get("yape_qr_path") or "")

        def refresh_modal_qr_preview(label_holder, image_store):
            path = yape_qr_path_var.get()
            if not path or not os.path.exists(path):
                label_holder.configure(image="", text="(Sin QR configurado)")
                image_store["image"] = None
                return
            try:
                img = Image.open(path)
                img = img.resize((140, 140), Image.Resampling.LANCZOS)
                image_store["image"] = ImageTk.PhotoImage(img)
                label_holder.configure(image=image_store["image"], text="")
            except Exception as exc:
                image_store["image"] = None
                label_holder.configure(image="", text="(Error al cargar QR)")
                self.show_error("Error", f"No se pudo cargar el QR: {exc}")

        # Checkbox IGV 
        row_igv = row_logo + 1
        include_igv_var = tk.BooleanVar(value=profile.get("include_igv", True))
        chk_igv = tb.Checkbutton(
            lf,
            text="Cobrar IGV (18%)",
            variable=include_igv_var,
            bootstyle="success-round-toggle"
        )
        chk_igv.grid(row=row_igv, column=0, columnspan=2, sticky="w", padx=5, pady=10)
        
        # Configuración de cobro (QR y pantallas)
        payment_lf = tb.Labelframe(lf, text="Cobro con Yape", padding=12, bootstyle="warning")
        payment_lf.grid(row=row_igv + 1, column=0, columnspan=2, sticky="nsew", padx=0, pady=(0, 10))
        payment_lf.columnconfigure(1, weight=1)

        tb.Label(payment_lf, text="QR de Yape:").grid(row=0, column=0, sticky="ne", padx=5, pady=5)
        modal_qr_frame = tb.Frame(payment_lf)
        modal_qr_frame.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        def select_yape_qr():
            path = filedialog.askopenfilename(
                title="Seleccionar QR de Yape",
                filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.bmp"), ("Todos", "*.*")]
            )
            if not path:
                return
            yape_qr_path_var.set(path)
            refresh_modal_qr_preview(modal_qr_preview, modal_qr_store)

        tb.Button(
            modal_qr_frame,
            text="Subir QR",
            bootstyle="secondary-outline",
            command=select_yape_qr
        ).pack(anchor="w", pady=(0, 6))

        modal_qr_store = {"image": None}
        modal_qr_preview = tb.Label(modal_qr_frame, text="(Sin QR configurado)")
        modal_qr_preview.pack(anchor="w")
        refresh_modal_qr_preview(modal_qr_preview, modal_qr_store)

        tb.Label(payment_lf, text="Pantalla del cliente:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        screen_options = self.customer_display.get_monitor_options() if hasattr(self, "customer_display") else []
        if not screen_options:
            screen_options = ["Pantalla 0 (Principal)"]

        try:
            saved_screen = int(self.settings_repo.get_setting("customer_screen_index", "0"))
        except (TypeError, ValueError):
            saved_screen = 0

        modal_screen_combo = tb.Combobox(payment_lf, values=screen_options, state="readonly")
        modal_screen_combo.grid(row=1, column=1, sticky="we", padx=5, pady=5)
        if 0 <= saved_screen < len(screen_options):
            modal_screen_combo.current(saved_screen)
        else:
            modal_screen_combo.current(0)

        def test_modal_screen():
            idx = modal_screen_combo.current() if modal_screen_combo.current() != -1 else 0
            if not self.customer_display.show_test_screen(idx):
                self.show_warning("Pantalla", "No se pudo abrir la vista previa en la pantalla seleccionada.")

        tb.Button(
            payment_lf,
            text="Probar Pantalla",
            bootstyle="warning-outline",
            command=test_modal_screen
        ).grid(row=2, column=1, sticky="w", padx=5, pady=(5, 0))

        # Botón Guardar
        row_save = row_igv + 2
        def save_profile():
            try:
                selected_screen = modal_screen_combo.current() if modal_screen_combo.current() != -1 else 0
                self.company_service.update_profile(
                    profile_id,
                    entries["name"].get().strip(),
                    entries["ruc"].get().strip(),
                    entries["address"].get().strip(),
                    entries["phone"].get().strip(),
                    entries["email"].get().strip(),
                    entries["website"].get().strip(),
                    entries["footer_message"].get().strip(),
                    logo_path_var.get() or None,
                    "#1f77b4",  # brand_color por defecto
                    1 if include_igv_var.get() else 0,
                    yape_qr_path_var.get() or None
                )
                self.settings_repo.set_setting("customer_screen_index", str(selected_screen))
                self.show_info("Éxito", "Perfil actualizado correctamente.")
                win.destroy()
                self.show_profile_selection()  # Refrescar la lista de perfiles
            except Exception as e:
                self.show_error("Error", str(e))
        
        btn_save = tb.Button(lf, text="Guardar cambios", bootstyle="success", command=save_profile)
        btn_save.grid(row=row_save, column=0, columnspan=2, pady=15)

    def set_app_icon(self, window):
        """Intenta cargar logo.ico o logo.png y establecerlo como ícono de la ventana."""
        base = os.path.dirname(os.path.abspath(__file__))
        candidates = ["logo.ico", "logo.png"]
        for name in candidates:
            path = os.path.join(base, name)
            if os.path.exists(path):
                try:
                    if name.endswith(".ico"):
                        window.iconbitmap(path)
                    else:
                        img = Image.open(path)
                        photo = ImageTk.PhotoImage(img)
                        window.iconphoto(False, photo)
                        # Guardar referencia para evitar garbage collection
                        if not hasattr(self, "_icon_refs"): self._icon_refs = []
                        self._icon_refs.append(photo)
                    break
                except Exception:
                    pass

    def center_window(self, window, width=None, height=None):
        """Centra una ventana en la pantalla."""
        window.update_idletasks()
        w = width or window.winfo_width()
        h = height or window.winfo_height()
        if w == 1 and width: w = width
        if h == 1 and height: h = height
        
        ws = window.winfo_screenwidth()
        hs = window.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        window.geometry(f'{w}x{h}+{x}+{y}')
    def open_pdf(self, path):
        """Abre un archivo PDF con el visor predeterminado del sistema."""
        try:
            if not os.path.exists(path):
                self.show_error("Archivo no encontrado", f"El PDF no existe en:\n{path}")
                return
            import subprocess
            if os.name == "nt":  # Windows
                subprocess.Popen(["start", "", path], shell=True)
            elif os.name == "posix":  # macOS / Linux
                subprocess.Popen(["xdg-open", path])
            else:
                self.show_info("PDF generado", f"Archivo PDF guardado en:\n{path}")
        except Exception as e:
            self.show_error("Error al abrir PDF", f"Error: {str(e)}\n\nIntenta abrirlo manualmente desde:\n{path}")

    def open_last_pdf(self):
        """Abre el último PDF generado si todavía existe."""
        path = getattr(self, "last_pdf_path", None)
        if path and os.path.exists(path):
            self.open_pdf(path)
            return
        self.show_info("Sin PDF", "No hay ningún PDF reciente para abrir. Genere una boleta primero.")
    def build_profile_ui(self):
        f = self.frame_profile
        f.columnconfigure(0, weight=1)
        f.rowconfigure(0, weight=1)

        layout = tb.Frame(f)
        layout.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        layout.columnconfigure(0, weight=3)
        layout.columnconfigure(1, weight=2)
        layout.rowconfigure(0, weight=1)

        main_lf = tb.Labelframe(
            layout,
            text="Perfil Comercial",
            padding=18,
            bootstyle="info"
        )
        main_lf.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        main_lf.columnconfigure(1, weight=1)

        tb.Label(main_lf, text="Identificación", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        tb.Separator(main_lf).grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 10))

        row = 2
        tb.Label(main_lf, text="Nombre de la empresa:").grid(row=row, column=0, sticky="e", padx=5, pady=4)
        self.entry_company_name = tb.Entry(main_lf, width=40)
        self.entry_company_name.grid(row=row, column=1, sticky="we", padx=5, pady=4)

        row += 1
        tb.Label(main_lf, text="RUC / NIF:").grid(row=row, column=0, sticky="e", padx=5, pady=4)
        self.entry_company_ruc = tb.Entry(main_lf)
        self.entry_company_ruc.grid(row=row, column=1, sticky="we", padx=5, pady=4)
        vcmd_company_ruc = (self.register(lambda P: self.validate_numeric(P, 11)), "%P")
        self.entry_company_ruc.configure(validate="key", validatecommand=vcmd_company_ruc)

        row += 1
        tb.Label(main_lf, text="Dirección:").grid(row=row, column=0, sticky="e", padx=5, pady=4)
        self.entry_company_address = tb.Entry(main_lf)
        self.entry_company_address.grid(row=row, column=1, sticky="we", padx=5, pady=4)

        tb.Label(main_lf, text="Contacto", font=("Segoe UI", 10, "bold")).grid(row=row + 1, column=0, columnspan=2, sticky="w", pady=(12, 4))
        tb.Separator(main_lf).grid(row=row + 2, column=0, columnspan=2, sticky="we", pady=(0, 10))
        row += 3

        tb.Label(main_lf, text="Teléfono / celular:").grid(row=row, column=0, sticky="e", padx=5, pady=4)
        self.entry_company_phone = tb.Entry(main_lf)
        self.entry_company_phone.grid(row=row, column=1, sticky="we", padx=5, pady=4)
        vcmd_company_phone = (self.register(lambda P: self.validate_numeric(P, 11)), "%P")
        self.entry_company_phone.configure(validate="key", validatecommand=vcmd_company_phone)

        row += 1
        tb.Label(main_lf, text="Correo electrónico:").grid(row=row, column=0, sticky="e", padx=5, pady=4)
        self.entry_company_email = tb.Entry(main_lf)
        self.entry_company_email.grid(row=row, column=1, sticky="we", padx=5, pady=4)

        row += 1
        tb.Label(main_lf, text="Página web:").grid(row=row, column=0, sticky="e", padx=5, pady=4)
        self.entry_company_website = tb.Entry(main_lf)
        self.entry_company_website.grid(row=row, column=1, sticky="we", padx=5, pady=4)

        tb.Label(main_lf, text="Mensaje para tickets", font=("Segoe UI", 10, "bold")).grid(row=row + 1, column=0, columnspan=2, sticky="w", pady=(12, 4))
        tb.Separator(main_lf).grid(row=row + 2, column=0, columnspan=2, sticky="we", pady=(0, 10))
        row += 3

        tb.Label(main_lf, text="Pie de página:").grid(row=row, column=0, sticky="e", padx=5, pady=4)
        self.entry_company_footer = tb.Entry(main_lf)
        self.entry_company_footer.grid(row=row, column=1, sticky="we", padx=5, pady=4)

        row += 1
        tb.Label(main_lf, text="Logo empresa:").grid(row=row, column=0, sticky="ne", padx=5, pady=4)
        logo_frame = tb.Frame(main_lf)
        logo_frame.grid(row=row, column=1, sticky="we", padx=5, pady=4)
        logo_frame.columnconfigure(0, weight=1)

        self.btn_load_logo = tb.Button(
            logo_frame,
            text="Subir logo",
            bootstyle="secondary-outline",
            command=self.load_logo
        )
        self.btn_load_logo.grid(row=0, column=0, sticky="w", pady=(0, 6))

        self.logo_preview_label = tb.Label(logo_frame)
        self.logo_preview_label.grid(row=1, column=0, sticky="w")

        row += 1
        tb.Button(
            main_lf,
            text="Guardar perfil",
            bootstyle="success",
            command=self.save_company_profile,
            width=26
        ).grid(row=row, column=0, columnspan=2, pady=(16, 0))

        payment_lf = tb.Labelframe(
            layout,
            text="Visor para el Cliente",
            padding=18,
            bootstyle="warning"
        )
        payment_lf.grid(row=0, column=1, sticky="nsew")
        payment_lf.columnconfigure(0, weight=1)
        payment_lf.columnconfigure(1, weight=1)

        tb.Label(payment_lf, text="Cobro por QR", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        tb.Separator(payment_lf).grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 10))

        tb.Label(payment_lf, text="QR de Yape:").grid(row=2, column=0, sticky="ne", padx=5, pady=5)
        qr_frame = tb.Frame(payment_lf)
        qr_frame.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        self.btn_load_yape_qr = tb.Button(
            qr_frame,
            text="Subir QR de Yape",
            bootstyle="secondary-outline",
            command=self.load_yape_qr_image
        )
        self.btn_load_yape_qr.pack(anchor="w", pady=(0, 6))

        self.yape_qr_preview_label = tb.Label(qr_frame)
        self.yape_qr_preview_label.pack(anchor="w")

        tb.Label(payment_lf, text="Pantalla del Cliente:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.combo_customer_screen = tb.Combobox(payment_lf, state="readonly")
        self.combo_customer_screen.grid(row=3, column=1, sticky="we", padx=5, pady=5)

        self.btn_test_customer_screen = tb.Button(
            payment_lf,
            text="Probar Pantalla",
            bootstyle="warning-outline",
            command=self.test_customer_screen
        )
        self.btn_test_customer_screen.grid(row=4, column=1, sticky="w", padx=5, pady=(5, 0))

        self.fill_company_profile_ui()
        
        # Forzar mayúsculas
        self.setup_uppercase_entry(
            self.entry_company_name,
            self.entry_company_ruc,
            self.entry_company_address,
            self.entry_company_phone,
            self.entry_company_email,
            self.entry_company_website,
            self.entry_company_footer
        )

    def fill_company_profile_ui(self):
        data = self.current_company_data or {}
        self.entry_company_name.delete(0, tk.END)
        self.entry_company_name.insert(0, data.get("name", ""))

        self.entry_company_ruc.delete(0, tk.END)
        self.entry_company_ruc.insert(0, data.get("ruc", ""))

        self.entry_company_address.delete(0, tk.END)
        self.entry_company_address.insert(0, data.get("address", ""))

        self.entry_company_phone.delete(0, tk.END)
        self.entry_company_phone.insert(0, data.get("phone", ""))

        self.entry_company_email.delete(0, tk.END)
        self.entry_company_email.insert(0, data.get("email", ""))

        self.entry_company_website.delete(0, tk.END)
        self.entry_company_website.insert(0, data.get("website", ""))

        self.entry_company_footer.delete(0, tk.END)
        self.entry_company_footer.insert(0, data.get("footer_message", ""))

        logo_path = data.get("logo_path")
        if logo_path and os.path.exists(logo_path):
            self.show_logo_preview(logo_path)

        self.show_yape_qr_preview(data.get("yape_qr_path"))
        self.populate_customer_screen_selector()

    def load_logo(self):
        filetypes = [
            ("Imágenes", "*.png;*.jpg;*.jpeg;*.bmp"),
            ("Todos los archivos", "*.*"),
        ]
        path = filedialog.askopenfilename(title="Seleccionar logo", filetypes=filetypes)
        if path:
            if self.current_company_data is None:
                self.current_company_data = {}
            self.current_company_data["logo_path"] = path
            self.show_logo_preview(path)

    def show_logo_preview(self, path):
        try:
            img = Image.open(path)
            w, h = img.size
            new_h = 120
            new_w = int(w * (new_h / h))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.current_logo_image = ImageTk.PhotoImage(img)
            self.logo_preview_label.configure(image=self.current_logo_image)
        except Exception as e:
            self.show_error("Error", f"No se pudo cargar el logo: {e}")

    def load_yape_qr_image(self):
        filetypes = [
            ("Imágenes", "*.png;*.jpg;*.jpeg;*.bmp"),
            ("Todos los archivos", "*.*"),
        ]
        path = filedialog.askopenfilename(title="Seleccionar QR de Yape", filetypes=filetypes)
        if not path:
            return

        if self.current_company_data is None:
            self.current_company_data = {}
        self.current_company_data["yape_qr_path"] = path
        self.show_yape_qr_preview(path)

    def show_yape_qr_preview(self, path):
        label = getattr(self, "yape_qr_preview_label", None)
        if not label:
            return

        if not path or not os.path.exists(path):
            label.configure(image="", text="(Sin QR configurado)")
            self.yape_qr_preview_image = None
            return

        try:
            img = Image.open(path)
            img = img.resize((160, 160), Image.Resampling.LANCZOS)
            self.yape_qr_preview_image = ImageTk.PhotoImage(img)
            label.configure(image=self.yape_qr_preview_image, text="")
        except Exception as e:
            self.yape_qr_preview_image = None
            label.configure(image="", text="(Error al cargar QR)")
            self.show_error("Error", f"No se pudo cargar el QR de Yape: {e}")

    def populate_customer_screen_selector(self):
        combo = getattr(self, "combo_customer_screen", None)
        if not combo:
            return

        options = self.customer_display.get_monitor_options() if hasattr(self, "customer_display") else []
        if not options:
            options = ["Pantalla 0 (Principal)"]
        combo.configure(values=options)

        try:
            saved_idx = int(self.settings_repo.get_setting("customer_screen_index", "0"))
        except (TypeError, ValueError):
            saved_idx = 0

        if saved_idx < 0 or saved_idx >= len(options):
            saved_idx = 0

        if options:
            combo.current(saved_idx)

    def test_customer_screen(self):
        combo = getattr(self, "combo_customer_screen", None)
        if not combo:
            return

        idx = combo.current() if combo.current() != -1 else 0
        if not self.customer_display.show_test_screen(idx):
            self.show_warning("Pantalla", "No se pudo abrir la vista previa en la pantalla seleccionada.")

    def save_company_profile(self):
        self.current_company_data = {
            "name": self.entry_company_name.get(),
            "ruc": self.entry_company_ruc.get(),
            "address": self.entry_company_address.get(),
            "phone": self.entry_company_phone.get(),
            "email": self.entry_company_email.get(),
            "website": self.entry_company_website.get(),
            "footer_message": self.entry_company_footer.get(),
            "logo_path": (self.current_company_data or {}).get("logo_path"),
            "yape_qr_path": (self.current_company_data or {}).get("yape_qr_path"),
            "include_igv": (self.current_company_data or {}).get("include_igv", 1)
        }
        # Guardar pantalla configurada
        combo = getattr(self, "combo_customer_screen", None)
        screen_idx = combo.current() if combo and combo.current() != -1 else 0
        self.settings_repo.set_setting("customer_screen_index", str(screen_idx))
        # Guardar el perfil usando el company_id actual
        self.company_service.save_profile(self.current_company_id, self.current_company_data)
        self.show_info("Éxito", "Perfil de empresa guardado correctamente.")

    def create_new_profile_dialog(self):
        """Abre un diálogo para crear un nuevo perfil de empresa."""
        win = tb.Toplevel(master=self)
        win.title("Crear Nuevo Perfil")
        win.geometry("450x250")
        self.set_app_icon(win)
        self.center_window(win, 450, 250)
        self.make_modal(win)

        lf = tb.Labelframe(win, text="Nuevo Perfil", padding=12, bootstyle="info")
        lf.pack(fill="both", expand=True, padx=10, pady=10)
        lf.columnconfigure(1, weight=1)

        tb.Label(lf, text="Nombre de la empresa:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        entry_name = tb.Entry(lf, width=40)
        entry_name.grid(row=0, column=1, sticky="we", padx=5, pady=5)

        tb.Label(lf, text="RUC / NIF:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        entry_ruc = tb.Entry(lf)
        entry_ruc.grid(row=1, column=1, sticky="we", padx=5, pady=5)
        vcmd_dialog_ruc = (self.register(lambda P: self.validate_numeric(P, 11)), "%P")
        entry_ruc.configure(validate="key", validatecommand=vcmd_dialog_ruc)
        
        self.setup_uppercase_entry(entry_name, entry_ruc)

        def save_new():
            name = entry_name.get().strip()
            ruc = entry_ruc.get().strip()
            if not name:
                self.show_warning("Atención", "El nombre es obligatorio.")
                return
            try:
                company_id = self.company_service.create_profile(name=name, ruc=ruc)
                self.current_company_id = company_id
                # Asegurar que company_id sea entero válido
                self.current_company_data = self.company_service.get_profile(company_id or 1)
                self.load_main_logo()
                self.show_info("Éxito", f"Perfil '{name}' creado correctamente.")
                win.destroy()
            except Exception as e:
                self.show_error("Error", str(e))

        btn_save = tb.Button(lf, text="Crear perfil", bootstyle="success-outline", command=save_new)
        btn_save.grid(row=2, column=0, columnspan=2, pady=12)

    def load_main_logo(self):
        """Carga el logo principal desde el perfil o desde un archivo llamado logo.* en la carpeta del script."""
        base = os.path.dirname(os.path.abspath(__file__))
        candidates = []
        if (self.current_company_data or {}).get("logo_path"):
            candidates.append((self.current_company_data or {}).get("logo_path"))
        for name in ("logo.png", "logo.jpg", "logo.jpeg", "logo.bmp"):
            candidates.append(os.path.join(base, name))

        chosen = None
        for p in candidates:
            if p and os.path.exists(p):
                chosen = p
                break

        if chosen:
            try:
                img = Image.open(chosen)
                w, h = img.size
                new_h = 48
                new_w = int(w * (new_h / h))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                self.main_logo_image = ImageTk.PhotoImage(img)
                if self.logo_label is not None:
                    try:
                        self.logo_label.configure(image=self.main_logo_image)
                    except Exception:
                        pass
            except Exception:
                pass

    def open_profile_modal(self):
        """Abre un modal para editar/guardar y seleccionar perfiles de empresa."""
        win = tb.Toplevel(master=self)
        win.title("Gestión de Perfiles de Empresa")
        win.geometry("600x500")
        self.set_app_icon(win)
        self.center_window(win, 600, 500)
        self.make_modal(win)

        body = self.create_scrollable_dialog_body(win, padding=12)

        # Marco para selector de perfil
        select_lf = tb.Labelframe(body, text="Seleccionar Perfil", padding=10, bootstyle="secondary")
        select_lf.pack(fill="x", padx=10, pady=(10, 5))
        select_lf.columnconfigure(1, weight=1)

        tb.Label(select_lf, text="Perfil actual:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        profiles = self.company_service.get_all_profiles()
        profile_names = [p["name"] for p in profiles]
        current_idx = next((i for i, p in enumerate(profiles) if p["id"] == (self.current_company_data or {}).get("id", 1)), 0)
        
        combo_profile = tb.Combobox(select_lf, values=profile_names, state="readonly", width=40)
        combo_profile.current(current_idx)
        combo_profile.grid(row=0, column=1, padx=5, pady=5, sticky="we")

        def switch_profile():
            idx = combo_profile.current()
            if 0 <= idx < len(profiles):
                self.current_company_data = profiles[idx]
                self.current_company_id = profiles[idx]["id"]
                fill_form()
        combo_profile.bind("<<ComboboxSelected>>", lambda _e: switch_profile())

        lf = tb.Labelframe(body, text="Datos del Perfil", padding=12, bootstyle="info")
        lf.pack(fill="both", expand=True, padx=10, pady=10)
        lf.columnconfigure(1, weight=1)

        fields = [
            ("Nombre de la empresa:", "name"),
            ("RUC / NIF:", "ruc"),
            ("Dirección:", "address"),
            ("Teléfono / celular:", "phone"),
            ("Correo electrónico:", "email"),
            ("Página web:", "website"),
            ("Mensaje pie de página:", "footer_message"),
            ("Color franja (hex):", "brand_color"),
        ]

        entries = {}
        for i, (label_text, key) in enumerate(fields):
            tb.Label(lf, text=label_text).grid(row=i, column=0, sticky="e", padx=5, pady=5)
            entry = tb.Entry(lf, width=40) if key == "name" else tb.Entry(lf)
            entry.grid(row=i, column=1, sticky="we", padx=5, pady=5)
            entries[key] = entry

        # Botón cargar logo
        row_logo = len(fields)
        tb.Label(lf, text="Logo empresa:").grid(row=row_logo, column=0, sticky="ne", padx=5, pady=5)
        btn_load = tb.Button(lf, text="Cargar logo", bootstyle="secondary-outline")
        btn_load.grid(row=row_logo, column=1, sticky="w", padx=5, pady=5)

        modal_logo_path = [(self.current_company_data or {}).get("logo_path")]

        def modal_load_logo():
            path = filedialog.askopenfilename(title="Seleccionar logo",
                                              filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.bmp"), ("Todos", "*.*")])
            if path:
                modal_logo_path[0] = path
                self.show_info("Logo", "Logo seleccionado. Guarda para aplicar.")

        btn_load.configure(command=modal_load_logo)

        def fill_form():
            data = self.current_company_data or {}
            entries["name"].delete(0, tk.END)
            entries["name"].insert(0, data.get("name", ""))
            entries["ruc"].delete(0, tk.END)
            entries["ruc"].insert(0, data.get("ruc", ""))
            entries["address"].delete(0, tk.END)
            entries["address"].insert(0, data.get("address", ""))
            entries["phone"].delete(0, tk.END)
            entries["phone"].insert(0, data.get("phone", ""))
            entries["email"].delete(0, tk.END)
            entries["email"].insert(0, data.get("email", ""))
            entries["website"].delete(0, tk.END)
            entries["website"].insert(0, data.get("website", ""))
            entries["footer_message"].delete(0, tk.END)
            entries["footer_message"].insert(0, data.get("footer_message", ""))
            entries["brand_color"].delete(0, tk.END)
            entries["brand_color"].insert(0, data.get("brand_color", "#1f77b4"))
            modal_logo_path[0] = data.get("logo_path")

        fill_form()

        def modal_save():
            newdata = {
                "name": entries["name"].get().strip(),
                "ruc": entries["ruc"].get().strip(),
                "address": entries["address"].get().strip(),
                "phone": entries["phone"].get().strip(),
                "email": entries["email"].get().strip(),
                "website": entries["website"].get().strip(),
                "footer_message": entries["footer_message"].get().strip(),
                "logo_path": modal_logo_path[0],
                "brand_color": entries["brand_color"].get().strip() or "#1f77b4",
                "yape_qr_path": (self.current_company_data or {}).get("yape_qr_path")
            }
            self.current_company_data = newdata
            try:
                self.company_service.save_profile(self.current_company_id, newdata)
                self.load_main_logo()
                self.show_info("Éxito", "Perfil de empresa guardado correctamente.")
                win.destroy()
            except Exception as e:
                self.show_error("Error", str(e))

        btn_save = tb.Button(lf, text="Guardar perfil", bootstyle="success-outline", command=modal_save)
        btn_save.grid(row=row_logo + 1, column=0, columnspan=2, pady=12)

    # ---------------- VENTAS / BOLETAS ---------------- #

    # ========== MÉTODOS PARA CATÁLOGO DE PRODUCTOS EN VENTAS ==========
    # (Movidos a ui_products.py y ui_sales.py)

    # ========== MÉTODOS PARA CATÁLOGO DE PRODUCTOS EN VENTAS ==========
    # (Movidos a ui_products.py)


    # ========== MÉTODOS PARA ENVÍO DE BOLETAS POR CORREO / WHATSAPP ==========
    def open_email_config_dialog(self):
        """Abre diálogo para configurar credenciales de correo."""
        if not self.ask_pin("Configuración de Correo"):
            return

        win = tb.Toplevel(master=self)
        win.title("Configuración de Correo (Outlook)")
        win.geometry("400x300")
        self.set_app_icon(win)
        self.center_window(win, 400, 300)
        self.make_modal(win)

        tb.Label(win, text="Configuración SMTP (Gmail)", font=("Helvetica", 12, "bold")).pack(pady=15)

        frame = tb.Frame(win, padding=10)
        frame.pack(fill="x")

        tb.Label(frame, text="Correo (Gmail):").pack(anchor="w")
        entry_email = tb.Entry(frame)
        entry_email.pack(fill="x", pady=(0, 10))
        
        # Cargar valor actual
        current_email = self.settings_service.repo.get_setting("email_sender", "")
        entry_email.insert(0, current_email)

        tb.Label(frame, text="Contraseña de Aplicación:").pack(anchor="w")
        entry_pass = tb.Entry(frame, show="*")
        entry_pass.pack(fill="x", pady=(0, 10))
        
        # Cargar valor actual
        current_pass = self.settings_service.repo.get_setting("email_password", "")
        entry_pass.insert(0, current_pass)

        def save_config():
            email = entry_email.get().strip()
            password = entry_pass.get().strip()
            
            if not email or not password:
                self.show_warning("Atención", "Ambos campos son obligatorios.")
                return
                
            self.settings_service.repo.set_setting("email_sender", email)
            self.settings_service.repo.set_setting("email_password", password)
            self.show_success("Guardado", "Credenciales guardadas correctamente.")
            win.destroy()

        tb.Button(win, text="Guardar Configuración", bootstyle="success", command=save_config).pack(pady=10)

    def ask_client_email_dialog(self, initial_value="", parent=None):
        """Diálogo personalizado para pedir correo del cliente."""
        dialog = tb.Toplevel(master=parent or self)
        dialog.title("Enviar Correo")
        dialog.geometry("400x220")
        self.set_app_icon(dialog)
        self.center_window(dialog, 400, 220)
        self.make_modal(dialog, parent=parent or self)

        tb.Label(dialog, text="📧 Enviar Boleta por Correo", font=("Helvetica", 12, "bold"), bootstyle="primary").pack(pady=15)
        
        tb.Label(dialog, text="Correo del Cliente:", font=("Helvetica", 10)).pack(pady=(0, 5))
        
        email_var = tk.StringVar(value=initial_value)
        entry = tb.Entry(dialog, textvariable=email_var, font=("Helvetica", 11), width=35)
        entry.pack(pady=5, padx=20)
        entry.focus_set()
        entry.select_range(0, tk.END)

        confirmed_email = None

        def on_confirm():
            nonlocal confirmed_email
            val = email_var.get().strip()
            if not is_valid_email(val):
                self.show_warning("Atención", "Ingrese un correo válido.")
                return
            confirmed_email = val
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = tb.Frame(dialog)
        btn_frame.pack(pady=20, fill="x")

        tb.Button(btn_frame, text="Cancelar", bootstyle="secondary", command=on_cancel).pack(side="right", padx=20)
        tb.Button(btn_frame, text="Enviar Ahora", bootstyle="success", command=on_confirm).pack(side="right", padx=5)
        
        dialog.bind("<Return>", lambda e: on_confirm())
        dialog.bind("<Escape>", lambda e: on_cancel())

        self.wait_window(dialog)
        return confirmed_email

    def ask_whatsapp_number_dialog(self, initial_value="", parent=None):
        """Solicita un número de WhatsApp asegurando que tenga al menos 9 dígitos."""
        dialog = tb.Toplevel(master=parent or self)
        dialog.title("Número de WhatsApp")
        dialog.geometry("360x220")
        self.set_app_icon(dialog)
        self.center_window(dialog, 360, 220)
        self.make_modal(dialog, parent=parent or self)

        tb.Label(dialog, text="💬 Enviar por WhatsApp", font=("Helvetica", 12, "bold"), bootstyle="success").pack(pady=15)
        tb.Label(dialog, text="Ingrese el número del cliente (solo dígitos):", font=("Helvetica", 10)).pack(pady=(0, 5))

        phone_var = tk.StringVar(value=initial_value)
        entry = tb.Entry(dialog, textvariable=phone_var, font=("Helvetica", 12), justify="center")
        entry.pack(padx=20, pady=5, fill="x")
        vcmd_whatsapp_phone = (self.register(lambda P: self.validate_numeric(P, 11)), "%P")
        entry.configure(validate="key", validatecommand=vcmd_whatsapp_phone)
        entry.focus_set()
        entry.select_range(0, tk.END)

        result = None

        def normalize_number(raw: str) -> str:
            digits = normalize_phone_number(raw)
            digits = ensure_country_prefix(digits)
            return digits

        def on_confirm():
            nonlocal result
            digits = normalize_number(phone_var.get())
            if len(digits) < 11:
                self.show_warning("Atención", "Debe ingresar un número válido (mínimo 9 dígitos sin prefijo o 11 con prefijo).")
                return
            result = digits
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = tb.Frame(dialog)
        btn_frame.pack(pady=20)

        tb.Button(btn_frame, text="Cancelar", bootstyle="secondary", command=on_cancel, width=12).pack(side="right", padx=5)
        tb.Button(btn_frame, text="Usar número", bootstyle="success", command=on_confirm, width=12).pack(side="right", padx=5)

        dialog.bind("<Return>", lambda _e: on_confirm())
        dialog.bind("<Escape>", lambda _e: on_cancel())

        self.wait_window(dialog)
        return result

    def _extract_name_from_email(self, email: str) -> str:
        if not email or "@" not in email:
            return ""
        local_part = email.split("@", 1)[0]
        local_part = local_part.replace('.', ' ').replace('_', ' ').strip()
        if not local_part:
            return ""
        return " ".join(segment.capitalize() for segment in local_part.split())

    def build_email_payload(self, sale_id, target_email, pdf_path, *, resend=False):
        """Genera asunto, cuerpo y recursos listos para enviar el comprobante."""
        from datetime import datetime

        company_data = self.current_company_data or {}
        display_company_name = (company_data.get("name") or "").strip() or "Tu Empresa"
        company_phone_raw = (company_data.get("phone") or "").strip()

        logo_path = company_data.get("logo_path")
        if not logo_path or not os.path.exists(logo_path):
            default_logo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
            logo_path = default_logo if os.path.exists(default_logo) else None

        sale_series = sale_number = sale_datetime = sale_total = None
        client_fullname = ""
        if sale_id:
            try:
                sale, _items = self.sale_service.get_sale(sale_id)
            except Exception:
                sale = None
            if sale:
                sale_map = self.sale_service.map_sale_row(sale)
                sale_series = sale_map.get("series")
                sale_number = sale_map.get("number")
                sale_datetime = sale_map.get("datetime")
                sale_total = sale_map.get("total")
                client_id = sale_map.get("client_id")
                if client_id:
                    client_row = self.client_repo.get_client_by_id(client_id)
                    if client_row and len(client_row) > 2 and client_row[2]:
                        client_fullname = client_row[2].strip()

        client_name = client_fullname or self._extract_name_from_email(target_email) or "Cliente"

        pdf_identifier = os.path.splitext(os.path.basename(pdf_path))[0] if pdf_path else "COMPROBANTE"

        comprobante = (
            f"{sale_series}-{int(sale_number):06d}"
            if sale_series and sale_number is not None else pdf_identifier
        )

        fecha_boleta = datetime.now().strftime("%d/%m/%Y")
        if sale_datetime:
            try:
                dt_sale = datetime.strptime(sale_datetime, "%Y-%m-%d %H:%M:%S")
                fecha_boleta = dt_sale.strftime("%d/%m/%Y %H:%M")
            except Exception:
                fecha_boleta = sale_datetime

        total_str = "0.00"
        if sale_total is not None:
            try:
                total_str = f"{float(sale_total):.2f}"
            except Exception:
                total_str = str(sale_total)

        phone_digits = normalize_phone_number(company_phone_raw)
        phone_digits = ensure_country_prefix(phone_digits)
        phone_visible = company_phone_raw or format_phone_display(phone_digits) or phone_digits
        phone_line_plain = f"\nWhatsApp: {phone_visible}" if phone_visible else ""

        if resend:
            opening_plain = "Atendiendo a tu solicitud, te reenviamos la copia de tu documento.\n\n"
            despedida_plain = "Quedamos a tu disposición."
        else:
            opening_plain = (
                f"¡Muchas gracias por su visita el día {fecha_boleta}! Agradecemos su preferencia.\n\n"
                "A continuación, hacemos entrega de su comprobante de pago electrónico.\n\n"
            )
            despedida_plain = "Gracias por tu preferencia."

        body_plain = (
            f"Hola, {client_name} 👋,\n\n"
            f"{opening_plain}"
            "Detalles de la transacción:\n"
            f"Comprobante: {comprobante}\n"
            f"Fecha: {fecha_boleta}\n"
            f"Total: S/ {total_str}\n\n"
            "El documento PDF se encuentra adjunto a este correo.\n\n"
            f"{despedida_plain}\nEl equipo de {display_company_name}{phone_line_plain}\n\n"
            "Representación impresa de nota de venta interna. Este documento no es válido para efectos tributarios hasta su validación final."
        )

        company_payload = dict(company_data)
        if phone_visible:
            company_payload.setdefault("phone", phone_visible)
        if logo_path and not company_payload.get("logo_path"):
            company_payload["logo_path"] = logo_path

        body_html = generate_email_html(
            client_name=client_name,
            sale_number=comprobante,
            total=total_str,
            date_str=fecha_boleta,
            company_data=company_payload,
            is_resend=resend,
        )

        subject_base = "REENVIO comprobante electrónico" if resend else "Comprobante electrónico"
        subject = f"{subject_base} - {display_company_name}"

        return {
            "subject": subject,
            "body_plain": body_plain,
            "body_html": body_html,
            "company_display_name": display_company_name,
            "logo_path": logo_path
        }

    def show_post_sale_options(self, sale_id, pdf_path, client_email, client_phone="", client_name=""):
        """Muestra opciones post venta y reutiliza el estilo de correo estándar."""
        win = tb.Toplevel(master=self)
        win.title("Venta Exitosa")
        win.geometry("500x350")
        self.set_app_icon(win)
        self.center_window(win, 500, 350)
        self.make_modal(win)

        tb.Label(win, text="✅ Venta Registrada y PDF Generado", font=("Helvetica", 14, "bold"), bootstyle="success").pack(pady=20)
        
        tb.Label(win, text=f"Archivo: {os.path.basename(pdf_path)}", font=("Helvetica", 10)).pack(pady=5)

        btn_frame = tb.Frame(win, padding=20)
        btn_frame.pack(fill="both", expand=True)

        # 1. Ver Archivo
        def open_folder():
            try:
                subprocess.Popen(f'explorer /select,"{os.path.abspath(pdf_path)}"')
            except Exception as e:
                self.show_error("Error", f"No se pudo abrir la carpeta:\n{e}")

        tb.Button(btn_frame, text="📂 Ver Archivo en Carpeta", bootstyle="info-outline", command=open_folder, width=30).pack(pady=10)

        # 2. Enviar Correo
        def send_email():
            sender = self.settings_service.repo.get_setting("email_sender")
            password = self.settings_service.repo.get_setting("email_password")
            
            if not sender or not password:
                self.show_error("Error", "No hay credenciales de correo configuradas.\nVaya a Configuración > Correo.")
                return

            # Confirmar correo del cliente (Custom Dialog)
            target_email = self.ask_client_email_dialog(client_email or "", parent=win)
            if not target_email:
                return

            payload = self.build_email_payload(sale_id, target_email, pdf_path)
            subject = payload["subject"]
            body_plain = payload["body_plain"]
            body_html = payload["body_html"]
            company_display_name = payload["company_display_name"]
            logo_path = payload["logo_path"]

            self.show_loading("Enviando correo...")

            def finish_email_send(success, msg):
                self.hide_loading()
                if success:
                    self.show_success("Correo Enviado", msg, use_toast=True)
                else:
                    self.show_error("Error al enviar", msg)

            def email_thread_task():
                try:
                    result = self.comm_service.send_email_with_pdf(
                        target_email,
                        subject,
                        body_plain,
                        pdf_path,
                        sender,
                        password,
                        company_name=company_display_name,
                        body_html=body_html,
                        logo_path=logo_path
                    )
                except Exception as exc:
                    result = (False, f"Error inesperado: {exc}")
                self.after(0, lambda res=result: finish_email_send(*res))

            threading.Thread(target=email_thread_task, daemon=True).start()

        tb.Button(btn_frame, text="📧 Enviar por Correo", bootstyle="warning-outline", command=send_email, width=30).pack(pady=10)

        # 3. Enviar por WhatsApp
        def send_whatsapp():
            # Preferir el número almacenado en la ficha del cliente
            phone_digits = normalize_phone_number(client_phone)

            # Si no disponemos de un número válido, solicitarlo al usuario
            if len(phone_digits) < 9:
                phone_candidate = self.ask_whatsapp_number_dialog("", parent=win)
                if not phone_candidate:
                    return
                phone_digits = normalize_phone_number(phone_candidate)

            phone_number = ensure_country_prefix(phone_digits)
            if not phone_number:
                self.show_warning("Atención", "No se pudo obtener un número de WhatsApp válido.")
                return

            # Generar mensaje personalizado reutilizando plantillas estándar
            try:
                sale_datetime = None
                client_from_sale = ""
                if sale_id:
                    try:
                        sale, _ = self.sale_service.get_sale(sale_id)
                    except Exception:
                        sale = None
                    if sale:
                        sale_map = self.sale_service.map_sale_row(sale)
                        if isinstance(sale_map, dict):
                            sale_dt_str = sale_map.get("datetime")
                            if sale_dt_str:
                                try:
                                    sale_datetime = datetime.strptime(sale_dt_str, "%Y-%m-%d %H:%M:%S")
                                except Exception:
                                    sale_datetime = None

                            client_id = sale_map.get("client_id")
                            if client_id:
                                try:
                                    client_row = self.client_repo.get_client_by_id(client_id)
                                except Exception:
                                    client_row = None
                                if client_row and len(client_row) > 2:
                                    client_from_sale = (client_row[2] or "").strip()

                company_name = (self.current_company_data or {}).get("name", "Nuestra Empresa")

                name_candidate = (client_name or "").strip()
                if not name_candidate:
                    name_candidate = client_from_sale
                if not name_candidate:
                    name_candidate = str((self.current_client or {}).get("name") or "").strip()
                client_display_name = name_candidate or "Cliente"

                mensaje = build_whatsapp_message(company_name, client_display_name, sale_datetime)
            except Exception:
                mensaje = "Adjunto encontrara su boleta de venta digital. Gracias por su preferencia!"
            
            # Enviar automáticamente en segundo plano
            self.show_loading("Enviando WhatsApp...")

            def finish_whatsapp_send(success, msg):
                self.hide_loading()
                if success:
                    self.show_success("WhatsApp", msg, use_toast=True, duration=1400)
                else:
                    self.show_error("Error al enviar", msg)

            def whatsapp_thread_task():
                try:
                    result = self.comm_service.send_whatsapp_pdf(
                        phone_number,
                        pdf_path,
                        message=mensaje,
                        wait_seconds=1
                    )
                except Exception as exc:
                    result = (False, f"Error inesperado: {exc}")
                self.after(0, lambda res=result: finish_whatsapp_send(*res))

            threading.Thread(target=whatsapp_thread_task, daemon=True).start()
        
        tb.Button(btn_frame, text="💬 Enviar por WhatsApp", bootstyle="success-outline", command=send_whatsapp, width=30).pack(pady=10)

        # 4. Cerrar
        tb.Button(btn_frame, text="Cerrar", bootstyle="secondary", command=win.destroy, width=30).pack(pady=10)




    # ---------------- ACTUALIZAR INFORMACIÓN (GESTIÓN MAESTRA) ---------------- #

    def build_update_info_ui(self):
        """Construye la interfaz dividida para gestionar Clientes y Productos."""
        # Limpiar frame
        for widget in self.frame_update_info.winfo_children():
            widget.destroy()

        # Contenedor principal con grid de 2 columnas
        main_container = tb.Frame(self.frame_update_info)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=1)

        # --- COLUMNA IZQUIERDA: CLIENTES ---
        frame_clients = tb.Labelframe(main_container, text="👥 Gestión de Clientes", padding=15, bootstyle="primary")
        frame_clients.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        frame_clients.rowconfigure(1, weight=1)  # Treeview expandible
        frame_clients.columnconfigure(0, weight=1)

        # Buscador Clientes
        search_frame_cli = tb.Frame(frame_clients)
        search_frame_cli.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        search_frame_cli.columnconfigure(0, weight=1)
        
        self.entry_search_client = tb.Entry(search_frame_cli, font=("Helvetica", 10))
        self.entry_search_client.grid(row=0, column=0, sticky="ew", padx=5)
        self.entry_search_client.insert(0, "Buscar cliente...")
        self.entry_search_client.bind("<FocusIn>", lambda e: self.entry_search_client.delete(0, tk.END) if self.entry_search_client.get() == "Buscar cliente..." else None)
        self.entry_search_client.bind(
            "<KeyRelease>",
            lambda event: self.on_search_debounce("clients", self.client_ui.filter_clients)
        )

        # Treeview Clientes con Scrollbar
        tree_frame_cli = tb.Frame(frame_clients)
        tree_frame_cli.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        tree_frame_cli.rowconfigure(0, weight=1)
        tree_frame_cli.columnconfigure(0, weight=1)

        cols_cli = ("id", "dni", "name", "phone", "email", "addr")
        self.tree_clients = tb.Treeview(tree_frame_cli, columns=cols_cli, show="headings", height=10, bootstyle="primary")
        self.tree_clients.heading("id", text="ID")
        self.tree_clients.heading("dni", text="DNI/RUC")
        self.tree_clients.heading("name", text="Nombre")
        self.tree_clients.heading("phone", text="Celular")
        self.tree_clients.heading("email", text="Email")
        self.tree_clients.heading("addr", text="Dirección")
        
        self.tree_clients.column("id", width=40, stretch=False)
        self.tree_clients.column("dni", width=80)
        self.tree_clients.column("name", width=150)
        self.tree_clients.column("phone", width=80)
        self.tree_clients.column("email", width=100)
        self.tree_clients.column("addr", width=100)
        
        scrollbar_cli = tb.Scrollbar(tree_frame_cli, orient="vertical", command=self.tree_clients.yview, bootstyle="primary-round")
        scrollbar_cli_x = tb.Scrollbar(tree_frame_cli, orient="horizontal", command=self.tree_clients.xview, bootstyle="primary-round")
        self.tree_clients.configure(yscrollcommand=scrollbar_cli.set, xscrollcommand=scrollbar_cli_x.set)
        
        self.tree_clients.grid(row=0, column=0, sticky="nsew")
        scrollbar_cli.grid(row=0, column=1, sticky="ns")
        scrollbar_cli_x.grid(row=1, column=0, sticky="ew")
        
        self.tree_clients.bind("<<TreeviewSelect>>", self.client_ui.on_client_select)

        # Formulario Clientes
        form_cli = tb.Labelframe(frame_clients, text="Datos del Cliente", padding=10)
        form_cli.grid(row=2, column=0, sticky="ew")
        form_cli.columnconfigure(1, weight=1)

        # Widgets del formulario (necesarios para ClientUIManager)
        tb.Label(form_cli, text="DNI/RUC:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        self.entry_client_dni = tb.Entry(form_cli)
        self.entry_client_dni.grid(row=0, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_cli, text="Nombre:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        self.entry_client_name = tb.Entry(form_cli)
        self.entry_client_name.grid(row=1, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_cli, text="Celular:").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        self.entry_client_phone = tb.Entry(form_cli)
        self.entry_client_phone.grid(row=2, column=1, sticky="ew", padx=5, pady=3)

        vcmd_dni = (self.register(lambda P: self.validate_numeric(P, 11)), "%P")
        self.entry_client_dni.configure(validate="key", validatecommand=vcmd_dni)

        vcmd_phone = (self.register(lambda P: self.validate_numeric(P, 11)), "%P")
        self.entry_client_phone.configure(validate="key", validatecommand=vcmd_phone)
        
        tb.Label(form_cli, text="Email:").grid(row=3, column=0, sticky="e", padx=5, pady=3)
        self.entry_client_email = tb.Entry(form_cli)
        self.entry_client_email.grid(row=3, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_cli, text="Dirección:").grid(row=4, column=0, sticky="e", padx=5, pady=3)
        self.entry_client_address = tb.Entry(form_cli)
        self.entry_client_address.grid(row=4, column=1, sticky="ew", padx=5, pady=3)

        # Botones Clientes
        btn_frame_cli = tb.Frame(form_cli)
        btn_frame_cli.grid(row=5, column=0, columnspan=2, pady=10)
        
        tb.Button(btn_frame_cli, text="➕ Nuevo", bootstyle="info-outline", command=self.client_ui.clear_client_form).pack(side="left", padx=5)
        tb.Button(btn_frame_cli, text="Limpiar", bootstyle="secondary", command=self.client_ui.clear_client_form).pack(side="left", padx=5)
        tb.Button(btn_frame_cli, text="💾 Guardar", bootstyle="success", command=self.client_ui.save_client_action).pack(side="left", padx=5)

        # --- COLUMNA DERECHA: PRODUCTOS ---
        frame_products = tb.Labelframe(main_container, text="📦 Gestión de Productos", padding=15, bootstyle="info")
        frame_products.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        frame_products.rowconfigure(1, weight=1)
        frame_products.columnconfigure(0, weight=1)

        # Buscador Productos
        search_frame_prod = tb.Frame(frame_products)
        search_frame_prod.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        search_frame_prod.columnconfigure(0, weight=1)
        
        self.entry_search_product = tb.Entry(search_frame_prod, font=("Helvetica", 10))
        self.entry_search_product.grid(row=0, column=0, sticky="ew", padx=5)
        self.entry_search_product.insert(0, "Buscar producto...")
        self.entry_search_product.bind("<FocusIn>", lambda e: self.entry_search_product.delete(0, tk.END) if self.entry_search_product.get() == "Buscar producto..." else None)
        self.entry_search_product.bind(
            "<KeyRelease>",
            lambda event: self.on_search_debounce("products", self.product_ui.filter_products)
        )

        # Treeview Productos con Scrollbar
        tree_frame_prod = tb.Frame(frame_products)
        tree_frame_prod.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        tree_frame_prod.rowconfigure(0, weight=1)
        tree_frame_prod.columnconfigure(0, weight=1)

        cols_prod = ("id", "code", "name", "unit", "price", "stock")
        self.tree_products = tb.Treeview(tree_frame_prod, columns=cols_prod, show="headings", height=10, bootstyle="info")
        self.tree_products.heading("id", text="ID")
        self.tree_products.heading("code", text="Código")
        self.tree_products.heading("name", text="Nombre")
        self.tree_products.heading("unit", text="Unidad")
        self.tree_products.heading("price", text="Precio")
        self.tree_products.heading("stock", text="Stock")
        
        self.tree_products.column("id", width=40, stretch=False)
        self.tree_products.column("code", width=80)
        self.tree_products.column("name", width=200)
        self.tree_products.column("unit", width=60)
        self.tree_products.column("price", width=80)
        self.tree_products.column("stock", width=70)
        
        scrollbar_prod = tb.Scrollbar(tree_frame_prod, orient="vertical", command=self.tree_products.yview, bootstyle="info-round")
        scrollbar_prod_x = tb.Scrollbar(tree_frame_prod, orient="horizontal", command=self.tree_products.xview, bootstyle="info-round")
        self.tree_products.configure(yscrollcommand=scrollbar_prod.set, xscrollcommand=scrollbar_prod_x.set)
        
        self.tree_products.grid(row=0, column=0, sticky="nsew")
        scrollbar_prod.grid(row=0, column=1, sticky="ns")
        scrollbar_prod_x.grid(row=1, column=0, sticky="ew")
        
        self.tree_products.bind("<<TreeviewSelect>>", self.product_ui.on_product_select)
        self.tree_products.tag_configure("stock_empty", background="#FDE4E4", foreground="#5A0B0B")
        self.tree_products.tag_configure("stock_low", background="#FFF3CD", foreground="#665200")
        self.tree_products.tag_configure("stock_ok", background="", foreground="")
        self.tree_products.tag_configure("stock_na", background="", foreground="")

        # Formulario Productos
        form_prod = tb.Labelframe(frame_products, text="Datos del Producto", padding=10)
        form_prod.grid(row=2, column=0, sticky="ew")
        form_prod.columnconfigure(1, weight=1)

        self.var_prod_id = tk.StringVar()
        self.var_prod_code = tk.StringVar()
        self.var_prod_name = tk.StringVar()
        self.var_prod_unit = tk.StringVar()
        self.var_prod_price = tk.StringVar()
        self.var_prod_stock = tk.StringVar()

        tb.Label(form_prod, text="Código:").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_prod, textvariable=self.var_prod_code).grid(row=0, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_prod, text="Nombre:").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_prod, textvariable=self.var_prod_name).grid(row=1, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_prod, text="Unidad:").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_prod, textvariable=self.var_prod_unit).grid(row=2, column=1, sticky="ew", padx=5, pady=3)
        
        tb.Label(form_prod, text="Precio (S/):").grid(row=3, column=0, sticky="e", padx=5, pady=3)
        tb.Entry(form_prod, textvariable=self.var_prod_price).grid(row=3, column=1, sticky="ew", padx=5, pady=3)

        tb.Label(form_prod, text="Stock:").grid(row=4, column=0, sticky="e", padx=5, pady=3)
        entry_prod_stock = tb.Entry(form_prod, textvariable=self.var_prod_stock)
        entry_prod_stock.grid(row=4, column=1, sticky="ew", padx=5, pady=3)
        vcmd_stock = (self.register(lambda P: self.validate_numeric(P, 6)), "%P")
        entry_prod_stock.configure(validate="key", validatecommand=vcmd_stock)

        # Botones Productos
        btn_frame_prod = tb.Frame(form_prod)
        btn_frame_prod.grid(row=5, column=0, columnspan=2, pady=10)
        
        tb.Button(btn_frame_prod, text="➕ Nuevo", bootstyle="info-outline", command=self.product_ui.clear_product_form).pack(side="left", padx=5)
        tb.Button(btn_frame_prod, text="Limpiar", bootstyle="secondary", command=self.product_ui.clear_product_form).pack(side="left", padx=5)
        tb.Button(btn_frame_prod, text="💾 Guardar", bootstyle="success", command=self.product_ui.save_product_action).pack(side="left", padx=5)
        tb.Button(btn_frame_prod, text="📊 Importar Excel", bootstyle="warning-outline", command=self.product_ui.import_products_from_excel).pack(side="left", padx=5)

        # Cargar datos iniciales
        self.load_initial_data()
        
        # --- CONFIGURAR MAYÚSCULAS AUTOMÁTICAS ---
        self.setup_uppercase_entry(self.entry_search_client, self.entry_search_product)
        # --- CONFIGURAR MAYÚSCULAS AUTOMÁTICAS ---
        self.setup_uppercase_entry(self.entry_search_client, self.entry_search_product)
        self.setup_uppercase_entry(self.entry_client_name, self.entry_client_address)
        self.setup_uppercase_var(self.var_prod_code, self.var_prod_name, self.var_prod_unit)

    def load_initial_data(self):
        """Carga todos los clientes y productos al iniciar la vista."""
        try:
            # Cargar clientes (usando ClientUIManager)
            # Nota: ClientUIManager.filter_clients usa self.client_service.search_clients
            # y actualiza self.tree_clients.
            self.client_ui.filter_clients()
            
            # Cargar productos
            self.all_products_cache = self.product_service.search_products("")
            self.product_ui.filter_products()
        except Exception as e:
            print(f"Error loading initial data: {e}")
            self.all_products_cache = []

    def filter_products(self, event=None):
        """Filtra productos en tiempo real."""
        # Verificar que el caché exista
        if not hasattr(self, 'all_products_cache'):
            self.all_products_cache = []
            return
            
        query = self.entry_search_product.get().lower()
        if query == "buscar producto...":
            query = ""
        
        tree = self.tree_products
        for item in tree.get_children():
            tree.delete(item)

        for product in self.all_products_cache:
            code = str(product[1] or "").lower()
            name = str(product[2] or "").lower()

            if query in code or query in name:
                stock = product[5] if len(product) > 5 else None
                tag = self.product_ui._resolve_stock_tag(stock) if hasattr(self, "product_ui") else "stock_ok"
                stock_display = self.product_ui._format_stock_display(stock) if hasattr(self, "product_ui") else ("Sin control" if stock is None else str(stock))
                price_value = product[4]
                try:
                    price_display = f"{float(price_value):.2f}"
                except (TypeError, ValueError):
                    price_display = str(price_value or "0.00")

                tree.insert("", "end", values=(
                    product[0],
                    product[1],
                    product[2],
                    product[3],
                    price_display,
                    stock_display
                ), tags=(tag,))

    def on_product_select(self, event):
        """Llena el formulario al seleccionar un producto."""
        sel = self.tree_products.focus()
        if not sel:
            return
        
        values = self.tree_products.item(sel, "values")
        product_id = values[0]
        
        # Buscar datos completos en caché
        product = next((p for p in self.all_products_cache if str(p[0]) == str(product_id)), None)
        if product:
            self.var_prod_id.set(product[0])
            self.var_prod_code.set(product[1] or "")
            self.var_prod_name.set(product[2] or "")
            self.var_prod_unit.set(product[3] or "")
            self.var_prod_price.set(f"{product[4]:.2f}")

    def clear_product_form(self):
        """Limpia el formulario de productos."""
        self.var_prod_id.set("")
        self.var_prod_code.set("")
        self.var_prod_name.set("")
        self.var_prod_unit.set("")
        self.var_prod_price.set("")
        self.var_prod_stock.set("")
        # Deseleccionar en el tree
        for item in self.tree_products.selection():
            self.tree_products.selection_remove(item)

    def save_product_action(self):
        """Guarda o actualiza un producto."""
        product_id = self.var_prod_id.get()
        code = self.var_prod_code.get().strip()
        name = self.var_prod_name.get().strip()
        unit = self.var_prod_unit.get().strip()
        price_str = self.var_prod_price.get().strip()
        stock_str = self.var_prod_stock.get().strip()

        if not name or not unit or not price_str:
            self.show_warning("Error", "Nombre, Unidad y Precio son obligatorios.")
            return

        try:
            if product_id:
                self.product_service.update_product(int(product_id), name, unit, price_str, code or None, stock=stock_str)
                self.show_info("Éxito", "Producto actualizado correctamente.")
            else:
                self.product_service.create_product(name, unit, price_str, code or None, stock=stock_str)
                self.show_info("Éxito", "Producto creado correctamente.")

            # Recargar datos
            self.all_products_cache = self.product_service.search_products("")
            self.product_ui.filter_products()
            self.clear_product_form()
        except Exception as e:
            self.show_error("Error", str(e))


    def open_verify_window(self):
        """Abre ventana para verificar autenticidad de boletas mediante código QR."""
        win = tb.Toplevel(master=self)
        win.title("Verificar Autenticidad de Boleta")
        win.geometry("500x300")
        self.set_app_icon(win)
        self.center_window(win, 500, 300)
        self.make_modal(win)
        
        # Frame principal
        main_frame = tb.Frame(win, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        tb.Label(
            main_frame,
            text="🔍 Verificar Autenticidad",
            font=("Helvetica", 18, "bold"),
            bootstyle="info"
        ).pack(pady=20)
        
        # Instrucciones
        tb.Label(
            main_frame,
            text="Digite el código hash o escanee el código QR del comprobante:",
            font=("Helvetica", 11)
        ).pack(pady=10)
        
        # Entry para recibir el código escaneado o ingresado manualmente
        entry_serial = tb.Entry(
            main_frame,
            font=("Helvetica", 14),
            justify="center",
            width=30
        )
        entry_serial.pack(pady=20, ipady=10)
        entry_serial.focus_set()  # Focus automático para recibir el escaneo
        
        # Forzar mayúsculas
        self.setup_uppercase_entry(entry_serial)
        
        # Variable para resultado
        result_label = tb.Label(main_frame, text="", font=("Helvetica", 12))
        result_label.pack(pady=10)
        
        def verify_serial(event=None):
            """Verifica el código de seguridad escaneado."""
            serial_input = entry_serial.get().strip()
            
            if not serial_input:
                return
            
            # Limpiar el prefijo "VERIFICAR:" si viene del QR
            if serial_input.startswith("VERIFICAR:"):
                serial = serial_input.replace("VERIFICAR:", "")
            else:
                serial = serial_input
            
            # Buscar la venta por serial
            sale, items = self.sale_service.get_sale_by_serial(serial)
            
            if sale:
                # sale: (id, series, number, datetime, client_id, subtotal, igv, total, pdf_path, serial_seguridad, ...)
                sale_id, series, number, dt_str, client_id, subtotal, igv, total, pdf_path, serial_seg, *rest = sale
                
                # Obtener datos del cliente
                client = self.client_repo.get_client_by_id(client_id)
                client_name = client[2] if client else "N/A"
                
                # Mostrar mensaje de éxito
                success_msg = f"✅ BOLETA AUTÉNTICA\n\n"
                success_msg += f"Boleta: {series}-{int(number):06d}\n"
                success_msg += f"Cliente: {client_name}\n"
                success_msg += f"Monto: S/. {total:.2f}\n"
                success_msg += f"Fecha: {dt_str}"
                
                self.show_success("Boleta Verificada", success_msg)
                
                result_label.config(
                    text="✅ Boleta Auténtica",
                    bootstyle="success"
                )
                
                # Limpiar entry para siguiente escaneo
                entry_serial.delete(0, tk.END)
                
            else:
                # Boleta no encontrada - ALERTA
                print('\a')  # Sonido de alerta
                
                self.show_error("VERIFICACION FALLIDA", "⚠️ BOLETA NO VÁLIDA\n\nEl código no corresponde a ninguna boleta registrada.")
                
                result_label.config(
                    text="❌ Boleta No Válida",
                    bootstyle="danger"
                )
                
                # Limpiar entry
                entry_serial.delete(0, tk.END)
        
        # Bind Enter para verificar automáticamente
        entry_serial.bind("<Return>", verify_serial)
        
        # Botón manual de verificación
        tb.Button(
            main_frame,
            text="Verificar",
            bootstyle="primary",
            command=verify_serial,
            width=20
        ).pack(pady=10)

    def create_manual_backup(self):
        """Crea un backup manual del sistema (base de datos + PDFs + logos)."""
        import zipfile
        import shutil
        from datetime import datetime
        
        # Pedir dónde guardar el backup
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"BACKUP_PABLITO_POS_{timestamp}.zip"
        
        backup_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP Archive", "*.zip")],
            title="Guardar Backup",
            initialfile=default_name
        )
        
        if not backup_path:
            return  # Usuario canceló
        
        try:
            # Crear archivo ZIP
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 1. Agregar base de datos
                if os.path.exists(DB_PATH):
                    zipf.write(DB_PATH, "boletas.sqlite3")
                
                # 2. Agregar carpeta de PDFs
                if os.path.exists(PDF_DIR):
                    for root, dirs, files in os.walk(PDF_DIR):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join("pdfs", os.path.relpath(file_path, PDF_DIR))
                            zipf.write(file_path, arcname)
                
                # 3. Agregar carpeta de logos
                logo_dir = "logos"
                if os.path.exists(logo_dir):
                    for root, dirs, files in os.walk(logo_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join("logos", os.path.relpath(file_path, logo_dir))
                            zipf.write(file_path, arcname)
                
                # 4. Agregar archivo de información del backup
                import json
                backup_info = {
                    "version": "1.0",
                    "timestamp": timestamp,
                    "computer_name": os.environ.get('COMPUTERNAME', 'Unknown'),
                    "user": os.environ.get('USERNAME', 'Unknown')
                }
                zipf.writestr("backup_info.json", json.dumps(backup_info, indent=2))
            
            self.show_success(
                "Backup Creado", 
                f"Backup guardado exitosamente en:\n{backup_path}\n\nTamaño: {os.path.getsize(backup_path) / (1024*1024):.2f} MB"
            )
        
        except Exception as e:
            self.show_error("Error al crear backup", f"No se pudo crear el backup:\n{str(e)}")

    def restore_backup(self):
        """Restaura el sistema desde un archivo de backup."""
        import zipfile
        import shutil
        from datetime import datetime
        
        # Advertencia
        if not self.show_question(
            "⚠️ Restaurar Backup",
            "ADVERTENCIA: Esta acción reemplazará todos los datos actuales.\n\n"
            "Se creará un backup de seguridad antes de continuar.\n\n"
            "¿Desea proceder?"
        ):
            return
        
        # Seleccionar archivo de backup
        backup_path = filedialog.askopenfilename(
            filetypes=[("ZIP Archive", "*.zip")],
            title="Seleccionar Backup a Restaurar"
        )
        
        if not backup_path:
            return  # Usuario canceló
        
        try:
            # 1. Crear backup de seguridad del estado actual
            safety_backup = f"safety_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            
            with zipfile.ZipFile(safety_backup, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if os.path.exists(DB_PATH):
                    zipf.write(DB_PATH, "boletas.sqlite3")
                if os.path.exists(PDF_DIR):
                    for root, dirs, files in os.walk(PDF_DIR):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join("pdfs", os.path.relpath(file_path, PDF_DIR))
                            zipf.write(file_path, arcname)
            
            # 2. Validar el archivo ZIP
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Verificar que tenga la estructura correcta
                file_list = zipf.namelist()
                if "boletas.sqlite3" not in file_list:
                    raise Exception("El archivo ZIP no parece ser un backup válido (falta boletas.sqlite3)")
                
                # 3. Extraer contenido
                # Eliminar base de datos actual
                if os.path.exists(DB_PATH):
                    os.remove(DB_PATH)
                
                # Limpiar carpeta de PDFs
                if os.path.exists(PDF_DIR):
                    shutil.rmtree(PDF_DIR)
                os.makedirs(PDF_DIR, exist_ok=True)
                
                # Limpiar carpeta de logos
                if os.path.exists("logos"):
                    shutil.rmtree("logos")
                os.makedirs("logos", exist_ok=True)
                
                # Extraer archivos
                for file in file_list:
                    if file.startswith("pdfs/"):
                        zipf.extract(file, ".")
                    elif file.startswith("logos/"):
                        zipf.extract(file, ".")
                    elif file == "boletas.sqlite3":
                        zipf.extract(file, ".")
                        # Mover desde ubicación temporal a DB_PATH si es necesario
                        if os.path.exists("boletas.sqlite3") and not os.path.samefile("boletas.sqlite3", DB_PATH):
                            shutil.move("boletas.sqlite3", DB_PATH)
            
            self.show_success(
                "Restauración Completa",
                f"Backup restaurado exitosamente.\n\n"
                f"Se creó un backup de seguridad en:\n{safety_backup}\n\n"
                f"La aplicación se reiniciará ahora."
            )
            
            # Reiniciar la aplicación
            self.destroy()
            os.execl(sys.executable, sys.executable, *sys.argv)
        
        except Exception as e:
            self.show_error("Error al restaurar", f"No se pudo restaurar el backup:\n{str(e)}")
    
    def open_export_dialog(self):
        """Abre la ventana de exportación de datos con filtros."""
        win = tb.Toplevel(master=self)
        win.title("📊 Exportar Datos")
        win.geometry("500x680")
        self.set_app_icon(win)
        self.center_window(win, 500, 680)
        self.make_modal(win)

        body = self.create_scrollable_dialog_body(win, padding=20)
        
        # Variables
        data_type_var = tk.StringVar(value="clientes")
        format_var = tk.StringVar(value="excel")
        time_filter_var = tk.StringVar(value="all")
        date_from_var = tk.StringVar()
        date_to_var = tk.StringVar()
        
        # Header
        tb.Label(
            body,
            text="📊 Exportar Datos del Sistema",
            font=("Helvetica", 16, "bold"),
            bootstyle="primary"
        ).pack(pady=20)
        
        # Frame principal
        main_frame = tb.Frame(body, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Sección: Tipo de datos
        lf_type = tb.Labelframe(main_frame, text="Tipo de Datos", padding=15, bootstyle="info")
        lf_type.pack(fill="x", pady=(0, 15))
        
        tb.Radiobutton(lf_type, text="👥 Clientes", variable=data_type_var, value="clientes").pack(anchor="w", pady=3)
        tb.Radiobutton(lf_type, text="📦 Productos", variable=data_type_var, value="productos").pack(anchor="w", pady=3)
        tb.Radiobutton(lf_type, text="🧾 Ventas (Detalladas)", variable=data_type_var, value="ventas_detalladas").pack(anchor="w", pady=3)
        tb.Radiobutton(lf_type, text="📈 Resumen de Ventas", variable=data_type_var, value="ventas_resumen").pack(anchor="w", pady=3)
        
        # Sección: Formato
        lf_format = tb.Labelframe(main_frame, text="Formato de Exportación", padding=15, bootstyle="success")
        lf_format.pack(fill="x", pady=(0, 15))
        
        tb.Radiobutton(lf_format, text="📗 Excel (.xlsx)", variable=format_var, value="excel").pack(anchor="w", pady=3)
        tb.Radiobutton(lf_format, text="📄 PDF (Profesional)", variable=format_var, value="pdf").pack(anchor="w", pady=3)
        
        # Sección: Rango de fechas
        lf_time = tb.Labelframe(main_frame, text="Rango de Fechas", padding=15, bootstyle="warning")
        lf_time.pack(fill="x", pady=(0, 15))
        
        tb.Radiobutton(lf_time, text="⏱ Última hora", variable=time_filter_var, value="1h").pack(anchor="w", pady=3)
        tb.Radiobutton(lf_time, text="📅 Últimas 24 horas", variable=time_filter_var, value="24h").pack(anchor="w", pady=3)
        tb.Radiobutton(lf_time, text="📆 Última semana", variable=time_filter_var, value="7d").pack(anchor="w", pady=3)
        tb.Radiobutton(lf_time, text="📊 Último mes", variable=time_filter_var, value="30d").pack(anchor="w", pady=3)
        tb.Radiobutton(lf_time, text="🌐 Todos los registros", variable=time_filter_var, value="all").pack(anchor="w", pady=3)
        tb.Radiobutton(lf_time, text="✏️ Personalizado:", variable=time_filter_var, value="custom").pack(anchor="w", pady=3)
        
        # Fechas personalizadas
        custom_frame = tb.Frame(lf_time)
        custom_frame.pack(fill="x", padx=20, pady=5)
        
        tb.Label(custom_frame, text="Desde:").grid(row=0, column=0, sticky="w", padx=5)
        tb.Entry(custom_frame, textvariable=date_from_var, width=12).grid(row=0, column=1, padx=5)
        tb.Label(custom_frame, text="(YYYY-MM-DD)", font=("Arial", 8)).grid(row=0, column=2, sticky="w")
        
        tb.Label(custom_frame, text="Hasta:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        tb.Entry(custom_frame, textvariable=date_to_var, width=12).grid(row=1, column=1, padx=5)
        tb.Label(custom_frame, text="(YYYY-MM-DD)", font=("Arial", 8)).grid(row=1, column=2, sticky="w")
        
        # Botones
        btn_frame = tb.Frame(body, padding=20)
        btn_frame.pack(fill="x")
        
        def do_export():
            win.destroy()
            self.execute_export(
                data_type=data_type_var.get(),
                format_type=format_var.get(),
                time_filter=time_filter_var.get(),
                date_from=date_from_var.get(),
                date_to=date_to_var.get()
            )
        
        tb.Button(btn_frame, text="Cancelar", bootstyle="secondary", command=win.destroy, width=15).pack(side="left")
        tb.Button(btn_frame, text="📊 Exportar", bootstyle="success", command=do_export, width=15).pack(side="right")
    
    def execute_export(self, data_type, format_type, time_filter, date_from, date_to):
        """Ejecuta la exportación según los parámetros seleccionados."""
        # 1. Calcular rango de fechas
        start_dt, end_dt = self.calculate_date_range(time_filter, date_from, date_to)
        
        # 2. Obtener datos según data_type
        headers = []
        data = []
        title = f"REPORTE DE {data_type.upper().replace('_', ' ')}"
        
        try:
            if data_type == "clientes":
                rows = self.client_service.search_clients("")
                headers = ["ID", "DNI", "Nombre", "Teléfono", "Email", "Dirección"]
                for r in rows:
                    data.append({
                        "id": r[0], "dni": r[1], "nombre": r[2], 
                        "telefono": r[3], "email": r[4], "direccion": r[5]
                    })
            
            elif data_type == "productos":
                rows = self.product_service.search_products("")
                headers = ["ID", "Código", "Nombre", "Unidad", "Precio"]
                for r in rows:
                    data.append({
                        "id": r[0], "codigo": r[1], "nombre": r[2], 
                        "unidad": r[3], "precio": f"{r[4]:.2f}"
                    })

            elif data_type == "ventas_detalladas" or data_type == "ventas_resumen":
                # Nota: ventas_resumen podría ser diferente, pero por ahora usaremos el detallado
                rows = self.sale_service.search_sales_by_client("")
                headers = ["Serie-Corr.", "Fecha", "Cliente", "DNI/RUC", "Total"]
                
                for r in rows:
                    # r: id, series, number, datetime, total, full_name, dni
                    sale_dt = r[3] # string YYYY-MM-DD HH:MM:SS
                    if self.is_date_in_range(sale_dt, start_dt, end_dt):
                        data.append({
                            "serie": f"{r[1]}-{int(r[2]):06d}",
                            "fecha": r[3],
                            "cliente": r[5],
                            "dni": r[6],
                            "total": f"{r[4]:.2f}"
                        })
            
            if not data:
                self.show_warning("Sin datos", "No se encontraron registros para exportar con los filtros seleccionados.")
                return

            # 3. Pedir archivo
            ext = ".xlsx" if format_type == "excel" else ".pdf"
            file_types = [("Excel", "*.xlsx")] if format_type == "excel" else [("PDF", "*.pdf")]

            def slugify(value):
                value = (value or "").lower()
                chars = []
                for ch in value:
                    if ch.isalnum():
                        chars.append(ch)
                    elif ch in ("-", "_"):
                        chars.append(ch)
                    else:
                        chars.append("_")
                cleaned = "".join(chars).strip("_")
                return cleaned or "datos"

            def build_range_label():
                if time_filter == "all":
                    return "todos"
                if time_filter == "custom":
                    if start_dt != datetime.min and end_dt != datetime.max:
                        return f"{start_dt.strftime('%Y%m%d')}_a_{end_dt.strftime('%Y%m%d')}"
                    df = (date_from or "").strip()
                    dt = (date_to or "").strip()
                    if df and dt:
                        return f"{df}_a_{dt}"
                    if df:
                        return f"desde_{df}"
                    if dt:
                        return f"hasta_{dt}"
                    return "personalizado"
                shortcuts = {
                    "1h": "ultima_hora",
                    "24h": "24h",
                    "7d": "7dias",
                    "30d": "30dias"
                }
                return shortcuts.get(time_filter, time_filter)

            type_slug = slugify(data_type)
            range_slug = slugify(build_range_label())
            timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M")
            suggested_name = f"informe_{type_slug}"
            if range_slug:
                suggested_name += f"_{range_slug}"
            suggested_name += f"_{timestamp_slug}{ext}"
            suggested_name = suggested_name.replace("__", "_")

            filename = filedialog.asksaveasfilename(
                defaultextension=ext,
                filetypes=file_types,
                title=f"Guardar Reporte {data_type}",
                initialfile=suggested_name
            )
            
            if not filename:
                return

            # 4. Generar
            company_info = self.current_company_data or {}
            company_dict = {
                "name": company_info.get("name", "Mi Empresa"),
                "ruc": company_info.get("ruc", ""),
                "address": company_info.get("address", ""),
                "footer_message": company_info.get("footer_message", "")
            }

            if format_type == "excel":
                generar_reporte.generate_excel(filename, title, headers, data, company_dict)
            else:
                generar_reporte.generate_pdf(filename, title, headers, data, company_dict)
                
            self.show_success("Éxito", f"Reporte guardado en:\n{filename}")
            if os.name == "nt":
                try:
                    os.startfile(filename)
                except:
                    pass

        except Exception as e:
            self.show_error("Error", f"Error al exportar:\n{e}")

    def calculate_date_range(self, time_filter, date_from, date_to):
        now = datetime.now()
        if time_filter == "1h":
            return now - timedelta(hours=1), now
        elif time_filter == "24h":
            return now - timedelta(hours=24), now
        elif time_filter == "7d":
            return now - timedelta(days=7), now
        elif time_filter == "30d":
            return now - timedelta(days=30), now
        elif time_filter == "all":
            return datetime.min, datetime.max
        elif time_filter == "custom":
            try:
                start = datetime.strptime(date_from + " 00:00:00", "%Y-%m-%d %H:%M:%S")
                end = datetime.strptime(date_to + " 23:59:59", "%Y-%m-%d %H:%M:%S")
                return start, end
            except:
                return datetime.min, datetime.max
        return datetime.min, datetime.max

    def is_date_in_range(self, date_str, start_dt, end_dt):
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            return start_dt <= dt <= end_dt
        except:
            return False



    def import_products_from_excel(self):
        """Importa productos desde un archivo Excel."""
        try:
            import pandas as pd
        except ImportError:
            self.show_error("Error", "La librería 'pandas' no está instalada.\nEjecuta: pip install pandas openpyxl")
            return

        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo Excel",
            filetypes=[("Excel files", "*.xlsx;*.xls")]
        )
        
        if not file_path:
            return

        try:
            df = pd.read_excel(file_path)
            
            # Verificar columnas requeridas
            required_columns = ['Nombre', 'Unidad', 'Precio']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                self.show_error("Error", f"El archivo Excel debe tener las columnas: {', '.join(required_columns)}.\nFaltan: {', '.join(missing_columns)}")
                return
            
            # Procesar filas
            success_count = 0
            error_count = 0
            
            for _, row in df.iterrows():
                try:
                    name = str(row['Nombre']).strip()
                    unit = str(row['Unidad']).strip()
                    price = float(row['Precio'])
                    code = str(row['Código']).strip() if 'Código' in df.columns and not pd.isna(row['Código']) else ""
                    
                    if not name or not unit:
                        error_count += 1
                        continue
                        
                    self.product_service.create_product(name, unit, price, code)
                    success_count += 1
                except Exception:
                    error_count += 1
            
            # Recargar productos
            self.all_products_cache = self.product_service.search_products("")
            self.filter_products()
            
            msg = f"Importación completada.\nImportados: {success_count}\nErrores: {error_count}"
            self.show_info("Resultado Importación", msg)
            
        except Exception as e:
            self.show_error("Error de Importación", f"Ocurrió un error al leer el archivo:\n{str(e)}")

if __name__ == "__main__":
    init_db()
    app = App()
    app.mainloop()
