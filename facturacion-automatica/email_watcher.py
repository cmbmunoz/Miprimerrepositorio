"""Monitor Microsoft 365 inbox for purchase orders via Graph API."""

import base64
import os
import logging

import requests

from config import USER_EMAIL, OC_SUBJECT_KEYWORDS, OUTPUT_DIR

GRAPH = "https://graph.microsoft.com/v1.0"
log = logging.getLogger(__name__)


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get_unread_oc_emails(token: str) -> list[dict]:
    url = f"{GRAPH}/users/{USER_EMAIL}/messages"
    params = {
        "$filter": "isRead eq false and hasAttachments eq true",
        "$select": "id,subject,from,receivedDateTime,hasAttachments",
        "$orderby": "receivedDateTime asc",
        "$top": 50,
    }
    r = requests.get(url, headers=_headers(token), params=params, timeout=30)
    r.raise_for_status()

    messages = r.json().get("value", [])
    return [
        m for m in messages
        if any(kw.lower() in m.get("subject", "").lower() for kw in OC_SUBJECT_KEYWORDS)
    ]


def get_pdf_attachments(token: str, message_id: str) -> list[dict]:
    """Return list of {name, content} for each PDF attachment."""
    url = f"{GRAPH}/users/{USER_EMAIL}/messages/{message_id}/attachments"
    r = requests.get(url, headers=_headers(token), timeout=30)
    r.raise_for_status()

    pdfs = []
    for att in r.json().get("value", []):
        is_pdf = (
            "pdf" in att.get("contentType", "").lower()
            or att.get("name", "").lower().endswith(".pdf")
        )
        if is_pdf and att.get("contentBytes"):
            pdfs.append({
                "name": att["name"],
                "content": base64.b64decode(att["contentBytes"]),
            })
    return pdfs


def mark_as_read(token: str, message_id: str) -> None:
    url = f"{GRAPH}/users/{USER_EMAIL}/messages/{message_id}"
    requests.patch(url, headers=_headers(token), json={"isRead": True}, timeout=30)


def save_pdf(content: bytes, filename: str) -> str:
    out_dir = os.path.join(OUTPUT_DIR, "pdfs")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, filename)
    with open(path, "wb") as f:
        f.write(content)
    return path
