"""Pruebas de IngresoRepositorio.

Internamiento hospitalario. Su `darbaja` es el caso mas particular de todos:
dar de baja un ingreso significa dar de ALTA al paciente, poniendole
`fecha_alta`.
"""

import sqlite3
import unittest
from datetime import datetime, timedelta

from model.ingreso import Ingreso
from model.repositories import IngresoRepositorio, IngresoSQLRepository

from .base import ContratoRepositorioMixin, RepositorioTestCase


class IngresoTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = IngresoSQLRepository(self.db)

    def hace_dias(self, dias: int) -> datetime:
        """Fecha relativa a hoy, sin microsegundos (el DDL guarda segundos).

        El ingreso por defecto tiene que quedar en el PASADO: `darbaja` usa el
        momento actual como fecha de alta, y `chk_ingreso_fechas` exige
        `fecha_alta > fecha_ingreso`. Con una fecha fija futura, dar de alta
        seria imposible.
        """
        return (datetime.now() - timedelta(days=dias)).replace(microsecond=0)

    def nuevo(self, **cambios) -> Ingreso:
        if "id_cita" not in cambios:
            cambios = {"id_cita": self.crear_cita().id_cita} | cambios
        datos = {
            "fecha_ingreso": self.hace_dias(3),
            "num_habitacion": self.habitacion.num_habitacion,
        } | cambios
        return Ingreso(**datos)


class ContratoDeIngreso(ContratoRepositorioMixin, IngresoTestCase):
    """IngresoRepositorio y su implementacion SQL."""

    interfaz = IngresoRepositorio
    implementacion = IngresoSQLRepository


class RegistrarIngreso(IngresoTestCase):
    def test_asigna_el_id_generado(self):
        self.assertEqual(self.repo.registrar(self.nuevo()).id_ingreso, 1)
        self.assertEqual(self.repo.registrar(self.nuevo()).id_ingreso, 2)

    def test_devuelve_la_misma_instancia(self):
        ingreso = self.nuevo()
        self.assertIs(self.repo.registrar(ingreso), ingreso)

    def test_deja_la_fila_escrita(self):
        ingreso = self.repo.registrar(self.nuevo(fecha_ingreso="2026-12-01 12:00:00"))

        fila = self.leer_fila("Ingreso", id_ingreso=ingreso.id_ingreso)
        self.assertEqual(fila["fecha_ingreso"], "2026-12-01 12:00:00")
        self.assertEqual(fila["num_habitacion"], self.habitacion.num_habitacion)
        self.assertIsNone(fila["fecha_alta"])

    def test_nace_sin_fecha_de_alta(self):
        """Un internamiento recien abierto todavia no termina."""
        ingreso = self.repo.registrar(self.nuevo())
        self.assertIsNone(ingreso.fecha_alta)

    def test_una_cita_no_puede_tener_dos_ingresos(self):
        """id_cita es UNIQUE en la tabla Ingreso."""
        ingreso = self.repo.registrar(self.nuevo())

        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nuevo(id_cita=ingreso.id_cita))

    def test_la_recepcionista_es_opcional(self):
        ingreso = self.repo.registrar(
            self.nuevo(id_recepcionista=self.recepcionista.id_recepcionista)
        )

        fila = self.leer_fila("Ingreso", id_ingreso=ingreso.id_ingreso)
        self.assertEqual(fila["id_recepcionista"], self.recepcionista.id_recepcionista)

    def test_el_alta_no_puede_ser_anterior_al_ingreso(self):
        with self.assertRaises(ValueError):
            self.nuevo(fecha_ingreso=self.hace_dias(3), fecha_alta=self.hace_dias(10))

    def test_una_fk_inexistente_falla_en_la_base(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nuevo(num_habitacion=9999))


