"""
Tracks processed purchase orders to avoid duplicate processing.
State is persisted in output/estado.json.
"""

import json
import logging
import os
from datetime import datetime

from config import OUTPUT_DIR

_STATE_FILE = os.path.join(OUTPUT_DIR, "estado.json")
log = logging.getLogger(__name__)


def _load() -> dict:
    if os.path.exists(_STATE_FILE):
        with open(_STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"ocs": {}}


def _save(state: dict) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def already_processed(numero_oc: str) -> bool:
    if not numero_oc:
        return False
    return numero_oc in _load()["ocs"]


def register_prefactura(numero_oc: str, email_id: str, pdf_path: str, prefactura_path: str, json_path: str) -> None:
    state = _load()
    state["ocs"][numero_oc] = {
        "numero_oc": numero_oc,
        "email_id": email_id,
        "pdf": pdf_path,
        "prefactura_xlsx": prefactura_path,
        "prefactura_json": json_path,
        "fecha_prefactura": datetime.now().isoformat(),
        "estado": "prefacturada",
        "factura_xlsx": None,
        "fecha_factura": None,
        "numero_factura": None,
    }
    _save(state)
    log.info("Estado registrado: OC %s → prefacturada", numero_oc)


def register_factura(numero_oc: str, factura_path: str, numero_factura: str) -> None:
    state = _load()
    if numero_oc not in state["ocs"]:
        state["ocs"][numero_oc] = {}
    state["ocs"][numero_oc].update({
        "factura_xlsx": factura_path,
        "fecha_factura": datetime.now().isoformat(),
        "numero_factura": numero_factura,
        "estado": "facturada",
    })
    _save(state)
    log.info("Estado actualizado: OC %s → facturada (%s)", numero_oc, numero_factura)


def list_pending() -> list[dict]:
    """Return OCs in 'prefacturada' state (awaiting approval)."""
    return [
        entry for entry in _load()["ocs"].values()
        if entry.get("estado") == "prefacturada"
    ]


def next_invoice_number() -> str:
    state = _load()
    facturas = [
        entry.get("numero_factura", "")
        for entry in state["ocs"].values()
        if entry.get("numero_factura")
    ]
    # Extract numeric suffix from strings like "F-0001"
    nums = []
    for f in facturas:
        try:
            nums.append(int(f.split("-")[-1]))
        except ValueError:
            pass
    n = max(nums) + 1 if nums else 1
    return f"F-{n:04d}"
