import ctypes
import hashlib
import os
import shutil
import sys
import subprocess
import uuid
import tempfile
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import filedialog, simpledialog, ttk
from typing import Any, Optional, List, Callable, cast
import ttkbootstrap as tb
from ttkbootstrap.dialogs import Messagebox
import threading

from PIL import Image, ImageTk
import random
import string
import json
import socket
import errno
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
import settings
from settings import (
    APPDATA_PATH,
    PDF_DIR,
    BACKUP_DIR,
    IGV_PORCENTAJE,
    SECURITY_MASTER_SECRET,
)
from utils import (
    build_whatsapp_message,
    configure_logging,
    create_guarded_backup,
    ensure_country_prefix,
    format_phone_display,
    generar_reporte,
    is_valid_email,
    normalize_phone_number,
)

from app_core.email_templates import generate_email_html
from app_core.logging_setup import setup_error_logging
from app_core.ui_helpers import TooltipManager
from app_ui.security import SecurityUI
from app_ui.profiles import ProfileSelectionUI
from app_ui.messages import MessageUI
from app_ui.effects import EffectsUI
from app_ui.hotkeys import HotkeyUI
from app_ui.backups import BackupsUI
from ui.ui_export import ExportUIManager


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
    FiadoRepository,
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
    FiadoService,
    SecurityService,
)
from services.storage_guard import StorageGuardian, StorageGuardianError, UnlockResult
from services.pairing_server import PairingServer
from ui import (
    CustomerDisplayManager,
    ClientUIManager,
    DashboardUIManager,
    HistoryUIManager,
    FiadosUIManager,
    ProductUIManager,
    SalesUIHelpers,
    SalesUIHelpers,
    SalesUIManager,
)
from ui.splash_screen import SplashScreen

NAV_ITEMS = [
    {"key": "dashboard", "label": "Dashboard", "view": "dashboard", "style": "base"},
    {"key": "sales", "label": "Ventas", "view": "sales", "style": "base"},
    {"key": "fiados", "label": "Fiados", "view": "fiados", "style": "base"},
    {"key": "boletin", "label": "Boletín", "view": "boletin", "style": "base"},
    {"key": "update", "label": "Actualizar Info", "view": "update", "style": "base"},
    {"key": "history", "label": "Historial de comprobantes", "view": "history", "style": "base"},
    {"key": "verify", "label": "🔍 Verificar Comprobante", "view": None, "style": "danger-outline"},
    {"key": "export", "label": "📊 Exportar (informe)", "view": "export", "style": "info-outline"},
]

CONFIGURABLE_NAV_KEYS = [item["key"] for item in NAV_ITEMS if item["key"] != "dashboard"]
NAV_ITEMS_BY_KEY = {item["key"]: item for item in NAV_ITEMS}

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


_INSTANCE_SOCKET = None


