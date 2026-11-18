"""Prueba la capa de modelo SIN Qt y SIN abrir ninguna ventana.

Si esto corre, la separación de capas es real y no solo un dibujo:

    ../env/bin/python verificar_modelo.py
"""

import sys

from app.modelos.repositorios_memoria import RepositorioPacientesMemoria
from app.modelos.repositorios_sqlite import RepositorioPacientesSQLite


def ejercitar(repositorio, etiqueta):
    repositorio.crear("Ana", "López")
    repositorio.crear("Beto", "Díaz")
    print(f"{etiqueta}: {len(repositorio.listar())} pacientes,",
          f"busqueda 'lóp' -> {[p.nombre for p in repositorio.listar('lóp')]}")
    primero = repositorio.listar()[0]
    repositorio.eliminar(primero.id)
    print(f"{etiqueta}: tras eliminar -> {len(repositorio.listar())}")


ejercitar(RepositorioPacientesMemoria(), "memoria")
ejercitar(RepositorioPacientesSQLite(), "sqlite ")
print("Qt cargado en este proceso:", any(m.startswith("PySide6") for m in sys.modules))
