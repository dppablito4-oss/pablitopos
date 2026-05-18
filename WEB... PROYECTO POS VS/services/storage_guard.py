"""Helpers to protect the SQLite database using symmetric encryption locks.

This module is the first step for the hardware-bound storage plan:
- The plain database is wrapped into ``boletas.sqlite3.crypt`` using a random
  secret ("Llave Dorada").
- ``security_hw.lock`` stores the same Llave Dorada encrypted with a key
  derived from the current hardware fingerprint.
- ``security_mobile.lock`` keeps an emergency copy encrypted with the
  ``master_secret`` so the mobile app can unlock new machines on demand.

At this stage the helpers do not hook into the startup flow yet; they simply
provide utilities to create and recover the encrypted bundle.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

try:  # Optional dependency – already required for portable backups
    import pyzipper  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    pyzipper = None  # type: ignore


class StorageGuardianError(Exception):
    """Raised when the storage guard cannot complete an operation."""


@dataclass(slots=True)
class UnlockResult:
    """Holds the Llave Dorada and metadata extracted from a lock."""

    key: str
    fingerprint: str
    issued_at: str


class StorageGuardian:
    """Manages the encrypted storage bundle (DB + hardware/mobile locks)."""

    DB_ENCRYPTED_NAME = "boletas.sqlite3.crypt"
    HW_LOCK_NAME = "security_hw.lock"
    MOBILE_LOCK_NAME = "security_mobile.lock"

    LOCK_VERSION = "1.0"
    HW_SALT = "BIOBOL_HW_LOCK_V1"
    MOBILE_SALT = "BIOBOL_MOBILE_LOCK_V1"

    def __init__(self, *, base_dir: str, master_secret: str) -> None:
        if not master_secret or not master_secret.strip():
            raise StorageGuardianError("El master_secret no puede estar vacío.")

        self.base_dir = os.path.abspath(base_dir)
        self.master_secret = master_secret.strip()

        self.db_plain_path = os.path.join(self.base_dir, "boletas.sqlite3")
        self.db_encrypted_path = os.path.join(self.base_dir, self.DB_ENCRYPTED_NAME)
        self.hw_lock_path = os.path.join(self.base_dir, self.HW_LOCK_NAME)
        self.mobile_lock_path = os.path.join(self.base_dir, self.MOBILE_LOCK_NAME)

    # ------------------------------------------------------------------
    # High level operations
    # ------------------------------------------------------------------
    def has_encrypted_bundle(self) -> bool:
        """Return True if all encrypted artifacts already exist."""

        return (
            os.path.exists(self.db_encrypted_path)
            and os.path.exists(self.hw_lock_path)
            and os.path.exists(self.mobile_lock_path)
        )

    def ensure_encrypted_bundle(self) -> None:
        """Create the encrypted layout if it does not exist yet."""

        if self.has_encrypted_bundle():
            return

        if not os.path.exists(self.db_plain_path):
            raise StorageGuardianError(
                f"No se encontró la base de datos en {self.db_plain_path}"
            )

        dorada_key = self._generate_dorada_key()
        db_bytes = self._read_file(self.db_plain_path)
        encrypted_db = self._encrypt_bytes(db_bytes, dorada_key)
        self._write_file(self.db_encrypted_path, encrypted_db)

        fingerprint = self.hardware_fingerprint()
        self._write_hw_lock(dorada_key, fingerprint)
        self._write_mobile_lock(dorada_key)

    def decrypt_database(self, *, output_path: str, key: str) -> None:
        """Decrypt ``boletas.sqlite3.crypt`` into ``output_path`` using the key."""

        if not os.path.exists(self.db_encrypted_path):
            raise StorageGuardianError("No existe la base de datos cifrada aún.")

        data = self._read_file(self.db_encrypted_path)
        print(f"[StorageGuardian] Decrypting {len(data)} bytes from {self.db_encrypted_path}")
        plain = self._decrypt_bytes(data, key)
        print(f"[StorageGuardian] Decrypted {len(plain)} bytes.")
        self._write_file(output_path, plain)

    def encrypt_database_from_plain(self, *, plain_path: str, key: str) -> None:
        """Encrypt ``plain_path`` and overwrite the encrypted DB using ``key``."""

        if not os.path.exists(plain_path):
            raise StorageGuardianError(f"No se encontró el archivo {plain_path}")

        data = self._read_file(plain_path)
        print(f"[StorageGuardian] Encrypting {len(data)} bytes from {plain_path}")
        encrypted = self._encrypt_bytes(data, key)
        print(f"[StorageGuardian] Encrypted size: {len(encrypted)} bytes.")
        self._write_file(self.db_encrypted_path, encrypted)

    def unlock_with_hardware(self) -> UnlockResult:
        """Return the Llave Dorada using the current hardware fingerprint."""

        fingerprint = self.hardware_fingerprint()
        password = self._derive_hw_password(fingerprint)
        payload = self._read_lock_file(self.hw_lock_path, password)

        if payload.get("fingerprint") != fingerprint:
            raise StorageGuardianError(
                "La huella del hardware no coincide con la registrada."
            )

        return UnlockResult(
            key=payload["key"],
            fingerprint=payload["fingerprint"],
            issued_at=payload["issued_at"],
        )

    def unlock_with_master(self) -> UnlockResult:
        """Return the Llave Dorada using the master_secret (flujo móvil)."""

        password = self._derive_master_password()
        payload = self._read_lock_file(self.mobile_lock_path, password)
        return UnlockResult(
            key=payload["key"],
            fingerprint=payload["fingerprint"],
            issued_at=payload["issued_at"],
        )

    def refresh_hardware_lock(self, *, key: str, new_fingerprint: str | None = None) -> None:
        """Re-write ``security_hw.lock`` for a new machine fingerprint."""

        fingerprint = new_fingerprint or self.hardware_fingerprint()
        self._write_hw_lock(key, fingerprint)

    def refresh_mobile_lock(self, *, key: str) -> None:
        """Re-write ``security_mobile.lock`` (por ejemplo si cambia el secreto)."""

        self._write_mobile_lock(key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def hardware_fingerprint() -> str:
        node = platform.node() or "unknown-host"
        system = platform.system() or "unknown"  # Windows / Linux / Darwin
        machine = platform.machine() or "?"
        mac = uuid.getnode()
        raw = f"{node}|{system}|{machine}|{mac}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest().upper()

    def _write_hw_lock(self, key: str, fingerprint: str) -> None:
        password = self._derive_hw_password(fingerprint)
        payload = self._build_lock_payload(key, fingerprint)
        data = self._encrypt_bytes(payload, password)
        self._write_file(self.hw_lock_path, data)

    def _write_mobile_lock(self, key: str) -> None:
        password = self._derive_master_password()
        payload = self._build_lock_payload(key, self.hardware_fingerprint())
        data = self._encrypt_bytes(payload, password)
        self._write_file(self.mobile_lock_path, data)

    def _build_lock_payload(self, key: str, fingerprint: str) -> bytes:
        payload = {
            "version": self.LOCK_VERSION,
            "key": key,
            "fingerprint": fingerprint,
            "issued_at": self._utc_now(),
        }
        return json.dumps(payload, separators=(",", ":")).encode("utf-8")

    def _read_lock_file(self, path: str, password: str) -> dict[str, Any]:
        if not os.path.exists(path):
            raise StorageGuardianError(f"No se encontró el archivo {path}")

        data = self._read_file(path)
        decrypted = self._decrypt_bytes(data, password)
        try:
            payload = json.loads(decrypted.decode("utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            raise StorageGuardianError("El lock se encuentra dañado o alterado.") from exc
        return payload

    @staticmethod
    def _generate_dorada_key() -> str:
        raw = secrets.token_bytes(32)
        return base64.urlsafe_b64encode(raw).decode("ascii")

    def _derive_hw_password(self, fingerprint: str) -> str:
        value = f"{fingerprint}:{self.HW_SALT}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _derive_master_password(self) -> str:
        value = f"{self.master_secret}:{self.MOBILE_SALT}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _encrypt_bytes(self, data: bytes, password: str) -> bytes:
        if pyzipper is None:
            raise StorageGuardianError(
                "pyzipper no está instalado. Instala 'pyzipper' para cifrar archivos."
            )
        buffer = BytesIO()
        with pyzipper.AESZipFile(buffer, "w", compression=pyzipper.ZIP_LZMA) as zipf:
            zipf.setpassword(password.encode("utf-8"))
            zipf.setencryption(pyzipper.WZ_AES, nbits=256)
            zipf.writestr("payload.bin", data)
        return buffer.getvalue()

    def _decrypt_bytes(self, data: bytes, password: str) -> bytes:
        if pyzipper is None:
            raise StorageGuardianError(
                "pyzipper no está instalado. Instala 'pyzipper' para descifrar archivos."
            )
        buffer = BytesIO(data)
        with pyzipper.AESZipFile(buffer, "r") as zipf:
            zipf.setpassword(password.encode("utf-8"))
            try:
                return zipf.read("payload.bin")
            except RuntimeError as exc:
                raise StorageGuardianError("Contraseña incorrecta para el lock o DB.") from exc

    @staticmethod
    def _read_file(path: str) -> bytes:
        with open(path, "rb") as fh:
            return fh.read()

    @staticmethod
    def _write_file(path: str, data: bytes) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()


__all__ = ["StorageGuardian", "StorageGuardianError", "UnlockResult"]