def acquire_single_instance(port: int = 54219) -> bool:
    """Impide múltiples instancias: abre un socket exclusivo; si falla, ya hay una instancia."""
    global _INSTANCE_SOCKET
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", port))
        s.listen(1)
        _INSTANCE_SOCKET = s
        return True
    except OSError as exc:
        if exc.errno in (errno.EADDRINUSE, errno.WSAEADDRINUSE if hasattr(errno, "WSAEADDRINUSE") else None):
            return False
        return False

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
    title_label: Any = None
    current_company_data: Optional[dict] = None
    main_logo_image: Any = None
    entry_client_search: Any = None
    entry_product_catalog_search: Any = None
    undo_last_client: Optional[tuple] = None
    undo_last_product: Optional[tuple] = None
    entry_search_prod: Any = None
    entry_search_cli: Any = None
    tooltip_manager: TooltipManager
    security_ui: SecurityUI
    profile_ui: ProfileSelectionUI
    message_ui: MessageUI
    effects_ui: EffectsUI
    hotkeys_ui: HotkeyUI
    backups_ui: BackupsUI
    holiday_overlay: Optional[object]
    storage_guard: Optional[StorageGuardian]
    _storage_unlock: Optional[UnlockResult]
    _storage_unlock_via_master: bool = False
    _storage_new_fingerprint: Optional[str] = None
    _runtime_plain_dir: Optional[str] = None
    _plain_db_path: Optional[str] = None

    def __init__(self):
        super().__init__(themename="cyborg")
        self.withdraw()  # Ocultar ventana principal durante carga
        
        # Mostrar Splash Screen
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
        self.splash = SplashScreen(self, logo_path=logo_path)
        self.splash.update_status("Cargando componentes del sistema...")
        
        self.title("Sistema de Emisión de Comprobantes - PABLITO_POS")
        self._base_title = self.title()
        self._holiday_mode = False
        self.holiday_features_enabled = False  # Post-navidad: decoración desactivada pero código conservado
        self.decoration_mode = "lights"  # lights | ribbon
        self.decoration_speed_ms = 500
        self.geometry("1100x650")
        self.minsize(1000, 600)
        self.set_app_icon(self)
        self.center_window(self, 1100, 650)

        # Crear un archivo 'señuelo' visible en la carpeta del proyecto
        try:
            settings.create_decoy_db()
        except Exception:
            pass

        self.storage_guard = None
        self._storage_unlock = None
        self._storage_unlock_via_master = False
        self._storage_new_fingerprint = None
        self._runtime_plain_dir = None
        self._plain_db_path = None
        # Mapping pairing_id -> waiter info for open QR modals so the
        # PairingServer can notify the UI to auto-fill and submit the code.
        # Each entry: { 'win': Toplevel, 'code_var': StringVar, 'on_submit': Callable }
        self._pairing_ui_waiters: dict[str, dict] = {}

        try:
            self.splash.update_status("Verificando seguridad y cifrado...")
            self._initialize_storage_guard()
        except StorageGuardianError as exc:
            self.splash.destroy()
            Messagebox.show_error(
                title="Bloqueo de seguridad",
                message=str(exc),
                parent=self,
            )
            self.destroy()
            raise SystemExit(1)
        except Exception as exc:  # pragma: no cover - defensive
            self.splash.destroy()
            Messagebox.show_error(
                title="Error de seguridad",
                message=f"No se pudo preparar el entorno cifrado:\n{exc}",
                parent=self,
            )
            self.destroy()
            raise SystemExit(1)

        try:
            self.splash.update_status("Conectando base de datos...")
            init_db()
        except Exception as exc:  # pragma: no cover - defensive
            self.splash.destroy()
            Messagebox.show_error(
                title="Inicialización fallida",
                message=f"No se pudo preparar la base de datos:\n{exc}",
                parent=self,
            )
            self.destroy()
            raise SystemExit(1)

        # Inicializar UI Managers
        self.splash.update_status("Cargando interfaz de usuario...")
        self.client_ui = ClientUIManager(self)
        self.product_ui = ProductUIManager(self)
        self.sales_ui = SalesUIManager(self)
        self.export_ui = ExportUIManager(self)

        # Estilo extra
        style = tb.Style()
        style.configure("Treeview", rowheight=24)

        # Capa de datos / servicios
        self.splash.update_status("Iniciando servicios...")
        db = Database(self._runtime_db_path())
        self.company_repo = CompanyRepository(db)
        self.client_repo = ClientRepository(db)
        self.product_repo = ProductRepository(db)
        self.sale_repo = SaleRepository(db)
        self.fiado_repo = FiadoRepository(db)
        self.settings_repo = SettingsRepository(db)

        self.company_service = CompanyService(self.company_repo)
        self.client_service = ClientService(self.client_repo)
        self.product_service = ProductService(self.product_repo)
        self.settings_service = SecurityService(self.settings_repo)
        self.sale_service = SaleService(self.sale_repo, self.client_repo, self.settings_service)
        self.pdf_service = PdfService(self.company_service, self.client_repo, self.sale_repo)
        self.fiado_service = FiadoService(self.fiado_repo, self.pdf_service, self.sale_service, self.product_service)
        self.comm_service = CommunicationService()
        self.customer_display = CustomerDisplayManager(self, self.settings_repo)

        # Start local pairing HTTP server (listening on localhost by default)
        try:
            self.splash.update_status("Iniciando servidor local...")
            # Bind en 0.0.0.0 para aceptar conexiones desde la LAN cuando sea necesario.
            self._pairing_server = PairingServer(self, host="0.0.0.0", port=8000)
            self._pairing_server.start()
        except Exception:
            # Si falla (probablemente firewall o puerto ocupado), intentamos aplicar el fix
            # y reintentamos una vez mas.
            try:
                print("[App] Fallo al iniciar servidor de emparejamiento. Intentando Auto-Fix Firewall...")
                fix_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fix_firewall.ps1")
                if os.path.exists(fix_script):
                    import subprocess
                    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", fix_script], check=False)
                    # Reintentar
                    self._pairing_server = PairingServer(self, host="0.0.0.0", port=8000)
                    self._pairing_server.start()
            except Exception as e:
                print(f"[App] No se pudo iniciar el servidor de emparejamiento: {e}")
                self._pairing_server = None

        if self._storage_unlock_via_master:
            try:
                fingerprint = self._storage_new_fingerprint or "unknown"
                self.settings_service.audit_log(
                    "STORAGE_UNLOCK_MASTER",
                    f"Huella autorizada: {fingerprint}",
                )
            except Exception:
                pass

        self.current_client = None
        self.selected_product = None
        self.sale_items = []
        self.last_pdf_path = None
        self.series = "B001"
        self.proforma_series = "PF001"
        self.boletin_series = "BL001"
        self.sales_mode = "sale"  # sale | boletin
        self.entry_search_prod = None
        self.entry_search_cli = None
        self._debounce_jobs: dict[str, Any] = {}
        self.loading_overlay: Optional[tb.Toplevel] = None
        self._loading_progress: Optional[tb.Progressbar] = None
        self._active_view = "dashboard"
        self._mousewheel_bound = False
        self.tooltip_manager = TooltipManager(self)
        self.security_ui = SecurityUI(self)
        self.profile_ui = ProfileSelectionUI(self)
        self.effects_ui = EffectsUI(self)
        self.message_ui = MessageUI(self)
        self.hotkeys_ui = HotkeyUI(self)
        self.backups_ui = BackupsUI(self)
        self._holiday_overlay: Optional[object] = None
        
        # Waiters for async UI updates (LAN pairing/recovery)
        self._recovery_ui_waiters: dict[str, dict] = {}
        
        self.splash.update_status("Finalizando carga...")
        self.show_profile_selection()

        # Configurar Atajos de Teclado (Hotkeys)
        self.hotkeys_ui.setup_hotkeys()

        # Compatibilidad global con rueda del ratón
        self.hotkeys_ui.setup_global_mousewheel_support()

        # Verificar si se usa el PIN por defecto (1234) y forzar cambio
        stored_pin = self.settings_repo.get_pin()
        default_pin = False
        if stored_pin == "1234":
            default_pin = True
        else:
            default_pin, _ = self.settings_service.verify_pin(
                "1234", context="DEFAULT_PIN_CHECK", record_attempt=False
            )
        if default_pin:
            self.after(1000, self.open_force_change_pin_window)
        
        # Cerrar Splash Screen y mostrar ventana principal
        self.splash.finish()

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
        try:
            if host.state() != "withdrawn":
                window.transient(host)
        except Exception:
            window.transient(host)
        window.lift()
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

    # ------------------------------------------------------------------
    # Guardián de almacenamiento (cifrado local)
    # ------------------------------------------------------------------
    def _initialize_storage_guard(self) -> None:
        print("[App] StorageGuardian desactivado para desarrollo local.")
        # Usar la base de datos por defecto sin cifrado
        plain_path = settings.DEFAULT_DB_PATH
        settings.set_db_path(plain_path)
        
        self.storage_guard = None
        self._storage_unlock = None
        self._plain_db_path = plain_path

    def _handle_storage_hardware_mismatch(
        self,
        guard: StorageGuardian,
        _original_error: StorageGuardianError | None = None,
    ) -> UnlockResult:
        # Nuevo flujo: generar una solicitud de emparejamiento (QR) y verificar
        # el código OTP de 4 dígitos. Control de intentos: 5 intentos máximos,
        # bloqueo por 1 hora si se exceden.
        fingerprint = guard.hardware_fingerprint()

        pairing = self._create_pairing_request(fingerprint)

        try:
            unlock = self._show_pairing_qr_and_wait(guard, pairing)
        except StorageGuardianError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise StorageGuardianError(f"Error en el flujo de emparejamiento: {exc}") from exc

        return unlock

    # -------------------- Pairing helpers --------------------
    def _pairings_file_path(self) -> str:
        return os.path.join(APPDATA_PATH, "pairings.json")

    def _load_pairings(self) -> dict:
        path = self._pairings_file_path()
        try:
            if not os.path.exists(path):
                return {}
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh) or {}
        except Exception:
            return {}

    def _save_pairings(self, data: dict) -> None:
        path = self._pairings_file_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
        except Exception:
            pass

    def _create_pairing_request(self, fingerprint: str, ttl_minutes: int = 10) -> dict:
        now = datetime.utcnow()
        issued_at = now.isoformat() + "Z"
        expire_at = (now + timedelta(minutes=ttl_minutes)).isoformat() + "Z"
        pid = uuid.uuid4().hex
        entry = {
            "id": pid,
            "fingerprint": fingerprint,
            "issued_at": issued_at,
            "expire_at": expire_at,
            "attempts": 0,
            "blocked_until": None,
        }
        data = self._load_pairings()
        data[pid] = entry
        self._save_pairings(data)
        return entry

    def _update_pairing(self, pid: str, updates: dict) -> None:
        data = self._load_pairings()
        entry = data.get(pid)
        if not entry:
            return
        entry.update(updates)
        data[pid] = entry
        self._save_pairings(data)

    def _show_pairing_qr_and_wait(self, guard: StorageGuardian, pairing: dict) -> UnlockResult:
        # Construir payload para QR
        # Determinar URL LAN accesible y añadirla al payload del QR para que
        # la app móvil pueda intentar la confirmación automáticamente.
        def _get_local_ip() -> str:
            # Intentar obtener la IP real conectando a un DNS público (no envía datos)
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(0.1)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except Exception:
                pass
            
            # Fallback: iterar interfaces
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "127.0.0.1"

        local_ip = _get_local_ip()
        port = getattr(self, "_pairing_server", None) and getattr(self._pairing_server, "port", 8000) or 8000
        server_url = f"http://{local_ip}:{port}"

        # Log para depuración
        print(f"[Pairing] Generando QR con Server URL: {server_url}")

        payload = {
            "pairing_id": pairing["id"],
            "fingerprint": pairing["fingerprint"],
            "issued_at": pairing["issued_at"],
            "server_url": server_url,
        }
        payload_text = json.dumps(payload, separators=(",", ":"))

        # Modal con QR y campo para ingresar código
        win = tb.Toplevel(master=self)
        self.begin_modal_construction(win)
        win.title("Autorizar nuevo equipo")
        # Larger and wider modal so the form stays fully visible on high DPI and landscape screens.
        win.geometry("720x560")
        win.minsize(720, 560)
        win.resizable(True, True)
        self.set_app_icon(win)

        # Scrollable body so the manual code input is always reachable even if DPI/zoom clips the view.
        container = tb.Frame(win)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        vscroll = tb.Scrollbar(container, orient="vertical", command=canvas.yview)
        body = tb.Frame(canvas, padding=12)

        body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=vscroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        def _bind_mousewheel(target: tk.Misc) -> None:
            target.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
            target.bind_all("<Button-4>", lambda _e: canvas.yview_scroll(-1, "units"))
            target.bind_all("<Button-5>", lambda _e: canvas.yview_scroll(1, "units"))

        _bind_mousewheel(win)

        tb.Label(body, text="Escanea este QR con tu app móvil para generar el código de 4 dígitos (La app intentará usar la red local o USB para confirmar automáticamente)", bootstyle="info").pack(pady=(6, 8))

        qr_holder = tb.Label(body, text="(QR no disponible)")
        qr_holder.pack(pady=6)

        if qrcode is not None:
            try:
                img = qrcode.make(payload_text)
                # Not all qrcode backends return a PIL image in every env; guard resize
                if hasattr(img, "resize"):
                    try:
                        img = img.resize((260, 260), Image.Resampling.LANCZOS)
                    except Exception:
                        img = img.resize((260, 260))
                photo = ImageTk.PhotoImage(img)
                qr_holder.configure(image=photo, text="")
                # keep reference on the Toplevel in a Pylance-friendly way
                setattr(win, "_qr_photo", photo)
            except Exception:
                qr_holder.configure(text=payload_text)
        else:
            qr_holder.configure(text=payload_text)
        # Mostrar URL accesible en la LAN para la app móvil (la misma incluida en el QR)
        tb.Label(body, text=f"IP Local detectada: {local_ip}\nURL para móvil: {server_url}", wraplength=420, bootstyle="info").pack(pady=(8, 6))
        def _copy_url():
            try:
                self.clipboard_clear()
                self.clipboard_append(server_url)
                self.show_toast("Copiado", f"URL copiada al portapapeles: {server_url}")
            except Exception:
                pass

        tb.Button(body, text="Copiar URL para móvil", bootstyle="secondary-outline", command=_copy_url).pack(pady=(0, 6))

        tb.Label(body, text="Ingrese el código de 4 dígitos generado por la app móvil:").pack(pady=(10, 2))
        code_var = tk.StringVar()
        vcmd = (self.register(lambda P: self.validate_alphanum(P, 4)), "%P")
        entry = tb.Entry(body, textvariable=code_var, font=("Segoe UI", 18), justify="center", validate="key", validatecommand=vcmd)
        entry.pack(pady=(2, 8))
        entry.focus_set()

        status_label = tb.Label(body, text="", bootstyle="secondary")
        status_label.pack(pady=(6, 4))

        result: dict = {"unlock": None}

        def _on_submit():
            code = (code_var.get() or "").strip().upper()
            if not code:
                status_label.configure(text="Ingrese el código de 4 dígitos.")
                return
            try:
                unlock = self._verify_pairing_code(guard, pairing["id"], code)
            except StorageGuardianError as exc:
                status_label.configure(text=str(exc))
                return
            result["unlock"] = unlock
            # cleanup waiter mapping if present
            try:
                self._pairing_ui_waiters.pop(pairing["id"], None)
            except Exception:
                pass
            win.destroy()

        def _on_cancel():
            try:
                self._pairing_ui_waiters.pop(pairing["id"], None)
            except Exception:
                pass
            win.destroy()

        btn_frame = tb.Frame(body)
        btn_frame.pack(pady=(8, 6))
        tb.Button(btn_frame, text="Cancelar", bootstyle="secondary", command=_on_cancel).pack(side="right", padx=6)
        tb.Button(btn_frame, text="Verificar código", bootstyle="success", command=_on_submit).pack(side="right", padx=6)

        self.reveal_modal(win)
        self.make_modal(win)
        entry.bind("<Return>", lambda _e: _on_submit())
        win.bind("<Escape>", lambda _e: _on_cancel())
        # Visual hint for default action
        try:
            entry.configure(bootstyle="primary")
        except Exception:
            pass
        # Register UI waiter so external confirm (from mobile via PairingServer)
        # can auto-fill and submit the code into this dialog.
        try:
            self._pairing_ui_waiters[pairing["id"]] = {
                "win": win,
                "code_var": code_var,
                "on_submit": _on_submit,
            }
        except Exception:
            pass

        self.wait_window(win)

        unlock = result.get("unlock")
        if not unlock:
            raise StorageGuardianError("Autorización cancelada o no completada.")
        return unlock

    def _notify_pairing_confirmed(self, pairing_id: str, otp: str) -> None:
        """Called by the local PairingServer when a mobile app posts a
        successful confirmation. If a QR dialog is open for `pairing_id`
        this will auto-fill the code field and trigger submission.
        Must use `after` to interact with Tk from another thread.
        """
        waiter = self._pairing_ui_waiters.get(pairing_id)
        if not waiter:
            return

        def _fill_and_submit():
            try:
                code_var = waiter.get("code_var")
                on_submit = waiter.get("on_submit")
                if code_var and hasattr(code_var, "set"):
                    code_var.set(otp)
                # call submit callback (same thread) so the dialog logic runs
                if callable(on_submit):
                    on_submit()
            except Exception:
                pass
            finally:
                try:
                    self._pairing_ui_waiters.pop(pairing_id, None)
                except Exception:
                    pass

        try:
            self.after(10, _fill_and_submit)
        except Exception:
            # fallback if after isn't available
            _fill_and_submit()

    def _notify_recovery_confirmed(self, challenge: str, response: str) -> None:
        """Called by the local PairingServer when a mobile app posts a
        successful recovery confirmation.
        """
        print(f"[DEBUG] Notificacion recibida para challenge: '{challenge}'")
        print(f"[DEBUG] Waiters activos: {list(self._recovery_ui_waiters.keys())}")
        
        waiter = self._recovery_ui_waiters.get(challenge)
        if not waiter:
            print("[DEBUG] ERROR: No se encontro waiter para este challenge.")
            return

        print("[DEBUG] Waiter encontrado. Ejecutando callback...")
        def _do_callback():
            try:
                on_success = waiter.get("on_success")
                if callable(on_success):
                    on_success(response)
            except Exception as e:
                print(f"[DEBUG] Error en callback UI: {e}")
            finally:
                try:
                    self._recovery_ui_waiters.pop(challenge, None)
                except Exception:
                    pass

        try:
            self.after(10, _do_callback)
        except Exception:
            _do_callback()

    def _verify_pairing_code(self, guard: StorageGuardian, pid: str, code: str) -> UnlockResult:
        data = self._load_pairings()
        entry = data.get(pid)
        if not entry:
            raise StorageGuardianError("Solicitud de emparejamiento no encontrada o expirada.")

        now = datetime.utcnow()
        blocked_until = entry.get("blocked_until")
        if blocked_until:
            try:
                bu = datetime.fromisoformat(blocked_until.replace("Z", "+00:00"))
                if now < bu:
                    remaining = bu - now
                    mins = int(remaining.total_seconds() // 60) + 1
                    raise StorageGuardianError(f"Demasiados intentos. Intente nuevamente en {mins} minutos.")
            except Exception:
                pass

        expire_at = entry.get("expire_at")
        if expire_at:
            try:
                ea = datetime.fromisoformat(expire_at.replace("Z", "+00:00"))
                if now > ea:
                    # eliminar
                    data.pop(pid, None)
                    self._save_pairings(data)
                    raise StorageGuardianError("Solicitud expirada. Genera un nuevo QR.")
            except Exception:
                pass

        expected = self._compute_storage_emergency_code(entry["fingerprint"]) or ""
        if code.strip().upper() != expected:
            # fallo
            attempts = int(entry.get("attempts", 0)) + 1
            updates = {"attempts": attempts}
            if attempts >= 5:
                blocked_until_ts = (now + timedelta(hours=1)).isoformat() + "Z"
                updates["blocked_until"] = blocked_until_ts
            self._update_pairing(pid, updates)
            remaining = max(0, 5 - attempts)
            if remaining <= 0:
                raise StorageGuardianError("Código inválido. Se han excedido los intentos; intento bloqueado por 1 hora.")
            raise StorageGuardianError(f"Código inválido. Intentos restantes: {remaining}.")

        # éxito: desbloquear con master y actualizar locks
        unlock = guard.unlock_with_master()
        guard.refresh_hardware_lock(key=unlock.key, new_fingerprint=entry["fingerprint"])
        guard.refresh_mobile_lock(key=unlock.key)
        # eliminar pairing
        data.pop(pid, None)
        self._save_pairings(data)

        self._storage_unlock_via_master = True
        self._storage_new_fingerprint = entry["fingerprint"]
        return unlock

    @staticmethod
    def _compute_storage_emergency_code(fingerprint: str) -> str:
        payload = f"{fingerprint}|{SECURITY_MASTER_SECRET}|AUTHV1"
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()
        return digest[:4]

    def _runtime_db_path(self) -> str:
        if not self._plain_db_path:
            raise StorageGuardianError("La base de datos desencriptada no está disponible.")
        return self._plain_db_path

    def _allocate_runtime_db_path(self) -> str:
        base_dir = os.path.join(APPDATA_PATH, "runtime_plain")
        os.makedirs(base_dir, exist_ok=True)
        self._mark_path_hidden(base_dir)
        
        # Eliminamos la limpieza automática para evitar borrar datos por error.
        # self._cleanup_stale_runtime_dirs(base_dir)

        # Usamos siempre la carpeta "current" para máxima persistencia.
        session_dir = os.path.join(base_dir, "current")
        os.makedirs(session_dir, exist_ok=True)
        self._mark_path_hidden(session_dir)
        self._runtime_plain_dir = session_dir

        target_db = os.path.join(session_dir, settings.DEFAULT_DB_FILENAME)

        # Migrar DB antigua si existe junto al exe/script y aún no se copió a APPDATA.
        if not os.path.exists(target_db):
            legacy_candidates = [
                os.path.join(os.path.dirname(sys.executable), settings.DEFAULT_DB_FILENAME) if hasattr(sys, "executable") else "",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), settings.DEFAULT_DB_FILENAME),
            ]
            for cand in legacy_candidates:
                if cand and os.path.exists(cand):
                    try:
                        shutil.copy2(cand, target_db)
                        print(f"[Storage] Migrada base de datos legacy desde {cand} a {target_db}")
                        break
                    except Exception as exc:
                        print(f"[Storage] No se pudo migrar DB legacy desde {cand}: {exc}")

        return target_db

    def _cleanup_stale_runtime_dirs(self, base_dir: str) -> None:
        # DESACTIVADO: No borrar nada automáticamente para proteger la DB.
        pass

    @staticmethod
    def _mark_path_hidden(path: str) -> None:
        if os.name != "nt":
            return
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(path)
            if attrs == -1:
                return
            hidden_flag = 0x02
            if attrs & hidden_flag:
                return
            ctypes.windll.kernel32.SetFileAttributesW(path, attrs | hidden_flag)
        except Exception:
            pass

    def _maybe_prompt_daily_guarded_backup(self) -> None:
        guard = self.storage_guard
        unlock = self._storage_unlock
        if not guard or not unlock:
            return

        # Ejecutar backup automático una vez por día (primera apertura del día).
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            last_prompt = self.settings_repo.get_setting("last_guarded_backup_date", "")
        except Exception:
            last_prompt = ""
        if last_prompt == today:
            return

        # Mostrar overlay de proceso y ejecutar el backup (mejor experiencia
        # visual consistente con la app en modo claro/oscuro).
        try:
            self.show_loading("Generando backup cifrado...")
            backup_path = self._perform_guarded_backup()
            try:
                self.settings_repo.set_setting("last_guarded_backup_date", today)
            except Exception:
                pass
            # Mostrar resultado con estilo de la aplicación
            self.hide_loading()
            self.show_success("Backup cifrado listo", f"Archivo: {backup_path}", use_toast=True)
        except Exception as exc:
            try:
                self.hide_loading()
            except Exception:
                pass
            self.show_error("Backup no completado", f"No se pudo crear la copia cifrada:\n{exc}")

    def _perform_guarded_backup(self) -> str:
        guard = self.storage_guard
        unlock = self._storage_unlock
        if not guard or not unlock:
            raise StorageGuardianError("El guardián de almacenamiento no está disponible.")

        plain_path = self._runtime_db_path()
        guard.encrypt_database_from_plain(plain_path=plain_path, key=unlock.key)
        artifacts = [
            (guard.db_encrypted_path, StorageGuardian.DB_ENCRYPTED_NAME),
            (guard.hw_lock_path, StorageGuardian.HW_LOCK_NAME),
            (guard.mobile_lock_path, StorageGuardian.MOBILE_LOCK_NAME),
        ]
        backup_path = create_guarded_backup(artifacts=artifacts)
        try:
            self.settings_service.audit_log(
                "STORAGE_BACKUP",
                f"Copia cifrada creada: {os.path.basename(backup_path)}",
            )
        except Exception:
            pass
        return backup_path

    def _on_app_close(self) -> None:
        self.destroy()

    def _reencrypt_and_sanitize_plain_db(self) -> None:
        # Ya no re-ciframos al cerrar; el cifrado se ejecuta bajo demanda
        # cuando se genera un backup protegido.
        return

    def destroy(self) -> None:  # type: ignore[override]
        self._reencrypt_and_sanitize_plain_db()
        try:
            self.pdf_service.cleanup_transient_pdfs()
        except Exception:
            pass
        super().destroy()

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

        def _on_mousewheel(event: tk.Event) -> None:
            try:
                delta = -1 * (event.delta // 120) if event.delta else (1 if event.num == 5 else -1)
                canvas.yview_scroll(delta, "units")
            except Exception:
                pass

        body.bind("<Configure>", _on_body_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Mouse wheel support across platforms.
        for widget in (body, canvas, container, window):
            widget.bind("<MouseWheel>", _on_mousewheel, add=True)
            widget.bind("<Button-4>", _on_mousewheel, add=True)
            widget.bind("<Button-5>", _on_mousewheel, add=True)

        return body

    # --- Deshacer borrados simples (Clientes/Productos) ---
    def undo_last_delete(self) -> None:
        """Restaura el último cliente o producto borrado desde 'Actualizar Info'."""
        if self._active_view != "update":
            return

        # Intentar restaurar producto primero si existe snapshot
        if self.undo_last_product:
            try:
                pid, code, name, unit, price, stock_display = self.undo_last_product
                stock_val = stock_display if stock_display not in ("", "Sin control") else None
                self.product_service.create_product(name, unit, str(price), code or None, stock=stock_val)
                self.all_products_cache = self.product_service.search_products("")
                self.product_ui.filter_products()
                self.show_success("Restaurado", f"Producto '{name}' recreado.")
            except Exception as exc:
                self.show_error("Error", f"No se pudo restaurar el producto: {exc}")
            finally:
                self.undo_last_product = None
            return

        # Restaurar cliente
        if self.undo_last_client:
            try:
                cid, dni, name, phone, email, addr = self.undo_last_client
                self.client_service.create_client(dni, name, phone, email, addr)
                self.client_ui.filter_clients()
                self.show_success("Restaurado", f"Cliente '{name}' recreado.")
            except Exception as exc:
                self.show_error("Error", f"No se pudo restaurar el cliente: {exc}")
            finally:
                self.undo_last_client = None


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
        try:
            overlay.attributes("-alpha", 0.0)
        except Exception:
            pass
        overlay.withdraw()  # oculta mientras se prepara para evitar parpadeo
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

        is_dark = self.is_dark_theme()
        theme_tag = "Dark" if is_dark else "Light"

        if is_dark:
            overlay_bg = "#050505"
            surface_color = "#111827"
            border_color = "#22c55e"
            title_color = "#f9fafb"
            subtitle_color = "#a7f3d0"
            accent_color = "#0ea5e9"
            accent_light = "#38bdf8"
            accent_dark = "#0369a1"
            trough_color = "#1f2937"
        else:
            overlay_bg = "#ecfdf5"
            surface_color = "#f8fafc"
            border_color = "#16a34a"
            title_color = "#065f46"
            subtitle_color = "#0f766e"
            accent_color = "#0284c7"
            accent_light = "#38bdf8"
            accent_dark = "#0369a1"
            trough_color = "#c7eae0"
        bg_color = overlay_bg

        style = ttk.Style()
        base_bar_style = "primary-striped.Horizontal.TProgressbar"
        bar_style = f"Loading{theme_tag}.Striped.Horizontal.TProgressbar"

        try:
            style.layout(bar_style, style.layout(base_bar_style))
        except Exception:
            bar_style = base_bar_style
        style.configure(
            bar_style,
            troughcolor=trough_color,
            bordercolor=bg_color,
            background=accent_color,
            lightcolor=accent_light,
            darkcolor=accent_dark,
        )

        overlay.configure(cursor="arrow", background=overlay_bg)

        border_frame = tk.Frame(overlay, bg=border_color, highlightthickness=0, bd=0)
        border_frame.pack(fill="both", expand=True, padx=0, pady=0)

        frame = tk.Frame(border_frame, bg=surface_color, padx=22, pady=18, highlightthickness=0, bd=0)
        frame.pack(fill="both", expand=True, padx=2, pady=2)

        title_label = tk.Label(
            frame,
            text=f"⏳ {text}",
            font=("Segoe UI", 12, "bold"),
            fg=title_color,
            bg=surface_color,
            anchor="w",
        )
        title_label.pack(fill="x", anchor="w")

        subtitle_label = tk.Label(
            frame,
            text="Estamos preparando todo...",
            font=("Segoe UI", 10),
            fg=subtitle_color,
            bg=surface_color,
            anchor="w",
        )
        subtitle_label.pack(fill="x", anchor="w", pady=(6, 18))

        progress = tb.Progressbar(frame, mode="indeterminate", bootstyle="primary-striped")
        if bar_style:
            progress.configure(style=bar_style)
        progress.pack(fill="x")
        progress.start(12)

        overlay.update_idletasks()
        overlay.deiconify()
        try:
            overlay.grab_set()
        except Exception:
            pass

        self.loading_overlay = overlay
        self._loading_progress = progress
        overlay.update()
        try:
            overlay.attributes("-alpha", 1.0)
        except Exception:
            pass

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

    # Utilidades generales para ventanas emergentes -----------------
    def begin_modal_construction(self, window: tk.Toplevel) -> None:
        """Deja la ventana invisible mientras se construyen widgets."""
        try:
            window.attributes("-alpha", 0.0)
        except Exception:
            pass

    def reveal_modal(self, window: tk.Toplevel) -> None:
        """Revela la ventana ya pintada para evitar parpadeos."""
        def _activate() -> None:
            window.deiconify()
            window.update()
            try:
                window.attributes("-alpha", 1.0)
            except Exception:
                pass

        window.after(60, _activate)

    def validate_numeric(self, proposed: str, max_len: Optional[int] = None) -> bool:
        """Valida que solo se ingresen dígitos y respeta un máximo opcional."""
        if proposed == "":
            return True
        if not proposed.isdigit():
            return False
        if max_len is not None and len(proposed) > max_len:
            return False
        return True

    def validate_alphanum(self, proposed: str, max_len: Optional[int] = None) -> bool:
        """Permite letras y números (OTP alfanum) con longitud máxima opcional."""
        if proposed == "":
            return True
        if not proposed.isalnum():
            return False
        if max_len is not None and len(proposed) > max_len:
            return False
        return True

    def ask_pin(self, title="Verificar PIN", allow_recovery=True):
        """Solicita el PIN de seguridad con opción de recuperación opcional."""
        return self.security_ui.ask_pin(title=title, allow_recovery=allow_recovery)

    def show_recovery_selector(self):
        """Paso 1: Elegir método de recuperación."""
        self.security_ui.show_recovery_selector()

    def show_backup_code_dialog(self):
        """Paso 2A: Ingresar código de respaldo de un solo uso."""
        self.security_ui.show_backup_code_dialog()

    def show_rescue_dialog(self):
        """Muestra el diálogo de recuperación con desafío matemático."""
        self.security_ui.show_rescue_dialog()

    def open_force_change_pin_window(self):
        """Ventana modal que obliga a cambiar el PIN después de recuperación."""
        self.security_ui.open_force_change_pin_window()

    # --- VENTANAS EMERGENTES PERSONALIZADAS ---
    
    def show_custom_message(self, title, message, icon_name="info", bootstyle="info", buttons=None):
        self.message_ui.show_custom_message(title, message, icon_name, bootstyle, buttons)

    def show_info(self, title, message):
        self.message_ui.show_info(title, message)

    def show_warning(self, title, message):
        self.message_ui.show_warning(title, message)

    def show_error(self, title, message):
        self.message_ui.show_error(title, message)

    def show_toast(self, title, message, level="success", duration=3200):
        """Muestra una notificación sutil en la parte superior de la ventana."""
        self.effects_ui.show_toast(title, message, level=level, duration=duration)

    def show_success(self, title, message, use_toast=False, duration=3200):
        self.message_ui.show_success(title, message, use_toast=use_toast, duration=duration)

    def show_question(self, title, message):
        return self.message_ui.show_question(title, message)

    def show_profile_selection(self):
        """Muestra la pantalla de selección de perfiles (Grid de Tarjetas) - Estilo Cyberpunk."""
        self.profile_ui.show_profile_selection()

    def animate_rgb(self, label, step=0):
        """Efecto RGB para el título."""
        self.effects_ui.animate_rgb(label, step=step)

    def change_pin_dialog(self):
        """Diálogo seguro para cambiar el PIN de administrador."""
        self.security_ui.change_pin_dialog()

    def open_security_dashboard(self):
        """Panel de control de seguridad y códigos de respaldo."""
        self.security_ui.open_security_dashboard()

    def create_profile_card(self, parent, profile, row, col):
        """Crea una tarjeta visual para un perfil - Estilo Cyberpunk."""
        self.profile_ui.create_profile_card(parent, profile, row, col)

    def delete_profile_action(self, profile_id):
        self.profile_ui.delete_profile_action(profile_id)

    def select_profile(self, profile_id):
        """Carga el perfil seleccionado y construye la UI principal."""
        self.current_company_id = profile_id
        self.current_company_data = self.company_service.get_profile(profile_id)
        
        # Limpiar ventana
        for widget in self.winfo_children():
            widget.destroy()
            
        self.title(f"Sistema POS - {(self.current_company_data or {}).get('name', 'Empresa')}")
        self.build_main_ui()

    def load_main_logo(self):
        """Carga el logo principal desde el perfil o desde un archivo llamado logo.* en la carpeta del script."""
        candidates = []
        if (self.current_company_data or {}).get("logo_path"):
            candidates.append((self.current_company_data or {}).get("logo_path"))
        
        # Fallback to default logos in resource path (for PyInstaller)
        for name in ("logo.png", "logo.jpg", "logo.jpeg", "logo.bmp"):
            candidates.append(resource_path(name))

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

    def _nav_pref_key(self, profile_id: int) -> str:
        return f"profile_nav_visible_{profile_id}"

    def load_nav_preferences(self, profile_id: Optional[int] = None) -> set[str]:
        """Obtiene las secciones visibles configuradas por perfil. Si no hay dato, todas visibles."""
        profile_key = profile_id or getattr(self, "current_company_id", 1)
        raw = ""
        try:
            raw = self.settings_repo.get_setting(self._nav_pref_key(profile_key), "")
        except Exception:
            raw = ""

        default_visible = [item["key"] for item in NAV_ITEMS]
        visible_keys: list[str] = default_visible
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    visible_keys = [k for k in parsed if k in NAV_ITEMS_BY_KEY]
            except Exception:
                visible_keys = default_visible

        if "dashboard" not in visible_keys:
            visible_keys.insert(0, "dashboard")
        return set(visible_keys)

    def save_nav_preferences(self, profile_id: int, visible_keys: list[str]) -> None:
        """Guarda las secciones visibles, asegurando dashboard siempre presente."""
        cleaned: list[str] = []
        seen: set[str] = set()
        for key in visible_keys:
            if key not in NAV_ITEMS_BY_KEY or key in seen:
                continue
            cleaned.append(key)
            seen.add(key)

        if "dashboard" not in cleaned:
            cleaned.insert(0, "dashboard")

        try:
            self.settings_repo.set_setting(self._nav_pref_key(profile_id), json.dumps(cleaned))
        except Exception:
            pass

    def _nav_style_for_item(self, item: dict[str, Any]) -> str:
        base_style = "danger" if getattr(self, "_holiday_mode", False) else self.nav_base_style
        return base_style if item.get("style") == "base" else cast(str, item.get("style", base_style))

    def _handle_nav_selection(self, key: str) -> None:
        if key == "verify":
            self.open_verify_window()
            return

        item = NAV_ITEMS_BY_KEY.get(key)
        target_view = item.get("view") if item else None
        if target_view:
            self.switch_view(target_view)

    def _create_nav_button(self, item: dict[str, Any]) -> tb.Button:
        return tb.Button(
            self.nav_frame,
            text=item["label"],
            bootstyle=self._nav_style_for_item(item),
            command=lambda key=item["key"]: self._handle_nav_selection(key),
        )

    def build_main_ui(self):
        """Construye la interfaz principal de la aplicación con Navegación por Botones."""
        # 1. Barra Superior (Header + Navegación)
        self.top_bar = tb.Frame(self)
        self.top_bar.pack(fill="x", side="top")
        
        # Contenedor de botones de navegación (Centrado o Izquierda)
        self.nav_frame = tb.Frame(self.top_bar)
        self.nav_frame.pack(side="left", fill="y", padx=10, pady=10)
        self.nav_buttons: list[tb.Button] = []
        self.nav_buttons_map: dict[str, tb.Button] = {}
        self.nav_overflow_button: Optional[tb.Menubutton] = None
        self.nav_overflow_menu: Optional[tk.Menu] = None

        # Estilo base uniforme (Elegante y sobrio)
        base_style = "secondary-outline" if self.is_dark_theme() else "primary-outline"
        self.nav_base_style = base_style
        self.nav_visible_keys = self.load_nav_preferences(self.current_company_id)

        # Dashboard siempre visible
        dashboard_item = NAV_ITEMS_BY_KEY["dashboard"]
        self.btn_nav_dashboard = self._create_nav_button(dashboard_item)
        self.btn_nav_dashboard.pack(side="left", padx=2)
        self.nav_buttons_map["dashboard"] = self.btn_nav_dashboard

        # Botón de overflow (⋯) junto al dashboard para las opciones ocultas
        hidden_items = [item for item in NAV_ITEMS if item["key"] != "dashboard" and item["key"] not in self.nav_visible_keys]
        if hidden_items:
            self.nav_overflow_menu = tk.Menu(self.nav_frame, tearoff=0)
            for item in hidden_items:
                self.nav_overflow_menu.add_command(
                    label=item["label"],
                    command=lambda key=item["key"]: self._handle_nav_selection(key),
                )

            self.nav_overflow_button = tb.Menubutton(
                self.nav_frame,
                text="⋯",
                bootstyle=base_style,
                direction="below",
            )
            self.nav_overflow_button["menu"] = self.nav_overflow_menu
            self.nav_overflow_button.pack(side="left", padx=2)

        # Botones visibles según configuración del perfil
        for item in NAV_ITEMS:
            key = item["key"]
            if key == "dashboard" or key not in self.nav_visible_keys:
                continue
            btn = self._create_nav_button(item)
            btn.pack(side="left", padx=2)
            self.nav_buttons_map[key] = btn

        # Compatibilidad con utilidades existentes
        self.nav_buttons = list(self.nav_buttons_map.values())
        if self.nav_overflow_button:
            self.nav_buttons.append(self.nav_overflow_button)

        # Modo navideño (desactivado por temporada pasada, se deja el código)
        self.btn_holiday_toggle = None
        if self.holiday_features_enabled:
            self.btn_holiday_toggle = tb.Button(
                self.top_bar,
                text="Modo 🎄",
                bootstyle="danger-outline",
                command=self.toggle_holiday_theme,
                width=12,
            )
            self.btn_holiday_toggle.pack(side="right", padx=5, pady=10)

        # Botón Cambiar Perfil (Derecha)
        current_theme = self.style.theme_use()
        toggle_icon = "☀️" if current_theme == "cyborg" else "🌙"

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

        # Banner festivo (dejado en código, no visible por defecto)
        self.holiday_banner = None
        self.holiday_banner_visible = False
        if self.holiday_features_enabled:
            self.holiday_banner = tb.Frame(self, bootstyle="danger")
            self.holiday_banner.pack(fill="x", side="top", padx=10, pady=(0, 5))
            msg = "¡Felices fiestas! Que tengas buenas ventas y clientes felices."
            tb.Label(self.holiday_banner, text=msg, bootstyle="inverse-danger").pack(side="left", padx=10, pady=6)
            tb.Button(
                self.holiday_banner,
                text="Cerrar",
                bootstyle="light-outline",
                command=self.hide_holiday_banner,
                width=10,
            ).pack(side="right", padx=10, pady=6)
            self.holiday_banner_visible = True
        
        # 2. Área de Contenido Principal con marco decorativo interno
        self.content_wrapper = tb.Frame(self, style="AppContent.TFrame")
        self.content_wrapper.pack(fill="both", expand=True, padx=10, pady=10)

        # Marco de luces navideñas (apagado por temporada)
        if self.holiday_features_enabled:
            self._build_light_border()

        # Frame central real de contenido
        self.content_area = tb.Frame(self.content_wrapper, style="AppContent.TFrame")
        self.content_area.pack(fill="both", expand=True)

        # Crear los frames de las vistas (pero no empaquetarlos aún)
        self.frame_dashboard = tb.Frame(self.content_area)
        self.frame_sales = tb.Frame(self.content_area)
        self.frame_boletin = tb.Frame(self.content_area)
        self.frame_fiados = tb.Frame(self.content_area)
        self.frame_update_info = tb.Frame(self.content_area)
        self.frame_history = tb.Frame(self.content_area)
        self.frame_export = tb.Frame(self.content_area)

        # Construir las UIs internas
        self.dashboard_manager = DashboardUIManager(self, self.frame_dashboard, self.sale_service)
        self.dashboard_manager.build_ui()
        self.sales_ui.build_sales_ui()
        self.fiados_manager = FiadosUIManager(self, self.frame_fiados, self.fiado_service)
        self.fiados_manager.build_ui()
        # Reutilizar UI de ventas para boletín (modo interno)
        self.boletin_ui = self.sales_ui
        self.build_update_info_ui()
        self.history_manager = HistoryUIManager(self, self.frame_history)
        self.history_manager.build_ui()
        # Exportar
        if getattr(self, "export_ui", None):
            try:
                self.export_ui.build_export_ui()
            except Exception:
                pass
        
        self.refresh_search_shortcut_targets()
        self.load_main_logo()

        self.apply_chrome_styles()
        self.register_default_tooltips()
        
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
        for frame in [
            self.frame_dashboard,
            self.frame_sales,
            self.frame_boletin,
            self.frame_fiados,
            self.frame_update_info,
            self.frame_history,
            self.frame_export,
        ]:
            frame.pack_forget()
            
        # Mostrar la seleccionada
        if view_name == "dashboard":
            self.frame_dashboard.pack(fill="both", expand=True)
            if getattr(self, "dashboard_manager", None):
                self.dashboard_manager.refresh_dashboard()
        elif view_name == "sales":
            self.sales_mode = "sale"
            if hasattr(self.sales_ui, "set_mode"):
                self.sales_ui.set_mode("sale")
            self.frame_sales.pack(fill="both", expand=True)
            # Auto-refresh products and clients when entering sales view
            try:
                if hasattr(self, "product_ui"):
                    self.product_ui.load_products_for_sales()
                    self.product_ui.filter_sales_products()
                if hasattr(self, "client_ui"):
                    self.client_ui.setup_client_autocomplete()
            except Exception:
                pass
        elif view_name == "boletin":
            self.sales_mode = "boletin"
            if hasattr(self.sales_ui, "set_mode"):
                self.sales_ui.set_mode("boletin")
            self.frame_sales.pack(fill="both", expand=True)
            try:
                if hasattr(self, "product_ui"):
                    self.product_ui.load_products_for_sales()
            except Exception:
                pass
        elif view_name == "fiados":
            self.frame_fiados.pack(fill="both", expand=True)
        elif view_name == "update":
            self.frame_update_info.pack(fill="both", expand=True)
        elif view_name == "history":
            self.frame_history.pack(fill="both", expand=True)
            if getattr(self, "history_manager", None):
                self.history_manager.refresh_tree()
        elif view_name == "export":
            self.frame_export.pack(fill="both", expand=True)

        # Actualizar resaltado del botón activo
        self.update_nav_buttons(view_name)

    # ------------------------------------------------------------------
    # Holiday helpers
    # ------------------------------------------------------------------
    def toggle_holiday_theme(self):
        if not getattr(self, "holiday_features_enabled", False):
            return
        self.apply_holiday_theme(not self._holiday_mode)

    def apply_holiday_theme(self, enabled: bool) -> None:
        if not getattr(self, "holiday_features_enabled", False):
            enabled = False
        self._holiday_mode = enabled
        self.refresh_nav_styles()

        # Ajustar botón y título
        if getattr(self, "btn_holiday_toggle", None):
            self.btn_holiday_toggle.configure(text=("Modo 🎄 ON" if enabled else "Modo 🎄"))
        try:
            self.title(f"{self._base_title} - Modo navideño" if enabled else self._base_title)
        except Exception:
            pass

        # Asegurar banner visible cuando está activo
        if enabled:
            self.show_holiday_banner()
        else:
            self.hide_holiday_banner()

    def toggle_decoration_mode(self, _event: tk.Event | None = None) -> None:
        if not getattr(self, "holiday_features_enabled", False):
            return
        self.decoration_mode = "ribbon" if self.decoration_mode == "lights" else "lights"
        self._draw_light_border()
        try:
            msg = "Modo cinta RGB" if self.decoration_mode == "ribbon" else "Modo luces"
            self.show_toast("Decoración", msg, level="info", duration=1800)
        except Exception:
            pass

    def cycle_decoration_speed(self, _event: tk.Event | None = None) -> None:
        if not getattr(self, "holiday_features_enabled", False):
            return
        speeds = [700, 500, 300, 150]
        current = self.decoration_speed_ms
        next_speed = speeds[(speeds.index(current) + 1) % len(speeds)] if current in speeds else speeds[1]
        self.decoration_speed_ms = next_speed
        self._draw_light_border()
        try:
            self.show_toast("Decoración", f"Velocidad: {next_speed} ms", level="info", duration=1600)
        except Exception:
            pass

    # Decoración: marco de luces navideñas (sin bloquear la UI)
    def _build_light_border(self) -> None:
        if not getattr(self, "holiday_features_enabled", False):
            return
        if getattr(self, "light_canvases", None):
            return
        # Paleta bicolor (verde y azul) para luces/cinta
        self.light_palette = ["#00ff6a", "#11a8ff"]
        self.light_phase = 0
        self.light_spacing = 20
        self.light_radius = 4

        top = tk.Canvas(self.content_wrapper, height=12, highlightthickness=0, bd=0, bg=self.cget("background"), state=tk.DISABLED)
        bottom = tk.Canvas(self.content_wrapper, height=12, highlightthickness=0, bd=0, bg=self.cget("background"), state=tk.DISABLED)
        left = tk.Canvas(self.content_wrapper, width=12, highlightthickness=0, bd=0, bg=self.cget("background"), state=tk.DISABLED)
        right = tk.Canvas(self.content_wrapper, width=12, highlightthickness=0, bd=0, bg=self.cget("background"), state=tk.DISABLED)

        top.pack(side="top", fill="x")
        bottom.pack(side="bottom", fill="x")
        left.pack(side="left", fill="y")
        right.pack(side="right", fill="y")

        self.light_canvases = {"top": top, "bottom": bottom, "left": left, "right": right}
        self._draw_light_border()

    def _draw_light_border(self) -> None:
        if not getattr(self, "holiday_features_enabled", False):
            return
        c = getattr(self, "light_canvases", None)
        if not c:
            return
        base_palette = getattr(self, "light_palette", ["#00ff6a", "#11a8ff"])
        palette = base_palette[:]
        random.shuffle(palette)
        phase = getattr(self, "light_phase", 0)
        spacing = getattr(self, "light_spacing", 20)
        r = getattr(self, "light_radius", 4)
        mode = getattr(self, "decoration_mode", "lights")

        for key in ("top", "bottom", "left", "right"):
            canvas = c.get(key)
            if not canvas:
                continue
            canvas.delete("all")
            if mode == "lights":
                if key in ("top", "bottom"):
                    w = max(canvas.winfo_width(), 1)
                    y0 = 2
                    y1 = y0 + 2 * r
                    for x in range(0, w, spacing):
                        color = palette[(x // spacing + phase) % len(palette)]
                        canvas.create_oval(x - r, y0, x + r, y1, fill=color, outline="")
                else:
                    h = max(canvas.winfo_height(), 1)
                    x0 = 2
                    x1 = x0 + 2 * r
                    for y in range(0, h, spacing):
                        color = palette[(y // spacing + phase + 1) % len(palette)]
                        canvas.create_oval(x0, y - r, x1, y + r, fill=color, outline="")
            else:  # ribbon con degradado tipo teclado
                band_step = 6
                band_width = 10
                phase_px = getattr(self, "light_phase_px", 0)
                if key in ("top", "bottom"):
                    w = max(canvas.winfo_width(), 1)
                    y0 = 1
                    y1 = canvas.winfo_height() - 2
                    for x in range(-band_width * len(palette), w + band_width * len(palette), band_step):
                        color = palette[((x + phase_px) // band_step) % len(palette)]
                        canvas.create_rectangle(x, y0, x + band_width, y1, fill=color, outline="")
                else:
                    h = max(canvas.winfo_height(), 1)
                    x0 = 1
                    x1 = canvas.winfo_width() - 2
                    for y in range(-band_width * len(palette), h + band_width * len(palette), band_step):
                        color = palette[((y + phase_px + band_step) // band_step) % len(palette)]
                        canvas.create_rectangle(x0, y, x1, y + band_width, fill=color, outline="")

                self.light_phase_px = (phase_px + band_step) % (band_step * len(palette))

        self.light_phase = (phase + 1) % len(palette)
        delay = getattr(self, "decoration_speed_ms", 500)
        list(c.values())[0].after(delay, self._draw_light_border)

    def hide_holiday_banner(self) -> None:
        if not getattr(self, "holiday_features_enabled", False):
            return
        if getattr(self, "holiday_banner", None) and self.holiday_banner.winfo_ismapped():
            try:
                self.holiday_banner.pack_forget()
                self.holiday_banner_visible = False
            except Exception:
                pass

    def show_holiday_banner(self) -> None:
        if not getattr(self, "holiday_features_enabled", False):
            return
        if not getattr(self, "holiday_banner", None):
            return
        if self.holiday_banner_visible:
            return
        try:
            self.holiday_banner.pack(fill="x", side="top", padx=10, pady=(0, 5), before=self.content_area)
            self.holiday_banner_visible = True
        except Exception:
            pass

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

    def refresh_nav_styles(self) -> None:
        base_style = "danger" if getattr(self, "_holiday_mode", False) else (
            "secondary-outline" if self.is_dark_theme() else "primary-outline"
        )
        self.nav_base_style = base_style

        for key, btn in getattr(self, "nav_buttons_map", {}).items():
            item = NAV_ITEMS_BY_KEY.get(key)
            if not item:
                continue
            style = "danger" if getattr(self, "_holiday_mode", False) else self._nav_style_for_item(item)
            try:
                btn.configure(bootstyle=style)
            except Exception:
                pass

        if getattr(self, "nav_overflow_button", None):
            try:
                self.nav_overflow_button.configure(bootstyle=base_style)
            except Exception:
                pass

    def update_nav_buttons(self, active_view):
        """Actualiza el estilo de los botones y activa el efecto RGB en el seleccionado."""
        self.refresh_nav_styles()
        self.stop_rgb_animation()

        active_key = None
        for item in NAV_ITEMS:
            if item.get("view") == active_view:
                active_key = item["key"]
                break

        active_btn = self.nav_buttons_map.get(active_key) if hasattr(self, "nav_buttons_map") else None
        if active_btn:
            self.animate_active_button(active_btn)
        elif getattr(self, "nav_overflow_button", None):
            self.animate_active_button(self.nav_overflow_button)

    def stop_rgb_animation(self):
        """Detiene cualquier animación RGB en curso en los botones."""
        self.effects_ui.stop_rgb_animation()

    def animate_active_button(self, btn, step=0):
        """Anima el color del botón activo (Efecto RGB Gamer)."""
        self.effects_ui.animate_active_button(btn, step=step)

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
        self.begin_modal_construction(win)
        win.title("Editar Perfil")
        win.geometry("580x620")
        self.set_app_icon(win)
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

        # Preferencias de navegación visibles en la barra principal
        nav_pref_row = row_igv + 2
        nav_pref_frame = tb.Labelframe(
            lf,
            text="Secciones visibles en la barra principal",
            padding=12,
            bootstyle="info",
        )
        nav_pref_frame.grid(row=nav_pref_row, column=0, columnspan=2, sticky="nsew", padx=0, pady=(0, 10))
        nav_pref_frame.columnconfigure((0, 1), weight=1)

        nav_visible_keys = self.load_nav_preferences(profile_id)
        nav_vars: dict[str, tk.BooleanVar] = {}
        nav_options = [item for item in NAV_ITEMS if item["key"] != "dashboard"]
        for idx, item in enumerate(nav_options):
            var = tk.BooleanVar(value=item["key"] in nav_visible_keys)
            nav_vars[item["key"]] = var
            tb.Checkbutton(
                nav_pref_frame,
                text=item["label"],
                variable=var,
                bootstyle="primary-round-toggle",
            ).grid(row=idx // 2, column=idx % 2, sticky="w", padx=6, pady=4)

        tb.Label(
            nav_pref_frame,
            text="Dashboard siempre visible",
            bootstyle="secondary",
        ).grid(row=(len(nav_options) + 1) // 2, column=0, columnspan=2, sticky="w", padx=6, pady=(6, 0))

        # Botón Guardar
        row_save = nav_pref_row + 1
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
                selected_nav_keys = ["dashboard"] + [key for key, var in nav_vars.items() if var.get()]
                self.save_nav_preferences(profile_id, selected_nav_keys)
                self.settings_repo.set_setting("customer_screen_index", str(selected_screen))
                self.show_info("Éxito", "Perfil actualizado correctamente.")
                win.destroy()
                self.show_profile_selection()  # Refrescar la lista de perfiles
            except Exception as e:
                self.show_error("Error", str(e))
        
        btn_save = tb.Button(lf, text="Guardar cambios", bootstyle="success", command=save_profile)
        btn_save.grid(row=row_save, column=0, columnspan=2, pady=15)

        win.update_idletasks()
        self.center_window(win, 580, 620)
        self.reveal_modal(win)
        self.make_modal(win)

    def set_app_icon(self, window):
        """Intenta cargar logo.ico o logo.png y establecerlo como ícono de la ventana."""
        # Soporta ruta normal y ejecutable PyInstaller (temp _MEIPASS)
        base_dirs = []
        base_dirs.append(os.path.dirname(os.path.abspath(__file__)))
        if getattr(sys, "_MEIPASS", None):
            base_dirs.insert(0, sys._MEIPASS)

        candidates = ["logo.ico", "logo.png"]
        for base in base_dirs:
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
                            if not hasattr(self, "_icon_refs"):
                                self._icon_refs = []
                            self._icon_refs.append(photo)
                        return
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
            if os.name == "nt":  # Windows
                # startfile evita bloqueos por shell y rutas con espacios
                os.startfile(path)  # type: ignore[attr-defined]
            elif os.name == "posix":  # macOS / Linux
                import subprocess
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

        win.update_idletasks()
        self.center_window(win, 600, 500)
        self.reveal_modal(win)
        self.make_modal(win)

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
        self.begin_modal_construction(win)
        win.title("Configuración de Correo (Outlook)")
        win.geometry("400x300")
        self.set_app_icon(win)

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

        win.update_idletasks()
        self.center_window(win, 400, 300)
        self.reveal_modal(win)
        self.make_modal(win)

    def ask_client_email_dialog(self, initial_value="", parent=None):
        """Diálogo personalizado para pedir correo del cliente."""
        dialog = tb.Toplevel(master=parent or self)
        self.begin_modal_construction(dialog)
        dialog.title("Enviar Correo")
        dialog.geometry("400x220")
        self.set_app_icon(dialog)

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

        dialog.update_idletasks()
        self.center_window(dialog, 400, 220)
        self.reveal_modal(dialog)
        self.make_modal(dialog, parent=parent or self)
        self.wait_window(dialog)
        return confirmed_email

    def ask_whatsapp_number_dialog(self, initial_value="", parent=None):
        """Solicita un número de WhatsApp asegurando que tenga al menos 9 dígitos."""
        dialog = tb.Toplevel(master=parent or self)
        self.begin_modal_construction(dialog)
        dialog.title("Número de WhatsApp")
        dialog.geometry("360x220")
        self.set_app_icon(dialog)

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

        dialog.update_idletasks()
        self.center_window(dialog, 360, 220)
        self.reveal_modal(dialog)
        self.make_modal(dialog, parent=parent or self)
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
        is_adelanto = False
        advance_amount = 0.0
        estimated_total = 0.0
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
                is_adelanto = bool(sale_map.get("is_adelanto"))
                advance_amount = float(sale_map.get("advance_amount") or 0)
                estimated_total = float(sale_map.get("estimated_total") or 0)
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

        advance_str = f"{advance_amount:.2f}"
        estimated_str = f"{estimated_total:.2f}"
        remaining_amount = max(estimated_total - advance_amount, 0.0)
        remaining_str = f"{remaining_amount:.2f}"

        if is_adelanto:
            if resend:
                opening_plain = "Te reenviamos tu recibo de adelanto según tu solicitud.\n\n"
                despedida_plain = "Puedes escribirnos si necesitas ajustar el saldo."
            else:
                opening_plain = (
                    f"Hemos registrado tu adelanto el {fecha_boleta}. Adjuntamos el recibo de adelanto en PDF.\n\n"
                )
                despedida_plain = "Podrás pagar el saldo pendiente al recoger tu pedido."

            body_plain = (
                f"Hola, {client_name} 👋,\n\n"
                f"{opening_plain}"
                "Detalles del adelanto:\n"
                f"Recibo: {comprobante}\n"
                f"Fecha: {fecha_boleta}\n"
                f"Adelanto: S/ {advance_str}\n"
                f"Total estimado del servicio: S/ {estimated_str}\n"
                f"Saldo pendiente: S/ {remaining_str}\n\n"
                "El recibo en PDF se encuentra adjunto.\n\n"
                f"{despedida_plain}\nEl equipo de {display_company_name}{phone_line_plain}\n\n"
                "Recibo de adelanto. Documento informativo para el servicio en curso."
            )
        else:
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
            is_adelanto=is_adelanto,
            advance_total=advance_str if is_adelanto else None,
            estimated_total=estimated_str if is_adelanto else None,
            remaining_total=remaining_str if is_adelanto else None,
        )

        subject_base = "REENVIO recibo de adelanto" if (resend and is_adelanto) else (
            "Recibo de adelanto" if is_adelanto else ("REENVIO comprobante electrónico" if resend else "Comprobante electrónico")
        )
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
        pdf_display = os.path.basename(pdf_path) if pdf_path else "(PDF no disponible)"

        win = tb.Toplevel(master=self)
        self.begin_modal_construction(win)
        win.title("Venta Exitosa")
        win.geometry("500x350")
        self.set_app_icon(win)

        tb.Label(win, text="✅ Venta Registrada y PDF Generado", font=("Helvetica", 14, "bold"), bootstyle="success").pack(pady=20)

        tb.Label(win, text=f"Archivo: {pdf_display}", font=("Helvetica", 10)).pack(pady=5)

        btn_frame = tb.Frame(win, padding=20)
        btn_frame.pack(fill="both", expand=True)

        # 1. Ver Archivo
        def open_folder():
            if not pdf_path:
                self.show_warning("PDF", "No se encontró la ruta del PDF generado.")
                return
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
            phone_number = None
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
                is_adelanto = False
                adv = est = 0.0
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

                            is_adelanto = bool(sale_map.get("is_adelanto")) if isinstance(sale_map, dict) else False
                            adv = float(sale_map.get("advance_amount") or 0) if isinstance(sale_map, dict) else 0.0
                            est = float(sale_map.get("estimated_total") or 0) if isinstance(sale_map, dict) else 0.0

                company_name = (self.current_company_data or {}).get("name", "Nuestra Empresa")

                name_candidate = (client_name or "").strip()
                if not name_candidate:
                    name_candidate = client_from_sale
                if not name_candidate:
                    name_candidate = str((self.current_client or {}).get("name") or "").strip()
                client_display_name = name_candidate or "Cliente"

                mensaje = build_whatsapp_message(
                    company_name,
                    client_display_name,
                    sale_datetime,
                    is_adelanto=is_adelanto,
                    advance_amount=adv,
                    estimated_total=est,
                )
            except Exception:
                mensaje = "Adjunto encontrara su boleta de venta digital. Gracias por su preferencia!"

            # Re-generar PDF si falta en disco (evita fallos al adjuntar)
            pdf_to_send = pdf_path
            if not pdf_to_send or not os.path.exists(pdf_to_send):
                try:
                    pdf_to_send = self.pdf_service.generate_sale_pdf(
                        sale_id,
                        output_dir="temp",
                        company_profile=self.current_company_data,
                    )
                except Exception as exc:
                    self.show_error("Error", f"No se pudo generar el PDF para WhatsApp:\n{exc}")
                    return
            
            # Validar disponibilidad de librerías WhatsApp
            if not getattr(self.comm_service, "WHATSAPP_AVAILABLE", True):
                self.show_error(
                    "WhatsApp",
                    "Faltan dependencias para enviar por WhatsApp. Instala:\n  pip install pyautogui pywin32",
                )
                return

            # Enviar automáticamente en segundo plano con timeout visual
            self.show_loading("Enviando WhatsApp...")
            timeout_id = self.after(10000, self.hide_loading)

            def finish_whatsapp_send(success, msg):
                try:
                    if timeout_id:
                        self.after_cancel(timeout_id)
                except Exception:
                    pass
                self.hide_loading()
                if success:
                    self.show_success("WhatsApp", msg, use_toast=True, duration=1400)
                else:
                    self.show_error("Error al enviar", msg)

            def whatsapp_thread_task(number, pdf_file, msg):
                try:
                    result = self.comm_service.send_whatsapp_pdf(
                        number,
                        pdf_file,
                        message=msg,
                        wait_seconds=7,
                    )
                except Exception as exc:
                    result = (False, f"Error inesperado: {exc}")
                self.after(0, lambda res=result: finish_whatsapp_send(*res))

            threading.Thread(target=whatsapp_thread_task, args=(phone_number, pdf_to_send, mensaje), daemon=True).start()
        
        tb.Button(btn_frame, text="💬 Enviar por WhatsApp", bootstyle="success-outline", command=send_whatsapp, width=30).pack(pady=10)

        # 4. Cerrar
        tb.Button(btn_frame, text="Cerrar", bootstyle="secondary", command=win.destroy, width=30).pack(pady=10)

        win.update_idletasks()
        self.center_window(win, 500, 350)
        self.reveal_modal(win)
        self.make_modal(win)




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
        self.begin_modal_construction(win)
        win.title("Verificar Autenticidad de Boleta")
        win.geometry("500x300")
        self.set_app_icon(win)
        
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

                # Monto consistente: usar el total almacenado tal cual (sin recalcular IGV)
                total_monto = float(total or 0.0)

                # Generar PDF temporal sin persistir en APPDATA
                temp_pdf_path = None
                try:
                    temp_pdf_path = self.pdf_service.generate_sale_pdf(
                        sale_id,
                        output_dir="temp",
                        company_profile=self.current_company_data,
                    )
                except Exception:
                    temp_pdf_path = None

                # Mostrar mensaje de éxito
                success_msg = f"✅ BOLETA AUTÉNTICA\n\n"
                success_msg += f"Boleta: {series}-{int(number):06d}\n"
                success_msg += f"Cliente: {client_name}\n"
                success_msg += f"Monto: S/. {total_monto:.2f}\n"
                success_msg += f"Fecha: {dt_str}"
                if temp_pdf_path:
                    success_msg += "\n\nSe regeneró un PDF temporal para visualización."

                self.show_success("Boleta Verificada", success_msg)

                result_label.config(
                    text="✅ Boleta Auténtica",
                    bootstyle="success"
                )

                # Link para abrir el PDF temporal (solo si se generó)
                if temp_pdf_path:
                    link = tb.Label(main_frame, text="Abrir PDF temporal", bootstyle="primary", cursor="hand2")
                    link.pack(pady=(4, 0))
                    link.bind("<Button-1>", lambda _e, p=temp_pdf_path: self.open_pdf(p))

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

        win.update_idletasks()
        self.center_window(win, 500, 300)
        self.reveal_modal(win)
        self.make_modal(win)

    def create_manual_backup(self):
        """Crea un backup manual del sistema (base de datos + PDFs + logos)."""
        self.backups_ui.create_manual_backup()

    def restore_backup(self):
        """Restaura el sistema desde un archivo de backup."""
        self.backups_ui.restore_backup()
    
    def open_export_dialog(self):
        """Abre la ventana de exportación de datos con filtros."""
        win = tb.Toplevel(master=self)
        self.begin_modal_construction(win)
        win.title("📊 Exportar Datos")
        win.geometry("500x800") # Increased height
        self.set_app_icon(win)

        body = self.create_scrollable_dialog_body(win, padding=20)
        
        # Variables
        data_type_var = tk.StringVar(value="clientes")
        format_var = tk.StringVar(value="excel")
        time_filter_var = tk.StringVar(value="all")
        date_from_var = tk.StringVar()
        date_to_var = tk.StringVar()
        
        self.selected_export_client_id = None # Reset selection
        
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
        
        # Frame de búsqueda de cliente (definido antes para usar en toggle)
        client_search_frame = tb.Frame(lf_type, padding=5)
        
        def toggle_client_search():
            if data_type_var.get() == "ventas_por_cliente":
                client_search_frame.pack(fill="x", pady=5, padx=20)
            else:
                client_search_frame.pack_forget()

        tb.Radiobutton(lf_type, text="👥 Clientes", variable=data_type_var, value="clientes", command=toggle_client_search).pack(anchor="w", pady=3)
        tb.Radiobutton(lf_type, text="📦 Productos", variable=data_type_var, value="productos", command=toggle_client_search).pack(anchor="w", pady=3)
        tb.Radiobutton(lf_type, text="🧾 Ventas (Detalladas)", variable=data_type_var, value="ventas_detalladas", command=toggle_client_search).pack(anchor="w", pady=3)
        tb.Radiobutton(lf_type, text="📈 Resumen de Ventas", variable=data_type_var, value="ventas_resumen", command=toggle_client_search).pack(anchor="w", pady=3)
        tb.Radiobutton(lf_type, text="👤 Ventas por Cliente", variable=data_type_var, value="ventas_por_cliente", command=toggle_client_search).pack(anchor="w", pady=3)
        
        # UI Búsqueda Cliente
        tb.Label(client_search_frame, text="Buscar Cliente (Nombre/DNI):", font=("Arial", 9, "bold")).pack(anchor="w")
        search_row = tb.Frame(client_search_frame)
        search_row.pack(fill="x", pady=5)
        
        txt_client_search = tb.Entry(search_row)
        txt_client_search.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Combobox con altura limitada a 5 items (scroll para ver más)
        cb_client_results = tb.Combobox(client_search_frame, state="readonly", height=5)
        cb_client_results.pack(fill="x", pady=5)
        
        # Variable para debounce
        self._export_search_job = None

        def search_client_action(event=None):
            query = txt_client_search.get().strip()
            if not query:
                # Si está vacío, limpiar
                cb_client_results['values'] = []
                cb_client_results.set("")
                self.selected_export_client_id = None
                return

            results = self.client_service.search_clients(query)
            if not results:
                cb_client_results['values'] = ["Sin resultados"]
                cb_client_results.current(0)
                self.selected_export_client_id = None
            else:
                values = [f"{r[2]} ({r[1]})" for r in results]
                cb_client_results['values'] = values
                cb_client_results.current(0)
                self.export_client_map = {i: r[0] for i, r in enumerate(results)}
                self.selected_export_client_id = results[0][0]
                
                # Opcional: Desplegar lista automáticamente si hay resultados
                # cb_client_results.event_generate('<Down>') 

        def on_search_change(event):
            if self._export_search_job:
                self.after_cancel(self._export_search_job)
            # Debounce de 500ms
            self._export_search_job = self.after(500, lambda: search_client_action())

        # Bind para escritura automática
        txt_client_search.bind("<KeyRelease>", on_search_change)

        # Botón manual (opcional, por si acaso)
        tb.Button(search_row, text="🔍", command=search_client_action, width=4, bootstyle="info-outline").pack(side="right")

        def on_client_select(event):
            idx = cb_client_results.current()
            if idx >= 0 and hasattr(self, 'export_client_map'):
                self.selected_export_client_id = self.export_client_map.get(idx)

        cb_client_results.bind("<<ComboboxSelected>>", on_client_select)
        
        # Sección: Formato
        lf_format = tb.Labelframe(main_frame, text="Formato de Exportación", padding=15, bootstyle="success")
        lf_format.pack(fill="x", pady=(0, 15))
        
        fmt_container = tb.Frame(lf_format)
        fmt_container.pack(fill="x", expand=True)
        
        # Estilo visual mejorado: Botones grandes lado a lado
        # Excel: Verde (success)
        tb.Radiobutton(
            fmt_container, 
            text="📗 Excel (.xlsx)", 
            variable=format_var, 
            value="excel",
            bootstyle="success-toolbutton-outline"
        ).pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=5)
        
        # PDF: Rojo (danger)
        tb.Radiobutton(
            fmt_container, 
            text="📄 PDF (Profesional)", 
            variable=format_var, 
            value="pdf",
            bootstyle="danger-toolbutton-outline"
        ).pack(side="left", fill="x", expand=True, padx=(10, 0), ipady=5)
        
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
                date_to=date_to_var.get(),
                fiado_status=None,
            )
        
        tb.Button(btn_frame, text="Cancelar", bootstyle="secondary", command=win.destroy, width=15).pack(side="left")
        tb.Button(btn_frame, text="📊 Exportar", bootstyle="success", command=do_export, width=15).pack(side="right")

        win.update_idletasks()
        self.center_window(win, 500, 750)
        self.reveal_modal(win)
        self.make_modal(win)
    
    def execute_export(self, data_type, format_type, time_filter, date_from, date_to, fiado_status=None):
        """Ejecuta la exportación según los parámetros seleccionados."""
        # 1. Calcular rango de fechas
        start_dt, end_dt = self.calculate_date_range(time_filter, date_from, date_to)
        
        # 2. Obtener datos según data_type
        headers = []
        data = []
        title = f"REPORTE DE {data_type.upper().replace('_', ' ')}"
        fiado_status = (fiado_status or "todos").lower()
        
        try:
            if data_type == "clientes":
                rows = self.client_service.search_clients("")
                headers = ["#", "Nombre", "Fecha Registro"]
                for idx, r in enumerate(rows, 1):
                    # r: id, dni, full_name, phone, email, address, created_at
                    created_at = r[6] if len(r) > 6 else ""
                    data.append({
                        "num": str(idx),
                        "nombre": r[2],
                        "fecha": created_at
                    })
            
            elif data_type == "productos":
                rows = self.product_service.search_products("")
                headers = ["ID", "Código", "Nombre", "Unidad", "Precio"]
                for r in rows:
                    data.append({
                        "id": r[0], "codigo": r[1], "nombre": r[2], 
                        "unidad": r[3], "precio": f"{r[4]:.2f}"
                    })

            elif data_type == "ventas_detalladas":
                rows = self.sale_service.search_sales_detailed("")
                headers = ["Serie", "Fecha", "Cliente", "Producto", "Cant", "P.Unit", "Total"]
                for r in rows:
                    # r: series, number, datetime, full_name, description, quantity, unit_price, subtotal
                    sale_dt = r[2]
                    if self.is_date_in_range(sale_dt, start_dt, end_dt):
                        data.append({
                            "serie": f"{r[0]}-{int(r[1]):06d}",
                            "fecha": r[2],
                            "cliente": r[3],
                            "producto": r[4],
                            "cant": f"{r[5]:.2f}",
                            "p_unit": f"{r[6]:.2f}",
                            "total": f"{r[7]:.2f}"
                        })

            elif data_type == "ventas_por_cliente":
                if not getattr(self, 'selected_export_client_id', None):
                    self.show_warning("Selección requerida", "Por favor busque y seleccione un cliente para este reporte.")
                    return
                
                rows = self.sale_service.get_sales_detailed_by_client_id(self.selected_export_client_id)
                headers = ["Serie", "Fecha", "Producto", "Cant", "P.Unit", "Total"]
                
                total_sum = 0.0
                client_name = "Cliente"

                for r in rows:
                    # r: series, number, datetime, full_name, description, quantity, unit_price, subtotal
                    sale_dt = r[2]
                    client_name = r[3]
                    if self.is_date_in_range(sale_dt, start_dt, end_dt):
                        subtotal = float(r[7] or 0)
                        total_sum += subtotal
                        data.append({
                            "serie": f"{r[0]}-{int(r[1]):06d}",
                            "fecha": r[2],
                            "producto": r[4],
                            "cant": f"{r[5]:.2f}",
                            "p_unit": f"{r[6]:.2f}",
                            "total": f"{subtotal:.2f}"
                        })
                
                # Add total row
                data.append({
                    "serie": "", "fecha": "", "producto": "", "cant": "", "p_unit": "TOTAL GASTADO:", 
                    "total": f"{total_sum:.2f}"
                })
                
                title = f"REPORTE DE VENTAS - {client_name.upper()}"

            elif data_type == "ventas_resumen":
                rows = self.sale_service.search_sales_by_client("")
                headers = ["Serie-Corr.", "Fecha", "Cliente", "Total"]
                
                for r in rows:
                    # r: id, series, number, datetime, total, full_name, dni
                    sale_dt = r[3] # string YYYY-MM-DD HH:MM:SS
                    if self.is_date_in_range(sale_dt, start_dt, end_dt):
                        data.append({
                            "serie": f"{r[1]}-{int(r[2]):06d}",
                            "fecha": r[3],
                            "cliente": r[5],
                            "total": f"{r[4]:.2f}"
                        })

            elif data_type == "fiados":
                if not hasattr(self, "fiado_service"):
                    self.show_error("Fiados", "Servicio de fiados no disponible.")
                    return

                rows = self.fiado_service.search_fiados("")
                headers = ["Código", "Fecha", "Cliente", "Estado", "Total", "Pagado", "Pendiente"]
                total_bruto_sum = 0.0
                total_pagado_sum = 0.0
                total_pendiente_sum = 0.0

                for fiado in rows:
                    dt_str = fiado.get("created_at") or ""
                    if not self.is_date_in_range(dt_str, start_dt, end_dt):
                        continue
                    status = (fiado.get("status") or "").lower()
                    if fiado_status == "pagados" and status != "pagado":
                        continue
                    if fiado_status == "pendientes" and status == "pagado":
                        continue

                    total_bruto = float(fiado.get("total_bruto") or 0.0)
                    total_pagado = float(fiado.get("total_pagado") or 0.0)
                    total_pend = float(fiado.get("total_pendiente") or 0.0)
                    total_bruto_sum += total_bruto
                    total_pagado_sum += total_pagado
                    total_pendiente_sum += total_pend

                    cliente = fiado.get("full_name") or ""
                    dni = fiado.get("dni") or ""
                    cliente_txt = f"{cliente} ({dni})" if dni else cliente
                    data.append({
                        "codigo": fiado.get("code") or "",
                        "fecha": dt_str,
                        "cliente": cliente_txt,
                        "estado": "Pagado" if status == "pagado" else "Pendiente",
                        "total": f"{total_bruto:.2f}",
                        "pagado": f"{total_pagado:.2f}",
                        "pendiente": f"{total_pend:.2f}",
                    })

                if data:
                    data.append({
                        "codigo": "",
                        "fecha": "",
                        "cliente": "",
                        "estado": "TOTAL",
                        "total": f"{total_bruto_sum:.2f}",
                        "pagado": f"{total_pagado_sum:.2f}",
                        "pendiente": f"{total_pendiente_sum:.2f}",
                    })
                    title = "REPORTE DE FIADOS"

            elif data_type == "fiados_por_cliente":
                if not getattr(self, 'selected_export_client_id', None):
                    self.show_warning("Selección requerida", "Seleccione un cliente para exportar sus fiados.")
                    return
                if not hasattr(self, "fiado_service"):
                    self.show_error("Fiados", "Servicio de fiados no disponible.")
                    return

                client_row = self.client_service.get_client_by_id(self.selected_export_client_id)
                client_name = client_row[2] if client_row else "Cliente"
                client_dni = client_row[1] if client_row else ""

                rows = self.fiado_service.list_by_client(self.selected_export_client_id)
                headers = ["Código", "Fecha", "Estado", "Total", "Pagado", "Pendiente"]
                total_bruto_sum = 0.0
                total_pagado_sum = 0.0
                total_pendiente_sum = 0.0

                for fiado in rows:
                    dt_str = fiado.get("created_at") or ""
                    if not self.is_date_in_range(dt_str, start_dt, end_dt):
                        continue
                    status = (fiado.get("status") or "").lower()
                    if fiado_status == "pagados" and status != "pagado":
                        continue
                    if fiado_status == "pendientes" and status == "pagado":
                        continue

                    total_bruto = float(fiado.get("total_bruto") or 0.0)
                    total_pagado = float(fiado.get("total_pagado") or 0.0)
                    total_pend = float(fiado.get("total_pendiente") or 0.0)
                    total_bruto_sum += total_bruto
                    total_pagado_sum += total_pagado
                    total_pendiente_sum += total_pend

                    data.append({
                        "codigo": fiado.get("code") or "",
                        "fecha": dt_str,
                        "estado": "Pagado" if status == "pagado" else "Pendiente",
                        "total": f"{total_bruto:.2f}",
                        "pagado": f"{total_pagado:.2f}",
                        "pendiente": f"{total_pend:.2f}",
                    })

                if data:
                    data.append({
                        "codigo": "",
                        "fecha": "",
                        "estado": "TOTAL",
                        "total": f"{total_bruto_sum:.2f}",
                        "pagado": f"{total_pagado_sum:.2f}",
                        "pendiente": f"{total_pendiente_sum:.2f}",
                    })
                    title = f"REPORTE DE FIADOS - {client_name.upper()} ({client_dni})"
            
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
                "footer_message": company_info.get("footer_message", ""),
                "logo_path": company_info.get("logo_path", "")
            }

            if format_type == "excel":
                generar_reporte.generate_excel(filename, title, headers, data, company_dict)
            else:
                generar_reporte.generate_pdf(filename, title, headers, data, company_dict)
                
            try:
                self.settings_service.audit_log(
                    "EXPORT_DATA",
                    f"{data_type} -> {filename}",
                )
            except Exception:
                pass

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
                    name = str(row['Nombre']).strip().upper()
                    unit = str(row['Unidad']).strip().upper()
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
    if not acquire_single_instance():
        try:
            Messagebox.show_warning(
                title="Ya está abierto",
                message="La aplicación ya está en ejecución.",
            )
        except Exception:
            print("La aplicación ya está en ejecución.")
        sys.exit(0)

    init_db()
    app = App()
    app.mainloop()
