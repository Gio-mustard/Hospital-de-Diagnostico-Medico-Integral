"""Pruebas de RecetaRepositorio.

Lo propio de esta tabla es la columna `tratamiento`: un JSON que el DDL obliga a
ser un objeto con tres llaves. El repositorio lo serializa al escribir y lo
deserializa al leer, asi que la entidad siempre ve un dict de Python.

Tambien tiene una regla XOR: la receta viene de una cita O de un ingreso de
emergencia, nunca de las dos ni de ninguna.
"""

import json
import sqlite3
import unittest
from datetime import date

from model.receta import Receta
from model.repositories import RecetaRepositorio, RecetaSQLRepository

from .base import TRATAMIENTO, ContratoRepositorioMixin, RepositorioTestCase


class RecetaTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = RecetaSQLRepository(self.db)

    def nueva(self, **cambios) -> Receta:
        if "id_cita" not in cambios and "id_ingreso_emergencia" not in cambios:
            cambios = {"id_cita": self.crear_cita().id_cita} | cambios
        datos = {"fecha_emision": "2026-12-01", "tratamiento": dict(TRATAMIENTO)} | cambios
        return Receta(**datos)


class ContratoDeReceta(ContratoRepositorioMixin, RecetaTestCase):
    """RecetaRepositorio y su implementacion SQL."""

    interfaz = RecetaRepositorio
    implementacion = RecetaSQLRepository


class RegistrarReceta(RecetaTestCase):
    def test_asigna_el_id_generado(self):
        self.assertEqual(self.repo.registrar(self.nueva()).id_receta, 1)
        self.assertEqual(self.repo.registrar(self.nueva()).id_receta, 2)

    def test_devuelve_la_misma_instancia(self):
        receta = self.nueva()
        self.assertIs(self.repo.registrar(receta), receta)

    def test_guarda_el_tratamiento_como_json(self):
        receta = self.repo.registrar(self.nueva())

        guardado = self.leer_fila("Receta", id_receta=receta.id_receta)["tratamiento"]

        self.assertIsInstance(guardado, str, "en la base tiene que ser texto")
        self.assertEqual(json.loads(guardado), TRATAMIENTO)

    def test_guarda_el_json_sin_escapar_los_acentos(self):
        """`ensure_ascii=False`: en la base se lee el texto tal cual."""
        receta = self.repo.registrar(
            self.nueva(tratamiento=dict(TRATAMIENTO, diagnostico="Migraña crónica"))
        )

        guardado = self.leer_fila("Receta", id_receta=receta.id_receta)["tratamiento"]
        self.assertIn("Migraña crónica", guardado)

    def test_guarda_la_fecha_como_texto_iso(self):
        receta = self.repo.registrar(self.nueva(fecha_emision=date(2026, 12, 1)))

        fila = self.leer_fila("Receta", id_receta=receta.id_receta)
        self.assertEqual(fila["fecha_emision"], "2026-12-01")

    def test_puede_venir_de_un_ingreso_de_emergencia(self):
        emergencia = self.crear_ingreso_emergencia()

        receta = self.repo.registrar(
            Receta(
                fecha_emision="2026-12-01",
                tratamiento=dict(TRATAMIENTO),
                id_ingreso_emergencia=emergencia.id_ingreso_emergencia,
            )
        )

        fila = self.leer_fila("Receta", id_receta=receta.id_receta)
        self.assertIsNone(fila["id_cita"])
        self.assertEqual(fila["id_ingreso_emergencia"], emergencia.id_ingreso_emergencia)

    def test_no_puede_venir_de_las_dos_cosas(self):
        with self.assertRaises(ValueError):
            Receta(
                fecha_emision="2026-12-01",
                tratamiento=dict(TRATAMIENTO),
                id_cita=self.crear_cita().id_cita,
                id_ingreso_emergencia=self.crear_ingreso_emergencia().id_ingreso_emergencia,
            )

    def test_no_puede_venir_de_ninguna(self):
        with self.assertRaises(ValueError):
            Receta(fecha_emision="2026-12-01", tratamiento=dict(TRATAMIENTO))

    def test_el_tratamiento_necesita_sus_tres_llaves(self):
        with self.assertRaises(ValueError):
            self.nueva(tratamiento={"diagnostico": "Solo una llave"})

    def test_valida_la_entidad_antes_de_escribir(self):
        receta = self.nueva()
        receta.tratamiento = {"incompleto": True}
        with self.assertRaises(ValueError):
            self.repo.registrar(receta)
        self.assertEqual(self.contar("Receta"), 0)


