"""Reusable text templates for outbound communications."""

from __future__ import annotations

from datetime import datetime
from typing import Optional


def build_whatsapp_message(
    company_name: str,
    client_name: Optional[str],
    sale_date: Optional[datetime],
    *,
    resend: bool = False,
    is_adelanto: bool = False,
    advance_amount: float | None = None,
    estimated_total: float | None = None,
) -> str:
    """Create a WhatsApp message for delivering a sales receipt."""
    company = (company_name or "Nuestra Empresa").strip() or "Nuestra Empresa"
    client = (client_name or "Cliente").strip() or "Cliente"
    date_str = (sale_date or datetime.now()).strftime("%d/%m/%Y")

    if is_adelanto:
        adelanto = max(0.0, float(advance_amount or 0))
        estimado = max(0.0, float(estimated_total or 0))
        saldo = max(estimado - adelanto, 0.0)
        if resend:
            return (
                f"Hola {client}, te reenviamos el recibo de adelanto del {date_str} de {company}. "
                f"Adelanto: S/ {adelanto:.2f}. Saldo pendiente: S/ {saldo:.2f}. "
                "Podras pagarlo al recoger tu pedido. Gracias!"
            )
        return (
            f"Hola {client}, registramos tu adelanto el {date_str} en {company}. "
            f"Adelanto: S/ {adelanto:.2f}. Saldo pendiente: S/ {saldo:.2f}. "
            "Podras pagarlo al recoger tu pedido. Gracias por tu confianza!"
        )

    if resend:
        return (
            f"Hola {client}, te reenviamos el comprobante de venta digital correspondiente al {date_str} de {company}. "
            "Gracias por tu preferencia!"
        )

    return (
        f"Hola {client}, le adjunto el comprobante de venta digital por su compra realizada el dia {date_str} en {company}. "
        "Que tenga buen dia!"
    )
