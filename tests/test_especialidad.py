"""Pruebas de EspecialidadRepositorio.

Tabla simple con PK AUTOINCREMENT y baja fisica (DELETE).
"""

import sqlite3
import unittest

from model.especialidad import Especialidad
from model.asignacion_especialidad import MedicoEspecialidad
from model.repositories import (
    AsignacionEspecialidadSQLRepository,
    EspecialidadRepositorio,
    EspecialidadSQLRepository,
)

from .base import ContratoRepositorioMixin, RepositorioTestCase


class EspecialidadTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = EspecialidadSQLRepository(self.db)

    def nueva(self, **cambios) -> Especialidad:
        return Especialidad(**({"nombre": "Cardiología", "descripcion": "Corazón"} | cambios))


class ContratoDeEspecialidad(ContratoRepositorioMixin, EspecialidadTestCase):
    """EspecialidadRepositorio y su implementacion SQL."""

    interfaz = EspecialidadRepositorio
    implementacion = EspecialidadSQLRepository


class RegistrarEspecialidad(EspecialidadTestCase):
    """registrar(entidad) inserta y asigna el id_esp que genero la base."""

    def test_asigna_el_id_generado(self):
        self.assertEqual(self.repo.registrar(self.nueva()).id_esp, 1)
        self.assertEqual(self.repo.registrar(self.nueva(nombre="Pediatría")).id_esp, 2)

    def test_devuelve_la_misma_instancia(self):
        esp = self.nueva()
        self.assertIs(self.repo.registrar(esp), esp)

    def test_deja_la_fila_escrita(self):
        esp = self.repo.registrar(self.nueva())
        fila = self.leer_fila("Especialidad", id_esp=esp.id_esp)
        self.assertEqual(fila["nombre"], "Cardiología")
        self.assertEqual(fila["descripcion"], "Corazón")

    def test_la_descripcion_es_opcional(self):
        esp = self.repo.registrar(self.nueva(descripcion=None))
        self.assertIsNone(self.leer_fila("Especialidad", id_esp=esp.id_esp)["descripcion"])

    def test_el_nombre_repetido_choca_con_el_unique(self):
        self.repo.registrar(self.nueva())
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nueva())

    def test_valida_la_entidad_antes_de_escribir(self):
        esp = self.nueva()
        esp.nombre = "  "
        with self.assertRaises(ValueError):
            self.repo.registrar(esp)
        self.assertEqual(self.contar("Especialidad"), 0)


class ObtenerEspecialidades(EspecialidadTestCase):
    """Las lecturas reconstruyen la entidad."""

    def test_obtener_por_id_reconstruye_la_especialidad(self):
        esp = self.repo.registrar(self.nueva())
        leida = self.repo.obtener_por_id(esp.id_esp)
        self.assertIsInstance(leida, Especialidad)
        self.assertEqual(leida.nombre, "Cardiología")

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())

    def test_obtener_todos_ordena_por_nombre(self):
        for nombre in ("Pediatría", "Cardiología", "Neurología"):
            self.repo.registrar(self.nueva(nombre=nombre))

        nombres = [e.nombre for e in self.repo.obtener_todos()]

        self.assertEqual(nombres, ["Cardiología", "Neurología", "Pediatría"])


class GuardarEspecialidad(EspecialidadTestCase):
    """guardar(entidad) inserta si no hay llave, y actualiza si ya la hay."""

    def test_sin_id_inserta_y_asigna_el_id(self):
        esp = self.nueva()
        self.assertTrue(self.repo.guardar(esp))
        self.assertIsNotNone(esp.id_esp)
        self.assertEqual(self.contar("Especialidad"), 1)

    def test_con_id_actualiza_sin_duplicar(self):
        esp = self.repo.registrar(self.nueva())
        esp.descripcion = "Corazón y vasos"

        self.assertTrue(self.repo.guardar(esp))

        self.assertEqual(self.contar("Especialidad"), 1)
        self.assertEqual(
            self.repo.obtener_por_id(esp.id_esp).descripcion, "Corazón y vasos"
        )

    def test_valida_la_entidad_antes_de_escribir(self):
        esp = self.repo.registrar(self.nueva())
        esp.nombre = ""
        with self.assertRaises(ValueError):
            self.repo.guardar(esp)


class DarBajaEspecialidad(EspecialidadTestCase):
    """Aqui la baja es fisica: la especialidad se borra de la tabla."""

    def test_borra_la_fila(self):
        esp = self.repo.registrar(self.nueva())

        self.assertTrue(self.repo.darbaja(esp))

        self.assertEqual(self.contar("Especialidad"), 0)
        self.assertIsNone(self.repo.obtener_por_id(esp.id_esp))

    def test_sin_id_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nueva()))

    def test_con_id_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nueva(id_esp=9999)))

    def test_no_se_puede_borrar_una_especialidad_asignada(self):
        """La FK de MedicoEspecialidad es ON DELETE RESTRICT."""
        esp = self.repo.registrar(self.nueva())
        AsignacionEspecialidadSQLRepository(self.db).registrar(
            MedicoEspecialidad(id_medico=self.medico.id_medico, id_esp=esp.id_esp)
        )

        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.darbaja(esp)

        self.assertEqual(self.contar("Especialidad"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
