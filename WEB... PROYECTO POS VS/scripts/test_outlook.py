import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# ⚙️ TUS CREDENCIALES DE GMAIL
# ==========================================
# 1. Tu correo de Gmail
USUARIO = "pabloclsa87@gmail.com" 

# 2. Tu Contraseña de Aplicación de Google (16 letras)
# ¡NO PONGAS TU CONTRASEÑA NORMAL!
# Tienes que generarla en: Cuenta Google > Seguridad > Verificación en 2 pasos > Contraseñas de aplicaciones
PASSWORD = "exhb oqqh kpwu aewd" 
# ==========================================

DESTINATARIO = USUARIO  # Te lo envías a ti mismo para probar

def probar_gmail():
    print("📧 Conectando con GMAIL...")
    
    try:
        # Configuración de Gmail
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls() # Encriptar conexión
        
        # Login
        print("🔑 Iniciando sesión...")
        server.login(USUARIO, PASSWORD)
        print("✅ ¡LOGIN EXITOSO! Las credenciales funcionan.")
        
        # Crear mensaje
        msg = MIMEMultipart()
        msg['From'] = USUARIO
        msg['To'] = DESTINATARIO
        msg['Subject'] = "Prueba de Sistema POS - Gmail"
        msg.attach(MIMEText("¡Funciona! Ya puedes usar este correo en tu sistema de ventas.", 'plain'))
        
        # Enviar
        server.send_message(msg)
        server.quit()
        print(f"🚀 Correo enviado exitosamente a {DESTINATARIO}")
        
    except smtplib.SMTPAuthenticationError:
        print("\n❌ ERROR DE CONTRASEÑA:")
        print("Google rechazó el acceso. Asegúrate de estar usando una 'Contraseña de Aplicación' y no tu clave normal.")
    except Exception as e:
        print("\n❌ ERROR:")
        print(e)

if __name__ == "__main__":
    probar_gmail()