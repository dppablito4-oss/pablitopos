import os
import sys
import shutil
import tempfile
import threading
from datetime import datetime
from typing import Any, List

import qrcode
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from repositories.client_repo import ClientRepository
from repositories.sale_repo import SaleRepository
from services.company_service import CompanyService
from settings import PDF_DIR


class PdfService:
    def __init__(self, company_service: CompanyService, client_repo: ClientRepository, sale_repo: SaleRepository) -> None:
        self.company_service = company_service
        self.client_repo = client_repo
        self.sale_repo = sale_repo
        self._transient_dirs: list[str] = []

    def cleanup_transient_pdfs(self) -> None:
        """Best-effort removal of transient PDF directories created during runtime."""

        seen: set[str] = set()
        transient_dirs: list[str] = []

        # Snapshot to avoid holding references while deleting
        for path in self._transient_dirs:
            if not path or path in seen:
                continue
            seen.add(path)
            transient_dirs.append(path)

        self._transient_dirs.clear()

        for path in transient_dirs:
            try:
                shutil.rmtree(path, ignore_errors=True)
            except Exception:
                # Ignore any cleanup failure to avoid blocking app shutdown
                pass

    def convertir_monto_a_letras(self, monto: float) -> str:
        """Convierte monto numérico al formato SUNAT ("UN MIL ... CON 42/100 SOLES")."""

        unidades = ("", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE")
        especiales = {10: "DIEZ", 11: "ONCE", 12: "DOCE", 13: "TRECE", 14: "CATORCE", 15: "QUINCE"}
        decenas = ("", "DIEZ", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA")
        centenas = (
            "",
            "CIENTO",
            "DOSCIENTOS",
            "TRESCIENTOS",
            "CUATROCIENTOS",
            "QUINIENTOS",
            "SEISCIENTOS",
            "SETECIENTOS",
            "OCHOCIENTOS",
            "NOVECIENTOS",
        )

        def tres_digitos(n: int) -> str:
            n = int(n)
            if n == 0:
                return ""
            if n == 100:
                return "CIEN"
            c = n // 100
            d = (n % 100) // 10
            u = n % 10
            parts: List[str] = []
            if c > 0:
                parts.append(centenas[c])
            if d == 1:
                val = 10 + u
                parts.append(especiales.get(val, "DIECI" + unidades[u].lower()))
            elif d == 2 and u > 0:
                parts.append("VEINTI" + unidades[u].lower())
            else:
                if d > 0:
                    parts.append(decenas[d])
                if u > 0:
                    parts.append(("Y " if d >= 3 else "") + unidades[u])
            return " ".join([p for p in parts if p]).upper()

        entero = int(abs(int(monto)))
        centavos = int(round((abs(monto) - entero) * 100))

        millones = entero // 1_000_000
        miles = (entero % 1_000_000) // 1_000
        cientos = entero % 1_000

        partes: List[str] = []
        if millones:
            partes.append("UN MILLON" if millones == 1 else f"{tres_digitos(millones)} MILLONES")
        if miles:
            partes.append("UN MIL" if miles == 1 else f"{tres_digitos(miles)} MIL")
        if cientos:
            partes.append(tres_digitos(cientos))

        texto_entero = " ".join([p for p in partes if p]).strip() if partes else "CERO"
        texto_entero = texto_entero.replace("UNO MIL", "UN MIL").replace("UNO MILLON", "UN MILLON")

        return f"{texto_entero} CON {centavos:02d}/100 SOLES"

    def generate_sale_pdf(self, sale_id, output_dir: str = PDF_DIR, company_profile: dict | None = None) -> str:
        if canvas is None:
            raise RuntimeError("La librería reportlab no está instalada.")

        # Si output_dir es None o "temp", generamos en un directorio temporal y lo limpiamos a discreción
        transient = output_dir is None or str(output_dir).lower() == "temp"
        if transient:
            # Guardar PDFs temporales en APPDATA (siempre escribible) para evitar bloqueos en Program Files
            base_temp_root = PDF_DIR if os.path.isdir(PDF_DIR) else tempfile.gettempdir()
            output_dir = tempfile.mkdtemp(prefix="pablito_pdf_", dir=base_temp_root)
            self._transient_dirs.append(output_dir)
        else:
            os.makedirs(output_dir, exist_ok=True)

        sale, items = self.sale_repo.get_sale(sale_id)
        if not sale:
            raise ValueError("Comprobante no encontrado.")

        try:
            conn_tmp = self.sale_repo.db.get_connection()
            cur_tmp = conn_tmp.cursor()
            cur_tmp.execute("PRAGMA table_info(sales)")
            sales_all_cols = [r[1] for r in cur_tmp.fetchall()]
            conn_tmp.close()
        except Exception:
            sales_all_cols = [
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
            if c in sales_all_cols
        ]
        if "serial_seguridad" in sales_all_cols:
            select_cols.append("serial_seguridad")
        if "discount" in sales_all_cols:
            select_cols.append("discount")

        sale_map = dict(zip(select_cols, sale)) if sale else {}

        series = sale_map.get("series", "")
        number = sale_map.get("number", 0)
        dt_str = sale_map.get("datetime", "")
        client_id = sale_map.get("client_id")
        company_id = sale_map.get("company_id")
        subtotal = float(sale_map.get("subtotal", 0.0) or 0.0)
        igv = float(sale_map.get("igv", 0.0) or 0.0)
        total = float(sale_map.get("total", 0.0) or 0.0)
        pdf_path_db = sale_map.get("pdf_path")
        serial_seguridad = sale_map.get("serial_seguridad")
        discount = float(sale_map.get("discount", 0.0) or 0.0)
        is_proforma = bool(sale_map.get("is_proforma", 0))
        is_boletin = bool(sale_map.get("is_boletin", 0))
        is_adelanto = bool(sale_map.get("is_adelanto", 0))
        advance_amount = float(sale_map.get("advance_amount", 0.0) or 0.0)
        estimated_total = float(sale_map.get("estimated_total", 0.0) or 0.0)
        if not is_proforma:
            try:
                is_proforma = str(series).upper().startswith("PF")
            except Exception:
                is_proforma = False
        if not is_boletin:
            try:
                is_boletin = str(series).upper().startswith("BL")
            except Exception:
                is_boletin = False

        client = self.client_repo.get_client_by_id(client_id)

        if company_profile:
            company = company_profile
        else:
            resolved_company_id = company_id if company_id else 1
            company = self.company_service.get_profile(resolved_company_id)

        try:
            dt_obj = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            dt_obj = datetime.now()
        date_str = dt_obj.strftime("%d/%m/%Y")

        if is_boletin:
            filename_prefix = "ADELANTO" if is_adelanto else "BOLETIN"
        elif is_proforma:
            filename_prefix = "PROFORMA"
        else:
            filename_prefix = "COMPROBANTE"
        filename = f"{filename_prefix}_{series}_{int(number):06d}_{dt_obj.strftime('%Y%m%d')}.pdf"
        pdf_path = os.path.join(output_dir, filename)

        try:
            c = canvas.Canvas(pdf_path, pagesize=A4)
        except PermissionError as exc:
            raise PermissionError(
                f"El archivo PDF está abierto en otro programa.\nPor favor, cierre '{filename}' e intente nuevamente."
            ) from exc
        width, height = A4

        margin_left = 10 * mm
        margin_right = 10 * mm

        logo_x = 10 * mm
        logo_y = height - 40 * mm
        logo_w = 50 * mm
        logo_h = 30 * mm

        if company.get("logo_path") and os.path.exists(company["logo_path"]):
            try:
                c.drawImage(
                    company["logo_path"],
                    logo_x,
                    logo_y,
                    width=logo_w,
                    height=logo_h,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass

        data_x = 65 * mm
        data_w = 70 * mm
        data_y_top = height - 15 * mm

        styles = getSampleStyleSheet()
        style_name = ParagraphStyle(
            "CompanyName",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            alignment=TA_CENTER,
            leading=16,
        )
        style_details = ParagraphStyle(
            "CompanyDetails",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            alignment=TA_CENTER,
            leading=8,
        )

        comp_name = (company.get("name") or "EMPRESA").upper()
        details_list: List[str] = []
        address = company.get("address") if company else ""
        if address:
            details_list.append(str(address))
        website = company.get("website") if company else ""
        if website:
            details_list.append(str(website))
        email = company.get("email") if company else ""
        if email:
            details_list.append(str(email))
        phone = company.get("phone") if company else ""
        if phone:
            details_list.append(f"Tlf: {phone}")
        details_text = "<br/>".join(details_list)

        p_name = Paragraph(comp_name, style_name)
        p_details = Paragraph(details_text, style_details)

        w_name, h_name = p_name.wrap(data_w, 50 * mm)
        p_name.drawOn(c, data_x, data_y_top - h_name)

        w_det, h_det = p_details.wrap(data_w, 60 * mm)
        p_details.drawOn(c, data_x, data_y_top - h_name - h_det - 2 * mm)

        ruc_x = 140 * mm
        ruc_w = 60 * mm
        ruc_h = 30 * mm
        ruc_y = height - 40 * mm

        c.setLineWidth(1)
        c.setStrokeColor(colors.black)
        c.rect(ruc_x, ruc_y, ruc_w, ruc_h)

        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(ruc_x + ruc_w / 2, ruc_y + ruc_h - 5 * mm, f"RUC: {company.get('ruc', '')}")
        c.setFont("Helvetica-Bold", 9)
        if is_boletin:
            doc_title = "RECIBO DE ADELANTO" if is_adelanto else "BOLETIN"
        else:
            doc_title = "PROFORMA" if is_proforma else "COMPROBANTE DE PAGO"
        c.drawCentredString(ruc_x + ruc_w / 2, ruc_y + ruc_h / 2, doc_title)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(ruc_x + ruc_w / 2, ruc_y + 5 * mm, f"Nº {series}-{int(number):06d}")

        client_entry = client or []
        client_name = client_entry[2] if len(client_entry) > 2 else "CLIENTE VARIOS"
        client_address = client_entry[5] if len(client_entry) > 5 else ""
        client_doc = client_entry[1] if len(client_entry) > 1 else ""

        client_y = ruc_y - 12 * mm
        c.setFont("Helvetica", 9)
        c.drawString(margin_left, client_y, f"CLIENTE: {client_name}")
        c.drawString(margin_left, client_y - 5 * mm, f"DIRECCION: {client_address}")
        c.drawString(margin_left, client_y - 10 * mm, f"DNI/RUC: {client_doc}")

        c.drawRightString(width - margin_right, client_y, f"FECHA: {date_str}")
        c.drawRightString(width - margin_right, client_y - 5 * mm, "MONEDA: SOLES")

        col_widths = [15 * mm, 20 * mm, 20 * mm, 90 * mm, 20 * mm, 25 * mm]
        table_y = client_y - 15 * mm

        data_table: List[List[Any]] = [["CANT", "U.M.", "CODIGO", "DESCRIPCION", "P.U.", "IMPORTE"]]
        expense_rows: List[int] = []

        style_desc = ParagraphStyle("CellDesc", parent=styles["Normal"], fontSize=8, leading=9)

        try:
            conn_i = self.sale_repo.db.get_connection()
            cur_i = conn_i.cursor()
            cur_i.execute("PRAGMA table_info(sale_items)")
            item_cols = [r[1] for r in cur_i.fetchall()]
            conn_i.close()
        except Exception:
            item_cols = [
                "id",
                "product_id",
                "description",
                "unit",
                "quantity",
                "unit_price",
                "subtotal",
            ]

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
                "discount",
            ]
            if c in item_cols
        ]

        for item in items:
            item_map = dict(zip(sel_item_cols, item)) if sel_item_cols else {}
            qty = float(item_map.get("quantity", 0.0) or 0.0)
            unit = str(item_map.get("unit", "") or "")
            code = str(item_map.get("product_id", "-") or "-")
            desc = str(item_map.get("description", "") or "")
            unit_price = float(item_map.get("unit_price", 0.0) or 0.0)
            importe = float(item_map.get("subtotal", unit_price * (qty or 1)) or (unit_price * (qty or 1)))

            row_index = len(data_table)
            if importe < 0:
                expense_rows.append(row_index)

            data_table.append(
                [
                    f"{qty:.2f}",
                    unit,
                    code,
                    Paragraph(desc, style_desc),
                    f"{unit_price:.2f}",
                    f"{importe:.2f}",
                ]
            )

        table = Table(data_table, colWidths=col_widths)
        style_rows = [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (3, 0), (3, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#B2EBF2")),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
        ]

        for row in expense_rows:
            style_rows.append(("BACKGROUND", (0, row), (-1, row), HexColor("#FFECEC")))
            style_rows.append(("TEXTCOLOR", (0, row), (-1, row), HexColor("#B3261E")))

        table.setStyle(TableStyle(style_rows))

        table_width, table_height = table.wrap(width - 20 * mm, height)
        table.drawOn(c, margin_left, table_y - table_height)

        footer_y = table_y - table_height - 8 * mm
        right_align_x = margin_left + sum(col_widths)

        suma_importes = sum(float(it[6] if len(it) > 6 else 0.0) for it in items)

        include_igv_flag = bool((company or {}).get("include_igv", True))
        base_imponible = round(subtotal, 2)
        igv_valor = round(igv, 2)

        if include_igv_flag:
            if base_imponible <= 0 and total > 0:
                base_imponible = round(total / 1.18, 2)
            if total > 0:
                igv_valor = round(total - base_imponible, 2)
        else:
            base_imponible = round(total, 2)
            igv_valor = 0.0

        if base_imponible > total:
            base_imponible = total
        if abs(igv_valor) < 0.01:
            igv_valor = 0.0

        c.setFont("Helvetica-Bold", 9)
        line_height = 5 * mm
        current_y = footer_y

        c.drawRightString(right_align_x, current_y, f"SUBTOTAL ITEMS: S/ {suma_importes:.2f}")
        current_y -= line_height

        c.drawRightString(right_align_x, current_y, f"DESCUENTO: - S/ {discount:.2f}")
        current_y -= line_height

        c.setLineWidth(0.5)
        c.line(right_align_x - 40 * mm, current_y + 1 * mm, right_align_x, current_y + 1 * mm)
        current_y -= 2 * mm

        if include_igv_flag:
            c.drawRightString(right_align_x, current_y, f"OP. GRAVADA: S/ {base_imponible:.2f}")
            current_y -= line_height
            c.drawRightString(right_align_x, current_y, f"IGV (18%): S/ {igv_valor:.2f}")
            current_y -= line_height
        else:
            c.drawRightString(right_align_x, current_y, f"SUBTOTAL: S/ {base_imponible:.2f}")
            current_y -= line_height

        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(right_align_x, current_y, f"IMPORTE TOTAL: S/ {total:.2f}")

        c.setFont("Helvetica", 8)
        monto_letras = self.convertir_monto_a_letras(total)
        c.drawString(margin_left, footer_y - 4 * line_height, f"SON: {monto_letras}")

        if is_boletin and is_adelanto and estimated_total > 0:
            c.setFont("Helvetica-Bold", 9)
            saldo_pendiente = max(0.0, round(estimated_total - advance_amount, 2))
            c.setFillColor(HexColor("#B3261E"))
            c.drawRightString(right_align_x, current_y - 2 * line_height, f"PAGO RESTANTE: S/ {saldo_pendiente:.2f}")
            c.setFillColor(colors.black)

        if is_proforma or is_boletin:
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(colors.red)
            if is_boletin:
                legend = "RECIBO DE ADELANTO - SIN VALOR FISCAL" if is_adelanto else "BOLETIN INTERNO - SIN VALOR FISCAL"
                c.drawString(margin_left, footer_y - 4 * line_height - 3 * mm, legend)
            else:
                c.drawString(margin_left, footer_y - 4 * line_height - 3 * mm, "PROFORMA - SIN VALOR FISCAL")
            c.setFillColor(colors.black)

        if is_boletin and is_adelanto:
            c.setFont("Helvetica-Bold", 9)
            adelanto_label_y = footer_y - 4 * line_height - 8 * mm
            saldo_base = estimated_total if estimated_total > 0 else subtotal
            saldo_pendiente = max(0.0, round(saldo_base - advance_amount, 2))
            c.drawString(margin_left, adelanto_label_y, f"Adelanto recibido: S/ {advance_amount:.2f}")
            c.drawString(margin_left, adelanto_label_y - 5 * mm, f"Saldo pendiente: S/ {saldo_pendiente:.2f}")

        if serial_seguridad:
            c.setFont("Helvetica", 7)
            c.drawString(margin_left, footer_y - 4 * line_height - 5 * mm, f"Hash: {serial_seguridad}")

        qr_x = 175 * mm
        qr_size = 25 * mm
        qr_y = current_y - qr_size - 5 * mm

        if qrcode:
            try:
                resumen_items = ", ".join([f"{i[2]} x{int(i[4])}" for i in items])
            except Exception:
                resumen_items = "VARIOS"

            resumen_safe = resumen_items.replace("|", "-")
            if len(resumen_safe) > 50:
                resumen_safe = resumen_safe[:47] + "..."

            qr_data = (
                f"PABLITOPOS|{series}|{number}|{total:.2f}|{dt_str}|{client_doc}|{resumen_safe}|{serial_seguridad or ''}"
            )
            qr_code = qrcode.QRCode(box_size=2, border=0)
            qr_code.add_data(qr_data)
            qr_code.make(fit=True)
            img_qr = qr_code.make_image(fill_color="black", back_color="white")
            qr_filename = os.path.join(output_dir, "temp_qr.png")
            with open(qr_filename, "wb") as qr_file:
                img_qr.save(qr_file)
            c.drawImage(qr_filename, qr_x, qr_y, width=qr_size, height=qr_size)
            c.setLineWidth(0.5)
            c.setStrokeColor(colors.black)
            c.rect(qr_x - 2 * mm, qr_y - 2 * mm, qr_size + 4 * mm, qr_size + 4 * mm)
            try:
                os.remove(qr_filename)
            except OSError:
                pass

        if serial_seguridad:
            c.setFont("Helvetica", 6)
            c.drawCentredString(qr_x + qr_size / 2, qr_y - 5 * mm, f"Codigo Verificador: {serial_seguridad}")

        bottom_text_y = 15 * mm
        c.setFont("Helvetica", 7)
        c.drawString(
            margin_left,
            bottom_text_y + 4 * mm,
            "Representación impresa de nota de venta interna. Documento no válido para efectos tributarios hasta su validación final.",
        )

        c.setStrokeColor(HexColor("#B2EBF2"))
        c.setLineWidth(1.5)
        c.line(margin_left, bottom_text_y + 2 * mm, width - margin_right, bottom_text_y + 2 * mm)

        client_name_footer = client_name or "Cliente"
        footer_template = company.get("footer_message") or "Gracias por su compra, vuelva pronto {CLIENTE}"
        footer_rendered = (
            footer_template
            .replace("{CLIENTE}", client_name_footer)
            .replace("{cliente}", client_name_footer)
            .replace("{EMPRESA}", company.get("name", ""))
            .replace("{empresa}", company.get("name", ""))
        )
        if not footer_rendered.strip():
            footer_rendered = f"Gracias por su compra, vuelva pronto {client_name_footer}"

        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.black)
        c.drawCentredString(width / 2, bottom_text_y - 3 * mm, footer_rendered)

        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, bottom_text_y - 7 * mm, f"Esperamos verte pronto {client_name_footer}")

        if pdf_path_db:
            c.setFont("Helvetica", 6)
            c.drawString(margin_left, bottom_text_y - 12 * mm, f"Ruta almacenada: {pdf_path_db}")

        c.save()
        try:
            self.sale_repo.update_pdf_path(sale_id, pdf_path)
        except Exception:
            # No bloquear por fallo de persistencia de ruta
            pass
        return pdf_path

    def generate_fiado_pdf(
        self,
        fiado: dict[str, Any],
        items: list[Any],
        client: dict | None = None,
        output_dir: str | None = "temp",
        company_profile: dict | None = None,
    ) -> str:
        if canvas is None:
            raise RuntimeError("La librería reportlab no está instalada.")
        if not fiado:
            raise ValueError("Fiado no encontrado.")

        transient = output_dir is None or str(output_dir).lower() == "temp"
        if transient:
            base_temp_root = PDF_DIR if os.path.isdir(PDF_DIR) else tempfile.gettempdir()
            output_dir = tempfile.mkdtemp(prefix="pablito_fiado_", dir=base_temp_root)
            self._transient_dirs.append(output_dir)
        else:
            os.makedirs(output_dir, exist_ok=True)

        company = company_profile or self.company_service.get_profile(fiado.get("company_id", 1))

        code = str(fiado.get("code") or f"FIADO-{fiado.get('id', '')}")
        dt_str = fiado.get("created_at") or ""
        try:
            dt_obj = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S") if dt_str else datetime.now()
        except Exception:
            dt_obj = datetime.now()
        date_str = dt_obj.strftime("%d/%m/%Y")
        filename = f"FIADO_{code}_{dt_obj.strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(output_dir, filename)

        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4

        margin_left = 10 * mm
        margin_right = 10 * mm

        logo_x = 10 * mm
        logo_y = height - 40 * mm
        logo_w = 50 * mm
        logo_h = 30 * mm

        if company.get("logo_path") and os.path.exists(company["logo_path"]):
            try:
                c.drawImage(
                    company["logo_path"],
                    logo_x,
                    logo_y,
                    width=logo_w,
                    height=logo_h,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass

        data_x = 65 * mm
        data_w = 70 * mm
        data_y_top = height - 15 * mm

        styles = getSampleStyleSheet()
        style_name = ParagraphStyle(
            "FiadoCompanyName",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            alignment=TA_CENTER,
            leading=16,
        )
        style_details = ParagraphStyle(
            "FiadoCompanyDetails",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            alignment=TA_CENTER,
            leading=8,
        )

        comp_name = (company.get("name") or "EMPRESA").upper()
        details_list: List[str] = []
        address = company.get("address") if company else ""
        if address:
            details_list.append(str(address))
        website = company.get("website") if company else ""
        if website:
            details_list.append(str(website))
        email = company.get("email") if company else ""
        if email:
            details_list.append(str(email))
        phone = company.get("phone") if company else ""
        if phone:
            details_list.append(f"Tlf: {phone}")
        details_text = "<br/>".join(details_list)

        p_name = Paragraph(comp_name, style_name)
        p_details = Paragraph(details_text, style_details)

        w_name, h_name = p_name.wrap(data_w, 50 * mm)
        p_name.drawOn(c, data_x, data_y_top - h_name)

        w_det, h_det = p_details.wrap(data_w, 60 * mm)
        p_details.drawOn(c, data_x, data_y_top - h_name - h_det - 2 * mm)

        ruc_x = 140 * mm
        ruc_w = 60 * mm
        ruc_h = 30 * mm
        ruc_y = height - 40 * mm

        c.setLineWidth(1)
        c.setStrokeColor(colors.black)
        c.rect(ruc_x, ruc_y, ruc_w, ruc_h)

        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(ruc_x + ruc_w / 2, ruc_y + ruc_h - 5 * mm, f"RUC: {company.get('ruc', '')}")
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(ruc_x + ruc_w / 2, ruc_y + ruc_h / 2, "VALE DE FIADO")
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(ruc_x + ruc_w / 2, ruc_y + 5 * mm, code)

        client_entry = client or {}
        client_name = client_entry.get("full_name") or client_entry.get("name") or "CLIENTE VARIOS"
        client_address = client_entry.get("address", "")
        client_doc = client_entry.get("dni") or client_entry.get("ruc") or ""

        client_y = ruc_y - 12 * mm
        c.setFont("Helvetica", 9)
        c.drawString(margin_left, client_y, f"CLIENTE: {client_name}")
        c.drawString(margin_left, client_y - 5 * mm, f"DIRECCION: {client_address}")
        c.drawString(margin_left, client_y - 10 * mm, f"DNI/RUC: {client_doc}")

        c.drawRightString(width - margin_right, client_y, f"FECHA: {date_str}")
        c.drawRightString(width - margin_right, client_y - 5 * mm, "MONEDA: SOLES")

        col_widths = [15 * mm, 20 * mm, 25 * mm, 85 * mm, 25 * mm, 25 * mm]
        table_y = client_y - 15 * mm

        data_table: List[List[Any]] = [["CANT", "U.M.", "BLOQUE", "DESCRIPCION", "P.U.", "IMPORTE"]]
        paid_rows: List[int] = []

        style_desc = ParagraphStyle("CellDescFiado", parent=styles["Normal"], fontSize=8, leading=9)

        for item in items:
            item_map = item if isinstance(item, dict) else {}
            qty = float(item_map.get("quantity", 0.0) or 0.0)
            unit = str(item_map.get("unit", "") or "")
            block = str(item_map.get("block", "") or "-")
            desc_text = str(item_map.get("description", "") or "")
            unit_price = float(item_map.get("unit_price", 0.0) or 0.0)
            importe = float(item_map.get("subtotal", unit_price * (qty or 1)) or (unit_price * (qty or 1)))
            status = (item_map.get("status") or "").lower()

            row_index = len(data_table)
            if status == "pagado":
                paid_rows.append(row_index)

            desc_para = Paragraph(f"<strike>{desc_text}</strike>" if status == "pagado" else desc_text, style_desc)
            data_table.append(
                [
                    f"{qty:.2f}",
                    unit,
                    block,
                    desc_para,
                    f"{unit_price:.2f}",
                    f"{importe:.2f}",
                ]
            )

        table = Table(data_table, colWidths=col_widths)
        style_rows = [
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (3, 0), (3, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#B2EBF2")),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
        ]

        for row in paid_rows:
            style_rows.append(("BACKGROUND", (0, row), (-1, row), HexColor("#E8F5E9")))
            style_rows.append(("TEXTCOLOR", (0, row), (-1, row), HexColor("#1B5E20")))

        table.setStyle(TableStyle(style_rows))

        table_width, table_height = table.wrap(width - 20 * mm, height)
        table.drawOn(c, margin_left, table_y - table_height)

        footer_y = table_y - table_height - 8 * mm
        right_align_x = margin_left + sum(col_widths)

        total_bruto = float(fiado.get("total_bruto", 0.0) or 0.0)
        total_pagado = float(fiado.get("total_pagado", 0.0) or 0.0)
        total_pendiente = float(fiado.get("total_pendiente", 0.0) or 0.0)

        c.setFont("Helvetica-Bold", 9)
        line_height = 5 * mm
        current_y = footer_y

        c.drawRightString(right_align_x, current_y, f"TOTAL FIADO: S/ {total_bruto:.2f}")
        current_y -= line_height
        c.drawRightString(right_align_x, current_y, f"PAGADO: S/ {total_pagado:.2f}")
        current_y -= line_height
        c.drawRightString(right_align_x, current_y, f"PENDIENTE: S/ {total_pendiente:.2f}")

        c.setFont("Helvetica", 8)
        monto_letras = self.convertir_monto_a_letras(total_bruto)
        c.drawString(margin_left, footer_y - 4 * line_height, f"SON: {monto_letras}")

        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(colors.red)
        c.drawString(margin_left, footer_y - 4 * line_height - 3 * mm, "VALE INTERNO - SIN VALOR FISCAL")
        c.setFillColor(colors.black)

        qr_x = 175 * mm
        qr_size = 25 * mm
        qr_y = current_y - qr_size - 5 * mm

        if qrcode:
            try:
                resumen_items = ", ".join([f"{item_map.get('description', '')} x{int(item_map.get('quantity', 0) or 0)}" for item_map in items])
            except Exception:
                resumen_items = "VARIOS"

            resumen_safe = resumen_items.replace("|", "-")
            if len(resumen_safe) > 50:
                resumen_safe = resumen_safe[:47] + "..."

            qr_data = f"FIADO|{code}|{total_bruto:.2f}|{dt_obj.strftime('%Y-%m-%d')}|{client_doc}|{fiado.get('id', '')}"
            qr_code = qrcode.QRCode(box_size=2, border=0)
            qr_code.add_data(qr_data)
            qr_code.make(fit=True)
            img_qr = qr_code.make_image(fill_color="black", back_color="white")
            qr_filename = os.path.join(output_dir, "temp_qr.png")
            with open(qr_filename, "wb") as qr_file:
                img_qr.save(qr_file)
            c.drawImage(qr_filename, qr_x, qr_y, width=qr_size, height=qr_size)
            c.setLineWidth(0.5)
            c.setStrokeColor(colors.black)
            c.rect(qr_x - 2 * mm, qr_y - 2 * mm, qr_size + 4 * mm, qr_size + 4 * mm)
            try:
                os.remove(qr_filename)
            except OSError:
                pass

        bottom_text_y = 15 * mm
        c.setStrokeColor(HexColor("#B2EBF2"))
        c.setLineWidth(1.5)
        c.line(margin_left, bottom_text_y + 2 * mm, width - margin_right, bottom_text_y + 2 * mm)

        client_name_footer = client_name or "Cliente"
        footer_template = company.get("footer_message") or "Gracias por su compra, vuelva pronto {CLIENTE}"
        footer_rendered = (
            footer_template
            .replace("{CLIENTE}", client_name_footer)
            .replace("{cliente}", client_name_footer)
            .replace("{EMPRESA}", company.get("name", ""))
            .replace("{empresa}", company.get("name", ""))
        )
        if not footer_rendered.strip():
            footer_rendered = f"Gracias por su compra, vuelva pronto {client_name_footer}"

        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.black)
        c.drawCentredString(width / 2, bottom_text_y - 3 * mm, footer_rendered)

        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, bottom_text_y - 7 * mm, f"Esperamos verte pronto {client_name_footer}")

        pdf_path_db = fiado.get("pdf_path")
        if pdf_path_db:
            c.setFont("Helvetica", 6)
            c.drawString(margin_left, bottom_text_y - 12 * mm, f"Ruta almacenada: {pdf_path_db}")

        c.save()
        return pdf_path
