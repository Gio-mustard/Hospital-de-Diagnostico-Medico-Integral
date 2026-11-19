"""Pruebas de DetalleRecetaRepositorio.

Tabla puente entre Receta y Medicamento, con PK COMPUESTA
(id_receta, id_medicamento). Es el caso que obliga a que `obtener_por_id`
reciba dos argumentos y a que `darbaja` reciba la entidad y no una llave
suelta: solo el objeto sabe cual es su llave completa.
"""

import sqlite3
import unittest

from model.detalle_receta import DetalleReceta
from model.repositories import DetalleRecetaRepositorio, DetalleRecetaSQLRepository

from .base import ContratoRepositorioMixin, RepositorioTestCase


class DetalleRecetaTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = DetalleRecetaSQLRepository(self.db)

    @property
    def receta(self):
        return self._perezoso("receta", self.crear_receta)

    def nuevo(self, **cambios) -> DetalleReceta:
        datos = {
            "id_receta": self.receta.id_receta,
            "id_medicamento": self.medicamento.id_medicamento,
            "dosis_indicaciones": "1 tableta cada 8 horas",
        } | cambios
        return DetalleReceta(**datos)


class ContratoDeDetalleReceta(ContratoRepositorioMixin, DetalleRecetaTestCase):
    """DetalleRecetaRepositorio y su implementacion SQL."""

    interfaz = DetalleRecetaRepositorio
    implementacion = DetalleRecetaSQLRepository

    def test_obtener_por_id_pide_las_dos_partes_de_la_llave(self):
        import inspect

        argumentos = list(
            inspect.signature(DetalleRecetaRepositorio.obtener_por_id).parameters
        )
        self.assertEqual(argumentos, ["self", "id_receta", "id_medicamento"])


class RegistrarDetalleReceta(DetalleRecetaTestCase):
    """No hay id que asignar: la llave la forman las dos FK."""

    def test_deja_la_fila_escrita(self):
        detalle = self.repo.registrar(self.nuevo())

        fila = self.leer_fila(
            "DetalleReceta",
            id_receta=detalle.id_receta,
            id_medicamento=detalle.id_medicamento,
        )
        self.assertEqual(fila["dosis_indicaciones"], "1 tableta cada 8 horas")

    def test_devuelve_la_misma_instancia(self):
        detalle = self.nuevo()
        self.assertIs(self.repo.registrar(detalle), detalle)

    def test_la_misma_llave_compuesta_no_se_puede_repetir(self):
        self.repo.registrar(self.nuevo())

        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nuevo())

    def test_la_misma_receta_admite_varios_medicamentos(self):
        otro = self.crear_medicamento()

        self.repo.registrar(self.nuevo())
        self.repo.registrar(self.nuevo(id_medicamento=otro.id_medicamento))

        self.assertEqual(self.contar("DetalleReceta"), 2)

    def test_el_mismo_medicamento_admite_varias_recetas(self):
        otra = self.crear_receta()

        self.repo.registrar(self.nuevo())
        self.repo.registrar(self.nuevo(id_receta=otra.id_receta))

        self.assertEqual(self.contar("DetalleReceta"), 2)

    def test_una_fk_inexistente_falla_en_la_base(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nuevo(id_medicamento=9999))

    def test_valida_la_entidad_antes_de_escribir(self):
        detalle = self.nuevo()
        detalle.dosis_indicaciones = "  "
        with self.assertRaises(ValueError):
            self.repo.registrar(detalle)
        self.assertEqual(self.contar("DetalleReceta"), 0)


class ObtenerDetallesReceta(DetalleRecetaTestCase):
    def test_obtener_por_id_necesita_las_dos_partes(self):
        detalle = self.repo.registrar(self.nuevo())

        leido = self.repo.obtener_por_id(detalle.id_receta, detalle.id_medicamento)

        self.assertIsInstance(leido, DetalleReceta)
        self.assertEqual(leido.dosis_indicaciones, "1 tableta cada 8 horas")

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999, 9999))

    def test_media_llave_no_encuentra_nada(self):
        detalle = self.repo.registrar(self.nuevo())

        self.assertIsNone(self.repo.obtener_por_id(detalle.id_receta, 9999))
        self.assertIsNone(self.repo.obtener_por_id(9999, detalle.id_medicamento))

    def test_obtener_todos_agrupa_por_receta_y_medicamento(self):
        otra = self.crear_receta()
        otro_med = self.crear_medicamento()

        self.repo.registrar(self.nuevo(id_receta=otra.id_receta))
        self.repo.registrar(self.nuevo(id_medicamento=otro_med.id_medicamento))
        self.repo.registrar(self.nuevo())

        llaves = [(d.id_receta, d.id_medicamento) for d in self.repo.obtener_todos()]

        self.assertEqual(llaves, sorted(llaves))

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarDetalleReceta(DetalleRecetaTestCase):
    """Upsert sobre una PK compuesta."""

    def test_inserta_cuando_la_llave_es_nueva(self):
        self.assertTrue(self.repo.guardar(self.nuevo()))
        self.assertEqual(self.contar("DetalleReceta"), 1)

    def test_actualiza_cuando_la_llave_ya_existe(self):
        detalle = self.repo.registrar(self.nuevo())

        detalle.dosis_indicaciones = "2 tabletas cada 12 horas"
        self.assertTrue(self.repo.guardar(detalle))

        self.assertEqual(self.contar("DetalleReceta"), 1)
        self.assertEqual(
            self.repo.obtener_por_id(
                detalle.id_receta, detalle.id_medicamento
            ).dosis_indicaciones,
            "2 tabletas cada 12 horas",
        )

    def test_valida_la_entidad_antes_de_escribir(self):
        detalle = self.repo.registrar(self.nuevo())
        detalle.dosis_indicaciones = ""
        with self.assertRaises(ValueError):
            self.repo.guardar(detalle)


class DarBajaDetalleReceta(DetalleRecetaTestCase):
    """Baja fisica, y necesita la llave compuesta completa."""

    def test_borra_solo_el_renglon_indicado(self):
        otro = self.crear_medicamento()
        detalle = self.repo.registrar(self.nuevo())
        self.repo.registrar(self.nuevo(id_medicamento=otro.id_medicamento))

        self.assertTrue(self.repo.darbaja(detalle))

        self.assertEqual(self.contar("DetalleReceta"), 1)
        self.assertIsNone(
            self.repo.obtener_por_id(detalle.id_receta, detalle.id_medicamento)
        )
        self.assertIsNotNone(self.repo.obtener_por_id(detalle.id_receta, otro.id_medicamento))

    def test_con_una_llave_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo(id_medicamento=9999)))

    def test_no_borra_la_receta_ni_el_medicamento(self):
        detalle = self.repo.registrar(self.nuevo())

        self.repo.darbaja(detalle)

        self.assertEqual(self.contar("Receta"), 1)
        self.assertEqual(self.contar("Medicamento"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
