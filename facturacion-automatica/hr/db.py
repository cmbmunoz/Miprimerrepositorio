"""SQLite database — connection and schema initialisation."""

import os
import sqlite3

from config import OUTPUT_DIR

DB_PATH = os.path.join(OUTPUT_DIR, "hr.db")


def get_connection() -> sqlite3.Connection:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS proyectos (
                id              TEXT PRIMARY KEY,
                nombre          TEXT NOT NULL,
                cliente_nombre  TEXT NOT NULL,
                cliente_cuit    TEXT DEFAULT '',
                cliente_email   TEXT DEFAULT '',
                descripcion     TEXT DEFAULT '',
                activo          INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS personas (
                id              TEXT PRIMARY KEY,
                nombre          TEXT NOT NULL,
                proyecto_id     TEXT NOT NULL,
                fecha_ingreso   TEXT NOT NULL,
                tarifa_mensual  REAL NOT NULL,
                moneda          TEXT DEFAULT 'ARS',
                activo          INTEGER DEFAULT 1,
                observaciones   TEXT DEFAULT '',
                FOREIGN KEY (proyecto_id) REFERENCES proyectos(id)
            );

            CREATE TABLE IF NOT EXISTS prefacturas_mensuales (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                mes              INTEGER NOT NULL,
                anio             INTEGER NOT NULL,
                proyecto_id      TEXT NOT NULL,
                fecha_generacion TEXT NOT NULL,
                pdf_path         TEXT,
                email_enviado    INTEGER DEFAULT 0,
                estado           TEXT DEFAULT 'generada',
                FOREIGN KEY (proyecto_id) REFERENCES proyectos(id)
            );
        """)
