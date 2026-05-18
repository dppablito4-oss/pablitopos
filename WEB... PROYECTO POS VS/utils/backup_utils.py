import os
import shutil
import zipfile
from datetime import datetime
from typing import Iterable, Tuple

import settings


def create_backup():
    """Crea una copia simple del SQLite en texto plano (modo legado)."""

    db_path = settings.get_db_path()

    if not os.path.exists(db_path):
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(settings.BACKUP_DIR, f"boletas_backup_{timestamp}.sqlite3")
    try:
        os.makedirs(settings.BACKUP_DIR, exist_ok=True)
        shutil.copy2(db_path, backup_file)
        backups = sorted(
            f for f in os.listdir(settings.BACKUP_DIR) if f.startswith("boletas_backup_") and f.endswith(".sqlite3")
        )
        while len(backups) > 10:
            oldest = backups.pop(0)
            try:
                os.remove(os.path.join(settings.BACKUP_DIR, oldest))
            except OSError:
                pass
        return backup_file
    except Exception as exc:  # pragma: no cover - best effort logging
        print(f"Error en backup: {exc}")
        return None


def create_guarded_backup(
    *,
    artifacts: Iterable[Tuple[str, str]],
    dest_dir: str = settings.BACKUP_DIR,
    prefix: str = "guarded_backup",
    max_count: int = 12,
) -> str:
    """Empaqueta los artefactos cifrados (DB y locks) dentro de un ZIP con sello temporal."""

    os.makedirs(dest_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_name = f"{prefix}_{timestamp}.zip"
    target_path = os.path.join(dest_dir, target_name)

    artifact_list = list(artifacts)
    if not artifact_list:
        raise ValueError("No hay artefactos para respaldar")

    with zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src_path, arc_name in artifact_list:
            if not os.path.exists(src_path):
                raise FileNotFoundError(f"No se encontró el archivo requerido: {src_path}")
            zf.write(src_path, arc_name)

    # Crear un archivo ZIP 'señuelo' en la carpeta del proyecto (si es escribible)
    # para mantener visible un backup sin contener datos reales. Esto no
    # reemplaza ni filtra el backup real que queda en `dest_dir`.
    try:
        import sys

        project_dir = os.path.dirname(os.path.abspath(__file__))
        # Intentar usar el directorio del ejecutable cuando la app esté "frozen"
        if getattr(sys, "frozen", False):
            proj_root = os.path.dirname(sys.executable)
        else:
            proj_root = project_dir

        decoy_name = os.path.basename(target_path)
        decoy_path = os.path.join(proj_root, decoy_name)

        # No sobreescribir si ya existe
        if not os.path.exists(decoy_path):
            # Crear un ZIP pequeño con un archivo de texto que indique que es señuelo
            try:
                with zipfile.ZipFile(decoy_path, "w", compression=zipfile.ZIP_DEFLATED) as dzf:
                    dzf.writestr("README.txt", "Este archivo es un respaldo señuelo. Los datos reales se guardan en el perfil del usuario (APPDATA).\n")
            except Exception:
                # No hacemos ruido si no es posible escribir en la carpeta de instalación
                pass
    except Exception:
        pass

    existing = sorted(
        f for f in os.listdir(dest_dir) if f.startswith(prefix) and f.endswith(".zip")
    )
    while len(existing) > max_count:
        remove_name = existing.pop(0)
        try:
            os.remove(os.path.join(dest_dir, remove_name))
        except OSError:
            pass

    return target_path
