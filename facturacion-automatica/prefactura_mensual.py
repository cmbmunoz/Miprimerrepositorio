"""
Monthly pre-invoice generation from HR data.
Automatically runs on day 2 of each month for the previous month.
Can also be triggered manually.

Usage:
    python prefactura_mensual.py                      # current month
    python prefactura_mensual.py --mes 3 --anio 2025  # specific month
    python prefactura_mensual.py --forzar             # regenerate even if already done
"""

import argparse
import logging
import os
import sys
from datetime import date

from config import OUTPUT_DIR, USER_EMAIL
from hr.db import init_db
from hr.operaciones import (
    listar_proyectos,
    listar_personas,
    ya_prefacturado,
    registrar_prefactura_mensual,
    marcar_email_enviado,
)
from pdf_rrhh import generate_prefactura_rrhh_pdf
from notificador import enviar_prefactura_rrhh

log = logging.getLogger(__name__)

EMPRESA_NOMBRE = os.getenv("EMPRESA_NOMBRE", "Mi Empresa S.A.")
EMPRESA_CUIT   = os.getenv("EMPRESA_CUIT",   "")


def generar_para_mes(mes: int, anio: int, forzar: bool = False) -> int:
    """Generate pre-invoices for all active projects. Returns count of PDFs generated."""
    init_db()

    proyectos = listar_proyectos()
    if not proyectos:
        log.warning("No hay proyectos activos. Usá: python hr.py proyecto agregar")
        return 0

    log.info("═" * 55)
    log.info("  Pre-facturación RRHH — %02d/%d", mes, anio)
    log.info("  Empresa: %s", EMPRESA_NOMBRE)
    log.info("═" * 55)

    token = None
    try:
        from auth import get_token
        token = get_token()
    except Exception as e:
        log.warning("Sin token de email (las prefacturas se generarán sin enviar): %s", e)

    generados = 0
    for proyecto in proyectos:
        log.info("── Proyecto: %s (%s)", proyecto.nombre, proyecto.id)

        if not forzar and ya_prefacturado(mes, anio, proyecto.id):
            log.info("   Ya prefacturado, saltando. (usá --forzar para regenerar)")
            continue

        personas = listar_personas(proyecto_id=proyecto.id)
        if not personas:
            log.info("   Sin personas activas, saltando.")
            continue

        log.info("   %d persona(s) activas.", len(personas))

        numero = f"PFRRHH-{anio}{mes:02d}-{proyecto.id}"
        out_dir = os.path.join(OUTPUT_DIR, "prefacturas_rrhh")
        pdf_path = os.path.join(out_dir, f"prefactura_{numero}.pdf")

        generate_prefactura_rrhh_pdf(
            proyecto=proyecto,
            personas=personas,
            mes=mes,
            anio=anio,
            output_path=pdf_path,
            numero_prefactura=numero,
            empresa_nombre=EMPRESA_NOMBRE,
            empresa_cuit=EMPRESA_CUIT,
        )
        log.info("   ✔ PDF: %s", pdf_path)

        registro_id = registrar_prefactura_mensual(mes, anio, proyecto.id, pdf_path)

        if token and proyecto.cliente_email:
            ok = enviar_prefactura_rrhh(
                token=token,
                proyecto=proyecto,
                personas=personas,
                mes=mes,
                anio=anio,
                pdf_path=pdf_path,
                numero=numero,
                remitente=USER_EMAIL,
            )
            if ok:
                marcar_email_enviado(registro_id)
                log.info("   ✔ Email enviado a %s", proyecto.cliente_email)
        else:
            if not proyecto.cliente_email:
                log.warning("   Sin email de cliente configurado para este proyecto.")

        generados += 1

    log.info("Pre-facturación completada: %d PDF(s) generado(s).", generados)
    return generados


def _mes_anterior(hoy: date) -> tuple[int, int]:
    """Return (mes, anio) of the previous month."""
    if hoy.month == 1:
        return 12, hoy.year - 1
    return hoy.month - 1, hoy.year


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(os.path.join(OUTPUT_DIR, "facturacion.log"), encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    parser = argparse.ArgumentParser(description="Pre-facturación mensual RRHH")
    parser.add_argument("--mes",    type=int, help="Mes (1-12). Default: mes anterior.")
    parser.add_argument("--anio",   type=int, help="Año (ej: 2025). Default: año actual.")
    parser.add_argument("--forzar", action="store_true", help="Regenerar aunque ya exista.")
    args = parser.parse_args()

    hoy = date.today()
    if args.mes and args.anio:
        mes, anio = args.mes, args.anio
    else:
        mes, anio = _mes_anterior(hoy)

    generar_para_mes(mes, anio, forzar=args.forzar)
