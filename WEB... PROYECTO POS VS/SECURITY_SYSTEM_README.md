# 🔐 SISTEMA DE SEGURIDAD BIOBOL POS

## 📋 Resumen de Implementación

El sistema de seguridad ha sido completamente refactorizado y ahora cuenta con un módulo independiente (`services/security_service.py`) que maneja toda la lógica de autenticación, auditoría y recuperación.

---

## 🎯 Características Implementadas

### 1. **Módulo de Seguridad Independiente**

- **Archivo:** `services/security_service.py`
- **Clase:** `SecurityService`
- **Semilla Secreta:** `BIOBOL_CLAVE_SECRETA_2025`

### 2. **Sistema de PIN Mejorado**

- Interfaz moderna con iconos
- Validación robusta
- Opción de recuperación integrada

### 3. **Sistema de Recuperación Matemático**

- Basado en hash SHA256
- Código de desafío aleatorio
- Generador externo requerido

### 4. **Guardian de Almacenamiento (WIP)**

- Archivo: `services/storage_guard.py`
- Envuelve la base `boletas.sqlite3` en `boletas.sqlite3.crypt` usando una Llave Dorada
- Genera `security_hw.lock` (Llave Dorada cifrada con la huella del equipo)
- Genera `security_mobile.lock` (Llave Dorada cifrada con `PABLITO_MASTER_SECRET`)
- Servirá para levantar el flujo de desbloqueo por hardware/QR en la siguiente fase
- El arranque ya bloquea si la huella cambia, solicitando un código de 4 dígitos generado vía app móvil

---

## 🔄 Flujo de Autenticación

### **Autenticación Normal:**

```text
Usuario → Ingresa PIN → Sistema valida → Acceso concedido/denegado
```

### **Recuperación de Acceso:**

```text
1. Usuario hace clic en "¿Olvidé mi contraseña?"
2. Sistema genera código aleatorio (4 caracteres)
   Ejemplo: "X7Z9"
3. Usuario usa su generador personal:
   - Ingresa "X7Z9" en el generador
   - Generador calcula: SHA256("X7Z9" + "BIOBOL_CLAVE_SECRETA_2025")
   - Generador muestra primeros 6 caracteres del hash
4. Usuario ingresa la respuesta en el sistema
5. Sistema valida la respuesta
6. Si es correcta:
   - PIN se resetea temporalmente a "1234"
   - Se abre ventana obligatoria para establecer nuevo PIN
   - Usuario DEBE crear nuevo PIN (no puede cerrar la ventana)
```

---

## 🛠️ Métodos Implementados

### **En `services/security_service.py` (SecurityService):**

#### `verify_pin(input_pin)`

- Verifica si el PIN ingresado es correcto y registra auditoría/bloqueos de fuerza bruta
- **Retorna:** `(bool, str)` indicando éxito y mensaje para UI

#### `force_reset_pin()`

- Resetea el PIN a "1234" (usado después de recuperación exitosa)
- **Uso:** Solo se llama tras validación matemática correcta

#### `generate_challenge_code()`

- Genera código aleatorio de 4 caracteres (letras mayúsculas + números)
- **Ejemplo:** "X7Z9", "A3B8", "K9M2"
- **Retorna:** String de 4 caracteres

#### `verify_master_response(challenge, input_response)`

- Valida la respuesta del usuario contra el desafío
- **Fórmula:** SHA256(challenge + SEMILLA) → primeros 6 caracteres
- **Parámetros:**
  - `challenge`: El código mostrado (ej: "X7Z9")
  - `input_response`: La respuesta del usuario (6 caracteres)
- **Retorna:** `True` si coincide, `False` si no

---

### **En `app_boletas.py` (App):**

#### `ask_pin(title="Seguridad")`

- Muestra diálogo para ingresar PIN
- **Características:**
  - Ventana 350x220 px
  - Botón "¿Olvidé mi contraseña?"
  - Botones Confirmar/Cancelar
  - Validación con SecurityService
- **Retorna:** `True` si PIN correcto, `False` si no

#### `show_rescue_dialog()`

