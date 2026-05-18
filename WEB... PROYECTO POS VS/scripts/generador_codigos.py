#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔐 GENERADOR DE CÓDIGOS DE RECUPERACIÓN - PABLITO POS
====================================================

Este script genera las respuestas para el sistema de recuperación
de acceso de PABLITO_POS.

IMPORTANTE: Guarda este archivo en un lugar seguro (USB, nube privada).
"""

import hashlib

# 🔑 SEMILLA SECRETA - DEBE SER IDÉNTICA A LA DE security_manager.py
SEMILLA = "BIOBOL_CLAVE_SECRETA_2025"

def generar_respuesta(codigo_desafio):
    """
    Genera la respuesta para un código de desafío.
    
    Args:
        codigo_desafio (str): El código de 4 caracteres mostrado en la app
        
    Returns:
        str: Respuesta de 6 caracteres en mayúsculas
    """
    # Concatenar desafío + semilla
    texto = f"{codigo_desafio}{SEMILLA}"
    
    # Calcular hash SHA256
    hash_obj = hashlib.sha256(texto.encode())
    
    # Tomar primeros 6 caracteres en mayúsculas
    respuesta = hash_obj.hexdigest().upper()[:6]
    
    return respuesta


def main():
    """Función principal - Modo interactivo."""
    print("=" * 60)
    print("🔐 GENERADOR DE CÓDIGOS DE RECUPERACIÓN - PABLITO_POS")
    print("=" * 60)
    print()
    print("Instrucciones:")
    print("1. La aplicación te mostrará un código de 4 caracteres")
    print("2. Ingresa ese código aquí")
    print("3. Este generador te dará una respuesta de 6 caracteres")
    print("4. Ingresa esa respuesta en la aplicación")
    print()
    print("Presiona Ctrl+C para salir")
    print("-" * 60)
    print()
    
    while True:
        try:
            # Solicitar código de desafío
            codigo = input("Ingresa el CÓDIGO DE DESAFÍO (4 caracteres): ").strip().upper()
            
            # Validar entrada
            if not codigo:
                print("⚠️  Error: Debes ingresar un código.\n")
                continue
            
            if len(codigo) != 4:
                print(f"⚠️  Error: El código debe tener 4 caracteres (ingresaste {len(codigo)}).\n")
                continue
            
            # Generar respuesta
            respuesta = generar_respuesta(codigo)
            
            # Mostrar resultado
            print()
            print("=" * 60)
            print(f"✅ RESPUESTA GENERADA:")
            print()
            print(f"   Código de Desafío: {codigo}")
            print(f"   Respuesta:         {respuesta}")
            print()
            print("=" * 60)
            print()
            print("Ingresa esta respuesta en la aplicación PABLITO_POS.")
            print()
            print("-" * 60)
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error inesperado: {e}\n")


if __name__ == "__main__":
    main()
