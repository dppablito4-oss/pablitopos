import hashlib
import random
import string
import json

class SecurityService:
    # --- 🔐 TU SECRETO MÁXIMO ---
    # Esta clave debe ser IDÉNTICA en tu generador personal.
    SEMILLA = "BIOBOL_CLAVE_SECRETA_2025"  
    
    def __init__(self, repo):
        self.repo = repo

    # ==========================================
    # 1. GESTIÓN DE PIN
    # ==========================================
    def verify_pin(self, input_pin):
        """Verifica si el PIN ingresado es correcto."""
        current = self.repo.get_pin()
        return input_pin == current

    def change_pin(self, current_pin, new_pin):
        """Cambia el PIN (usado en la ventana de cambio obligatorio)."""
        self.repo.set_pin(new_pin)
        
    def force_reset_pin(self):
        """
        Resetea el PIN a '1234' temporalmente tras una recuperación exitosa.
        La UI debe detectar esto y obligar al usuario a cambiarlo inmediatamente.
        """
        self.repo.set_pin("1234")

    # ==========================================
    # 2. MÉTODO A: DESAFÍO - RESPUESTA (MATEMÁTICO)
    # ==========================================
    
    def generate_challenge_code(self):
        """Genera el código aleatorio (Reto) que se muestra en pantalla."""
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=4))

    def verify_master_response(self, challenge_shown, input_response):
        """
        Valida la respuesta usando la fórmula matemática:
        SHA256( Reto + Semilla ) = Respuesta
        """
        # 1. Concatenar
        texto_crudo = f"{challenge_shown}{self.SEMILLA}"
        
        # 2. Hashear
        hash_obj = hashlib.sha256(texto_crudo.encode())
        expected = hash_obj.hexdigest().upper()[:6]
        
        # 3. Comparar
        return input_response.strip().upper() == expected

    # ==========================================
    # 3. MÉTODO B: CÓDIGOS DE RESPALDO (BACKUP CODES)
    # ==========================================

    def get_backup_codes(self):
        """Obtiene la lista de códigos activos desde la BD."""
        conn = self.repo.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key='backup_codes'")
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            return json.loads(row[0])
        return []

    def generate_new_backup_codes(self):
        """Genera 10 códigos nuevos (ej: REC-A1B2) y los guarda."""
        codes = []
        for _ in range(10):
            # Generamos sufijo aleatorio de 4 caracteres
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            codes.append(f"REC-{suffix}")
        
        self._save_codes_to_db(codes)
        return codes

    def consume_backup_code(self, code_input):
        """
        Verifica si el código es válido. Si lo es, LO BORRA (un solo uso)
        y devuelve True para permitir el acceso.
        """
        codes = self.get_backup_codes()
        code_input = code_input.strip().upper()
        
        if code_input in codes:
            codes.remove(code_input) # Se quema el código usado
            self._save_codes_to_db(codes)
            return True
        return False

    def _save_codes_to_db(self, codes):
        """Guarda la lista de códigos en la base de datos como JSON."""
        conn = self.repo.db.get_connection()
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('backup_codes', ?)", (json.dumps(codes),))
        conn.commit()
        conn.close()
    # ==========================================
    # 4. FIRMA DIGITAL DE BOLETAS (HMAC) - ACTUALIZADO
    # ==========================================
    
    def generate_ticket_signature(self, series, number, total, datetime_str, client_dni, items_resumen):
        """
        Crea firma única incluyendo el resumen de productos.
        Fórmula: SHA256( SERIE | NUM | TOTAL | FECHA | DNI | ITEMS | SEMILLA )
        """
        # Limpieza básica para evitar errores en el string (quitar pipes | del nombre del producto para no romper el formato)
        # Convertimos a string y reemplazamos | por guiones
        items_safe = str(items_resumen).replace("|", "-")
        
        # Construimos la cadena maestra
        data_string = f"{series}|{number}|{float(total):.2f}|{datetime_str}|{client_dni}|{items_safe}|{self.SEMILLA}"
        
        # Hashing
        hash_obj = hashlib.sha256(data_string.encode())
        
        # Retornamos los primeros 8 caracteres
        return hash_obj.hexdigest().upper()[:8]