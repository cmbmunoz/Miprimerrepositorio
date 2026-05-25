"""Extract structured purchase-order data from a PDF using pdfplumber + Claude."""

import json
import logging

import pdfplumber
import anthropic

from config import ANTHROPIC_API_KEY

log = logging.getLogger(__name__)

_client = None


def _anthropic():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


SYSTEM_PROMPT = """\
Sos un asistente especializado en leer órdenes de compra de empresas argentinas.
Dado el texto de un PDF, extraé los datos y devolvé ÚNICAMENTE un objeto JSON válido \
con la siguiente estructura. No agregues explicaciones ni bloques de código markdown.

{
  "numero_oc": "string | null",
  "fecha": "YYYY-MM-DD | null",
  "cliente": {
    "nombre": "string",
    "cuit": "XX-XXXXXXXX-X | null",
    "direccion": "string | null"
  },
  "proveedor": {
    "nombre": "string | null",
    "cuit": "XX-XXXXXXXX-X | null"
  },
  "items": [
    {
      "descripcion": "string",
      "cantidad": 0,
      "precio_unitario": 0.0,
      "subtotal": 0.0
    }
  ],
  "subtotal": 0.0,
  "iva_porcentaje": 21,
  "iva_monto": 0.0,
  "total": 0.0,
  "moneda": "ARS | USD",
  "notas": "string | null"
}
"""


def _extract_text(pdf_path: str) -> str:
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            # Also try extracting tables for structured POs
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    page_text += " | ".join(str(c or "") for c in row) + "\n"
            text += page_text + "\n"
    return text.strip()


def _parse_with_claude(text: str) -> dict:
    response = _anthropic().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Texto del PDF:\n\n{text}"}],
    )
    raw = response.content[0].text.strip()

    # Strip markdown fences if the model adds them anyway
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    return json.loads(raw)


def extract_oc_data(pdf_path: str) -> dict:
    text = _extract_text(pdf_path)
    if not text:
        raise ValueError(f"No se pudo extraer texto del PDF: {pdf_path}")
    log.debug("Texto extraído (%d chars), enviando a Claude…", len(text))
    data = _parse_with_claude(text)
    return data
