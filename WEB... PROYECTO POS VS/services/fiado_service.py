from typing import Any

from repositories.fiado_repo import FiadoRepository


class FiadoService:
    def __init__(self, repo: FiadoRepository, pdf_service=None, sale_service=None, product_service=None):
        self.repo = repo
        self.pdf_service = pdf_service
        self.sale_service = sale_service
        self.product_service = product_service

    def _map_fiado_row(self, row: Any) -> dict[str, Any]:
        if not row:
            return {}
        keys = [
            "id",
            "code",
            "client_id",
            "status",
            "total_bruto",
            "total_pagado",
            "total_pendiente",
            "pdf_path",
            "sale_id",
            "created_at",
            "updated_at",
        ]
        return {k: row[idx] if idx < len(row) else None for idx, k in enumerate(keys)}

    def _map_item_row(self, row: Any) -> dict[str, Any]:
        if not row:
            return {}
        keys = [
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
        return {k: row[idx] if idx < len(row) else None for idx, k in enumerate(keys)}

    def create_fiado(self, client_id: int, items: list[dict[str, Any]]) -> dict[str, Any]:
        if not items:
            raise ValueError("Debe agregar al menos un item al fiado.")

        normalized_items: list[dict[str, Any]] = []
        for item in items:
            qty = float(item.get("quantity", 0) or 0)
            price = float(item.get("unit_price", 0) or 0)
            subtotal = float(item.get("subtotal", qty * price))
            normalized_items.append(
                {
                    "product_id": item.get("product_id"),
                    "description": item.get("description", ""),
                    "quantity": qty,
                    "unit": item.get("unit", ""),
                    "unit_price": price,
                    "subtotal": subtotal,
                    "block": item.get("block", ""),
                    "status": item.get("status", "pendiente"),
                }
            )

        total_bruto = sum(i["subtotal"] for i in normalized_items)
        total_pagado = sum(i["subtotal"] for i in normalized_items if (i.get("status") or "").lower() == "pagado")
        total_pendiente = max(0.0, round(total_bruto - total_pagado, 2))
        code = self.repo.generate_code(prefix="C")

        fiado_id = self.repo.create_fiado(
            client_id=client_id,
            items=normalized_items,
            code=code,
            total_bruto=total_bruto,
            total_pagado=total_pagado,
            total_pendiente=total_pendiente,
            status="pagado" if total_pendiente <= 0 else "pendiente",
            pdf_path=None,
            sale_id=None,
        )
        return {"id": fiado_id, "code": code, "total_bruto": total_bruto, "total_pendiente": total_pendiente}

    def get_fiado_with_items(self, fiado_id: int) -> dict[str, Any]:
        fiado_row, item_rows = self.repo.get_fiado(fiado_id)
        fiado = self._map_fiado_row(fiado_row)
        items = [self._map_item_row(r) for r in item_rows]
        return {"fiado": fiado, "items": items}

    def list_by_client(self, client_id: int) -> list[dict[str, Any]]:
        rows = self.repo.list_by_client(client_id)
        return [self._map_fiado_row(r) for r in rows]

    def search_fiados(self, text: str) -> list[dict[str, Any]]:
        rows = self.repo.search_fiados(text)
        mapped: list[dict[str, Any]] = []
        for r in rows:
            mapped.append(
                {
                    "id": r[0] if len(r) > 0 else None,
                    "code": r[1] if len(r) > 1 else None,
                    "status": r[2] if len(r) > 2 else None,
                    "total_bruto": r[3] if len(r) > 3 else 0.0,
                    "total_pagado": r[4] if len(r) > 4 else 0.0,
                    "total_pendiente": r[5] if len(r) > 5 else 0.0,
                    "created_at": r[6] if len(r) > 6 else "",
                    "updated_at": r[7] if len(r) > 7 else "",
                    "full_name": r[8] if len(r) > 8 else "",
                    "dni": r[9] if len(r) > 9 else "",
                    "sale_id": r[10] if len(r) > 10 else None,
                }
            )
        return mapped

    def set_item_paid(self, item_id: int, paid: bool) -> dict[str, Any]:
        status = "pagado" if paid else "pendiente"
        fiado_id = self.repo.set_item_status(item_id, status)
        if fiado_id is None:
            raise ValueError("Item de fiado no encontrado")
        self.repo.recalc_totals(fiado_id)
        return self.get_fiado_with_items(fiado_id)

    def set_pdf_path(self, fiado_id: int, pdf_path: str) -> None:
        self.repo.set_pdf_path(fiado_id, pdf_path)

    def set_sale_id(self, fiado_id: int, sale_id: int) -> None:
        self.repo.set_sale_id(fiado_id, sale_id)
        self.repo.set_status(fiado_id, "pagado")

    def set_status(self, fiado_id: int, status: str) -> None:
        self.repo.set_status(fiado_id, status)

    def recalc_totals(self, fiado_id: int) -> dict[str, Any]:
        self.repo.recalc_totals(fiado_id)
        return self.get_fiado_with_items(fiado_id)

    def generate_fiado_pdf(self, fiado_id: int, client: dict | None = None, output_dir: str | None = "temp") -> str:
        if not self.pdf_service:
            raise RuntimeError("Servicio de PDF no disponible.")

        data = self.get_fiado_with_items(fiado_id)
        fiado = data.get("fiado") or {}
        items = data.get("items") or []
        if not fiado:
            raise ValueError("Fiado no encontrado")

        pdf_path = self.pdf_service.generate_fiado_pdf(fiado, items, client=client, output_dir=output_dir)

        try:
            self.set_pdf_path(fiado_id, pdf_path)
        except Exception:
            pass
        return pdf_path

    def generate_official_sale(self, fiado_id: int, series: str = "B001") -> dict[str, Any]:
        if not self.sale_service or not self.pdf_service:
            raise RuntimeError("Servicios de venta o PDF no disponibles.")

        data = self.get_fiado_with_items(fiado_id)
        fiado = data.get("fiado") or {}
        items = data.get("items") or []
        if not fiado:
            raise ValueError("Fiado no encontrado")
        status = (fiado.get("status") or "").lower()
        if status != "pagado":
            raise ValueError("El fiado debe estar pagado para generar la boleta oficial.")
        if fiado.get("sale_id"):
            raise ValueError("Este fiado ya tiene boleta generada.")

        sale_items: list[dict[str, Any]] = []
        for item in items:
            sale_items.append(
                {
                    "product_id": item.get("product_id"),
                    "description": item.get("description", ""),
                    "unit": item.get("unit", ""),
                    "quantity": float(item.get("quantity", 0) or 0),
                    "unit_price": float(item.get("unit_price", 0) or 0),
                    "subtotal": float(item.get("subtotal", 0) or 0),
                }
            )

        sale_id, series_used, number, subtotal, igv, total, serial = self.sale_service.create_sale(
            series,
            fiado.get("client_id"),
            sale_items,
            discount=0.0,
            include_igv=True,
            product_service=self.product_service,
        )

        pdf_path = self.pdf_service.generate_sale_pdf(sale_id)
        self.set_sale_id(fiado_id, sale_id)
        updated = self.get_fiado_with_items(fiado_id).get("fiado") or fiado
        return {
            "sale_id": sale_id,
            "series": series_used,
            "number": number,
            "pdf_path": pdf_path,
            "subtotal": subtotal,
            "igv": igv,
            "total": total,
            "serial_seguridad": serial,
            "fiado": updated,
        }
