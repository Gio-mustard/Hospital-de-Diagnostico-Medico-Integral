"""Implementación en memoria, sin base de datos.

Está aquí para que compruebes la promesa de la arquitectura: cambia dos
líneas en main.py y la app entera corre sin SQLite. Si eso funciona,
mañana funcionará igual con Supabase.
"""

from itertools import count

from app.modelos.entidades import Medico, Paciente
from app.modelos.repositorios import RepositorioMedicos, RepositorioPacientes


class RepositorioPacientesMemoria(RepositorioPacientes):

    def __init__(self):
        self._pacientes: list[Paciente] = []
        self._siguiente_id = count(1)

    def listar(self, busqueda: str = "") -> list[Paciente]:
        q = busqueda.lower()
        return sorted(
            (p for p in self._pacientes
             if not q or q in p.nombre.lower() or q in p.apellido.lower()),
            key=lambda p: (p.apellido, p.nombre),
        )

    def crear(self, nombre: str, apellido: str) -> int:
        nuevo_id = next(self._siguiente_id)
        self._pacientes.append(Paciente(nuevo_id, nombre, apellido))
        return nuevo_id

    def eliminar(self, paciente_id: int) -> int:
        antes = len(self._pacientes)
        self._pacientes = [p for p in self._pacientes if p.id != paciente_id]
        return antes - len(self._pacientes)


class RepositorioMedicosMemoria(RepositorioMedicos):

    def listar(self) -> list[Medico]:
        return [Medico(1, "Dra. Ruiz", "Radiología"),
                Medico(2, "Dr. Pérez", "Patología clínica")]
