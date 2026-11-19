"""Pruebas de HabitacionRepositorio.

PK manual (`num_habitacion`, sin AUTOINCREMENT) y baja fisica.
"""

import sqlite3
import unittest

from model.constants import EstadosHabitacion, TiposHabitacion
from model.habitacion import Habitacion
from model.repositories import HabitacionRepositorio, HabitacionSQLRepository

from .base import ContratoRepositorioMixin, RepositorioTestCase


class HabitacionTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = HabitacionSQLRepository(self.db)

    def nueva(self, **cambios) -> Habitacion:
        return Habitacion(
            **(
                {
                    "num_habitacion": 101,
                    "piso": 1,
                    "tipo": "Individual",
                    "estado": "Disponible",
                }
                | cambios
            )
        )


class ContratoDeHabitacion(ContratoRepositorioMixin, HabitacionTestCase):
    """HabitacionRepositorio y su implementacion SQL."""

    interfaz = HabitacionRepositorio
    implementacion = HabitacionSQLRepository


class RegistrarHabitacion(HabitacionTestCase):
    """La llave la pone quien registra, no la base."""

    def test_respeta_el_numero_que_trae_la_entidad(self):
        hab = self.repo.registrar(self.nueva(num_habitacion=305))

        self.assertEqual(hab.num_habitacion, 305)
        self.assertIsNotNone(self.leer_fila("Habitacion", num_habitacion=305))

    def test_deja_la_fila_escrita_con_sus_enums_como_texto(self):
        hab = self.repo.registrar(
            self.nueva(tipo=TiposHabitacion.UCI, estado=EstadosHabitacion.LIMPIEZA)
        )

        fila = self.leer_fila("Habitacion", num_habitacion=hab.num_habitacion)
        self.assertEqual(fila["tipo"], "UCI")
        self.assertEqual(fila["estado"], "Limpieza")

    def test_un_numero_repetido_choca_con_la_pk(self):
        self.repo.registrar(self.nueva())
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nueva())

    def test_valida_la_entidad_antes_de_escribir(self):
        hab = self.nueva()
        hab.piso = 99  # el DDL solo acepta 1..20
        with self.assertRaises(ValueError):
            self.repo.registrar(hab)
        self.assertEqual(self.contar("Habitacion"), 0)


class ObtenerHabitaciones(HabitacionTestCase):
    """Las lecturas devuelven los enums del dominio, no texto."""

    def test_obtener_por_id_reconstruye_la_habitacion(self):
        self.repo.registrar(self.nueva(num_habitacion=204, tipo="Doble"))

        leida = self.repo.obtener_por_id(204)

        self.assertIsInstance(leida, Habitacion)
        self.assertIs(leida.tipo, TiposHabitacion.DOBLE)
        self.assertIs(leida.estado, EstadosHabitacion.DISPONIBLE)

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))

    def test_obtener_todos_ordena_por_numero(self):
        for numero in (305, 101, 204):
            self.repo.registrar(self.nueva(num_habitacion=numero))

        numeros = [h.num_habitacion for h in self.repo.obtener_todos()]

        self.assertEqual(numeros, [101, 204, 305])

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarHabitacion(HabitacionTestCase):
    """Upsert sobre una PK manual: la llave viene siempre puesta."""

    def test_inserta_cuando_el_numero_es_nuevo(self):
        self.assertTrue(self.repo.guardar(self.nueva(num_habitacion=410)))
        self.assertIsNotNone(self.repo.obtener_por_id(410))

    def test_actualiza_cuando_el_numero_ya_existe(self):
        hab = self.repo.registrar(self.nueva())
        hab.estado = EstadosHabitacion.OCUPADA

        self.assertTrue(self.repo.guardar(hab))

        self.assertEqual(self.contar("Habitacion"), 1)
        self.assertIs(
            self.repo.obtener_por_id(hab.num_habitacion).estado,
            EstadosHabitacion.OCUPADA,
        )

    def test_valida_la_entidad_antes_de_escribir(self):
        hab = self.repo.registrar(self.nueva())
        hab.estado = "Inventado"
        with self.assertRaises(ValueError):
            self.repo.guardar(hab)


class DarBajaHabitacion(HabitacionTestCase):
    """Baja fisica: la habitacion se borra."""

    def test_borra_la_fila(self):
        hab = self.repo.registrar(self.nueva())

        self.assertTrue(self.repo.darbaja(hab))

        self.assertEqual(self.contar("Habitacion"), 0)

    def test_con_numero_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nueva(num_habitacion=9999)))

    def test_no_se_puede_borrar_una_habitacion_con_ingresos(self):
        """La FK de Ingreso es ON DELETE RESTRICT."""
        from model.ingreso import Ingreso
        from model.repositories import IngresoSQLRepository

        hab = self.repo.registrar(self.nueva())
        IngresoSQLRepository(self.db).registrar(
            Ingreso(
                fecha_ingreso="2026-12-01 12:00:00",
                id_cita=self.crear_cita().id_cita,
                num_habitacion=hab.num_habitacion,
            )
        )

        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.darbaja(hab)

        self.assertEqual(self.contar("Habitacion"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
