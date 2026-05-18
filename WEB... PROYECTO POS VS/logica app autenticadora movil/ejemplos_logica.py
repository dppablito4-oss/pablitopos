import hashlib
import random
import string
import platform
import uuid

# ==============================================================================
# CONFIGURACIÓN COMPARTIDA (Debe coincidir en la App Móvil)
# ==============================================================================
SEMILLA_SECRETA = "BIOBOL_CLAVE_SECRETA_2025"
MASTER_SECRET = "PABLITO_MASTER_SECRET_V1"

# ==============================================================================
# 1. RECUPERACIÓN DE CONTRASEÑA DE ADMIN (Challenge-Response)
# ==============================================================================
def generar_reto():
    """
    Genera un código aleatorio de 4 caracteres (ej: 'ABCD').
    Este código se muestra en la pantalla del PC.
    """
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=4))

def verificar_respuesta(reto_mostrado, respuesta_ingresada):
    """
    Verifica si la respuesta ingresada es válida para el reto mostrado.
    
    Lógica:
    1. Concatenar RETO + SEMILLA.
    2. Calcular hash SHA256.
    3. Tomar los primeros 6 caracteres del hash en mayúsculas.
    """
    texto_crudo = f"{reto_mostrado.strip().upper()}{SEMILLA_SECRETA}"
    hash_obj = hashlib.sha256(texto_crudo.encode())
    
    # La respuesta esperada son los primeros 6 caracteres del hash
    esperado = hash_obj.hexdigest().upper()[:6]

    return respuesta_ingresada.strip().upper() == esperado

# ==============================================================================
# 2. VERIFICACIÓN DE BOLETA (Firma Digital)
# ==============================================================================
def generar_firma_boleta(serie, numero, total, fecha_hora, dni_cliente, items_resumen):
    """
    Genera una firma única de 8 caracteres para la boleta.
    Cualquier cambio en los datos invalidará esta firma.
    
    Parámetros:
    - serie: Serie de la boleta (ej: 'B001')
    - numero: Número correlativo (ej: '0000123')
    - total: Monto total (ej: 150.00)
    - fecha_hora: Fecha y hora exacta (ej: '2023-10-27 10:30:00')
    - dni_cliente: DNI o RUC del cliente
    - items_resumen: Cadena resumen de los productos
    """
    # Normalizar datos para evitar errores por espacios o formatos
    # Reemplazamos pipes | por guiones para evitar conflictos con el separador
    items_safe = str(items_resumen).replace("|", "-")

    # Forzamos mayúsculas/trim en campos clave y total con dos decimales estilo US
    serie = str(serie).strip().upper()
    numero = str(numero).strip().upper()
    dni_cliente = str(dni_cliente).strip().upper()
    fecha_hora = str(fecha_hora).strip()
    total_num = float(total)
    
    # Construir la cadena de datos separada por pipes
    data_string = (
        f"{serie}|{numero}|{total_num:.2f}|{fecha_hora}|"
        f"{dni_cliente}|{items_safe}|{SEMILLA_SECRETA}"
    )
    
    # Generar hash SHA256
    hash_obj = hashlib.sha256(data_string.encode())
    
    # Retornar los primeros 8 caracteres como "Serial de Seguridad"
    return hash_obj.hexdigest().upper()[:8]

# ==============================================================================
# 3. BACKUP Y BLOQUEO POR ID DE HARDWARE (Storage Guardian)
# ==============================================================================
def obtener_huella_hardware():
    """
    Genera un ID único para la computadora actual.
    Combina Nombre PC + Sistema Operativo + Arquitectura + Dirección MAC.
    """
    node = platform.node() or "unknown"
    system = platform.system() or "unknown"
    machine = platform.machine() or "?"
    mac = uuid.getnode()
    
    raw_data = f"{node}|{system}|{machine}|{mac}".encode("utf-8")
    return hashlib.sha256(raw_data).hexdigest().upper()

def generar_codigo_emergencia(fingerprint):
    """
    Genera el código OTP de 4 dígitos para desbloquear la DB en una PC nueva.
    
    Lógica:
    1. Concatenar FINGERPRINT + MASTER_SECRET + "AUTHV1"
    2. Calcular hash SHA256.
    3. Tomar los primeros 4 caracteres.
    """
    payload = f"{fingerprint.strip().upper()}|{MASTER_SECRET}|AUTHV1"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()
    return digest[:4]  # Código de 4 dígitos que el usuario debe ingresar
