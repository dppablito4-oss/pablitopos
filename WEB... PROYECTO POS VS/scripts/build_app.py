import PyInstaller.__main__
import os
import shutil

def build():
    # Definir nombre del ejecutable
    app_name = "SistemaBoletasPOS"
    main_script = "app_boletas.py"
    icon_path = "logo.ico"
    
    # Asegurarse de que estamos en el directorio correcto
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_dir)
    
    print(f"Iniciando compilación de {app_name}...")
    
    # Argumentos para PyInstaller
    args = [
        main_script,
        f'--name={app_name}',
        '--noconsole',  # No mostrar consola negra
        '--onefile',    # Crear un único archivo ejecutable
        '--clean',      # Limpiar caché antes de construir
        f'--icon={icon_path}',
        
        # Incluir carpetas de código fuente (si no se detectan automáticamente)
        # PyInstaller suele detectar imports, pero los datos estáticos no.
        
        # Incluir Assets e Imágenes
        '--add-data=logo.png;.',
        '--add-data=logo.ico;.',
        
        # Incluir paquetes que a veces dan problemas
        '--collect-all=ttkbootstrap',
        '--collect-all=reportlab',
        '--collect-all=PIL',
        '--hidden-import=app_ui.security',
        '--hidden-import=app_ui.profiles',
        '--hidden-import=app_ui.messages',
        '--hidden-import=app_ui.effects',
        '--hidden-import=app_ui.hotkeys',
        '--hidden-import=app_ui.backups',
        '--hidden-import=app_core.email_templates',
        '--hidden-import=app_core.logging_setup',
        '--hidden-import=app_core.ui_helpers',
        '--collect-all=app_ui',
        '--collect-all=app_core',
        
        # Opciones de optimización
        '--log-level=INFO',
    ]
    
    # Ejecutar PyInstaller
    PyInstaller.__main__.run(args)
    
    print("\n" + "="*50)
    print(f"[OK] Compilación finalizada. El ejecutable está en la carpeta 'dist/{app_name}'.")
    print("="*50)

if __name__ == "__main__":
    # Verificar si PyInstaller está instalado
    try:
        import PyInstaller
        build()
    except ImportError:
        print("Error: PyInstaller no está instalado.")
        print("Ejecuta: pip install pyinstaller")
