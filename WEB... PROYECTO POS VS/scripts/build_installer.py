"""
Script para crear el instalador con PyInstaller
Ejecutar: python build_installer.py
"""

import os
import sys
import tempfile
import zipfile
from pathlib import Path

import PyInstaller.__main__

def build_installer():
    """Construye el ejecutable con PyInstaller"""
    
    print("="*70)
    print("PablitoPOS - Constructor de Instalador")
    print("="*70)
    
    # Verificar dependencias críticas
    try:
        import PyInstaller
        print(f"PyInstaller encontrado: {PyInstaller.__version__}")
    except ImportError:
        print("PyInstaller no está instalado")
        print("Instalar con: pip install pyinstaller")
        return False

    try:
        import pyzipper  # type: ignore
        print("pyzipper disponible para ZIP cifrados")
    except ImportError:
        print("Falta la librería 'pyzipper' (requerida para backups portables)")
        print("Instalar con: pip install pyzipper")
        return False
    
    # Rutas
    scripts_dir = Path(__file__).resolve().parent
    project_dir = scripts_dir.parent
    app_file = project_dir / "app_boletas.py"
    workspace_dist = project_dir / "dist"
    dist_dir = Path(tempfile.mkdtemp(prefix="pablito_dist_"))
    build_dir = Path(tempfile.mkdtemp(prefix="pablito_build_"))
    spec_file = project_dir / "app_boletas.spec"
    
    # Verificar que app_boletas.py existe
    if not app_file.exists():
        print(f"❌ No se encontró: {app_file}")
        return False
    
    print(f"Archivo principal: {app_file.name}")
    
    # Comando PyInstaller
    # Usar rutas relativas y mover el cwd para evitar problemas con espacios en rutas.
    os.chdir(project_dir)

    exe_name = "Pablito_POS"

    cmd = [
        "--onefile",
        "--windowed",
        f"--name={exe_name}",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--specpath={project_dir}",
        "--icon=logo.ico",
        "--add-data=logo.png;.",
        "--add-data=logo.ico;.",
        "--clean",
        "--log-level=INFO",
        "--hidden-import=ttkbootstrap",
        "--hidden-import=ttkbootstrap.constants",
        "--hidden-import=reportlab",
        "--hidden-import=reportlab.pdfgen",
        "--hidden-import=reportlab.lib",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=app_ui.security",
        "--hidden-import=app_ui.profiles",
        "--hidden-import=app_ui.messages",
        "--hidden-import=app_ui.effects",
        "--hidden-import=app_ui.hotkeys",
        "--hidden-import=app_ui.backups",
        "--hidden-import=app_core.email_templates",
        "--hidden-import=app_core.logging_setup",
        "--hidden-import=app_core.ui_helpers",
        "--collect-all=app_ui",
        "--collect-all=app_core",
        "--hidden-import=pyzipper",
        "--noupx",
        "app_boletas.py",
    ]
    
    print("\n" + "="*70)
    print("Comando PyInstaller:")
    print("="*70)
    print(" ".join(cmd))
    print("\nEsto puede tomar 1-2 minutos...\n")
    
    # Ejecutar PyInstaller (uso de API para evitar problemas de PATH)
    try:
        PyInstaller.__main__.run(cmd)

        exe_file = dist_dir / f"{exe_name}.exe"
        if exe_file.exists():
            size_mb = exe_file.stat().st_size / (1024*1024)
            print("[OK] Compilación exitosa")
            print(f"\n[OK] Ejecutable creado:")
            print(f"   Ubicación temporal: {exe_file}")
            print(f"   Tamaño: {size_mb:.1f} MB")

            # Empaquetar el exe en ZIP dentro de la carpeta dist del proyecto (OneDrive)
            workspace_dist.mkdir(exist_ok=True)
            zip_path = workspace_dist / f"{exe_name}.zip"
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(exe_file, arcname=f"{exe_name}.exe")
            print(f"   ZIP guardado en: {zip_path}")

            print("\n" + "="*70)
            print("Próximos pasos:")
            print("="*70)
            print("1. Copiar BiobolPOS.exe a: dist/BiobolPOS.exe")
            print("2. Crear instalador con:")
            print("   - NSIS (gratuito)")
            print("   - Inno Setup (gratuito)")
            print("   - Advanced Installer")
            print("3. El programa crea automáticamente carpeta en:")
            print("   %APPDATA%\\PablitoPOS\\")
            print("\nNota: No necesita distribuir boletas.sqlite3 ni db.key")
            print("      Ambos se generan en la primera ejecución y se cifran automáticamente")
            print("="*70)

            return True

        print(f"[WARN] No se encontró: {exe_file}")
        return False

    except Exception as e:
        print("[ERROR] Error en la compilación:")
        print(e)
        return False

def cleanup():
    """Limpia archivos temporales (opcional)"""
    project_dir = Path(__file__).resolve().parent.parent
    
    to_remove = [
        project_dir / "build",
        project_dir / "app_boletas.spec",
    ]
    
    for path in to_remove:
        if path.exists():
            if path.is_dir():
                import shutil
                shutil.rmtree(path)
                print(f"[CLEAN] Limpiado: {path}")

if __name__ == "__main__":
    success = build_installer()
    
    if success:
        # Preguntar si limpiar archivos temporales
        user_input = input("\n¿Limpiar archivos temporales (build, .spec)? (s/n): ").lower()
        if user_input == 's':
            cleanup()
        
        print("\n[OK] Proceso completado")
        sys.exit(0)
    else:
        print("\n[ERROR] El proceso falló. Revisar errores arriba.")
        sys.exit(1)
