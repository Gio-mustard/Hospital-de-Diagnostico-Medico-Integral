"""Pruebas de ConsultorioRepositorio.

PK manual (`num_consultorio`) y baja fisica, igual que Habitacion.
"""

import sqlite3
import unittest

from model.constants import EstadosConsultorio
from model.consultorio import Consultorio
from model.repositories import ConsultorioRepositorio, ConsultorioSQLRepository

from .base import ContratoRepositorioMixin, RepositorioTestCase


class ConsultorioTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = ConsultorioSQLRepository(self.db)

    def nuevo(self, **cambios) -> Consultorio:
        return Consultorio(
            **(
                {
                    "num_consultorio": 5,
                    "piso": 2,
                    "departamento": "Medicina Interna",
                    "estado": "Disponible",
                }
                | cambios
            )
        )


class ContratoDeConsultorio(ContratoRepositorioMixin, ConsultorioTestCase):
    """ConsultorioRepositorio y su implementacion SQL."""

    interfaz = ConsultorioRepositorio
    implementacion = ConsultorioSQLRepository


class RegistrarConsultorio(ConsultorioTestCase):
    """La llave la pone quien registra."""

    def test_respeta_el_numero_que_trae_la_entidad(self):
        cons = self.repo.registrar(self.nuevo(num_consultorio=12))

        self.assertEqual(cons.num_consultorio, 12)
        self.assertIsNotNone(self.leer_fila("Consultorio", num_consultorio=12))

    def test_devuelve_la_misma_instancia(self):
        cons = self.nuevo()
        self.assertIs(self.repo.registrar(cons), cons)

    def test_deja_la_fila_escrita(self):
        cons = self.repo.registrar(
            self.nuevo(departamento="Cardiología", estado=EstadosConsultorio.MANTENIMIENTO)
        )

        fila = self.leer_fila("Consultorio", num_consultorio=cons.num_consultorio)
        self.assertEqual(fila["departamento"], "Cardiología")
        self.assertEqual(fila["estado"], "Mantenimiento")
        self.assertEqual(fila["piso"], 2)

    def test_un_numero_repetido_choca_con_la_pk(self):
        self.repo.registrar(self.nuevo())
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nuevo())

    def test_valida_la_entidad_antes_de_escribir(self):
        cons = self.nuevo()
        cons.piso = 0  # el DDL solo acepta 1..20
        with self.assertRaises(ValueError):
            self.repo.registrar(cons)
        self.assertEqual(self.contar("Consultorio"), 0)


class ObtenerConsultorios(ConsultorioTestCase):
    def test_obtener_por_id_reconstruye_el_consultorio(self):
        self.repo.registrar(self.nuevo(num_consultorio=7))

        leido = self.repo.obtener_por_id(7)

        self.assertIsInstance(leido, Consultorio)
        self.assertIs(leido.estado, EstadosConsultorio.DISPONIBLE)

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))

    def test_obtener_todos_ordena_por_numero(self):
        for numero in (12, 3, 7):
            self.repo.registrar(self.nuevo(num_consultorio=numero))

        self.assertEqual(
            [c.num_consultorio for c in self.repo.obtener_todos()], [3, 7, 12]
        )

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarConsultorio(ConsultorioTestCase):
    def test_inserta_cuando_el_numero_es_nuevo(self):
        self.assertTrue(self.repo.guardar(self.nuevo(num_consultorio=20)))
        self.assertIsNotNone(self.repo.obtener_por_id(20))

    def test_actualiza_cuando_el_numero_ya_existe(self):
        cons = self.repo.registrar(self.nuevo())
        cons.estado = EstadosConsultorio.OCUPADO

        self.assertTrue(self.repo.guardar(cons))

        self.assertEqual(self.contar("Consultorio"), 1)
        self.assertIs(
            self.repo.obtener_por_id(cons.num_consultorio).estado,
            EstadosConsultorio.OCUPADO,
        )

    def test_valida_la_entidad_antes_de_escribir(self):
        cons = self.repo.registrar(self.nuevo())
        cons.estado = "Inventado"
        with self.assertRaises(ValueError):
            self.repo.guardar(cons)


class DarBajaConsultorio(ConsultorioTestCase):
    """Baja fisica: el consultorio se borra."""

    def test_borra_la_fila(self):
        cons = self.repo.registrar(self.nuevo())

        self.assertTrue(self.repo.darbaja(cons))

        self.assertEqual(self.contar("Consultorio"), 0)

    def test_con_numero_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo(num_consultorio=9999)))

    def test_no_se_puede_borrar_un_consultorio_con_citas(self):
        """La FK de Cita es ON DELETE RESTRICT."""
        cons = self.repo.registrar(self.nuevo())
        self.crear_cita(num_consultorio=cons.num_consultorio)

        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.darbaja(cons)

        self.assertEqual(self.contar("Consultorio"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
