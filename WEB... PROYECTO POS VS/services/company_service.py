from repositories.company_repo import CompanyRepository


class CompanyService:
    def __init__(self, repo: CompanyRepository):
        self.repo = repo

    def get_all_profiles(self):
        rows = self.repo.get_all_profiles()
        profiles = []
        for row in rows:
            profiles.append(
                {
                    "id": row[0],
                    "name": row[1] or "",
                    "ruc": row[2] or "",
                    "address": row[3] or "",
                    "phone": row[4] or "",
                    "email": row[5] or "",
                    "website": row[6] or "",
                    "footer_message": row[7] or "",
                    "logo_path": row[8] if len(row) > 8 else None,
                    "brand_color": (row[9] if len(row) > 9 and row[9] else "#1f77b4"),
                    "include_igv": bool(row[10]) if len(row) > 10 else True,
                    "yape_qr_path": row[11] if len(row) > 11 else None,
                }
            )
        return profiles

    def get_profile(self, company_id=1):
        row = self.repo.get_profile(company_id)
        if not row:
            return {
                "id": company_id,
                "name": "",
                "ruc": "",
                "address": "",
                "phone": "",
                "email": "",
                "website": "",
                "footer_message": "Gracias por su compra",
                "logo_path": None,
                "brand_color": "#1f77b4",
                "include_igv": True,
                "yape_qr_path": None,
            }
        return {
            "id": row[0],
            "name": row[1] or "",
            "ruc": row[2] or "",
            "address": row[3] or "",
            "phone": row[4] or "",
            "email": row[5] or "",
            "website": row[6] or "",
            "footer_message": row[7] or "",
            "logo_path": row[8] if len(row) > 8 else None,
            "brand_color": (row[9] if len(row) > 9 and row[9] else "#1f77b4"),
            "include_igv": bool(row[10]) if len(row) > 10 else True,
            "yape_qr_path": row[11] if len(row) > 11 else None,
        }

    def save_profile(self, company_id, data):
        self.repo.save_profile(
            company_id,
            data.get("name", ""),
            data.get("ruc", ""),
            data.get("address", ""),
            data.get("phone", ""),
            data.get("email", ""),
            data.get("website", ""),
            data.get("footer_message", ""),
            data.get("logo_path"),
            data.get("brand_color", "#1f77b4"),
            data.get("include_igv", 1),
            data.get("yape_qr_path"),
        )

    def create_profile(
        self,
        name,
        ruc="",
        address="",
        phone="",
        email="",
        website="",
        footer_message="",
        logo_path=None,
        brand_color="#1f77b4",
        include_igv=1,
        yape_qr_path=None,
    ):
        return self.repo.create_profile(
            name,
            ruc,
            address,
            phone,
            email,
            website,
            footer_message,
            logo_path,
            brand_color,
            include_igv,
            yape_qr_path,
        )

    def update_profile(
        self,
        company_id,
        name,
        ruc,
        address,
        phone,
        email,
        website,
        footer_message,
        logo_path,
        brand_color,
        include_igv,
        yape_qr_path=None,
    ):
        self.repo.save_profile(
            company_id,
            name,
            ruc,
            address,
            phone,
            email,
            website,
            footer_message,
            logo_path,
            brand_color,
            include_igv,
            yape_qr_path,
        )

    def delete_profile(self, company_id):
        self.repo.soft_delete_profile(company_id)
