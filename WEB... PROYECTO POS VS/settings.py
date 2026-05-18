import os
import sqlite3
from typing import Final

# Definir rutas en APPDATA para installer
APPDATA_PATH: Final[str] = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "PablitoPOS",
)

DEFAULT_DB_FILENAME: Final[str] = "boletas.sqlite3"
DEFAULT_DB_PATH: Final[str] = os.path.join(APPDATA_PATH, DEFAULT_DB_FILENAME)
PDF_DIR: Final[str] = os.path.join(APPDATA_PATH, "boletas")
BACKUP_DIR: Final[str] = os.path.join(APPDATA_PATH, "backups")
RECOVERY_DIR: Final[str] = os.path.join(APPDATA_PATH, "recovery")
IGV_PORCENTAJE: Final[float] = 0.18  # 18%

# Secreto maestro para desbloqueos móviles (puede sobreescribirse por env var)
DEFAULT_MASTER_SECRET: Final[str] = "PABLITO_MASTER_SECRET_V1"
SECURITY_MASTER_SECRET: Final[str] = os.environ.get("PABLITO_MASTER_SECRET", DEFAULT_MASTER_SECRET)

_RUNTIME_DB_PATH: str = DEFAULT_DB_PATH


def get_db_path() -> str:
    """Devuelve la ruta actual del SQLite en texto plano."""

    return _RUNTIME_DB_PATH


def set_db_path(path: str) -> None:
    """Permite sobreescribir la ruta activa del SQLite en tiempo de ejecución."""

    global _RUNTIME_DB_PATH
    _RUNTIME_DB_PATH = os.path.abspath(path)
    globals()["DB_PATH"] = _RUNTIME_DB_PATH  # Compatibilidad con imports existentes


# Alias legacy para compatibilidad
DB_PATH = _RUNTIME_DB_PATH

# Crear directorios si no existen
os.makedirs(APPDATA_PATH, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(RECOVERY_DIR, exist_ok=True)


def create_decoy_db(path: str | None = None) -> None:
    """Crea un archivo SQLite minimal en la ruta especificada para actuar
    como 'señuelo' visible al usuario. No se usa para operaciones reales;
    la aplicación mantiene la DB real en la carpeta oculta runtime_plain.

    Por defecto crea `boletas.sqlite3` junto al archivo `settings.py`.
    """
    try:
        if path is None:
            base = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base, DEFAULT_DB_FILENAME)
        path = os.path.abspath(path)
        if os.path.exists(path):
            return
        # Crear archivo SQLite vacío
        os.makedirs(os.path.dirname(path), exist_ok=True)
        conn = sqlite3.connect(path)
        conn.close()
    except Exception:
        # No hacer ruido si falla la creación del archivo de señuelo
        pass
