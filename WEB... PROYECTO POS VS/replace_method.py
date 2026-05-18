# Script para reemplazar build_update_info_ui
with open(r'e:\OneDrive\VISUAL STUDIO BOLETAS POS\app_boletas.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open(r'e:\OneDrive\VISUAL STUDIO BOLETAS POS\ui\ui_update_info.py', 'r', encoding='utf-8') as f:
    new_methods = f.read()

# Encontrar las líneas de inicio y fin del método antiguo
# build_update_info_ui empieza en línea 3113 y termina en línea 3362
start_line = 3110  # Línea antes del comentario "# ---------------- ACTUALIZAR INFORMACIÓN"
end_line = 3362    # Línea antes de "def open_verify_window"

# Construir el nuevo archivo
new_content = lines[:start_line] + ['\n' + new_methods + '\n'] + lines[end_line:]

# Escribir el archivo
with open(r'e:\OneDrive\VISUAL STUDIO BOLETAS POS\app_boletas.py', 'w', encoding='utf-8') as f:
    f.writelines(new_content)

print("Reemplazo completado exitosamente!")
