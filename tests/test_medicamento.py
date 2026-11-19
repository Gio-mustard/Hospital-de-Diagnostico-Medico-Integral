"""Pruebas de MedicamentoRepositorio.

Inventario de farmacia. Su baja es logica pero con dos columnas: `stock = 0` y
`disponible = 0`, que el DDL ademas amarra con
`chk_med_stock_disponible` (no se puede estar disponible con stock en cero).
"""

import sqlite3
import unittest
from datetime import date, timedelta

from model.medicamento import Medicamento
from model.repositories import MedicamentoRepositorio, MedicamentoSQLRepository

from .base import ContratoRepositorioMixin, RepositorioTestCase


class MedicamentoTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = MedicamentoSQLRepository(self.db)

    def dentro_de(self, dias: int) -> date:
        """El trigger trg_medicamento_caducidad_ins exige 15 dias de margen."""
        return date.today() + timedelta(days=dias)

    def nuevo(self, **cambios) -> Medicamento:
        n = self._siguiente()
        datos = {
            "nombre": f"Paracetamol {n}",
            "presentacion": "Tabletas 500mg",
            "stock": 50,
            "lote": f"L-{n:04d}",
            "caducidad": self.dentro_de(90),
            "disponible": True,
        } | cambios
        return Medicamento(**datos)


class ContratoDeMedicamento(ContratoRepositorioMixin, MedicamentoTestCase):
    """MedicamentoRepositorio y su implementacion SQL."""

    interfaz = MedicamentoRepositorio
    implementacion = MedicamentoSQLRepository


class RegistrarMedicamento(MedicamentoTestCase):
    def test_asigna_el_id_generado(self):
        self.assertEqual(self.repo.registrar(self.nuevo()).id_medicamento, 1)
        self.assertEqual(self.repo.registrar(self.nuevo()).id_medicamento, 2)

    def test_devuelve_la_misma_instancia(self):
        med = self.nuevo()
        self.assertIs(self.repo.registrar(med), med)

    def test_deja_la_fila_escrita(self):
        med = self.repo.registrar(self.nuevo(stock=25, lote="LOTE-X"))

        fila = self.leer_fila("Medicamento", id_medicamento=med.id_medicamento)
        self.assertEqual(fila["stock"], 25)
        self.assertEqual(fila["lote"], "LOTE-X")
        self.assertEqual(fila["disponible"], 1)

    def test_guarda_el_booleano_disponible_como_entero(self):
        med = self.repo.registrar(self.nuevo(stock=0, disponible=False))

        fila = self.leer_fila("Medicamento", id_medicamento=med.id_medicamento)
        self.assertEqual(fila["disponible"], 0)
        self.assertIsInstance(fila["disponible"], int)

    def test_guarda_las_fechas_como_texto_iso(self):
        caducidad = self.dentro_de(120)
        med = self.repo.registrar(
            self.nuevo(caducidad=caducidad, proximo_pedido=self.dentro_de(30))
        )

        fila = self.leer_fila("Medicamento", id_medicamento=med.id_medicamento)
        self.assertEqual(fila["caducidad"], caducidad.isoformat())
        self.assertEqual(len(fila["caducidad"]), 10)

    def test_el_proximo_pedido_es_opcional(self):
        med = self.repo.registrar(self.nuevo(proximo_pedido=None))

        fila = self.leer_fila("Medicamento", id_medicamento=med.id_medicamento)
        self.assertIsNone(fila["proximo_pedido"])

    def test_no_acepta_una_caducidad_demasiado_cercana(self):
        """La entidad exige el mismo margen de 15 dias que el trigger del DDL."""
        with self.assertRaises(ValueError):
            self.nuevo(caducidad=self.dentro_de(3))

    def test_no_puede_estar_disponible_con_stock_en_cero(self):
        with self.assertRaises(ValueError):
            self.nuevo(stock=0, disponible=True)

    def test_valida_la_entidad_antes_de_escribir(self):
        med = self.nuevo()
        med.stock = -5
        with self.assertRaises(ValueError):
            self.repo.registrar(med)
        self.assertEqual(self.contar("Medicamento"), 0)


