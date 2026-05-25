"""
CLI to approve a pre-invoice and generate the final invoice.

Usage:
    python aprobar.py              # interactive — lists pending and lets you choose
    python aprobar.py OC-12345     # approve by OC number directly
"""

import argparse
import json
import os
import sys

from estado import list_pending, register_factura, next_invoice_number
from factura import generate_factura
from config import OUTPUT_DIR


def _color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m"


def _green(t): return _color(t, "92")
def _yellow(t): return _color(t, "93")
def _red(t): return _color(t, "91")
def _bold(t): return _color(t, "1")


def show_summary(entry: dict) -> None:
    json_path = entry.get("prefactura_json")
    if not json_path or not os.path.exists(json_path):
        print(_red(f"  No se encontró el JSON de datos: {json_path}"))
        return

    with open(json_path, encoding="utf-8") as f:
        oc = json.load(f)

    print()
    print(f"  OC             : {_bold(oc.get('numero_oc', '?'))}")
    print(f"  Fecha OC       : {oc.get('fecha', '?')}")
    print(f"  Cliente        : {oc.get('cliente', {}).get('nombre', '?')}")
    print(f"  CUIT           : {oc.get('cliente', {}).get('cuit', '?')}")
    print(f"  Total          : {oc.get('moneda', 'ARS')} {oc.get('total', 0):,.2f}")
    print(f"  Prefactura     : {entry.get('prefactura_xlsx', '?')}")
    print()


def approve(entry: dict) -> None:
    json_path = entry.get("prefactura_json")
    if not json_path or not os.path.exists(json_path):
        print(_red("Error: no se encontró el archivo de datos JSON de la pre-factura."))
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        oc = json.load(f)

    numero_factura = next_invoice_number()
    print(f"\nGenerando factura {_bold(numero_factura)}…")

    out_dir = os.path.join(OUTPUT_DIR, "facturas")
    factura_path = generate_factura(oc, out_dir, numero_factura)
    register_factura(entry["numero_oc"], factura_path, numero_factura)

    print(_green(f"\n✔  Factura generada: {factura_path}"))
    print(_green(f"   Número          : {numero_factura}"))
    print()


def interactive() -> None:
    pending = list_pending()
    if not pending:
        print(_yellow("No hay pre-facturas pendientes de aprobación."))
        return

    print(_bold(f"\nPre-facturas pendientes ({len(pending)}):"))
    print("─" * 50)
    for i, entry in enumerate(pending, start=1):
        json_path = entry.get("prefactura_json", "")
        total = "?"
        moneda = "ARS"
        if json_path and os.path.exists(json_path):
            with open(json_path, encoding="utf-8") as f:
                oc = json.load(f)
            total = f"{oc.get('total', 0):,.2f}"
            moneda = oc.get("moneda", "ARS")
        print(f"  [{i}] OC {entry['numero_oc']:20s}  {moneda} {total:>15}  {entry['fecha_prefactura'][:10]}")

    print("  [0] Salir")
    print()

    choice = input("Seleccioná una pre-factura para aprobar: ").strip()
    if choice == "0" or not choice:
        return

    try:
        idx = int(choice) - 1
        entry = pending[idx]
    except (ValueError, IndexError):
        print(_red("Opción inválida."))
        return

    show_summary(entry)
    confirm = input(f"¿Aprobar OC {_bold(entry['numero_oc'])} y generar factura? [s/N] ").strip().lower()
    if confirm == "s":
        approve(entry)
    else:
        print("Cancelado.")


def approve_by_oc(numero_oc: str) -> None:
    pending = {e["numero_oc"]: e for e in list_pending()}
    if numero_oc not in pending:
        print(_red(f"No hay pre-factura pendiente para OC '{numero_oc}'."))
        all_ocs = list(pending.keys())
        if all_ocs:
            print(f"Pendientes: {', '.join(all_ocs)}")
        sys.exit(1)
    show_summary(pending[numero_oc])
    approve(pending[numero_oc])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aprobar pre-factura y generar factura final")
    parser.add_argument("numero_oc", nargs="?", help="Número de OC a aprobar (opcional)")
    args = parser.parse_args()

    if args.numero_oc:
        approve_by_oc(args.numero_oc)
    else:
        interactive()
