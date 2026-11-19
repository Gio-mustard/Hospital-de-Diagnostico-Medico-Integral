"""Pruebas de IngresoEmergenciaRepositorio.

Es la otra especializacion de AtencionMedica, junto con Cita. A diferencia de
Cita, su baja es fisica (DELETE) y la atencion se ubica en una habitacion, no
en un consultorio.
"""

import sqlite3
import unittest
from datetime import datetime

from model.constants import NivelesUrgencia
from model.ingreso_emergencia import IngresoEmergencia
from model.repositories import (
    IngresoEmergenciaRepositorio,
    IngresoEmergenciaSQLRepository,
)

from .base import ContratoRepositorioMixin, RepositorioTestCase


class IngresoEmergenciaTestCase(RepositorioTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.repo = IngresoEmergenciaSQLRepository(self.db)

    def nuevo(self, **cambios) -> IngresoEmergencia:
        datos = {
            "id_paciente": self.paciente.id_paciente,
            "id_medico": self.medico.id_medico,
            "fecha_hora": "2026-12-01 03:15:00",
            "motivo": "Dolor torácico",
            "nivel_urgencia": "Alto",
        } | cambios
        return IngresoEmergencia(**datos)


class ContratoDeIngresoEmergencia(ContratoRepositorioMixin, IngresoEmergenciaTestCase):
    """IngresoEmergenciaRepositorio y su implementacion SQL."""

    interfaz = IngresoEmergenciaRepositorio
    implementacion = IngresoEmergenciaSQLRepository


class RegistrarIngresoEmergencia(IngresoEmergenciaTestCase):
    def test_asigna_el_id_generado(self):
        self.assertEqual(self.repo.registrar(self.nuevo()).id_ingreso_emergencia, 1)
        self.assertEqual(self.repo.registrar(self.nuevo()).id_ingreso_emergencia, 2)

    def test_devuelve_la_misma_instancia(self):
        emergencia = self.nuevo()
        self.assertIs(self.repo.registrar(emergencia), emergencia)

    def test_deja_la_fila_escrita(self):
        emergencia = self.repo.registrar(
            self.nuevo(nivel_urgencia=NivelesUrgencia.CRITICO, motivo="Politraumatismo")
        )

        fila = self.leer_fila(
            "IngresoEmergencia", id_ingreso_emergencia=emergencia.id_ingreso_emergencia
        )
        self.assertEqual(fila["motivo"], "Politraumatismo")
        self.assertEqual(fila["nivel_urgencia"], "Crítico")
        self.assertIsNone(fila["diagnostico"])

    def test_guarda_la_fecha_con_el_formato_del_ddl(self):
        emergencia = self.repo.registrar(
            self.nuevo(fecha_hora=datetime(2026, 12, 1, 3, 15))
        )

        fila = self.leer_fila(
            "IngresoEmergencia", id_ingreso_emergencia=emergencia.id_ingreso_emergencia
        )
        self.assertEqual(fila["fecha_hora"], "2026-12-01 03:15:00")

    def test_la_habitacion_y_la_recepcionista_son_opcionales(self):
        emergencia = self.repo.registrar(
            self.nuevo(
                num_habitacion=self.habitacion.num_habitacion,
                id_recepcionista=self.recepcionista.id_recepcionista,
            )
        )

        fila = self.leer_fila(
            "IngresoEmergencia", id_ingreso_emergencia=emergencia.id_ingreso_emergencia
        )
        self.assertEqual(fila["num_habitacion"], self.habitacion.num_habitacion)
        self.assertEqual(fila["id_recepcionista"], self.recepcionista.id_recepcionista)

    def test_la_ubicacion_de_una_emergencia_es_su_habitacion(self):
        emergencia = self.repo.registrar(
            self.nuevo(num_habitacion=self.habitacion.num_habitacion)
        )

        self.assertEqual(emergencia.ubicacion, self.habitacion.num_habitacion)

    def test_valida_la_entidad_antes_de_escribir(self):
        emergencia = self.nuevo()
        emergencia.nivel_urgencia = "Urgentísimo"
        with self.assertRaises(ValueError):
            self.repo.registrar(emergencia)
        self.assertEqual(self.contar("IngresoEmergencia"), 0)

    def test_una_fk_inexistente_falla_en_la_base(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.registrar(self.nuevo(id_medico=9999))


class ObtenerIngresosEmergencia(IngresoEmergenciaTestCase):
    def test_obtener_por_id_reconstruye_la_entidad(self):
        emergencia = self.repo.registrar(self.nuevo())

        leido = self.repo.obtener_por_id(emergencia.id_ingreso_emergencia)

        self.assertIsInstance(leido, IngresoEmergencia)
        self.assertIsInstance(leido.fecha_hora, datetime)
        self.assertIs(leido.nivel_urgencia, NivelesUrgencia.ALTO)

    def test_obtener_por_id_devuelve_none_si_no_existe(self):
        self.assertIsNone(self.repo.obtener_por_id(9999))

    def test_obtener_todos_va_del_mas_reciente_al_mas_antiguo(self):
        self.repo.registrar(self.nuevo(fecha_hora="2026-01-15 09:00:00"))
        self.repo.registrar(self.nuevo(fecha_hora="2026-03-20 09:00:00"))
        self.repo.registrar(self.nuevo(fecha_hora="2026-02-10 09:00:00"))

        fechas = [e.fecha_hora for e in self.repo.obtener_todos()]

        self.assertEqual(fechas, sorted(fechas, reverse=True))

    def test_obtener_todos_sin_filas_devuelve_tupla_vacia(self):
        self.assertEqual(self.repo.obtener_todos(), ())


class GuardarIngresoEmergencia(IngresoEmergenciaTestCase):
    def test_sin_id_inserta_y_asigna_el_id(self):
        emergencia = self.nuevo()

        self.assertTrue(self.repo.guardar(emergencia))

        self.assertIsNotNone(emergencia.id_ingreso_emergencia)
        self.assertEqual(self.contar("IngresoEmergencia"), 1)

    def test_con_id_actualiza_sin_duplicar(self):
        emergencia = self.repo.registrar(self.nuevo())
        emergencia.diagnostico = "Infarto agudo"

        self.assertTrue(self.repo.guardar(emergencia))

        self.assertEqual(self.contar("IngresoEmergencia"), 1)
        self.assertEqual(
            self.repo.obtener_por_id(emergencia.id_ingreso_emergencia).diagnostico,
            "Infarto agudo",
        )

    def test_puede_asignar_la_habitacion_despues(self):
        emergencia = self.repo.registrar(self.nuevo())
        self.assertIsNone(emergencia.num_habitacion)

        emergencia.num_habitacion = self.habitacion.num_habitacion
        self.assertTrue(self.repo.guardar(emergencia))

        self.assertEqual(
            self.repo.obtener_por_id(emergencia.id_ingreso_emergencia).num_habitacion,
            self.habitacion.num_habitacion,
        )

    def test_valida_la_entidad_antes_de_escribir(self):
        emergencia = self.repo.registrar(self.nuevo())
        emergencia.motivo = ""
        with self.assertRaises(ValueError):
            self.repo.guardar(emergencia)


class DarBajaIngresoEmergencia(IngresoEmergenciaTestCase):
    """Aqui la baja es fisica: a diferencia de Cita, no hay estado que cambiar."""

    def test_borra_la_fila(self):
        emergencia = self.repo.registrar(self.nuevo())

        self.assertTrue(self.repo.darbaja(emergencia))

        self.assertEqual(self.contar("IngresoEmergencia"), 0)

    def test_sin_id_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo()))

    def test_con_id_inexistente_devuelve_false(self):
        self.assertFalse(self.repo.darbaja(self.nuevo(id_ingreso_emergencia=9999)))

    def test_no_se_puede_borrar_una_emergencia_con_receta(self):
        """La FK de Receta es ON DELETE RESTRICT."""
        emergencia = self.repo.registrar(self.nuevo())
        self.crear_receta(id_ingreso_emergencia=emergencia.id_ingreso_emergencia)

        with self.assertRaises(sqlite3.IntegrityError):
            self.repo.darbaja(emergencia)

        self.assertEqual(self.contar("IngresoEmergencia"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
