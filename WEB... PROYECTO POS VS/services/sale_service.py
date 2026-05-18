import random
import string
from datetime import datetime, timedelta

from repositories.sale_repo import SaleRepository
from repositories.client_repo import ClientRepository
from services.security_service import SecurityService


class SaleService:
    def __init__(self, sale_repo: SaleRepository, client_repo: ClientRepository, settings_service: SecurityService):
        self.sale_repo = sale_repo
        self.client_repo = client_repo
        self.settings_service = settings_service

    def _generate_security_serial(self):
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=12))

    def create_sale(
        self,
        series,
        client_id,
        items,
        discount=0.0,
        include_igv=True,
        product_service=None,
        is_proforma: bool = False,
        is_boletin: bool = False,
        is_adelanto: bool = False,
        advance_amount: float = 0.0,
        estimated_total: float | None = None,
    ):
        if not items:
            raise ValueError("Debe agregar al menos un ítem al comprobante.")

        subtotal_items = sum(it["subtotal"] for it in items)

        if is_adelanto:
            total = max(0.0, round(float(advance_amount or 0), 2))
            total_bruto = total
        else:
            total_bruto = max(0, subtotal_items - discount)
            total = max(0.0, round(total_bruto, 2))

        if include_igv:
            base_imponible = round(total / 1.18, 2)
            igv = round(total - base_imponible, 2)
        else:
            base_imponible = total
            igv = 0.0

        number = self.sale_repo.get_next_number(series)
        dt = datetime.now()

        client = self.client_repo.get_client_by_id(client_id)
        client_dni = client[1] if client else "00000000"

        resumen_items = ", ".join([f"{i['description']} x{int(i['quantity'])}" for i in items])
        if len(resumen_items) > 50:
            resumen_items = resumen_items[:47] + "..."

        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        serial_seguridad = self.settings_service.generate_ticket_signature(
            series,
            number,
            total,
            dt_str,
            client_dni,
            resumen_items,
        )

        sale_id = self.sale_repo.create_sale(
            series,
            number,
            dt_str,
            client_id,
            base_imponible,
            igv,
            total,
            items,
            serial_seguridad=serial_seguridad,
            discount=discount,
            is_proforma=is_proforma,
            is_boletin=is_boletin,
            is_adelanto=is_adelanto,
            advance_amount=advance_amount,
            estimated_total=estimated_total,
        )

        if product_service and not is_proforma and not is_boletin and not is_adelanto:
            for item in items:
                product_id = item.get("product_id")
                quantity = item.get("quantity", 0)
                if product_id and quantity > 0:
                    product_service.reduce_stock(product_id, quantity)

        return sale_id, series, number, base_imponible, igv, total, serial_seguridad

    def get_sale(self, sale_id):
        return self.sale_repo.get_sale(sale_id)

    def map_sale_row(self, sale_row):
        return self.sale_repo.map_sale_row(sale_row)

    def get_pdf_path(self, sale_id):
        return self.sale_repo.get_pdf_path(sale_id)

    def get_sale_by_serial(self, serial):
        return self.sale_repo.get_sale_by_serial(serial)

    def search_sales_by_client(self, text, *, proformas_only: bool = False, boletines_only: bool = False, sales_only: bool = False):
        return self.sale_repo.search_sales_by_client(text, proformas_only=proformas_only, boletines_only=boletines_only, sales_only=sales_only)

    def search_sales_by_client_with_adelantos(self, text, *, proformas_only=False, boletines_only=False, sales_only=False, adelantos_only=False):
        return self.sale_repo.search_sales_by_client(
            text,
            proformas_only=proformas_only,
            boletines_only=boletines_only,
            sales_only=sales_only,
            adelantos_only=adelantos_only,
        )

    def update_adelanto_amounts(self, sale_id: int, advance_amount: float, estimated_total: float) -> None:
        self.sale_repo.update_adelanto_amounts(sale_id, advance_amount, estimated_total)

    def search_sales_detailed(self, text):
        return self.sale_repo.search_sales_detailed(text)

    def get_sales_detailed_by_client_id(self, client_id):
        return self.sale_repo.get_sales_detailed_by_client_id(client_id)

    def set_pdf_path(self, sale_id, pdf_path):
        """Deprecated: PDFs ahora son transitorios; no persistimos rutas."""
        try:
            return self.sale_repo.update_pdf_path(sale_id, None)
        except Exception:
            return None

    def get_daily_summary(self):
        return self.sale_repo.get_daily_summary()

    def get_summary_for_day(self, day: datetime):
        return self.sale_repo.get_summary_for_day(day)

    def get_previous_day_summary(self):
        return self.sale_repo.get_summary_for_day(datetime.now() - timedelta(days=1))

    def get_payment_breakdown_for_day(self, day: datetime):
        return self.sale_repo.get_payment_breakdown_for_day(day)

    def get_payment_breakdown_today(self):
        return self.get_payment_breakdown_for_day(datetime.now())

    def get_month_sales_total(self, day: datetime | None = None) -> float:
        target_day = day or datetime.now()
        repo_method = getattr(self.sale_repo, "get_month_sales_total", None)
        if callable(repo_method):
            result = repo_method(target_day)
            if isinstance(result, (int, float)):
                return float(result)
            if isinstance(result, str):
                try:
                    return float(result)
                except ValueError:
                    return 0.0
        return 0.0

    def get_top_products_for_day(self, day: datetime | None = None, limit: int = 5):
        target_day = day or datetime.now()
        repo_method = getattr(self.sale_repo, "get_top_products_for_day", None)
        if callable(repo_method):
            return repo_method(target_day, limit)
        return []

    def get_weekly_sales(self):
        return self.sale_repo.get_weekly_sales()

    def delete_sale(self, sale_id, product_service=None):
        if product_service:
            try:
                sale, items = self.get_sale(sale_id)
                if items:
                    for item in items:
                        pid = item[1]
                        qty = item[4]
                        if pid and qty > 0:
                            product_service.reduce_stock(pid, -qty)
            except Exception as e:
                print(f"Error restaurando stock al anular venta: {e}")

        return self.sale_repo.delete_sale(sale_id)

    def get_last_sale(self):
        return self.sale_repo.get_last_sale()
