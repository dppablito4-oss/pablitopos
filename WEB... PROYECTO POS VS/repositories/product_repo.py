from db_connection import Database


class ProductRepository:
    def __init__(self, db: Database):
        self.db = db

    def search_products(self, text):
        conn = self.db.get_connection()
        cur = conn.cursor()
        like = f"%{text}%"
        cur.execute(
            """
            SELECT id, code, name, unit, price, stock, price_includes_igv
            FROM products
            WHERE active = 1 AND (name LIKE ? OR code LIKE ?)
            ORDER BY name
            """,
            (like, like),
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_product_by_id(self, product_id):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, code, name, unit, price, stock, price_includes_igv
            FROM products
            WHERE id = ?
            """,
            (product_id,),
        )
        row = cur.fetchone()
        conn.close()
        return row

    def _normalize_stock(self, value):
        if value is None:
            return None
        return int(round(float(value)))

    def create_product(self, code, name, unit, price, stock=None, price_includes_igv=0):
        conn = self.db.get_connection()
        cur = conn.cursor()

        normalized_code = code.strip() if code else None

        cur.execute(
            """
            INSERT INTO products (code, name, unit, price, active, stock, price_includes_igv)
            VALUES (?, ?, ?, ?, 1, ?, ?)
            """,
            (normalized_code, name, unit, price, self._normalize_stock(stock), price_includes_igv),
        )

        product_id = cur.lastrowid

        # Si no se proporcionó código, generar uno basado en el ID (ej. P0001)
        if not normalized_code:
            generated_code = f"P{product_id:04d}"
            cur.execute(
                "UPDATE products SET code = ? WHERE id = ?",
                (generated_code, product_id),
            )

        conn.commit()
        conn.close()
        return product_id

    def update_product_price(self, product_id, price, price_includes_igv=None):
        conn = self.db.get_connection()
        cur = conn.cursor()
        if price_includes_igv is not None:
            cur.execute(
                """
                UPDATE products
                SET price = ?, price_includes_igv = ?
                WHERE id = ?
                """,
                (price, price_includes_igv, product_id),
            )
        else:
            cur.execute(
                """
                UPDATE products
                SET price = ?
                WHERE id = ?
                """,
                (price, product_id),
            )
        conn.commit()
        conn.close()

    def update_stock(self, product_id, new_stock):
        """Actualiza el stock de un producto."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE products
            SET stock = ?
            WHERE id = ?
            """,
            (self._normalize_stock(new_stock), product_id),
        )
        conn.commit()
        conn.close()

    def reduce_stock(self, product_id, quantity):
        """Reduce el stock de un producto (si tiene control de stock)."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT stock FROM products WHERE id = ?", (product_id,))
        row = cur.fetchone()
        if row and row[0] is not None:
            new_stock = row[0] - quantity
            if new_stock < 0:
                new_stock = 0
            cur.execute(
                "UPDATE products SET stock = ? WHERE id = ?",
                (self._normalize_stock(new_stock), product_id),
            )
            conn.commit()
        conn.close()

    def update_product(self, product_id, code, name, unit, price, stock=None):
        """Actualiza todos los datos de un producto."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE products
            SET code = ?, name = ?, unit = ?, price = ?
            WHERE id = ?
            """,
            (code, name, unit, price, product_id),
        )
        if stock is not None:
            cur.execute(
                "UPDATE products SET stock = ? WHERE id = ?",
                (self._normalize_stock(stock), product_id),
            )
        conn.commit()
        conn.close()

    def delete_product(self, product_id):
        """Eliminado lógico del producto (active = 0)."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE products SET active = 0 WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()
