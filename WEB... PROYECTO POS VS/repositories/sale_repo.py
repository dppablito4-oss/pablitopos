import sqlite3
from datetime import datetime, timedelta

from db_connection import Database


class SaleRepository:
    def __init__(self, db: Database):
        self.db = db
        self._sale_select_columns = None
        self._sale_item_columns = None
        self._sales_all_cols = None

    def get_next_number(self, series):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT MAX(number) FROM sales WHERE series = ?", (series,))
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            return row[0] + 1
        return 1

    def create_sale(
        self,
        series,
        number,
        dt,
        client_id,
        subtotal,
        igv,
        total,
        items,
        pdf_path=None,
        serial_seguridad=None,
        discount=0.0,
        is_proforma: bool = False,
        is_boletin: bool = False,
        is_adelanto: bool = False,
        advance_amount: float = 0.0,
        estimated_total: float | None = None,
    ):
        print(f"DEBUG: Intentando guardar venta... {series}-{number}")
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(sales)")
            sales_cols = [r[1] for r in cur.fetchall()]
            self._sales_all_cols = sales_cols

            insert_cols = [
                "series",
                "number",
                "datetime",
                "client_id",
                "subtotal",
                "igv",
                "total",
                "pdf_path",
            ]
            insert_vals = [series, number, dt, client_id, subtotal, igv, total, pdf_path]

            if "serial_seguridad" in sales_cols:
                insert_cols.append("serial_seguridad")
                insert_vals.append(serial_seguridad)
            if "discount" in sales_cols:
                insert_cols.append("discount")
                insert_vals.append(discount)
            if "is_proforma" in sales_cols:
                insert_cols.append("is_proforma")
                insert_vals.append(1 if is_proforma else 0)
            if "is_boletin" in sales_cols:
                insert_cols.append("is_boletin")
                insert_vals.append(1 if is_boletin else 0)
            if "is_adelanto" in sales_cols:
                insert_cols.append("is_adelanto")
                insert_vals.append(1 if is_adelanto else 0)
            if "advance_amount" in sales_cols:
                insert_cols.append("advance_amount")
                insert_vals.append(float(advance_amount or 0))
            if "estimated_total" in sales_cols:
                insert_cols.append("estimated_total")
                insert_vals.append(float(estimated_total or 0))

            placeholders = ",".join(["?" for _ in insert_cols])
            sql = f"INSERT INTO sales ({', '.join(insert_cols)}) VALUES ({placeholders})"
            cur.execute(sql, tuple(insert_vals))
            sale_id = cur.lastrowid

            cur.execute("PRAGMA table_info(sale_items)")
            item_cols = [r[1] for r in cur.fetchall()]
            base_item_cols = [
                "sale_id",
                "product_id",
                "description",
                "unit",
                "quantity",
                "unit_price",
                "subtotal",
            ]
            if "discount" in item_cols:
                base_item_cols.append("discount")
            if "discount_type" in item_cols:
                base_item_cols.append("discount_type")

            item_placeholders = ",".join(["?" for _ in base_item_cols])
            item_sql = f"INSERT INTO sale_items ({', '.join(base_item_cols)}) VALUES ({item_placeholders})"

            for it in items:
                vals = [
                    sale_id,
                    it.get("product_id"),
                    it.get("description", ""),
                    it.get("unit", ""),
                    it.get("quantity", 0),
                    it.get("unit_price", 0.0),
                    it.get("subtotal", 0.0),
                ]
                if "discount" in item_cols:
                    vals.append(it.get("discount", 0.0))
                if "discount_type" in item_cols:
                    vals.append(it.get("discount_type", "fixed"))
                cur.execute(item_sql, tuple(vals))

            conn.commit()
            print(f"DEBUG: Venta guardada con ID {sale_id}")
            return sale_id
        except sqlite3.Error as e:
            print(f"ERROR SQL CRÍTICO: {e}")
            conn.rollback()
            raise
        except Exception as e:
            print(f"ERROR DESCONOCIDO AL GUARDAR: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_sale_select_columns(self):
        if self._sale_select_columns is None:
            if self._sales_all_cols is None:
                conn = self.db.get_connection()
                cur = conn.cursor()
                try:
                    cur.execute("PRAGMA table_info(sales)")
                    self._sales_all_cols = [r[1] for r in cur.fetchall()]
                finally:
                    conn.close()
            sales_cols = self._sales_all_cols or []

            select_cols = [
                c
                for c in [
                    "id",
                    "series",
                    "number",
                    "datetime",
                    "client_id",
                    "company_id",
                    "subtotal",
                    "igv",
                    "total",
                    "pdf_path",
                ]
                if c in sales_cols
            ]
            if "serial_seguridad" in sales_cols:
                select_cols.append("serial_seguridad")
            if "discount" in sales_cols:
                select_cols.append("discount")
            if "is_proforma" in sales_cols:
                select_cols.append("is_proforma")
            if "is_boletin" in sales_cols:
                select_cols.append("is_boletin")
            if "is_adelanto" in sales_cols:
                select_cols.append("is_adelanto")
            if "advance_amount" in sales_cols:
                select_cols.append("advance_amount")
            if "estimated_total" in sales_cols:
                select_cols.append("estimated_total")
            self._sale_select_columns = select_cols
        return self._sale_select_columns

    def get_sale_item_columns(self):
        if self._sale_item_columns is None:
            conn = self.db.get_connection()
            cur = conn.cursor()
            try:
                cur.execute("PRAGMA table_info(sale_items)")
                item_cols = [r[1] for r in cur.fetchall()]
            finally:
                conn.close()

            sel_item_cols = [
                c
                for c in [
                    "id",
                    "product_id",
                    "description",
                    "unit",
                    "quantity",
                    "unit_price",
                    "subtotal",
                ]
                if c in item_cols
            ]
            if "discount" in item_cols:
                sel_item_cols.append("discount")
            if "discount_type" in item_cols:
                sel_item_cols.append("discount_type")
            self._sale_item_columns = sel_item_cols
        return self._sale_item_columns

    def map_sale_row(self, sale_row):
        if not sale_row:
            return {}
        cols = self.get_sale_select_columns()
        data = {}
        for idx, col in enumerate(cols):
            if idx < len(sale_row):
                data[col] = sale_row[idx]
        return data

    def get_sale(self, sale_id):
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            select_cols = self.get_sale_select_columns()
            sql = f"SELECT {', '.join(select_cols)} FROM sales WHERE id = ?"
            cur.execute(sql, (sale_id,))
            sale = cur.fetchone()
            if not sale:
                return None, []

            sel_item_cols = self.get_sale_item_columns()
            item_sql = f"SELECT {', '.join(sel_item_cols)} FROM sale_items WHERE sale_id = ?"
            cur.execute(item_sql, (sale_id,))
            items = cur.fetchall()
            return sale, items
        finally:
            conn.close()

    def get_pdf_path(self, sale_id):
        cols = self.get_sale_select_columns()
        if "pdf_path" not in cols:
            return None
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT pdf_path FROM sales WHERE id = ?", (sale_id,))
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def update_pdf_path(self, sale_id, pdf_path):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE sales SET pdf_path = ? WHERE id = ?", (pdf_path, sale_id))
        conn.commit()
        conn.close()

    def search_sales_by_client(self, text, *, proformas_only: bool = False, boletines_only: bool = False, sales_only: bool = False, adelantos_only: bool = False):
        conn = self.db.get_connection()
        cur = conn.cursor()
        like = f"%{text}%"
        filters = ["(c.full_name LIKE ? OR c.dni LIKE ?)"]
        params = [like, like]

        # Detectar si existe columna is_proforma
        has_flag = False
        try:
            cur.execute("PRAGMA table_info(sales)")
            cols = [r[1] for r in cur.fetchall()]
            has_flag = "is_proforma" in cols
        except Exception:
            cols = []

        if proformas_only:
            if has_flag:
                filters.append("COALESCE(s.is_proforma,0)=1")
            else:
                filters.append("UPPER(COALESCE(s.series,'')) LIKE 'PF%'")
        elif boletines_only:
            if has_flag:
                filters.append("COALESCE(s.is_boletin,0)=1")
            else:
                filters.append("UPPER(COALESCE(s.series,'')) LIKE 'BL%'")
        elif sales_only:
            if has_flag:
                filters.append("COALESCE(s.is_proforma,0)=0")
                filters.append("COALESCE(s.is_boletin,0)=0")
            else:
                filters.append("UPPER(COALESCE(s.series,'')) NOT LIKE 'PF%'")
                filters.append("UPPER(COALESCE(s.series,'')) NOT LIKE 'BL%'")

        if adelantos_only:
            if has_flag and "is_adelanto" in cols:
                filters.append("COALESCE(s.is_adelanto,0)=1")
            else:
                # Adelanto usa serie BL y requiere bandera; fallback a BL si no existe
                filters.append("UPPER(COALESCE(s.series,'')) LIKE 'BL%'")

        where_clause = " AND ".join(filters)

        sql = f"""
            SELECT s.id, s.series, s.number, s.datetime, s.total, c.full_name, c.dni,
                   COALESCE(s.is_proforma,0) as is_proforma,
                   COALESCE(s.is_boletin,0) as is_boletin,
                   COALESCE(s.is_adelanto,0) as is_adelanto,
                   COALESCE(s.advance_amount,0) as advance_amount,
                   COALESCE(s.estimated_total,0) as estimated_total
            FROM sales s
            LEFT JOIN clients c ON s.client_id = c.id
            WHERE {where_clause}
            ORDER BY s.datetime DESC
        """
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        conn.close()
        return rows

    def update_adelanto_amounts(self, sale_id: int, advance_amount: float, estimated_total: float) -> None:
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            subtotal = round(advance_amount / 1.18, 2)
            igv = round(advance_amount - subtotal, 2)
            cur.execute(
                """
                UPDATE sales
                SET advance_amount = ?,
                    estimated_total = ?,
                    total = ?,
                    subtotal = ?,
                    igv = ?,
                    is_adelanto = 1
                WHERE id = ?
                """,
                (advance_amount, estimated_total, advance_amount, subtotal, igv, sale_id),
            )
            conn.commit()
        finally:
            conn.close()

    def search_sales_detailed(self, text):
        conn = self.db.get_connection()
        cur = conn.cursor()
        like = f"%{text}%"
        # Join sales, clients, and sale_items
        # s: series, number, datetime
        # c: full_name
        # si: description, quantity, unit_price, subtotal
        cur.execute(
            """
            SELECT 
                s.series, s.number, s.datetime, c.full_name, 
                si.description, si.quantity, si.unit_price, si.subtotal
            FROM sales s
            JOIN clients c ON s.client_id = c.id
            JOIN sale_items si ON s.id = si.sale_id
            WHERE c.full_name LIKE ? OR c.dni LIKE ?
            ORDER BY s.datetime DESC, s.id DESC
            """,
            (like, like),
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_sales_detailed_by_client_id(self, client_id):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 
                s.series, s.number, s.datetime, c.full_name, 
                si.description, si.quantity, si.unit_price, si.subtotal
            FROM sales s
            JOIN clients c ON s.client_id = c.id
            JOIN sale_items si ON s.id = si.sale_id
            WHERE s.client_id = ?
            ORDER BY s.datetime DESC, s.id DESC
            """,
            (client_id,),
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_sale_by_serial(self, serial):
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            select_cols = self.get_sale_select_columns()
            if "serial_seguridad" not in select_cols:
                return None, []

            sql = f"SELECT {', '.join(select_cols)} FROM sales WHERE serial_seguridad = ?"
            cur.execute(sql, (serial,))
            sale = cur.fetchone()
            if not sale:
                return None, []

            sale_id = sale[0]
            sel_item_cols = self.get_sale_item_columns()
            item_sql = f"SELECT {', '.join(sel_item_cols)} FROM sale_items WHERE sale_id = ?"
            cur.execute(item_sql, (sale_id,))
            items = cur.fetchall()
            return sale, items
        finally:
            conn.close()

    def get_daily_summary(self):
        return self.get_summary_for_day(datetime.now())

    def get_summary_for_day(self, day: datetime):
        date_str = day.strftime("%Y-%m-%d")
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT COUNT(*), COALESCE(SUM(total), 0) FROM sales WHERE date(datetime) = ?",
                (date_str,),
            )
            row = cur.fetchone()
            count = row[0] if row else 0
            total = float(row[1] or 0)
            return count, total
        finally:
            conn.close()

    def get_payment_breakdown_for_day(self, day: datetime):
        date_str = day.strftime("%Y-%m-%d")
        conn = self.db.get_connection()
        cur = conn.cursor()
        breakdown = {"cash": 0.0, "yape": 0.0, "others": 0.0, "has_split": False}

        def _find_column(columns, *names):
            lowered = {col.lower(): col for col in columns}
            for name in names:
                col = lowered.get(name.lower())
                if col:
                    return col
            return None

        try:
            cur.execute("PRAGMA table_info(sales)")
            columns = [row[1] for row in cur.fetchall()]

            cash_col = _find_column(columns, "cash_amount", "cash_total", "efectivo", "efectivo_amount")
            yape_col = _find_column(columns, "yape_amount", "yape_total", "yape")
            card_col = _find_column(columns, "card_amount", "tarjeta_amount", "tarjeta", "card")
            transfer_col = _find_column(columns, "transfer_amount", "transferencia", "transfer")

            expected_fields = sum(1 for col in [cash_col, yape_col, card_col, transfer_col] if col)

            if expected_fields:
                select_parts = []
                if cash_col:
                    select_parts.append(f"COALESCE(SUM({cash_col}), 0) AS cash_sum")
                if yape_col:
                    select_parts.append(f"COALESCE(SUM({yape_col}), 0) AS yape_sum")
                if card_col:
                    select_parts.append(f"COALESCE(SUM({card_col}), 0) AS card_sum")
                if transfer_col:
                    select_parts.append(f"COALESCE(SUM({transfer_col}), 0) AS transfer_sum")

                select_sql = ", ".join(select_parts)
                cur.execute(
                    f"SELECT {select_sql} FROM sales WHERE date(datetime) = ?",
                    (date_str,),
                )
                row = cur.fetchone()
                if not row:
                    row = tuple(0 for _ in range(expected_fields))
                idx = 0
                if cash_col:
                    breakdown["cash"] = float(row[idx] or 0)
                    idx += 1
                if yape_col:
                    breakdown["yape"] = float(row[idx] or 0)
                    idx += 1
                if card_col:
                    breakdown["others"] += float(row[idx] or 0)
                    idx += 1
                if transfer_col:
                    breakdown["others"] += float(row[idx] or 0)
                breakdown["has_split"] = True
                return breakdown

            payment_method_col = _find_column(
                columns,
                "payment_method",
                "metodo_pago",
                "payment_type",
                "tipo_pago",
            )

            if payment_method_col:
                cur.execute(
                    f"SELECT {payment_method_col}, COALESCE(SUM(total), 0) FROM sales WHERE date(datetime) = ? GROUP BY {payment_method_col}",
                    (date_str,),
                )
                for method, total in cur.fetchall():
                    total_val = float(total or 0)
                    method_name = (method or "").strip().lower()
                    if any(word in method_name for word in ("yape", "plin")):
                        breakdown["yape"] += total_val
                    elif any(word in method_name for word in ("efectivo", "cash", "contado")):
                        breakdown["cash"] += total_val
                    else:
                        breakdown["others"] += total_val
                breakdown["has_split"] = True
                return breakdown

            cur.execute(
                "SELECT COALESCE(SUM(total), 0) FROM sales WHERE date(datetime) = ?",
                (date_str,),
            )
            total = cur.fetchone()
            breakdown["cash"] = float((total[0] if total else 0) or 0)
            return breakdown
        finally:
            conn.close()

    def get_month_sales_total(self, day: datetime) -> float:
        start_month = day.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (start_month + timedelta(days=32)).replace(day=1)

        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT COALESCE(SUM(total), 0)
                FROM sales
                WHERE datetime >= ? AND datetime < ?
                """,
                (
                    start_month.strftime("%Y-%m-%d %H:%M:%S"),
                    next_month.strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            row = cur.fetchone()
            return float(row[0] or 0.0)
        finally:
            conn.close()

    def get_top_products_for_day(self, day: datetime, limit: int = 5):
        date_str = day.strftime("%Y-%m-%d")
        conn = self.db.get_connection()
        cur = conn.cursor()

        try:
            cur.execute(
                """
                SELECT
                    COALESCE(si.description, 'Sin descripción') AS description,
                    COALESCE(SUM(si.quantity), 0) AS total_qty,
                    COALESCE(SUM(si.subtotal), 0) AS total_amount
                FROM sale_items si
                INNER JOIN sales s ON s.id = si.sale_id
                WHERE date(s.datetime) = ?
                GROUP BY si.description
                ORDER BY total_qty DESC, total_amount DESC
                LIMIT ?
                """,
                (date_str, limit),
            )
            rows = cur.fetchall()
            results = []
            for description, qty, amount in rows:
                try:
                    quantity = float(qty or 0.0)
                except (TypeError, ValueError):
                    quantity = 0.0
                try:
                    total_amount = float(amount or 0.0)
                except (TypeError, ValueError):
                    total_amount = 0.0
                results.append(
                    {
                        "description": description or "Sin descripción",
                        "quantity": quantity,
                        "amount": total_amount,
                    }
                )
            return results
        finally:
            conn.close()

    def get_weekly_sales(self):
        conn = self.db.get_connection()
        cur = conn.cursor()
        sql = """
            SELECT date(datetime) as sale_date, SUM(total)
            FROM sales
            WHERE date(datetime) >= date('now', '-6 days')
            GROUP BY date(datetime)
            ORDER BY sale_date ASC
        """
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
        return rows

    def delete_sale(self, sale_id):
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM sale_items WHERE sale_id = ?", (sale_id,))
            cur.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error borrando venta: {e}")
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_last_sale(self):
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(sales)")
            sales_cols = [r[1] for r in cur.fetchall()]
            select_cols = [
                c
                for c in [
                    "id",
                    "series",
                    "number",
                    "datetime",
                    "client_id",
                    "subtotal",
                    "igv",
                    "total",
                    "pdf_path",
                ]
                if c in sales_cols
            ]
            if "serial_seguridad" in sales_cols:
                select_cols.append("serial_seguridad")
            if "discount" in sales_cols:
                select_cols.append("discount")

            sql = f"SELECT {', '.join(select_cols)} FROM sales ORDER BY id DESC LIMIT 1"
            cur.execute(sql)
            row = cur.fetchone()
            return row
        finally:
            conn.close()
