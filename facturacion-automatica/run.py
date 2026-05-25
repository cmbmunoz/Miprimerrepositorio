"""
Main orchestrator — two independent loops:

  1. OC email monitor: polls M365 inbox every POLL_INTERVAL_SECONDS,
     detects purchase-order PDFs, generates pre-invoices (Excel).

  2. Monthly HR billing: at 08:00 on the 2nd of each month generates
     one PDF pre-invoice per project from HR data and emails each client.

Usage:
    python run.py            # continuous mode
    python run.py --once     # one pass only (email check + day-2 check) then exit
"""

import argparse
import logging
import os
import sys
import time
from datetime import date

import schedule

from config import OUTPUT_DIR, POLL_INTERVAL_SECONDS, USER_EMAIL
from auth import get_token
from hr.db import init_db
from email_watcher import (
    get_unread_oc_emails,
    get_pdf_attachments,
    mark_as_read,
    save_pdf,
)
from pdf_extractor import extract_oc_data
from prefactura import generate_prefactura
from estado import already_processed, register_prefactura
from notificador import enviar_prefactura

# ── Logging ───────────────────────────────────────────────────────────────────
os.makedirs(OUTPUT_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(OUTPUT_DIR, "facturacion.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# Optional: set a different notification recipient in .env
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL") or USER_EMAIL


# ── Core logic ────────────────────────────────────────────────────────────────
def process_inbox() -> None:
    log.info("Verificando bandeja de entrada…")
    try:
        token = get_token()
    except Exception as e:
        log.error("Error de autenticación con Microsoft 365: %s", e)
        return

    try:
        emails = get_unread_oc_emails(token)
    except Exception as e:
        log.error("Error leyendo emails: %s", e)
        return

    if not emails:
        log.info("Sin órdenes de compra nuevas.")
        return

    log.info("Encontradas %d OC(s) nuevas.", len(emails))

    for email in emails:
        subject = email.get("subject", "(sin asunto)")
        sender  = email.get("from", {}).get("emailAddress", {}).get("address", "?")
        msg_id  = email["id"]
        log.info("━━━ '%s'  de  %s", subject, sender)

        try:
            pdfs = get_pdf_attachments(token, msg_id)
            if not pdfs:
                log.warning("  Sin PDFs adjuntos, se omite.")
                mark_as_read(token, msg_id)
                continue

            for pdf in pdfs:
                log.info("  PDF: %s (%d KB)", pdf["name"], len(pdf["content"]) // 1024)

                pdf_path = save_pdf(pdf["content"], pdf["name"])

                oc = extract_oc_data(pdf_path)
                numero_oc = oc.get("numero_oc") or pdf["name"]

                # ── Deduplication ──────────────────────────────────────────
                if already_processed(numero_oc):
                    log.info("  OC %s ya procesada — saltando.", numero_oc)
                    continue

                log.info(
                    "  OC extraída → #%s | %s | %s %s",
                    numero_oc,
                    oc.get("cliente", {}).get("nombre") or "?",
                    oc.get("moneda", "ARS"),
                    f"{oc.get('total', 0):,.2f}",
                )

                out_dir = os.path.join(OUTPUT_DIR, "prefacturas")
                prefactura_path, json_path = generate_prefactura(oc, out_dir)

                register_prefactura(
                    numero_oc=numero_oc,
                    email_id=msg_id,
                    pdf_path=pdf_path,
                    prefactura_path=prefactura_path,
                    json_path=json_path,
                )

                # ── Notify ─────────────────────────────────────────────────
                if NOTIFY_EMAIL:
                    enviar_prefactura(token, NOTIFY_EMAIL, numero_oc, prefactura_path)

            mark_as_read(token, msg_id)
            log.info("  Email marcado como leído.")

        except Exception as e:
            log.error("  Error procesando '%s': %s", subject, e, exc_info=True)


# ── Entry point ───────────────────────────────────────────────────────────────
# ── Monthly HR pre-invoice (day 2) ───────────────────────────────────────────
def check_monthly_rrhh() -> None:
    hoy = date.today()
    if hoy.day != 2:
        return
    # Bill the previous month
    mes  = hoy.month - 1 if hoy.month > 1 else 12
    anio = hoy.year      if hoy.month > 1 else hoy.year - 1
    log.info("Día 2 detectado — iniciando pre-facturación RRHH para %02d/%d", mes, anio)
    try:
        from prefactura_mensual import generar_para_mes
        generar_para_mes(mes, anio)
    except Exception as e:
        log.error("Error en pre-facturación RRHH: %s", e, exc_info=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sistema de facturación automática")
    parser.add_argument("--once", action="store_true", help="Ejecutar una vez y salir")
    args = parser.parse_args()

    init_db()  # ensure HR tables exist

    log.info("=" * 60)
    log.info("  Sistema de Facturación Automática")
    log.info("  OC email check: cada %ds", POLL_INTERVAL_SECONDS)
    log.info("  RRHH mensual  : día 2 de cada mes a las 08:00")
    log.info("  Salida        : %s", OUTPUT_DIR)
    log.info("=" * 60)

    if args.once:
        process_inbox()
        check_monthly_rrhh()
        return

    process_inbox()
    check_monthly_rrhh()

    schedule.every(POLL_INTERVAL_SECONDS).seconds.do(process_inbox)
    schedule.every().day.at("08:00").do(check_monthly_rrhh)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Detenido por el usuario.")


if __name__ == "__main__":
    main()
