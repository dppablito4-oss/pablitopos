import sqlite3

import settings


def init_db():
    """Crea las tablas necesarias si no existen."""
    conn = sqlite3.connect(settings.get_db_path())
    cur = conn.cursor()

    # Perfil de empresa (ahora múltiples perfiles)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS company_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            ruc TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            website TEXT,
            footer_message TEXT,
            logo_path TEXT,
            brand_color TEXT DEFAULT '#1f77b4',
            is_active INTEGER DEFAULT 1,
            yape_qr_path TEXT
        );
    """)
    
    # Agregar columnas faltantes si existen (migración)
    try:
        cur.execute("ALTER TABLE company_profile ADD COLUMN brand_color TEXT DEFAULT '#1f77b4'")
    except sqlite3.OperationalError:
        pass  # Columna ya existe
    
    try:
        cur.execute("ALTER TABLE company_profile ADD COLUMN is_active INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass  # Columna ya existe

    try:
        cur.execute("ALTER TABLE company_profile ADD COLUMN yape_qr_path TEXT")
    except sqlite3.OperationalError:
        pass  # Columna ya existe

    # Clientes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dni TEXT,
            full_name TEXT,
            phone TEXT,
            email TEXT,
            address TEXT
        );
    """)
    # Asegurar migración: si existe columna 'name' (BD vieja), copiar a 'full_name'
    try:
        cur.execute("PRAGMA table_info(clients)")
        cols = [r[1] for r in cur.fetchall()]
        if 'name' in cols and 'full_name' not in cols:
            try:
                cur.execute("ALTER TABLE clients ADD COLUMN full_name TEXT")
            except sqlite3.OperationalError:
                pass
            cur.execute("UPDATE clients SET full_name = name WHERE full_name IS NULL OR TRIM(full_name) = ''")
        elif 'name' in cols and 'full_name' in cols:
            cur.execute("UPDATE clients SET full_name = name WHERE (full_name IS NULL OR TRIM(full_name) = '') AND (name IS NOT NULL AND TRIM(name) <> '')")
    except Exception:
        pass

    # Productos
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            name TEXT,
            unit TEXT,
            price REAL,
            active INTEGER DEFAULT 1,
            stock INTEGER DEFAULT 0,
            price_includes_igv INTEGER DEFAULT 0
        );
    """)

    # Migración: asegurar columna stock como INTEGER
    try:
        cur.execute("PRAGMA table_info(products)")
        products_cols = cur.fetchall()
        stock_col = next((col for col in products_cols if col[1] == "stock"), None)
        if not stock_col:
            cur.execute("ALTER TABLE products ADD COLUMN stock INTEGER DEFAULT 0")
        elif (stock_col[2] or "").upper() != "INTEGER":
            # Reconstruir tabla para ajustar el tipo de la columna stock
            cur.execute("ALTER TABLE products RENAME TO products_temp")
            cur.execute("""
                CREATE TABLE products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT,
                    name TEXT,
                    unit TEXT,
                    price REAL,
                    active INTEGER DEFAULT 1,
                    stock INTEGER DEFAULT 0,
                    price_includes_igv INTEGER DEFAULT 0
                );
            """)
            cur.execute("""
                INSERT INTO products (id, code, name, unit, price, active, stock, price_includes_igv)
                SELECT id, code, name, unit, price, active,
                       CAST(COALESCE(stock, 0) AS INTEGER),
                       COALESCE(price_includes_igv, 0)
                FROM products_temp
            """)
            cur.execute("DROP TABLE products_temp")
    except sqlite3.OperationalError:
        pass
    
    # Migración: agregar columna price_includes_igv
    try:
        cur.execute("ALTER TABLE products ADD COLUMN price_includes_igv INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Ventas (boletas)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series TEXT,
            number INTEGER,
            datetime TEXT,
            client_id INTEGER,
            company_id INTEGER DEFAULT 1,
            subtotal REAL,
            igv REAL,
            total REAL,
            pdf_path TEXT,
            serial_seguridad TEXT,
            discount REAL DEFAULT 0,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(company_id) REFERENCES company_profile(id)
        );
    """)
    # Migración: agregar columna pdf_path si no existe
    try:
        cur.execute("ALTER TABLE sales ADD COLUMN pdf_path TEXT")
    except sqlite3.OperationalError:
        pass  # Columna ya existe

    # Migración: agregar columna serial_seguridad (código QR) si no existe
    try:
        cur.execute("ALTER TABLE sales ADD COLUMN serial_seguridad TEXT UNIQUE;")
    except sqlite3.OperationalError:
        pass

    # Migración: agregar columna discount si no existe
    try:
        cur.execute("ALTER TABLE sales ADD COLUMN discount REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Migración: soportar flags para proforma y boletín
    try:
        cur.execute("ALTER TABLE sales ADD COLUMN is_proforma INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE sales ADD COLUMN is_boletin INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE sales ADD COLUMN is_adelanto INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE sales ADD COLUMN advance_amount REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE sales ADD COLUMN estimated_total REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Detalle de venta
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            product_id INTEGER,
            description TEXT,
            unit TEXT,
            quantity REAL,
            unit_price REAL,
            subtotal REAL,
            FOREIGN KEY(sale_id) REFERENCES sales(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
    """)

    # Fiados (vale pendiente)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS fiados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            client_id INTEGER,
            status TEXT DEFAULT 'pendiente',
            total_bruto REAL DEFAULT 0,
            total_pagado REAL DEFAULT 0,
            total_pendiente REAL DEFAULT 0,
            pdf_path TEXT,
            sale_id INTEGER,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(sale_id) REFERENCES sales(id)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS fiado_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fiado_id INTEGER,
            product_id INTEGER,
            description TEXT,
            quantity REAL,
            unit TEXT,
            unit_price REAL,
            subtotal REAL,
            block TEXT,
            status TEXT DEFAULT 'pendiente',
            created_at TEXT,
            FOREIGN KEY(fiado_id) REFERENCES fiados(id)
        );
        """
    )

    # Migración: agregar columna product_id a fiado_items si no existe
    try:
        cur.execute("PRAGMA table_info(fiado_items)")
        fi_cols = [r[1] for r in cur.fetchall()]
        if "product_id" not in fi_cols:
            cur.execute("ALTER TABLE fiado_items ADD COLUMN product_id INTEGER")
    except sqlite3.OperationalError:
        pass

    cur.execute("CREATE INDEX IF NOT EXISTS idx_fiados_client_status ON fiados(client_id, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fiado_items_fiado ON fiado_items(fiado_id)")

    # Auditoría de eventos sensibles
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            user_pc TEXT
        );
    """)

    # Configuración / Seguridad
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    # Insertar PIN por defecto si no existe
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_pin', '1234')")
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('customer_screen_index', '0')")
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('onboarding_completed', '0')")

    # Migración: include_igv en company_profile
    try:
        cur.execute("ALTER TABLE company_profile ADD COLUMN include_igv INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass

    # Migración: discount y discount_type en sale_items
    try:
        cur.execute("ALTER TABLE sale_items ADD COLUMN discount REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE sale_items ADD COLUMN discount_type TEXT DEFAULT 'fixed'")
    except sqlite3.OperationalError:
        pass

    # Migración: serial_seguridad en sales (para QR de verificación)
    try:
        cur.execute("ALTER TABLE sales ADD COLUMN serial_seguridad TEXT")
    except sqlite3.OperationalError:
        pass

    # Migración: created_at en clients (para reporte de clientes)
    try:
        cur.execute("ALTER TABLE clients ADD COLUMN created_at TEXT")
        # Backfill para clientes existentes
        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("UPDATE clients SET created_at = ? WHERE created_at IS NULL", (now_str,))
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
