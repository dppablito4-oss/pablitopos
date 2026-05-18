"""Backup and restore helpers extracted from the main application."""

from __future__ import annotations

import glob
import hashlib
import json
import os
import platform
import shutil
import sys
import uuid
import zipfile
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, cast

import tkinter as tk
from tkinter import filedialog

import ttkbootstrap as tb

import settings

try:  # Opcional para cifrado AES en ZIP
    import pyzipper  # type: ignore
except ImportError:  # pragma: no cover - dependencia opcional
    pyzipper = None

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app_boletas import App

from services.storage_guard import StorageGuardian, StorageGuardianError


class BackupsUI:
    """Gestiona la creación y restauración de respaldos del sistema."""

    def __init__(self, app: "App") -> None:
        self.app = app

    def create_manual_backup(self) -> None:
        app = self.app

        win = tb.Toplevel(master=app)
        app.begin_modal_construction(win)
        win.title("Crear Backup")
        win.geometry("550x450")
        app.set_app_icon(win)

        container = tb.Frame(win, padding=20)
        container.pack(fill="both", expand=True)

        tb.Label(
            container,
            text="Selecciona el tipo de copia de seguridad",
            font=("Segoe UI", 13, "bold"),
        ).pack(pady=(0, 10))

        tb.Label(
            container,
            text="\n• Copia de Seguridad (Móvil): clona archivos encriptados para migración controlada."
                 "\n• Exportar Portable (ZIP): genera un ZIP protegido con contraseña para compartir.",
            justify="left",
            wraplength=360,
        ).pack(pady=(0, 18))

        btn_frame = tb.Frame(container)
        btn_frame.pack(fill="x", pady=5)

        tb.Button(
            btn_frame,
            text="Copia de Seguridad (Móvil)",
            bootstyle="secondary",
            command=lambda: [win.destroy(), self._create_raw_clone_backup()],
            width=28,
        ).pack(pady=6)

        tb.Button(
            btn_frame,
            text="Exportar Portable (ZIP)",
            bootstyle="success",
            command=lambda: [win.destroy(), self._create_portable_zip_backup()],
            width=28,
        ).pack(pady=6)

        tb.Button(
            container,
            text="Cancelar",
            bootstyle="link",
            command=win.destroy,
        ).pack(pady=10)

        win.update_idletasks()
        app.center_window(win, 550, 350)
        app.reveal_modal(win)
        app.make_modal(win)

    def restore_backup(self) -> None:
        app = self.app

        if not app.show_question(
            "⚠️ Restaurar Backup",
            "ADVERTENCIA: Esta acción reemplazará todos los datos actuales.\n\n"
            "Se creará un backup de seguridad antes de continuar.\n\n"
            "¿Desea proceder?",
        ):
            return

        backup_path = filedialog.askopenfilename(
            filetypes=[("ZIP Archive", "*.zip")],
            title="Seleccionar Backup a Restaurar",
        )

        if not backup_path:
            return

        try:
            # Guardar backup de seguridad en la carpeta de datos, no en la raíz del proyecto
            backup_dir = os.path.join(settings.APPDATA_PATH, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            safety_backup = os.path.join(backup_dir, f"safety_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
            
            db_path = settings.get_db_path()
            pdf_dir = settings.PDF_DIR

            with zipfile.ZipFile(safety_backup, "w", zipfile.ZIP_DEFLATED) as zipf:
                if os.path.exists(db_path):
                    zipf.write(db_path, "boletas.sqlite3")
                if os.path.exists(pdf_dir):
                    for root, _dirs, files in os.walk(pdf_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join("pdfs", os.path.relpath(file_path, pdf_dir))
                            zipf.write(file_path, arcname)

            zip_reader = self._open_zip_reader(backup_path)
            if zip_reader is None:
                return

            with zip_reader as zipf:
                requires_password = self._archive_requires_password(zipf)
                if requires_password:
                    if pyzipper is None:
                        self.app.show_error(
                            "Dependencia faltante",
                            "Este backup está cifrado. Instala 'pyzipper' para restaurarlo:\n"
                            "pip install pyzipper",
                        )
                        return
                    password = self._prompt_zip_password(
                        title="Contraseña del Backup",
                        confirm=False,
                        hint="Ingresa la contraseña del ZIP exportable.",
                    )
                    if password is None:
                        return
                    zipf.setpassword(password.encode("utf-8"))

                metadata = self._load_metadata_from_zip(zipf)
                if not self._verify_metadata(metadata):
                    return

                file_list = zipf.namelist()
                has_plain_db = "boletas.sqlite3" in file_list
                has_encrypted = any(f.endswith(".crypt") for f in file_list)

                if not has_plain_db and not has_encrypted:
                    raise Exception("El archivo no parece contener la base de datos esperada (ni plana ni cifrada).")

                if os.path.exists(db_path):
                    os.remove(db_path)

                # Intentar liberar recursos visuales que puedan bloquear archivos (logos)
                try:
                    if hasattr(self.app, "logo_label") and self.app.logo_label:
                        self.app.logo_label.configure(image="")
                        self.app.logo_label.image = None
                    if hasattr(self.app, "logo_preview_label") and self.app.logo_preview_label:
                        self.app.logo_preview_label.configure(image="")
                        self.app.logo_preview_label.image = None
                    self.app.main_logo_image = None
                except Exception:
                    pass

                if os.path.exists(pdf_dir):
                    try:
                        shutil.rmtree(pdf_dir)
                    except OSError:
                        pass
                os.makedirs(pdf_dir, exist_ok=True)

                if os.path.exists("logos"):
                    try:
                        shutil.rmtree("logos")
                    except OSError:
                        pass
                os.makedirs("logos", exist_ok=True)

                for file in file_list:
                    if file.startswith("pdfs/"):
                        zipf.extract(file, ".")
                    elif file.startswith("logos/"):
                        zipf.extract(file, ".")
                    elif file == "boletas.sqlite3":
                        zipf.extract(file, ".")
                        extracted = os.path.join(".", "boletas.sqlite3")
                        same_target = False
                        try:
                            same_target = os.path.exists(db_path) and os.path.samefile(extracted, db_path)
                        except FileNotFoundError:
                            same_target = False
                        if os.path.exists(extracted) and not same_target:
                            os.makedirs(os.path.dirname(db_path), exist_ok=True)
                            # Usar shutil.move en lugar de os.replace para evitar WinError 17 entre unidades
                            shutil.move(extracted, db_path)
                    elif file.endswith(".crypt") or file.endswith(".lock"):
                        # Restaurar archivos cifrados en la carpeta de datos (APPDATA)
                        # Extraer directamente en APPDATA_PATH sin crear subcarpetas del ZIP si las hubiera
                        target_dir = settings.APPDATA_PATH
                        filename = os.path.basename(file)
                        target_path = os.path.join(target_dir, filename)
                        
                        # Extraer a temporal (preservando estructura del zip si la tiene)
                        zipf.extract(file, ".")
                        
                        # La ruta extraída es relativa a "." + el nombre del archivo en el zip
                        extracted_source = os.path.join(".", file)
                        
                        if os.path.exists(extracted_source):
                            if os.path.exists(target_path):
                                try:
                                    os.remove(target_path)
                                except OSError:
                                    pass
                            
                            # Mover al destino final (APPDATA)
                            shutil.move(extracted_source, target_path)
                            print(f"[Restore] Movido {extracted_source} -> {target_path}")

            # INTENTO DE DESENCRIPTACIÓN INMEDIATA (Solo si se restauraron archivos cifrados y NO hay base plana)
            if has_encrypted and not has_plain_db:
                try:
                    print("[Restore] Intentando desencriptación in-situ...")
                    # Re-inicializar guardian para leer los nuevos locks restaurados
                    temp_guard = StorageGuardian(base_dir=settings.APPDATA_PATH, master_secret=settings.SECURITY_MASTER_SECRET)
                    
                    # Intentar desbloquear con hardware local
                    unlock = None
                    try:
                        unlock = temp_guard.unlock_with_hardware()
                    except Exception as e:
                        print(f"[Restore] No se pudo desbloquear con hardware local: {e}")
                    
                    if unlock:
                        plain_target = settings.get_db_path()
                        print(f"[Restore] Desencriptando a: {plain_target}")
                        temp_guard.decrypt_database(output_path=plain_target, key=unlock.key)
                        print("[Restore] Desencriptación in-situ EXITOSA.")
                except Exception as e:
                    print(f"[Restore] Advertencia: Falló la desencriptación in-situ: {e}")
            
            # Si se restauró una base plana, sería bueno actualizar la copia encriptada para que estén sincronizadas
            elif has_plain_db:
                 try:
                    print("[Restore] Sincronizando copia encriptada desde base plana restaurada...")
                    temp_guard = StorageGuardian(base_dir=settings.APPDATA_PATH, master_secret=settings.SECURITY_MASTER_SECRET)
                    # Intentamos desbloquear (o usar fingerprint local si no hay lock restaurado)
                    try:
                        unlock = temp_guard.unlock_with_hardware()
                    except:
                        # Si falla (ej. backup legacy sin locks), usamos el hardware actual para crear nuevos locks
                        unlock = None
                    
                    if unlock:
                        plain_source = settings.get_db_path()
                        temp_guard.encrypt_database_from_plain(plain_path=plain_source, key=unlock.key)
                        print("[Restore] Sincronización de encriptación EXITOSA.")
                 except Exception as e:
                     print(f"[Restore] No se pudo sincronizar encriptación (no crítico): {e}")

            app.show_success(
                "Restauración Completa",
                "Backup restaurado exitosamente.\n\n"
                f"Se creó un backup de seguridad en:\n{safety_backup}\n\n"
                "La aplicación se reiniciará ahora.",
            )
            try:
                # Intentar cerrar conexiones antes de reiniciar
                if hasattr(app, "sale_repo") and hasattr(app.sale_repo, "db"):
                    app.sale_repo.db.close()
            except Exception:
                pass

            app.destroy()
            # Reiniciar aplicación de forma segura (manejando espacios en rutas)
            import subprocess
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit()

        except Exception as exc:  # pragma: no cover - UI feedback
            app.show_error("Error al restaurar", f"No se pudo restaurar el backup:\n{exc}")

    # ------------------------------------------------------------------
    # Flujos internos
    # ------------------------------------------------------------------
    def _create_raw_clone_backup(self) -> None:
        app = self.app
        # Forzar encriptación de la base de datos actual para asegurar que el backup tenga los últimos datos
        # Forzar encriptación de la base de datos actual para asegurar que el backup tenga los últimos datos
        if app.storage_guard and app._storage_unlock:
            print("[Backup] Iniciando actualización de base de datos cifrada...")
            try:
                plain = app._runtime_db_path()
                print(f"[Backup] Encriptando desde: {plain}")
                app.storage_guard.encrypt_database_from_plain(plain_path=plain, key=app._storage_unlock.key)
                print("[Backup] Encriptación actualizada correctamente.")
            except Exception as e:
                print(f"Error actualizando backup cifrado: {e}")
                app.show_error("Error de Backup", f"No se pudo actualizar la copia cifrada antes del backup:\n{e}")
                return
        else:
            print("[Backup] ADVERTENCIA: No se pudo actualizar el cifrado (Falta guard o unlock).")
            print(f"  - storage_guard: {app.storage_guard}")
            print(f"  - _storage_unlock: {app._storage_unlock}")
            app.show_warning(
                "Backup Incompleto",
                "No se pudo verificar la seguridad de la base de datos.\nEl backup podría contener datos antiguos.\n\nReinicie la aplicación e intente nuevamente."
            )
            return

        db_path = settings.get_db_path()
        guardian = getattr(app, "storage_guard", None)
        base_dir = getattr(guardian, "base_dir", os.path.dirname(settings.DEFAULT_DB_PATH))
        artifacts = self._collect_encrypted_artifacts(base_dir)

        if not artifacts:
            app.show_warning(
                "Sin archivos encriptados",
                "No se encontraron archivos .crypt o .lock para copiar."
                "\nSe copiará la base de datos actual como contingencia.",
            )
            if os.path.exists(db_path):
                artifacts.append(db_path)
            else:
                return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"BACKUP_MOVIL_{timestamp}.zip"

        target_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP Archive", "*.zip")],
            title="Guardar Copia de Seguridad (Móvil)",
            initialfile=default_name,
        )
        if not target_path:
            return

        try:
            with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for src in artifacts:
                    zf.write(src, os.path.basename(src))
                self._write_metadata_entry(zf, mode="raw_clone", encrypted=True)
            
            self.app.settings_service.audit_log(
                "BACKUP_RAW",
                f"ZIP Móvil -> {target_path}",
            )
        except Exception as exc:
            app.show_error("Error de Copia", f"No se pudo crear el backup móvil:\n{exc}")
            return

        app.show_success(
            "Copia completada",
            "Se generó el backup móvil en:\n"
            f"{target_path}",
        )

    def _create_portable_zip_backup(self) -> None:
        app = self.app

        if pyzipper is None:
            app.show_error(
                "Dependencia faltante",
                "Instala la librería 'pyzipper' para generar ZIP cifrados:\n"
                "pip install pyzipper",
            )
            return

        if not app.ask_pin("Exportar Backup Portable", allow_recovery=False):
            return

        password = self._prompt_zip_password(
            title="Contraseña para el ZIP",
            hint="Define la contraseña que protegerá el backup portable.",
            confirm=True,
        )
        if password is None:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"BACKUP_PORTABLE_{timestamp}.zip"

        backup_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP Archive", "*.zip")],
            title="Guardar Backup Portable",
            initialfile=default_name,
        )

        if not backup_path:
            return

        try:
            with pyzipper.AESZipFile(backup_path, "w", compression=pyzipper.ZIP_LZMA) as zipf:
                zipf.setpassword(password.encode("utf-8"))
                zipf.setencryption(pyzipper.WZ_AES, nbits=256)
                self._write_standard_payload(zipf)
                self._write_metadata_entry(zipf, mode="portable_zip", encrypted=True)

            size_mb = os.path.getsize(backup_path) / (1024 * 1024)
            try:
                self.app.settings_service.audit_log(
                    "BACKUP_PORTABLE",
                    f"ZIP cifrado -> {backup_path}",
                )
            except Exception:
                pass
            app.show_success(
                "Backup exportado",
                f"ZIP cifrado guardado en:\n{backup_path}\n\nTamaño: {size_mb:.2f} MB",
            )

        except Exception as exc:  # pragma: no cover - UI feedback
            app.show_error("Error al exportar", f"No se pudo generar el backup portable:\n{exc}")

    # ------------------------------------------------------------------
    # Utilitarios
    # ------------------------------------------------------------------
    def _collect_encrypted_artifacts(self, base_dir: str) -> list[str]:
        artifacts: list[str] = []
        for pattern in ("*.crypt", "*.lock"):
            artifacts.extend(glob.glob(os.path.join(base_dir, pattern)))
        return sorted(set(artifacts))

    def _write_standard_payload(self, zipf: Any) -> None:
        db_path = settings.get_db_path()
        pdf_dir = settings.PDF_DIR

        if os.path.exists(db_path):
            zipf.write(db_path, "boletas.sqlite3")

        if os.path.exists(pdf_dir):
            for root, _dirs, files in os.walk(pdf_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join("pdfs", os.path.relpath(file_path, pdf_dir))
                    zipf.write(file_path, arcname)

        logo_dir = "logos"
        if os.path.exists(logo_dir):
            for root, _dirs, files in os.walk(logo_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join("logos", os.path.relpath(file_path, logo_dir))
                    zipf.write(file_path, arcname)

    def _write_metadata_entry(self, zipf: Any, *, mode: str, encrypted: bool) -> None:
        info = self._build_metadata(mode=mode, encrypted=encrypted)
        zipf.writestr("backup_info.json", json.dumps(info, indent=2))

    def _write_metadata_file(self, destination: str, *, mode: str) -> None:
        info = self._build_metadata(mode=mode, encrypted=False)
        metadata_path = os.path.join(destination, "backup_info.json")
        with open(metadata_path, "w", encoding="utf-8") as fh:
            json.dump(info, fh, indent=2)

    def _prompt_zip_password(
        self,
        *,
        title: str,
        hint: str,
        confirm: bool,
        min_length: int = 6,
    ) -> Optional[str]:
        app = self.app
        result: Optional[str] = None

        dialog = tb.Toplevel(master=app)
        app.begin_modal_construction(dialog)
        dialog.title(title)
        dialog.geometry("360x250")
        app.set_app_icon(dialog)

        password_var = tk.StringVar()
        confirm_var = tk.StringVar()

        tb.Label(dialog, text=hint, wraplength=320, justify="left").pack(pady=(15, 10))

        entry = tb.Entry(dialog, show="•", textvariable=password_var, font=("Segoe UI", 12))
        entry.pack(pady=4, padx=20, fill="x")
        entry.focus_set()

        confirm_entry = None
        if confirm:
            confirm_entry = tb.Entry(dialog, show="•", textvariable=confirm_var, font=("Segoe UI", 12))
            confirm_entry.pack(pady=4, padx=20, fill="x")

        error_label = tb.Label(dialog, text="", bootstyle="danger")
        error_label.pack(pady=(6, 2))

        def validate_and_close(_event: Optional[tk.Event] = None) -> None:
            nonlocal result
            password = password_var.get().strip()
            confirmation = confirm_var.get().strip()

            if len(password) < min_length:
                error_label.configure(text=f"Usa al menos {min_length} caracteres.")
                return

            if confirm and password != confirmation:
                error_label.configure(text="Las contraseñas no coinciden.")
                return

            result = password
            dialog.destroy()

        btn_frame = tb.Frame(dialog)
        btn_frame.pack(pady=12)

        tb.Button(btn_frame, text="Cancelar", bootstyle="secondary", command=dialog.destroy, width=12).pack(side="left", padx=6)
        tb.Button(btn_frame, text="Aceptar", bootstyle="success", command=validate_and_close, width=12).pack(side="left", padx=6)

        entry.bind("<Return>", validate_and_close)
        if confirm_entry:
            confirm_entry.bind("<Return>", validate_and_close)
            confirm_dialog.bind("<Escape>", lambda _e: confirm_dialog.destroy())

        dialog.update_idletasks()
        app.center_window(dialog, 360, 250)
        app.reveal_modal(dialog)
        app.make_modal(dialog)
        app.wait_window(dialog)

        return result

    def _open_zip_reader(self, path: str) -> Optional[zipfile.ZipFile]:
        if pyzipper is not None:
            return cast(zipfile.ZipFile, pyzipper.AESZipFile(path, "r"))
        try:
            return zipfile.ZipFile(path, "r")
        except Exception as exc:  # pragma: no cover - feedback
            self.app.show_error("Error", f"No se pudo abrir el archivo de backup:\n{exc}")
            return None

    def _archive_requires_password(self, zipf: zipfile.ZipFile) -> bool:
        try:
            infos = zipf.infolist()
        except Exception:
            return False
        return any(info.flag_bits & 0x1 for info in infos)

    def _build_metadata(self, *, mode: str, encrypted: bool) -> dict[str, Any]:
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        fingerprint = self._machine_fingerprint()
        info: dict[str, Any] = {
            "version": "2.0",
            "timestamp": timestamp,
            "mode": mode,
            "encrypted": bool(encrypted),
            "computer_name": os.environ.get("COMPUTERNAME", "Unknown"),
            "user": os.environ.get("USERNAME", "Unknown"),
            "fingerprint": fingerprint,
        }
        signature = self.app.settings_service.generate_backup_signature(
            fingerprint=fingerprint,
            timestamp=timestamp,
            mode=mode,
            encrypted=encrypted,
        )
        info["signature"] = signature
        return info

    def _machine_fingerprint(self) -> str:
        node = platform.node()
        system = platform.system()
        mac = uuid.getnode()
        raw = f"{node}|{system}|{mac}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest().upper()

    def _load_metadata_from_zip(self, zipf: zipfile.ZipFile) -> Optional[dict[str, Any]]:
        try:
            content = zipf.read("backup_info.json")
        except KeyError:
            return None
        try:
            return json.loads(content.decode("utf-8"))
        except Exception:
            return None

    def _verify_metadata(self, metadata: Optional[dict[str, Any]]) -> bool:
        if not metadata:
            return True

        if not self.app.settings_service.verify_backup_signature(metadata):
            self.app.show_error(
                "Firma inválida",
                "La firma del backup no coincide. El archivo podría estar corrompido o alterado.",
            )
            return False

        expected_fingerprint = self._machine_fingerprint()
        stored_fingerprint = metadata.get("fingerprint", "")
        if stored_fingerprint and stored_fingerprint != expected_fingerprint:
            self.app.show_warning(
                "Equipo diferente",
                "El respaldo proviene de otro equipo. Se requiere el flujo de recuperación móvil antes de usarlo.",
            )
        return True
