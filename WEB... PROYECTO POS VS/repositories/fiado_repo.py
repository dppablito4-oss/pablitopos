import sqlite3
from datetime import datetime
from typing import Any

from db_connection import Database


class FiadoRepository:
    def __init__(self, db: Database):
        self.db = db

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate_code(self, prefix: str = "C") -> str:
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT code FROM fiados WHERE code LIKE ? ORDER BY id DESC LIMIT 1", (f"{prefix}-%",))
            row = cur.fetchone()
            if row and row[0]:
                code = row[0]
                try:
                    num_part = int(code.split("-")[-1])
                    next_num = num_part + 1
                except Exception:
                    cur.execute("SELECT MAX(id) FROM fiados")
                    next_num = (cur.fetchone()[0] or 0) + 1
            else:
                cur.execute("SELECT MAX(id) FROM fiados")
                next_num = (cur.fetchone()[0] or 0) + 1
            return f"{prefix}-{next_num:03d}"
        finally:
            conn.close()

    def create_fiado(
        self,
        client_id: int,
        items: list[dict[str, Any]],
        *,
        code: str,
        total_bruto: float,
        total_pagado: float,
        total_pendiente: float,
        status: str = "pendiente",
        pdf_path: str | None = None,
        sale_id: int | None = None,
    ) -> int:
        conn = self.db.get_connection()
        cur = conn.cursor()
        now = self._now()
        try:
            cur.execute("PRAGMA table_info(fiado_items)")
            item_cols = [r[1] for r in cur.fetchall()]

            cur.execute(
                """
                INSERT INTO fiados (code, client_id, status, total_bruto, total_pagado, total_pendiente, pdf_path, sale_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (code, client_id, status, total_bruto, total_pagado, total_pendiente, pdf_path, sale_id, now, now),
            )
            fiado_id = cur.lastrowid

            base_cols = [
                "fiado_id",
                "product_id" if "product_id" in item_cols else None,
                "description",
                "quantity",
                "unit",
                "unit_price",
                "subtotal",
                "block",
                "status",
                "created_at",
            ]
            insert_cols = [c for c in base_cols if c]
            placeholders = ",".join(["?" for _ in insert_cols])
            insert_sql = f"INSERT INTO fiado_items ({', '.join(insert_cols)}) VALUES ({placeholders})"

            for item in items:
                vals = [fiado_id]
                if "product_id" in item_cols:
                    vals.append(item.get("product_id"))
                vals.extend(
                    [
                        item.get("description", ""),
                        float(item.get("quantity", 0) or 0),
                        item.get("unit", ""),
                        float(item.get("unit_price", 0) or 0),
                        float(item.get("subtotal", 0) or 0),
                        item.get("block", ""),
                        item.get("status", "pendiente"),
                        now,
                    ]
                )
                cur.execute(insert_sql, tuple(vals))

            conn.commit()
            return fiado_id
        except sqlite3.Error:
            conn.rollback()
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_fiado(self, fiado_id: int):
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT id, code, client_id, status, total_bruto, total_pagado, total_pendiente, pdf_path, sale_id, created_at, updated_at FROM fiados WHERE id = ?",
                (fiado_id,),
            )
            fiado = cur.fetchone()
            cur.execute("PRAGMA table_info(fiado_items)")
            item_cols = [r[1] for r in cur.fetchall()]
            select_item_cols = [
                c
                for c in [
                    "id",
                    "fiado_id",
                    "product_id",
                    "description",
                    "quantity",
                    "unit",
                    "unit_price",
                    "subtotal",
                    "block",
                    "status",
                    "created_at",
                ]
                if c in item_cols
            ]
            item_sql = f"SELECT {', '.join(select_item_cols)} FROM fiado_items WHERE fiado_id = ? ORDER BY id"
            cur.execute(item_sql, (fiado_id,))
            items = cur.fetchall()
            return fiado, items
        finally:
            conn.close()

    def list_by_client(self, client_id: int):
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT id, code, client_id, status, total_bruto, total_pagado, total_pendiente, pdf_path, sale_id, created_at, updated_at FROM fiados WHERE client_id = ? ORDER BY created_at DESC",
                (client_id,),
            )
            return cur.fetchall()
        finally:
            conn.close()

    def search_fiados(self, text: str):
        conn = self.db.get_connection()
        cur = conn.cursor()
        like = f"%{text or ''}%"
        try:
            cur.execute(
                """
                SELECT f.id, f.code, f.status, f.total_bruto, f.total_pagado, f.total_pendiente,
                       f.created_at, f.updated_at, c.full_name, c.dni, f.sale_id
                FROM fiados f
                LEFT JOIN clients c ON f.client_id = c.id
                WHERE c.full_name LIKE ? OR c.dni LIKE ? OR f.code LIKE ?
                ORDER BY f.created_at DESC
                """,
                (like, like, like),
            )
            return cur.fetchall()
        finally:
            conn.close()

    def _get_fiado_id_for_item(self, item_id: int) -> int | None:
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT fiado_id FROM fiado_items WHERE id = ?", (item_id,))
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def set_item_status(self, item_id: int, status: str) -> int | None:
        fiado_id = self._get_fiado_id_for_item(item_id)
        if fiado_id is None:
            return None
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE fiado_items SET status = ? WHERE id = ?", (status, item_id))
            conn.commit()
            return fiado_id
        finally:
            conn.close()

    def recalc_totals(self, fiado_id: int) -> None:
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT subtotal, status FROM fiado_items WHERE fiado_id = ?", (fiado_id,))
            rows = cur.fetchall()
            total_bruto = sum(r[0] or 0 for r in rows)
            total_pagado = sum(r[0] or 0 for r in rows if (r[1] or "").lower() == "pagado")
            total_pendiente = max(0.0, round(total_bruto - total_pagado, 2))
            status = "pagado" if total_pendiente <= 0 else "pendiente"
            now = self._now()
            cur.execute(
                """
                UPDATE fiados
                SET total_bruto = ?, total_pagado = ?, total_pendiente = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (total_bruto, total_pagado, total_pendiente, status, now, fiado_id),
            )
            conn.commit()
        finally:
            conn.close()

    def set_pdf_path(self, fiado_id: int, pdf_path: str) -> None:
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE fiados SET pdf_path = ?, updated_at = ? WHERE id = ?", (pdf_path, self._now(), fiado_id))
            conn.commit()
        finally:
            conn.close()

    def set_sale_id(self, fiado_id: int, sale_id: int) -> None:
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE fiados SET sale_id = ?, updated_at = ? WHERE id = ?", (sale_id, self._now(), fiado_id))
            conn.commit()
        finally:
            conn.close()

    def set_status(self, fiado_id: int, status: str) -> None:
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE fiados SET status = ?, updated_at = ? WHERE id = ?", (status, self._now(), fiado_id))
            conn.commit()
        finally:
            conn.close()
