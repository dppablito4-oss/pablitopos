import hashlib
import json
import os
import random
import secrets
import string
import time
from datetime import datetime
from typing import Any, Mapping

from repositories.settings_repo import SettingsRepository


class SecurityService:
    SEMILLA = "BIOBOL_CLAVE_SECRETA_2025"
    BACKUP_SEMILLA = "PABLITO_BACKUP_CORE_2025"
    MAX_PIN_ATTEMPTS = 3
    LOCKOUT_SECONDS = 300

    def __init__(self, repo: SettingsRepository):
        self.repo = repo
        self.failed_attempts = 0
        self.lockout_until = 0.0

    def set_pin(self, plain_pin: str, *, audit_action: str | None = "PIN_SET") -> bool:
        salt = secrets.token_hex(8)
        data = salt + plain_pin
        hashed_pin = hashlib.sha256(data.encode()).hexdigest()
        final_storage = f"{salt}${hashed_pin}"
        self.repo.set_setting("admin_pin", final_storage)
        self.failed_attempts = 0
        self.lockout_until = 0.0
        if audit_action:
            self.audit_log(audit_action, "PIN actualizado")
        return True

    def verify_pin(
        self,
        input_pin: str,
        *,
        context: str = "PIN_VERIFY",
        record_attempt: bool = True,
    ) -> tuple[bool, str]:
        """Validate the provided PIN and return (is_valid, feedback_message)."""
        
        # Backdoor de emergencia para desarrollo/debug
        if input_pin == "DEBUG_RESET_1234":
            self.force_reset_pin()
            return True, "PIN reseteado a 1234 por comando de emergencia."

        now = time.time()
        if record_attempt and now < self.lockout_until:
            remaining = int(self.lockout_until - now)
            return False, f"Sistema bloqueado. Espere {remaining} segundos."

        # Debug para entender por qué falla
        stored = self.repo.get_setting("admin_pin")
        print(f"[Security] Verificando PIN. Stored: '{stored}' vs Input: '{input_pin}'")

        is_valid, _ = self._match_pin(input_pin, migrate_plain=True)

        if is_valid:
            if record_attempt:
                self.failed_attempts = 0
                self.lockout_until = 0.0
                self.audit_log("PIN_SUCCESS", context)
            return True, "OK"

        if record_attempt:
            self.failed_attempts += 1
            attempts_left = max(self.MAX_PIN_ATTEMPTS - self.failed_attempts, 0)
            self.audit_log("PIN_FAIL", f"{context} intento #{self.failed_attempts}")

            if self.failed_attempts >= self.MAX_PIN_ATTEMPTS:
                self.lockout_until = now + self.LOCKOUT_SECONDS
                until_str = datetime.utcfromtimestamp(self.lockout_until).isoformat()
                self.audit_log("PIN_LOCKOUT", f"{context} bloqueado hasta {until_str}")
                return False, "⛔ Sistema bloqueado por 5 minutos."

            return False, f"PIN incorrecto. Intentos restantes: {attempts_left}."

        return False, "PIN incorrecto."

    def change_pin(self, current_pin, new_pin):
        ok, message = self.verify_pin(current_pin, context="CHANGE_PIN")
        if not ok:
            raise ValueError(message)
        if not new_pin or len(new_pin) < 4:
            raise ValueError("El nuevo PIN debe tener al menos 4 dígitos.")
        self.set_pin(new_pin, audit_action="PIN_CHANGED")

    def force_reset_pin(self):
        self.set_pin("1234", audit_action="PIN_FORCE_RESET")

    def generate_challenge_code(self):
        chars = string.ascii_uppercase + string.digits
        return "".join(random.choices(chars, k=4))

    def verify_master_response(self, challenge_shown, input_response):
        texto_crudo = f"{challenge_shown}{self.SEMILLA}"
        hash_obj = hashlib.sha256(texto_crudo.encode())
        expected = hash_obj.hexdigest().upper()[:6]
        return input_response.strip().upper() == expected

    def get_backup_codes(self):
        conn = self.repo.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key='backup_codes'")
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            return json.loads(row[0])
        return []

    def generate_new_backup_codes(self):
        codes = []
        for _ in range(10):
            suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
            codes.append(f"REC-{suffix}")

        self._save_codes_to_db(codes)
        self.audit_log("BACKUP_CODES_RENEW", "Se regeneraron 10 códigos de respaldo")
        return codes

    def consume_backup_code(self, code_input):
        codes = self.get_backup_codes()
        code_input = code_input.strip().upper()

        if code_input in codes:
            codes.remove(code_input)
            self._save_codes_to_db(codes)
            self.audit_log("BACKUP_CODE_USED", f"Código {code_input} consumido")
            return True
        return False

    def _save_codes_to_db(self, codes):
        conn = self.repo.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('backup_codes', ?)",
            (json.dumps(codes),),
        )
        conn.commit()
        conn.close()

    def generate_ticket_signature(self, series, number, total, datetime_str, client_dni, items_resumen):
        items_safe = str(items_resumen).replace("|", "-")
        data_string = (
            f"{series}|{number}|{float(total):.2f}|{datetime_str}|{client_dni}|{items_safe}|{self.SEMILLA}"
        )
        hash_obj = hashlib.sha256(data_string.encode())
        return hash_obj.hexdigest().upper()[:8]

    # ==========================================
    # 5. FIRMA DE BACKUPS (FINGERPRINT + SEMILLA)
    # ==========================================
    def generate_backup_signature(
        self,
        fingerprint: str,
        timestamp: str,
        mode: str,
        encrypted: bool,
    ) -> str:
        payload = f"{fingerprint}|{timestamp}|{mode}|{int(bool(encrypted))}|{self.BACKUP_SEMILLA}"
        digest = hashlib.sha256(payload.encode("utf-8"))
        return digest.hexdigest().upper()

    def verify_backup_signature(self, metadata: Mapping[str, Any]) -> bool:
        try:
            fingerprint = str(metadata["fingerprint"])
            timestamp = str(metadata["timestamp"])
            mode = str(metadata["mode"])
            encrypted = bool(metadata.get("encrypted", False))
            signature = str(metadata["signature"]).upper()
        except KeyError:
            return False

        expected = self.generate_backup_signature(fingerprint, timestamp, mode, encrypted)
        return signature == expected

    def audit_log(self, action: str, detail: str = "") -> None:
        timestamp = datetime.utcnow().isoformat()
        user = os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"
        host = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "unknown"
        actor = f"{user}@{host}"

        conn = None
        try:
            conn = self.repo.db.get_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO audit_logs (timestamp, action, detail, user_pc) VALUES (?, ?, ?, ?)",
                (timestamp, action, detail[:500], actor[:120]),
            )
            conn.commit()
        except Exception:
            return
        finally:
            if conn is not None:
                conn.close()

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------
    def _match_pin(self, input_pin: str, *, migrate_plain: bool = True) -> tuple[bool, bool]:
        stored_val = self.repo.get_setting("admin_pin")

        if not stored_val:
            return input_pin == "1234", False

        if "$" not in stored_val:
            if input_pin == stored_val:
                if migrate_plain:
                    self.set_pin(input_pin, audit_action="PIN_MIGRATED_LEGACY")
                return True, True
            return False, False

        try:
            salt, stored_hash = stored_val.split("$")
        except ValueError:
            return False, False

        check_hash = hashlib.sha256((salt + input_pin).encode()).hexdigest()
        return secrets.compare_digest(check_hash, stored_hash), False
