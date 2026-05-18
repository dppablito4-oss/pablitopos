"""Email templates and helpers for outbound communications."""

from __future__ import annotations

import html
from urllib.parse import quote

from utils import ensure_country_prefix, normalize_phone_number


def generate_email_html(
    client_name: str,
    sale_number: str,
    total: str,
    date_str: str,
    company_data: dict | None,
    *,
    is_resend: bool = False,
    is_adelanto: bool = False,
    advance_total: str | None = None,
    estimated_total: str | None = None,
    remaining_total: str | None = None,
) -> str:
    """Build the HTML body used when emailing a receipt to the customer."""
    company_data = company_data or {}
    company_name_raw = (company_data.get("name") or "Tu Empresa").strip() or "Tu Empresa"
    company_name = html.escape(company_name_raw)
    company_ruc = html.escape((company_data.get("ruc") or "").strip())
    company_phone = html.escape((company_data.get("phone") or "").strip())
    company_email = html.escape((company_data.get("email") or "").strip())
    safe_client = html.escape(client_name or "Cliente")
    safe_sale_number = html.escape(sale_number or "")
    safe_total = html.escape(total or "0.00")
    safe_date = html.escape(date_str or "")

    logo_block = (
        '<img src="cid:company_logo" alt="Logo" style="max-width:180px;height:auto;display:block;margin:0 auto 16px auto;">'
        if company_data.get("logo_path")
        else ""
    )

    ruc_line = (
        f"<p style=\"color:#8d8d8d;font-size:13px;margin:4px 0 0 0;\">RUC: {company_ruc}</p>"
        if company_ruc
        else ""
    )
    phone_line = f"<span style=\"margin-right:12px;\">Tel: {company_phone}</span>" if company_phone else ""
    email_line = f"<span>Email: {company_email}</span>" if company_email else ""

    contact_block = ""
    if phone_line or email_line:
        contact_block = f"<p style=\"color:#cccccc;font-size:12px;margin:12px 0 0 0;\">{phone_line}{email_line}</p>"

    headline = (
        f"Reenvío de su comprobante de pago del dia {safe_date}"
        if is_resend
        else f"Tu comprobante de pago del dia {safe_date} está listo"
    )

    intro_text = (
        "Atendiendo a tu solicitud, te reenviamos copia de tu documento en formato PDF. Para cualquier consulta sobre su comprobante, no dude en responder a este correo o escribirnos por WhatsApp usando el siguiente enlace. Con gusto le atenderemos."
        if is_resend
        else "Adjunto encontrarás tu comprobante de pago electrónico en formato PDF. Para cualquier consulta sobre su comprobante, no dude en responder a este correo o escribirnos por WhatsApp usando el siguiente enlace. Con gusto le atenderemos."
    )

    despedida_text = "Quedamos a tu disposición." if is_resend else "Gracias por tu preferencia."

    raw_phone = (company_data.get("phone") or "").strip()
    phone_digits = ensure_country_prefix(normalize_phone_number(raw_phone))
    whatsapp_btn_html = ""
    if phone_digits:
        message_text = f"Hola equipo {company_name_raw}, necesito información sobre mi comprobante..."
        encoded_message = quote(message_text)
        whatsapp_url = f"https://wa.me/{phone_digits}?text={encoded_message}"
        whatsapp_btn_html = (
            f"<div style=\"text-align:center;margin:24px 0;\">"
            f"<a href=\"{whatsapp_url}\" style=\"display:inline-block;background-color:#25D366;color:#ffffff;"
            "padding:12px 28px;border-radius:24px;text-decoration:none;font-weight:600;font-size:15px;"
            "letter-spacing:0.3px;\">Contactar por WhatsApp</a></div>"
        )

    if is_adelanto:
        adelanto_html = html.escape(advance_total or safe_total)
        estimado_html = html.escape(estimated_total or "0.00")
        saldo_html = html.escape(remaining_total or "0.00")
        detail_rows = (
            "<tr><td style=\"padding:12px 16px;font-size:14px;color:#E3F2FD;\">Comprobante</td><td style=\"padding:12px 16px;font-size:16px;color:#FFFFFF;font-weight:600;text-align:right;\">"
            f"{safe_sale_number}</td></tr>"
            "<tr><td style=\"padding:12px 16px;font-size:14px;color:#E3F2FD;border-top:1px solid rgba(255,255,255,0.2);\">Fecha</td><td style=\"padding:12px 16px;font-size:15px;color:#FFFFFF;border-top:1px solid rgba(255,255,255,0.2);text-align:right;\">"
            f"{safe_date}</td></tr>"
            "<tr><td style=\"padding:12px 16px;font-size:14px;color:#E3F2FD;border-top:1px solid rgba(255,255,255,0.2);\">Adelanto</td><td style=\"padding:12px 16px;font-size:18px;color:#00E676;font-weight:700;border-top:1px solid rgba(255,255,255,0.2);text-align:right;\">S/ "
            f"{adelanto_html}</td></tr>"
            "<tr><td style=\"padding:12px 16px;font-size:14px;color:#E3F2FD;border-top:1px solid rgba(255,255,255,0.2);\">Total estimado</td><td style=\"padding:12px 16px;font-size:15px;color:#FFFFFF;border-top:1px solid rgba(255,255,255,0.2);text-align:right;\">S/ "
            f"{estimado_html}</td></tr>"
            "<tr><td style=\"padding:12px 16px;font-size:14px;color:#E3F2FD;border-top:1px solid rgba(255,255,255,0.2);\">Saldo pendiente</td><td style=\"padding:12px 16px;font-size:16px;color:#ffb74d;font-weight:700;border-top:1px solid rgba(255,255,255,0.2);text-align:right;\">S/ "
            f"{saldo_html}</td></tr>"
        )
    else:
        detail_rows = (
            "<tr><td style=\"padding:12px 16px;font-size:14px;color:#E3F2FD;\">Comprobante</td><td style=\"padding:12px 16px;font-size:16px;color:#FFFFFF;font-weight:600;text-align:right;\">"
            f"{safe_sale_number}</td></tr>"
            "<tr><td style=\"padding:12px 16px;font-size:14px;color:#E3F2FD;border-top:1px solid rgba(255,255,255,0.2);\">Fecha</td><td style=\"padding:12px 16px;font-size:15px;color:#FFFFFF;border-top:1px solid rgba(255,255,255,0.2);text-align:right;\">"
            f"{safe_date}</td></tr>"
            "<tr><td style=\"padding:12px 16px;font-size:14px;color:#E3F2FD;border-top:1px solid rgba(255,255,255,0.2);\">Total</td><td style=\"padding:12px 16px;font-size:18px;color:#00E676;font-weight:700;border-top:1px solid rgba(255,255,255,0.2);text-align:right;\">S/ "
            f"{safe_total}</td></tr>"
        )

    return f"""<!DOCTYPE html>
<html lang=\"es\">
<body style=\"margin:0;padding:0;background-color:#f4f4f4;font-family:'Segoe UI',Tahoma,Arial,sans-serif;\">
    <table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" style=\"background-color:#f4f4f4;\">
        <tr>
            <td align=\"center\" style=\"padding:32px 12px;\">
                <table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" style=\"max-width:600px;background-color:#1a1a1a;border-radius:16px;overflow:hidden;box-shadow:0 18px 45px rgba(0,0,0,0.35);\">
                    <tr>
                        <td style=\"padding:36px 40px 28px 40px;text-align:center;\">{logo_block}
                            <h1 style=\"color:#ffffff;font-size:24px;margin:0;letter-spacing:0.5px;font-weight:600;\">{company_name}</h1>
                            {ruc_line}
                            {contact_block}
                        </td>
                    </tr>
                    <tr>
                        <td style=\"padding:0 40px 24px 40px;\">
                            <div style=\"background:linear-gradient(135deg,#2979FF,#00B0FF);border-radius:14px;padding:28px 24px;text-align:center;\">
                                <p style=\"margin:0;font-size:17px;color:#E3F2FD;letter-spacing:0.4px;\">Hola, <span style=\"color:#ffffff;font-weight:600;\">{safe_client}</span> 👋</p>
                                <h2 style=\"margin:12px 0 0 0;font-size:26px;color:#ffffff;font-weight:700;letter-spacing:1px;\">{headline}</h2>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td style=\"padding:0 40px 16px 40px;\">
                            <table width=\"100%\" cellpadding=\"0\" cellspacing=\"0\" border=\"0\" style=\"background-color:rgba(41,121,255,0.14);border-radius:12px;\">
                                {detail_rows}
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style=\"padding:0 40px 28px 40px;\">
                            <p style=\"color:#d8d8d8;font-size:15px;line-height:1.7;margin:0 0 18px 0;\">{intro_text}</p>
                            {whatsapp_btn_html}
                            <p style=\"color:#a0a0a0;font-size:13px;margin:0;\">{despedida_text}<br>El equipo de <span style=\"color:#ffffff;\">{company_name}</span></p>
                        </td>
                    </tr>
                    <tr>
                        <td style=\"padding:24px 40px 36px 40px;background-color:#111111;\">
                            <p style=\"color:#666666;font-size:11px;margin:0 0 8px 0;\">Representación impresa de nota de venta interna. Documento no válido para efectos tributarios hasta su validación final.</p>
                            <p style=\"color:#4f4f4f;font-size:11px;margin:0;\">&copy; {company_name}. Todos los derechos reservados.</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
