"""Conexión a SQLite. Solo la usan las implementaciones del repositorio."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

RUTA_BD = Path(__file__).resolve().parents[2] / "ejemplo.db"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS paciente (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre   TEXT NOT NULL,
    apellido TEXT NOT NULL,
    UNIQUE (nombre, apellido)
);
CREATE TABLE IF NOT EXISTS medico (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre       TEXT NOT NULL,
    especialidad TEXT NOT NULL
);
"""


@contextmanager
def conectar():
    cx = sqlite3.connect(RUTA_BD)
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA foreign_keys = ON")
    try:
        yield cx
        cx.commit()
    except Exception:
        cx.rollback()
        raise
    finally:
        cx.close()


def inicializar() -> None:
    with conectar() as cx:
        cx.executescript(ESQUEMA)
