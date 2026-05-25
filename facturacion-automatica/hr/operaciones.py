"""CRUD operations for personas, proyectos and monthly pre-invoice tracking."""

from datetime import date
from typing import Optional

from .db import get_connection
from .models import Persona, Proyecto


# ── Proyectos ─────────────────────────────────────────────────────────────────

def agregar_proyecto(p: Proyecto) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO proyectos
               (id, nombre, cliente_nombre, cliente_cuit, cliente_email, descripcion, activo)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (p.id, p.nombre, p.cliente_nombre, p.cliente_cuit,
             p.cliente_email, p.descripcion, int(p.activo)),
        )


def listar_proyectos(solo_activos: bool = True) -> list[Proyecto]:
    q = "SELECT * FROM proyectos" + (" WHERE activo = 1" if solo_activos else "")
    with get_connection() as conn:
        rows = conn.execute(q).fetchall()
    return [Proyecto(**{k: bool(r[k]) if k == "activo" else r[k] for k in r.keys()}) for r in rows]


def obtener_proyecto(id: str) -> Optional[Proyecto]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM proyectos WHERE id = ?", (id,)).fetchone()
    if not row:
        return None
    return Proyecto(**{k: bool(row[k]) if k == "activo" else row[k] for k in row.keys()})


def actualizar_proyecto(p: Proyecto) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE proyectos
               SET nombre=?, cliente_nombre=?, cliente_cuit=?, cliente_email=?, descripcion=?
               WHERE id=?""",
            (p.nombre, p.cliente_nombre, p.cliente_cuit, p.cliente_email, p.descripcion, p.id),
        )


def desactivar_proyecto(id: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE proyectos SET activo = 0 WHERE id = ?", (id,))


# ── Personas ──────────────────────────────────────────────────────────────────

def agregar_persona(p: Persona) -> None:
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO personas
               (id, nombre, proyecto_id, fecha_ingreso, tarifa_mensual, moneda, activo, observaciones)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (p.id, p.nombre, p.proyecto_id, p.fecha_ingreso.isoformat(),
             p.tarifa_mensual, p.moneda, int(p.activo), p.observaciones),
        )


def listar_personas(proyecto_id: Optional[str] = None, solo_activos: bool = True) -> list[Persona]:
    q = "SELECT * FROM personas WHERE 1=1"
    params: list = []
    if solo_activos:
        q += " AND activo = 1"
    if proyecto_id:
        q += " AND proyecto_id = ?"
        params.append(proyecto_id)
    q += " ORDER BY proyecto_id, nombre"
    with get_connection() as conn:
        rows = conn.execute(q, params).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["fecha_ingreso"] = date.fromisoformat(d["fecha_ingreso"])
        d["activo"] = bool(d["activo"])
        result.append(Persona(**d))
    return result


def obtener_persona(id: str) -> Optional[Persona]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM personas WHERE id = ?", (id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["fecha_ingreso"] = date.fromisoformat(d["fecha_ingreso"])
    d["activo"] = bool(d["activo"])
    return Persona(**d)


def dar_baja_persona(id: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE personas SET activo = 0 WHERE id = ?", (id,))


def actualizar_persona(id: str, tarifa: Optional[float] = None,
                       proyecto_id: Optional[str] = None) -> None:
    with get_connection() as conn:
        if tarifa is not None:
            conn.execute("UPDATE personas SET tarifa_mensual = ? WHERE id = ?", (tarifa, id))
        if proyecto_id is not None:
            conn.execute("UPDATE personas SET proyecto_id = ? WHERE id = ?", (proyecto_id, id))


# ── Pre-facturación mensual ───────────────────────────────────────────────────

def ya_prefacturado(mes: int, anio: int, proyecto_id: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM prefacturas_mensuales WHERE mes=? AND anio=? AND proyecto_id=?",
            (mes, anio, proyecto_id),
        ).fetchone()
    return row is not None


def registrar_prefactura_mensual(mes: int, anio: int, proyecto_id: str, pdf_path: str) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO prefacturas_mensuales
               (mes, anio, proyecto_id, fecha_generacion, pdf_path, email_enviado, estado)
               VALUES (?, ?, ?, datetime('now'), ?, 0, 'generada')""",
            (mes, anio, proyecto_id, pdf_path),
        )
        return cur.lastrowid


def marcar_email_enviado(registro_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE prefacturas_mensuales SET email_enviado=1, estado='enviada' WHERE id=?",
            (registro_id,),
        )


def listar_prefacturas_mensuales(mes: Optional[int] = None, anio: Optional[int] = None) -> list[dict]:
    q = "SELECT pm.*, p.nombre as proyecto_nombre, p.cliente_nombre FROM prefacturas_mensuales pm JOIN proyectos p ON pm.proyecto_id = p.id WHERE 1=1"
    params: list = []
    if mes:
        q += " AND pm.mes = ?"; params.append(mes)
    if anio:
        q += " AND pm.anio = ?"; params.append(anio)
    q += " ORDER BY pm.anio DESC, pm.mes DESC, p.nombre"
    with get_connection() as conn:
        rows = conn.execute(q, params).fetchall()
    return [dict(r) for r in rows]
