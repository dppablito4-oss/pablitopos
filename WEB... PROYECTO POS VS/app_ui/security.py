"""Security-related dialog flows extracted from the main application."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING, Any

import tkinter as tk
from tkinter import filedialog
from tkinter.scrolledtext import ScrolledText
import ttkbootstrap as tb

try:  # Optional QR support
    from PIL import Image, ImageTk  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    Image = None  # type: ignore
    ImageTk = None  # type: ignore

try:  # Optional QR support
    import qrcode  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    qrcode = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - only for type checking
    from app_boletas import App


class SecurityUI:
    """Encapsula diálogos y rutinas de seguridad alrededor del PIN."""

    def __init__(self, app: "App") -> None:
        self.app = app
        self._rescue_qr_photo = None  # cache for QR code image to prevent GC

    # ------------------------------------------------------------------
    # Flujo de verificación de PIN
    # ------------------------------------------------------------------
    def ask_pin(self, title: str = "Verificar PIN", allow_recovery: bool = True) -> bool:
        app = self.app
        pin_var = tk.StringVar(master=app)

        dialog = tb.Toplevel(master=app)
        app.begin_modal_construction(dialog)
        dialog.title(title)
        dialog.geometry("350x280")
        app.set_app_icon(dialog)
        tb.Label(dialog, text="Ingrese su PIN:", font=("Helvetica", 10)).pack(pady=5)
        entry = tb.Entry(dialog, show="●", textvariable=pin_var, justify="center", font=("Helvetica", 14), bootstyle="primary")
        entry.pack(pady=5, padx=20, fill="x", ipady=5)
        entry.focus_set()

        confirmed = False
        forgot_password = False

        def on_confirm(_event: Optional[tk.Event] = None) -> None:
            nonlocal confirmed
            confirmed = True
            dialog.destroy()

        def on_forgot() -> None:
            nonlocal forgot_password
            forgot_password = True
            dialog.destroy()

        entry.bind("<Return>", on_confirm)

        btn_frame = tb.Frame(dialog)
        btn_frame.pack(pady=15)

        tb.Button(btn_frame, text="✓ Confirmar", bootstyle="success", command=on_confirm, width=12).pack(side="left", padx=5)
        tb.Button(btn_frame, text="✗ Cancelar", bootstyle="secondary", command=dialog.destroy, width=12).pack(side="left", padx=5)
        # Tecla Escape para cerrar/cancelar sin ratón
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        dialog.bind("<Return>", lambda _e: on_confirm())
        if allow_recovery:
            tb.Button(dialog, text="¿Olvidé mi contraseña?", bootstyle="link", command=on_forgot).pack(pady=5)

        dialog.update_idletasks()
        app.center_window(dialog, 350, 280)
        app.reveal_modal(dialog)
        app.make_modal(dialog)
        app.wait_window(dialog)

        if forgot_password:
            self.show_recovery_selector()
            return False

        if not confirmed or not pin_var.get():
            return False

        ok, message = app.settings_service.verify_pin(pin_var.get(), context="PIN_DIALOG")
        if ok:
            return True

        title = "Acceso bloqueado" if "bloqueado" in message.lower() else "Acceso Denegado"
        app.show_error(title, message)
        return False

    def show_recovery_selector(self) -> None:
        app = self.app
        dialog = tb.Toplevel(master=app)
        app.begin_modal_construction(dialog)
        dialog.title("Método de Recuperación")
        dialog.geometry("400x300")
        app.set_app_icon(dialog)

        tb.Label(
            dialog,
            text="¿Cómo deseas recuperar tu acceso?",
            font=("Helvetica", 12, "bold"),
            bootstyle="primary",
        ).pack(pady=20)

        tb.Button(
            dialog,
            text="🔑 Usar Código de Respaldo\n(Lista de 10 códigos)",
            bootstyle="info-outline",
            command=lambda: [dialog.destroy(), self.show_backup_code_dialog()],
            width=30,
        ).pack(pady=10, ipady=5)

        tb.Button(
            dialog,
            text="📱 Usar Código Autenticador (App Externa)",
            bootstyle="warning-outline",
            command=lambda: [dialog.destroy(), self.show_rescue_dialog()],
            width=30,
        ).pack(pady=10, ipady=5)

        tb.Button(dialog, text="Cancelar", bootstyle="secondary", command=dialog.destroy).pack(pady=20)

        # Escape para cerrar selector rápidamente
        dialog.bind("<Escape>", lambda _e: dialog.destroy())

        dialog.update_idletasks()
        app.center_window(dialog, 400, 300)
        app.reveal_modal(dialog)
        app.make_modal(dialog)

    def show_backup_code_dialog(self) -> None:
        app = self.app
        dialog = tb.Toplevel(master=app)
        app.begin_modal_construction(dialog)
        dialog.title("Código de Respaldo")
        dialog.geometry("400x250")
        app.set_app_icon(dialog)

        tb.Label(dialog, text="Ingrese uno de sus códigos de respaldo:", font=("Helvetica", 10)).pack(pady=15)

        code_var = tk.StringVar(master=app)
        entry = tb.Entry(
            dialog,
            textvariable=code_var,
            font=("Courier New", 14, "bold"),
            justify="center",
            width=15,
        )
        entry.pack(pady=10, ipady=5)
        entry.focus_set()

        app.setup_uppercase_entry(entry)

        def verify_code() -> None:
            code = code_var.get().strip()
            if not code:
                return

            if app.settings_service.consume_backup_code(code):
                dialog.destroy()
                app.show_success("Acceso Recuperado", "Código válido aceptado.\nEl código ha sido eliminado de su lista.")
                app.settings_service.force_reset_pin()
                self.open_force_change_pin_window()
            else:
                app.show_error("Error", "Código inválido o ya utilizado.")
                entry.delete(0, tk.END)

        entry.bind("<Return>", lambda _e: verify_code())
        tb.Button(dialog, text="Verificar Código", bootstyle="success", command=verify_code).pack(pady=15)

        # Escape para cancelar rápidamente
        dialog.bind("<Escape>", lambda _e: dialog.destroy())

        dialog.update_idletasks()
        app.center_window(dialog, 400, 250)
        app.reveal_modal(dialog)
        app.make_modal(dialog)
        dialog.bind("<Return>", lambda _e: verify_code())

    def show_rescue_dialog(self) -> None:
        app = self.app
        challenge = app.settings_service.generate_challenge_code()

        dialog = tb.Toplevel(master=app)
        app.begin_modal_construction(dialog)
        dialog.title("🔓 Recuperación de Acceso")
        dialog.geometry("420x420")
        app.set_app_icon(dialog)

        body = app.create_scrollable_dialog_body(dialog, padding=18)

        tb.Label(
            body,
            text="Verificación de Identidad",
            font=("Helvetica", 13, "bold"),
            bootstyle="primary",
        ).pack(pady=12)
        tb.Label(
            body,
            text=(
                "Ingresa el código generado por tu aplicación autenticadora.\n"
                "Si no la tienes, selecciona el método de códigos de respaldo."
            ),
            justify="center",
            wraplength=360,
        ).pack(pady=5)

        tb.Label(body, text="Código mostrado en tu autenticador:", font=("Helvetica", 11, "bold")).pack(pady=10)

        tb.Label(
            body,
            text=challenge,
            font=("Courier New", 22, "bold"),
            bootstyle="secondary",
        ).pack(pady=5)

        # Determinar URL LAN accesible (reutilizando lógica de App si es posible, o simple fallback)
        def _get_local_ip() -> str:
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(0.1)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except Exception:
                return "127.0.0.1"

        local_ip = _get_local_ip()
        # Asumimos puerto 8000 que es el default en app_boletas
        port = 8000 
        server_url = f"http://{local_ip}:{port}"

        # Payload JSON para soporte LAN
        import json
        
        fingerprint = "unknown"
        if getattr(app, "storage_guard", None):
             try:
                 fingerprint = app.storage_guard.hardware_fingerprint()
             except:
                 pass

        # QR payload con el reto al inicio para apps que leen los primeros 4 caracteres
        qr_payload = f"{challenge}|{fingerprint}|{server_url}"

        # Registrar waiter en la app para auto-completar
        if hasattr(app, "_recovery_ui_waiters"):
            print(f"[DEBUG] Registrando waiter para challenge: {challenge}")
            app._recovery_ui_waiters[challenge] = {
                "on_success": lambda resp: [response_var.set(resp), validate_response()]
            }
        else:
            print("[DEBUG] ERROR: app no tiene _recovery_ui_waiters")

        if qrcode is not None and ImageTk is not None:
            try:
                qr_builder = qrcode.QRCode(version=1, box_size=6, border=2)
                qr_builder.add_data(qr_payload)
                qr_builder.make(fit=True)
                qr_render = qr_builder.make_image(fill_color="black", back_color="white")
                pil_image: Any = qr_render.get_image() if hasattr(qr_render, "get_image") else qr_render
                if hasattr(pil_image, "resize"):
                    pil_image = pil_image.resize((220, 220))
                self._rescue_qr_photo = ImageTk.PhotoImage(pil_image)  # type: ignore[arg-type]
                tb.Label(
                    body,
                    text="Escanee este QR con la app móvil para autorizar automáticamente.",
                    font=("Helvetica", 9),
                    wraplength=360,
                ).pack(pady=(10, 4))
                tb.Label(body, image=self._rescue_qr_photo).pack(pady=(0, 12))
            except Exception:
                self._rescue_qr_photo = None

        tb.Label(
            body,
            text="Ingrese la respuesta de 6 caracteres que muestra su app autenticadora:",
            font=("Helvetica", 10),
            wraplength=360,
            justify="center",
        ).pack(pady=10)

        response_var = tk.StringVar(master=app)
        vcmd_resp = (app.register(lambda P: app.validate_alphanum(P, 6)), "%P")
        entry_response = tb.Entry(
            body,
            textvariable=response_var,
            justify="center",
            font=("Courier New", 16, "bold"),
            width=10,
            validate="key",
            validatecommand=vcmd_resp,
        )
        entry_response.pack(pady=5, ipady=5)
        app.setup_uppercase_entry(entry_response)
        entry_response.focus_set()
        entry_response.bind("<Return>", lambda _e: validate_response())
        entry_response.configure(bootstyle="primary")

        dialog.update_idletasks()
        app.center_window(dialog, 420, 420)
        app.reveal_modal(dialog)
        app.make_modal(dialog)

        # Escape para cancelar rápidamente
        dialog.bind("<Escape>", lambda _e: dialog.destroy())

        def validate_response() -> None:
            response = response_var.get().strip()

            if not response:
                app.show_warning("Atención", "Debes ingresar la respuesta.")
                return

            if len(response) != 6:
                app.show_warning("Atención", "La respuesta debe tener 6 caracteres.")
                return

            if app.settings_service.verify_master_response(challenge, response):
                dialog.destroy()
                app.show_info("✓ Verificación Exitosa", "Código correcto. Ahora debes establecer un nuevo PIN.")
                app.settings_service.force_reset_pin()
                self.open_force_change_pin_window()
            else:
                app.show_error("✗ Código Incorrecto", "Digite correctamente. Verifica tu APP autenticadora.")

        btn_frame = tb.Frame(body)
        btn_frame.pack(pady=15)

        tb.Button(btn_frame, text="Verificar", bootstyle="success", command=validate_response, width=15).pack(side="left", padx=5)
        tb.Button(btn_frame, text="Cancelar", bootstyle="secondary", command=dialog.destroy, width=15).pack(side="left", padx=5)

    def open_force_change_pin_window(self) -> None:
        app = self.app
        dialog = tb.Toplevel(master=app)
        app.begin_modal_construction(dialog)
        dialog.title("⚠ Cambio de PIN Obligatorio")
        dialog.geometry("400x320")
        app.set_app_icon(dialog)

        def block_close() -> None:
            app.show_warning("Atención", "Debes establecer un nuevo PIN para continuar.")

        dialog.protocol("WM_DELETE_WINDOW", block_close)

        tb.Label(
            dialog,
            text="🔒 Establecer Nuevo PIN",
            font=("Helvetica", 14, "bold"),
            bootstyle="danger",
        ).pack(pady=15)
        tb.Label(
            dialog,
            text="Por seguridad, debes establecer un nuevo PIN ahora.",
            font=("Helvetica", 9),
        ).pack(pady=5)

        form = tb.Frame(dialog)
        form.pack(pady=20, padx=30, fill="x")

        tb.Label(form, text="Nuevo PIN:").grid(row=0, column=0, sticky="e", padx=5, pady=10)
        new_pin_var = tk.StringVar(master=app)
        entry_new = tb.Entry(form, show="●", textvariable=new_pin_var, justify="center", font=("Helvetica", 12))
        entry_new.grid(row=0, column=1, sticky="ew", padx=5, pady=10, ipady=3)
        entry_new.focus_set()

        tb.Label(form, text="Confirmar PIN:").grid(row=1, column=0, sticky="e", padx=5, pady=10)
        confirm_pin_var = tk.StringVar(master=app)
        entry_confirm = tb.Entry(form, show="●", textvariable=confirm_pin_var, justify="center", font=("Helvetica", 12))
        entry_confirm.grid(row=1, column=1, sticky="ew", padx=5, pady=10, ipady=3)

        form.columnconfigure(1, weight=1)

        def save_new_pin() -> None:
            new_pin = new_pin_var.get().strip()
            confirm_pin = confirm_pin_var.get().strip()

            if not new_pin or not confirm_pin:
                app.show_warning("Atención", "Ambos campos son obligatorios.")
                return

            if len(new_pin) < 4:
                app.show_warning("Atención", "El PIN debe tener al menos 4 dígitos.")
                return

            if new_pin != confirm_pin:
                app.show_error("Error", "Los PINs no coinciden.")
                return

            app.settings_service.set_pin(new_pin, audit_action="PIN_FORCED_CHANGE")
            dialog.destroy()
            app.show_info("✓ PIN Actualizado", "Tu nuevo PIN ha sido establecido correctamente.\n\nRecuérdalo bien.")

        tb.Button(dialog, text="Guardar PIN", bootstyle="success", command=save_new_pin, width=20).pack(pady=15)

        dialog.update_idletasks()
        app.center_window(dialog, 400, 320)
        app.reveal_modal(dialog)
        app.make_modal(dialog)

    # ------------------------------------------------------------------
    # Panel de seguridad
    # ------------------------------------------------------------------
    def change_pin_dialog(self) -> None:
        app = self.app
        dialog = tb.Toplevel(master=app)
        app.begin_modal_construction(dialog)
        dialog.title("Cambiar PIN de Seguridad")
        dialog.geometry("400x350")
        app.set_app_icon(dialog)

        tb.Label(dialog, text="🔐 Actualizar PIN de Seguridad", font=("Helvetica", 12, "bold"), bootstyle="primary").pack(pady=15)

        frame = tb.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)

        tb.Label(frame, text="PIN Actual:").pack(anchor="w", pady=(5, 0))
        entry_current = tb.Entry(frame, show="*", justify="center")
        entry_current.pack(fill="x", pady=(0, 10))

        tb.Label(frame, text="Nuevo PIN (mín 4 dígitos):").pack(anchor="w", pady=(5, 0))
        entry_new = tb.Entry(frame, show="*", justify="center")
        entry_new.pack(fill="x", pady=(0, 10))

        tb.Label(frame, text="Confirmar Nuevo PIN:").pack(anchor="w", pady=(5, 0))
        entry_confirm = tb.Entry(frame, show="*", justify="center")
        entry_confirm.pack(fill="x", pady=(0, 10))

        entry_current.focus_set()

        def save_new_pin() -> None:
            current_pin = entry_current.get().strip()
            new_pin = entry_new.get().strip()
            confirm_pin = entry_confirm.get().strip()

            ok, message = app.settings_service.verify_pin(current_pin, context="CHANGE_PIN_DIALOG")
            if not ok:
                app.show_error("Error", message)
                return

            if len(new_pin) < 4:
                app.show_warning("Atención", "El nuevo PIN debe tener al menos 4 dígitos.")
                return

            if new_pin != confirm_pin:
                app.show_error("Error", "Los nuevos PIN no coinciden.")
                return

            if new_pin == "1234":
                app.show_warning("Seguridad", "No puede usar '1234' como PIN. Elija uno más seguro.")
                return

            try:
                app.settings_service.change_pin(current_pin, new_pin)
                app.show_success("Éxito", "PIN actualizado correctamente.\nNo olvide su nuevo PIN.")
                dialog.destroy()
            except Exception as exc:  # pragma: no cover - UI feedback
                app.show_error("Error", str(exc))

        tb.Button(dialog, text="Guardar Nuevo PIN", bootstyle="success", command=save_new_pin, width=20).pack(pady=10)

        dialog.bind("<Return>", lambda _e: save_new_pin())
        dialog.bind("<Escape>", lambda _e: dialog.destroy())

        dialog.update_idletasks()
        app.center_window(dialog, 400, 350)
        app.reveal_modal(dialog)
        app.make_modal(dialog)
        app.wait_window(dialog)

    def open_security_dashboard(self) -> None:
        app = self.app
        if not self.ask_pin("Acceso a Seguridad", allow_recovery=False):
            return

        win = tb.Toplevel(master=app)
        app.begin_modal_construction(win)
        win.title("Gestión de Seguridad")
        win.geometry("600x600")  # Un poco más alto
        app.set_app_icon(win)

        body = app.create_scrollable_dialog_body(win, padding=16)

        # --- SECCIÓN 1: GESTIÓN DE PIN ---
        lf_pin = tb.Labelframe(body, text="🔐 Contraseña / PIN de Administrador", padding=15, bootstyle="primary")
        lf_pin.pack(fill="x", pady=(10, 20))

        tb.Label(
            lf_pin, 
            text="Cambie su contraseña regularmente para mantener seguro el sistema.", 
            bootstyle="secondary",
            wraplength=350
        ).pack(side="left", fill="x", expand=True)
        
        tb.Button(
            lf_pin, 
            text="Cambiar Contraseña", 
            bootstyle="primary", 
            command=self.change_pin_dialog,
            width=20
        ).pack(side="right", padx=5)

        # --- SECCIÓN 2: CÓDIGOS DE RECUPERACIÓN ---
        tb.Label(
            body,
            text="🛡 Códigos de Recuperación de Emergencia",
            font=("Helvetica", 16, "bold"),
            bootstyle="danger",
        ).pack(pady=(10, 5))

        tb.Label(
            body,
            text=(
                "Estos códigos permiten acceder si olvida su PIN.\n"
                "Guárdelos en un lugar seguro (impresos o en un archivo)."
            ),
            justify="center",
            bootstyle="secondary",
        ).pack(pady=(0, 15))

        frame_codes = tb.Frame(body, padding=10, bootstyle="dark")
        frame_codes.pack(fill="both", expand=True, padx=20, pady=5)

        txt_codes = ScrolledText(frame_codes, height=8, font=("Consolas", 12), state="disabled")
        txt_codes.pack(fill="both", expand=True)

        def refresh_codes() -> None:
            codes = app.settings_service.get_backup_codes()
            txt_codes.config(state="normal")
            txt_codes.delete("1.0", tk.END)
            if codes:
                for code in codes:
                    txt_codes.insert(tk.END, f"{code}\n")
            else:
                txt_codes.insert(tk.END, "No hay códigos activos.\nGenere nuevos códigos para asegurar su acceso.")
            txt_codes.config(state="disabled")

        refresh_codes()

        btn_frame = tb.Frame(body, padding=20)
        btn_frame.pack(fill="x")

        def generate_new() -> None:
            if app.show_question("¿Generar nuevos códigos?\nEsto invalidará los códigos anteriores.", "Confirmar"):
                app.settings_service.generate_new_backup_codes()
                refresh_codes()
                app.show_success("Éxito", "Nuevos códigos generados.")

        def save_to_file() -> None:
            codes = app.settings_service.get_backup_codes()
            if not codes:
                app.show_warning("Atención", "No hay códigos para guardar.")
                return

            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt")],
                title="Guardar Códigos de Recuperación",
                initialfile="PABLITO_POS_BACKUP_CODES.txt",
            )
            if filename:
                try:
                    with open(filename, "w", encoding="utf-8") as fout:
                        fout.write("=========================================\n")
                        fout.write(" CÓDIGOS DE RECUPERACIÓN - PABLITO POS\n")
                        fout.write("=========================================\n")
                        fout.write("Guarde este archivo en un lugar seguro.\n")
                        fout.write("Cada código sirve para UN solo uso.\n\n")
                        for code in codes:
                            fout.write(f"[ ] {code}\n")
                        fout.write("\nGenerado el: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    app.show_success("Guardado", f"Códigos guardados en:\n{filename}")
                except Exception as exc:  # pragma: no cover - UI feedback
                    app.show_error("Error", f"No se pudo guardar el archivo:\n{exc}")

        tb.Button(btn_frame, text="💾 Guardar lista", bootstyle="info", command=save_to_file).pack(side="left", padx=5)
        tb.Button(btn_frame, text="🔄 Generar Nuevos", bootstyle="warning", command=generate_new).pack(side="right", padx=5)

        win.update_idletasks()
        app.center_window(win, 600, 600)
        app.reveal_modal(win)
        app.make_modal(win)
        app.wait_window(win)
