from datetime import datetime
from db_connection import Database


class ClientRepository:
    def __init__(self, db: Database):
        self.db = db

    def search_clients(self, text):
        text = text or ""
        conn = self.db.get_connection()
        cur = conn.cursor()
        like = f"%{text}%"
        cur.execute(
            """
            SELECT id, dni, full_name, phone, email, address, created_at
            FROM clients
            WHERE dni LIKE ? OR full_name LIKE ? OR phone LIKE ?
            ORDER BY full_name
            """,
            (like, like, like),
        )
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_client_by_id(self, client_id):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, dni, full_name, phone, email, address, created_at
            FROM clients
            WHERE id = ?
            """,
            (client_id,),
        )
        row = cur.fetchone()
        conn.close()
        return row

    def create_client(self, dni, full_name, phone, email, address):
        conn = self.db.get_connection()
        cur = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """
            INSERT INTO clients (dni, full_name, phone, email, address, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (dni, full_name, phone, email, address, created_at),
        )
        conn.commit()
        client_id = cur.lastrowid
        conn.close()
        return client_id

    def update_client(self, client_id, dni, full_name, phone, email, address):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE clients
            SET dni = ?, full_name = ?, phone = ?, email = ?, address = ?
            WHERE id = ?
            """,
            (dni, full_name, phone, email, address, client_id),
        )
        conn.commit()
        conn.close()

    def delete_client(self, client_id):
        """Elimina un cliente de la base de datos."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        conn.commit()
        conn.close()