class ObtenerIngresos(IngresoTestCase):
    def test_obtener_por_id_reconstruye_la_entidad(self):
        ingreso = self.repo.registrar(self.nuevo(fecha_ingreso="2026-12-01 12:00:00"))

        leido = self.repo.obtener_por_id(ingreso.id_ingreso)

        self.assertIsInstance(leido, Ingreso)
        self.assertIsInstance(leido.fecha_ingreso, datetime)
        self.assertEqual(leido.fecha_ingreso, datetime(2026, 12, 1, 12, 0))

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))

    def test_obtener_todos_va_del_mas_reciente_al_mas_antiguo(self):
        self.repo.registrar(self.nuevo(fecha_ingreso="2026-01-15 09:00:00"))
        self.repo.registrar(self.nuevo(fecha_ingreso="2026-03-20 09:00:00"))
        self.repo.registrar(self.nuevo(fecha_ingreso="2026-02-10 09:00:00"))

        fechas = [i.fecha_ingreso for i in self.repo.obtener_todos()]

        self.assertEqual(fechas, sorted(fechas, reverse=True))

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarIngreso(IngresoTestCase):
    def test_sin_id_inserta_y_asigna_el_id(self):
        ingreso = self.nuevo()

        self.assertTrue(self.repo.guardar(ingreso))

        self.assertIsNotNone(ingreso.id_ingreso)
        self.assertEqual(self.contar("Ingreso"), 1)

    def test_con_id_actualiza_sin_duplicar(self):
        ingreso = self.repo.registrar(self.nuevo())
        otra = self.crear_habitacion()

        ingreso.num_habitacion = otra.num_habitacion
        self.assertTrue(self.repo.guardar(ingreso))

        self.assertEqual(self.contar("Ingreso"), 1)
        self.assertEqual(
            self.repo.obtener_por_id(ingreso.id_ingreso).num_habitacion,
            otra.num_habitacion,
        )

    def test_valida_la_entidad_antes_de_escribir(self):
        ingreso = self.repo.registrar(self.nuevo())
        ingreso.fecha_alta = self.hace_dias(10)  # anterior al ingreso
        with self.assertRaises(ValueError):
            self.repo.guardar(ingreso)


class DarBajaIngreso(IngresoTestCase):
    """Dar de baja un ingreso es dar de alta al paciente: le pone fecha_alta."""

    def test_asigna_la_fecha_de_alta(self):
        ingreso = self.repo.registrar(self.nuevo())

        self.assertTrue(self.repo.darbaja(ingreso))

        fila = self.leer_fila("Ingreso", id_ingreso=ingreso.id_ingreso)
        self.assertIsNotNone(fila["fecha_alta"])

    def test_no_borra_la_fila(self):
        ingreso = self.repo.registrar(self.nuevo())

        self.repo.darbaja(ingreso)

        self.assertEqual(self.contar("Ingreso"), 1)

    def test_refleja_la_fecha_de_alta_en_la_entidad(self):
        ingreso = self.repo.registrar(self.nuevo())

        self.repo.darbaja(ingreso)

        self.assertIsInstance(ingreso.fecha_alta, datetime)

    def test_la_fecha_de_alta_que_genera_no_trae_microsegundos(self):
        """`chk_ingreso_formato` compara contra datetime(), que los descarta.

        Si `darbaja` escribiera `datetime.now()` tal cual, el CHECK fallaria
        siempre y nunca se podria dar de alta a nadie.
        """
        ingreso = self.repo.registrar(self.nuevo())

        self.assertTrue(self.repo.darbaja(ingreso))

        self.assertEqual(ingreso.fecha_alta.microsecond, 0)
        guardada = self.leer_fila("Ingreso", id_ingreso=ingreso.id_ingreso)["fecha_alta"]
        self.assertEqual(len(guardada), 19, f"formato inesperado: {guardada!r}")

    def test_respeta_la_fecha_de_alta_que_ya_traia_la_entidad(self):
        ingreso = self.repo.registrar(self.nuevo())
        alta = ingreso.fecha_ingreso + timedelta(days=1)
        ingreso.fecha_alta = alta

        self.assertTrue(self.repo.darbaja(ingreso))

        self.assertEqual(ingreso.fecha_alta, alta)
        self.assertEqual(
            self.leer_fila("Ingreso", id_ingreso=ingreso.id_ingreso)["fecha_alta"],
            alta.isoformat(sep=" "),
        )

    def test_sin_id_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo()))

    def test_con_id_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo(id_ingreso=9999)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
