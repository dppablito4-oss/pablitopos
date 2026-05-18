from db_connection import Database


class SettingsRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_pin(self):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key='admin_pin'")
        row = cur.fetchone()
        conn.close()
        return row[0] if row else "1234"

    def set_pin(self, new_pin):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_pin', ?)",
            (new_pin,),
        )
        conn.commit()
        conn.close()

    def get_setting(self, key, default=""):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else default

    def set_setting(self, key, value):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()
        conn.close()
