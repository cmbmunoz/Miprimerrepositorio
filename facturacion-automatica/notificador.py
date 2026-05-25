"""
Send email notifications via Microsoft Graph API.
Used to notify when a pre-invoice is generated.
"""

import base64
import logging
import os

import requests

from config import USER_EMAIL

GRAPH = "https://graph.microsoft.com/v1.0"
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

    url = f"{GRAPH}/users/{USER_EMAIL}/sendMail"
    r = requests.post(url, headers=_headers(token), json=payload, timeout=30)
    if r.status_code == 202:
        log.info("Notificación enviada a %s", destinatario)
        return True
    else:
        log.warning("No se pudo enviar notificación: %s %s", r.status_code, r.text[:200])
        return False
