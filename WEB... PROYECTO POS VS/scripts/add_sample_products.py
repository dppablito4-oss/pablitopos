import sqlite3

import settings

conn = sqlite3.connect(settings.get_db_path())
cur = conn.cursor()

# Productos de ejemplo
productos = [
    ("PROD001", "PRODUTO GENERICO", "UNIDAD", 2.00),
]

for code, name, unit, price in productos:
    # Verificar si ya existe
    cur.execute("SELECT id FROM products WHERE code = ?", (code,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO products (code, name, unit, price, active)
            VALUES (?, ?, ?, ?, 1)
        """, (code, name, unit, price))
        print(f"✅ Agregado: {name}")
    else:
        print(f"⚠️  Ya existe: {name}")

conn.commit()

# Verificar
cur.execute("SELECT COUNT(*) FROM products WHERE active = 1")
count = cur.fetchone()[0]
print(f"\n📦 Total productos activos: {count}")

conn.close()
print("\n✅ Productos de ejemplo agregados!")
