import sqlite3

import settings

conn = sqlite3.connect(settings.get_db_path())
cur = conn.cursor()

# Contar productos activos
cur.execute("SELECT COUNT(*) FROM products WHERE active = 1")
count = cur.fetchone()[0]
print(f"Productos activos: {count}")

# Listar productos
cur.execute("SELECT id, code, name, unit, price FROM products WHERE active = 1 LIMIT 10")
products = cur.fetchall()
print("\nProductos:")
for p in products:
    print(f"  ID: {p[0]}, Código: {p[1]}, Nombre: {p[2]}, Unidad: {p[3]}, Precio: {p[4]}")

conn.close()
