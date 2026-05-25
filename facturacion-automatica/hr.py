"""
HR management CLI — manage people and projects.

  python hr.py persona agregar
  python hr.py persona listar [--proyecto PROJ-A]
  python hr.py persona baja --id EMP-001
  python hr.py persona actualizar --id EMP-001 --tarifa 150000 [--proyecto PROJ-B]

  python hr.py proyecto agregar
  python hr.py proyecto listar
  python hr.py proyecto actualizar --id PROJ-A

  python hr.py prefacturas [--mes 3] [--anio 2025]
"""

import argparse
import sys
from datetime import date

from hr.db import init_db
from hr.models import Persona, Proyecto
from hr.operaciones import (
    agregar_persona, listar_personas, dar_baja_persona, actualizar_persona, obtener_persona,
    agregar_proyecto, listar_proyectos, obtener_proyecto, actualizar_proyecto,
    listar_prefacturas_mensuales,
)

# ── ANSI helpers ──────────────────────────────────────────────────────────────
def _c(code, t): return f"\033[{code}m{t}\033[0m"
def green(t):  return _c("92", t)
def yellow(t): return _c("93", t)
def red(t):    return _c("91", t)
def bold(t):   return _c("1",  t)
def blue(t):   return _c("94", t)


def _confirm(prompt: str) -> bool:
    return input(f"{prompt} [s/N] ").strip().lower() == "s"


def _input(prompt: str, default: str = "") -> str:
    val = input(f"{prompt}: ").strip()
    return val or default


# ── Persona commands ──────────────────────────────────────────────────────────
def cmd_persona_agregar(_args):
    print(blue("\n── Agregar persona ──\n"))
    proyectos = listar_proyectos()
    if not proyectos:
        print(red("No hay proyectos. Creá uno primero:  python hr.py proyecto agregar"))
        sys.exit(1)

    print("Proyectos disponibles:")
    for p in proyectos:
        print(f"  {p.id:<15}  {p.nombre}")
    print()

    id_p       = _input("ID único (ej: EMP-001)")
    nombre     = _input("Nombre completo")
    proy_id    = _input("ID del proyecto")

    if not obtener_proyecto(proy_id):
        print(red(f"Proyecto '{proy_id}' no existe."))
        sys.exit(1)

    fecha_str  = _input("Fecha de ingreso (YYYY-MM-DD) [hoy]", date.today().isoformat())
    tarifa     = float(_input("Tarifa mensual"))
    moneda     = _input("Moneda (ARS/USD) [ARS]", "ARS").upper()
    obs        = _input("Observaciones (opcional)", "")

    persona = Persona(
        id=id_p, nombre=nombre, proyecto_id=proy_id,
        fecha_ingreso=date.fromisoformat(fecha_str),
        tarifa_mensual=tarifa, moneda=moneda, observaciones=obs,
    )
    agregar_persona(persona)
    print(green(f"\n✔  {nombre} ({id_p}) agregada al proyecto {proy_id}.\n"))


def cmd_persona_listar(args):
    personas = listar_personas(proyecto_id=args.proyecto)
    if not personas:
        print(yellow("No hay personas activas."))
        return

    print()
    print(f"  {'ID':<12}  {'Nombre':<28}  {'Proyecto':<14}  {'Ingreso':<12}  {'Mon':<5}  {'Tarifa':>14}")
    print("  " + "─" * 95)
    for p in personas:
        print(f"  {p.id:<12}  {p.nombre:<28}  {p.proyecto_id:<14}  "
              f"{p.fecha_ingreso.strftime('%d/%m/%Y'):<12}  {p.moneda:<5}  {p.tarifa_mensual:>14,.2f}")
    print()


def cmd_persona_baja(args):
    p = obtener_persona(args.id)
    if not p:
        print(red(f"Persona '{args.id}' no encontrada."))
        sys.exit(1)
    if _confirm(f"¿Dar de baja a {p.nombre} ({p.id})?"):
        dar_baja_persona(args.id)
        print(green(f"✔  {p.nombre} dada de baja.\n"))
    else:
        print("Cancelado.")


def cmd_persona_actualizar(args):
    p = obtener_persona(args.id)
    if not p:
        print(red(f"Persona '{args.id}' no encontrada."))
        sys.exit(1)
    actualizar_persona(args.id, tarifa=args.tarifa, proyecto_id=args.proyecto)
    cambios = []
    if args.tarifa:   cambios.append(f"tarifa → {args.tarifa:,.2f}")
    if args.proyecto: cambios.append(f"proyecto → {args.proyecto}")
    print(green(f"✔  {p.nombre}: {', '.join(cambios)}.\n"))


# ── Proyecto commands ─────────────────────────────────────────────────────────
def cmd_proyecto_agregar(_args):
    print(blue("\n── Agregar proyecto ──\n"))
    p = Proyecto(
        id             = _input("ID único (ej: PROJ-ALPHA)"),
        nombre         = _input("Nombre del proyecto"),
        cliente_nombre = _input("Razón social del cliente"),
        cliente_cuit   = _input("CUIT del cliente (opcional)", ""),
        cliente_email  = _input("Email del cliente (donde enviar prefacturas)"),
        descripcion    = _input("Descripción (opcional)", ""),
    )
    agregar_proyecto(p)
    print(green(f"\n✔  Proyecto '{p.nombre}' ({p.id}) creado.\n"))


