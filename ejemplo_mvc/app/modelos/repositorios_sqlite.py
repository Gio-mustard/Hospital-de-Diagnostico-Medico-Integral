"""Implementación con SQLite. Aquí vive TODO el SQL de la app."""

from app.modelos.conexion import conectar, inicializar
from app.modelos.entidades import Medico, Paciente
from app.modelos.repositorios import RepositorioMedicos, RepositorioPacientes


class RepositorioPacientesSQLite(RepositorioPacientes):

    def __init__(self):
        inicializar()

    def listar(self, busqueda: str = "") -> list[Paciente]:
        sql = """
            SELECT id, nombre, apellido FROM paciente
            WHERE (:q = '' OR nombre   LIKE '%' || :q || '%'
                           OR apellido LIKE '%' || :q || '%')
            ORDER BY apellido, nombre
        """
        with conectar() as cx:
            return [Paciente(**dict(f)) for f in cx.execute(sql, {"q": busqueda})]

    def crear(self, nombre: str, apellido: str) -> int:
        with conectar() as cx:
            return cx.execute(
                "INSERT INTO paciente (nombre, apellido) VALUES (?, ?)",
                (nombre, apellido),
            ).lastrowid

    def eliminar(self, paciente_id: int) -> int:
        with conectar() as cx:
            return cx.execute("DELETE FROM paciente WHERE id = ?",
                              (paciente_id,)).rowcount


class RepositorioMedicosSQLite(RepositorioMedicos):

    def __init__(self):
        inicializar()
        with conectar() as cx:
            if not cx.execute("SELECT 1 FROM medico LIMIT 1").fetchone():
                cx.executemany(
                    "INSERT INTO medico (nombre, especialidad) VALUES (?, ?)",
                    [("Dra. Ruiz", "Radiología"),
                     ("Dr. Pérez", "Patología clínica")],
                )

    def listar(self) -> list[Medico]:
        with conectar() as cx:
            return [Medico(**dict(f)) for f in
                    cx.execute("SELECT id, nombre, especialidad FROM medico ORDER BY nombre")]
