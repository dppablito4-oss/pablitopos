from db_connection import Database


class CompanyRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_all_profiles(self):
        """Obtiene todos los perfiles de empresa activos."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        # Construir columna seleccionada dinámicamente para soportar esquemas antiguos
        try:
            cur.execute("PRAGMA table_info(company_profile)")
            cols = [r[1] for r in cur.fetchall()]
        except Exception:
            cols = ['id', 'name', 'ruc', 'address', 'phone', 'email', 'website', 'footer_message', 'logo_path', 'brand_color', 'include_igv', 'yape_qr_path']

        select_order = ['id', 'name', 'ruc', 'address', 'phone', 'email', 'website', 'footer_message', 'logo_path', 'brand_color', 'include_igv', 'yape_qr_path']
        select_cols = [c for c in select_order if c in cols]
        sql = f"SELECT {', '.join(select_cols)} FROM company_profile WHERE is_active = 1 ORDER BY name"
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
        return rows

    def get_profile(self, company_id=1):
        """Obtiene un perfil específico por ID (por defecto el primero)."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("PRAGMA table_info(company_profile)")
            cols = [r[1] for r in cur.fetchall()]
        except Exception:
            cols = ['id', 'name', 'ruc', 'address', 'phone', 'email', 'website', 'footer_message', 'logo_path', 'brand_color', 'include_igv', 'yape_qr_path']

        select_order = ['id', 'name', 'ruc', 'address', 'phone', 'email', 'website', 'footer_message', 'logo_path', 'brand_color', 'include_igv', 'yape_qr_path']
        select_cols = [c for c in select_order if c in cols]
        sql = f"SELECT {', '.join(select_cols)} FROM company_profile WHERE id = ?"
        cur.execute(sql, (company_id,))
        row = cur.fetchone()
        conn.close()
        return row

    def save_profile(self, company_id, name, ruc, address, phone, email, website, footer_message, logo_path, brand_color="#1f77b4", include_igv=1, yape_qr_path=None):
        """Guarda o actualiza un perfil."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM company_profile WHERE id = ?", (company_id,))
        exists = cur.fetchone()

        if exists:
            cur.execute(
                """
                UPDATE company_profile
                SET name=?, ruc=?, address=?, phone=?, email=?, website=?, footer_message=?, logo_path=?, brand_color=?, include_igv=?, yape_qr_path=?
                WHERE id = ?
                """,
                (name, ruc, address, phone, email, website, footer_message, logo_path, brand_color, include_igv, yape_qr_path, company_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO company_profile (name, ruc, address, phone, email, website, footer_message, logo_path, brand_color, is_active, include_igv, yape_qr_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (name, ruc, address, phone, email, website, footer_message, logo_path, brand_color, include_igv, yape_qr_path),
            )

        conn.commit()
        conn.close()

    def create_profile(self, name, ruc="", address="", phone="", email="", website="", footer_message="", logo_path=None, brand_color="#1f77b4", include_igv=1, yape_qr_path=None):
        """Crea un nuevo perfil de empresa."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO company_profile (name, ruc, address, phone, email, website, footer_message, logo_path, brand_color, is_active, include_igv, yape_qr_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (name, ruc, address, phone, email, website, footer_message, logo_path, brand_color, include_igv, yape_qr_path),
        )
        conn.commit()
        company_id = cur.lastrowid
        conn.close()
        return company_id

    def soft_delete_profile(self, company_id):
        """Desactiva un perfil (Soft Delete)."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE company_profile SET is_active = 0 WHERE id = ?", (company_id,))
        conn.commit()
        conn.close()