class ObtenerRecetas(RecetaTestCase):
    """Al leer, el JSON vuelve a ser un dict."""

    def test_obtener_por_id_deserializa_el_tratamiento(self):
        receta = self.repo.registrar(self.nueva())

        leida = self.repo.obtener_por_id(receta.id_receta)

        self.assertIsInstance(leida, Receta)
        self.assertIsInstance(leida.tratamiento, dict)
        self.assertEqual(leida.tratamiento, TRATAMIENTO)
        self.assertEqual(leida.tratamiento["medicamentos"], ["Omeprazol 20mg"])

    def test_obtener_por_id_devuelve_la_fecha_como_date(self):
        receta = self.repo.registrar(self.nueva())

        leida = self.repo.obtener_por_id(receta.id_receta)

        self.assertIsInstance(leida.fecha_emision, date)
        self.assertEqual(leida.fecha_emision, date(2026, 12, 1))

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))

    def test_obtener_todos_va_de_la_mas_reciente_a_la_mas_antigua(self):
        self.repo.registrar(self.nueva(fecha_emision="2026-01-15"))
        self.repo.registrar(self.nueva(fecha_emision="2026-03-20"))
        self.repo.registrar(self.nueva(fecha_emision="2026-02-10"))

        fechas = [r.fecha_emision for r in self.repo.obtener_todos()]

        self.assertEqual(fechas, sorted(fechas, reverse=True))

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarReceta(RecetaTestCase):
    def test_sin_id_inserta_y_asigna_el_id(self):
        receta = self.nueva()

        self.assertTrue(self.repo.guardar(receta))

        self.assertIsNotNone(receta.id_receta)
        self.assertEqual(self.contar("Receta"), 1)

    def test_con_id_actualiza_sin_duplicar(self):
        receta = self.repo.registrar(self.nueva())

        receta.tratamiento = dict(TRATAMIENTO, diagnostico="Gastritis crónica")
        self.assertTrue(self.repo.guardar(receta))

        self.assertEqual(self.contar("Receta"), 1)
        self.assertEqual(
            self.repo.obtener_por_id(receta.id_receta).tratamiento["diagnostico"],
            "Gastritis crónica",
        )

    def test_el_json_sobrevive_una_vuelta_completa(self):
        """Escribir y volver a leer no debe deformar el tratamiento."""
        complejo = {
            "diagnostico": "Múltiple",
            "medicamentos": [{"nombre": "Omeprazol", "dosis": 20}, "Ranitidina"],
            "indicaciones_generales": None,
        }
        receta = self.repo.registrar(self.nueva(tratamiento=complejo))

        self.assertEqual(self.repo.obtener_por_id(receta.id_receta).tratamiento, complejo)

    def test_valida_la_entidad_antes_de_escribir(self):
        receta = self.repo.registrar(self.nueva())
        receta.tratamiento = {}
        with self.assertRaises(ValueError):
            self.repo.guardar(receta)


class DarBajaReceta(RecetaTestCase):
    """Baja fisica: la receta se borra."""

    def test_borra_la_fila(self):
        receta = self.repo.registrar(self.nueva())

        self.assertTrue(self.repo.darbaja(receta))

        self.assertEqual(self.contar("Receta"), 0)

    def test_sin_id_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nueva()))

    def test_con_id_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nueva(id_receta=9999)))

    def test_arrastra_sus_renglones_de_detalle(self):
        """La FK de DetalleReceta es ON DELETE CASCADE, no RESTRICT."""
        from model.detalle_receta import DetalleReceta
        from model.repositories import DetalleRecetaSQLRepository

        receta = self.repo.registrar(self.nueva())
        DetalleRecetaSQLRepository(self.db).registrar(
            DetalleReceta(
                id_receta=receta.id_receta,
                id_medicamento=self.medicamento.id_medicamento,
                dosis_indicaciones="1 cada 8 horas",
            )
        )

        self.assertTrue(self.repo.darbaja(receta))

        self.assertEqual(self.contar("Receta"), 0)
        self.assertEqual(self.contar("DetalleReceta"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
