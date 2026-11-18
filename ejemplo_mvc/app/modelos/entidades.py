"""Entidades del dominio. Python puro: ni Qt ni SQL."""

from dataclasses import dataclass


@dataclass
class Paciente:
    id: int | None
    nombre: str
    apellido: str


@dataclass
class Medico:
    id: int | None
    nombre: str
    especialidad: str
