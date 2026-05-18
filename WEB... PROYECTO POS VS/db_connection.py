import sqlite3

import settings


class Database:
    """Manejador simple de conexión a SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)


def get_default_database() -> "Database":
    return Database(settings.get_db_path())
