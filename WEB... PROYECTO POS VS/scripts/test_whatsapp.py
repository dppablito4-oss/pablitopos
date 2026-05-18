"""
Script de prueba para el envío automático por WhatsApp
Ejecuta este script para probar la funcionalidad sin usar la app completa
"""

import os
import sys

# Asegurar que el directorio raíz del proyecto esté en sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from services import CommunicationService

def test_whatsapp_send():
    """Prueba el envío de un PDF por WhatsApp"""
    
    print("=" * 60)
    print("  PRUEBA DE ENVÍO POR WHATSAPP")
    print("=" * 60)
    print()
    
    # Crear instancia del servicio
    comm = CommunicationService()
    
    # Pedir datos al usuario
    print("📱 Ingresa el número de celular (9 dígitos):")
    print("   Se agregará +51 automáticamente")
    print("   Ejemplo: 999888777")
    phone = input("   Número: ").strip()
    
    print()
    print("📄 Ingresa la ruta del PDF a enviar:")
    print("   Ejemplo: C:\\Users\\tu_usuario\\Desktop\\test.pdf")
    pdf_path = input("   Ruta: ").strip()
    
    # Validar que el archivo existe
    if not os.path.exists(pdf_path):
        print()
        print("❌ ERROR: El archivo no existe")
        print(f"   Ruta: {pdf_path}")
        return
    
    print()
    print("⏳ Preparando envío...")
    print("   IMPORTANTE: NO toques el teclado ni el mouse durante 10 segundos")
    print()
    input("   Presiona ENTER cuando estés listo...")
    
    # Enviar
    print()
    print("🚀 Enviando por WhatsApp...")
    success, message = comm.send_whatsapp_pdf(phone, pdf_path, wait_seconds=5)
    
    print()
    if success:
        print("✅ ÉXITO!")
        print(f"   {message}")
    else:
        print("❌ ERROR!")
        print(f"   {message}")
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_whatsapp_send()
    except KeyboardInterrupt:
        print("\n\n⚠️  Prueba cancelada por el usuario")
    except Exception as e:
        print(f"\n\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