def cmd_proyecto_listar(_args):
    proyectos = listar_proyectos()
    if not proyectos:
        print(yellow("No hay proyectos activos."))
        return
    print()
    print(f"  {'ID':<16}  {'Nombre':<24}  {'Cliente':<24}  {'CUIT':<16}  {'Email'}")
    print("  " + "─" * 105)
    for p in proyectos:
        print(f"  {p.id:<16}  {p.nombre:<24}  {p.cliente_nombre:<24}  "
              f"{p.cliente_cuit:<16}  {p.cliente_email}")
    print()


def cmd_proyecto_actualizar(args):
    p = obtener_proyecto(args.id)
    if not p:
        print(red(f"Proyecto '{args.id}' no encontrado."))
        sys.exit(1)
    print(blue(f"\n── Actualizar proyecto {p.id} ──\n"))
    print("(Dejá en blanco para mantener el valor actual)\n")
    p.nombre         = _input(f"Nombre          [{p.nombre}]",         p.nombre)
    p.cliente_nombre = _input(f"Cliente         [{p.cliente_nombre}]", p.cliente_nombre)
    p.cliente_cuit   = _input(f"CUIT            [{p.cliente_cuit}]",   p.cliente_cuit)
    p.cliente_email  = _input(f"Email           [{p.cliente_email}]",  p.cliente_email)
    p.descripcion    = _input(f"Descripción     [{p.descripcion}]",    p.descripcion)
    actualizar_proyecto(p)
    print(green(f"\n✔  Proyecto {p.id} actualizado.\n"))


# ── Prefacturas ───────────────────────────────────────────────────────────────
def cmd_prefacturas(args):
    registros = listar_prefacturas_mensuales(mes=args.mes, anio=args.anio)
    if not registros:
        print(yellow("No hay prefacturas mensuales registradas."))
        return
    print()
    print(f"  {'Mes/Año':<10}  {'Proyecto':<20}  {'Cliente':<22}  {'Estado':<12}  {'Email':<6}  PDF")
    print("  " + "─" * 105)
    for r in registros:
        mes_anio  = f"{r['mes']:02d}/{r['anio']}"
        email_ok  = green("✔") if r["email_enviado"] else yellow("✗")
        pdf_short = (r["pdf_path"] or "—").replace("\\", "/").split("/")[-1]
        print(f"  {mes_anio:<10}  {r['proyecto_id']:<20}  {r['cliente_nombre']:<22}  "
              f"{r['estado']:<12}  {email_ok:<6}  {pdf_short}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    init_db()

    parser = argparse.ArgumentParser(
        description="Sistema RRHH — gestión de personas y proyectos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="entidad")

    # persona
    p_cmd = sub.add_parser("persona", help="Gestionar personas")
    p_sub = p_cmd.add_subparsers(dest="accion")
    p_sub.add_parser("agregar", help="Agregar persona")
    p_listar = p_sub.add_parser("listar", help="Listar personas activas")
    p_listar.add_argument("--proyecto", help="Filtrar por proyecto")
    p_baja = p_sub.add_parser("baja", help="Dar de baja una persona")
    p_baja.add_argument("--id", required=True)
    p_act = p_sub.add_parser("actualizar", help="Actualizar tarifa o proyecto")
    p_act.add_argument("--id",       required=True)
    p_act.add_argument("--tarifa",   type=float, default=None)
    p_act.add_argument("--proyecto", default=None)

    # proyecto
    pr_cmd = sub.add_parser("proyecto", help="Gestionar proyectos")
    pr_sub = pr_cmd.add_subparsers(dest="accion")
    pr_sub.add_parser("agregar", help="Crear proyecto")
    pr_sub.add_parser("listar",  help="Listar proyectos activos")
    pr_act = pr_sub.add_parser("actualizar", help="Actualizar datos del proyecto")
    pr_act.add_argument("--id", required=True)

    # prefacturas (historial)
    pf_cmd = sub.add_parser("prefacturas", help="Ver historial de prefacturas mensuales")
    pf_cmd.add_argument("--mes",  type=int, default=None)
    pf_cmd.add_argument("--anio", type=int, default=None)

    args = parser.parse_args()

    dispatch = {
        ("persona",    "agregar"):    cmd_persona_agregar,
        ("persona",    "listar"):     cmd_persona_listar,
        ("persona",    "baja"):       cmd_persona_baja,
        ("persona",    "actualizar"): cmd_persona_actualizar,
        ("proyecto",   "agregar"):    cmd_proyecto_agregar,
        ("proyecto",   "listar"):     cmd_proyecto_listar,
        ("proyecto",   "actualizar"): cmd_proyecto_actualizar,
        ("prefacturas", None):        cmd_prefacturas,
    }

    key = (args.entidad, getattr(args, "accion", None))
    fn  = dispatch.get(key)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