- Muestra sistema de recuperación con desafío matemático
- **Características:**
  - Genera código de desafío
  - Muestra código en grande (32pt)
  - Renderiza un QR escaneable (si `qrcode`/`Pillow` están instalados)
  - Cuerpo desplazable compatible con rueda del ratón para pantallas pequeñas
  - Entry para respuesta de 6 caracteres
  - Validación con `verify_master_response()`
  - Si es correcta → resetea PIN y abre cambio obligatorio

#### `open_force_change_pin_window()`

- Ventana modal para establecer nuevo PIN
- **Características:**
  - NO se puede cerrar con X
  - Validaciones:
    - Campos no vacíos
    - Mínimo 4 caracteres
    - Confirmación coincide
  - Guarda nuevo PIN en BD

---

## 🔑 Generador de Códigos Externo

Para que el sistema de recuperación funcione, necesitas un **generador externo** (aplicación web, script Python, etc.) que implemente la misma fórmula:

### **Fórmula del Generador:**

```python
import hashlib

SEMILLA = "BIOBOL_CLAVE_SECRETA_2025"

def generar_respuesta(codigo_desafio):
    texto = f"{codigo_desafio}{SEMILLA}"
    hash_obj = hashlib.sha256(texto.encode())
    respuesta = hash_obj.hexdigest().upper()[:6]
    return respuesta

# Ejemplo:
codigo = "X7Z9"
respuesta = generar_respuesta(codigo)
print(f"Código: {codigo}")
print(f"Respuesta: {respuesta}")
```

### **Ejemplo de Uso:**

```text
Código de Desafío: X7Z9
Respuesta: 8A3F2B
```

---

## ⚠️ Seguridad Importante

### **Protección de la Semilla:**

- La semilla `BIOBOL_CLAVE_SECRETA_2025` debe ser **IDÉNTICA** en:
  - `services/security_service.py` (línea 10)
  - Tu generador externo
- **NUNCA** compartas la semilla públicamente
- Si cambias la semilla, debes actualizarla en ambos lugares
- El guardián usa `SECURITY_MASTER_SECRET` (env `PABLITO_MASTER_SECRET`) para cifrar `security_mobile.lock`. Configura un valor propio en producción.

### **Recomendaciones:**

1. Guarda tu generador en un lugar seguro (USB, nube privada)
2. Haz backup de la semilla en lugar seguro
3. No compartas el generador con terceros
4. Cambia la semilla periódicamente (cada 6 meses)

---

## 🧪 Pruebas del Sistema

### **Probar Autenticación Normal:**

1. Ejecuta la aplicación
2. Intenta acceder a función protegida
3. Ingresa PIN correcto
4. Verifica acceso concedido

### **Probar Recuperación:**

1. Haz clic en "¿Olvidé mi contraseña?"
2. Anota el código de desafío (ej: "X7Z9")
3. Usa tu generador para obtener respuesta
4. Ingresa la respuesta
5. Verifica que se resetee el PIN
6. Establece nuevo PIN

### **Probar Validaciones:**

- PIN incorrecto → Mensaje de error
- Respuesta incorrecta → Mensaje de error
- Nuevo PIN < 4 caracteres → Mensaje de error
- Confirmación no coincide → Mensaje de error

---

## 📝 Archivos del Sistema

```text
📁 VISUAL STUDIO BOLETAS POS/
├── 📄 app_boletas.py (Aplicación principal)
├── 📄 services/security_service.py (Módulo de seguridad)
├── 📄 services/storage_guard.py (Cifrado local y llaves de hardware)
├── 📄 app_boletas_v2_gestion_maestra.py (Backup V2)
├── 📄 app_boletas_backup_refactor.py (Backup V1)
└── 📄 BACKUPS_README.md (Documentación de backups)
```

---

## 🔄 Historial de Cambios

### **Versión 2.1 - Sistema de Seguridad** (2025-11-20)

- ✅ Módulo `services/security_service.py` creado
- ✅ Clase `SecurityService` implementada
- ✅ Sistema de recuperación con desafío matemático
- ✅ Ventana de cambio obligatorio de PIN
- ✅ Interfaz mejorada para autenticación
- ✅ Validaciones robustas

---

**Desarrollado por:** BiobolPOS Team  
**Última actualización:** 2025-11-20 22:30 hrs
