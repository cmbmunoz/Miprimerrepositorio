"""
Send email notifications via Microsoft Graph API.
Used to notify when a pre-invoice is generated (OC flow and HR monthly flow).
"""

import base64
import calendar
import logging
import os

import requests

GRAPH = "https://graph.microsoft.com/v1.0"
MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
log = logging.getLogger(__name__)


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def enviar_prefactura(token: str, destinatario: str, numero_oc: str, prefactura_path: str) -> bool:
    """Send the pre-invoice Excel as an email attachment."""
    filename = os.path.basename(prefactura_path)
    with open(prefactura_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "message": {
            "subject": f"Pre-factura generada — OC {numero_oc}",
            "body": {
                "contentType": "HTML",
                "content": f"""
                <p>Se procesó automáticamente la Orden de Compra <strong>{numero_oc}</strong>.</p>
                <p>Adjunto encontrás la pre-factura para revisar y aprobar.</p>
                <p>Para emitir la factura final, ejecutá:</p>
                <pre>python aprobar.py</pre>
                <hr>
                <p style="color:#888;font-size:12px;">Sistema de pre-facturación automática</p>
                """,
            },
            "toRecipients": [
                {"emailAddress": {"address": destinatario}}
            ],
            "attachments": [
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": filename,
                    "contentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "contentBytes": content_b64,
                }
            ],
        },
        "saveToSentItems": True,
    }

    from config import USER_EMAIL
    url = f"{GRAPH}/users/{USER_EMAIL}/sendMail"
    r = requests.post(url, headers=_headers(token), json=payload, timeout=30)
    if r.status_code == 202:
        log.info("Notificación enviada a %s", destinatario)
        return True
    else:
        log.warning("No se pudo enviar notificación: %s %s", r.status_code, r.text[:200])
        return False


def enviar_prefactura_rrhh(
    token: str,
    proyecto,
    personas: list,
    mes: int,
    anio: int,
    pdf_path: str,
    numero: str,
    remitente: str,
) -> bool:
    """Send monthly HR pre-invoice PDF to the project client."""
    periodo   = f"{MESES[mes].capitalize()} {anio}"
    filename  = os.path.basename(pdf_path)
    n_personas = len(personas)

    with open(pdf_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()

    # Build a plain summary table for the email body
    filas = "".join(
        f"<tr><td>{p.id}</td><td>{p.nombre}</td>"
        f"<td style='text-align:right'>{p.moneda} {p.tarifa_mensual:,.2f}</td></tr>"
        for p in personas
    )
    total_str = " / ".join(
        f"{m} {sum(p.tarifa_mensual for p in personas if p.moneda == m):,.2f}"
        for m in {p.moneda for p in personas}
    )

    body_html = f"""
    <p>Estimado/a,</p>
    <p>Adjunto la pre-factura <strong>{numero}</strong> correspondiente al período
    <strong>{periodo}</strong> para el proyecto <strong>{proyecto.nombre}</strong>.</p>

    <table border="1" cellpadding="6" cellspacing="0"
           style="border-collapse:collapse;font-family:Calibri,sans-serif;font-size:13px">
      <thead style="background:#2E75B6;color:white">
        <tr><th>ID</th><th>Nombre</th><th>Tarifa mensual</th></tr>
      </thead>
      <tbody>{filas}</tbody>
      <tfoot style="background:#1F3864;color:white;font-weight:bold">
        <tr><td colspan="2">TOTAL ({n_personas} persona{'s' if n_personas != 1 else ''})</td>
            <td style='text-align:right'>{total_str}</td></tr>
      </tfoot>
    </table>

    <p>Por favor revisá el PDF adjunto y confirmá para proceder con la facturación.</p>
    <hr>
    <p style="color:#888;font-size:11px">
      Enviado automáticamente · Sistema de Pre-Facturación RRHH
    </p>
    """

    payload = {
        "message": {
            "subject": f"Pre-factura RRHH — {proyecto.nombre} — {periodo}",
            "body": {"contentType": "HTML", "content": body_html},
            "toRecipients": [{"emailAddress": {"address": proyecto.cliente_email}}],
            "attachments": [{
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": filename,
                "contentType": "application/pdf",
                "contentBytes": content_b64,
            }],
        },
        "saveToSentItems": True,
    }

    url = f"{GRAPH}/users/{remitente}/sendMail"
    r = requests.post(url, headers=_headers(token), json=payload, timeout=30)
    if r.status_code == 202:
        log.info("Email RRHH enviado a %s (%s)", proyecto.cliente_email, periodo)
        return True
    log.warning("No se pudo enviar email RRHH: %s %s", r.status_code, r.text[:200])
    return False