class ObtenerMedicamentos(MedicamentoTestCase):
    def test_obtener_por_id_reconstruye_la_entidad(self):
        med = self.repo.registrar(self.nuevo(nombre="Ibuprofeno"))

        leido = self.repo.obtener_por_id(med.id_medicamento)

        self.assertIsInstance(leido, Medicamento)
        self.assertEqual(leido.nombre, "Ibuprofeno")

    def test_obtener_por_id_devuelve_bool_y_date_no_texto(self):
        med = self.repo.registrar(self.nuevo())

        leido = self.repo.obtener_por_id(med.id_medicamento)

        self.assertIsInstance(leido.disponible, bool)
        self.assertIs(leido.disponible, True)
        self.assertIsInstance(leido.caducidad, date)

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))

    def test_obtener_todos_ordena_por_nombre_y_lote(self):
        self.repo.registrar(self.nuevo(nombre="Zidovudina", lote="L-1"))
        self.repo.registrar(self.nuevo(nombre="Amoxicilina", lote="L-2"))
        self.repo.registrar(self.nuevo(nombre="Amoxicilina", lote="L-1"))

        pares = [(m.nombre, m.lote) for m in self.repo.obtener_todos()]

        self.assertEqual(
            pares, [("Amoxicilina", "L-1"), ("Amoxicilina", "L-2"), ("Zidovudina", "L-1")]
        )

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarMedicamento(MedicamentoTestCase):
    def test_sin_id_inserta_y_asigna_el_id(self):
        med = self.nuevo()

        self.assertTrue(self.repo.guardar(med))

        self.assertIsNotNone(med.id_medicamento)
        self.assertEqual(self.contar("Medicamento"), 1)

    def test_con_id_actualiza_sin_duplicar(self):
        med = self.repo.registrar(self.nuevo())
        med.stock = 10

        self.assertTrue(self.repo.guardar(med))

        self.assertEqual(self.contar("Medicamento"), 1)
        self.assertEqual(self.repo.obtener_por_id(med.id_medicamento).stock, 10)

    def test_puede_reabastecer_un_medicamento_agotado(self):
        med = self.repo.registrar(self.nuevo())
        self.repo.darbaja(med)

        med.stock = 100
        med.disponible = True
        self.assertTrue(self.repo.guardar(med))

        leido = self.repo.obtener_por_id(med.id_medicamento)
        self.assertEqual(leido.stock, 100)
        self.assertIs(leido.disponible, True)

    def test_valida_la_entidad_antes_de_escribir(self):
        med = self.repo.registrar(self.nuevo())
        med.nombre = ""
        with self.assertRaises(ValueError):
            self.repo.guardar(med)


class DarBajaMedicamento(MedicamentoTestCase):
    """Baja logica: se agota el stock y se marca como no disponible."""

    def test_pone_el_stock_en_cero_y_lo_marca_no_disponible(self):
        med = self.repo.registrar(self.nuevo(stock=50))

        self.assertTrue(self.repo.darbaja(med))

        fila = self.leer_fila("Medicamento", id_medicamento=med.id_medicamento)
        self.assertEqual(fila["stock"], 0)
        self.assertEqual(fila["disponible"], 0)

    def test_no_borra_la_fila(self):
        med = self.repo.registrar(self.nuevo())

        self.repo.darbaja(med)

        self.assertEqual(self.contar("Medicamento"), 1)

    def test_refleja_la_baja_en_la_entidad(self):
        med = self.repo.registrar(self.nuevo())

        self.repo.darbaja(med)

        self.assertEqual(med.stock, 0)
        self.assertIs(med.disponible, False)

    def test_la_entidad_sigue_siendo_valida_despues_de_la_baja(self):
        """stock=0 con disponible=False no choca con chk_med_stock_disponible."""
        med = self.repo.registrar(self.nuevo())

        self.repo.darbaja(med)

        med._validar_propiedades()  # no debe levantar

    def test_sin_id_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo()))

    def test_con_id_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo(id_medicamento=9999)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
